# Roadmaps

Active roadmap and status documents for DungeonBuddy.

## Active authority

| Document | Role |
|---|---|
| [`../Design/ARCHITECTURE-campaign-supergraph.md`](../Design/ARCHITECTURE-campaign-supergraph.md) | Canonical World Supergraph architecture and authority model |
| [`ROADMAP-campaign-supergraph.md`](ROADMAP-campaign-supergraph.md) | Canonical implementation phases and current critical path |
| [`../Plans/PR-TRACKER-campaign-supergraph.md`](../Plans/PR-TRACKER-campaign-supergraph.md) | Sole active sequencing tracker for Campaign Supergraph slices |
| [`ROADMAP-cross-surface-statblock-demo.md`](ROADMAP-cross-surface-statblock-demo.md) | Active integration roadmap across Ingest, Graph Review, Hermes, Build, Plan, Play, and statblocks |
| [`ROADMAP-con-ready.md`](ROADMAP-con-ready.md) | Product-readiness user stories and CON-READY acceptance gates |
| [`ROADMAP-playable-hoist-dungeonmind-kernel.md`](ROADMAP-playable-hoist-dungeonmind-kernel.md) | Living Playable → Buddy-shared → DungeonMind kernel graduation map and mandatory implementation-PR review ledger |
| [`../Design/STATUS-world-graph-continuity-spine.md`](../Design/STATUS-world-graph-continuity-spine.md) | Current-state guide to how the read/write authority path works in the product |

The architecture owns invariants. The Campaign Supergraph roadmap owns phases. The PR tracker owns implementation order. The cross-surface roadmap coordinates the end-to-end product demonstration without overriding any owning workstream. The CON-READY roadmap owns GM-visible acceptance stories. The Playable hoist roadmap owns graduation/hoist sequence and must be re-read against evidence on every Playable implementation PR.

## Retired and historical material

- [`../Design/GRAPH-MEMORY-SUPERGRAPH-ARCHITECTURE-ROADMAP.md`](../Design/GRAPH-MEMORY-SUPERGRAPH-ARCHITECTURE-ROADMAP.md) is a tombstone for the superseded June 2026 roadmap. Its full copy lives under `Docs/Archive/Architecture/`.
- The detailed pre-consolidation Campaign Supergraph roadmap, tracker, and cross-surface roadmap remain available in Git history at `09aed8db` (the `main` snapshot immediately after PR #443 merged).
- Completed handoffs and acceptance reports are evidence, not active roadmap authority. Archive them under `Docs/Plans/archive/` or `Docs/Reports/` when their slice closes.
