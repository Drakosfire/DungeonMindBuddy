# DOGFOOD · Preserve pending Build page creation from retained context

Status: ACTIVE in `codex/dogfood-pending-lore-retention` on main
`c7d1f2862f4c2cc710d21da0c595c5316d8442a7`. Alan authorized fixes for
long-chat page creation, reuse without new retrieval, and release delivery.
This serial slice follows the merged pending Build integration #4998.
The owning reader and producer work remains with #5008 and #4987.

Pending Build requires the V3 retained closure for both discussion and page
review. The shared retained owner continues to authorize each source and
validate the locked claim. Carry the serving reasoning setting for this
writer path while retaining main's current writer schema and exact
instruction witness.

Scope is this handoff, the pending retained admission in
`src/application_state/agent_conversation/service.py`, the conversation-page
writer effort in `apps/live_control_server/services/plan_jev_writer.py`,
fresh pending lore completion in
`src/application_state/agent_conversation/native_completion.py`, and
the 60-turn controls in `tests/test_build_source_free_protocol.py`.
Verify one successful stored draft and replay, exact dialogue preservation,
zero source materialization, and rejection of a non-page response and an
unbound citation. Use simulated providers and no database. Independent
exact-head review is required. The running serving release already uses V3
and the lower reasoning setting. Release work must preserve its current
reader dependencies and be qualified against the current serving source.
