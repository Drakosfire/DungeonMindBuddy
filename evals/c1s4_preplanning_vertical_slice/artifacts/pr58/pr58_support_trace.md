# PR58 Support-card Step2C trace

## Root cause (fixed)
`build_preplanning_context_bundle` treated support-card `source_reference` dicts as corpus paths and dropped them via `is_allowed_retrieval_corpus_path`.

## Fix
Support knowledge cards bypass corpus path hygiene and append directly with `presentation_lane=support_knowledge` and `subject_class=support`.

## Verification
- Unit test `test_support_bundle_preserves_support_card_hits` passes with an explicit support hit.
- Direct probe with expected terms still reaches `support:hempholm_tree_visible_threat`.

## Remaining Q5 Step2C miss (not bundle assembly)
For the actual Q5 planner question text, hempholm campaign-corpus section records outrank the support card in the top-50 candidate pool (`_retrieve` returns no support unit_id). This is query-construction / ranking depth, not admission — track as PR59.

## Audit counts (this run)
- support retrieval_probe_hit rows: 2
- support step2c_candidate_hit rows: 0
- support probe hit but step2c retrieved miss: 2
