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

- **Source differs from occurrence** (source session N, gold occurrence at different normalized fictional time M): **not found** as a sealable C2 candidate assertion — see report stop conditions.
- **Valid-time end / explicit transition**: **not found** as a sealable C2 candidate assertion — see report stop conditions.
- **Relative-historical exile / "long ago"**: no suitable sealed C2 assertion included; Session 11 contains relative “30 years ago” prose but no matching sealed candidate assertion in this cohort.

Synthetic unit regressions cover source-leakage and foreign-evidence metric paths even when live corpus categories are missing.

## Files

- `temporal-case.json` — sealed case (paths, digests, evidence registry)
- `base-contribution.json` — candidate-only GraphContribution
- `gold-overlay.json` — human gold `TemporalAnnotationOverlayV1`
