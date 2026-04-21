# Session recap ingest benchmark — gate status

**Spec:** [EXPERIMENT-Session-Recap-Ingest-Benchmark.md](EXPERIMENT-Session-Recap-Ingest-Benchmark.md) (gate definitions in §5; current architecture in §15).
**Scope-B contract:** [SCOPE-B-GOLD-Session-20-Ingest.md](SCOPE-B-GOLD-Session-20-Ingest.md) §J.
**Last cohort run:** 2026-04-19, 5/5 PASS, `recap_ingest_summary--gpt-5.4-mini--N5--20260419T214553Z.{md,json}`.

Update the **Last verified** column whenever you re-run the listed command. This file is the **living** pass/fail ledger; the experiment doc §5 remains the normative gate list.

---

## Legend


| Status          | Meaning                                                                                                                                 |
| --------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| **PASS**        | Automated test or benchmark gate green on last run; cited artifact reproduces it.                                                       |
| **PASS (live)** | Live-API benchmark gate green on the cited cohort run.                                                                                  |
| **PARTIAL**     | Some automation exists; not all sub-criteria exercised end-to-end.                                                                      |
| **OPEN**        | No automation wired; gate not proven for this benchmark yet.                                                                            |
| **DEFERRED**    | Out of scope for the current implementation; tracked in [BACKLOG-session-recap-benchmarking.md](BACKLOG-session-recap-benchmarking.md). |


---

## Scope-A (mechanical recap, no LLM)


| Gate | Status | Last verified | How verified                                                                           |
| ---- | ------ | ------------- | -------------------------------------------------------------------------------------- |
| A1   | PASS   | 2026-04-18    | Subsumed by A8; fields match gold frontmatter.                                         |
| A2   | PASS   | 2026-04-18    | Subsumed by A8.                                                                        |
| A3   | PASS   | 2026-04-18    | `tests/test_recap_ingest_helpers.py::test_split_paragraphs_session_20_counts`; A8.     |
| A4   | PASS   | 2026-04-18    | `tests/test_recap_ingest_helpers.py::test_detect_duplicates_session_20_lines_6_and_10` |
| A5   | PASS   | 2026-04-18    | `tests/test_recap_ingest_helpers.py::test_assemble_body_not_leading_title`             |
| A6   | PASS   | 2026-04-18    | Covered by Session 20 fixture + splitter tests; A8.                                    |
| A7   | PASS   | 2026-04-18    | `tests/test_recap_ingest_helpers.py::test_assemble_body_matches_gold_body`             |
| A8   | PASS   | 2026-04-18    | `tests/test_session_20_scope_a_gold.py::test_session_20_recap_byte_equal_to_gold`      |


**Batch command (Scope-A):**

```bash
uv run pytest tests/test_recap_ingest_helpers.py tests/test_session_20_scope_a_gold.py -q
```

---

## Scope-B (live planner; mechanical Scope-B grader)

The Scope-B benchmark now has its own grader (`evals/session_recap_ingest_vertical_slice/scope_b_grader.py`),
invoked from `step1_recap_ingest_run.py` (there is no separate `step2_grade_against_gold` module),
that asserts a smaller, mechanical contract than the original §J item-by-item gold:

- exactly one `get_recap_context` call with **unpinned** args (`campaign_id` / `target_session` empty),
- every subsequent `read_corpus_file` / `load_context_markdown` path is in `recent_recaps[].path` ∪ `prep_doc_path` (∪ scenario-supplied `read_allowlist_extra`),
- exactly one `assemble_recap_draft` call whose `target_session` and `campaign_id` match the snapshotted `RecapContext`,
- `write_corpus_file` preview/commit phases satisfy `preview_required` / `commit_required` knobs in the gold scenario,
- the planner's final assistant message contains a top-level `recap_write` field that parses + validates as `recap_write_v1`.

This contract maps onto the original §J gates as follows:


| Original gate                             | Scope-B grader coverage                                                                                                                                                                                                                                                   | Status                          | Notes                                                                  |
| ----------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------- | ---------------------------------------------------------------------- |
| B1 (recap byte-equal)                     | **Indirect:** mechanical assembly is forced via `assemble_recap_draft`; tool returns deterministic `recap_body`; `write_corpus_file` `mode=create` for the recap path. Byte-equal is not re-asserted live, but the path that produced it is now mechanically constrained. | PASS (live) — 2026-04-19 cohort | Byte-equal still proven by Scope-A A8 against the same helpers.        |
| B2 (Lysandra timeline)                    | **DEFERRED.** Single-turn ingest demonstrates `npc_audit.timeline_append_candidates` discovery in `recap_write_v1`. Live append of `append_timeline_row` is not exercised by the current scenario.                                                                        | DEFERRED                        | Tracked: backlog item "two-phase append for Lysandra row in followup". |
| B3, B5, B6 (setting-hub seeds byte-equal) | **DEFERRED.** Setting-hub creation not yet in scope of recap-write skill in this benchmark; gold remains byte-equal contract on disk.                                                                                                                                     | DEFERRED                        | See backlog "expand recap-write to dual-hub create".                   |
| B4 (Marla campaign hub shape)             | **DEFERRED.** Campaign-hub dossier path requires resolving the open question in EXPERIMENT §12.2.                                                                                                                                                                         | DEFERRED                        |                                                                        |
| B7 (unsure queue)                         | **PASS.** Unsure queue remains a top-level `unsure_queue` array on the planner envelope; the existing regex grader in `step3_unsure_queue_grading.py` is now wired into the live Scope-B grader / runner path.                                                            | PASS                            | Last verified: 2026-04-21 (pending cohort)                             |
| B8 (footer pointers)                      | **DEFERRED.** `prep_pointer_proposal` is in the strict schema; mechanical apply is not yet a tool call.                                                                                                                                                                   | DEFERRED                        |                                                                        |
| B9 (findings)                             | **PASS.** Findings are now asserted by a case-insensitive substring gate over the planner findings surface (`notes_for_gm`, envelope `message`, optional `findings`) inside the live Scope-B grader / runner path.                                                       | PASS                            | Last verified: 2026-04-21 (pending cohort)                             |
| **Scope-B mechanical contract (above)**   | **PASS (live)**                                                                                                                                                                                                                                                           | 2026-04-19 cohort               | 5/5 runs pass; signature stable across cohort.                         |


**Cohort-level metrics (from last 5x):**


| Metric                                   | Value                                                                         |
| ---------------------------------------- | ----------------------------------------------------------------------------- |
| `gates_pass_rate`                        | 5/5                                                                           |
| `tool_trace_gates_pass_rate`             | 5/5                                                                           |
| `payload_gates_pass_rate`                | 5/5                                                                           |
| `distinct_tool_trace_signatures`         | 1 (`get_recap_context, read×4, assemble_recap_draft, write_corpus_file × 2`)  |
| `write_corpus_file` phases               | `preview→commit` × 5 (commit_required hard-gated)                             |
| `distinct recap_write payload sha256_16` | 5 (mechanical core stable; `notes_for_gm`/`npc_audit` narrative still varies) |
| `cost_usd.sum`                           | $0.32                                                                         |
| `tool_trace_rows`                        | 8 / 8 / 8                                                                     |


**Run command (sequential):**

```bash
PLANNER_REVIEW_MODE=summary uv run python -m \
  evals.session_recap_ingest_vertical_slice.step1_recap_ingest_run --n 5
```

**Run command (parallel cohort, ~5x faster):**

```bash
PYTHONUNBUFFERED=1 PLANNER_REVIEW_MODE=summary uv run python -m \
  evals.session_recap_ingest_vertical_slice.step1_recap_ingest_run \
  --n 5 --parallel 5 2>&1 | tee /tmp/recap_5x.log
```

**Detached background run:**

```bash
uv run python -m evals.session_recap_ingest_vertical_slice.step1_recap_ingest_run \
  --detach --detach-follow --n 5 --parallel 5 --detach-log /tmp/recap_5x.log
```

---

## Cross-cutting C-gates (writer safety + trace)


| Gate | Status          | Last verified | How verified                                                                                                                                                                                                                                                        |
| ---- | --------------- | ------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| C1   | PASS (live)     | 2026-04-19    | `preview_required: true` hard-gated; cohort `phase_shapes` shows `preview→commit` × 5.                                                                                                                                                                              |
| C2   | PASS (implicit) | 2026-04-19    | `corpus_writer` rejects mismatched/missing `confirm_token`; commit succeeds 5/5 in cohort with the preview's token.                                                                                                                                                 |
| C3   | PASS            | 2026-04-18    | `tests/test_corpus_writer.py::test_token_invalidates_when_content_changes_between_phases` and related two-phase tests.                                                                                                                                              |
| C4   | PARTIAL         | 2026-04-19    | `corpus_writer` allowlist covers writes; recap-write read guard (`planner_skill_dispatch_guards.py`) covers reads. **Not asserted as a Scope-B gate**; trust comes from the unit tests + dispatch guard, not from a tool-trace forbidden-path filter at grade time. |
| C5   | OPEN            | —             | Allowlist-rejection finding-surfacing not asserted by Scope-B grader.                                                                                                                                                                                               |
| C6   | OPEN            | —             | Pre vs post fingerprint parity assertion not wired (cohort sidecar records post-state `corpus_fingerprint` per run; comparison absent).                                                                                                                             |
| C7   | OPEN            | —             | Pre vs post tmpdir diff not implemented.                                                                                                                                                                                                                            |


**Batch command (C3 + writer allowlist baseline):**

```bash
uv run pytest tests/test_corpus_writer.py tests/test_planner_write_dispatch.py -q
```

---

## Implementation surface (added since the original §11 hand-off)


| Module                                                                 | Purpose                                                                                                                       | Gate(s) it serves                                                    |
| ---------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------- |
| `src/agent/recap_context.py`                                           | `RecapContext` dataclass + `resolve_recap_context` (snapshot-friendly: `frozen=True`).                                        | Scope-B mechanical contract; consumed by guard + grader.             |
| `src/agent/planner_skill_dispatch_guards.py`                           | Fail-closed wrappers around `dispatch_tool` for `recap-write`. Rejects pinned `get_recap_context` and out-of-allowlist reads. | Scope-B `tool_trace_gates`.                                          |
| `src/agent/planner_skill_output_schema.py`                             | Per-skill `text.format` registry; recap-write turns get the `planner_turn_output_recap_write` strict schema.                  | Scope-B `payload_gates`.                                             |
| `src/agent/recap_write_output_schema.py`                               | `recap_write_v1` JSON Schema + Python validator.                                                                              | Scope-B `payload_gates`.                                             |
| `src/agent/recap_ingest_helpers.py`                                    | Pure mechanical helpers (split, dedup, frontmatter, `assemble_recap`).                                                        | Scope-A. Wrapped by `assemble_recap_draft` planner tool for Scope-B. |
| `evals/session_recap_ingest_vertical_slice/scope_b_grader.py`          | `collect_scope_b_recap_ingest_violations` (hard) + `collect_scope_b_recap_ingest_report_extras` (soft).                       | Scope-B contract above.                                              |
| `evals/session_recap_ingest_vertical_slice/recap_ingest_run_report.py` | Per-run `.md` + `.json` artifacts; cohort `recap_ingest_summary--*.{md,json}`.                                                | All gate reporting.                                                  |
| `evals/session_recap_ingest_vertical_slice/step1_recap_ingest_run.py`  | Runner. Sequential / `--parallel K` / `--detach[--detach-follow]`; default verbosity `-vv`.                                   | All Scope-B execution.                                               |


---

## Summary counts


| Bucket                             | PASS                  | PARTIAL    | OPEN | DEFERRED                   |
| ---------------------------------- | --------------------- | ---------- | ---- | -------------------------- |
| Scope-A                            | 8                     | 0          | 0    | 0                          |
| Scope-B (mechanical contract)      | 1 (live)              | 0          | 0    | —                          |
| Scope-B (original §J item-by-item) | 1 (live, B1 indirect) | 2 (B7, B9) | 0    | 5 (B2, B3, B4, B5, B6, B8) |
| C-gates                            | 3                     | 1          | 3    | 0                          |


**Definition of "full benchmark pass" (current):** all of A1–A8 + Scope-B mechanical contract + C1, C2, C3 are true. The original §J item-by-item view tracks the path to a stricter end-state; deferrals are intentional and motivated in [BACKLOG-session-recap-benchmarking.md](BACKLOG-session-recap-benchmarking.md).

---

## Related paths

- Helpers: `[src/agent/recap_ingest_helpers.py](../../src/agent/recap_ingest_helpers.py)`
- Eval slice: `[evals/session_recap_ingest_vertical_slice/README.md](../../evals/session_recap_ingest_vertical_slice/README.md)`
- Last cohort artifact: `evals/session_recap_ingest_vertical_slice/artifacts/runs/2026-04-19/recap_ingest_summary--gpt-5.4-mini--N5--20260419T214553Z.md`

