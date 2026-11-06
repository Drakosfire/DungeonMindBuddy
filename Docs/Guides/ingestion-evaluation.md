# Isolated ingestion evaluation

Use `scripts/evaluate_ingestion.py` for future cohorts. The old per-cohort capture/monitor/audit scripts remain historical evidence, not the execution interface. This CLI calls Buddy's ordinary ingestion route; it does not add a producer, change ingestion passes or score semantic Gold automatically.

## Steps

1. Prepare one JSON manifest with the exact runtime, sources, ordinary requests and isolated database identities. Keep credentials in environment variables. Pin the evaluator code with `ingestion_evaluation.runner.tooling_identity()` and pin every source/request file by SHA256. Use a fresh output directory for each distinct cohort; do not reuse it after an unknown outcome.
2. Run `python scripts/evaluate_ingestion.py qualify --manifest MANIFEST`. This is read-only and returns the qualification SHA. It verifies runtime files and dependency revisions, database addresses/OIDs/cluster, source revisions, generic name-review decisions, native revision and prior run contracts.
3. Run `python scripts/evaluate_ingestion.py capture --manifest MANIFEST --qualification-sha SHA`. This performs one ordinary request per item, serially, and stops on the first failure or unproven result. The manifest and qualification are rechecked before dispatch. A database-scoped advisory lease excludes other standardized captures, active evaluator transactions are checked, and an unresolved prepared/running run for the same source blocks redispatch even from a new output directory. There is no evaluator provider-attempt cap; product accounting and attempt policy own that boundary.
4. Use `observe` for read-only actual run status. Use `pause` to write a durable pause marker; the current ordinary turn settles, and no later item dispatches. SIGINT/SIGTERM also request this graceful stop. Force-killing leaves the item unknown. A dispatch record prevents automatic replay even if the process disappeared or observation timed out.
5. After capture has settled, run `audit` and `report`. Audit acquires the lifecycle lock and verifies conserved database rows, exact components, corrected-source lineage, the owning quote-integrity validator, private response bindings and existing product usage projection. A report names the next broken/unproven boundary and reports actual costs/tokens, keeping missing totals unknown. Literal integrity is not semantic correctness.
6. Review semantic completeness/precision independently against the source-grounded Gold. Preserve those judgments separately. Governed claim publication and actual readback follow their own owner contracts; capture mode never publishes. The explicit source-authority mode below can publish source evidence only.

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

## Source-authority operations

Use this same CLI with `mode: source_authority_v1` to evaluate exactly one existing source API operation. This mode never dispatches ingestion, providers, claim preparation/confirmation, migrations or terminal-run adjudication. Ordinary capture's native-write ban remains intact. Source-mode manifests cannot enter ordinary capture commands.

Retain the common schema, tooling/runtime/dependency pins, isolated DB identities, product environment, World/native context, private output directory and operator-token environment name. Set `app_append_tables` to `[]`; the adapter's fixed source-operation policy owns allowed effects, not a manifest-supplied table exemption. Provider credentials, model settings and source files are not needed. APP/Core remain source-byte authority.

Add `source_authority: {"operation": "admit_context" | "extend_support", "review_pins": [{"path": "...", "sha256": "..."}]}`. Review pins retain concrete independent evidence; a file does not itself confer execution authorization. The authorized lane must own the declared evaluator/output resources.

Include one item with a safe `id`, `retained_run_id`, `expected_run_revision`, `campaign_id`, `session_id`, APP `source_artifact_id`, APP `source_revision_id`, `effective_sha256`, and a `request` file pin. The existing run must be reviewable and its actual database-backed source must match. There is no source-file selector or alternate producer. The request uses the existing strict product model:

- `admit_context`: exact `native_recap_source` snapshot, `operation: build_graph_preview_bundle`, `include_graph_extraction: false`; no text, model, supplemental evidence, fresh extraction or resume. Adds the ordinary APP source intent and Core whole-source CONTEXT evidence.
- `extend_support`: existing admitted source, exact parent/epoch, unique SUPPORT intervals and slice hashes through `/api/live/source-statements/extend-evidence`. Adds no APP rows or semantic claims. Already available exact SUPPORT intervals are refused rather than duplicated.

Run `source-qualify --manifest MANIFEST`, then `source-execute --manifest MANIFEST --qualification-sha SHA`. The first command is read-only. It verifies the existing source/run, exact request, Core context and actual head-table/row identities before effects. Execution rechecks the complete qualification under the shared evaluator lease and records one immutable intent before one authenticated, route-allowlisted request. It forbids external HTTP and restores both DB bindings to read-only. Native writes are limited to that source route window; only context admission enables APP's ordinary source-intent write.

Use `source-inspect` for read-only receipt/opening/conservation reconciliation in the same qualified operation directory, or `source-report` to read local outcome metadata without opening a database. An execution marker always prevents redispatch, including after process interruption; a new output directory is not permission to retry an unresolved intent. Source intent/receipt checks and the shared DB lease also exclude existing or concurrent operations. Existing product authority remains readable without these local HTTP copies; inspection never derives source identity from them.

Outcomes distinguish `verified`, `committed_unverified` and `outcome_unknown`. A post-commit verification or filesystem error never means the source operation did not happen. Original responses, scrubbed errors, snapshots and later inspections remain separate immutable records. Read-only inspection may resolve the proof; it never retries/resumes a source intent. Missing original qualification prevents a historical conservation claim. Advancing the native head or changing other resources may leave the original operation committed but its current conservation window unproven.

Conservation permits exact replacements of the selected World's `knowledge_heads` row and the singleton global `knowledge_native_source_authority` epoch row, preserving all other rows. It also checks unchanged semantic entities/assertions and prior evidence against Core, exact receipt parent/child/intent, source roles, body bytes and intervals. Source-only admission's current product wire does not accept an external parent pin: the evaluator checks immediately before dispatch and verifies the actual receipt parent afterward, under its exclusive lane. It does not claim atomic protection against unrelated writers. Existing established Worlds only; no authority provisioning or World genesis.

Source authority success is not semantic publication or Gold acceptance. Continue through the separate reviewed claim-publication owner and independent actual readback.
