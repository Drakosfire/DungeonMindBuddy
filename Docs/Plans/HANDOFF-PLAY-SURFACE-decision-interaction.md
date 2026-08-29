---
pr_body_template: |
  ## Handoff pointer
  - Conversation/workstream: PLAY-SURFACE / BF3B
  - Flow: PLAY-SURFACE
  - Direction: DESIGN → CODE → REVIEW
  - Handoff: `Docs/Plans/HANDOFF-PLAY-SURFACE-decision-interaction.md`
  - Branch / PR: `agent/play-surface-decision-interaction` / `PLAY-SURFACE: make authored Decisions table-usable`

  ## Verification pointer
  - Dispatch base: record exact current `main`; design base is `6b7706eec400129dbe01288630c443ae2d8a1e67`
  - Changed paths: HANDOFF §9
  - Verification: HANDOFF §11

  The checked-in handoff, cumulative diff, exact-head automated evidence,
  real browser Decision dogfood witness using the §5 Runbook, and independently
  rerun evidence are the review contract. This body is transport metadata.
---

# HANDOFF — Authored Decision interaction dogfood (BF3B)

**Created:** 2026-08-29  
**Status:** READY FOR DISPATCH  
**Canonical handoff path:** `Docs/Plans/HANDOFF-PLAY-SURFACE-decision-interaction.md`  
**Workstream:** `PLAY-SURFACE / BF3B`  
**Flow / owner:** `PLAY-SURFACE`  
**Handoff direction:** DESIGN → CODE  
**Suggested branch:** `agent/play-surface-decision-interaction`  
**PR title:** `PLAY-SURFACE: make authored Decisions table-usable`

> **Design / dispatch base:** `main` `6b7706eec400129dbe01288630c443ae2d8a1e67`.
>
> This main includes merged BF4A / PR #660. Re-fetch main and inspect active
> PRs/worktrees immediately before implementation. No open GitHub PRs were
> present when this handoff was written; do not assume that remains true.

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
  DONE — local Play dogfood bootstrap
  accepted head: dc20fe8e63eec691265e75eb73c69f441ffd779d
  merge:         87a769d05605ff021d28f0b69c5d7ab0b8205440
  review cycles: 3

PLAN-BLANK-SHELL / PR #661
  DONE — blank Plan is a real authoring surface state
  accepted head: ffa0b18d6212a6780d6be90f91a25626bf15b464
  merge:         770f79cca4aa3c12aa8a35db2db77ce376f2ff9e
  review cycles: 4

BF4A / PR #660
  DONE — native Runbook reopen/save
  accepted head: d9b34ca87166572af8b482523862722fdd928fbe
  merge:         a3fd6219062d1cd978c394d07e2f80aaa6d203eb
  review cycles: 2
```

BF3B is now the active Play Surface slice.

---

## §0 Why this slice exists

We now have the complete authored-material path that earlier BF3B planning was
missing:

```text
Play
→ Create blank Runbook
→ Edit Runbook
→ ordinary Plan/TipTap authoring
→ Save pathless native Runbook WorkRevision
→ Start exact Run
→ BF3A Current Moment
```

BF4A's real browser witness proved that the representative v2 Runbook in §5 can
be authored through the product and admitted by Play. It also proved historical
Run isolation and cross-campaign fail-closed authoring.

The next missing table capability is no longer authoring. It is using the
Decision that is already present in the pinned Runbook.

Current product truth:

```text
NativeRunbookReadyV2 already contains:
  Beat.choices[]
  Choice.options[]
  Choice/Option body text

Run.progress already persists:
  selections: { choiceId: optionId }

v2RuntimeProjection already derives:
  emphasized / de-emphasized / default
  from sealed manifest edges + persisted selections

PlayCurrentMomentCockpit currently renders:
  current Beat
  current Scene
  Scenes inventory / inspect / Make Current

But it does not render or mutate Decisions.
```

Therefore BF3B is deliberately a projection/runtime interaction slice, not a
new data-model slice.

---

## §1 Mission and merge-ready invariant

### 1.1 Mission

> **Make authored Decisions operable in the Scene-centered Current Moment. The
> GM can see the Decision relevant to the current context, select/change/clear
> one authored Option, see the selected Option's authored consequence, and see
> the resulting Beat/Scene relevance change. Each selection mutation uses the
> existing Play Runtime CAS. Decision interaction never navigates, never writes
> relevance, and never changes the current Beat/Scene.**

### 1.2 Merge-ready invariant

Given the exact §5 Runbook and a READY Run with `scene:north-gate` current:

```text
Current Beat  = beat:hold-breach
Current Scene = scene:north-gate
Decision      = choice:surviving-brood
Selection     = none
```

The GM can perform:

```text
Select option:follow-brood
→ one existing progress CAS
→ selection persists
→ current Beat/Scene unchanged
→ authored consequence visible
→ scene:tunnel-pursuit is emphasized
→ beat:lower-tunnels is emphasized

Change to option:seal-breach
→ one existing progress CAS
→ selection changes
→ current Beat/Scene unchanged
→ authored consequence changes
→ scene:tunnel-pursuit is de-emphasized
→ beat:lower-tunnels returns to default

Clear selection
→ one existing progress CAS
→ choice entry removed from selections
→ current Beat/Scene unchanged
→ no selected consequence
→ affected relevance returns to derived default
```

After hard reload, persisted selection is restored and relevance is re-derived
from the sealed edges. No relevance value is stored in Runtime.

### 1.3 First dogfood loop this completes

BF3B closes the first complete authored-intent → runtime-use loop:

```text
GM authors Decision in Runbook
→ immutable WorkRevision
→ Run pins exact revision
→ Play shows current Scene
→ GM selects an authored Option
→ Runtime records the selection
→ authored consequence + relevance become visible
→ reload preserves the table state
```

---

## §2 Atomic capability boundary

### KEEP — this PR

- Render authored Decisions in the current-moment central workspace.
- Render authored Option labels.
- Explicit select Option.
- Explicit change selected Option.
- Explicit clear selection.
- Show current selected state from authoritative Runtime only.
- Show the selected Option's authored `bodyText` as its consequence framing.
- Show resulting relevance for Beat/Scene targets touched by that selected Option.
- Preserve activation-wins-suppression semantics from the existing derived projection.
- Use the existing `putPlayRunProgress` CAS boundary.
- Preserve all unrelated Run progress fields.
- Exact reread/reconcile after failed writes.
- 409 conflict remains conflict; no automatic merge/retry.
- Same-generation 422 rejection is never retried or reclassified as 409.
- Reload/resume preserves selection and re-derives relevance.
- De-emphasized Scene remains Inspectable and Make Current remains available.
- Real browser witness using the exact §5 Runbook authored through the normal product path.

### SPLIT / DEFER

- Add Decision / Add Option authoring controls — BF4.
- Edit Decision/Option structure from Play — BF4/later authoring.
- Freeform `Option D` creation during Play — later Agent/authoring proposal path.
- Persistent `currentDecisionId` or Decision focus — reject.
- Automatic navigation after selecting an Option — reject.
- Automatic Beat/Scene resolution — reject.
- Condition/expression/workflow DSL — reject.
- Persisted relevance fields — reject.
- At-a-Glance Decisions category — later only if dogfood proves need.
- Global cross-Beat Scene browser — later retrieval/At-a-Glance work.
- Notes changes — separate slice.
- Threat/NPC/global retrieval — subsequent Play slice.
- Combat — Combat lane.
- Runbook grammar/parser changes — reject.
- WorkObject/WorkRevision changes — reject.
- Backend schema/migration/new endpoint — reject.
- Plan/authoring changes — reject.
- Agent/Hermes — separate lane.

This PR remains one independently useful capability:

> **Use the authored fork at the table.**

---

## §3 Decision projection contract

### 3.1 Decision ownership remains Beat-first

Durable containment stays:

```text
Beat
  → Scene
  → Decision
      → Option
```

A Decision is a Beat-owned `choice` and may optionally carry a Scene
association used for projection.

Do not move Decisions under Scenes in the durable model.

### 3.2 Which Decisions are operable in the current workspace

BF3B freezes this minimum projection rule:

When a Scene is current:

```text
operable Decisions =
  current Beat choices where sceneId == null
  + current Beat choices where sceneId == currentSceneId
```

When no Scene is current:

```text
operable Decisions =
  current Beat choices where sceneId == null
```

A Decision associated with another Scene is not silently projected into the
current Scene merely because it belongs to the same Beat.

This is a presentation rule, not access control. Future At-a-Glance/retrieval
work may expose Decisions from other Scenes without changing Runtime position.

For the §5 dogfood material:

```text
choice:surviving-brood scene=scene:north-gate
```

so it becomes operable when North Gate is current.

### 3.3 Placement

Current Scene remains the dominant central workspace.

Preferred composition:

```text
CURRENT SCENE
North Gate
<scene prose>

Decisions
  What do they do with the surviving brood?
  <choice body>
  <Options>
```

Do not turn the Decision into a new full-screen workspace for BF3B.
Do not add a second side rail.
Do not make Decision interaction compete with Scene identity/orientation.

Exact visual styling is not frozen.

### 3.4 No durable Decision focus

There is no `currentDecisionId`.

If multiple Decisions are operable, render them in authored order. Local visual
focus may exist for accessibility/usability but is ephemeral and never persisted.

---

## §4 Option / consequence / relevance contract

### 4.1 Option state

The authoritative selected Option is always:

```text
run.progress.selections[choice.id]
```

No local optimistic selected state may pretend a write succeeded.

UI requirements:

- every authored Option label is visible;
- the selected Option is unambiguous;
- selecting another Option changes the selection explicitly;
- Clear selection is explicit and visible when a selection exists;
- selecting the already-selected Option should be a no-op rather than spending a CAS;
- clearing when nothing is selected should be disabled/absent/no-op.

Native radio semantics or equivalent accessible pressed/selected controls are
acceptable. Exact component choice is not frozen.

### 4.2 Consequence

For BF3B, the selected Option's authored `bodyText` is the consequence framing.

For the dogfood material:

```text
Follow it
→ "The party pursues the retreating creatures into the lower tunnels before reinforcements arrive."

Seal the breach
→ "The immediate breach is contained, but the surviving creatures remain somewhere below."
```

Do not infer outcome from edges.
Do not invent prose when bodyText is empty.
Do not claim the selected Option is what actually happened beyond the explicit
Runtime selection.

### 4.3 Resulting relevance

Relevance continues to be derived only by the existing rule:

```text
selected Runtime Options
+ sealed manifest activates/suppresses edges
→ emphasized / de-emphasized / default
```

Activation wins suppression.

BF3B must not write relevance into `PlayRunProgress`.

The selected Decision should expose enough resulting relevance to make the
branch legible without forcing navigation. For each target touched by the
selected Option's sealed edges, show:

```text
target human title
final derived relevance
```

Use the final `deck.relevanceByTargetId` result, not merely the raw edge verb,
because another selected Decision may activate a target that this Option
suppresses.

For §5:

```text
Follow it
  Tunnel Pursuit → emphasized
  Lower Tunnels  → emphasized

Seal the breach
  Tunnel Pursuit → de-emphasized
```

When switching Follow → Seal, `Lower Tunnels` must return to `default`; it must
not remain visually sticky merely because a prior selection activated it.

The existing Scenes inventory should continue to show its relevance label.
A small selected-Decision relevance summary is necessary because the dogfood
also targets `beat:lower-tunnels`, which is outside the current Beat's Scenes
inventory.

### 4.4 Relevance is never permission

After selecting `Seal the breach`, `Tunnel Pursuit` is de-emphasized.

It must still be possible to:

```text
At a Glance → Scenes
→ Tunnel Pursuit · de-emphasized
→ Inspect
→ Make Current
```

No filtering, disabling, hiding, or navigation denial is allowed merely because
a target is suppressed/de-emphasized.

---

## §5 Mandatory dogfood Runbook

Use this exact representative material. It is inherited from BF4A and was
already proven authorable/round-trippable through the real product.

It is acceptance material, not production seed data.

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

Expected structure:

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

### 5.1 BF4A paste-residue finding

BF4A browser dogfood discovered that ordinary paste into the DF0 blank Runbook
does not replace the existing `Untitled Beat`; it can leave an empty starter
Beat/heading that later fails Play admission as an orphaned marker.

That is **not** a BF3B implementation problem.

For the BF3B browser witness:

1. create/open the blank Runbook through the product;
2. unlock editing;
3. deliberately clear/remove the starter Beat content using ordinary editor
   controls before inserting the §5 Markdown;
4. Save;
5. verify the committed Runbook starts with the §5 material and is Play-admissible.

Do not implement paste-replace semantics, parser forgiveness, automatic starter
cleanup, or schema changes in BF3B. Record any additional authoring UX residue
for later BF4/paste-replace work.

### 5.2 Do not depend on prior disposable UUIDs

The BF4A witnesses produced useful disposable identities, but they are not
product fixtures or durable cross-environment inputs.

Do not hardcode:

```text
af649cb5-7cc1-4aea-81dc-0f21925530f9
307911bd-c63b-42bd-82fd-896ceecc9a5f
d3fffd93-91c5-49ef-9695-962f183f0bb9
```

The §5 semantic IDs are the stable dogfood identities. WorkObject/Run UUIDs are
allocated normally in each witness environment.

---

## §6 Runtime mutation law

### 6.1 Existing CAS only

BF3B adds no backend endpoint.

Every select/change/clear uses the existing boundary already used by Current
Moment:

```text
PUT Play Run progress
expected_run_revision = authoritative current run_revision
progress = full canonical progress with only selections changed
```

Select/change:

```ts
selections = {
  ...run.progress.selections,
  [choiceId]: optionId,
}
```

Clear:

```text
copy current selections
remove only choiceId
preserve every other selection
```

Preserve exactly:

```text
current_beat_id
current_scene_id
resolved_beat_ids
notes_by_element_id
other Decision selections
```

### 6.2 Client validity

The UI must only offer Options belonging to the rendered Choice.

Before constructing the mutation, the client should fail closed/no-op if the
requested Option is not a member of that Choice in the admitted deck.

The backend remains final authority.

### 6.3 No optimistic selection

During the write:

```text
old authoritative selection remains visibly authoritative
Saving… may be shown
controls may be disabled
```

Only the returned/reconciled Run may change the selected state.

### 6.4 Success

On successful CAS:

```text
onAuthoritativeRun(updated Run)
→ existing v2 Runtime overlay/re-admission path
→ relevance re-derived
→ same current Beat/Scene
```

Do not locally patch `deck.relevanceByTargetId`.

### 6.5 409 conflict

Existing posture remains:

```text
409
→ exact GET Run
→ reconcile authoritative Run
→ show conflict
→ no automatic retry
→ no merge
```

### 6.6 422 rejection

A same-generation semantic 422 is not a stale-write conflict and must never be
reclassified as 409.

Required:

```text
422
→ exact GET Run for reconciliation
→ no resend/retry
→ no optimistic selection retained
→ visible rejection/error state distinct from conflict
```

A local cockpit error state is preferred over widening the shared v1
`RunbookMutationStatus` unless evidence proves a shared type change is cleaner.

If the reread proves the Run binding itself changed, allow the existing parent
admission/reconciliation path to handle that new authority. Do not automatically
replay the rejected selection against it.

### 6.7 Unknown outcome

Keep the existing exact-reread posture for network/unknown errors.

No blind retry.

---

## §7 Suggested implementation shape

This is guidance, not a requirement to manufacture abstractions.

### 7.1 Keep the mutation boundary in Current Moment

`PlayCurrentMomentCockpit.tsx` already owns one `replaceProgress(next)` CAS
boundary for Make Current. Reuse it.

Do not create a second fetch/write stack for Decisions.

A small refactor is acceptable if it makes select/change/clear readable while
preserving the exact same ownership and failure semantics.

### 7.2 Add one small derived Decision model if useful

Preferred bounded helper:

```text
currentMoment/decisionInteractionModel.ts
```

Possible responsibilities:

- operable Decisions for current Beat/Scene;
- selected Option lookup;
- validate Option belongs to Choice;
- selected consequence projection;
- touched relevance targets from sealed edges;
- map Beat/Scene target IDs to human titles;
- final relevance lookup from `relevanceByTargetId`.

This helper must be pure derived projection. It owns no persistence or local
Runtime truth.

Do not add a generalized workflow engine or global Play state store.

### 7.3 Existing projection should remain sufficient

Current `NativeRunbookReadyV2` already provides:

```text
beats[].choices[].options[]
manifest.edges[]
relevanceByTargetId
run.progress.selections
```

Prefer deriving BF3B display from those existing truths.

Only widen `nativeRunbookProjection.ts` if an exact missing datum is proven.
Do not duplicate edges or persisted relevance merely for component convenience.

---

## §8 UX / accessibility acceptance

The table interaction must be fast and legible.

Minimum requirements:

- Decision prompt is a real heading/legend relationship, not anonymous text.
- Options are keyboard reachable.
- selected Option is exposed semantically (`checked`, `aria-pressed`, or
  equivalent appropriate control semantics).
- Clear selection is keyboard reachable and specifically labeled.
- Save/mutation busy state prevents double-submit.
- consequence is associated visibly with the selected Option.
- relevance target names are human titles; IDs may remain diagnostic only.
- current Beat and Scene orientation remain visible through selection/change.
- no focus teleport to another Scene after selection.

Do not overbuild styling. This is a table-speed capability proof.

---

## §9 Write lease

Re-check actual current `main` and open worktrees before editing.

### 9.1 Primary production lease

Expected:

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

### 9.2 Bounded discovery / conditional lease

Only if implementation evidence requires it:

```text
apps/live-control-ui/src/playSurface/currentMoment/currentMomentModel.ts
apps/live-control-ui/src/playSurface/currentMoment/currentMomentModel.test.ts
apps/live-control-ui/src/playSurface/runbook/nativeRunbookProjection.ts
apps/live-control-ui/src/playSurface/runbook/nativeRunbookProjection.test.ts
apps/live-control-ui/src/App.test.tsx
```

If a new tiny test-only representative Markdown fixture materially reduces
copy/paste drift, it may live under the existing Play Surface test area. It must
not become production seed behavior.

### 9.3 State-authority sync leased to this implementation PR

Routine state sync rides with BF3B rather than a docs-only PR:

```text
Docs/Plans/HANDOFF-PLAY-SURFACE-runbook-authoring-gateway.md
Docs/Plans/HANDOFF-PLAY-SURFACE-decision-interaction.md
Docs/Roadmaps/ROADMAP-con-ready.md
Docs/Sources/design-agent/ACTIVE_AUTHORITY/ROADMAP-con-ready.md
Docs/Plans/STEWARDS-ANCHOR-con-ready.md
Docs/Sources/design-agent/ACTIVE_AUTHORITY/STEWARDS-ANCHOR-con-ready.md
```

Required backward-looking truth:

```text
BF4A / PR #660
  DONE
  accepted head d9b34ca87166572af8b482523862722fdd928fbe
  merge a3fd6219062d1cd978c394d07e2f80aaa6d203eb
  review cycles 2

BF3B
  CURRENT / IN FLIGHT until this PR merges
```

Re-anchor headers to the actual implementation base, not merely the design base
in this handoff. Keep canonical/mirror pairs byte-identical.

### 9.4 Explicitly unleased

Do not modify without STOP + operator/reviewer approval:

```text
backend Play progress schemas/routes/services
Alembic migrations
application-state schema
WorkObject / WorkRevision model
BF1 grammar / marker parser / serializer
Plan authoring / BF4A authoring paths
blank Plan shell / promotion state
Combat
World Graph / CUTOVER
AgentRuntime / Hermes
shared AppChrome host semantics
```

If BF3B appears to require any of these, stop and record the exact missing seam.

---

## §10 Automated evidence contract

### 10.1 Pure derived model

If a Decision helper is added, cover at minimum:

1. current Scene gets Beat-level + same-Scene associated Decisions;
2. Decision associated with a different Scene is not projected into current Scene;
3. Beat-only gets only unassociated Beat Decisions;
4. selected Option lookup from Runtime;
5. selected consequence is Option bodyText;
6. Follow it touched targets resolve to human titles + final emphasized relevance;
7. Seal the breach resolves Tunnel Pursuit to de-emphasized;
8. activation-wins-suppression uses final derived relevance, not raw edge wording;
9. invalid cross-Choice option lookup fails closed.

### 10.2 Cockpit interaction

Use the exact §5 semantic structure in tests.

Prove:

1. North Gate current renders `choice:surviving-brood`;
2. unselected state renders both Options and no selected consequence;
3. selecting Follow it performs exactly one progress write;
4. outgoing progress preserves current Beat/Scene/resolved/notes/unrelated selections;
5. no optimistic selected state before response;
6. authoritative rerender shows Follow selected and consequence;
7. resulting relevance summary shows Tunnel Pursuit + Lower Tunnels emphasized;
8. change to Seal performs exactly one write and replaces only this choice's selection;
9. Seal consequence becomes visible;
10. Tunnel Pursuit becomes de-emphasized and Lower Tunnels returns default;
11. clear performs exactly one write and removes only this choice key;
12. selection mutations never alter current Beat/Scene;
13. de-emphasized Tunnel Pursuit remains Inspectable / Make Current capable;
14. already-selected Option does not spend a second CAS;
15. 409 exact-rereads and does not retry;
16. 422 exact-rereads, does not retry, and is not presented as 409 conflict;
17. unknown outcome exact-rereads and does not blind retry;
18. stale async completion after Run switch/unmount cannot mutate visible state.

### 10.3 Projection/reload

Prove through the existing admission/overlay tests as needed:

```text
persisted selections
→ overlayRuntimeOnV2Ready / equivalent existing path
→ selected Option restored
→ relevance re-derived
```

No test should assert a persisted relevance field because none is authorized.

### 10.4 Regression

At minimum rerun:

```text
PlayCurrentMomentCockpit tests
nativeRunbookProjection tests
v2RuntimeProjection tests
App tests relevant to v2 Current Moment
frontend build/typecheck
```

Run the owning backend Play progress validation suite even if no backend code
changes, because BF3B relies on its Choice→Option validation and CAS semantics.

Recommended existing backend boundary:

```text
uv run pytest tests/test_play_run_progress.py -q
```

Use the project's application-state disposable PostgreSQL test posture; do not
skip because local APP-STATE is inconvenient.

### 10.5 Static / scope

- `git diff --check`
- changed paths inside §9
- canonical/mirror `cmp` identical
- no backend/schema/grammar diff
- no relevance persistence field added
- no `currentDecisionId` added
- no auto-navigation code after Option mutation

---

## §11 Mandatory real browser dogfood witness

Fixture-only evidence is insufficient. The reason BF4A existed was that a test
could prove a capability the GM could not actually reach.

Run this witness against the exact implementation head using a disposable
APP-STATE PostgreSQL database.

### Witness A — author the real dogfood Runbook

1. start ordinary API + Vite UI against disposable APP-STATE;
2. open `/play?choose=1`;
3. create a blank Runbook for a campaign compatible with the active Plan view
   (`longmont-c2` is acceptable for the current local product context);
4. use product **Edit Runbook**;
5. verify Plan says the exact Runbook is being edited;
6. unlock editing;
7. deliberately remove/clear the starter `Untitled Beat` content per §5.1;
8. paste the exact §5 Markdown through ordinary editor interaction;
9. Save;
10. hard reload the exact Runbook URL;
11. verify Hold the Breach / North Gate / Decision / Options remain intact;
12. return to Play;
13. start a new exact Run from that current committed revision;
14. verify READY begins at Hold the Breach with no current Scene;
15. Make North Gate current.

Record allocated WorkObject UUID, revision/SHA, and Run UUID as witness evidence
only. Do not turn them into fixtures.

### Witness B — select Follow it

Starting from North Gate current:

1. Decision prompt is visible in the central Current Scene workspace;
2. both authored Options are visible;
3. select **Follow it**;
4. verify North Gate remains current;
5. verify Follow it is authoritatively selected;
6. verify Follow it consequence text is visible;
7. verify **Tunnel Pursuit — emphasized**;
8. verify **Lower Tunnels — emphasized**;
9. hard reload the Run;
10. verify the same selection/consequence/relevance return;
11. verify current Scene is still North Gate.

### Witness C — change to Seal the breach

1. select **Seal the breach**;
2. verify exactly one visible selection now exists for the Decision;
3. verify North Gate remains current;
4. verify Seal consequence text is visible;
5. verify **Tunnel Pursuit — de-emphasized**;
6. verify Lower Tunnels is no longer emphasized (default);
7. open At a Glance → Scenes;
8. verify Tunnel Pursuit remains present despite de-emphasis;
9. Inspect Tunnel Pursuit;
10. verify inspecting it does not change current Scene;
11. verify Make Current remains available;
12. Back returns to North Gate.

Do not actually Make Current unless useful for an additional proof; BF3B's key
claim is that relevance does not gate the action.

### Witness D — clear

1. return to the current Scene Decision;
2. Clear selection;
3. verify no Option is selected;
4. verify no selected consequence is claimed;
5. verify Tunnel Pursuit returns default;
6. verify Lower Tunnels remains/defaults to default;
7. hard reload;
8. verify cleared selection remains cleared;
9. verify current Scene remains North Gate.

### Witness E — historical authored revision safety spot-check

BF4A already proved historical Run isolation; BF3B must not regress it.

If the witness environment still has an older Run pinned to an earlier revision
of the same Runbook, reopen it and confirm BF3B Decision UI derives only from
that Run's exact pinned revision. Do not require fabricating an extra old Run
solely for this optional spot-check if the environment is clean; automated
historical revision regression remains mandatory.

---

## §12 Failure / adversarial witness

At least one exact-head automated or browser-level adversarial proof must cover
semantic rejection:

```text
attempt selection where option does not belong to choice
→ backend 422 / client rejection boundary
→ no Runtime progress mutation
→ no retry
→ no conflict mislabel
→ authoritative Run reread
```

This may be automated rather than manually forged through browser UI, because
ordinary UI must not expose invalid cross-Choice combinations.

Also prove stale run_revision:

```text
writer A advances Run
writer B selects with stale expected revision
→ 409
→ exact reread
→ no selection replay
```

---

## §13 Stop conditions

STOP and report before widening if implementation requires:

- a new backend endpoint or progress field;
- a migration;
- changing Choice/Option membership rules;
- changing v2 marker grammar;
- persisting relevance;
- adding `currentDecisionId`;
- auto-navigating after selection;
- auto-resolving Beats/Scenes;
- changing Runbook authoring or paste behavior;
- changing Plan blank-shell state;
- changing shared AppChrome host semantics;
- changing Combat or World Graph;
- creating a generalized condition/workflow engine;
- hiding/removing de-emphasized material from explicit navigation.

If the exact §5 material exposes a new parser/manifest defect, stop and classify
whether the material or existing BF1 contract is wrong before changing grammar.

---

## §14 PR narrative / review expectations

The implementation PR should tell a simple story:

```text
BF4A made the authored Decision reachable.
BF3B makes that authored Decision usable.

North Gate stays current.
The GM chooses Follow it / Seal the breach / clear.
The selected consequence is visible.
Authored relevance changes.
Nothing navigates automatically.
Reload returns the same Runtime truth.
```

Review should be performed against one exact head SHA at a time. Count each
formal distinct-head judgment as one review cycle.

Do not claim the broader Play Surface is complete after BF3B. This slice proves
one authored branch interaction. Retrieval, additional At-a-Glance categories,
notes refinement, Threat→Combat, Combat durability, and real-session dogfood
remain subsequent capabilities.
