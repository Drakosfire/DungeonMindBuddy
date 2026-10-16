# AGENT: retain unvalidated governed answers for deterministic diagnosis

Status ACTIVE under PRIME's Mirathorn lifecycle goal. Base `362d304413deabf39c12ca52e4c41d33816fa513`;
serial successor to accepted #1221. PRIME implements solo in
`/tmp/prime-recap-mention-boundaries`, branch `codex/agent-unvalidated-answer-capture`.
ARCHITECTURE independently reviews before merge.

## Invariant

Ordinary Build now traverses Graph and opens source passages. Turn
0485a8e8-289a-4e73-84f6-b1cee1f3324a completed four provider responses, two Graph
expansions and one source read, then failed typed/citation_shape. Only a hash and
length of final text remain; do not replay the failed attempt or guess its JSON.

Retain exact returned text at the host boundary immediately before parsing, after
binding to the latest producing provider attempt and frozen context. Use existing
protected APP trace context snapshots, explicitly labeled unvalidated diagnostic
material, with an idempotent producer/receipt item identity. Same capture is a
no-op; changed text or producer cannot overwrite prior evidence. Never include
this material in ordinary history, answer, source/citation admission or completion
authority. No raw output in ordinary logs.

Respect existing aggregate trace byte/event limits; record explicit size/event/
encoding omission reasons, never a prefix labeled complete. Capture failures must
not erase the original parse rejection; persistence/fencing failures cannot enable
completion. No new APP schema, migration, provider route or publication contract.

## Exclusive write set

- This handoff.
- `Docs/Plans/HANDOFF-AGENT-parent-page-reservation.md` (settle #1221/live outcome).
- `apps/live_control_server/services/agent_context_trace_collector.py`
- `apps/live_control_server/services/agent_turn_service.py`
- `tests/test_agent_context_trace_collector.py`
- `tests/test_agent_build_governed_graph.py`

One PR. No open-PR overlap found. No provider calls, retained source/World writes,
DB migration, serving changes or dependency edits during implementation. Owned
preview 5207/8004 stays matched362d3044 on verified APP clone under portable
preview authority a2064010b3013794b1ca5e0f7b3dc6f4b67b1d1e; user5202/stable5876
untouched.

## Owning verification and follow-through

Real APP malformed completion survives fresh-service protected trace readback;
ordinary history/assistant/completion stay absent and original failure survives.
Prove producer/receipt identity, duplicate/changed capture, wrong producer,
aggregate limits/encoding and persistence failure. Existing successful Plan/Build
answers remain unchanged. Inspect cumulative diff, commit/push/open assigned PR,
independent exact-head review. After accepted preview rollout, a future fresh
question may supply diagnostic output; no unchanged replay. Full ordinary-answer,
source-open, restart/historical-source and operator acceptance remain required.

## Review evidence

60 collector/real APP Build/protected trace-consumer tests pass. The malformed
citation payload is retained exactly under producer+frozen-receipt identity in a
fresh service readback; failed turn/history have no answer or completion. Same
capture is idempotent, changed bytes/wrong or earlier producer/mismatched frozen
context reject. Size/event/encoding gaps are explicit without prefixes. APP's
actual JSON serialization and terminal reserve govern byte preflight. Persistence
failure never enables completion and does not mask the original parse failure.
Existing successful Build Graph/source-open/trace readback remains green.
Log `/tmp/answer-draft-regression.log`; Ruff/cumulative diff checks pass. No
provider inference, retained DB/source/World writes or serving changes occurred.
