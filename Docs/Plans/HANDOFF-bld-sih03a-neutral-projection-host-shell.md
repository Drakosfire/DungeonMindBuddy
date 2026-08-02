---
pr_body_template: |
  ## Outcome

  The singular Projection host shell, host CSS identity, and canonical shared Projection runtime types are owned outside Plan, while current Plan/Ingest policy and renderer selection remain behind an explicit temporary adapter.

  ## Merge-ready invariant

  Exactly one neutral ProjectionHost mount exists in production; Plan no longer owns the host DOM/CSS or canonical ActiveProjection/ProjectionSize types; LegacyProjectionHostAdapter alone retains URL/session/renderer policy; projectionRegistry.tsx is byte-behavior-equivalent and untouched.

  ## Evidence required to merge

  See HANDOFF §7. Local author evidence is insufficient without authority-lineage proof and complete host lifecycle/theme replacement coverage.

  ## Scope and explicit deferrals

  Implementation base must be the exact origin/main SHA that contains this handoff. Docs sync, SIH-03b catalog, Tool/Edit hosts, Build capability, and persistence remain out of scope.

  ## Evidence produced

  ### Automated
  TODO
  ### Adversarial
  TODO
  ### Regression
  TODO
  ### Manual / dogfood
  Not applicable for this ownership-transfer slice unless visible Plan toolbox behavior changes.

  ## Gaps, waivers, and stop conditions
  TODO: none, or exact missing evidence, operator waiver, and stop report.
---

# HANDOFF — BLD-SIH-03a Neutral Projection Host Shell

**Created:** 2026-08-02.  
**Status:** ACTIVE — Design Agent dispatch to Code Agent.  
**Workstream label:** BLD-SIH-03a  
**Suggested branch:** `bld/sih03a-neutral-projection-host-shell`  
**Canonical repo path:** `Docs/Plans/HANDOFF-bld-sih03a-neutral-projection-host-shell.md`  
**PR number:** intentionally irrelevant and omitted.  
**Implementation PR documentation:** code and tests only; roadmap, tracker, handoff-status, and post-merge documentation synchronization happen in separate documentation changes.

**Status banner:** ACTIVE AUTHORITY CANDIDATE — dispatch only after this handoff is checked into `main`.  
**Use for:** Implementing exactly one Build-lane Surface Interaction capability: moving the singular Projection host shell and its shared runtime types out of Plan ownership.  
**Do not use for:** Projection catalog registration, Tool/Edit host extraction, Build graph-reference capability, Plan native recomposition, renderer redesign, persistence, or roadmap/status synchronization.  
**Design-state anchor inspected at authoring:** `main@917b9d5dff3985b3664aa274eafad7eacb776658`  
**Implementation base rule:** the Code Agent must branch from the exact immutable `origin/main` SHA that contains this checked-in handoff and record that SHA before changing production code.  
**Last design sync checked:** 2026-08-02

**Amended 2026-08-02 (pre-merge review round):** §4 now explicitly enumerates the five predicted owning-suite maintenance test paths (`App.test.tsx`, `PlanSurfaceShell.test.tsx`, `GraphReviewWorkbenchModule.test.tsx`, `projectionBindings.test.tsx`, `surfaceInteraction/boundaries.test.ts`). The prior two-file bounded discovery exception is closed (maximum additional paths: 0). `projectionTestHost.tsx` comment-only edits are explicitly out of allowlist. Neutral `ProjectionHost` must not embed Plan-owned presentation defaults (for example `"Plan toolbox"`); callers supply complete `ProjectionHostLabels`. Tool projection keys must not be interpolated into CSS class tokens.

Conversation and agent routing

This handoff belongs to the Build workstream. The BLD- prefix is the human routing key that identifies which agent lane owns the work.

Design conversation name: BLD — DungeonBuddy Build Design Agent

Code conversation name: BLD — DungeonBuddy Build Code Agent

Direction: the Build Design Agent authored this handoff and is passing it to the Build Code Agent.

Review target name: BLD-SIH-03a — Neutral Projection Host Shell

The Code Agent must preserve the BLD-SIH-03a label in its branch, handback, and review requests. A GitHub PR number is incidental metadata, not the identity of this work.

Lane-specific operator workflow rules

These rules are explicit operator instructions for this Build lane:

The checked-in handoff, actual base/head SHAs, code diff, tests, and review ledger are authoritative.

The PR description is not an authority and is not an acceptance artifact. It may be minimal, stale, or absent without weakening the review contract.

Reviewers must identify the work by BLD-SIH-03a, the head branch, and the exact head SHA. Do not navigate or reason primarily from a PR number.

Documentation synchronization is separate. The implementation PR must not update roadmaps, trackers, handoff status, archive state, or “what is next” prose.

Review is allowed to request as many changes as are required to make the declared invariant true. Do not cap findings or accept a known defect merely to keep a review round small.

Every requested change must be discrete and specific: exact path or symbol, falsifying sequence, required fix, and required proof.

The Code Agent works in nano commits. Preserve a readable commit story during implementation and review rather than collapsing the work into one opaque commit.

These lane rules intentionally replace PR-number-first navigation and PR-description-first review for this slice. Repository safety, test, scope, and non-destructive-work rules remain in force.

Dispatch gate

Do not begin implementation until all of the following are true:

This handoff exists on origin/main at its canonical path.

The Code Agent records the immutable origin/main SHA containing this handoff.

main includes merged BLD-SIH-01 / SIH-01 neutral contracts and merged BLD-SIH-02 / SIH-02 lease-scoped publication ownership.

The current production topology still has exactly one app-level AdaptiveProjectionContainer mount beneath AgentInteractionProvider.

Renderer selection still lives in planSurface/projection/projectionRegistry.tsx.

No competing BLD-SIH-03a implementation is active against the same host files.

The Code Agent has read the authority and implementation files listed in §2 in order.

If the handoff has landed but main has moved materially beyond the inspected design anchor, the Code Agent must re-run the seam inventory. A later base is permitted only when the declared ownership split remains valid. Material divergence is a stop condition, not permission to reinterpret the mission.

Build-lane sequence label map

Older design documents use unprefixed SIH-* names. For operator navigation, this lane uses the following names going forward:

Build-lane label

Older label

State at design anchor

BLD-SIH-01

SIH-01

MERGED — neutral Surface Interaction contracts

BLD-SIH-02

SIH-02

MERGED — singular lease-scoped publication store

BLD-SIH-03a

SIH-03a

THIS HANDOFF — neutral Projection host shell

BLD-SIH-03b

SIH-03b

SUCCESSOR — explicit Projection catalog registrations

BLD-SIH-04

SIH-04

SUCCESSOR — shared Tool Host

BLD-SIH-05

SIH-05

SUCCESSOR — shared Edit Host

BLD-REF-01

BLD-REF-01

SUCCESSOR — Build search and inspect

BLD-REF-02

BLD-REF-02

SUCCESSOR — Build insert, persist, and reopen

BLD-SIH-06

SIH-06

SUCCESSOR — cleanup and dogfood handback

This handoff does not edit the older authority documents to apply those labels. That synchronization is a separate docs operation.

§0 Capability decomposition decision

Candidate outcome

Independently useful?

Public/durable contract changed?

Operator surface changed?

Failure model changed?

Independently testable or revertible?

Decision

Move canonical Projection host runtime types out of planSurface/types.ts

No, not useful without moving the host shell that consumes them

Internal runtime type ownership only

No

No

Yes

Include — same ownership invariant

Extract drawer/toggle/backdrop/header/nav/body DOM and neutral lifecycle into surfaceInteraction/projection/**

Yes

Internal component contract

No intended visual change

Yes, ownership and cleanup become explicit

Yes

Include — selected capability

Keep URL tool selection, latest-ingested-session inference, Plan context requirements, graph-reference policy, and renderer choice in a Plan-owned compatibility adapter

No separate user capability; required to keep the extraction behavior-preserving

No new durable contract

No

Preserves existing failure behavior

Yes

Include — compatibility proof

Rename and relocate Projection-host CSS away from plan-* ownership

No useful outcome separately from shell ownership

Internal CSS contract

No intended visual change

No

Yes

Include — same ownership invariant

Replace the Plan-owned hardcoded renderer switch with registrations

Yes

New runtime catalog/registration contract

Potentially

Yes

Yes

Successor: BLD-SIH-03b

Extract Tool launcher DOM from AppChrome

Yes

New shared host contract

Yes

Yes

Yes

Successor: BLD-SIH-04

Extract Edit command DOM from AppChrome

Yes

New shared host contract

Yes

Yes

Yes

Successor: BLD-SIH-05

Enable Build search, inspect, insertion, or persistence

Yes

New Build capability

Yes

Yes

Yes

Successor: BLD-REF-01 / BLD-REF-02

Make Plan a native neutral publisher and delete compatibility adapters

Yes

Consumer migration contract

Potentially

Yes

Yes

Deferred after BLD-SIH-06 dogfood

Persist active projection or host UI state

Yes

Durable storage contract

Yes

Yes

Yes

Reject / separate capability

Redesign the right-side drawer or bottom Agent pane

Yes

Product UI contract

Yes

Yes

Yes

Reject / separate capability

Selected capability

The application has one Projection host shell and canonical Projection runtime types owned by surfaceInteraction/projection/**, while current Plan/Ingest navigation, session inference, graph policy, and renderer selection remain behavior-equivalent behind an explicitly temporary Plan-owned adapter.

Why the included rows share one invariant

Moving the JSX without its runtime types and CSS leaves Plan as the real host owner. Moving the host without isolating Plan URL/session and renderer policy makes the neutral layer depend on Plan. These changes are one ownership transfer: neutral shell and lifecycle move; domain policy does not.

Named successors

BLD-SIH-03b — explicit Projection catalog registrations and removal of the Plan-owned renderer switch.

BLD-SIH-04 — shared Tool Host.

BLD-SIH-05 — shared Edit Host.

BLD-REF-01 / BLD-REF-02 — Build-native World Reference Loop.

Deferred Plan native recomposition after BLD-SIH-06 evidence.

§1 Mission

The application renders its singular adaptive Projection shell from surfaceInteraction/projection/** so the shell, shared runtime types, CSS identity, open/close behavior, and size behavior no longer belong to Plan, while existing Plan and Ingest projection behavior remains unchanged through an explicit compatibility adapter.

Merge-ready invariant

At every observable point there is exactly one app-level Projection host.

The host shell, host CSS identity, and canonical ActiveProjection / ProjectionSize
runtime types are owned by surfaceInteraction/projection/** and import no Plan,
Build, Ingest, graph policy, session inference, API lookup, or concrete renderer.

Plan-owned code may adapt the current legacy publication, URL/session behavior,
graph-reference policy, diagnostics payload, and hardcoded renderer selection into
neutral host props, but it may not own or duplicate host DOM, host open/close
effects, host size classes, backdrop behavior, Escape handling, or body-open state.

The existing provider remains the sole selected-projection and lease owner.
No new provider, token, catalog, renderer registry, persistent state, Build
capability, or Plan-native publication is introduced.

Mission falsification test

This is not BLD-SIH-03a if implementation must also:

- introduce renderer registration or a projection catalog;
- change which concrete component renders for any existing projection ID;
- move graph-reference authorization or Plan session policy into the neutral host;
- add a Build tool, projection, reference search, insertion, or graph lens;
- extract Tool Host or Edit Host DOM;
- change Graph Review authority or candidate/committed-memory behavior;
- persist active projection or drawer state;
- redesign visible chrome or navigation copy;
- migrate Plan off the legacy projection publication adapter;
- change graph identity, matching, evidence, or fallback semantics.

§2 Context, authority, and boundaries

Field

Required content

Architecture authority

Docs/Design/ARCHITECTURE-surface-interaction-layer.md

Executable sequence

Docs/Plans/PLAN-surface-interaction-host-hoist-pr-sequence.md

Parent execution plan

Docs/Plans/PLAN-surface-interaction-hoist-build-first.md

Predecessor authority

Docs/Plans/HANDOFF-sih01-neutral-surface-interaction-contracts.md; Docs/Plans/HANDOFF-sih02-lease-scoped-surface-interaction-store.md

Historical host authority

Docs/Plans/HANDOFF-r10a-app-scoped-projection-host-lift.md

Repository rules

AGENTS.md; applicable non-destructive and test rules; this handoff’s explicit Build-lane workflow overrides for PR numbering/body/docs sync

Design-state base inspected

917b9d5dff3985b3664aa274eafad7eacb776658

Implementation base

Exact immutable origin/main SHA containing this handoff, recorded before code changes

Current host mount

apps/live-control-ui/src/App.tsx mounts AdaptiveProjectionContainer once beneath AgentInteractionProvider

Current host shell

apps/live-control-ui/src/planSurface/projection/AdaptiveProjectionContainer.tsx

Current selected-state owner

apps/live-control-ui/src/agentInteraction/AgentInteractionProvider.tsx

Current shared type leak

ActiveProjection / ProjectionSize are defined in planSurface/types.ts and imported by app-level provider types

Current renderer selection

apps/live-control-ui/src/planSurface/projection/projectionRegistry.tsx

Current Plan/session adapter responsibilities

URL tool parsing, session parsing, session-aware tool set, recap artifact lookup, campaign-keyed cache, exact stale-surface check

Exact inputs consumed

Current provider projection state, validated legacy ProjectionSurfacePublication, SurfaceConfig, existing graph-reference resolution/binding state, diagnostics payload, current registry functions

Named successor

BLD-SIH-03b

What remains false

Build has no Projection trigger; renderer selection is still hardcoded under Plan; Tool/Edit hosts remain in AppChrome; Plan still publishes through compatibility APIs

Explicit non-goals

Backend work, graph writes, persistence, route rewrite, visual redesign, new projection IDs, renderer changes, source/session policy changes, roadmap sync

Authority precedence

1. Explicit operator instructions in this handoff for BLD naming, PR navigation,
   PR-description irrelevance, nano commits, review behavior, and separate docs sync.
2. Docs/Design/ARCHITECTURE-surface-interaction-layer.md.
3. Docs/Plans/PLAN-surface-interaction-host-hoist-pr-sequence.md.
4. Docs/Plans/PLAN-surface-interaction-hoist-build-first.md.
5. Merged BLD-SIH-01 / SIH-01 and BLD-SIH-02 / SIH-02 contracts.
6. This checked-in handoff.
7. Current repository implementation and owning-boundary tests at the implementation base.
8. Historical R10a handoff for preserved behavior, not target ownership.
9. Project Sources and chat summaries.

Read authoritative inputs in order

Docs/Design/ARCHITECTURE-surface-interaction-layer.md

Docs/Plans/PLAN-surface-interaction-host-hoist-pr-sequence.md

Docs/Plans/PLAN-surface-interaction-hoist-build-first.md

Docs/Plans/HANDOFF-sih01-neutral-surface-interaction-contracts.md

Docs/Plans/HANDOFF-sih02-lease-scoped-surface-interaction-store.md

Docs/Plans/HANDOFF-r10a-app-scoped-projection-host-lift.md — preserved behavior only

apps/live-control-ui/src/App.tsx

apps/live-control-ui/src/agentInteraction/AgentInteractionProvider.tsx

apps/live-control-ui/src/agentInteraction/agentInteractionTypes.ts

apps/live-control-ui/src/surfaceInteraction/types.ts

apps/live-control-ui/src/planSurface/types.ts

apps/live-control-ui/src/planSurface/projection/AdaptiveProjectionContainer.tsx

apps/live-control-ui/src/planSurface/projection/projectionContext.tsx

apps/live-control-ui/src/planSurface/projection/projectionRegistry.tsx

apps/live-control-ui/src/planSurface/projection/projectionBindings.ts

apps/live-control-ui/src/planSurface/projection/AdaptiveProjectionContainer.test.tsx

apps/live-control-ui/src/planSurface/projection/projectionBindings.test.tsx

apps/live-control-ui/src/planSurface/PlanSurfaceShell.test.tsx

apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewWorkbenchModule.test.tsx

apps/live-control-ui/src/planSurface/planSurface.css

Current implementation seam

The current app already has one projection-state owner and one global host mount:

App
└─ AgentInteractionProvider
   └─ AskPluginSlotProvider
      ├─ active route content
      ├─ AdaptiveProjectionContainer   ← one global mount, wrong source ownership
      └─ AgentInteractionChrome

The current AdaptiveProjectionContainer mixes four layers:

Neutral host shell and lifecycle
  - fixed toggle
  - drawer/backdrop
  - open/closed body class
  - Escape close
  - compact/wide/fullscreen classes
  - header/nav/body chrome
  - content Expand and Close controls
  - active theme application

Provider-owned state and lease actions
  - active projection
  - close / expand / openTool
  - current reference state and registered payloads

Plan-owned navigation and session policy
  - ?tool= and hash parsing
  - ?session= parsing
  - session-aware tool ID set
  - latest recap artifact lookup
  - campaign-keyed session cache
  - exact stale-surface identity rejection

Plan-owned renderer and graph policy
  - renderToolProjection
  - renderContentProjection
  - SurfaceConfig / PlanContextDescriptor
  - graph-reference binding and diagnostics payload

BLD-SIH-03a extracts only the first layer and canonical shared runtime types. The provider stays the state owner. The third and fourth layers stay behind a temporary adapter until BLD-SIH-03b or later consumer recomposition.

§3 Observable-path inventory

Observable path

Current behavior

Required behavior after BLD-SIH-03a

Same invariant?

Owning boundary

App route has no valid projection publication

Global Plan-owned container returns null; no host chrome

Temporary adapter returns null; neutral host is not mounted; no toggle, drawer, backdrop, Escape handler, or body-open class

Yes

Adapter + neutral host cleanup

Build publishes valid empty tools

Plan-owned container returns null

Adapter returns null; neutral host renders nothing; no stale Plan/Ingest chrome

Yes

Adapter

Contradictory/invalid publication

Provider exposes no authorized projection; old host disappears

Same fail-closed result; neutral host unmount removes its open body class and handlers

Yes

Provider + adapter + host effect cleanup

Plan opens first Tool from side toggle

Container performs existing URL/session inference then provider openTool

Plan adapter performs identical inference and lease recheck; neutral host only emits exact item ID to adapter

Yes

Plan adapter + provider

Plan clicks another Tool in host nav

Current code updates URL and opens exact ID

Same exact order, labels, URL behavior, and tool opening; neutral host owns nav DOM only

Yes

Host DOM + Plan adapter

URL requests enabled tool

Current container opens exact configured ID

Adapter preserves exact current behavior; neutral host contains no URL logic

Yes

Plan adapter

URL requests unknown/unavailable tool

No open

Same no-op

Yes

Plan adapter/provider

Session-aware Tool has no explicit session

Current container fetches recap artifacts and infers latest numeric session

Same lookup and sorting/filtering behavior in Plan adapter

Yes

Plan adapter

Session lookup resolves after surface/campaign replacement

Current exact identity ref rejects stale result

Same rejection; stale result cannot mutate URL or projection state

Yes

Plan adapter + provider lease

Active Tool is open

Right drawer, backdrop, nav, header, body, Escape close

Same visible/accessibility behavior; DOM and effects come from neutral host

Yes

Neutral host

Active content reference is open

No backdrop, nav hidden, Reference header, optional Expand

Same behavior and copy; renderer output unchanged

Yes

Neutral host + Plan renderer adapter

Same-identity config changes tool label/size

Provider rebuilds active metadata; drawer updates

Neutral host consumes latest ActiveProjection and updates title/size exactly

Yes

Provider + neutral host

Current Tool removed or publication invalidated

Provider clears active state; body class cleaned

Same result; neutral host effects clean synchronously on unmount/update

Yes

Provider + neutral host

Theme tokens/theme ID change

Current host applies legacy config theme

Adapter passes current theme to neutral host; old theme cannot remain after replacement/unmount

Yes

Adapter + neutral host

Escape while open

Current container closes

Neutral host owns one Escape listener and calls current lease-guarded close

Yes

Neutral host + provider

Backdrop click on Tool projection

Current container closes

Same

Yes

Neutral host

Backdrop interaction on content reference

Backdrop absent/disabled to preserve canvas chip hit-testing

Same defense-in-depth behavior

Yes

Neutral host CSS/DOM

Concrete Tool renderer selection

Plan hardcoded switch chooses existing component

Unchanged; Plan adapter invokes existing renderToolProjection

Yes

Existing Plan registry

Concrete content renderer selection

Plan card renderer handles graph resolution/binding

Unchanged; Plan adapter invokes existing renderContentProjection

Yes

Existing Plan registry

Missing Plan graph-reference binding

Current renderer fails closed/omits unavailable actions

Unchanged

Yes

Existing Plan card/registry

Graph Review diagnostics payload

Current registry passes latest current-lease payload

Unchanged

Yes

Existing registry/provider

App production topology

App imports Plan-owned container once

App mounts one temporary adapter which renders exactly one neutral ProjectionHost; no old container remains

Yes

App + source boundary test

Every row is one ownership-transfer invariant. Any required new renderer, catalog, Build capability, or persistence path is a split trigger.

§4 Files in scope — exact allowlist

The implementation PR may change only the following paths.

Action

Path

Purpose: how this establishes or proves the invariant

Create

apps/live-control-ui/src/surfaceInteraction/projection/types.ts

Own canonical ProjectionKind, ProjectionSize, and ActiveProjection runtime types outside Plan; add only host-facing presentation types needed by the neutral shell

Create

apps/live-control-ui/src/surfaceInteraction/projection/ProjectionHost.tsx

Own all Projection host DOM and neutral open/close/size/backdrop/Escape/theme behavior through props; import no Plan/domain policy

Create

apps/live-control-ui/src/surfaceInteraction/projection/projectionHost.css

Own neutral host selectors and the mechanically moved host styling; contain no .plan-* selectors

Create

apps/live-control-ui/src/surfaceInteraction/projection/ProjectionHost.test.tsx

Prove neutral shell behavior independently of Plan, provider, API lookup, graph policy, and concrete renderers

Create

apps/live-control-ui/src/surfaceInteraction/projection/projectionBoundaries.test.ts

Prove import ownership, CSS ownership, one production host mount, and absence of the old Plan-owned container

Create

apps/live-control-ui/src/planSurface/projection/LegacyProjectionHostAdapter.tsx

Retain current legacy publication gating, URL/session policy, stale lookup protection, and renderer calls; translate them into neutral host props without host DOM

Create

apps/live-control-ui/src/planSurface/projection/LegacyProjectionHostAdapter.test.tsx

Preserve and extend current Plan/Ingest integration tests after the shell extraction

Modify

apps/live-control-ui/src/App.tsx

Replace the one old global container mount with exactly one temporary adapter/neutral-host composition

Modify

apps/live-control-ui/src/agentInteraction/AgentInteractionProvider.tsx

Import canonical Projection runtime types from the neutral owner; no provider behavior change is authorized

Modify

apps/live-control-ui/src/agentInteraction/agentInteractionTypes.ts

Import/export canonical Projection runtime types from the neutral owner; no public behavior expansion

Modify

apps/live-control-ui/src/planSurface/types.ts

Remove canonical ownership of shared Projection runtime types and import the neutral size type for legacy SurfaceToolConfig

Modify

apps/live-control-ui/src/planSurface/projection/projectionContext.tsx

Consume neutral runtime types and remove Plan-owned host class-name utility; remain a compatibility facade over AgentInteractionProvider

Modify

apps/live-control-ui/src/planSurface/planSurface.css

Delete only the host-shell CSS moved to projectionHost.css; retain Plan content, card, Agent, and domain styles

Delete

apps/live-control-ui/src/planSurface/projection/AdaptiveProjectionContainer.tsx

Remove the Plan-owned mixed host implementation after its responsibilities are split

Delete

apps/live-control-ui/src/planSurface/projection/AdaptiveProjectionContainer.test.tsx

Replace with neutral host tests plus legacy adapter integration tests

Modify

apps/live-control-ui/src/App.test.tsx

Owning-suite maintenance for the singular host mount selector (`.plan-toolbox` → `.surface-projection-host`)

Modify

apps/live-control-ui/src/planSurface/PlanSurfaceShell.test.tsx

Owning-suite maintenance for AdaptiveProjectionContainer → LegacyProjectionHostAdapter / neutral type imports

Modify

apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewWorkbenchModule.test.tsx

Owning-suite maintenance for AdaptiveProjectionContainer → LegacyProjectionHostAdapter / neutral type imports

Modify

apps/live-control-ui/src/planSurface/projection/projectionBindings.test.tsx

Owning-suite maintenance for AdaptiveProjectionContainer → LegacyProjectionHostAdapter / neutral type imports

Modify

apps/live-control-ui/src/surfaceInteraction/boundaries.test.ts

SIH-01 production-file inventory must skip the new `projection/` subdirectory without widening SIH-01 production ownership

Out of allowlist (do not change)

apps/live-control-ui/src/planSurface/projection/projectionTestHost.tsx

Comment-only churn is not an authorized implementation path; leave this file untouched in the implementation PR

Bounded discovery exception

Directory: apps/live-control-ui/src
Maximum additional paths: 0
Allowed path kinds: none in this amended handoff
Decision rule: the five owning-suite maintenance paths above are predicted and enumerated in §4. Do not use a discovery exception to absorb predictable boundary-suite updates. If any additional path is required, stop and re-brief.

No additional production path is permitted. If a production path outside this table is required, stop and report it.

§5 Files and capabilities explicitly out of scope

Path, ownership layer, or capability

Why this slice must not touch or claim it

apps/live-control-ui/src/planSurface/projection/projectionRegistry.tsx

Renderer selection must remain byte-behavior-equivalent and Plan-owned until BLD-SIH-03b

apps/live-control-ui/src/planSurface/projection/projectionBindings.ts

Typed binding/payload ownership and catalog registration are BLD-SIH-03b

Concrete modules imported by projectionRegistry.tsx

No renderer move, redesign, prop change, or selection change is authorized

apps/live-control-ui/src/agentInteraction/surfaceInteractionLease.ts

BLD-SIH-02 lease behavior is a predecessor; this slice consumes it and must not reopen it

Provider lease/action behavior

Provider changes are import-only unless a compile-only type annotation is unavoidable; any runtime change is a stop condition

apps/live-control-ui/src/chrome/AppChrome.tsx

Tool/Edit host extraction belongs to BLD-SIH-04 / BLD-SIH-05

apps/live-control-ui/src/planSurface/PlanSurfaceShell.tsx

Plan publication and domain policy remain unchanged

apps/live-control-ui/src/ingestSurface/MemoryIngestPage.tsx

Ingest workflow and publication remain unchanged

apps/live-control-ui/src/buildSurface/**

Build gains no tool, projection, graph lens, search, inspect, insert, save, or reopen capability

apps/live-control-ui/src/graphReference/**

Graph-reference contract and identity behavior remain unchanged

apps/live-control-ui/src/surfaceInteraction/types.ts and publication.ts

SIH-01 neutral publication contract is not amended by a host ownership move

New projection catalog, registration API, renderer map, plugin discovery

BLD-SIH-03b

New bottom pane, responsive redesign, animation redesign, focus-trap redesign

Separate product/UI capability

localStorage, URL persistence, thread persistence, projection rehydration

Separate durable-state capability

Router rewrite or SPA navigation

Separate routing capability

Graph Review candidate/commit authority

Campaign Supergraph lane, unrelated invariant

Roadmaps, trackers, handoff status, archive notes, PR-number maps

Separate documentation synchronization after implementation merge

PR description authoring as evidence

Explicitly non-authoritative in this Build lane

Nearby cleanup is not authorization. Do not rename unrelated Plan styles, reorganize projection modules, or “finish” the next catalog slice while these files are open.

§6 Implementation contract

§6.1 Final ownership topology

After this slice, the production topology must be equivalent to:

App
└─ AgentInteractionProvider                 selected state + lease owner (unchanged)
   └─ AskPluginSlotProvider
      ├─ active route content
      ├─ LegacyProjectionHostAdapter        temporary Plan-owned policy adapter
      │  └─ ProjectionHost                  one neutral host shell
      └─ AgentInteractionChrome

Forbidden topologies:

App
├─ Plan ProjectionHost
└─ neutral ProjectionHost                   // duplicate hosts

surfaceInteraction/projection/ProjectionHost
└─ imports projectionRegistry / PlanContext // neutral host still Plan-owned

LegacyProjectionHostAdapter
└─ duplicates drawer/header/nav JSX         // adapter remains a second host

ProjectionHost
└─ owns active projection state or token     // second state owner

§6.2 Canonical runtime types

Create surfaceInteraction/projection/types.ts as the canonical owner of the existing runtime shapes:

export type ProjectionKind = SurfaceInteractionProjectionKind;
export type ProjectionSize = SurfaceInteractionProjectionSize;

export interface ActiveProjection {
  kind: ProjectionKind;
  key: string;
  size: ProjectionSize;
  title: string;
  glanceOnly?: boolean;
}

The exact aliases may import from ../types, but the values and optionality must remain exact.

Host-facing presentation types may be added here only when they are truly neutral, for example:

interface ProjectionHostNavigationItem {
  id: string;
  label: string;
}

interface ProjectionHostTheme {
  themeId?: string;
  tokens?: Readonly<Record<string, string>>;
}

interface ProjectionHostLabels {
  toggleTitle: string;
  closedDrawerLabel: string;
  navigationLabel: string;
  closeLabel: string;
  toolKicker: string;
  contentKicker: string;
  toolTitle: string;
  contentTitle: string;
}

Do not move SurfaceConfig, PlanContextDescriptor, PlanSessionDescriptor, graph bindings, diagnostics payloads, or renderer props into the neutral package.

planSurface/types.ts may consume the neutral ProjectionSize for legacy config typing, but it must no longer define canonical shared Projection runtime types.

AgentInteractionProvider.tsx and agentInteractionTypes.ts must import ActiveProjection / ProjectionSize from the neutral owner. A Plan re-export must not remain the provider-facing API.

§6.3 Neutral ProjectionHost

ProjectionHost is a controlled shell. It receives current state and guarded actions through props. It does not read domain configuration or choose renderers.

Required responsibilities:

render the fixed Tools toggle;

render the drawer, backdrop, header, navigation, body, Expand, and Close controls;

derive open state from active !== null;

apply compact/wide/fullscreen class from the current active projection size;

show backdrop only for active Tool projections;

hide navigation for content projections;

expose the same active nav pressed state;

call the supplied exact navigation callback with the exact item ID;

call current supplied Close/Expand callbacks;

install one Escape listener only while open;

add/remove one neutral body-open class only while open;

remove the body class and listener on unmount;

apply supplied theme tokens and theme ID;

preserve existing visible and accessibility copy through supplied neutral labels;

render supplied body content without inspecting its domain type.

The neutral host must not:

import AgentInteractionProvider or own selected state;

allocate or compare surface lease tokens;

parse URL/query/hash values;

call getRecapArtifacts or any API;

know session-aware Tool IDs;

import SurfaceConfig or PlanContextDescriptor;

import graph-reference or Graph Review types;

import projectionRegistry.tsx or any concrete renderer;

inspect a campaign, session, document, node, or binding;

persist state;

silently provide a fallback renderer.

The preferred implementation is a pure controlled component. If a hook is needed for its own DOM lifecycle, that hook remains in surfaceInteraction/projection/** and follows the same import boundary.

§6.4 Temporary LegacyProjectionHostAdapter

The adapter is explicit compatibility code and must carry a deletion-owner comment naming BLD-SIH-03b or the later Plan recomposition slice.

It retains these current responsibilities without semantic change:

read current legacy projection publication and provider state;

determine whether the current legacy publication is host-capable;

pass current active state and guarded actions to the neutral host;

parse requested Tool ID from query/hash;

parse explicit requested session;

retain the exact SESSION_AWARE_TOOLS set;

fetch recap artifacts through the existing API;

apply existing numeric filtering and sorting;

cache latest inferred session by exact campaign ID;

capture and compare exact legacy projection surface identity around async lookup;

reject stale lookup completion after surface/campaign replacement or unmount;

update URL exactly as before;

call provider openTool only after current identity validation;

pass current legacy theme to the neutral host;

call existing renderToolProjection and renderContentProjection unchanged;

pass current graph-reference binding, projection state, glance-only flag, and diagnostics payload unchanged;

supply the existing Loading reference and Unknown tool presentation behavior from the current Plan layer.

It must not:

contain toggle/drawer/backdrop/header/nav/body JSX;

install body classes or Escape listeners;

calculate host CSS classes;

own selected projection state;

introduce a renderer registration map;

broaden Plan-only graph authorization;

make Build host-capable;

copy renderer components into the adapter.

§6.5 Host visibility contract

The adapter renders no ProjectionHost when any existing host-disabling condition is true:

no validated legacy projection config
OR projections disabled
OR no configured tools
OR no required current legacy context

This preserves current behavior for inactive routes, Build empty publication, loading, and invalid composition.

The neutral host itself may assume that the adapter has provided at least one navigation item when closed. It must still fail safely if passed an empty list: the toggle may call no action and must never throw.

§6.6 Renderer selection remains unchanged

projectionRegistry.tsx is intentionally excluded from the diff.

The mapping from existing projection IDs to concrete components remains exactly the predecessor mapping, including:

ingest-recap → IngestionModule

statblock → StatblockWorkbenchModule

recap → RecapGraphModule

graph-preview → GraphPreviewModule

graph-gold-review → GraphGoldReviewModule

graph-review-diagnostics → GraphReviewDiagnosticsToolPanel

manual-review → ManualReviewModule

party-registry → PartyRegistryModule

unknown Tool ID → existing Plan empty/unknown presentation

content resolution → PlanReferenceObjectCard

Do not convert this switch into a map, registration, context, plugin, or neutral renderer API in this slice. That is the sole capability of BLD-SIH-03b.

§6.7 CSS ownership and mechanical equivalence

Move only Projection host-shell styling from planSurface.css into surfaceInteraction/projection/projectionHost.css.

The moved scope includes the current visual behavior for:

fixed side toggle;

open toggle state;

backdrop and hidden backdrop;

content-reference backdrop suppression;

host navigation and buttons;

drawer/container positioning and transition;

compact/wide/fullscreen sizes;

header and header actions;

host body scrolling/padding;

neutral host kicker used by the host header.

The new CSS must:

use neutral selectors such as .surface-projection-* or an equally explicit neutral prefix;

contain no .plan-* selector;

preserve the current geometry, z-index, spacing, backdrop, widths, transition, and interaction behavior unless a current bug makes exact copying impossible;

avoid moving Plan card/content/Agent styles;

avoid global selector expansion;

use one neutral body class, recommended surface-projection-open.

planSurface.css must no longer own host selectors such as the old .plan-toolbox*, .plan-projection-container, .plan-projection-compact, .plan-projection-wide, .plan-projection-fullscreen, .plan-projection-header*, or host-body selector. Plan renderer content classes may remain.

§6.8 App mount and singularity

App.tsx must contain one production mount of the temporary adapter and therefore one neutral host shell.

Required shape:

<AgentInteractionProvider>
  <AskPluginSlotProvider>
    {content}
    <LegacyProjectionHostAdapter />
    <AgentInteractionChrome />
  </AskPluginSlotProvider>
</AgentInteractionProvider>

Equivalent naming is allowed only when ownership is equally explicit.

Required singularity proofs:

old AdaptiveProjectionContainer symbol absent from production source;

exactly one production adapter mount;

exactly one production ProjectionHost JSX mount, inside the adapter;

no route-local host mount;

no second provider/context introduced.

§6.9 Lease and stale-operation behavior

The provider remains the lease/action authority. The host receives current guarded callbacks and invokes them; it does not create a lease layer.

The Plan adapter retains the existing extra async protection around latest-session lookup:

capture exact surface identity
→ await recap artifact lookup
→ read current exact surface identity
→ mismatch / unmount => return without URL or openTool mutation
→ exact match => preserve current URL update and openTool behavior

Do not weaken exact identity to label, campaign only, instance key only, or concatenated delimiter key.

Host effect cleanup must guarantee:

open host unmounts or becomes inactive
→ body open class removed
→ Escape listener removed
→ no stale DOM action remains mounted

§6.10 Nano-commit sequence

The Code Agent must implement this PR as a readable nano-commit series. Do not squash or amend away the story while review is active.

Recommended sequence:

Nano commit 1 — canonical type ownership

refactor(ui): move projection runtime types to surface interaction

Create neutral Projection runtime types.

Update provider and compatibility imports.

Remove canonical type definitions from Plan.

No JSX or CSS move.

Typecheck and focused provider tests green.

Nano commit 2 — neutral host shell and styles

refactor(ui): extract neutral projection host shell

Create controlled ProjectionHost and neutral CSS.

Add neutral host component tests.

The existing Plan container may temporarily delegate to it in this commit if needed to keep the tree green.

No URL/session or renderer movement yet.

Nano commit 3 — isolate legacy Plan adapter

refactor(ui): isolate legacy projection host policy adapter

Move current URL/session lookup and renderer orchestration into LegacyProjectionHostAdapter.

Delete Plan-owned host DOM.

Move/rename integration tests.

Preserve behavior and exact stale lookup protection.

Nano commit 4 — switch app mount and enforce boundaries

test(ui): enforce neutral projection host ownership

Switch the one App mount.

Delete the obsolete Plan container files.

Add static boundary/singularity/CSS ownership tests.

Run the complete §7 evidence set.

Review fixes should normally be new focused commits, for example:

fix(ui): preserve projection host escape cleanup
fix(ui): keep stale session lookup lease-scoped

Do not hide a review fix by rewriting an earlier commit unless the reviewer explicitly requests history repair.

Each nano commit must:

express one sentence of the ownership story;

avoid docs changes;

avoid unrelated formatting or cleanup;

be buildable and testable where practical;

never temporarily introduce two production hosts in the committed state.

§6A State and fallback matrix

Observable path

Loading/initializing

Exact success

Ordinary miss

Dependency unavailable

Integrity/contract failure

Stale/superseded

Retry/replay

Host availability

Adapter renders null

One neutral host is available

No publication/tools/context → no host

Same no-host state

Invalid publication → no host, old state already revoked by provider

Old host unmounts and effects clean

Current surface may republish

Tool toggle

No action before host-capable publication

Adapter opens first exact configured ID

Empty nav → no-op

Session lookup failure preserves current no-session behavior

Unknown ID never substituted

Stale async result ignored

Operator may click again

Tool nav

Hidden before host

Exact ID/label/order preserved

Unknown/removed ID no-op via provider

Existing renderer dependencies handle their own state

No first-match or fallback ID

Old button removed with host

Current operator action allowed

URL-requested Tool

Waits for current adapter effect

Exact enabled ID opens

Unknown ID no-op

No current host → no-op

No inferred replacement

Request cannot act through stale identity

Re-evaluated on valid publication

Latest-session inference

Only eligible Plan/Ingest Tool path

Existing latest numeric session used

No records → no session parameter

API failure → no session parameter

No cross-campaign reuse

Exact identity mismatch/unmount → discard

Later operator action may retry

Active Tool drawer

Closed until provider active state

Backdrop/nav/header/body render

No active → closed toggle state

Renderer owns existing unavailable UI

Invalid publication clears active

Old DOM removed

Current action may reopen

Active content drawer

Closed until provider content state

No backdrop/nav; Reference chrome; Expand when glance-only

Missing resolution → existing loading presentation

Missing binding remains existing fail-closed card behavior

No fallback renderer

Old content cannot survive lease replacement

Existing resolver retry only

Escape/backdrop/close

No listener while closed

Current guarded close called once

No active → no-op

Not applicable

No second close owner

Listener removed on unmount

Current operator action allowed

Theme

No host styles applied

Current tokens/theme ID applied

Missing theme → default variables

Not applicable

Malformed publication already fails upstream

Old style disappears with host/update

Current publication may update

Concrete renderer

No render while inactive

Existing hardcoded registry result

Existing unknown Tool presentation

Existing module behavior

No catalog fallback

Stale host unmounted

Existing module retry only

No new fallback source is introduced.

§6B Identity matrix

Situation

Required matching rule

Ambiguity behavior

Fallback permitted?

Persistence consequence

Active surface

Exact predecessor surface identity pair

Mismatch fails stale async completion

No

None

Surface lease

Existing SIH-02 exact token

Old callbacks/cleanup remain no-op

No

None

Tool navigation item

Exact configured Tool ID

Unknown ID no-op; never first-win

No

None

Active projection

Exact kind + key under current lease

Provider clears invalid/removed target

No

None

Display label/title

Display only; never identity

Cannot select or preserve by label

No

None

Projection size

Exact compact / wide / fullscreen value

Invalid value rejected upstream

No

None

Campaign session cache

Exact campaign ID key plus exact surface identity recheck before use

No cross-campaign substitution

No

Transient only

Graph object/reference

Existing graphReference exact identity semantics

Unchanged predecessor ambiguity behavior

Existing named predecessor behavior only

Unchanged

CSS class

Presentation only

Never used as runtime identity

No

None

This slice introduces no new durable identity, alias, rename, deletion, or rebinding behavior.

§6C Persistence and replay matrix

Not applicable — BLD-SIH-03a is a transient ownership refactor. It introduces no
stored format, localStorage key, URL persistence contract, migration, save/reload
behavior, or process-restart state. Existing URL mutation performed during Tool
navigation is preserved exactly and remains Plan adapter behavior, not new host
persistence.

Required negative proof:

no new localStorage use under surfaceInteraction/projection/**;

no projection host fields added to Agent threads or stored state;

remount starts from provider/current URL behavior exactly as before;

no callbacks, renderer nodes, config objects, or theme objects are serialized.

§6D Predecessor-to-consumer mapping

Grounding source

main@917b9d5dff3985b3664aa274eafad7eacb776658

apps/live-control-ui/src/planSurface/projection/AdaptiveProjectionContainer.tsx
apps/live-control-ui/src/planSurface/projection/projectionContext.tsx
apps/live-control-ui/src/planSurface/projection/projectionRegistry.tsx
apps/live-control-ui/src/planSurface/types.ts
apps/live-control-ui/src/agentInteraction/AgentInteractionProvider.tsx
apps/live-control-ui/src/App.tsx

Predecessor field or outcome

Real shape and optionality

Consumer after this slice

Transformation

Required proof

ProjectionKind

"tool" | "content"

neutral surfaceInteraction/projection/types.ts

Exact alias/definition move

Typecheck + boundary test

ProjectionSize

"compact" | "wide" | "fullscreen"

neutral runtime type

Exact alias/definition move

Typecheck + size component test

ActiveProjection

{ kind, key, size, title, glanceOnly? }

provider and neutral host

Exact shape move; no field change

Provider regression + host tests

projectionContainerClass(size)

Plan function returning Plan CSS classes

neutral host internal class selection

Preserve size behavior with neutral class names

Host size tests

isOpen = Boolean(active)

controlled by provider state

neutral host

Direct

Open/closed tests

document.body.classList.toggle("plan-toolbox-open", isOpen)

global host-open indicator

neutral host with neutral class

Mechanical class rename and exact cleanup

Host effect tests + CSS boundary

Escape listener

only while open

neutral host

Direct move

Host Escape test

Tool backdrop

open Tool only

neutral host

Direct move

Tool/content host tests

content nav hidden

active kind content

neutral host

Direct move

Content host test

config.theme

optional legacy theme/tokens

adapter → neutral host props

Copy current values only

Adapter integration test

config.tools

ordered legacy IDs/labels/sizes

adapter nav items + provider active state

Preserve order/labels; no neutral registry

Integration test

requestedToolFromLocation

exact query/hash parser

legacy adapter

Move without semantic change

URL tests

requestedSessionFromLocation

exact trimmed query session

legacy adapter

Move without semantic change

URL/session tests

SESSION_AWARE_TOOLS

exact current set

legacy adapter

Move unchanged

Session lookup tests / diff review

recap artifact lookup/filter/sort

current API and helper functions

legacy adapter

Move unchanged

Same-surface and stale-campaign tests

exact stale identity comparison

sameProjectionSurfaceIdentity before/after await

legacy adapter

Preserve

Stale async test

renderToolProjection

hardcoded Plan registry

legacy adapter

Call unchanged

Existing Tool integration tests

renderContentProjection

Plan reference card and binding policy

legacy adapter

Call unchanged

Existing content/binding tests

provider openTool/close/expandContent

current lease-guarded actions

adapter props → neutral host

Pass through; no wrapper authority

Provider regression + host click tests

App mount

one <AdaptiveProjectionContainer />

one <LegacyProjectionHostAdapter /> containing one neutral host

Replace exact mount

Boundary/singularity test

host CSS in planSurface.css

.plan-toolbox* / .plan-projection-*

projectionHost.css neutral selectors

Mechanical move and rename

CSS boundary test + component tests

§7 Verification ownership map and commands

Every guarantee must be proved at the boundary that owns it.

Guarantee

Owning boundary

Command or scenario

Expected evidence

Canonical runtime types no longer belong to Plan

Type/import boundary

projectionBoundaries.test.ts + TypeScript build

Provider/shared imports resolve through neutral owner; Plan contains no canonical definitions

Neutral host imports no domain policy or concrete renderer

Source boundary

projectionBoundaries.test.ts

No Plan/Build/Ingest/API/graph/registry imports in neutral host directory

Exactly one production host mount remains

App/source boundary

projectionBoundaries.test.ts

One adapter mount, one neutral host mount, zero old container symbols

Host toggle/open/close/backdrop/nav/header/body behavior

Neutral component

ProjectionHost.test.tsx

DOM and callbacks behave equivalently

Escape and body-open cleanup

Neutral component lifecycle

ProjectionHost.test.tsx

Listener/class active only while open and removed on unmount

compact/wide/fullscreen behavior

Neutral component

ProjectionHost.test.tsx

Exact neutral size class per active size

content glance behavior

Neutral component

ProjectionHost.test.tsx

nav/backdrop hidden; Expand present only when allowed

Theme transfer and replacement

Adapter + neutral component

LegacyProjectionHostAdapter.test.tsx

Current theme applied; old theme absent after replacement

No host for inactive/Build/invalid publication

Adapter/provider integration

LegacyProjectionHostAdapter.test.tsx

No toggle/drawer/body class

Plan URL/session behavior unchanged

Plan adapter integration

LegacyProjectionHostAdapter.test.tsx

exact query updates and inferred session behavior

Stale async lookup cannot act on replacement surface

Plan adapter/provider sequence

LegacyProjectionHostAdapter.test.tsx

no stale URL or open state mutation

Existing Tool renderer behavior unchanged

Plan adapter/registry integration

legacy adapter tests + Plan/Graph Review suites

Existing components render for existing IDs

Existing content renderer/binding behavior unchanged

Plan adapter/graph-reference integration

legacy adapter tests + projection binding suites

Existing card and fail-closed binding behavior

Provider lease behavior unchanged

Provider

existing AgentInteractionProvider.test.tsx

same focused suite green without provider behavior edits

Plan and Graph Review remain equivalent

Owning surface components

existing Plan/Graph Review tests

No regression

No persistence introduced

Source scan

boundary test

no localStorage/storage import in new neutral package

Production build remains valid

Frontend build

npm run build

TypeScript and Vite build clean

Run from apps/live-control-ui unless otherwise noted:

npx vitest run \
  src/surfaceInteraction/projection/ProjectionHost.test.tsx \
  src/surfaceInteraction/projection/projectionBoundaries.test.ts \
  src/planSurface/projection/LegacyProjectionHostAdapter.test.tsx

npx vitest run \
  src/agentInteraction/AgentInteractionProvider.test.tsx \
  src/planSurface/projection/projectionBindings.test.tsx \
  src/planSurface/PlanSurfaceShell.test.tsx \
  src/planSurface/graphReviewWorkbench/GraphReviewWorkbenchModule.test.tsx \
  src/App.surfaceInteraction.test.tsx

npx vitest run src/surfaceInteraction src/agentInteraction src/graphReference

npm run build

From repository root:

git diff --check

git diff --name-only <implementation-base>...HEAD

git diff --stat <implementation-base>...HEAD -- \
  apps/live-control-ui/src/surfaceInteraction/projection \
  apps/live-control-ui/src/planSurface/projection \
  apps/live-control-ui/src/planSurface/types.ts \
  apps/live-control-ui/src/planSurface/planSurface.css \
  apps/live-control-ui/src/agentInteraction/AgentInteractionProvider.tsx \
  apps/live-control-ui/src/agentInteraction/agentInteractionTypes.ts \
  apps/live-control-ui/src/App.tsx

Minimal live proof

Not required as a merge gate because this slice intends no visible behavior change and the owning interaction paths are covered by component/integration tests. If a local server is already available, the smallest optional smoke is:

Open Plan → open Recap → switch Tool → open a reference → Expand → Close →
switch to Build and confirm no Projection toggle → return to Plan.

Do not build new diagnostics, screenshots, fixtures, or a dedicated proof surface for this optional smoke.

Baseline failure protocol

For every required command that fails on the implementation base:

Command

Base result

Head result

New failure introduced?

Acceptance effect

Waiver

<exact command>

<exact result>

<exact result>

Yes / No

Blocked unless proven baseline-only and explicitly accepted

<none or explicit operator waiver>

Rules:

Compare the same command on base and head.

Preserve exact failure output.

Do not report a failing gate as green.

Distinguish Code-Agent-local results, reviewer-rerun results, CI, and optional manual observation.

A new failure blocks merge.

A baseline failure that prevents owning-boundary proof requires explicit operator waiver.

§8 Required Code Agent handback

The Code Agent must deliver a handback in the BLD — DungeonBuddy Build Code Agent conversation. It may also be posted as a top-level PR comment. The PR description is not the handback and is not reviewed as authority.

Required fields:

Slice: BLD-SIH-03a — Neutral Projection Host Shell.

Branch name.

Implementation base SHA containing this handoff.

Head SHA.

Nano-commit list in order, with one sentence explaining each commit.

Actual changed paths.

Focused diff stat.

Paths outside §4 and bounded exception: none or exact stop report.

Every §7 command and exact result.

Evidence provenance for every result: Code-Agent-local, independently rerun, CI, or optional manual.

Baseline failures with base/head comparison.

Operator waivers: none or exact waiver.

Stop conditions encountered: none or exact report.

Deviations from this handoff: none or exact report.

Confirmation that projectionRegistry.tsx and concrete renderer mapping were not changed.

Confirmation that Build gained no projection capability.

Confirmation that Tool/Edit hosts were not extracted.

Confirmation that no persistence or new provider was introduced.

Confirmation that the implementation preserved the handoff without compressing or omitting constraints.

A PR body may contain nothing more than a locator to the branch or handback. Reviewers must not infer missing evidence from prose in a PR description.

§9 Acceptance rubric

The reviewer accepts only when every item is true:

The review explicitly identifies BLD-SIH-03a, branch, base SHA, and head SHA.

Exactly one app-level Projection host remains — proved by boundary test and source inspection.

Host DOM and lifecycle live under surfaceInteraction/projection/** — proved by path and import inspection.

Canonical ActiveProjection / ProjectionSize ownership moved out of Plan — proved by type/import boundary tests and build.

Neutral host imports no Plan, Build, Ingest, API/session, graph policy, binding, diagnostics, or concrete renderer code.

Temporary Plan-owned adapter contains policy/orchestration only and no host DOM/effects/CSS class calculation.

URL Tool selection and latest-session inference remain in the adapter and behave exactly as before.

Exact stale-surface rejection still guards async session lookup.

Renderer selection remains the unchanged Plan registry; no catalog/registration API landed.

Tool and content rendering remain behavior-equivalent.

Inactive, Build-empty, and invalid publications render no host and clear host effects.

Tool/content backdrop, nav, header, Expand, Close, Escape, and size behavior pass neutral host tests.

Host CSS has neutral ownership and no .plan-* selectors; Plan CSS no longer owns host shell selectors.

Provider runtime behavior is unchanged; only canonical type imports changed.

No route-local host, second provider, second token, or second selected-state owner exists.

No Build search/inspect/insert capability exists.

No Tool/Edit host extraction exists.

No persistence, router rewrite, or visual redesign exists.

Every changed path is in §4 or the bounded test-only exception.

Every required §7 command is truthfully reported with provenance.

New failures are zero; unresolved baseline gates have explicit operator waiver.

Nano commits tell the ownership story and review fixes remain discrete.

BLD-SIH-03b remains unimplemented and explicitly named as the renderer/catalog successor.

§10 Reviewer protocol — Build lane

§10.1 Resolve and state the exact review target

Before reading the diff, the reviewer must write:

Reviewing BLD-SIH-03a — Neutral Projection Host Shell
Branch: <head branch>
Base: <base SHA>
Head: <head SHA>
Prior reviewed head: <SHA or none>

Use the branch and SHA to locate the PR. Do not use the PR number or PR description as the work identity or merge contract.

§10.2 Review sources

Review in this order:

This handoff.

Actual base-to-head commit list and nano-commit story.

Actual changed paths and diff.

Owning production files.

Owning tests and independently rerun evidence.

Prior review finding ledger.

PR description only as non-authoritative incidental text, if read at all.

§10.3 Finding standard

Reviews must capture as many changes as are required to move the slice to merge. Do not intentionally withhold known findings for later rounds.

Every actionable finding must contain:

Priority: P0 / P1 / P2
Path and symbol:
Invariant violated:
Concrete falsifying sequence or observable consequence:
Discrete required code fix:
Discrete required test or proof:
Successor/scope impact: none, or stop condition

A finding is not sufficiently specific when it says only:

“this seems coupled”;

“add more tests”;

“consider moving this”;

“clean this up”;

“the architecture is wrong.”

The reviewer must name the exact coupling, behavior, path, and merge-enabling correction.

§10.4 Review breadth

Review the whole invariant, not just the latest changed lines. In each round, audit:

singular host ownership;

neutral import boundary;

exact type ownership;

host lifecycle cleanup;

Tool versus content behavior;

theme replacement;

stale session lookup;

unchanged renderer mapping;

provider behavior stability;

CSS ownership;

changed-path scope;

successor capabilities remaining false.

There is no numerical finding limit. A review with multiple discrete fixes is preferred over a sequence of drip-fed discoveries.

§10.5 Verdict language

Use one of:

REQUEST CHANGES — <count> merge blockers / required corrections
APPROVE — no merge-blocking defects found; evidence caveats listed separately

An approval may note missing hosted CI as an evidence caveat when the required tests were independently rerun locally. It must not call author-reported evidence independent.

§10.6 Re-review ledger

Begin every re-review with:

Prior finding

Claimed fix commit

Owning path/test

Verified?

New consequence?

<finding>

<SHA>

<paths>

Yes / No

<none or exact consequence>

Then:

verify every prior finding;

rerun the whole invariant;

inspect all commits since the prior reviewed head;

check that a fix did not create new ownership, identity, state, CSS, or compatibility defects;

add every newly discovered discrete fix;

update the head SHA in the review target statement.

Do not review only the literal line changed in response to a comment.

§10.7 Merge movement

A review request must explain the shortest concrete path to merge:

To reach merge:
1. <specific fix>
2. <specific proof>
3. <specific rerun>

When there are many fixes, list them all. The purpose of review is to move the implementation to a trustworthy merge, not to preserve a small comment count.

§11 Code Agent operating instructions

Work only in the BLD — DungeonBuddy Build Code Agent conversation.

Start from the exact immutable origin/main SHA containing this handoff.

Create/use branch bld/sih03a-neutral-projection-host-shell or an unmistakably equivalent bld/ branch.

State BLD-SIH-03a at the beginning of every implementation handback and review request.

Implement in nano commits following §6.10.

Keep the PR description minimal; do not spend implementation time maintaining it as a contract.

Do not add docs sync to the code PR.

Do not change renderer selection.

Do not absorb BLD-SIH-03b.

Do not create a second host/provider/context.

Run §7 after each meaningful boundary move and at final head.

When review asks for changes, add focused fix commits and return a finding-by-finding ledger.

If a stop condition occurs, report it in the Code conversation before changing scope.

Stop conditions

Stop and report rather than expanding the slice when any of the following is discovered:

The current host cannot be split without changing renderer selection.

A neutral host requires importing Plan/Build/Ingest policy or a concrete renderer.

Provider runtime behavior must change rather than only type imports.

A second provider/context/token is required.

A production path outside §4 is required.

Build must gain a Tool or Projection to make the extraction useful.

Existing URL/session behavior cannot be preserved without a new public contract.

Current renderer mapping differs materially from the predecessor inventory.

CSS cannot be moved without a visible redesign or unrelated Plan style changes.

A required owning-boundary test is failing on base and cannot prove the invariant without operator waiver.

The implementation base does not contain the required SIH-01/SIH-02 contracts.

Another active branch has materially changed the same host seam.

The Code Agent is asked to update roadmaps/trackers in the implementation PR.

The Code Agent is asked to use a PR description as authority instead of this handoff and actual evidence.

Use this report:

Stop condition:
Why BLD-SIH-03a cannot absorb it:
Affected invariant:
Affected observable paths:
Required production path outside scope:
New contract or capability discovered:
Proposed successor or amended handoff:
Operator decision required:

The Code Agent must not resolve a stop condition by silently widening the diff.

Final dispatch check

Work is labeled BLD-SIH-03a everywhere operator-facing.

Design conversation and Code conversation names are explicit.

Design → Code direction is explicit.

PR number is intentionally irrelevant.

PR description is explicitly non-authoritative.

Documentation synchronization is explicitly separate.

Mission is one independently useful ownership transfer.

Merge-ready invariant separates neutral shell from Plan policy.

Observable paths are inventoried.

Exact production/test allowlist is present.

Renderer registry is explicitly excluded.

Nano-commit sequence is explicit.

Review may request all required merge fixes in one or more complete rounds.

Review findings require discrete fixes and proofs.

Re-review begins from a finding ledger and prior head SHA.

BLD-SIH-03b and later Build capabilities remain false.

Dispatch statement

BLD — DungeonBuddy Build Design Agent dispatches BLD-SIH-03a to
BLD — DungeonBuddy Build Code Agent.

Move the singular Projection host shell, host CSS identity, and canonical shared
runtime types out of Plan ownership. Preserve current Plan/Ingest policy and
renderer selection behind an explicit temporary adapter. Work in nano commits,
keep docs sync separate, and treat this handoff plus actual code/evidence—not the
PR number or PR description—as the implementation and review contract.
