# EXPERIMENT — Session recap autonomous timeline pass (Stage 2 v1)

**Parent v0 (operator-instructed):** [EXPERIMENT-Session-Recap-Timeline-Append-Benchmark.md](EXPERIMENT-Session-Recap-Timeline-Append-Benchmark.md) — single-NPC append on Lysandra. v0 stays as-is and is the tool-surface baseline; this slice grades **autonomous discovery + selectivity**.
**Slice root:** `evals/session_recap_timeline_pass_vertical_slice/`

This benchmark proves **autonomous downstream enrichment** after recap ingest: given a committed recap and a pre-loaded list of existing C2 timeline files, the planner decides which NPCs need a Session-N row, which to skip, and which prominent NPCs lack a hub entirely.

---

## Design choices (normative)

### A. Grading mode — **Hybrid** (per APPEND target)

Reuses v0's hybrid row rubric verbatim (imported from
`evals.session_recap_timeline_append_vertical_slice.grader`):

- **Cells 1 + 3 (session + recap pointer):** strict shape — session token `**N**`; third column must be a single backticked path whose basename is `Session N - Recap.md` (full corpus-relative path allowed).
- **Cell 2 (beat):** non-empty prose with **order-independent** regex anchors. Each APPEND target has its own anchor set in gold (e.g. Lysandra + one of forest/Mossford/camp/rocky/cult/tower/meat/antidote/charm/Sara/blueprint/shimmer).

### B. User message — **verbatim** (gold JSON), pre-loads the timeline list

Stored in `evals/session_recap_timeline_pass_vertical_slice/gold/timeline_pass_session20.json` under `input.user_message`. It names the recap path, **pre-loads the six existing C2 timeline file paths and their slugs** (option a — see §G), instructs a "timeline pass" with two-phase `append_timeline_row` (commit in same turn), forbids `write_corpus_file` and recap-assembly tools, and mandates the universal `planner_turn_output` envelope (no `recap_write` field).

### C. Skill choice — **Option (b): skill-less turn**

Same as v0: `active_skill_id=None` → universal JSON schema. Runner appends an
**eval-only suffix** after `load_or_build_planner_instructions` (does **not** edit `corpus_session_planner.py`) explaining the timeline-pass contract, the PC-path `timeline_path` requirement, the skip-without-append rule, and the hub-proposal `unsure_queue` convention.

### D. Cohort scope — **Session 20 (C2)**

The first cohort uses Session 20 because all six existing C2 timelines either need a row or have a clean SKIP rationale, and four high-prominence S20 NPCs lack hubs (Karsemine, Ephanna, Stafl, Marla) — letting us exercise APPEND, SKIP, and FLAG in one turn.

### E. Hub-proposal `unsure_queue` overload

No schema change to `planner_turn_output`. Instead each hub-proposal item uses:

- `id` like `hub_proposal_karsemine` (snake_case),
- `question` literally starting with `hub-proposal: <slug-or-name> — <one-line why>`,
- `default_summary` describing what would be created (e.g. empty `NPCs/<slug>/{README.md,timeline.md}` skeleton),
- ≥ 2 `alternative_summaries`.

**TP4 prefix contract (Iteration 2, 2026-04-21):** the grader now requires the literal `hub-proposal:` prefix (case-insensitive on the token, mandatory colon) at the start of the queue entry's `question` field. Only entries that pass this prefix gate are eligible to satisfy a must-flag name; the must-flag (slug or surface name, case-insensitive) must then appear within that same qualifying entry's flattened text (`id` + `question` + `default_summary` + `alternative_summaries`). Soft flags follow the same prefix rule. The bare-substring matcher used in iteration 1 was both too lenient (counted any incidental mention) and too strict (the model rarely produced the prefix without an example). The current scenario JSON shape (`expected_hub_proposals_must` as a list of bare slug/surface strings) is unchanged; the grader does the prefix work.

### F. Hallucination guard

`grading.allowed_npc_slugs` lists exactly the six slugs whose timelines exist in the pre-state. Any `append_timeline_row` whose `npc_slug` is outside this set is a hard fail (TP5). This is a budget guard against the model inventing slugs / paths.

### G. Timeline enumeration: option (a), `list_npc_timelines` deferred

For MVP, the user message **pre-loads** the six timeline paths. The right long-term answer is a deterministic helper tool (`list_npc_timelines(campaign_hub)`), but it is out of scope for this MVP — see Backlog `[READY]` "Engineering principle — prefer deterministic corpus-search tools over LLM discovery". When that ticket lands, this slice will switch to option (b) (model calls the tool) and the user message will shrink accordingly.

---

## Gates

| ID | Description |
|----|-------------|
| TP1 | APPEND completeness: preview→commit pair landed for all four expected_appends; each resulting row passes the v0 hybrid rubric (per-NPC `beat_regex`). |
| TP2 | SKIP correctness: no `**20**` row exists in either skip-target timeline after the run. |
| TP3 | Tool contract: every `append_timeline_row` is preview→commit (per-slug ordering: first call preview, last commit; last commit `ok=true phase=committed`); no `write_corpus_file`; none of `assemble_recap_draft`/`build_recap_write_payload`/`get_recap_context` fired. |
| TP4 | FLAG completeness: `unsure_queue` substring matches each must-flag name (`karsemine`, `ephanna`, `stafl`, `marla`). Soft flags (`stuart`, `stacey`) are scored for telemetry, not gated. |
| TP5 | Hallucination guard: every `append_timeline_row` call's `npc_slug` is in `allowed_npc_slugs`. |
| TP6 | Pre-state offline: pytest asserts the four target rows are absent and the two skip-target rows match HEAD bytes after pre-state build. |

**Pass:** TP1–TP5 true for a live run; TP6 verified offline.

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
3. **Hub-proposal richness.** `unsure_queue` substring matching is intentionally permissive for MVP. A future tightening could require structured fields (e.g. a typed `proposed_paths` list) once the convention is stable.

---

## Relationship to v0 (`session_recap_timeline_append_vertical_slice/`)

- v0 is **operator-instructed single-NPC append** on Lysandra. This slice does **not** modify v0's code, gold, or STATUS doc.
- This slice **imports** v0's grader helpers (`_commit_outcome`, `_dry_run_arg`, `find_session_table_row`, `grade_timeline_row_hybrid`, `violations_forbid_write_corpus_file`, `violations_forbidden_tool_names`) so the per-NPC row rubric and forbidden-tool checks stay in one place.
- v0's pre-state pins the recap from gold; this slice does the same with the same `Session 20 - Recap.md` byte snapshot for reproducibility independent of live corpus drift.
