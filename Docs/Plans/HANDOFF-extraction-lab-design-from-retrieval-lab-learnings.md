# Extraction Lab

**Date:** 2026-04-03  
**Priority:** HIGH (architectural foundation for all future benchmarking)  
**Estimated Effort:** Large (design + phased implementation)  
**Goal:** Learn from RulesIngestion's Retrieval Lab, decide what to adopt vs build new, then design and implement a proper benchmarking lab for DungeonMindBuddy's extraction/projection domain.

---

## 1) The Two Systems Compared

### What Retrieval Lab Measures (RulesIngestion)

**Problem domain:** "Can the system find the right chunks?" — retrieval quality over shaped corpora.

**Metrics:** recall@k, hit@k, nDCG@k, MRR, failure taxonomy (no_gold_defined, gold_not_in_candidates, gold_in_candidates_but_low_rank, success).

**Key architectural patterns (worth adopting):**


| Pattern                            | What It Does                                                                                                                                                                 | Where It Lives                                              |
| ---------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------- |
| **Corpus contract**                | Fingerprints the exact corpus identity (SHA, recipe, content hash). Metrics are only meaningful relative to one exact corpus contract.                                       | `retrieval_lab/benchmark_contract.py`                       |
| **GoldAnchors**                    | Decouples editorial gold intent from volatile chunk IDs. Anchors resolve to current IDs via a deterministic ladder (direct → lineage → page+path+quote → nearby fallback).   | `retrieval_lab/anchor_schema.py`, `anchor_resolver.py`      |
| **Benchmark projection lifecycle** | Separates definition (human intent) → corpus contract (identity) → projection (resolved gold) → scoring → promotion. Gold is re-resolved against each corpus, not hardcoded. | `Docs/Design/gold_resolution_design.md`                     |
| **Evaluation surfaces**            | Explicit partitions: `full_working_set`, `clean_subset`, optional `pre_review`/`post_review`. Prevents mixing ratified vs experimental queries in aggregate metrics.         | `retrieval_lab/benchmark_ratification.py`                   |
| **Run manifest**                   | Every run records exact config, corpus contract, timing, artifacts. Enables reproducibility and promotion.                                                                   | `retrieval_lab/run_manifest.py`                             |
| **Drift guard**                    | Query expansion variants checked against original via Jaccard overlap threshold. Prevents LLM-generated variants from straying.                                              | `retrieval_lab/query_enhancement/enhancer.py` lines 243–259 |
| **Baseline regression**            | Per-experiment MRR and ceiling floors. New runs compared to timestamped baselines.                                                                                           | `evals/v1_baseline/assert_baseline_regression.py`           |
| **Promotion pipeline**             | `prod_readiness.json` selects which surface is recommendation-grade. Only contract-valid runs can be promoted.                                                               | `retrieval_lab/report.py`, `RETRIEVAL_LAB.md` §8            |


### What DungeonMindBuddy Measures

**Problem domain:** "Can the system understand what it found?" — extraction quality (entity recall, fact coverage, temporal provenance), canon projection correctness, and synthesis answer quality.

**Current eval infrastructure (honest assessment):**


| System                                                                       | Maturity        | Strengths                                                                                 | Weaknesses                                                                                                                      |
| ---------------------------------------------------------------------------- | --------------- | ----------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| `llm_ingestion_slice` (gates A/V/T/B/C/D/G)                                  | Most systematic | Ordered gates, JSON outputs, manifest-backed SHA integrity, gold scoring, pytest coverage | Gold IDs are direct (no anchor resolution), no corpus contract concept, no baseline comparison, no promotion                    |
| `canon_layering` (scenarios 01–07)                                           | Good            | Fixed inputs/expected outputs, threshold file, determinism hash checks                    | Isolated from extraction pipeline, no connection to live corpus                                                                 |
| `mirathorn_vertical_slice` (entity recall, fact quality, council room Q-set) | Ad-hoc          | Covers real extraction + synthesis quality                                                | Hardcoded paths, overlapping "phase" naming with slice gates, no single orchestrator, stale `phase_d_store`, no drift detection |
| `smoke_results`                                                              | Snapshots       | Captures real run data                                                                    | Not wired as assertions, manual comparison only                                                                                 |


**What's missing (critical gaps):**

1. **No corpus contract** — Gate A checks SHA but doesn't formalize corpus identity. When extraction filters change, there's no mechanism to know which gold data is valid for which pipeline version.
2. **No gold anchor/resolution** — Gold entity/fact IDs are hardcoded. When the pipeline changes (prompt v6, filter tightening), gold data silently becomes stale. The quality drift investigation proved this: 303→86 entities, gold was authored against the old count.
3. **No baseline comparison** — No way to compare Run N to Run N-1. Each run is evaluated in isolation. The smoke report comparison to prior artifacts was done manually.
4. **No drift detection** — Quality drift was discovered manually by comparing smoke run counts to prior artifacts. No automated detector.
5. **No promotion pipeline** — No concept of "this store/extraction profile is the one to trust."
6. **Fragmented orchestration** — Three separate eval systems with overlapping scope, different naming, and no single entry point.

---

## 2) The Verdict: Don't Adopt Retrieval Lab, Build an Extraction Lab

### Why not adopt Retrieval Lab directly

Retrieval Lab is purpose-built for **retrieval** (finding chunks in a shaped substrate via embeddings/BM25/hybrid). DungeonMindBuddy's problem is **extraction** (understanding chunks — entity recognition, fact extraction, temporal provenance, canon projection, synthesis). The metrics, gold data, and scoring logic are fundamentally different:


| Dimension         | Retrieval Lab                                 | Extraction Lab (needed)                                                                    |
| ----------------- | --------------------------------------------- | ------------------------------------------------------------------------------------------ |
| Input             | Shaped substrate + queries                    | Raw markdown + frontmatter                                                                 |
| Gold              | "Which chunks answer this question?"          | "Which entities/facts/events should this text produce?"                                    |
| Metrics           | recall@k, nDCG, MRR                           | Entity recall, fact coverage, temporal accuracy, projection correctness, synthesis quality |
| Drift source      | Chunking/merging changes invalidate chunk IDs | Prompt/filter/taxonomy changes invalidate extraction counts                                |
| Contract identity | Corpus fingerprint (SHA of chunks)            | Pipeline fingerprint (prompt version + filter config + model + corpus SHA)                 |


Retrieval Lab's **machinery** doesn't apply, but its **architectural patterns** absolutely do.

### What to adopt (patterns, not code)

1. **Contract-aware benchmarking** — every scored run is bound to one exact pipeline identity
2. **Gold anchor/resolution** — editorial gold intent survives pipeline changes
3. **Evaluation surfaces** — separate ratified core from experimental/working-set queries
4. **Run manifests** — exact reproducibility
5. **Baseline regression** — automated comparison to prior runs
6. **Drift detection from the outset** — not bolted on after the fact

---

## 3) Extraction Lab Design

### 3.1 Pipeline Identity Contract

The equivalent of Retrieval Lab's "corpus contract" for extraction is a **pipeline contract** — a fingerprint of everything that affects extraction output for the same input:

```json
{
  "contract_version": 1,
  "corpus_sha256": "abc...",
  "entity_prompt_id": "phase_b_pass1_entity_extraction_v6_prompt_cache_split",
  "fact_prompt_id": "fact_extraction_v3_...",
  "recap_prompt_id": "recap_extraction_v2_prompt_cache",
  "entity_model": "gpt-5.4-nano",
  "fact_model": "gpt-5.4-nano",
  "batch_size": 5,
  "filter_version": "v2_tightened",
  "taxonomy_hash": "<sha256 of entity_taxonomy.py enum + facet sets>",
  "heuristic_blocklist_hash": "<sha256 of _JUNK_ENTITY_EXACT + _LOW_SIGNAL_* + ...>"
}
```

**Rule:** Two runs with the same pipeline contract should produce identical (deterministic) or near-identical (LLM variance) outputs. Gold data is only valid for the pipeline contract it was authored against.

### 3.2 Gold Anchor System (Extraction Domain)

Retrieval Lab's `GoldAnchor` maps editorial intent → current chunk IDs via a resolution ladder. The extraction equivalent maps editorial gold intent → expected extraction outcomes, surviving prompt/filter changes.

**Entity gold anchors:**

```json
{
  "anchor_id": "mirathorn_city",
  "intent": "The city of Mirathorn should be extracted as a place entity",
  "expected_class": "place",
  "expected_names": ["Mirathorn", "City of Mirathorn"],
  "source_text_marker": "Mirathorn is a fortified city",
  "source_file": "The City of Mirathorn.md",
  "resolution_strategy": "name_in_store",
  "min_fact_count": 5
}
```

**Resolution:** Instead of resolving chunk IDs, resolve by checking if an entity matching the anchor's name/class exists in the extraction output. This survives prompt changes, filter changes, and model changes — the editorial intent ("Mirathorn should be extracted") persists even if the `entity_id` changes.

**Fact gold anchors:**

```json
{
  "anchor_id": "mirathorn_geography",
  "intent": "Mirathorn's geographical setting should be captured",
  "subject_anchor": "mirathorn_city",
  "expected_attribute": "geography",
  "match_keywords": ["storm", "peaks", "river", "valley"],
  "alternative_attributes": ["location", "setting"],
  "source_text_marker": "nestled in the Stormbreak Valley"
}
```

**Key insight from Retrieval Lab:** The anchor is the **durable editorial artifact**. The resolved match is the **transient projection** against a specific pipeline contract. This is exactly why DMB's current gold (hardcoded `gold_entities.json` with 13 entries authored against the old pipeline) became silently stale.

### 3.3 Evaluation Surfaces

Borrowing Retrieval Lab's surface concept:


| Surface           | Purpose                                                         | Queries                                                    |
| ----------------- | --------------------------------------------------------------- | ---------------------------------------------------------- |
| `core_extraction` | Ratified, high-confidence gold anchors for regression detection | Mirathorn city entities, key facts, known temporal anchors |
| `vertical_slice`  | Council Room end-to-end (extraction → projection → synthesis)   | Wolf status, architectural deltas, pre/post contrast       |
| `recap_lane`      | Event records and claims from session recaps                    | Session 17+ recap coverage                                 |
| `working_set`     | Experimental / newly added gold, not yet ratified               | New corpus expansions, edge cases                          |


**Promotion rule:** Only `core_extraction` is used for automated regression gating. Other surfaces are informational until ratified.

### 3.4 Run Manifest and Baseline Comparison

Every extraction lab run produces:

```
out/extraction_lab/<run_id>/
  pipeline_contract.json      # exact pipeline identity
  run_manifest.json           # timing, config, corpus stats
  entity_results.json         # per-anchor resolution results
  fact_results.json           # per-anchor resolution results
  aggregate_metrics.json      # recall, coverage, drift metrics
  drift_report.json           # comparison to baseline (if one exists)
  report.md                   # human-readable summary
```

**Baseline regression:** `assert_extraction_regression.py` loads the latest promoted baseline's `aggregate_metrics.json` and fails if key metrics drop below thresholds (entity recall, fact coverage, temporal accuracy).

### 3.5 Drift Detection (Built In From Day One)

Three drift signals:

1. **Pipeline contract drift** — prompt ID, filter hash, model, or taxonomy changed since baseline. Automatic re-resolution of gold anchors required.
2. **Extraction count drift** — entity/fact counts deviate from baseline by more than configurable threshold (e.g., ±15%). Warning, not hard fail — drift may be intentional (filter tightening).
3. **Gold anchor resolution drift** — previously-resolved anchors no longer resolve. Hard fail if core anchors break; warning for working-set anchors.

---

## 4) Implementation Plan

### Phase 0: Pipeline Contract (foundation)

- Build `extraction_lab/pipeline_contract.py` — compute pipeline fingerprint from prompt IDs, filter hashes, model names, taxonomy state
- Add `compute_pipeline_contract()` callable from any eval script
- Store contract in run output directory

**File locations to read for prompt/filter/taxonomy identity:**

- `src/ingestion/entity_extractor.py` line 57 (`_PROMPT_ID`), lines 107–224 (blocklists)
- `src/ingestion/fact_extractor.py` (equivalent prompt ID)
- `src/contracts/entity_taxonomy.py` (`EntityClass` enum, `ALLOWED_SUBTYPE_FACETS`)
- `src/ingestion/entity_extractor.py` line 913 (`_RECAP_PROMPT_ID`)

### Phase 1: Gold Anchor System

- Define `ExtractionGoldAnchor` schema (Pydantic model)
- Build anchor resolver: entity anchors → entity store lookup, fact anchors → fact store lookup
- Migrate `evals/mirathorn_vertical_slice/gold/gold_entities.json` (13 entries) and `gold_facts.json` (10 entries) to anchor format
- Add resolution tests

**Pattern source:** `retrieval_lab/anchor_schema.py` (GoldAnchor model), `retrieval_lab/anchor_resolver.py` (resolution ladder)

### Phase 2: Run Manifest and Reporting

- Build `extraction_lab/run_manifest.py` — capture config, timing, corpus stats, pipeline contract
- Build `extraction_lab/report.py` — aggregate metrics, per-anchor results, human-readable report
- Output to `out/extraction_lab/<run_id>/`

**Pattern source:** `retrieval_lab/run_manifest.py`, `retrieval_lab/report.py`

### Phase 3: Baseline Regression

- Build `extraction_lab/assert_regression.py` — compare current run to promoted baseline
- Define threshold config file (`extraction_lab/regression_thresholds.json`)
- Implement `promote_baseline.py` — mark a run as the new baseline

**Pattern source:** `evals/v1_baseline/assert_baseline_regression.py`

### Phase 4: Unified Orchestrator

- Build `extraction_lab/run_extraction_lab.py` — single entry point that:
  - Computes pipeline contract
  - Resolves gold anchors against current store (or runs extraction)
  - Scores all surfaces
  - Compares to baseline
  - Emits run artifacts
- Subsumes the current fragmented eval scripts into one harness with configurable surfaces

### Phase 5: Drift Detection

- Automated pipeline contract comparison between runs
- Count-drift alerting (entity/fact/evidence unit counts vs baseline)
- Gold anchor resolution tracking (which anchors resolved, which broke, which are new)

---

## 5) What NOT to Build (Scope Boundaries)

- **Do not import RulesIngestion code** — different repo, different problem. Adopt patterns, not packages.
- **Do not build retrieval metrics** — DMB doesn't do chunk retrieval. Its "retrieval" is canon projection, which is already covered by the reducer benchmarks.
- **Do not replace existing eval scripts immediately** — Phase 4 unification comes after the foundation (Phases 0–3) is proven. Existing scripts continue working.
- **Do not build embedding/BM25 infrastructure** — not applicable to the extraction domain.

---

## 6) Decision Framework for the Implementing Agent

Read these before implementing:


| Question                                       | Answer                                                                                                                                                                             |
| ---------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Should I import from `retrieval_lab`?          | **No.** Adopt patterns and architectural ideas. Write new code.                                                                                                                    |
| Should I modify existing eval scripts?         | **Not until Phase 4.** Build the lab alongside them first.                                                                                                                         |
| Which gold data do I use?                      | Start by migrating the existing 13 entity / 10 fact gold entries to anchor format. Add new anchors for the quality drift investigation findings (86 entities, 536 facts baseline). |
| What pipeline contract do I fingerprint first? | Start with `_PROMPT_ID` + model name + entity taxonomy hash. Add filter hashes in Phase 1 when anchors need them.                                                                  |
| Where does the code live?                      | `extraction_lab/` at repo root (sibling to `src/`, `evals/`, `tools/`).                                                                                                            |
| How do I test?                                 | `tests/extraction_lab/` — mirror the `tests/retrieval_lab/` structure from RulesIngestion.                                                                                         |


---

## 7) Reference Files

### RulesIngestion (read for patterns, don't import)


| File                                                             | What to learn                                                |
| ---------------------------------------------------------------- | ------------------------------------------------------------ |
| `RulesIngestion/Docs/Design/RETRIEVAL_LAB.md`                    | Architecture doc structure, lifecycle, surfaces, promotion   |
| `RulesIngestion/Docs/Design/gold_resolution_design.md`           | Definition → contract → projection → scoring separation      |
| `RulesIngestion/retrieval_lab/anchor_schema.py`                  | GoldAnchor model, resolution strategy                        |
| `RulesIngestion/retrieval_lab/anchor_resolver.py`                | Resolution ladder (direct → lineage → structural → fallback) |
| `RulesIngestion/retrieval_lab/benchmark_contract.py`             | Contract validation, alignment summary                       |
| `RulesIngestion/retrieval_lab/metrics.py` lines 177–191          | Failure bucket taxonomy                                      |
| `RulesIngestion/retrieval_lab/run_manifest.py`                   | Run reproducibility                                          |
| `RulesIngestion/evals/v1_baseline/assert_baseline_regression.py` | Regression thresholds                                        |


### DungeonMindBuddy (current state)


| File                                                          | Current role                                                           |
| ------------------------------------------------------------- | ---------------------------------------------------------------------- |
| `evals/llm_ingestion_slice/run_slice.py`                      | Most systematic current harness — gates, outputs, gold scoring         |
| `evals/llm_ingestion_slice/score_gold.py`                     | Gold scoring with sub-gates (core recall, temporal, catalog, negative) |
| `evals/mirathorn_vertical_slice/gold/gold_entities.json`      | 13 entity gold entries (authored against old pipeline)                 |
| `evals/mirathorn_vertical_slice/gold/gold_facts.json`         | 10 fact gold entries (authored against old pipeline)                   |
| `evals/canon_layering/run_benchmarks.py`                      | Deterministic projection scenarios with hash checks                    |
| `Docs/Plans/HANDOFF-investigate-entity-fact-quality-drift.md` | Quality drift investigation — new baseline (86 entities / 536 facts)   |


---

## 8) Success Criteria

The Extraction Lab is "done enough to use" when:

- Pipeline contract is computable and stored with every run
- At least 13 entity anchors + 10 fact anchors exist in anchor format
- Anchors resolve against a current store (e.g., `batch_api_full_corpus`)
- A single `run_extraction_lab.py` produces a structured run directory with metrics
- Baseline regression can detect a -10% entity recall drop
- Gold anchor resolution drift is flagged when an anchor stops resolving
- The lab runs without API calls (uses cached/pre-built stores)

---

## 9) V1 Spec Lock: Contract + Anchor Semantics + Thresholds

This section is the implementation lock for Extraction Lab v1. If a detail here conflicts with earlier prose, treat this section as source-of-truth.

### 9.1 Pipeline Contract v1 (Minimal, Stable)

**Goal:** keep v1 strict enough for reproducibility, but small enough to avoid contract churn.

**Required fields (v1):**

```json
{
  "contract_version": 1,
  "corpus_sha256": "sha256-of-corpus-input-set",
  "entity_prompt_id": "entity-extractor-prompt-id",
  "fact_prompt_id": "fact-extractor-prompt-id",
  "entity_model": "gpt-5.4-nano",
  "fact_model": "gpt-5.4-nano",
  "taxonomy_hash": "sha256-of-EntityClass-and-allowed-facets",
  "heuristic_blocklist_hash": "sha256-of-entity-filter-blocklists"
}
```

**Optional fields (record if available, do not fail if absent in v1):**

- `recap_prompt_id`
- `recap_model`
- `batch_size`
- `filter_version` (human-readable tag, not required for identity if hash is present)
- `pipeline_code_sha` (git commit or content hash for extraction modules)

**Identity rule (v1):**

- Two runs are **contract-equal** only if all required fields match exactly.
- Baseline regression checks run only when contract-equal.
- If not contract-equal, run anchor re-resolution and emit drift report as **non-regression comparison**.

### 9.2 Anchor Matching Semantics v1

Use deterministic, explicit matching to avoid evaluator ambiguity.

**Entity anchor pass conditions:**

1. At least one extracted entity matches anchor `expected_class`
2. Name match succeeds against `expected_names` using normalized comparison:
  - lowercase
  - trim/collapse whitespace
  - strip surrounding punctuation
3. If `min_fact_count` is present, matched entity has `fact_count >= min_fact_count`

**Entity anchor fail buckets (required in output):**

- `class_mismatch`
- `name_not_found`
- `fact_count_below_min`
- `missing_entity`

**Fact anchor pass conditions:**

1. Subject entity anchor resolves first (`subject_anchor`)
2. At least one fact for that subject matches:
  - attribute in `{expected_attribute} U alternative_attributes`, and
  - contains at least one `match_keywords` token (normalized substring match)

**Fact anchor fail buckets (required in output):**

- `subject_unresolved`
- `attribute_mismatch`
- `keyword_mismatch`
- `missing_fact`

### 9.3 Regression Thresholds v1

Store in `extraction_lab/regression_thresholds.json`.


| Surface           | Metric                       | Gate Type | Threshold (v1)         | Notes                                                     |
| ----------------- | ---------------------------- | --------- | ---------------------- | --------------------------------------------------------- |
| `core_extraction` | entity_anchor_recall         | hard fail | drop > 10% vs baseline | Primary extraction health gate                            |
| `core_extraction` | fact_anchor_recall           | hard fail | drop > 12% vs baseline | Slightly looser than entity due to wording variability    |
| `core_extraction` | unresolved_core_anchors      | hard fail | any increase > 0       | Core anchors are ratified; new unresolved anchor is a bug |
| `core_extraction` | total_entity_count_drift_pct | warning   | abs(delta) > 15%       | Drift can be intentional; require human review            |
| `core_extraction` | total_fact_count_drift_pct   | warning   | abs(delta) > 20%       | Fact counts are typically noisier than entity counts      |
| `vertical_slice`  | question_pass_rate           | warning   | drop > 10%             | Informational until ratified                              |
| `recap_lane`      | event_record_recall          | warning   | drop > 15%             | Recap lane remains experimental in v1                     |
| `working_set`     | any metric                   | none      | no hard threshold      | Report-only surface                                       |


**Threshold interpretation:**

- `drop > X%` means relative drop from promoted baseline metric.
- `abs(delta) > X%` means absolute percent change in raw counts.
- Missing baseline for a surface -> emit `no_baseline_for_surface` warning, do not fail run.

### 9.4 Minimal End-to-End Runner Requirement (before full Phase 4)

To reduce delivery risk, implement a thin runner in Phase 2 or 3:

- Command: `uv run python -m extraction_lab.run_extraction_lab --surface core_extraction --store <path>`
- Must produce:
  - `pipeline_contract.json`
  - `aggregate_metrics.json`
  - `entity_results.json`
  - `fact_results.json`
  - `report.md`
- Full multi-surface orchestration can still land in Phase 4.

This ensures v1 can be validated end-to-end before unifying all legacy scripts.