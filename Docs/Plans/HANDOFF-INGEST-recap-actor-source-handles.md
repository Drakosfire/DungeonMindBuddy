# INGEST: exact source handles for recap actors

Status: ACTIVE under PRIME's authorized ingestion goal, 2026-10-15.
Base: `de4100b6c1b9ac8e5e586d112d0bdd0880f6834d`.
Lane: `codex/recap-actor-source-handles`, `/tmp/prime-recap-mention-boundaries`.
Topology: serial successor; solo PRIME implementation, ARCHITECTURE review.

## Contract

Buddy constructs an immutable source-sentence packet from admitted recap rows.
Only the supported GE actor pass receives this explicit packet. Its wire schema
accepts sentence handles; the host materializes exact source paragraph IDs and
quotes before canonical validation/application. Injected canonical clients and
other profiles/passes retain their existing contract. No prompt-text parsing to
reconstruct authority and no model-echoed fingerprint as authority.

Bind the packet digest and exact source revision in retained request context;
retain raw wire output separately from normalized evidence. Unknown handles,
stale source, damaged offsets and incomplete binding reject the whole pass.
Quote provenance does not prove entailment, identity or type correctness. The
Session 29 candidate remains held. Known World type context is a separate slice.

## Exclusive write set

- This handoff.
- `Docs/Plans/HANDOFF-INGEST-recap-edge-response-capacity.md` (settlement).
- `src/graph_memory/extraction/source_sentence_evidence.py`
- `src/graph_memory/extraction/category_candidate_graph_extractor.py`
- `src/graph_memory/extraction/bounded_recap_execution.py`
- `tests/test_source_sentence_evidence.py`
- `tests/test_bounded_recap_execution.py`
- `tests/test_category_candidate_graph_extractor.py`

DOGFOOD owns disjoint UI files (#1183, #1188, #1190, #1191). Historical open
extractor PRs #1139/#1148/#1149 remain held; their leases do not authorize edits
in this active serial lane. No serving runtime, database, provider call or World
publication in this implementation. Prove producer→GE schema→wire response→
normalization→canonical validation, packet swaps/stale revisions, repeated
sentences, cross-paragraph support and preserved conditions/negation.
