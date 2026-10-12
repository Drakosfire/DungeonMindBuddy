# HANDOFF — AGENT: bind accepted relationship evidence in the initial packet

**Status:** ACTIVE, authorized by PRIME on 2026-10-12. **Base:** fetched Buddy GitHub `main@ef39f2e5c08bb851c5646c47586506d6e7150dd4`. **Topology:** parallel-independent Buddy PR; active SOURCE reader work is on disjoint paths and remains BLOCKED on its Core contract. PRIME owns independent review and merge.

## Primary question

When an accepted retrieved relationship has `evidenceRefIds` that exactly match source-anchor `evidenceRefId`s in the same result and revision, can its support survive the ordinary Agent's initial claim packet and final provider envelope without claiming that the source passage was opened?

The frozen native oracle at `rev:62820bcd7eca116af9d889e128fabf4e` supplies accepted relationships with matching evidence refs and anchors, but no anchor's supporting-object IDs contain those relationship edge IDs. The current classifier joins by edge ID, leaving `source_anchor_ids` empty; the existing Agent turn admission then withholds evidence. This is a producer-contract repair. The campaign-scoped oracle does not prove the exact manual World-scope Mossglade turn failed at this gate.

## Exclusive write lease

- `src/graph_memory/interaction/authority_classifier.py`
- `tests/test_graph_retrieval_interaction.py`
- `tests/test_agent_turn_service.py` for focused frozen-envelope proof
- this handoff

Production `agent_turn_service.py` is outside the lease. If a focused owning-boundary test demonstrates that it needs a production change, stop for PRIME to re-scope. No provider call, runtime restart, database/corpus/native Graph write, reader DTO, route/API change, or source-context feature is authorized.

## Invariant and stop conditions

For an accepted relationship, use only its exact, valid evidence-ref IDs intersected with anchors returned in the same result at the requested revision. Preserve relationship edge/subject/object/predicate, campaign scope, revision, authority, and source-readable/opened state. Do not use a nearby anchor, label/slug match, foreign revision, candidate node, rejected/nonfact assertion, or opaque label as support. A Graph-grounded fact may remain available with `source_opened=false`; no source-text quotation follows from this join. Absent or malformed evidence fails closed. Stop for PRIME if native retrieval does not attest refs, the final envelope requires an unleased production path, or a new public contract is needed.

## Acceptance witness

Focused classifier tests prove exact matching to an unreadable anchor and exclusion of an unrelated readable anchor, plus absent/foreign/mismatched/revision-negative cases. A test at the Agent turn boundary freezes an actual serialized provider envelope without a provider call and proves the exact relationship/evidence IDs survive in `claimLedger`, `dispatched_relationship_ids`, and `dispatched_evidence_ref_ids` with `packet_disposition=included` and `source_opened=false`. Run focused tests and relevant repository gates, inspect cumulative base-to-head diff, then commit/push/open the PR. Update this handoff with exact implementation head and evidence before handing it to PRIME.
