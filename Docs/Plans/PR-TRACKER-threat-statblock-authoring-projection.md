# PR Tracker — Grounded Threat + Statblock Magic Moment

**Status:** ACTIVE REANCHORED TRACKER  
**Date:** 2026-07-28  
**Repository anchor:** `main` at `0f6f48ed6502a9a4e69b57f351ae9c795da54694`  
**Latest completed PR:** `#439` — `SBW06c` Workbench revise UX  
**Immediate authority:** restore the real provider and re-run `R0-A`; keep `R0-B` blocked until strict authoritative Graph V1 projection is restored  
**Roadmap:** [`../Roadmaps/ROADMAP-threat-statblock-authoring-projection.md`](../Roadmaps/ROADMAP-threat-statblock-authoring-projection.md)  
**Lifecycle decision:** [`../Design/DECISION-grounded-authored-world-object-lifecycle.md`](../Design/DECISION-grounded-authored-world-object-lifecycle.md)  
**Dogfood runbook:** [`../Runbooks/RUNBOOK-authored-world-object-magic-moment-dogfood.md`](../Runbooks/RUNBOOK-authored-world-object-magic-moment-dogfood.md)  
**Re-anchor report:** [`../Reports/REPORT-threat-statblock-roadmap-reanchor-2026-07-28.md`](../Reports/REPORT-threat-statblock-roadmap-reanchor-2026-07-28.md)  
**Current R0-A report:** [`../Reports/MAGIC-MOMENT-R0-A-2026-07-28.md`](../Reports/MAGIC-MOMENT-R0-A-2026-07-28.md) — `BLOCKED_DEPENDENCY`

This tracker is the sequencing authority for the Threat + Statblock magic-moment workstream. It does not override unrelated Campaign Supergraph or Hermes cleanup sequencing.

## 1. Dispatch rules

1. Dogfood gates are blocking dependencies, not retrospective demos.
2. Every implementation PR proves one independently useful capability and one invariant.
3. Stateful, idempotent, partial-completion, or recoverable workflows require a doc-only contract/transition review before code when the contract is not already frozen.
4. No slice silently adds graph writes, mechanics persistence, document mutation, placement mutation, or combat mutation outside its mission.
5. Exact consumers pin exact revision identity; no latest fallback.
6. Saved mechanics, graph publication, placement, and runtime activation remain distinct states.
7. Pre-designed SBW handoffs must be re-anchored to current paths, contracts, fixtures, and base SHA before dispatch.
8. Every runtime slice names the dogfood gate it enables and the predecessor behavior it removes.

Required demolition declaration:

```text
Replaced path:
Deleted in this PR: yes | no
If no, retained reason:
Named remaining consumer:
Required deletion owner:
```

## 2. Completed foundation

| Slice | Status | Outcome |
|---|---|---|
| `SBW01` | MERGED `#386` | Server-owned DungeonMind statblock client/readiness. |
| `SBW02` | MERGED `#387` | Durable versioned `ThreatDraftV1`. |
| `SBW03` | MERGED `#388` | Exact draft-version candidate generation. |
| `SBW04` | MERGED `#397`; live-provider debt | Shared semantic renderer and candidate Workbench. |
| `SBW05a–c` | COMPLETE `#398`, `#402`, `#404` | Complete-definition editing and validation. |
| `SBW07 contract/a–c` | COMPLETE `#405–#409` | Immutable accepted mechanics persistence. |
| `SBW06 contract/a` | MERGED `#413`, `#417` | Revise contract and revise from edited definition. |
| `Dogfood Gate A` | MERGED `#425` | Context-aware draft create/generate Workbench entry. Historical partial proof only: create succeeded; real-provider generate was unavailable. |
| `SBW06b` | MERGED `#435` | Candidate-ref status and lineage persistence. |
| `SBW06c` | MERGED `#439` | Workbench revise UX, prior proposal inspection, stable retry behavior. Real-provider dogfood was not run. |

## 3. Reboot queue

| ID | Type | Mission | Exit / next action |
|---|---|---|---|
| `R0-A` | `BLOCKED_DEPENDENCY` / DOGFOOD / CONTRACT AUDIT | Prove current real-provider create→generate→edit→validate→revise→accept→reload. | Current agent could not reach the operator runtime/provider. Start configured DMS + Live Control, re-run through the normal Workbench, and replace the blocked report with actual product evidence. No implementation slice is selected yet. |
| `R0-B` | `IN_PROGRESS` / DOGFOOD / HERMES AUDIT | Prove broad query across admitted unioned graph/source context and produce editable grounded Threat description. | Live Hermes probes are now running and recorded in `Docs/Reports/MAGIC-MOMENT-R0-B-2026-07-30.md`. Complete exact revision/session/node/anchor capture and obtain the paste-ready Threat description before marking the gate. |
| `SBW06d` | PRE-DESIGNED; RE-ANCHOR REQUIRED | Revise from exact accepted mechanics locator. | No latest fallback; dispatch only after R0 observations. |
| `AOW01` | NEW; CONTRACT FIRST | Grounded authored-object context envelope. | Exact revision/nodes/source anchors survive handoff. |
| `AOW02` | NEW | Hermes “Develop as Threat” creates/opens exact ThreatDraft. | Enables `MAGIC-D1`. |
| `AUTHORING-LIBRARY` | DECOMPOSE | Browse/reopen/update real ThreatDrafts and accepted mechanics; local recovery as separate slice if needed. | Backend `GET /api/live/threat-drafts` list already exists; Workbench + `liveApi` ThreatDraft list/update clients and accepted-mechanics library UI do not. Record the actual R0-A reopening friction before dispatch. |

## 4. Graph publication queue

Existing `SBW08–SBW10` handoffs are strategic designs, not dispatch-ready implementation instructions.

| ID | Status | Mission | Notes |
|---|---|---|---|
| `SBW08` | PRE-DESIGNED / RE-ANCHOR | Typed external-resource identity and `ThreatStatblockBinding` graph contract. | Contract only; no product write. |
| `SBW09a` | NEW SPLIT | Publication operation/state and recoverable partial completion. | Separate from match resolution and commit. |
| `SBW09b` | NEW SPLIT | Create-new versus connect-existing Threat resolution. | Must expose candidate matches and explicit refusal. |
| `SBW09c` | NEW SPLIT | Governed preview/confirm Threat + exact binding commit. | Existing graph governance path; stale-safe. |
| `SBW10` | PRE-DESIGNED / RE-ANCHOR | Exact-revision Threat projection. | Binding-selection policy must be explicit. |

`MAGIC-D3` blocks cross-surface placement implementation.

## 5. Projection and placement queue

| ID | Status | Mission | Notes |
|---|---|---|---|
| `SBW11` | RE-AUDIT | Identify only the missing Plan document hydration/shared-canvas capability. | Original handoff predates current authoring hook/shared canvas foundation. |
| `SBW12` | PRE-DESIGNED / RE-ANCHOR | Exact statblock revision embed with honest unresolved state. | Embed is not placement. |
| `AOW03` | NEW; CONTRACT FIRST | Durable generic `ObjectPlacementV1` plus Threat placement extension. | Quantity/role/trigger/notes/exact revision. |
| `AOW04` | NEW; DECOMPOSE | Shared object capability routing from Ingest, Build, Plan, and projections. | Surface initiates; owning service performs write. |

`MAGIC-D4` blocks combat integration.

## 6. Combat integration queue

Current truth:

- the original static Mireward page is a harness, not the product;
- a live server-backed `CombatRosterModule` exists;
- current combat persists to standalone `combat/current_combat.json` state (with automatic backups);
- combat entity statblock identity remains legacy `statblock_path` / `statblock_artifact_id` / `statblock_title` shaped;
- exact graph Threat + binding + accepted revision is not authoritative;
- the old Statblock View still offers add-to-combat for corpus-promotion / generated artifacts, but that is not the new Workbench → accepted-revision path;
- exact-revision insertion, reload, and mechanics drilldown from the new lifecycle remain absent.

| ID | Status | Mission | Notes |
|---|---|---|---|
| `COMBAT01-contract` | NEW DOC-ONLY | Freeze exact source locator, insertion/idempotency, reload, drilldown, and migration semantics. | Required before code. |
| `COMBAT01` | NEW | Evolve live combat store/module to retain Threat/binding/revision/placement lineage. | Retain mutable runtime independence. |
| `SBW15` | PRE-DESIGNED / RE-ANCHOR | Deterministic exact-revision or exact-placement `CombatantSeed` and insertion. | Not a thin button over legacy state. |

`MAGIC-D5` is the core roadmap completion gate.

## 7. Later queue

| ID | Status | Outcome |
|---|---|---|
| `SBW13` | PRE-DESIGNED | Append immutable child revision and compare exact parent/child. |
| `SBW14` | PRE-DESIGNED | Governed adoption for one Threat binding only. |
| embed repin successor | UNNUMBERED | Explicitly repin one document embed. |
| placement repin successor | UNNUMBERED | Explicitly repin one durable placement. |
| `SBW16` | PRE-DESIGNED / PARALLEL | Optional image generation. |
| `SBW17` | PRE-DESIGNED | Durable image selection/binding. |
| `SBW18` | DEFERRED | 3D reconnaissance. |
| `AOW05` | FUTURE PROVING DOMAIN | Item Generator through the same lifecycle. |

## 8. Dogfood gate ledger

| Gate | Current status | Capability proved | Blocks |
|---|---|---|---|
| `R0-A` | `BLOCKED_DEPENDENCY` | Existing real statblock dependency path actually works. | `SBW06d` and broad statblock continuation. |
| `R0-B` | `IN_PROGRESS` | Hermes has demonstrated multi-hop investigation and uncertainty honesty; the exact evidence package and paste-ready editable Threat description remain unproved. | `AOW01–02`. |
| `MAGIC-D1` | DOGFOOD REQUIRED | Query → grounded description → durable ThreatDraft handoff. | Full authoring continuation. |
| `MAGIC-D2` | DOGFOOD REQUIRED | Grounded draft → accepted immutable statblock revision. | Graph publication. |
| `MAGIC-D3` | BLOCKED_DEPENDENCY | Accepted revision → governed reusable Threat + binding. | Placement. |
| `MAGIC-D4` | BLOCKED_DEPENDENCY | Same Threat placed from Ingest, Build, and Plan. | Combat integration. |
| `MAGIC-D5` | BLOCKED_DEPENDENCY | Exact graph-backed Threat/placement imported into live combat and reloaded. | Core completion. |
| `AOW05` gate | DEFERRED | Item lifecycle reuses the architecture. | General architecture completion. |

## 9. Immediate next dispatch logic

```text
complete R0-B evidence capture from the live Hermes session
→ ask the bounded authoring follow-up
→ record PASS / PASS_WITH_FRICTION / FAIL with exact artifacts
→ re-anchor one smallest slice from observed friction
→ dispatch only that slice
```

Expected branches after the gates:

- provider/contract mismatch found → narrow consumer contract-sync slice;
- real mechanics path works but normal reopening remains opaque-ID recovery → smallest ThreatDraft browse/reopen client + Workbench library slice;
- local in-progress edits are destroyed by dependency failure → separate local recovery slice;
- Hermes cannot search the required admitted union → narrow retrieval/tooling slice;
- Hermes can answer but cannot preserve context → `AOW01`;
- exact accepted revision revise is the next isolated gap → re-anchor `SBW06d`;
- multiple gaps found → sequence them by the earliest blocked dogfood gate, not by the old SBW numbering alone.

## 10. PR body requirements

Every PR in this workstream states:

- the magic-moment segment it enables;
- the exact dogfood gate affected;
- why the slice is the smallest useful capability;
- authority and persistence boundaries;
- current/legacy path retained or demolished;
- tests run;
- live dogfood still required after merge.
