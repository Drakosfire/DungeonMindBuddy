# Transfer — Eldyrwild world graph (2026-07-27)

Machine-local `out/` is gitignored. This branch force-adds a snapshot so another
desktop can restore the durable World Graph without re-promoting.

## Snapshot

| Field | Value |
|---|---|
| World | `eldyrwild` |
| Head revision | `rev:2a72ef7a40ba37bc33e3f2680d528970` |
| Head updated_at | `2026-07-27T22:34:38Z` |
| Path | `out/graph_memory/worlds/eldyrwild/` |
| Not included | `out/graph_memory/runs/` (session extracts), `.write.lock` |

## Restore on the other desktop

From a clean-enough checkout of this repo:

```bash
git fetch origin transfer/eldyrwild-world-graph-2026-07-27
git checkout origin/transfer/eldyrwild-world-graph-2026-07-27 -- out/graph_memory/worlds/eldyrwild
```

Verify:

```bash
cat out/graph_memory/worlds/eldyrwild/head.json
# expect head_revision_id: rev:2a72ef7a40ba37bc33e3f2680d528970
```

Then return to your working branch (`git switch main` or your feature branch).
The restored files stay in the working tree as untracked/ignored under `out/`.

## Notes

- Do not merge this branch into `main`. It exists only as a transfer vehicle.
- After restore, delete or leave the remote branch; it is not product history.
