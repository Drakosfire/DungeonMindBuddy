# RAKE: mounted Plan test harness repair

Status: ACTIVE
Owner: RAKE repair worker under PRIME's explicit two-path lease transfer
PR topology: parallel-independent
Authority/base: Buddy remote main `d9b7d1e1ef9c1ad4401e107694260ad4f19455b6`

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
/home/drakosfire/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node node_modules/vitest/vitest.mjs run src/planSurface/PlanSurfacePage.test.tsx
```
Capture baseline and repaired outcomes; inspect full base-to-head diff and changed paths.

## 8. Delivery
Commit, push and open one RAKE implementation PR; return exact head and evidence to PRIME for independent review. No autonomous merge.

## 9. Acceptance
- Existing mounted assertions remain intact.
- History and action fixtures conform to current response contracts.
- The mounted suite passes or remaining exact failures are explicitly reported.
- No production, runtime or forbidden-path changes.
