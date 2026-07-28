# Transfer PR — Eldyrwild world graph

Machine-local `out/` is gitignored. This branch (and its open PR) force-adds a
durable World Graph snapshot so another desktop can restore without re-promoting.

**Do not merge into `main`.** Keep the PR open and refresh the branch when the
local head moves.

## Current snapshot

| Field | Value |
|---|---|
| World | `eldyrwild` |
| Path | `out/graph_memory/worlds/eldyrwild/` |
| Not included | `out/graph_memory/runs/`, `.write.lock` |

Check `head.json` on this branch for the exact `head_revision_id` / `updated_at`.

## Restore on another desktop

```bash
git fetch origin transfer/eldyrwild-world-graph-2026-07-27
git checkout origin/transfer/eldyrwild-world-graph-2026-07-27 -- out/graph_memory/worlds/eldyrwild
git rm -r --cached out/graph_memory/worlds/eldyrwild
cat out/graph_memory/worlds/eldyrwild/head.json
```

Return to your working branch afterward. Files remain under ignored `out/`.

## Refresh this transfer (source machine)

From a checkout that already has the up-to-date local graph under `out/`:

```bash
git fetch origin
git checkout transfer/eldyrwild-world-graph-2026-07-27
git pull --ff-only origin transfer/eldyrwild-world-graph-2026-07-27

# Replace the packaged snapshot with the local out/ tree
git rm -r --cached out/graph_memory/worlds/eldyrwild 2>/dev/null || true
rm -rf out/graph_memory/worlds/eldyrwild
# copy/rsync from the machine-local graph if this checkout is not the source,
# otherwise the files are already present under out/
git add -f \
  out/graph_memory/worlds/eldyrwild/head.json \
  out/graph_memory/worlds/eldyrwild/contribution_index.json \
  out/graph_memory/worlds/eldyrwild/contributions \
  out/graph_memory/worlds/eldyrwild/contribution_rebuild \
  out/graph_memory/worlds/eldyrwild/initialization \
  out/graph_memory/worlds/eldyrwild/revisions

git commit -m "transfer: refresh Eldyrwild world graph snapshot"
git push origin transfer/eldyrwild-world-graph-2026-07-27

# Restore local ignored graph if checkout removed it when switching branches:
git checkout HEAD -- out/graph_memory/worlds/eldyrwild
git rm -r --cached out/graph_memory/worlds/eldyrwild
git checkout main
```

Prefer a new commit per refresh (keeps the PR timeline readable). Avoid amending
pushed history unless you intentionally force-push.

## Notes

- Campaign graph content is private; keep the PR draft/internal and do not paste
  node/edge prose into public channels.
- Session extract runs stay out unless explicitly requested.
