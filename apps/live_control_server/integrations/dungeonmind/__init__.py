"""Permanent DungeonMind product integration namespace (CUTOVER R.3).

This package owns Buddy's direct consumption of DungeonMind's native World
Graph read services (R.1 projection / R.2 retrieval) in ``dungeonmind``
authority mode. It replaces the compatibility-era hydration/kernel read path
under ``integrations/dungeonmind_kernel`` for production reads: no
UnionSupergraphStore construction, no contribution replay, no Buddy graph
kernel, and no frozen Buddy graph files are involved on this path.
"""
