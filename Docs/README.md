# Buddy documentation

Start with the [repository README](../README.md) for the product overview and
local quick start. This page routes you to the owner of a question; a link to a
design or historical report does not by itself mean that every feature it
describes is implemented or deployed.

## Find what you need

| I want to… | Start here |
| --- | --- |
| Run Buddy locally | [Local Play runbook](Runbooks/RUNBOOK-local-play-dogfood.md) and [frontend guide](../apps/live-control-ui/README.md) |
| Understand World knowledge and product boundaries | [Campaign and World architecture](Design/ARCHITECTURE-campaign-supergraph.md) |
| Understand source review and publication | [Source-to-World authoring contract](Design/DESIGN-source-to-world-authoring-interaction-contract.md) |
| Work on shared surfaces and interaction | [Surface interaction architecture](Design/ARCHITECTURE-surface-interaction-layer.md) and [frontend guide](../apps/live-control-ui/README.md) |
| Understand Agent orchestration and context | [Agent runtime boundary](../apps/live_control_server/services/agent_runtime.py), [context compilation decision](Design/DECISION-agent-context-compilation.md), and the dated [runtime design direction](Design/DECISION-agent-runtime-and-semantic-adjudication.md) |
| Choose verification for a change | [Agent policy: review and verification](../AGENTS.md#review-and-verification), [frontend commands](../apps/live-control-ui/README.md#commands), and the owning contract |
| Find experiments, fixtures, or evaluation evidence | [Lab and evaluation guide](../evals/README.md) |
| Deploy or recover a system | [Production deployment](Runbooks/RUNBOOK-buddy-production-deployment.md) and [application-state recovery](Runbooks/RUNBOOK-application-state-authority-recovery.md) |

## Current work and historical material

[AGENTS.md](../AGENTS.md) is the repository's operating policy. Before changing
code, re-anchor on the remote default branch, inspect relevant open work, and
read the explicitly authorized, pinned handoff for the assignment. A handoff
may be on a branch or another durable reference; its location alone does not
make it active. Current code and the owning contract establish the applicable
behavior; dated plans, reports, and archived documents preserve context or
evidence and may describe earlier states.

The [design source index](Design/INDEX-design-agent-source-set.md) is a dated
curated reference, including a user-managed Project Sources snapshot. Check
its stated refresh dates and reconcile process guidance with current
[AGENTS.md](../AGENTS.md); it is not an independent policy gate. Exported
copies are not a substitute for their current owning documents.

[Plans](Plans/) contain handoffs and design work;
[reports](Reports/) contain findings and evidence; [roadmaps](Roadmaps/)
describe bounded workstreams. Check a document's scope and status before
using it as current sequencing authority.

## Hosted deployment

The [production deployment runbook](Runbooks/RUNBOOK-buddy-production-deployment.md)
covers recovery verification, release commands, public edge checks, and the
browser sign-in and sign-out smoke. The
[Compose example](../deploy/production/compose.production.yaml) shows runtime
configuration and persistent paths. Merged code and an observed deployment
are different evidence; consult the actual release before asserting hosted
feature availability.
