# Handoff: Managed World Agent Graph Adapter

**Status:** BLOCKED — proposal only; no implementation lease is active.
**Implementation owner:** DungeonMindBuddy owns Agent orchestration and its runtime adapter.
**Receipt owner:** APP-STATE owns durable Agent conversation/provenance contracts.
**Authority owners:** Buddy owns managed World verification/binding; DungeonMind owns native graph authority and reads.
**Historical design source:** Server PR #36 at exact head `be6cf4789500949aa58562b09304d7b7d9b5cd0b` was a steward-side proposal held by PRIME for incorrect repository ownership and replay semantics; it was not formally accepted. This Buddy handoff carries forward its useful source analysis with corrected ownership and replay rules.

## Re-anchored basis

- DungeonMindBuddy main: `a1d2424a986328a9459631c0634da67bc91d1620` (includes merged #904 at `fb1c48d622c9d8d404b1dddb5d5f618e03cc7ef0` and merged #907; latest Plan-to-Play settlement is included).
- DungeonOverMind architecture and ownership authorities were refreshed at `9a80ab328a687039519569855c2b25a4ee7df07b`.
- Open Buddy PRs rechecked for collisions:
  - #886 remains open and owns Plan navigation/shell paths. The #906 mounted-harness repair has merged and #904's lease is settled; allocation of `PlanSurfacePage.test.tsx` follows #886's explicit geometry settlement and then the card slice. Do not assign it to another worker in this handoff. No path overlap with this handoff.
  - #826 remains open and owns managed World/KnowledgeSpace provisioning, registry, and binding implementation paths. No path overlap with this handoff.
  - #904 Agent composer merged as `fb1c48d622c9d8d404b1dddb5d5f618e03cc7ef0`; it preserves graphless exact-basis Plan Ask.
  - #907 Plan-to-Playable design and its follow-up settlement are merged at current main `a1d2424a986328a9459631c0634da67bc91d1620`; it does not alter Graph receipt ownership or replay semantics.
  - Merged #898 remains an APP-STATE Plan Ask projection and does not change the Graph receipt contract.
- This proposed handoff file is still absent from main. Recheck current heads, leases, and path collisions before activation.

## Primary question

Can Buddy's generic Agent Graph read translate a verified managed World into its currently active native graph authority, preserve supported query scope and the selected graph revision, and attach truthful authority evidence to the resulting durable turn without changing public API vocabulary or graphless Plan Ask v1?

## Observed defect and existing seam

At the inspected Buddy code baseline, `apps/live_control_server/routes/agent.py::_graph_resolver` passed the requested managed World ID to the native graph projection as `world_id`. If managed and native IDs differ, the native read can target the wrong authority. The existing full-route test used equal IDs, so it did not prove translation.

Buddy already has `services/managed_world_graph_projection.py::project_managed_world_graph`. It resolves a verified managed World and active native binding, reads the graph, rereads the binding, and rejects drift in native World ID, binding version, or source root. Reuse that authority fence; never accept client-supplied native IDs or binding versions.

The Agent route's `graph_scope.world_id` is also the canonical managed World ID for turn invariants, historical references, retry, and replay. Preserve that identity in product scope. The currently inspected durable Graph historical reference records managed ID and graph revision, but not the native ID or binding version; this is insufficient to attest which binding produced a completed answer.

## Required receipt and replay semantics

A Graph receipt must identify the original evidence and authority used by the turn, at minimum:

```text
managed_world_id
native_world_id
binding_version
graph_revision
```

Keep those fields in server-owned durable provenance. Do not expose native authority as a client-selected request field.

- **Completed durable replay:** return the immutable stored answer and its original Graph receipt. Do not require the active binding to still match, and do not perform a fresh Graph or provider read. The receipt describes historical evidence used for that completed answer; it does not claim that the same binding is still current.
- **Pending or interrupted retry:** before any Graph source read or provider call, revalidate that the original managed World still resolves to the recorded native World and binding version, and verify that the exact recorded Graph revision remains available. A newer Graph head alone is not binding drift: use the original historical revision if it remains available. If the binding changed or the pinned revision is unavailable, stop with an explicit stale/unavailable outcome. Never refresh the pin or silently substitute a newer revision.
- **Initial execution:** resolve the active binding from verified managed ownership, preserve the requested revision pin and supported scope, and use the existing before/after binding fence. Once the exact Graph snapshot and its available evidence references/anchors are established, APP-STATE must durably freeze and attach their versioned receipt to the turn before provider dispatch. The receipt stores those available evidence references/anchors and any opened-source proof only when a separate authorized product opener actually supplied verified proof. This metadata-only adapter does not open source bodies and must not claim opened-source citations. A retry reuses the immutable receipt. On success, validate answer references against the frozen evidence, then atomically commit the answer and validated reference mapping with that unchanged receipt. Preserve strict-v1 provenance.
- Keep response/product ownership and turn invariants anchored to the managed World ID.
- APP-STATE owns the versioned durable receipt contract, its pre-dispatch freeze, and atomic answer/reference-mapping completion. Its proposed two-document design has not been published: the APP-STATE thread reports that publication was blocked pending direct authorization. Treat the receipt details below as this handoff's proposal, not as an APP-STATE accepted contract. Do not imply that a route-only in-memory receipt is durable across process restart.

## DungeonMind source-read and retention boundary

Re-checked DungeonMind main `619329c2c8586572ffd04558a79b3555c2ca3764`:

- The legacy World Graph retrieval path can pin and return an exact graph projection revision. Its admitted source anchors carry evidence/source identity and locator metadata; they do not open or return source bodies. See [`world_graph_retrieval.py`](https://github.com/DrakosFire/DungeonMind/blob/619329c2c8586572ffd04558a79b3555c2ca3764/src/dungeonmind/application/world_graph_retrieval.py#L212-L230).
- DungeonMind's `SourceRepository` is an identity store; its contract explicitly allows bodies to live elsewhere. Evidence metadata and locators may be durable while the referenced body is external. See [`repositories.py`](https://github.com/DrakosFire/DungeonMind/blob/619329c2c8586572ffd04558a79b3555c2ca3764/src/dungeonmind/application/repositories.py#L412-L443) and [`evidence.py`](https://github.com/DrakosFire/DungeonMind/blob/619329c2c8586572ffd04558a79b3555c2ca3764/src/dungeonmind/contracts/evidence.py#L17-L22).
- DungeonMind's R.2 handoff explicitly leaves opening source bodies to a later product-owned opener after anchor validation. It does not promise historical body retention. See [`HANDOFF-cutover-direct-world-graph-retrieval.md`](https://github.com/DrakosFire/DungeonMind/blob/619329c2c8586572ffd04558a79b3555c2ca3764/Docs/Handoffs/HANDOFF-cutover-direct-world-graph-retrieval.md#L86-L86).
- A separate vNext native-source admission path persists exact admitted body bytes and can reopen text with pinned-revision, span-proof, digest, and active-source checks. That API belongs to the KnowledgeSpace/vNext path; it is not wired to this legacy World Graph Agent adapter. Do not claim DungeonMind has no source reopening capability at all.

Therefore completed-answer replay can be fully historical by returning the stored answer and its Graph receipt, without reopening source bodies. This metadata-only adapter supplies evidence references/anchors; it does not supply opened-source citation text or proof. If a future product requirement needs reopening the cited source itself after completion, the legacy Graph receipt alone is insufficient: the product opener needs an explicit source-body identity and retention/revalidation contract. That is a separate blocker and must not be smuggled into this adapter slice.

## Required product invariants

- Keep current Agent route authentication and owner/saved-Plan scope checks at the boundary.
- Preserve currently supported graph query scope, campaign/focus/selection inputs, and revision pins; the adapter must not silently drop them.
- Preserve Plan Agent Ask v1 graphless behavior: Plan surface with primary Plan requires graph request mode `none`. This slice does not activate Graph for Plan Ask.
- Keep native graph access read-only. Use fake native-owner route tests; no provider/model calls are required to establish translation and receipt semantics.
- Do not trust request fields for native ID, binding version, source root, or revision receipt authority.

## Candidate Buddy implementation lease, pending activation

The exact write set requires PRIME approval after refreshed collision/lease review:

- `apps/live_control_server/routes/agent.py`
- `apps/live_control_server/services/managed_world_graph_projection.py` only if its request cannot preserve supported Agent scope and revision pins
- `tests/test_agent_turn_route.py`
- `tests/test_managed_world_graph_projection.py` only if the projection service changes

APP-STATE must separately approve and own the versioned durable receipt type, repository, service, and persistence changes. Do not edit APP-STATE-owned files under the Buddy route lease. Do not edit #886-owned Page or shell paths; Page test allocation follows #886 geometry settlement, then the card slice.

## Acceptance witness

A fake-owner full HTTP route test must use distinct managed and native IDs, an active binding, and a requested graph revision. It must prove that the native owner receives the resolved native ID and pin, while product scope remains managed-ID based. At the persistence boundary, prove the versioned receipt is durably attached before provider dispatch, preserves strict-v1 provenance, and records the original binding/revision/evidence references; prove successful completion validates answer references against that frozen evidence and atomically saves the answer plus validated reference mapping against the unchanged receipt.

Add tests proving:

1. Binding drift during initial projection is rejected before a result is accepted.
2. Completed replay returns the stored answer and original receipt after the active binding changes, with no Graph or provider call.
3. Pending/interrupted retry validates the original active managed/native/binding tuple and exact historical revision availability before reads; a newer Graph head alone is accepted when the pinned revision remains available, and the retry never replaces the receipt or pin.
4. Existing authentication and scope denials happen before receipt/runtime work.
5. Client native authority fields are rejected or ignored according to the current strict request contract.
6. Plan Ask v1 stays graphless.

Use isolated fake services and test clients only. Do not contact providers or depend on live 5202/5203 services.

Before proposing code readiness, inspect the exact cumulative Buddy base-to-head diff and run focused route/projection and receipt-owner tests plus applicable repository gates. Record exact base/head, evidence, and acceptance token only after all witnesses pass.

## Blockers and stop conditions

This handoff remains **BLOCKED** until:

1. APP-STATE publishes and confirms the versioned receipt contract, durable pre-dispatch freeze, strict-v1 provenance preservation, atomic answer/citation completion, immutable retry behavior, and exact pinned-revision availability check. Its current proposed two-document design is unpublished and is not an accepted dependency yet.
2. PRIME reviews this Buddy-owned design and explicitly activates the implementation lease after fresh PR/path collision checks.
3. The adapter mapping is confirmed for currently supported campaign/focus/selection fields and revision semantics, with a fake-owner test witness.

Stop and return to PRIME if the accepted semantics require a new public API contract, broader auth changes, a database migration outside the APP-STATE owner lease, or changes to DungeonMind native graph read/write semantics. Do not expand into Plan Graph activation, provider execution changes, DungeonMind graph writes, or runtime operation.

## Operational limits

Do not restart or modify the UI on 5202, API on 8000, or DOGFOOD on 5203. Do not modify operator credentials or private corpus state. Future fixtures must use isolated test clients/ports and must not use 5202.
