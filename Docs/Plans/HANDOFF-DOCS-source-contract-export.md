# DOCS: reconcile source contract export

Status: HISTORICAL — completed by Buddy PR #4004, merged at `7ee521ee3b2c83b3929d9d11863555082b3f104d`. The lease is closed.

Originally authorized by the documentation goal. PR topology: serial.
Base: Buddy main `ecba0365cd25942a47fb019f1fba7eca9c557608`.
Branch: `codex/docs-source-contract-export`. Predecessor: merged #4003.

## Outcome and boundary

Refresh the non-authoritative source-to-World export from the canonical contract
updated by #3982, and explain export-relative link limitations in the Docs map.
Settle the merged predecessor handoff. Do not change the contract, process
index, user-managed Project Sources, runtime, credentials or deployment.

Expected write lease: `Docs/Sources/design-agent/ACTIVE_AUTHORITY/DESIGN-source-to-world-authoring-interaction-contract.md`,
`Docs/README.md`, `Docs/Plans/HANDOFF-DOCS-surface-runtime-authority.md`, and
this handoff. No services, ports, databases or provider calls are needed.

## Verification

Compare export bytes with canonical source, inspect the cumulative diff and
link caveat, check maintained links, then obtain exact-head independent review
and local verification. Mirror parity is not proof that copied relative links
resolve within the export directory.
