# Agent Harness — bounded recoverable Graph tool pages

Status: ACTIVE. PRIME implements solo; ARCHITECTURE independently reviews.
Base: `a76f462b83e6229d67e85869d57fb00f38c82e23`.
Branch: `codex/agent-graph-tool-pages`; topology: serial.

## Outcome and boundary

Preserve structured Graph tool responses through the pinned Hermes 0.18.2 budget
path. Ordinary Build council benchmark failed with hermes_worker_timeout after
121.291 seconds; live logs show result/aggregate clipping into invalid JSON.
Saved deterministic replay reproduces both thresholds without provider requests.

Harness plugin return boundary covers direct Build reads and parent-brokered
Plan reads. Cache only immutable already-authorized result presentation, scoped
to worker instance, active retrieval session, frozen World/revision, tool,
original request and page position. Parent Graph authority, complete ledger and
source receipts remain unchanged. Continuations perform no Graph/broker read,
claim append or source opening. Expired/evicted/foreign tokens fail explicitly;
never silently rerun. Bounded lifetime/memory and complete serialized pages.
Use operation-local claim delta, not the cumulative ledger, in presentation.
Preserve original record qualification; oversized strings use explicit Unicode
fragments with original offsets/length/digest, never unmarked clipping.
Core truncation is distinct from transport pagination and its next token.

Graph-enabled agents request parallel_tool_calls=False through the existing
request_overrides constructor parameter (both provider transports). Safety also
uses a Buddy-owned adapter to the private pinned _execute_tool_calls dispatcher:
copy the assistant message per call, preserve original IDs/order and shared
messages/task/accounting, invoke the original dispatcher on singleton batches.
Original cancellation/guardrails/callbacks remain in force for every call.
Unsupported signatures fail explicitly; no unsafe fallback. No vendor edit,
budget increase, filesystem tools or total-call authorization cap.

## Exact write lease

- `Docs/Plans/HANDOFF-AGENT-graph-tool-pages.md`
- `apps/live_control_server/services/graph_tool_transport.py`
- `apps/live_control_server/services/hermes_graph_dispatch_adapter.py`
- `apps/live_control_server/services/hermes_graph_interaction_tools.py`
- `apps/live_control_server/services/hermes_graph_agent.py`
- `src/graph_memory/hermes_graph_plugin.py`
- `tests/test_graph_tool_transport.py`
- `tests/test_hermes_graph_dispatch_adapter.py`

Current open PRs were inspected; none owns these paths. Non-serving implementation
and private evidence; DOGFOOD5202/API8000 untouched. Plan parent object reads lack
the reviewed-observation facet supplied by Build's direct path: separate gap,
not authority to expand this slice into observation adoption or trace storage.

## Required evidence

Test broker/direct plugin boundary, token scope/request binding, cold/expired
cache, source receipt preservation, Unicode fragments and exact reconstruction,
unchanged parent claims, and truthful omitted/remaining counts. Invoke actual
Hermes per-result and per-batch enforcement with >200KB cumulative serial
transcript, oversized source and multi-call/stop cases; all responses paired,
parseable, bounded and recoverable. Verify both transports emit parallel false.
Review full cumulative diff and exact head; finish to PR. After accepted merge,
roll out stable5876/API8002 and repeat ordinary conversation only on changed
runtime. No end-to-end acceptance from helper tests alone.

## Implementation evidence

Pages are at most8,000 UTF-8 bytes, below even the pinned Harness's8,000-char
minimum single-result threshold. The worker-local cache holds at most8MB of
serialized pages for300seconds; expiry/eviction/foreign scope fail explicitly.
Thirty-two serial results (stronger cumulative-volume proof than the initial
24-result plan) exceed200KB while actual vendor persistence/enforcement and
next-request call/response pairing remain valid. Real pinned dispatch tests also
prove cancellation and capability denial prevent further Graph IO.

Retained frozen-revision plugin probe: search12pages (maximum7,922bytes),
object2pages (maximum7,227bytes), opened source1page/1,574bytes. Continuing pages
changes neither operation count nor authoritative claims/source-read receipts.
Descriptions/qualification lead the search pages; full remaining records stay
recoverable. No provider call or retained World publication in implementation.

Focused regression passes69tests. The wider pre-existing Harness suite has six
failures (profile permissions, model-visible surface fixtures and a parent-source
policy expectation); the exact same six reproduce against unchanged main with
the same installed environment. They are not counted as passing. Ordinary live
conversation, latency and operator acceptance remain pending after review.
