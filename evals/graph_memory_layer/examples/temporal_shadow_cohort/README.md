# TL01B temporal shadow cohort

Sealed case fixtures for evidence-bound model shadow temporal extraction.

## Cohort matrix

| # | Category | Assertion label | Gold status |
| --- | --- | --- | --- |
| 1 | Event (revive) | Stafl revives Caelynn | `resolved` occurrence `session-7` |
| 2 | Valid-time start | Lysandra assigned to lead | `resolved` valid from `session-13` |
| 3 | Event destroy | Hybrid monster destroyed | `resolved` occurrence `session-24` (explicit same-session) |
| 4 | Scene framing | Party at Copper and Quartz | `not_applicable` |
| 5 | Negative provenance | Road observation | `not_applicable` (legacy `session-22` scope ≠ occurrence) |
| 6 | Ambiguous mention | Maelthor password mention | `ambiguous` |

## Missing categories (corpus search)

- **Relative-historical exile / "long ago"**: no suitable C2 recap span found; not included in this cohort.

## Files

- `temporal-case.json` — sealed case (paths, digests, evidence registry)
- `base-contribution.json` — candidate-only GraphContribution
- `gold-overlay.json` — human gold `TemporalAnnotationOverlayV1`
