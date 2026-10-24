# Preserve complete recent authoring exchanges

ACTIVE serial PRIME implementation; branch codex/build-complete-followup-history,
base 573d6a4dec7f91fa8d1e2f0c7734c8cf4335f0aa; existing buddy-context-loop checkout.
One capability/PR; open hosted/Combat/Ingest lanes are disjoint. PRIME owns API8000
and UI5202; no live model probes while operator dogfood continues.

The Build interaction silently omits a completed exchange when its combined user
and assistant text exceeds the remaining 12000-character history allowance. This
can remove the very draft referenced by a follow-up. Keep complete recent completed
exchanges from the existing bounded six-turn read, in chronology, with their exact
IDs/digests. Remove the separate character cutoff and describe the current input
policy truthfully. Existing configured provider admission remains the capacity gate;
never truncate or silently replace an oversized exchange. Historical dialogue remains
reference, not source authority. Do not broaden history queries or add another read.

Exclusive writes: this handoff; HANDOFF-BUILD-admission-diagnostics.md and
Docs/Roadmaps/ROADMAP-demo.md for predecessor settlement;
apps/live_control_server/services/build_jev_driver.py;
tests/test_agent_build_jev_ordinary_harness.py.
No schema/UI/corpus/dependency or retained user-state mutation.

Prove actual mocked SDK→APP discussion follow-up and page-proposal follow-up retain
an exchange beyond the removed cutoff, exact digest/chronology, shared proposal
writer input, immutable proposal reopening and source preservation. Verify existing
history scoping, unfinished-turn exclusion, tamper and genuine admission gates.
Independent exact cumulative Bugbot review, PRIME merge and protected API delivery.
Live authoring/model/latency and complete goal acceptance remain open.
