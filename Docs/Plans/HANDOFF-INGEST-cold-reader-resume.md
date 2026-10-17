# HANDOFF — INGEST cold reader resume

**Status:** ACTIVE — PRIME authorized the bounded cold-reader repair and directed DOGFOOD to complete it.
**Pinned implementation checkout:** `/home/drakosfire/.codex/worktrees/996b/DungeonMindBuddy`
**Branch:** `codex/ingest-cold-reader-resume`
**Starting commit:** `91c44e0382e2970985f943216bc3b484510543bb` (#1350 merge).
**Re-anchoring evidence:** current `main` is `39aa16045536eb259926a0c89f9065ee01f0a304`; GitHub compare shows four intervening commits, all confined to the separate Build writer paths. The implementation checkout's shared Git metadata is read-only, so PRIME will commit and publish the prepared patch from its writable host after verification.
**Topology:** serial, one Ingest cold-reader PR. No server, extraction, source, graph, or database changes.

## Mission

Fix the saved recap reader's automatic restoration after a cold page load or route selection. Keep explicit “Load processed recap” behavior, exact campaign/session scoping, and stale A→B→A request protection intact.

## Reproduced failure and invariant

On the Session 10 route in 5202, a cold reload can show `Saved recap could not be opened` / `No saved recap is available for this session` even though the exact saved recap exists in the artifact list. Clicking **Load processed recap** then opens the same source successfully.

The automatic reader currently treats a matching inspect-status result as proof that an addressable source exists. That result can have no exact artifact, normalized path, or run ID. The effect records its `readerAttempt` before the asynchronous saved-artifact lookup finishes; the error from the incomplete status result then suppresses retry when the exact saved artifact arrives.

**Invariant:** automatic restoration starts only when an exact source address is available, or after the exact saved-artifact lookup has completed and supplied the source to load. A status match alone is not an address. Do not mark a reader attempt before that decision. Preserve explicit manual load and request-generation guards so a late A response cannot overwrite B or a later A selection.

## Exact write lease

- `Docs/Plans/HANDOFF-INGEST-cold-reader-resume.md` — this bounded contract and truthful settlement.
- `apps/live-control-ui/src/modules/IngestionModule.tsx` — gate automatic restore on addressable source/finished artifact lookup; retain manual-load and stale-selection behavior.
- `apps/live-control-ui/src/modules/IngestionModule.test.tsx` — regression coverage for deferred exact-artifact lookup and empty completed lookup.

No other product paths, APIs, shared navigation, schemas, migrations, dependencies, runtime services, saved content, extraction runs, or World publication. Return to PRIME before widening the lease.

## Verification

- Reproduce the race with an exact Session 10 selection and a deferred saved-artifact-list response.
- Assert no premature failed reader attempt/error before the exact list resolves; when it resolves with the matching artifact, assert the recap restores automatically.
- Assert a completed lookup with no matching address reports no saved recap without looping, and that explicit manual load still works.
- Preserve A→B→A stale-response fences with focused coverage if the change touches their lifecycle.
- Run the owning `IngestionModule.test.tsx` suite, applicable typecheck/build, and `git diff --check` against the cumulative current-main diff.
- No **Process**, extraction/provider call, candidate confirmation, World write, or retained database change. The user's Session 10 browser state is not a fixture and must not be mutated.

## Completion boundary

This slice proves cold restoration of an existing saved recap at the UI boundary. It does not prove live recap processing, enriched-node extraction quality, publication, or complete Session 29/28/27/26 Graph coverage. PRIME retains review and merge authority; DOGFOOD may report the primary Process→enriched-results path ready only after its own separate acceptance evidence exists.
