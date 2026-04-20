# DungeonMindBuddy — Backlog

Project-specific learnings, ideas, and follow-ups for the DungeonMindBuddy repo and the Eldyrwild corpus it serves. Cross-project / AI-tooling items live in `~/.cursor/learnings/Backlog.md` instead.

**Format:** see `~/.cursor/skills/capture-learning/SKILL.md`.
**Status legend:** `IDEA` → `READY` → `DOING` → `DONE` / `DROPPED`.

Sort newest → oldest within each status; promote with `/promote`.

---

## [READY] Extraction Lab — pipeline contract field-name drift vs Section 9 — captured 2026-04-19
**Context:** Top-to-bottom audit (this conversation). `Docs/Plans/HANDOFF-extraction-lab-design-from-retrieval-lab-learnings.md` §9.1 names a single `corpus_sha256` field. The shipped implementation uses **`store_sha256`** (hash of serialized entities+facts) plus an optional **`corpus_source_sha256`** (from `ingest_index.json` or a passed `--corpus-source-root`). Older runs on disk under `out/extraction_lab/real_smoke_*` only have `corpus_sha256`, so manifests across the dated run dirs do not share a schema.
**Insight:** This is real spec drift — the lab actually distinguishes "store hash" from "source-corpus hash" (which is the better factoring) but the handoff still claims one field. Either rename in code or update §9.1 to lock in both fields.
**Action:** Either (a) update §9.1 to `store_sha256` + optional `corpus_source_sha256` and add a one-line "what each answers" note, or (b) rename `store_sha256` → `corpus_sha256` and absorb `corpus_source_sha256` as the canonical optional field. Then run a single fresh extraction_lab run and confirm the new contract round-trips through `contracts_equal`.
**Surfaces when:** Any Extraction Lab work; introducing a new contract field; debugging a regression that turns out to be store vs corpus drift.
**Refs:** `extraction_lab/pipeline_contract.py` (`compute_pipeline_contract`), `extraction_lab/run_extraction_lab.py:16-19`, `Docs/Plans/HANDOFF-extraction-lab-design-from-retrieval-lab-learnings.md` §9.1.

## [DONE] Extraction Lab — `assert_regression` only enforces `core_extraction` surface — captured 2026-04-19, completed 2026-04-19
**Context:** `regression_thresholds.json` defines thresholds for `core_extraction`, `vertical_slice`, `recap_lane`, `working_set`, but `extraction_lab/assert_regression.py:48-81` only reads `core_extraction`. The other surfaces are accepted silently. Combined with the observed-on-disk pattern of `aggregate_metrics.json` carrying `entity_anchor_recall: 0.0` and `unresolved_core_anchors: 23` *passing* (no baseline → `no_baseline_for_surface`), the regression layer can rubber-stamp a fully-failing run.
**Insight:** Three of the four surface-specific threshold tables are dead config. The "no baseline" branch can also paper over a green-from-zero run (current vs baseline both at 0 recall = 0% drop = pass).
**Action:** (a) Implement the `vertical_slice` / `recap_lane` / `working_set` branches in `evaluate_regression`. (b) Add an absolute-floor check (e.g. `entity_anchor_recall >= 0.5` or "raise unless every anchor has been resolved at least once historically") so a baseline of 0 doesn't mask a still-failing surface. (c) Add tests for each new branch alongside `tests/extraction_lab/test_assert_regression.py`.
**Surfaces when:** Extending the lab to a new surface; investigating why a regression "passed" with low recall; promoting a baseline from a real-corpus run.
**Refs:** `extraction_lab/assert_regression.py:34-81`, `extraction_lab/regression_thresholds.json`, `out/extraction_lab/handoff_validate_smoke_2/regression_result.json`.

## [READY] Extraction Lab — `contracts_equal` is unused; no drift_report.json — captured 2026-04-19
**Context:** §9.1 defines a contract-equal regression rule: if two runs share an identical pipeline contract you compare metrics directly; if they don't, you emit a `drift_report.json` and skip hard regression. `contracts_equal()` exists in `extraction_lab/pipeline_contract.py:73-85` but is never called from `assert_regression.py` or `run_extraction_lab.py`, and no `drift_report.json` is ever written.
**Insight:** Without this check, a model swap or prompt change can silently masquerade as a metric regression and waste an investigation. The function is one import away from the only place it matters.
**Action:** In `assert_regression.evaluate_regression`, load the baseline's `pipeline_contract.json`, compare to the current contract via `contracts_equal`, and either (i) downgrade hard fails to warnings + write `drift_report.json`, or (ii) refuse to evaluate and exit with a clear "contract changed; promote a fresh baseline" message. Add a test that flips one contract field and asserts the new behavior.
**Surfaces when:** Promoting a baseline; bumping `entity_extractor` / `fact_extractor` prompt IDs; changing the taxonomy.
**Refs:** `extraction_lab/pipeline_contract.py:73-85`, `extraction_lab/assert_regression.py`, handoff §9.1.

## [DONE] Recap-ingest grader — `commit_outcome=unknown` is a soft pass — captured 2026-04-19, completed 2026-04-19
**Context:** `evals/session_recap_ingest_vertical_slice/scope_b_grader.py:343-368` correctly hard-fails when the *last* commit response parses as `ok=false`, but emits only a soft observation when the response is unparseable (`succeeded is None`). With `commit_required=true` set by the scenario, an unparseable last-commit response can still produce `gates_passed=True`.
**Insight:** This is a smaller version of the original "grader doesn't notice the protocol caught it" hole — instead of treating the absence of a parseable success as failure, we treat absence of evidence as evidence of OK.
**Action:** When `commit_required=true` and `_commit_outcome["succeeded"] is None`, escalate to a hard violation (or at minimum a separate `gates_passed_unverified` bit so cohort summaries can stratify). Add a unit test feeding a truncated `output_excerpt` through the grader and asserting `gates_passed=False`.
**Surfaces when:** Adding a new Scope-B scenario; debugging a flaky cohort run; tightening the writer protocol; whenever someone proposes a "chaos" Scope-B scenario whose expected outcome is `refused`.
**Refs:** `evals/session_recap_ingest_vertical_slice/scope_b_grader.py:343-368`, `Docs/Plans/STATUS-Session-Recap-Ingest-Benchmark.md` (C2 row).

## [READY] Recap-ingest — `step2_grade_against_gold.py` is a stub; STATUS doc claims grader supersession — captured 2026-04-19
**Context:** `evals/session_recap_ingest_vertical_slice/step2_grade_against_gold.py` is a placeholder ("Grader not wired"). The STATUS ledger and EXPERIMENT doc both reference grading via `scope_b_grader.py`. Anyone reading the slice top-down will hit the stub and assume there is a second grading path that doesn't exist.
**Action:** Delete `step2_grade_against_gold.py` (or rename to `step2_grade_against_gold.deprecated.py` with a one-line "see scope_b_grader.py" pointer). Same pass: review `step3_unsure_queue_grading.py` (standalone, not wired into pass/fail) and decide whether to wire it or label it explicitly experimental in the README.
**Surfaces when:** Onboarding to the recap-ingest slice; cleaning the evals tree; deciding whether B7 (unsure_queue) becomes a hard gate.
**Refs:** `evals/session_recap_ingest_vertical_slice/step2_grade_against_gold.py`, `evals/session_recap_ingest_vertical_slice/step3_unsure_queue_grading.py`, `Docs/Plans/STATUS-Session-Recap-Ingest-Benchmark.md`.

## [READY] OpenAI client — collapse three `_load_api_key` copies and stop passing `api_key=` — captured 2026-04-19
**Context:** `src/agent/synthesis.py:153-165`, `src/agent/document_planner.py:139-147`, and `src/agent/query_planner.py:220-228` each implement a `_load_api_key` that loads only `.env.development` (two paths) — they don't match the canonical `bootstrap_env.load_dungeonmindbuddy_dotenv` order (`.env` → `.env.development` → parent). Many call sites then construct `OpenAI(api_key=api_key)` despite the rule in `.cursor/rules/dungeonbuddy-environment.mdc` that says env-only.
**Insight:** This is the same anti-pattern in three places. Fixing it once removes a class of "key loaded from wrong file" bugs and aligns library code with the CLI/test-conftest behavior.
**Action:** Make every `_load_api_key` site call `load_dungeonmindbuddy_dotenv()` first (or import from a single shared helper), and replace `OpenAI(api_key=api_key)` with bare `OpenAI()` everywhere except where the `DungeonMindApiClient.wrap` boundary already covers it. Update the env-loading rule to say "if you find yourself writing `_load_api_key`, you're already wrong — call `load_dungeonmindbuddy_dotenv()`."
**Surfaces when:** Any new entrypoint that talks to OpenAI; any debugging of "key not found"; touching `synthesis.py` / `document_planner.py` / `query_planner.py` / `wiki_compiler.py` / `entity_extractor.py` / `fact_extractor.py`.
**Refs:** `src/agent/synthesis.py:153-165`, `src/agent/document_planner.py:139-147`, `src/agent/query_planner.py:220-228`, `src/bootstrap_env.py:16-30`, `.cursor/rules/dungeonbuddy-environment.mdc`.

## [DONE] `src/agent/query_planner.py` is dead code (test-only) — captured 2026-04-19, completed 2026-04-19
**Context:** Repo-wide grep shows `query_planner` imported only by `tests/test_query_planner.py`. `src/cli.py` does not reference it; the live ask path goes retriever → `document_planner` → synthesis. The module's own docstring still describes it as "between retriever and synthesis."
**Insight:** This is dead surface that also passes tests, which is the worst flavor — we maintain it forever without running it. It also re-implements `_load_api_key`, MODEL_POLICY resolution, and `_normalize_attribute` (which silently fuzzy-repairs typos — explicitly the kind of silent disambiguation we said we don't want).
**Action:** Decide: ship it (wire behind a CLI flag and add a smoke test in `tests/test_cli.py`) or delete it (and its tests). Default recommendation: **delete** — re-add later if you actually need entity LLM-triage between retrieval and synthesis.
**Surfaces when:** Designing the ask pipeline; touching `document_planner` or `evidence_retriever`; reviewing the `src/agent/` surface for cruft.
**Refs:** `src/agent/query_planner.py`, `tests/test_query_planner.py`, `src/cli.py`.

## [READY] Evals artifact bloat — `npc_voice` and `session_recap_ingest` track run dirs in git — captured 2026-04-19
**Context:** `evals/lysandra_vertical_slice/artifacts/.gitignore` correctly hides `runs/` and `last_planner_step1_run.md`. The same is **not** true under `evals/npc_voice_vertical_slice/artifacts/runs/2026-04-16/`, `2026-04-17/`, or `evals/session_recap_ingest_vertical_slice/artifacts/runs/2026-04-2*/` — those are versioned and visible in `git status` already.
**Insight:** Each cohort run leaks 5–20 MD/JSON files into git. This is what is making `git status` long after every benchmark run and what will eventually make `git log -p` unwieldy.
**Action:** Add a slice-level `.gitignore` to `npc_voice_vertical_slice/artifacts/` and `session_recap_ingest_vertical_slice/artifacts/` mirroring Lysandra's: ignore `runs/`, optionally keep `last_*` mirrors. Then `git rm --cached -r` the existing run dirs in a focused commit so future cohorts don't show up as untracked noise.
**Surfaces when:** Any cohort run; reviewing `git status` after benchmarking; setting up a new vertical slice.
**Refs:** `evals/lysandra_vertical_slice/artifacts/.gitignore` (good template), `evals/npc_voice_vertical_slice/artifacts/runs/`, `evals/session_recap_ingest_vertical_slice/artifacts/runs/`.

## [IDEA] Hoist a shared `evals/reporting/` module — captured 2026-04-19
**Context:** Per-run+cohort report writers exist independently in `evals/planner_slice/live_report.py`, `evals/session_recap_ingest_vertical_slice/recap_ingest_run_report.py`, `evals/npc_voice_vertical_slice/npc_voice_planner_trace.write_npc_voice_suite_report`, `evals/llm_ingestion_slice/`, and `evals/canon_layering/run_benchmarks.py`. Each duplicates the "write JSON sidecar + MD with header + cohort rollup" pattern.
**Action:** Lift a tiny helper (timestamped filename, header block with `corpus_fprint`/`model_id`/`gates_passed`, JSON+MD pair, cohort min/mean/max/sum). Don't refactor existing call sites in one go — adopt module-by-module as new slices land.
**Surfaces when:** Adding a new vertical slice; touching any per-run report writer; the next time someone copies a report writer.
**Refs:** the report writers above.

## [IDEA] Hoist a shared `evals/common/step0_corpus_environment.py` — captured 2026-04-19
**Context:** `evals/lysandra_vertical_slice/step0_corpus_environment.py` is the de facto helper imported by NPC voice and recap Step 1. `evals/session_recap_ingest_vertical_slice/step0_corpus_environment.py` is a duplicate that nothing imports.
**Action:** Move the canonical helper into `evals/common/` (or `evals/__init__.py` exports), update the two consumers, delete the unused duplicate.
**Surfaces when:** Adding a new slice that needs corpus-root resolution; cleaning the recap-ingest slice (above).

## [IDEA] Top-level evals/ HANDOFF cleanup — captured 2026-04-19
**Context:** `evals/HANDOFF-phase1-…` through `HANDOFF-phase8-openai-batch-api.md`, `MODEL_AB_COMPARISON.md`, `AUTO_ESCALATION_FULL_CORPUS_REPORT.md`, and `HANDOFF-commit-and-model-ab.md` describe completed work. Active playbooks: `HANDOFF-e2e-smoke-and-quality-validation.md`, `HANDOFF-next-agent-ingestion-temporal-gates.md`. Mixed: `HANDOFF-gold-scoring-eval.md` (some sections still open), `HANDOFF-taxonomy-rework.md` (Phases A–C done, follow-ups linger).
**Action:** Move the eight phase HANDOFFs + `MODEL_AB_COMPARISON.md` + `AUTO_ESCALATION_FULL_CORPUS_REPORT.md` + `HANDOFF-commit-and-model-ab.md` into `Docs/Plans/archive/` with a one-line README pointer. Leave the active two in place.
**Surfaces when:** Onboarding to the evals tree; cleaning Docs/Plans/.
**Refs:** `evals/HANDOFF-phase*.md`, `Docs/Plans/archive/`.

---

## [READY] Roll-lookup as `grep`, not LLM call — captured 2026-04-18
**Context:** Live-play workflow analysis (Session 21 prep). The user typed *"Tell me what 28 on the traveling d100"* (transcript line 4765) — a deterministic line-of-file fetch that went through the full LLM round-trip.
**Insight:** Every die-result lookup against a corpus markdown table is `read line N of file F`. Zero model needed. The current behavior burns latency and tokens for a `sed -n '28p'`-equivalent operation.
**Action:** Add a `/roll <table-name-or-path> <n>` shortcut (skill or hook) that grep/reads the matching row from `Elderwyld/Roads/*.md`, `Elderwyld/Wilderness/*.md`, etc., and returns the row text plus the file:line ref. No LLM call.
**Surfaces when:** Building any d100/d20 table the user will roll on at the table; designing live-play tooling; corpus-search shortcuts.
**Refs:** `canvases/live-play-workflow-analysis.canvas.tsx` (DungeonMindBuddy canvas), corpus files under `corpus/eldyrwild-markdown/Elderwyld/Roads/` and `Elderwyld/Wilderness/`

## [IDEA] Mirathorn — what is happening while the party is away? — captured 2026-04-18
**Context:** Closing aside in the live-play workflow analysis: *"The question of what is happening in Mirathorn is one I need to think more about and have very clear ideas about."* This is the canonical example of a side-thought that needed a parking lot.
**Insight:** The party is multi-day-travel out from Mirathorn, but the city has multiple live threads (tainted jerky / supply chain, Sara's *"who can I trust"* wobble, Tealeaf line still hanging, Lysandra reunion, Dustwalker decoy fallout, curfew council, Stormbark Tea / Mossford handoff). Without a clear authored state, the city goes flat the moment the party turns around.
**Action:** Author a `Longmont Campaign/Campaign 2/Mirathorn — While You Were Away.md` doc that timelines what happens in the city across the party's travel days. Pull from the existing threads in `Elderwyld_Narrative_Ledger_Campaign2.md` and the Sara / Lysandra dossiers. Result should answer: *"if the party scries / sends / asks Sara on the rockie-talkie at any point during the journey, what truthful state can the GM relay?"*
**Surfaces when:** Prepping any session where a Mirathorn check-in is plausible; party uses a rockie-talkie; party reaches Mossford or further; building the swamp-arc bridge.
**Refs:** `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Elderwyld_Narrative_Ledger_Campaign2.md`, `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/NPCs/sara_mirathorn_operator/`, `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/`, `canvases/live-play-workflow-analysis.canvas.tsx`
