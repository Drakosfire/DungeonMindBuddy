# Support Knowledge Retrieval Contract

This contract governs how C1S4 support knowledge may be loaded, indexed, retrieved, bundled, and evaluated.

The purpose is to prevent the C1S4 vertical slice from becoming a keyed lookup harness disguised as retrieval.

The support knowledge in this directory is intentionally hand-authored and unusually clean. That is acceptable only if the retrieval path treats it like a normal mixed corpus after policy filtering. The retriever must not use benchmark labels, question IDs, or target metadata to select answers.

## Core invariant

Planner-visible retrieval must operate over a normalized corpus surface, not over benchmark answers.

Bad:

```python
if query.question_id in card["usable_for_questions"]:
    return card
```

Good:

```python
records = load_normalized_records()
allowed = policy_filter(records, mode="prior_plus_support")
ranked = retrieve(query.text, allowed)
bundle = build_context_bundle(ranked, preserve_authority=True)
```

## Retrieval-visible fields

Support-card retrieval may index only these fields:

- `title`
- `summary`
- `retrieval_terms`

The default support retrieval mode should run in two variants:

1. `content_only`
   - Indexes `title` and `summary` only.
   - This tests whether the record content itself is sufficient.

2. `content_plus_lexical_hints`
   - Indexes `title`, `summary`, and `retrieval_terms`.
   - This tests the value of lexical artifacts.

If `content_only` fails and `content_plus_lexical_hints` succeeds, that is a useful diagnostic. It should not be hidden inside one happy score.

## Retrieval-forbidden fields

The retriever must not use these fields for indexing, filtering, ranking, selection, query expansion, or admission:

- `usable_for_questions`
- `question_id`
- `answer_product`
- `authority_label` when used as a gold/eval target label
- `oracle_risk`
- `expected_retrieval_context`
- `known_context_gaps`
- `must_not_include_unless_sourced`
- `must_not_claim`
- any future `gold_*`, `target_*`, `expected_*`, `oracle_*`, or `benchmark_*` fields

These fields may exist in records, but they are evaluation metadata, guardrails, or bundle annotations. They are not retrieval evidence.

## Bundle-visible fields

A context bundle should preserve enough authority metadata for the planner and evaluator to reason about source type and risk.

The bundle may include:

- `source_layer`
- `authority_role`
- `canon_status`
- `source_reference`
- `must_not_claim`
- `must_not_include_unless_sourced`
- `support_card_id`
- `schema`

Bundle visibility is not retrieval visibility. These fields may be shown after retrieval, but they must not determine retrieval selection.

## Normalized record contract

All corpus surfaces should eventually enter retrieval through a common normalized record interface.

Example:

```json
{
  "unit_id": "support:hempholm_tree_visible_threat",
  "source_kind": "support_knowledge_card",
  "source_layer": "source_module",
  "authority_role": "planning_support",
  "canon_status": "source_supported_adaptation_candidate",
  "title": "Grotesque tree as visible threat",
  "lexical_plain": "Grotesque tree as visible threat. The source tree is an obvious village-scale problem...",
  "retrieval_terms": ["grotesque tree", "magical tree", "metallic leaves"],
  "source_reference": {
    "document": "Of Conks & Cons v2.1"
  },
  "eval_metadata": {
    "usable_for_questions": ["q05_merchant_description_of_giant_tree"],
    "must_not_claim": ["tree swatted Karsemine unless C1S4 oracle is allowed"]
  }
}
```

The future loader may materialize `lexical_plain` from `title + summary`, optionally appending `retrieval_terms` only in the `content_plus_lexical_hints` diagnostic mode.

## Required retrieval modes

The next wiring PR should support at least these modes:

### `prior_only`

Planner-visible records:

- C1S1-C1S3 session-memory records only.

Forbidden:

- support knowledge
- C1S4 recap/oracle material

Purpose:

- Tests broad inference from prior play only.

### `prior_plus_support_content_only`

Planner-visible records:

- C1S1-C1S3 session-memory records
- support knowledge cards

Indexable support fields:

- `title`
- `summary`

Forbidden:

- support-card eval metadata
- C1S4 recap/oracle material

Purpose:

- Tests whether support-card content is retrievable without lexical hints or benchmark keys.

### `prior_plus_support_content_plus_lexical_hints`

Planner-visible records:

- C1S1-C1S3 session-memory records
- support knowledge cards

Indexable support fields:

- `title`
- `summary`
- `retrieval_terms`

Forbidden:

- support-card eval metadata
- C1S4 recap/oracle material

Purpose:

- Tests whether dynamic lexical artifacts improve retrieval.

### `oracle_grading`

Planner-visible records:

- none

Grader-visible records:

- C1S4 oracle targets/recap according to the KB policy.

Purpose:

- Compares generated prep against held-out observed play after planner generation is complete.

## Required anti-fake-good tests

The wiring PR should include tests equivalent to the following.

### 1. Do not use `usable_for_questions`

Create a fake support card where `usable_for_questions` matches the target question, but `title`, `summary`, and `retrieval_terms` are unrelated. The retriever must not rank it highly merely because the Q ID matches.

### 2. Retrieve without Q IDs

Ask a natural paraphrase that does not contain the target question ID. The retriever should be able to find relevant support records from content fields.

### 3. Decoy resistance

Add decoy support cards from unrelated domains. The retriever should not return Hempholm tree cards for route-ecology questions or Mirathorn travel cards for tree-threat questions unless the query genuinely bridges those concepts.

### 4. Authority preservation

Returned bundle items must preserve source authority fields, including whether an item came from:

- session memory
- source module
- adaptation planning
- world canon
- campaign-stateful reference
- known gap / support synthesis

### 5. Oracle exclusion still holds

Adding support knowledge must not weaken C1S4 oracle exclusion. Prior-plus-support mode still forbids original C1S4 recap, normalized C1S4 recap, C1S4 breadcrumb/session-memory derivatives, and generated oracle targets.

## Reporting requirements

Do not report one aggregate success score.

Report at least:

- boundary safety
- policy correctness
- retrieval relevance
- authority preservation
- lexical-hint lift
- oracle discipline
- answer utility, when planner generation exists

This avoids a benchmark report that says retrieval is working when the harness merely selected pre-labeled cards.

## Design consequence

The support cards may remain intentionally helpful. They are a manual perfect-ingestion surrogate. But the retrieval path must behave as if they are ordinary corpus records from a future ingestion system.

The win condition is not “Q5 finds the Q5 card.”

The win condition is:

```text
A corpus-agnostic retriever can search mixed session-memory, source-module, adaptation, and worldbuilding records using only retrieval-visible text, preserve authority metadata, and keep the C1S4 oracle out of planner context.
```
