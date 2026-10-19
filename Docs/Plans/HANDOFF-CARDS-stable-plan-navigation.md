# Stable Plan navigation chrome

Status: COMPLETED / SETTLED, 2026-10-19. No active write lease or successor
authorization remains. PRIME implemented the operator's dogfood correction on serial
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

Historical expected paths (released): this handoff; planSurface/PlanSurfacePage.tsx and owning
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

## Completion evidence

- Buddy PR #1464 merged at `52f51c199b57ade490c6ed04728073b01c25e46a`.
  Accepted implementation head: `4553098bd762d6c24a3dafeb9403dd045b78cb12`.
- One formal Architecture review cycle: source APPROVE on that exact head.
  Bugbot independently found no concrete blockers. Architecture independently
  passed 85 distinct tests: eight owning Plan tests, two PlanCardDeck tests,
  seven PlanSurfaceContext tests and all 68 PlayCurrentMomentCockpit tests.
  The diff check passed and the reviewed checkout was clean. PRIME separately
  reported the production build passing; Architecture did not rerun it.
- PRIME reported rendered 5202 acceptance on the real Plan: Document and Cards
  controls had identical positions in each viewport. Desktop x coordinates
  were 996.60 / 1072.26 / 1148.66 / 1199.93 at y 69.36; at 433px width they
  were 31.51 / 107.17 / 183.58 / 234.84 at y 100.16, without horizontal overflow.
  Document editor and Contents tops both measured 129.6354, side-by-side and
  nonblank. The full-width Contents header remained usable for collapse.
- PRIME reported shared Play Contents inspection of First sight left the
  Journey note target and current scene unchanged. All 11 protected responses
  and the real Run review remained exact; no document mutations or API restart
  occurred. These browser/runtime observations are PRIME's acceptance evidence,
  separate from Architecture's source and mocked-test review.
- Serving UI index:
  `674cadbe6f5990e3487785a95f032dddb8fed4c508f9206567b98834e558c5af`.
  PRIME retains the final read-only serving check. This settlement authorizes
  no successor capability, additional PR or runtime operation.
