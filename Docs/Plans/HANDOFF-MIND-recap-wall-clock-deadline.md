# Fresh recap inference wall-clock deadline

Status: ACTIVE under PRIME dispatch, 2026-10-13. Implementation and one PR are
authorized; merge, provider execution and publication are separate.

## Authority and lane

- Owner: Buddy MIND extraction. GenerationEngine remains the exclusive inference
  IO owner. Sol 6.1 Light checkpoint for process cancellation/outcome accounting.
- Beginning: remote Buddy main `c4a81c6661dd292c6adb9d314ce4d154d1e78352`.
- Branch: `codex/recap-wall-clock-deadline`; isolated checkout:
  `/tmp/buddy-recap-wall-clock-deadline`.
- Topology: parallel-independent. Open PRs #1014, #869, #844, #826, #798,
  #765, #764 and #763 inspected; none owns these extraction paths. Existing
  #1118/#1120 presentation/context work is merged at this beginning.
- Exact writes: this handoff; `src/graph_memory/extraction/bounded_recap_execution.py`;
  `tests/test_bounded_recap_execution.py`; if process mechanics require it, one
  private worker helper `src/graph_memory/extraction/_recap_inference_worker.py`
  and its focused test `tests/test_recap_inference_worker.py`.
- PRIME amendment: `tests/test_graph_ingest_packaging_live_call_shape.py`, only
  its bounded schema-failure fake seam. Spawn requires pickleable factories and
  shared counters; preserve the actual packaging file/digest/ledger assertions.
- No runtime, port, retained database, corpus, registry or publication writes.
  No provider calls, dependency/provider/SDK edits or new owning contracts.

## Problem and invariant

R4's GE receipt timed out at 60,030 ms, but the synchronous wrapper returned at
360.15 seconds. `asyncio.run` waited another 300 seconds for default-executor
shutdown. The per-call and remaining run budgets must bound startup, inference
and cleanup together. An owned process may be terminated/reaped at the deadline;
no unrelated process may be signaled.

The child must preserve completed text/receipt before cleanup and before local
schema validation. A known receipt remains known when cleanup hangs. Missing
receipt means external outcome unknown, with unknown usage/cost and no automatic
redispatch, retry or fallback. GE request/provider ownership and existing null
usage semantics remain intact. Error/ledger metadata must not contain private
request/response bodies or exception messages.

## Proof obligations

Offline owning-boundary tests must recreate blocked default-executor cleanup,
bound parent return, leave no owned child alive and forbid another call. Cover
missing receipt, completed receipt, schema failure, known provider failure,
startup/worker failure, deadline/run-budget reduction and normal accounting.
Inspect cumulative beginning-to-head diff, focused checks, commit/push one PR,
then return exact head and independent-review request to PRIME.

## Preserved R4 evidence and authorization cross-reference

Do not rewrite `/tmp/c1s16-ge-deepseek-reconciled-r4-{final-authority,attempt,result}.json`
or the existing response/ledger/manifest. Original authority label
`user-authorization-2026-10-13` corresponds to operator reply
`call_htpno1uKXUvoSWZIWkArIcKy`: "Authorize the corrected ingestion run".
The R4 per-call usage/cost is null; its result's zero aggregate came from `or 0`
and cannot establish zero provider consumption or billing.

## Future run boundary

After acceptance, prepare a distinct one-use candidate-only runner pinned to the
accepted Buddy commit and unchanged C1S16 raw/normalized/span/context digests.
It must run through `exec_command` with `sandbox_permissions="require_escalated"`
and explicit OpenRouter destination/grant justification; an ordinary shell command
does not escape `codex-linux-sandbox`. Budget remains max 8 calls, 60s/call,
480s/run, 8192 output tokens/call, no retry/fallback or publication. Do not execute
under the consumed R4 grant. Explicit SDK timeout is a GenerationEngine follow-up.

## Implementation evidence

One owned spawned process per pass calls GenerationEngine. A private atomic
receipt records returned text/observation or GE failure before async cleanup.
The parent applies the remaining call/run wall budget, reserves 50ms (or one
quarter of a shorter remaining budget) for kill/reap, and signals only its child.
Missing GE receipt produces `external_outcome=unknown`; spawn failure before
dispatch produces `not_started`. Both stop. Forced cleanup also stops further
passes while preserving an already returned result/failure and null accounting.
Injected engine factories must be pickleable; production uses a top-level partial.

Focused offline proof: 50 passed across `test_bounded_recap_execution.py`,
`test_recap_inference_worker.py`, and `test_graph_ingest_packaging_live_call_shape.py`.
The real GE test receives its 50ms timeout observation then blocks on a default
executor thread; the parent kills/reaps within a 2s budget plus a 250ms scheduling
tolerance. Missing receipt, worker exit/failure, stalled aclose, normal response,
schema rejection, known provider failure and reduced remaining run budget are
covered. Original semantic request/schema tests use an explicitly local fake
worker seam; the new process tests and actual packaging test use real spawning.
All changed Python paths pass Ruff and the cumulative diff passes whitespace checks.
Existing read-only prepared interpreter: GE `38d77f33d0e45b3be02459f43add560c2ca2ff8a`,
OpenAI SDK 2.24.0; tests import Buddy source from this isolated current-main lane.
No new provider request, SDK/dependency change or deployed runtime proof is claimed.

The next-run source must use the accepted repair commit, Core pin
`d81ed4e126c55ef8df57804c9ab7128b7499c7a1`, and GE pin above. Input pins remain
raw `e8b8399abc94ba38daa3151d68b550f0ebc1c90e7a9181552ac71aecb098c161`,
normalized `d44898920ee091ec32ca23fdfd07c83b4abaa452042ce4d70f45c3ab114b2330`,
span index `e7c742f7578ecd40d497e11339b25caf23d55b8db0d8c429c730ae587c50a81b`,
and the unchanged eight C1 context hashes in the preserved R4 authority.
R4's original runner hardcodes its old source checkout, Core pin and used paths:
changing PYTHONPATH alone cannot re-anchor it. Fresh runner/proof/authority/output
paths must be issued together before release. The launch must be structured tool
arguments with `sandbox_permissions="require_escalated"`, not a shell-only claim
of host execution. No next run has been released or executed in this implementation.
