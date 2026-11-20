# Selected observation anchor priority

ACTIVE PRIME implementation; base b2c76cb6c83b3e4d9835376dd92956ab5f2b6f13.
Exact write set: this handoff, apps/live_control_server/integrations/dungeonmind/world_graph_reads.py,
tests/test_agent_selected_observations.py.

Fresh Mirathorn 1.11 clone publication committed seven reviewed observations, but
explicit object selection returns none when canonical object anchors saturate the
32-anchor bound. Reserve the complete selected evidence union before canonical
anchors; fill remaining canonical capacity deterministically and report displaced
source evidence as partial. Never admit an incomplete observation, raise bounds,
change unselected behavior, alter source pins or bypass pinned-ID validation.
If the selected union exceeds the bound, omit the selected set with an explicit gap.
ARCHITECTURE owns independent review. Prove saturated allocation, shared anchors,
over-bound union, unknown IDs and unchanged unselected behavior; rerun the committed
clone's fresh read/source-opening witness with the accepted implementation.
No provider, retained publication, serving or schema changes in this code slice.
