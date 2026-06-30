# HANDOFF — Campaign 1 Session 1 candidate-graph gold (full S22/S23 parity)

Status: ready for execution (composer-2)
Workstream: Graph Memory / Contextual Vocabulary test-bed expansion
Design authority: `Docs/Design/DESIGN-contextual-vocabulary-layer.md` (2026-06-30 addendum, "Test-bed expansion")
Roadmap: `Docs/Design/GRAPH-MEMORY-CONTEXTUAL-VOCABULARY-ROADMAP.md` (Milestone 4 follow-ups)

## Mission

Create a hand-authored **Campaign 1 Session 1** candidate-graph gold fixture at
full parity with the existing Session 22 / Session 23 fixtures, so the four-variant
vocabulary ablation can run on a fresh cross-campaign bed with built-in cross-class
and do-not-merge probes. Source recap:
`Session 01 - Stonebridge and Glowkindle Rats` (`longmont-c1`, session 1).

This is **mechanical replication** of the S23 fixture scaffold with the content
spec below. All node/edge/anchor judgment is fixed in this document — do not invent,
add, or drop entities, and do not "improve" wording.

## Required reading (read before writing)

Read these S23 files and mirror their structure exactly, renaming `23`→`1`,
`longmont-c2`→`longmont-c1`, and session-specific IDs per the constants table:

- `evals/graph_memory_layer/session_23_recap_ingest_fixture.py`
- `evals/graph_memory_layer/session_23_candidate_graph_gold_fixture.py`
- `evals/graph_memory_layer/validate_session_23_recap_ingest_fixture.py`
- `evals/graph_memory_layer/report_session_23_recap_ingest_fixture.py`
- `evals/graph_memory_layer/validate_session_23_candidate_graph_gold_fixture.py`
- `evals/graph_memory_layer/report_session_23_candidate_graph_gold_fixture.py`
- `evals/graph_memory_layer/examples/session_23_recap_ingest/` (all JSON + md)
- `evals/graph_memory_layer/examples/session_23_candidate_graph_gold/` (gold + manifest)
- `tests/test_graph_memory_session_23_recap_ingest_fixture.py`
- `tests/test_graph_memory_session_23_candidate_graph_gold_fixture.py`
- `apps/live_control_server/services/graph_gold_review.py` (`_GOLD_SESSIONS`, `_resolve_session_seed_refs`)
- `src/graph_memory/candidate_graph_preview.py` (schema/validation — DO NOT EDIT)
- `src/graph_memory/source_span.py` (resolver — DO NOT EDIT)

## Files IN SCOPE (create these; default-deny everything else)

Data files:
1. `evals/c1_live_prep/live/session_1/session_1_raw_recap.md`
2. `evals/graph_memory_layer/examples/session_1_recap_ingest/expected_normalized_recap.md`
3. `evals/graph_memory_layer/examples/session_1_recap_ingest/expected_paragraph_index.json`
4. `evals/graph_memory_layer/examples/session_1_recap_ingest/source_span_seed_refs.json`
5. `evals/graph_memory_layer/examples/session_1_recap_ingest/session_1_recap_ingest_manifest.json`
6. `evals/graph_memory_layer/examples/session_1_recap_ingest/README.md` (short, mirror S23 README tone)
7. `evals/graph_memory_layer/examples/session_1_candidate_graph_gold/candidate_graph_gold.json`
8. `evals/graph_memory_layer/examples/session_1_candidate_graph_gold/session_1_candidate_graph_gold_manifest.json`

Python loaders + CLIs (mirror S23 byte-for-byte structure, renamed):
9. `evals/graph_memory_layer/session_1_recap_ingest_fixture.py`
10. `evals/graph_memory_layer/session_1_candidate_graph_gold_fixture.py`
11. `evals/graph_memory_layer/validate_session_1_recap_ingest_fixture.py`
12. `evals/graph_memory_layer/report_session_1_recap_ingest_fixture.py`
13. `evals/graph_memory_layer/validate_session_1_candidate_graph_gold_fixture.py`
14. `evals/graph_memory_layer/report_session_1_candidate_graph_gold_fixture.py`

Tests:
15. `tests/test_graph_memory_session_1_recap_ingest_fixture.py`
16. `tests/test_graph_memory_session_1_candidate_graph_gold_fixture.py`

Registry wiring (edit ONLY the named symbols):
17. `apps/live_control_server/services/graph_gold_review.py` — add a Session 1 entry to
    `_GOLD_SESSIONS`, the two imports, and a `session_number == 1` branch in
    `_resolve_session_seed_refs`. Mirror the S23 entry exactly. Touch nothing else.
18. `evals/graph_memory_layer/FIXTURE-STATUS.md` — add one row for the new manual gold
    (the bounded hygiene task). Touch nothing else.

## Files explicitly OUT OF SCOPE

- `src/graph_memory/candidate_graph_preview.py`, `src/graph_memory/source_span.py`,
  `src/agent/recap_ingest_helpers.py` — read only, never edit.
- The S22/S23 fixtures, loaders, tests — never edit.
- Any `src/prompts/*.py`, any other `evals/*/gold/*.json`, any UI/`apps/live-control-ui/**`.
- The vocabulary ablation runner/report. The worldbuilding-doc gold (separate handoff).

## ID / name constants (use verbatim)

| Purpose | Value |
|---|---|
| campaign_id | `longmont-c1` |
| session (int) | `1` |
| recap-ingest fixture_id | `graph-memory:session-1-recap-ingest:v0` |
| recap-ingest manifest schema | `dmb_session_1_recap_ingest_fixture_manifest_v0` |
| paragraph index schema | `dmb_session_1_recap_paragraph_index_v0` |
| source-span seed schema | `dmb_session_1_recap_source_span_seed_refs_v0` |
| raw recap rel path | `evals/c1_live_prep/live/session_1/session_1_raw_recap.md` |
| recap title | `Session 1 - Stonebridge and Glowkindle Rats` |
| gold fixture_id | `graph-memory:session-1-candidate-graph-gold:v0` |
| gold manifest schema | `dmb_session_1_candidate_graph_gold_manifest_v0` |
| source_artifact_id | `source-artifact:session-1-normalized-recap` |
| source_ref_id | `source-ref:session-1-normalized-recap` |
| preview_id | `candidate-preview:longmont-c1:s1:stonebridge-glowkindle-rats:gold-v0` |
| session_id (gold) | `session-1` |

## Step 1 — raw recap (file 1), verbatim content

Write this EXACT text (preserve all original typos/double-spaces — source truth):

```
Session 1 Recap

After traveling together for some time together as merchant guards, our mish mash of travelers;  Karsemine the Tiefling Ranger, Stafl the 'Human' Bard, Caelynn the Half Elf Sorcerer, Ephanna the Kenku Warlock, Bonogo the Bugbear Rogue, and Baergrom the Dwarf Fighter, found themselves outside the town of Stone Bridge.

The town of Stone Bridge is known for very few things, in fact Stone Bridge is hardly known. It has the Stone Bridge over the river [River name], it's tavern  The River's Edge Pub run by Grishna the Half-orc, and that's about it. It did have a job board, and most importantly the local brewer Glowkindle had posted a help request on the jobs board and spread word all around town of his need of a band of mercenaries to help clean up some rats.

While doing some drinking at the Riv'ers Edge Pub to wash away the road, Grishna was quick to share that Glowkindle had been through, where the The Wizard's Tower Brewing Co was located. Up river, west at the big rock, walk till you see it. Bonogo, having very little awareness or care for the cost of things, and greatly enjoying the beer, bought a Firkin of ale for two gold. He quite enjoyed the hike to the brewery.

Grishna was true to her word, the directions were sound. There was a clear trail along the river to an enormous boulder.  As the group approached it resolved into what must have been the foot of a once enormous statue. Or a mad sculptures dedication to someone's foot, probably the  former but who really knows with art anyway.

Another few hours walk away from the river along the trail led the group to the Wizard's Tower Brewing Company.  Bustling with activity, and smelling of brewing, the fine tap room lit by magical crystals, was empty except for the troupe of gnomes busily brewing.

Within they met Glowkindle who told them, a bit about the issue at hand. Giant rats had assaulted his excavation crew after they broke through a wall expanding the fermentation cellar. For a healthy prize of 25 gold pieces each, the team agreed to clear out the rats.  Which was significantly harder than expected, led to multiple folk going down, a mysterious cat owl being tossed into the room to help, a lot of blood from rats and teammates, and many, many, many health potions being downed.

A fine first combat to bring the team together!

Finally, free to explore the team found a beautifully tiled hallway, a trapped mosaic on the ground, a room full of broken alchemical tools. As Karsemine wisely searched the room, eventually looking up, she made eye contact with another resident of the shatter mages tower. Some kind of flaming magma infused spider monstrosity.
```

## Step 2 — generate deterministic artifacts (files 2 & 3) via the helper

Generate with `assemble_recap` / `build_paragraph_index` so the test
`load_expected_normalized_recap() == normalized` passes. The normalized recap
MUST be exactly (verified):

- frontmatter lines 1–11, `# Session 1 Recap` on line 12, blank line 13,
- 8 body paragraphs on lines **14, 16, 18, 20, 22, 24, 26, 28** (blank lines between),
- `paragraph_count_out == 8`, no flattened `---` junk paragraph.

Use a one-off generation script (NOT committed) that reads file 1 and calls
`assemble_recap(raw_notes=raw, session=1, campaign_id="longmont-c1",
title="Session 1 - Stonebridge and Glowkindle Rats", remove_duplicates=True)`,
then `build_paragraph_index(raw)` analog (mirror the S23 fixture's
`build_paragraph_index`, paragraph_id prefix `s1-p{ii:03d}`). Write the outputs to
files 2 and 3. The S1 loader's `build_paragraph_index` must reproduce file 3 exactly.

## Step 3 — anchors (file 4: source_span_seed_refs.json)

`source_artifacts[]`: two entries mirroring S23 — the raw recap
(`artifact_kind: raw_recap`, path = file 1) and the normalized recap
(`artifact_kind: normalized_recap`, path = file 2). `evidence_role: source_evidence`,
`visibility_state: gm_private`. Schema = `dmb_session_1_recap_source_span_seed_refs_v0`,
version `0.1`, fixture_id = recap-ingest fixture_id.

For every anchor below: `source_ref_id`/`source_artifact_id` = the **normalized**
recap ids, `artifact_kind: normalized_recap`, `evidence_role: source_evidence`,
`visibility_state: gm_private`, `start_line == end_line == LINE`.

**Offset rule (compute, do not guess):** in the normalized recap, let
`line = lines[LINE-1]`; set `start_char = line.index(EXPECTED_PHRASE)` and
`end_char = min(len(line), start_char + 220)`. Verify each resolves with
`resolve_many_source_span_refs(..., snippet_max_chars=240, context_lines=0)` so that
`EXPECTED_PHRASE in preview_snippet`, `len(snippet) <= 240`, and the snippet does
not start with `#`.

| anchor_id | line | expected_phrase | label |
|---|---|---|---|
| `anchor:c1s1-party-arrival` | 14 | `Karsemine the Tiefling Ranger` | party of six arrives outside Stone Bridge |
| `anchor:c1s1-stonebridge-overview` | 16 | `The town of Stone Bridge is known` | Stone Bridge town overview |
| `anchor:c1s1-stone-bridge-span` | 16 | `Stone Bridge over the river` | the literal Stone Bridge over the river |
| `anchor:c1s1-rivers-edge-pub-grishna` | 16 | `The River's Edge Pub run by Grishna` | River's Edge Pub run by Grishna |
| `anchor:c1s1-glowkindle-job` | 16 | `the local brewer Glowkindle had posted` | Glowkindle posts the rat-clearing job |
| `anchor:c1s1-wizards-tower-located` | 18 | `The Wizard's Tower Brewing Co was located` | Wizard's Tower Brewing Co location/directions |
| `anchor:c1s1-bonogo-firkin` | 18 | `bought a Firkin of ale` | Bonogo buys a Firkin of ale |
| `anchor:c1s1-statue-foot` | 20 | `the foot of a once enormous statue` | giant statue-foot landmark on the trail |
| `anchor:c1s1-tower-gnomes` | 22 | `the troupe of gnomes busily brewing` | brewing gnomes at the tower tap room |
| `anchor:c1s1-rats-cellar` | 24 | `Giant rats had assaulted his excavation crew` | giant rats attack the cellar excavation crew |
| `anchor:c1s1-rats-job-agreed` | 24 | `the team agreed to clear out the rats` | party accepts the rat-clearing job |
| `anchor:c1s1-cat-owl` | 24 | `a mysterious cat owl being tossed into the room` | mysterious cat owl tossed in to help |
| `anchor:c1s1-first-combat` | 26 | `A fine first combat to bring the team together` | first combat brings the team together |
| `anchor:c1s1-tower-interior` | 28 | `a beautifully tiled hallway, a trapped mosaic` | tower interior: hallway, mosaic, alchemy room |
| `anchor:c1s1-magma-spider` | 28 | `flaming magma infused spider monstrosity` | magma spider cliffhanger |

(15 anchors; all single-line. `anchor:c1s1-tower-interior` uses
`shatter mages tower` as a secondary phrase is NOT needed — use the table phrase.)

## Step 4 — gold graph (file 7: candidate_graph_gold.json)

Top-level: schema `dmb_candidate_graph_preview_v0`, version `0.1`,
preview_id/campaign_id/session_id per constants, `source_artifact_ids:
["source-artifact:session-1-normalized-recap"]`, `status: "preview"`.

Every node and edge `semantic_state` = `{canon_state: "played_canon",
lifecycle_state: "candidate", evidence_role: "source_evidence",
authority_state: "system_derived", visibility_state: "gm_private"}`.
Every node/edge: `proposed_action: "create"`, `confidence: "high"|"medium"|"low"`
per importance. Every `evidence_ref`: `{source_ref_id, source_artifact_id,
source_anchor_id, label, evidence_role: "source_evidence", can_open_source: true,
can_highlight_span: true}` using the normalized-recap ids. `node_type` MUST be one of
the IR set (`character, location, item, faction, organization, event, session_beat,
clue, thread, mystery, group, warning, promise, debt, rumor, unknown_important`) —
note `combat_encounter` is NOT allowed; the rat fight uses `event`; creatures use
`unknown_important`.

### Nodes (26)

corpus_ref: use `resolution: "proposed"` with the slug shown for all EXCEPT Grishna.
Grishna is `resolution: "resolved"`, hub_path
`Elderwyld/Cities and Towns/Stonebridge/NPCs/grishna/README.md`. Party node has no corpus_ref.

| node_id | label | node_type | importance | anchors | corpus_ref (type/slug) | warnings |
|---|---|---|---|---|---|---|
| `node:heroes-party` | `Heroes / Party` | group | high | party-arrival | — | |
| `node:karsemine` | `Karsemine` | character | high | party-arrival, tower-interior | pc/`karsemine` | |
| `node:stafl` | `Stafl` | character | medium | party-arrival | pc/`stafl` | |
| `node:caelynn` | `Caelynn` | character | medium | party-arrival | pc/`caelynn` | |
| `node:ephanna` | `Ephanna` | character | medium | party-arrival | pc/`ephanna` | |
| `node:bonogo` | `Bonogo` | character | medium | party-arrival, bonogo-firkin | pc/`bonogo` | |
| `node:baergrom` | `Baergrom` | character | medium | party-arrival | pc/`baergrom` | |
| `node:stone-bridge-town` | `Stone Bridge` | location | high | party-arrival, stonebridge-overview | location/`stonebridge` | do-not-merge with `node:stone-bridge-span` (the bridge) — shared label, distinct concepts |
| `node:stone-bridge-span` | `the Stone Bridge` | location | low | stone-bridge-span | sublocation/`stone_bridge_span` | the river crossing, not the town; do-not-merge with `node:stone-bridge-town` |
| `node:rivers-edge-pub` | `The River's Edge Pub` | location | medium | rivers-edge-pub-grishna | location/`rivers_edge_pub` | |
| `node:grishna` | `Grishna` | character | medium | rivers-edge-pub-grishna | npc/`grishna` RESOLVED | |
| `node:glowkindle` | `Glowkindle` | character | high | glowkindle-job, rats-cellar | npc/`glowkindle` | |
| `node:wizards-tower-brewing-co` | `The Wizard's Tower Brewing Co` | organization | high | wizards-tower-located, tower-gnomes | organization/`wizards_tower_brewing_co` | cross-class: same site surfaces as organization (the company) and as location `node:wizards-tower` |
| `node:wizards-tower` | `the shatter mage's tower` | location | medium | tower-interior, magma-spider | location/`wizards_tower_site` | cross-class with `node:wizards-tower-brewing-co`: the physical tower vs the brewing company |
| `node:fermentation-cellar` | `the fermentation cellar` | location | medium | rats-cellar | sublocation/`fermentation_cellar` | |
| `node:statue-foot-landmark` | `the giant statue foot` | location | low | statue-foot | location/`statue_foot_landmark` | |
| `node:brewing-gnomes` | `the troupe of gnomes` | group | medium | tower-gnomes | faction/`wizards_tower_gnomes` | |
| `node:excavation-crew` | `Glowkindle's excavation crew` | group | low | rats-cellar | faction/`glowkindle_excavation_crew` | |
| `node:giant-rats` | `Giant rats` | unknown_important | high | rats-cellar | creature/`giant_rats` | |
| `node:cat-owl` | `the cat owl` | unknown_important | low | cat-owl | creature/`cat_owl` | |
| `node:magma-spider` | `flaming magma infused spider monstrosity` | unknown_important | high | magma-spider | creature/`magma_spider` | cliffhanger reveal |
| `node:rat-clearing-job` | `the rat-clearing job` | thread | high | glowkindle-job, rats-job-agreed | — | |
| `node:rat-cellar-combat` | `the rat cellar fight` | event | high | rats-job-agreed, first-combat | — | combat encounter modeled as event (combat_encounter not in IR) |
| `node:firkin-of-ale` | `a Firkin of ale` | item | low | bonogo-firkin | item/`firkin_of_ale` | |
| `node:job-board` | `the Stone Bridge job board` | item | low | stonebridge-overview, glowkindle-job | item/`stonebridge_job_board` | |
| `node:shatter-mage-mystery` | `the shatter mage's tower mystery` | mystery | medium | tower-interior, magma-spider | — | |

### Edges (24)

relationship_type is a free string (no enum). Each edge needs ≥1 evidence_ref from
the listed anchor. Confidence per importance.

| edge_id | from | to | relationship_type | anchors |
|---|---|---|---|---|
| `edge:karsemine-member-of-party` | node:karsemine | node:heroes-party | member_of | party-arrival |
| `edge:stafl-member-of-party` | node:stafl | node:heroes-party | member_of | party-arrival |
| `edge:caelynn-member-of-party` | node:caelynn | node:heroes-party | member_of | party-arrival |
| `edge:ephanna-member-of-party` | node:ephanna | node:heroes-party | member_of | party-arrival |
| `edge:bonogo-member-of-party` | node:bonogo | node:heroes-party | member_of | party-arrival |
| `edge:baergrom-member-of-party` | node:baergrom | node:heroes-party | member_of | party-arrival |
| `edge:grishna-operates-pub` | node:grishna | node:rivers-edge-pub | operates | rivers-edge-pub-grishna |
| `edge:pub-located-in-stonebridge` | node:rivers-edge-pub | node:stone-bridge-town | located_in | stonebridge-overview |
| `edge:bridge-located-in-stonebridge` | node:stone-bridge-span | node:stone-bridge-town | located_in | stone-bridge-span |
| `edge:jobboard-located-in-stonebridge` | node:job-board | node:stone-bridge-town | located_in | stonebridge-overview |
| `edge:glowkindle-operates-brewery` | node:glowkindle | node:wizards-tower-brewing-co | operates | rats-cellar |
| `edge:glowkindle-posted-job` | node:glowkindle | node:rat-clearing-job | posted | glowkindle-job |
| `edge:job-on-jobboard` | node:rat-clearing-job | node:job-board | posted_on | glowkindle-job |
| `edge:party-accepts-job` | node:heroes-party | node:rat-clearing-job | undertakes | rats-job-agreed |
| `edge:party-travels-to-brewery` | node:heroes-party | node:wizards-tower-brewing-co | travels_to | wizards-tower-located |
| `edge:grishna-knows-brewery` | node:grishna | node:wizards-tower-brewing-co | knows_about | wizards-tower-located |
| `edge:gnomes-member-of-brewery` | node:brewing-gnomes | node:wizards-tower-brewing-co | member_of | tower-gnomes |
| `edge:brewery-located-in-tower` | node:wizards-tower-brewing-co | node:wizards-tower | located_in | wizards-tower-located |
| `edge:cellar-located-in-tower` | node:fermentation-cellar | node:wizards-tower | located_in | rats-cellar |
| `edge:crew-member-of-brewery` | node:excavation-crew | node:wizards-tower-brewing-co | member_of | rats-cellar |
| `edge:rats-located-in-cellar` | node:giant-rats | node:fermentation-cellar | located_in | rats-cellar |
| `edge:rats-part-of-combat` | node:giant-rats | node:rat-cellar-combat | part_of | first-combat |
| `edge:combat-threatens-crew` | node:rat-cellar-combat | node:excavation-crew | threatens | rats-cellar |
| `edge:catowl-part-of-combat` | node:cat-owl | node:rat-cellar-combat | part_of | cat-owl |

### Beats (5), proposed_writes (2), ignored_items (1), deferred_items (2)

Author `beats[]` (order 1..5, each with title/summary/involved_node_ids drawn from
the node_ids above, ≥1 evidence_ref, proposed_action `create`): (1) arrival at Stone
Bridge, (2) the pub + the job from Glowkindle, (3) trail to the brewery past the
statue foot, (4) the rat-cellar fight, (5) the tower interior + magma-spider
cliffhanger. `proposed_writes[]` (write_type `create_node`, status `pending`): one for
`node:glowkindle`, one for `node:wizards-tower-brewing-co`. `ignored_items[]`: one
(e.g. `[River name]` unnamed river placeholder). `deferred_items[]`: two — the
Stone-Bridge town-vs-span do-not-merge and the brewing-company-vs-tower cross-class,
each with `suggested_next_step`. All need ≥1 evidence_ref.

`diagnostics`: `{preview_only: true, extraction_performed: false, llm_used: false,
runtime_connected: false, plan_connected: false, agent_interaction_connected: false,
corpus_scanned: false, corpus_mutated: false, facts_promoted: false,
canon_promoted: false, unresolved_evidence_refs: 0, missing_evidence_objects: 0,
warning_count: <count of node+edge warnings>}`.

## Step 5 — manifests (files 5 & 8) and loaders (files 9–14)

Mirror the S23 manifests and loader modules exactly, renamed per constants. The gold
manifest `notes[]` should describe: source = C1S1 normalized recap; the
town-vs-span do-not-merge probe; the brewing-company-vs-tower cross-class probe;
corpus_ref resolvability convention (Grishna resolved, rest proposed). The gold loader
must define a `HIGH_RISK_EVIDENCE_AUDIT` tuple covering at least:
`node:stone-bridge-span`/`anchor:c1s1-stone-bridge-span`/`Stone Bridge over the river`;
`node:wizards-tower-brewing-co`/`anchor:c1s1-wizards-tower-located`/`Wizard's Tower Brewing Co`;
`node:wizards-tower`/`anchor:c1s1-magma-spider`/`magma`.

## Step 6 — tests (files 15 & 16)

Mirror the S23 test files, renamed, with C1S1-appropriate thresholds:
nodes ≥ 24, edges ≥ 22, beats ≥ 5, proposed_writes ≥ 2, ignored_items ≥ 1,
deferred_items ≥ 2, anchors ≥ 14. Keep the same structural/boundary/no-corpus-leak
assertions (gold JSON must NOT contain the full normalized recap or raw recap text).
Replace the S23 content-term list with C1S1 terms (e.g. `stone bridge`, `grishna`,
`glowkindle`, `wizard's tower brewing co`, `the troupe of gnomes`, `giant rats`,
`fermentation cellar`, `magma`, `karsemine`, `bonogo`). Keep the CLI subprocess tests
pointing at the new `validate_/report_` modules.

## Step 7 — gold-review wiring (file 17)

In `apps/live_control_server/services/graph_gold_review.py`: add the two S1 imports,
add a Session 1 dict to `_GOLD_SESSIONS` (mirror the S23 entry: `session_number: 1`,
`gold_fixture_id`, `load_gold_manifest`, `load_gold_graph_dict`), and add a
`session_number == 1` branch to `_resolve_session_seed_refs` returning the S1 seed
refs. Do not change behavior for sessions 22/23.

## Verification (run all; paste output)

```bash
PYTHONPATH=. python -m pytest tests/test_graph_memory_session_1_recap_ingest_fixture.py tests/test_graph_memory_session_1_candidate_graph_gold_fixture.py -q
PYTHONPATH=. python -m evals.graph_memory_layer.validate_session_1_recap_ingest_fixture
PYTHONPATH=. python -m evals.graph_memory_layer.validate_session_1_candidate_graph_gold_fixture
PYTHONPATH=. python -m pytest tests/test_live_graph_gold_review_api.py tests/test_graph_memory_session_23_candidate_graph_gold_fixture.py -q
```

All must pass (the last command proves S23 + the gold-review API still work after wiring).

## Reporting contract

Report `git status --porcelain` and `git diff --stat` filtered to ONLY the files you
created/edited (the 18 paths above) — not the whole worktree. Paste the full output of
the four verification commands. If any node/edge/anchor in the spec cannot be made to
validate, STOP and report the exact validator error rather than altering the content
spec.
