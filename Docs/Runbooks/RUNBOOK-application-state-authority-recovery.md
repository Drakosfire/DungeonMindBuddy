# RUNBOOK — Buddy APP-STATE durable authority and recovery

**Status:** ACTIVE operator procedure (born 2026-09-07, post-tmpfs-loss rebrief)
**Authority:** `HANDOFF-DOGFOOD-CONTINUITY-application-state-durable-authority-v1.md` (§0A rebrief)
**Substrate:** `compose.postgres.app-state.yml` — `dungeonbuddy-app-state` on `127.0.0.1:54331`, named volume `dungeonbuddy_app_state_data`
**Tooling:** `scripts/application_state_authority.py` (`check` / `fingerprint` / `backup` / `restore` / `verify`)

## Local PostgreSQL topology

| Port | Container | Owner | Durability |
| --- | --- | --- | --- |
| 54329 | `dungeonmind-postgres-dev` | DungeonMind dev | **tmpfs — never durable** |
| 54330 | `dungeonmind-postgres-authority` | DungeonMind durable World authority | named volume |
| 54331 | `dungeonbuddy-app-state` | **Buddy APP-STATE authority (this runbook)** | named volume |

Buddy APP-STATE and DungeonMind World are separate authorities. Never point Buddy at a DungeonMind database; the tooling blocks World DSNs as targets.

## Operating law

1. **No migrate-on-start.** Schema changes are explicit: `uv run python scripts/bootstrap_local_play.py apply` (or `python -m application_state.cli upgrade`) with the target DSN configured. Neither the compose service nor the Buddy API migrates on boot.
2. **Runtime reads exactly the configured DSN.** `DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL` is the only APP-STATE coordinate. There is no fallback database.
3. **Schema-at-head is never READY.** `check` without `--expect-fingerprint` reports **OBSERVED**. READY requires fingerprint parity against a trusted expected fingerprint (`check --expect-fingerprint` or `verify` / `restore`).
4. **Restore verifies dump bytes before replay.** The `.sha256` sidecar (or `--expect-sha256`) must match the dump; a missing or mismatched digest refuses restore. The `.fingerprint.json` sidecar (or `--expect-fingerprint`) is required — restore cannot claim READY without it.
5. **The volume is the destroy line.** `docker compose -f compose.postgres.app-state.yml down` and container replacement keep data. `down -v` or `docker volume rm dungeonbuddy_app_state_data` destroys the authority — never run these as part of ordinary stop/start.
6. **Local persistence is not remote backup.** External dumps via `backup` are the recovery artifact. Remote hosting/HA is Stage 8 and out of scope.
7. **Backups and fingerprints are local artifacts.** Do not commit dump bytes. Fingerprints contain no secrets; DSNs are always redacted in output.

## Bring up the durable authority (first birth)

```bash
# 1. Start the durable substrate
docker compose -f compose.postgres.app-state.yml up -d

# 2. Point this shell at the durable authority (local dev default credentials)
export DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL=\
postgresql://buddy:buddy-local-dev@127.0.0.1:54331/dungeonbuddy_application_state

# 3. Birth the schema explicitly (no migrate-on-start)
uv run python scripts/bootstrap_local_play.py apply

# 4. Observe: reachable, at head, fingerprint computed — not READY
uv run python scripts/application_state_authority.py check
# OBSERVED. Capture the fingerprint JSON if you will need a later READY check:
uv run python scripts/application_state_authority.py fingerprint --out out/application_state/birth.fingerprint.json
```

## Routine backup

```bash
uv run python scripts/application_state_authority.py backup \
  --source-dsn "$DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL" \
  --out out/application_state/authority-backup-$(date -u +%Y%m%dT%H%M%SZ).dump
```

Produces the custom-format dump plus `.sha256` and `.fingerprint.json` sidecars. The command fingerprints the source before and after the dump; if the source changed mid-backup it fails — recapture, never claim a stale dump is current authority. Restore will refuse the dump if either sidecar is missing or the dump bytes no longer match the SHA-256 sidecar.

## Restore into a second clean target (recovery witness)

```bash
# 1. Create a clean target database on the durable server
PGPASSWORD=buddy-local-dev psql -h 127.0.0.1 -p 54331 -U buddy -d postgres \
  -c 'CREATE DATABASE dungeonbuddy_application_state_witness'

# 2. Restore: SHA-256 sidecar is verified before replay; fingerprint sidecar is the READY bar
uv run python scripts/application_state_authority.py restore \
  --target-dsn postgresql://buddy:buddy-local-dev@127.0.0.1:54331/dungeonbuddy_application_state_witness \
  --backup out/application_state/<dump>.dump \
  --expect-fingerprint out/application_state/<dump>.dump.fingerprint.json
# READY exit 0 only when dump digest matches and restored fingerprint matches expected;
# NOT_READY exit 2 with per-domain mismatches; missing/mismatched SHA-256 refuses restore

# 3. Drop the witness only after the proof is recorded
PGPASSWORD=buddy-local-dev psql -h 127.0.0.1 -p 54331 -U buddy -d postgres \
  -c 'DROP DATABASE dungeonbuddy_application_state_witness'
```

Restore refuses a target that already contains APP-STATE schemas — destructive restore over a live authority is not a supported operation. To re-birth intentionally, drop the database explicitly first (an operator decision, never a tool default).

## Container replacement survival

```bash
# Record the live fingerprint before recreate, then require it after:
uv run python scripts/application_state_authority.py fingerprint \
  --out out/application_state/pre-recreate.fingerprint.json
docker compose -f compose.postgres.app-state.yml up -d --force-recreate
uv run python scripts/application_state_authority.py check \
  --expect-fingerprint out/application_state/pre-recreate.fingerprint.json
# READY only if the live fingerprint still matches; OBSERVED check is not enough
```

## Switching the runtime to the durable authority

Set `DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL` in `.env` to the durable coordinates and restart the Buddy API. The preflight (`scripts/bootstrap_local_play.py check`) reports redacted coordinates and fails closed if the authority is unreachable or behind head. After a switch, run `check --expect-fingerprint` against the pre-switch fingerprint JSON — a bare `check` is OBSERVED only.

## Failure modes and responses

| Symptom | Meaning | Response |
| --- | --- | --- |
| `check` exits 0, OBSERVED | reachable and at head; not a READY claim | capture `--expect-fingerprint` before treating it as recovered |
| `check` exits 2, unreachable | authority container down or wrong DSN | start the compose service; verify coordinates |
| `check` exits 2, behind head | schema not migrated | explicit `apply` with the target DSN configured |
| `check` / `restore` exits 2, NOT_READY | live fingerprint does not match expected | do not bless the target; investigate per-domain mismatch output |
| `restore` refuses SHA-256 mismatch / missing sidecar | dump bytes are unverified or tampered | recapture; never restore an unverified dump |
| `restore` refuses non-empty target | target already holds APP-STATE | use a second clean target; destructive restore is out of scope |
| `backup` reports source changed | writes during dump | recapture; never claim a stale dump |
| volume deleted (`down -v`) | authority destroyed | restore the newest external backup into a re-born empty database, then `check --expect-fingerprint` |

## History

- **2026-09-07:** the previous APP-STATE database lived on the tmpfs dev server (54329) and was destroyed by an ordinary container stop before any backup existed. This runbook and the durable substrate are the corrective authority. Repopulation of C1/C2 content through supported product seams is the Stage 2B successor.
