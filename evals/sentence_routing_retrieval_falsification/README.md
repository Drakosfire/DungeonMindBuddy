# Sentence routing and retrieval falsification (scaffold)

Companion plan: `Docs/Plans/EXPERIMENT-Sentence-Routing-Retrieval-Falsification.md`  
Operational guardrails: `Docs/Plans/GUARDRAILS-Sentence-Grounded-Ingestion-Vision.md`

## Pipeline steps (read this first)

**Explicit names** (what each step is for) and **legacy letter labels** (still used in filenames and JSON keys for compatibility):

| Explicit name | Legacy | What it does | Run with | Dated artifact filename | Last-run mirror (under `artifacts/`) |
| --- | --- | --- | --- | --- | --- |
| **`capture_sentence_units`** | A | Deterministic **sentence-unit capture** from recap markdown | `python -m evals.sentence_routing_retrieval_falsification.step1_capture_run` | `sentence_routing_stage_a_capture--<scenario>--<PASS_or_FAIL>--<UTC>.json` | `last_sentence_routing_stage_a_capture.json` |
| **`route_sentence_units_to_hubs`** | B | **Hub routing** (each unit → allowed hub slugs) | `python -m evals.sentence_routing_retrieval_falsification.step2_route_run` | `sentence_routing_stage_b_hub_routes--<scenario>--<PASS_or_FAIL>--<UTC>.json` | `last_sentence_routing_stage_b_hub_routes.json` |
| **`route_sentence_units_to_hubs` (cohort)** | B | Repeat routing **N** times; aggregate pass rate + cost | same module + `--n <N>` (N>1) | `sentence_routing_stage_b_cohort_summary--<model>--N<n>--<UTC>.json` (+ `.md`) | (stderr lists paths; no mirror file) |
| **`propose_new_hubs_from_unmapped_units`** | C | New-hub proposals (planned) | `step3_propose_run.py` (TBD) | `sentence_routing_stage_c_hub_proposals--…` | `last_sentence_routing_stage_c_hub_proposals.json` |
| **`assemble_hub_scoped_retrieval_context`** | D | Scoped **retrieval context pack** (planned) | `step4_retrieval_pack_run.py` (TBD) | `sentence_routing_stage_d_context_pack--…` | `last_sentence_routing_stage_d_context_pack.json` |


Module filenames keep the historical `step1_`* / `step2_`* pattern so `python -m` invocations stay stable; **artifact names** use the explicit `sentence_routing_stage_`* prefix.

## What exists today

- **`capture_sentence_units` (A):** `capture.py` splits recap lines into `sentence_units` with 1-based line addresses; `step1_capture_run.py` writes capture sidecars.
- **`route_sentence_units_to_hubs` (B):** `route_schema.py` (manifest + `sentence_hub_routes_v1`); `grader.py` (`normalize_gold_routing_matches`, `collect_stage_b_violations`); `step2_route_run.py` (OpenAI or `--no-llm` + `fixture_routes`; `--n` for cohort summaries via `sentence_routing_stage_b_cohort_report.py`).
- **`propose_new_hubs_from_unmapped_units` / `assemble_hub_scoped_retrieval_context` (C–D):** stubbed in grader telemetry until gold + runners exist.

## Run

**`capture_sentence_units` (A) — capture:**

```bash
uv run python -m evals.sentence_routing_retrieval_falsification.step1_capture_run
```

**`route_sentence_units_to_hubs` (B) — hub routing (offline, CI-safe):** uses `fixture_routes` in `gold/scenario_mini.json`:

```bash
uv run python -m evals.sentence_routing_retrieval_falsification.step2_route_run --no-llm
```

**`route_sentence_units_to_hubs` (B) — cohort (e.g. N=3, still offline with fixture):**

```bash
uv run python -m evals.sentence_routing_retrieval_falsification.step2_route_run --n 3 --no-llm
```

**Real-recap scaffold:** `gold/scenario_real_recap_template.json` — runnable default (mini fixture); copy and set `input.recap_relative_path` + `hub_manifest` + `gold_`* after GM approval (see `scenario_notes` in file).

**`route_sentence_units_to_hubs` (B) — hub routing (live LLM):** requires `OPENAI_API_KEY` after `load_dungeonmindbuddy_dotenv()`; model defaults to `DUNGEONMIND_PLANNER_MODEL` or `gpt-5.4-mini`. Chain from the capture mirror file:

```bash
uv run python -m evals.sentence_routing_retrieval_falsification.step1_capture_run
uv run python -m evals.sentence_routing_retrieval_falsification.step2_route_run \\
  --prior-json evals/sentence_routing_retrieval_falsification/artifacts/last_sentence_routing_stage_a_capture.json
```

## Fixture + gold

- `fixtures/mini_recap.md` — tiny synthetic recap (no corpus PII).
- `gold/scenario_mini.json` — `gold_capture`, `input.hub_manifest`, `gold_routing`, `fixture_routes` for `--no-llm`.
- `gold/scenario_real_recap_template.json` — same shape with `gold_routing` using **match** rows (DESIGN §6.5); replace paths for a pinned corpus recap when promoting.
- `gold/scenario_c1_session1_pc.json`, `gold/scenario_c1_session2_pc.json`, `gold/scenario_c1_session3_pc.json`, `gold/scenario_c2_session20_pc.json` — real-recap **PC-only** routing gates for **`route_sentence_units_to_hubs` (B)** (manifest = that campaign’s PC hubs only). Semantics:
  - **must_route:** any PC named or clearly implicated as actor, object, addressee, rescuer, or **affected party** in the unit must appear in `expected_hubs` (subset of model `assigned_hubs`). After the roster is established, party-wide beats that say **the team** / **teammates** in a fight or job, or **first combat** + **team**, may **must_route all PCs**; **the group** may **must_route all PCs** when the PCs are the joint subject of movement or approach in that unit—otherwise vague **the group** framing stays **must_abstain** (see `scenario_c1_session1_pc.json` `scenario_notes`).
  - **Pronoun / continuation:** when the prior narrative focal names a PC and the unit is clearly the same beat, gold may **must_route** that PC even if the surface text is pronoun-heavy (see per-scenario `scenario_notes` + `fixture_routes`).
  - **must_abstain:** `max_assigned_hubs: 0` keeps the model from attaching recap beats to PC hubs when no PC belongs there. For **named NPCs/locations not in the manifest**, do **not** require `needs_new_hub_candidate: false` — the runner does not treat `candidate: true` as a B2 failure by itself; purely generic rows still pin `needs_new_hub_candidate: false` for abstain pressure.

## Hypothesis 1 (H1) — party vs generic group vs named PCs

Tool module: [`h1_routing_evidence.py`](h1_routing_evidence.py). It classifies `violations.stage_b` strings into buckets (`named_pc_omission`, `party_reference_boundary`, `pronoun_carryover`, `out_of_manifest_candidate`, `schema_row_integrity`), prints an automated **ACCEPT_H1 / REJECT_H1 / INCONCLUSIVE** verdict from aggregate counts, and emits a **directional scorecard** (alongside binary PASS/FAIL): `named_pc_recall`, `party_boundary_precision` (generic-`group` abstain rows with no party keywords), `candidate_sanity` (gold-pinned `needs_new_hub_candidate: false` rows satisfied).

```bash
# Historical FAIL PC sidecars under artifacts/runs
uv run python -m evals.sentence_routing_retrieval_falsification.h1_routing_evidence scan-artifacts

# One run: violations + scorecard (needs matching scenario gold JSON)
uv run python -m evals.sentence_routing_retrieval_falsification.h1_routing_evidence scorecard \\
  --sidecar evals/sentence_routing_retrieval_falsification/artifacts/runs/<date>/sentence_routing_stage_b_hub_routes--....json \\
  --scenario-json evals/sentence_routing_retrieval_falsification/gold/scenario_c1_session1_pc.json

# After a `route_sentence_units_to_hubs` cohort (--n 5): per-cohort bucket merge, then merge all cohort summaries
uv run python -m evals.sentence_routing_retrieval_falsification.h1_routing_evidence summarize-cohort \\
  evals/sentence_routing_retrieval_falsification/artifacts/runs/<date>/sentence_routing_stage_b_cohort_summary--<model>--N5--....json

uv run python -m evals.sentence_routing_retrieval_falsification.h1_routing_evidence aggregate-summaries \\
  path/to/cohort1.json path/to/cohort2.json path/to/cohort3.json path/to/cohort4.json

# Matrix v2.1 threshold check (uses artifacts/h1_thresholds_v2_1.json by default)
uv run python -m evals.sentence_routing_retrieval_falsification.h1_routing_evidence check-thresholds
```

## Known limitations (v0 capture)

Sentence splitting uses a simple regex; abbreviations and dialogue punctuation can misfire. The suite is designed to be **falsifiable**: tighten rules or replace with a tokenizer once failure buckets justify it.