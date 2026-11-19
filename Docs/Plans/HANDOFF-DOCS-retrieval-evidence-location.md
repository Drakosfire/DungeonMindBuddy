# DOCS: clarify retrieval evidence location

Status: HISTORICAL — completed by Buddy PR #4009, merged at `54085982b2dcbc901d0ccccea02e4f0f7b822426`. The lease is closed.

Originally authorized by the documentation goal. PR topology: serial.
Base: Buddy main `92e1d597b2a5b2275eca18a8c7a033039f1edd93`.
Branch: `codex/docs-retrieval-evidence-location`. Predecessor: merged #4007.

## Outcome and boundary

Make the Wandering Forest lab evidence location and its local-only portability
limit explicit. Settle the predecessor handoff. Do not change the experiment,
metrics, source data, runtime, process indexes or user-managed external state.

Expected write lease: `evals/README.md`,
`Docs/Plans/HANDOFF-DOCS-development-verification.md`, and this handoff. No
services, ports, databases or provider calls are needed.

## Verification

Inspect the named local directory without publishing its contents; verify that
it is not a repository-tracked bundle, check maintained links and cumulative
diff, then complete exact-head independent review and local verification.
Artifact existence is not independent reproduction of the results.
