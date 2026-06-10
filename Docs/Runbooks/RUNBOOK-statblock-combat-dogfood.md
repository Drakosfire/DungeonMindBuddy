# Runbook: Statblock → Corpus → Retrieval → Combat Dogfood

## Purpose

This runbook makes the completed local alpha lifecycle safe, repeatable, and testable by a human GM:

```text
Workbench → generate/render draft → store draft → preview corpus promotion → confirmed corpus write
→ activate/verify retrieval → Statblock View → Add to Combat → Combat Roster
→ refresh/restart persistence check
```

Use it to answer: can a GM manually walk the full generated-statblock lifecycle and use the result in combat without code-agent assistance?

## Scope and non-goals

This is a dogfood-readiness procedure. It does not validate new statblock generation behavior, real DungeonMindServer provider integration, planning-mode tasks, multi-encounter combat management, or map/terrain systems.

## Prerequisites

Run from the repository root unless a command says otherwise.

```bash
uv sync
uv run python -c "import dotenv; import fastapi; import uvicorn; print('backend deps ok')"
```

Install and build the UI:

```bash
cd apps/live-control-ui
npm install
npm run build
cd ../..
```

The UI package declares `@types/node` for Vite config/editor parity, and `tsconfig.node.json` also includes a tiny local `vite.config.env.d.ts` declaration so the build is not blocked by a missing installed Node type package. If package installation cannot reach the npm registry, record the exact install error in the dogfood results and use the focused tests plus dev server as the fallback:

```bash
cd apps/live-control-ui
npm test -- --run src/api/liveApi.test.ts src/surface/modules/CombatRosterModule.test.tsx src/surface/modules/StatblockViewModule.test.tsx src/surface/modules/StatblockWorkbenchModule.test.tsx
npm run dev
```

## Optional readiness check

The read-only checker prints backend import status, live-session file status, module enablement, UI dependency status, and startup commands:

```bash
uv run python scripts/live_dogfood_check.py \
  --session-dir evals/c2_live_prep/live/session_22
```

If the backend is already running, add the HTTP check:

```bash
uv run python scripts/live_dogfood_check.py \
  --session-dir evals/c2_live_prep/live/session_22 \
  --server-url http://127.0.0.1:8000
```

## Reset before a dogfood run

The reset script defaults to dry-run and only targets dogfood-created live-session artifacts:

- `<session_dir>/statblock_drafts/`
- `<session_dir>/statblock_retrieval/`
- `<session_dir>/combat/current_combat.json`

Dry-run first:

```bash
uv run python scripts/live_dogfood_reset.py \
  --session-dir evals/c2_live_prep/live/session_22
```

Apply only after reviewing the planned deletions:

```bash
uv run python scripts/live_dogfood_reset.py \
  --session-dir evals/c2_live_prep/live/session_22 \
  --apply
```

Generated corpus files are not deleted by default. Treat generated corpus purge as a high-intent cleanup command for throwaway dogfood artifacts only. If a run must also remove generated statblock markdown, use the narrow corpus purge flag plus the second confirmation flag. It only applies to `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Statblocks/generated/*.md`, prints the purge count, and still lists each planned deletion before applying:

```bash
uv run python scripts/live_dogfood_reset.py \
  --session-dir evals/c2_live_prep/live/session_22 \
  --apply \
  --purge-generated-corpus \
  --yes-delete-generated-corpus
```

The script refuses unsafe paths such as `/`, the home directory, the repo root, `evals/`, and live-session parent directories. It also requires `live_packet.json` inside the session directory.

## Backend startup

Use the live Session 22 fixture unless intentionally testing another live session:

```bash
export DUNGEONMIND_LIVE_SESSION_DIR=evals/c2_live_prep/live/session_22
uv run uvicorn apps.live_control_server.main:app --reload
```

Expected backend URL:

```text
http://127.0.0.1:8000
```

Optional manual smoke after startup:

```bash
curl http://127.0.0.1:8000/api/live/combat/current
```

## Frontend startup

In a second terminal:

```bash
cd apps/live-control-ui
npm run dev
```

Expected frontend URL:

```text
http://127.0.0.1:5173
```

If Vite selects a different port, use the URL printed by Vite.

## Module enablement

The dogfood modules are present in `evals/c2_live_prep/live/session_22/surface_layout.json` but are disabled by default:

- `statblock_workbench` — Statblock Workbench
- `statblock_view` — Statblock View
- `combat_roster` — Combat Roster

Before dogfood, enable those module rows by changing each row's `enabled` field to `true` in the live session layout file. Leave unrelated modules unchanged. If the UI later provides a module-enable affordance, prefer the UI affordance and record that in the results.

## Full manual lifecycle checklist

Copy `Docs/Runbooks/TEMPLATE-statblock-combat-dogfood-results.md` for each run, then work through this checklist:

- [ ] Workbench loads.
- [ ] Generate/render draft.
- [ ] Store draft.
- [ ] Reload stored draft.
- [ ] Preview corpus promotion.
- [ ] Prepare corpus write.
- [ ] Confirm corpus write.
- [ ] Generated markdown file exists.
- [ ] Activate retrieval.
- [ ] Verify retrieval admits generated statblock evidence.
- [ ] Statblock View lists the generated statblock.
- [ ] Detail view reads corpus markdown.
- [ ] Add to current combat.
- [ ] Combat Roster shows entity.
- [ ] Sort initiative.
- [ ] Set active actor.
- [ ] Advance/rewind turn.
- [ ] Damage/heal/temp HP.
- [ ] Edit notes/conditions.
- [ ] Mark defeated.
- [ ] Refresh browser and confirm state persists.
- [ ] Restart backend and confirm state persists.

## Expected files created during dogfood

```text
<session_dir>/statblock_drafts/<artifact_id>.json
<session_dir>/statblock_retrieval/generated_statblocks_manifest.json
<session_dir>/combat/current_combat.json
corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Statblocks/generated/<slug>.md
```

## Focused checks before or after dogfood

Backend checks:

```bash
uv run python -c "import dotenv; import fastapi; import uvicorn; print('backend deps ok')"
uv run pytest \
  tests/test_live_dogfood_reset.py \
  tests/test_combat_roster_operations.py \
  tests/test_statblock_add_to_combat.py \
  tests/test_statblock_view.py \
  -q
```

Frontend checks:

```bash
cd apps/live-control-ui
npm test -- \
  src/api/liveApi.test.ts \
  src/surface/modules/CombatRosterModule.test.tsx \
  src/surface/modules/StatblockViewModule.test.tsx \
  src/surface/modules/StatblockWorkbenchModule.test.tsx
npm run build
```

Lint and whitespace checks:

```bash
uv run ruff check \
  scripts/live_dogfood_reset.py \
  scripts/live_dogfood_check.py \
  tests/test_live_dogfood_reset.py
git diff --check
```

## Known limitations

- Workbench generation may still be mock-backed unless a later PR swaps in live DungeonMindServer provider calls. Mark each dogfood run as validating lifecycle mechanics only, real DungeonMindServer generation, or both.
- Statblock View reads generated corpus-backed statblocks only.
- Combat Roster manages one current combat state, not multiple encounters.
- Combat Roster does not yet provide statblock drilldown from rows.
- There is no map, terrain, or positioning support in this lifecycle.
- There is no planning-mode task integration yet.

## Troubleshooting

### Backend import failures

Prefer `uv run ...` commands so dependencies come from the project environment. Re-run `uv sync` if `dotenv`, `fastapi`, or `uvicorn` cannot be imported.

### Empty or missing modules in the UI

Confirm the backend is using the intended session directory:

```bash
echo "$DUNGEONMIND_LIVE_SESSION_DIR"
```

Then confirm the three dogfood module IDs exist in `surface_layout.json` and are enabled.

### Stale draft, retrieval, or combat state

Run reset in dry-run mode, review the planned deletions, then rerun with `--apply` if the targets are correct.

### UI build failure

Run `npm install` inside `apps/live-control-ui`, then rerun `npm run build`. If registry access is blocked, record the npm error and run the focused Vitest command plus `npm run dev` for manual dogfood.

## Results template

Use `Docs/Runbooks/TEMPLATE-statblock-combat-dogfood-results.md` for each dogfood run. Store completed results near the plan or runbook chosen by the current project workflow.
