# HANDOFF — SERVER: Plan World Graph context route v1

**Status:** ACTIVE — bounded implementation authorized by PRIME on 2026-10-05.
**Owner:** DungeonMindBuddy SERVER owns request admission, managed-to-native binding integration, exact Graph retrieval, provider-envelope accounting, answer validation, and API/history projection. APP-STATE owns the durable receipt/completion types and atomic persistence. DEMO owns client presentation. PRIME owns path arbitration and review.
**Pinned base:** Buddy `main@93c07c243acd9abc9acc044f9a4e59390710871d` (APP-STATE #923 merge).
**Branch:** `codex/plan-world-graph-context-route`.
**Topology:** one serial SERVER route PR after APP-STATE receipt implementation. DEMO follows under a separate lease. #924 Hermes request-budget contract is a separate predecessor for provider-boundary integration; its current reviewed head is on HOLD and must remain unchanged until its reviewer supplies a complete disposition.

## Mission

Add explicit `auto_plan_world` context to the existing durable World Plan conversation. Resolve a fixed, bounded World Graph packet against the exact committed Plan basis, persist the APP-STATE receipt before any provider SDK dispatch, and return/history-project typed answer attribution and citations. No-policy Plan Ask remains byte-compatible. This is not a new endpoint, generic Graph query, Plan mutation, or UI change.

## Accepted persistence authority

Consume the receipt/completion contract merged on base `93c07c243acd9abc9acc044f9a4e59390710871d`, specifically `Docs/Plans/DESIGN-APP-STATE-plan-world-graph-context-receipt-v1.md`, `src/application_state/agent_conversation/types.py`, repository/service, and migration `20261004_0016_agent_turn_graph_context_receipt.py`. #923 released APP-STATE's implementation lease. Do not change or duplicate its types/migration.

New accepted turns require exactly one submitted intent: existing v1 without policy, or v2 with explicit `auto_plan_world`. The policy remains distinct from generic `graph_request=none`; it is valid only for a saved Plan with exact committed revision/digest and optional independent typed card focus on that same basis. Freeze the immutable receipt atomically with turn acceptance. Completion stores the unchanged receipt and validated typed completion atomically. Completed replay returns stored answer/receipt/completion before current Plan, binding, Graph, or provider reads. Retry verifies the original basis and never repins.

## Exact request, dispatch, and persistence boundary

The public message cap remains 8,000 characters. Never truncate the committed Plan or Graph packet to satisfy a model budget. A separate server-owned full-input guard may reject oversized composed context, but must not change the public question cap or call character counting token accounting.

The only acceptable `assembled_input_sha256` is derived from the **actual final canonical provider request after Hermes middleware and Responses preflight shaping**, using the accepted Hermes request-budget contract. That exact request view must also supply provider/model/API mode, estimator identity, payload digest/byte count, and output reserve. The route must successfully freeze the corresponding APP-STATE receipt before the SDK call can proceed. A hash of `_plan_message`, `AgentRuntimeInvocation`, retrieval packet alone, or any other pre-Hermes/pre-middleware representation is not acceptance evidence. Do not add a second estimator, accounting path, SDK wrapper, or dispatch path.

PR #924 is currently under independent review at `0fe99fcf0068775d5e0439a5bcd9b894e456cea8` and is not accepted. Its reviewer has identified gaps in strict request-shape closure, actual Buddy provider identity mapping, and terminal failure/observer normalization. Route work may proceed on disjoint intent, binding, receipt, completion, history/replay logic with deterministic synthetic provider-boundary fakes. It must not claim integrated budget/dispatch acceptance or ship an alternative boundary. When #924's accepted contract changes, reconcile only the contract at this boundary; preserve its reviewed head until the review is complete.

## Path lease

Exclusive write paths for this slice:

- `Docs/Plans/HANDOFF-SERVER-plan-world-graph-context-route-v1.md`
- `apps/live_control_server/models/agent_turn.py`
- `apps/live_control_server/routes/agent.py`
- `apps/live_control_server/services/agent_turn_service.py`
- `tests/test_agent_turn_route.py`
- `tests/test_agent_turn_service.py`

No other path is authorized. In particular, do not change the Hermes runtime/IPC/contract, APP-STATE, DEMO, graph-memory, migrations, or unrelated roadmap paths. If actual final-envelope observation and synchronous receipt freezing cannot be connected through the accepted #924 contract within this lease, stop and return the smallest required path/contract expansion to PRIME before editing outside this list.

PRIME explicitly withdrew/froze draft PR #917's production reservation for the three core backend paths above. Preserve its branch; its prototype settlement is not a predecessor. Reconcile it later without editing it. PR #922 is docs-only and not backend acceptance evidence. PR #914 remains UI-only. #924 remains a separate provider-boundary prerequisite.

## Binding/projection inspection

Before implementation, inspect the current `managed_world_graph_projection.py` and its tests. Its current request accepts managed World plus optional exact revision pin, resolves only an active binding, performs a native projection, verifies the binding version/native ID/source root did not change during the read, and returns managed/native IDs plus binding version and typed projection. The agent-turn Graph resolver currently bypasses this binding seam and sends the managed owner ID as the Graph world ID. The route service therefore must resolve/revalidate managed→native authority before using its existing Graph context/retrieval path. Do not add the conditional projector/test paths unless the existing function cannot preserve the exact revision, evidence identities, and fixed World scope needed by the route; if necessary, stop, amend this handoff with the concrete gap and obtain PRIME approval before editing those paths.

## Required behavior and witnesses

1. **Legacy and strict admission:** preserve no-policy request/response/history schemas and golden request, idempotency, and v1 submitted-intent fingerprints byte-for-byte. Policy contradictions, non-Plan/unsaved work, generic Graph selection, missing exact Plan basis, and unsupported inputs fail before turn claim, Graph read, or provider dispatch.
2. **Managed/native binding:** test a managed World ID distinct from native Graph ID. Resolve active binding server-side; fix scope to World/null campaign; preserve managed identity in product provenance. Fail closed for absent/inactive/unverified binding, version/identity/source-root drift, exact revision unavailable, and invalid/foreign/duplicate evidence IDs. The client cannot select native identity or binding version.
3. **Receipt and packet:** distinguish retrieved candidate packet digest/IDs from included dispatched packet digest/IDs. Insufficient evidence records omission, sends no Graph claim payload, and keeps full committed Plan/history/question. Sufficient-but-unused is distinct from insufficient. The assembled-input digest is the actual final Hermes-boundary digest under the rule above, not a preassembled prompt hash.
4. **Budget and dispatch ordering:** final post-middleware envelope is checked by accepted #924 request-budget logic. Over-budget or unobservable final envelope fails before receipt freeze/SDK dispatch and never downgrades automatically. On success, freeze the exact receipt before the SDK call. Provider call count remains zero on any predispatch error. Until #924 is accepted and integrated, only deterministic fake-boundary tests may exercise this ordering; label those tests synthetic and keep integrated acceptance outstanding.
5. **Completion/citations:** validate typed `graph_claim`, `plan_claim`, `proposal`, and `connective` segments; derive answer basis/status; ensure citation map exactly matches claims and only references dispatched IDs/evidence at the frozen revision and receipt digest, with `source_opened=false`. Exercise all four APP-STATE statuses: `plan_only_insufficient_evidence`, `plan_only_graph_unused`, `graph_grounded`, `graph_grounded_partial`.
6. **Lifecycle:** receipt freeze precedes dispatch; completion commits answer plus unchanged receipt atomically; same-key changed policy/Plan/card intent conflicts. Completed replay has zero current Plan/binding/Graph/provider reads and returns the original receipt/completion with response-only `delivery_replay`. Pending retry reconstructs the original binding/revision/packet and fails without repinning. History projects receipts with nullable completion for pending/interrupted/failed turns while no-policy history remains v1.
7. **Public API errors:** preserve existing no-policy error bodies. For the policy, map the frozen APP-STATE predispatch failure codes to exact statuses/body, with `provider_dispatched=false`, `automatic_downgrade=false`, and no receipt only for failures before freeze. Do not mislabel post-dispatch failures as predispatch failures.

## Verification and stop conditions

Use deterministic fake bindings, Graph packets, APP-STATE service, Hermes provider-boundary views, and provider runtimes. No live provider, Graph, operator database/process, external service, or runtime action. Run focused route/service suites, changed-path Ruff, and current relevant repository gates; preserve full errors and separate clean-base failures. Inspect exact cumulative base→head diff and allowlist before PR publication.

Stop and report to PRIME if:

- post-middleware final request observation and receipt freeze cannot occur synchronously before SDK dispatch through accepted #924 without out-of-lease code;
- the exact APP-STATE types or migration head differ from this pinned base;
- legacy request/fingerprint compatibility, managed/native identity, exact-revision replay, citation-to-dispatched-ID, or atomic receipt/completion invariants fail;
- a new path, API contract, runtime, database, provider, or shared fixture is needed.

The first implementation commit must update this handoff with any contract boundary discovery before source changes. Record exact base/head, tested seams, deviations, and unresolved integration status at completion. Route logic passing synthetic tests does not satisfy the integrated post-middleware budget acceptance while #924 remains unaccepted.
