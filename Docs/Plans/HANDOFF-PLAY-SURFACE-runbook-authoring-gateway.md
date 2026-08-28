---
pr_body_template: |
  ## Handoff pointer
  - Conversation/workstream: PLAY-SURFACE / BF4A
  - Flow: PLAY-SURFACE
  - Direction: DESIGN → CODE → REVIEW
  - Handoff: `Docs/Plans/HANDOFF-PLAY-SURFACE-runbook-authoring-gateway.md`
  - Branch / PR: `agent/play-surface-runbook-authoring-gateway` / `PLAY-SURFACE: make native Runbooks editable`

  ## Verification pointer
  - Base/head: record exact SHAs in the PR
  - Changed paths: HANDOFF §7
  - Verification: HANDOFF §9

  The checked-in handoff, cumulative diff, nano-commit story, real browser
  authoring witness, and independently rerun evidence are the review contract.
  This body is transport metadata.
---

# HANDOFF — Native Runbook authoring gateway (BF4A)

**Created:** 2026-08-28  
**Status:** READY FOR DISPATCH  
**Canonical handoff path:** `Docs/Plans/HANDOFF-PLAY-SURFACE-runbook-authoring-gateway.md`  
**Workstream:** `PLAY-SURFACE / BF4A`  
**Flow / owner:** `PLAY-SURFACE`  
**Handoff direction:** DESIGN → CODE  
**Suggested branch:** `agent/play-surface-runbook-authoring-gateway`  
**PR title:** `PLAY-SURFACE: make native Runbooks editable`

> **Dispatch base:** `87a769d05605ff021d28f0b69c5d7ab0b8205440`
>
> This is current `main`, containing merged DF0 / PR #657.
>
> Re-fetch `main` and inspect active write leases immediately before
> implementation. Do not silently absorb overlapping work.

Parent authorities:

- `AGENTS.md`
- `Docs/Design/ARCHITECTURE-playable-material-and-runtime.md`
- `Docs/Design/DESIGN-play-current-moment-cockpit.md`
- `Docs/Design/DESIGN-playable-authoring-and-adoption.md`
- `Docs/Design/ARCHITECTURE-application-state-layer.md`
- `Docs/Roadmaps/ROADMAP-con-ready.md`
- `Docs/Plans/STEWARDS-ANCHOR-con-ready.md`

Completed predecessors:

```text
BF2 / PR #652
  DONE
  accepted head:
    9dffcab96ad3f527efedc3981aea805a63deb4df
  merge:
    39ef105d3996ef0062dd45a089fecada14915436
  review cycles:
    5

BF3A / PR #655
  DONE — Current Moment
  accepted head:
    3d5925c8ad1bdbe934020e1c4cd7f2f3fafbbec7
  merge:
    4d82f12ad9c6d679b5dbce83db527eb7dbd27957
  review cycles:
    2

DF0 / PR #657
  DONE — local Play dogfood gateway
  accepted head:
    dc20fe8e63eec691265e75eb73c69f441ffd779d
  merge:
    87a769d05605ff021d28f0b69c5d7ab0b8205440
  review cycles:
    3
```

Active parallel lanes at design time:

```text
#659 AGENT-INTERACTION
  AgentRuntime / Hermes backend boundary
  no BF4A write-lease overlap identified

#651 CUTOVER
  DungeonMind World Graph authority continuity
  no BF4A write-lease overlap identified
```

BF3B status at dispatch:

```text
PAUSED ON PRODUCT PREREQUISITE

Cockpit implementation has not started.
The BF3B handoff remains useful and should not be rewritten to hide the stop.
After BF4A merges, re-anchor BF3B onto then-current main and resume it.
```

---

## §0 Why BF4A exists

### 0.1 DF0 made Play reachable; BF3B exposed the next false assumption

DF0 now proves the ordinary local path:

```text
explicit APP-STATE setup
→ Play
→ Create blank Runbook
→ Start exact Run
→ BF3A Current Moment
→ reload/resume
```

The next intended capability, BF3B, is authored Decision interaction:

```text
Decision
→ Options
→ select/change/clear
→ consequence
→ derived relevance
```

But a real GM cannot currently produce the Decision-bearing Runbook needed to
dogfood BF3B through ordinary product UI.

Observed product truth:

```text
Play Create blank Runbook
  → one Untitled Beat
  → no Decision / Option
  → target_relpath = null

Play Runbook projection
  → read/runtime surface, not authoring surface

Plan selector
  → lists kind=plan only

Plan ?documentId=<runbook UUID>
  → can resolve the Runbook when the operator already knows the opaque ID

Plan Canvas
  → shared TipTap authoring machinery can load the Runbook

Plan Save
  → currently refuses the pathless Runbook because canSave requires
     target_relpath != null
```

That hidden `?documentId=<uuid>` path proves the authoring substrate is close.
It does **not** count as a product workflow.

### 0.2 The owning defect

The current Plan Canvas save gate encodes a filesystem-era assumption:

```text
save allowed only when target_relpath exists
```

That remains appropriate for current `kind=plan` behavior, but is wrong for an
APP-STATE-native Runbook.

A Runbook is now a first-class WorkObject / WorkRevision authority. Its durable
identity is not a filesystem path. DF0 deliberately creates pathless Runbooks,
and TipTap prepare/commit already supports them.

Therefore BF4A freezes this product/architecture correction:

> **A Runbook WorkObject does not require `target_relpath` to be edited or
> committed. Path remains an optional projection/storage attribute; WorkObject
> identity and immutable WorkRevision bytes are the authoring authority.**

### 0.3 Why BF3B must wait

Continuing BF3B with fixtures or a memorized `?documentId=` URL would repeat the
pre-DF0 failure mode:

```text
automated test proves capability
≠
GM can actually reach capability
```

BF4A is therefore a narrow prerequisite, not a reprioritization away from
BF3B.

---

## §1 Mission and merge-ready invariant

### 1.1 Mission

> **Make an existing native Runbook a normal editable product object. From the
> Play Runbook chooser, a GM can explicitly open the selected Runbook in the
> existing authoring surface, edit/paste canonical Markdown, and Save a new
> immutable WorkRevision even when that Runbook has no `target_relpath`. No
> existing Run is automatically rebased or moved.**

### 1.2 Merge-ready invariant

> **For any active committed `kind=runbook` WorkObject discoverable in Play,
> including a DF0-created pathless Runbook, the operator can select it and use
> an explicit `Edit Runbook` action to open that exact WorkObject in the normal
> TipTap authoring surface. The editor loads the exact current document,
> identifies it truthfully as a Runbook, permits ordinary editing and canonical
> Markdown paste, and commits through the existing prepare/commit pipeline to a
> new immutable WorkRevision. Pathless Runbooks are saveable; existing Plan
> save rules remain unchanged. Saving never mutates an existing Play Run's
> pinned revision, Runtime progress, manifest, current Beat/Scene, or active Run
> selection.**

### 1.3 What becomes true

```text
Play chooser
→ select committed Runbook
→ Edit Runbook
→ same WorkObject opens in ordinary editor
→ edit / canonical Markdown paste
→ Save
→ new immutable WorkRevision
→ return to Play
→ Start exact Run from current committed revision
```

For the DF0 blank object specifically:

```text
Create blank Runbook
→ selected Blank Runbook
→ Edit Runbook
→ add canonical Beat/Scene/Decision/Option Markdown
→ Save revision 2
→ Play
→ Start exact Run
→ revision 2 is the explicit new-Run binding
```

### 1.4 What remains false

```text
structure-aware Beat insertion
structure-aware Scene insertion
Insert Decision control
Insert Option control
branch editor
activates/suppresses visual authoring
BF3B Decision runtime controls
automatic Run rebase
automatic Start Run
automatic World publication
Runbook filesystem-path creation
mixed Plan/Runbook selector redesign
new persistence
new backend endpoint
```

---

## §2 Capability decomposition

| Candidate | Decision |
|---|---|
| `Edit Runbook` from ordinary Play chooser | **KEEP — core mission** |
| Open exact selected Runbook WorkObject in existing editor | **KEEP** |
| Save pathless `kind=runbook` through existing TipTap pipeline | **KEEP** |
| Preserve current Plan path requirement | **KEEP — regression law** |
| Canonical Markdown paste in Runbook | **KEEP — reuse existing capability** |
| Commit immutable next WorkRevision | **KEEP — existing authority** |
| Return to Play through ordinary AppChrome navigation | **KEEP — existing navigation** |
| Existing Run remains pinned to old revision after Save | **KEEP — mandatory authority proof** |
| Add Runbooks to normal Plan selector | **REJECT / DEFER** |
| Rename Plan surface to generic Authoring | **REJECT** |
| New Runbook editor route | **REJECT unless stop condition proves reuse impossible** |
| Structure-aware authoring palette | **SPLIT — BF4** |
| Decision/Option insert controls | **SPLIT — BF4** |
| BF3B runtime selection UI | **SPLIT — BF3B** |
| Auto-rebase current Run after Save | **REJECT** |
| Auto-start new Run after Save | **REJECT** |
| Create filesystem target for pathless Runbook | **REJECT** |
| Change WorkObject / WorkRevision schema | **REJECT** |
| New backend persistence/API | **REJECT** |

This slice must stay one independently useful capability:

> **Reopen and save the Runbook you already have.**

---

## §3 Product interaction contract

### 3.1 Play is the discovery point

DF0 already makes active Runbooks visible inside `StartRunPanel`.

BF4A extends that existing product point rather than teaching the operator an
opaque UUID URL.

Required chooser behavior:

```text
Start a Run

[ Blank Runbook · <id> ]   selected

[ Edit Runbook ]
[ Start exact Run ]
```

`Edit Runbook` is enabled only when a Runbook is selected.

A newly created blank Runbook is already selected by DF0, so the immediate
first-use flow is:

```text
Create blank Runbook
→ Edit Runbook
```

No Run must be created merely to unlock editing.

### 3.2 Navigation identity

The edit action must navigate using the exact WorkObject UUID already owned by
Play:

```text
/plan?documentId=<exact runbook document_id>
```

or the equivalent existing document-selection helper.

Do not derive identity from:

```text
title
filesystem path
target session
list position
latest Run
```

Do not create a second Runbook copy for editing.

### 3.3 Existing Plan selector remains Plan-only

BF4A does not broaden the normal Plan selector.

Current default Plan behavior remains:

```text
no explicit documentId
→ list/select kind=plan
```

The Runbook enters the editor only through an explicit exact document identity
from Play.

This keeps the slice narrow and avoids prematurely deciding that Plan should
become a generic mixed-document browser.

### 3.4 Truthful editor identity

When the explicitly opened document is `kind=runbook`, the authoring surface
must not silently coerce it to `kind=plan`.

At minimum the visible authoring context must make the loaded object's title
and Runbook kind recoverable to the operator.

Preferred human-facing framing:

```text
Editing Runbook · Blank Runbook
```

Exact wording is not frozen, but the operator must not reasonably believe they
are editing a different Plan WorkObject.

Do not expose opaque document UUID as the primary label.

### 3.5 Return to Play

No bespoke return-stack state is authorized.

Ordinary AppChrome `Play` navigation is sufficient:

```text
Save
→ Play
→ chooser / existing Run
```

The editor does not auto-start or auto-rebase anything on exit.

---

## §4 Save contract

### 4.1 Kind-aware save eligibility

The current Canvas guard is conceptually:

```text
canSave = targetRelpath exists
```

BF4A changes the product law to:

```text
kind == plan
  → retain existing targetRelpath requirement

kind == runbook
  → targetRelpath may be null
  → ordinary authoring/save is allowed
```

Do not globally delete the Plan guard.

Do not fabricate a target path merely to satisfy the old condition.

### 4.2 Existing TipTap authoring pipeline remains owner

Runbook Save must continue through the ordinary shared authoring machinery:

```text
WorkspaceDocument snapshot
→ TipTap editor
→ prepare write
→ commit write
→ immutable WorkRevision
→ refreshed WorkspaceDocument record/snapshot
```

Do not introduce:

```text
Runbook-specific save endpoint
Runbook-specific database writer
raw SQL
filesystem side write
special BF4A revision store
```

### 4.3 Canonical Markdown paste is enough for BF4A

The existing semantic/canonical Markdown path is sufficient for the BF3B
prerequisite.

A GM may paste/edit canonical v2 material such as:

```markdown
<!-- dmb-playable-element:v2 kind=beat id=beat:hold-breach beat_kind=spine -->
## Hold the Breach

<!-- dmb-playable-element:v2 kind=scene id=scene:north-gate -->
### North Gate

<!-- dmb-playable-element:v2 kind=choice id=choice:brood [scene=scene:north-gate] -->
### What do they do with the surviving brood?

<!-- dmb-playable-element:v2 kind=option id=option:follow activates=scene:tunnel-pursuit -->
- Follow it

  The party pursues it into the lower tunnel.

<!-- dmb-playable-element:v2 kind=option id=option:seal suppresses=scene:tunnel-pursuit -->
- Seal the breach

  The immediate breach closes, but the brood remains below.

<!-- dmb-playable-element:v2 kind=scene id=scene:tunnel-pursuit -->
### Tunnel Pursuit
```

The exact example syntax must be validated against the current BF1 grammar
before using it in tests/dogfood. Do not weaken BF1 parsing merely to accept a
bad example in this handoff.

BF4A does **not** add buttons for creating those structures.

### 4.4 Commit means new immutable revision

Starting state:

```text
WorkObject W
current committed revision = 1
```

After edit + Save:

```text
WorkObject W          same identity
revision 1            still immutable/loadable
revision 2            new committed bytes
current committed revision = 2
```

Do not mint a replacement WorkObject.

Do not rewrite revision 1.

---

## §5 Existing Run isolation

This is a mandatory BF4A invariant, not deferred cleanup.

Suppose:

```text
Run R
  playable_artifact_id = W
  playable_revision = 1
  playable_content_sha256 = sha(revision 1)
```

Then the operator edits W and commits revision 2.

Required result:

```text
Run R remains:
  playable_artifact_id = W
  playable_revision = 1
  playable_content_sha256 = sha(revision 1)

Run R manifest unchanged
Run R progress unchanged
Run R current Beat/Scene unchanged
```

Opening R after the Save must continue to read exact historical revision 1.

A new explicit Start Run from W may bind revision 2.

BF4A must not call or simulate rebase.

### 5.1 Why this matters for dogfood

The intended BF3B material path is:

```text
Create blank Runbook revision 1
→ Edit + Save Decision-bearing revision 2
→ Start exact Run
→ new Run pins revision 2
```

But BF4A must also remain safe when the GM edits a Runbook that already has a
live historical Run.

---

## §6 Error / concurrency posture

BF4A inherits the existing workspace-document authoring state machine.

Do not invent a second conflict model.

Required behavior:

```text
load failure
→ truthful editor failure
→ no replacement WorkObject

prepare/commit conflict
→ existing authoring conflict handling
→ no silent overwrite

save failure
→ current committed revision remains authoritative
→ local draft/recovery behavior remains owned by shared authoring machinery

successful commit
→ success only for the exact loaded WorkObject
```

### 6.1 Navigation races

If the operator selects Runbook A and clicks Edit, the exact UUID for A is the
navigation authority.

A stale chooser refresh or list reorder must not navigate to another Runbook.

Do not key the transition to selected array index.

### 6.2 Campaign/context mismatch

The explicit document loader already allows a named WorkObject to resolve.
BF4A must not broaden cross-campaign authority accidentally.

If implementation discovers that opening the exact Runbook through Plan can
publish or bind a different campaign context than the Runbook's own
`campaign_id`, STOP and report the mismatch rather than silently normalizing it.

This handoff does not authorize a broad campaign-context redesign.

---

## §7 Write lease

### 7.1 Handoff

| Action | Path |
|---|---|
| Create | `Docs/Plans/HANDOFF-PLAY-SURFACE-runbook-authoring-gateway.md` |

### 7.2 Play chooser entry

| Action | Path | Purpose |
|---|---|---|
| Modify | `apps/live-control-ui/src/playSurface/StartRunPanel.tsx` | explicit Edit selected Runbook action |
| Modify | `apps/live-control-ui/src/playSurface/StartRunPanel.test.tsx` | selection/navigation/no-auto-start proof |
| Modify if needed | `apps/live-control-ui/src/playSurface/playSurface.css` | bounded chooser action layout only |

A tiny pure navigation helper may be added under:

```text
apps/live-control-ui/src/playSurface/
```

only if it materially improves exact-identity tests.

Do not add a routing framework.

### 7.3 Runbook save gate

| Action | Path | Purpose |
|---|---|---|
| Modify | `apps/live-control-ui/src/planSurface/components/PlanSurfaceCanvas.tsx` | kind-aware pathless Runbook save eligibility |

### 7.4 Authoring integration tests

Preferred lease:

| Action | Path |
|---|---|
| Create | `apps/live-control-ui/src/planSurface/PlanSurfaceRunbookAuthoring.test.tsx` |
| Modify if needed | `apps/live-control-ui/src/planSurface/PlanSurfaceShell.test.tsx` |

Use the smallest test surface that exercises the real `PlanSurfaceShell` /
`PlanSurfaceCanvas` + shared authoring path.

Do not mock away the save eligibility condition being changed.

### 7.5 App route proof

| Action | Path |
|---|---|
| Modify if required | `apps/live-control-ui/src/App.test.tsx` |

Only lease this if the Play→Plan route transition cannot be proven at the
owning components without it.

### 7.6 DF0 / sequencing state sync

The implementation PR carries the backward-looking predecessor update:

| Action | Path |
|---|---|
| Modify | `Docs/Plans/HANDOFF-PLAY-SURFACE-local-dogfood-bootstrap.md` |
| Modify | `Docs/Roadmaps/ROADMAP-con-ready.md` |
| Modify | `Docs/Sources/design-agent/ACTIVE_AUTHORITY/ROADMAP-con-ready.md` |
| Modify | `Docs/Plans/STEWARDS-ANCHOR-con-ready.md` |
| Modify | `Docs/Sources/design-agent/ACTIVE_AUTHORITY/STEWARDS-ANCHOR-con-ready.md` |

Do not mark BF4A DONE inside its own implementation PR before review/merge.

### 7.7 Explicitly unleased

Do not modify:

```text
BF1 grammar/parser/serializer
v2 manifest schema
Play Run schema
Play progress semantics
Play Run registry/backend routes
APP-STATE migrations
Content repository/service schemas
workspace-document backend APIs
TipTap prepare/commit backend APIs
Plan selector default kind=plan query
Agent Interaction
World Graph / CUTOVER
Combat
BF3B cockpit files
```

In particular, do not start:

```text
PlayCurrentMomentCockpit Decision UI
NativeRunbookOptionV2 BF3B edge projection
selection CAS work
```

inside BF4A.

---

## §8 State-authority sync required in implementation PR

### 8.1 DF0 completion

Append to:

```text
Docs/Plans/HANDOFF-PLAY-SURFACE-local-dogfood-bootstrap.md
```

approximately:

```text
## Completion

PR #657 merged.

Accepted implementation head:
  dc20fe8e63eec691265e75eb73c69f441ffd779d

Merge:
  87a769d05605ff021d28f0b69c5d7ab0b8205440

Formal review cycles:
  3

DF0 outcome:
  DONE

Real operator witness:
  zero startable Runbooks
  → Create blank Runbook
  → Start exact Run
  → Beat-only Current Moment
  → reload/resume

Successor sequencing discovery:
  BF3B remains the next table capability, but its real Decision-bearing
  dogfood material is not product-reachable yet.

Immediate predecessor:
  BF4A — native Runbook authoring gateway
```

Do not rewrite the original DF0 dispatch or review-amendment history.

### 8.2 Roadmap target state

```text
BF2
  DONE

BF3A
  DONE

DF0 / PR #657
  DONE
  accepted head dc20fe8e...
  merge 87a769d...
  review cycles 3

BF4A
  CURRENT — reopen/save native Runbook WorkObjects

BF3B
  BLOCKED ON BF4A — Decision interaction and visible relevance

BF4
  later — structure-aware Playable authoring controls

BF3C / BF3.x / P3
  later

P4
  later
```

### 8.3 CR-U11 / CR-U15 truth

Preferred update:

```text
CR-U11 — PARTIAL

Runbook WorkObjects / immutable WorkRevisions are durable. DF0 can create a
blank native Runbook. BF4A owns the missing ordinary reopen/edit/save path for
that native WorkObject. Structure-aware Beat/Scene/Decision authoring remains
BF4.

CR-U15 — PARTIAL

BF3A Current Moment and DF0 local Play entry are merged. BF3B remains the next
runtime capability but is blocked on BF4A because a Decision-bearing Runbook
must first be product-authorable. Retrieval, notes UX, and Combat remain
incomplete.
```

Canonical/mirror pairs must remain byte-identical.

---

## §9 Required evidence

### 9.1 Play chooser tests

Run:

```bash
pnpm --dir apps/live-control-ui exec vitest run \
  src/playSurface/StartRunPanel.test.tsx
```

Must prove:

1. no selection → Edit Runbook disabled/absent;
2. select existing Runbook → Edit Runbook targets exact document UUID;
3. create blank Runbook → committed object remains selected → Edit available;
4. Edit does not call `putPlayRun`;
5. Edit does not call manifest sealing;
6. Edit does not mutate selected Runbook identity;
7. list reorder/refresh cannot retarget the exact edit navigation;
8. Start exact Run behavior remains unchanged.

### 9.2 Runbook authoring integration

Use a real `kind=runbook` descriptor with:

```text
targetRelpath = null
contentStatus = committed
revision = 1
```

Exercise the existing editor/authoring pipeline.

Must prove:

1. explicit documentId resolves the exact Runbook WorkObject;
2. Runbook content loads into the normal editor;
3. the editor is interactive under the ordinary edit-unlocked state;
4. pathless Runbook Save is enabled;
5. Save uses existing prepare/commit calls;
6. committed response remains the same document UUID;
7. revision advances;
8. saved/reloaded Markdown equals the committed content;
9. Runbook kind remains Runbook;
10. no target path is fabricated;
11. a pathless `kind=plan` does **not** gain Save permission;
12. an ordinary path-backed Plan remains unchanged.

Preferred command:

```bash
pnpm --dir apps/live-control-ui exec vitest run \
  src/planSurface/PlanSurfaceRunbookAuthoring.test.tsx \
  src/planSurface/PlanSurfaceShell.test.tsx
```

Adjust only to exact test paths created/owned by the implementation.

### 9.3 Canonical v2 round-trip witness

The integration test must not merely change plain prose.

Starting from the DF0 one-Beat Runbook, paste/edit a small valid canonical v2
Decision-bearing document and prove:

```text
editor
→ Save
→ committed WorkRevision
→ reload exact Runbook
→ BF1 structure remains admitted
```

Use existing parser/indexer as the assertion boundary. Do not duplicate grammar
validation in BF4A test code.

This is specifically intended to establish real material for resumed BF3B.

### 9.4 Historical Run isolation regression

Prove the authority invariant:

```text
Run R pins W revision 1
→ edit/save W revision 2
→ R still resolves revision 1
→ new Start Run from W resolves revision 2
```

Prefer existing real-PostgreSQL APP-STATE/Play helpers rather than introducing
a new product API.

If an existing owning test already proves the first half, rerun and cite it;
add only the smallest missing integration needed to connect the BF4A edit to
that invariant.

No direct SQL should be used as the product-success witness.

### 9.5 App regression

If `App.test.tsx` is leased:

```bash
pnpm --dir apps/live-control-ui exec vitest run src/App.test.tsx
```

Prove:

```text
Play chooser
→ Edit selected Runbook
→ Plan authoring route names exact documentId
```

and existing Play/Plan routing remains green.

### 9.6 Frontend build

```bash
pnpm --dir apps/live-control-ui run build
git diff --check
```

### 9.7 Relevant backend regression

BF4A should not modify backend production code, but rerun the existing owning
Runbook revision / Play historical-binding tests that implementation identifies.

At minimum retain DF0's end-to-end path:

```bash
uv run pytest tests/test_blank_runbook_play_path.py -q
```

and the Play Runtime progress/binding suite relevant to historical pinning.

### 9.8 Mirrors

```bash
cmp Docs/Roadmaps/ROADMAP-con-ready.md \
    Docs/Sources/design-agent/ACTIVE_AUTHORITY/ROADMAP-con-ready.md

cmp Docs/Plans/STEWARDS-ANCHOR-con-ready.md \
    Docs/Sources/design-agent/ACTIVE_AUTHORITY/STEWARDS-ANCHOR-con-ready.md
```

---

## §10 Mandatory real operator dogfood witness

Automated authoring tests are not sufficient. BF4A exists because ordinary UI
reachability is the acceptance boundary.

### 10.1 Primary zero-to-Decision material path

Use the actual local product after normal DF0 bootstrap.

Required browser flow:

```text
1. Open Play chooser.
2. Create blank Runbook if no suitable disposable Runbook exists.
3. Confirm Blank Runbook is selected.
4. Click Edit Runbook.
5. Confirm ordinary editor opens the same titled Runbook.
6. Confirm no opaque UUID knowledge was required.
7. Unlock editing if the ordinary editor starts locked.
8. Replace/extend the starter with valid canonical v2 material containing:
     - one Beat
     - one Scene
     - one Decision
     - at least two Options
     - consequence prose
     - at least one activates/suppresses edge
9. Save.
10. Confirm Save succeeds although target_relpath is null.
11. Reload the editor URL.
12. Confirm exact saved content returns.
13. Navigate to Play through normal product navigation.
14. Select the same Runbook.
15. Start exact Run.
16. Confirm the Run binds the newly committed revision, not the old blank one.
17. Confirm native READY succeeds.
```

Do **not** implement BF3B controls merely to continue this witness.

The witness stops once the Decision-bearing Runbook reaches native READY.
BF3B owns interacting with it.

### 10.2 Existing-Run isolation witness

Also prove with a disposable Runbook/Run:

```text
1. Start Run R from revision N.
2. Record R's exact pinned revision/digest/current moment.
3. Return to chooser and Edit the same Runbook.
4. Save revision N+1.
5. Reopen existing Run R.
6. R still renders revision N.
7. Runtime current Beat/Scene is unchanged.
8. Start a separate new Run from the same Runbook.
9. New Run binds N+1.
```

This may be recorded as a browser + API-visible witness, but must use ordinary
product editing for the revision change.

### 10.3 Evidence hygiene

Record the witness on the implementation PR against the exact reviewed head.

Do not include:

```text
DSN passwords
full credentials
private source content not intended for the repository
```

---

## §11 Acceptance rubric

Merge only when all are true:

- [ ] Handoff is checked in before implementation.
- [ ] Implementation branch was re-anchored to exact current `main`.
- [ ] Active leases were rechecked.
- [ ] DF0 completion is recorded backward-looking.
- [ ] Roadmap/steward mirrors identify BF4A as current and BF3B as blocked on it.
- [ ] Play chooser exposes explicit Edit Runbook for exact selected WorkObject.
- [ ] A newly created blank Runbook can be edited before any Run is started.
- [ ] Operator does not need to know/copy an opaque document UUID.
- [ ] Edit does not create a Run.
- [ ] Edit does not create another Runbook WorkObject.
- [ ] Exact Runbook kind/title are truthfully represented in authoring UI.
- [ ] Existing default Plan selector remains `kind=plan` only.
- [ ] Pathless Runbook is saveable.
- [ ] Pathless Plan does not become saveable merely because BF4A exists.
- [ ] No filesystem path is fabricated for a native Runbook.
- [ ] Existing TipTap prepare/commit remains the save authority.
- [ ] Save produces a new immutable WorkRevision on the same WorkObject.
- [ ] Prior WorkRevision remains loadable.
- [ ] Existing Run pinned to prior revision remains unchanged.
- [ ] New explicit Run can bind the new revision.
- [ ] Canonical v2 Decision-bearing Markdown survives save/reload/indexing.
- [ ] No structure-aware insertion controls landed.
- [ ] No BF3B runtime Decision interaction landed.
- [ ] No auto-rebase landed.
- [ ] No auto-start landed.
- [ ] No backend/API/schema change landed.
- [ ] No Agent/CUTOVER/Combat scope landed.
- [ ] Real browser witness completes the zero-to-Decision-bearing Runbook path.
- [ ] Real witness proves old Run vs new revision isolation.
- [ ] Exact-head verification is recorded before review.
- [ ] Every changed path is inside §7 or an explicitly approved review amendment.

---

## §12 Stop conditions

Stop and report if implementation requires:

- changing WorkObject / WorkRevision schema;
- a new persistence table;
- a new Runbook save endpoint;
- changing TipTap prepare/commit backend semantics;
- changing BF1 grammar;
- changing manifest schema;
- assigning a fake filesystem path to pathless Runbooks;
- making all pathless Plans saveable as collateral behavior;
- automatic Run rebase after Save;
- automatic Start Run after Save;
- modifying Play Runtime state during editing;
- turning Plan selector into a mixed document browser;
- a new generic authoring surface/router;
- BF3B cockpit work;
- BF4 structure-aware insert controls;
- Agent / World / Combat changes;
- another active lane's production lease;
- a campaign-context mismatch where Plan would edit the Runbook under the wrong campaign authority.

Report:

```text
Stop condition:
Observed product path:
Owning invariant:
Why BF4A cannot absorb it:
Missing seam:
Evidence:
Proposed split/successor:
Authority update required:
```

Do not widen silently.

---

## §13 Named successor — resume BF3B

After BF4A merges, re-anchor the paused BF3B handoff onto current `main`.

Its real acceptance path becomes:

```text
Create blank Runbook
→ Edit Runbook
→ Save Decision-bearing revision
→ Start exact Run
→ BF3B Decision visible
→ select Option
→ consequence visible
→ relevance changes
→ change / clear
→ reload/resume
```

BF3B retains its own previously discovered evidence laws:

```text
v2 Options are list items
→ Choice prose and Option body must remain disjoint in projection

stale mutation may fail 422 before CAS
→ selection conflict handling must not misclassify same-generation 422 as a
  retryable 409
```

Those are BF3B implementation/review concerns, not work for BF4A.

The reason for BF4A is deliberately narrower:

> **Before we build a richer table interaction around authored material, the GM
> must be able to author that material through the product.**
