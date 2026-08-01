---
# Literal Markdown the worker MUST use as the PR-body skeleton.
# The complete checked-in handoff remains authoritative.
pr_body_template: |
  ## Outcome
  The live-control server can inspect exact revision-pinned Threat candidates and durably record one explicit create-new, connect-existing, or refuse identity resolution for one ready SBW09a publication operation, so later governed publication never derives world identity from a name, rank, or mutable graph state.

  ## Merge-ready invariant
  For one `resolution_id`, the owning SBW09a operation identity, source digest, expected World Graph parent, candidate-query profile, candidate-set digest, exact selected or server-derived Threat identity, operator decision, reason, and supersession lineage round-trip exactly across prepare, decide, reload, replay, and replacement. Candidate ranking is advisory only: no score, label, alias, slug, redirect, or first result becomes durable identity without an explicit typed decision. Changed inputs or candidate sets conflict; stale or terminal publication authority cannot mint a resolution; and this slice performs no DungeonMind, ThreatDraft, accepted-mechanics, or World Graph mutation.

  ## Evidence required to merge
  | Guarantee | Owning boundary | Required evidence | Result |
  |---|---|---|---|
  | Candidate discovery is exact-parent, Threat-only, deterministic, and advisory | candidate service | revision-pinned projection and rank/no-auto-select matrix | Pending implementation evidence; merge blocked until recorded |
  | Create-new cannot bypass exact label/alias collisions | decision service | collision review and deterministic-ID matrix | Pending implementation evidence; merge blocked until recorded |
  | Connect-existing selects one exact visible Threat node | decision service | exact candidate, wrong-kind, redirect, and missing-target matrix | Pending implementation evidence; merge blocked until recorded |
  | Resolution authority is durable, replay-safe, and supersession-safe | identity ledger | restart, replay, concurrency, atomic-failure, and corruption tests | Pending implementation evidence; merge blocked until recorded |
  | SBW09a remains the sole freshness/source/parent authority | predecessor integration | ready/stale/terminal/source-parent mismatch tests | Pending implementation evidence; merge blocked until recorded |
  | Routes expose the typed lifecycle without graph publication or mechanics mutation | FastAPI boundary | route contract and no-mutation proof | Pending implementation evidence; merge blocked until recorded |
  | SBW09a, projection, and SBW08 contracts do not regress | predecessor boundaries | focused regression commands | Pending implementation evidence; merge blocked until recorded |

  ## Scope and explicit deferrals
  Design anchor: `2fa5b7909a28f0c7cf15aab35a56db68ef67ca2e`
  Required implementation base: `178ed6766a847275525a23349d24e77270db97f9`
  Actual base/head: Pre-dispatch; implementation head does not exist yet.
  Actual changed paths: Pre-dispatch documentation synchronization only.
  Paths outside the handoff allowlist: none known; stop and report any discovered path.
  Permitted adjacent predecessor write: only the existing SBW09a refresh transition invoked through its owning service; this PR must not directly edit SBW09a durable files or schema.
  Still false after merge: graph assertion/proposal construction, review preview, confirmation token, World Graph mutation, publication receipt, post-commit verification, Workbench UI, Hermes hydration, Threat projection UI, placement, and combat.

  ## Evidence produced
  ### Automated
  Pending implementation; the exact §13 commands are mandatory.

  ### Adversarial
  Pending implementation; the ordered §6 sequences are mandatory.

  ### Regression
  Pending implementation; SBW09a, projection, and SBW08 regressions are mandatory.

  ### Manual / dogfood
  Not applicable. This slice exposes server-side candidate inspection and durable identity authority; it does not yet create or connect a graph Threat.

  ## Gaps, waivers, and stop conditions
  Pre-dispatch evidence is intentionally pending. No waiver is granted. The implementation PR must replace these pending entries with exact author-local or CI provenance and report every stop condition.
---

# HANDOFF — SBW09b exact Threat identity resolution

**Created:** 2026-07-31.  
**Status:** ACTIVE DESIGN — dispatch exactly one durable create-new / connect-existing / refuse identity-resolution capability after the repository synchronization gate below.  
**Canonical handoff path:** `Docs/Plans/HANDOFF-sbw09b-threat-identity-resolution.md`  
**Repository:** `Drakosfire/DungeonMindBuddy`  
**Design anchor:** `2fa5b7909a28f0c7cf15aab35a56db68ef67ca2e` — merge commit for PR `#462` / SBW09a.  
**Required implementation base:** `178ed6766a847275525a23349d24e77270db97f9` — exact authority-sync commit, or a later deliberate authority-sync commit.  
**Suggested branch:** `feat/sbw09b-threat-identity-resolution`

No future pull-request number is assigned by this handoff. The hosting system or operator may assign one when a pull request is actually opened.

> **Predecessor gate:** PR `#462` merged SBW09a. The live-control server now owns one durable publication operation containing an immutable mechanics-saved ThreatDraft source snapshot, exact accepted-mechanics locator, exact expected World Graph parent, replay identity, and ready/stale/cancelled/superseded lifecycle. Consume that authority; do not reconstruct it.
>
> **Dispatch boundary:** this slice discovers possible existing Threats and records exactly one explicit identity decision. It does not construct graph assertions, prepare a Graph Review proposal, mint a confirmation token, create a Threat node, connect a binding, commit a World Graph revision, or add Workbench controls.
>
> **Architecture warning:** the Graph Kernel already has extraction/reconciliation identity models and an internal durable identity-decision store. Those records govern graph extraction, alias, merge, split, and rebuild behavior. An application-level pre-publication choice must not write that store, import its internal persistence module, or pretend the chosen Threat exists before SBW09c publishes it.

## §0 Repository synchronization gate

At design anchor `2fa5b7909a28f0c7cf15aab35a56db68ef67ca2e`, SBW09a is merged, but the active tracker and roadmap still describe SBW09a as the immediate dispatch authority. Before implementation dispatch:

1. add this handoff at `Docs/Plans/HANDOFF-sbw09b-threat-identity-resolution.md`;
2. mark `Docs/Plans/HANDOFF-sbw09a-publication-operation-ledger.md` complete / merged in PR `#462` without rewriting its frozen contract;
3. update `Docs/Plans/PR-TRACKER-threat-statblock-authoring-projection.md` so:
   - latest merged workstream PR is `#462`;
   - SBW09a is `MERGED #462`;
   - SBW09b is the active immediate authority;
   - the immediate dispatch sequence begins with SBW09b;
4. update `Docs/Roadmaps/ROADMAP-threat-statblock-authoring-projection.md` so:
   - durable publication-operation authority is current truth rather than a gap;
   - SBW09a is recorded as proven;
   - this handoff is the current implementation authority;
5. update the current-dispatch sequence in the superseded bundled SBW09 handoff to link this exact unnumbered file while preserving its historical status;
6. use the immutable main SHA `178ed6766a847275525a23349d24e77270db97f9` recorded in this handoff as the implementation base;
7. dispatch the implementation worker from that exact SHA.

Do not combine the synchronization edits with implementation unless repository process explicitly requires the handoff file to travel on the implementation branch. If unrelated PRs move main, re-anchor only when they change SBW09a contracts, World Graph projection/retrieval behavior, Threat node vocabulary, route registration, or lock assumptions used below.

## §1 Capability decomposition decision

| Candidate outcome | Independently useful? | Public/durable contract changed? | User/operator surface changed? | Failure model changed? | Independently testable/revertible? | Decision |
|---|---:|---:|---:|---:|---:|---|
| Exact-parent candidate inspection | Yes | Yes, read contract | Server API only | Yes | Yes | Include as preparation for the same identity decision |
| Durable create-new / connect-existing / refuse decision | Yes | Yes | Server API only | Yes | Yes | Include |
| Graph Threat assertion construction | Yes | Yes | Later review surface | Yes | Yes | Successor: SBW09c |
| Graph proposal, preview, confirmation token | Yes | Yes | Review surface | Yes | Yes | Successor: SBW09c |
| World Graph commit and exact verification | Yes | Yes | Publication result | Yes | Yes | Successor: SBW09c |
| Workbench create/connect controls | Yes | No new authority by itself | Yes | Yes | Yes | Successor after server publication |
| Generic identity framework for every object kind | No, before a second proving domain | Broad | Broad | Broad | Broad | Explicitly exclude |

**Selected capability:** exact candidate inspection plus durable explicit Threat identity resolution attached to one ready SBW09a operation.

**Why these paths share one invariant:** candidate preparation defines the exact finite review set and its digest; the decision binds one explicit create/connect/refuse choice to that reviewed set. Without the candidate digest, connect authority can silently drift. Without the durable decision, candidate ranking can be mistaken for identity authority.

**Mission falsification test:** this ceases to be one slice if implementation must define graph assertions, Graph Review effects, proposal tokens, commit receipts, post-commit verification, UI review state, or a general object-identity framework.

## §2 Mission and merge-ready invariant

The live-control server can inspect exact revision-pinned Threat candidates and durably record one explicit create-new, connect-existing, or refuse identity resolution for one ready SBW09a publication operation, so later governed publication never derives world identity from a name, rank, or mutable graph state.

**Merge-ready invariant**

For one `resolution_id`, the owning SBW09a operation identity, source digest,
expected World Graph parent, candidate-query profile, candidate-set digest,
exact selected or server-derived Threat identity, operator decision, reason,
and supersession lineage round-trip exactly across prepare, decide, reload,
replay, and replacement.

Candidate ranking is advisory only. No score, label, alias, slug, redirect,
or first result becomes durable identity without an explicit typed decision.

Changed inputs or candidate sets conflict. Stale, cancelled, or superseded
publication authority cannot mint a resolution. This slice performs no
DungeonMind, ThreatDraft, accepted-mechanics, or World Graph mutation.

The only permitted adjacent predecessor mutation is invoking SBW09a's existing
refresh transition through its owning service, which may monotonically mark
the publication operation stale. This slice must not edit SBW09a durable files
or schema directly.

## §3 Context, authority, and boundaries

| Field | Required content | Parent authority |
|---|---|---|
| Parent authority | Grounded authored-object lifecycle decision, active Threat/statblock roadmap, and tracker | `Docs/Design/DECISION-grounded-authored-world-object-lifecycle.md` |
| Predecessor implementation | Merged PR `#462`, especially `ThreatPublicationOperationV1`, immutable source snapshot, expected parent, refresh/read behavior, and publication ledger | SBW09a models/services/routes |
| World read authority | Revision-pinned World Graph projection through the public Kernel / live-control projection service | `apps/live_control_server/services/world_graph_projection.py` |
| Threat vocabulary | Projectable World Graph node with `kind.casefold() == "threat"` | World Graph projection |
| Ranking precedent | Existing deterministic `rank_search_node_matches`; advisory ordering only | `src/graph_memory/projection/world_projection.py` |
| Internal identity precedent | Kernel `IdentityCandidate` / `IdentityResolution` vocabulary may inform naming, but the internal identity-decision store is not an app write boundary | `src/graph_memory/kernel/identity_models.py` |
| Exact input consumed | Route draft/operation IDs; ready SBW09a operation; immutable source snapshot/digest; exact expected graph parent; optional bounded query; explicit typed operator decision | SBW09a + typed requests |
| Named successor | SBW09c reviewed effects, proposal-bound confirmation, immutable commit, and exact verification | Roadmap |
| Explicit non-goals | LLM matching, vector search, corpus fallback, graph writes, merge/split/alias decisions, DMS calls, ThreatDraft mutation, UI, Hermes, placement, combat | This handoff |

Read authoritative inputs in order before changing code:

1. `AGENTS.md`, `.cursor/rules/external-agent-pr-loop.mdc`, and the external-agent PR loop skill.
2. `Docs/Design/DECISION-grounded-authored-world-object-lifecycle.md`.
3. synchronized `Docs/Plans/PR-TRACKER-threat-statblock-authoring-projection.md`.
4. synchronized `Docs/Roadmaps/ROADMAP-threat-statblock-authoring-projection.md`.
5. completed `Docs/Plans/HANDOFF-sbw09a-publication-operation-ledger.md`.
6. `apps/live_control_server/models/threat_publication.py`.
7. `apps/live_control_server/services/threat_publication_operations.py`.
8. `apps/live_control_server/routes/threat_publication.py`.
9. `src/graph_memory/projection/world_projection.py` and `src/graph_memory/kernel/world_projection.py`.
10. `apps/live_control_server/services/world_graph_projection.py`.
11. `src/graph_memory/union_supergraph/model.py` and SBW08 statblock-binding contracts/tests.
12. `src/graph_memory/kernel/identity_models.py` only as vocabulary precedent.
13. `src/graph_memory/world_supergraph/identity_decision_store.py` only to preserve its “apps must not import” boundary.
14. current `apps/live_control_server/main.py` route registration.

**Authority precedence:**

```text
repository rules
→ grounded authored-world-object lifecycle decision
→ synchronized publication-first tracker/roadmap
→ this SBW09b handoff
→ merged SBW09a operation authority
→ revision-pinned World Graph projection
→ merged SBW08 binding contract
→ existing ranking/identity vocabulary precedents
→ superseded bundled SBW09 design
→ chat or local summaries
```

## §4 Shared vocabulary

| Term | Definition |
|---|---|
| Publication operation | The exact ready SBW09a authority being resolved. Its source snapshot and expected parent are immutable. |
| Identity candidate | One exact projectable Threat node from the operation's expected parent revision, presented for review with advisory matching metadata. It is not selected merely by appearing in the set. |
| Candidate query | The bounded text used to rank visible Threats. If omitted, the immutable source name is used. |
| Matching profile | The frozen deterministic matching rules and version included in candidate-set identity. Initial value: `dmb_threat_identity_match_v1`. |
| Exact-name collision | NFKC-normalized, trimmed, internal-whitespace-collapsed, case-folded equality between the source name and a candidate label or alias. Punctuation is not discarded. |
| Candidate-set digest | SHA-256 over operation identity, matching profile, query, exact parent, source digest, complete ordered candidate snapshots, and truncation/count metadata. |
| Create new | Explicit operator decision that SBW09c should propose one deterministic new Threat node identity. No node exists yet. |
| Connect existing | Explicit operator decision that SBW09c should bind publication effects to one exact candidate Threat node ID. |
| Refuse | Explicit operator decision to stop identity resolution without producing a Threat identity usable by SBW09c. |
| Deterministic proposed Threat ID | Server-derived future node ID based on world, campaign, draft, and SBW09a operation identity—not display name or slug. It is proposal input, not proof a graph node exists. |
| Active resolution | The one non-superseded identity resolution currently attached to the publication operation. |
| Historical resolution | A superseded immutable decision retained for audit/replay. |
| Usable resolution | Active create-new or connect-existing resolution whose SBW09a operation remains ready and whose exact parent is still current when a successor consumes it. Read alone does not assert usability forever. |

## §5 Observable-path inventory

| Observable path | Current behavior | Required behavior | Same invariant? | Owning boundary |
|---|---|---|---:|---|
| Prepare candidates for ready operation | No contract | Refresh predecessor; load exact expected-parent projection; return deterministic Threat-only candidate set + digest | Yes | candidate service |
| Prepare after source/head drift | No identity contract | Existing SBW09a refresh may mark stale; return operation-not-ready; write no identity ledger | Yes | predecessor integration |
| Prepare from cancelled/superseded operation | No contract | Return exact terminal/not-ready result; do not inspect candidates | Yes | candidate service |
| Candidate ranking | Existing ranker exists for search | Reuse deterministic scores/reasons only for ordering; never choose identity | Yes | candidate service |
| Exact source-name collision | No publication rule | Surface all exact label/alias collisions even when query would not rank them | Yes | candidate service |
| Candidate overflow/truncation | No contract | Never omit exact collisions silently; bounded advisory results; typed overflow/integrity behavior | Yes | candidate service |
| Decide create-new | No contract | Require reviewed candidate digest and explicit rejection of every exact-name collision; derive deterministic proposed node ID | Yes | decision service |
| Decide connect-existing | No contract | Require one exact candidate node ID of kind Threat; preserve its snapshot; no redirect/name fallback | Yes | decision service |
| Decide refuse | No contract | Persist explicit terminal refusal with reason; no usable target identity | Yes | decision service |
| Exact decision replay | No contract | Same resolution ID + exact request returns durable record before predecessor/graph reads | Yes | identity ledger |
| Resolution ID reused with changed input | No contract | Typed conflict; existing record unchanged | Yes | ledger/service |
| Competing first decisions | No contract | Exactly one active resolution; loser gets busy/conflict | Yes | identity ledger |
| Replace an active decision | No contract | Explicit new ID + `supersedes_resolution_id`; old/new links and active pointer change in one atomic replacement | Yes | identity ledger |
| Read after restart | No contract | Exact candidate snapshot, digests, decision, identity, and lineage reload | Yes | identity ledger |
| Read after predecessor later becomes stale | No contract | Return immutable record plus predecessor-usability status; do not rewrite history | Yes | read service |
| Corrupt identity ledger | No contract | Fail closed; never auto-repair or overwrite opportunistically | Yes | parser/store |
| Downstream SBW09c use | Could reconstruct/guess identity | Consume exact active resolution plus exact ready operation; no fallback | Yes | durable public contract |

## §6 Ordered adversarial sequences

| Sequence | Required safe outcome | Owning proof |
|---|---|---|
| Prepare operation pinned to parent A; current head is B | SBW09a refresh returns stale/not-ready; no candidate set usable for decision | predecessor-drift integration |
| Prepare exact parent A; graph has a better-scoring non-Threat node | Non-Threat is excluded; no auto-selection | filter/rank test |
| Source name exactly equals a low-ranked alias while query is unrelated | Collision candidate is still present and marked exact collision | collision-union test |
| Candidate A scores 1000, candidate B scores 900 | Response orders A first, but neither becomes selected or durable | advisory-only test |
| Create-new with one exact collision not explicitly rejected | Review-required conflict; no record | collision-review test |
| Create-new after explicitly rejecting all exact collisions | Deterministic proposed ID recorded, provided it does not already exist | create-new test |
| Derived proposed ID already exists in exact parent | New-ID collision; never append random suffix or silently connect | collision test |
| Connect by label/alias but omit exact node ID | Validation failure; no name lookup fallback | request-contract test |
| Connect to candidate ID that is NPC/location/non-Threat | Target-invalid; no record | wrong-kind test |
| Connect to merged-away ID whose redirect points to a Threat | Target-invalid/not-found unless exact selected projectable node itself is in reviewed set; no redirect following | redirect test |
| Prepare candidate set; graph bytes at pinned revision are tampered | Projection integrity failure; typed graph failure; no resolution | integrity test |
| Prepare digest D1; submit decision after request/profile/result changes to D2 | Candidate-set-changed conflict; no resolution | digest race test |
| Exact same resolution replay after head advances | Return existing durable resolution before refresh/graph reads | replay test |
| Same resolution ID with changed actor/reason/query/decision/target | Input conflict; existing record unchanged | request-digest test |
| Two first decisions race | One active resolution; loser busy/conflict | concurrency test |
| Active connect decision explicitly superseded by create-new while another replace races | One coherent active winner; bidirectional acyclic lineage | supersession race test |
| Atomic write fails during supersession | Prior ledger remains byte-identical; old active resolution remains authoritative | injected failure test |
| Predecessor source digest/parent differs from persisted identity ledger | Integrity/predecessor mismatch; never rebind ledger | cross-authority tamper test |
| Any prepare/decide/read/supersede path | No graph revision, ThreatDraft, accepted mechanics, or DMS state changes; only identity ledger plus permitted SBW09a refresh transition | no-mutation proof |

## §7 Files in scope — allowlist

| Action | Path | Purpose |
|---|---|---|
| Create | `apps/live_control_server/models/threat_publication_identity.py` | Strict candidate, request, resolution, ledger, digest, state, and response contracts |
| Create | `apps/live_control_server/services/threat_publication_identity.py` | Candidate preparation, exact-parent projection, deterministic matching, create/connect/refuse orchestration, lock order, and atomic persistence |
| Create | `apps/live_control_server/routes/threat_publication_identity.py` | Typed prepare/decide/read API under the existing publication-operation namespace |
| Modify | `apps/live_control_server/main.py` | Mount only the focused router |
| Create | `tests/test_threat_publication_identity.py` | Candidate, digest, decision, replay, supersession, concurrency, corruption, and no-mutation proof |
| Create | `tests/test_threat_publication_identity_routes.py` | Exact route schemas, status mapping, restart/replay, and route no-write proof |

**Bounded discovery exception**

Directories: `apps/live_control_server/`, `tests/`  
Maximum additional paths: `3`  
Allowed path kinds:

- an existing shared test fixture/helper;
- a package export;
- an existing route-registration test;
- a minimal read-only public adapter already owning exact projection access.

The path must already own the exact behavior this slice consumes. It may not
add graph mutation, new matching semantics, or a second identity store.
Prefer calling public `read_publication_operation` / `refresh_publication_operation`
and the existing projection service rather than modifying predecessor modules.
If a new predecessor helper is genuinely required, stop and report the exact
contract gap before adding it.

## §8 Files and capabilities explicitly out of scope

Do not modify:

- `apps/live_control_server/models/threat_publication.py`;
- SBW09a ledger schema or durable records;
- `apps/live_control_server/models/threat_draft.py`;
- accepted-mechanics models/store;
- DungeonMind client, OpenAPI, or mechanics payloads;
- `src/graph_memory/world_supergraph/identity_decision_store.py`;
- Graph Kernel identity models merely to fit this app workflow;
- World Graph contribution, proposal, commit, revision, or projection contracts;
- SBW08 external-resource / binding contracts;
- live-control UI or generated clients;
- Hermes tools;
- documents, placements, maps, scenes, or combat.

Do not add:

- automatic identity selection;
- fuzzy/semantic/LLM merge authority;
- vector or corpus search fallback;
- redirect following as selection;
- “use current head” fallback;
- direct graph-file writes;
- a generic authored-object identity framework;
- create/connect graph effects;
- proposal/confirm/commit endpoints;
- a route that accepts caller-supplied source snapshot, accepted mechanics locator, candidate snapshot, or proposed new node ID.

## §9 Public contract

### 9.1 Routes

```text
POST /api/live/threat-drafts/{draft_id}/publication-operations/{operation_id}/identity-candidates/prepare
POST /api/live/threat-drafts/{draft_id}/publication-operations/{operation_id}/identity-resolutions
GET  /api/live/threat-drafts/{draft_id}/publication-operations/{operation_id}/identity-resolutions/{resolution_id}
```

No aliases. No GET with freshness side effects. No endpoint that writes graph state.

### 9.2 Candidate preparation request

```text
PrepareThreatIdentityCandidatesRequestV1:
  schema: dmb_prepare_threat_identity_candidates_request_v1
  query_text?
```

`query_text` is optional, trimmed, nonblank when supplied, and bounded to 500
characters. Candidate result bounds are server-owned. The client must not
supply a candidate set, score, exact-collision flag, graph revision, source
digest, target node, or matching profile.

### 9.3 Matching profile

Initial profile: `dmb_threat_identity_match_v1`.

Exact collision normalization:

```text
Unicode NFKC
→ trim leading/trailing whitespace
→ collapse internal Unicode whitespace to one ASCII space
→ casefold
```

Punctuation is not discarded. Do not stem, singularize, remove articles, or
resolve aliases through global alias-map ownership.

Advisory ranking reuses deterministic `rank_search_node_matches` over the
exact revision-pinned projection, after filtering to `kind.casefold() == "threat"`.
Preserve deterministic score and reasons. Tie-break by exact `node_id`. Score
participates in candidate-set identity only through the snapshot/digest; it
never selects a target.

Candidate composition:

- load all projectable campaign-visible Threat nodes from the exact expected parent;
- compute every exact source-name collision across label and aliases;
- return every exact collision without truncation, then highest-ranked non-collisions;
- suggested advisory candidates: `12`;
- maximum total candidates: `32`;
- if exact collisions alone exceed the maximum, return typed candidate-overflow
  and forbid decision rather than hiding collisions.

### 9.4 Candidate snapshot

```text
ThreatIdentityCandidateV1:
  node_id
  label
  kind
  role
  aliases[]
  campaign_scope?
  summary?
  source_domains[]
  binding_ids[]
  has_exact_accepted_binding
  match_score
  match_reasons[]
  exact_name_collision
```

Build only from the exact revision-pinned typed World Graph projection. `kind`
must be Threat. `binding_ids` and `has_exact_accepted_binding` are advisory
facts derived from typed SBW08 relationship projections; mechanics are never
copied. Sort source domains, binding IDs, and match reasons deterministically.
The node ID is the only connect-existing identity authority.

### 9.5 Candidate response and digest

```text
ThreatIdentityCandidateSetV1:
  schema: dmb_threat_identity_candidate_set_v1
  draft_id
  operation_id
  source_digest
  expected_parent_revision_id
  matching_profile
  candidate_query
  eligible_threat_count
  exact_collision_count
  truncated
  candidates[]
  candidate_set_digest
```

The digest payload includes every field above except the digest itself. Serialize
sorted keys, compact separators, UTF-8, and SHA-256. Recompute and verify it
whenever a durable resolution containing the candidate set is loaded.

### 9.6 Decision request

```text
CreateThreatIdentityResolutionRequestV1:
  schema: dmb_create_threat_identity_resolution_request_v1
  resolution_id
  matching_profile
  candidate_query
  candidate_set_digest
  decision: create_new | connect_existing | refuse
  target_node_id?
  rejected_candidate_node_ids[]
  actor
  reason
  supersedes_resolution_id?
```

Strict rules:

- `create_new`: target is null, reason is nonblank, every exact collision is
  explicitly rejected, rejected IDs are unique members of the candidate set.
- `connect_existing`: target is required and exactly one snapshotted candidate
  of kind Threat; no redirect/name lookup; target is not rejected.
- `refuse`: target is null, reason is nonblank, and no created node exists.
- with no active resolution, supersession is null;
- with an active resolution, a new decision names exactly that active resolution;
- same resolution ID is replay or conflict, never supersession.

### 9.7 Deterministic proposed Threat ID

The caller must not supply a new node ID. For `create_new`, derive:

```text
seed =
  "dmb_threat_identity_v1"
  + NUL + world_id
  + NUL + campaign_id
  + NUL + draft_id
  + NUL + operation_id

created_node_id =
  "threat:authored:" + first_32_lowercase_hex(sha256(seed))
```

The ID is stable for the same publication operation, independent of display
name, slug, rank, or candidate ordering, and is proposal input rather than
proof a node exists. Collision with any node at the exact expected parent
fails closed as `publication_identity_new_id_collision`; never add a suffix or
silently connect.

### 9.8 Durable resolution model

```text
ThreatPublicationIdentityResolutionV1:
  schema: dmb_threat_publication_identity_resolution_v1
  resolution_id
  draft_id
  operation_id
  source_digest
  expected_parent_revision_id
  matching_profile
  candidate_query
  candidate_set
  candidate_set_digest
  request_digest
  decision: create_new | connect_existing | refuse
  selected_target?
  created_node_id?
  rejected_candidate_node_ids[]
  actor
  reason
  state: active | superseded
  supersedes_resolution_id?
  superseded_by_resolution_id?
  created_at
  updated_at
```

Unknown fields reject. IDs are bounded and traversal-safe. Route draft/operation
IDs participate in `request_digest`. Candidate/request digests recompute on
load. Candidate IDs are unique. The selected target equals one complete
snapshotted candidate. Create-new has only the deterministic created ID;
connect-existing has only the selected target; refuse has neither. Rejected
IDs are unique members of the candidate set and exclude the selected target.
Immutable identity fields never change after creation. Timestamps are audit
metadata. Superseded records require exact forward links; active records have
no forward link.

### 9.9 Identity ledger

```text
ThreatPublicationIdentityLedgerV1:
  schema: dmb_threat_publication_identity_ledger_v1
  draft_id
  operation_id
  source_digest
  expected_parent_revision_id
  active_resolution_id?
  resolutions[]
```

Storage:

```text
out/threat_publication_identity/<draft_id>/<operation_id>/ledger.json
out/threat_publication_identity/<draft_id>/<operation_id>/.identity.lock
```

Maximum 16 resolutions. Embedded draft/operation/source/parent identities
must exactly match every resolution. IDs are unique. The active pointer is null
or identifies exactly one active resolution; all others are superseded.
Supersession links are bidirectional, acyclic, and local to this ledger.
Candidate and request digests validate on every load. Duplicate IDs, impossible
decisions, bad targets, bad digests, broken links, unknown schemas, malformed
JSON, path mismatch, and over-bound history fail closed. Corruption is never
auto-repaired or overwritten by decide.

### 9.10 Response envelope and labels

```text
ThreatPublicationIdentityResponseV1:
  schema: dmb_threat_publication_identity_response_v1
  draft_id
  operation_id
  result_label
  candidate_set?
  resolution?
  predecessor_state?
  predecessor_usable
  message?
```

Closed labels:

```text
publication_identity_candidates_ready
publication_identity_created_new
publication_identity_connected_existing
publication_identity_refused
publication_identity_superseded
publication_identity_operation_not_ready
publication_identity_candidate_overflow
publication_identity_candidate_set_changed
publication_identity_review_required
publication_identity_target_not_found
publication_identity_target_invalid
publication_identity_new_id_collision
publication_identity_busy
publication_identity_input_conflict
publication_identity_history_full
publication_identity_not_found
publication_identity_graph_unavailable
publication_identity_storage_unavailable
publication_identity_integrity_failure
```

### 9.11 HTTP behavior

| Outcome | Status |
|---|---:|
| Candidate prepare success | 200 |
| New first or superseding resolution | 201 |
| Exact replay or read | 200 |
| Draft / operation / resolution / target missing | 404 |
| Not-ready, busy, changed candidate set, review required, target invalid, ID collision, input conflict, history full | 409 |
| Invalid ID or strict request | 422 |
| Graph or predecessor dependency temporarily unavailable; identity storage unavailable | 503 |
| Corrupt identity ledger or impossible persisted invariant | 500 |

The typed response body is authoritative; status code alone is insufficient proof.

## §10 Lifecycle behavior

**Prepare candidates**

1. Validate route IDs and typed request.
2. Invoke the existing SBW09a refresh operation through its owning service.
3. Require result `publication_ready`; otherwise return operation-not-ready
   with no identity-ledger write.
4. Use only the immutable source snapshot and exact expected parent.
5. Call the existing World Graph projection boundary with the same world,
   campaign, GM admissibility, `revision_pin=expected_parent_revision_id`, and
   campaign scope.
6. Require projection revision, head, and `is_head` all equal the expected parent.
7. Build the exact Threat-only candidate set using the frozen profile.
8. Return the typed candidate set and digest; write no identity ledger.

The projection may race with a later graph-head move after response. A later
decision recomputes against the same exact parent and requires SBW09a still ready.

**Decide**

1. Validate route IDs and typed request.
2. Acquire the identity-resolution lock.
3. Strictly load and validate the identity ledger, or construct an empty ledger
   from the exact predecessor identity.
4. If `resolution_id` already exists, an exact request digest returns the
   existing durable record before predecessor/graph reads; changed input conflicts.
5. Enforce the active-slot / explicit-supersession rules.
6. Refresh SBW09a through its owning service and require ready.
7. Require predecessor draft/operation/source/parent identities equal ledger identities.
8. Recompute the exact candidate set and require candidate-set digest equality.
9. Apply decision-specific validation and derive/check the create-new ID where needed.
10. Atomically replace the ledger, linking old/new records for supersession.

**Read**

Validate route IDs, acquire the identity lock, strictly load the ledger and
resolution, and return the immutable record. Read predecessor operation only
to report current `predecessor_state` / `predecessor_usable`. Do not refresh
candidates or mutate predecessor, graph, or identity ledger.

## §11 Lock, commit, replay, and failure contract

Lock order:

```text
identity-resolution lock
→ SBW09a publication-operation lock via public read/refresh service
→ exact World Graph projection/read locks
```

No SBW09a or graph path may call back into the identity service while holding
its lock. Candidate prepare has no identity-ledger lock because it writes no
identity authority. Decide and read use the identity lock.

Commit point: atomic replacement of one `ThreatPublicationIdentityLedgerV1`.
Before commit no identity resolution exists or the prior active resolution
remains authoritative. After commit exact reviewed candidates, decision,
target/proposed identity, and lineage survive restart.

Failure behavior:

```text
publication operation missing/unavailable -> no identity write
publication operation stale/cancelled/superseded -> no identity write
source or parent mismatch -> no identity write
candidate projection unavailable/integrity failure -> no identity write
candidate digest changed -> no identity write
create-new unresolved exact collision -> no identity write
connect target absent/wrong kind/unreviewed -> no identity write
derived new node ID collision -> no identity write
same ID changed request -> existing record unchanged
active slot without explicit supersession -> existing record unchanged
history full -> existing record unchanged
ledger corruption -> fail closed; never auto-repair
atomic write failure -> prior ledger remains authoritative
```

## §12 Identity, fallback, persistence, and predecessor matrices

### Identity matrix

| Identity | Rule | Ambiguity behavior | Fallback? |
|---|---|---|---|
| Publication operation | Exact route operation ID and durable SBW09a record | Missing/not-ready rejects | No |
| Source | Exact immutable source digest/snapshot | Mismatch is integrity/predecessor conflict | No |
| Graph parent | Exact SBW09a expected parent and current head at prepare/decide | Head drift makes predecessor not ready | No |
| Candidate | Exact node ID + complete reviewed snapshot at exact parent | Candidate-set digest mismatch conflicts | No |
| Connect target | Exact reviewed projectable Threat node ID | Wrong kind/missing/redirect rejects | No |
| Proposed new Threat | Deterministic server-derived ID | Existing ID collision rejects | No random suffix |
| Display name | Review/collision signal only | Exact collisions require explicit rejection | Never durable identity |
| Rank/score | Advisory ordering only | Ties deterministic | Never selection |
| Resolution | Exact validated resolution ID + request digest | Reuse with changed request conflicts | No |
| Supersession | Exact old/new IDs and bidirectional links | Wrong active predecessor conflicts | No |

### Fallback matrix

No fallback is permitted to current/latest graph head; mutable ThreatDraft
fields; another SBW09a operation; label, alias, slug, display name, or first
result; identity redirect target; generic alias-map ownership; vector/corpus/
repository/LLM/external search; internal extraction identity records; random
node suffix; existing binding as implicit connect authority; or a prior
candidate set with a different digest/profile/query.

### Persistence matrix

| Operation | Durable representation | Round-trip guarantee | Replay behavior | Migration rule |
|---|---|---|---|---|
| Prepare | None; typed response only | Deterministic from exact operation + parent | Repeat recomputes | Profile change creates a new profile value |
| First decision | Identity ledger | Exact candidate set/digest/decision/identity | Same ID/body exact record | Strict v1 |
| Refuse | Identity ledger | Explicit no-target decision | Same ID/body exact record | No implicit reopen |
| Supersede | Same ledger, linked old/new | Old/new links + active pointer exact | Same new ID/body exact new record | No in-place decision rewrite |
| Read | Strict ledger parser | Every digest/invariant rechecked | Read-only | Operator repair is separate tooling |

### Predecessor-to-consumer mapping

| Predecessor | Real shape | SBW09b use | Transformation | Required proof |
|---|---|---|---|---|
| SBW09a draft/operation IDs | Exact validated IDs | Ledger ownership | Exact copy | Round-trip test |
| SBW09a source snapshot | Immutable typed publication source | Candidate query context | Read-only; name for default query | Real typed fixture |
| SBW09a source digest | Canonical SHA-256 | Cross-authority binding | Exact copy | Tamper test |
| SBW09a expected parent | Revision ID | Projection pin | Exact equality | Drift/race test |
| SBW09a lifecycle | ready/stale/cancelled/superseded | Decision eligibility | Existing refresh/read service | Negative matrix |
| World projection node | Typed node ID/label/kind/role/aliases | Candidate snapshot | Threat filter, exact copy + advisory score | Canonical graph fixture |
| World projection relationships | Typed SBW08 binding views | Advisory binding facts | IDs/exact-locator comparison only | Mapping test |
| Existing ranker | Deterministic ranked matches | Candidate ordering | Reuse; never auto-select | Score/no-selection test |
| Internal identity models/store | Extraction/reconciliation authority | Vocabulary precedent only | No import/write | Boundary inspection test |
| SBW08 exact locator/binding | Six-field mechanics identity | Binding advisory facts | Equality only | Compatibility test |

Invented fixtures that bypass canonical SBW09a models, World Graph projection,
actual Threat nodes, or SBW08 bindings do not prove the boundary.

## §13 Evidence required to merge

| Guarantee | Owning boundary | Evidence | Expected result | Stop condition |
|---|---|---|---|---|
| Candidate set is exact-parent and Threat-only | candidate service | Real revision-pinned graph with mixed kinds | Only visible Threats; expected parent exact | Any latest/head fallback |
| Ranking remains advisory | candidate service | Highest-score and tie tests | Ordering only; no selected identity | Any implicit target |
| Exact collisions cannot be hidden | matching profile | Unrelated query + exact alias collision | Every collision included | Truncated collision |
| Create-new requires collision adjudication | decision service | Missing/all explicit rejection matrix | Review-required or durable proposed ID | Silent duplicate |
| Proposed ID is deterministic and name/slug independent | decision service | Formula + collision tests | Stable exact ID or fail closed | Random suffix |
| Connect selects exact reviewed Threat | decision service | Exact candidate, missing, wrong-kind, redirect matrix | One exact node or typed reject | Name/redirect fallback |
| Candidate digest binds review | model/service | Query/profile/order/snapshot tamper matrix | Mismatch conflicts | Recomputed hidden authority |
| Replay is dependency-independent | ledger/service | Same-ID replay after graph drift/corruption | Existing exact record returned | Graph reread on replay |
| One active decision and atomic replacement | ledger | Concurrency, supersession, injected write failure | One active lineage or prior ledger | Dual active/orphan |
| Persistence fails closed | parser/store | Malformed JSON/schema/digest/link/history/path tests | Typed integrity, byte-identical storage | Auto-repair |
| SBW09a owns freshness | integration | Stale/terminal/source-parent mismatch tests | No identity record minted | Duplicate freshness model |
| External authorities stay untouched | service + route | Byte hashes/spies | No graph/Draft/mechanics/DMS mutation | Any forbidden write |
| Route contract is strict and reloadable | FastAPI | Route integration + new app instance | Typed statuses + exact reload | Opaque failure |
| Predecessor contracts remain green | predecessor boundaries | Focused regressions | No unexplained regression | Unwaived failure |

Required test names or exact equivalents:

```text
test_prepare_uses_exact_expected_parent_and_threat_only_candidates
test_prepare_refreshes_and_rejects_stale_publication_operation
test_prepare_surfaces_exact_alias_collision_despite_unrelated_query
test_candidate_rank_never_selects_identity
test_create_new_requires_explicit_rejection_of_every_exact_collision
test_create_new_derives_stable_name_independent_proposed_threat_id
test_create_new_rejects_existing_derived_id_without_random_suffix
test_connect_existing_requires_exact_reviewed_threat_node
test_connect_existing_rejects_wrong_kind_redirect_and_name_fallback
test_decision_rejects_changed_candidate_set_digest_without_mutation
test_resolution_exact_replay_does_not_read_predecessor_or_graph
test_resolution_same_id_changed_request_conflicts
test_one_active_resolution_requires_explicit_supersession
test_supersession_atomically_links_old_new_and_active_pointer
test_concurrent_first_decisions_have_one_coherent_winner
test_concurrent_supersessions_have_one_coherent_winner
test_atomic_identity_write_failure_preserves_prior_ledger
test_corrupt_identity_ledger_fails_closed_without_rewrite
test_identity_ledger_rejects_predecessor_source_or_parent_mismatch
test_identity_routes_preserve_exact_restart_reload
test_identity_flow_leaves_graph_draft_mechanics_and_dms_unchanged
```

Required commands:

```bash
uv run pytest -q \
  tests/test_threat_publication_identity.py \
  tests/test_threat_publication_identity_routes.py

uv run pytest -q \
  tests/test_threat_publication_operations.py \
  tests/test_threat_publication_routes.py

uv run pytest -q \
  tests/test_world_graph_projection_service.py \
  tests/test_graph_kernel_world_projection.py \
  tests/test_statblock_binding_graph_contract.py

uv run ruff check \
  apps/live_control_server/models/threat_publication_identity.py \
  apps/live_control_server/services/threat_publication_identity.py \
  apps/live_control_server/routes/threat_publication_identity.py \
  apps/live_control_server/main.py \
  tests/test_threat_publication_identity.py \
  tests/test_threat_publication_identity_routes.py

uv run python -m compileall -q \
  apps/live_control_server/models/threat_publication_identity.py \
  apps/live_control_server/services/threat_publication_identity.py \
  apps/live_control_server/routes/threat_publication_identity.py

git diff --check
git diff --name-only 178ed6766a847275525a23349d24e77270db97f9...HEAD
```

For every required command failure that also occurs on base, run the identical
command on base and head, record exact output and provenance, do not call the
gate green, and obtain/name an explicit operator waiver if the failure remains.
Author-local test output must be labeled author-local when no CI run/check is attached.

## §14 PR description and handback requirements

The implementation PR body must include the §2 mission and invariant verbatim;
each §13 guarantee, owning boundary, produced result, and provenance; required
base and actual GitHub base/head SHAs; exact changed paths and diff stat;
every required command and exact result; base/head comparison for failures;
explicit waivers or none; paths outside §7 or none; stop conditions and
resolution; confirmation of no graph proposal/commit, DMS call, ThreatDraft
write, accepted-mechanics write, or direct SBW09a ledger mutation; confirmation
that any SBW09a stale transition came only through its existing refresh service;
confirmation that the internal Graph Kernel identity-decision store was not
imported or written; confirmation that rank/name/alias/slug/redirect/first
result never auto-select identity; confirmation that SBW09c remains
unimplemented; and confirmation that the complete matrices were followed.

**Required demolition declaration**

```text
Replaced path:
  ad hoc create/connect identity inferred later from current ThreatDraft,
  current graph head, display name, or first-ranked graph result

Deleted in this PR:
  no

If no, retained reason:
  no existing product SBW09b identity-resolution authority exists to delete;
  graph extraction identity decisions remain valid for their separate consumers

Named remaining consumer:
  Graph Kernel extraction/reconciliation and generic graph authoring flows

Required deletion owner:
  SBW09c must reject or remove any temporary publication bypass that constructs
  Threat identity without an active SBW09b resolution
```

## §15 Acceptance rubric

- [ ] Exactly one independently useful capability was delivered: exact candidate inspection plus durable explicit Threat identity resolution.
- [ ] The implementation consumes the merged SBW09a operation rather than rebuilding mutable source/parent authority.
- [ ] Candidate projection is pinned to the exact expected parent and requires it still be head at prepare/decide time.
- [ ] Only projectable visible Threat nodes enter the candidate set.
- [ ] Exact label/alias collisions are never hidden by ranking or truncation.
- [ ] Ranking is advisory and cannot auto-select.
- [ ] Create-new requires explicit adjudication of every exact-name collision.
- [ ] Proposed new Threat ID is server-derived, deterministic, bounded, and not name/slug based.
- [ ] Proposed ID collision fails closed without random suffix or silent connect.
- [ ] Connect-existing selects one exact reviewed Threat node ID.
- [ ] No name, alias, redirect, alias-map, or first-result fallback exists.
- [ ] Candidate-set and request digests recompute on durable load.
- [ ] Exact replay returns existing record before mutable dependency reads.
- [ ] Changed same-ID input conflicts without mutation.
- [ ] One operation has at most one active resolution.
- [ ] Supersession updates old/new records and active pointer in one atomic ledger replacement.
- [ ] Corrupt storage, dependency failure, and write failure do not auto-repair or invent authority.
- [ ] Read preserves historical resolution while reporting current predecessor usability separately.
- [ ] No World Graph, ThreatDraft, accepted-mechanics, or DungeonMind mutation occurs.
- [ ] The only adjacent predecessor mutation is an existing SBW09a refresh transition through its owning service.
- [ ] The internal Graph Kernel identity-decision store remains untouched.
- [ ] No create/connect graph effects, proposal, confirm, commit, verification, or UI contract was introduced.
- [ ] Every changed path is in §7 or a reported bounded exception.
- [ ] PR body records evidence, provenance, gaps, and waivers truthfully.
- [ ] SBW09c remains the named, unimplemented successor.

## §16 Stop conditions

Stop and report rather than widening the slice if candidate inspection cannot be
pinned to the SBW09a expected parent; candidate projection cannot prove the
selected node is projectable and campaign-visible; exact collisions cannot be
included within a safe bounded response; the ranker would need to become
identity authority; selection requires following a redirect or mutating
alias/merge state; create-new cannot be deterministic without graph mutation;
an identity decision cannot be durable without changing SBW09a schema; lock
order creates a cycle with SBW09a or graph stores; a second active resolution
cannot be rejected or atomically superseded; graph assertions/proposals/tokens/
receipts/verification are needed; the internal identity store must be written;
ThreatDraft, accepted mechanics, DungeonMind, or World Graph must be mutated;
a UI is needed to prove the server contract; a required path falls outside §7;
a required test passes only through current/latest, name, alias, redirect, or
first-result fallback; or a base failure requires operator waiver.

**Stop report template**

```text
Stop condition:
Why the current mission cannot absorb it:
Invariant clause affected:
Required evidence now missing:
New public/durable contract discovered:
Affected observable paths or ownership layers:
Proposed successor slice:
Tracker or authority update needed:
```

## §17 Named successors

**SBW09c — governed Threat + exact binding publication**

Consumes one ready SBW09a publication operation plus one active usable SBW09b
create_new or connect_existing resolution. Produces exact Threat/resource/
binding effects through a no-write reviewed proposal, proposal-bound
confirmation against the exact parent, an immutable World Graph revision, and
exact post-commit verification. Refuse is never publishable. Create-new uses
only the deterministic proposed Threat ID. Connect-existing uses only the
exact selected target node ID and reviewed snapshot. SBW09c revalidates
operation readiness/current parent immediately before proposal/commit and
does not rewrite SBW09a or SBW09b authority. Committed-but-unverified remains
distinct from not committed.

**SBW10a / SBW10b — query, hydration, and exact projection**

After SBW09c publishes, Hermes and product surfaces may resolve the published
Threat, inspect zero/one/many exact bindings explicitly, hydrate mechanics from
DungeonMind by the exact locator, and present useful game information without
copying mechanics into graph state.

**Generalization rule:** do not extract a universal authored-object identity
resolution framework from SBW09b alone. Revisit the seam only after Item + Item
Mechanics proves which matching, collision, create/connect, refusal, and
publication contracts genuinely generalize.
