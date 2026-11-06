# Isolated ingestion evaluation

Use `scripts/evaluate_ingestion.py` for future cohorts. The old per-cohort capture/monitor/audit scripts remain historical evidence, not the execution interface. This CLI calls Buddy's ordinary ingestion route; it does not add a producer, change ingestion passes or score semantic Gold automatically.

## Steps

1. Prepare one JSON manifest with the exact runtime, sources, ordinary requests and isolated database identities. Keep credentials in environment variables. Pin the evaluator code with `ingestion_evaluation.runner.tooling_identity()` and pin every source/request file by SHA256. Use a fresh output directory for each distinct cohort; do not reuse it after an unknown outcome.
2. Run `python scripts/evaluate_ingestion.py qualify --manifest MANIFEST`. This is read-only and returns the qualification SHA. It verifies runtime files and dependency revisions, database addresses/OIDs/cluster, source revisions, generic name-review decisions, native revision and prior run contracts.
3. Run `python scripts/evaluate_ingestion.py capture --manifest MANIFEST --qualification-sha SHA`. This performs one ordinary request per item, serially, and stops on the first failure or unproven result. The manifest and qualification are rechecked before dispatch. A database-scoped advisory lease excludes other standardized captures, active evaluator transactions are checked, and an unresolved prepared/running run for the same source blocks redispatch even from a new output directory. There is no evaluator provider-attempt cap; product accounting and attempt policy own that boundary.
4. Use `observe` for read-only actual run status. Use `pause` to write a durable pause marker; the current ordinary turn settles, and no later item dispatches. SIGINT/SIGTERM also request this graceful stop. Force-killing leaves the item unknown. A dispatch record prevents automatic replay even if the process disappeared or observation timed out.
5. After capture has settled, run `audit` and `report`. Audit acquires the lifecycle lock and verifies conserved database rows, exact components, corrected-source lineage, the owning quote-integrity validator, private response bindings and existing product usage projection. A report names the next broken/unproven boundary and reports actual costs/tokens, keeping missing totals unknown. Literal integrity is not semantic correctness.
6. Review semantic completeness/precision independently against the source-grounded Gold. Preserve those judgments separately. Governed publication and actual readback follow their own owner contracts; this runner never publishes.

Commands share `--manifest MANIFEST`. For historical comparison, set `retained_run_id` on every item, then use `qualify`, `audit-retained`, and `report`. Such a manifest cannot dispatch. This mode attributes exact retained runs and does not claim they were produced by a newer build. Pin the historical producing runtime and source. Interrupted/unknown runs remain unproven; do not use retained audit to manufacture terminal or semantic success.

## Manifest contract

`schema` is `dmb_ingestion_evaluation_v1`. The following fields are required by the Buddy adapter:

- `tooling_sha256`: hash returned by `tooling_identity()` for this CLI/core/adapter.
- `runtime`: `{ "path": "...", "sha256": "..." }` pin to a runtime manifest containing `root` and `files` (`path`, `sha256`). Paths and hashes identify actual build bytes, including retained composition constituents.
- `dependencies`: installed package names mapped to exact VCS commit IDs.
- `output`: new private evidence directory; `isolation`: `isolated`.
- `world_id`, `native_context`, `profile_id`, `model_id`, `expected_limits`: exact qualified product/native configuration. Limits are adopted existing product settings, not new evaluator caps.
- `databases`: `app` and `native`, each containing `dsn_env`, `host`, `port`, `database`, `oid`, `cluster` and the owning `product_env`. Database credentials are environment-only. Native is always read-only. APP writes are permitted only during the ordinary route request.
- `app_append_tables`: a subset of `source.artifact`, `source.revision`, `ingest.run`, `ingest.component_payload`. Existing rows must be conserved.
- `environment`: explicit non-secret isolated product configuration, including `DMB_ARTIFACT_DATA_ROOT`, deployment/auth mode and graph authority. Implicit local profiles and environment files in the runtime are rejected. The runner assigns its own auth session-store path.
- `operator_token_env`, `provider_credential_envs`: names of existing environment variables, never their secret values.
- `items`: unique safe `id`, `campaign_id`, `session_id`, `source_artifact_id`, `source_revision_id`, `source` file pin, `request` file pin, and `effective_sha256` after the reviewed generic name corrections. Requests are ordinary fresh source-only recap requests. Neither accepted answers nor Gold enter them. Historical read-only items also have `retained_run_id`.

Output records include qualification, execution intent, per-item dispatch, exact HTTP bytes (base64 plus SHA256), errors, component copies, terminal outcome, audit and report projection. Database source/run/components remain product authority; copies support reproducibility. Component export failure never grants permission to repeat inference. Reports preserve source scope and distinguish capture, literal evidence, independent semantics and publication.

The product adapter currently supports the source-only recap workflow. Worldbuilding must adopt its distinct source/publication rules in a separately reviewed adapter before execution; do not disguise it as recap.
