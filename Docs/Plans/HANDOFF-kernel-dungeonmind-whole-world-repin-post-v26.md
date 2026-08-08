# HANDOFF — DungeonMind whole World Graph post-v26 repin (v2 analyzer)

**Created:** 2026-08-08  
**Status:** COMPLETE — diagnostic disposition (v2 against `dm_union_graph_v5`)  
**Repository:** `Drakosfire/DungeonMindBuddy` (+ contract evidence from pinned `Drakosfire/DungeonMind`)  
**Flow:** KERNEL  
**Canonical path:** `Docs/Plans/HANDOFF-kernel-dungeonmind-whole-world-repin-post-v26.md`

**Suggested branch:** `kernel/dungeonmind-whole-world-repin-post-v26`  
**Suggested PR title:** `KERNEL: re-pin Eldyrwild whole-world conformance after DungeonMind v5`  
**PR:** [#523](https://github.com/Drakosfire/DungeonMindBuddy/pull/523)

**Cursor conversation (recorded at Review Cycle 1; not claimed as pre-dispatch):**  
[Eldyrwild conformance re-pin](e3ce4fe4-e3c5-44d0-8c43-4775e4b9f91f)

---

## §1 Repository state

| Anchor | SHA / ref |
|--------|-----------|
| DungeonMindBuddy base (PR branch merge-base / `origin/main` at open) | `825ad33bb4df1a2d3b34117b1eda7e5748da0911` |
| Historical #522 merge (pre-rebase handoff start) | `d30f94f1bfd3eac78f345689fbe44e9dc2a85328` |
| Branch | `kernel/dungeonmind-whole-world-repin-post-v26` |
| Implementation commit (initial PR head) | `3e95f31ec5d33d1e167d090ea13fc6c7fdf300e3` |
| Review Cycle 1 fix commit | `affdafabfe9937546241eb085bd105eb4e87de08` |
| PR | [#523](https://github.com/Drakosfire/DungeonMindBuddy/pull/523) |
| review cycles | **1** |
| **DungeonMind pin (this workstream)** | `da7c32576c319d1030410eabe5c589ef7e990a9f` |
| Historical v1 pin (#522) | `8095321ed011b8a38640615a90cbc9efaf385e8c` |
| Real world | `out/graph_memory/worlds/eldyrwild` |
| Pinned revision | `rev:3413bf6f5044cf2680233f5e37c90dcf` |
| `graph_payload_sha256` | `346c1fbfb3cbbf6d0e5ded1453fdd7760264a5106022e398d6074679799ab0fa` |
| Source tree digest (read-only proof) | `b79f956141424f7ed332d86f3249666c9353e048f2776364bcb09e65edff6a77` |

Head was read once during test setup to confirm the pin; v2 analyzer entrypoints never consult head after `revision_id` is supplied.

---

## §1b Review Cycle 1 (acceptance-contract fixes)

Requested before merge (no semantic redesign):

1. Pin `assertion_metadata_schema = dm_knowledge_assertion_metadata_v1` on the v2 report.
2. Make the checked-in compact fixture a durable CI regression contract: add `classification_inventory`, CI-stable fixture test, and full compact-report equality when Eldyrwild `out/` is present.
3. Record exact Cursor conversation + PR/#523/base/head provenance (this section).
4. Fix adversarial mapping test: forbid generic `dnd5e:` prefix fallback, not identical spelling from the explicit adapter table.

## §2 Contract pins (v2 identity)

| Contract | Value |
|----------|-------|
| Report schema | `dmb_dungeonmind_whole_world_conformance_report_v2` |
| DungeonMind dependency | `da7c32576c319d1030410eabe5c589ef7e990a9f` |
| Target graph schema | `dm_union_graph_v5` |
| Semantic profile | `dungeonmind.dnd5e` / `dnd5e-profile-v3` / descriptor_sha256 `2199e8fb96e917c22718e6aec59cbbf55a37ee81575e1bcf16ce13fae0393496` |
| World-object vocabulary | `dungeonmind.dnd5e.world_object` / `world-object-v2` / catalog_sha256 `a53e2d0ec45878288800ff3d30006d54803db70a17e6680b359a0fa88f2a9922` |
| Source artifact schema | `dm_source_artifact_v2` |
| Evidence schema | `dm_evidence_ref_v2` |
| Assertion metadata schema | `dm_knowledge_assertion_metadata_v1` |
| Vocabulary loader | `load_builtin_world_object_v2_vocabulary()` — never `latest` |

v1 analyzer (`whole_world_conformance.py`) remains on historical pin semantics; `WHOLE_WORLD_CONFORMANCE_REPORT_SCHEMA` unchanged.

---

## §3 Public API (v2)

| Symbol | Role |
|--------|------|
| `WHOLE_WORLD_CONFORMANCE_REPORT_SCHEMA_V2` | `dmb_dungeonmind_whole_world_conformance_report_v2` |
| `analyze_exact_buddy_world_revision_v2` | Primary inventory + classification against v5 contracts |
| `build_exact_dungeonmind_adoption_revision_v2` | Fail-closed adoption builder (raises on NOT_READY; cites `dm_union_graph_v5`) |
| `WholeWorldConformanceReportV2` | Report model incl. `relationship_predicate_inventory`, `property_gap_inventory` |

Shared with v1 (re-exported unchanged): `snapshot_world_graph_tree_digest`, `inspect_dungeonmind_durable_adoption_seam`, `WholeWorldConformanceError`.

---

## §4 Before / after blocker table (#522 historical vs executed v2)

Real Eldyrwild @ `rev:3413bf6f5044cf2680233f5e37c90dcf`. Historical counts from #522 handoff (v1 @ `8095321…`).

| Blocker class | #522 (v1) | v2 @ `da7c325…` | Delta note |
|---------------|----------:|----------------:|------------|
| WORLD_OBJECT_KIND | 260 | **0** | All 12 Buddy kinds + mechanics `external_resource` adapter |
| EPISTEMIC_STATE | 786 | **0** | `EpistemicKindV2` exact peers (`fact`, `source_derived_candidate`, …) |
| FICTIONAL_TIME | 333 | **0** | `edge.session_ids` → `session_refs` adapter; not fictional time |
| CAMPAIGN_SCOPE | 787 | **1** | Nonblank → metadata adapter; `None` → world-universal null; residual `store.campaign_id` only |
| EVIDENCE_PROVENANCE | 1209 | **862** | v2 key/domain preservation; statblock/party_registry no longer gaps |
| ATTRIBUTE_ASSERTION | 438 | 438 | `node.role` (and description) still semantic gaps |
| RELATIONSHIP_PREDICATE | 336 | 336 | Unmapped predicates + endpoint admission on mapped predicates |
| CONTRIBUTION_HISTORY | 4090 | 4090 | Unchanged — genesis policy undecided |
| IDENTITY_HISTORY | — | **0** | Eldyrwild has no identity_redirect/merge/decision records |
| DURABLE_ADOPTION_BOUNDARY | 1 | 1 | Introspected MISSING |
| POSTGRES_ADOPTION | 1 | 1 | BLOCKED |

**Disposition:** `WHOLE_GRAPH_ADOPTION_NOT_READY` (both v1 and v2).  
**Completeness:** `unaccounted_durable_elements = 0` (18106 durable paths).

---

## §5 Relationship predicate inventory (complete @ pin, 348 edges)

| Buddy predicate | Count | Disposition | Mapped DM term |
|-----------------|------:|-------------|----------------|
| allied_with | 1 | SEMANTIC_ADJUDICATION_REQUIRED | — |
| appeared_in | 1 | SEMANTIC_ADJUDICATION_REQUIRED | — |
| associated_with | 8 | SEMANTIC_ADJUDICATION_REQUIRED | — |
| attacks | 26 | SEMANTIC_ADJUDICATION_REQUIRED | — |
| aware_of | 4 | SEMANTIC_ADJUDICATION_REQUIRED | — |
| belongs_to | 1 | SEMANTIC_ADJUDICATION_REQUIRED | — |
| carries | 16 | SEMANTIC_ADJUDICATION_REQUIRED | — |
| carries_report_to | 1 | SEMANTIC_ADJUDICATION_REQUIRED | — |
| causes | 4 | SEMANTIC_ADJUDICATION_REQUIRED | — |
| commands | 5 | SEMANTIC_ADJUDICATION_REQUIRED | — |
| contains | 17 | SEMANTIC_ADJUDICATION_REQUIRED | — |
| controls_comms_with | 3 | SEMANTIC_ADJUDICATION_REQUIRED | — |
| cooperates_with | 1 | SEMANTIC_ADJUDICATION_REQUIRED | — |
| defends_weakened_location | 1 | SEMANTIC_ADJUDICATION_REQUIRED | — |
| displaced_from | 2 | SEMANTIC_ADJUDICATION_REQUIRED | — |
| holds | 12 | SEMANTIC_ADJUDICATION_REQUIRED | — |
| identified_as | 4 | SEMANTIC_ADJUDICATION_REQUIRED | — |
| knows_about | 8 | SEMANTIC_ADJUDICATION_REQUIRED | — |
| leads | 11 | SEMANTIC_ADJUDICATION_REQUIRED | — |
| leads_to | 11 | SEMANTIC_ADJUDICATION_REQUIRED | — |
| linked_to | 1 | SEMANTIC_ADJUDICATION_REQUIRED | — |
| located_in | 48 | SEMANTIC_ADJUDICATION_REQUIRED | — |
| member_of | 24 | ENDPOINT_ADMISSION_GAP | `dnd5e:member_of` |
| mission_targets | 1 | SEMANTIC_ADJUDICATION_REQUIRED | — |
| near | 2 | SEMANTIC_ADJUDICATION_REQUIRED | — |
| objective_of | 2 | SEMANTIC_ADJUDICATION_REQUIRED | — |
| occurred_at | 2 | SEMANTIC_ADJUDICATION_REQUIRED | — |
| owns | 5 | SEMANTIC_ADJUDICATION_REQUIRED | — |
| parent_of | 1 | SEMANTIC_ADJUDICATION_REQUIRED | — |
| part_of | 11 | SEMANTIC_ADJUDICATION_REQUIRED | — |
| part_of_group | 1 | SEMANTIC_ADJUDICATION_REQUIRED | — |
| participated_in | 2 | SEMANTIC_ADJUDICATION_REQUIRED | — |
| participates_in | 9 | ENDPOINT_ADMISSION_GAP | `dnd5e:participates_in` |
| path_to | 2 | SEMANTIC_ADJUDICATION_REQUIRED | — |
| possesses | 4 | SEMANTIC_ADJUDICATION_REQUIRED | — |
| present_at | 16 | SEMANTIC_ADJUDICATION_REQUIRED | — |
| pursues | 3 | SEMANTIC_ADJUDICATION_REQUIRED | — |
| recruits_for | 3 | SEMANTIC_ADJUDICATION_REQUIRED | — |
| reports_threat_in | 1 | SEMANTIC_ADJUDICATION_REQUIRED | — |
| results_in | 5 | SEMANTIC_ADJUDICATION_REQUIRED | — |
| rivals | 1 | SEMANTIC_ADJUDICATION_REQUIRED | — |
| routes_to | 2 | SEMANTIC_ADJUDICATION_REQUIRED | — |
| same_as | 5 | SEMANTIC_ADJUDICATION_REQUIRED | — |
| serves | 7 | SEMANTIC_ADJUDICATION_REQUIRED | — |
| south_of | 1 | SEMANTIC_ADJUDICATION_REQUIRED | — |
| sublocation_of | 1 | SEMANTIC_ADJUDICATION_REQUIRED | — |
| suspects | 1 | SEMANTIC_ADJUDICATION_REQUIRED | — |
| threatens | 6 | ENDPOINT_ADMISSION_GAP | `dnd5e:threatens` |
| travels_to | 16 | SEMANTIC_ADJUDICATION_REQUIRED | — |
| trusts | 1 | SEMANTIC_ADJUDICATION_REQUIRED | — |
| uses_statblock | 2 | MECHANICS_SPECIALIZATION | — |
| within | 15 | SEMANTIC_ADJUDICATION_REQUIRED | — |
| works_with | 10 | SEMANTIC_ADJUDICATION_REQUIRED | — |
| **Total** | **348** | | |

Sum check: 348 = 348 edges. No `f"dnd5e:{buddy_predicate}"` string-prefix mappings. `located_in` never renamed to `located_at`; `attacks` never mapped to `dnd5e:threatens`.

---

## §6 Provenance-axis table (v2 @ pin)

| Buddy `source_domain` | Artifacts | Evidence | v2 disposition |
|-----------------------|----------:|---------:|----------------|
| recap | 16 | 158 | `source_domain_key=recap`; adapter → `session_recap` |
| worldbuilding | 4 | 4 | key + exact `worldbuilding` domain |
| statblock | 3 | 9 | key preserved; `source_domain=null` (REPRESENTABLE) |
| manual_seed | 1 | 13 | key + adapter → `manual` |
| party_registry | 1 | 1 | key preserved; `source_domain=null` (REPRESENTABLE) |

`authority_state` (`draft`/`reviewed`/`canonical`) → `SourceArtifactV2.review_state` (SourceReviewState).  
`visibility_state` → `source_visibility_state` adapter (not DM operational `Visibility.player`).

---

## §7 Residual property inventory (`node.role`)

16 distinct role values; top counts: `item` 125, `location` 101, `mystery` 93, `npc` 45, `group` 29.  
Classification: `DUNGEONMIND_SEMANTIC_CONTRACT_GAP` / `ATTRIBUTE_ASSERTION` — generic PropertyAssertion ≠ semantic `dnd5e:role`.  
`node.description` (where present): same ATTRIBUTE_ASSERTION gap; not mapped to v4 summary.

---

## §8 Remaining architecture gates

| Gate | Result |
|------|--------|
| v2 exact pin + `dm_union_graph_v5` identity | **PASS** |
| world-object-v2 vocabulary (no `latest`) | **PASS** |
| Completeness invariant (=0 unaccounted) | **PASS** |
| Read-only tree digest | **PASS** |
| v1 analyzer unchanged (#522 semantics preserved) | **PASS** |
| Kind adapters (12 + mechanics) | **PASS** |
| Relationship inventory sums to edge count | **PASS** |
| Durable adoption seam | **FAIL** (MISSING) |
| Postgres adoption | **BLOCKED** |
| Whole-graph READY | **FAIL** (blockers remain) |

---

## §9 Stop conditions

None triggered as defects. Expected NOT_READY. Analyzer did not coerce predicates, invent `domain=other`, map `located_in→located_at`, or mutate Eldyrwild graph data.

---

## §10 Verification

```bash
cd /home/drakosfire/Projects/DungeonOverMind/DungeonMindBuddy-wt-whole-world-repin
uv sync --locked
uv run ruff check apps/live_control_server/integrations/dungeonmind_kernel \
  tests/test_dungeonmind_whole_world_conformance.py \
  tests/test_dungeonmind_whole_world_conformance_v2.py
uv run pytest tests/test_dungeonmind_whole_world_conformance.py \
  tests/test_dungeonmind_whole_world_conformance_v2.py -q
uv run pytest tests/test_dungeonmind_world_object_conformance_bridge.py \
  tests/test_dungeonmind_cutover_readiness_audit.py -q
```

Result: **72 passed**, ruff clean.

Fixture: `tests/fixtures/dungeonmind_kernel/eldyrwild_post_v26_conformance_v1.json`  
(compact v2 report via `compact_whole_world_conformance_report_v2`; `mapping_buckets` stripped; includes `classification_inventory` + full relationship/blocker residual ledger).  
CI protects the fixture via `test_committed_eldyrwild_fixture_is_durable_regression_contract` without requiring `out/`.

---

## §11 Files touched

| Path | Change |
|------|--------|
| `apps/live_control_server/integrations/dungeonmind_kernel/whole_world_conformance_v2.py` | CREATE |
| `apps/live_control_server/integrations/dungeonmind_kernel/__init__.py` | export v2 symbols |
| `tests/test_dungeonmind_whole_world_conformance_v2.py` | CREATE |
| `tests/fixtures/dungeonmind_kernel/eldyrwild_post_v26_conformance_v1.json` | CREATE (real run) |
| `Docs/Plans/HANDOFF-kernel-dungeonmind-whole-world-repin-post-v26.md` | CREATE (this doc) |

Out of scope honored: v1 file behavior unchanged; Eldyrwild graph not mutated; DungeonMind repo not modified.

---

## §12 Nonclaims

```text
No DungeonMind vocabulary was changed.
No new relationship mapping was accepted.
No Eldyrwild data was migrated.
No DungeonMind graph revision was published.
No PostgreSQL adoption was attempted.
No source visibility policy was invented.
No alias-level evidence was manufactured.
No Buddy contribution history was discarded.
No fictional time was derived from session IDs.
uses_statblock was not mapped to threatens.
located_in was not mapped to located_at.
attacks was not mapped to threatens.
contains was not synthesized as an inverse relationship.
The current Buddy head was not used as a substitute for the pinned source revision.
WHOLE_GRAPH_ADOPTION_NOT_READY remains correct because blockers remain.
```

---

## §12b Successor input (relationship endpoint pressure)

Mapped predicates with incomplete endpoint admission (world-object-v2 ranges unchanged from v1):

| Predicate | Admitted | Gap | Example gap pairs |
|-----------|---------:|----:|-------------------|
| `member_of` → `dnd5e:member_of` | 3/24 | 21 | pc→group (12), pc→party (6), npc→party, group→party, group→item |
| `participates_in` → `dnd5e:participates_in` | 2/9 | 7 | pc→group (3), group→group, group→location, item→pc |
| `threatens` → `dnd5e:threatens` | 5/6 | 1 | group→group |

`located_in` (48) is not spatial-only: pairs include item→location (12), location→location (11), npc→location (7), group→location (5), item→pc (2), encounter→item, location→party, mystery→location. Do not assume containment ≡ `dnd5e:located_at`.

Immediate next DungeonMind PR: **DND: publish adjudicated Eldyrwild relationship vocabulary v3** from this inventory.

---

## §13 Review cycles

**1** — acceptance-contract / provenance fixes (assertion metadata pin, durable fixture regression, handoff anchors).
