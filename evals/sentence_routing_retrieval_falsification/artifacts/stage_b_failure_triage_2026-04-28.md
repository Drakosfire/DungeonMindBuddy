# Stage B — Failure triage (full scenario `sentence_routing_c2_session20_pc`)

**Date:** 2026-04-28  
**Sidecar:** `evals/sentence_routing_retrieval_falsification/artifacts/last_sentence_routing_stage_b_hub_routes.json`  
**Stability reference:** `evals/sentence_routing_retrieval_falsification/artifacts/last_stage_b_stability_c2s20_full.json` (72 sidecars, per-row `pass_rate`).

## Aggregate (latest full run)

| Metric | Value |
|--------|------:|
| `gold_gate_checks_pass` / `total` | 58 / 74 |
| `must_route` pass / fail | 35 / 15 |
| `must_abstain` pass / fail | 23 / 1 |
| `scenario_estimated_cost_usd` | 0.039401 |
| B0 diagnostic contradiction | 0 |
| B1 missing | 12 |
| B1 over-route | 3 |
| B2 over-assigned | 1 |

## Classification rules (triage)

- **gold_intent** — B2 on `u-L0018-10` (listener / reported-speech / abstain); needs GM product intent or explicit gold+`scenario_notes`, not just prompt.
- **regression_risk** — Historical `pass_rate` **≥ 0.85** on 72 sidecars; a single miss is surprising and should be diffed (prompt / expansion / this draw) before broad prompt rewrites.
- **known_hard** — Historical `pass_rate` **< 0.5**; chronic B1 / routing judgment issue (roster-copy, scene arc, continuation).
- **known_flaky** — Historical `pass_rate` in **[0.5, 0.85)**; still routing judgment, but not “new shock.”

## Row-level triage (16 violation lines)

| code | `gold` kind | unit_id | Stability `pass_rate` (N=72) | Class | Notes (from sidecar) |
|------|---------------|---------|-----------------------------|-------|------------------------|
| B1 | must_route | u-L0014-03 | 0.806 | known_flaky | over-route (full roster vs expected narrow) |
| B1 | must_route | u-L0016-06 | 0.972 | **regression_risk** | over-route |
| B1 | must_route | u-L0018-02 | 0.569 | known_flaky | missing `bonogo` |
| B1 | must_route | u-L0018-08 | 0.375 | **known_hard** | missing `bonogo` |
| B1 | must_route | u-L0022-05 | 1.000 | **regression_risk** | missing `bonogo` |
| B1 | must_route | u-L0022-07 | 0.486 | **known_hard** | missing `bonogo` |
| B1 | must_route | u-L0026-03 | 0.167 | **known_hard** | missing full roster (empty assign) |
| B1 | must_route | u-L0026-06 | 0.556 | known_flaky | missing `bonogo` (subset vs full) |
| B1 | must_route | u-L0028-02 | 0.153 | **known_hard** | missing `caelynn` |
| B1 | must_route | u-L0028-04 | 0.931 | **regression_risk** | missing `caelynn` |
| B1 | must_route | u-L0028-05 | 0.792 | known_flaky | missing `caelynn` |
| B1 | must_route | u-L0028-09 | 0.944 | **regression_risk** | over-route |
| B1 | must_route | u-L0030-03 | 0.653 | known_flaky | missing full roster |
| B1 | must_route | u-L0030-05 | 0.833 | known_flaky | missing `caelynn` |
| B1 | must_route | u-L0032-09 | 0.653 | known_flaky | missing `caelynn` |
| B2 | must_abstain | u-L0018-10 | 0.486 | **gold_intent** | over-assigned PC (listener boundary) |

**Counts:** regression_risk **4** · known_hard **4** · known_flaky **7** · gold_intent **1**

## Dominant failure bucket (next-lever)

1. **Largest by count (routing judgment, not “new”):** **known_flaky (7)** + **known_hard (4)** = **11/16** — chronic B1 recall, roster-copy, Bonogo/Caelynn arc beats. This is where most session-level work will go once regressions are ruled out.

2. **Highest priority for a *falsification* pass:** **regression_risk (4)** — `u-L0016-06`, `u-L0022-05`, `u-L0028-04`, `u-L0028-09` were historically high-pass. A single run failing all four is worth treating as a possible interaction bug (e.g. `the_party` expansion, prompt hash, or stochastic draw) until N≥3 reproduces the pattern on current `routing_prompt_id`.

3. **Must not be prompt-solved first:** **gold_intent (1)** — `u-L0018-10` is the documented listener/adjudication row; pick retrieval intent, then either gold+`scenario_notes` or a narrow base-prompt line.

**Chosen lever (ordering):**  
(1) **Regression quarantine** on the 4 high-pass units — N=3 full-scenario reruns, same gold and base prompt, compare per-unit outcomes and costs.  
(2) In parallel, **u-L0018-10** **GM decision** (abstain vs must_route).  
(3) If regressions are noise, return to **known_hard** (especially `u-L0026-03`, `u-L0028-02`, `u-L0018-08`, `u-L0022-07`) via `the_party` + role-intersection sentinels already in `evals/sentence_routing_retrieval_falsification/gold/`.

## Smallest N=5 experiment (when ready)

**Precondition:** After N=3 on full scenario shows whether the 4 regression-risk rows are stable fails or one-off.

**A — Regression pack (if N=3 confirms repeats)**  
- Command: `uv run python -m evals.sentence_routing_retrieval_falsification.step2_route_run`  
- `--scenario-json` `evals/sentence_routing_retrieval_falsification/gold/scenario_c2_session20_pc.json`  
- `--corpus-root .`  
- `--n 5`  
- Default prompt (no variant, unless comparing to `party_roster_strict_v1`).  
- **Report (per run and cohort):** `gold_gate_checks_pass`, `must_route` / `must_abstain` split, `violation_failure_buckets` (B1 missing vs over-route, B0/H8), `routing_prompt_id`, `scenario_estimated_cost_usd` (min/mean/max/sum).

**B — Known-hard slices (if regressions are noise)**  
- Run N=5 on: `gold/scenario_c2_session20_pc_edge_slice_party_boundary.json` and `gold/scenario_c2_session20_pc_edge_slice_h1_h2_sentinel.json` (already in matrix).  
- **Report:** same triple + B1/B2 + cost vs prior README baselines.

**C — Intent (single row)**  
- Adjudicate `u-L0018-10` offline; if gold changes, re-run `gold/scenario_c2_session20_pc.json` with `--n 1` and update fingerprint/stability if gold shape shifts.

**Cost (planning only):** Full-scenario N=5 is ~5× the last per-run `~$0.039` unless model pricing changes; cohort summary must log `cost_usd.sum` per `cost-as-signal.mdc`.
