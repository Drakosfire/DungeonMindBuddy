# Batched admitted source reads

ACTIVE. PRIME solo implementation; ARCHITECTURE independent review.
Buddy base `85b3949c5cb4fd6419767c7a6037e3002a20750e`, branch
`codex/batched-admitted-source-reads`, non-serving checkout
`/tmp/prime-recap-mention-boundaries`. Stacked topology: depends on Core #129
reviewed head `1ed749d6ba701d6fa5a0752e743fa505a35b530b`; independent review
passed and Core/type/benchmark CI passed, integration CI remains live. Consumer
implementation may use that exact reviewed contract; merge/deployment requires
accepted Core merge and final dependency pin. No serving changes in this slice.

## Outcome and invariant

The existing Agent Harness source-read batch validates its admitted selectors in
one Core pinned context, then uses existing immutable-source body joins for each
result. Deduplicate revision digest lookups within the call. Do not treat session
pins, metadata resolution, or a sibling's successful read as an opened passage.
Preserve ordering, exact per-anchor/source/revision proof, truncation, unavailable
bodies, actual-read receipts, provider inclusion, and existing citation checks.
No new model operation, cache authority, source lookup fallback, visibility rule,
authorization limit, or Graph/publication write.

Per-anchor body failures remain explicit. A batch context/integrity failure must
not trigger unchanged single-read retries or return a successful prefix. Missing,
reordered, duplicated or foreign internal results must fail closed before receipts.
Legacy receipt-v1 behavior stays outside this adoption; production parent-owned
receipt-v2 uses the new batch. This is an existing owner contract adoption, not a
new compatibility reader.

## Exclusive write set

- This handoff
- `apps/live_control_server/integrations/dungeonmind/world_graph_reads.py`
- `apps/live_control_server/services/world_graph_retrieval.py`
- `src/graph_memory/interaction/expansion_executor.py`
- `tests/test_batched_admitted_source_reads.py` (new)
- `tests/test_selected_subject_initial_sources.py` (existing fake native-reader seam)
- `tests/test_world_graph_source_admission.py` (existing receipt fake-reader seam)
- `tests/test_recap_source_read_continuity.py` (existing split-root native fixture)
- `tests/test_agent_turn_service.py` (mounted real-APP source-read counter and
  discovery-to-object detail in the synthetic provider fixture)
- `pyproject.toml`
- `uv.lock`

Open PRs inspected: active DOGFOOD #1235 is UI-only and #1244 owns packaging;
older open document/Plan/Play/recap lanes do not own these paths. No 5202/5876,
8000/8002, retained database, provider, source/corpus or runtime config lease.

## Verification

Prove one Core batch resolution and exact single/batch body equivalence, distinct
context rejection, missing/foreign/duplicate/reordered native results, unavailable
or corrupted bodies, immutable historical source access, and digest deduplication.
Exercise the actual receipt-v2 executor and existing parent provider/citation
regressions; mocks of payload helpers alone do not establish receipt authority.
Preserve initial failures. Review cumulative diff and exact dependency pin; test,
lint/lock/diff check, commit/push/open one dependent PR for prompt review. No merge
until Core CI/merge and independent consumer review pass. Measure the saved
116-anchor workload read-only only after review; do not promise a latency target.

Predecessor: Core #129 adds typed ordered metadata batch resolution, sharing full
admission derivation with the existing single resolver. Author 162 tests, Ruff
and full Pyright pass; independent 24 batch tests and cumulative review pass.

Core #129 is now accepted and merged as `d83689cda92691758bdb132fb5ffcd170abb86df` after exact-head independent PASS and CI success (run 38928972378). Consumer dependency pin advances to that accepted merge; the original stacked gate is satisfied. No consumer or runtime acceptance is implied.

## Author evidence

59 focused adapter/body/executor/initial-hydration/receipt tests pass; one unrelated
existing search metadata fixture is deselected after reproducing its missing
`objects` fake field. Both that failing test and production search function have
identical ASTs to the base. A separate 57-test source/provider/citation selection
passed before the final two malformed-batch regressions were added.

All four mounted authenticated traversal cases pass with actual Core memory
authority, immutable source opener, synthetic provider and real disposable APP
PostgreSQL authorization/receipt, provider inclusion, delivery and history:
`/home/drakosfire/.local/state/dungeonmindbuddy/build-scratch/batch-source-read-d70ed9654c/result.json`.
The first run passed object/support but search/neighborhood correctly rejected
the fixture's unsupported property claim; the synthetic provider now follows
discovery with object detail before citing that assertion. No production claim
admission gate was relaxed.

Ruff, lock check and diff check pass. Initial lint issues were corrected. One
test rerun exhausted root disk and produced environmental errors; preserved the
cache and moved one unused old PRIME checkout with full byte/symlink verification
to `/home`, retaining its old path and untracked files. Further test scratch/cache
uses `/home`. No retained database, provider, serving process, schema or corpus
change occurred. Read-only retained performance measurement follows review.
