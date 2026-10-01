# HANDOFF — DEMO: World-only reviewed Agent-to-Plan Apply

**Status:** ACTIVE — PRIME activated the bounded implementation lease after
reviewing and merging this handoff; a separate post-merge runtime lease remains
required.

**Steward:** DEMO task `01a0efc8-f3a8-7be2-a556-33eb338338e8`

**Authority:** [STEWARDS-HANDOFF-demo.md](STEWARDS-HANDOFF-demo.md), merged
World Plan conversation contract in
[HANDOFF-DEMO-plan-agent-conversation.md](HANDOFF-DEMO-plan-agent-conversation.md),
accepted reviewed-edit behavior in
[HANDOFF-DEMO-plan-agent-reviewed-edit-v1.md](HANDOFF-DEMO-plan-agent-reviewed-edit-v1.md),
ARCHITECTURE's World-only Apply ruling, RAKE DUTY's J2 race audit, PRIME's
explicit activation, and PRIME's disposition that the current policy-selected
`gpt-6-luna` witness passes the #812 Responses gate.

**Implementation branch/base:** `codex/demo-world-plan-agent-apply-impl`, based
on fresh `origin/main@5b7e1e4543c94708e11687feb60093d98d6db93f` after the
handoff PR #825 merged. Isolated checkout:
`/home/drakosfire/.codex/worktrees/demo-world-plan-trace-inspector/DungeonMindBuddy`.
The implementation uses fixture-backed tests only: no product database,
service, model/provider call, port, or corpus is leased or used.

**Topology:** serial within DEMO: one J2 implementation PR on the active branch;
do not merge it. The next Plan slice stays blocked until this implementation
merges and its separate runtime witness completes.

**Runtime/state ownership:** No live product service, provider, product
database, demo World, or corpus is used by this implementation. The real-route
code test used only a disposable PostgreSQL fixture container on localhost port
54329; it was stopped after the tests. No app runtime port or external product
state is leased. The eventual post-merge product witness requires a fresh,
explicit PRIME runtime lease. Do not reuse the still-running database pair from
the 2026-10-01 #812 witness; it remains under PRIME's runtime ownership.

## 1. Broken transition and one capability

On the saved managed-World Plan route, ordinary Ask correctly remains
metadata-only: it does not read Plan prose and cannot edit the mounted draft.
The route currently has no World-only reviewed Apply path. The legacy reviewed
editor bridge is campaign/session-shaped and requires `session >= 1`; a World
ID must not be aliased as a campaign or given a fabricated session.

Deliver one capability: a user can explicitly ask the Agent to compose or
revise an edit for the exact mounted World Plan draft, inspect the proposed
change, apply it to that same mounted editor, and then use the existing Plan
Save path. The Agent proposes; the user reviews and applies; existing Plan
Save remains the only persistence authority.

This slice does not close full DEMO-J2, add a general document-writing API, or
change ordinary Ask, campaign/session editing, Plan storage, Agent runtime,
graph behavior, or provider policy.

## 2. Contract and failure cases

1. Add a distinct World-only typed proposal request/response and route. The
   request carries exact `world_id`, saved `document_id`, committed
   `base_revision`, committed `base_content_sha256`, the explicitly selected
   mounted `draft_markdown` and its digest, target kind/selection, user
   instruction, and bounded existing Plan action context. It has no
   campaign/session authority fields. Preserve the existing legacy request,
   response, route, and session validation unchanged.
2. Server admission verifies the managed World and the exact active
   World-owned Plan, then compares the committed revision and digest and
   validates the submitted draft digest and target shape. Reject a missing,
   foreign, wrong-kind, inactive, stale, malformed, or digest-mismatched
   request before constructing or calling the generation client. Never infer
   World ownership from campaign-ID equality.
3. Generation uses the configured structured-generation role and returns an
   inert, validated Markdown proposal. The server may use the submitted
   mounted draft, explicit selection, instruction, and bounded action context
   as untrusted model input. It must not retrieve or append committed Plan
   Markdown to the prompt. Do not add a second provider, model policy, retry
   path, generic Agent endpoint, storage writer, or graph request.
4. The UI exposes a separate Compose/Revise-in-Plan action with clear
   disclosure that the selected current draft, selection, and instruction are
   sent to the configured model. Ordinary Ask stays metadata-only and
   unchanged. Show a before/after review with explicit Discard and Apply
   controls. Apply changes only the same mounted editor draft; it does not
   call a server write or mark the document saved. The existing Save and
   reload flow persists the resulting registered Markdown components.
5. Keep proposal payload, replacement Markdown, editor-application state, and
   save receipts in the existing Plan-owned action representation. Reuse its
   safe `planEdit` shape; do not create a second transcript store, import the
   proposal payload as a canonical World conversation turn, or modify APP-STATE
   conversation schema/adoption. A future durable proposal/action adoption
   contract remains with Plan/Content.
6. Fence every asynchronous result to the same verified World, document,
   surface, current Agent thread, mounted editor, base revision, draft
   generation/content, save state, and selection. Invalidate/hide Review as
   soon as any captured editor binding changes. After any awaited capture,
   hashing, or proposal work, recheck the complete fence at the synchronous
   editor transaction boundary. The final guard must call an authoritative
   live getter for current Agent thread and scope, require the exact active
   thread and World Plan namespace, and fail closed on null or foreign scope.
   No await may occur between that final getter/check and dispatching the
   editor transaction. Never fall back to a captured thread or scope. If the
   bridge cannot provide that ordering within the leased paths, stop and return
   the exact path/API need to PRIME before editing outside the lease.
7. Do not accept a late proposal after the component unmounts. Do not use a
   pending-thread fallback when active scope is null or foreign. A stale World,
   document, revision, draft, save, selection, thread, scope, or mounted-editor
   result leaves both the editor draft and persisted document unchanged.

The observed RAKE audit found that the legacy bridge checks World/document/
revision/body/selection but the caller checks the active thread before awaiting
Apply and only after mutation; a thread switch during that await can apply the
old proposal. Review can also remain stale after editor changes, and a pending
thread fallback can accept completion after scope becomes null/foreign. Those
baseline gaps motivate the active slice: its World bridge requires the live
thread/scope getter immediately before editor mutation, invalidates Review on
binding changes, and drops late responses after unmount. Focused World route
and mounted-editor regressions are required before PR handback.

## 3. Active exclusive implementation path lease

This is the exact ACTIVE implementation write lease PRIME approved. No other
path is authorized by this handoff. If the contract needs another path, return
the exact need to PRIME before editing it.

1. `Docs/Plans/HANDOFF-DEMO-world-plan-agent-apply-v1.md` — activation,
   bounded acceptance evidence, and truthful completion state.
2. `Docs/Plans/HANDOFF-DEMO-plan-agent-responses-mode.md` — record the
   adjudicated #812 current-policy live PASS without changing its implementation
   scope or inventing a historical `gpt-5.3-codex` live requirement.
3. `Docs/Roadmaps/ROADMAP-demo.md` — record #812 PASS, #824 merge and trace
   inspection, keep the separate bootstrap 503 and malformed-looking document
   identifier observation accurately scoped, and record this J2 transition's
   actual result without pre-marking it complete.
4. `apps/live_control_server/models/plan_document_edit_proposal.py` — add
   distinct World-only request/response types; keep legacy types intact.
5. `apps/live_control_server/routes/live.py` — add the separately typed
   World-only proposal endpoint; leave existing routes unchanged.
6. `apps/live_control_server/services/plan_document_edit_proposal.py` — add
   the exact World-owned admission and inert generation path without a writer
   or committed-body prompt access.
7. `tests/test_world_plan_edit_proposal.py` — new World-only route/service
   admission and no-provider-on-reject witnesses.
8. `apps/live-control-ui/src/api/types.ts` — add World-only API types.
9. `apps/live-control-ui/src/api/liveApi.ts` — add the typed World-only
   endpoint client.
10. `apps/live-control-ui/src/api/liveApi.test.ts` — cover the new route and
    preserve legacy transport behavior.
11. `apps/live-control-ui/src/planSurface/agentEdit/planAgentEditProposal.ts`
    — adapt the mounted-editor bridge for a World-only identity without
    relaxing the legacy campaign/session checks.
12. `apps/live-control-ui/src/planSurface/agentEdit/planAgentEditProposal.test.ts`
    — prove exact World-only request identity, response admission, and stale
    target rejection.
13. `apps/live-control-ui/src/planSurface/PlanSurfacePage.tsx` — connect only
    the managed-World Plan editor and conversation to the bridge.
14. `apps/live-control-ui/src/planSurface/components/WorldPlanAgentConversation.tsx`
    — add explicit compose/revise, review, apply, and stale-result behavior.
15. `apps/live-control-ui/src/planSurface/components/WorldPlanAgentConversation.css`
    — style the review controls within the existing Plan Agent surface.
16. `apps/live-control-ui/src/planSurface/PlanSurfacePage.test.tsx` — mount
    the World Plan route and prove unchanged metadata-only Ask plus explicit
    compose/review/apply affordances.
17. `apps/live-control-ui/src/planSurface/WorldPlanAgentReviewedEdit.integration.test.tsx`
    — new route-to-mounted-editor regression matrix, including asynchronous
    races and ordinary Save/reload.

The current J3 World-binding lane owns World-container registry/routes,
MIND-provisioning adapter, dependency pin, and its tests; those paths do not
overlap this proposed set. The merged #822 APP-STATE storage lease owns its
conversation migration/service/tests and authority docs; those paths also do
not overlap. Its successor backend-adoption work does not authorize changes to
canonical transcript contracts here. PRIME must recheck all active leases and
the exact open-PR changed-path census before activation. No generic Agent
turn/history contract, APP-STATE code/schema, World registry, Content writer,
Plan save route, campaign/session flow, shared runtime, Play, Graph, or other
surface is leased.

## 4. Owning-boundary acceptance witness

Use the real World-owned Plan service/route boundary and mounted
`PlanSurfacePage` World route. Mock only the structured model generation and
network/UI dependencies required by the fixture. Do not use a live product
database or provider for this code-test witness.

1. Create or load an exact managed World and active World-owned Plan. A valid
World-only request contains no session/campaign alias and returns an inert
proposal bound to the exact World, document, committed revision/digest,
submitted draft digest, target kind, and selection digest. Confirm the existing
campaign/session request still follows its original contract.
2. At the server boundary, prove foreign/missing World, foreign/wrong-kind or
inactive document, stale revision, stale committed digest, bad draft digest,
invalid target, and malformed identity fail before model generation. Supply a
committed body that differs from the explicit request draft and assert the
provider prompt contains only the explicit request context and never the
committed body fetched for authority validation.
3. On the mounted World Plan route, ordinary Ask stays metadata-only with
`graph_request={"mode":"none"}` and sends no document prose. Compose/revise
is a separate explicit action with the required disclosure. A selected draft
proposal can be reviewed, discarded, applied to the current mounted editor,
saved through the existing writer, reloaded, and revised in a second
configured-policy proposal; prove prose and existing registered Markdown
components survive ordinary Save/reload.
4. Exercise stale World, Plan, revision, draft generation/content, save state,
selection, thread, null/foreign active scope, and editor-unmount cases. Include
a deferred Apply with a thread switch during its awaited preparation and a
deferred model response completing after unmount. Every stale case must leave
the mounted draft and saved record unchanged, render no actionable stale
Review, and make no Plan write.
5. Run focused server/service, route, proposal bridge, mounted World Plan,
history-safety, and API tests; run relevant existing campaign/session reviewed
edit regressions; run scoped UI typecheck, Python lint, and `git diff --check`.
Review the exact cumulative base-to-head diff and every leased path. Report the
inherited `ThreatPublicationPanel.tsx:553` JSX namespace typecheck diagnostic
and any unrelated legacy fixture failures without expanding this lease.

After the implementation PR merges, obtain a fresh PRIME runtime lease and
rehearse the ordinary World Plan flow on an isolated synthetic World: make at
least two real configured-policy proposals on the same Plan, review/apply,
Save/reload, revise, and verify the saved Plan and conversation/action history
remain correctly scoped. Capture actual model/transport/usage/cost evidence
when available; label trace estimates as estimates and unavailable receipts as
unknown. Keep any World graph projection bootstrap failure separate from the
Plan Agent turn. This is bounded J2 evidence, not full connected DEMO or
operator acceptance.

## 5. Backward-looking predecessor synchronization

The implementation PR must record only established predecessor facts:

- PR #812 merged; PRIME adjudicated its post-merge live Responses gate PASS for
  the current policy-selected `gpt-6-luna` call with observed
  `api_mode=codex_responses`. The saved trace has status `ok`, one model call,
  zero graph tools, usage 569 input / 52 output / 621 total (43 reasoning), and
  trace-estimated USD 0.0000829. Opening the saved trace made no Agent request.
  The historical `gpt-5.3-codex` offline probe is not a live-call requirement.
- PR #824 merged at `02350b1aff560033f53dbe86de8f5fc5f44b992b` and added the
  opt-in, default-hidden per-turn trace inspector. The saved turn showed the
  same successful Responses request. The page-bootstrap World Graph projection
  separately returned 503 for a missing adoption receipt and was not part of
  the Plan Agent call.
- The observed Plan inventory also returned a malformed-looking document ID
  that the direct ID route rejects, while inventory selection and saved-turn
  trace loading succeeded. Keep this as a separate navigation/data-integrity
  rake only; it neither proves nor negates J2.

Do not claim usage cost is a billing receipt, use the projection 503 as a Plan
turn failure, pre-mark this implementation complete, invent a merge SHA or
review count, or claim full J2/operator acceptance before those gates pass.

## Current implementation checkpoint

The implementation worktree is based on the recorded fresh `origin/main` and
stays within the 17-path lease. Focused backend admission and real-route tests
passed `22/22`; the real World-owned Plan route witness used a disposable
PostgreSQL fixture on localhost port 54329, and its test container was stopped
afterward. No product database, live provider, or app runtime was used.

Focused UI/API verification passed `159/159` across the World Plan page, API,
proposal bridge, and new mounted-route integration suites. The integration
suite covers Compose → Review → Apply → existing Save → reload, late proposal
completion after unmount, and a deferred Apply interrupted by an Agent-thread
switch. Bridge regressions also cover stale World/document/revision/digest/
draft/selection/save state and null/foreign scope/thread. Scoped Ruff and
`git diff --check` passed.

The scoped UI typecheck reports only the inherited
`ThreatPublicationPanel.tsx:553` `JSX` namespace diagnostic. The normal build
also cannot write its TypeScript build-info file under the read-only dependency
mount; verification redirected that file to `/tmp` and confirmed there are no
additional production-source diagnostics. The live configured-policy proposal
rehearsal remains pending the separate PRIME runtime lease after merge.

## 6. Completion boundary

PRIME already activated the exact §3 implementation lease against fresh
`origin/main@5b7e1e4543c94708e11687feb60093d98d6db93f` on the isolated branch
and checkout recorded above. Continue implementation through focused tests,
cumulative diff review, commit, push, and the assigned PR handback. Do not
merge. The implementation has no live runtime lease; after merge, request a
fresh PRIME runtime lease for the product witness. If any required path or
contract exceeds §3, stop before editing it and return the exact gap to PRIME.

This implementation completes only when the approved World-only Apply
capability passes its owning-boundary tests, cumulative diff review,
implementation PR review/merge, and its separately leased live witness. It does not close the
remaining J2 multi-turn acceptance, full demo journey, or human product
acceptance by itself.
