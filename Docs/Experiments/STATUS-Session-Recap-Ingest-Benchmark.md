# Session recap ingest benchmark — gate status

**Spec:** [EXPERIMENT-Session-Recap-Ingest-Benchmark.md](EXPERIMENT-Session-Recap-Ingest-Benchmark.md) (gate definitions in §5; current architecture in §15).
**Scope-B contract:** [SCOPE-B-GOLD-Session-20-Ingest.md](SCOPE-B-GOLD-Session-20-Ingest.md) §J.
**Last cohort run:** 2026-04-21, 3/3 PASS (Tier-0 refresh), `recap_ingest_summary--gpt-5.4-mini--N3--20260421T032706Z.{md,json}` — preview→commit × 3, distinct payload sha16=3, tool-trace signatures=2, `cost_usd.sum=$0.1946`. Prior baseline 5/5 PASS on 2026-04-19 still holds.

Update the **Last verified** column whenever you re-run the listed command. This file is the **living** pass/fail ledger; the experiment doc §5 remains the normative gate list.

---

## Legend


| Status          | Meaning                                                                                                                                 |
| --------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| **PASS**        | Automated test or benchmark gate green on last run; cited artifact reproduces it.                                                       |
| **PASS (live)** | Live-API benchmark gate green on the cited cohort run.                                                                                  |
| **PARTIAL**     | Some automation exists; not all sub-criteria exercised end-to-end. **Also used** for §J items that are **wired in the grader but turned off on canonical gold** (B7, B9): the contract is proven when enabled; canonical Session 20 opts out for architectural reasons (see `Backlog.md`). |
| **OPEN**        | No Scope-B / cohort automation for this check yet. When triage marks a gate as a **small follow-up**, the sketch lives in **How verified** (no separate status token). |
| **CLOSED**      | The property is **satisfied outside** the Scope-B grader surface (e.g. `corpus_writer` + `make_tool_dispatcher` + unit tests). Ledger records *why* we are not duplicating it at grade time. |
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
| B1 (recap byte-equal)                     | **Indirect:** mechanical assembly is forced via `assemble_recap_draft`; tool returns deterministic `recap_body`; `write_corpus_file` `mode=create` for the recap path. Byte-equal is not re-asserted live, but the path that produced it is now mechanically constrained. | PASS (live) — 2026-04-19 (N=5), 2026-04-21 (N=3) | Byte-equal still proven by Scope-A A8 against the same helpers.        |
| B2 (Lysandra timeline)                    | **DEFERRED.** Single-turn ingest demonstrates `npc_audit.timeline_append_candidates` discovery in `recap_write_v1`. Live append of `append_timeline_row` is not exercised by the current scenario.                                                                        | DEFERRED                        | Tracked: backlog item "two-phase append for Lysandra row in followup". |
| B3, B5, B6 (setting-hub seeds byte-equal) | **DEFERRED.** Setting-hub creation not yet in scope of recap-write skill in this benchmark; gold remains byte-equal contract on disk.                                                                                                                                     | DEFERRED                        | See backlog "expand recap-write to dual-hub create".                   |
| B4 (Marla campaign hub shape)             | **DEFERRED.** Campaign-hub dossier path requires resolving the open question in EXPERIMENT §12.2.                                                                                                                                                                         | DEFERRED                        |                                                                        |
| B7 (unsure queue)                         | **WIRED, opted out on canonical.** `step3_unsure_queue_grading.py` (now with `mode: "shape"`) is invoked from `scope_b_grader.py` and gated by `require_unsure_queue` in the scenario JSON. Canonical Session 20 has `require_unsure_queue: false` because the planner LLM emits `unsure_queue: null` on the happy path; see Backlog READYs `Recap-write planner — SKILL.md body has no injection path…` and `_UNSURE_QUEUE_ADDENDUM "prefer 0" line contradicts B7…`. | PARTIAL                         | Grader path proven when enabled; canonical gold opts out. Last enabled-state check: 2026-04-21 perturbation offline tests. |
| B8 (footer pointers)                      | **DEFERRED.** `prep_pointer_proposal` is in the strict schema; mechanical apply is not yet a tool call.                                                                                                                                                                                                                                                                                                                       | DEFERRED                        |                                                                        |
| B9 (findings)                             | **WIRED, opted out on canonical.** Case-insensitive substring gate over `notes_for_gm` / envelope `message` / optional `findings`, gated by `require_findings`. Canonical Session 20 has `require_findings: false` for the same architectural reason as B7; gates pass-when-enabled.                                                                                                                                          | PARTIAL                         | Same ledger rule as B7. Last enabled-state check: 2026-04-21 perturbation offline tests. |
| **Scope-B mechanical contract (above)**   | **PASS (live)**                                                                                                                                                                                                                                                           | PASS (live) — 2026-04-19 (N=5), 2026-04-21 (N=3) | 5/5 then 3/3 gates pass; all runs `preview→commit`. N=5 had one tool-trace signature; N=3 had two (one trial issued an extra `read_corpus_file`). |


**Cohort-level metrics (latest = N=3 on 2026-04-21; N=5 on 2026-04-19 in parens):**


| Metric                                   | Value                                                                                                                                          |
| ---------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| `gates_pass_rate`                        | 3/3 (5/5)                                                                                                                                      |
| `tool_trace_gates_pass_rate`             | 3/3 (5/5)                                                                                                                                      |
| `payload_gates_pass_rate`                | 3/3 (5/5)                                                                                                                                      |
| `distinct_tool_trace_signatures`         | 2 in N=3 (1 in N=5); both shapes are `get_recap_context, read×{4,5}, assemble_recap_draft, build_recap_write_payload, write_corpus_file × 2`   |
| `write_corpus_file` phases               | `preview→commit` × 3 (commit_required hard-gated; was × 5 in N=5)                                                                              |
| `distinct recap_write payload sha256_16` | 3 in N=3 (5 in N=5) — mechanical core stable; `notes_for_gm` / `npc_audit` narrative still varies                                              |
| `cost_usd.sum`                           | $0.1946 in N=3 ($0.32 in N=5)                                                                                                                  |
| `tool_trace_rows`                        | 9 / 9 / 10 in N=3 (8 / 8 / 8 in N=5) — one trial added one extra `read_corpus_file` (accounts for the second tool-trace signature)             |
| `mechanical_fields.match_rate_overall`   | 2/3 in N=3 — one trial's final `recap_write` deviated from strict mechanical match yet still passed gates; watch if it persists across cohorts |


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
| C4   | CLOSED          | 2026-04-21    | Write-path allowlist + dossier/seed/statblock denials enforced in `src/agent/corpus_writer.py` and `make_tool_dispatcher`; covered by `tests/test_corpus_writer.py` + `tests/test_planner_write_dispatch.py::test_dispatcher_blocks_dossier_write_even_when_writes_enabled`. A Scope-B tool-trace forbidden-path filter would only duplicate those invariants — the gold `forbidden_writes` key was removed in 2026-04-22 (it was not consumed by `scope_b_grader.py`; enforcement is dispatcher-layer, as above). |
| C5   | DEFERRED        | 2026-04-21    | Surfacing allowlist-rejections as findings would need a machine-readable §H attempt list paired to the findings surface; current grader supports only OR-substring matching and committed `gold/scope_b_session_20.json` keeps `require_findings: false`. Revisit when B7/B9 architectural READYs land (then `require_findings` can flip on for canonical too).                                                                                                       |
| C6   | OPEN            | —            | **WIRE (small):** post-commit fingerprint parity. **Sidecar `corpus_fingerprint` today is the pre-turn instruction-cache fingerprint, not a post-commit recompute** (`step1_recap_ingest_run.py:228-232,345-350` writes the same `fp` from `load_or_build_planner_instructions` into the sidecar). True C6: either (a) parse `new_corpus_fingerprint` from the final successful `write_corpus_file` (`src/agent/corpus_writer.py:249-265`), or (b) call `recompute_corpus_fingerprint(corpus_dir)` after the run and assert equality. |
| C7   | OPEN            | —            | **WIRE (small):** pre/post tmpdir manifest diff. Capture a manifest of `corpus_dir` after harness staging write (`step1_recap_ingest_run.py:197-203`) and again after the planner returns; diff post-minus-pre against the union of successful write/append paths from `tool_trace`. Catches stray creates without a full `copytree` snapshot. |


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


| Bucket                             | PASS                  | PARTIAL    | OPEN | CLOSED | DEFERRED |
| ---------------------------------- | --------------------- | ---------- | ---- | ------ | -------- |
| Scope-A                            | 8                     | 0          | 0    | 0      | 0        |
| Scope-B (mechanical contract)      | 1 (live)              | 0          | 0    | 0      | —        |
| Scope-B (original §J item-by-item) | 1 (live, B1 indirect) | 2 (B7, B9) | 0    | 0      | 6 (B2, B3, B5, B6, B4, B8 — **six** deferred gate-checks; the §J table **merges** B3+B5+B6 on **one** markdown row, so the row count is 4) |
| C-gates                            | 3 (C1, C2, C3)        | 0          | 2 (C6, C7) | 1 (C4) | 1 (C5) |


**Definition of "full benchmark pass" (current):** all of A1–A8 + Scope-B mechanical contract + C1, C2, C3 are true. The original §J item-by-item view tracks the path to a stricter end-state; deferrals are intentional and motivated in [BACKLOG-session-recap-benchmarking.md](BACKLOG-session-recap-benchmarking.md).

---

## Related paths

- Helpers: `[src/agent/recap_ingest_helpers.py](../../src/agent/recap_ingest_helpers.py)`
- Eval slice: `[evals/session_recap_ingest_vertical_slice/README.md](../../evals/session_recap_ingest_vertical_slice/README.md)`
- Latest cohort artifact (Tier-0 refresh): `evals/session_recap_ingest_vertical_slice/artifacts/runs/2026-04-21/recap_ingest_summary--gpt-5.4-mini--N3--20260421T032706Z.md`
- Prior baseline cohort (N=5): `evals/session_recap_ingest_vertical_slice/artifacts/runs/2026-04-19/recap_ingest_summary--gpt-5.4-mini--N5--20260419T214553Z.md`

