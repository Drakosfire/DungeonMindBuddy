# Shared Contents and top alignment

Status: SETTLED, 2026-10-19. PR #1461 merged at
`6f4092d0cf6e9344b294704003dc93c63696ea8f` after Architecture Review Cycle 1 PASS
on `e375d10dc11cf60afd7d2fc41e30a0c60ad1426e`. PRIME completed final real-host and
retained-state acceptance. Source/runtime leases and reviewer consumers are
released. The historical contract below grants no continuing implementation lease.

Operator dogfood correction authorized naming the
thumbnail navigation Contents, reusing it in Plan/Play and removing its top gap.
PRIME owns a serial lane from e5e7838e0 in buddy-context-loop on
codex/shared-contents-top-alignment. No overlapping active Contents PR.

Invariant: share the inert thumbnail navigation presentation, not save or scene
state. Plan uses its fenced draft cursor; Play uses its existing inspection
callback. Browsing cannot Make Current, change a note target or save a document.
Plan editor/deck identity and Play overlay/Escape/focus/current-vs-inspected and
notes controllers remain owners. Sticky Contents is relative to the existing
surface scrollport; do not apply the navbar offset a second time.

Exclusive paths: this handoff; shared/Contents.tsx and Contents.css;
planSurface/components/PlanCardDeck.tsx, CSS/tests and existing integration tests;
playSurface/currentMoment/PlayCockpitPanels.tsx, PlayCurrentMomentCockpit.tsx and
its tests; playSurface.css only for owner-local shared-presentation sizing.
markdownReader/ReadOnlyBodyContent.tsx only to export its existing body-admission
check for thumbnail fidelity. No schema, backend, Graph, notes writer, lockfile or structural/direct editing.

Verify Plan/deck mounted continuity tests; Play cockpit/notes inspection tests;
production build and cumulative diff; independent Architecture exact-head review;
Plan/Play desktop/narrow real-host behavior and top-offset measurements with
retained documents/Run/notes/reflections unchanged. UI-only 5202 atomic lease,
prior index372d1ab815933b4028f1e9d4e650cc2829d9fb7df03bdab26e6821b396975114;
keep rollback assets/index, no API restart. One reviewed PR then guarded settlement.

## Completed evidence and limits

Architecture independently ran all 107 targeted Plan/deck/model, Play cockpit
and floating-note tests; all passed. Cumulative whitespace checks passed and
Bugbot found no issue. PRIME reported a passing production build.

PRIME's final 5202 witness measured Plan Contents and workspace tops both at
129.64 CSS pixels in selected/outline views, with an 8-pixel sticky offset and
no duplicate navbar offset. Shared Play Contents inspected another scene while
the current scene and current-scene Notes target stayed unchanged. At narrow CSS
width 433, Plan collapse/focus and Play More → Browse Contents overlay/Escape
behavior passed without horizontal page overflow. All 12 protected responses,
including notes and closing reflections, remained exact. These browser/state
checks are PRIME-owned evidence.

Delivered UI index SHA256:
`877c2da063ed4229847e2f7bfc278579bdb55993f7d8c07cdae4bc6899ca3e77`.
See the [delivery receipt](https://github.com/Drakosfire/DungeonMindBuddy/pull/1461#issuecomment-6278019464).

This settles shared Contents presentation and top alignment. Existing owners still
control Plan draft navigation, Play inspection/current state and notes. Direct
card editing, structural editing, dense-scene facets and broader Plan/Play
acceptance remain open; no successor is activated here.
