# Research Brief: Entity Taxonomy Design for TTRPG Knowledge Extraction

**Date:** 2026-04-03  
**Audience:** Research and design agent  
**Purpose:** Design a better entity taxonomy for LLM-driven extraction from TTRPG worldbuilding documents. The current taxonomy produces a ~27% "other" entity rate and models struggle with classification even when escalated to stronger models.

---

## 1. The problem

We extract named entities from TTRPG worldbuilding documents (session recaps, world references, NPC dossiers, item cards, encounter tables, cultural docs) using LLM structured output. Each entity gets classified on two axes:

- **`entity_type`** (5 values): `npc`, `location`, `faction`, `item`, `other`
- **`entity_kind`** (8 values): `actor`, `group`, `place`, `object`, `event`, `concept`, `document_anchor`, `unknown`

Plus optional **`semantic_facets`** from a controlled vocabulary of ~22 tokens (deity, species, festival, ritual, theme, plot_hook, document_section, etc.) and a `domain:*` namespace for campaign-specific extensions.

The LLM assigns `entity_type` and `entity_kind` directly. When `entity_type=other` and `entity_kind` is missing, post-processing infers `entity_kind` from facets (e.g. festival facet → event kind).

### What's going wrong

From a full 130-file corpus ingest (7,667 entities total):

| entity_type | Count | % |
|-------------|------:|----:|
| other | 2,075 | 27.1% |
| item | 1,799 | 23.5% |
| npc | 1,731 | 22.6% |
| location | 1,635 | 21.3% |
| faction | 427 | 5.6% |

| entity_kind | Count | % |
|-------------|------:|----:|
| object | 1,859 | 24.2% |
| actor | 1,637 | 21.4% |
| place | 1,614 | 21.1% |
| concept | 1,275 | 16.6% |
| group | 572 | 7.5% |
| event | 379 | 4.9% |
| document_anchor | 323 | 4.2% |
| unknown | 8 | 0.1% |

Of the 2,075 `other` entities:
- 1,250 (60%) are `concept` kind
- 374 (18%) are `event` kind
- 298 (14%) are `document_anchor` kind
- 271 (13%) have **no semantic facets at all**

Top facets on `other` entities:
| Facet | Count | Typical `entity_kind` |
|-------|------:|----------------------|
| theme | 770 | concept |
| document_section | 409 | document_anchor |
| plot_hook | 336 | concept / event |
| festival | 160 | event |
| conflict | 141 | event / concept |
| ritual | 106 | concept |
| creature_species | 79 | concept / actor |

### Concrete examples of what falls into "other"

**No-facet "other" entities (should not be entities at all):**
`candlelight`, `roots`, `water`, `light`, `breath`, `smoke`, `students`, `cages`, `rune`, `message`

**Mechanical/rules text extracted as entities:**
`Dexterity save (DC 12)`, `Athletics check (DC 13)`, `Insight`, `Failure results in 1d8 necrotic damage`, `Charisma (Performance) check`, `Mage Hand`, `Invisibility`

**Document structure extracted as entities:**
`Tilly Tuffcrust's Tastings`, `Executive DM Summary (Read Before Play)`, `Branching Paths After the Fight`, `First Step Inside`, `The Immediate Reaction`, `Within minutes`, `Nothing blocks the party outright`

**Actual narrative things that should be typed better:**
`Maelthor` (patron deity → should be npc or a new type), `Festival of Expansion` (named event), `The Protest` (plot event), `Shepherd's rise` (plot arc)

### The escalation experiment result

Escalating 40 flagged files from `gpt-5.4-mini` to `gpt-5.4` (strongest model) made taxonomy **worse**:
- `other_rate`: 36.9% → 42.5% (+5.5pp)
- `other_missing_facets_rate`: 8.4% → 23.6% (+15.2pp)
- Pairwise: taxonomy improved on only 9/40 files, worsened on 30/40

This means the problem is **not model capability** — it's the taxonomy definition and prompt design.

---

## 2. Questions for the research agent

### Core taxonomy design question

**How should entity types be structured for LLM-driven extraction from heterogeneous TTRPG documents, given these constraints?**

1. The taxonomy must work across document types: session recaps (narrative), world references (encyclopedic), NPC dossiers (character sheets), item cards (mechanical stat blocks), encounter tables (lists), cultural/event docs (ceremonial/festival descriptions).

2. The LLM sees one evidence chunk at a time (a paragraph or section), not the full document. It must classify from limited context.

3. The taxonomy must be stable across models of different capability levels (nano through frontier).

4. The taxonomy serves downstream retrieval and synthesis: a GM asks "what happened at the gate?" and the system needs to find entities relevant to that query and compose a narrative answer.

### Specific sub-questions

**A. Is `entity_type` vs `entity_kind` redundant or complementary?**

Currently `entity_type` has 5 values and `entity_kind` has 8 values. They partially overlap (`npc`↔`actor`, `location`↔`place`, `faction`↔`group`, `item`↔`object`). The only value `entity_kind` adds over `entity_type` is distinguishing `concept`, `event`, and `document_anchor` — all of which currently collapse into `entity_type=other`.

Should we:
- Merge them into a single axis with more values?
- Keep both but with clearer separation of concerns?
- Replace `entity_type` with `entity_kind` entirely and use facets for what `entity_type` currently captures?

**B. What should happen with "concept" entities?**

1,275 entities are classified as `entity_kind=concept`. Many are legitimate (named rituals, cosmology concepts, political doctrines). Many are noise (generic words like "light", "breath", "smoke"). How should the taxonomy handle:
- Named abstract concepts that are retrievable ("The Doctrine of the Shepherds")
- Generic thematic words that aren't real entities ("light", "storms")
- Game mechanics that aren't narrative entities ("DC 12 save", "Mage Hand")

**C. Should document structure be entities?**

323 entities are `document_anchor` kind. These are section headings or structural markers extracted as entities. Examples: "Executive DM Summary", "Branching Paths After the Fight". Are these useful for retrieval, or should the prompt explicitly exclude them?

**D. How should the prompt handle the boundary between "entity" and "not an entity"?**

The current prompt says: "Include proper names and durable named concepts that matter for retrieval across sessions. DO NOT output full-sentence fragments, generic prose phrases, or purely descriptive clauses." But models still extract `candlelight`, `water`, `roots`, `smoke`, `students` as entities. What framing produces better extraction boundaries?

**E. Should the taxonomy be domain-aware (TTRPG-specific) or generic?**

Current types (npc, location, faction, item) are TTRPG-specific. Would a more generic ontology (person, place, organization, object, event, concept) work better for LLM classification, with TTRPG semantics applied via facets?

**F. What's the right size for a type enum that LLMs classify reliably?**

Research suggests LLMs classify more accurately into smaller enums (5-7 values) than larger ones (15+). But 5 types with "other" as a catch-all produces 27% other. What's the sweet spot?

---

## 3. What we need as output

A taxonomy recommendation document that includes:

1. **Proposed type/kind structure** — how many axes, what values, clear definitions with TTRPG examples
2. **Boundary criteria** — what IS an entity vs what is NOT (with examples from the problem cases above)
3. **Facet vocabulary** — which facets to keep, add, or remove; how facets relate to types
4. **Prompt design guidance** — how to instruct the LLM to apply the taxonomy (including negative examples)
5. **Migration path** — how to get from the current 3-axis system (type + kind + facets) to the new one without breaking existing data
6. **Testable success criteria** — what "other" rate is acceptable, what the facet coverage target should be

---

## 4. Current system context

### Files to read for full understanding

| File | What it contains |
|------|-----------------|
| `src/ingestion/entity_extractor.py` lines 454-481 | The current extraction prompt (taxonomy instructions) |
| `src/contracts/entity_taxonomy.py` | `EntityKind` literal, `ALLOWED_SEMANTIC_FACETS` set, `normalize_semantic_facets()` |
| `schemas/v0.1/entity.schema.json` | Full entity schema with `entity_type`, `entity_kind`, `semantic_facets` |
| `src/contracts/entity_tags.py` | Legacy `entity_tags` normalizer (being replaced by `semantic_facets`) |
| `evals/AUTO_ESCALATION_FULL_CORPUS_REPORT.md` | Full escalation experiment results |
| `evals/llm_ingestion_slice/gold/manual_entity_extraction_gold.json` | Human-authored entity expectations (13 segments, ~30 entities) |

### Downstream consumers of entity type/kind

- **Context formatter** (`src/agent/context_formatter.py`): Displays `== Entity: Name (type) [facets] ==` in synthesis context
- **Canon projection** (`src/reducer/canon_projection.py`): Groups facts by entity for state projection
- **Retrieval**: Entity type/kind is used for filtering relevant entities during question answering
- **Merge policy** (`src/store.py`): Entities are merged by name; type/kind inform merge compatibility
