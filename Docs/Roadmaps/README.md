# Roadmaps

Active roadmap and status documents for DungeonBuddy.

## Active authority

| Document | Role |
|---|---|
| [`../Design/ARCHITECTURE-campaign-supergraph.md`](../Design/ARCHITECTURE-campaign-supergraph.md) | Canonical World Supergraph architecture and authority model |
| [`ROADMAP-campaign-supergraph.md`](ROADMAP-campaign-supergraph.md) | Canonical implementation phases and current critical path |
| [`../Plans/PR-TRACKER-campaign-supergraph.md`](../Plans/PR-TRACKER-campaign-supergraph.md) | Sole active sequencing tracker for Campaign Supergraph slices |
| [`ROADMAP-cross-surface-statblock-demo.md`](ROADMAP-cross-surface-statblock-demo.md) | Active integration roadmap across Ingest, Graph Review, Hermes, Build, Plan, Play, and statblocks |
| [`../Design/STATUS-world-graph-continuity-spine.md`](../Design/STATUS-world-graph-continuity-spine.md) | Current-state guide to how the read/write authority path works in the product |

The architecture owns invariants. The Campaign Supergraph roadmap owns phases. The PR tracker owns implementation order. The cross-surface roadmap coordinates the end-to-end product demonstration without overriding any owning workstream.

## Retired and historical material

- [`../Design/GRAPH-MEMORY-SUPERGRAPH-ARCHITECTURE-ROADMAP.md`](../Design/GRAPH-MEMORY-SUPERGRAPH-ARCHITECTURE-ROADMAP.md) is a tombstone for the superseded June 2026 roadmap. Its full copy lives under `Docs/Archive/Architecture/`.
- The detailed pre-consolidation Campaign Supergraph roadmap, tracker, and cross-surface roadmap remain available in Git history at `09aed8db` (the `main` snapshot immediately after PR #443 merged).
- Completed handoffs and acceptance reports are evidence, not active roadmap authority. Archive them under `Docs/Plans/archive/` or `Docs/Reports/` when their slice closes.
