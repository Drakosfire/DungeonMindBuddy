# DOCS: check maintained documentation links

Status: MERGED / HISTORICAL. Buddy PR #3985, merge `1fadf2cabff8353db3e86faf7602033372a45056`. The lane is closed; this record does not authorize new work.

Base: Buddy main `65641eaffb2d7df866ec9ba61b86aada9e89dacf`. Branch: `codex/docs-link-check`. Concurrent lane: PR #3982 (`codex/docs-source-world-status`), which edits the source-to-World contract and its own handoff only. No behavioral dependency or shared paths exist. Both lanes use the shared frontend verification lock.

## Outcome and boundary

Provide a small repeatable check of local links in maintained entry points. Detect missing targets, explicit unresolved references and common Markdown fragments; document unsupported syntax and external-link limits. Do not scan all archives or change product runtime, documentation authority, CI triggers, dependencies or external state.

Expected write lease: `scripts/check_docs_links.py`, `tests/test_check_docs_links.py`, and this handoff. No services, ports or databases required. Re-anchor and inspect active file leases before review.

## Verification

Run the checker on its named entry points; test valid and invalid targets, fragments, reference definitions, escapes, code fences and images. Inspect the cumulative diff; run `git diff --check`; use exact-head review and the repository verification standard. Report unsupported syntax and actual environment honestly.
