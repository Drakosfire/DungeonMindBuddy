# HANDOFF — Statblock Workbench read-only PR3

**Created:** 2026-06-09  
**Repo:** `Drakosfire/DungeonMindBuddy`  
**Target base branch:** `main`  
**Suggested next branch:** `codex/statblock-workbench-readonly-pr3`  
**Depends on:** PR #104 / `254548cef5171d7d1b0d41a05f680f6fc93c1727` — Add statblock lifecycle command facade and developer smoke harness  
**Primary design:** `Docs/Design/DESIGN-statblock-lifecycle-agentic-workbench.md`  
**Previous handoffs:**
- `Docs/Plans/HANDOFF-statblock-lifecycle-seam-pr1.md`
- `Docs/Plans/HANDOFF-statblock-lifecycle-command-smoke-pr2.md`
**Production report:** `Docs/Plans/REPORT-to-design-agent-statblock-v2-production-deploy-2026-06-09.md`  
**Mode:** First visible Workbench slice. Build a read-only review skeleton over `StatblockDraftArtifact` using mock/service output. Do not persist, promote, ingest, or mutate combat.

---

## 0. Copyable task prompt

```markdown
You are implementing Statblock Workbench PR3 in `Drakosfire/DungeonMindBuddy`.

Read first:

- `Docs/Plans/HANDOFF-statblock-workbench-readonly-pr3.md`
- `Docs/Design/DESIGN-statblock-lifecycle-agentic-workbench.md`
- `Docs/Plans/HANDOFF-statblock-lifecycle-command-smoke-pr2.md`
- `Docs/Plans/REPORT-to-design-agent-statblock-v2-production-deploy-2026-06-09.md`

Goal: make statblock draft artifacts visible for the first time through a read-only Workbench/review skeleton.

Use the PR #104 command facade and mock provider first. Add a small server-side live-control endpoint that returns a `StatblockDraftArtifact` generated/rendered through `StatblockLifecycleService(MockStatBlockGeneratorProvider)` and a React surface module that displays the artifact's markdown, combat defaults, warnings, provenance, breadcrumbs, and lifecycle/storage/corpus statuses.

Do not call live DungeonMindServer from the browser. Do not expose `DUNGEONBUDDY_INTERNAL_API_KEY`. Do not persist artifacts. Do not write to corpus. Do not ingest into the Semantic Knowledge Layer. Do not add to combat. Storage/corpus/combat actions may appear as disabled/read-only affordances only.
```

---

## 1. Re-anchor

The statblock lifecycle is now:

```text
PR #103: API-backed seam
→ v2 contract models
→ server-side HTTP provider
→ mock provider
→ StatblockDraftArtifact mapper
→ lifecycle/status enums
→ command constants

PR #104: commandable seam
→ StatblockLifecycleService
→ health/generate/render command execution
→ optional response → artifact mapping
→ safe structured errors
→ developer smoke CLI
```

What does **not** exist yet:

```text
No Workbench UI
No draft artifact storage
No corpus promotion
No ingestion
No retrieval surface
No combat integration
```

This PR should cross the next threshold: **make a draft artifact visible and reviewable without making it durable yet.**

---

## 2. Product intent

The Workbench is the dedicated interface for the statblock lifecycle. It should eventually manage:

```text
description draft
→ generation
→ review/edit
→ stored draft artifact
→ corpus promotion preview
→ corpus write
→ ingestion/retrieval
→ add to combat
```

This PR only implements the read-only first panel:

```text
mock/service command result
→ StatblockDraftArtifact
→ read-only Workbench display
```

It should be enough for a GM/developer to see the shape of the future experience:

- rendered markdown;
- combat-ready defaults;
- warnings needing DM review;
- provenance;
- breadcrumbs;
- lifecycle/storage/corpus status;
- disabled future actions.

---

## 3. Right-sized PR scope

### In scope

- Add a server-side live-control statblock workbench endpoint using mock provider by default.
- Add TypeScript Workbench types that mirror the JSON shape returned by the endpoint.
- Add a small API client function in `apps/live-control-ui/src/api/liveApi.ts`.
- Add a `StatblockWorkbenchModule` React component.
- Register the module in `apps/live-control-ui/src/surface/moduleRegistry.tsx`.
- Add the module to the default surface catalog/layout as optional, preferably collapsed or hidden by default.
- Add CSS for readable markdown/defaults/warnings/provenance/status display.
- Add focused backend and frontend tests where existing test harnesses support it.

### Out of scope

- No live HTTP calls to DungeonMindServer from the UI.
- No browser-visible internal API key.
- No artifact persistence.
- No corpus writes.
- No ingestion jobs.
- No retrieval/index verification.
- No combat insertion.
- No markdown editing.
- No generation form yet.
- No revise/variant UI.
- No replacement of the legacy planner hook.

---

## 4. Existing repo shape to respect

Current live-control UI loads all state from the live server in `App.tsx`, then renders modules through `SurfaceShell` and `moduleRegistry`.

Relevant files:

```text
apps/live_control_server/routes/live.py
apps/live-control-ui/src/App.tsx
apps/live-control-ui/src/api/liveApi.ts
apps/live-control-ui/src/api/types.ts
apps/live-control-ui/src/surface/SurfaceShell.tsx
apps/live-control-ui/src/surface/moduleRegistry.tsx
src/live_play/session_bootstrap.py
```

Important constraints:

- The live-control UI already uses `/api/live/*` through `apps/live-control-ui/src/api/liveApi.ts`.
- Surface modules are selected by `module_id` in `moduleRegistry.tsx`.
- The default surface catalog/layout is seeded by `src/live_play/session_bootstrap.py`.
- Optional disabled modules show in `SurfaceLayoutPanel`, so the Workbench can be added to layout as hidden by default.

---

## 5. Proposed server endpoint

Add a read-only endpoint under the live router.

Suggested endpoint:

```text
GET /api/live/statblocks/workbench/sample
```

Alternative if preferred:

```text
GET /api/live/statblock-workbench/sample
```

Keep it explicitly sample/dev for this PR. This is not durable storage and not a general query API yet.

### 5.1 Endpoint behavior

The endpoint should:

1. Build a `StatblockLifecycleCommandRequest` for either generate or render.
2. Use `StatblockLifecycleService(MockStatBlockGeneratorProvider(...))`.
3. Return a JSON-safe response containing:
   - `schema_version`;
   - `mode`, e.g. `sample_mock`;
   - `command_result` or summary;
   - `artifact`;
   - `available_actions` with future actions disabled.
4. Never use `DungeonMindServerStatBlockGeneratorClient` by default.
5. Never require or return `DUNGEONBUDDY_INTERNAL_API_KEY`.

Suggested response model:

```python
class StatblockWorkbenchAction(BaseModel):
    action_id: str
    label: str
    enabled: bool = False
    disabled_reason: str | None = None

class StatblockWorkbenchSampleResponse(BaseModel):
    schema_version: Literal["dmb_statblock_workbench_sample_v1"] = "dmb_statblock_workbench_sample_v1"
    mode: Literal["sample_mock"] = "sample_mock"
    artifact: StatblockDraftArtifact
    command_status: str
    diagnostics: list[str] = Field(default_factory=list)
    available_actions: list[StatblockWorkbenchAction] = Field(default_factory=list)
```

Suggested disabled actions:

```text
store_draft
preview_corpus_promotion
promote_to_corpus
ingest_to_semantic_layer
add_to_combat
```

Disabled reasons should say these are future PRs.

### 5.2 Which mock artifact?

Prefer using the existing command facade rather than constructing `StatblockDraftArtifact` directly.

Example flow:

```python
provider = MockStatBlockGeneratorProvider()
service = StatblockLifecycleService(provider)
result = service.execute(
    StatblockLifecycleCommandRequest(
        command_type=STATBLOCK_DRAFT_GENERATE,
        payload={...fixture-like generate request...},
        requested_by="agent",
        breadcrumbs=[...],
    )
)
```

Then return `result.artifact`.

For breadcrumbs, include a small sample set that demonstrates the future:

```text
campaign:c2
session:23
surface:statblock_workbench
source:mock_provider
```

Do not write these breadcrumbs anywhere.

---

## 6. Proposed frontend API/types

### 6.1 `apps/live-control-ui/src/api/types.ts`

Add lightweight types. Keep `structured_statblock` / provenance details permissive.

Suggested types:

```ts
export interface StatblockWorkbenchAction {
  action_id: string;
  label: string;
  enabled: boolean;
  disabled_reason: string | null;
}

export interface StatblockBreadcrumb {
  label: string;
  source?: string | null;
  target?: string | null;
  metadata?: Record<string, unknown>;
}

export interface StatblockCombatDefaults {
  name?: string | null;
  armor_class?: number | string | null;
  hit_points?: number | string | null;
  initiative_bonus?: number | null;
  passive_perception?: number | string | null;
  speed_summary?: string | null;
  speed?: string | null;
  senses_summary?: string | null;
  primary_actions?: string[];
  suggested_tactics?: string[];
  legendary_actions?: number | null;
}

export interface StatblockReviewWarning {
  code?: string | null;
  message: string;
  severity?: string;
  path?: string | null;
}

export interface StatblockDraftArtifactView {
  artifact_id: string;
  draft_id: string;
  title: string;
  markdown: string;
  structured_statblock: Record<string, unknown>;
  combat_defaults: StatblockCombatDefaults;
  warnings: StatblockReviewWarning[];
  provenance: Record<string, unknown>;
  review_status: string;
  lifecycle_state: string;
  storage_status: string;
  corpus_status: string;
  source_refs: Array<Record<string, unknown>>;
  breadcrumbs: StatblockBreadcrumb[];
  created_by: string;
  created_at: string;
  updated_at: string;
}

export interface StatblockWorkbenchSampleResponse {
  schema_version: "dmb_statblock_workbench_sample_v1";
  mode: "sample_mock";
  artifact: StatblockDraftArtifactView;
  command_status: string;
  diagnostics: string[];
  available_actions: StatblockWorkbenchAction[];
}
```

### 6.2 `apps/live-control-ui/src/api/liveApi.ts`

Add:

```ts
export async function getStatblockWorkbenchSample(): Promise<StatblockWorkbenchSampleResponse> {
  return apiFetch<StatblockWorkbenchSampleResponse>("/api/live/statblocks/workbench/sample");
}
```

---

## 7. Proposed frontend module

Suggested file:

```text
apps/live-control-ui/src/surface/modules/StatblockWorkbenchModule.tsx
```

Register in:

```text
apps/live-control-ui/src/surface/moduleRegistry.tsx
```

Module behavior:

- On mount, call `getStatblockWorkbenchSample()`.
- Show loading/error/ready states.
- Show read-only badge: `Sample / mock / read-only`.
- Display the artifact title and statuses.
- Display markdown in a readable pre-wrap block. Do not add a markdown renderer dependency.
- Display combat defaults as compact key/value rows.
- Display warnings as a list with severity/code/message/path.
- Display breadcrumbs as chips or list rows.
- Display provenance as pretty JSON in `<details>`.
- Display source refs as pretty JSON or summarized rows.
- Display disabled future action buttons with disabled reasons.

Suggested component sections:

```text
Header
Status rail
Markdown preview
Combat defaults
Warnings
Breadcrumbs
Provenance / source refs
Future actions disabled
```

This should be useful and visually clear, but do not over-polish. The goal is a skeleton that teaches the lifecycle.

---

## 8. Surface catalog/layout

Add a module catalog entry in `src/live_play/session_bootstrap.py`:

```json
{
  "module_id": "statblock_workbench",
  "title": "Statblock Workbench",
  "default_slot": "main",
  "required": false,
  "enabled_by_default": false,
  "description": "Read-only statblock draft artifact review surface.",
  "config_schema": null
}
```

Add a default layout row, preferably hidden by default so it appears in the Hidden Modules panel:

```json
{
  "module_id": "statblock_workbench",
  "slot": "main",
  "order": 2,
  "enabled": false,
  "collapsed": false,
  "size": "1fr",
  "config": {}
}
```

If there are checked-in eval live session layout/catalog fixtures that need explicit updates, update only the smallest relevant fixture(s). Do not mass-rewrite session data.

---

## 9. Styling

Use existing CSS conventions in `apps/live-control-ui/src/styles.css` unless modules already have co-located CSS.

Add conservative classes, for example:

```text
.statblock-workbench
.statblock-workbench-header
.statblock-status-grid
.statblock-markdown-preview
.statblock-defaults-grid
.statblock-warning-list
.statblock-breadcrumb-list
.statblock-action-row
```

No new UI dependencies.

---

## 10. Backend tests

Add focused backend tests where existing patterns allow.

Suggested file:

```text
tests/live_control/test_statblock_workbench_endpoint.py
```

or under existing live-control test structure if different.

Cover:

- `GET /api/live/statblocks/workbench/sample` returns 200.
- Response schema is `dmb_statblock_workbench_sample_v1`.
- Response contains `artifact`.
- Artifact has markdown, combat defaults, statuses, provenance, breadcrumbs.
- `available_actions` are present and disabled.
- Response does not contain `DUNGEONBUDDY_INTERNAL_API_KEY` or a fake secret if env is set.
- Endpoint uses mock/provider path and does not require production DungeonMindServer credentials.

Do not make live network calls.

---

## 11. Frontend tests

Use the existing frontend test style if present. If there is no existing frontend test harness for modules, keep tests minimal or skip with a clear PR note.

Potential tests:

- API helper calls `/api/live/statblocks/workbench/sample`.
- Component renders title, markdown, combat defaults, warnings, breadcrumbs, disabled future actions from a mocked API response.

If frontend test setup is too heavy, do not invent a large new testing stack in this PR. Backend tests + TypeScript compile are acceptable for the first visible skeleton.

---

## 12. Manual smoke

Expected local smoke:

```bash
# Terminal 1
export DUNGEONMIND_LIVE_SESSION_DIR=evals/c2_live_prep/live/session_22
uv run uvicorn apps.live_control_server.main:app --reload

# Terminal 2
cd apps/live-control-ui
npm run dev
```

Then open the live UI, enable **Statblock Workbench** from Hidden Modules if hidden, and verify:

- module loads sample artifact;
- markdown is visible;
- combat defaults are visible;
- warnings are visible;
- provenance/source refs are visible;
- breadcrumbs are visible;
- future action buttons are disabled;
- no secret value appears in page or API response.

Direct backend smoke:

```bash
curl -s http://127.0.0.1:8000/api/live/statblocks/workbench/sample | jq
```

---

## 13. Out of scope reminders

Do not call live DungeonMindServer from the browser.

Do not add `DUNGEONBUDDY_INTERNAL_API_KEY` to Vite env, frontend config, fixtures, or page output.

Do not persist the artifact.

Do not write markdown files.

Do not modify corpus.

Do not trigger ingestion.

Do not add to combat.

Do not build editable markdown.

Do not add generation/revision forms yet.

Do not make `revise_existing` or `generate_from_source_statblock` visible as enabled product actions.

---

## 14. Acceptance criteria

The PR is ready when:

- A server-side read-only Workbench sample endpoint exists.
- The endpoint uses `StatblockLifecycleService` and mock provider/service output to produce a `StatblockDraftArtifact`.
- The endpoint returns artifact, diagnostics, and disabled future actions.
- The response contains no internal secrets and requires no DungeonMindServer live credentials.
- TypeScript types exist for the Workbench response/artifact view.
- `getStatblockWorkbenchSample()` exists in `liveApi.ts`.
- A `StatblockWorkbenchModule` renders artifact markdown, combat defaults, warnings, provenance/source refs, breadcrumbs, statuses, and disabled future actions.
- The module is registered in `moduleRegistry.tsx`.
- The module is present in default catalog/layout as optional/hidden or otherwise safely discoverable.
- Backend tests cover the endpoint.
- Frontend compile/tests pass according to existing repo practice.
- No persistence, corpus, ingestion, or combat mutation is introduced.

---

## 15. Suggested PR description

```markdown
### Motivation

PR #103 made the StatBlockGenerator v2 seam available inside Buddy, and PR #104 made it commandable. This PR makes the lifecycle visible for the first time by adding a read-only Statblock Workbench skeleton over a mock-generated `StatblockDraftArtifact`.

### Description

- Added a read-only live-control Workbench sample endpoint that uses `StatblockLifecycleService` with the mock provider to produce a `StatblockDraftArtifact`.
- Added Workbench response/action types and a frontend API helper.
- Added `StatblockWorkbenchModule` to display markdown, combat defaults, warnings, provenance/source refs, breadcrumbs, lifecycle/storage/corpus statuses, and disabled future actions.
- Registered `statblock_workbench` in the surface module registry and default catalog/layout as an optional module.
- Added focused tests for the sample endpoint and UI/API behavior where supported.

### Testing

- `uv run python -m pytest tests/statblocks tests/live_control -v` or the repo-appropriate focused backend command
- `cd apps/live-control-ui && npm run typecheck` or repo-appropriate frontend command
- Manual smoke: enable Statblock Workbench in the live UI and confirm the read-only artifact renders without secrets
```

---

## 16. Design reminder

This PR makes the lifecycle **visible**, not durable.

The next durable product steps remain:

```text
read-only Workbench
→ review/edit controls
→ draft storage
→ corpus promotion preview
→ corpus write
→ ingestion/retrieval
→ Statblock View
→ add to combat
```

Keep this slice focused. A clear read-only Workbench teaches the lifecycle and gives future storage/corpus/combat PRs a stable surface to grow from.
