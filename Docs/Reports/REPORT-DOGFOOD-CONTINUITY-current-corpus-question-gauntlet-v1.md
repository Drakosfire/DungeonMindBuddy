# REPORT — DOGFOOD-CONTINUITY: accepted-world question gauntlet v1

**Status:** NOT READY — operator cannot dogfood this World
**Run ID:** `gauntlet-dogfood-not-ready`
**Runtime git SHA:** `ff79374fffad38f07c4ce1807e3037015d74f451`
**Acceptance run:** `execute-2026-09-16T020204Z-6e3b812a`
**World:** `dogfood-current-corpus-acceptance-v1`
**BENCHMARK_REVISION (C1S10):** `rev:6d15a3f9f7d2208d444df1097db0166a`
**Terminal head (lineage only):** `rev:cce8d24621d65a018d3e2922552f56f2`
**Benchmark ID:** `longmont-c1-sessions-01-10-graph-query-v1`
**SEMANTIC MODEL SELECTION:** `HOLD`
**Readiness law:** [`Docs/Design/ACCEPTANCE-dogfood-readiness.md`](../Design/ACCEPTANCE-dogfood-readiness.md) — structural acceptance → product loadability → operator dogfoodability → semantic usefulness → Agent usefulness. A lower-layer PASS cannot override a higher-layer failure.
**Successor:** [`HANDOFF-DOGFOOD-CONTINUITY-published-object-addressability-v1.md`](../Plans/HANDOFF-DOGFOOD-CONTINUITY-published-object-addressability-v1.md) remains **BLOCKED** until this report is durable on `main`. No implementation PR from this evaluation.

## Operator dogfood

If the operator cannot dogfood the accepted World, it is not ready. Structural retrieval PASS is not product readiness.

**dogfood_ready:** `False`

Blockers:

- `hermes_cannot_answer` — Hermes returned 0 FULL answers (tool_calls=0). HTTP 200 / hermes_graph_agent is not dogfood if the operator cannot get a usable graph-backed answer.
- `ingested_object_unreadable` — Admitted C2S22 Mireward is not loadable through product reads (seed_status=product_unresolved; candidate=loc:mireward; published=['node:location:mireward']).

### Ingested-object loadability (C2S22 Mireward)

```text
seed_status:     product_unresolved
openable:        False
revision_pin:    rev:24268294e868b30034e247aa9e23087b
identity_remap:  loc:mireward -> ['node:location:mireward']
payload_ids:     ['node:location:mireward']
search_world:    empty
search_campaign: empty
loc:mireward: payload=False product_found=False status=candidate_not_admitted
node:location:mireward: payload=True product_found=False status=product_unresolved
```

Graph Review `evidence[2]` quote-in-span cannot be validated until the published object is loadable. Candidate `loc:mireward` has two quotes; the third live extract is not a candidate evidence row.

## Totals

```text
oracle answerable: 4 / 16
Agent FULL:        0 / 16
Agent PARTIAL:     0 / 16
Agent FAIL:        16 / 16
A: 12
B: 0
C: 0
D: 4
E: 0
F: 0
```

## Per-question results

| Q | Oracle answerable | Agent grade | Primary failure | Agent tool calls | Source anchors | Short finding |
|---:|---|---|---|---:|---:|---|
| 01 | yes | FAIL | D | 0 | 0 | DungeonBuddy’s World Graph does not currently contain enough admitted evidence t |
| 02 | yes | FAIL | D | 0 | 0 | DungeonBuddy’s World Graph does not currently contain enough admitted evidence t |
| 03 | no | FAIL | A | 0 | 0 | DungeonBuddy’s World Graph does not currently contain enough admitted evidence t |
| 04 | no | FAIL | A | 0 | 0 | DungeonBuddy’s World Graph does not currently contain enough admitted evidence t |
| 05 | no | FAIL | A | 0 | 0 | DungeonBuddy’s World Graph does not currently contain enough admitted evidence t |
| 06 | no | FAIL | A | 0 | 0 | DungeonBuddy’s World Graph does not currently contain enough admitted evidence t |
| 07 | yes | FAIL | D | 0 | 0 | DungeonBuddy’s World Graph does not currently contain enough admitted evidence t |
| 08 | no | FAIL | A | 0 | 0 | DungeonBuddy’s World Graph does not currently contain enough admitted evidence t |
| 09 | no | FAIL | A | 0 | 0 | DungeonBuddy’s World Graph does not currently contain enough admitted evidence t |
| 10 | no | FAIL | A | 0 | 0 | DungeonBuddy’s World Graph does not currently contain enough admitted evidence t |
| 11 | no | FAIL | A | 0 | 0 | DungeonBuddy’s World Graph does not currently contain enough admitted evidence t |
| 12 | no | FAIL | A | 0 | 0 | DungeonBuddy’s World Graph does not currently contain enough admitted evidence t |
| 13 | yes | FAIL | D | 0 | 0 | DungeonBuddy’s World Graph does not currently contain enough admitted evidence t |
| 14 | no | FAIL | A | 0 | 0 | DungeonBuddy’s World Graph does not currently contain enough admitted evidence t |
| 15 | no | FAIL | A | 0 | 0 | DungeonBuddy’s World Graph does not currently contain enough admitted evidence t |
| 16 | no | FAIL | A | 0 | 0 | DungeonBuddy’s World Graph does not currently contain enough admitted evidence t |

## Qualitative findings

### Identity continuity

Q11=FAIL (fail=A)

### Multi-hop connectivity

Q06=FAIL (fail=A), Q07=FAIL (fail=D), Q08=FAIL (fail=A)

### Ordered path retrieval

Q09=FAIL (fail=A)

### Learned encounter facts

Q10=FAIL (fail=A)

### Source / play-vs-plan authority

Q14=FAIL (fail=A), Q16=FAIL (fail=A)

### Broad campaign-state investigation

Q15=FAIL (fail=A)

### Bounded inference / abstention quality

Q16=FAIL (fail=A)

## Safeguards

- Readiness ready: `True`
- Head before: `rev:cce8d24621d65a018d3e2922552f56f2`; head after: `rev:cce8d24621d65a018d3e2922552f56f2`
- Head unchanged: `True`
- Gold SHA256: `87187a52cf32ce505ffb9cc91944d0c2249e44f85e2971c0785294405d29b62d`

## Interpretation

Operator dogfood is the readiness gate. Oracle-answerable vs Agent FULL is diagnostic only: a large gap points to Agent orchestration/synthesis; a low oracle count points to graph coverage/publication/authority. Neither structural score can override a dogfood blocker. This report does not select a semantic model. Production defects discovered here are handbacks, not repairs in this lane.

## Handbacks (production; not repaired in this evaluation lane)

- **Published objects are not product-loadable.** C2S22 Mireward exists in `graph_payload` as `node:location:mireward` but search/object/complete-object/evidence all return empty / `found: false`. Candidate IDs stay `loc:mireward`. Graph Review quote-in-span (`evidence[2]`) cannot be validated against a product object the UI cannot open.
- **Hermes did not use the graph.** Agent smoke was HTTP 200 / `hermes_graph_agent` / `partial`, but Q01–Q16 recorded 0 tool calls and 0 FULL answers. Several questions were oracle-answerable from production retrieval; Hermes still abstained. Smoke is not dogfood.
- **Default World targeting is `eldyrwild`.** The accepted World id is `dogfood-current-corpus-acceptance-v1`. Without an explicit world-id override the operator cannot open this World in the UI.
- **World-union projection rejects empty `campaignId`.** Selecting C1+C2 has historically failed with `Projection campaign does not match requested campaign longmont-c2`. That is a product verifier defect.

