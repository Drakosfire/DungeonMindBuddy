# Graph request recovery and answer acceptance

Status: ACTIVE. Operator authorized PRIME to own the Q01 fix on 2026-10-26.
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
