# HANDOFF — DEMO: Session 29 across the existing Elderwyld graph

**Status:** BLOCKED — bounded successor design recorded; no implementation lease or lane is active.

**Steward:** DEMO

**Design base:** Buddy `origin/main@c48abb9fa5857df90af0b086ab78294445fd252a`.

**Serial predecessor:** Buddy PR #833, `DEMO: ask from saved Plan content`, head `86c1ea2552a6f035f4b172ce83a694f57628f9b1`. This graph successor must not start until #833 merges and the steward re-anchors.

**Future implementation PR title:** `DEMO: query Session 29 across Elderwyld graph`

## 1. One user-visible capability

From the existing saved-Plan Agent conversation, the GM can ask questions grounded in the already populated Elderwyld graph across Campaign 1 and Campaign 2. The Agent can answer a C1 question, a C2 Session 29 question, and a question that needs multiple hops across both campaigns, with truthful native source citations. Every graph-backed subquery and evidence/source read in one turn uses one pinned native graph head.

The current saved-Plan Ask slice remains graphless (`graph_request.mode=none`). This is a serial successor, not an expansion of PR #833. It adds graph context to the existing Plan conversation only after the predecessor merges; it does not create a graph, import a recap, write canon, or change Plan content.

## 2. Settled scope and identity contract

- Buddy must resolve a verified managed World and read its persisted, explicit binding to the existing native MIND `space_id=eldyrwild`. The binding has an active/inactive state and a version or revision identity. Do not derive it from World name, slug, campaign ID, or graph contents; do not treat `managed_world_id == campaign_id` as authority.
- The managed World ID and native space ID are distinct identities. A missing, inactive, wrong, or stale binding fails closed before provider dispatch.
- Buddy `scope_mode=world` maps to MIND V2 native scope `WORLD_CROSS_CAMPAIGN` with GM admissibility. The older `campaign` scope with `campaign_id=longmont-c2` hides C1 and is not acceptable for this gate.
- C2 Session 29 is Buddy Agent narrative focus only. Carry the exact C2/session focus into the Plan Agent turn, but do not use it as the native scope filter. The current direct adapter does not forward this focus; the successor must add the bounded Buddy-side narrative context.
- Resolve the native head once at the beginning of the turn. Pin search, every multi-hop expansion, evidence lookup, and source read to that same head. If the native API cannot honor the pin, fail closed; do not mix revisions.
- Return native citations backed by evidence/source references from the pinned head. Never infer citations from local Buddy graph files or recap registries.
- Return a compact receipt containing the managed World ID, native space ID, binding version/state, native scope and admissibility, C2/session narrative focus, native revision/head IDs, and evidence/source references. Do not include Plan Markdown or a graph dump in the receipt, response trace, or logs.

The saved committed Plan remains governed by the PR #833 content-basis contract. Its Markdown may be sent to the configured model as already disclosed by that surface, but it must not be copied into graph receipts, native query logs, or traces.

## 3. Existing graph evidence and limits

A static audit of the sealed Eldyrwild V6 adoption bundle reports 469 objects, 323 relationships, 83 source artifacts, and 93 contributions. This establishes the package's contents only; it does not prove that the current native graph answers C1, C2, or cross-campaign queries.

A prior PRIME read-only native observation recorded head `rev:680c246047d67f9fe0293ee90526f670`, parent adoption `rev:34b1f8e2625d5ba693fc726a2a1a4720`, and 95 native contributions. Treat that as historical evidence, not a live witness for this successor. The older local Buddy graph snapshot is not native authority. Session 28 recap ingestion and proof of Sessions 26–28 in native authority remain separate gates; this handoff does not claim them complete.

## 4. Acceptance witness

- Use a deliberately distinct managed World ID with an active explicit binding to the existing, non-empty native `eldyrwild` graph. Prove the read path does not initialize, create, or populate a KnowledgeSpace.
- At one captured native head, ask a C1 question and a C2 Session 29 question, then a cross-campaign multi-hop question that requires evidence from both campaigns. Verify every search, hop, evidence lookup, and source read used that same head.
- Verify the answer citations resolve to native source/evidence references and support the claims. Reject unsupported claims instead of manufacturing citations.
- Restart the Buddy process/runtime, re-resolve the active binding and newest native head R2, and repeat a graph-backed query. The returned receipt and citations must identify R2 and its sources.
- Prove wrong, missing, inactive, and stale binding identities fail closed before provider dispatch. Prove no Plan Markdown or full graph payload is persisted in receipts, traces, or logs.
- Run owner-boundary tests at the Buddy binding/route and MIND native query/evidence APIs. A static bundle inspection or fake adapter alone is not acceptance evidence; a read-only live witness against the existing native graph is required.

## 5. Blockers and topology

This is a serial successor. It has no write lease and allocates no implementation lane while BLOCKED.

Before activation, the steward must:

1. Wait for PR #833 to merge, fetch the current remote default, and reconcile the consumer receipt/handoff with the merged base.
2. Reinspect PR #826 and all active leases. PR #826's empty-space provisioning does not satisfy or implement the binding to this pre-existing Elderwyld graph. Resolve any shared World registry/binding ownership before assigning paths.
3. Confirm a read-only native MIND V2 endpoint and isolated runtime are available to prove `WORLD_CROSS_CAMPAIGN`, pinned-head evidence/source reads, and restart behavior against `eldyrwild`.
4. Pin the exact Buddy and MIND base refs, final exclusive path allowlists, data stores, runtime/database/output ownership, verification commands, and PR topology in an ACTIVE handoff before implementation.

Candidate boundaries for later assignment are Buddy's managed-World binding owner, graph query context/Agent route and service, native response/citation receipt models, and their tests, plus the MIND V2 cross-campaign query/evidence boundary. These are investigation targets only, not a write allowlist. Do not edit them under this BLOCKED handoff.
