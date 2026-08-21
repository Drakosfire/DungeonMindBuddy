---
pr_body_template: |
  ## Handoff pointer
  - Workstream: PLAY-SURFACE / Lane A1 active-Run continuity
  - Flow: PLAY-SURFACE
  - Direction: DESIGN → CODE → REVIEW
  - Handoff: Docs/Plans/HANDOFF-PLAY-SURFACE-active-run-continuity.md
  - Branch / PR: agent/play-surface-active-run-continuity / `PLAY-SURFACE: resume the active Run`

  ## Verification pointer
  - Design/base anchor: `850daa75469965fa4306ab05d0920b99d1fa8b03` (merge of PR #624)
  - Predecessor: merged PR #624 / post-C2S27 PLAY-SURFACE re-anchor
  - Base/head: `850daa75469965fa4306ab05d0920b99d1fa8b03` / <implementation head>
  - Changed paths: HANDOFF §4 only
  - Verification: HANDOFF §7 + exact post-merge state sync

  The checked-in handoff, cumulative diff, independently rerun evidence, and
  exact reviewed-head judgment are the review contract. The PR description is
  transport metadata only.
---

# HANDOFF — resume the active Run without creating another one

**Created:** 2026-08-20  
**Status:** ACTIVE — dispatch exactly one PLAY-SURFACE capability from current `main` `850daa75469965fa4306ab05d0920b99d1fa8b03`; re-anchor and amend before dispatch if `main` moves.  
**Canonical handoff path:** `Docs/Plans/HANDOFF-PLAY-SURFACE-active-run-continuity.md`  
**Workstream:** `PLAY-SURFACE / Lane A1 active-Run continuity`  
**Flow / owner:** `PLAY-SURFACE`  
**Direction:** DESIGN → CODE → REVIEW  
**Implementation base:** `850daa75469965fa4306ab05d0920b99d1fa8b03`  
**Suggested branch:** `agent/play-surface-active-run-continuity`  
**PR title:** `PLAY-SURFACE: resume the active Run`

> Repository law: `AGENTS.md`.  
> PLAY-SURFACE architecture: `Docs/Design/ARCHITECTURE-playable-material-and-runtime.md`.  
> Play projection: `Docs/Design/DESIGN-play-surface-projection.md`.  
> Parent acceptance roadmap: `Docs/Roadmaps/ROADMAP-con-ready.md`.  
> Living Play sequence: `Docs/Roadmaps/ROADMAP-playable-hoist-dungeonmind-kernel.md`.  
> Dogfood evidence: `Docs/Reports/REPORT-play-c2s27-native-runbook-dogfood-2026-08.md`.  
> Predecessor reset: `Docs/Plans/HANDOFF-PLAY-SURFACE-c2s27-reanchor-and-workspace-cleanup.md`.

---

## 0. Re-anchor, predecessor sync, and decomposition

Current repository truth at design time:

```text
main:
  850daa75469965fa4306ab05d0920b99d1fa8b03
  merge of PR #624

PR #624:
  final branch head:        693ff9062e3518a66ad04feae1fdf64c7c9362c4
  merge commit:             850daa75469965fa4306ab05d0920b99d1fa8b03
  formal review cycle 1:    REQUEST-CHANGES-equivalent @ 58c20222...
  formal review cycle 2:    REQUEST-CHANGES-equivalent @ 91d9af08...
  final repair head:        693ff906... merged without a posted Cycle 3 judgment
```

Do **not** invent a third review cycle retroactively. The repository definition remains:

```text
one formal reviewer judgment against one distinct head SHA = one review cycle
```

The consuming implementation PR records the predecessor truth exactly: PR #624 merged after **2 formal review cycles**, with the final naming-only repair head merged without a third formal reviewer judgment. That is process telemetry, not a reason to rewrite history.

### Backward-looking state-authority sync carried by this PR

This implementation consumes the merged post-C2S27 reset. Update the following together while keeping this in-flight slice ACTIVE/not-complete:

1. `Docs/Plans/HANDOFF-PLAY-SURFACE-c2s27-reanchor-and-workspace-cleanup.md`
   - mark PR #624 MERGED / HISTORICAL;
   - record final head `693ff906...`, merge `850daa754...`, and **2 formal review cycles**;
   - state explicitly that no Cycle 3 judgment was posted before merge;
   - name this active-Run continuity slice as the immediate consuming implementation.
2. `Docs/Roadmaps/ROADMAP-playable-hoist-dungeonmind-kernel.md`
   - re-anchor integration tip to `850daa754...`;
   - record #624/reset complete;
   - select this handoff as the active Lane A implementation slice;
   - keep Lane B blocked on the retained Combat-save worktree;
   - keep Beat/Scene/Decision + Plan→Playable redesign and P3B/P4 deferred.
3. `Docs/Roadmaps/ROADMAP-con-ready.md`
   - record the reset itself as merged at `850daa754...`;
   - make clear CR-U17 remains false overall;
   - identify this slice as a bounded repair of Play re-entry / duplicate-Run churn, not completion of cross-worktree persistence.
4. `Docs/Plans/STEWARDS-ANCHOR-con-ready.md`
   - re-anchor current state to merged #624 and this active PLAY-SURFACE slice;
   - preserve CON-READY as parent acceptance authority.
5. Repository source-set/export basis only where it claims the pre-merge base:
   - `Docs/Design/INDEX-design-agent-source-set.md` + byte-identical mirror;
   - `Docs/Sources/design-agent/README.md`;
   - byte-identical mirrors for the three changed canonical current-state authorities above.

Do **not** advance the user-managed Project Sources snapshot date merely because repository mirrors are refreshed.

### Why Lane A is split here

PR #624 selected “active-Run continuity / Resume vs Start New.” That phrase contains two different persistence problems if treated carelessly:

```text
A. current product-navigation problem
   bare /play forgets which Run the GM was using
   → chooser appears again
   → Start Run remains prominent
   → repeated ordinary re-entry creates duplicate Run UUIDs

B. checkout-authority problem
   Play Run/manifests/workspace state live under checkout-local out/
   → a different worktree may not have the same durable authority set
```

Do **not** solve A and B in one PR by silently inventing a generic database, moving WorkspaceDocument authority, or redesigning P2 storage. This handoff is **Lane A1**: close the direct table-facing re-entry problem with one Play-owned active-Run selection over the existing Run authority.

The remaining checkout-independent Play state problem stays explicitly false after this PR and returns to stewardship after this user-visible repair. That is preferable to smuggling a multi-authority persistence migration into a navigation fix.

### Capability decomposition

| Candidate outcome | Decision |
|---|---|
| Persist one Play-owned active Run selection server-side | **Include** |
| Bare `/play` resumes that exact active Run | **Include** |
| Opening a different exact Run successfully makes it active | **Include** |
| Explicit `Start New Run` enters chooser/start mode | **Include** |
| New Run becomes active only after normal exact READY admission succeeds | **Include** |
| Failed/incomplete new start leaves prior active Run unchanged | **Include** |
| Browser reload / browser restart / server restart on the same Play store resumes active Run | **Include** |
| Pick “latest” or first Run when no active selection exists | **Prohibited** |
| Delete old duplicate Runs | **Exclude — lifecycle/cleanup** |
| Add active/completed/abandoned lifecycle to Run records | **Exclude** |
| Move Play Run/manifest/rebase storage out of checkout-local `out/` | **Exclude — separate persistence slice** |
| Move WorkspaceDocument/Plan authority | **Prohibited** |
| New generic persistence/database abstraction | **Prohibited** |
| Beat-first P1/P2 redesign | **Prohibited — reviewed design task later** |
| Combat durability / P4 | **Prohibited — Lane B** |
| AppChrome ownership/navigation redesign | **Prohibited** |

---

## §1 Mission and merge-ready invariant

**Mission:** A GM who already has a usable Play Run can leave Play, return later, and continue that exact Run without choosing it again and without accidentally creating another Run. Starting another Run is a separate explicit action.

**Merge-ready invariant:**

> **Play owns one durable active-Run selection referencing an existing exact Play Run UUID. When `/play` is entered without an explicit Run or chooser intent, Play resolves that selection and resumes the same exact Run through the existing P3A/D2 admission path; it never chooses “latest,” never chooses the first listed Run, and never allocates a new Run UUID. A successful explicit exact-Run open may replace the active selection only after the existing Run + sealed-manifest + Runbook admission reaches READY. “Start New Run” is a distinct explicit user action that exposes the existing chooser/start workflow without clearing the current active selection; an incomplete/blocked/failed new start cannot displace the previous active Run. Missing/corrupt/unavailable active-selection state is reported truthfully and falls back to explicit chooser behavior, not implicit Run creation. The active selection survives browser reload/reopen and backend restart on the same Play state store.**

### What this invariant intentionally does not claim

After merge, all of these remain false:

- switching to another worktree is guaranteed to expose the same Run/manifests/workspace snapshot;
- old duplicate Runs are deleted, hidden, or assigned lifecycle states;
- Play owns a historical immutable Runbook archive;
- the Beat-first hierarchy is implemented;
- Plan→Playable persistence is repaired;
- Combat is durable.

Do not use this PR to claim CR-U17 complete.

### Pre-dispatch critique

| Question | Answer |
|---|---|
| Can one invariant govern the whole slice? | **Yes.** Every write/read answers one question: which exact existing READY Run should bare `/play` resume? |
| Why is server state required instead of React/localStorage? | Browser-local state was explicitly rejected by C2S27. The active selection must survive browser reload/reopen and server restart on the same Play store and remain visible to every browser using that server. |
| Why not use the newest Run? | `created_at` is history, not operator intent. The C2S27 failure was precisely that repeated starts generated plausible-but-wrong additional Runs. |
| Why not add Run lifecycle now? | `active/completed/abandoned` is a second public/durable contract with cleanup semantics. One pointer fixes the observed re-entry failure without guessing lifecycle policy. |
| Why not make AppChrome preserve `?run=`? | AppChrome is shared chrome and bare `/play` is the stable product route. Play should resolve its own active context; otherwise Plan/Build would need Play-specific query-state knowledge. |
| Most dangerous sequence | U1 is active → GM explicitly starts U2 → Run creation succeeds but sealing/admission fails → code marks U2 active too early. Required: U1 remains active until U2 reaches existing READY admission. |
| Second dangerous sequence | active pointer is absent/corrupt → UI uses newest listed Run as fallback. Required: explicit chooser, no heuristic. |
| Stop/split trigger | If this requires relocating Run/manifest/workspace authority, adding a generic DB, changing Run schema/lifecycle, or modifying shared chrome ownership, stop and return to stewardship. |

---

## §2 Current implementation truth and authority boundaries

### Read in this order

1. `AGENTS.md`
2. `Docs/Plans/HANDOFF-PLAY-SURFACE-c2s27-reanchor-and-workspace-cleanup.md`
3. `Docs/Roadmaps/ROADMAP-playable-hoist-dungeonmind-kernel.md`
4. `Docs/Roadmaps/ROADMAP-con-ready.md`
5. `Docs/Design/ARCHITECTURE-playable-material-and-runtime.md`
6. `Docs/Design/DESIGN-play-surface-projection.md`
7. `Docs/Reports/REPORT-play-c2s27-native-runbook-dogfood-2026-08.md`
8. `apps/live_control_server/services/play_run_registry.py`
9. `apps/live_control_server/services/play_run_reference_manifest.py`
10. `apps/live_control_server/routes/play_runs.py`
11. `apps/live-control-ui/src/playSurface/PlaySurfacePage.tsx`
12. `apps/live-control-ui/src/playSurface/StartRunPanel.tsx`
13. `apps/live-control-ui/src/playSurface/startRunAttempt.ts`
14. `apps/live-control-ui/src/api/types.ts`
15. `apps/live-control-ui/src/api/liveApi.ts`
16. current owning tests.

### Current product behavior to preserve

Current `main` already has:

```text
GET /api/live/play-runs
GET /api/live/play-runs/{run_id}
PUT /api/live/play-runs/{run_id}
PUT /api/live/play-runs/{run_id}/reference-manifest
PUT /api/live/play-runs/{run_id}/progress
PUT /api/live/play-runs/{run_id}/rebase

/play?run=<uuid>
  → exact Run
  → exact sealed manifest
  → exact current committed workspace Runbook snapshot
  → native admission
  → READY / truthful blocked status

/play
  → chooser every time
  → Existing Runs + StartRunPanel
```

The current chooser is useful as an **explicit** chooser. The bug is that it is also the ordinary re-entry path.

`StartRunPanel` correctly allocates a fresh UUID for a **fresh explicit start attempt**. Do not change that workflow into a dedupe heuristic. Remove accidental repetition by changing how the GM reaches Start Run, not by making UUID creation semantic.

### New Play-owned durable representation

Add exactly one small server-owned selection record under the existing Play runtime authority:

```text
out/runtime/play/active-run.json
```

Conceptual shape:

```text
PlayActiveRunState
  schema_version = dmb_play_active_run_v1
  run_id: canonical UUID | null
  selected_at: UTC timestamp | null
```

Rules:

- no file means `run_id = null`;
- `run_id` and `selected_at` are both present or both null;
- PUT of the already-active exact Run is idempotent and need not churn `selected_at`;
- switching to a different exact Run is last-explicit-selection-wins;
- no CAS is required for this operator-focus pointer;
- writes use the repository’s normal atomic JSON + registry-lock discipline;
- the pointer does not duplicate Run progress, Runbook content, manifest content, campaign data, or lifecycle state.

### Suggested API contract

Keep this inside the existing Play route family:

```text
GET /api/live/play-active-run
  → 200 PlayActiveRunState
  → missing selection is a normal state (`run_id: null`), not an error

PUT /api/live/play-active-run
  body: { run_id }
  → validate canonical UUID
  → require that exact Run exists
  → require its sealed reference manifest exists and matches the Run binding
  → persist/return PlayActiveRunState
```

Do not add DELETE in this slice. “Start New” does not mean “forget the current active Run before a replacement succeeds.”

### Authority rule

The active pointer answers only:

> “Which existing exact Run should ordinary Play entry resume?”

It does not make a Run valid. Existing Run / manifest / workspace admission remains authoritative. The client must still use the existing exact admission path after resolving the pointer.

### Shared chrome boundary

`APP_NAV_ITEMS` may remain:

```text
Play → /play
```

That is desirable. Shared AppChrome does not need to know a Play Run UUID. `/play` itself resolves the active Play context.

Do not modify AppChrome/AppChrome config unless a stop-and-report review proves the invariant impossible otherwise.

---

## §3 Observable behavior and state machine

### Entry modes

Play has three intentional entry meanings:

```text
/play?run=<uuid>
  explicit exact Run

/play?choose=1
  explicit chooser / Start New mode

/play
  ordinary Play entry → resolve active selection
```

`choose=1` is the recommended concrete transport grammar for this slice. If implementation discovers a materially better Play-local spelling, it may change only with tests proving the same three-way meaning. Do not put this mode into shared navigation config.

### Bare `/play`

```text
enter /play
→ GET active selection

run_id = U
  → replace current browser entry with /play?run=U
  → existing exact admission owns READY/blocked result
  → no Run creation path invoked

run_id = null
  → explicit chooser

active-selection read unavailable/corrupt
  → explicit chooser + truthful continuity warning
  → no latest/first fallback
  → no automatic Start Run
```

Use history **replace**, not push, when bare `/play` resolves to the active Run. Browser Back should return to the surface the GM came from rather than an intermediate empty Play entry.

### Successful exact Run open

When `/play?run=U` reaches the existing READY state:

```text
READY U
→ PUT active selection U
```

Requirements:

- update at most once for the admission generation / Run identity;
- an active-selection write failure does **not** invalidate the already READY Run;
- show a quiet truthful warning such as “Run is open, but Resume state could not be saved”;
- no automatic new Run, no redirect to chooser, no mutation of Run progress.

A blocked/missing/rebase-required/integrity-failed exact Run must **not** replace the prior active selection.

### Explicit Start New

READY Play must expose one clear `Start New Run` action.

```text
READY U1
→ Start New Run
→ /play?choose=1
→ existing chooser + StartRunPanel
```

Entering chooser mode does **not** clear U1.

If a new start:

```text
creates U2
→ manifest seals
→ exact /play?run=U2 admission reaches READY
→ active pointer changes U1 → U2
```

If U2 is incomplete/blocked/fails before READY:

```text
active pointer remains U1
```

Returning through ordinary `/play` resumes U1.

### Explicit existing-Run selection

Chooser remains able to open any exact existing Run. If that Run reaches READY, it becomes the active Run by the same rule as any successful exact open.

### Required behavior matrix

| Condition | Required behavior |
|---|---|
| no active selection | bare `/play` shows chooser; no Run generated |
| active U exists | bare `/play` replaces route with `/play?run=U` and loads U |
| active-state read unavailable | chooser + warning; no heuristic |
| active file malformed | fail truthful + chooser; do not overwrite silently |
| active pointer references missing Run | exact Run load reports miss; no replacement/new Run |
| active U is now rebase-required | exact existing rebase-required state; no different fallback |
| explicit exact U reaches READY | PUT U active once |
| exact U fails admission | do not change prior active selection |
| active PUT fails after READY | U remains usable; continuity warning visible |
| click Start New | chooser/start workflow only; prior active remains |
| new Run U2 creation incomplete | prior active U1 remains |
| U2 reaches READY | U2 becomes active |
| choose existing U3 and READY | U3 becomes active |
| hard reload exact active U | exact U reloads; no new UUID |
| navigate Plan → Play | bare `/play` resumes active U |
| backend restart, same state store | bare `/play` resumes active U |
| multiple existing Runs | never infer active from sort order / `created_at` |

### Duplicate-Run policy

This slice prevents **new accidental duplicates caused by ordinary re-entry**.

It does not delete or collapse historical duplicate Runs. The chooser may still show old records. Run lifecycle, abandonment, archival, and cleanup remain separate product policy.

---

## §4 Files in scope — exclusive write lease

### Checked-in authority / predecessor sync

| Action | Path | Purpose |
|---|---|---|
| Create | `Docs/Plans/HANDOFF-PLAY-SURFACE-active-run-continuity.md` | implementation authority |
| Modify | `Docs/Plans/HANDOFF-PLAY-SURFACE-c2s27-reanchor-and-workspace-cleanup.md` | mark #624 merged/historical; exact head/merge/review telemetry |
| Modify | `Docs/Roadmaps/ROADMAP-playable-hoist-dungeonmind-kernel.md` | re-anchor #624 and select this Lane A1 slice; do not pre-mark it complete |
| Modify | `Docs/Roadmaps/ROADMAP-con-ready.md` | parent story/current-delivery sync; CR-U17 remains false overall |
| Modify | `Docs/Plans/STEWARDS-ANCHOR-con-ready.md` | parent steward state sync |
| Modify | `Docs/Design/INDEX-design-agent-source-set.md` | repository export basis only; Project Sources snapshot date unchanged |
| Modify | `Docs/Sources/design-agent/README.md` | repository export basis only |
| Modify | `Docs/Sources/design-agent/ACTIVE_AUTHORITY/ROADMAP-playable-hoist-dungeonmind-kernel.md` | byte-identical mirror |
| Modify | `Docs/Sources/design-agent/ACTIVE_AUTHORITY/ROADMAP-con-ready.md` | byte-identical mirror |
| Modify | `Docs/Sources/design-agent/ACTIVE_AUTHORITY/STEWARDS-ANCHOR-con-ready.md` | byte-identical mirror |
| Modify | `Docs/Sources/design-agent/ACTIVE_REFERENCE/INDEX-design-agent-source-set.md` | byte-identical mirror |

### Backend

| Action | Path | Purpose |
|---|---|---|
| Create | `apps/live_control_server/services/play_active_run.py` | Play-owned active selection record + atomic read/write validation |
| Modify | `apps/live_control_server/routes/play_runs.py` | GET/PUT active-Run routes only |
| Create | `tests/test_play_active_run.py` | service persistence/idempotence/corruption proofs |
| Create | `tests/test_live_play_active_run.py` | HTTP contract proofs |

### Frontend

| Action | Path | Purpose |
|---|---|---|
| Modify | `apps/live-control-ui/src/api/types.ts` | exact active-state/request types |
| Modify | `apps/live-control-ui/src/api/liveApi.ts` | thin GET/PUT active-state clients |
| Modify | `apps/live-control-ui/src/api/liveApi.test.ts` | exact path/body/response proofs |
| Modify | `apps/live-control-ui/src/playSurface/PlaySurfacePage.tsx` | three entry modes, resume resolution, READY activation, Start New action |
| Modify | `apps/live-control-ui/src/playSurface/playSurface.css` | minimal continuity/chooser warning/action presentation only |
| Modify | `apps/live-control-ui/src/App.test.tsx` | owning composition proofs across bare Play, exact Run, chooser, READY activation |

### Bounded discovery exception

Maximum **two** additional files, both under `apps/live-control-ui/src/playSurface/`:

- one small Play-local entry/active-selection helper;
- its focused test.

Use only if extracting the entry state machine materially improves proof of §1. No shared-chrome, Plan, Build, Combat, TipTap grammar, or backend path may enter through this exception.

If another path is required, stop and report before editing.

---

## §5 Explicitly out of scope

Do not modify or claim:

```text
apps/live_control_server/config.py
apps/live_control_server/services/play_run_registry.py
apps/live_control_server/services/play_run_reference_manifest.py
apps/live_control_server/services/play_run_rebase.py
apps/live-control-ui/src/chrome/AppChrome.tsx
apps/live-control-ui/src/chrome/appChromeConfig.ts
apps/live-control-ui/src/planSurface/**
apps/live-control-ui/src/buildSurface/**
apps/live-control-ui/src/tiptap/playable/**
apps/live-control-ui/src/playSurface/runbook/**
apps/live-control-ui/src/graphReference/**
apps/live-control-ui/src/surfaceInteraction/** ownership contracts
Combat runtime/tracker files
WorkspaceDocument storage/registry authority
DungeonMind / DungeonMindDnD packages
```

Specifically forbidden:

- `localStorage` / `sessionStorage` as active-Run authority;
- “most recent Run” / “first Run” fallback;
- implicit Start Run on entry;
- dedupe-by-Runbook heuristics in `startRunAttempt.ts`;
- changing fresh-start UUID allocation semantics;
- Run deletion, archive, completion, abandonment, garbage collection;
- mutating Run progress merely because a Run became active;
- moving `out/runtime/play/**` to a new root;
- adding a generic database/persistence layer;
- moving WorkspaceDocument state;
- historical Runbook snapshot/archive creation;
- P1/P2 containment/manifest/rebase redesign;
- Beat-first table implementation;
- P3B graph-object sheets;
- P4 Add to Combat;
- dynamic Play query knowledge in shared AppChrome.

If the table-facing invariant cannot be satisfied without one of those, stop and hand it back as a decomposition failure.

---

## §6 Implementation contract

### Backend state

```text
Input:
  exact existing Run UUID

Output:
  one PlayActiveRunState

Authority:
  existing Play Run + sealed manifest prove the Run identity exists
  active-run.json only records operator focus

Persistence:
  out/runtime/play/active-run.json

Concurrency:
  registry/file lock + atomic JSON write
  same Run replay is idempotent
  different valid Run: last explicit selection wins

No CAS:
  this pointer is not Run progress and carries no semantic game state
```

### Frontend entry state

```text
EXPLICIT_RUN
  /play?run=U
  load exact existing P3A/D2 path
  READY → persist U active

EXPLICIT_CHOOSER
  /play?choose=1
  show existing chooser + StartRunPanel
  do not clear current active selection

RESOLVE_ACTIVE
  /play
  GET active
    U    → replace URL with /play?run=U
    null → chooser
    error→ chooser + warning
```

### Identity rules

| Concept | Identity | Forbidden substitute |
|---|---|---|
| active Run | exact canonical `run_id` | created_at/title/campaign/latest/array index |
| explicit existing Run | exact URL UUID | active pointer if URL already names another Run |
| Start New | one explicit UI action | ordinary navigation to `/play` |
| active write | READY exact Run UUID | Runbook ID / manifest ID / current Scene/Beat |

### Failure ownership

| Failure | Owner | Required UI behavior |
|---|---|---|
| active GET missing selection | normal Play entry | chooser |
| active GET unavailable/corrupt | continuity layer | chooser + warning |
| resolved active Run missing | existing exact Run admission | existing `Run not found` truth |
| resolved active Run rebase/integrity block | existing exact Run admission | existing truthful blocked state |
| active PUT failure after READY | continuity layer | non-blocking warning; Run remains usable |
| Start New failure before READY | existing StartRunPanel | prior active remains |

---

## §7 Evidence required to merge

### Backend focused proof

From repository root:

```bash
uv run pytest -q \
  tests/test_play_active_run.py \
  tests/test_live_play_active_run.py \
  tests/test_live_play_runs.py \
  tests/test_play_run_registry.py \
  tests/test_live_play_run_reference_manifest.py \
  tests/test_play_run_reference_manifest.py \
  tests/test_live_play_run_progress.py \
  tests/test_live_play_run_rebase.py
```

Required backend cases:

- missing `active-run.json` → normal null state;
- malformed file → fail closed, never silently reset;
- PUT non-canonical UUID → 422;
- PUT missing Run → no pointer write;
- PUT Run without matching sealed manifest → no pointer write;
- PUT valid exact Run → pointer persists;
- PUT same Run again → idempotent result/no unnecessary timestamp churn;
- PUT different valid Run → pointer changes intentionally;
- restart/re-read service → same pointer;
- active selection never mutates Run progress/revision.

### Frontend focused proof

From `apps/live-control-ui`:

```bash
pnpm exec vitest run \
  src/api/liveApi.test.ts \
  src/App.test.tsx \
  src/playSurface/StartRunPanel.test.tsx \
  src/playSurface/startRunAttempt.test.ts \
  src/playSurface/runbook/nativeRunbookProjection.test.ts \
  src/playSurface/runbook/RunbookTableDeck.test.tsx

pnpm run typecheck
pnpm run build
```

If the bounded Play-local helper/test is used, include it explicitly in the command.

### Required owning evidence ledger

| Guarantee | Owning boundary | Required proof |
|---|---|---|
| bare `/play` does not show Start Run when active U exists | App / PlaySurfacePage | active GET U → exact U READY |
| bare `/play` creates no Run UUID | App / StartRun workflow spies | `putPlayRun` / UUID generator untouched during resume |
| resume uses history replace | Play entry helper/Page | no intermediate `/play` Back-stack entry |
| no active → chooser | App | active null + Run list renders chooser |
| active read error → chooser + warning | App | no latest/first Run auto-open |
| explicit `?run=U` keeps exact URL authority | PlaySurfacePage | do not replace with another active V |
| exact READY U persists active | PlaySurfacePage + liveApi | one PUT U after READY |
| blocked U does not become active | PlaySurfacePage | zero active PUT on miss/rebase/integrity states |
| active PUT failure is non-blocking | PlaySurfacePage | READY deck remains mounted + warning |
| Start New is explicit | PlaySurfacePage | action → chooser mode; no write/UUID before explicit start |
| failed U2 start preserves U1 | composition | no active PUT U2; ordinary re-entry resolves U1 |
| successful U2 becomes active only after READY | composition | Run+manifest success alone insufficient; READY triggers PUT U2 |
| existing chooser Run U3 becomes active after READY | composition | explicit chooser link → exact READY → PUT U3 |
| no heuristic from created_at/list order | composition | multiple Runs + no active → chooser, none auto-open |
| same-store restart survives | backend integration | pointer read after fresh service/client instance |
| #624 predecessor truth synchronized | docs review | exact merge/head/2-cycle truth; no invented Cycle 3 |

### Repository/mirror integrity

```bash
git diff --check

# Changed paths must be HANDOFF §4 only.
git diff --name-only 850daa75469965fa4306ab05d0920b99d1fa8b03...HEAD

# Mirrors changed by predecessor sync must be byte-identical.
diff Docs/Roadmaps/ROADMAP-playable-hoist-dungeonmind-kernel.md \
  Docs/Sources/design-agent/ACTIVE_AUTHORITY/ROADMAP-playable-hoist-dungeonmind-kernel.md

diff Docs/Roadmaps/ROADMAP-con-ready.md \
  Docs/Sources/design-agent/ACTIVE_AUTHORITY/ROADMAP-con-ready.md

diff Docs/Plans/STEWARDS-ANCHOR-con-ready.md \
  Docs/Sources/design-agent/ACTIVE_AUTHORITY/STEWARDS-ANCHOR-con-ready.md

diff Docs/Design/INDEX-design-agent-source-set.md \
  Docs/Sources/design-agent/ACTIVE_REFERENCE/INDEX-design-agent-source-set.md
```

Every `diff` must produce no output.

### Live dogfood — merge evidence, not optional polish

Use a real existing READY Run U1.

```text
1. Open /play?run=U1 and confirm READY.
2. Navigate to Plan (or another primary surface).
3. Click Play in shared nav.
   PASS: /play resolves back to exact U1 without chooser and without creating a Run.
4. Hard refresh.
   PASS: U1 remains exact.
5. Close/reopen the browser tab or browser; reopen /play.
   PASS: U1 resumes from server-side active selection.
6. Restart the backend against the same checkout/state store; reopen /play.
   PASS: U1 resumes.
7. Click Start New Run.
   PASS: chooser/start UI appears; U1 is still active and no new Run exists yet.
8. Force one incomplete/blocked new-start attempt U2.
   PASS: ordinary /play still resumes U1.
9. Complete a successful explicit new Run U3 through normal StartRunPanel + READY admission.
10. Leave Play and return.
    PASS: U3 now resumes; U1 remains an existing historical Run.
11. Confirm no additional Run UUID was created by steps 2–6 or by merely entering chooser mode.
```

Record exact U1/U2/U3 UUIDs and before/after `out/runtime/play/runs/` filenames in the PR evidence comment.

---

## §8 Review contract

Formal review is against one exact head SHA.

Review must independently verify:

1. exact `main` base still equals the handoff base or the handoff was truthfully re-anchored;
2. every changed path is inside §4;
3. #624 predecessor state sync is backward-looking and exact;
4. no third #624 review cycle was invented;
5. bare `/play` resolves only explicit active state, never list order;
6. exact `?run=` authority beats active pointer;
7. READY is the only point where a different Run may become active;
8. Start New does not clear the old pointer before replacement READY;
9. active-selection persistence failure cannot take down an otherwise usable Run;
10. no localStorage, Run lifecycle, storage-root migration, P1/P2 redesign, Combat, or shared-chrome scope entered;
11. live dogfood proves zero new Run files during ordinary exit/re-entry/reload;
12. all required tests/build/mirror checks were independently rerun.

A fix commit after review creates a new head. Re-review that distinct head before merge.

---

## §9 Post-merge state / successor guidance

If this PR merges, record it in the next consuming state sync as one partial CR-U17 repair:

```text
true:
  ordinary Play entry resumes one explicit active Run
  Resume survives browser/backend restart on the same Play store
  Start New is explicit
  failed replacement start preserves prior active Run
  ordinary re-entry no longer creates duplicate Run churn

still false:
  Play runtime/workspace authority is checkout-independent across worktrees
  historical duplicate Run lifecycle/cleanup exists
  Plan→Playable authoring is lossless
  Combat is durable
  Beat-first Playable wire/runtime redesign exists
  native Play table instrument is product-ready
```

After merge, re-anchor before choosing the next slice.

Candidate next work is **not automatically fixed here**:

- Lane B can proceed only after the retained `agent/play-command-board-disk-saves` worktree is dispositioned.
- The remaining checkout-local Play persistence problem should be re-evaluated from this slice’s concrete active-selection evidence and Lane B’s Combat evidence before extracting a shared persistence seam.
- Beat/Scene/Decision + Plan→Playable remains a reviewed design task before another native table implementation.

Do not pre-authorize any successor from this handoff.
