# REPORT — CON-READY PLAY-1 WorldKeeper consumer proof

**Status:** IMPLEMENTED / REVIEW PENDING — not an acceptance disposition

**Dispatch base:** `1367bf2cc3828055ed71774414086a2c3fa421ff`, the
checked-in PLAY-0 PR #753 head. The user authorized execution before that
handoff reached `main`; PR #753 has not been merged by this implementation.
The implementation branch remains dependent on the PLAY-0 design decision.

## Installed authority

- WorldKeeper `a0a70db275cf6c5f3876fe7b4d2a557de12388f5` — #8 merge,
  verified from installed package `direct_url.json`.
- DungeonMind `0f709d76fdc53bac9c9258d1751463ae2c76ca71` — unchanged Buddy
  runtime pin, verified from installed package `direct_url.json`.
- Buddy DomainContract `dungeonbuddy.world` revision 2 digest
  `d12f3a517a37d29a2ba52455d9ae1691bc5e4ff3fd6853b701a9e28e46ec65cd`.
- Buddy custom SemanticProfile `dungeonbuddy.dnd5e` revision 2 digest
  `d40a352d1c6cbd24df68be887be6dc65a470e4cea8fb64970ef9ad89b96a3339`.

## Public consumer seam

`PlayAuthoringContext` carries exact space, campaign, admitted evidence IDs,
and producer. `WorldKeeperGraphAuthoringConsumer` accepts an injected
`WorldChangeService` and exposes `build_intent`, `prepare`, and `commit`.
The consumer maps Buddy proposal DTOs only; WorldKeeper performs preparation,
publication/recovery coordination, allocation delegation, and exact-child
verification through its accepted runtime.

Supported mapping:

- staged `object` create → `CreateObject`; name, recognized classification,
  and nonblank summary → distinct `CreateFact` operations with transaction-local
  IDs;
- staged directed `relationship` create → `CreateRelationship`;
- exact existing endpoint → `DurableObjectRef`; same-batch object endpoint →
  `ResultOf(client_op_id)`, independent of proposal order;
- accepted fixed qualified relationship term → identical term; valid
  GM-authored local term → `dungeonbuddy.custom:<exact-term>`;
- canonical GM/campaign metadata uses exact admitted evidence IDs.

Unsupported semantics raise `PlayAuthoringMappingError` before service calls:
`link_existing`, merge, update, manual/authored-node endpoint, unresolved
local reference, unknown object kind, aliases/role, undirected or extra
relationship detail, unsupported visibility/graph scope, invalid term, or
invalid/duplicate IDs. The mapper has no source admission, profile transition,
durable-ID prediction, production writer fallback, or predicate substitution.

## Runtime witnesses

The canonical test seeds an in-memory native vNext parent pinned to the Buddy
V3-backed profile revision 2, with `ent:pippa` and exact evidence ID
`ev:play-session-note`. Its source artifact/revision fixture is coherent.

The submitted relationship appears before the brewery object, yet maps to
`Pippa dungeonbuddy.custom:works_at ResultOf(brewery)`. Prepare leaves the
head and event list unchanged. Explicit commit yields one child with a
DungeonMind-allocated brewery `ent:*`, relationship `asrt:*`, exact predicate,
subject `ent:pippa`, and target equal to that allocated brewery. The result
reports exact-child read-back. Retrying the same prepared value returns the
same result and adds no head event.

Independent `mentors` and `trained_by` tests take the same generic namespace
branch and appear as exact qualified predicates in committed children. A
V2-pinned parent fails at prepare with no profile transition or child.
Additional tests cover missing admitted evidence, stale prepared values,
client-operation collisions, reference integrity, unsupported product
semantics, and source-level guards against DungeonMind write APIs or old Buddy
writer imports. Production route modules remain unmodified and do not import
this consumer.

## Verification

- `uv sync --locked`: PASS (100 packages; WorldKeeper exact #8 merge pin).
- Focused PLAY-1 test: 29 passed.
- V6.1 and V6.0.1 regressions: 29 passed.
- Scoped Ruff: PASS.
- WorldKeeper runtime import: PASS.
- `git diff --check`: PASS.
- Default non-live suite: collection stops on eight inherited missing-module
  errors. The exact PLAY-0 base lacks the same imported modules/tests
  (`recap_projection`, `graph_ingest_verified_snapshot`, `digest_audit`,
  `test_graph_memory_merge_reconciliation_planner`, and
  `bench_world_graph_warm_path`); PLAY-1 adds none of those paths and changes
  no legacy import path. This is baseline debt, not a PLAY-1 test failure.

## Still false / next gate

PR #753 remains the unmerged PLAY-0 design predecessor at dispatch. The
implementation is not accepted until review of the exact implementation head,
reconciliation onto fresh `main` after #753 merges, and the remaining PR
topology decision. No production route, persistent/PostgreSQL authority,
browser surface, source admission, V2→V3 migration, or live Eldyrwild state
has been changed. PLAY-2 is not authorized here.
