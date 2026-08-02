# Temporal shadow holdout cohort V14 (TL01G)

**RETIRED as independent TL01G promotion evidence.**

Holdout V14 was sealed as TL01G promotion holdout after fixture seal
`cde3b48d5b95ba4fc1f7c779993c2497f66914f7`. Fixture, gold, audit, source, case,
and observed matrix bytes are retained **unchanged** — **do not patch gold** and
**do not rerun** the promotion matrix on this cohort.

**Seal SHA:** `cde3b48d5b95ba4fc1f7c779993c2497f66914f7` (retained)

## Why retired (shared matrix invalid)

The paired adversarial cohort Adv V12 contains sealed gold that is not grounded
in its owned evidence (`valid_time.start.raw_expression = "since the equinox flood"`
absent from source). The handoff forbids post-observation gold repair. The
entire V14/Adv V12 promotion matrix is therefore **`PROMOTION_EVIDENCE_INCOMPLETE`**
and cannot authorize `ITERATE_PROMPT` / `tl01h-v1` or broader shadow readiness.

V14 gold itself may still be useful as observed regression material after
failure classification, but it is **not** independent promotion authority while
paired with defective Adv V12.

## Next action

Require a fresh successor cohort pair before another promotion claim. Do not
edit these sealed bytes.

Adversarial V12 is retired with this cohort.
