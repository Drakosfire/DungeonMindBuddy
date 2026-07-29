# REPORT — TL01B temporal shadow cohort

**Status:** Live provider run completed (post grounding/manifest/failure-artifact fixes)  
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
| Provider response ID | `resp_084f02c116c4cd98006a6a887d47d4819596bdb375f0cc36f3` |
| Selected assertions | 6 |
| Overlay ID | `temporal-overlay:e985d830e8461a3f` |
| Run ID | `temporal-shadow-run:522390fed3fe62f8` |
| Preview verdict | `complete` |
| Comparison verdict | `fail` |
| Evaluation verdict | `ITERATE_PROMPT` |
| Input tokens | 3525 |
| Output tokens | 846 |
| Elapsed ms | ~4882 |
| Cost | not reported by client |

Artifacts (local, not committed): `evals/graph_memory_layer/artifacts/temporal_shadow_cohort/live-run/`

## Metrics (live vs gold, semantic comparator)

| Metric | Count |
| --- | ---: |
| Exact match | 1 |
| Wrong temporal value (same status) | 3 |
| Wrong temporal lane | 0 |
| Unsafe over-resolution | 1 |
| Safe under-resolution | 0 |
| Other status mismatch | 1 |
| Missing / extra | 0 / 0 |

Expanded phrase grounding (every non-null `source_phrase`, including `not_applicable`) did not reject this provider batch; the run completed to overlay/preview/comparison.

## Strengths

- Sealed digests → owned spans → Responses API strict schema → TL01 overlay → preview.
- Target set exact; no foreign-evidence or missing-target failures.
- Preview verdict `complete`.
- Run manifest now seals repository SHA, case/base digests, selected IDs, artifact digests, provider ID, tokens, and verdicts.
- One true `exact_match` on a `not_applicable` row.

## Failure modes

- Three resolved rows with wrong temporal value.
- One **unsafe over-resolution**: gold `ambiguous` predicted as `resolved`.
- One status mismatch (`not_applicable` → `unresolved`).
- Model quality still insufficient for TL02.

## Next decision

**`ITERATE_PROMPT`** — evaluator contracts (semantic compare, grounding, gold binding, failure artifacts, sealed manifest) are sound; model quality is not ready for participant-role / projected-occurrence work.
