# HANDOFF — SBW06b Revise Candidate Reconciliation: Lineage-on-Ref + Atomic Source Status

**Created:** 2026-07-27
**Status:** ACTIVE — dispatch exactly one implementation capability.
**Canonical handoff path:** `Docs/Plans/HANDOFF-sbw06b-revise-candidate-reconciliation.md`
**Implementation base:** `13b2e25856db945d67bfd0e6dcfae8b7c1446f63`
**Suggested branch:** `feat/sbw06b-reconcile-lineage`
**Repository:** `Drakosfire/DungeonMindBuddy`
**Workstream:** Threat + Statblock Authoring and Projection
**Slice:** `SBW06b`
**Normative contract:** `Docs/Plans/HANDOFF-sbw06-candidate-revise-lineage.md` §12, especially §§12.7–12.10, 12.12, and 12.15
**Merged predecessors:**

* `SBW06-contract` — PR `#413`
* `SBW06a` — PR `#417`, merge `8a73b10185e0e4b5c84bca92c2b1f3e0deda9432`
* Dogfood Gate A — PR `#425`, merge `13b2e25856db945d67bfd0e6dcfae8b7c1446f63`

**Next Milestone B slice:** `SBW06c` — Workbench revise UX
**Parallel work that remains independently dispatchable:** `SBW08` — World Graph external-resource/binding contract

> The dogfood pause has ended. This slice completes the backend product boundary intentionally deferred by SBW06a: a revise operation that has produced and cached a candidate becomes ordinary product success only after one lineage-bearing candidate ref is visible on the ThreatDraft and the revise journal is durably reconciled.

---

> **Note (2026-07-27):** §3 authority sync for `#413`/`#417`/`#425` already landed in PR `#434` (`00fa026d`). Dogfood Gate A handoff is archived at `Docs/Plans/archive/2026-07-27/handoffs/HANDOFF-sbw-dogfood-create-generate.md`. Code base tip: `00fa026d` (docs-only ahead of handoff base `13b2e258`).


## §0 Capability decomposition decision

| Candidate outcome                                                                                                  |                            Independently useful? |   Durable contract changed? | Surface changed? | Failure model changed? | Decision                        |
| ------------------------------------------------------------------------------------------------------------------ | -----------------------------------------------: | --------------------------: | ---------------: | ---------------------: | ------------------------------- |
| Attach one revise-produced candidate to its ThreatDraft with required embedded lineage and reconcile the operation |                                              Yes |                         Yes | Backend API only |                    Yes | **Include**                     |
| Validate and atomically apply an explicitly supplied source-candidate lifecycle transition with the attach         |          Required by the same mutation invariant |                         Yes |               No |                    Yes | **Include in the same CAS**     |
| Synchronize stale roadmap, tracker, and SBW06 handoff banners with merged `#417` and `#425`                        | No product capability; required authority repair |          Documentation only |               No |                     No | **Include as first commit**     |
| Add Workbench revise controls                                                                                      |                                              Yes |                          No |              Yes |                    Yes | **Successor `SBW06c`**          |
| Add candidate-origin UI and public source-status controls                                                          |                                              Yes |                 Potentially |              Yes |                    Yes | **Successor; not exposed here** |
| Revise from accepted mechanics locator                                                                             |                                              Yes | Uses exact locator identity |              Yes |                    Yes | **Successor `SBW06d`**          |
| Append a child mechanics revision or compare revisions                                                             |                                              Yes |                         Yes |              Yes |                    Yes | **Successor `SBW13`**           |
| Publish Threat or binding graph state                                                                              |                                              Yes |                         Yes |              Yes |                    Yes | **`SBW08–09`; exclude**         |
| Expand the statblock editor, renderer, media, or combat integration                                                |                                              Yes |                      Varies |              Yes |                 Varies | **Exclude**                     |

**Selected capability**

One revise operation that has a bound cached candidate can converge to ordinary success by atomically attaching one required-lineage candidate ref to the exact ThreatDraft and applying any valid, explicitly supplied source-status transition in the same draft CAS.

**Why the included work shares one invariant**

The candidate ref, its lineage, and any requested source-status transition are one product mutation. Exposing any subset would create a misleading or unrecoverable intermediate state.

**Named successors**

* `SBW06c` — revise UX and candidate-origin interaction.
* `SBW06d` — accepted-revision source.
* `SBW13` — append and compare immutable mechanics revisions.
* `SBW08–09` — graph binding contract and publication.

---

## §1 Mission

A revise-produced candidate becomes durable, inspectable ThreatDraft proposal history so that successful model-assisted iteration survives reload without overwriting or obscuring its exact source.

**Invariant**

```text
One ThreatDraft CAS either:

  appends exactly one new candidate ref
  + embeds its required CandidateLineageV1
  + applies the explicitly requested valid source-status transition, if any
  + increments ThreatDraft.version exactly once

or it applies none of those writes.

After the mutation is proven, the revise journal becomes reconciled.
Same-key recovery never appends a duplicate or increments the draft again.
```

**Mission falsification test**

```text
This is not one slice if implementation must also add:

- Workbench or liveApi revise UX,
- candidate-origin request construction,
- accepted-revision source mapping,
- immutable mechanics append or compare,
- graph publication,
- media,
- combat,
- or a sibling lineage store.
```

---

## §2 Context, authority, and boundaries

| Field                    | Required content                                                                                                                     |
| ------------------------ | ------------------------------------------------------------------------------------------------------------------------------------ |
| Parent authority         | Threat/statblock design; roadmap; PR tracker; frozen SBW06 §12                                                                       |
| Repository rules         | `AGENTS.md`; external-agent PR loop rule, skill, and canonical template                                                              |
| Base revision            | `13b2e25856db945d67bfd0e6dcfae8b7c1446f63`                                                                                           |
| Predecessor contract     | SBW06a revise journal reaches `cache_stored_ref_pending`; candidate is bound to journal request identity and existing cache boundary |
| Exact input consumed     | One existing revise operation and its exact candidate payload/cache record                                                           |
| Product output           | One updated `ThreatDraftV1` and one `ReviseOperationV1(status="reconciled")`                                                         |
| Current reachable origin | `edited_working_copy`                                                                                                                |
| Named successor          | `SBW06c`                                                                                                                             |
| What remains false       | No revise UI; no accepted-locator revise; no mechanics revision append; no graph truth                                               |
| Explicit non-goals       | Editor changes, browser state, DMS contract changes, graph/document/media/combat work                                                |

Read in this order before editing:

1. `Docs/Plans/HANDOFF-sbw06-candidate-revise-lineage.md` §12.
2. `Docs/Roadmaps/ROADMAP-threat-statblock-authoring-projection.md`.
3. `Docs/Plans/PR-TRACKER-threat-statblock-authoring-projection.md`.
4. `Docs/Plans/HANDOFF-sbw06a-revise-adapter-journal.md`.
5. `Docs/Plans/HANDOFF-sbw-dogfood-create-generate.md`.
6. `apps/live_control_server/models/threat_draft.py`.
7. `apps/live_control_server/models/statblock_candidate_revision.py`.
8. `apps/live_control_server/services/threat_draft_store.py`.
9. `apps/live_control_server/services/statblock_revise_reconciliation.py`.
10. `apps/live_control_server/services/statblock_candidate_revision.py`.
11. `apps/live_control_server/services/statblock_candidate_capacity.py`.
12. `apps/live_control_server/routes/statblock_candidates.py`.
13. Owning tests.
14. Repository rules.

### Authority precedence

```text
1. Accepted architecture and design decisions
2. Frozen SBW06 §12 contract
3. Active roadmap and PR tracker after this PR’s metadata sync
4. This checked-in SBW06b handoff
5. Current implementation and owning tests
6. Chat summaries or attached context
```

Do not rewrite or reinterpret the frozen §12 decisions. Metadata banners and status tables may be synchronized; normative transition semantics may not be changed inside this implementation PR.

---

## §3 Pre-implementation authority sync

The first commit on the branch must synchronize repository authority with merged reality.

Update:

```text
SBW06-contract — MERGED #413
SBW06a — MERGED #417 / 8a73b101
Dogfood Gate A — MERGED #425 / 13b2e258
current slice — SBW06b
next Milestone B slice — SBW06c
parallel lane — SBW08 remains independently dispatchable
```

Required documents:

* `Docs/Roadmaps/ROADMAP-threat-statblock-authoring-projection.md`
* `Docs/Plans/PR-TRACKER-threat-statblock-authoring-projection.md`
* `Docs/Plans/HANDOFF-sbw06-candidate-revise-lineage.md`
* `Docs/Plans/HANDOFF-sbw06a-revise-adapter-journal.md`
* `Docs/Plans/HANDOFF-sbw-dogfood-create-generate.md`

Rules:

* Change stale banners, current-slice markers, merge SHAs, and bite statuses.
* Do not rewrite frozen §12 tables.
* Mark the Dogfood Gate A pause as completed/released by the operator.
* Do not claim that SBW06 is complete.
* Do not move `SBW08` behind SBW06; it remains a parallel lane.
* Do not silently close the SBW04 real-candidate proof debt unless exact evidence is named.

---

## §4 Current implementation seam

At the implementation base:

```text
Revise request
→ durable revise journal
→ claimed
→ dispatched_unknown
→ candidate_received
→ candidate cache
→ cache_stored_ref_pending
→ STOP
```

Current limitations that this slice owns:

1. `ThreatDraftCandidateRefV1` has no lineage field.
2. `ReviseOperationStatus` has no `reconciled` state.
3. Revise draft-ref materialization cannot become `attached`.
4. Source-status materialization is not represented.
5. The revise service returns partial success after cache storage.
6. No Buddy route exposes ordinary revise success.
7. Existing `append_candidate_ref()` is an SBW03 generation operation:

   * it permits historical source-version attachment;
   * it does not increment `ThreatDraft.version`;
   * it cannot combine ref, lineage, and status transition.

**Required architectural decision**

Do not modify `append_candidate_ref()` into the SBW06b mutation.

Create a dedicated revise-materialization store boundary, conceptually:

```python
reconcile_revise_candidate_ref(
    root,
    *,
    draft_id,
    expected_version,
    candidate_ref,
    requested_source_transition=None,
) -> ThreatDraftV1
```

The exact function name may differ. Its semantics may not.

---

## §5 Observable-path inventory

| Observable path                        | Current behavior                   | Required behavior                                                                  | Owning boundary    |
| -------------------------------------- | ---------------------------------- | ---------------------------------------------------------------------------------- | ------------------ |
| Fresh edited-definition revise         | Ends at `cache_stored_ref_pending` | Attaches lineage-bearing ref and returns `reconciled`                              | Service + store    |
| ThreatDraft reload                     | No revise lineage visible          | Ref and embedded lineage reload exactly                                            | Model + store      |
| Same-key replay after success          | Re-enters cache recovery           | Returns reconciled without duplicate ref/version increment                         | Service + journal  |
| Draft CAS stale                        | Partial operation remains          | No ref, lineage, or status mutation; journal remains pending                       | Store + service    |
| Invalid source-status transition       | Not implemented                    | Entire CAS fails; no new ref is visible                                            | Store              |
| CAS succeeds, journal write fails      | Not implemented                    | Draft reread proves attach; same-key recovery marks journal reconciled             | Service + journal  |
| Journal already pending but ref exists | Could block forever                | Prove exact request/candidate/lineage and reconcile idempotently                   | Service            |
| Legacy generated ref                   | No lineage                         | Continues to load with `lineage: null`                                             | Model              |
| Revise-created ref without lineage     | Possible if generic append used    | Dedicated revise CAS rejects it                                                    | Store              |
| Capacity reservation after attach      | Journal remains unresolved         | Attached candidate ceases to count as reserved; reconciled op releases active slot | Capacity + journal |
| Existing mechanics-saved draft         | Candidate append may occur         | Accepted mechanics and `mechanics_saved` state remain unchanged                    | Store              |
| Backend HTTP entry                     | No revise route                    | Exact request can reach ordinary reconciled response                               | Route              |
| Candidate payload later unavailable    | No reconciled product state        | Ref/lineage remain durable; payload availability is reported honestly              | Service/read path  |

Every row establishes the §1 invariant.

---

## §6 Files in scope — allowlist

| Action | Path                                                                   | Purpose                                                           |
| ------ | ---------------------------------------------------------------------- | ----------------------------------------------------------------- |
| Create | `Docs/Plans/HANDOFF-sbw06b-revise-candidate-reconciliation.md`         | Check in complete dispatch authority                              |
| Modify | `Docs/Roadmaps/ROADMAP-threat-statblock-authoring-projection.md`       | Synchronize merged Gate A and activate SBW06b                     |
| Modify | `Docs/Plans/PR-TRACKER-threat-statblock-authoring-projection.md`       | Synchronize sequence and current slice                            |
| Modify | `Docs/Plans/HANDOFF-sbw06-candidate-revise-lineage.md`                 | Metadata/banner sync only                                         |
| Modify | `Docs/Plans/HANDOFF-sbw06a-revise-adapter-journal.md`                  | Mark merged and name SBW06b                                       |
| Modify | `Docs/Plans/HANDOFF-sbw-dogfood-create-generate.md`                    | Mark merged and pause completed                                   |
| Modify | `apps/live_control_server/models/threat_draft.py`                      | Add frozen lineage-on-ref schema and validation                   |
| Modify | `apps/live_control_server/models/statblock_candidate_revision.py`      | Add reconciled journal/result/materialization states              |
| Modify | `apps/live_control_server/services/threat_draft_store.py`              | Dedicated atomic revise ref/lineage/status CAS                    |
| Modify | `apps/live_control_server/services/statblock_revise_reconciliation.py` | Reconciled journal transition and recovery proof                  |
| Modify | `apps/live_control_server/services/statblock_candidate_revision.py`    | Continue cache-pending operations through draft reconciliation    |
| Modify | `apps/live_control_server/routes/statblock_candidates.py`              | Expose exact backend revise entry through current service         |
| Modify | `tests/test_threat_draft_store.py`                                     | Model, CAS, status, idempotency, and backward-compatibility proof |
| Modify | `tests/test_statblock_candidate_revision.py`                           | Service/journal/recovery/capacity proof                           |
| Modify | `tests/test_statblock_candidate_routes.py`                             | Exact HTTP route and reconciled response proof                    |

### Bounded discovery exception

```text
Directory:
  tests/

Maximum additional paths:
  1

Allowed path:
  A new focused test module for revise reconciliation only.

Decision rule:
  Use only if separating pure journal/store recovery cases materially improves
  ownership and readability over adding them to test_statblock_candidate_revision.py.

Required report:
  Name the path and explain why the existing owning test file was insufficient.
```

No generated DMS contract or fixture change is expected.

---

## §7 Explicitly out of scope

| Path or capability                          | Why excluded                                                      |
| ------------------------------------------- | ----------------------------------------------------------------- |
| `apps/live-control-ui/**`                   | Revise UX belongs to `SBW06c`                                     |
| DMS OpenAPI/generated contract regeneration | SBW06a transport contract is already proven                       |
| Candidate-origin request mapper             | Not needed for the currently reachable edited-working-copy origin |
| Accepted-revision locator mapper            | `SBW06d`                                                          |
| New mechanics revision creation             | `SBW13`                                                           |
| Comparison UI                               | `SBW13`                                                           |
| Graph contracts or writes                   | `SBW08–09`                                                        |
| Plan documents or embeds                    | `SBW11–12`                                                        |
| Images or media                             | `SBW16–18`                                                        |
| Combat                                      | `SBW15`                                                           |
| New sibling lineage files/store             | Frozen §12 requires lineage on the candidate ref                  |
| Candidate history eviction or compaction    | Requires separate architecture review                             |
| Automatic source supersede                  | Explicitly forbidden                                              |
| Changing generic SBW03 append semantics     | Different persistence/version contract                            |
| Public journal-management UI                | `SBW06c` or a separately justified recovery surface               |

Nearby work is not authorization.

---

## §8 Implementation contract

### 8.1 CandidateLineageV1

Implement the frozen lineage structure under the ThreatDraft domain model.

Common required fields:

```text
schema = dmb_candidate_lineage_v1
revise_request_id
source_origin_kind
instruction_options_digest
created_at
```

Exactly one variant object must be present.

```text
edited_working_copy:
  draft_id
  source_draft_version
  editor_state_revision
  source_definition_digest

candidate:
  source_candidate_id
  source_candidate_request_id
  draft_id
  source_generated_from_draft_version
  source_definition_digest

accepted_revision:
  provider
  statblock_id
  revision_id
  contract
  contract_version
  definition_digest
```

Validation must fail closed when:

* the declared variant is absent;
* more than one variant is present;
* fields belonging to another variant are present;
* a required source identity field is missing;
* `candidate_ref.request_id != lineage.revise_request_id`.

Add:

```text
ThreatDraftCandidateRefV1.lineage: CandidateLineageV1 | null
```

Compatibility rule:

* Existing pre-SBW06 generation refs may deserialize with `lineage=null`.
* The dedicated revise CAS must reject a new revise ref whose lineage is null.

Do not duplicate the complete working definition into the ThreatDraft.

### 8.2 Dedicated revise CAS

The dedicated mutation must:

1. Acquire the ThreatDraft store lock.
2. Load the committed draft.
3. Require exact `expected_version == current.version`.
4. Validate the new ref and lineage binding.
5. Detect candidate and request identity conflicts.
6. Validate the optional source-status transition.
7. Construct one complete updated `ThreatDraftV1`.
8. Increment `version` exactly once.
9. Preserve authored concept fields.
10. Preserve accepted mechanics.
11. Preserve `workflow_state="mechanics_saved"` when already saved.
12. Otherwise promote `drafting` to `candidate_ready`.
13. Persist with one atomic draft replacement.

No write may happen before all checks pass.

### 8.3 Dedupe and conflict rules

For the incoming revise ref:

```text
candidate_ref.request_id
  == lineage.revise_request_id
  == journal.request_id
  == Server request_id
```

Required behavior:

| Existing state                                          | Required result                                                                            |
| ------------------------------------------------------- | ------------------------------------------------------------------------------------------ |
| No matching ref/request                                 | Append once                                                                                |
| Same candidate ID, same request ID, exact lineage       | Idempotent success                                                                         |
| Same candidate ID, different request or lineage         | 409 conflict                                                                               |
| Same request ID, different candidate ID                 | 409 conflict                                                                               |
| Existing exact ref but requested status not yet applied | Apply status only in the same recovery CAS if the original request proves it was requested |
| Existing exact ref and requested status already applied | Idempotent success                                                                         |
| Missing lineage on incoming revise ref                  | Fail closed                                                                                |
| Legacy unrelated ref with null lineage                  | Preserve unchanged                                                                         |

Same-key replay after an already completed mutation must not increment the draft version again.

### 8.4 Source-status transition table

Implement the frozen lifecycle rules:

```text
active → superseded
active → rejected
active → expired
active → accepted_source
same → same
```

Rules:

* `active → superseded` and `active → rejected` require an explicit transition request.
* `active → expired` requires exact expiry proof.
* `active → accepted_source` requires `accepted_mechanics_ref.accepted_from_candidate_id` to equal the candidate.
* Same status is idempotent.
* `accepted_source`, `superseded`, `rejected`, and `expired` are terminal for SBW06.
* No new revise candidate automatically changes its source.
* An invalid transition aborts the complete ref/lineage/status CAS.

### 8.5 Reachable transition behavior in SBW06b

The currently implemented request origin is `edited_working_copy`. It does not identify a source candidate whose lifecycle should change.

Therefore the ordinary route in this slice must reconcile with:

```text
source_status materialization = none
```

The dedicated CAS and store tests must implement and prove the frozen status table for an explicitly supplied transition.

Do not:

* invent a candidate source from browser/session state;
* smuggle a transition into `intent`, `context`, or another Server field;
* change the frozen request-digest recipe without explicit contract authority;
* claim `source_status=applied` when the journal does not prove a transition was requested.

If implementing recoverable requested transitions requires adding a previously unspecified journal request field or changing request-digest inputs, stop and report that contract gap. Do not silently alter frozen §12.

### 8.6 Revise journal state

Extend the revise journal with:

```text
status:
  reconciled

materialization.draft_ref:
  attached

materialization.source_status:
  none | applied
```

Backward compatibility:

* Existing journal records lacking `source_status` must load with `none`.
* Existing SBW06a records in `cache_stored_ref_pending` must remain valid.

`reconciled` requires:

* exact candidate ID;
* cache materialization truth retained;
* `draft_ref=attached`;
* `source_status=none|applied`;
* no terminal fields;
* no unresolved recovery classification.

`reconciled` is not an unresolved operation and does not occupy the active revise slot.

### 8.7 Building the edited-working-copy lineage

For the existing SBW06a origin, construct lineage from durable journal authority:

```text
schema                       = dmb_candidate_lineage_v1
revise_request_id            = operation.request_id
source_origin_kind           = edited_working_copy
instruction_options_digest   = operation.instruction_options_digest
created_at                   = stable operation/candidate creation time

edited_working_copy:
  draft_id                   = operation.draft_id
  source_draft_version       = operation.source_draft_version
  editor_state_revision      = operation.editor_state_revision
  source_definition_digest   = operation.source_definition_digest
```

The candidate ref must use:

```text
candidate_id
generated_from_draft_version = operation.source_draft_version
request_id                   = operation.request_id
created_at                   = stable candidate or operation timestamp
status                       = active
lineage                      = required object above
```

Do not read mutable editor state while materializing lineage.

### 8.8 Service orchestration

Change the existing revise service from:

```text
cache_stored_ref_pending
→ return partial
```

to:

```text
cache_stored_ref_pending
→ verify bound cached candidate
→ build exact candidate ref + lineage
→ read current ThreatDraft version
→ dedicated revise CAS
→ mark journal reconciled
→ return reconciled
```

The operation may still return partial states when local materialization genuinely fails.

Required result label:

```text
reconciled
```

A reconciled response proves ordinary product success.

### 8.9 CAS-success / journal-failure recovery

Required sequence:

```text
1. Attempt draft CAS.
2. If CAS reports success, attempt journal reconciled write.
3. If journal write fails or outcome is uncertain:
   a. reread the ThreatDraft;
   b. find the candidate ref by candidate_id;
   c. prove request_id equality;
   d. prove exact embedded lineage;
   e. prove requested source status is applied, or none was requested;
   f. retry marking the journal reconciled.
```

If proof fails:

* do not rewrite the ref;
* do not append another ref;
* do not release authority locally;
* return an honest pending/integrity result.

If proof succeeds but journal storage remains unavailable, ordinary product data exists but the workflow has not fully reconciled. Preserve the same request ID and allow later recovery.

### 8.10 Capacity behavior

Do not add a separate reservation record.

The unresolved revise journal remains the reservation until:

* its candidate ref is attached; or
* terminal non-begin proof releases it.

Capacity accounting must not double-count an attached candidate whose journal has not yet reached `reconciled`.

After reconciliation:

```text
attached count includes the ref
revise reservation excludes the operation
active revise slot is free
```

Do not modify the limit of 64.

### 8.11 Lock ordering

Preserve the frozen lock order:

```text
new claim:
  ThreatDraft store
  → shared candidate capacity
  → revise journal

materialization:
  read journal authority
  → release journal lock
  → ThreatDraft CAS under store lock
  → release store lock
  → journal reconciled write
```

Never hold the revise journal lock while acquiring the ThreatDraft store lock.

If current helpers require reverse nesting, stop and report rather than introducing a deadlock risk.

### 8.12 HTTP route

Add the Buddy backend entry:

```text
POST /api/live/threat-drafts/{draft_id}/candidates:revise
```

Request:

```text
ReviseCandidateFromEditedDefinitionRequestV1
```

Response:

```text
ReviseCandidateFromEditedDefinitionResponseV1
```

The route must:

* call the existing service;
* return `result=reconciled` on ordinary success;
* preserve typed partial results;
* translate known store/reconciliation/service errors into their owned HTTP status;
* not construct privileged DMS requests itself.

Do not add frontend code.

A public raw-journal read or management route is not required for this slice. If one becomes necessary to satisfy reload or recovery, stop and justify it as either part of this invariant or a successor capability—do not expose private stored instruction bodies casually.

---

## §9 State and recovery matrix

| Starting state                                        | Required action                               | Successful destination             | Failure destination                |
| ----------------------------------------------------- | --------------------------------------------- | ---------------------------------- | ---------------------------------- |
| `claimed`                                             | Existing SBW06a write-ahead/dispatch behavior | Existing downstream states         | Existing partial/terminal states   |
| `dispatched_unknown`, no candidate                    | Existing same-key recovery                    | Candidate known or remains unknown | Preserve same request              |
| `candidate_received`, cache missing/failed            | Existing exact cache/GET repair               | `cache_stored_ref_pending`         | `candidate_received`               |
| `cache_stored_ref_pending`, ref absent                | Dedicated draft CAS                           | `reconciled`                       | Remain pending                     |
| `cache_stored_ref_pending`, exact ref already present | Prove ref/lineage/status; mark journal        | `reconciled`                       | Integrity/pending                  |
| `reconciled`                                          | Read-only same-key replay                     | Same reconciled authority          | No new mutation                    |
| Draft CAS stale                                       | Reread and bounded same-operation retry       | Reconciled                         | Pending; no partial draft mutation |
| Invalid requested status                              | Reject complete CAS                           | No mutation                        | Typed conflict                     |
| Journal write fails after CAS                         | Reread and prove                              | Reconciled on retry                | Pending with same request          |
| Legacy ref with null lineage                          | Preserve                                      | Unchanged                          | No migration required              |
| Revise ref with null lineage                          | Reject                                        | None                               | Fail closed                        |

---

## §10 Required adversarial tests

### Model and backward compatibility

1. Pre-SBW06 ref with `lineage=null` reloads.
2. Valid edited-working-copy lineage reloads.
3. Valid candidate and accepted-revision variants validate structurally.
4. Mixed origin variants fail.
5. Missing declared variant fields fail.
6. Candidate-ref/request lineage mismatch fails.

### Dedicated CAS

7. Fresh attach adds one ref, one lineage, and increments version exactly once.
8. Same-key replay adds no duplicate and performs no second version increment.
9. Same candidate ID with different request or lineage conflicts.
10. Same request ID with different candidate ID conflicts.
11. Missing lineage causes no mutation.
12. Stale expected version causes no mutation.
13. Invalid status transition causes no ref, lineage, status, or version mutation.
14. Valid `active → superseded`.
15. Valid `active → rejected`.
16. `active → expired` fails without expiry proof and succeeds with exact proof.
17. `active → accepted_source` fails without accepted-mechanics proof and succeeds with exact proof.
18. Terminal status cannot transition.
19. Existing `mechanics_saved` state and accepted ref remain unchanged.
20. Drafting state becomes `candidate_ready`.

### Journal and service reconciliation

21. Current edited-source revise reaches `reconciled`.
22. Journal records `draft_ref=attached` and `source_status=none`.
23. ThreatDraft read shows exact lineage.
24. CAS failure leaves `cache_stored_ref_pending`.
25. CAS success followed by journal-write failure converges on same-key retry.
26. Ref already attached with pending journal reconciles without duplicate.
27. Mismatched attached lineage does not reconcile.
28. Reconciled operation does not occupy active slot.
29. Capacity does not double-count attached ref plus pending journal.
30. Candidate/cache identity binding remains enforced.
31. Source candidate and accepted mechanics are never automatically changed.

### Route

32. Exact revise POST returns `reconciled`.
33. ThreatDraft GET after route success exposes exact candidate ref and lineage.
34. Same-key route replay returns the same candidate and no duplicate ref.
35. Stale draft version remains typed and creates no product mutation.
36. Partial cache or draft failure remains a truthful partial result.

---

## §11 Verification commands

Run focused tests:

```bash
uv run pytest \
  tests/test_threat_draft_store.py \
  tests/test_statblock_candidate_revision.py \
  tests/test_statblock_candidate_routes.py \
  -q --tb=line
```

Run adjacent regression owners:

```bash
uv run pytest \
  tests/test_statblock_candidate_generation.py \
  tests/test_statblock_mechanics_acceptance.py \
  tests/test_statblock_acceptance_reconciliation.py \
  -q --tb=line
```

Run static checks on changed Python paths using the repository’s established commands. At minimum:

```bash
uv run ruff check \
  apps/live_control_server/models/threat_draft.py \
  apps/live_control_server/models/statblock_candidate_revision.py \
  apps/live_control_server/services/threat_draft_store.py \
  apps/live_control_server/services/statblock_revise_reconciliation.py \
  apps/live_control_server/services/statblock_candidate_revision.py \
  apps/live_control_server/routes/statblock_candidates.py \
  tests/test_threat_draft_store.py \
  tests/test_statblock_candidate_revision.py \
  tests/test_statblock_candidate_routes.py

git diff --check
```

Record base and head behavior for any pre-existing failure.

### Minimal live/backend proof

Use a real ThreatDraft and a real DMS revise candidate where available:

1. Produce or recover an SBW06a operation at `cache_stored_ref_pending`.
2. Call the Buddy revise route with the same request.
3. Observe `result=reconciled`.
4. GET the ThreatDraft.
5. Record:

   * draft ID;
   * pre- and post-CAS versions;
   * request ID;
   * candidate ID;
   * lineage source kind;
   * source definition digest;
   * journal status/materialization;
   * confirmation that accepted mechanics were unchanged.
6. Restart or reload the backend.
7. Replay the same request.
8. Confirm no duplicate and no second version increment.

If DMS is unavailable, a fully seeded journal/cache integration proof may substitute for Server dispatch, but the limitation must be stated precisely.

---

## §12 Demolition declaration

```text
Replaced path:
  SBW06a ordinary processing stops at cache_stored_ref_pending even when
  all local data required for ThreatDraft materialization is available.

Deleted in this PR:
  No.

Retained reason:
  cache_stored_ref_pending remains a truthful partial-completion state when
  the draft CAS or journal reconciliation cannot complete.

Named remaining consumer:
  SBW06 recovery and future SBW06c UI.

Required deletion owner:
  None. The partial state is a durable recovery state, not temporary scaffolding.
```

`append_candidate_ref()` remains because SBW03 generation owns its current semantics.

---

## §13 Required implementation handback

The PR body must include:

1. Base SHA `13b2e25856db945d67bfd0e6dcfae8b7c1446f63`.
2. Head SHA.
3. Actual changed paths.
4. Focused diff stat.
5. Exact test commands, counts, exit codes, and evidence provenance.
6. Documentation-sync summary.
7. Exact lineage schema added.
8. Exact dedicated CAS function and its version behavior.
9. Journal transition evidence to `reconciled`.
10. CAS-success/journal-failure recovery evidence.
11. Capacity release/no-double-count proof.
12. Route contract and live/backend proof.
13. Confirmation that generic generation append semantics were unchanged.
14. Confirmation that existing accepted mechanics were unchanged.
15. Confirmation that no source status changes automatically.
16. Confirmation that current edited-origin success records `source_status=none`.
17. Paths outside the allowlist or `none`.
18. Stop conditions encountered or `none`.
19. Baseline failures/waivers or `none`.
20. Explicit statement that `SBW06c`, `SBW06d`, `SBW08–09`, `SBW13`, media, and combat remain false.

Do not describe SBW06 as complete after this PR. `SBW06c–d` remain.

---

## §14 Acceptance rubric

The reviewer accepts only when:

* [ ] Repository metadata names `#413`, `#417`, and `#425` accurately.
* [ ] `SBW06b` is current and `SBW06c` is next in the Milestone B lane.
* [ ] `SBW08` remains a parallel lane.
* [ ] Legacy refs with null lineage reload.
* [ ] Every revise-created ref requires embedded lineage.
* [ ] All lineage variants are structurally closed.
* [ ] Request identity equality is enforced.
* [ ] A dedicated revise CAS exists.
* [ ] Generic SBW03 append semantics remain unchanged.
* [ ] New ref, lineage, and requested status are both-or-neither.
* [ ] Successful attach increments the draft version exactly once.
* [ ] Same-key replay does not increment it again.
* [ ] Invalid status transitions produce no mutation.
* [ ] Creating a revised candidate never automatically supersedes its source.
* [ ] Existing accepted mechanics remain unchanged.
* [ ] Journal reaches `reconciled`.
* [ ] Reconciled materialization records `draft_ref=attached`.
* [ ] Edited-origin success records `source_status=none`.
* [ ] CAS-success/journal-failure recovery converges.
* [ ] Reconciled operation releases its active slot and reservation.
* [ ] Capacity is not double-counted.
* [ ] Backend route returns ordinary reconciled success.
* [ ] Partial states remain truthful and recoverable.
* [ ] No frontend, graph, append, compare, media, or combat work entered the diff.
* [ ] Focused and adjacent regression suites pass or have exact base/head evidence.

---

## Stop conditions

Stop and report rather than widening the slice when:

* current `main` differs materially from base `13b2e258`;
* frozen §12 must be changed to implement the requested behavior;
* recoverable source-status requests require a new journal field or digest input not authorized by §12;
* a sibling lineage store appears necessary;
* generic `append_candidate_ref()` must change;
* the DMS revise contract must change;
* candidate-origin or accepted-locator transport must be implemented;
* a frontend or liveApi path is required;
* lock ordering would require revise-journal → ThreatDraft-store nesting;
* candidate history requires eviction, compaction, or a limit change;
* ordinary success cannot be proven from the ThreatDraft read path;
* a changed path falls outside §6 and the bounded exception.

Use this report:

```text
Stop condition:
Why SBW06b cannot absorb it:
Frozen contract affected:
New durable/public decision required:
Affected observable paths:
Required path outside scope:
Proposed successor or contract clarification:
Operator decision required:
```

---

## Final dispatch check

* [ ] Branch from `13b2e25856db945d67bfd0e6dcfae8b7c1446f63`.
* [ ] Check this complete handoff into the canonical path.
* [ ] Synchronize stale documentation before production code.
* [ ] Re-anchor the current models, store, journals, capacity helper, service, route, and tests.
* [ ] Add lineage as backward-compatible ref data.
* [ ] Implement a dedicated revise CAS.
* [ ] Preserve generic generation append behavior.
* [ ] Extend the journal to reconciled/attached/source-status.
* [ ] Continue current edited-origin service through ordinary success.
* [ ] Add the backend route without frontend work.
* [ ] Prove recovery, idempotency, capacity, and status atomicity.
* [ ] Run focused and adjacent regression suites.
* [ ] Record exact evidence.
* [ ] Stop before `SBW06c`.
