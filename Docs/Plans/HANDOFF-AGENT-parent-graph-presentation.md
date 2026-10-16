# AGENT: parent-owned Graph presentation and evidence inclusion

Status ACTIVE under PRIME's Mirathorn lifecycle goal. Serial successor to #1218,
accepted merge `5d14ed96b0a7b93b84c58cd21c2cabf9489935e8` (base).
Lane `codex/agent-parent-graph-presentation`, `/tmp/prime-recap-mention-boundaries`.
PRIME implements solo; ARCHITECTURE reviews independently before merge.

## Outcome and contract

The ordinary Build question reached one provider call and Graph neighborhood,
then parent admission rejected worker-paginated bytes. Do not replay that attempt.
Parent currently compares raw packets, then admits all originating event IDs;
worker independently replaces packets with overview/pages. Fix both boundaries.

Parent owns the existing bounded page cache and exact delivered-byte manifest.
Worker forwards parent bytes unchanged and forwards continuation requests to the
parent. Continuations never issue another Graph/source read. Bind cache to exact
tool, original arguments, retrieval session, World and revision. Unknown, expired,
foreign and changed continuations return exact registered denial feedback.

Keep complete validated operation records for audit. Model exposure is separate:
only complete, byte-faithful records present in the final provider envelope can
contribute assertion/relationship/evidence ID subsets. Discovery pointers or
abbreviated overviews cannot stand in for qualified full records. Reassembled
fragments count only when every exact fragment is included in that envelope;
never accumulate exposure from earlier requests. Source/related-context inclusion
requires the complete original result, including qualifications and passage.
Repeat pages are idempotent; mutations and ambiguous payloads fail before inference.
Use existing APP V3 subset validation; no new durable schema or migration.

## Exclusive write set

- This handoff.
- `Docs/Plans/HANDOFF-AGENT-native-reference-limits.md` (settle #1218).
- `apps/live_control_server/services/graph_tool_presentation.py` (new ephemeral manifest).
- `apps/live_control_server/services/agent_turn_service.py`
- `src/graph_memory/hermes_graph_plugin.py`
- `tests/test_graph_tool_presentation.py` (new).
- `tests/test_graph_tool_transport.py`
- `tests/test_agent_build_governed_graph.py`

No open PR overlaps these paths. Session29 gold is independently leased elsewhere.
Existing page presenter is reused without changing its format. No provider calls,
retained DB writes, publication, dependencies or serving changes in implementation.
5207/8004 remains on accepted main and cloned APP under preview handoff pin
`a2064010b3013794b1ca5e0f7b3dc6f4b67b1d1e`; 5202/5876 untouched.

## Owning verification and delivery

Exercise real presenter/broker/provider gate and real APP ledger with synthetic
large qualified records. Prove omitted records absent, fragments incomplete until
all included, source passage completeness, tampered bytes rejected, continuation
scope/request/expiry isolation, repeat/out-of-order pages idempotent and no extra
Graph I/O. Preserve small-result Plan/Build behavior and direct non-governed paging.
Inspect cumulative diff, commit/push one PR, obtain independent exact-head review.
After acceptance roll owned preview, use a fresh ordinary question (no replay),
open passages and obtain DOGFOOD/operator inspection; restart/historical-source
acceptance remains required by the full goal.
