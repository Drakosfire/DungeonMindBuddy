# PR006D1 — Generic Atomic World Initialization

**Status:** draft GitHub #336  
**Depends on:** PR006C (`eldyrwild-longmont-c2-initial-v1` used only as a Kernel test fixture)

## Mission

The system can atomically initialize a new world from a validated contribution
plan without exposing a partial graph.

## What this slice owns

- Structural-vs-fixture validator split
- Empty technical baseline store
- Generic staged build + `os.rename` promotion
- `WorldInitializationPlan` binding (ordered contribution IDs + complete
  canonical contribution payload digests + caller attestation)
- Immutable receipt that records measured counts and **attested** approval metadata
- Revision-lineage classification:
  - `active` — head equals initialized head
  - `active_head_advanced` — initialized head is an ancestor of current head
  - `inconsistent_lineage` — rollback, divergent head, missing revision, or cycle
- Rebuild + contribution/world integrity proof before promotion

## What this slice does **not** own

- Eldyrwild exact node/edge/support counts or forbidden legacy IDs
- Bundle certification (`invalid_bundle`) — service concern (PR006D2)
- prepare/confirm API, CLI, or `/ingest` UI (PR006D2 / PR006D3)
- Projection Engine / Plan migration

## Trust boundary

`initialize_world_from_contributions(plan=..., contributions=..., actor=...)`
verifies:

1. `contributions` IDs exactly match `plan.ordered_contributions` in order
2. every contribution payload digest matches the complete canonical
   `GraphContribution` payload in the plan
3. every contribution `world_id` matches `plan.world_id`
4. identity-decision references are rejected until their records are included
5. rebuild equivalence and integrity before promotion

It records the complete initialization-plan digest, focus session, ordered
contribution IDs, payload digests, and `plan.approval_attestation` on the
receipt with `plan_binding_verified=true`. Idempotency compares that complete
plan binding, not only the attestation. The Kernel does **not** re-load an
on-disk bundle to independently certify the attested `bundle_digest`.

After the staged world is renamed into production, that rename is the commit
point. Cleanup and diagnostics are best-effort and cannot turn a published
world into an error response.

## Structural validation

Production storage/integrity uses `validate_union_supergraph_store_payload`,
which now validates each `assertion_support` record against
the neutral `graph_memory.evidence.assertion_support.DurableAssertionSupport`
model, requires key/`assertion_id` equality, and checks local
evidence/artifact/graph-object references.

`validate_union_supergraph_fixture` remains the richer representative-fixture
gate.

## Follow-ons

- **PR006D2** — Eldyrwild acceptance policy + bootstrap service/CLI + review projection
- **PR006D3** — `/ingest` review/activation UI against the D2 contract
- **PR007** remains blocked until D1–D3 complete
