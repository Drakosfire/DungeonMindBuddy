# RETRIEVAL: reader-first native citation compatibility

Status: ACTIVE, serial serving prerequisite for #4955. The main citation fix
merged in #4954. Review of #4955 found that the current serving reader cannot
reconstruct a newer citation-capable semantic Build reply, because both reply
generations share one name. Deploy this reader before enabling the writer so
the writer's rollback target can read replies it produces.

Base: `a3b765cf7980f5c191b810c3efe0f549ef844676`; branch:
`codex/negative-native-citation-reader`. Write lease is this handoff, the
native Rules packet admission verifier, and focused admission tests. Only
retained readback changes; fresh dispatch and producer selection stay as-is.
The successor must match the complete sealed schema, not just its name.

Verify fresh and retained acceptance for the current format, retained
acceptance of the successor, fresh rejection of the successor, and rejection
of modified historical schemas. Review the exact head, deploy via the
authorized Actions process, verify production, then rebase #4955 onto the
deployed serving lineage and requalify it before publication. The broader
negative-retrieval work and live source-required replay remain open.
