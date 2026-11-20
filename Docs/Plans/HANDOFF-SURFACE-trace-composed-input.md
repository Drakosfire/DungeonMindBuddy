# SURFACE — composed input and readable execution trace

ACTIVE PRIME slice, codex/trace-composed-input from f1f9f2774 in the existing
Buddy context-loop checkout. One serial UI PR, explicitly requested dogfood trace
improvements. Broad goal and API1709 remain paused; no source/provider writes.

Exclusive writes: BuddyContextTrace.tsx/.css and focused tests;
BuddyPromptInspector.tsx and tests; PreparedRequestInspector.tsx and tests;
BuddyContextTraceLoader.tsx and tests; traceCostEstimate.ts and tests; this handoff.
No API/schema/model behavior changes. Preserve existing turn-owned prompt reader,
identity validation, cancellation and demand loading. Exact captured requests may
be compared only to the previous captured call in the same attempt; never rebuild
missing prompts from context snapshots. Color added/changed/removed request
components with text labels, retain exact JSON and capture identities. Context
snapshots remain distinct recorded material inventories with changes called out.
Estimate known Jev call costs from provider-reported input usage and the verified
2026-10-24 public gateway USD rate (0.042/M input, output free); scope by provider
and exact version, unknown models/rates/usage remain unavailable, not zero.
Preserve inline kept-suggestion decisions; no new durable decision schema.

Verify lazy exact prompt reads, previous-call diff, missing/stale identity behavior,
literal escaping, usage/cost unknown handling and response reconciliation. Build,
exact cumulative Bugbot review, PRIME merge and protected UI-only delivery5202;
rendered existing trace proof without model calls or editing retained documents.
