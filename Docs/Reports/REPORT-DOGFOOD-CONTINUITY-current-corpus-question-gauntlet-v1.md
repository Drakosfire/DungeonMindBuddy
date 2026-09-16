# REPORT — DOGFOOD-CONTINUITY: accepted-world question gauntlet v1

**Status:** NOT READY — operator cannot dogfood this World
**Run ID:** `gauntlet-compliant-stop-v1`
**Runtime git SHA:** `561c28a9e5f131f7dfc167a11ceadd6ac05f4d92`
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
oracle answerable: not started (STOP before Q01)
Agent suite:       STOPPED (not scored)
Agent FULL:        —
Agent PARTIAL:     —
Agent FAIL:        —
A/B/C proven:      not started
ABC-unresolved:    not started
D/E/F:             not started
```

Q01–Q16 were not started. Agent backend/provider unavailable → STOP.

## Historical diagnostic (superseded; not the canonical score)

Pre-fix run `gauntlet-dogfood-not-ready` at `ff79374fffad38f07c4ce1807e3037015d74f451` walked Q01–Q16 after Agent smoke failed and observed oracle answerable 4 / 16. That walk violated handoff §5. Pre-fix capture that began Q01–Q16 after Agent smoke failed. Not the canonical score of a handoff-compliant run. It is diagnostic evidence only.

## Safeguards

- Retrieval harness ready (C1S10 pin): `True`
- Agent smoke ok: `False`
- dogfood_ready: `False`
- Head before: `rev:cce8d24621d65a018d3e2922552f56f2`; head after: `rev:cce8d24621d65a018d3e2922552f56f2`
- Head unchanged: `True`
- Gold SHA256: `87187a52cf32ce505ffb9cc91944d0c2249e44f85e2971c0785294405d29b62d`
- Q01–Q16 started: `False` (handoff §5: STOP before Q01 unless Agent readiness is green)

## Interpretation

Operator dogfood is the readiness gate. This compliant run STOPs before Q01 when Agent readiness fails, so oracle-answerable is not a current score. A pre-fix 4/16 oracle walk exists only as superseded diagnostic evidence. Neither that historical walk nor a structural retrieval PASS can override a dogfood blocker. This report does not select a semantic model. Production defects discovered here are handbacks, not repairs in this lane.

## Handbacks (production; not repaired in this evaluation lane)

- **Published objects are not product-loadable.** C2S22 Mireward exists in `graph_payload` as `node:location:mireward` but search/object/complete-object/evidence all return empty / `found: false`. Candidate IDs stay `loc:mireward`. Graph Review quote-in-span (`evidence[2]`) cannot be validated against a product object the UI cannot open.
- **Agent runtime unavailable (STOP).** Hermes `/api/live/query` returned HTTP 200 / `hermes_graph_agent` wrapping `openai-api` / `gpt-5.6-luna` / `chat_completions` 400 `BadRequestError` before any tool call. The Agent suite is STOPPED and not scored. That is a provider/model prerequisite failure, not D. HTTP 200 / `hermes_graph_agent` / `partial` is not Agent-ready.
- **Default World targeting is `eldyrwild`.** The accepted World id is `dogfood-current-corpus-acceptance-v1`. Without an explicit world-id override the operator cannot open this World in the UI.
- **World-union projection rejects empty `campaignId`.** Selecting C1+C2 has historically failed with `Projection campaign does not match requested campaign longmont-c2`. That is a product verifier defect.

