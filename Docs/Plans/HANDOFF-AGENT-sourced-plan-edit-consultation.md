# AGENT — sourced saved Plan edit consultation

Status: ACTIVE under PRIME, 2026-10-12. Pinned activation:
`/tmp/HANDOFF-SERVER-sourced-plan-edit-consultation-activation.json`, SHA-256
`3339a0fbe1596ca52fc6bf52f40da71c107d6329f139506cd9e6dce7293eed2a`.
Design: `/tmp/continuity-edit-contract-decision.json`, SHA-256
`0751fd8e159f35e94528c90228398167b98867873611a39593cee52141b756fa`.
Base: fetched Buddy main `1fb127f8a0a2f0456eb385186e54cecff6f58b33`
after accepted #1106. Branch: `codex/server-sourced-plan-edit-consultation`,
isolated checkout `/tmp/buddy-sourced-plan-edit-consultation`. APP #1101
consultation persistence is merged. The #1104 publication-readback lease is
settled and released. RAKE's #1106 current-context shared broker/API/UI lease
was transferred to SERVER. Open Buddy PRs #1014, #869, #844, #826, #798,
#765–763 have no current lease on this path set. The primary Buddy checkout
has unrelated uncommitted UI work and is read-only for this slice.

## One capability

For a saved Plan in an initialized managed World, an ordinary
`replace_selection` edit uses the existing Agent Harness and parent-brokered
Graph/source/context tools within the same request. Freeze server-resolved
World binding, Graph pin, Plan basis, draft, selection, input and consultation
policy in the existing APP action ledger before provider authorization. The
outcome is a cited conversational clarification with no Apply, or an inert,
reviewable proposal. A short reply linked to a clarification creates a new
action, revalidates its target and facts, and may produce a proposal. Failed
required authority/read is `context_unavailable`, distinct from verified
empty or irrelevant knowledge. A Plan retcon never changes published World
facts.

This first adopter preserves verified blank-World authoring and existing caret
and Playable-body edit behavior. Keep saved APP Ask/action history and current
V2 source-context contracts. Do not fabricate an Ask Turn, add a second
broker/store, route other surfaces, widen source authority, call a live
provider, mutate retained data/schema, restart runtime or use operator corpus.
The existing generated v1/v2 proposal DTOs are retained only for their
existing unaffected target paths, without new compatibility machinery.

## Exact exclusive write set

- `Docs/Plans/HANDOFF-AGENT-sourced-plan-edit-consultation.md`
- `apps/live_control_server/services/plan_document_edit_proposal.py`
- `apps/live_control_server/services/plan_action_consultation.py`
- `apps/live_control_server/services/agent_turn_service.py`
- `apps/live_control_server/models/plan_document_edit_proposal.py`
- `apps/live_control_server/routes/live.py`
- `tests/test_world_plan_edit_proposal.py`
- `tests/test_agent_turn_service.py`
- `apps/live-control-ui/src/api/types.ts`
- `apps/live-control-ui/src/api/liveApi.ts`
- `apps/live-control-ui/src/planSurface/components/WorldPlanAgentConversation.tsx`
- `apps/live-control-ui/src/planSurface/WorldPlanAgentReviewedEdit.integration.test.tsx`
- `apps/live-control-ui/src/planSurface/WorldPlanAgentConversation.worldHistory.test.tsx`

An essential extra path or second capability requires rebriefing PRIME before
editing. APP types/repository/migrations, Core, provider SDK/model policy,
other UI surfaces and source readers are read-only dependencies.

## Acceptance witness

Synthetic saved initialized-World action and mounted UI prove fresh and
discuss-to-edit retrieval, exact typed Graph/source/context provenance,
ambiguous authored fact → natural clarification/no Apply, linked reply →
freshly grounded inert proposal → exact Before/After Apply/Save/reload. Test
wrong World, stale work/draft/target, foreign or superseded clarification,
duplicate/unknown outcomes, source failure versus verified empty/no relevant
fact, and blank World/caret/Playable preservation. Use fake provider only and
disposable APP PostgreSQL. A separately labelled synthetic half-elf continuity
fixture may prove mechanics; real corpus semantic acceptance is not claimed.
Run owning focused tests, relevant lint/type gates, inspect cumulative exact
base→head diff, commit/push/open PR, then return to PRIME for independent review.

## Implementation evidence for PRIME review

Implementation commit: `2199504490feefa56af59528e0cfe506cb517aab`. GitHub's
`main` remains `1fb127f8a0a2f0456eb385186e54cecff6f58b33` at handback;
the separate local Buddy checkout's `origin/main` points at unpublished local
work and is not the GitHub PR base. Current open GitHub PRs #1014, #869,
#844, #826, #798, and #763–765 retain no active collision on this lease.

The mounted synthetic saved-selection proof uses the real selected-World
Graph resolver, parent Harness authorization, parent source broker callback,
and disposable APP PostgreSQL. The first action returns a cited clarification
with an openable source target and no proposal or Plan write. A short linked
reply creates a new action with a newly resolved Graph pin and source read,
then returns an inert cited proposal. The test confirms no automatic write;
an explicit Markdown prepare/commit advances the saved Plan, and a snapshot
reopen observes the new digest. The mounted UI test shows the clarification
without Apply, opens evidence, reloads, links a reply, renders Before/After,
applies only to the editor draft, and reloads without an executable review.
The actual page Save control lives outside the conversation component; the
HTTP prepare/commit witness covers its owning persistence boundary. Source
text and provider replies in this witness are synthetic, so this does not
claim real-corpus semantic acceptance.

Verification on the implementation commit's exact files:

- `tests/test_world_plan_edit_proposal.py` and `tests/test_agent_turn_service.py`:
  145 passed in disposable PostgreSQL, including the positive sourced path,
  error/empty paths, existing Ask broker cases, and preserved legacy targets.
- `WorldPlanAgentConversation.worldHistory.test.tsx`: 197 passed.
- UI `npm run typecheck -- --pretty false` and `npm run build`: passed.
- Ruff on all changed Python source and owning tests: passed.
- `git diff --check`: passed. Cumulative implementation diff contains only
  this lease's source and test paths; the handoff is the eleventh path.

The older `WorldPlanAgentReviewedEdit.integration.test.tsx` fixture has 17/18
failures on this base because its radio-control and copy assumptions predate
accepted #1106. This slice did not rewrite those unrelated historical cases.
PRIME owns independent exact-head review. Do not merge on this handoff alone.
