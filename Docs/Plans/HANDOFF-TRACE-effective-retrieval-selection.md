# TRACE: effective retrieval selection

ACTIVE serial trace slice. The user authorized the intent-first goal, including
trace clarity, independent review, merge and deployment. Base: Buddy main
b39fb7440b60231adc0499ddc9ac6e7d97c66d7b. Branch:
`codex/trace-effective-selection`. Checkout:
`Projects/.codex/intent-trace-label/DungeonMindBuddy`.

Outcome: show the actual durable host selection beside the matching raw Jev
response, scoped to the trace attempt. An absent recorded selection is unknown;
never infer it from model candidate votes. This is read-only diagnostics and
cannot grant source or write authority. No new runtime retrieval path is added.

Write set: `src/application_state/agent_conversation/{neighborhood_replay,context_trace,context_trace_store}.py`, `tests/test_agent_context_trace_projection.py`,
`apps/live-control-ui/src/api/buddyContextTraceTypes.ts`,
`apps/live-control-ui/src/planSurface/components/{BuddyContextTrace.tsx,BuddyContextTrace.test.tsx}`,
and this handoff. The existing Build routing PR #4642 retains its exclusive
source-free write lease; benchmark PR #4584 retains its benchmark files. Neither
is an unmerged behavioral parent. This trace slice follows merged #4669.

Verify original execution event provenance and per-attempt boundaries at the
trace reader, including omitted historical events and mismatched correlation;
verify UI display and unavailable state. Run affected backend contracts and the
repository local frontend verifier on the exact head, independently review the
cumulative diff, and retain any inherited diagnostic failures honestly. It does
not establish intent-first routing or authorize a production data change.
