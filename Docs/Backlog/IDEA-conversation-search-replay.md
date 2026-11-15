# [IDEA] Replay Buddy's search in Conversation Details

**Captured:** 2026-11-14  
**Status:** Unscheduled product idea. Not an implementation handoff.

When a GM opens **Details** on a Buddy reply, show a small, read-only graph that plays back how Buddy gathered context for that turn. Let the GM pause, step backward and forward, and open an exact retained citation without leaving the conversation. Make it feel like watching the search unfold at a human pace, not watching live telemetry or reading an event log.

## First slice

- Reuse the Graph visualizer's rendering and visual language, with a compact layout designed for replay. Load it only when Details is opened. No full World graph, editing tools, or separate graph page.
- Highlight matched nodes and recorded graph steps in order. Distinguish a relationship returned in search results from an edge actually traversed. Do not animate a hop when the trace only records a result or lacks endpoints.
- Keep source search and citation reads alongside the graph. Distinguish what Buddy found, what it opened, and what was included in the final answer's model input when the saved attempt proves that. Label missing, bounded, or unavailable evidence rather than filling it in.
- Keep the detailed trace available below the replay and offer a text step list. Stepping through a saved attempt does not rerun the search or call a model. Exact historical citation reopening keeps existing World, revision, and viewer-access checks.

## Dogfood check

Start with one real saved Buddy reply, not a hand-drawn route. Open its Details, step through a recorded search and an evidence read, and reopen the exact citation. If the trace has a gap or a non-graph fallback, show it plainly. The Wandering Forest is a good demo candidate if a suitable turn exists.

Related design: [Buddy's work, explained](https://github.com/Drakosfire/DungeonMindBuddy/blob/42f5fd6f36fffa71eea73ad3d7ac4cff1bc63fe5/Docs/Design/DESIGN-agent-trace-teaching-and-timing.md). This idea covers completed-turn playback only, not live status or timing estimates.
