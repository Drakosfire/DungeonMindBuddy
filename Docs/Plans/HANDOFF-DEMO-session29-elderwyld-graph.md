# HANDOFF — DEMO: Session 29 across the existing Elderwyld graph

**Status:** BLOCKED — bounded successor design recorded; no implementation lease or lane is active.

**Steward:** DEMO

**Design base:** Buddy `origin/main@5a7abdfdf0be13c11b0ce849be433e03a6cb662d`.

**Merged serial predecessor:** Buddy PR #833, `DEMO: ask from saved Plan content`,
merged at `5a7abdfdf0be13c11b0ce849be433e03a6cb662d`. The saved-Plan Ask
implementation is merged; its configured-provider live witness remains
unclaimed. This successor is re-anchored on that merge and remains BLOCKED on
its own design/runtime gates.

**Future implementation PR title:** `DEMO: query Session 29 across Elderwyld graph`

## 1. One user-visible capability

From the existing saved-Plan Agent conversation, the GM can ask questions grounded in the already populated Elderwyld graph across Campaign 1 and Campaign 2. The Agent can answer a C1 question, a C2 Session 29 question, and a question that needs multiple hops across both campaigns, with truthful native source citations. Every graph-backed subquery and evidence/source read in one turn uses one pinned native graph head.

The current saved-Plan Ask slice remains graphless (`graph_request.mode=none`). This is a serial successor, not an expansion of PR #833. It adds graph context to the existing Plan conversation only after the predecessor merges; it does not create a graph, import a recap, write canon, or change Plan content.

## 2. Settled scope and identity contract

- Buddy must resolve a verified managed World and read its persisted, explicit, active binding to the existing native MIND V2 Graph `world_id=eldyrwild`. The binding has an active/inactive state and a version or revision identity. Do not derive it from World name, slug, campaign ID, or graph contents; do not treat `managed_world_id == campaign_id` as authority.
- The managed World ID and native Graph `world_id` are distinct identities. MIND V2 Graph `world_id` is separate from VNext Knowledge `space_id`; do not translate or substitute these identifiers. A missing, inactive, wrong, or stale binding fails closed before provider dispatch. #826 provisions a new empty KnowledgeSpace and does not satisfy this existing-graph binding.
- Buddy `scope_mode=world` maps to MIND V2 native scope `WORLD_CROSS_CAMPAIGN` with GM admissibility. Buddy derives GM authority from trusted server-side surface/session state before the native read. The browser and model cannot supply the native `world_id`, GM role, scope, or binding version. A non-GM turn or missing trusted GM state fails closed before provider dispatch. The older `campaign` scope with `campaign_id=longmont-c2` hides C1 and is not acceptable for this gate.
- C2 Session 29 is Buddy Agent narrative focus only. Carry `campaign_id=longmont-c2` and `session_id=session-29` as narrative-focus labels into the Plan Agent turn; these are not a canonical native graph entity ID and neither narrows the native scope filter. If the query requires a native Session 29 entity ID, resolve it from the adopted graph during verification; if it is absent, report that absence instead of guessing an ID or assuming a Session 29 recap. The C2 acceptance question must use facts already present in the adopted graph. The current direct adapter does not forward this focus; the successor must add the bounded Buddy-side narrative context.
- Resolve the native head once at the beginning of the turn. Pin search, every multi-hop expansion, evidence lookup, and source read to that same head. If the native API cannot honor the pin, fail closed; do not mix revisions.
- Return native citations backed by evidence/source references from the pinned head. Never infer citations from local Buddy graph files or recap registries.
- Return a compact receipt containing the managed World ID, native Graph `world_id`, binding version/state, native scope and admissibility, C2/session narrative focus, native revision/head IDs, `is_head`, and evidence/source references. Require `is_head=true` for the pinned current head. Do not include Plan Markdown or a graph dump in the receipt, response trace, or logs.

The saved committed Plan remains governed by the merged PR #833 content-basis
contract. The user has separately granted blanket authorization for bounded use
of their personal corpus in this connected session, including graph excerpts.
Before dispatch, the Plan UI/turn contract must still disclose the configured
provider destination and the bounded retrieved graph evidence/source excerpts
being sent for that turn. Send only excerpts needed to answer; never the full
graph. PR #833 discloses the committed Plan text and question, but that
disclosure alone does not identify the graph excerpts or provider destination.
Do not copy Plan Markdown or full graph payloads into graph receipts, native
query logs, or traces.

## 3. Existing graph evidence and limits

A static audit of the sealed Eldyrwild V6 adoption bundle reports 469 objects, 323 relationships, 83 source artifacts, and 93 contributions. This establishes the package's contents only; it does not prove that the current native graph answers C1, C2, or cross-campaign queries.

A prior PRIME read-only native observation recorded head `rev:680c246047d67f9fe0293ee90526f670`, parent adoption `rev:34b1f8e2625d5ba693fc726a2a1a4720`, and 95 native contributions. Treat that as historical evidence, not a live witness for this successor. The older local Buddy graph snapshot is not native authority. Session 28 recap ingestion and proof of Sessions 26–28 in native authority remain separate gates; this handoff does not claim them complete.

## 4. Acceptance witness

- On the real, non-empty native `eldyrwild` Graph, use a deliberately distinct managed World ID with a persisted active binding to Graph `world_id=eldyrwild`. Keep this witness read-only: do not initialize, create, or populate a KnowledgeSpace or mutate the existing graph.
- At one captured current native head R1, ask a C1 question, a C2 Session 29 question using facts already present in the adopted graph, and a cross-campaign multi-hop question requiring evidence from both campaigns. Verify every search, hop, evidence lookup, and source read used that same head and the receipt reports `is_head=true`.
- Verify the Plan focus uses `campaign_id=longmont-c2` and `session_id=session-29` as narrative labels, not as a native graph entity ID; neither value narrows the MIND V2 `WORLD_CROSS_CAMPAIGN` query. If a native Session 29 entity ID is required but absent, report that absence and do not invent an ID or assume a recap.
- Verify answer citations resolve to native source/evidence references from the pinned head and support the claims. Reject unsupported claims instead of manufacturing citations.
- In an isolated disposable native fixture, prove head refresh across restart: read fixture head R1, advance only the fixture to R2, restart Buddy, re-resolve the binding and newest head, then verify a graph-backed query and receipt identify R2 with `is_head=true`. Never advance the real `eldyrwild` graph for this witness.
- Prove wrong, missing, inactive, and stale binding identities fail closed before provider dispatch. Add a non-GM negative witness using trusted server-side session state; prove browser/model-supplied role, scope, native ID, or binding version cannot grant access.
- Verify the Plan UI/turn contract shows the configured provider destination and the exact bounded graph evidence/source excerpts sent for the turn. No full graph payload is sent or persisted in receipts, traces, or logs.
- Run owner-boundary tests at the Buddy binding/route and MIND native query/evidence APIs. Static bundle inspection or a fake adapter alone is not acceptance evidence; combine the read-only live `eldyrwild` witness with the isolated fixture restart witness.

## 5. Blockers and topology

This is a serial successor. It has no write lease and allocates no implementation lane while BLOCKED.

Before activation, the steward must:

1. Keep this design anchored at `origin/main@5a7abdfdf0be13c11b0ce849be433e03a6cb662d`; record that #833 is merged there and that its configured-provider witness remains outstanding. Re-anchor again before any later implementation dispatch.
2. Reinspect PR #826 and all active leases. PR #826's empty-space provisioning does not satisfy or implement the binding to this pre-existing Elderwyld graph. Resolve any shared World registry/binding ownership before assigning paths.
3. Confirm a read-only native MIND V2 Graph endpoint for `world_id=eldyrwild` and a separate isolated disposable native fixture/runtime for the R1→R2 restart proof. Keep the real graph witness read-only.
4. Pin the exact Buddy and MIND base refs, final exclusive path allowlists, data stores, runtime/database/output ownership, verification commands, and PR topology in an ACTIVE handoff before implementation.

Candidate boundaries for later assignment are Buddy's managed-World binding owner, graph query context/Agent route and service, native response/citation receipt models, and their tests, plus the MIND V2 cross-campaign query/evidence boundary. These are investigation targets only, not a write allowlist. Do not edit them under this BLOCKED handoff.
