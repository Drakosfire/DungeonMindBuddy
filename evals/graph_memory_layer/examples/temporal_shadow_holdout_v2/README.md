# Temporal shadow holdout cohort V2 (TL01D) — RETIRED

**Status:** Retired as invalid promotion evidence (2026-07-30).  
**Do not use** for promotion calibration, READY thresholds, or successor-prompt design.

## Why retired

Two gold rows misclassified assertion propositions relative to the frozen
`tl01d-v1` eligibility rules:

1. `assertion:b042d6ef548a1ce0` (`thanks` / “Thrin thanks … again”) is a
   **bounded event**, not persistent-state re-attestation. Gold marked
   `not_applicable`; candidate correctly resolved occurrence `session-21`.
   That incorrect gold produced the entire holdout V2 candidate
   `unsafe_over_resolution` / source-to-occurrence false-positive headline.
2. `assertion:1f8580500f4fa97c` (`observed_watching` / hooded figure) is an
   observation **event** grounded in Session 10. Gold marked `ambiguous`
   because watcher identity was unknown; identity uncertainty does not make
   the observation time ambiguous.

Additional audit concern: the Lysandra “command” row used
“reminds … she is in command” evidence while labeling a valid-time **start** —
closer to re-attestation than a first boundary.

## Replacement

Promotion holdout evidence continues under:

```text
evals/graph_memory_layer/examples/temporal_shadow_holdout_v3/
```

This directory remains sealed and unmodified as a historical artifact of the
invalid run. Do not edit fixtures in place.
