---
pr_body_template: |
  ## Handoff pointer
  - Workstream: APP-STATE / AS4 — Play continuity on PostgreSQL
  - Flow: APP-STATE
  - Direction: CODE → REVIEW
  - Handoff: Docs/Plans/HANDOFF-APP-STATE-play-continuity-postgres.md
  - Implementation repository: Drakosfire/DungeonMindBuddy

  ## Verification pointer
  - Architecture: Docs/Design/ARCHITECTURE-application-state-layer.md v1.1
  - Play authority: Docs/Design/ARCHITECTURE-playable-material-and-runtime.md v1.1
  - Product predecessor: Docs/Plans/HANDOFF-PLAY-SURFACE-active-run-continuity.md
  - Predecessor: AS3 PR #646 merge 9c946cd8c24effccec8d06cfc1cb5e310c9edc5e
  - Accepted predecessor head: 913cfe0bbce4db27250afd8277e3af50712ee029
  - Predecessor review: 3 distinct-head cycles; final PASS-equivalent review 5026608908
  - Predecessor exact-head evidence: PR #646 comment 5420273265
  - Production consumer: bare /play resume + exact-Run open + active selection GET/PUT

  The checked-in handoff, cumulative diff, nano-commit story, and independently
  rerun evidence are the review contract. This body is transport metadata.
---

# HANDOFF — AS4: Play Continuity on PostgreSQL

**Created:** 2026-08-25  
**Status:** READY — next APP-STATE implementation slice  
**Canonical handoff path:** `Docs/Plans/HANDOFF-APP-STATE-play-continuity-postgres.md`  
**Workstream / flow:** `APP-STATE`  
**Direction:** CODE → REVIEW  
**Implementation repository:** `Drakosfire/DungeonMindBuddy`  
**Exact implementation base:** `9c946cd8c24effccec8d06cfc1cb5e310c9edc5e` — merge of PR #646  
**AS3 accepted head:** `913cfe0bbce4db27250afd8277e3af50712ee029`  
**AS3 review:** 3 distinct-head review cycles; final PASS-equivalent review `5026608908`  
**AS3 exact-head evidence:** PR #646 comment `5420273265` — real-PostgreSQL owning-boundary `28 passed`; full APP-STATE `72 passed, 0 skipped`; leased Play regressions `71 + 60 passed, 0 skipped`; Start Run UI `14 passed`; clean `git diff --check`  
**Suggested branch:** `agent/app-state-play-continuity`  
**Suggested PR title:** `APP-STATE: persist active Run continuity`  
**Named successor:** AS5 — Play persistence demolition — remains false until AS4 merges  

> Repository law: [`AGENTS.md`](../../AGENTS.md). Steward process: [`../Process/STEWARD-CYCLE.md`](../Process/STEWARD-CYCLE.md). Application-state authority: [`../Design/ARCHITECTURE-application-state-layer.md`](../Design/ARCHITECTURE-application-state-layer.md). Play authority: [`../Design/ARCHITECTURE-playable-material-and-runtime.md`](../Design/ARCHITECTURE-playable-material-and-runtime.md). Historical product contract: [`HANDOFF-PLAY-SURFACE-active-run-continuity.md`](HANDOFF-PLAY-SURFACE-active-run-continuity.md).

---

## §1 Mission and merge-ready invariant

**Mission:** Move Play's durable active-Run selection from `out/runtime/play/active-run.json` into the Buddy Application State PostgreSQL database so ordinary `/play` re-entry survives backend restart, checkout/worktree changes, and missing legacy Play files while still resuming the exact Run the GM explicitly selected.

**Merge-ready invariant:**

> **After AS4, `play.active_run` is the sole durable authority for the local operator's active Play Run. A missing row means no active selection. Setting an active Run first proves that exact PostgreSQL Run + sealed manifest aggregate is coherent, then records only `run_id + selected_at`; selecting the already-active Run is idempotent and does not churn `selected_at`; selecting a different valid Run is last-explicit-selection-wins. Bare `/play` reads this PostgreSQL selection and then follows the existing exact Run + manifest + pinned WorkRevision admission path — the pointer never makes an invalid Run valid, never chooses latest/first, and never allocates a Run. Explicit chooser mode still bypasses automatic resume, and Start New never clears the prior active selection before a replacement reaches READY. Ordinary active-Run reads/writes never read or write `active-run.json` after the switch; DB unavailable fails closed without file fallback. Physical deletion of the replaced Play file/lock modules remains AS5.**

Target transition:

```text
AS3
play.run + play.run_manifest       PostgreSQL authority
active-run.json                    file authority
        ↓
/play
  → read file pointer
  → load exact Run
  → load manifest
  → load pinned WorkRevision
  → READY / truthful block

AS4
play.run + play.run_manifest       PostgreSQL authority
play.active_run                    PostgreSQL authority
        ↓
/play
  → read DB pointer
  → load exact Run
  → load manifest
  → load pinned WorkRevision
  → READY / truthful block
```

### Pre-dispatch critique

| Question | Frozen answer |
|---|---|
| Most likely false-positive implementation | Add `play.active_run`, but leave `get_play_active_run()` reading the file first or as fallback. That is not a switch. |
| Most dangerous semantic regression | Treat the active pointer as Run validity and skip exact Run/manifest/WorkRevision admission on `/play`. The pointer records operator intent only. |
| Most dangerous UX regression | Clear the old active Run when the user clicks `Start New Run`, so a failed/blocked new start destroys ordinary resume. Preserve the current READY-first replacement rule. |
| Most dangerous migration trap | Import the pointer before AS3 Runs exist, or silently overwrite a conflicting DB selection. Import only after the referenced Run is present and coherent; conflicting durable state is a stop. |
| Most dangerous identity trap | Add campaign path, checkout root, browser id, DB row id, or account-shaped fields as product identity. Current product semantics are one local-operator active selection; do not invent multi-user/account architecture. |
| Most dangerous cleanup trap | Delete `play_active_run.py`, registry locking, or all `out/runtime/play` helpers here. AS4 switches the active pointer. AS5 proves and performs demolition of replaced Play filesystem machinery. |
| Performance trap | Hide the AS3 Runtime CAS measurement because it exceeded the original 50 ms hypothesis. AS4 records continuity/resume measurements honestly; performance hypotheses are evidence, not license to weaken correctness. |

---

## §2 Re-anchored authority and lane

### 2.1 Accepted predecessor truth

AS3 / PR #646 is merged at:

```text
merge:         9c946cd8c24effccec8d06cfc1cb5e310c9edc5e
accepted head: 913cfe0bbce4db27250afd8277e3af50712ee029
review cycles: 3 distinct heads
final review:  5026608908 PASS-equivalent
exact evidence: PR #646 comment 5420273265
```

AS3 established:

- `play.run` as the sole ordinary Run binding + mutable Runtime authority;
- `play.run_manifest` as the sole ordinary sealed-manifest authority;
- Run create + manifest seal in one PostgreSQL transaction;
- SQL `run_revision` CAS;
- preserve-only rebase as one PostgreSQL transaction;
- no ordinary Run/manifest/rebase fallback to legacy Run files, manifest sidecars, or rebase-intent files;
- coherent legacy Run + manifest import;
- existing `active-run.json` deliberately remained file-backed and was only verified as referencing an imported Run.

Do not reopen AS3's aggregate model in AS4.

### 2.2 Current active-selection authority

At the exact AS4 base, `apps/live_control_server/services/play_active_run.py` owns:

```text
out/runtime/play/active-run.json

PlayActiveRunState
  schema_version = dmb_play_active_run_v1
  run_id: canonical UUID | null
  selected_at: UTC timestamp | null
```

Current behavior worth preserving:

- missing file → normal null state;
- malformed persisted file → fail closed;
- setting requires a canonical UUID and an existing coherent Run/manifest;
- selecting the same exact Run is idempotent and preserves `selected_at`;
- selecting a different valid Run replaces the pointer;
- the file duplicates no progress, Playable bytes, manifest bytes, campaign truth, or lifecycle state.

The current Play UI already implements the desired product state machine:

```text
/play?choose=1
  → explicit chooser
  → do not auto-resume

/play?run=<uuid>
  → exact Run + manifest + pinned committed WorkRevision admission
  → only after READY, persist that exact Run as active

/play
  → read active selection
  → if none, explicit chooser
  → if present, replace URL with exact ?run=<uuid>
  → run the same exact admission path

Start New Run
  → enter chooser/start mode
  → prior active selection remains intact
  → a new Run replaces it only after normal READY admission
```

AS4 changes the persistence boundary underneath this behavior. It does not redesign it.

### 2.3 Application-state architecture already freezes the target

The accepted Application State architecture classifies Play active Run as Play-owned durable continuity state and names its target disposition:

```text
play.active_run
  singleton for the current local operator context
  → run_id references play.run inside the Play schema
  → selected_at records last explicit successful selection
```

Do not introduce:

- account/user/team tables;
- browser/session identifiers;
- per-worktree or filesystem-root identity;
- a campaign-scoped list of active Runs;
- a generic key/value preference table;
- CAS/version history for this pointer;
- Run lifecycle (`active/completed/abandoned`) fields.

There is one current product question: **which exact existing Run should ordinary Play entry resume?** Preserve that question exactly.

### 2.4 Parallel lane

At dispatch, open PR #647 is CUTOVER D.3 design-only and changes only:

```text
Docs/Plans/HANDOFF-CUTOVER-buddy-graph-engine-demolition.md
```

It is disjoint from AS4. Re-check active PR paths immediately before implementation. If a later D.3 implementation acquires an AS4 production/doc path, serialize that path explicitly. APP-STATE owns Buddy Play continuity; CUTOVER owns removal of Buddy World Graph authority.

---

## §3 Required observable behavior and contracts

### 3.1 Add one forward migration only

Create the next Buddy Alembic revision after `20260825_0003_play_runtime.py`.

Expected migration:

```text
src/application_state/migrations/versions/20260825_0004_play_active_run.py
```

AS4 creates only:

```text
play.active_run
```

Recommended physical shape:

```text
play.active_run
  scope_key TEXT PRIMARY KEY
    CHECK (scope_key = 'local')
  run_id UUID NOT NULL
    REFERENCES play.run(run_id)
  selected_at TIMESTAMPTZ NOT NULL
```

Rules:

- exactly zero or one row may represent the current local selection;
- missing row = `run_id: null, selected_at: null` at the public adapter;
- `scope_key='local'` is a persistence singleton key, not user-facing identity;
- the FK is inside the Play schema and is allowed;
- do not add SQL FK to Content or DungeonMind;
- do not add `schema_version` to the table merely because the HTTP model has one;
- do not use `ON DELETE CASCADE` to silently clear operator intent if Run lifecycle later changes — future Run deletion must address active continuity deliberately;
- ordinary application boot still verifies migration head and never auto-upgrades.

Do not modify already-applied `20260825_0001`, `0002`, or `0003` migrations.

### 3.2 Extend the existing Play domain package, not a new subsystem

Use the AS3 Play package:

```text
src/application_state/play/
  types.py
  repository.py
  service.py
```

Conceptual durable type:

```text
PlayActiveRun
  run_id: UUID
  selected_at: datetime
```

The public `PlayActiveRunState` wire type may remain in the existing server compatibility adapter. The DB model should not absorb wire-only `schema_version` or null-pair representation; absence is represented by no row.

Repository responsibilities:

- get singleton row;
- set/upsert singleton row;
- clear/delete singleton row if the domain clear operation is implemented;
- never commit;
- SQL only inside `play.*`.

Service responsibilities:

- transaction/UoW;
- exact Run aggregate integrity before set;
- idempotent same-Run semantics;
- last-explicit-selection-wins different-Run semantics;
- DB unavailable/integrity error behavior;
- no legacy-file reads.

Do not create a generic preferences/settings repository.

### 3.3 GET active Run is PostgreSQL authority

After switch:

```text
GET /api/live/play-active-run
```

keeps the existing response contract:

```json
{
  "schema_version": "dmb_play_active_run_v1",
  "run_id": null,
  "selected_at": null
}
```

or the selected exact Run UUID + UTC timestamp.

Required behavior:

- no DB row → 200 null state;
- one valid DB row → 200 exact selection;
- malformed/impossible persisted DB state → integrity failure, never silent reset;
- DB unavailable → fail closed (normal application-state unavailable status), never read `active-run.json`;
- GET does not choose newest/first Run;
- GET does not allocate a Run;
- GET does not need to re-admit Content/Playable bytes. The client subsequently performs existing exact Run admission.

### 3.4 PUT active Run proves the existing Runtime aggregate, then records intent

Preserve the existing wire endpoint:

```text
PUT /api/live/play-active-run
body: { "run_id": "<canonical uuid>" }
```

Required transaction:

```text
BEGIN
  validate canonical UUID
  load/prove play.run + play.run_manifest aggregate
  require persisted manifest/progress integrity using AS3 owning seam
  read active singleton

  if same run_id:
    return existing selection unchanged
    selected_at does not churn

  else:
    insert/update singleton to run_id
    selected_at = current UTC time
COMMIT
```

Do **not** make active selection a second Run admission system. The set operation proves that the durable Run aggregate exists and is internally coherent; the Play surface still owns the full exact Run + manifest + pinned WorkRevision READY admission before it chooses to call PUT.

Required outcomes:

- noncanonical UUID → 422 before write;
- missing Run → 404;
- Run missing/incoherent manifest or corrupt persisted progress → fail closed with no pointer mutation;
- same Run retry → identical public state, including `selected_at`;
- different valid Run → new selected Run and new `selected_at`;
- two concurrent different valid selections require no CAS; the last successfully committed explicit selection is authoritative;
- no Run row/progress/manifest mutation occurs while changing the pointer.

### 3.5 Preserve the null/clear state without changing Start New semantics

The roadmap requires the owning boundary to prove set/get/clear semantics. Representing “clear” means deleting the singleton row, not writing a row whose `run_id` is null.

A small domain clear operation is allowed in AS4. If exposed over HTTP, use a narrow explicit operation (for example `DELETE /api/live/play-active-run`) returning the existing null-state wire shape. Do **not** add a new client/UI control unless product evidence requires it.

Regardless of whether the HTTP clear route is exposed:

- `Start New Run` must **not** clear active selection;
- entering `?choose=1` must **not** clear active selection;
- failed/blocked/incomplete new Run creation/admission must leave the prior active Run unchanged;
- clearing the pointer is not Run deletion, completion, abandonment, or lifecycle state.

If the implementation cannot satisfy the roadmap clear evidence without widening product behavior, stop and report rather than silently redefining Start New.

### 3.6 Preserve PlaySurfacePage behavior; prefer zero UI production changes

AS4 should be able to switch persistence without changing the existing UI protocol.

Current client calls already suffice:

```text
getPlayActiveRun()
putPlayActiveRun(run_id)
```

Preferred outcome:

- no production changes under `apps/live-control-ui/`;
- existing continuity tests become PostgreSQL-backed through the server switch;
- exact chooser/resume behavior remains byte-for-behavior compatible.

A production UI change is a stop-and-report condition unless it is strictly necessary to preserve the existing AS4 invariant. Do not use AS4 to deepen BF2/BF3 cockpit semantics.

### 3.7 Honest legacy `active-run.json` adoption

AS3 already proved that a pre-existing active pointer must reference a Run captured/imported into PostgreSQL. AS4 now adopts the pointer itself.

Explicit pre-switch import procedure:

```text
1. require AS3 play.run + run_manifest migration/import complete
2. inspect legacy active-run.json under the predecessor file lock
3. if file is absent:
     import no row
4. if file contains a valid null pair:
     import no row
5. if file contains run_id + selected_at:
     parse exact canonical UUID + UTC timestamp
     require referenced PostgreSQL Run aggregate exists and is coherent
     insert play.active_run with exact selected_at
6. verify stored row exactly matches captured pointer
7. only then switch ordinary active-Run authority
```

Import replay:

- same captured pointer + same DB selection → no-op;
- absent/null legacy pointer + no DB row → no-op;
- legacy pointer references missing/unreadable/incoherent Run → fail closed;
- DB row exists with a different Run or different preserved `selected_at` during import → conflict; do not overwrite;
- malformed legacy pointer → fail closed and leave DB state unchanged;
- do not infer selection from Run ordering when no pointer exists.

Migration tooling is the **only** AS4 code permitted to read `active-run.json` after the new service exists.

### 3.8 Authority switch: legacy file may remain, but must become irrelevant

After switch, prove all of these:

```text
legacy active-run.json absent
  → bare /play still resumes DB-selected Run

legacy active-run.json unreadable
  → GET/PUT active Run still operate from PostgreSQL

legacy active-run.json contains a different valid UUID
  → GET returns PostgreSQL selection
  → ordinary /play resumes PostgreSQL selection
  → no reconciliation/fallback occurs
```

Do not delete the file/module merely to prove this. AS5 owns physical demolition.

`play_active_run_path()` may remain temporarily for explicit migration/tests and AS5 inventory, but no ordinary production read/write may call it after the switch.

### 3.9 Restart / worktree continuity is the product proof

AS4 is independently useful only if it closes the checkout-local continuity defect.

Required witness:

```text
shared Buddy PostgreSQL

repo root/worktree A
  Run X exists in play.run
  set active Run X
  no active-run.json needed

backend process ends

repo root/worktree B
  same application-state DSN
  legacy out/runtime/play directory absent/unreadable
  GET active Run → X
  GET Run + manifest → exact X
  GET pinned WorkRevision → exact bound revision
  native Play admission → READY
  current Runtime progress → exactly the stored run_revision/progress
```

Do not call “server restart” a test that merely reuses an in-memory service object. Recreate the app/service boundary and prove the selection from PostgreSQL.

### 3.10 Resume must preserve exact current moment

The active pointer stores only Run identity. Exact current moment remains owned by `play.run.progress` and the sealed manifest/Playable revision.

Required acceptance after selection/restart:

- same `run_id`;
- same `run_revision`;
- same `current_beat_id`;
- same optional `current_scene_id`;
- same resolved beats;
- same durable selections;
- same notes;
- same Playable revision + content SHA;
- same manifest grammar/membership;
- no “latest Runbook” substitution;
- no Runtime canonicalization/repair during resume.

A valid pointer to a Run whose authoritative aggregate is corrupt must fail through normal exact admission. It must not select another Run automatically.

### 3.11 Failure posture

AS4 preserves the shared application-state failure rules:

- wrong/missing migration head → ordinary boot/service use fails; no auto-upgrade;
- database unavailable → fail closed; no active-run file fallback;
- missing selection → normal null state, not error;
- malformed DB row / impossible FK-integrity condition → named integrity failure;
- stale or conflicting legacy import → stop, not overwrite;
- no World Graph DSN fallback;
- no localStorage active-Run authority.

### 3.12 Latency evidence

Measure, do not tune prematurely.

Capture comparable predecessor-vs-head p50/p95, preferably 30+ samples, for:

```text
GET active selection
PUT different active selection
bare /play continuity admission (server-side equivalent if browser timing is noisy)
```

Use predecessor `9c946cd8…` file-backed active pointer versus AS4 PostgreSQL head in the same local environment where practical.

Record:

- p50;
- p95;
- max if useful;
- environment/sample count;
- whether the existing UI interaction still feels immediate.

Do not turn an architecture hypothesis into a hidden test threshold. AS3's Runtime CAS p95 was ~74 ms against a 50 ms hypothesis and was correctly reported as measurement rather than hidden.

---

## §4 Implementation write lease

The implementation PR may write only these production/migration/doc paths unless bounded discovery below is exercised:

```text
src/application_state/migrations/versions/20260825_0004_play_active_run.py
src/application_state/play/types.py
src/application_state/play/repository.py
src/application_state/play/service.py
src/application_state/play/import_active_run.py
src/application_state/play/__init__.py

apps/live_control_server/services/play_active_run.py
apps/live_control_server/routes/play_runs.py

Docs/Roadmaps/ROADMAP-application-state.md
Docs/Plans/STEWARDS-ANCHOR-application-state.md
```

Required/expected test paths:

```text
tests/application_state/test_play_active_run_postgres.py
tests/application_state/test_play_active_run_existing_state_import.py
tests/test_play_active_run.py
tests/test_live_play_active_run.py
apps/live-control-ui/src/App.test.tsx
apps/live-control-ui/src/api/liveApi.test.ts
```

Existing test helpers may be changed only if directly required to establish the owning-boundary fixtures:

```text
tests/application_state/play_runtime_helpers.py
```

### Bounded discovery

The agent may add at most:

```text
tests/application_state/          +3 directly relevant test/helper paths
apps/live-control-ui/src/         +2 test-only paths
src/application_state/migrations/versions/ +1 forward migration path only
```

Rules:

- test discovery is for direct evidence, not production expansion;
- a required **production** path outside the named lease is a stop-and-report/re-brief condition;
- do not quietly widen into AppChrome, Start Run state-machine redesign, Play Run schema changes, Content schema changes, or AS5 deletion.

### Backward-looking state-authority sync carried by this PR

Because #646 could not truthfully record its own merge before merge, AS4 must atomically synchronize current state while keeping AS4 itself unmerged:

```text
AS3
  DONE — PR #646 merge 9c946cd8c24effccec8d06cfc1cb5e310c9edc5e
  accepted head 913cfe0bbce4db27250afd8277e3af50712ee029
  3 distinct-head review cycles
  final PASS-equivalent review 5026608908
  exact-head evidence comment 5420273265

AS4
  THIS PR — do not claim merged

AS5
  still false / blocked on AS4
```

Update both current state authorities:

```text
Docs/Roadmaps/ROADMAP-application-state.md
Docs/Plans/STEWARDS-ANCHOR-application-state.md
```

Do not rewrite historical review-cycle counts or invent an AS4 merge SHA.

---

## §5 Explicitly out of scope / forbidden

Do not touch or claim:

- `play.run` / `play.run_manifest` model redesign;
- Beat / Scene / Decision / Option persistence redesign;
- Run mutation-history/event-sourcing tables;
- Run lifecycle (`active`, `completed`, `abandoned`) fields;
- account/user/team/operator identity systems;
- campaign-scoped multiple active pointers;
- browser/localStorage active authority;
- Content WorkObject / WorkRevision / WorkingCopy schema changes;
- `worldbuilding_source` migration;
- Combat persistence;
- Ingest / Source / Asset / generated-artifact schemas;
- DungeonMind schema or World Graph behavior;
- DungeonMindServer storage/CDN;
- BF2/BF3 cockpit deepening;
- AppChrome navigation redesign;
- physical deletion of Play Run/manifest/rebase/active file helpers;
- global `registry_file_lock.py` demolition;
- cleanup/deletion of production `out/runtime/play/**` user state;
- CUTOVER D.3 implementation;
- generic preference/KV/object tables;
- permanent feature toggle between file and DB active-Run authority.

AS4 is complete when **active selection authority switches**. AS5 exists specifically so AS4 does not disguise demolition as migration.

---

## §6 Required acceptance matrix

### 6.1 PostgreSQL active selection

Prove on a real disposable PostgreSQL database:

1. no row → public null state;
2. valid Run X → set persists X;
3. restart/new service instance → get returns X;
4. same-X retry → exact same state and `selected_at`;
5. valid Run Y → selection changes to Y; Runs/manifests unchanged;
6. clear operation (owning boundary) → row absent/null state;
7. set missing Run → fail, no row mutation;
8. set Run with corrupt/missing manifest → fail, no row mutation;
9. set Run with corrupt persisted progress → fail, no row mutation;
10. database unavailable → fail closed; no file fallback.

### 6.2 Honest legacy adoption

Prove:

1. pre-AS4 `active-run.json` selecting imported Run X + timestamp T → DB row X/T exactly;
2. rereun exact import → no-op;
3. absent file → no row, no inferred Run;
4. valid null-pair legacy file → no row;
5. malformed legacy file → no DB write;
6. pointer to Run absent from PostgreSQL → import failure;
7. pointer to incoherent PostgreSQL Run → import failure;
8. existing DB selection different from legacy pointer → conflict, no overwrite;
9. exact matching existing DB selection → no-op.

### 6.3 No legacy file authority after switch

With a valid DB selection:

1. delete/hide `out/runtime/play/active-run.json` → GET/PUT work;
2. make legacy active file directory unreadable → GET/PUT work;
3. write a contradictory legacy pointer to another Run → GET returns DB Run;
4. no ordinary code recreates the file;
5. no file lock is acquired for ordinary active GET/PUT.

### 6.4 Product continuity

Prove existing UI/state-machine behavior:

1. bare `/play` + no active row → chooser;
2. bare `/play` + active Run X → exact X admission;
3. `?choose=1` bypasses active X and shows chooser without clearing X;
4. explicit exact Run Y reaches READY → Y becomes active;
5. exact Run Y fails before READY → X remains active;
6. Start New enters chooser/start mode without clearing X;
7. successful new Run reaches READY → new Run becomes active;
8. backend restart + same DB → bare `/play` resumes same exact Run/current moment;
9. different repo root/worktree + same DB + no legacy Play files → same result;
10. active X whose authoritative Run aggregate becomes corrupt → fail truthfully; do not auto-select another Run.

### 6.5 AS3 regressions remain green

AS4 must not weaken:

- Run + manifest atomic create;
- historical Playable revision pinning;
- persisted-progress integrity;
- SQL Run CAS;
- transactional preserve-only rebase;
- cross-grammar rebase fail-closed;
- legacy Run/manifest import;
- Plan AS1 and Runbook AS2 isolation;
- no World DB usage.

---

## §7 Required execution evidence

No required test may skip because PostgreSQL is unavailable. Use the existing disposable product-safe database fixture/guard.

At minimum run and report exact counts for:

```bash
uv run pytest \
  tests/application_state/test_play_active_run_postgres.py \
  tests/application_state/test_play_active_run_existing_state_import.py \
  -rs -s --tb=short

uv run pytest tests/application_state -q

uv run pytest \
  tests/test_play_active_run.py \
  tests/test_live_play_active_run.py \
  tests/test_play_run_registry.py \
  tests/test_play_run_registry_integrity.py \
  tests/test_play_run_progress.py \
  tests/test_play_run_reference_manifest.py \
  tests/test_play_run_rebase.py \
  tests/test_live_play_runs.py \
  tests/test_live_play_run_reference_manifest.py \
  tests/test_live_play_run_progress.py \
  tests/test_live_play_run_rebase.py \
  -q

pnpm --dir apps/live-control-ui test -- \
  src/App.test.tsx \
  src/api/liveApi.test.ts

git diff --check

git diff --name-only 9c946cd8c24effccec8d06cfc1cb5e310c9edc5e...HEAD
```

Also attach concise exact-head evidence for:

- migration head before/after;
- DB row shape/invariants;
- restart/new-app-instance continuity;
- different-root/worktree continuity with same DB;
- contradictory legacy file ignored after switch;
- no legacy active file recreation;
- malformed legacy import no-write;
- same-Run idempotency preserving `selected_at`;
- failed replacement preserving previous selection;
- exact-current-moment resume;
- baseline-vs-head active GET/PUT/resume p50/p95;
- open-PR collision check;
- final cumulative lease ledger.

### Evidence quality rule

A test name is not evidence by itself. For the migration/continuity boundary, the witness must literally establish predecessor state **before** switching/import/restart, then exercise the real switched service/admission path.

Do not call a test “restart” if it simply calls the same in-memory object twice.

---

## §8 Preferred nano-commit story

Keep the PR reviewable as independent semantic steps:

```text
1. play.active_run forward migration + Play repository/type
2. PostgreSQL active-selection service invariants
3. honest legacy active-run import
4. switch existing play_active_run compatibility adapter/routes to DB authority
5. owning-boundary + migration + restart/worktree evidence
6. existing Play UI continuity regressions + latency capture
7. backward-looking AS3 roadmap/anchor sync
```

Do not mix unrelated formatting or cleanup into these commits.

---

## §9 Reviewer questions / exact invariant pass

A reviewer should answer all of these against the exact PR head:

1. Is `play.active_run` the only ordinary durable active-selection authority?
2. Can the legacy file be absent, unreadable, or contradictory without changing ordinary behavior?
3. Does missing row mean null selection without choosing another Run?
4. Does set prove the PostgreSQL Run + manifest aggregate before changing intent?
5. Can corrupt persisted progress/manifest be silently legitimized by selecting that Run?
6. Does same-Run retry preserve `selected_at` exactly?
7. Does a different explicit valid Run replace the pointer without mutating either Run?
8. Does bare `/play` still perform full exact admission rather than trusting the pointer?
9. Can `?choose=1` or Start New accidentally clear the prior active selection?
10. Can a failed new/exact Run admission displace the prior active Run?
11. Does restart/worktree continuity use the same DB rather than checkout-local files?
12. Does resume restore the exact stored Runtime/current moment and pinned Playable revision?
13. Is legacy import exact and conflict-safe rather than heuristic?
14. Did AS4 avoid account systems, campaign-multipointer semantics, lifecycle fields, and generic KV storage?
15. Are AS3 Runtime invariants still green?
16. Is AS5 still visibly false?
17. Does the cumulative diff stay inside the §4 write lease plus recorded bounded discovery?

Any “no” on 1–13 or 15–17 is a blocker.

---

## §10 Handback contract and what remains false

The implementation handback must include:

```text
Exact base
Exact head
Nano-commit list
Changed-path lease ledger
Bounded-discovery ledger, if used
Test commands + exact pass/skip counts
Real-PostgreSQL confirmation
Migration head
Legacy import witness
Restart/worktree witness
No-file/no-fallback witness
Latency baseline/head
Open PR collision check
Stop conditions encountered
What remains false
```

### What remains false after AS4

Even after a successful AS4 merge:

```text
legacy Play file modules/helpers       still physically present until AS5
legacy Run/manifest file code          may remain for migration/forensics until AS5
legacy rebase-intent code              may remain for migration/forensics until AS5
registry file-lock machinery           still exists for other file-backed domains
out/runtime/play filesystem state      not automatically deleted
Play demolition                        not AS4
Combat persistence                     unchanged
worldbuilding_source                   still file-backed
Ingest / Source / Asset schemas        not implemented
Generated artifact lifecycles          not selected by this PR
Run mutation history                   not implemented
multi-user/account active selection    not implemented
BF2/BF3 cockpit deepening              not bundled here
CUTOVER D.3                             separate lane
```

### What AS4 unlocks

After AS4, the APP-STATE Play-first migration has moved all user-relied-on Play continuity authority off checkout-local files:

```text
Plan / Runbook authoring      PostgreSQL
Playable historical revision PostgreSQL
Run + sealed manifest        PostgreSQL
Runtime CAS + rebase         PostgreSQL
active Run continuity        PostgreSQL
```

That removes application-state persistence as the reason BF2/BF3 Play Surface cockpit work was paused. The steward may then choose to resume Play Surface deepening in parallel with AS5 **only with disjoint write leases**.

AS5 remains necessary because switched authority is not the same thing as demolition. AS5 must prove Play operates with the replaced filesystem machinery physically absent and then delete it rather than preserving fallback topology.

---

## §11 Dispatch capsule

```text
PR: APP-STATE: persist active Run continuity
branch: agent/app-state-play-continuity
base: 9c946cd8c24effccec8d06cfc1cb5e310c9edc5e

Build exactly AS4:
- one play.active_run singleton
- missing row = no active selection
- exact Run+manifest integrity before set
- same-run idempotency preserves selected_at
- last explicit valid selection wins
- honest active-run.json import
- GET/PUT switch to PostgreSQL only
- bare /play exact resume survives restart/worktree
- no file fallback
- no UX/cockpit redesign
- no AS5 demolition
- carry AS3 DONE state sync into roadmap + steward anchor

Review from the checked-in handoff, not from this capsule.
```