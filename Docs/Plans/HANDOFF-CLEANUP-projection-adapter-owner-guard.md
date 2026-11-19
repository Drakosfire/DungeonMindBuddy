# CLEANUP: verify the current projection adapter owner

Status: SETTLED by #4086, merged 1b1decc8703db9d1912ec237f4f4a075038c237b.
Reviewed head: 0cf965e222aa5da11a95d7afcdfbc6e6cf48791c.
Independent exact-head source/raw-evidence review approved. Hosted 1411 tests,
build and evidence validation passed. Full discovered diagnostic: 8039 passed,
140 failed, 2 pending; all 13 boundary cases passed. Exactly one old App.tsx case
was paired with its renamed LocalWorkspace.tsx replacement; no other additions
or omissions, new failures or changed remaining leading messages. Both negative
ownership probes failed as intended. Full qualification remains red with two
conditional inventory extras and the earlier unresolved quote-correction case.
Base: 322dbb332f1c421f03cb0dced6fbd8c72aa3a092.
Branch: codex/projection-adapter-owner-guard, existing cleanup checkout.
Topology: serial after merged #4085; no unmerged behavioral dependency.
Owner: cleanup steward; independent Bugbot review before merge. Follow-up #4074.

Outcome: align the stale App.tsx ownership assertion with the current local
workspace composition. LocalWorkspace.tsx mounts the adapter once; App.tsx
loads BuddyApp, which defers the workspace. Scan every production TS/TSX source
for named adapter JSX mounts and adapter-module from-specifiers, stripping
comments through the existing scanner. Require each inventory to contain only
LocalWorkspace.tsx:1, preventing duplicates elsewhere rather than just checking
the expected owner's file. Existing neutral projection/import/removal guards
remain unchanged. This is a source-shape guard, not exhaustive semantic import
resolution or proof of a deployed route. No runtime changes.

Write lease: apps/live-control-ui/src/surfaceInteraction/projection/projectionBoundaries.test.ts,
this handoff, and HANDOFF-CLEANUP-build-proposal-verification-fixtures.md for
truthful predecessor settlement. All 60 open PR file lists checked at activation;
no overlap on existing leased paths. App/BuddyApp/LocalWorkspace runtime owners
and broader surfaceInteraction architecture allowlists remain read-only.

Verification: focused baseline 12 passes/1 failure; updated module 13 passes.
Negative duplicate-mount and outside-owner-import probes each yield 12 passes
and one intended ownership failure. These are working-tree diagnostics only. Exact-head hosted verifier/build/validator,
then full discovered diagnostic under the global frontend lock with verified
Projects external scratch. The old case name explicitly mentions App.tsx; rename
that single case to LocalWorkspace.tsx and account for exactly that before/after
ID pair in the complete inventory comparison. No other additions/omissions are
accepted. Require its inherited failure to resolve, with no new failures or
changed remaining leading messages. Preserve unrelated red results, the two
conditional inventory extras and earlier unresolved quote-correction observation.
Obtain independent exact-head cumulative source/raw-evidence review before merge.
Original cleanup owner/release gates remain outstanding.
