---
pr_body_template: |
  ## Handoff pointer
  - Conversation/workstream: PLAY-SURFACE / BF3A
  - Flow: PLAY-SURFACE
  - Direction: DESIGN → CODE → REVIEW
  - Handoff: Docs/Plans/HANDOFF-PLAY-SURFACE-current-moment-cockpit.md
  - Branch / PR: agent/play-surface-current-moment-cockpit / PLAY-SURFACE: make the current moment table-usable

  ## Verification pointer
  - Base/head: record exact SHAs in the PR
  - Changed paths: HANDOFF §4
  - Verification: HANDOFF §7

  The checked-in handoff, cumulative diff, nano-commit story, and independently
  rerun evidence are the review contract. This body is transport metadata.
---

# HANDOFF — Scene-centered Current Moment cockpit (BF3A)

**Created:** 2026-08-26
**Status:** READY FOR DISPATCH
**Canonical handoff path:** `Docs/Plans/HANDOFF-PLAY-SURFACE-current-moment-cockpit.md`
**Workstream:** `PLAY-SURFACE / BF3A`
**Flow / owner:** `PLAY-SURFACE`
**Handoff direction:** DESIGN → CODE
**Suggested branch:** `agent/play-surface-current-moment-cockpit`
**PR title:** `PLAY-SURFACE: make the current moment table-usable`

> **Dispatch base:** `39ef105d3996ef0062dd45a089fecada14915436`
>
> This is current `main`, containing merged PR #652 / BF2.
>
> Before branch creation, fetch `main`, record the exact base SHA, and inspect
> active PR/worktree leases again. A disjoint `main` advance is not itself a
> blocker; overlapping writes are.

Parent authorities:

- `AGENTS.md`
- `Docs/Design/ARCHITECTURE-playable-material-and-runtime.md`
- `Docs/Design/ARCHITECTURE-surface-interaction-layer.md`
- `Docs/Design/DESIGN-play-current-moment-cockpit.md`
- `Docs/Design/DESIGN-play-surface-projection.md`
- `Docs/Design/DESIGN-play-surface-gm-cockpit-target.md`
- `Docs/Roadmaps/ROADMAP-con-ready.md`
- `Docs/Plans/STEWARDS-ANCHOR-con-ready.md`

Completed predecessor:

- BF2 / PR #652
- accepted head: `9dffcab96ad3f527efedc3981aea805a63deb4df`
- merge commit: `39ef105d3996ef0062dd45a089fecada14915436`
- review cycles: **5**
- outcome: v2 native READY, deterministic Beat seed, exact historical
  WorkRevision admission, Beat/Scene progress semantics, derived Choice
  relevance, server-owned first admission.

Parallel work:

- CUTOVER remains separately owned.
- Agent Interaction / trace work remains separately owned.
- Neither is a prerequisite for this slice.
- Do not modify their authority/runtime paths merely to implement BF3A.

---

## §0 Re-anchor and capability decomposition

### 0.1 Current executable truth

BF2 now supplies a native v2 READY model:

```text
NativeRunbookReadyV2
  run
  exact pinned WorkRevision
  Beat-rooted authored projection
  currentBeatId
  currentSceneId?
  Beats[]
    Scenes[]
    Decisions[]
      Options[]
  relevanceByTargetId
```

The production `/play` route truthfully obtains that model.

The current v2 presentation is still transitional:

```text
v2 Run READY
current Beat <id>
current Scene <id | none>
revision / digest
```

There is not yet a Scene-centered table cockpit.

### 0.2 Candidate capabilities

| Candidate                                                  | Decision                                              |
| ---------------------------------------------------------- | ----------------------------------------------------- |
| Render exact persisted current Scene as dominant workspace | **KEEP — BF3A mission**                               |
| Truthful Beat-only state when no Scene is current          | **KEEP — same invariant**                             |
| Collapsible Beat Context                                   | **KEEP — presentation of same current moment**        |
| Collapsible At a Glance                                    | **KEEP — presentation of same current moment**        |
| `Scenes` as first At-a-Glance workspace                    | **KEEP — proves workspace swap contract**             |
| Inspect another Scene in current Beat                      | **KEEP — proves inspect semantics**                   |
| Explicit Make Current for inspected/current-Beat Scene     | **KEEP — proves Runtime mutation boundary**           |
| Decision Option selection                                  | **SPLIT — BF3B**                                      |
| Relevance presentation after Decision                      | **SPLIT — BF3B**                                      |
| NPC/Location/Threat/Table contextual categories            | **SPLIT — BF3C / later contextual projection slices** |
| Cross-Beat inspection                                      | **SPLIT — BF3.x / P3**                                |
| Global finder                                              | **SPLIT — BF3.x / P3**                                |
| Runbook reference workspace                                | **SPLIT — later BF3 slice**                           |
| Notes authoring UX                                         | **SPLIT — later BF3 slice**                           |
| Threat → exact statblock                                   | **SPLIT — P3**                                        |
| Combat workspace                                           | **SPLIT — P4 / Combat**                               |
| Agent interaction changes                                  | **SPLIT — Agent Interaction lane**                    |

### 0.3 Why Scenes is the first At-a-Glance category

BF2 already has authoritative current-Beat Scene membership, titles, bodies,
stable IDs, relevance, and parentage.

It does **not** yet give this component a general contextual inventory of NPCs,
Locations, Threats, Roll Tables, or mechanics.

Do not fabricate those categories merely to make the target layout look full.

BF3A proves the interaction mechanism with one real category:

```text
At a Glance
→ Scenes
→ same central workspace
→ inspect
→ exact return
→ optional explicit Make Current
```

Later categories extend that proven mechanism.

---

## §1 Mission and merge-ready invariant

### 1.1 Mission

> **Turn a READY v2 Run into the first genuinely table-usable current-moment
> cockpit: the persisted Scene is the default central workspace, Beat-only
> Runtime is represented truthfully, and the GM may transiently inspect
> current-Beat Scenes without moving the table moment until an explicit
> Make Current action succeeds.**

### 1.2 Merge-ready invariant

> **For every admitted v2 READY Run, Play renders exactly one authoritative
> current moment derived from persisted `currentBeatId/currentSceneId`.
> Collapsing context, opening the Scenes inventory, and inspecting another
> Scene are transient presentation operations that perform zero Runtime
> writes. Only explicit Make Current may change current position, through one
> existing Run-progress CAS mutation preserving all unrelated progress.
> Success renders the returned authoritative moment; conflict/unknown outcome
> reconciles from durable Runtime rather than pretending the requested Scene
> became current. Closing/back always resolves to the exact authoritative
> current moment.**

### 1.3 What becomes true

```text
READY + currentSceneId
→ current Scene is dominant central workspace

READY + no currentSceneId
→ Beat-only central workspace
→ no Scene fabricated

Beat Context
→ visible and collapsible

At a Glance
→ visible and collapsible
→ real Scenes presence

Scenes category
→ central workspace Scene inventory
→ no Runtime mutation

Inspect Scene
→ central workspace inspection
→ current Runtime position unchanged

Back / close
→ exact persisted current Scene
→ or exact Beat-only state

Make Current
→ one progress CAS
→ Beat + Scene set intentionally
→ server response becomes authoritative

reload
→ exact durable current moment resumes
```

### 1.4 What must remain false

```text
Decision selection UI
Decision consequence/relevance UI
cross-Beat Scene browsing
global finder
NPC object sheet
Location object sheet
Threat object sheet
exact statblock hot path
Notes lifecycle redesign
Combat workspace
Runbook central reference mode
durable collapse state
durable workspace-navigation state
new backend API/schema
new Surface Interaction host
Play-owned projection-pane infrastructure
Agent dependency
automatic Scene selection
optimistic durable current-position claims
```

---

## §2 Product and interaction contract

### 2.1 Resolve the authoritative current moment

Given `NativeRunbookReadyV2`:

```text
currentBeat
  = Beat whose id == deck.currentBeatId

currentScene
  = null
    OR Scene whose id == deck.currentSceneId
       and beatId == currentBeat.id
```

BF2 admission should already guarantee these identities.

BF3A must still fail safely if an impossible in-memory state appears.

Do not silently choose:

* first Beat;
* first Scene;
* first emphasized Scene;
* first spine Scene;
* most recently inspected Scene.

### 2.2 Default central workspace

When a Scene is current:

```text
CURRENT SCENE

<Scene title>

<authored bodyText>
```

The current Beat remains accessible in Beat Context.

When no Scene is current:

```text
CURRENT BEAT

<Beat title>

<authored Beat bodyText>

Scenes in this Beat
  Scene A      Make Current
  Scene B      Make Current
```

This is not a preview.

The UI must communicate that no Scene is current.

### 2.3 Authored content boundary

BF3A renders the authored content already projected by BF2:

```text
title
bodyText
```

Do not invent semantic parsing for:

* Read Aloud;
* GM Note;
* Rules Now;
* Warning;
* clocks;
* bespoke block cards.

If useful semantic-block presentation requires a new projection contract,
stop and split it.

Plain authored content is sufficient for BF3A.

### 2.4 Beat Context

Beat Context presents current Beat orientation.

Minimum useful content:

```text
Beat title
Beat kind when useful
Beat bodyText
resolved status if already available
relevance status if useful and non-distracting
```

It is collapsible.

Collapse state is local presentation state only.

```text
collapse Beat Context
→ zero network writes
→ currentBeatId unchanged
→ currentSceneId unchanged
```

When collapsed, enough identity remains visible to recover orientation,
for example the Beat title or a compact labeled affordance.

Exact geometry is not frozen.

### 2.5 At a Glance

BF3A ships one real category:

```text
Scenes
```

It may show:

```text
Scenes 3
```

or a similarly compact presence-first summary.

The full Scene content does not render inline in the rail.

At a Glance is collapsible.

Collapse is local presentation state only.

Do not display disabled/fake NPC, Threat, Combat, Notes, or Location categories
just to resemble the target image.

### 2.6 Central workspace modes

Use a small local presentation model.

Conceptually:

```ts
type PlayWorkspace =
  | { kind: "current" }
  | { kind: "scenes" }
  | { kind: "scene-inspect"; sceneId: string };
```

This is not a durable schema and not a universal workspace registry.

It lives only for the active Play surface instance.

Run change/unmount must not leak this state into another Run.

### 2.7 Open Scenes

Clicking the At-a-Glance Scenes category:

```text
current workspace
→ Scenes inventory
```

This performs zero Runtime writes.

The Scenes inventory is scoped to the **current Beat** in BF3A.

Each Scene should visibly distinguish:

* current;
* not current;
* relevance when useful;
* inspect action;
* Make Current action.

An empty Beat is truthful:

```text
No authored Scenes in this Beat.
```

Do not redirect to Runbook or invent filler.

### 2.8 Inspect Scene

Inspecting a Scene:

```text
Scene inventory
→ scene-inspect workspace
```

It must be visibly labeled as inspection when the Scene is not current.

The shell must preserve enough current-moment orientation that the GM can tell:

```text
Current: Tunnel Breach
Inspecting: Courtyard
```

Inspection performs zero Runtime writes.

No ordinary card click is Make Current.

### 2.9 Exact return

From Scene inventory or Scene inspection:

```text
Back / Close
→ workspace = current
→ resolve central content from authoritative deck.currentBeatId/currentSceneId
```

Do not store a copied Scene snapshot as the source of return truth.

If current Runtime changed while an inspection was open, return to the
**new authoritative current moment**, not the stale origin snapshot.

This is important.

“Exact return” means exact current Runtime context, not replaying stale UI
history.

### 2.10 Make Current

BF3A allows Make Current only for a Scene owned by the current Beat.

The mutation is:

```text
nextProgress = {
  ...run.progress,
  current_beat_id: targetScene.beatId,
  current_scene_id: targetScene.id,
}
```

One existing CAS request:

```text
PUT /api/live/play-runs/{runId}/progress
expected_run_revision = current run_revision
```

Preserve exactly:

```text
resolved_beat_ids
selections
notes_by_element_id
```

No optimistic current-position mutation.

Before success:

```text
UI may show "Saving…"
authoritative current Scene remains the old Scene
```

On success:

```text
returned PlayRunRecord
→ authoritative Runtime
→ current workspace
→ newly current Scene becomes central
```

### 2.11 Mutation conflict / unknown outcome

Mirror the existing fail-safe Play posture rather than inventing a second
concurrency model.

On mutation error:

1. do not claim the requested Scene became current;
2. reread the exact Run;
3. if the Playable binding is unchanged, overlay the returned Runtime onto the
   admitted v2 projection;
4. if the binding changed, trigger full exact Run admission;
5. show a truthful conflict/unknown banner.

Do not automatically retry or merge a human Runtime mutation.

### 2.12 v2 Runtime overlay

Add a pure v2 equivalent of the existing v1 runtime overlay.

Conceptually:

```ts
overlayRuntimeOnV2Ready(
  admission: NativeRunbookReadyV2,
  run: PlayRunRecord,
): NativeRunbookReadyV2 | null
```

It must:

* require the same exact Run/Playable binding;
* require non-null admitted `current_beat_id`;
* require current Beat membership;
* require optional current Scene membership;
* require Scene parent == current Beat;
* replace the authoritative Run/current IDs;
* re-derive relevance from the sealed v2 manifest + returned selections;
* update Beat/Scene relevance projections accordingly;
* return null rather than guessing when coherence cannot be proven.

Although BF3A does not yet mutate Decisions, external/concurrent Runtime changes
may alter selections. The overlay must not leave relevance stale.

### 2.13 Collapse semantics

Beat Context and At a Glance collapse independently.

They are allowed to reset on:

* reload;
* Run switch;
* component remount.

They are not required to persist.

Do not add:

```text
beat_context_collapsed
at_a_glance_collapsed
workspace_mode
inspected_scene_id
```

to Run progress, APP-STATE, URL state, or another durable store.

### 2.14 Accessibility

Required:

* collapse buttons use `aria-expanded`;
* central workspace has a clear accessible heading;
* current versus inspecting is perceivable without color alone;
* Make Current is an explicit labeled control;
* keyboard focus remains usable;
* closing inspection returns focus to a sensible invoker when practical;
* loading/saving/conflict state is communicated textually.

Do not spend this slice inventing a complete visual design system.

---

## §3 Architecture and ownership boundaries

### 3.1 AppChrome / Surface Interaction

Do not modify AppChrome ownership.

BF3A central workspace is Play surface content inside the existing AppChrome
content slot.

It is **not**:

* a second global Projection Pane host;
* a Tool Bar;
* an Edit Bar;
* an Agent Bar;
* a new Surface Interaction provider.

Do not build a universal workspace registry.

### 3.2 Backend

No backend change is expected.

Reuse:

```text
GET Run
GET manifest
GET exact committed WorkRevision
PUT progress
```

BF2 already owns admission and persistence semantics.

A need for a new endpoint or persisted field is a stop condition.

### 3.3 v1

The existing v1 `RunbookTableDeck` remains supported and unchanged except for
strictly unavoidable shared typing/import changes.

Do not retrofit the new cockpit into v1 in this slice.

### 3.4 Agent Interaction

No Agent Interaction behavior is required.

Do not widen the lane into:

* current Beat/Scene Agent publication;
* turn telemetry;
* traces;
* Agent workspace actions.

Those may consume the cockpit context later.

---

## §4 Write lease

### 4.1 New handoff

| Path                                                        | Purpose                         |
| ----------------------------------------------------------- | ------------------------------- |
| `Docs/Plans/HANDOFF-PLAY-SURFACE-current-moment-cockpit.md` | Checked-in BF3A review contract |

### 4.2 Production UI

| Path                                                                              | Purpose                                                                          |
| --------------------------------------------------------------------------------- | -------------------------------------------------------------------------------- |
| `apps/live-control-ui/src/playSurface/PlaySurfacePage.tsx`                        | Replace transitional v2 READY card with BF3A cockpit; authoritative Run callback |
| `apps/live-control-ui/src/playSurface/playSurface.css`                            | Current-moment layout, rails, central workspace, responsive/accessibility states |
| `apps/live-control-ui/src/playSurface/currentMoment/PlayCurrentMomentCockpit.tsx` | BF3A Scene/Beat cockpit and transient workspace state                            |
| `apps/live-control-ui/src/playSurface/runbook/nativeRunbookProjection.ts`         | v2 authoritative Runtime overlay helper                                          |

### 4.3 Focused tests

| Path                                                                                   | Purpose                                  |
| -------------------------------------------------------------------------------------- | ---------------------------------------- |
| `apps/live-control-ui/src/playSurface/currentMoment/PlayCurrentMomentCockpit.test.tsx` | cockpit interaction contract             |
| `apps/live-control-ui/src/playSurface/runbook/nativeRunbookProjection.test.ts`         | v2 overlay proof                         |
| `apps/live-control-ui/src/App.test.tsx`                                                | `/play` v2 integration and v1 regression |

### 4.4 Backward-looking BF2 state-authority sync

The current roadmap/steward documents still describe BF2 as not implemented.
This PR must synchronize that completed predecessor before claiming the cycle
re-anchored.

| Path                                                                      | Required sync                                                                  |
| ------------------------------------------------------------------------- | ------------------------------------------------------------------------------ |
| `Docs/Plans/HANDOFF-PLAY-SURFACE-v2-runtime-ready.md`                     | Append completion record for merged BF2; do not rewrite original dispatch body |
| `Docs/Roadmaps/ROADMAP-con-ready.md`                                      | BF2 DONE; record #652 / merge SHA; BF3A active first cockpit slice             |
| `Docs/Sources/design-agent/ACTIVE_AUTHORITY/ROADMAP-con-ready.md`         | byte-identical mirror                                                          |
| `Docs/Plans/STEWARDS-ANCHOR-con-ready.md`                                 | re-anchor current truth on BF2 completion / BF3A                               |
| `Docs/Sources/design-agent/ACTIVE_AUTHORITY/STEWARDS-ANCHOR-con-ready.md` | byte-identical mirror                                                          |

BF2 completion facts:

```text
PR: #652
accepted head: 9dffcab96ad3f527efedc3981aea805a63deb4df
merge SHA: 39ef105d3996ef0062dd45a089fecada14915436
review cycles: 5
```

Do **not** mark BF3A complete in those docs.

### 4.5 Bounded discovery

Maximum additional production files under:

```text
apps/live-control-ui/src/playSurface/currentMoment/
```

beyond the two explicitly named above:

```text
1
```

Allowed only if a small pure local workspace/resolver helper materially keeps
the component testable.

Not allowed under bounded discovery:

* registry/plugin system;
* backend helper;
* shared AppChrome host;
* global object projection abstraction.

Any other path is a stop/review condition.

---

## §5 Observable and adversarial paths

| Path                                             | Required behavior                                |
| ------------------------------------------------ | ------------------------------------------------ |
| v2 READY + current Scene                         | Current Scene dominates center                   |
| v2 READY + no current Scene                      | Beat-only center; no fabricated Scene            |
| collapse Beat Context                            | Presentation only; zero PUT                      |
| collapse At a Glance                             | Presentation only; zero PUT                      |
| open Scenes category                             | Same central workspace; zero PUT                 |
| inspect non-current Scene                        | Inspection labeled; zero PUT                     |
| Back from inspection                             | Exact authoritative current moment               |
| current Runtime changes while inspection open    | Back returns to new authoritative current moment |
| Make Current succeeds                            | One CAS; returned Scene becomes central          |
| Make Current preserves notes/selections/resolved | Exact preservation                               |
| double-click while saving                        | No duplicate mutation                            |
| CAS 409                                          | Reconcile exact Run; no retry/merge              |
| unknown mutation outcome                         | Reconcile exact Run; no optimistic current claim |
| reconcile same Playable binding                  | v2 runtime overlay                               |
| reconcile changed Playable binding               | Full exact re-admission                          |
| external selection changed                       | overlay re-derives relevance                     |
| current Beat has zero Scenes                     | Truthful empty Scene inventory                   |
| Run switch while inspecting                      | inspection state does not leak                   |
| reload                                           | persisted current Scene resumes                  |
| v1 Run                                           | Existing `RunbookTableDeck` behavior unchanged   |

---

## §6 Implementation contract

### 6.1 Component boundary

Preferred shape:

```ts
type PlayCurrentMomentCockpitProps = {
  deck: NativeRunbookReadyV2;
  mutationStatus: RunbookMutationStatus;
  onMutationStatus: (status: RunbookMutationStatus) => void;
  onAuthoritativeRun: (run: PlayRunRecord) => void;
};
```

Reusing the existing mutation-status vocabulary is acceptable.

Do not refactor `RunbookTableDeck` into a new shared mutation framework in this
slice.

A generalized Play mutation hook might eventually be worthwhile, but rewriting
v1 and v2 together is a second independently useful/revertible change.

### 6.2 Local workspace state

Keep local:

```ts
current
scenes
scene-inspect(sceneId)
```

No durable store.

No URL contract.

No provider contract.

### 6.3 Scene lookup

All Scene actions derive from BF2's admitted structure.

For BF3A:

```text
target Scene must belong to current Beat
```

Cross-Beat actions are deferred.

### 6.4 Authoritative mutation

Use the current `run_revision`.

Do not mutate the displayed current Scene before the returned record proves it.

### 6.5 Relevance

The cockpit need not make Decision relevance visually prominent yet.

However the v2 Runtime overlay must keep the already-existing relevance model
correct after reconciliation.

BF3B will make those states table-visible.

---

## §7 Required evidence

### 7.1 Current-moment component

Run:

```bash
pnpm --dir apps/live-control-ui exec vitest run \
  src/playSurface/currentMoment/PlayCurrentMomentCockpit.test.tsx
```

Must prove at minimum:

1. persisted Scene is central;
2. Beat-only state does not fabricate Scene;
3. Beat Context collapses with zero progress write;
4. At a Glance collapses with zero progress write;
5. Scenes category opens central workspace with zero progress write;
6. inspect another Scene performs zero progress write;
7. inspection visibly differs from current;
8. Back resolves from authoritative current state;
9. Make Current sends one CAS with Beat+Scene;
10. unrelated progress fields are preserved;
11. controls do not double-submit while saving;
12. successful authoritative response changes central Scene;
13. 409 does not optimistically change current Scene;
14. same-generation/unknown reconcile is truthful;
15. Run switch clears transient inspection state.

### 7.2 v2 Runtime overlay

Run:

```bash
pnpm --dir apps/live-control-ui exec vitest run \
  src/playSurface/runbook/nativeRunbookProjection.test.ts
```

Required cases:

* same binding overlays current Beat/Scene;
* changed binding returns null;
* null v2 current Beat fails overlay;
* unknown Beat fails overlay;
* foreign-parent current Scene fails overlay;
* external selection change re-derives relevance;
* activation still wins suppression.

### 7.3 App integration

Run:

```bash
pnpm --dir apps/live-control-ui exec vitest run src/App.test.tsx
```

Must prove:

```text
v2 READY
→ current-moment cockpit
→ transitional "v2 Run READY" card absent

v1 READY
→ existing RunbookTableDeck unchanged
```

At least one App-level interaction should prove that a returned authoritative
Run from Make Current is reflected by the routed Play surface.

### 7.4 Build

```bash
pnpm --dir apps/live-control-ui run build
git diff --check
```

### 7.5 Predecessor state sync

Verify mirrors:

```bash
cmp Docs/Roadmaps/ROADMAP-con-ready.md \
    Docs/Sources/design-agent/ACTIVE_AUTHORITY/ROADMAP-con-ready.md

cmp Docs/Plans/STEWARDS-ANCHOR-con-ready.md \
    Docs/Sources/design-agent/ACTIVE_AUTHORITY/STEWARDS-ANCHOR-con-ready.md
```

Inspect the canonical docs and prove they record:

```text
BF2 DONE
PR #652
merge 39ef105d3996ef0062dd45a089fecada14915436
5 review cycles
BF3A current/in flight
BF3A not DONE
BF3B/BF3.x/P4 still false
```

### 7.6 Focused diff

```bash
git diff --name-only <BASE>...HEAD
git diff --stat <BASE>...HEAD
git diff --check
```

Every changed path must be in §4 or covered by its bounded discovery rule.

---

## §8 Predecessor state-authority sync contract

This PR consumes BF2.

It therefore owns the routine backward-looking sync that could only become
fully truthful after BF2 merged.

Append to the BF2 handoff rather than rewriting its historical dispatch:

```text
## Completion

PR #652 merged.
Accepted implementation head:
  9dffcab96ad3f527efedc3981aea805a63deb4df

Merge:
  39ef105d3996ef0062dd45a089fecada14915436

Formal review cycles:
  5

BF2 outcome:
  DONE

Successor:
  BF3A current-moment cockpit
```

The roadmap/steward sync should also correct the stale claim that BF2 is
“next” or unimplemented.

Do not alter stable design/architecture documents merely for ceremony.

---

## §9 Acceptance rubric

Merge only when all are true:

* [ ] BF2 predecessor authority sync is complete.
* [ ] v2 transitional READY-ID card is replaced by current-moment cockpit.
* [ ] Current Scene is dominant when persisted.
* [ ] Beat-only state is truthful when current Scene is null.
* [ ] No Scene is automatically selected.
* [ ] Beat Context is collapsible.
* [ ] At a Glance is collapsible.
* [ ] Collapse state performs zero Runtime writes.
* [ ] Scenes is a real presence-first At-a-Glance category.
* [ ] Scenes category uses the central workspace.
* [ ] Scene inspection performs zero Runtime writes.
* [ ] Current versus inspecting is visibly distinguishable.
* [ ] Back returns to authoritative current moment.
* [ ] Explicit Make Current is the only Scene-position mutation.
* [ ] Make Current uses one existing CAS request.
* [ ] Make Current preserves unrelated progress.
* [ ] No optimistic Runtime position is claimed before success.
* [ ] 409/unknown mutation outcome reconciles rather than retries/merges.
* [ ] v2 overlay rejects changed/incoherent binding.
* [ ] v2 overlay re-derives relevance from authoritative selections.
* [ ] v1 table deck is unchanged.
* [ ] No backend/API/schema change landed.
* [ ] No durable collapse/workspace state landed.
* [ ] No AppChrome/Surface Interaction ownership moved.
* [ ] No Decision mutation UI landed.
* [ ] No fake non-Scene At-a-Glance categories landed.
* [ ] No Combat/Agent/global finder scope landed.
* [ ] Every changed path is inside §4.
* [ ] Required local evidence passes on the exact PR head.

---

## §10 Minimal acceptance scenario

Use a representative Mireward-style v2 Run:

```text
Beat: Survive the Current Breach

Scenes:
  Tunnel Breach
  North Gate
  Courtyard
```

Start with:

```text
currentBeatId = Survive the Current Breach
currentSceneId = null
```

Required flow:

```text
1. Open Play.
2. Beat-only cockpit appears.
3. No Scene is labeled current.
4. At a Glance says Scenes: 3.
5. Open Scenes.
6. Central workspace becomes Scene inventory.
7. Inspect Tunnel Breach.
8. Confirm no progress PUT occurred.
9. Back.
10. Confirm Beat-only current moment remains.
11. Make Tunnel Breach Current.
12. Confirm one CAS write.
13. Confirm Tunnel Breach becomes central.
14. Collapse Beat Context.
15. Collapse At a Glance.
16. Confirm Tunnel Breach remains central.
17. Expand At a Glance → Scenes.
18. Inspect Courtyard.
19. Confirm shell still says Tunnel Breach is current.
20. Back.
21. Confirm Tunnel Breach is central again.
22. Reload.
23. Confirm Tunnel Breach resumes exactly.
```

Adversarial extension:

```text
24. Inspect Courtyard.
25. Simulate another writer changing current Scene to North Gate.
26. Back.
27. Confirm central workspace resolves to North Gate, not stale Tunnel Breach.
```

---

## §11 Named successors

### BF3B — Decision interaction and visible relevance

```text
current-context Decisions
Options
select / change / clear selection
authored consequence
selected state
emphasized / de-emphasized Scene/Beat presentation
no auto-navigation
```

### BF3C — contextual At-a-Glance projections

Extend the proven:

```text
category
→ central workspace
→ close
→ current moment
```

mechanism to real admitted contextual data such as:

```text
Notes
Locations
NPCs
Threats
Roll Tables
```

Only categories backed by authoritative resolvable context should ship.

### BF3.x / P3 — unexpected-play retrieval

```text
cross-Beat inspect
global/on-demand finder
known object projection
Threat → exact StatblockRevision
```

### P4 / Combat

```text
Threat → Add to Combat
Combat At-a-Glance status
Combat central workspace
Combat-owned runtime
exact Scene return
durability proof
```

### BF4 — Plan composition

May remain parallel on a disjoint lease.

---

## §12 Stop conditions

Stop and report if BF3A requires any of:

* a new backend endpoint;
* a new persisted Runtime field;
* a durable workspace/collapse schema;
* a change to Playable grammar;
* a change to manifest schema;
* a new Note model;
* a new shared Projection host;
* AppChrome ownership changes;
* Surface Interaction provider changes;
* Agent Interaction changes;
* object/graph retrieval;
* cross-Beat browsing;
* Decision mutation;
* Combat state;
* semantic-block parsing not already present in BF2;
* refactoring v1 and v2 mutation architecture together;
* any production path leased by another active lane.

Report:

```text
Stop condition:
Why BF3A cannot absorb it:
Invariant clause affected:
Owning boundary:
Missing evidence:
New contract discovered:
Proposed split/successor:
Authority update required:
```

Do not widen the PR silently.

---

## Review amendments

The dispatch body above is the original 2026-08-26 steward dispatch. Cycle 1
requirements live here, not in the dispatch sections.

### Cycle 1 — review `5037135564` (head `ceaea412…`)

1. **Collapsed rails must release desktop column space.** Expanding Beat Context
   and At a Glance still uses the full rail tracks. Collapsing must shrink those
   tracks so the central workspace actually widens. Padding-only collapse is not
   enough.

2. **Inspection return focus must target a still-mounted control.** Opening
   inspection unmounts the Scene inventory, so the clicked Inspect button is not
   a valid focus restore target. Restore to the Scenes At-a-Glance launcher when
   it remains mounted, otherwise to the At a Glance toggle. Prove this with a
   focus regression.

Must prove, in addition to the original dispatch matrix:

* collapsed Beat Context / At a Glance set shell `data-beat-collapsed` /
  `data-glance-collapsed` and do not keep expanded rail tracks;
* Back from inspection focuses the mounted Scenes launcher;
* Back from inspection after At a Glance is collapsed focuses a still-mounted
  At a Glance control.
