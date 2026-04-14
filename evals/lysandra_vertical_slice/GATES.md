# Lysandra vertical slice — gate completion (signpost)

Canonical “is this step done?” answers for humans and agents.

**Planner alignment (one line):** Production-style document choice in Buddy is **`run_planning_turn_detailed`** → **`read_corpus_file`** → **`tool_trace`**. Prefer extending benchmarks with **trace-based gates**; Step 1 keyword scan is an **offline baseline** only (`step1_retrieval.py`). Details: `Docs/Plans/DESIGN-lysandra-statblock-vertical-slice-benchmark.md` → subsection *Planner alignment — one line*.

**Machine hooks:** `gold/step0_status.json`, `gold/step1_status.json`, `gold/planner_step1_status.json`, `gold/step2_status.json`, `gold/step3_status.json`, `gold/step4_status.json`.

---

## Step 0 — Corpus pin + environment (G0.1–G0.3)

**Status: DONE (implementation + tests).**

| Gate | Question | Done when |
|------|----------|-----------|
| **G0.1** | Is the corpus directory present? | `resolve_corpus_dir()` exists and `corpus/eldyrwild-markdown` is a directory in this repo. |
| **G0.2** | Does the tree match pinned gold? | `gold/step0_environment.json` → `expected_fingerprint` equals `corpus_fingerprint(corpus_dir)` from `src.agent.planner_cache`. Refresh gold after intentional corpus edits. |
| **G0.3** | Is statblock integration configured *or* explicitly skipped? | One of: non-empty `DUNGEONMIND_STATBLOCK_URL`, or `LYSANDRA_SLICE_MOCK_STATBLOCK=1`, or `LYSANDRA_SLICE_SKIP_STATBLOCK_URL_GATE=1` (corpus-only / CI). |

**Verify:**

```bash
cd /path/to/DungeonMindBuddy
uv run pytest tests/test_lysandra_vertical_slice_step0.py -q
```

**Artifacts:** `gold/step0_environment.json`, `gold/corpus_policy.json`, `step0_corpus_environment.py`, `SURVEY-captain_lysandra_corpus.md`.

---

## Step 1 — Retrieval (two lanes)

### Lane A — Planner `tool_trace` (primary)

**Status: DONE (fixture + harness + unit tests; live opt-in).**

| Check | Question | Done when |
|-------|----------|-----------|
| **Lane A** | Did the planner loop open the right corpus files for the scenario? | `read_corpus_file` paths in `PlanningTurnDetail.tool_trace` match the chosen gold fixture → `final.require` (substring checks + `read_corpus_file` present + `min_output_chars`; `hit_tool_round_limit` fails via shared live_eval rules). **Directed** / **Autonomous** / **Stat check** — see `gold/planner_step1_*.json` and each `fixture_note`. Env: `LYSANDRA_PLANNER_STEP1_SCENARIO` = `directed` \| `autonomous` (default) \| `stat_check`. After the turn, **Step 2 planner bridge** (same `user_message`, optional trace vs `corpus_policy.canonical_statblock_relpath`) merges violations under `step2_bridge` — see Step 2 §bridge. |

**Harness:** `step1_planner_trace.py` → `run_planner_step1_turn()` (same wiring as planner live eval: manifest, tools, `make_tool_dispatcher`).

**Verify (no API):**

```bash
uv run pytest tests/test_lysandra_vertical_slice_planner_step1.py -q
```

**Verify (live model, costs money):** `LYSANDRA_PLANNER_STEP1_LIVE=1`, optional `LYSANDRA_PLANNER_STEP1_SCENARIO` (default **autonomous**), corpus present, and `OPENAI_API_KEY` in `.env` / `.env.development` (loaded by pytest `conftest` + harness — no `export` required) — same pytest file runs `test_planner_step1_live_passes_with_model`.

**CLI (manual, from repo root):** `uv run python evals/lysandra_vertical_slice/step1_planner_trace.py` — prints a review (turns, per-round `input_tokens`, replayed corpus bodies, final answer) and emits `dmb.planner` JSON telemetry on stderr. Optional: `PLANNER_LOG_FULL_IO=1` for larger telemetry payloads.

**Artifacts:** `gold/planner_step1_directed.json`, `gold/planner_step1_autonomous.json`, `gold/planner_step1_stat_check.json`, `step1_planner_trace.py`, `tests/test_lysandra_vertical_slice_planner_step1.py`.

---

### Lane B — Keyword scan (G1.1–G1.3, offline baseline)

**Status: DONE (keyword scan v1 + tests).**

| Gate | Question | Done when |
|------|----------|-----------|
| **G1.1** | Are required Lysandra files in the top‑K recall list? | Every path in `gold/step1_retrieval.json` → `required_paths_retrieved` appears in the first `top_k` rows of the keyword-ranked list. |
| **G1.2** | Is the Step‑2 seed (or canonical statblock) recalled? | If `corpus_policy.canonical_statblock_relpath` is set, it must be in top‑`K`. If **null**, `primary_reference_relpath` and `session_anchor_relpath` must both be in top‑`K`. |
| **G1.3** | Are all candidates under allowed corpus roots? | Every ranked path must start with one of `corpus_policy.corpus_roots_allowed_prefixes`. |

**Retriever (v1):** Case-insensitive substring counts for `corpus_policy.aliases` over markdown under `gold/step1_retrieval.json` → `scan_subdirs` (default `Longmont Campaign`, `Elderwyld`; ~130 files).

**Verify:**

```bash
uv run pytest tests/test_lysandra_vertical_slice_step1.py -q
```

**Artifacts:** `gold/step1_retrieval.json`, `step1_retrieval.py` (`keyword_scan_ranked`, `run_step1_gates`, `run_step1_keyword_scan_and_gates`).

---

## Step 2 — Canonical statblock + intent classification (v1)

**Status: IMPLEMENTED (deterministic; no LLM).**

Draft gate updates (aligned to CR-first NPC workflow and ambiguous "level" language):

| Gate | Question | Done when |
|------|----------|-----------|
| **G2.1** | Is canonical statblock selected deterministically? | Selected path matches `corpus_policy.canonical_statblock_relpath` or deterministic selection rule. |
| **G2.2** | Is extracted canonical content structurally valid? | Required statblock markers are present (`Armor Class`, `Hit Points`, `Challenge Rating`, etc., per gold) in the **full** file read. `run_step2_canonical_gates` `detail` also includes `extracted_markdown`, `extracted_section_span`, and `selection_reason` (see harness). |
| **G2.3** | Is canonical selection unique? | No unresolved ties; tie-break rule is explicit and logged. |
| **G2.4.1** | Is user intent mode classified? | Classifier emits one of `factual_lookup`, `upgrade_request`, `comparison_request`. |
| **G2.4.2** | Is power axis classified? | Axis is one of `challenge_rating`, `class_level`, `hybrid`, `unknown`. |
| **G2.4.3** | Is clarifier required when axis is ambiguous for upgrade asks? | For upgrade asks with `unknown` axis, set `clarifier_required=true` and emit one concise clarifier question. |
| **G2.4.4** | Are factual asks CR-safe? | Factual mode does not force class-level when only CR evidence exists (permits `class_level_current=null`). |

**Planner bridge (Lane A + Step 2, optional via gold):** After `run_planner_step1_turn`, `gold/step2_canonical_and_intent.json` → `planner_bridge` runs `classify_intent` on the **same** planner `user_message` and checks intent expectations per `fixture_role` (`intent_expectations_by_planner_scenario_key`). If `assert_statblock_read_matches_canonical_when_present` is true and the trace includes any Lysandra `*_statblock_*.md` read, the **canonical** path from `corpus_policy.canonical_statblock_relpath` must appear among those reads (opening an archive sheet such as CR2 **in addition** to canonical is allowed). Violations are attached as `step2_bridge` on `LiveEvalResult` without changing Lane A substring gates.

**Verify:**

```bash
uv run pytest tests/test_lysandra_vertical_slice_step2.py -q
uv run python evals/lysandra_vertical_slice/step2_canonical_intent.py
```

**Artifacts:** `gold/step2_canonical_and_intent.json`, `step2_canonical_intent.py`, `tests/test_lysandra_vertical_slice_step2.py`.

---

## Step 3 — `power_baseline` + evidence spans (G3.*)

**Status: IMPLEMENTED (deterministic v1; no LLM).**

| Gate | Question | Done when |
|------|----------|-----------|
| **G3.1** | Does parsed CR match gold? | `power_baseline.challenge_rating_current` equals `gold/step3_power_baseline.json` → `expected_power_baseline.challenge_rating_current` when the canonical statblock body parses a CR line. |
| **G3.2** | Are configured evidence fields anchored to verbatim text? | For each field in `evidence_span_fields`, `run_step3_power_baseline_gates` finds one logical line; each span’s `verbatim` equals `body[start_char:end_char]` with exclusive `end_char` (`end_char_exclusive: true`). |
| **G3.3** | Is class level handled for v1? | `class_level_current` is `null` and matches gold when gold expects null. |
| **G3.4** | What if the CR line is missing? | Gold `fallback_when_cr_absent` supplies `power_baseline` and `evidence_spans`; harness applies it and does not fail closed for “no CR line” alone. |

**Harness:** `step3_power_baseline.py` — `run_step3_power_baseline_gates(corpus_dir, step2_canonical_detail=…)` (or omit detail to run Step 2 canonical first). `run_step2_and_step3()` runs Step 2 canonical + intent fixtures, then Step 3.

**Verify:**

```bash
uv run pytest tests/test_lysandra_vertical_slice_step3.py -q
uv run python evals/lysandra_vertical_slice/step3_power_baseline.py
```

**Artifacts:** `gold/step3_power_baseline.json`, `gold/step3_status.json`, `step3_power_baseline.py`, `tests/test_lysandra_vertical_slice_step3.py`.

---

## Step 4 — Level-up **context bundle** (deterministic; no model-output schema)

**Status: IMPLEMENTED (deterministic v1).** Assembles grounding for a downstream generator: `power_baseline` + gold `target_challenge_rating`, statblock excerpt, C2 dossier excerpt, optional `session_anchor_relpath` excerpt from `corpus_policy`, and **keyword-ranked** session recap snippets (policy aliases + optional theme-keyword boosts; per-file snippet = **highest-scoring paragraph** by default, else first-alias window).

| Check | Question | Done when |
|-------|----------|-----------|
| **G4.1** | Is target CR strictly above baseline? | `target_challenge_rating` from `gold/step4_levelup_context.json` exceeds `power_baseline.challenge_rating_current` from Step 3 (baseline must be numeric). |
| **G4_RECAP** | Does the recap bundle meet gold assertions? | At least `min_recap_snippets` snippets; union of `verbatim` contains every `assert_snippets_union_contains_substrings` entry; at least one of `assert_snippets_union_contains_one_of`. |

**Harness:** `step4_levelup_context.py` — `build_levelup_context_bundle`, `run_step4_levelup_context_gates`, `run_step2_through_step4`, `assemble_model_context_plaintext`.

**Verify:**

```bash
uv run pytest tests/test_lysandra_vertical_slice_step4.py -q
uv run python evals/lysandra_vertical_slice/step4_levelup_context.py
```

**Artifacts:** `gold/step4_levelup_context.json`, `gold/step4_status.json`, `step4_levelup_context.py`, `tests/test_lysandra_vertical_slice_step4.py`.

---

## Step 5+

See `Docs/Plans/DESIGN-lysandra-statblock-vertical-slice-benchmark.md` §6 (Statblock service call); update this file when each step lands.
