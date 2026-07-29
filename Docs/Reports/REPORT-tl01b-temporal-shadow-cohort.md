# REPORT — TL01B temporal shadow cohort

**Status:** Live provider run completed (post semantic-comparator fix)  
**Repository SHA (implementation base):** `d6ea4959c9bcc2f113ef50d912629864c1a1c04b`  
**Evaluation verdict:** `ITERATE_PROMPT`

## Cohort matrix

| # | Scenario | Gold |
| --- | --- | --- |
| 1 | Stafl revives Caelynn (Session 7 L14) | `resolved` occurrence `session-7` |
| 2 | Lysandra assigned to lead (Session 13 L18) | `resolved` valid from `session-13` |
| 3 | Hybrid destroyed (Session 24 L14) | `resolved` occurrence `session-24` |
| 4 | Party scene (Session 12 L14) | `not_applicable` |
| 5 | Road edge + legacy `session-22` scope | `not_applicable` |
| 6 | Maelthor password mention (Session 6 L18) | `ambiguous` |

## Missing corpus categories

- Relative-historical exile / explicit “long ago” recap span: **not found** in Campaign 2 recaps.

## Live run

| Field | Value |
| --- | --- |
| Case ID | `tl01b-temporal-shadow-cohort-v1` |
| Base contribution ID | `contribution:8408dabc602b750f` |
| Model | `gpt-5.4-mini` |
| Prompt version (executed) | `tl01b-v1` |
| Provider response ID | `resp_0a6675d8572b4db4006a6a6d3f2f208193b46c09a6bc7b51ec` |
| Selected assertions | 6 |
| Overlay ID | `temporal-overlay:bf373a6dfad16df2` |
| Run ID | `temporal-shadow-run:7bab9f6b9bddcca9` |
| Preview verdict | `complete` |
| Comparison verdict | `fail` |
| Evaluation verdict | `ITERATE_PROMPT` |
| Input tokens | 3525 |
| Output tokens | 893 |
| Elapsed ms | ~5154 |
| Cost | not reported by client |

Artifacts (local, not committed): `evals/graph_memory_layer/artifacts/temporal_shadow_cohort/live-run/`

## Metrics (live vs gold, semantic comparator)

Comparison ignores annotation ID, producer identity, diagnostic wording, source-phrase wording, and extraction confidence. Equality uses interpretation status, occurrence/valid-time payloads, and normalized evidence selection.

| Metric | Count |
| --- | ---: |
| Exact match | 1 |
| Wrong temporal value (same status) | 3 |
| Wrong temporal lane | 0 |
| Unsafe over-resolution | 2 |
| Safe under-resolution | 0 |
| Other status mismatch | 0 |
| Missing / extra | 0 / 0 |

## Strengths

- Infrastructure completed end-to-end: sealed digests → owned spans → Responses API strict schema → TL01 overlay → preview.
- Target set exact; no foreign-evidence or missing-target failures.
- Preview verdict `complete` (no skipped unresolved schemas).
- Semantic comparator no longer mislabels metadata/ID drift as temporal error (prior contaminated 0/6 exact matches).
- One true `exact_match` on a `not_applicable` negative-provenance row.

## Failure modes

- Three resolved rows with same status but wrong temporal value.
- Two **unsafe over-resolutions**: gold `not_applicable`/`ambiguous` predicted as `resolved`.
- Model quality still insufficient for TL02.

## Next decision

**`ITERATE_PROMPT`** — evidence binding, gold binding, and TL01 assembly are sound; model quality is not ready for participant-role / projected-occurrence work. Do not cut over authoritative temporal production. Prefer a narrow prompt/schema-clarification slice before TL02.
