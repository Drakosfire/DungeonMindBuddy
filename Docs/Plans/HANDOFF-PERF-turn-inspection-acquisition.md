# One owned trace observation per inspected turn

**Status:** ACTIVE; PRIME owns implementation and delivery under the frontend-foundation goal.
**Base:** cdb5867b066a5c422180695778bc8b6668b7cfc2; branch codex/turn-inspection-acquisition, existing buddy-context-loop checkout.
**Topology:** serial successor to accepted1488. No overlapping active acquisition lane found.

## Invariant and design critique

Native Debug→The Prompt independently fetched the same completed45,251-byte trace twice. Lift the existing trace read/cache/poll owner to one parent resource per rendered World-conversation turn; both views subscribe to it. This is one captured historical observation, not a freshness claim for the mutable all-attempt list. Retain it through closing/reopening within the same mounted turn inspection session, provide explicit Refresh trace to revalidate, and retire it on World/conversation/turn/lifecycle/access/read-wave change or unmount. Do not introduce a global TTL cache or share raw provider request bodies. Historical source passage readers remain separate for the next bounded endpoint slice.

Use the owning turn lifecycle for the single canonical recording decision. Preserve existing enabled gating, exact whole-payload binding validation, recording poll interval/stop, explicit failed-read retry and late-result rejection. Aggregate consumer demand gives one poll owner; closing one consumer must not cancel another. Latest/failed/error/empty observations remain truthful. A closed snapshot above256KiB serializedUTF8 is not retained after all consumers close; active display may still show the existing admitted response. No generalized multi-entry cache. Expose read-wave subscription/version from existing protected transport so credentials and write dispatch+settlement synchronously retire private display and late completions cannot repopulate. Hidden consumers must not start polling. Optional trace AbortSignal is transport control, not API/query data.

Architecture's design critique favors this parent-owned selected-turn resource over a generalized cache. Exact historical passage endpoint work is a separate capability. This does not assert immutability or perpetual currency from a trace ID.

## Exclusive expected write lease

- This handoff and predecessor HANDOFF-PERF-trace-code-loading.md settlement.
- UI src/api/inFlightReads.ts and its test: observable read-wave version, existing transport semantics preserved.
- UI src/api/liveApi.ts and liveApi.worldConversation.test.ts: trace signal only.
- UI src/planSurface/components/BuddyTurnInspection.tsx and its test (new parent owner).
- UI src/planSurface/components/BuddyContextTraceLoader.tsx and its test: shared consumer/view, no standalone alternate owner.
- UI src/planSurface/components/WorldPlanAgentConversation.tsx: per-turn provider only.
- UI src/planSurface/WorldPlanAgentConversation.worldHistory.test.tsx: real Debug/Prompt acquisition and signal assertions.

Verify Debug→Prompt one fetch, close/reopen retained captured observation, explicit refresh/new attempts, one recording poller with two consumers, partial cancellation, credential/write-wave and World/conversation ABA completion fencing, failed retry/no resend, oversized closed release, cancellation through body and no query signal leakage. Inspect cumulative diff, exact-head independent review, PR/merge/adopt5202; protected17 responses unchanged. No backend/schema/provider/dispatch changes. Full goal remains open: other payload/list bounds, heavy editor/controller split, launcher delivery sizing, user+Agent Rules lookup, native Combat. Rule-graph experiments only after all objectives complete.

## Author evidence before independent review

- Protected transport/projection cohort:275passed across8files. Observable wave publication preserves existing mutation dispatch/settlement and credential fences; a faulty observer is logged with its error and cannot break transport or starve other owners.
- Final focused ownership cohort:28passed across3files, including10 shared-resource cases, inherited loader behavior and read-wave tests. Tests cover two viewers/one poll owner, explicit refresh, known lifecycle changes/new attempts, partial/last cancellation, credential and mutation waves, separate World/conversation/turn ABA, failed retry, mismatch/disabled zero acquisition and oversized closed release.
- Real World-history Debug→Prompt→close/reopen integration passes with one acquisition; new optional signal is verified as transport-only on the exact encoded trace endpoint.
- Broader World-history/persistent-host cohort:261passed/15 inherited failures, same8history+7integration failures recorded by predecessors. No new failure remains. Source inspection confirms no prompt/provider/dispatch/draft/recovery path moved.
- TypeScript/Vite production build pass; cumulative source/test diff inspected, diff check clean. Native5202 one-read/explicit-refresh/authority continuity and protected17state comparison remain pending reviewed merge/adoption. Read waves can conservatively revalidate an actively viewed observation after unrelated writes; hidden consumers never acquire/poll.

The bounded retention ceiling is per mounted turn inspection, not a total application-memory claim. API all-attempt list is still mutable and potentially large; this snapshot is labeled Captured observation with Refresh trace, never advertised as current all-attempt authority. Raw prepared requests remain separate no-store reads. Historical source-passage payload bounds/reuse are explicitly a successor.
