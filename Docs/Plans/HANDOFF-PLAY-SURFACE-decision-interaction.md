---
pr_body_template: |
  ## Handoff pointer
  - Conversation/workstream: PLAY-SURFACE / BF3B
  - Flow: PLAY-SURFACE
  - Direction: DESIGN → CODE → REVIEW
  - Handoff: `Docs/Plans/HANDOFF-PLAY-SURFACE-decision-interaction.md`
  - Branch / PR: `agent/play-surface-decision-interaction` / `PLAY-SURFACE: make authored Decisions table-usable`

  ## Verification pointer
  - Implementation base: `d4a91d7b727c0eae7dd0e09ba068e250b4819b44`
  - Approved visual target: `Docs/Design/assets/play-surface-gm-cockpit-target.webp`
  - Changed paths: HANDOFF §9
  - Verification: HANDOFF §11

  The checked-in handoff, cumulative diff, exact-head automated evidence,
  screenshots against the approved cockpit target, real browser Decision
  witness against the already-committed §6 Runbook, and independently rerun
  evidence are the review contract.
---

# HANDOFF — Authored Decision interaction dogfood (BF3B)

**Created:** 2026-08-29  
**Scope correction:** 2026-08-29  
**Visual-target correction:** 2026-08-29  
**Status:** CURRENT / IN FLIGHT  
**Canonical handoff:** `Docs/Plans/HANDOFF-PLAY-SURFACE-decision-interaction.md`  
**Workstream:** `PLAY-SURFACE / BF3B`  
**Owner:** `PLAY-SURFACE`  
**Suggested branch:** `agent/play-surface-decision-interaction`  
**PR title:** `PLAY-SURFACE: make authored Decisions table-usable`

> Rebased onto current `main` `d4a91d7b727c0eae7dd0e09ba068e250b4819b44`.
> Intervening CUTOVER work remains a separate lane and is not in the BF3B write
> lease. Do not absorb CUTOVER source merely because that commit is now the
> integration tip.

Parent authorities:

- `AGENTS.md`
- `Docs/Design/ARCHITECTURE-playable-material-and-runtime.md`
- `Docs/Design/DESIGN-play-current-moment-cockpit.md`
- `Docs/Design/DESIGN-play-surface-gm-cockpit-target.md`
- `Docs/Design/DESIGN-playable-authoring-and-adoption.md`
- `Docs/Roadmaps/ROADMAP-con-ready.md`
- `Docs/Plans/STEWARDS-ANCHOR-con-ready.md`

Accepted predecessors:

```text
BF2 / PR #652
  DONE — v2 Runtime admission
  accepted head: 9dffcab96ad3f527efedc3981aea805a63deb4df
  merge:         39ef105d3996ef0062dd45a089fecada14915436
  review cycles: 5

BF3A / PR #655
  DONE — Scene-centered Current Moment cockpit
  accepted head: 3d5925c8ad1bdbe934020e1c4cd7f2f3fafbbec7
  merge:         4d82f12ad9c6d679b5dbce83db527eb7dbd27957
  review cycles: 2

DF0 / PR #657
  DONE — local Play dogfood/bootstrap + explicit blank Runbook creation
  accepted head: dc20fe8e63eec691265e75eb73c69f441ffd779d
  merge:         87a769d05605ff021d28f0b69c5d7ab0b8205440
  review cycles: 3

PLAN-BLANK-SHELL / PR #661
  DONE — blank Plan authoring shell
  accepted head: ffa0b18d6212a6780d6be90f91a25626bf15b464
  merge:         770f79cca4aa3c12aa8a35db2db77ce376f2ff9e
  review cycles: 4

BF4A / PR #660
  DONE — native Runbook reopen/save
  accepted head: d9b34ca87166572af8b482523862722fdd928fbe
  merge:         a3fd6219062d1cd978c394d07e2f80aaa6d203eb
  review cycles: 2
```

---

## §0 Scope correction: Runbook creation is not BF3B

### 0.1 Product vocabulary is authoritative

```text
RUNBOOK
  durable Playable document / session script
  kind=runbook WorkObject
  immutable committed WorkRevisions
  campaign-bound authored intent

RUN
  runtime instance of play
  pins one exact committed Runbook WorkRevision
  owns current Beat/Scene, selections, notes, resolution state, etc.
```

A Runbook is **not** a Run.

### 0.2 What Create blank Runbook already means

The existing Play chooser action **Create blank Runbook** is predecessor
behavior. It commits the smallest legal durable Playable session script:

```text
kind        = runbook
title       = Blank Runbook
campaign    = explicit/validated campaign
content     = one empty spine Beat, Untitled Beat
status      = committed
```

It does **not** create a Run, start table play, make a Scene current, mutate
Runtime progress, or write Plan prep notes.

It exists because a Run must pin an exact committed Runbook revision and local
bootstrap is forbidden from inventing fake campaign material.

BF3B must not change, rename, explain, or otherwise absorb that chooser action.

### 0.3 The chooser-language problem is separate

There is a legitimate product-language problem on the chooser:

```text
page title: Choose a Run
empty-state action: Create blank Runbook
neighboring actions: Edit Runbook / Start exact Run
```

A new operator may not yet know:

```text
Runbook = script
Run     = one pinned runtime/performance of a script revision
```

That missing explanatory sentence belongs to the Play chooser and is captured
separately in `Backlog.md` as an IDEA. It is **not BF3B**.

### 0.4 BF3B begins later

BF3B begins only after:

```text
1. a Decision-bearing Runbook WorkRevision is committed;
2. an exact Run pins that revision;
3. the Run is READY;
4. current Beat/Scene are authoritative Runtime state.
```

Disposable witness setup may use already-merged DF0/BF4A behavior to produce
that state. Setup is not BF3B product scope or BF3B acceptance.

---

## §1 Visual target is part of the BF3B contract

The current implementation is not the visual authority.

The approved directional target is:

`Docs/Design/DESIGN-play-surface-gm-cockpit-target.md`

and its committed visual artifact:

`Docs/Design/assets/play-surface-gm-cockpit-target.webp`

![Approved Play Surface GM cockpit target](../Design/assets/play-surface-gm-cockpit-target.webp)

**Before editing production UI, open and inspect that image.** Do not infer the
product target from the current `PlayCurrentMomentCockpit` DOM/CSS alone.

The design authority says the image is stronger than a mood board and weaker
than a pixel-perfect wire contract. It is the hierarchy and interaction anchor.
The later 2026-08-26 interpretation lock overrides only misleading implications
that Beat Context and At a Glance must always remain expanded or that Combat
owns a permanent right-side rail.

### 1.1 Explicit correction to current implementation posture

The current BF3A UI is structurally useful but visually reads as three columns:

```text
[ Beat Context ] [ Scene/workspace ] [ At a Glance ]
```

That is **not** the accepted visual destination and must not become the BF3B
reference merely because it already exists.

Do not preserve three roughly equal vertical columns simply to minimize the
diff.

BF3B should move the actual Current Moment materially toward the approved
cockpit hierarchy while adding Decisions:

```text
supporting Beat context      DOMINANT CURRENT SCENE BOARD      compact launchers
       subordinate            table interaction focus           subordinate
```

The center should feel like the thing the GM is running. The side regions are
supporting context/chrome.

### 1.2 Scene is a board/work surface, not the middle column

When North Gate is current:

- the Scene owns the visual center and most available working width;
- Scene title/body establish immediate table orientation;
- the Decision appears **inside that Scene work surface** as a distinct action
  block, not as another generic rail/card column;
- Beat Context remains immediately accessible but visually subordinate;
- At a Glance remains a compact presence-first launcher region;
- collapsing either supporting region is presentation-only;
- collapsing both must materially widen the Scene work surface.

The implementation may change Current Moment layout proportions, spacing,
containers, and responsive CSS inside the BF3B lease to achieve this hierarchy.
That is not scope creep; visual hierarchy is part of this capability's product
acceptance.

### 1.3 Decision interaction must look table-usable

Use the target image as interaction/composition guidance, not generic browser
form defaults.

The Decision should read as one coherent block in the Scene:

```text
Decision prompt
short authored framing

[ Follow it ]       [ Seal the breach ]

selected consequence
what this makes more / less relevant
```

Exact card count, color, typography, and spacing are not frozen. But:

- Options must be visually tactile and fast to distinguish;
- selected state must be obvious at a glance;
- consequence must be visually attached to the selected Option/Decision;
- relevance changes must be legible without opening another screen;
- internal IDs are diagnostic, not primary presentation;
- unselected/default state must not look like a broken or disabled form;
- this should not resemble an admin radio-button form dropped into a text column.

### 1.4 What the target image does not authorize

Do **not** use BF3B to recreate every detail in the mockup.

Still out of scope:

- global AppChrome redesign;
- new Play navigation architecture;
- implementing every At-a-Glance category;
- permanent Combat rail;
- exact colors/icons/typography/pixel dimensions;
- mobile redesign;
- fictional content from the mockup as campaign truth.

Use the image to establish **hierarchy, density, workspace dominance, and
Decision interaction posture** for the slice we are actually implementing.

---

## §2 Mission and merge-ready invariant

### 2.1 Mission

> **Given an already-authored, already-committed v2 Runbook and a READY Run
> pinned to it, make authored Decisions operable inside a visually dominant,
> Scene-centered Current Moment. The GM can select/change/clear one authored
> Option, see its authored consequence, and see derived Beat/Scene relevance
> change without navigation.**

### 2.2 Merge-ready invariant

Given the exact §6 Runbook and a READY Run with:

```text
Current Beat  = beat:hold-breach
Current Scene = scene:north-gate
Decision      = choice:surviving-brood
Selection     = none
```

Play supports:

```text
Select option:follow-brood
→ exactly one existing progress CAS
→ current Beat/Scene unchanged
→ selected only after authoritative response
→ authored consequence visible
→ scene:tunnel-pursuit emphasized
→ beat:lower-tunnels emphasized

Change to option:seal-breach
→ exactly one existing progress CAS
→ current Beat/Scene unchanged
→ authored consequence changes
→ scene:tunnel-pursuit de-emphasized
→ beat:lower-tunnels returns default

Clear
→ exactly one existing progress CAS
→ only choice:surviving-brood removed from selections
→ current Beat/Scene unchanged
→ no selected consequence
→ affected relevance returns to derived default
```

Hard reload restores persisted selection and re-derives relevance from the
Run's exact sealed manifest + pinned Runbook. Relevance itself is never stored.

Visual merge-readiness additionally requires that North Gate reads as the
primary Scene board, not one of three equal columns, and the Decision interaction
visibly belongs to that board.

---

## §3 Atomic capability boundary

### KEEP — BF3B

- Project authored Decisions into the current Scene work surface.
- Render authored Option labels/body text.
- Explicit select/change/clear.
- Authoritative selected state from `run.progress.selections` only.
- Selected Option body text as consequence framing.
- Human-readable final derived relevance for affected Beat/Scene targets.
- Existing `putPlayRunProgress` CAS only.
- Preserve unrelated Runtime fields and unrelated Decision selections.
- Exact reread/reconcile after rejected/unknown writes.
- 409 conflict: reread, no automatic retry/merge.
- 422 semantic rejection: reread, no retry, not mislabeled as conflict.
- Reload/resume selection + derived relevance.
- De-emphasized material remains inspectable and Make Current-capable.
- Materially align Current Moment layout with the §1 approved visual hierarchy.
- Real browser screenshots/witness against the §1 visual target and §6 Runbook.

### OUT OF SCOPE / REJECT

- Create blank Runbook behavior or chooser copy.
- Runbook-vs-Run explanation on chooser — backlog IDEA.
- Plan prep-note behavior.
- Add Decision / Add Option authoring controls — later BF4 authoring.
- Runbook paste/replace or starter cleanup UX.
- Editing Runbook structure from Play.
- Freeform Option D creation.
- `currentDecisionId` or durable Decision focus.
- Automatic navigation after Option selection.
- Automatic Beat/Scene resolution.
- Persisted relevance.
- Condition/workflow DSL.
- New backend endpoint/schema/migration.
- Runbook grammar/parser changes.
- WorkObject/WorkRevision changes.
- Global AppChrome redesign.
- Combat, World Graph/CUTOVER, Agent/Hermes.

One independently useful capability:

> **Use an already-authored fork at the table, in the intended cockpit.**

---

## §4 Decision projection contract

Durable containment remains Beat-first:

```text
Beat
  → Scene
  → Decision / choice
      → Option
```

A Decision is Beat-owned and may optionally associate with one Scene.

Minimum projection rule:

```text
when a Scene is current:
  operable Decisions =
    current Beat unassociated choices
    + current Beat choices associated with current Scene

when Beat-only:
  operable Decisions = current Beat unassociated choices
```

Do not project a Decision associated with another Scene merely because it is in
the same Beat.

For §6:

```text
choice:surviving-brood scene=scene:north-gate
```

so it appears when North Gate is current.

No new full-screen Decision workspace, no Decision side rail, and no durable
`currentDecisionId`.

If multiple Decisions are operable, render them in authored order inside the
current Scene/Beat work surface.

---

## §5 Option, consequence, and relevance law

Authoritative selected Option:

```text
run.progress.selections[choice.id]
```

Rules:

- show every authored Option;
- selection is semantically unambiguous and keyboard reachable;
- selecting already-selected Option spends no CAS;
- Clear exists only/primarily when selected;
- no optimistic selected state;
- while saving, old authoritative selection remains truthful;
- controls may disable to prevent duplicate mutation.

Consequence for BF3B is the selected Option's authored `bodyText`.
Do not infer outcome from transition edges and do not claim that selection
proves what actually happened at the table.

Relevance remains existing derived projection:

```text
persisted selected Options
+ sealed activates/suppresses edges
→ emphasized / de-emphasized / default
```

Activation wins suppression. BF3B writes no relevance field.

For each target touched by the selected Option, show its human title and final
derived relevance, not merely raw edge wording.

For §6:

```text
Follow it
  Tunnel Pursuit → emphasized
  Lower Tunnels  → emphasized

Seal the breach
  Tunnel Pursuit → de-emphasized
  Lower Tunnels  → default
```

Suppression is relevance, not permission. `Tunnel Pursuit` remains visible,
inspectable, and Make Current-capable when de-emphasized.

---

## §6 Mandatory dogfood Runbook input

This exact Markdown is the BF3B input. It was already proven authorable and
Play-admissible by BF4A.

It is acceptance material, not production seed behavior.

```markdown
# Breach Dogfood Runbook

<!-- dmb-playable-element:v2 kind=beat id=beat:hold-breach beat_kind=spine -->
## Hold the Breach

Creatures have broken through the defensive wall. The party must decide
whether to pursue the surviving brood or stabilize the breach before the line
fails completely.

<!-- dmb-playable-element:v2 kind=scene id=scene:north-gate -->
### North Gate

The gate is damaged, the last creatures are retreating toward a broken tunnel,
and exhausted defenders are trying to stabilize the wall.

<!-- dmb-playable-element:v2 kind=choice id=choice:surviving-brood scene=scene:north-gate -->
### What do they do with the surviving brood?

The brood is disappearing underground while the defenders call for help at the
breach.

<!-- dmb-playable-element:v2 kind=option id=option:follow-brood activates=scene:tunnel-pursuit,beat:lower-tunnels -->
- Follow it

  The party pursues the retreating creatures into the lower tunnels before
  reinforcements arrive.

<!-- dmb-playable-element:v2 kind=option id=option:seal-breach suppresses=scene:tunnel-pursuit -->
- Seal the breach

  The immediate breach is contained, but the surviving creatures remain
  somewhere below.

<!-- dmb-playable-element:v2 kind=scene id=scene:tunnel-pursuit -->
### Tunnel Pursuit

The party enters a damaged tunnel after the fleeing creatures while loose stone
and timbers shift overhead.

<!-- dmb-playable-element:v2 kind=beat id=beat:lower-tunnels beat_kind=optional -->
## Lower Tunnels

Following the brood deeper turns the defense of the gate into a search below
the fortifications.
```

Expected semantic structure:

```text
beat:hold-breach [spine]
  scene:north-gate
  choice:surviving-brood [scene:north-gate]
    option:follow-brood
      activates scene:tunnel-pursuit
      activates beat:lower-tunnels
    option:seal-breach
      suppresses scene:tunnel-pursuit
  scene:tunnel-pursuit

beat:lower-tunnels [optional]
```

### 6.1 Witness preparation is not BF3B

Before the BF3B browser witness begins, prepare a disposable environment until:

```text
committed §6 Runbook exists
→ exact Run pins that revision
→ Run is READY
→ Hold the Breach is current
→ North Gate is current
→ no Decision selection exists
```

Already-merged DF0/BF4A behavior may be used to reach that state. Do not count
those setup interactions as BF3B acceptance and do not modify those product
paths.

If setup starts from a blank Runbook, manually remove the original starter Beat
before pasting the §6 bytes. The BF4A paste-residue finding is later authoring UX
debt, not BF3B scope.

Do not hardcode disposable WorkObject or Run UUIDs. Stable witness identities
are the semantic IDs above.

---

## §7 Runtime mutation law

Every select/change/clear uses the existing full-progress CAS already owned by
Current Moment:

```text
PUT Play Run progress
expected_run_revision = authoritative run.run_revision
progress = canonical full progress with only selections changed
```

Select/change:

```ts
selections = {
  ...run.progress.selections,
  [choiceId]: optionId,
}
```

Clear removes only `choiceId`.

Preserve exactly:

```text
current_beat_id
current_scene_id
resolved_beat_ids
notes_by_element_id
all other selections
```

The UI only offers Options belonging to the rendered Choice. Invalid
cross-Choice mutation fails closed/no-op client-side; backend remains final
authority.

No optimistic selected state. During a write, old authoritative selection stays
visibly authoritative. On success, use the returned Run and existing overlay to
re-derive relevance.

Failure posture:

```text
409
→ exact reread
→ conflict
→ no retry / merge / selection replay

422 semantic rejection
→ exact reread
→ visible rejection distinct from conflict
→ no retry / replay

unknown/network outcome
→ exact reread
→ truthful unknown state
→ no blind retry
```

Stale async completion after Run switch or unmount must not mutate visible
state.

---

## §8 Suggested implementation shape

Primary owner remains:

`apps/live-control-ui/src/playSurface/currentMoment/PlayCurrentMomentCockpit.tsx`

Reuse its existing `replaceProgress(next)` CAS boundary rather than creating a
second mutation stack.

A small pure helper is allowed if useful:

`apps/live-control-ui/src/playSurface/currentMoment/decisionInteractionModel.ts`

Possible pure responsibilities:

- operable Decisions for current Beat/Scene;
- selected Option lookup;
- cross-Choice validation;
- selected consequence projection;
- touched target IDs from sealed edges;
- map target IDs to human titles;
- final relevance lookup.

The helper owns no persistence or local Runtime truth.

### 8.1 Visual implementation guidance

`playSurface.css` is an expected owning file, not incidental polish.

The current three-column shell may be refactored inside Current Moment so long
as the architectural behaviors remain:

- one central workspace;
- Beat Context collapsible;
- At a Glance collapsible;
- category inspect does not mutate Runtime;
- Back resolves to authoritative current Scene;
- supporting rails are not new persistent workspace authorities.

Prefer CSS/layout composition that makes the center visibly dominant on normal
desktop widths and increasingly dominant when rails collapse.

Do not create a second Play-local global projection host or change AppChrome.

---

## §9 Write lease

Re-check actual current `main` and open PR/worktree leases before editing.

### 9.1 Primary production lease

```text
apps/live-control-ui/src/playSurface/currentMoment/PlayCurrentMomentCockpit.tsx
apps/live-control-ui/src/playSurface/currentMoment/PlayCurrentMomentCockpit.test.tsx
apps/live-control-ui/src/playSurface/playSurface.css
```

Authorized new sibling if useful:

```text
apps/live-control-ui/src/playSurface/currentMoment/decisionInteractionModel.ts
apps/live-control-ui/src/playSurface/currentMoment/decisionInteractionModel.test.ts
```

### 9.2 Bounded conditional lease

Only if exact evidence requires it:

```text
apps/live-control-ui/src/playSurface/currentMoment/currentMomentModel.ts
apps/live-control-ui/src/playSurface/currentMoment/currentMomentModel.test.ts
apps/live-control-ui/src/playSurface/runbook/nativeRunbookProjection.ts
apps/live-control-ui/src/playSurface/runbook/nativeRunbookProjection.test.ts
apps/live-control-ui/src/App.test.tsx
```

A tiny test-only §6 Markdown fixture may be added under existing Play Surface
test ownership to avoid semantic drift. It must not become production seed
behavior.

### 9.3 State-authority sync leased to implementation PR

```text
Docs/Plans/HANDOFF-PLAY-SURFACE-decision-interaction.md
Docs/Roadmaps/ROADMAP-con-ready.md
Docs/Sources/design-agent/ACTIVE_AUTHORITY/ROADMAP-con-ready.md
Docs/Plans/STEWARDS-ANCHOR-con-ready.md
Docs/Sources/design-agent/ACTIVE_AUTHORITY/STEWARDS-ANCHOR-con-ready.md
```

Record BF4A DONE and BF3B IN FLIGHT until merge. Re-anchor headers to the actual
implementation base. Keep canonical/mirror pairs byte-identical.

### 9.4 Explicitly unleased

Do not modify without STOP + operator/reviewer approval:

```text
backend Play progress schemas/routes/services
Alembic migrations
application-state schema
WorkObject / WorkRevision model
BF1 grammar / marker parser / serializer
Plan authoring / BF4A authoring paths
blank Runbook creation / chooser copy
Combat
World Graph / CUTOVER
AgentRuntime / Hermes
shared AppChrome host semantics
```

---

## §10 Automated evidence contract

### 10.1 Derived Decision model

If a helper is added, prove at minimum:

1. current Scene gets Beat-level + same-Scene associated Decisions;
2. other-Scene associated Decision is excluded;
3. Beat-only gets only unassociated Decisions;
4. selected Option comes from Runtime;
5. selected consequence is Option bodyText;
6. Follow touched targets resolve to human titles + final emphasized state;
7. Seal resolves Tunnel Pursuit de-emphasized and Lower Tunnels default;
8. final relevance, not raw edge wording, wins when multiple selections touch a target;
9. invalid cross-Choice Option fails closed.

### 10.2 Cockpit interaction

Using §6 semantic structure, prove:

1. North Gate current renders the surviving-brood Decision;
2. unselected renders both Options and no selected consequence;
3. Follow performs exactly one progress write;
4. outgoing progress preserves Beat/Scene/resolved/notes/unrelated selections;
5. no optimistic selected state before response;
6. authoritative Follow selection + consequence;
7. Tunnel Pursuit + Lower Tunnels emphasized;
8. change to Seal performs exactly one write;
9. Seal consequence appears;
10. Tunnel Pursuit de-emphasized and Lower Tunnels default;
11. Clear removes only this choice with exactly one write;
12. selection mutations never alter current Beat/Scene;
13. de-emphasized Tunnel Pursuit remains Inspect/Make Current-capable;
14. already-selected Option spends no CAS;
15. 409 rereads and does not retry;
16. 422 rereads, does not retry, and is not a 409 conflict;
17. unknown outcome rereads and does not blind retry;
18. stale async completion cannot mutate the next Run/unmounted view.

### 10.3 Visual/layout behavior

Automated layout tests should assert semantics/classes/state, not brittle pixel
snapshots. Prove where practical:

- Current Scene remains central workspace owner;
- Decision is rendered inside Current Scene/Beat work surface, not a rail;
- Beat Context and At a Glance collapse independently;
- collapse state does not mutate Runtime;
- both collapsed produces the CSS/layout state intended to reclaim center width;
- existing At-a-Glance Scenes inspect/back semantics remain green.

The **browser witness/screenshots**, not DOM pixel tests, own qualitative visual
comparison to the approved target image.

### 10.4 Regression / static

At minimum rerun:

```text
PlayCurrentMomentCockpit tests
nativeRunbookProjection tests
v2RuntimeProjection tests
relevant App v2 Current Moment tests
uv run pytest tests/test_play_run_progress.py -q
frontend build/typecheck
git diff --check
canonical/mirror cmp
```

No backend/schema/grammar diff. No relevance persistence. No
`currentDecisionId`. No automatic navigation after selection.

---

## §11 Mandatory real browser dogfood + visual witness

Fixture-only evidence is insufficient.

Run exact implementation head against disposable APP-STATE PostgreSQL.

### 11.1 Pre-witness setup

Prepare the environment until this state exists:

```text
committed §6 Runbook
READY exact Run
Current Beat  Hold the Breach
Current Scene North Gate
no selected Option
```

Then begin BF3B evidence.

### Witness A — unselected Current Scene

Verify:

- North Gate is visually the dominant central work surface;
- Beat Context is subordinate and accessible;
- At a Glance is compact/supporting;
- surviving-brood Decision is visibly part of North Gate;
- Decision prompt/framing and both Options are immediately legible;
- no Option is falsely selected;
- the page does **not** read as three equal content columns.

Capture a screenshot of the complete Play cockpit at a representative desktop
width and compare it against:

`Docs/Design/assets/play-surface-gm-cockpit-target.webp`

The PR/review packet should state the important hierarchy similarities and any
intentional differences justified by the design interpretation lock.

### Witness B — Follow it

Select **Follow it** and verify:

- North Gate remains current;
- selected state is visually obvious;
- authored Follow consequence is immediately attached to the Decision;
- Tunnel Pursuit — emphasized;
- Lower Tunnels — emphasized;
- no navigation occurs;
- hard reload restores selection/consequence/relevance and North Gate.

Capture the Decision/Scene state in a screenshot.

### Witness C — Seal the breach

Select **Seal the breach** and verify:

- one selected Option;
- North Gate remains current;
- Seal consequence is immediately legible;
- Tunnel Pursuit — de-emphasized;
- Lower Tunnels — default;
- At a Glance → Scenes still contains Tunnel Pursuit;
- Inspect does not change current Scene;
- Make Current remains available;
- Back returns to North Gate.

Capture the Decision/Scene state in a screenshot.

### Witness D — Clear

Clear selection and verify:

- no Option selected;
- no selected consequence claimed;
- affected relevance returns default;
- hard reload remains cleared;
- North Gate remains current.

### Witness E — collapse hierarchy

From North Gate:

1. collapse Beat Context;
2. collapse At a Glance;
3. verify the central Scene materially expands/reclaims width;
4. verify Decision remains usable and readable;
5. verify neither action changes Runtime Beat/Scene/selection.

Capture one screenshot with supporting regions collapsed. This is evidence that
those regions are chrome around one central workspace rather than three equal
workspace columns.

---

## §12 Adversarial evidence

At least automated evidence must cover:

```text
invalid Option for Choice
→ reject/no progress mutation
→ no retry
→ authoritative reread when backend rejects
→ no conflict mislabel

stale run_revision
→ 409
→ exact reread
→ no selection replay
```

Ordinary browser UI should never expose an invalid cross-Choice combination, so
manual forging is not required.

---

## §13 Stop conditions

STOP and report before widening if implementation appears to require:

- new backend endpoint/progress field/migration;
- Choice/Option membership or v2 grammar changes;
- persisted relevance;
- `currentDecisionId`;
- automatic navigation/resolution;
- Runbook creation/chooser copy changes;
- Plan authoring/paste behavior changes;
- shared AppChrome host redesign;
- Combat or World Graph changes;
- generalized condition/workflow engine;
- hiding/removing de-emphasized material from explicit navigation.

**Do not STOP merely because the existing three-column CSS must change.**
Current Moment layout/CSS within the leased Play Surface files is intentionally
available to move BF3B toward the approved visual target.

---

## §14 Review narrative

The PR should tell one product story:

```text
The script already exists.
The Run already pins it.
North Gate is the obvious table workspace.

The GM sees the authored fork inside that Scene.
Follow it / Seal the breach / Clear mutate only Runtime selection.
Consequence and future relevance are visible immediately.
Nothing navigates automatically.
Reload returns the same truth.

And the Play surface now reads materially more like the approved GM cockpit,
not three generic columns.
```

Formal review is against one exact head SHA at a time. Count each distinct-head
review judgment as one review cycle.

Do not claim the broader Play Surface is complete. Additional At-a-Glance
categories, global retrieval, notes refinement, Threat→Combat, Combat durability,
and real-session dogfood remain subsequent capabilities.
