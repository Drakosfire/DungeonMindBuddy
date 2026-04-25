# Sentence routing and retrieval falsification (scaffold)

Companion plan: `Docs/Plans/EXPERIMENT-Sentence-Routing-Retrieval-Falsification.md`  
Operational guardrails: `Docs/Plans/GUARDRAILS-Sentence-Grounded-Ingestion-Vision.md`

## Harness names (read this first)


| Stage | What the harness does                                       | Run with                                                                     | Dated artifact filename                                                       | Last-run mirror (under `artifacts/`)               |
| ----- | ----------------------------------------------------------- | ---------------------------------------------------------------------------- | ----------------------------------------------------------------------------- | -------------------------------------------------- |
| **A** | Deterministic **sentence-unit capture** from recap markdown | `python -m evals.sentence_routing_retrieval_falsification.step1_capture_run` | `sentence_routing_stage_a_capture--<scenario>--<PASS_or_FAIL>--<UTC>.json`    | `last_sentence_routing_stage_a_capture.json`       |
| **B** | **Hub routing** (each unit → allowed hub slugs)             | `python -m evals.sentence_routing_retrieval_falsification.step2_route_run`   | `sentence_routing_stage_b_hub_routes--<scenario>--<PASS_or_FAIL>--<UTC>.json` | `last_sentence_routing_stage_b_hub_routes.json`    |
| **B cohort** | Repeat Stage B **N** times; aggregate pass rate + cost | same module + ``--n <N>`` (N>1) | `sentence_routing_stage_b_cohort_summary--<model>--N<n>--<UTC>.json` (+ `.md`) | (stderr lists paths; no mirror file) |
| **C** | New-hub proposals (planned)                                 | `step3_propose_run.py` (TBD)                                                 | `sentence_routing_stage_c_hub_proposals--…`                                   | `last_sentence_routing_stage_c_hub_proposals.json` |
| **D** | Scoped **retrieval context pack** (planned)                 | `step4_retrieval_pack_run.py` (TBD)                                          | `sentence_routing_stage_d_context_pack--…`                                    | `last_sentence_routing_stage_d_context_pack.json`  |


Module filenames keep the historical `step1_`* / `step2_*` pattern so `python -m` invocations stay stable; **artifact names** use the explicit `sentence_routing_stage_`* prefix.

## What exists today

- **Stage A:** `capture.py` splits recap lines into `sentence_units` with 1-based line addresses; `step1_capture_run.py` writes Stage A sidecars.
- **Stage B:** `route_schema.py` (manifest + `sentence_hub_routes_v1`); `grader.py` (`normalize_gold_routing_matches`, `collect_stage_b_violations`); `step2_route_run.py` (OpenAI or `--no-llm` + `fixture_routes`; `--n` for cohort summaries via `sentence_routing_stage_b_cohort_report.py`).
- **Stages C–D:** stubbed in grader telemetry until gold + runners exist.

## Run

**Stage A — capture:**

```bash
uv run python -m evals.sentence_routing_retrieval_falsification.step1_capture_run
```

**Stage B — hub routing (offline, CI-safe):** uses `fixture_routes` in `gold/scenario_mini.json`:

```bash
uv run python -m evals.sentence_routing_retrieval_falsification.step2_route_run --no-llm
```

**Stage B — cohort (e.g. N=3, still offline with fixture):**

```bash
uv run python -m evals.sentence_routing_retrieval_falsification.step2_route_run --n 3 --no-llm
```

**Real-recap scaffold:** `gold/scenario_real_recap_template.json` — runnable default (mini fixture); copy and set `input.recap_relative_path` + `hub_manifest` + `gold_*` after GM approval (see `scenario_notes` in file).

**Stage B — hub routing (live LLM):** requires `OPENAI_API_KEY` after `load_dungeonmindbuddy_dotenv()`; model defaults to `DUNGEONMIND_PLANNER_MODEL` or `gpt-5.4-mini`. Chain from the Stage A mirror file:

```bash
uv run python -m evals.sentence_routing_retrieval_falsification.step1_capture_run
uv run python -m evals.sentence_routing_retrieval_falsification.step2_route_run \\
  --prior-json evals/sentence_routing_retrieval_falsification/artifacts/last_sentence_routing_stage_a_capture.json
```

## Fixture + gold

- `fixtures/mini_recap.md` — tiny synthetic recap (no corpus PII).
- `gold/scenario_mini.json` — `gold_capture`, `input.hub_manifest`, `gold_routing`, `fixture_routes` for `--no-llm`.
- `gold/scenario_real_recap_template.json` — same shape with `gold_routing` using **match** rows (DESIGN §6.5); replace paths for a pinned corpus recap when promoting.

## Known limitations (v0 capture)

Sentence splitting uses a simple regex; abbreviations and dialogue punctuation can misfire. The suite is designed to be **falsifiable**: tighten rules or replace with a tokenizer once failure buckets justify it.