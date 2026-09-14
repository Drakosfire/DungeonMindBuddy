# Stage 4L PC Identity Normalization Repair: Relationship Analysis

**Created:** 2026-09-14  
**PR:** #714 — `DOGFOOD-CONTINUITY: build Campaign 1 memory through Session 10`  
**Exact Starting Head:** `78aff372e2e419a67018805f5803a88c6fd111f0`  
**Authoritative Rehearsal World Revision:** `rev:b82db72693c27e0218026fd1ff514a68`  
**Model Calls:** `0` (100% zero-model evidence analysis)  
**Cohort:** Campaign 1, Sessions 1–10  
**Denominator:** 276 extracted relationship denominator  

---

## 1. Executive Result

This report provides the causal accounting of relationship publication for Campaign 1 Sessions 1–10 under the authoritative rehearsal World revision `rev:b82db72693c27e0218026fd1ff514a68`.
Out of 276 extracted relationships, **219 are published (79.3%)** and **57 remain unpublished**.
Among the published relationships, **208 are truthful and faithful** (75.4% truthful publication rate) and **11 rely on semantically lossy coercions** (`governs` → `owns`, `refers_to` → `associated_with`).
Of the 57 remaining rejects, **9 are correctly rejected bad extractions**, while the remaining are blocked by weak/missing endpoint typing, narrow ontology contracts, or unmapped predicates. Crucially, **blocked collisions due to PC kind mismatch dropped to 0**.

---

## 2. Reconciled Sequential Survival Funnel

Cumulative survival across sequential stages:

```text
extracted:                              276 (100.0%)
  ↓
endpoint_ids_present:                   276 (100.0%)
  ↓
endpoints_resolve_to_world_objects:     276 (100.0%)
  ↓
predicate_accepts_endpoint_kinds:       219 (79.3%)
  ↓
published:                              219 (79.3%)
```

---

## 3. PC Continuity Table

| Player Character | Candidate Relationships | Published Relationships | Remaining Rejects |
| :--- | :---: | :---: | :---: |
| Baergrom | 13 | 13 | 0 |
| Bonogo | 20 | 20 | 0 |
| Caelynn | 15 | 12 | 3 |
| Ephanna | 18 | 15 | 3 |
| Karsemine | 13 | 13 | 0 |
| Stafl | 14 | 10 | 4 |

---

## 4. Rejection Decomposition

Every one of the 57 unpublished relationships is classified into one primary diagnostic category:

| Primary Category | Count | Share (%) |
| :--- | :---: | :---: |
| `endpoint_kind_missing_or_weak` | 25 | 43.9% |
| `ontology_endpoint_contract_too_narrow` | 14 | 24.6% |
| `extraction_semantically_bad` | 9 | 15.8% |
| `predicate_unmapped` | 9 | 15.8% |

---

## 5. Most Common Rejection Signatures

The most frequent rejection signatures (Reason × Predicate × Subject Kind × Object Kind) across unpublished relationships:

| Reason | Predicate | Subject Kind | Object Kind | Count |
| :--- | :--- | :--- | :--- | :---: |
| `duplicate_node_reconciliation_as_edge:same_as` | `same_as` | `item` | `mystery` | 4 |
| `works_with_rejects_location_endpoint` | `works_with` | `npc` | `location` | 3 |
| `unmapped_organization_kind_needs_faction_or_group` | `member_of` | `npc` | `organization` | 3 |
| `presence_in_or_on_item_unsupported` | `present_at` | `player_character` | `item` | 2 |
| `weak_mystery_typing_replaces_concrete_entity` | `part_of` | `creature` | `mystery` | 2 |
| `duplicate_node_reconciliation_as_edge:identified_as` | `identified_as` | `item` | `mystery` | 1 |
| `weak_mystery_typing_replaces_concrete_entity` | `attacks` | `mystery` | `group` | 1 |
| `weak_mystery_typing_replaces_concrete_entity` | `participates_in` | `mystery` | `mystery` | 1 |
| `weak_mystery_typing_replaces_concrete_entity` | `present_at` | `item` | `mystery` | 1 |
| `weak_mystery_typing_replaces_concrete_entity` | `part_of` | `location` | `mystery` | 1 |
| `weak_mystery_typing_replaces_concrete_entity` | `located_in` | `item` | `mystery` | 1 |
| `beast_goat_typed_as_npc_instead_of_creature` | `owns` | `npc` | `npc` | 1 |
| `attends_participates_in_rejects_social_gatherings` | `attends` | `player_character` | `group` | 1 |
| `beast_goat_typed_as_npc_instead_of_creature` | `carries` | `npc` | `player_character` | 1 |
| `weak_mystery_typing_replaces_concrete_entity` | `part_of` | `item` | `mystery` | 1 |
| `beast_goat_typed_as_npc_instead_of_creature` | `holds` | `item` | `npc` | 1 |
| `weak_mystery_typing_replaces_concrete_entity` | `threatens` | `mystery` | `group` | 1 |
| `unmapped_predicate:mission_targets` | `mission_targets` | `thread` | `location` | 1 |
| `unmapped_predicate:mission_focus` | `mission_focus` | `thread` | `location` | 1 |
| `unmapped_predicate:mission_targets` | `mission_targets` | `mystery` | `item` | 1 |
| `carries_rejects_item_carrying_item` | `carries` | `item` | `item` | 1 |
| `unmapped_predicate:controls_comms_with` | `controls_comms_with` | `player_character` | `npc` | 1 |
| `weak_mystery_typing_replaces_concrete_entity` | `participates_in` | `faction` | `mystery` | 1 |
| `weak_mystery_typing_replaces_concrete_entity` | `present_at` | `player_character` | `mystery` | 1 |
| `part_of_rejects_item_part_of_creature` | `part_of` | `item` | `creature` | 1 |

---

## 6. Reconciled Bottleneck Quantification

All metrics derive mechanically from the per-edge disposition in `relationships.json`:

- **Total Extracted Relationships:** 276
- **Worthy / Source-Supported Relationships:** 259
- **Worthy Published Relationships:** 211
- **Blocked by Identity Resolution:** 0
- **Blocked by Endpoint Typing:** 25
- **Blocked by Narrow Ontology Contract:** 14
- **Blocked by Unmapped Predicates:** 9
- **Correctly Rejected Bad Extractions:** 9
- **Published Relying on Lossy Coercions:** 11
- **Truthful Publication Rate (Excluding Lossy):** 75.4%
- **Share of Loss Involving Weak / Mystery Typing:** 43.9%
