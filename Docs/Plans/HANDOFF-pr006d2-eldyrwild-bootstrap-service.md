# HANDOFF — PR006D2 — Approved Eldyrwild bootstrap activation service

**Blocked on:** PR006D1 (GitHub #336 draft)

## Mission

The approved Eldyrwild package can be inspected and explicitly activated through
a stable backend contract.

## Scope (allowlist)

- Eldyrwild acceptance policy (exact counts, forbidden legacy IDs, bundle pin)
- Bundle certification → `invalid_bundle` precedence in status
- `/api/live/world-graph-bootstrap` status / prepare / confirm
- Review projection: nodes, edges, attributes, contribution/source classification,
  evidence summaries
- Truthful prepare/confirm token binding (proposal + actor) and result statements
- Headless CLI
- Exact serialized API contract fixture (generated from backend response models)
- Tests for service/routes only

## Explicitly out of scope

- Kernel storage/validation changes (PR006D1)
- `/ingest` UI (PR006D3)
- Projection Engine / Plan migration

## Blocking findings from #336 to absorb

1. Backend/frontend contract mismatch → one exact serialized contract
2. Review projection required before confirmation can be honest
5. `invalid_bundle` must take precedence over world readiness
6. Confirm token must bind proposal + actor; statements must match published=true/false

## Verification

- pytest for bootstrap service + routes
- CLI prepare→confirm smoke against tmp root
- Contract fixture round-trip (backend dump ↔ typed client models)
