# INGEST: preserve campaign and session affinity in prior recap selection

**Status:** ACTIVE — PRIME explicitly dispatched this bounded selector repair after PR #1315 merged on 2026-10-17.
**Base:** fetched `origin/main@53c9fd723258a4a528fdfb81ee725497fb7ebbae`.
**Branch:** `codex/ingest-session-affinity-default`.
**Checkout:** `/home/drakosfire/.codex/worktrees/996b/DungeonMindBuddy` (reuse the assigned checkout).
**Topology:** parallel-independent with draft PR #1235, whose checked changed-file list is limited to Graph Review/API observation-review paths and does not overlap this write set. PRIME owns independent review and merge of this one PR. PR #1315 is merged. PR #1244 edits the recap evidence materializer and separate handoff/tests, is not a dependency, and remains held per PRIME.

## Mission

When a user opens Ingest for a campaign/session, the prior processed recap selector must not silently default to the newest recap from another session. Default only to a recap whose `campaign_id` and `session_id` exactly match the current target. If there is no exact match or no valid session target, leave the selector at its “Load a processed recap…” placeholder. Selecting an option remains an explicit user action, and loading remains a separate explicit action.

## Invariant and failure cases

- Session 10 must never select Session 27 merely because Session 27 is the latest registered recap.
- A returned artifact list must not select another campaign or session after the user changes either target while that list request is pending.
- The selector must show only artifacts whose `campaign_id` matches the selected campaign.
- When the campaign changes, stale options from the previous campaign must not remain selectable while the new list is loading.
- An exact matching artifact may be preselected; it must not be loaded automatically.
- Explicit user selection, local draft contents, source lineage checks, and load/reopen behavior remain unchanged.

## Exact write lease

- `Docs/Plans/HANDOFF-INGEST-session-affinity-default.md` — this bounded contract and evidence.
- `Docs/Plans/HANDOFF-INGEST-rendered-recap-acceptance.md` — factual settlement of merged PR #1315 and pointer to this successor only.
- `apps/live-control-ui/src/modules/IngestionModule.tsx` — exact-match defaulting against the latest session target when a campaign list resolves, campaign-change request invalidation, and clearing prior-campaign options. No unrelated presentation changes.
- `apps/live-control-ui/src/modules/IngestionModule.test.tsx` — regression coverage for exact match, no match, explicit load remaining explicit, and stale list responses after target changes.

No API/server/schema, extraction/materializer, raw source, graph publication, provider, database, retained artifact, or 5202 changes are leased. Return to PRIME before expanding scope or write paths.

## Verification

- Complete `IngestionModule.test.tsx`: **49 passed**, including existing draft-preservation and lineage tests.
- `git diff origin/main --check` passed.
- UI typecheck is blocked by five existing TypeScript errors in untouched `src/planSurface/components/WorldPlanAgentAnswer.tsx` (lines 47, 49, and 50). I did not run the production build because its first step is the same failing TypeScript check; no changed Ingest path is named in the diagnostics.
- Inspect the exact cumulative `origin/main` to head diff. Commit and push this branch, then open one PR for PRIME review. Do not merge or mutate 5202.
- Rendered acceptance is limited to read-only inspection of the current selector state. PRIME says the user may inspect and author now; extraction richness/readiness remains unproven. A new recap can be processed as dogfood, but any result should be treated as an experiment. Do not load a prior recap from the affected selector until this repair is reviewed. No recap was loaded, processed, or modified during the observed mismatch.
