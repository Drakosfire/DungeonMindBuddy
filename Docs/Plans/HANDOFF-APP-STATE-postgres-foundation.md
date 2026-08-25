---
pr_body_template: |
  ## Handoff pointer
  - Workstream: APP-STATE / AS1 — PostgreSQL foundation + Plan WorkObject consumer
  - Flow: APP-STATE
  - Direction: DESIGN → CODE → REVIEW
  - Handoff: Docs/Plans/HANDOFF-APP-STATE-postgres-foundation.md
  - Implementation repository: Drakosfire/DungeonMindBuddy

  ## Verification pointer
  - Architecture: Docs/Design/ARCHITECTURE-application-state-layer.md v1.1
  - Predecessor: AS0.1 PR #639 merge dd09f7f707e38f9f4348b759da8cfdbbe420fd60
  - Accepted predecessor head: abb3fb15f9b56e8712c07c798674d0462827677f
  - Predecessor review: Review Cycle 2 PASS-equivalent, review 5014814402
  - Production consumer: kind=plan workspace documents
  - Empty-table PRs are not this slice

  The checked-in handoff, cumulative diff, nano-commit story, and independently
  rerun evidence are the review contract. This body is transport metadata.
---

# HANDOFF — AS1: Buddy PostgreSQL foundation with Plan WorkObject consumer

**Created:** 2026-08-24  
**Re-anchored:** 2026-08-24 after AS0.1 / PR #639 merge  
**Status:** DONE — merged PR #641 at `29ff1584b9f76bb5100a724a96bebbbcf8f08d12`  
**Accepted head:** `b42eb629e8924695af7af5a6c986f44a26dc3536`  
**Review:** 3 distinct-head cycles; final PASS-equivalent review `5023488870`  
**Execution evidence:** PR #641 comment `5415847095`  
**Canonical handoff path:** `Docs/Plans/HANDOFF-APP-STATE-postgres-foundation.md`  
**Conversation/workstream:** `APP-STATE`  
**Flow / owner:** `APP-STATE`  
**Direction:** DESIGN → CODE → REVIEW  
**Base revision:** `dd09f7f707e38f9f4348b759da8cfdbbe420fd60` — merge of PR #639  
**Predecessor accepted head:** `abb3fb15f9b56e8712c07c798674d0462827677f`  
**Predecessor review:** Review Cycle 2 PASS-equivalent, review `5014814402`  
**PR title:** `APP-STATE: persist Plan documents on PostgreSQL`

> Repository law: [`AGENTS.md`](../../AGENTS.md). Steward process: [`../Process/STEWARD-CYCLE.md`](../Process/STEWARD-CYCLE.md). Architecture authority: [`../Design/ARCHITECTURE-application-state-layer.md`](../Design/ARCHITECTURE-application-state-layer.md). Roadmap: [`../Roadmaps/ROADMAP-application-state.md`](../Roadmaps/ROADMAP-application-state.md).

---

## §1 Mission and merge-ready invariant

**Mission:** Make the first real Buddy application-state consumer boringly durable.
A GM can create, autosave, commit, restart, and reload a Plan workspace document
(`kind=plan`) through the existing live-control workspace-document API, with
committed Markdown and recoverable drafts owned by Buddy PostgreSQL rather than
`out/` files.

**Merge-ready invariant:**

> **After AS1, `kind=plan` durable state is owned by the Content domain service over the Buddy application-state unit of work. WorkObject identity is the existing document UUID; WorkingCopy is the recoverable mutable draft; WorkRevision is immutable committed Markdown with SHA-256; CAS conflicts fail closed; PostgreSQL unavailable never falls back to leftover Plan files; existing current bytes import exactly and idempotently without fabricated history; and owning-boundary tests prove the existing route/service behavior against real PostgreSQL.**

A PR that only adds connection helpers, Alembic scaffolding, and unused
`content.*` tables is **not** AS1.

AS1 is intentionally the smallest real proof of the wider v1.1 architecture.
It must prove the shared substrate without turning WorkObject into a universal
application object or pulling Ingest, Asset, generated-artifact, Play Runtime,
or Combat schemas into the slice.

### Pre-dispatch critique

| Question | Answer |
|---|---|
| Why Plan first? | It is a real persisted surface with enough behavior to prove configuration, migrations, UoW, CAS, revision identity, import, restart durability, fail-closed behavior, and route wiring without the transactional complexity of Play Runtime. |
| Most likely false-positive implementation | Repository tests pass while production Plan routes still write registry JSON / Markdown files. |
| Required defense | Route/domain-service integration must create, autosave, commit, restart/reconnect, and reload a Plan with its former Plan Markdown path absent. |
| Easiest migration mistake | Fabricating revision history from the old integer CAS token. Import **one** exact current WorkRevision at the existing revision number; do not invent R1…R(n-1). |
| Easiest architecture mistake | Generalizing WorkObject into `application_object(id,type,jsonb)` or introducing path/URL/storage locator identity into shared APIs. |
| Scope-expansion stop | If Runbook, Play Run, Combat, Ingest, Asset, generated artifacts, Docker changes, or DungeonMind schema changes are required to make AS1 work, stop and re-brief. |

---

## §2 Current authority and lane

### 2.1 Accepted predecessor

AS0 established Buddy-owned PostgreSQL as the transactional application-state
substrate. AS0.1 / PR #639 widened the law before implementation:

```text
stable Buddy domain identity
    → owning Buddy domain service
    → Buddy PostgreSQL durable state

large binary bytes
    → stable asset_id / metadata in Buddy state
    → DungeonMindServer storage/CDN for bytes

World truth
    → DungeonMind

derived/regenerable representations
    → remain derived unless product correctness says otherwise
```

AS1 consumes only the first branch, for Content `kind=plan`.

### 2.2 Context matrix

| Field | Frozen AS1 answer |
|---|---|
| Parent authority | `Docs/Design/ARCHITECTURE-application-state-layer.md` v1.1 |
| Exact implementation base | `dd09f7f707e38f9f4348b759da8cfdbbe420fd60` |
| Predecessor | AS0 #636 + AS0.1 #639 |
| Existing identity contract | `CONTRACT-workspace-document-identity-v1.md`: UUID identity, discard-not-delete, kind enum |
| Exact input consumed | Current `kind=plan` registry records + snapshot Markdown bytes; existing `/api/live/workspace-documents*` and Tiptap prepare/commit behavior |
| Named successor | AS2 — Playable/`runbook` historical WorkRevisions |
| Branch | `agent/app-state-postgres-foundation` in an isolated worktree |
| Runtime authority | Buddy logical DB `dungeonbuddy_application_state` or isolated worktree override |
| World DB boundary | Never use `DUNGEONMIND_WORLD_GRAPH_AUTHORITY_DATABASE_URL`, `DUNGEONMIND_DATABASE_URL`, `dungeonmind_cutover_live`, or `DMB_CUTOVER_TEST_DATABASE_URL` as application-state fallback |

### 2.3 Parallel CUTOVER lane

PR #638 is currently a **design-only** CUTOVER D.2B PR. Its handoff explicitly
keeps D.2B disjoint from `pyproject.toml`, `uv.lock`, `src/application_state/**`,
workspace-document persistence, and APP-STATE authority docs.

Therefore AS1 may proceed in parallel from this base.

Before implementation begins, re-check current changed-path leases. If a later
CUTOVER implementation has acquired `pyproject.toml`, `uv.lock`, or the same
server bootstrap path, serialize that file ownership rather than merging through
a conflict. Do not broaden AS1 to absorb CUTOVER work.

### 2.4 What remains false after AS1

Even when AS1 is successful:

```text
kind=runbook                 still file-backed
Play Run / manifest          still file-backed
active Run                   still file-backed
Combat                       still file-backed
worldbuilding_source         unchanged
Ingest / Source schemas      unimplemented
Asset service/CDN wiring     unimplemented
Generated artifact schemas   unimplemented
World Graph                  unchanged; DungeonMind authority
historical Plan revisions    only exist from import point forward
corpus Session Prep publish  still explicit; never silent
```

That is expected. Do not “finish the platform” in this PR.

---

## §3 Required observable behavior

| Observable path | Current behavior | AS1 required behavior | Owning boundary |
|---|---|---|---|
| `POST /api/live/workspace-documents`, `kind=plan` | registry JSON + optional target path | create WorkObject; stable UUID preserved | Content service + PostgreSQL |
| Plan snapshot GET | registry + current file bytes | WorkObject + WorkingCopy or exact current WorkRevision | Content service + PostgreSQL |
| Plan autosave | browser/file-oriented recovery | server WorkingCopy durable across process restart | Content service + PostgreSQL |
| Tiptap prepare/commit Plan | file write + registry revision increment | WorkingCopy validation + immutable WorkRevision insert + CAS | Content service + route adapter |
| CAS mismatch | registry expected revision → 409 | DB-native compare-and-swap → 409, no partial write | Content service + PostgreSQL |
| DB unavailable after switch | files may still exist | named failure; **no Plan file fallback** | config/service |
| `kind=runbook` through same routes | file-backed | unchanged file behavior | existing registry/writer |
| existing Plan adoption | no DB import | exact current registry metadata + current bytes → one honest WorkRevision/WorkingCopy state | import service |
| corpus Session Prep `target_relpath` | file may be authority | metadata/export pointer only; not read authority after switch | Content service |

### Adversarial sequences

| Sequence | Required safe outcome |
|---|---|
| transaction fails before COMMIT | no half-created WorkRevision; prior durable state remains |
| two writers commit with same expected revision | exactly one succeeds; the other receives 409 |
| exact commit replay after success | no second semantic revision if the exact committed digest/revision is already durable |
| changed bytes with stale CAS | 409; no overwrite |
| import same legacy state twice | second pass no-ops |
| import same identity with conflicting digest | fail closed; do not switch that object |
| delete former `out/workspace/plan/<id>.md` after switch | Plan snapshot/commit still operate from PostgreSQL |
| invalid/missing app-state DSN after switch | named unavailable error; no file read |
| World Graph DSN supplied as app-state URL | isolation guard refuses |
| Runbook save during AS1 | remains on existing file-backed path |
| server process restart after autosave | WorkingCopy is still recoverable |

---

## §4 Storage model AS1 is allowed to introduce

### 4.1 Shared substrate

```text
src/application_state/
  config
  errors
  isolation / database naming guards
  connection factory
  unit of work
  explicit migration CLI / head check
  Buddy-owned Alembic tree
```

Shared means transaction/configuration infrastructure—not a shared domain
ontology.

### 4.2 Content domain

AS1 may introduce the Content primitives already frozen by the architecture:

```text
WorkObject
  stable document identity + metadata + lifecycle

WorkingCopy
  mutable recoverable draft for one WorkObject

WorkRevision
  immutable committed UTF-8 content + digest + revision identity
```

Exact table/column spelling may follow the accepted architecture and repository
conventions, but the semantics above are not optional.

Expected schema family:

```text
content.work_object
content.work_revision
content.working_copy
```

### 4.3 Explicitly forbidden generalization

Do **not** create:

```text
application_object
  id
  type
  jsonb
```

as the universal future state model.

Do not create speculative:

```text
ingest.*
assets.*
statblock.*
play.*
combat.*
```

AS1 proves substrate reuse by restraint, not by pre-creating every future table.

---

## §5 Migration / adoption contract

AS1 must handle existing Plan state honestly.

### 5.1 Legacy → Content mapping

| Predecessor field | AS1 meaning |
|---|---|
| `document_id` | exact `work_object_id`; never issue a replacement UUID |
| `kind=plan` | admitted Content kind |
| title / campaign / target session | WorkObject metadata |
| `target_relpath` | optional locator/export metadata; not byte authority after switch |
| active/discarded | lifecycle state; no hard-delete rewrite |
| draft | WorkingCopy; no fabricated committed revision |
| committed current bytes | one WorkRevision at the current predecessor revision number |
| predecessor integer `revision` | current imported revision/CAS anchor only; **not evidence that historical bytes exist** |
| Markdown bytes | exact UTF-8 bytes used to compute persisted SHA-256 |
| `file_fingerprint` | retired as authority after switch |

### 5.2 Import rules

```text
capture existing metadata + current bytes
    → compute exact digest
    → write WorkObject + honest current state transactionally
    → verify persisted identity/digest
    → matching replay = no-op
    → conflicting replay = fail closed
    → only then treat PostgreSQL as Plan authority
```

Never fabricate historical revisions.

Never silently rewrite corpus Session Prep Markdown as part of adoption.

Import tests must operate on disposable fixture state, not mutate the operator's
real Plan/corpus files.

---

## §6 Configuration and migration contract

### Runtime DSN

```text
DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL
```

### Test/admin DSN

```text
DMB_APPLICATION_STATE_TEST_DATABASE_URL
```

The application-state URL is independent of every DungeonMind World Graph URL.
No fallback from one authority to the other is permitted.

### Dependencies

AS1 adds direct Buddy dependencies for:

```text
psycopg
alembic
```

Do not rely on `dungeonmind[postgres]` transitively as the Buddy app-state driver
contract.

### Migration behavior

- Buddy owns a separate Alembic tree.
- Explicit CLI applies migrations.
- Ordinary app boot verifies migration head and fails closed if behind.
- Ordinary app boot must **not** run `alembic upgrade` as a traffic-serving side effect.
- Tests create/use isolated disposable databases.
- No second PostgreSQL server/container is required by AS1; stop if local reality contradicts that assumption rather than editing Docker opportunistically.

---

## §7 Files in scope — implementation write lease

### Application-state package

| Action | Path | Purpose |
|---|---|---|
| Create | `src/application_state/__init__.py` | package export |
| Create | `src/application_state/config.py` | app-state DSN parsing; no World fallback |
| Create | `src/application_state/errors.py` | named fail-closed errors |
| Create | `src/application_state/naming.py` | database isolation / denylist guards |
| Create | `src/application_state/engine.py` | psycopg connection factory |
| Create | `src/application_state/unit_of_work.py` | transaction boundary |
| Create | `src/application_state/cli.py` | explicit upgrade/head-check entrypoint |
| Create | `src/application_state/alembic.ini` | Buddy Alembic config |
| Create | `src/application_state/migrations/env.py` | Buddy migration environment |
| Create | `src/application_state/migrations/script.py.mako` | Alembic template |
| Create | `src/application_state/migrations/versions/*.py` | initial Content schema |

### Content domain

| Action | Path | Purpose |
|---|---|---|
| Create | `src/application_state/content/__init__.py` | Content exports |
| Create | `src/application_state/content/types.py` | WorkObject / WorkRevision / WorkingCopy types |
| Create | `src/application_state/content/repository.py` | Content SQL only |
| Create | `src/application_state/content/service.py` | Plan-admitted domain service |
| Create | `src/application_state/content/import_plans.py` | exact/idempotent legacy Plan adoption |

### Existing product adapters

| Action | Path | Purpose |
|---|---|---|
| Modify | `pyproject.toml` | direct `psycopg` + `alembic` dependencies |
| Modify | `uv.lock` | dependency lock |
| Modify | `apps/live_control_server/routes/workspace_documents.py` | route `kind=plan` through Content service |
| Modify | `apps/live_control_server/services/tiptap_markdown_write.py` | Plan prepare/commit through Content service |
| Modify | `apps/live_control_server/services/workspace_document_registry.py` | cease Plan-kind authority after switch; preserve other kinds |

### Evidence

| Action | Path | Purpose |
|---|---|---|
| Create | `tests/application_state/conftest.py` | ephemeral PostgreSQL fixture + isolation guards |
| Create | `tests/application_state/test_isolation_guards.py` | no World DB / product DB accidents |
| Create | `tests/application_state/test_plan_work_object_postgres.py` | create/autosave/commit/reload/CAS/restart/unavailable/file-absent |
| Create | `tests/application_state/test_plan_existing_state_import.py` | exact/idempotent import + conflicts |

### State-authority sync in the AS1 PR

| Action | Path | Required state truth |
|---|---|---|
| Modify | `Docs/Roadmaps/ROADMAP-application-state.md` | AS0.1 = DONE at #639 merge; AS1 = THIS PR; do not claim AS1 merged |
| Modify | `Docs/Plans/HANDOFF-APP-STATE-application-state-architecture.md` | archive/backward-looking AS0/AS0.1 predecessor truth as appropriate |
| Modify | `Docs/Plans/STEWARDS-ANCHOR-application-state.md` | #639 merge/review truth; AS1 active/this PR; AS2 still false |

After AS1 actually merges, the **next steward re-anchor** records AS1 merge SHA
and review-cycle count and decides/dispatches AS2. Do not pre-claim that state in
this implementation PR.

### Bounded discovery

```text
Directory: tests/application_state/
Maximum additional paths: 8
Allowed: pytest modules needed to prove an existing §10 evidence row

Directory: src/application_state/migrations/versions/
Maximum additional paths: 3
Allowed: migration revisions only if one initial revision cannot honestly carry
         the schema after the branch has already been shared
```

A required production path outside this lease is a stop report.

---

## §8 Explicitly out of scope

Do not touch or claim:

- `apps/live_control_server/services/play_run_*.py` — AS3;
- `apps/live_control_server/services/play_active_run.py` — AS4;
- Combat persistence/services — later domain migration;
- `kind=runbook` authority switch — AS2;
- `kind=worldbuilding_source` authority switch — later Content migration;
- `ingest.*`, SourceArtifact persistence, Asset schemas, generated-artifact schemas;
- DungeonMindServer storage/CDN integration;
- DungeonMind schema or World Graph authority behavior;
- Docker/compose unless a stop/re-brief explicitly changes the architecture;
- event sourcing / speculative mutation-history tables;
- automatic Plan export back to corpus;
- path, CDN URL, bucket key, or DB coordinate as stable product identity.

`apps/live_control_server/config.py` World Graph helpers remain separate. If a
one-line app-state re-export is unavoidable, stop and document why before taking
that path; app-state configuration belongs under `src/application_state`.

---

## §9 Failure / replay / trust contract

### Fail closed

| Situation | Required result |
|---|---|
| app-state DSN missing/unusable after Plan switch | named unavailable error; no Plan file fallback |
| schema behind head | ordinary app operation refuses; no automatic migration |
| stale CAS | 409; no partial write |
| import digest conflict | abort that adoption; no best-effort overwrite |
| identity mismatch | fail closed; never create replacement identity silently |
| World DB detected as app-state target | refuse before destructive/useful write |

### Replay

| Operation | Replay rule |
|---|---|
| read | idempotent |
| exact successful commit replay | no duplicate semantic revision when exact digest/revision already durable |
| changed bytes + stale CAS | 409 |
| exact import replay | no-op |
| conflicting import replay | fail closed |

### Trust boundary

AS1 verifies:

```text
stable UUID identity
plan kind admission
stored byte digest
CAS
migration head
application-state DB isolation
post-switch no-file authority
```

AS1 does **not** prove or own:

```text
Play semantics
Combat state
World truth
Ingest lifecycle
Asset delivery
browser localStorage as durable authority
```

---

## §10 Evidence required to merge

### 10.1 Owning-boundary evidence matrix

| Guarantee | Owning boundary | Required evidence |
|---|---|---|
| Plan create/autosave/commit/reload is PostgreSQL-backed | existing route → Content service → real Postgres | integration test using disposable PostgreSQL |
| process restart preserves WorkingCopy and committed content | Content service + new DB connection/process-equivalent fixture | reconnect/recreate service and load exact bytes |
| former Plan Markdown file is unnecessary after switch | route/service | delete/withhold file and repeat snapshot + commit behavior |
| CAS protects concurrent writers | Content service + DB | two writers with same expected revision: one success, one 409 |
| unavailable DB fails closed | route/service | break DSN after switch; prove no file fallback |
| World/app-state isolation | config/naming guard | refuse World Graph DSN/database names |
| exact legacy adoption | import service | IDs, revision number, bytes, SHA match source fixture |
| import replay | import service | second identical pass produces no semantic change |
| import conflict | import service | same identity / changed digest fails closed |
| Runbook remains file-backed | existing routes/writer | regression proving `kind=runbook` did not switch |
| app boot does not migrate | startup + CLI | behind-head DB fails/checks; schema remains unchanged until explicit upgrade |
| latency hypothesis is measured | route/service benchmark artifact | baseline vs head load/autosave/commit numbers recorded without inventing a performance claim |
| exact lease | git | diff from `dd09f7f707e38f9f4348b759da8cfdbbe420fd60` contains only §7 + bounded evidence paths |

Repository-only tests are insufficient for the core invariant. At least one
integration path must traverse the existing live-control route/domain boundary
against a real disposable PostgreSQL database.

### 10.2 Exact verification commands

Implementation may split node IDs, but preserve this proof shape:

```bash
uv run pytest \
  tests/application_state/test_isolation_guards.py \
  tests/application_state/test_plan_work_object_postgres.py \
  tests/application_state/test_plan_existing_state_import.py \
  -q

# Default APP-STATE tests must not require or mutate the operator product DB.
uv run pytest tests/application_state -q

git diff --check
git diff --name-only dd09f7f707e38f9f4348b759da8cfdbbe420fd60...HEAD
```

### 10.3 Minimal product dogfood

```text
1. Create or open one kind=plan document through the existing surface/API.
2. Autosave a draft.
3. Restart/recreate the live-control server process/service boundary.
4. Confirm the draft is recoverable.
5. Commit Markdown.
6. Confirm snapshot digest/bytes.
7. Remove or make inaccessible the old Plan Markdown authority path.
8. Reload again.

Expected:
  exact content survives;
  PostgreSQL remains sole Plan durable authority;
  no file fallback occurs.
```

If UI dogfood is unavailable, route-level integration against disposable
PostgreSQL is mandatory and UI dogfood is recorded as an explicit operator
follow-up—not silently omitted.

### 10.4 Baseline handling

Run the relevant new tests or equivalent checks against base
`dd09f7f707e38f9f4348b759da8cfdbbe420fd60` where useful. Collection misses for
new tests are baseline absence, not product regressions. Record unrelated
baseline failures separately.

---

## §11 Nano-commit / implementation story

Prefer independently reviewable commits along this shape; exact count is not a
contract:

```text
1. app-state config + DB isolation + explicit migration lifecycle
2. Content schema + repository/UoW
3. Plan service + exact legacy import
4. existing Plan route/Tiptap authority switch
5. adversarial PostgreSQL integration + restart/file-absent proof
6. atomic roadmap/anchor predecessor sync
```

Do not use commit boundaries to excuse a temporarily widened final PR. The final
cumulative diff must still obey one AS1 invariant and the §7 lease.

---

## §12 Required review handback

The implementation agent must hand back:

1. exact PR number / branch / head SHA;
2. `Review Cycle 1` starting point;
3. §1 invariant disposition;
4. exact changed paths vs §7;
5. nano-commit story;
6. migration(s) and app-state DB configuration introduced;
7. required-vs-produced §10 evidence with command output/provenance;
8. baseline failures/waivers;
9. demonstration that former Plan files are not authority after switch;
10. demonstration that Runbook remains file-backed;
11. current parallel CUTOVER collision check;
12. stop conditions encountered and resolution;
13. explicit statement that AS2 remains false/unimplemented.

---

## §13 Acceptance rubric

- [ ] One independently useful capability: durable Plan authoring on PostgreSQL.
- [ ] Existing Plan create/snapshot/autosave/commit behavior is wired through the Content service.
- [ ] WorkingCopy survives process/service restart.
- [ ] WorkRevision is immutable and byte/digest exact.
- [ ] Existing UUID identity is preserved.
- [ ] Existing current state imports honestly and idempotently without fabricated history.
- [ ] CAS conflict returns 409 with no partial/last-writer overwrite.
- [ ] App-state DB unavailable fails closed with no Plan file fallback.
- [ ] Former Plan Markdown path can be absent after switch.
- [ ] Runbook and `worldbuilding_source` authority are unchanged.
- [ ] Direct Buddy `psycopg` + `alembic` dependencies exist.
- [ ] App boot checks migration head but does not mutate schema.
- [ ] App-state DSN cannot silently resolve to World Graph authority.
- [ ] WorkObject remains a Content primitive, not universal `id/type/jsonb` state.
- [ ] No Ingest/Source/Asset/generated-artifact/Play/Combat schema expansion.
- [ ] No CDN/storage integration in AS1.
- [ ] No path/URL/storage locator becomes stable domain identity.
- [ ] Required real-PostgreSQL route/service evidence exists.
- [ ] Latency is measured rather than assumed.
- [ ] Final changed paths remain inside §7 / bounded discovery.
- [ ] Roadmap/anchor state sync records #639 as predecessor and AS1 as this PR, not already merged.

---

## §14 Stop conditions

Stop and report instead of broadening the PR when any of these appears:

- a second independently useful product outcome is required;
- `kind=runbook`, Play Run, Combat, Ingest, SourceArtifact, Asset, or generated-artifact migration becomes necessary;
- a universal application-object table seems necessary;
- Docker/compose change is required to obtain a usable Buddy database;
- owning-boundary evidence cannot be produced against disposable PostgreSQL;
- WorkingCopy vs committed WorkRevision semantics become ambiguous;
- a production path outside §7 is required;
- a later parallel lane acquires `pyproject.toml`, `uv.lock`, or another AS1 path and cannot be serialized cleanly;
- application state cannot be isolated from DungeonMind World databases;
- migrate-on-boot becomes necessary;
- the implementation requires path/URL/storage-locator identity in a shared API;
- post-switch Plan behavior requires reading the old file authority.

Report using:

```text
Stop condition:
Invariant clause affected:
Why current mission cannot absorb it:
Required evidence now missing:
Affected paths / ownership layers:
Proposed successor or re-brief:
State-authority update needed:
```
