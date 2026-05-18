# PR49 Corpus Artifact Report — Stone Bridge + River's Edge Hubs

## Scope

PR49 creates corpus/reference artifacts only. It does not modify retrieval ranking, admission behavior, renderer behavior, lane classification, or active benchmark gold.

## Files added

- `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/Locations/stone_bridge/README.md`
- `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/README.md`
- `evals/c1s4_preplanning_vertical_slice/analysis/pr49_corpus_artifact_report.md`

## Convention updates made

PR49 also clarifies `Docs/CONVENTION-Location-Hub.md` for this scenario:

- Location hub NPC-anchor sections are navigation/affiliation indexes only.
- Location hubs must not satisfy NPC-continuity gold merely because they name or link an NPC.
- NPC continuity must be read from `subject_class: npc` artifacts or observed play records admitted into the NPC/character lane.
- Location hub spelling variants should be handled as aliases/retrieval keywords unless a deliberate canon decision splits them into separate places.
- No new core frontmatter alias field was introduced; the corpus subject-schema frontmatter vocabulary remains closed.

## Existing NPC hubs verified

Verified existing hubs are present and not duplicated:

- `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/NPCs/pippa/README.md`
- `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/README.md`
- `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/NPCs/grishna/README.md`

## Light updates made to existing NPC hubs

- None in PR49. Existing hubs were verified for presence and continuity role.

## Authority boundary statement

All new canon claims in the location hubs are grounded in observed Session 3 recap material (`Session 3 - The Stone Bridge Flood.md`). Uncertain details are preserved as open questions and not canonized.

## NPC anchor evidence boundary

The Stone Bridge and River's Edge Pub hubs link Pippa, Bubbles, and Grishna as location-affiliation/navigation anchors. Those mentions help a planner find the correct NPC hubs, but they are not themselves NPC-continuity evidence.

Future lane-aware gold must enforce this boundary:

- `location_worldbuilding` expectations may be satisfied by `subject_class: location` hubs.
- `character_party_behavior` / NPC-continuity expectations must require `subject_class: npc` artifacts or observed play records admitted into the NPC/character lane.
- Location hub `Suggested reads`, `Cross-references`, `Retrieval keywords`, and NPC-anchor lists must not count as evidence for NPC-continuity gold.

## Canonical name and slug decision

PR49 canonizes the campaign-facing location name as **Stone Bridge**.

- Canonical campaign display name: `Stone Bridge`
- Canonical campaign filesystem slug: `stone_bridge`
- Legacy/support spellings retained only for retrieval: `StoneBridge`, `Stonebridge`

Use **Stone Bridge** in new campaign artifacts. Treat `StoneBridge` and `Stonebridge` as older/support spellings unless a later canon decision deliberately splits them into distinct places.

## Open questions preserved

- Exact Stone Bridge-to-Mirathorn route specifics.
- Intermediate settlements and route ecology.
- Detailed Stone Bridge civic/governance/economic structures.
- River's Edge Pub ownership/staffing/building-plan details.

## Gold / oracle safety notes

- `Retrieval keywords`, `Suggested reads`, and `Cross-references` are lexical/navigation aids only and must not count as benchmark evidence.
- Location hubs may mention NPC names as anchors, but those mentions must not satisfy NPC-continuity gold unless the evidence source is an NPC artifact or observed play record admitted into the character/NPC lane.
- PR reports, eval analysis files, gold files, canvas payloads, and planning docs must never be included in the retrieval corpus.
- Future gold should require expected rendered section and source/subject class, not only substring matches.

## What PR49 does not solve

- PR49 does not classify artifacts into planner presentation lanes.
- PR49 does not guarantee immediate lane-balanced rendering in context canvas outputs.
- Location/worldbuilding and character/NPC lanes may still not render until PR50 classification/indexing work.
- Active benchmark gold is unchanged until PR51.

## What PR50 should do next

PR50 should classify and index these location and NPC artifacts into the intended context lanes:

- Location hubs to `location_worldbuilding`
- NPC continuity hubs to `character_party_behavior`

Then verify Q1/Q3/Q5 packets render lane-balanced context using:

- `Locations/stone_bridge/README.md`
- `Locations/rivers_edge_pub/README.md`
- `NPCs/pippa/README.md`
- `NPCs/bubbles_the_float_goat/README.md`
- `NPCs/grishna/README.md`
- `Locations/hempholm/README.md`

PR50 should also add or verify retrieval-corpus hygiene tests so `evals/**`, `Docs/**`, tests, PR reports, gold files, and canvas payloads cannot appear as candidate retrieval context.