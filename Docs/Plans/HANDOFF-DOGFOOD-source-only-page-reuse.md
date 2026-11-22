# DOGFOOD: reuse cited discussion before Graph activation

Status ACTIVE. The user assigned DOGFOOD the conversation-to-page lane, authorized
replays/submissions and independently reviewed merges for concrete fresh-context
page creation, and directed testing with ONBOARDING's new-World flow.

One serial PR on `codex/dogfood-onboarding-check`, base
`043a5481b3f2d0718e8044a49b84089f44ef9196`, current isolated checkout
`/home/drakosfire/Projects/.codex/79e2/DungeonMindBuddy`. No unmerged behavioral
parent. ONBOARDING retains its live Sizzek World, import and deployment lane;
this work uses fresh disposable APP/Core templates and invented test lore only.
No production data, backup copy, flags, publication or deployment is authorized.

Exclusive expected writes: `native_corpus.py`'s existing
`conversation_route_can_admit` predicate; owning tests in
`tests/test_native_body_writer_selection.py`; forward-only reader fence
`20261122_0187` after canonical `0186`; this handoff. Open #3307's source campaign
metadata/bounded-section changes do not touch this predicate; preserve them and
all Plan/retrieval semantics. Open #4428 has no overlapping expected files.
Do not edit shared native execution, source acquisition, prompts, DTOs or CI
classification. The external test runner/evidence use the verified Projects
filesystem and uniquely owned databases, with no service ports or live state.

## Observed failure and bounded contract

In a new World, ordinary source admission and a cited source discussion succeed.
The real opening decision correctly chooses conversation-only lore review and
anchored context. The host nevertheless skips prior-citation admission because
the Graph query is unavailable rather than pending; the writer loses the
already retrieved facts/citation and returns no page review.

Keep the pending-query protocol unchanged. Also allow route eligibility for the
existing `native_graph_binding_unavailable` receipt only when a real native
source authority and a fresh Build intent name the same World. This reason
covers missing, inactive and provisioning bindings, not only new Worlds.
Reject reviewed work, explicit authored references, explicit revision pins,
Graph-head-unavailable, absent/foreign source authority, non-Build work and
Graph settlement. The unavailable branch must itself reject the same new
body/retrieval/related-page acquisition inventory as the pending protocol;
the pending protocol's later acquisition guard does not run for unavailable
queries. Eligibility alone grants no citation support: existing frozen history,
completion digest, ordinal, exact extent, current conversation and fresh source
authorization owners remain authoritative.

This permits a newly valid stored receipt/event combination. Add a no-op
forward-only schema fence so older readers cannot silently operate on those
rows. Existing release/recovery artifacts do not qualify this new fence;
deployment and compatible recovery require their own exact-source evidence.

## Validation

Exercise pure predicate refusal cases and forged same-turn acquisition after
prior admission, then the ordinary new-World/source-admission/cited-discussion/
page-review/save/reopen path with real providers and no new source acquisition
for synthesis. Preserve proposed lore and unresolved questions, exact citation
digests, one saved page and identical confirmation replay. Keep the empty-World
supplied-discussion case passing. Verify the reader fence and owning backend
contracts from the exact commit, compare inherited failures honestly, review the
cumulative diff independently, commit/push and open the assigned PR. Keep private
operational evidence outside GitHub; the PR summary describes feature behavior
and validation without host, backup or private source details.
