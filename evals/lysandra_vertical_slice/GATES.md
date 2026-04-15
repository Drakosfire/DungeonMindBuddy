# Lysandra vertical slice — gate completion (signpost)

Canonical "is this step done?" answers for humans and agents.

**Agent loop is the product:** Document choice in Buddy is **`run_planning_turn_detailed`** → **`read_corpus_file`** → **`tool_trace`**. The agent receives a natural user ask and figures out what to do. Benchmarks gate on the **trace** (what the agent opened) and the **output** (what the agent wrote). Details: `Docs/Plans/DESIGN-lysandra-statblock-vertical-slice-benchmark.md`.

**Machine hooks:** `gold/step0_status.json`, `gold/step1_status.json`, `gold/planner_step1_status.json`, `gold/step2_status.json`, `gold/step3_status.json`, `gold/step4_status.json`.

**Unified deterministic run (no LLM):** `run_vertical_slice_deterministic()` in `run_deterministic_slice.py` chains Step 0 → Step 1 keyword gates → `run_step2_through_step4` (Steps 2–4). CLI: `uv run python evals/lysandra_vertical_slice/run_deterministic_slice.py` (set `LYSANDRA_SLICE_SKIP_STATBLOCK_URL_GATE=1` for corpus-only if G0.3 is not satisfied). Tests: `tests/test_lysandra_vertical_slice_run_deterministic.py`.

---

## Step 0 — Corpus pin + environment (G0.1–G0.2)

**Status: DONE (implementation + tests).**

| Gate | Question | Done when |
|------|----------|-----------|
| **G0.1** | Is the corpus directory present? | `resolve_corpus_dir()` exists and `corpus/eldyrwild-markdown` is a directory in this repo. |
| **G0.2** | Does the tree match pinned gold? | `gold/step0_environment.json` → `expected_fingerprint` equals `corpus_fingerprint(corpus_dir)` from `src.agent.planner_cache`. Refresh gold after intentional corpus edits. |

**Verify:**

```bash
cd /path/to/DungeonMindBuddy
uv run pytest tests/test_lysandra_vertical_slice_step0.py -q
```

**Artifacts:** `gold/step0_environment.json`, `gold/corpus_policy.json`, `step0_corpus_environment.py`, `SURVEY-captain_lysandra_corpus.md`.

---

## Step 1 — Agent retrieval (planner trace)

**Status: DONE (fixture + harness + unit tests; live opt-in).**

| Check | Question | Done when |
|-------|----------|-----------|
| **Agent benchmark** | Did the agent, given a natural user ask, open the right corpus files and produce a grounded response? | `read_corpus_file` paths in `PlanningTurnDetail.tool_trace` match the chosen gold fixture → `final.require` (substring checks + `read_corpus_file` present + `min_output_chars`; `hit_tool_round_limit` fails via shared live_eval rules). Scenarios: **directed**, **autonomous**, **stat_check**, **upgrade_prose** — see `gold/planner_step1_*.json`. Env: `LYSANDRA_PLANNER_STEP1_SCENARIO` (CLI **default** when unset: **`upgrade_prose`** — natural power-rise ask). After the turn, optional **Step 2 benchmark** checks (`evaluate_step2_post_planner_benchmark`; observation only, see `Docs/Plans/NAMING-benchmark-vs-runtime.md`). |

**Harness:** `step1_planner_trace.py` → `run_planner_step1_turn()` (same wiring as planner live eval: manifest, tools, `make_tool_dispatcher`).

**Verify (no API):**

```bash
uv run pytest tests/test_lysandra_vertical_slice_planner_step1.py -q
```

**Verify (live model, costs money):** `LYSANDRA_PLANNER_STEP1_LIVE=1`, optional `LYSANDRA_PLANNER_STEP1_SCENARIO` (CLI default **upgrade_prose** when unset), corpus present, and `OPENAI_API_KEY` in `.env` / `.env.development` (loaded by pytest `conftest` + harness — no `export` required) — same pytest file runs `test_planner_step1_live_passes_with_model`.

**CLI (manual, from repo root):** `uv run python evals/lysandra_vertical_slice/step1_planner_trace.py` — default scenario **upgrade_prose**; prints a review (turns, per-round `input_tokens`, replayed corpus bodies, final answer) and writes `artifacts/last_planner_step1_run.md`; emits `dmb.planner` JSON telemetry on stderr.

**Artifacts:** `gold/planner_step1_directed.json`, `gold/planner_step1_autonomous.json`, `gold/planner_step1_stat_check.json`, `gold/planner_step1_upgrade_prose.json`, `step1_planner_trace.py`, `tests/test_lysandra_vertical_slice_planner_step1.py`.

---

### Corpus keyword regression (offline, no LLM)

**Status: DONE (keyword scan v1 + tests).**

Separate from the agent benchmark. Verifies lexical signal exists in the corpus for this entity — useful for gold authoring, regressions when corpus text moves, and CI without an API key. Does **not** prove the agent would open those files.

| Gate | Question | Done when |
|------|----------|-----------|
| **G1.1** | Are required entity files in the top‑K recall list? | Every path in `gold/step1_retrieval.json` → `required_paths_retrieved` appears in the first `top_k` rows of the keyword-ranked list. |
| **G1.2** | Is the canonical baseline recalled? | If `corpus_policy.canonical_statblock_relpath` is set, it must be in top‑`K`. |
| **G1.3** | Are all candidates under allowed corpus roots? | Every ranked path must start with one of `corpus_policy.corpus_roots_allowed_prefixes`. |

**Verify:**

```bash
uv run pytest tests/test_lysandra_vertical_slice_step1.py -q
```

**Artifacts:** `gold/step1_retrieval.json`, `step1_retrieval.py`.

---

## Step 2 — Canonical baseline + intent classification (v1)

**Status: IMPLEMENTED** (canonical gates deterministic; intent classification LLM-backed or test doubles).

| Gate | Question | Done when |
|------|----------|-----------|
| **G2.1** | Is canonical baseline selected deterministically? | Selected path matches `corpus_policy.canonical_statblock_relpath`. |
| **G2.2** | Is extracted content structurally valid? | Required statblock markers are present in the full file read. |
| **G2.3** | Is canonical selection unique? | No unresolved ties. |
| **G2.4.1** | Is user intent mode classified? | Classifier emits one of `factual_lookup`, `upgrade_request`, `comparison_request`. |
| **G2.4.2** | Is power axis classified? | Axis is one of `challenge_rating`, `class_level`, `hybrid`, `unknown`. |
| **G2.4.3** | Is clarifier required when axis is ambiguous for upgrade asks? | For upgrade asks with `unknown` axis, set `clarifier_required=true` and emit one concise clarifier question. |
| **G2.4.4** | Are factual asks safe? | Factual mode does not force class-level when only CR evidence exists. |

**Post-planner benchmark (optional, observation only):** After `run_planner_step1_turn`, `gold/step2_canonical_and_intent.json` → key `planner_bridge` configures `evaluate_step2_post_planner_benchmark`: runs `classify_intent` on the same planner `user_message` and may assert the canonical path appears in the trace. Violations merge under key `step2_bridge` on `LiveEvalResult` without changing agent behavior.

**Verify:**

```bash
uv run pytest tests/test_lysandra_vertical_slice_step2.py -q
uv run python evals/lysandra_vertical_slice/step2_canonical_intent.py
```

**Artifacts:** `gold/step2_canonical_and_intent.json`, `step2_canonical_intent.py`, `tests/test_lysandra_vertical_slice_step2.py`.

---

## Step 3 — Power baseline + evidence spans (G3.*)

**Status: IMPLEMENTED (deterministic v1; no LLM).**

| Gate | Question | Done when |
|------|----------|-----------|
| **G3.1** | Does parsed CR match gold? | `power_baseline.challenge_rating_current` equals gold expectation. |
| **G3.2** | Are evidence fields anchored to verbatim text? | Each span's `verbatim` equals `body[start_char:end_char]`. |
| **G3.3** | Is class level handled? | `class_level_current` is `null` and matches gold when gold expects null. |
| **G3.4** | What if the CR line is missing? | Gold `fallback_when_cr_absent` is applied. |

**Verify:**

```bash
uv run pytest tests/test_lysandra_vertical_slice_step3.py -q
```

**Artifacts:** `gold/step3_power_baseline.json`, `step3_power_baseline.py`, `tests/test_lysandra_vertical_slice_step3.py`.

---

## Step 4 — Level-up context bundle (deterministic)

**Status: IMPLEMENTED (deterministic v1).** Assembles a **regression bundle** for gates and humans — not fed to agent prompts.

| Check | Question | Done when |
|-------|----------|-----------|
| **G4.1** | Is target power strictly above baseline? | Gold `power_target.value` > Step 3 `challenge_rating_current` (v1: `challenge_rating` axis only). |
| **G4_RECAP** | Does the recap bundle meet gold assertions? | At least `min_recap_snippets` snippets; union of `verbatim` contains required substrings. |
| **G4_TIMELINE** | Is campaign continuity included? | If gold requires it: `corpus_policy.timeline_relpath` is non-empty, file exists, and bundle excerpt is non-empty. |

**Verify:**

```bash
uv run pytest tests/test_lysandra_vertical_slice_step4.py -q
```

**Artifacts:** `gold/step4_levelup_context.json`, `step4_levelup_context.py`, `tests/test_lysandra_vertical_slice_step4.py`.

---

## Steps 5+ (future scope)

See `Docs/Plans/DESIGN-lysandra-statblock-vertical-slice-benchmark.md` §8 (Future scope). Update this file when each step lands.
