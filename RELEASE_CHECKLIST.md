# AsBuiltDoc Contracts Release Checklist

This repo is the canonical source of contracts/schemas for AsBuiltDoc.
Releases are consumed as immutable versioned packs by LNV.AsBuiltDoc.Core.

## 1. Pre-release validation

### 1.1 Required standards schemas present
Confirm these exist under `standards/`:
- solution.plan.schema.v1.json
- bundle.manifest.schema.v1.json
- objectIndex.schema.v1.json
- coverage.schema.v1.json
- finding.schema.v1.json

### 1.2 JSON sanity
- All schema files are valid JSON (no trailing commas)
- No duplicate keys in JSON objects

### 1.3 Pack layout
The contracts zip MUST unzip to:
- `standards/`
- `tech/`

No extra top-level folder is preferred. If one exists, ensure Core’s sync script can flatten it.

### 1.4 Dataset schema folder naming (Direct-v1)
For `CollectorContractManifest` contracts, schema folder naming is explicit via
`spec.datasetSchemaPath` (for example, `dataset`).

Guidance:
- New Direct-v1 contracts SHOULD use `dataset/` and set `spec.datasetSchemaPath: dataset`.
- Legacy `schemaVersion: 1` manifests may still use `schemas/` by convention.
- If a contract uses a non-default folder name, document it in the manifest/spec so Core tools can resolve it deterministically.

## 2. Build the contracts pack

Name:
- `asbuiltdoc-contracts-vX.Y.Z.zip`

Contents:
- `standards/*`
- `tech/*`

Reference command (run from repo root):
- `git archive --format=zip --output asbuiltdoc-contracts-vX.Y.Z.zip HEAD standards tech`

Validation command:
- `unzip -l asbuiltdoc-contracts-vX.Y.Z.zip`

## 3. Smoke test the pack (required)

From a Core checkout:

1) Sync from the release URL (or by version)
- `pwsh .\scripts\Sync-ContractsToDeps.ps1 -ContractsVersion X.Y.Z -Clean -VerboseOutput`

2) Run Echo capture in strict mode
- `pwsh .\scripts\Invoke-LnvSolutionCapture.ps1 -PlanPath .\plans\Echo-Local-...json -ConfigPath .\config\config_used.json -OutputPath .\out -StrictPlan -StrictContracts`

3) Confirm manifest stamps the contracts snapshot
- `manifest.json` contains `dependencies.contractsSnapshot.version == X.Y.Z`

## 4. Tag + Release (immutable)

1) Create and push tag:
- `git tag vX.Y.Z`
- `git push origin vX.Y.Z`

2) Create GitHub Release from that tag:
- Release name: `vX.Y.Z`
- Target tag: `vX.Y.Z`
- Attach: `asbuiltdoc-contracts-vX.Y.Z.zip`

CLI example (`gh`):
- `gh release create vX.Y.Z asbuiltdoc-contracts-vX.Y.Z.zip --title "vX.Y.Z" --notes "Contracts pack release vX.Y.Z"`

DO NOT replace assets on an existing version. Publish a new version instead.

## 5. Notes on versioning
- Patch: safe additions / clarifications
- Minor: additive schema changes
- Major: breaking schema changes
