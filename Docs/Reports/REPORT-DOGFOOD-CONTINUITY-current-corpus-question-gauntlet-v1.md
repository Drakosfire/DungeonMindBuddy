# REPORT — DOGFOOD-CONTINUITY: accepted-world question gauntlet v1

**Status:** NOT READY — operator cannot dogfood this World
**Run ID:** `gauntlet-dogfood-not-ready`
**Runtime git SHA:** `ff79374fffad38f07c4ce1807e3037015d74f451`
**Acceptance run:** `execute-2026-09-16T020204Z-6e3b812a`
**World:** `dogfood-current-corpus-acceptance-v1`
**BENCHMARK_REVISION (C1S10):** `rev:6d15a3f9f7d2208d444df1097db0166a`
**Terminal head (lineage only):** `rev:cce8d24621d65a018d3e2922552f56f2`
**Benchmark ID:** `longmont-c1-sessions-01-10-graph-query-v1`
**Agent runtime:** provider=`openai-api` model=`gpt-5.6-luna` api_mode=`chat_completions` source=`agent_trace`
**SEMANTIC MODEL SELECTION:** `HOLD`
**Readiness law:** [`Docs/Design/ACCEPTANCE-dogfood-readiness.md`](../Design/ACCEPTANCE-dogfood-readiness.md) — structural acceptance → product loadability → operator dogfoodability → semantic usefulness → Agent usefulness. A lower-layer PASS cannot override a higher-layer failure.
**Successor:** [`HANDOFF-DOGFOOD-CONTINUITY-published-object-addressability-v1.md`](../Plans/HANDOFF-DOGFOOD-CONTINUITY-published-object-addressability-v1.md) remains **BLOCKED** until this report is durable on `main`. No implementation PR from this evaluation.

## Operator dogfood

If the operator cannot dogfood the accepted World, it is not ready. Structural retrieval PASS is not product readiness.

**dogfood_ready:** `False`

Blockers:

- `hermes_agent` — Hermes Agent runtime was unavailable. HTTP 200 / hermes_graph_agent wrapping a provider/model error is not Agent-ready. The Agent suite STOPPED and is not scored.
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
Agent suite:       STOPPED (not scored)
Agent FULL:        —
Agent PARTIAL:     —
Agent FAIL:        —
A proven:          0
B proven:          0
C proven:          0
ABC-unresolved:    12
D: 0
E: 0
F: 0
```

A/B/C are only counted when the owning boundary is proven. An oracle miss from empty or partial retrieval is `ABC-unresolved`, not a graph-coverage claim.

## Per-question results

| Q | Oracle answerable | Agent grade | Primary failure | Agent tool calls | Source anchors | Short finding |
|---:|---|---|---|---:|---:|---|
| 01 | yes | STOPPED | — | 0 | 0 | Agent STOPPED (agent_runtime_unavailable); gpt-5.6-luna chat_completions 400 BadRequestError |
| 02 | yes | STOPPED | — | 0 | 0 | Agent STOPPED (agent_runtime_unavailable); gpt-5.6-luna chat_completions 400 BadRequestError |
| 03 | no | STOPPED | ABC-unresolved | 0 | 0 | oracle miss; retrieval nodes=0 match_ratio=0.5; ABC-unresolved; Agent STOPPED |
| 04 | no | STOPPED | ABC-unresolved | 0 | 0 | oracle miss; retrieval nodes=0 match_ratio=0.67; ABC-unresolved; Agent STOPPED |
| 05 | no | STOPPED | ABC-unresolved | 0 | 0 | oracle miss; retrieval nodes=0 match_ratio=0.67; ABC-unresolved; Agent STOPPED |
| 06 | no | STOPPED | ABC-unresolved | 0 | 0 | oracle miss; retrieval nodes=0 match_ratio=0.14; ABC-unresolved; Agent STOPPED |
| 07 | yes | STOPPED | — | 0 | 0 | Agent STOPPED (agent_runtime_unavailable); gpt-5.6-luna chat_completions 400 BadRequestError |
| 08 | no | STOPPED | ABC-unresolved | 0 | 0 | oracle miss; retrieval nodes=0 match_ratio=0.67; ABC-unresolved; Agent STOPPED |
| 09 | no | STOPPED | ABC-unresolved | 0 | 0 | oracle miss; retrieval nodes=0 match_ratio=0.5; ABC-unresolved; Agent STOPPED |
| 10 | no | STOPPED | ABC-unresolved | 0 | 0 | oracle miss; retrieval nodes=0 match_ratio=0.67; ABC-unresolved; Agent STOPPED |
| 11 | no | STOPPED | ABC-unresolved | 0 | 0 | oracle miss; retrieval nodes=0 match_ratio=0.4; ABC-unresolved; Agent STOPPED |
| 12 | no | STOPPED | ABC-unresolved | 0 | 0 | oracle miss; retrieval nodes=0 match_ratio=0.75; ABC-unresolved; Agent STOPPED |
| 13 | yes | STOPPED | — | 0 | 0 | Agent STOPPED (agent_runtime_unavailable); gpt-5.6-luna chat_completions 400 BadRequestError |
| 14 | no | STOPPED | ABC-unresolved | 0 | 0 | oracle miss; retrieval nodes=0 match_ratio=0.75; ABC-unresolved; Agent STOPPED |
| 15 | no | STOPPED | ABC-unresolved | 0 | 0 | oracle miss; retrieval nodes=0 match_ratio=0.44; ABC-unresolved; Agent STOPPED |
| 16 | no | STOPPED | ABC-unresolved | 0 | 0 | oracle miss; retrieval nodes=0 match_ratio=0.6; ABC-unresolved; Agent STOPPED |

## Qualitative findings

### Identity continuity

Q11 oracle miss (ABC-unresolved); Agent STOPPED

### Multi-hop connectivity

Q06 oracle miss (ABC-unresolved); Agent STOPPED, Q07 Agent STOPPED (not scored), Q08 oracle miss (ABC-unresolved); Agent STOPPED

### Ordered path retrieval

Q09 oracle miss (ABC-unresolved); Agent STOPPED

### Learned encounter facts

Q10 oracle miss (ABC-unresolved); Agent STOPPED

### Source / play-vs-plan authority

Q14 oracle miss (ABC-unresolved); Agent STOPPED, Q16 oracle miss (ABC-unresolved); Agent STOPPED

### Broad campaign-state investigation

Q15 oracle miss (ABC-unresolved); Agent STOPPED

### Bounded inference / abstention quality

Q16 oracle miss (ABC-unresolved); Agent STOPPED

## Safeguards

- Retrieval harness ready (C1S10 pin): `True`
- Agent smoke ok: `False`
- dogfood_ready: `False`
- Head before: `rev:cce8d24621d65a018d3e2922552f56f2`; head after: `rev:cce8d24621d65a018d3e2922552f56f2`
- Head unchanged: `True`
- Gold SHA256: `87187a52cf32ce505ffb9cc91944d0c2249e44f85e2971c0785294405d29b62d`

## Interpretation

Operator dogfood is the readiness gate. Oracle-answerable vs Agent FULL is diagnostic only: a large gap points to Agent orchestration/synthesis; a low oracle count points to graph coverage/publication/authority. Neither structural score can override a dogfood blocker. The Agent suite is not scored when the runtime prerequisite fails. A low oracle-answerable count is not, by itself, a proven graph-coverage failure (A); those misses remain ABC-unresolved until an owning-boundary check exists. This report does not select a semantic model. Production defects discovered here are handbacks, not repairs in this lane.

## Handbacks (production; not repaired in this evaluation lane)

- **Published objects are not product-loadable.** C2S22 Mireward exists in `graph_payload` as `node:location:mireward` but search/object/complete-object/evidence all return empty / `found: false`. Candidate IDs stay `loc:mireward`. Graph Review quote-in-span (`evidence[2]`) cannot be validated against a product object the UI cannot open.
- **Agent runtime unavailable (STOP).** Hermes `/api/live/query` returned HTTP 200 / `hermes_graph_agent` wrapping `openai-api` / `gpt-5.6-luna` / `chat_completions` 400 `BadRequestError` before any tool call. The Agent suite is STOPPED and not scored. That is a provider/model prerequisite failure, not D. HTTP 200 / `hermes_graph_agent` / `partial` is not Agent-ready.
- **Default World targeting is `eldyrwild`.** The accepted World id is `dogfood-current-corpus-acceptance-v1`. Without an explicit world-id override the operator cannot open this World in the UI.
- **World-union projection rejects empty `campaignId`.** Selecting C1+C2 has historically failed with `Projection campaign does not match requested campaign longmont-c2`. That is a product verifier defect.

