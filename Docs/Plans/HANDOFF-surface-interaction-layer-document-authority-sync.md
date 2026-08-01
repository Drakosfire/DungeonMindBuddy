---
pr_body_template: |
  ## Outcome
  DungeonBuddy's active surface documentation now distinguishes the independent
  Canvas work object, the shared Surface Interaction Layer hosts, and Surface
  domain publication.

  ## Merge-ready invariant
  Canvas owns the active work object; shared Nav, Agent, Tool, Edit, and Projection
  hosts own interaction infrastructure; Surfaces publish domain capabilities and
  do not own those hosts.

  ## Scope and verification
  Base: `5744477839b9e57b60c77554a167405c8c7df2eb`; documentation-only paths in
  §5 plus bounded-discovery `Backlog-DONE.md`; static authority scans, ancestry,
  link validation, fence validation, and `git diff --check`.

  ## Evidence produced
  Automated and manual results are recorded in §10 below. Runtime behavior is
  unchanged; runtime implementation is a named successor.

  ## Gaps, waivers, and stop conditions
  One pre-existing Cursor transcript token in `Backlog.md` is not a filesystem
  link. All new relative links resolve; historical evidence is preserved behind
  banners.
---

# HANDOFF — Surface interaction-layer document authority synchronization

**Created:** 2026-08-01
**Status:** COMPLETE — documentation-only; no commit or push in this slice.
**Canonical handoff path:** `Docs/Plans/HANDOFF-surface-interaction-layer-document-authority-sync.md`
**Implementation branch:** `docs/surface-interaction-layer-authority-sync`
**Authoring and implementation base:** `5744477839b9e57b60c77554a167405c8c7df2eb`

> This is a documentation-management slice. It changes no runtime behavior,
> TypeScript contracts, APIs, schemas, storage, graph state, or UI implementation.
> Its purpose is to make the next implementation slice dispatchable from one
> coherent authority model.

---

## §0 Capability decomposition decision

| Candidate outcome | Decision |
|---|---|
| Create one neutral architecture authority for Canvas versus shared interaction-bar ownership | **Include** |
| Create one execution plan for hoisting Plan's proven interactions and composing Build | **Include** |
| Synchronize active architecture, design, roadmap, tracker, product-story, and backlog docs | **Include** |
| Add truthful merged/completed banners to predecessor handoffs | **Include** |
| Mark superseded runbook/surface documents historical without rewriting their evidence | **Include** |
| Implement shared Nav/Agent/Tool/Edit hosts or a `SurfaceInteractionManifest` type | **Named successor** |
| Enable Build graph-reference search, insert, save/reload, and reopen UX | **Named successor** |
| Recompose Plan or implement Play | **Named successor** |
| Rename or delete current `*SurfaceShell`, `*Toolbar`, or `*EditBar` code | **Out of scope** |

**Selected capability:** Synchronize DungeonBuddy's documentation authority around
one neutral surface-composition model so the next implementation agent can hoist
shared interaction bars and compose Build without inferring ownership from
contradictory Plan-, Build-, and runbook-era documents.

The included rows share one invariant: a new authority without synchronization
would create another competing document, while synchronization without a neutral
authority would leave no stable center. Status banners and historical tombstones
are therefore part of the same documentation guarantee.

**Named successors**

1. Shared interaction-layer implementation hoist.
2. Build first-class composition over Canvas plus shared bars.
3. Plan recomposition without behavioral regression.
4. Play composition and runtime-specific contributions.
5. Runtime naming or file-layout cleanup.

---

## §1 Mission

DungeonBuddy's document set can direct one unambiguous surface-composition
implementation so that Canvas remains an independent work primitive while Plan,
Build, and Play publish into shared Nav, Agent, Tool, and Edit interaction hosts
they do not own.

**Merge-ready invariant**

```text
Across every active authority document:

Canvas owns the active work object and its document/runtime authority.

The shared interaction layer owns Nav Bar, Agent Bar, Tool Bar, Edit Bar,
and the shared Projection Pane.

A Surface owns domain semantics, policy, authorization, context, and typed
registrations into those primitives; it does not implement or privately own them.
```

**Mission falsification test**

This is not one documentation slice if it must also change React ownership or
mounting, introduce a runtime `SurfaceInteractionManifest` type, enable Build
reference/search/project behavior, move Plan controls at runtime, alter graph or
workspace-document authority, redesign the visual layout of a bar, or define
complete Play behavior.

---

## §2 Context, authority, and boundaries

### Predecessor facts

The following facts are verified from Git and GitHub:

| Capability | Merged PR | Merge commit |
|---|---:|---|
| Build-first shared Markdown Canvas | #426 | `7d98074d434a5310d21d4fe645e497789e0a3114` |
| App-scoped projection host in `AgentInteractionProvider` | #441 | `4ec74045f0b7878434e911fa73c407727d3e958c` |
| Surface-neutral existing-object `graphReference` lifecycle | #431 | `130104442b0ac7ad9a56c7e744014f1b8d56ad62` |

### Authority table

| Field | Authority |
|---|---|
| Shared interaction ownership | `Docs/Design/ARCHITECTURE-surface-interaction-layer.md` |
| Canvas authority | `Docs/Design/DESIGN-shared-markdown-canvas-surface-composition.md` |
| Plan domain composition | `Docs/Design/ARCHITECTURE-plan-surface-toolbox.md` |
| Projection/Agent predecessor | PR #441 and `HANDOFF-r10a-app-scoped-projection-host-lift.md` |
| Neutral graph-reference predecessor | PR #431 and `HANDOFF-pr431-surface-neutral-graph-reference-loop.md` |
| Build product story | `Docs/Reports/MAGIC-MOMENT-BUILD-SURFACE-2026-07-30.md` |
| Graph authority | `Docs/Design/ARCHITECTURE-campaign-supergraph.md` |
| Execution sequence | `Docs/Plans/PLAN-surface-interaction-hoist-build-first.md` |
| Repository rules | `AGENTS.md`, `.cursor/rules/external-agent-pr-loop.mdc`, and the canonical handoff template |
| Base revision | `5744477839b9e57b60c77554a167405c8c7df2eb` |

### Authority precedence

```text
1. Operator-approved ownership decision frozen in this handoff
2. Canonical repository architecture and current merged contracts
3. Neutral interaction-layer architecture produced by this slice
4. Updated active design/roadmap/tracker documents
5. Current implementation and tests as evidence of present state
6. Historical handoffs, archived roadmaps, reports, and prototypes
7. Chat summaries
```

Stop before editing if the base lacks the three predecessor merges, a newer
merged document-authority PR conflicts with this model, repository rules require
another canonical location, a separate active authority was omitted, or a
runtime change would be needed to make a documentation statement true.

---

## §3 Normative ownership model to encode

### 3.1 Three architectural layers

```text
Canvas primitives
  The object the user is directly working on and the authority governing it.

Shared interaction layer
  Nav Bar · Agent Bar · Tool Bar · Edit Bar · Projection Pane.

Surface composition
  Selects a Canvas and publishes typed context, capabilities, tools, commands,
  navigation, terminology, and policy into shared hosts.
```

### 3.2 Canvas

Canvas is an independent primitive, not a container for all surface UI. It owns
work-object identity, revision/runtime identity, local editor state, selection,
dirty/clean/conflict/recovery state, document-bound commands, and save/commit
authority where applicable.

Canvas does not own global navigation, Agent or Tool or Edit Bar hosts, the
Projection Pane, tool catalog presentation, graph identity/writes, or
surface-wide capability selection. `MarkdownCanvasSession` and `MarkdownCanvas`
remain valid primitives and are not collapsed into a workbench.

### 3.3 Nav Bar

Nav Bar is shared application navigation infrastructure. It owns routes, named
surfaces, current location, and shared navigation affordances. A Surface may
publish identity, destinations, labels, or navigation contributions; it does
not render a private Nav Bar.

### 3.4 Agent Bar and Projection Pane

Agent Bar and Projection Pane are app/user-scoped infrastructure owned by the
Agent Interaction layer. They own thread and composer presentation, pane and
projection state, back stack where implemented, projection hosting, continuity
across surface changes, and exact surface-lease authorization. A Surface
publishes context and capabilities; it does not own the host or thread state.

### 3.5 Tool Bar

Tool Bar owns presentation and grouping of workflows, enabled/loading states,
launch through the shared projection host, and common accessibility behavior.
A Surface publishes registrations and typed parameters. **Find existing object**
is a Tool Bar capability. Insertion is a tool action invoking an explicit
Canvas/edit command; it is not the defining responsibility of Edit Bar.

### 3.6 Edit Bar

Edit Bar presents commands for the current editable work object or selection:
lock/unlock, save/commit/export, undo/redo where supported, selection-scoped
mutations, and dirty/saving/conflict/receipt state. Canvas or the owning domain
capability supplies command authority. Edit Bar does not invent write authority.

### 3.7 Surface

A Surface owns domain meaning and terminology, selected Canvas kind and adapter,
graph lens and admissibility policy, document/runtime admission, tool
registrations, edit-command contributions, navigation contributions, agent
context, authorization boundaries, and surface-specific product rules.

A Surface does not own bar implementations, the projection host, private
graph-reference or document stacks, a private agent thread, or graph identity.

### 3.8 Surface shell / frame

`SurfaceShell` or `SurfaceFrame` may remain a thin layout compositor:

```text
place shared interaction hosts and the selected Canvas in the active layout
```

It must not own tool implementations, edit authority, graph resolution, Agent
state, Canvas state machines, or surface-specific bar branches.

### 3.9 Shared does not mean identical

Plan, Build, and Play may publish different tools, edit capabilities, labels,
lenses, layouts, and authority states. Shared hosts remain recognizable while
each Surface preserves its task-specific interaction contract.

### 3.10 Conceptual publication contract

Use **Surface Interaction Layer** as the architecture term. Use
**`SurfaceInteractionManifest`** only as a conceptual name in diagrams and
examples. Do not add a TypeScript type in this slice.

```ts
interface SurfaceInteractionManifest {
  surfaceId: SurfaceMode;
  context: SurfaceContextPublication;
  canvas: SurfaceCanvasSelection;
  navigation: NavigationContribution[];
  tools: ToolRegistration[];
  editing: EditCapabilityPublication;
  agent: AgentCapabilityPublication;
}
```

The future contract publishes into independently owned hosts; it does not mount
bars.

---

## §4 Observable-path inventory

| Path | Required authority result | Owning boundary |
|---|---|---|
| New implementer reads surface architecture | Canvas, Interaction Layer, and Surface composition are separate | Neutral architecture |
| Build planning | Build publishes into shared hosts; it does not own chrome | Build story + hoist plan |
| Plan maintenance | Plan is a characterized consumer and domain authority | Plan architecture/current-goal docs |
| Agent/projection planning | App-level provider/projection host is landed; remaining chrome is partial | Agent anchor + predecessor handoff |
| Graph roadmap reading | Graph contracts remain graph authority; UI sequencing points across boundary | Graph architecture/roadmap/tracker |
| Successor reads #426/#441/#431 | Merged banners identify completed primitives and successors | Handoff status banners |
| Reader follows old runbook/surface design | Historical documents cannot override active authority | Historical banners |
| Backlog grooming | Canvas item is archived; one shared-interaction successor is READY | Backlog / Backlog-DONE |
| Code reader | Current runtime is distinguished from target ownership | Active authority docs |

---

## §5 Expected changed-path allowlist

### Create

- `Docs/Design/ARCHITECTURE-surface-interaction-layer.md`
- `Docs/Plans/PLAN-surface-interaction-hoist-build-first.md`
- `Docs/Plans/HANDOFF-surface-interaction-layer-document-authority-sync.md`

### Active authority corrections

- `Docs/Design/ARCHITECTURE-plan-surface-toolbox.md`
- `Docs/Design/DESIGN-shared-markdown-canvas-surface-composition.md`
- `Docs/Plans/PLAN-shared-markdown-canvas-build-first.md`
- `Docs/Reports/MAGIC-MOMENT-BUILD-SURFACE-2026-07-30.md`
- `Docs/Design/DESIGN-plan-surface-session-prep-current-goal-2026-07.md`
- `Docs/Design/ANCHOR-plan-surface-agent-interaction.md`
- `Backlog.md`
- `Docs/Plans/HANDOFF-build-stay-on-build-dogfood-after-mc02.md`
- `Docs/Design/ARCHITECTURE-campaign-supergraph.md`
- `Docs/Roadmaps/ROADMAP-campaign-supergraph.md`
- `Docs/Plans/PR-TRACKER-campaign-supergraph.md`
- `Docs/Design/STATUS-world-graph-continuity-spine.md`

### Status and forwarding corrections

- `Docs/Plans/HANDOFF-pr426-build-first-markdown-canvas.md`
- `Docs/Plans/HANDOFF-r10a-app-scoped-projection-host-lift.md`
- `Docs/Plans/HANDOFF-pr431-surface-neutral-graph-reference-loop.md`
- `Docs/Plans/ROADMAP-build-surface-worldbuilding-ingest.md`
- `Docs/Plans/PLAN-build-surface-worldbuilding-ingest-pr-slices.md`
- `Docs/Reports/HERMES-PHASE-0-UI-CLEANUP-MAP.md`

### Historical banners only

- `Docs/Design/DESIGN-play-mode-runbook-product-direction.md`
- `Docs/Plans/DESIGN-session-runbook-command-surface.md`
- `Docs/Design/DESIGN-runbook-roadmap-and-session-ingestion.md`
- `Docs/Plans/README-c2-live-control-ui.md`
- `Docs/Plans/HANDOFF-self-continuity-plan-toolbar-ingestion-design.md`
- `.cursor/plans/plan-surface-toolbox_5034ad28.plan.md`

`Backlog-DONE.md` was added as a bounded-discovery path because the repository
backlog rule requires a terminal entry to move as a whole block when it leaves
the active backlog. No other bounded-discovery paths were required.

Explicitly out of scope: runtime code, tests, schemas, fixtures, generated
outputs, graph data, corpus files, secrets, UI styling, routes, graph authority,
workspace-document authority, reference schema, agent behavior, tool
implementations, and all pre-existing unrelated untracked paths.

---

## §6 Required content of the two new authorities

`ARCHITECTURE-surface-interaction-layer.md` must remain the neutral authority
with status/scope, vocabulary, the three-layer diagram, ownership and state
tables, conceptual publication model, current landed/partial/target mapping,
interaction contracts, Plan/Build examples, migration/demolition principles,
non-goals, and graph/workspace authority boundaries.

`PLAN-surface-interaction-hoist-build-first.md` must remain the execution
sequence:

```text
SI-00 documentation authority sync
  → SI-01 characterize Plan interaction contributions
    → SI-02 hoist shared Tool/Edit publication and hosts
      → SI-03 recompose Plan without regression
        → SI-04 compose Build World Reference Loop
          → SI-05 dogfood and refine shared interaction grammar
            → Play composition later
```

It must preserve the boundaries: characterize before moving; one host per bar;
Canvas remains independent; Plan is not the shared API; Build does not own bars;
Build is search → inspect → insert → save → reload → reopen; extraction
inspection is a separate tool capability; graph writes remain separate.

---

## §7 Editing rules and semantic traps

1. Preserve Plan's product lessons while reassigning ownership to shared hosts.
2. Do not overcorrect into a monolithic workbench or universal SurfaceShell store.
3. Do not claim runtime implementation that has not landed; label primitives,
   transitional implementation, target ownership, and named successors.
4. Keep graph identity, write authority, source admission, graph review, and
   statblock authority unchanged.
5. Historical documents preserve evidence; banners correct authority without
   rewriting old experiments or PR bodies.
6. Prefer `Canvas primitive`, `Surface Interaction Layer`, `shared interaction
   host`, `Surface composition`, and `publishes/registers/contributes`.
7. Avoid current target language such as `surface-owned toolbar`, `Build
   toolbar` as owner, `Plan Agent Bar` as durable host, or `SurfaceShell owns
   the regions`.

---

## §8 Verification and evidence contract

Before editing, `HEAD` was the required base and the three predecessor SHAs
were ancestors. After editing, rerun:

```bash
git rev-parse HEAD
git merge-base --is-ancestor 7d98074d434a5310d21d4fe645e497789e0a3114 HEAD
git merge-base --is-ancestor 4ec74045f0b7878434e911fa73c407727d3e958c HEAD
git merge-base --is-ancestor 130104442b0ac7ad9a56c7e744014f1b8d56ad62 HEAD
git diff --name-only
git diff --check
```

Targeted active-document scans must cover Build-nebulous/not-in-scope claims,
future provider claims, `blocked on #431`, queued MC-02a, immediate Build-local
MC-02b wiring, nonexistent UI package claims, SurfaceShell bar ownership, and
Find existing assigned to Edit Bar. Historical matches must be bannered and
reported, not hidden.

Positive scans must cover Canvas primitive, Surface Interaction Layer, shared
Tool/Edit/Agent Bar, Surface composition, publish/register/contribute, Build
does not own, and Plan characterized consumer.

Validate relative Markdown links in changed Markdown files, check balanced
fences, and inspect the document matrix. Runtime tests are not required because
no runtime files changed.

---

## §9 Acceptance criteria

1. The neutral architecture and hoist plan exist and are linked.
2. Plan architecture is demoted to Plan composition authority.
3. Canvas remains independent and bars are not Canvas-owned slots.
4. Build publishes into shared bars; Find Existing is Tool Bar.
5. Agent/projection documentation says the app-level host is landed.
6. #426, #441, and #431 handoffs have truthful merged banners and successors.
7. Graph documents remain graph authorities and only cross-link UI sequencing.
8. Historical documents cannot override active authority.
9. Backlog contains one actionable shared-interaction successor and the completed
   Canvas item is archived.
10. No runtime files changed and all changed-document links resolve.
11. No active document simultaneously gives a Surface bar ownership and shared
   infrastructure ownership without an explicit historical banner.

---

## §10 Implementation handback

**Actual base/head:** `5744477839b9e57b60c77554a167405c8c7df2eb` /
uncommitted documentation changes on `docs/surface-interaction-layer-authority-sync`.

**PR:** Not opened; commit and push are explicitly deferred to the operator.

**Changed paths:** the 27 allowlisted paths above plus bounded-discovery
`Backlog-DONE.md`; no runtime, corpus, graph, or unrelated untracked path changed.

**Document matrix**

| Path | Classification | Change |
|---|---|---|
| `Docs/Design/ARCHITECTURE-surface-interaction-layer.md` | Canonical | New neutral shared-chrome authority |
| `Docs/Plans/PLAN-surface-interaction-hoist-build-first.md` | Canonical | New SI-00–SI-05 composition sequence |
| `Docs/Plans/HANDOFF-surface-interaction-layer-document-authority-sync.md` | Handoff | Contract plus truthful completion handback |
| `Docs/Design/ARCHITECTURE-plan-surface-toolbox.md` | Canonical, demoted | Plan domain authority; publishes, does not own bars |
| `Docs/Design/DESIGN-shared-markdown-canvas-surface-composition.md` | Canvas authority | Independent Canvas and shared registration boundary |
| `Docs/Plans/PLAN-shared-markdown-canvas-build-first.md` | Prerequisite plan | MC-01/R10a/MC-02a landed; successors routed to SI plan |
| `Docs/Reports/MAGIC-MOMENT-BUILD-SURFACE-2026-07-30.md` | Product story | Build publishes; Find existing is Tool Bar |
| `Docs/Design/DESIGN-plan-surface-session-prep-current-goal-2026-07.md` | Plan product authority | Contribution map and no host ownership |
| `Docs/Design/ANCHOR-plan-surface-agent-interaction.md` | Surface reference | #441/#431 landed; SI sequence |
| `Backlog.md` | Active backlog | Canvas item retired; SI successor READY |
| `Backlog-DONE.md` | Backlog archive | Completed Canvas item moved as required |
| `Docs/Plans/HANDOFF-build-stay-on-build-dogfood-after-mc02.md` | Named successor | #431 gate cleared; SI-04 is next |
| `Docs/Design/ARCHITECTURE-campaign-supergraph.md` | Graph authority | Cross-boundary UI pointer only |
| `Docs/Roadmaps/ROADMAP-campaign-supergraph.md` | Graph roadmap | Cross-boundary UI pointer only |
| `Docs/Plans/PR-TRACKER-campaign-supergraph.md` | Graph tracker | Cross-boundary UI pointer only |
| `Docs/Design/STATUS-world-graph-continuity-spine.md` | Graph status | Cross-boundary UI pointer only |
| `Docs/Plans/HANDOFF-pr426-build-first-markdown-canvas.md` | Historical handoff | PR #426 merged banner |
| `Docs/Plans/HANDOFF-r10a-app-scoped-projection-host-lift.md` | Historical handoff | PR #441 merged banner |
| `Docs/Plans/HANDOFF-pr431-surface-neutral-graph-reference-loop.md` | Historical handoff | PR #431 merged banner |
| `Docs/Plans/ROADMAP-build-surface-worldbuilding-ingest.md` | Historical forwarder | Links current authorities |
| `Docs/Plans/PLAN-build-surface-worldbuilding-ingest-pr-slices.md` | Historical forwarder | Links current authorities |
| `Docs/Reports/HERMES-PHASE-0-UI-CLEANUP-MAP.md` | Evidence | Transitional Plan-local note |
| `Docs/Design/DESIGN-play-mode-runbook-product-direction.md` | Historical | Non-authoritative banner |
| `Docs/Plans/DESIGN-session-runbook-command-surface.md` | Historical | Non-authoritative banner |
| `Docs/Design/DESIGN-runbook-roadmap-and-session-ingestion.md` | Historical | Non-authoritative banner |
| `Docs/Plans/README-c2-live-control-ui.md` | Historical | Stale package claim banner |
| `Docs/Plans/HANDOFF-self-continuity-plan-toolbar-ingestion-design.md` | Historical | Non-authoritative banner |
| `.cursor/plans/plan-surface-toolbox_5034ad28.plan.md` | Historical | Non-authoritative banner and link repair |

**Static evidence:** predecessor ancestry and GitHub PR merge metadata verified;
active authority scans rerun; relative-link validation and fence checks rerun;
`git diff --check` passed after removing one trailing-whitespace line.

**Named successor:** SI-01 — characterize Plan contributions, then dispatch the
SI-02 implementation handoff with a runtime allowlist and owning-boundary tests.

**Stop conditions, waivers:** no stop condition remains. The worktree retains
pre-existing untracked files untouched. Runtime verification is intentionally
not run for this documentation-only slice.

---

## §11 Demolition declaration

**Replaced model**

```text
SurfaceShell as the apparent owner of Nav/Tool/Edit/Canvas regions,
with Build or Plan assembling their own interaction chrome.
```

**Replacement**

```text
Independent Canvas primitive + shared Surface Interaction Layer + domain Surface composition.
```

No runtime path is deleted in this slice. Historical prose is retained behind
banners. The runtime interaction-hoist successor owns any later removal or
demotion of redundant Plan-/Build-local bar ownership after shared hosts and
registrations are proven.

---

## §12 Final stop conditions

Stop and report instead of completing if the work requires runtime changes, a
stronger operator-approved authority contradicts this model, the document
ledger expands by more than five substantive active documents, graph authority
must change, historical evidence cannot be distinguished from active authority,
the implementation plan bundles host hoist with Plan migration and Play
migration, terminology requires a runtime type change, or link/authority
precedence cannot be made unambiguous.

Do not resolve a stop condition by quietly softening the invariant.
