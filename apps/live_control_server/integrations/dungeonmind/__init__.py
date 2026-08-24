"""Permanent DungeonMind product integration namespace (CUTOVER R.3 / D.1).

This package owns Buddy's direct consumption of DungeonMind's native World
Graph services in ``dungeonmind`` authority mode:

- ``world_graph_reads`` — production projection / retrieval / recap facts
- ``world_graph_writes`` — exact-run prepare mutation context and confirm

Neither path constructs a UnionSupergraphStore, replays contributions, opens
the Buddy graph kernel, or hydrates a Buddy-shaped cache.
"""
