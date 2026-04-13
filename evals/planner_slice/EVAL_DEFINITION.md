# Planner evaluation — formal definition

This document defines what “evaluation” means for the corpus-grounded planner (`plan` / `run_planning_turn`). It is distinct from **harness tests** (scripted `responses.create` returns) which only prove wiring and fail-loud mechanics.

## What an evaluation is

An evaluation is a **repeatable trial** with:

1. **Prebuilt input** — Either a full `input.user_message`, or an **on-disk prior session** plus `input.planning_ask` (see fixture schema). Stored in JSON fixtures under `live_fixtures/`.
2. **Expected actions** — Predicates on what the **real model** should do, checked **after each model response** (each OpenAI `responses.create` result). Examples: “this step includes a `read_corpus_file` whose `path` contains `Migrating Forest`”, “later step calls `generate_statblock`”.
3. **Expected outputs** — Predicates on the **final** assistant-visible text and/or the accumulated **tool trace** (e.g. final answer mentions `Witness Seed`, statblock tool was invoked, minimum length).

Evaluations run against a **real model** (live API). Scripted fake responses are **not** evaluations; they are regression harnesses for the loop and dispatcher (see `tests/test_planner_eval_scenarios.py` + `evals/planner_slice/fixtures/`).

## Steps vs trace

- **Step** — One model response in order: the `output` of a single `responses.create` (may include `function_call` items, optional `message` / `output_text`, or both). Recorded as `PlanningModelStepRecord` in code.
- **Tool trace** — Ordered list of executed tools with arguments and output excerpts (`run_planning_turn_detailed`).

Step checks are indexed by step order (`steps[0]` = first model response after the user line). Optional steps allow the model to finish early without failing the scenario.

## Gates

A **gate** is an aggregate threshold for a **suite** of evaluation scenarios (not a single scenario):

- `**PLANNER_EVAL_MIN_PASS_RATE`** — Minimum fraction of scenarios in the live suite that must pass (default `1.0`). Example: `0.8` allows 20% flaky/regression tolerance across many scenarios.

A scenario **passes** only if:

- Every **non-optional** step expectation passes for its corresponding step index, and  
- **Final** expectations pass, and  
- `hit_tool_round_limit` is false.

Failures must be **explicit** (assertion messages include scenario id and predicate).

## Enabling live runs

Live evaluations are **opt-in** (cost + latency + nondeterminism):

- Set `**PLANNER_LIVE_EVAL=1`**
- Ensure `**OPENAI_API_KEY**` is available in `.env` / `.env.development` (pytest loads via `tests/conftest.py` → `src.bootstrap_env.load_dungeonmindbuddy_dotenv()`) or in the process environment
- Default planner model id resolves from `MODEL_POLICY.json` on the planner search path (action `corpus_session_planner` → role such as `fast_smart_mini` → `gpt-5.4-mini`). Override by passing an explicit model into `run_planning_session` / your harness if supported.

Run:

```bash
PLANNER_LIVE_EVAL=1 PLANNER_EVAL_MIN_PASS_RATE=1.0 uv run pytest tests/test_planner_eval_live.py -v
```

Run a **single** live scenario by id (avoids loading every `live_fixtures/*.json` in one API suite):

```bash
PLANNER_LIVE_EVAL=1 PLANNER_LIVE_SCENARIO_ID=live_mirathorn_main_gate_detail uv run pytest tests/test_planner_eval_live.py::test_planner_live_suite_meets_gate -v --log-cli-level=INFO
```

Write Markdown reports (human-readable step log + full final answer) to a directory:

```bash
mkdir -p out/planner_live_reports/run1
PLANNER_LIVE_EVAL=1 PLANNER_LIVE_REPORT_DIR=out/planner_live_reports/run1 \
  PLANNER_LIVE_SCENARIO_ID=live_mirathorn_main_gate_detail \
  uv run pytest tests/test_planner_eval_live.py::test_planner_live_suite_meets_gate -v
```

## Logging and telemetry

Each OpenAI `responses.create` in the planner loop is logged at **INFO** on logger `dmb.planner` as a single JSON line prefixed with `[dmb.planner.telemetry]`. Fields include:

- **event** — `request`  `response`  `turn_complete` (and statblock fallback: same pattern under `op: statblock_via_responses`).
- **latency_ms** — wall time for that HTTP round-trip.
- **usage** — `input_tokens`, `output_tokens`, `total_tokens`, `cached_tokens` (from the Responses usage object).
- **response_id**, **model**, **output_text** (preview unless full I/O is enabled).
- **extras** — safe subset of response metadata (e.g. `status`, `output_item_types`).
- **turn_complete** — `usage_totals` (sum over rounds), `latency_ms_by_round`, `hit_tool_round_limit`, `final_text_chars`, plus **estimated USD** (`planner_estimated_cost_usd`, per-round `planner_cost_by_round_usd`, and cost split fields). Statblock-only `responses.create` logs the same cost fields on its `response` event (`op: statblock_via_responses`).
- **Pricing source** — `src/agent/planner_pricing.py` (aligned with `tools/batch_ingest_corpus.py`): uncached input, cached input, and output tokens priced per 1M. Figures are **approximate** until reconciled with billing.
- **Suite / scenario totals** — `dmb.planner.live_eval` logs `estimated_cost_usd` on `scenario_end` (planner + statblock tool) and `suite_estimated_cost_usd` on `suite_end`. `LiveEvalResult.estimated_cost_usd` holds the scenario total for future cost gates.

Suite-level lines use logger `dmb.planner.live_eval` (`scenario_start` / `scenario_end` / `suite_start` / `suite_end`). On failure, `scenario_end` is logged at **WARNING** with full **violations** and a **final_text_preview**.

**Environment**


| Variable                   | Effect                                                                                                                                                                                                      |
| -------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `PLANNER_LOG_FULL_IO`      | If `1` / `true` / `yes`, log full user line, assistant `output_text`, and tool output bodies (still capped at ~200k chars per field).                                                                       |
| `PLANNER_LIVE_SCENARIO_ID` | Exact fixture `id`; `run_live_suite` runs only that JSON file.                                                                                                                                              |
| `PLANNER_LIVE_REPORT_DIR`  | Directory path: after each scenario, write a readable **Markdown** report (`{scenario_id}.md`) with step-by-step tool timeline and **full final assistant output**; suite run also writes `SUITE_INDEX.md`. |


### Answer benchmark — response accuracy rig (citations + concepts)

When `PLANNER_LIVE_REPORT_DIR` is set, scenarios that appear in `evals/planner_slice/benchmark/manifest.json` also get (currently: `live_festival_aspitome_ceremony_detail`, `live_festival_tindlewix_illusionist_detail`, `live_mirathorn_main_gate_detail`, `live_migrating_forest_branchbound_plan`):

- A **Benchmark instrumentation** section at the end of the Markdown report: **citation grounding** (reads vs citations in the final answer), **concept coverage** (weighted phrase scores), legacy **substring keyword** hit/miss (for comparison), plus declared thresholds from the manifest.
- A machine-readable sidecar: `{scenario_id}_benchmark.json` in the same report directory.

**Pass/fail authority:** Citation correctness for the live suite is the fixture predicates `cited_paths_must_match_reads` and `min_cited_markdown_paths` (see above). **Which files were read** is authoritative from `tool_trace`; Markdown reports append **Corpus files retrieved (`read_corpus_file`)** after the final answer so the model does not need to repeat every path in prose. Benchmark JSON **replays the same citation facts** for dashboards; it does not replace those gates. In `citation_grounding`, `reads` / `read_count` / `reads_not_mentioned_in_final` use **deduplicated** `read_corpus_file` paths; `reads_not_mentioned_in_final` is **diagnostic** (paths opened but not echoed in the assistant reply), not a default pass/fail gate.

**Signals:** Primary continuous signal is **`concept_coverage.weighted_score`** (token bag + proximity window + exact phrase, stopword-stripped). Primary binary signals are the **live citation gates**. Optional embedding cosine is **diagnostic only** (often saturated for planner-style prose); same stack as `evals/mirathorn_vertical_slice/embedding_scorer.py`.

**Manifest** (`evals/planner_slice/benchmark/manifest.json` per scenario):

- `critical_keywords` — drives legacy substring `keyword_coverage` and, unless overridden, the list of phrases for `concept_coverage` (each weight `1.0`).
- `concept_checks` (optional) — list of `{ "phrase": "...", "weight": 1.0 }`; when non-empty, **only** these phrases are used for `concept_coverage` (useful to drop noisy legacy strings without deleting `critical_keywords` yet).
- `min_weighted_concept_score` (optional) — reserved for a future gate; telemetry only today.

### How to judge quality from a benchmark run (not “did we pass?”)

Benchmark JSON and the Markdown **Quality summary** section are for **comparing runs** and **grading answer shape**, not for replacing live-eval gates.

| Dimension | What it tells you | Pitfalls |
| --------- | ----------------- | -------- |
| **Citation alignment** (`quality_summary.citation_alignment`) | **Aligned** when there are no hallucinated citations (cites in prose not opened this turn). Count of reads not echoed in prose is diagnostic only. | If `tool_trace` was not passed into instrumentation, this block is vacuous. |
| **Exemplar concepts** (`concept_coverage` / `quality_summary.exemplar_concepts`) | Density of manifest phrases in the answer (token bag + proximity + exact phrase). | Short tokens can collide (e.g. “mage” + “hand”); use `per_phrase` and optional `concept_checks` weights. |
| **Legacy substring keywords** | Old contiguous-string bar; good for historical comparison. | Systematically low vs concepts when the model uses bullets or line breaks. |
| **Embedding cosine** | Optional drift / sanity check vs gold exemplar text. | Often **saturated** for planner-style prose; do not use alone to infer correctness. |

Treat **`quality_summary.notes`** as heuristic flags (substring vs concept gap, high cosine + low concepts, many phrases below 0.5), not as a verdict.

| Variable                  | Effect                                                                                                                                                                                                 |
| ------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `PLANNER_BENCHMARK_EMBED` | If `1` / `true` / `yes`, load SentenceTransformers and append embedding diagnostics (cosine between full exemplar and full model answer). Omit or leave unset to skip model load in CI and quick runs. |


**Pytest:** telemetry only appears if log capture shows INFO, for example:

```bash
PLANNER_LIVE_EVAL=1 uv run pytest tests/test_planner_eval_live.py -v --log-cli-level=INFO
```

## Fixture schema (version 1)

See `live_fixtures/*.json`. Top-level fields:


| Field                        | Meaning                                                                                                                                                                                                                      |
| ---------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `id`                         | Stable scenario id (used in failure messages).                                                                                                                                                                               |
| `version`                    | Schema version (`1`).                                                                                                                                                                                                        |
| `input.user_message`         | If non-empty: full user prompt for one turn (ignores `planning_ask` / `prior_session_path`).                                                                                                                                 |
| `input.prior_session_path`   | Optional when `user_message` is empty: corpus-relative path to a markdown session/recap file (POSIX, no `..`).                                                                                                               |
| `input.planning_ask`         | When `user_message` is empty: explicit planning instructions; combined with prior file body if `prior_session_path` is set. If both `planning_ask` and `planning_goal` are set, `planning_ask` wins.                         |
| `input.planning_goal`        | When `user_message` and `planning_ask` are empty: a **high-level outcome** only. The harness appends a short **autonomous planning** block so the model must choose corpus reads and `##` section structure itself (Gate 3). |
| `PLANNER_PRIOR_SESSION_PATH` | Optional env: overrides `prior_session_path` from the fixture so you can point at a recap without editing JSON.                                                                                                              |
| `PLANNER_LIVE_SCENARIO_ID`   | Optional env: when set to a fixture `id` string, `run_live_suite` runs only that scenario’s JSON (others skipped).                                                                                                           |
| `PLANNER_LIVE_REPORT_DIR`    | Optional env: directory for Markdown reports (`{scenario_id}.md` + `SUITE_INDEX.md`).                                                                                                                                        |
| `steps`                      | List of step checks, index-aligned with model responses.                                                                                                                                                                     |
| `steps[].id`                 | Human label for logs.                                                                                                                                                                                                        |
| `steps[].optional`           | If true: if the model stops before this step exists, the step is skipped (pass). If the step exists, `require` still applies.                                                                                                |
| `steps[].require`            | Predicate object (see below). Empty object = no check.                                                                                                                                                                       |
| `final.require`              | Predicates on the whole turn after the last model response.                                                                                                                                                                  |
| `gates`                      | Optional; per-scenario overrides are reserved for future use. Suite gate is env-only for now.                                                                                                                                |


### `require` predicates (step or final)

**Step `require`:**

- `**calls_satisfy`** — List of matchers. Each matcher must be satisfied by **a distinct** `function_call` in **this step’s** `function_calls` list (greedy one-to-one). Matcher fields:
  - `tool` (string, required)
  - `path_contains` (string, optional) — substring match, case-insensitive, on `arguments.path` for `read_corpus_file`
  - `description_min_chars` (int, optional) — for `generate_statblock`, `len(description) >= n`
- `**max_function_calls`** (int, optional) — Fail if more than N tool calls in this step.

**Final `require`:**

- `**output_text_contains_any`** — List of strings; at least one must appear in `final_text` (case-sensitive unless we add flag later).
- `**output_text_contains_all`** — All must appear.
- `**min_output_chars**` — Minimum length of `final_text`.
- `**min_h2_headings**` (int, optional) — **Gate 3 / structure:** at least this many Markdown lines matching top-level `##`  headings (`^\s*##\s+\S`) in `final_text`. Encourages a self-authored multi-section plan instead of one blob paragraph.
- `**tool_trace_must_include_tool`** — One tool name must appear at least once in `tool_trace`.
- `**tool_trace_must_include_tools**` — Every listed tool name must appear at least once (unordered multiset check).
- `**tool_trace_tools_in_order**` — Optional strict subsequence over the full trace (use sparingly; higher flake).
- `**read_corpus_paths_must_include**` — List of substrings; each must appear (case-insensitive) in at least one `read_corpus_file` `path` recorded in `tool_trace`. Use when grounding must not depend on which **step** performed the read.

**Gate 3 — Autonomous plan shape (optional, pairs with `planning_goal`):**

- Prefer `input.planning_goal` when you want the model to **derive** file choice and sectioning (suffix text: `src/prompts/planner_live_eval_user.py` → `AUTONOMOUS_PLANNING_USER_SUFFIX`, appended in `resolve_planner_user_message`), rather than mirroring a long numbered checklist from the prompt.
- Combine with `min_h2_headings` (and existing Gate 2 citation rules) so output is **structured** and **grounded**; retrieved paths are still listed in the report appendix.

**Final citation / grounding (Gate 2):**

- `**cited_paths_must_match_reads`** (bool) — When true, every citation path extracted from `final_text` must correspond to a path actually read via `read_corpus_file` in `tool_trace`. Extraction is anchored on corpus roots `Elderwyld/` or `Longmont Campaign/` (so stray `Forest/foo.md` fragments are ignored); matching allows normalized equality, suffix paths, or same basename.
- `**min_cited_markdown_paths`** (int, optional, default `1`) — Used with `cited_paths_must_match_reads`: require at least this many distinct extracted `.md` citations in the final answer.
- `**read_paths_must_appear_in_final**` (bool, **legacy / optional**) — When true, each **distinct** `read_corpus_file` `path` from `tool_trace` must appear in `final_text` (normalized substring) or its basename must appear. Default live fixtures omit this; prefer the report’s **Corpus files retrieved** list instead of requiring the model to enumerate every read in prose.

## Relationship to DungeonMindServer

Statblock (and other generators) are **real services** elsewhere in the monorepo. Live planner evals today assert **that the model invokes** `generate_statblock` and that narrative output is grounded enough for your bar; they do **not** require the HTTP statblock endpoint until you wire `DUNGEONMIND_STATBLOCK_URL` and extend fixtures to assert on HTTP responses.