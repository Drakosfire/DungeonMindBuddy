# DOGFOOD: reserve page output for the requested draft

ACTIVE, Alan authorized4459 latency/reliability fixes through deployment. DOGFOOD
owns this bounded Buddy runtime slice. Stacked implementation/serial delivery,
parent4499 exact71709c838551d51483f531c6c0b6d5fd4a8cf833; branch
codex/dogfood-page-writer-effort, same isolated checkout. Merge order4484(merged),
4496,4499,this PR. No runtime write lease. Other source leases are frozen for
exact-SHA verification; no concurrent implementation writer in these paths.

Outcome: conversation-page synthesis uses the existing configured writer with
reasoning effort none rather than medium. Actual Maelthor diagnostics show medium
spends1139–1886 output tokens on reasoning; none spends output on the draft and
reduced writer time to6.2s. It preserves full frozen input, selected source handles,
output reserve/capacity checks and typed response validation. No model/provider,
fallback, truncation, hidden summarization or acquisition change. Single-statblock
variant remains medium and ordinary discussion remains low.

Exclusive writes: this handoff; plan_jev_writer.py only the effort selection;
ordinary HTTP fake only effort expectation; tests/test_build_retained_conversation.py
only physical serialized-request assertion. No context schema/migration, cache,
frontend, Rules or provider configuration edits. Immutable source caching remains
a separate independently useful successor.

Validation: existing default/variant output-limit safeguards plus actual retained
page HTTP request carries reasoning none while discussion/variant defaults remain;
real unpatched configured-provider Maelthor replays retain full context and exact
citations, with complete latency/usage/failure counts. Run exact-source owning
contracts/frontend verifier and independent review. Latency experiments are not
qualification; final serving integration and actual-app proof remain required.

Working-tree checks:41 passed,35 deselected in178.14s, including the physical
retained page request (none), discussion(low), existing exact prompt/default(low),
and incomplete-output/debug/no-retry guards. An initial broader writer run failed
its existing mixed Rules fixture schema; exact717 parent reproduces the same
GenerationEngine structured-output error (8.54s). Preserve both failures; do not
label the full writer module green or change unrelated Rules fixtures.
