---
pr_body_template: |
  ## Handoff pointer
  - Workstream: DEMO / J2 — Plan canvas visual acceptance
  - Direction: DESIGN → CODE → PRIME
  - Handoff: `Docs/Plans/HANDOFF-DEMO-J2-plan-canvas-visual-acceptance-v1.md`
  - Topology: design PR now; one serial implementation PR only after this authority merges and re-anchors

  ## Review contract
  The exact product-owner rejection is the gate: a visible CSS border is not enough if the Plan still reads as nested generic panels. This PR defines the bounded next witness and implementation lease; it contains no product-code changes and does not claim J2 acceptance.

  ## Base
  Buddy `main@bab345d64b6de1075f7a5fa44dc6af87d30d9afa` after #790/#791 and #789.
---

# HANDOFF — DEMO: make the Plan canvas feel like a deliberate writing surface

**Created:** 2026-09-29  
**Status:** ACTIVE — re-anchored and activated after #792 merged on 2026-09-29  
**Activation base:** Buddy `main@4017a876a1f0fb6aa3fd5d3ac80083fb93ca52c9` (merge commit for #792)  
**Workstream / owner:** LOCAL DEMO ACCEPTED / DEMO J2; Buddy Plan presentation  
**Direction:** DESIGN → CODE → PRIME  
**Design base:** Buddy `main@bab345d64b6de1075f7a5fa44dc6af87d30d9afa`  
**PR topology:** serial; #792 is merged design authority; one implementation PR is now authorized from the activation base  
**PR title:** `DEMO: refine the Plan canvas visual boundary`  
**Implementation authority:** ACTIVE on `main@4017a876a1f0fb6aa3fd5d3ac80083fb93ca52c9`; exactly one implementation PR under DEMO is authorized.  
**Merge authority:** PRIME owns ecosystem coordination; do not merge from DEMO.

## §1 Mission and invariant

Make the selected World-owned Plan read immediately as one intentional, editable writing surface—not a dark generic panel containing a large blank slab and nested default-looking controls.

**Human invariant:** on the actual Plan route, the operator can immediately distinguish the Plan page/work surface from surrounding chrome, recognize the editor's boundary when the Plan is blank or populated, and read registered Markdown components without the presentation feeling like browser/editor defaults.

A border declaration is not proof. The operator already rejected #789's visual result after viewing the real page even though its CSS contained a 3px outer frame and 2px editor edge. Human acceptance on the rendered product is required after implementation; screenshots, tests, component reuse, and computed styles are supporting evidence only.

## §2 Re-anchored evidence

- #789 merged at `ed1bf1ba0531bf9018f2397863825fa20c781bfe` from reviewed code head `7e4fb73d5a553b58bd1350c9c0ded653ef97b2e0`. It restored shared Plan composition and tools, but did not earn visual acceptance.
- The operator re-viewed the blank World Plan at `http://127.0.0.1:5201/plan?world=pr788-exact-head-witness-a-2026-09-28&documentId=8e02715a-fc5b-48dc-ab7c-ba470a0909a8` and rejected it: “This canvas looks awful and has no boundary. Where did that go? We have a bunch of default styling.”
- In follow-up dogfood on that 5201 route, the operator clarified that the inline `TEXT` / `INSERT BLOCKS` bar is functional but less useful than placing editing actions in Buddy's established toolbars or a dedicated Plan surface navigation bar. This control-placement/composition issue remains open; recoloring the inline bar does not resolve it. Do not call the inline bar accepted final UX or dismiss the route as a throwaway prototype: #789 was a merged intermediate product integration. An earlier 5202 preview used a synthetic route with disabled controls; that preview is historical. The later disposable `of-conks-demo-plan-canvas` World route on 5202 rendered an editable blank draft and was used only for read-only styling inspection. It does not answer the toolbar-placement question. Resolve that question through bounded reuse of the existing AppChrome/tool-host/context seams, not new authority or broad shell redesign.
- Exact-head inspection found a 3px slate wrapper and 2px parchment-editor border, but two nested framed regions read as generic panels rather than a clear canvas/page boundary. The Plan requests theme ID `mireward-runbook`, for which `prepMarkdownThemes.css` has no theme-specific selector; scoped ad-hoc rules currently carry much of the appearance. This is a likely implementation cause, not a settled visual solution.
- #789's composition handoff is COMPLETE/HISTORICAL. Its write lease is released. Do not amend or silently reopen #789.
- Current authoritative roadmap already states that J2 and operator acceptance remain open. This handoff refines the next visual witness; it does not change any domain, Agent, persistence, or Plan→Run status.

## §3 Bounded design/implementation contract

The implementation, after activation, will own one capability: **a coherent visual boundary and purposeful presentation for the World-owned Plan editor**.

Required visible behavior:

1. One clear, intentional canvas/page hierarchy on desktop and narrow screens. Avoid multiple equally prominent nested frames; the boundary must remain obvious for an empty document and authored content.
2. Plan editing tools look like Buddy controls intentionally grouped with the writing surface, not unstyled browser defaults or a stack of unrelated boxes. Preserve the existing toolbar behavior and current-at-click editor binding.
3. The selected Markdown theme identifier must resolve to actual supported presentation rules. Registered callouts, Decision/Consequence blocks, and graph-reference chips retain their semantics and remain legible. Do not ship a theme name that silently falls through to generic defaults.
4. Blank, short, and longer Plan documents all retain sensible reading width and editing affordance without a large empty slab being mistaken for content.
5. World/document identity, Save/reload/CAS/conflict/recovery, navigation, editor tools, and the established campaign Plan presentation remain unchanged.

Use the existing Buddy visual language and already-accepted primitives where appropriate. The code worker may prototype at most two bounded visual treatments in the existing backend-free Ladle lab, then choose one for the real product witness. Do not add a UI framework, theme-pack system, global shell redesign, new domain authority, or Canvas dependency. If the required appearance implies a broader design-system or shell change, stop and return for re-decomposition.

## §4 ACTIVE implementation write lease

| Path | Bounded role |
| --- | --- |
| `apps/live-control-ui/src/planSurface/PlanSurfacePage.tsx` | Supply the actual World Plan identity and existing toolbar/context to the shared presentation boundary; no fabricated campaign/session identity |
| `apps/live-control-ui/src/planSurface/PlanSurfacePage.test.tsx` | Blank/authored view, identity replacement, actual toolbar and persistence regressions |
| `apps/live-control-ui/src/planSurface/components/PlanSurfaceCanvas.tsx` | Reusable presentation-only canvas seam; preserve existing editor and command owners |
| `apps/live-control-ui/src/planSurface/components/PlanSurfaceShell.test.tsx` | Ensure campaign Plan composition and behavior remain compatible |
| `apps/live-control-ui/src/planSurface/planSurface.css` | Plan canvas layout and boundary where shared Plan styling belongs |
| `apps/live-control-ui/src/tiptap/prepMarkdownThemes.css` | Resolve actual theme styling for the selected Plan theme and registered components |
| `apps/live-control-ui/src/styles.css` | Remove/replace only the conflicting World-owned presentation rules |
| `Docs/Plans/HANDOFF-DEMO-J2-plan-canvas-visual-acceptance-v1.md` | Backward-looking exact design decision, activation/evidence and final operator disposition |
| `Docs/Plans/HANDOFF-DEMO-J2-world-plan-canvas-composition-v1.md` | Record #789 completion and its still-rejected visual result without rewriting its historical authority |
| `Docs/Roadmaps/ROADMAP-demo.md` | Keep the Plan visual gate and DEMO next action truthful |

No other path is leased. The lease was activated on `main@4017a876a1f0fb6aa3fd5d3ac80083fb93ca52c9` after #792 merged. The activation audit found the then-open PRs #781 (Build-only), #763–#765 (Rules), and #760–#761 (UI substrate); none claims a leased Plan canvas path. Recheck PRs and runtime ownership before opening the implementation PR; if shared file ownership or required paths differ, stop for a reviewed lease amendment.

## §5 Exclusions and collision boundaries

- No Agent UI/backend/context change; #790/#791 do not waive the visual gate.
- No Plan ownership/persistence/API/recovery change, new World or graph write, or database reset.
- No Plan→Run change; no Ingest, Build, Play, or Combat redesign.
- No production global theme or shell redesign, theme packs, UI substrate expansion, Canvas/F5, or broad editor rewrite.
- No change to campaign Plan semantics or other active PRs.
- No model/provider calls and no durable product mutations during visual dogfood.

Use the existing isolated demo app/runtime. Inspect only the named World Plan; do not save or edit the user's Plan while measuring presentation. If that exact witness is unavailable, establish a separately disposable visual fixture without resetting or deleting existing demo data.

## §6 Activation and implementation constraints

The design/architecture authority merged as PR #792 at `4017a876a1f0fb6aa3fd5d3ac80083fb93ca52c9`; PRIME's Cycle 3 DESIGN PASS was issued on exact design head `7f3e3f3ca582db0437d71efa16be05de5432f25d` (review `5351790554`). This handoff is re-anchored and ACTIVE on that exact main commit. Open exactly one assigned implementation PR under `DEMO`; no stacked successor.
5. Keep all Plan editor, draft, Save, conflict, identity, and focus behavior owned by the current semantic controllers. Presentation components receive view data and emit existing intents only.
6. Do not count the Ladle prototype as product acceptance.

## §7 Required proof after implementation

- Focused owning-boundary tests for blank and populated World Plan, exact toolbar/editor identity, supported theme mapping, registered component rendering, identity replacement, Save/reload and existing conflict/recovery behavior.
- Campaign Plan compatibility tests; scoped typecheck/build attempt, test run and `git diff --check`. Report inherited failures exactly.
- Exact-head real browser screenshots at desktop and 390×844 for blank, short, and longer authored Plans. Record actual browser viewport, URL/identity, styles/theme selected, and verify the page boundary visually without using computed CSS alone as proof.
- No browser console errors, horizontal overflow, stale toolbar actions, cross-World/document mutations, API or database writes during visual inspection.
- Human product-owner disposition on the actual rendered route: ACCEPT or REJECT with the remaining defect. Until accepted, DEMO-J2 stays open.

## §8 Handoff

Return the implementation PR URL, exact base/head, cumulative changed-path table, review cycles, test/build evidence, six viewport/content combinations (blank, short, and longer authored Plan at both desktop and 390×844), console/overflow result, and the operator's visual disposition. This slice only addresses Plan canvas presentation; it does not pass the complete DEMO-J2 multi-turn Agent/session journey or LOCAL DEMO ACCEPTED.

### Active implementation evidence (2026-09-29)

- Code is being implemented on the serial branch `codex/demo-j2-plan-canvas-visual-impl`. It contains activation base `4017a876a1f0fb6aa3fd5d3ac80083fb93ca52c9` plus activation-authority sync `76239846c98797bb1455ffa22b2a273d64591205`; the implementation PR's actual base is the latter.
- The current branch still keeps the existing inline editor toolbar inside the Plan canvas frame. Its warm styling/grouping is an interim presentation treatment, not resolution of the operator's established toolbar/surface-navigation placement requirement. The frame has a continuous warm perimeter around a dark work surface; the parchment sheet has a stronger continuous outline and inset keyline; the blank editor minimum height is shorter. World Plan selects the explicitly defined `world-plan` theme; Campaign Plan remains on its existing theme/configuration.
- Historical responsive preview, before the current disposable-World inspection: local implementation UI `http://127.0.0.1:5202/plan?world=pr776-second-synthetic-world` used API 8817. Desktop viewport was 1280×720; a 390×844 check reported `document.scrollWidth=375` and `clientWidth=375`. That synthetic route had legacy document scope and disabled editing controls, so this was only responsive layout evidence, not the required valid-route witness or operator acceptance.
- On 2026-09-29 the operator reported the canvas still looked generic and lacked a boundary. Inspection found their visible tab at port 5201, served by the older `dmb-demo-world-plan-composition-work` checkout, while the current implementation preview is port 5202. The 5201 screenshot did show the older separated toolbar/default-looking groups. The implementation was refined on this PR: retain the toolbar as unboxed canvas chrome, and make the paper itself a distinct parchment page with a high-contrast edge, inset keyline, and visible spine. A follow-on styling pass replaced generic blue-gray toolbar controls with compact warm-toned actions and text-group separators. That palette refinement does not resolve the operator's separate placement preference: editing commands should be evaluated for reuse of established Buddy toolbars or a dedicated Plan surface nav. The operator then correctly pointed out that the outer work-surface boundary had been removed entirely (the wrapper had only a top divider); commit `42d232a9` restores a continuous, subdued dark work-surface boundary around the paper. The 5201 tab remains the older checkout. The exact PR UI now runs on 5202 with its isolated API on 8821; a separate `/world-graph/projection` request still returns 503 because `DUNGEONMIND_WORLD_GRAPH_AUTHORITY_DATABASE_URL` is not configured. That affects the authority badge/projection, not the availability of the blank Plan editor surface.
- Earlier boundary-restoration iteration: `42d232a92f83fb6c73025a64b285407af9020da7`; it is not the latest code-changing commit. The later warm-perimeter refinement is `d9ff5ac2557d4c0948367231837182e5a606ed74` (with subsequent documentation commits). Focused tests and diff-check evidence are recorded against their exact heads below; PRIME Cycle 6 HOLD `5353355918` confirmed only the earlier boundary correction. The six-case live witness and operator disposition remain open.
- After the operator reiterated that the canvas still looked boundaryless/default, I inspected the PR preview at `http://127.0.0.1:5202/plan?world=of-conks-demo-plan-canvas` (blank unsaved Plan draft, 1279×718 viewport). Commit `d9ff5ac2557d4c0948367231837182e5a606ed74` strengthened the work-surface boundary to a 2px warm perimeter with inset keyline and aligned the toolbar divider. The last observed unfocused state visibly distinguished the framed dark work surface from the parchment page. A subsequent focused-editor screenshot showed the same 3px action outline on the editor and its `:focus-within` canvas ancestor; the current repair removes the ancestor outline while retaining visible keyboard focus on controls/editor. The inline toolbar remains an unresolved placement issue. Focused `PlanSurfacePage.test.tsx`: 8 passed at the prior code head; re-run after the focus repair. The visual inspection used a disposable blank World, did not save Plan content, and did not call a model or write graph data.
- **This is not the required product acceptance witness.** The named #789 World Plan document was unavailable from the API database used for that inspection. The separately disposable World `of-conks-demo-plan-canvas` was created once via the ordinary World chooser; its blank Plan route rendered with an editable draft. The most recent browser inventory now shows that the 5202 preview is unreachable because its local servers are stopped. Do not treat the disposable fixture as the named Plan or as a persisted Plan round-trip: the DungeonMind graph-authority endpoint returned 503 because `DUNGEONMIND_WORLD_GRAPH_AUTHORITY_DATABASE_URL` was not configured, and the status badge correctly reported attention. Styling inspection did not save Plan text, call a model, or write graph data. The six-case blank/short/long × desktop/390×844 proof and operator ACCEPT/REJECT remain outstanding; do not merge or mark J2 accepted from this partial preview.
- Focused automated evidence: `PlanSurfacePage.test.tsx` + `PlanSurfaceShell.test.tsx`, 108 passed. `vite build` passed (existing >500 kB chunk warning). `npm run build` stops at the inherited `ThreatPublicationPanel.tsx:553` `Cannot find namespace 'JSX'` TypeScript error. `git diff --check` passed on the complete implementation + authority-sync diff before commit `a4a29a68721892595dff959908cdff31b0b66d75`.
