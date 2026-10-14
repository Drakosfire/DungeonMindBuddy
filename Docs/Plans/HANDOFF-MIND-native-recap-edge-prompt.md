# MIND: align recap edge prompt with native admission

Status: ACTIVE. Owner: PRIME, solo implementation. Non-serving lane.
Branch: codex/native-recap-edge-prompt.
Pinned base: 01d33b8cdfff87fc7b997bfccf886f9321272416, pending Buddy #1145.
Remote main: c9f5c21f3b835f35660b85fbd2e9a38312c401d4.

## Outcome

Fresh recap extraction advertises only currently native-mapped predicate catalog entries, with deterministic allowed endpoint kinds and truthful direction. Remove contradictory sweep examples that recommend unmapped relations. This improves candidate construction; it does not replace native admission, prove entailment, or publish knowledge.

Private evidence: Session 15 original edge pass has 20 raw qualification failures across 60 edges. Append-only config guidance produces 4 across 48 but loses detail and introduces semantic errors; not adopted. Production catalog has 74 entries, only 42 native-mapped. Source corpus and provider evidence stay private.

## Exact write set

- src/graph_memory/extraction/native_edge_prompt_catalog.py
- src/graph_memory/extraction/category_candidate_graph_extractor.py
- tests/test_native_edge_prompt_catalog.py
- this handoff

Serial successor to frozen #1145: PRIME transfers its extractor write lease here; merge/rebase #1143 then #1145 before this slice. Other open work is disjoint. No provider, database, serving, identity, schema or dependency-file writes in this implementation slice. No new native predicates or endpoint allowances.

Derive from existing Buddy predicate mappings and DungeonMind vocabulary; intersect with the existing catalog. Preserve reverse mappings. Failed/unsupported mappings must not be advertised as usable. Guidance must require source entailment, exact listed endpoints, descriptive labels and deferred unsupported facts, rather than coercing semantics to satisfy a tuple.

Verify every advertised endpoint pair at the owning native qualifier, including reverse-direction predicates. Verify the actual generated edge prompt drops unsupported examples and retains narrative/evidence instructions. Inspect cumulative diff, commit/push/open a stacked PR. Independent review required before merge; fresh private benchmark and rollout remain separate gates.
