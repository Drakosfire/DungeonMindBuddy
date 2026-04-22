# Session recap → autonomous timeline pass (Stage-2 v1 vertical slice)

**What this slice grades:** After Stage-1 has committed `Session 20 - Recap.md`, the planner performs an **autonomous** turn (no recap-write skill) over a pre-loaded list of eight existing C2 timeline files. For each: read the recap, decide whether the NPC/PC has a meaningful Session-20 beat, and if yes append a row via **one-phase** `append_timeline_row` (the call commits). Skip the rest. Hub-proposal evaluation is **out of scope for this slice** as of Iteration 6.

This is the autonomous sibling of the v0 operator-instructed slice (`session_recap_timeline_append_vertical_slice/`). v0 stays as the tool-surface baseline; this slice grades **discovery + selectivity + halt-when-done**.

**Iteration 6 runner mode:** pass `--per-slug` to chain **eight** single-subject Responses micro-turns (one slug at a time) on the same `previous_response_id` thread. Artifacts use `--8turn--` in the basename instead of `--1turn--`. The hub-proposal micro-turn was removed in Iteration 6 alongside TP4. The planner still exposes read-only **`list_npc_hubs`** / **`list_pc_hubs`** tools for deterministic hub discovery, used by the runner pre-state and by future hub-proposal slices.

### Why one-phase autonomous writes

The dispatcher's `autonomous_writes=True` mode runs `append_timeline_row` through a one-phase loopback: the model sees a single tool call, the dispatcher internally runs `dry_run=True` then `dry_run=False` with the returned `confirm_token`, and only the commit-phase response is returned to the model. The writer's safety properties (allowlist, payload validators, `file_state_token` CAS) are preserved unchanged. Five iterations of dispatcher patches and prompt-tuning had failed to lift TP1 because the autonomous benchmark was being driven through a writer designed for human-in-the-loop ops; the structural fix removes the preview surface from the model rather than continuing to patch around it. See `.cursor/rules/corpus-two-phase-commit.mdc` for the scope/contract split between operator-driven and autonomous flows.

- **Spec:** [Docs/Plans/EXPERIMENT-Session-Recap-Timeline-Pass-Benchmark.md](../../Docs/Plans/EXPERIMENT-Session-Recap-Timeline-Pass-Benchmark.md)
- **Gate ledger:** [Docs/Plans/STATUS-Session-Recap-Timeline-Pass-Benchmark.md](../../Docs/Plans/STATUS-Session-Recap-Timeline-Pass-Benchmark.md)
- **Stage-1 artifact pinned in:** `gold/Session 20 - Recap.md`

## Pre-state corpus

Copies `corpus/eldyrwild-markdown`, strips Session-20 rows from the six expected APPEND-target timelines (Lysandra, Caelynn, Sara, Thrin, **Karsemine**, **Ephanna**), leaves the two SKIP-target timelines (Dustwalker, Torbin Jove) untouched, and overwrites the recap path from `gold/Session 20 - Recap.md`. The Karsemine and Ephanna PC hubs (`PCs/karsemine/`, `PCs/ephanna/`) are seeded with slim Backstory + Sessions 1, 3, 7 / 1, 2, 14 rows; the Session 20 strip is a documented no-op for those two.

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
