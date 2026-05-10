# BACKLOG — Session-recap writer benchmarking

**Status:** living backlog. Mechanical Scope-B contract is green (5/5 cohort, 2026-04-19). This file tracks the prioritized follow-ups from the April 2026 Staff Designer review **plus** the original deferred §J item-by-item gates and the original Option-A/B/C/D framing.
**Spec:** [EXPERIMENT-Session-Recap-Ingest-Benchmark.md](EXPERIMENT-Session-Recap-Ingest-Benchmark.md) (§15 = as-built architecture).
**Live ledger:** [STATUS-Session-Recap-Ingest-Benchmark.md](STATUS-Session-Recap-Ingest-Benchmark.md).
**Skill under test:** `.cursor/skills/recap-write/SKILL.md`.

---

## §1 Tier-1 — correctness drift risk (do these first)

### 1.0 `commit_required` gate counts call attempts, not commit success (Tier-1 — `gates_passed: true` can lie)

Discovered by 2026-04-20 smoke test (single run, `gpt-5.4-mini` alias, `recap_ingest--…--PASS--2turn--20260420T014526Z.json`). The run was graded `gates_passed: true` / `tool_trace_gates_passed: true`, but the model's own `notes_for_gm` says: *"Stale token on commit; no write completed."* No file landed in the corpus.

**Mechanism.** `_check_write_phases` classifies each `write_corpus_file` row by its `dry_run` argument (preview vs. commit) and counts the second `dry_run=false` row as the commit toward `commit_required`. It never inspects the call's response. So a model can:

1. Preview successfully (server returns `confirm_token`).
2. Regenerate the recap body (or any other byte that participates in the token hash) before commit — token now stale.
3. Call `write_corpus_file(dry_run=false, confirm_token=…)` → server rejects with a stale-token error.
4. Self-report failure in `notes_for_gm`.
5. Pass gates.

This makes `gates_passed: true` an unreliable signal for "the recap reached the corpus." Same severity class as §1.1 / §1.4: any cohort pass-rate aggregated under this hole over-reports actual success.

**Why it surfaced now (and not in earlier cohorts):** the M1 helper (`build_recap_write_payload`) gives the model a stable mechanical payload, which makes its **prose** (the parts that aren't mechanical) the only remaining variance source between preview and commit. Adopting M1 has, paradoxically, made it slightly more likely the model will recompute the body between turns and trip the stale-token path. The smoke test run had `mechanical_fields_match: true` *and* a failed commit — that combination is exactly the pattern this hole hides.

**Fix sketch:**
1. **Capture the response signal.** `tool_trace[i]` already records `output_excerpt` (first 800 chars of the dispatcher response). For `write_corpus_file`, the response is a JSON envelope with a success/error marker — parse it during grading.
2. **New helper** in `scope_b_grader.py`: `_write_corpus_file_committed(row) -> bool` that returns `True` iff the row's `dry_run` is `False` **and** the response indicates success (no error key, status ok, file actually written — pick the leanest signal in the dispatcher's output).
3. **Wire into `_check_write_phases`:** when `commit_required=True`, count *successful* commits, not commit *attempts*. A failed commit becomes a hard violation (`scope_b_tool`), not a silent pass.
4. **Soft signal in extras:** `commit_succeeded: bool | None` and `commit_error_excerpt: str | None` so cohort summaries can surface "N runs attempted commit, M succeeded, K failed (stale token / other)."
5. **Test:** synthesize a tool_trace with a `dry_run=false` row whose `output_excerpt` carries a stale-token error; assert grader fails with `commit_required=True`, passes the soft observation when `commit_required=False`.

**Must land before** any cohort that draws conclusions from `gates_pass_rate`. The M1 soft signals (`mechanical_fields_match`, `build_recap_write_payload_called`) are unaffected by this hole and can still be measured in the meantime — they're independent of commit success.

**Related:** if `output_excerpt` is too short to reliably carry the dispatcher response (some response shapes may exceed 800 chars), bump the cap *for `write_corpus_file` rows specifically* in `src/agent/planner.py:_dispatch_loop`; it's a one-tool special case, not a global cost.

### 1.1 Unify preview/commit knob resolution between grader and report extras — **done**

Implemented as `_resolve_write_phase_knobs(scenario)` in `evals/session_recap_ingest_vertical_slice/scope_b_grader.py`, shared by `collect_scope_b_recap_ingest_violations` and `collect_scope_b_recap_ingest_report_extras`. Test: `test_report_extras_matches_violation_knobs_commit_only` in `tests/test_scope_b_grader.py`.

### 1.4 Plumb `RecapContext` snapshot through `make_tool_dispatcher` (high — temporal-coupling regression in M1)

`build_recap_write_payload`'s dispatch branch (`src/agent/planner.py` ~lines 806–850) calls `resolve_recap_context(corpus_path, campaign_id=cid, target_session=ts_int)` *fresh*, then builds the payload from that fresh context. The dispatch **guard** (`planner_skill_dispatch_guards._wrap_recap_write`) accepts `precomputed_recap_context`, but the dispatcher itself does not, so the new tool re-derives `prep_doc_path` / `session_recaps_dir` / `recent_recaps` from the live corpus on every call. If the model invokes the tool after `write_corpus_file` commits the recap (a defensible workflow — recompute payload before final emission), the fresh resolve sees `Session 20 - Recap.md` already on disk and may either raise `RecapContextError` or shift derived fields. Meanwhile the grader (`collect_scope_b_recap_ingest_violations`) asserts `bargs.target_session == ctx.target_session` against the **snapshot** — so any drift becomes a graded violation. Same failure class we just removed from the read guard.

`assemble_recap_draft`'s dispatch branch has the same shape (re-resolves via `_assemble_recap` directly; `target_session` is pinned by the model arg today, so the bug is masked but latent).

**Fix:**
1. Add `recap_context_snapshot: RecapContext | None = None` kwarg to `make_tool_dispatcher`.
2. In the `build_recap_write_payload` branch, prefer the snapshot; only re-resolve if no snapshot was supplied. Same change for `assemble_recap_draft` if/when it consumes context fields beyond what the model passes.
3. In the live recap-ingest runner, pass the same snapshot used by the dispatch guard so guard, dispatcher, and grader agree on context.
4. **Must land before** flipping `require_build_recap_write_payload: true` in `gold/scope_b_session_20.json` (otherwise the gate fires on the latent regression).

**Test:** parametrized scenario where the model calls `build_recap_write_payload` *after* a successful `write_corpus_file` commit; assert grader passes and tool returns snapshot-derived fields, not live-resolved ones.

### 1.5 M1 enforcement gap — grader doesn't compare tool output to final payload — **(b) shipped**

Plan framed M1 as "reduce payload variance in mechanical fields." Originally `collect_scope_b_recap_ingest_violations` only checked the **call** (presence + args), never the **adoption** (does the model's `recap_write` actually equal what the helper would return?).

**Option (b) — soft signal — landed:**

- New helpers in `evals/session_recap_ingest_vertical_slice/scope_b_grader.py`:
  - `_compute_expected_mechanical_payload(scenario, ctx, corpus_path)` re-runs `assemble_recap` + `build_recap_write_payload_from_ingest` against the snapshot to compute what the tool *would* return.
  - `_compare_mechanical_fields(expected, actual)` projects `recap_preview` to `path` + `mode` only (drops the model-authored `confirm_token`), then equality-compares `recap_preview` / `duplicate_paragraphs` / `prep_pointer_proposal`.
- `collect_scope_b_recap_ingest_report_extras` now accepts `corpus_path` + `recap_context_snapshot` (both optional for back-compat) and emits:
  - `build_recap_write_payload_called: bool`
  - `mechanical_fields_match: True | False | None` (`None` = not applicable: missing snapshot/corpus_path/raw notes, or unparseable `recap_write`)
  - `mechanical_fields_diff: {field: {expected, actual}}` (only when `mechanical_fields_match is False`)
- `step1_recap_ingest_run.py` threads the pre-turn snapshot from `run_session_recap_ingest_turn(return_snapshot=True)` to `_emit_run_report` and `capture_and_write_recap_ingest_report`, so the comparison sees the same view the dispatch guard saw (closes the §1.4 latent bug for the report path; the dispatcher branch is still §1.4 work).
- Cohort summary in `recap_ingest_run_report.py` aggregates:
  - `build_recap_write_payload_called_rate`
  - `match_rate_when_called` / `match_rate_when_not_called` / `match_rate_overall`
  - `applicable_runs` / `not_applicable_runs`
- Tests: 5 new cases in `tests/test_scope_b_grader.py` (match / mismatch + diff / no-corpus → None / unparseable → None / raw-notes-missing → None / called-flag presence).

**Why soft, not hard:** lets us collect adoption + variance data over real cohorts before deciding whether (a) byte-equality enforcement is justified or whether the soft signal alone keeps drift visible.

**Open follow-up — option (a) decision:** after the next `--n 5 --parallel 5` cohort, look at `match_rate_when_called`. If `1.0` consistently, soft signal is sufficient. If `< 1.0`, that's evidence the model edits mechanical fields after pulling them from the tool, and (a) — promote to a hard violation when `require_build_recap_write_payload=true` — is the next step.

**Status of M1 strategic move:** downgraded to "landed (presence + soft-adoption signal); hard enforcement deferred to cohort data."

### 1.2 Refresh stale docstrings in `recap_write_output_schema.py`

Module docstring + `recap_write_output_json_schema` docstring still describe the deprecated path ("payload embedded in `message`, no `text.format` enforcement"). The strict per-skill schema replaced that. New maintainers will follow the wrong path.

**Fix:** rewrite both docstrings; point at `planner_skill_output_schema.planner_turn_with_recap_write_text_format` as the live integration; preserve the loose-extract helpers as forensic-replay tools.

### 1.3 Compute Scope-B extras once per run and plumb through

Today `collect_scope_b_recap_ingest_report_extras` is invoked in three places under three different exception-handling regimes (runner stderr log; per-run sidecar; cohort summary derives from the sidecar's stored copy). Risk: the three views of the same run can disagree.

**Fix:** compute once in `run_session_recap_ingest_turn`, attach to `PlannerStep1Run` (or alongside it), pass into `_emit_run_report` and `capture_and_write_recap_ingest_report` explicitly.
**Cost:** ~20 lines, removes duplication.

---

## §2 Tier-2 — coupling / API quality

### 2.1 Resolve `c:` refs in the recap-write read guard — **done**

`_wrap_recap_write` now builds `ref_index` via `build_corpus_path_ref_index` and resolves `path` with `_resolve_planner_read_argument` before allowlist membership; unknown `c:` refs return the same error shape as the base dispatcher. Tests: `test_recap_write_guard_resolves_c_ref_before_allowlist`, `test_recap_write_guard_blocks_unknown_c_ref`.

### 2.2 Promote `_sanitize_planner_step1_filename_segment` out of the lysandra slice

`recap_ingest_run_report.py` imports a private helper from `evals.lysandra_vertical_slice.step1_planner_trace`. Two slices reach into each other's privates.

**Fix:** create `evals/_shared/filename_sanitize.py`; both slices import from there.

### 2.3 Single-touch skill plugin interface (deferred until skill #2)

Adding a second guarded/strict-schema skill needs touches in: `SKILL_DISPATCH_GUARDS` set + `wrap_dispatch_for_skill` if-branch + `_SKILL_TEXT_FORMAT_REGISTRY` dict + possibly a new `*_output_schema` module + possibly a new grader.

**Fix (when triggered):** define `SkillProfile = (id, dispatch_wrapper_factory, text_format_factory, validator)`; collapse the three registries into one keyed by `id`. Defer until a second skill actually needs it; no need to abstract on N=1.

### 2.4 Thread skill kwargs through `run_planning_turn` (or deprecate it)

`run_planning_turn` calls `run_planning_turn_detailed` without `active_skill_id`. Production callers that route through this path get the universal envelope and unguarded dispatch even for `recap-write`.

**Fix options:**
- **(a)** Add the kwargs and forward.
- **(b)** Mark `run_planning_turn` deprecated; migrate live callers to `_detailed`.

### 2.5 Consolidate `_dry_run_arg` helpers

Defined in both `scope_b_grader.py` (lines 115–122) and `step1_recap_ingest_run.py` (lines 450–456). Drift risk.

**Fix:** keep one in `scope_b_grader.py` (it's the semantic owner — "what does the planner see as a preview?"), import from the runner.

### 2.6 Single source for default `ingest_raw_notes_relpath`

Hardcoded in two places (grader fallback + runner fallback). Fine for one gold file; brittle if multiple scenarios diverge silently.

**Fix:** single module-level constant in `scope_b_grader.py`; runner imports.

### 2.7 Lift `_resolve_planner_read_argument` + `build_corpus_path_ref_index` out of `planner.py`

`_wrap_recap_write` lazy-imports `_resolve_planner_read_argument` (a single-underscore "private" helper) from `src.agent.planner` to avoid a circular import. Two issues: (a) cross-module reach into a `_`-prefixed symbol means any planner-side rename silently breaks the guard at runtime with no static signal; (b) the lazy-import comment papers over a layering bug — the dispatch guard depends on a planner internal that the planner depends on the guard to invoke.

**Fix:** create `src/agent/corpus_paths.py`; move both `build_corpus_path_ref_index` and `_resolve_planner_read_argument` (rename to `resolve_planner_read_argument` while we're at it). Both `planner.py` and `planner_skill_dispatch_guards.py` import at module top-level. Drop the lazy-import block. Pure mechanical refactor — no behavior change.

---

## §3 Tier-3 — observability / ergonomics

### 3.1 Soft-fail individual workers in parallel cohorts

Today `as_completed` re-raises (`step1_recap_ingest_run.py:953-960`). One slow API timeout aborts the whole cohort and discards the in-flight runs.

**Fix:** catch worker exceptions, record a synthetic FAIL `RecapIngestRunSummary` row with the exception repr in `extras`, continue. Cohort summary surfaces "errored" count alongside pass/fail.

### 3.2 Expose `--seed` for reproducible payloads

OpenAI Responses API accepts a `seed` parameter; combined with low temperature it reduces payload variance when forensics need exact reproduction. Today the 5-distinct-hash result is uncontrolled.

**Fix:** `--seed N` flag → forwarded to `client.responses.create(seed=N)`. Default unset (today's behavior).

### 3.3 `--max-cost-usd` ceiling

Cohort cost is reported, never gated. A 50-run cohort with a fat scenario could surprise.

**Fix:** track cumulative `scenario_estimated_cost_usd` across runs in the cohort loop; abort with explanatory message when the ceiling is exceeded; emit a partial cohort summary.

### 3.4 Rename / comment `first_turn_final_text = ""` reassignment

Lines 285–286 in `run_session_recap_ingest_turn` clear the variable when no `followup_turn` exists. Confusing without context. Either (a) add a one-line comment, or (b) rename to make the intent obvious.

### 3.5 Replace `sys.path.insert` with `__main__`-guarded bootstrap

Runner inserts repo root at module-import time. Ergonomic for `python -m`; will trip future packaging.

**Fix:** move under `if __name__ == "__main__":` or rely on the package being installed in dev mode.

### 3.6 Add CI wiring (Phase 4 of the EXPERIMENT plan)

Phase 4 of the original spec was never landed.

**Cheap (every PR, no API key, < 1s):**
- `pytest tests/test_recap_ingest_helpers.py tests/test_session_20_scope_a_gold.py tests/test_scope_b_grader.py tests/test_recap_ingest_run_report.py tests/test_recap_ingest_detach_argv.py tests/test_planner_skill_dispatch_guards.py tests/test_planner_skill_output_schema.py tests/test_planner_turn_output_schema.py tests/test_corpus_writer.py`

**Manual / nightly (gated by `OPENAI_API_KEY`):**
- `step1_recap_ingest_run.py --n 5 --parallel 5` cohort; succeed if cohort `gates_pass_rate == 5/5`. Budget: ~$0.30/run.

### 3.7 Cost-ceiling alarm on per-run sidecar

Independent of §3.3 (which gates the cohort): per-run, emit a soft observation when `scenario_estimated_cost_usd` exceeds an expected envelope (e.g. 1.5× cohort mean). Useful for catching prompt-bloat regressions.

### 3.8 Document the snapshot invariant; rename `ref_index` to make session-scope visible — **(b) chosen**

`ref_index = build_corpus_path_ref_index(corpus_path.resolve())` runs *once* at guard construction and is captured in the closure. The recap-write allowlist is also frozen on the snapshot today, so the user-visible bug ("ref index doesn't see new file written by turn 1") is masked — but the cohabitation of "frozen allowlist" + "frozen ref index" + "frozen recap context" is implicit and easy to mis-read as a bug.

**Discussion (Apr 2026):** the right framing is that **session = scenario** in this benchmark, and the **snapshot** is the index built once at session start (recap context + ref index + allowlist). All three are co-frozen for the duration of the session. The runner already does this — it's not a missing concept, it's an underdocumented one. Option (b) is the right answer: don't add runtime invalidation logic (option (a)) for a problem that doesn't exist within the lifecycle we ship; instead, name and document the invariant so the next reader sees it.

**Fix:**
1. Rename the local in `_wrap_recap_write` from `ref_index` to `session_ref_index_snapshot` (or similar) so the session-scope is visible at the point of capture.
2. Document on `_wrap_recap_write` that `ref_index`, `allowlist`, and `precomputed_recap_context` are intentionally co-snapshotted at session start; the snapshot is the **only** thing the guard reads, and that is by design.
3. Update the "unknown corpus file ref" error to say "ref index is frozen at session start; if you wrote a new file this session, refer to it by its `.md` path, not its `c:` token" so failures point at the snapshot lifecycle rather than a phantom bug.

**Out of scope (deferred): option (a) — `mtime`-based lazy rebuild.** Was on the table for multi-turn scenarios where the corpus mutates *during* a session. We don't have such scenarios today (Turn 2 is followup-text only, no further corpus reads via `c:` refs against newly-written files), and adding stat-based invalidation would (i) hide the snapshot invariant, (ii) introduce a TOCTOU window between rebuild and use, and (iii) cost a `stat` per call. If we ever need it, it's a small change — but it should be a deliberate "we now have a use case" decision, not a "just in case."

> **What "invalidate when `corpus_path` mtime advances" would have meant:** the guard would call `Path(corpus_path).stat().st_mtime_ns` on each `read_corpus_file` invocation; if the timestamp is newer than the one captured at guard construction, throw the cached `ref_index` away and rebuild from disk. `mtime` ("modification time") is a filesystem-maintained timestamp updated whenever the directory's contents change. The cost is one `stat` per tool call (cheap); the *real* cost is conceptual — it makes the guard a stateful cache instead of a session-scoped read of an immutable snapshot, and that change deserves its own design pass when (if) we have a multi-turn scenario that needs it.

### 3.9 `mode: "create"` is unconditional in `build_recap_write_payload_from_ingest` — **agreed; needs fix**

`canonical_recap_path` always returns the new recap's path; `build_recap_write_payload_from_ingest` always sets `recap_preview.mode = "create"`. For replay/idempotency (re-running the same scenario after a successful commit) or a future gold scenario where the recap already exists and we want to overwrite, the mechanical helper returns `mode: "create"` and `write_corpus_file` rejects the dry_run because the file already exists.

> **Idempotency** = a property where running the same operation twice has the same effect as running it once. Concrete example: pressing an elevator button twice has the same effect as pressing it once (it's idempotent); withdrawing $20 from an ATM twice has a different effect than withdrawing once (not idempotent). Here: re-running `build_recap_write_payload` after a successful commit *should* return a payload that — if applied — produces the same end state as the first run. Today the second run returns `mode: "create"` against a file that already exists, so the second `write_corpus_file` rejects it. Same input, different outcome → not idempotent.

**Why this matters in practice:** every cohort run today starts from a clean per-run corpus rebuild (so the bug is masked), but the moment we want to (a) replay a single failed run for diagnostic purposes without rebuilding the corpus, (b) test the "model recovers from a failed commit and retries" path, or (c) write a gold scenario where the recap already exists, the helper produces a payload that's guaranteed to fail downstream. The fix is cheap; do it before either of those use cases lands.

**Fix:** in `build_recap_write_payload_from_ingest`, check whether the resolved recap path exists on disk; pick `mode = "create"` if absent, `"update"` if present. Add a unit test for both branches in `tests/test_recap_write_mechanical_payload.py`.

### 3.10 Schema relaxation comment on `confirm_token: minLength: 0`

Setting `minLength: 0` was necessary so `build_recap_write_payload`'s placeholder validates. The cost: a model that prints the unmodified empty placeholder (or skips the commit phase entirely) now produces a schema-valid payload. The 2PC gate (`commit_required`) catches the missing commit, and `write_corpus_file` itself rejects a wrong/empty token, so this isn't a safety bug — but the schema no longer carries a static "this field was filled in" signal.

**Fix:** add an inline comment on `_RECAP_PREVIEW_SCHEMA.confirm_token` in `src/agent/recap_write_output_schema.py` explaining (a) the deliberate relaxation for the placeholder pattern, (b) the gates that compensate (`commit_required` in the grader, token-equality in `write_corpus_file`), and (c) the note that if `commit_required` is ever degraded to soft, this schema constraint must be re-tightened or the missing-commit case will go unsignalled.

### 3.11 Deboilerplate `prep_pointer_proposal` copy or version it

`prep_pointer_proposal_from_context` ships hard-coded English ("`> **Prep:** See ...`", "`> **Played:** See ...`") through tool output into the model's final JSON. Today no grader compares those strings. The risk: a future grader or gold scenario string-compares this field and the helper becomes an undocumented coupling point between schema content and prose.

**Fix options:**
- **(a):** strip the copy — return `prep_path` + `recap_path` only and let the model phrase the lines in `notes_for_gm`.
- **(b):** accept that this is part of the contract; bump `RECAP_WRITE_SCHEMA_VERSION` whenever the copy changes; document the strings in the schema.

(a) is cleaner ("mechanical helpers don't ship prose"); (b) is OK if we want the model relieved of the phrasing burden.

### 3.12 Backfill `_resolve_write_phase_knobs` parametrized tests

The function has five distinct fallback paths (cfg-preview-only, cfg-commit-only, expected-trace-fallback, legacy `two_phase_commit_required`, both-None default → false/false). The new test (`test_report_extras_matches_violation_knobs_commit_only`) covers exactly one. The cohort-summary-vs-grader bug we set out to prevent in §1.1 could still recur on any of the four untested fallback edges.

**Fix:** parametrized test enumerating all five paths, asserting `(preview_required, commit_required)` matches expected for each.

### 3.13 Process: don't mark BACKLOG/STATUS green while `pytest tests/` is red

The April-19 implementation pass declared three plan items "completed" and updated BACKLOG/STATUS to reflect that. A concurrent `uv run pytest tests/` showed 6 failures (`test_lysandra_vertical_slice_*`, `test_recap_ingest_helpers::test_assemble_body_matches_gold_body`, `test_session_20_scope_a_gold::test_session_20_recap_byte_equal_to_gold`). The diagnosis was "corpus / gold drift, not introduced by these edits" — likely correct, but the next operator opens a red suite with no breadcrumb explaining which red is theirs.

**Fix (process):** before flipping any BACKLOG/STATUS row to green, either (a) confirm the failures predate the edit (`git stash && pytest`) and link the predecessor commit in the BACKLOG entry, or (b) open a new BACKLOG item titled "Reconcile gold drift in lysandra slice + scope-a byte-equality" and reference it from the green row. Right now this would be a new §1.6 item.

### 3.14 Reconcile gold drift in lysandra slice + scope-a byte-equality

Six tests are red as of 2026-04-19 and were not introduced by §1.1 / §2.1 / §M1:

- `tests/test_lysandra_vertical_slice_run_deterministic.py::test_run_vertical_slice_deterministic_wires_step234_like_direct_call`
- `tests/test_lysandra_vertical_slice_run_deterministic.py::test_run_vertical_slice_violations_concat_step_outputs`
- `tests/test_lysandra_vertical_slice_step0.py::test_run_step0_gates_passes_with_skip_flag`
- `tests/test_lysandra_vertical_slice_step4.py::test_step2_through_step4_aggregate`
- `tests/test_recap_ingest_helpers.py::test_assemble_body_matches_gold_body`
- `tests/test_session_20_scope_a_gold.py::test_session_20_recap_byte_equal_to_gold`

**Fix:** triage each failure. The two `recap`-shaped ones suggest the on-disk recap helpers diverged from the gold body bytes; either (a) the helpers regressed and need fixing, or (b) the gold body needs refreshing to match a deliberate behavior change. The four lysandra-slice failures suggest an upstream corpus-snapshot drift; check `step0_pre_state.py` outputs against the lysandra fixtures.

---

## Strategic moves (review-level recommendations)

### M1 — Mechanical `build_recap_write_payload` tool — **landed**

**Shipped:** `build_recap_write_payload` in `src/agent/planner.py` (same args as `assemble_recap_draft`), pure builders in `src/agent/recap_write_mechanical_payload.py`, `recap_preview.confirm_token` allows empty placeholder (`minLength: 0`), docs in `corpus_session_planner.py` + `.cursor/skills/recap-write/SKILL.md`. Optional Scope-B gate `scope_b_grader.require_build_recap_write_payload` in `scope_b_grader.py` (default **false**; Session 20 gold unchanged).

**Follow-up:** enable `require_build_recap_write_payload: true` in gold after a green cohort if we want a hard regression on tool usage; expect lower `notes_for_gm` / `npc_audit` hash variance only when models adopt the tool consistently.

### M2 — Second gold scenario for generalization

The benchmark is single-fixture today. Until a second `(raw_notes, gold_artifacts)` pair lands, every "deterministic" property is "deterministic for this one input." The runner is fixture-agnostic; only `gold/scope_b_session_20.json` is pinned. A second scenario with **different `target_session`**, **different `recent_recaps` shape** (e.g. K < 3 available), **no duplicates in raw notes**, etc. would catch over-fitting in the snapshotting + allowlist code paths.

**Trigger:** the GM's next real recap with raw notes preserved.
**Cost when triggered:** low (one new gold JSON, one new fixture file, no runner changes).

---

## §4 Deferred original-spec gates (from STATUS)

These were §J item-by-item gates in the original SCOPE-B-GOLD spec; the implementation pivoted to a narrower mechanical contract first. Pick these up after the Tier-1 / Tier-2 backlog clears.

| Original gate | Why deferred | Trigger to implement |
|---|---|---|
| **B2** Lysandra timeline append | Single-turn recap-write only previews + commits the recap. Live `append_timeline_row` two-phase is not exercised. | Add a third turn (or extend the followup) that calls `append_timeline_row` for the candidate emitted in `npc_audit.timeline_append_candidates`. |
| **B3, B5, B6** Setting-hub seeds (Marla / Stacey / Stuart byte-equal) | Setting-hub creation is not in scope of the recap-write skill in this benchmark. The relevant `corpus_writer` allowlist patterns exist; the skill flow doesn't drive them yet. | Either (a) extend recap-write to handle dual-hub creation, or (b) split into a separate `npc-hub-create` skill + benchmark. |
| **B4** Marla campaign-hub dossier shape | Resolves on EXPERIMENT §12.2 (byte-equal vs shape grading for newly authored prose). | Decide §12.2; author/freeze the gold; add shape grader. |
| **B8** Footer pointers | `prep_pointer_proposal` is in `recap_write_v1`; mechanical apply is not yet a tool call. | Add an `apply_prep_pointers` tool (two-phase) wired to the proposal; grade exact-text. |
| **B9** Findings (Sara, Frank, Tealeaf substrings) | `notes_for_gm` is freeform; substring grader exists in spirit but is not wired into the runner pass/fail. | Add a substring matcher over `notes_for_gm` from `gold/scope_b_session_20_findings.json`; promote to a `findings_gates_passed` flag alongside tool/payload. |
| **B7** Unsure queue | `unsure_queue` is in the strict schema; `step3_unsure_queue_grading.py` regex-grader exists but is not consumed by the runner. | Wire the regex grader into the runner; add `unsure_queue_gates_passed` flag. |

---

## §5 Original options framing (April 2026, condensed; full text below)

The pre-implementation analysis weighed four benchmark architectures. The chosen approach is **Option A** (structural / contract gates) realized through the mechanical Scope-B contract in EXPERIMENT §15.3. Options B, C, D remain on the shelf:

- **Option B (time-rewind snapshot)** — best end-to-end signal *once we have one real raw-notes/recap pair*. Triggered by M2 above.
- **Option C (compress-then-expand)** — defer; the compressor's choices silently shape what the expander can produce; benchmarks the compressor as much as the writer.
- **Option D (mini-campaign)** — high up-front cost; toy data may not surface real-notes failure modes. Defer until at least one real pair calibrates "messy enough."

---

## Appendix — Original options analysis (preserved for context)

> The text below is the original April-2026 backlog rationale, prior to implementation. Kept for the Option-B/C/D framing.

### Option A — Structural / contract gates

**Measures:** Mechanical correctness of the on-disk artifact, independent of prose quality.

**What we'd assert:**

- New recap file lives at `Session Recaps/Session NN - <slug>.md` under the chosen campaign hub.
- Frontmatter contains `title`, `document_class: play`, `canon_layer: campaign`, `campaign_id`, `session: N`, `origin_session: N`, `last_updated_session: N`, `source_class: observed_session_recap`.
- Body has a numbered TLDR section followed by long-form prose (heuristic: at least one numbered list and at least N paragraphs).
- Each appended `timeline.md` row has correct columns (Session | Beat | Recap file) and the `Recap file` cell matches the literal new filename.
- No edit landed on `*_character_dossier.md`, `character_seed.md`, or `*_statblock*.md` (allowlist already enforces server-side; gate confirms in artifact form).
- Corpus fingerprint changed exactly by the expected delta (recap file added, N timeline files mutated, nothing else).

**Cost:** Low. Pure assertions over the diff/artifact set; no LLM judge needed.

**Status (April 2026):** **Built — partially.** The mechanical Scope-B contract (EXPERIMENT §15.3) is the realization. Frontmatter / path / allowlist / two-phase is enforced. Fingerprint-delta diff is not yet wired (open as C6/C7 in STATUS).

### Option B — Time-rewind snapshot

**Measures:** End-to-end prose quality + path-discovery correctness against a known-good target.

**Shape:**

1. Take a real session N's raw notes (when we have them).
2. Snapshot the corpus *as it would have been before session N* — i.e. delete that recap file and revert the affected `timeline.md` rows.
3. Feed the snapshot + raw notes to the planner with `--allow-corpus-writes`.
4. Compare the writer's output recap to the human-authored original; compare the new timeline rows to what the human appended.

**What it catches:** Path mistakes (writing to wrong session number, wrong campaign hub), missing affected NPCs, prose drift relative to the GM's voice.

**Cost:** Medium. Needs paired raw-notes ↔ recap data, plus a snapshot/restore harness.

**Status:** the snapshot/restore harness *is built* (`step0_pre_state.py` + manifest). Only the second `(raw_notes, recap)` pair is missing to make this a real generalization signal.

### Option C — Compress-then-expand

**Measures:** Round-trip fidelity (can the writer recover a recap from a synthetic compression of itself?).

**Shape:**

1. Take an existing recap file as gold.
2. Use a separate model call to summarize it into "synthetic raw notes" (terse, GM-scratch-shaped).
3. Feed those synthetic notes to the writer.
4. Compare the writer's recap to the original gold.

**Risk:** The compressor's choices about what to omit silently shape what the expander is *capable* of producing. Benchmarks the compressor as much as the writer.

**Status:** Defer. Only worth building if Options A + B are insufficient and we still need more cases than real raw-notes pairs can provide.

### Option D — Mini-campaign

**Measures:** Same as Option B but with controlled, paired inputs we author on purpose.

**Shape:** Write a short toy campaign (~5 sessions) with explicit paired notes ↔ recap files.

**Risk:** Toy data may not surface the failure modes real session notes do.

**Status:** Probably the right end state, but premature before we have one real raw-notes/recap pair to calibrate "messy enough."

---

## Related

- Lesson 13 (deterministic-vs-judgment rationale, condensed): `Docs/Learnings/LEARNINGS-Corpus-Layout-For-LLM-Grounding.md`.
- Skill under test: `.cursor/skills/recap-write/SKILL.md`.
- Writer module: `src/agent/corpus_writer.py`.
- Existing planner-trace eval shape (template for any future skill benchmark): `evals/lysandra_vertical_slice/step1_planner_trace.py`, `evals/npc_voice_vertical_slice/npc_voice_planner_trace.py`.
