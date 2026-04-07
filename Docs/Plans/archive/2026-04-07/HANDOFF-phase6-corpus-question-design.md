# Handoff: Phase 6 — Corpus Examination and Benchmark Question Design

**Date:** 2026-04-05  
**Status:** READY  
**Priority:** HIGH  
**Precondition:** Gate 1/2/3 GREEN on Mirathorn vertical slice (commit `9821a0f`). Gold coverage currently limited to `The City of Mirathorn.md` only.

---

## 1) Mission

Examine the full DungeonMindBuddy corpus, design benchmark questions that cover it, and surface a first sample batch for user review. The user authored this corpus and can validate quickly.

This is the "expand beyond happy path" step that proves the benchmark infrastructure works on material beyond the original Mirathorn gazetteer.

---

## 2) Current Gold Coverage (Gap Analysis)

### What is covered

- `The City of Mirathorn.md` — 11 entity anchors, 10 fact anchors, 10 gold facts
- Council room question set — 5 manually authored questions with must/stale tokens
- eval_synthesis.py — single "Catch me up on Mirathorn" question

### What is NOT covered

The following corpus documents have zero gold questions, zero anchors, and zero fact coverage:

| Document                                         | Content                                  | Why it matters                           |
| ------------------------------------------------ | ---------------------------------------- | ---------------------------------------- |
| `The Council Room.md`                            | Architecture, chandelier, atmosphere     | Tests static-description extraction      |
| `Battle with The Wolf and Aftermath.md`          | Combat, terminal outcomes, aftermath     | Tests temporal/event extraction          |
| `The Emergency Council Meeting.md`               | Narrative, NPC actions under stress      | Tests multi-actor event sequences        |
| `The City Council.md`                            | Institution, members, governance         | Tests faction/role extraction            |
| `Longmont Campaign General Notes.md`             | Campaign-layer observed material         | Tests campaign vs world layer separation |
| `corpus/eldyrwild-markdown/Elderwyld/` (broader) | Regions, cities, items, events, factions | Tests corpus-wide generalization         |

---

## 3) Pattern Source: RulesIngestion Benchmark Construction

RulesIngestion uses a semi-automatic pipeline. Adapt these patterns for extraction/projection (not retrieval):

### 3a) Template-driven question authorship

RulesIngestion pattern: `benchmark_template_retrieval.json` defines the schema; questions are filled manually or by agent.

**DMB adaptation:** Create a question template with fields appropriate for extraction/projection QA:

```json
{
  "id": "q_wolf_terminal_state",
  "document_source": "Battle with The Wolf and Aftermath.md",
  "question": "What happened to The Wolf at the end of the council room battle?",
  "expected_answer_summary": "The Wolf was killed. Bonogo dealt the killing blow, decapitating The Wolf.",
  "must_hit_tokens": ["killed", "dead", "killing blow", "decapitated", "bonogo"],
  "stale_tokens": ["alive", "still fighting", "escaped"],
  "update_signal_tokens": ["decapitated", "killing blow", "dead", "aftermath"],
  "semantic_equivalences": {
    "killing blow": ["decapitated", "head removed", "fatal strike"]
  },
  "target_entities": ["ent_the_wolf", "ent_bonogo"],
  "target_attributes": ["status", "combat_outcome"],
  "surface": "core_extraction",
  "tier": "must_pass"
}
```

### 3b) LLM-assisted question generation from corpus text

RulesIngestion pattern: `auto_gold_review/` uses LLM to propose gold from retrieved chunks.

**DMB adaptation:** Use LLM to read each corpus document and generate candidate questions. The prompt should:

1. Read the document markdown
2. Identify key factual claims, entity relationships, temporal states, and narrative outcomes
3. Generate 3-5 questions per document that a GM would realistically ask
4. For each question, propose `must_hit_tokens`, `stale_tokens`, and `expected_answer_summary`
5. Tag each question with `target_entities` and `target_attributes`

### 3c) Corpus-grounded validation

RulesIngestion pattern: `cite_gold_from_retrieval.py` uses Jaccard matching to ground gold to actual extracted content.

**DMB adaptation:** After generating candidate questions, validate against the actual fact store:

1. For each question's `target_entities` + `target_attributes`, check whether matching facts exist in the store
2. Classify each question as: `answerable` (facts exist), `partially_answerable` (some facts exist), `unanswerable` (no matching facts — extraction gap)
3. Surface `unanswerable` questions as extraction coverage gaps, not benchmark failures

---

## 4) Execution Plan

### Phase A — Corpus inventory and document profiling

1. Read every file listed in `corpus/eldyrwild-markdown/` (recursive).
2. Build a document manifest:
  - path, title, `document_class`, `canon_layer`, approximate word count
  - key entities mentioned (proper nouns, faction names, place names)
  - narrative type: static description / event sequence / character profile / session recap / campaign notes
3. Prioritize documents for question generation by:
  - narrative density (events > static descriptions)
  - entity coverage gap (documents with entities not yet in gold)
  - layer diversity (world + campaign material)

### Phase B — Generate candidate questions (LLM-assisted)

For each priority document (start with top 5):

1. Feed document text to LLM with the question-generation prompt
2. Collect 3-5 candidate questions per document
3. Format each question using the template from §3a
4. Tag with surface (`core_extraction` or `vertical_slice`)

Target: 15-25 candidate questions from first pass.

### Phase C — Validate against existing store

1. Load current fact store (from latest successful ingest)
2. For each candidate question, check entity/attribute coverage
3. Classify: `answerable` / `partially_answerable` / `unanswerable`
4. Annotate each question with coverage status and closest-match facts

### Phase D — Surface first sample for user review

1. Select 8-10 highest-quality candidates (mix of answerable + partially_answerable)
2. Format as a review document with:
  - the question
  - expected answer summary
  - must-hit / stale tokens
  - coverage status against current store
  - source document reference
3. Present to user for editorial review before committing to gold

---

## 5) Question Design Principles

Carry forward from `DESIGN-benchmark-philosophy.md`:

1. **Score semantics, not tokens.** Include `semantic_equivalences` for every must-hit token that an LLM might paraphrase.
2. **Classify failures, don't count them.** Every question must support `pass_updated` / `fail_stale` / `fail_incomplete` / `fail_error` verdicts.
3. **Test temporal state awareness.** For event-bearing documents, include questions that distinguish "before" from "after" states. Include `stale_tokens` that would indicate the model is stuck in a prior temporal state.
4. **Test layer separation.** Include at least 2 questions that can only be answered correctly if campaign-layer facts are properly overlaid on world-layer canon.
5. **Cover the entity taxonomy.** Questions should span actors, places, factions, items, and events — not just actors.
6. **GM-realistic phrasing.** Questions should sound like what a GM would actually type: "What do the players see when they enter the council room?", not "List all architectural features of entity ent_council_room."

---

## 6) Corpus File Reference

```
corpus/eldyrwild-markdown/
├── Elderwyld/
│   ├── Cities and Towns/
│   │   ├── Mirathorn/
│   │   │   ├── The City of Mirathorn.md          ← COVERED (gold exists)
│   │   │   ├── City Council Building/
│   │   │   │   ├── The Council Room.md            ← UNCOVERED
│   │   │   │   ├── Battle with The Wolf and Aftermath.md  ← UNCOVERED
│   │   │   │   ├── The Emergency Council Meeting.md       ← UNCOVERED
│   │   │   │   └── The City Council.md            ← UNCOVERED
│   │   │   ├── Sewers/
│   │   │   ├── Stormspire Academy/
│   │   │   ├── Wolf Manor/
│   │   │   └── ...
│   │   └── Mossford/
│   ├── Regions/
│   ├── Events/
│   ├── Factions/
│   └── Items/
├── Longmont Campaign/
│   ├── Campaign 1/
│   │   ├── Session Recaps/
│   │   ├── Prep/
│   │   └── Longmont Campaign General Notes.md     ← UNCOVERED
│   └── Campaign 2/
└── ...
```

---

## 7) Key Files

| File                                                              | Purpose                                          |
| ----------------------------------------------------------------- | ------------------------------------------------ |
| `corpus/eldyrwild-markdown/`                                      | Source corpus (user-authored)                    |
| `evals/mirathorn_vertical_slice/benchmark_corpus_paths.txt`       | Current benchmark file list                      |
| `evals/mirathorn_vertical_slice/gold/gold_facts.json`             | Existing fact gold (10 entries, Mirathorn-only)  |
| `evals/mirathorn_vertical_slice/gold/entity_anchors.json`         | Existing entity anchors (11 entries)             |
| `evals/mirathorn_vertical_slice/gold/fact_anchors.json`           | Existing fact anchors (10 entries)               |
| `evals/mirathorn_vertical_slice/run_council_room_question_set.py` | Existing manual question runner (pattern source) |
| `evals/mirathorn_vertical_slice/eval_synthesis.py`                | Current synthesis gate (single-question)         |
| `evals/mirathorn_vertical_slice/eval_fact_quality.py`             | Fact quality evaluator with mismatch taxonomy    |
| `Docs/Design/DESIGN-benchmark-philosophy.md`                      | Benchmark principles and gate model              |

---

## 8) Exit Criteria

1. Corpus inventory document produced (document manifest with profiling).
2. 15-25 candidate questions generated across at least 4 uncovered documents.
3. Each question validated against current store (coverage classification).
4. First sample batch (8-10 questions) formatted and surfaced for user review.
5. Sample includes mix of:
  - static-description questions (council room architecture)
  - temporal-state questions (Wolf outcome, emergency meeting sequence)
  - layer-separation questions (campaign vs world canon)
  - faction/role questions (Shepherd's Flock goals, City Council governance)

---

## 9) Definition of Done

This handoff is complete when the user has reviewed the first sample batch and made editorial accept/reject/revise decisions on each candidate question. Accepted questions become the seed for expanded gold coverage in the next phase.

Do NOT commit generated questions to gold until the user has reviewed and approved them.
