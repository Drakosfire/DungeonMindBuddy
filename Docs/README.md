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

## Hosted deployment gates

The [production package smoke](https://github.com/Drakosfire/DungeonMindBuddy/pull/2478)
was rerun on merged main at `d9d4985e5`. It exercised the built SPA, liveness
and readiness, and signed-out and synthetic signed-in requests to the World
collection. It used disposable databases and a DMS fixture. Record the live evidence below against the release image digest
before exposing Buddy at `buddy.dungeonmind.net`.

1. Run the [read-only host inventory](Plans/RUNBOOK-HOSTED-read-only-host-inventory.md).
   Confirm capacity, the loopback upstream, DNS and TLS, and the
   [Nginx streaming configuration](../deploy/production/nginx-buddy.conf).
2. Confirm migration heads and owners for Buddy application state and
   DungeonMind WorldGraph. Verify the durable managed-World, artifact,
   session, and WorldGraph roots against the
   [Compose example](../deploy/production/compose.production.yaml). Rehearse
   backup restoration and record the previous image digest and rollback owner.
3. Confirm the approved DMS subjects and managed World assignments. From a
   browser on the Buddy origin, exercise real DMS login, the landing target,
   session cookie delivery, the assigned World collection, and logout. Verify
   signed-out and unauthorized requests are denied.
4. Check `/health/live`, `/health/ready`, the SPA and a supported signed-in
   route through the deployed edge. Record results with the release digest.
