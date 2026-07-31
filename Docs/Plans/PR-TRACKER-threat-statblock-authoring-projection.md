# PR Tracker — Threat + Statblock Publication, Query, and Placement

**Status:** ACTIVE PUBLICATION-FIRST TRACKER  
**Date:** 2026-07-30  
**Repository anchor:** `main` after merged PR `#455` and the PR457 dispatch correction  
**Latest merged workstream PR:** `#454` — R0 reports, Workbench unblockers, Hermes UX  
**Immediate authority:** dispatch [`HANDOFF-pr459-sbw09a-durable-threat-statblock-publication-operation.md`](HANDOFF-pr459-sbw09a-durable-threat-statblock-publication-operation.md)
**Roadmap:** [`../Roadmaps/ROADMAP-threat-statblock-authoring-projection.md`](../Roadmaps/ROADMAP-threat-statblock-authoring-projection.md)  
**Lifecycle decision:** [`../Design/DECISION-grounded-authored-world-object-lifecycle.md`](../Design/DECISION-grounded-authored-world-object-lifecycle.md)  
**Current re-anchor report:** [`../Reports/REPORT-threat-statblock-roadmap-reanchor-2026-07-30.md`](../Reports/REPORT-threat-statblock-roadmap-reanchor-2026-07-30.md)  
**Historical R0-A report:** [`../Reports/MAGIC-MOMENT-R0-A-2026-07-29.md`](../Reports/MAGIC-MOMENT-R0-A-2026-07-29.md) — `FAIL_PRODUCT` before the merged unblockers  
**Accepted-revision prerequisite:** `SATISFIED_BY_OPERATOR_CONFIRMATION` — the GM manually completed create → generate → edit → validate → accept → hard reload → reopen at least twice; exact run IDs were not captured as a checked-in report  
**R0-B evidence:** [`../Reports/MAGIC-MOMENT-R0-B-2026-07-30.md`](../Reports/MAGIC-MOMENT-R0-B-2026-07-30.md) — `IN_PROGRESS`

This tracker is the sequencing authority for the Threat + Statblock workstream. The critical path is accepted mechanics → governed publication → query/hydration → projection → placement → combat. Grounded Hermes authoring is a parallel enhancement lane. The accepted-revision prerequisite is closed by operator confirmation and must not be redispatched as PR457.

## 1. Dispatch rules

1. Every implementation PR proves one independently useful capability and one invariant.
2. Stateful, idempotent, partial-completion, or recoverable workflows require a frozen contract/transition review before code when the contract is not already accepted.
3. No slice silently adds graph writes, mechanics persistence, document mutation, placement mutation, or combat mutation outside its mission.
4. Exact consumers pin exact revision identity; no `latest` fallback.
5. Saved mechanics, graph publication, projection, placement, and runtime activation remain distinct.
6. Existing SBW handoffs must be re-anchored to current paths, contracts, fixtures, and base SHA before dispatch.
7. Product dogfood is required at the gate enabled by the slice; a prior unrelated gate does not block a lane unless it is a real technical prerequisite.
8. Hermes-to-draft convenience work does not block publication when one exact accepted revision already exists.
9. Operator-confirmed product evidence is authoritative for dispatch readiness when recorded honestly as operator-reported rather than CI- or repo-attested evidence.

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
| `Dogfood Gate A` | MERGED `#425` | Context-aware Workbench create/generate entry; historical partial attempt only. |
| PR `#454` | MERGED | R0 reports, current provider-contract sync, timeout alignment, freestanding provenance honesty, and Hermes UX unblockers. |
| `ACCEPTED-REVISION-PROOF` | OPERATOR-CONFIRMED | The GM completed the normal real-provider acceptance and reopen lifecycle at least twice. This is sufficient to dispatch the graph contract; it is not represented as automated or checked-in run evidence. |

## 3. Current evidence and prerequisite queue

| ID | Status | Mission | Exit / next action |
|---|---|---|---|
| `R0-A` | `OPERATOR_CONFIRMED_PASS` | Prove real-provider create→generate→edit→validate→accept→reload. | Closed for dispatch purposes. Preserve the 2026-07-29 failure as historical evidence; do not create another proof-only PR unless a future regression reopens the gate. |
| `R0-B` | `IN_PROGRESS` / PROVISIONAL PASS | Prove unioned-graph investigation and useful Threat-description authoring. | Capture final authoring trace/verdict. Does not block publication-first work. |
| `R0-A-DIAGNOSTICS` | NOT DISPATCHED | Surface field/reference validation diagnostics and classify producer vs consumer ownership. | Conditional future regression slice only; the successful operator runs mean it is not the current next action. |
| `ACCEPTED-REVISION-PROOF` | `SATISFIED_BY_OPERATOR_CONFIRMATION` | Produce one exact accepted revision through the normal Workbench. | `SBW08` is unlocked. Exact IDs remain runtime data rather than checked-in authority. |

## 4. Critical publication queue

`SBW08` is merged and `SBW09a` is delivered. `SBW09b–SBW10` remain bounded successor slices and must be re-anchored before dispatch.

| ID | Status | Mission | Notes |
|---|---|---|---|
| `SBW08` / PR `#457` | MERGED | Freeze exact external-resource identity and `ThreatStatblockBinding`. | Contract only; no product graph write. |
| `SBW09a` / PR `#459` | DELIVERED | Durable publication operation and recoverable partial state. | Begin/reload/reconcile/cancel only; no identity resolution or graph commit. Authority: [`HANDOFF-pr459-sbw09a-durable-threat-statblock-publication-operation.md`](HANDOFF-pr459-sbw09a-durable-threat-statblock-publication-operation.md). |
| `SBW09b` | NEXT SUCCESSOR | Create-new versus connect-existing Threat resolution. | Candidate matches, explicit selection, explicit refusal, no silent merge. |
| `SBW09c` | NEW SPLIT | Governed preview/confirm Threat + exact binding commit. | Existing graph governance path; server success plus graph failure remains recoverable. |
| `SBW10a` | NEW EXPLICIT SLICE | Hermes query and exact mechanics hydration for published Threats. | Query by name, role, capability, relationship, and campaign context. |
| `SBW10b` | RE-ANCHOR FROM OLD `SBW10` | Compact/full exact-revision Threat projection. | Useful game information first; explicit binding-selection behavior. |

`MAGIC-D3` proves publication, queryability, hydration, and projection. It blocks placement.

## 5. Placement and shared-capability queue

| ID | Status | Mission | Notes |
|---|---|---|---|
| `SBW11` | RE-AUDIT | Identify only missing Plan hydration/shared-canvas capability. | Original handoff predates current authoring foundations. |
| `SBW12` | PRE-DESIGNED / RE-ANCHOR | Exact Threat/statblock embed with honest unresolved state. | Embed is not placement. |
| `AOW03` | CONTRACT FIRST | Durable `ObjectPlacementV1` plus exact Threat extension. | Threat, binding, revision, host, quantity, role, trigger, notes, local adjustments. |
| `AOW04` | DECOMPOSE | Shared object capability routing from Hermes, graph inspection, Ingest, Build, Plan, and projections. | Surface initiates; owning service performs write. |

`MAGIC-D4` blocks combat integration.

## 6. Combat integration queue

Current truth:

- the live server-backed `CombatRosterModule` exists;
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

These do not block `SBW08–SBW10` after an exact accepted revision exists.

| ID | Status | Outcome |
|---|---|---|
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
| `R0-A` | `OPERATOR_CONFIRMED_PASS` | Exact accepted revision lifecycle manually completed at least twice; no further proof-only PR required |
| `R0-B` | `IN_PROGRESS`; provisional grounding pass | Grounded-authoring enhancement lane only |
| `MAGIC-D1` | DOGFOOD REQUIRED / PARALLEL | Query → grounded description → durable ThreatDraft |
| `MAGIC-D2` | DOGFOOD REQUIRED / PARALLEL | Grounded draft → connected accepted mechanics |
| `MAGIC-D3` | BLOCKED ON `SBW08–SBW10` | Accepted revision → published/queryable/projectable Threat |
| `MAGIC-D4` | BLOCKED | Same exact Threat placed from relevant surfaces |
| `MAGIC-D5` | BLOCKED | Exact published Threat/placement enters live combat |
| `AOW05` | DEFERRED | Second domain proves general architecture |

## 10. Immediate dispatch logic

```text
dispatch PR457 / SBW08 exact statblock resource + ThreatStatblockBinding contract
→ SBW09a publication operation
→ SBW09b create-or-connect resolution
→ SBW09c governed commit
→ SBW10a Hermes query + exact hydration
→ SBW10b exact projection
→ dogfood MAGIC-D3
→ AOW03 / AOW04 placement
→ dogfood MAGIC-D4
→ COMBAT01 / SBW15
→ dogfood MAGIC-D5
```

Parallel work may close R0-B and improve grounded authoring, but it does not preempt the critical sequence above.

## 11. PR body requirements

Every PR in this workstream states:

- the exact lifecycle segment and gate enabled;
- why the slice is the smallest useful capability;
- authority and persistence boundaries;
- current/legacy path retained or demolished;
- success, failure, retry, stale, and reload behavior;
- tests run;
- live dogfood still required after merge.