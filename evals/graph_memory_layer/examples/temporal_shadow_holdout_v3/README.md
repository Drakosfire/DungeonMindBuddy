# Temporal shadow holdout cohort V3 (TL01D)

Sealed replacement for retired holdout V2. Authored after `tl01d-v1` freeze; human gold only.

Independent of development, prior holdout, retired holdout V2, and adversarial V2/V3 casts.
Prompt-example vocabulary (Dessa/Orun/Caldrin/...) excluded.

| # | Category | Gold |
| --- | --- | --- |
| 1 | Same-source event (Dust Devil) | resolved occurrence session-16 |
| 2 | Same-source event (Hunger of Hadar) | resolved occurrence session-23 |
| 3 | Structural (Glimmering Globe / lake) | not_applicable |
| 4 | Scene framing (back to the Inn) | not_applicable |
| 5 | Ambiguous mention/identity (Seraphine roster) | ambiguous + null extents |
| 6 | Relative/incomplete historical | textual occurrence "not long before the group arrived" |
| 7 | Persistent-state re-attestation (Orik is mayor) | not_applicable |

## Coverage gaps (canonical)

- Persistent **valid-time start** not safely available in unused sessions without fabrication — covered only in adversarial V3.
- Persistent **valid-time end** — covered only in adversarial V3.
- Explicit **source-session ≠ occurrence/valid-start** — covered only in adversarial V3.

## Audit notes vs retired V2

- Re-attestation uses a persistent role proposition (`is_mayor_of`), not an eventive thanks.
- Ambiguous row is a roster **mention**, not an observed event with unknown actor identity.
- Textual raw_expression is a verbatim contiguous substring of the cited line.
