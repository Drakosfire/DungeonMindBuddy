# HANDOFF — INGEST cold reader resume

**Status:** ACTIVE — PRIME authorized the bounded cold-reader repair and directed DOGFOOD to complete it.
**Pinned implementation checkout:** `/home/drakosfire/.codex/worktrees/996b/DungeonMindBuddy`
**Branch:** `codex/ingest-cold-reader-snapshot` (same existing checkout).
**Starting commit:** `0dbdd85a8db8038ef7fe21e083dbe3cc8905462d` (#1352 merge); successor activated by PRIME after the real cold-load failure. Original #1352 implementation lease ended at that merge.
**Re-anchoring evidence:** GitHub and the local remote ref identify current `main` as `0dbdd85a8db8038ef7fe21e083dbe3cc8905462d`, the merge of #1352 atop `39aa16045536eb259926a0c89f9065ee01f0a304`. Open PR #1235 changes only Graph Review/API files and does not overlap this lease; no other open PR matched `IngestionModule`. The implementation checkout's shared Git metadata is read-only, so PRIME will create the successor branch and publish the verified patch from its writable host.
**Topology:** serial, one Ingest cold-reader PR. No server, extraction, source, graph, or database changes.

## Mission

Fix the saved recap reader's automatic restoration after a cold page load or route selection. Keep explicit “Load processed recap” behavior, exact campaign/session scoping, and stale A→B→A request protection intact.

## Reproduced failure and invariant

On the Session 10 route in 5202, a cold reload can show `Saved recap could not be opened` / `No saved recap is available for this session` even though the exact saved recap exists in the artifact list. Clicking **Load processed recap** then opens the same source successfully.

The cold route has a separate premature caller: `NativeGraphAccessControl` reports an available session during mount and its callback directly calls `reviewSavedSource(true)` before the route selection or artifact lookup has hydrated. That call records `readerAttempt` and reports no saved recap. When the automatic restore effect later sees the hydrated Session 10 result and exact saved artifact, it skips because that identity is already marked attempted.

**Invariant:** the Native Graph availability callback must not start or consume a reader attempt until the route selection is hydrated and an exact source address is known. The automatic effect remains the owner of first cold restoration and waits for the exact saved-artifact lookup when status supplies no address. A later Graph reconnect may retry a failed projection once those conditions hold. Preserve explicit manual load and request-generation guards so a late A response cannot overwrite B or a later A selection.

## Successor failure after #1352 and repair

A hidden fresh 5202 tab with the temporary `readerDebug=1` panel reproduced the failure without using **Load processed recap** or **Process recap**. At `reviewSavedSource` entry the snapshot showed `preserveSelection=false`, `restore=true`, `selectionHydrated=false`, `readerAttempt` already set, no current lookup result, zero artifacts, and no source address. The reader showed `Saved recap could not be opened` / `No saved recap is available for this session`.

After hydration, the trace showed `selectionHydrated=true`, `resultOwnsSelection=true`, a normalized path, lookup `loaded`, 27 listed artifacts, and the exact `longmont-c2/session-10` artifact ID. The effect then reported `gateReason=attempt-already-recorded` with `restore=false`. Source inspection traced the premature call to the mount-time `NativeGraphAccessControl.onChanged` callback. The repair leaves that callback inert until the current selection has an exact address, allowing the automatic effect to restore; it still lets a later Graph reconnect retry a failed projection.

The cold-route regression resolves Graph availability before inspect-status or artifact-list hydration and verifies there is no premature error, then confirms the exact Session 10 projection starts automatically when the source arrives. A second test verifies a failed projection retries after explicitly reconnecting Graph. Existing manual-load and A→B→A guards remain covered.

ARCHITECTURE found an additional reconnect defect in review of `d0d2bfc6cd638f298d21ab21ce05717e3440c13b`: after a successful reader projection, revoking Graph access cleared `reviewSource` but retained `readerAttempt` with no error. Reconnect therefore hit the successful-attempt guard and did not request another projection, leaving the selected source empty. The fix clears the consumed attempt when Graph becomes unavailable; only an explicit later availability callback can retry. A success→revoke→reconnect regression failed on that reviewed head because projection was called once instead of twice, and passes with the repair.

## Exact write lease

- `Docs/Plans/HANDOFF-INGEST-cold-reader-resume.md` — this bounded contract and truthful settlement.
- `apps/live-control-ui/src/modules/IngestionModule.tsx` — prevent early Graph-availability callbacks from consuming cold-reader attempts; preserve eligible reconnect retry, manual load, and stale-selection behavior.
- `apps/live-control-ui/src/modules/IngestionModule.test.tsx` — regress the early callback before hydration and preserve Graph reconnect retry alongside existing cold-load, manual-load, and stale-response coverage.

No other product paths, APIs, shared navigation, schemas, migrations, dependencies, runtime services, saved content, extraction runs, or World publication. Return to PRIME before widening the lease.

## Verification

- Reproduce the failure with Graph availability resolving before Session 10 selection/status/artifact hydration.
- Assert that callback does not consume the reader attempt; after the exact saved source arrives, assert automatic projection and rendering without clicking Load.
- Assert that a failed projection retries after an explicit Graph reconnect, and that a successful projection is restored after revoke/reconnect without duplicate initial restoration.
- Assert a completed lookup with no matching address reports no saved recap without looping, and that explicit manual load still works.
- Preserve A→B→A stale-response fences with focused coverage if the change touches their lifecycle.
- Run the owning `IngestionModule.test.tsx` suite, applicable typecheck/build, and `git diff --check` against the cumulative current-main diff.
- No **Process**, extraction/provider call, candidate confirmation, World write, or retained database change. The user's Session 10 browser state is not a fixture and must not be mutated.
- Verification against exact base `0dbdd85a8db8038ef7fe21e083dbe3cc8905462d`: the early-callback regression fails with the premature `No saved recap is available for this session` alert. On published head `d0d2bfc6cd638f298d21ab21ce05717e3440c13b`, the added success→revoke→reconnect regression failed because `postWorldGraphRecapProjection` was called once, not twice. The corrected working tree passes the early-callback, failed-projection retry, and success→revoke→reconnect regressions; all 76 `IngestionModule.test.tsx` tests pass, UI typecheck and production build pass, and `git diff --check` passes. The build retains its existing >500 KB chunk warning and the suite emits existing React `act(...)` warnings. PRIME restored the normal 5202 index; a fresh hidden tab shows no diagnostic panel. Do not claim the repair is live until the corrected PR is reviewed, merged, and rolled out.

## Completion boundary

This slice proves cold restoration of an existing saved recap at the UI boundary. It does not prove live recap processing, enriched-node extraction quality, publication, or complete Session 29/28/27/26 Graph coverage. PRIME retains review and merge authority; DOGFOOD may report the primary Process→enriched-results path ready only after its own separate acceptance evidence exists.
