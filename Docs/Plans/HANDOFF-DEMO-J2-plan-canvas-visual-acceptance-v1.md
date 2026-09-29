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
- The World Plan toolbar is now composed inside the shared canvas frame. The frame has a deliberate warm top rule and defined perimeter; the parchment sheet has a darker, continuous outline and book-spine edge; the blank editor minimum height is shorter so the empty document no longer reads as a large slab. World Plan now selects the explicitly defined `world-plan` theme. Campaign Plan remains on its existing theme/configuration.
- Read-only browser preview: local implementation UI `http://127.0.0.1:5202/plan?world=pr776-second-synthetic-world` using existing API 8817. Desktop viewport was 1280×720. A 390×844 viewport check reported `document.scrollWidth=375` and `clientWidth=375`; no horizontal overflow. Browser console returned no errors/warnings. Screenshots were inspected at both sizes.
- On 2026-09-29 the operator reported the canvas still looked generic and lacked a boundary. Inspection found their visible tab at port 5201, served by the older `dmb-demo-world-plan-composition-work` checkout, while the current implementation preview is port 5202. The 5201 screenshot did show the older separated toolbar/default-looking groups. The implementation was refined on this PR: remove the surrounding generic card frame, retain the toolbar as unboxed canvas chrome, and make the paper itself the single dominant boundary with a high-contrast continuous edge, inset keyline, and visible spine. The current 5202 preview reflects this refinement; it still uses the scope-mismatched synthetic Plan and therefore does not prove enabled-toolbar styling or satisfy product acceptance.
- Latest exact code head for this visual refinement: `298be4bf`. Focused `PlanSurfacePage.test.tsx`: 8 passed. `git diff --check` passed for the code change. PRIME's original HOLD evidence remains applicable to the missing six-case live witness; this CSS iteration does not close it.
- **This is not the required product acceptance witness.** The named #789 World Plan document is unavailable from the currently reachable API database. The substitute synthetic World Plan renders, but its legacy document scope mismatches the selected World, so the route correctly shows `Managed Plan context does not match the selected World` and disables editing controls. The branch did not save/edit a document, create a fixture, call a model, or mutate the database. The six-case blank/short/long proof and operator ACCEPT/REJECT remain outstanding; do not merge or mark J2 accepted from this partial preview.
- Focused automated evidence: `PlanSurfacePage.test.tsx` + `PlanSurfaceShell.test.tsx`, 108 passed. `vite build` passed (existing >500 kB chunk warning). `npm run build` stops at the inherited `ThreatPublicationPanel.tsx:553` `Cannot find namespace 'JSX'` TypeScript error. `git diff --check` passed on the complete implementation + authority-sync diff before commit `a4a29a68721892595dff959908cdff31b0b66d75`.
