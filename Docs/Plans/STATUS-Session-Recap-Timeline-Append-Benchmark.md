# Session recap timeline append (Stage 2) — gate status

**Spec:** [EXPERIMENT-Session-Recap-Timeline-Append-Benchmark.md](EXPERIMENT-Session-Recap-Timeline-Append-Benchmark.md)  
**Stage-1 ledger (model):** [STATUS-Session-Recap-Ingest-Benchmark.md](STATUS-Session-Recap-Ingest-Benchmark.md)

Update **Last verified** when you re-run the listed commands.

---

## Legend

Same tokens as Stage-1 STATUS: **PASS**, **PASS (live)**, **OPEN**, etc.

---

## Automation gates

| Gate | Status | Last verified | How verified |
|------|--------|---------------|--------------|
| T1 two-phase `append_timeline_row` | PASS (live) | 2026-04-21 | `step1_timeline_append_run.py` cohort N=3 `gpt-5.4-mini` |
| T2 no `write_corpus_file` | PASS (live) | 2026-04-21 | same |
| T3 no recap assembler tools | PASS (live) | 2026-04-21 | same |
| T4 hybrid timeline row | PASS (live) | 2026-04-21 | same |
| T5 pre-state shape | PASS | 2026-04-21 | `tests/test_timeline_append_pre_state.py` |

**Offline batch:**

```bash
uv run pytest tests/test_timeline_append_grader.py tests/test_timeline_append_pre_state.py -q
```

---

## Live cohort log

| Date | Model | N | Pass | Notes / artifacts |
|------|-------|---|------|-------------------|
| 2026-04-21 | gpt-5.4-mini | 3 | 3/3 | `artifacts/runs/2026-04-21/timeline_append_summary--gpt-5.4-mini--N3--20260421T142110Z.{md,json}`; prompt required explicit “commit in same turn” (first N=3 stopped at preview-only). |

---

## Follow-ups

- Expand cohort NPCs once Lysandra gate is stable (see diversification list in run reports / parent backlog).
