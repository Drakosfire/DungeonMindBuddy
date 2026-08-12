# HANDOFF: Eldyrwild deferred node-kind source repair — Stage B

## 1. Authority and mission

This handoff authorizes a non-publishing successor to the post-#563
Eldyrwild relationship semantic closure. Stage B performs exactly four
source-supported in-place node-kind repairs:

1. `item_shatter_mages_tower`: `item` → `location`, clearing
   `edge:combat_shatter_mages_tower_spider:located_in:item_shatter_mages_tower`.
2. `mystery_stone_bridge_river_name`: `mystery` → `location`, clearing
   `edge:loc:stone_bridge:contains:mystery_stone_bridge_river_name`.
3. `loc:guilds`: `location` → `faction`, clearing
   `edge:node:torrin_flamescale:serves:loc:guilds:represents`.
4. `item:torvak-hemp-caravan`: `item` → `group`, clearing
   `edge:node:torvak_hempdealer_crew:member_of:item:torvak-hemp-caravan`.

The three dual-sense rows below are explicit STOP/deferred-out-of-Stage-B
rows. Stage B does not invent identities, add nodes, rewire endpoints, or
authorize synthetic identity/aspect IDs. A separate successor design must
choose and prove the identity/aspect modeling contract before any of these
edges can be re-admitted.

The authority must not mutate the live World Graph, publish a revision, alter
Kernel shared APIs, or perform durable re-admission. Its only durable output is
the allowlisted manifest:

`graph_data/approved_graph_corrections/eldyrwild/relationship-node-kind-source-repair-v1/manifest.json`

## 2. Activation pins

| Pin | Locked value |
|---|---|
| merge SHA context | `0479d50d048a88b92b9d200dbf3cbbc93d295ba2` |
| base revision | `rev:5a7c13ae45c49a65b402920499be72ed` |
| base graph payload SHA-256 | `2632870ef70638969503de788cfdec97acd490875deff3e2630ac91dc96fe974` |
| predecessor closure | `eldyrwild-relationship-semantic-closure-v1` |
| predecessor closure manifest SHA-256 | `3d5da9b19b74a28d4930132e281c0e41197d3ea1493c5a202ba1ef6c6ffbfb25` |
| manifest SHA-256 | `96cc26fc6e99448e8fba5cd6982070c1e29bb058f2b1e8a4ac291f8a0a083247` |
| canonical payload SHA-256 | `452341b9ef46f00d0596c2100d876fae7998315a405da161717ed7b377483ca7` |

Eligibility is exact: stale head, payload drift, base inventory drift,
deferred-set drift, predecessor authority drift, or manifest digest drift is
ineligible or an integrity failure.

## 3. Inventories and residual boundary

The pinned base inventory is:

`{semantic: 323, represented: 314, residual: 9, uses_statblock_mechanics: 3}`

The projected Stage-B inventory is:

`{semantic: 323, represented: 318, residual: 5, uses_statblock_mechanics: 3}`

The exact remaining residual edge IDs after Stage B are:

```text
edge:loc:central-office:located_in:node:meat_distribution_network_session9:site-of
edge:loc:packing-loading-area:part_of:node:meat_distribution_network_session9
edge:node:headmaster_tinkerbright:leads:loc:wizard_college
edge:node:hempholm_townsfolk:participates_in:node:hempholm_folk_revelry
edge:pc:caelynn:participates_in:node:hempholm_folk_revelry
```

No arithmetic projection is authoritative. The projected inventory and
remaining set are obtained by classifying the kind-only overlay and then
running effective relationship conformance at its owning boundary.

## 4. Deferred dual-sense STOP rows

These rows remain deferred and must be recorded as
`deferred_dual_sense_stops` in the manifest:

| Node | Deferred edge IDs | Why kind-only fails |
|---|---|---|
| `loc:wizard_college` | `edge:node:headmaster_tinkerbright:leads:loc:wizard_college` | `faction` admits `leads`, but regresses retained `travels_to` edges that require a location target. |
| `node:meat_distribution_network_session9` | `edge:loc:central-office:located_in:node:meat_distribution_network_session9:site-of`; `edge:loc:packing-loading-area:part_of:node:meat_distribution_network_session9` | `location` admits containment, but regresses retained `leads` edges that require a party/group/faction target. |
| `node:hempholm_folk_revelry` | `edge:node:hempholm_townsfolk:participates_in:node:hempholm_folk_revelry`; `edge:pc:caelynn:participates_in:node:hempholm_folk_revelry` | `event` admits participation, but breaks retained `within` → `located_in` because the source must remain location-compatible. |

For every row, the proof must show that the speculative candidate kind admits
all named deferred edges and makes at least one currently-effective retained
edge residual. If a row becomes kind-only solvable, the proof fails closed.

## 5. Source authority

Each of the four kind repairs and each STOP row is bound to the exact #563
deferred closure units. The manifest carries closure unit IDs, source
contribution IDs and locked payload digests, source artifact IDs and complete
source seals, plus primary evidence/span/excerpt/locator digest references.

Before derivation or verification, the service resolves every primary evidence
excerpt with `resolve_evidence_excerpt` and verifies it with
`verify_excerpt_against_seal`. It also verifies every source contribution
against the current revision digest map, active replay manifest, mutable
contribution ledger, and contribution index. Any mismatch refuses closed.

## 6. Owning-boundary proof

The proof must:

1. Load the exact pinned base store.
2. Create an in-memory `model_copy` overlay changing only the four node kinds.
3. Classify every current relationship edge on that overlay with
   `_classify_edge_predicate_v4` and
   `load_builtin_world_object_v4_vocabulary`, skipping
   `MECHANICS_SPECIALIZATION`.
4. Copy the disk v4 report and replace only its residual IDs/count and
   represented count with the classified overlay values.
5. Derive continuity with
   `analyze_relationship_adjudication_continuity_v1`.
6. Derive composed authority with
   `analyze_composed_relationship_adjudication_authority_v1`.
7. Load `load_eldyrwild_relationship_explicit_adapter_catalog_v1`.
8. Call the existing private injectable helper
   `_analyze_relationship_effective_conformance_with_authorities` with the
   synthesized report, continuity, catalog, overlay store, and composed
   authority.

The private helper import is the only shared integration change. It is
existing code whose injectable store/report seam is required to prove an
unpublished overlay at the effective-conformance owner; no Kernel public API
is changed.

The proof compares base and overlay effective remaining sets. No currently
effective non-deferred edge involving a repaired node may become residual.

## 7. Build, verify, and locked v1 behavior

The service exposes `status`, `build`, `verify`, and isolated-proof functions.
Build derives and validates the complete payload and pretty bytes before any
filesystem replacement.

`build` then:

1. Computes the pretty-byte SHA-256.
2. Refuses with `manifest_digest_mismatch` if it differs from the locked
   `LOCKED_MANIFEST_SHA256`.
3. If the path exists, refuses with
   `locked_manifest_overwrite_refused` when existing bytes differ.
4. Returns `already_built` without rewriting when existing bytes are identical.
5. Writes only a missing manifest whose generated digest equals the lock.

The CLI `--allow-live-world` flag is only a no-op guard acknowledgement. Build
and verify remain non-publishing even when the read root is the configured live
root.

## 8. Verification commands

```bash
cd /tmp/dmb-deferred-kind-repair
export PYTHONPATH=/tmp/dmb-deferred-kind-repair:/tmp/dmb-deferred-kind-repair/src
export DUNGEONMIND_WORLD_GRAPH_ROOT=/home/drakosfire/Projects/DungeonOverMind/DungeonMindBuddy/out
export DUNGEONMIND_LIVE_WORLD_GRAPH_ROOT=/home/drakosfire/Projects/DungeonOverMind/DungeonMindBuddy/out
uv run pytest -q tests/test_eldyrwild_relationship_node_kind_source_repair.py
uv run python scripts/build_eldyrwild_relationship_node_kind_source_repair.py status
uv run python scripts/build_eldyrwild_relationship_node_kind_source_repair.py verify
```

All operations must leave the live graph head, revision payload, and graph
tree digest unchanged.
