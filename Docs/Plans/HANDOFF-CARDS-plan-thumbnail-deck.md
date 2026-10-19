# Plan Cards thumbnail deck

Status: SETTLED, 2026-10-19. PR #1460 merged at
`4a6d758bce73567d0f4543528200c45b73e2d220` after Architecture Review Cycle 2 PASS
on `975130eebd85ec7549493e248696b5797834d10b`. PRIME completed final desktop/narrow
and retained-state acceptance. Source/runtime leases and reviewer consumers are
released. Direct card editing is not activated.

The following records the completed contract. Operator explicitly authorized
implementation, independent review, merge and delivery on 5202. Serial lane owned by PRIME in the
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

## Completed evidence and limits

Architecture independently ran 34 owning Plan/deck tests on the implementation
head; all passed. Cycle 2 checked the final CSS-only correction for scoped sidebar
selectors, explicit text color and font; behavioral test evidence carried forward.
Cumulative whitespace checks passed and Bugbot found no implementation issue.
PRIME reported the final production build passed.

PRIME's browser acceptance verified an independently scrolling 14-scene deck,
selected-card scroll position through Document/Cards, keyboard selection, draft
previews before autosave, resolved saved-media thumbnails, and authored image
collapse through autosave/reopen. At narrow CSS width 433 the deck starts collapsed,
selection returns focus to the toggle, and the page has no horizontal overflow.
Final styling and retained-state checks passed: all 12 protected responses,
including notes and closing reflections, remained exact. The synthetic fixture
was moved recoverably to Trash. These are PRIME-owned runtime witnesses.

Delivered UI index SHA256:
`372d1ab815933b4028f1e9d4e650cc2829d9fb7df03bdab26e6821b396975114`.
See the [final delivery receipt](https://github.com/Drakosfire/DungeonMindBuddy/pull/1460#issuecomment-6277721621).

This settles existing-scene thumbnail navigation only. One scene remains one deck
entry; focused direct editing, structural editing, dense-scene facets and broader
Plan/Play acceptance remain open and require separate bounded authorization.
