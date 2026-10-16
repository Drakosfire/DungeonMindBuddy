# AGENT: explicit uncapped Harness iteration support

Status: ACTIVE under PRIME's Mirathorn ordinary-conversation goal and operator instruction that calls/Graph operations need no fixed count cap. ARCHITECTURE independently reviews.

Base `fc2807af1df456f47c71592a7fe404a1852e3048`, branch `codex/harness-nullable-iterations`, isolated non-serving checkout `/tmp/prime-recap-mention-boundaries`. Pinned first before implementation. Serial prerequisite to the ordinary Agent consumer. Current open PRs inspected; no active patch/dependency/iteration owner. Solo implementation; no serving, provider or retained database operations.

## Invariant and failure cases

The pinned Harness default is 90 iterations. Explicit `max_iterations=None` must mean no iteration count ceiling, while omitted/default and finite integer behavior stay unchanged. Preserve iteration accounting, refund semantics, provider pre-dispatch veto, terminal uncertainty, cancellation and finalization. An uncapped turn must not silently request the SDK's count-exhaustion summary or retire tools. Do not use a huge finite integer or non-finite numeric value as a substitute.

## Exclusive write set

- `Docs/Plans/HANDOFF-AGENT-nullable-harness-iterations.md`
- `Docs/Plans/HANDOFF-APP-nullable-execution-counts.md` — predecessor settlement
- `patches/hermes-agent/0001-pre-dispatch-budget-veto.patch` — reproducible pinned SDK changes and owning tests
- `tests/hermes_patch/test_pre_dispatch_budget_veto.py` — run the expanded offline pinned SDK suite

The generated ignored `out/hermes-agent` and manifest are local build artifacts owned by the existing preparation script, not new runtime configuration. No lock, dependency pin or upstream checkout mutation outside this lane. Existing upstream commit remains `861d69c7bba8d2ea6a1cd170e989c901c74d32d1`.

## Verification and completion

Prepare from exact pinned upstream with existing script; inspect cumulative patch; run actual offline SDK iteration/conversation/finalization and pre-dispatch tests with fake provider responses, including >90 calls, finite exhaustion, refund, cancellation and veto. Confirm default remains90 and nullable state serializes as JSON null. Ruff/diff checks; commit/push/open one PR, independent exact-head review before PRIME merge. No ordinary runtime is uncapped until the separate consumer explicitly passes this option and proves APP→IPC→Harness→parent behavior.
