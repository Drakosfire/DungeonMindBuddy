# HANDOFF — DEMO-J3 / V6.4 / CON-READY PLAY-2: persistent vNext authority composition

**Status:** COMPLETE / HISTORICAL — Buddy #779 merged 2026-09-27 at `2ccc96ff2a7d76328578609d5289fd3babcf6442`
**Execution owner:** `Drakosfire/DungeonMindBuddy` (Buddy composition proof)
**Roadmap owner:** Buddy `Docs/Roadmaps/ROADMAP-demo.md`, milestone DEMO-J3
**Kernel context:** DungeonMind V6 consumer/domain phase; V6.4 is this proof label, not a Kernel runtime cutover
**Design-time Buddy main:** `397e60791f938a4662f134dbf8e11538f61cb51d`
**Design-time DungeonMind main:** `4d11686d679029ae4ef0902a13edc0509c0ce476`
**Design-time WorldKeeper main:** `662a028fb1882719c4c3e192134a1a6b7a58026c`
**Installed Buddy runtime pins:** DungeonMind `0f709d76fdc53bac9c9258d1751463ae2c76ca71`; WorldKeeper `49a8620f066ce7ef8972a699020c012f50af9158`
**Predecessor:** PLAY-1 Buddy PR #773, reviewed head `5a1736c55988e4b852bbcc2f0ada36d493fa5668`, merge `7fe771e86df2e796484b058aa2e6a8e7c94c9fb9`
**PR topology on activation:** serial within DEMO Knowledge/J3; one assigned PLAY-2 PR, no stacked successor
**Suggested branch/title after activation:** `codex/demo-j3-play2-persistent-vnext-postgres` / `DEMO-J3 PLAY-2: prove persistent vNext authority composition`

**Activation base:** Buddy `397e60791f938a4662f134dbf8e11538f61cb51d`
**Runtime ownership:** one disposable database created through the local
`dungeonmind-postgres-dev` admin authority on port 54329; live World authority
and Buddy application-state databases are excluded
**Migration source:** clean detached DungeonMind checkout at installed pin
`0f709d76fdc53bac9c9258d1751463ae2c76ca71`
**Concurrent lease check:** Buddy PR #775 is active on DEMO-J1 selected-World
context, but its production/UI write set is disjoint from this proof's two new
paths and its runtime witness does not own the disposable PLAY-2 database.
The user explicitly selected this as the next Kernel/DEMO-J3 slice; execution
is parallel-independent of #775 while remaining serial within DEMO Knowledge/J3.

The activation and acceptance sections below are retained as historical implementation evidence. Their write lease is released; the merged proof does not authorize PLAY-3 or product cutover.

## 0. Authority and activation

This is a bounded implementation design, **not dispatch authority**. PLAY-1
proved Buddy → WorldKeeper → DungeonMind in memory. Buddy's current DEMO roadmap
is the sole Buddy execution roadmap and explicitly says PLAY-2/3 do not dispatch
automatically. The DEMO steward must choose this as the next DEMO-J3 technical
witness after re-anchoring the actual journey and active leases.

Before changing this handoff to `ACTIVE`, the steward must:

1. fetch Buddy, DungeonMind and WorldKeeper default branches and all relevant
   open PRs; record exact Buddy implementation base and dependency pins;
2. confirm PLAY-1's Buddy consumer, WorldKeeper runtime and DungeonMind native
   PostgreSQL repository still compose without a new contract or dependency pin;
3. confirm no open Buddy PR leases the expected paths below, and identify a
   dedicated PostgreSQL admin DSN permitted to create one disposable database;
4. identify a **clean DungeonMind source checkout at the exact installed Buddy
   pin** for Alembic migrations 0001–0010 (the migrations are not in the wheel);
5. obtain DEMO-J3 sequencing agreement and name the runtime database ownership;
6. land only activation facts/status on Buddy main, then dispatch one isolated
   implementation checkout from that newly accepted base.

If any precondition fails, keep `BLOCKED`. Do not work around it by using live
Eldyrwild, repinning dependencies, copying migration SQL into Buddy, or opening
an implementation PR from this design-time base.

At design time, Buddy Rules PR #763 owns `pyproject.toml` and `uv.lock`; PLAY-2
does **not** lease either file. E5Q remains separately blocked by that Rules
dependency-file lease. This proof may be scheduled independently only while
its source, dependency and database ownership remain disjoint.

## 1. One merge-ready invariant

One ordinary PLAY-1 Buddy proposal pair (an object plus a GM-authored custom
relationship to it) can be prepared and explicitly confirmed through the
accepted Buddy consumer and WorldKeeper service against a **new, isolated,
persisted DungeonMind vNext PostgreSQL authority**. A fresh repository/service
instance can read and verify the exact immutable child; replay is idempotent;
stale and competing writes fail without an extra child or head event.

The accepted chain is:

```text
Buddy GraphObjectAuthoringProposalPayload + PlayAuthoringContext
  → WorldKeeperGraphAuthoringConsumer.build_intent/prepare/commit
  → DungeonMindWorldKeeperRuntime
  → PostgresKnowledgeRevisionRepository(PostgresDatabase(disposable_dsn))
  → native vNext revision, head, event, receipt and prospective result
  → exact-child read-back from a newly constructed repository
```

This is an **isolated acceptance composition**, not a production route or a
browser journey. No source-ingestion, legacy World Graph, bridge-genesis,
V2→V3 profile transition, live campaign data or cutover is part of the PR.

## 2. Reuse the accepted contracts unchanged

- Buddy owns proposal validation/mapping, `PlayAuthoringContext`, its exact
  `dungeonbuddy.custom:<local-term>` predicate mapping and GM/campaign labels.
- WorldKeeper owns `WorldChangeIntent`, immutable `PreparedWorldChange`,
  `ResultOf(client_op_id)`, confirmation coordination, and
  `VerifiedCommittedChange` with exact-child verification.
- DungeonMind owns native vNext storage, profile/domain refs, durable IDs,
  expected-parent CAS, publication identity, receipt, replay and head events.

Use the existing `WorldKeeperGraphAuthoringConsumer` and
`DungeonMindWorldKeeperRuntime(repository=...)`. The canonical fixture is PLAY-1's
`Pippa works_at brewery` proposal with the relationship listed before the
new object, exact `ent:pippa`, admitted `ev:play-session-note`, and semantic
profile `dungeonbuddy.dnd5e` revision 2 (`dm_semantic_profile_v3`). Seed a
native vNext parent pinned to that profile from inception. The evidence ref is
fixture authority only: it does **not** prove source admission or source-content
persistence.

The Buddy-installed DungeonMind and WorldKeeper runtime pins already contain
the necessary APIs; the current default branches have no changes to the
relevant runtime modules since those pins. Do not bump `pyproject.toml` or
`uv.lock` merely because their repositories' mains advanced through governance.

## 3. Expected write lease (only while ACTIVE)

```text
tests/integration/test_demo_j3_play2_persistent_vnext_postgres.py  # new
Docs/Reports/REPORT-DEMO-J3-PLAY-2-persistent-vnext-postgres.md    # new
```

The steward, not the implementation worker, owns activation/completion edits
to this handoff and the DEMO roadmap. The implementation PR may include a
backward-looking PLAY-1 state correction only if the steward explicitly adds
that path to the active lease before dispatch.

Verify but normally do not edit:

```text
apps/live_control_server/integrations/worldkeeper/graph_authoring_consumer.py
apps/live_control_server/integrations/dungeonmind/vnext_complete_object.py
src/graph_memory/vnext/domain_runtime.py
pyproject.toml
uv.lock
apps/live_control_server/routes/**
apps/live_control_server/main.py
```

A need to change Buddy production code, WorldKeeper, DungeonMind, migration
packaging, dependencies, or a shared fixture is a stop/split signal. This
acceptance PR must not silently become a runtime repair PR.

## 4. Runtime and database isolation

The test file may contain a local fixture/helper for provisioning; do not
modify global `tests/conftest.py`. Require explicit
`DMB_PLAY2_PG_ADMIN_DSN` and `DMB_PLAY2_DUNGEONMIND_SOURCE` for the positive
PostgreSQL run. The latter must be a clean checkout of the exact Buddy-pinned
DungeonMind SHA; verify `HEAD` and `alembic.ini`/`migrations/**` cleanliness.

The fixture creates a unique `dmb_play2_test_<random>` database via the admin
connection, derives its DSN by replacing **only** the database path, runs the
exact source checkout's Alembic upgrade to head against that new database,
then constructs `PostgresDatabase` and `PostgresKnowledgeRevisionRepository`.
It drops only the database it created, by its validated exact generated name,
in `finally`. No broad truncation, shared test DB, cached app-state DB or
pre-existing World database is allowed. Guard against the configured live
DungeonMind/World and Buddy APP-STATE DSNs before connecting or migrating.
Do not print DSN credentials in test output or the report.

Default tests may skip this external-I/O fixture when the explicit admin DSN
is absent; the **merge-blocking positive run must report zero skips**. An
unavailable PostgreSQL instance or missing exact migration checkout is an
unmet gate, not a green acceptance result. PostgreSQL data must outlive the
first connection and service objects for restart/read-back witnesses; no
database server restart or live authority access is required.

## 5. Canonical and negative witnesses

The owning integration test must prove, at the PostgreSQL boundary:

1. prepare is read-only: native head, event, receipt and prospective-result
   counts do not change;
2. explicit confirm publishes one child from the exact parent; one head event,
   one receipt and one prospective-result row agree on publication/child IDs;
3. DungeonMind allocates the brewery `ent:*` and relationship `asrt:*`; the
   exact child contains `ent:pippa → dungeonbuddy.custom:works_at → allocated
   brewery`, with the accepted GM/campaign/evidence semantics;
4. `VerifiedCommittedChange` IDs and digest agree with the stored immutable
   child, head and receipt—not merely with a returned creation payload;
5. close/rebuild the database repository, WorldKeeper runtime and Buddy
   consumer; an independent process or newly opened connection reads the same
   head/child/digest. No in-memory repository may serve read-back;
6. replay the **same prepared value** through the rebuilt service: same
   verified child/result, no additional revision, head event or receipt;
7. two distinct prepared values from one parent race through separate
   PostgreSQL connections: exactly one wins, the other is stale/conflicting,
   and there is only one child/head advance; concurrent duplicate confirmation
   of one prepared value cannot create a second child and must end in exact
   replay or a documented retry-safe recovery path;
8. missing evidence, V2-pinned parent, altered prepared meaning/identity,
   changed publication request, and stale parent fail closed with no extra
   publication. A deliberately unsafe/live DSN is rejected before migration
   or mutation.

Retain a focused PLAY-1 in-memory regression and V6.2 complete-object adapter
regressions, but do not claim this proof is the browser read path or a full
source-admission witness. If an exact process-restart check cannot serialize
the immutable prepared value under an accepted contract, perform the
cross-process read-back separately and replay via a newly constructed service
using the original immutable prepared value; do not invent a public wire
serialization format or use untrusted pickle.

## 6. Verification and evidence receipt

At activation, record actual base/pins and a safe admin DSN fingerprint (not
credentials). With an exact DungeonMind source checkout and disposable
PostgreSQL admin authority:

```bash
uv sync --locked
DMB_PLAY2_PG_ADMIN_DSN='<admin PostgreSQL DSN>' \
DMB_PLAY2_DUNGEONMIND_SOURCE='<clean exact-pin DungeonMind checkout>' \
  uv run pytest -q tests/integration/test_demo_j3_play2_persistent_vnext_postgres.py -rs
uv run pytest -q tests/test_con_ready_play_worldkeeper_consumer.py \
  tests/test_v6_2_vnext_complete_object_adapter.py
uv run ruff check tests/integration/test_demo_j3_play2_persistent_vnext_postgres.py
git diff --check
```

Inspect the full default non-live suite too. PLAY-1 reported eight inherited
collection errors on its activation base; compare exact new base and head
before classifying any such failure. No skip/xfail may stand in for the
positive PostgreSQL witness. Report database creation/cleanup, test count and
zero skips, exact repository/pin/migration SHAs, revision/head/event/receipt
counts before/after/replay/race, and whether process-independent read-back
passed. The report must explicitly state what remains unproved.

## 7. Stop conditions

Stop and return to the DEMO and KERNEL stewards if any of these appears:

- a direct Buddy import of DungeonMind write/publication APIs is needed
  outside the test's composition fixture;
- the accepted WorldKeeper runtime cannot use the PostgreSQL repository port
  without a contract or implementation change;
- the installed DungeonMind migration source cannot be pinned/provisioned
  reproducibly without copying migration logic into Buddy;
- one of the exact-child, receipt, CAS, replay or concurrency witnesses fails;
- source admission, V2→V3 migration, a production route, UI or APP-STATE
  change is needed to make the test pass;
- any test would read or mutate live Eldyrwild or a pre-existing operator DB;
- the required write lease expands beyond a local proof/report into a second
  independently useful capability.

Do not patch another repository from the PLAY-2 PR. Return a precise defect
and a bounded owner-specific repair request instead.

## 8. Handback, acceptance token and successor

The implementation handback includes exact Buddy base/head, changed paths,
installed package `direct_url.json` pins, DungeonMind migration-source SHA,
positive PostgreSQL test counts with zero skips, negative/concurrency/replay
and restart evidence, lock/Ruff/regression results, PR URL, and explicit
unproved boundaries. A reviewer evaluates the exact cumulative diff and
reruns the isolated PostgreSQL witness before any merge-ready judgment.

Only after independent exact-head review and authorized merge may the steward
record:

```text
CON_READY_PLAY_2_PERSISTENT_VNEXT_POSTGRES_ACCEPTED
```

That token means **isolated persistent composition only**. It is not DEMO-J3
human acceptance, PLAY-3/browser authorization, source-admission completion,
bridge migration, live Eldyrwild publication or cutover.

The successor is a fresh DEMO-J3 re-anchor: decide the smallest browser/
next-turn retrieval integration or external contract repair from the observed
journey. Do not auto-dispatch PLAY-3 or change the Kernel roadmap phase merely
because this proof passes.

## 9. Accepted completion record

Buddy PR [#779](https://github.com/Drakosfire/DungeonMindBuddy/pull/779) merged on 2026-09-27 at `2ccc96ff2a7d76328578609d5289fd3babcf6442` from exact accepted head `2d5ab6ade1d89ec608c941093819ea36404fd18e`. PRIME Cycle 1 HOLD review `5331382343` covered `b3eab88b27acc547e76998c7960cd9c06ad31e62`; Cycle 2 PASS review `5331441470` accepted the repaired head. Independent Cycle 2 evidence: four isolated PostgreSQL tests passed with zero skips, 54 PLAY-1/V6.2 regressions passed, scoped Ruff and cumulative diff check passed, and no disposable `dmb_play2_test_*` database remained. The eight default-suite collection errors were inherited on base and head.

`CON_READY_PLAY_2_PERSISTENT_VNEXT_POSTGRES_ACCEPTED` is now recorded for isolated persistent composition only. Source admission, browser interaction, next-turn retrieval, DEMO-J3 human acceptance, and production cutover remain open.
