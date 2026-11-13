# MIND: admit already-mapped event location predicate

Status: ACTIVE. PRIME solo implementation.
Base: `c9f5c21f3b835f35660b85fbd2e9a38312c401d4`.
Branch: `codex/recap-event-location-predicate`; isolated non-serving checkout.
Topology: parallel-independent of #1142–#1146 and held #1139; disjoint paths, no unmerged dependency. No ports, databases or provider calls leased.

Outcome: candidate extraction and correction admit `occurred_at`, which the existing Buddy adapter maps to native `dnd5e:occurs_at`. Use the existing participation family alongside present_at; do not classify event occurrence as containment among places. Preserve native endpoint qualification, unknown-predicate rejection, and located_in behavior. No new native predicate or Graph contract.

Exact write set:
- `src/graph_memory/identity_resolution.py`
- `tests/test_event_location_predicate_boundary.py`
- this handoff

Verify catalog/prompt recognition and the actual correction tuple planner, then native Event→Location qualification; reject inverse endpoints and unknown spellings. Run neighboring catalog/identity tests, Ruff and cumulative diff checks; commit, push, open PR. Independent review required before merge. No World publication or selected-World readiness claim.
