# SBW07a Server create/read transcript provenance

Recorded from a **clean** DungeonMindServer checkout via:

`scripts/capture_sbw07a_server_create_transcripts.py`

The capture script refuses dirty Server worktrees, requires the imported
`statblocks_v1` package to resolve inside `--server-repo`, records the Server
OpenAPI fingerprint + source-fixture blob hashes, and fails unless that
fingerprint matches Buddy's vendored `OPENAPI_FINGERPRINT`.

## Historical schema identity (create and revise)

These captures and the sibling `server_revise_transcripts` are historical
evidence. Their manifests record the schema used at capture time, SHA256
`df46327f24180150aadd28a8fe6477ceabde40c300b64c931b27e639a762f36a`.
The exact [historical Buddy schema](https://github.com/Drakosfire/DungeonMindBuddy/blob/14d8b50343fd9b9cecbb7890bb5e4684b78ba514/apps/live_control_server/integrations/dungeonmind_statblocks/openapi/dungeonbuddy-statblocks-v1.json)
remains in Git; do not relabel the manifests when today's schema changes.
Existing response/request replay checks establish compatibility with current
models, not a new Server capture or current end-to-end qualification.

`generated.OPENAPI_FINGERPRINT` names the current canonical schema. New captures
still refuse a Server schema that differs from that current fingerprint by
default. Updating captures requires genuine new execution and provenance.

## Server anchor

See `MANIFEST.json` for:

- Server commit SHA
- `worktree_clean: true`
- `statblocks_v1` package path
- OpenAPI fingerprint (equal to Buddy vendored fingerprint at capture time)
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

The capture stages files before replacing the destination files and publishes
the manifest last. If `.capture-in-progress` is present, treat the fixture
set as incomplete. Confirm the capture process has stopped, restore the prior
fixture set from its known Git revision or saved copy, then remove the marker
and rerun. For scratch captures, rerun into a new directory.
