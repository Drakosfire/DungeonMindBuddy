# [IDEA] Step through Buddy’s trace and search in Conversation Details

**Captured:** 2026-11-14  
**Status:** Original design capture retained below; merged local mechanisms and remaining acceptance are distinguished here. Not an implementation handoff.

## Evidence reconciliation — 2026-11-17

The original “first slice” below is historical design intent, not an unbuilt assignment. Saved replay, exact evidence opening, writer-evidence labels, unified Details, directed hops/pruning, node inspection and shared node views landed in the replay series from [#3738](https://github.com/Drakosfire/DungeonMindBuddy/pull/3738) through [#3784](https://github.com/Drakosfire/DungeonMindBuddy/pull/3784) (replay-specific changes, not every PR in that numeric interval). Representative boundaries: [#3741](https://github.com/Drakosfire/DungeonMindBuddy/pull/3741), [#3745](https://github.com/Drakosfire/DungeonMindBuddy/pull/3745), [#3755](https://github.com/Drakosfire/DungeonMindBuddy/pull/3755), [#3764](https://github.com/Drakosfire/DungeonMindBuddy/pull/3764), [#3767](https://github.com/Drakosfire/DungeonMindBuddy/pull/3767), [#3772](https://github.com/Drakosfire/DungeonMindBuddy/pull/3772), [#3773](https://github.com/Drakosfire/DungeonMindBuddy/pull/3773), [#3776](https://github.com/Drakosfire/DungeonMindBuddy/pull/3776), [#3781](https://github.com/Drakosfire/DungeonMindBuddy/pull/3781) and [#3784](https://github.com/Drakosfire/DungeonMindBuddy/pull/3784).

[#3773](https://github.com/Drakosfire/DungeonMindBuddy/pull/3773) has local source/browser verification in the Graph owner's lane. Later local 5202 rollouts include the replay improvements; that does not qualify the hosted route or every original ambition. Retain exact saved-attempt citations, missing-evidence disclosure, World/revision isolation and accessible controls as acceptance boundaries. Hosted access/ordinary browser acceptance must be verified on its own route; broader live trace teaching/timing and any unrecorded search paths remain separate, not inferred complete from playback. Do not reconstruct missing hops or call a model merely to replay a saved turn.

[#3683](https://github.com/Drakosfire/DungeonMindBuddy/pull/3683) remains unmerged historical design input for extending this experience; its original narrative is not adopted or discarded by this status update. The product roadmap retains sequencing authority.

## Original design narrative (historical)

When a GM opens **Details** on a Buddy reply, show a small, read-only graph that plays back how Buddy gathered context for that turn. Let the GM pause, step backward and forward, and open an exact retained citation without leaving the conversation. Make it feel like watching the search unfold at a human pace, not watching live telemetry or reading an event log.

## One experience

Extend the existing Conversation Details trace tooling instead of adding a separate trace explorer, replay screen, or Jev-only viewer. The saved attempt is the record. The graph visualizes recorded World search steps, including Jev where present, beside a readable timeline; source reads and final context can be shown when the same attempt proves them. A missing relationship in the World is a separate problem from showing what the attempt actually did.

## First slice

- Reuse the Graph visualizer's rendering and visual language, with a compact layout designed for replay. Load it only when Details is opened. No full World graph, editing tools, or separate graph page.
- Highlight matched nodes and recorded graph steps in order. Distinguish a relationship returned in search results from an edge actually traversed. Do not animate a hop when the trace only records a result or lacks endpoints.
- Keep source search and citation reads alongside the graph. Distinguish what Buddy found, what it opened, and what was included in the final answer's model input when the saved attempt proves that. Label missing, bounded, or unavailable evidence rather than filling it in.
- Keep the detailed trace available below the replay and offer a text step list. Stepping through a saved attempt does not rerun the search or call a model. Exact historical citation reopening keeps existing World, revision, and viewer-access checks.

## Dogfood check

Start with one real saved Buddy reply, not a hand-drawn route. Open its Details, step through a recorded search and an evidence read, and reopen the exact citation. If the trace has a gap or a non-graph fallback, show it plainly. The Wandering Forest is a useful second witness if a suitable saved turn exists: distinguish a recorded path to Fallen Spine, a missing connection to Thrin, or a recap fallback without filling in absent hops. Do not make Forest ingestion repair part of the replay slice.

Related design: [Buddy's work, explained](https://github.com/Drakosfire/DungeonMindBuddy/blob/42f5fd6f36fffa71eea73ad3d7ac4cff1bc63fe5/Docs/Design/DESIGN-agent-trace-teaching-and-timing.md). This idea covers completed-turn playback only, not live status or timing estimates.
