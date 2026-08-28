# Runbook: Local Play dogfood

Make merged Beat-first Play reachable from a normal developer checkout.

This is the supported **Play dogfood gateway**. It does not migrate on FastAPI
boot, does not import leftover files on boot, and does not reuse the World Graph
database as Buddy application state.

## What this proves

```text
configured safe Buddy application-state DSN
→ explicit bootstrap
→ ordinary uvicorn + Vite
→ /play
→ choose or start an exact Run
→ BF3A Current Moment cockpit
```

## Prerequisites

- PostgreSQL is already running.
- A **separate** Buddy logical database name is available. Recommended:

  `dungeonbuddy_application_state`

- Do **not** point Buddy application state at `dungeonmind`,
  `dungeonmind_cutover_live`, or the configured World Graph database.
- The same PostgreSQL **server** may host both databases.

## First setup / after application-state schema changes

1. Configure repo `.env` or `.env.development` with a safe Buddy DSN:

   ```bash
   DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL=postgresql://USER:PASSWORD@127.0.0.1:54329/dungeonbuddy_application_state
   ```

2. Run the explicit bootstrap:

   ```bash
   uv run python scripts/bootstrap_local_play.py apply
   ```

That command may create the standard Buddy logical database when it is missing,
upgrade it to Alembic head, and adopt leftover legacy Runbooks. It never starts
a Play Run and never seeds a fake Runbook.

Inspect without mutating:

```bash
uv run python scripts/bootstrap_local_play.py check
```

Do not run bootstrap on every server restart. Re-run `apply` after application-state
schema changes, or when `check` reports `NEEDS BOOTSTRAP`.

## Normal runtime

Terminal 1:

```bash
uv run uvicorn apps.live_control_server.main:app --reload
```

Terminal 2:

```bash
pnpm --dir apps/live-control-ui dev
```

Then open `http://127.0.0.1:5173/`, choose **Play**, or go to
`http://127.0.0.1:5173/play`.

## Expected Play path

- Existing Runs load from application state, or show that none exist.
- Start a Run lists active committed Runbooks.
- If none exist, **Create blank Runbook** asks for a campaign (or uses a valid
  World Graph focus) and commits one Untitled Beat. It does not start a Run.
- Start exact Run admits v2 native READY.
- A blank Runbook opens BF3A in Beat-only Current Moment (`current Scene = null`).
- Make Scene Current, reload, and the same Scene resumes.

Zero leftover file-backed Runbooks is a truthful bootstrap `NOT READY`. Create
the first Playable document in Play; do not ask bootstrap to invent one.

## Readiness results

| Result | Meaning |
| --- | --- |
| `NEEDS CONFIGURATION` | Set `DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL` to a separate Buddy database |
| `NEEDS BOOTSTRAP` | Run `apply` (database missing, schema behind, or leftover Runbooks not adopted) |
| `READY` | At least one active committed Runbook can be started |
| `NOT READY` | Application state is at head, but no committed Runbook exists. Nothing was faked. |
| `BLOCKED` / `UNAVAILABLE` | Isolation failed, import conflicted, or PostgreSQL did not reply |

## Forbidden shortcuts

- Do not start FastAPI hoping it will create the database or migrate.
- Do not reuse the World Graph DSN.
- Do not run `scripts/live_dogfood_check.py` for this path. That script is the
  statblock/combat session-dir checker.

## Related

- Application-state architecture: `Docs/Design/ARCHITECTURE-application-state-layer.md`
- Current Moment cockpit: `Docs/Design/DESIGN-play-current-moment-cockpit.md`
- Implementation handoff: `Docs/Plans/HANDOFF-PLAY-SURFACE-local-dogfood-bootstrap.md`
