# HANDOFF — DEMO: automatic World context for Plan Ask

**Status:** BLOCKED — bounded design only. This handoff grants no implementation, provider, database, service, process, Graph, or runtime lease.

- **Steward:** DEMO task `01a0efc8-f3a8-7be2-a556-33eb338338e8`
- **Repository:** `Drakosfire/DungeonMindBuddy`
- **Design base:** Buddy `main@c8a32aba3d0e050b351ab28be41d9046b9a2aef2`
- **Topology:** serial successor after the saved managed-World Plan conversation cutover. PRIME owns activation and any exact implementation lease.

## One user-visible capability

After the saved Plan conversation cutover is accepted, a natural-language question in a saved Plan automatically receives a bounded context packet from:

1. the exact committed content basis of the selected Plan, using relevant complete sections; and
2. relevant, admissible knowledge from that Plan's verified World Graph, with valid source-anchor evidence where available.

The user does not choose a campaign, Graph section, or retrieval scope. The Plan remains a usable World document without a Graph head. This is one read-only Plan Ask capability; it does not write Graph data, change Plan content, or complete J1–J6 acceptance.

### Keep request intent explicit

The current #833 Plan Ask contract sends the question and exact committed Plan content, excludes the mounted draft, and sets `graph_request.mode="none"`. Preserve that request field's existing meaning. It does not authorize automatic Graph context.

This successor adds a separate, explicit product context policy for automatic Plan/World context (provisional semantic name: `auto_plan_world`). The policy must be represented as a distinct, versioned server-resolved intent. Never infer it from `graph_request.mode="none"`, a missing Graph request, the current route, a client-supplied World/campaign ID, or the existence of Graph data. This handoff fixes the product semantics, not a public request schema; the owning runtime and PRIME must approve the exact transport contract before activation.

## Resolution and context contract

- Authenticate and verify World access before reading the Plan, Graph, anchors, or calling a provider.
- Derive the World only from the verified owner of the saved Plan. Resolve the exact committed basis server-side: World ID, Plan document ID, object revision, WorkRevision ID and number, and content SHA-256. Reject missing, foreign, removed, contradictory, stale, or uncommitted bases before Graph reads or provider work. Never use the mounted editor draft as committed context.
- Read the Plan's committed content under that frozen basis. Relevance selection may omit unrelated sections, but each included section is complete. Record every included and omitted section with stable identity, heading path, digest, and omission reason. If the aggregate context budget prevents enough Plan context to answer safely, disclose the omission or ask the user to narrow the question; do not imply that the full Plan was supplied.
- Resolve Graph retrieval against the same verified World using the existing R.3 World Graph consumer contract: the server-derived `scope_mode=world`, `focus=none`, and its GM/PLAYER admissibility rules. Do not synthesize a campaign selector or issue per-campaign queries. If implementation consumes vNext instead, its owner must explicitly map World to that contract's campaign axis/wildcard; the consumer must not invent the mapping.
- Pin the exact Graph revision/head and retrieval status. Record scope, focus, admissibility, diagnostics, truncation, selected node/edge identities, and omission reasons. No client input may widen or replace this scope.
- Treat Graph content as context, not citation authority. A source excerpt may be used or cited only after the anchor's artifact, source revision/hash, span identity, read status, and admissibility are verified against the pinned Graph basis. Invalid, unreadable, mismatched, or stale anchors cannot support a citation or source-dependent claim.
- Apply one configured aggregate provider-input budget to the complete provider request, including the question, system/developer/tool instructions and schema overhead as applicable, committed Plan sections, Graph context, verified source excerpts, and eligible conversation history. Measure the actual assembled request before dispatch and record total and per-source usage, truncation, and omissions. Do not silently truncate the request or let downstream prompt assembly clip material; if the complete request cannot fit, disclose the limitation and refuse or ask for a narrower question.
- Disclose on the Plan turn that committed Plan content and same-World Graph context were used, and show material omissions or unavailability in a place the user can act on. If Graph is unavailable or stale, explicitly disclose the limitation. A Plan-only answer is allowed only when it is safely answerable from the committed Plan alone; otherwise refuse the Graph-dependent claim or ask for a retry after recovery.

Conversation continuity remains governed by the accepted Plan cutover: only its eligible exact-basis Ask and Plan-action projections may enter provider history. This Graph capability does not widen that history or change the six-turn merge limit.

## Receipt, replay, and ownership

Persist a compact immutable per-turn context receipt sufficient to identify what the provider received without duplicating full excerpts:

- exact committed Plan basis and section inclusion/omission identities and digests;
- exact World Graph scope, focus, admissibility, revision/head, retrieval diagnostics, selected object identities, truncation, and omissions;
- verified source-anchor/artifact/revision/hash/span evidence and read status for any excerpt used;
- complete provider-input budget accounting, including question/instruction/schema overhead and total/per-source usage, packet digest, context-policy version, and user-visible disclosure/omission state.

A matching completed idempotent retry returns the original result and frozen receipt before resolving current Plan or Graph state. Reuse of the same key with changed message, basis, surface/instance, or context policy conflicts. Pending, lost, or indeterminate provider outcomes follow the accepted #865/#867 recovery contract; do not promise exactly-once provider invocation. Do not rebuild a completed turn's context from a newer Graph head.

Ownership stays at existing boundaries:

- **DEMO** owns the Plan product policy, turn disclosure, omission/recovery experience, and eventual mounted Plan witness.
- **APP-STATE** owns canonical turn identity, idempotency/replay, and durable per-turn basis/receipt under its reviewed contract.
- **AGENT-INTERACTION** owns authenticated World/Plan resolution, context assembly, provider dispatch, and retry correlation.
- **Plan/Content** owns committed Plan revisions and their authoritative reads; mounted drafts and ordinary Save remain separate.
- **MIND/DungeonMind** owns Graph scope/admissibility, revision authority, and source-anchor validity.

If any required read, receipt field, or contract is absent at an owning boundary, return the exact gap to PRIME and its owner. Do not add a competing store, resolver, migration, public route, or cross-repository adapter under this handoff.

## Failure invariants and future evidence

Fail closed before provider dispatch for unauthorized World access, an invalid or changing Plan basis, or unresolved World ownership. A dirty editor draft never substitutes for committed content. A late result remains attached to the originating turn and frozen Plan/Graph receipt, not a newly selected Plan or newer Graph head. Invalid source evidence cannot be cited. Retrieval failure, truncation, or budget omission is visible; no unsupported graph-dependent claim may be presented as grounded.

After activation, owning-boundary tests must prove exact World scoping, no campaign/client override, complete-section inclusion, aggregate budgeting and omission receipts, source-anchor verification, unauthorized-read/provider call counts of zero, and replay after current Plan/Graph state changes returning the original result without fresh reads or provider dispatch. Mounted tests must prove truthful disclosure and recovery on the real Plan conversation path. The eventual product witness must ask a question that requires same-World Graph knowledge, confirm the exact committed Plan and Graph bases, verify any cited source anchor, reload the conversation, and show that a completed retry retains its original receipt.

Use deterministic fake Graph/provider ports and only owner-approved disposable persistence for implementation tests. A real provider, database, service, or product-state witness requires its own exact PRIME lease. This design itself authorizes none of those operations.

## Predecessors and activation

The sequence is serial:

1. AGENT-INTERACTION #865 and its APP-STATE replay recovery are accepted and merged, including exact completed-receipt replay before current-state resolution.
2. The separate Plan-owned action-dialogue projection and APP-STATE exact-basis Ask projection are accepted under their own reviewed capabilities.
3. DEMO's saved managed-World Plan conversation cutover in `HANDOFF-DEMO-plan-world-conversation-cutover.md` is complete and accepted. That cutover preserves #833 committed-Plan-only Ask with Graph not requested.
4. ARCHITECTURE and the Graph owner confirm the R.3 World scope/admissibility and source-anchor contract for this consumer, including any explicit vNext mapping decision.
5. PRIME re-anchors main, inspects open PRs and active leases, then grants an exact exclusive path allowlist, branch/base, disposable persistence/provider/runtime boundaries, verification evidence, and one serial implementation PR.

Until each gate is satisfied, this remains BLOCKED. Candidate code paths may be inspected later, but this document is not a write allowlist. At this design base, #865 is open at head `b8aa42c3b4b6b5201d39b19aa62c2bef364cc94c` and changes `apps/live_control_server/models/agent_turn.py`, `apps/live_control_server/routes/agent.py`, `apps/live_control_server/services/agent_turn_service.py`, `tests/application_state/test_agent_conversation_postgres.py`, and `tests/test_agent_turn_route.py`. An open PR is transport state; it does not itself grant a post-PR runtime lease for this successor. APP-STATE's current blocked replay-repair proposal identifies `src/application_state/agent_conversation/service.py` as a required narrow ownership transfer for full-intent fingerprinting and receipt lookup before current-pointer access. That proposal is not yet a pinned, activated lease. PRIME must settle the repair authority and separately assign any successor runtime/path lease before implementation. No successor implementation PR is authorized by this handoff.

## Design review and settlement

This handoff is a separate J3 product capability after Plan conversation cutover. It does not broaden #865, the current Plan cutover, or #833. PRIME owns design acceptance, future activation, and ecosystem merge coordination. Merge of this design artifact alone would not activate implementation or claim a connected J3 witness.
