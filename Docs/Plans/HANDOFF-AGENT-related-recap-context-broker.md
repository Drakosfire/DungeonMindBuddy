# HANDOFF — AGENT: broker related recap context for World Plan turns

**Status:** REVIEW — SERVER implementation committed at `34c9c3db` on 2026-10-12; PRIME owns independent review and merge. **Owner:** SERVER. **Base:** fetched Buddy `main@8b5e73eccdbd168ab2bc21acb01a147835eafd0c`, branch `codex/agent-related-recap-broker` in isolated `/tmp/buddy-agent-source-targets` checkout. **Authority:** merged source-open producer #1090 at `5614fb1c9156a6a42aed94e2f2422f52df412667`; SOURCE #1089 at `8fce46de7e33bc352300abdf3ece0369a3ac1e68`; UI predecessor at `39af83580e8d9a4a6367560f34f9ab6d021aa6b7`; APP typed-receipt #1092 independently accepted at `ade479bb7fb549c61ba415b3c789b2b366e1f7cb` and merged at `8b5e73eccdbd168ab2bc21acb01a147835eafd0c`. The APP receipt records the actual source descriptor campaign separately from the null WORLD_CROSS_CAMPAIGN projection campaign. Open Buddy PR inventory at activation has no overlap with the expected SERVER paths; #1014 is UI/rollout, #1093 is a DEMO handoff, and legacy Rules PRs do not touch this lease. No shared runtime, provider, or private data state is used for this implementation.

## Primary question

Can one model-visible `read_related_recap_context` request return a bounded, byte-verified recap section through the trusted parent broker while durable APP authorization, validated-read, and provider-inclusion receipts prove exactly which text reached the provider? This context may inform prose. It is never an evidence opener, `source_read_id`, `source_opened`, claim support, or a substitute citation.

## Contract and intended topology

Topology is serial SERVER broker integration on the merged APP predecessor. No APP model or persistence edits belong to this slice.

SERVER takes an exact target and evidence-ref set admitted by the turn's frozen initial dispatched Graph input, an earlier validated Graph operation, or a committed selected index. At the same native GM WORLD_CROSS_CAMPAIGN World/revision it requires complete Core `get_evidence` provenance, then a complete nonoverflow context index; exact evidence-ref/artifact/source-revision joins one unambiguous descriptor. Preserve the descriptor's source campaign even though the projection campaign is null. Re-resolve the same pin before each read and call the SOURCE recap-context reader using only server-injected authority and Core context ID. Require exact returned descriptor, source-byte digest, section/range/continuation commitments, and bounded content. Authorization must be durable before IO; validated outcome must be durable before text is returned. Final provider-envelope inspection matches context tool outputs to validated event IDs/digests and appends the APP inclusion event immediately before matching provider authorization. An unresolved append/read outcome fails closed. No passage text, raw path, opaque continuation, or catalog is stored in APP receipts.

## Exclusive write lease

- `apps/live_control_server/services/agent_turn_service.py` — parent broker, durable fence, exact provider inclusion.
- `apps/live_control_server/services/hermes_graph_interaction_tools.py`, `hermes_graph_agent_host.py`, `hermes_graph_agent.py` — strict model-visible tool, parent IPC, bounded reservation.
- `src/graph_memory/hermes_graph_plugin.py` — the existing parent-broker tool allowlist only; PRIME approved this minimal path addition after activation. The existing `tests/test_hermes_graph_agent.py` owns its focused registration/IPC witness.
- `apps/live_control_server/services/hermes_agent_runtime.py` — server-supplied `context_read_enabled` flag and read-only tool policy rule only; PRIME approved this call-path addition after activation. Default false preserves V1/non-context turns. `tests/test_hermes_agent_runtime.py` owns focused policy serialization coverage.
- `apps/live_control_server/services/agent_graph_policy.py` only if truthful tool instructions require it.
- Focused `tests/test_agent_turn_service.py`, `tests/test_hermes_graph_agent_host.py`, `tests/test_hermes_graph_agent.py`, `tests/test_hermes_agent_runtime.py`, and this handoff.

A newly needed public contract, APP/SOURCE path, provider plumbing, runtime configuration, or extra product capability is a stop/split signal for PRIME. No runtime restart, provider call, private corpus/native Graph/DB write, or UI work is included.

## Acceptance witness

Focused parent-broker and IPC tests must cover one successful unreadable-old-anchor provenance → verified recap read; all three admission origins; same-descriptor continuation; wrong target/ref, source campaign, pair, World/revision/scope, digest, selector, page offset, index completeness, ambiguity, and duplicate output rejection; the APP contract's 8-call, 12,000-character-per-call, and 96,000-character-total bounds; authorization-before-read, validated-read-before-return, inclusion-before-dispatch, and replay/dangling-inclusion behavior. Assert context is absent from all evidence/citation source-read fields and no body/path/token is persisted. Run focused owning-boundary tests, changed-path lint/type gates, inspect the exact cumulative base→head diff, commit/push the assigned PR, and hand the exact head to PRIME for review without merging.

## Implementation evidence at `34c9c3db`

The parent now offers opaque context IDs only from validated Graph traversal results after same-pin Core provenance and complete context-index checks. The model request must carry the offered ID. The parent then re-resolves the exact target/ref/descriptor join, appends APP authorization before SOURCE IO, validates the returned section and page before release, and appends an APP provider-inclusion receipt before provider authorization when the exact tool output is included. New Plan Graph turns freeze V2 even with no readable source scope; persisted V1 retries retain V1. The new tool remains outside ordinary non-parent model-visible policy.

Focused gate: 10 passed across parent traversal/read/provider inclusion, V2 policy freeze, runtime policy serialization, correlated IPC, plugin registration, and operation reservations. Changed Python paths pass Ruff and `git diff --check` passes. The broad Graph-agent file reaches an unrelated sandbox failure creating `/home/drakosfire/.hermes/logs` on the read-only home filesystem; the broad service file stalls in the pre-existing history HTTP test. No provider or private corpus run was used.

Focused negatives prove unadmitted target/ref/context ID, stale revision, incomplete index, and duplicate provider output fail closed. Additional handoff matrix cases (selected-index origin, continuation, wrong SOURCE page metadata, and explicit quota exhaustion) remain for PRIME review or a follow-up test patch; the implementation enforces these checks but this evidence does not claim they were all executed. No acceptance token is asserted by SERVER.
