# AGENT — Unified reply Details

Status: ACTIVE. The user authorized implementation, independent review, merge,
and deployment to 5202 in the unified reply Details goal. This serial first
slice starts from Buddy main at `191fc9d2165e4ef39234a50982e650a38166f4ad`.
The implementation branch is `codex/buddy-unified-reply-details` in the
`graph-timeline-layouts/DungeonMindBuddy` checkout.

The slice owns the reply Details composition in WorldPlanAgentConversation,
BuddyContextTrace, BuddyContextTraceLoader, and their existing tests. One
opt-in trace lifecycle serves replay and diagnostics. Keep exact inline
citation routing and source readers. Capture and prompt reads retain their
existing World, conversation, turn and attempt checks. The prompt reads on
disclosure. Previous attempts remain independently inspectable.

Validate focused trace and World conversation tests, the repository frontend
verifier, the full frontend diagnostic against its baseline, and independent
review of the exact cumulative diff. On 5202, check that one reply Details
opening loads one trace and that an inline citation opens its exact excerpt.

The successor owns directed hop and pruning provenance. Inspect the producer
before assigning that work. A further Buddy slice consumes the saved decisions,
shows them in replay, and proves fresh and historical behavior on 5202.
