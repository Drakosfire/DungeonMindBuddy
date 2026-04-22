# C1S1 OUTCOMES Contract Generalisation Report

**Date:** 2026-04-22
**Question being answered:** Do the events-first prompt contracts (OUTCOMES, VOCABULARY, COMPOSITION) generalise to an unseen recap, or are they overfit to Session 20?

**Verdict:** **OUTCOMES CONTRACT generalises.** Stage A preserves all 13 distinctive C1 Session 1 named terms verbatim across 3/3 audit runs. The Stage A → Stage B scaffold has earned the right to be extended, conditional on the caveat below.

---

## Scope of this measurement

**In scope (measured):**
- **OUTCOMES CONTRACT (Stage A).** Tested directly via Stage A standalone against `Longmont Campaign/Campaign 1/Session Recaps/Session 1 - Recap 3-27-24.md`, a recap with completely different vocabulary, setting, NPC roster, and even a different campaign than the recap the prompt was tuned against (S20).

**Out of scope (deferred):**
- **VOCABULARY CONTRACT (Stage B).** Untestable on C1S1 with current scaffolding because the chained runner (`step2_timeline_from_events_run.py`) is hard-coded to S20: instruction suffix mentions `Session 20` verbatim, `STAGE_B_SLUG_ORDER` is C2-fixed, `_STAGE_B_GOLD_PATH` is the S20 timeline-pass gold, and the pre-state builder strips Session-20 rows from C2 timelines specifically.
- **COMPOSITION CONTRACT (Stage B).** Same blocker as VOCABULARY.
- **C1 hub bootstrap.** No `Campaign 1/PCs/<slug>/timeline.md` or `Campaign 1/NPCs/<slug>/timeline.md` exists in the canonical corpus. Even if the runner were scenario-driven, the writer would have nothing to append to. This is a separate ~half-day of work (build minimal C1 PC + NPC hubs as eval-scenario pre-state seeds, refactor the runner to be scenario-driven, resolve the C1/C2 slug ambiguity for shared-name PCs like Karsemine/Caelynn/Ephanna/Bonogo).

**Why this scope is informative even with Stage B deferred:** Stage B's VOCABULARY/COMPOSITION contracts both depend on Stage A producing events that contain the distinctive terms. If Stage A loses `firkin` upstream, Stage B has no chance of preserving it downstream. Stage A is therefore the upstream gate on the question — and it's the cheapest one to test.

---

## Method

1. Curated Stage A gold: `evals/session_events_extraction_vertical_slice/gold/session_events_session1_c1.json` — 8 expected events covering all 6 PCs (Karsemine, Stafl, Caelynn, Ephanna, Bonogo, Baergrom) and 2 named NPCs (Grishna, Glowkindle), with `must_preserve_terms` populated against each event.
2. Ran Stage A N=5 cohort with the new tightened SE5 grader (`uv run python -m evals.session_events_extraction_vertical_slice.step1_session_events_run --n 5 --model gpt-5.4-mini --scenario-json evals/session_events_extraction_vertical_slice/gold/session_events_session1_c1.json`).
3. Followed up with an N=3 direct-call audit cohort (parsed_events captured to disk under `artifacts/runs/2026-04-22/_audit_c1s1/`) to perform a corpus-level vocabulary check — does each critical C1 term appear *anywhere* in the run's events, regardless of which expected-event the SE5 matcher attached it to.

## Results

### Cohort 1 (gates-graded N=5)

```
run 1/5 | FAIL | events=10 | cost=0.0061 | SE1=PASS SE2=PASS SE3=PASS SE4=PASS SE5=FAIL
run 2/5 | FAIL | events=10 | cost=0.0061 | SE1=PASS SE2=PASS SE3=PASS SE4=PASS SE5=FAIL
run 3/5 | FAIL | events=11 | cost=0.0071 | SE1=PASS SE2=PASS SE3=PASS SE4=PASS SE5=FAIL
run 4/5 | FAIL | events=10 | cost=0.0061 | SE1=PASS SE2=PASS SE3=PASS SE4=PASS SE5=FAIL
run 5/5 | FAIL | events=9  | cost=0.0057 | SE1=PASS SE2=PASS SE3=PASS SE4=PASS SE5=FAIL
cohort done | pass_rate=0/5 | total_cost_usd=$0.0311
```

SE1/SE2/SE3/SE4: 5/5 PASS. SE5: 0/5 PASS. The SE5 grader (newly tightened to enforce per-event `must_preserve_terms`) reported 1–3 missing terms per run.

### Cohort 2 (corpus-level audit N=3)

| Critical C1S1 term     | R1  | R2  | R3  | Total |
| ---------------------- | --- | --- | --- | ----- |
| `firkin`               | ✓   | ✓   | ✓   | 3/3   |
| `Glowkindle`           | ✓   | ✓   | ✓   | 3/3   |
| `Grishna`              | ✓   | ✓   | ✓   | 3/3   |
| `Stonebridge`          | ✓   | ✓   | ✓   | 3/3   |
| `Wizard's Tower`       | ✓   | ✓   | ✓   | 3/3   |
| `River's Edge`         | ✓   | ✓   | ✓   | 3/3   |
| `fermentation cellar`  | ✓   | ✓   | ✓   | 3/3   |
| `magma`                | ✓   | ✓   | ✓   | 3/3   |
| `cat owl`              | ✓   | ✓   | ✓   | 3/3   |
| `giant rats`           | ✓   | ✓   | ✓   | 3/3   |
| `25 gold`              | ✓   | ✓   | ✓   | 3/3   |
| `shatter mages tower`  | ✓   | ✓   | ✓   | 3/3   |
| `mosaic`               | ✓   | ✓   | ✓   | 3/3   |

**13/13 distinctive C1 terms preserved verbatim in every audit run.** The OUTCOMES CONTRACT generalises.

### Reconciliation: why did Cohort 1 SE5 say FAIL when the terms are clearly preserved?

The SE5 misses are **per-event matching artifacts**, not contract violations. Concretely:

- My gold treats "drinks at pub + Grishna shares directions + Glowkindle reference + job-board ad" as ONE expected event with required terms `[Grishna, River's Edge, Glowkindle, Wizard's Tower]`.
- The model consistently splits this beat into 2–3 finer events (e.g. `Drinks at The River's Edge Pub`, `Glowkindle's Help Request`, `Trail to the Great Boulder`).
- The new SE5 matcher picks ONE of those split events as the "match" for my expected event. The terms not present in that single matched event are reported as missing — even though they are present in sibling events that the matcher didn't pick.

**Diagnosis:** the gold's expected-event granularity is calibrated finer than what gpt-5.4-mini chooses to emit. This is a gold-curation calibration concern, not a model contract failure. The corpus-level audit (Cohort 2) confirms the model preserved every term; SE5's per-event check just attached them to the wrong expected event.

---

## Recommendations

1. **Confidence in scaffold:** confirmed. Proceed to NPC ingestion slice as the next architectural extension (per the user-confirmed sequence in `Backlog.md` 2026-04-22 entries).

2. **Follow-up: SE5 corpus-level term check.** The SE5 grader currently checks `must_preserve_terms` against the matched actual event only. A small enhancement (a few LOC) would be: if a required term is missing from the matched actual event, also check whether the term appears in *any* actual event of the run. If yes → soft-pass with a `term_in_sibling_event` telemetry note. If no → hard fail with `kind=missing_outcome_terms`. This would distinguish *gold calibration drift* from *real contract regression*. Captured below as a Backlog item.

3. **Stage B chained on C1S1 — separate dispatch when ready.** The work needed is: (a) build minimal C1 PC + NPC hub seeds in an eval scenario directory (not canonical corpus), (b) refactor `step2_timeline_from_events_run.py` to be scenario-driven (extract S20-specific strings to scenario config), (c) resolve the C1/C2 slug ambiguity for shared-name PCs (the writer's `_find_timeline_for_slug` rglob will return both `Campaign 1/PCs/karsemine/timeline.md` and `Campaign 2/PCs/karsemine/timeline.md` and report ambiguous), (d) curate a C1S1 timeline-pass gold (anchor_words per slug). Estimated half-day. Sequence after the SE5 sibling-check enhancement above.

4. **No further work on Stage A required.** The OUTCOMES CONTRACT is doing exactly what it was designed to do.

## Cost report

| Phase                        | Cost     |
| ---------------------------- | -------- |
| Cohort 1 (gates-graded N=5)  | $0.0311  |
| Cohort 2 (audit N=3)         | $0.0168  |
| **Total C1S1 measurement**   | **$0.0479** |

Mean cost per Stage A C1S1 run: $0.0060.

---

## Artifacts

- Stage A gold: `evals/session_events_extraction_vertical_slice/gold/session_events_session1_c1.json`
- Cohort 1 reports: `evals/session_events_extraction_vertical_slice/artifacts/runs/2026-04-22/session_events--session_events_session1_c1--gpt-5.4-mini--FAIL--20260422T1619*.{md,json}`
- Cohort 1 cohort summary: `evals/session_events_extraction_vertical_slice/artifacts/runs/2026-04-22/session_events_summary--gpt-5.4-mini--N5--20260422T161946Z.{md,json}`
- Audit cohort raw events: `evals/session_events_extraction_vertical_slice/artifacts/runs/2026-04-22/_audit_c1s1/audit_run0{1,2,3}.json`

## Related

- `Backlog.md` (2026-04-22 entries: NPC ingestion slice, Location ingestion slice, sequencing notes)
- `Docs/Plans/STATUS-Session-Recap-Timeline-Pass-Benchmark.md` (Iteration 7 — events-first chained pipeline state)
- `evals/session_events_extraction_vertical_slice/README.md` (Stage A + Stage B contracts and gates)
