# HANDOFF — DungeonMind whole World Graph adoption-readiness

**Created:** 2026-08-07  
**Status:** COMPLETE — diagnostic disposition  
**Repository:** `Drakosfire/DungeonMindBuddy` (+ contract evidence from pinned `Drakosfire/DungeonMind`)  
**Flow:** KERNEL  
**Canonical path:** `Docs/Plans/HANDOFF-kernel-dungeonmind-whole-world-adoption.md`

**Suggested branch:** `kernel/dungeonmind-whole-world-adoption`  
**Suggested PR title:** `KERNEL: whole World Graph DungeonMind adoption readiness`

---

## §1 Repository state

| Anchor | SHA / ref |
|--------|-----------|
| DungeonMindBuddy base (#521 merge) | `3a9bdaab30cf19450f0a0f753b3046e5443c45c4` |
| Branch | `kernel/dungeonmind-whole-world-adoption` |
| Implementation commit | `49c01c179cff2f82399d5cf87849e7f52a36c05a` (accounting/provenance tighten) |
| PR | [#522](https://github.com/Drakosfire/DungeonMindBuddy/pull/522) |
| DungeonMind pin (unchanged) | `8095321ed011b8a38640615a90cbc9efaf385e8c` |
| Real world | `out/graph_memory/worlds/eldyrwild` |
| Pinned revision | `rev:3413bf6f5044cf2680233f5e37c90dcf` |
| `graph_payload_sha256` | `346c1fbfb3cbbf6d0e5ded1453fdd7760264a5106022e398d6074679799ab0fa` |

Head was read once during test setup to confirm the pin; analyzer entrypoints never consult head after `revision_id` is supplied.

---

## §2 Mission

Deliver one reusable analyzer (`whole_world_conformance.py`) that:

1. integrity-loads one exact Buddy World Graph revision;
2. inventories every durable semantic element;
3. classifies each element against pinned DungeonMind contracts using explicit registries only;
4. emits machine-readable disposition `WHOLE_GRAPH_ADOPTION_READY | WHOLE_GRAPH_ADOPTION_NOT_READY`;
5. refuses `build_exact_dungeonmind_adoption_revision` when NOT_READY.

Not in scope: per-kind bridges, product hydration, Postgres internals, live graph mutation, or coercing Buddy vocabulary into DM shapes.

---

## §3 Public API exercised

| Symbol | Role |
|--------|------|
| `WHOLE_WORLD_CONFORMANCE_REPORT_SCHEMA` | `dmb_dungeonmind_whole_world_conformance_report_v1` |
| `analyze_exact_buddy_world_revision` | Primary inventory + classification report |
| `build_exact_dungeonmind_adoption_revision` | Fail-closed adoption builder (raises on NOT_READY) |
| `inspect_dungeonmind_durable_adoption_seam` | Public DM contract seam probe |
| `snapshot_world_graph_tree_digest` | Read-only source-tree digest proof |

Loader duplicates the bridge integrity pattern via `kernel.load_world_graph_revision_with_integrity` + manifest load. No post-parse digest rehash.

---

## §4 Classification enum (closed)

```text
EXACTLY_REPRESENTABLE
REPRESENTABLE_BY_EXPLICIT_ADAPTER
DUNGEONMIND_SEMANTIC_CONTRACT_GAP
DUNGEONMIND_DURABILITY_CONTRACT_GAP
SOURCE_MIGRATION_HISTORY
BUDDY_OPERATIONAL_ONLY
INVALID_SOURCE
```

---

## §5 Kind registry (explicit)

**REPRESENTABLE_BY_EXPLICIT_ADAPTER**

| Buddy kind | DM term |
|------------|---------|
| threat | dnd5e:threat |
| npc | dnd5e:npc |
| pc | dnd5e:player_character |
| creature | dnd5e:creature |
| location | dnd5e:location |
| faction | dnd5e:faction |
| encounter | dnd5e:encounter |
| external_resource | mechanics resource locator via #521 adapter (not a world-object kind) |

**SEMANTIC_CONTRACT_GAP (real Eldyrwild)**

| Buddy kind | Count @ pin |
|------------|-------------|
| item | 125 |
| mystery | 93 |
| group | 29 |
| party | 11 |
| event | 2 |

---

## §6 Predicate registry (explicit)

**REPRESENTABLE_BY_EXPLICIT_ADAPTER** (bare Buddy predicate → `dnd5e:` namespace)

| Buddy | DM |
|-------|-----|
| member_of | dnd5e:member_of |
| participates_in | dnd5e:participates_in |
| threatens | dnd5e:threatens |

**MECHANICS specialization (retained #521 semantics)**

| Buddy | Classification |
|-------|----------------|
| uses_statblock | REPRESENTABLE_BY_EXPLICIT_ADAPTER (mechanics specialization; not dnd5e:threatens) |

**SEMANTIC_CONTRACT_GAP (not silently renamed)**

| Buddy predicate | Real count @ pin | Note |
|-----------------|------------------|------|
| located_in | 48 | ≠ located_at; no accepted rename contract |
| attacks | 26 | no adapter |
| contains | 17 | no adapter |
| all other observed Buddy predicates | remainder | explicit gap |

Endpoint-kind mismatch on mapped predicates (e.g. `member_of` → non-faction target) is reported as RELATIONSHIP_PREDICATE gap for those edges.

---

## §7 Real Eldyrwild inventory @ pin

| Family | Count |
|--------|------:|
| nodes | 438 |
| edges | 348 |
| evidence | 185 |
| source_artifacts | 25 |
| aliases | 424 |
| assertion_support | 968 |
| contribution_replay_manifest | 34 |

**Kind inventory**

```text
item 125, location 103, mystery 93, npc 45, group 29, faction 13,
party 11, pc 6, creature 4, threat 3, encounter 2, event 2, external_resource 2
```

**Mechanics / location signals**

| Signal | Count |
|--------|------:|
| uses_statblock edges | 2 |
| located_in gaps | 48 |

Completeness invariant: `unaccounted_durable_elements = 0` (`classified_elements_count = 18106` durable serialized paths). Accounting derives from `enumerate_durable_element_ids(store)` over the serialized payload — not from classifier-loop self-counts. Unknown Pydantic extras remain unaccounted (adversarial test covers this).

**Source domain inventory (25 artifacts / 185 evidence)**

| Domain | Artifacts | Evidence | Disposition |
|--------|----------:|---------:|-------------|
| recap | 16 | 158 | EXPLICIT_ADAPTER → DM `session_recap` |
| worldbuilding | 4 | 4 | EXACTLY_REPRESENTABLE |
| statblock | 3 | 9 | SEMANTIC_CONTRACT_GAP |
| manual_seed | 1 | 13 | EXPLICIT_ADAPTER → DM `manual` |
| party_registry | 1 | 1 | SEMANTIC_CONTRACT_GAP |

---

## §8 State / evidence / history classification (executed)

| Family | Disposition |
|--------|-------------|
| visibility gm/player | EXACTLY_REPRESENTABLE |
| canon_state canonical/provisional/retracted | EXACTLY_REPRESENTABLE |
| epistemic_kind fact / source_derived_candidate | SEMANTIC_CONTRACT_GAP (EPISTEMIC_STATE) |
| campaign_scope | SEMANTIC_CONTRACT_GAP (CAMPAIGN_SCOPE) |
| node.role | SEMANTIC_CONTRACT_GAP (ATTRIBUTE_ASSERTION) |
| approval/memory/support/identity/introduced_by_contribution_id | SOURCE_MIGRATION_HISTORY (CONTRIBUTION_HISTORY) |
| aliases label→node_id + node.aliases | DURABILITY gap (EVIDENCE_PROVENANCE) |
| evidence fields (incl. `source_domain`) | field-for-field; role adapter + Buddy-only span/session durability gaps + domain gaps |
| source_artifact fields (incl. `source_domain`, `content_sha256`→SourceRevision) | field-for-field; not wholesale adapter |
| assertion_support | SOURCE_MIGRATION_HISTORY |
| contribution_replay + source payload digests | SOURCE_MIGRATION_HISTORY |
| edge.session_ids | FICTIONAL_TIME gap |
| focus_session_id | BUDDY_OPERATIONAL_ONLY |
| adjacency / diagnostics | BUDDY_OPERATIONAL_ONLY |
| initialization_* | SOURCE_MIGRATION_HISTORY |

---

## §9 Durable adoption seam

```text
inspect_dungeonmind_durable_adoption_seam()
→ DURABLE_ADOPTION_BOUNDARY_MISSING
world_graph_repository_methods (introspected):
  get_head, get_revision, publish_revision, rollback_head
```

Status is derived from introspected public callables on pinned `WorldGraphRepository` (no hardcoded method list / hardcoded MISSING). No public governed adopt-existing-world / bootstrap-complete-revision service for pre-existing Buddy worlds.

Postgres adoption: `BLOCKED` (seam missing; no postgres import).

---

## §10 Disposition

```text
DISPOSITION: WHOLE_GRAPH_ADOPTION_NOT_READY
```

`build_exact_dungeonmind_adoption_revision` raises `WholeWorldConformanceError` on real Eldyrwild pin and on synthetic fixtures with semantic gaps.

`mechanics_specialization_retained: true` — #521 Threat/NPC/PC + `uses_statblock` rules remain documented; whole-graph analyzer does not replace per-object bridge.

---

## §11 Top blockers (real Eldyrwild @ pin)

| Blocker class | Count | Responsible | Smallest next change |
|---------------|------:|---------------|----------------------|
| CONTRIBUTION_HISTORY | 4090 | DungeonMind | Adopt-existing-world seam + genesis policy A/B/C |
| EVIDENCE_PROVENANCE | 1209 | DungeonMind | Preserve Buddy evidence/alias/source_domain/artifact field peers |
| CAMPAIGN_SCOPE | 787 | DungeonMind | DM campaign/scope field for Buddy `campaign_scope` |
| EPISTEMIC_STATE | 786 | DungeonMind | Buddy epistemic vocabulary mapping (no coercion) |
| ATTRIBUTE_ASSERTION | 438 | DungeonMindBuddy | Document or map Buddy `node.role` (and similar) |
| RELATIONSHIP_PREDICATE | 336 | DungeonMind | Predicate contracts / adapters (incl. `located_in`) |
| FICTIONAL_TIME | 333 | DungeonMind | Transport durable `edge.session_ids` |
| WORLD_OBJECT_KIND | 260 | DungeonMind | Extend world-object-v1 for item/mystery/group/party/event |
| DURABLE_ADOPTION_BOUNDARY | 1 | DungeonMind | Public adopt-existing-world service |
| POSTGRES_ADOPTION | 1 | DungeonMind | Exercise only after public seam exists |

Source tree digest before/after analyze: `b79f956141424f7ed332d86f3249666c9353e048f2776364bcb09e65edff6a77` (equal).

Classification bucket totals @ pin: EXACTLY_REPRESENTABLE 3227, REPRESENTABLE_BY_EXPLICIT_ADAPTER 3995, SEMANTIC_CONTRACT_GAP 2969, DURABILITY_CONTRACT_GAP 1180, SOURCE_MIGRATION_HISTORY 4090, BUDDY_OPERATIONAL_ONLY 2645.

---

## §12 Adoption genesis policy note

Policies A/B/C were evaluated for reporting only; none was executed.

- Historical Buddy contribution chains cannot be silently discarded.
- Option B (versioned one-time adoption record + new DM contribution chain) is the likely future policy **only if** semantics + durability gaps close and the public adoption seam lands.
- Today: blocked by semantic gaps (including source_domain vocabulary + artifact field peers), alias/evidence durability gaps, contribution history, and missing DM adoption seam.

---

## §13 Whole-world cutover gates (§26 ledger)

| Gate | Result |
|------|--------|
| WHOLE_WORLD_INVENTORY exact pin | **PASS** |
| Completeness invariant (=0 unaccounted; payload-derived) | **PASS** |
| Unknown durable extras force unaccounted > 0 | **PASS** (adversarial test) |
| Source/evidence field+domain classification | **PASS** |
| BRIDGE_MAPPING closed (#521) | **PASS** (per-object bridge unchanged) |
| Mapped kinds inventory | **PASS** (threat/npc/pc/location/faction/encounter/creature/external_resource) |
| Semantic gap kinds surfaced | **PASS** (item/mystery/group/party/event) |
| uses_statblock mechanics retained | **PASS** |
| located_in not mapped to located_at | **PASS** (gap) |
| Durable adoption seam (introspected) | **FAIL** |
| build refuses NOT_READY | **PASS** |
| Source tree digest unchanged by analyze | **PASS** |

Overall cutover disposition remains **`CUTOVER_NOT_READY`** (see cutover handoff whole-world section).

---

## §14 Stop conditions (none triggered as defects)

Expected success mode for this PR is diagnostic NOT_READY. The analyzer did **not**:

- coerce kinds/predicates;
- flatten attributes;
- drop evidence;
- write to live graph;
- import DM postgres internals.

---

## §15 Verification commands / results

```bash
cd /home/drakosfire/Projects/DungeonOverMind/DungeonMindBuddy
uv sync --locked
uv run ruff check \
  apps/live_control_server/integrations/dungeonmind_kernel/whole_world_conformance.py \
  apps/live_control_server/integrations/dungeonmind_kernel/__init__.py \
  tests/test_dungeonmind_whole_world_conformance.py \
  tests/test_dungeonmind_cutover_readiness_audit.py
uv run pytest \
  tests/test_dungeonmind_world_object_conformance_bridge.py \
  tests/test_dungeonmind_world_object_conformance_generalized.py \
  tests/test_dungeonmind_cutover_readiness_audit.py \
  tests/test_dungeonmind_whole_world_conformance.py \
  -q
```

Paste pytest output in PR body from executing agent run.

---

## §16 Files touched

| Path | Change |
|------|--------|
| `apps/live_control_server/integrations/dungeonmind_kernel/whole_world_conformance.py` | CREATE |
| `apps/live_control_server/integrations/dungeonmind_kernel/__init__.py` | export public symbols |
| `tests/test_dungeonmind_whole_world_conformance.py` | CREATE |
| `tests/test_dungeonmind_cutover_readiness_audit.py` | whole-world gates |
| `Docs/Plans/HANDOFF-statblock-dungeonmind-cutover-readiness-proof.md` | whole-world ledger section |
| `Docs/Plans/PR-TRACKER-campaign-supergraph.md` | narrow slice entry |
| `Docs/Roadmaps/ROADMAP-cross-surface-statblock-demo.md` | whole-graph adoption sequence pointer |

Out of scope honored: `world_object_conformance_bridge.py` behavior unchanged; `out/graph_memory/worlds/eldyrwild/**` not mutated.

---

## §17 Nonclaims

```text
DungeonMind is not Buddy runtime authority for whole-graph migration
Whole-graph adoption is NOT_READY on real Eldyrwild @ pin
Per-object #521 bridge remains the only mechanics conformance path exercised in product
No Postgres adoption exercised
No durable DM revision was published from Buddy source
Play / Build / Plan hydration unchanged
```

---

## §18 Successor discipline

Evidence-driven successor (**Outcome A** — semantic gaps dominate):

```text
DungeonMind:
WORLD: add the exact missing whole-graph semantic contracts required by Eldyrwild adoption
```

Scope only observed missing families: item/mystery/group/party/event kinds; unmapped predicates (starting with `located_in` + high-count gaps); campaign_scope; Buddy epistemic vocabulary; fictional-time/`session_ids`; evidence span fields; alias evidence attachment; Buddy `source_domain` values without DM peers (`statblock`, `party_registry`, and other note domains); Buddy artifact fields without DM peers (`workspace_document_*`, `updated_at`, `lineage` when populated, visibility_state vocab); Buddy `node.role`.

Then (**Outcome B**, already confirmed missing):

```text
DungeonMind:
WORLD: add exact existing-world bootstrap adoption into durable repositories
```

Do **not** dispatch Buddy authority promotion / dark cutover until whole-graph analyzer disposition flips to READY on the pinned Eldyrwild revision and a public DM adoption seam exists.

Until then, continue per-object bridge proofs (#520/#521) and campaign publication dogfood as **preconditions**, not as immediate mechanics-authority cutover.
