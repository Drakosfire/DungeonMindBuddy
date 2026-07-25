# SBW07a Server create/read transcript provenance

Recorded from DungeonMindServer `create_test_app()` TestClient via:

`scripts/capture_sbw07a_server_create_transcripts.py`

## Server anchor

See `MANIFEST.json` for the exact Server commit SHA, source fixtures, and
server-owned tests that already prove the same behaviors:

- `tests/statblocks_v1/api/test_statblock_resource_routes.py::test_create_append_and_exact_replay`
- `...::test_create_idempotent_replay_binds_observability`
- `...::test_write_idempotency_parent_stale_and_exact_locator_errors`
- `...::test_persistence_validation_failure_returns_receipt`
- `...::test_open_provenance_field_rejected_and_actor_is_not_created_by`
- `...::test_idempotency_conflict_before_validation_for_changed_invalid_payload`

## Regeneration

```bash
cd /path/to/DungeonMindServer
uv run python /path/to/DungeonMindBuddy/scripts/capture_sbw07a_server_create_transcripts.py \
  --buddy-repo /path/to/DungeonMindBuddy \
  --server-repo .
```

Buddy client tests must replay these recorded response bodies. They must not
invent Server idempotency or terminality by returning an unconditional success
fixture.
