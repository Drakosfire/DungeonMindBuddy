---
pr_body_template: |
  ## Summary
  Lift deterministic session-memory ingestion (`capture`, `breadcrumb_smoke`, `breadcrumb_normalize`) into `src/session_memory/`; eval modules become thin shims; production scripts import from `src`. No retrieval, gold, or frozen-baseline changes.

  ## Verification (verbatim §7)
  {{paste after run}}

  ## `git diff --stat` (§4 paths only)
  ```text
  {{paste}}
  ```
---

# HANDOFF — PR #25: Canonical `src/session_memory/` package (Prime-Agent PR-A)

**Created:** 2026-05-14 (UTC).  
**Status:** COMPLETED in-IDE — landed **`c71d438989a223a201de55b56e4cb423eae59ccf`** (`refactor(session_memory): canonical src/session_memory package (PR-A)`). Open GitHub PR if remote review required.  
**Parent agent:** Prime coordinator (Cursor).  
**Plan anchor:** [PLAN-split-corpus-retrieval-to-autonomous-demo.md](PLAN-split-corpus-retrieval-to-autonomous-demo.md) — Prime-Agent Operating Reset PR-A (layering correction).

---

## §1 Mission

Move `capture.py`, `breadcrumb_smoke.py`, and `breadcrumb_normalize.py` to **`src/session_memory/`** as the canonical implementation, replace eval copies with **compatibility shims**, and repoint **`scripts/materialize_session_memory.py`** and **`scripts/rebuild_breadcrumb_from_session_memory.py`** to import from `src` (not `evals`).

## §2 Why this slice

- Prior state: corpus materialization (`materialize_session_memory.py`) imported from `evals/.../breadcrumb_normalize`, coupling production scripts to the benchmark tree.
- Target: `src`-owned ingestion boundary per Prime-Agent reset plan; benchmarks keep working via re-export shims.
- Out of scope: `breadcrumb_query_run.py`, `cohort_baseline_run.py`, `session_memory_query.py`, gold, frozen baselines, prompts, canvases.

## §3 Authoritative inputs

1. `.cursor/rules/external-agent-pr-loop.mdc`
2. [scripts/materialize_session_memory.py](scripts/materialize_session_memory.py)
3. Prior eval modules (now shims): `evals/sentence_routing_retrieval_falsification/{capture,breadcrumb_smoke,breadcrumb_normalize}.py`

## §4 Files in scope (allowlist)

| Action | Path | Purpose |
|--------|------|---------|
| Create | `src/session_memory/__init__.py` | Public exports for normalization API. |
| Create | `src/session_memory/capture.py` | Canonical Stage-A capture (moved). |
| Create | `src/session_memory/breadcrumb_smoke.py` | Canonical smoke/parsing helpers (moved). |
| Create | `src/session_memory/breadcrumb_normalize.py` | Canonical normalize + JSONL writer (moved). |
| Modify | `evals/sentence_routing_retrieval_falsification/capture.py` | Shim → `src.session_memory.capture`. |
| Modify | `evals/sentence_routing_retrieval_falsification/breadcrumb_smoke.py` | Shim → `src.session_memory.breadcrumb_smoke`. |
| Modify | `evals/sentence_routing_retrieval_falsification/breadcrumb_normalize.py` | Shim → `src.session_memory.breadcrumb_normalize`. |
| Modify | `scripts/materialize_session_memory.py` | Import from `src.session_memory.breadcrumb_normalize`. |
| Modify | `scripts/rebuild_breadcrumb_from_session_memory.py` | Import from `src.session_memory`. |
| Create | `tests/test_session_memory_canonical_location.py` | Identity + AST guard: scripts avoid eval imports. |

## §5 Denylist

| Path | Reason |
|------|--------|
| `src/agent/session_memory_query.py` | Retrieval — not this slice. |
| `evals/.../breadcrumb_query_run.py`, `cohort_baseline_run.py` | Harness behavior unchanged beyond shim transparency. |
| `evals/.../gold/*`, `artifacts/baselines/*` | No rubric drift. |

## §7 Verification commands

```bash
uv run pytest tests/test_session_memory_canonical_location.py tests/test_sentence_routing_capture.py tests/test_breadcrumb_smoke.py -q
uv run pytest tests/test_breadcrumb_natural_query.py tests/test_session_memory_query.py -q
uv run pytest tests/test_breadcrumb_query_run_lexicon_records_jsonl.py tests/test_breadcrumb_unit_annotations.py tests/test_breadcrumb_routing_only_ingest.py -q
uv run python scripts/materialize_session_memory.py --all-blessed --check
uv run python -m evals.sentence_routing_retrieval_falsification.cohort_baseline_run --check
```

## §9 Acceptance rubric

- [ ] Eval shims re-export same `normalize_breadcrumb_artifact` / `write_records_jsonl` objects as `src` — `test_session_memory_canonical_location`.
- [ ] `materialize_session_memory.py` contains no `from evals...` imports — AST test.
- [ ] `--all-blessed --check` passes — storage boundary.
- [ ] Default cohort `--check` passes — score-neutral harness boundary.
- [ ] No paths outside §4 touched.

## §10 Notes

- Follow-up PR-B/C: extract `breadcrumb_query_run` kernel and replace cohort subprocess without touching this package layout.
