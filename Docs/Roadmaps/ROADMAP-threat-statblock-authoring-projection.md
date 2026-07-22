# Roadmap — Threat + Statblock Authoring and Projection

**Status:** ACTIVE IMPLEMENTATION ROADMAP  
**Date:** 2026-07-22  
**Product/integration design:** [`../Design/DESIGN-threat-statblock-authoring-projection-workflow.md`](../Design/DESIGN-threat-statblock-authoring-projection-workflow.md)  
**PR tracker:** [`../Plans/PR-TRACKER-threat-statblock-authoring-projection.md`](../Plans/PR-TRACKER-threat-statblock-authoring-projection.md)  
**DungeonBuddy domain boundary:** [`../Design/DECISION-statblock-contract-consumer-boundary.md`](../Design/DECISION-statblock-contract-consumer-boundary.md)  
**Campaign Supergraph authority:** [`../Design/ARCHITECTURE-campaign-supergraph.md`](../Design/ARCHITECTURE-campaign-supergraph.md)

## 1. Goal

Turn the existing DungeonMindServer statblock v1 contract and DungeonBuddy World Graph, Plan, Graph Review, Markdown canvas, and combat foundations into one dogfoodable authoring loop:

```text
World Graph context
→ versioned ThreatDraft
→ typed generated candidate
→ review/edit/validate/revise
→ immutable statblock revision
→ governed Threat + exact binding publication
→ exact-revision Threat Sheet
→ committed Plan document hydration
→ revision-pinned Markdown/Tiptap embed
→ append and compare mechanics revisions
→ explicit one-binding adoption
→ exact-revision combat instances
→ optional image generation
→ durable image selection
```

Three-dimensional media remains a separate deferred contract investigation.

The roadmap optimizes for small, independently useful, easy-to-review PRs. A PR may cross backend, frontend, persistence, and tests only when every changed layer establishes or proves one invariant.

## 2. Locked sequencing rules

1. Do not reopen or redesign DungeonMindServer's v1 mechanics contract from DungeonBuddy.
2. Establish server-owned transport before product workflow.
3. Establish durable `ThreatDraft` identity before generation.
4. Bind every candidate to one exact draft version and request identity.
5. Make real candidate review useful before persistence or graph writes.
6. Edit one complete generated definition; do not introduce sparse patches or a local mechanics schema.
7. Persist mechanics before proposing graph memory.
8. Establish the typed external-resource/binding graph contract before publishing the first real Threat binding.
9. Use the existing governed graph prepare/review/confirm path; never add a statblock-only graph writer.
10. Build one shared semantic renderer for candidate review, accepted views, embeds, and combat drilldown.
11. Make committed Plan-document content reload real before introducing a durable embedded block.
12. Pin exact revisions in graph bindings, Plan embeds, placements, exports, and combat.
13. Separate immutable child-revision creation from adoption by a campaign binding.
14. One binding upgrade must not migrate other Threats, embeds, placements, or combatants.
15. Separate optional image generation from durable image selection/binding.
16. Media selection changes presentation state only; it never changes mechanics digest or graph identity.
17. Treat 3D as a distinct media/job/storage contract, not an extension of image-only `AssetRefV1`.
18. Delete mock, corpus, path-based, or Markdown-first predecessor behavior when the exact replacement becomes production-ready.
19. Every PR names success, miss, unavailable, integrity failure, stale state, retry/replay, persistence, and demolition behavior where applicable.

## 3. Stable slice IDs, dependencies, and handoffs

Stable slice IDs are design identifiers. Only `SBW01` has a tentative GitHub PR number in its current filename; later GitHub PR numbers are assigned at dispatch after the predecessor base is known.

| Slice | Status | Outcome | Canonical handoff |
|---|---|---|---|
| `SBW01` | READY | Server-owned DungeonMind statblock v1 client, readiness, and typed errors. | [`HANDOFF-pr382-statblock-v1-backend-client-readiness.md`](../Plans/HANDOFF-pr382-statblock-v1-backend-client-readiness.md) |
| `SBW02` | BLOCKED on SBW01 route conventions | Versioned, durable, non-canonical `ThreatDraftV1` CRUD. | [`HANDOFF-sbw02-threat-draft-store.md`](../Plans/HANDOFF-sbw02-threat-draft-store.md) |
| `SBW03` | BLOCKED on SBW01+02 | One exact draft version generates one reloadable typed candidate; failure preserves the draft. | [`HANDOFF-sbw03-generate-candidate-from-draft.md`](../Plans/HANDOFF-sbw03-generate-candidate-from-draft.md) |
| `SBW04` | BLOCKED on SBW03 | Shared semantic renderer and real read-only candidate workbench; normal mock/corpus presentation removed. | [`HANDOFF-sbw04-semantic-renderer-candidate-workbench.md`](../Plans/HANDOFF-sbw04-semantic-renderer-candidate-workbench.md) |
| `SBW05` | BLOCKED on SBW04 | Complete-definition typed editing and exact-digest preview validation. | [`HANDOFF-sbw05-typed-candidate-edit-validation.md`](../Plans/HANDOFF-sbw05-typed-candidate-edit-validation.md) |
| `SBW06` | BLOCKED on SBW05 | Model-assisted candidate revise/regenerate with exact source lineage and explicit statuses. | [`HANDOFF-sbw06-candidate-revise-lineage.md`](../Plans/HANDOFF-sbw06-candidate-revise-lineage.md) |
| `SBW07` | BLOCKED on SBW05; SBW06 optional for first save | Idempotently persist one logical statblock and immutable first revision; record exact accepted mechanics ref. | [`HANDOFF-sbw07-persist-accepted-mechanics.md`](../Plans/HANDOFF-sbw07-persist-accepted-mechanics.md) |
| `SBW08` | READY in parallel after graph main stabilizes | Typed external statblock resource node and `ThreatStatblockBinding` graph contract. | [`HANDOFF-sbw08-world-graph-statblock-binding-contract.md`](../Plans/HANDOFF-sbw08-world-graph-statblock-binding-contract.md) |
| `SBW09` | BLOCKED on SBW07+08 and graph confirm | Governed planned Threat + exact binding publication with recoverable partial state. | [`HANDOFF-sbw09-governed-threat-binding-publication.md`](../Plans/HANDOFF-sbw09-governed-threat-binding-publication.md) |
| `SBW10` | BLOCKED on SBW09 | Exact-revision composed Threat Sheet opened from graph/Plan. | [`HANDOFF-sbw10-exact-revision-threat-sheet.md`](../Plans/HANDOFF-sbw10-exact-revision-threat-sheet.md) |
| `SBW11` | READY once current document contracts are re-anchored | Fresh Plan open hydrates committed Markdown with explicit dirty-local precedence. | [`HANDOFF-sbw11-plan-document-content-hydration.md`](../Plans/HANDOFF-sbw11-plan-document-content-hydration.md) |
| `SBW12` | BLOCKED on SBW10+11 | Strict revision-pinned Markdown/Tiptap statblock block with real save/fresh-reload. | [`HANDOFF-sbw12-revision-pinned-markdown-tiptap-embed.md`](../Plans/HANDOFF-sbw12-revision-pinned-markdown-tiptap-embed.md) |
| `SBW13` | BLOCKED on SBW06+07+10 | Append an immutable exact-parent child revision and compare parent/child; no use migrates. | [`HANDOFF-sbw13-append-revision-compare.md`](../Plans/HANDOFF-sbw13-append-revision-compare.md) |
| `SBW14` | BLOCKED on SBW13+graph replacement semantics | Governed adoption of one exact child revision by one exact Threat binding only. | [`HANDOFF-sbw14-governed-binding-revision-upgrade.md`](../Plans/HANDOFF-sbw14-governed-binding-revision-upgrade.md) |
| `SBW15` | BLOCKED on SBW10 | Deterministic exact-revision `CombatantSeedV1`, insertion, reload/export, offline operation, and drilldown. | [`HANDOFF-sbw15-exact-revision-combat-adapter.md`](../Plans/HANDOFF-sbw15-exact-revision-combat-adapter.md) |
| `SBW16` | BLOCKED on SBW04; parallel thereafter | Explicit optional image generation on candidate generate/revise with typed partial outcomes. | [`HANDOFF-sbw16-optional-image-generation.md`](../Plans/HANDOFF-sbw16-optional-image-generation.md) |
| `SBW17` | BLOCKED on SBW10+16 | Versioned image selection for exact Threat/binding roles and composition into existing projections. | [`HANDOFF-sbw17-durable-image-selection-binding.md`](../Plans/HANDOFF-sbw17-durable-image-selection-binding.md) |
| `SBW18` | DEFERRED on SBW17 dogfood and operator choice | Select one 3D use case/provider and define a distinct model/job/storage contract plus split successor handoffs. | [`HANDOFF-sbw18-3d-media-contract-reconnaissance.md`](../Plans/HANDOFF-sbw18-3d-media-contract-reconnaissance.md) |

## 4. Dependency graph

### Core first-use path

```text
SBW01 backend client/readiness
  → SBW02 ThreatDraft store
  → SBW03 exact draft-version generation
  → SBW04 shared renderer + real candidate review
  → SBW05 typed edit + validation
  → SBW07 immutable first mechanics revision
  → SBW09 governed Threat + exact binding publication
  → SBW10 exact-revision Threat Sheet
  → SBW12 pinned Plan embed
  → SBW15 exact-revision combat adapter
```

`SBW12` also requires the document-foundation lane:

```text
current workspace-document/writer contracts
  → SBW11 committed Plan-document hydration
  → SBW12 pinned Plan embed
```

### Parallel and later lanes

```text
Graph contract lane:
  current graph main stabilizes
    → SBW08 external resource + binding contract
    → SBW09 publication

Mechanics iteration lane:
  SBW05
    → SBW06 candidate revise lineage
    → SBW13 append + compare
    → SBW14 one-binding adoption

Media lane:
  SBW04
    → SBW16 optional image generation
  SBW10 + SBW16
    → SBW17 durable image selection
  SBW17 dogfood + operator choice
    → SBW18 3D reconnaissance
```

`SBW14` intentionally changes only one graph binding. Plan-embed/placement bulk or individual upgrade UX remains a later capability and is not required for the first complete dogfood.

## 5. Milestones

### Milestone A — Typed candidate is real

Slices: `SBW01–04`.

Exit:

- DungeonBuddy has one server-owned authenticated v1 client and honest readiness.
- A durable ThreatDraft survives reload and provider failure.
- One exact draft version generates one traceable candidate.
- The shared renderer presents real typed mechanics.
- The normal workbench no longer presents mock/corpus Markdown as canonical mechanics.

### Milestone B — Human-adjudicated mechanics workflow

Slices: `SBW05–07`.

Exit:

- Complete-definition edits preserve all typed structures.
- Validation applies to one exact digest and stale receipts cannot save.
- Revise/regenerate creates new candidate lineage rather than overwriting.
- One immutable logical statblock/revision survives reload with exact IDs and digest.
- UI says `mechanics_saved`, not published Threat.

### Milestone C — World Graph publication

Slices: `SBW08–09`.

Exit:

- External mechanics identity and typed binding metadata round-trip through Kernel/projection contracts.
- The GM previews and confirms a planned GM-visible Threat and exact binding.
- Existing-object resolution avoids duplicates.
- Stale or failed graph publication leaves saved mechanics intact and recoverable.
- Exact committed graph revision verifies the node and relationship.

### Milestone D — Reusable read and document projections

Slices: `SBW10–12`.

Exit:

- A graph Threat opens one exact composed Threat Sheet through the shared renderer.
- A fresh Plan-document open hydrates committed content instead of starter content.
- The statblock directive/Tiptap node round-trips exact identity.
- Missing/unavailable mechanics retain the locator and never select latest.

### Milestone E — Mechanics evolution without silent migration

Slices: `SBW13–14`.

Exit:

- A validation-clean child revision appends against one exact parent.
- Parent and child remain readable and compare semantically.
- Existing bindings, embeds, placements, and combatants remain pinned after append.
- One chosen Threat binding may adopt the child through governed confirmation.
- No other use migrates automatically.

### Milestone F — Table operation

Slice: `SBW15`.

Exit:

- One exact revision derives one deterministic combat seed.
- Combat save/load/export retains exact locator and bounded snapshot.
- HP, initiative, conditions, and notes mutate only combat state.
- Existing rows remain operational when DungeonMindServer is unavailable; full detail fails honestly.
- The artifact/corpus path is no longer the normal insertion identity.

### Milestone G — Images

Slices: `SBW16–17`.

Exit:

- Image generation is explicit and defaults off.
- Mechanics success remains valid when images partially fail.
- Only typed provider-owned durable image refs are trusted.
- The GM can select an exact image for a typed Threat/binding role.
- Selection survives reload, changes no mechanics digest, and never deletes the provider asset.

`SBW18` is not part of the initial product completion gate.

## 6. End-to-end dogfood gate

Use a real Campaign 2 Shepherds' Flock/Mireward scene rather than a synthetic product example:

1. Select the campaign and intended session/scene World Graph lens in Plan.
2. Ask Hermes for graph-grounded scene and Shepherds' Flock context.
3. Paste the designed threat prose into a saved ThreatDraft.
4. Generate a typed candidate with images off by default.
5. Inspect it through the shared renderer.
6. Edit one attack/effect and validate the exact digest.
7. Optionally revise once and inspect lineage.
8. Save one immutable statblock revision.
9. Preview and confirm a planned GM-visible Threat + exact binding.
10. Reload the exact graph revision and open the Threat Sheet.
11. Insert the pinned statblock block into a Plan document, commit, clear local state/use a fresh browser, and reload it.
12. Append a child revision and compare it without changing the existing embed or combat state.
13. Optionally adopt it for the one Threat binding and prove the embed remains pinned.
14. Add the chosen exact revision to combat; mutate HP/conditions; save/reload; verify mechanics remain unchanged.
15. Generate images explicitly, tolerate a partial failure, select a portrait/token, and reload the Threat Sheet without changing mechanics digest.

Write one cumulative dogfood report under `Docs/Reports/` after `SBW15` and `SBW17`. It is evidence, not a substitute for per-PR tests.

## 7. Review discipline

Every implementation handoff contains:

- §0 capability decomposition;
- one-sentence mission and one invariant;
- exact dependencies and immutable base SHA at dispatch;
- observable-path inventory;
- bounded changed-path allowlist;
- explicit non-goals and named successors;
- state/fallback, identity, persistence/replay, and predecessor mappings;
- irreversible commit/partial-failure semantics where applicable;
- tests at the boundary owning each guarantee;
- minimal live proof using an existing surface;
- demolition declaration;
- stop conditions that require a report rather than scope growth.

A PR is too large when it creates two independently useful outcomes, two public/durable contracts, or two independently revertible migrations—even when it touches only a few files.

Pre-designed handoffs are not automatically ready. At dispatch, the operator/dispatcher must re-anchor:

- current `main` SHA;
- merged predecessor contracts and paths;
- real Server OpenAPI/fixtures;
- current graph token/revision semantics;
- actual baseline test commands;
- any handoff stop condition made true by repository drift.

## 8. Workstream completion

The initial workstream is complete when Milestones A–G pass and the cumulative Shepherds' Flock dogfood is recorded. `SBW18` remains a separate follow-on investigation unless a concrete 3D use case, provider, licensing model, and storage/delivery contract are selected.
