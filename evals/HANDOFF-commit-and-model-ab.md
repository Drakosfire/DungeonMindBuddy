# Handoff: Commit Packaging + Model A/B Comparison

**Date:** 2026-04-02  
**Repo:** `DungeonMindBuddy` (`/home/drakosfire/Projects/DungeonOverMind/DungeonMindBuddy`)  
**Branch:** `main` — ahead of `origin/main` (not pushed). Working tree should be clean except optional local artifacts below.  
**Audience:** Next agent pushing `main`, or continuing entity/temporal work.

## Status Update (2026-04-02)

Task A is complete and committed on `main` in this sequence:
- `cb75e7a` `docs: temporal metadata design doc, status report, handoffs`
- `ec3ca3f` `feat(evals): gold scoring eval with entity recall, temporal accuracy, Gate G`
- `e5fddfd` `feat(temporal): tick gate, consistency gate, quality warning, evidence metadata propagation`
- `f788cc1` `feat(entities): prompt narrowing, hygiene filters, entity_tags, alias caps`
- `3c4767d` `feat(corpus): upgrade frontmatter to temporal metadata v0.2`
- `2430957` `feat(entities): add entity_kind and semantic_facets with taxonomy normalization`

Verification after commit packaging:
- `uv run pytest tests/ -q` -> `170 passed, 2 skipped`
- `uv run python evals/llm_ingestion_slice/run_slice.py` -> exit `0`

Remaining untracked artifacts intentionally excluded from version control:
- `.cursor/agents/*.md`
- `evals/mirathorn_vertical_slice/output/council_room_*`
- `evals/mirathorn_vertical_slice/output/q_wolf_status_*`
- `evals/mirathorn_vertical_slice/output/post_play_delta_*`

Task B is complete. A/B report written to:
- `evals/MODEL_AB_COMPARISON.md`

Task B headline results (3-file slice):
- Weighted `other` entity rate improved from `33.4%` (nano) to `16.8%` (fast_smart)
- Aggregate counts dropped on fast_smart: entities `410 -> 280`, facts `949 -> 741`
- Aggregate ingest wall time increased on fast_smart: `195115ms -> 224755ms`
- Gold-score recall is mixed by source; see report table for per-file core recall/precision/F1
- Token-cost and hygiene-blocked counts are currently `n/a` because those metrics are not persisted in logs

## Status Update (2026-04-03): Auto-escalation pilot + full corpus

Auto-escalation policy design, implementation, pilot, and full-corpus run are complete.

Primary report:
- `evals/AUTO_ESCALATION_FULL_CORPUS_REPORT.md`

Key run facts:
- **Pilot (10 files):**
  - `flagged_count=9`, `escalation_runs_count=9`, runtime `~14.0m`
  - run used `--escalate-world=true` (intentional stress test)
- **Full corpus (130 files):**
  - `decisions_count=121`, `flagged_count=40`, `escalation_runs_count=40`, runtime `~94.2m`
  - `--escalate-world=false` (as requested), base=`fast_smart_mini`, escalation=`highest_intelligence`
  - `9` corpus files produced zero-output deltas (non-ingestible card/template/token-style docs)

Observed quality vs throughput tradeoff on escalated subset (full run, 40 files):
- Throughput improved: `entities_per_chunk 1.066 -> 1.229`, `facts_per_chunk 3.326 -> 3.782`
- Taxonomy quality worsened:
  - `other_rate 36.91% -> 42.45%` (worse)
  - `other_missing_facets_rate 8.41% -> 23.59%` (worse)
  - `unknown_kind_rate 0.07% -> 0.29%` (worse)
- Pairwise quality outcomes:
  - `other_rate`: improved `9`, worsened `30`, same `1`
  - `other_missing_facets_rate`: improved `8`, worsened `29`, same `3`

Escalation trigger distribution (full run):
- `other_rate>0.30`: `32`
- `entities_per_chunk<0.80`: `9`
- `other_missing_facets_rate>0.40`: `6`
- `facts_per_chunk<2.00`: `2`

Learnings:
- Current policy improves volume but often regresses taxonomy quality.
- Blanket world escalation is not worth the cost/quality risk and should stay disabled.
- Acceptance gating is required before trusting escalated output.

Recommended next implementation:
- Add acceptance gate in `tools/batch_ingest_corpus.py`:
  - keep escalation only if `other_rate` and `other_missing_facets_rate` are non-worse (or within tolerance),
  - otherwise keep base pass output.
- Write `escalation_acceptance.json` with accepted/rejected decision and metric deltas.
- Based on completed full-run data, strict non-worse acceptance would have accepted only `3/40` escalations.

---

## 0. Verify baseline

```bash
cd /home/drakosfire/Projects/DungeonOverMind/DungeonMindBuddy
uv run pytest tests/ -q                                 # 170 passed, 2 skipped
uv run python evals/llm_ingestion_slice/run_slice.py     # exit 0, all 9 gates pass (A/V/T/TC/TW/B/C/D/G)
```

If either fails, stop and investigate.

---

## 1. Task A: Commit the dirty tree

### Why this is urgent

153 modified files and 22 untracked files represent weeks of work sitting uncommitted. Any workspace accident, reset, or branch switch risks losing it. This is pure risk reduction.

### Logical commit boundaries

The changes fall into 4 functional commits (plus 1 optional docs commit). Each should be committed in order — later commits depend on earlier ones.

#### Commit 1: Corpus frontmatter v0.2 rewrite

**Message:** `feat(corpus): upgrade frontmatter to temporal metadata v0.2`

**Files to stage:**

```
corpus/eldyrwild-markdown/**/*.md                       # ~130 modified corpus files
schemas/v0.1/document_metadata.schema.json              # v0.2 schema (temporal_scope, origin/last_updated_session)
src/ingestion/frontmatter.py                            # DocumentMetadata + parse/render for v0.2 fields
src/ingestion/frontmatter_inference.py                  # heuristic/LLM inference emits v0.2 fields
evals/llm_ingestion_slice/slice_manifest.json           # updated SHA256 entries
tests/ingestion/test_frontmatter.py                     # updated test fixtures
tests/test_chunker.py                                   # updated test fixtures
```

**Verify after staging:** `uv run pytest tests/ingestion/test_frontmatter.py tests/test_chunker.py -q`

#### Commit 2: Entity extraction hardening

**Message:** `feat(entities): prompt narrowing, hygiene filters, entity_tags, alias caps`

**Files to stage:**

```
src/ingestion/entity_extractor.py                       # _relevant_known_entities, _is_plausible_entity_name, ExtractedEntity.entity_tags
src/store.py                                            # _MAX_ALIASES_PER_ENTITY, _MAX_ENTITY_TAGS_MERGED, merge logic
src/contracts/entity_tags.py                            # NEW — normalize_entity_tags()
src/agent/context_formatter.py                          # entity_tags in header display
schemas/v0.1/entity.schema.json                         # entity_tags field
schemas/v0.1/examples/entity.example.json               # includes entity_tags
tests/ingestion/test_entity_extractor_filters.py        # NEW — pronoun, length, relevant-known tests
tests/test_store.py                                     # entity_tags merge tests
tests/test_context_formatter.py                         # entity_tags display tests
tests/test_fact_extractor.py                            # minor update
```

**Verify after staging:** `uv run pytest tests/ingestion/test_entity_extractor_filters.py tests/test_store.py tests/test_context_formatter.py tests/test_fact_extractor.py -q`

#### Commit 3: Temporal gates + evidence metadata

**Message:** `feat(temporal): tick gate, consistency gate, quality warning, evidence metadata propagation`

**Files to stage:**

```
src/contracts/temporal_tick_gate.py                     # NEW — campaign_temporal_tick_violations, consistency, quality summary
src/cli.py                                              # 3 new ingest gates in _build_ingest_gate_report
src/ingestion/event_sourced_slice.py                    # temporal metadata on seeds, entity seeding fix, fact session inheritance
src/ingestion/chunker.py                                # stamps evidence units with document_temporal_scope/origin/last_updated
schemas/v0.1/evidence_unit.schema.json                  # optional temporal metadata fields
tests/contracts/test_temporal_tick_gate.py               # NEW — tick, consistency, quality summary tests
tests/test_cli.py                                       # temporal gate pass/fail integration
```

**Verify after staging:** `uv run pytest tests/contracts/test_temporal_tick_gate.py tests/test_cli.py -q`

#### Commit 4: Gold scoring pipeline + Gate G

**Message:** `feat(evals): gold scoring eval with entity recall, temporal accuracy, Gate G`

**Files to stage:**

```
evals/llm_ingestion_slice/score_gold.py                 # NEW — standalone scorer
evals/llm_ingestion_slice/run_slice.py                  # Gate G integration, GOLD_SCORE_THRESHOLDS
evals/llm_ingestion_slice/gold/manual_entity_extraction_gold.json  # NEW — human-authored gold
tests/evals/test_score_gold.py                          # NEW — 7 scorer tests
tests/evals/test_manual_entity_extraction_gold.py       # NEW — gold structure tests
tests/evals/test_llm_ingestion_slice.py                 # Gate G assertions, regression tests
```

**Verify after staging:** `uv run pytest tests/evals/ -q`

#### Commit 5 (optional): Docs and status

**Message:** `docs: temporal metadata design doc, status report, handoffs`

**Files to stage:**

```
Docs/Design/SCHEMA-document-temporal-metadata-v0.2.md   # NEW
report/REPORT-current-status.md
evals/HANDOFF-gold-scoring-eval.md                      # NEW
evals/HANDOFF-commit-and-model-ab.md                    # NEW (this file)
evals/HANDOFF-next-agent-ingestion-temporal-gates.md    # NEW
```

### Files to NOT stage

```
.cursor/agents/*.md                                     # local agent briefs
evals/mirathorn_vertical_slice/output/council_room_*    # investigation artifacts
evals/mirathorn_vertical_slice/output/q_wolf_status_*   # investigation artifacts
evals/mirathorn_vertical_slice/output/post_play_delta_* # investigation notes
```

### After all commits

```bash
uv run pytest tests/ -q                                 # full suite: 170 passed, 2 skipped
uv run python evals/llm_ingestion_slice/run_slice.py     # exit 0, all gates pass
git log --oneline -5                                     # verify commit sequence
```

Push when satisfied: `git push origin main`

---

## 2. Task B: Model A/B comparison

### Why this matters now

The nano experiment (17/130 corpus files ingested) showed:
- 43% of entities classified as `"other"` (vs npc/location/faction/item)
- Pronoun entities created ("his", "her") — now blocked by filters, but indicates extraction quality floor
- 31 entities with names > 60 chars — now blocked by length filter

These are symptoms. The question is: **how much is the model vs how much is the pipeline?** The hygiene filters catch the worst garbage, but entity-type classification accuracy determines whether the knowledge graph is usable for downstream synthesis. If a mid-tier model gets the "other" rate down to ~15%, the pipeline is fine and the model is the bottleneck. If it stays at 40%, the prompt or extraction architecture needs work.

### What to compare

Run the same 3 corpus files through ingest twice:
1. `MODEL_POLICY.json` → `cheapest` (gpt-5.4-nano)
2. `MODEL_POLICY.json` → `fast_smart` (or whatever the next tier is)

### Suggested files (cover world + campaign + session recap)

```
corpus/eldyrwild-markdown/Elderwyld/Cities and Towns/Mirathorn/The City of Mirathorn.md
corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/Longmont Campaign General Notes.md
corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/Session Recaps/Session 6 - The Road to Miraholm.md
```

### Metrics to compare

| Metric | How to measure |
|--------|---------------|
| Entity type distribution | `entity_type` counts from `stage_entities.json` — % npc/location/faction/item/other |
| Entity name quality | Count of entities blocked by hygiene filters (with filters temporarily disabled or logged) |
| Entity count | Total unique entities per file |
| Fact count | Total facts per file |
| Temporal fill | % of campaign facts with `asserted_in_session` non-null |
| Token cost | Total tokens (input + output) per file — log from API calls |
| Gold score | Run `score_gold.py --eval-mode full_ingest` against outputs for the 2 gold source files |

### How to run

```bash
# 1. Create two separate stores
mkdir -p /tmp/ab_nano /tmp/ab_smart

# 2. Ingest with nano (current default)
uv run python -m src ingest \
  --store /tmp/ab_nano \
  --file "corpus/eldyrwild-markdown/Elderwyld/Cities and Towns/Mirathorn/The City of Mirathorn.md" \
  --layer world

# 3. Change MODEL_POLICY.json structured_generation to fast_smart, repeat
# 4. Compare stage_entities.json / stage_facts.json from each store
```

### Where MODEL_POLICY.json lives

```
/home/drakosfire/Projects/DungeonOverMind/MODEL_POLICY.json
```

This is at the **monorepo root**, not inside `DungeonMindBuddy/`. The `structured_generation` key routes to `cheapest` → `gpt-5.4-nano`. Changing this to the next tier for the comparison, then reverting, is the simplest approach.

### Output

Write a short comparison report to `evals/MODEL_AB_COMPARISON.md` with the metrics table. This informs whether to invest in prompt engineering (if both models struggle) or just use a better model (if mid-tier solves it).

---

## 3. Remaining gaps (context, not action for this handoff)

| Gap | Status | Next step |
|-----|--------|-----------|
| Gap 1: Temporal quality | Infrastructure built (Gate TW reports `sequence_only_ratio`). No enforcement threshold set. | Needs real full-ingest data to calibrate. Blocked on model A/B decision. |
| Gap 3: Cache invalidation | Manual `_PROMPT_ID` bump discipline. No tooling. | Low urgency. Could add a CI check that prompt text hash matches `_PROMPT_ID`, but not critical. |
| Gap 4: Validity fields | `valid_from_session`, `valid_to_session`, `validity_state` in schema only. Not populated by any code. | Deferred. These fields matter for multi-session temporal projection, which isn't implemented yet. |

---

## 4. Key file index

| Area | Path |
|------|------|
| Model policy | `/home/drakosfire/Projects/DungeonOverMind/MODEL_POLICY.json` |
| CLI ingest entry | `src/cli.py` → `ingest` subcommand |
| Entity extractor | `src/ingestion/entity_extractor.py` |
| Fact extractor | `src/ingestion/fact_extractor.py` |
| Store | `src/store.py` |
| Gold scorer | `evals/llm_ingestion_slice/score_gold.py` |
| Gold contract | `evals/llm_ingestion_slice/gold/manual_entity_extraction_gold.json` |
| Run slice | `evals/llm_ingestion_slice/run_slice.py` |
| Batch ingest tool | `tools/batch_ingest_corpus.py` |
| Temporal contracts | `src/contracts/temporal_tick_gate.py` |
| Entity tags | `src/contracts/entity_tags.py` |
| Frontmatter | `src/ingestion/frontmatter.py` |
| Completed gold handoff | `evals/HANDOFF-gold-scoring-eval.md` |
| Temporal gates handoff | `evals/HANDOFF-next-agent-ingestion-temporal-gates.md` |
