# HANDOFF — Generalized Buddy world object → DungeonMind v3 conformance

**Created:** 2026-08-07  
**Status:** IMPLEMENTATION COMPLETE — proof + audit follow-on  
**Repository:** `Drakosfire/DungeonMindBuddy`  
**Flow:** KERNEL / STATBLOCK  
**Canonical path:** `Docs/Plans/HANDOFF-statblock-dungeonmind-world-object-conformance.md`

**Suggested branch:** `kernel/dungeonmind-world-object-conformance`  
**Suggested PR title:** `STATBLOCK: bridge exact Buddy world objects into DungeonMind v3`

---

## §25 — Repository identity

| Anchor | SHA / ref |
|--------|-----------|
| Buddy base (`main` at branch start) | `6fac8686c55a6cf9e513b7dbb47cfaa3baa964ae` |
| Branch | `kernel/dungeonmind-world-object-conformance` |
| Implementation commit | `09b47de44078199b8ab5affa93f6a390cf2eb7e3` |
| PR | [#521](https://github.com/Drakosfire/DungeonMindBuddy/pull/521) |
| DungeonMind dependency pin | `8095321ed011b8a38640615a90cbc9efaf385e8c` |
| Predecessor handoffs | #518 Threat bridge, #519 shadow, #520 cutover audit |

---

## §25 — New graph contract summary

| Item | Identity |
|------|----------|
| Generic binding schema | `dmb_world_object_statblock_binding_v1` |
| Edge field | `statblock_binding` (additive; legacy `threat_statblock_binding` unchanged) |
| Binding id | `compute_world_object_statblock_binding_id(...)` → `world-object-statblock-binding:{digest}` |
| Parse entry | `parse_uses_statblock_binding_assertion` → exactly one of legacy/generic |
| Eligible kinds | `threat`, `npc` only for generic bindings |
| Legacy rule | `threat_statblock_binding` requires `kind=threat` source node |
| PC / creature / monster | generic binding rejected at schema, merge, validate, and bridge |
| Mixed legacy+generic | allowed when semantic keys differ; same semantic key → fail closed |

---

## §25 — Public bridge surface

| Export | Role |
|--------|------|
| `bridge_exact_buddy_world_object(root, world_id, revision_id, node_id, campaign_id=None)` | General entrypoint: Threat, NPC, PC |
| `bridge_exact_buddy_threat(...)` | Threat-only compatibility wrapper (`required_source_kind=threat`) |
| `map_buddy_world_object_id` | `obj:dmb:{node_id}` |
| `map_buddy_threat_object_id` | alias of world-object mapper |
| `ThreatConformanceBridgeError` | stable `reason` codes incl. `duplicate_semantic_attachment`, `pc_mechanics_attachment_forbidden` |

Private: `_bridge_buddy_world_object_revision`, `_load_exact_buddy_revision_bridge_source` — not exported.

---

## §25 — Mapping table

| Buddy source | DungeonMind target |
|--------------|-------------------|
| `kind=threat` | `dnd5e:threat` |
| `kind=npc` | `dnd5e:npc` |
| `kind=pc` | `dnd5e:player_character` (semantic only; zero mechanics attachments) |
| legacy `threat_statblock_binding` | normalized → mechanics when `kind=threat` |
| generic `statblock_binding` | normalized → mechanics when `kind=threat|npc` |
| `uses_statblock` on PC | `pc_mechanics_attachment_forbidden` |
| contextual hostility edges | not synthesized; `dnd5e:threatens` never added by bridge |

Provider/digest/resource mapping unchanged from #518.

---

## §25 — Proof matrix (§13 letters)

| Letter | Case | Result | Test name(s) |
|--------|------|--------|--------------|
| A | Historical Threat legacy primary | PASS | `test_matrix_a_one_threat_one_binding_hydrates` (`test_dungeonmind_world_object_conformance_bridge.py`) |
| B | Generic Threat primary → same DM semantics as A | PASS | `test_matrix_b_generic_threat_primary_matches_legacy_semantics` |
| C | NPC + exact mechanics + zero hostility | PASS | `test_matrix_c_npc_exact_mechanics_zero_hostility` |
| D | NPC zero mechanics | PASS | `test_matrix_d_npc_zero_mechanics` |
| E | NPC hostility evidence independent | PASS | `test_matrix_e_npc_hostility_evidence_does_not_change_identity` |
| F | NPC five-role + reverse order | PASS | `test_matrix_f_npc_five_role_multiplicity_and_reverse_order`, `test_npc_five_role_cardinality_enumerate_hydrate_and_reverse_order` |
| G | PC semantic identity only | PASS | `test_matrix_g_pc_semantic_identity_only`, `test_canonical_public_bridge_entrypoint_maps_pc_semantics_only` |
| H | Mixed legacy primary + generic phase | PASS | `test_matrix_h_mixed_legacy_primary_and_generic_phase` |
| I | Mixed duplicate primary same resource | PASS (fail-closed; no silent dedupe) | `test_matrix_i_mixed_duplicate_primary_same_resource_fails_closed` |
| J | Exact revision R1 beats head R2 | PASS | `test_matrix_j_exact_revision_r1_beats_head_r2`, `test_bridge_pins_old_revision_and_ignores_newer_head` |

### §14 source-contract adversarial (graph)

| Case | Result | Test name(s) |
|------|--------|--------------|
| generic on pc/creature/monster | FAIL | `test_parse_uses_statblock_rejects_generic_pc_kind_via_model`, `test_world_object_statblock_binding_rejects_ineligible_kind`, `test_kernel_merge_rejects_generic_binding_on_pc` |
| legacy Threat binding on npc | FAIL | `test_kernel_merge_rejects_legacy_binding_on_npc` |
| uses_statblock neither / both payloads | FAIL | `test_parse_uses_statblock_rejects_neither_payload`, `test_parse_uses_statblock_rejects_both_legacy_and_generic_payloads` |
| binding.world_object_kind ≠ source kind | FAIL | `test_parse_uses_statblock_rejects_generic_kind_mismatch_with_source`, `test_persisted_store_rejects_generic_adversarial_mutations` |
| forged generic binding_id / edge_id | FAIL | `test_persisted_store_rejects_generic_adversarial_mutations`, `test_fail_forged_generic_binding_and_edge_ids` |

### §15 bridge adversarial

| Case | Result | Test name(s) |
|------|--------|--------------|
| unsupported kind | FAIL | `test_fail_unsupported_kind` |
| PC mechanics attachment | FAIL | `test_fail_pc_mechanics_attachment` |
| duplicate semantic attachment | FAIL | `test_fail_duplicate_semantic_attachment_generic_npc`, `test_matrix_i_*` |
| read-only tree digest multi-kind | PASS | `test_bridge_execution_is_read_only_against_source_graph` |

---

## §25 — #520 ledger delta

**Closed (synthetic PASS):**

- Threat semantic mapping
- NPC semantic mapping
- NPC exact mechanics mapping (synthetic)
- PC world-object semantic mapping
- Exact graph/mechanics identity, hostility independence, zero/one/many, roles, no implicit winner
- **BRIDGE_MAPPING** — removed from blocker set

**Still FAIL / NOT YET PROVEN:**

- Real Threat/NPC mechanics dogfood (`graph_data/` has zero durable `uses_statblock`)
- Shared product projection (`PRODUCT_PROJECTION`)
- Local Buddy authority kill / dark cutover
- Poisoned fallback: `NOT_EXERCISED` (blocked by `PRODUCT_PROJECTION`)

**Disposition:** `CUTOVER_NOT_READY`

**Remaining blockers:** `REAL_DATA_INCOMPATIBILITY`, `PRODUCT_PROJECTION`

---

## §25 — Verification commands / results

```bash
cd /home/drakosfire/Projects/DungeonOverMind/DungeonMindBuddy
uv run ruff check \
  tests/test_statblock_binding_graph_contract.py \
  tests/test_dungeonmind_world_object_conformance_bridge.py \
  tests/test_dungeonmind_world_object_conformance_generalized.py \
  tests/test_dungeonmind_cutover_readiness_audit.py

uv run pytest \
  tests/test_statblock_binding_graph_contract.py \
  tests/test_dungeonmind_world_object_conformance_bridge.py \
  tests/test_dungeonmind_threat_hydration_shadow.py \
  tests/test_dungeonmind_cutover_readiness_audit.py \
  tests/test_dungeonmind_world_object_conformance_generalized.py \
  -q --tb=line
```

(Paste pytest summary from agent run below parent merge.)

**Agent run (2026-08-07):** `128 passed, 10 warnings in 10.90s` — ruff clean on scoped changed paths.

Note: full `pytest -m "not integration"` still shows pre-existing main failures (eldyrwild contribution_id staleness / bootstrap invalid_bundle / graph kernel boundary allowlist), reproduced on clean `origin/main` without this branch; not introduced here.

---

## §25 — Changed paths

| Path | Role |
|------|------|
| `tests/test_statblock_binding_graph_contract.py` | Generic binding adversarial + publish/reload proofs |
| `tests/test_dungeonmind_world_object_conformance_generalized.py` | Matrix B–J + bridge adversarial |
| `tests/test_dungeonmind_cutover_readiness_audit.py` | Flip BRIDGE_MAPPING; NPC/PC PASS gates |
| `Docs/Plans/HANDOFF-statblock-dungeonmind-world-object-conformance.md` | This handback |
| `Docs/Plans/HANDOFF-statblock-dungeonmind-cutover-readiness-proof.md` | #520 ledger delta |

Implementation (pre-merged on branch, not re-implemented here):

- `src/graph_memory/union_supergraph/statblock_binding.py`
- `src/graph_memory/union_supergraph/model.py`, `validate.py`
- `src/graph_memory/kernel/contribution_merge.py`, `world_projection.py`
- `src/graph_memory/projection/world_projection.py`
- `apps/live_control_server/integrations/dungeonmind_kernel/world_object_conformance_bridge.py`
- `apps/live_control_server/integrations/dungeonmind_kernel/__init__.py`

---

## §25 — Remaining nonclaims

```text
DungeonMind is not Buddy runtime mechanics authority
Buddy _hydrate_binding still determines product Threat hydration
No durable real-domain uses_statblock dogfood in graph_data
Shared product projection does not consume bridge
Dark-cutover / authority promotion not performed
PC mechanics authority cutover OUT OF CLAIM (DM forbids PC on mechanics-eligible kinds)
Poisoned A-vs-B fallback NOT_EXERCISED until PRODUCT_PROJECTION lands
Historical Threat legacy fixtures intentionally not rewritten to generic schema
```

---

## Successor

```text
STATBLOCK: publish real durable Threat (+ ideally NPC) uses_statblock dogfood
→ re-enable shadow full_match on real data
→ promote DM hydrate behind existing Buddy API (PRODUCT_PROJECTION)
→ then local-authority kill + poisoned-fallback become exercisable
```
