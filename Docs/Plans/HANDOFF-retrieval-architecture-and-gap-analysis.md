# HANDOFF: Retrieval Architecture & Gap Analysis

**Date:** 2026-04-08  
**Status:** Ready for next agent  
**Scope:** End-to-end QA pipeline — ingestion through synthesis  
**Benchmark:** 15-question council room set, `gpt-5.4-nano` planner, `gpt-5.3-chat-latest` synthesis  

---

## 1. Current Architecture

```
Markdown docs
  │
  ▼
┌──────────────────┐
│  Chunker          │  chunk_document() → evidence_units (blake3-hashed)
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Entity Extractor │  LLM pass 1: evidence_units → entities (with dedupe)
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Fact Extractor   │  LLM pass 2: evidence_units + entities → facts
└────────┬─────────┘       (attribute from fixed enum, truth_state derived)
         │
         ▼
┌──────────────────┐
│  FactStore        │  JSON-backed: evidence_units, entities, facts,
│                   │  canon_decisions, event_records, claims, ingest_index
└────────┬─────────┘
         │  store.project(campaign_id)
         ▼
┌──────────────────┐
│  Canon Projection │  Layers facts by authority/session/sequence,
│                   │  resolves conflicts, picks selected fact per attribute
└────────┬─────────┘
         │  projection dict: {entities: {eid: {attributes: {...}}}}
         ▼
┌──────────────────┐
│  Retriever        │  Stage 1: keyword + name match (~50-70 entities)
│  (retriever.py)   │  Optional: embedding search, graph expansion
└────────┬─────────┘
         │  ranked: [(entity_id, score), ...]
         ▼
┌──────────────────┐
│  Query Planner    │  Stage 2: LLM triage (~5-15 entities + attribute focus)
│  (query_planner)  │  Model: gpt-5.4-nano (from MODEL_POLICY.json)
└────────┬─────────┘
         │  QueryPlan: selected_entity_ids, relevant_attributes
         ▼
┌──────────────────┐
│  filter_projection│  Subsets projection to planner's selections
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Context Formatter │  Renders entities → text with truth states,
│                   │  conflict annotations, scope markers
└────────┬─────────┘
         │  formatted_context string (~4-14K chars with planner)
         ▼
┌──────────────────┐
│  Synthesis LLM    │  gpt-5.3-chat-latest (from MODEL_POLICY.json)
│  (synthesis.py)   │  System prompt: TL;DR first, cite truth states,
│                   │  terminal outcome rule, Key Attributes section
└──────────────────┘
```

### Model policy reference

All models resolve through `/home/drakosfire/Projects/DungeonOverMind/MODEL_POLICY.json`:


| Action            | Policy key                           | Model                 |
| ----------------- | ------------------------------------ | --------------------- |
| Query planning    | `query_planning` → `cheapest`        | `gpt-5.4-nano`        |
| Synthesis         | `retrieval_synthesis`                | `gpt-5.3-chat-latest` |
| Entity extraction | `structured_generation` → `cheapest` | `gpt-5.4-nano`        |
| Fact extraction   | `structured_generation` → `cheapest` | `gpt-5.4-nano`        |


---

## 2. Ingestion Pipeline Detail

### 2.1 Chunker (`src/ingestion/chunker.py`)

- Converts markdown (or DOCX via converter) into **evidence units**
- Each unit = one paragraph with metadata: `document_id`, `source_class`, `canon_layer`, `campaign_id`, `section_path`, `source_order_index`, `inferred_session`
- Evidence IDs are blake3 hashes of (document_id + section_path + text)
- Heading text is absorbed into the first child paragraph
- Very short units merged (`min_chars=50`)
- Validated against `evidence_unit.schema.json`

### 2.2 Entity Extractor (`src/ingestion/entity_extractor.py`)

- LLM pass 1 over evidence units
- Two lanes: **standard** (worldbuilding docs) and **recap** (session recap → also extracts `event_records` + `claims`)
- Structured output via OpenAI `responses.parse`
- Post-filters: `_is_plausible_entity_name` removes hallucinated/junk entities
- Disk cache keyed by blake3(text + prompt_id + model + profile)
- Dedupe via temporary FactStore merge (normalized name overlap + class check)
- Entity schema: `entity_id`, `entity_class`, `display_name`, `aliases`, `subtype_facets`, `semantic_facets`, `narrative_tags`, `entity_tags`

### 2.3 Fact Extractor (`src/ingestion/fact_extractor.py`)

- LLM pass 2: requires entity list from pass 1
- Each fact = `(entity_id, attribute, value)` where attribute is from a **fixed enum**:
`atmosphere, current_location, defenses, demographics, economy, geography, goals, history, loyalty_or_alignment_context, mental_state, notable_abilities, operational_status, physical_condition, portrayal_notes, relationship_tags, role, species`
- Truth state derived from `(canon_layer, source_class)`: CANON, PREP, OBSERVED
- Scopes prompt to entities mentioned in each evidence unit's text
- Deduplication by compaction key
- Session/sequence metadata from evidence unit

### 2.4 FactStore (`src/store.py`)

- JSON files under `store_dir`: `evidence_units.json`, `entities.json`, `facts.json`, `canon_decisions.json`, `event_records.json`, `claims.json`
- Entity merge: normalized name overlap with class compatibility check, audit log
- `project(campaign_id)` delegates to `canon_projection.py`:
  - Groups facts by (entity_id, attribute)
  - Applies canon decisions (explicit `selected_fact_ids`)
  - Resolves conflicts via ordering: session/sequence, truth state priority (OBSERVED > CANON), terminal-outcome phrases
  - Output: `{entities: {eid: {attributes: {attr: {value_label, truth_state, ...}}}}}`

---

## 3. Retrieval Pipeline Detail

### 3.1 Retriever (`src/agent/retriever.py`)

Multi-signal search over the projected graph:


| Signal         | Method                                             | Weight                 |
| -------------- | -------------------------------------------------- | ---------------------- |
| **Name match** | Entity name/alias substring in question            | `name_boost=1.0`       |
| **Keyword**    | BM25-style IDF over tokenized entity summaries     | `keyword_weight=0.5`   |
| **Embedding**  | Cosine similarity (optional, `pplx-embed-v1-0.6B`) | `embedding_weight=0.3` |


Entity summaries: built from display_name + class + facets + aliases + non-noise fact labels. Noise filtering excludes `source_comments`, `unresolved_questions`, and labels starting with "Not mentioned", "No direct assertion", etc.

Graph expansion:

- `_expand_via_relationships`: follows `relationship_tags` to connected entities
- `_expand_via_shared_evidence`: finds entities sharing `provenance_evidence_ids`

Default `top_k=30`, expanded results typically 50-75 entities.

### 3.2 Query Planner (`src/agent/query_planner.py`)

LLM triage of retriever candidates:

- Builds compact **entity roster**: one line per candidate with entity_id, name, class, top 3-4 attribute summaries (~12K chars for 60 entities)
- System prompt instructs: select 5-20 entities, pick 2-6 relevant attribute types
- JSON output: `{selected_entity_ids, relevant_attributes, reasoning}`
- Fallback on error/empty/no API key → returns all candidates (graceful degradation)
- `filter_projection` applies both entity and attribute filtering

### 3.3 Context Formatter (`src/agent/context_formatter.py`)

Renders filtered projection as text:

- Per entity: `== Entity: Name (class) [tags] {facets} ==`
- Per attribute: value label + `[truth_state, from: layer/campaign/source_class/fact_id]`
- Optional CONFLICTS block when multiple facts compete
- Optional scope annotations (in_scope / unknown / out_of_scope)
- `MAX_ENTITIES=200` cap (pre-retrieval safety net)

### 3.4 Synthesis (`src/agent/synthesis.py`)

System prompt rules:

- Answer from projection context ONLY
- Distinguish CANON / PREP / OBSERVED
- TL;DR first (1-2 sentences)
- Cite entity names
- 100-200 words target
- **Terminal outcome rule**: copy phrases like "killing blow", "decapitated" verbatim
- Key Attributes section when relevant attributes present

---

## 4. Benchmark Results (Latest Run)

**Pipeline:** Retriever (top_k=30) → Planner (gpt-5.4-nano) → Synthesis (gpt-5.3-chat-latest)


| Metric                 | Value          |
| ---------------------- | -------------- |
| Strict pass            | 4/15 (27%)     |
| Semantic pass          | **8/15 (53%)** |
| Stale                  | 0              |
| Errors                 | 0              |
| Avg entities (planner) | 11.1           |
| Avg context chars      | 9,581          |
| Avg planner latency    | 2,135ms        |


### 4.1 Per-Question Results


| #   | Question                  | Strict   | Semantic | Planner ents | Context | Root cause                                      |
| --- | ------------------------- | -------- | -------- | ------------ | ------- | ----------------------------------------------- |
| 1   | Emergency meeting + catch | fail     | **pass** | 16           | 12.9K   | Token: `tradeoff` not in answer                 |
| 2   | Session 12 roster         | fail     | fail     | 12           | 11.2K   | **Retriever gap**: PC entities not surfaced     |
| 3   | Shepherds + god           | **pass** | **pass** | 5            | 4.8K    | —                                               |
| 4   | Wizard council rep        | **pass** | **pass** | 11           | 10.3K   | —                                               |
| 5   | Merril/Torrin/Rurik       | **pass** | **pass** | 11           | 10.2K   | —                                               |
| 6   | Wolf outcome              | fail     | **pass** | 8            | 4.9K    | **Temporal**: escape vs death conflict          |
| 7   | Thalia corruption type    | fail     | fail     | 8            | 9.6K    | Token: `not fully corrupted` exact phrase       |
| 8   | Room hazards              | fail     | fail     | 11           | 7.7K    | **Content gap**: `alarm pulses` absent          |
| 9   | Trust Thalia              | fail     | **pass** | 12           | 10.0K   | Token: `guard operations` exact phrase          |
| 10  | Inaction consequences     | fail     | fail     | 11           | 9.5K    | Token: `countdown`, `consequences`              |
| 11  | Room after fight          | fail     | fail     | 15           | 11.4K   | **Content gap**: `chandelier`, `secret passage` |
| 12  | Room changes              | fail     | fail     | 15           | 14.1K   | **Content gap**: `chandelier`, `secret passage` |
| 13  | Wolf status end S12       | fail     | **pass** | 9            | 9.3K    | Token: `oily sheen fades` (has `oily sheen`)    |
| 14  | Before vs after Wolf      | fail     | fail     | 14           | 9.7K    | **Temporal**: escape narrative, no kill         |
| 15  | Thalia ensorcelled        | **pass** | **pass** | 8            | 8.1K    | —                                               |


---

## 5. Gap Analysis — Five Root Causes

### 5.1 Temporal / Conflict Resolution Inconsistency

**Evidence:** In the same benchmark run, Q6 says the Wolf **escaped** while Q13 correctly says he's **dead/decapitated**. Both questions hit the same store and projection.

**Root cause:** The projection contains multiple OBSERVED snapshots at different points in the session timeline. The canon projection resolver picks a "selected" fact per attribute, but the outcome depends on which entity/attribute slice the planner surfaces. When the planner selects `ent_the_wolf` with `[goals, operational_status, defenses]`, escape facts dominate. When it selects `ent_the_wolf` with `[operational_status, physical_condition]`, the terminal decapitation surfaces.

**Affected questions:** Q6 (aftermath_1), Q14 (pre_post)

**Fix direction:** The projection resolver's temporal ordering logic needs to more aggressively promote terminal-outcome facts. The system prompt's "terminal outcome rule" only works if the terminal fact reaches the context — the retriever/planner must ensure terminal facts are never filtered out.

### 5.2 Retriever Not Surfacing Key Entities

**Evidence:** Q2 (roster) needs PC names (Bonogo, Caelynn, Ephanna) but the retriever's top-5 are event/place entities. PC entities either have low BM25 scores or aren't name-matched because the question says "who's in the chamber" not "Bonogo."

**Root cause:** Entity summaries for PCs may be thin (few facts, generic labels). The retriever's keyword search finds "council chamber" and "fight" entities but not PCs whose summaries don't contain those terms.

**Affected questions:** Q2 (roster), Q8 (room hazards — `ent_grobnok_the_goblin` ranks above room defence entities)

**Fix direction:** 

- Enrich PC entity summaries (add session-specific location/event context)
- Add a "question entity extraction" step: if the question mentions a fight, auto-include entities whose facts reference that event's evidence units
- Consider bidirectional expansion: if the battle entity mentions PCs, include them

### 5.3 Attribute Filter Dropping Facts

**Evidence:** Prior run with `gpt-4o-mini` returned `portray_notes` (typo) instead of `portrayal_notes`, silently excluding that attribute. Current run with `gpt-5.4-nano` improved but the risk remains structural.

**Root cause:** The planner's attribute selection is a free-text field. The system prompt lists the 17 valid attribute names, but the LLM can misspell or pick an invalid name. `filter_projection` does strict set-membership checks.

**Affected questions:** Previously Q11 (arch_current) — currently less impactful with better model

**Fix direction:**

- Validate/fuzzy-match planner attribute names against the known enum before filtering
- Consider making attribute filtering opt-in rather than default (entity selection alone provides most of the context reduction)

### 5.4 Token Vocabulary Mismatch (Scoring System)

**Evidence:** Multiple questions where the answer contains the correct concept but different words:

- "magical lockdown" vs `arcane lockdown` (Q1, but semantic equiv covers this)
- "each round builds" vs `countdown` (Q10)
- "unreliable actor under influence" vs `uncertain reliability` (Q9)
- "not corrupted like the guards" vs `not fully corrupted` (Q7)

**Root cause:** The strict scorer requires exact substring matches. Semantic equivalences cover some cases but not all.

**Affected questions:** Q1, Q7, Q9, Q10, Q13

**Fix direction:** 

- Expand `semantic_equivalences` in `gold_questions.json` for known paraphrase patterns
- Consider embedding-based scoring as the primary accuracy metric rather than token matching
- Review whether strict scoring is measuring retrieval quality or synthesis vocabulary

### 5.5 Content Gaps in the Fact Store

**Evidence:** Q8 expects `alarm pulses` — the answer covers runes, wards, debris, illusory walls but never mentions alarm pulses. Q11/Q12 expect `floating chandelier` and `secret passage` but these never appear in any answer despite 15 entities and 14K chars of context.

**Root cause:** Either (a) these details were never ingested from the source documents, (b) they were ingested but assigned to entities/attributes the retriever doesn't surface, or (c) the ingestion prompts didn't extract them.

**Affected questions:** Q8 (alarm pulses), Q11 (chandelier, arched ceilings, secret passage), Q12 (chandelier, secret passage)

**Fix direction:**

- **Audit the source documents** against gold questions to determine if these details exist in the corpus
- grep the fact store for `chandelier`, `alarm`, `secret passage`, `arched ceilings` to determine if they're ingested but not retrieved
- If not ingested: re-examine chunker boundaries and extraction prompts
- If ingested but not retrieved: trace which entity/attribute they live on and why retrieval missed it

---

## 6. Key Files


| File                                                                 | Purpose                                        |
| -------------------------------------------------------------------- | ---------------------------------------------- |
| `src/ingestion/chunker.py`                                           | Markdown → evidence units                      |
| `src/ingestion/entity_extractor.py`                                  | Evidence units → entities (LLM pass 1)         |
| `src/ingestion/fact_extractor.py`                                    | Evidence units + entities → facts (LLM pass 2) |
| `src/store.py`                                                       | FactStore: persistence + `project()`           |
| `src/reducer/canon_projection.py`                                    | Fact conflict resolution + projection          |
| `src/agent/retriever.py`                                             | Multi-signal entity retrieval + EntityIndex    |
| `src/agent/query_planner.py`                                         | LLM entity/attribute triage                    |
| `src/agent/context_formatter.py`                                     | Projection → text for LLM                      |
| `src/agent/synthesis.py`                                             | System prompt + LLM answer generation          |
| `src/agent/scope_relevance.py`                                       | Document/entity scope filtering                |
| `src/contracts/entity_taxonomy.py`                                   | Entity classes, facets, tags                   |
| `src/cli.py`                                                         | CLI orchestration (`_cmd_ask`)                 |
| `evals/mirathorn_vertical_slice/run_council_room_question_set.py`    | Benchmark runner                               |
| `evals/mirathorn_vertical_slice/gold/gold_questions.json`            | Gold question definitions                      |
| `evals/mirathorn_vertical_slice/output/council_room_question_set.md` | Latest results                                 |
| `evals/mirathorn_vertical_slice/output/council_room_trace.jsonl`     | Per-question trace log                         |


---

## 7. Recommended Investigation Order

### Phase A: Fact Store Audit (no code changes)

Determine which failures are content gaps vs retrieval gaps:

```bash
# Check if chandelier/secret passage/alarm facts exist in the store
uv run python -c "
from src.store import FactStore; from pathlib import Path
s = FactStore(Path('evals/mirathorn_vertical_slice/output/phase_d_store'))
s.load()
for f in s.facts:
    label = f.get('value', {}).get('label', '')
    if any(t in label.lower() for t in ['chandelier', 'alarm pulse', 'secret passage', 'arched ceiling']):
        print(f['entity_id'], f['attribute'], label[:120])
"
```

If facts exist → retrieval gap. If facts don't exist → ingestion gap. This determines whether to fix retrieval or re-ingest.

### Phase B: Temporal Resolution (projection layer)

The projection resolver's `selected_fact_id` per attribute should always prefer terminal-outcome facts when they exist. The `canon_projection.py` fact ordering logic is the place to enforce this. Verify:

- Does the ordering already check for terminal phrases?
- When both "escape" and "decapitated" OBSERVED facts exist for `operational_status`, which wins?
- Should the system tag terminal-outcome facts at ingestion time for deterministic resolution?

### Phase C: Retriever Improvements

1. **PC entity surfacing**: For "who is present" questions, entities connected via shared `provenance_evidence_ids` to event entities should be boosted
2. **Retrieval noise**: Audit why `ent_grobnok_the_goblin` and `ent_the_city` rank above room-specific entities for hazard questions — likely keyword overlap on common terms
3. **Entity summary enrichment**: Thin entity summaries (few facts, generic labels) rank poorly in keyword search

### Phase D: Planner Attribute Validation

Add fuzzy matching for planner-returned attribute names:

```python
VALID_ATTRIBUTES = {"atmosphere", "current_location", "defenses", ...}
def _normalize_attribute(raw: str) -> str | None:
    if raw in VALID_ATTRIBUTES: return raw
    # fuzzy: "portray_notes" → "portrayal_notes"
    for valid in VALID_ATTRIBUTES:
        if raw in valid or valid in raw: return valid
    return None
```

### Phase E: Gold Question Rubric Refinement

Several failures are scoring artifacts, not retrieval problems:

- Expand `semantic_equivalences` for known paraphrase patterns
- Add equivalences for `countdown` → `builds each round`, `timer`
- Add equivalences for `consequences` → `risk`, `danger increases`
- Consider whether strict scoring should be deprecated in favor of semantic + embedding

---

## 8. Environment & Commands

```bash
# Run benchmark (planner enabled)
DMB_PLANNER=1 DMB_WRITE_COUNCIL_ROOM_QUESTION_SET_ARTIFACTS=1 \
  uv run python evals/mirathorn_vertical_slice/run_council_room_question_set.py

# Run benchmark (retriever only, no planner)
DMB_WRITE_COUNCIL_ROOM_QUESTION_SET_ARTIFACTS=1 \
  uv run python evals/mirathorn_vertical_slice/run_council_room_question_set.py

# Run benchmark (no retrieval, full context baseline)
DMB_RETRIEVAL=0 DMB_WRITE_COUNCIL_ROOM_QUESTION_SET_ARTIFACTS=1 \
  uv run python evals/mirathorn_vertical_slice/run_council_room_question_set.py

# Run tests
uv run pytest tests/test_retriever.py tests/test_query_planner.py tests/test_cli.py -v

# Interactive CLI
uv run python -m src.cli --store evals/mirathorn_vertical_slice/output/phase_d_store
# then: ask "your question" --campaign longmont-c1 --planner
```

