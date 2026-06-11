# LNV.AsBuiltDoc.Contracts

Canonical contracts/schemas repository for AsBuiltDoc.

## Repository layout
- `standards/` shared schema contracts.
- `tech/` per-technology contracts (`manifest.yaml`, `plan_validation.yaml`, collector specs, dataset schemas).

## Release publishing (contract zip pack)
Releases are produced by GitHub Actions workflow `.github/workflows/release-pack.yml`.

### What triggers a release
- Pushing a tag that matches `v*` (for example `v1.2.3`).

### Pre-release validation
- Pull requests targeting `dev` or `main` validate changes under `standards/` and `tech/`.
- Pushes to `dev` run the same validation used by tagged releases.
- Validation checks required contract files, JSON/YAML syntax, manifest dataset paths, and the candidate zip archive.

### What the workflow does
1. Validates required folders exist: `standards/` and `tech/`.
2. Verifies every `tech/*` folder has `manifest.yaml` and `plan_validation.yaml`.
3. Builds `asbuiltdoc-contracts-vX.Y.Z.zip` from `standards/` + `tech/`.
4. Generates `asbuiltdoc-contracts-vX.Y.Z.zip.sha256`.
5. Creates/updates the GitHub Release for the tag and uploads both assets.

### Correct release steps
1. Ensure branch is ready and merged.
2. Create and push a semver tag:
   - `git tag vX.Y.Z`
   - `git push origin vX.Y.Z`
3. Wait for workflow **Release contracts pack** to complete.
4. Verify GitHub Release `vX.Y.Z` contains:
   - `asbuiltdoc-contracts-vX.Y.Z.zip`
   - `asbuiltdoc-contracts-vX.Y.Z.zip.sha256`

For pre-release checks and smoke test guidance, see `RELEASE_CHECKLIST.md`.
