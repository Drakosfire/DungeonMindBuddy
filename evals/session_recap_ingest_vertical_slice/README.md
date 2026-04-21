# Session recap ingest — Scope-B benchmark slice

**What this slice grades:** the `recap-write` skill against the Session 20 raw notes, end-to-end through the live planner, with a mechanical Scope-B contract that is hard-gated.

- **Spec:** [Docs/Plans/EXPERIMENT-Session-Recap-Ingest-Benchmark.md](../../Docs/Plans/EXPERIMENT-Session-Recap-Ingest-Benchmark.md)
- **Live gate ledger:** [Docs/Plans/STATUS-Session-Recap-Ingest-Benchmark.md](../../Docs/Plans/STATUS-Session-Recap-Ingest-Benchmark.md)
- **Skill under test:** [`.cursor/skills/recap-write/SKILL.md`](../../.cursor/skills/recap-write/SKILL.md)
- **Backlog (Staff Designer follow-ups):** [Docs/Plans/BACKLOG-session-recap-benchmarking.md](../../Docs/Plans/BACKLOG-session-recap-benchmarking.md)

---

## What you actually get

Each run produces:

1. A **per-run sidecar JSON** (`recap_ingest--<scenario>--<model>--<PASS|FAIL>--<turn-count>--<utc>--runNNN.json`) with split gates (`tool_trace_gates_passed`, `payload_gates_passed`, `gates_passed`), violations dict, full `tool_trace_tools` list, telemetry, `recap_write_v1` payload + sha256_16, and `scope_b_extras` (write phases, soft observations).
2. A matching **per-run markdown report** with the planner review embedded plus the sidecar JSON in a fenced block.
3. When `--n > 1`, a **cohort summary** (`recap_ingest_summary--<model>--N<n>--<utc>.{md,json}`) aggregating pass rates, cost stats, distinct payload hashes, distinct trace signatures, and `write_corpus_file` preview/commit/no_write rates.

Artifacts live under `artifacts/runs/<YYYY-MM-DD>/` and the legacy `artifacts/last_recap_ingest_run.{md,json}`.

---

## Scope-A — fast, no LLM

Mechanical recap ingest is unit-tested in-repo. No API key required.

```bash
uv run pytest tests/test_session_20_scope_a_gold.py tests/test_recap_ingest_helpers.py -q
```

---

## Scope-B — live planner

### One-shot run (sequential)

```bash
export OPENAI_API_KEY=…   # or rely on repo .env / .env.development (auto-loaded)
PLANNER_REVIEW_MODE=summary uv run python -m \
  evals.session_recap_ingest_vertical_slice.step1_recap_ingest_run
```

### One perturbation scenario

```bash
export OPENAI_API_KEY=…   # optional if repo .env / .env.development already has it
PLANNER_REVIEW_MODE=summary uv run python -m \
  evals.session_recap_ingest_vertical_slice.step1_recap_ingest_run \
  --scenario-json evals/session_recap_ingest_vertical_slice/scope_b_scenarios/guarded_staging_read_recovery.json
```

### Cohort run

```bash
PLANNER_REVIEW_MODE=summary uv run python -m \
  evals.session_recap_ingest_vertical_slice.step1_recap_ingest_run --n 5
```

### Parallel cohort (~5x faster on N=5)

Workers race on the OpenAI API; report writing is serialized so stdout review blocks don't garble.

```bash
PYTHONUNBUFFERED=1 PLANNER_REVIEW_MODE=summary uv run python -m \
  evals.session_recap_ingest_vertical_slice.step1_recap_ingest_run \
  --n 5 --parallel 5 2>&1 | tee /tmp/recap_5x.log
```

### Detached background run

The benchmark is API-bound for several minutes; detach if you want to keep working in the terminal.

```bash
# Background, exit immediately, observe via tail -f:
uv run python -m evals.session_recap_ingest_vertical_slice.step1_recap_ingest_run \
  --detach --n 5 --parallel 5 --detach-log /tmp/recap_5x.log
tail -f /tmp/recap_5x.log

# Or detach + stream the log to this terminal (Ctrl+C stops the viewer only):
uv run python -m evals.session_recap_ingest_vertical_slice.step1_recap_ingest_run \
  --detach --detach-follow --n 5 --parallel 5 --detach-log /tmp/recap_5x.log
```

### Useful flags

| Flag | Effect |
|---|---|
| `--n N` | Run N planner turns; cohort summary written if `N > 1`. |
| `--parallel K` / `-p K` | Up to K cohort runs concurrent (default 1; capped at `N`). |
| `--detach` / `--background` | Spawn the same run in a child process; parent exits unless `--detach-follow`. |
| `--detach-log PATH` | Log file for detached child (default `/tmp/recap_ingest_detach_<UTC>.log`). |
| `--detach-follow` | With `--detach`: stream the log to stdout (`tail -f` style). |
| `-v` / `-vv` | One-line-per-run / full tool_trace dump on stderr. **Default is `-vv`.** |
| `-q` / `--quiet` | Suppress stderr progress. |
| `--print-root` | Build the pre-state tmp corpus, print its path, exit (no API call). |
| `--live-corpus` | Use the live `corpus/eldyrwild-markdown` (no pre-state strip). Debugging only; warns when `--n > 1` because per-run isolation is lost. |
| `--tmp-parent DIR` | Pin the pre-state copy under a known parent (forensics). |
| `--model ID` | Override planner model id (else `MODEL_POLICY` / default). |
| `--no-writes` | Disable corpus write tools. |
| `--runs-root DIR` | Override the report root (else `<slice>/artifacts/runs` or env `RECAP_INGEST_RUNS_ROOT`). |

---

## How the benchmark is wired

```
   gold/scope_b_session_20.json (single fixture)
            │
            ▼
   step0_pre_state.build_pre_state_corpus()  ────────►  /tmp/<…>/eldyrwild-markdown
            │                                            (per-run, isolated)
            ▼
   resolve_recap_context(corpus_path)  ─►  RecapContext (frozen snapshot,
            │                              shared across all turns + grader)
            ▼
   run_planning_turn_detailed(
       active_skill_id="recap-write",        ──► per-skill text.format
                                                 (planner_skill_output_schema)
       skill_recap_context=…,                ──► dispatch guard allowlist
       skill_read_allowlist_extras=…,            (planner_skill_dispatch_guards)
       …)
            │
            │   tool calls: get_recap_context, read_corpus_file × N,
            │               assemble_recap_draft, optional build_recap_write_payload,
            │               write_corpus_file (preview)
            ▼
   followup_turn (chained via previous_response_id)
            │   tool calls: write_corpus_file (commit, with confirm_token)
            ▼
   collect_scope_b_recap_ingest_violations(  ──► hard gates:
       sc, detail, corpus_path,                  scope_b_tool, scope_b_payload
       precomputed_recap_context=…)
            │
            ▼
   collect_scope_b_recap_ingest_report_extras(           ──► soft signals:
       sc, detail, corpus_path,                              write_phases, soft_observations,
       recap_context_snapshot=…)                             build_recap_write_payload_called,
            │                                                mechanical_fields_match (T/F/None),
            │                                                mechanical_fields_diff
            ▼
   capture_and_write_recap_ingest_report(…)   ──► per-run .md + .json
            │
            ▼
   write_recap_ingest_multi_summary(summaries) ──► cohort summary (N > 1)
```

### Mechanical Scope-B contract (what the grader hard-asserts)

1. Exactly one `get_recap_context` call with **unpinned** `campaign_id` / `target_session`.
2. Every `read_corpus_file` (or `load_context_markdown`) path ∈ `recent_recaps[].path` ∪ `prep_doc_path` ∪ `read_allowlist_extra`. Defense-in-depth: the dispatch guard fail-closes out-of-allowlist reads at tool dispatch *before* the model burns tokens.
3. Exactly one `assemble_recap_draft` call with `target_session` and `campaign_id` matching the snapshotted `RecapContext`, and `raw_notes_path == ingest_raw_notes_relpath`.
4. **Optional (off by default):** `scope_b_grader.require_build_recap_write_payload: true` requires exactly one `build_recap_write_payload` call with the same three args as `assemble_recap_draft`. The Session 20 gold leaves this **disabled** so the model may merge mechanical fields by hand or via the tool. Adoption + payload alignment is tracked as a soft signal — see `mechanical_fields_match` in the report extras (BACKLOG §1.5).
5. `write_corpus_file` phase shape satisfies the `preview_required` / `commit_required` knobs in the gold scenario (currently both `true` → `preview→commit` is required).
6. Final assistant message contains a top-level `recap_write` field that parses + validates as `recap_write_v1` (`recap_preview.confirm_token` may be empty until after preview; schema allows `minLength: 0`).

These map onto the original SCOPE-B-GOLD §J item-by-item gates as documented in [STATUS-Session-Recap-Ingest-Benchmark.md](../../Docs/Plans/STATUS-Session-Recap-Ingest-Benchmark.md).

---

## Files in this slice

```
evals/session_recap_ingest_vertical_slice/
├── README.md                        # this file
├── scope_b_grader.py                # mechanical Scope-B contract (violations + extras)
├── recap_ingest_run_report.py       # per-run + cohort artifact writers
├── step0_corpus_environment.py      # corpus fingerprint pin + service gate
├── step0_pre_state.py               # build per-run pre-state tmp corpus
├── step1_recap_ingest_run.py        # the runner (CLI entry)
├── step3_unsure_queue_grading.py    # legacy unsure-queue regex grader (NOT wired into runner today)
├── step4_chaos_two_phase.py         # doc anchor; C3 covered by tests/test_corpus_writer.py
├── gold/
│   ├── scope_b_session_20.json      # the single gold scenario
│   ├── scope_b_session_20_unsure_queue.json
│   └── step0_pre_state_manifest.json
├── fixtures/
│   └── session_20_raw_notes.txt     # copy of repo-root Session 20 Recap.txt
└── artifacts/
    ├── last_recap_ingest_run.{md,json}
    └── runs/<YYYY-MM-DD>/…
```

### Test coverage

| Module under test | Test file |
|---|---|
| Scope-B grader (split gates, allowlist, knob resolution, write phases) | `tests/test_scope_b_grader.py` |
| Report writer (per-run + cohort artifacts) | `tests/test_recap_ingest_run_report.py` |
| Detach argv filter (subprocess argv hygiene) | `tests/test_recap_ingest_detach_argv.py` |
| Dispatch guards (recap-write read allowlist, no-pin enforcement) | `tests/test_planner_skill_dispatch_guards.py` |
| Per-skill output schemas | `tests/test_planner_skill_output_schema.py` |
| Universal turn schema | `tests/test_planner_turn_output_schema.py` |
| Pure recap helpers (Scope-A) | `tests/test_recap_ingest_helpers.py` |
| Scope-A gold | `tests/test_session_20_scope_a_gold.py` |

```bash
uv run pytest \
  tests/test_scope_b_grader.py \
  tests/test_recap_ingest_run_report.py \
  tests/test_recap_ingest_detach_argv.py \
  tests/test_planner_skill_dispatch_guards.py \
  tests/test_planner_skill_output_schema.py \
  tests/test_planner_turn_output_schema.py \
  tests/test_recap_ingest_helpers.py \
  tests/test_session_20_scope_a_gold.py -q
```

---

## Operational notes

- **Default verbosity is `-vv`** because long API rounds (~10–20s each) made earlier silent log gaps look like hangs.
- **Per-run pre-state corpus** rebuilds on every iteration (`_build_corpus_for_run(i)`); cross-run isolation is preserved in both the sequential and parallel paths.
- **`RecapContext` is snapshotted before any turn runs.** The same snapshot is passed to (a) the dispatch guard, (b) the followup turn, (c) the grader. This eliminates a temporal-coupling bug where a turn-1 commit would shift `max(session)` and rewrite turn-2's read allowlist.
- **Parallel cohort speedup is bounded by tail latency.** With 5 workers, total wall time ≈ slowest per-run wall time. One slow OpenAI round dominates a cohort. There is currently **no soft-fail / continue on worker exception**; one timeout aborts the cohort. Tracked in [BACKLOG](../../Docs/Plans/BACKLOG-session-recap-benchmarking.md).
- **Cost is reported, not gated.** Last 5×: $0.32 USD total. There is currently no `--max-cost-usd` ceiling. Tracked in BACKLOG.

---

## Fixture provenance

`fixtures/session_20_raw_notes.txt` is a copy of repo-root `Session 20 Recap.txt`. Update both together if the gold input changes (and re-author Scope-A gold via `tests/test_session_20_scope_a_gold.py`).
