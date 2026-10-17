# Agent: inspect the full composed request
Status: ACTIVE — explicit operator top priority after conversation comfort, 2026-10-16. PRIME implements; ARCHITECTURE independently reviews; PRIME merges.
Base: origin/main@ad325a2b61ca7678816ce2c108a7c8bb101a7bf5.
Lane: codex/agent-prompt-inspection, /tmp/prime-agent-prompt-inspection. Parallel-independent of DOGFOOD Ingest; no shared paths.

One capability: in the existing evidence inspector, tabs named Evidence Trail and The Prompt. The Prompt selects a captured model call, lists actual request components in a left column, and displays the complete composed request or selected component. Show full request resets component selection. Historical calls with no captured body are explicitly unavailable, never reconstructed.

ARCHITECTURE advised private immutable blobs plus small APP trace references; no SQL migration. Exact prepared UTF-8 JSON is captured at the final provider authorization gate, bound to actual provider UUID/hash/byte count and World/conversation/turn/APP attempt. Blob write precedes scoped trace append and successful dispatch acknowledgment. Capture errors refuse before provider IO when capture is enabled. Authorized does not mean sent; existing lifecycle remains separate. Never capture credentials/HTTP headers, expose arbitrary paths, include raw bodies in normal history/logs, or use body capture as evidence/publication authority.

Owner-private stable artifact_data_root/out/agent_request_evidence stores blobs under 0700 directories/0600 files, immutable/no overwrite/no symlink traversal. APP trace metadata is the sole read authority; require its exact matching durable provider authorization. GM-authenticated explicit GET validates World/turn/trace/provider scope, body size/digest/strict UTF-8. Missing/corrupt blob is unavailable/integrity failure. No fallback to latest or reconstructed data. No body truncation. Technical 16 MiB storage maximum is explicit and unrelated to authorization call budgets.

Enable capture explicitly in the local developer runtime with DMB_AGENT_PROMPT_CAPTURE=1; uninstrumented/older calls remain honestly unavailable. UI fetches only after The Prompt/call selection, fences stale responses, clears previous payload on identity change, renders escaped text, and never stores body in browser storage. Known request schemas yield JSON-pointer components from actual captured JSON; unknown schemas retain full view. Capture concerns composed provider-envelope bytes at the final gate, not unobserved transport headers/hidden provider internals.

Exclusive expected write set:
- this handoff
- Backlog.md (operator-requested next authoring insight only; no second runtime capability)
- apps/live_control_server/services/agent_prompt_evidence.py (new)
- apps/live_control_server/services/agent_context_trace_collector.py
- apps/live_control_server/services/agent_turn_service.py
- apps/live_control_server/routes/agent.py
- src/application_state/agent_conversation/context_trace.py
- src/application_state/agent_conversation/context_trace_store.py
- apps/live-control-ui/src/api/buddyContextTraceTypes.ts
- apps/live-control-ui/src/api/liveApi.ts (prompt read only)
- apps/live-control-ui/src/planSurface/components/WorldPlanAgentConversation.tsx (primary Evidence trail placement)
- apps/live-control-ui/src/planSurface/components/BuddyContextTraceLoader.tsx (prompt-only lazy view)
- apps/live-control-ui/src/planSurface/components/BuddyContextTrace.tsx
- apps/live-control-ui/src/planSurface/components/BuddyContextTrace.css
- apps/live-control-ui/src/planSurface/components/BuddyPromptInspector.tsx (new)
- apps/live-control-ui/src/planSurface/components/BuddyPromptInspector.test.tsx (new)
- tests/test_agent_prompt_evidence.py (new)
- tests/application_state/test_agent_prompt_capture.py (new)
- tests/test_agent_context_trace_collector.py
- tests/test_agent_build_jev_single_writer.py (capture integration assertions only if needed)

PRIME's previous saved-section/provider-inclusion lane remains paused with dirty work preserved at /tmp/prime-recap-mention-boundaries. The overlapping agent_turn_service write lease transfers to this prompt slice; no worker is running that predecessor. Do not fold the predecessor's unrelated changes into this PR.

Verify exact bytes/authorized provider binding/fresh readback; capture failure zero provider IO; cross-scope/foreign-call/path/symlink/hash/size refusal; uncaptured old calls unavailable; stale UI reads, two-call component reset and full-view reset. Use synthetic payloads and disposable APP databases on existing host54329; no paid model calls, private corpus replay, retained Graph publication or SQL migration. Inspect cumulative diff; commit/push/PR; independent exact-head review; merge and same-port deployment with preserved browser drafts. Existing approved developer capture configuration is runtime-owned, never Overmind-imported.
