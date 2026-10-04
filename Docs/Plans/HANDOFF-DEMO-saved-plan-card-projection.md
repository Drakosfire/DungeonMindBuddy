---
title: First production card projection from a saved World Plan
document_class: implementation_handoff
status: BLOCKED
created_at: "2026-10-04"
workstream: DEMO
design_authority: "../Plans/STEWARDS-HANDOFF-demo.md"
roadmap_authority: "../Roadmaps/ROADMAP-demo.md"
design_base: "Buddy main 4efada56aa93d529bf49128d82ba2d097b074af1"
pr_topology: serial
implementation_branch: not_assigned
implementation_pr: not_authorized_until_activation
---

# HANDOFF — DEMO: saved World Plan card projection

> This is a concrete product design, currently BLOCKED. It grants no runtime or
> implementation write lease. PR #886 merged at
> `4efada56aa93d529bf49128d82ba2d097b074af1` from tested head
> `502b54d713e32e48f160182170c87b4f41fca990`; its geometry gate passed and its
> Page lease is released. PRIME assigned RAKE the parser-conformance repair.
> Card implementation remains blocked until that gate passes review and PRIME
> pins a fresh ACTIVE handoff.

PRIME reviewed and accepted this initial boundary on 2026-10-04: the Cards view
is a GM-only read-only lens over the same Plan editor draft; supported edits stay
in the existing Document editor and use ordinary Save/fresh reopen. The boundary
is independently useful, but it is not the completed Plan/Play experience and
does not change this handoff's BLOCKED status.

## Status and activation gate

**Status: BLOCKED on RAKE's parser-conformance repair/review and PRIME's exact implementation path activation.**

Buddy `origin/main` is re-anchored at
`4efada56aa93d529bf49128d82ba2d097b074af1`. Current relevant work is:

- PR #886 merged at
  `4efada56aa93d529bf49128d82ba2d097b074af1` from tested head
  `502b54d713e32e48f160182170c87b4f41fca990`. Its focused suite passed 187/187,
  isolated desktop/mobile geometry passed 1/1, and its production Plan
  Page/shell lease is closed.
- PR #904 merged at `fb1c48d622c9d8d404b1dddb5d5f618e03cc7ef0` from reviewed
  head `c355234d1486d8cbc46aa9afa611d6d1340b812c`. Its six-path lease is settled.
- RAKE PR #906 merged at `6feb3059b2da4d2ec29966ce9723f0effc70108f`; its
  mounted-test repair lease is closed.
- PR #907's Plan-to-Playable design merged at
  `d8e861661716d2fa8c1fb1e3e56ef08268d32da8`. It defines a later Plan-to-Run
  contract and its card projection predecessor tests; it does not activate Run
  implementation.
- PRIME assigned RAKE a bounded editor/server parser-conformance repair after
  ARCHITECTURE found that the editor accepts duplicate targets within a v2
  `activates` or `suppresses` list while the existing server parser rejects
  them. RAKE owns the identity-validator/index regression, shared fixtures, and
  Python parser test. Its exact implementation handoff and review are pending;
  DEMO owns no parser or conformance-test paths.
- PR #887 remains DOGFOOD's prototype-only evidence lane. Its private
  corpus/media/state snapshots are not production data or sources to copy.

Before activation, re-fetch Buddy `main` and all open PRs; verify RAKE's
conformance repair and PRIME review; then have PRIME pin exact code/test/style
paths, resource owners, and cumulative authority-sync paths. This BLOCKED
handoff authorizes no implementation branch, code, schema, route, provider,
database, corpus, or runtime changes.

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

### Newly discovered conformance blocker

ARCHITECTURE found a concrete v2 mismatch: the editor-side
`validatePlayableOptionItemAttrs` validates edge IDs and activate/suppress
overlap but does not reject a duplicate target within one `activates` or
`suppresses` list. `indexPlayableStructureV2` consequently accepts that Plan,
while the existing server `derive_play_run_reference_elements_v2` rejects the
same duplicate effect target. The current editor index can therefore accept a
structure that the canonical server parser rejects, which conflicts with this
handoff's proposed canonical, fail-closed card projection.

PRIME chose to retain the canonical, fail-closed card projection and require a
bounded duplicate-edge validator repair plus a shared-fixture conformance witness through editor Markdown
import/index/serialization and the existing Python parser. RAKE owns the
validator and cross-parser proof; the server parser is not called by the UI at
runtime and no Run is started. This card handoff remains BLOCKED until that
repair passes independent review and PRIME pins the separate card implementation
lease. No parser or conformance-test path is authorized to DEMO by this document.

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

Current source evidence at `4efada56aa93d529bf49128d82ba2d097b074af1`:

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
   server Run manifest parser at runtime or invokes Run admission. Before card
   activation, RAKE's validator repair and shared-fixture conformance proof through editor Markdown
   import/index/serialization and the existing Python parser must pass review,
   including valid v1/v2 identity, membership, edge and order parity plus shared
   rejection of the duplicate-edge, unknown/mixed/orphan cases. The first-card
   implementation consumes that accepted conformance result; it does not own
   the parser repair or Python test.
   Full Plan-to-Run runtime and APP-STATE admission remain later work; the
   existing `admit_playable_revision` rejects WorkObjects whose kind is not
   `runbook`.
5. Session 29 remains the intended operator acceptance example after the code
   merges. Until operator use succeeds, no J1–J6 or connected-demo gate is
   closed. Use a synthetic fixture for tests and isolated preview; do not copy
   private DOGFOOD corpora or touch ports 5202/5203.

## Candidate implementation paths — not a write lease

PRIME approved the following candidate implementation paths after the RAKE
conformance gate passes. This remains a design allowlist, not an ACTIVE write
lease; PRIME must re-anchor and pin the exact lease before code starts:

- `apps/live-control-ui/src/planSurface/PlanSurfacePage.tsx` — mount the view
  switch/projection beside the same World-owned editor and pass current identity,
  draft/editor transaction, and Save state. #886 merged and released this path;
  a fresh card lease is still required.
- `apps/live-control-ui/src/planSurface/components/WorldPlanCardProjection.tsx`
  — new marker-derived view component consuming existing indexes.
- `apps/live-control-ui/src/planSurface/components/WorldPlanCardProjection.css`
  — local component styling; do not add global shell/layout rules.
- `apps/live-control-ui/src/planSurface/WorldPlanCardProjection.model.test.ts`
  — new focused projection/failure-matrix tests, if the model is factored out.
- `apps/live-control-ui/src/planSurface/WorldPlanCardProjection.integration.test.tsx`
  — new mounted Save/reopen equivalence witness using synthetic APIs.
- `Docs/Plans/HANDOFF-DEMO-saved-plan-card-projection.md`,
  `Docs/Plans/HANDOFF-DEMO-plan-agent-panel-usability.md`,
  `Docs/Plans/HANDOFF-DEMO-plan-navigation-shell.md`, and
  `Docs/Roadmaps/ROADMAP-demo.md` — record the settled #904/#886 predecessors
  and current serial gate backward-looking in the eventual card implementation
  PR.

Do not modify the existing Playable parsers/indexes or RAKE-owned conformance
paths, API types/routes, database, Graph contracts, generic editor semantics,
shared UI package, or any path outside the candidate list before PRIME pins the
fresh ACTIVE card lease. If new source access or a new public contract is
required, pause and return the exact owner/path/capability question to PRIME.

## Topology and resources

**Topology: serial.** One card implementation PR after RAKE's conformance repair
passes PRIME review and PRIME activates the fresh exact-path lease. #886 has
merged, but no card code PR is authorized before that gate. No stacked or
parallel code PR is authorized.
The #887 prototype remains separate. #907's Plan-to-Run design is an accepted
contract reference, not an active implementation dependency. Keep the current
operator UI/API 5202/8000 and DOGFOOD 5203 reserved. The card implementation
uses mounted mocked tests and a separate synthetic preview; no database,
provider, credentials, private corpus, Graph, or user Plan state is required.

## Stop conditions

Return to PRIME before writing code if:

- RAKE's parser-conformance repair has not passed independent review, or any
  proposed card path is still leased;
- the current editor/parser contract cannot project supported v1/v2 identities
  without changing its public/admission contract;
- the projection cannot reflect the same Tiptap draft and survive supported
  Document edits plus ordinary Save/reopen without adding a second content
  store, identity system, or public API;
- the ordinary World Plan writer cannot save/reopen the resulting exact source;
- unmarked or malformed content would be hidden, normalized, or represented as
  valid cards;
- scope expands into map/location authority, new grammar, API/schema/Graph,
  Run, player visibility, Agent targeting, or another PR.

No acceptance claim may exceed the exact mounted Save/reopen tests, isolated
preview, and operator use actually completed.
