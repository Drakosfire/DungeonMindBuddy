---
pr_body_template: |
  ## Handoff pointer
  - Workstream: APP-STATE / AS5 — Play persistence demolition
  - Flow: APP-STATE
  - Direction: CODE → REVIEW
  - Handoff: Docs/Plans/HANDOFF-APP-STATE-play-persistence-demolition.md
  - Implementation repository: Drakosfire/DungeonMindBuddy

  ## Verification pointer
  - Architecture: Docs/Design/ARCHITECTURE-application-state-layer.md v1.1
  - Play authority: Docs/Design/ARCHITECTURE-playable-material-and-runtime.md v1.1
  - AS4 predecessor: PR #649 merge 993f837b6f2fc601acf2ae3a4b7926af1858ac6c
  - AS4 accepted head: be109c429460b6e22b0ded1c13e77dd0cc8e6b5e
  - AS4 final review: 2 distinct-head cycles; PASS-equivalent 5033365385
  - AS4 exact-head evidence: PR #649 comment 5428663041
  - Production consumer: all Play Run/manifest/progress/rebase/active-selection HTTP and native Play admission paths

  Branch from current main containing this handoff. Record that exact branch/base SHA
  in the PR body and review PR_BASE...HEAD. The checked-in handoff, actual PR-base
  diff, nano-commit story, and independently rerun evidence are the review contract.
---

# HANDOFF — AS5: Play Persistence Demolition

**Created:** 2026-08-26  
**Status:** READY — AS4 merged; final predetermined Play-first APP-STATE slice  
**Canonical handoff:** `Docs/Plans/HANDOFF-APP-STATE-play-persistence-demolition.md`  
**Workstream / flow:** `APP-STATE`  
**Implementation repository:** `Drakosfire/DungeonMindBuddy`  
**AS4 predecessor merge:** `993f837b6f2fc601acf2ae3a4b7926af1858ac6c` — PR #649  
**AS4 accepted head:** `be109c429460b6e22b0ded1c13e77dd0cc8e6b5e`  
**AS4 review:** 2 distinct-head review cycles; final PASS-equivalent `5033365385`  
**AS4 exact-head evidence:** PR #649 comment `5428663041`  
**Branching rule:** branch from the current `main` that contains this handoff, record that exact SHA as the PR base, and review `PR_BASE...HEAD`; do not branch from the historical AS4 merge if `main` has moved.  
**Suggested branch:** `agent/app-state-play-demolition`  
**Suggested PR title:** `APP-STATE: demolish legacy Play persistence`  
**Successor rule:** there is **no pre-authorized AS6 implementation**. After AS5, re-anchor and choose the next APP-STATE family from evidence.  

> Repository law: [`AGENTS.md`](../../AGENTS.md). Steward process: [`../Process/STEWARD-CYCLE.md`](../Process/STEWARD-CYCLE.md). Application-state authority: [`../Design/ARCHITECTURE-application-state-layer.md`](../Design/ARCHITECTURE-application-state-layer.md). Play authority: [`../Design/ARCHITECTURE-playable-material-and-runtime.md`](../Design/ARCHITECTURE-playable-material-and-runtime.md).

---

## §1 Mission and merge-ready invariant

**Mission:** Delete the superseded Play filesystem persistence and recovery machinery now that Playable revisions, Runs, sealed manifests, Runtime CAS/rebase, and active-Run continuity are all PostgreSQL authority.

**Merge-ready invariant:**

> **After AS5, current production code contains no Play persistence implementation for `out/runtime/play/**`: no Run JSON loader/writer, no manifest-sidecar loader/writer, no active-run file loader/writer, no durable rebase-intent protocol, no Play acquisition of registry file locks/tokens, and no in-head legacy Play import modules. The existing Play HTTP/wire/domain contracts continue to operate entirely through Content + `play.*` PostgreSQL authority. The application boots and Start Run, manifest replay/read, Run list/get, progress CAS, preserve-only rebase, active selection, bare `/play` resume, and exact historical Playable admission all work when the legacy `out/runtime/play` topology is physically absent or hostile. Database failure still fails closed and never falls back to legacy files. AS5 deletes code, not user data: old files may remain inert on disk, but current production no longer knows how to read or write them.**

Target transition:

```text
AS4
Content WorkRevision             PostgreSQL authority
play.run                         PostgreSQL authority
play.run_manifest                PostgreSQL authority
play.active_run                  PostgreSQL authority

BUT repository still contains:
  Run JSON path/load helpers
  manifest-sidecar path/load helpers
  active-run.json migration loader
  file-era rebase-intent recovery engine
  explicit Play legacy import modules
  Play tests coupled to those helpers
        ↓
AS5
Content + play.* PostgreSQL      only live Play persistence implementation

legacy out/runtime/play/**       inert historical residue only
legacy parser/recovery code      absent from current production tree
legacy migration recovery        available from Git history/predecessor checkout,
                                 not kept executable in current production
```

### Pre-dispatch critique

| Trap | Frozen ruling |
|---|---|
| False demolition | Leave all legacy helpers in place because ordinary paths no longer call them. Switched authority is not demolition. Delete the superseded implementation. |
| Over-demolition | Delete `registry_file_lock.py` or `src/live_play/live_store.py` globally. Those are shared by still-file-backed domains. Remove **Play's dependency** on them; do not delete shared infrastructure unless its last repository consumer is gone in another reviewed slice. |
| Contract churn | Move Play wire models/grammar into new modules merely to make deleted files prettier. Preserve public API and grammar ownership; strip dead persistence from the existing compatibility modules. |
| Migration theater | Keep permanent `import_runtime.py` / `import_active_run.py` because someone might someday find an old file. Git history is the legacy migration archive after this deliberate demolition. |
| Data-loss trap | Delete `out/runtime/play/**` user files as part of code cleanup. Do **not** delete operator data. The software simply stops treating those paths as meaningful. |
| Hidden fallback | Remove path helpers but add a debug env toggle or emergency file mode. No fallback toggle. DB unavailable remains fail-closed. |
| Test illusion | Mock file helpers so tests pass while production can still touch them. The acceptance test must make the legacy path physically absent/hostile and exercise real current Play seams. |
| Scope trap | Normalize Play schemas, redesign Beat/Scene/Decision semantics, deepen BF2/BF3 cockpit, migrate Combat, or start AS6. None belongs here. |

---

## §2 Re-anchor: what AS4 made true

### 2.1 Accepted predecessor truth

AS4 / PR #649 merged as:

```text
merge:          993f837b6f2fc601acf2ae3a4b7926af1858ac6c
accepted head:  be109c429460b6e22b0ded1c13e77dd0cc8e6b5e
review cycles:  2 distinct heads
final review:   5033365385 PASS-equivalent
exact evidence: 5428663041
```

AS4 proved:

- one `play.active_run` singleton is active-selection authority;
- missing row is normal null selection;
- setting active Run proves the existing Run+manifest aggregate;
- same-Run replay preserves `selected_at`;
- different valid explicit selection wins;
- `active-run.json` is ignored by ordinary GET/PUT after switch;
- restart/different-root continuity restores the exact Run/current moment from PostgreSQL;
- the existing `/play` state machine remains intact;
- legacy active pointer import remained explicit migration-only code for AS5 demolition.

AS3 already proved Run+manifest atomic create, SQL progress CAS, transactional preserve-only rebase, and ordinary no-fallback behavior. AS2 already proved immutable historical Runbook WorkRevisions. AS5 must not reimplement any of those semantics.

### 2.2 Current roadmap truth is one merge stale

The AS4 implementation could not truthfully record its own merge SHA before merge. At AS5 dispatch, repository truth is:

```text
AS0   DESIGN                 DONE
AS0.1 STORAGE TOPOLOGY       DONE
AS1   PLAN DOCUMENTS         DONE
AS2   PLAYABLE               DONE
AS3   PLAY RUNTIME           DONE
AS4   PLAY CONTINUITY        DONE — PR #649 merge 993f837b
AS5   PLAY DEMOLITION        THIS PR — unmerged
AS6+  evidence-driven        no implementation pre-authorized
```

AS5 must carry the backward-looking AS4 completion stamp into the current roadmap/anchor and mark AS5 as this unmerged PR. Do not invent an AS5 merge SHA.

### 2.3 Play Surface sequencing changes now

The persistence reason for pausing BF2/BF3 ended when AS4 merged. Therefore:

> **AS5 does not block renewed Play Surface cockpit work.**

PLAY-SURFACE may proceed in parallel with AS5 when write leases are disjoint. AS5 is a server/runtime demolition slice, not a semantic prerequisite for new cockpit behavior. If another active Play PR acquires an AS5 path, serialize that path explicitly.

### 2.4 Parallel CUTOVER lane

At design time, open PR #647 is CUTOVER graph-engine demolition **design** and is disjoint from these Play persistence paths. Re-check open PRs immediately before implementation. CUTOVER owns World authority/runtime demolition; APP-STATE AS5 owns Buddy Play persistence demolition.

---

## §3 Current demolition inventory

The current repository intentionally contains mixed-era compatibility modules. Do not delete a whole module merely because it once contained a file writer; distinguish live API/grammar from dead persistence.

### 3.1 `play_run_registry.py`

**Keep:**

- public wire/request/response models;
- canonical UUID/SHA/revision validation used by current routes;
- `PlayRunProgress` and its current admission/canonicalization helpers still consumed by PostgreSQL Play service;
- DB-backed `get_play_run`, `list_play_runs`, `create_or_replay_play_run`, `replace_play_run_progress` adapters;
- error mapping/public compatibility behavior.

**Remove when no current consumer remains:**

```text
PLAY_RUNS_REL
play_runs_dir
play_run_path
_load_record
_load_authoritative_record
file-backed manifest/pending-intent admission helpers whose only consumers are legacy import/recovery
src.live_play.live_store imports used only for Run JSON
```

Do not move the surviving models simply to make the diff aesthetically clean.

### 3.2 `play_run_reference_manifest.py`

**Keep:**

- v1/v2 manifest models;
- marker grammar and derivation;
- `detect_playable_grammar_version`;
- `derive_sealed_manifest` / membership logic;
- `parse_manifest_payload`;
- binding validation used by current PostgreSQL manifest adapters;
- DB-backed manifest get/replay/seal compatibility functions.

**Remove when no current consumer remains:**

```text
PLAY_RUN_REFERENCE_MANIFESTS_REL
manifest-sidecar path helpers
_load_manifest or equivalent sidecar parser entrypoint
file-I/O-only serialization helpers
src.live_play.live_store imports used only for sidecar loading/writing
```

A pure manifest serializer/parser is not forbidden merely because legacy code once used it. The forbidden thing is current **filesystem authority machinery**. Use repository search to distinguish pure grammar from file persistence.

### 3.3 `play_run_rebase.py`

This is the largest demolition target. Preserve only the current public request/error/adapter contract around PostgreSQL `rebase_play_run`.

Expected retained surface is conceptually:

```text
RebasePlayRunRequest
PlayRunRebaseError
rebase_or_replay_play_run(...)
```

Delete the file-era forward-recovery subsystem, including when present:

```text
PLAY_RUN_REBASE_INTENT_SCHEMA
PLAY_RUN_REBASE_INTENTS_REL
PlayRunRebaseIntent
intent path/list/existence helpers
require_no_pending_rebase_intent
registry file tokens
intent JSON tokens
intent load/write/delete
manifest/run target file writes
recovery-stage classification
resume/complete intent machinery
recover_legacy_rebase_intents
registry file-lock acquisition for Play rebase
```

The PostgreSQL transaction is the rebase recovery mechanism now. Do not retain a dormant second transaction engine.

### 3.4 `play_active_run.py`

**Keep:** public request/state/error model and PostgreSQL-backed get/set/clear adapters.

Delete file-era active selection support:

```text
PLAY_ACTIVE_RUN_REL
play_active_run_path
load_legacy_play_active_run_file
registry_file_lock import
live_store load_json import
legacy file timestamp/parser code if no live wire validator needs it
```

Wire validation for `selected_at` remains if it is still part of `PlayActiveRunState`; do not confuse validation with persistence.

### 3.5 Application-state legacy import modules

Delete from current production tree:

```text
src/application_state/play/import_runtime.py
src/application_state/play/import_active_run.py
```

Then remove their exports and import-only report/types from:

```text
src/application_state/play/__init__.py
src/application_state/play/types.py
```

Do **not** replace them with a new `legacy/` package, hidden CLI, debug endpoint, or feature flag. The predecessor commit in Git history is the deliberate emergency migration tool after demolition.

### 3.6 Shared file infrastructure stays

Do not delete merely because Play no longer uses it:

```text
apps/live_control_server/services/registry_file_lock.py
src/live_play/live_store.py
```

Other file-backed domains still rely on shared file infrastructure. AS5 proves **zero Play persistence dependency** on those modules; it does not claim repository-wide file persistence is gone.

### 3.7 Database schema is unchanged

AS5 creates no Alembic revision and no tables.

Head remains:

```text
20260825_0004
```

Do not alter applied migrations `0001`–`0004`. Do not add `0005` merely to mark demolition.

---

## §4 Migration-support retirement gate

Deleting importers is intentionally stronger than merely making them unused. Before the deletion becomes merge-ready, prove the predecessor migration path once without preserving that code on the AS5 head.

### 4.1 Git history is the migration archive

Use the AS4 merge `993f837b6f2fc601acf2ae3a4b7926af1858ac6c` in a detached worktree/subprocess fixture:

```text
predecessor checkout 993f837b
  ↓
materialize coherent legacy Run JSON + manifest + optional active-run pointer
  ↓
run predecessor AS3/AS4 import tooling into disposable PostgreSQL
  ↓
verify play.run + play.run_manifest + play.active_run
  ↓
remove/hide predecessor worktree + entire legacy out/runtime/play tree
  ↓
AS5 head against the same PostgreSQL
  ↓
Run/list/progress/rebase/active/resume continue correctly
```

This witness proves that deleting current import code does not erase the known upgrade route.

Do not import predecessor Python modules into the AS5 process. Use a subprocess/worktree boundary so current production remains independent.

### 4.2 Real legacy roots are never auto-deleted

AS5 must not delete or rewrite operator-owned `out/runtime/play/**` files.

If a **known real legacy root still requires import**, stop before demolition and import it with the predecessor implementation. A known unimported root that the operator intends to preserve is a merge blocker.

If no real legacy root is available/required, state that explicitly in handback. The repository still preserves the predecessor via Git history.

### 4.3 No post-demolition migration fallback

After AS5 merges, discovering an old Play file does not cause current software to auto-import, inspect, reconcile, or prefer it. Recovery is an explicit operator action using historical code, not ordinary product behavior.

---

## §5 Required negative architecture after demolition

The current production tree should make these searches empty for **Play persistence**:

```text
out/runtime/play
PLAY_RUNS_REL
PLAY_RUN_REFERENCE_MANIFESTS_REL
PLAY_RUN_REBASE_INTENTS_REL
PLAY_ACTIVE_RUN_REL
load_legacy_play_active_run_file
recover_legacy_rebase_intents
import_play_runtime_from_legacy_files
import_play_active_run_from_legacy_file
```

And the surviving Play compatibility/application-state modules must not import file transaction machinery for persistence:

```text
registry_mutation_lock
registry_token
src.live_play.live_store.load_json
src.live_play.live_store.write_json
```

Scope this proof to Play-owned production modules. Shared file-backed domains are allowed to keep using those primitives.

Do not satisfy the negative check with comments/string obfuscation. Delete the code.

---

## §6 Product behavior that must remain unchanged

AS5 is a deletion slice. It has no product permission to alter:

- Run ID / campaign / Playable binding semantics;
- historical Playable revision pinning;
- Run create + manifest seal transaction;
- manifest v1/v2 grammar;
- progress CAS or canonical persisted-integrity posture;
- same-grammar preserve-only rebase;
- cross-grammar fail-closed behavior;
- active Run set/get/clear semantics;
- same-Run `selected_at` idempotency;
- `/play?choose=1` chooser semantics;
- READY-before-active replacement rule;
- exact `/play?run=<uuid>` admission;
- bare `/play` resume;
- HTTP response schemas;
- database failure status behavior.

No UI production change is expected. A required UI production change is a stop-and-report condition.

---

## §7 Implementation write lease

### 7.1 Production paths

AS5 may modify only these production paths unless the stop/re-brief rule below is triggered:

```text
apps/live_control_server/services/play_run_registry.py
apps/live_control_server/services/play_run_reference_manifest.py
apps/live_control_server/services/play_run_rebase.py
apps/live_control_server/services/play_active_run.py

src/application_state/play/__init__.py
src/application_state/play/types.py
```

AS5 is expected to **delete**:

```text
src/application_state/play/import_runtime.py
src/application_state/play/import_active_run.py
```

No route change is expected:

```text
apps/live_control_server/routes/play_runs.py
```

If current production cannot be demolished without modifying that route or another production path, stop and report the exact dependency before editing it. Do not silently widen the lease.

### 7.2 Test paths

Expected write/delete targets:

```text
tests/application_state/play_runtime_helpers.py
tests/application_state/test_play_runtime_postgres.py
tests/application_state/test_play_active_run_postgres.py
tests/application_state/test_runbook_existing_state_import.py

tests/application_state/test_play_runtime_existing_state_import.py       # expected delete
 tests/application_state/test_play_active_run_existing_state_import.py    # expected delete

tests/application_state/test_play_runtime_demolition.py                  # expected new

tests/test_play_run_registry.py
tests/test_live_play_runs.py
tests/test_play_run_progress.py
tests/test_live_play_run_progress.py
tests/test_play_run_reference_manifest.py
tests/test_live_play_run_reference_manifest.py
tests/test_play_run_rebase.py
tests/test_live_play_run_rebase.py
tests/test_play_active_run.py
tests/test_live_play_active_run.py
```

The AS2 Runbook import test contains both still-valid Content import coverage and historical Play file-import witnesses. Preserve the Content import/capture/revision tests; delete or rewrite only the portions whose sole purpose is the now-retired Play file importer.

### 7.3 Docs/state-authority sync

AS5 may update:

```text
Docs/Roadmaps/ROADMAP-application-state.md
Docs/Plans/STEWARDS-ANCHOR-application-state.md
Docs/Plans/HANDOFF-APP-STATE-play-continuity-postgres.md
```

Required backward-looking stamp:

```text
AS4
  DONE — PR #649 merge 993f837b6f2fc601acf2ae3a4b7926af1858ac6c
  accepted head be109c429460b6e22b0ded1c13e77dd0cc8e6b5e
  2 distinct-head review cycles
  final PASS-equivalent 5033365385
  exact-head evidence 5428663041

AS5
  THIS PR — unmerged

AS6+
  evidence-driven; no implementation dispatched
```

Also remove the old statement that BF2/BF3 is paused on `active-run.json`; AS4 closed that reason for pause. Do not claim BF2/BF3 itself is implemented.

### 7.4 Bounded discovery

Test-only bounded discovery:

```text
tests/application_state/   +5 directly relevant paths
 tests/                     +5 directly relevant Play test paths
```

Documentation bounded discovery:

```text
Docs/Plans/ or Docs/Reports/   +1 AS5-specific evidence/recovery note only if directly required
```

There is **no production bounded-discovery allowance**. A required production path outside §7.1 is a stop report/re-brief condition.

---

## §8 Explicitly forbidden / out of scope

Do not:

- add an Alembic migration;
- change `play.run`, `play.run_manifest`, or `play.active_run` schema;
- move Play models merely for cleanup aesthetics;
- redesign public Play routes/wire contracts;
- add Run lifecycle state;
- add mutation/event history;
- redesign Beat/Scene/Decision/Option semantics;
- deepen BF2/BF3 cockpit in this PR;
- change PlaySurface/AppChrome production code;
- migrate Combat;
- migrate `worldbuilding_source`;
- create Ingest/Source/Asset/generated-artifact schemas;
- touch DungeonMind schema/World Graph authority;
- implement CUTOVER D.2C3/D.3;
- delete `registry_file_lock.py` globally;
- delete `src/live_play/live_store.py` globally;
- delete or mutate operator `out/runtime/play/**` data;
- add a hidden file fallback, legacy mode, debug import endpoint, or env toggle;
- keep current-production legacy importer packages under a new name;
- invent AS6 merely because AS5 is terminal for the Play-first sequence.

---

## §9 Required acceptance matrix

### 9.1 Physical absence / hostile-path proof

On real disposable PostgreSQL, exercise the full Play chain with the supplied repo root having **no** `out/runtime/play` directory:

1. create/commit a Runbook WorkRevision;
2. Start/create Run;
3. manifest replay/get;
4. list/get Run;
5. replace progress via CAS;
6. commit newer same-grammar Runbook revision;
7. preserve-only rebase;
8. set/get active Run;
9. recreate app/service instance and resume exact current moment;
10. exact historical Playable read remains valid.

Then repeat a focused subset with `root/out/runtime/play` occupied by a hostile sentinel (for example a regular read-only file rather than a directory). Current Play must still work and must not alter the sentinel.

### 9.2 No file recreation

Before and after Start/manifest/progress/rebase/active operations:

```text
out/runtime/play does not exist
```

must remain true.

If using a hostile sentinel, bytes/metadata remain unchanged.

### 9.3 No fallback on DB failure

Materialize contradictory legacy-looking JSON files manually in the test fixture **without using production legacy helpers**. Make application-state PostgreSQL unavailable. Current Play operations must fail with the normal application-state unavailable behavior and must not return or mutate the file data.

### 9.4 Legacy importer symbols are gone

Prove current production cannot import/use the retired migration API:

```text
application_state.play.import_runtime                absent
application_state.play.import_active_run             absent
import_play_runtime_from_legacy_files                not exported
import_play_active_run_from_legacy_file              not exported
recover_legacy_rebase_intents                        absent from current Play API
load_legacy_play_active_run_file                     absent from current Play API
```

Do not add a compatibility shim that raises “deprecated.” The implementation should be gone.

### 9.5 No Play file-lock dependency

Static/source evidence must show surviving Play production modules do not import/acquire registry file locks/tokens for Runtime persistence. Runtime tests should not monkeypatch those locks merely to make this claim.

`registry_file_lock.py` may remain because other domains still use it.

### 9.6 Predecessor migration bridge

Using a detached `993f837b…` checkout/subprocess and one disposable database:

1. create coherent file-era Run+manifest and active pointer;
2. import them with predecessor import tooling;
3. verify exact DB state;
4. remove/hide the legacy files and predecessor process;
5. open the same DB with AS5 head;
6. prove exact Run binding/current progress/manifest/active selection/resume.

This is the durable witness replacing in-head legacy importer tests.

### 9.7 Current integrity regressions

Keep green:

- Run+manifest atomicity;
- missing/malformed manifest fail-closed;
- persisted-progress integrity;
- progress SQL CAS conflict and exact retry;
- historical Playable pinning;
- same-grammar rebase;
- cross-grammar rebase rejection;
- active pointer idempotency;
- corrupt aggregate cannot become active;
- restart/worktree continuity;
- no World DB fallback;
- Plan/Runbook Content isolation.

### 9.8 UI behavior regression

With no UI production diff, run the already-repaired App/API Play continuity suite. It must remain green. Do not re-open App test expectations merely to accommodate demolition.

---

## §10 Required execution evidence

No required PostgreSQL test may skip because the database is unavailable.

At minimum report exact counts for:

```bash
uv run pytest \
  tests/application_state/test_play_runtime_demolition.py \
  tests/application_state/test_play_runtime_postgres.py \
  tests/application_state/test_play_active_run_postgres.py \
  -rs -s --tb=short

uv run pytest tests/application_state -q

uv run pytest \
  tests/test_play_run_registry.py \
  tests/test_play_run_progress.py \
  tests/test_play_run_reference_manifest.py \
  tests/test_play_run_rebase.py \
  tests/test_play_active_run.py \
  tests/test_live_play_runs.py \
  tests/test_live_play_run_progress.py \
  tests/test_live_play_run_reference_manifest.py \
  tests/test_live_play_run_rebase.py \
  tests/test_live_play_active_run.py \
  -q

pnpm --dir apps/live-control-ui exec vitest run \
  src/App.test.tsx \
  src/api/liveApi.test.ts

git diff --check

git diff --name-only PR_BASE...HEAD
```

Also attach exact-head evidence for:

- Alembic head remains `20260825_0004`; no new migration;
- predecessor-worktree migration bridge;
- physical-absence full Play chain;
- hostile-sentinel no-touch proof;
- DB-down contradictory-file no-fallback proof;
- current-production legacy symbols/modules absent;
- no Play production import of registry file lock/token or live-store file I/O;
- open-PR collision check;
- cumulative lease ledger;
- deleted-path ledger;
- whether any known real legacy root still required import;
- what remains false after AS5.

### Static search evidence

Include repository search/grep output scoped to current production Play modules for:

```text
out/runtime/play
PLAY_RUNS_REL
PLAY_RUN_REFERENCE_MANIFESTS_REL
PLAY_RUN_REBASE_INTENTS_REL
PLAY_ACTIVE_RUN_REL
load_legacy_play_active_run_file
recover_legacy_rebase_intents
import_play_runtime_from_legacy_files
import_play_active_run_from_legacy_file
registry_mutation_lock
registry_token
```

Explain any surviving match. Documentation/history/test-fixture strings are not production authority, but production matches require a finding.

---

## §11 Preferred nano-commit story

Keep deletion reviewable:

```text
1. add AS5 absence/hostile-path + predecessor-migration witnesses while old helpers still exist
2. remove active-run file migration/path support
3. remove Run/manifest file path/load support
4. remove file-era rebase-intent/recovery engine
5. delete application-state legacy Play import modules + import-only exports/types
6. delete/rewrite migration-only tests/helpers; preserve enduring Content/Play invariants
7. run full no-file/no-fallback regression + UI continuity evidence
8. sync AS4 DONE / AS5 this PR in roadmap + steward anchor + AS4 handoff
```

The first commit should make the demolition target executable before deleting implementation. Do not combine all deletions into one opaque commit unless repository constraints force it.

---

## §12 Reviewer exact-invariant questions

A reviewer should answer all of these against the exact head:

1. Are `play.run`, `play.run_manifest`, and `play.active_run` still the only Play durability authorities?
2. Does the app boot with the complete `out/runtime/play` topology absent?
3. Can Start Run + manifest + progress + rebase + active selection operate with that topology absent?
4. Can a hostile `out/runtime/play` sentinel remain untouched throughout those operations?
5. On DB outage, can any legacy-looking file satisfy a Play read/write? The answer must be no.
6. Are Run JSON path/load/write helpers gone from current production?
7. Are manifest-sidecar path/load/write helpers gone from current production?
8. Is the file-era rebase-intent/recovery engine gone?
9. Is active-run file migration/path support gone?
10. Are `import_runtime.py` and `import_active_run.py` gone from current production?
11. Does current Play no longer import registry file locks/tokens or live-store JSON I/O for persistence?
12. Did shared file infrastructure remain for domains that still need it?
13. Did the PR avoid deleting operator data?
14. Does a predecessor-checkout witness still prove migration into the same DB that AS5 can read?
15. Are all AS2–AS4 semantic/integrity regressions still green?
16. Did AS5 avoid schema/API/UI/semantic redesign?
17. Is BF2/BF3 correctly described as unblocked by AS4, not implemented by AS5?
18. Is AS6 still unselected?
19. Is the cumulative diff inside the §7 lease plus recorded test/doc bounded discovery?

Any “no” on 1–16, 18, or 19 is a blocker.

---

## §13 Handback contract and what remains false

The implementation handback must include:

```text
Exact PR base
Exact head
Nano-commit list
Changed-path lease ledger
Deleted-path ledger
Bounded-discovery ledger
Test commands + exact pass/skip counts
Real-PostgreSQL confirmation
Alembic head confirmation (0004; no new migration)
Predecessor migration-bridge witness
Physical absence + hostile sentinel witness
DB-down no-fallback witness
Static legacy-symbol/import sweep
Open PR collision check
Known-real-legacy-root statement
Stop conditions encountered
What remains false
```

### What becomes true after AS5

The Play-first APP-STATE migration is structurally complete:

```text
Plan / Runbook authoring       PostgreSQL
Playable historical revisions  PostgreSQL
Run + sealed manifest          PostgreSQL
Runtime CAS + rebase           PostgreSQL
active Run continuity          PostgreSQL
legacy Play persistence code   demolished
```

### What remains false after AS5

AS5 does **not** mean all DungeonBuddy application state is migrated:

```text
Combat persistence                         still file-backed
worldbuilding_source Content               still requires later decision/migration
Ingest processing/review durability        not migrated
SourceArtifact stable identity             not migrated
Asset metadata + DungeonMindServer bytes   not implemented as APP-STATE consumer
Generated artifact lifecycles              evidence-driven future work
Card project durability                    evidence-driven future work
Run mutation history                       not implemented
multi-user/account active selection        not implemented
BF2/BF3 cockpit                             not implemented by AS5 (but persistence pause is gone)
CUTOVER D.2C3/D.3                           separate lane
shared registry file locks                 still exist for other file-backed domains
src/live_play/live_store.py                 still exists for other consumers
```

### Next APP-STATE decision after AS5

Do **not** auto-name AS6. Re-anchor and inventory current product pain/evidence among:

- Combat Runtime;
- Ingest processing/review;
- SourceArtifact identity;
- generated artifact lifecycles;
- Asset metadata/storage boundary;
- remaining Content/worldbuilding sources;
- optional agent proposal/task durability;
- explicit Plan publication/export.

Choose the next slice because a real consumer earns it, not because a table family appears next in an old diagram.

---

## §14 Dispatch capsule

```text
PR: APP-STATE: demolish legacy Play persistence
branch: agent/app-state-play-demolition
base: current main containing this handoff; record exact SHA in PR

Build exactly AS5:
- no schema/API/UI redesign
- preserve live Play wire/grammar adapters
- delete Run JSON + manifest sidecar persistence helpers
- delete active-run.json persistence/import helpers
- delete file-era rebase-intent/recovery engine
- delete current-production Play legacy import modules
- remove Play dependency on registry file locks/tokens + live-store JSON I/O
- do NOT delete shared file infrastructure globally
- do NOT delete user legacy files
- prove full Play with out/runtime/play physically absent/hostile
- prove DB-down cannot fall back to contradictory legacy files
- prove predecessor 993f837b can import a legacy fixture, then AS5 head can run from same DB with files gone
- sync AS4 DONE / AS5 this PR
- leave AS6 unselected

Review from the checked-in handoff, not from this capsule.
```
