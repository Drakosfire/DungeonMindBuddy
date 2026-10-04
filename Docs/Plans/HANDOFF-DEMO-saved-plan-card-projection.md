---
title: First production card projection from a saved World Plan
document_class: implementation_handoff
status: ACTIVE
created_at: "2026-10-04"
workstream: DEMO
design_authority: "../Plans/STEWARDS-HANDOFF-demo.md"
roadmap_authority: "../Roadmaps/ROADMAP-demo.md"
design_base: "Buddy main 4efada56aa93d529bf49128d82ba2d097b074af1"
activation_base: "Buddy main e7b1464af6474e64a0f36c8a2fc57927b85db190"
pr_topology: serial
implementation_branch: codex/demo-first-saved-plan-card-projection
implementation_pr: "https://github.com/Drakosfire/DungeonMindBuddy/pull/909"
---

# HANDOFF — DEMO: saved World Plan card projection

> ACTIVE implementation handoff, pinned to Buddy `main@e7b1464af6474e64a0f36c8a2fc57927b85db190` by PRIME on 2026-10-04. The design base was `4efada56aa93d529bf49128d82ba2d097b074af1`; the Page lease from #886 is released. PRIME accepted RAKE PR #908 at exact reviewed head `fb866cd707ffc622b6be053822b0ffb03e0901b7`, merged as `e7b1464af6474e64a0f36c8a2fc57927b85db190`, and activated this bounded card slice with the path/resource lease below.


PRIME reviewed and accepted this initial boundary on 2026-10-04: the Cards view
is a GM-only read-only lens over the same Plan editor draft; supported edits stay
in the existing Document editor and use ordinary Save/fresh reopen. The boundary is independently useful but is not the completed Plan/Play
experience. This handoff now activates its implementation.

## Status and activation record

**Status: ACTIVE.** PRIME authorized one serial production card projection PR on
Buddy `main@e7b1464af6474e64a0f36c8a2fc57927b85db190` and pinned the exact
exclusive write lease below. The implementation branch is
`codex/demo-first-saved-plan-card-projection` in the isolated `/tmp` checkout.

Re-anchor and collision audit at activation:

- PR #886 merged at `4efada56aa93d529bf49128d82ba2d097b074af1` from tested head
  `502b54d713e32e48f160182170c87b4f41fca990`; its Page/shell lease is closed.
- PR #904 merged at `fb1c48d622c9d8d404b1dddb5d5f618e03cc7ef0` from reviewed
  head `c355234d1486d8cbc46aa9afa611d6d1340b812c`; its six-path Agent composer
  lease is settled.
- RAKE PR #906 merged at `6feb3059b2da4d2ec29966ce9723f0effc70108f`; its
  mounted-test repair lease is closed.
- PR #907's Plan-to-Playable design merged at
  `d8e861661716d2fa8c1fb1e3e56ef08268d32da8`; it is a later contract, not Run
  implementation authority.
- RAKE PR #908 merged at this activation base from exact reviewed head
  `fb866cd707ffc622b6be053822b0ffb03e0901b7`. Its owning UI/index and Python
  conformance suites passed 53/53 and 7/7, respectively. The seven shared cases
  cover valid v1, distinct v2 targets, cross-Option target reuse, duplicate
  activates, duplicate suppresses, cross-list overlap, and dangling targets.
  This is bounded effect-target evidence, not full grammar equivalence. The
  fixture does not establish shared cross-parser parity for unknown versions,
  mixed grammars, or orphan Choice/Option cases. PRIME's activation keeps this
  card slice moving without changing parser paths: this projection's own model
  tests must independently fail closed for malformed, mixed, unknown, and orphan
  structures. No claim of full parser equivalence or Run admission is made.
- Open Buddy PRs rechecked at activation: #887, #869, #844, #826, #798, #781,
  #765, #764, #763, #761, and #760. Their current path leases do not overlap the
  ten-path card lease below. #887 remains prototype-only; its private
  corpus/media/state is not production data or a source to copy.

The card user action remains bounded: open a saved World Plan in a GM-only,
read-only card view, switch to the existing Document editor for supported text
edits, explicitly Save through the ordinary Plan writer, and freshly reopen the
same World/document to verify the projection at the exact committed revision.
This slice has no card-native editing controls and does not complete the broader
Plan/Play experience.

The same World-owned Plan and mounted `MarkdownEditorCore` remain the sole
content authority. The projection consumes the current Tiptap document and
existing Playable indexes; it does not copy Markdown, create a card store, or
mint identities. Cards and Document view show the same mounted draft. Card view
is read-only; text edits happen only in Document and use the existing Save.
After Save, the test reopens the same World/document from the committed mock
snapshot and compares IDs, hierarchy, associations, edges, source order,
revision, and digest. The initial projection is GM-only. Viewing/saving does not
publish Graph canon or authorize Run admission.

## User action and observable gap

The operator adopted connected scene cards, lenses, choices, a grouped outline,
location/map navigation, readable source, and contextual writing as the
production Plan/Play direction. The next bounded user action is opening an
existing saved World Plan in a GM-only, read-only card view, switching to the
existing Document editor for supported text edits, explicitly saving through
the ordinary Plan writer, and freshly reopening the same World/document to
verify the card structure at the exact new committed revision. This slice adds
no card-native editing controls.

At the current base, `PlanSurfacePage.tsx` mounts the World-owned Plan as a
`MarkdownEditorCore` inside `PlanSurfaceCanvasFrame`; it has no production card
projection. The user can read/edit the Plan as Markdown but cannot switch that
same saved Plan into marker-backed scene cards. This is a source inspection
finding, not a live-session or private-corpus witness. No reserved service or
operator tab was opened for this handoff.

The first slice is deliberately the saved-Plan card/document projection. It
is independently useful as a same-content read-only lens with clear unsaved
state, while the existing Document editor and Save/reopen flow remain the edit
path. It does not
claim the entire adopted board: location/map navigation, additional lenses,
Agent targeting, Play/Run, Graph enrichment, media, rolls, outcomes, and
player-facing visibility remain later bounded work where their source contracts
are available.

## Proposed contract

### Source and identity

1. The World-owned saved Plan and its current `MarkdownEditorCore` document are
   the sole content authority. The projection consumes the existing Tiptap
   document and the existing Playable element identity/index code; it does not
   keep another Markdown/card copy.
2. The projection is bound to the selected World ID, saved Plan document ID,
   and exact loaded committed revision/digest from the existing World Plan
   snapshot contract. Keep raw revision/digest inspectable in a compact details
   disclosure, not dominant chrome. A dirty mounted draft is clearly labeled
   `Draft / unsaved`, updates from the same editor session, and is never described
   as committed or Run-ready. Invalidate the projection on a
   World/document switch, editor rebase, revision mismatch, or diagnostics. A
   blank local Plan is not eligible until saved with a server identity.
3. Recognize only the existing v1 Scene-first and v2 Beat-first grammars,
   using `indexPlayableStructure` and `indexPlayableStructureV2` respectively.
   Keep their distinct heading shapes: v1 Scene H2 with Beat/Choice H3 and
   Options H4; v2 Beat H2 with Scene/Choice H3 siblings, optional explicit
   Choice-to-Scene association, and marked Option list items. Preserve stable IDs,
   document
   order, containment, associations, and v2 activation/suppression edges. Show
   v2 edges only as authored relationships; never execute them. Do not mint IDs,
   infer cards from headings/prose, retag markers, translate grammars, or change
   parser admission.
4. Cards and the complete Document view read the same current editor state;
   switching views never saves or changes the source. Cards are read-only. A
   supported text edit is made only in the existing Document editor against the
   same Tiptap draft, then saved with the existing explicit Save Plan action.
   Add no card-local editor, transaction path, record, or browser storage. Keep
   existing stale-revision, uncertain-save, local-recovery, and Markdown-fidelity
   safeguards intact.
5. After Save succeeds, freshly reopen that same World/document and derive
   the projection from its exact returned revision and its own committed content
   digest. IDs, hierarchy, authored links/edges, and source order must match the
   serialized result; unchanged markers and source regions remain unchanged,
   and only the intended Document edit differs. Never fall forward to unrelated
   local state or an older browser snapshot.
6. The initial projection is GM-only. Plan/Playable markers do not establish
   player visibility. A `dmb-ref` remains a source/navigation reference, not
   authority for Graph reads or writes. Viewing cards or saving through the
   existing Document writer does not publish Graph canon.

### Readable failure behavior

- **No recognized markers:** show a friendly empty card list, never infer cards,
  and keep the entire Plan readable with a direct Document-view/edit affordance.
  This is not a playable-ready structure and is not an error that blocks the Plan.
- **Malformed active structure:** unknown-version or mixed markers, duplicate
  IDs, wrong heading levels, nested identities, orphan Choice/Option, invalid
  Scene associations, unresolved v2 edge targets, or malformed marker-like
  text outside fenced code fail the whole projection closed. Show a concise
  diagnostic and a direct return to Document view; never show partial cards.
  Marker-like text inside code fences remains ordinary source text.
- **Unmarked prose or unsupported editor syntax:** never drop it from the Plan or
  fold it into the final card body. Preserve the full Document view and existing
  Markdown fidelity warnings/save blocks. Card view states that unmarked prose
  is not a card and provides a direct Document view. Use the existing body
  boundary rule: stop a card at the next marked element or ordinary document-root
  H1/H2; ordinary H3/H4 remain body prose.
- **World/document/revision changes, editor rebase, or new diagnostics:**
  invalidate the projection and refresh from the current exact source before it
  can be shown as current. There are no card actions that can mutate a stale
  replacement document.

### Settled duplicate-edge mismatch and accepted evidence boundary

ARCHITECTURE found that `validatePlayableOptionItemAttrs` did not reject a
repeated target inside one v2 `activates` or `suppresses` list, while the
canonical server parser rejects that duplicate. RAKE repaired the UI validator
and published PR #908, merged at `e7b1464af6474e64a0f36c8a2fc57927b85db190`.
Its exact reviewed head was `fb866cd707ffc622b6be053822b0ffb03e0901b7`; UI
identity/index/conformance suites passed 53/53 and Python passed 7/7.

The shared fixture proves seven bounded cases recorded in the RAKE handoff; it
does not prove shared unknown-version, mixed-grammar, or orphan Choice/Option
parity. PRIME explicitly activated this card slice with that limitation recorded.
The card model owns fail-closed projection coverage for those structures. DEMO
owns no parser/index/conformance fixture path and does not claim full grammar
parity or Run admission. Any broader Run/conformance requirement is a separate
steward decision after this slice.

### First-slice boundary

Include a switch between marker-backed scene cards and the complete Document
view, plus a grouped outline derived from existing marker hierarchy/order and
read-only Choices/Options with their authored relationships. The card lens is
read-only; edits to existing title/body text happen only after switching to the
current Document editor and use its ordinary transaction and Save path. Do not
add card creation, deletion, drag reorder, location maps, new grammar, automatic
markers, Run actions, new Agent context, Graph querying, or player projection
in this slice. No code may imply that a marked Plan is accepted as a Playable
Run source. If a new public or cross-owner API is required, stop and return the
exact gap to PRIME before implementation.

## Owning evidence and failure cases

Current source evidence at activation `e7b1464af6474e64a0f36c8a2fc57927b85db190`:

- `apps/live-control-ui/src/tiptap/playable/playableElementIdentity.ts` parses
  canonical v1 and v2 identities and rejects malformed marker forms. Its
  identity is attached to Tiptap nodes, including v2 `scene`, `activates`, and
  `suppresses` attributes.
- `apps/live-control-ui/src/tiptap/playable/playableStructureIndex.ts` exposes
  separate v1 and v2 indexes, structural order/hierarchy, and fail-closed
  diagnostics for unsupported grammar, duplicates, orphan membership,
  invalid scene association, and bad edges.
- `apps/live-control-ui/src/playSurface/runbook/nativeRunbookProjection.ts`
  provides `slicePlayableBodies`: card bodies stop at the next marked element or
  ordinary document-root H1/H2. Reuse this boundary so trailing Plan instructions
  cannot leak into the last card; ordinary H3/H4 remain body text.
- `apps/live-control-ui/src/planSurface/PlanSurfacePage.tsx` owns World Plan
  selection, editor state, exact save/recovery fences, and the existing
  World-scoped commit path. #886 merged and released this integration path;
  DEMO may use it only after PRIME pins the fresh card implementation lease.
- `apps/live-control-ui/src/tiptap/MarkdownEditorCore.tsx` and the existing
  semantic Markdown adapter import/export editor content. The slice must prove
  the supported transaction/serializer preserves the actual marker attributes
  and source references; the helper index alone cannot prove Save/reopen.
- `Docs/Plans/HANDOFF-world-plan-playable-adoption.md` (merged through #907)
  requires exact saved revision/digest projection authority, GM-only initial
  projection, and marker/order/link equivalence through editor transaction,
  ordinary Save, and fresh reopen before Plan-to-Run work.

Required owning-boundary evidence after activation:

1. Model tests cover valid v1 Scene-first and v2 Beat-first fixtures, exact
   parentage/order/IDs/edges, unmarked content with no minted IDs, malformed
   marker handling, mixed versions, duplicate/orphan identities, invalid
   associations/edges, and unknown structure failure without partial cards.
   Assert existing `slicePlayableBodies` boundaries: a body stops at the next
   marked element or document-root H1/H2; ordinary H3/H4 remain prose; trailing
   unmarked Plan instructions beyond those boundaries are not absorbed.
2. A mounted World Plan integration test uses synthetic mocked World/document
   APIs. It loads a saved Plan at an exact revision/digest, switches Document ↔
   Cards without changing source, edits an existing marked title/body once in
   the existing Document editor, and proves the read-only Cards lens reflects
   that same dirty Tiptap draft. It proves no server write before explicit Save,
   then verifies the existing prepare/commit writer receives preserved
   markers/refs/order and the changed prose. It reopens the same World/document
   from the committed mock snapshot and compares card/document structure and the
   exact returned revision/digest.
3. While Cards is active, changing World/document/revision invalidates the
   prior projection. The new projection is not labeled current until indexed
   from the exact selected editor snapshot. Switching Cards/Document never
   writes. Failed/uncertain Save preserves existing draft/recovery behavior;
   test stale ordinary Document Save callbacks only where the mounted surface
   retains such callbacks. Unmarked/malformed Plans remain readable in Document
   view with no false playable cards.
4. Focused `PlanSurfacePage`, Markdown import/export, Playable identity/index,
   and Save-fidelity tests run on the exact cumulative base-to-head diff. A
   synthetic browser check covers the card lens at desktop/mobile sizes; it does
   not replace the mounted exact Save/reopen witness. This slice never calls the
   server Run manifest parser at runtime or invokes Run admission. The card model
   tests independently fail closed for unknown versions, mixed grammar, malformed
   markers and orphan Choice/Option, in addition to the bounded edge cases. The
   shared #908 fixture proves its seven recorded cases only; it is not full
   parser/grammar equivalence. Full Plan-to-Run runtime and APP-STATE admission
   remain later work; the existing `admit_playable_revision` rejects WorkObjects
   whose kind is not `runbook`.
5. Session 29 remains the intended operator acceptance example after the code
   merges. Until operator use succeeds, no J1–J6 or connected-demo gate is
   closed. Use a synthetic fixture for tests and isolated preview; do not copy
   private DOGFOOD corpora or touch ports 5202/5203.

## ACTIVE exclusive write lease

Only this lane may write the following ten paths while ACTIVE:

1. `Docs/Plans/HANDOFF-DEMO-saved-plan-card-projection.md` — this activation,
   acceptance evidence, and final settlement.
2. `apps/live-control-ui/src/planSurface/PlanSurfacePage.tsx` — integrate the
   view switch and pass current World/document/revision/digest, editor draft, and
   ordinary Save state.
3. `apps/live-control-ui/src/planSurface/components/WorldPlanCardProjection.tsx`
   — new read-only projection component.
4. `apps/live-control-ui/src/planSurface/components/WorldPlanCardProjection.css`
   — local component styling only; no global shell/layout rules.
5. `apps/live-control-ui/src/planSurface/WorldPlanCardProjection.model.test.ts`
   — new focused projection and failure-matrix tests.
6. `apps/live-control-ui/src/planSurface/WorldPlanCardProjection.integration.test.tsx`
   — new mounted Save/reopen equivalence witness using synthetic APIs.
7. `Docs/Roadmaps/ROADMAP-demo.md` — record this active lease, exact evidence,
   and the remaining demo gate.
8. `Docs/Plans/HANDOFF-DEMO-plan-agent-panel-usability.md` — settle only the
   accepted/merged #904 predecessor state for this successor.
9. `Docs/Plans/HANDOFF-DEMO-plan-navigation-shell.md` — settle only the
   accepted/merged #886 predecessor state for this successor.
10. `Docs/Plans/HANDOFF-RAKE-playable-edge-conformance.md` — settle only
    #908's merged status, closed lease, and bounded evidence pin.

No other path is leased. The merged predecessor Page/shell work is released;
this handoff grants a new, exclusive `PlanSurfacePage.tsx` lease for the card
integration only. If required paths exceed the ten above, return to PRIME before
editing them.

## Topology and resources

**Topology: serial; one implementation PR.** Base: Buddy `main@e7b1464af6474e64a0f36c8a2fc57927b85db190`. Branch: `codex/demo-first-saved-plan-card-projection`, isolated checkout `/tmp/dmb-demo-first-saved-plan-card-projection`. PRIME owns independent review and merge. Opening/updating the one assigned PR is part of this ACTIVE implementation authority.

The implementation uses mocked World/document APIs and synthetic source only.
No provider, database, credential, real World/Plan, private corpus, Graph read/write,
Run, API/schema, or server runtime is leased. A synthetic browser preview may use
UI port 54126 and mock API port 54127 only after confirming both are free and
have no existing owner. If either port is occupied or assigned, return the
resource collision to PRIME; do not reuse the listener. Operator ports 5202/8000
and DOGFOOD 5203 remain untouched.

## Stop conditions

Return to PRIME before writing code if:

- a card path is found to be actively leased by another lane, or a required
  resource has an existing owner;
- the editor/parser contract cannot project supported v1/v2 identities without
  changing its public/admission contract;
- the projection cannot reflect the same Tiptap draft and survive supported
  Document edits plus ordinary Save/reopen without adding a second content
  store, identity system, or public API;
- the ordinary World Plan writer cannot save/reopen the resulting exact source;
- unmarked or malformed content would be hidden, normalized, or represented as
  valid cards;
- scope expands into map/location authority, new grammar, API/schema/Graph,
  Run, player visibility, Agent targeting, or another PR.

No acceptance claim may exceed the exact mounted Save/reopen tests, isolated
preview, and operator use actually completed. This ACTIVE lease does not close
J1–J6 or the operator acceptance gate.

## DEMO implementation verification — 2026-10-04

The following evidence is on the active serial branch and uses only synthetic
World/Plan data:

- `WorldPlanCardProjection.model.test.ts` and
  `WorldPlanCardProjection.integration.test.tsx`, together with
  `PlanSurfacePage.test.tsx`, `WorldPlanEditHost.integration.test.tsx`,
  `playableStructureIndex.test.ts`, and `playableEdgeConformance.test.ts`:
  **107/107 passed** across six files. Mounted witnesses confirm the same
  editor node and selection survive view switching; the card lens reflects its
  dirty draft; and no prepare/commit runs before explicit Save. The v1 witness
  verifies exact marker order through the ordinary writer and fresh reopen at
  revision 6 with its returned digest. A v2 witness edits Document, opens Cards,
  saves while Cards remains active, then freshly reopens and checks exact ID
  order, Beat→Scene/Choice siblings, Choice→Option containment, Scene
  association, authored `activates`/`suppresses`, both preserved `dmb-ref`
  links, revision, and digest. A pending/uncertain commit witness confirms the
  card basis is unavailable instead of combining a prepared revision with an
  older digest; the dirty draft and pending recovery record remain, and no
  duplicate prepare/commit occurs. A further mounted test confirms
  document/World changes retire the old projection.
- `markdownIngressCorpus.test.ts` and `usePlanMarkdownSave.test.ts`:
  **133/133 passed** across two files.
- Final focused evidence is **240/240** across eight files (the 107 tests above
  plus 133 Markdown ingress/save-fidelity tests).
- `node_modules/.bin/vite build --configLoader=runner --outDir
  /tmp/dmb-demo-card-build-final-review` succeeds. Vite emits the repository's
  existing advisory about a JavaScript chunk above 500 kB. The standard
  `npm run build` typecheck step remains blocked by the inherited JSX namespace
  error below and its attempt to write build metadata through the read-only
  `node_modules` symlink; the standalone Vite production build is green.
- `tsc -p tsconfig.app.json --noEmit --pretty false
  --tsBuildInfoFile /tmp/dmb-demo-card-tsbuildinfo-prime-review` reports only the inherited
  `src/statblocks/publication/ThreatPublicationPanel.tsx(553,77): TS2503 Cannot
  find namespace 'JSX'` error, outside this ten-path lease.
- Synthetic browser preview on UI/API ports 54126/54127 uses no live service.
  At desktop 1280×800, the card region measures 608px wide and the document
  width is 1265px. At mobile 390×844, body width is 375px, the card region is
  335px wide at a 20px inset, the one-column heading/grid styles apply, and the
  document does not overflow the viewport. Operator UI/API 5202/8000 and
  DOGFOOD 5203 were not opened or contacted; no Save was performed in preview.
- The separate graphless Ask path was not exercised or changed. The legacy
  `/api/live/query` route does not establish canonical World conversation or
  Graph provenance. No clean-draft Graph basis is adopted by this slice.

The implementation is delivered in [PR #909](https://github.com/Drakosfire/DungeonMindBuddy/pull/909)
against `main@e7b1464af6474e64a0f36c8a2fc57927b85db190`. The PR is open for
PRIME's independent review; its exact final implementation head is recorded in
the PR metadata after this verification update. The ACTIVE lease remains in
review and PRIME owns merge.
