# HANDOFF — DungeonBuddy → DungeonMind bridge cutover-readiness proof

**Created:** 2026-08-07  
**Status:** COMPLETE — adversarial disposition  
**Repository:** `Drakosfire/DungeonMindBuddy` (+ contract evidence from `Drakosfire/DungeonMind`)  
**Flow:** KERNEL / STATBLOCK  
**Canonical path:** `Docs/Plans/HANDOFF-statblock-dungeonmind-cutover-readiness-proof.md`

**Suggested branch:** `kernel/dungeonmind-cutover-readiness-proof`  
**Suggested PR title:** `STATBLOCK: cutover-readiness proof (CUTOVER_NOT_READY)`

---

## Repository state

| Anchor | SHA / ref |
|--------|-----------|
| DungeonMind main / PR #23 merge | `8095321ed011b8a38640615a90cbc9efaf385e8c` |
| DungeonMindBuddy main (#519 merge; includes #518) | `f79940e8e3f005a2500fca3b780d3327b6bf9a41` |
| Branch | `kernel/dungeonmind-cutover-readiness-proof` |
| Implementation commit | `c53e4569017f007cc77aa598b60955917b8df60e` |
| PR | [#520](https://github.com/Drakosfire/DungeonMindBuddy/pull/520) |
| Buddy `dungeonmind` dependency pin | `8095321ed011b8a38640615a90cbc9efaf385e8c` |

Open adjacent Buddy PRs inspected: #517 (PWO01 docs), #516 (benchmark), #510 (Build refs), #497 (navbar), #442 (transfer). No shared-file collisions with this audit.

---

## Contract actually exercised

| Contract surface | Exact identity |
|------------------|----------------|
| Semantic profile | `dungeonmind.dnd5e` / `dnd5e-profile-v3` (via pinned `dungeonmind` / `dungeonmind_dnd`) |
| World-object vocabulary | `world-object-v1` terms including `dnd5e:threat`, `dnd5e:npc`, `dnd5e:player_character` |
| Mechanics-eligible kinds | `WORLD_OBJECT_MECHANICS_ELIGIBLE_KINDS = {dnd5e:threat, dnd5e:npc}` — **PC not eligible** |
| Binding schema | `dmdnd_world_object_mechanics_binding_v1` (`mechbind:…`) |
| Statblock attachment schema | `dmdnd_statblock_mechanics_attachment_v1` (`mechattach:…`) |
| Roles | `primary`, `alternate`, `phase`, `encounter_variant`, `template` |
| Qualifiers | `phase_key`, `variant_label` (Buddy string grammar preserved in #518/#519) |
| Resource ref | `ruleset_id=dnd5e`, `provider_id=dungeonmind.statblocks`, `resource_schema=dungeonmind.dungeonbuddy-statblocks.1.0.0`, bare `payload_sha256` |
| Contextual hostility | `dnd5e:threatens` **independent** of persistent kind / mechanics (ADR-0013); Buddy bridge never synthesizes it |
| Historical B.3a | `DndThreatMechanicsBinding` retained; Threat transport unchanged |

Predecessor contract: **present and materially as accepted**. Disposition is **not** “predecessor missing.”

---

## Mapping table

### Threat

```text
Buddy kind=threat + uses_statblock*
  → bridge_exact_buddy_threat (#518)
  → obj:dmb:<node_id> / dnd5e:threat + mechbind + mechattach*
  → (product) still ThreatQueryHydration via Buddy _hydrate_binding
  → (optional) shadow log only (#519)
```

### NPC

```text
Buddy kind=npc (+ optional uses_statblock)
  → NO bridge
  → DM contract WOULD accept dnd5e:npc mechanics
  → product may surface npc via Threat query heuristics, but shadow marks not_eligible
  → CUTOVER GATE FAIL
```

### PlayerCharacter

```text
Buddy kind=pc
  → NO bridge to dnd5e:player_character
  → DM forbids PC on WORLD_OBJECT_MECHANICS_ELIGIBLE_KINDS
  → PC mechanics authority cutover: OUT OF CLAIM
  → PC world-object semantic bridge: FAIL (absent)
```

---

## Full proof matrix (§7–§24)

| Case | Result | Evidence |
|------|--------|----------|
| §7 A Threat + primary + zero hostility | PASS (synthetic) | #518/#519 matrix A |
| §7 B NPC + mechanics + zero hostility | FAIL | `test_canonical_public_bridge_entrypoint_rejects_npc` |
| §7 C Threat + threatens + zero mechanics | PASS (synthetic Threat) | #518 matrix B / shadow B; hostility not synthesized |
| §7 D NPC + contextual threatens | FAIL (Buddy bridge) | no NPC semantic bridge; DM vocabulary allows NPC+threatens independently |
| §7 E primary+alternate | PASS (synthetic Threat) | #518/#519 matrix C |
| §7 F primary+phase | PASS (synthetic Threat) | #518/#519 matrix D |
| §7 G encounter_variant + template (+ full five-role set) | PASS (synthetic Threat) | `test_five_role_cardinality_enumerate_hydrate_and_reverse_order` |
| §7 H zero attachments | PASS (synthetic Threat) | #518/#519 matrix B |
| §7 I PlayerCharacter | FAIL | `test_canonical_public_bridge_entrypoint_rejects_pc` |
| §7 J historical B.3a | PASS (executed on DM pin line) | `uv run pytest tests/unit/test_dnd_threat_mechanics.py tests/unit/test_dnd_world_object_mechanics.py` @ `DungeonMind-wt-main-cutover` `073ca149` (55 passed) |
| §8 Losslessness (Threat synthetic) | PASS | #518 field mapping + digest proof |
| §8 Losslessness (NPC/PC) | FAIL / NOT_APPLICABLE | no bridge |
| §9 Cardinality / no implicit winner | PASS (synthetic Threat) | five-role enumerate + hydrate-each + reverse insertion order → same semantic set |
| §10 Hostility Cartesian (Threat) | PASS (synthetic) | bridge builds zero relationships; DM binding has no threat_relationship_ids |
| §10 Hostility Cartesian (NPC) | FAIL | no NPC bridge |
| §11 Exactness adversarial (Threat bridge) | PASS | #518 fail-closed matrix |
| §12 Exact revision beats latest | PASS (synthetic Threat) | #518/#519 matrix L |
| §13 Poisoned-fallback (A vs B) | NOT_EXERCISED | blocked by `PRODUCT_PROJECTION` — no authoritative DM product path yet; cannot claim hidden Buddy recovery |
| §14 Dependency-failure no Buddy fallback | NOT_EXERCISED / BLOCKED | same as §13; current Buddy `_hydrate_binding` fails closed to typed statuses without a second hydrator (`test_product_authority_has_no_alternate_hydration_fallback`) |
| §15 Local-authority kill | FAIL | product authority still requires Buddy `get_exact_revision`; dark-cutover not wired |
| §16 Dark-cutover rehearsal | FAIL | not implemented; #519 shadow is non-authoritative |
| §17 Real Threat + uses_statblock | FAIL / NOT_APPLICABLE | Threat nodes exist; **zero** durable `uses_statblock` in `graph_data/` |
| §17 Real NPC mechanics (Lysandra) | FAIL / NOT_APPLICABLE | no durable Lysandra/`uses_statblock` mechanics object |
| §17 Real PC semantic | FAIL | kind=`pc` objects exist; no bridge |
| §18 Real multiplicity | NOT_APPLICABLE | “No current real-domain plural attachment fixture found. Multiplicity proven synthetically only.” |
| §19 Projection identity | FAIL | canonical Plan/world projection entrypoints do not consume bridge |
| §20 Surface parity Plan/Build | FAIL | `test_canonical_plan_and_world_projection_entrypoints_do_not_consume_bridge` |
| §21 Read-only | PASS (executed snapshot) | `test_bridge_execution_is_read_only_against_source_graph` |
| §22 Historical compatibility | PASS (executed) | DM unit suites above; not an inherited assumption-only row |
| §23 Import boundaries | PASS (direction) | Buddy depends on public `dungeonmind`/`dungeonmind_dnd`; DM does not import Buddy |
| §24 Performance sanity | PASS / N/A | Threat shadow loads exact graph once per response; not pathological |

---

## §28 Cutover gate answers

| Gate | Result |
|------|--------|
| Threat semantic mapping lossless | PASS (synthetic) |
| NPC semantic mapping lossless | **FAIL** |
| PC world-object semantic mapping | **FAIL** |
| Exact graph identity retained | PASS (Threat synthetic) |
| Exact mechanics identity retained | PASS (Threat synthetic) |
| Mechanics independent of hostility | PASS (Threat synthetic / DM contract) |
| Zero attachments represented correctly | PASS (Threat synthetic) |
| Multiple attachments preserved | PASS (five-role synthetic + reverse order) |
| Role/phase/variant semantics preserved | PASS (five-role includes template) |
| No implicit winner | PASS (semantic set independent of insertion order) |
| Exact revision beats latest/current | PASS (Threat synthetic) |
| Digest mismatch fails closed | PASS (Threat synthetic) |
| Cross-world/revision mismatch fails closed | PASS (Threat synthetic) |
| DungeonMind failure does not fall back locally | NOT_EXERCISED (blocked by PRODUCT_PROJECTION) |
| Buddy local authority kill test | **FAIL** |
| Real Threat bridge proof | **FAIL** (no durable uses_statblock dogfood) |
| Real NPC mechanics bridge proof | **FAIL** |
| Real PC semantic proof | **FAIL** |
| Shared product projection consumes bridge | **FAIL** |
| Dark-cutover rehearsal | **FAIL** |
| No governed writes | PASS (executed tree digest snapshot) |
| Historical B.3a remains valid | PASS (executed DM unit suites) |
| No published profile/catalog mutation | PASS |
| Dependency boundaries remain valid | PASS |

Mandatory gates cannot be waived.

---

## Real objects exercised

### Attempted / present without mechanics binding

```text
world bundle: eldyrwild-longmont-c2-initial-v1
object_id: threat:tripod-null-calf
object_kind: threat
uses_statblock: ABSENT
mechanics: none in contribution 006-tripod-null-calf-threat-prep.json
```

### Real PC objects (semantic only; not bridged)

```text
kind=pc examples in graph_data contributions
(e.g. pc roster / ownership supersede bundles)
mechanics authority cutover: OUT OF CLAIM
```

### Lysandra Ironveil

```text
No accepted durable NPC + uses_statblock mechanics object found in repository graph_data.
```

---

## Failure evidence (intentional blockers locked by audit)

| Probe | Observed |
|-------|----------|
| Public bridge + `kind=npc` | `source_object_kind_not_bridgeable` |
| Public bridge + `kind=pc` | `source_object_kind_not_bridgeable` |
| Product `_hydrate_binding` | still `client.get_exact_revision` — no DM hydrate; failures → typed statuses only |
| Canonical Plan / world projection modules | no `dungeonmind_kernel` / bridge exports |
| Durable `uses_statblock` in `graph_data/` | zero hits |
| Five-role reverse-order semantic set | PASS (primary/alternate/phase/encounter_variant/template) |

Executable lock: `tests/test_dungeonmind_cutover_readiness_audit.py`

---

## Dark-cutover result

```text
Could all claimed bridged product paths execute with the Buddy-local mechanics authority hard-disabled?
NO
```

Product Threat hydration still depends on `DungeonMindStatblockV1Client.get_exact_revision` inside `_hydrate_binding`. Shadow (#519) is post-response, non-authoritative, and Threat-only.

---

## Hidden-fallback result

```text
When DungeonMind failed, did any claimed bridge path recover via Buddy-local mechanics authority?
NOT_EXERCISED / BLOCKED BY PRODUCT_PROJECTION
```

There is currently **no authoritative DungeonMind product path** against which to run poisoned A-vs-B. The existing Buddy `_hydrate_binding` path does **not** implement an alternate hydrator: `get_exact_revision` failures become `exact_revision_missing`, `unavailable`, or `integrity_failure` (`test_product_authority_has_no_alternate_hydration_fallback`).

`HIDDEN_FALLBACK` is therefore **not** a proven defect in this ledger. Revisit only after an authoritative bridge path exists.

---

## Verification commands/results

```bash
# Buddy audit + predecessor Threat suites
cd DungeonMindBuddy-wt-cutover-proof
uv sync --locked
uv run ruff check tests/test_dungeonmind_cutover_readiness_audit.py
uv run pytest \
  tests/test_dungeonmind_cutover_readiness_audit.py \
  tests/test_dungeonmind_world_object_conformance_bridge.py \
  tests/test_dungeonmind_threat_hydration_shadow.py \
  -q
git diff --check

# DungeonMind historical B.3a + world-object mechanics (executed for §22)
cd DungeonMind-wt-main-cutover  # tip 073ca149 on #23 line
uv run pytest \
  tests/unit/test_dnd_threat_mechanics.py \
  tests/unit/test_dnd_world_object_mechanics.py \
  -q
# → 55 passed
```

No DungeonMind code changes in this proof.

---

## Remaining nonclaims

```text
DungeonMind is not Buddy runtime mechanics authority
Buddy _hydrate_binding still determines product Threat hydration
NPC mechanics bridge is unimplemented
PC world-object bridge is unimplemented
PC mechanics authority cutover is OUT OF CLAIM (DM forbids PC on mechanics-eligible kinds)
No durable real-domain uses_statblock dogfood in graph_data
Dark-cutover / authority promotion not performed
Play / Combat Tracker / CombatSourceLocator out of scope
Legacy Buddy hydrator not deleted
```

---

## Blocking classification

```text
DISPOSITION: CUTOVER_NOT_READY

Blocking class: BRIDGE_MAPPING
Failing proof: §7 B / §28 NPC semantic+mechanics mapping; §7 I / PC world-object semantic mapping
Responsible layer: DungeonMindBuddy (bridge absent; DM already admits dnd5e:npc)
Smallest durable fix: extend the #518 conformance boundary into a typed world-object
  semantic mapper shared by Threat/NPC/(later) PC kind mapping, with statblock
  attachment specialization remaining Threat/NPC-only. Do NOT clone a wholly
  separate NPC architecture, convert NPC→Threat, or synthesize dnd5e:threatens.

Blocking class: PRODUCT_PROJECTION
Failing proof: §15–§16 / §19–§20 / §28 shared product projection + dark-cutover;
  also blocks §13–§14 poisoned-fallback exercise
Responsible layer: DungeonMindBuddy (routes/services)
Smallest durable fix: after Threat+NPC bridges prove synthetic+real dogfood,
  promote DM hydrate behind existing /api/live/threats/query-hydration (or shared
  projection seam) with kill-switch; then local-authority kill + dark-cutover +
  poisoned A-vs-B

Blocking class: REAL_DATA_INCOMPATIBILITY
Failing proof: §17 real Threat/NPC mechanics dogfood
Responsible layer: campaign data / publication (not bridge invention)
Smallest durable fix: publish/accept at least one durable kind=threat (and ideally
  kind=npc) with uses_statblock + available exact revision; re-run shadow/full_match
  before promotion

Not a proven blocker in this ledger:
  HIDDEN_FALLBACK — current Buddy authority fails closed without an alternate
  hydrator; poisoned-fallback remains NOT_EXERCISED until PRODUCT_PROJECTION lands
```

Do not repair missing Buddy NPC mapping by inventing semantics inside DungeonMind.
Do not force green by converting NPCs to Threats.

---

## Successor discipline

Because disposition is `CUTOVER_NOT_READY`, do **not** dispatch:

```text
STATBLOCK: promote DungeonMind exact mechanics authority and demolish duplicate DungeonBuddy hydration
```

Next handoff addresses the **smallest durable blocker**:

```text
STATBLOCK: bridge exact Buddy NPC identity into DungeonMind v3
```

Prefer extending #518 into a **typed world-object semantic mapper** shared by Threat/NPC/(later) PC kind mapping, with statblock attachment specialization remaining Threat/NPC-only — not a wholly separate NPC-only architecture clone. Preserve `kind=npc`; never synthesize `dnd5e:threatens`.

In parallel / gated after NPC bridge:

```text
publish real durable Threat (+ ideally NPC) uses_statblock dogfood
→ re-enable shadow full_match on real data
→ only then authority promotion behind existing Buddy API
→ then poisoned-fallback + local-authority kill become exercisable
```

PC semantic mapping can ride the shared mapper later; PC mechanics stay OUT OF CLAIM until DM eligibility changes by explicit ADR.

---

## Final disposition

```text
DISPOSITION: CUTOVER_NOT_READY

Blocking class: BRIDGE_MAPPING (+ PRODUCT_PROJECTION, REAL_DATA_INCOMPATIBILITY)
Failing proof: mandatory NPC/PC/product/dark-cutover/real-domain gates
Responsible layer: DungeonMindBuddy adapter + product authority path (DM Threat+NPC contract is present)
Smallest durable fix: shared typed world-object mapper with NPC mechanics next;
  then real dogfood; then authority promotion — not a soft “mostly ready”

HIDDEN_FALLBACK: not a proven defect (NOT_EXERCISED / blocked by PRODUCT_PROJECTION)
```