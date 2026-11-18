# Historical isolated Graph demo

This lab retains the isolated launcher and loopback HTTP transport used by the
earlier native Graph demonstration. Buddy's product Graph uses its maintained
routes and the shared service/storage in `apps/live_control_server/native_graph_demo/`.
Those production modules stay in place. The isolated HTTP server is no longer
copied into the production image.

## Dependency and support boundary

The launcher deliberately requires these historical dependency revisions:

- DungeonMind: `430c1a6db631d097dfa0a273f8933067f708bc56`.
- WorldKeeper: `ef9c50f2d6aa89a35e9408f83fc4d0ba47825ca2`.

Buddy's current locked DungeonMind revision differs. An ordinary current-lock
environment therefore fails the launcher's exact dependency guard. Relocation
does not qualify a historical environment against today's product service or
establish native create/edit/restart compatibility. Do not weaken the guard or
silently replace the pin to make startup succeed. Current-lock requalification
or retirement belongs to [the Graph owner follow-up #4014](https://github.com/Drakosfire/DungeonMindBuddy/issues/4014).

From the repository root, inspect the retained CLI without starting a runtime:

```bash
python3 evals/native_graph_demo/launch.py --help
```

Actual launch additionally requires the matching dependency environment, clean
exact Core source, isolated built UI assets, and a private task-owned PostgreSQL
runtime. The retained checks refuse ambient PostgreSQL settings, foreign state,
unverified source and ambiguous ownership. No shared database fallback exists.
Use the [lab guide](../README.md) for Projects storage and scratch isolation.
For ordinary Buddy use, follow the [local Play runbook](../../Docs/Runbooks/RUNBOOK-local-play-dogfood.md).

## Evidence and recovery

`tests/test_native_graph_demo_http.py` retains the real loopback protocol and
launcher isolation tests. Its fake-service cases do not qualify native semantic
operations. Shared service/storage and index Graph tests remain independent.

The original source locations are recoverable from the exact pre-relocation
Buddy revision `26132b18652ef80b0c311cdfc08a8f6b118ad5b3`:

```bash
git show 26132b18652ef80b0c311cdfc08a8f6b118ad5b3:scripts/native_graph_demo.py
git show 26132b18652ef80b0c311cdfc08a8f6b118ad5b3:apps/live_control_server/native_graph_demo/server.py
```

The [historical handoff](../../Docs/Plans/HANDOFF-SURFACE-native-graph-demo.md)
preserves dated topology and evidence limits. Its old paths and assignments are
historical references, not current launch instructions or active leases.
