# PERF — conversation history follows consumption and recovery

**Status:** COMPLETE; accepted on 5202, write lease released. The full frontend-foundation goal remains active.
**Base:** main e13221a8415b84db1f0e0943530e39652873f55b; branch codex/conversation-history-demand, existing buddy-context-loop checkout.
**Topology:** serial successor to accepted 1484; no concurrent read-efficiency implementation PR.

## Invariant / critique

The persistent World conversation controller must keep drafts, registrations, in-flight sends and recovery owners alive, while an ordinary closed Buddy pane should not read its transcript. Existing native traces show Plan history reads at recovery backoff intervals; preserve that reconciliation rather than treating every repeat as a duplicate. Play's active-pointer mutation also separates reads conservatively. Demand-gating ordinary history before user opening avoids the premature read without weakening mutation freshness.

History may load when the pane is open OR a currently owned saved/unconfirmed request, pending command, active send or active shared turn needs reconciliation. Keep existing exact World/scope/visible admission guards; do not widen hidden-surface ownership or delete stored request bytes. Closing/reopening must retain composer drafts, show current canonical history on reopening, and not repost any provider request. A history effect no longer owning a read should abort its latest-page and older-page subscriptions; older-page single-flight and post-verification ownership checks also apply; shared transport must preserve other subscribers. Keep terminal/error semantics and cached correctly scoped history; optional AbortSignal is transport control only and never becomes query/provider data.

## Exclusive expected write lease

- This handoff.
- apps/live-control-ui/src/api/liveApi.ts: history options/transport AbortSignal only.
- apps/live-control-ui/src/api/liveApi.worldConversation.test.ts: history cancellation transport proof.
- apps/live-control-ui/src/planSurface/components/WorldPlanAgentConversation.tsx: history demand and effect cleanup only.
- apps/live-control-ui/src/planSurface/WorldPlanAgentConversation.worldHistory.test.tsx: isolated pane/recovery demand and current signal expectations.
- apps/live-control-ui/src/agentInteraction/WorldAgentConversation.planPlay.integration.test.tsx: real persistent host Plan/Play/Build closed/open, draft/switch/pending recovery tests.

No registry, prompt, dispatch, backend/schema/dependency changes. Paused Rules 763–765 are candidates, not active owners; 1188/1190 welcome proposals do not own the controller/transport paths. Prior PERF leases released. Verify native closed/open behavior, cancellation isolation, pending/recovery continuity, exact scope switching and existing owner tests; inherited 8 history-suite failures must remain identified against the existing exact-base proof. Inspect cumulative diff, independently review exact head, merge and adopt existing 5202 assets. Read-only native browser acceptance must preserve 17 current protected JSON responses and existing drafts/notes/scene position; use owned temporary probes/tabs and clean up. No provider calls for this slice. Code loading, payload/list bounds, user+Agent Rules lookup and native Combat remain outstanding.

## Pre-review verification

- Exact cumulative source/test diff inspected; `git diff --check`, TypeScript build and production Vite build pass.
- Eight transport/projection suites: 272 passed. New real-host Plan/Play/Build demand, closed pending recovery, draft retention and late-result cancellation cases plus saved Plan recovery: 8 passed.
- Full two owner suites: 261 passed, 15 failed. The same 7 integration failures were reproduced against exact base e13221a (in-memory Vite base transform), and the same 8 history failures were previously reproduced against the accepted baseline. They concern obsolete rich-text/UI expectations, recovery expectations and unmocked extra fetch totals. No new failure remains; this slice does not repair or hide these inherited failures.
- Older-page test now also proves a New Conversation aborts the abandoned page and can load the new conversation's older page. API test proves the optional signal stays out of the exact history query and aborts owned transport.
- Native browser acceptance and protected-state comparison remain pending merge/adoption. No provider request was sent by these checks.

## Independent review, merge and native acceptance

Architecture ReviewCycle1 approved exact head a2320b4f2e2e40c13f89821dd63ea1702e4d6ea8 in chat (no external review post). Independent transport cohort 256/256 and 9 targeted owner cases pass; no blocking source finding. PR1485 merged at 4a4173ba90aca0cd1e76360627bdcae2635a0ab4; re-anchored before UI adoption.

Owned 5202 process PID17085 retained, API unchanged. Atomically adopted reviewed index-B06pSrlL.js; served index SHA256 3640f71e458431967a30b69607d81eb53f817f1c53148579d1edd625527405ea; prior hashed assets retained for active tabs/rollback.

Native current-host six-second samples: Build closed history 1→0 and API bytes 2,260,298→2,194,663; ended Play review history 2→0 and API bytes 2,362,540→2,231,414. The Build native trace records no history until opening Buddy at ~12.97s, then exactly one read, and one fresh read on reopening at ~27.97s. A temporary unsent composer draft survived close/reopen, then was restored to the original empty value; no provider request was sent. Actual Plan retains saved recovery demand (2 reads in the sample), correctly not forced to zero. Document/Cards retained Journey north scene and rendered content.

All 17 protected canonical JSON responses unchanged before/after native acceptance, including Plan, Build, ended Run/review/active pointer, media and registry state. Private evidence retained in established experiment state under history-demand-*; temporary probe HTML/tabs removed. Screenshot APIs remain unavailable in this browser; acceptance uses rendered DOM, native request metadata and protected-state comparison. Warm/cache-uncontrolled host samples are not an older-laptop performance claim.
