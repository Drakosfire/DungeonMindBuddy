# EXPERIMENT — Session recap autonomous timeline pass (Stage 2 v1)

**Parent v0 (operator-instructed):** [EXPERIMENT-Session-Recap-Timeline-Append-Benchmark.md](EXPERIMENT-Session-Recap-Timeline-Append-Benchmark.md) — single-NPC append on Lysandra. v0 stays as-is and is the tool-surface baseline; this slice grades **autonomous discovery + selectivity**.
**Slice root:** `evals/session_recap_timeline_pass_vertical_slice/`

This benchmark proves **autonomous downstream enrichment** after recap ingest: given a committed recap and a pre-loaded list of existing C2 timeline files, the planner decides which NPCs need a Session-N row, which to skip, and which prominent NPCs lack a hub entirely.

---

## Design choices (normative)

### A. Grading mode — **Count + flat-anchor-words** on rows on disk (Iteration 6)

Replaces the v0-imported hybrid regex rubric. For each entry under
`grading.expected_appends`:

- **Count gate:** the target timeline file must contain at least
  `expected_count` table rows whose first cell is `**N**` after the run.
- **Anchor-word gate:** every word in `anchor_words` (case-insensitive
  substring) must appear at least once across the **union of beat-cell text**
  in those new rows. The list is intentionally short (3–6 distinctive terms
  per character) — the qualitative-review pass (the second leg of the gate)
  is what judges prose quality.
- **Strict cells 1 and 3** are no longer enforced row-by-row; they are
  enforced by the writer (`append_timeline_row` validators) so a
  successful commit already implies a well-formed row.

Why the change: the v0 hybrid rubric was a cheap-and-fast inheritance from a
single-NPC operator-instructed slice. In Stage 2 it conflated two qualities
(prose anchor presence and per-row schema) and produced unstable verdicts on
otherwise plausible model output. Counting rows on disk plus a small,
auditable anchor-word list is a structural fit for autonomous discovery: the
rows-on-disk side is mechanical and cheap; the anchor-word list is the
machine surface for what a GM would care about; richer prose judgement lives
in the human review pass.

### B. User message — **verbatim** (gold JSON), pre-loads the timeline list

Stored in `evals/session_recap_timeline_pass_vertical_slice/gold/timeline_pass_session20.json` under `input.user_message`. It names the recap path, **pre-loads the eight existing C2 timeline file paths and their slugs** (option a — see §G), instructs a one-phase `append_timeline_row` ("call once per character; the call commits"), forbids `write_corpus_file` and recap-assembly tools, and mandates the universal `planner_turn_output` envelope (no `recap_write` field, `unsure_queue: []`). Hub-proposal language has been removed from the user message in Iteration 6.

### C. Skill choice — **Option (b): skill-less turn**

Same as v0: `active_skill_id=None` → universal JSON schema. Runner appends an
**eval-only suffix** after `load_or_build_planner_instructions` (does **not** edit `corpus_session_planner.py`) explaining the timeline-pass contract, the PC-path `timeline_path` requirement, the skip-without-append rule, and the one-phase commit semantics. The runner threads `autonomous_writes=True` into both the dispatcher and the writer-tool schema generator (see "Autonomous writer mode" below).

### D. Cohort scope — **Session 20 (C2)**

The first cohort uses Session 20 because all eight existing C2 timelines either need a row or have a clean SKIP rationale. (Two PC hubs — Karsemine and Ephanna — were promoted to first-class APPEND targets in Iteration 4 once their hub corpus was added; they were previously hub-proposal candidates.) Hub-proposal evaluation is **out of scope for this slice** until timelines are reliably passing.

### E. Autonomous writer mode

This slice uses the dispatcher's one-phase **autonomous-writes** loopback for `append_timeline_row` (see `make_tool_dispatcher(..., autonomous_writes=True)` in `src/agent/planner.py` and the rule `corpus-two-phase-commit.mdc`). The model sees a single tool call: `append_timeline_row(npc_slug=..., session=..., beat=..., recap_filename=..., timeline_path?=...)`. The dispatcher internally runs `dry_run=True` to obtain the `confirm_token`, then `dry_run=False` with that token, returning only the commit-phase response. The writer's safety properties — allowlist, payload validators, `file_state_token` CAS — are unchanged.

**Why structurally and not by prompt:** five iterations of dispatcher patches and prompt-tuning failed to lift TP1 because the autonomous benchmark was being driven through a writer designed for human-in-the-loop ops (preview → operator approves → commit). The two-phase surface produced a stable failure mode where the model wrote the diff to its `message` field as if narrating to an operator instead of issuing the commit call. Per Principle 2 (Robust and Effective Over Cheap and Fast — `.cursor/rules/engineering-principles.mdc`), the right move was to remove the surface that produced the symptom rather than keep patching either the prompt or the dispatcher with model-side enforcement. The internal contract is preserved; only the model-facing tool shape changed.

### F. Hallucination guard

`grading.allowed_npc_slugs` lists exactly the eight slugs whose timelines exist in the pre-state. Any `append_timeline_row` whose `npc_slug` is outside this set is a hard fail (TP5).

### G. Timeline enumeration: option (a), `list_npc_timelines` deferred

For MVP, the user message **pre-loads** the eight timeline paths. The right long-term answer is a deterministic helper tool (`list_npc_timelines(campaign_hub)`), but it is out of scope for this MVP — see Backlog `[READY]` "Engineering principle — prefer deterministic corpus-search tools over LLM discovery". When that ticket lands, this slice will switch to option (b) (model calls the tool) and the user message will shrink accordingly.

---

## Gates

| ID | Description |
|----|-------------|
| TP1 | APPEND completeness: each `expected_appends` entry has ≥`expected_count` rows for the target session in its timeline file, and every `anchor_words` term appears (case-insensitive substring) at least once across the union of those new rows' beat-cell text. (See §A for rationale.) |
| TP2 | SKIP correctness: no `**20**` row exists in any skip-target timeline after the run. |
| TP3 | Tool contract: no `write_corpus_file` (recap is pre-pinned); none of `assemble_recap_draft` / `build_recap_write_payload` / `get_recap_context` fired. |
| ~~TP4~~ | **Removed in Iteration 6 — hub proposals are out of scope for this slice; revisit when timelines are reliably passing.** |
| TP5 | Hallucination guard: every `append_timeline_row` call's `npc_slug` is in `allowed_npc_slugs`. |
| TP6 | Pre-state offline: pytest asserts the six target rows are absent and the two skip-target rows match HEAD bytes after pre-state build. |

**Pass:** TP1, TP2, TP3, TP5 true for a live run; TP6 verified offline.

---

## Run protocol

1. **Offline:** `uv run pytest tests/test_timeline_pass_grader.py tests/test_timeline_pass_pre_state.py -q`
2. **Pre-state spot-check:** `step1_timeline_pass_run.py --print-root`, then assert recap exists and the four target timelines have no `| **20** |` row, and the two skip-target timelines match HEAD bytes.
3. **Live cohort:** `step1_timeline_pass_run.py --n 3 --model gpt-5.4-mini` with `DUNGEONMIND_PLANNER_ALLOW_WRITES=1`.
4. **Budget:** stop early if cumulative live spend exceeds **$1.50** with **≤1** pass (harness guard); hard cap **$3.00** total (4 appends per run, expected ~3× per-run cost vs. v0).

---

## Artifacts

Per run: `timeline_pass--<scenario>--<model>--PASS|FAIL--1turn--<utc>--runNNN.{md,json}` under `evals/session_recap_timeline_pass_vertical_slice/artifacts/runs/<YYYY-MM-DD>/`.

Cohort summary: `timeline_pass_summary--<model>--N<n>--<utc>.{md,json}` (includes per-gate pass counts across runs).

---

## Known design caveats / follow-ups

1. ~~**PC-timeline writer allowlist gap.**~~ **Resolved 2026-04-21 (Iteration 2 Fix 1).** `_TIMELINE_RE` is now `(?:^|/)(?:NPCs|PCs)/[^/]+/timeline\.md$`, accepting both NPC and PC paths for `append` mode. Strict scope: `append_timeline_row` only — no other writer-allowlist branch (create, README, dossier, etc.) was touched. Verified live in iteration-2 run 1 where the Caelynn preview returned `ok=true phase=preview`. Unit coverage: `tests/test_corpus_writer.py::test_timeline_allowlist_accepts_npc_and_pc_paths` plus a denial-list parametrize for look-alike paths.
2. **Deterministic discovery tool deferred.** See §G; option (a) (pre-loaded list) is the MVP shortcut. A `list_npc_timelines(campaign_hub)` tool would let the planner discover the timeline set itself and would shrink the gold user message dramatically.
3. ~~**Hub-proposal richness.**~~ **Out of scope as of Iteration 6.** Hub-proposal evaluation will return as a separate slice once timelines pass reliably; the iteration-1/2 `unsure_queue` substring scaffolding has been removed from this gold and grader.
4. **Anchor-word list maintenance.** Anchor lists are short and live in gold. When session content shifts (new NPC arc, new mechanics), update them in `gold/timeline_pass_session20.json` rather than the grader. Three to six anchor words per character is the budget — past that, the rubric is doing review-pass work that should live with the human.

---

## Relationship to v0 (`session_recap_timeline_append_vertical_slice/`)

- v0 is **operator-instructed single-NPC append** on Lysandra. This slice does **not** modify v0's code, gold, or STATUS doc.
- As of Iteration 6, this slice imports only the v0 helpers it still needs — `_iter_tool_trace`, `violations_forbid_write_corpus_file`, `violations_forbidden_tool_names`. Row grading is now local (count + anchor-words on disk); the v0 hybrid `grade_timeline_row_hybrid` rubric is no longer invoked here.
- v0's pre-state pins the recap from gold; this slice does the same with the same `Session 20 - Recap.md` byte snapshot for reproducibility independent of live corpus drift.
