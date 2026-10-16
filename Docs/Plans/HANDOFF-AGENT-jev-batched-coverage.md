# AGENT — batch unread actions for missing answer coverage

ACTIVE. PRIME solo; ARCHITECTURE independent code/evidence review and policy advice.
Baseae0e4614d2aca1535d13c67533a4c1900c78ea8b; branch
codex/jev-batched-coverage-check; isolated /tmp/prime-recap-mention-boundaries.
Serial successor to merged #1273; checked open Ingest leases are disjoint.

One optional evaluator capability: before tentative sufficient stopping, independently
classify every unread legal action as useful/not_useful/unknown for missing coverage,
qualification or contradiction of the exact question and current evidence. Acquire
all useful unique actions as a wave with existing native bounded chunks, then
reevaluate full evidence. Discovery hints remain non-authoritative. If no useful
action remains and any necessary coverage is unknown, hold success. None remains
heuristic; no roster/gold IDs/manual facets or subject-identity inventions.

Writes: this handoff; Docs/Plans/HANDOFF-AGENT-jev-competing-evidence.md;
evals/graph_memory_layer/jev_evidence_loop.py;
evals/graph_memory_layer/jev_controller_cohort.py;
evals/graph_memory_layer/run_jev_controller_cohort.py;
tests/test_jev_evidence_loop.py; tests/test_jev_controller_cohort.py.
Private live scripts/evidence have no product write lease. No runtime/API/Graph/APP
contract change, deployment, World/history/corpus write, new provider or dependency.
Existing GE→TypeSafe Jev-only execution authorized; no Luna/retry/uncertain replay.

Preserve Council7/10 and question-only conflicting-source failures. Known failures
are development regressions, not unseen validation. Freeze new plural-collection
control before inference; compare singular, redundant/foreign/temporal/belief and
unknown/failing batch controls. Prove typed ID validity, unique finite progress,
batched owning-reader validation, gold exclusion, recorded decisions/stops/usage.
After independent policy review, run exact saved-source Float/Council read-only,
record coverage/classes/latency/token changes and independent semantic review.
No automatic generic accuracy, answer quality or ordinary adoption clearance.
