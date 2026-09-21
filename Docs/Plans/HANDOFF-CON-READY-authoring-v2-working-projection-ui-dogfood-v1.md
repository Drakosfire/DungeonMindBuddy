# HANDOFF — CON-READY: Authoring v2 working projection UI dogfood

**Created:** 2026-09-20
**Status:** DONE — MERGED as PR #741 @ `28754d1fdda15be97475f35e08127833b088a256`; accepted implementation head `9b5874e9b30663d4008427acebdff03d7c6531ae`; Review Cycle 3 PASS / MERGE-READY (`5262735475`)
**Canonical handoff path:** `Docs/Plans/HANDOFF-CON-READY-authoring-v2-working-projection-ui-dogfood-v1.md`
**Conversation/workstream:** `CON-READY / DOGFOOD-CONTINUITY / campaign memory authoring`
**Flow / owner:** `CON-READY`
**Direction:** DESIGN → CODE → DOGFOOD → CLEANUP → REVIEW
**Design authority base:** `main@b9067303b6f88acf51429c2dfc331e3f2a48bd35` — V2-1 / PR #738 merged
**Activation gate:** `none — #738 merged and operator dogfood supplied successor direction`
**Dispatch base rule:** fresh current `main` containing this checked-in handoff; record the exact implementation branch base at dispatch/review.
**PR topology:** `serial` within CON-READY
**PR authorization:** open/update exactly this one assigned UI dogfood PR without asking; no successor/repair PRs.
**PR title:** `CON-READY: make recap authoring a live working surface`
**Proposed branch:** `con-ready/authoring-v2-working-projection-ui-dogfood-v1`

> Repository law: `AGENTS.md`. Steward process: `Docs/Process/STEWARD-CYCLE.md`. Parent sequencing authority: `Docs/Plans/PLAN-CON-READY-authoring-v2-derived-gold-ablation-loop-v1.md`.

---

## §1 Mission and merge-ready invariant

### Mission

Turn the ordinary published recap into a **continuous graph-authoring workspace** where the GM can:

1. read the recap Markdown;
2. highlight prose or choose an existing graph object;
3. author through the existing **Author Node** tool rather than an inline form below the document;
4. keep the source Markdown visible while authoring;
5. immediately see local human adjudications reflected in the current projection;
6. inspect graph objects with useful root prose and progressively expand connected-object prose without losing the root object or recap context.

This PR exists specifically to make the current human-authoring loop usable enough for sustained dogfood.

### Merge-ready invariant

**The GM always remains oriented to the same source and working projection. Authoring occurs beside the recap, local adjudications immediately change the visible local projection, and graph exploration progressively reveals useful prose without navigating away from the source/root context. No UI improvement in this slice may silently acquire durable World-write authority or mutate the canonical recap source.**

The central loop is:

```text
read recap
→ notice semantic problem
→ highlight phrase / choose existing object
→ Author Node opens beside the recap
→ bind / create / edit / relate
→ stage local adjudication
→ current working projection visibly changes
→ continue reading
→ inspect a pill
→ see useful root prose
→ expand connected object for its prose
→ continue authoring
```

### Pre-dispatch critique

| Question                            | Answer                                                                                                                                                                                               |
| ----------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Can one invariant govern the slice? | Yes. Every core change serves continuous source-oriented graph authoring and inspection.                                                                                                             |
| Most likely failure                 | Authoring technically stages a proposal but leaves the recap unchanged, forcing the operator to remember invisible state or leave the source to inspect it.                                          |
| Second likely failure               | Opening Author Node replaces/hides the recap, recreating the same context-loss problem in a different component.                                                                                     |
| Third likely failure                | Connected-object exploration replaces the root object rather than expanding context, so the operator loses what relationship they were inspecting.                                                   |
| Easiest boundary to under-test      | Proposal → visible working-projection derivation, especially after remove/reload/scope switch.                                                                                                       |
| PR topology                         | Serial CON-READY UI successor. V2-2 durable commit remains held.                                                                                                                                     |
| Fact that forces stop/split         | Backend/API contract change, durable World mutation, canonical recap mutation, new persistence contract, or inability to represent the working projection from existing local proposal/source state. |

---

## §2 Context, authority, and sequencing

### Predecessor

PR #738 / V2-1 established:

```text
published recap
→ source-grounded local object / link-existing / relationship proposal
→ sessionStorage persistence scoped by campaign/session
→ no prepare/commit
→ no World mutation
```

Accepted V2-1 authority rules continue to apply:

```text
PublishedMemoryBrowseContext != GraphReviewWriteAuthority
source-contextualized local proposal != canonical World contribution
```

### Why this slice comes before V2-2

V2-1 proved that local human proposals can exist truthfully.

Dogfood proved that this is not yet a usable authoring loop.

The UI currently allows the GM to express a correction, but does not provide the immediate visual feedback necessary to work through a real recap. Moving directly into governed World commit would make us durable-write a workflow whose interaction model is still awkward to operate.

Therefore sequencing becomes:

```text
V2-1 local proposal                     MERGED
→ V2-1A working-projection UI dogfood   THIS PR
→ V2-2 governed World commit            HELD
→ V2-3 derived gold
→ V2-4 extraction/model ablation
→ V2-5 Agent assistance
```

### What remains false after this PR

This PR does **not** make local authoring durable World truth.

Still false:

* no `/graph-authoring/prepare`;
* no `/graph-authoring/commit`;
* no immutable World revision from this ordinary browse workflow;
* no canonical source-span invention;
* no Agent authoring;
* no extraction change;
* no derived-gold export;
* no automatic duplicate merge.

V2-2 remains separately governed.

### Lane, topology, and state-authority sync

| Field | Current truth |
|---|---|
| PR topology | `serial` within CON-READY |
| Implementation lane | `con-ready/authoring-v2-working-projection-ui-dogfood-v1` from `main@b9067303b6f88acf51429c2dfc331e3f2a48bd35` |
| Authorized PR | PR #741 only; no successor or repair PR while this PR is open |
| State-authority sync set after merge | This handoff, the CON-READY PLAN, both byte-identical STEWARDS anchors, and the dogfood report |
| Named successor | V2-2 governed World commit remains held behind this slice |

---

### Operator findings that define this slice

### A. Author Node is the right tool, but the workflow is in the wrong place

Current observed behavior:

```text
highlight source phrase
→ click Author graph object
→ authoring state opens
→ form exists below the recap on the same page
→ operator must leave/scroll away from the text being adjudicated
```

Meanwhile the product already has:

```text
GraphReviewAuthorNodeHost
→ GraphReviewAuthorNodeDrawer
→ GraphReviewAuthorNodePanel
→ Author Node
```

The existing Author Node UI must become the home for published-recap local authoring.

Do not invent another authoring surface.

Required behavior:

```text
highlight "Mirathorn"
→ Author graph object
→ existing Author Node tool opens
→ selected phrase/context already loaded
→ recap remains visible and readable
→ authoring controls are usable beside it
```

For published recap authoring, opening Author Node **must not hide the main recap projection**.

Exact-run behavior may retain different presentation semantics where justified.

The current `liveRun` requirement in `GraphReviewAuthorNodePanel` must not be treated as proof that the drawer itself requires write authority. Published local staging has truthful source context without `GraphReviewWriteAuthority`.

### B. Local authoring must visibly change the current projection

Observed dogfood:

```text
highlight "Mirathorn"
→ choose existing Mirathorn
→ stage alias/link
→ proposal exists
→ recap still shows ordinary text "Mirathorn"
```

That is not sufficient for sustained dogfood.

The current recap must become a **working authored projection**:

```text
canonical recap source
+ current campaign/session local proposals
= visible working projection
```

The canonical recap Markdown remains immutable.

The World remains unchanged.

The rendered working projection changes immediately.

Minimum required behavior:

#### `link_existing`

If a highlighted source occurrence is bound to an existing node:

```text
"Mirathorn"
→ stage local link_existing/reference
→ that exact occurrence immediately renders as a graph pill
→ pill targets the exact existing node identity
```

Removing the proposal removes the local pill.

Reloading/revisiting the same campaign/session reconstructs the same local projection from persisted proposals.

#### `object`

If highlighted source becomes a locally proposed new object:

```text
selected text
→ stage local object
→ selected occurrence visibly becomes an authored/local graph reference
```

The UI must make clear that the object is local/uncommitted.

Clicking it must not pretend that a durable World node already exists.

A local proposal identity may be used for working-projection UI, but it must not masquerade as a World node ID.

#### `relationship`

A locally staged relationship should become visible when inspecting the relevant working object(s), rather than living only in the staging tray.

It remains visibly local/uncommitted.

#### proposal removal

```text
remove local proposal
→ corresponding working-projection effect disappears
```

### C. Identity is not always alias

Existing-object resolution is useful and should remain.

But:

```text
selected text == existing node primary label
```

is normally:

```text
this is that object
```

not:

```text
add the same string as an alias
```

During this UI tuning slice, improve the decision vocabulary where practical:

```text
exact primary-label match
→ Use existing node / Link to this node

different string resolving to known node
→ Add as alias

no appropriate node
→ Create new
```

Do not solve duplicate identity/merge here.

If two same-name nodes exist, present truthful ambiguity. Do not choose a winner by inventing an alias rule.

### D. Object prose cleanup went too far

Current graph-object exploration can present identity and relationships with little or no useful root prose.

The root object needs human-readable context again.

Required posture:

```text
opened object
→ identity
→ useful root prose visible by default
→ relationships
→ source/technical material progressively disclosed
```

Use truthful prose already available from the loaded projection/complete-object authority.

Preferred source order should be based on existing authoritative fields such as a real summary/game summary and existing complete-object/source material.

Do not generate new prose.

Do not turn technical provenance into fake narrative prose.

If no truthful prose exists, represent that honestly rather than synthesizing copy.

### E. Connected objects should expand instead of replacing the root

Current recap behavior can treat a relationship click like navigation:

```text
root object A
→ click related B
→ active object becomes B
→ root A disappears
```

For this dogfood workflow, preserve the relationship context.

Required interaction:

```text
root object A
  prose for A
  relationships
    relationship to B
      click
      → expand B beneath/within this relationship
          useful prose for B
          compact identity
          relevant context
```

Clicking again may collapse it.

At least one connected object must be expandable without replacing the root.

A separate explicit “open as root” action may remain or be added if useful, but expansion is the default dogfood interaction.

Keep this bounded. This PR does not need an infinitely recursive graph tree.

One-hop progressive expansion is sufficient to prove the interaction.

---

## §6 Implementation contract — working projection

The local working projection is presentation state derived from already-authorized V2-1 state.

```text
Input:
  canonical recap Markdown
  exact campaign/session/graph context
  canonical projected nodeViews
  local GraphObjectAuthoringProposal[] for that scope

Output:
  read-only visible working projection
  containing canonical graph references
  plus truthful local authoring overlays
```

Rules:

1. Do not mutate canonical recap Markdown.
2. Do not write authored markup back to the recap artifact.
3. Do not invent canonical evidence spans.
4. Do not create fake durable World IDs.
5. Existing-node pills resolve by exact existing node identity.
6. Local-object references remain visibly local.
7. Scope remains campaign + session isolated.
8. Rehydrated local proposals reproduce the local projection.
9. Removing a proposal reverses its visual overlay.
10. Local projection state is allowed to be richer than the canonical published projection but must never be presented as committed World truth.

### Selection stability

V2-1 Tiptap offsets / paragraph ordinal / surrounding text are interaction context, not canonical evidence.

They may be used to reconstruct the working projection.

If replay cannot uniquely and safely identify the selected source occurrence, fail visibly/local-only rather than applying a proposal to the wrong occurrence.

---

### Author Node composition contract

Published recap authoring needs a dedicated presentation mode distinct from exact-run write authority.

Conceptually:

```text
Author Node
├── exact-run mode
│   └── existing exact-run authoring behavior
│
└── published-local mode
    ├── source = current published recap
    ├── authority = local staging only
    ├── selected source text / existing node preseeded
    ├── no prepare/commit
    └── recap remains visible
```

The implementation does not have to use these exact names.

What matters is that UI presentation and write authority are no longer conflated.

The published-local mode may reuse `GraphObjectAuthoringSurface` and `useGraphObjectAuthoringDraft`.

Avoid duplicating the whole authoring workflow into a second implementation.

### Layout

This is deliberately dogfood-driven.

Acceptable directions include:

* docked left tool;
* persistent drawer;
* resizable side panel;
* another existing Author Node/tool-host composition.

Required:

* recap remains simultaneously visible;
* user can scroll/read source while tool remains available;
* opening the authoring workflow visibly changes the interface;
* source selection remains understandable in the tool;
* closing the tool returns cleanly to reading;
* do not force the user to scroll below the entire recap to find the form.

---

## §4 Files in scope — UI write lease

Expected production, test, and state-authority paths:

| Action           | Path                                                                                                  | Purpose                                                                       |
| ---------------- | ----------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------- |
| Create / Modify | `Docs/Plans/HANDOFF-CON-READY-authoring-v2-working-projection-ui-dogfood-v1.md` | canonical handoff, §4 lease, §7 evidence, and review handback |
| Modify | `Docs/Plans/PLAN-CON-READY-authoring-v2-derived-gold-ablation-loop-v1.md` | backward-looking V2-1 predecessor and V2-1A sequencing sync |
| Modify | `Docs/Plans/STEWARDS-ANCHOR-con-ready.md` | active PR #741 anchor without marking V2-1A complete |
| Create | `Docs/Reports/REPORT-CON-READY-authoring-v2-working-projection-ui-dogfood-v1.md` | durable dogfood design and flow learnings |
| Modify | `Docs/Sources/design-agent/ACTIVE_AUTHORITY/STEWARDS-ANCHOR-con-ready.md` | byte-identical design-agent authority anchor |
| Modify | `apps/live-control-ui/src/planSurface/graphPreview/WorldGraphRecapProjection.tsx` | local-object state and non-destructive related-object expansion |
| Modify | `apps/live-control-ui/src/planSurface/graphPreview/WorldGraphRecapProjection.test.tsx` | root prose, local state, and failed expansion evidence |
| Modify | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewWorkbenchModule.tsx` | connect published recap local-authoring state to existing Author Node host |
| Modify | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewWorkbenchModule.test.tsx` | module integration coverage |
| Modify | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewAuthorNodeHost.tsx` | allow published-local Author Node without hiding source projection |
| Modify | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewAuthorNodeDrawer.tsx` | published-local presentation, expansion, and scroll behavior |
| Modify | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewAuthorNodePanel.tsx` | separate drawer usefulness from exact-run write authority |
| Modify | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewAuthorDraftWorkspace.test.tsx` | local-authoring workspace regression coverage |
| Modify | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/PublishedRecapLocalAuthoring.tsx` | compose the recap-side Author Node workflow and context tabs |
| Modify | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/PublishedRecapLocalAuthoring.test.tsx` | published-local wizard, persistence, identity, and alias-copy coverage |
| Modify | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphObjectAuthoringSurface.tsx` | side-tool/local-working-projection presentation |
| Modify | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphObjectAuthoringSurface.test.tsx` | authoring surface regression coverage |
| Modify | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphObjectAuthoringBindExistingPanel.tsx` | identity vs alias decision vocabulary and duplicate suggestion |
| Modify | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphObjectAuthoringObjectRefPicker.tsx` | scoped fuzzy object search and anchored result list |
| Create | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphObjectAuthoringPublishedWizard.tsx` | linear local authoring workflow |
| Modify | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphObjectAuthoringRelationshipForm.tsx` | relationship guidance and target selection |
| Modify | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphObjectAuthoringRelationshipForm.test.tsx` | relationship search and guidance coverage |
| Modify | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphObjectAuthoringSelectedSource.tsx` | compact selected-source context |
| Modify | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/graphExistingObjectIdentityWorkbench.ts` | existing-node identity mapping |
| Modify | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/graphObjectAuthoringDraft.ts` | local proposal and reference semantics |
| Create | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/graphObjectAuthoringSearch.ts` | reusable fuzzy search helper |
| Create | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/graphObjectAuthoringSearch.test.ts` | fuzzy search helper coverage |
| Create | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/publishedRecapWorkingProjection.ts` | pure local working-projection derivation |
| Create | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/publishedRecapWorkingProjection.test.ts` | overlay, reversal, persistence-shape, and scope coverage |
| Modify | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/useGraphObjectAuthoringDraft.ts` | campaign/session-scoped local proposal persistence |
| Modify | `apps/live-control-ui/src/planSurface/planSurface.css` | recap + Author Node working layout and progressive expansion |

Focused tests adjacent to these components are authorized and expected.

### Deliberate dogfood tuning allowance

This PR is intentionally less rigid than V2-1.

The operator and code agent are expected to discover interaction problems while using the branch.

Bounded discovery:

```text
Directories:
  apps/live-control-ui/src/planSurface/graphReviewWorkbench/
  apps/live-control-ui/src/planSurface/graphPreview/
  apps/live-control-ui/src/planSurface/graphProjectionReader/
  apps/live-control-ui/src/graphObjectCard/
  apps/live-control-ui/src/surfaceInteraction/contextHost/

Maximum additional paths:
  10

Allowed:
  frontend UI components
  focused UI helpers
  CSS
  component/integration tests
  small Surface Context contribution needed to support this workflow

Decision rule:
  the change must improve or prove the §1 continuous authoring/inspection loop
  and must not introduce a new backend/durable contract.
```

This explicitly permits small layout, focus, copy, scroll, affordance, and progressive-disclosure adjustments discovered during dogfood.

### Ad hoc implementation is allowed; ad hoc final diff is not

The code agent may experiment aggressively on the branch.

Intermediate commits may contain:

* layout experiments;
* temporary component movement;
* provisional copy;
* instrumentation;
* competing approaches;
* CSS tuning.

Before review, perform a cleanup pass.

The cumulative PR must not contain:

* abandoned components;
* dead feature flags;
* duplicate authoring implementations;
* debug controls/logging;
* test-only production attributes without product value;
* stale copy from discarded interactions;
* unused CSS;
* commented-out experiments;
* unnecessary compatibility wrappers created only during exploration.

**Review the final cumulative diff as a product implementation, not as a diary of the experimentation required to reach it.**

---

## §5 Explicitly out of scope / collision boundary

Do not modify or claim:

* `apps/live_control_server/routes/graph_authoring.py`
* `apps/live_control_server/services/graph_object_authoring_prepare.py`
* `apps/live_control_server/services/graph_object_authoring_commit.py`
* DungeonMind World publication
* extraction/model/prompt paths
* derived-gold export
* merge-object semantics
* automatic identity reconciliation
* canonical recap source files
* new Buddy-owned durable graph/overlay storage

Do not make published browse acquire `ExplicitAuthoringAuthority`.

Do not invoke prepare/commit merely to make UI feedback visible.

Immediate projection feedback is a **local working overlay**, not a shortcut durable write.

---

## §3 Observable paths and adversarial sequences

| Sequence                                        | Required outcome                                                         |
| ----------------------------------------------- | ------------------------------------------------------------------------ |
| highlight phrase → Author graph                 | existing Author Node tool opens with source seeded; recap stays visible  |
| close/reopen Author Node                        | recap position/context remains usable; local draft remains truthful      |
| highlight Mirathorn → choose existing Mirathorn | exact occurrence becomes existing-node pill in working projection        |
| selected text exactly equals node primary label | UI presents identity/reference semantics, not mandatory alias semantics  |
| stage true alias                                | selected occurrence becomes pill targeting exact existing node           |
| stage new object                                | occurrence visibly becomes local authored reference; clearly uncommitted |
| stage relationship                              | relationship visible in local object inspection                          |
| remove proposal                                 | corresponding projection overlay disappears                              |
| reload same campaign/session                    | persisted proposals reconstruct working projection                       |
| switch campaign/session                         | overlays do not leak                                                     |
| return to original scope                        | original local working projection restores                               |
| click root pill                                 | root identity + useful prose visible                                     |
| click relationship target                       | target prose expands while root remains visible                          |
| collapse target                                 | returns to root relationship view without navigation loss                |
| unavailable target                              | root remains intact; failure is localized to expansion                   |
| no truthful root prose                          | honest empty/thin state; no synthesized narrative                        |
| any local authoring action                      | zero prepare/commit/World mutation                                       |

---

## §7 Evidence required to merge

### Automated proof

At minimum cover:

1. highlight → Author Node published-local mode;
2. opening Author Node does not remove the recap;
3. staged `link_existing` changes the visible working projection into a pill;
4. proposal removal reverses the pill;
5. persisted proposal rehydrates the pill on remount;
6. campaign/session scope isolation still holds;
7. local object proposal has visible uncommitted projection representation;
8. local relationship appears in working object inspection;
9. published-local Author Node renders no prepare/commit;
10. exact-run Author Node behavior has not accidentally lost its existing authority semantics;
11. root graph-object prose is visible when authoritative prose exists;
12. relationship click expands related object without replacing root;
13. failed related-object expansion leaves root intact.

Run the focused test suite covering all modified owners.

Also:

```bash
pnpm --dir apps/live-control-ui exec vitest run src/planSurface/graphReviewWorkbench/PublishedRecapLocalAuthoring.test.tsx src/planSurface/graphReviewWorkbench/GraphObjectAuthoringSurface.test.tsx src/planSurface/graphPreview/WorldGraphRecapProjection.test.tsx src/graphObjectCard/GraphObjectCard.test.tsx
pnpm --dir apps/live-control-ui typecheck
pnpm --dir apps/live-control-ui build
git diff --check
git diff --name-only b9067303b6f88acf51429c2dfc331e3f2a48bd35...HEAD
```

If the known baseline TypeScript failure still exists, compare exact base/head output and demonstrate this PR introduces no additional failure.

### Required live dogfood

Automated tests are not sufficient for this slice.

Use a real Campaign 1 or Campaign 2 recap.

Minimum scenario:

```text
1. Open /ingest published recap.
2. Find ordinary prose that should reference an existing node.
3. Highlight it.
4. Click Author graph.
5. Confirm Author Node opens while recap stays visible.
6. Bind/use the existing object.
7. Confirm that occurrence becomes a pill immediately.
8. Continue reading without reload.
9. Create or enrich one additional local object.
10. Inspect a graph pill.
11. Confirm useful root prose is visible.
12. Expand one connected object.
13. Confirm connected-object prose appears without losing the root.
14. Remove at least one staged proposal and confirm its projection effect reverses.
15. Reload and verify remaining local adjudications reconstruct.
```

Record friction discovered during dogfood.

Small UI fixes discovered here are authorized under §4.

If dogfood uncovers a **different product contract**, record it for successor work rather than swallowing it.

---

### UI quality bar

This is a dogfood PR, but “dogfood” does not mean temporary-quality UI.

Before review ask:

* Can I author while continuously reading the source?
* Does clicking Author graph cause an obvious, useful interface transition?
* Do I immediately see what my adjudication changed?
* Can I tell local/uncommitted memory from durable World memory?
* Can I undo/remove a local adjudication and see the projection revert?
* Does object inspection answer “what is this?” with prose, not just metadata?
* Can I explore one relationship without losing the object I started from?
* Is the interface using existing product surfaces rather than creating another panel metaphor?
* Did dogfood produce any copy/layout/focus fixes that should be cleaned up before review?
* Is the final implementation simpler than the experiments used to discover it?

---

### State-authority synchronization

Because #738 is merged, this PR should perform backward-looking predecessor synchronization.

Update:

* `Docs/Plans/PLAN-CON-READY-authoring-v2-derived-gold-ablation-loop-v1.md`
* `Docs/Plans/STEWARDS-ANCHOR-con-ready.md`
* `Docs/Sources/design-agent/ACTIVE_AUTHORITY/STEWARDS-ANCHOR-con-ready.md`

Record:

```text
V2-1 published-recap local proposal       MERGED — PR #738
V2-1A working-projection UI dogfood       ACTIVE — this handoff/PR
V2-2 governed World commit                HELD BEHIND V2-1A DOGFOOD
```

Canonical and design-agent STEWARDS anchors remain byte-identical.

Do not pre-mark this UI slice complete before merge.

---

## §8 Required review handback

Record:

1. exact branch/head and dispatch base;
2. actual changed paths;
3. any bounded-discovery paths and why each was needed;
4. dogfood experiments attempted and which final interaction survived;
5. cleanup performed before review;
6. Author Node composition before/after;
7. working-projection derivation and reversal behavior;
8. persistence/remount/scope-switch behavior;
9. identity-vs-alias behavior;
10. local-object representation;
11. local-relationship representation;
12. root prose source/rule;
13. connected-object expansion behavior;
14. proof that prepare/commit/World mutation remain unreachable;
15. exact-run regression result;
16. focused tests/build/static checks;
17. operator dogfood findings still unresolved;
18. named successor V2-2 remains false.

---

## §9 Acceptance rubric

- [ ] #738 is recorded merged and V2-1 predecessor state is synchronized.
- [ ] Highlight → Author graph opens the existing Author Node tool.
- [ ] Published-local Author Node does not hide/replace the recap.
- [ ] Authoring controls remain usable while reading source Markdown.
- [ ] Local `link_existing` visibly creates an exact-node pill in the working projection.
- [ ] Exact node identity is distinguished from true aliasing in the UI where resolvable.
- [ ] Local new-object authoring visibly affects the working projection without pretending durable identity.
- [ ] Local relationship authoring visibly affects working inspection.
- [ ] Proposal removal reverses its local projection effect.
- [ ] Local overlays rehydrate from existing scoped persistence.
- [ ] Campaign/session isolation remains intact.
- [ ] Root object presents truthful useful prose when available.
- [ ] Connected-object prose can be expanded without replacing the root.
- [ ] Expansion failure leaves root context intact.
- [ ] Canonical recap Markdown remains unmodified.
- [ ] Published browse remains non-write authority.
- [ ] No prepare/commit/quick-commit/World publication is introduced.
- [ ] Existing exact-run behavior remains truthful.
- [ ] Dogfood tuning was followed by an explicit cleanup pass.
- [ ] Final cumulative diff contains no abandoned experimental UI.
- [ ] Changed paths remain within §4/bounded discovery.
- [ ] V2-2 remains unimplemented and unauthorized.

---

## Stop conditions

Stop and return to the steward if:

* making the current projection responsive requires modifying canonical recap files;
* immediate UI feedback appears to require a durable World write;
* an API/backend contract change is required;
* a new persistence format/store is required beyond existing local proposal persistence;
* local object references cannot be represented without pretending to be durable World IDs;
* exact-run and published-local authoring cannot be separated without changing write authority;
* usable root/related prose is not present in current projection/complete-object authority and would require generated/synthesized prose;
* relationship expansion requires a generalized recursive graph browser;
* duplicate identity resolution or `merge_objects` becomes necessary;
* a required change escapes the frontend bounded-discovery areas;
* dogfood uncovers a separate independently useful capability that should become its own PR.

When stopping, preserve the experimental evidence and describe what the UI attempt revealed rather than quietly broadening the contract.
