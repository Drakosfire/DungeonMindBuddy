# REPORT — TL01B temporal shadow cohort

**Status:** Live provider run completed  
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
| Prompt version | `tl01b-v1` |
| Provider response ID | `resp_091ceeec16858b07006a6a66e6d3188193a476c9236fad619a` |
| Selected assertions | 6 |
| Overlay ID | `temporal-overlay:4f832a54e4dbc9fd` |
| Preview verdict | `complete` |
| Comparison verdict | `fail` |
| Evaluation verdict | `ITERATE_PROMPT` |
| Input tokens | 3525 |
| Output tokens | 1031 |
| Elapsed ms | ~5917 |
| Cost | not reported by client |

Artifacts (local, not committed): `evals/graph_memory_layer/artifacts/temporal_shadow_cohort/live-run/`

## Metrics (live vs gold)

| Metric | Count |
| --- | ---: |
| Exact match | 0 |
| Wrong temporal value (same status) | 4 |
| Unsafe over-resolution | 1 |
| Other status mismatch | 1 |
| Safe under-resolution | 0 |
| Missing / extra | 0 / 0 |

## Strengths

- Infrastructure completed end-to-end: sealed digests → owned spans → Responses API strict schema → TL01 overlay → preview.
- Target set exact; no foreign-evidence or missing-target failures.
- Preview verdict `complete` (no skipped unresolved schemas).
- Negative provenance path did not crash; grounding checks held.

## Failure modes

- Zero exact semantic matches against human gold.
- One **unsafe over-resolution**: gold `ambiguous` predicted as `resolved`.
- One status mismatch (`not_applicable` → `unresolved`).
- Several resolved rows with wrong temporal point/interval payloads (same status, wrong value).

## Next decision

**`ITERATE_PROMPT`** — evidence binding and TL01 assembly are sound; model quality is not ready for participant-role / projected-occurrence work. Do not cut over authoritative temporal production. Prefer a narrow prompt/schema-clarification slice before TL02.
