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
| Understand local World storage and recovery | [Local managed-World storage](Guides/GUIDE-local-world-storage.md) |
| Understand source ingestion, evidence and publication | [Source ingestion contributor map](Guides/GUIDE-source-ingestion-and-evidence.md) and [source-to-World authoring contract](Design/DESIGN-source-to-world-authoring-interaction-contract.md) |
| Work on shared surfaces and interaction | [Surface contributor map](Guides/GUIDE-surface-contributor-map.md), [interaction architecture](Design/ARCHITECTURE-surface-interaction-layer.md), and [frontend guide](../apps/live-control-ui/README.md) |
| Understand Agent orchestration and context | [Agent context and runtime guide](Guides/GUIDE-agent-context-and-runtime.md), the [context compilation decision](Design/DECISION-agent-context-compilation.md), and the dated [runtime design direction](Design/DECISION-agent-runtime-and-semantic-adjudication.md) |
| Choose verification for a change | [Development and verification guide](Guides/GUIDE-development-verification.md), [agent policy](../AGENTS.md#review-and-verification), and the owning contract |
| Check links in maintained entry points | [Local documentation link check](../scripts/check_docs_links.py) |
| Determine whether a handoff or evidence is current | [Handoff and evidence navigation](Guides/GUIDE-handoff-and-evidence-navigation.md) |
| Find Agent actions and their evidence | [Canonical action catalog](../evals/plan-authoring-benchmark.md#action-catalog) |
| Understand decision and end-to-end benchmark coverage | [Workflow decision benchmark](../evals/plan-authoring-benchmark.md#workflow-decision-benchmark), [coverage matrix](../evals/right-action-coverage.md), and [adventure-to-follow-up benchmark](../evals/adventure-to-follow-up-benchmark.md) |
| Find proposed ingestion and statblock reviews | [Worldbuilding ingestion refinement](Backlog/IDEA-worldbuilding-ingestion-refinement.md) and [statblock dogfood review](Backlog/IDEA-statblock-dogfood-review.md) |\n| Find experiments, fixtures, or evaluation evidence | [Lab and evaluation guide](../evals/README.md) |
| Find the accepted ingestion baseline and historical retrieval evidence | [Baseline and retrieval history report](Reports/REPORT-ingestion-baseline-and-retrieval-history-2026-11-07.md) |
| Deploy or recover a system | [Production deployment](Runbooks/RUNBOOK-buddy-production-deployment.md), [manual Actions cutover](Runbooks/RUNBOOK-buddy-actions-cutover.md), and [application-state recovery](Runbooks/RUNBOOK-application-state-authority-recovery.md) |

From the repository root, run `uv run python scripts/check_docs_links.py .` to
check the maintained entry points, domain guides, and local Play runbook named
in the script. It checks local targets
and common Markdown fragments; external and root-relative URLs, shortcut
references, non-Markdown fragments, and full GitHub anchor parity are outside
its scope. This opt-in check does not replace the repository's review and
verification standard.

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
copies are not a substitute for their current owning documents. The export
preserves copied Markdown paths, which may not resolve from the export directory;
open the canonical document to follow its relative links.

[Plans](Plans/) contain handoffs and design work;
[reports](Reports/) contain findings and evidence; [roadmaps](Roadmaps/)
describe bounded workstreams. Some directory indexes retain earlier sequencing
and role terminology; check a document's scope, status, and applicable handoff
before using it as current sequencing authority.

## Hosted deployment

The [production deployment runbook](Runbooks/RUNBOOK-buddy-production-deployment.md)
covers recovery verification, release commands, public edge checks, and the
browser sign-in and sign-out smoke. The
[Compose example](../deploy/production/compose.production.yaml) shows runtime
configuration and persistent paths. Merged code and an observed deployment
are different evidence; consult the actual release before asserting hosted
feature availability.
