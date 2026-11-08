# RETRIEVAL: commit consecutive selected direct-source grants together

Status: ACTIVE. User retrieval optimization goal; root designs/owns backend;
PRIME owns merge/delivery. Branch codex/direct-source-grants.
Topology: stacked on #2216 exact400d999c1b811be142a9909998f966dae7c1a64b.
Merge/rebase order: #2214, #2216, then this slice. Overlapping service ownership
is an explicit successor lease, not an independent competing lane.

Outcome: one authorization commit per consecutive direct-source group from one
acknowledged selection, before source I/O. Keep existing individual grant events,
activity capture, read order and individual observation commits. No new durable
representation, provider decision, source choice, observation batch or recovery.
Replace the singular direct-source authorization producer, including singleton use.

Expected writes: this handoff; src/application_state/agent_conversation/native_reads.py;
src/application_state/agent_conversation/service.py;
apps/live_control_server/services/corpus_source_navigation.py;
apps/live_control_server/services/plan_jev_driver.py;
tests/test_native_direct_source_selection.py; tests/test_native_retrieval_activity.py.

Evidence: direct-source-grants-v1 under chat evidence root. Independent ordering
review passes all four retained prefixes and exact writer frames. Predicted saved
grant transactions Q01=8,Q09=9,Q14=1,Q15=0; not a measured speedup.

Hypothesis: reducing repeated full-ledger transactions materially lowers admission
cost without changing selected evidence. Controls: same corpus/model/selection,
existing typed grants, independent per-source observations. Accept only closed-batch
atomicity, exact complete replay without revision bump, payload/citation conservation,
and measured reduced transaction work. Partial/conflicting/reordered replay, duplicate
IDs/handles, stale claims and foreign selection must reject atomically before I/O.
Group no grants across search/section operations. Do not call offered() while draining
pending grants. Resolve returned grants by exact requested IDs, not a ledger tail slice.
Crash with pending grants remains fail closed; no recovery behavior is invented.

Validation: actual disposable APP and ordinary SDK source tests for batch and singleton,
mixed source/search/section selection, progress before each Core read, mid-group failure,
replay/conflicts/stale claims, and final source/citation equality. Independent cumulative
review. Local retained-prefix comparison first; then bounded matched ordinary workflow
only after review. Promising results require full15 repeated validation before adoption.
Stop on acceptance bypass, partial grant commit, changed I/O order, missing traces,
recovery expansion or quality regression; do not repeat unchanged paid runs.

Resources: evaluator55447 disposable clones/test DBs, unique evidence directories only.
No primary/live UI/API/native graph mutations. No UI paths. Historical evidence retained.

Discovery checkpoint: driver previously invoked select per handle. Its loop joins this
same capability lease to forward consecutive direct selections together; all other
capabilities keep order and remain separate. This is required for batching to occur.

Local verification: 63 direct-source/activity/dispatch checks, 37 durable writer/
decision checks, and 43 component checks pass. Existing serializer fixture warnings
remain visible. A new inspection fixture self-deadlocked on fence.turn inside the
read lock; the provider-free test was stopped and its callback corrected. Corrected
ordinary multi-source execution and injected mid-read failure both pass. Evidence
is retained; no runtime/latency adoption or full benchmark success is claimed.
