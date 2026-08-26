---
pr_body_template: |
  ## Handoff pointer
  - Workstream: CUTOVER / D.3 — Buddy graph-engine demolition DESIGN
  - Flow: CUTOVER
  - Direction: DESIGN → REVIEW
  - Handoff: `Docs/Plans/HANDOFF-CUTOVER-buddy-graph-engine-demolition.md`
  - Implementation repository: `Drakosfire/DungeonMindBuddy`
  - Exact design base: `9c946cd8c24effccec8d06cfc1cb5e310c9edc5e`
  - Predecessor: Buddy #645 merge `3ff46922e679ad6bef2ef0cf37f0bf87e4542a6c`
  - #645 accepted head: `f772db17e00cbe2c0198ae53f169a10a6332a3ed`
  - #645 final review: Review Cycle 2 PASS-equivalent `5026532158`
  - Parallel re-anchor: APP-STATE #646 merged into main as `9c946cd8c24effccec8d06cfc1cb5e310c9edc5e`
  - DungeonMind provider pin: `bf40e933bdedf3cf08bb23a07a135958bdb7cc6b`

  This design decomposes final CUTOVER demolition into D.3A mounted production
  graph-engine excision followed by D.3B physical legacy-package deletion.
  D.3 is not DONE until D.3B merges and the final absence proof passes.
---

# HANDOFF — CUTOVER D.3: Buddy graph-engine demolition

**Created:** 2026-08-25  
**Status:** DESIGN — steward review required before implementation dispatch  
**Canonical handoff:** `Docs/Plans/HANDOFF-CUTOVER-buddy-graph-engine-demolition.md`  
**Workstream / flow:** `CUTOVER`  
**Direction:** DESIGN → REVIEW  
**Implementation repository:** `Drakosfire/DungeonMindBuddy`  
**Exact design base / current `main`:** `9c946cd8c24effccec8d06cfc1cb5e310c9edc5e` — merge of APP-STATE #646 on top of #645  
**D.2C2 implementation:** Buddy #645 merge `3ff46922e679ad6bef2ef0cf37f0bf87e4542a6c`  
**D.2C2 accepted head:** `f772db17e00cbe2c0198ae53f169a10a6332a3ed`  
**D.2C2 review:** 2 distinct-head cycles; final PASS-equivalent `5026532158`  
**D.2C2 design:** Buddy #644 merge `f1eae2a3d27e430ee19e254d5b52fa556b2632ff`; accepted head `ded066cec49c3840c3b19c3e817ffa569a116f39`; Cycle 2 PASS-equivalent `5025378684`  
**DungeonMind pin:** `bf40e933bdedf3cf08bb23a07a135958bdb7cc6b` — PR #46 reviewed zero-parent initialization authority  
**Design branch:** `cutover/design-buddy-graph-engine-demolition`  
**Design PR title:** `CUTOVER: design Buddy graph-engine demolition`  
**First implementation successor:** D.3A / `cutover/mounted-graph-engine-excision`  
**Suggested D.3A PR title:** `CUTOVER: excise Buddy graph engine from production`  
**Named D.3B successor:** `cutover/delete-legacy-graph-engine`  
**Suggested D.3B PR title:** `CUTOVER: delete legacy Buddy graph engine`  

> Repository law: [`AGENTS.md`](../../AGENTS.md). Sequencing authority:
> [`PR-TRACKER-campaign-supergraph.md`](PR-TRACKER-campaign-supergraph.md).
> Architecture authority:
> [`../Design/ARCHITECTURE-campaign-supergraph.md`](../Design/ARCHITECTURE-campaign-supergraph.md).

---

## 1. Mission

D.2 is complete. All mounted World Graph authority is now DungeonMind-owned:

```text
reads                         → DungeonMind native
exact-run Graph Review writes → DungeonMind native
Threat publication            → WorldGraphAuthority → DungeonMind
existing-world worldbuilding  → WorldGraphAuthority → DungeonMind
first-world/bootstrap         → WorldGraphInitializationAuthority → DungeonMind
Buddy product/runtime state   → Buddy-owned stores
```

D.3 must therefore be demolition, not another authority migration.

The tracker currently names one final capability:

```text
D.3 final Buddy graph-engine deletion
  delete graph_memory.kernel / world_supergraph / union_supergraph
  production imports
  prove the old graph is physically absent
```

At this base, however, the legacy namespaces still contain a mixture of:

- retired graph storage/publication/replay authority;
- production compatibility routing;
- pure Buddy-owned contribution and mechanics value contracts;
- projection DTOs;
- historical Eldyrwild migration/conformance tooling;
- tests and fixtures.

A bounded code inventory at #645's merge found, within `apps/live_control_server`,
37 references to `graph_memory.kernel`, 20 to `graph_memory.world_supergraph`, and
26 to `graph_memory.union_supergraph`. The sets overlap. Count alone is not an
authority classification.

One PR that relocates surviving product values, removes production routing,
deletes historical tools, and removes three package trees would violate the
one-capability rule and make semantic regressions hard to distinguish from
bulk deletion fallout.

### Frozen decomposition

```text
D.3A  mounted production graph-engine excision
      ↓
      mounted server works with legacy engine imports blocked
      and old Buddy graph filesystem absent
      ↓
D.3B  physical legacy graph-engine package deletion
      ↓
      retired source/compatibility implementation disappears
```

**D.3 is not DONE after D.3A.** D.3 becomes DONE only after D.3B merges and the
final source/runtime absence proof passes.

Both slices are retirement work under already-living DungeonMind authority.
Neither slice is a new semantic migration program.

---

## 2. Re-anchored predecessor truth

### 2.1 D.2C2 is complete

Buddy #645 is merged:

```text
PR              #645
accepted head   f772db17e00cbe2c0198ae53f169a10a6332a3ed
review cycles   2
final review    5026532158 — PASS-equivalent
merge           3ff46922e679ad6bef2ef0cf37f0bf87e4542a6c
```

It proved the last authority migration required before demolition:

- first-world eligibility/prepare use `WorldGraphInitializationAuthority.probe()`;
- first-world confirm creates/replays one DungeonMind `D_0` with null parent;
- native receipt truth is `baselineRevisionId=null`;
- mounted first-world review/prepare/confirm do not require Buddy graph files;
- exact retry, lost-response restart, and synchronized concurrent confirms
  converge on one receipt and one `D_0`;
- verified reviewed-init integrity errors stay inside the storage-neutral port.

### 2.2 APP-STATE AS3 merged during design authoring

APP-STATE #646 merged after #645 and before this design was finalized:

```text
PR              #646
accepted branch head observed 913cfe0bbce4db27250afd8277e3af50712ee029
merge           9c946cd8c24effccec8d06cfc1cb5e310c9edc5e
```

Its Play/Application-State changes are now part of the D.3 design base rather
than a parallel lease. This design intentionally does not touch them.

At final re-anchor there are no other open implementation PRs besides this
D.3 design PR. D.3A must still repeat the active-PR/write-lease check immediately
before implementation; current absence is not permission to ignore future lanes.

### 2.3 Current state docs are one CUTOVER merge behind

The Campaign Supergraph tracker/roadmap still say #645 is `DOING` and D.3 is
`BLOCKED`, because those documents were correctly written before #645's merge
SHA was knowable.

Do not open a routine docs-only sync PR.

The D.3A implementation PR owns the backward-looking predecessor sync:

```text
#645 D.2C2                 DONE
  merge                    3ff46922e679ad6bef2ef0cf37f0bf87e4542a6c
  accepted head            f772db17e00cbe2c0198ae53f169a10a6332a3ed
  review cycles            2
  final PASS-equivalent    5026532158

this D.3 design             DONE only with its real merge/review facts
D.3A                        active / DOING in its implementation PR
D.3B                        BLOCKED on D.3A
D.3                         not DONE
```

---

## 3. Definitions

### 3.1 Legacy Buddy graph engine

For D.3, the legacy engine is the runtime/storage/replay implementation under:

```text
graph_memory.kernel
graph_memory.world_supergraph
graph_memory.union_supergraph
```

It includes the old file-backed head/revision store, local mutation/publication,
contribution replay/rebuild when used as graph authority, old initialization,
old projection/retrieval runtime, hydration support, and `UnionSupergraphStore`
as a runtime/store shape.

### 3.2 Mounted production

Mounted production means code reachable through normal DungeonBuddy operation:

```text
FastAPI app boot
Plan / Play / Build / Recap
Graph Review exact-run review/prepare/confirm
Threat query + publication
worldbuilding publication
first-world initialization
World Graph projection/retrieval/evidence/anchor
Hermes / agent graph reads
```

Historical migration/conformance scripts and explicit legacy fixtures are not
mounted product merely because they live under `apps/` or `tests/`.

### 3.3 Surviving Buddy-owned graph-shaped values

D.3 deletes the old engine, not every graph-shaped product value.

The following may survive when Buddy still owns their product semantics:

- Graph Review/publication contribution values;
- operator decisions and digests;
- source/evidence/candidate contracts;
- projection/retrieval request and response DTOs;
- product-side mechanics/statblock binding values;
- storage-neutral authority ports and receipts;
- DungeonMind-backed adapters implementing those ports.

A surviving value contract must have a non-engine owner after D.3A. It may not
remain implemented by importing one of the three retired namespaces.

### 3.4 Historical executable consumers

Historical docs and sealed reports may mention old namespace names forever.
Executable historical consumers must be classified before D.3B:

```text
DELETE   no remaining operational use
REHOME   still useful, but move under explicit non-engine tooling ownership
REWRITE  still useful proof can consume source/DungeonMind durable facts
STOP     real operational dependency discovered; re-brief before deletion
```

No test/forensic tool gets to keep the old engine alive as hidden production
compatibility.

---

## 4. Frozen architecture decisions

### 4.1 Production authority selection is retired

`DUNGEONMIND_WORLD_GRAPH_AUTHORITY` was a migration control plane. Its old
values currently include `buddy_files`, `quiesced`, and `dungeonmind`.

After D.3A:

```text
unset       → DungeonMind mounted authority
dungeonmind → DungeonMind mounted authority
buddy_files → fail closed as retired production configuration
quiesced    → fail closed as retired production configuration
unknown     → fail closed
```

Do not silently treat `buddy_files` or `quiesced` as DungeonMind aliases. A
stale operator setting should produce a clear configuration failure, not
resurrect the old graph.

D.3B may delete the obsolete selector parser/constant entirely once no retained
tooling needs its diagnostic compatibility.

### 4.2 Mounted authority factories become one-way DungeonMind

Today:

```text
get_world_graph_authority(...)
get_world_graph_initialization_authority(...)
```

can still construct `BuddyFiles...Adapter` implementations for old modes or
alternate roots.

After D.3A, mounted product accessors have one implementation: DungeonMind.
Preferred shape:

```python
def get_world_graph_authority() -> WorldGraphAuthority:
    return DungeonMindWorldGraphAuthorityAdapter()


def get_world_graph_initialization_authority() -> WorldGraphInitializationAuthority:
    return DungeonMindWorldGraphInitializationAdapter()
```

Lazy imports are fine if needed for startup/cycle control. What is not allowed
is a product-reachable fallback branch.

Tests/tools that intentionally need legacy fixtures must construct an explicit
fixture helper directly. Do not recreate the selector as `test_mode`, a hidden
env var, API parameter, query parameter, or header.

### 4.3 Relocate pure product values, not graph authority

#### Contribution values

`apps/live_control_server/models/world_graph_contribution_values.py` is already
an explicit shim declaring that contribution values are Buddy-owned and not a
World Graph store. D.3A makes that boundary real.

Relocate only pure models/helpers still needed by mounted Buddy flows, including
as needed:

```text
GraphContribution
GraphContributionAssertion
ContributionIdentityMention
ContributionMergeResult
build_assertion
stable assertion/contribution digest helpers
provenance normalization helpers
```

Preserve exactly:

- field names/aliases and validation;
- canonical serialization;
- assertion IDs;
- contribution IDs;
- source/contribution SHA-256 values;
- accepted/rejected semantics;
- deterministic ordering.

Do not relocate local publish, replay, head mutation, identity merge, or revision
store behavior with these values.

Mounted `extract_promote` code imports the new Buddy-owned boundary, never
`graph_memory.kernel`.

#### Mechanics/statblock values

Pure mechanics values currently housed under
`graph_memory.union_supergraph.statblock_binding` are not graph authority.
Relocate still-used contracts to a product/mechanics-owned module, preserving
current semantics, including as needed:

```text
ExternalResourceV1
ThreatStatblockBindingV1
WorldObjectStatblockBindingV1
```

Mechanics remain product-side. D.3 does not migrate them into DungeonMind
semantic World Graph authority.

#### Projection DTOs

`graph_memory.projection` is not automatically deleted because of its package
name. It may remain temporarily as a storage-neutral DTO/validation package.

After D.3A, however, no mounted projection DTO module may import `kernel`,
`world_supergraph`, or `union_supergraph`.

Do not churn public wire schemas merely to rename a package during demolition.

### 4.4 Classify before moving code

For each old-engine dependency:

```text
PURE VALUE / PURE TRANSFORM still needed → relocate to bounded Buddy owner
DUNGEONMIND mapping needed              → keep/relocate inside DM integration
LEGACY AUTHORITY / STORE / REPLAY        → delete caller or use existing port
HISTORICAL TOOLING                       → classify for D.3B
UNKNOWN                                  → STOP and re-brief
```

Moving the old Kernel wholesale to a new module name does not satisfy D.3.

### 4.5 “Physically absent” is a runtime proof, not data destruction

The product must work when:

```text
<configured-root>/graph_memory/worlds/
```

does not exist.

D.3A must prove it is absent before a mounted test and still absent afterward.

D.3 does **not** authorize runtime deletion of a user's old graph data. Do not
add `rm -rf`, `shutil.rmtree`, startup cleanup, or equivalent destructive code.
Historical local graph bytes may be archived/removed later only by an explicit
operator action.

### 4.6 `world_graph_root` may survive only as a non-authority designation

If a configured graph-root path still has a real safety/fixture role, D.3A need
not rename it for aesthetics.

After D.3A:

- mounted production never opens a head/revision under it;
- the directory need not exist;
- passing a different path may not select another mounted authority;
- no client/API input may create a legacy-root escape hatch.

If inventory shows the path has no remaining purpose, remove the obsolete config
in D.3A. Otherwise retain only the narrow safety/fixture designation.

### 4.7 Hydration/cache compatibility has no production owner

The DungeonMind→Buddy hydrated read model and cache existed for migration. D.2
is complete.

D.3A deletes mounted hydration routing/configuration once inventory confirms no
remaining product consumer. Tests must move to native DungeonMind or explicit
legacy fixtures; tests do not justify product fallback.

### 4.8 DungeonMind contracts are frozen during demolition

D.3 adds no new provider capability.

If D.3A discovers a mounted behavior that cannot execute using already-landed
DungeonMind read, governed publication, and reviewed initialization contracts,
STOP. That means D.2 is incomplete; do not smuggle a provider feature into a
deletion slice.

### 4.9 No semantic rewrite

Preserve accepted behavior for:

```text
GM/PLAYER admissibility
search / exact object / neighborhood / evidence / source-anchor
revision pins and head semantics
exact-run Graph Review seals
Threat mechanics separation
existing-world worldbuilding publish/recovery
first-world initialization/retry/restart/concurrency
source/evidence closure
current API/wire schemas
stable contribution/source IDs and digests
```

---

## 5. D.3A — mounted production graph-engine excision

### 5.1 Merge-ready invariant

D.3A is merge-ready only when:

> **The mounted DungeonBuddy server can boot and execute its World Graph read,
> review, publication, and first-world workflows with imports from
> `graph_memory.kernel`, `graph_memory.world_supergraph`, and
> `graph_memory.union_supergraph` blocked before app import, while the legacy
> Buddy graph filesystem is absent. All authoritative graph I/O remains
> DungeonMind-owned. Any retained legacy consumer is explicit test/tooling/
> historical code and unreachable from mounted product accessors.**

D.3A gives D.3B a production dependency count of zero. That is independently
useful and reviewable.

### 5.2 Required implementation sequence

#### Step 0 — re-anchor and freeze inventory

Re-read current `main`, active PRs, this handoff, and the accepted design PR.

At minimum inventory:

```bash
rg -n \
  '(^|[[:space:]])(from|import)[[:space:]]+graph_memory\.(kernel|world_supergraph|union_supergraph)' \
  apps/live_control_server src scripts tests

rg -n \
  'DUNGEONMIND_WORLD_GRAPH_AUTHORITY|buddy_files|quiesced|route_service_read|ensure_hydrated_authority|WORLD_GRAPH_AUTHORITY_CACHE' \
  apps/live_control_server src scripts tests
```

Classify every executable hit:

```text
MOUNTED_PRODUCT
DUNGEONMIND_ADAPTER
PURE_PRODUCT_VALUE
LEGACY_FIXTURE
HISTORICAL_TOOL
DEAD
```

Handback must explain every retained executable occurrence.

If a `MOUNTED_PRODUCT` hit represents a new semantic dependency not covered by
this design, STOP.

#### Step 1 — establish surviving value owners

Relocate contribution/mechanics values before removing old imports.

While old implementations still exist, parity-test stable fixtures:

```text
model_dump(mode="json") identical
canonical bytes identical
assertion/contribution IDs identical
source/contribution SHA-256 identical
validation accept/reject behavior identical
```

After callers switch, new product modules are the sole owner. Do not leave a
permanent dual implementation.

#### Step 2 — retire mounted authority selection

Make authority accessors DungeonMind-only.

Remove product branches that instantiate:

```text
BuddyFilesWorldGraphAuthorityAdapter
BuddyFilesWorldGraphInitializationAdapter
```

Retired environment values fail closed. Explicit legacy tests construct fixtures
directly.

#### Step 3 — remove mounted engine imports

Switch every `MOUNTED_PRODUCT` / `PURE_PRODUCT_VALUE` dependency to:

- an existing storage-neutral World Graph port;
- the existing DungeonMind integration; or
- the new Buddy-owned pure value boundary.

Do not rewrite historical tooling unless app boot or a mounted route imports it.

#### Step 4 — retire hydration/file fallback

Delete mounted hydration/cache/router fallback once inventory proves it has no
product consumer.

DungeonMind failure continues to fail closed; it never falls through to local
or hydrated graph state.

#### Step 5 — add a true import-blocker witness

Add a subprocess/test proof that blocks modules whose FQNs start with:

```text
graph_memory.kernel
graph_memory.world_supergraph
graph_memory.union_supergraph
```

Install the blocker **before importing the mounted app**. Already-cached forbidden
modules invalidate the witness.

Under the blocker, boot/import and execute representative mounted DungeonMind
boundaries.

#### Step 6 — prove legacy filesystem absence

Use a configured root where:

```text
<root>/graph_memory/worlds
```

does not exist before the test. Assert it still does not exist afterward.

A sentinel/permission trap is optional. Absence-before/after plus import blocking
is the minimum.

#### Step 7 — regress completed D.1/D.2 paths

Run owning boundaries for:

```text
native projection/retrieval/evidence/anchor
exact-run Graph Review D.1
Threat D.2A
worldbuilding D.2B
first-world D.2C2
Hermes/latest-recap graph reads
```

Use real PostgreSQL for publication/initialization cohorts where their accepted
handoffs require it. Required integration proofs must not silently skip.

#### Step 8 — carry backward state-authority sync

D.3A owns the #645 predecessor sync from §2.3.

At minimum update current mutable CUTOVER authorities that still claim #645 is
in flight:

```text
Docs/Plans/PR-TRACKER-campaign-supergraph.md
Docs/Roadmaps/ROADMAP-campaign-supergraph.md
Docs/Design/STATUS-world-graph-continuity-spine.md
Docs/Plans/STEWARDS-ANCHOR-cutover.md
Docs/Sources/design-agent/ACTIVE_AUTHORITY/PR-TRACKER-campaign-supergraph.md
Docs/Sources/design-agent/ACTIVE_AUTHORITY/ROADMAP-campaign-supergraph.md
this handoff / D.3A implementation handoff as appropriate
```

Record #645's real merge/head/review. Record this design PR's real completion
only when known. Mark D.3A active. Keep D.3B blocked and D.3 not DONE. Do not
invent D.3A future merge/review facts.

### 5.3 D.3A implementation write lease

#### Core owned paths

```text
apps/live_control_server/config.py
apps/live_control_server/ports/world_graph_authority_access.py
apps/live_control_server/ports/world_graph_initialization_access.py
apps/live_control_server/integrations/buddy_files/**
apps/live_control_server/integrations/dungeonmind/world_graph*.py
apps/live_control_server/models/world_graph_contribution_values.py
apps/live_control_server/models/extract_promote.py
apps/live_control_server/models/threat_query_hydration.py
apps/live_control_server/services/first_world_graph.py
apps/live_control_server/services/first_world_graph_publication.py
apps/live_control_server/services/world_graph_*.py
apps/live_control_server/services/graph_review_*.py
apps/live_control_server/services/worldbuilding_graph_publication.py
apps/live_control_server/services/threat_*.py
src/graph_memory/projection/**
new narrowly named Buddy-owned contribution/mechanics value modules required by §4.3
```

#### Bounded discovery lease

A file under `apps/live_control_server/**` or mounted product `src/**` may be
added only when all are true:

1. it has a base-revision executable import from a retired namespace;
2. D.3A only replaces that import/call with a frozen owner from this design;
3. no wire/public semantics change;
4. it is not leased by another active PR at implementation re-anchor;
5. handback names the file and original classification.

Otherwise STOP and re-brief.

#### Owning tests

```text
tests/test_cutover_*.py
tests/test_world_graph_*.py
tests/test_first_world_graph.py
tests/test_live_extract_promote_api.py
focused Graph Review / Threat / worldbuilding / Hermes tests owning changed seams
new D.3 import-blocker / filesystem-absence tests
```

Do not claim all `tests/**` as a lease.

#### Backward state sync

The exact current-state files in Step 8.

#### Explicitly outside D.3A unless re-briefed

```text
src/application_state/**
Play Runtime/continuity feature work
APP-STATE migrations/schemas
DungeonMind repository/provider code
new World Graph semantics
broad historical Eldyrwild correction/conformance deletion
source-artifact/evidence/extraction redesign
Combat/application-state work
```

D.3A must re-check active PRs at implementation time. Any new lease overlap is
a serialization/transfer decision, not permission to edit through it.

### 5.4 Required D.3A evidence

#### Static dependency gate

At accepted head:

```text
0 mounted-product imports from graph_memory.kernel
0 mounted-product imports from graph_memory.world_supergraph
0 mounted-product imports from graph_memory.union_supergraph
0 mounted factory branches selecting buddy_files/quiesced
0 hydration/local fallback on DungeonMind failure
```

Historical docs are excluded. Named legacy tooling/tests may remain for D.3B.

#### Import-blocked mounted proof

With all three namespaces blocked before app import, cover at least:

```text
FastAPI app boot
World Graph projection
search + exact object + neighborhood
evidence + source-anchor open
exact-run review package
existing-world Graph Review prepare/confirm
first-world review/prepare/confirm
Threat publish/recover
worldbuilding publish/recover
Hermes/latest-recap graph comparison or owning service boundary
```

Route-level + owning service tests may be combined, but the blocker remains active
across the real boundary.

#### Legacy filesystem absence

Before and after the mounted proof:

```text
<configured-root>/graph_memory/worlds  DOES NOT EXIST
```

No Buddy graph head/revision/cache directory is created.

#### Retired selector matrix

Prove:

```text
unset       → DungeonMind
dungeonmind → DungeonMind
buddy_files → configuration failure; no file adapter
quiesced    → configuration failure; no file adapter
garbage     → configuration failure
```

#### Value parity

For every relocated value family, record serialization/digest/ID/validation
parity against the pre-relocation implementation.

#### D.2 regression invariants

```text
Threat: one DungeonMind child + exact retry/recovery
existing-world worldbuilding: one DungeonMind child + exact retry/recovery
first-world: one D_0 parent=None + one reviewed-init receipt + exact retry +
             lost-response restart + synchronized concurrent confirm
```

#### Quality gates

At minimum:

```bash
uv run ruff check <changed Python paths>
git diff --check
```

Run focused owning suites and broad non-live-LLM tests when reasonable. Report
exact pass/fail/skip counts. Required D.3 PostgreSQL witnesses have zero required
skips.

---

## 6. D.3B — physical legacy graph-engine deletion

D.3B is blocked until D.3A is merged and its import-blocked production proof is
green on current `main`.

### 6.1 Merge-ready invariant

> **Retired Buddy graph-engine source packages and compatibility adapters no
> longer exist as executable implementation; every intentionally retained
> historical executable tool has a new explicit non-engine owner; mounted
> DungeonBuddy remains green on DungeonMind; and the legacy-filesystem absence
> proof still passes.**

### 6.2 Primary deletion targets

Subject to D.3A's inventory:

```text
src/graph_memory/kernel/**
src/graph_memory/world_supergraph/**
src/graph_memory/union_supergraph/**
apps/live_control_server/integrations/buddy_files/**
retired hydration/cache implementation
legacy-only tests whose sole purpose is deleted authority behavior
```

If a storage-neutral product value still lives in those directories after D.3A,
D.3A is incomplete. Do not rescue it during bulk deletion by creating a second
owner.

### 6.3 Historical tooling classification

Before deleting package trees, inventory executable imports in:

```text
scripts/**
apps/live_control_server/services/*eldyrwild*
tests/**
other migration/conformance tooling
```

Choose DELETE / REHOME / REWRITE / STOP for every remaining consumer.

Old correction/conformance execution code may be deleted when its authority is
fully preserved by merged history, sealed source artifacts, current DungeonMind
state, and non-executable evidence. Do not delete source/evidence artifacts merely
because a producer tool retires.

### 6.4 Final D.3 evidence

At D.3B accepted head:

```text
legacy source package directories absent
buddy_files integration absent
production import-blocker still green
legacy graph filesystem absence still green
current DungeonMind read/write cohorts green
no product selector can recreate Buddy graph ownership
no automatic user-data deletion introduced
```

Only then may current state say:

```text
D.3 final Buddy graph-engine deletion DONE
```

If D.3B is the last dependent CUTOVER implementation, it owns the final direct
guarded state-authority sync after merge if no later implementation exists to
carry that truth.

---

## 7. Final production architecture

```text
DungeonBuddy product
  |
  +-- WorldGraphAuthority --------------------------+
  |                                                  |
  +-- WorldGraphInitializationAuthority ------------+--> DungeonMind
  |                                                  |    PostgreSQL authority
  +-- native projection/retrieval/evidence ----------+

Buddy-owned product state
  +-- source/corpus/workspace authority
  +-- exact-run review decisions/seals
  +-- Threat operation/proposal/receipt state
  +-- Application State / Play state
  +-- product-side statblock mechanics

NO mounted Buddy graph store
NO Buddy graph head/revision authority
NO local graph publication/replay fallback
NO buddy_files/quiesced production mode
NO DungeonMind→Buddy hydration runtime
```

This is the CUTOVER completion condition: DungeonMind authority no longer relies
on future engineers remembering not to call the old engine. The engine is first
absent from the production dependency graph, then absent from source.

---

## 8. Explicitly out of scope

Do not use D.3 to:

- change DungeonMind semantics/public contracts;
- reopen ExistingWorldAdoption or catch-up without a real `STALE` event;
- create another Buddy graph database/schema;
- move mechanics/statblocks into semantic World Graph authority;
- redesign Graph Review UX/API;
- redesign Plan/Play/Build/Hermes behavior;
- merge APP-STATE feature work into CUTOVER;
- delete source artifacts/evidence/candidate/workspace state;
- rename every surviving `graph_memory` package for aesthetics;
- rewrite historical docs to erase old names;
- automatically delete user/local graph data;
- introduce generic JSON/CRUD replacement abstractions;
- move the old Kernel wholesale under a new namespace;
- broaden into optimization unless a concrete correctness blocker appears.

---

## 9. Stop / re-brief conditions

STOP if:

1. a mounted behavior still requires local Buddy head/revision/store semantics;
2. a required path is leased by another active lane and cannot be serialized;
3. value relocation changes durable IDs, canonical bytes, digests, acceptance
   semantics, or public API shape;
4. a supposed pure value materially depends on local graph state/replay;
5. a new DungeonMind provider contract is required;
6. an old authority mode is actually required by a production deployment rather
   than tests/tooling;
7. filesystem absence would require deleting user data;
8. an operational historical tool cannot be rehomed without the engine;
9. the app cannot boot under a true pre-import blocker;
10. implementation needs broad Play/Application-State changes;
11. a concrete post-cutover failure shows D.2 authority migration was incomplete.

---

## 10. Suggested D.3A nano-commit story

```text
1. establish Buddy-owned contribution/mechanics values + parity tests
2. switch mounted DTOs/services off legacy value imports
3. make authority factories DungeonMind-only and retire old modes
4. remove mounted hydration/file fallback and production engine imports
5. add import-blocked + legacy-filesystem-absent witnesses
6. run D.1/D.2 regressions and close the dependency inventory
7. carry #645 + accepted-design predecessor state sync
```

Do not mix D.3B bulk deletion into D.3A.

---

## 11. D.3A review handback contract

Return:

1. exact PR / branch / final head SHA;
2. exact implementation base and rebase status;
3. accepted D.3 design merge/head/review authorizing D.3A;
4. cumulative changed paths against lease;
5. active parallel PRs checked and serialization decisions;
6. complete legacy-import classification summary;
7. relocated value families and canonical owners;
8. serialization/ID/digest/validation parity evidence;
9. final selector behavior for unset/dungeonmind/buddy_files/quiesced/unknown;
10. static zero-mounted-import proof for all three legacy namespaces;
11. import-blocker witness installed before app import;
12. legacy graph filesystem absent-before/after proof;
13. no hydration/cache/local fallback on DungeonMind failure;
14. projection/retrieval/evidence/anchor results;
15. D.1 Graph Review results;
16. D.2A Threat PostgreSQL publish/recovery results;
17. D.2B worldbuilding PostgreSQL publish/recovery results;
18. D.2C2 first-world PostgreSQL init/retry/restart/concurrency results;
19. Hermes/latest-recap graph-read result;
20. exact commands with pass/fail/skip counts;
21. ruff + `git diff --check`;
22. state sync showing #645 DONE, design DONE, D.3A active, D.3B blocked,
    D.3 not DONE;
23. executable legacy consumers deferred to D.3B with
    DELETE/REHOME/REWRITE classification;
24. stop conditions or `none`.

The D.3A dispatch seed is not Review Cycle 1. Review begins with executable
implementation and owning evidence.

---

## 12. Design review focus

Review this design specifically for:

1. **Decomposition:** is D.3A production excision → D.3B physical deletion the
   right one-capability boundary?
2. **Authority retirement:** should `buddy_files` / `quiesced` fail closed rather
   than be silently ignored?
3. **Value ownership:** are contribution/projection/mechanics values preserved
   without copying graph authority into a new namespace?
4. **Absence proof:** does pre-import blocking + real DungeonMind flows + missing
   legacy graph directory prove production independence?
5. **Historical tooling:** is DELETE/REHOME/REWRITE/STOP sufficient to keep
   forensic compatibility from preserving the engine indefinitely?
6. **Parallelism:** is the bounded discovery lease compatible with future lanes
   after mandatory implementation-time re-anchor?
7. **Data safety:** is “physically absent” correctly defined as runtime
   independence rather than automatic deletion of user graph data?

Do not dispatch D.3A until this design has a formal PASS-equivalent review on a
distinct accepted head and is merged.
