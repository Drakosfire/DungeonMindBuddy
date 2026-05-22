# Post-PR65 Planning Recommendations

Generated from `111` planner-facing mode rows.

## Hard boundary status

- `prompt_payload_invalid`: 0
- `forbidden_prompt_key_hits`: 0
- `forbidden_prompt_value_hits`: 0
- `known_context_gaps_leaked`: 0
- `generated_answer_control_leaks`: 0
- `prior_only_support_leaks`: 0
- `must_not_include_terms_in_prompt_payload`: 0

## Coverage classes (Tier B diagnostics)

- `creative_generation_no_strict_context_required`: 39
- `needs_manual_review`: 38
- `ok_or_later_stage`: 28
- `support_expected_but_missing`: 6

## Recommended next PR

**PR66 support-required retrieval/admission expansion**

- Support-required gaps cluster on questions: [10, 11, 20]
- `39` creative-generation rows are boundary-clean; do not overfit strict retrieval there.

PR65 is a baseline expansion PR. Unresolved retrieval insufficiency is expected and classified, not repaired here.