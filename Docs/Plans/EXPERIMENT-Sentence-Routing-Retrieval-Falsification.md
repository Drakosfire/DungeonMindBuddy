# EXPERIMENT — Sentence Routing and Retrieval Falsification Suite

**Date:** 2026-04-24  
**Status:** Proposed benchmark plan  
**Purpose:** Falsify (or validate) the premise that sentence-grounded canonical memory + hub routing yields fast, relevant planning context.

**Detailed execution roadmap (Stages B–D):** `Docs/Plans/PLAN-Sentence-Routing-Stages-B-through-D.md`

---

## 1. Hypothesis

Given recap corpus markdown, we can:

1. deterministically capture sentence/claim units with verifiable source anchors,
2. route those units to existing hubs with reliable multi-label attribution,
3. propose new hubs only for unresolved units,
4. retrieve compact, relevant, grounded context for planning/tool turns.

If any link in this chain fails under realistic scenarios, the architecture premise is false or incomplete.

---

## 2. Scope

This suite evaluates four stages separately:

- **Stage A:** Capture (deterministic)
- **Stage B:** Hub routing (LLM)
- **Stage C:** New-hub proposal (LLM)
- **Stage D:** Retrieval assembly for planning context (deterministic + optional LLM ranker)

Projection prose quality (timeline/dossier writing style) is out of scope for this suite.

---

## 3. Why Falsification (Not Just Pass Rates)

Pass-rate-only reporting can hide structural failures.  
This suite explicitly tests failure modes:

- over-routing (everything maps everywhere),
- under-routing (important units left unresolved),
- relevance collapse (out-of-scope hubs pollute context),
- anchor drift (citations no longer verify),
- cost blow-up with corpus growth.

---

## 4. Gold Bundle Shape

Each scenario should include:

1. `input`:
   - recap path(s),
   - campaign/session scope,
   - known hub manifest (slug + path + class).
2. `gold_capture`:
   - expected sentence-unit count range,
   - required anchor verification outcomes.
3. `gold_routing`:
   - must-route examples (`unit_id -> expected_hubs[]`),
   - must-abstain examples.
4. `gold_proposals`:
   - expected new-hub candidates (or explicit none).
5. `gold_retrieval`:
   - scoped planning queries,
   - must-include entities/hubs,
   - must-exclude entities/hubs,
   - max context size budget.

---

## 5. Gates

Gate IDs (**A**–**D**) align with pipeline stages: **A** = deterministic capture harness, **B** = hub routing harness, **C** = new-hub proposals harness, **D** = scoped retrieval / context-pack harness.

### 5.1 Gate set A — deterministic sentence capture (Stage A harness; hard)

- **A1:** sentence/claim split deterministic under replay.
- **A2:** every unit has valid source anchor fields.
- **A3:** anchor hash verifies against current corpus bytes.
- **A4:** no whole-file placeholder anchors for multi-line sources.

### 5.2 Gate set B — hub routing (Stage B harness; hard + soft)

- **B1 (hard):** must-route units include all required hubs.
- **B2 (hard):** must-abstain units do not force confident false routes.
- **B3 (soft):** multi-label precision/recall by hub class.
- **B4 (soft):** unresolved rate within envelope.

### 5.3 Gate set C — new-hub proposals (Stage C harness; hard + soft)

- **C1 (hard):** no proposal collisions with existing canonical slugs/paths.
- **C2 (hard):** proposal schema/pathing valid for corpus conventions.
- **C3 (soft):** reviewer acceptance rate of proposals.

### 5.4 Gate set D — retrieval fit / context pack (Stage D harness; hard)

- **D1:** scoped query excludes confident out-of-scope hubs.
- **D2:** scoped query includes required in-scope hubs/evidence.
- **D3:** context pack remains under budget (token and unit count caps).
- **D4:** every returned claim is traceable to verified anchors.

---

## 6. Metrics

Required per-run metrics:

- `capture.anchor_verify_rate`
- `routing.must_route_pass_rate`
- `routing.must_abstain_pass_rate`
- `routing.unresolved_rate`
- `proposal.collision_count`
- `proposal.acceptance_rate`
- `retrieval.scope_precision`
- `retrieval.scope_recall`
- `retrieval.context_tokens`
- `scenario_estimated_cost_usd`

Required cohort metrics:

- pass counts per gate,
- unresolved-rate distribution,
- context-size distribution,
- cost `{min, mean, max, sum}`.

---

## 7. Cost Policy

Cost is a first-class signal.

- Report cost in every run/cohort output.
- Flag regression if cohort sum or per-run cost exceeds 1.5x prior baseline.
- If cost doubles without quality gain, treat as a blocker for promotion.

---

## 8. Minimal Scenario Set (v1)

1. **Clean known-hub recap**
   - Mostly existing PCs/NPCs/locations; low unresolved expected.
2. **Mixed recap with novel named entity**
   - Forces Stage C proposal behavior.
3. **Scope-conflict query set**
   - Same corpus, different scoped questions; validates D1/D2.
4. **Alias-heavy recap**
   - Tests routing stability under name variants.
5. **Cross-session callback recap**
   - Tests retrieval relevance under temporal references.

---

## 9. Promotion Rule

Do not promote architecture confidence from one aggregated pass rate.

Promotion requires:

1. all hard gates passing on target scenario set,
2. unresolved/proposal metrics within documented envelope,
3. retrieval precision/recall meeting thresholds,
4. cost within envelope vs prior cohort.

If hard gates pass but retrieval-fit fails, architecture is not promotion-ready.

---

## 10. Open Questions

1. Sentence-only units vs sentence-plus-neighbor windows as canonical unit.
2. Document-level vs evidence-level scope gating defaults.
3. Whether routing rationales are required for all assignments or only low confidence.
4. Registry write policy for accepted new-hub proposals (manual vs guarded auto-apply).

---

## 11. Implementation Notes (First Cut)

**Naming:** stage-first in prose; historical **module filenames** stay `step1_*` / `step2_*` for stable `python -m` entrypoints. **Artifact filenames** use explicit `sentence_routing_stage_*` prefixes (see `PLAN-Sentence-Routing-Stages-B-through-D.md` §3).

**Stage A — deterministic sentence capture (shipped):** capture + grader + CLI + pytest.

- Suite root: `evals/sentence_routing_retrieval_falsification/`
- Capture logic: `capture.py`
- Graders: `grader.py` (`collect_stage_a_violations`, `collect_stage_b_violations`; Stages C–D still stubbed)
- **Stage A runner (CLI):** `step1_capture_run.py` → `python -m evals.sentence_routing_retrieval_falsification.step1_capture_run`
- **Stage B runner (CLI):** `step2_route_run.py` → `python -m evals.sentence_routing_retrieval_falsification.step2_route_run` (add ``--n 3`` for a cohort; writes ``sentence_routing_stage_b_cohort_summary--*.{json,md}`` when N>1).
- Gold: `gold/scenario_mini.json` + `fixtures/mini_recap.md`; real-recap scaffold: `gold/scenario_real_recap_template.json` (uses ``gold_routing.match`` per DESIGN §6.5).
- Tests: `tests/test_sentence_routing_capture.py`, `tests/test_sentence_routing_stage_b_grader.py`
- Artifacts: dated files `artifacts/runs/<YYYY-MM-DD>/sentence_routing_stage_a_capture--*.json` and mirror `artifacts/last_sentence_routing_stage_a_capture.json`; Stage B writes `sentence_routing_stage_b_hub_routes--*.json` and `artifacts/last_sentence_routing_stage_b_hub_routes.json`. **Cohort (N>1):** also `sentence_routing_stage_b_cohort_summary--<model>--N<n>--*.{json,md}` (paths echoed on stderr). All under `artifacts/` gitignore rules.

**Next implementation tranche:**

1. Finish **Stage B** live-LLM path tuning if needed; keep `gold_routing` + `--no-llm` fixture discipline.
2. Add **Stage C** proposal gold (`gold_proposals`) and **`step3_propose_run.py`** (new-hub proposals runner) for unresolved units only.
3. Add **Stage D** retrieval gold (`gold_retrieval`) and **`step4_retrieval_pack_run.py`** (scoped context-pack runner) with deterministic builder + gates from `Docs/Plans/HANDOFF-relevance-gated-retrieval-and-pruning.md`.
4. Emit **one sidecar per stage** so failures never blur across stages.

---

## 12. Exit criteria (when this experiment doc is “landed”)

This experiment is considered **landed** when:

1. The suite directory exists with **runnable harness entrypoints** (`python -m evals.sentence_routing_retrieval_falsification.*`) and gold fixtures,
2. At least one **3-run cohort report** is written with all metrics in §6,
3. A **promotion decision** is recorded with explicit pass/fail rationale.
