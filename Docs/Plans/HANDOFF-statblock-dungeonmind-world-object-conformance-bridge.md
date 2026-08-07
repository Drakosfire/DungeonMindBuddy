# HANDOFF — Exact DungeonBuddy Threat → DungeonMind v3 conformance bridge

**Created:** 2026-08-07  
**Status:** IMPLEMENTATION COMPLETE — ready for review  
**Repository:** `Drakosfire/DungeonMindBuddy`  
**Flow:** KERNEL / STATBLOCK  
**Canonical path:** `Docs/Plans/HANDOFF-statblock-dungeonmind-world-object-conformance-bridge.md`

**Suggested branch:** `kernel/dungeonmind-threat-conformance-bridge`  
**Suggested PR title:** `STATBLOCK: bridge exact Buddy Threat identity into DungeonMind v3`

---

## Repository identity

| Anchor | SHA |
|--------|-----|
| Buddy base (`main` at branch start) | `46d3677d9ade0b7a83ab2cb07d2b6c635fb50f40` |
| Branch | `kernel/dungeonmind-threat-conformance-bridge` |
| Head SHA | `064f0db8d19b959d31762dd6ec80bf440ef26758` |
| PR | [#518](https://github.com/Drakosfire/DungeonMindBuddy/pull/518) |
| DungeonMind dependency (PR #23 merge) | `8095321ed011b8a38640615a90cbc9efaf385e8c` |

Open adjacent PRs inspected before shared-file edits: #517 (PWO01 docs — not absorbed), #516 (benchmark), #510 (Build refs), #497 (navbar), #442 (transfer). No shared-file collisions with this seam.

**Dependency proof:**

- `uv.lock` pins `dungeonmind @ git+…@8095321ed011b8a38640615a90cbc9efaf385e8c`
- Installed package version: `dungeonmind 0.1.0`
- Successful imports: `dungeonmind`, `dungeonmind_dnd`
- Real symbols exercised (not mocked): `canonical_sha256`, `compute_revision_id`, `derive_world_object_mechanics_binding`, `derive_statblock_mechanics_attachment_id`, `hydrate_world_object_mechanics`

---

## What shipped

| Path | Role |
|------|------|
| `pyproject.toml` / `uv.lock` | Pin exact DungeonMind #23 merge |
| `apps/live_control_server/integrations/dungeonmind_kernel/world_object_conformance_bridge.py` | Exact Threat → v3 conformance bridge |
| `apps/live_control_server/integrations/dungeonmind_kernel/__init__.py` | Public adapter exports |
| `tests/test_dungeonmind_world_object_conformance_bridge.py` | Conformance + adversarial + hydration matrix |

No product routes, no shadow wiring, no graph writes, no PWO01 / Play absorption.

---

## Source → target identity example

From fixture matrix A (`threat:bridge-synthetic`, one primary binding):

| Buddy source | DungeonMind target |
|--------------|--------------------|
| `world_id` = `bridge-test-world` | `target_world_id` = `bridge-test-world` |
| `campaign_id` = `longmont-c2` | retained as bridge/source context only |
| `revision_id` = exact Buddy `rev:…` | distinct content-addressed DM `rev:…` |
| `node_id` = `threat:bridge-synthetic` | `object_id` = `obj:dmb:threat:bridge-synthetic` |
| `binding_id` = `threat-statblock-binding:…` | `mechbind:…` (different algorithm) |
| `edge_id` = `edge:threat-statblock-binding:…` | retained as `source_edge_id` |
| — | `mechattach:…` from role/phase/variant |
| `definition_digest` = `sha256:<hex>` | `payload_sha256` = bare `<hex>` |
| provider `dungeonmind` | `provider_id` = `dungeonmind.statblocks` |
| contract + version | `resource_schema` = `dungeonmind.dungeonbuddy-statblocks.1.0.0` |

---

## Field mapping table

| Source field | Target field | Transformation | Lossy? |
|--------------|--------------|----------------|--------|
| Threat `node_id` | `object_id` | `"obj:dmb:" + node_id` (alphabet-checked) | no |
| Threat `kind=threat` | `kind=dnd5e:threat` | explicit kind map | no |
| Threat `label` | node `label` | exact copy | no |
| Threat `aliases[]` | `alias_assertions[].alias` | exact strings + bridge evidence | no |
| Threat summary | — | not invented when absent | n/a |
| `campaign_id` | — | retained as bridge/source context; not in #23 binding | n/a (documented) |
| Buddy provenance domains | — | **NOT MIGRATED**; bridge evidence points at exact source graph revision (`source_domain=other`) | n/a (documented) |
| `uses_statblock` edge | mechanics attachment | not a graph relationship | no |
| `ThreatStatblockBindingV1.role` | attachment `role` | exact | no |
| `phase_key` / `variant_label` | attachment fields + `attachment_id` | exact strings (Buddy grammar) | no |
| `provider=dungeonmind` | `provider_id=dungeonmind.statblocks` | frozen compatibility map | no |
| `contract` + `contract_version` | `resource_schema` | `contract + "." + version` | no |
| `definition_digest` | `payload_sha256` | strip exactly one `sha256:` | no |
| `statblock_id` / `revision_id` | `resource_id` / `resource_revision` | exact | no |
| Buddy `revision_id` | DM `revision_id` | recomputed via DM `compute_revision_id` | no (different contract by design) |
| Buddy binding_id | DM binding_id | different algorithms; both retained | no |

---

## Multiplicity proof

| Case | Result |
|------|--------|
| zero bindings | valid `dnd5e:threat` object; `attachments=[]`; no fabricated mechanics |
| one primary | one `mechbind` + one `mechattach`; hydrate PASS |
| same resource primary+alternate | one generic `binding_id`; two `attachment_id`s |
| two phases (`bloodied`, `enraged`) | both survive; distinct attachments |
| `phase_key=" enraged "`, `variant_label=""`, `variant_label=" night raid "` | byte-for-byte preserved in attachment + identity |

---

## Hydration proof

- Exact resolver call count: **1**
- Resource ref requested: `sb_bridge01` / `rev_bridge01` / `dungeonmind.statblocks` / schema `dungeonmind.dungeonbuddy-statblocks.1.0.0`
- Payload digest: Buddy `sha256:<hex>` → DM bare `<hex>` → `canonical_sha256(payload)` match
- DungeonMind `hydrate_world_object_mechanics` succeeds without `dnd5e:threatens`

---

## Head behavior

Pinned old revision R1 with binding A; newer head R2 with binding B.

- Bridge against R1 → `source_revision_id == R1`, only binding A visible
- Request I/O `head_json_reads == 0` (bridge does not open head)

---

## Remains false

```text
DungeonMind is not yet Buddy runtime mechanics authority
no shadow comparison runs in production
Buddy hydration still calls its current provider path
no DungeonMind graph persistence exists
no Buddy graph migration exists
no old graph kernel is deleted
KERNEL-0 is not yet declared fully complete
Play remains gated
NPC mechanics bridge remains unimplemented
PC mechanics remains unimplemented
```

---

## Successor

```text
STATBLOCK: shadow verify Buddy Threat hydration through DungeonMind
```

Reuse this bridge; insert non-authoritative comparison at `_hydrate_binding` / shared Threat hydration orchestration; Buddy remains authority; immediate disable switch; no writes.
