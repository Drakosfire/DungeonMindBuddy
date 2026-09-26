# REPORT — CON-READY PLAY-1 WorldKeeper consumer proof

**Status:** IMPLEMENTED / REVIEW PENDING — not an acceptance disposition

**Implementation base:** `main@f30b4c906bb179b25f00207c40cb38c0debdc264`,
the PR #767 merge. PLAY-0 / PR #753 is accepted and merged. The reviewed
handoff is activated on this fresh-main-based branch under the user's explicit
exception to main-first handoff placement. This is one serial PLAY-1 PR.

## Installed authority

- WorldKeeper `49a8620f066ce7ef8972a699020c012f50af9158` — reviewed #8 head,
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
V3-backed profile revision 2, with `ent:pippa` and exact `EvidenceRefV3` ID
`ev:play-session-note` in the graph payload. No source reader is involved.

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
Additional tests cover missing evidence, stale prepared values,
client-operation collisions, reference integrity, unsupported product
semantics (including both object- and relationship-side visibility, reveal, and
scope rejection), and source-level guards against DungeonMind write APIs or
old Buddy writer imports. Production route modules remain unmodified and do
not import this consumer.

## Verification

- `uv sync --locked`: PASS (WorldKeeper exact reviewed #8 head pin).
- Focused PLAY-1 test: 39 passed.
- V6.1 and V6.0.1 regressions: 29 passed.
- Scoped Ruff: PASS.
- WorldKeeper runtime import: PASS.
- `git diff --check`: PASS.
- Default non-live suite: collection stops on eight inherited missing-module
  errors. `main@f30b4c9` lacks the same imported modules/tests
  (`recap_projection`, `graph_ingest_verified_snapshot`, `digest_audit`,
  `test_graph_memory_merge_reconciliation_planner`, and
  `bench_world_graph_warm_path`); PLAY-1 adds none of those paths and changes
  no legacy import path. This is baseline debt, not a PLAY-1 test failure.

## Still false / next gate

The implementation is not accepted until review of the exact implementation
head. No production route, persistent/PostgreSQL authority,
browser surface, source admission, V2→V3 migration, or live Eldyrwild state
has been changed. PLAY-2 is not authorized here.
