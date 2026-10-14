# BUILD — immutable extraction source snapshot

Status ACTIVE; operator resilience goal. PRIME implementation, ARCHITECTURE review.
Base e9e56c7a041449d29f541f9fade6edde35021bdf.
Lane /tmp/buddy-run-source-snapshot; branch codex/build-run-source-snapshot.
Topology parallel-independent prerequisite to #1155; disjoint source runner files.
Write lease: this handoff; src/graph_memory/extraction/graph_preview_runner.py;
tests/test_graph_preview_runner.py;
apps/live_control_server/services/graph_run_registry.py.

Prepared registration stores exact digest-verified normalized source bytes in the
run-owned output directory, never links the source component to mutable workspace
Markdown. Preserve original provenance in source registry; no legacy recovery.
Existing snapshot cannot be overwritten with different bytes. Source/span offsets
must refer to the same normalized body. Verify later mutable-file edits do not alter
snapshot/components; wrong digest and conflicting snapshot reject before inference.
No provider, serving or retained database writes. Finish bounded PR and independent
review before adoption; #1155 historical witness consumes accepted behavior.

Scope amendment: registered evidence admission must recognize only the exact
source.md sibling of the registered candidate component, with bytes matching the
original SourceArtifact digest. Never accept arbitrary alternate source URIs.
