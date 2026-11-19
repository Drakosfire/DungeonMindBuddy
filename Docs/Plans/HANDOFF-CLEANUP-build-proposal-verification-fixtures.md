# CLEANUP: repair proposal source identity and committed-read fixtures

Status: SETTLED by #4085, merged 322dbb332f1c421f03cb0dced6fbd8c72aa3a092.
Reviewed head: 8f163eb0bb2975f1aa2a6a296357ee5b801a3f37.
Independent exact-head source/raw-evidence review approved. Hosted 1411 tests,
build and evidence validation passed. Full discovered diagnostic: 8038 passed,
141 failed, 2 pending. All 33 proposal cases passed; exactly two intended failures
resolved, with no added/omitted cases, new failures or changed remaining leading
messages. Full qualification remains red with the same two conditional inventory
extras and the earlier unresolved quote-correction observation under #4074.
Base: 0f19b5acb888632cac2ff52f4e878842164c6ca3.
Branch: codex/build-proposal-verification-fixtures, existing cleanup checkout.
Topology: serial after merged #4084; no unmerged behavioral dependency.
Owner: cleanup steward; independent Bugbot review before merge. Follow-up #4074.

Outcome: repair two stale proposal-test assumptions without runtime changes.
Identify the source heading through ProseMirror nodeDOM(0), then require H2 type,
direct editor parent and exact original title. The existing :scope query selects
the nested suggestion editor's Culture heading in the current test DOM; raw
instrumented source JSON/node/DOM confirms the Quarry Households source survives.
For spacer/lost-save recovery, mock the committed snapshot API used by the actual
save owner. Require its exact document argument and reject/forbid working-copy
snapshot reads. Preserve insertion cardinality, single application, no extra Save,
unchanged current JSON/receipt and all Undo/recovery assertions.

Write lease: apps/live-control-ui/src/buildSurface/BuildPageProposal.test.tsx,
this handoff, and HANDOFF-CLEANUP-projection-catalog-host-fixtures.md for truthful
predecessor settlement. All 60 open PR file lists checked at activation; no overlap
on existing leased paths. Runtime owners, shared fixtures and active work remain
read-only. No provider, database or remote host writes.

Verification: retained baseline diagnostic 31 passes/2 failures, including raw
source-heading identity/DOM evidence. Run focused after fixture repair, then
exact-head hosted verifier/build/validator and full discovered diagnostic under
the shared frontend lock with verified Projects external scratch. Require all
33 module cases to pass and compare every test ID/failure/leading message against
the retained byte-identical parent frontend: two intended resolutions, no new
failures or omissions. Preserve unrelated red failures, two conditional inventory
extras and the earlier unresolved quote-correction observation. Independent
cumulative exact-head source and raw-evidence review is required before merge.
Original cleanup owner/release gates remain outstanding.
