# INGEST: preserve campaign and session affinity in prior recap selection

**Status:** SETTLED — PR #1333 (`INGEST: reset prior recap selection on route change`) merged at `6531f0038d79431c6265afb3fd01e6d99458cd2b` from head `88510a3d8aeaff0caf9b84b674ee63e1b49836a5`. Its exact-session route reset supersedes this handoff's active lease.
**Base:** current GitHub `main@1c810a208e27be6efc7f21ed10bdcc18c05c0bb3`.
**Branch:** `codex/ingest-session-affinity-route-reset`.
**Checkout:** `/home/drakosfire/.codex/worktrees/996b/DungeonMindBuddy` (reuse the assigned checkout).
**Topology:** one independent Ingest UI PR. PR #1318 is settled at merge commit `1ed861d7c123fd62d7583204eff7f2236a5680e4` from head `e3c231dab039f6842864888c8fb71e5a2ead58d7`; this follow-up repairs the mounted-route case its initial exact-match default did not cover. Open PR #1235 remains limited to disjoint Graph Review/API observation-review paths. No new worktree, live service, or retained-data lane is introduced.

## Settlement

PR #1333 passed independent ARCHITECTURE review and merged. It fixed the mounted same-campaign session-route case that the original PR #1318 did not cover. Its UI suite passed 63 tests with typecheck and diff-check. This handoff no longer grants a write lease. Rendered post-merge selector behavior, source load/process/save, real recap ingestion and persistence acceptance remain unverified and are tracked separately.

## Mission

When a user opens Ingest for a campaign/session, the prior processed recap selector must not silently default to the newest recap from another session. Default only to a recap whose `campaign_id` and `session_id` exactly match the current target. If there is no exact match or no valid session target, leave the selector at its “Load a processed recap…” placeholder. Selecting an option remains an explicit user action, and loading remains a separate explicit action.

## Invariant and failure cases

- Session 10 must never select Session 27 merely because Session 27 is the latest registered recap.
- A returned artifact list must not select another campaign or session after the user changes either target while that list request is pending.
- The selector must show only artifacts whose `campaign_id` matches the selected campaign.
- When the campaign changes, stale options from the previous campaign must not remain selectable while the new list is loading.
- An exact matching artifact may be preselected; it must not be loaded automatically.
- When a mounted route changes sessions within the same campaign, immediately replace a prior-session selection with the exact target-session artifact, or clear it to the placeholder when there is no exact match.
- Explicit user selection, local draft contents, source lineage checks, and load/reopen behavior remain unchanged.

## Exact write lease

- `Docs/Plans/HANDOFF-INGEST-session-affinity-default.md` — this bounded contract and evidence.
- `apps/live-control-ui/src/modules/IngestionModule.tsx` — exact-match defaulting and mounted-route reselection, campaign-change request invalidation, and clearing prior-campaign options. No source loading or processing changes.
- `apps/live-control-ui/src/modules/IngestionModule.test.tsx` — regression coverage for exact match, no match, explicit load remaining explicit, mounted route changes, and stale list responses after target changes.

No API/server/schema, extraction/materializer, raw source, graph publication, provider, database, retained artifact, or 5202 changes are leased. Return to PRIME before expanding scope or write paths.

## Verification

- Complete `IngestionModule.test.tsx`: **63 passed**, including the new mounted Session 27 → Session 10 selector regression plus existing draft-preservation and lineage tests. Existing unrelated React `act(...)` warnings remain.
- UI typecheck passed. `git diff --check` against `main@1c810a208e27be6efc7f21ed10bdcc18c05c0bb3` passed. The cumulative product diff is limited to the two leased Ingest UI files; no production build was written over serving assets.
- Commit the bounded changes to `codex/ingest-session-affinity-route-reset` based on current main and open one PR for PRIME review. Do not merge or mutate 5202.
- Rendered inspection remains before-fix evidence only: on the Session 10 route the selector visibly showed Session 27 while the source editor remained empty; Session 10 was also present in the options. No recap was loaded, processed, or modified. Recheck the corrected selector only after the reviewed build is available; real ingestion and persistence acceptance remain open.

## Rendered discovery and review boundary

- The triggering browser route targeted `world=elderwyld`, `campaign=longmont-c2`, `session=session-10`. The rendered selector showed Session 27 even though Session 10 was present; the editor was empty and the user did not load the prior artifact. No retained recap or database state was changed.
- PR #1318 implemented exact-session defaulting and merged at `1ed861d7c123fd62d7583204eff7f2236a5680e4` from head `e3c231dab039f6842864888c8fb71e5a2ead58d7`. Its initial-mount test did not cover navigating between sessions while the component stayed mounted. The current repair adds that case.
- This remains before-fix rendered evidence. 5202 has not been updated or changed, and this handoff does not claim the corrected selector has passed browser acceptance. Real ingestion and persistence acceptance remain open.
