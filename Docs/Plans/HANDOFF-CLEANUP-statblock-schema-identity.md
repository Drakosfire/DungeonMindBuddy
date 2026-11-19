# CLEANUP: reconcile statblock schema identity

Status: ACTIVE. Cleanup steward adopts original finding 52 / #4156 under the
standing cleanup goal's implementation, independent review and merge authority.
Serial, one PR; branch `codex/statblock-schema-identity`, base
`73f2efd3c6e95a07c6e9b2abf76e2949b1c529a4`. Reused isolated checkout; no runtime,
database, provider or deployment resources. No unmerged dependency.

## Boundary and exclusive write lease

- this handoff
- `apps/live_control_server/integrations/dungeonmind_statblocks/generated/__init__.py`
- `apps/live_control_server/integrations/dungeonmind_statblocks/README.md`
- `tests/test_sbw06a_server_revise_transcripts.py`
- `tests/test_sbw07a_server_transcripts.py`
- `tests/test_sbw07a_capture_output.py` (negative fingerprint refusal)
- `tests/fixtures/statblocks/v1/server_transcripts/README.md`

Current schema/models cite3887196e, but public fingerprint still citesdf46327f.
Capture tooling consumes that public identity. Correct it without relabeling raw
historical create/revise captures or their manifests. Historical schema is
recoverable at exact Git pin; no duplicate schema copy is introduced. Existing
fixture-model compatibility and capture mismatch refusal must remain intact.
No schema or generated model body change, recapture, API or runtime behavior
expansion. Checkpoint/split if regeneration reveals further drift.

## Regeneration checkpoint and split

Exact documented regeneration ataa6f3794 found additional pre-existing drift:
required nullable movement/ruleset/proficiency fields become default-None in the
generator output, plus a generated root type and description differences. The
discriminator transformation still matched14unions. The steward splits this
contract decision from the independently useful fingerprint correction. This
PR preserves existing model behavior and raw captures, reports regeneration RED,
and does not close original52/#4156. Its residual remains owned by statblock
integration/generated-client maintainers and cleanup steward. No successor lane
is dispatched; decide schema/model nullability authority before implementation.
Blindly replacing models or normalizing away semantic differences is forbidden.

Fresh open PR changed-path audit found no overlap, including complete102paths
for unchanged#3824. Relevant#3808/#3729/#3716 scopes have no proposed-path claim.

## Verification

Prove current snapshot/exported constant/generated headers agree; separately
prove historical manifest identities and raw fixture hashes. Recover exact old
schema bytes from Git. Run affected create/revise/capture contracts in a fresh
locked exact-source environment, including negative capture refusal. Run the
documented pinned generator and retain the complete body difference; the known
failure above is a deferred contract decision, not a passing regeneration claim.
Exact-source local
hosted/build/validator and independent cumulative-head review before merge.
No frontend changes: no duplicate full UI diagnostic or release qualification.
Record any failures and do not rewrite old captures to make checks pass.

Predecessor#4155 merged73f2efd3, exact reviewed retirement paths preserved;
the historical Campaign roadmap now forwards to pinned Git. Its retirement
handoff is settled by that merged result; no roadmap write lease is assumed here.
