# INGEST: require explicit retry of saved recap execution

Status: MERGED_DELIVERED as PR2046 at
783980f2809a7e7c93cd9e67faf0132e3f997d12; implementation lease closed. Exact PR-head
independent approval/all7CI plus actual-merge source qualification and33owning
checks passed. Conserved API delivery preserved all91primarytables,9sessionfiles,
savedPlanHTTP/UI/native439objects; proof recap-explicit-retry-api-delivery-proof.json.
The database-execution-evidence handoff owns the separate diagnostics successor.
Owner: PRIME. Base: origin/main@e4773b18c559e14f95e39c84dc3fcca582784add.
Branch: codex/recap-explicit-retry.
Checkout: /home/drakosfire/.codex/worktrees/buddy-context-loop/DungeonMindBuddy.
Topology: parallel-independent of ADVERSARY PR2045's profile-only guidance;
serial prerequisite to PRIME's database-owned execution diagnostics. No profile,
Gold, provider, primary database, runtime or Graph effect lease.

## Outcome and critique

Return the newest exact saved extraction on ordinary repeat Process, including
failed or pending attempts, instead of implicitly dispatching again. Explicit
force_graph_run remains the retry command; changed source/configuration is a new
request. Keep exact source bytes, World binding, profile, model and supplemental
evidence checks. Never revive an older success around a newer matching failure,
or treat a non-reviewable attempt as reviewable or published.

The catalog already projects pending/failed states and an explicit retry action,
but reusable_recap_extraction discards any status other than REVIEWABLE. The
controller also records the chosen model only after execution, so a PREPARED
record cannot prove that configuration. Pin the resolved model in the existing
DRAFT/PREPARED lineage before dispatch; no new registry, state machine, table,
lock, reservation or compatibility inference is justified. This is not a global
exactly-once guarantee for simultaneous first requests or a recovery reconciler.

## Exclusive write set

- apps/live_control_server/services/ingest_run_catalog.py: return the existing
  projection for an exact matching saved configuration regardless of lifecycle.
- src/graph_memory/extraction/graph_preview_runner.py: retain the selected model
  before dispatch through the existing controller lineage.
- tests/test_live_recap_ingest_graph_preview_api.py: ordinary authenticated API
  regression tests with real disposable APP state and a synthetic provider.
- This handoff. No adjacent diagnostics transport, parser, prompt, Gold, discovery
  UI, fixture-debt, publication or manual curation changes.

## Proof and delivery

First retain red provider-free reproduction at the fetched base. Verify repeated
failed and pending requests preserve the exact saved attempt and do not execute,
mutate its revision, or create a new source/run. Verify explicit retry and changed
source remain independent attempts and an older success cannot mask a failure.
Use existing disposable54329 and dependencies, never primary data/providers.
Exercise current source/scope/model/supplement guards and owning runner tests;
inspect the cumulative diff, obtain independent exact-head Bugbot review and CI,
then merge/deliver under standing PRIME authority with conserved retained state.
No model-quality, Gold-completeness or overall ingestion-acceptance claim.

## Author verification

At the fetched base, three ordinary authenticated Process regressions fail:
failed repeat invokes the synthetic extractor twice, and PREPARED/INCOMPLETE
repeats each dispatch unexpectedly. The unmodified failure log is retained in
private runtime evidence as recap-explicit-retry-red.log. After the repair,
29 API/Build request-recovery checks and 90 runner/model/supplement/scope/catalog
checks pass. Ruff and cumulative diff checks pass. No provider, primary state,
Graph or Gold effects; these tests do not measure ingestion semantic quality.

The fix recognizes exact configuration only. Historical pending records without
a model pin are not guessed or backfilled. Existing first-request concurrency
semantics are unchanged; this is not an exactly-once dispatch contract.
