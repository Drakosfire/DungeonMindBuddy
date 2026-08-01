# REPORT — SBW09c Threat publication re-anchor and capability decomposition

**Status:** ACTIVE RECONCILIATION RECORD  
**Date:** 2026-08-01  
**Repository:** `Drakosfire/DungeonMindBuddy`  
**Reconciled main:** `35c3d34c6db44371cba81eb65883b2b76e011cad`  
**Predecessor anchor:** `5744477839b9e57b60c77554a167405c8c7df2eb` — merged PR `#467`  
**Next authority:** [`../Plans/HANDOFF-sbw09c1-threat-publication-proposal.md`](../Plans/HANDOFF-sbw09c1-threat-publication-proposal.md)

## 1. Reconciliation result

`origin/main` is two commits ahead of the PR `#467` anchor. The intervening merged work is PR `#469`, a documentation-only interaction-layer authority sync. It does not modify SBW08, SBW09a, SBW09b, `ThreatStatblockBinding`, Graph Kernel contribution merge, or extract-promote proposal/confirm code.

The Threat roadmap and tracker were stale at this anchor. Both still described SBW09b as pending and SBW09c as blocked on it. This report repairs that authority:

```text
SBW08   exact graph binding contract                       MERGED #457
SBW09a  durable exact-source / expected-parent operation   MERGED #462
SBW09b  exact create/connect/refuse identity resolution    MERGED #467
SBW09c1 durable exact no-write publication proposal        NEXT
SBW09c2 proposal-bound commit + receipt/recovery/verify     BLOCKED ON SBW09c1
SBW10a  Hermes query + exact mechanics hydration            BLOCKED ON PUBLICATION
SBW10b  exact compact/full Threat projection                BLOCKED ON SBW10a
```

No current open PR touches Threat publication, statblock binding, or graph-governance ownership:

- PR `#468` is the separate TL01G temporal-abstention implementation lane.
- PR `#465` is a stale/diverged TL01G handoff PR.
- PR `#442` is a draft transfer snapshot explicitly marked not for merge.

GitHub exposed no workflow runs or combined status contexts for `35c3d34c...`. This report therefore does not claim a green repository-wide CI baseline.

## 2. Current predecessor authority map

### SBW09a — source and expected-parent authority

Owner:

```text
apps/live_control_server/models/threat_publication.py
apps/live_control_server/services/threat_publication_operations.py
apps/live_control_server/routes/threat_publication.py
```

Durable state:

```text
out/threat_publication_operations/<draft_id>/ledger.json
```

Exact fields consumed by SBW09c:

| SBW09a field | Publication use |
|---|---|
| `operation_id` | Durable publication-root identity. |
| `source_snapshot.draft_id` / `draft_version` | Exact authored source identity; never reconstructed from mutable draft state. |
| `source_snapshot.world_id` / `campaign_id` | World and campaign scope for the contribution and proposal. |
| `source_snapshot.name` | Create-new Threat label and canonical initial alias. |
| `source_snapshot.description` | Create-new authored description attribute. |
| `source_snapshot.threat_kind` | Create-new Threat role/kind metadata. |
| `source_snapshot.intended_roles` | Create-new semantic role attributes. |
| `source_snapshot.tags` | Create-new semantic tag attributes. |
| `source_snapshot.accepted_mechanics_ref` | Exact six-field mechanics locator used to construct the external resource and binding. |
| `source_digest` | Exact source snapshot identity and proposal input. |
| `expected_parent_revision_id` | Sole World Graph parent authority. |
| `state` | Must be `ready` at proposal preparation and revalidated at confirmation. |

SBW09a lock order is:

```text
publication ledger lock
→ ThreatDraft store read
→ trusted World Graph head read
```

SBW09c must never call back into a proposal/receipt owner from any predecessor lock.

### SBW09b — Threat identity authority

Owner:

```text
apps/live_control_server/models/threat_publication_identity.py
apps/live_control_server/services/threat_publication_identity.py
apps/live_control_server/routes/threat_publication_identity.py
```

Durable state:

```text
out/threat_publication_identity/<draft_id>/<operation_id>/ledger.json
```

Exact fields consumed by SBW09c:

| SBW09b field | Publication use |
|---|---|
| `resolution_id` | Exact identity-decision authority and proposal input. |
| `draft_id` / `operation_id` | Must equal the SBW09a operation identity. |
| `source_digest` | Must equal the SBW09a source digest. |
| `expected_parent_revision_id` | Must equal the SBW09a expected parent. |
| `candidate_set_digest` / embedded candidate set | Exact reviewed candidate evidence. |
| `decision` | Sole `create_new`, `connect_existing`, or `refuse` authority. |
| `created_node_id` | Exact deterministic Threat ID for `create_new`. |
| `selected_target` | Exact snapshotted Threat target for `connect_existing`. |
| `request_digest` | Durable identity-decision replay identity. |
| `state` | Must be `active`; superseded resolutions cannot prepare or confirm. |

SBW09b lock order is:

```text
identity-resolution lock
→ SBW09a publication lock
→ exact World Graph projection / exact-revision occupancy read
```

### SBW08 — exact external resource and binding authority

Owner:

```text
src/graph_memory/union_supergraph/statblock_binding.py
```

The graph-owned contract already provides:

- deterministic external node identity;
- deterministic binding and edge identity;
- strict provider/statblock/revision/contract/version/digest agreement;
- pinned-only binding semantics;
- rejection of mechanics bodies and unsupported fields;
- exact typed projection and immutable round-trip support.

SBW09c must call these helpers rather than reproduce ID or validation formulas.

### Existing proposal-bound graph governance

Owners:

```text
src/graph_memory/extract_promote_proposal.py
src/graph_memory/extract_promote_ops.py
src/graph_memory/kernel/contributions.py
src/graph_memory/kernel/contribution_merge.py
```

Current behavior already proves the following reusable semantics:

| Concern | Existing owner and behavior |
|---|---|
| Proposal identity | `seal_promote_proposal` / `seal_multi_contribution_promote_proposal` seal a complete effect body and proposal digest. |
| Confirmation binding | `verify_promote_proposal` rejects changed effect, proposal, parent, principal, or selected assertions. |
| Deterministic contribution | `create_graph_contribution` includes proposal and selection digests in contribution identity. |
| Exact parent | `merge_contribution_to_revision(... expected_parent_revision_id=...)` performs an expected-parent check and CAS-protected immutable publish. |
| Atomic graph result | One contribution applies all accepted assertions to one proposed store and publishes one revision or leaves the prior graph revision authoritative. |
| Replay | An already-active and already-applied identical contribution returns an idempotent no-op. |
| Receipt | `ContributionMergeResult` exposes `published`, parent, exact revision, contribution IDs, assertion IDs, and diagnostics. |
| Exact verification | Existing extract-promote confirm verifies rebuild and projection against the exact committed revision, never mutable current head. |
| Honest post-commit failure | Existing confirm reports `published=true` plus the exact committed revision when verification fails or degrades. |

The current proposal format is extract-promote-shaped rather than a general public Graph Kernel proposal API. SBW09c1 may reuse its sealing and verification functions through an explicit field mapping, but it must not pretend source-extraction terminology is Threat identity authority. If a correct adapter cannot be built without changing the proposal format or adding a generic public proposal contract, implementation must stop and propose a contract-first predecessor slice.

## 3. Capability decomposition

| Candidate outcome | Independently useful? | New public/durable contract? | Failure/recovery boundary | Decision |
|---|---:|---:|---|---|
| Construct exact create/connect Threat publication assertions | Yes | No new graph schema; new application mapping | Pure validation/build failure | Include in SBW09c1 |
| Seal and durably reload an exact no-write proposal | Yes | Yes — proposal ledger and response contract | stale predecessor, changed request, storage integrity | Include in SBW09c1 |
| Bind confirmation to exact proposal/operation/resolution/parent | Yes | Existing sealed-proposal semantics, new Threat route contract | changed proposal or predecessor | SBW09c2 |
| Commit one atomic contribution | Yes | Existing Kernel contribution/revision contract | stale parent, collision, atomic publish failure | SBW09c2 |
| Persist exact commit outcome and recover ambiguous response | Yes | Yes — durable receipt/recovery owner | response interruption, restart, partial ledger update | SBW09c2 |
| Verify exact committed revision | Yes | No new graph schema; exact outcome semantics | committed-but-unverified | SBW09c2 |
| Workbench publication action | Yes | Product surface contract | UI retry/reload | Successor after backend authority |
| Hermes query/hydration | Yes | Consumer contract | zero/one/many binding | SBW10a |
| Threat projection | Yes | Presentation contract | unresolved/multiple binding | SBW10b |

### Decision

SBW09c is split into two capabilities:

```text
SBW09c1 — exact durable Threat publication proposal
SBW09c2 — proposal-bound governed commit, durable receipt/recovery, and exact verification
```

A separate SBW09c3 is not currently justified. Existing graph-governance code already supplies exact-revision rebuild/projection verification and honest `published` versus verification status. SBW09c2 should adapt those semantics unless reconnaissance during implementation proves a missing public recovery contract.

The split is necessary because a no-write proposal is independently reviewable and usable, while ambiguous commit recovery introduces a distinct durable terminal-state contract. Combining both in one first implementation PR would hide a second ledger/receipt authority and make failure injection too broad to review safely.

## 4. SBW09c1 selected invariant

```text
One exact ready SBW09a publication operation plus one exact active, non-refuse
SBW09b identity resolution can produce and durably reload at most one exact,
deterministic, no-write proposal whose sealed accepted assertions represent only
the intended Threat identity, authored source fields, external statblock resource,
and exact immutable ThreatStatblockBinding against the operation's expected parent;
changed inputs, stale or superseded authority, refusal, collisions, storage failure,
and replay cannot mutate the World Graph or predecessor stores.
```

Create-new effects:

```text
new exact Threat node
+ deterministic authored description / threat-kind / intended-role / tag attributes
+ deterministic external DungeonMind statblock resource node
+ deterministic exact primary ThreatStatblockBinding edge
```

Connect-existing effects:

```text
no Threat node rewrite
+ deterministic external DungeonMind statblock resource node
+ deterministic exact primary ThreatStatblockBinding edge to the reviewed target
```

Refuse never produces a proposal.

## 5. Skeptical review findings carried into the handoff

1. **Do not silently rewrite an existing Threat.** `connect_existing` publishes only the resource and binding. It does not replace label, aliases, kind, role, description, tags, or relationships.
2. **Do not trust a candidate label at proposal time.** The selected target node ID and full candidate snapshot are the authority.
3. **Do not invent a second binding formula.** All external-resource, binding, and edge IDs come from SBW08 helpers.
4. **Do not copy mechanics.** Proposal schemas reject `definition`, rules elements, rendered Markdown, assets, and equivalent mechanics bodies recursively.
5. **Do not call current head a parent.** The proposal package is pinned to SBW09a's exact expected parent. Preparation fails when freshness checks no longer support it; no repin occurs.
6. **Do not treat durable proposal storage as a commit receipt.** SBW09c1 remains no-write. SBW09c2 must introduce and own exact commit recovery explicitly.
7. **Do not let exact replay depend on list order.** Intended roles, tags, and generated attribute effects must be canonicalized deterministically before digest and assertion construction.
8. **Do not let preparation mutate predecessors.** Tests compare SBW09a ledger, SBW09b ledger, ThreatDraft, accepted-mechanics references, and graph head/revision bytes before and after success and failure.
9. **Do not overclaim MAGIC-D3.** SBW09c1 proves only the review/proposal half of publication. Query, hydration, projection, and graph commit remain false.

## 6. Required next sequence

```text
merge this authority repair
→ record the immutable merge SHA
→ start SBW09c1 implementation from that exact main anchor
→ review and merge SBW09c1
→ re-anchor SBW09c2 against the actual proposal ledger and Kernel behavior
→ implement commit / receipt / recovery / exact verification
→ continue immediately to SBW10a and SBW10b
→ dogfood MAGIC-D3
```

Implementation must stop rather than widen scope if the existing sealed-proposal owner cannot represent the exact Threat effect without semantic placeholders, if a generic proposal contract must be introduced, or if safe commit recovery requires changes to Kernel durability not acknowledged by SBW09c2.