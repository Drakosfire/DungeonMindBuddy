# AGENT: preserve the author-selected reviewed action

Status: DESIGN REVIEW. PRIME/Buddy stewardship under the active connected-authoring goal. One focused design PR from base0b05bf58152e7f313d752d240be20a97ebddd0d7 on codex/reviewed-action-binding-design in the existing buddy-context-loop checkout. Exclusive design write lease: this file only. No runtime lease, implementation, provider requests, retained data edits or service changes in this PR. Open authoring lanes inspected; no competing implementation PR. Hosted, ingestion and combat lanes remain separate. Independent Bugbot reviews the exact design head before implementation activation.

## Invariant and evidence

An author selecting Discuss or Prepare an insertion in a saved reviewed plan has already chosen the supported action. Continue must carry that action through admission, evidence acquisition and the existing writer/tool boundary. It must not become a request for the controller to choose a different action. Only the selected step executes; no automatic following step, source Save, relationship publication or image generation is authorized.

Current code stores Step.kind and freezes a dispatched step. continue_step describes the kind in message prose. Dispatch, SurfaceConversationRequest and AgentTurnRequest transport identities/message without a reviewed-action reference. BuildGraphIntentV1 does not bind the step. Jev selects among available operations again. work_plan._result detects a wrong result afterward as needs_attention. Existing test_prepare_insertion_requires_real_proposal_not_discussion explicitly exercises that detection; all nine current reviewed-plan boundary tests pass. Thus detection is delivered, enforcement is missing. No claim is made that this audit reproduced an actual continued insertion failure.

This correction does not solve free-form utterance classification. Preserve the ordinary writing-routing regression and the rejected instruction-only experiment as separate acceptance requirements. Do not replace that broad requirement with a successful explicit-step demonstration.

## Contract: retained step reference, not caller operation authority

Add a closed optional reviewed-step reference to the existing Build request. Minimum selectors: conversation_id, source_turn_id and command_id. APP resolves step_id, kind and the exact persisted Dispatch; the client must not supply an authoritative operation string. The continuation response supplies the reference alongside its existing plan/dispatch. Surface queue, pending-turn persistence and retry retain it unchanged.

Before durable turn admission or provider authorization, resolve the reference through the existing work_plan owner using exact World/conversation/source selectors. Verify:

- Source is the retained completed Build turn, its answer hash still matches the saved plan, and the plan names the requested document.
- Command belongs to the retained dispatch and its selected immutable step; the source conversation is the submitted draft/capability conversation.
- Client thread ID, client turn ID and message exactly match the dispatch. A valid UUID alone is insufficient.
- The request is Build with requested World Graph and current page/draft context. Prepare an insertion requires the existing exact captured write capability. Discuss may use captured context without write authority.
- New execution requires the existing current active-conversation/page fences. A completed replay may resolve the immutable retained reference in an archived conversation; it must not redispatch or require the conversation to become active again.

Return a closed resolved binding containing selectors, step identity/kind, source-answer hash and a canonical digest of the immutable step+dispatch. Include the binding in normalized submitted intent and its idempotency fingerprint. Refuse altered or unknown selectors, scope, IDs, message or digest before provider dispatch. A plan revision increment caused by another step must not invalidate an already immutable dispatch. New executions still capture the latest eligible page revision; do not bind them to the page revision of the old plan-producing turn.

Do not parse message labels or local queue IDs as authority. A missing reference on an ordinary request remains ordinary unstructured intent, not a hidden fallback executor. Existing completed histories remain readable and replayable. Never reinterpret a previously admitted unbound turn as author-bound after deployment. Existing pending dispatches may obtain the reference from their current Continue response; do not manufacture a new command/turn to hide unresolved execution.

## Contract: truthful action authority in APP execution

Introduce a distinct closed author-reviewed action-selection ledger event. Bind its operation, broker operation ID, argument digest and capability digest to the resolved submitted intent. Allowed mapping is exactly Discuss -> answer_from_sources and Prepare an insertion -> propose_build_insertion. No other action is offered by this workflow.

APP append and retained-turn validation must prove the mapping and binding, reject duplicate/mixed author and model selection events, and preserve existing proposal-origin/completion checks. The author event has no invented controller call ID, envelope, probability or token usage. Current BuildJevActionSelectionV1 remains the truthful actual model-selection event for ordinary turns.

The driver uses the admitted binding to select the operation. It does not ask an operation question for a bound step. Keep actual model decisions for related-page read/skip, rules queries where applicable, acquisition, support and writer synthesis. Those auxiliary decisions retain real SDK envelopes and receipts; they do not gain permission to override the selected action. When no auxiliary selection question exists, skip that call rather than send a fake single-option classification. Preserve provider-role, acquisition and evidence-selection admission and existing writer/tool guards.

Insertion continues through the existing reversible proposal owner and explicit page Save. Missing/stale placement capability yields a specific obstacle with the original reviewed dispatch retained; discussion is not a fallback. A generation/acquisition failure remains a real failure, not an empty proposal or automatic retry. A discussion step cannot produce an insertion completion. No second page/Graph publisher is added.

## Durability and delivery

Add an APP migration only as required for the new retained intent/event vocabulary; no rewriting of histories or reviewed plans. Downgrade must refuse retained new-contract rows before an older runtime can misread them. Validate foreign IDs, stale/current state, altered message, pointer changes, interrupted dispatch, same-command replay, concurrent Continue and completed archived replay at the owning boundary. Do not claim compatible old execution as a solution to the new contract.

Protected paired API/UI delivery requires current remote re-anchor, exact review/check head, current runtime lease, no owned in-flight turns, retained-data fingerprints and health/state checks. Preserve all sources, conversations, plans, drafts, versions and native state. No new port, checkout, dependency environment or runtime source export. Use existing candidate delivery tooling and current checkpoints, never a revision copied from this design as runtime authority.

## Verification and acceptance

1. Disposable PostgreSQL plus real API admission: exact retained reference reaches durable intent; each mutated selector/identity/message/scope is rejected before provider calls. Replay cannot shed or swap the binding. Unrelated plan edits do not invalidate the immutable dispatch.
2. APP execution: real author event and exact capability/arguments; wrong operation, forged/mismatched binding, dual selection, incorrect proposal origin or completion fail. New vocabulary downgrade refusal, old retained histories readable, ordinary model-selected actions unchanged.
3. Actual host/SDK: no operation question for a bound step; auxiliary model questions and evidence acquisition remain actual prepared requests. Ordinary requests retain their existing model path. A valid acquisition answer cannot change the bound action. No synthetic model-selection event or unobserved usage.
4. Mounted UI: continuation response reference -> queue -> exact pending request, reload/retry retention, newer composer protection, single logical turn. Preserve selected/deferred state and only dispatch the chosen step.
5. Ordinary synthetic dogfood: reviewed insertion -> real content -> intended page placement -> direct edit -> one Save -> reload; discussion-only continuation produces no proposal. Repeat/reload does not duplicate a turn or execute the next step. Exercise missing/stale capability and retained request recovery. Then return to the original free-form routing regression and actual connected-authoring acceptance; none of these tests establishes full goal completion.

## Implementation activation and expected write set

Serial successor, one implementation PR after this design is reviewed and settled. Activate a pinned bounded handoff before edits; amend the lease if inspection identifies another required boundary. Expected owner paths: work_plan.py; agent_turn request and APP types/intent/event service validation; build_jev_harness/driver and existing build_authoring origin checks; additive migration; UI continuation API/types, Surface conversation queue and WorldPlanAgentConversation transport; relevant trace projection only for truthful author-event display; focused boundary/SDK/UI tests; this handoff and the existing roadmap/predecessor handoff settlement. No GenerationEngine, native Graph or corpus ownership change is intended. Extra capabilities remain separate scope.

Settle the verified #1756 light-activity proof with the implementation slice: ordinary deployed light/technical/Copy inspection passed, including retention of all58 observations. Do not reopen that capability or create a status-only PR. This design does not claim implementation, runtime adoption or operator acceptance.
