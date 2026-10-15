# INGEST: party-fill source binding

Status: ACTIVE under PRIME's authorized recap ingestion repair, 2026-10-15.
Base: `e778b3f048bea547e6531c950bc7565a96922fa4`.
Lane: `codex/party-fill-source-binding`, `/tmp/prime-mirathorn-governance-current`.
Topology: serial, one bounded PR; implementation solo, ARCHITECTURE independent review.

## Invariant and failure cases

The enrichment producer selects packet-local source row indexes. Buddy binds them
to immutable source-span IDs and verifies quotes against the selected row before
any fill is applied. An invalid or partial fill preserves all baseline nodes and
reports incomplete enrichment. Final validation counts nested evidence and rejects
unresolved citations. Unknown rows, copied/shortened IDs, cross-row quotes,
invented identities, duplicates and partial failures must not replace valid data.
This proves provenance, not natural-language entailment.

## Exclusive write set

- This handoff.
- `src/graph_memory/extraction/party_claimed_fill.py`
- `src/graph_memory/extraction/category_candidate_graph_extractor.py`
- `src/graph_memory/extraction/category_candidate_graph_schema.py`
- `src/graph_memory/extraction/graph_ingest_packaging.py`
- `tests/test_party_claimed_fill.py`
- `tests/test_party_fill_source_binding.py`
- `tests/test_graph_ingest_packaging_live_call_shape.py` (bind its synthetic supplied-candidate citation to the exact admitted source index; no legacy-ID rebinding in production).

Open relevant PRs and existing leases inspected; prior PRIME extraction lanes are
frozen/merged predecessors, not concurrent writers. DOGFOOD owns UI changes and
5202; no overlapping runtime or file lease is granted here.

## Boundary evidence and exclusions

Exercise the production schema selection, producer result binding, atomic apply,
final sanitation and packaging validation with synthetic source packets. Preserve
run `f43e48e6-c775-4960-824f-fb398fe50bb9` unchanged. No retained DB writes,
publication, provider call or service change in this code slice. A changed-pipeline
live extraction follows exact-head independent review, with publication separately
reviewed. No display mention-matching repair or graph retrieval ledger change.
