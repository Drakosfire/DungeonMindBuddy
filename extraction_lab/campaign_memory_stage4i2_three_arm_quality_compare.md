# Stage 4I.2 three-arm GM-quality compare

Zero additional API spend. Derived from isolated stores already written under
`out/stage4i2-reasoning-ablation-d63a688c6bf9/`. This file is the committed,
sanitized review artifact. Full subject-attached facts live in the sibling JSON.

```text
Arms:     deepseek-none · deepseek-low · luna-flex-low
Method:   name/alias match → facts whose subject_entity_id is that entity
Not used: mention-bleed, evaluator LLM, semantic repair
Ratings:  NOT_EVALUATED — this artifact is evidence, not a verdict
```

Do not treat mechanical fact-anchor recall as GM-usable quality. Do not freeze a
Stage 4J ingestion profile from cost/latency/transport alone.

## Companion JSON

`extraction_lab/campaign_memory_stage4i2_three_arm_quality_compare.json`

Schema: `dmb_stage4i2_three_arm_quality_compare_v1`. `evaluator_llm` is false.

## Identity on the freeze list

| Object | DeepSeek none | DeepSeek low | Luna Flex low |
|---|---|---|---|
| Brin Holloway | Brin Holloway [actor] · Holloway [concept] | Brin Holloway [actor] · Brin [actor] · Holloway [group] | Brin Holloway [actor] · Brin [actor] |
| Orik / Orric | Orik Tane · Orik · Mayor Orric Tane | same 3-way split | same 3-way split |
| Karsemine | Karsemine [actor] · cursed idol [object] | same | same |
| Mireward | Reach + Mireward + field packet **+ 3 source-filename entities** | Reach + Mireward + field packet + civilians | Reach + Mireward (place+actor) + field packet |
| Hesta | 1 actor | 1 actor | 1 actor |
| Thrin | 1 actor | 1 actor | 1 actor |
| Tripod | 5 fragments | 3 fragments | 7 fragments |
| Refugees | Survivors [group] · Refugee camp · Edge support wave | Edge support wave only | Edge support wave only |
| Ironveil Warehouse | Warehouse + generic `the warehouse` | Warehouse + `The Warehouse` | Warehouse + `warehouse` |
| The Mayor (bare title) | minted (`the mayor`) | minted (`The Mayor`) | absent |

The Orik/Orric/Mayor split is not DeepSeek-specific.

## Structural observations (not scores)

- All three arms keep Brin’s grounded roles (`cook from Edge`, column/refugee lead). None collapsed to generic “wants to help.”
- DeepSeek none and Luna attach `defenses: resistant to poison, weak to fire` on a Tripod entity. DeepSeek low only records that discovery as a Karsemine Hunter’s Mark event, so the Tripod card cannot answer the question.
- Luna is the noisiest Tripod identity (7 fragments). DeepSeek none is the noisiest Mireward identity (source filenames as entities).
- DeepSeek minted a bare The Mayor; Luna did not.
- Hesta stays one actor everywhere. Luna is the only card that keeps “gave the five sleep potions on hand” on Hesta herself.

## Rating rubric (still empty)

For each object × arm, rate 0–2:

```text
identity coherence
continuity-critical factual completeness
specificity / source grounding
GM-facing prose usefulness
noise / unnecessary facts
```

Forcing questions:

```text
If this object appeared beside Session Prep right now, would I trust it
enough to plan from without reopening the recap?

Does the representation retain minor declared facts strongly enough that a
later planning operation could detect a contradiction?
```

Until those ratings exist, the paid screen answers cost, latency, transport
reliability, and rough recall — not the core GM question.
