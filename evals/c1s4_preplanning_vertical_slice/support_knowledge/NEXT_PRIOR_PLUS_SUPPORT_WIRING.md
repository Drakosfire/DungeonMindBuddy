# Next Wiring Step — Prior Plus Support Retrieval

This note defines the next implementation step after the support-knowledge retrieval contract lands.

## Goal

Add a corpus-agnostic `prior_plus_support` retrieval mode for the C1S4 vertical slice.

It should load:

- C1S1-C1S3 session-memory records
- Hempholm support cards
- Elderwyld world/travel support cards

It should not load:

- original C1S4 recap
- normalized C1S4 recap
- C1S4 breadcrumb/session-memory derivatives
- generated C1S4 oracle target artifacts

## Important constraint

The implementation must not retrieve support cards by question ID or benchmark target metadata.

Support cards contain fields such as `usable_for_questions` to help humans and evaluators understand relevance. These are not retrieval fields.

Use `support_retrieval_field_policy.json` as the field visibility source of truth.

## Suggested files

Create something like:

```text
evals/c1s4_preplanning_vertical_slice/support_knowledge_loader.py
evals/c1s4_preplanning_vertical_slice/step1b_prior_plus_support_context.py
tests/test_c1s4_support_knowledge_loader.py
tests/test_c1s4_prior_plus_support_context.py
```

## Normalization target

Every support card should become a normalized record with a shared shape similar to:

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
  "source_reference": {"document": "Of Conks & Cons v2.1"},
  "eval_metadata": {
    "usable_for_questions": ["q05_merchant_description_of_giant_tree"],
    "must_not_claim": ["tree swatted Karsemine unless C1S4 oracle is allowed"]
  }
}
```

Session-memory records and support records should flow through the same retrieval/ranking surface after policy filtering.

## Required diagnostic modes

### `prior_plus_support_content_only`

Index support-card:

- `title`
- `summary`

Do not index:

- `retrieval_terms`
- `usable_for_questions`
- guardrail fields
- authority fields

### `prior_plus_support_content_plus_lexical_hints`

Index support-card:

- `title`
- `summary`
- `retrieval_terms`

Still do not index:

- `usable_for_questions`
- guardrail fields
- authority fields

Report content-only and lexical-hint results separately.

## Required tests

### `test_support_loader_normalizes_cards`

Loads both support-card JSONL files and produces normalized records with:

- `unit_id`
- `source_kind`
- `source_layer`
- `authority_role`
- `canon_status`
- `title`
- `lexical_plain`
- `source_reference`

### `test_support_loader_separates_eval_metadata`

Asserts `usable_for_questions` is inside `eval_metadata` or equivalent and not in indexable text.

### `test_content_only_index_excludes_retrieval_terms`

Asserts `content_only` text is exactly title/summary-derived and does not include hand-authored lexical hints.

### `test_content_plus_lexical_hints_includes_retrieval_terms`

Asserts lexical hints are included only in that diagnostic mode.

### `test_retrieval_does_not_use_usable_for_questions`

Create a fake card with a matching `usable_for_questions` value but unrelated title/summary. It must not be selected merely because of that metadata.

### `test_prior_plus_support_preserves_oracle_boundary`

Asserts prior-plus-support still rejects C1S4 original, normalized, breadcrumb, session-memory derivative, and oracle target paths.

### `test_bundle_preserves_authority`

Returned support records in context bundles preserve:

- `source_layer`
- `authority_role`
- `canon_status`
- `source_reference`

## Reporting

The Step 1B summary should report:

- retrieval mode
- number of session-memory records considered
- number of support records considered
- oracle leakage hits
- top-k items by source kind/layer
- whether lexical hints were enabled

Do not report one aggregate success score.

## Non-goals

Do not implement:

- live planner calls
- LLM answer generation
- oracle grading
- corpus ingestion
- retrieval tuning
- baseline regeneration

This is a retrieval-surface and boundary proof only.
