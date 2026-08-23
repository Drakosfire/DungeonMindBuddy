---
pr_body_template: |
  ## Handoff pointer
  - Workstream: CUTOVER / R.3 — direct DungeonMind production reads
  - Direction: DESIGN → CODE → REVIEW
  - Handoff: Docs/Plans/HANDOFF-CUTOVER-direct-dungeonmind-production-reads.md
  - Implementation repository: Drakosfire/DungeonMindBuddy

  ## Exact predecessor truth
  - Buddy implementation base: `b850b9f8126a8c8488d17b3bdb6f99a60a162338` (main at dispatch).
  - DungeonMind R.1 direct projection landed in PR #38.
  - DungeonMind R.2 direct retrieval landed in PR #40 / `fd0b76056ecd159662dd1d314858aab5c9ff4440`.
  - DungeonMind R.2a observability + benchmark landed in PR #41 / `b3f419b08676eaca763c8a75c374be6e96ee624e`.
  - Eldyrwild authority cutover is already complete; DungeonMind is the living World Graph authority. Do not reopen adoption/cutover readiness.

  Replace Buddy's production World Graph read execution in `dungeonmind`
  authority mode with DungeonMind's native R.1/R.2 read services. Preserve the
  existing Buddy product wire surface where semantically supported, prove
  normalized semantic parity and actual-current performance, and make every
  production read independent of Buddy hydration, contribution rebuild,
  UnionSupergraphStore construction, and graph_memory.kernel read operations.
---

# HANDOFF — R.3: direct DungeonMind production reads

**Created:** 2026-08-22  
**Status:** IMPLEMENTATION IN PROGRESS — rebased onto Buddy `main` after #630 and the live Eldyrwild V4 repair  
**Workstream:** CUTOVER / World Graph runtime retirement  
**Direction:** DESIGN → CODE → REVIEW  
**Implementation repository:** `Drakosfire/DungeonMindBuddy`  
**Exact Buddy base at original dispatch:** `b850b9f8126a8c8488d17b3bdb6f99a60a162338`  
**Current rebase base:** Buddy `origin/main` `3b25dbd89664b5a148ad76e0f5780b5ddc742f9a` (#630 merge)  
**Required DungeonMind pin:** `519b2c96fc42d22f3113cc9ca0d48bc70b6780e5` (merge of DungeonMind PR #43; separately reviewed V4 repair predecessor on top of #41 R.1/R.2/R.2a)  
**Original dispatch pin (historical):** `b3f419b08676eaca763c8a75c374be6e96ee624e` (DungeonMind PR #41)  
**Suggested branch:** `cutover/direct-dungeonmind-production-reads`  
**Suggested PR title:** `CUTOVER: retire Buddy graph hydration from production reads`  
**Predecessor:** DungeonMind R.2a — World Graph read observability + cutover benchmark baseline  
**Named successor:** DungeonMind R.3a — reusable World Graph read context / parsed immutable revision reuse

> **Dispatch ruling:** authority transfer is finished. This PR is not another
> migration/readiness exercise. Its job is to remove Buddy's graph engine from
> the normal product **read** path while preserving read semantics and creating
> the frozen parity/performance witness that later DungeonMind optimization
> must not change.
>
> Do not optimize DungeonMind in this PR. Do not delete Buddy's write-side
> compatibility machinery merely because production reads stop using it.

---

## 1. Mission

When `DUNGEONMIND_WORLD_GRAPH_AUTHORITY=dungeonmind`, every mounted production
World Graph projection and retrieval operation must execute directly against
DungeonMind's exact published World Graph revision through the landed R.1/R.2
application services.

A successful production read in DungeonMind authority mode must require **none**
of the following:

```text
Buddy UnionSupergraphStore
Buddy contribution replay
Buddy contribution rebuild
Buddy graph revision publication
Buddy hydrated cache root
Buddy world_read_runtime resident
Buddy graph_memory.kernel projection/retrieval operations
frozen Buddy World Graph files
private Buddy hydrated revision identity
```

The target path is:

```text
product request
  → Buddy product/service boundary
  → thin DungeonMind request adapter
  → DungeonMind PostgreSQL repositories
  → DungeonMind WorldGraphProjectionService / WorldGraphRetrievalService
  → thin Buddy product DTO adapter
  → existing product consumer
```

Not:

```text
product request
  → DungeonMind rows
  → translate rows back to Buddy contributions
  → rebuild UnionSupergraphStore
  → publish private Buddy revision
  → call Buddy Graph Kernel
  → rewrite Buddy revision id to DungeonMind id
```

The second path is the current derivative hydration architecture and is exactly
what R.3 retires from production reads.

### Merge-ready invariant

> In DungeonMind authority mode, product graph reads are pure consumers of one
> exact DungeonMind published revision. Buddy may adapt request/response shape
> and perform clearly non-authoritative product presentation joins, but it may
> not reconstruct a graph, choose graph truth, broaden admissibility, replay
> contributions, invoke the legacy graph read kernel, or fall back to Buddy
> files.

---

## 2. Why this PR exists

DungeonMind already owns Eldyrwild authority, but Buddy still owns the execution
engine for every normal graph read.

Current read routing in
`apps/live_control_server/integrations/dungeonmind_kernel/world_graph_authority.py`
describes the architecture accurately: DungeonMind durable rows are translated
back into Buddy contribution/identity records, replayed into a temporary
`UnionSupergraphStore`, rebuilt/published as a private Buddy revision, and then
served through the old Buddy kernel. The cache is derivative rather than
second authority, but the entire Buddy graph runtime remains in the product
request path.

Current projection then calls Buddy runtime machinery such as
`resolve_projection_read_context` and `project_world_graph_from_context`.
Current retrieval calls Buddy kernel operations such as
`search_campaign_graph`, `get_campaign_object`, `get_object_neighborhood`,
`get_object_evidence`, `resolve_admitted_anchor_match`, and
`read_source_anchor`.

DungeonMind R.1/R.2 now expose the native seam required to remove that detour,
and R.2a has characterized its current cost before cutover.

This slice establishes a much stronger boundary:

```text
Before R.3
DungeonMind owns truth
Buddy reconstructs truth and executes reads

After R.3
DungeonMind owns truth AND graph-semantic read execution
Buddy consumes/adapts the result
```

That is the first point at which Buddy's graph engine becomes genuinely legacy
for production reads.

---

## 3. Authoritative docs and exact predecessor truth

Read these before editing, in order:

### Buddy

1. `AGENTS.md`
2. `Docs/Plans/STEWARDS-ANCHOR-cutover.md`
3. `Docs/Plans/HANDOFF-CUTOVER-whole-world-authority-transfer.md`
4. `Docs/Plans/HANDOFF-CUTOVER-dungeonmind-authority-completion.md` — historical completed predecessor; do not reopen it
5. this handoff
6. `Docs/Plans/PR-TRACKER-campaign-supergraph.md`
7. `Docs/Roadmaps/ROADMAP-campaign-supergraph.md`

### DungeonMind

At exact merge `b3f419b08676eaca763c8a75c374be6e96ee624e`:

1. `Docs/Handoffs/HANDOFF-cutover-direct-world-graph-projection.md`
2. `Docs/Handoffs/HANDOFF-cutover-direct-world-graph-retrieval.md`
3. `Docs/Handoffs/HANDOFF-cutover-world-graph-read-observability-benchmark.md`
4. `Docs/Benchmarks/BASELINE-world-graph-reads-r2a.md`
5. `src/dungeonmind/contracts/projection_v2.py`
6. `src/dungeonmind/application/world_graph_projection.py`
7. `src/dungeonmind/application/world_graph_retrieval.py`
8. `src/dungeonmind/application/world_graph_observability.py`
9. `src/dungeonmind/application/graph_scope.py`
10. `src/dungeonmind/application/graph_snapshot.py`

### Locked predecessor facts

- DungeonMind is already the living Eldyrwild World Graph authority.
- Live D_A→D_B has already occurred.
- Buddy local World Graph mutation is fail-closed under DungeonMind authority.
- R.1 direct projection is landed.
- R.2 direct retrieval is landed.
- R.2a read observability and the synthetic baseline are landed.
- R.2a intentionally did **not** optimize the read path.
- R.2a intentionally did **not** perform the Buddy-vs-direct real-current
  product comparison; R.3 owns that witness.

If current repository truth contradicts any exact base/pin above, stop and
re-anchor before implementation.

---

## 4. Current implementation to inspect

### 4.1 Hydration / authority adapter

Primary file:

```text
apps/live_control_server/integrations/dungeonmind_kernel/world_graph_authority.py
```

Inspect especially:

```text
bind_world_authority
hydrate_world_graph
_ensure_hydrated_revision
ensure_hydrated_authority
route_read_request
route_service_read
HydrationHandle
AuthorityReadRoute
```

Current hydration performs, among other things:

```text
DungeonMind durable state
→ verify adopted membership
→ translate DND contribution + identity records back to Buddy shapes
→ recover replay/migration metadata from frozen Buddy store
→ construct empty UnionSupergraphStore
→ write temporary Buddy contribution/identity ledger
→ rebuild_from_contributions(..., publish=True)
→ load private Buddy revision
→ coverage-check against DND revision
→ serve Buddy kernel from derivative cache
```

This remains useful historical/compatibility code for now, but **must not run on
production reads after R.3**.

Do not delete governed-write functionality from this file unless bounded
inspection proves it has no current write consumer. Read retirement and write
retirement are separate concerns.

### 4.2 Projection service

```text
apps/live_control_server/services/world_graph_projection.py
```

Current production projection:

- routes through `route_service_read()`;
- receives a hydrated Buddy graph root/private revision;
- uses `graph_memory.kernel`;
- resolves a Buddy resident read context;
- uses Buddy projection cache + recipe/prewarm infrastructure;
- calls Buddy projection semantics;
- rewrites the private Buddy revision identity back to public DungeonMind id.

After R.3, DungeonMind authority mode must not touch any of those Buddy graph
read mechanisms.

### 4.3 Retrieval service

```text
apps/live_control_server/services/world_graph_retrieval.py
```

Current operations all route through hydration and then call Buddy kernel:

```text
search_campaign_graph
get_campaign_object
get_object_neighborhood
get_object_evidence
read_source_anchor
```

The source-anchor read path currently revalidates/admit-matches through Buddy
kernel before opening source content. R.3 must make **DungeonMind** the
source-anchor admission/revalidation authority.

### 4.4 Old read optimization machinery

Inspect:

```text
apps/live_control_server/services/world_graph_projection_recipes.py
apps/live_control_server/services/world_graph_prewarm.py
src/graph_memory/world_projection_cache.py
src/graph_memory/kernel/world_read_runtime.py
```

These optimize the old Buddy projection execution path. They must not silently
keep Buddy graph reads alive after the main service switches.

R.3 should **disable/bypass** these mechanisms in DungeonMind authority mode,
not port their caching strategy into DungeonMind. R.3a will design native
DungeonMind reuse from the R.3 frozen witness.

### 4.5 Product callers that must be represented in acceptance

At minimum inspect mounted call paths for:

```text
Plan / graph lens
Build graph lens
Play / graphReference exact open
Hermes graph query / live agent loop
World Graph retrieval routes
World Graph projection routes
source-anchor opening
```

Do not approve a helper-only cutover whose mounted product path still reaches
hydration or Buddy kernel.

---

## 5. Locked design decisions

### 5.1 New direct integration boundary

Prefer a new non-legacy integration namespace:

```text
apps/live_control_server/integrations/dungeonmind/
  __init__.py
  world_graph_reads.py
```

Do **not** put the new permanent read adapter under
`integrations/dungeonmind_kernel` unless repo constraints force it. That name
represents the compatibility/hydration era we are retiring.

The direct read adapter owns only:

1. opening the configured DungeonMind repository bundle;
2. constructing the accepted v6 semantic-profile graph reader;
3. constructing R.1/R.2 application services;
4. mapping authorized Buddy request context to DungeonMind v2 request context;
5. invoking exactly one native DungeonMind operation;
6. adapting admitted DungeonMind results to existing Buddy product contracts;
7. mapping stable authority/application errors to the existing service error
   envelope.

It does **not** own graph semantics, caching, contribution replay, source-body
search, LLM fallback, vector retrieval, or a new durable store.

### 5.2 Dependency pin

Buddy currently pins DungeonMind PR #43 (the reviewed V4 repair
predecessor). R.3 must remain pinned to exactly:

```text
519b2c96fc42d22f3113cc9ca0d48bc70b6780e5
```

That pin is a descendant of the original dispatch pin
`b3f419b08676eaca763c8a75c374be6e96ee624e` (#41) and still exposes the
reviewed R.1/R.2/R.2a contracts plus V4 receipt/manifest types.

Do not float the dependency to `main`.

### 5.3 Scope mapping

The semantic mapping is fixed:

```text
Buddy scope_mode="campaign"
  → DungeonMind ScopeModeV2.CAMPAIGN

Buddy scope_mode="world"
  → DungeonMind ScopeModeV2.WORLD_CROSS_CAMPAIGN
```

Do **not** map Buddy `world` to DungeonMind v2 `WORLD`; DND `WORLD` means
world-owned-only and would silently narrow the existing Buddy cross-campaign
lens.

`admissibility` maps only through the closed DungeonMind `GM` / `PLAYER`
vocabulary. Unknown values fail closed.

### 5.4 Exact revision identity

For normal DungeonMind ids:

```text
Buddy request revision_pin=DND_REV
  → DND request revision_pin=DND_REV
  → response revision_id=DND_REV
```

No private Buddy revision translation is allowed on this path.

Preserve the one intentional historical bridge if still part of the mounted
public contract:

```text
legacy adopted Buddy A
  → exact receipt-bound DungeonMind D_A
```

Implement this bridge from the **DungeonMind adoption receipt**, not by reading
the frozen Buddy graph head and not by hydrating D_A.

Arbitrary historical Buddy revision ids and private hydrated-cache revision ids
remain unsupported and fail closed.

A normal head/pinned DungeonMind read must not require the frozen Buddy graph at
all.

### 5.5 Focus is not authority — but do not fake parity

There is a known contract mismatch that implementation must resolve explicitly:

Buddy supports a product lens shaped like:

```text
scope_mode = world        # cross-campaign
campaign_id = longmont-c2 # product/lens qualification
focus = session-27 / C2
```

DungeonMind v2 maps Buddy `world` to `WORLD_CROSS_CAMPAIGN`, which requires
`campaign_id=None`; DungeonMind v2 also currently requires an enclosing
`campaign_id` for `SESSION` focus.

This is **not permission** to silently:

- narrow the world lens to campaign scope;
- drop focus and pretend the result is equivalent;
- add a second campaign authority inside the adapter;
- reimplement a broad projection engine in Buddy.

During implementation, classify actual mounted use:

1. If the focus is only a product-level annotation/ranking concern and exact
   current behavior can be reconstructed from **already-admitted DungeonMind
   source metadata** (for example admitted source artifact campaign/session
   identity) without broadening/narrowing authority, a small read-only adapter
   annotation is permitted. Document and parity-test it.
2. If exact mounted behavior depends on graph-semantic focus behavior that the
   DungeonMind v2 seam cannot express, **STOP** and dispatch a bounded
   DungeonMind prerequisite. Do not encode a permanent shadow projection
   engine in Buddy.

The same rule applies to every Buddy projection field: product presentation
adaptation is allowed; reconstructing missing graph truth is not.

### 5.6 Buddy public DTOs may remain temporarily

R.3 is an execution cutover, not a wire-contract rewrite.

Existing Buddy projection/retrieval Pydantic contracts may remain as product
API DTOs in this slice. The adapter may translate admitted DND values into
those DTOs.

That compatibility layer is acceptable only if:

- every graph fact comes from the selected admitted DND projection/retrieval
  result or an explicitly categorized non-authoritative product join;
- missing data is not guessed;
- no Buddy graph store/kernel is consulted;
- representation-only differences are documented;
- wire compatibility does not force reconstruction of the old graph model.

Moving DTOs out of `src/graph_memory` is a later namespace-evacuation task.

### 5.7 Projection output adaptation

For each existing Buddy projection field, classify it during implementation as
one of:

```text
A. Direct DND graph fact
B. Deterministic presentation derived from admitted DND facts
C. Product-local non-authoritative join
D. Intentionally retired / no active mounted consumer
E. BLOCKER — requires graph semantics absent from direct DND seam
```

Examples that require deliberate inspection rather than assumption:

```text
role
anchored_to_focus_session
campaign_scope presentation
adjacency / suggested expansions
source/evidence badges
external_resource
threat/statblock bindings
active_contribution_ids
history-only relationships
query_context
```

The existing hydration code explicitly notes that the DungeonMind authority
snapshot is a current-semantic view and may omit Buddy-only external-resource,
mechanics, and history-only rows. Do not silently restore those rows from the
frozen/derivative Buddy graph.

If an actively required product behavior falls into category E, stop/split.

### 5.8 Retrieval mapping

Use the native DungeonMind operations directly:

```text
Buddy search              → DND WorldGraphRetrievalService.search
Buddy exact object        → DND .get_object
Buddy neighborhood        → DND .get_neighborhood
Buddy evidence            → DND .get_evidence
Buddy anchor revalidation → DND .resolve_source_anchor
```

Bounds map exactly where both contracts have the same hard limits. Never widen
bounds as a compatibility convenience.

Search ranking is allowed to differ only where R.2 deliberately defines a new
deterministic ranking policy. Such differences must be classified in the R.3
parity witness; admissibility, exact seeds, identity, and bounded result safety
must not regress.

### 5.9 Source-anchor opening

DungeonMind R.2 intentionally does **not** open source bodies. Buddy still owns
rich product/source presentation.

Correct R.3 shape:

```text
opaque anchor token from DND result
  → DND resolve_source_anchor under exact same projection context
  → admitted DND SourceAnchorMetadata
  → bounded product source opener using already-admitted artifact/revision/span
  → excerpt/result
```

The caller must never supply a path/URI/locator to bypass DND admission.

Do not call:

```text
kernel.resolve_admitted_anchor_match
kernel.read_source_anchor
```

in DungeonMind authority mode.

DungeonMind anchor ids currently use `dm-source-anchor:v1:` while Buddy's
legacy contract historically emitted `source-anchor:v1:`. Treat the token as
opaque. Prefer passing the DND anchor id through unchanged if current mounted
wire consumers do not validate the old prefix. If prefix compatibility is a
real external contract, stop/review the smallest deterministic adapter design;
do **not** rederive Buddy anchor semantics from graph state.

### 5.10 Errors and fallback

Known DungeonMind authority/read errors must map to existing stable Buddy
service/HTTP envelopes without leaking arbitrary internal exception text.

Unexpected errors remain generic internal errors.

In DungeonMind authority mode:

```text
DND unavailable → visible failure
DND integrity error → visible failure
bad DND pin → visible failure
scope contradiction → visible failure
```

Never:

```text
DND failure → try frozen Buddy graph
DND failure → try hydrated cache
DND failure → latest preview / latest ingest
```

### 5.11 Old read caches / prewarm

Do not port Buddy's projection cache, resident read runtime, recipe registry, or
prewarm behavior into the direct adapter in R.3.

In DungeonMind authority mode, old Buddy read prewarm/recipe paths must be
bypassed or no-op so they cannot trigger hidden hydration/kernel work.

Legacy explicit Buddy/test modes may retain them temporarily.

The performance findings from R.3 become input to R.3a, where native DND reuse
will be designed against immutable revision and live source/provenance state.

---

## 6. R.3 parity witness

R.3 is the final semantic cutover witness before Buddy's read runtime is treated
as dead.

Build a bounded comparison harness that can execute the **same logical input**
through:

```text
legacy path:
DND authority → Buddy hydration → Buddy kernel

new path:
DND authority → DND R.1/R.2 direct read
```

The legacy path exists only as the comparison oracle during this PR. It is not
a permanent shadow mode.

### 6.1 Semantic cases

At minimum include:

1. head projection, campaign GM;
2. head projection, world/cross-campaign GM;
3. the mounted world + qualified session-focus case if currently used;
4. exact historical DND pin;
5. legacy A → D_A bridge;
6. exact object hit;
7. exact object miss / hidden object miss;
8. lexical search with an exact known referent;
9. search with explicit seed(s);
10. depth-1 neighborhood;
11. depth-2 neighborhood;
12. evidence retrieval for object;
13. evidence retrieval for relationship/assertion where product-supported;
14. source-anchor emit → exact revalidation → source-open path;
15. PLAYER admissibility case;
16. broken/scope-unknown provenance fail-closed case.

### 6.2 What must compare exactly

After normalizing representation-only differences:

```text
selected DND revision/head identity
is_head
scope/admissibility
admitted object identity
labels / admitted aliases / admitted summary where represented
relationship identity/endpoints/predicate
property assertion identity/value/metadata where represented
evidence identity and admitted provenance
visibility/admissibility outcome
exact seed preservation
missing/denied behavior
truncation/bounds
historical pin behavior
source-anchor contextual revalidation
```

### 6.3 Allowed classified divergence

Do not force byte equality where the successor intentionally differs.
Classify every divergence as one of:

```text
representation only
new deterministic R.2 search ranking
product-local presentation join
intentionally retired legacy-only field
blocking semantic difference
```

A blocking semantic difference prevents cutover.

Do not normalize away visibility, provenance, scope, identity, or missing-data
differences.

### 6.4 Preserve the witness

The normalized R.3 fixture/harness becomes the post-cutover regression oracle.
After R.3 merges, future R.3a optimization compares:

```text
R.3 direct result
==
R.3a optimized direct result
```

Buddy hydration is not required to remain live merely to preserve the oracle.

---

## 7. Real-current performance / operational witness

R.2a established a reproducible synthetic scaling baseline. Do not modify it.

R.3 adds the missing **actual current product graph** comparison.

### Required local/operator comparison

Against the same exact current DungeonMind revision and same logical requests,
record aggregate results for:

```text
projection
exact object
search
neighborhood depth 1
neighborhood depth 2
evidence
anchor resolution
```

Compare, where meaningful:

```text
legacy hydrated path
new direct DND path
```

Record only safe aggregate information in the checked-in summary:

- DND revision identity if already public operational metadata;
- parsed/admitted object/relationship/evidence counts;
- operation names;
- median/distribution summary;
- cold/warm characterization labels;
- DND R.2a phase/count observations;
- environment metadata sufficient to interpret the run;
- warnings/limitations.

Do **not** check private campaign query text, labels, aliases, source paths, source
content, object IDs, or evidence IDs into a benchmark artifact.

### Performance decision rule

R.3 does not introduce a hard absolute SLO.

However, if the actual mounted direct path is clearly product-breaking — for
example multi-second latency on a normal interaction that the current product
serves materially faster — stop/review before deleting the old read path.

The decision may then be:

```text
semantic parity proven
→ preserve R.3 witness
→ dispatch R.3a optimization before production switch
```

That is not a failure of R.3. It is exactly why R.2a/R.3 measure before
optimization.

Do not optimize inside the R.3 Buddy PR.

---

## 8. Required implementation

### 8.1 Repin DungeonMind

Modify:

```text
pyproject.toml
uv.lock
```

to exact PR #43 merge `519b2c96fc42d22f3113cc9ca0d48bc70b6780e5`.

### 8.2 Add direct DungeonMind read adapter

Create preferred paths:

```text
apps/live_control_server/integrations/dungeonmind/__init__.py
apps/live_control_server/integrations/dungeonmind/world_graph_reads.py
```

Keep this adapter transport-neutral relative to the routes; services call it.

It should expose a small Buddy-facing application integration, not mirror the
entire DungeonMind API.

Suggested responsibilities/classes may include:

```text
DirectWorldGraphReadServices
DirectWorldGraphReadError
build_direct_world_graph_read_services(...)
map_projection_request(...)
legacy_adopted_revision_bridge(...)
```

Names are flexible. Boundaries are not.

### 8.3 Switch projection service by authority mode

`apps/live_control_server/services/world_graph_projection.py` should have an
explicit authority dispatch:

```text
if dungeonmind:
    direct DND projection adapter
else:
    existing legacy/test path
```

Do not route the DND branch through `route_service_read()` if that function's
contract is hydration-root selection. The direct path should not produce a
`graph_root` at all.

### 8.4 Switch retrieval service by authority mode

Do the same for:

```text
search_campaign_graph
get_campaign_object
get_object_neighborhood
get_object_evidence
read_source_anchor
```

In DungeonMind authority mode each must call the DND-native operation.

### 8.5 Remove read dependence on frozen Buddy state

A normal DND head/pinned read must boot and serve with the old Buddy graph root
absent/unreadable.

If retaining legacy A→D_A compatibility, resolve A from the DND adoption
receipt. Do not require a frozen `head.json`.

This closes a major retirement gate:

> Frozen Buddy graph is not needed to boot or serve DungeonMind reads.

### 8.6 Disable old Buddy read prewarming in DND mode

Ensure projection recipe/prewarm/cache machinery cannot call the legacy graph
engine as a side effect of a successful direct read.

No replacement cache is authorized in R.3.

### 8.7 Preserve write path

Normal governed Graph Review confirmation already publishes through
DungeonMind. Do not regress it.

If current write verification still relies on Buddy hydration/rebuild, retain
that code in this PR and name it explicitly as remaining retirement debt.

R.3 is complete when reads are direct even if write-side compatibility still
uses legacy machinery.

---

## 9. Retain / rewrite / delete

### Retain in this PR

- existing Buddy product HTTP/wire contracts when semantically supportable;
- governed DND write path;
- old hydration implementation if still required by write verification or
  explicit legacy/test tools;
- explicit non-production test roots;
- R.2a baseline unchanged;
- source-body/product presentation owned outside graph authority.

### Rewrite

- production DungeonMind projection dispatch;
- production DungeonMind retrieval dispatch;
- source-anchor revalidation path;
- legacy-A bridge so reads do not require frozen Buddy files;
- old projection prewarm/recipe behavior in DND mode;
- tests that currently assert hydration/kernel as the DND production read
  implementation rather than as historical compatibility behavior.

### Do not delete yet unless proven unconsumed

```text
apps/live_control_server/integrations/dungeonmind_kernel/world_graph_authority.py
src/graph_memory/kernel/**
src/graph_memory/world_supergraph/**
src/graph_memory/union_supergraph/**
```

R.3 removes their **production read consumers**. Later demolition deletes the
implementation after write/legacy consumers are evacuated.

---

## 10. File allowlist / write lease

Expected implementation diff:

| Action | Path | Purpose |
|---|---|---|
| Modify | `pyproject.toml` | Pin DND R.2a merge |
| Modify | `uv.lock` | Lock exact DND revision |
| Create | `apps/live_control_server/integrations/dungeonmind/__init__.py` | New permanent DND product integration namespace |
| Create | `apps/live_control_server/integrations/dungeonmind/world_graph_reads.py` | Direct R.1/R.2 construction, request mapping, compatibility adaptation helpers |
| Modify | `apps/live_control_server/services/world_graph_projection.py` | DND-mode direct projection; legacy mode stays isolated |
| Modify | `apps/live_control_server/services/world_graph_retrieval.py` | DND-mode direct retrieval and DND-native anchor revalidation |
| Modify | `apps/live_control_server/services/world_graph_projection_recipes.py` | Prevent legacy prewarm/replay in DND mode |
| Modify | `apps/live_control_server/services/world_graph_prewarm.py` | Prevent legacy read prewarm in DND mode if active/mounted |
| Modify | `apps/live_control_server/integrations/dungeonmind_kernel/world_graph_authority.py` | Only if needed to isolate read-era hydration / receipt bridge from write compatibility; no broad rewrite |
| Create | `tests/test_cutover_direct_dungeonmind_world_graph_reads.py` | Owning direct-read/no-hydration/parity tests |
| Modify | `tests/test_cutover_dungeonmind_world_graph_authority.py` | Reclassify hydration as legacy/write compatibility and preserve write proof |
| Modify | `tests/test_world_graph_retrieval_routes.py` | Mounted direct retrieval/error/anchor proof |
| Modify | existing World Graph projection service/route tests | Mounted direct projection proof; exact file selected during bounded discovery |
| Modify | `tests/test_live_query_hermes_graph.py` | Hermes mounted read proves no legacy kernel/hydration |
| Modify | `tests/test_live_control_server.py` | Live-agent mounted read proof if still owning path |
| Create | `scripts/compare_direct_dungeonmind_world_graph_reads.py` **or** one bounded eval equivalent | Local real-current parity/perf witness runner; no private output committed |
| Create | `Docs/Benchmarks/BASELINE-r3-direct-dungeonmind-current-reads.md` | Safe aggregate current-graph cutover witness if benchmark evidence is checked in |
| Modify | `Docs/Plans/STEWARDS-ANCHOR-cutover.md` | Record direct-read retirement truth after implementation |
| Modify | `Docs/Plans/PR-TRACKER-campaign-supergraph.md` | R.3 state + successor |
| Modify | `Docs/Roadmaps/ROADMAP-campaign-supergraph.md` | R.3 state + R.3a named successor |

### Bounded discovery exception

Additional production files are allowed only when static call-path inspection
proves they are mounted graph readers or side-effect prewarmers that would
otherwise keep hydration/kernel execution alive.

```text
Directories:
  apps/live_control_server/services/
  apps/live_control_server/routes/
  apps/live_control_server/integrations/

Maximum additional production paths:
  6

Rule:
  every added path must be named in the PR body with the exact legacy read
  call it closes and an owning regression test.
```

Do not expand this into write-side, preview-union, ingestion, or namespace-wide
cleanup.

---

## 11. Tests and proofs

### 11.1 Legacy-read explosion proof

In DungeonMind authority mode, tests should arrange for the old read machinery
to raise immediately if touched, then prove mounted reads still succeed.

Where import structure permits, explode or spy on at least:

```text
world_graph_authority.ensure_hydrated_authority
world_graph_authority._ensure_hydrated_revision
world_graph_authority.hydrate_world_graph

kernel.resolve_projection_read_context
kernel.project_world_graph_from_context
kernel.search_campaign_graph
kernel.get_campaign_object
kernel.get_object_neighborhood
kernel.get_object_evidence
kernel.resolve_admitted_anchor_match
kernel.read_source_anchor
```

Also prove no production read invokes contribution rebuild or constructs a
`UnionSupergraphStore`.

Do not assert only that a helper was not called; exercise mounted service/route
paths.

### 11.2 Frozen-root independence

With DungeonMind repositories populated and authority mode selected:

```text
Buddy frozen graph root missing/unreadable
Buddy derivative cache empty
→ head read succeeds
→ exact DND pin succeeds
→ source-anchor revalidation succeeds
```

If legacy A compatibility is retained:

```text
frozen Buddy graph absent
→ revision_pin=A
→ exact D_A through adoption receipt
```

### 11.3 Authority failure

DND unavailable/corrupt/missing pin must return the mapped error and prove:

```text
no Buddy file fallback
no cache fallback
no preview fallback
```

### 11.4 Scope/admissibility

Prove:

```text
Buddy campaign → DND CAMPAIGN
Buddy world → DND WORLD_CROSS_CAMPAIGN
PLAYER hides GM-only rows
cross-campaign PLAYER still does not leak GM-only rows
```

### 11.5 Historical pins

Returned DND revision ids must self-repin directly without a private translation
map.

### 11.6 Source anchor

Prove:

```text
anchor emitted from direct DND operation
→ same context resolves
→ changed revision/scope/admissibility fails/rejects as DND contract requires
→ only admitted metadata reaches source opener
```

### 11.7 Write regression

The existing normal governed GM-confirmed publication path remains green and
continues to create DungeonMind child revisions with no local Buddy fallback.

R.3 must not accidentally break writes while separating reads.

### 11.8 Full repository gates

Run repository-standard gates from current `AGENTS.md` / CI, including at
minimum:

```bash
uv run ruff check .
uv run pytest tests/ --maxfail=1
```

and every focused cutover/projection/retrieval/Hermes test added or touched.

---

## 12. Static boundary gates

The goal is not yet zero `graph_memory.kernel` imports repository-wide; write,
maintenance, scripts, and legacy tests still exist.

The R.3 gate is narrower and enforceable:

> no mounted DungeonMind-authority production **read** path imports/calls the
> Buddy graph read kernel or hydration runtime.

Add a targeted static/runtime proof around the direct service integration.

At review, explicitly inventory remaining production imports of:

```text
graph_memory.kernel
graph_memory.world_supergraph
graph_memory.union_supergraph
```

and classify each surviving production consumer as:

```text
write path
legacy authority/test mode
maintenance/tooling
preview-era debt
other blocker
```

That inventory becomes the demolition map after R.3a/write migration.

---

## 13. Non-goals

R.3 does **not** authorize:

- DungeonMind projection caching/memoization;
- parsed-revision cache implementation;
- scoped-projection cache implementation;
- search indexing;
- anchor/supporter indexing;
- changing R.1/R.2 read semantics;
- changing graph schema;
- changing provenance/admissibility rules;
- deleting Buddy's governed write compatibility path;
- deleting the entire `src/graph_memory` package;
- deleting all legacy `buddy_files`/quiesced test support;
- preview-union/latest-ingest demolition;
- generalized namespace cleanup;
- Play/Agent UI redesign;
- vector/semantic/LLM retrieval;
- new graph fallback behavior;
- broad source-body architecture redesign;
- hard performance SLOs.

If implementation pressure points toward one of these, stop/split.

---

## 14. Stop conditions

Stop and return to design/review if any of the following occurs:

1. Buddy branch is not based on current `main` after #630
   (`3b25dbd89664b5a148ad76e0f5780b5ddc742f9a`) or relevant main read seams
   changed materially after this rebase.
2. DungeonMind pin `519b2c96fc42d22f3113cc9ca0d48bc70b6780e5` no
   longer exposes the reviewed R.1/R.2/R.2a contracts plus V4 receipt types.
3. A mounted product projection requires graph-semantic information absent
   from DND direct projection/retrieval and cannot be represented from admitted
   DND facts plus clearly non-authoritative product data.
4. The cross-campaign + campaign-qualified session-focus case cannot preserve
   mounted behavior without changing DungeonMind projection semantics.
5. Preserving a Buddy wire contract requires constructing/replaying a
   `UnionSupergraphStore` or invoking Buddy graph kernel.
6. Source-anchor opening requires old Buddy graph revalidation or a
   caller-controlled path/locator.
7. Semantic parity finds visibility/admissibility/provenance/identity drift.
8. Exact DND revision ids cannot round-trip directly as pins.
9. Legacy A→D_A compatibility cannot be resolved from DND durable adoption
   metadata without the frozen Buddy graph and the compatibility is still a
   required mounted contract.
10. Actual-current direct performance is clearly product-breaking relative to
    the existing mounted path. Preserve the witness and decide whether R.3a
    must precede the production switch.
11. A fix requires a DungeonMind contract/schema change in the same Buddy PR.
    Split a bounded DND prerequisite.
12. The implementation begins adding caching/indexing/optimization to make the
    benchmark look better.
13. Any DND-mode read still silently falls back to hydration/Buddy files.
14. Tests prove only isolated helpers and not mounted product paths.

---

## 15. Acceptance criteria

R.3 is merge-ready only when all are true:

1. Buddy is pinned to DND PR #43 merge `519b2c96...`.
2. DungeonMind authority projection calls R.1 directly.
3. DungeonMind authority retrieval calls R.2 directly for all five operations.
4. DND-mode production reads construct no `UnionSupergraphStore`.
5. DND-mode production reads perform no Buddy contribution replay/rebuild.
6. DND-mode production reads call no Buddy graph kernel read operation.
7. DND-mode production reads require no hydrated cache root.
8. Normal DND head and exact DND pins require no frozen Buddy graph files.
9. Returned DND revision ids are exactly re-pinnable.
10. Legacy A→D_A bridge, if retained, is receipt-backed and hydration-free.
11. Campaign/world scope mapping is exact; `world` means
    `WORLD_CROSS_CAMPAIGN`.
12. GM/PLAYER admissibility remains fail-closed.
13. Mounted Plan/Build/Play graph-reference/Hermes paths represented in the
    affected read surface succeed without legacy read machinery.
14. Source-anchor revalidation is DND-native before product source opening.
15. DND failure produces no Buddy/preview fallback.
16. Old Buddy projection recipe/prewarm cannot trigger hidden legacy reads in
    DND mode.
17. The normal governed write path remains green.
18. A normalized legacy-vs-direct semantic parity witness exists.
19. A safe actual-current aggregate performance witness exists or the PR stops
    explicitly on the performance gate.
20. R.2a synthetic artifacts remain unchanged.
21. Static inventory records every surviving production graph-kernel/storage
    consumer and its retirement category.
22. Steward/roadmap/tracker state moves atomically with implementation truth.
23. R.3a is named as the immediate post-cutover read optimization successor.

---

## 16. Definition of done

The PR is done when this statement is true and proven:

> **DungeonMind authority mode can serve the product's World Graph projection,
> search, object, neighborhood, evidence, and source-anchor workflows directly
> from DungeonMind durable authority, with exact revision/scope/admissibility
> semantics and no Buddy graph hydration or read-kernel execution.**

At that point the old Buddy graph engine is no longer a production read engine.
It is remaining compatibility/write/legacy debt with a finite consumer list.

---

## 17. Named successor and optimization freeze

After R.3 lands, freeze the R.3 semantic witness and the R.1/R.2 public read
semantics. The immediate read-performance successor belongs in DungeonMind:

```text
R.3a — reusable World Graph read context / parsed immutable revision reuse
```

R.3a may change execution strategy but must preserve the R.3 semantic outputs.

First candidate:

```text
content-addressed revision
→ parse once
→ reuse immutable ParsedGraphSnapshot
```

Scoped projection reuse is a separate design concern because projection
admission consults live source/provenance authority state. It is **not** safe to
cache merely by `(revision, scope, admissibility, profile)`; it requires an
explicit source/provenance state version/digest, bounded coherent context, or
equivalent invalidation model.

Search indexing and anchor/supporter indexing should remain distinct successor
optimizations driven by measured warm-path cost.

Do not continue deeper graph-runtime demolition until this optimization pass
has established the read architecture we actually want to keep.

---

## 18. What remains after R.3 — full Buddy graph retirement

R.3 is a major boundary, not the final deletion PR.

After R.3 the expected state is:

```text
DungeonMind
  durable graph authority             DONE
  governed authoritative publication  DONE
  native projection/retrieval          DONE
  product production reads             DONE after R.3

Buddy graph engine
  production read authority            DEAD after R.3
  derivative read hydration            DEAD after R.3
  write/review compatibility            MAY REMAIN
  legacy modes/tests/tools              REMAIN
  preview-era paths                     REMAIN
  graph_memory namespace                REMAIN
```

Likely later retirement domains, subject to fresh design after R.3a:

1. **DND-native candidate/review/write boundary** — remove any remaining need
   to hydrate/rebuild Buddy graph state merely to verify or confirm governed
   writes.
2. **Legacy authority and preview demolition** — retire `buddy_files` as a
   production-selectable authority, latest-preview/latest-ingest product graph
   selectors, and obsolete root/manifest routing.
3. **Production consumer evacuation** — move Hermes/product integrations and
   surviving legitimate product contracts out of the old graph-engine
   namespace.
4. **Static-zero + deletion** — prove no production imports of
   `graph_memory.kernel`, `graph_memory.world_supergraph`, or
   `graph_memory.union_supergraph`, then delete the graph engine and obsolete
   tests/tooling.

Do not pre-commit exact PR numbering for those later slices until R.3/R.3a
reveal the true remaining consumer graph.
