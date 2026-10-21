# Design — Buddy’s work, explained

**Status:** Later product candidate; this note does not activate implementation.
**Repository anchor:** DungeonMindBuddy `origin/main@60436ac9164cbc7c443822f17ea0c4a5ad17639b` (PR #1540, 2026-10-21).
**Product authority:** [ROADMAP-demo.md](../Roadmaps/ROADMAP-demo.md), “Buddy’s work, explained.”
**Owner boundary:** Buddy owns product composition and status presentation. Existing runtime, trace, provider, and APP authorities retain their current contracts and access boundaries.

## Product intent

Let a curious GM see how Buddy worked through a real turn. The experience should feel like a friendly glimpse behind the table screen: understandable, optional, and a little fun. It explains recorded orchestration, retrieval, provider calls, and validation events. It does not narrate hidden model thoughts or turn a useful product into a mandatory course.

## Reuse the trace we have

There is no user-facing guided tour, onboarding flow, contextual-help layer, or React tour dependency in the live-control UI today. The repo does contain contributor process guides and handoffs, such as the [steward-cycle guide](../Process/STEWARD-CYCLE.md); those are developer documentation, not in-app teaching. The relevant product surface is the existing **Advanced diagnostics** disclosure, not a tutorial. It renders product phase spans, model-call timing and usage, and graph-tool activity. The composer shows a generic “Working…” while its local send/compose flags are set. These are useful foundations, but neither is currently a teaching experience or a server-observed live phase label.

The relevant code is `apps/live-control-ui/src/agentInteraction/trace/AgentTraceInspector.tsx` and `apps/live-control-ui/src/api/types.ts` (`AgentInteractionTrace`, `AgentInteractionTraceSpan`, `AgentInteractionModelCallTrace`, and `HermesGraphToolTraceEvent`). The generic composer label is in `apps/live-control-ui/src/planSurface/components/WorldPlanAgentConversation.tsx`. `trace_id`, `span_id`, and `call_id` identify the containing trace, phase, and model call. The separate Buddy context trace now shows exact provider-attempt IDs and provider durations.

PR #1527 correlates reported provider usage to the authorized attempt using the SDK request ID; it explicitly leaves unidentified telemetry uncorrelated instead of guessing from order, timing, model, or token estimates. PR #1528 preserves completion evidence before the durable turn completes. PR #1529 adds exact GenerationEngine prepared-attempt correlation. These are useful attribution and ordering foundations, not a live progress stream or a tutorial system. Reuse their identities and the existing trace surfaces; do not create a parallel trace store.

There are still gaps for exact step links: graph-tool trace events and legacy `steps` do not have their own stable event IDs, and the current busy label is driven by UI busy flags rather than a server-observed phase. Where an existing span or call ID is present, link to it. Add a trace-scoped event identity only for event types that lack one; never infer identity from list position or timing. Existing documentation and trace diagnostics remain distinct from user-facing teaching.

## Sequence

### 1. Make the known status friendlier

Improve the copy from the existing `sending`, `composing`, and busy states. A small line such as “Buddy’s on it — your reply is in progress” can be more human and reassuring while saying only what the UI knows. Keep composing/editing states distinct where the current state already distinguishes them. Avoid claiming that Buddy is searching, reading, or validating until an observable event says so.

This is independently useful and can ship before the teaching layer. It needs no trace-schema change, new transport, provider call, or timing prediction. It must still use the current UI owner's path lease and remain within PRIME's active sequencing.

### 2. Give actual progress stable identities and click-through

Extend the existing turn trace with bounded start, completion, and failure observations for phases the runtime can actually observe. Carry the exact `trace_id` and turn identity, plus a stable event ID. Reuse `span_id`, `call_id`, and provider-attempt IDs for the corresponding records. Add an event ID only for records such as graph-tool events that lack one today.

Expose current progress only from those recorded observations. Link a status update or completed-turn summary to the exact event row, opening the existing inspector at that row. Keep “unknown/unavailable” as a truthful fallback when no event was emitted. The current request/response UI does not supply exact live-phase text; this step needs real server observations and an owned transport for delivering them.

Reuse the existing trace, span, model-call, and graph-tool durations. Add bounded start/end or monotonic measurements only for observable steps that lack them, alongside this instrumentation rather than waiting until estimate work begins.

### 3. Add optional authored explanations

Add a lightweight “Explain this run” or per-event explanation inside the existing trace disclosure. Explanations are authored copy selected by actual event kind/name/status and point to that event's captured detail. Keep this separate from live status and optional by default. A non-modal disclosure is enough; do not require a guided tour or add a React tour dependency.

Explain observable work such as “this step checked the selected World revision” only when that check appears in the trace. Do not claim access to private reasoning, invent a rationale from the final answer, or expose raw prompts, user messages, source excerpts, tool arguments, or raw tool results as tutorial content.

### 4. Estimate phase duration from comparable runs

Use measured per-step/phase durations to show a typical value and an uncertainty range, for example a median plus a recent p10–p90 range and the number of comparable observations. Compare similar step/runtime/provider/model cohorts only as needed to avoid misleading mixtures. State that the range describes prior comparable steps, not a guarantee. Suppress the estimate or say “not enough comparable runs” when the cohort is sparse or the measurement is missing.

Keep phase estimates distinct from whole-agent-loop completion estimates. The current elapsed trace value does not establish that every queue, transport, and user-visible delay is measured. Do not show a total ETA until the measured boundaries support it. Show the actual phase duration after completion.

## Boundaries and costs

- Explanations and estimates are local presentation over already captured, authorized trace data. They must not trigger inference or add tutorial text to the agent prompt; no additional inference dependency or token cost is needed.
- New live progress observations add bounded transport and retention work, but should come from existing execution events rather than a second trace system. Keep trace caps, redaction, and turn/world access unchanged.
- Reuse exact provider correlation from #1527–1529. Missing correlation remains explicitly unknown; never match by call order, approximate duration, or model label.
- Do not add a fake countdown, animation that implies measured progress, mandatory onboarding, raw chain-of-thought narration, or a completion estimate for an unmeasured loop.
- This candidate does not supersede the roadmap's focused-card/Play direction or PRIME-owned Rules/Combat work. Resolve product owner, write lease, and sequencing at activation; this design note grants none.

## Evidence anchors

- [Advanced Agent Trace Inspector handoff](../Plans/HANDOFF-AGENT-INTERACTION-trace-inspector-v1.md)
- [Per-call provider usage correlation, PR #1527](../Plans/HANDOFF-AGENT-provider-usage-correlation.md)
- [Native completion trace ordering, PR #1528](../Plans/HANDOFF-AGENT-native-completion-trace-order.md)
- [Build provider usage correlation, PR #1529](../Plans/HANDOFF-AGENT-build-provider-usage-correlation.md)
- [DEMO steward mandate](../Plans/STEWARDS-HANDOFF-demo.md)
