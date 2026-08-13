# HANDOFF — CUTOVER classify identity lifecycle shadow state after PR #571

**Created:** 2026-08-12  
**Status:** DONE — merged as PR #575 at `d32c244e8505b2d35d1aa536f6ef6cc097d735ce`; cumulative review cycles = 3  
**Workstream:** CUTOVER  
**Repository:** `Drakosfire/DungeonMindBuddy`  
**Direction:** DESIGN → CODE  
**Suggested PR title:** `CONFORMANCE: classify identity lifecycle state as migration history`  
**Suggested branch:** `cutover/classify-identity-lifecycle-history-after-571`

---

# 0. Steward anchor

> **Do not turn Buddy identity bookkeeping into DungeonMind world-property assertions. Prove the 28 current ATTRIBUTE_ASSERTION paths are reconstructable identity-lifecycle shadow state, classify only the proven paths as SOURCE_MIGRATION_HISTORY, preserve the separate IDENTITY_HISTORY adoption blocker, remeasure, and let the refreshed ledger choose the next slice.**

This is a non-publishing CUTOVER conformance slice.

It is not:

- a graph repair;
- a property-vocabulary PR;
- an identity replay implementation;
- an adoption transaction;
- a relationship cleanup;
- a source rewrite;
- an authority switch.

The purpose is to stop treating identity transaction bookkeeping as fictional-world attributes.

---

# 1. Why this PR exists

Buddy PR #571 re-pinned CUTOVER to DungeonMind PR #30 and produced the first post-`dnd5e:thread` blocker ledger.

That report is now the immediate CUTOVER authority.

It proved:

```text
WORLD_OBJECT_KIND = 0

ATTRIBUTE_ASSERTION = 28
EVIDENCE_PROVENANCE = 8

migration RELATIONSHIP_PREDICATE = 5
  blocking_stage = adoption_package_construction
  ownership_scope = cross_repository

IDENTITY_HISTORY = 14
  blocking_stage = durable_adoption

DURABLE_ADOPTION_BOUNDARY = 1
POSTGRES_ADOPTION = 1

cutover_disposition = CUTOVER_NOT_READY

next_slice =
  CASE_C
  repository = DungeonMindBuddy
  basis = ATTRIBUTE_ASSERTION
```

The old normalized recommendation text says:

```text
Materialize attribute values or document DM assertion transport.
```

That is only a generic blocker instruction.

The actual 28 paths must be understood before choosing materialization.

The current report's durable state-family inventory shows exactly:

```text
node.state.last_identity_decision_id = 14
node.state.merged_into               = 7
node.state.identity_state            = 7
                                         --
                                         28
```

The representative ATTRIBUTE_ASSERTION examples are already from those families:

```text
node:item:session11:council-headquarters:state:last_identity_decision_id
node:item:session11:council-headquarters:state:merged_into
node:item_enormous_boulder:state:last_identity_decision_id
node:item_enormous_boulder:state:merged_into
node:item_foot_of_statue:state:identity_state
```

This is a strong diagnosis, but it is not yet sufficient proof.

The PR MUST establish exact durable-element set equality before changing classification:

```text
current ATTRIBUTE_ASSERTION element IDs
==
validated identity-lifecycle shadow element IDs
```

If that equality does not hold, STOP.

---

# 2. Exact authority pins

## 2.1 Buddy base

Current `DungeonMindBuddy/main` at handoff creation:

```text
9d5efb7eaa92a4890bd49db45130e5843777c8b9
```

This is Buddy PR #571 merge:

```text
PR #571
CONFORMANCE: re-pin CUTOVER to DungeonMind world-object-v5
```

BUILD should branch from this exact commit or a later `main` descendant that preserves the pinned CUTOVER/source inputs.

If `main` advances:

1. sync/rebase;
2. re-run stale-input checks;
3. verify #571 fixture bytes;
4. do not silently update expected world/source authority.

## 2.2 DungeonMind semantic authority

Remain pinned to:

```text
DungeonMind PR #30 merge:
be76acc997c5fbcb8ceaa090969ec051afa6051d
```

Contracts remain:

```text
world-object-v5
f9fd5420e0ab3849224e0d58cf83dd432ca2e5da22ce661b25654406ec9c60d8

world-property-v3
aa94df78c10a913e7ca6774198f080131f8f447c90cc917b9b840ed88bd856e4

dnd5e-profile-v3
2199e8fb96e917c22718e6aec59cbbf55a37ee81575e1bcf16ce13fae0393496

graph schema
dm_union_graph_v5
```

No DungeonMind dependency update is expected.

## 2.3 Canonical Eldyrwild authority

Keep exact:

```text
world_id:
eldyrwild

canonical revision:
rev:5a7c13ae45c49a65b402920499be72ed

canonical graph payload SHA-256:
2632870ef70638969503de788cfdec97acd490875deff3e2630ac91dc96fe974
```

## 2.4 #566 migration projection

Keep exact repair authority:

```text
repair id:
eldyrwild-relationship-node-kind-source-repair-v1

manifest SHA-256:
96cc26fc6e99448e8fba5cd6982070c1e29bb058f2b1e8a4ac291f8a0a083247
```

Projection remains exactly four kind paths.

This PR changes no projected source value.

## 2.5 PR #571 historical fixture

Immediate predecessor fixture:

```text
tests/fixtures/dungeonmind_kernel/
eldyrwild_cutover_repin_after_dm30_v1.json
```

Locked SHA-256:

```text
a666a2bc0d7fabe7a8b66e1dc93698a29bb911efede7c3089df28887477c13b5
```

This fixture is immutable.

PR #571 behavior must remain independently reproducible.

## 2.6 Older #568 fixture

Also preserve:

```text
eldyrwild_cutover_reanchor_after_566_v1.json

SHA-256:
6c978f89527ccd82e9bad32eac70a5386a5d714e80f7e426f574d7dbc0e43cbf
```

Do not rewrite historical measurement artifacts.

---

# 3. Source-derived diagnosis

## 3.1 Current state classifier

Current `whole_world_conformance_v4.py` already treats these node-state fields as migration history:

```text
approval_state
memory_state
support_state
identity_canon_state
introduced_by_contribution_id
```

They return:

```text
SemanticClassification.SOURCE_MIGRATION_HISTORY
blocker = None
```

But the current fallback for any other node-state field is:

```text
DUNGEONMIND_SEMANTIC_CONTRACT_GAP
ATTRIBUTE_ASSERTION
"unclassified state field ..."
```

Therefore these identity lifecycle keys currently fall through:

```text
identity_state
merged_into
last_identity_decision_id
```

The next PR should resolve that classification seam.

## 3.2 Buddy identity merge semantics

Buddy's durable identity merge implementation establishes the source semantics.

For a successful merge:

### survivor / target node

The target receives:

```text
identity_state = "survivor"
identity_canon_state = "canonical"
last_identity_decision_id = <merge decision id>
```

### merged-away / source node

The source receives:

```text
memory_state = "merged_away"
identity_canon_state = "merged_away"
merged_into = <target node id>
last_identity_decision_id = <merge decision id>
```

### durable redirect

The merge also creates an identity redirect:

```text
redirect_id = "redirect:" + decision_id
from_node_id = source
to_node_id = target
status = active
```

and appends the durable identity decision record.

Thus:

```text
identity_state
merged_into
last_identity_decision_id
```

are not independent claims such as:

```text
"the castle is ruined"
"the NPC is a captain"
"the item weighs 4 lb"
```

They are read-model shadow state produced by an identity transaction.

## 3.3 DungeonMind property semantics

DungeonMind `dm_union_graph_v5` accepts independently durable property assertions:

```text
property_term
value
KnowledgeAssertionMetadataV1
```

Those properties are assertion-grain world knowledge.

The identity lifecycle shadow fields above do not become world knowledge merely because their JSON values could fit inside a generic property `value`.

Do NOT manufacture terms such as:

```text
dnd5e:merged_into
dnd5e:last_identity_decision_id
dnd5e:identity_state
```

Do NOT create generic property assertions solely to clear the counter.

Identity history belongs to the identity adoption/replay path.

---

# 4. Architectural decision

## Decision

Classify these fields as:

```text
SOURCE_MIGRATION_HISTORY
```

**only when a new exact identity-lifecycle proof demonstrates that the stored field is reconstructable from Buddy's durable identity decision / redirect authority.**

Do not classify by field name alone.

Do not classify by count alone.

Do not classify by a hardcoded Eldyrwild element-ID allowlist alone.

The proof is the authority.

## Why SOURCE_MIGRATION_HISTORY

This disposition means:

```text
preserve/history matters
but
this is not an independently materialized DungeonMind world assertion
```

That is exactly the distinction already used for:

```text
approval_state
memory_state
identity_canon_state
introduced_by_contribution_id
```

The durable adoption obligation does not disappear.

It remains represented by:

```text
IDENTITY_HISTORY
```

which must remain a blocker at:

```text
blocking_stage = durable_adoption
```

This PR moves the 28 shadow fields out of the wrong blocker class.

It does not declare identity adoption solved.

---

# 5. Mission

Implement one non-publishing Case C successor that:

1. reproduces PR #571 exactly before doing new work;
2. inventories all current `ATTRIBUTE_ASSERTION` classified elements at durable-element level;
3. constructs a deterministic identity-lifecycle shadow proof from the exact loaded Buddy store;
4. proves the current 28 ATTRIBUTE_ASSERTION paths are exactly the validated shadow paths;
5. proves those fields are reconstructable from durable identity decision / redirect records;
6. adds a successor analysis policy that classifies only proven shadow paths as `SOURCE_MIGRATION_HISTORY`;
7. preserves the PR #571 analyzer behavior as historical/default behavior;
8. re-runs canonical + #566 migration projection;
9. proves `ATTRIBUTE_ASSERTION` clears without source mutation;
10. proves `IDENTITY_HISTORY` remains;
11. proves relationships remain unchanged;
12. seals a deterministic successor fixture;
13. derives the next slice from the refreshed migration ledger.

---

# 6. Non-goals

Do not:

- edit any Eldyrwild node state;
- delete identity shadow keys;
- alter identity decisions;
- alter identity redirects;
- alter identity merge records;
- replay identity into DungeonMind;
- add DungeonMind identity APIs;
- add DungeonMind property terms;
- add Buddy property assertions;
- add evidence for these bookkeeping fields;
- modify relationship residuals;
- resolve the five dual-sense STOPs;
- start governed existing-world adoption;
- exercise Postgres adoption;
- switch Buddy reads or writes to DungeonMind;
- demolish Buddy authority;
- broaden into general identity cleanup.

---

# 7. Exact identity-lifecycle proof contract

Create one reusable diagnostic/proof surface.

Recommended module:

```text
apps/live_control_server/integrations/dungeonmind_kernel/
identity_lifecycle_history_conformance_v1.py
```

Recommended schema:

```text
dmb_identity_lifecycle_history_conformance_v1
```

## 7.1 Recommended row

Example shape:

```python
class IdentityLifecycleShadowRowV1(BaseModel):
    element_id: str
    node_id: str
    field: Literal[
        "identity_state",
        "merged_into",
        "last_identity_decision_id",
    ]
    stored_value: Any
    decision_id: str
    decision_kind: str
    decision_status: str
    subject_node_id: str | None
    target_node_id: str | None
    redirect_id: str | None
    redirect_status: str | None
    lifecycle_role: Literal["merge_source", "merge_survivor"]
    reconstructable: bool
    rationale: str
```

Exact model names may follow local conventions.

Required semantics are normative.

## 7.2 Recommended report

```python
class IdentityLifecycleHistoryConformanceV1(BaseModel):
    schema_: Literal["dmb_identity_lifecycle_history_conformance_v1"]
    world_id: str
    canonical_revision_id: str
    canonical_graph_payload_sha256: str
    rows: list[IdentityLifecycleShadowRowV1]
    field_counts: dict[str, int]
    element_ids: list[str]
    reconstructable_count: int
    unresolved_element_ids: list[str]
    passed: bool
```

---

# 8. Proof algorithm

The proof MUST use the loaded durable store.

It must not infer truth from PR fixture prose.

## 8.1 Index durable identity decisions

Build an exact map:

```text
decision_id -> identity decision record
```

Fail closed on duplicate decision IDs.

Every lifecycle-shadow decision pointer must resolve.

## 8.2 Index current redirects

Build exact current redirect information from:

```text
store.identity_redirects
```

Respect redirect status.

Do not treat a retracted redirect as current identity routing.

## 8.3 Candidate shadow fields

Candidate fields are only:

```text
identity_state
merged_into
last_identity_decision_id
```

Collect their exact durable element IDs from the loaded store.

Before classification change, expected current field-family counts are:

```text
identity_state             7
merged_into                7
last_identity_decision_id 14
                           --
                           28
```

If counts differ at the pinned source, STOP and report stale source / unexpected identity state.

## 8.4 `last_identity_decision_id` proof

For every node carrying:

```text
last_identity_decision_id = X
```

require:

1. `X` is a nonblank string;
2. `X` resolves to exactly one durable identity decision;
3. the node is named by that decision as subject, target, or affected node as appropriate;
4. the decision semantics explain the node's current lifecycle shadow role;
5. no guessed decision ID is created.

Current source is expected to be merge lifecycle state.

If a split/unmerge or another decision kind is encountered, do not silently admit it under the merge proof.

Either:

- prove it explicitly in this PR if the exact current 28 require it; or
- STOP and narrow the disposition.

## 8.5 `merged_into` proof

For every node carrying:

```text
merged_into = TARGET
```

require:

1. `TARGET` is an existing node ID;
2. node has a resolvable `last_identity_decision_id`;
3. that decision is a merge whose:
   - `subject_node_id == node.node_id`
   - `target_node_id == TARGET`;
4. current identity redirect authority agrees:
   - `from_node_id == node.node_id`
   - `to_node_id == TARGET`;
5. no conflicting active redirect exists;
6. source lifecycle fields are consistent with merged-away state:
   - `memory_state == "merged_away"`
   - `identity_canon_state == "merged_away"`.

Do not alter those fields.

## 8.6 `identity_state` proof

For every current candidate:

```text
identity_state = VALUE
```

the proof must validate its exact stored value.

Expected merge-survivor shape from Buddy's merge implementation is:

```text
VALUE == "survivor"
```

and requires:

1. resolvable `last_identity_decision_id`;
2. decision kind is merge;
3. `target_node_id == node.node_id`;
4. node is the surviving target of that decision;
5. `identity_canon_state == "canonical"`.

If any current value is not `survivor`, STOP rather than broadening semantics by assumption.

## 8.7 Reconstruction proof

The strongest acceptance criterion is not merely referential validity.

Construct the expected shadow values from durable identity authority and compare to stored values.

At minimum prove:

```text
stored merged_into
==
decision/redirect target

stored last_identity_decision_id
==
the decision that produced the currently materialized lifecycle shadow

stored identity_state
==
the role implied by the proven current merge lifecycle
```

The proof must report:

```text
reconstructable = true
```

for every admitted shadow field.

No field may be reclassified solely because its name is in an allowed set.

---

# 9. Exact blocker-set equality

PR #571 added full durable classified-element capture.

Use it.

Before new classification policy, compute:

```text
ATTRIBUTE_ASSERTION element IDs
```

from the exact PR #571-compatible v5 analysis.

Then compute:

```text
identity lifecycle proven element IDs
```

from §7–8.

Acceptance requires:

```text
attribute_assertion_ids
==
identity_lifecycle_proof.element_ids
```

and:

```text
len(...) == 28
```

This is the activation gate.

If there is even one:

- ATTRIBUTE_ASSERTION not explained by identity history; or
- identity shadow field not in ATTRIBUTE_ASSERTION;

STOP and report the discrepancy.

Do not partially green the ledger.

---

# 10. Historical behavior must remain reproducible

This is critical.

Do not simply change `_classify_state_field_v4()` so every historical report suddenly becomes greener.

PR #571 must continue to reproduce its locked bytes.

## Required design

Add an explicit successor source-history classification policy.

Historical/default analysis stays unchanged.

A recommended internal shape:

```python
@dataclass(frozen=True, slots=True)
class WholeWorldSourceHistoryPolicy:
    policy_id: str
    proven_node_state_history_element_ids: frozenset[str]
```

with:

```text
LEGACY_SOURCE_HISTORY_POLICY
```

as the default.

The new successor uses a policy produced only from the verified identity-lifecycle proof.

Alternative local designs are acceptable if they preserve these invariants:

1. old `analyze_exact_buddy_world_revision_v5()` behavior stays byte-stable;
2. PR #571 fixture still verifies;
3. new behavior is explicitly selected;
4. no "latest"/"default successor" inference;
5. no arbitrary post-processing of blocker rows;
6. classification changes occur during durable-element classification.

## Do not

Do not:

```text
remove ATTRIBUTE_ASSERTION from normalized blocker ledger after analysis
```

Do not:

```text
subtract 28 from the count
```

Do not:

```text
filter element IDs after report composition
```

The classifier itself must emit:

```text
SOURCE_MIGRATION_HISTORY
blocker = None
```

for proven lifecycle-shadow paths.

---

# 11. Recommended analyzer hook

One bounded option is to extend the loaded-store analyzer with an explicit source-history policy:

```python
def _analyze_loaded_buddy_world_store_v4(
    ...,
    target: WholeWorldTargetContract = HISTORICAL_V4_TARGET,
    source_history_policy: WholeWorldSourceHistoryPolicy = LEGACY_SOURCE_HISTORY_POLICY,
    classified_out: list[ClassifiedElement] | None = None,
) -> WholeWorldConformanceReportV4:
```

For each node state element:

```python
element_id = ...
if element_id in source_history_policy.proven_node_state_history_element_ids:
    classification = SOURCE_MIGRATION_HISTORY
    blocker = None
    note = (
        "validated identity lifecycle shadow; durable authority is the "
        "identity decision/redirect history, not a world-property assertion"
    )
else:
    classification = legacy classifier(...)
```

The policy constructor must only accept the output of the proof, or revalidate it.

Do not expose a convenient public API that lets arbitrary callers mark arbitrary durable elements as migration history.

If the implementation can make the type relationship stronger, do so.

---

# 12. New CUTOVER successor report

Create a successor service rather than replacing PR #571's artifact.

Recommended path:

```text
apps/live_control_server/services/
cutover_identity_lifecycle_history_after_571.py
```

Recommended schema:

```text
dmb_cutover_identity_lifecycle_history_after_571_v1
```

Recommended fixture:

```text
tests/fixtures/dungeonmind_kernel/
eldyrwild_cutover_identity_lifecycle_history_after_571_v1.json
```

The new report should include:

```text
predecessor
identity_lifecycle_proof
canonical_view
migration_projection
classification_delta
blocker_delta
relationship invariants
adoption_seam
cutover_disposition
next_slice_recommendation
```

---

# 13. Predecessor reproduction

Before composing the successor report:

1. verify PR #571 fixture exists;
2. verify exact SHA:
   `a666a2bc...`;
3. call PR #571 verifier;
4. require `verified == true`;
5. require its report still says:
   `ATTRIBUTE_ASSERTION == 28`;
6. require its thread classified-element transitions remain exact;
7. require old fixture bytes unchanged before/after.

This makes PR #571 the explicit baseline.

---

# 14. Canonical + migration views

Run both:

```text
canonical exact Eldyrwild
```

and:

```text
exact #566 four-kind in-memory migration projection
```

with the new identity-history policy.

The identity-lifecycle proof should be identical between these two views because #566 changes only four `kind` fields.

Assert:

```text
canonical identity lifecycle element IDs
==
migration identity lifecycle element IDs
```

If the four-kind projection changes any identity-lifecycle proof row, STOP.

---

# 15. Expected classification delta

The predecessor report is expected to contain exactly 28 relevant classified elements:

```text
classification:
DUNGEONMIND_SEMANTIC_CONTRACT_GAP

blocker:
ATTRIBUTE_ASSERTION
```

The successor must change those exact elements to:

```text
classification:
SOURCE_MIGRATION_HISTORY

blocker:
None
```

No other durable-element classification may change.

Seal this as an exact durable-element transition set.

Recommended report section:

```json
{
  "classification_delta": {
    "count": 28,
    "field_counts": {
      "identity_state": 7,
      "last_identity_decision_id": 14,
      "merged_into": 7
    },
    "element_ids": [],
    "transitions": [],
    "lossless": true
  }
}
```

The actual fixture must include the exact 28 IDs.

Do not truncate this list to representative examples.

---

# 16. Expected blocker outcome

If §9 and §15 hold:

```text
ATTRIBUTE_ASSERTION
28 -> 0
```

and the blocker row should disappear from both:

```text
canonical
migration projection
```

This is an authorized expected result.

It is not achieved by source mutation.

## Must remain

At minimum these must remain unchanged unless real execution proves otherwise:

```text
EVIDENCE_PROVENANCE = 8

migration RELATIONSHIP_PREDICATE = 5
  adoption_package_construction
  cross_repository
  responsible_repo = null

IDENTITY_HISTORY = 14
  durable_adoption

DURABLE_ADOPTION_BOUNDARY = 1
POSTGRES_ADOPTION = 1
```

`CONTRIBUTION_HISTORY` also remains a durable-adoption concern.

---

# 17. IDENTITY_HISTORY must not be weakened

This PR is only correct if it preserves the separate identity-history obligation.

Current analyzer computes `IDENTITY_HISTORY` from:

```text
identity_redirects
+
identity_merge_records
+
identity_decisions
```

The successor must continue to report the same exact identity-history count on the same store.

Expected pinned result:

```text
IDENTITY_HISTORY = 14
```

If the count drops because the new classifier "absorbed" identity history, STOP.

The smallest-next-change remains conceptually:

```text
Expose governed identity migration replay at adoption seam.
```

This PR does not implement that seam.

---

# 18. Relationship invariants

No relationship semantics change.

Canonical must remain:

```text
semantic: 323
represented: 314
residual: 9
uses_statblock: 3
```

Migration projection must remain:

```text
semantic: 323
represented: 318
residual: 5
uses_statblock: 3
```

The exact five migration residual IDs remain:

```text
edge:loc:central-office:located_in:node:meat_distribution_network_session9:site-of

edge:loc:packing-loading-area:part_of:node:meat_distribution_network_session9

edge:node:headmaster_tinkerbright:leads:loc:wizard_college

edge:node:hempholm_townsfolk:participates_in:node:hempholm_folk_revelry

edge:pc:caelynn:participates_in:node:hempholm_folk_revelry
```

Do not touch them.

---

# 19. Evidence blocker is separate

Do not opportunistically fix:

```text
EVIDENCE_PROVENANCE = 8
```

in this PR.

Those are alias/evidence reconstruction concerns.

Identity lifecycle classification does not authorize alias assertion reconstruction.

If the refreshed selector chooses EVIDENCE_PROVENANCE next, that becomes the next PR.

---

# 20. No-mutation proof

Snapshot before and after composition:

```text
canonical head
World Graph tree digest

contribution index
contributions
contribution rebuild

identity decision index / identity decision family
identity redirects
identity merge records

initialization
revisions

#566 repair manifest
#571 predecessor fixture
```

Assert byte/digest equality.

Particularly important:

```text
identity decisions before == after
identity redirects before == after
node state before == after
```

This PR changes classification only.

---

# 21. Stale-input refusal

Fail closed if any activation pin drifts.

At minimum:

```text
Buddy base ancestry
canonical revision
canonical payload SHA
#566 repair manifest SHA
DungeonMind dependency ref
world-object-v5 SHA
world-property-v3 SHA
profile-v3 SHA
PR #571 fixture SHA
```

Also fail closed if current source no longer has:

```text
ATTRIBUTE_ASSERTION = 28
```

or the expected state-family inventory:

```text
last_identity_decision_id = 14
merged_into = 7
identity_state = 7
```

This PR is a measured successor to a specific world state.

If that state changed, re-anchor instead of forcing the proof.

---

# 22. Source-shape refusal

The identity-lifecycle proof must fail closed on:

```text
dangling last_identity_decision_id
duplicate decision_id
dangling merged_into target
merged_into disagrees with decision target
merged_into disagrees with active redirect
multiple conflicting active redirects
identity_state value not proven by current lifecycle semantics
decision kind not covered by the proof
decision subject/target mismatch
identity_canon_state inconsistent with lifecycle role
memory_state inconsistent with merged-away source role
candidate field with no reconstructable identity authority
```

Do not silently classify malformed identity state as migration history.

---

# 23. New fixture sealing

Recommended path:

```text
tests/fixtures/dungeonmind_kernel/
eldyrwild_cutover_identity_lifecycle_history_after_571_v1.json
```

Build flow:

1. verify predecessor;
2. load exact source;
3. build identity lifecycle proof;
4. assert exact ATTRIBUTE set equality;
5. analyze canonical under successor policy;
6. analyze #566 projection under successor policy;
7. compute exact 28 transitions;
8. assert all unrelated classifications stable;
9. compute blocker delta;
10. derive recommendation;
11. prove no mutation;
12. seal deterministic fixture SHA;
13. independently reproduce fixture.

Do not invent the new SHA in this handoff.

---

# 24. Suggested implementation surfaces

Expected allowlist:

```text
Docs/Plans/HANDOFF-cutover-identity-lifecycle-history-after-571.md
Docs/Plans/PR-TRACKER-campaign-supergraph.md
Docs/Design/STATUS-world-graph-continuity-spine.md
Backlog.md

apps/live_control_server/integrations/dungeonmind_kernel/
whole_world_conformance_v4.py

apps/live_control_server/integrations/dungeonmind_kernel/
identity_lifecycle_history_conformance_v1.py

apps/live_control_server/services/
cutover_identity_lifecycle_history_after_571.py

scripts/
build_cutover_identity_lifecycle_history_after_571.py

tests/
test_identity_lifecycle_history_conformance_v1.py
test_cutover_identity_lifecycle_history_after_571.py
test_cutover_whole_world_repin_after_dm30.py

tests/fixtures/dungeonmind_kernel/
eldyrwild_cutover_identity_lifecycle_history_after_571_v1.json
```

A thin helper in another existing CUTOVER module is acceptable if it keeps the scope clearer.

No dependency files should change.

---

# 25. Explicitly forbidden surfaces

Do not modify:

```text
pyproject.toml
uv.lock

src/graph_memory/kernel/identity_decisions.py
src/graph_memory/kernel/identity_models.py

graph_data/approved_graph_corrections/eldyrwild/**

tests/fixtures/dungeonmind_kernel/
eldyrwild_cutover_repin_after_dm30_v1.json

tests/fixtures/dungeonmind_kernel/
eldyrwild_cutover_reanchor_after_566_v1.json
```

unless the implementation discovers a genuine pre-existing defect that makes this handoff invalid.

If so, STOP and report it.

Do not "fix it while here."

---

# 26. Acceptance tests

## T1 — exact Buddy predecessor

Assert current branch descends from:

```text
9d5efb7eaa92a4890bd49db45130e5843777c8b9
```

## T2 — exact DungeonMind contracts unchanged

Assert:

```text
be76acc997c5fbcb8ceaa090969ec051afa6051d

world-object-v5
f9fd5420e0ab3849224e0d58cf83dd432ca2e5da22ce661b25654406ec9c60d8

world-property-v3
aa94df78c10a913e7ca6774198f080131f8f447c90cc917b9b840ed88bd856e4

profile-v3
2199e8fb96e917c22718e6aec59cbbf55a37ee81575e1bcf16ce13fae0393496
```

## T3 — predecessor fixture exact

Assert PR #571 fixture SHA:

```text
a666a2bc0d7fabe7a8b66e1dc93698a29bb911efede7c3089df28887477c13b5
```

## T4 — predecessor verifier still passes

Assert:

```text
verify_cutover_whole_world_repin_after_dm30(...).verified is True
```

## T5 — predecessor still reports ATTRIBUTE 28

Assert old policy still returns:

```text
ATTRIBUTE_ASSERTION = 28
```

This proves the historical analyzer was not silently rewritten.

## T6 — candidate field-family inventory exact

Assert pinned canonical:

```text
identity_state = 7
merged_into = 7
last_identity_decision_id = 14
```

and total:

```text
28
```

## T7 — durable ATTRIBUTE set captured losslessly

Capture all predecessor classified elements with:

```text
blocker_class == ATTRIBUTE_ASSERTION
```

Assert:

```text
count == 28
```

Persist the exact IDs in the successor proof/fixture.

## T8 — identity proof covers exact same set

Assert:

```text
set(attribute_assertion_ids)
==
set(identity_lifecycle_proof.element_ids)
```

No subset acceptance.

No superset acceptance.

## T9 — every proof row reconstructable

Assert:

```text
unresolved_element_ids == []
reconstructable_count == 28
passed == True
```

## T10 — decision pointers resolve

Every stored:

```text
last_identity_decision_id
```

must resolve exactly once.

## T11 — merged-away sources are coherent

For every `merged_into` row, prove exact source/target agreement among:

```text
node state
identity decision
current redirect
```

and required lifecycle state.

## T12 — survivor state is coherent

For every `identity_state` row, prove the stored value and decision-target relationship.

Do not merely assert the key exists.

## T13 — adversarial dangling decision fails

Construct fixture/unit case:

```text
last_identity_decision_id = nonexistent
```

and assert fail closed.

## T14 — adversarial redirect mismatch fails

Construct:

```text
merged_into = B
decision target = B
active redirect target = C
```

and assert fail closed.

## T15 — adversarial unsupported identity_state fails

Construct e.g.:

```text
identity_state = split_from
```

under this merge-shadow policy without matching explicit proof.

Assert fail closed.

This does not claim split state is invalid globally.

It claims this PR has not proven it.

## T16 — historical policy byte-stable

PR #571 report/fixture reproduction must remain byte-identical.

## T17 — successor classifier changes exact 28 elements

Compare predecessor-v5 classified inventory to successor-v5 inventory.

Assert transition IDs equal the exact 28 identity proof IDs.

For each:

```text
previous.classification =
DUNGEONMIND_SEMANTIC_CONTRACT_GAP

previous.blocker =
ATTRIBUTE_ASSERTION

current.classification =
SOURCE_MIGRATION_HISTORY

current.blocker =
None
```

## T18 — no other classification transition

Assert:

```text
total classification transitions == 28
```

and no unrelated element ID changes classification/blocker.

## T19 — ATTRIBUTE clears

Assert both successor views have no:

```text
ATTRIBUTE_ASSERTION
```

normalized blocker row.

## T20 — IDENTITY_HISTORY remains exact

Assert:

```text
IDENTITY_HISTORY = 14
```

and:

```text
blocking_stage = durable_adoption
```

Do not change its ownership or smallest-next-change merely because shadow fields are reclassified.

## T21 — EVIDENCE_PROVENANCE unchanged

Assert:

```text
EVIDENCE_PROVENANCE = 8
```

unless actual source drift causes fail-closed re-anchor.

## T22 — relationship inventory unchanged

Canonical:

```text
323 / 314 / 9 / 3
```

Migration:

```text
323 / 318 / 5 / 3
```

Exact five migration residual IDs unchanged.

## T23 — canonical/migration identity proof identical

Assert #566 overlay does not alter any identity-lifecycle proof row or element ID.

## T24 — no source mutation

Before/after exact equality for:

```text
head
graph tree
node state
identity decisions
identity redirects
identity merge records
source/provenance authority
repair manifest
predecessor fixture
```

## T25 — stage-driven recommendation

Assert:

```text
recommendation
==
_next_slice_recommendation(actual migration blockers)
```

and:

```text
if package-construction blockers remain:
    recommendation.case != CASE_B
```

Do not hardcode the expected next class into production selection.

## T26 — CUTOVER stays not ready

Five dual-sense package-construction STOPs remain.

Therefore assert:

```text
CUTOVER_NOT_READY
```

## T27 — deterministic fixture

Build + independently reproduce the new fixture bytes.

## T28 — stale source refusal

Monkeypatch the predecessor count/field-family/proof pins and show the successor refuses to seal.

---

# 27. Expected blocker delta

If all acceptance criteria hold, the expected blocker delta is:

```text
ATTRIBUTE_ASSERTION
28 -> 0
```

and:

```text
IDENTITY_HISTORY
14 -> 14
```

The semantic meaning is:

```text
28 paths were moved from
"unexplained world-attribute gap"

to
"validated identity migration history"
```

not:

```text
28 identity facts were deleted
```

and not:

```text
28 properties were invented
```

---

# 28. Likely next dispatch — not an acceptance constant

If current evidence remains stable after ATTRIBUTE clears, the next singular Buddy package-construction blocker is likely:

```text
EVIDENCE_PROVENANCE = 8
```

with the five dual-sense relationship STOPs still cross-repository.

That would likely produce:

```text
CASE_C
DungeonMindBuddy
EVIDENCE_PROVENANCE
```

But do not encode that as the required recommendation.

The refreshed ledger decides.

Possible outcomes:

### Case C — EVIDENCE_PROVENANCE

Design the narrow alias/evidence reconstruction slice.

### Case A — cross-repository relationship package decision

Only if singular Buddy package blockers are gone and the five dual-sense STOPs become first.

### Case B — durable adoption

Still forbidden while any package-construction blocker remains.

### Case D — shadow readiness

Not expected in this slice.

---

# 29. Suggested commit sequence

### Commit 1

```text
DOCS: handoff CUTOVER identity lifecycle history classification
```

### Commit 2

```text
CONFORMANCE: prove identity lifecycle shadow state
```

Add the exact proof module and focused tests.

### Commit 3

```text
CONFORMANCE: add explicit source-history classification policy
```

Preserve legacy behavior by default.

### Commit 4

```text
CONFORMANCE: remeasure CUTOVER after identity history proof
```

Add successor service/report.

### Commit 5

```text
TEST: seal identity lifecycle CUTOVER fixture
```

Seal exact 28 classified transitions and no-mutation/stale-input proofs.

### Commit 6

```text
DOCS: record refreshed CUTOVER dispatch
```

Update tracker/status/backlog from actual ledger result.

Do not add unrelated cleanup.

---

# 30. Verification

At minimum run predecessor regressions:

```bash
uv run pytest -q \
  tests/test_cutover_whole_world_repin_after_dm30.py \
  tests/test_dungeonmind_whole_world_conformance_v5.py
```

New proof suites:

```bash
uv run pytest -q \
  tests/test_identity_lifecycle_history_conformance_v1.py \
  tests/test_cutover_identity_lifecycle_history_after_571.py
```

Retain relationship proof coverage:

```bash
uv run pytest -q \
  tests/test_eldyrwild_relationship_node_kind_source_repair.py \
  tests/test_cutover_whole_world_reanchor.py
```

Run:

```text
PR #571 verify
successor status
successor build
successor verify
```

Run Ruff over every changed Python file:

```bash
uv run ruff check <changed-python-files>
```

Run repository-required typing/tests for changed surfaces.

Finish:

```bash
git diff --check
```

The handback must report actual commands and pass counts.

---

# 31. Implementer handback

Return:

## Git identity

```text
base SHA:
head SHA:
branch:
PR:
```

## Authority pins

```text
DungeonMind ref:
world-object-v5 SHA:
world-property-v3 SHA:
profile-v3 SHA:
canonical revision:
canonical payload SHA:
#566 manifest SHA:
#571 fixture SHA:
```

## Predecessor proof

```text
#571 verifier:
#571 ATTRIBUTE_ASSERTION count:
#571 fixture unchanged:
```

## Identity lifecycle inventory

```text
ATTRIBUTE_ASSERTION total:
identity_state count:
merged_into count:
last_identity_decision_id count:

exact ATTRIBUTE element IDs:
<all 28>
```

## Identity authority proof

```text
identity decision count:
identity redirect count:
identity merge-record count:

candidate rows:
reconstructable rows:
unresolved rows:

unsupported decision kinds encountered:
redirect mismatches:
dangling decision ids:
```

## Classification delta

Return exact:

```text
element_id
previous classification
previous blocker
current classification
current blocker
proof row / rationale
```

for all 28.

## Refreshed blockers

Return:

```text
blocker_class | predecessor migration | successor migration | stage | owner
```

At minimum:

```text
ATTRIBUTE_ASSERTION
EVIDENCE_PROVENANCE
RELATIONSHIP_PREDICATE
IDENTITY_HISTORY
CONTRIBUTION_HISTORY
DURABLE_ADOPTION_BOUNDARY
POSTGRES_ADOPTION
```

## Relationship inventories

```text
canonical:
migration:
exact five residual IDs:
```

## Recommendation

```text
case:
repository:
basis:
blocking stage:
smallest next change:
cross-repository package blockers:
nonclaim:
```

## Mutation proof

```text
head before/after:
graph tree before/after:
node-state digest before/after:
identity decisions digest before/after:
identity redirects digest before/after:
identity merge records digest before/after:
source authority before/after:
#566 manifest before/after:
#571 fixture before/after:
```

## Fixture

```text
new fixture path:
new fixture SHA:
verify result:
```

## Verification

```text
ruff:
predecessor tests:
identity proof tests:
successor tests:
relationship regression:
type checks:
git diff --check:
```

---

# 32. Steward review checklist

Before merge, every answer must be YES:

- [ ] Is base anchored to PR #571 merge or a verified descendant?
- [ ] Does PR #571 fixture still reproduce exactly?
- [ ] Does the old policy still report ATTRIBUTE_ASSERTION 28?
- [ ] Are the 28 old blocker IDs captured losslessly?
- [ ] Does field-family inventory equal 14 + 7 + 7?
- [ ] Does the identity proof cover exactly those 28 IDs?
- [ ] Does every last_identity_decision_id resolve?
- [ ] Does every merged_into agree with decision + redirect authority?
- [ ] Is every identity_state value explicitly validated?
- [ ] Are all admitted fields reconstructable from durable identity authority?
- [ ] Does malformed identity state fail closed?
- [ ] Are only proven fields reclassified?
- [ ] Are exactly 28 classified elements changed?
- [ ] Are all 28 changed to SOURCE_MIGRATION_HISTORY with no blocker?
- [ ] Are there zero unrelated classification changes?
- [ ] Is ATTRIBUTE_ASSERTION absent afterward?
- [ ] Does IDENTITY_HISTORY remain 14?
- [ ] Does EVIDENCE_PROVENANCE remain separate?
- [ ] Are relationship inventories unchanged?
- [ ] Are the exact five dual-sense STOPs unchanged?
- [ ] Is there no property-vocabulary expansion?
- [ ] Are no Buddy properties/assertions invented?
- [ ] Are no identity records mutated?
- [ ] Is there no adoption transaction?
- [ ] Is there no authority switch?
- [ ] Does the successor fixture reproduce deterministically?
- [ ] Is the next recommendation derived from the actual refreshed ledger?

If any answer is NO, do not merge until the discrepancy is understood.

---

# 33. Final boundary

The current blocker label says:

```text
ATTRIBUTE_ASSERTION
```

but the source semantics say these 28 values are generated by identity operations.

The correct CUTOVER move is:

```text
prove identity authority
    ->
prove shadow reconstructability
    ->
classify shadow as migration history
    ->
preserve IDENTITY_HISTORY gate
    ->
remeasure
```

Not:

```text
see generic property gap
    ->
invent 28 DungeonMind properties
```

This PR should make the blocker ledger more semantically accurate without changing one byte of world truth.

Then let the ledger choose the next slice.
