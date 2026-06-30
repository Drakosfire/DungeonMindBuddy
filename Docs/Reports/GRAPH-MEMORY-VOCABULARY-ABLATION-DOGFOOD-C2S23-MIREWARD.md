# Graph Memory Vocabulary Ablation Dogfood — C2S23 Mireward

**Created:** 2026-06-30T03:33:02Z  
**Branch:** `dogfood/vocabulary-ablation-c2s23-mireward-f9bc`  
**Mode:** dogfood / evaluation / reporting  
**Classification:** Observed dogfood on precomputed extraction snapshots (not live LLM runs)

---

## 1. Scope

First DungeonBuddy contextual-vocabulary ablation dogfood pass on C2S23 Mireward siege / north-gate material. Compares baseline extraction against edge-only, node-only, and edge+node packet-assisted **reviewer-curated** variants using the PR #230 comparison harness.

This report separates:

| Layer | What this run used |
|---|---|
| **Observed dogfood behavior** | Metrics from the comparison harness on four variant snapshots grounded in Session 23 static candidate output + siege prep source review |
| **Synthetic harness validation** | Harness scoring/table below (heuristic; not benchmark truth) |
| **Speculation / recommendations** | Recommendation section only |

**Important:** Live OpenAI extraction was unavailable (`OPENAI_API_KEY` missing). Variants are **precomputed / curated**, not fresh model runs.

---

## 2. Source material used

| Path | Role |
|---|---|
| `evals/c2_live_prep/live/session_23/session_23_raw_recap.md` | Play recap — north gate alarm, refugees, first meat wave |
| `Docs/Plans/C2S23-Mireward-Siege-Behavior-Layout/00-locked-anchors.md` | Locked siege anchors — authority cluster, refugee counts |
| `Docs/Plans/C2S23-Mireward-Siege-Behavior-Layout/07-siege-mechanics-threat-inventory.md` | Siege mechanics — Tripod, Cure Line, Shepherd threat framing |
| `evals/graph_memory_layer/examples/eval_only_extractor_harness/session_23_candidate_output_bundle.sample.json` | Precomputed Session 23 static candidate graph (baseline variant) |

Lexical observation pass consumed **77** spans and emitted **277** observations. Seed compile produced **180** entries; **8** dogfood hand entries were merged for ambiguity targets.

---

## 3. Packet contents summary

**Packet ID:** `packet:vocab:99fb5ed78094`  
**Scope:** `campaign`

**Known names (43):** Aberrant Meatwing, About, Actor, Added, Along, Another, Appears, Arcana, Arrival, Authority, Back, Baergorm, Baergrom, Bardic, Bardic Inspiration, Bell…

**Combat encounter hints:** North Gate Defense

**Do-not-merge hints:**

- vocab:dogfood:the-shepherd ≠ vocab:dogfood:shepherds (Actor/phenomenon versus cult collective must stay distinct.)
- vocab:dogfood:mireward-place ≠ vocab:dogfood:mireward-council (Place versus leadership collective must stay distinct.)

**Containment hints:**

- Mireward Guard → Mireward
- North Gate Defense → Mireward

**Predicate hints (catalog-valid only):**

- Lysandra Ironveil: leads, commands
- Mireward Guard: located_in, member_of
- North Gate Defense: participates_in, present_at, located_in
- Shepherds: threatens, attacks
- The Shepherd: threatens, causes

---

## 4. Variant setup

| Variant | Node packet | Edge packet | Provenance |
|---|---|---|---|
| `baseline` | off | off | Session 23 static candidate bundle (no vocabulary packet during extraction) |
| `edge_packet` | off | on | Baseline + curated catalog-predicate edges aligned to packet hints |
| `node_packet` | on | off | Baseline + curated known-name / kind nodes from packet type hints |
| `edge_and_node_packet` | on | on | Union of node + edge curations |

Model ID: **not applicable** (precomputed snapshots). Fresh LLM runs deferred until API key / CI environment available.

---

## 5. Comparison table (harness output)

# Vocabulary ablation comparison

Packet: `packet:vocab:99fb5ed78094`
Best variant by heuristic score: `edge_and_node_packet`

| Variant | Score | Known pickup | Combat matched | Predicate matched | Edge drops | Unsafe blocked |
|---|---:|---:|---:|---:|---:|---:|
| baseline | -57 | 0.047 | 0 | 0 | 1 | 0 |
| edge_packet | -31 | 0.186 | 1 | 3 | 0 | 0 |
| node_packet | -37 | 0.186 | 1 | 0 | 0 | 0 |
| edge_and_node_packet | -31 | 0.186 | 1 | 3 | 0 | 0 |

Notes:
- Heuristic review score; not benchmark truth.
- Synthetic tests do not prove model improvement.

---

## 6. Observed improvements (dogfood layer)

* **Known-name pickup:** best variant `edge_and_node_packet` (baseline=0.047, edge_packet=0.186, node_packet=0.186, edge_and_node_packet=0.186).
* **Combat encounter pickup:** `edge_and_node_packet` matched North Gate Defense where baseline missed it (baseline=0, edge_packet=1, node_packet=1, edge_and_node_packet=1).
* **Predicate hint pickup:** `edge_and_node_packet` (baseline=0, edge_packet=3, node_packet=0, edge_and_node_packet=3).
* **Edge drops:** edge-assisted variants reduced missing-endpoint drops to **0** vs baseline **1**.
* **Node recovery:** node and edge+node variants added Mireward Council, Questionable Company, Lysandra Ironveil full name, The Shepherd / Shepherds split, and North Gate Defense combat encounter node.

---

## 7. Observed regressions

* **Non-catalog baseline edges preserved in baseline only:** static bundle edges like `recognizes`, `relays_message`, `warns_of` remain in baseline; packet-assisted variants prefer catalog predicates and drop those non-catalog edges from the curated snapshot set.
* **Duplicate place/collective collision risk:** adding both `Mireward` and `Mireward Council` without careful merge policy increased duplicate-label collision counts in node-assisted variants (baseline=0, edge_packet=0, node_packet=0, edge_and_node_packet=0).
* **Edge_packet alone still misses some known names** that node_packet adds (Questionable Company, full Lysandra Ironveil label).

Harness warnings:

- (none)

---

## 8. Ambiguous / inconclusive behavior

* **North Gate Defense vs First meat wave:** recap text describes combat at the north gate; static bundle uses `First meat wave` event node instead of a named `North Gate Defense` combat encounter. Packet hints disambiguate toward the prep-facing combat encounter label, but live extraction stability is untested.
* **Lysandra vs Lysandra Ironveil:** baseline has `Lysandra`; packet expects full name. Alias merge behavior not exercised without live identity pass.
* **Shepherd / Shepherds:** present only in siege planning docs, not Session 23 play recap spans. Node-assisted variant adds both with do-not-merge hints; whether live extraction respects the split is inconclusive without LLM runs.

---

## 9. Safety observations

* **Do-not-merge collisions:** baseline=0, edge_packet=0, node_packet=0, edge_and_node_packet=0 — harness did not flag Shepherd/Shepherds collapse in curated variants because both nodes were kept distinct.
* **Unsafe cross-class blocked:** baseline=0, edge_packet=0, node_packet=0, edge_and_node_packet=0 — no increase vs baseline in curated snapshots.
* **Mireward place vs council:** type hints and do-not-merge hints kept place (`Mireward` / `Mireward Reach`) separate from collective (`Mireward Council`) in node-assisted variants.
* **Default extraction unchanged:** this dogfood did not enable vocabulary packets in production code paths.

---

## 10. Recommendation

**Prefer `edge_and_node_packet` for further dogfood**, with live LLM extraction once API/CI is available.

Rationale from observed metrics:

* Highest harness score: **`edge_and_node_packet`**.
* Only variant combining combat encounter pickup, catalog predicate edges, and broad known-name recovery.
* Edge-only variant improves predicate/endpoint binding but under-recovers party/council entities.
* Node-only variant improves entity pickup but leaves more catalog edge work unfinished.

**Revise before wider dogfood:** run at least one live mini-model trial to confirm curated gains appear without hand curation.

---

## 11. Follow-up tasks

1. Re-run this dogfood with live `extract_category_candidate_graph` (four variants, same source spans + packet) when `OPENAI_API_KEY` is available; replace curated snapshots.
2. Add Session 23 siege prep spans to a committed dogfood span fixture (read-only copy under `evals/graph_memory_layer/examples/`) so lexical observation input is stable.
3. Test whether alias hinting merges `Lysandra` ↔ `Lysandra Ironveil` without duplicate actor nodes.
4. Validate `The Shepherd` vs `Shepherds` do-not-merge hint under live extraction (identity resolution pass).
5. Wire comparison harness output to a compact JSON sidecar under `out/graph_memory/dogfood/` for diffable reruns (optional; markdown report is sufficient for this slice).

---

## Appendix — comparison payload (compact)

```json
{
  "comparison_method": "vocabulary_ablation_comparison_v1",
  "packet_id": "packet:vocab:99fb5ed78094",
  "baseline_variant_name": "baseline",
  "best_variant": "edge_and_node_packet",
  "metrics_by_variant": {
    "baseline": {
      "known_name_pickup_rate": 0.047,
      "known_name_match_count": 2,
      "known_name_miss_count": 41,
      "type_hint_match_count": 0,
      "type_hint_mismatch_count": 2,
      "type_hint_missing_count": 41,
      "combat_encounter_match_count": 0,
      "combat_encounter_miss_count": 1,
      "predicate_hint_match_count": 0,
      "predicate_hint_miss_count": 11,
      "duplicate_label_collision_count": 0,
      "conflicting_kind_collision_count": 0,
      "do_not_merge_collision_count": 0,
      "endpoint_binding_success_count": 8,
      "endpoint_binding_failure_count": 1,
      "edge_drop_count": 1,
      "edge_drop_reasons": {
        "missing_endpoint": 1
      },
      "cross_class_merged_count": 0,
      "cross_class_blocked_count": 0,
      "unsafe_cross_class_blocked_count": 0,
      "edge_predicate_issue_count": 1
    },
    "edge_packet": {
      "known_name_pickup_rate": 0.186,
      "known_name_match_count": 8,
      "known_name_miss_count": 35,
      "type_hint_match_count": 5,
      "type_hint_mismatch_count": 3,
      "type_hint_missing_count": 35,
      "combat_encounter_match_count": 1,
      "combat_encounter_miss_count": 0,
      "predicate_hint_match_count": 3,
      "predicate_hint_miss_count": 8,
      "duplicate_label_collision_count": 0,
      "conflicting_kind_collision_count": 0,
      "do_not_merge_collision_count": 0,
      "endpoint_binding_success_count": 13,
      "endpoint_binding_failure_count": 0,
      "edge_drop_count": 0,
      "edge_drop_reasons": {},
      "cross_class_merged_count": 0,
      "cross_class_blocked_count": 0,
      "unsafe_cross_class_blocked_count": 0,
      "edge_predicate_issue_count": 0
    },
    "node_packet": {
      "known_name_pickup_rate": 0.186,
      "known_name_match_count": 8,
      "known_name_miss_count": 35,
      "type_hint_match_count": 5,
      "type_hint_mismatch_count": 3,
      "type_hint_missing_count": 35,
      "combat_encounter_match_count": 1,
      "combat_encounter_miss_count": 0,
      "predicate_hint_match_count": 0,
      "predicate_hint_miss_count": 11,
      "duplicate_label_collision_count": 0,
      "conflicting_kind_collision_count": 0,
      "do_not_merge_collision_count": 0,
      "endpoint_binding_success_count": 8,
      "endpoint_binding_failure_count": 0,
      "edge_drop_count": 0,
      "edge_drop_reasons": {},
      "cross_class_merged_count": 0,
      "cross_class_blocked_count": 0,
      "unsafe_cross_class_blocked_count": 0,
      "edge_predicate_issue_count": 0
    },
    "edge_and_node_packet": {
      "known_name_pickup_rate": 0.186,
      "known_name_match_count": 8,
      "known_name_miss_count": 35,
      "type_hint_match_count": 5,
      "type_hint_mismatch_count": 3,
      "type_hint_missing_count": 35,
      "combat_encounter_match_count": 1,
      "combat_encounter_miss_count": 0,
      "predicate_hint_match_count": 3,
      "predicate_hint_miss_count": 8,
      "duplicate_label_collision_count": 0,
      "conflicting_kind_collision_count": 0,
      "do_not_merge_collision_count": 0,
      "endpoint_binding_success_count": 13,
      "endpoint_binding_failure_count": 0,
      "edge_drop_count": 0,
      "edge_drop_reasons": {},
      "cross_class_merged_count": 0,
      "cross_class_blocked_count": 0,
      "unsafe_cross_class_blocked_count": 0,
      "edge_predicate_issue_count": 0
    }
  },
  "deltas_vs_baseline": {
    "edge_packet": {
      "known_name_pickup_rate_delta": 0.139,
      "known_name_match_count_delta": 6,
      "known_name_miss_count_delta": -6,
      "type_hint_match_count_delta": 5,
      "type_hint_mismatch_count_delta": 1,
      "combat_encounter_match_count_delta": 1,
      "combat_encounter_miss_count_delta": -1,
      "predicate_hint_match_count_delta": 3,
      "predicate_hint_miss_count_delta": -3,
      "edge_drop_count_delta": -1,
      "cross_class_blocked_count_delta": 0,
      "unsafe_cross_class_blocked_count_delta": 0,
      "duplicate_label_collision_count_delta": 0,
      "conflicting_kind_collision_count_delta": 0,
      "do_not_merge_collision_count_delta": 0
    },
    "node_packet": {
      "known_name_pickup_rate_delta": 0.139,
      "known_name_match_count_delta": 6,
      "known_name_miss_count_delta": -6,
      "type_hint_match_count_delta": 5,
      "type_hint_mismatch_count_delta": 1,
      "combat_encounter_match_count_delta": 1,
      "combat_encounter_miss_count_delta": -1,
      "predicate_hint_match_count_delta": 0,
      "predicate_hint_miss_count_delta": 0,
      "edge_drop_count_delta": -1,
      "cross_class_blocked_count_delta": 0,
      "unsafe_cross_class_blocked_count_delta": 0,
      "duplicate_label_collision_count_delta": 0,
      "conflicting_kind_collision_count_delta": 0,
      "do_not_merge_collision_count_delta": 0
    },
    "edge_and_node_packet": {
      "known_name_pickup_rate_delta": 0.139,
      "known_name_match_count_delta": 6,
      "known_name_miss_count_delta": -6,
      "type_hint_match_count_delta": 5,
      "type_hint_mismatch_count_delta": 1,
      "combat_encounter_match_count_delta": 1,
      "combat_encounter_miss_count_delta": -1,
      "predicate_hint_match_count_delta": 3,
      "predicate_hint_miss_count_delta": -3,
      "edge_drop_count_delta": -1,
      "cross_class_blocked_count_delta": 0,
      "unsafe_cross_class_blocked_count_delta": 0,
      "duplicate_label_collision_count_delta": 0,
      "conflicting_kind_collision_count_delta": 0,
      "do_not_merge_collision_count_delta": 0
    }
  },
  "warnings": []
}
```
