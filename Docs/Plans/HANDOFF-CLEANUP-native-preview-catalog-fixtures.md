# CLEANUP: complete native object-preview catalog fixtures

Status: ACTIVE under the user's cleanup goal and standing review/merge authority.
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
