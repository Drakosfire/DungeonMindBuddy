# Handoff: Relevance-Gated Retrieval and Pruning Candidacy

**Date:** 2026-04-06  
**Status:** READY  
**Priority:** HIGH  
**Origin:** Phase 6 benchmark question review — Elric Vane is fully answerable but narratively irrelevant to battle scenes. The benchmark should detect and penalize this, and the architecture should support it.

---

## 1) The Problem This Solves

Commander Elric Vane has 4 facts in the store (rank, goals, cult coordination). When a GM asks "Catch me up on the council room battle," the context formatter ranks entities by fact count and includes Elric Vane — even though he never appears in that scene. He was mentioned in campaign notes, not the battle document.

This is worse than a missing entity. It's **actively misleading context** that wastes synthesis token budget and can cause the LLM to fabricate connections between Elric Vane and the battle.

The same problem exists for any entity whose facts come entirely from documents unrelated to the current query scope. The store currently has no mechanism to express "this entity exists but is irrelevant to this scene."

---

## 2) What "Relevance" Means Here

Every fact in the store has `evidence_ids`. Every evidence unit has a `document_id` (derived from the source file path). This chain already exists:

```
question/query scope
  → documents in scope (by topic, scene, campaign context)
    → evidence units from those documents
      → facts linked to those evidence units
        → entities that are subjects of those facts
```

An entity is **scene-relevant** if at least one of its facts traces back to an evidence unit from a document in the query scope.

An entity is **scene-irrelevant** if all of its facts trace to evidence units from documents outside the query scope.

This is not fuzzy. It's a deterministic set intersection: `entity_evidence_document_ids ∩ query_scope_document_ids`.

---

## 3) Current Architecture (What Exists)

### Evidence → Fact linkage (already present)

Every fact has `evidence_ids`:

```json
{
  "fact_id": "fact_commander_elric_vane_rank_or_title_6b606b2e1610",
  "subject_entity_id": "ent_commander_elric_vane",
  "evidence_ids": ["eu_doc_longmont_campaign_general_notes_chunk_003"],
  ...
}
```

### Projection → Provenance (already present)

The reducer emits `provenance_evidence_ids` per projected attribute:

```python
# src/reducer/canon_projection.py
"provenance_evidence_ids": sorted(
    {evidence_id for entry in entries for evidence_id in entry.fact["evidence_ids"]}
),
```

### Context formatting (no relevance awareness)

`format_projection_context` ranks entities by fact count only:

```python
# src/agent/context_formatter.py
ordered = sorted(
    projection_entities.items(),
    key=lambda item: _entity_fact_count(item[1]),
    reverse=True,
)
```

There is no concept of "which documents are relevant to this query" and no filtering or reranking based on evidence provenance.

---

## 4) Two Complementary Capabilities

### 4A: Relevance-Gated Retrieval

**Goal:** When building synthesis context, deprioritize or exclude entities whose facts have zero evidence overlap with the query scope.

**Mechanism:** Before ranking entities for context, compute each entity's **scope overlap score**:

```
entity_document_ids = {doc_id(eu) for eu in evidence_units 
                       where eu.evidence_id in entity.all_evidence_ids}

scope_document_ids = {doc_id for doc_id in query_scope_documents}

overlap = len(entity_document_ids & scope_document_ids) / len(entity_document_ids)
```

Three buckets:

- `overlap > 0`: entity has at least one fact from an in-scope document → include, rank normally
- `overlap == 0`: entity has facts but none from in-scope documents → **deprioritize or exclude**
- Entity has no facts at all → already handled (shown as "no projected attributes")

**Where it lives:** `src/agent/context_formatter.py`, either as a filter before ranking or as a secondary sort key after fact count.

**Query scope definition:** This is the design question. Options:

- Explicit document list (passed as argument to `format_projection_context`)
- Inferred from the question text (entity name mentions, keyword matching against document titles)
- Campaign-scoped (all documents in the active campaign)
- Full store (no filtering — current behavior, backward compatible)

### 4B: Pruning Candidacy Signal

**Goal:** Surface a per-entity metadata signal: "this entity may not be relevant to the active scope and could be a candidate for deprioritization or pruning."

**Mechanism:** Add a computed field to the projection or entity metadata:

```json
{
  "entity_id": "ent_commander_elric_vane",
  "scope_relevance": {
    "in_scope_document_count": 0,
    "total_evidence_count": 4,
    "in_scope_document_ids": [],
    "all_document_ids": ["doc_longmont_campaign_general_notes"],
    "pruning_candidate": true
  }
}
```

This is not automatic deletion. It's a **signal** that:

- The context formatter can use for ranking/exclusion
- The benchmark can validate (assert that pruning candidates are not in the top-N context for a scoped query)
- A future GM-facing UI could surface as "these entities exist in your world but aren't relevant to this scene"

---

## 5) Benchmark Surface: How to Prove This Works

### Benchmark Gate: Scope Precision

For a scoped query (e.g., "Catch me up on the council room battle"), the benchmark asserts:

1. **No irrelevant entities in top context:** Entities with `overlap == 0` to the battle document should not appear in the formatted context.
2. **Relevant entities are present:** Entities with `overlap > 0` (The Wolf, Council Room, Thalia, etc.) should appear.
3. **Pruning candidates are flagged:** The `scope_relevance` metadata correctly identifies out-of-scope entities.

### Concrete test case (Elric Vane):

```json
{
  "id": "q_battle_scope_elric_vane_exclusion",
  "question": "Catch me up on the council room battle",
  "scope_documents": ["doc_battle_with_the_wolf_and_aftermath"],
  "must_include_entities": ["ent_the_wolf", "ent_council_room"],
  "must_exclude_entities": ["ent_commander_elric_vane"],
  "gate": "scope_precision"
}
```

This is a new gate type — not scoring prose answers, but scoring context assembly. It validates the architecture, not the LLM.

---

## 6) Implementation Plan

### Phase A — Evidence provenance index (data layer)

Build a lookup from entity_id → set of document_ids, derived from fact evidence_ids → evidence_unit document_ids.

1. Add `_build_entity_document_index(entities, facts, evidence_units) -> dict[str, set[str]]` to `context_formatter.py` or a new `src/agent/scope.py`.
2. Unit test: given fixture entities/facts/evidence, the index correctly maps entity_id to document_id sets.

No changes to the store schema. This is a computed view.

### Phase B — Scope overlap scoring

1. Add `compute_scope_relevance(entity_id, entity_doc_index, scope_doc_ids) -> ScopeRelevance` that returns overlap ratio and pruning_candidate flag.
2. Add `scope_doc_ids: set[str] | None` parameter to `format_projection_context`. When `None`, no filtering (backward compatible). When provided, compute overlap for each entity.
3. Reorder entities: in-scope first (by fact count), then out-of-scope (deprioritized or excluded based on a configurable policy).
4. Unit test: Elric Vane is excluded from context when scope is set to battle document. Wolf and Council Room are retained.

### Phase C — Projection metadata enrichment

1. When projecting, optionally compute and attach `scope_relevance` to each entity in the projection output.
2. This makes the signal available to downstream consumers (CLI, future UI, benchmarks).
3. Test: projection output for a scoped query includes `scope_relevance` metadata.

### Phase D — Benchmark gate implementation

1. Add a new gate type (`scope_precision`) to the evaluation harness.
2. Gate checks:
  - `must_include_entities` appear in formatted context
  - `must_exclude_entities` do not appear in formatted context
  - `pruning_candidates` list matches expected set
3. Create 3-5 scope precision test cases using known entities:
  - Elric Vane excluded from battle scope
  - Wolf included in battle scope
  - Elric Vane included in campaign notes scope (he IS relevant there)
4. Integrate into the three-gate model as a sub-gate under Gate 2 (Projection Semantics) or as a new Gate 2B.

### Phase E — Iteration and expansion

1. Run the scope precision gate against current store.
2. Identify other entities that should be pruning candidates.
3. Consider whether the scope definition should be:
  - Explicit (user provides document list)
  - Inferred (from question text matching document titles/content)
  - Both (explicit when available, inferred as fallback)

---

## 7) Key Files


| File                                                           | Role                                                           |
| -------------------------------------------------------------- | -------------------------------------------------------------- |
| `src/agent/context_formatter.py`                               | Current entity ranking (fact count only) — primary edit target |
| `src/reducer/canon_projection.py`                              | Already emits `provenance_evidence_ids` per attribute          |
| `src/store.py`                                                 | FactStore with evidence_units, entities, facts                 |
| `src/cli.py`                                                   | CLI entry point (will pass scope to formatter)                 |
| `evals/mirathorn_vertical_slice/eval_fact_quality.py`          | Existing Gate 1 — pattern source for new gate                  |
| `evals/mirathorn_vertical_slice/run_step1.py` - `run_step3.py` | Existing Gate 2 — integration point for scope precision        |
| `tests/test_context_formatter.py`                              | Existing formatter tests — extend for scope filtering          |


---

## 8) Design Questions to Resolve

1. **Scope definition mechanism:** How does the system know which documents are "in scope" for a query? Explicit parameter? Inferred from question text? Campaign-level default?
2. **Exclusion vs deprioritization:** Should out-of-scope entities be completely excluded from context, or just sorted to the bottom with a "[out of scope]" annotation? Exclusion is simpler and saves tokens. Annotation preserves information but adds noise.
3. **Gate placement:** Is scope precision a sub-gate of Gate 2 (Projection Semantics), or a new Gate 2B? It's deterministic (no LLM), which argues for Gate 2. But it requires evidence provenance, which is closer to Gate 1.
4. **Granularity:** Should scope overlap operate at the document level (coarse) or evidence unit level (fine)? Document level is simpler and sufficient for the Elric Vane case. Evidence unit level would allow within-document scoping (e.g., only the battle section of a long document).

---

## 8.5) Failure Modes and Guardrails (Must-Have)

Scope gating must avoid becoming an over-pruning mechanism. The following failure modes are required design constraints:

1. **Cold start / fresh world:** For new spaces with weak scope signal, `overlap == 0` means "unknown", not "irrelevant."
2. **Ambiguous scope inference:** If scope is inferred from weak lexical hints, hard exclusion can remove correct entities.
3. **Sparse evidence linkage:** Missing/partial evidence links can create false `overlap == 0` for relevant entities.
4. **Causal-background relevance:** Entities can be relevant to a scene without direct in-scene evidence overlap.

Required guardrails:

- **Tri-state classification, not binary:**
  - `in_scope`
  - `out_of_scope_confident`
  - `unknown_insufficient_signal`
- **Hard exclusion is gated:** only for `out_of_scope_confident`.
- **Unknown is deprioritized, not dropped:** preserve recall under uncertainty.
- **Question-mention protection:** entities named in query (display name/alias) are never hard-excluded.
- **Exploration quota:** reserve context slots for unknown entities to prevent all-in-scope monopolization.

Default policy constants (initial):

- `min_scope_confidence = 0.75`
- `min_entity_evidence_count = 2`
- `unknown_exploration_quota = 10`
- `hard_exclude_out_of_scope = False` by default

---

## 9) What This Enables Long-Term

- **Token efficiency:** Stop wasting synthesis context on irrelevant entities. With 200-entity cap and many out-of-scope entities, this directly improves answer quality.
- **GM trust:** A system that correctly says "Elric Vane isn't relevant to this scene" is more trustworthy than one that confidently includes him.
- **Pruning workflow:** The pruning_candidate signal could feed a future GM-facing "suggested cleanup" feature: "These entities exist in your world but have no connection to your current campaign arc."
- **Scoped projection:** Eventually, the projection itself could be scope-aware — only projecting entities relevant to the query, not the entire store. This is a natural evolution from the filtering approach.

---

## 10) Exit Criteria

1. Entity-to-document index is computed and tested.
2. `format_projection_context` accepts optional scope and filters/deprioritizes correctly.
3. Elric Vane is excluded from battle-scoped context; Wolf and Council Room are retained.
4. At least 3 scope precision benchmark cases pass.
5. Backward compatibility: when no scope is provided, behavior is identical to current.
6. No regression in existing Gate 1/2/3 results.
7. New safety checks pass: cold-start and ambiguous-scope scenarios do not hard-prune needed entities.
8. Mentioned entities survive scope gating even when overlap is zero.

---

## 11) Definition of Done

This handoff is complete when:

- Scope-aware context formatting is implemented and tested,
- the benchmark proves the architecture correctly excludes irrelevant entities,
- and the pruning candidacy signal is available in projection metadata for downstream consumption.

The benchmark drives the architecture, not the other way around.