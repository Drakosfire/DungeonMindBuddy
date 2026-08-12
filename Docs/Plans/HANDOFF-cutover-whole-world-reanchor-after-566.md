# HANDOFF — CUTOVER whole-world re-anchor after PR #566

**Created:** 2026-08-12  
**Status:** READY FOR BUILD  
**Conversation / workstream:** `CUTOVER`  
**Repository:** `Drakosfire/DungeonMindBuddy`  
**Flow:** CONFORMANCE / CUTOVER  
**Direction:** DESIGN → CODE  
**Canonical handoff path:** `Docs/Plans/HANDOFF-cutover-whole-world-reanchor-after-566.md`  

**Suggested branch:** `cutover/reanchor-whole-world-after-566`  
**Suggested PR title:** `CONFORMANCE: re-anchor CUTOVER after #566`  

---

## 1. Mission

Re-anchor CUTOVER against the exact post-PR-#566 state and produce the single machine-readable blocker ledger that governs the next cross-repository slice.

This PR is **diagnostic and compositional**. It must answer, exactly:

> Given the current canonical Eldyrwild World Graph, the current pinned DungeonMind contracts, and the four source-sealed migration-only kind repairs proved by PR #566, what still prevents DungeonMind from adopting Eldyrwild and becoming product authority?

The PR must expose two views without conflating them:

1. **Canonical Buddy truth** — the exact current durable World Graph as published.
2. **Approved migration projection** — the same exact world analyzed with only the four PR-#566 kind corrections applied in memory.

The PR must **not** mutate canonical Eldyrwild, apply the four repairs durably, invent aspect identities for the five STOP edges, add DungeonMind semantics, build the existing-world adoption seam, or switch product authority.

The expected value of this slice is not a green dashboard. The expected value is an exact, replayable answer about what the next CUTOVER PR actually is.

---

## 2. Why this slice exists

The prior relationship work reached the useful boundary of Buddy-side cleanup.

PR #563 durably closed the mutable relationship-semantic correction program and left canonical Eldyrwild at:

```text
323 semantic relationships
314 effectively represented
9 residual
3 uses_statblock mechanics
```

PR #566 then proved that the nine are not homogeneous. It sealed four source-supported node-kind corrections and explicitly STOPPED on five edges across three dual-sense source objects. PR #566 is non-publishing; canonical graph truth is unchanged.

PR #566 therefore establishes a migration authority, not a new canonical graph revision:

```text
canonical Buddy truth       323 / 314 / 9 / 3
approved migration overlay  323 / 318 / 5 / 3
```

The previous tracker still points toward “finish Buddy semantic closure, then cut over.” That is now stale as a sequencing model. CUTOVER needs to return to the actual objective:

```text
DungeonMind owns the governed kernel and durable world authority.
DungeonMindBuddy consumes it as the D&D product.
```

This PR is the bridge back to that objective. It must measure the whole-world adoption problem from current truth rather than extending the relationship-repair workstream by inertia.

---

## 3. Activation pins

### 3.1 DungeonMindBuddy repository

| Pin | Exact value |
|---|---|
| Required base / PR #566 merge | `9f08d72462f87b39073920f7726aa8f3e392ef08` |
| PR #566 implementation head | `6598834166daaaaf578900188889164e3b349c5f` |
| PR #566 repair ID | `eldyrwild-relationship-node-kind-source-repair-v1` |
| PR #566 manifest SHA-256 | `96cc26fc6e99448e8fba5cd6982070c1e29bb058f2b1e8a4ac291f8a0a083247` |

If `origin/main` does not descend from the PR #566 merge pin at dispatch, rebase/re-anchor before implementation. Do not silently substitute a newer semantic baseline.

### 3.2 Canonical Eldyrwild World Graph

| Pin | Exact value |
|---|---|
| world | `eldyrwild` |
| canonical revision | `rev:5a7c13ae45c49a65b402920499be72ed` |
| graph payload SHA-256 | `2632870ef70638969503de788cfdec97acd490875deff3e2630ac91dc96fe974` |
| canonical effective relationship inventory | `323 / 314 / 9 / 3` |

PR #566 is non-publishing. Its tests and service contract require the live World Graph head/tree to remain unchanged. Therefore this exact revision/payload remains the activation source for this handoff.

If the canonical head has moved for any reason before BUILD begins, **STOP**. This handoff is not authority to reinterpret a descendant as equivalent.

### 3.3 DungeonMind dependency

| Pin | Exact value |
|---|---|
| DungeonMind commit | `2e4fdc51f91c5c2a428500f7c2ece0d6742d04b4` |
| graph schema | `dm_union_graph_v5` |
| D&D world-object vocabulary | `world-object-v4` |
| world-object-v4 SHA-256 | `552c59a3fa9a20e437294d1a77974c05e37b69ec95e5ea03337a7d010e4d287b` |
| D&D world-property vocabulary | `world-property-v2` |
| world-property-v2 SHA-256 | `8ad4c223e83ce48cf5cd33a33e10f5be5d48a80ad742784d7c561470b450ab73` |
| semantic profile | `dnd5e-profile-v3` |
| semantic profile descriptor SHA-256 | `2199e8fb96e917c22718e6aec59cbbf55a37ee81575e1bcf16ce13fae0393496` |
| source artifact contract | `dm_source_artifact_v2` |
| evidence contract | `dm_evidence_ref_v2` |
| knowledge assertion metadata | `dm_knowledge_assertion_metadata_v1` |

These are explicit pins. Do not add a `latest` contract path.

---

## 4. Governing invariant

Against the exact pins above, the PR must produce one deterministic CUTOVER re-anchor report in which:

1. the **canonical view** is derived from the exact published Eldyrwild revision with no mutation or projection;
2. the **migration view** differs from canonical world semantics only at the four PR-#566 node-kind fields;
3. relationship truth in both views is taken from the **effective-conformance owning boundary**, never inferred from raw v4 predicate classification or arithmetic;
4. all non-relationship durable families are reclassified against the pinned DungeonMind contracts with `unaccounted_durable_elements == 0`;
5. every remaining adoption blocker is preserved with an owner, count, examples, and smallest next change;
6. the five PR-#566 dual-sense residual edges remain explicit unresolved migration decisions;
7. the report does not claim CUTOVER readiness merely because a relationship counter improves;
8. no canonical World Graph byte, revision, contribution ledger, identity ledger, source artifact, evidence record, or head pointer changes.

The report is successful when it makes the next dependency exact, including when the disposition remains `CUTOVER_NOT_READY`.

---

## 5. Exact PR #566 migration authority

### 5.1 Four allowed kind corrections

The migration overlay may change exactly these fields:

| Node | Canonical kind | Migration kind |
|---|---|---|
| `item_shatter_mages_tower` | `item` | `location` |
| `mystery_stone_bridge_river_name` | `mystery` | `location` |
| `loc:guilds` | `location` | `faction` |
| `item:torvak-hemp-caravan` | `item` | `group` |

The source repair authority must be verified from the locked PR-#566 manifest before the overlay is constructed.

The overlay must be created with immutable/in-memory model copies. It must not publish a graph revision and must not write a replacement source file.

### 5.2 Exact four relationship deltas

The overlay is expected to make these four deferred edges effectively represented:

```text
edge:combat_shatter_mages_tower_spider:located_in:item_shatter_mages_tower
edge:loc:stone_bridge:contains:mystery_stone_bridge_river_name
edge:node:torrin_flamescale:serves:loc:guilds:represents
edge:node:torvak_hempdealer_crew:member_of:item:torvak-hemp-caravan
```

### 5.3 Five explicit STOP edges

These remain residual in the migration projection:

```text
edge:loc:central-office:located_in:node:meat_distribution_network_session9:site-of
edge:loc:packing-loading-area:part_of:node:meat_distribution_network_session9
edge:node:headmaster_tinkerbright:leads:loc:wizard_college
edge:node:hempholm_townsfolk:participates_in:node:hempholm_folk_revelry
edge:pc:caelynn:participates_in:node:hempholm_folk_revelry
```

They group into three source-model conflicts:

- `loc:wizard_college` — place / organization;
- `node:meat_distribution_network_session9` — project or collective / physical site;
- `node:hempholm_folk_revelry` — revelers/group / event.

This PR must not create aspect nodes, replacement IDs, endpoint rewrites, merge/split decisions, or durable correction operations for them.

The CUTOVER interpretation is:

> these are unresolved migration/materialization decisions, not automatic authorization for another live Buddy repair program.

---

## 6. Architecture of the re-anchor

### 6.1 Keep historical analyzers historical

`whole_world_conformance_v4.py` is the current whole-world contract classifier. Its module contract explicitly describes it as diagnostic infrastructure, not migration.

Do not rewrite its historical meaning or change existing fixture results merely to make the new re-anchor convenient.

A minimal private refactor is allowed if needed to analyze an already integrity-loaded `UnionSupergraphStore` in memory:

```text
public existing entrypoint
analyze_exact_buddy_world_revision_v4(root, world_id, revision_id)
        |
        v
integrity load exact manifest + store
        |
        v
private pure loaded-store analyzer
```

The existing public entrypoint must remain behaviorally identical and all existing v4 fixture/digest tests must remain green.

### 6.2 New CUTOVER composition service

Create a new composition service rather than teaching the base whole-world analyzer about PR #566.

Suggested path:

`apps/live_control_server/services/cutover_whole_world_reanchor.py`

It owns the sequence:

```text
exact canonical revision
        |
        +--> whole-world v4 canonical classification
        |
        +--> effective relationship canonical analysis
        |
        +--> verify PR #566 locked repair authority
                    |
                    v
              in-memory four-kind overlay
                    |
                    +--> whole-world v4 projected classification
                    |
                    +--> PR #566 owning-boundary relationship proof
        |
        v
compose CUTOVER canonical + migration views
        |
        v
exact blocker ledger + deterministic fixture
```

The service is read-only with respect to the World Graph.

### 6.3 Relationship authority must remain effective-conformance authority

This is non-negotiable.

Raw `_classify_edge_predicate_v4` results are useful inputs to whole-world diagnostics, but they are not equivalent to current effective relationship truth. Earlier review already exposed a concrete example: a raw v4 classification can describe an edge as an endpoint admission gap while that edge is not in the effective residual set because continuity/adjudication authority changes the effective result.

Therefore:

- canonical relationship summary must come from `analyze_relationship_effective_conformance_v1` on the exact canonical revision;
- migration relationship summary must come from the PR-#566 isolated owning-boundary proof;
- the CUTOVER report must not calculate `represented +/- N` or treat raw whole-world relationship fields as the authoritative current relationship ledger;
- when composing blocker summaries, raw `RELATIONSHIP_PREDICATE` blocker rows from the base whole-world report must not double-count or override the effective relationship ledger.

The CUTOVER composition layer owns this normalization. The historical v4 report remains intact.

---

## 7. Required report contract

Create a strict versioned report. Suggested schema:

```text
dmb_cutover_whole_world_reanchor_v1
```

Suggested model shape:

```text
CutoverWholeWorldReanchorReportV1
  schema
  world_id
  buddy_repository_base_sha
  canonical_revision_id
  canonical_graph_payload_sha256
  dungeonmind_dependency_ref
  dungeonmind_contract_pins
  repair_authority
    repair_id
    manifest_sha256
    verified
    changed_node_kind_paths[]
  canonical_view
    whole_world_report_digest
    durable_inventory
    classification_inventory
    relationship_inventory
    relationship_residual_edge_ids[]
    blockers[]
  migration_projection
    whole_world_report_digest
    durable_inventory
    classification_inventory
    relationship_inventory
    relationship_residual_edge_ids[]
    blockers[]
  projection_delta
    changed_node_ids[]
    changed_durable_paths[]
    newly_represented_relationship_edge_ids[]
    remaining_relationship_edge_ids[]
    added_blockers[]
    cleared_blockers[]
    changed_blockers[]
  adoption_seam
  cutover_disposition
  diagnostics[]
```

Names may change if existing conventions strongly prefer another shape. The semantic obligations may not.

### 7.1 Canonical relationship inventory

Must equal exactly:

```json
{
  "semantic": 323,
  "represented": 314,
  "residual": 9,
  "uses_statblock_mechanics": 3
}
```

The residual set must be the exact nine PR-#566 input edges.

### 7.2 Migration relationship inventory

Must equal exactly:

```json
{
  "semantic": 323,
  "represented": 318,
  "residual": 5,
  "uses_statblock_mechanics": 3
}
```

The residual set must be the exact five STOP edges in §5.3.

### 7.3 Full durable accounting

For both canonical and migration views:

```text
unaccounted_durable_elements == 0
```

The report must preserve the whole-world classification inventories and blocker examples needed to identify all non-relationship adoption gaps.

Do not hide `SOURCE_MIGRATION_HISTORY`, identity history, evidence/provenance, alias reconstruction, durability, or adoption-boundary blockers because they are inconvenient to the preferred next slice.

### 7.4 Projection-diff proof

The in-memory source-store diff must show exactly four changed durable value paths and no identity changes:

```text
nodes[item_shatter_mages_tower].kind
nodes[mystery_stone_bridge_river_name].kind
nodes[loc:guilds].kind
nodes[item:torvak-hemp-caravan].kind
```

No node IDs, edge IDs, edge endpoints, predicates, evidence refs, source artifacts, assertion support, contribution replay state, aliases, identity decisions, or store metadata may change.

`enumerate_durable_element_ids(base_store)` and `enumerate_durable_element_ids(overlay_store)` must contain the same exact ID set.

---

## 8. Blocker ledger and next-slice selection

The main deliverable is the **projected blocker ledger**, not a relationship score.

Every remaining blocker must carry:

- blocker class;
- count;
- representative durable IDs or edge IDs;
- responsible repository where ownership is singular;
- exact smallest next change;
- whether the blocker exists in canonical only, projection only, or both;
- whether it blocks adoption-package construction, durable adoption, shadow parity, or authority promotion.

The report must preserve uncertainty rather than force every cross-repository dependency into one owner.

### 8.1 The five dual-sense edges

Do not schedule a live Buddy repair merely because these five remain.

Record them as an explicit migration decision set. Their successor may require two capabilities:

1. source-backed identity/decomposition decisions on the Buddy side;
2. a DungeonMind adoption/materialization contract capable of consuming those decisions.

This PR does not decide that contract.

### 8.2 Dispatch rule after merge

After the re-anchor report is independently verified:

**Case A — projected DungeonMind semantic/durability contract gaps remain before adoption can be expressed**  
Dispatch one narrow DungeonMind contract PR for the highest-leverage exact gap family. Do not dispatch a generic “finish semantics” program.

**Case B — the semantic target is expressible and the public existing-world adoption boundary is the first remaining DungeonMind gate**  
Dispatch:

```text
DungeonMind
WORLD: add governed existing-world adoption transaction
```

This is the expected likely path, but the BUILD agent must not hardcode Case B into the report.

**Case C — a Buddy source/provenance defect prevents even a deterministic adoption package**  
Stop and name the exact defect. Do not reopen broad relationship cleanup.

**Case D — no adoption blockers remain**  
Do not switch product authority in this PR. Dispatch a separate shadow-adoption/readiness proof.

---

## 9. Durable adoption seam treatment

The whole-world analyzer currently introspects the DungeonMind durable repository API and reports whether a public governed existing-world adoption seam exists.

At the pinned DungeonMind commit, the expected result remains a missing durable adoption boundary.

The re-anchor must inspect this through the existing seam probe rather than hardcoding `MISSING`.

If the probe result differs from the expected pinned contract behavior, fail the pin or report contract drift. Do not silently reinterpret the newer API.

No Postgres import or durable DungeonMind publication belongs in this PR.

---

## 10. Out of scope

This PR must not:

- publish a Buddy World Graph revision;
- apply the four #566 repairs to canonical Eldyrwild;
- create or rename world-object identities;
- split Wizard College, meat distribution, or Hempholm revelry;
- rewrite edge endpoints;
- change DungeonMind vocabulary/contracts;
- modify the DungeonMind repository;
- implement existing-world adoption;
- build an Eldyrwild adoption package;
- write to DungeonMind durable repositories;
- switch Buddy read authority;
- switch Buddy write authority;
- migrate Play/Build/Plan/Hermes consumers;
- touch PR #567 / the parallel CON-READY branch;
- use “latest” revision, latest ingest, preview union, mutable run output, or arbitrary Markdown as graph authority;
- delete historical analyzers, fixtures, or adjudication ledgers.

---

## 11. Suggested file allowlist

Implementation should remain close to this list:

```text
Docs/Plans/HANDOFF-cutover-whole-world-reanchor-after-566.md
apps/live_control_server/integrations/dungeonmind_kernel/whole_world_conformance_v4.py
apps/live_control_server/services/cutover_whole_world_reanchor.py
scripts/build_cutover_whole_world_reanchor.py
tests/test_cutover_whole_world_reanchor.py
tests/fixtures/dungeonmind_kernel/eldyrwild_cutover_reanchor_after_566_v1.json
Docs/Plans/PR-TRACKER-campaign-supergraph.md
Docs/Design/STATUS-world-graph-continuity-spine.md
```

`whole_world_conformance_v4.py` may change only for a private loaded-store analysis seam/refactor that preserves its public behavior and historical fixtures. If a larger analyzer redesign appears necessary, STOP and return to Steward review.

No `src/graph_memory/kernel/**` changes are authorized.

No DungeonMind repository changes are authorized.

---

## 12. CLI / operator surface

Suggested CLI:

```bash
uv run python scripts/build_cutover_whole_world_reanchor.py status
uv run python scripts/build_cutover_whole_world_reanchor.py build
uv run python scripts/build_cutover_whole_world_reanchor.py verify
```

Semantics:

- `status` — read-only exact-pin eligibility and dependency diagnostics;
- `build` — derive deterministic report/fixture bytes; repository artifact write only;
- `verify` — reload locked artifact and independently reproduce both views/deltas;
- no `apply` command;
- no `--allow-live-world` mutation flag should be necessary because there is no graph write path.

If a live-root acknowledgement flag is retained for consistency, it must be a no-op observation exactly like PR #566 and tests must prove there is no mutation path.

---

## 13. Acceptance test ledger

The following are normative acceptance requirements.

### T1 — exact repository and contract pins

Prove:

- Buddy base descends from PR #566 merge `9f08d724…`;
- DungeonMind dependency is exactly `2e4fdc51…`;
- graph/vocabulary/property/evidence/profile digests match §3.

No implicit latest resolution.

### T2 — exact canonical World Graph pin

Open exact `rev:5a7c13ae45c49a65b402920499be72ed` and prove payload SHA `2632870e…`.

Stale/different head is ineligible.

### T3 — historical whole-world v4 behavior is unchanged

All current `tests/test_dungeonmind_whole_world_conformance_v4.py` fixture/digest tests remain green byte-for-byte where they assert immutability.

The private loaded-store refactor must be behavior preserving.

### T4 — canonical effective relationship truth

`analyze_relationship_effective_conformance_v1` must reproduce:

```text
323 / 314 / 9 / 3
```

with the exact nine residual IDs.

### T5 — PR #566 authority is exact and verified

The locked repair manifest SHA must equal:

`96cc26fc6e99448e8fba5cd6982070c1e29bb058f2b1e8a4ac291f8a0a083247`

Tamper, predecessor drift, source seal drift, or contribution digest drift refuses before projection.

### T6 — migration overlay changes only four kind paths

Deep-diff the canonical and overlay serialized stores.

Exactly four value paths may differ, all `.kind` fields named in §7.4.

The durable element ID set must be identical.

### T7 — migration effective relationship truth

The PR-#566 isolated proof must reproduce:

```text
323 / 318 / 5 / 3
```

with the exact five residual IDs and exact four newly represented edge IDs.

### T8 — dual-sense STOPs remain STOPs

Prove the report contains the three STOP source nodes and five residual edges.

Prove no aspect IDs, replacement IDs, endpoint rewrites, or split operations appear in the projection artifact.

### T9 — complete whole-world accounting in both views

Canonical and projected whole-world analyses must each produce:

```text
unaccounted_durable_elements == 0
```

Unknown durable extras in a synthetic adversarial fixture must still force a nonzero unaccounted result / failure exactly as the existing analyzer contract requires.

### T10 — no raw-v4 relationship truth leakage

Add a regression demonstrating that CUTOVER relationship counts/residual sets are populated from effective-conformance authority, not raw `_classify_edge_predicate_v4` totals.

Use an existing known case where raw and effective semantics differ if practical; otherwise introduce a synthetic continuity/adjudication case.

### T11 — blocker ledger is lossless

For every blocker in the normalized canonical/projected whole-world analyses, prove it is either:

- present in the CUTOVER blocker ledger;
- explicitly replaced by the effective relationship blocker representation; or
- documented as a non-blocking operational classification.

No blocker may disappear because a composer forgot to carry it forward.

### T12 — durable adoption seam is introspected

Call the existing DungeonMind adoption-seam probe.

At the pinned dependency, expected result is still missing. Do not hardcode the result.

### T13 — no canonical mutation

Snapshot before and after build + verify:

- world head revision;
- complete World Graph tree digest;
- pinned revision payload bytes/digest.

All must be unchanged.

### T14 — no source/provenance mutation

On a cloned root or byte inventory, prove build/verify does not change:

- contribution ledgers;
- contribution indexes;
- contribution replay manifests;
- assertion support;
- identity redirects/merges/decisions;
- source artifacts;
- evidence records.

### T15 — deterministic report bytes

Two independent builds against exact pins produce byte-identical report/fixture bytes and the same SHA-256.

Changed meaning under the same report identity must fail closed or require a version bump; do not silently overwrite a locked v1 artifact.

### T16 — stale dependency refusal

Adversarially drift at least:

- canonical revision/head;
- canonical payload SHA;
- PR #566 manifest digest;
- DungeonMind dependency/contract pin.

Each must produce a precise ineligible/integrity result before report publication.

---

## 14. Expected verification commands

At minimum:

```bash
uv sync --locked

uv run ruff check \
  apps/live_control_server/integrations/dungeonmind_kernel/whole_world_conformance_v4.py \
  apps/live_control_server/services/cutover_whole_world_reanchor.py \
  scripts/build_cutover_whole_world_reanchor.py \
  tests/test_cutover_whole_world_reanchor.py

uv run pytest -q \
  tests/test_cutover_whole_world_reanchor.py \
  tests/test_dungeonmind_whole_world_conformance_v4.py \
  tests/test_dungeonmind_relationship_effective_conformance.py \
  tests/test_eldyrwild_relationship_node_kind_source_repair.py

uv run python scripts/build_cutover_whole_world_reanchor.py status
uv run python scripts/build_cutover_whole_world_reanchor.py verify

git diff --check
```

The BUILD agent should record exact pass counts from its environment in the PR handback rather than copying counts from this handoff.

---

## 15. Stop conditions

STOP and hand back to Steward if any of the following occurs:

1. canonical Eldyrwild head is not the exact §3.2 revision;
2. canonical graph payload digest differs;
3. PR #566 locked manifest/source authority does not verify;
4. the migration projection needs any change other than the four exact kind fields;
5. any of the five STOP edges appears kind-only solvable under the sealed #566 proof and current pinned contracts;
6. resolving a remaining blocker requires creating an aspect identity in this PR;
7. a new DungeonMind semantic contract is required to make the report run;
8. full durable accounting is not zero-unaccounted;
9. effective relationship truth cannot be composed without changing historical analyzer semantics;
10. the implementation needs a canonical graph write path;
11. the implementation needs `src/graph_memory/kernel/**` changes;
12. a deterministic blocker ledger cannot distinguish canonical truth from migration projection;
13. DungeonMind dependency has advanced and current pins are no longer the repo contract actually being tested.

Do not broaden the PR to fix a stop condition.

---

## 16. Nonclaims

A successful merge of this PR does **not** mean:

```text
Eldyrwild has been migrated to DungeonMind
DungeonMind can durably adopt an existing world
DungeonMind is current product authority
Buddy's four kind repairs have been published
The five dual-sense relationships have been resolved
323 / 323 / 0 / 3 has been achieved canonically
Play / Build / Plan / Hermes have switched graph authority
CUTOVER is complete
```

It means:

> CUTOVER has one exact current blocker ledger and can dispatch the next cross-repository capability without guessing or continuing Buddy repair work by inertia.

---

## 17. Expected likely exit and successor

The design expectation — **not an acceptance assumption** — is that the current DungeonMind semantic contracts will account for most whole-world durable semantics, while the public governed existing-world adoption boundary remains missing.

If the report proves that to be the first actionable DungeonMind gate, the next handoff should target:

```text
Repository: Drakosfire/DungeonMind
Suggested title: WORLD: add governed existing-world adoption transaction
```

That successor should own:

- one-time adoption/genesis identity;
- complete candidate validation;
- immutable adoption/source receipt;
- empty-world / expected-parent CAS semantics;
- durable publication;
- idempotent retry and uncertain-outcome recovery;
- replay/readback proof;
- no Eldyrwild-specific semantics.

Do not author or implement that successor inside this PR.

---

## 18. Suggested nano-commit story

A clean implementation history would look approximately like:

1. `DOCS: handoff CUTOVER whole-world re-anchor after #566`
2. `REFACTOR: expose loaded-store whole-world v4 analysis seam`
3. `CONFORMANCE: compose canonical and migration CUTOVER views`
4. `TEST: seal post-#566 blocker ledger and no-mutation proofs`
5. `DOCS: re-anchor CUTOVER tracker and continuity status`

The exact commit count is not sacred. The semantic boundaries are.

---

## 19. Review handback contract

The implementing agent must return:

- exact base SHA and head SHA;
- changed-file list;
- commit list;
- generated report/fixture SHA-256;
- canonical revision + payload pins actually observed;
- canonical relationship inventory + nine residual IDs;
- migration relationship inventory + five residual IDs;
- exact four changed kind paths;
- canonical and projected blocker summaries by class/owner/count;
- adoption-seam result;
- `unaccounted_durable_elements` for both views;
- test/ruff command outputs and pass counts;
- before/after World Graph head/tree digest proof;
- explicit recommendation for the next bounded CUTOVER slice derived from the blocker ledger.

Review is cumulative against this handoff and the exact PR base. A green relationship projection alone is insufficient.

---

## 20. Steward anchor

The single sentence to preserve through implementation and review is:

> **Measure the exact world we have, project only the four corrections we have actually proved, keep the five unresolved identities unresolved, and use the resulting whole-world blocker ledger to move CUTOVER back into DungeonMind.**
