# Plan Cards thumbnail deck

Status: ACTIVE, 2026-10-19. Operator explicitly authorizes implementation,
independent review, merge and delivery on 5202. Serial lane owned by PRIME in the
existing buddy-context-loop checkout, branch codex/plan-cards-thumbnail-deck,
base dba1def41. No overlapping Cards implementation PR.

Invariant: a vertical thumbnail deck selects existing Plan scenes through the
existing Page navigation callback. Plan selection stays in the surface navbar;
Cards no longer duplicates scene selection in a second navbar dropdown. Document
retains its existing scene navigation. One scene is one deck entry in this slice;
no new card/scene storage, scene structure edits or direct card editing.

Thumbnails are inert previews of current authored draft content (title, text,
media when present), not summaries or independent writers. The full selected
scene remains authoritative and available. Show selected state and Beat context;
keep the deck independently vertically scrollable on desktop with a collapsible
full-width list on narrow screens. Keep the deck mounted across Document/Cards
switches to retain its scroll/collapse state. Existing editor, save controller,
caret/undo, draft media and document-scoped scene cursor remain owners. No Run,
notes, backend, Graph or schema changes.

Exclusive paths: this handoff; PlanSurfacePage.tsx;
components/PlanCardDeck.tsx, PlanCardDeck.css and dedicated tests;
WorldPlanCardProjection.integration.test.tsx for current mounted acceptance.
The existing projection model is consumed, not changed. No dependency/lockfile.

Verify deck selection across Beats, selected-state and current-draft previews,
Document canonical return and Cards retained focus; mounted draft/media/caret/
undo/save/reopen regressions; identity replacement/stale callbacks, no writes on
browsing. Independent exact-head Architecture review and desktop/narrow keyboard,
scroll, media and real-host acceptance. UI-only 5202 guarded atomic lease:
buddy-main-af6779d/ui-dist, prior index
0142ebf13e2ef03f60af7e880ed06e20ecd41736cdef6c4571ae76f80d854440.
Keep old assets/index; retain real Plan, Run, notes/reflections and media exactly.
No API restart. Finish one reviewed implementation PR and settle after merge.
