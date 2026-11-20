# AGENT: selection-aware ordinary conversation

Status: SETTLED. Merged #1213 as `60c35904d1ef9658f3f00922d9394508b981e973` after ARCHITECTURE independent PASS at `c3f0068872e07dd742404770fe60321876732666` (15 owning tests independently passed; 202 combined author tests). Backend implementation lease ended; browser adoption, semantic runtime evidence and proposal/apply remain outstanding.
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

## Submitted contract and evidence

`POST /api/live/agent/turn` accepts optional `selected_knowledge` with `runId`,
`contextRequest` (the #1211 selector/preconditions), and `expectedContextSha256`.
This first consumer requires the matching managed-World Ingest surface and no
primary work. Authentication supplies the annotation subject. The client never
supplies authoritative context records. Existing unselected intent fingerprints
remain byte-identical. Historical provenance uses the existing generic reference
revision string, not Content-only object/work revision fields.

Author evidence: 15 new tests exercise actual frozen source/candidate resolution,
real disposable APP PostgreSQL acceptance/completion/fresh-service replay,
changed intent, stale source/revision/digest, attributed annotations, authenticated
route subject, serialized/deserialized Harness transport, unchanged Graph tools,
and pre-dispatch payload bounds. Combined selection/runtime/turn suites pass 202
tests with two unchanged-main Plan fake-contract failures explicitly excluded;
both reproduce against source archived from exact `9abb6c5f1903a10f784c5563081052472a3dc19e`.
Ruff and cumulative diff check pass. No actual provider call, serving change,
retained corpus mutation or World publication. Rendered adoption and typed
proposal/apply remain outstanding; this proves context delivery, not model quality.

Authenticated route regression: 53 passed; four pre-existing Graph-policy tests
fail on unchanged main as well (sufficiency expectation, two V2/V3 execution-policy
digest assertions, and a V2 scope schema fixture). This slice does not alter that
Graph policy or source scope. Unselected turns do not consume an annotation subject.
