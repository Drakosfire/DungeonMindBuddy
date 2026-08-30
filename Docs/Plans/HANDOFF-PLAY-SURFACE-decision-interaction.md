---
pr_body_template: |
  ## Handoff pointer
  - Conversation/workstream: PLAY-SURFACE / BF3B
  - Flow: PLAY-SURFACE
  - Direction: DESIGN → CODE → REVIEW
  - Handoff: `Docs/Plans/HANDOFF-PLAY-SURFACE-decision-interaction.md`
  - Branch / PR: `agent/play-surface-decision-interaction` / `PLAY-SURFACE: make authored Decisions table-usable`

  ## Verification pointer
  - Implementation base: record exact rebased `main`; design re-anchor observed `d4a91d7b727c0eae7dd0e09ba068e250b4819b44`
  - Changed paths: HANDOFF §8
  - Verification: HANDOFF §10

  The checked-in handoff, cumulative diff, exact-head automated evidence,
  real browser Decision witness against the already-committed §5 Runbook,
  and independently rerun evidence are the review contract.
---

# HANDOFF — Authored Decision interaction dogfood (BF3B)

**Created:** 2026-08-29  
**Scope correction:** 2026-08-29  
**Status:** READY FOR DISPATCH AFTER REBASE  
**Canonical handoff:** `Docs/Plans/HANDOFF-PLAY-SURFACE-decision-interaction.md`  
**Workstream:** `PLAY-SURFACE / BF3B`  
**Owner:** `PLAY-SURFACE`  
**Suggested branch:** `agent/play-surface-decision-interaction`  
**PR title:** `PLAY-SURFACE: make authored Decisions table-usable`

> Re-fetch and rebase onto current `main` before implementation. The latest
> observed `main` while correcting this handoff was
> `d4a91d7b727c0eae7dd0e09ba068e250b4819b44`; intervening CUTOVER work is a
> separate lane and must not be absorbed merely because main moved.

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

The previous handoff blurred witness setup with product scope. Correct that
before writing code.

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

### 0.2 What “Create blank Runbook” already means

The existing Play chooser action **Create blank Runbook** is predecessor
behavior. It creates the smallest legal durable Playable session script:

```text
kind        = runbook
title       = Blank Runbook
campaign    = explicit/validated campaign
content     = one empty spine Beat, Untitled Beat
status      = committed
```

It does **not**:

```text
create a Run
start a table session
make a Scene current
write Runtime progress
write Plan prep notes
invent campaign material beyond the minimum legal empty Beat
```

It exists because Play cannot start from nothing. A Run must pin an exact
committed Runbook revision, bootstrap is forbidden from seeding fake campaign
material, and empty APP-STATE therefore needs an explicit way to create the
future script.

BF3B must not change, rename, explain, or otherwise absorb that chooser action.

### 0.3 The chooser-language problem is separate

There is a legitimate product-language problem on the chooser:

```text
page title: Choose a Run
first empty-state action: Create blank Runbook
neighboring actions: Edit Runbook / Start exact Run
```

A new operator may not yet understand:

```text
Runbook = script
Run     = one pinned performance/runtime of a script revision
```

That missing explanatory sentence belongs to the Play chooser. It has been
captured separately in `Backlog.md` as an IDEA. It is **not BF3B** and must not
be implemented in this PR.

### 0.4 BF3B begins later

BF3B begins only after these facts are already true:

```text
1. a Decision-bearing Runbook WorkRevision is committed;
2. an exact Run pins that revision;
3. the Run is READY;
4. current Beat/Scene are authoritative Runtime state.
```

The BF3B implementation does not need to know how that Runbook was initially
created.

For disposable browser testing, the operator may use the already-shipped
DF0/BF4A product flow to prepare the §5 Runbook before the witness begins. That
is **environment preparation**, not BF3B acceptance and not BF3B code scope.

---

## §1 Mission and merge-ready invariant

### 1.1 Mission

> **Given an already-authored, already-committed v2 Runbook and a READY Run
> pinned to it, make authored Decisions operable in the Scene-centered Current
> Moment. The GM can select/change/clear one authored Option, see its authored
> consequence, and see derived Beat/Scene relevance change without navigation.**

### 1.2 Merge-ready invariant

Given the exact §5 Runbook and a READY Run with:

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
→ Follow it becomes authoritative selection only after server response
→ authored consequence visible
→ scene:tunnel-pursuit emphasized
→ beat:lower-tunnels emphasized

Change to option:seal-breach
→ exactly one existing progress CAS
→ current Beat/Scene unchanged
→ Seal the breach becomes authoritative selection
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

Hard reload restores the persisted selection and re-derives relevance from the
Run's exact sealed manifest + pinned Runbook. Relevance itself is never stored.

---

## §2 Atomic capability boundary

### KEEP — BF3B

- Project authored Decisions into the current Scene workspace.
- Project authored Option labels/body text.
- Explicit select Option.
- Explicit change selected Option.
- Explicit clear selection.
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
- Exact-head real browser witness using §5 material.

### OUT OF SCOPE / REJECT

- Create blank Runbook behavior or chooser copy.
- Explanation of Runbook vs Run on the chooser — backlog IDEA.
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
- Combat, World Graph/CUTOVER, Agent/Hermes.

One independently useful capability:

> **Use an already-authored fork at the table.**

---

## §3 Decision projection contract

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

For §5:

```text
choice:surviving-brood scene=scene:north-gate
```

so it appears when North Gate is current.

Current Scene remains the central workspace:

```text
CURRENT SCENE
North Gate
<scene prose>

Decisions
  What do they do with the surviving brood?
  <choice prose>
  Follow it
  Seal the breach
```

No new full-screen Decision workspace and no side rail are authorized.
No durable `currentDecisionId`.

---

## §4 Option, consequence, and relevance law

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

Activation wins suppression.
BF3B writes no relevance field.

For each target touched by the selected Option, show its human title and **final
derived relevance**, not merely raw edge wording.

For §5:

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

## §5 Mandatory dogfood Runbook input

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

### 5.1 Witness environment preparation is not BF3B

A disposable APP-STATE database may begin empty. Before executing the BF3B
browser witness, prepare the input using already-merged product behavior:

```text
obtain/create one committed Runbook containing the exact §5 bytes
→ Start exact Run from that committed revision
→ reach READY
→ Make North Gate current
```

This setup can reuse DF0/BF4A (`Create blank Runbook` → Edit Runbook → Save) if
needed. Do not count those steps as BF3B evidence and do not modify those paths.

The BF4A paste-residue finding remains authoring UX debt: ordinary paste can
leave the original blank Beat behind unless the operator removes it. If setup
uses the blank authoring path, remove the starter Beat manually before saving.
Do not fix paste/replace semantics in BF3B.

Do not hardcode disposable WorkObject or Run UUIDs. Stable dogfood identities
are the semantic IDs in the Markdown above.

---

## §6 Runtime mutation law

Use the existing full-progress CAS already owned by Current Moment:

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
all other selections
```

Client only offers Options belonging to the rendered Choice. Invalid
cross-Choice Option mutation fails closed/no-op client-side; backend remains
final authority.

Success:

```text
server returns updated Run
→ onAuthoritativeRun(updated)
→ existing v2 overlay/re-admission
→ selection becomes authoritative
→ relevance re-derived
```

Do not locally patch relevance.

Failure posture:

```text
409 stale CAS
→ exact GET Run
→ reconcile
→ visible conflict
→ no retry / merge / replay

422 semantic rejection
→ exact GET Run
→ reconcile
→ visible rejection distinct from conflict
→ no retry

unknown/network outcome
→ exact GET Run when possible
→ no blind retry
```

Stale async completion after Run switch/unmount must not mutate visible state.

---

## §7 Suggested implementation shape

Primary owner remains:

```text
apps/live-control-ui/src/playSurface/currentMoment/PlayCurrentMomentCockpit.tsx
```

It already owns the `replaceProgress(next)` CAS used by Make Current. Reuse that
boundary rather than creating a second write stack.

A small pure helper is allowed if useful:

```text
currentMoment/decisionInteractionModel.ts
```

Possible responsibilities only:

- operable Decisions for current Beat/Scene;
- selected Option lookup;
- membership validation;
- consequence projection;
- touched edge targets;
- Beat/Scene ID → human title;
- final relevance lookup.

No persistence, no workflow engine, no global Play state store.

Existing `NativeRunbookReadyV2` should already contain enough truth:

```text
beats[].choices[].options[]
manifest.edges[]
relevanceByTargetId
run.progress.selections
```

Only widen projection types after proving one exact missing datum.

---

## §8 Write lease

Re-check actual current main and active leases before editing.

Primary production/test lease:

```text
apps/live-control-ui/src/playSurface/currentMoment/PlayCurrentMomentCockpit.tsx
apps/live-control-ui/src/playSurface/currentMoment/PlayCurrentMomentCockpit.test.tsx
apps/live-control-ui/src/playSurface/playSurface.css
```

Optional new pure sibling:

```text
apps/live-control-ui/src/playSurface/currentMoment/decisionInteractionModel.ts
apps/live-control-ui/src/playSurface/currentMoment/decisionInteractionModel.test.ts
```

Conditional only if evidence requires:

```text
apps/live-control-ui/src/playSurface/currentMoment/currentMomentModel.ts
apps/live-control-ui/src/playSurface/currentMoment/currentMomentModel.test.ts
apps/live-control-ui/src/playSurface/runbook/nativeRunbookProjection.ts
apps/live-control-ui/src/playSurface/runbook/nativeRunbookProjection.test.ts
apps/live-control-ui/src/App.test.tsx
```

Routine state sync may update:

```text
Docs/Plans/HANDOFF-PLAY-SURFACE-runbook-authoring-gateway.md
Docs/Plans/HANDOFF-PLAY-SURFACE-decision-interaction.md
Docs/Roadmaps/ROADMAP-con-ready.md
Docs/Sources/design-agent/ACTIVE_AUTHORITY/ROADMAP-con-ready.md
Docs/Plans/STEWARDS-ANCHOR-con-ready.md
Docs/Sources/design-agent/ACTIVE_AUTHORITY/STEWARDS-ANCHOR-con-ready.md
```

Backward-looking truth must record BF4A/#660 DONE at accepted head
`d9b34ca87166572af8b482523862722fdd928fbe`, merge
`a3fd6219062d1cd978c394d07e2f80aaa6d203eb`, 2 review cycles; BF3B remains
CURRENT/IN FLIGHT until merge.

Explicitly unleased without STOP + approval:

```text
StartRunPanel / blank Runbook creation / chooser copy
Backlog.md chooser IDEA
Plan authoring or blank shell
backend progress schema/routes/services
Alembic / APP-STATE schema
WorkObject / WorkRevision
BF1 marker grammar/parser/serializer
Combat
World Graph / CUTOVER
AgentRuntime / Hermes
shared AppChrome host semantics
```

---

## §9 Automated evidence

Use §5 semantic structure in tests. Fixtures may represent the already-authored
Runbook; tests must not test or modify blank Runbook creation as part of BF3B.

Prove at minimum:

1. North Gate current projects `choice:surviving-brood`.
2. Beat-only does not project the Scene-associated Decision.
3. another Scene does not project North Gate's Decision.
4. unselected renders both Options and no selected consequence.
5. Follow performs exactly one progress write.
6. outgoing progress preserves Beat/Scene/resolved/notes/unrelated selections.
7. no optimistic selected state before authoritative response.
8. authoritative Follow renders consequence + Tunnel Pursuit/Lower Tunnels emphasized.
9. changing to Seal performs exactly one write and changes only this Choice.
10. Seal consequence renders; Tunnel Pursuit de-emphasized; Lower Tunnels default.
11. Clear performs exactly one write and removes only this Choice key.
12. selection mutations never change current Beat/Scene.
13. de-emphasized Tunnel Pursuit remains Inspectable and Make Current-capable.
14. already-selected Option spends no second CAS.
15. 409 rereads and never retries.
16. 422 rereads, never retries, and is distinct from 409 conflict.
17. unknown outcome rereads/no blind retry.
18. invalid cross-Choice Option fails closed.
19. reload restores selection and re-derives relevance.
20. stale async completion after Run switch/unmount is ignored.

Rerun owning regressions:

```text
PlayCurrentMomentCockpit tests
nativeRunbookProjection tests
v2RuntimeProjection tests
relevant App v2 Current Moment tests
frontend build/typecheck
uv run pytest tests/test_play_run_progress.py -q
```

Static checks:

```text
git diff --check
all changed paths inside §8
roadmap/steward mirrors byte-identical
no backend/schema/grammar diff
no persisted relevance
no currentDecisionId
no automatic navigation after selection
no StartRunPanel / blank Runbook product changes
```

---

## §10 Mandatory real browser dogfood witness

The BF3B witness begins **after environment preparation**.

Precondition recorded before Witness A:

```text
Committed Runbook = exact §5 semantic material
Run pins that exact committed revision
Run READY
Current Beat  = Hold the Breach
Current Scene = North Gate
selection for choice:surviving-brood = none
```

Record WorkObject UUID, revision/SHA, and Run UUID as evidence, but their
creation is predecessor setup rather than BF3B capability proof.

### Witness A — select Follow it

1. open the exact READY Run with North Gate current;
2. Decision prompt is visible inside the Current Scene workspace;
3. both authored Options are visible;
4. select **Follow it**;
5. verify North Gate remains current;
6. verify Follow is authoritatively selected;
7. verify its authored consequence is visible;
8. verify **Tunnel Pursuit — emphasized**;
9. verify **Lower Tunnels — emphasized**;
10. hard reload;
11. verify selection/consequence/relevance return;
12. verify Current Scene remains North Gate.

### Witness B — change to Seal the breach

1. select **Seal the breach**;
2. exactly one visible Option is selected;
3. North Gate remains current;
4. Seal consequence is visible;
5. **Tunnel Pursuit — de-emphasized**;
6. Lower Tunnels is default/not emphasized;
7. open At a Glance → Scenes;
8. Tunnel Pursuit remains present;
9. Inspect Tunnel Pursuit;
10. inspection does not move Current Scene;
11. Make Current remains available;
12. Back returns to North Gate.

### Witness C — clear

1. return to North Gate Decision;
2. Clear selection;
3. no Option remains selected;
4. no selected consequence is claimed;
5. Tunnel Pursuit returns default;
6. Lower Tunnels remains/defaults default;
7. hard reload;
8. cleared state remains cleared;
9. Current Scene remains North Gate.

At least one exact-head adversarial automated/browser proof must additionally
cover invalid Option→Choice membership and stale `run_revision` behavior.

---

## §11 Stop conditions

STOP before widening if BF3B appears to require:

- changing Create blank Runbook;
- changing chooser terminology/copy;
- Plan prep-note behavior;
- new backend endpoint/progress field/migration;
- grammar or Choice/Option membership changes;
- persisted relevance;
- `currentDecisionId`;
- auto-navigation or auto-resolution;
- Runbook authoring/paste changes;
- shared AppChrome changes;
- Combat, World Graph, AgentRuntime changes;
- generalized condition/workflow engine;
- hiding/removing de-emphasized material from explicit navigation.

If §5 exposes a parser/manifest defect, stop and classify whether the material
or existing BF1 contract is wrong before changing grammar.

---

## §12 PR narrative

Keep the implementation story narrow:

```text
The Runbook already exists.
The Run already pins it.
North Gate is already current.

BF3B adds one missing table interaction:
Decision → select/change/clear authored Option
         → authored consequence visible
         → relevance re-derived
         → no navigation
         → reload returns the same Runtime truth
```

Do not claim broader Play completion. Chooser language, richer authoring,
retrieval, additional At-a-Glance categories, notes refinement, Threat→Combat,
Combat durability, and real-session dogfood remain separate work.

Formal review is one judgment against one exact head SHA per cycle.