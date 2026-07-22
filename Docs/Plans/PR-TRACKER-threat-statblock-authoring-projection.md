# PR Tracker — Threat + Statblock Authoring and Projection

**Status:** ACTIVE SLICE / REVIEW AUTHORITY  
**Date:** 2026-07-22  
**Design:** [`../Design/DESIGN-threat-statblock-authoring-projection-workflow.md`](../Design/DESIGN-threat-statblock-authoring-projection-workflow.md)  
**Roadmap:** [`../Roadmaps/ROADMAP-threat-statblock-authoring-projection.md`](../Roadmaps/ROADMAP-threat-statblock-authoring-projection.md)  
**Contract owner:** DungeonMindServer statblock v1; DungeonBuddy consumes generated contracts and owns workflow, projection, graph bindings, Plan documents, media selection, and runtime combat state.

This tracker is the implementation sequencing authority for this workstream. It does not override Campaign Supergraph sequencing for unrelated graph infrastructure.

## 1. Dispatch rules

- Stable slice IDs are `SBW01` through `SBW18`; GitHub PR numbers are assigned only when dispatching.
- Every implementation PR establishes one independently useful capability and one invariant.
- Every handoff after `SBW01` is pre-designed, not immediately dispatch-ready. Re-anchor it to the actual merged predecessor, current paths, current OpenAPI/fixtures, and an immutable base SHA.
- No PR may silently add graph writes, mechanics persistence, document mutation, media selection, or combat mutation when its mission excludes them.
- Any new durable schema must be versioned and fixture-tested.
- Replacement paths are deleted in the PR that makes the replacement production-ready unless a named remaining consumer blocks deletion.
- The complete checked-in handoff is dispatch authority. A PR body summary cannot replace it.
- `SBW01` uses the earlier complete handoff shape. `SBW02+` use the current external-agent capability template; review automation must not assume identical section syntax for `SBW01`.

Required demolition declaration in every implementation PR:

```text
Replaced path:
Deleted in this PR: yes | no
If no, retained reason:
Named remaining consumer:
Required deletion owner:
```

## 2. Sequence summary

| Slice | Status | Dependency | Outcome | Canonical handoff |
|---|---|---|---|---|
| `SBW01` | READY after docs merge/re-anchor | DungeonMindServer v1 merged | Server-owned DungeonMind client, readiness, and typed errors | [`HANDOFF-pr382-statblock-v1-backend-client-readiness.md`](HANDOFF-pr382-statblock-v1-backend-client-readiness.md) |
| `SBW02` | PRE-DESIGNED | `SBW01` | Versioned non-canonical `ThreatDraftV1` CRUD/reload | [`HANDOFF-sbw02-threat-draft-store.md`](HANDOFF-sbw02-threat-draft-store.md) |
| `SBW03` | PRE-DESIGNED | `SBW01–02` | Generate one candidate from one exact draft version | [`HANDOFF-sbw03-generate-candidate-from-draft.md`](HANDOFF-sbw03-generate-candidate-from-draft.md) |
| `SBW04` | PRE-DESIGNED | `SBW03` | Shared semantic renderer + real read-only candidate workbench | [`HANDOFF-sbw04-semantic-renderer-candidate-workbench.md`](HANDOFF-sbw04-semantic-renderer-candidate-workbench.md) |
| `SBW05` | PRE-DESIGNED | `SBW04` | Complete-definition editing + authoritative preview validation | [`HANDOFF-sbw05-typed-candidate-edit-validation.md`](HANDOFF-sbw05-typed-candidate-edit-validation.md) |
| `SBW06` | PRE-DESIGNED | `SBW05` | Revise/regenerate candidate lineage | [`HANDOFF-sbw06-candidate-revise-lineage.md`](HANDOFF-sbw06-candidate-revise-lineage.md) |
| `SBW07` | PRE-DESIGNED | `SBW05` | Persist accepted mechanics as exact immutable first revision | [`HANDOFF-sbw07-persist-accepted-mechanics.md`](HANDOFF-sbw07-persist-accepted-mechanics.md) |
| `SBW08` | PRE-DESIGNED / PARALLEL | Stable current graph contracts | External statblock resource + typed Threat binding graph contract | [`HANDOFF-sbw08-world-graph-statblock-binding-contract.md`](HANDOFF-sbw08-world-graph-statblock-binding-contract.md) |
| `SBW09` | PRE-DESIGNED | `SBW07–08` + governed graph review | Publish planned Threat + exact binding through preview/confirm | [`HANDOFF-sbw09-governed-threat-binding-publication.md`](HANDOFF-sbw09-governed-threat-binding-publication.md) |
| `SBW10` | PRE-DESIGNED | `SBW09` | Exact-revision Threat Sheet/full view | [`HANDOFF-sbw10-exact-revision-threat-sheet.md`](HANDOFF-sbw10-exact-revision-threat-sheet.md) |
| `SBW11` | PRE-DESIGNED / EARLY PARALLEL | Current Plan document contracts; independent of `SBW10` | Committed Plan-document content hydration/reload | [`HANDOFF-sbw11-plan-document-content-hydration.md`](HANDOFF-sbw11-plan-document-content-hydration.md) |
| `SBW12` | PRE-DESIGNED | `SBW10–11` | Revision-pinned Markdown/Tiptap statblock embed | [`HANDOFF-sbw12-revision-pinned-markdown-tiptap-embed.md`](HANDOFF-sbw12-revision-pinned-markdown-tiptap-embed.md) |
| `SBW13` | PRE-DESIGNED | `SBW06` + exact accepted revision read | Append immutable child revision + compare; no binding change | [`HANDOFF-sbw13-append-revision-compare.md`](HANDOFF-sbw13-append-revision-compare.md) |
| `SBW14` | PRE-DESIGNED | `SBW13` + governed graph path | Adopt a child revision for one Threat binding only | [`HANDOFF-sbw14-governed-binding-revision-upgrade.md`](HANDOFF-sbw14-governed-binding-revision-upgrade.md) |
| `SBW15` | PRE-DESIGNED | `SBW10` | Exact-revision CombatantSeed + existing tracker insertion | [`HANDOFF-sbw15-exact-revision-combat-adapter.md`](HANDOFF-sbw15-exact-revision-combat-adapter.md) |
| `SBW16` | PRE-DESIGNED / PARALLEL | `SBW04` + image-capable Server contract | Optional image generation request/outcome | [`HANDOFF-sbw16-optional-image-generation.md`](HANDOFF-sbw16-optional-image-generation.md) |
| `SBW17` | PRE-DESIGNED | `SBW16`; Threat binding context for Threat-owned roles | Durable image selection/binding and rendering | [`HANDOFF-sbw17-durable-image-selection-binding.md`](HANDOFF-sbw17-durable-image-selection-binding.md) |
| `SBW18` | DEFERRED RECONNAISSANCE | `SBW17` dogfood + selected use case/provider | 3D media/job/storage contract decision package | [`HANDOFF-sbw18-3d-media-contract-reconnaissance.md`](HANDOFF-sbw18-3d-media-contract-reconnaissance.md) |

## 3. Critical path and parallel lanes

```text
SBW01 backend client/readiness
  → SBW02 ThreatDraft store
  → SBW03 candidate generation
  → SBW04 shared renderer + read-only review
  → SBW05 typed edit + validation
  → SBW07 immutable mechanics save
  → SBW09 governed Threat + binding publication
  → SBW10 exact-revision Threat Sheet
  → SBW12 pinned Plan embed
  → SBW15 combat adapter
```

Parallel lanes:

```text
SBW08 graph binding contract → SBW09
SBW11 Plan hydration → SBW12
SBW06 candidate lineage → SBW13 append/compare → SBW14 one-binding adoption
SBW16 image generation → SBW17 durable selection
SBW18 deferred 3D reconnaissance
```

Deferred, deliberately unnumbered capabilities:

```text
explicitly repin one existing Plan embed to another exact revision
explicitly upgrade one persisted Plan/encounter placement to another exact revision
```

These are not owned by `SBW14`. Before dispatch, decompose them according to their actual durable stores and invariants; document and placement upgrades may require separate slices.

## 4. Slice contracts

### SBW01 — Server-owned DungeonMind statblock v1 client and readiness

**Mission:** Establish one DungeonBuddy backend adapter that authenticates to DungeonMindServer statblock v1, reads health/readiness, and translates typed transport failures without exposing credentials or adding product workflow.

**Invariant:** Every later statblock operation crosses one server-owned typed client boundary; no UI or route constructs privileged DungeonMind requests directly.

**Key exclusions:** drafts, generation workflow, workbench UI, persistence, graph writes, Markdown, combat, media.

**Demolition:** none; this establishes a new boundary.

### SBW02 — Versioned ThreatDraft store and CRUD API

**Mission:** Persist and revise one non-canonical threat concept independently of generation/provider/graph state.

**Invariant:** `draft_id` remains stable and every successful authored update increments `version` exactly once.

**Key exclusions:** generation, candidate storage, UI replacement, graph/corpus write, combat, media.

**Demolition:** retain transitional `StatblockDraftArtifactView` until `SBW04` replaces the normal user path.

### SBW03 — Generate candidate from one exact ThreatDraft version

**Mission:** Map one exact draft version to one DungeonMind candidate request and retain candidate lineage without mutating authored concept or graph truth.

**Invariant:** Every candidate reference names exact draft version and request identity; every failure preserves the draft.

**Key exclusions:** renderer/editor, mechanics save, graph, images.

**Demolition:** none until real candidate review exists.

### SBW04 — Shared semantic renderer and read-only workbench

**Mission:** Make a real typed candidate reviewable through one reusable semantic renderer in the existing workbench.

**Invariant:** Displayed mechanics come only from structured contract fields/receipts, never mock or Markdown mechanics.

**Key exclusions:** editing, validation submission, persistence, graph, embed, combat, media generation.

**Demolition:** remove mock/corpus-first normal candidate presentation and promotion/retrieval controls; name any retained consumer.

### SBW05 — Complete-definition editing and validation

**Mission:** Edit one complete generated input definition and validate the exact working digest through the Server.

**Invariant:** Any edit invalidates prior validation; errors/warnings remain tied to exact current digest.

**Key exclusions:** revise/regenerate, mechanics save, graph, embed, combat/media.

**Demolition:** remove any UI claiming Markdown-only edits changed mechanics.

### SBW06 — Candidate revise/regenerate lineage

**Mission:** Create a new candidate from one exact edited definition or accepted revision plus explicit instructions.

**Invariant:** Revision creates a new proposal and never overwrites draft/candidate/revision lineage.

**Key exclusions:** mechanics persistence, graph, compare, media.

**Demolition:** remove any regenerate action that silently replaces current state.

### SBW07 — Persist accepted mechanics

**Mission:** Save one validated complete definition as an exact logical statblock and immutable first revision.

**Invariant:** “Mechanics saved” means exact `(statblock_id, revision_id, digest)` and does not imply graph publication.

**Key exclusions:** Threat node/binding publication, Markdown, combat, media choice.

**Demolition:** corpus promotion is no longer acceptance.

### SBW08 — World Graph external resource/binding contract

**Mission:** Teach graph contribution/Kernel/projection contracts to represent external statblock resources and typed `ThreatStatblockBinding` state without publishing a product Threat.

**Invariant:** Graph traversal can reach exact external mechanics identity while complete definitions remain outside graph storage.

**Key exclusions:** workbench, Server calls, product publication, preferred-revision UI.

**Demolition:** none.

### SBW09 — Governed Threat + exact binding publication

**Mission:** Prepare, review, confirm, and reload a planned Threat plus exact statblock binding through the existing governed graph path.

**Invariant:** Saved mechanics become campaign memory only through proposal-bound human confirmation and atomic Kernel publication.

**Key exclusions:** full Threat Sheet, Markdown, combat, revision adoption, autonomous Hermes commit.

**Demolition:** no statblock-specific graph bypass writer.

### SBW10 — Exact-revision Threat Sheet

**Mission:** Open a graph Threat and compose its identity with the exact selected mechanics revision and media selection.

**Invariant:** Every mechanic shown traces to the exact binding/revision; Threat identity remains distinct.

**Key exclusions:** editing/append, embed node, combat mutation, media generation.

**Demolition:** remove corpus artifact/path canonical lookup for replaced consumers.

### SBW11 — Plan-document content hydration

**Mission:** Reopen a registered Plan document and hydrate committed Markdown with revision-aware local-draft precedence.

**Invariant:** Committed data, starter state, and unsaved local state are never confused or silently overwritten.

**Key exclusions:** statblock node, writer redesign, arbitrary file API, graph.

**Demolition:** none; fixes the read side required for durable embeds.

### SBW12 — Revision-pinned Markdown/Tiptap embed

**Mission:** Store, reload, and render one exact statblock locator as a typed Plan document block.

**Invariant:** Directive/Tiptap attributes round-trip exactly and never resolve latest or copied canonical Markdown.

**Key exclusions:** revision append, embed repinning, placement upgrade, graph binding mutation, combat, media.

**Named deferred successor:** an unnumbered pinned-use upgrade capability for explicitly repinning one Plan embed. Placement upgrades remain separately decomposable and are not part of `SBW14`.

**Demolition:** remove any live embed whose source is copied pending Markdown when replaced.

### SBW13 — Append revision and compare

**Mission:** Fork one exact accepted revision, validate, append an immutable child, and compare it to its parent.

**Invariant:** New mechanics create a new revision; no binding, placement, embed, or combatant moves.

**Key exclusions:** adoption/migration, bulk update, graph mutation, active combat update.

**Demolition:** remove in-place accepted revision mutation semantics.

### SBW14 — Adopt revision for one Threat binding

**Mission:** Govern a replacement of one exact Threat binding from an old revision to a chosen child revision.

**Invariant:** Only the confirmed binding moves; documents, placements, and combatants remain pinned.

**Key exclusions:** append mechanics, embed/placement update, bulk campaign migration, combat update.

**Demolition:** remove any preferred/latest shortcut that bypasses governed binding replacement.

### SBW15 — Exact-revision combat adapter

**Mission:** Derive deterministic combat seeds from one exact revision and add one or more mutable instances to the existing tracker.

**Invariant:** Runtime state is mutable but exact mechanics/provenance are immutable and never written back.

**Key exclusions:** Play redesign, rules automation, graph, revision adoption.

**Demolition:** replace artifact/corpus identity in the normal generated-statblock combat path.

### SBW16 — Optional image generation

**Mission:** Request optional image generation and display typed partial success/failure without selecting campaign media.

**Invariant:** Image outcome is non-blocking presentation output and does not affect mechanics validity/digest.

**Key exclusions:** durable selection, Threat binding, delete/unbind, 3D.

**Demolition:** remove transient/data URI provider image use only where this response path replaces it.

### SBW17 — Durable image selection and binding

**Mission:** Select one durable provider asset for one exact Threat/statblock role and render that choice across reload.

**Invariant:** Selection is a versioned DungeonBuddy presentation record; it never changes mechanics or graph truth implicitly.

**Key exclusions:** generation request, arbitrary URL delete, 3D, mechanics digest, graph write unless separately governed.

**Demolition:** remove transient durable-image state where replaced.

### SBW18 — 3D media contract reconnaissance

**Mission:** Produce the decision/contract package necessary to decide whether one selected 3D use case can become a later implementation roadmap.

**Invariant:** 3D is never represented as an image asset with another extension.

**Key exclusions:** core workflow blocking, premature provider integration, arbitrary uploads, rigging/animation/printing promises.

**Demolition:** none.

## 5. Cumulative proof

After `SBW15` and `SBW17`, add a dogfood report under `Docs/Reports/` proving the Shepherds' Flock/Mireward path:

```text
World Graph/Hermes context
→ saved ThreatDraft
→ typed candidate
→ edit + validation
→ immutable mechanics
→ governed planned Threat + exact binding
→ graph reload + Threat Sheet
→ committed Plan embed + fresh reload
→ combat instance mutation
→ selected image with unchanged mechanics digest
```

The report is evidence, not a replacement for per-PR tests or this tracker.

## 6. External-agent loop registration

This documentation PR does not create implementation-loop judgment records or checklist YAML. At implementation dispatch:

- register the PR in the active plan/tracker mechanism used by the external-agent loop;
- add the relevant `external_pull_requests[]` entry where that workflow expects it;
- pin base/head and owning handoff;
- record judgment and doc-sync atomically after review.

Do not fabricate future PR numbers or green judgment records in this design PR.

## 7. Review corrections applied

A post-draft architecture review identified stale slice IDs left from the earlier 15-slice decomposition. Corrected before dispatch:

- `SBW02`: combat → `SBW15`; media → `SBW16+`; `Kernal` → `Kernel`.
- `SBW04`: Tiptap embed → `SBW12`; combat → `SBW15`.
- `SBW05`: Markdown/Tiptap embed → `SBW12`.
- `SBW11`: explicitly independent of `SBW10`, required before `SBW12`.
- `SBW12`: removed incorrect ownership by `SBW14`; embed/placement repinning is deferred and unnumbered.
- `SBW01`: documented its intentional older handoff-template shape for review tooling.
