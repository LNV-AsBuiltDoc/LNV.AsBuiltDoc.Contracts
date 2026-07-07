# Direct-v1 Collector Contracts Architecture (Contracts Pack 2.x)

This document defines the collector-contract architecture expected by Core for any technology contract that uses `CollectorContractManifest`.

## 1) Manifest model
A tech contract MUST provide `tech/<TechId>/manifest.yaml` with:

- `kind: CollectorContractManifest`
- `spec.datasetSchemaPath: dataset`
- `spec.datasetToSdtMapping: mapping.dataset-to-sdt.v1.yaml`
- `spec.datasets`: explicit list of dataset keys emitted by the collector
- `spec.bundleSchemas.dataset: lnv.collector.dataset.v1`

## 2) Layout model
Collector-contract tech layout MUST be:

- `tech/<TechId>/manifest.yaml`
- `tech/<TechId>/plan_validation.yaml`
- `tech/<TechId>/collector_spec.md`
- `tech/<TechId>/sdt_inventory.md`
- `tech/<TechId>/skeleton_blueprint.md`
- `tech/<TechId>/mapping.dataset-to-sdt.v1.yaml`
- `tech/<TechId>/dataset/*.schema.json`

Legacy schema layout (`tech/<TechId>/datasets/`) is not allowed.

## 3) Dataset envelope model
Collector output datasets MUST conform to envelope schema identifier:

- `schema_version: lnv.collector.dataset.v1`

Required fields in each dataset file:

- `collector`
- `source`
- `dataset`
- `item_count`
- `items`

And:

- `collector.tech_id` MUST equal the technology directory ID.
- `collector.module` and `collector.entry_point` MUST identify the invoked Direct-v1 collector.
- `source.target_key` MUST equal the canonical object key in the dataset path.
- `source.file` MUST equal the bundle-relative canonical dataset path.
- `item_count` MUST equal the length of `items`.
- `<datasetKey>.json` MUST map to `tech/<TechId>/<datasetSchemaPath>/<datasetKey>.schema.json`.
- Dataset keys MUST be in `spec.datasets`.

## 4) Contracts pack compatibility
Collector-contract tech validation assumes contracts pack version `>=2.0.0 <3.0.0` via `contracts.snapshot.json`.

## 5) Canonical output enforcement
Core accepts native envelopes only at
`datasets/<TechId>/<Domain>/<ObjectKey>/<Dataset>.json`. Raw collector captures
belong under `evidence/<TechId>/<ObjectKey>/`. Legacy wrappers, collector
staging directories, unresolved placeholders, and raw evidence under
`datasets/` fail validation.

## 6) Target location metadata
Document and inventory location metadata belongs in the solution plan target
object, not in collector runtime settings. Plans SHOULD use
`targets[].location` for stable fields such as `site`, `siteSort`, `facility`,
`building`, `room`, `row`, `rack`, `rackLocation`, `position`, and `role`.

Collectors MAY echo location metadata into normalized document datasets for
convenience, but renderers MUST NOT require collector-owned site fields when
the same target-level metadata is available from `config/solution.plan.json`.
Assembler projections should prefer the dataset value, then the plan-derived
assembler context such as `_assembler.location.site`, and then compatibility
fallbacks such as `_assembler.tags.site` or `_assembler.params.site`.

`targets[].tags.site` and legacy `targets[].params.site/rack/role` remain
compatibility inputs. Core should normalize those values into
`targets[].location` when creating a bundle. Technology-specific `params`
should remain runtime-oriented, for example API choices, timeouts, transport
options, and collection flags.

If no site can be derived, document-facing grouped projections SHOULD render an
explicit `Unassigned Site` heading rather than silently using a placeholder site
name.

## 7) Machine-readable onboarding plan
For zero-context agent onboarding and implementation planning, see:

- `docs/codex.collector-contracts.onboarding.plan.v1.yaml`
