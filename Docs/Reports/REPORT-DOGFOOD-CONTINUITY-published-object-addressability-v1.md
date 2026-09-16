# REPORT — DOGFOOD-CONTINUITY: published-object addressability v1

**Status:** STOP — Case B. Native DungeonMind cannot open its own published object. No Buddy read-adapter repair.
**Handoff:** [`HANDOFF-DOGFOOD-CONTINUITY-published-object-addressability-v1.md`](../Plans/HANDOFF-DOGFOOD-CONTINUITY-published-object-addressability-v1.md)
**Implementation branch:** `dogfood-continuity/published-object-addressability-v1`
**Runtime git SHA:** `f95de4c26483b5b556a8f3411e389824c837f3a4` (dispatch base; no production code change)
**World:** `dogfood-current-corpus-acceptance-v1`
**Database:** `dmb_current_corpus_acceptance_v1` @ `127.0.0.1:54329`
**C2S22 loadability pin:** `rev:24268294e868b30034e247aa9e23087b`
**C1S10 benchmark pin:** `rev:6d15a3f9f7d2208d444df1097db0166a`
**Terminal head:** `rev:cce8d24621d65a018d3e2922552f56f2`
**Head before == head after:** `true` (read-only ledger; no graph write)
**PRODUCT OBJECT ADDRESSABILITY:** `FAIL` at the DungeonMind native retrieval/provenance boundary
**OPERATOR DOGFOOD:** `NOT_READY`
**DOGFOOD_READY:** `false`

This slice did **not** change Buddy production reads. Case A was not proven. A Buddy alias, prefix heuristic, or evaluator translation would hide a DungeonMind dependency defect.

---

## Verdict

```text
Case A  Buddy loses/remaps identity while native DungeonMind round-trips
        FALSE — native already misses the published ID

Case B  published object is in the revision payload; native retrieval cannot open it
        TRUE  — STOP

Case C  publication wrote internally inconsistent IDs (map X / assertion Y / evidence Z)
        FALSE as an identity-split. Existence assertion subject is the published object ID.
        The native miss is missing source artifacts behind admitted evidence, not a loc:/node: split.
```

Authorized Buddy repair does not proceed. Steward must route a DungeonMind-owned source-artifact / provenance repair. UI/Hermes/coverage successors remain blocked.

---

## Identity ledger (C2S22)

Captured in-process against the accepted database before any production edit.

| Surface | Identity / result |
|---|---|
| candidate/extract id | `loc:mireward` (not in revision payload) |
| published DungeonMind object id | `node:location:mireward` |
| kind / label | `dnd5e:location` / `Mireward` |
| existence assertion id | `assertion:173cf91e8151e83d` |
| existence subject | `node:location:mireward` (same as published object id) |
| campaign_scope | `longmont-c2` |
| existence evidence_ref | `evidence:artifact:recap:longmont-c2:session-21:ad4ecd013dad:…:span:ad4ecd013dad:16-16:dmv1:5ed30338…` |
| evidence in revision payload | present (`399` evidence_refs) |
| source artifact id | `artifact:recap:longmont-c2:session-21:ad4ecd013dad` |
| `dungeonmind.source_artifacts` row | **missing** (`get_artifact` → `None`) |
| native projection objects at pin | **0** (`dm_union_graph_v6`; payload has **924** objects) |
| native exclusion for published id | `ObjectScopeExclusion(rejections=[], out_of_scope=False, scope_unknown=True)` |
| native exact-object `node:location:mireward` | `found=False`, `gap_codes=['stored_provenance_invalid']` |
| native exact-object `loc:mireward` | `found=False`, no gap (not in payload) |
| native exact-object `location:mireward` | `found=False`, no gap (not in payload) |
| native search `Mireward` | matched `[]` |
| native neighborhood seed published id | empty |
| native evidence(node) published id | `found=False` |
| Buddy projection / search / object / complete-object / neighborhood / evidence | empty / `found=False` / `outcome=empty` for both `loc:mireward` and `node:location:mireward` |
| C1S10 native exact-object published id | `found=False` |
| terminal-head native exact-object published id | `found=False` |

Native request used for the ledger:

```text
WorldGraphProjectionRequestV2
  world_id=dogfood-current-corpus-acceptance-v1
  campaign_id=None
  admissibility=GM
  scope_mode=WORLD_CROSS_CAMPAIGN
  revision_pin=rev:24268294e868b30034e247aa9e23087b
```

Buddy adapter requests used `scopeMode=world` (mapped to the same `WORLD_CROSS_CAMPAIGN` + `campaign_id=None`) and passed `nodeId` through unchanged as DungeonMind `object_id`.

---

## Why this is not a Buddy identity round-trip bug

The gauntlet correctly observed a candidate→published remap:

```text
loc:mireward  →  node:location:mireward
```

That remap is real, but it is not the failing product-read boundary. DungeonMind already stores the durable object as `node:location:mireward`. Buddy `get_object_direct` / `get_complete_object_direct` pass `request.node_id` to `services.retrieval.get_object(..., object_id=request.node_id)` with no prefix rewrite.

Native `WorldGraphRetrievalService.get_object` is an exact dict lookup on the **scoped** projection. The published id is parsed onto the unscoped snapshot, then hidden because provenance cannot be established:

```text
source artifact missing
  → EvidenceScopeVerdict.SCOPE_UNKNOWN
  → object excluded from scoped projection
  → get_object found=False
  → public gap stored_provenance_invalid (no artifact id leaked)
```

World-wide at this pin:

```text
payload objects:                    924
scoped admitted objects:            0
scope_unknown exclusions:           918
in-scope provenance rejections:     6
source_artifacts for this world:    1
evidence_refs in payload:           399
```

The six in-scope rejections are party-registry PCs (`node:ephanna`, `node:bonogo`, `node:caelynn`, `node:baergrom`, `node:stafl`, `node:karsemine`) with `evidence_source_domain_mismatch`. They also do not round-trip.

Making Buddy accept `loc:mireward` as an alias for `node:location:mireward` would still return empty, because native retrieval cannot open the published id.

---

## Compact DungeonMind dependency handback

```text
world_id:     dogfood-current-corpus-acceptance-v1
revision:     rev:24268294e868b30034e247aa9e23087b
object_id:    node:location:mireward
assertion:    assertion:173cf91e8151e83d
evidence:     evidence:artifact:recap:longmont-c2:session-21:ad4ecd013dad:…
artifact:     artifact:recap:longmont-c2:session-21:ad4ecd013dad
native:       found=false, stored_provenance_invalid, scope_unknown
root:         admitted recap evidence is not backed by source_artifacts rows
              (1 source artifact in the whole accepted World vs 399 evidence_refs)
```

This is a DungeonMind source-admission / source-persistence defect observed at the native retrieval boundary. It is not a Buddy wire-ID adaptation defect.

Do not:

- add a Buddy `loc:` / `node:` / `location:` alias table
- prefix-guess unknown ids
- duplicate the object in Buddy
- translate ids only in the evaluator
- mutate or republish the accepted World from this slice

---

## What this slice did and did not do

Did:

- allocate `dogfood-continuity/published-object-addressability-v1` from the ACTIVE dispatch base
- capture the accepted-world identity/read ledger read-only
- classify Case B
- leave `apps/live_control_server/integrations/dungeonmind/world_graph_reads.py` unchanged
- leave the accepted World head unchanged

Did not:

- implement a Buddy round-trip repair
- add a focused Case A regression (the contract is not repairable here)
- open UI / Hermes / coverage work
- claim `PRODUCT OBJECT ADDRESSABILITY = PASS`

---

## Successor for the steward

Design a DungeonMind-owned slice that makes admitted recap evidence resolvable through `source_artifacts` / `source_revisions` at the accepted World, then re-run this exact published-id ledger. Only if native exact-object/search/complete-object then round-trip may a Buddy-owned Case A identity adapter be reconsidered.

Until native retrieval opens `node:location:mireward` at `rev:24268294e868b30034e247aa9e23087b`, CON-READY remains `NOT READY` at product loadability.
