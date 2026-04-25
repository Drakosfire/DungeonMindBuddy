# Plan — Sentence routing falsification: Stages B through D

**Date:** 2026-04-25  
**Status:** Planning (execution follows this doc)  
**Depends on:** Stage A (deterministic sentence capture) scaffold in `evals/sentence_routing_retrieval_falsification/`  
**Companion docs:**  
`Docs/Plans/EXPERIMENT-Sentence-Routing-Retrieval-Falsification.md`,  
`Docs/Plans/GUARDRAILS-Sentence-Grounded-Ingestion-Vision.md`,  
`Docs/Design/DESIGN-citation-grounded-corpus-architecture.md`

---

## 0. North star (unchanged)

**Canonical layer:** sentence (or sentence-window) units + verifiable source anchors + hub links.  
**Derived layer:** timeline, dossier prose, relationship summaries — compression lives here, not in capture.

This plan only covers **benchmark + harness** work to falsify the premise: *routing + retrieval are good enough for planning context.*

---

## 1. Stage map (what ships in which order)


| Stage        | Input                                  | Output                                  | LLM?            | Primary falsification question                                |
| ------------ | -------------------------------------- | --------------------------------------- | --------------- | ------------------------------------------------------------- |
| **A** (done) | recap file                             | `sentence_units[]`                      | No              | Can we segment deterministically with stable line provenance? |
| **B**        | `sentence_units[]` + hub manifest      | `routes[]` (multi-label)                | Yes             | Do units land on the right hubs without over-routing?         |
| **C**        | unrouted / low-confidence units        | `hub_proposals[]`                       | Yes             | Are new-hub proposals schema-valid and non-colliding?         |
| **D**        | `routes` + manifest + **scoped query** | `context_pack` (ordered excerpts + ids) | Optional ranker | Is scoped retrieval precise, bounded, and grounded?           |


Stages **B** and **D** are the load-bearing falsification surfaces for your vision. **C** is a safety valve so B does not hallucinate hubs.

---

## 2. Gold and scenario schema (versioned)

Keep `schema: sentence_routing_falsification_v1` until a breaking change forces `v2`.

**Stage B full design (manifest, model JSON, grader, runner):**  
`Docs/Plans/DESIGN-Sentence-Routing-Stage-B-Hub-Routing.md`

### 2.1 `input` (all stages)

- `recap_relative_path` (required)
- `corpus_root` optional override (default: repo root for synthetic; `corpus/eldyrwild-markdown` for real recaps in later scenarios)
- `campaign_id`, `session` (metadata for hub manifest and queries)
- `hub_manifest`: list of `{ slug, path, subject_class }` — **allowlist** for Stage B outputs (prevents free-text hub paths)

### 2.2 `gold_capture` (Stage A — existing)

Unchanged: count window + `must_contain_substrings_anywhere`.

### 2.3 `gold_routing` (Stage B — new)

Two disjoint test families:

1. **Must-route** — list of:
  - `unit_id` **or** `match: { line_start, text_substring }` (prefer `unit_id` once stable)
  - `expected_hubs`: non-empty list of slugs (order-independent compare)
  - optional `max_extra_hubs`: caps over-routing
2. **Must-abstain** — list of:
  - `unit_id` or match
  - `allowed_hubs`: usually `[]` meaning model must output **no** hub assignments, **or** only `unknown` bucket if we add one
3. **Telemetry thresholds** (soft gates, optional in v1):
  - `max_unresolved_fraction`
  - `max_mean_hubs_per_unit`

**Multi-label rule:** gold explicitly lists **all** required hubs for a unit. Grader checks superset: `expected_hubs ⊆ assigned_hubs` plus `max_extra_hubs` if set.

### 2.4 `gold_proposals` (Stage C — new)

Only evaluated for units flagged `needs_new_hub_candidate` or with empty routes after B.

- `expected_proposals_min` / `max`
- optional list of `{ match_text, expected_slug_prefix, subject_class }` for synthetic cases
- **hard:** proposal slug must not collide with `hub_manifest`

### 2.5 `gold_retrieval` (Stage D — new)

Per **scoped query**:

- `query_id`, `query_text`
- `scope`: one of `document_ids` | `recap_only` | `explicit_hub_slugs` (start with `explicit_hub_slugs` + recap path for v1)
- `must_include_hubs`: slugs that must contribute ≥1 unit excerpt to the pack
- `must_exclude_hubs`: slugs that must **not** appear when building the pack from routed units
- `max_context_chars` or `max_units` — hard budget gate

---

## 3. Runners and artifacts (file contract)

All harness entrypoints write **dated JSON** under `evals/sentence_routing_retrieval_falsification/artifacts/runs/<YYYY-MM-DD>/` plus a **last-run mirror** JSON at `artifacts/` (gitignored), per slice convention.

**Vocabulary (explicit):** the repo still uses historical **module filenames** (`step1_*`, `step2_*`) for import stability; in prose, prefer the **stage + action** names below. **Artifact filenames** use the `sentence_routing_stage_*` prefix so runs sort and grep by role.

| Stage | Harness role (what it does) | Python module (`python -m …`) | Reads | Dated artifact prefix | Last-run mirror filename |
| ----- | ---------------------------- | ------------------------------ | ----- | ---------------------- | ------------------------- |
| **A** | Deterministic sentence-unit capture from recap markdown | `evals.sentence_routing_retrieval_falsification.step1_capture_run` | scenario | `sentence_routing_stage_a_capture--…json` | `last_sentence_routing_stage_a_capture.json` |
| **B** | Hub routing (units → manifest slugs) | `evals.sentence_routing_retrieval_falsification.step2_route_run` | scenario + Stage A sidecar **or** re-capture | `sentence_routing_stage_b_hub_routes--…json` | `last_sentence_routing_stage_b_hub_routes.json` |
| **C** | New-hub proposals for unresolved units (planned) | `evals.sentence_routing_retrieval_falsification.step3_propose_run` (TBD) | scenario + Stage B sidecar | `sentence_routing_stage_c_hub_proposals--…json` | `last_sentence_routing_stage_c_hub_proposals.json` |
| **D** | Scoped retrieval context pack (planned) | `evals.sentence_routing_retrieval_falsification.step4_retrieval_pack_run` (TBD) | scenario + Stage B sidecar | `sentence_routing_stage_d_context_pack--…json` | `last_sentence_routing_stage_d_context_pack.json` |

**Cohort (Stage B only today):** when ``step2_route_run --n`` is greater than 1, the harness also emits ``sentence_routing_stage_b_cohort_summary--<model>--N<n>--*.{json,md}`` next to the per-run sidecars (see slice README).

**Chaining:** Stage **B**/**C**/**D** runners accept `--prior-json` pointing at the **previous stage’s sidecar** so you do not re-run earlier LLM stages while iterating. Stage **A** stays a cheap deterministic recompute from the recap path anytime.

---

## 4. Stage B — routing design

### 4.1 Model output shape (strict JSON)

Recommend a Pydantic model in the runner module:

- `routes`: list of `{ unit_id, assigned_hubs: list[str], confidence: float|enum, rationale: str, needs_new_hub_candidate: bool }`

Constraints:

- every `assigned_hubs` entry must be in `hub_manifest.slug`
- `needs_new_hub_candidate` true only if `assigned_hubs` empty or model declares inability to map

### 4.2 Prompt principles

- Pass **only** unit text + line numbers + allowed slug list (no full corpus tree provisioning per llm-context-discovery — manifest is harness-built, not “discover this recap” prose).
- Require abstain rather than false attach when unsure.
- Multi-label: explicitly allowed.

### 4.3 Grader

- Hard: must-route, must-abstain, allowlist membership
- Soft: histogram of hubs-per-unit, unresolved rate

### 4.4 Corpus choice for first B gold

1. **Synthetic v1** (fast, no PII): extend `fixtures/` with a tiny `hub_manifest` embedded in scenario JSON.
2. **Real recap v2** (slower): one pinned recap under `corpus/eldyrwild-markdown/…` with manifest built from **public-safe** hub list only; never paste recap body into docs.

---

## 5. Stage C — new hub proposals

### 5.1 When it runs

Only units with:

- `needs_new_hub_candidate: true`, or
- empty `assigned_hubs` after B, **and** gold says proposals are expected for that unit class

### 5.2 Output shape

`hub_proposals[]`: `{ suggested_slug, subject_class, parent_path_guess, rationale, source_unit_ids[] }`

### 5.3 Grader

- Hard: schema/path/shape vs `Docs/CONVENTION-`* (or slice-local relaxations for synthetic parents)
- Hard: no collision with manifest
- Soft: human review checklist exported to markdown (out of scope for automated v1)

---

## 6. Stage D — retrieval context pack

### 6.0 Existing retrieval benchmarks (reuse, not rewrite)

These already measure **retrieval + context quality** in different layers. None are wired to `sentence_routing_retrieval_falsification` yet; Stage D should **delegate or mirror** them instead of inventing parallel metrics.


| Surface                                 | What it proves                                                                                                                          | Artifacts / entrypoints                                                                                                                                                                                                                               | Best reuse for Stage D                                                                                                                                                                                                                        |
| --------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Mirathorn council-room question set** | End-to-end **evidence → retriever → synthesis** with `context_support`, `evidence_gap`, `retriever_gap`, `synthesis_gap`, semantic pass | `evals/mirathorn_vertical_slice/run_council_room_question_set.py`, `output/council_room_question_set.{json,md}`, `output/evidence_gap_phase_ledger.json`; execution notes in `Docs/Plans/HANDOFF-execute-evidence-retrieval-synthesis-experiments.md` | When Stage D includes an **optional LLM answer** step, reuse this **loss taxonomy** (especially separating “pack had it” vs “model said it”). Prior “pretty good context” iteration is quantified here (`avg context_support`, phase ledger). |
| **Lysandra vertical slice — keyword retrieval benchmark** | Deterministic **corpus keyword scan** + gates that required markdown paths appear in top‑K | `evals/lysandra_vertical_slice/step1_retrieval.py`, `gold/step1_retrieval.json` | Map to **“required hub anchor files must be reachable from routed slugs”** — a cheap deterministic gate before any LLM pack ranking. |
| **Planner live eval**                   | Real planner **read trace + citation alignment + concept coverage**                                                                     | `evals/planner_slice/live_eval.py`, `evals/planner_slice/EVAL_DEFINITION.md`                                                                                                                                                                          | Product-shaped **regression** after sentence-store exists: “given planning ask, does planner read the hubs implied by routes?” — not the first slice gate.                                                                                    |
| **Relevance-gated retrieval handoff**   | **Scope precision** for projection context (`must_include` / `must_exclude` entities by document scope)                                 | `Docs/Plans/HANDOFF-relevance-gated-retrieval-and-pruning.md`, `src/agent/context_formatter.py`                                                                                                                                                       | Direct template for Stage D **scoped query** gates once `facts → evidence_ids → document_id` exists; for v1 sentence routes, substitute **unit_id → hub path** as the provenance edge until the fact store path is unified.                   |
| **LLM ingestion slice Gate G**          | Gold scoring over extracted **entities/facts/chunks**                                                                                   | `evals/llm_ingestion_slice/score_gold.py`, `HANDOFF-gold-scoring-eval.md`                                                                                                                                                                             | Ingestion-store correctness, not prompt packing — useful when sentence units promote into **facts** with `evidence_ids`.                                                                                                                      |


**Wiring principle:** keep `evals/sentence_routing_retrieval_falsification/` as the **narrow falsification spine** (A→B→D deterministic pack first). Add an **adapter** layer that exports packs into the same JSON shapes mirathorn / planner evals already consume, rather than merging runners prematurely.

### 6.1 Deterministic pack builder (v1, no LLM)

Given `routes` + `gold_retrieval.scope`:

1. Select units that route to any `must_include_hubs`.
2. Exclude any unit whose **only** hubs are in `must_exclude_hubs` (tri-state refinement later per relevance handoff).
3. Concatenate excerpts in stable order: session order by `(line_start, unit_id)`.
4. Truncate to `max_context_chars` with a clear `[truncated]` marker.

### 6.2 Grader

- Hard: inclusion / exclusion / budget
- Optional: substring presence of key tokens from gold (avoid duplicating Stage A)

### 6.3 Path to “LLM ranker” (v2, optional)

Only if deterministic ordering fails real queries: small rerank pass that **does not** drop anchors — only reorders or trims with logged rationale.

---

## 7. Falsification matrix (what would kill the vision)


| Failure                    | Stage | Signal                           |
| -------------------------- | ----- | -------------------------------- |
| Segmentation unstable      | A     | gold capture fails on tiny edits |
| Systematic wrong hub       | B     | must-route violations            |
| Over-attach to hubs        | B     | `max_extra_hubs` violations      |
| Refuses to abstain         | B     | must-abstain violations          |
| Proposal spam / collisions | C     | collision or count gates         |
| Scoped retrieval polluted  | D     | must_exclude violations          |
| Pack too large / noisy     | D     | budget or precision failures     |


---

## 8. Milestones (execution order)

1. **Synthetic Stage B — hub routing gold + runner**  
   - Extend `scenario_mini.json` with `hub_manifest` + `gold_routing` (must-route + must-abstain).  
   - Ship **Stage B hub-routing runner** (`step2_route_run.py`) + pytest on **fixture routing JSON** (`--no-llm`, no API) + optional live OpenAI smoke with artifact on disk.
2. **Synthetic Stage D — deterministic context pack**  
   - `gold_retrieval` with one query; deterministic pack builder + tests (no API).
3. **Stage C stub — proposal grader only**  
   - Gold + grader for collisions; LLM runner optional until Stage B is stable.
4. **Cohort harness — Stage B hub routing at N≥3**  
   - **Landed:** ``step2_route_run.py --n <N>`` (N>1) repeats the run and writes ``sentence_routing_stage_b_cohort_summary--<model>--N<N>--*.json`` + ``.md`` under ``evals/sentence_routing_retrieval_falsification/artifacts/runs/<date>/``. Cost block includes ``min`` / ``mean`` / ``max`` / ``sum`` per cost-as-signal.mdc.
5. **Real-recap scenario — pinned corpus gold**  
   - **Scaffold:** [evals/sentence_routing_retrieval_falsification/gold/scenario_real_recap_template.json](evals/sentence_routing_retrieval_falsification/gold/scenario_real_recap_template.json) (runnable copy of mini + ``scenario_notes`` + ``gold_routing`` using **match** rows). **Promotion:** copy/rename, set ``input.recap_relative_path`` to a pinned Session Recap under ``corpus/eldyrwild-markdown``, rebuild ``hub_manifest`` from that campaign’s README paths only; GM sign-off on PII (PLAN §9.4) before committing names or prose.

---

## 9. Open decisions (need explicit calls)

1. **Canonical unit:** strict sentence vs sentence-plus-neighbor window (affects A and D excerpt width).
2. **Unknown bucket:** explicit `unknown` pseudo-hub vs empty routes only.
3. **Stage B model tier:** default `gpt-5.4-mini` vs policy role from `MODEL_POLICY.json` for `actions.structured_generation`.
4. **Real-recap first scenario:** which session recap is safe to pin as gold without PII leakage in committed JSON (prefer synthetic until decided).

---

## 10. Done criteria for “plan is executed”

- B and D have **offline** pytest coverage (grader + pack builder).  
- B has **one** live smoke path with artifact on disk.  
- EXPERIMENT doc **exit criteria (§12)** updated: “landed” = synthetic Stages B+D green + cohort report stub OR full N=3 for Stage B only.

---

## 11. Immediate next implementation step (after plan approval)

Complete **Synthetic Stage B — hub routing gold + runner**: `gold_routing` in `scenario_mini.json`, `collect_stage_b_violations` in `grader.py`, and **Stage B hub-routing runner** `step2_route_run.py` with structured output + `--no-llm` fixture mode for CI.