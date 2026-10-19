# Shared Contents and top alignment

Status: ACTIVE, 2026-10-19. Operator dogfood correction authorizes naming the
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
