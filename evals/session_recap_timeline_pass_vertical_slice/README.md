# Session recap → autonomous timeline pass (Stage-2 v1 vertical slice)

**What this slice grades:** After Stage-1 has committed `Session 20 - Recap.md`, the planner performs an **autonomous** turn (no recap-write skill) over a pre-loaded list of six existing C2 timeline files. For each: read the recap, decide whether the NPC has a meaningful Session-20 beat, and if yes append a row via two-phase `append_timeline_row`. Skip the rest. Surface NPCs prominent in the recap who lack a hub (`unsure_queue` `hub-proposal:` prefix).

This is the autonomous sibling of the v0 operator-instructed slice (`session_recap_timeline_append_vertical_slice/`). v0 stays as the tool-surface baseline; this slice grades **discovery + selectivity + halt-when-done**.

- **Spec:** [Docs/Plans/EXPERIMENT-Session-Recap-Timeline-Pass-Benchmark.md](../../Docs/Plans/EXPERIMENT-Session-Recap-Timeline-Pass-Benchmark.md)
- **Gate ledger:** [Docs/Plans/STATUS-Session-Recap-Timeline-Pass-Benchmark.md](../../Docs/Plans/STATUS-Session-Recap-Timeline-Pass-Benchmark.md)
- **Stage-1 artifact pinned in:** `gold/Session 20 - Recap.md`

## Pre-state corpus

Copies `corpus/eldyrwild-markdown`, strips Session-20 rows from the four expected APPEND-target timelines (Lysandra, Caelynn, Sara, Thrin), leaves the two SKIP-target timelines (Dustwalker, Torbin Jove) untouched, and overwrites the recap path from `gold/Session 20 - Recap.md`.

```bash
uv run python -m evals.session_recap_timeline_pass_vertical_slice.step1_timeline_pass_run --print-root
```

## Offline tests

```bash
uv run pytest tests/test_timeline_pass_grader.py tests/test_timeline_pass_pre_state.py -q
```

## Live cohort

```bash
export DUNGEONMIND_PLANNER_ALLOW_WRITES=1
PLANNER_REVIEW_MODE=summary uv run python -m \
  evals.session_recap_timeline_pass_vertical_slice.step1_timeline_pass_run \
  --n 3 --model gpt-5.4-mini
```

Artifacts: `artifacts/runs/<YYYY-MM-DD>/timeline_pass--*.{md,json}` and `artifacts/last_timeline_pass_run.{md,json}`.

Optional: `TIMELINE_PASS_RUNS_ROOT` to override the runs directory.

## Grading (summary — see EXPERIMENT for normative gate IDs)

- **TP1 APPEND completeness:** preview→commit landed for all four expected targets; each row passes the v0 hybrid rubric.
- **TP2 SKIP correctness:** no `**20**` row exists in either skip-target timeline.
- **TP3 Tool contract:** preview→commit ordering per slug; no `write_corpus_file`; no recap-assembly tools.
- **TP4 FLAG completeness:** `unsure_queue` substring matches each must-flag (`karsemine`, `ephanna`, `stafl`, `marla`).
- **TP5 Hallucination guard:** every commit's `npc_slug` is in `allowed_npc_slugs`.
- **TP6 Pre-state offline:** four target rows absent + two skip-target rows match HEAD bytes (pytest).

## Hub-proposal queue convention

Per-item shape (snake_case `id`; literal `hub-proposal:` prefix in `question`):

```json
{
  "id": "hub_proposal_karsemine",
  "question": "hub-proposal: karsemine — appears in S20 swarm fight + recap, no NPC hub exists",
  "default_summary": "Create empty NPCs/karsemine/{README.md,timeline.md} skeleton.",
  "alternative_summaries": ["...", "..."]
}
```

The grader matches must-flag names case-insensitively against the concatenation of `id`, `question`, `default_summary`, and `alternative_summaries` for each queue item.
