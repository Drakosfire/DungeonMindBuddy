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
  - AS3 merge: PR #646 @ 9c946cd8c24effccec8d06cfc1cb5e310c9edc5e
  - AS3 accepted head: 913cfe0bbce4db27250afd8277e3af50712ee029
  - AS3 final review: 3 distinct-head cycles; PASS-equivalent 5026608908
  - AS3 exact-head evidence: PR #646 comment 5420273265
  - Post-AS3 state sync: PR #648 merge dd6c36abd3943f2a51ab2c69b8e789f005cc2b99
  - Production consumer: bare /play resume + exact-Run open + active selection GET/PUT

  Branch from current main containing this handoff. Record that exact branch/base SHA
  in the PR body and use it for the cumulative lease check. The checked-in handoff,
  actual PR-base diff, nano-commit story, and independently rerun evidence are the
  review contract.
---

# HANDOFF — AS4: Play Continuity on PostgreSQL

**Created:** 2026-08-25  
**Status:** DONE — PR #649 merge `993f837b6f2fc601acf2ae3a4b7926af1858ac6c`  
**Canonical handoff:** `Docs/Plans/HANDOFF-APP-STATE-play-continuity-postgres.md`  
**Workstream / flow:** `APP-STATE`  
**Implementation repository:** `Drakosfire/DungeonMindBuddy`  
**AS3 predecessor merge:** `9c946cd8c24effccec8d06cfc1cb5e310c9edc5e` — PR #646  
**AS3 accepted head:** `913cfe0bbce4db27250afd8277e3af50712ee029`  
**AS3 review:** 3 distinct-head cycles; final PASS-equivalent `5026608908`  
**AS3 exact-head evidence:** PR #646 comment `5420273265`  
**Post-AS3 state-sync merge:** `dd6c36abd3943f2a51ab2c69b8e789f005cc2b99` — PR #648  
**AS4 merge:** `993f837b6f2fc601acf2ae3a4b7926af1858ac6c` — PR #649  
**AS4 accepted head:** `be109c429460b6e22b0ded1c13e77dd0cc8e6b5e`  
**AS4 review:** 2 distinct-head review cycles; final PASS-equivalent `5033365385`  
**AS4 exact-head evidence:** PR #649 comment `5428663041`  
**Branching rule:** create the implementation branch from the current `main` that contains this handoff, record that exact SHA as the PR base, and review `PR_BASE...HEAD`; do not branch from the historical AS3 merge.  
**Suggested branch:** `agent/app-state-play-continuity`  
**Suggested PR title:** `APP-STATE: persist active Run continuity`  
**Named successor:** AS5 — Play persistence demolition — current unmerged APP-STATE slice; AS6+ remains unselected  

> Repository law: [`AGENTS.md`](../../AGENTS.md). Steward process: [`../Process/STEWARD-CYCLE.md`](../Process/STEWARD-CYCLE.md). Application-state authority: [`../Design/ARCHITECTURE-application-state-layer.md`](../Design/ARCHITECTURE-application-state-layer.md). Play authority: [`../Design/ARCHITECTURE-playable-material-and-runtime.md`](../Design/ARCHITECTURE-playable-material-and-runtime.md). Historical product contract: [`HANDOFF-PLAY-SURFACE-active-run-continuity.md`](HANDOFF-PLAY-SURFACE-active-run-continuity.md).

---

## §1 Mission and merge-ready invariant

**Mission:** Move Play's durable active-Run selection from `out/runtime/play/active-run.json` into Buddy Application State PostgreSQL so ordinary `/play` re-entry survives backend restart and checkout/worktree changes while still resuming the exact Run the GM explicitly selected.

**Merge-ready invariant:**

> **After AS4, `play.active_run` is the sole durable authority for the local operator's active Play Run. Missing row means no selection. Setting an active Run first proves that exact PostgreSQL Run + sealed manifest aggregate is coherent, then records only `run_id + selected_at`; selecting the already-active Run is idempotent and does not churn `selected_at`; selecting a different valid Run is last-explicit-selection-wins. Bare `/play` reads this PostgreSQL pointer and then follows the existing exact Run + manifest + pinned WorkRevision admission path — the pointer never makes a Run valid, never chooses latest/first, and never allocates a Run. Explicit chooser mode still bypasses automatic resume, and Start New never clears the prior active selection before a replacement reaches READY. Ordinary active-Run reads/writes never read or write `active-run.json` after the switch; DB unavailable fails closed without file fallback. Physical deletion remains AS5.**

```text
AS3
play.run + play.run_manifest       PostgreSQL
active-run.json                    file authority

AS4
play.run + play.run_manifest       PostgreSQL
play.active_run                    PostgreSQL

/play
  → active Run id
  → exact Run + manifest
  → exact pinned WorkRevision
  → READY / truthful blocked state
```

### Pre-dispatch traps

| Trap | Frozen ruling |
|---|---|
| Add the table but keep file fallback | Not AS4. Ordinary active selection must be DB-only after switch. |
| Trust the pointer as Run validity | Wrong. The pointer records operator intent only; exact admission remains unchanged. |
| Clear active selection on `Start New Run` | Wrong. Failed/blocked new starts must leave the prior active Run intact. |
| Import before AS3 Runtime exists | Wrong. Legacy pointer may be adopted only after its referenced PostgreSQL Run aggregate exists and is coherent. |
| Invent campaign/account/browser/worktree identity | Prohibited. Preserve one local-operator singleton until product evidence earns another model. |
| Delete old Play modules now | AS5. AS4 switches authority; AS5 demolishes replaced topology. |

---

## §2 Re-anchor and current behavior

### 2.1 Predecessor truth

AS3 / #646 is DONE. It established:

- `play.run` as Run binding + mutable Runtime authority;
- `play.run_manifest` as sealed-manifest authority;
- atomic Run create + manifest seal;
- SQL `run_revision` CAS;
- transactional preserve-only rebase;
- no ordinary Run/manifest/rebase fallback to legacy files;
- coherent legacy Run+manifest import;
- `active-run.json` deliberately remained file-backed.

PR #648 then synchronized the living APP-STATE roadmap/anchor to record AS3 DONE and AS4 NEXT. Do **not** repeat that backward-looking repair. The AS4 implementation PR may update those authorities only to say **AS4 = THIS PR / unmerged** and **AS5 remains false**.

### 2.2 Current active-selection contract to preserve

`apps/live_control_server/services/play_active_run.py` currently owns:

```text
out/runtime/play/active-run.json

PlayActiveRunState
  schema_version = dmb_play_active_run_v1
  run_id: canonical UUID | null
  selected_at: UTC timestamp | null
```

Current product state machine:

```text
/play?choose=1
  → explicit chooser; do not auto-resume

/play?run=<uuid>
  → exact Run + manifest + pinned WorkRevision admission
  → only after READY, persist this Run as active

/play
  → read active selection
  → none: chooser
  → selected: navigate to exact ?run=<uuid>
  → use the same exact admission path

Start New Run
  → chooser/start mode
  → old active selection remains until a new Run reaches READY
```

AS4 changes storage under this behavior. Prefer zero production UI changes.

### 2.3 Parallel lane

At dispatch, CUTOVER #647 is D.3 design-only and leases only `Docs/Plans/HANDOFF-CUTOVER-buddy-graph-engine-demolition.md`. It is disjoint from AS4. Re-check active PRs before implementation; serialize any later overlapping path explicitly.

---

## §3 Required implementation contract

### 3.1 One forward migration

Create the next migration after `20260825_0003_play_runtime.py`:

```text
src/application_state/migrations/versions/20260825_0004_play_active_run.py
```

Create only:

```text
play.active_run
  scope_key TEXT PRIMARY KEY CHECK (scope_key = 'local')
  run_id UUID NOT NULL REFERENCES play.run(run_id)
  selected_at TIMESTAMPTZ NOT NULL
```

Rules:

- zero or one row;
- missing row is the durable null state;
- `scope_key='local'` is persistence machinery, not public identity;
- FK stays inside Play; no FK to Content or DungeonMind;
- do not store HTTP `schema_version` in SQL merely because the wire has one;
- do not use `ON DELETE CASCADE` to silently erase operator intent;
- no app-boot auto migration;
- do not edit migrations `0001`–`0003`.

### 3.2 Extend the existing Play package

Use:

```text
src/application_state/play/types.py
src/application_state/play/repository.py
src/application_state/play/service.py
```

Conceptual storage type:

```text
PlayActiveRun
  run_id: UUID
  selected_at: datetime
```

Repository owns SQL only and never commits. Service owns UoW, aggregate proof, idempotency, replacement, clear/null semantics, and fail-closed behavior. Do not create a generic preference/KV store.

### 3.3 GET remains the existing wire contract

`GET /api/live/play-active-run` remains:

```json
{
  "schema_version": "dmb_play_active_run_v1",
  "run_id": null,
  "selected_at": null
}
```

or the exact selected UUID/timestamp.

Required:

- no row → 200 null state;
- row → exact value;
- DB unavailable → application-state fail-closed status, no file fallback;
- impossible persisted state → integrity failure, not silent reset;
- never infer newest/first Run;
- GET need not re-admit WorkRevision bytes; `/play` does that next.

### 3.4 PUT proves the AS3 aggregate before changing intent

`PUT /api/live/play-active-run { run_id }` remains compatible.

Inside one UoW:

```text
validate canonical UUID
load play.run + play.run_manifest
prove the same persisted aggregate integrity used by AS3 get/list/mutation
read active singleton

same run_id
  → return existing row unchanged
  → selected_at unchanged

different valid run_id
  → upsert singleton
  → selected_at = now UTC
```

Required outcomes:

- noncanonical UUID → 422, no write;
- missing Run → 404;
- missing/incoherent manifest or corrupt persisted progress → fail closed, pointer unchanged;
- same-Run retry preserves timestamp exactly;
- different valid Run changes pointer without mutating either Run/manifest;
- concurrent different valid selections need no CAS; last committed explicit selection wins.

The server set operation proves Runtime coherence, not full Playable READY. The UI already calls it only after exact admission reaches READY; preserve that boundary.

### 3.5 Null/clear semantics

The roadmap names set/get/clear evidence. “Clear” means deleting the singleton row, never writing a null `run_id` row.

A small Play-domain clear operation is allowed. An HTTP DELETE may be added only if useful to expose that owning behavior; do not add UI for it in AS4 without product evidence.

Regardless:

- `Start New Run` must not clear;
- `?choose=1` must not clear;
- failed/blocked/incomplete new admission must leave prior active selection unchanged;
- clear is not Run completion/abandonment/deletion.

### 3.6 Honest legacy pointer adoption

Add explicit migration tooling, preferably:

```text
src/application_state/play/import_active_run.py
```

Procedure:

```text
1. require AS3 Run/manifest state already in PostgreSQL
2. capture active-run.json under predecessor file lock
3. absent file or valid null pair → import no row
4. selected run → parse exact UUID + selected_at
5. require referenced PostgreSQL Run aggregate exists and is coherent
6. insert exact run_id + exact selected_at
7. verify exact stored state
8. only then switch ordinary authority
```

Replay rules:

- exact legacy pointer + exact DB row → no-op;
- absent/null pointer + no DB row → no-op;
- malformed legacy pointer → fail, no DB mutation;
- referenced Run missing/incoherent → fail;
- conflicting existing DB selection or timestamp → conflict, never overwrite;
- never infer selection from Run ordering.

Migration tooling is the only AS4 path allowed to read the legacy pointer after the new service exists.

### 3.7 No legacy authority after switch

Prove all three:

```text
active-run.json absent      → GET/PUT and bare /play work from DB
active-run path unreadable  → GET/PUT and bare /play work from DB
legacy file says Run Y while DB says Run X
                            → ordinary behavior uses X; no reconciliation
```

Do not delete the file/module merely to prove this. `play_active_run_path()` may remain for migration/AS5 inventory, but ordinary production GET/PUT must not call it.

### 3.8 Restart/worktree continuity is the product proof

Required literal witness:

```text
shared Buddy PostgreSQL

root/worktree A
  Run X + manifest + progress in DB
  set active X

recreate backend/app boundary

root/worktree B
  same application-state DSN
  legacy out/runtime/play absent/unreadable
  GET active → X
  GET Run + manifest → X
  GET pinned WorkRevision → exact revision
  Play admission → READY
  Runtime current moment → exact stored run_revision/progress
```

Do not call two calls on the same in-memory object a restart test.

### 3.9 Exact current moment remains Runtime-owned

Resume must preserve exactly:

- `run_id`;
- `run_revision`;
- current Beat;
- optional current Scene;
- resolved Beats;
- selections;
- notes;
- Playable revision + SHA;
- sealed manifest grammar/membership.

No latest-Runbook substitution. No Runtime repair/canonicalization during resume. If the selected Run aggregate is corrupt, fail truthfully; never auto-select another Run.

### 3.10 Latency evidence

Capture predecessor-vs-head p50/p95, preferably 30+ samples, for:

- active GET;
- switching active PUT;
- bare `/play` server-side continuity/admission path if browser timing is noisy.

Use the file-backed AS3 state as baseline and report sample count/environment. Measurements are not hidden gates. Retain the AS3 note that Runtime CAS was ~74 ms p95 vs the original 50 ms hypothesis.

---

## §4 Write lease

Production/migration/doc lease:

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

Expected test lease:

```text
tests/application_state/test_play_active_run_postgres.py
tests/application_state/test_play_active_run_existing_state_import.py
tests/application_state/play_runtime_helpers.py
tests/test_play_active_run.py
tests/test_live_play_active_run.py
apps/live-control-ui/src/App.test.tsx
apps/live-control-ui/src/api/liveApi.test.ts
```

Bounded discovery:

```text
tests/application_state/  +3 direct test/helper paths
apps/live-control-ui/src/ +2 test-only paths
migrations/versions/      +1 forward migration only
```

Any required **production** path outside the named lease is a stop/re-brief. In particular, do not quietly add AppChrome, PlaySurfacePage production changes, StartRunPanel changes, Content changes, or AS5 deletion.

### Current-state doc update carried by the implementation PR

PR #648 already recorded AS3 DONE. Do not redo that history. If the implementation PR updates the two APP-STATE state authorities, record only:

```text
AS3  DONE — #646 merge 9c946cd8; accepted head 913cfe0b; 3 cycles; PASS 5026608908
AS4  DONE — #649 merge 993f837b; accepted head be109c42; 2 cycles; PASS 5033365385; evidence 5428663041
AS5  THIS PR — unmerged Play persistence demolition
AS6+ evidence-driven; no implementation dispatched
```

Preserve the AS3 latency note and exact evidence IDs.

---

## §5 Explicitly forbidden / out of scope

Do not add or claim:

- `play.run` / manifest model redesign;
- Beat/Scene/Decision persistence changes;
- Run mutation history/event sourcing;
- Run lifecycle fields;
- accounts/users/teams/operators;
- per-campaign multiple active pointers;
- browser/localStorage active authority;
- Content schema changes;
- Combat, Ingest, Source, Asset, generated-artifact migrations;
- DungeonMind/World changes;
- BF2/BF3 cockpit deepening;
- AppChrome navigation redesign;
- physical deletion of Play file helpers or registry locks;
- deletion of production `out/runtime/play/**` state;
- CUTOVER D.3 implementation;
- generic preference/KV tables;
- permanent DB/file toggle.

AS4 switches active-selection authority. AS5 demolishes replaced Play filesystem machinery.

---

## §6 Acceptance matrix

### PostgreSQL selection

1. no row → public null state;
2. valid X → persist X;
3. recreate service/app → get X;
4. set X again → identical timestamp;
5. valid Y → pointer changes, Runs unchanged;
6. clear owning operation → row absent/null;
7. missing Run → no pointer mutation;
8. corrupt/missing manifest → no pointer mutation;
9. corrupt persisted progress → no pointer mutation;
10. DB unavailable → fail closed, no file read.

### Legacy import

1. pre-AS4 X/T pointer → DB X/T exactly;
2. exact import replay → no-op;
3. absent/null pointer → no row, no inference;
4. malformed pointer → no write;
5. missing/incoherent referenced Run → fail;
6. conflicting DB selection/timestamp → conflict, no overwrite.

### File-independence

1. legacy file absent → DB GET/PUT works;
2. legacy path unreadable → DB GET/PUT works;
3. contradictory legacy file → DB wins;
4. ordinary code never recreates file;
5. ordinary active GET/PUT acquires no file lock.

### Product continuity

1. bare `/play` + no row → chooser;
2. bare `/play` + X → exact X READY admission;
3. `?choose=1` bypasses X without clearing it;
4. explicit Y reaches READY → Y becomes active;
5. Y fails before READY → X remains active;
6. Start New does not clear X;
7. successful new Run reaches READY → becomes active;
8. backend restart + same DB → exact same current moment;
9. different root/worktree + same DB + no legacy Play files → same result;
10. corrupt selected Run → truthful failure, no heuristic fallback.

### AS3 regression floor

Keep green:

- atomic Run+manifest create;
- historical Playable revision pinning;
- persisted-progress integrity;
- SQL Run CAS;
- transactional preserve-only rebase;
- cross-grammar fail-closed;
- legacy Runtime import;
- Plan/Runbook DB isolation;
- no World DB fallback.

---

## §7 Required execution evidence

No required test may skip because PostgreSQL is unavailable.

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

git diff --name-only <RECORDED_PR_BASE_SHA>...HEAD
```

The implementation handback must state the exact recorded PR base SHA used in the final command.

Also attach exact-head evidence for:

- migration head;
- DB singleton constraints;
- restart/new-app-instance witness;
- different-root/worktree witness;
- contradictory legacy file ignored;
- no file recreation/lock on ordinary path;
- legacy import no-write conflicts;
- same-Run timestamp idempotency;
- failed replacement preserves previous selection;
- exact-current-moment resume;
- baseline/head latency;
- current open-PR collision check;
- final lease ledger.

Evidence rule: establish predecessor state first, then cross the real import/switch/restart boundary. Test names alone are not proof.

---

## §8 Preferred nano-commits

```text
1. play.active_run migration + repository/type
2. active-selection service invariants
3. honest active-run.json import
4. switch compatibility adapter/routes to DB authority
5. owning-boundary/import/restart/worktree evidence
6. existing UI continuity regressions + latency capture
7. roadmap/anchor mark AS4 THIS PR; keep AS5 false
```

No unrelated cleanup.

---

## §9 Reviewer checklist

Block merge unless all are true:

1. `play.active_run` is sole ordinary active-selection authority.
2. Legacy file can be absent/unreadable/contradictory without affecting ordinary behavior.
3. Missing row means null; no newest/first heuristic.
4. Set proves AS3 Runtime aggregate integrity before mutation.
5. Corrupt progress/manifest cannot be legitimized by selecting the Run.
6. Same-Run retry preserves timestamp.
7. Different valid Run replaces only the pointer.
8. Bare `/play` still performs full exact admission.
9. Chooser/Start New cannot clear prior active selection accidentally.
10. Failed new/exact admission cannot displace prior selection.
11. Restart/worktree continuity comes from DB, not checkout-local files.
12. Exact Runtime current moment + pinned Playable revision survive resume.
13. Legacy import is exact/conflict-safe, never heuristic.
14. No account/campaign-multipointer/lifecycle/KV expansion.
15. AS3 regressions remain green.
16. AS5 remains false.
17. Diff stays inside §4 + recorded bounded discovery.

---

## §10 Handback and what remains false

Handback must include:

```text
recorded PR base
exact head
nano-commits
lease/bounded-discovery ledger
test counts / skips
real PostgreSQL confirmation
migration head
legacy import witness
restart/worktree witness
no-file/no-fallback witness
latency baseline/head
open PR collision check
stop conditions
what remains false
```

After AS4, these remain false:

```text
Play file/helper demolition          AS5
physical deletion of out/runtime     not automatic
registry lock removal                still used elsewhere
Combat persistence                   unchanged
worldbuilding_source                 file-backed
Ingest / Source / Asset schemas      not implemented
Generated artifact migrations        not selected
Run mutation history                 absent
multi-user active selection          absent
BF2/BF3 cockpit work                 not bundled
CUTOVER D.3                           separate lane
```

AS4 does unlock a sequencing change: once active continuity is PostgreSQL-owned, APP-STATE persistence is no longer the reason BF2/BF3 Play Surface cockpit work is paused. The steward may resume Play Surface deepening in parallel with AS5 only under disjoint leases.

---

## §11 Dispatch capsule

```text
PR: APP-STATE: persist active Run continuity
branch: agent/app-state-play-continuity
branch from: current main containing this handoff
record: exact branch/PR base SHA in PR body

Build only AS4:
- one play.active_run singleton
- missing row = no selection
- exact Run+manifest integrity before set
- same-run idempotency preserves selected_at
- last explicit valid selection wins
- honest active-run.json import
- GET/PUT switch to PostgreSQL only
- bare /play exact resume survives restart/worktree
- no file fallback
- no UI/cockpit redesign
- no AS5 demolition
- roadmap/anchor may say AS4 THIS PR, never merged

Review against the recorded actual PR base, not the historical AS3 merge.
```
