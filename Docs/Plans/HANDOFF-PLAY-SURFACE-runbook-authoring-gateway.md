---
pr_body_template: |
  ## Handoff pointer
  - Conversation/workstream: PLAY-SURFACE / BF4A
  - Flow: PLAY-SURFACE
  - Direction: DESIGN → CODE → REVIEW
  - Handoff: `Docs/Plans/HANDOFF-PLAY-SURFACE-runbook-authoring-gateway.md`
  - Branch / PR: `agent/play-surface-runbook-authoring-gateway` / `PLAY-SURFACE: make native Runbooks editable`

  ## Verification pointer
  - Re-dispatch base: `770f79cca4aa3c12aa8a35db2db77ce376f2ff9e` or later current `main`
  - Changed paths: HANDOFF §8 only
  - Verification: HANDOFF §10

  The checked-in handoff, cumulative diff from the actual rebased base, real
  browser Runbook-authoring witness, historical-Run isolation witness, and
  independently rerun evidence are the review contract. This body is transport
  metadata.
---

# HANDOFF — Native Runbook authoring gateway (BF4A)

**Created:** 2026-08-28  
**Re-designed / re-anchored:** 2026-08-29  
**Status:** DONE  
**Canonical handoff path:** `Docs/Plans/HANDOFF-PLAY-SURFACE-runbook-authoring-gateway.md`  
**Workstream:** `PLAY-SURFACE / BF4A`  
**Flow / owner:** `PLAY-SURFACE`  
**Handoff direction:** DESIGN → CODE  
**Implementation branch / PR:** `agent/play-surface-runbook-authoring-gateway` / PR #660  
**PR title:** `PLAY-SURFACE: make native Runbooks editable`  
**Accepted head:** `d9b34ca87166572af8b482523862722fdd928fbe`  
**Merge:** `a3fd6219062d1cd978c394d07e2f80aaa6d203eb`  
**Review cycles:** 2

> **Required re-dispatch base:** current `main` at or after
> `770f79cca4aa3c12aa8a35db2db77ce376f2ff9e`, the merge of PLAN-BLANK-SHELL /
> PR #661.
>
> Re-fetch `main`, inspect active PRs/write leases, and rebase before any more
> implementation work. The pre-rebase PR #660 head
> `4423f3af47915b984d78f3f74a9f87c4d2d8a84b` is candidate code, not accepted
> evidence. Mine it if useful; do not preserve a behavior merely because it is
> already implemented there.

Parent authorities:

- `AGENTS.md`
- `Docs/Design/ARCHITECTURE-playable-material-and-runtime.md`
- `Docs/Design/DESIGN-play-current-moment-cockpit.md`
- `Docs/Design/DESIGN-playable-authoring-and-adoption.md`
- `Docs/Design/ARCHITECTURE-application-state-layer.md`
- `Docs/Plans/HANDOFF-PLAN-SURFACE-blank-authoring-shell.md`
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
  DONE — Current Moment
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
```

BF4A is DONE at PR #660 (accepted head `d9b34ca87166572af8b482523862722fdd928fbe`,
merge `a3fd6219062d1cd978c394d07e2f80aaa6d203eb`, 2 review cycles). BF3B is the
current successor and owns Runtime Decision selection, consequence presentation,
and relevance changes on an already-committed Runbook and READY Run.

---

## §0 Why this re-anchor exists

The first BF4A design correctly identified the authoring gap but was written
before we understood the Plan zero-material failure mode. PR #661 has now fixed
that prerequisite:

```text
bare /plan
→ truthful local blank shell
→ Edit / Tools chrome remains mounted
→ first Plan Save promotes local draft safely
→ exact document load/error states retain shell chrome
```

That means BF4A no longer owns blank-shell semantics.

It owns one smaller thing:

> **A committed native Runbook that already exists must be reachable from Play,
> editable in the existing Plan authoring surface, and saveable as the next
> immutable Runbook WorkRevision even when `target_relpath` is null.**

PR #660 Review Cycle 1 also exposed an independent authority flaw in the old
implementation: exact Runbook editing could combine a Runbook from one campaign
with Plan/World context from another campaign. This re-anchor resolves that as
part of BF4A rather than leaving it as an implementation-time stop condition.

Finally, the handoff now freezes the actual small Runbook we intend to use for
BF4A/BF3B dogfood. It is test/witness material, not production seed content.

---

## §1 Mission and merge-ready invariant

### 1.1 Mission

> **From the ordinary Play Runbook chooser, a GM can select one committed native
> Runbook, explicitly open that exact WorkObject in the existing Plan/TipTap
> authoring surface, edit or paste canonical v2 Playable Markdown, and Save a
> new immutable WorkRevision even when the Runbook has no `target_relpath`.
> Existing Runs remain pinned to their historical revisions.**

### 1.2 Merge-ready invariant

For any selected active committed `kind=runbook` WorkObject whose campaign is
admissible to the current Plan context:

```text
Play chooser
→ Edit Runbook
→ /plan?documentId=<exact WorkObject UUID>
→ truthful Runbook editor identity
→ Unlock editing
→ edit / canonical Markdown paste
→ Save
→ same WorkObject UUID
→ next immutable WorkRevision
→ hard reload exact URL
→ exact committed content survives
→ Play
→ Start exact Run
→ new Run binds the new revision
```

At the same time:

```text
an existing Run pinned to revision N
remains pinned to revision N
when Runbook revision N+1 is committed
```

No Save may automatically start, rebase, switch, or mutate a Run.

### 1.3 First-use path enabled by the predecessor

DF0 + PLAN-BLANK-SHELL make this ordinary path possible:

```text
Play chooser
→ Create blank Runbook
→ newly committed blank Runbook remains selected
→ Edit Runbook
→ Plan authoring surface
→ replace the minimal Beat-only material with canonical v2 material
→ Save revision N+1
→ Play
→ Start exact Run from N+1
```

No Run needs to exist before editing.

---

## §2 Atomic capability boundary

### KEEP — this PR

- Explicit `Edit Runbook` action from the selected Runbook in `StartRunPanel`.
- Exact WorkObject UUID navigation; list reorder/refresh cannot retarget it.
- Truthful `kind=runbook` identity in the authoring surface.
- Runbook-specific exact-document campaign admission.
- Pathless Runbook Save through the existing shared prepare/commit pipeline.
- Existing path-backed/path-required Plan Save behavior unchanged.
- Same WorkObject identity, new immutable WorkRevision.
- Canonical v2 Beat/Scene/Decision/Option Markdown survives edit → Save → reload.
- Existing Run remains pinned to its historical revision.
- New explicit Run may bind the new revision.
- Real browser witness using the representative Runbook in §5.

### SPLIT / REJECT

- Structure-aware `Add Beat`, `Add Scene`, `Add Decision`, `Add Option` controls — BF4.
- Decision selection/change/clear UI — BF3B.
- Runtime relevance presentation — BF3B.
- Mixed Plan/Runbook default selector — defer.
- Generic Authoring product/router redesign — reject for this slice.
- New Runbook save endpoint or persistence model — reject.
- WorkObject/WorkRevision schema changes — reject.
- BF1 grammar changes — reject.
- Automatic Run rebase — reject.
- Automatic Start Run — reject.
- Fake filesystem target for a pathless Runbook — reject.
- World publication/canon adoption — reject.
- Agent authoring — later lane.

This must remain one independently useful capability:

> **Reopen and save the Runbook you already have.**

---

## §3 Product interaction contract

### 3.1 Play remains the discovery point

`StartRunPanel` already lists active Runbooks and leaves a newly created blank
Runbook selected. BF4A adds one explicit action bound to that selected record:

```text
[ selected Runbook ]

[ Edit Runbook ]
[ Start exact Run ]
```

No selection:

```text
Edit Runbook disabled or absent
```

The edit target is the selected record's exact `document_id`, never title,
list index, target path, latest Run, or remembered previous selection.

### 3.2 Navigation

Use the existing exact document route:

```text
/plan?documentId=<runbook.document_id>
```

No new Runbook editor route is authorized unless reuse proves impossible and
the implementer stops for design review.

### 3.3 Truthful Runbook identity

Once exact admission succeeds, the authoring surface must make it obvious that
the operator is editing a Runbook rather than silently treating it as a Plan.

At minimum:

```text
Runbook kind is preserved
Runbook title is visible
exact WorkObject is the Canvas/Agent durable identity
```

Opaque UUID may remain diagnostic identity; it must not be the primary label.

### 3.4 Return path

Normal AppChrome Play navigation is sufficient. Do not add a durable return
stack or auto-navigation after Save.

---

## §4 Campaign authority law

The pre-reanchor PR #660 allowed this unsafe shape:

```text
selected Runbook campaign = C1
PlanView / World context  = C2
→ exact document opened under C2 session/graph authority
```

BF4A must fail closed on that mismatch.

### 4.1 Product guard

When Play has a known `productCampaignId` and the selected Runbook has a
different `campaign_id`, `Edit Runbook` must not open the Runbook as though the
current context were compatible.

Preferred behavior:

```text
Edit Runbook disabled
→ visible reason identifies campaign mismatch
```

Starting/opening a Run is a separate Play capability and is not changed merely
to make this edit guard convenient.

### 4.2 Plan exact-admission guard

Defense in depth is mandatory. A direct URL must not bypass the product guard.

For an exact requested document that resolves to `kind=runbook`:

```text
record.campaign_id == planView.campaign_id
  → Runbook may be admitted to authoring

record.campaign_id != planView.campaign_id
  → truthful load/admission error
  → no durable Runbook Canvas/Agent authority is published
  → blank-shell/error-shell chrome remains available per PR #661
```

Do not silently rewrite `planView.campaign_id`.
Do not switch World Graph focus as a side effect of opening a Runbook.
Do not invent cross-campaign publication semantics.

Preserve existing exact `kind=plan` behavior unless a separate proven defect is
encountered. This PR needs only the Runbook-specific guard.

### 4.3 Unknown product campaign

If Play has no product campaign context, the edit action may navigate using the
exact selected UUID, but Plan's exact-admission guard remains authoritative.
A mismatch must still fail closed rather than borrowing the requested
Runbook's campaign automatically.

---

## §5 Representative BF4A/BF3B Runbook material

This material is deliberately small. It exists to prove the ordinary authoring
path and then become BF3B's Decision/relevance dogfood input.

It is **not** a production fixture, automatic seed, migration payload, sample
campaign, or new canonical content object.

The exact IDs below are intentionally stable for the witness.

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

### 5.1 Structural expectations

After parse/index/Save/reload:

```text
Runbook

beat:hold-breach [spine]
  scene:north-gate
  choice:surviving-brood [associated with scene:north-gate]
    option:follow-brood
      activates scene:tunnel-pursuit
      activates beat:lower-tunnels
    option:seal-breach
      suppresses scene:tunnel-pursuit
  scene:tunnel-pursuit

beat:lower-tunnels [optional]
```

### 5.2 Grammar laws the witness must prove

- v2 Beat = H2.
- v2 Scene and Decision/wire `choice` = H3 Beat-owned siblings.
- Option = marked list item, **not a heading**.
- Option marker immediately precedes its list item.
- Choice prose and Option body remain disjoint after round-trip.
- `scene=scene:north-gate` is the Decision's same-Beat Scene association.
- `activates` / `suppresses` target exact existing Beat/Scene IDs.
- Future targets are legal.
- Activation/suppression are authored relevance intent, not navigation gates.
- No parser/serializer weakening is permitted to make this sample pass.

If this exact material is rejected by current BF1 grammar, first determine
whether the handoff sample is wrong. Correct the sample; do not casually alter
BF1.

---

## §6 Save and revision contract

### 6.1 Kind-aware Save law

BF4A changes only this product rule:

```text
kind == plan
  → retain existing Plan save eligibility/path rules

kind == runbook
  → target_relpath may be null
  → ordinary Save is allowed
```

Do not globally remove the path guard.
Do not fabricate a target path.

### 6.2 Existing authoring authority remains owner

Runbook Save uses the existing shared pipeline:

```text
exact WorkspaceDocument snapshot
→ TipTap working state
→ prepare
→ commit
→ immutable WorkRevision
→ refreshed exact WorkspaceDocument/committed snapshot
```

Do not create a Runbook-specific writer, endpoint, database table, or raw SQL
path.

### 6.3 Revision identity

Given:

```text
WorkObject W
current committed WorkRevision N
```

After Save:

```text
WorkObject W           unchanged
WorkRevision N         immutable and still loadable
WorkRevision N+1       newly committed
current head           N+1
```

The editor must reload the newly committed bytes for W without minting W2.

---

## §7 Existing Run isolation

This is mandatory acceptance, not a regression footnote.

Given Run R already pins W revision N:

```text
R.playable_artifact_id = W
R.playable_revision    = N
R.playable_content_sha = sha(N)
```

Then Save W revision N+1.

Required:

```text
R still pins W / N / sha(N)
R sealed manifest unchanged
R progress unchanged
R current Beat/Scene unchanged
R still loads exact historical N bytes
```

Only a new explicit Start Run may bind N+1.

No BF4A code may call rebase or imitate rebase behavior.

---

## §8 Write lease

Re-check exact current `main` and all active PR leases before editing.

### 8.1 Create / replace handoff

- `Docs/Plans/HANDOFF-PLAY-SURFACE-runbook-authoring-gateway.md`

### 8.2 Play chooser

Modify:

- `apps/live-control-ui/src/playSurface/StartRunPanel.tsx`
- `apps/live-control-ui/src/playSurface/StartRunPanel.test.tsx`

Allowed bounded helper if useful:

- one small pure navigation/campaign-admission helper under
  `apps/live-control-ui/src/playSurface/`
- focused test for that helper.

`apps/live-control-ui/src/playSurface/playSurface.css` may change only if the
new action/disabled reason requires bounded presentation.

### 8.3 Plan exact Runbook admission + Save

Modify:

- `apps/live-control-ui/src/planSurface/components/PlanSurfaceCanvas.tsx`
- `apps/live-control-ui/src/planSurface/config/planSessionDescriptor.ts`
- the corresponding existing focused tests, including
  `PlanSurfaceShell.test.tsx` when integration coverage is required.

Preferred bounded new test:

- `apps/live-control-ui/src/planSurface/PlanSurfaceRunbookAuthoring.test.tsx`

Do not redesign the default Plan selector.

### 8.4 App integration

Modify `apps/live-control-ui/src/App.test.tsx` only if owning-component tests
cannot prove the route/integration contract.

### 8.5 Predecessor/state cleanup in the implementation PR

The implementation PR may update:

- `Docs/Plans/HANDOFF-PLAN-SURFACE-blank-authoring-shell.md`
- `Docs/Roadmaps/ROADMAP-con-ready.md`
- `Docs/Sources/design-agent/ACTIVE_AUTHORITY/ROADMAP-con-ready.md`
- `Docs/Plans/STEWARDS-ANCHOR-con-ready.md`
- `Docs/Sources/design-agent/ACTIVE_AUTHORITY/STEWARDS-ANCHOR-con-ready.md`

Record PR #661 as merged at `770f79cca4aa3c12aa8a35db2db77ce376f2ff9e`
with 4 formal review cycles. BF4A later merged as PR #660 at
`a3fd6219062d1cd978c394d07e2f80aaa6d203eb` (accepted head
`d9b34ca87166572af8b482523862722fdd928fbe`, 2 review cycles).

The old branch-local note
`Docs/Plans/NOTE-PLAY-SURFACE-authoring-blank-shell-design-correction.md` may be
deleted or marked historical/resolved so it does not continue to claim an open
design decision already resolved by #661.

### 8.6 Explicitly unleased

- `Backlog.md` — old #660 changes here must be absent from the rebased diff.
- BF1 parser/grammar/serializer production files.
- Play Run schema/progress semantics.
- APP-STATE migrations/repositories.
- workspace-document backend APIs.
- TipTap prepare/commit backend APIs.
- default Plan selector mixed-kind behavior.
- global EditHost / ToolHost semantics.
- blank-shell local promotion state machine.
- BF3B current-moment Decision files.
- Agent Interaction.
- World Graph / CUTOVER.
- Combat.

If the rebase shows another active lane owns one of §8.2–§8.5 paths, stop and
resolve the lease before editing.

---

## §9 Error and concurrency posture

Reuse existing exact-document and authoring failure states.

Required:

```text
Runbook load failure
→ truthful Plan load/error shell
→ no fabricated document

campaign mismatch
→ fail closed
→ no Runbook durable authority publication

prepare/commit conflict
→ existing authoring conflict/recovery posture
→ no duplicate WorkObject

unknown outcome
→ exact authoritative reread/reconciliation
→ no blind replay that creates a new Runbook
```

The blank Plan first-save promotion controller is not involved when editing an
already committed Runbook. Do not route Runbook revision Save through local
blank promotion merely because Plan now owns that state machine.

---

## §10 Verification contract

### 10.1 Play chooser tests

Prove:

- no selected Runbook → Edit disabled/absent;
- selecting a Runbook binds Edit to that exact UUID;
- list reorder/refresh cannot retarget Edit;
- Create blank Runbook → committed Runbook remains selected → Edit available;
- Edit does not create a Run or seal a manifest;
- known product campaign mismatch → Edit cannot silently open the Runbook;
- Start exact Run behavior remains unchanged.

### 10.2 Plan exact-admission tests

Prove:

- exact same-campaign `kind=runbook` resolves normally;
- exact cross-campaign Runbook fails closed;
- failure publishes no durable Runbook document identity;
- Edit/Tools chrome remains present through the #661 error-shell contract;
- exact Plan behavior is unchanged by the Runbook-specific guard.

### 10.3 Runbook authoring tests

Prove:

- pathless Runbook Save is enabled once editing is unlocked and document is
  otherwise saveable;
- pathless Plan remains governed by existing Plan law;
- path-backed Plan remains unchanged;
- Save calls the existing prepare/commit authority;
- same WorkObject UUID survives Save;
- immutable revision number advances;
- committed/reloaded Markdown matches the edited material;
- Runbook `kind` remains `runbook`;
- no filesystem path is fabricated.

### 10.4 Canonical v2 round-trip test

Use the §5 material or byte-equivalent canonical material to prove:

```text
Markdown
→ TipTap admission
→ ordinary edit/save serialization
→ committed reload
→ v2 structure index
```

Assert at minimum:

- `beat:hold-breach` spine;
- `scene:north-gate` parent Beat;
- `choice:surviving-brood` Scene association;
- exactly two Options;
- Choice prose excludes Option consequence bodies;
- Option bodies remain attached to the correct Option;
- follow Option activates `scene:tunnel-pursuit` and `beat:lower-tunnels`;
- seal Option suppresses `scene:tunnel-pursuit`;
- `scene:tunnel-pursuit` and `beat:lower-tunnels` exist as exact targets;
- Option remains a list item after reload.

Use the existing parser/indexer assertion boundary. Do not duplicate grammar in
a BF4A-only parser.

### 10.5 Historical Run isolation test

Prove:

```text
commit W rev N
→ Start Run R pinned to N
→ edit/save W rev N+1
→ reopen R
→ R still resolves N bytes/digest/manifest/progress
→ new explicit Start Run resolves N+1
```

### 10.6 Backend regressions

At minimum rerun the existing tests owning:

- blank Runbook create/start path;
- historical Runbook revision binding;
- Play Run progress/manifest integrity if touched indirectly.

No backend production change is expected.

### 10.7 Build/static

Required:

```text
pnpm --dir apps/live-control-ui run build
git diff --check
```

Canonical/mirror roadmap + steward pairs must remain byte-identical.

---

## §11 Mandatory real browser dogfood

Automated fixtures are not sufficient. This slice exists because hidden exact
routes and fixture-authored material previously produced false confidence.

Use ordinary Chrome/browser UI against normal servers and a disposable or
operator-approved PostgreSQL application-state database.

### Witness A — blank Runbook → real authored v2 revision → new Run

1. Re-anchor to the exact reviewed head and start normal backend/frontend.
2. Open Play chooser under the same campaign Plan will admit.
3. Create a blank Runbook through the existing product action.
4. Record its exact WorkObject UUID and committed revision N.
5. Confirm no Run was auto-created.
6. Click `Edit Runbook`; do not copy/paste a UUID into the URL manually.
7. Confirm Plan opens the same Runbook with Edit/Tools chrome and truthful
   Runbook identity.
8. Unlock editing through ordinary UI.
9. Replace/edit the minimal blank material with the canonical §5 Runbook.
10. Save through ordinary UI.
11. Confirm `target_relpath` remains null.
12. Confirm the WorkObject UUID is unchanged and committed revision is N+1.
13. Hard reload `/plan?documentId=<same UUID>`.
14. Confirm the authored Beat/Scene/Decision/Options/consequences survive.
15. Navigate to Play through ordinary AppChrome.
16. Select the same Runbook and Start exact Run.
17. Confirm the Run binds N+1 and reaches native v2 READY.
18. Confirm current Beat is `Hold the Breach`; a current Scene is not fabricated
    merely by admission.
19. Confirm `North Gate` and `Tunnel Pursuit` are visible as real authored
    Scenes through the existing BF3A projection.
20. Optionally Make `North Gate` Current to prove the authored Scene is usable;
    do not require BF3B Decision controls yet.

Stop the witness there. BF3B owns selecting `Follow it` / `Seal the breach` and
showing relevance changes.

### Witness B — historical Run isolation

1. Before editing, or with another equivalent Runbook, Start Run R from revision
   N.
2. Record R's exact revision/digest/current moment.
3. Edit the same Runbook and Save N+1 through BF4A.
4. Reopen R.
5. Confirm R still renders N and its Runtime current moment is unchanged.
6. Start a new Run and confirm the new Run binds N+1.

### Witness C — campaign mismatch

Using ordinary UI or an explicit adversarial exact URL:

```text
Runbook campaign != PlanView campaign
```

must produce truthful refusal without publishing the mismatched Runbook as the
authoritative Plan document. Edit/Tools shell chrome must remain recoverable.

### Forbidden witness shortcuts

Do not claim success using:

- direct SQL edits;
- direct APP-STATE row mutation;
- pytest-created dogfood content;
- fake bootstrap content;
- hidden Runbook seed;
- hand-authored UUID-only route as the primary success path;
- browser devtools mutation of application state.

The Runbook body may be pasted as canonical Markdown in the ordinary editor.
Structure-aware insertion controls are explicitly deferred to BF4.

---

## §12 Stop conditions

Stop and report rather than widen BF4A if implementation requires:

- WorkObject/WorkRevision schema changes;
- new APP-STATE migration;
- new backend persistence or endpoint;
- BF1 grammar/parser/serializer semantic change;
- fake target path creation;
- globally enabling pathless Plans;
- global EditHost/ToolHost redesign;
- blank-shell state-machine redesign;
- automatic Run start/rebase/adoption;
- mixed Plan/Runbook selector redesign;
- structure-aware Playable controls;
- BF3B Decision Runtime behavior;
- World/Agent/Combat changes;
- changing PlanView/World campaign focus as a side effect of opening Runbook;
- a campaign-authority problem that cannot be solved with the bounded
  Runbook-specific admission guard above;
- active write-lease collision.

---

## §13 Acceptance checklist

- [ ] implementation branch rebased onto `main` containing PR #661 merge
      `770f79cca4aa3c12aa8a35db2db77ce376f2ff9e` or later;
- [ ] this re-anchored handoff is present before further implementation;
- [ ] stale #660 out-of-lease `Backlog.md` diff is gone;
- [ ] `Create blank Runbook → Edit Runbook` requires no Run and no UUID copying;
- [ ] exact selected WorkObject identity drives navigation;
- [ ] truthful Runbook title/kind shown in Plan;
- [ ] same-campaign exact Runbook is admitted;
- [ ] cross-campaign exact Runbook fails closed;
- [ ] pathless Runbook Save works;
- [ ] pathless Plan law remains unchanged;
- [ ] no fake filesystem path;
- [ ] same WorkObject, next immutable WorkRevision;
- [ ] old WorkRevision remains loadable;
- [ ] old Run remains pinned to old revision;
- [ ] new explicit Run binds new revision;
- [ ] §5 Decision-bearing v2 material survives edit → Save → reload;
- [ ] Option list-item structure survives;
- [ ] Choice prose / Option consequence bodies remain disjoint;
- [ ] activates/suppresses edges survive exactly;
- [ ] no BF3B runtime selection implementation;
- [ ] no BF4 structure-aware authoring controls;
- [ ] no backend/schema/migration changes;
- [ ] real browser Witness A complete;
- [ ] real browser Witness B complete;
- [ ] campaign mismatch witness/proof complete;
- [ ] focused frontend tests pass;
- [ ] owning backend regressions pass;
- [ ] frontend build passes;
- [ ] `git diff --check` clean;
- [ ] roadmap/steward mirrors byte-identical;
- [ ] predecessor state sync records #661 merge + 4 formal review cycles;
- [ ] PR stays draft until all mandatory browser evidence is recorded against
      the exact review head.

---

## §14 Successor

After BF4A merges:

```text
re-anchor BF3B on the BF4A merge SHA
→ use this exact committed Runbook as the ordinary dogfood input
→ North Gate current
→ Decision visible
→ select Follow it
→ consequence visible
→ Tunnel Pursuit + Lower Tunnels emphasized
→ change to Seal the breach
→ Tunnel Pursuit de-emphasized
→ clear selection
→ default relevance restored
→ reload exact Run
→ selection and derived relevance resume truthfully
```

BF4 later replaces canonical-Markdown-only authoring with structure-aware
Beat/Scene/Decision/Option controls. That is not a prerequisite for BF3B.

The architectural/product checkpoint remains:

> **Before we build richer table interaction around authored material, the GM
> must be able to author that material through the ordinary product path.**
