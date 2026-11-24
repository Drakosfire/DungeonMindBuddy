# Idea: refine Worldbuilding ingestion

**Status:** IDEA — review and design, not an implementation assignment.
**Captured:** 2026-11-24
**Owner:** Buddy Build / ingestion; World authority and publication remain with their owning components.
**Sequencing:** The [product roadmap](../Roadmaps/ROADMAP-demo.md) owns sequencing.

Review the current Worldbuilding source-to-World journey as a whole: source
selection and evidence, extraction, identity and relationship proposals,
review, publication and source readback. Start by mapping what already works
and the strongest current evidence before deciding which gaps merit separate
slices. Preserve source-grounded review and explicit publication.

Consider together:

- Reviewing extracted observations beside their exact source support and making
  explicit identity and assertion decisions. The old [#1235](https://github.com/Drakosfire/DungeonMindBuddy/pull/1235)
  is retained design and implementation evidence, not proof that the current
  workflow lacks this capability.
- Extraction and admission polish for player-character and party candidate kinds,
  Event-to-location relationships, and unsupported relationship output. Compare
  current schemas, mappings and handling with [#1144](https://github.com/Drakosfire/DungeonMindBuddy/pull/1144),
  [#1147](https://github.com/Drakosfire/DungeonMindBuddy/pull/1147) and
  [#1149](https://github.com/Drakosfire/DungeonMindBuddy/pull/1149) before
  proposing a repair; do not assume the old behavior is missing.
- Identity review: check whether article-prefixed name variants are surfaced
  without automatic merges and whether a reviewed observation can bind to an
  exact existing location. Reconcile historical [#1853](https://github.com/Drakosfire/DungeonMindBuddy/pull/1853)
  and [#1855](https://github.com/Drakosfire/DungeonMindBuddy/pull/1855) with
  current identity and admission owners.
- Ingest usability: dogfood independent per-session source drafts, including an
  intentional empty draft and stale-response protection ([#2081](https://github.com/Drakosfire/DungeonMindBuddy/pull/2081)).
  Check truthful elapsed-time and waiting feedback against the existing
  [activity proposal #4333](https://github.com/Drakosfire/DungeonMindBuddy/pull/4333)
  and historical [#2082](https://github.com/Drakosfire/DungeonMindBuddy/pull/2082);
  do not invent progress the backend cannot observe.

- Known-name review: assess optional, explicit correction or keep decisions for
  likely source spelling mistakes, preserving original source and context.
  [#2087](https://github.com/Drakosfire/DungeonMindBuddy/pull/2087) is
  historical evidence; check current behavior before introducing another step.
- Evidence selection: assess safe handling of uniquely identifiable exact
  quotes with wrong nominated paragraphs, harmless source whitespace, and
  separately selected supported extents around unsupported gaps. Preserve exact
  source bytes and admission; ambiguous or unsupported material must remain
  held. Historical examples: [#2118](https://github.com/Drakosfire/DungeonMindBuddy/pull/2118),
  [#2124](https://github.com/Drakosfire/DungeonMindBuddy/pull/2124), and
  [#2152](https://github.com/Drakosfire/DungeonMindBuddy/pull/2152).
- Uncertainty and source status: check that extraction and downstream answers
  preserve attribution, rumor, tentative claims and planning versus played
  events. Reconcile [#2131](https://github.com/Drakosfire/DungeonMindBuddy/pull/2131)
  and [#2225](https://github.com/Drakosfire/DungeonMindBuddy/pull/2225)
  with current ingestion and answer-composition owners; neither a citation nor
  a fluent answer alone establishes that an event occurred.
- Incomplete-run accounting: compare current operation-level usage reporting
  with [#2113](https://github.com/Drakosfire/DungeonMindBuddy/pull/2113)'s
  acknowledged-attempt lower-bound concern. Current source retains attempt
  evidence, but the inspected usage summarizer reads operation observations.
  Verify whether acknowledged usage survives a missing final receipt without
  double-counting or presenting unknown totals as complete.

- Failure observability: check existing safe provider and worker failure
  diagnostics against the concern in [#1146](https://github.com/Drakosfire/DungeonMindBuddy/pull/1146).
  Add work only for a demonstrated gap, without exposing raw provider bodies,
  credentials or sensitive messages. The current worker records safe error
  kinds and types; this note does not establish whether the old HTTP-status
  requirement is satisfied.

**Already addressed in current source:** standard recap composition qualifies
colliding local node IDs by pass and rejects duplicate IDs within a pass. See
`src/graph_memory/extraction/category_candidate_graph_extractor.py` and its
owning tests; [#2149](https://github.com/Drakosfire/DungeonMindBuddy/pull/2149)
is historical context, not a new assignment. This source inspection is not
proof that every historical extraction failure has been repaired.

Use representative source-backed dogfood and review exact evidence, identity,
admission and fresh readback at their owning boundaries. Split confirmed gaps
into independently reviewable slices; this idea does not authorize a provider
run, corpus mutation, World publication, or implementation.
