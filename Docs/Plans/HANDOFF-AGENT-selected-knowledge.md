# AGENT: selection-aware ordinary conversation

Status: ACTIVE under PRIME's authorized selected-source/knowledge interaction scope.
Base: `9abb6c5f1903a10f784c5563081052472a3dc19e`.
Lane: `codex/agent-selected-knowledge`, `/tmp/prime-recap-mention-boundaries`.
Topology: serial successor; PRIME implementation, ARCHITECTURE independent review.

## Contract

Ordinary Ingest conversation submits exact selection identities/preconditions,
not a trusted rendered context. Buddy resolves through merged #1211, binds the
selector into durable submitted intent and context identity into turn provenance,
then supplies a harness-neutral selected-knowledge packet. The Harness renders
saved source, candidate-only records and attributed annotations separately from
admitted World facts. Selection never retargets Graph tools. Keep read-only
capability policy; prose suggestions are not durable proposals or applied edits.
Reject stale/foreign selection, changed retry semantics and oversized context
before model dispatch. Completed-turn replay remains historical. No provider or
retained World mutation in implementation/tests. Later typed proposal/apply remains
separate. Preserve existing authored conversation/history and source identity.

## Exclusive write set

- This handoff.
- `Docs/Plans/HANDOFF-INGEST-selection-context.md` (settle #1211).
- `src/graph_memory/ingestion/selection_context.py` (shared selection input types).
- `apps/live_control_server/models/ingest_selection_context.py` (API type export).
- `apps/live_control_server/models/agent_turn.py`
- `src/application_state/agent_conversation/types.py`
- `apps/live_control_server/services/agent_runtime.py`
- `apps/live_control_server/services/agent_turn_service.py`
- `apps/live_control_server/services/hermes_agent_runtime.py`
- `apps/live_control_server/routes/agent.py`
- `tests/test_agent_selected_knowledge_context.py`

DOGFOOD UI and completed gold paths are disjoint. Verify actual request→resolver→
durable intent/provenance→runtime→Harness context, retry selection binding,
annotation qualification and unchanged Graph policy/scope. API/port tests do not
claim rendered UX or native Graph write support. No changes to serving services,
credentials, dependencies, DB schema, parent candidate or native World.
