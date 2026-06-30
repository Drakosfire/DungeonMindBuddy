# HANDOFF — Mirathorn City worldbuilding candidate-graph gold (world-authority bed)

Status: ready for execution (composer-2)
Workstream: Graph Memory / Contextual Vocabulary test-bed expansion
Design authority: `Docs/Design/DESIGN-contextual-vocabulary-layer.md` (2026-06-30 addendum, "Test-bed expansion")
Sibling build: `Docs/Plans/HANDOFF-c1s1-candidate-graph-gold.md` (the recap bed; mirror its loader/CLI/test structure)

## Mission

Create a hand-authored **worldbuilding** candidate-graph gold fixture for the
evergreen city doc **"The City of Mirathorn"**, at parity with the S22/S23/C1S1
fixtures, to give the vocabulary ablation a **world-authority** bed (no session
occurrence; setting reference facts). This is mechanical replication of the C1S1
gold scaffold MINUS the recap-ingest normalization (a world doc is not a recap),
PLUS a small gold-review registry generalization. All node/edge/anchor judgment is
fixed below — do not invent, add, drop, or reword entities.

## Source doc

Canonical text source (primary corpus, the processed twin of the .docx the user
named): `corpus/eldyrwild-markdown/Elderwyld/Cities and Towns/Mirathorn/The City of Mirathorn.md`
Snapshot its EXACT bytes into the fixture (file 1 below) so anchor offsets are stable
and self-contained. Anchor line numbers below are 1-based against that file verbatim
(frontmatter on lines 1–11; body begins line 12).

## World-authority semantic mapping (IR has no world-canon state — use this verbatim)

The `candidate_graph_preview` IR `CANON_STATES` has no `world_reference`. For every
world node AND edge use:
`semantic_state = {canon_state: "unknown", lifecycle_state: "candidate",
evidence_role: "source_evidence", authority_state: "gm_prep",
visibility_state: "player_visible"}`
EXCEPT the spoiler entities (`node:the-wolf`, `node:thalia-ashenvale`,
`edge:wolf-controls-thalia`) which use `visibility_state: "spoiler_sensitive"`.
`proposed_action: "create"`. Document this mapping in the gold manifest `notes[]`
(world authority is carried by the vocabulary layer, not this IR).

## Files IN SCOPE (create unless noted; default-deny everything else)

1. `evals/graph_memory_layer/examples/mirathorn_city_world_doc/mirathorn_city_source.md` (verbatim snapshot of the source doc)
2. `evals/graph_memory_layer/examples/mirathorn_city_world_doc/source_span_seed_refs.json`
3. `evals/graph_memory_layer/examples/mirathorn_city_world_doc/mirathorn_city_world_doc_manifest.json`
4. `evals/graph_memory_layer/examples/mirathorn_city_world_doc/README.md` (short)
5. `evals/graph_memory_layer/examples/mirathorn_city_candidate_graph_gold/candidate_graph_gold.json`
6. `evals/graph_memory_layer/examples/mirathorn_city_candidate_graph_gold/mirathorn_city_candidate_graph_gold_manifest.json`
7. `evals/graph_memory_layer/mirathorn_city_world_doc_fixture.py` (loader: source artifact + span seeds; mirror `session_1_recap_ingest_fixture.py` but NO assemble_recap / paragraph index — the source is the snapshot file read directly)
8. `evals/graph_memory_layer/mirathorn_city_candidate_graph_gold_fixture.py` (mirror `session_1_candidate_graph_gold_fixture.py`, incl. a `HIGH_RISK_EVIDENCE_AUDIT`)
9. `evals/graph_memory_layer/validate_mirathorn_city_world_doc_fixture.py`
10. `evals/graph_memory_layer/report_mirathorn_city_world_doc_fixture.py`
11. `evals/graph_memory_layer/validate_mirathorn_city_candidate_graph_gold_fixture.py`
12. `evals/graph_memory_layer/report_mirathorn_city_candidate_graph_gold_fixture.py`
13. `tests/test_graph_memory_mirathorn_city_world_doc_fixture.py`
14. `tests/test_graph_memory_mirathorn_city_candidate_graph_gold_fixture.py`
15. `apps/live_control_server/services/graph_gold_review.py` — generalize the registry (see "Registry generalization"). Edit only the named symbols.
16. `tests/test_live_graph_gold_review_api.py` — update the session-list assertion to include the new world-doc fixture key, plus mirror the existing vocab-ablation test style if needed. Minimal edits only.
17. `evals/graph_memory_layer/FIXTURE-STATUS.md` — add one "Manual gold" row (bounded hygiene task).

## Files explicitly OUT OF SCOPE

- `src/graph_memory/candidate_graph_preview.py`, `src/graph_memory/source_span.py` — read only.
- The S22/S23/C1S1 fixtures, loaders, tests — never edit.
- `corpus/**` — never mutate (read the source doc only).
- Any `src/prompts/*.py`, `apps/live-control-ui/**`, the vocabulary ablation runner/report.

## Registry generalization (file 15) — do this carefully; keep S22/S23 green

`_GOLD_SESSIONS` entries currently key on `session_number: int` and
`_gold_manifest_rel_path(session_number)` computes the dir as
`session_{n}_candidate_graph_gold`. Generalize so a non-session fixture works:

- Add a `fixture_key: str` and `gold_dir_rel: str` to EACH `_GOLD_SESSIONS` entry
  (S1/S22/S23 keep `session_number`; set their `gold_dir_rel` to the existing
  `session_{n}_candidate_graph_gold` path and `fixture_key` to e.g. `"session-1"`).
- Add the Mirathorn entry: `fixture_key: "mirathorn-city"`, `session_number: None`,
  `campaign_id: None`, `session_id: None`, `gold_fixture_id`, `load_gold_manifest`,
  `load_gold_graph_dict`, `gold_dir_rel:
  "evals/graph_memory_layer/examples/mirathorn_city_candidate_graph_gold"`.
- Change `_gold_manifest_rel_path` (and any seed-ref resolution branch) to use the
  entry's `gold_dir_rel` / a `fixture_key` switch instead of computing from
  `session_number`. Add a Mirathorn branch to the seed-ref resolver that calls the
  new world-doc fixture's `build_source_span_artifacts` / `parse_source_span_seed_refs`.
- The vocab-ablation hunks already in this file from the worktree are pre-existing —
  do not touch them.

If the gold-review service assumes `session_number` is an int elsewhere (e.g. summary
DTOs), make the field optional rather than breaking S22/S23. Keep the existing
sessions' API responses byte-identical.

## Anchors (file 2) — schema `dmb_mirathorn_city_world_doc_source_span_seed_refs_v0`, version `0.1`

`source_artifacts[]`: one entry — the snapshot (`artifact_kind: worldbuilding_doc`,
path = file 1, `evidence_role: source_evidence`, `visibility_state: player_visible`,
ids = the source_artifact_id/source_ref_id constants). All refs use those ids,
`artifact_kind: worldbuilding_doc`, `evidence_role: source_evidence`,
`visibility_state: player_visible`, `start_line == end_line == LINE`.

**Offset rule (compute, verify):** `line = lines[LINE-1]`;
`start_char = line.index(EXPECTED_PHRASE)`; `end_char = min(len(line), start_char+220)`.
Verify each resolves so `EXPECTED_PHRASE in preview_snippet`, snippet ≤ 240 chars,
snippet does not start with `#`.

| anchor_id | line | expected_phrase |
|---|---|---|
| `anchor:mira-cosmology-goddess` | 14 | `The nameless goddess gone, given their life to save everything` |
| `anchor:mira-elderwyld-continent` | 16 | `The Elderwyld is a continent on the edge of reality` |
| `anchor:mira-origin-lundayell` | 24 | `Founded over 200 years ago by settlers fleeing the Lundayell Empire` |
| `anchor:mira-airship` | 24 | `They repaired an ancient airship` |
| `anchor:mira-location-peaks-lake` | 30 | `At the base of the Stormspire Peaks, by Lake Mirathorn` |
| `anchor:mira-economy` | 38 | `Major industries include brewing, craftsmanship, fishing, agriculture` |
| `anchor:mira-luminox-sheep` | 44 | `Luminox Sheep are fluffy, woolly creatures` |
| `anchor:mira-float-goats` | 134 | `Float Goats are whimsical, goat-like creatures` |
| `anchor:mira-governance-council` | 166 | `A democratic city-state governed by a council` |
| `anchor:mira-key-locations` | 170 | `The Grand Market, Stormspire Academy, Lake Mirathorn Docks` |
| `anchor:mira-festival-expansion` | 174 | `Commemorates the Goddess` |
| `anchor:mira-temple-goddess` | 180 | `Built with murals transported tile-by-tile from the Lundayell Empire` |
| `anchor:mira-mayor-elara` | 190 | `Mayor Elara Swiftwind` |
| `anchor:mira-barin-inn` | 192 | `Barin Stonefoot` |
| `anchor:mira-grobnok` | 202 | `Grobnok the Goblin` |
| `anchor:mira-tinkerbright-college` | 212 | `Headmaster Tinkerbright` |
| `anchor:mira-thalia-commander` | 222 | `Commander Thalia Ashenvale` |
| `anchor:mira-thalia-wolf` | 228 | `she has been ensorcelled by the Wolf` |
| `anchor:mira-torrin-guilds` | 232 | `Torrin Flamescale` |
| `anchor:mira-merril-agri` | 242 | `Merril Tealeaf` |
| `anchor:mira-rurik-architect` | 252 | `Rurik Stonehammer` |
| `anchor:mira-brewing-co` | 318 | `Wizard's Tower Brewing Co` |
| `anchor:mira-walls-gates` | 336 | `The main gates of Mirathorn are grand and sturdy` |
| `anchor:mira-shepherds-flock` | 358 | `a group of Shepherd's Flock cultists is staging a protest` |

(24 anchors. If `index()` for an expected_phrase fails because the line has different
whitespace, STOP and report — do not silently alter the phrase.)

## Gold graph (file 5)

Top-level: schema `dmb_candidate_graph_preview_v0`, version `0.1`, preview_id
`candidate-preview:elderwyld:mirathorn-city:world-gold-v0`, `campaign_id: null`,
`session_id: null`, `source_artifact_ids: ["source-artifact:mirathorn-city-world-doc"]`,
`status: "preview"`. All semantic_state per the mapping section. Every node/edge needs
≥1 evidence_ref (the listed anchors) with `can_open_source: true, can_highlight_span:
true`. `node_type` must be in the IR set (`organization` is valid as a node_type;
but `corpus_ref.type` has no `organization`, so organization nodes use
`corpus_ref.type: "faction"` per the S22/C1S1 precedent). All `corpus_ref.resolution:
"proposed"` EXCEPT the two with existing hubs: `node:mirathorn`
(location/`mirathorn`/resolved, hub `Elderwyld/Cities and Towns/Mirathorn/README.md`)
and `node:stormspire-academy` (location/`stormspire_academy`/resolved, hub
`Elderwyld/Cities and Towns/Mirathorn/Stormspire Academy/README.md`).

### Nodes (28)

| node_id | label | node_type | importance | anchors | corpus_ref (type/slug) | warnings |
|---|---|---|---|---|---|---|
| `node:mirathorn` | `Mirathorn` | location | high | origin-lundayell, location-peaks-lake, governance-council | location/`mirathorn` RESOLVED | |
| `node:elderwyld` | `The Elderwyld` | location | high | elderwyld-continent | region/`elderwyld` | |
| `node:lundayell-empire` | `the Lundayell Empire` | faction | medium | origin-lundayell, temple-goddess | faction/`lundayell_empire` | |
| `node:ancient-airship` | `an ancient airship` | item | low | airship | item/`ancient_airship` | |
| `node:stormspire-peaks` | `the Stormspire Peaks` | location | medium | location-peaks-lake | region/`stormspire_peaks` | |
| `node:lake-mirathorn` | `Lake Mirathorn` | location | medium | location-peaks-lake, key-locations | location/`lake_mirathorn` | |
| `node:stormspire-academy` | `Stormspire Academy` | location | medium | key-locations | location/`stormspire_academy` RESOLVED | ambiguous: may be the same institution as `node:wizards-college`; do-not-auto-merge until source confirms |
| `node:wizards-college` | `the Wizard's College` | organization | medium | tinkerbright-college | faction/`wizards_college` | ambiguous: may run Stormspire Academy; needs review, do-not-auto-merge with `node:stormspire-academy` |
| `node:wizards-tower-brewing-co` | `Wizard's Tower Brewing Co` | organization | medium | brewing-co | faction/`wizards_tower_brewing_co` | SAME entity as the C1S1 `node:wizards-tower-brewing-co` — cross-document identity link (generalization probe) |
| `node:shepherds-flock` | `Shepherd's Flock` | faction | high | shepherds-flock | faction/`shepherds_flock` | cross-arc cult; appears as a contamination probe in other beds — here it is legitimate world canon |
| `node:temple-nameless-goddess` | `Temple of the Nameless Goddess` | location | medium | key-locations, temple-goddess | location/`temple_nameless_goddess` | |
| `node:nameless-goddess` | `the Nameless Goddess` | character | medium | cosmology-goddess, temple-goddess | npc/`nameless_goddess` | deity / cosmology figure |
| `node:festival-of-expansion` | `the Festival of Expansion` | event | medium | festival-expansion | — | evergreen recurring festival, not a session event |
| `node:mirathorn-city-council` | `the city council` | organization | high | governance-council | faction/`mirathorn_city_council` | cross-class: governance body vs the city/place `node:mirathorn` |
| `node:elara-swiftwind` | `Mayor Elara Swiftwind` | character | high | mayor-elara | npc/`elara_swiftwind` | |
| `node:tinkerbright` | `Headmaster Tinkerbright` | character | medium | tinkerbright-college | npc/`tinkerbright` | |
| `node:thalia-ashenvale` | `Commander Thalia Ashenvale` | character | medium | thalia-commander, thalia-wolf | npc/`thalia_ashenvale` | spoiler: secretly ensorcelled by the Wolf |
| `node:the-wolf` | `the Wolf` | character | medium | thalia-wolf | npc/`the_wolf` | spoiler: hidden antagonist controlling the Guard |
| `node:torrin-flamescale` | `Torrin Flamescale` | character | low | torrin-guilds | npc/`torrin_flamescale` | |
| `node:merril-tealeaf` | `Merril Tealeaf` | character | low | merril-agri | npc/`merril_tealeaf` | |
| `node:rurik-stonehammer` | `Rurik Stonehammer` | character | low | rurik-architect | npc/`rurik_stonehammer` | |
| `node:grobnok` | `Grobnok the Goblin` | character | low | grobnok | npc/`grobnok` | |
| `node:barin-stonefoot` | `Barin Stonefoot` | character | low | barin-inn | npc/`barin_stonefoot` | |
| `node:copper-quartz-inn` | `the Copper and Quartz Inn` | location | low | barin-inn | location/`copper_quartz_inn` | |
| `node:grit-and-grime` | `Grit and Grime` | location | low | grobnok | location/`grit_and_grime` | |
| `node:luminox-sheep` | `Luminox Sheep` | unknown_important | low | luminox-sheep | creature/`luminox_sheep` | |
| `node:float-goats` | `Float Goats` | unknown_important | low | float-goats | creature/`float_goats` | |
| `node:mirathorn-main-gates` | `the main gates of Mirathorn` | location | low | walls-gates | sublocation/`mirathorn_main_gates` | |

### Edges (26)

relationship_type is a free string. Each edge ≥1 evidence_ref from the listed anchor.

| edge_id | from | to | relationship_type | anchor |
|---|---|---|---|---|
| `edge:mirathorn-in-elderwyld` | node:mirathorn | node:elderwyld | located_in | elderwyld-continent |
| `edge:mirathorn-near-peaks` | node:mirathorn | node:stormspire-peaks | located_near | location-peaks-lake |
| `edge:mirathorn-by-lake` | node:mirathorn | node:lake-mirathorn | adjacent_to | location-peaks-lake |
| `edge:mirathorn-founded-from-lundayell` | node:mirathorn | node:lundayell-empire | founded_by_settlers_from | origin-lundayell |
| `edge:mirathorn-settled-via-airship` | node:mirathorn | node:ancient-airship | founded_using | airship |
| `edge:academy-in-mirathorn` | node:stormspire-academy | node:mirathorn | located_in | key-locations |
| `edge:temple-in-mirathorn` | node:temple-nameless-goddess | node:mirathorn | located_in | key-locations |
| `edge:copperquartz-in-mirathorn` | node:copper-quartz-inn | node:mirathorn | located_in | barin-inn |
| `edge:gritgrime-in-mirathorn` | node:grit-and-grime | node:mirathorn | located_in | grobnok |
| `edge:gates-part-of-mirathorn` | node:mirathorn-main-gates | node:mirathorn | located_in | walls-gates |
| `edge:festival-commemorates-goddess` | node:festival-of-expansion | node:nameless-goddess | commemorates | festival-expansion |
| `edge:temple-dedicated-to-goddess` | node:temple-nameless-goddess | node:nameless-goddess | dedicated_to | temple-goddess |
| `edge:temple-built-from-lundayell` | node:temple-nameless-goddess | node:lundayell-empire | murals_sourced_from | temple-goddess |
| `edge:council-governs-mirathorn` | node:mirathorn-city-council | node:mirathorn | governs | governance-council |
| `edge:elara-leads-council` | node:elara-swiftwind | node:mirathorn-city-council | leads | mayor-elara |
| `edge:tinkerbright-leads-college` | node:tinkerbright | node:wizards-college | leads | tinkerbright-college |
| `edge:tinkerbright-member-council` | node:tinkerbright | node:mirathorn-city-council | member_of | tinkerbright-college |
| `edge:thalia-member-council` | node:thalia-ashenvale | node:mirathorn-city-council | member_of | thalia-commander |
| `edge:torrin-member-council` | node:torrin-flamescale | node:mirathorn-city-council | member_of | torrin-guilds |
| `edge:merril-member-council` | node:merril-tealeaf | node:mirathorn-city-council | member_of | merril-agri |
| `edge:rurik-member-council` | node:rurik-stonehammer | node:mirathorn-city-council | member_of | rurik-architect |
| `edge:grobnok-operates-gritgrime` | node:grobnok | node:grit-and-grime | operates | grobnok |
| `edge:barin-operates-inn` | node:barin-stonefoot | node:copper-quartz-inn | operates | barin-inn |
| `edge:wolf-controls-thalia` | node:the-wolf | node:thalia-ashenvale | controls | thalia-wolf |
| `edge:flock-protests-mirathorn` | node:shepherds-flock | node:mirathorn | protests_at | shepherds-flock |
| `edge:brewery-near-mirathorn` | node:wizards-tower-brewing-co | node:mirathorn | located_near | brewing-co |

### Beats / writes / ignored / deferred

- `beats`: empty (`[]`) — world reference docs have no session beats. The test must
  NOT require beats.
- `proposed_writes` (2, write_type `create_node`, status `pending`, ≥1 ref):
  `node:mirathorn`, `node:shepherds-flock`.
- `ignored_items` (1): the fantastic-livestock bestiary tangent beyond the 2 sampled
  creatures (e.g. "Tidal Turtles / Starling Cows / Sunflower Ducks / Flutter Ferrets
  livestock catalog"), anchor `anchor:mira-luminox-sheep`.
- `deferred_items` (3, each ≥1 ref + suggested_next_step):
  (a) Stormspire Academy vs Wizard's College same-institution ambiguity;
  (b) Wizard's Tower Brewing Co cross-document identity link to the C1S1 gold;
  (c) the Wolf/Thalia spoiler control as a player-hidden relationship.
- `diagnostics`: `{preview_only: true, ...all dangerous flags false...,
  unresolved_evidence_refs: 0, missing_evidence_objects: 0, warning_count: <count>}`.

`HIGH_RISK_EVIDENCE_AUDIT` (file 8) must cover: `node:wizards-tower-brewing-co` /
`anchor:mira-brewing-co` / `Wizard's Tower Brewing Co`; `node:shepherds-flock` /
`anchor:mira-shepherds-flock` / `Shepherd's Flock`; `node:the-wolf` /
`anchor:mira-thalia-wolf` / `Wolf`.

## Manifests + loaders + tests

Mirror the C1S1 manifests/loaders/CLIs, renamed. The world-doc loader (file 7) has NO
recap normalization: `build_source_span_artifacts()` reads the snapshot file (file 1)
as a `SourceArtifactText`; `parse_source_span_seed_refs()` and
`resolve_source_span_seed_refs()` mirror C1S1. The gold loader (file 8) mirrors C1S1's
including `resolve_gold_evidence_refs()` and `validate_high_risk_evidence_audit()`.
Tests (files 13–14) mirror C1S1's structure with thresholds: nodes ≥ 26, edges ≥ 24,
anchors ≥ 22, deferred ≥ 3; beats may be 0; assert the snapshot text is NOT embedded
in the gold JSON; assert content terms (`mirathorn`, `the elderwyld`, `lundayell`,
`stormspire`, `shepherd's flock`, `wizard's tower brewing co`, `elara swiftwind`,
`tinkerbright`, `nameless goddess`). Keep CLI subprocess tests pointing at the new
`validate_/report_` modules.

## ID / name constants (verbatim)

| Purpose | Value |
|---|---|
| world-doc fixture_id | `graph-memory:mirathorn-city-world-doc:v0` |
| world-doc source-span schema | `dmb_mirathorn_city_world_doc_source_span_seed_refs_v0` |
| world-doc manifest schema | `dmb_mirathorn_city_world_doc_fixture_manifest_v0` |
| gold fixture_id | `graph-memory:mirathorn-city-candidate-graph-gold:v0` |
| gold manifest schema | `dmb_mirathorn_city_candidate_graph_gold_manifest_v0` |
| source_artifact_id | `source-artifact:mirathorn-city-world-doc` |
| source_ref_id | `source-ref:mirathorn-city-world-doc` |
| preview_id | `candidate-preview:elderwyld:mirathorn-city:world-gold-v0` |
| gold-review fixture_key | `mirathorn-city` |

## Verification (run all; paste full output)

```bash
PYTHONPATH=. python -m pytest tests/test_graph_memory_mirathorn_city_world_doc_fixture.py tests/test_graph_memory_mirathorn_city_candidate_graph_gold_fixture.py -q
PYTHONPATH=. python -m evals.graph_memory_layer.validate_mirathorn_city_world_doc_fixture
PYTHONPATH=. python -m evals.graph_memory_layer.validate_mirathorn_city_candidate_graph_gold_fixture
PYTHONPATH=. python -m pytest tests/test_live_graph_gold_review_api.py tests/test_graph_memory_session_1_candidate_graph_gold_fixture.py tests/test_graph_memory_session_22_candidate_graph_gold_fixture.py tests/test_graph_memory_session_23_candidate_graph_gold_fixture.py -q
```

All must pass (the last command proves S1/S22/S23 + the gold-review API still work
after the registry generalization).

## Reporting contract

Report `git status --porcelain` and `git diff --stat` filtered to ONLY the files you
created/edited (the 17 paths above). Paste full output of all four verification
commands. If any node/edge/anchor cannot validate, STOP and report the exact validator
error rather than altering the content spec.
