# DOCS: check maintained domain guide links

Status: ACTIVE. Authorized by the documentation goal. PR topology: serial.
Base: Buddy main `1acbf62ac34bcf3f86ae22294979b02be34e1705`.
Branch: `codex/docs-check-domain-guides`. Predecessor: merged #4005.

## Outcome and boundary

Include the five maintained domain/navigation guides and local Play runbook in
the existing opt-in checker. Explain the scope in the Docs index and settle the
merged predecessor handoff. Keep checker behavior, parser, exclusions, runtime
and CI triggers unchanged. Do not attempt a repository-wide link audit.

Expected write lease: `scripts/check_docs_links.py`, `Docs/README.md`,
`Docs/Plans/HANDOFF-DOCS-handoff-navigation.md`, and this handoff. No services,
ports, databases or provider calls are needed.

## Verification

Run the checker against the full maintained set and its focused tests; inspect
the cumulative diff, then complete exact-head independent review and local
verification. External URLs and the other documented exclusions remain outside
its scope.
