# PR Tracker — Threat + Statblock Publication, Query, and Placement

**Status:** ACTIVE PUBLICATION-FIRST TRACKER  
**Date:** 2026-08-01  
**Repository anchor:** `36def9e102c3e58f0ad00cd8ad7a4fbfe15de594` — re-anchor base for SBW09c2b authority PR `#474` (contains merged `#476` + `#478`)  
**Latest merged Threat implementations:** `#478` — exact durable no-write Threat publication proposal; `#476` — exact contribution-operation-to-immutable-revision lookup  
**Latest merged Threat authority:** `#473` — SBW09c2a exact operation-to-revision lookup handoff  
**Immediate implementation authority:**
- [`HANDOFF-sbw09c2b-threat-publication-commit-recovery.md`](HANDOFF-sbw09c2b-threat-publication-commit-recovery.md) — ACTIVE / NEXT PUBLICATION IMPLEMENTATION; re-anchored against merged c1/c2a; after this authority merges, the implementation PR records that immutable `origin/main` SHA in its body before code changes  
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
11. Ambiguous commit recovery must search immutable revision authority by exact contribution operation ID; current head, first match, or retrying against a repinned parent is not recovery.
12. Once any commit record claims a proposal, proposal supersession must be blocked under the same lifecycle lock.

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
| `SBW09c1` | MERGED `#478` | Exact durable no-write publication proposal; sealed create/connect effect, replay, supersession; no graph write. |
| `SBW09c2a` | MERGED `#476` | Public exact contribution-operation→immutable revision lookup; plural zero/one/many; manifest identity hardening; no write. |

## 3. Current evidence and prerequisite queue

| ID | Status | Mission | Exit / next action |
|---|---|---|---|
| `R0-A` | `OPERATOR_CONFIRMED_PASS` | Real-provider create→generate→edit→validate→accept→reload. | Closed unless regression. |
| `R0-B` | `IN_PROGRESS` / provisional pass | Unioned-graph investigation and useful Threat-description authoring. | Capture final trace; does not block publication. |
| `SBW08` | `MERGED #457` | Exact graph resource/binding contract. | Complete. |
| `SBW09a` | `MERGED #462` | Exact source and expected-parent authority. | Complete. |
| `SBW09b` | `MERGED #467` | Exact Threat identity authority. | Complete. |
| `SBW09c1` | `MERGED #478` | Durable exact no-write publication proposal. | Complete. |
| `SBW09c2a` | `MERGED #476` | Public read-only exact operation→immutable revision lookup. | Complete. |
| `SBW09c2b` | ACTIVE / NEXT PUBLICATION IMPLEMENTATION | Proposal claim, exact commit, durable intent/receipt, recovery, verification. | Merge PR `#474`; open one implementation PR that records the resulting immutable `origin/main` SHA in its body before code. |

## 4. Critical publication queue

The old bundled `HANDOFF-sbw09-governed-threat-binding-publication.md` remains superseded. Publication is split at durable authority and recovery seams.

| ID | Status | Mission | Notes |
|---|---|---|---|
| `SBW09a` | MERGED `#462` | Durable publication operation. | Immutable source snapshot + exact parent. |
| `SBW09b` | MERGED `#467` | Exact Threat identity resolution. | Explicit create/connect/refuse; no automatic identity. |
| `SBW09c1` | MERGED `#478` | Exact durable no-write Threat publication proposal. | Sealed deterministic create/connect effects; persist/replay/supersede without graph mutation. |
| `SBW09c2a` | MERGED `#476` | Exact operation-to-revision lookup across all immutable revision manifests. | Zero/one/many plural result; head advance/rollback cannot hide a match; manifest identity hardening; no write. |
| `SBW09c2b` | ACTIVE / NEXT PUBLICATION IMPLEMENTATION | Proposal-bound commit, durable intent/receipt/recovery, and exact verification. | Authority: [`HANDOFF-sbw09c2b-threat-publication-commit-recovery.md`](HANDOFF-sbw09c2b-threat-publication-commit-recovery.md). After this authority merges, one implementation PR records that immutable `origin/main` SHA in its body and branches from it. |
| `SBW10a` | BLOCKED ON PUBLICATION | Hermes query and exact mechanics hydration. | Name/role/capability/relationship/context; explicit zero/one/many bindings. |
| `SBW10b` | BLOCKED ON `SBW10a` | Compact/full exact-revision Threat projection. | Useful game information first. |

### Publication split invariant

```text
SBW09a:   immutable source + expected-parent operation authority
SBW09b:   explicit Threat identity authority
SBW09c1:  exact durable no-write reviewed proposal
SBW09c2a: public exact contribution-operation→immutable revision recovery lookup
SBW09c2b: proposal claim + exact commit + durable receipt/recovery + exact verification
```

No successor may rewrite source/identity, repin a parent, copy mechanics, treat proposal storage as publication, infer commit from current head, choose the first revision match, or permit proposal supersession after durable commit intent exists.

### Why `SBW09c2a` exists

World Graph revisions immutably retain `operation_ids`; merged Kernel publication records the Graph contribution ID there. The public Kernel previously could not resolve by operation ID, so a crash after head advance but before application receipt persistence was unrecoverable once head moved. Merged PR `#476` closes that read-contract gap with manifest world/revision identity hardening. `SBW09c2b` remains the sole Threat commit and receipt owner.

### Frozen `SBW09c2b` claim boundary

The re-anchored handoff freezes:

- the merged c1 operation-scoped `.proposal.lock`, exposed as `threat_publication_lifecycle_lock`, as the sole proposal/commit lifecycle lock;
- once any valid commit record exists, c1 refuses new-proposal creation and supersession with `publication_proposal_busy` and an explicit commit-claim message (no new c1 result label);
- c1 no-artifact fast paths remain valid only when both the proposal ledger and the commit ledger are absent; an orphaned commit claim fails integrity under the shared lock;
- contribution reconstruction uses `proposal.created_by` as `confirming_principal`; the c2b request actor is commit audit identity only and cannot alter contribution ID;
- intent persisted before the first Kernel merge; exact contribution ID and lifecycle-neutral source digest persisted in the commit record;
- recovery lookup keyed by the exact expected contribution ID (merged Kernel records `operation_ids=[contribution_id]`), not the SBW09a publication operation ID;
- every uncertain Kernel outcome — including typed `published=False` — reconciles through c2a exactly once before terminal classification;
- zero matches plus unchanged parent and full authority revalidation permitting at most one exact retry;
- one exact immutable match requiring core publication-proof checks (parent, integrity load, contribution digest, replay entry); a unique match that fails those checks is ambiguity;
- multiple matches remaining an integrity ambiguity despite deterministic result ordering;
- immediate `committed_unverified` persistence before rebuild/projection audits;
- no merge retry after any committed revision is known;
- response envelopes carrying no sentinel identities.

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
SBW09c1 proposal MERGED #478 ─┐
                              ├→ SBW09c2b handoff re-anchored (PR #474)
SBW09c2a lookup MERGED #476  ─┘
→ merge #474
→ open implementation PR recording that immutable origin/main SHA in its body
→ dispatch SBW09c2b exact commit/receipt/recovery/verify
→ SBW10a exact query/hydration
→ SBW10b exact projection
→ dogfood MAGIC-D3
→ AOW03 / AOW04
→ dogfood MAGIC-D4
→ COMBAT01 / SBW15
→ dogfood MAGIC-D5
```

SBW09c1 and SBW09c2a merged without production-path overlap. SBW09c2b is now the sole next publication implementation; after its authority merges, the implementation PR records that immutable `origin/main` SHA in its body before any c2b code exists.

## 11. PR body requirements

Every PR states the lifecycle segment/gate, smallest useful capability, authority/persistence boundaries, demolition declaration, success/failure/retry/stale/reload/concurrency/ambiguous-outcome behavior, evidence provenance, live dogfood still required, and named successors that remain false.
