# Product surfaces: contributor map

Buddy's Build, Plan and Play surfaces share a UI shell while retaining different
product responsibilities. This map identifies starting points in the repository;
individual routes and deployed releases may support only a subset of the
intended experience. For setup and commands use the [frontend guide](../../apps/live-control-ui/README.md).

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
