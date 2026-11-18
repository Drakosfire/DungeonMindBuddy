# DOCS: Agent context and runtime guide

Status: MERGED / HISTORICAL. Buddy PR #3986, merge `afcb748185c5983df5df9b51c6bd363ae1361629`. The lane is closed; this record does not authorize new work.

Base: Buddy main `1fadf2cabff8353db3e86faf7602033372a45056`. Branch: `codex/docs-agent-context`.

## Outcome and boundary

Provide a contributor navigation guide to Agent context, runtime selection,
owning contracts and tests. Preserve the separation between source, design and
hosted deployment; do not change runtime behavior, model prompts, policy or
cross-repository ownership. Mark the merged #3963, #3980, #3982 and #3985 handoffs historical
as backward-looking state settlement. The link checker has its own contract and
is not changed here.

Expected write lease: `Docs/Guides/GUIDE-agent-context-and-runtime.md`,
`Docs/README.md`, this handoff, and the four merged predecessor handoffs
`HANDOFF-DOCS-entry-navigation.md`, `HANDOFF-DOCS-retrieval-evidence-navigation.md`,
`HANDOFF-DOCS-source-world-status.md` and `HANDOFF-DOCS-link-check.md`. No
services, ports, databases or provider calls are required. Check open PRs and
path leases before review.

## Verification

Check links and compare guide claims against the runtime port, assembler, turn
selection and cited tests. Run the maintained documentation link check and
`git diff --check`, inspect the full diff, and follow the exact-head review
standard. Do not infer deployed capabilities from source.
