# SBW07a Server create/read transcript provenance

Recorded from a **clean** DungeonMindServer checkout via:

`scripts/capture_sbw07a_server_create_transcripts.py`

The capture script refuses dirty Server worktrees, requires the imported
`statblocks_v1` package to resolve inside `--server-repo`, records the Server
OpenAPI fingerprint + source-fixture blob hashes, and fails unless that
fingerprint matches Buddy's vendored `OPENAPI_FINGERPRINT`.

## Server anchor

See `MANIFEST.json` for:

- Server commit SHA
- `worktree_clean: true`
- `statblocks_v1` package path
- OpenAPI fingerprint (must equal Buddy vendored fingerprint)
- `simple_bruiser.json` / `unknown_resource_pool.json` sha256 hashes
- server-owned route tests that already prove the same behaviors

## Regeneration

```bash
# Use a clean detached worktree of the intended Server commit:
git -C /path/to/DungeonMindServer worktree add --detach /tmp/dms-clean <commit>
cd /tmp/dms-clean
PYTHONPATH=/tmp/dms-clean /path/to/DungeonMindServer/.venv/bin/python \
  /path/to/DungeonMindBuddy/scripts/capture_sbw07a_server_create_transcripts.py \
  --buddy-repo /path/to/DungeonMindBuddy \
  --server-repo /tmp/dms-clean
```

Buddy client tests must replay these recorded response bodies. They must not
invent Server idempotency or terminality by returning an unconditional success
fixture.
