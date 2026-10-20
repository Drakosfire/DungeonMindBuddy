# One owned trace observation per inspected turn

**Status:** COMPLETE; source lease released, paired1489/1490 delivery accepted on5202.
**Base:** cdb5867b066a5c422180695778bc8b6668b7cfc2; branch codex/turn-inspection-acquisition, existing buddy-context-loop checkout.
**Topology:** serial successor to accepted1488. No overlapping active acquisition lane found.

## Invariant and design critique

Native Debug→The Prompt independently fetched the same completed45,251-byte trace twice. Lift the existing trace read/cache/poll owner to one parent resource per rendered World-conversation turn; both views subscribe to it. This is one captured historical observation, not a freshness claim for the mutable all-attempt list. Retain only a nonempty complete/closed terminal observation through closing/reopening within the same mounted turn inspection session, provide explicit Refresh trace to revalidate, and retire it on World/conversation/turn/lifecycle/access/read-wave change or unmount. Do not introduce a global TTL cache or share raw provider request bodies. Historical source passage readers remain separate for the next bounded endpoint slice.

Use the owning turn lifecycle for the single canonical recording decision. Preserve existing enabled gating, exact whole-payload binding validation, recording poll interval/stop, explicit failed-read retry and late-result rejection. Aggregate consumer demand gives one poll owner; closing one consumer must not cancel another. Latest/failed/error/empty observations remain truthful. Active, empty or incomplete snapshots, and terminal snapshots above256KiB serializedUTF8, are not retained after all consumers close; active display may still show the existing admitted response. No generalized multi-entry cache. Expose read-wave subscription/version from existing protected transport so credentials and write dispatch+settlement synchronously retire private display and late completions cannot repopulate. Hidden consumers must not start polling. Optional trace AbortSignal is transport control, not API/query data.

Architecture's design critique favors this parent-owned selected-turn resource over a generalized cache. Exact historical passage endpoint work is a separate capability. This does not assert immutability or perpetual currency from a trace ID.

## Exclusive expected write lease

- This handoff and predecessor HANDOFF-PERF-trace-code-loading.md settlement.
- UI src/api/inFlightReads.ts and its test: observable read-wave version, existing transport semantics preserved.
- UI src/api/liveApi.ts and liveApi.worldConversation.test.ts: trace signal only.
- UI src/planSurface/components/BuddyTurnInspection.tsx and its test (new parent owner).
- UI src/planSurface/components/BuddyContextTrace.tsx and its test: view receives owning activity to distinguish active recording from an ended turn with an incomplete capture.
- UI src/planSurface/components/BuddyContextTraceLoader.tsx and its test: shared consumer/view, no standalone alternate owner.
- UI src/planSurface/components/WorldPlanAgentConversation.tsx: per-turn provider only.
- UI src/planSurface/WorldPlanAgentConversation.worldHistory.test.tsx: real Debug/Prompt acquisition and signal assertions.

Verify Debug→Prompt one fetch, close/reopen retained captured observation, explicit refresh/new attempts, one recording poller with two consumers, partial cancellation, credential/write-wave and World/conversation ABA completion fencing, failed retry/no resend, oversized closed release, cancellation through body and no query signal leakage. Inspect cumulative diff, exact-head independent review, PR/merge/adopt5202; protected17 responses unchanged. No backend/schema/provider/dispatch changes. Full goal remains open: other payload/list bounds, heavy editor/controller split, launcher delivery sizing, user+Agent Rules lookup, native Combat. Rule-graph experiments only after all objectives complete.

## Author evidence before independent review

- Protected transport/projection cohort:275passed across8files. Observable wave publication preserves existing mutation dispatch/settlement and credential fences; a faulty observer is logged with its error and cannot break transport or starve other owners.
- Final focused ownership cohort:28passed across3files, including11 shared-resource cases, inherited loader behavior and read-wave tests. Tests cover two viewers/one poll owner, explicit refresh, known lifecycle changes/new attempts, partial/last cancellation, credential and mutation waves, separate World/conversation/turn ABA, failed retry, mismatch/disabled zero acquisition and oversized closed release.
- Real World-history Debug→Prompt→close/reopen integration passes with one acquisition; new optional signal is verified as transport-only on the exact encoded trace endpoint.
- Broader World-history/persistent-host cohort:261passed/15 inherited failures, same8history+7integration failures recorded by predecessors. No new failure remains. Source inspection confirms no prompt/provider/dispatch/draft/recovery path moved.
- TypeScript/Vite production build pass; cumulative source/test diff inspected, diff check clean. Native5202 one-read/explicit-refresh/authority continuity and protected17state comparison remain pending reviewed merge/adoption. Read waves can conservatively revalidate an actively viewed observation after unrelated writes; hidden consumers never acquire/poll.

The bounded retention ceiling is per mounted turn inspection, not a total application-memory claim. API all-attempt list is still mutable and potentially large; this snapshot is labeled Captured observation with Refresh trace, never advertised as current all-attempt authority. Raw prepared requests remain separate no-store reads. Historical source-passage payload bounds/reuse are explicitly a successor.

## ReviewCycle1 hold and correction contract

Architecture held24e809c223fb627605d490daf1a0375f900d52cc: the inherited attempt.closed_at polling predicate violated the new canonical owning-lifecycle contract. Independently reproduced running owner + closed prior attempt stopping after one read, and terminal owner + open capture continuing indefinitely. Held head was not merged/adopted.

The correction makes accepted/running owner status the sole polling decision: one2-second poller while inspection is demanded, including between attempts; terminal owners never background-poll, even when a capture is open/incomplete/empty. Explicit Refresh remains a read only. Preserve actual recorded fields; views label an ended owner's unclosed snapshot incomplete without fabricating trace closure. Reuse across close only for a nonempty, fully closed/complete captured observation under a terminal owner. Active, empty or incomplete snapshots are released when all viewers close, so reopening reads fresh. Known lifecycle changes retire the observation. Add mismatch/partial/empty close-reopen cases and review the new exact head.

## ReviewCycle2 author evidence

Corrected lifecycle mismatch cohort39/39passes across shared resource, loader and trace view. Final9-file diagnostic/transport-owner cohort80/80passes; broader history/host remains261pass/15sameinheritedfailures, including the real Debug→Prompt single-acquisition case. TypeScript/Vite build and diff check pass. Existing275-case protected transport evidence remains applicable: those production paths did not change in this correction.

Tests now explicitly witness three reads over4seconds for a running owner between closed attempts, then no background reads after its terminal lifecycle transition; terminal empty/open/incomplete captures stay at one read over4seconds, reopen freshly and refresh only explicitly. Two viewers retain one poller. A terminal unclosed view is labeled incomplete without changing recorded closed_at. Completed closed snapshot reuse still proves Debug→Prompt one fetch. Current source is reviewable; native delivery remains pending Cycle2 approval/merge.

## ReviewCycle2 approval and source merge

Architecture approved exact c4b776128c643f14a6b207a1f6c767c6a19d57aa, independently80/80owner cases plus both formerly failing review probes and real World Debug→Prompt integration. PR1489 merged279ba2e245437f23577f61e923fbb94f0a4921fe. No held head was adopted. Source lease released.

Runtime adoption is deliberately pending a newly verified predecessor1487 global CSS regression: a fresh Index load has no lazy Plan stylesheet, while globally mounted AgentInteractionChrome still depended on it. Native launcher button1277×1274/image1254×1254 instead of the defined80px button. This is not a trace-acquisition failure. Corrective HANDOFF-PERF-shared-agent-chrome-styles.md owns stylesheet/import paths and this delivery settlement; adopt the reviewed combined source and verify trace one-read/Refresh/protected17 after correction. Existing5202 still serves accepted1488 assets, not unaccepted1489 assets. No runtime/data operation accompanied this source merge.

## Paired delivery accepted

Architecture ReviewCycle1 approved exacta27fa2da6929a8f202766f78645a3815afcd07e2; PR1490 merged7ab8340461a465b29744a4da143f84c1cd9f4187. Combined1489/1490 adopted atomically on owned5202, API untouched; default index-D-rXrI1c.js/indexSHA256371b1bbd42e64ae3a2b1cfafbdae91490d9653cfaa31be987a4ca9c2f313a34e. Native default root confirms80px launcher before visiting Plan and the exact accepted asset; saved Plan Cards renders normally. Candidate desktop/narrow/load-order checks prove existing launcher/pane geometry, with viewport reset. Debug→The Prompt shared one200trace GET; explicit Refresh added exactly one more200GET, zero provider turn POSTs. All17protected responses unchanged after candidate and default acceptance. Screenshots unavailable; native DOM/rectangle/request metadata evidence only, no target-laptop latency claim. Original assets retained for active tabs/rollback. Temporary probes/tabs cleaned after acceptance. Remaining payload/list/controller/media work and Rules/Combat stay open.
