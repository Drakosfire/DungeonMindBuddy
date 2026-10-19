# Stable Plan navigation chrome

Status: ACTIVE, 2026-10-19. PRIME owns the operator's dogfood correction on serial
branch codex/plan-navigation-continuity from8d6bd67dc in buddy-context-loop.
No overlapping open Plan navigation PR or active source lease. One implementation
PR, independent Architecture review, merge and guarded UI-only delivery on5202.

Remove the redundant Document-only scene selector now that Contents handles scene
navigation. Keep the same Contents/editor grid and navbar control positions across
Document/Cards; no view-dependent top-level geometry. Restyle Contents as an
integrated full-width panel header, retaining keyboard collapse and counts. Explain
that Markdown is source editing via tooltip/help, not an instructions-only mode.
Fix the Document layout where a sticky block-flow Contents list can push the editor
below the viewport. Keep current scene, drafts, undo, media captures and Plan/Play
writer separation unchanged. No document mutations from presentation/navigation.

Exclusive expected paths: this handoff; planSurface/PlanSurfacePage.tsx and owning
integration tests; planSurface/components/PlanSurfaceContext.css, PlanCardDeck.css;
shared/Contents.tsx and Contents.css plus Contents/PlanCardDeck tests. No dependency,
backend, state schema, other surface toolbar redesign or card topology changes.
Shared Contents header styling must remain usable in Play.

Verify stable DOM/editor identity, current scene and draft across views; Contents
navigation in Document, no redundant navbar selector, source still edits Markdown;
focused existing Cards/autosave/media gates and production build. Exact-head review,
rendered desktop/narrow positions and no blank Document, retained campaign records,
notes/reflections and protected routes. Serving prior index
 a0580a69c2a86dbee4097fd6997e70a9e894020ee3abad0c94ab1bd34bf98877;
retain old hashed assets/index; no API restart. Prior Cards/callout leases settled.
