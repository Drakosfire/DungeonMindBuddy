# AGENT — current recap context consumer cutover

Status: ACTIVE under PRIME, 2026-10-12. One current-format end-to-end capability.
Pinned activation SHA `85d157fa5c1709278b1c921e145455f6434e040e094c4c5fa5bbc3b1de1a8a7a`.
Base `62417c6664a3625505bd7775c3c14de224b612dd`; Core `aa344e743c138ca099c023d2c384fee90328d37e`.

Root serializes this cutover before SERVER actionconsultation broker/types/UI
work. The primary dirty UI checkout is untouched; isolated implementation is
`/tmp/buddy-current-recap-consumer-cutover` on `codex/agent-current-recap-context-cutover`.
Core obsolete selector cleanup is excluded. No retained write or runtime activation.

## Current contract

Use current V2 only for related-context broker intent, APP admission/read/inclusion
records, generated source targets and UI passage reads. Retire related V1 routes,
DTOs, cursors, delegation and compatibility-only fixtures. Preserve original human
H1 and H2+Recap Markdown as source material; no normalization, relabel or source edit.

Discover Core V2 under frozen GM World/revision; admit only exact cited/admitted
target/ref provenance and same artifact/revision source tuple. Existing index,
choice, page and execution budgets remain. Every page verifies the full tuple,
selector, original hash, form, bounds and continuation. Context never becomes
literal evidence, `source_read_id`, claim `source_opened` or Graph authority.

Saved prompts, answers, general Graph/claim receipts, authoring revisions, working
copies, Play runs and source identities remain intact. The read-only inventory had
27 turns and zero V1 related-context events; recheck before cutover. Rebuild only
current source-opening views from original pinned receipts/completions. Do not
rerun a provider or retarget history to latest revision. If actual old related
rows appear, stop for a reviewed preservation migration, not a dual decoder.
General Graph/evidence contracts with V1 names remain where they represent real data.

## 4. Exclusive write lease

| Path |
| --- |
| apps/live_control_server/models/agent_turn.py |
| apps/live_control_server/services/agent_turn_service.py |
| apps/live_control_server/services/hermes_graph_interaction_tools.py |
| apps/live_control_server/services/hermes_graph_agent.py |
| src/application_state/agent_conversation/types.py |
| src/application_state/agent_conversation/service.py |
| src/application_state/plan_action_dialogue/graph_consultation.py |
| apps/live-control-ui/src/api/types.ts |
| apps/live-control-ui/src/api/liveApi.ts |
| apps/live-control-ui/src/planSurface/components/WorldPlanAgentConversation.tsx |
| src/graph_memory/retrieval/models.py |
| apps/live_control_server/integrations/dungeonmind/world_graph_reads.py |
| apps/live_control_server/services/world_graph_retrieval.py |
| apps/live_control_server/routes/world_graph_retrieval.py |
| tests/test_agent_turn_service.py |
| tests/test_hermes_graph_agent.py |
| tests/application_state/test_agent_conversation_service.py |
| tests/application_state/test_agent_conversation_postgres.py |
| tests/application_state/test_plan_action_consultation.py |
| tests/test_recap_source_read_continuity.py |
| tests/test_world_graph_retrieval_contract.py |
| apps/live-control-ui/src/planSurface/WorldPlanAgentConversation.worldHistory.test.tsx |
| Docs/Plans/HANDOFF-AGENT-current-recap-context-consumer-cutover.md |
| apps/live-control-ui/src/planSurface/PlanSurfacePage.test.tsx |

## 5. Exclusions

| Path |
| --- |
| corpus/** |
| out/** |
| src/application_state/migrations/** |

No paid provider, retained APP/native/source write, source publication, runtime
restart or saved-Plan mutation. Browser authored/recovery data is not wholesale
cleared. No new capability or extra path without rebrief.

## 7. Owning proof

Mounted Agent route -> actual broker -> APP disposable PostgreSQL -> fake provider
-> saved answer/current source opening; React passage, contiguous page and history
reload proof; negative authority/tuple/byte/pin/cursor cases and context-versus-claim
checks. Reuse the reviewed real reader witness. No helper-only PASS and no repeated
unrelated full suites. Exact commands/results will be recorded when known.

## 9. Review and rollout

- Current V2 wire/event/source-opening pipeline works through mounted boundaries.
- Old related-context protocol machinery is removed; human data and current claim
  evidence are preserved using the current projection.
- Whole selected recap context can be consumed through ordinary Agent within the
  existing budgets, without counterfeit evidence or native semantic admission.
- PRIME reviews cumulative exact head before merge. Retained/runtime cutover and
  operator journey remain separately gated after implementation evidence.

Mutable authority sync set: this handoff only. No merge or independent acceptance
is pre-marked complete.

PRIME amended the lease on 2026-10-12 for the existing PlanSurfacePage fixture
that builds the retired generated plan-context shape. It is a test-only extension;
no additional product contract is introduced.

## Implementation and author evidence

Implementation is ready for PRIME's independent exact-head review; no merge,
retained cutover, runtime activation or operator journey acceptance is claimed.
The authorized design base remains `62417c6664a3625505bd7775c3c14de224b612dd`.
Before publication remote main advanced disjointly to
`f58b5adad711a2ac9f2a54a5d4120db9db09e505` (GE bounded client #1105).
The integration branch is rebased on that ref, preserving its GE pin/extra and
Core `aa344e743c138ca099c023d2c384fee90328d37e`; neither dependency file is changed.

Current related admission/authorization/read/inclusion types and digests are V2
only. All four selector values, the immutable source tuple, selected H1/H2 form,
session heading, marker/body bounds and page/source/section hashes bind current
read receipts and contiguous continuation. Audit contains no passage text or
reusable cursor. General Graph/execution/evidence records retain their meaning.

The owning mounted witness exposed and fixes two previously unexercised seams:
SOURCE dispatch needs the frozen native World ID (the managed World remains the
APP owner); APP provider authorization duplicate checks must compare earlier
provider authorizations rather than an inclusion event with the same attempt ID.
Provider ordering, claim fencing and exact event retry remain enforced.

The authenticated Agent route uses the real parent adapter, current SOURCE reader,
real APP service and a new disposable PostgreSQL database. Synthetic Core
metadata proves exact target/ref to artifact/revision admission; original synthetic
H2 Markdown has a prelude and afterword which stay excluded. Two contiguous pages
consume the entire recap body before a separately authorized fake provider
request. The completed answer has a current related opener, with `source_opened`
false and no evidence source-read IDs from context. Fresh service and a separate
Python process read back the exact saved turn; current history projection does
not replay the provider. Projection in the fresh process honestly marks metadata
unavailable without the synthetic native authority; same-process current target
rebuild is verified against that authority. No real provider inference occurs.

Mounted React tests open evidence and context separately, load a contiguous page,
close/reopen and remount saved history with a fresh initial cursor and no provider
repost. Changed offset/section/form/marker/selector, extra descriptor keys, old
cursors and late pages after close/Plan/World switching fail closed. The current
consultation owner admits the V2 event set and rejects context as source evidence.

Author commands (the existing Python environment is used with the exact Core
source pin first on PYTHONPATH; disposable admin DSN is supplied privately):

```bash
export PYTHONPATH="/tmp/core-recap-context-v2/src:$PWD/src:$PWD"
python -m pytest -q -p no:cacheprovider tests/test_recap_source_read_continuity.py tests/test_world_graph_retrieval_contract.py -k recap_context
python -m pytest -q -p no:cacheprovider tests/test_agent_turn_service.py tests/test_hermes_graph_agent.py tests/application_state/test_agent_conversation_service.py tests/application_state/test_agent_conversation_postgres.py tests/application_state/test_plan_action_consultation.py -k 'related_recap or source_open_target or provider_envelope or provider_authorization or action_attribution or shared_extraction or graph_completion_round_trip or initial_provider_authorization or stale_attempt'
ruff check $(git diff --name-only -- '*.py')
cd apps/live-control-ui
npm run typecheck
npm test -- --run src/planSurface/WorldPlanAgentConversation.worldHistory.test.tsx src/planSurface/PlanSurfacePage.test.tsx
```

Results: 36 source tests and 63 consumer/audit/provider/consultation tests pass,
zero skips in these selections. The source selection has the inherited Pydantic
`CandidateAdmissionBinding.schema` shadow warning. Changed Python files pass
Ruff; TypeScript typecheck passes. React: 196 WorldHistory tests pass; the combined
owning files have 263 passes and two failures. Both failing PlanSurface tests
(`keeps Ask disabled for an unresolved pending write` and `does not send the
prepared revision while its Plan save is still committing`) fail identically at
unmodified `62417c6` in a separate isolated baseline export; their implementation
is outside this cutover. The seven fixture-induced failures are resolved by the
coordinator-authorized V2 fixture update. No unrelated save behavior is changed.
Cumulative diff check and the exact 24-path lease check pass.

The private read-only APP gate recheck at 2026-10-12T22:55:32Z found five
conversations, 27 turns (22 completed, four failed, one interrupted), zero related
V1 audit events, six work objects, 18 revisions, five working copies, five Play
runs, 94 source artifacts/revisions and 229 ingestion runs. None is written by
this implementation. The accepted original C1S16 reader witness is reused from
`/tmp/c1-session16-recap-context-v2-reader-witness.json`; it proves original legacy
Markdown reader bytes/ranges, not this new complete operator journey.

Rollout remains PRIME-owned: preserve private APP/browser narrative and recovery
backup/inventory, require zero old related audit rows again, deploy the current
reader and consumer together, regenerate pinned views without provider replay,
and discard only derived cursors. Do not clear localStorage or rewrite saved
turns, claims, source identities or bytes. A real old related row is a separately
reviewed preservation-migration gate. Core obsolete metadata cleanup remains
outside this lease. No retained/native write, admission/publication, Plan edit,
shared-runtime action or primary-checkout mutation was performed.
