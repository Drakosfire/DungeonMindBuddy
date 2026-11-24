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

- Failure observability: check existing safe provider and worker failure
  diagnostics against the concern in [#1146](https://github.com/Drakosfire/DungeonMindBuddy/pull/1146).
  Add work only for a demonstrated gap, without exposing raw provider bodies,
  credentials or sensitive messages. The current worker records safe error
  kinds and types; this note does not establish whether the old HTTP-status
  requirement is satisfied.

Use representative source-backed dogfood and review exact evidence, identity,
admission and fresh readback at their owning boundaries. Split confirmed gaps
into independently reviewable slices; this idea does not authorize a provider
run, corpus mutation, World publication, or implementation.
