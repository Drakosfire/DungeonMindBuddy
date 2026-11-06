# INGEST: H1 shared node coverage simplification

Status: ACTIVE experiment implementation, not adopted or deployed default.
User-authorized study; root owns design and this bounded product lane.

Topology: stacked on PR #2152 exact9de7c37ae69a594ccff17ed4ffdfbc95bba5c6ee.
Merge/rebase its product parents first; do not merge H1 until planned quality and
heldout validation passes. Branch codex/ingest-h1-node-coverage in reused clean
attached direct-source-precedence checkout. Evaluator checkout remains at reviewed
PR #2156 head4722209f8. No overlapping writes, services or primary data changes.

Exclusive writes: src/graph_memory/extraction/recap_extraction_profile.py
(_NODE_DESCRIPTION_COVERAGE only); tests/test_recap_source_faithfulness_profile.py;
tests/fixtures/recap_node_coverage_baseline.json; this handoff. Existing profile/test
write ownership is consumed from the completed product predecessor; no other lane
is writing these files. No schema, provider, pass ordering, output allocation,
publication, code fallback or alternate producer changes.

Pinned design: external study-experiment-h1-prompt-coverage-v1/design-v2.json,
SHA2e0f67dbcd7ae34dd7ce6ae6e7787e002bc79f76973c69af90a92576353b1551.
Rubric: precision-workload-rubric-v1.json,
SHAf8e19c54927295f43fa5aa359eb293d8e796010d5a7081dc5421109c6d995c56.
Exact change: replace148word shared node coverage paragraph with71word paragraph;
shared faithfulness/ambiguity policy remains unchanged. This is a hypothesis, not
an assertion that fewer words preserve quality.

Test-only scope: preserve original paragraph as inert frozen data for earlier
prompt-hash comparisons, using the existing historical comparison helper. Remove
six duplicated literal-wording checks; retain actual policy insertion/scope and
historical source/schema checks. No historical text is a production fallback.

Validation: existing profile/source evidence contract tests; actual offline prompt
diff against retained baseline, only five node-pass prompts changed; no semantic
quality claim from unit checks. Independent exact-head review, draft PR delivery.
Model calls require qualified isolated inputs/context and fixed design first.
Primary unchanged; no publication/migration. Rejected experiment remains unmerged
history with no active runtime switch or fallback. Adopted path must be singular.

Observed implementation validation:114 existing profile/source-evidence/quote/compact/schema
tests passed. Independent review confirmed AST-only production change to the one
constant, both exact preregistered strings, and inert parent fixture bytes;18
profile tests independently passed (read-only pytest-cache warning only). This
is no model-quality or default-adoption judgment.
