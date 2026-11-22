# Product surfaces: contributor map

Buddy's Build, Plan and Play surfaces share a UI shell while retaining different
product responsibilities. This map identifies starting points in the repository;
individual routes and deployed releases may support only a subset of the
intended experience. For setup and commands use the [frontend guide](../../apps/live-control-ui/README.md).

## What Buddy brings together

Buddy is a campaign workspace for tabletop GMs: a place to create and organize
material, explore a World in conversation, prepare a session, and use that
preparation at the table. Its capabilities connect across surfaces:

- **Documents and composition:** Build supports campaign sources and authored
  Pages; Plan supports World-owned session preparation, including composed
  layouts. Work is saved through its owning document workflow.
- **Conversation and assisted authoring:** the Agent can discuss ideas,
  acquire relevant context and propose supported edits. In bounded Build and
  Plan paths, a proposal targets a particular document or slot and is reviewed
  before the user applies or saves it. A conversation does not itself publish
  a World fact. See the [Agent context guide](GUIDE-agent-context-and-runtime.md).
- **World knowledge and evidence:** the World Graph provides scoped object,
  relationship and evidence reads. Source workflows can produce candidates for
  review and governed publication; extraction alone does not make a candidate
  durable truth. See the [source ingestion map](GUIDE-source-ingestion-and-evidence.md)
  and [World architecture](../Design/ARCHITECTURE-campaign-supergraph.md).
- **Images and statblocks:** Image Studio can generate World-owned artwork;
  authored Pages can use managed images. Build also supports reviewed
  statblock variants. The available editing and Agent actions depend on the
  specific surface and current workflow.
- **Play and Combat:** Play brings prepared session material to the table.
  Combat provides an encounter workspace with a roster, turn controls, HP,
  conditions, notes and access to saved sheets. See the
  [local Play runbook](../Runbooks/RUNBOOK-local-play-dogfood.md).

DungeonMind owns durable World knowledge, revisions, provenance and scoped
retrieval; Buddy owns its product surfaces and Agent orchestration. WorldKeeper
coordinates supported governed changes, and GenerationEngine supplies shared
inference execution. A model's suggestion is not automatically a published World
change.

Recent retrieval work batches some graph and provenance reads and reduces
unnecessary work in bounded Plan paths. Component benchmarks and serving
qualification have different scopes: see
[Core neighborhood batching](https://github.com/Drakosfire/DungeonMind/pull/283),
[Buddy batch integration](https://github.com/Drakosfire/DungeonMindBuddy/pull/4353)
and [Plan claim projection](https://github.com/Drakosfire/DungeonMindBuddy/pull/4391).
The latter's measured whole-turn p95 improvement was not reproducible; these
results are not a general latency guarantee.

Capabilities in source do not establish their availability in a particular
hosted deployment, and focused tests do not establish full release qualification.
Consult the deployed revision, relevant evidence and the
[deployment runbook](../Runbooks/RUNBOOK-buddy-production-deployment.md).

## Surface entry points

| Work area | Product intent | Frontend entry point | Focused tests |
| --- | --- | --- | --- |
| Build | Work with source documents and review material | [BuildSurfacePage](../../apps/live-control-ui/src/buildSurface/BuildSurfacePage.tsx) | [Build surface tests](../../apps/live-control-ui/src/buildSurface/BuildSurfacePage.test.tsx) |
| Plan | Prepare session material with campaign context | [PlanSurfacePage](../../apps/live-control-ui/src/planSurface/PlanSurfacePage.tsx) | [Plan surface tests](../../apps/live-control-ui/src/planSurface/PlanSurfacePage.test.tsx) |
| Play | Work with prepared material during a session | [PlaySurfacePage](../../apps/live-control-ui/src/playSurface/PlaySurfacePage.tsx) | [Play surface tests](../../apps/live-control-ui/src/playSurface/PlaySurfacePage.test.tsx) |
| Shared hosts | Compose chrome, surface context and document work | [AppChrome](../../apps/live-control-ui/src/chrome/AppChrome.tsx), [SurfaceContextHost](../../apps/live-control-ui/src/surfaceInteraction/contextHost/SurfaceContextHost.tsx), [MarkdownCanvasSession](../../apps/live-control-ui/src/markdownCanvas/MarkdownCanvasSession.tsx) | [Chrome](../../apps/live-control-ui/src/chrome/AppChrome.test.tsx), [context host](../../apps/live-control-ui/src/surfaceInteraction/contextHost/SurfaceContextHost.test.tsx), [canvas](../../apps/live-control-ui/src/markdownCanvas/MarkdownCanvasSession.test.tsx) |

The [surface interaction architecture](../Design/ARCHITECTURE-surface-interaction-layer.md)
describes shared-host ownership and distinguishes a surface's context from its
active work object. Its companion contracts cover Plan, Play, application
state and World boundaries. Buddy owns product interaction and work state;
DungeonMind owns durable World identity, source/evidence admission and governed
publication. Review the [source ingestion map](GUIDE-source-ingestion-and-evidence.md)
and [agent context guide](GUIDE-agent-context-and-runtime.md) when a surface
change crosses those boundaries.

These test files are entry points, not an exhaustive acceptance suite. Trace the
specific server route, authorization and storage owner for a change, then use
[repository verification policy](../../AGENTS.md#review-and-verification) and
the applicable handoff to select exact-source checks. The local operator profile
and a hosted signed-in session have different admission conditions; check the
[deployment runbook](../Runbooks/RUNBOOK-buddy-production-deployment.md) and
the actual release before claiming hosted availability.
