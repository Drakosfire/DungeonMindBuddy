---
pr_body_template: |
  ## Handoff pointer
  - Conversation/workstream: PLAY-SURFACE / BF3B recut
  - Flow: PLAY-SURFACE
  - Direction: DESIGN → CODE → REVIEW
  - Handoff: `Docs/Plans/HANDOFF-PLAY-SURFACE-decision-interaction.md`
  - Branch / PR: `agent/play-surface-decision-cockpit-recut` / `PLAY-SURFACE: make Scene Decisions table-usable`

  ## Recut reason
  - Closed exploratory PR #670 at `f2e4fe60b7753ca3f2c6a3702b2f249ab1bfa84f`
  - #670 is design/dogfood evidence only; no formal review cycle and no merge
  - Start implementation from current `main`, not the #670 branch

  ## Verification pointer
  - Design base: `c71e4e18905a8a482e7cba3be9b80f0e12cf999c`
  - Approved visual target: `Docs/Design/assets/play-surface-gm-cockpit-target.webp`
  - Changed paths: HANDOFF §9
  - Verification: HANDOFF §§10–12

  The checked-in handoff, cumulative diff, exact-head automated evidence,
  exact-head browser Decision witness, and screenshots against the approved
  cockpit target are the review contract.
---

# HANDOFF — Scene-owned Decision interaction dogfood (BF3B recut)

**Created / recut:** 2026-08-30  
**Status:** READY FOR DISPATCH  
**Canonical handoff:** `Docs/Plans/HANDOFF-PLAY-SURFACE-decision-interaction.md`  
**Workstream:** `PLAY-SURFACE / BF3B`  
**Owner:** `PLAY-SURFACE`  
**Branch:** `agent/play-surface-decision-cockpit-recut`  
**PR title:** `PLAY-SURFACE: make Scene Decisions table-usable`  
**Design base:** `main` `c71e4e18905a8a482e7cba3be9b80f0e12cf999c`

> Re-fetch current `main` before implementation. Rebase if it has advanced.
> The branch was deliberately cut from `main`, not from closed PR #670.

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

Exploratory predecessor:

```text
PR #670 — PLAY-SURFACE: make authored Decisions table-usable
  CLOSED UNMERGED
  prototype head: f2e4fe60b7753ca3f2c6a3702b2f249ab1bfa84f
  formal review cycles: 0
  disposition: design/dogfood evidence only
```

Do not cherry-pick #670 wholesale. It deliberately tested a more aggressive
navigation/chrome composition and exposed product-boundary problems. Reuse an
idea or small algorithm only after proving it still satisfies this handoff and
current `main`.

---

## §0 Product vocabulary and BF3B starting point

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

A Runbook is not a Run.

`Create blank Runbook` is predecessor behavior. It commits the smallest legal
session script; it does not create a Run or start play. The chooser-language
problem is already captured separately in `Backlog.md` and is not BF3B.

BF3B begins only after:

```text
1. a Decision-bearing Runbook WorkRevision is committed;
2. an exact Run pins that revision;
3. the Run is READY;
4. current Beat/Scene are authoritative Runtime state.
```

Disposable browser setup may use DF0/BF4A to reach that state. Setup is not
BF3B product scope.

---

## §1 Why PR #670 was closed instead of repaired

#670 produced useful evidence but crossed frozen product boundaries while
trying to solve the visual problem.

### 1.1 Findings to KEEP

The replacement implementation should preserve these findings:

1. **The current Scene must be the obvious board.** The three-column BF3A
   composition was too egalitarian.
2. **A Decision belongs inside the current Scene work surface.** It is not a
   side rail or separate full-screen mode.
3. **Decision Runtime behavior was directionally correct:** explicit
   select/change/clear; one existing full-progress CAS; no optimistic selected
   truth; exact reread on failure; stale-completion protection.
4. **Authored Option body text is the consequence framing.** Selection does not
   claim what actually happened at the table.
5. **Suppression changes relevance, not navigation permission.**

### 1.2 Findings to FIX

#670 exposed two correctness gaps:

1. After changing `Follow it` → `Seal the breach`, `Lower Tunnels` disappeared
   from consequence/relevance presentation. The contract requires the Decision
   to make the reversion visible:

   ```text
   Tunnel Pursuit → de-emphasized
   Lower Tunnels  → default
   ```

2. A 422 path could claim `Reloaded the exact Run` and unlock mutations even if
   the exact reread itself failed. A semantic rejection is only reconciled when
   the reread succeeds.

### 1.3 Findings to BACK OUT / REDESIGN

Do not carry these #670 experiments into BF3B:

- deleting At a Glance;
- replacing At a Glance Scenes with a Beat/Scene chrome navigator;
- ordinary Beat click = Runtime `Make Current`;
- mixing `Start New Run` with Runbook location controls;
- generalized Play navigation architecture;
- the unused reference-chip projection experiment.

The prototype proved that these jobs are different:

```text
SESSION LIFECYCLE
  Start / resume / choose Run

RUNTIME ORIENTATION
  what Beat + Scene are actually current

CONTEXTUAL MATERIAL
  what Scenes / NPCs / Threats / Locations / Tables / Notes / Combat
  are useful around this moment
```

Do not collapse them into one instrument merely because they all contain names.

### 1.4 The strongest UX finding

The #670 pause note is accepted as product evidence:

> A Scene containing a branching Decision can visually read as if there is no
> Scene at all.

The repair is **not** to make the Decision tiny. The owning Scene needs stronger
visual identity and framing so the operator reads:

```text
I am running NORTH GATE
and this Scene contains a meaningful Decision
```

rather than:

```text
I am on a Decision screen
```

---

## §2 Visual target and composition contract

The approved directional target remains:

`Docs/Design/DESIGN-play-surface-gm-cockpit-target.md`

with visual artifact:

`Docs/Design/assets/play-surface-gm-cockpit-target.webp`

![Approved Play Surface GM cockpit target](../Design/assets/play-surface-gm-cockpit-target.webp)

Open and inspect that image before changing production UI.

The image is a hierarchy/interaction anchor, not a pixel-perfect wire contract.
The 2026-08-26 interpretation lock remains authoritative:

- Beat Context need not remain permanently expanded;
- At a Glance need not remain permanently expanded;
- Combat is not a permanent right rail;
- one central workspace remains the table instrument.

### 2.1 Required hierarchy

At representative desktop widths the surface must read approximately as:

```text
SESSION / SURFACE CHROME
  existing lifecycle affordances remain distinct from Playable location

Beat context / orientation
  compact, subordinate, collapsible

┌──────────────────────────────────────────────────────────┐
│ NORTH GATE                                  CURRENT SCENE │
│                                                          │
│ Immediate Scene framing / table situation                │
│                                                          │
│ Decision                                                 │
│ What do they do with the surviving brood?                │
│                                                          │
│ [ Follow it ]                    [ Seal the breach ]      │
│                                                          │
│ selected consequence / authored branch relevance         │
└──────────────────────────────────────────────────────────┘

At a Glance
  compact/presence-first contextual launchers
```

Exact vertical/horizontal placement is not frozen. The semantic hierarchy is.

### 2.2 Scene identity must survive Decision density

When a current Scene exists:

- Scene title is the strongest local workspace identity;
- the UI communicates that it is the **current Scene** without noisy repeated
  diagnostic labels;
- Scene body/framing remains visibly associated with the Scene;
- the Decision appears after/within that framing as owned content;
- Decision chrome must not visually replace the Scene frame;
- collapsing supporting regions materially benefits the Scene workspace.

### 2.3 Beat Context remains supporting chrome

Beat Context remains:

- immediately accessible;
- collapsible;
- presentation-only when collapsed;
- not an equal peer workspace;
- not a new durable state field.

A compact bar, narrow supporting region, or equivalent composition is allowed.
Do not turn every Beat into a primary navigation button as part of BF3B.

### 2.4 At a Glance remains a product concept

Do not delete or replace At a Glance.

For BF3B the only mature category may still be Scenes. That is enough.
At a Glance remains the future-compatible presence-first launcher for:

```text
Scenes
Locations
NPCs / characters
Threats
Roll tables
Notes
Combat
```

BF3B only needs to preserve existing Scenes behavior and visual hierarchy.
It must not implement the other categories.

At-a-Glance Scenes law remains:

```text
open Scenes
→ central workspace temporarily shows Scene inventory
→ no Runtime current mutation

inspect Scene
→ central workspace shows inspected Scene
→ current Beat/Scene remain unchanged

Make Current
→ explicit separate action
→ one Runtime CAS

Back / close
→ authoritative current Scene, not stale UI history
```

At a Glance itself remains collapsible/presentation-only.

### 2.5 Ordinary click is never hidden Make Current

The current cockpit authority remains explicit:

```text
OPEN / INSPECT
  read/projection only
  no currentBeatId/currentSceneId mutation

MAKE CURRENT
  explicit Runtime mutation
```

Do not introduce a Beat or Scene affordance whose ordinary click silently
changes Runtime position.

BF3B does not need new cross-Beat navigation to make Decision interaction
useful. If such navigation appears necessary, STOP and design it separately.

### 2.6 Session lifecycle stays separate

Do not relocate `Start New Run` into the same control group as Beat/Scene names.
Preserve current-main lifecycle semantics unless an unrelated current-main
integration change requires a mechanical adaptation.

---

## §3 Mission and merge-ready invariant

### 3.1 Mission

> Given an already-authored, already-committed v2 Runbook and a READY Run pinned
> to it, make authored Decisions operable **inside an unmistakably Scene-owned
> Current Moment**. The GM can select/change/clear one authored Option, see its
> authored consequence and the full Decision branch relevance state, while the
> current Beat/Scene remain unchanged.

### 3.2 Merge-ready invariant

Given the exact §7 Runbook and READY Runtime:

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
→ selected only after authoritative server response
→ Follow consequence visible
→ Tunnel Pursuit emphasized
→ Lower Tunnels emphasized

Change to option:seal-breach
→ exactly one existing progress CAS
→ current Beat/Scene unchanged
→ Seal consequence visible
→ Tunnel Pursuit de-emphasized
→ Lower Tunnels default and still shown as part of this Decision's branch state

Clear
→ exactly one existing progress CAS
→ only choice:surviving-brood removed from selections
→ current Beat/Scene unchanged
→ no selected consequence
→ no Decision branch-state block is claimed as selected outcome
```

Hard reload restores persisted selection and re-derives all relevance from the
Run's exact sealed manifest + pinned Runbook. Relevance itself is never stored.

Visual merge-readiness additionally requires:

```text
North Gate reads first as the current Scene
Decision reads as owned content within North Gate
Beat Context and At a Glance remain supporting chrome
surface does not read as three equal workspace columns
```

---

## §4 Atomic capability boundary

### KEEP — BF3B recut

- project authored Decisions into current Scene/Beat work surface;
- authored Option labels and body text;
- explicit select Option;
- explicit change selected Option;
- explicit Clear;
- authoritative selected state from `run.progress.selections` only;
- selected Option body text as consequence framing;
- full Decision branch target relevance presentation after selection;
- existing `putPlayRunProgress` full-progress CAS only;
- preserve Beat/Scene/resolved/notes/unrelated selections;
- no optimistic selected state;
- 409 exact reread + conflict, no retry;
- 422 exact reread + semantic rejection only when reread succeeds;
- reread failure → truthful unknown/locked posture;
- unknown write outcome → exact reread, no blind retry;
- stale async completion protection;
- reload/resume selection + derived relevance;
- de-emphasized Scene remains Inspect and Make Current capable;
- materially strengthen Scene-board visual ownership;
- preserve collapsible Beat Context;
- preserve collapsible At a Glance and existing Scenes inspect/back semantics;
- exact-head browser screenshots against approved target.

### OUT OF SCOPE / REJECT

- blank Runbook creation or chooser copy;
- Runbook-vs-Run explanatory UX;
- Plan prep notes;
- Decision/Option authoring controls;
- paste/replace behavior;
- freeform Option D authoring;
- `currentDecisionId`;
- automatic navigation after selection;
- automatic Beat/Scene resolution;
- persisted relevance;
- new backend endpoint/schema/migration;
- grammar/parser changes;
- WorkObject/WorkRevision changes;
- new Beat/Scene global navigator;
- deleting/replacing At a Glance;
- moving Start New Run into location/navigation chrome;
- implementing new At-a-Glance categories;
- global AppChrome redesign;
- Combat implementation;
- World Graph/CUTOVER changes;
- Agent/Hermes changes;
- generalized workflow/condition DSL;
- reference-chip UI generalized from #670 unless separately justified.

One independently useful capability:

> **Use an authored fork while unmistakably remaining in the current Scene.**

---

## §5 Decision projection contract

Durable containment stays Beat-first:

```text
Beat
  → Scene
  → Decision / choice
      → Option
```

A Decision is Beat-owned and may optionally associate with one Scene.

Projection:

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

There is no durable `currentDecisionId`.
If multiple Decisions are operable, preserve authored order inside the current
work surface.

---

## §6 Option, consequence, and Decision branch relevance

### 6.1 Authoritative selected Option

```text
run.progress.selections[choice.id]
```

Rules:

- render all authored Options;
- selection is accessible and visually unambiguous;
- clicking the already-selected Option spends no CAS;
- Clear is available when a selection exists;
- no optimistic selected state;
- while saving, prior authoritative selection remains truthful;
- controls may temporarily disable to prevent duplicate mutation.

### 6.2 Consequence

Selected consequence is exactly the selected Option's authored `bodyText`.

Do not infer actual table outcome from transition edges. Runtime selection is an
authored choice record, not proof of what happened in fiction.

### 6.3 Relevance remains derived

```text
persisted selected Options
+ sealed activates/suppresses edges
→ final emphasized / de-emphasized / default relevance
```

Activation wins suppression. BF3B persists no relevance field.

### 6.4 Correct Decision target-set projection

#670 exposed that looking only at edges from the **currently selected Option**
is insufficient because it hides targets that just returned to default.

For consequence/relevance presentation, derive the stable target set from the
entire authored Decision:

```text
choiceTargetIds(choice) =
  distinct target IDs referenced by edges from ANY authored Option in choice
```

Then, after a selected Option is authoritative:

```text
for each choiceTargetId in stable authored order:
  title     = authored Beat/Scene human title
  relevance = deck.relevanceByTargetId[targetId] ?? default
```

The selected Option determines consequence text; the whole Decision determines
which branch targets are useful to show.

For §7:

```text
Follow it
  Tunnel Pursuit → emphasized
  Lower Tunnels  → emphasized

Seal the breach
  Tunnel Pursuit → de-emphasized
  Lower Tunnels  → default
```

This is intentionally **final derived relevance**, not a restatement of raw
edges. Other selections may cause activation to win suppression.

When no Option is selected, do not imply a consequence has happened. The UI may
omit the branch-state block entirely or present neutral authored possibilities,
but must not claim selected relevance causality.

---

## §7 Mandatory dogfood Runbook input

Use this exact Markdown for BF3B acceptance. It was already proven authorable
and Play-admissible through BF4A.

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

Semantic structure:

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

### 7.1 Witness preparation is predecessor behavior

Before BF3B browser evidence begins, prepare a disposable environment until:

```text
committed §7 Runbook exists
→ exact Run pins that revision
→ Run READY
→ Hold the Breach current
→ North Gate current
→ no surviving-brood selection
```

DF0/BF4A may be used to create/edit/save the Runbook. Do not count that setup
as BF3B evidence or modify those paths.

If starting from Blank Runbook, remove the starter Beat before pasting. The
known paste-residue issue remains separate authoring UX debt.

---

## §8 Runtime mutation and failure law

Every select/change/clear uses the existing full-progress CAS:

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

Preserve:

```text
current_beat_id
current_scene_id
resolved_beat_ids
notes_by_element_id
all unrelated selections
```

### 8.1 Success

```text
server returns authoritative Run
→ overlay exact Run
→ selected state becomes visible
→ re-derive relevance
→ remain on exact current Beat/Scene
```

### 8.2 409 conflict

```text
write returns 409
→ exact get Run
→ if reread succeeds, publish authoritative Run + conflict posture
→ no automatic retry / merge / selection replay
→ if reread fails, unknown/locked posture
```

### 8.3 422 semantic rejection

```text
write returns 422
→ exact get Run
→ if reread succeeds:
     publish authoritative Run
     show semantic rejection distinct from conflict
     mutation controls may return to safe idle state
     message may truthfully say exact Run was reloaded
→ if reread fails:
     DO NOT claim reload
     DO NOT unlock as reconciled
     unknown/locked posture
→ no retry / selection replay
```

### 8.4 Unknown/network outcome

```text
unknown write result
→ exact reread attempt
→ publish reread if available
→ remain truthful that write outcome is unknown
→ no blind retry
```

Stale completion after Run switch or unmount must not mutate the next Run/view.

---

## §9 Write lease

Re-check current main and open worktree/PR leases before coding.

### 9.1 Primary production lease

```text
apps/live-control-ui/src/playSurface/currentMoment/PlayCurrentMomentCockpit.tsx
apps/live-control-ui/src/playSurface/currentMoment/PlayCurrentMomentCockpit.test.tsx
apps/live-control-ui/src/playSurface/playSurface.css
```

Authorized small sibling helpers:

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

A test-only §7 dogfood fixture is allowed under Current Moment test ownership.
It must never become automatic production seed behavior.

### 9.3 State-authority sync leased to implementation PR

```text
Docs/Plans/HANDOFF-PLAY-SURFACE-decision-interaction.md
Docs/Roadmaps/ROADMAP-con-ready.md
Docs/Sources/design-agent/ACTIVE_AUTHORITY/ROADMAP-con-ready.md
Docs/Plans/STEWARDS-ANCHOR-con-ready.md
Docs/Sources/design-agent/ACTIVE_AUTHORITY/STEWARDS-ANCHOR-con-ready.md
```

Record #670 as CLOSED / UNMERGED exploratory evidence with 0 review cycles.
Record BF3B recut as IN FLIGHT until accepted merge. Keep mirrors byte-identical.

### 9.4 Explicitly unleased

Do not modify without STOP + operator/reviewer approval:

```text
PlaySurfacePage / lifecycle behavior except mechanical current-main adaptation
new PlayRunNavigator or equivalent navigation architecture
SurfaceContext/AppChrome host semantics
backend Play progress schemas/routes/services
Alembic/application-state schema
WorkObject / WorkRevision model
BF1 grammar / marker parser / serializer
Plan/BF4A authoring paths
blank Runbook creation / chooser copy
Combat
World Graph / CUTOVER
AgentRuntime / Hermes
```

`nativeRunbookProjection.ts` is conditional only. The #670 reference-label fix
is not automatically part of BF3B. If actual §7 or real dogfood material loses
meaningful reference labels on current main, STOP/report and justify the bounded
projection fix rather than also introducing reference-chip UI.

---

## §10 Automated evidence contract

### 10.1 Decision model

Prove:

1. current Scene receives Beat-level + same-Scene associated Decisions;
2. other-Scene associated Decision is excluded;
3. Beat-only receives only unassociated Decisions;
4. selected Option comes from Runtime selections;
5. consequence is selected Option bodyText;
6. invalid cross-Choice Option fails closed;
7. select/change/clear preserve unrelated selections;
8. selected Option clicked again is no-op;
9. Decision target set is union of targets across all authored Options;
10. Follow yields Tunnel Pursuit emphasized + Lower Tunnels emphasized;
11. Seal yields Tunnel Pursuit de-emphasized + **Lower Tunnels default**;
12. final derived relevance wins over raw edge wording/activation wins suppression.

### 10.2 Cockpit interaction

Using §7:

1. North Gate current visibly owns the Decision;
2. unselected renders both Options and no false consequence;
3. Follow spends exactly one CAS;
4. outgoing progress preserves Beat/Scene/resolved/notes/unrelated selections;
5. no optimistic selected state;
6. authoritative Follow shows consequence + both emphasized rows;
7. change to Seal spends exactly one CAS;
8. authoritative Seal shows consequence + Tunnel Pursuit de-emphasized + Lower Tunnels default;
9. Clear removes only this Decision selection with one CAS;
10. selection mutations never alter current Beat/Scene;
11. de-emphasized Tunnel Pursuit remains available through existing At-a-Glance Scenes inspect path;
12. Inspect does not mutate current context;
13. explicit Make Current still works separately;
14. Back returns to authoritative current Scene;
15. Beat Context collapse writes no Runtime;
16. At a Glance collapse writes no Runtime;
17. both supporting regions collapsed leave Decision usable and Scene visually dominant.

### 10.3 Failure handling

Prove separately:

```text
409 + reread success
  → authoritative reread + conflict, no retry

409 + reread failure
  → unknown/locked, no false reconciliation

422 + reread success
  → authoritative reread + semantic rejection, no retry, not conflict

422 + reread failure
  → unknown/locked, no "reloaded exact Run" claim

unknown outcome
  → reread attempt, no blind retry

Run identity changes while write in flight
  → stale completion ignored
```

### 10.4 Regression/static

At minimum rerun relevant current-main equivalents of:

```text
PlayCurrentMomentCockpit tests
decisionInteractionModel tests
nativeRunbookProjection tests if touched
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

## §11 Mandatory exact-head browser dogfood + visual witness

Fixture-only evidence is insufficient.

Run the exact implementation head against disposable APP-STATE PostgreSQL.
Prepare §7 predecessor state first, then begin BF3B evidence.

### Witness A — Scene ownership before selection

Starting state:

```text
Current Beat  Hold the Breach
Current Scene North Gate
Selection     none
```

Verify and capture screenshot:

- North Gate is clearly the current Scene and dominant workspace identity;
- Scene framing remains visible and visually owns the Decision;
- Beat Context is subordinate and accessible;
- At a Glance is present as compact supporting chrome;
- Decision prompt/framing and both Options are immediately legible;
- no Option falsely selected;
- page does not read as three equal columns;
- page does not read as a standalone Decision screen.

Compare against:

`Docs/Design/assets/play-surface-gm-cockpit-target.webp`

Record intentional differences justified by the interpretation lock.

### Witness B — Follow it

Select **Follow it**.

Verify:

- one progress mutation;
- North Gate remains current;
- selected state obvious only after authoritative response;
- authored consequence attached to Decision;
- Tunnel Pursuit — emphasized;
- Lower Tunnels — emphasized;
- no automatic navigation;
- hard reload restores selection/consequence/relevance and North Gate.

Capture screenshot.

### Witness C — change to Seal the breach

Select **Seal the breach**.

Verify:

- exactly one new progress mutation;
- North Gate remains current;
- Seal is the only selected Option;
- Seal consequence visible;
- Tunnel Pursuit — de-emphasized;
- **Lower Tunnels — default remains visibly represented**;
- At a Glance → Scenes still exposes Tunnel Pursuit;
- Inspect Tunnel Pursuit does not change current Scene;
- explicit Make Current remains available;
- Back returns to North Gate.

Capture screenshot.

### Witness D — Clear

Clear the Decision.

Verify:

- only this selection removed;
- no selected consequence claimed;
- no selected branch-state causality claimed;
- North Gate remains current;
- hard reload remains cleared.

### Witness E — supporting chrome collapse

From North Gate:

1. collapse Beat Context;
2. collapse At a Glance;
3. verify Scene materially reclaims/dominates available workspace;
4. Decision stays readable/usable;
5. neither action changes Beat/Scene/selections;
6. restore both supporting regions without Runtime mutation.

Capture screenshot with both collapsed.

### Witness F — 422 truthful reconciliation

Automated evidence is mandatory; browser forging is optional. If a real browser
path can safely induce a semantic rejection, confirm UI wording does not claim
an exact reload when reread fails. Do not build a production debug affordance
for this witness.

---

## §12 Visual review questions

The reviewer should answer these explicitly from screenshots, not only tests:

1. **What does my eye identify first: North Gate or the Decision?**
   Required answer: North Gate/current Scene.
2. **Does the Decision feel like playable content inside the Scene?**
   Required answer: yes.
3. **Do Beat Context and At a Glance support the board rather than compete with it?**
   Required answer: yes.
4. **Can I still tell that At a Glance is the contextual-launcher concept that can later hold NPCs/Threats/Combat?**
   Required answer: yes; do not optimize it into a Scenes-only navigation bar.
5. **Is Make Current explicit?**
   Required answer: yes; ordinary inspect/open actions do not silently mutate Runtime.
6. **Does Seal visibly explain that Lower Tunnels returned to default?**
   Required answer: yes.

If these are not true, keep the PR draft and treat the screenshots as design
evidence rather than polishing around the failure.

---

## §13 Stop conditions

STOP and report before widening if implementation appears to require:

- new backend endpoint/progress field/migration;
- Choice/Option membership or v2 grammar changes;
- persisted relevance;
- `currentDecisionId`;
- automatic navigation/resolution;
- Runbook creation/chooser changes;
- Plan authoring/paste changes;
- new Beat/Scene global navigation architecture;
- deleting/replacing At a Glance;
- moving session lifecycle into Runbook location controls;
- shared AppChrome/SurfaceContext redesign;
- Combat or World Graph changes;
- generalized condition/workflow engine;
- hiding/removing de-emphasized material from explicit navigation.

Do **not** STOP merely because BF3A CSS/layout needs meaningful change. Current
Moment layout inside the leased Play files is intentionally available to make
the Scene board dominant.

---

## §14 Review narrative

The PR should tell one product story:

```text
The Runbook already exists.
The Run already pins it.
North Gate is unmistakably the thing the GM is running.

The authored Decision lives inside North Gate.
Follow / Seal / Clear mutate only Runtime selection.
Consequence and the full authored branch-state relevance are immediately legible.
Nothing navigates automatically.
Inspect remains read-only; Make Current remains explicit.
At a Glance remains the contextual launcher around the one board.
Reload returns the same truth.
```

Do not claim the broader Play Surface is complete. NPC/Threat/Location/Table
At-a-Glance categories, global retrieval, notes refinement, Threat→Combat,
Combat durability, richer Runbook authoring, and real campaign session dogfood
remain later capabilities.

Formal review is against one exact head SHA at a time. Count each distinct-head
review judgment as one review cycle.
