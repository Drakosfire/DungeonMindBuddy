# REPORT — Buddy APP-STATE durability drill

**Status:** PASSED — three proofs complete. Stage 2A is DONE. This file is **not** a Stage 2B dispatch.  
**Handoff:** `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-application-state-durability-drill-v1.md`  
**Recorded:** 2026-09-07 (America/Denver)

```text
container dies → Plan survives
computer reboots → Plan survives
volume destroyed → Plan restored from backup
```

Stage 2B was not started.

## 1. Exact git SHA

```text
35269f087cf1dcee52f169f339d1de79599b3374
main — squash merge of PR #691
```

Checkout: `/home/drakosfire/Projects/DungeonOverMind/DungeonMindBuddy`. Old #691 worktree was not recreated.

## 2. Redacted DSN

```text
host=127.0.0.1 port=54331 db=dungeonbuddy_application_state user=buddy
```

`.env` `DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL` was previously `dungeonmind@127.0.0.1:54329`. For this drill it was pinned to the documented local 54331 DSN (user `buddy`) so `load_dungeonmindbuddy_dotenv(override=True)` cannot send uvicorn back to tmpfs 54329.

## 3. Empty digest vs witness digest

| When | Digest |
| --- | --- |
| Empty birth (before Plan UI write) | `d98c650c5c87117fde689fc7497331925b3b93f84fac4733ffde5dd8d21ebb2a` |
| After Plan UI create (and after restore) | `57e74f3f3836fd126a6a62c786ed283d5f03a59c6a547e48d3291b1d1f2a97a8` |

They differ. Artifact: `out/application_state/witness.fingerprint.json` (gitignored).

Witness Plan created only through Plan **Create prep** (POST `/api/live/workspace-documents` 200). No SQL insert.

- Title: `Durability Witness — Delete Me Later`
- `document_id`: `3c8c6f8b-498d-4d3e-afaf-15b2e1a6520d`
- campaign: `longmont-c2` session: 23
- `content.work_object` rows: 1

## 4. Container restart (volume intact)

The live 54331 container had been started from the retired worktree compose project `dungeonmindbuddy-application-state-durable-authority-v1`. `docker compose -f compose.postgres.app-state.yml down` from this checkout would not have owned that container.

```text
docker compose -p dungeonmindbuddy-application-state-durable-authority-v1 -f compose.postgres.app-state.yml down
# 54331 gone; 54329 and 54330 still listening
docker compose -f compose.postgres.app-state.yml up -d
# remounted named volume dungeonbuddy_app_state_data
```

54330 (`dungeonmind-postgres-authority`) was not touched.

```text
uv run python scripts/application_state_authority.py check \
  --expect-fingerprint out/application_state/witness.fingerprint.json
READY: live fingerprint matches expected
fingerprint: 57e74f3f3836fd126a6a62c786ed283d5f03a59c6a547e48d3291b1d1f2a97a8
```

Buddy reload: Plan combobox still `Durability Witness — Delete Me Later · Session 23` at `/plan?campaigns=longmont-c2&documentId=3c8c6f8b-498d-4d3e-afaf-15b2e1a6520d`.

**Proof 1:** container dies → Plan survives.

## 5. Machine reboot

Human shutdown/boot. `who -b`: system boot **2026-09-07 18:49**. Checked at 18:53 (uptime 4 min). Docker was empty; 54329/54330/54331 were all down.

```text
docker compose -f compose.postgres.app-state.yml up -d
# remounted existing volume dungeonbuddy_app_state_data (CreatedAt 2026-09-07 15:55)
uv run python scripts/application_state_authority.py check \
  --expect-fingerprint out/application_state/witness.fingerprint.json
READY: live fingerprint matches expected
fingerprint: 57e74f3f3836fd126a6a62c786ed283d5f03a59c6a547e48d3291b1d1f2a97a8
```

Buddy after reboot: same Plan title in the combobox. World 54330 was not started (`authority_unavailable`); the Plan still loaded from 54331.

Vite hit `ENOSPC` (inotify watchers) on first start after reboot because uvicorn `--reload` was already watching the tree. Vite was restarted with `CHOKIDAR_USEPOLLING=1`. Not a durability failure.

**Proof 2:** computer reboots → Plan survives.

## 6. Backup SHA-256

```text
uv run python scripts/application_state_authority.py backup \
  --out out/application_state/witness.dump
backup sha256: 49f7260a98838d8189b071239e0c1d39a7979c4b491118693c856c4a7afad08a
dump fingerprint: 57e74f3f3836fd126a6a62c786ed283d5f03a59c6a547e48d3291b1d1f2a97a8
```

Sidecars (gitignored, not committed):

- `out/application_state/witness.dump`
- `out/application_state/witness.dump.sha256`
- `out/application_state/witness.dump.fingerprint.json`

## 7. `down -v`: Plan gone

```text
docker compose -f compose.postgres.app-state.yml down -v
# Volume dungeonbuddy_app_state_data Removed
# 54331 Connection refused
check --expect-fingerprint → exit 2
application-state PostgreSQL is unavailable
```

**Destroy succeeded.** 54330 was not running and was not named in this compose file.

After `up -d` with a **new** empty volume, before restore:

```text
application-state schema is behind Alembic head
check exit 2
```

No `bootstrap apply` was run. That empty-of-APP-STATE-schemas database is the supported restore target.

## 8. Restore

```text
uv run python scripts/application_state_authority.py restore \
  --backup out/application_state/witness.dump
READY: backup SHA-256 verified; restored fingerprint matches expected
fingerprint: 57e74f3f3836fd126a6a62c786ed283d5f03a59c6a547e48d3291b1d1f2a97a8
```

Follow-up `check --expect-fingerprint`: `READY: live fingerprint matches expected`.

Buddy UI after restore: combobox `Durability Witness — Delete Me Later · Session 23`, same `document_id` `3c8c6f8b-498d-4d3e-afaf-15b2e1a6520d`.

**Proof 3:** volume destroyed → Plan restored from backup.

## 9. Confirmations

- No SQL inserts into `content.*` / `play.*` / `ingest.*` / `source.*`
- Seed happened before the first kill
- 54330 untouched (World compose never used; after reboot it stayed down)
- Dump bytes not committed
- Stage 2B not started
- Restore verified SHA-256 before replay; did not `pg_restore` by hand
- Restore did not need a hand-dropped schema (target was unborn after `down -v`)

## 10. Stage 2A ruling

Steward ruling 2026-09-07: **Stage 2A — durable APP-STATE substrate: DONE.** Stage 2 and STOP 2 remain open. Stage 2B is next and is not dispatched.

## 11. Witness Plan retention

Steward ruling 2026-09-07: **keep** `Durability Witness — Delete Me Later` on `54331` for now (`3c8c6f8b-498d-4d3e-afaf-15b2e1a6520d`). Its presence is harmless, its identity is historical evidence of the drill, and deleting durable WorkObjects waits until Plan has a supported lifecycle operation. Do not invent a one-off cleanup path (SQL, curl discard, or local-draft Discard). The row is not campaign canon and is not C1/C2 material.
