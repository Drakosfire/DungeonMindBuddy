# Lysandra vertical slice — gate completion (signpost)

Canonical “is this step done?” answers for humans and agents.

**Planner alignment (one line):** Production-style document choice in Buddy is **`run_planning_turn_detailed`** → **`read_corpus_file`** → **`tool_trace`**. Prefer extending benchmarks with **trace-based gates**; Step 1 keyword scan is an **offline baseline** only (`step1_retrieval.py`). Details: `Docs/Plans/DESIGN-lysandra-statblock-vertical-slice-benchmark.md` → subsection *Planner alignment — one line*.

**Machine hooks:** `gold/step0_status.json`, `gold/step1_status.json`, `gold/planner_step1_status.json`.

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
| **Lane A** | Did the real planner loop open the dossier and Session 18 recap? | `read_corpus_file` paths in `PlanningTurnDetail.tool_trace` match `gold/planner_step1.json` → `final.require` (substring checks + `read_corpus_file` present + `min_output_chars`; `hit_tool_round_limit` fails via shared live_eval rules). |

**Harness:** `step1_planner_trace.py` → `run_planner_step1_turn()` (same wiring as planner live eval: manifest, tools, `make_tool_dispatcher`).

**Verify (no API):**

```bash
uv run pytest tests/test_lysandra_vertical_slice_planner_step1.py -q
```

**Verify (live model, costs money):** `LYSANDRA_PLANNER_STEP1_LIVE=1`, corpus present, and `OPENAI_API_KEY` in `.env` / `.env.development` (loaded by pytest `conftest` + harness — no `export` required) — same pytest file runs `test_planner_step1_live_passes_with_model`.

**CLI (manual, from repo root):** `uv run python evals/lysandra_vertical_slice/step1_planner_trace.py` — prints a review (turns, per-round `input_tokens`, replayed corpus bodies, final answer) and emits `dmb.planner` JSON telemetry on stderr. Optional: `PLANNER_LOG_FULL_IO=1` for larger telemetry payloads.

**Artifacts:** `gold/planner_step1.json`, `step1_planner_trace.py`, `tests/test_lysandra_vertical_slice_planner_step1.py`.

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

## Step 2 — Canonical statblock selection (next)

**Status: NOT STARTED.**

Implement `G2.*` when a machine-readable statblock path exists or when gold defines extractors for narrative-only sources.

---

## Step 3+

See `Docs/Plans/DESIGN-lysandra-statblock-vertical-slice-benchmark.md` §6; update this file when each step lands.
