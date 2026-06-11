#!/usr/bin/env python3
"""Collect a normalized contract-state document from an AsBuiltDoc repository."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--role", required=True)
    parser.add_argument("--config", default=".knowledgeCI/contract-state.yaml")
    parser.add_argument("--schema", required=True)
    parser.add_argument("--output", default="contract-state.json")
    return parser.parse_args()


def run_git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=root, check=False, text=True, capture_output=True
    )
    return result.stdout.strip() if result.returncode == 0 else ""


def load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        import yaml  # type: ignore
    except ModuleNotFoundError as exc:
        raise SystemExit("PyYAML is required when contract-state.yaml exists") from exc
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def evidence(root: Path, patterns: list[str]) -> list[dict[str, str]]:
    found: dict[str, dict[str, str]] = {}
    for pattern in patterns:
        for path in root.glob(pattern):
            if path.is_file():
                relative = path.relative_to(root).as_posix()
                found[relative] = {"path": relative, "sha256": sha256(path)}
    return [found[key] for key in sorted(found)]


def read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return None


def psd1_version(path: Path) -> str | None:
    if not path.exists():
        return None
    match = re.search(
        r"(?im)^\s*ModuleVersion\s*=\s*['\"]([^'\"]+)['\"]",
        path.read_text(encoding="utf-8-sig"),
    )
    return match.group(1) if match else None


def normalize_version(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text[1:] if text.lower().startswith("v") else text or None


def validate(document: dict[str, Any], schema_path: Path) -> None:
    try:
        import jsonschema  # type: ignore
    except ModuleNotFoundError as exc:
        raise SystemExit("jsonschema is required to validate contract-state output") from exc
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker()).validate(document)


def check_observations(full_name: str, commit: str, required: list[str]) -> list[dict[str, str]]:
    token = os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN")
    if not token or not required or not commit:
        return [{"name": name, "status": "unknown"} for name in required]
    request = urllib.request.Request(
        f"https://api.github.com/repos/{full_name}/commits/{commit}/check-runs?per_page=100",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.load(response)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return [{"name": name, "status": "unknown"} for name in required]
    observed: dict[str, str] = {}
    failing = {"failure", "timed_out", "cancelled", "action_required", "startup_failure"}
    for check in payload.get("check_runs") or []:
        name = str(check.get("name") or "")
        conclusion = str(check.get("conclusion") or "")
        status = "passing" if conclusion in {"success", "neutral", "skipped"} else "unknown"
        if conclusion in failing:
            status = "failing"
        observed[name] = status
    return [{"name": name, "status": observed.get(name, "unknown")} for name in required]


def main() -> int:
    args = arguments()
    root = Path(args.repo_root).resolve()
    config = load_yaml(root / args.config)
    repository_config = config.get("repository") or {}
    discovery = config.get("discovery") or {}
    github_repository = os.getenv("GITHUB_REPOSITORY", "")
    remote_repo = run_git(root, "remote", "get-url", "origin")
    inferred_name = root.name
    if github_repository and "/" in github_repository:
        owner, name = github_repository.split("/", 1)
    else:
        match = re.search(r"github\.com[:/]([^/]+)/([^/.]+)(?:\.git)?$", remote_repo)
        owner, name = (match.group(1), match.group(2)) if match else ("unknown", inferred_name)

    owner = str(repository_config.get("owner") or owner)
    name = str(repository_config.get("name") or name)
    commit = os.getenv("GITHUB_SHA") or run_git(root, "rev-parse", "HEAD")
    branch = os.getenv("GITHUB_REF_NAME") or run_git(root, "branch", "--show-current") or "unknown"
    ref_type = os.getenv("GITHUB_REF_TYPE")
    tag = branch if ref_type == "tag" else run_git(root, "describe", "--tags", "--exact-match")
    tag = tag or None

    manifest_path = root / str(discovery.get("module_manifest") or "")
    component_version = psd1_version(manifest_path) if str(manifest_path) != str(root) else None
    version_source = manifest_path.relative_to(root).as_posix() if component_version else None
    if not component_version and tag:
        component_version = normalize_version(tag)
        version_source = "git-tag"
    if not component_version:
        described = run_git(root, "describe", "--tags", "--abbrev=0")
        component_version = normalize_version(described)
        version_source = "git-describe" if component_version else None

    snapshot_path = root / str(discovery.get("contracts_snapshot") or ".deps/contracts/contracts.snapshot.json")
    snapshot_raw = read_json(snapshot_path)
    snapshot = None
    resolved_version = None
    contracts_source = None
    if snapshot_raw is not None:
        resolved_version = normalize_version(snapshot_raw.get("version"))
        contracts_source = str(snapshot_raw.get("source") or "") or None
        snapshot = {
            "path": snapshot_path.relative_to(root).as_posix(),
            "version": resolved_version,
            "source": contracts_source,
            "checksum": snapshot_raw.get("packSha256") or snapshot_raw.get("sha256"),
            "syncedAtUtc": snapshot_raw.get("syncedUtc"),
        }
    elif args.role == "contract-authority":
        resolved_version = component_version
        contracts_source = version_source

    standard_patterns = list(discovery.get("standards") or ["standards/**/*.json"])
    tech_patterns = list(discovery.get("tech_manifests") or ["tech/**/manifest.yaml"])
    export_patterns = list(discovery.get("contract_exports") or ["exports/**/manifest.yaml", "exports/**/*.schema.json"])
    standards = evidence(root, standard_patterns)
    tech_manifests = evidence(root, tech_patterns)
    contract_exports = evidence(root, export_patterns)
    schema_ids: set[str] = set()
    for item in standards + contract_exports:
        if item["path"].endswith(".json"):
            payload = read_json(root / item["path"])
            if payload:
                identifier = payload.get("$id") or payload.get("schema_version") or payload.get("schemaVersion")
                if identifier is not None:
                    schema_ids.add(str(identifier))

    warnings: list[str] = []
    errors: list[str] = []
    if args.role != "contract-authority" and snapshot is None:
        warnings.append("No contracts snapshot was discovered.")
    if args.role == "contract-authority" and not standards:
        errors.append("No standards schemas were discovered.")

    workflow_url = None
    if os.getenv("GITHUB_SERVER_URL") and os.getenv("GITHUB_REPOSITORY") and os.getenv("GITHUB_RUN_ID"):
        workflow_url = (
            f"{os.environ['GITHUB_SERVER_URL']}/{os.environ['GITHUB_REPOSITORY']}"
            f"/actions/runs/{os.environ['GITHUB_RUN_ID']}"
        )
    required_check_names = [str(value) for value in (config.get("required_checks") or [])]
    required_checks = check_observations(f"{owner}/{name}", commit, required_check_names)
    technologies = sorted(
        {str(value) for value in (config.get("technology_ids") or []) if str(value).strip()}
    )
    document = {
        "schemaVersion": 1,
        "generatedAtUtc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "repository": {
            "owner": owner,
            "name": name,
            "fullName": f"{owner}/{name}",
            "role": args.role,
            "commit": commit or "unknown",
            "branch": branch,
            "tag": tag,
            "workflowRunUrl": workflow_url,
        },
        "component": {
            "version": component_version,
            "versionSource": version_source,
            "directV1": bool(config.get("direct_v1", args.role != "legacy")),
            "technologyIds": technologies,
        },
        "contracts": {
            "resolvedVersion": resolved_version,
            "versionSource": contracts_source,
            "supportedRange": config.get("supported_contracts_range"),
            "snapshot": snapshot,
            "schemaIdentifiers": sorted(schema_ids),
        },
        "artifacts": {
            "standards": standards,
            "techManifests": tech_manifests,
            "contractExports": contract_exports,
        },
        "validation": {
            "requiredChecks": required_checks,
            "strictContractsCapable": bool(config.get("strict_contracts_capable", False)),
        },
        "diagnostics": {
            "warnings": warnings,
            "errors": errors,
            "evidence": sorted(
                {item["path"] for item in standards + tech_manifests + contract_exports}
                | ({snapshot["path"]} if snapshot else set())
            ),
        },
    }
    validate(document, Path(args.schema).resolve())
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
