# INGEST — preserve exact candidate relationships

Status: SETTLED. Merged PR1823 at 0a2541d36c9805a5d8c44ce72385bda7ffb1c5bc;
reviewed head2d5cd33c1 approved independently, hosted checks passed. API8000 adopted
the immutable merge source; retained 3640 APP rows,1096 native rows,40813 files.
Implementation/review lease ended. No historical repair or S8 semantic improvement
claimed. Originally ACTIVE. PRIME owns serial implementation under operator authorization to
resolve ADVERSARY material/Graph regressions. Base origin/main
04e1f9c2f116eeeadc113c29ce5aa463248ff28c; branch codex/ingest-exact-edge-dedup,
existing buddy-context-loop checkout. Remote/open PRs inspected; no overlapping
live write lease identified. Q10 consumer handoff-only branch is deferred.

## Contract and critique

Candidate extraction must not use comparison-family similarity as relationship
identity. Distinct predicates, direction, descriptive and semantic qualifiers
survive. Collapse only exact payload duplicates or explicit parent_of/child_of
inverses, unioning evidence. Family-based comparison scoring stays unchanged.
Broad families do not establish symmetry. Missing endpoints retain literal IDs.
Conservative retention avoids dropping qualifiers; this does not establish source
entailment, repair historical data, or authorize publication.

## Exclusive write lease and proof

- src/graph_memory/identity_resolution.py
- tests/test_graph_memory_identity_resolution.py
- tests/test_category_candidate_graph_extractor.py
- This handoff

No ports, live dependencies, databases, corpus or provider calls change. Reuse
existing dependencies. Reproduce loss provider-free, prove predicate and evidence
retention through ordinary candidate extraction in either order. Exact/inverse
duplicates merge evidence; different labels, semantic state and direction survive.
Inspect cumulative diff; independent Bugbot review; commit/push/open one PR.
PRIME may merge when gates pass; protected runtime adoption is a separate step.
Tests do not establish historical repair or full authoring/play acceptance.
