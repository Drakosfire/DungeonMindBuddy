# RAKE: mounted Plan test harness repair

Status: SETTLED — PR #906 merged; write lease closed
Owner: RAKE repair worker under PRIME's explicit two-path lease transfer
PR topology: parallel-independent
Authority/base: Buddy remote main `0f42fec0812655bb37c87b6be9a7fe5741d7f25f` (PRIME audit correction; fetched from GitHub)

## 1. Mission
Restore the mounted Plan regression suite's faithful API fixtures after World conversation history and Plan action projection were introduced. Preserve every behavioral assertion; no production behavior change.

## 2. State and activation
PRIME explicitly transferred only this test path from #886 for this repair. #886 retains Page/shell runtime paths; #904 retains Agent component and its focused tests. This lane has no unmerged behavioral dependency. Its handoff is pinned on its branch before implementation. No predecessor state claims need rewriting. After merge PRIME returns the exact revision and closes this lease; #886 re-anchors before its integration gate.

## 3. Isolation
Branch `codex/rake-plan-mounted-harness`, checkout `/tmp/dmb-rake-mounted-repair`. Use existing isolated UI dependencies, Node 24. No ports, DB, corpus, model calls or runtime restarts; preserve 5202 and 5203.

## 4. Write lease
| Path | Purpose |
| --- | --- |
| apps/live-control-ui/src/planSurface/PlanSurfacePage.test.tsx | Faithful history/action API fixtures and observed blank-Plan async race |
| Docs/Plans/HANDOFF-RAKE-plan-mounted-harness-repair.md | Exact repair contract and evidence |

## 5. Forbidden writes
| Path | Reason |
| --- | --- |
| apps/live-control-ui/src/planSurface/PlanSurfacePage.tsx | #886 lease |
| apps/live-control-ui/src/planSurface/WorldPlanAgentConversation.tsx | #904 lease |
| RTK.md | Preserve existing file |

All other source, APIs, types and configuration remain outside this lease.

## 6. Implementation constraints
Model the actual typed history/action response contracts. No assertion weakening, skips or production changes. Adopt the known blank-Plan wait only if the owner race reproduces. Unexpected failures must be diagnosed and reported rather than hidden.

## 7. Verification
From apps/live-control-ui with isolated node_modules available:
```bash
/home/drakosfire/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node node_modules/vitest/vitest.mjs run src/planSurface/PlanSurfacePage.test.tsx --configLoader runner
```
Capture baseline and repaired outcomes; inspect full base-to-head diff and changed paths.

## 8. Delivery
Commit, push and open one RAKE implementation PR; return exact head and evidence to PRIME for independent review. No autonomous merge.

## 9. Acceptance
- Existing mounted assertions remain intact.
- History and action fixtures conform to current response contracts.
- The mounted suite passes or remaining exact failures are explicitly reported.
- No production, runtime or forbidden-path changes.

## Contract migration and author evidence
PRIME explicitly adopted the test-only migration of stale pre-#900 expectations within this same lease. Baseline on remote-main audit correction: 32 failures / 18 passes. Empty history/action fixtures alone: 8 failures / 42 passes. Remaining assertions described removed behavior; the repair preserves these owning invariants:

| Old expectation | Current merged owning invariant |
| --- | --- |
| Local transcript and stable client thread ID | Refreshed server World history, exact Plan provenance, ordered turns, independent request correlations; no browser transcript dual write |
| New trace payload persisted locally | Server-owned completion; raw prompt, provider trace and request IDs excluded from browser storage |
| Trace toggle creates/mutates persistent thread | Mounted toggle works without creating a transcript; remount resets toggle; legacy trace remains inspectable and original bytes unchanged |
| Legacy provider pointer cleared on mount | Legacy bytes unchanged with no thread rewrite or render-phase update |
| Old credential labels and first-conversation copy | Currently merged labels, password input cleared, memory setter/clear verified; server-owned first conversation message |

The blank-Plan race is nondeterministic on baseline. The context-publication wait adopted from #886 ensures its owner context has mounted before asserting Agent-empty state; no assertion is dropped. Successful mock replies carry conversation identity and project typed exact-basis history. Empty action pages avoid fabricating extra committed-revision reads. No replay proof is invented: existing invalid/correlation/stale-basis tests still reject invalid replies.

Author verification: all 50 mounted tests pass. A follow-up run exposed a second pre-existing async assertion race: `findAllByText` returned the already-visible first reply before the second history refresh. The test now waits for both server-projected replies before checking their sequence and provenance. The runner loader avoids Vite's bundled-config writes into read-only shared dependencies. This is test-boundary evidence, not live product acceptance. PRIME independently reviews the exact head before merge.

## PRIME settlement — 2026-10-04

PR #906 reviewed head `7ea7e9d319e82dec6e33248cdbc74e0fda86d1be` merged at `6feb3059b2da4d2ec29966ce9723f0effc70108f`. PRIME independently reran the mounted suite: 50/50 passed. This test-only lease is closed; the historical sections above authorize no further writes.
