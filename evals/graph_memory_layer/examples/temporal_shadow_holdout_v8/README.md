# Temporal shadow holdout cohort V8 (TL01G promotion)

**Independent TL01G promotion holdout.** Sealed before first provider run.

Twelve canonical corpus rows with fresh propositions and source spans disjoint from all prior holdout cohorts (V3–V7, cohort, holdout). Covers occurrence (session and textual/relative), valid-time start/end (session and textual), restatement, structure, unresolved, and ambiguous lane classes.

Do not edit after the promotion seal commit used for the first TL01G provider run.

| Row | Source | Proposition type | Gold |
| --- | --- | --- | --- |
| 1 | Session 23 L20 | event (shadow alarm) | resolved occurrence session-23 |
| 2 | Session 21 L14 | event forecast | resolved occurrence textual (`in about seven hours`) |
| 3 | Session 13 L14 | state-start | resolved valid-time start session-13 |
| 4 | Session 22 L24 | state-start (source-different) | resolved valid-time start textual (`has been compromised`) |
| 5 | Session 23 L36 | state-end | resolved valid-time end session-23 |
| 6 | Mirathorn L290 | historical event | resolved occurrence textual |
| 7 | Session 23 L18 | restatement | not_applicable |
| 8 | Session 4 L20 | non-temporal structure | not_applicable |
| 9 | Session 2 L30 | unresolved future pledge | unresolved |
| 10 | Session 15 L30 | unresolved plan/urgency | unresolved |
| 11 | Session 20 L26 | ambiguous competing readings | ambiguous |
| 12 | Session 1 L13 | ambiguous identity | ambiguous |

See `GOLD-AUDIT.md` for row-level audit.
