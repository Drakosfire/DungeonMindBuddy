# Buddy documentation

- [Campaign and World architecture](Design/ARCHITECTURE-campaign-supergraph.md)
  explains the product boundary and durable World authority.
- [Source-to-World authoring](Design/DESIGN-source-to-world-authoring-interaction-contract.md)
  follows source evidence from review through publication.
- [Design source index](Design/INDEX-design-agent-source-set.md) identifies the
  owning documents for design decisions and current work.
- [Local Play runbook](Runbooks/RUNBOOK-local-play-dogfood.md) covers first-time
  state setup. [State recovery](Runbooks/RUNBOOK-application-state-authority-recovery.md)
  covers recovery and verification.
- [Production package example](../deploy/production/compose.production.yaml)
  shows required configuration and persistent paths. Host and edge setup
  are deployment work.
- [Lab and evaluation guide](../evals/README.md) points to harnesses and evidence.

Use [the agent instructions](../AGENTS.md) when picking up work. Read the
owning contract and the active handoff for that assignment. Archived plans
and dated reports provide historical evidence.

## Hosted deployment

Follow the [Buddy production deployment runbook](Runbooks/RUNBOOK-buddy-production-deployment.md)
for recovery verification, release commands, public edge checks, and the real
browser sign-in and sign-out smoke. The [local production smoke](https://github.com/Drakosfire/DungeonMindBuddy/pull/2478)
used disposable databases and a synthetic DMS session.
