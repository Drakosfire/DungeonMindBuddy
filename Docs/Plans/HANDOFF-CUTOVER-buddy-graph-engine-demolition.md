---
pr_body_template: |
  ## Handoff pointer
  - Workstream: CUTOVER / D.3 — Buddy graph-engine demolition DESIGN
  - Flow: CUTOVER
  - Direction: DESIGN → REVIEW
  - Handoff: `Docs/Plans/HANDOFF-CUTOVER-buddy-graph-engine-demolition.md`
  - Implementation repository: `Drakosfire/DungeonMindBuddy`
  - Exact design base: `764d9d1ddbebbf398cb1f701d23de83c4c67a454`
  - Predecessor: Buddy #645 merge `3ff46922e679ad6bef2ef0cf37f0bf87e4542a6c`
  - #645 accepted head: `f772db17e00cbe2c0198ae53f169a10a6332a3ed`
  - #645 final review: Review Cycle 2 PASS-equivalent `5026532158`
  - Cycle 1 review: REQUEST-CHANGES-equivalent `5026690745` on `e7b34502eb3a7a3fcc8b716ef4a25a5bb7fc9db2`
  - Cycle 1 addendum: `5420568935` (same head; not Cycle 2)
  - Cycle 2 review: REQUEST-CHANGES-equivalent `5031234283` on `1d99c5e7a23cf864b671c6d3f0d17c65618a9327`
  - Parallel re-anchor: APP-STATE Play-continuity docs on `main` as `764d9d1ddbebbf398cb1f701d23de83c4c67a454`
  - DungeonMind provider pin: `bf40e933bdedf3cf08bb23a07a135958bdb7cc6b`

  This design freezes one remaining D.2 continuity predecessor, then decomposes
  demolition into D.3A mounted production graph-engine excision followed by
  D.3B physical legacy-package deletion.

  Sequence:

      D.2C2  reviewed first-world initialization       DONE
         ↓
      D.2C3  native genesis read/write continuity      REQUIRED
         ↓
      D.3A   mounted graph-engine excision
         ↓
      D.3B   physical legacy-package deletion

  D.3 is not DONE until D.3B merges and the final absence proof passes.
  D.2C3 is not dispatched until this design PR merges.
  D.3A is not dispatched until D.2C3 merges.
---

# HANDOFF — CUTOVER D.3: Buddy graph-engine demolition

**Created:** 2026-08-25
**Status:** CYCLE 2 REPAIR — awaiting Review Cycle 3
**Canonical handoff:** `Docs/Plans/HANDOFF-CUTOVER-buddy-graph-engine-demolition.md`
**Workstream / flow:** `CUTOVER`
**Direction:** DESIGN → REVIEW
**Implementation repository:** `Drakosfire/DungeonMindBuddy`
**Exact design base / current `main`:** `764d9d1ddbebbf398cb1f701d23de83c4c67a454` — APP-STATE Play-continuity re-anchor on top of #646/#645
**Cycle 1 review:** REQUEST-CHANGES-equivalent `5026690745` on `e7b34502eb3a7a3fcc8b716ef4a25a5bb7fc9db2`
**Cycle 1 addendum:** issue comment `5420568935` on the same head; not Review Cycle 2
**Cycle 2 review:** REQUEST-CHANGES-equivalent `5031234283` on `1d99c5e7a23cf864b671c6d3f0d17c65618a9327`
**D.2C2 implementation:** Buddy #645 merge `3ff46922e679ad6bef2ef0cf37f0bf87e4542a6c`
**D.2C2 accepted head:** `f772db17e00cbe2c0198ae53f169a10a6332a3ed`
**D.2C2 review:** 2 distinct-head cycles; final PASS-equivalent `5026532158`
**D.2C2 design:** Buddy #644 merge `f1eae2a3d27e430ee19e254d5b52fa556b2632ff`; accepted head `ded066cec49c3840c3b19c3e817ffa569a116f39`; Cycle 2 PASS-equivalent `5025378684`
**DungeonMind pin:** `bf40e933bdedf3cf08bb23a07a135958bdb7cc6b` — PR #46 reviewed zero-parent initialization authority
**Design branch:** `cutover/design-buddy-graph-engine-demolition`
**Design PR title:** `CUTOVER: design Buddy graph-engine demolition`
**First implementation successor:** D.2C3 / `cutover/native-genesis-read-write-continuity`
**Suggested D.2C3 PR title:** `CUTOVER: native genesis read/write continuity`
**Named D.3A successor:** `cutover/mounted-graph-engine-excision`
**Suggested D.3A PR title:** `CUTOVER: excise Buddy graph engine from production`
**Named D.3B successor:** `cutover/delete-legacy-graph-engine`
**Suggested D.3B PR title:** `CUTOVER: delete legacy Buddy graph engine`

> Repository law: [`AGENTS.md`](../../AGENTS.md). Sequencing authority:
> [`PR-TRACKER-campaign-supergraph.md`](PR-TRACKER-campaign-supergraph.md).
> Architecture authority:
> [`../Design/ARCHITECTURE-campaign-supergraph.md`](../Design/ARCHITECTURE-campaign-supergraph.md).

---

## 1. Mission

D.2C2 completed reviewed first-world *initialization*. That is not the same as
D.2 being complete.

A world created by D.2C2 currently cannot enter the shared native DungeonMind
read/write path. The mounted binder still assumes every world has the
historical Buddy-A → DungeonMind-D_A existing-world adoption bridge. Reviewed
initialization is reciprocally exclusive with that bridge: it publishes a real
`D_0` with `parent_revision_id = None` and no adoption receipt.

Demolition cannot begin until that continuity seam is closed. The frozen
sequence is:

```text
D.2C2  reviewed first-world initialization       DONE
  ↓
D.2C3  native genesis read/write continuity      REQUIRED
  ↓
D.3A   mounted production graph-engine excision
  ↓
       mounted server works with legacy engine imports blocked
       and old Buddy graph filesystem absent
  ↓
D.3B   physical legacy graph-engine package deletion
  ↓
       retired source/compatibility implementation disappears
```

D.2C3 is the last D.2 authority-migration slice. After it merges, D.3 is
demolition, not another semantic migration.

**D.3 is not DONE after D.3A.** D.3 becomes DONE only after D.3B merges and the
final source/runtime absence proof passes.

**D.2C3 is not dispatched until this design PR merges.** Then re-anchor
current `main` and dispatch the parseable D.2C3 CODE wrapper.

**D.3A is not dispatched until D.2C3 merges.** The D.3A → D.3B split remains
the demolition boundary. What changed is that repository inspection exposed
one remaining D.2 continuity seam that must close first.

After D.2C3, all mounted World Graph authority is DungeonMind-owned for both
legal genesis families:

```text
reads                         → DungeonMind native
exact-run Graph Review writes → DungeonMind native
Threat publication            → WorldGraphAuthority → DungeonMind
existing-world worldbuilding  → WorldGraphAuthority → DungeonMind
first-world/bootstrap         → WorldGraphInitializationAuthority → DungeonMind
native D_0 / D_A continuity   → one shared DirectAuthorityBinding
Buddy product/runtime state   → Buddy-owned stores
```

The tracker currently names one final capability:

```text
D.3 final Buddy graph-engine deletion
  delete graph_memory.kernel / world_supergraph / union_supergraph
  production imports
  prove the old graph is physically absent
```

At this base, the legacy namespaces still contain a mixture of:

- retired graph storage/publication/replay authority;
- production compatibility routing;
- pure Buddy-owned contribution and mechanics value contracts;
- projection DTOs;
- historical Eldyrwild migration/conformance tooling;
- tests and fixtures.

Independent AST inventory under `apps/live_control_server` at this design
base:

```text
graph_memory.kernel            58 import statements / 36 files
graph_memory.world_supergraph  36 import statements / 19 files
graph_memory.union_supergraph  32 import statements / 25 files
```

The sets overlap. Count is not an authority classification. The previous
37/20/26 figure is retired; do not treat it as current census.

One PR that relocates surviving product values, removes production routing,
deletes historical tools, and removes three package trees would violate the
one-capability rule and make semantic regressions hard to distinguish from
bulk deletion fallout. D.2C3 is likewise one capability: native genesis
binding. It does not excavate the engine.

---

## 2. Re-anchored predecessor truth

### 2.1 D.2C2 is complete as initialization

Buddy #645 is merged:

```text
PR              #645
accepted head   f772db17e00cbe2c0198ae53f169a10a6332a3ed
review cycles   2
final review    5026532158 — PASS-equivalent
merge           3ff46922e679ad6bef2ef0cf37f0bf87e4542a6c
```

It proved first-world *creation*:

- first-world eligibility/prepare use `WorldGraphInitializationAuthority.probe()`;
- first-world confirm creates/replays one DungeonMind `D_0` with null parent;
- native receipt truth is `baselineRevisionId=null`;
- mounted first-world review/prepare/confirm do not require Buddy graph files;
- exact retry, lost-response restart, and synchronized concurrent confirms
  converge on one receipt and one `D_0`;
- verified reviewed-init integrity errors stay inside the storage-neutral port.

It did **not** prove that the resulting `D_0` can be read or parented through
the shared native projection/retrieval/`WorldGraphAuthority` path.

### 2.2 The remaining D.2 seam is native genesis binding

`apps/live_control_server/integrations/dungeonmind/world_graph_reads.py::_load_direct_authority_binding()`
unconditionally requires:

```python
receipt = bundle.existing_world_adoptions.get_for_world(world_id)
if receipt is None:
    raise DirectWorldGraphReadError(..., code="authority_receipt_missing", ...)
```

`DirectAuthorityBinding.legacy_buddy_revision_id` is a required `str`.
`_resolve_revision_pin()` always has a Buddy-A to rewrite. Writes inherit the
same binder: `world_graph_writes._direct_services()` delegates to
`direct_services_from_bundle()`, and `DungeonMindWorldGraphAuthorityAdapter`
uses that path for D.2A/D.2B.

That algebra is correct for Eldyrwild existing-world adoption. It is false for
a D.2C2 world:

```text
reviewed-init receipt present
existing-world adoption receipt absent
D_0.parent_revision_id = None
no legacy Buddy revision exists to bridge
```

The two receipt families are reciprocally exclusive by D.2C1/D.2C2 design.
No new DungeonMind provider contract is required; the repository bundle already
exposes `existing_world_adoptions` and `reviewed_world_initializations`.

This is this design's own STOP condition: a concrete post-cutover gap showing
D.2 authority migration is incomplete. Hide it inside D.3A and demolition
starts from a lie.

### 2.3 APP-STATE merged during design authoring and Cycle 1 repair

APP-STATE #646 merged after #645 and before the original design head:

```text
PR              #646
accepted branch head observed 913cfe0bbce4db27250afd8277e3af50712ee029
merge           9c946cd8c24effccec8d06cfc1cb5e310c9edc5e
```

Cycle 1 repair re-anchors onto later APP-STATE Play-continuity docs that
landed on `main` after #646:

```text
f27bf550  APP-STATE: record AS3 done and keep AS4 next
89bb2a4c  APP-STATE: hand off Play continuity migration
764d9d1d  APP-STATE: reanchor Play continuity dispatch
```

Those commits are now part of the design base rather than a parallel lease.
This design intentionally does not touch them.

At this Cycle 2 repair the open PRs are:

```text
this D.3 design PR                          #647  this lease (design file only)
APP-STATE persist active Run continuity     #649  disjoint Play/AS4
```

`#649` currently touches `apps/live-control-ui/src/api/liveApi.test.ts` as a
test-only path. D.3A names `liveApi.ts` and Statblock/Graph Review UI in
§6.3; that is a **future** implementation lease. If #649 is still open when
D.3A is dispatched, serialize or split `liveApi.ts` / its tests rather than
editing through AS4.

D.2C3 and D.3A must still repeat the active-PR/write-lease check immediately
before implementation.

### 2.4 Current state docs are behind both #645 and this repair

The Campaign Supergraph tracker/roadmap still say #645 is `DOING` and D.3 is
`BLOCKED`, because those documents were correctly written before #645's merge
SHA was knowable.

Do not open a routine docs-only sync PR.

**D.2C3 implementation owns the #645 predecessor sync:**

```text
#645 D.2C2                 DONE
  merge                    3ff46922e679ad6bef2ef0cf37f0bf87e4542a6c
  accepted head            f772db17e00cbe2c0198ae53f169a10a6332a3ed
  review cycles            2
  final PASS-equivalent    5026532158

this D.3 design             DONE only with its real merge/review facts
D.2C3                       active / DOING in its implementation PR
D.3A                        BLOCKED on D.2C3
D.3B                        BLOCKED on D.3A
D.3                         not DONE
```

**D.3A implementation owns the D.2C3 predecessor sync** after that merge is
knowable. Mark D.3A active. Keep D.3B blocked and D.3 not DONE. Do not invent
future merge/review facts.

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

Mounted production means code reachable through normal DungeonBuddy operation,
including FastAPI app construction/`create_app()` imports:

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

The following are mounted FastAPI surface *today*, not historical scripts.
Their D.3A fate is frozen in §5.1 at **endpoint / UI** granularity, not
router-unmount granularity. D.2C3 does not change them.

```text
/api/live/world-graph-bootstrap/*                Kernel Eldyrwild bootstrap
/api/live/graph-authoring/*                      UnionSupergraph file apply
/api/live/graph-preview/union-supergraph/projection
                                                store-backed Plan/GR preview
remaining /api/live/graph-preview/*              mixed live product router
lifespan world_graph_prewarm                     import graph_memory.kernel
config.world_graph_authority_mode()              parser in world_supergraph.storage
routes.world_graph_projection                    module-level kernel import
routes.world_graph_retrieval                     module-level kernel import
routes.threat_query_hydration                    union_supergraph.statblock_binding
```

Active UI callers that D.3A must not orphan:

```text
Plan GraphIngestProjectionPanel          Open Union Graph
Graph Review live/candidate projection   getUnionSupergraphProjection
Graph Review authoring workspace         prepare/commit/merge-reconciliation
Statblock workbench create-context       getWorldGraphBootstrapStatus
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

### 3.5 Two legal genesis families

DungeonMind worlds have exactly two legal genesis authorities:

```text
existing-world adoption
  receipt family   bundle.existing_world_adoptions
  first revision   receipt.published_revision_id   (D_A)
  legacy bridge    receipt.source_provenance.source_world_revision_id  (Buddy-A)

reviewed first-world initialization
  receipt family   bundle.reviewed_world_initializations
  first revision   receipt.published_revision_id   (D_0)
  legacy bridge    none
```

They are reciprocally exclusive. Both present is integrity. A published head
with neither is integrity. Absence of both *and* absence of a head is the
existing uninitialized/not-adopted fail-closed case; do not invent a third
genesis.

---

## 4. D.2C3 — native genesis read/write continuity

D.2C3 is a bounded Buddy-side predecessor. It generalizes the already-landed
native binder across both genesis families. It is not demolition.

### 4.1 Merge-ready invariant

> **A world whose only genesis authority is a verified reviewed-world
> initialization receipt can be read through native projection/retrieval and
> parented through `WorldGraphAuthority` / existing-parent publication, using
> the same DirectAuthorityBinding path as an existing-world adopted world.
> The Eldyrwild Buddy-A → D_A bridge remains unchanged. No new DungeonMind
> provider contract is introduced.**

### 4.2 Frozen binding algebra

`_load_direct_authority_binding()` becomes a genesis binder, not an
adoption-only binder.

```text
existing-world adopted world
  existing_world_adoption receipt present
  reviewed_world_initialization receipt absent
  current head present
  → preserve Buddy-A → D_A compatibility bridge
  → legacy_buddy_revision_id = source_world_revision_id
  → dungeonmind_first_revision_id = adoption.published_revision_id
  → dungeonmind_head_revision_id = head.head_revision_id

reviewed first-world world
  reviewed_world_initialization receipt present
  existing_world_adoption receipt absent
  current head present
  → no legacy Buddy revision
  → dungeonmind_first_revision_id = init.published_revision_id   (D_0)
  → dungeonmind_head_revision_id = head.head_revision_id
  → legacy_buddy_revision_id = None

both receipts present
  → integrity failure
  → do not report initialized/adopted and do not report authority_unavailable

head present with neither recognized genesis receipt
  → integrity failure
  → fail closed; do not invent a genesis and do not fall back to Buddy files

neither receipt and no head
  → existing uninitialized / not-adopted fail-closed
  → do not mint a D_0 or an adoption from this binder
```

Verified receipt reads remain integrity-mapped, matching D.2C2:
`PersistenceIntegrityError` is integrity, not `authority_unavailable`.
A recognized genesis receipt without a current head remains an integrity
contradiction.

### 4.3 DirectAuthorityBinding shape

`legacy_buddy_revision_id` becomes optional. Preferred shape:

```python
@dataclass(frozen=True)
class DirectAuthorityBinding:
    world_id: str
    dungeonmind_first_revision_id: str
    dungeonmind_head_revision_id: str
    legacy_buddy_revision_id: str | None
    genesis: Literal["existing_world_adoption", "reviewed_world_initialization"]
```

Do not keep a fake Buddy revision string for first-world worlds. Do not reuse
`D_0` as `legacy_buddy_revision_id`.

### 4.4 Pin and parent algebra

`_resolve_revision_pin()`:

```text
revision_pin is None
  → None (current head), unchanged

legacy_buddy_revision_id is not None
  and revision_pin == legacy_buddy_revision_id
  → dungeonmind_first_revision_id     # A → D_A bridge only

otherwise
  → pass through to DungeonMind
  → unknown pins still fail closed as revision_not_bridged / not found
```

Ordinary DungeonMind pins, including `D_0` and later children, pass through
unchanged. First-world worlds have no A → D_A rewrite.

`_classify_parent_revision()`:

```text
legacy_buddy_revision_id is not None
  and parent == that id
  → governed_write_legacy_package, unchanged

otherwise
  → parent must be a real DungeonMind revision
  → D_0 is a legal existing parent for the next child
```

Do not require an adoption receipt to publish a D.2A/D.2B child of `D_0`.

### 4.5 Shared path, not a second factory

Reads, writes, and `DungeonMindWorldGraphAuthorityAdapter` continue to share
one binder. Do not create a first-world-only read adapter that bypasses
`direct_services_from_bundle()`.

`dungeonmind_kernel.world_graph_authority.bind_world_authority()` remains the
historical hydrated/frozen-store adoption binder. D.2C3 does not extend it
and does not put first-world worlds on that path. D.3A retires it from
mounted production (§5.1).

### 4.6 No new DungeonMind provider contract

D.2C3 consumes repositories already on the pin:

```text
bundle.existing_world_adoptions.get_for_world(world_id)
bundle.reviewed_world_initializations.get_for_world(world_id)
bundle.world_graph.get_head(world_id)
bundle.world_graph.get_revision(...)
```

If implementation discovers that a required native read/write cannot execute
with those already-landed contracts, STOP. That is not a demolition problem
and not permission to add a provider feature.

### 4.7 Required owning proof

One real-PostgreSQL witness, using the real mounted boundaries, covering
both genesis families:

```text
1. create a pristine world through D.2C2 first-world prepare/confirm
2. prove exactly one reviewed-init receipt, one D_0 with parent=None,
   and no existing-world adoption receipt
3. immediately native-project and native-retrieve that world/D_0
   (search + exact object as the retrieval minimum)
4. call WorldGraphAuthority.current_head / read_revision / mutation_context
   on the same world
5. publish one legal existing-parent child through an already-landed
   D.2A Threat or D.2B worldbuilding path
6. read the child natively; prove exact retry/recovery remains intact
7. rerun the existing Eldyrwild/adoption bridge witnesses so
   Buddy-A → D_A compatibility is unchanged
```

Required integration proofs must not silently skip. Report exact
pass/fail/skip counts. Zero required skips for this witness.

Also prove fail-closed cases at unit/adapter scope:

```text
both receipts present            → integrity, not a clean initialized state
receipt without current head     → integrity
head with neither genesis        → integrity
uninitialized (no head, neither) → not integrity-as-initialized
```

### 4.8 D.2C3 implementation write lease

#### Core owned paths

```text
apps/live_control_server/integrations/dungeonmind/world_graph_reads.py
apps/live_control_server/integrations/dungeonmind/world_graph_writes.py
apps/live_control_server/integrations/dungeonmind/world_graph_authority_adapter.py
```

Touch `world_graph_initialization_adapter.py` only if a verified-receipt
helper must be shared to keep integrity mapping identical. Do not reopen
first-world confirm semantics.

#### Owning tests

```text
tests/test_cutover_dungeonmind_first_world_initialization.py
tests/test_cutover_dungeonmind_world_graph_authority.py
new focused native-genesis continuity tests if cleaner than overloading
  the first-world file
existing Eldyrwild adoption / D.2A / D.2B regression cohorts named in §4.7
```

#### Explicitly outside D.2C3

```text
boot-imported engine stores in §5.1
authority-mode parser rehome
import blocker / filesystem-absence witnesses
buddy_files compatibility removal
Kernel / world_supergraph / union_supergraph deletion
Plan / Play / Build / Recap UX
APP-STATE
DungeonMind repository/provider code
new World Graph semantics
```

D.2C3 may not install the D.3A import blocker. `buddy_files` remains
supported until D.3A.

### 4.9 D.2C3 CODE successor shape

This steward design file is not `§1`–`§9` parseable. The D.2C3 dispatch
wrapper must be a parseable CODE handoff. Treat this document as semantic
authority; do not send implementers this file as the lease parser input.

Suggested wrapper:

```text
Docs/Plans/HANDOFF-CUTOVER-native-genesis-read-write-continuity-code.md
branch  cutover/native-genesis-read-write-continuity
title   CUTOVER: native genesis read/write continuity
```

The wrapper pins execution metadata, write lease, evidence, state sync, and
handback. It does not reopen the binding algebra.

**Dispatch law:** merge this design PR first. Then re-anchor current `main`
and dispatch the parseable D.2C3 CODE wrapper from the **merged** design.
Do not dispatch D.2C3 from an accepted-but-unmerged design head. That would
implement from a side-branch authority document and violates repository law.

### 4.10 D.2C3 review handback contract

Return:

1. exact PR / branch / final head SHA;
2. exact implementation base and rebase status;
3. this design PR's **merge SHA**, accepted head, and PASS-equivalent review
   authorizing D.2C3. An accepted-but-unmerged design head is not authority;
4. cumulative changed paths against the D.2C3 lease;
5. active parallel PRs checked;
6. binding algebra implemented for both genesis families;
7. `legacy_buddy_revision_id` optional; no fake Buddy revision on `D_0`;
8. pin/parent proofs: A→D_A still bridges, `D_0` passes through;
9. real-Postgres witness counts from §4.7;
10. Eldyrwild adoption-bridge regression result;
11. both-receipt / receipt-without-head / head-without-genesis integrity proofs;
12. exact commands with pass/fail/skip counts; zero required skips;
13. ruff + `git diff --check`;
14. state sync showing #645 DONE, this design's known facts, D.2C3 active,
    D.3A blocked, D.3 not DONE;
15. stop conditions or `none`.

The D.2C3 dispatch seed is not Review Cycle 1. Review begins with executable
implementation and owning evidence.

---

## 5. Frozen demolition architecture decisions

These decisions apply to D.3A/D.3B. D.2C3 does not execute them.

### 5.1 Boot-imported engine stores — frozen product fate

D.3A's merge-ready proof installs an import blocker for
`graph_memory.kernel`, `graph_memory.world_supergraph`, and
`graph_memory.union_supergraph` **before app import**. Any module-level
engine import on the `create_app()` graph fails that witness.

Step 0 classification is not the owner of these choices. Unresolved
architecture is not an implementation lease.

Dispositions:

```text
FAIL_CLOSED   retire the named capability; no engine import remains on the
              boot graph; HTTP/UI contract is frozen in §5.1.1
REHOME_DTO    consume already-landed DungeonMind projection/retrieval/value
              contracts only; byte/ID/digest parity where values move
REWRITE_PORT  already-frozen WorldGraphAuthority / initialization port;
              no new provider contract
STOP          still requires local head/revision/UnionSupergraphStore
              semantics; D.2 incomplete or split a predecessor
```

#### 5.1.1 Observable retired-HTTP contract

`FAIL_CLOSED` does **not** mean “unmount the router and hope.” An unmounted
route is 404. Live UI currently treats some 404s as “missing artifact,” not
“retired capability.”

For each retired HTTP path, D.3A uses exactly this observable:

```text
KEEP_MOUNTED_410
  the path stays registered on the live FastAPI app
  the handler imports none of kernel / world_supergraph / union_supergraph
  response is HTTP 410
  JSON carries a stable retired code + explicit retirement message
  no UnionSupergraphStore load, Kernel init, or file apply runs
```

Frozen retired codes:

```text
/api/live/graph-preview/union-supergraph/projection
  → 410  code=union_supergraph_preview_retired

/api/live/graph-authoring/prepare
/api/live/graph-authoring/commit
/api/live/graph-authoring/merge-reconciliation/prepare
/api/live/graph-authoring/merge-reconciliation/apply
  → 410  code=graph_authoring_store_retired

/api/live/world-graph-bootstrap/status
/api/live/world-graph-bootstrap/prepare
/api/live/world-graph-bootstrap/confirm
  → 410  code=world_graph_bootstrap_retired
```

Never:

- unmount a still-public path so callers observe 404;
- keep the engine implementation behind a 410;
- leave a live button/workspace that presents 404 as “missing projection”
  or “write succeeded.”

Engine implementation modules may remain on disk until D.3B DELETE. They must
not be imported by `create_app()`, retained routers, or lifespan.

#### 5.1.2 `/api/live/graph-preview` is endpoint-level, not router-level

`routes/graph_preview.py` is a mixed router. **Keep it mounted.** Do not
treat the whole `graph_preview.py` path as FAIL_CLOSED in the D.3A static
gate.

Retire only the store-backed endpoint:

```text
GET /api/live/graph-preview/union-supergraph/projection
```

Keep these mounted and import-block-safe (they are live product/source
workflows; they are not UnionSupergraphStore loads):

```text
GET  /api/live/graph-preview/artifacts
GET  /api/live/graph-preview/runs
GET  /api/live/graph-preview/latest
GET  /api/live/graph-preview/graph-ingest/runs
GET  /api/live/graph-preview/graph-ingest/latest
GET  /api/live/graph-preview/extraction-runs/{run_id}
GET  /api/live/graph-preview/extraction-runs/{run_id}/build-context
POST /api/live/graph-preview/extraction-runs
POST /api/live/graph-preview/existing-object-resolver/candidates
POST /api/live/graph-preview/gold-authoring/prepare
POST /api/live/graph-preview/gold-authoring/commit
POST /api/live/graph-preview/gold-authoring/verify-commit
GET  /api/live/graph-preview/gold-review/sessions
GET  /api/live/graph-preview/gold-review/compare
GET  /api/live/graph-preview/gold-review/evidence
GET  /api/live/graph-preview/gold-review/projection
GET  /api/live/graph-preview/gold-review/vocabulary-ablation
GET  /api/live/graph-preview/manual-review/beds
GET  /api/live/graph-preview/manual-review/beds/{bed_id}
GET  /api/live/graph-preview/recap
```

Required module splits so the retained router is import-block-safe:

```text
routes/graph_preview.py
  must not import union_supergraph_projection_adapter

GET /union-supergraph/projection
  KEEP_MOUNTED_410 stub with no adapter/engine import

POST /existing-object-resolver/candidates stays mounted
  graph_object_candidate_sources.py currently imports
  graph_memory.union_supergraph.load at module top for
  current_recap_projection. Drop that import.
  That scope is FAIL_CLOSED-as-unavailable (diagnostic, not 410 on
  the resolver endpoint) or REHOME_DTO onto already-mounted
  World Graph projection. Do not load a UnionSupergraphStore.

world_graph_recap_projection.py
  currently imports corpus-recap helpers from
  union_supergraph_projection_adapter. Extract those helpers into a
  non-engine module. Recap projection stays mounted.
```

If any other currently retained endpoint is later proven to import a
retired namespace at module top, split or FAIL_CLOSED that endpoint; do
not unmount the router.

Store-backed preview is ingest-store semantics, not the published World
Graph. Do not pretend native DungeonMind projection is the same product.
Plan/Graph Review may keep using `/api/live/world-graph-projection` and
`/api/live/world-graph-retrieval` for published authority.

#### 5.1.3 Live UI callers — Open Union Graph / candidate store preview

Live callers of `getUnionSupergraphProjection` today:

```text
GraphIngestProjectionPanel          Plan “Open Union Graph”
graphReviewLiveReviewState.ts       Graph Review candidate/live ingest projection
```

`GraphIngestProjectionPanel` currently maps HTTP 404 to “the latest
graph-ingest run disappeared or its projection artifact is missing.”

D.3A product choice for this store-backed visualization: **intentional
retirement**, not STOP, and not a Plan/Graph Review UX redesign.

Same PR must:

1. keep `GET /union-supergraph/projection` as KEEP_MOUNTED_410;
2. stop offering Open Union Graph as a working action; the Plan panel
   communicates that Union Graph store preview is retired;
3. stop Graph Review candidate/live ingest projection from calling the
   store API; that lane shows explicit retired/unavailable for
   preview-union visualization;
4. leave committed/exact-run DungeonMind World Graph projection in place
   (`GraphReviewCommittedProjectionPanel` / extract-promote);
5. treat HTTP 410 `union_supergraph_preview_retired` as retirement, never
   as a missing artifact;
6. update owning UI tests.

#### 5.1.4 Graph authoring — intentional retirement, not STOP

`/api/live/graph-authoring` is the expired PR003 UnionSupergraph *file
writer*. Exact-run Graph Review already publishes through DungeonMind.
This is **not** a remaining intended World Graph write capability, so D.3A
does **not** insert a predecessor migration and does **not** rewrite it
onto `WorldGraphAuthority`.

It is also not abandoned backend: Graph Review currently calls
`prepareGraphObjectAuthoringWrite` / `commitGraphObjectAuthoringWrite`,
mounts `GraphReviewAuthorDraftWorkspace`, and presents successful durable
writes.

D.3A product choice: **intentional retirement of the authoring UI/workflow
in the same PR as the backend 410.** Do not 410 the backend while a live
authoring surface remains.

Same PR must:

1. KEEP_MOUNTED_410 on all four authoring endpoints;
2. disable/remove the Graph Review authoring prepare/commit/merge-reconciliation
   workspace so users cannot operate a dead write flow, including at least:
   `GraphReviewAuthorDraftWorkspace`,
   `GraphObjectAuthoringPrepareCommitPanel`,
   `GraphReviewAuthoringRail` merge-reconciliation,
   `GraphProjectionReader` `graph-authoring-action`,
   authoring mode toggle;
3. keep exact-run extract-promote Graph Review mounted and working;
4. not copy `apply_union_supergraph_merge_plan_to_file` into a new namespace;
5. update owning UI tests.

Gold-authoring under `/api/live/graph-preview/gold-authoring/*` is fixture
JSON preview, not the UnionSupergraph file writer. It stays mounted unless
inventory proves a retired-namespace import on the boot graph.

#### 5.1.5 World-graph-bootstrap — 410, not unmount

Kernel Eldyrwild bootstrap prepare/confirm is retired. First-world creation
is `WorldGraphInitializationAuthority`; Eldyrwild living authority is
existing-world adoption. Do not rewrite bootstrap onto reviewed-init.

`StatblockWorkbenchModule` currently calls `getWorldGraphBootstrapStatus()`
as a live head/world oracle for create-context. Unmounting to 404 would
break that pin.

KEEP_MOUNTED_410 for status/prepare/confirm. D.3A updates Statblock
create-context to pin from already-landed World Graph / DungeonMind head
(`WorldGraphAuthority` / native projection), not Kernel bootstrap status.
Handle 410 as retired if any call remains.

#### 5.1.6 Remaining boot-imported surfaces

| Boot-imported surface | Disposition | D.3A meaning |
|---|---|---|
| Retained `/api/live/graph-preview/*` except `/union-supergraph/projection` | **keep mounted** | Import-block-safe. Not FAIL_CLOSED as a router. |
| Plan graph-preview / recap DTOs that do not import the three retired namespaces | **REHOME_DTO** | Keep storage-neutral `graph_memory.projection` / retrieval DTO modules. After D.3A they must not import kernel / world_supergraph / union_supergraph. Do not churn public wire schemas merely to rename a package. |
| `world_graph_prewarm` Kernel coordinator (`services/world_graph_prewarm.py`, app lifespan) | **FAIL_CLOSED** | No Kernel resident/prewarm worker. Lifespan start/stop may remain as a no-op so shutdown ownership does not import `graph_memory.kernel`. No HTTP 410; there is no public route. |
| `config.world_graph_authority_mode()` parser currently in `graph_memory.world_supergraph.storage` | **REHOME_DTO** | D.3A **must** rehome the parser/constants into Buddy-owned `config` / ports and apply §5.2. App boot cannot be import-blocked while `config.py` imports `world_supergraph.storage`. D.3B deletion of the old parser is not a substitute. |
| Module-level `import graph_memory.kernel` on `services/world_graph_projection.py` and `services/world_graph_retrieval.py` | **FAIL_CLOSED** for the file/kernel branch; production already uses DungeonMind | Remove the top-level kernel import. Production native methods stay. `_route_authority_read` / `dungeonmind_kernel.route_service_read` buddy_files passthrough is not a mounted production path after D.3A. Lazy kernel import is not an escape: these modules are imported at app construction. |
| Mounted `dungeonmind_kernel` hydrated read passthrough (`route_service_read`, `bind_world_authority` requiring frozen Buddy store) | **FAIL_CLOSED** | Not a production path after D.3A. Do not extend it for first-world worlds. Historical modules may remain until D.3B. |
| `routes/threat_query_hydration.py` → `graph_memory.union_supergraph.statblock_binding` | **REHOME_DTO** | Relocate still-used mechanics contracts per §5.4. Query/hydration stays mounted; it must not import `union_supergraph` after D.3A. |
| `get_world_graph_authority(world_root=...)` / `get_world_graph_initialization_authority(world_root=...)` selecting `BuddyFiles*Adapter` for a non-production root | **FAIL_CLOSED** | After D.3A a different `world_root` argument must not select the file adapter. Tests/tools that need legacy fixtures construct them directly. Configuration failure, not HTTP 410. |

If implementation discovers that a FAIL_CLOSED surface is still a real
operational dependency that requires local store semantics, STOP and re-brief.
Do not silently convert FAIL_CLOSED into REWRITE_PORT. Do not convert
intentional authoring retirement into STOP without a re-brief.

### 5.2 Production authority selection is retired

`DUNGEONMIND_WORLD_GRAPH_AUTHORITY` was a migration control plane. Its old
values currently include `buddy_files`, `quiesced`, and `dungeonmind`.
Today unset still defaults to `buddy_files` inside
`graph_memory.world_supergraph.storage.world_graph_authority_mode()`.

After D.3A, the *rehomed* parser is:

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

### 5.3 Mounted authority factories become one-way DungeonMind

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
is a product-reachable fallback branch, including a non-production
`world_root` selecting `BuddyFiles*Adapter`.

Tests/tools that intentionally need legacy fixtures must construct an explicit
fixture helper directly. Do not recreate the selector as `test_mode`, a hidden
env var, API parameter, query parameter, or header.

### 5.4 Relocate pure product values, not graph authority

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

### 5.5 Classify remaining hits before moving code

For each old-engine dependency *other than* the frozen §5.1 table:

```text
PURE VALUE / PURE TRANSFORM still needed → relocate to bounded Buddy owner
DUNGEONMIND mapping needed              → keep/relocate inside DM integration
LEGACY AUTHORITY / STORE / REPLAY        → delete caller or use existing port
HISTORICAL TOOLING                       → classify for D.3B
UNKNOWN                                  → STOP and re-brief
```

Moving the old Kernel wholesale to a new module name does not satisfy D.3.
Do not reclassify a §5.1 FAIL_CLOSED surface as PURE VALUE in order to keep
it mounted.

### 5.6 “Physically absent” is a runtime proof, not data destruction

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

### 5.7 `world_graph_root` may survive only as a non-authority designation

If a configured graph-root path still has a real safety/fixture role, D.3A need
not rename it for aesthetics.

After D.3A:

- mounted production never opens a head/revision under it;
- the directory need not exist;
- passing a different path may not select another mounted authority;
- no client/API input may create a legacy-root escape hatch.

If inventory shows the path has no remaining purpose, remove the obsolete config
in D.3A. Otherwise retain only the narrow safety/fixture designation.

### 5.8 Hydration/cache compatibility has no production owner

The DungeonMind→Buddy hydrated read model and cache existed for migration. After
D.2C3, D.2 native authority is complete.

D.3A deletes mounted hydration routing/configuration once inventory confirms no
remaining product consumer. Tests must move to native DungeonMind or explicit
legacy fixtures; tests do not justify product fallback.

### 5.9 DungeonMind contracts are frozen during demolition

D.3 adds no new provider capability. D.2C3 also adds none.

If D.3A discovers a mounted behavior that cannot execute using already-landed
DungeonMind read, governed publication, and reviewed initialization contracts
*after D.2C3*, STOP. That means D.2 is still incomplete; do not smuggle a
provider feature into a deletion slice.

### 5.10 No semantic rewrite

Preserve accepted behavior for:

```text
GM/PLAYER admissibility
search / exact object / neighborhood / evidence / source-anchor
revision pins and head semantics
exact-run Graph Review seals
Threat mechanics separation
existing-world worldbuilding publish/recovery
first-world initialization/retry/restart/concurrency
native D_0 read/write continuity after D.2C3
source/evidence closure
current API/wire schemas for remaining mounted routes
stable contribution/source IDs and digests
```

FAIL_CLOSED retired capabilities in §5.1 keep their public paths as
KEEP_MOUNTED_410 stubs; engine implementations are not rewritten onto
DungeonMind.

---

## 6. D.3A — mounted production graph-engine excision

Blocked until D.2C3 is merged and its native-genesis witness is green on
current `main`.

### 6.1 Merge-ready invariant

D.3A is merge-ready only when:

> **The mounted DungeonBuddy server can boot and execute its World Graph read,
> review, publication, and first-world workflows with imports from
> `graph_memory.kernel`, `graph_memory.world_supergraph`, and
> `graph_memory.union_supergraph` blocked before app import, while the legacy
> Buddy graph filesystem is absent. All authoritative graph I/O remains
> DungeonMind-owned. Boot-imported engine stores named in §5.1 are FAIL_CLOSED
> or REHOME_DTO as frozen. Any retained legacy consumer is explicit test/tooling/
> historical code and unreachable from mounted product accessors.**

D.3A gives D.3B a production dependency count of zero. That is independently
useful and reviewable.

### 6.2 Required implementation sequence

#### Step 0 — re-anchor and freeze inventory

Re-read current `main`, active PRs, this handoff, the accepted design PR, and
the merged D.2C3 implementation.

Confirm D.2C3's native-genesis witness is on the implementation base.

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

Apply §5.1 dispositions to the named boot-imported surfaces *before* inventing
new ones. Handback must explain every retained executable occurrence.

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

Rehome the authority-mode parser into Buddy-owned config/ports.

Make authority accessors DungeonMind-only.

Remove product branches that instantiate:

```text
BuddyFilesWorldGraphAuthorityAdapter
BuddyFilesWorldGraphInitializationAdapter
```

Retired environment values fail closed. Explicit legacy tests construct fixtures
directly. A non-production `world_root` does not select the file adapter.

#### Step 3 — execute §5.1 and remaining mounted engine imports

Keep `routes.graph_preview` mounted. Replace store-backed
`/union-supergraph/projection` with an import-free 410 stub and drop the
adapter import from the retained router.

Keep `routes.graph_authoring` and `routes.world_graph_bootstrap` registered
as import-free 410 stubs (KEEP_MOUNTED_410). Do not `include_router`-remove
them into 404.

In the same PR, apply the §5.1.3–§5.1.5 UI retirements so no live button
or authoring workspace still presents store writes/preview as working.

Switch every remaining `MOUNTED_PRODUCT` / `PURE_PRODUCT_VALUE` dependency to:

- an existing storage-neutral World Graph port;
- the existing DungeonMind integration; or
- the new Buddy-owned pure value boundary.

Do not rewrite historical tooling unless app boot or a mounted route still
imports it after §5.1. The §5.1 consumers *are* boot-imported; their fate is
already frozen.

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
boundaries, including a D.2C3 first-world world and the Eldyrwild adopted world.

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
native genesis D.2C3 (fresh D_0 read + existing-parent child)
Hermes/latest-recap graph reads
```

Use real PostgreSQL for publication/initialization/genesis cohorts where their
accepted handoffs require it. Required integration proofs must not silently skip.

#### Step 8 — carry backward state-authority sync

D.3A owns the D.2C3 predecessor sync from §2.4.

At minimum update current mutable CUTOVER authorities that still claim D.2C3
or D.3A is in flight:

```text
Docs/Plans/PR-TRACKER-campaign-supergraph.md
Docs/Roadmaps/ROADMAP-campaign-supergraph.md
Docs/Design/STATUS-world-graph-continuity-spine.md
Docs/Plans/STEWARDS-ANCHOR-cutover.md
Docs/Sources/design-agent/ACTIVE_AUTHORITY/PR-TRACKER-campaign-supergraph.md
Docs/Sources/design-agent/ACTIVE_AUTHORITY/ROADMAP-campaign-supergraph.md
this handoff / D.3A implementation handoff as appropriate
```

Record #645 and D.2C3 real merge/head/review. Record this design PR's real
completion only when known. Mark D.3A active. Keep D.3B blocked and D.3 not
DONE. Do not invent D.3A future merge/review facts.

### 6.3 D.3A implementation write lease

#### Core owned paths

```text
apps/live_control_server/main.py
apps/live_control_server/config.py
apps/live_control_server/ports/world_graph_authority_access.py
apps/live_control_server/ports/world_graph_initialization_access.py
apps/live_control_server/integrations/buddy_files/**
apps/live_control_server/integrations/dungeonmind/world_graph*.py
apps/live_control_server/integrations/dungeonmind_kernel/**   only to stop calling it from mounted product
apps/live_control_server/models/world_graph_contribution_values.py
apps/live_control_server/models/extract_promote.py
apps/live_control_server/models/threat_query_hydration.py
apps/live_control_server/routes/world_graph_bootstrap.py
apps/live_control_server/routes/graph_authoring.py
apps/live_control_server/routes/graph_preview.py
apps/live_control_server/routes/threat_query_hydration.py
apps/live_control_server/services/world_graph_bootstrap.py
apps/live_control_server/services/graph_object_authoring_commit.py
apps/live_control_server/services/graph_merge_reconciliation_materialize.py
apps/live_control_server/services/union_supergraph_projection_adapter.py
apps/live_control_server/services/graph_object_candidate_sources.py
apps/live_control_server/services/world_graph_recap_projection.py
apps/live_control_server/services/world_graph_prewarm.py
apps/live-control-ui/src/api/liveApi.ts
apps/live-control-ui/src/planSurface/graphPreview/GraphIngestProjectionPanel.tsx
apps/live-control-ui/src/planSurface/graphReviewWorkbench/graphReviewLiveReviewState.ts
apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewAuthorDraftWorkspace.tsx
apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphObjectAuthoringPrepareCommitPanel.tsx
apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewAuthoringRail.tsx
apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphMergeReconciliationMaterializationPanel.tsx
apps/live-control-ui/src/planSurface/graphProjectionReader/GraphProjectionReader.tsx
apps/live-control-ui/src/surface/modules/StatblockWorkbenchModule.tsx
owning UI tests for those retired actions / workspaces
apps/live_control_server/services/first_world_graph.py
apps/live_control_server/services/first_world_graph_publication.py
apps/live_control_server/services/world_graph_*.py
apps/live_control_server/services/graph_review_*.py
apps/live_control_server/services/worldbuilding_graph_publication.py
apps/live_control_server/services/threat_*.py
src/graph_memory/projection/**
new narrowly named Buddy-owned contribution/mechanics value modules required by §5.4
```

The named boot-imported routes/adapters and the §5.1.3–§5.1.5 UI files are
the lease. Bounded `apps/live_control_server/**` or `apps/live-control-ui/**`
discovery is **not** permission to redesign Plan/Graph Review. FAIL_CLOSED
means KEEP_MOUNTED_410 plus the frozen minimal UI retirement, not a new UX.

#### Bounded discovery lease

A file under `apps/live_control_server/**` or mounted product `src/**` may be
added only when all are true:

1. it has a base-revision executable import from a retired namespace;
2. D.3A only replaces that import/call with a frozen owner from this design
   or executes a §5.1 KEEP_MOUNTED_410 / import-free stub;
3. no remaining mounted wire/public semantics change except the frozen
   410 retirement responses and the frozen minimal UI disable/removal;
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
FAIL_CLOSED proofs for KEEP_MOUNTED_410 bootstrap / graph-authoring /
  union-supergraph projection; retained graph-preview endpoints still boot;
  Open Union Graph / authoring workspace / Statblock bootstrap-status UI
  / prewarm / retired selector / non-production world_root
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
Plan UX replacement beyond the frozen §5.1.3–§5.1.5 retirements
```

D.3A must re-check active PRs at implementation time. Any new lease overlap is
a serialization/transfer decision, not permission to edit through it.

### 6.4 Required D.3A evidence

#### Static dependency gate

At accepted head:

```text
0 mounted-product imports from graph_memory.kernel
0 mounted-product imports from graph_memory.world_supergraph
0 mounted-product imports from graph_memory.union_supergraph
0 mounted factory branches selecting buddy_files/quiesced
0 hydration/local fallback on DungeonMind failure
0 engine implementation behind KEEP_MOUNTED_410 stubs
0 create_app() import of union_supergraph_projection_adapter
  / Kernel bootstrap service / UnionSupergraph file-apply
0 lifespan Kernel prewarm import
graph-preview router remains mounted; retained endpoints besides
  /union-supergraph/projection still registered
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
native D_0 projection/retrieval + one existing-parent child (D.2C3)
Threat publish/recover
worldbuilding publish/recover
Hermes/latest-recap graph comparison or owning service boundary
FAIL_CLOSED retired bootstrap/authoring/store-preview paths as 410
retained graph-preview extraction/gold/manual/recap endpoints still boot
Open Union Graph / authoring workspace / Statblock bootstrap-status UI
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
non-production world_root → configuration failure; no file adapter
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
native genesis: D.2C3 witness still green under the import blocker
Eldyrwild adoption bridge: Buddy-A → D_A unchanged
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

## 7. D.3B — physical legacy graph-engine deletion

D.3B is blocked until D.3A is merged and its import-blocked production proof is
green on current `main`.

### 7.1 Merge-ready invariant

> **Retired Buddy graph-engine source packages and compatibility adapters no
> longer exist as executable implementation; every intentionally retained
> historical executable tool has a new explicit non-engine owner; mounted
> DungeonBuddy remains green on DungeonMind; and the legacy-filesystem absence
> proof still passes.**

### 7.2 Primary deletion targets

Subject to D.3A's inventory:

```text
src/graph_memory/kernel/**
src/graph_memory/world_supergraph/**
src/graph_memory/union_supergraph/**
apps/live_control_server/integrations/buddy_files/**
retired hydration/cache implementation
FAIL_CLOSED bootstrap/authoring/store-preview implementations replaced by
  import-free 410 stubs in D.3A
legacy-only tests whose sole purpose is deleted authority behavior
```

If a storage-neutral product value still lives in those directories after D.3A,
D.3A is incomplete. Do not rescue it during bulk deletion by creating a second
owner.

### 7.3 Historical tooling classification

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

### 7.4 Final D.3 evidence

At D.3B accepted head:

```text
legacy source package directories absent
buddy_files integration absent
production import-blocker still green
legacy graph filesystem absence still green
current DungeonMind read/write cohorts green, including D.2C3 genesis
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

## 8. Final production architecture

```text
DungeonBuddy product
  |
  +-- WorldGraphAuthority --------------------------+
  |                                                  |
  +-- WorldGraphInitializationAuthority ------------+--> DungeonMind
  |                                                  |    PostgreSQL authority
  +-- native projection/retrieval/evidence ----------+
  |
  +-- one DirectAuthorityBinding covering
        existing-world adoption  (Buddy-A → D_A)
        reviewed first-world     (D_0, no legacy bridge)

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
NO mounted Kernel bootstrap / UnionSupergraph file apply /
   UnionSupergraphStore Plan preview / Kernel prewarm
```

This is the CUTOVER completion condition: DungeonMind authority no longer relies
on future engineers remembering not to call the old engine. The engine is first
absent from the production dependency graph, then absent from source.

---

## 9. Explicitly out of scope

Do not use D.2C3 or D.3 to:

- change DungeonMind semantics/public contracts;
- reopen ExistingWorldAdoption or catch-up without a real `STALE` event;
- create another Buddy graph database/schema;
- move mechanics/statblocks into semantic World Graph authority;
- redesign Graph Review UX/API;
- redesign Plan/Play/Build/Hermes behavior beyond the frozen §5.1.3–§5.1.5
  retirements (410 + disable dead store actions is not a replacement UX);
- merge APP-STATE feature work into CUTOVER;
- delete source artifacts/evidence/candidate/workspace state;
- rename every surviving `graph_memory` package for aesthetics;
- rewrite historical docs to erase old names;
- automatically delete user/local graph data;
- introduce generic JSON/CRUD replacement abstractions;
- move the old Kernel wholesale under a new namespace;
- smuggle D.2C3 into D.3A or D.3A into D.3B;
- broaden into optimization unless a concrete correctness blocker appears.

---

## 10. Stop / re-brief conditions

STOP if:

1. a mounted behavior still requires local Buddy head/revision/store semantics
   after the §5.1 FAIL_CLOSED retirements;
2. a required path is leased by another active lane and cannot be serialized;
3. value relocation changes durable IDs, canonical bytes, digests, acceptance
   semantics, or public API shape for remaining mounted routes;
4. a supposed pure value materially depends on local graph state/replay;
5. a new DungeonMind provider contract is required;
6. an old authority mode is actually required by a production deployment rather
   than tests/tooling;
7. filesystem absence would require deleting user data;
8. an operational historical tool cannot be rehomed without the engine;
9. the app cannot boot under a true pre-import blocker after §5.1;
10. implementation needs broad Play/Application-State changes;
11. D.2C3 cannot bind a reviewed-init world without an adoption receipt using
    already-landed repositories;
12. a concrete post-cutover failure shows D.2 authority migration was incomplete
    *beyond* the frozen D.2C3 seam;
13. a §5.1 FAIL_CLOSED / KEEP_MOUNTED_410 surface is still operationally
    required as a local store;
14. a live UI still presents store-backed preview or authoring as a working
    write/open action after the frozen 410 retirement.

---

## 11. Suggested nano-commit stories

### D.2C3

```text
1. generalize DirectAuthorityBinding across both genesis families
2. optional legacy bridge; pin/parent algebra; integrity cases
3. first-world D_0 native read + existing-parent child witness
4. Eldyrwild adoption-bridge regression
5. carry #645 predecessor state sync; keep D.3A blocked
```

### D.3A (after D.2C3 merges)

```text
1. establish Buddy-owned contribution/mechanics values + parity tests
2. switch mounted DTOs/services off legacy value imports
3. rehome selector parser; make factories DungeonMind-only; retire old modes
4. KEEP_MOUNTED_410 stubs + §5.1.3–§5.1.5 UI retirement; drop engine
   imports from retained routers; Kernel prewarm no-op
5. add import-blocked + legacy-filesystem-absent witnesses
6. run D.1/D.2/D.2C3 regressions and close the dependency inventory
7. carry D.2C3 + accepted-design predecessor state sync
```

Do not mix D.2C3 into D.3A. Do not mix D.3B bulk deletion into D.3A.

---

## 12. D.3A review handback contract

Return:

1. exact PR / branch / final head SHA;
2. exact implementation base and rebase status;
3. accepted D.3 design merge/head/review authorizing D.3A;
4. merged D.2C3 SHA/review authorizing demolition to begin;
5. cumulative changed paths against lease;
6. active parallel PRs checked and serialization decisions;
7. complete legacy-import classification summary, including §5.1 outcomes;
8. relocated value families and canonical owners;
9. serialization/ID/digest/validation parity evidence;
10. final selector behavior for unset/dungeonmind/buddy_files/quiesced/unknown
    and non-production `world_root`;
11. static zero-mounted-import proof for all three legacy namespaces;
12. import-blocker witness installed before app import;
13. legacy graph filesystem absent-before/after proof;
14. no hydration/cache/local fallback on DungeonMind failure;
15. KEEP_MOUNTED_410 proofs for bootstrap / graph-authoring /
    `/union-supergraph/projection`; retained graph-preview endpoints still
    boot; Open Union Graph / authoring workspace / Statblock bootstrap-status
    UI plus Kernel prewarm;
16. projection/retrieval/evidence/anchor results;
17. D.1 Graph Review results;
18. D.2A Threat PostgreSQL publish/recovery results;
19. D.2B worldbuilding PostgreSQL publish/recovery results;
20. D.2C2 first-world PostgreSQL init/retry/restart/concurrency results;
21. D.2C3 native genesis read/write results under the blocker;
22. Hermes/latest-recap graph-read result;
23. exact commands with pass/fail/skip counts;
24. ruff + `git diff --check`;
25. state sync showing #645 DONE, D.2C3 DONE, design DONE, D.3A active,
    D.3B blocked, D.3 not DONE;
26. executable legacy consumers deferred to D.3B with
    DELETE/REHOME/REWRITE classification;
27. stop conditions or `none`.

The D.3A dispatch wrapper must also be a parseable CODE handoff. Suggested:

```text
Docs/Plans/HANDOFF-CUTOVER-mounted-graph-engine-excision-code.md
```

The D.3A dispatch seed is not Review Cycle 1. Review begins with executable
implementation and owning evidence.

---

## 13. Design review focus

Review this repaired design specifically for:

1. **Predecessor:** is D.2C3 the right one-capability closure before demolition,
   and is the two-family genesis binder complete enough to dispatch?
2. **Decomposition:** after D.2C3, is D.3A production excision → D.3B physical
   deletion still the right demolition boundary?
3. **Boot fate:** are KEEP_MOUNTED_410 + endpoint-level graph-preview +
   intentional UI retirement the right product decisions, vs STOP?
4. **Authority retirement:** should `buddy_files` / `quiesced` / non-production
   `world_root` fail closed rather than be silently ignored?
5. **Value ownership:** are contribution/projection/mechanics values preserved
   without copying graph authority into a new namespace?
6. **Absence proof:** does pre-import blocking + real DungeonMind flows + missing
   legacy graph directory prove production independence *after* §5.1?
7. **Historical tooling:** is DELETE/REHOME/REWRITE/STOP sufficient to keep
   forensic compatibility from preserving the engine indefinitely?
8. **Parallelism:** are the D.2C3 and D.3A leases compatible with future lanes
   after mandatory implementation-time re-anchor?
9. **Data safety:** is “physically absent” correctly defined as runtime
   independence rather than automatic deletion of user graph data?

Do not dispatch D.2C3 until this design PR **merges** after a formal
PASS-equivalent review. An accepted-but-unmerged design head is not
dispatch authority.

Do not dispatch D.3A until D.2C3 is merged.

Do not merge D.3 as DONE from D.3A.
