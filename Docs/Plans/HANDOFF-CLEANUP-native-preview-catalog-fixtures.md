# CLEANUP: complete native object-preview catalog fixtures

Status: SETTLED by #4081, merged c4a3403e8e552797e185899b7f35f4a6817047f9.
Reviewed head: c11f8868c84cd7a0478e23bbdd50dfd79402763a.
Actual execution parent: e36abef5d75d543b7e8c656d611b93723757b362.
The original authority anchor below preceded a docs-only change; frontend,
verifier and contract sources were byte-identical. Hosted 1411 tests and build
passed; the repeated full diagnostic had 8031 passes, 148 failures and 2 pending
cases (8181 reported, 8179 inventory). Both intended failures resolved, all six
preview cases passed, and no other failure IDs changed versus the parent.
Full qualification remains red, including two conditional inventory extras.
The earlier quote-correction failure variant remains unresolved under #4074/#1235;
the passing repeat does not establish its cause or retire the observation.
Base: c54d6545563d68a3120d748287bbda75783b62b0, fetched origin/main.
Branch: codex/native-preview-catalog-fixtures in the existing cleanup checkout.
Topology: one serial PR after merged #4080; no unmerged behavioral dependency.
Owner: cleanup steward with independent Bugbot review. Follow-up #4074.

Outcome: restore two object-preview cases whose strict API mock lacks the native
Graph/source catalog dependencies used by editable reference controls. Provide
complete typed catalog responses at the existing captured World/revision pin.
Preserve exact entity reads, changed-pin rejection, close/reopen and hydration
assertions. Add explicit no-catalog-read assertions for read-only preview paths.
No runtime changes or stale assertion retirement.

Write lease: apps/live-control-ui/src/graphLens/NativeGraphObjectPreview.test.tsx,
this handoff, and predecessor HANDOFF-CLEANUP-staged-work-plan-fixtures.md for
truthful completed-state settlement. All 60 open PR file lists checked at
activation; no test-file overlap. Shared test registries and active #3824/#2298
files stay read-only. The separate eager picker loading and Plan proposal
transport concerns are not absorbed here.

Verification: exact-source diagnostic reports 4 passes/2 failures before, 6 passes
after with original assertions retained and new negative-read assertions. This
is not final commit proof. Run exact-commit hosted verifier/validator and full
discovered diagnostic. Preserve the complete reported inventory, prove both
intended failures resolve with all six module cases passing, and compare every
other failure against the retained byte-identical parent frontend. Full release
qualification remains red while inherited failures/inventory discrepancies exist.
Independent exact-head cumulative/raw-evidence review is required before merge.

Runtime: no application, database, provider, remote host or operator-data writes.
Frontend work honors the global resource lock and uses task-owned external
scratch/cache on the verified Projects filesystem. The original cleanup owner
and SSH gates remain outstanding; this test-only slice does not satisfy them.
