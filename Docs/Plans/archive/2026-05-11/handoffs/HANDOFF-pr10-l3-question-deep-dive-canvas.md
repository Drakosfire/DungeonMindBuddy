---
# Optional workflow contract: literal markdown the worker pastes into the
# GitHub PR description.
pr_body_template: |
  ## Summary
  Add a deterministic per-question L3 A/B artifact and a dedicated deep-dive canvas emitter so every query in `c1s1_to_c1s3_v1` can be reviewed in a collapsible baseline-vs-with-equivalence accordion.

  ## Verification (verbatim §7)
  {{TODO: paste command outputs after the worker runs §7}}

  ## `git diff --stat` (§4 paths only)
  ```text
  {{TODO}}
  ```
---

# HANDOFF — PR #10: L3 per-question deep-dive artifact + review canvas

**Created:** 2026-05-11 (UTC).
**Status:** COMPLETED — merged via [PR #10](https://github.com/Drakosfire/DungeonMindBuddy/pull/10) on 2026-05-11T14:54:48Z (merge commit `c75c3f6b622b35658eafd0a5b1641421b791357e`). Review round: 1 (`APPROVE` demoted to `COMMENTED` under self-review fallback, review id `4264759583`).
**Parent agent:** Cursor agent; dispatcher is responsible for post-merge atomic doc-sync of `Docs/Plans/CHECKLIST-dynamic-lexical-retrieval-rollout.md` and `Docs/Plans/PLAN-split-corpus-retrieval-to-autonomous-demo.md`.
**Plan anchor:** `Docs/Plans/PLAN-split-corpus-retrieval-to-autonomous-demo.md` (`active_phase: B`, `M2: in_progress`, `M3: complete`, `M4: not_started`). This handoff is a post-PR #9 understanding/diagnostics slice; it does not promote retrieval defaults.

---

## §1 Mission

Add a deterministic per-question L3 A/B artifact plus a dedicated canvas emitter that renders one collapsible deep-dive card per query (baseline vs with-equivalence) for the `c1s1_to_c1s3_v1` cohort, with reproducible `--write`/`--check` gates and no retrieval-path behavior changes.

## §2 Why this slice (context for the subagent)

- PR #9 landed scenario-level L3 delta (`cohort_l3_ab_delta_c1s1_to_c1s3_v1.json`) and proved the gated ranking flag can regress on the tight cohort (baseline 3/3 vs with-equivalence 1/3).
- Scenario-level deltas are not enough for judgment calls; operators need per-query evidence showing route-coverage, must-hit/support, promoted context behavior, and top-hit differences side-by-side.
- This slice intentionally does **not** change scoring logic, alias-construction logic, route-equivalence producer artifacts, or default retrieval wiring; it only adds deterministic diagnostics and a review surface.

## §3 Authoritative inputs (read these in this order, before writing any code)

1. **`.cursor/rules/external-agent-pr-loop.mdc`** — non-negotiable §4/§5/§7/§9 contract.
2. `Docs/Plans/PLAN-split-corpus-retrieval-to-autonomous-demo.md` — current Phase B/M3 state, PR #9 rubric bullets, and `next_gate_command`.
3. `Docs/Plans/CHECKLIST-dynamic-lexical-retrieval-rollout.md` — Reanchor block + Phase C evidence language.
4. `evals/sentence_routing_retrieval_falsification/cohort_baseline_run.py` — existing `--mode both`, `_build_l3_delta`, `--write-delta` / `--check-delta`.
5. `evals/sentence_routing_retrieval_falsification/breadcrumb_query_run.py` — row fields available for deep-dive extraction (`full_result.hits`, `retrieved_context`, `expected_route_substring_breakdown`, `context_must_hits`, `context_support_ratio`, `violations`, `ranking_augmented_by_equivalences`).
6. `tests/test_cohort_baseline_run.py` — existing regression and delta tests to extend.
7. `evals/sentence_routing_retrieval_falsification/c1s1_benchmark_canvas_emit.py` and `canvases/c1s1-breadcrumb-query-benchmark-review.canvas.tsx` — canonical emitter/template pattern for generated canvas payloads.
8. **`tests/conftest.py`** — confirm env bootstrap expectations (no exported key assumptions).

## §4 Files in scope (allowlist)

| Action | Path | Purpose |
|---|---|---|
| Modify | `evals/sentence_routing_retrieval_falsification/cohort_baseline_run.py` | Add per-question deep-dive summary builder and deterministic `--write-question-delta` / `--check-question-delta` CLI contract (separate from existing scenario-level delta). |
| Create | `evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_l3_ab_question_delta_c1s1_to_c1s3_v1.json` | Committed deterministic per-question deep-dive artifact generated from `--mode both`. |
| Create | `evals/sentence_routing_retrieval_falsification/cohort_l3_question_deep_dive_canvas_emit.py` | Deterministic emitter that reads the committed per-question artifact and writes `canvases/cohort-l3-ab-question-deep-dive.canvas.tsx`. |
| Create | `canvases/cohort-l3-ab-question-deep-dive.canvas.tsx` | Canvas template/output with one collapsible deep-dive card per query (44 total). |
| Modify | `tests/test_cohort_baseline_run.py` | Add tests for question-delta schema, deterministic `--check-question-delta`, and CWD invariance for question-delta output. |
| Create | `tests/test_cohort_l3_question_deep_dive_canvas_emit.py` | Add emitter contract tests (schema load, deterministic output markers, expected question count rendered). |

> Expected diff stat shape: **6 paths** exactly. If extra paths appear, revert them before opening the PR.

## §5 Files explicitly OUT OF SCOPE (denylist)

Do NOT touch any of these:

| Path | Why this PR must not touch it |
|---|---|
| `src/agent/session_memory_query.py` | Retrieval/scoring behavior is intentionally frozen for this diagnostics slice. |
| `evals/sentence_routing_retrieval_falsification/breadcrumb_query_run.py` | Input harness contract already landed in PR #9; this slice only consumes its existing outputs. |
| `evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_baseline_c1s1_to_c1s3_v2.json` | Existing frozen baseline anchor; must remain byte-identical. |
| `evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_l3_ab_delta_c1s1_to_c1s3_v1.json` | Existing scenario-level delta anchor; do not mutate in this PR. |
| `evals/sentence_routing_retrieval_falsification/artifacts/lexicon/*.jsonl` | Producer artifacts are inputs only. |
| `evals/sentence_routing_retrieval_falsification/gold/**` | Gold deflation risk; this PR is diagnostics-only. |
| `src/lexicon_phase_b/**` | Producer lane is out of scope. |
| `Docs/Plans/**` (except this handoff is read-only) | Post-merge doc-sync belongs to parent, not worker. |
| `src/prompts/**` | Forbidden by scope and risk profile. |

If a denylisted file appears necessary, stop and ask in PR body before proceeding.

## §6 Implementation contract

### §6.1 Per-question L3 artifact in `cohort_baseline_run.py`

Add a new deterministic artifact schema:

```json
{
  "schema_id": "dmb_breadcrumb_query_cohort_l3_question_delta_v1",
  "cohort_manifest": "evals/.../cohorts/c1s1_to_c1s3_v1.json",
  "scenario_level_delta_path": "evals/.../artifacts/baselines/cohort_l3_ab_delta_c1s1_to_c1s3_v1.json",
  "baseline_schema": "dmb_breadcrumb_query_cohort_summary_v2",
  "question_count": 44,
  "summary": {
    "regressed": 0,
    "improved": 0,
    "unchanged_pass": 0,
    "unchanged_fail": 0
  },
  "scenarios": [
    {
      "scenario_id": "c1s1",
      "question_count": 16,
      "baseline_pass_count": 16,
      "with_equivalence_pass_count": 15,
      "questions": [
        {
          "question_id": "c1s1_...",
          "question": "...",
          "expected_answer": "...",
          "must_hit_tokens": ["..."],
          "expected_route_substrings": ["..."],
          "min_context_support_ratio": 0.55,
          "baseline": {
            "ok": true,
            "violations": [],
            "context_support_ratio": 1.0,
            "context_must_hits": ["..."],
            "semantic_verdict": "pass_updated",
            "expected_route_substring_breakdown": [{"substring":"...","matched":true}],
            "hit_count": 18,
            "ranking_augmented_by_equivalences": false,
            "top_hits": [{"unit_id":"...","score":15,"line_start":3,"line_end":3,"routes":["..."],"why_matched":["..."]}]
          },
          "with_equivalence": { "... same shape ...", "ranking_augmented_by_equivalences": true },
          "delta": {
            "verdict": "regressed|improved|unchanged_pass|unchanged_fail",
            "support_ratio_delta": -0.5,
            "tokens_added_by_equivalences": ["..."],
            "tokens_removed_by_equivalences": [],
            "topk_units_swapped_in": ["..."],
            "topk_units_swapped_out": ["..."],
            "substrings_flipped_lost": [],
            "substrings_flipped_gained": []
          }
        }
      ]
    }
  ]
}
```

Rules:
- Build this artifact from the same `--mode both` run data; do not add extra retrieval runs.
- Deterministic ordering:
  - scenarios ordered by manifest order,
  - questions ordered by gold scenario order,
  - `top_hits` ordered by retrieval rank and capped to top 5 for artifact size discipline,
  - arrays in `delta` sorted.
- `tokens_added_by_equivalences` and `tokens_removed_by_equivalences` are set differences of `full_result.trace.query_tokens`.
- Keep existing scenario-level delta behavior unchanged.

CLI additions:
- `--write-question-delta [PATH]` (default path is the committed baseline above when flag provided without arg).
- `--check-question-delta [PATH]` (default path same as above).
- `--check-question-delta` regenerates into temp and byte-compares like existing `--check`/`--check-delta`.

### §6.2 Dedicated canvas emitter

Create `cohort_l3_question_deep_dive_canvas_emit.py` with deterministic emitter pattern:
- Input: committed question-delta JSON.
- Output: `canvases/cohort-l3-ab-question-deep-dive.canvas.tsx`.
- Include a generated payload block marker (`BEGIN GENERATED ...` / `END GENERATED ...`) and keep logic/template outside the block.
- Render one collapsible card per question (44 total) with:
  - baseline and with-equivalence side-by-side summaries,
  - route breakdown table per mode,
  - top-hit table per mode,
  - delta panel (verdict, support ratio delta, token diff, top-k swap diff).
- Default open only for `regressed` and `improved` questions.

Do not depend on external files at canvas runtime; inline payload in TSX.

## §7 Verification commands

Run all commands and paste outputs verbatim in PR body.

```bash
# 1) Existing lexicon lane remains green (producer untouched).
uv run pytest tests/lexicon_phase_b/ -q

# 2) Cohort runner suite including new question-delta tests.
uv run pytest tests/test_cohort_baseline_run.py -q

# 3) New canvas emitter tests.
uv run pytest tests/test_cohort_l3_question_deep_dive_canvas_emit.py -q

# 4) Existing baseline/delta checks still pass unchanged.
uv run python -m evals.sentence_routing_retrieval_falsification.cohort_baseline_run --check
uv run python -m evals.sentence_routing_retrieval_falsification.cohort_baseline_run --check-delta

# 5) New question-delta write smoke + key summary.
uv run python -m evals.sentence_routing_retrieval_falsification.cohort_baseline_run --mode both --write-question-delta /tmp/pr10_question_delta_smoke.json && uv run python -c "import json; d=json.load(open('/tmp/pr10_question_delta_smoke.json')); print(d['schema_id']); print('question_count', d['question_count']); print('summary', d['summary'])"

# 6) New question-delta check against committed artifact.
uv run python -m evals.sentence_routing_retrieval_falsification.cohort_baseline_run --check-question-delta

# 7) Canvas emit smoke: regenerate canvas and print question-card count marker.
uv run python -m evals.sentence_routing_retrieval_falsification.cohort_l3_question_deep_dive_canvas_emit && uv run python -c "from pathlib import Path; p=Path('canvases/cohort-l3-ab-question-deep-dive.canvas.tsx'); t=p.read_text(encoding='utf-8'); print('canvas_exists', p.exists()); print('has_generated_markers', 'BEGIN GENERATED' in t and 'END GENERATED' in t); print('question_count_literal', 'question_count' in t)"
```

## §8 Reporting contract

PR body must include:

1. `git diff --stat origin/main...HEAD` for §4 paths only (exactly 6 rows).
2. Verbatim output for all §7 commands.
3. One paragraph “what stayed unchanged” explicitly stating:
   - default baseline check unchanged,
   - scenario-level L3 delta check unchanged,
   - retriever implementation untouched,
   - gold untouched,
   - route-equivalence producer artifacts untouched.

## §9 Acceptance rubric

- [ ] New question-delta artifact is deterministic, schema-valid, and reports `question_count: 44` with summary buckets (`regressed`, `improved`, `unchanged_pass`, `unchanged_fail`) — verified by §7 #5 and §7 #6.
- [ ] Existing baseline (`--check`) and scenario-level L3 delta (`--check-delta`) remain green and byte-stable — verified by §7 #4.
- [ ] Question-level entries preserve route-vs-support distinction (route substrings can remain matched while support ratio drops) with both mode panels present — verified by artifact inspection in §7 #5 and canvas render in §7 #7.
- [ ] Canvas emitter is deterministic and writes the expected generated block markers in the target canvas file — verified by §7 #3 and §7 #7.
- [ ] No files outside §4 are touched — verified by allowlisted diff-stat.
- [ ] Cost remains retrieval-only for new artifact generation (no new LLM calls in this slice) — verified by code path and §7 command set.

> Reviewer reminder: validate behavior at the harness boundary (`cohort_baseline_run --mode both --write-question-delta` + `--check-question-delta`), not only helper-unit tests.

## §10 Out-of-band notes (optional)

- This slice is diagnostics-only; it does not attempt relevance-gated aliasing or retrieval-policy changes.
- If the generated canvas file size grows substantially, keep top-hit payload capped (top 5) rather than widening scope to compression/refactors.
- Post-merge parent should update PLAN/CHECKLIST with a precise “question-level blast radius” sentence derived from committed artifact counts.

---

**End of handoff.** Dispatcher next step after PR opens:
`uv run python scripts/review_external_pr.py fetch 10 --handoff Docs/Plans/HANDOFF-pr10-l3-question-deep-dive-canvas.md --extract-rubric`
