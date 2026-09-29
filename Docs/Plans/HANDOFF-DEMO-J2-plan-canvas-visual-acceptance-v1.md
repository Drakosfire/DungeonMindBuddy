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
**Status:** DESIGN READY — implementation blocked until this authority merges, then re-anchor and activate  
**Workstream / owner:** LOCAL DEMO ACCEPTED / DEMO J2; Buddy Plan presentation  
**Direction:** DESIGN → CODE → PRIME  
**Design base:** Buddy `main@bab345d64b6de1075f7a5fa44dc6af87d30d9afa`  
**PR topology:** serial; this is a design/authority PR only; one implementation PR after merge/re-anchor  
**PR title:** `DEMO: refine the Plan canvas visual boundary`  
**Implementation authority:** none until PRIME accepts this bounded handoff on main and an implementation lane is activated. Do not change app code in this design PR.  
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

## §4 Proposed implementation write lease (inactive until activation)

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

No other path is leased. The lease is inactive while this design is pending. At activation, recheck all open PRs and current main; if shared file ownership or required paths differ, stop for a reviewed lease amendment before editing.

## §5 Exclusions and collision boundaries

- No Agent UI/backend/context change; #790/#791 do not waive the visual gate.
- No Plan ownership/persistence/API/recovery change, new World or graph write, or database reset.
- No Plan→Run change; no Ingest, Build, Play, or Combat redesign.
- No production global theme or shell redesign, theme packs, UI substrate expansion, Canvas/F5, or broad editor rewrite.
- No change to campaign Plan semantics or other active PRs.
- No model/provider calls and no durable product mutations during visual dogfood.

Use the existing isolated demo app/runtime. Inspect only the named World Plan; do not save or edit the user's Plan while measuring presentation. If that exact witness is unavailable, establish a separately disposable visual fixture without resetting or deleting existing demo data.

## §6 Activation and implementation constraints

This is a rare DEMO design/architecture PR because the existing implementation has merged and been explicitly rejected by its product owner. The PR's design output is this bounded handoff plus a backward pointer in the roadmap.

After PRIME accepts and this PR merges:
1. Re-anchor to the exact new main.
2. Record the predecessor decision and current open-PR/runtime ownership.
3. Change the handoff from blocked to ACTIVE only after those gates are true.
4. Open exactly one assigned implementation PR under `DEMO`; no stacked successor.
5. Keep all Plan editor, draft, Save, conflict, identity, and focus behavior owned by the current semantic controllers. Presentation components receive view data and emit existing intents only.
6. Do not count the Ladle prototype as product acceptance.

## §7 Required proof after implementation

- Focused owning-boundary tests for blank and populated World Plan, exact toolbar/editor identity, supported theme mapping, registered component rendering, identity replacement, Save/reload and existing conflict/recovery behavior.
- Campaign Plan compatibility tests; scoped typecheck/build attempt, test run and `git diff --check`. Report inherited failures exactly.
- Exact-head real browser screenshots at desktop and 390×844 for blank, short, and longer authored Plans. Record actual browser viewport, URL/identity, styles/theme selected, and verify the page boundary visually without using computed CSS alone as proof.
- No browser console errors, horizontal overflow, stale toolbar actions, cross-World/document mutations, API or database writes during visual inspection.
- Human product-owner disposition on the actual rendered route: ACCEPT or REJECT with the remaining defect. Until accepted, DEMO-J2 stays open.

## §8 Handoff

Return the implementation PR URL, exact base/head, cumulative changed-path table, review cycles, test/build evidence, four viewport/content witnesses, console/overflow result, and the operator's visual disposition. This slice only addresses Plan canvas presentation; it does not pass the complete DEMO-J2 multi-turn Agent/session journey or LOCAL DEMO ACCEPTED.
