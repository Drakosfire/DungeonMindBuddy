# PR Tracker — Threat + Statblock Publication, Query, and Placement

**Status:** ACTIVE PUBLICATION-FIRST TRACKER  
**Date:** 2026-08-01  
**Repository anchor:** `25ca4b941ce80e9cfa336c41c59667b9a3ed771d` — current `main`; no net file change from the immediately preceding accidental placeholder/revert pair  
**Latest merged Threat implementation:** `#467` — durable exact Threat identity resolution  
**Latest merged Threat authority:** `#471` — SBW09c1 proposal handoff and publication-path re-anchor  
**Immediate implementation authorities:**
- [`HANDOFF-sbw09c1-threat-publication-proposal.md`](HANDOFF-sbw09c1-threat-publication-proposal.md) — exact durable no-write Threat proposal
- [`HANDOFF-sbw09c2a-operation-revision-lookup.md`](HANDOFF-sbw09c2a-operation-revision-lookup.md) — read-only operation-to-revision recovery primitive; dispatch only after its authority merges

**Roadmap:** [`../Roadmaps/ROADMAP-threat-statblock-authoring-projection.md`](../Roadmaps/ROADMAP-threat-statblock-authoring-projection.md)  
**Lifecycle decision:** [`../Design/DECISION-grounded-authored-world-object-lifecycle.md`](../Design/DECISION-grounded-authored-world-object-lifecycle.md)  
**Publication re-anchor:** [`../Reports/REPORT-sbw09c-publication-reanchor-2026-08-01.md`](../Reports/REPORT-sbw09c-publication-reanchor-2026-08-01.md)  
**Accepted-revision prerequisite:** `SATISFIED_BY_OPERATOR_CONFIRMATION`  
**R0-B evidence:** [`../Reports/MAGIC-MOMENT-R0-B-2026-07-30.md`](../Reports/MAGIC-MOMENT-R0-B-2026-07-30.md) — `IN_PROGRESS`

This tracker is the sequencing authority for the Threat + Statblock workstream. The critical path is accepted mechanics → governed publication → query/hydration → projection → placement → combat. Grounded Hermes authoring remains parallel.

## 1. Dispatch rules

1. Every implementation PR proves one independently useful capability and one invariant.
2. Stateful, idempotent, concurrent, partially durable, or recoverable workflows require frozen state/persistence contracts and ordered adversarial evidence.
3. No slice silently adds graph writes, mechanics persistence, document mutation, placement mutation, or combat mutation outside its mission.
4. Exact consumers pin exact revision identity; no `latest` fallback.
5. Saved mechanics, publication intent, identity resolution, reviewed proposal, commit intent/receipt, graph publication, projection, placement, and runtime activation remain distinct.
6. Pre-designed handoffs are research until re-anchored to current code, paths, and base SHA.
7. Product dogfood is required at the gate enabled by the slice; unrelated authoring gaps do not block publication-first work.
8. Operator-confirmed evidence must be labeled as operator-reported rather than CI-attested.
9. Active handoffs are committed to `main` before implementation dispatch.
10. A durable proposal is not a commit receipt.
11. Ambiguous commit recovery must search immutable revision authority by exact operation ID; current head, first match, or retrying against a repinned parent is not recovery.

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
| `SBW03` | MERGED `#388` | Exact draft-version generation. |
| `SBW04` | MERGED `#397` | Shared renderer and candidate Workbench. |
| `SBW05a–c` | COMPLETE `#398`, `#402`, `#404` | Dedicated editing and authoritative validation. |
| `SBW07 contract/a–c` | COMPLETE `#405–#409` | Immutable accepted mechanics persistence. |
| `SBW06 contract/a–c` | MERGED through `#439` | Revise contracts, lineage, durable status, proposal UX, retry. |
| Dogfood Gate A | MERGED `#425` | Context-aware Workbench create/generate entry. |
| R0 unblockers | MERGED `#454` | Provider sync, timeout alignment, provenance honesty, Hermes UX. |
| Accepted-revision proof | OPERATOR-CONFIRMED | Normal acceptance and reopen completed at least twice. |
| `SBW08` | MERGED `#457` | Strict external resource + exact immutable `ThreatStatblockBinding`; no copied mechanics. |
| `SBW09a` | MERGED `#462` | Durable exact-source / expected-parent operation; no graph write. |
| `SBW09b` | MERGED `#467` | Exact Threat candidate review and explicit create/connect/refuse resolution; no graph write. |

## 3. Current evidence and prerequisite queue

| ID | Status | Mission | Exit / next action |
|---|---|---|---|
| `R0-A` | `OPERATOR_CONFIRMED_PASS` | Real-provider create→generate→edit→validate→accept→reload. | Closed unless regression. |
| `R0-B` | `IN_PROGRESS` / provisional pass | Unioned-graph investigation and useful Threat-description authoring. | Capture final trace; does not block publication. |
| `SBW08` | `MERGED #457` | Exact graph resource/binding contract. | Complete. |
| `SBW09a` | `MERGED #462` | Exact source and expected-parent authority. | Complete. |
| `SBW09b` | `MERGED #467` | Exact Threat identity authority. | Complete. |
| `SBW09c1` | ACTIVE HANDOFF; implementation branch empty at its authority anchor | Durable exact no-write publication proposal. | Implement/review/merge. |
| `SBW09c2a` | ACTIVE HANDOFF after this docs authority merges | Public read-only operation→immutable revision lookup. | May implement in parallel with c1; no overlapping production paths. |

## 4. Critical publication queue

The old bundled `HANDOFF-sbw09-governed-threat-binding-publication.md` remains superseded. Publication is split at durable authority and recovery seams.

| ID | Status | Mission | Notes |
|---|---|---|---|
| `SBW09a` | MERGED `#462` | Durable publication operation. | Immutable source snapshot + exact parent. |
| `SBW09b` | MERGED `#467` | Exact Threat identity resolution. | Explicit create/connect/refuse; no automatic identity. |
| `SBW09c1` | ACTIVE / NEXT PRODUCT CAPABILITY | Exact durable no-write Threat publication proposal. | Seal deterministic create/connect effects and persist/replay/supersede without graph mutation. |
| `SBW09c2a` | ACTIVE READ-ONLY PREREQUISITE | Exact operation-to-revision lookup across all immutable revision manifests. | Zero/one/many plural result; head advance/rollback cannot hide a match; no write. |
| `SBW09c2b` | BLOCKED ON `SBW09c1` + `SBW09c2a` | Proposal-bound commit, durable intent/receipt/recovery, and exact verification. | One Kernel merge; receipt persisted before/after audit; crash recovery resolves exact operation ID before any retry. |
| `SBW10a` | BLOCKED ON PUBLICATION | Hermes query and exact mechanics hydration. | Name/role/capability/relationship/context; explicit zero/one/many bindings. |
| `SBW10b` | BLOCKED ON `SBW10a` | Compact/full exact-revision Threat projection. | Useful game information first. |

### Publication split invariant

```text
SBW09a:  immutable source + expected-parent operation authority
SBW09b:  explicit Threat identity authority
SBW09c1: exact durable no-write reviewed proposal
SBW09c2a: public exact operation→immutable revision recovery lookup
SBW09c2b: proposal-bound commit + durable receipt/recovery + exact verification
```

No successor may rewrite source/identity, repin a parent, copy mechanics, treat proposal storage as publication, infer commit from current head, or choose the first revision match.

### Why `SBW09c2a` exists

World Graph revisions immutably retain `operation_ids`; internal storage can enumerate revision IDs and load typed manifests. The public Kernel does not currently expose lookup by operation ID. A crash after head advance but before application receipt persistence therefore cannot be recovered safely when head later advances or rolls back. `SBW09c2a` closes only that read-contract gap. `SBW09c2b` remains the sole Threat commit and receipt owner.

## 5. Placement and shared-capability queue

| ID | Status | Mission |
|---|---|---|
| `SBW11` | RE-AUDIT | Identify only missing Plan hydration/shared-canvas capability. |
| `SBW12` | PRE-DESIGNED / RE-ANCHOR | Exact Threat/statblock embed; embed is not placement. |
| `AOW03` | CONTRACT FIRST | Durable `ObjectPlacementV1` with exact Threat/binding/revision extension. |
| `AOW04` | DECOMPOSE | Shared capability routing; initiating surface does not own writes. |

`MAGIC-D4` blocks combat integration.

## 6. Combat integration queue

Current truth: the server-backed combat roster exists, but durable combat identity remains legacy path/artifact/title shaped; exact Threat/binding/revision/placement lineage is absent.

| ID | Status | Mission |
|---|---|---|
| `COMBAT01-contract` | DOC-ONLY FIRST | Exact source locator, insertion/idempotency, reload, drilldown, migration. |
| `COMBAT01` | NEW | Persist Threat/binding/revision/placement lineage while runtime HP/conditions remain independent. |
| `SBW15` | RE-ANCHOR | Deterministic exact-revision or exact-placement `CombatantSeed`. |

## 7. Parallel authoring and usability queue

| ID | Status | Outcome |
|---|---|---|
| `R0-B` closeout | PARALLEL | Final authoring trace/verdict. |
| `AOW01` | CONTRACT FIRST / PARALLEL | Grounded authored-object context envelope. |
| `AOW02` | PARALLEL | Hermes “Develop as Threat” creates/opens exact draft. |
| `AUTHORING-ARTIFACT` | NEW | Stable editable/copyable markdown artifact with separate provenance. |
| `GRAPH-CHIPS` | NEW | Evidence chips and query node anchors. |
| `AUTHORING-LIBRARY` | DECOMPOSE | Browse/reopen/update drafts and accepted mechanics. |
| `SBW06d` | DEFERRED / RE-ANCHOR | Revise from exact accepted locator. |
| `REVISE-UX` | BACKLOG | GM-facing recovery flow. |
| `EDITOR-EXPANSION` | BACKLOG | Dedicated mechanical fields. |
| `HERMES-LIVENESS` | BACKLOG | Honest long-turn state and telemetry. |

## 8. Later queue

| ID | Status | Outcome |
|---|---|---|
| `SBW13` | PRE-DESIGNED | Immutable child revision and comparison. |
| `SBW14` | PRE-DESIGNED | Governed adoption for one binding. |
| embed/placement repin | UNNUMBERED | Explicitly move one pinned consumer. |
| `SBW16–18` | LATER / DEFERRED | Image generation, durable selection, 3D reconnaissance. |
| `AOW05` | FUTURE PROVING DOMAIN | Item lifecycle proves generality. |

## 9. Gate ledger

| Gate | Status | Dependency |
|---|---|---|
| `R0-A` | `OPERATOR_CONFIRMED_PASS` | Exact accepted revision lifecycle |
| `R0-B` | `IN_PROGRESS` | Parallel grounded-authoring lane |
| `MAGIC-D1` | DOGFOOD REQUIRED / PARALLEL | Query → grounded description → draft |
| `MAGIC-D2` | DOGFOOD REQUIRED / PARALLEL | Grounded draft → accepted mechanics |
| `MAGIC-D3` | BLOCKED ON `SBW09c1`, `SBW09c2a`, `SBW09c2b`, `SBW10a`, `SBW10b` | Published/queryable/projectable Threat |
| `MAGIC-D4` | BLOCKED | Durable placement |
| `MAGIC-D5` | BLOCKED | Exact live-combat activation |
| `AOW05` | DEFERRED | Second domain generality proof |

## 10. Immediate dispatch logic

```text
SBW09c1 proposal implementation  ─┐
                                 ├→ re-anchor and dispatch SBW09c2b commit/receipt/recovery/verify
SBW09c2a operation lookup       ─┘
→ SBW10a exact query/hydration
→ SBW10b exact projection
→ dogfood MAGIC-D3
→ AOW03 / AOW04
→ dogfood MAGIC-D4
→ COMBAT01 / SBW15
→ dogfood MAGIC-D5
```

SBW09c1 and SBW09c2a may proceed in parallel only because their production allowlists do not overlap. If actual c1 implementation touches the Kernel lookup paths, stop c2a and re-anchor.

## 11. PR body requirements

Every PR states the lifecycle segment/gate, smallest useful capability, authority/persistence boundaries, demolition declaration, success/failure/retry/stale/reload/concurrency/ambiguous-outcome behavior, evidence provenance, live dogfood still required, and named successors that remain false.