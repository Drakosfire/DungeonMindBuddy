# DOCS: documentation link-check navigation

Status: MERGED / HISTORICAL. Buddy PR #3987, merge `335d6eac27eb8f730219be7bbebf40bee86dba1b`. The lane is closed; this record does not authorize new work.

Base: Buddy main `afcb748185c5983df5df9b51c6bd363ae1361629`, after #3986. Branch: `codex/docs-checker-navigation`.

## Outcome and boundary

Make the merged opt-in link checker discoverable from the documentation map,
including its command and explicit scope. Mark the merged Agent guide handoff
historical. Do not change the checker, runtime, CI or verification policy.

Expected write lease: `Docs/README.md`, `Docs/Plans/HANDOFF-DOCS-agent-context-guide.md`,
and this handoff. No services, ports, databases or provider calls are required.

## Verification

Run the documented check, confirm the script link and compare stated limitations
with the script; verify the predecessor merge SHA, inspect the full diff and run
`git diff --check`. Follow the exact-head review standard.
