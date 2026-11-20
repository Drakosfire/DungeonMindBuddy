# GRAPH: retire unused single-slice contribution builder

Status: ACTIVE. Owner: PRIME under cleanup/demolition authority.
Base: origin/main@26ba5231c67aa0a4779cce99876a773a8457dd7c.
Branch: codex/retire-single-slice-contribution-builder; reuse buddy-context-loop.
Topology: parallel-independent of PR2058@0b416b7d64bf86bb5f0b257799795e400092ba8a
(extract_promote_ops/native wrapper/threat callers and their tests). Paths are
disjoint, no unmerged dependency. Serial conserved runtime delivery.
ADVERSARY owns Gold/ingestion quality; no change to those artifacts or decisions.

## Outcome and contract

Delete build_accepted_contribution_from_proposals: repository-wide search finds
no product callers, only three calls in one producer test module. The live sealed
reconstruction uses build_accepted_contribution_from_multi_slice_proposals for
one or many slices. Keep that function and every other runtime function/class
AST-identical. No replacement adapter, alias, new authority or code path.
Retain producer tests for default-off source observations, missing selected
subject rejection, same-slice selected-subject success and cross-slice atomic
subject dependency. Exercise the existing live multi-slice owner for each.

## Exclusive expected writes

- src/graph_memory/extract_identity_gate.py
- tests/test_recap_source_observation_producer.py
- Docs/Plans/HANDOFF-GRAPH-retire-single-slice-builder.md
- Docs/Plans/HANDOFF-GRAPH-directed-edge-alignment.md

Last path truthfully settles delivered predecessor2057; no new behavior/scope.
Do not alter native source/identity guards, proposal sealing, selection/dedup,
retained data, source files, Gold, model guidance, dependencies or schema.
Do not absorb the separate retired-root-context/receipt-projection investigation.

## Validation

Existing producer/known-party/exact-edge/admission cohort baseline80 passes.
Compare every retained runtime function/class AST with exact base, verify no
remaining caller/import for the removed helper, run same80 checks, source Ruff
and diff checks. Independently review full diff and require CI before merge;
qualify actual merge then deliver with primary tables/session files conserved.
No provider or primary database effects during implementation/review.
