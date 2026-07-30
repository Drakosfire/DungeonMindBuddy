# Temporal shadow adversarial cohort V2 (TL01C)

Synthetic adversarial cases for prompt calibration. **Not** canonical corpus.

## Independence from few-shots

Must not reuse the `tl01c-v1` synthetic few-shot cast, predicates, or sentence templates.
This V2 cohort uses **Jorin / Pella / Tovin / Quill Harbor / frost seal / Ash Riders** with different proposition shapes and wording.

V1 (`examples/temporal_shadow_adversarial/`) is retained only as contaminated historical reference and must not be used for calibration.

## Patterns covered

1. Occurrence ≠ source session
2. Valid-time start ≠ source session
3. Valid-time end in narrated episode
4. Re-attestation → not_applicable
5. Ambiguous relative history

Seal before live calibration runs; do not merge into development/holdout metrics.
