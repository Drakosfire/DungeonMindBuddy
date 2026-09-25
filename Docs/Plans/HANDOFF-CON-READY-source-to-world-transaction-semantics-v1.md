# HANDOFF — CON-READY: source-to-World transaction semantics

**Created:** 2026-09-22
**Retired:** 2026-09-25
**Status:** HISTORICAL MIGRATION EVIDENCE — RETIRED / DO NOT DISPATCH
**Flow / owner:** `CON-READY`
**PR topology:** historical; no implementation lane or write lease
**Current authority:** `Docs/Design/DESIGN-source-to-world-authoring-interaction-contract.md`

## Why this handoff is retired

This handoff recorded a real Buddy classifier defect: a same-batch relationship
could be rejected when its endpoint was an object created by the same
transaction.

The architectural decision is complete. The destination is not continued
growth of Buddy's prospective-ID classifier. Same-transaction semantics live
through WorldKeeper and DungeonMind V5.4.

```text
Buddy
  assigns unique client_op_id values

WorldKeeper
  interprets result_of(client_op_id)
  resolves semantic dependencies
  prepares one coherent change
  does not predict durable IDs

DungeonMind V5.4
  allocates durable IDs atomically
  substitutes them through dependent operations
  publishes one child or none
  returns client-operation → durable-result mappings
```

## Preserved acceptance evidence

- valid durable-to-`result_of(client_op_id)` relationships prepare coherently;
- every `client_op_id` is non-empty and unique;
- missing, duplicate, wrong-kind, out-of-transaction, or otherwise
  unresolvable references fail closed;
- same-intent result references are order-independent;
- prepare performs no durable mutation;
- confirmation binds to the exact prepared change and parent;
- one confirmation produces one immutable child or no mutation;
- object and dependent relationship use the same DungeonMind-allocated ID;
- retry/recovery does not create a second child;
- result mappings and child read-back prove the outcome.

## Historical Buddy lease

The former candidate paths are reconstructable migration evidence only:

- `apps/live_control_server/services/graph_object_authoring_prepare.py`;
- `tests/test_graph_object_authoring_prepare.py`;
- `tests/test_graph_object_authoring_published_recap_write.py`.

They are not leased. Do not reactivate this handoff or treat the legacy
classifier as the destination.

## Next authority

A fresh handoff may authorize a bounded Buddy consumer migration to the
WorldKeeper WK-5 seam. It must start from current `main`, declare PR topology,
and leave production switching/runtime/bridge-genesis work to its later
cutover owner.

```text
STATUS = HISTORICAL
BUDDY LEGACY CLASSIFIER REPAIR = NOT THE DESTINATION
BUDDY CONSUMER MIGRATION = NEXT, NOT YET AUTHORIZED
V2-3 = NOT AUTHORIZED
```
