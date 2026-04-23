# Session recap → autonomous timeline pass (Stage-2 v1 vertical slice)

**What this slice grades:** After Stage-1 has committed `Session 20 - Recap.md`, a downstream pipeline appends Session-20 timeline rows to the eight expected C2 timeline files (six append targets + two skip targets). For each expected-append slug: produce ≥`expected_count` rows whose beat-cell text covers `anchor_words`. For each skip-target slug: produce no `**20**` row. Hub-proposal evaluation is **out of scope for this slice** as of Iteration 6.

This is the autonomous sibling of the v0 operator-instructed slice (`session_recap_timeline_append_vertical_slice/`). v0 stays as the tool-surface baseline; this slice grades **discovery + selectivity + halt-when-done**.

**Two driver modes:**

- **Iteration 6 single-stage** (legacy, in this directory): `step1_timeline_pass_run.py [--per-slug]` runs the planner end-to-end on the recap. Single tool surface, autonomous-writes loopback. Best for testing the planner's own discovery/selectivity. **Cohort TP1: 0/5.**
- **Iteration 7 events-first chained** (current focus, lives in sibling slice): `evals/session_events_extraction_vertical_slice/step2_timeline_from_events_run.py` runs Stage A (events extraction) then per-slug Stage B (events-driven `append_timeline_row` micro-turns). Stage B never re-reads the recap. **Grades against this slice's gold unchanged** so iteration history is comparable. **Cohort TP1: 3/5; per-PC anchor gates 5/5 for `caelynn`/`karsemine`/`ephanna`.**

The chained-pipeline cohort row in the gate ledger uses this slice's `collect_timeline_pass_violations` and gold file. The split exists because events-first decomposition removed a compression failure mode that single-stage prompt-tuning couldn't close.

### Why one-phase autonomous writes

The dispatcher's `autonomous_writes=True` mode runs `append_timeline_row` through a one-phase loopback: the model sees a single tool call, the dispatcher internally runs `dry_run=True` then `dry_run=False` with the returned `confirm_token`, and only the commit-phase response is returned to the model. The writer's safety properties (allowlist, payload validators, `file_state_token` CAS) are preserved unchanged. Five iterations of dispatcher patches and prompt-tuning had failed to lift TP1 because the autonomous benchmark was being driven through a writer designed for human-in-the-loop ops; the structural fix removes the preview surface from the model rather than continuing to patch around it. See `.cursor/rules/corpus-two-phase-commit.mdc` for the scope/contract split between operator-driven and autonomous flows.

- **Spec:** [Docs/Plans/EXPERIMENT-Session-Recap-Timeline-Pass-Benchmark.md](../../Docs/Plans/EXPERIMENT-Session-Recap-Timeline-Pass-Benchmark.md)
- **Gate ledger:** [Docs/Plans/STATUS-Session-Recap-Timeline-Pass-Benchmark.md](../../Docs/Plans/STATUS-Session-Recap-Timeline-Pass-Benchmark.md)
- **Stage-1 artifact pinned in:** `gold/Session 20 - Recap.md`

## Pre-state corpus

Copies `corpus/eldyrwild-markdown`, strips Session-20 rows from the six expected APPEND-target timelines (Lysandra, Caelynn, Sara, Thrin, **Karsemine**, **Ephanna**), leaves the two SKIP-target timelines (Dustwalker, Torbin Jove) untouched, and overwrites the recap path from `gold/Session 20 - Recap.md`. The Karsemine and Ephanna PC hubs (`PCs/karsemine/`, `PCs/ephanna/`) are seeded with slim Backstory + Sessions 1, 3, 7 / 1, 2, 14 rows; the Session 20 strip is a documented no-op for those two.

**Campaign 1 (Stage B benchmarks):** `gold/timeline_pass_session{1,2,3}_c1.json` reference `pre_state_manifest_relative` manifests (`step0_pre_state_manifest_session*_c1.json`) that (1) **`delete_relative_paths`** — remove `Campaign 2/PCs/<slug>/timeline.md` for the six C1 PC slugs so slug-only `append_timeline_row` resolution is not ambiguous when both campaigns share a PC name; (2) **`copy_into_corpus`** — seed empty `Campaign 1/PCs/<slug>/timeline.md` from `gold/c1_pc_timeline_seeds/`; (3) **`remove_table_row_session_in`** — strip the benchmark session row if already present. Recaps are the canonical files already in the corpus under `Longmont Campaign/Campaign 1/Session Recaps/`.

```bash
uv run python -m evals.session_recap_timeline_pass_vertical_slice.step1_timeline_pass_run --print-root
```

## Offline tests

```bash
uv run pytest tests/test_timeline_pass_grader.py tests/test_timeline_pass_pre_state.py \
  tests/test_timeline_pass_per_slug_order.py tests/test_planner_hub_list_tools.py \
  tests/test_planner_autonomous_writes.py -q
```

## Live cohort

### Iteration 7 — events-first chained pipeline (current)

```bash
export DUNGEONMIND_PLANNER_ALLOW_WRITES=1
uv run python -m evals.session_events_extraction_vertical_slice.step2_timeline_from_events_run \
  --n 5 --model gpt-5.4-mini
```

Stage A extracts events; Stage B per-slug appends rows from those events. Per-PC anchor gates met at 5/5 in N=5 cohort. Cohort artifacts under `evals/session_events_extraction_vertical_slice/artifacts/runs/<YYYY-MM-DD>/step2_events_summary--*.{md,json}`.

### Iteration 6 — single-stage autonomous (legacy)

```bash
export DUNGEONMIND_PLANNER_ALLOW_WRITES=1
PLANNER_REVIEW_MODE=summary uv run python -m \
  evals.session_recap_timeline_pass_vertical_slice.step1_timeline_pass_run \
  --n 3 --model gpt-5.4-mini
```

Per-slug chain (higher API cost — eight model turns per benchmark run):

```bash
export DUNGEONMIND_PLANNER_ALLOW_WRITES=1
PLANNER_REVIEW_MODE=summary uv run python -m \
  evals.session_recap_timeline_pass_vertical_slice.step1_timeline_pass_run \
  --per-slug --n 3 --model gpt-5.4-mini
```

Artifacts: `artifacts/runs/<YYYY-MM-DD>/timeline_pass--*.{md,json}` and `artifacts/last_timeline_pass_run.{md,json}`.

Optional: `TIMELINE_PASS_RUNS_ROOT` to override the runs directory.

## Grading (summary — see EXPERIMENT for normative gate IDs)

- **TP1 APPEND completeness (count + flat-anchor-words):** for each `expected_appends` entry, the target timeline file must contain at least `expected_count` rows for Session 20, and every word in `anchor_words` must appear (case-insensitive substring) at least once across the union of those new rows' beat-cell text. Anchor lists live in gold (`grading.expected_appends[*].anchor_words`).
- **TP2 SKIP correctness:** no `**20**` row exists in any skip-target timeline.
- **TP3 Tool contract:** no `write_corpus_file`; none of `assemble_recap_draft` / `build_recap_write_payload` / `get_recap_context` fired.
- ~~**TP4 FLAG completeness**~~ — **removed in Iteration 6.** Hub-proposal evaluation is out of scope for this slice; revisit when timelines are reliably passing.
- **TP5 Hallucination guard:** every commit's `npc_slug` is in `allowed_npc_slugs`.
- **TP6 Pre-state offline:** six target rows absent + two skip-target rows match HEAD bytes (pytest).

Per-run telemetry surfaces `per_slug_new_row_count` and `per_slug_anchor_words_missing` so the qualitative-review pass has structured handles into each character's row contents.
