# DOCS: clarify local first-start prerequisites

Status: HISTORICAL — completed by Buddy PR #3993, merged at `250f1673870b694ae31f2a6514d40de333ccab65`. The lease is closed.

Originally authorized by the documentation goal. PR topology: serial.

Base: Buddy main `fe8cdcc1e3ca6f463b99b1635217f37c3c9f4dc3`. Branch: `codex/docs-fresh-start`.

## Outcome and boundary

Clarify the separate DungeonMindServer configuration boundary, the launcher's
existing-listener behavior, and the expected exit/readiness result for a fresh
empty Play database. Settle the merged #3989 handoff. Do not change runtime,
configuration, credentials, data or provider behavior.

Expected write lease: `README.md`, `Docs/Runbooks/RUNBOOK-local-play-dogfood.md`,
`Docs/Plans/HANDOFF-DOCS-world-storage.md`, and this handoff. No services,
ports, databases or provider calls are required for the documentation change.

## Verification

Compare wording with the launcher and bootstrap code and the isolated fresh-start
witness; validate links and the maintained link check, inspect the cumulative
diff and run `git diff --check`. Follow the exact-head review standard. The
prior witness used task-owned data services and an existing server interpreter;
it does not establish normal authentication, Graph operations or deployment.
