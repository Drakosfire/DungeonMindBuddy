---
pr_body_template: |
  ## Handoff pointer
  - Workstream: CUTOVER / D.3B — physical legacy graph-engine deletion
  - Flow: CUTOVER
  - Direction: DESIGN → CODE
  - Handoff: `Docs/Plans/HANDOFF-CUTOVER-delete-legacy-graph-engine.md`
  - Frozen design authority: `Docs/Plans/HANDOFF-CUTOVER-buddy-graph-engine-demolition.md` §8
  - Predecessor: Buddy #665 / D.3A mounted production graph-engine excision
  - Predecessor accepted head: `189ffd50157534d192b2af008c48a76d12ccbc4c`
  - Predecessor executable implementation tip: `064db76a7be5af73a655480506eab1baf6161a24`
  - Predecessor merge: `1a98bdb8a462ecc088ee70c2cecbed5c0d99ac3b`
  - Predecessor formal review cycles: 3
  - Predecessor final review: Cycle 3 PASS-equivalent `5059851179`
  - Steward re-anchor base before this handoff commit: `1a98bdb8a462ecc088ee70c2cecbed5c0d99ac3b`
  - Branch: `cutover/delete-legacy-graph-engine`
  - PR title: `CUTOVER: delete legacy Buddy graph engine`

  ## Verification pointer
  The checked-in handoff, executable-consumer disposition ledger, cumulative diff,
  source-absence proof, retained D.3A fresh-interpreter witness, exact DungeonMind
  read/write regression evidence, and verification provenance are the review contract.
  The PR body is transport metadata.
---

# HANDOFF — CUTOVER D.3B: physical legacy graph-engine deletion

**Created:** 2026-08-29  
**Status:** ACTIVE — dispatch one implementation capability  
**Canonical handoff:** `Docs/Plans/HANDOFF-CUTOVER-delete-legacy-graph-engine.md`  
**Workstream / flow:** CUTOVER  
**Direction:** DESIGN → CODE  
**Repository:** `Drakosfire/DungeonMindBuddy`  
**Branch:** `cutover/delete-legacy-graph-engine`  
**PR title:** `CUTOVER: delete legacy Buddy graph engine`  
**Frozen design authority:** `Docs/Plans/HANDOFF-CUTOVER-buddy-graph-engine-demolition.md` §8  
**Steward re-anchor base before this handoff commit:** `1a98bdb8a462ecc088ee70c2cecbed5c0d99ac3b`  
**Predecessor:** D.3A / Buddy #665 / accepted head `189ffd50157534d192b2af008c48a76d12ccbc4c` / merge `1a98bdb8a462ecc088ee70c2cecbed5c0d99ac3b` / 3 formal review cycles / Cycle 3 PASS-equivalent `5059851179`  
**Named successor:** none inside D.3. This is the final D.3 implementation slice. After merge + final absence proof, D.3 may become `DONE`.

> D.3A proved the mounted product does not need the Buddy graph engine.
> D.3B removes the retired executable implementation from the repository.
>
> This is **deletion after authority transfer**, not another migration.
> If implementation discovers a retained product capability that still requires
> the retired engine semantics, STOP. Do not hide a semantic migration inside a
> package-deletion PR.

---

## Dispatch law

The worker must branch from the current `main` **containing this handoff**, record
that exact SHA before changing executable code, and re-check active PRs/write leases.
The immutable predecessor truth at steward design time is:

```text
D.3A / Buddy #665
accepted head               189ffd50157534d192b2af008c48a76d12ccbc4c
executable implementation   064db76a7be5af73a655480506eab1baf6161a24
merge                       1a98bdb8a462ecc088ee70c2cecbed5c0d99ac3b
formal review cycles        3
final review                5059851179 — PASS-equivalent
```

D.3A's accepted proof established, with the forbidden imports blocked before app
import and with the legacy graph filesystem absent:

```text
mounted app boot/lifespan                    GREEN
native projection/retrieval                  GREEN
search/object/neighborhood/evidence/anchor   GREEN
Threat publish + exact retry                 GREEN
worldbuilding publish + exact retry          GREEN
first-world DungeonMind D_0                  GREEN
Graph Review D_0 → D_1 publish               GREEN
Graph Review retry + fresh-client recovery   GREEN
Hermes owning query boundary                 GREEN
source admission                             GREEN
retired 410 routes                           GREEN
legacy graph filesystem absent before/after  GREEN
required PostgreSQL skips                    0
```

That proof is D.3B's safety floor. D.3B may delete implementation that D.3A proved
unnecessary; it may not weaken or replace those surviving product contracts.

### Parallel-lane check at design time

The only open PR observed after #665 merged is AGENT-INTERACTION #666,
`AGENT-INTERACTION: extract ContextAssembler v1`.

Its changed paths are:

```text
Docs/Plans/HANDOFF-AGENT-INTERACTION-context-assembler-v1.md
Docs/Plans/HANDOFF-AGENT-INTERACTION-graph-agent-policy-boundary-v1.md
apps/live_control_server/services/agent_context_assembler.py
apps/live_control_server/services/agent_turn_trace.py
apps/live_control_server/services/hermes_graph_query.py
tests/test_agent_context_assembler.py
tests/test_agent_turn_trace.py
tests/test_live_control_server.py
tests/test_live_query_hermes_graph.py
```

D.3B is expected to be disjoint from those paths. Do **not** edit them merely to
make broad deletion fallout green. If physical deletion exposes a genuine dependency
inside a #666-leased path, STOP and report the exact dependency / ownership collision.
Whichever branch merges second must re-anchor normally.

---

## §1 Mission and merge-ready invariant

### Mission

Physically remove the retired Buddy World Graph engine and its obsolete compatibility
adapters from executable repository state while preserving the already-proven
DungeonMind-native product behavior.

### Merge-ready invariant

> **The retired Buddy graph-engine source packages, BuddyFiles authority adapter,
> and obsolete Kernel compatibility implementation no longer exist as executable
> code; every surviving executable consumer has either been deleted with them or
> explicitly rehomed under a non-engine historical/tooling owner; the mounted
> DungeonBuddy application remains green on DungeonMind; and the D.3A legacy-import
> and legacy-filesystem-absence proof still passes.**

The final state must make this statement true without qualification:

```text
src/graph_memory/kernel/              ABSENT
src/graph_memory/world_supergraph/    ABSENT
src/graph_memory/union_supergraph/    ABSENT
apps/live_control_server/integrations/buddy_files/        ABSENT
mounted Buddy graph authority                              ABSENT
product fallback to Buddy graph files                      IMPOSSIBLE
DungeonMind-native read/write/init/authoring               GREEN
legacy <root>/graph_memory/worlds creation                  ABSENT
```

`apps/live_control_server/integrations/dungeonmind_kernel/**` is also part of the
D.3B executable-consumer inventory. It is a historical compatibility/migration tree,
not a mounted product owner after D.3A. It must not remain as an executable
`integrations/` backdoor to the deleted engine. Delete it when dead; if an exact
historical/conformance tool still has operational value, rehome only that bounded
tool under an explicit non-engine tooling owner before deleting the compatibility
tree. Do not preserve or rename the whole bridge.

### What this capability is not

D.3B does **not**:

- change DungeonMind graph schemas, publication semantics, identity semantics, or
  source provenance;
- add another graph authority or compatibility mode;
- migrate user data;
- delete user/local graph data from disk;
- rewrite historical docs so old namespace names disappear from history;
- rename all remaining `graph_memory` modules for aesthetics;
- replace the retired engine with generic JSON/CRUD abstractions;
- move the old Kernel wholesale under a new namespace;
- reopen D.2C3 genesis, D.2C4 manual authoring, or D.3A mounted authority choices;
- optimize unrelated code while deleting packages.

---

## §2 Authority and predecessor truth

Read before editing, in this order:

1. `AGENTS.md`
2. `Docs/Plans/PR-TRACKER-campaign-supergraph.md`
3. `Docs/Plans/HANDOFF-CUTOVER-buddy-graph-engine-demolition.md` §8
4. `Docs/Plans/HANDOFF-CUTOVER-mounted-graph-engine-excision.md`
5. `Docs/Plans/HANDBACK-CUTOVER-D3A-Review-Cycle-3.md`
6. this handoff
7. current repository import/entrypoint/test inventory on the exact dispatch head

Frozen predecessor chain:

```text
D.2C2 first-world initialization
  #645 / merge 3ff46922e679ad6bef2ef0cf37f0bf87e4542a6c

D.2C3 native genesis continuity
  #651 / accepted 9508b71655665005df8f12da74c239fe7eb17c0c
  merge 84f3401b23fcac32a57416d5419dc7d33cf6eabc
  4 formal cycles

D.2C4 Graph Review manual authoring continuity
  #662 / accepted 1ab48453cb556ca9d01ff84173ab3e2fdf81d1ec
  merge 2f1b44aa8ad8bad78269c0cadf624882cd0f459f
  4 formal cycles / PASS 5059141212

D.3A mounted graph-engine excision
  #665 / accepted 189ffd50157534d192b2af008c48a76d12ccbc4c
  executable tip 064db76a7be5af73a655480506eab1baf6161a24
  merge 1a98bdb8a462ecc088ee70c2cecbed5c0d99ac3b
  3 formal cycles / PASS 5059851179
```

Current DungeonMind pin at design time remains:

```text
5ca5d688612349034f8ca490d465af166d883e6e
```

Do not move that pin in D.3B unless physical deletion exposes an independently
reviewable provider-contract blocker. That is a STOP/split signal, not incidental
cleanup.

---

## §3 Step 0 is mandatory: executable-consumer disposition ledger

D.3B must **not** begin with recursive deletion. Begin by proving what still imports,
loads, executes, re-exports, references through an entrypoint, or dynamically imports
the retired implementation.

### 3.1 Inventory targets

Inventory executable consumers of at least:

```text
graph_memory.kernel
graph_memory.kernel.*
graph_memory.world_supergraph
graph_memory.world_supergraph.*
graph_memory.union_supergraph
graph_memory.union_supergraph.*
apps.live_control_server.integrations.buddy_files
apps.live_control_server.integrations.buddy_files.*
apps.live_control_server.integrations.dungeonmind_kernel
apps.live_control_server.integrations.dungeonmind_kernel.*
```

Also inventory direct filesystem assumptions tied to the retired store:

```text
graph_memory/worlds
WorldGraphStore / head files / revision files
hydration / replay / prewarm caches
legacy union-store paths
BuddyFilesWorldGraphAuthorityAdapter
BuddyFilesWorldGraphInitializationAdapter
```

Search these executable domains, not just mounted server imports:

```text
apps/**
src/**
scripts/**
tests/**
pyproject.toml / packaging entrypoints
other executable migration/conformance tooling
```

Historical Markdown, merged reports, sealed evidence, and old PR records may mention
these names forever. Textual history is not an executable consumer and is not a
reason to rewrite history.

### 3.2 Inventory method

Use AST/import inspection plus literal/dynamic import and entrypoint searches. A
plain grep count is useful as a seed but is not sufficient authority.

Classify every executable hit into one of exactly four dispositions:

```text
DELETE
  The executable consumer exists only for the retired Buddy graph engine or a
  completed migration/conformance operation. Delete it and its legacy-only tests.

REHOME
  The executable tool still has explicit operational/forensic value, but that value
  is not graph-engine authority. Move only the minimal tool/value into an existing
  explicit non-engine tooling owner, preserve behavior with focused parity evidence,
  then delete the old dependency.

REWRITE
  The consumer is still a current product/proof boundary but can consume already-
  landed DungeonMind/Buddy-owned contracts without changing public behavior. Keep
  the rewrite minimal and prove parity at the owning boundary.

STOP
  The consumer still requires real Buddy graph-head/revision/store semantics,
  would require a new DungeonMind provider contract, or would change a surviving
  product workflow. Report it before deletion. That means D.3A's claimed semantic
  migration was incomplete or D.3B needs an explicit split.
```

No `KEEP_LEGACY` category exists.

### 3.3 Rehome law

Do not create a new generic `legacy_graph_engine`, `old_kernel`, `compat_graph`, or
similar package merely to make deletion statistics look green.

A REHOME is valid only when:

1. the surviving behavior is explicitly non-authoritative tooling/history;
2. the target owner is semantically honest and non-mounted;
3. the moved code is minimal rather than a renamed dependency subtree;
4. no deleted engine type/store becomes a new public product abstraction;
5. focused parity evidence proves the moved behavior did not change.

If there is no natural owner, STOP rather than invent one casually.

### 3.4 Current-main seed that must be resolved

D.3A intentionally left at least one known executable compatibility seam:

```text
apps/live_control_server/services/threat_publication_commits.py
  _KernelProxy
    → lazy import graph_memory.kernel
```

D.3A proved mounted DungeonMind publication never touches that proxy; it exists for
explicit unmounted/test-injected graph hooks. D.3B cannot delete `graph_memory.kernel`
and leave a product service with a latent import of the deleted package.

Expected D.3B disposition:

- remove the Kernel default/adapter path if it exists only for legacy tests;
- keep explicit injected `merge_fn` / `lookup_fn` testing hooks only if they remain
  useful without importing Kernel;
- legacy behavior tests that require real Kernel semantics become DELETE or explicit
  historical-tooling REHOME, not product fallbacks.

If inspection proves a current user-facing Threat path still genuinely requires this
Kernel fallback, STOP: that contradicts the D.3A authority invariant.

---

## §4 Physical deletion targets and write lease

The HANDOFF §4 allowlist is this lane's write lease. D.3B is deletion-heavy, so the
lease is category-bounded rather than pretending every obsolete file is already
known. Every changed path must appear in the final handback with its Step-0
classification.

### 4.1 Primary package deletion lease

```text
src/graph_memory/kernel/**
src/graph_memory/world_supergraph/**
src/graph_memory/union_supergraph/**
apps/live_control_server/integrations/buddy_files/**
apps/live_control_server/integrations/dungeonmind_kernel/**
```

Target final state:

```text
all five trees above are absent as executable compatibility/engine owners
```

For `dungeonmind_kernel/**`, a bounded REHOME of genuinely useful historical tooling
is allowed only under §3.3; the integration compatibility tree itself must disappear.

### 4.2 Legacy implementation cleanup lease

Files outside the primary trees may be edited/deleted when Step 0 classifies them as
an executable consumer of those trees or as an implementation behind a capability
already frozen retired in D.3A. Expected seeds include, if still present on dispatch
head:

```text
apps/live_control_server/services/world_graph_prewarm.py
apps/live_control_server/services/union_supergraph_projection_adapter.py
apps/live_control_server/services/graph_merge_reconciliation_materialize.py
apps/live_control_server/services/world_graph_bootstrap.py
retired hydration/replay/cache implementation
legacy-only migration/conformance services under apps/live_control_server/services/*cutover*
legacy-only CLI / scripts / entrypoints
```

The mounted **410 route stubs themselves are retained** where D.3A froze a stable
public retirement contract. Delete obsolete implementation behind them, not the
registered 410 behavior.

Do not assume every `cutover_*` service is deletable. Step 0 must classify it from
current consumers and preserved evidence authority.

### 4.3 Surviving storage-neutral `graph_memory` modules are not deletion targets

D.3B deletes the retired engine packages, **not all of `src/graph_memory`**.
Storage-neutral candidate/extraction/evidence/projection/retrieval/value modules that
remain legitimate product contracts may stay when they do not depend on the three
retired namespaces.

Examples of categories that may legitimately survive after proof:

```text
candidate graph / extraction DTOs
source/evidence utilities
projection/retrieval DTOs and pure view helpers
extract-promote sealed proposal/value helpers
non-authoritative ingestion artifacts/contracts
```

Do not rename them merely because `graph_memory` is aesthetically broad. The final
absence target is authority/engine implementation, not vocabulary cleansing.

### 4.4 Bounded dependent-consumer lease

Any executable file under these domains may be changed **only after** Step 0 records
its exact DELETE / REHOME / REWRITE disposition:

```text
apps/live_control_server/**
src/graph_memory/** outside the primary deletion trees
scripts/**
tests/**
pyproject.toml
```

`uv.lock` is not expected to change. If dependency/package metadata must change only
because deleted internal modules disappear, keep it minimal and explain it. A new
third-party dependency is a STOP/split signal.

### 4.5 Explicit parallel exclusions

While PR #666 is open, D.3B does not lease:

```text
apps/live_control_server/services/agent_context_assembler.py
apps/live_control_server/services/agent_turn_trace.py
apps/live_control_server/services/hermes_graph_query.py
tests/test_agent_context_assembler.py
tests/test_agent_turn_trace.py
tests/test_live_control_server.py
tests/test_live_query_hermes_graph.py
Docs/Plans/HANDOFF-AGENT-INTERACTION-context-assembler-v1.md
Docs/Plans/HANDOFF-AGENT-INTERACTION-graph-agent-policy-boundary-v1.md
```

If #666 merges before dispatch, re-anchor and re-run Step 0. If D.3B truly needs one
of these paths after re-anchor, report the dependency and serialize/transfer the
lease; do not create a silent cross-lane edit.

### 4.6 Backward-looking state-authority sync lease

D.3B implementation owns the truthful predecessor sync for merged D.3A #665:

```text
Docs/Plans/HANDOFF-CUTOVER-mounted-graph-engine-excision.md
Docs/Plans/HANDOFF-CUTOVER-buddy-graph-engine-demolition.md
Docs/Plans/PR-TRACKER-campaign-supergraph.md
Docs/Plans/STEWARDS-ANCHOR-cutover.md
Docs/Design/STATUS-world-graph-continuity-spine.md
Docs/Roadmaps/ROADMAP-campaign-supergraph.md
Docs/Sources/design-agent/ACTIVE_AUTHORITY/PR-TRACKER-campaign-supergraph.md
Docs/Sources/design-agent/ACTIVE_AUTHORITY/ROADMAP-campaign-supergraph.md
Docs/Sources/design-agent/ACTIVE_REFERENCE/STATUS-world-graph-continuity-spine.md
this handoff
```

That sync should record:

```text
D.3A   COMPLETE / MERGED
       PR #665
       accepted head 189ffd50157534d192b2af008c48a76d12ccbc4c
       merge 1a98bdb8a462ecc088ee70c2cecbed5c0d99ac3b
       formal review cycles 3
       final PASS-equivalent 5059851179

D.3B   DOING / active CUTOVER write lease / this implementation PR
D.3    NOT DONE
```

Do **not** pre-mark D.3B `DONE`, invent its future merge/review facts, or mark D.3
complete inside the in-flight implementation PR.

Because D.3B has no dependent D.3 implementation successor, the final D.3B merge facts
and D.3=`DONE` state require a direct guarded steward sync after merge/re-anchor unless
another genuinely dependent CUTOVER implementation has been intentionally created.
Do not open a routine docs-only PR for that sync.

---

## §5 Deletion behavior matrix

| Surface / behavior | D.3B required outcome |
|---|---|
| `graph_memory.kernel*` imports | No executable import remains; package tree absent. |
| `graph_memory.world_supergraph*` imports | No executable import remains; package tree absent. |
| `graph_memory.union_supergraph*` imports | No executable import remains; package tree absent. |
| `integrations.buddy_files*` | No executable import remains; tree absent. |
| `integrations.dungeonmind_kernel*` | No mounted/compat integration remains; tree absent after DELETE/REHOME classification. |
| App import + lifespan | Green through current DungeonMind-only paths. |
| World Graph projection/retrieval | Behavior unchanged from accepted D.3A. |
| Search / object / neighborhood / evidence / source anchor | Behavior unchanged. |
| Graph Review prepare/commit | Governed DungeonMind publication unchanged. |
| Graph Review retry/recovery | Same child; no duplicate revision. |
| Threat publish/retry | DungeonMind authority path unchanged; no Kernel default. |
| Worldbuilding publish/retry | DungeonMind authority path unchanged. |
| First-world D_0 | DungeonMind reviewed initialization unchanged. |
| Hermes graph query | Existing native graph boundary unchanged; do not edit #666 lease merely for deletion. |
| UnionSupergraph preview route | Remains registered 410 with frozen code; old adapter implementation may be gone. |
| Merge-reconciliation routes | Remain registered 410; old file materializer implementation may be gone. |
| World-graph-bootstrap routes | Remain registered 410; old bootstrap implementation may be gone. |
| Authority env unset / `dungeonmind` | DungeonMind behavior unchanged. |
| `buddy_files` / `quiesced` / unknown config | Fail closed; no deleted adapter is reconstructable. |
| alternate `world_root` | Fail closed; cannot select files authority. |
| legacy `<root>/graph_memory/worlds` absent | Still absent before and after mounted workflow proof. |
| local historical user graph files already on disk | Not deleted by product or migration script. |

---

## §6 Required source-absence proof

D.3B needs proof stronger than “our mounted test did not import it.” The source itself
must be gone.

### 6.1 Directory absence

At final executable head assert the following paths do not exist:

```text
src/graph_memory/kernel
src/graph_memory/world_supergraph
src/graph_memory/union_supergraph
apps/live_control_server/integrations/buddy_files
apps/live_control_server/integrations/dungeonmind_kernel
```

If an explicitly approved historical REHOME occurred, prove the old compatibility
tree is absent and identify the exact new non-engine owner in the disposition ledger.

### 6.2 Executable import absence

AST/literal/entrypoint proof across executable source must find zero imports or
dynamic loads of:

```text
graph_memory.kernel
graph_memory.world_supergraph
graph_memory.union_supergraph
apps.live_control_server.integrations.buddy_files
apps.live_control_server.integrations.dungeonmind_kernel
```

Allowed textual hits:

```text
historical docs
comments explaining removed compatibility
sealed reports/evidence
negative tests asserting absence
this handoff / D.3 design history
```

Any executable import hit is a blocker even if its test is currently skipped or the
path is described as “legacy.”

### 6.3 Import behavior after physical deletion

A fresh interpreter should prove deleted namespaces are not importable from the
working tree. This complements—not replaces—the D.3A blocker witness.

Do not add empty tombstone packages that merely raise on use; physical deletion means
those executable package directories are absent.

---

## §7 Required runtime proof after deletion

### 7.1 Retain the D.3A fresh-interpreter witness

The accepted D.3A witness remains the owner for “mounted product does not require the
legacy engine.” Adapt only what is necessary because source packages no longer exist;
do not weaken its behavior matrix.

It must still run in a fresh interpreter with:

```text
legacy import blocker installed before app import
legacy graph filesystem absent before boot
real create_app() / lifespan
retained DungeonMind read/write workflows executed
legacy filesystem absent after workflows
```

Physical deletion should make the blocker redundant in principle, but retaining it
protects against accidental vendored/reintroduced compatibility modules and proves
that D.3B did not weaken D.3A while cleaning tests.

### 7.2 Owning workflow floor

Under the fresh-process proof, retain execution of:

```text
native projection
search / exact object / neighborhood / evidence / source-anchor
source admission
Threat publish + exact retry
worldbuilding publish + exact retry
first-world DungeonMind D_0
Graph Review prepare + commit
Graph Review exact retry
Graph Review fresh-client/lost-response recovery
DungeonMind read-back of authored child
Hermes owning graph-query boundary, unless #666 owns an equivalent current test at
  dispatch time — coordinate rather than edit its active lease
retired 410 routes
```

Required PostgreSQL witnesses must run with **zero required skips**.

### 7.3 Current DungeonMind cohorts

Run the current focused D.2/D.3 regression cohorts appropriate to the final tree,
including at least:

```text
D.2C3 native genesis continuity
D.2C4 Graph Review authoring continuity
D.3A direct DungeonMind read/projection/retrieval coverage
D.3A source admission
D.3A mounted authority selector/fail-closed config
Threat publication/recovery
worldbuilding publication/recovery
first-world initialization
```

When a legacy-only test is deleted, record why it is DELETE rather than silently
shrinking the suite. Surviving product behavior must remain covered at its new owner.

---

## §8 Legacy tests and historical tooling

### 8.1 Test disposition

Tests are executable consumers and must be classified too.

```text
DELETE
  Test exists only to exercise removed Kernel/WorldSupergraph/UnionSupergraph/BuddyFiles
  runtime semantics that are no longer a product capability.

REHOME/REWRITE
  Test contains valuable contract/parity evidence for surviving product behavior.
  Move it to the surviving owner and remove legacy imports.

STOP
  Test exposes a product invariant that has no surviving DungeonMind/Buddy-owned owner.
```

Do not preserve thousands of lines of dead compatibility implementation solely to
keep legacy implementation tests green.

Do not delete a regression test solely because it fails after deletion if the behavior
it protects is still part of the surviving product matrix.

### 8.2 Historical migration/conformance tools

Completed Eldyrwild/CUTOVER producers may be deleted when their authoritative outputs
are already preserved by:

```text
merged Git history
sealed source/evidence artifacts
accepted DungeonMind state
checked-in non-executable reports / design evidence
```

A useful read-only forensic tool may be REHOME only if its operational value is
explicit and it can run without the deleted authority packages.

No historical tool may recreate or mutate the retired Buddy graph authority after
D.3B.

### 8.3 User-data safety

D.3B deletes source code, not user data.

Forbidden without explicit separate approval:

```text
rm / truncate / migrate local graph worlds
modify historical campaign data to fit deletion
rewrite source recaps/evidence artifacts
purge generated artifacts merely because old code produced them
```

Test-database truncation remains allowed only under the existing explicit cutover test
DB guard used by accepted owning witnesses.

---

## §9 Adversarial sequences

| Sequence | Required outcome |
|---|---|
| Delete packages → import real app | App boots; no missing legacy import. |
| Delete packages → run Threat publish | Publishes/retries through DungeonMind; no lazy Kernel import. |
| Delete packages → first-world create | D_0 publishes via DungeonMind; no adoption/Kernel bridge. |
| Delete packages → Graph Review prepare/commit/retry | One DungeonMind child; recovery remains idempotent. |
| Delete `buddy_files` integration → `buddy_files` config | Explicit configuration failure; never import error / silent alias. |
| Alternate world root after deletion | Explicit fail-closed configuration error; no filesystem graph created. |
| Call retired preview/bootstrap/merge routes | Stable registered 410s, not 404/import failure. |
| Fresh process with legacy root absent | Full retained witness passes; no `graph_memory/worlds` created. |
| Import deleted namespace | Fails because source package is absent; no tombstone implementation. |
| Run historical docs/indexing | Textual references remain harmless; no pressure to rewrite history. |
| Discover useful historical executable importing Kernel | DELETE/REHOME/REWRITE/STOP decision recorded before removal. |
| Discover current mounted feature needing Kernel semantics | STOP; do not redesign inside D.3B. |

---

## §10 STOP / split conditions

STOP and report before widening scope if any of the following is true:

1. A mounted/user-facing product path still requires Buddy graph head/revision/store
   semantics.
2. A surviving capability requires a new DungeonMind provider API or schema change.
3. A storage-neutral product contract still exists only inside one of the three engine
   package trees and was not already rehomed by D.3A.
4. Deleting `integrations/dungeonmind_kernel/**` would remove a still-required mounted
   behavior rather than historical tooling.
5. A new third-party dependency is proposed to replace deleted code.
6. The worker needs a path actively leased by #666 or another parallel PR.
7. Physical deletion would change a public API/wire contract rather than merely remove
   unreachable implementation.
8. The D.3A fresh-interpreter witness must be weakened, skipped, or converted to
   import-only assertions to get green.
9. Required PostgreSQL witnesses cannot run with zero required skips.
10. Any proposed cleanup deletes local/user campaign data.

A STOP is useful evidence. It means the “D.3A made D.3B boring” hypothesis found a real
exception that should be understood explicitly.

---

## §11 Suggested implementation sequence / nano-commit story

Keep deletion reviewable. Suggested semantic commits:

```text
1. sync merged D.3A predecessor state + freeze D.3B executable-consumer ledger
2. retire remaining product-side Kernel/BuddyFiles compatibility hooks
3. classify/delete or minimally rehome historical executable consumers
4. delete buddy_files + dungeonmind_kernel compatibility integrations
5. delete graph_memory.kernel / world_supergraph / union_supergraph package trees
6. remove legacy-only tests/entrypoints and retarget surviving contract tests
7. add/finalize source-absence + executable-import-absence proof
8. rerun D.3A mounted witness + DungeonMind regression floor
9. final docs/state handback only; do not pre-mark D.3B or D.3 DONE
```

The exact commit count may differ. Keep each commit semantically understandable.

Do not mix broad formatting/refactoring with deletion.

---

## §12 Verification matrix

The worker must return exact commands and exact result counts/provenance.

### Required evidence families

| Evidence | Requirement |
|---|---|
| Step-0 executable-consumer ledger | Every executable legacy hit classified DELETE/REHOME/REWRITE/STOP. |
| Primary source absence | Five target trees absent. |
| Executable import absence | Zero executable imports/dynamic loads of retired namespaces/integrations. |
| D.3A fresh-interpreter mounted witness | Green after physical deletion. |
| Legacy filesystem absence | Absent before/after full mounted proof. |
| Native read/projection/retrieval | Green. |
| D.2C3 genesis | Green. |
| D.2C4 Graph Review publish/retry/recovery | Green. |
| Threat publish/retry | Green without Kernel default. |
| Worldbuilding publish/retry | Green. |
| First-world D_0 | Green. |
| Source admission | Green. |
| Authority selector/config | DungeonMind-only; stale legacy modes fail closed. |
| Retired 410 routes | Still registered with frozen codes. |
| Frontend retirement states | Still truthful; no resurrected legacy action. |
| Ruff / static | Clean on touched Python. |
| `git diff --check` | Clean final head. |
| dependency immutability | DungeonMind pin unchanged unless STOP/split approved. |
| required PG skips | **0**. |
| CI | Record actual presence/absence; do not imply CI if none exists. |
| manual dogfood | Record separately; never relabel as automated evidence. |

### Test deletion accounting

The handback must report:

```text
legacy tests deleted: N
  each grouped by deleted capability / disposition
surviving tests rewritten/rehomed: N
new absence tests: N
required PG skipped: 0
```

Counts need not be targets; they are evidence that suite shrinkage was intentional.

### Provenance vocabulary

Use exactly:

```text
author-local
reviewer-independent rerun
CI
manual/operator dogfood
BLOCKED_DEPENDENCY
NOT_RUN
```

Do not call author-local execution independent verification.

---

## §13 Final D.3 evidence contract

At the accepted D.3B executable head, reviewers must be able to verify:

```text
legacy source package directories absent
buddy_files integration absent
dungeonmind_kernel compatibility integration absent
zero executable imports of retired namespaces/integrations
production import-blocker/fresh-process witness still green
legacy graph filesystem absence still green
current DungeonMind read/write cohorts green
D.2C3 native genesis green
D.2C4 manual Graph Review authoring/recovery green
Threat/worldbuilding/first-world publication green
no product selector can recreate Buddy graph ownership
no user-data cleanup performed
DungeonMind pin unchanged (unless separately approved split)
D.3B package deletion is the only semantic capability in the PR
```

Only after D.3B merges and this evidence is accepted may repository authority say:

```text
D.3 Buddy graph-engine demolition DONE
```

The implementation PR itself remains:

```text
D.3A COMPLETE / MERGED
D.3B DOING
D.3 NOT DONE
```

Final completion facts become knowable only after merge.

---

## §14 CODE → REVIEW handback contract

Return one cumulative checked-in handback containing:

1. PR / branch / exact final PR head SHA.
2. Exact implementation/executable tip if the final head is docs-only.
3. Exact dispatch base containing this handoff and any later main rebase/merge.
4. D.3A predecessor facts: #665 accepted head, merge SHA, 3 cycles, final review ID.
5. Current DungeonMind pin and proof it did/did not move.
6. Active PR/write-lease recheck and any #666 serialization/rebase facts.
7. Full Step-0 executable-consumer ledger with DELETE/REHOME/REWRITE/STOP for every
   retired namespace/integration consumer.
8. Exact paths deleted from the five primary trees.
9. Exact historical tools deleted.
10. Exact historical tools rehomed, with new owner and parity evidence.
11. Exact surviving product consumers rewritten, with proof behavior did not change.
12. Source-directory absence proof.
13. Executable-import/dynamic-load absence proof.
14. Packaging/entrypoint absence proof.
15. D.3A fresh-interpreter witness result after deletion.
16. Legacy graph filesystem absence result before/after witness.
17. Native projection/retrieval result.
18. D.2C3 native genesis result.
19. D.2C4 source-admission + Graph Review prepare/commit/retry/recovery result.
20. Threat publication/retry result.
21. Worldbuilding publication/retry result.
22. First-world D_0 result.
23. Hermes/native graph-query result or explicit parallel-owner evidence if #666 owns
    the final equivalent boundary.
24. Frozen retired-route 410 results.
25. Authority config/factory fail-closed matrix.
26. Legacy-test deletion accounting and surviving-test relocation accounting.
27. Exact test/build/lint/static commands with pass/fail/skip counts.
28. Required PostgreSQL skip count — must be 0.
29. Ruff + `git diff --check`.
30. Dependency/pin/lockfile result.
31. State-authority mirror equality result.
32. Verification provenance table.
33. Confirmation that no user/local data cleanup ran.
34. Confirmation D.3A is synced COMPLETE/MERGED while D.3B remains DOING and D.3
    remains NOT DONE in the in-flight PR.
35. Stop conditions encountered or `none`.

If a final docs-only commit records the handback after all executable verification:
identify the exact executable tip. Do not rerun unrelated expensive executable gates
solely because the final delta is handback/state documentation; final-head-sensitive
`git diff --check`, mirror equality, source-absence, and executable-import/static
checks still apply to the final PR head.

---

## §15 Reviewer checklist

Review D.3B against these questions, in order:

1. **Was deletion earned?** Is D.3A #665 actually merged and is this branch based on
   current main containing its accepted implementation?
2. **Was every executable consumer classified before deletion?** No unowned imports,
   dynamic loads, packaging hooks, or “legacy but executable” exceptions.
3. **Are the retired packages physically absent?** Not tombstoned, renamed, vendored,
   or hidden under a new compatibility namespace.
4. **Did compatibility adapters disappear too?** `buddy_files` and the historical
   `dungeonmind_kernel` integration are not backdoors.
5. **Did storage-neutral current contracts survive under honest owners?** No product
   semantics were deleted just because an old package happened to own them.
6. **Did any REHOME preserve a whole engine subtree?** If yes, reject. Rehome must be
   minimal, explicit, and non-authoritative.
7. **Does the mounted product still pass D.3A's fresh-process proof?** Actual workflows,
   not route registration/import-only evidence.
8. **Do D.2C3/D.2C4 writes still work?** Native D_0 and manual Graph Review publication
   are non-negotiable survivors.
9. **Did Threat/worldbuilding/first-world paths lose latent Kernel defaults?** No
   deleted-package import can be triggered by a current product path.
10. **Do retired routes fail truthfully?** Stable 410s remain instead of turning into
    404s/import crashes.
11. **Is the old graph filesystem still absent?** No cleanup accidentally recreated a
    local authority/cache.
12. **Was suite shrinkage intentional?** Every deleted legacy test has a disposition;
    surviving behavior has a current owner.
13. **Was user data untouched?** Source deletion only.
14. **Is state sync truthful?** #665 complete, D.3B active, D.3 not done yet.
15. **Would merging this PR make the phrase “Buddy graph engine” historical rather
    than executable?** If not, D.3B is incomplete.

---

## §16 Definition of completion after merge

D.3B implementation acceptance is not itself the final state-authority sync.

After the PR is formally PASS-equivalent and merged:

1. re-anchor current `main` and exact merge SHA;
2. verify no successor implementation needs to carry the backward-looking completion
   facts;
3. directly and atomically sync the mutable CUTOVER state authorities because D.3B is
   the final D.3 slice;
4. record exact D.3B accepted head, merge SHA, formal review-cycle count, and final
   review ID;
5. mark D.3B `COMPLETE / MERGED`;
6. mark **D.3 Buddy graph-engine demolition `DONE`** only if final source/runtime
   absence proof remains accepted;
7. do not rewrite historical architecture/design evidence to pretend the old engine
   never existed.

At that point the migration-specific invariant becomes simple:

```text
one durable World Graph identity
one runtime World Graph authority: DungeonMind
one publication lineage
one provenance model
no executable Buddy graph engine
```

That is the exit from CUTOVER's graph-authority demolition phase.
