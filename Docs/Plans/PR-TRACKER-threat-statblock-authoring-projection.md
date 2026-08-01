# PR Tracker — Threat + Statblock Publication, Query, and Placement

**Status:** ACTIVE PUBLICATION-FIRST TRACKER  
**Date:** 2026-08-01  
**Repository anchor:** `35c3d34c6db44371cba81eb65883b2b76e011cad` — current main after merged PR `#469`  
**Latest merged workstream PR:** `#467` — durable exact Threat identity resolution  
**Immediate authority:** [`HANDOFF-sbw09c1-threat-publication-proposal.md`](HANDOFF-sbw09c1-threat-publication-proposal.md); implementation dispatch begins only after this authority merges and the exact immutable `origin/main` SHA is recorded  
**Roadmap:** [`../Roadmaps/ROADMAP-threat-statblock-authoring-projection.md`](../Roadmaps/ROADMAP-threat-statblock-authoring-projection.md)  
**Lifecycle decision:** [`../Design/DECISION-grounded-authored-world-object-lifecycle.md`](../Design/DECISION-grounded-authored-world-object-lifecycle.md)  
**Current re-anchor report:** [`../Reports/REPORT-sbw09c-publication-reanchor-2026-08-01.md`](../Reports/REPORT-sbw09c-publication-reanchor-2026-08-01.md)  
**Accepted-revision prerequisite:** `SATISFIED_BY_OPERATOR_CONFIRMATION` — the GM manually completed create → generate → edit → validate → accept → hard reload → reopen at least twice  
**R0-B evidence:** [`../Reports/MAGIC-MOMENT-R0-B-2026-07-30.md`](../Reports/MAGIC-MOMENT-R0-B-2026-07-30.md) — `IN_PROGRESS`

This tracker is the sequencing authority for the Threat + Statblock workstream. The critical path is accepted mechanics → governed publication → query/hydration → projection → placement → combat. Grounded Hermes authoring remains a parallel enhancement lane.

## 1. Dispatch rules

1. Every implementation PR proves one independently useful capability and one invariant.
2. Stateful, idempotent, partially durable, concurrent, or recoverable workflows require a frozen state/persistence contract and ordered adversarial evidence.
3. No slice silently adds graph writes, mechanics persistence, document mutation, placement mutation, or combat mutation outside its mission.
4. Exact consumers pin exact revision identity; no `latest` fallback.
5. Saved mechanics, publication intent, identity resolution, reviewed proposal, graph publication, projection, placement, and runtime activation remain distinct.
6. Pre-designed handoffs are research until re-anchored to current code, paths, and base SHA.
7. Product dogfood is required at the gate enabled by the slice; unrelated authoring gaps do not block publication-first work.
8. Operator-confirmed product evidence is authoritative when recorded honestly as operator-reported rather than CI-attested.
9. Active handoffs are committed to `main` before external implementation dispatch. Prefer an unnumbered path until a real pull request exists; do not pre-assign a future PR number in tracker or handoff text.
10. A durable proposal is not a commit receipt. Ambiguous commit recovery must have one explicit owner before a graph-writing slice dispatches.

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
| `SBW03` | MERGED `#388` | Exact draft-version candidate generation contract. |
| `SBW04` | MERGED `#397` | Shared semantic renderer and candidate Workbench. |
| `SBW05a–c` | COMPLETE `#398`, `#402`, `#404` | Dedicated editing and authoritative validation. |
| `SBW07 contract/a–c` | COMPLETE `#405–#409` | Immutable accepted mechanics persistence. |
| `SBW06 contract/a–c` | MERGED `#413`, `#417`, `#435`, `#439` | Revise contracts, lineage, durable status, proposal UX, and retry behavior. |
| Dogfood Gate A | MERGED `#425` | Context-aware Workbench create/generate entry. |
| R0 unblockers | MERGED `#454` | Provider-contract sync, timeout alignment, provenance honesty, Hermes UX. |
| Accepted-revision proof | OPERATOR-CONFIRMED | Normal real-provider acceptance and reopen lifecycle completed at least twice. |
| `SBW08` | MERGED `#457` | Strict graph-owned external statblock resource + exact immutable `ThreatStatblockBinding`; reload/projection; no copied mechanics; fail-closed collisions. |
| `SBW09a` | MERGED `#462` | Durable exact-source / expected-parent publication operation; no graph write. |
| `SBW09b` | MERGED `#467` | Exact revision-pinned Threat candidates plus durable explicit create/connect/refuse resolution; no graph write. |

## 3. Current evidence and prerequisite queue

| ID | Status | Mission | Exit / next action |
|---|---|---|---|
| `R0-A` | `OPERATOR_CONFIRMED_PASS` | Real-provider create→generate→edit→validate→accept→reload. | Closed for dispatch. Preserve the 2026-07-29 failure as historical evidence. |
| `R0-B` | `IN_PROGRESS` / PROVISIONAL PASS | Unioned-graph investigation and useful Threat-description authoring. | Capture final trace/verdict; does not block publication. |
| `R0-A-DIAGNOSTICS` | NOT DISPATCHED | Surface validation diagnostics if the product regresses. | Conditional future regression slice only. |
| `ACCEPTED-REVISION-PROOF` | `SATISFIED_BY_OPERATOR_CONFIRMATION` | One exact accepted revision through the normal Workbench. | Closed. |
| `SBW08` | `MERGED #457` | Exact resource/binding graph contract. | Complete. |
| `SBW09a` | `MERGED #462` | Durable no-write publication operation ledger. | Complete. |
| `SBW09b` | `MERGED #467` | Durable exact Threat identity resolution. | Complete; SBW09c1 unlocked. |

## 4. Critical publication queue

The old bundled `HANDOFF-sbw09-governed-threat-binding-publication.md` is superseded. Publication is deliberately split at durable ownership and recovery seams.

| ID | Status | Mission | Notes |
|---|---|---|---|
| `SBW09a` | MERGED `#462` | Durable no-write publication operation ledger. | Historical authority: [`HANDOFF-sbw09a-publication-operation-ledger.md`](HANDOFF-sbw09a-publication-operation-ledger.md). |
| `SBW09b` | MERGED `#467` | Exact Threat identity resolution. | Historical authority: [`HANDOFF-sbw09b-threat-identity-resolution.md`](HANDOFF-sbw09b-threat-identity-resolution.md). |
| `SBW09c1` | ACTIVE HANDOFF / NEXT | Exact durable no-write Threat publication proposal. | Build deterministic create/connect effects, reuse sealed-proposal authority, persist/reload/replay/supersede; no graph write. Authority: [`HANDOFF-sbw09c1-threat-publication-proposal.md`](HANDOFF-sbw09c1-threat-publication-proposal.md). |
| `SBW09c2` | BLOCKED ON `SBW09c1` | Proposal-bound governed commit, durable receipt/recovery, and exact verification. | One Kernel contribution/revision; exact parent; committed-but-unverified honesty; retry reconciles receipt before write. |
| `SBW10a` | BLOCKED ON PUBLICATION | Hermes query and exact mechanics hydration for published Threats. | Query by name, role, capability, relationship, and campaign context; explicit zero/one/many bindings. |
| `SBW10b` | BLOCKED ON `SBW10a` | Compact/full exact-revision Threat projection. | Useful game information first; evidence and scores secondary. |

`MAGIC-D3` proves publication, queryability, hydration, and projection. It blocks placement.

### Publication split invariant

```text
SBW09a: immutable source + expected-parent operation authority
SBW09b: explicit Threat identity resolution attached to that operation
SBW09c1: exact durable no-write reviewed proposal
SBW09c2: proposal-bound commit + exact receipt/recovery + exact verification
```

No successor may rewrite SBW09a's source snapshot, replace SBW09b's identity, repin the parent, copy mechanics, or treat proposal storage as proof a graph commit occurred.

## 5. Placement and shared-capability queue

| ID | Status | Mission | Notes |
|---|---|---|---|
| `SBW11` | RE-AUDIT | Identify only missing Plan hydration/shared-canvas capability. | Original handoff predates current foundations. |
| `SBW12` | PRE-DESIGNED / RE-ANCHOR | Exact Threat/statblock embed with honest unresolved state. | Embed is not placement. |
| `AOW03` | CONTRACT FIRST | Durable `ObjectPlacementV1` plus exact Threat extension. | Threat, binding, revision, host, quantity, role, trigger, notes, local adjustments. |
| `AOW04` | DECOMPOSE | Shared object capability routing from Hermes, graph inspection, Ingest, Build, Plan, and projections. | Surface initiates; owning service performs write. |

`MAGIC-D4` blocks combat integration.

## 6. Combat integration queue

Current truth:

- the server-backed `CombatRosterModule` exists;
- current combat persists to `combat/current_combat.json`;
- combat identity remains legacy `statblock_path` / `statblock_artifact_id` / `statblock_title` shaped;
- exact Threat, binding, accepted revision, and placement lineage are absent;
- corpus-promotion add-to-combat is not the Workbench accepted-revision lifecycle.

| ID | Status | Mission | Notes |
|---|---|---|---|
| `COMBAT01-contract` | DOC-ONLY FIRST | Freeze exact source locator, insertion/idempotency, reload, drilldown, and migration. | Required before runtime code. |
| `COMBAT01` | NEW | Evolve live combat persistence/module to retain Threat/binding/revision/placement lineage. | Runtime HP/initiative/conditions remain independent. |
| `SBW15` | RE-ANCHOR | Deterministic exact-revision or exact-placement `CombatantSeed`. | Not a thin button over legacy state. |

`MAGIC-D5` is the core statblock roadmap completion gate.

## 7. Parallel authoring and usability queue

These do not block `SBW09–SBW10`.

| ID | Status | Outcome |
|---|---|---|
| `R0-B` closeout | PARALLEL | Capture final authoring trace/verdict. |
| `AOW01` | CONTRACT FIRST / PARALLEL | Grounded authored-object context envelope. |
| `AOW02` | PARALLEL | Hermes “Develop as Threat” creates/opens exact ThreatDraft. |
| `AUTHORING-ARTIFACT` | NEW | Stable editable/copyable markdown artifact with separate provenance. |
| `GRAPH-CHIPS` | NEW | Response evidence chips and query node anchors. |
| `AUTHORING-LIBRARY` | DECOMPOSE | Browse/reopen/update ThreatDrafts and accepted mechanics. |
| `SBW06d` | DEFERRED / RE-ANCHOR | Revise from exact accepted locator. |
| `REVISE-UX` | BACKLOG | GM-facing instruction flow; hide transport recovery until needed. |
| `EDITOR-EXPANSION` | BACKLOG | Dedicated speed, attack, damage, and save fields. |
| `HERMES-LIVENESS` | BACKLOG | Honest long-turn state, recovery, and telemetry. |

## 8. Later queue

| ID | Status | Outcome |
|---|---|---|
| `SBW13` | PRE-DESIGNED | Append immutable child revision and compare exact parent/child. |
| `SBW14` | PRE-DESIGNED | Governed adoption for one Threat binding. |
| embed repin successor | UNNUMBERED | Explicitly repin one document embed. |
| placement repin successor | UNNUMBERED | Explicitly repin one placement. |
| `SBW16` | PARALLEL LATER | Optional image generation. |
| `SBW17` | LATER | Durable image selection/binding. |
| `SBW18` | DEFERRED | 3D reconnaissance. |
| `AOW05` | FUTURE PROVING DOMAIN | Item lifecycle through the same architecture. |

## 9. Gate ledger

| Gate | Current status | Capability / dependency |
|---|---|---|
| `R0-A` | `OPERATOR_CONFIRMED_PASS` | Exact accepted revision lifecycle complete |
| `R0-B` | `IN_PROGRESS`; provisional grounding pass | Grounded-authoring enhancement lane |
| `SBW09a` | `MERGED #462` | Exact publication source/parent authority |
| `SBW09b` | `MERGED #467` | Exact Threat identity authority |
| `MAGIC-D1` | DOGFOOD REQUIRED / PARALLEL | Query → grounded description → durable ThreatDraft |
| `MAGIC-D2` | DOGFOOD REQUIRED / PARALLEL | Grounded draft → connected accepted mechanics |
| `MAGIC-D3` | BLOCKED ON `SBW09c1–c2`, `SBW10a–b` | Accepted revision → published/queryable/projectable Threat |
| `MAGIC-D4` | BLOCKED | Same exact Threat placed from relevant surfaces |
| `MAGIC-D5` | BLOCKED | Exact published Threat/placement enters live combat |
| `AOW05` | DEFERRED | Second domain proves general architecture |

## 10. Immediate dispatch logic

```text
merge and re-anchor SBW09c1 handoff authority
→ dispatch SBW09c1 exact durable no-write proposal
→ re-anchor and dispatch SBW09c2 commit/receipt/recovery/verify
→ SBW10a Hermes query + exact hydration
→ SBW10b exact projection
→ dogfood MAGIC-D3
→ AOW03 / AOW04 placement
→ dogfood MAGIC-D4
→ COMBAT01 / SBW15
→ dogfood MAGIC-D5
```

Parallel work may close R0-B and improve grounded authoring, but it does not preempt the critical sequence.

## 11. PR body requirements

Every PR in this workstream states:

- the exact lifecycle segment and gate enabled;
- why the slice is the smallest independently useful capability;
- authority and persistence boundaries;
- current/legacy path retained or demolished;
- success, failure, retry, stale, reload, concurrency, and ambiguous-outcome behavior where applicable;
- tests run and provenance;
- live dogfood still required after merge;
- named successors that remain false.