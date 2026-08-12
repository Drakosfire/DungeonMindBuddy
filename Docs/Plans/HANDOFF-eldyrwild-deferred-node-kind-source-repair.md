# HANDOFF: Eldyrwild deferred node-kind/source repair

## 1. Authority and mission

This handoff authorizes a non-publishing successor to the post-#563
Eldyrwild relationship semantic closure. The successor is a read-only
relationship repair authority, not a World Graph migration:

1. Four source-supported in-place node-kind repairs:
   `item_shatter_mages_tower` item→location,
   `mystery_stone_bridge_river_name` mystery→location,
   `loc:guilds` location→faction, and
   `item:torvak-hemp-caravan` item→group.
2. Three source-supported dual-sense aspect splits. Each split retains the
   original node and kind, creates an aspect node, and rewires only the named
   deferred edges to that aspect:
   Wizard's College location + faction aspect, the meat-distribution project
   party + site aspect, and Hempholm revelry group + event aspect.

The authority must not mutate the live World Graph, publish a revision, alter
Kernel shared APIs, or perform durable re-admission. Its durable output is only
the allowlisted repair manifest under
`graph_data/approved_graph_corrections/eldyrwild/relationship-node-kind-source-repair-v1/`.

## 2. Activation pins

| Pin | Locked value |
|---|---|
| merge SHA context | `0479d50d048a88b92b9d200dbf3cbbc93d295ba2` |
| base revision | `rev:5a7c13ae45c49a65b402920499be72ed` |
| base graph payload SHA-256 | `2632870ef70638969503de788cfdec97acd490875deff3e2630ac91dc96fe974` |
| inventory | semantic 323 / represented 314 / residual 9 / uses_statblock 3 |
| predecessor closure | `eldyrwild-relationship-semantic-closure-v1` |
| predecessor closure manifest SHA-256 | `3d5da9b19b74a28d4930132e281c0e41197d3ea1493c5a202ba1ef6c6ffbfb25` |
| live read root | `/home/drakosfire/Projects/DungeonOverMind/DungeonMindBuddy/out` |

The exact deferred residual set is the nine sorted edge IDs in the repair
manifest. Eligibility is exact: a stale head, payload drift, inventory drift,
or residual-set drift is ineligible.

## 3. Scope, split semantics, and endpoint domain

The repair domain is all and only the nine deferred edges from #563:

- `edge:combat_shatter_mages_tower_spider:located_in:item_shatter_mages_tower`
- `edge:loc:central-office:located_in:node:meat_distribution_network_session9:site-of`
- `edge:loc:packing-loading-area:part_of:node:meat_distribution_network_session9`
- `edge:loc:stone_bridge:contains:mystery_stone_bridge_river_name`
- `edge:node:headmaster_tinkerbright:leads:loc:wizard_college`
- `edge:node:hempholm_townsfolk:participates_in:node:hempholm_folk_revelry`
- `edge:node:torrin_flamescale:serves:loc:guilds:represents`
- `edge:node:torvak_hempdealer_crew:member_of:item:torvak-hemp-caravan`
- `edge:pc:caelynn:participates_in:node:hempholm_folk_revelry`

The kind repairs are in-place overlay corrections. The aspect splits are:

| Source retained | Aspect | Rewired edges | Retained source edges |
|---|---|---|---|
| `loc:wizard_college` location | `faction:wizard_college` faction, `Wizard's College (organization)` | headmaster `leads` | Thalia and Torbin `travels_to`; college `within` Mirathorn |
| `node:meat_distribution_network_session9` party | `loc:meat_distribution_site_session9` location, `Meat Distribution Site` | central office `located_in`; packing area `part_of` | Blart and Lyra `leads` |
| `node:hempholm_folk_revelry` group | `event:hempholm_folk_revelry` event, `Hempholm folk revelry` | townsfolk and Caelynn `participates_in` | revelry `within` Hempholm |

Conflict detection is fail-closed: an aspect source or aspect ID may not be
claimed twice, a deferred edge may not be rewired by two splits, and an edge
may not be both rewired and retained. A split also refuses if the source kind
or durable edge shape has drifted.

The Kernel `split_identity` seam is insufficient for this authority. It creates
a same-kind identity-split node, does not express a semantic aspect kind, and
does not rewire a selected subset of deferred edge endpoints. This repair
therefore uses only an in-memory `store.model_copy` overlay and does not add a
new Kernel API.

## 4. Evidence and contribution authority

Every kind repair and aspect split is bound to the deferred #563 units in the
predecessor closure. The manifest copies:

- closure unit IDs and source-grounded rationale;
- source contribution IDs and their locked source-payload digests;
- source artifact IDs and complete source seals;
- primary evidence, span, excerpt, artifact, and locator digest references.

Before derivation or verification, the service resolves each primary evidence
excerpt with `resolve_evidence_excerpt` and checks it with
`verify_excerpt_against_seal`. It also checks every source contribution against
the current revision digest map, active replay manifest, mutable contribution
ledger, and contribution index. Any authority mismatch refuses closed.

## 5. Isolation and proof contract

The proof loads exactly the pinned base revision and creates an in-memory
overlay with `UnionSupergraphStore.model_copy`:

- corrected kinds replace only the four source node `kind` values;
- three aspect nodes are added only to the overlay;
- exactly the five listed deferred edges change endpoint to an aspect node.

No whole-payload JSON rewrite is used. Whole-payload cloning/rewrite can cause
unrelated continuity checks to report `SOURCE_GROUNDING_DRIFT`; the overlay
avoids that class of false mutation.

The proof invokes `_classify_edge_predicate_v4` with
`load_builtin_world_object_v4_vocabulary` and requires all nine deferred edges
to be `EXISTING_EXPLICIT_ADAPTER`. It also proves that no previously
representable non-deferred edge involving a touched source becomes a gap.
Starting from 323/314/9/3 and clearing exactly the nine deferred residuals, the
projected inventory must be 323/323/0/3.

## 6. Build, verify, and publication boundary

The service exposes status, build, verify, and isolated-proof functions. Build
derives the complete manifest first and atomically replaces the repository
manifest only after all source, base, split, endpoint, and inventory checks
pass. Verify returns a pin only for the locked manifest and exact base proof.

`--allow-live-world` is only a no-op guard acknowledgement for the CLI. Build
and verify remain non-publishing even when the read root is the configured live
root. No `publish_world_revision`, contribution merge, identity merge, or
other graph mutation seam is called.

## 7. Re-admission and next handoff

This handoff does not durably re-admit the repaired relationships. It does not
write a new graph revision, mutate source contributions, update Kernel
vocabulary, or claim that the World Graph has adopted the overlay. Durable
re-admission remains out of scope and requires a separately authorized
source-repair/adoption operation with its own revision and continuity proofs.

The locked artifact for this handoff is:

`graph_data/approved_graph_corrections/eldyrwild/relationship-node-kind-source-repair-v1/manifest.json`

The service locks both its canonical self-excluding payload digest and the
manifest byte digest. Tests must use `uv run`, may clone the live world into a
temporary root, and must assert that build/verify leave the canonical live
world unchanged.
