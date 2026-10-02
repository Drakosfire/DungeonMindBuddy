# HANDOFF — DEMO: Session 29 across the existing Elderwyld graph

**Status:** BLOCKED — bounded successor design recorded; no implementation lease or lane is active.

**Steward:** DEMO

**Design base:** Buddy `origin/main@5b8686829a8f734d99dca59e4998611aee5df5cb`.

**Merged serial predecessor:** Buddy PR #833, `DEMO: ask from saved Plan content`,
merged at `5a7abdfdf0be13c11b0ce849be433e03a6cb662d`. Its configured-provider
saved-Plan witness passed on 2026-10-01: committed Plan content was used, an
unsaved conflicting draft was excluded, one OpenAI `gpt-6-luna` call completed,
and the turn plus exact revision basis survived reload; no tools or graph were
used. Trace `agent-trace-a66bdf5dd035` estimated `$0.0000851`; the provider
request ID was not separately surfaced. Buddy PR #834 then merged the corrected
Session 29 full-graph gate at `5b8686829a8f734d99dca59e4998611aee5df5cb`.
Full graph querying remains BLOCKED on its independent gates. The local GM auth
prerequisite is now active under
[`HANDOFF-DEMO-agent-graph-auth.md`](HANDOFF-DEMO-agent-graph-auth.md); it does
not implement binding or graph querying.

**Future implementation PR title:** `DEMO: query Session 29 across Elderwyld graph`

## 1. One user-visible capability

From the existing saved-Plan Agent conversation, the GM can ask questions grounded in the already populated Elderwyld graph across Campaign 1 and Campaign 2. The Agent can answer a C1 question, a C2 Session 29 question, and a question that needs multiple hops across both campaigns, with truthful native source citations. Every graph-backed subquery and evidence/source read in one turn uses one pinned native graph head.

The current saved-Plan Ask slice remains graphless (`graph_request.mode=none`). This is a serial successor, not an expansion of PR #833. It adds graph context to the existing Plan conversation only after the predecessor merges; it does not create a graph, import a recap, write canon, or change Plan content.

## 2. Settled scope and identity contract

- Buddy must resolve a verified managed World and read its persisted, explicit, active binding to the existing native MIND V2 Graph `world_id=eldyrwild`. The binding has an active/inactive state and a version or revision identity. Do not derive it from World name, slug, campaign ID, or graph contents; do not treat `managed_world_id == campaign_id` as authority.
- The managed World ID and native Graph `world_id` are distinct identities. MIND V2 Graph `world_id` is separate from VNext Knowledge `space_id`; do not translate or substitute these identifiers. A missing, inactive, wrong, or stale binding fails closed before provider dispatch. #826 provisions a new empty KnowledgeSpace and does not satisfy this existing-graph binding.
- Buddy `scope_mode=world` maps to MIND V2 native scope `WORLD_CROSS_CAMPAIGN` with GM admissibility. Buddy derives GM authority from trusted server-side surface/session state before the native read. The browser and model cannot supply the native `world_id`, GM role, scope, or binding version. A non-GM turn or missing trusted GM state fails closed before provider dispatch. The older `campaign` scope with `campaign_id=longmont-c2` hides C1 and is not acceptable for this gate.
- C2 Session 29 is Buddy Agent narrative focus only. Carry `campaign_id=longmont-c2` and `session_id=session-29` in a separate Buddy narrative-context field/path used for context and ranking. Never map either value into native V2 query `scope`, `campaign_id`, `focus`, or a graph entity ID. If a C2 answer requires a native Session 29 entity, resolve its exact ID from the adopted graph during verification; if absent, report that absence instead of guessing an ID or assuming a recap. The C2 acceptance question must use facts already present in the adopted graph. The current direct adapter does not forward this focus; the successor must add the bounded Buddy-side narrative context.
- Resolve the native head once at the beginning of the turn. Pin search, every multi-hop expansion, evidence lookup, and source read to that same head. If the native API cannot honor the pin, fail closed; do not mix revisions.
- Return native citations backed by evidence/source references from the pinned head. Never infer citations from local Buddy graph files or recap registries.
- Return a compact receipt containing the managed World ID, native Graph `world_id`, binding version/state, native scope and admissibility, Buddy narrative focus, pinned revision/head ID, head-at-resolution (`is_head_at_resolution`), the latest observed native `is_head` value when available, and evidence/source references. The chosen R1 must be the current head when resolved. If R2 is published later, a consistent read pinned to R1 may complete and report `is_head=false`; if any read loses the R1 pin, re-resolve and repeat the full retrieval or fail closed. Never require a later `is_head=true` or mix heads. Do not include Plan Markdown or a graph dump in the receipt, response trace, or logs.

The saved committed Plan remains governed by the merged PR #833 content-basis
contract. The user has separately granted blanket authorization for bounded use
of their personal corpus in this connected session, including graph excerpts.
Before provider dispatch, the Plan UI/turn contract must disclose the configured
provider destination and that bounded graph evidence/source excerpts may be
sent. After the turn, show the exact evidence references and excerpts actually
included in the provider request. This does not require a two-phase preview.
PR #833 discloses the committed Plan text and question, but that disclosure
alone does not identify graph context or provider destination. Send only the
context needed to answer; never the full graph. Do not copy Plan Markdown or
full graph payloads into receipts, native query logs, or traces.

## 3. Existing graph evidence and limits

A static audit of the sealed Eldyrwild V6 adoption bundle reports 469 objects, 323 relationships, 83 source artifacts, and 93 contributions. This establishes the package's contents only; it does not prove that the current native graph answers C1, C2, or cross-campaign queries.

A prior PRIME read-only native observation recorded head `rev:680c246047d67f9fe0293ee90526f670`, parent adoption `rev:34b1f8e2625d5ba693fc726a2a1a4720`, and 95 native contributions. Treat that as historical evidence, not a live witness for this successor. The older local Buddy graph snapshot is not native authority. Session 28 recap ingestion and proof of Sessions 26–28 in native authority remain separate gates; this handoff does not claim them complete.

## 4. Acceptance witness

- On the real, non-empty native `eldyrwild` Graph, use a deliberately distinct managed World ID with a persisted active binding to Graph `world_id=eldyrwild`. Keep this witness read-only: do not initialize, create, or populate a KnowledgeSpace or mutate the existing graph.
- At one captured current native head R1, ask a C1 question, a C2 Session 29 question using facts already present in the adopted graph, and a cross-campaign multi-hop question requiring evidence from both campaigns. Verify every search, hop, evidence lookup, and source read is pinned to R1. Record that R1 was head at resolution and report any later `is_head=false` honestly.
- Verify `campaign_id=longmont-c2` and `session_id=session-29` travel only in the separate Buddy narrative-context path for context/ranking. Neither value may populate native V2 query `scope`, `campaign_id`, or `focus`, or act as a graph entity ID. If a C2 answer requires a native Session 29 entity ID and it is absent, report that absence; do not invent an ID or assume a recap.
- Verify answer citations resolve to native source/evidence references from the pinned head and support the claims. Reject unsupported claims instead of manufacturing citations.
- In an isolated disposable native fixture, test concurrent publication during one turn: resolve R1 as head, advance only the fixture to R2 while retrieval is in progress, then prove every subread either completes against pinned R1 with truthful head-at-resolution/current-`is_head` reporting, or triggers an explicit full retry at R2. Mixing R1 and R2 is a failure.
- In the same isolated fixture class, prove head refresh across restart: read fixture head R1, advance only the fixture to R2, restart Buddy, re-resolve the binding and newest head, then verify a graph-backed query and receipt identify R2. Never advance the real `eldyrwild` graph for either fixture witness.
- Prove wrong, missing, inactive, and stale binding identities fail closed before provider dispatch. Add a non-GM negative witness using trusted server-side session state; browser/model-supplied role, scope, native ID, or binding version cannot grant access.
- Before provider dispatch, verify the Plan UI shows the configured destination and that bounded graph evidence/source excerpts may be sent. After the turn, verify it identifies the exact evidence references and excerpts actually included. No full graph payload is sent or persisted in receipts, traces, or logs.
- Run owner-boundary tests at the Buddy binding/route and MIND native query/evidence APIs. Static bundle inspection or a fake adapter alone is not acceptance evidence; combine the read-only live `eldyrwild` witness with isolated fixture concurrency/restart witnesses.

## 5. Blockers and topology

This is a serial successor. It has no write lease and allocates no implementation lane while BLOCKED.

Before activation, the steward must:

1. Keep this design anchored at current Buddy `origin/main@5b8686829a8f734d99dca59e4998611aee5df5cb`; preserve the #833 witness PASS and #834 BLOCKED gate accurately. Obtain ARCHITECTURE exact-head acceptance of this corrected contract; re-anchor again before any later implementation dispatch.
2. Reinspect PR #826 and all active leases. PR #826's empty-space provisioning does not satisfy or implement the binding to this pre-existing Elderwyld graph. Resolve any shared World registry/binding ownership before assigning paths.
3. Land and independently review the active serial local-operator GM prerequisite in [`HANDOFF-DEMO-agent-graph-auth.md`](HANDOFF-DEMO-agent-graph-auth.md). It protects the listed graph-read responses, including Agent/query, projection/retrieval, Threat query-hydration, and Threat identity-candidate data. Its bearer capability proves only local-operator access; MIND GM admissibility remains independent. Before any C1+C2 retrieval activation, recheck route coverage and prove no excluded write-workflow route returns native source, evidence, object, or projection data or permits cross-campaign retrieval through browser-controlled scope.
4. Confirm a read-only native MIND V2 Graph endpoint for `world_id=eldyrwild` and a separate isolated disposable native fixture/runtime for concurrent head movement and R1→R2 restart proof. Keep the real graph witness read-only.
5. Pin the exact Buddy and MIND base refs, final exclusive path allowlists, data stores, runtime/database/output ownership, verification commands, and PR topology in an ACTIVE handoff before implementation.

Candidate boundaries for later assignment are Buddy's managed-World binding owner, graph query context/Agent route and service, native response/citation receipt models, and their tests, plus the MIND V2 cross-campaign query/evidence boundary. These are investigation targets only, not a write allowlist. Do not edit them under this BLOCKED handoff.
