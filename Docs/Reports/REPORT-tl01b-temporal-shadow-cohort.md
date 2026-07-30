# REPORT — TL01B temporal shadow cohort

**Status:** Live provider run completed
**Live execution commit (manifest `repository_sha`):** `52eef8e84e71dce6fb501e0e713a34428226e34e`
**Implementation base (TL01 merge):** `d6ea4959c9bcc2f113ef50d912629864c1a1c04b`
**Evaluation verdict:** `ITERATE_PROMPT`

The live-proof SHA above is copied from the generated `run-manifest.json` for this run. It is the clean repository HEAD that executed the provider call (not merely the original TL01 merge base).

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
| Provider response ID | `resp_06f86ddaf15e3e3f006a6a9dcbe65c819393689fa66e3483bb` |
| Selected assertions | 6 |
| Overlay ID | `temporal-overlay:072b1eb5beac7b25` |
| Run ID | `temporal-shadow-run:e830cac21f4e1924` |
| Preview verdict | `complete` |
| Comparison verdict | `fail` |
| Evaluation verdict | `ITERATE_PROMPT` |
| Input tokens | 3525 |
| Output tokens | 863 |
| Elapsed ms | ~6048 |
| Cost | not reported by client |

Artifacts (local, gitignored): `evals/graph_memory_layer/artifacts/temporal_shadow_cohort/live-run/`

## Metrics (live vs gold)

### Classification

| Metric | Count |
| --- | ---: |
| Exact semantic match | 1 |
| Resolved exact match | 0 |
| Wrong temporal value | 3 |
| Wrong temporal lane | 0 |
| Unsafe over-resolution / unsupported resolved | 1 |
| Status mismatch | 1 |
| Safe under-resolution | 0 |
| Missing / extra | 0 / 0 |

### Safety

| Metric | Count |
| --- | ---: |
| Source→occurrence false positives | 0 |
| Source→valid-time false positives | 0 |
| Unsupported resolved annotations | 1 |
| Foreign evidence attempts | 0 |
| Ungrounded source phrases | 0 |
| Invalid temporal payloads | 0 |

### Quality

| Metric | Value |
| --- | --- |
| Status accuracy | 0.667 (4/6) |
| Exact semantic match count | 1 |
| Resolved exact match count | 0 |
| Ambiguous or unresolved (gold) | 1 |
| Not-applicable accuracy | 0.5 (1/2) |

## Strengths

- Atomic overwrite: success and failure directories no longer retain contradictory sibling artifacts.
- Sealed run manifest records the exact execution commit SHA.
- Safety metrics now separate unsupported over-resolution from ordinary wrong-value rows.
- No source→occurrence or source→valid-time false positives in this provider batch.
- Preview verdict `complete`.

## Failure modes

- Three resolved rows with wrong temporal value (same status/lane, different payload).
- One unsupported resolved annotation (gold `ambiguous` → predicted `resolved`).
- One status mismatch on a `not_applicable` gold row.
- Model quality still insufficient for TL02.

## Next decision

**`ITERATE_PROMPT`** — evaluator contracts (atomic publish, safety/quality metrics, sealed SHA) are sound; model quality is not ready for participant-role / projected-occurrence work.
