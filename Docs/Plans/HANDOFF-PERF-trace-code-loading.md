# Trace and prompt presentation follows inspection

**Status:** ACTIVE; PRIME owns this bounded successor under the frontend-foundation goal.
**Base:** 08a2ae057ea759482ffcd72d50c41a477f9ea7a3; branch codex/trace-code-loading, existing buddy-context-loop checkout.
**Topology:** serial successor to accepted 1487; no overlapping active trace renderer lane found.

## Invariant critique

Keep transcript, saved-request recovery, trace read/cache/poll ownership and enabled gating mounted exactly as before. Defer only trace/prompt renderer code. Separate the small evidence/prompt tab controller from the prompt viewer so a transcript with closed inspection does not pull prompt rendering into the entry bundle. No compatibility re-export from the former module; update all current imports. Stable shared deferred wrappers provide local loading/error/retry. World/turn/conversation/trace binding and explicit read retry remain unchanged. A lazy presentation must not start extra reads, resend messages, or discard cached trace bytes on close/reopen.

## Exclusive expected write lease

- This handoff and predecessor HANDOFF-PERF-surface-code-loading.md settlement.
- src paths below are relative to apps/live-control-ui.
- src/planSurface/components/ResponseEvidenceTabs.tsx (new extracted controller).
- src/planSurface/components/{BuddyPromptInspector,BuildComposeProposal,WorldPlanAgentConversation,BuddyContextTraceLoader,PlanAgentInteractionBar}.tsx: import/render code boundaries only; no request/controller semantics change.
- src/planSurface/components/{BuddyPromptInspector,BuildSourcePassageEvidence,BuddyContextTraceLoader}.test.tsx: current imports and async view readiness/cache-read proofs only.

Verify actual trace loader enabled/cache/poll/binding/late-result tests, prompt/evidence tabs, and shared deferred failure/state tests; tsc/build and initial/dynamic chunk audit. Inspect exact cumulative diff; independent exact-head review then merge/adopt on owned 5202. Native Debug open/close/reopen must show the saved trace without resending or repeat completed trace reads, and 17 protected canonical responses must remain unchanged. No schema/API/provider/admission changes or backward compatibility. Remaining payload/list bounds, heavier controller/editor split, launcher sizing, user+Agent Rules lookup and native Combat remain open.

## Pre-review evidence

All 46 cases across trace loader, prompt inspector, source evidence, trace rendering, action prompt and shared deferred wrapper suites pass. The real World-history Debug activation case also passes (215 unrelated cases intentionally not run); full broader owner-suite baseline failures remain documented by predecessors, not claimed repaired. Existing loader tests exercise disabled reads, exact cache reuse on close/reopen, recording poll termination, failed read retry without resend, World/turn/conversation binding rejection and late-response retirement. No read/cache/poll implementation changed. TypeScript and production Vite build pass; cumulative diff inspected and diff check clean. Diagnostic styles are imported by their actual tab/prompt consumers, avoiding a style dependency on opening Debug.

Initial JS remains a single static entry, 1,324,902 raw / about378,940 Vite gzip bytes, versus accepted1,359,390 /387,904. Trace/prompt/legacy trace renderers have separate dynamic entries. Native exact Debug request/chunk/cache behavior and protected-state acceptance remain pending review/merge/adoption.
