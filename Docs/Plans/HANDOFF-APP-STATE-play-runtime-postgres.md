---
pr_body_template: |
  ## Handoff pointer
  - Workstream: APP-STATE / AS3 — transactional Play Runtime
  - Flow: APP-STATE
  - Direction: CODE → REVIEW
  - Handoff: Docs/Plans/HANDOFF-APP-STATE-play-runtime-postgres.md
  - Implementation repository: Drakosfire/DungeonMindBuddy

  ## Verification pointer
  - Architecture: Docs/Design/ARCHITECTURE-application-state-layer.md v1.1
  - Playable authority: Docs/Design/ARCHITECTURE-playable-material-and-runtime.md v1.1
  - Predecessor: AS2 PR #643 merge b4d63daab3eeb8150ca73fe9492d7a3d8744a4e0
  - Accepted predecessor head: 6b1c2e77648eee6180d293c92d2c97a428e9002f
  - Predecessor review: 3 distinct-head cycles; final PASS-equivalent review 5024971680
  - Production consumer: Play Run create/list/get/progress/manifest/rebase

  The checked-in handoff, cumulative diff, nano-commit story, and independently
  rerun evidence are the review contract. This body is transport metadata.
---

# HANDOFF — AS3: Transactional Play Runtime on PostgreSQL

**Created:** 2026-08-25  
**Status:** READY — AS2 merged; dispatch from the exact base below  
**Canonical handoff path:** `Docs/Plans/HANDOFF-APP-STATE-play-runtime-postgres.md`  
**Workstream / flow:** `APP-STATE`  
**Direction:** CODE → REVIEW  
**Implementation repository:** `Drakosfire/DungeonMindBuddy`  
**Exact base:** `b4d63daab3eeb8150ca73fe9492d7a3d8744a4e0` — merge of PR #643  
**AS2 accepted head:** `6b1c2e77648eee6180d293c92d2c97a428e9002f`  
**AS2 review:** 3 distinct-head review cycles; final PASS-equivalent review `5024971680`  
**AS2 exact-head evidence:** PR #643 comment `5417774447` — legacy Run migration witnesses `7 passed, 0 skipped`; owning-boundary suite `42 passed, 0 skipped`; clean `git diff --check`  
**Suggested branch:** `agent/app-state-play-runtime`  
**Suggested PR title:** `APP-STATE: persist Play Runtime transactionally`  
**Named successor:** AS4 — active Run continuity on PostgreSQL  

> Repository law: [`AGENTS.md`](../../AGENTS.md). Steward process: [`../Process/STEWARD-CYCLE.md`](../Process/STEWARD-CYCLE.md). Application-state authority: [`../Design/ARCHITECTURE-application-state-layer.md`](../Design/ARCHITECTURE-application-state-layer.md). Play authority: [`../Design/ARCHITECTURE-playable-material-and-runtime.md`](../Design/ARCHITECTURE-playable-material-and-runtime.md).

---

## §1 Mission and merge-ready invariant

**Mission:** Move the mutable Play Run aggregate and its sealed reference manifest from coordinated files into the Buddy Application State PostgreSQL database, so Start Run, Runtime CAS, manifest integrity, and preserve-only rebase are real database transactions rather than application-level multi-file protocols.

**Merge-ready invariant:**

> **After AS3, `play.run` is the sole durable authority for Run binding + mutable Runtime state and `play.run_manifest` is the sole durable sealed-manifest authority. Creating a Run and sealing its manifest is one PostgreSQL transaction; progress replacement uses SQL `run_revision` CAS; preserve-only rebase changes the Run binding and manifest in one transaction; a crash before COMMIT leaves the prior durable state; ordinary Play runtime never reads/writes `out/runtime/play/runs`, manifest sidecars, or rebase-intent files as fallback. `active-run.json` remains the active-selection authority until AS4, and deletion of replaced Play persistence code is AS5.**

The target transition is:

```text
AS2
Committed WorkRevision N
  ↓
file Run JSON
  + manifest sidecar
  + per-file locks
  + rebase intent/recovery

AS3
Committed WorkRevision N
  ↓ one UoW
play.run + play.run_manifest
  ↓
SQL run_revision CAS
  ↓ one UoW
transactional rebase
```

### Pre-dispatch critique

| Question | Frozen answer |
|---|---|
| Most likely false-positive implementation | Add `play.run` tables, but keep `PUT Run` and `PUT manifest` as two durable writes. A crash can still leave a Run without its required manifest. |
| Most dangerous compatibility trap | Rewrite the Start Run UI/API because the storage transaction changed. The current UI may keep create→seal; create must already atomically seal, and the later seal call becomes idempotent replay/read. |
| Most dangerous migration trap | Import Run JSON independently from sidecar manifests, or import while a legacy rebase intent is pending. AS3 imports a coherent Run+manifest aggregate only after legacy recovery is clean. |
| Most dangerous schema trap | Normalize Beats, Choices, notes, selections, or manifest elements into tables. Architecture freezes Run as an aggregate and explicitly allows `progress JSONB`. |
| Most dangerous authority trap | Keep a hidden env toggle/file fallback after switch. Import tooling may read legacy files explicitly; ordinary switched runtime may not. |
| Scope trap | Move `active-run.json` into SQL, delete all Play file modules, migrate Combat, or add mutation/event history. Those are AS4/AS5/later. |

---

## §2 Re-anchored authority and lane

### 2.1 Accepted predecessor truth

AS2 / PR #643 is merged at `b4d63daab3eeb8150ca73fe9492d7a3d8744a4e0` with accepted head `6b1c2e77648eee6180d293c92d2c97a428e9002f` after **3 distinct-head review cycles**; final PASS-equivalent review is `5024971680`.

AS2 proved:

- `kind=runbook` identity, WorkingCopy, and committed Markdown are PostgreSQL Content authority;
- Playable identity is `WorkRevision.revision_n + SHA-256`, not object CAS or path;
- historical Runbook revisions remain addressable after newer commits;
- existing pre-AS2 Runs survive honest Runbook adoption when their pinned revision bytes exist;
- missing historical bytes fail closed through the real Play admission path;
- Run/manifest/progress/rebase persistence intentionally remained file-backed for AS3.

AS3 must not weaken those Content semantics. In particular, a Run stores the exact Playable binding and never copies Runbook Markdown into Play storage.

### 2.2 Current Runtime authority at this base

At `b4d63daa…`, authoritative Runtime is still spread across:

```text
out/runtime/play/runs/<run-id>.json
out/runtime/play/reference-manifests/<run-id>.json
out/runtime/play/rebase-intents/<run-id>.json
out/runtime/play/active-run.json
```

with coordination in:

```text
apps/live_control_server/services/play_run_registry.py
apps/live_control_server/services/play_run_reference_manifest.py
apps/live_control_server/services/play_run_rebase.py
apps/live_control_server/services/registry_file_lock.py
src/live_play/live_store.py
```

The first three authorities switch in AS3. `active-run.json` does **not**.

### 2.3 Architecture already freezes the storage posture

Do not redesign this slice into a new data model. The accepted architecture freezes:

```text
play.run
  run_id UUID PK
  campaign_id
  playable_work_object_id
  playable_revision_n
  playable_work_revision_id
  playable_content_sha256
  run_revision INTEGER
  progress JSONB
  rebased_from_run_revision
  created_at / updated_at

play.run_manifest
  one row per Run
  exact Run/Playable binding
  validated sealed manifest JSON
  sealed_at
```

`progress JSONB` is the existing validated `PlayRunProgress` aggregate. It is **not** a generic application-object bucket. Do not split `resolvedBeatIds`, selections, notes, or current position into persistence tables in AS3.

The manifest row may store the validated manifest document as JSONB plus the explicit binding/integrity columns needed to prove 1:1 coherence. The existing v1/v2 manifest wire grammar is predecessor truth and is not redesigned here.

`play.run_manifest.run_id` may enforce a 1:1 FK to `play.run` inside the Play schema. AS3 does **not** require a SQL FK from Play into Content; the Play service must validate the stable Content revision identity through a Content-owned transactional admission seam. No SQL FK to DungeonMind is ever permitted.

### 2.4 Current Start Run protocol should survive

The UI currently performs:

```text
PUT /play-runs/{run_id}
PUT /play-runs/{run_id}/reference-manifest
```

AS3 does **not** require a UI protocol rewrite.

Required interpretation after switch:

```text
PUT Run
  → transaction validates committed Runbook revision
  → derives manifest
  → inserts Run + manifest
  → COMMIT

PUT manifest
  → idempotently return/prove the already-sealed manifest
  → never create a missing manifest as an independent second write
```

If a database Run exists without a manifest after switch, that is an integrity failure, not an invitation for the second endpoint to repair it silently.

### 2.5 Parallel lane

At dispatch, open PR #644 is CUTOVER design-only (`HANDOFF-CUTOVER-mounted-first-world-authority-migration.md`). Its current one-file design lease is disjoint from AS3.

Re-check active PRs immediately before implementation. If the later D.2C2 implementation acquires an AS3 path, serialize that path explicitly. APP-STATE owns Buddy Runtime only; CUTOVER owns World authority.

---

## §3 Required observable behavior and contracts

### 3.1 Add the Play schema with one forward migration

Create one new forward Buddy Alembic revision after the AS2 head. Do not rewrite `20260825_0001` or `20260825_0002`.

AS3 creates only:

```text
play.run
play.run_manifest
```

Do **not** create:

```text
play.active_run
play.run_mutation
play.rebase_intent
combat.*
ingest.*
assets.*
```

No app boot migration. Existing explicit migration-head behavior remains.

### 3.2 Introduce a Play-owned persistence package

Preferred shape:

```text
src/application_state/play/
  __init__.py
  types.py
  repository.py
  service.py
  import_runtime.py
```

Responsibilities:

- repository owns SQL for `play.*` only and never commits;
- service owns Run/manifest transaction invariants;
- import module owns explicit pre-switch legacy capture/adoption;
- existing FastAPI service modules remain public compatibility/domain adapters where useful;
- existing Pydantic/wire schemas may be reused rather than churned merely to move persistence.

Do not create a generic `application_state.store_json()` abstraction.

### 3.3 Content-owned transactional Playable admission

Run create/rebase needs the same Buddy database transaction to prove the exact Runbook WorkRevision. Do not make the Play repository query Content tables ad hoc and do not open a second independent Content transaction that can race the Play write.

Add a small Content-owned transaction-compatible admission seam, conceptually:

```text
admit_playable_revision(
  conn,
  work_object_id,
  revision_n,
  expected_sha256,
  require_current=bool,
  require_clean=bool,
)
```

It must preserve AS2 rules:

- `kind=runbook`;
- active WorkObject;
- exact `WorkRevision.revision_n + sha`;
- historical revisions are allowed for an existing Run/rebase target as specified;
- new Run creation requires the current committed revision and no divergent WorkingCopy;
- returned Markdown is immutable committed bytes, never WorkingCopy.

The exact module/function spelling may differ, but Content owns this boundary and Play uses it inside the shared UoW.

### 3.4 Run create + manifest seal is one transaction

Required sequence:

```text
BEGIN
  admit current clean Runbook WorkRevision matching request revision + sha
  derive/validate v1 or v2 reference manifest from those exact bytes
  INSERT play.run
  INSERT play.run_manifest
COMMIT
```

Failure deriving or validating the manifest writes **neither** row.

Create replay:

- same `run_id` + same Playable binding + coherent stored manifest → return existing Run;
- same `run_id` + different binding → 409;
- existing Run with missing/mismatched manifest → integrity failure (500), not repair;
- unknown DB outcome may be reconciled by GET/replay using the same UUID.

No observable database state may contain a READY-capable Run without its required manifest.

### 3.5 Manifest get/seal compatibility

After switch:

- GET manifest reads `play.run_manifest`;
- PUT manifest validates/replays the already-sealed row and returns it;
- PUT manifest does not independently derive and persist a manifest;
- Run/manifest binding mismatch is integrity failure;
- existing public response shape remains compatible with current Play UI/tests unless evidence forces a re-brief.

### 3.6 Run list/get are DB authority

`list_play_runs()` and `get_play_run()` read only PostgreSQL after the switch.

Preserve current filtering/order semantics:

- campaign filter;
- Playable artifact filter;
- deterministic current ordering;
- persisted progress is revalidated against the sealed manifest before being returned when current service semantics require it.

Database unavailable → named fail-closed failure. Do not inspect `out/runtime/play/runs` as fallback.

### 3.7 Progress replacement is SQL CAS

Use the accepted CAS posture:

```text
UPDATE play.run
SET progress = $canonical_progress,
    run_revision = run_revision + 1,
    updated_at = now()
WHERE run_id = $run_id
  AND run_revision = $expected
RETURNING *
```

Before the update, validate the proposed progress against the sealed manifest in the same transaction.

Required outcomes:

- exactly one of two writers using the same expected revision succeeds;
- the loser receives 409 with no partial write;
- exact replay of a completed update may no-op only when stored `run_revision == expected + 1` **and** canonical stored progress equals the requested progress;
- stale request with changed progress → 409;
- do not create `play.run_mutation` or event sourcing.

### 3.8 Rebase is one transaction; rebase intents are no longer Runtime authority

Preserve existing Play rebase semantics: same artifact, exact target committed revision, grammar compatibility, preserve-only Runtime admission, no silent semantic repair.

Required transaction:

```text
BEGIN
  SELECT play.run FOR UPDATE
    WHERE run_id + expected run_revision match
  load/prove existing manifest
  admit exact target WorkRevision + sha
  derive/validate target manifest
  prove current Runtime references survive target manifest
  UPDATE Run binding + run_revision + rebased_from_run_revision
  REPLACE manifest row
COMMIT
```

Crash before COMMIT → previous Run + previous manifest unchanged.

After switch:

- ordinary rebase creates **no** `out/runtime/play/rebase-intents/*` file;
- ordinary Run reads do not inspect pending rebase-intent files;
- no durable SQL `rebase_intent` row exists;
- exact successful replay may return the already-rebased aggregate only when the expected source revision, target binding, and stored manifest prove it is the same operation;
- changed/stale target → 409.

The legacy intent/recovery code may remain temporarily for explicit pre-switch migration recovery and AS5 deletion, but it is not switched Runtime authority.

### 3.9 Honest legacy Runtime adoption

AS3 import must adopt a **coherent Run aggregate**, not independent files.

Pre-switch procedure:

```text
1. inventory legacy Run files
2. recover/finish every pending legacy rebase intent using the existing protocol
3. require no unresolved rebase intents remain
4. ensure each Run has a valid sealed manifest under legacy authority
5. capture Run JSON + matching manifest together under the predecessor lock ordering
6. import that exact pair transactionally
7. verify identity/binding/progress/manifest/timestamps/revision
8. only then switch ordinary Runtime authority
```

Import mapping:

| Legacy | PostgreSQL |
|---|---|
| Run file UUID | exact `run_id` |
| campaign | exact `campaign_id` |
| Playable artifact/revision/sha | exact Play binding + AS2 WorkRevision identity |
| `run_revision` | exact integer |
| progress | exact canonical `PlayRunProgress` JSONB |
| `rebased_from_run_revision` | exact nullable value |
| timestamps | preserve |
| sealed manifest | exact validated manifest JSON + binding |

Import replay of the same pair is a no-op success. Same `run_id` with different binding/progress/manifest is conflict and stops the switch.

Do not import `active-run.json` into SQL in AS3. If an active pointer exists, migration verification must prove it references a successfully imported Run so current resume behavior continues while the pointer remains file-backed.

### 3.10 Switch semantics — no file fallback

After AS3 switch, ordinary product operations must succeed with these paths absent or unreadable:

```text
out/runtime/play/runs/
out/runtime/play/reference-manifests/
out/runtime/play/rebase-intents/
```

Explicit legacy import tooling may read those paths before switch. Runtime may not.

`out/runtime/play/active-run.json` remains readable/writable and keeps its file lock until AS4.

AS3 is therefore allowed to leave old helper modules physically present for AS5, but their Run/manifest/rebase-intent persistence paths must no longer be product authority.

### 3.11 Preserve current UI/API contract unless forced

Do not deepen BF2/BF3 or redesign Play Surface in this PR.

The current Start Run state machine should remain valid:

```text
create Run
→ seal/replay manifest
→ READY
```

AS3 changes the server transaction behind those calls, not the user interaction. UI source edits are a stop/re-brief unless a narrow compatibility change is genuinely required by an unavoidable public contract correction.

### 3.12 What remains false after AS3

Still false and explicitly out of scope:

```text
active Run pointer in PostgreSQL       → AS4
resume/reload continuity acceptance    → AS4
physical deletion of replaced Play persistence modules/locks → AS5
Combat PostgreSQL                      → later Combat slice
BF2/BF3 cockpit deepening              → after persistence gate
Run mutation/audit history             → not authorized
World Graph changes                     → CUTOVER only
```

---

## §4 Implementation write lease

Only the paths below plus bounded-discovery allowances are leased to the AS3 implementation PR.

### 4.1 Application-state / Play domain

| Action | Path | Purpose |
|---|---|---|
| Create | `src/application_state/play/__init__.py` | Play persistence exports |
| Create | `src/application_state/play/types.py` | storage/domain transfer types if required; do not redefine public grammar |
| Create | `src/application_state/play/repository.py` | SQL for `play.run` / `play.run_manifest` |
| Create | `src/application_state/play/service.py` | create+manifest, list/get, CAS progress, transactional rebase |
| Create | `src/application_state/play/import_runtime.py` | explicit coherent legacy Runtime adoption |
| Create | `src/application_state/migrations/versions/*.py` | one forward AS3 migration creating `play` schema/tables |

### 4.2 Content transaction seam

| Action | Path | Purpose |
|---|---|---|
| Create | `src/application_state/content/playable_admission.py` | Content-owned UoW-compatible exact Runbook revision admission |
| Modify if required | `src/application_state/content/__init__.py` | bounded export only |

Do not broadly refactor AS2 Content services/repository unless the transaction seam proves impossible in this shape. A required wider Content production edit is a stop/re-brief.

### 4.3 Existing Play adapters

| Action | Path | Purpose |
|---|---|---|
| Modify | `apps/live_control_server/services/play_run_registry.py` | preserve public Run models/API while delegating durable authority to Play service |
| Modify | `apps/live_control_server/services/play_run_reference_manifest.py` | keep grammar/derivation; DB manifest get/replay; no sidecar authority |
| Modify | `apps/live_control_server/services/play_run_rebase.py` | delegate switched rebase to transaction; retain only explicitly needed legacy-import recovery seams |
| Modify if required | `apps/live_control_server/routes/play_runs.py` | error/compatibility wiring only; route shapes should remain stable |

`play_active_run.py`, `registry_file_lock.py`, and `src/live_play/live_store.py` are **not** general AS3 write leases. They remain required by unswitched state. If production changes there are truly required, stop and re-brief rather than turning AS3 into AS5.

### 4.4 Tests

Create/modify:

```text
tests/application_state/test_play_runtime_postgres.py
tests/application_state/test_play_runtime_existing_state_import.py
tests/application_state/test_play_runtime_rebase_transaction.py

tests/test_play_run_registry.py
tests/test_play_run_reference_manifest.py
tests/test_play_run_rebase.py
tests/test_play_run_progress.py
tests/test_play_run_registry_integrity.py
tests/test_live_play_runs.py
tests/test_live_play_run_reference_manifest.py
tests/test_live_play_run_rebase.py
tests/test_live_play_run_progress.py
```

The authority switch is expected to change these regression assumptions, so they are explicitly leased rather than discovered late.

### 4.5 State authorities carried atomically in the implementation PR

Modify:

```text
Docs/Roadmaps/ROADMAP-application-state.md
Docs/Plans/STEWARDS-ANCHOR-application-state.md
```

Required backward-looking truth:

- AS2 = DONE — PR #643 merge `b4d63daa…`, accepted head `6b1c2e77…`, 3 cycles, PASS-equivalent review `5024971680`;
- AS3 = THIS PR / not merged;
- AS4 remains false.

Do not pre-claim the AS3 merge SHA or AS4 dispatch.

### 4.6 Bounded discovery

Allowed without re-brief:

- up to **8** additional tests under `tests/application_state/**`;
- up to **8** additional existing Play-only tests whose assumptions directly depend on Run/manifest/rebase persistence;
- exactly **one** new AS3 Alembic revision;
- small test-only helpers under `tests/application_state/**`.

Production path outside §4 is a stop report, not an invitation to edit it silently.

---

## §5 Explicitly out of scope

Do not bundle:

- `play.active_run` table or active-run pointer switch (AS4);
- deletion of `play_active_run.py`, `registry_file_lock.py`, `live_store.py`, or all old Play code (AS5);
- Combat persistence or Play→Combat wire redesign;
- Beat/Scene/Choice/Option relational tables;
- Playable grammar changes or BF2/BF3 cockpit work;
- `play.run_mutation`, event sourcing, audit-log infrastructure;
- user/account/multi-operator semantics;
- Ingest, Asset, SourceArtifact, Statblock, Card, Location, NPC, Shop schemas;
- DungeonMind/CUTOVER World changes;
- Docker/compose changes unless a concrete environment fact invalidates the existing shared-server/different-database posture;
- new permanent file fallback/environment toggle;
- corpus/path identity changes unrelated to Play Runtime.

---

## §6 Required adversarial sequences

At minimum prove:

```text
CREATE ATOMICITY
manifest derivation fails
→ no play.run row
→ no play.run_manifest row

crash/exception after Run insert but before manifest insert/COMMIT
→ transaction rolls back
→ neither row

CREATE REPLAY
same run_id + same exact binding
→ same Run + same manifest
→ no duplicate semantic aggregate

different binding on same run_id
→ 409

PROGRESS CAS
two writers use expected run_revision N
→ exactly one succeeds to N+1
→ other 409

exact retry of successful progress request
→ no-op success only at N+1 with equal canonical progress

stale request with changed progress
→ 409

REBASE ATOMICITY
failure before COMMIT after target validation
→ old Run binding + old manifest remain
→ no rebase intent file

successful rebase
→ Run binding + manifest both move atomically
→ run_revision increments once
→ rebased_from_run_revision records source

rebase exact replay
→ no duplicate mutation

LEGACY IMPORT
pending legacy rebase intent exists
→ recover fully before capture OR stop import
→ never import half-rebased pair

same frozen Run+manifest imported twice
→ second no-op

same run_id with changed binding/progress/manifest
→ fail closed

SWITCH
remove/make unreadable legacy runs + manifests + rebase-intents paths
→ list/get/progress/rebase still work from PostgreSQL
→ no file fallback

ACTIVE POINTER COMPATIBILITY
existing active-run.json points to imported Run
→ active pointer remains readable
→ referenced Run + manifest resolve from PostgreSQL
→ pointer itself remains file-backed
```

---

## §7 Required evidence before review handback

### 7.1 Real PostgreSQL owning-boundary evidence

Use the existing disposable Buddy PostgreSQL fixture. Required tests must **fail**, not skip, when PostgreSQL is unavailable.

At minimum run:

```bash
uv run pytest \
  tests/application_state/test_play_runtime_postgres.py \
  tests/application_state/test_play_runtime_existing_state_import.py \
  tests/application_state/test_play_runtime_rebase_transaction.py \
  -rs -s --tb=short

uv run pytest tests/application_state -q
```

### 7.2 Relevant Play regression surface

Run the existing Play server/service suites affected by the switch, including at least the explicitly leased tests in §4.4. Report exact pass/skip counts. Zero required skips.

Also run the existing Start Run UI state-machine tests without changing the UI unless re-briefed:

```bash
pnpm --dir apps/live-control-ui exec vitest run \
  src/playSurface/startRunAttempt.test.ts
```

The important compatibility witness is that create→manifest still reaches READY even though create now persisted both rows atomically.

### 7.3 File-absence dogfood witness

With imported/new PostgreSQL Runtime present:

```text
1. Start a Run.
2. Confirm Run + manifest via API.
3. Make legacy Run/manifest/rebase-intent directories absent or inaccessible.
4. Reload Run list/get.
5. Replace progress.
6. Rebase to a newer compatible Runbook revision.
7. Reload again.
Expected: exact behavior survives; no old Runtime path is recreated/read.
```

Keep `active-run.json` available for this AS3 witness because AS4 has not switched it.

### 7.4 Migration witness

Use a fixture representing real pre-AS3 state:

```text
legacy Run JSON
+ sealed manifest
+ pinned AS2 WorkRevision
(+ optional active-run pointer)
```

Import, restart the service boundary, then prove exact IDs/revisions/digests/progress/manifest survive. Include an already-rebased Run and a pending-intent precondition case.

### 7.5 Latency measurements

Architecture §15 makes these AS3 measurements mandatory:

- Runtime CAS mutation;
- Start Run + seal manifest.

Capture **baseline file-backed behavior at base `b4d63daa…`** and PostgreSQL head in comparable environment. Prefer repeated samples with p50/p95 (for example 30+ operations) rather than one anecdotal timing. Report the values as measurements, not gates.

Architecture hypotheses are:

```text
Runtime CAS mutation owning-boundary p95: 50 ms
Start Run + seal manifest owning-boundary p95: 250 ms
```

A result over hypothesis is not automatically a review failure; hiding or failing to measure it is.

### 7.6 Lease / hygiene

```bash
git diff --check
git diff --name-only b4d63daab3eeb8150ca73fe9492d7a3d8744a4e0...HEAD
```

Hand back the exact cumulative changed-path set and identify every bounded-discovery path.

---

## §8 Suggested nano-commit story

Prefer independently reviewable commits:

```text
1. play schema + repository + transaction-compatible Content admission
2. Run create/get/list + atomic manifest seal
3. progress SQL CAS + replay semantics
4. transactional preserve-only rebase; switched Runtime stops using intent files
5. coherent legacy Run+manifest import + switch/fail-closed behavior
6. adversarial real-Postgres + regression + file-absence evidence
7. atomic roadmap/anchor predecessor sync
```

Do not mix AS4 active-run migration into the final commit because it appears nearby.

---

## §9 Review handback contract

The implementation agent should return:

1. exact PR / branch / head SHA;
2. Review Cycle 1 starting point;
3. invariant disposition against §1 and each §3 contract;
4. changed paths vs §4 lease and bounded-discovery ledger;
5. nano-commit story;
6. exact migration revision and final `play.run` / `play.run_manifest` schema;
7. explanation of the Content-owned transaction admission seam;
8. create+manifest atomicity evidence, including forced rollback;
9. progress CAS + exact replay evidence;
10. rebase atomicity + no-intent-file evidence;
11. legacy recovery/capture/import evidence and idempotency/conflict behavior;
12. file-absence/no-fallback witness;
13. existing active-run pointer compatibility witness;
14. relevant Python + UI regression results and skip counts;
15. baseline-vs-head Runtime mutation and Start+seal latency evidence;
16. `git diff --check` + exact lease output;
17. parallel CUTOVER collision check;
18. state-authority sync showing AS2 DONE, AS3 this PR, AS4 false;
19. explicit list of stop conditions encountered or `none`.

Review is exact-head. Count review cycles by distinct reviewed PR heads. Same-account GitHub review restrictions may require `COMMENT` with `PASS-equivalent` / `REQUEST-CHANGES-equivalent` wording.

---

## §10 Stop conditions

Stop and report rather than broadening if implementation appears to require:

- `play.active_run` or migration of `active-run.json`;
- physical deletion/refactor of all Play file-lock/live-store infrastructure;
- Combat persistence or Combat schema changes;
- UI/Start Run workflow redesign rather than compatible server semantics;
- Beat/Scene/Decision persistence normalization;
- mutation/audit/event history;
- a durable rebase-intent SQL concept;
- Runbook/Content schema redesign beyond the transaction admission seam;
- a production path outside §4 that cannot be avoided;
- an environment/file fallback for switched Runtime;
- Docker/compose changes without a concrete contradiction of current deployment posture;
- any DungeonMind World Graph table/join/FK;
- AS4/AS5 state claims before AS3 acceptance.

If the existing manifest parser/domain model cannot be reused without a broad refactor, stop and re-brief rather than using persistence migration as cover for a Play grammar rewrite.

---

## §11 What remains false after merge

Even a successful AS3 does **not** mean Play persistence is finished.

```text
AS2   PLAYABLE            DONE — #643
AS3   PLAY RUNTIME        this PR
AS4   PLAY CONTINUITY     still false — active-run pointer + resume/reload acceptance
AS5   PLAY DEMOLITION     still false — physical deletion of replaced Play persistence machinery
```

After AS3 merges, the next steward re-anchor must record the actual merge SHA + accepted head + distinct review-cycle count before dispatching AS4. Do not pre-authorize AS4 implementation inside this PR.
