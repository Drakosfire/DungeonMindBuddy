# Direct page proposal interaction

MERGED and API/UI-delivered as7ed38faf after exact Bugbotc28b89490.
Ordinary collapse/reveal passed; native Ctrl+End escaped the nested editor.
Correction ACTIVE in HANDOFF-SURFACE-proposal-keyboard.md; direct-editing rendered
acceptance remains open.

Former serial PRIME implementation on codex/surface-direct-proposal, base
3a82e322c645131340b41bdef6ef33b43fc6c839, existing buddy-context-loop checkout.
Operator authoring goal and current dogfood explicitly prioritize direct rendered
editing, movable placement and collapse/reveal over the floating-layout successor.

## One capability and critique
Make the current inert shared page proposal directly editable as rendered content,
without Edit/Preview modes. Keep author review distinct from accepted page bytes.
Allow a native drag handle and keyboard/caret placement; persist the chosen caret
with the mutable review, preserving immutable generated evidence and the original
exact page snapshot. Never map an old proposal through changed page content.
Review-on-page collapses conversation and reveals/focuses the proposal in context.
The initial placement is the captured author caret, not a model location decision;
make this understandable. Prevent a move from changing source, losing local text,
duplicating apply, accepting an outside drag or bypassing terminal/CAS gates.

## Exclusive writes
- This handoff; HANDOFF-BUILD-review-page-reload.md;
  HANDOFF-BUILD-page-proposal-review.md; Docs/Roadmaps/ROADMAP-demo.md.
- apps/live-control-ui/src/surface/SurfacePageProposal.tsx, .css and new .test.tsx.
- apps/live-control-ui/src/buildSurface/BuildPageProposal.tsx and .test.tsx.
- apps/live-control-ui/src/api/buildProposalReviewApi.ts and .test.ts.
- apps/live-control-ui/src/planSurface/components/BuildComposeProposal.tsx and .test.tsx;
  WorldPlanAgentConversation.tsx: explicit review collapse callback only.
- src/application_state/build_proposal/review.py;
  migrations/versions/20261023_0060_build_review_placement.py under application_state.
- tests/test_build_proposal_review.py; UI review fixture producers referencing v1.
No other current PR leases these paths. PRIME owns API8000/UI5202. Preserve user
tabs/drafts and all immutable proposal/provider evidence. One serial PR, reused
checkout. No floating layout code in this slice.

## Contract and gates
Review v2 requires placement_caret and binds it into apply receipts. Migration
converts retained mutable reviews deterministically using original proposal caret;
no legacy execution path. Original proposal fingerprints remain unchanged.
Mounted actual editor proves direct typing preserves page JSON until Keep, local
and saved review reload, drag and accessible placement, one Undo, stale page and
uncertain move/apply recovery. APP tests prove migration, move CAS, terminal guards,
receipt identity, immutable generated evidence and source isolation. Existing
review/auth/shared conversation gates, TypeScript/build, exact cumulative Bugbot,
PRIME merge, protected API/UI delivery. Rendered synthetic rehearsal verifies
collapse/reveal, direct typing, movement, Keep/Discard and reload. User source and
conversation drafts remain untouched. Full goal remains open.

## Predecessor settlement
#1675 merged as3a82e322; UI delivered with API4b851a07. Ordinary retained manual
review returned with chat closed; Keep/Save/reload retained its text once;
subsequent Discard/reload preserved accepted source bytes. Floating conversation
remains the next layout slice after current direct-review dogfood corrections.
