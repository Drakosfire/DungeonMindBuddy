# Handoff: Investigate Entity/Fact Quality Drift

**Date:** 2026-04-03  
**Status:** COMPLETED — Outcome A (noise reduction, no code changes needed)  
**Priority:** MEDIUM  
**Estimated Effort:** Medium (run + analyze, no code changes expected initially)  
**Precondition:** Read this file, then read referenced code and artifacts before running anything.

---

## 1) Problem Statement

The smoke report (`evals/smoke_results/HANDOFF-benchmark-sample-e2e-report-2026-04-03.md`, Run D) showed a substantial extraction-profile shift on the same 4 Mirathorn council-room files versus a prior artifact:


| Metric   | Prior Artifact | Current (Run D) | Delta |
| -------- | -------------- | --------------- | ----- |
| Entities | 303            | 91              | -70%  |
| Facts    | 969            | 514             | -47%  |


This **may or may not** be a regression. The pipeline underwent prompt version bumps, expanded heuristic filters, batching changes, and taxonomy tightening. Many of the removed entities could be noise. The goal of this investigation is to **classify** the drift — how much is intentional noise reduction vs. how much is real entity/fact loss.

---

## 2) Known Mechanisms Driving the Reduction

Five additive mechanisms were identified from the codebase. Each should be quantified.

### 2a: LLM-level `decision: "exclude"` gate

The v6 entity prompt instructs the model to emit `decision: "exclude"` with an `exclude_reason` for generic nouns, document structure, mechanics, collectives, and temporal connectors.

- **File:** `src/ingestion/entity_extractor.py` lines 676–690 (prompt instructions)
- **File:** `src/ingestion/entity_extractor.py` lines 1391–1399 (exclude collection)

### 2b: Post-LLM heuristic filter `_is_plausible_entity_name`

A multi-rule filter applied after extraction:

- **File:** `src/ingestion/entity_extractor.py` lines 1028–1087
- **Blocklists:** `_JUNK_ENTITY_EXACT` (line 107), `_JUNK_ENTITY_PREFIXES` (line 118), `_LOW_SIGNAL_SINGLE_TOKENS` (line 135), `_LOW_SIGNAL_PHRASES` (line 185), `_DND_SKILLS` (line 204), `_DND_SPELLS` (line 224)
- **Substring grounding:** line 1062–1064 — rejects names not found in source text
- **Concept/event rules:** lines 1074–1085 — single-token < 5 chars, mention_count < 2 with <= 2 tokens, no capitalized token, all-connectors

### 2c: Taxonomy narrowing

`EntityClass` no longer includes `unknown` or `document_anchor`. The prompt explicitly instructs the model not to emit those classes.

- **File:** `src/contracts/entity_taxonomy.py` — `EntityClass` enum, facet allowlists
- **File:** `schemas/v0.1/entity.schema.json` — `entity_class` enum (lines 57–66)

### 2d: Entity deduplication at store level

After filtering, entities are deduped through `FactStore.add_entities` which merges candidates that match existing entities by alias/overlap.

- **File:** `src/ingestion/entity_extractor.py` lines 1441–1443
- **File:** `src/store.py` — `add_entities` merge logic

### 2e: Fact reduction (cascading from fewer entities)

- **Scoped entity lists per unit:** `_prompt_entities_for_unit` (line 453 in `fact_extractor.py`) only passes entities whose names match the unit text. Fewer entities → fewer valid `subject_entity_id` targets.
- **Invalid subject/attribute drops:** `_build_fact_record` returns `None` if subject not in entity set or attribute not in `_VALID_ATTRIBUTES` (line 537).
- **Fact deduplication:** `_deduplicate_facts` merges rows with same `(subject, attribute, normalized-key)` (line 588).

---

## 3) Investigation Protocol

### Step 1: Fresh ingest with excluded_candidates capture

Run a fresh 4-file ingest on the benchmark sample to generate the `excluded_candidates.json` artifact. Clear any existing cache first to ensure the v6 prompt runs.

```bash
# Clean cache for fresh run
rm -rf out/stores/quality_drift_investigation

uv run python tools/batch_ingest_corpus.py \
    --store out/stores/quality_drift_investigation \
    --paths-file evals/mirathorn_vertical_slice/benchmark_corpus_paths.txt \
    --exclude-pattern "Longmont Campaign"
```

**Note:** The `--exclude-pattern` drops the 5th file (Longmont General Notes) to match Run D's 4-file scope. If `--exclude-pattern` is not supported, manually create a 4-line paths file from the first 4 entries of `benchmark_corpus_paths.txt`.

Paths file location: `evals/mirathorn_vertical_slice/benchmark_corpus_paths.txt`

### Step 2: Analyze excluded_candidates.json

After the run, examine the excluded candidates artifact:

```bash
# Location: <cache_dir>/excluded_candidates.json
# Expected fields per entry: display_name, exclude_reason, entity_class, source, evidence_id
```

Classify the excluded candidates into buckets:


| Bucket            | Description                                                          | Example                               |
| ----------------- | -------------------------------------------------------------------- | ------------------------------------- |
| **True noise**    | Generic nouns, mechanics, pronouns, document structure               | "description", "DC 15", "some"        |
| **Borderline**    | Could be entities in some contexts but not narratively important     | "rescue", "fire", "corruption"        |
| **Real entities** | Named characters, places, factions, items that should have been kept | "Captain Lysandra", "The Shadow Cult" |


Count each bucket. If "Real entities" > 10% of excluded candidates, the filters are too aggressive.

### Step 3: Compare entity class distributions

Load the current run's entities and the prior artifact's entities. Compare class distributions:

- Prior artifact: `evals/mirathorn_vertical_slice/output/council_room_ingest_scope.json`
- Current run: `out/stores/quality_drift_investigation/entities.json`

Key questions:

- Which `entity_class` values lost the most entries?
- Are `concept` and `event` disproportionately affected (expected given the stricter rules)?
- Are `actor`, `place`, `faction`, `item` counts stable (they should be, as filters target low-signal generics)?

### Step 4: Spot-check fact coverage

For the top 10 entities by fact count in the prior artifact, check whether they exist in the current run and whether their fact counts are comparable. This identifies whether important entities survived filtering but lost facts, or whether they were removed entirely.

### Step 5: Assess the grounding filter specifically

The substring-grounding rule (line 1062–1064) rejects any entity whose `display_name` doesn't appear in the source text. This is anti-hallucination but may be too strict for:

- Entities referred to by partial name or pronoun in the chunk
- Entities whose canonical name differs from the in-text reference

Check `excluded_candidates.json` for entries with `exclude_reason: "heuristic_filter"` and manually verify whether their names actually appear in the source text of the cited `evidence_id`.

---

## 4) Decision Framework

After the investigation, one of three outcomes:

### Outcome A: Drift is almost entirely noise reduction

- "Real entities" bucket < 5% of excluded
- `actor`, `place`, `faction` counts are stable
- `concept`, `event` reductions are from genuinely low-signal entries
- **Action:** Accept current counts as the new baseline. Update prior artifact references.

### Outcome B: Filters are slightly too aggressive

- "Real entities" bucket is 5–15% of excluded
- A few specific blocklist entries or rules catch legitimate names
- **Action:** Tune specific entries (remove from blocklists, adjust thresholds). Re-run and compare.

### Outcome C: Significant quality loss

- "Real entities" bucket > 15% of excluded
- Named characters, places, or factions are being dropped
- Fact coverage for important entities has large gaps
- **Action:** Broader filter review needed. Consider relaxing concept/event rules, adjusting mention_count thresholds, or loosening substring grounding.

---

## 5) File Reference Summary


| File                                                                   | What to look at                                                                                                  |
| ---------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| `src/ingestion/entity_extractor.py`                                    | Lines 107–224 (blocklists), 1028–1087 (filter function), 1383–1457 (post-processing + excluded_candidates write) |
| `src/ingestion/fact_extractor.py`                                      | Lines 453–469 (entity scoping per unit), 537–540 (record drops), 588–601 (dedup)                                 |
| `src/contracts/entity_taxonomy.py`                                     | `EntityClass` enum, `ALLOWED_SUBTYPE_FACETS`                                                                     |
| `evals/mirathorn_vertical_slice/output/council_room_ingest_scope.json` | Prior artifact baseline (303 entities, 969 facts for 4 council files)                                            |
| `evals/mirathorn_vertical_slice/benchmark_corpus_paths.txt`            | Deterministic file list for reproducible runs                                                                    |
| `tests/ingestion/test_entity_extractor_filters.py`                     | Existing filter tests (check for locked-in behavior)                                                             |


---

## 6) Investigation Results (2026-04-03)

**Outcome A confirmed: drift is almost entirely noise reduction. No code changes needed.**

### Excluded Candidate Classification

| Bucket | Count | % | Interpretation |
|--------|-------|---|----------------|
| True noise | 148 | 70.1% | Generic nouns, mechanics, document structure, sentence fragments |
| Borderline | 59 | 28.0% | Low-signal concepts/events (kaiju summoning, purification ritual, etc.) |
| Real entities | 4 | 1.9% | All survived in store via other chunks or were correctly excluded |

The 4 "real entity" exclusions: Elara Swiftwind (present in store with 19 facts), Barin Coppergleam (present with 1 fact + "Barin Stonefoot" variant with 6), Players (correctly excluded as underspecified collective), Gnome/Race (correctly excluded).

### Entity Class Distribution

Core classes dominate: 73/86 entities (85%) are actor/place/group/object. Concept/event reduction to 13 entities (15%) is the intended effect of the stricter filters.

### Fact Coverage

Only 1 entity with zero facts out of 86 (Agricultural Union). Top-10 entities are narratively significant. 536 facts well-distributed.

### New Baseline

Accept **86 entities / 536 facts** on the 4-file council-room subset as the post-filter baseline.

### Minor Future Opportunities (not regressions)

- **Alias resolution:** "Barin Coppergleam" and "Barin Stonefoot" likely the same character; not merged.
- **Typo tolerance:** "Torrin Flamescale" (13 facts) and "Torin Flamescale" (2 facts) are typo variants not merged.
- **Canonical naming:** "the cult" has 37 facts as a group entity — could benefit from resolution to its canonical name if one exists in the source material.

---

## 7) Scope Boundary

This handoff was an **investigation**, not a code change. The outcome was accepting current counts as baseline with no code changes needed.

Do NOT:

- Revert filters wholesale without evidence
- Change prompts without understanding which filter stage is responsible
- Conflate this with the recap lane bug (separate handoff: `HANDOFF-fix-recap-lane-text-format-bug.md`)

