---
pr_body_template: |
  ## Summary
  **Session-memory canonicalization + doc tracker sync:** lift deterministic ingestion (`capture`, `breadcrumb_smoke`, `breadcrumb_normalize`) into `src/session_memory/` with eval shims and production scripts on `src`; include PLAN/CHECKLIST updates and `derive_stopwords` docstring reference fix. No retrieval, gold, or frozen-baseline changes.

  ## Verification (verbatim §7)
  {{paste after run}}

  ## `git diff --stat` (§4 paths only)
  ```text
  {{paste}}
  ```
---

# HANDOFF — PR #24: Canonical `src/session_memory/` package (Prime-Agent PR-A)

**Created:** 2026-05-14 (UTC).  
**Status:** OPEN — reviewed under [GitHub PR #24](https://github.com/Drakosfire/DungeonMindBuddy/pull/24) (branch `cursor/pr25-session-memory-canonical-src`; filename matches GitHub number).  
**Parent agent:** Prime coordinator (Cursor).  
**Plan anchor:** [PLAN-split-corpus-retrieval-to-autonomous-demo.md](PLAN-split-corpus-retrieval-to-autonomous-demo.md) — Prime-Agent Operating Reset PR-A (layering correction).

---

## §1 Mission

Move `capture.py`, `breadcrumb_smoke.py`, and `breadcrumb_normalize.py` to **`src/session_memory/`** as the canonical implementation, replace eval copies with **compatibility shims**, repoint **`scripts/materialize_session_memory.py`** and **`scripts/rebuild_breadcrumb_from_session_memory.py`** to import from `src` (not `evals`), and land the **atomic workstream doc sync** (PLAN + CHECKLIST) plus the harmless **`derive_stopwords.py`** module-reference docstring update.

## §2 Why this slice

- Prior state: corpus materialization imported from `evals/.../breadcrumb_normalize`, coupling production scripts to the benchmark tree.
- Target: `src`-owned ingestion boundary; benchmarks keep working via re-export shims.
- **In-scope alongside code:** super-plan **v32** changelog + `integration_notes`, checklist **session log** + super-plan pointer bump, and `src/token_resolution/derive_stopwords.py` docstring only (points canonical module at `src.session_memory.breadcrumb_normalize`).
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
| Create | `tests/test_session_memory_canonical_location.py` | Identity + AST guard: materialize avoids eval imports. |
| Modify | `Docs/Plans/PLAN-split-corpus-retrieval-to-autonomous-demo.md` | v32 changelog + `integration_notes` (doc-sync). |
| Modify | `Docs/Plans/CHECKLIST-dynamic-lexical-retrieval-rollout.md` | Session log + super-plan pointer v32 (doc-sync). |
| Create | `Docs/Plans/HANDOFF-pr24-session-memory-canonical-src-package.md` | This handoff (review contract). |
| Modify | `src/token_resolution/derive_stopwords.py` | Docstring: canonical module reference → `src.session_memory.breadcrumb_normalize`. |

> Expected `git diff --stat` MUST be expressible from this table (**14 paths**). Anything else is scope creep.

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
uv run pytest tests/test_cohort_baseline_run.py -q
```

## §9 Acceptance rubric

- [ ] Eval shims re-export same `normalize_breadcrumb_artifact` / `write_records_jsonl` objects as `src` — `test_session_memory_canonical_location`.
- [ ] `materialize_session_memory.py` contains no `from evals...` imports — AST test.
- [ ] `--all-blessed --check` passes — storage boundary.
- [ ] Default cohort `--check` passes — score-neutral harness boundary.
- [ ] **Scope:** no files outside §4 allowlist (14 paths) — `git diff --stat origin/main...HEAD` filtered to §4.

## §10 Notes

- GitHub opened this change set as **PR #24**; this handoff filename uses **pr24** to match. Earlier draft used “PR #25” in prose only — superseded by this file.
- Follow-up PR-B/C: extract `breadcrumb_query_run` kernel and replace cohort subprocess without touching this package layout.
