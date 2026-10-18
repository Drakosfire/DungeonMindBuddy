# DOGFOOD Play blank welcome

Status: ACTIVE

Branch: `codex/play-empty-welcome` rebased onto `origin/main@3a890b9e`

Checkout: `/tmp/dmb-play-empty-welcome-reanchor`

Topology: parallel-independent from Build PR #1183 and Plan PR #1188. This slice owns Play's first-use chooser presentation only.

## Mission

Make Play's no-run / no-Runbook state feel like a deliberate beginning. Explain how to start from a saved Runbook or create a blank one, remove duplicate empty-state copy, and retain the existing exact-run creation and selection authority.

## Write lease

- `apps/live-control-ui/src/playSurface/PlaySurfacePage.tsx`
- `apps/live-control-ui/src/playSurface/StartRunPanel.tsx`
- `apps/live-control-ui/src/playSurface/playSurface.css`
- `apps/live-control-ui/src/playSurface/PlaySurfacePage.test.tsx`
- `apps/live-control-ui/src/playSurface/StartRunPanel.test.tsx`
- This handoff

No changes to Run identity, Run creation semantics, API contracts, server, database, Build, Plan, Ingest, shared app shell, or 5876. Keep 5202 unchanged; rendered checks use an isolated current-main preview.

## Invariants and acceptance

- A verified empty Run list is visually distinct from loading, unavailable, recovery-pending, and exact-Run failure states.
- A first-time user sees a clear path to select a saved Runbook or create a blank Runbook; existing creation and exact-revision gates remain unchanged.
- Empty Runs and empty Runbooks are explained once, without repeated status copy.
- The experience is responsive, keyboard accessible, and visually belongs to the Play surface.
- Verify focused Play tests, UI TypeScript, production build, `git diff --check`, and the exact cumulative diff.
- Keep 5876 and 5202 untouched. Do not claim visual acceptance without inspecting a current-main preview that includes this branch.

## Initial verification before isolated fixture — 2026-10-15

The Play focused page and start-panel suites pass 48 tests, and the app
TypeScript check passes. Rendered acceptance remains pending in the integrated
current-main preview; the Build-only 5204 preview does not include this branch,
and Elderwyld already has saved Runs, so a verified empty Run state still needs
an isolated empty-world fixture or a safe UI-only fixture.

## Integrated preview acceptance — 2026-10-15

The integrated local preview on 5205 includes `main@3a890b9e` and current heads of PRs #1183, #1188, #1190, and #1191. Shared navigation from Build opened the Play surface. Elderwyld already has saved Runs, so the no-run welcome could not be exercised against live World state without creating/changing data; at this point this remained a rendered acceptance gap. The first-run state is covered by the focused Play page and Start Run Panel tests (48 passed), and TypeScript plus the combined production build passed. No Runbook or Run was created; 5202 and 5876 were not modified. The synthetic fixture below closes the no-run rendering gap without touching World data.

## Local-only empty-Run visual fixture lease amendment — 2026-10-15

PRIME authorizes a bounded synthetic fixture to close the no-run rendered acceptance gap without touching a real World or application database. The fixture is visual-test-only; it must not add a production query parameter, endpoint, fallback, or runtime behavior.

The exclusive lease is amended to include these exact paths before they are edited:

- `apps/live-control-ui/src/playSurface/PlayEmptyWelcome.stories.tsx` — Ladle story that renders the real Play surface against a synthetic World with no Runs or Runbooks; its local fetch adapter returns fixture GET responses and permits only the production read-only `POST /api/live/world-graph/managed-projection` query. Every other non-GET request is rejected and logged as a write attempt.
- `apps/live-control-ui/tests/ui-visual.pw.ts` — Playwright rendered acceptance for the fixture at desktop (1280×800) and narrow (390×844), including a check that the fixture issues no write requests.
- `apps/live-control-ui/tests/ui-visual-snapshots/play-empty-welcome-desktop.png` — reviewed desktop baseline.
- `apps/live-control-ui/tests/ui-visual-snapshots/play-empty-welcome-narrow.png` — reviewed narrow baseline.

The synthetic World identity and responses must not resolve to Elderwyld or use an operator database. Verify the story’s network boundary before screenshot capture. The allowed POST exists because the production graph status hook uses POST for this non-mutating read; no other server/database/API contract or Play behavior changes are authorized by this amendment. Keep 5202 and existing World data untouched.

## Empty-Run rendered acceptance — 2026-10-15

The synthetic Ladle story renders the real Play chooser with a verified empty Run and Runbook list. Its fetch boundary returns fixture GET data, permits only the read-only managed-projection POST, and rejects/logs every other non-GET request. The desktop 1280×800 and narrow 390×844 Playwright screenshots were reviewed; the test confirms no write requests, no horizontal overflow, and the Buddy launcher does not cover the narrow first-run prompt. The welcome no longer repeats the generic “Open one exact durable Run” instruction above it.

Verification on the Play lane: 48 focused tests pass, UI TypeScript passes, the production Vite build passes with its existing large-chunk warning, Ladle builds, the isolated desktop/narrow visual test passes, and `git diff --check` passes. The integration visual check remains intentionally synthetic; it proves the empty Play projection without creating a Run/Runbook or writing to a real World. Live Save/reopen and conversation checks remain blocked by the preview’s rejected local authorization. 5202 and 5876 remain unchanged.
