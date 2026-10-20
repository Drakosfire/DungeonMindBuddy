# PERF — coalesce protected read acquisition

**Status:** ACTIVE. PRIME owns design, implementation and delivery under the operator's frontend-foundation goal.
**Base:** Buddy main5696490647c0e1ac1d1c4083ba22481ab2a64639.
**Lane:** serial, codex/bounded-protected-reads in existing buddy-context-loop checkout; one implementation PR.
**Authority:** OverMind assessment51 at03024f34bf3be8343a01edb0d9cc797eb1bdae82 and operator implementation goal.

## Program meaning

Sequence: bounded reads → demand-loaded code/media → Rules lookup for user AND Agent → native Combat. RulesLawyer means an inspectable citation-bearing lookup capability which Buddy's Agent can call;763–765 and existing RulesLawyer/RulesIngestion experiments are inputs, not the definition of completion. Only after all four objectives are delivered may rule-graph ingestion/reasoning experiments begin; those also target user and Agent query. No experimental graph prerequisite is introduced into lookup.

## First bounded capability and invariant critique

Equivalent protected reads may share a pending transport within the same access epoch, exact URL/query, method, body, headers and request options. Reads have no settled cache here. Commands, provider calls and writes never coalesce. A write starts a new read wave at dispatch and settlement (success, failure or unknown transport outcome), so a post-write refresh cannot join a pre-write or during-write request. Overlapping writes each invalidate at their own boundaries. The initial cookie-session bootstrap emits a credential event while the requesting graph read is already waiting for that bootstrap; this is a concrete reproduction target, not permission to suppress actual invalidation.

Failure cases: distinct World/revision/query/page must remain separate; bearer rotation/revoke/reconnect must fence old admission; cookie recovery must remain bounded and keep its existing retry rules; one subscriber cancelling must not cancel another; last subscriber cancellation may abort owned transport; failed/settled reads must be released and a subsequent explicit refresh must fetch again. Sharing a Response requires an independently consumable clone per caller. Cancellation and backend errors must not become empty evidence. Existing native projection warm cache must invalidate on real credential transitions, including renewal, without treating initial bootstrap as a new authority epoch. Shared parsed response mutation is avoided by sharing transport only.

## Exclusive expected write lease

- This handoff.
- apps/live-control-ui/src/api/liveApi.ts (read transport/credential/cache invalidation only).
- apps/live-control-ui/src/api/liveApi.test.ts (replace one incomplete synthetic Response fixture with a real Response; preserve its error assertions).
- apps/live-control-ui/src/api/inFlightReads.ts and inFlightReads.test.ts (new internal coordinator).
- apps/live-control-ui/src/api/liveApi.readEfficiency.test.tsx (new transport+mounted-provider regression evidence).

No overlapping paths in current open product PRs have an active implementation lease: Rules763–765 remain paused/stale candidates and receive no dependency or rules-path edits; active Ingest1235 owns source observation review, not shared read transport. No lockfile, backend, schema or authority changes.

## Verification and delivery

Prove cold bootstrap mounted graph acquisition, concurrent history/evidence/candidate reads, World/page/query isolation, success/error freshness, auth epoch separation, cookie recovery, cancellation ownership and post-write refresh. Run existing credential/recovery/projection/provider owner tests and production build. Inspect exact cumulative diff and obtain independent review before merge. Adopt accepted UI only on established5202 artifact target, after re-anchoring its lease/process and preserving current assets and data/draft snapshots; no API restart, migration, extraction, inference or user-data writes. Browser acceptance compares five-screen requests, scope/route continuity, retained Plan/Play/Build state. Cleanup temporary probes and retain private aggregate evidence. Subsequent payload bounding, remaining cause removal and demand-loading get separately bounded successor slices; this handoff does not claim the whole goal complete.

## Author evidence before acceptance

Cold bootstrap reproduced two managed network requests at the base and one after the fix. Final transport/provider/cache/recovery cohort259/259 passes; TypeScript and production build pass. Supplemental conversation/Plan Cards/review/evidence cohort236pass/8fail. All8 are in the unchanged conversation-history suite and reproduce with the exact base liveApi source substituted in-memory via a temporary Vite transform (207pass/8fail in that suite); no checkout switch/export or other production source change was used for that baseline proof. The incomplete Response fixture correction preserves its original diagnostics assertions.

Architecture Cycle1 held775ea76314a22f66cbf60f499c0b9da8597902d2 for a new during-write→post-write freshness race. The candidate now invalidates at settlement as well as dispatch, with success, failure, unknown outcome and overlapping-write coverage. Independent re-review and5202 adoption remain required. The broader goal remains active.
