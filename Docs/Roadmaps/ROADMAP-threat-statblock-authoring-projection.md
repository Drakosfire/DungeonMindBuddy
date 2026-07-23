# Roadmap — Threat + Statblock Authoring and Projection

**Status:** ACTIVE IMPLEMENTATION ROADMAP  
**Date:** 2026-07-23  
**Integration tip:** `b8dbe68c` on `main` (PR `#381` merge; SBW01–03 landed; Milestone A needs SBW04)  

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
→ committed Plan document hydration
→ pinned Markdown/Tiptap embed
→ immutable child revision + compare
→ one-binding adoption
→ combat
→ image generation
→ durable image selection
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
9. Pin exact revisions in bindings, Plan embeds, placements, exports, and combat.
10. Committed Plan-document read/hydration is a separate prerequisite from the statblock embed node.
11. Appending a child mechanics revision and adopting it for one Threat binding are separate capabilities.
12. Updating a pinned Plan embed or placement to another revision is not owned by the binding-adoption slice and remains a later, separately decomposed capability.
13. Image generation and durable image selection are separate capabilities.
14. Images are non-blocking presentation state. 3D media is a separate deferred contract/reconnaissance item.
15. Delete mock/corpus/path-based predecessor behavior when the replacement path becomes production-ready.
16. Every PR names success, miss, failure, retry, reload, stale, and predecessor behavior where applicable.

## 3. Workstream IDs and status

Workstream IDs are stable design identifiers. GitHub PR numbers are assigned when a handoff becomes active; do not reserve a long fragile range of future GitHub numbers.

| Slice | Status | Outcome |
|---|---|---|
| `SBW01` | MERGED `#386` (`2ab5b28b`, 2026-07-22) | DungeonBuddy backend can call and classify DungeonMind statblock v1 readiness/read operations through one server-owned client. |
| `SBW02` | MERGED `#387` (`0d4831ee`, 2026-07-22) | Persistent versioned `ThreatDraftV1` CRUD with no generation side effects. |
| `SBW03` | MERGED `#388` (`889acf96`, 2026-07-23) | One exact draft version generates one typed candidate; failure preserves the draft. Operation-authority durability journal with Server durable-code terminality. |
| `SBW04` | NEXT — PRE-DESIGNED; re-anchor to tip before dispatch | Shared semantic renderer + read-only candidate review workbench; normal UI stops using mock/corpus-first generation. |
| `SBW05` | PRE-DESIGNED | Complete-definition typed editing and editor-preview validation. |
| `SBW06` | PRE-DESIGNED | Revise/regenerate candidate lineage without mutating drafts or revisions silently. |
| `SBW07` | PRE-DESIGNED | Save accepted mechanics as an immutable logical statblock/revision; draft becomes `mechanics_saved`. |
| `SBW08` | PRE-DESIGNED / PARALLEL | Typed external-resource node + `ThreatStatblockBinding` edge state in Kernel/projection contracts; no product write yet. |
| `SBW09` | PRE-DESIGNED | Preview/confirm Threat + exact binding publication with recoverable partial completion. |
| `SBW10` | PRE-DESIGNED | Exact-revision Threat Sheet/full statblock read projection opened from graph/Plan. |
| `SBW11` | PRE-DESIGNED / EARLY PARALLEL | Registered Plan documents load committed Markdown with revision-aware local-draft precedence; independent of `SBW10`, required before `SBW12`. |
| `SBW12` | PRE-DESIGNED | Revision-pinned Markdown/Tiptap statblock embed and honest unresolved state. |
| `SBW13` | PRE-DESIGNED | Append immutable child revision and compare it to its exact parent; no consumer moves. |
| `SBW14` | PRE-DESIGNED | Governed adoption of one child revision for one Threat binding only. |
| `SBW15` | PRE-DESIGNED | Deterministic CombatantSeed and existing combat tracker insertion/reload/drilldown. |
| `SBW16` | PRE-DESIGNED / PARALLEL | Optional image generation with typed partial outcomes; no durable selection. |
| `SBW17` | PRE-DESIGNED | Durable selected-image binding and renderer slots without changing mechanics identity. |
| `SBW18` | DEFERRED RECONNAISSANCE | Decide/define a separate 3D media/job/storage contract after image dogfood and provider/use-case selection. |

Deferred, deliberately unnumbered successors:

- explicitly repin one existing Plan embed to another exact revision;
- explicitly upgrade one persisted Plan/encounter placement to another exact revision.

These are not `SBW14`. They must be decomposed after the actual document and placement stores are proven; they may become separate slices.

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
  → SBW12 revision-pinned Plan embed
  → SBW15 combat adapter
```

Parallel lanes:

```text
SBW08 graph binding contract
  starts after current graph contract is stable
  must finish before SBW09

SBW11 Plan-document hydration
  can run early after current document/read/write contracts are re-anchored
  is independent of SBW10
  must finish before SBW12

SBW06 revise/regenerate
  starts after SBW05
  required before SBW13, not before first mechanics save

SBW13 append + compare
  starts after SBW06 and accepted-revision read exists
  creates no graph/document/placement/combat mutation

SBW14 one-binding adoption
  starts after SBW13 and governed graph replacement is available
  changes one Threat binding only

SBW16 image generation
  starts after SBW04 and current Server image contract is re-anchored
  does not block first mechanics/graph/combat slice

SBW17 image selection
  starts after SBW16; Threat-owned roles may also require SBW09 context

SBW18 3D reconnaissance
  begins only after image ownership is dogfooded and operator selects a use case/provider
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

### Milestone D — Reusable exact projections and documents

Slices: `SBW10–SBW12`.

Exit:

- Summary/full Threat Sheet resolves an exact binding revision.
- Committed Plan Markdown loads after a fresh browser/session reload.
- The statblock embed stores and reloads an exact revision locator.
- Renderer identity is shared across review, full view, and embed.
- A newer revision does not silently change a binding or document.

### Milestone E — Immutable revision evolution

Slices: `SBW06`, `SBW13`, `SBW14`.

Exit:

- A new candidate can preserve lineage from exact source mechanics.
- A validated child revision appends without changing any consumer.
- The GM compares parent/child revisions.
- One governed Threat binding may adopt the child revision.
- Plan embeds, placements, and combatants remain unchanged.

Explicitly excluded from this milestone: document/placement repinning. Those are later unnumbered successors.

### Milestone F — Table operation

Slice: `SBW15`.

Exit:

- The exact accepted revision creates a deterministic combat seed.
- Combat reload retains the exact locator and operational snapshot.
- Mutable combat state cannot change mechanics or graph truth.

### Milestone G — Image media

Slices: `SBW16–SBW17`.

Exit:

- Optional generation returns typed asset outcomes/warnings without blocking mechanics.
- A GM selects a durable asset for one exact presentation role.
- The selected asset renders after reload.
- Asset selection does not alter mechanics digest.

### Deferred — 3D media

Slice: `SBW18` reconnaissance only.

Exit:

- one user use case and provider decision;
- explicit model formats/MIME and preview relationship;
- job lifecycle and ownership/deletion policy;
- CDN/range/licensing/retention decision;
- recommendation whether to create a later implementation roadmap.

No core completion gate depends on 3D.

## 6. End-to-end dogfood gate

Use a real Shepherds' Flock/Mireward scene design rather than a synthetic fixture:

1. Load Campaign 2 and intended scene/session focus.
2. Ask Hermes for graph-grounded context on the scene and Shepherds' Flock.
3. Paste a newly authored threat description into a saved draft.
4. Generate a candidate.
5. Edit one attack/effect and validate.
6. Save immutable mechanics.
7. Publish a planned Threat + binding through governed confirmation.
8. Reload from the committed graph revision and open the Threat Sheet.
9. Open a registered Plan document from committed Markdown in a fresh browser/session.
10. Embed the exact statblock revision, save, clear local state, and reload.
11. Append a child mechanics revision and prove the existing embed remains pinned.
12. Explicitly adopt the child revision for one Threat binding and prove the embed still remains pinned.
13. Add the selected exact revision to combat and change runtime state.
14. Request image generation and observe typed asset outcomes.
15. Select/bind one durable image and prove mechanics digest is unchanged.

## 7. Review and dispatch discipline

Every implementation handoff contains:

- one-sentence mission and one invariant;
- capability-decomposition decision;
- exact dependencies and current base SHA at dispatch;
- bounded expected path allowlist;
- public/durable contracts introduced or intentionally not introduced;
- success, miss, failure, retry, reload, stale, and predecessor behavior;
- state/fallback, identity, persistence/replay, and predecessor mappings where applicable;
- explicit non-goals and named successors;
- demolition declaration;
- tests at the owning boundary;
- stop conditions requiring a report instead of scope growth;
- final dispatch checklist.

`SBW01` predates the current full template shape but remains complete and dispatch-ready. Dispatch/review automation must not assume identical section numbering without adapting it.

A PR is too large when it creates two independently useful outcomes, two durable contracts, or two independently revertible migrations. Cross-layer code remains one PR when every layer establishes/proves one invariant.

Pre-designed is not ready. Before every later dispatch:

1. pin current merged base SHA;
2. replace expected/fuzzy paths with actual paths;
3. capture real generated OpenAPI/types/fixtures/error payloads;
4. re-anchor graph tokens and contribution/projection contracts;
5. register the implementation PR in the active external-agent loop/plan mechanism;
6. record baseline failures rather than weakening acceptance gates.

## 8. Workstream completion

The core roadmap is complete when Milestones A–F and image Milestone G pass the cumulative dogfood. `SBW18` remains a separate deferred decision item.

Pinned Plan embed/placement upgrade is intentionally outside current completion. First dogfood must prove that users need explicit repinning and reveal whether document and placement storage warrant one or multiple successor slices.
