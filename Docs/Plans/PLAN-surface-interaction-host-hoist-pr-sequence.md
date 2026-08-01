---
document_id: dmb-plan-surface-interaction-host-hoist-pr-sequence
title: Surface Interaction Host Hoist — Executable PR Sequence
document_class: implementation_plan
status: active_dispatch_detail
version: 1.0
created_at: "2026-08-01"
updated_at: "2026-08-01"
architecture: ../Design/ARCHITECTURE-surface-interaction-layer.md
parent_plan: PLAN-surface-interaction-hoist-build-first.md
base_anchor: "main@35c3d34c6db44371cba81eb65883b2b76e011cad (PR #469 merge)"
---

# Surface Interaction Host Hoist — Executable PR Sequence

## Purpose

This document turns the Surface Interaction Layer architecture into a sequence of
small implementation PRs suitable for a capable code agent and strict review.

The immediate focus is the **shared host hoist** and a **Build-native proof** of
those hosts. **Plan recomposition is deliberately deferred.** Plan remains a
characterized compatibility consumer while the neutral contracts, host ownership,
and Build World Reference Loop are proven.

This document refines the immediate dispatch order in
[`PLAN-surface-interaction-hoist-build-first.md`](PLAN-surface-interaction-hoist-build-first.md).
It does not replace the architecture authority in
[`ARCHITECTURE-surface-interaction-layer.md`](../Design/ARCHITECTURE-surface-interaction-layer.md).

## Immediate sequencing decision

Do **not** make Plan native to the new publication API before the hosts are proven.
Use compatibility adapters to preserve current Plan behavior while the shared layer
is extracted and Build becomes the first native publisher.

```text
PR #469 authority sync
  → SIH-01 neutral interaction contracts
  → SIH-02 one lease-scoped publication store
  → SIH-03a neutral projection host shell and types
  → SIH-03b explicit projection catalog registrations
  → SIH-04 shared Tool Host
  → SIH-05 shared Edit Host
  → BLD-REF-01 Build search + inspect
  → BLD-REF-02 Build insert + persist + reopen
  → SIH-06 cleanup + dogfood handback

Plan native recomposition
  → deferred until after SIH-06 evidence
```

## Sequence-wide invariant

At every merge point:

1. there is one active surface lease;
2. there is one Tool host, one Edit host, and one Projection host;
3. Canvas retains document authority and document-bound command arbitration;
4. Plan remains behavior-equivalent through explicit compatibility adapters;
5. Build does not acquire graph-write or Graph Review authority;
6. stale registrations, callbacks, and async completions cannot act on the next
   surface lease;
7. no PR requires the next PR to preserve the current product.

## PR construction rules

Every PR in this sequence should:

- have one sentence describing the sole new runtime capability;
- include an exact allowlist in its handoff;
- add owning-boundary tests before changing a consumer;
- preserve a compatibility path until the replacement is exercised by a real
  consumer;
- name the replaced path and its deletion owner;
- avoid broad renames, CSS redesign, or unrelated cleanup;
- remain independently revertible;
- report baseline failures separately from new failures.

A PR should stop and split again when it needs to change both **host lifecycle** and
**domain behavior**, or when review requires understanding more than one authority
transition at once.

## Current compatibility posture

| Current behavior | Temporary treatment during hoist | Native replacement owner |
|---|---|---|
| Plan `editorTools` prop into `AppChrome` | Compatibility adapter publishes Edit contributions | Deferred Plan recomposition |
| Live Control `pageActions` prop | Compatibility adapter publishes Tool contributions | Later surface-native publication |
| Plan `SurfaceConfig` / projection publication | Adapter maps existing Plan config into neutral projection publication | Deferred Plan recomposition |
| Plan hardcoded projection render switch | Retained behind explicit Plan registration adapter until SIH-03b | SIH-03b |
| Build Canvas footer Save | Retained until Build Edit publication is proven | BLD-REF-02 / SIH-06 |
| Build exact graph-pointer context | Retained as inbound compatibility path | BLD-REF-01 / SIH-06 |
| Build extraction toolbar | Out of this hoist; remains Build-owned workflow UI | Stay-on-Build successor |

Compatibility adapters are temporary and must be visibly named `compat` or
`legacyAdapter`; they must not become the neutral public API.

# Slice details

## SIH-01 — Neutral interaction contracts

### Sole capability

The repository has a surface-neutral runtime contract for publishing Tool, Edit,
Canvas, Agent-context, and Projection contributions under one exact surface
identity.

### Implement

Create a neutral package such as:

```text
apps/live-control-ui/src/surfaceInteraction/
  types.ts
  surfaceIdentity.ts
  publication.ts
  boundaries.test.ts
```

Define only the fields required by current behavior:

- exact `surfaceId` + opaque `instanceKey` identity;
- tool launcher ID, label, grouping/order, enabled state, disabled reason, and
  projection target ID;
- edit command ID, label, grouping/order, enabled state, disabled reason, command
  target identity, and invocation callback;
- Canvas handle/pointer sufficient to identify the active work object without
  copying document state;
- projection contribution IDs and bindings;
- bounded Agent ambient context pointers already supported today.

Move or re-export neutral types currently owned by `planSurface/types.ts` only when
that move is mechanical and behavior-preserving. Do not migrate consumers yet.

### Evidence

- Contract tests reject contradictory `surfaceId` / identity combinations.
- Import-boundary test: `surfaceInteraction/**` imports no `planSurface`,
  `buildSurface`, or `ingestSurface` production modules.
- Existing focused Plan, Build, AgentInteraction, and projection tests remain green.

### Must remain false

- No provider/store change.
- No Tool/Edit DOM move.
- No new Build affordance.
- No Plan recomposition.

### Review shape

Types, validators/helpers, adapters, and tests only. No JSX except bounded test
harnesses.

---

## SIH-02 — One lease-scoped publication store

### Sole capability

The existing app-scoped interaction owner can bind one neutral Surface Interaction
publication and safely replace or clear it across route/surface changes.

### Implement

Extend the existing app-level owner rather than creating a second projection owner.
The current `AgentInteractionProvider` may host this state initially; provider
renaming is not part of this PR.

Required lifecycle:

- exact token on bind;
- same-identity update preserves lease and revalidates contributions;
- different identity clears active Tool/Edit/Projection state before binding new;
- stale cleanup cannot erase a newer lease;
- callbacks captured without a valid token remain permanent no-ops;
- invalid/contradictory publication disables contributions and clears prior active
  state;
- no publication produces honest empty hosts.

Add compatibility publishers for current Plan projection publication,
`AppChrome.editorTools`, and `AppChrome.pageActions`; do not remove their existing
call sites yet.

### Evidence

Adversarial provider tests cover:

1. Plan lease A cleanup after Build lease B binds;
2. same-identity config update while a Tool is open;
3. invalid same-identity update clearing actions and projection;
4. async callback captured on A completing after B;
5. null publication after a populated publication;
6. Build empty publication revealing no stale Plan actions.

### Must remain false

- No visible UI change.
- No host DOM extraction.
- No Plan or Build native publication.
- No localStorage expansion.

### Review shape

Provider/state-machine code plus tests. Keep render components unchanged.

---

## SIH-03a — Neutral projection host shell and types

### Sole capability

The singular adaptive Projection host no longer depends on Plan-owned host types,
CSS identity, or Plan-specific context merely to mount and enforce its lease.

### Implement

Move the neutral shell and shared projection types from `planSurface/**` into
`surfaceInteraction/projection/**` while preserving behavior through Plan adapters.

The host may know:

- active surface identity;
- active projection descriptor;
- size and open/close behavior;
- lease-safe Tool/content open requests;
- registered renderer lookup;
- neutral host chrome.

The host must not know:

- Plan session descriptors;
- Plan graph lens construction;
- latest-ingested-session inference;
- Plan-specific tool IDs;
- Plan unresolved-copy policy;
- Plan CSS naming as its public contract.

Plan-specific URL/session inference may remain in a Plan adapter in this PR.

### Evidence

- Exactly one production adaptive container mount remains.
- No production `surfaceInteraction/projection/**` import from `planSurface/**`.
- Existing Plan Tool and reference projection interactions remain equivalent.
- Route switch and stale async session lookup tests remain green.

### Must remain false

- No registry redesign yet.
- No Build projection enablement.
- No Tool Bar move.
- No Plan native publication.

### Review shape

Mechanical ownership move with compatibility adapters. Avoid changing renderer
selection and host ownership in the same PR.

---

## SIH-03b — Explicit projection catalog registrations

### Sole capability

Tool and content renderers are supplied to the neutral Projection host through
explicit registrations instead of a Plan-owned hardcoded render switch.

### Implement

Introduce typed catalog registration with:

- stable projection ID;
- kind (`tool` or `content`);
- preferred size;
- renderer;
- required binding/context contract;
- authorization predicate or capability requirement;
- replacement/cleanup tied to the active surface lease.

Register current implementations through owning adapters:

- Plan registers recap, party registry, statblock, and Plan reference content;
- Ingest registers Graph Review diagnostics;
- unknown/unregistered IDs fail closed.

Do not make catalog registration a graph-write or tool-execution authority. It only
makes a renderer reachable after the surface publication authorizes it.

### Evidence

- Duplicate registration and stale replacement tests.
- Missing binding renders truthful unavailable state or nothing, never a crash.
- Unknown projection ID cannot render arbitrary content.
- Current Plan and Ingest projection suites remain green.
- Source guard: neutral catalog imports no Plan or Ingest concrete component.

### Must remain false

- No Build registration yet.
- No dynamic plugin discovery.
- No Plan UI redesign.

### Review shape

Catalog/registration boundary plus adapter migrations. Do not move Tool/Edit chrome
here.

---

## SIH-04 — Shared Tool Host

### Sole capability

A single Tool host owned by the Surface Interaction Layer renders the active
surface's published launchers and opens authorized registered projections.

### Implement

Extract Tool drawer/bar DOM and open-state behavior from `AppChrome` into a neutral
`ToolHost` that reads the active publication.

Preserve current call sites through compatibility adapters:

- Live Control `pageActions` become temporary Tool contributions;
- Plan tool definitions become temporary Tool contributions;
- Build publishes an empty set.

Tool invocation must re-check the current lease at click time. A stale button or
captured callback cannot launch after a surface switch.

### Evidence

- One production Tool host.
- Plan current tool launch behavior remains equivalent.
- Live Control Inspector action remains available.
- Build shows no stale Plan or Live Control tools.
- Tool open state clears or revalidates on identity change.
- Keyboard close/focus behavior has focused tests.

### Must remain false

- No Find Existing on Build yet.
- No Edit commands in Tool Host.
- No Plan native manifest.
- No broad visual redesign.

### Review shape

One UI host extraction and compatibility wiring. CSS movement is mechanical.

---

## SIH-05 — Shared Edit Host

### Sole capability

A single Edit host owned by the Surface Interaction Layer renders commands for the
active work object without owning Canvas document authority.

### Implement

Extract Edit drawer/bar DOM and open-state behavior from `AppChrome` into a neutral
`EditHost` that reads active edit contributions.

The Edit host may:

- render grouped commands;
- show lock/dirty/status labels supplied by the publisher;
- invoke a lease-validated command;
- show disabled reasons;
- close/revalidate on surface/work-object change.

The Edit host may not:

- read editor localStorage;
- reconstruct document revision/digest;
- mutate Tiptap directly without a Canvas/edit command;
- decide graph identity or durable graph writes.

Keep Plan's `editorTools` path working through a compatibility adapter. Build's Save
footer remains until BLD-REF-02.

### Evidence

- One production Edit host.
- Existing Plan lock, callout, remove-block, copy, and save behaviors remain
  equivalent through the adapter.
- A stale Plan edit command cannot run after Build binds.
- Empty Build edit publication shows no stale Plan controls.
- Disabled reason and command-target identity tests.

### Must remain false

- No Plan native manifest.
- No Build reference insertion yet.
- No Canvas ownership move.
- No Tool workflow rendered in Edit Host.

### Review shape

One UI host extraction, command gate, and compatibility wiring. No domain feature
work.

---

## BLD-REF-01 — Build native search and inspect

### Sole capability

Build becomes the first native Surface Interaction publisher and can search and
inspect existing World Graph objects without leaving the active Canvas.

### Implement

Build publishes:

- exact Build surface identity;
- campaign/world graph lens;
- `Find existing object` Tool contribution;
- graphReference projection binding;
- graph object content registration if not already globally registered;
- no edit/reference insertion command yet.

Flow:

```text
Build Canvas remains mounted
  → Tool Host: Find existing object
  → neutral graphReference search with Build lens
  → operator selects View
  → shared Projection host opens exact object
  → relationship traversal remains lease- and revision-safe
```

Reuse `graphReference` contracts from PR #431. Adapt or retire the current
`BuildGraphObjectContext` only where the shared projection path fully replaces it;
keep inbound exact-pointer URLs working until SIH-06.

### Evidence

- Build search uses exact campaign/lens scope.
- View does not dirty or save the document.
- Ambiguity never auto-selects.
- Pinned revision and current-head states are distinguishable.
- Relationship navigation cannot complete onto a replaced Build document/surface.
- Plan behavior is unchanged.

### Must remain false

- No insertion.
- No graph write or node creation.
- No extraction candidate mapping.
- No Plan recomposition.
- No Ask-on-Build expansion.

### Review shape

One read-only vertical slice. Prefer one Build adapter and one shared search tool
registration over Build-local UI.

---

## BLD-REF-02 — Build insert, persist, and reopen

### Sole capability

An operator can insert an exact existing graph reference into the current Build
Canvas, save it, reload the document, and reopen the same exact object from the
rendered chip.

### Implement

Build publishes Edit contributions for:

- Insert selected exact reference at the current Canvas selection;
- Save current document through `MarkdownCanvasSession`;
- optional lock/edit state only if the Canvas contract already supports it.

Insertion requirements:

- exact durable node ID on the selected payload;
- Canvas/editor selection identity captured explicitly;
- command runs through the Canvas command/admission path;
- document switch invalidates pending insertion;
- successful insert marks dirty but performs no implicit save;
- save receipt remains the sole durable document authority;
- chip click resolves and projects through the shared graphReference path.

Once the shared Edit Save command is proven, remove or demote the duplicate Build
footer Save in SIH-06 rather than mixing demolition into the feature PR.

### Evidence

End-to-end focused test:

```text
open Build document A
→ Find existing Tripod Null-Calf
→ inspect exact node
→ Insert reference
→ document dirty
→ Save
→ hard-remount/reload exact document
→ click chip
→ same exact node ID and revision policy reopen
```

Adversarial tests:

- insert completion after document A → B switch;
- ambiguous result cannot insert;
- unavailable graph keeps existing chip visible but unresolved;
- save conflict preserves inserted local content;
- stale projection result cannot bind a different exact node.

### Must remain false

- No candidate-to-node auto-match.
- No graph mutation.
- No Plan native publication.
- No Agent-generated insertion.

### Review shape

One document-write vertical slice using already-landed Canvas authority.

---

## SIH-06 — Cleanup, dogfood, and next handback

### Sole capability

The host hoist and Build World Reference Loop have one clean product path, with
temporary duplicate Build paths removed only after replacement evidence exists.

### Implement

- Remove unused Build-local duplicate graph context/UI only where BLD-REF-01/02
  fully replace it.
- Remove duplicate Build Save affordance if the shared Edit command is accepted.
- Keep Plan compatibility adapters and label them as the owner of deferred Plan
  recomposition.
- Record live dogfood for surface switching, Build search/inspect/insert/reload,
  and Plan regression.
- Write the next handoff from observed friction rather than automatically
  dispatching Plan recomposition.

### Required dogfood

1. Open Plan, launch current tools, edit/save current planning document.
2. Switch to Build; verify no stale Plan Tool/Edit/Projection state.
3. Search, inspect, traverse, insert, save, reload, and reopen an existing object.
4. Switch back to Plan; verify current Plan behavior remains intact.
5. Exercise a stale async operation across both switch directions.

### Must remain false

- No Plan native recomposition.
- No Play work.
- No graph writes.
- No broad chrome redesign.

### Review shape

Demolition and evidence only. No new capability should be introduced here.

# Deferred Plan recomposition

Plan native publication is intentionally **not** part of the immediate sequence.
Until a later handoff is authorized:

- Plan continues to publish through compatibility adapters;
- Plan session/prep policy remains Plan-owned;
- Plan callouts, lock semantics, graph lens, and Agent query behavior remain
  unchanged;
- compatibility adapters receive explicit deletion ownership in the future Plan
  recomposition handoff;
- no code agent should opportunistically replace Plan's authoring stack or migrate
  Plan to `MarkdownCanvasSession` during SIH or BLD-REF work.

The decision after SIH-06 may be Plan recomposition, further Build refinement, or a
host-contract correction. Dogfood evidence decides.

# Parallel work

These lanes may proceed independently when they do not touch the same host files:

- BLD inspection-truth defect;
- Temporal extraction work;
- Threat/statblock publication work;
- R10b conversation/persistence design, provided it does not introduce a second
  projection or surface lease owner.

Coordinate before merging any parallel branch that edits:

```text
apps/live-control-ui/src/App.tsx
apps/live-control-ui/src/chrome/AppChrome.tsx
apps/live-control-ui/src/agentInteraction/AgentInteractionProvider.tsx
apps/live-control-ui/src/agentInteraction/projectionSurfacePublication.ts
apps/live-control-ui/src/planSurface/projection/**
apps/live-control-ui/src/surfaceInteraction/**
```

# Dispatch checklist for the code agent

Before each PR:

1. rebase/reset onto current `main`;
2. read this document, the architecture authority, and the parent plan;
3. inspect the current implementation rather than trusting path names in this
   document;
4. write the PR handoff with exact base SHA and allowlist;
5. characterize current tests on base;
6. implement only the named sole capability;
7. run focused owning-boundary tests, full frontend suite when feasible, typecheck,
   build, and `git diff --check`;
8. compare failures against the exact base;
9. include a demolition declaration;
10. stop instead of absorbing the next slice.

# Completion condition

This plan is complete when:

- one lease-scoped Surface Interaction publication controls Tool, Edit, and
  Projection hosts;
- those hosts are surface-neutral and singular;
- Build natively publishes a graph lens, search workflow, projection binding, and
  Canvas edit commands;
- the Build search → inspect → insert → save → reload → reopen loop passes;
- Plan remains behavior-equivalent through explicit temporary adapters;
- live dogfood records whether Plan recomposition is actually the next best move.
