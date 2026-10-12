# HANDOFF — AGENT: broker related recap context for World Plan turns

**Status:** BLOCKED — design approved by PRIME on 2026-10-12; no SERVER implementation lease is active. **Owner:** SERVER. **Authority:** merged source-open producer #1090 at `5614fb1c9156a6a42aed94e2f2422f52df412667`, settled at Buddy main `36a44d5e67133ae5a2d5061c6c2ac759d14d467b`; SOURCE #1089 merged at `8fce46de7e33bc352300abdf3ece0369a3ac1e68`; UI predecessor merged at `39af83580e8d9a4a6367560f34f9ab6d021aa6b7`. APP typed-receipt PR #1092 is the contract predecessor. Its corrected candidate head `ade479bb7fb549c61ba415b3c789b2b366e1f7cb` is **not yet independently accepted**. The precise gate is an accepted exact APP type pin where `descriptor_campaign_id` records the actual source descriptor campaign, distinct from the frozen WORLD_CROSS_CAMPAIGN projection's null campaign. PRIME may dispatch against that accepted unmerged pin as an explicit stacked dependency; handoff location or merge state alone does not activate work.

## Primary question

Can one model-visible `read_related_recap_context` request return a bounded, byte-verified recap section through the trusted parent broker while durable APP authorization, validated-read, and provider-inclusion receipts prove exactly which text reached the provider? This context may inform prose. It is never an evidence opener, `source_read_id`, `source_opened`, claim support, or a substitute citation.

## Contract and intended topology

After the APP gate and PRIME dispatch, re-anchor the current Buddy default branch, #1092 base/head, active PRs, file leases, and runtime state. Record the accepted APP pin and actual implementation base here before activating. The intended topology is serial SERVER broker integration after the merged producer, stacked on the accepted APP ref only if it remains unmerged and PRIME names that exact parent. No speculative APP model or persistence edits belong to this slice.

SERVER takes an exact target and evidence-ref set admitted by the turn's frozen initial dispatched Graph input, an earlier validated Graph operation, or a committed selected index. At the same native GM WORLD_CROSS_CAMPAIGN World/revision it requires complete Core `get_evidence` provenance, then a complete nonoverflow context index; exact evidence-ref/artifact/source-revision joins one unambiguous descriptor. Preserve the descriptor's source campaign even though the projection campaign is null. Re-resolve the same pin before each read and call the SOURCE recap-context reader using only server-injected authority and Core context ID. Require exact returned descriptor, source-byte digest, section/range/continuation commitments, and bounded content. Authorization must be durable before IO; validated outcome must be durable before text is returned. Final provider-envelope inspection matches context tool outputs to validated event IDs/digests and appends the APP inclusion event immediately before matching provider authorization. An unresolved append/read outcome fails closed. No passage text, raw path, opaque continuation, or catalog is stored in APP receipts.

## Expected write lease after activation

- `apps/live_control_server/services/agent_turn_service.py` — parent broker, durable fence, exact provider inclusion.
- `apps/live_control_server/services/hermes_graph_interaction_tools.py`, `hermes_graph_agent_host.py`, `hermes_graph_agent.py` — strict model-visible tool, parent IPC, bounded reservation.
- `apps/live_control_server/services/agent_graph_policy.py` only if truthful tool instructions require it.
- Focused `tests/test_agent_turn_service.py`, `tests/test_hermes_graph_agent_host.py`, `tests/test_hermes_graph_agent.py`, and this handoff.

This list is a proposed exclusive lease, not an active one. A newly needed public contract, APP/SOURCE path, provider plumbing, runtime configuration, or extra product capability is a stop/split signal for PRIME. No runtime restart, provider call, private corpus/native Graph/DB write, or UI work is included.

## Acceptance witness

Focused parent-broker and IPC tests must cover one successful unreadable-old-anchor provenance → verified recap read; all three admission origins; same-descriptor continuation; wrong target/ref, source campaign, pair, World/revision/scope, digest, selector, page offset, index completeness, ambiguity, and duplicate output rejection; the APP contract's 8-call, 12,000-character-per-call, and 96,000-character-total bounds; authorization-before-read, validated-read-before-return, inclusion-before-dispatch, and replay/dangling-inclusion behavior. Assert context is absent from all evidence/citation source-read fields and no body/path/token is persisted. Run focused owning-boundary tests, changed-path lint/type gates, inspect the exact cumulative base→head diff, commit/push the assigned PR, and hand the exact head to PRIME for review without merging.
