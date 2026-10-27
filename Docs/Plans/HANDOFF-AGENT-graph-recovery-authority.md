# Graph request recovery and answer acceptance

Status: SETTLED. PR1808 merged167e74fca38f8066f49117a71f65896b679a81ae after
independent Bugbot approval of exact9e3d7923b6a52415cd911ef0fbf815445ab874bd,
229 owning tests and the independent unchanged Q01 delivery checkpoint. Protected
API8000 adoption behind5202 preserved all3588 APP rows,1097 native rows and39933
retained files; schemas0077/0017 and UI11f83820 unchanged. Saved Conks Plan and both
conversation turns reloaded. Implementation lease released. Original v3 retained;
live checkpoint avoided rejection, so recovery safety rests on owning regressions
and review, not a live rejection exercise. Full typed benchmark capture remains
separate. Historical operator authorization: 2026-10-26.
Base: 0b069942b846bc6d281dbf4f26775427f3f99771.
Branch: codex/graph-recovery-authority, existing buddy-context-loop checkout.
Topology: parallel-independent of paused PR1807 and HOSTED1802; no unmerged dependency.
PR1807 remains paused, committed and pushed. This lane owns no ports or retained data.

Invariant: a rejected optional request is distinct from a failed authority check and
from an unsupported answer. Only known request-shape/capability rejections can be
recovered, with matching dispatched scope/revision and a valid retrieval session.
A successful corrected expansion can proceed to normal claim/source validation;
telemetry anchors and prose never confer answer authority. Unknown, integrity and
scope failures stay fatal regardless of later success. Preserve all failed events.
The tool surface must advertise source bundles only when its actual parent broker
is available. Keep the direct executor's authority refusal intact.

Expected write lease:
- this handoff
- apps/live_control_server/services/hermes_graph_query.py
- apps/live_control_server/services/hermes_graph_agent.py
- apps/live_control_server/services/hermes_graph_interaction_tools.py
- tests/test_live_query_hermes_graph.py
- tests/test_hermes_graph_agent.py

Verification: provider-free captured overview/batch-read event shapes; successful
recovery through ordinary claim validation; absent/foreign/stale session, no claims,
failed retry, denied/unknown outcomes, integrity errors in either order, mixed error
codes, and direct versus broker-backed tool projection. Inspect cumulative diff and
obtain independent Bugbot review. Open a separate PR. Retain original Q01 v3 and ask
BENCHMARK for the unchanged contract at the fixed ref; semantic evaluation remains
independent. No runtime deployment or database migration in this slice.

Critique: the old helper is labelled trace-only but gates delivery, and clears any
earlier error on later ID-bearing success. Merely normalizing missing fields would
expand that unsafe behavior. Recovery will classify request failures independently
of evidence projection; existing answer validation remains the acceptance owner.
