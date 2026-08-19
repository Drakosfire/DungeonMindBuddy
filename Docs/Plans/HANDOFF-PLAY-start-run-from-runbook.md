---
pr_body_template: |
  ## Handoff pointer
  - Workstream: Playable Architecture Graduation / dogfood bridge D1
  - Flow: PLAY
  - Direction: DESIGN → CODE → REVIEW
  - Handoff: Docs/Plans/HANDOFF-PLAY-start-run-from-runbook.md
  - Branch / PR: agent/play-start-run-from-runbook / `PLAY: start exact Run from committed Runbook`

  ## Verification pointer
  - Design/base anchor: `509ad35a0c97aeed146f3a79d0895e430ed1efe7`
  - Predecessor: merged PR #618 / P3A native Runbook table deck
  - Base/head: `509ad35a0c97aeed146f3a79d0895e430ed1efe7` / <implementation head>
  - Changed paths: must remain inside HANDOFF §4
  - Verification: HANDOFF §7 + roadmap review disposition

  The checked-in handoff, cumulative diff, nano-commit story, independently
  rerun evidence, and roadmap review disposition are the review contract.
  This body is transport metadata.
---

# HANDOFF — start one exact Run from a committed Runbook

**Created:** 2026-08-19  
**Status:** ACTIVE — dispatch exactly one dogfood-enabling Play capability.  
**Canonical handoff path:** `Docs/Plans/HANDOFF-PLAY-start-run-from-runbook.md`  
**Workstream:** `Playable Architecture Graduation / dogfood bridge D1`  
**Flow / owner:** `PLAY`  
**Direction:** DESIGN → CODE → REVIEW  
**Implementation base:** `509ad35a0c97aeed146f3a79d0895e430ed1efe7`  
**Suggested branch:** `agent/play-start-run-from-runbook`  
**PR title:** `PLAY: start exact Run from committed Runbook`

> Repository law: `AGENTS.md`.
> Playable authority: `Docs/Design/ARCHITECTURE-playable-material-and-runtime.md`.
> Play product design: `Docs/Design/DESIGN-play-surface-projection.md`.
> P2 Run authority: `Docs/Plans/HANDOFF-PLAY-durable-run-binding.md` and `Docs/Plans/HANDOFF-PLAY-run-reference-manifest.md`.
> P3A predecessor: `Docs/Plans/HANDOFF-PLAY-native-runbook-table-deck.md`.
> Living sequence: `Docs/Roadmaps/ROADMAP-playable-hoist-dungeonmind-kernel.md`.

---

## 0. Re-anchor, predecessor sync, and sequencing decision

Current repository truth at design time:

```text
main:
  509ad35a0c97aeed146f3a79d0895e430ed1efe7

P3A / PR #618:
  merged:                  03252d51c8e13ff0322204bacdc605d3fc3a1201
  implementation/evidence 196144bb59281f15931305ecc70b252d69f5670d
  final reviewed head:    a907e623c3e53113688c2a55161e0c7ad4c4d53b
  formal review cycles:   3

post-P3A main:
  509ad35a... additionally restores the Session 26 wall-breach Combat roster.

native /play now has:
  explicit durable Run chooser
  exact Run + sealed manifest + committed Runbook admission
  Scene / Beat / Choice / Option table deck
  existing P2 Runtime progress mutations under run_revision CAS
  fail-closed rebase / integrity / recovery behavior

missing dogfood lifecycle:
  the UI cannot create a Run
  the UI cannot seal its reference manifest
  therefore a GM cannot begin from a committed Runbook without manual API/tool work
```

### Backward-looking state-authority sync carried by this PR

Per `AGENTS.md`, this implementation PR consumes merged P3A and therefore owns the truthful predecessor sync that was not knowable until #618 merged.

Update together:

1. `Docs/Plans/HANDOFF-PLAY-native-runbook-table-deck.md`
   - mark P3A / PR #618 merged/historical;
   - record merge SHA, implementation/evidence head, final reviewed head, and **3 review cycles**;
   - name this Start Run dogfood bridge as the immediate consuming successor.
2. `Docs/Roadmaps/ROADMAP-playable-hoist-dungeonmind-kernel.md`
   - replace `this PR` P3A ledger wording with merged PR #618 truth;
   - update the mutable current-sequence block to current `main`;
   - mark P3A complete;
   - select this Start Run slice as current next;
   - keep P3B designed but deferred behind the dogfood bridge sequence.
3. `Docs/Plans/HANDOFF-PLAY-native-graph-object-sheet.md`
   - keep P3B **NON-DISPATCHABLE**;
   - replace the stale condition “P3A state sync names P3B next” with the new sequencing truth: Start Run → Runbook briefing/instructions → live dogfood → re-anchor before P3B.

These are predecessor/current-sequence truth updates, not completion claims about this PR.

### Why sequence changes after P3A

P3B remains a valid designed capability, but product review after P3A exposed a more immediate table-use gap.

The intended planning-to-play path is now:

```text
accepted/editable Runbook
        ↓
committed exact Runbook revision
        ↓
Start Run                ← THIS PR
        ↓
Play Runbook briefing    ← named successor
        ↓
real session dogfood
        ↓
P3B exact graph reference opening, re-briefed from dogfood evidence
```

This is a sequencing update, not a stable architecture ownership change.

### Capability decomposition

| Candidate outcome | Decision |
|---|---|
| Explicitly start one Run from one chosen committed Runbook | **Include** |
| Generate one canonical opaque Run UUID for that start attempt | **Include — identity clause of same workflow** |
| Bind exact current committed Runbook revision + SHA through existing P2A endpoint | **Include** |
| Seal exact P2B1 reference manifest through existing endpoint | **Include** |
| Navigate to `/play?run=<uuid>` only after both authorities are confirmed | **Include** |
| Reconcile unknown create/seal outcomes using exact GETs | **Include — retry safety of same workflow** |
| Preserve existing explicit Run chooser | **Include — regression requirement** |
| Runbook briefing / root-level instructions in Play | **Exclude — named successor** |
| Interactive planning scaffold Keep/Edit/Remove/Decide UI | **Exclude — later Plan authoring workflow** |
| Create/commit/edit Runbooks | **Exclude — existing workspace authoring authority** |
| New backend “start run” endpoint | **Exclude unless stop/split review proves existing endpoints cannot safely support §1** |
| Run deletion / orphan cleanup | **Exclude — separate lifecycle capability** |
| Run rebase UI | **Exclude — separate lifecycle capability** |
| Exact graph-reference opening | **Exclude — P3B** |
| Threat mechanics integration changes | **Exclude — P3C already landed** |
| Add to Combat | **Exclude — P4** |
| New Runtime persistence/schema | **Prohibited** |
| New Playable grammar / instruction schema | **Prohibited** |
| New shared Projection/Agent host | **Prohibited** |

---

## §1 Mission and merge-ready invariant

**Mission:** A GM can deliberately start one playable Run from one explicitly chosen committed Runbook and arrive in native `/play` on that exact Run without manual API work.

**Merge-ready invariant:**

> **One explicit Start Run attempt owns one canonical Run UUID and one exact selected Runbook workspace-document identity + committed revision + content SHA. The UI may enter READY navigation only after the existing P2A Run authority confirms that exact binding and the existing P2B1 manifest authority confirms a sealed manifest for the same Run/binding. Workspace drift, discarded/uncommitted/missing content, recovery state, identity conflict, request failure, or unknown network outcome never causes a different Runbook/revision/Run UUID to be substituted, never generates an implicit “latest” choice, never navigates to a falsely ready Play deck, and never creates or mutates any authority other than the existing Run + manifest operations. Replay/reconciliation of the same attempt retains the same Run UUID and exact intended binding.**

### Pre-dispatch critique

| Question | Answer |
|---|---|
| Can one invariant govern every claimed observable path? | **Yes.** Selection, preflight, Run creation/replay, manifest seal/replay, unknown-outcome reconciliation, and navigation all answer whether one explicit attempt produced one exact admitted Run. |
| Most dangerous adversarial sequence | GM selects Runbook R@7/SHA-A → UI reads snapshot → R@8/SHA-B commits elsewhere → UI starts. The workflow must not silently bind R@8, refresh to “latest”, or navigate under stale assumptions. Existing P2A create must reject the stale exact expectation. |
| Second dangerous sequence | Run PUT succeeds but its response is lost → UI retries by generating a new UUID. That would create duplicate Runs for one user action. The same attempt must reconcile/replay the original UUID instead. |
| Would §7 detect those failures? | **Yes.** Component/workflow tests must inject snapshot drift and lost create/seal responses, then assert exact UUID/binding reuse and no false navigation. |
| Easiest owning boundary to under-test | The two-step create→seal transition. A green Run PUT is not enough; navigation is forbidden until manifest authority is also confirmed. |
| Stop/split trigger | If safe Start Run requires a new durable transaction journal, delete/rollback semantics, a new backend persistence format, or Plan-surface authoring changes, stop. Those are separate capabilities. |

---

## §2 Context, authority, and boundaries

### Read authoritative inputs in this order

1. `AGENTS.md`
2. `Docs/Design/ARCHITECTURE-playable-material-and-runtime.md`
3. `Docs/Design/DESIGN-play-surface-projection.md`
4. `Docs/Roadmaps/ROADMAP-playable-hoist-dungeonmind-kernel.md`
5. `Docs/Plans/HANDOFF-PLAY-native-runbook-table-deck.md`
6. `Docs/Plans/HANDOFF-PLAY-durable-run-binding.md`
7. `Docs/Plans/HANDOFF-PLAY-run-reference-manifest.md`
8. `apps/live_control_server/routes/play_runs.py` — **read only**
9. `apps/live_control_server/services/play_run_registry.py` — **read only**
10. `apps/live_control_server/services/play_run_reference_manifest.py` — **read only**
11. `apps/live-control-ui/src/api/types.ts`
12. `apps/live-control-ui/src/api/liveApi.ts`
13. `apps/live-control-ui/src/playSurface/PlaySurfacePage.tsx`
14. current owning UI/API tests

### Existing predecessor contract — do not redesign it

The backend already exposes the exact required operations:

```text
PUT /api/live/play-runs/{run_id}
  body:
    playable_artifact_id
    expected_playable_revision
    expected_playable_content_sha256

PUT /api/live/play-runs/{run_id}/reference-manifest
  no request body
```

P2A create/replay already:

- requires canonical caller-chosen Run UUID;
- requires `kind == runbook`;
- requires `status == active`;
- requires `content_status == committed`;
- requires target file exists;
- revalidates exact expected revision and SHA while holding workspace authority;
- returns the existing Run unchanged for an exact replay;
- returns 409 if the UUID is already bound differently.

P2B1 seal/replay already:

- requires the exact Run;
- revalidates the same committed Runbook binding;
- derives the canonical Playable reference manifest;
- returns an existing exact bound manifest unchanged on replay.

This slice **consumes** those contracts. It does not duplicate their authority in TypeScript.

### Lane / collision review

Current open PR #578 touches historical/mining Play surface code. It is evidence/mining only and is not implementation authority for this slice.

Rules for this lane:

- branch from exact base `509ad35a...` in an isolated checkout/worktree;
- do not cherry-pick or merge #578;
- do not edit #578's branch;
- do not merge #578 while this lane is under active review without re-anchoring for overlapping Play paths;
- other open Build/benchmark/transfer PRs are read-only adjacent work unless a §4 path collision appears.

### Boundary table

| Field | Required content |
|---|---|
| Base revision | `509ad35a0c97aeed146f3a79d0895e430ed1efe7` |
| Predecessor | merged PR #618 / P3A plus existing P2A/P2B1 APIs |
| Exact input consumed | explicit workspace Runbook document UUID; exact committed snapshot revision + SHA; one locally generated canonical Run UUID |
| Durable writes | existing P2 Run record + existing sealed manifest only |
| New durable representation | **none** |
| Named successor | `PLAY — project Runbook briefing/instructions in native Play` |
| Later successor | P3B exact graph-reference opening after live dogfood/re-anchor |
| What remains false | Play still does not surface unmarked/root-level planning instructions; Plan still has no interactive scaffold workflow; no rebase/delete/cleanup UI |

---

## §3 Observable paths and adversarial sequences

### Product shape

Keep `/play` as the owner.

The chooser should expose two deliberately separate capabilities:

```text
Existing Runs
  open exact existing Run

Start a Run
  choose explicit active Runbook
  start exact Run
```

Do not move Start Run into Plan in this slice. The richer planning scaffold is not yet designed as a durable authoring surface and should not become a prerequisite for beginning Play.

### Start Run selection

Use existing workspace list authority to discover candidates:

```text
kind = runbook
status = active
```

No first/latest/default Runbook selection.

Display labels/titles are presentation only. The start action is bound to exact `document_id`.

On explicit start action:

1. allocate one canonical Run UUID for **this attempt**;
2. fetch exact current workspace snapshot for the chosen Runbook;
3. require the snapshot is the same explicit document, active, committed, file-existing Runbook with valid loaded revision and content SHA;
4. call existing P2A Run PUT with that exact revision/SHA expectation;
5. confirm/reconcile the exact returned Run binding;
6. call existing P2B1 manifest seal PUT with **no request body**;
7. confirm/reconcile the exact manifest binding;
8. only then navigate to `/play?run=<same uuid>` and let existing P3A admission own READY.

The frontend preflight is user feedback, not authority. P2A/P2B1 must still revalidate server-side.

### Existing chooser regression

Existing Run selection must remain explicit and independently usable if the workspace Runbook discovery/start panel is unavailable.

A failure to list candidate Runbooks must not hide or disable existing durable Runs.

### Required failure matrix

| Condition | Required behavior |
|---|---|
| no active Runbooks | Start section says none available; existing Runs unaffected |
| workspace list unavailable | Start section unavailable/error; existing Runs unaffected |
| chosen Runbook becomes discarded/uncommitted/missing before snapshot | no Run PUT; truthful blocked state |
| snapshot is not exact `kind=runbook` | no Run PUT; integrity/contract block |
| snapshot has no exact loaded revision/SHA | no Run PUT; block |
| Runbook changes between snapshot and Run PUT | server 409; no silent latest/re-read/rebind; user must intentionally retry |
| Run PUT exact success | retain authoritative returned Run and continue to seal |
| Run PUT exact replay | treat as same successful attempt; continue to seal |
| Run PUT 409 different binding | block; never reuse that UUID with another binding |
| Run PUT unknown/network outcome | reconcile `GET` by the same Run UUID before any new attempt/UUID |
| unknown create outcome + exact Run exists | adopt it only if artifact/revision/SHA equal the intended binding; continue to seal |
| unknown create outcome + 404 | preserve same attempt UUID/binding and offer/replay same PUT; do not mint a new UUID automatically |
| manifest seal success/replay | verify same Run/binding, then navigate |
| manifest seal 409 because workspace advanced | show **Run created; setup incomplete** with exact Run UUID; no navigation; no auto-rebase |
| manifest seal unknown/network outcome | reconcile exact manifest GET before claiming failure/success |
| manifest GET proves exact manifest exists | navigate to same exact Run |
| manifest still missing/fails | keep incomplete state; retry same seal on same Run; no new Run UUID |
| user chooses a different Runbook after a failed attempt | new explicit attempt may allocate a new UUID; never silently repurpose the prior UUID |
| successful navigation | exact `/play?run=<uuid>`; P3A performs normal exact admission |

### Ordered adversarial proofs

#### A. Snapshot drift

```text
select Runbook R
→ snapshot R@7 / SHA-A
→ another actor commits R@8 / SHA-B
→ PUT Run expecting 7/A
```

Required: 409/stale feedback; no Run bound to 8/B; no automatic refresh/retry; no navigation.

#### B. Lost create response

```text
allocate UUID U
→ PUT U succeeds durably
→ response is lost
→ UI receives network failure
```

Required: reconcile `GET U`; if U is exactly R@7/A, continue with U. Never allocate U2 as an automatic retry.

#### C. Run created, seal blocked by drift

```text
PUT U binds R@7/A
→ R@8/B commits
→ manifest seal for U revalidates workspace and returns 409
```

Required: truthfully report durable Run U exists but is not playable-ready; do not navigate; do not auto-rebase; retry action retains U.

#### D. Lost seal response

```text
manifest seal for U succeeds durably
→ response is lost
```

Required: reconcile exact manifest GET; if exact U/R@7/A manifest exists, navigate once to U.

---

## §4 Files in scope — exclusive write lease

| Action | Path | Purpose |
|---|---|---|
| Create | `Docs/Plans/HANDOFF-PLAY-start-run-from-runbook.md` | checked-in implementation authority |
| Modify | `Docs/Plans/HANDOFF-PLAY-native-runbook-table-deck.md` | backward-looking P3A merge/review-cycle sync |
| Modify | `Docs/Plans/HANDOFF-PLAY-native-graph-object-sheet.md` | keep P3B non-dispatchable under revised dogfood sequence |
| Modify | `Docs/Roadmaps/ROADMAP-playable-hoist-dungeonmind-kernel.md` | P3A completion ledger + select this dogfood bridge; do not pre-mark this slice complete |
| Modify | `apps/live-control-ui/src/api/types.ts` | exact TypeScript mirror for existing P2A create request only |
| Modify | `apps/live-control-ui/src/api/liveApi.ts` | thin clients for existing Run PUT + manifest-seal PUT |
| Modify | `apps/live-control-ui/src/api/liveApi.test.ts` | prove exact request paths/body semantics, especially bodyless manifest seal |
| Modify | `apps/live-control-ui/src/playSurface/PlaySurfacePage.tsx` | compose Start Run capability beside existing chooser without changing exact Run admission |
| Modify | `apps/live-control-ui/src/playSurface/playSurface.css` | minimal Play-owned chooser/start presentation |
| Create | `apps/live-control-ui/src/playSurface/StartRunPanel.tsx` | explicit Runbook chooser + exact start/reconcile workflow |
| Create | `apps/live-control-ui/src/playSurface/StartRunPanel.test.tsx` | owning UI/workflow adversarial proofs |

### Bounded discovery exception

Maximum **two** additional paths, only under `apps/live-control-ui/src/playSurface/`.

Allowed kinds:

- one small Play-local workflow/helper module;
- its focused test.

Use only if extracting the async start/reconciliation state machine materially improves proof of the same §1 invariant. No shared, Plan, Build, backend, P1, P2, P3B, P3C, or Combat path may enter through this exception.

If any other path is required, stop and report it before editing.

---

## §5 Explicitly out of scope

Do not modify or claim:

```text
apps/live_control_server/**
apps/live-control-ui/src/planSurface/**
apps/live-control-ui/src/buildSurface/**
apps/live-control-ui/src/workspaceDocument/** authoring behavior
apps/live-control-ui/src/tiptap/playable/** grammar / identity
apps/live-control-ui/src/playSurface/runbook/** P3A admission/deck semantics
apps/live-control-ui/src/playSurface/reference/**
apps/live-control-ui/src/graphReference/**
apps/live-control-ui/src/agentInteraction/** host ownership
apps/live-control-ui/src/surfaceInteraction/** host ownership
src/graph_memory/**
DungeonMind / DungeonMindDnD packages
Combat state/mutation
```

Specifically forbidden in this slice:

- Keep/Edit/Remove/Decide planning scaffold UI;
- multi-choice agent planning interview;
- new `pressure`, `briefing`, `npc-cue`, `exit-ramp`, or other Playable element kind;
- automatic Runbook commit;
- automatic latest/first Runbook selection;
- automatic Run start when `/play` opens;
- automatic Run rebase;
- Run deletion/garbage collection;
- healing every pre-existing unsealed Run in the chooser;
- new backend transaction/start endpoint;
- localStorage Run authority;
- graph-reference opening;
- Add to Combat.

If incomplete-Run cleanup or general recovery becomes necessary to make Start Run usable, stop and propose it as a successor rather than silently adding delete/repair semantics.

---

## §6 Implementation contract and matrices

```text
Input:
  explicit active Runbook workspace document ID
  exact current WorkspaceDocumentSnapshot
  one canonical Run UUID generated once per explicit attempt
  existing P2A create/replay route
  existing P2B1 seal/replay route

Output:
  exact durable Run + exact sealed manifest
  navigation to /play?run=<same UUID> only after both are confirmed

Invariant:
  §1 merge-ready invariant

Durable writes:
  existing P2A Run record
  existing P2B1 reference manifest

New durable representation:
  none

Trust boundary:
  UI verifies enough snapshot shape to give truthful feedback.
  Server P2A/P2B1 remain authoritative for exact admission and persistence.

Replay / idempotency:
  same attempt + same UUID + same binding → replay/adopt exact existing Run/manifest
  same UUID + different binding → block 409; never repurpose
  unknown result → exact GET reconciliation before another write identity is created
```

### Commit model

There are two existing durable commit points; this slice does not pretend they are one transaction.

```text
Commit point 1:
  P2A Run record durably exists.

Between 1 and 2:
  UI must truthfully represent "Run created; setup incomplete" if sealing cannot be confirmed.

Commit point 2:
  P2B1 manifest durably exists and matches the Run binding.

Ready navigation:
  only after commit point 2 is confirmed/reconciled.
```

No rollback/delete behavior is introduced.

### State / fallback matrix

| Observable path | Loading | Exact success | Ordinary miss | Dependency unavailable | Integrity / stale | Retry / replay |
|---|---|---|---|---|---|---|
| Existing Runs | existing P3A behavior | exact Run links | empty list | existing P3A error | existing P3A behavior | existing behavior |
| Start Runbook list | independent loading state | active Runbooks | “No Runbooks” | Start section error only | n/a | refetch explicitly |
| Snapshot preflight | starting state | exact committed snapshot | document miss | show error, no write | block, no write | explicit retry |
| Run PUT | starting | exact Run/adopt replay | n/a | reconcile exact Run GET | 409 block | same UUID + binding only |
| Manifest PUT | sealing | exact manifest/adopt replay | n/a | reconcile exact manifest GET | block/incomplete | same Run only |
| Navigation | none | exact `/play?run=U` | n/a | never navigate | never navigate | navigate only after confirmation |

### Identity matrix

| Situation | Rule | Fallback? |
|---|---|---|
| Runbook identity | exact workspace `document_id` | No label/title fallback |
| Runbook version | exact `loaded_revision + content_sha256` snapshot pair | No latest fallback |
| Run identity | one canonical UUID generated once per explicit start attempt | No semantic/human ID |
| Same UUID exact binding | replay/adopt | Yes — exact predecessor replay only |
| Same UUID different binding | fail closed | No |
| display title/campaign | presentation only | Never identity |

### Predecessor-to-consumer mapping

| Predecessor field/outcome | Consumer behavior | Transformation |
|---|---|---|
| `WorkspaceDocumentRecord.document_id` | selected Runbook authority | exact UUID string |
| `WorkspaceDocumentSnapshot.loaded_revision` | `expected_playable_revision` | exact integer, no increment/normalization |
| `WorkspaceDocumentSnapshot.content_sha256` | `expected_playable_content_sha256` | exact lowercase SHA |
| P2A returned `PlayRunRecord.run_id` | attempt/result identity | must equal generated UUID |
| P2A returned artifact/revision/SHA | confirm intended binding | exact equality |
| P2B1 manifest `run_id` + binding | confirm seal authority | exact equality with returned Run |
| 409 stale/binding conflict | blocked attempt | no retry with refreshed version |
| network/unknown outcome | exact GET reconciliation | never infer success/failure |

---

## §7 Evidence required to merge

### Focused UI/API proof

From `apps/live-control-ui`:

```bash
pnpm exec vitest run \
  src/playSurface/StartRunPanel.test.tsx \
  src/api/liveApi.test.ts \
  src/App.test.tsx \
  src/playSurface/runbook/nativeRunbookProjection.test.ts \
  src/playSurface/runbook/RunbookTableDeck.test.tsx

pnpm run typecheck
pnpm run build
```

If a bounded Play-local workflow helper/test is created, include its test in the focused command.

### Existing P2 authority regression

From repository root:

```bash
uv run pytest -q \
  tests/test_live_play_runs.py \
  tests/test_play_run_registry.py \
  tests/test_live_play_run_reference_manifest.py \
  tests/test_play_run_reference_manifest.py
```

No backend file may change merely to make these tests pass.

### Required owning evidence ledger

| Guarantee | Owning boundary | Required proof |
|---|---|---|
| no implicit Runbook selection | StartRunPanel | multiple candidates; no write until explicit click |
| active Runbook discovery failure does not break existing Run chooser | PlaySurfacePage composition | workspace list fails while Run list succeeds; existing Run remains openable |
| exact snapshot revision/SHA sent to P2A | StartRunPanel + liveApi | request capture proof |
| stale snapshot race blocks | StartRunPanel workflow | injected 409 after snapshot; no manifest call, no navigation |
| same start attempt keeps one UUID | StartRunPanel workflow | lost create response + reconciliation/replay; generated UUID count stays one |
| exact create replay is adopted | StartRunPanel workflow | GET/PUT returns same exact binding; proceed |
| different binding on same UUID fails closed | StartRunPanel workflow | returned/reconciled mismatch blocks; no seal/navigation |
| manifest PUT has no body | liveApi.test | exact request assertion |
| navigation waits for manifest authority | StartRunPanel | Run success + seal failure never navigates |
| lost manifest response reconciles | StartRunPanel workflow | manifest GET proves exact seal → one navigation |
| Run created / seal incomplete is truthful | StartRunPanel | 409/failed seal shows exact Run UUID and retry; no new UUID |
| successful path enters existing P3A exact route | component integration/manual | `/play?run=U`; existing admission renders ready deck |
| no backend/new persistence contract | changed-path/diff review | no `apps/live_control_server/**`; only existing API mirrors |
| P3A predecessor state truth is synchronized | docs diff | exact merge/evidence/review-cycle facts; current roadmap chooses this slice without pre-marking it complete |

### Repository hygiene

```bash
uv run python scripts/steward_preflight.py \
  --handoff Docs/Plans/HANDOFF-PLAY-start-run-from-runbook.md

git diff --check
git diff --stat 509ad35a0c97aeed146f3a79d0895e430ed1efe7...HEAD -- \
  Docs/Plans/HANDOFF-PLAY-start-run-from-runbook.md \
  Docs/Plans/HANDOFF-PLAY-native-runbook-table-deck.md \
  Docs/Plans/HANDOFF-PLAY-native-graph-object-sheet.md \
  Docs/Roadmaps/ROADMAP-playable-hoist-dungeonmind-kernel.md \
  apps/live-control-ui/src/api/types.ts \
  apps/live-control-ui/src/api/liveApi.ts \
  apps/live-control-ui/src/api/liveApi.test.ts \
  apps/live-control-ui/src/playSurface/PlaySurfacePage.tsx \
  apps/live-control-ui/src/playSurface/playSurface.css \
  apps/live-control-ui/src/playSurface/StartRunPanel.tsx \
  apps/live-control-ui/src/playSurface/StartRunPanel.test.tsx

git diff --name-only 509ad35a0c97aeed146f3a79d0895e430ed1efe7...HEAD
```

### Minimal live dogfood proof — merge evidence

Use the existing local app/backend; do not create a new demo surface.

```text
1. Have one active committed Runbook with at least one marked Scene/Beat.
2. Open /play with no run query.
3. Confirm no existing Run or Runbook is auto-selected.
4. In Start a Run, deliberately choose that Runbook.
5. Start it.
6. Confirm the browser navigates to /play?run=<canonical UUID>.
7. Confirm native P3A renders the exact Runbook deck READY.
8. Resolve or set one Beat using existing Runtime controls.
9. Hard reload the same URL.
10. Confirm the exact Run reopens with persisted progress.
```

Capture:

```text
Runbook document ID:
Runbook revision:
Runbook SHA:
Run UUID:
Observed READY route:
Reload result:
```

If the local environment cannot produce this proof, record the blocker. Do not replace it with a newly built debug/demo panel.

### Baseline failure protocol

If any required command is already failing on exact base `509ad35a...`:

- run/cite the same command on base and head;
- record whether head adds failures;
- do not call the gate green;
- require an explicit operator waiver for a remaining acceptance gate.

---

## §8 Required review handback

Return all of the following:

1. exact PR URL, branch, base SHA, and head SHA;
2. §1 mission and invariant copied exactly;
3. nano-commit list and one discrete story per commit;
4. actual changed paths and focused diff stat;
5. confirmation all paths are inside §4 / bounded discovery;
6. exact §7 command results and provenance;
7. adversarial proof results for snapshot drift, lost create response, partial create→seal failure, and lost seal response;
8. live dogfood identifiers/results;
9. predecessor state-sync results:
   - P3A #618 merged/historical;
   - evidence `196144bb...`;
   - reviewed head `a907e623...`;
   - merge `03252d51...`;
   - 3 formal review cycles;
10. roadmap disposition/hoist observation at implementation evidence head;
11. operator waivers (`none` unless explicitly granted);
12. stop conditions encountered and resolution;
13. successors still false:
   - Runbook briefing/instructions;
   - interactive planning scaffold;
   - P3B graph-reference open;
   - P4 Combat mutation.

Formal review cycles use repository law:

```text
one formal reviewer judgment against one distinct head SHA = one review cycle
```

---

## §9 Acceptance rubric

Reviewer accepts only when every item is true:

- [ ] One explicit chosen committed Runbook can start one exact durable Run without manual API work.
- [ ] No Runbook or Run is auto-selected by first/latest/default heuristics.
- [ ] One explicit attempt generates/retains exactly one canonical Run UUID through retry/reconciliation.
- [ ] P2A receives the exact snapshot revision + SHA and remains the authoritative admission boundary.
- [ ] P2B1 manifest is confirmed before navigation; Run creation alone never produces a false READY transition.
- [ ] Unknown create/seal outcomes are reconciled by exact UUID/binding GETs before another identity/write is attempted.
- [ ] A Run created before failed sealing is shown truthfully as incomplete; no auto-rebase/delete/new UUID is invented.
- [ ] Existing Run chooser remains usable when Start Run discovery is unavailable.
- [ ] No backend path, durable schema, Playable grammar, Plan authoring workflow, graph-reference workflow, or Combat mutation was added.
- [ ] P3A predecessor state is atomically synchronized in the named mutable authorities.
- [ ] P3B remains non-dispatchable; named successor is Runbook briefing/instructions, followed by live dogfood/re-anchor.
- [ ] Every §7 required proof has an exact result/provenance or explicit operator waiver.
- [ ] No path outside §4/bounded discovery changed.

---

## Stop conditions

Stop and report rather than expanding if implementation discovers:

- safe retry requires a new durable journal/transaction format;
- incomplete Run cleanup requires delete/rollback semantics;
- the existing P2A/P2B1 APIs cannot represent the exact Start Run invariant;
- Start Run requires modifying workspace authoring/commit behavior;
- a Plan-surface Start button is required to make the capability useful;
- root-level Runbook instruction parsing/projection becomes necessary for starting the Run;
- any backend modification is needed;
- a path outside §4/bounded discovery is required;
- open PR #578 or another active lane begins modifying the same leased Play paths;
- the implementation base moves and rebase changes the predecessor contracts.

Use the standard stop report:

```text
Stop condition:
Why the current mission cannot absorb it:
Invariant clause affected:
Required evidence now missing:
New public/durable contract discovered:
Affected observable paths or ownership layers:
Proposed successor slice:
Tracker or authority update needed:
```

---

## Named successor — do not implement here

**Next capability:** `PLAY — project Runbook briefing/instructions in native Play`.

Purpose:

> Let native Play expose accepted Runbook-level instructional prose — session intent, current state, pressures, GM decisions/reminders, and other unmarked planning guidance — alongside the existing Scene/Beat deck without inventing new durable Playable element kinds or Runtime identities.

That successor is where the recent planning-scaffold product direction first changes what Play *reads*. This Start Run slice changes only how an exact committed Runbook becomes an exact runnable session.

After briefing lands, run a real session dogfood before re-briefing P3B.
