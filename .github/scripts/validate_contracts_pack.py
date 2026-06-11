#!/usr/bin/env python3
"""Validate the tracked content used to build a contracts release pack."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml


REQUIRED_STANDARDS = (
    "solution.plan.schema.v1.json",
    "bundle.manifest.schema.v1.json",
    "objectIndex.schema.v1.json",
    "coverage.schema.v1.json",
    "finding.schema.v1.json",
)


def parse_json(path: Path) -> Any:
    def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate key {key!r}")
            result[key] = value
        return result

    with path.open(encoding="utf-8-sig") as stream:
        return json.load(stream, object_pairs_hook=reject_duplicate_keys)


def parse_yaml(path: Path) -> Any:
    with path.open(encoding="utf-8-sig") as stream:
        return yaml.safe_load(stream)


def validate(root: Path) -> list[str]:
    errors: list[str] = []
    standards = root / "standards"
    tech = root / "tech"

    if not standards.is_dir():
        errors.append("Missing required directory: standards")
    if not tech.is_dir():
        errors.append("Missing required directory: tech")
        return errors

    for name in REQUIRED_STANDARDS:
        path = standards / name
        if not path.is_file():
            errors.append(f"Missing required standard: {path.relative_to(root)}")

    contract_dirs = sorted(
        path
        for path in tech.iterdir()
        if path.is_dir() and any(child.is_file() for child in path.rglob("*"))
    )
    if not contract_dirs:
        errors.append("No contract directories found under tech")

    for contract_dir in contract_dirs:
        manifest_path = contract_dir / "manifest.yaml"
        plan_path = contract_dir / "plan_validation.yaml"

        if not manifest_path.is_file():
            errors.append(
                f"Missing contract manifest: {manifest_path.relative_to(root)}"
            )
        if not plan_path.is_file():
            errors.append(
                f"Missing plan validation: {plan_path.relative_to(root)}"
            )

        manifest = None
        for yaml_path in (manifest_path, plan_path):
            if not yaml_path.is_file():
                continue
            try:
                parsed = parse_yaml(yaml_path)
                if yaml_path == manifest_path:
                    manifest = parsed
            except Exception as exc:
                errors.append(f"Invalid YAML {yaml_path.relative_to(root)}: {exc}")

        if isinstance(manifest, dict):
            spec = manifest.get("spec")
            dataset_path = (
                spec.get("datasetSchemaPath") if isinstance(spec, dict) else None
            )
            if dataset_path:
                resolved_dataset_path = contract_dir / str(dataset_path)
                if not resolved_dataset_path.is_dir():
                    errors.append(
                        "Manifest datasetSchemaPath does not exist: "
                        f"{resolved_dataset_path.relative_to(root)}"
                    )

    for json_path in sorted(
        path
        for base in (standards, tech)
        if base.is_dir()
        for path in base.rglob("*.json")
    ):
        try:
            parse_json(json_path)
        except Exception as exc:
            errors.append(f"Invalid JSON {json_path.relative_to(root)}: {exc}")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path.cwd(),
        help="Repository root to validate",
    )
    args = parser.parse_args()
    root = args.repo_root.resolve()
    errors = validate(root)

    if errors:
        print("Contracts pack validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    contract_count = len(
        [
            path
            for path in (root / "tech").iterdir()
            if path.is_dir() and any(child.is_file() for child in path.rglob("*"))
        ]
    )
    print(f"Contracts pack validation passed for {contract_count} contract directories.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
