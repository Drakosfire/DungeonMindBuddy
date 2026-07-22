# Roadmap — Threat + Statblock Authoring and Projection

**Status:** ACTIVE IMPLEMENTATION ROADMAP
**Date:** 2026-07-21
**Product/integration design:** [`../Design/DESIGN-threat-statblock-authoring-projection-workflow.md`](../Design/DESIGN-threat-statblock-authoring-projection-workflow.md)
**PR tracker:** [`../Plans/PR-TRACKER-threat-statblock-authoring-projection.md`](../Plans/PR-TRACKER-threat-statblock-authoring-projection.md)
**DungeonBuddy domain boundary:** [`../Design/DECISION-statblock-contract-consumer-boundary.md`](../Design/DECISION-statblock-contract-consumer-boundary.md)
**Campaign Supergraph authority:** [`../Design/ARCHITECTURE-campaign-supergraph.md`](../Design/ARCHITECTURE-campaign-supergraph.md)

## 1. Goal

Turn the existing DungeonMindServer statblock v1 contract and DungeonBuddy World Graph/Plan/Graph Review/combat foundations into one dogfoodable authoring loop:

```text
World Graph context
→ ThreatDraft
→ typed generated candidate
→ review/edit/validate
→ immutable statblock revision
→ governed Threat + binding graph publication
→ exact-revision projections
→ Markdown embed
→ revision workflow
→ combat
→ CDN image binding
```

The roadmap optimizes for small, independently useful, easy-to-review PRs. A PR may cross backend/UI/test layers only when every changed layer proves one invariant.

## 2. Locked sequencing rules

1. Do not reopen or redesign DungeonMindServer's v1 mechanics contract from DungeonBuddy.
2. Establish server-owned transport before UI integration.
3. Establish durable `ThreatDraft` identity before generation.
4. Make candidate review useful before persistence or graph writes.
5. Persist mechanics before proposing a graph binding.
6. Establish the typed graph external-resource/binding contract before publishing the first Threat binding.
7. Use the existing governed graph preview/confirm path; do not invent a statblock-only graph writer.
8. Build one shared semantic renderer; do not create separate candidate, view, Markdown, and combat renderers.
9. Pin exact revisions in Plan placements, embeds, exports, and combat.
10. Images are a parallel/later capability. 3D media is a separate deferred contract.
11. Delete mock/corpus/path-based predecessor behavior when the replacement path becomes production-ready.
12. Every PR names success, failure, reload, retry, and predecessor behavior.

## 3. Workstream IDs and status

Workstream IDs are stable design identifiers. GitHub PR numbers are assigned when a handoff becomes active; do not reserve a long fragile range of future GitHub numbers.

| Slice | Status | Outcome |
|---|---|---|
| `SBW01` | READY | DungeonBuddy backend can call and classify DungeonMind statblock v1 readiness/read operations through one server-owned client. |
| `SBW02` | BLOCKED on SBW01 only for route conventions; domain design ready | Persistent versioned `ThreatDraftV1` CRUD with no generation side effects. |
| `SBW03` | BLOCKED on SBW01+SBW02 | One draft version generates one typed candidate; failure preserves the draft. |
| `SBW04` | BLOCKED on SBW03 | Shared semantic renderer + read-only candidate review workbench; normal UI stops using mock/corpus-first generation. |
| `SBW05` | BLOCKED on SBW04 | Complete-definition typed editing and editor-preview validation. |
| `SBW06` | BLOCKED on SBW05 | Revise/regenerate candidate lineage without mutating drafts or revisions silently. |
| `SBW07` | BLOCKED on SBW05 | Save accepted mechanics as an immutable logical statblock/revision; draft becomes `mechanics_saved`. |
| `SBW08` | READY in parallel after current graph main stabilizes | Typed external-resource node + `ThreatStatblockBinding` edge state in Kernel/projection contracts; no product write yet. |
| `SBW09` | BLOCKED on SBW07+SBW08 and governed graph confirm path | Preview/confirm Threat + exact binding publication with recoverable partial completion. |
| `SBW10` | BLOCKED on SBW09 | Exact-revision Threat Sheet/full statblock read projection opened from graph/Plan. |
| `SBW11` | BLOCKED on SBW10 | Revision-pinned Markdown/Tiptap statblock embed and honest unresolved state. |
| `SBW12` | BLOCKED on SBW10+SBW06 | Append revision, compare, and explicitly upgrade selected bindings/placements. |
| `SBW13` | BLOCKED on SBW10 | Deterministic CombatantSeed and existing combat tracker insertion/reload/drilldown. |
| `SBW14` | BLOCKED on SBW04; may run parallel to SBW07–SBW13 | Generate/select/bind CDN image assets without changing mechanics identity. |
| `SBW15` | DEFERRED on SBW14 dogfood | 3D media contract and asynchronous generation/storage design; no image-field overloading. |

## 4. Critical path

```text
SBW01 backend client/readiness
  → SBW02 ThreatDraft store
  → SBW03 candidate generation
  → SBW04 shared renderer + read-only review workbench
  → SBW05 typed edit + validation
  → SBW07 immutable mechanics save
  → SBW09 Threat + binding graph publish
  → SBW10 exact-revision Threat Sheet
  → SBW11 Markdown/Tiptap embed
  → SBW13 combat adapter
```

Parallel lanes:

```text
SBW08 graph binding contract
  starts after current graph contract is stable
  must finish before SBW09

SBW06 revise/regenerate
  starts after SBW05
  required before SBW12, not before first mechanics save

SBW14 images
  starts after SBW04
  does not block first end-to-end mechanics/graph/combat slice

SBW15 3D
  begins only after image media ownership is dogfooded
```

## 5. Milestones

### Milestone A — Typed candidate is real

Slices: `SBW01–SBW04`.

Exit:

- A persisted ThreatDraft can call DungeonMindServer through the Buddy backend.
- A typed candidate renders through the shared semantic renderer.
- Provider/auth/timeout/validation failures are distinct.
- The normal workbench no longer claims mock or Markdown corpus output is canonical mechanics.

### Milestone B — Human-adjudicated mechanics workflow

Slices: `SBW05–SBW07`.

Exit:

- The GM can edit the complete definition, validate, revise/regenerate, and save one immutable revision.
- Error validation blocks save; warnings remain visible.
- Accepted mechanics survive reload with exact IDs and digest.
- No graph truth is claimed yet.

### Milestone C — World Graph publication

Slices: `SBW08–SBW09`.

Exit:

- The graph has a typed external statblock resource/binding representation.
- The GM previews and confirms a planned GM-visible Threat and binding.
- The graph write is revision-bound and stale-safe.
- Server success + graph failure is recoverable and truthfully displayed.

### Milestone D — Reusable projections

Slices: `SBW10–SBW12`.

Exit:

- Summary/full Threat Sheet and Markdown embed resolve exact revisions.
- Renderer identity is shared across review, full view, and embed.
- New revisions append; old embeds/placements remain pinned.
- Upgrades are explicit and scoped.

### Milestone E — Table operation

Slice: `SBW13`.

Exit:

- The exact accepted revision creates a deterministic combat seed.
- Combat reload/export retains the exact locator and operational snapshot.
- Mutable combat state cannot change mechanics.

### Milestone F — Media

Slices: `SBW14`, then `SBW15` later.

Exit for images:

- Generated/uploaded assets are durable CDN refs.
- The GM selects portrait/token/form roles.
- Asset failure is non-blocking and mechanics digest remains unchanged.

3D exit criteria are intentionally not part of this roadmap's initial product gate.

## 6. End-to-end dogfood gate

Use a real Shepherds' Flock/Mireward scene design rather than a synthetic fixture for the cumulative dogfood:

1. Load Campaign 2 and the intended session/scene focus.
2. Ask Hermes for graph-grounded context on the scene and Shepherds' Flock.
3. Paste a newly authored threat description into a saved draft.
4. Generate a candidate.
5. Edit one attack/effect and validate.
6. Save immutable mechanics.
7. Publish a planned Threat + binding through governed confirmation.
8. Reload from the committed graph revision and open the Threat Sheet.
9. Embed it in the Plan Markdown board and reload.
10. Add it to combat and change runtime state.
11. Add/select an image without changing the revision digest.

## 7. Review discipline

Every implementation handoff must contain:

- one-sentence mission and one invariant;
- exact dependencies and current base SHA at dispatch;
- bounded expected path inventory;
- public/durable contracts introduced or intentionally not introduced;
- success, miss, failure, retry, reload, and stale behavior;
- explicit non-goals and named successors;
- demolition declaration;
- tests at the owning boundary;
- stop conditions that force a design report rather than scope growth.

A PR is too large when it creates two independently usable outcomes, two durable contracts, or two independently revertible migrations.

## 8. Workstream completion

This roadmap is complete when Milestones A–E and image Milestone F pass the cumulative dogfood. `SBW15` remains a separate follow-on roadmap item unless a real 3D product use case and provider/storage contract are selected.
