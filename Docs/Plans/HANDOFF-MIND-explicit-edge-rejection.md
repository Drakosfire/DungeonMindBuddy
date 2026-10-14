# MIND: defer explicitly rejected edge output

Status: ACTIVE. Owner: PRIME solo. Non-serving.
Branch: codex/recap-explicit-edge-rejection.
Base: c2e5e1b6efcf2102b99cb8c3eb1e44bd0e834db8, pending #1148.
Remote main: c9f5c21f3b835f35660b85fbd2e9a38312c401d4.

## Outcome and bounds

Consolidation must not publish a positive relationship from model output whose label explicitly begins `Omitted: no source support`. Move that record to existing deferred items, preserving source refs and the rejected tuple in its reason. Ordinary narrative negation, quotes and unrelated uses of omitted are not classified. No general entailment claim.

Exact write set: category_candidate_graph_extractor.py; tests/test_explicit_edge_rejection.py; this handoff. Serial extractor lease transfers from frozen #1148. Merge/rebase #1143, #1145, #1148 first. No provider, retained database, source, serving, schema, identity, dependency or native vocabulary changes.

Verify the actual consolidation boundary: explicit rejection becomes one deferred item with retained evidence and no positive edge; supported neighboring edge survives; ambiguous narrative labels remain unchanged; input raw output stays immutable. Capture the real private benchmark replay locally. Commit/push/open stacked PR; independent review before merge. No selected-World readiness claim.
