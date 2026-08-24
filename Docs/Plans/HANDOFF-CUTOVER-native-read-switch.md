---
pr_body_template: |
  ## Handoff pointer
  - Workstream: CUTOVER / native-read switch
  - Direction: DESIGN → CODE → REVIEW
  - Handoff: Docs/Plans/HANDOFF-CUTOVER-native-read-switch.md
  - Implementation repository: Drakosfire/DungeonMindBuddy

  Remove the temporary `DUNGEONMIND_WORLD_GRAPH_DIRECT_READ` rollout gate and
  make native DungeonMind reads unconditional for every production World Graph
  read in `dungeonmind` authority mode. Preserve explicit non-production root
  overrides for tests/tooling and keep `buddy_files` / `quiesced` behavior
  unchanged. Migrate the one known Hermes latest-recap comparison that still
  asks the hydration router for a Buddy-shaped graph root.
---

# HANDOFF — CUTOVER: native DungeonMind read switch

**Created:** 2026-08-24  
**Status:** READY TO IMPLEMENT  
**Workstream:** CUTOVER / World Graph runtime retirement  
**Direction:** DESIGN → CODE → REVIEW  
**Implementation repository:** `Drakosfire/DungeonMindBuddy`  
**Buddy base:** `main` `54779636750ebf7a639aef8a6184cc61ead9c860` (merge of Buddy PR #632)  
**DungeonMind pin:** `c5d3688587b0f5d506e0f7d64f33eb0628bac896` (DungeonMind PR #45 merge / R.3a)  
**Suggested implementation branch:** `cutover/native-read-switch`  
**Suggested PR title:** `CUTOVER: make DungeonMind native reads unconditional`  
**Predecessor:** Buddy PR #632 — R.3a pin + sealed witness + `SWITCH_READY`  
**Successor:** Buddy graph-runtime demolition / hydrated-runtime retirement

> **Dispatch ruling:** PIN + VERIFY is complete. Operator dogfood after #632 was
> acceptable with no noticed read-path issues, including deliberate Buddy
> process replacement while `DUNGEONMIND_WORLD_GRAPH_AUTHORITY=dungeonmind`
> and native reads were enabled. The temporary rollout gate has served its
> purpose. This slice removes the fallback choice from the production read
> path; it does **not** delete the old graph runtime yet.

---

## 1. Mission

Make the following statement mechanically true:

> **When `DUNGEONMIND_WORLD_GRAPH_AUTHORITY=dungeonmind`, every production
> World Graph read executes from DungeonMind's native read services. A
> DungeonMind failure fails closed. Buddy never substitutes its hydrated graph
> runtime.**

Today the normal projection/retrieval services still have two possible
`dungeonmind` read paths:

```text
DUNGEONMIND_WORLD_GRAPH_AUTHORITY=dungeonmind
        |
        +-- DUNGEONMIND_WORLD_GRAPH_DIRECT_READ=1
        |      -> DungeonMind native projection/retrieval
        |
        +-- unset / 0
               -> DungeonMind authority
               -> hydrate Buddy-shaped graph cache
               -> Buddy graph kernel read
```

After this PR:

```text
DUNGEONMIND_WORLD_GRAPH_AUTHORITY=dungeonmind
        |
        +-> DungeonMind native projection/retrieval
```

There is no rollout decision left.

This slice also closes one production exception discovered during design:
`apps/live_control_server/services/live_agent_loop.py::_latest_recap_graph_root`
currently calls `world_graph_authority.route_service_read(...)` directly.
That route hydrates a Buddy-shaped graph even when ordinary R.3 direct reads
are enabled. The latest-recap comparison must stop depending on a hydrated
filesystem graph in `dungeonmind` mode before this slice can claim success.

---

## 2. Governing invariants

### 2.1 Authority means read authority

`dungeonmind` is no longer merely the durable truth source behind a temporary
Buddy read model. In production it names the system that serves the graph read.

No production `dungeonmind` request may:

- build or reuse a DungeonMind-hydrated Buddy graph;
- invoke Buddy contribution replay to answer a read;
- select the frozen Buddy graph as an emergency fallback;
- switch behavior because `DUNGEONMIND_WORLD_GRAPH_DIRECT_READ` is present,
  absent, `0`, `1`, or any other value.

### 2.2 Fail closed

If the DungeonMind database URL is missing, PostgreSQL is unavailable, the
receipt/head is invalid, an exact pin cannot resolve, or a native read fails,
the product returns the existing typed failure/unavailable behavior.

It must **not** call the hydrated authority router after a native failure.

### 2.3 Current R.3 semantics are frozen

This PR is routing cleanup, not graph semantics work.

Preserve the accepted R.3 supported-client contract:

- head and exact DungeonMind pin reads;
- the historical Buddy-A → DungeonMind-D_A bridge where currently supported;
- campaign and world-cross-campaign scope;
- GM / PLAYER admissibility and fail-closed unknown values;
- object lookup;
- deterministic search / referent behavior;
- depth-1 / depth-2 neighborhood;
- evidence retrieval;
- source-anchor emit → revalidate → open;
- current Buddy DTO/wire contracts;
- current approved semantic-divergence ledger.

The sealed witness remains:

```text
0 blocking
0 errored
199 approved semantic divergence
```

### 2.4 Explicit non-production roots remain a tooling seam

The current services deliberately treat an explicit `root` that is different
from `config.world_graph_root()` as a test/tooling override. Preserve that
behavior in this PR.

Definition for this slice:

```text
production read
  = root is None
    OR resolved(root) == resolved(config.world_graph_root())

non-production override
  = explicit root is provided
    AND resolved(root) != resolved(config.world_graph_root())
```

In `dungeonmind` authority mode:

- a production read is always native DungeonMind;
- a genuinely different explicit root may continue to exercise file/kernel
  fixtures for tests and tools;
- merely passing `world_graph_root()` explicitly is **not** an escape hatch.

Do not expose a new product/API parameter whose purpose is to manufacture a
non-production root override.

### 2.5 Other authority modes are not being retired here

Keep the existing intentional behavior of `buddy_files` and `quiesced` in
this slice. Their eventual disposition belongs to graph-runtime demolition.

---

## 3. Current implementation facts

These are the concrete seams to change, not suggestions to redesign broadly.

### 3.1 Rollout configuration

`apps/live_control_server/config.py` currently defines:

- `WORLD_GRAPH_DIRECT_READ_ENV = "DUNGEONMIND_WORLD_GRAPH_DIRECT_READ"`
- `world_graph_direct_read_enabled()`

Delete both active runtime concepts. Historical documentation may still mention
the former rollout gate as history; do not rewrite historical evidence merely
to make `rg` globally empty.

### 3.2 Projection dispatch

`apps/live_control_server/services/world_graph_projection.py` currently uses
`_direct_read_active(root)` and requires both:

1. `authority == dungeonmind`; and
2. `world_graph_direct_read_enabled()`.

Change the production predicate so `dungeonmind` + production root is enough.
The existing direct adapter remains the implementation:
`_project_world_graph_direct(...)`.

Do not redesign the adapter in this slice.

### 3.3 Retrieval dispatch

`apps/live_control_server/services/world_graph_retrieval.py` has the same gate
for:

- search;
- exact object;
- neighborhood;
- evidence;
- source-anchor open.

Make all five operations unconditional native reads for `dungeonmind`
production requests.

### 3.4 Known hidden hydrated production read: Hermes latest recap

`apps/live_control_server/services/live_agent_loop.py::_latest_recap_graph_root`
currently calls the legacy authority router directly to obtain a hydrated
Buddy graph root. `src/graph_memory/interaction/latest_recap.py` then calls
`load_current_world_graph(...)` and derives:

- admitted graph session ids;
- latest graph session id;
- object/relationship ids tied to the recap session.

This is a real production graph read even though it is not one of the ordinary
projection/retrieval HTTP operations. It must be migrated in this slice.

The existing native Buddy projection DTO already carries the facts needed for
this feature:

- snapshot revision identity;
- source-artifact `campaign_id` / `session_id`;
- evidence `session_id`;
- node evidence refs / evidence badges;
- relationship `session_ids` and evidence refs.

**Preferred shape:** make the latest-recap comparison storage-neutral rather
than teaching DungeonMind about a Buddy/Hermes workflow.

A small typed/internal value such as `LatestRecapGraphFacts` is acceptable:

```text
revision_id
session_ids
object_or_relationship_ids_by_session
```

Then provide two producers:

1. legacy file-store → facts, for `buddy_files` / explicit fixture roots;
2. native `WorldGraphProjection` → facts, for `dungeonmind` production.

`build_latest_recap_change_context(...)` should compare the admitted recap to
those facts, not require a `UnionSupergraphStore` specifically.

For the DungeonMind path, use the already-supported projection service with:

- the same `world_id` / campaign;
- GM admissibility;
- campaign scope;
- the exact graph revision pin already carried by the graph envelope when
  present, otherwise head;
- no lossy query-text filtering for the comparison facts.

Do **not** add a new DungeonMind API solely for this product workflow unless the
existing native projection demonstrably lacks required accepted facts.

If the projection contract turns out not to contain enough admitted
session/evidence identity to preserve the feature, **STOP** and report the
specific missing library fact. Do not hydrate as a workaround.

---

## 4. Required implementation sequence

### Step 0 — production-read inventory

Before editing, run a bounded inventory over production code for direct access
to hydration/file graph reads. At minimum search:

```bash
rg -n \
  'WORLD_GRAPH_DIRECT_READ_ENV|world_graph_direct_read_enabled|DUNGEONMIND_WORLD_GRAPH_DIRECT_READ|route_service_read\(|ensure_hydrated_authority\(|load_current_world_graph\(' \
  apps src scripts tests
```

Classify every production occurrence.

Known production callers at dispatch:

- projection service;
- retrieval service;
- Hermes latest-recap path in `live_agent_loop.py`.

If another product path directly hydrates/loads the World Graph, include it
only if it is the same bounded read-switch responsibility. If it represents a
new product capability or a materially different migration, STOP and hand it
back rather than silently widening the PR.

### Step 1 — retire the rollout flag

Delete the active config constant/function and remove the gate check from
projection and retrieval dispatch.

Do not replace it with another equivalent feature flag.

An obsolete environment variable left in an operator shell must have no effect
on routing. Tests should cover at least `0`, `1`, and an arbitrary non-empty
value to prove the old control plane is dead.

### Step 2 — make normal projection/retrieval dispatch unconditional

For a production root under `dungeonmind` authority:

- projection → `_project_world_graph_direct`;
- search/object/neighborhood/evidence/anchor → existing direct adapter methods.

The hydrating authority router must not be called on those requests, including
when native read construction fails.

### Step 3 — migrate latest-recap comparison off hydration

Replace the `dungeonmind` path that asks for a hydrated graph root with native
projection-derived graph facts.

Preserve current product outcomes:

- `changed`;
- `no_change`;
- `memory_lag`;
- `unknown`;
- `source_unavailable`.

Preserve recap-registry/source-file authority. This migration only changes
where graph comparison facts come from.

DungeonMind/native failure should retain the current safe degradation to
`unknown` / `latest_recap_authority_unavailable` (or the current equivalent)
without reading the frozen Buddy graph.

### Step 4 — update executable witnesses/tests

The R.3 comparison harness currently knows about the rollout flag. Make the
harness exercise the new production rule: `authority=dungeonmind` is sufficient.

Do not change divergence classifications or the sealed ledger.

### Step 5 — atomic current-state docs

In the implementation PR, update the canonical CUTOVER state atomically:

- `HANDOFF-CUTOVER-r3a-dungeonmind-pin.md` → LANDED / dogfood accepted;
- `PR-TRACKER-campaign-supergraph.md` and ACTIVE_AUTHORITY mirror;
- `ROADMAP-campaign-supergraph.md` and ACTIVE_AUTHORITY mirror;
- `STEWARDS-ANCHOR-cutover.md` where it describes the live read path;
- this handoff → implementation/review state.

Required forward sequence after this PR:

```text
DONE  #632 pin + verify
DONE  operator native-read dogfood
DONE  native-read switch          <- this PR when accepted
NEXT  demolish Buddy graph runtime
```

Historical baseline/report sections may retain statements such as “the gate was
formerly default-off” when clearly historical.

---

## 5. Explicitly out of scope

Do **not** use this PR to:

- delete `graph_memory.kernel` wholesale;
- delete `UnionSupergraphStore` wholesale;
- delete contribution replay / rebuild code wholesale;
- delete the hydration implementation itself;
- delete all hydrated-cache files or cache configuration;
- retire `buddy_files` or `quiesced` modes;
- redesign `direct_services_from_config()`;
- introduce a global DungeonMind service/cache singleton;
- further optimize R.3a;
- change graph admission, scope, evidence, anchor, or search semantics;
- change write/publication routing;
- change Play Surface behavior;
- change the agent harness or Hermes provider/tool loop;
- add a new DungeonMind product-specific “latest recap” capability.

The point of this PR is to make the old hydrated runtime **unreachable from the
production DungeonMind read path**. Deletion comes next.

---

## 6. Acceptance tests

### 6.1 Owning Python cohort

At minimum:

```bash
uv run pytest \
  tests/test_cutover_direct_dungeonmind_world_graph_reads.py \
  tests/test_cutover_dungeonmind_world_graph_authority.py \
  tests/test_world_graph_projection_routes.py \
  tests/test_world_graph_retrieval_routes.py \
  tests/test_latest_recap_change.py \
  tests/test_live_query_hermes_graph.py
```

Record exact collected / passed / skipped / failed counts in the handback.

### 6.2 Routing explosion proofs

Add or update tests that replace the old machinery with explosion stubs.

For `authority=dungeonmind` + production root, all of these must remain
unreachable while native reads succeed:

- `world_graph_authority.route_service_read` for ordinary projection/retrieval;
- Buddy kernel projection/retrieval functions;
- hydration entry points;
- frozen/current Buddy graph loaders.

For the Hermes latest-recap `dungeonmind` path, prove that both the hydrating
router and `load_current_world_graph` can explode while the comparison is still
computed from native admitted facts.

### 6.3 Obsolete env cannot reactivate hydration

For otherwise identical `dungeonmind` production reads, test with:

```text
DUNGEONMIND_WORLD_GRAPH_DIRECT_READ unset
DUNGEONMIND_WORLD_GRAPH_DIRECT_READ=0
DUNGEONMIND_WORLD_GRAPH_DIRECT_READ=1
DUNGEONMIND_WORLD_GRAPH_DIRECT_READ=garbage
```

All four must take the same native path.

The implementation need not explicitly parse/reject the obsolete variable;
it simply must no longer control anything.

### 6.4 Explicit-root boundary

Prove both sides:

1. `root=None` or `root=config.world_graph_root()` + `dungeonmind` → native;
2. an explicit different fixture root → existing file/kernel fixture behavior.

This is the only retained read-path distinction in this PR.

### 6.5 Fail-closed authority failure

Under `dungeonmind` production routing, cover at least:

- missing database URL;
- unavailable database / direct-service construction failure;
- unknown exact revision pin.

Expected: typed existing failure behavior and **zero hydration/frozen-store
fallback**.

### 6.6 Other modes unchanged

Keep focused regression proof that `buddy_files` / `quiesced` continue their
current intended file-path behavior in this slice.

### 6.7 Sealed supported-contract witness

Rerun the current R.3 witness against the live Eldyrwild authority after the
routing change.

Expected:

```text
17 cases
0 errored
0 blocking
199 approved semantic divergence
```

The harness should not require the retired direct-read env flag to obtain the
native path.

### 6.8 Live smoke without the retired flag

Before handback, start or exercise Buddy with:

```text
DUNGEONMIND_WORLD_GRAPH_AUTHORITY=dungeonmind
DUNGEONMIND_WORLD_GRAPH_AUTHORITY_DATABASE_URL=<live authority>
DUNGEONMIND_WORLD_GRAPH_DIRECT_READ absent
```

Demonstrate at least:

- one product projection;
- one retrieval/search/object operation;
- one evidence or source-anchor operation;
- one exact revision pin;
- the latest-recap comparison path if its test fixture can be exercised safely.

No old flag may be required.

---

## 7. Static disposition evidence

At handback provide two inventories.

### 7.1 Retired rollout control

In active executable code, there should be no dependency on:

```text
WORLD_GRAPH_DIRECT_READ_ENV
world_graph_direct_read_enabled
DUNGEONMIND_WORLD_GRAPH_DIRECT_READ
```

Historical docs may still contain the literal name.

### 7.2 Remaining hydrated-runtime consumers

List every remaining production import/call into:

```text
apps/live_control_server/integrations/dungeonmind_kernel/world_graph_authority.py
src/graph_memory/kernel
src/graph_memory/world_supergraph
src/graph_memory/union_supergraph
```

Classify each as:

- write/publication path;
- `buddy_files` / `quiesced` legacy mode;
- test/tooling;
- obsolete and ready for deletion.

This inventory is the input to the successor demolition handoff. Do not delete
all of it here.

---

## 8. Stop conditions

STOP and hand back rather than broadening the PR if any of the following occurs:

1. A supported production `dungeonmind` read still requires hydration after the
   bounded latest-recap migration.
2. The latest-recap feature cannot be expressed from the currently supported
   DungeonMind/native projection facts without losing a surviving product
   requirement. Name the exact missing fact/API.
3. The sealed R.3 witness gains any blocking or errored row.
4. A DungeonMind failure reaches Buddy hydration/frozen state as fallback.
5. Preserving explicit test/tooling roots would require exposing a new product
   escape hatch.
6. `buddy_files` / `quiesced` behavior must be redesigned to land the switch.
7. The change starts deleting broad graph-runtime internals instead of making
   them unreachable.
8. A new DungeonMind capability, cache subsystem, or semantic rule appears
   necessary without direct evidence from the current client contract.

---

## 9. Review bar

This PR is mergeable only when the reviewer can make all of these statements:

- `dungeonmind` + production root has exactly one graph-read implementation:
  native DungeonMind;
- the old direct-read env variable has no routing power;
- ordinary projection/retrieval cannot reach the hydration router;
- Hermes latest-recap comparison cannot reach a hydrated Buddy graph in
  `dungeonmind` mode;
- DungeonMind failure fails closed;
- current direct semantics and wire contracts are unchanged;
- explicit different-root fixtures still work without becoming a product
  fallback;
- the remaining hydrated graph runtime is now removable by reachability in the
  successor slice.

---

## 10. Required handback

Return:

1. exact Buddy base SHA and implementation head SHA;
2. changed-file list;
3. exact code points where the rollout flag was removed;
4. exact production routing rule after the change;
5. latest-recap migration design and tests;
6. proof that obsolete env values do not alter routing;
7. fail-closed no-fallback proofs;
8. explicit-root boundary proofs;
9. owning test counts;
10. sealed live R.3 witness result;
11. live smoke result without the retired flag;
12. remaining hydrated-runtime consumer inventory by classification;
13. atomic roadmap/tracker/steward status update;
14. workspace/branch status;
15. explicit recommendation: `DEMOLITION_READY` or `DEMOLITION_NOT_READY`.

Expected disposition if all acceptance criteria pass:

```text
DEMOLITION_READY
```

The successor then deletes the old Buddy graph runtime rather than maintaining
it as an alternate production implementation.
