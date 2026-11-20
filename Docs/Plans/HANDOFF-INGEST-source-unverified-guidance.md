# INGEST: guide operators past an unverified saved candidate

**Status:** ACTIVE — PRIME authorized this bounded user-guidance repair on 2026-10-17.
**Base:** `origin/main@82b2099bfc7f68bd4497fa47cbb42ec91e6c3181` (merged #1356).
**Branch:** `codex/ingest-source-unverified-guidance`, advanced from the former base to current `main` through GitHub before implementation; shared local Git metadata is read-only.
**Checkout:** `/home/drakosfire/.codex/worktrees/996b/DungeonMindBuddy`, reused assigned checkout.
**Observed checkout head:** `a0db876f5c6386978d61f18d82c1f979688e5272`; its leased product files match current main. GitHub compare confirmed the eight commits since #1353 change only Conversation UI files, disjoint from this lease. Shared Git metadata is read-only.
**Topology:** serial Ingest UI successor. Open PR #1235 remains on the Graph Review/source-observation files and does not overlap this three-path lease. Do not modify Graph Review, APIs, or route contracts.

## Mission

When the selected campaign/session has a retained graph candidate marked `source_unverified`, explain in the main Ingest workspace that it is preserved history and cannot be treated as current evidence. Give the operator the normal next step: load or paste the verified recap for the selected session, then Process through the ordinary flow. Do not create a legacy recovery or replay path.

## Evidence and failure

On the retained Session 29 route, status reports a saved graph candidate but no verified normalized recap or current World binding. The source selector has no Session 29 entry, and Graph Review is correctly unavailable. Today the user sees the terse `source unverified` label and low-level proof details; they lack a plain-language explanation of whether the old candidate can be used and what action creates a valid current result.

The retained `f43e48e6-c775-4960-824f-fb398fe50bb9` artifact is not a source for rerun or publication. It remains untouched. The user owns any real Process initiation. Do not mutate source, candidate, World, database, runtime, or serving assets during this slice.

## Exact write lease

- `Docs/Plans/HANDOFF-INGEST-source-unverified-guidance.md` — this bounded contract and truthful implementation evidence.
- `apps/live-control-ui/src/modules/IngestionModule.tsx` — show a concise guidance card in the main Ingest workspace only when the current selected result is source-unverified; distinguish a retained run from a source-check failure with no exact run; point to the existing normal source controls; do not add a review, retry, recovery, or publication action.
- `apps/live-control-ui/src/modules/IngestionModule.test.tsx` — prove current-selection scoping, plain-language guidance for retained and no-run source-unverified states, no Graph Review exposure, and no Process action while the source is missing; preserve ordinary Process eligibility after a real source is supplied.

No `MemoryIngestPage`, Graph Review, shared navigation, API, server, schema, extraction, candidate packaging, source content, corpus, World Graph, database, environment, build output, or port/5202 write is authorized. Return to PRIME before widening the lease.

## Invariants and failure cases

- Use only a status result whose campaign/session equals the currently selected campaign/session (`resultOwnsSelection`). A stale A→B result cannot show a message for B.
- Keep all status copy rooted in observable fields: say a retained candidate is unverified only when the exact current result has `graph_preview.status === "source_unverified"` and an exact run ID; otherwise describe only the source verification gap.
- Never present a source-unverified candidate as reviewable, current, or publishable. Do not make the exact-run Graph Review action available.
- Do not reuse, repair, resubmit, or publish the historical run. No processing starts from the guidance card.
- Keep Process unavailable until the normal flow has actual recap text or a verified saved source. Existing source eligibility remains authoritative.
- Keep the copy compact, in the main workflow, and free of internal run IDs, file paths, schema/status jargon, and raw server recommendations.

## Verification

- Focused `IngestionModule.test.tsx` regressions for exact selected-result scoping, retained-run and no-run guidance, missing-source Process gating, no Graph Review, and ordinary source behavior.
- Run the full focused component suite, UI typecheck, and `git diff --check` against the cumulative main diff.
- No real Process, provider call, source/candidate/World/database write, server change, or 5202 asset modification. PRIME retains review and merge authority.

## Implementation evidence (in flight)

- Added a main-surface guidance card for a current source-unverified result. It explains that an exact retained candidate is history, not the current result, and directs the operator to load or paste the correct recap through the normal flow. A source-verification failure without an exact run gets separate copy; neither variant exposes internal run IDs or raw paths.
- Source-unverified status now blocks the Graph Review action even if a stale nested preview still says `candidate_validation_ready` or `preview_union_store_ready`. Existing Process eligibility remains tied to actual recap text or a verified saved source.
- Tests cover both `source_unverified` and ready-shaped stale candidate statuses, confirm that rendering causes only `inspect_status` requests, assert no Process or Graph Review action is exposed without a verified source, and extend the A→B→A regression to prove a stale source-unverified response cannot show guidance for the current selection. The existing source-check test covers a source-verification gap without an exact candidate; verified saved-source processing remains covered by the existing ready-source test.
- `npm test -- --reporter=dot --run src/modules/IngestionModule.test.tsx`: **78 passed**. Existing React `act(...)` warnings remain in unrelated editor/empty-navigation tests.
- `npm run typecheck`: passed.
- `git diff --check`: passed.
- GitHub confirms open PR #1235 changes the Graph Review/API paths and does not overlap this Ingest module/test lease. No code review/merge or rendered 5202 acceptance has been performed for this successor.
