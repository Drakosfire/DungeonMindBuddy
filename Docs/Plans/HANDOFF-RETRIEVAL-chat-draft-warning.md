# RETRIEVAL: Do not add a retrieval warning to anchored chat proposals

Status: ACTIVE under the user's over-retrieval objective and deployment
approval. Serial serving slice, based on the current observed production
revision `5352ab4cabcd9f7d9b979a07e35b4cbe08da0b75`; PR base is
`codex/draft-warning-serving-base` at that revision, branch
`codex/draft-warning-serving` in the isolated `retrieval-draft-warning` checkout.
The earlier discussion-only warning fix landed in #4839/#4841; its prior
lease has settled. The pending Build codec exists on this serving lineage and
is absent from current main, so this slice is a serving overlay, not a claim
that main has the same runtime owner. Recheck serving parent before publication.

Observed user behavior: an anchored, proposal-only conversation draft completed
with no retrieval entries. The writer returned no limitations, but the host
added a partial-retrieval warning. Treat the already-admitted anchored chat-draft
work like anchored discussion only for host-derived partial retrieval. Preserve
source-required and uncertain paths, mixed factual claims, explicit limitations,
all citation checks, action routing, stored historical replies and other surfaces.
Do not suppress writer-supplied caveats or infer source sufficiency from text.

Write lease: this handoff, `src/application_state/agent_conversation/native_completion.py`
and focused tests in `tests/test_build_source_free_routing.py`. Existing #4823
changes neither file; its shared catalog and contract-test paths remain outside
this slice. Clarification #4652 and manual-summon #4381 are merged; their old
ACTIVE handoffs do not allocate live successor writes. No schema, provider,
action routing, prompts, database, or shared benchmark writes.

Verify at the actual writer/host completion boundary with anchored chat draft,
explicit writer limitation, source-required or uncertain work, mixed/forged
citation, historical replay and cross-release in-flight behavior. Use only
focused local cases; no provider or database required. Independent exact-head
review and all merge gates apply. Before deployment, inspect actual current
serving identity and compatibility, evaluate in-flight exact-output risk, use
Actions with a reviewed serving-parent candidate and pinned rollback, and
smoke the signed-in creative draft. The held-out unsupported-action error is a
separate serial successor, not fixed by this slice.
