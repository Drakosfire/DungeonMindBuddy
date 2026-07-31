# Temporal shadow holdout cohort V7 (TL01F corrective replay)

**Not independent promotion evidence.** V7 is a corrective replay of retired V6: eight rows reuse the same V6 propositions and source spans; assertion IDs for those rows match V6 after removing the invalid `cohort_tag` identity hack. One additional Lysandra unresolved-pledge row is new.

V6 remains in-tree as a sealed historical artifact and must not be edited. Promotion matrices may still *execute* V7 for corrected gold scoring, but reports must not describe V7 as a fresh/independent promotion holdout. True independence requires a later cohort with new propositions and source spans plus semantic-overlap tests.

Corrections vs V6 gold:

* Forest forecast → resolved textual occurrence (`in 4–5 hours`), not unresolved
* Abandoned restaurant attribute → `valid_time.start` textual (state with explicit start), not occurrence
* Lysandra contacts/records pledge → genuine unresolved

Do not edit after the corrective-replay seal commit used for the next promotion rerun.

| Row | Source | Proposition type | Gold |
| --- | --- | --- | --- |
| A | Session 6 L24 | event | resolved occurrence session-6 |
| B | Session 8 L19 | state-start | resolved valid-time start session-8 |
| C | Session 23 L36 | state-end | resolved valid-time end session-23 |
| D | Session 18 L24 | restatement | not_applicable |
| E | Session 14 L20 | non-temporal structure | not_applicable |
| F | Session 22 L30 | state-start (source ≠ start) | resolved textual valid-time start |
| G | Session 18 L24 | event forecast | resolved textual occurrence (`in 4-5 hours`) |
| H | Session 12 L20 | ambiguous | ambiguous |
| I | Session 3 L30 | unresolved future pledge | unresolved |

See `GOLD-AUDIT.md` for row-level audit.
