# Temporal shadow holdout cohort V13 (TL01G)

**RETIRED as independent TL01G promotion evidence.**

Holdout V13 was sealed as TL01G promotion holdout after prompt freeze `67408bd871ba684e70ddf6e53dd7088d0036a475`. Gold is retained unchanged as **observed regression** material only — do not patch gold to fix defects below.

**Seal SHA:** `33bae3485babb0d15373b91b0cbcb13282b42491` (retained)

## Observed gold defects (regression evidence; do not patch gold)

1. **Gate E3 — resulting-state report licensed as valid-end:** assertion *The rebel humans feel represented in Mirathorn* is resolved with `valid_time.end.session_id=session-7` from source phrase `no longer feel represented`. That prose reports a resulting attitude/state, not an in-episode boundary event — resolving valid-end at session-7 is **not Gate-E3-faithful**.
2. **Proposition-first value — reschedule time as occurrence:** assertion *The council raid on the compromised guardhouse has been postponed until dawn* uses `postponed until dawn` as the occurrence value of the postponement decision rather than leaving the decision unresolved or treating dawn as a different proposition.

## Next action

Diagnose the shared grounding path that produced these defects. Do **not** author holdout V14 / tl01h promotion cohorts until that diagnosis lands.

Holdout V12 is also **RETIRED** (gold/Gate defects retained as observed regression only).
