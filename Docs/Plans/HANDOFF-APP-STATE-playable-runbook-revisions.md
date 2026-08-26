---
pr_body_template: |
  ## Handoff pointer
  - Workstream: APP-STATE / AS2 — Playable Runbook historical WorkRevisions
  - Flow: APP-STATE
  - Direction: CODE → REVIEW
  - Handoff: Docs/Plans/HANDOFF-APP-STATE-playable-runbook-revisions.md
  - Implementation repository: Drakosfire/DungeonMindBuddy

  ## Verification pointer
  - Architecture: Docs/Design/ARCHITECTURE-application-state-layer.md v1.1
  - Playable authority: Docs/Design/ARCHITECTURE-playable-material-and-runtime.md v1.1
  - Predecessor: AS1 PR #641 merge 29ff1584b9f76bb5100a724a96bebbbcf8f08d12
  - Accepted predecessor head: b42eb629e8924695af7af5a6c986f44a26dc3536
  - Predecessor review: 3 distinct-head cycles; final PASS-equivalent review 5023488870
  - Production consumer: kind=runbook + existing Play exact-revision reads

  The checked-in handoff, cumulative diff, nano-commit story, and independently
  rerun evidence are the review contract. This body is transport metadata.
---

# HANDOFF — AS2: Playable Runbooks as historical WorkRevisions

**Created:** 2026-08-25  
**Status:** DONE — merged PR #643 at `b4d63daab3eeb8150ca73fe9492d7a3d8744a4e0`  
**Accepted head:** `6b1c2e77648eee6180d293c92d2c97a428e9002f`  
**Review:** 3 distinct-head cycles; final PASS-equivalent review `5024971680`  
**Exact-head evidence:** PR #643 comment `5417774447`  
**Canonical handoff path:** `Docs/Plans/HANDOFF-APP-STATE-playable-runbook-revisions.md`  
**Workstream / flow:** `APP-STATE`  
**Direction:** CODE → REVIEW  
**Implementation repository:** `Drakosfire/DungeonMindBuddy`  
**Exact base:** `29ff1584b9f76bb5100a724a96bebbbcf8f08d12` — merge of PR #641  
**AS1 accepted head:** `b42eb629e8924695af7af5a6c986f44a26dc3536`  
**AS1 review:** 3 distinct-head review cycles; final PASS-equivalent review `5023488870`  
**AS1 execution evidence:** PR #641 comment `5415847095` — real PostgreSQL `24 passed, 0 skipped`; APP-STATE suite `24 passed, 0 skipped`; clean lease/diff evidence  
**Suggested branch:** `agent/app-state-playable-runbook-revisions`  
**Suggested PR title:** `APP-STATE: persist Playable Runbooks as historical revisions`  
**Named successor:** AS3 — Play Run + sealed manifest transaction  

> Repository law: [`AGENTS.md`](../../AGENTS.md). Steward process: [`../Process/STEWARD-CYCLE.md`](../Process/STEWARD-CYCLE.md). Application-state authority: [`../Design/ARCHITECTURE-application-state-layer.md`](../Design/ARCHITECTURE-application-state-layer.md). Playable authority: [`../Design/ARCHITECTURE-playable-material-and-runtime.md`](../Design/ARCHITECTURE-playable-material-and-runtime.md).

---

## §1 Mission and merge-ready invariant

**Mission:** Make Playable Runbooks real revisioned content instead of “whatever the current Runbook file contains.” Switch `kind=runbook` authoring to the Content domain/PostgreSQL substrate proven by AS1, retain every committed Runbook revision from the adoption point forward, and teach the existing file-backed Play Runtime to read the exact committed revision already bound into a Run.

**Merge-ready invariant:**

> **After AS2, `kind=runbook` identity, WorkingCopy, and committed Markdown are owned by the Content service over Buddy PostgreSQL. A Playable revision is an immutable `WorkRevision.revision_n` + SHA-256, not `WorkObject.object_revision`, a registry revision, a target path, or the current file. New Runs bind the current committed Playable revision; an existing Run bound to revision N can still load exactly revision N after N+1 is committed; a divergent WorkingCopy is never substituted for committed Playable bytes; and no Run/manifest/active-run/rebase-intent persistence moves to PostgreSQL before AS3/AS4.**

This is the first slice where the Content substrate must prove a real cross-surface invariant:

```text
Plan / Canvas authors Runbook A
        ↓
WorkingCopy                     mutable / recoverable / not Run-admissible
        ↓ explicit Save
WorkRevision 17                 immutable Playable revision
        ↓ Start Run
Run X pins A + revision 17 + sha
        ↓ later authoring
WorkRevision 18                 new immutable Playable revision
        ↓
Run X still loads revision 17 exactly
```

### Pre-dispatch critique

| Question | Frozen answer |
|---|---|
| Most likely false-positive implementation | `runbook` is added to the SQL CHECK, but Play still reads the current workspace snapshot/file and therefore marks an old Run `rebase_required` as soon as a newer Runbook revision exists. |
| Most dangerous semantic conflation | Treating `object_revision` (metadata/draft CAS) as `playable_revision`. Architecture §8 separates them: Runs bind `WorkRevision.revision_n`. |
| Migration trap | Fabricating historical Runbook revisions because a legacy registry record says `revision=17`. Only current bytes are known. Import one honest WorkRevision at revision 17; revisions 1–16 do not exist unless actual bytes exist. |
| Working-copy trap | Returning draft bytes from the ordinary workspace snapshot and allowing Start Run / manifest seal to bind them. WorkingCopy is explicitly not Run-admissible. |
| Scope trap | Moving Run JSON, manifest sidecars, active-run, or rebase intents into SQL because Play code must be touched for historical reads. Those are AS3/AS4. |

---

## §2 Re-anchored authority and lane

### 2.1 Accepted predecessor truth

AS1 / PR #641 is merged at `29ff1584b9f76bb5100a724a96bebbbcf8f08d12` with accepted head `b42eb629e8924695af7af5a6c986f44a26dc3536` after **3 distinct-head review cycles**.

AS1 proved:

- Buddy-owned application-state DSN and Alembic lifecycle;
- Content `WorkObject` / `WorkRevision` / `WorkingCopy` for `kind=plan`;
- real PostgreSQL route/domain integration;
- one-way kind authority with no file fallback;
- object/WorkingCopy CAS and exact commit replay;
- honest import without fabricated history;
- real disposable PostgreSQL evidence that fails rather than skips.

AS1 also produced an important measured cost signal, not a performance claim: in its exact-head evidence environment, file-backed control prepare/commit/load measured roughly `0.9 / 1.5 / 0.9 ms` while PostgreSQL Plan measured roughly `58.5 / 68.9 / 25.0 ms`. AS2 must measure its own Playable paths and report them; do not hide the difference and do not prematurely optimize without evidence.

### 2.2 Current Runbook authority at this base

At `29ff1584…`, `kind=runbook` remains file-backed:

```text
WorkspaceDocumentRecord
  → out/registries/workspace_documents.json
  → target_relpath under evals/.../content/tiptap/*.md
  → workspace_document_mutation_lock / registry lock
  → current file bytes + fingerprint
```

The current writer authorizes Runbook targets only through the eval Tiptap allowlist. That path may remain **locator/export metadata** after AS2, but it must stop being Runbook byte authority.

### 2.3 Current Play assumption AS2 must retire

The shipped Play Runtime is still file-backed, but its **read** side assumes the current workspace file is the bound Playable revision:

- `play_run_registry.py` creates a Run by locking the workspace document and requiring `snapshot.file_exists`, `snapshot.loaded_revision == expected_playable_revision`, and exact SHA;
- `play_run_reference_manifest.py` seals/rebuilds manifests from the current workspace snapshot and rejects a missing file or changed current revision;
- `play_run_rebase.py` admits the target through the current workspace snapshot and filesystem lock;
- `PlaySurfacePage.tsx` loads an existing Run and then fetches the **current** workspace snapshot;
- `nativeRunbookProjection.ts` requires both `snapshot.record.revision` and `snapshot.loaded_revision` to equal `run.playable_revision` and requires `file_exists=true`;
- `startRunAttempt.ts` rejects a committed Runbook when `file_exists=false`.

That behavior was rational when historical bytes did not exist. It becomes wrong after AS2.

### 2.4 Revision identities — do not conflate them

The architecture already freezes the distinction:

```text
WorkObject.object_revision
  metadata + WorkingCopy + commit CAS
  may advance on autosave or metadata change
  NOT a Playable revision

WorkRevision.revision_n
  immutable committed content sequence
  this IS playable_revision

WorkRevision.work_revision_id
  immutable revision UUID
  future AS3 Run rows should store it

content_sha256
  exact committed bytes digest
```

AS2 preserves the existing file-backed `PlayRunRecord.playable_revision` integer, but after the Runbook switch its semantic source is **`WorkRevision.revision_n`**. Do not change the Run wire schema merely to add `work_revision_id`; AS3 owns the relational Run binding. AS2 may carry `work_revision_id` in Content/committed-revision responses so the future binding is available without redefining Runtime now.

### 2.5 Parallel lane

Open PR #642 is CUTOVER design-only and currently leases only:

```text
Docs/Plans/HANDOFF-CUTOVER-reviewed-first-world-initialization.md
```

It does not collide with AS2. Re-check active PR leases immediately before implementation. If later D.2C implementation acquires an AS2 path, serialize that path explicitly; do not merge through a runtime/state collision.

---

## §3 Required observable behavior and contracts

### 3.1 Admit `runbook` to Content without weakening Plan

AS2 may widen the Content kind gate from:

```text
plan
```

to:

```text
plan | runbook
```

through a new Buddy-owned Alembic revision. Do not edit the already-applied AS1 migration in place.

Repository/service queries must become kind-aware rather than silently changing every Plan query to “all Content.” Preserve all AS1 Plan behavior and failure semantics.

### 3.2 Ordinary Runbook authoring

Existing workspace-document/Tiptap APIs remain the authoring surface.

Required behavior:

- create `kind=runbook` → Content WorkObject with the existing document UUID;
- autosave → WorkingCopy, durable across restart;
- explicit Save → immutable WorkRevision;
- save replay → no duplicate semantic revision;
- stale object/WorkingCopy CAS → 409, no partial write;
- Runbook target path is metadata only after switch;
- database unavailable → named failure, never read/write old Runbook Markdown as fallback;
- `worldbuilding_source` remains file-backed and unaffected.

Runbook Markdown canonicalization must remain compatible with the current Tiptap authoring contract.

### 3.3 Explicit committed-revision read seam

Do **not** overload the ordinary workspace editor snapshot into the historical Playable API. Editor snapshots may legitimately expose a divergent WorkingCopy; Play must address committed truth explicitly.

AS2 must provide a Content-owned committed-revision read seam with two operations conceptually equivalent to:

```text
current_committed_revision(work_object_id)
exact_committed_revision(work_object_id, revision_n)
```

The route/API spelling may follow existing workspace-document conventions, but the product contract must expose enough stable information to return:

```text
work_object/document id
kind=runbook
current object metadata needed for admission
work_revision_id
revision_n
exact committed Markdown
content_sha256
```

A historical lookup must never return WorkingCopy bytes.

A requested revision that was never retained returns a named miss/conflict such as “historical revision bytes were never retained”; it must not substitute current bytes or synthesize history.

### 3.4 Start Run binds current committed revision, not object CAS

The Start Run path may continue to use the existing file-backed Run creation/manifest workflow, but its Playable binding must come from the **current committed WorkRevision**.

Required semantics:

```text
selected runbook has divergent WorkingCopy
  → Start Run remains blocked by the existing unsaved-draft posture

selected runbook is clean/committed
  → Start Run binds current WorkRevision.revision_n + sha
  → no file_exists requirement
  → no workspace filesystem lock for Runbook bytes
```

Do not bind `WorkspaceDocumentRecord.revision` / `object_revision` as `playable_revision`.

### 3.5 Existing Run loads exact historical revision

For an existing Run:

```text
Run.playable_artifact_id
Run.playable_revision
Run.playable_content_sha256
```

must resolve the exact committed WorkRevision, even when a newer revision exists.

The minimum acceptance sequence is:

```text
import/adopt Runbook current legacy revision 17 with bytes A
existing/new Run X pins 17 + sha(A)
commit revision 18 with bytes B

open Run X
  → load WorkRevision 17 / A
  → validate sealed manifest against A
  → READY if all other Play invariants pass
  → do NOT report rebase_required merely because 18 exists
```

A divergent WorkingCopy based on revision 18 must likewise not alter Run X’s projection.

### 3.6 Manifest sealing/recovery reads the Run binding

`play_run_reference_manifest.py` may remain the file-backed manifest authority until AS3. Its source bytes must change from “current Runbook workspace snapshot” to “exact committed Playable revision named by the Run.”

Therefore:

- exact manifest create/replay after Runbook revision advance still uses the bound revision;
- missing bound historical revision fails closed;
- manifest binding remains Run id + Playable artifact id + revision_n + sha;
- manifest file persistence itself is unchanged in AS2.

### 3.7 Rebase target reads committed revision

`play_run_rebase.py` remains file-backed and keeps its current intent/recovery protocol until AS3. AS2 only changes Playable read authority:

- target revision must resolve an exact committed Runbook WorkRevision;
- target SHA must match;
- WorkingCopy is not a rebase target;
- filesystem Runbook path/file lock is not required;
- preserve-only / grammar compatibility rules remain unchanged.

Do not remove rebase-intent files in AS2.

### 3.8 Honest legacy Runbook adoption

Import current legacy Runbook state under the standard architecture §12 rule:

| Legacy state | AS2 representation |
|---|---|
| document UUID | exact `work_object_id` |
| registry `kind=runbook` | admitted Content kind |
| title/campaign/status/metadata | WorkObject metadata |
| `target_relpath` | locator/export metadata only |
| committed current bytes | one WorkRevision whose `revision_n` equals the legacy registry revision |
| draft current bytes | WorkingCopy; no fabricated committed revision |
| older unseen revisions | absent; never synthesized |

This mapping intentionally preserves currently valid pre-AS2 Run bindings when the legacy Run’s revision+SHA equals the imported current Runbook bytes.

If an existing Run pins revision 16 but only legacy revision 17 bytes exist at adoption, fail honestly. AS2 does not reconstruct missing history.

### 3.9 What remains file-backed after AS2

These remain unchanged authorities:

```text
out/runtime/play/runs/*.json
out/runtime/play/reference-manifests/*
out/runtime/play/active-run.json
out/runtime/play/rebase-intents/*
per-Run Runtime file locks / CAS
worldbuilding_source files
Combat persistence
```

Touching Play services to change their Runbook **read** seam does not authorize moving their durable Runtime state.

---

## §4 Implementation write lease

Only the paths below plus the bounded-discovery allowances are leased to the AS2 implementation PR.

| Action | Path | Purpose |
|---|---|---|
| Modify | `src/application_state/content/types.py` | admit `runbook`; preserve explicit kind model |
| Modify | `src/application_state/content/repository.py` | kind-aware Content queries + exact revision lookup |
| Modify | `src/application_state/content/service.py` | Runbook authoring + committed-revision read seam; preserve Plan wrappers/contracts |
| Modify | `src/application_state/content/__init__.py` | bounded Content exports if required |
| Create | `src/application_state/content/import_runbooks.py` | honest/idempotent legacy Runbook adoption |
| Create | `src/application_state/migrations/versions/*.py` | new migration widening Content kind admission; never rewrite AS1 migration |
| Modify | `apps/live_control_server/services/workspace_document_registry.py` | switch `runbook` identity/snapshot metadata to Content; leave worldbuilding file-backed |
| Modify | `apps/live_control_server/services/tiptap_markdown_write.py` | Runbook autosave/commit through Content; no file authority/lock |
| Modify | `apps/live_control_server/routes/workspace_documents.py` | expose committed-revision read seam if route wiring is required |
| Modify | `apps/live_control_server/services/play_run_registry.py` | Start Run/current Playable binding reads committed WorkRevision; Runtime file storage unchanged |
| Modify | `apps/live_control_server/services/play_run_reference_manifest.py` | seal/recover manifest from exact bound WorkRevision |
| Modify | `apps/live_control_server/services/play_run_rebase.py` | target exact committed WorkRevision; keep file intent/recovery |
| Modify | `apps/live-control-ui/src/api/types.ts` | committed-revision response / additive fields if required |
| Modify | `apps/live-control-ui/src/api/liveApi.ts` | committed-revision fetch wiring if required |
| Modify | `apps/live-control-ui/src/playSurface/startRunAttempt.ts` | bind current committed revision; retire `file_exists` as Playable authority |
| Modify | `apps/live-control-ui/src/playSurface/PlaySurfacePage.tsx` | load exact Run-bound committed revision rather than current workspace bytes |
| Modify | `apps/live-control-ui/src/playSurface/runbook/nativeRunbookProjection.ts` | validate exact bound revision/sha; do not require current object revision/file |
| Create | `tests/application_state/test_runbook_work_object_postgres.py` | Runbook authoring/revision/history/fail-closed evidence |
| Create | `tests/application_state/test_runbook_existing_state_import.py` | honest import + existing-Run binding evidence |
| Modify | `tests/test_play_run_registry.py` | Start Run exact WorkRevision regression |
| Modify | `tests/test_play_run_reference_manifest.py` | historical bound-revision manifest evidence |
| Modify | `tests/test_play_run_rebase.py` | committed target revision / no Runbook file authority evidence |
| Modify | `tests/test_live_play_runs.py` | route-level exact-revision Play regression if needed |
| Modify | `tests/test_live_play_run_reference_manifest.py` | route-level manifest regression if needed |
| Modify | `tests/test_live_play_run_rebase.py` | route-level rebase regression if needed |
| Modify | `apps/live-control-ui/src/playSurface/startRunAttempt.test.ts` | Start Run revision_n + no-file tests |
| Modify | `apps/live-control-ui/src/playSurface/runbook/nativeRunbookProjection.test.ts` | historical admission after newer commit |
| Modify | `apps/live-control-ui/src/playSurface/StartRunPanel.test.tsx` | only if public preflight shape changes |
| Modify | `Docs/Roadmaps/ROADMAP-application-state.md` | backward-looking AS1 DONE truth; AS2 THIS PR; AS3 still false |
| Modify | `Docs/Plans/STEWARDS-ANCHOR-application-state.md` | record #641 merge/head/review/evidence; AS2 active |
| Modify | `Docs/Plans/HANDOFF-APP-STATE-postgres-foundation.md` | mark AS1 completed with merge/head/review truth |

### Bounded discovery

```text
Directory: tests/application_state/
Maximum additional paths: 4
Allowed: evidence helpers/tests required to prove an existing §7 row

Directory: apps/live-control-ui/src/playSurface/
Maximum additional paths: 4
Allowed: tests or narrow API consumer files that directly enforce exact historical Runbook admission

Directory: src/application_state/migrations/versions/
Maximum additional paths: 2
Allowed: migration revisions only if branch history requires more than one honest forward revision
```

A required production path outside this lease is a **stop report**, not an invitation to edit it silently.

---

## §5 Explicit out-of-scope / forbidden paths

| Path / family | Reason |
|---|---|
| `src/application_state/migrations/versions/20260825_0001_content_work_objects.py` | already-applied AS1 migration; use a new forward revision |
| `apps/live_control_server/services/play_active_run.py` | AS4 persistence |
| `apps/live_control_server/routes/play_active_run.py` | AS4 persistence |
| `src/application_state/play/**` or any `play.*` SQL migration | AS3; no Run/manifest tables now |
| `apps/live_control_server/services/registry_file_lock.py` | AS2 does not globally demolish Runtime file locks; route around it for switched Runbook bytes |
| `out/runtime/play/**` fixtures/production data | Runtime remains file-backed; tests use temp roots |
| Combat services / schemas | later domain migration |
| `worldbuilding_source` authority migration | later Content slice |
| Ingest / Source / Asset / generated-artifact schemas | AS6+ evidence-driven families |
| DungeonMind schema / World Graph authority | separate authority/workstream |
| DungeonMindServer storage/CDN | unrelated to UTF-8 Runbook content |
| Beat-first grammar semantics / BF2/BF3 cockpit redesign | accepted Play semantics are preserved; AS2 changes persistence/read authority only |
| automatic Playable → World publication | forbidden authority crossing |
| generic `application_object(id,type,jsonb)` | rejected architecture |

If the current Play UI cannot consume an exact committed revision without a larger BF2/BF3 redesign, stop and report the smallest missing seam. Do not use AS2 as permission to restart the Play surface.

---

## §6 Migration, failure, replay, and trust contract

### 6.1 Switch lifecycle

```text
inventory legacy runbook rows + current bytes
→ CAS-safe capture under existing file authority
→ import exact ids/metadata/current bytes
→ verify revision_n + digest + status
→ verify currently valid Run bindings can resolve imported revision
→ switch kind=runbook reads/writes to Content
→ old Runbook file reads/writes fail closed / are bypassed
→ prove target file absent/unwritable
```

Do not maintain a production `runbook=file|postgres` toggle after switch.

### 6.2 Exact replay

| Operation | Required replay behavior |
|---|---|
| Runbook read | idempotent |
| WorkingCopy autosave | CAS-safe; stale writer rejected |
| identical Save retry | return existing committed revision; no duplicate semantic WorkRevision |
| exact historical read | same immutable bytes/digest forever |
| import same legacy state | no-op |
| import same identity with different digest | fail closed |
| existing Run open | resolves its own revision_n+sha, never silently current |
| manifest seal retry | uses Run-bound revision; no semantic drift after newer Runbook commit |
| rebase target replay | existing Play rebase rules unchanged; target bytes are exact committed WorkRevision |

### 6.3 Required failure behavior

- app-state DSN missing/unavailable → Runbook operations fail closed; no file fallback;
- schema behind head → named migration failure; no automatic upgrade;
- historical revision absent → named failure; never current-byte substitution;
- revision exists but SHA differs from Run binding → integrity/rebase failure; never accept by revision number alone;
- Runbook has divergent WorkingCopy → Start New Run remains blocked from binding draft bytes;
- existing Run + divergent WorkingCopy → existing Run still reads its committed bound revision;
- `worldbuilding_source` continues to operate from current file authority when app-state is unavailable, subject to existing behavior;
- Plan remains PostgreSQL-backed and unchanged.

### 6.4 Product identity

After switch, these are never Runbook identity or byte authority:

```text
evals/.../content/tiptap/foo.md
file fingerprint / mtime
workspace file lock
current checkout/worktree path
```

`target_relpath` may survive as compatibility/export metadata until a later demolition/export slice earns its removal.

---

## §7 Evidence required to merge

Repository-only unit tests are insufficient for the core AS2 invariant. At least one path must traverse existing workspace/Play adapters against a **real disposable PostgreSQL database**.

### 7.1 Owning-boundary evidence matrix

| Guarantee | Required witness |
|---|---|
| Runbook create/autosave/commit/reload uses PostgreSQL | existing workspace/Tiptap API/service with legacy target file absent |
| committed revision history is real | commit N, commit N+1, load N exact bytes/digest/id after N+1 exists |
| revision identity is not object CAS | exercise autosave/metadata CAS movement and prove Playable `revision_n` remains the committed sequence |
| WorkingCopy not Run-admissible | divergent draft blocks Start New Run and is never returned by exact committed-revision lookup |
| existing Run ignores newer current revision | Run pinned N opens READY after Runbook N+1 exists |
| existing Run ignores divergent WorkingCopy | Run pinned N still projects N exact bytes |
| manifest uses bound revision | seal/reload exact manifest for Run N after N+1 exists |
| rebase reads exact target revision | target revision+sha admitted from Content with Runbook file missing |
| honest import | current legacy revision maps to one WorkRevision at that revision number; no earlier rows fabricated |
| existing legacy Run preservation | current legacy Run pin matching imported revision+sha remains resolvable after switch |
| missing historical legacy bytes | older Run pin fails with named non-fabrication error |
| no file fallback | remove/make unwritable Runbook target + registry lock path and repeat authoring/Play reads |
| Plan regression | AS1 Plan suite remains green on real Postgres |
| worldbuilding regression | explicit `kind=worldbuilding_source` remains file-backed / not coupled to Content kind switch |
| Runtime remains AS3-owned | no `play.*` schema/tables; Run/manifest/intent files still authoritative |
| latency measured | record file-backed baseline vs AS2 Runbook current read, historical read, autosave, commit, and existing-Run admission; measurements only unless a reviewed threshold already exists |
| exact lease | diff contains only §4 + bounded-discovery paths |

### 7.2 Exact verification commands

Implementation may add a narrow command when an owning-boundary test requires it, but these are mandatory:

```bash
uv run pytest \
  tests/application_state/test_isolation_guards.py \
  tests/application_state/test_plan_work_object_postgres.py \
  tests/application_state/test_runbook_work_object_postgres.py \
  tests/application_state/test_runbook_existing_state_import.py \
  -rs -s --tb=short

uv run pytest tests/application_state -q

uv run pytest \
  tests/test_play_run_registry.py \
  tests/test_play_run_reference_manifest.py \
  tests/test_play_run_rebase.py \
  tests/test_live_play_runs.py \
  tests/test_live_play_run_reference_manifest.py \
  tests/test_live_play_run_rebase.py \
  -q

pnpm --dir apps/live-control-ui test -- \
  src/playSurface/startRunAttempt.test.ts \
  src/playSurface/runbook/nativeRunbookProjection.test.ts \
  src/playSurface/StartRunPanel.test.tsx

git diff --check
git diff --name-only 29ff1584b9f76bb5100a724a96bebbbcf8f08d12...HEAD
```

**Real-Postgres requirement:** required APP-STATE tests must report **0 skipped**. A missing disposable PostgreSQL server is evidence failure, not a green skip.

### 7.3 Minimal dogfood

Use a disposable/test Runbook or safe local fixture, not campaign corpus authority:

```text
1. Create/adopt one Runbook.
2. Save committed Playable revision N.
3. Start a Run pinned to N.
4. Add/edit material and Save revision N+1.
5. Reopen the old Run.
6. Confirm it still shows N, not N+1.
7. Create a divergent WorkingCopy for N+1/N+2 authoring.
8. Reopen the old Run again; confirm draft bytes do not leak in.
9. Make the former Runbook target file absent/unreadable.
10. Repeat old-Run open and current Runbook save/load.
```

Expected: exact historical content remains trustworthy; no path fallback occurs.

---

## §8 Implementation story, review focus, and state sync

### 8.1 Preferred nano-commit story

Exact count is not a contract; preserve independent reviewability:

```text
1. forward migration + Content kind-aware repository/service
2. honest Runbook import + exact committed-revision reads
3. workspace/Tiptap Runbook authority switch
4. Play server reads exact current/historical WorkRevision
5. Play UI binds/loads revision_n instead of file/current object CAS
6. owning-boundary + adversarial + latency evidence
7. backward-looking AS1 state sync
```

Do not mix AS3 Run persistence into any of these commits.

### 8.2 Reviewer finding ledger

Review should explicitly answer:

1. Does `playable_revision` mean `WorkRevision.revision_n` everywhere after the switch?
2. Can `object_revision` advance without invalidating an already committed Playable revision?
3. Can Run N load after N+1 exists?
4. Can Run N load while a divergent WorkingCopy exists?
5. Does Start New Run still refuse draft/uncommitted bytes?
6. Can the Runbook target file and its workspace lock disappear without breaking switched behavior?
7. Are manifest/rebase **reads** migrated without migrating their durable Runtime files?
8. Does import preserve currently valid legacy Run bindings and fail honestly for missing historical bytes?
9. Did Plan behavior regress while Content became kind-aware?
10. Did any code start treating target paths or DB coordinates as product identity?

### 8.3 State-authority sync carried by the AS2 PR

The current roadmap/anchor on `main` still describe AS1 as “this PR” because #641 could not pre-claim its own merge. AS2 must perform the backward-looking sync atomically:

```text
AS1
  DONE — PR #641 merge 29ff1584b9f76bb5100a724a96bebbbcf8f08d12
  accepted head b42eb629e8924695af7af5a6c986f44a26dc3536
  3 review cycles
  final PASS-equivalent review 5023488870
  execution evidence comment 5415847095

AS2
  THIS PR — do not claim merged

AS3
  still false / blocked on AS2
```

Sync only the leased APP-STATE state authorities in §4. Do not opportunistically rewrite Play/CUTOVER roadmaps.

After AS2 actually merges, the next steward re-anchor records its merge SHA/review-cycle count before AS3 dispatch.

---

## §9 Acceptance checklist and what remains false

Merge only when all of these are true:

- [ ] `kind=runbook` is admitted by a **new forward migration**, not by rewriting AS1 migration history.
- [ ] Runbook create/autosave/save/reload is PostgreSQL-backed through existing product adapters.
- [ ] Plan remains PostgreSQL-backed with AS1 semantics intact.
- [ ] `worldbuilding_source` remains on its existing file authority.
- [ ] `WorkObject.object_revision` and `WorkRevision.revision_n` are mechanically distinct in code/tests.
- [ ] Start New Run binds the current committed `revision_n` + SHA, never WorkingCopy bytes or object CAS.
- [ ] A Run pinned to revision N opens exact N after N+1 is committed.
- [ ] A divergent WorkingCopy cannot change an existing Run’s projected bytes.
- [ ] Manifest sealing/recovery resolves the Run-bound committed revision.
- [ ] Rebase target admission resolves an exact committed revision without Runbook filesystem authority.
- [ ] Legacy Runbook import preserves UUID/current revision+SHA honestly and fabricates no history.
- [ ] A legacy Run pinned to an unavailable older revision fails closed rather than receiving current bytes.
- [ ] Former Runbook target files/locks can be absent without switched Runbook/Play read failure.
- [ ] Real disposable PostgreSQL required tests pass with 0 skipped.
- [ ] File-backed baseline vs AS2 latency measurements are recorded without inventing a performance claim.
- [ ] Cumulative diff obeys the exact lease + bounded-discovery contract.
- [ ] APP-STATE roadmap/anchor/AS1 handoff record #641 merge truth and AS2 as this PR.
- [ ] No `play.*`, Combat, Ingest, Asset, generated-artifact, or World Graph schema is introduced.

### What remains intentionally false after AS2

```text
Play Run rows                 still file-backed
sealed Run manifests          still file-backed
Run progress CAS              still file-backed
rebase intents                still file-backed
active Run                    still file-backed
Play Runtime transaction      not yet AS3
Play continuity PostgreSQL    not yet AS4
Play file demolition          not yet AS5
Combat persistence            unchanged
worldbuilding_source          still file-backed
Ingest / Source / Asset       not implemented here
BF2/BF3 cockpit deepening     still paused unless separately re-sequenced
```

AS2 succeeds when **historical Playable truth becomes real**. It does not succeed by making all of Play PostgreSQL-backed early.
