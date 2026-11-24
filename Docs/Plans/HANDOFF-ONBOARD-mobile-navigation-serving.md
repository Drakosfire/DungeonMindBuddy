# ONBOARD: mobile graph navigation on the serving lineage

Status: ACTIVE. Carry merged main PR #4577 onto deployed serving parent #4575,
base `3d49e210e55024e7d252748c542a9ffadc0c2cf5`. The running image revision is
`10d40d6633d3493800f2faa59df6c933869a8c9e`. Branch:
`codex/onboard-mobile-navigation-serving-3d49`. Scope is the guest graph page,
styles, focused tests and these handoffs. No API, auth, database, schema, copy
content or provider behavior changes.

Verify the exact serving head with hosted and discovered frontend suites and
compare inherited failures against the retained serving baseline. Obtain
independent Bugbot review. Re-anchor live image, runtime ownership and the
detached fallback before building and deploying; do not use the superseded
Compose activation packets. Verify mobile detail and return navigation, health,
guest access and anonymous private-World isolation after activation.
