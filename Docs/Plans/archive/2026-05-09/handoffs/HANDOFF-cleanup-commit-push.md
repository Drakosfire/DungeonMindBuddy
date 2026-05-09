# HANDOFF: Cleanup, Commit & Push

**Date:** 2026-04-08  
**Status:** Ready for execution  
**Goal:** Stage all pending work, organize into clean commits, push to origin  

---

## 1. Current State

- **Branch:** `main` (ahead of `origin/main` by 7 commits — those are already committed)
- **Lint:** All files pass `ruff check` — zero violations
- **Tests:** 118/118 passing across all test files
- **No prior-committed files re-modified:** The earlier commit (`d18d7f5`) files (`.gitignore`, `schemas/`, `src/contracts/`, `src/ingestion/`, `src/store.py`, etc.) have no new changes

---

## 2. Pending Changes (Not Yet Committed)

### Modified files (12 files, ~2181 lines changed)


| File                                                                   | What changed                                                                            |
| ---------------------------------------------------------------------- | --------------------------------------------------------------------------------------- |
| `src/cli.py`                                                           | Evidence-first flags, context budget knobs, hybrid fusion, hard budget enforcement      |
| `src/agent/retriever.py`                                               | Attribute filter in `filter_projection`, semantic rerank option, stage-loss helpers     |
| `src/agent/context_formatter.py`                                       | `max_entities` override, `priority_entity_ids` front-loading                            |
| `src/agent/synthesis.py`                                               | Minor prompt/contract refinements                                                       |
| `evals/mirathorn_vertical_slice/run_council_room_question_set.py`      | Evidence-first env vars, stage-loss instrumentation, comparison payload, planner wiring |
| `evals/mirathorn_vertical_slice/gold/gold_questions.json`              | Expanded semantic equivalences, must_hit refinements                                    |
| `evals/mirathorn_vertical_slice/output/council_room_question_set.json` | Latest benchmark results artifact                                                       |
| `evals/mirathorn_vertical_slice/output/council_room_question_set.md`   | Latest benchmark report                                                                 |
| `tests/test_retriever.py`                                              | New tests for attribute filter, semantic rerank                                         |
| `tests/test_synthesis.py`                                              | Minor test updates                                                                      |
| `tests/evals/test_council_room_question_set.py`                        | `evidence_gap` stage-loss assertion                                                     |
| `tests/evals/test_council_room_scoring.py`                             | New scoring edge-case tests                                                             |


### New files (17 untracked)


| File                                                                            | Category     | Description                         |
| ------------------------------------------------------------------------------- | ------------ | ----------------------------------- |
| `src/agent/evidence_retriever.py`                                               | **Core**     | Evidence-first retrieval module     |
| `src/agent/query_planner.py`                                                    | **Core**     | LLM entity/attribute triage planner |
| `tests/test_evidence_retriever.py`                                              | **Tests**    | Evidence retriever unit tests       |
| `tests/test_query_planner.py`                                                   | **Tests**    | Query planner unit tests            |
| `evals/mirathorn_vertical_slice/embedding_scorer.py`                            | **Evals**    | Embedding similarity scorer         |
| `evals/mirathorn_vertical_slice/claim_verifier.py`                              | **Evals**    | Claim verification evaluator        |
| `tests/evals/test_embedding_scorer.py`                                          | **Tests**    | Embedding scorer tests              |
| `tests/evals/test_claim_verifier.py`                                            | **Tests**    | Claim verifier tests                |
| `evals/mirathorn_vertical_slice/output/council_room_trace.jsonl`                | **Artifact** | Per-question trace log              |
| `evals/mirathorn_vertical_slice/output/rubric_alignment_eval_no_benchmark.json` | **Artifact** | Rubric alignment eval output        |
| `evals/mirathorn_vertical_slice/output/stage_loss_deep_dive_no_planner.json`    | **Artifact** | Stage-loss deep dive output         |
| `Docs/Plans/archive/2026-05-09/handoffs/HANDOFF-answer-accuracy-measurement.md`                             | **Docs**     | Handoff doc                         |
| `Docs/Plans/archive/2026-05-09/handoffs/HANDOFF-embedding-scoring-refinement.md`                            | **Docs**     | Handoff doc                         |
| `Docs/Plans/archive/2026-05-09/handoffs/HANDOFF-qa-synthesis-system-design-review.md`                       | **Docs**     | Handoff doc                         |
| `Docs/Plans/archive/2026-05-09/handoffs/HANDOFF-retrieval-architecture-and-gap-analysis.md`                 | **Docs**     | Handoff doc                         |
| `Docs/Plans/archive/2026-05-09/reports/REPORT-answer-accuracy-measurement-execution-2026-04-07.md`         | **Docs**     | Report                              |
| `Docs/Plans/archive/2026-05-09/reports/REPORT-embedding-scoring-session.md`                                | **Docs**     | Report                              |


---

## 3. Recommended Commit Plan

Three commits, from foundational to dependent:

### Commit 1: `feat(agent): add query planner and evidence-first retrieval modules`

New core agent modules and their tests.

**Stage these files:**

```
src/agent/query_planner.py
src/agent/evidence_retriever.py
tests/test_query_planner.py
tests/test_evidence_retriever.py
```

### Commit 2: `feat(agent): wire evidence-first retrieval, context budgets, and stage-loss instrumentation`

All modifications to the pipeline — CLI, retriever, formatter, synthesis, eval runner, gold questions, and their test updates.

**Stage these files:**

```
src/cli.py
src/agent/retriever.py
src/agent/context_formatter.py
src/agent/synthesis.py
evals/mirathorn_vertical_slice/run_council_room_question_set.py
evals/mirathorn_vertical_slice/gold/gold_questions.json
tests/test_retriever.py
tests/test_synthesis.py
tests/evals/test_council_room_question_set.py
tests/evals/test_council_room_scoring.py
```

### Commit 3: `feat(evals): add embedding scorer, claim verifier, and benchmark artifacts`

Eval tooling, eval artifacts, and documentation.

**Stage these files:**

```
evals/mirathorn_vertical_slice/embedding_scorer.py
evals/mirathorn_vertical_slice/claim_verifier.py
tests/evals/test_embedding_scorer.py
tests/evals/test_claim_verifier.py
evals/mirathorn_vertical_slice/output/council_room_question_set.json
evals/mirathorn_vertical_slice/output/council_room_question_set.md
evals/mirathorn_vertical_slice/output/council_room_trace.jsonl
evals/mirathorn_vertical_slice/output/rubric_alignment_eval_no_benchmark.json
evals/mirathorn_vertical_slice/output/stage_loss_deep_dive_no_planner.json
Docs/Plans/archive/2026-05-09/handoffs/HANDOFF-answer-accuracy-measurement.md
Docs/Plans/archive/2026-05-09/handoffs/HANDOFF-embedding-scoring-refinement.md
Docs/Plans/archive/2026-05-09/handoffs/HANDOFF-qa-synthesis-system-design-review.md
Docs/Plans/archive/2026-05-09/handoffs/HANDOFF-retrieval-architecture-and-gap-analysis.md
Docs/Plans/archive/2026-05-09/reports/REPORT-answer-accuracy-measurement-execution-2026-04-07.md
Docs/Plans/archive/2026-05-09/reports/REPORT-embedding-scoring-session.md
```

---

## 4. Pre-Commit Checklist

All of these are already verified as of this handoff:

- `uv run ruff check` on all files: **All checks passed**
- `uv run pytest` on all test files: **118/118 passed**
- No `.env`, credentials, or secrets in any staged file
- No `.cache/` directories (already in `.gitignore`)
- Benchmark output artifacts are deterministic pipeline products (safe to commit)

---

## 5. Post-Commit: Push

After all three commits:

```bash
git push origin main
```

The remote is HTTPS (`https://github.com/Drakosfire/DungeonMindBuddy.git`). If push fails due to auth, the user will need to push manually from an authenticated terminal.

---

## 6. Files to NOT commit

- `.cache/` — already gitignored (HuggingFace model caches)
- Any `.env*` files
- This handoff file itself (`Docs/Plans/archive/2026-05-09/handoffs/HANDOFF-cleanup-commit-push.md`) — include it in Commit 3 with the other docs if desired, or skip it

