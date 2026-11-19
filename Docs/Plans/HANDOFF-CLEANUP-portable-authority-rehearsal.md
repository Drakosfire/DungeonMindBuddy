# CLEANUP: make authority rehearsal use its owned database

ACTIVE under the standing cleanup goal's implementation, independent review and
merge authority. Serial one PR; branch `codex/portable-authority-rehearsal`, base
`663718879553dc535df8b94a62c4a3b4ab0da5ec`. Reused isolated checkout.

Exclusive writes: this brief and
`tests/application_state/test_application_state_authority.py`. Current open PR
paths and pinned handoffs have no claim. Keep shared conftest, inventory,
production backup/restore implementation, workflows and deployments unchanged.

The complete authority/CLI run on an owned dynamic-port PostgreSQL16 container
passed33cases and failed one hardcoded54329/container-name assertion. Replace
that test's fixed Docker target with its configured per-test clone and the public
backup/restore APIs. Preserve exact edition fingerprint equality; exercise staged
dump/sidecars, verified restore and READY through production code. No skips or
weakened assertions. Require normal PostgreSQL clients on PATH.

Verify complete authority and CLI modules in a locked exact-source environment
with uniquely labeled tmpfs PostgreSQL16, dynamic loopback port, existing image
and matching clients copied to task-owned Projects storage. Preserve raw baseline
failure, client provenance, database/template cleanup and container removal.
Run exact-head hosted/build/validator and independent review before merge. No
operator data, real provider, shared container, fixture-port claim or release
qualification. New findings beyond this case are a checkpoint/split signal.

Predecessor#4169 merged02e28978, removing two obsolete Graph test arguments with
identical full outcomes; native profile transition#4168 is now merged on this
base. Original release/restore operator acceptance gates remain separately owned.
