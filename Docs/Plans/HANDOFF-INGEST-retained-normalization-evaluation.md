# Retained normalization evaluation

Status: ACTIVE for bounded implementation, tests and independent review. No study execution, provider or DB authority.

Authority: owning study steward adopts the reviewed generic tooling plan under the user-approved ingestion study. H3 is settled rejected; H4 product PR #2173 is separately frozen and reviewed. This slice prevents a custom replay harness for each recap.

Branch `codex/ingest-retained-normalization-evaluation`; exact base PR #2169 at `c8e1777fb5bb1a66ab941c11e6e8880a19290e1e`. Stacked topology: existing evaluator predecessors → #2169 → this tooling PR. Product #2173 is an independent pinned runtime input, not a compile-time dependency. No merge authority. CLI/guide write lease transfers from completed #2169 implementation to this child; no active concurrent product writes.

Expected paths: `src/ingestion_evaluation/normalization.py`, `scripts/evaluate_ingestion.py`, `tests/test_ingestion_evaluation_normalization.py`, `Docs/Guides/ingestion-study-assessments.md`, this handoff. No product, schema, source/Gold, live lifecycle or publication API changes.

Add one manifest-driven offline command. Reuse existing pins/sealing. Validate accepted response-component links, bindings, source/context and owner parsing/materialization. Controlled pinned runtime workers use complete fixtures with no network/provider/DB effects. Strict old decoded-candidate equality is required before treatment comparison; unexplained differences stop qualification. Preserve raw actual scores/costs as references, never synthetic fixture metrics. Outputs are labeled counterfactual artifacts, not new actual runs or DB candidate replacements.

Verify generic success and tampered/missing response/context/runtime inputs, reconstruction failures, side-effect traps, worker failure/timeout and output collisions/idempotence. Review exact cumulative diff independently, then commit/push/open a bounded PR. Actual H4 comparison and fresh ingestion/publication require their own pinned activation after tool qualification. Primary data and sealed holdouts remain untouched.
