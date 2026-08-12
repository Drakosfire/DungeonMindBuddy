# HANDOFF — CUTOVER re-pin to DungeonMind world-object-v5 after PR #30

**Created:** 2026-08-12  
**Status:** READY FOR BUILD  
**Workstream:** CUTOVER  
**Repository:** `Drakosfire/DungeonMindBuddy`  
**Direction:** DESIGN → CODE  
**Suggested PR title:** `CONFORMANCE: re-pin CUTOVER to DungeonMind world-object-v5`  
**Suggested branch:** `cutover/repin-dungeonmind-v5-after-pr30`

---

## 0. Steward anchor

> **Re-pin Buddy's CUTOVER analyzer to the exact merged DungeonMind v5/v3 semantic contracts, re-run the same Eldyrwild canonical + four-kind migration projection, prove the old #568 artifact still reproduces, and let the refreshed blocker ledger choose the next slice. Do not mutate Buddy world truth and do not start adoption work.**

This PR is a measurement/update slice.

It is not:

- a graph repair;
- a migration;
- an adoption transaction;
- an identity decomposition;
- a relationship cleanup;
- a product-authority switch.

The only authorized semantic change comes from already-merged DungeonMind PR #30.

---

# 1. Why this PR exists

DungeonMindBuddy PR #568 re-anchored CUTOVER after #566 and produced one normalized blocker ledger.

Its migration projection selected:

```text
CASE_A
repository = DungeonMind
basis = WORLD_OBJECT_KIND
source kind = thread
blocking_stage = adoption_package_construction
```

DungeonMind PR #30 has now merged and completed that exact Case A semantic publication.

Therefore Buddy must now:

1. pin the exact new DungeonMind dependency;
2. analyze the exact same Buddy world/revision against `world-object-v5` + `world-property-v3`;
3. prove the `thread` kind gap is actually gone;
4. remeasure every other blocker rather than carrying stale counts forward;
5. seal a new CUTOVER report;
6. dispatch the next PR from the refreshed ledger.

Nothing in this PR authorizes changing source truth in order to make the report greener.

---

# 2. Exact authority pins

## 2.1 Buddy predecessor

Current DungeonMindBuddy `main` at handoff creation:

```text
e5aaaf1d3d1e1e9f8c07a62383770dfd8326f259
```

This is the merge commit for Buddy PR #568.

The implementation branch should start from that commit or a later `main` descendant that preserves the #568 CUTOVER files and source authority unchanged.

If `main` advances before BUILD:

- rebase/sync normally;
- re-run all stale-input checks;
- do not silently reinterpret changed CUTOVER inputs.

Open unrelated PRs are not dependencies on this slice.

## 2.2 DungeonMind semantic authority

Merged DungeonMind PR #30:

```text
PR:
Drakosfire/DungeonMind#30

title:
DND: admit campaign thread world-object kind v5

merge commit:
be76acc997c5fbcb8ceaa090969ec051afa6051d
```

This merge publishes:

```text
world-object-v5
SHA-256:
f9fd5420e0ab3849224e0d58cf83dd432ca2e5da22ce661b25654406ec9c60d8

world-property-v3
SHA-256:
aa94df78c10a913e7ca6774198f080131f8f447c90cc917b9b840ed88bd856e4

dnd5e-profile-v3
descriptor SHA-256:
2199e8fb96e917c22718e6aec59cbbf55a37ee81575e1bcf16ce13fae0393496
```

The PR #30 semantic delta is:

```text
world-object kinds: 12 -> 13
new term: dnd5e:thread

world-object predicates:
identical to world-object-v4
dnd5e:thread appears in zero predicate endpoint sets

world-property:
world-property-v3 pins exact world-object-v5
dnd5e:role subject-kind delta = {dnd5e:thread}

profile:
unchanged

graph schema:
unchanged

mechanics:
unchanged
```

## 2.3 Canonical Eldyrwild source authority

Keep the same exact Buddy world authority:

```text
world_id:
eldyrwild

canonical revision:
rev:5a7c13ae45c49a65b402920499be72ed

canonical graph payload SHA-256:
2632870ef70638969503de788cfdec97acd490875deff3e2630ac91dc96fe974
```

## 2.4 #566 migration projection authority

Keep the exact same non-publishing repair authority:

```text
repair id:
eldyrwild-relationship-node-kind-source-repair-v1

manifest SHA-256:
96cc26fc6e99448e8fba5cd6982070c1e29bb058f2b1e8a4ac291f8a0a083247
```

Projection remains exactly four in-memory kind changes:

```text
nodes[item_shatter_mages_tower].kind
nodes[mystery_stone_bridge_river_name].kind
nodes[loc:guilds].kind
nodes[item:torvak-hemp-caravan].kind
```

No fifth Buddy kind change is authorized.

`thread` is not a Buddy source repair in this PR.

It is a target-contract re-pin.

## 2.5 Historical #568 artifact

Historical fixture:

```text
tests/fixtures/dungeonmind_kernel/
eldyrwild_cutover_reanchor_after_566_v1.json
```

Locked SHA-256:

```text
6c978f89527ccd82e9bad32eac70a5386a5d714e80f7e426f574d7dbc0e43cbf
```

This file is immutable.

The old report must remain reproducible after the DungeonMind dependency advances because PR #30 preserves explicit historical v4/v2 loaders.

---

# 3. Important upstream hygiene note

PR #30 was merged after its reviewed head had a known GitHub Actions Ruff `SIM300` failure in a test assertion.

That failure was test-style-only and did not change the published v5/v3 catalog bytes or runtime semantic APIs.

This Buddy PR MUST NOT modify DungeonMind to repair that upstream lint debt.

The semantic authority remains PR #30 / `be76acc...`.

If a later DungeonMind descendant lands before BUILD and only fixes upstream hygiene, BUILD may pin that later exact commit **only if all of these remain exact**:

```text
world-object-v5 SHA
world-property-v3 SHA
dnd5e-profile-v3 SHA
world-object-v4 SHA
world-property-v2 SHA
```

If any semantic digest changes, STOP and re-anchor this handoff.

The PR handback must record the actual exact DungeonMind commit pinned.

---

# 4. Mission

Implement one non-publishing CUTOVER re-pin that:

1. updates Buddy's exact DungeonMind package dependency to PR #30 semantic authority;
2. preserves the historical v4/v2 analyzer behavior and #568 fixture;
3. adds an explicit v5/v3 target path without copying the whole analyzer;
4. maps Buddy `thread` -> `dnd5e:thread` only in the v5 target;
5. validates Buddy `role` under world-property-v3 for the v5 target;
6. re-analyzes:
   - canonical Eldyrwild;
   - the exact #566 four-kind migration projection;
7. proves relationship inventories do not change from the #568 owning authorities;
8. proves `WORLD_OBJECT_KIND` for `thread` clears;
9. remeasures all other blocker counts from actual classification;
10. writes a new deterministic CUTOVER fixture;
11. derives the next-slice recommendation from the new migration ledger;
12. leaves canonical graph/source/provenance bytes untouched.

---

# 5. Core architectural decision — target-contract parameterization, not analyzer duplication

## 5.1 Preserve report-shape version separately from target-contract version

Current file:

```text
apps/live_control_server/integrations/dungeonmind_kernel/
whole_world_conformance_v4.py
```

contains a report schema and classifier implementation that are currently hard-wired to:

```text
DungeonMind ref 2e4fdc...
world-object-v4
world-property-v2
```

PR #30 changes the target contract, not the durable report shape.

Do NOT create a copied 2,000+ line `whole_world_conformance_v5.py` implementation.

Instead, parameterize only the target-sensitive seams while keeping historical v4 behavior exact.

The report schema may remain:

```text
dmb_dungeonmind_whole_world_conformance_report_v4
```

because its fields already carry the exact target dependency/catalog revisions and digests.

A target-catalog publication does not automatically require a diagnostic JSON schema bump.

## 5.2 Introduce one explicit target descriptor

Recommended internal shape:

```python
@dataclass(frozen=True, slots=True)
class WholeWorldTargetContract:
    target_id: str
    dungeonmind_dependency_ref: str
    world_object_loader: Callable[[], Any]
    world_object_ref_loader: Callable[[], Any]
    world_property_loader: Callable[[], Any]
    world_property_ref_loader: Callable[[], Any]
    role_validator: Callable[..., None]
    buddy_to_dm_kind: Mapping[str, str]
```

Names may follow local conventions.

The behavior is normative, not this exact class spelling.

Define two exact targets:

```text
HISTORICAL_V4_TARGET
CURRENT_V5_TARGET
```

### HISTORICAL_V4_TARGET

Must preserve:

```text
dependency ref:
2e4fdc51f91c5c2a428500f7c2ece0d6742d04b4

world-object:
world-object-v4
552c59a3fa9a20e437294d1a77974c05e37b69ec95e5ea03337a7d010e4d287b

world-property:
world-property-v2
8ad4c223e83ce48cf5cd33a33e10f5be5d48a80ad742784d7c561470b450ab73

Buddy kind map:
unchanged; no thread mapping

role validator:
validate_world_property_assignment_v2
```

### CURRENT_V5_TARGET

Must use:

```text
dependency ref:
be76acc997c5fbcb8ceaa090969ec051afa6051d
(or explicitly approved later green descendant per §3)

world-object:
world-object-v5
f9fd5420e0ab3849224e0d58cf83dd432ca2e5da22ce661b25654406ec9c60d8

world-property:
world-property-v3
aa94df78c10a913e7ca6774198f080131f8f447c90cc917b9b840ed88bd856e4

Buddy kind-map delta:
thread -> dnd5e:thread

role validator:
validate_world_property_assignment_v3
```

All other Buddy kind mappings remain identical.

## 5.3 Target-sensitive helpers

Only target-sensitive behavior should receive/use the descriptor.

At minimum this includes the current logic corresponding to:

```text
_dm_kind_for_buddy_kind
_endpoint_dm_kinds
_map_buddy_node_kind_v4
_classify_node_role_v4
_classify_node_field_v4
_admit_mapped_edge_v4
_classify_edge_predicate_v4
_classify_edge_field_v4
_build_relationship_predicate_inventory_v4
_role_summary_counts
_analyze_loaded_buddy_world_store_v4
```

Do not rename every historical `_v4` helper just for aesthetics.

A small internal target parameter is preferable to a broad naming/refactor PR.

Historical public entrypoints must behave exactly as before.

## 5.4 Explicit v5 public entrypoint

Add a new explicit target entrypoint, e.g.:

```python
def analyze_exact_buddy_world_revision_v5(
    *,
    root: Path,
    world_id: str,
    revision_id: str,
) -> WholeWorldConformanceReportV4:
    ...
```

and an equivalent already-loaded private path for the migration projection.

The new entrypoint must:

- request `CURRENT_V5_TARGET` explicitly;
- never infer "latest";
- never fall back to v4;
- never rewrite source data.

Avoid APIs named:

```text
latest
current
default
auto_upgrade
```

Exact target selection remains mandatory.

---

# 6. Dependency update

Update:

```text
pyproject.toml
uv.lock
```

from:

```text
dungeonmind @ git+https://github.com/Drakosfire/DungeonMind.git@2e4fdc...
```

to the exact approved PR #30 dependency ref.

Expected semantic ref at handoff creation:

```text
be76acc997c5fbcb8ceaa090969ec051afa6051d
```

After `uv lock` / `uv sync --locked`, test the imported DungeonMind package APIs directly.

Do not rely only on the lockfile URL text.

---

# 7. New CUTOVER re-pin report

Create a successor service instead of rewriting the historical #568 report.

Recommended path:

```text
apps/live_control_server/services/
cutover_whole_world_repin_after_dm30.py
```

Recommended schema:

```text
dmb_cutover_whole_world_repin_after_dm30_v1
```

Recommended fixture:

```text
tests/fixtures/dungeonmind_kernel/
eldyrwild_cutover_repin_after_dm30_v1.json
```

The old service and fixture remain historical and valid.

---

# 8. New report composition

The new report should reuse the existing #568 authority boundaries.

## 8.1 Canonical view

Load exact:

```text
eldyrwild
rev:5a7c13ae45c49a65b402920499be72ed
payload SHA 2632870e...
```

Analyze against `CURRENT_V5_TARGET`.

## 8.2 Migration projection

Create exactly the same #566 four-kind in-memory overlay.

Analyze the overlay against `CURRENT_V5_TARGET`.

Do not apply the projection.

Do not create `thread` source edits.

## 8.3 Relationship truth

Relationships continue to use the existing owning authorities:

Canonical:

```text
dmb_dungeonmind_relationship_effective_conformance_v1
323 / 314 / 9 / 3
```

Migration projection:

```text
eldyrwild-relationship-node-kind-source-repair-v1
323 / 318 / 5 / 3
```

PR #30 intentionally changed no predicates/endpoints.

Therefore these inventories MUST remain exact.

If any of the four relationship counts or exact residual sets change, STOP.

That is not an expected consequence of the v5 kind publication.

## 8.4 Non-relationship truth

Recompute from the actual v5 target classification.

Do not manually edit blocker counts.

In particular, do not assume the only numeric delta is:

```text
WORLD_OBJECT_KIND -1
```

The old analyzer validates every node's `role` through the target property vocabulary.

Because `thread` was previously an unmapped kind and world-property-v3 now admits it, another classification may also legitimately change.

The report must discover that from execution.

---

# 9. Required target delta section

The new fixture/report should contain an explicit target-contract delta from #568.

Recommended structure:

```json
{
  "target_contract_delta": {
    "previous": {
      "dungeonmind_dependency_ref": "...",
      "world_object_revision": "world-object-v4",
      "world_object_sha256": "...",
      "world_property_revision": "world-property-v2",
      "world_property_sha256": "..."
    },
    "current": {
      "dungeonmind_dependency_ref": "...",
      "world_object_revision": "world-object-v5",
      "world_object_sha256": "...",
      "world_property_revision": "world-property-v3",
      "world_property_sha256": "..."
    },
    "source_kind_mapping_delta": {
      "thread": "dnd5e:thread"
    },
    "cleared_blocker_classes": [],
    "changed_blockers": []
  }
}
```

Exact field names may vary.

The key invariant is that review can see:

- exactly which target contract changed;
- exactly which blocker rows changed because of it;
- that source truth did not change.

---

# 10. Historical #568 reproduction is mandatory

Before sealing the new fixture, independently run the old #568 verifier.

Expected historical result:

```text
verified = true
fixture SHA =
6c978f89527ccd82e9bad32eac70a5386a5d714e80f7e426f574d7dbc0e43cbf
```

This proves:

- updating the installed DungeonMind dependency did not change historical v4/v2 catalog behavior;
- explicit historical loaders still work;
- CUTOVER artifacts remain reproducible by exact contract pin.

Do not update the old fixture digest.

Do not rewrite old report bytes.

If historical reproduction fails, STOP.

---

# 11. Required refreshed blocker behavior

## 11.1 WORLD_OBJECT_KIND must clear

Under both v5 target views:

```text
canonical
migration projection
```

the prior `WORLD_OBJECT_KIND` blocker for:

```text
node:mystery:session25:light-and-sound-as-search-tools-during-night-response:field:kind
```

must be absent.

The exact Buddy source kind remains:

```text
thread
```

and the target mapping is:

```text
dnd5e:thread
```

If `WORLD_OBJECT_KIND` remains, STOP.

Do not work around it by post-processing the ledger.

## 11.2 Five dual-sense relationship STOPs remain

Migration projection must still contain exactly:

```text
edge:loc:central-office:located_in:node:meat_distribution_network_session9:site-of

edge:loc:packing-loading-area:part_of:node:meat_distribution_network_session9

edge:node:headmaster_tinkerbright:leads:loc:wizard_college

edge:node:hempholm_townsfolk:participates_in:node:hempholm_folk_revelry

edge:pc:caelynn:participates_in:node:hempholm_folk_revelry
```

Their normalized blocker remains:

```text
blocker_class = RELATIONSHIP_PREDICATE
count = 5
blocking_stage = adoption_package_construction
ownership_scope = cross_repository
responsible_repo = null
```

Do not resolve them in this PR.

## 11.3 Durable adoption gates remain diagnostic

Continue introspecting the public DungeonMind adoption seam.

Do not hardcode the old result if the newly pinned dependency changed it.

At PR #30 semantic authority, no adoption service was part of the PR.

Expected result is therefore still likely:

```text
DURABLE_ADOPTION_BOUNDARY_MISSING
```

But the analyzer must inspect, not assume.

If a later dependency descendant adds an adoption boundary, record the observed truth and re-dispatch normally.

## 11.4 Other package-construction blockers are remeasured

Remeasure at least:

```text
ATTRIBUTE_ASSERTION
EVIDENCE_PROVENANCE
RELATIONSHIP_PREDICATE
WORLD_OBJECT_KIND
```

Do not carry `ATTRIBUTE_ASSERTION = 29` merely because #568 had 29.

Do not carry `EVIDENCE_PROVENANCE = 8` without re-analysis.

The new target may legitimately affect a thread node's property classification.

Every changed count needs a machine-readable delta and representative durable IDs.

---

# 12. Next-slice recommendation — derive, never preselect

Use the stage/ownership selector proven by #568.

The new report must call the same recommendation semantics over the refreshed migration blocker ledger.

Do not hardcode:

```text
CASE_B
CASE_C
DungeonMind
DungeonMindBuddy
```

before the report exists.

The selector must still satisfy:

```text
any adoption_package_construction blocker
    => Case B is forbidden
```

Expected current evidence suggests package-construction blockers will remain after `thread` clears.

That means Case B is not expected yet.

But acceptance is based on the ledger, not this expectation.

The PR must report exactly what the refreshed ledger selects.

---

# 13. New report disposition

This PR MUST NOT return CUTOVER_READY merely because `WORLD_OBJECT_KIND` clears.

Expected disposition remains:

```text
CUTOVER_NOT_READY
```

unless the refreshed complete blocker ledger is actually empty across all required stages.

Given the five dual-sense package-construction STOPs, CUTOVER_READY would be a serious regression unless their semantics have been explicitly re-authorized elsewhere.

---

# 14. No-mutation proof

Snapshot before and after report composition:

```text
canonical head
World Graph tree digest
contribution index
contributions
contribution rebuild
identity decision index
identity decisions
initialization
revisions
```

The exact same T14 source-authority inventory from #568 remains applicable.

Assert byte/digest equality before/after.

Also assert the #566 repair manifest is unchanged.

Allowed writes:

```text
new deterministic repository fixture
docs
dependency lock files
test code
analyzer/service code
```

Forbidden writes:

```text
graph_memory/worlds/eldyrwild/**
approved graph correction manifests
source artifacts
evidence records
contribution history
identity history
canonical head
```

---

# 15. Stale-input refusal

The new service must fail closed when any exact activation pin drifts.

At minimum cover:

```text
Buddy canonical revision
Buddy canonical payload SHA
#566 repair manifest SHA
DungeonMind dependency ref
world-object-v5 revision
world-object-v5 SHA
world-property-v3 revision
world-property-v3 SHA
dnd5e-profile-v3 SHA
historical #568 fixture SHA
```

Monkeypatch/refusal tests should prove:

- no new fixture overwrite on stale input;
- no old fixture mutation;
- no graph mutation;
- no source-authority mutation.

---

# 16. New fixture sealing

Recommended path:

```text
tests/fixtures/dungeonmind_kernel/
eldyrwild_cutover_repin_after_dm30_v1.json
```

BUILD flow:

1. compose report;
2. inspect report and expected contract delta;
3. compute exact deterministic bytes;
4. seal SHA in code/tests;
5. refuse overwrite if existing bytes differ;
6. verify independent reproduction.

Do not invent the fixture SHA in advance.

The implementer handback must report it.

---

# 17. Suggested implementation surfaces

Expected allowlist:

```text
Docs/Plans/HANDOFF-cutover-repin-dungeonmind-v5-after-pr30.md
Docs/Plans/PR-TRACKER-campaign-supergraph.md
Docs/Plans/STATUS-world-graph-continuity-spine.md

pyproject.toml
uv.lock

apps/live_control_server/integrations/dungeonmind_kernel/
whole_world_conformance_v4.py

apps/live_control_server/integrations/dungeonmind_kernel/
whole_world_conformance_v5.py

apps/live_control_server/services/
cutover_whole_world_repin_after_dm30.py

scripts/
cutover_whole_world_repin_after_dm30.py

tests/
test_dungeonmind_whole_world_conformance_v4.py
test_dungeonmind_whole_world_conformance_v5.py
test_cutover_whole_world_reanchor.py
test_cutover_whole_world_repin_after_dm30.py

tests/fixtures/dungeonmind_kernel/
eldyrwild_cutover_repin_after_dm30_v1.json
```

Notes:

- `whole_world_conformance_v5.py` should be thin.
- Do not copy the v4 analyzer wholesale.
- If a CLI is unnecessary because the established CUTOVER script can accept a subcommand cleanly, reuse the existing script surface.
- File names may follow local naming conventions, but the authority boundaries above are fixed.

---

# 18. Explicitly forbidden surfaces

Do not modify:

```text
graph_data/approved_graph_corrections/eldyrwild/**
graph_data canonical world payloads
#566 repair manifest bytes
#568 historical fixture bytes
```

Do not add:

```text
Buddy durable kind repair
thread source mutation
dual-sense aspect identities
dual-sense node splits
relationship rewrites
new predicate semantics
new DungeonMind vocabulary terms
existing-world adoption transaction
Postgres adoption execution
shadow adoption
read-authority switch
write-authority switch
fallback graph authority
Buddy graph demolition
```

Do not "fix" unrelated CON-READY work or PR #569 in this slice.

---

# 19. Acceptance tests

## T1 — exact dependency pin

Assert the installed/declared DungeonMind dependency is the approved exact commit.

Expected at handoff creation:

```text
be76acc997c5fbcb8ceaa090969ec051afa6051d
```

If a later approved green descendant is used, assert:

- it descends from PR #30 merge;
- v5/v3/profile digests are identical;
- handback records both PR #30 semantic authority and actual dependency ref.

## T2 — exact v5/v3 contract pins

Assert:

```text
world-object-v5
f9fd5420e0ab3849224e0d58cf83dd432ca2e5da22ce661b25654406ec9c60d8

world-property-v3
aa94df78c10a913e7ca6774198f080131f8f447c90cc917b9b840ed88bd856e4

dnd5e-profile-v3
2199e8fb96e917c22718e6aec59cbbf55a37ee81575e1bcf16ce13fae0393496

graph schema
dm_union_graph_v5

source artifact
dm_source_artifact_v2

evidence
dm_evidence_ref_v2

knowledge assertion metadata
dm_knowledge_assertion_metadata_v1
```

## T3 — historical v4/v2 contract pins remain exact

Assert old explicit loaders still produce:

```text
world-object-v4
552c59a3fa9a20e437294d1a77974c05e37b69ec95e5ea03337a7d010e4d287b

world-property-v2
8ad4c223e83ce48cf5cd33a33e10f5be5d48a80ad742784d7c561470b450ab73
```

## T4 — #568 historical fixture still reproduces

Assert:

```text
verify_cutover_whole_world_reanchor(...).verified is True
```

and SHA remains:

```text
6c978f89527ccd82e9bad32eac70a5386a5d714e80f7e426f574d7dbc0e43cbf
```

## T5 — v4 analyzer behavior unchanged

On the exact canonical and exact four-kind overlay, historical v4 target output must remain byte/model equivalent to the pre-PR baseline.

At minimum preserve:

```text
dependency ref = 2e4fdc...
world-object-v4
world-property-v2
WORLD_OBJECT_KIND blocker still visible historically
```

This test proves parameterization did not retroactively reinterpret history.

## T6 — v5 target kind map delta is exactly thread

Assert:

```text
historical map does not contain thread
v5 map contains:
thread -> dnd5e:thread
```

and no other Buddy kind mapping changes.

## T7 — v5 target uses property-v3 validator

Prove the v5 path validates `dnd5e:role` through v3 and the historical path still uses v2.

No implicit fallback.

## T8 — canonical activation pins unchanged

Assert canonical:

```text
world = eldyrwild
revision = rev:5a7c13...
payload = 2632870e...
```

## T9 — migration projection changes exactly four Buddy paths

Assert the #566 projection still changes only the known four paths.

`thread` must not appear in `changed_durable_paths`.

## T10 — relationship inventories unchanged

Assert exact canonical:

```text
323 / 314 / 9 / 3
```

Assert exact migration:

```text
323 / 318 / 5 / 3
```

Assert exact residual edge sets.

## T11 — WORLD_OBJECT_KIND clears under v5

Assert no v5 normalized blocker row exists for:

```text
WORLD_OBJECT_KIND
```

in either canonical or migration view.

Assert the exact formerly blocked source path is now classified as target-representable through:

```text
thread -> dnd5e:thread
```

Do not satisfy this by filtering the blocker after analysis.

## T12 — target delta is lossless

Compare historical target report vs v5 target report.

Every changed blocker/classification must have:

- old value;
- new value;
- representative durable IDs;
- explanation tied to PR #30 contract delta.

No unexplained changed blocker.

## T13 — dual-sense STOP remains exact

Assert migration `RELATIONSHIP_PREDICATE`:

```text
count = 5
blocking_stage = adoption_package_construction
ownership_scope = cross_repository
responsible_repo = null
```

with exact five IDs.

## T14 — blocker accounting remains complete

Assert:

```text
unaccounted_durable_elements == 0
```

in both v5 views.

Every blocker carries:

```text
blocker_class
count
examples
presence_scope
blocking_stage
ownership_scope
responsible_repo
smallest_next_change
ledger_disposition
```

## T15 — recommendation remains stage-driven

Unit-test selector behavior separately.

Must prove:

```text
if any package-construction blocker remains:
    recommendation.case != CASE_B
```

The actual report's recommendation must equal selector output over the actual migration ledger.

No expected-case constant may be inserted simply to satisfy the handoff.

## T16 — no mutation

Before/after:

```text
head
graph tree
source authority family digests
```

must be identical.

## T17 — stale DungeonMind pin refusal

Monkeypatch:

```text
dependency ref
v5 object revision
v5 object SHA
v3 property revision
v3 property SHA
profile SHA
```

and assert fail-closed before fixture write.

## T18 — stale Buddy/source authority refusal

Monkeypatch:

```text
canonical revision
canonical payload SHA
repair manifest SHA
historical fixture SHA
```

and assert fail-closed.

## T19 — old fixture overwrite forbidden

Any attempt to rewrite:

```text
eldyrwild_cutover_reanchor_after_566_v1.json
```

must fail tests/review.

## T20 — new fixture deterministic

Build then verify new fixture.

Assert independently reproduced report bytes are identical.

## T21 — CUTOVER nonclaim

Assert refreshed report remains:

```text
CUTOVER_NOT_READY
```

while package-construction blockers remain.

No authority switch surface is present.

---

# 20. What not to hardcode

Do NOT predeclare:

```text
ATTRIBUTE_ASSERTION new count
EVIDENCE_PROVENANCE new count
classification inventory delta
next CASE
next responsible repository
new fixture SHA
```

Those are outputs of this PR.

The handoff deliberately locks only facts already proven by source authority or PR #30.

---

# 21. Expected observations, not acceptance constants

Current evidence makes these likely:

1. `WORLD_OBJECT_KIND` clears from `1 -> 0`.
2. Relationship counts do not move.
3. The five dual-sense package blockers remain.
4. Evidence provenance remains a Buddy package-construction issue.
5. Attribute assertion blockers remain, although their count may change because `thread` role compatibility is newly expressible.
6. Durable adoption boundary remains missing.
7. Recommendation probably moves away from the completed DungeonMind kind Case A toward the smallest remaining Buddy/cross-repository package-construction problem.

These are hypotheses to verify.

Do not encode them as fake truth if execution disagrees.

---

# 22. Dispatch after this PR

After the new fixture is sealed, read:

```text
migration_projection.blockers
next_slice_recommendation
```

and dispatch exactly one successor.

Possible truthful outcomes:

### Case C — Buddy source/provenance package gap

If the first remaining singular Buddy package blocker is:

```text
ATTRIBUTE_ASSERTION
or
EVIDENCE_PROVENANCE
```

design the smallest deterministic adoption-package materialization/source repair required.

Do not reopen relationship cleanup.

### Case A — cross-repository package decision

If only the five dual-sense cross-repository STOPs remain at package construction:

```text
repository = null
ownership_scope = cross_repository
```

design the exact adoption/materialization decision contract.

Do not assign it to one repo by convenience.

### Case A — new DungeonMind semantic gap

If a genuinely new singular DungeonMind package blocker appears, name its exact contract gap.

Do not broaden to adoption yet.

### Case B — governed existing-world adoption

Only if **all** adoption-package-construction blockers are gone and the public durable adoption seam is now the first remaining DungeonMind gate.

### Case D — shadow readiness

Only if blocker ledger is actually clear.

No product-authority switch in this re-pin PR.

---

# 23. Suggested commit sequence

### Commit 1

```text
DOCS: handoff CUTOVER DungeonMind v5 re-pin
```

Add the checked-in handoff.

### Commit 2

```text
DEPS: pin DungeonMind PR30 semantic authority
```

Update:

```text
pyproject.toml
uv.lock
```

No analyzer changes yet.

### Commit 3

```text
CONFORMANCE: parameterize whole-world target contracts
```

Preserve historical v4 behavior exactly.

Add thin explicit v5 target.

### Commit 4

```text
CONFORMANCE: remeasure Eldyrwild against world-object-v5
```

Add new non-publishing re-pin service/fixture path.

### Commit 5

```text
TEST: seal CUTOVER post-PR30 blocker ledger
```

Seal deterministic fixture and stale/no-mutation/historical-reproduction proofs.

### Commit 6

```text
DOCS: record refreshed CUTOVER dispatch
```

Update tracker/status with actual report output.

If commits can be combined cleanly without reducing reviewability, fewer is acceptable.

Do not add unrelated cleanup commits.

---

# 24. Verification

At minimum run:

```bash
uv sync --locked
```

Then focused historical + current suites:

```bash
uv run pytest -q \
  tests/test_dungeonmind_whole_world_conformance_v4.py \
  tests/test_cutover_whole_world_reanchor.py \
  tests/test_eldyrwild_relationship_node_kind_source_repair.py
```

New target suites:

```bash
uv run pytest -q \
  tests/test_dungeonmind_whole_world_conformance_v5.py \
  tests/test_cutover_whole_world_repin_after_dm30.py
```

Run CLI/status/verify for both:

```text
historical #568 re-anchor verify
new post-PR30 re-pin status
new post-PR30 re-pin build
new post-PR30 re-pin verify
```

Run lint on every changed Python file:

```bash
uv run ruff check <changed-python-files>
```

Run the repository's normal relevant type/unit checks required by current CI.

Finish with:

```bash
git diff --check
```

The handback must report actual commands and pass counts.

---

# 25. Implementer handback

Return:

## Git identity

```text
Buddy base SHA:
Buddy head SHA:
branch:
PR:
```

## DungeonMind identity

```text
PR #30 semantic authority:
actual dependency ref:
world-object-v5 SHA:
world-property-v3 SHA:
profile-v3 SHA:
```

## Historical reproduction

```text
old #568 fixture SHA:
old verifier result:
historical v4 target report unchanged?:
```

## New target proof

```text
v5 dependency ref:
v5 object revision/SHA:
v3 property revision/SHA:
thread mapping:
thread property validator:
```

## Canonical relationship inventory

```text
semantic:
represented:
residual:
uses_statblock:
exact residual IDs:
```

## Migration relationship inventory

```text
semantic:
represented:
residual:
uses_statblock:
exact residual IDs:
```

## Blocker delta

Return a table:

```text
blocker_class | old canonical | new canonical | old migration | new migration
```

Include every changed row.

Explicitly include:

```text
WORLD_OBJECT_KIND
ATTRIBUTE_ASSERTION
EVIDENCE_PROVENANCE
RELATIONSHIP_PREDICATE
```

## New recommendation

```text
case:
repository:
basis blocker(s):
blocking stage:
examples:
smallest next change:
nonclaim:
```

## Mutation proof

```text
canonical head before/after:
graph tree digest before/after:
source-authority inventory before/after:
#566 manifest before/after:
```

## Fixture identity

```text
new fixture path:
new fixture SHA:
verify result:
```

## Verification

```text
ruff:
focused historical:
focused new target:
full relevant suite:
git diff --check:
```

---

# 26. Steward review checklist

Before merge, answer YES:

- [ ] Is Buddy dependency pinned to exact approved DungeonMind PR #30 authority?
- [ ] Are v5/v3/profile digests exact?
- [ ] Does old v4/v2 analysis still reproduce #568 exactly?
- [ ] Is the old fixture byte-immutable?
- [ ] Is there one target-parameterized analyzer core rather than a copied analyzer?
- [ ] Is `thread -> dnd5e:thread` the only Buddy kind-map delta?
- [ ] Does v5 role validation use property-v3?
- [ ] Does canonical source truth remain unchanged?
- [ ] Does #566 projection still change exactly four Buddy kind paths?
- [ ] Are canonical relationships still `323 / 314 / 9 / 3`?
- [ ] Are migration relationships still `323 / 318 / 5 / 3`?
- [ ] Are the exact five dual-sense STOPs still present?
- [ ] Is `WORLD_OBJECT_KIND` gone under v5 analysis?
- [ ] Are all other blocker-count changes actually remeasured and explained?
- [ ] Are both views fully accounted?
- [ ] Is Case B impossible while any package-construction blocker remains?
- [ ] Is the actual recommendation derived from the refreshed ledger?
- [ ] Is CUTOVER still non-publishing?
- [ ] Are graph/source/provenance digests unchanged?
- [ ] Is there no adoption transaction?
- [ ] Is there no authority switch?
- [ ] Does the new fixture reproduce deterministically?

If any answer is NO, do not merge until the discrepancy is understood.

---

# 27. Final boundary

PR #30 changed DungeonMind's ability to describe one Buddy kind.

This PR changes Buddy's **measurement target**, not Buddy's world.

The correct sequence is:

```text
old exact measurement
    +
new exact DungeonMind contract
    ->
new exact measurement
    ->
new blocker ledger
    ->
one next PR
```

Not:

```text
PR #30 merged
    ->
assume thread is fixed
    ->
jump to adoption
```

Remeasure first.

Let the ledger decide.
