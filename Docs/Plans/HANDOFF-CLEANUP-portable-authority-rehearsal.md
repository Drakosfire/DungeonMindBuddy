# CLEANUP: make authority rehearsal use its owned database

ACTIVE under the standing cleanup goal's implementation, independent review and
merge authority. Serial one PR; branch `codex/portable-authority-rehearsal`, base
`609205a4e6b0baf6ff6db558cfd86a4f051000ca`. Reused isolated checkout.

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

Re-anchor: main advanced native profile/read services and Python dependency pins
during review. Rebase the same bounded slice on609205a4 and requalify the exact
source in a fresh locked environment plus hosted/build, then obtain new exact-head
review. The prior2ac59402 approval/evidence is superseded for acceptance. The
33pass/1fail baseline at66371887 remains historical evidence of fixed-port
coupling; no current-dependency baseline result is invented.

Predecessor#4169 merged02e28978, removing two obsolete Graph test arguments with
identical full outcomes; native profile transition#4168 is now merged on this
base. Original release/restore operator acceptance gates remain separately owned.
