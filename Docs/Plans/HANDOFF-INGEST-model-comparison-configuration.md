# INGEST: immutable ordinary ingestion configuration

Status: ACTIVE — root adopts the bounded nine-file configuration consolidation lease.
The original routing-only design followed
independent design PASS `3b88c26cbcd972ed2a20fd2201f517805c81c3d24398f33dbd2e8005cce084a5`.
Authority snapshot and review are retained under `ingestion-resume/study-model-comparison-readiness-v1`.

## Authority and bounded outcome

Root is the study steward under the user's active ingestion-study objective
(`/home/drakosfire/.codex/attachments/4ab5d6dc-f721-455f-afa2-096feac2ce6a/goal-objective.md`).
Make ordinary ingestion configuration a first-class immutable value shared by
the recap producer and evaluator. Model/provider selection supports future tuning;
no new model comparison is part of this amendment. Keep the standard DeepSeek default and its effective
requests unchanged. This slice does not adopt H4, select a winning model, run
inference, migrate data, publish facts, or change the UI.

## Re-anchor, lane and topology

- Fetched `origin/main`: `413021a988093b8ad28771f27e81752c378b8283`.
- Design branch: `codex/ingest-model-comparison-configuration`, existing isolated
  checkout `/home/drakosfire/Projects/.codex/ingest-draft-navigation/DungeonMindBuddy`.
- **stacked**: exact parent PR #2176/head
  `1df09854b3cc3816df3382aa60da60ef97ab55c3`; parent evaluator stack settles
  before #2176, then this slice. No merge authority is granted.
- No dependency on unadopted H4/PR #2173. Pinned study runtime compositions remain
  evidence, not a new production default.
- Inspected adjacent #2179 ACTIVITY and #2172 PLAY write paths; no overlap with
  the expected write set. No concurrent agent is editing this code. Existing
  frozen predecessor ownership of these study paths transfers only on ACTIVE.
- No runtime port, database or provider write lease. Tests use inert SDK/engine
  doubles or isolated fixtures; primary data stays unchanged.

## Observed owning boundaries

`graph_preview_runner` rejects an ordinary `graph_model_id` other than the
DeepSeek constant and constructs its limits inline. The evaluator repeats that
constant check. `BoundedRecapPassClient` selects the JSON instruction suffix and
fixed DeepSeek endpoint from model identity. Both branches already supply the
same JSON schema; the pinned GenerationEngine OpenRouter adapter uses one local
schema-validation/JSON-object request path. Do not invent a second schema mode.

## Proposed invariant and implementation

1. Add one pure configuration resolver in the existing bounded execution owner:
   `DMB_RECAP_MODEL_ID` and `DMB_RECAP_OPENROUTER_PROVIDER`. Absent settings resolve
   to the current DeepSeek model and `DeepSeek` endpoint. A changed model requires
   an explicit nonblank endpoint. Settings must be both absent or both present,
   including when the explicitly selected model is the default; invalid/partial configuration fails before a
   producer starts. Do not infer endpoint names or add routing fallbacks.
2. Extend the existing limits data with the explicit OpenRouter endpoint. Preserve
   existing default DeepSeek construction semantics; generic non-OpenRouter
   clients retain their existing behavior. One common request builder consumes
   the endpoint data, applies the existing JSON suffix for explicitly routed
   requests, and sends the existing schema. Delete the duplicated schema update.
   Endpoint routing stays single-provider, `allow_fallbacks=False`,
   `require_parameters=True`. Preserve allocations, deadlines, accounting and
   ordinary retry policy; add no pass or arbitrary provider-attempt cap.
3. The ordinary producer uses the resolver. Existing `graph_model_id` may be
   absent or match the configured model; it is not an arbitrary client override.
4. The shared evaluator calls this same owner to verify selected model/endpoint
   and retains that selection in qualification. Recheck selection after app
   startup and before HTTP dispatch so startup cannot silently change the model.
   Keep actual receipts, schema validation and accounting authoritative.
5. Do not add a new runner, model registry, transport, compatibility wrapper or
   provider fallback. Historical snapshots/artifacts remain immutable. Alternative
   model inference requires a later pinned comparison design and exact exposure
   authorization; this PR only supplies the ordinary configuration capability.

## Expected write set on activation

- `Docs/Plans/HANDOFF-INGEST-model-comparison-configuration.md`
- `src/graph_memory/extraction/bounded_recap_execution.py`
- `src/graph_memory/extraction/graph_preview_runner.py`
- `apps/live_control_server/services/graph_preview_runner.py`
- `src/ingestion_evaluation/buddy.py`
- `tests/test_bounded_recap_execution.py`
- `tests/test_graph_preview_runner.py`
- `tests/test_ingestion_evaluation_runner.py` (extend existing owning startup/dispatch tests)
- `Docs/Guides/ingestion-evaluation.md`

A needed change outside this set is a scope checkpoint before editing. In
particular, no GenerationEngine changes or unrelated API/PLAY/writer edits.

## Failure cases to critique before activation

- An alternate model silently inherits the DeepSeek endpoint.
- Blank/partial settings silently revert to defaults.
- Model choice changes effective prompt/schema/allocation besides the declared
  model and endpoint identity.
- A client model override bypasses server configuration.
- App startup changes configured selection after qualification.
- Historical DeepSeek constructor/request behavior changes.
- Evaluator checks introduce a second model-selection policy.

## Validation and delivery

Prove resolver default/invalid/explicit cases at its owner; prove ordinary runner
model matching and selected limits; exercise real GenerationEngine-to-fake-SDK
kwargs for default and alternate endpoint configurations. Compare default messages,
schema, routing and settings with the existing DeepSeek request contract; for
alternate comparisons only declared model/endpoint fields may differ. Verify
qualification/startup drift fails before dispatch. Run relevant bounded execution,
runner and evaluator tests, inspect cumulative base-to-head diff, obtain independent
subagent review, then commit/push/open one bounded PR. No merge or inference.

## Scope checkpoint

Discovery found an existing evaluator startup/dispatch fixture in
`tests/test_ingestion_evaluation_runner.py`. Root replaces the planned new test
module with that existing file before editing it. The original eight-file lease and
single capability remained bounded at that earlier checkpoint; no second harness or extra PR is introduced.

## Implementation verification

The three targeted suites completed with 180 passes and one existing gazetteer
fixture failure: `BoundedFixtureClient` lacks `execution_binding` when binding to
its run. The affected fixture and binding logic are unchanged by this slice;
the failure is retained at `/tmp/model-config-gazetteer-failure.txt`. Three new
ordinary producer cases passed. Real GenerationEngine with an inert SDK verifies
that only model/endpoint differ, and evaluator startup drift tests stop dispatch.
No live inference, publication or primary-state changes were performed.

## User-directed configuration consolidation checkpoint

Root adopts the user's versioned configuration direction in this existing lane.
Topology remains stacked on #2176, independent of sibling #2189/#2190/#2193;
no extra PR, merge, provider execution, publication or migration is authorized.

The amended lease includes `src/graph_memory/extraction/graph_preview_runner.py` (nine
files total). This owning controller must execute the frozen profile described
by the configuration, so snapshot retention and actual execution cannot drift.

Replace the tuple resolver and ordinary inline defaults with one immutable
`RecapIngestionConfiguration` composing the existing execution limits and a
recursively frozen registered profile. Resolve default or explicitly supplied
bounded limits once with a declared source. Record canonical snapshot/hash before
provider dispatch, refusing conflicting prior lineage. Hashes identify effective
configuration, not source/request content or executable code; callable names are
only descriptors and rely on separately pinned runtime code.

The controller retains registered-profile admission, checks descriptor equality,
and passes the frozen profile through its existing extraction options. Unsupported
mutable policy values fail rather than leak into the configuration. The evaluator
uses the same resolver, verifies expected allocations before dispatch, rechecks
full configuration after startup and binds new run lineage/telemetry to it.
Historical absence stays explicitly unknown; no default snapshot is backfilled.
Assessment policies/Gold remain separate and never enter model requests.

Verify nested immutability and real controller/extractor serialization, unchanged
standard DeepSeek messages/schema/route/settings, explicit-limit provenance,
configuration-sensitive hashes, failure-before-dispatch drift and persisted run
identity. Existing edge allocation override is retained; new per-pass models,
new pass architecture, UI and worldbuilding expansion are outside this slice.
Independent contract critique: `/tmp/ingest-firstclass-config-design-review-v1.json`.


The recap service now accepts the complete `ingestion_configuration` value;
its partial `execution_limits` entry point and the tuple model resolver are
removed, not retained as alternate configuration paths. The separate existing
worldbuilding execution API is unchanged. Tests correct one existing partial
BoundedFixtureClient initializer to use its actual superclass contract; another
baseline failure required the normal PYTHONPATH for its subprocess. Baseline
failures are retained in `/tmp/firstclass-config-inherited-failures-v1.log`.

The owning suites passed 197 tests before the final explicit-endpoint guard;
that guard's configuration unit suite passed 16 tests. Final exact-head results
and independent review travel in PR evidence; no live providers were dispatched.
