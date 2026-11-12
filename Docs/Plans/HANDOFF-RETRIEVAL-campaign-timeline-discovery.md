# RETRIEVAL campaign timeline discovery

Status: ACTIVE under the Campaign 1 chronology goal.
Base: `8bcff4db28f022f66cbb1a89fcfd09f383d36dfc`.
Branch: `codex/campaign-timeline-discovery`.
Checkout: managed `campaign-timeline-discovery/DungeonMindBuddy`.
Topology: parallel-independent of #2468. That ingestion PR edits run catalog and persistence tests.

Write set: this handoff, `apps/live_control_server/services/native_graph_reads.py`, and `tests/test_native_recap_event_placement.py`.

Expand a campaign search hit one hop along its published timeline placements. Use the existing pinned, scoped Core reads and assertion selection. Skip incomplete campaign reads, deduplicate Event IDs, and keep other search scopes unchanged. No migrations, providers, or primary writes. Use the existing isolated chronology evaluator for readback and disposable local contract fixtures for regression tests.

The retained Campaign 1 probe recovered all 60 missing edges through scoped entity reads. Verify the integrated path against that evidence and test that ordinary campaign and World searches remain scoped.
