---
pr_body_template: |
  ## Handoff pointer
  - Workstream: APP-STATE / AS0 — Application State architecture + migration gate
  - Flow: APP-STATE
  - Direction: DESIGN → REVIEW
  - Handoff: Docs/Plans/HANDOFF-APP-STATE-application-state-architecture.md
  - Implementation repository: Drakosfire/DungeonMindBuddy

  ## Verification pointer
  - Design authority base: 31f2885cc18f96b98a1028304ae98914d1139fa3 (CUTOVER #634 merge)
  - Dispatch: branch from fresh current main containing this handoff; re-anchor if main advances materially
  - Output: architecture authority + migration roadmap + AS1 implementation handoff
  - Production code: none

  The checked-in handoff, cumulative diff, and exact-head formal review are the
  review contract. This body is transport metadata.
---

# HANDOFF — AS0: define the Buddy Application State architecture and migration contract

**Created:** 2026-08-24
**Status:** ARCHIVED — completed by PR #636 merge `4c90df353bfb5d0f6857357e00eb8b2b6e142257`; successor AS0.1 PR #639 merge `dd09f7f707e38f9f4348b759da8cfdbbe420fd60`; AS1 is the active implementation slice
**Canonical handoff path:** `Docs/Plans/HANDOFF-APP-STATE-application-state-architecture.md`
**Conversation/workstream:** `APP-STATE`
**Flow / owner:** `APP-STATE`
**Direction:** DESIGN → REVIEW
**Design authority base:** `31f2885cc18f96b98a1028304ae98914d1139fa3` (merge of CUTOVER PR #634)
**Dispatch base rule:** branch from fresh current `main` containing this handoff; if `main` advances after dispatch, use steward preflight and stop only when the advance materially changes AS0 authority, write lease, or evidence.
**Suggested branch:** `agent/app-state-application-state-architecture`
**Suggested PR title:** `APP-STATE: define application-state architecture and migration contract`

> Repository law: [`AGENTS.md`](../../AGENTS.md). Steward process: [`Docs/Process/STEWARD-CYCLE.md`](../Process/STEWARD-CYCLE.md). Parent pickup authority: [`STEWARDS-ANCHOR-application-state.md`](STEWARDS-ANCHOR-application-state.md).

---

## §1 Mission and merge-ready invariant

**Mission:** Define and formally review the durable architecture and migration contract for a Buddy-owned PostgreSQL Application State Layer so future surface migrations—beginning with Play/Playable—can be implemented without guessing persistence ownership, revision semantics, transaction boundaries, failure behavior, migration/cutover rules, runtime isolation, or performance acceptance.

**Merge-ready invariant:**

> **One reviewed architecture assigns Buddy-owned durable application state to explicit domain authorities over one shared transactional PostgreSQL substrate, freezes the cross-surface persistence/revision/transaction/migration rules required for implementation, preserves DungeonMind as sole World Graph authority, and emits one bounded AS1 implementation handoff whose independently useful consumer and owning-boundary proof are concrete.**

AS0 is successful only if the next implementation worker can execute AS1 without making a new architecture decision about the database lifecycle, migration owner, repository/transaction seam, WorkObject revision semantics, database isolation, or failure/fallback posture.

### Pre-dispatch critique

| Question | Answer |
|---|---|
| Can one invariant govern every claimed observable path? | Yes, because this slice changes design authority only: one persistence architecture must govern every later Buddy-owned state migration while preserving domain ownership. |
| Most likely adversarial sequence | The design becomes a generic SQL abstraction, then Play/Combat/Plan must reconstruct their invariants in callers; or the design optimizes Play only and creates a second bespoke persistence stack. |
| Second likely failure | The design says "Postgres" without freezing deployment/config, migration ownership, transaction/revision semantics, worktree isolation, exact cutover/deletion rules, or unavailable behavior—leaving AS1 to guess. |
| Easiest owning boundary to under-review | Existing persistence reality: registry+Markdown snapshots, Play Run/manifest/rebase coordination, browser/local state, Combat state, and server startup/config may be incompletely inventoried. |
| Fact that forces stop/split | A material target requires production code or a new product/domain semantic contract to resolve. AS0 may design it, but must not implement it. A newly discovered authority that cannot fit the shared substrate without changing its domain contract must be recorded as a successor/reconnaissance question rather than silently absorbed. |

---

## §2 Context, authority, and lane

| Field | Required content |
|---|---|
| Parent authority | `Docs/Plans/STEWARDS-ANCHOR-application-state.md` |
| Repository law | `AGENTS.md` + `Docs/Process/STEWARD-CYCLE.md` |
| Design authority base | `31f2885cc18f96b98a1028304ae98914d1139fa3` |
| Dispatch base | Fresh current `main` containing this checked-in handoff. Do not fork from the historical design-authority base if later non-conflicting commits are already on main. |
| Play predecessor | BF1 / PR #628 merged at `b850b9f8126a8c8488d17b3bdb6f99a60a162338`; Beat-first grammar + v2 manifest foundation are predecessor truth. |
| World authority predecessor | CUTOVER through PR #634. Production reads are native DungeonMind and the normal governed write context no longer requires Buddy graph hydration. DungeonMind remains living World Graph authority. APP-STATE must not create a Buddy World-data store or couple its implementation to CUTOVER D.2/D.3 demolition. |
| Exact input consumed | Current repository persistence implementations and routes/services, existing Play/Playable architecture/design authorities, CON-READY user stories, current server/dependency/runtime configuration. |
| Named successor | AS1 — `HANDOFF-APP-STATE-postgres-foundation.md`, authored by this PR and only dispatchable after AS0 PASS/merge/re-anchor. |
| What remains false | No PostgreSQL application-state tables, migrations, runtime wiring, data migration, Play cutover, or filesystem demolition exist after AS0. Play remains on current persistence until implementation slices land. |
| Branch / isolated checkout | `agent/app-state-application-state-architecture` in an isolated worktree/checkout. |
| Parallel lanes / collision hotspots | No open Buddy PRs at the steward re-anchor after #634. Re-check before work. CUTOVER D.2/D.3 may resume; root DB config, dependency pins, server bootstrap, Docker/dev lifecycle, and central state-authority docs are future collision hotspots but are read-only in AS0. |
| Runtime/state ownership | None. This is design-only; do not mutate live/test databases, `out/`, workspace documents, Play Runs, Combat state, or DungeonMind authority. |
| Backward state-authority sync | None beyond the design artifacts themselves. The steward seed is already current. AS1 will carry backward-looking sync for the accepted AS0 merge/review truth. |

### Authority precedence after AS0

The architecture PR must make this ownership boundary explicit:

```text
ARCHITECTURE-application-state-layer
  owns:
    Buddy persistence substrate
    durable work/revision lifecycle
    transaction/repository boundary
    schema migration/deployment rules
    application-state cutover/demolition rules
    DB failure/isolation/backup posture

ARCHITECTURE-playable-material-and-runtime
DESIGN-play-current-moment-cockpit
DESIGN-playable-authoring-and-adoption
  continue to own:
    Playable vs Runtime meaning
    Beat / Scene / Decision / Option semantics
    Run behavior
    relevance semantics
    product interaction semantics

DungeonMind / Campaign Supergraph authorities
  continue to own:
    World Graph identity, durable World truth, graph reads/writes,
    contribution/correction/publication authority
```

AS0 may state which prior persistence assumptions are superseded by the new target architecture. It must not redesign Play domain semantics merely because their storage changes.

---

## §3 Observable design paths and required current-state inventory

AS0 must ground the architecture in the implementation that actually exists on the exact dispatch base. Do not design only from filenames in the steward seed.

### 3.1 Required persistence inventory

Produce an architecture section or appendix covering at least:

| Durable/product state | Current owner | Current authority representation | Real consumers | Current concurrency/recovery | Target disposition |
|---|---|---|---|---|---|
| Workspace/Plan/Runbook document metadata | Buddy content/authoring | registry JSON | Plan/Build/Play/authoring routes as applicable | registry CAS + locks | decide shared WorkObject posture |
| Workspace document bytes | Buddy content/authoring | Markdown target files | editor/Plan/Build/Play/Hermes as applicable | document lock + digest/fingerprint | decide revision/working-copy posture |
| Play Run | Play Runtime | per-Run JSON | Play routes/surface | file lock + `run_revision` CAS | transactional Play aggregate |
| Play Run manifest | Play integrity | sidecar JSON | Run admission/rebase/Play | coordinated file writes | immutable/transactional representation |
| Play active Run | Play continuity | JSON pointer | Play entry | file lock | scoped durable pointer |
| Play rebase recovery | Play Runtime | intent JSON | Play rebase/read/list | forward-recovery protocol | eliminate if one DB transaction owns commit |
| Combat runtime | Combat | inspect exact current implementation | Combat + Play link | inspect exact current behavior | future Combat-owned schema, not Play progress |
| Browser/local-only durable state relied on by product | owning domain | inspect exact keys/consumers | affected surfaces | browser semantics | migrate only when product correctness depends on it |
| Source/artifact bytes and metadata | Source/asset owner | inspect | surfaces/Hermes | inspect | distinguish relational metadata from large immutable blobs |

The inventory is evidence, not a commitment to one table per row.

### 3.2 Required call-path tracing

Trace enough current routes/services to prove where authority actually crosses persistence boundaries. At minimum:

```text
workspace document create/load/save
Plan/Runbook committed revision load
Play Run create/list/get/progress replace
Run reference-manifest seal/load
active Run get/set
Run rebase prepare/commit/recovery
Play entry/resume path
Combat current persistence boundary
```

The final architecture should be able to point from each later migration target to a current authority owner and a target repository/transaction owner.

### 3.3 Existing PostgreSQL/dependency posture

Current `pyproject.toml` receives PostgreSQL dependencies through `dungeonmind[postgres]`. AS0 must decide whether Buddy Application State deliberately owns its own direct PostgreSQL dependency/configuration contract rather than accidentally depending on DungeonMind's extra for driver availability.

Do not edit `pyproject.toml` in AS0. Freeze the intended AS1 dependency/config decision in architecture and handoff.

---

## §4 Files in scope — exclusive write lease

This is a steward-designated design/architecture PR. Production code is out of scope.

| Action | Path | Purpose |
|---|---|---|
| Create | `Docs/Design/ARCHITECTURE-application-state-layer.md` | Canonical cross-surface persistence architecture authority. |
| Create | `Docs/Roadmaps/ROADMAP-application-state.md` | Sequencing authority for AS1+ migration slices and product/quality gates. |
| Create | `Docs/Plans/HANDOFF-APP-STATE-postgres-foundation.md` | One bounded implementation handoff for the first independently useful substrate capability. |

**Bounded discovery exception:** none for writes.

Repository code, current design authorities, roadmaps, reports, and historical handoffs may be read freely for grounding. Any discovered need to modify another path is a stop report to the steward. Do not widen the PR because a related document could be cleaned up.

The current handoff (`HANDOFF-APP-STATE-application-state-architecture.md`) is dispatch authority and is read-only to the design worker. If current repository truth materially invalidates its scope, stop and request steward amendment rather than self-editing the lease.

---

## §5 Explicitly out of scope / collision boundary

| Path / concern | Why AS0 must not touch or claim it |
|---|---|
| `pyproject.toml`, `uv.lock` | AS1 implementation/dependency ownership. AS0 freezes the decision only. |
| application/server Python or TS/React code | No production implementation in architecture gate. |
| SQL migration files/directories | AS1. AS0 defines migration framework/ownership and naming. |
| Docker/compose/service configuration | AS1 or dedicated lifecycle slice after architecture decision. |
| `out/**` | Current state is evidence only; no migration/mutation. |
| DungeonMind repository/schema | Separate World authority. APP-STATE must consume stable public references, not modify DungeonMind storage. |
| CUTOVER D.2/D.3 implementation | Separate graph-runtime retirement line. Shared dependency/config paths must be serialized if later implementation leases overlap. |
| Play BF2/BF3 semantics | PLAY-SURFACE successor. AS0 may sequence them after persistence, not redesign current Beat/Scene/Decision contracts. |
| Combat domain schema details | Future Combat-owned migration. AS0 freezes boundary/primitives only. |
| Event sourcing | Not justified. Current-state authority remains default. Mutation history is a later independent capability if proven useful. |
| Universal "everything JSONB" object store | Explicitly rejected by parent steward authority. |
| Large binary blob migration | AS0 defines policy/ownership only; no asset byte migration. |

---

## §6 Architecture contract the PR must freeze

The design PR must answer the parent anchor's eighteen questions and resolve them into one coherent contract rather than an open-question list.

### 6.1 Authority and deployment

Freeze:

1. exact boundary between DungeonMind World authority and Buddy application state;
2. Buddy database logical ownership: same PostgreSQL server is allowed, but authority must not depend on co-location;
3. database/schema naming posture and whether Buddy owns one DB with domain schemas or another equivalent boundary;
4. application-state configuration contract for local, test, and production-like use;
5. startup/unavailable behavior: database unavailable must fail truthfully; no stale file fallback after a domain switches.

### 6.2 Migration framework and schema ownership

Freeze:

- what migration framework/tool owns Buddy schema evolution;
- where migrations live;
- how migration ordering/version is recorded;
- which code owns connection/session/transaction lifecycle;
- how schema creation/upgrade happens in local/dev/test versus application startup;
- whether automatic production schema mutation at ordinary app boot is allowed or prohibited;
- rollback/restore expectations for a personal/local deployment.

The contract must avoid both extremes:

```text
"every repository manages its own connection/migrations"
```

and

```text
"one god service knows every domain's invariants"
```

### 6.3 Shared primitives versus domain-owned models

Explicitly accept/revise/reject the candidate:

```text
WorkObject
WorkRevision (immutable committed revision)
WorkingCopy (recoverable mutable draft)
```

If accepted/revised, freeze at least:

- stable identity;
- kind/owner semantics without turning `kind` into a universal ontology;
- campaign/world scope fields and their optionality;
- committed revision identity/version rules;
- canonical content representation and digest semantics;
- immutable historical revision retention;
- current-revision pointer behavior;
- working-copy base revision/CAS semantics;
- explicit Save/commit meaning;
- discard/archive semantics;
- metadata versioning behavior;
- whether a Run may pin historical revision N after revision N+1 exists (target answer should be yes unless evidence disproves it).

Do not require every future surface to use WorkObject. State the admission criteria for using the shared primitive.

### 6.4 Play target transaction model

Freeze enough target semantics to make later AS2/AS3 design non-speculative:

```text
Playable committed revision
→ Run creation + sealed manifest
→ mutable Run CAS
→ active Run selection
→ preserve-only rebase/migration where supported
```

At minimum decide:

- Run aggregate relational columns versus JSONB posture;
- `run_revision` CAS commit rule and no-op/replay behavior;
- manifest immutability/versioning and Run binding;
- transaction boundary for new Run + required manifest;
- transaction boundary for rebase;
- whether durable rebase intent disappears once one transaction owns all state (expected: yes unless a concrete external side effect remains);
- active-Run scope/identity model sufficient for current single-operator product without over-designing accounts;
- whether run mutation/audit history is excluded from AS1 and later separately justified.

Do not reopen Beat-first manifest semantics; map them onto storage.

### 6.5 Cross-authority references

Freeze the rule that Buddy application tables reference World/Source/Mechanics/Combat authorities through stable public identities and service contracts rather than accidental storage coupling.

Specifically address:

- no SQL FK into DungeonMind World Graph tables;
- World revision/object reference posture where exact pinning matters;
- Source/asset references and large-byte storage policy;
- exact mechanics reference posture;
- Play→Combat runtime reference posture while Combat owns HP/initiative/conditions.

### 6.6 Existing-state migration and cutover

Define a standard migration lifecycle applicable to each domain migration:

```text
inventory exact old authority
→ quiesce or establish CAS-safe capture boundary
→ import exact identity/revision/content/state
→ verify counts + identity + digests + semantic invariants
→ exercise new read/write path
→ switch authority
→ old writes fail closed
→ dogfood/reload proof
→ delete replacement path
```

Freeze:

- idempotency/retry behavior;
- how already-imported versus conflicting rows are distinguished;
- no silent "new ID" remapping of durable identities;
- how historical Playable revisions are handled when the current filesystem never stored them;
- whether absence of historical bytes is represented honestly rather than fabricated;
- fallback allowed before authority switch versus prohibited after switch;
- demolition criteria per migrated domain.

### 6.7 Parallel-agent and test database isolation

This is mandatory because source isolation is not runtime isolation.

Freeze a concrete policy for:

- per-test ephemeral DB/schema/database;
- parallel pytest runs;
- two worktrees/agents running migrations simultaneously;
- local developer database naming;
- destructive test/migration guards;
- never pointing default tests at the living DungeonMind authority DB or a shared Buddy product DB;
- cleanup ownership.

The AS1 handoff must name exact runtime isolation derived from this contract.

### 6.8 Backup, restore, portability

Define a proportionate personal-project posture:

- what must be backed up;
- whether standard PostgreSQL dump/restore is the first supported mechanism;
- how external immutable blobs participate if used;
- what identity/integrity is verified after restore;
- what is intentionally not a high-availability requirement.

Avoid enterprise ceremony that does not serve the project, but do not leave "database is durable" as the entire disaster-recovery story.

### 6.9 Speed and "pop" acceptance

The architecture must make product performance a migration invariant, not a later polish concern.

Freeze a measurement vocabulary:

```text
owning-boundary DB/service latency
end-to-end surface latency
orientation/recovery time
interaction depth
software-caused interruption
external-tool abandonment
```

For the first Play migrations, propose explicit **hypothesis budgets** for at least:

- load active Run + pinned Playable revision;
- Runtime CAS mutation;
- Save/commit a typical Runbook revision;
- Start Run + derive/seal manifest;
- Resume Play → current moment usable;
- reload/restart → exact current moment restored.

Do not present invented numbers as measured baselines. Mark them as proposed targets and require AS1/AS2/AS3 to capture real baseline/head measurements at their owning boundaries.

The architecture must preserve the broader product definition:

> **Persistence is successful only when durability improves without making the GM administer the software or wait long enough to leave the table moment.**

### 6.10 AS1 must be independently useful

The design must select the smallest first implementation consumer that proves the substrate is real.

Possible candidates include:

- one real WorkObject/revision flow on PostgreSQL;
- a narrow admitted existing workspace-document kind;
- another bounded consumer discovered from current code.

A PR that only creates connection helpers + empty migrations + unused tables is **not independently useful** and must not be the AS1 handoff unless the design proves why that infrastructure itself has an observable required consumer in the same slice.

AS1 should be small enough to review deeply and strong enough that a successful merge proves:

```text
real domain state
→ domain service
→ shared transaction/repository seam
→ PostgreSQL
→ reload/retry/concurrency proof
```

---

## §7 Required evidence to merge AS0

AS0 is design work, so evidence is repository-grounded architecture completeness rather than production tests.

| Guarantee / invariant clause | Owning boundary | Evidence class | Required proof | Merge blocker |
|---|---|---|---|---|
| Current persistence inventory is truthful | Current routes/services/stores | repository audit | Architecture maps each claimed authority to concrete current code/path and consumers | Material durable state omitted or authority guessed from filename alone |
| Shared substrate does not collapse domains | Architecture | contract review | Explicit ownership table/matrix covering Content/Playable/Play/Combat/World/Source/Mechanics | Generic object/blob store or Play semantics leak into shared layer |
| DungeonMind boundary preserved | Cross-repo authority contract | architecture review | No Buddy table owns World truth; no storage-level FK/coupling required | APP-STATE becomes second World authority |
| Historical revision problem is solved | Content/Playable contract | design scenario | R17-pinned Run remains openable after R18 commit without reading current bytes as R17 | Design still requires "current file equals bound Run" |
| Multi-file transaction debt has a target deletion path | Play persistence contract | adversarial design trace | Run create/seal and rebase show one DB transaction boundary and name obsolete file intents/locks | Permanent intent-file protocol retained without external transaction reason |
| Failure is truthful | DB/service boundary | state/fallback matrix | DB unavailable after switch never reads stale old file authority | Permanent fallback or toggle with split authority |
| Existing-state migration is exact and bounded | Migration contract | replay/idempotency matrix | Same old state replays safely; conflict fails closed; IDs/revisions/digests not silently remapped | "Best effort" import or fabricated historical state |
| Parallel work is isolated | Test/runtime contract | concurrency design | Exact per-test/worktree DB isolation and destructive guards are named | Agents/tests can collide in one default mutable DB |
| Speed/pop are first-class | Product quality contract | metric ledger | Proposed target budgets + explicit baseline capture requirements, clearly distinguished | Correctness-only migration acceptance |
| AS1 is dispatchable | Successor handoff | handoff review | Exact §1 invariant, write lease, DB isolation, migrations, PostgreSQL owning-boundary tests, performance proof | AS1 still asks implementation agent to decide architecture |

### Required repository review inputs

At minimum inspect fresh current versions of:

```text
AGENTS.md
Docs/Process/STEWARD-CYCLE.md
Docs/Plans/STEWARDS-ANCHOR-application-state.md
Docs/Plans/STEWARDS-ANCHOR-cutover.md
Docs/Plans/STEWARDS-ANCHOR-con-ready.md
Docs/Design/ARCHITECTURE-playable-material-and-runtime.md
Docs/Design/DESIGN-play-current-moment-cockpit.md
Docs/Design/DESIGN-playable-authoring-and-adoption.md

pyproject.toml
apps/live_control_server/config.py
apps/live_control_server/services/workspace_document_registry.py
apps/live_control_server/services/tiptap_markdown_write.py
apps/live_control_server/routes/workspace_documents.py
apps/live_control_server/services/play_run_registry.py
apps/live_control_server/services/play_run_reference_manifest.py
apps/live_control_server/services/play_active_run.py
apps/live_control_server/services/play_run_rebase.py
apps/live_control_server/routes/play_runs.py
apps/live_control_server/services/registry_file_lock.py
src/live_play/live_store.py
```

Use repository search/call tracing to discover additional current persistence consumers. Do not treat this list as complete.

### Design verification

Before requesting review:

```bash
# Repository law / handoff mechanical preflight
uv run python scripts/steward_preflight.py \
  --handoff Docs/Plans/HANDOFF-APP-STATE-application-state-architecture.md

# No production-code expansion; compare from actual dispatch base recorded by worker
# after branching from current main.
git diff --name-only <DISPATCH_BASE>...HEAD

git diff --check
```

Expected changed paths are exactly the three §4 outputs.

No test suite is required merely for documentation. If the design worker adds executable tooling to prove something, that is scope expansion and requires a split/new implementation handoff.

---

## §8 Required output shape

### 8.1 `ARCHITECTURE-application-state-layer.md`

Must contain at least:

1. purpose/scope/non-goals;
2. authority diagram and ownership matrix;
3. current-state persistence inventory;
4. logical deployment/configuration contract;
5. migration/schema ownership;
6. domain-service/repository/transaction layering;
7. accepted shared primitives and admission criteria;
8. WorkObject/revision/working-copy contract or reviewed replacement;
9. Play target transaction model;
10. cross-authority reference rules;
11. failure/fallback matrix;
12. migration/idempotency/cutover/demolition contract;
13. test/worktree/database isolation contract;
14. backup/restore posture;
15. speed/pop measurement contract;
16. explicit relationship to existing Play/CUTOVER/CON-READY authorities;
17. rejected alternatives and why;
18. known future decisions deliberately deferred.

### 8.2 `ROADMAP-application-state.md`

Must be capability-sequenced rather than table/layer-sequenced.

For each planned slice record:

```text
status
independently useful outcome
primary consumer/story
predecessor
durable/public contract introduced
runtime/database collision boundary
required product + owning-boundary evidence
what remains false
```

Re-evaluate the seed AS0→AS7 hypothesis. Do not preserve it for ceremony if current code supports a better decomposition.

### 8.3 `HANDOFF-APP-STATE-postgres-foundation.md`

Must satisfy the normal implementation handoff template and freeze:

- exact accepted architecture authority;
- one independently useful consumer;
- exact base expectation after AS0 merge/re-anchor (do not invent future merge SHA in the design PR; express predecessor binding correctly);
- exact write lease with bounded discovery only where justified;
- PostgreSQL dependency/config/migration files;
- DB/runtime isolation across tests/worktrees;
- transaction/CAS/failure behavior;
- actual PostgreSQL owning-boundary integration proof;
- baseline/head performance measurement;
- backward-looking state-authority sync set for AS0 completion;
- named AS2 successor and explicit remaining falsehood.

---

## §9 Required review handback

Record for each formal review cycle:

1. `Review Cycle <N>` and exact PR/branch/head SHA;
2. §1 invariant disposition;
3. actual changed paths vs §4;
4. persistence inventory gaps found during review;
5. architecture questions from §6 still unresolved or contradictory;
6. rejected/accepted alternatives materially affecting later implementation;
7. whether AS1 is truly dispatchable without architectural guessing;
8. state-authority conflicts with Play/CUTOVER/CON-READY (`none` or exact conflict);
9. prior finding ledger on re-review;
10. final disposition: `PASS` or `REQUEST-CHANGES-equivalent`.

A formal PASS should make no claim that PostgreSQL application-state implementation exists. It means the architecture is sufficient to dispatch the first bounded implementation capability.

---

## §10 Acceptance rubric

AS0 may merge only when all are true:

- [ ] Exactly the three §4 design artifacts changed.
- [ ] Current durable Buddy persistence has been inventoried from real code/call paths, including Play and the shared workspace-document substrate.
- [ ] The architecture clearly separates Buddy application state from DungeonMind World authority.
- [ ] Shared substrate primitives are explicit and domain admission criteria prevent a generic JSON-object architecture.
- [ ] WorkObject/revision/working-copy semantics are accepted/revised/rejected with historical-revision and CAS behavior fully resolved.
- [ ] Play Run + manifest + Runtime transaction posture is concrete enough for later migration without redesign.
- [ ] Existing-state migration, switch, no-fallback-after-cutover, and demolition rules are explicit.
- [ ] Database/test/worktree isolation is concrete.
- [ ] Dependency/config/migration ownership is concrete.
- [ ] Backup/restore posture is proportionate and explicit.
- [ ] Performance and perceived-leverage metrics are part of migration acceptance; proposed numbers are labeled hypotheses until measured.
- [ ] The roadmap is capability-sequenced and names what remains false after each slice.
- [ ] AS1 has one independently useful real consumer and a normal implementation handoff with exact PostgreSQL owning-boundary evidence.
- [ ] BF2/BF3 remain intentionally paused from deepening the file-backed Play Runtime until APP-STATE persistence direction is implemented or the steward explicitly re-sequences them.
- [ ] No production code, SQL migrations, dependency pins, runtime state, or database contents changed in AS0.

---

## §11 Stop conditions

Stop and return to the steward instead of widening AS0 when:

- resolving the architecture requires modifying production code or running a destructive migration;
- a newly discovered domain authority cannot be represented without changing its product semantics;
- current CUTOVER work resumes with an overlapping write lease on documents AS0 is required to change;
- the design requires Buddy to read/write DungeonMind internal tables directly;
- the only way to make AS1 "useful" is to bundle multiple independently useful domain migrations;
- the proposed shared primitive becomes a generic arbitrary JSON store;
- the design cannot state which old persistence authority is deleted after a successful migration;
- database isolation across parallel agents/tests remains hand-wavy;
- performance acceptance remains "should be fast" rather than measurable;
- AS1 still contains unresolved architecture choices that belong in AS0.

---

## Closing thesis

The architecture gate should leave the repository with a simple, durable direction:

> **DungeonBuddy owns one transactional application-state substrate, not one universal domain model. Surfaces operate through domain services; PostgreSQL owns durable Buddy application state; DungeonMind owns World truth; migrations end by deleting the replaced file authority; and Play is the first proving ground because it makes durability, concurrency, revision history, and table-speed failures impossible to hide.**
