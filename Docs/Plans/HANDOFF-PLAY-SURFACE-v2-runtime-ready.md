---
pr_body_template: |
  ## Handoff pointer
  - Conversation/workstream: PLAY-SURFACE / BF2
  - Flow: PLAY-SURFACE
  - Direction: DESIGN → CODE → REVIEW
  - Handoff: Docs/Plans/HANDOFF-PLAY-SURFACE-v2-runtime-ready.md
  - Branch / PR: agent/play-surface-v2-runtime-ready / PLAY-SURFACE: admit beat-first v2 runtime

  ## Verification pointer
  - Base/head: record exact SHAs in the PR
  - Changed paths: HANDOFF §4 (addendum parser projection of original §8 plus review extras)
  - Verification: HANDOFF §7 (addendum)

  The checked-in handoff, cumulative diff, nano-commit story, and independently
  rerun evidence are the review contract. This body is transport metadata.
---

# HANDOFF — Beat-first v2 Runtime READY and cockpit contract sync (BF2)

**Created:** 2026-08-26
**Status:** READY FOR DISPATCH after exact-current-main re-anchor
**Canonical handoff path:** `Docs/Plans/HANDOFF-PLAY-SURFACE-v2-runtime-ready.md`
**Workstream:** `PLAY-SURFACE / BF2`
**Flow / owner:** `PLAY-SURFACE`
**Handoff direction:** DESIGN → CODE
**Suggested branch:** `agent/play-surface-v2-runtime-ready`
**PR title:** `PLAY-SURFACE: admit beat-first v2 runtime`

> **Dispatch base at design time:** `555a9c7965aca47a24536277b9b36ae569a7285a` — `PLAY-SURFACE: re-anchor cockpit design on scene-centered play`.
>
> Before branch creation, fetch `main`, record the exact base SHA, inspect active PR/worktree leases, and stop if another owner has acquired any production path in §4. A disjoint main advance is not itself a blocker.

Parent authorities:

* `Docs/Design/ARCHITECTURE-playable-material-and-runtime.md`
* `Docs/Design/DESIGN-play-current-moment-cockpit.md`
* `Docs/Design/DESIGN-play-surface-projection.md`
* `Docs/Design/DESIGN-play-surface-gm-cockpit-target.md`
* `Docs/Roadmaps/ROADMAP-con-ready.md`
* `Docs/Plans/STEWARDS-ANCHOR-con-ready.md`
* `Docs/Design/ARCHITECTURE-application-state-layer.md`
* `Docs/Design/ARCHITECTURE-surface-interaction-layer.md`

Predecessors:

* BF1 / PR #628 — Beat-first v2 grammar, index, and manifest foundation.
* APP-STATE AS2–AS5 — historical immutable Runbook WorkRevisions, PostgreSQL Play Runtime, active-Run continuity, legacy Play persistence demolition.
* `555a9c7…` — Scene-centered Play design re-anchor.

---

## 0. Repository truth and capability decomposition

### 0.1 Current truth

The durable Playable model is already:

```text
Runbook
  → Beat
      → Scene
      → Decision
          → Option
```

BF1 already supplies:

```text
dmb-playable-element:v2
dmb_play_run_reference_manifest_v2
Beat-rooted structure indexing
Option activates / suppresses edges
exact Run-bound manifest sealing
v1/v2 manifest discrimination
```

APP-STATE already supplies:

```text
immutable historical WorkRevision
exact Run → WorkRevision binding
PostgreSQL Run + manifest
PostgreSQL progress CAS
PostgreSQL active Run / resume
```

What remains structurally false is BF2:

```text
v2 sealed Run
→ native Play admission
→ durable current Beat
→ optional same-Beat current Scene
→ valid v2 progress mutation
→ derived Choice relevance
→ READY
```

The current native path is still intentionally v1-only and the existing progress admission semantics remain Scene-first.

### 0.2 Candidate outcomes

| Candidate                                | Decision                                                            |
| ---------------------------------------- | ------------------------------------------------------------------- |
| v2 Runtime current-position admission    | **KEEP — BF2 mission**                                              |
| v2 Choice relevance derivation           | **KEEP — same Runtime/projection invariant**                        |
| Scene-centered cockpit implementation    | **SPLIT — BF3**                                                     |
| Collapsible Beat Context / At a Glance   | **SPLIT — BF3**                                                     |
| At-a-Glance category → central workspace | **SPLIT — BF3**, contract synchronized here                         |
| Combat → central workspace               | **SPLIT — P4/Combat**, same presentation contract synchronized here |
| Global/on-demand object finder           | **SPLIT — BF3.x/P3**                                                |
| New Note persistence model               | **SPLIT / not authorized**                                          |
| Agent-assisted Play authoring            | **SPLIT / later**                                                   |

### 0.3 Operator-directed document-sync exception

This PR is explicitly authorized to update the active Play design documents to record the cockpit refinement accepted on 2026-08-26.

These edits **do not count as implemented BF2 capability**.

They constrain BF3/P4 and must say clearly that the corresponding UI remains unimplemented after BF2.

If recording the refinement requires a new runtime schema, projection host, durable workspace mode, Combat ownership change, or Surface Interaction architecture change, **stop and split**. The accepted refinement is presentation composition only.

---

# 1. Mission and merge-ready invariant

## 1.1 Mission

> **A Beat-first v2 Play Run can become truthfully READY against its exact pinned Playable WorkRevision, with durable current-position semantics and derived authored-Choice relevance, so the later Scene-centered cockpit can consume Runtime state without inventing or repairing it in presentation code.**

## 1.2 Merge-ready invariant

> **Every native-ready v2 Run is bound to one exact historical Playable WorkRevision and its sealed v2 manifest; before READY it has one durably admitted `current_beat_id` seeded from the exact pinned document order, `current_scene_id` is either null or a Scene owned by that Beat, all resolved Beats / Decision selections / note anchors are admitted against the sealed v2 membership, progress changes retain the existing `run_revision` CAS contract, and Beat/Scene relevance is derived solely from sealed `activates`/`suppresses` edges plus persisted selections and is never stored independently. Zero-Beat v2 material fails closed, stale mutations fail closed, and existing v1 Run admission/progress behavior remains unchanged.**

## 1.3 What becomes true

```text
v2 Run can cross native Play admission into READY
v2 current Beat is durably seeded before READY
Beat-only current position is legal
current Scene is optional
current Scene must belong to current Beat
explicit Beat + Scene progress is admitted
v2 Decisions / Options are valid Runtime selections
activates / suppresses produces derived relevance
activation wins when the same target is both activated and suppressed
suppressed material remains admitted / addressable
historical pinned WorkRevision remains the source of document order and prose
v1 Runs behave exactly as before
```

## 1.4 What must remain false

```text
BF3 cockpit exists
Beat Context collapses in production
At a Glance collapses in production
At a Glance category expansion exists in production
Scene/object/Combat central-workspace switching exists in production
Combat state becomes Play-owned
global campaign finder exists
Threat → Combat is complete
new Note table/schema exists
workspace projection state is persisted in Run progress
Agent writes Playable or Runtime state
v1 is silently migrated to v2
manifest array order becomes document-order authority
```

---

## 1.5 Pre-dispatch critique

| Question                                            | Answer                                                                                                                                                                                                 |
| --------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Can one invariant govern every BF2 observable path? | **Yes.** Every path is admission or mutation of one exact Run/Playable/manifest binding plus derivation from that state.                                                                               |
| Most likely adversarial failure                     | Two clients open one BF1-created v2 Run with empty progress → both derive seed → one CAS wins → stale completion attempts a second mutation or reports a different current Beat.                       |
| Does §7 detect it?                                  | Yes. PostgreSQL concurrency/idempotency proof plus native-admission test must show convergence on one seed and one truthful READY state.                                                               |
| Easiest boundary to under-test                      | The join between exact historical WorkRevision document order and durable seed mutation. Manifest arrays must not accidentally become ordering authority.                                              |
| Split trigger                                       | Native READY requires a new public endpoint/schema, a new durable state field, or a real BF3 workspace UI merely to avoid misrepresenting v2. Stop and redesign the boundary rather than absorbing it. |

---

# 2. BF2 capability contract

## 2.1 Exact pinned authority

BF2 never derives current position from:

* current/latest Runbook revision;
* current workspace draft;
* filesystem Runbook bytes;
* manifest array order;
* display labels;
* a reconstructed document from current state.

It uses the Run's exact persisted binding:

```text
playable_artifact_id
playable_revision / WorkRevision identity
playable_content_sha256
sealed dmb_play_run_reference_manifest_v2
```

The exact pinned WorkRevision bytes remain document-order authority.

---

## 2.2 First READY admission / seed

A BF1-created v2 Run may already exist with empty progress.

BF2 must make first native admission deterministic and durable.

Seed rule:

```text
exact pinned v2 WorkRevision
→ derive Beat order from document bytes
→ first beat_kind=spine Beat
→ otherwise first Beat
→ zero Beats = fail closed
```

Before the surface reports the Run as READY:

```text
current_beat_id = chosen seed
current_scene_id = null
```

must be durable Runtime truth.

### Concurrency

Two simultaneous first admissions must not produce divergent state.

Allowed pattern:

```text
client A derives same deterministic seed
client B derives same deterministic seed

A CAS succeeds
B CAS conflicts or observes already-applied equivalent state
B rereads exact Run
both converge on same persisted current Beat
```

A stale response may not overwrite a newer Runtime position.

Do not introduce a second lock/lease protocol if existing `run_revision` CAS can own this guarantee.

---

## 2.3 v2 current-position rules

For v2:

```text
current_beat_id
  required once READY

current_scene_id
  optional
```

Legal:

```text
Beat A + no Scene
Beat A + Scene A1
Beat C + Scene C2
resolved Beat remains current
de-emphasized Beat/Scene remains current
```

Illegal:

```text
READY + current_beat_id = null
current_scene_id = Scene C2 while current_beat_id = Beat A
unknown Beat
unknown Scene
Scene from another Beat
display label substituted for stable ID
```

An explicit later `Make Current Scene C2` operation will be represented through the existing Runtime progress mutation:

```text
current_beat_id = parent Beat C
current_scene_id = Scene C2
```

The visual Make Current control belongs to BF3. BF2 must make the underlying existing progress contract capable of admitting this state.

Setting a Beat without a Scene is legal and clears the prior Scene.

---

## 2.4 v1 compatibility

The v1 semantics remain version-scoped and unchanged.

In particular, do not globally replace the current legacy rule merely because v2 permits Beat-only state.

Progress admission must branch by manifest grammar.

Conceptually:

```text
v1
  preserve existing Scene-first membership and current-position rules

v2
  Beat owns Scene
  current Beat required at READY
  current Scene optional
  Scene must belong to Beat
```

Do not convert v1 manifest payloads into v2-shaped pseudo-manifests.

---

## 2.5 v2 selections, resolved Beats, and notes

For v2 progress:

### Resolved Beats

Every `resolved_beat_ids[]` entry must be an admitted Beat in the sealed v2 manifest.

Resolution does not remove navigation/current-position legality.

### Decision selections

For every:

```text
selections[choice_id] = option_id
```

require:

* `choice_id` is an admitted v2 Decision / wire `choice`;
* `option_id` is admitted;
* the Option belongs to that Decision.

Changing or clearing a selection does not itself move current Beat/Scene.

### Notes

Existing:

```text
notes_by_element_id
```

remains the Runtime persistence capability.

For v2, admitted anchors may include:

```text
Beat
Scene
Decision / choice
Option
```

Do not introduce `RunNote`, multiple-note identity, timestamps, move/re-pin, or another durable note representation.

---

# 3. Derived authored-Choice relevance

Relevance is projection state.

It is never persisted.

Input:

```text
sealed v2 manifest edges
+
Run.progress.selections
```

For each Beat/Scene target:

```text
emphasized
  at least one selected Option activates target

de-emphasized
  at least one selected Option suppresses target
  AND no selected Option activates target

default
  otherwise
```

Conflict rule:

```text
activate + suppress → emphasized
```

Resolved state is orthogonal.

No selection:

```text
default authored relevance
```

Clearing/changing a selection:

```text
persist only selections
→ re-derive relevance
```

Do not write:

```text
relevance
activeScenes
possibleBeats
suppressedIds
branchState
```

into Run progress.

`activates` / `suppresses` never delete membership or block inspection/current-position mutation.

---

# 4. Native Play admission contract

BF2 extends the native Play admission seam rather than creating a second Play loader.

The resulting internal ready model must distinguish v1 and v2 truthfully.

For v2, the ready projection must expose enough structural truth for BF3 to consume later:

```text
exact Run binding
exact pinned WorkRevision
v2 manifest
Beat-rooted structure
current Beat
optional current Scene
Decisions / Options in admitted structure
derived Beat/Scene relevance
```

Do not force v2 through the existing v1 Scene-first:

```text
Scene
  → Beats
  → Choices
```

projection shape merely to reuse `RunbookTableDeck`.

### Transitional BF2 presentation

BF2 does **not** own the target cockpit.

If the current `/play` page requires some renderable content for a v2 READY admission, the smallest truthful transitional state is allowed:

```text
Run READY
current Beat
current Scene when present
```

plus enough diagnostics to prove the binding.

It must not:

* recreate the old Scene-first table deck for v2;
* implement At a Glance;
* implement collapsible side regions;
* implement central object/Combat workspaces;
* become a second long-lived cockpit design.

If truthful v2 READY cannot be represented without implementing a substantial new UI, stop and split the staging seam rather than quietly absorbing BF3.

---

# 5. Cockpit design contract synchronization

These design changes are required in the BF2 PR because the operator has accepted them before the series begins.

They describe BF3/P4 target behavior; BF2 does not implement them.

## 5.1 Central workspace is singular

The default:

```text
Beat Context | CURRENT SCENE | At a Glance
```

is a composition, not three equally important permanent panes.

The **central workspace** is the main instrument.

Default content:

```text
current Scene
```

or, when no Scene is current:

```text
current Beat / available Scenes
```

---

## 5.2 Beat Context is collapsible

Beat Context exists for orientation, not permanent width consumption.

It may collapse to a compact affordance while preserving:

```text
current Beat identity
current Scene identity
Runtime current position
```

Collapsing Beat Context is presentation-only.

It must not change Run progress.

No durable `beatContextCollapsed` field is authorized.

---

## 5.3 At a Glance is collapsible

At a Glance is likewise optional chrome around the central workspace.

It may collapse entirely or to a compact affordance.

Collapsing it:

```text
does not alter current context
does not alter admitted references
does not alter Runtime
does not alter Combat
```

No durable `atAGlanceCollapsed` Run field is authorized.

---

## 5.4 At a Glance is a launcher/inventory, not a detail pane

Its persistent form remains presence-first:

```text
Scenes
Locations
NPCs / characters
Threats
Roll tables
Notes
Combat
```

with names/counts/status where useful.

It does **not** show the expanded content of those categories inline.

Opening a category means:

```text
At a Glance category
→ inspect projection
→ central workspace temporarily shows that category
```

Examples:

```text
NPCs
→ central workspace shows contextual NPCs

Threats
→ central workspace shows contextual Threats
→ exact mechanics may open from there

Roll Tables
→ central workspace shows contextual tables

Notes
→ central workspace shows notes for this context

Scenes
→ central workspace shows Scene choices / inspection

Combat
→ central workspace shows Combat instrument
```

The same central workspace is used rather than creating permanent side panels per capability.

---

## 5.5 Exact return

Category/object/tool expansion is inspection unless a specific action explicitly mutates authority.

Conceptual flow:

```text
Scene is current
→ click Threats in At a Glance
→ central workspace = Threat inventory
→ inspect Threat
→ close / back
→ exact same Scene
```

Likewise:

```text
Scene is current
→ click Combat
→ central workspace = Combat
→ collapse / close
→ exact same Scene
```

The Scene is not reconstructed from navigation history. Runtime current Beat/Scene never changed.

Do not create a durable workspace-navigation stack in BF2.

Transient presentation history may eventually support back/close behavior, but it is not campaign truth.

---

## 5.6 Combat is not a special side rail

The existing approved-target image currently suggests Combat as a separate side instrument.

The accepted refinement supersedes that visual implication.

New rule:

> **Combat is one At-a-Glance capability. It may show compact status there. Opening it makes Combat the central workspace; closing it restores the exact current Scene.**

Combat remains Combat-owned.

Play may own:

```text
open / close / projection
origin Scene pointer/context
Add to Combat action
```

Play does not own:

```text
HP
initiative
conditions
combatant mutation
Combat persistence
```

No permanent floating Combat rail is part of the target.

---

## 5.7 Same composition rule for the other categories

Combat does not get a one-off workspace mechanism.

The product target is:

```text
At a Glance
→ choose useful category
→ central workspace
→ inspect/use
→ exact return
```

This is a general Play workspace composition rule.

Implementation should eventually reuse the shared Surface Interaction projection ownership rather than building a second Play-only global projection host.

---

## 5.8 Documents to synchronize

Modify:

```text
Docs/Design/DESIGN-play-current-moment-cockpit.md
Docs/Design/DESIGN-play-surface-projection.md
Docs/Design/DESIGN-play-surface-gm-cockpit-target.md
Docs/Roadmaps/ROADMAP-con-ready.md
```

The cockpit-target document must explicitly state that the 2026-08-26 composition refinement overrides any implication in the older image that:

* Beat Context must always remain expanded;
* At a Glance must always remain expanded;
* Combat occupies a dedicated right-side rail.

The old image may remain as directional evidence. Do **not** invent or regenerate a replacement binary asset inside this code slice.

Update byte-identical design-agent mirrors for every mirrored document touched.

The roadmap should describe the future BF3/P4 behavior truthfully but must not mark it implemented.

---

# 6. Observable paths and failure matrix

| Path                                            | Required BF2 behavior                                      |
| ----------------------------------------------- | ---------------------------------------------------------- |
| Existing v1 Run                                 | Existing admission/render/progress semantics unchanged     |
| New v2 Run with empty progress                  | Deterministically seed first spine/first Beat before READY |
| BF1-created existing v2 Run with empty progress | Same deterministic seed; no migration/reseal               |
| v2 Run already seeded                           | Resume exact persisted Beat/Scene; do not reseed           |
| v2 Beat-only progress                           | Legal                                                      |
| v2 Beat + same-Beat Scene                       | Legal                                                      |
| v2 Beat + foreign Scene                         | Fail closed                                                |
| unknown Beat / Scene                            | Fail closed                                                |
| Decision → own Option                           | Legal                                                      |
| Decision → foreign Option                       | Fail closed                                                |
| suppressed current Scene                        | Still legal/current                                        |
| simultaneous first admissions                   | One seed wins; other converges after CAS conflict/reread   |
| stale progress mutation                         | Existing conflict behavior; no overwrite                   |
| zero-Beat v2 Runbook                            | Never READY                                                |
| malformed/unknown manifest                      | Fail closed                                                |
| pinned historical revision N while N+1 exists   | Continue from N; no latest-revision substitution           |
| dependency unavailable during seed              | Not READY; truthful retryable failure                      |
| derived relevance                               | Recompute; never write separate persisted branch state     |

---

# 7. Implementation contract

```text
Input:
  PlayRunRecord
  exact historical pinned WorkRevision
  sealed PlayRunReferenceManifestV1 | V2
  current PlayRunProgress

Output:
  v1: unchanged admitted native projection
  v2: truthful READY native projection after durable current-Beat seed,
      with Beat-rooted structure, optional current Scene, admitted progress,
      and derived relevance

Durable state:
  existing PlayRunProgress only

New persisted schema:
  none

New endpoint:
  none expected

Mutation authority:
  existing run_revision CAS

Document order authority:
  exact pinned WorkRevision bytes

Relevance authority:
  sealed v2 edges + persisted selections

Failure:
  identity/membership/integrity mismatch → fail closed
  stale CAS → conflict / reread
  dependency unavailable → no fabricated READY state
```

### 7.1 Persistence matrix

| Operation                 | Durable representation              | Rule                                  |
| ------------------------- | ----------------------------------- | ------------------------------------- |
| First v2 seed             | existing `progress.current_beat_id` | Persist before READY                  |
| Set Beat-only             | existing progress                   | `current_scene_id = null` legal in v2 |
| Set Beat + Scene          | existing progress                   | Scene must belong to Beat             |
| Choice selection          | existing `selections`               | Choice/Option membership admitted     |
| Relevance                 | none                                | Derived every read/render             |
| Collapse Beat Context     | none                                | BF3 presentation state                |
| Collapse At a Glance      | none                                | BF3 presentation state                |
| Open At-a-Glance category | none in Run                         | BF3 presentation state                |
| Open Combat workspace     | no Play combat state                | P4 projects Combat authority          |

### 7.2 Identity rules

Stable IDs only:

```text
beat:<slug>
scene:<slug>
choice:<slug>
option:<slug>
```

Display title is never fallback identity.

No first-match label resolution.

No normalized-label current-position mutation.

---

# 8. Files in scope — exclusive expected write lease

## 8.1 Runtime production paths

| Path                                                                      | Purpose                                                                                         |
| ------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------- |
| `apps/live_control_server/services/play_run_registry.py`                  | Version-aware v1/v2 progress admission                                                          |
| `src/application_state/play/service.py`                                   | Existing CAS/persisted aggregate boundary if required for deterministic READY seeding           |
| `apps/live-control-ui/src/playSurface/runbook/nativeRunbookProjection.ts` | v2 native admission, exact seed derivation input, Beat-rooted ready model, relevance derivation |
| `apps/live-control-ui/src/playSurface/PlaySurfacePage.tsx`                | First-admission orchestration and smallest truthful v2 READY presentation                       |
| `apps/live-control-ui/src/playSurface/runbook/index.ts`                   | Export only if new pure BF2 helper/type requires it                                             |

Do not modify `RunbookTableDeck.tsx` merely to force v2 into its v1 Scene-first presentation.

If it proves impossible to keep v1 `RunbookTableDeck` untouched while maintaining truthful BF2 READY state, stop and report the required seam.

## 8.2 Focused tests

| Path                                                                           | Purpose                                                                |
| ------------------------------------------------------------------------------ | ---------------------------------------------------------------------- |
| `tests/test_play_run_progress.py`                                              | v1/v2 progress admission semantics                                     |
| `tests/application_state/test_play_runtime_postgres.py`                        | exact durable seed/CAS/concurrency/historical-revision proof           |
| `apps/live-control-ui/src/playSurface/runbook/nativeRunbookProjection.test.ts` | v2 admission, order, membership, relevance                             |
| `apps/live-control-ui/src/App.test.tsx`                                        | exact Play load/READY boundary only if current app integration owns it |

### Bounded discovery exception

```text
Directory:
  apps/live-control-ui/src/playSurface/runbook/

Maximum additional paths:
  2

Allowed:
  one BF2-local pure helper/type module
  its focused test

Decision rule:
  only if extracting v2 structure/relevance prevents nativeRunbookProjection.ts
  from accumulating unrelated presentation logic.

Not allowed:
  cockpit layout
  At a Glance component
  Combat component
  CSS/theme work
  global finder
```

## 8.3 Design-contract sync

Canonical:

```text
Docs/Design/DESIGN-play-current-moment-cockpit.md
Docs/Design/DESIGN-play-surface-projection.md
Docs/Design/DESIGN-play-surface-gm-cockpit-target.md
Docs/Roadmaps/ROADMAP-con-ready.md
```

Mirrors where present:

```text
Docs/Sources/design-agent/ACTIVE_REFERENCE/DESIGN-play-current-moment-cockpit.md
Docs/Sources/design-agent/ACTIVE_REFERENCE/DESIGN-play-surface-projection.md
Docs/Sources/design-agent/ACTIVE_REFERENCE/DESIGN-play-surface-gm-cockpit-target.md
Docs/Sources/design-agent/ACTIVE_AUTHORITY/ROADMAP-con-ready.md
```

No other roadmap/status doc is automatically authorized.

---

# 9. Explicitly out of scope

Do not modify or claim:

```text
Combat runtime/persistence
Combat service/API semantics
Campaign Supergraph graph semantics
World identity / graph writes
mechanics/statblock authority
Surface Interaction host ownership
AgentInteractionProvider architecture
Plan authoring composition
new Run schema/version
new PlayRunProgress fields
new note schema
global search/finder
At a Glance runtime UI
Beat Context runtime UI
cockpit CSS/layout
new image asset
legacy v1 migration
temporal/tick ledger
```

`ARCHITECTURE-playable-material-and-runtime.md` should not need a semantic architecture change for the accepted cockpit refinement. If it does, stop and return to design.

---

# 10. Evidence required to merge

## 10.1 Backend progress contract

Run:

```bash
uv run pytest tests/test_play_run_progress.py -q
```

Must prove:

* v1 regression unchanged;
* v2 Beat-only legal;
* v2 Beat+same-Beat Scene legal;
* cross-Beat Scene rejected;
* unknown IDs rejected;
* valid Decision/Option selection admitted;
* foreign Option rejected;
* v2 note anchors admitted;
* malformed manifest fails closed.

## 10.2 PostgreSQL Runtime proof

Run:

```bash
uv run pytest tests/application_state/test_play_runtime_postgres.py -q
```

Required cases:

1. BF1-style v2 Run with empty progress → first native admission seed persists.
2. Seed is first spine Beat by pinned document order.
3. No spine → first Beat.
4. Zero Beat → no READY.
5. revision N remains authority after N+1 exists.
6. stale CAS cannot overwrite newer position.
7. simultaneous/equivalent seed attempts converge idempotently.
8. restart/re-read preserves exact current Beat/Scene.

If existing test structure cannot exercise first native admission at this boundary, add the smallest owning-boundary integration proof rather than asserting it indirectly.

## 10.3 Frontend native admission

Run:

```bash
npm --prefix apps/live-control-ui test -- src/playSurface/runbook/nativeRunbookProjection.test.ts
```

Must prove:

* v1 path unchanged;
* v2 manifest is accepted only against exact matching pinned revision;
* v2 structure remains Beat-rooted;
* document bytes, not manifest array order, choose seed/order;
* current Scene is optional;
* current Scene parent is enforced;
* selected Option produces relevance;
* activation beats suppression;
* suppressed targets remain present/addressable;
* no relevance field is written to progress;
* malformed/mixed/unknown contract fails closed.

## 10.4 App boundary

If `PlaySurfacePage.tsx` changes:

```bash
npm --prefix apps/live-control-ui test -- src/App.test.tsx
```

or the narrowest existing owning test that exercises `/play`.

Prove:

```text
v2 empty progress
→ seed operation
→ exact reread / accepted CAS result
→ READY

v2 already seeded
→ no reseed

seed conflict
→ no false READY / stale overwrite
```

A minimal transitional v2 READY display must not instantiate `RunbookTableDeck` using fabricated Scene-first data.

## 10.5 Build / typecheck

```bash
npm --prefix apps/live-control-ui run build
uv run ruff check apps/live_control_server/services/play_run_registry.py src/application_state/play/service.py tests/test_play_run_progress.py tests/application_state/test_play_runtime_postgres.py
git diff --check
```

## 10.6 Doc contract proof

Verify canonical/mirror byte identity for every touched mirrored authority:

```bash
cmp Docs/Design/DESIGN-play-current-moment-cockpit.md \
    Docs/Sources/design-agent/ACTIVE_REFERENCE/DESIGN-play-current-moment-cockpit.md

cmp Docs/Design/DESIGN-play-surface-projection.md \
    Docs/Sources/design-agent/ACTIVE_REFERENCE/DESIGN-play-surface-projection.md

cmp Docs/Design/DESIGN-play-surface-gm-cockpit-target.md \
    Docs/Sources/design-agent/ACTIVE_REFERENCE/DESIGN-play-surface-gm-cockpit-target.md

cmp Docs/Roadmaps/ROADMAP-con-ready.md \
    Docs/Sources/design-agent/ACTIVE_AUTHORITY/ROADMAP-con-ready.md
```

Inspect the final docs and prove they state all of:

```text
Beat Context is collapsible
At a Glance is collapsible
current Scene remains the default central workspace
At a Glance is presence-first
opening an At-a-Glance category uses the central workspace
opening does not change Runtime current position
closing returns to the exact current Scene
Combat is one At-a-Glance entry, not a floating side rail
Combat remains Combat-owned
same central-workspace rule applies to the other At-a-Glance categories
these are BF3/P4 target semantics, not BF2 implementation claims
```

## 10.7 Focused diff proof

```bash
git diff --name-only <BASE>...HEAD
git diff --stat <BASE>...HEAD
git diff --check
```

Any production path outside §8 is a stop condition unless covered by the bounded discovery exception.

---

# 11. Minimal acceptance scenario

Use one representative C2S27-shaped v2 Runbook:

```text
Beat 1 — spine
  Scene A
  Decision X
    Option X1 → activates Beat 2
    Option X2 → suppresses Scene B

Beat 2 — optional
  Scene B

Beat 3 — spine
  Scene C
```

Required sequence:

```text
1. Create/seal exact v2 Run.
2. Confirm initial stored progress has no fabricated Scene.
3. Open through native Play.
4. First READY admission durably seeds Beat 1.
5. Reload.
6. Confirm Beat 1 resumes exactly.
7. Persist Scene A as current.
8. Reload.
9. Confirm Beat 1 + Scene A.
10. Select Option X1.
11. Confirm Beat 2 derives emphasized.
12. Select a configuration that also suppresses Beat 2.
13. Confirm activation wins.
14. Persist Beat 2 with no Scene.
15. Confirm Beat-only state is admitted.
16. Attempt Beat 1 + Scene B.
17. Confirm fail-closed mismatch.
18. Commit newer Runbook revision.
19. Reopen original Run.
20. Confirm original exact WorkRevision and current position remain authoritative.
```

This is a structural/runtime proof, not the BF3 live-table dogfood.

---

# 12. Acceptance rubric

Accept only when all are true:

* [ ] One v2 Run crosses the native admission boundary into READY without Scene-first reinterpretation.
* [ ] READY has a durable `current_beat_id`.
* [ ] Seed uses exact pinned document order, not manifest array order.
* [ ] Zero-Beat v2 material fails closed.
* [ ] Beat-only v2 current position is legal.
* [ ] Scene parentage is enforced.
* [ ] Existing `run_revision` CAS owns mutation concurrency.
* [ ] Concurrent/equivalent first seeds converge without divergent Runtime.
* [ ] Decision/Option membership is validated from the sealed v2 manifest.
* [ ] Relevance is derived from selections + sealed edges and never persisted.
* [ ] Activation wins suppression.
* [ ] Suppression never removes membership/navigation eligibility.
* [ ] Historical pinned WorkRevision remains authority after a newer revision exists.
* [ ] v1 admission/progress/render semantics are unchanged.
* [ ] No second public Runtime API or persisted state contract was introduced.
* [ ] BF3 cockpit UI remains unimplemented and unclaimed.
* [ ] No Combat runtime behavior changed.
* [ ] The four canonical design/roadmap documents capture the accepted collapsible-context / central-workspace refinement.
* [ ] Those docs explicitly state that Combat is an At-a-Glance entry, not a permanent side rail.
* [ ] Canonical/mirror pairs remain byte-identical.
* [ ] No paths outside the §8 lease changed without an explicit stop/review.

---

# 13. Named successors

## BF3 — Scene-centered cockpit

Consumes BF2 truth and implements:

```text
current Scene central workspace
Beat-only state
collapsible Beat Context
collapsible At a Glance
Decision interaction
At-a-Glance category → central workspace
exact close/back return
inspect vs Make Current
Runbook as secondary source/reference
```

## BF3.x / P3 — fast retrieval

```text
cross-Beat inspect
global/on-demand finder
NPC/location/Threat/table lookup
exact statblock hot path
```

## P4 / Combat

```text
Threat → Add to Combat
Combat listed/statused in At a Glance
Combat opens into the same central workspace
Combat-owned state
collapse → exact Scene
durable Combat continuity
```

## BF4 — Plan composition

Beat-first authoring controls may proceed independently on a disjoint lease.

---

# 14. Stop conditions

Stop and report if implementation discovers any of the following:

* v2 READY requires a new persisted progress field;
* first seed cannot be expressed safely with existing CAS semantics;
* document order is unavailable from the exact pinned WorkRevision at admission;
* a new public endpoint is required solely for BF2;
* v1 and v2 cannot coexist without changing v1 behavior;
* native admission requires fabricating Scene-first v2 structure;
* BF2 requires meaningful cockpit layout/component work;
* design refinement requires a second projection host;
* collapse/open workspace state must become durable Run state;
* Combat ownership must change;
* a new Note schema appears necessary;
* a leased production path is owned by another active PR/worktree;
* current `main` materially contradicts this handoff.

Report:

```text
Stop condition:
Why BF2 cannot absorb it:
Invariant clause affected:
Owning boundary:
Missing evidence:
New contract discovered:
Proposed split/successor:
Authority/tracker update required:
```

Do not widen the PR silently.
---

# Review amendments (not part of the original dispatch)

These sections record review-authorized corrections. They do **not** rewrite the dispatch copy above. Cycle 1 review `5035652206` required the dispatch handoff to be checked in without retroactive rewriting. Cycle 2 review `5035983080` found the Cycle 1 repair was a reconstructed post-review contract labeled as exact.

## Provenance

The dispatch body above is recovered verbatim from the 2026-08-26 steward dispatch message (conversation `e8f60a90-cce9-4fce-a6d1-7a419179a84f`), starting at `# HANDOFF — Beat-first v2 Runtime READY and cockpit contract sync (BF2)` through the original stop-condition report block. YAML frontmatter is the repository HANDOFF template wrapper required for PR transport; it is not a rewrite of the dispatch prose.

The file previously committed as `95b9dfdf` was a Cycle 1 reconstruction and is superseded by this restoration plus the amendments below.

## Cycle 1 — review `5035652206` (head `43452172…`)

Already implemented on later heads; recorded here so the original dispatch is not rewritten in place:

1. A READY v2 Run must not be clearable back to empty progress.
2. First seed is the last mutation after a read-only v2 authority preflight. A mismatched Run ↔ manifest ↔ pinned WorkRevision set performs zero Runtime writes.
3. Seed CAS 409 / rebase recovery rebinds the full authority set (Run + manifest + exact committed WorkRevision), not a reread Run paired with stale bytes.
4. Native integrity comparison includes `beat_kind` and `activates`/`suppresses` edges.
5. Opening-Beat derivation uses BF1 fence/grammar admission, not a raw marker scan.
6. This HANDOFF file is the checked-in review contract.

## Cycle 2 — review `5035983080` (head `1427b8c2…`)

1. **Handoff restoration.** The original dispatch copy is preserved above. This addendum is the only place Cycle 1/2 requirements are recorded.
2. **v2 Option authored content.** BF1 represents v2 Options as marked top-level list items. Native READY projection must slice those list items as Option boundaries so Option title/body are the authored list-item text and Choice prose does not absorb Option text. Heading-only slicing is insufficient for v2.
3. **One production first-admission workflow.** `ensure_v2_native_ready()` is the production first-admission authority. Native Play load calls existing `GET /api/live/play-runs/{run_id}?ensure_native_ready=true`, which preflights the pinned authority set and seeds an empty v2 Run. PlaySurfacePage does not independently PUT a seed. Default GET without the query remains a non-mutating read. This is not a new public endpoint; it is an opt-in query on the existing Run GET. Cycle 2 explicitly required either an end-to-end production path or making the tested helper the real first-admission boundary.

## Cycle 3 — review `5036663214` (head `6d343d43…`)

1. **Sealed JSON binding preflight.** `ensure_v2_native_ready()` must compare the sealed manifest document's `run_id`, `playable_artifact_id`, `playable_revision`, and `playable_content_sha256` to the Run before any seed. Row-level identity columns and structural membership are not enough: a persisted JSON document whose binding metadata is corrupted while beats/edges stay identical must perform zero Runtime writes.
2. **One authority generation.** First admission loads Run + sealed manifest from one application-state aggregate/UoW, then loads that exact pinned WorkRevision. Independent Run then manifest reads are forbidden: a rebase that commits between them is a cross-generation read, not integrity corruption. A structure-changing rebase that lands after the coherent snapshot CAS-conflicts and retries onto one generation.

## Cycle 4 — review `5036857233` (head `47f29f67…`)

1. **Removed opening Beat is a generation move, not integrity failure.** A concurrent rebase that removes/renames the preflight opening Beat can 422 the stale seed because application-state admits the candidate against the new manifest before checking `expected_run_revision`. First admission must re-read Run generation/binding after a seed 422; if it moved, reload the coherent authority set and persist the new opening Beat. Same-generation unknown-Beat/integrity 422s remain fail-closed and are not retried. Do not reorder `replace_play_run_progress` merely to emit 409 earlier.

## Parser-facing lease / evidence (does not replace original §8 / §10 / §12)

The original dispatch uses numbered headings, not the `## §N` template the review parser matches. The tables below project the original §8 lease plus Cycle 1–4 authorized extras so `scripts/review_external_pr.py` can extract them.

## §4 Write lease

| Path | Why |
|---|---|
| `Docs/Plans/HANDOFF-PLAY-SURFACE-v2-runtime-ready.md` | Checked-in review contract (original dispatch + this addendum) |
| `apps/live_control_server/services/play_run_registry.py` | Version-aware v1/v2 progress admission; BF1 opening Beat; sealed-structure compare; production `ensure_v2_native_ready`; Cycle 3 sealed JSON binding + one-generation aggregate load; Cycle 4 generation-moved 422 retry |
| `apps/live_control_server/routes/play_runs.py` | Cycle 2: existing GET exposes `ensure_native_ready` so the tested helper is the production first-admission path |
| `src/application_state/play/service.py` | Distinguish legal pre-READY empty progress from clearing an already-seeded v2 current Beat |
| `apps/live-control-ui/src/api/liveApi.ts` | Cycle 2: GET Run may request native-ready first admission |
| `apps/live-control-ui/src/api/liveApi.test.ts` | Cycle 2: exact query-string contract for native-ready GET |
| `apps/live-control-ui/src/playSurface/runbook/nativeRunbookProjection.ts` | v2 native admission, v2-aware authored-content slicing, Beat-rooted ready model |
| `apps/live-control-ui/src/playSurface/runbook/v2RuntimeProjection.ts` | Original bounded discovery: empty progress, opening Beat, sealed-structure compare, relevance |
| `apps/live-control-ui/src/playSurface/PlaySurfacePage.tsx` | Native load uses production GET native-ready; smallest truthful v2 READY presentation |
| `apps/live-control-ui/src/playSurface/runbook/index.ts` | Export only if required |
| `tests/test_play_run_progress.py` | v1/v2 progress admission, including refuse empty-clear after READY |
| `tests/application_state/test_play_runtime_postgres.py` | Durable seed/CAS/concurrency and helper-level first admission |
| `tests/test_live_play_run_progress.py` | Cycle 2–4: HTTP owning-boundary GET native-ready against PostgreSQL, including JSON binding mismatch, rebase that removes the stale opening Beat, and same-generation 422 fail-closed |
| `apps/live-control-ui/src/playSurface/runbook/nativeRunbookProjection.test.ts` | v2 admission, Option/Choice disjoint authored content, edges, relevance |
| `apps/live-control-ui/src/playSurface/runbook/v2RuntimeProjection.test.ts` | BF2-local helper tests |
| `apps/live-control-ui/src/App.test.tsx` | `/play` load/READY against the production GET native-ready contract |
| `Docs/Design/DESIGN-play-current-moment-cockpit.md` | Original design-contract sync |
| `Docs/Design/DESIGN-play-surface-projection.md` | Original design-contract sync |
| `Docs/Design/DESIGN-play-surface-gm-cockpit-target.md` | Original design-contract sync |
| `Docs/Roadmaps/ROADMAP-con-ready.md` | Original design-contract sync |
| `Docs/Sources/design-agent/ACTIVE_REFERENCE/DESIGN-play-current-moment-cockpit.md` | Byte-identical mirror |
| `Docs/Sources/design-agent/ACTIVE_REFERENCE/DESIGN-play-surface-projection.md` | Byte-identical mirror |
| `Docs/Sources/design-agent/ACTIVE_REFERENCE/DESIGN-play-surface-gm-cockpit-target.md` | Byte-identical mirror |
| `Docs/Sources/design-agent/ACTIVE_AUTHORITY/ROADMAP-con-ready.md` | Byte-identical mirror |

## §5 Explicitly out of scope

| Path | Why |
|---|---|
| `apps/live-control-ui/src/playSurface/runbook/RunbookTableDeck.tsx` | v1 Scene-first deck stays v1-only |
| Combat runtime/persistence/service/API | P4 |
| `ARCHITECTURE-playable-material-and-runtime.md` | stop if cockpit refinement requires a semantic architecture change |
| `apps/live_control_server/services/play_run_reference_manifest.py` | BF1 parser is consumed, not rewritten |

## §7 Evidence required to merge

```bash
uv run pytest tests/test_play_run_progress.py -q
uv run pytest tests/application_state/test_play_runtime_postgres.py tests/test_live_play_run_progress.py -q
pnpm --dir apps/live-control-ui exec vitest run src/playSurface/runbook/nativeRunbookProjection.test.ts src/playSurface/runbook/v2RuntimeProjection.test.ts src/App.test.tsx src/api/liveApi.test.ts
pnpm --dir apps/live-control-ui run build
uv run ruff check apps/live_control_server/services/play_run_registry.py apps/live_control_server/routes/play_runs.py src/application_state/play/service.py tests/test_play_run_progress.py tests/application_state/test_play_runtime_postgres.py tests/test_live_play_run_progress.py
git diff --check
cmp Docs/Design/DESIGN-play-current-moment-cockpit.md Docs/Sources/design-agent/ACTIVE_REFERENCE/DESIGN-play-current-moment-cockpit.md
cmp Docs/Design/DESIGN-play-surface-projection.md Docs/Sources/design-agent/ACTIVE_REFERENCE/DESIGN-play-surface-projection.md
cmp Docs/Design/DESIGN-play-surface-gm-cockpit-target.md Docs/Sources/design-agent/ACTIVE_REFERENCE/DESIGN-play-surface-gm-cockpit-target.md
cmp Docs/Roadmaps/ROADMAP-con-ready.md Docs/Sources/design-agent/ACTIVE_AUTHORITY/ROADMAP-con-ready.md
git diff --name-only origin/main...HEAD
git diff --stat origin/main...HEAD
```

Must prove, in addition to the original dispatch matrix:

* empty v2 progress is legal only as pre-READY stored state; a READY v2 current Beat cannot be cleared;
* `GET /play-runs/{id}?ensure_native_ready=true` is the production first-admission path and calls `ensure_v2_native_ready`;
* mismatched document/manifest performs zero Runtime writes;
* sealed `beat_kind` and `activates`/`suppresses` participate in integrity comparison;
* opening Beat derivation honors BF1 fence/grammar admission;
* v2 Option title/body come from marked list-item text; Choice prose and Option text remain disjoint;
* default GET without the query remains a non-mutating read;
* native-ready GET refuses a sealed JSON binding mismatch (artifact/revision/sha) with zero Runtime writes;
* native-ready GET that straddles a rebase which **removes** opening Beat A and adds B converges on B, not `integrity_failure`;
* same-generation unknown-Beat/integrity 422 during native-ready seed is fail-closed and is not retried.

## §9 Acceptance rubric

- [ ] The checked-in HANDOFF preserves the original dispatch copy and records review amendments separately.
- [ ] One v2 Run crosses native admission into READY without Scene-first reinterpretation.
- [ ] READY has a durable `current_beat_id`.
- [ ] Seed uses exact pinned document order via BF1 grammar, not manifest array order.
- [ ] A READY v2 Run cannot be cleared back to empty progress.
- [ ] First seed is owned by `ensure_v2_native_ready` on the existing Run GET.
- [ ] Authored v2 Option text is present in the READY model and disjoint from Choice body.
- [ ] v1 admission/progress/render semantics are unchanged.
- [ ] No new public endpoint path was introduced.
- [ ] BF3 cockpit UI remains unimplemented and unclaimed.
- [ ] Canonical/mirror pairs remain byte-identical.
- [ ] Native-ready first admission proves sealed JSON binding before any seed.
- [ ] First admission loads one Run+manifest generation and converges when a concurrent rebase removes the stale opening Beat.
- [ ] Same-generation native-ready seed 422s remain fail-closed.

## Completion

PR #652 merged.

Accepted implementation head:
  `9dffcab96ad3f527efedc3981aea805a63deb4df`

Merge:
  `39ef105d3996ef0062dd45a089fecada14915436`

Formal review cycles:
  5

BF2 outcome:
  DONE

Successor:
  BF3A current-moment cockpit
