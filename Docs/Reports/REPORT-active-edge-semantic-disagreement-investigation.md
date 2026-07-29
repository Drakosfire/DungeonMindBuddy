# REPORT — Active-Edge Semantic Disagreement in World-Graph Projection

**Status:** COMPLETE (investigation only)  
**Created:** 2026-07-28  
**Mode:** Architecture forensics / semantic-model audit  
**Implementation authority used:** None  
**Graph mutation authority used:** None (read-only inspection after the already-completed head migration)  
**Repo tip at investigation:** `817427bd`  
**World inspected:** `eldyrwild`  
**Head at investigation:** `rev:5017a20164555f11d4508f67661058f1`  
**Prior restored head:** `rev:2a72ef7a40ba37bc33e3f2680d528970`

---

## 8.1 Executive summary

**What was found.** The projection failure
`409 projection_integrity_error: Active edge assertions disagree on semantic fields`
is caused by **one** durable edge:

```text
edge:pc:baergrom:serves:pc:caelynn
```

Two co-active assertions support that edge with different **labels** (`serves` vs `revives`) while sharing the same **predicate** (`serves`) and therefore the same durable `edge_id`. The integrity gate compares labels as correction-sensitive and hard-fails.

**Correction to the triggering claim.** The backlog / handoff said “nine edges … whose semantic labels differ.” That is **not accurate**.

| Population | Count | Projection effect |
| --- | ---: | --- |
| Edges with >1 active assertion at head | **9** | 8 of these **agree** under `_edge_core_semantic_fingerprint` |
| Edges whose active assertions **disagree** on the fingerprint | **1** | Sole cause of the current `409` |

The other eight are multi-active **re-attestations** (same label/predicate; only session stamps differ). Session stamps are intentionally stripped from the edge core fingerprint (`4d137f6a`, 2026-07-19). They are legal under today’s projection contract and are **not** the failure.

**One root cause or several?** Several cooperating causes, not one:

1. **Edge identity is `source:predicate:target`** (label is not part of the key).
2. **Assertion identity includes `label`**, so unlike labels create distinct `assertion_id`s that still attach to one edge.
3. **Merge/rebuild do not refuse co-active edge disagreements** (nodes do; edges do not).
4. **Projection is the first stage that enforces edge semantic agreement.**
5. For the failing edge specifically: **extraction assigned predicate `serves` to combat heal/revive events**, with free-text labels that disagree (`serves` vs `revives`), and both contributions remain active without supersession of one another.

**Which layer first creates the ambiguous state?** Contribution merge / rebuild when applying accepted edge assertions: `_apply_edge_assertion` groups by `edge_id`; `_add_support` records separate support rows for each `assertion_id` under the same `graph_object_id`. No edge semantic-agreement refuse runs here.

**Which layer first detects it?** World-graph projection relationship build → `_aggregate_active_edge_support` → `_assert_active_edge_assertions_agree`.

**Immediate product impact.** Plan / Ingest / Build / Graph Review / Hermes unioned-graph surfaces that call `POST /api/live/world-graph/projection` (or recap-projection) fail closed. Statblock Workbench / `R0-A` does not depend on this path and remains available. `R0-B` remains blocked.

**Confidence.** High for the as-built identity rules, the projection gate, the 9-vs-1 inventory, and the validation-boundary mismatch. Medium for extraction ontology intent (why `relationship_type` became `serves` for revive/heal prose). Low for whether older published heads would have projected under today’s gate without the stale-field parse failure (the restored head’s support map was also structurally odd — see §8.2).

---

## 8.2 Incident reconstruction

Keep these as **two separate incidents**.

### Incident A — resolved: stale `per_contribution_assertion_ids`

1. Restored head `rev:2a72ef7a` failed projection with `projection_internal_error`.
2. Diagnostics showed Pydantic `extra_forbidden` on `DurableAssertionSupport.per_contribution_assertion_ids` (889 support rows).
3. Current model (`src/graph_memory/evidence/assertion_support.py`) is `extra="forbid"` and does not declare that field.
4. In-place edit of `graph.json` is unsafe (content-addressed revision integrity).
5. Operator-approved `kernel.rebuild_from_contributions(publish=True)` produced clean head `rev:5017a201…` with identical node/edge counts (`432` / `344`).
6. Archived in `Backlog-DONE.md` as `[DONE] Restored Eldyrwild graph head migrated past stale support field`.

### Incident B — open: active-edge semantic disagreement

1. After rebuild, projection returns `409 projection_integrity_error`.
2. Diagnostic detail:

```text
graph_object_id='edge:pc:baergrom:serves:pc:caelynn'
active_assertion_ids=['assertion:134135a4f3a2487b', 'assertion:b6ec355852102812']
```

3. Reproduced 2026-07-28 against live Buddy API on head `rev:5017a201…`.

### Important restored-head detail (observed, not mutated)

On `rev:2a72ef7a`, support row `assertion:134135a4f3a2487b` listed **both** `contribution:280788…` and `contribution:9080…` in `active_contribution_ids`, while its stale `per_contribution_assertion_ids` map already recorded:

```text
contribution:280788… → assertion:134135…
contribution:9080…  → assertion:b6ec…
```

So the restored head’s support **key** collapsed two assertion identities under one support record, even though the per-contribution map knew they differed. Rebuild from contribution ledgers produced the cleaner (and currently failing) state: two support rows, one edge, disagreeing labels.

**Inference (medium confidence):** the stale-field failure masked both (a) model drift and (b) a support-map collapse. Rebuild fixed (a) and normalized support keys from ledgers, exposing (b)’s underlying semantic disagreement.

---

## 8.3 As-built semantic model

### Durable edge identity

**As-built rule (one sentence):** Two accepted edge assertions denote the same durable edge iff they resolve to the same `edge_id` — explicit `value.edge_id` if present, otherwise `edge:{source_node_id}:{predicate}:{target_node_id}` after endpoint resolution.

**Code path:**

| Stage | Location |
| --- | --- |
| Ingest packaging | `src/graph_memory/candidate_graph_to_contribution.py` ~547: sets `value["edge_id"] = f"edge:{subject_id}:{predicate}:{target_id}"` where `predicate = (edge.relationship_type or "related_to")` and `label = (edge.label or predicate)` |
| Merge | `src/graph_memory/kernel/contribution_merge.py` `_apply_edge_assertion` ~861: `edge_id = str(value.get("edge_id") or f"edge:{source_id}:{predicate}:{target_id}")` |
| Support attach | `_add_support` stores that `edge_id` as `DurableAssertionSupport.graph_object_id` |

**Not in the edge key:** `label`, direction (defaults outbound), temporal scope, contribution id, assertion id.

### Assertion identity

**As-built rule (one sentence):** `assertion_id = assertion:{sha256(canonical_json(semantic_fields))[:16]}` over kind, subject, target, predicate, **label**, semantic `value` (provenance keys stripped), campaign_scope, **full temporal_scope**, epistemic_kind, visibility.

**Code:** `src/graph_memory/kernel/contributions.py` `compute_assertion_id` (111–137), `semantic_assertion_value` (140–146), provenance-only keys (18–27).

**Consequence:** Changing only `label` or only `temporal_scope.session_id` yields a **new** `assertion_id`, but the durable edge key may still be identical if predicate/endpoints match.

### Semantic field ownership

| Field | Durable edge (`UnionSupergraphEdge`) | Per assertion | Contribution | Projection |
| --- | --- | --- | --- | --- |
| endpoints | yes (source/target) | yes (subject/target) | via assertions | read from assertion then edge fallback |
| predicate | yes | yes | via assertions | fingerprint |
| label | stored on edge at create; **not updated** on later merge of same `edge_id` | yes (identity + fingerprint) | via assertions | fingerprint |
| direction | yes | in `value` | via assertions | used in views; in semantic value |
| session_ids | additive merge on edge | in `value` / temporal_scope | often set for non-campaign-stable domains | stripped from edge core fingerprint; unioned for display |
| campaign_scope | in edge `state` | assertion field | contribution `campaign_scope` | fingerprint |
| evidence | additive on edge | assertion + nested value | contribution source artifact | provenance views |

**Identity vs mutable metadata tension:** `label` is **not** part of durable edge identity, but **is** part of assertion identity and projection’s correction-sensitive fingerprint. That is the central contract mismatch.

### What `active` means (distinct meanings found)

| Layer | Meaning | Where |
| --- | --- | --- |
| Contribution ledger | `status ∈ {active, superseded, retracted, failed}` | contribution records + `contribution_index.json` |
| Assertion acceptance | `acceptance_state == "accepted"` and graph-mutating identity outcome | `contribution_merge._is_graph_mutating_accepted_assertion` |
| Durable support live backing | `DurableAssertionSupport.active_contribution_ids` non-empty | `assertion_support.py`; merge `_add_support` / `_remove_contribution_support` |
| Support lifecycle | `support_state ∈ {supported, unsupported, contradicted, retracted}` | type allows `contradicted`; **kernel merge/rebuild never assign `contradicted`** (observed) |
| Projection “active support” | `support_state == "supported"` **and** non-empty `active_contribution_ids` | `world_projection._active_supports_for_graph_object` |
| Graph object visibility | `state.memory_state == "unsupported_assertion"` hides objects | `_mark_graph_objects_unsupported` |

**Not found:** a separate “currently true in-world” flag distinct from “accepted and not superseded/retracted.”

### Temporal semantics

- Ingest often sets `temporal_scope={"session_id": …}` and `value.session_ids=[…]` for non–campaign-stable source domains (`candidate_graph_to_contribution.py` ~568–577).
- Those session stamps **change assertion_id**.
- Merge treats `session_ids` as **additive observation provenance** on the edge (comment at contribution_merge ~920–921).
- Projection edge core fingerprint **strips** `value.session_ids` and `temporal_scope.session_id` (`_edge_core_semantic_fingerprint`, world_projection.py 415–442), by design since `4d137f6a`.
- Other temporal qualifiers (e.g. `as_of`) remain fingerprint-sensitive (unit test `test_edge_fingerprint_disagrees_on_other_temporal_scope_fields`).

**Not found:** first-class representation of historically-true vs currently-true as distinct activation states.

### Supersession semantics

- Contribution field `supersedes_contribution_id` participates in **contribution_id** hashing.
- `supersede_graph_contribution` removes the old contribution from support actives, applies the new contribution’s assertions, marks ledger status superseded.
- Supersession is **contribution-scoped**, not “later session automatically supersedes earlier assertion on same edge.”
- Observed example: `contribution:9080…` supersedes `contribution:dba1…` (same session-12 artifact lineage). It does **not** supersede session-10 `contribution:280788…`.
- Superseded history remains in contribution ledgers and may remain inspectable via support `superseded_contribution_ids` when emptied of actives.

### Projection invariants (edges)

`_assert_active_edge_assertions_agree` requires all active edge assertions for one `graph_object_id` to share one `_edge_core_semantic_fingerprint`:

```text
assertion_kind, subject, target, predicate, label,
semantic_value(minus session_ids),
epistemic_kind, visibility, campaign_scope,
temporal_scope(minus session_id)
```

Introduced in commit `4d137f6a` (2026-07-19): `fix(graph): connect-existing support-only observation path` — message includes “Exclude additive edge session_ids from projection core fingerprints.”

---

## 8.4 End-to-end code path

Compact pipeline (as-built):

```text
corpus / recap / standing registry
  → extraction / candidate graph (relationship_type + label)
  → candidate_graph_to_contribution.build edge assertion
       edge_id := edge:{subject}:{predicate}:{target}
       assertion_id := hash(… includes label + temporal_scope …)
  → contribution validation / Graph Review accept (not re-checked here)
  → merge_contribution_to_revision
       apply_accepted_assertions
         node: may _refuse_disagreeing_active_node_assertion (if root+world_id)
         edge: _apply_edge_assertion (NO semantic refuse)
         _add_support(graph_object_id=edge_id)
  → publish revision (content-addressed graph.json + manifest)
  → rebuild_from_contributions (optional)
       apply_accepted_assertions WITHOUT root/world_id
         → no node refuse either
  → project_world_graph
       load revision + integrity hash/identity checks
       _build_relationship_views
         _aggregate_active_edge_support
           _assert_active_edge_assertions_agree  ← FAILS HERE
  → Plan / Ingest / Build / Graph Review / Hermes consumers
```

### Stage notes

| Stage | Owning modules | Dedup / identity | Validation | Temporal | Supersession |
| --- | --- | --- | --- | --- | --- |
| Extraction packaging | `candidate_graph_to_contribution.py` | edge_id from predicate triple; assertion_id from full semantic hash | promote mapping states | session stamps for non-stable domains | none |
| Contribution merge | `contribution_merge.py` | same edge_id merges evidence/sessions; new assertion_id gets new support row | **nodes only** refuse disagreeing active | additive session_ids | via supersede API |
| Rebuild | `contribution_rebuild.py` | replays ledgers onto baseline | **no** edge/node refuse when called without root/world_id | same as merge | replays superseded/retracted removals |
| Publish | world supergraph revision writers | content-addressed revision id + payload hash | structural integrity | stored as serialized | N/A |
| Projection | `world_projection.py` | groups supports by `graph_object_id` | **edge (+ node) semantic agreement** | session stamps stripped from edge core fp | only sees remaining actives |
| Hermes / surfaces | live UI + retrieval | consume projection | inherit projection fail-closed | focus overlays | N/A |

---

## 8.5 Nine-edge forensic inventory

**Definitions used in this table**

- **Multi-active:** ≥2 distinct active `assertion_id`s with `support_state=supported` and non-empty `active_contribution_ids` for one `graph_object_id`.
- **Fingerprint-disagree:** `_edge_core_semantic_fingerprint` yields >1 distinct fingerprint across those active assertions.
- **First grouping point:** `_apply_edge_assertion` / `_add_support` under shared `edge_id` (unless noted).

All nine multi-active edges at head `rev:5017a201…`:

### Table

| Durable edge ID | Source | Target | Active assertion IDs | Labels (per assertion) | Direction | Evidence (minimal) | Source anchors | Contributions (active) | Temporal scope | First grouping point | Classification | Confidence | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `edge:pc:baergrom:serves:pc:caelynn` | `pc:baergrom` / Baergrom | `pc:caelynn` / Caelynn | `assertion:134135a4f3a2487b`, `assertion:b6ec355852102812` | `serves`; `revives` | outbound; outbound | S10: “Bargrom uses a health potion on Caelynn…”; S12: “Baergrom revives Caelynn with a potion…” | `…session-10…paragraph:009`; `…session-12…span:7184000a8cfb:29-29` | `contribution:2807888820d76c78` (S10 recap, active); `contribution:9080eb4963640ec5` (S12 recap, active; supersedes `dba1…`) | session-10; session-12 | Merge/rebuild by `edge_id` from predicate `serves` | **unsupported extraction label** + **separate valid events** + **reconciliation/identity collision** + **active-state overload** | High | **Sole fingerprint-disagree; sole current 409 cause.** Both predicates=`serves`. Label≠predicate on S12. |
| `edge:pc:baergrom:member_of:node:heroes-party` | Baergrom | Heroes / party | `48cbd6a2656f9304`, `4fd0705f3f0dcdad`, `f62ab4fe4543353b` | identical long label (“…responding heroes / party”) ×3 | outbound | party-registry standing + recap re-attest | `artifact:party-registry:longmont-c1`; also recap S1/S5 contribs | `75a840…` (standing, S3), `dac556…` (standing, S4), `f2fbbf…`+`66f983…` share assertion `f62ab4…` | session-3; session-4; none | same edge_id `member_of` | **duplicate fact with vocabulary-stable re-attestation** (not label drift) | High | Fingerprints **agree**. Not a projection failure. |
| `edge:pc:bonogo:member_of:node:heroes-party` | Bonogo | Heroes / party | `22dc0d2bef0bb95c`, `5a656d83bf6bb1dc`, `68f514dd58b39d40` | identical ×3 | outbound | same pattern | party-registry + recaps | standing S3/S4 + shared extraction assertion | session-3/4/none | same | re-attestation (agree) | High | Fingerprints agree. |
| `edge:pc:caelynn:member_of:node:heroes-party` | Caelynn | Heroes / party | `3c165921c0d19d8e`, `d7ad611ea263e858`, `edd92a04138ddcad` | identical ×3 | outbound | same pattern | party-registry + recaps | standing + extraction | session-3/4/none | same | re-attestation (agree) | High | Fingerprints agree. |
| `edge:pc:ephanna:member_of:node:heroes-party` | Ephanna | Heroes / party | `4beae8688066c860`, `f12c853e9f32860f`, `fdc46149dda44355` | identical ×3 | outbound | same pattern | party-registry + recaps | standing + extraction | session-3/4/none | same | re-attestation (agree) | High | Fingerprints agree. |
| `edge:pc:karsemine:member_of:node:heroes-party` | Karsemine | Heroes / party | `07398b785e7b591e`, `4e12d2875b05a7b7`, `8e6362d763d266f0` | identical ×3 | outbound | same pattern | party-registry + recaps | standing + extraction | session-3/4/none | same | re-attestation (agree) | High | Fingerprints agree. |
| `edge:pc:stafl:member_of:node:heroes-party` | Stafl | Heroes / party | `2c2afb277ec01c31`, `36c64a92268c8e48`, `c39ade04909d519f` | identical ×3 | outbound | same pattern | party-registry + recaps | standing + extraction | session-3/4/none | same | re-attestation (agree) | High | Fingerprints agree. |
| `edge:pc:bonogo:attacks:node:wolf` | Bonogo | Wolf | `129c2a91f507d6d9`, `6cad9cdc72e63ab9`, `7466f79256f416f0` | `attacks` ×3 | outbound | combat attacks across S11/S12/S17 | recap artifacts session-11/12/17 | `97f5ef…`, `9080…`, `55047…` | session-11/12/17 | same edge_id `attacks` | **separate valid events** collapsed to one durable edge; fingerprints agree via session-strip | High | Legal under current gate; architecture smell for event vs relationship. |
| `edge:pc:bonogo:carries:item:session17:dagger` | Bonogo | dagger | `4941dcb3bee2cc2a`, `67563798aa200a5d` | `carries` ×2 | outbound | carries attestations | S12 and S17 recap artifacts | `9080…` (S12), `55047…` (S17) | session-12; session-17 | same edge_id | **reconciliation/identity collision risk** (S12 assertion targets `item:session17:dagger`) + re-attestation | Medium | Fingerprints agree. Item id encodes session-17 while one assertion is session-12 — suspicious packaging. |

### Failing edge — expanded evidence

**Assertion A — `assertion:134135a4f3a2487b`**

- Contribution: `contribution:2807888820d76c78` (`source_extraction`, produced `2026-07-22T02:33:40Z`, status `active`, supersedes `None`)
- Label/predicate: `serves` / `serves`
- `value.edge_id`: `edge:pc:baergrom:serves:pc:caelynn`
- Evidence excerpt (run span):  
  `out/graph_memory/runs/longmont-c1/session-10/20260722T023048Z/source_spans/recap_paragraph_009.md`  
  > The party pushes the attack now. … Caelynn is knocked unconscious … **Bargrom uses a health potion on Caelynn**, …

**Assertion B — `assertion:b6ec355852102812`**

- Contribution: `contribution:9080eb4963640ec5` (`source_extraction`, produced `2026-07-27T20:03:43Z`, status `active`, supersedes `contribution:dba1d85c7eeae8b5`)
- Label/predicate: `revives` / `serves` (**label ≠ predicate**)
- Same `value.edge_id`
- Evidence excerpt:  
  `…/session-12/…/source_spans/recap_paragraph_007.md`  
  > **Baergrom revives Caelynn with a potion** then hits and kills another guard …

**Observed classification of the prose (high confidence):** both passages describe discrete combat heal/revive **events**, not a durable “Baergrom serves Caelynn” relationship. Predicate `serves` is not entailed by either excerpt; S12 free-text label `revives` matches the prose but was forced onto the `serves` edge identity.

### Related non-multi-active anomaly (not in the nine)

`contribution:9080…` also contains `assertion:809518e50178f15c` with `label=revives`, `predicate=serves`, edge `edge:pc:karsemine:serves:pc:stafl`. Only one active support — does not trip the multi-active gate, but shows the same label/predicate packaging pattern.

---

## 8.6 Conflict classification

| Category | Count among the nine | Which |
| --- | ---: | --- |
| Fingerprint-disagree (projection-breaking) | **1** | `baergrom:serves:caelynn` |
| Multi-active but fingerprint-agree | **8** | six `member_of` + `attacks` + `carries` |
| unsupported extraction label | 1 (primary) | failing edge (predicate `serves` vs heal/revive prose) |
| separate valid events | 1 primary + 1 architectural pattern | failing edge; also `attacks` (agreeing) |
| duplicate / re-attestation | 6 | all `member_of` heroes-party |
| reconciliation / identity collision | 1–2 | failing edge; possible `carries` session17 id from S12 |
| genuine world contradiction | **0** found | no evidence Baergrom both does and does not serve Caelynn as standing fact |
| direction error | 0 | all outbound |
| legacy schema/migration artifact | partial | restored head support collapse + stale field (Incident A); not the label disagreement itself |
| unclear | low residual | exact extraction prompt/ontology path that chose `relationship_type=serves` |

**Mixed case:** the failing edge is simultaneously an extraction/ontology error, an event/relationship conflation, an identity collision (label out of key), and an active-state overload (two session events both “active support”).

---

## 8.7 Hypothesis assessment

### H1 — Endpoint-pair identity collision

**Partially supported.**

- Edge key is endpoints **plus predicate**, not endpoints alone.
- Label is absent from durable edge key but present in projection fingerprint.
- Expected evidence matched for the failing edge: unlike labels reconcile into one `edge_id` because predicates match (`serves`).

### H2 — Event and relationship conflation

**Supported.**

- No separate durable “event edge” type; events appear as nodes (`event:…`) and/or ordinary edges with event-like predicates (`attacks`, `revives` via label, etc.).
- Repeated event predicates (`attacks` across sessions) share one edge; session stamps are additive.
- Current-state projection cannot distinguish “standing relationship” from “historical combat event” once both are active edge supports.

### H3 — Extraction or normalization error

**Supported** for the failing edge (high confidence on entailment; medium on mechanism).

- S10 “uses a health potion” does not entail predicate/label `serves`.
- S12 “revives” matches label `revives` but was packaged with `predicate=serves` / `edge_id=…:serves:…`.
- `candidate_graph_to_contribution` sets `predicate` from `relationship_type` and `label` separately; edge_id follows predicate.
- Same packaging appears again on `karsemine:serves:stafl` (label `revives`).

### H4 — Active-state semantic overload

**Supported.**

- Active ≈ accepted + contribution not superseded/retracted + listed in `active_contribution_ids`.
- No separate current/historical activation.
- Historical session events remain active indefinitely unless contribution-level supersession removes them.

### H5 — Validation-boundary mismatch

**Supported (strong).**

| Stage | Co-active edge semantic agreement enforced? |
| --- | --- |
| Contribution merge | **No** (node refuse only, and only when `root`+`world_id` passed) |
| Rebuild | **No** (`apply_accepted_assertions` without root/world_id) |
| Union validate | structural / lineage — **no** fingerprint check |
| Publish / integrity hash | bytes/identity — **no** semantic agreement |
| Projection | **Yes** — fails closed |

A revision can exist that never projects.

### H6 — Temporal change without scoped supersession

**Partially supported.**

- Failing case is less “state change of one relationship” and more “two discrete events wrongly sharing one relationship edge.”
- Still true that later contribution did not supersede the earlier one on the same edge; only contribution-local supersession (`9080` supersedes `dba1`) occurred.

### H7 — Legacy data admitted under an older contract

**Partially supported / mixed.**

- Edge agreement gate landed `4d137f6a` (2026-07-19).
- Failing contributions dated 2026-07-22 and 2026-07-27 — **after** the gate existed — so this is not “pre-gate legality” for those writes.
- Gate never ran at write time anyway (H5), so later strictness at projection is the detector, not a post-hoc invalidation of a previously legal publish path.
- Restored-head support collapse + stale `per_contribution_assertion_ids` **are** legacy/migration artifacts (Incident A).

### Additional hypothesis H8 — Label/predicate split packaging

**Supported.**

- System allows `label != predicate`.
- Edge identity follows predicate; projection treats label as invariant among co-active supports.
- This alone can create projection-breaking states even when endpoints and predicates agree.

---

## 8.8 Validation-boundary analysis

```text
ingest / contribution create  → admits label≠predicate; hashes distinct assertion_ids
union reconciliation / merge  → merges by edge_id; accumulates support rows; refuses disagreeing NODES only
rebuild                       → replays ledgers; publishes new head; still no edge refuse
structural integrity          → hash/revision identity OK on rev:5017a201…
projection                    → compares edge core fingerprints including label → 409
Hermes / Graph Review / Plan  → cannot load projection payload
```

**Structural integrity ≠ semantic projection integrity.** Rebuild proved structural equivalence counts and content-addressing; it did not prove projectability.

**Why earlier stages “passed”:** they were never asked the question projection asks. There is no shared invariant function used by merge and projection for edges.

---

## 8.9 Product and architecture implications

| Surface | Implication |
| --- | --- |
| Hermes unioned-graph querying | Hard-blocked on projection read for this world head |
| Graph Review | Post-confirm / committed projection reads fail closed |
| Ingest | Can still write contributions; may deepen multi-active edge sets without detection |
| Build | Graph context loads that use projection fail |
| Plan | Plan surface status shows projection error (observed user report) |
| Threat publication / binding | Depends on healthy graph context for grounded ThreatDraft provenance (`R0-B`); blocked |
| Placement / combat import | Not directly this bug, but any path that needs projected relationship views is blocked |
| Future generated object types | Same edge identity + active-support model will re-hit this whenever label/predicate diverge or events share relationship edges |

`R0-A` (statblock Workbench live dependency) remains independently dogfoodable.

---

## 8.10 Decision points for the next design phase

These are **questions**, not recommendations.

1. **Durable edge identity:** Should `label` participate? Should event-like predicates include session/event identity in the edge key?
2. **Event vs relationship:** Are `attacks` / `revives` / heal events durable edges, event nodes with participation edges, or time-scoped observations?
3. **Label vs predicate:** Is `label` display-only, a synonym, or a correction-sensitive semantic field? If display-only, why is it in the projection fingerprint and assertion hash?
4. **Active vs historical:** Should “active support” mean current world truth, or accepted history available to retrieval?
5. **Temporal scope:** When are session stamps additive observations vs distinct facts?
6. **Contradiction vs multiplicity:** When do unlike co-active assertions contradict, and when do they accumulate?
7. **Write-time vs read-time enforcement:** Should merge/rebuild share projection’s edge invariant (symmetric to nodes)?
8. **Supersession policy:** Can a later contribution supersede earlier assertions on the same edge without superseding the whole prior contribution?
9. **Migration:** For `rev:5017a201…`, is the fix data curation, a new publish after ontology repair, projection tolerance, or a model change — and in what order?
10. **Extraction ontology / abstention:** Should heal/revive prose be allowed to mint `predicate=serves`? Should extractors abstain or force event typing?
11. **Backlog accuracy:** Update the `[READY]` backlog entry that currently overclaims “9 edges … labels differ.”

---

## 8.11 Evidence appendix

### Graph revisions

| Revision | Role |
| --- | --- |
| `rev:2a72ef7a40ba37bc33e3f2680d528970` | Restored transfer head; stale support field; collapsed support row for serves assertions |
| `rev:5017a20164555f11d4508f67661058f1` | Current clean head after `rebuild_from_contributions(publish=True)` |
| Baseline referenced by rebuild report | `rev:fd3e0a2b96a7a5919a02a8905e73f7b9` |

### Commands used (read-only except prior approved publish, already done)

```bash
# Inventory + fingerprints
uv run python - <<'PY'
# script written during investigation; outputs MULTI_ACTIVE=9, FINGERPRINT_DISAGREE=1
PY

# Live reproduction
curl -s -X POST http://127.0.0.1:8000/api/live/world-graph/projection \
  -H 'Content-Type: application/json' \
  -d '{"schema":"dmb_world_graph_projection_request_v1","world_id":"eldyrwild","campaign_id":"longmont-c2","scope_mode":"campaign","focus":{"kind":"none","session_id":null},"admissibility":"gm"}'
# → 409 projection_integrity_error; diagnostic names edge:pc:baergrom:serves:pc:caelynn
```

### Key files / functions

- `src/graph_memory/evidence/assertion_support.py` — `DurableAssertionSupport`
- `src/graph_memory/kernel/contributions.py` — `compute_assertion_id`, `semantic_assertion_value`
- `src/graph_memory/candidate_graph_to_contribution.py` — edge packaging ~520–580
- `src/graph_memory/kernel/contribution_merge.py` — `_apply_edge_assertion`, `apply_accepted_assertions`, `_refuse_disagreeing_active_node_assertion`, `supersede_graph_contribution`
- `src/graph_memory/kernel/contribution_rebuild.py` — `rebuild_from_contributions`
- `src/graph_memory/kernel/world_projection.py` — `_edge_core_semantic_fingerprint`, `_assert_active_edge_assertions_agree`, `_aggregate_active_edge_support`, `_build_relationship_views`
- `tests/test_edge_core_semantic_fingerprint.py`
- `Docs/Reports/PR006B-SEMANTIC-ASSERTION-IDENTITY-REPAIR.md` (intent; understates projection session-strip exception)
- `Backlog.md` `[READY] Active-edge semantic disagreement…` (overclaims 9 label-differing edges)
- `Backlog-DONE.md` `[DONE] Restored Eldyrwild graph head migrated…`

### Key IDs

- Edge: `edge:pc:baergrom:serves:pc:caelynn`
- Assertions: `assertion:134135a4f3a2487b`, `assertion:b6ec355852102812`
- Contributions: `contribution:2807888820d76c78`, `contribution:9080eb4963640ec5`, superseded `contribution:dba1d85c7eeae8b5`
- Gate commit: `4d137f6a` (2026-07-19)

### Mutations performed during this investigation

**none**

(Prior session already published `rev:5017a201…`; this investigation did not republish, edit contributions, edit corpus, or change code.)

---

## Stop-condition check

| Condition | Status |
| --- | --- |
| Nine multi-active edge IDs recoverable | Yes |
| Contribution ledgers present | Yes |
| Source anchors resolvable for failing edge | Yes (run span files + corpus recaps) |
| Restored + rebuilt revisions inspectable | Yes |
| External service required | No (local store + optional live API reproduce) |
| Nondeterministic identity | Not observed; assertion ids recompute stably |
| Would require mutation to proceed | No |

Investigation complete under §11 acceptance criteria, with the explicit correction that “nine conflicting edges” means **nine multi-active edges**, of which **one** is projection-breaking under the current fingerprint.
