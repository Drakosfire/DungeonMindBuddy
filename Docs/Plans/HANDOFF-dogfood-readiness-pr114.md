# HANDOFF — Dogfood readiness PR114

**Created:** 2026-06-10  
**Repo:** `Drakosfire/DungeonMindBuddy`  
**Target base branch:** `main`  
**Suggested next branch:** `codex/dogfood-readiness-pr114`  
**Depends on:** PR #113 / `21bc8231ec7eb505e68dfa9de453869099d73c99` — Add Combat Roster tracker  
**Primary designs:**
- `Docs/Design/DESIGN-command-board-combat-statblock-generator-integration.md`
- `Docs/Design/DESIGN-statblock-lifecycle-agentic-workbench.md`

**Mode:** Dogfood readiness, environment hardening, reset/runbook tooling. Do not add new product surface area unless it directly supports manual testing.

---

## 0. Copyable task prompt

```markdown
You are implementing Dogfood Readiness PR114 in `Drakosfire/DungeonMindBuddy`.

Read first:

- `Docs/Plans/HANDOFF-dogfood-readiness-pr114.md`
- `Docs/Plans/HANDOFF-combat-roster-tracker-pr113.md`
- `Docs/Plans/HANDOFF-statblock-add-to-combat-pr112.md`
- `Docs/Design/DESIGN-command-board-combat-statblock-generator-integration.md`
- `apps/live_control_server/services/combat_state.py`
- `apps/live-control-ui/package.json`
- `apps/live-control-ui/tsconfig.node.json`

Goal: make the now-complete statblock → corpus → retrieval → combat lifecycle ready for manual dogfooding.

PR113 completed the first table-facing combat loop over `combat/current_combat.json`. PR114 should not add new gameplay features. It should provide a safe, repeatable manual test path:

- a dogfood runbook/checklist;
- clear local startup commands;
- safe reset/cleanup tooling for live-session dogfood artifacts;
- optional smoke/check script for environment and endpoint readiness;
- fix or document known environment blockers, especially the UI build `@types/node` issue;
- document how to run focused backend/frontend checks before dogfood;
- produce a manual dogfood results template.

Do not add generation behavior, combat features, corpus write behavior, retrieval behavior, planning tasks, or terrain/map systems. This PR is about making the existing flow testable and repeatable.
```

---

## 1. Re-anchor

Current ladder:

```text
Producer API live ✅
Buddy v2 seam ✅
Lifecycle command facade ✅
Read-only Workbench ✅
Interactive Workbench ✅
Persistent non-corpus draft storage ✅
Corpus promotion preview ✅
Confirmed corpus write ✅
Retrieval activation/verification ✅
Statblock View ✅
Add to combat ✅
Combat Roster / Tracker ✅
Planning Mode generation tasks ❌
```

We have reached **local alpha dogfood threshold**.

The feature spine now supports:

```text
Generate/render draft
→ store draft
→ preview corpus promotion
→ confirmed corpus write
→ activate/verify retrieval
→ view in Statblock View
→ add to current combat
→ manage in Combat Roster
```

PR114 should make that path executable by a human without improvising environment setup or risking stale state.

---

## 2. Product intent

The first dogfood session should answer:

```text
Can a GM manually walk the full generated-statblock lifecycle and use the result in combat without code-agent assistance?
```

PR114 should reduce uncertainty around:

- local server startup;
- UI startup/build;
- test dependency setup;
- hidden module enablement;
- dogfood state reset;
- generated corpus files from prior runs;
- current combat state leftovers;
- what exactly to click/check;
- how to record friction and bugs.

This is not a feature PR. It is a readiness PR.

---

## 3. Design boundary

### PR114 does

- add a dogfood runbook;
- add a manual lifecycle checklist;
- add a results/notes template;
- add safe reset/cleanup tooling for dogfood artifacts;
- add optional local readiness/smoke checks;
- fix the known UI build type dependency if appropriate;
- clarify backend dependency setup for `python-dotenv` / `uv`;
- document exact commands for backend, frontend, focused tests, and manual cURL smoke;
- ensure reset scripts are dry-run friendly and scoped to the live session dir.

### PR114 does not

- add new statblock generation behavior;
- replace the mock generator;
- add real DungeonMindServer provider calls;
- alter corpus writer policy;
- alter retrieval activation semantics;
- add combat operations;
- improve Combat Roster UX beyond test-readiness bugs;
- add planning-mode task integration;
- create map/terrain systems;
- change campaign canon content.

---

## 4. Known blockers / caveats to resolve or document

### 4.1 UI build `@types/node` issue

`apps/live-control-ui/tsconfig.node.json` declares:

```json
"types": ["node"]
```

But `apps/live-control-ui/package.json` currently does not include `@types/node` in dev dependencies.

PR113 repeatedly documented:

```text
npm run build blocked by missing TypeScript type definitions (@types/node)
```

PR114 should fix this if possible:

```json
"@types/node": "<compatible version>"
```

Recommended: add `@types/node` to `devDependencies` and update the lockfile if the repo has one.

After fix, run:

```bash
cd apps/live-control-ui
npm run build
```

If the build still fails for unrelated reasons, document the new failure precisely in the PR body.

### 4.2 Backend `python-dotenv` issue

`pyproject.toml` already includes:

```text
python-dotenv>=1.2.2
```

But PR113 reported route/integration tests blocked by `ModuleNotFoundError` / missing runtime dependency.

PR114 should not add duplicate dependencies blindly. Instead:

- add the dependency/setup check to the runbook;
- prefer `uv run ...` over bare `python ...` or bare `pytest ...`;
- add a readiness command:

```bash
uv run python -c "import dotenv; import fastapi; import uvicorn; print('backend deps ok')"
```

If there is a `uv.lock`, update only if needed. If the environment still fails under `uv run`, investigate and fix the project dependency setup.

---

## 5. Files to add/update

### 5.1 Add dogfood runbook

Create:

```text
Docs/Runbooks/RUNBOOK-statblock-combat-dogfood.md
```

If `Docs/Runbooks/` does not exist, create it.

Runbook should include:

- purpose;
- prerequisites;
- environment setup;
- backend startup;
- frontend startup;
- reset steps;
- full manual checklist;
- expected artifacts/files;
- known caveats;
- troubleshooting section;
- results template link or inline section.

### 5.2 Add results template

Create either:

```text
Docs/Runbooks/TEMPLATE-statblock-combat-dogfood-results.md
```

or include a copyable template at the bottom of the runbook.

Preference: separate template file so each dogfood run can copy it.

### 5.3 Add safe reset script

Create:

```text
scripts/live_dogfood_reset.py
```

If the repo does not have `scripts/`, create it.

Purpose:

- safely remove dogfood-created live session artifacts;
- default to dry-run unless `--apply` is passed;
- require explicit live session dir via `--session-dir` or `DUNGEONMIND_LIVE_SESSION_DIR`;
- refuse to operate outside a path that looks like a live session dir;
- print every path it would remove;
- never delete arbitrary corpus directories.

Recommended reset targets:

```text
<session_dir>/statblock_drafts/
<session_dir>/statblock_retrieval/
<session_dir>/combat/current_combat.json
```

Optional target:

```text
<session_dir>/combat/
```

but only if empty after deleting current combat.

Generated corpus files are trickier. Prefer **not** deleting corpus files automatically in the first script. Instead:

- list generated corpus files that match `Longmont Campaign/Campaign 2/Statblocks/generated/*.md`;
- include `--purge-generated-corpus` only if implemented safely;
- require both `--apply` and `--purge-generated-corpus` for corpus deletion;
- never delete outside `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Statblocks/generated/`.

### 5.4 Optional readiness script

Create if small:

```text
scripts/live_dogfood_check.py
```

Purpose:

- print resolved session dir;
- verify backend imports;
- verify expected live session files exist;
- verify UI dependency caveat status if possible;
- print expected startup commands;
- optionally perform HTTP checks if `--server-url` is provided.

Keep it small. Do not build a full orchestration runner.

If this feels too large, skip this script and keep checks in the runbook.

### 5.5 Update package metadata

Update:

```text
apps/live-control-ui/package.json
```

Add:

```json
"@types/node": "..."
```

Update lockfile if present.

### 5.6 Optional docs index

If there is a docs index or README section for live-control, add a short pointer to the runbook. Do not spend time reorganizing docs.

---

## 6. Runbook content requirements

The runbook should be operationally precise.

### 6.1 Prerequisites

Include:

```bash
uv sync
uv run python -c "import dotenv; import fastapi; import uvicorn; print('backend deps ok')"

cd apps/live-control-ui
npm install
npm run build
```

If `npm run build` remains blocked, explain the workaround:

```bash
npm test -- --run src/api/liveApi.test.ts src/surface/modules/CombatRosterModule.test.tsx
npm run dev
```

### 6.2 Backend startup

Include exact command:

```bash
export DUNGEONMIND_LIVE_SESSION_DIR=evals/c2_live_prep/live/session_22
uv run uvicorn apps.live_control_server.main:app --reload
```

Mention expected URL:

```text
http://127.0.0.1:8000
```

### 6.3 Frontend startup

Include:

```bash
cd apps/live-control-ui
npm run dev
```

Mention expected URL:

```text
http://127.0.0.1:5173
```

If Vite port differs, use whatever Vite prints.

### 6.4 Reset command

Include dry-run and apply examples:

```bash
uv run python scripts/live_dogfood_reset.py \
  --session-dir evals/c2_live_prep/live/session_22

uv run python scripts/live_dogfood_reset.py \
  --session-dir evals/c2_live_prep/live/session_22 \
  --apply
```

Corpus purge, only if implemented:

```bash
uv run python scripts/live_dogfood_reset.py \
  --session-dir evals/c2_live_prep/live/session_22 \
  --apply \
  --purge-generated-corpus
```

### 6.5 Module enablement

The modules are hidden/disabled by default. Document how to enable or confirm these modules in the command board:

```text
Statblock Workbench
Statblock View
Combat Roster
```

If the UI does not have an obvious module-enable affordance, document the current workaround by editing the live surface layout file. Keep this explicit and safe.

### 6.6 Full lifecycle checklist

Include these checks as a checkbox list:

```text
[ ] Workbench loads.
[ ] Generate/render draft.
[ ] Store draft.
[ ] Reload stored draft.
[ ] Preview corpus promotion.
[ ] Prepare corpus write.
[ ] Confirm corpus write.
[ ] Generated markdown file exists.
[ ] Activate retrieval.
[ ] Verify retrieval admits generated statblock evidence.
[ ] Statblock View lists the generated statblock.
[ ] Detail view reads corpus markdown.
[ ] Add to current combat.
[ ] Combat Roster shows entity.
[ ] Sort initiative.
[ ] Set active actor.
[ ] Advance/rewind turn.
[ ] Damage/heal/temp HP.
[ ] Edit notes/conditions.
[ ] Mark defeated.
[ ] Refresh browser and confirm state persists.
[ ] Restart backend and confirm state persists.
```

### 6.7 File expectations

Document expected files created during dogfood:

```text
<session_dir>/statblock_drafts/<artifact_id>.json
<session_dir>/statblock_retrieval/generated_statblocks_manifest.json
<session_dir>/combat/current_combat.json
corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Statblocks/generated/<slug>.md
```

### 6.8 Known limitations

Document clearly:

- Workbench generation may still be mock-backed unless a later PR swapped in live DungeonMindServer provider calls.
- Statblock View reads generated corpus-backed statblocks only.
- Combat Roster is one current combat, not multi-encounter management.
- Combat Roster does not yet provide statblock drilldown from rows.
- No map/terrain/positioning.
- No planning-mode task integration yet.

---

## 7. Reset script behavior

### 7.1 CLI contract

Suggested CLI:

```bash
uv run python scripts/live_dogfood_reset.py --session-dir evals/c2_live_prep/live/session_22
uv run python scripts/live_dogfood_reset.py --session-dir evals/c2_live_prep/live/session_22 --apply
uv run python scripts/live_dogfood_reset.py --session-dir evals/c2_live_prep/live/session_22 --apply --purge-generated-corpus
```

Arguments:

```text
--session-dir PATH              required unless DUNGEONMIND_LIVE_SESSION_DIR is set
--apply                         actually delete; without it, dry run
--purge-generated-corpus         also remove generated statblock markdown files under the narrow generated folder
--repo-root PATH                optional; default current working directory
```

### 7.2 Safety checks

The script must:

- resolve paths;
- confirm session dir exists;
- confirm `live_packet.json` exists in session dir;
- refuse `/`, home dir, repo root, or `evals/` parent as session dir;
- refuse corpus deletion unless generated corpus path is exactly under:

```text
corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Statblocks/generated/
```

- print all planned deletions;
- exit nonzero on unsafe path;
- default to dry run.

### 7.3 Tests

Add:

```text
tests/test_live_dogfood_reset.py
```

Test:

- dry run does not delete;
- `--apply` deletes only session dogfood artifacts;
- unsafe session dir refused;
- corpus purge requires explicit flag and stays in generated path;
- live packet remains untouched.

If script test plumbing is too heavy, test helper functions directly.

---

## 8. Readiness checks / smoke script

Optional script:

```text
scripts/live_dogfood_check.py
```

If implemented, keep it read-only.

Suggested checks:

```text
backend import check
session dir exists
live_packet.json exists
surface_layout.json exists
expected modules known in bootstrap
current dogfood artifact paths found/missing
optional HTTP GET /api/live/combat/current if --server-url provided
```

Do not perform lifecycle mutations in this script.

---

## 9. Tests to run in PR114

Backend:

```bash
uv run python -c "import dotenv; import fastapi; import uvicorn; print('backend deps ok')"

uv run pytest \
  tests/test_live_dogfood_reset.py \
  tests/test_combat_roster_operations.py \
  tests/test_statblock_add_to_combat.py \
  tests/test_statblock_view.py \
  -q
```

Frontend:

```bash
cd apps/live-control-ui
npm test -- \
  src/api/liveApi.test.ts \
  src/surface/modules/CombatRosterModule.test.tsx \
  src/surface/modules/StatblockViewModule.test.tsx \
  src/surface/modules/StatblockWorkbenchModule.test.tsx

npm run build
```

Lint/format:

```bash
uv run ruff check \
  scripts/live_dogfood_reset.py \
  scripts/live_dogfood_check.py \
  tests/test_live_dogfood_reset.py

git diff --check
```

Adjust if optional check script is not added.

---

## 10. Acceptance criteria

The PR is ready when:

- Dogfood runbook exists.
- Dogfood results template exists or is included in the runbook.
- Safe reset script exists and defaults to dry-run.
- Reset script only touches approved dogfood artifacts.
- Reset script refuses unsafe paths.
- UI build `@types/node` issue is fixed or precisely documented with an explicit reason.
- Backend dependency check is documented and works under `uv run`.
- Manual lifecycle checklist covers Workbench → corpus → retrieval → Statblock View → Add to Combat → Combat Roster.
- Expected artifact files are documented.
- Known limitations are documented.
- Focused reset script tests pass.
- No new gameplay features are introduced.

---

## 11. Suggested PR description

```markdown
### Motivation

PR113 completed the first end-to-end generated-statblock lifecycle through Combat Roster. Before adding more product surface, this PR makes the flow safe and repeatable for manual dogfooding.

### Description

- Added a statblock/combat dogfood runbook with local startup commands, reset instructions, module enablement, full manual lifecycle checklist, expected files, caveats, and troubleshooting.
- Added a dogfood results template for recording manual test findings.
- Added a safe dogfood reset script that defaults to dry-run and only removes approved live-session dogfood artifacts.
- Added tests for reset-script safety and deletion scope.
- Fixed or documented the UI `@types/node` build blocker.
- Documented backend dependency/readiness checks using `uv run`.
- Kept generation, corpus, retrieval, combat feature work, terrain, and planning-mode tasks out of scope.

### Testing

- `uv run python -c "import dotenv; import fastapi; import uvicorn; print('backend deps ok')"`
- `uv run pytest tests/test_live_dogfood_reset.py tests/test_combat_roster_operations.py tests/test_statblock_add_to_combat.py tests/test_statblock_view.py -q`
- `cd apps/live-control-ui && npm test -- src/api/liveApi.test.ts src/surface/modules/CombatRosterModule.test.tsx src/surface/modules/StatblockViewModule.test.tsx src/surface/modules/StatblockWorkbenchModule.test.tsx`
- `cd apps/live-control-ui && npm run build`
- `uv run ruff check scripts/live_dogfood_reset.py tests/test_live_dogfood_reset.py`
- `git diff --check`
```

---

## 12. Design reminder

PR114 is a readiness/hardening slice.

After PR114, we should perform the first actual manual dogfood run before choosing the next feature PR.

Likely next steps after dogfood:

```text
PR115 — Fix dogfood findings / operator friction
or
PR115 — Statblock drilldown from Combat Roster rows
or
PR115 — Real DungeonMindServer provider integration into Workbench commands
```

Do not choose that before the dogfood run produces evidence.
