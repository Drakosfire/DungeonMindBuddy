# HANDOFF — Statblock Workbench draft storage PR107

**Created:** 2026-06-09  
**Repo:** `Drakosfire/DungeonMindBuddy`  
**Target base branch:** `main`  
**Suggested next branch:** `codex/statblock-workbench-draft-storage-pr107`  
**Depends on:** PR #106 / `e1228b1f85554b9322d8d6380a90275020f48e08` — Add mock statblock Workbench command endpoint and UI controls  
**Primary design:** `Docs/Design/DESIGN-statblock-lifecycle-agentic-workbench.md`  
**Previous handoffs:**
- `Docs/Plans/HANDOFF-statblock-lifecycle-seam-pr1.md`
- `Docs/Plans/HANDOFF-statblock-lifecycle-command-smoke-pr2.md`
- `Docs/Plans/HANDOFF-statblock-workbench-readonly-pr3.md`
**Mode:** Draft storage lane. Make Workbench artifacts durable as **non-corpus** live/prep draft records. Do not write corpus, ingest, retrieve from Semantic Knowledge Layer, or mutate combat.

---

## 0. Copyable task prompt

```markdown
You are implementing Statblock Workbench PR107 in `Drakosfire/DungeonMindBuddy`.

Read first:

- `Docs/Plans/archive/2026-06-22/handoffs/HANDOFF-statblock-workbench-draft-storage-pr107.md`
- `Docs/Design/DESIGN-statblock-lifecycle-agentic-workbench.md`
- `Docs/Plans/HANDOFF-statblock-workbench-readonly-pr3.md`
- `Docs/Plans/HANDOFF-statblock-lifecycle-command-smoke-pr2.md`

Goal: add a non-corpus draft storage lane for Statblock Workbench artifacts.

PR #106 made the Workbench interactive but non-durable. This PR should let the user store the currently displayed `StatblockDraftArtifact` as a live/prep draft artifact in the current live session workspace, then list/read stored drafts back into the Workbench.

Add server-side file-backed storage under the current live session directory, for example:

`<live_session_dir>/statblock_drafts/<artifact_id>.json`

Use safe path validation and atomic JSON writes. Stored drafts are not corpus canon. They must not be written into the markdown corpus, ingested into the Semantic Knowledge Layer, or added to combat.

Frontend goal: enable a real “Store draft” action in the Workbench, show stored status/path, list stored drafts, and allow loading a stored draft back into the display.

Do not call live DungeonMindServer from the browser. Do not expose `DUNGEONBUDDY_INTERNAL_API_KEY`. Do not write corpus. Do not ingest. Do not add to combat. Store/Promote/Ingest/Add-to-combat must remain separate lifecycle steps; this PR only implements draft storage.
```

---

## 1. Re-anchor

Current ladder:

```text
Producer API live ✅
Buddy v2 seam ✅
Lifecycle command facade ✅
Read-only Workbench ✅
Interactive mock Workbench ✅
Draft storage ❌
Corpus promotion preview ❌
Corpus write ❌
Semantic ingestion/retrieval ❌
Statblock View ❌
Add to combat ❌
Planning Mode generation tasks ❌
```

PR #106 proved:

```text
Workbench button
→ server-side Workbench command endpoint
→ StatblockLifecycleService
→ MockStatBlockGeneratorProvider
→ StatblockDraftArtifact
→ UI replaces displayed artifact
```

PR #107 should add the first durable step:

```text
Displayed StatblockDraftArtifact
→ Store draft
→ file-backed non-corpus draft record
→ list/read stored drafts in Workbench
```

This is still **not corpus promotion**.

---

## 2. Product intent

The Workbench should now become more than a preview surface. It should let a GM keep generated work without making it campaign canon yet.

The new user-visible flow:

```text
Open Statblock Workbench
→ generate or render mock draft
→ inspect markdown/defaults/warnings/provenance/breadcrumbs
→ click Store draft
→ artifact storage_status becomes stored_draft
→ stored draft appears in Stored drafts list
→ click stored draft to reload it into the Workbench
```

This prepares the next PR: corpus promotion preview.

---

## 3. Storage concept

There are two different storage levels in the larger design:

```text
Draft storage
Corpus storage
```

This PR implements **draft storage only**.

Draft storage is:

- file-backed;
- live-session scoped;
- JSON artifact records;
- safe for local prep/live use;
- not part of the markdown corpus;
- not indexed into the Semantic Knowledge Layer;
- not automatically combat-ready.

Corpus storage remains future work:

```text
stored draft
→ preview corpus promotion
→ confirm corpus write
→ markdown file + frontmatter + breadcrumbs
→ ingestion
→ retrieval verification
```

---

## 4. Right-sized PR scope

### In scope

- Add a small file-backed statblock draft store service.
- Store `StatblockDraftArtifact` records under the current live session workspace.
- Update stored artifact status to:
  - `lifecycle_state = "stored_artifact"`
  - `storage_status = "stored_draft"`
  - `corpus_status = "not_promoted"`
- Add live-control endpoints to store/list/read draft artifacts.
- Enable a real Store draft action in the Workbench.
- Show stored status/path after successful storage.
- List stored drafts in the Workbench.
- Load a stored draft back into the Workbench display.
- Add backend and frontend tests.

### Out of scope

- No markdown corpus writes.
- No frontmatter generation for corpus promotion.
- No Semantic Knowledge Layer ingestion.
- No retrieval/index verification.
- No combat mutation.
- No Add to Combat behavior.
- No live DungeonMindServer browser calls.
- No internal API-key exposure.
- No prompt editing/general generation form.
- No full artifact database.
- No multi-user concurrency guarantees beyond existing local single-user file store patterns.

---

## 5. Existing repo shape to respect

Relevant server files:

```text
apps/live_control_server/routes/live.py
apps/live_control_server/services/statblock_workbench.py
apps/live_control_server/session_store.py
src/live_play/live_store.py
src/live_play/session_paths.py
src/statblocks/lifecycle_artifact.py
```

Useful existing patterns:

- `apps/live_control_server.routes.live` hosts `/api/live/*` endpoints.
- `apps.live_control_server.config.session_dir()` resolves the current live session directory.
- `src.live_play.live_store.write_json()` writes JSON atomically using stable formatting.
- Existing session storage is file-backed and local-first.

Relevant frontend files:

```text
apps/live-control-ui/src/api/types.ts
apps/live-control-ui/src/api/liveApi.ts
apps/live-control-ui/src/api/liveApi.test.ts
apps/live-control-ui/src/surface/modules/StatblockWorkbenchModule.tsx
apps/live-control-ui/src/surface/modules/StatblockWorkbenchModule.test.tsx
apps/live-control-ui/src/styles.css
```

---

## 6. Proposed storage paths

Use a new directory under the current live session directory:

```text
<live_session_dir>/statblock_drafts/
```

Each draft record:

```text
<live_session_dir>/statblock_drafts/<artifact_id>.json
```

Example:

```text
evals/c2_live_prep/live/session_22/statblock_drafts/statblock-draft-abc123.json
```

Do **not** write to:

```text
corpus/
corpus/eldyrwild-markdown/
Docs/
evals/c2_live_prep/benchmarks/
```

### 6.1 Artifact ID safety

Do not allow artifact IDs to become paths.

Recommended validation:

```text
^[A-Za-z0-9_.:-]+$
```

Reject IDs containing:

```text
/
\\
..
~
absolute paths
URL-like paths
```

If artifact IDs are too permissive today, keep storage validation strict and return a 422/400 error for unsafe IDs.

---

## 7. Server storage service

Add a dedicated service module:

```text
apps/live_control_server/services/statblock_draft_store.py
```

Suggested models:

```python
class StoredStatblockDraftRecord(BaseModel):
    schema_version: Literal["dmb_statblock_draft_record_v1"] = "dmb_statblock_draft_record_v1"
    artifact_id: str
    title: str
    campaign_id: str
    session: int
    stored_at: str
    updated_at: str
    storage_path: str
    artifact: StatblockDraftArtifact

class StoredStatblockDraftSummary(BaseModel):
    artifact_id: str
    title: str
    draft_id: str
    review_status: str
    lifecycle_state: str
    storage_status: str
    corpus_status: str
    stored_at: str
    updated_at: str
    storage_path: str

class StoreStatblockDraftRequest(BaseModel):
    artifact: StatblockDraftArtifact
    source: Literal["workbench"] = "workbench"

class StoreStatblockDraftResponse(BaseModel):
    schema_version: Literal["dmb_statblock_draft_store_v1"] = "dmb_statblock_draft_store_v1"
    record: StoredStatblockDraftRecord
    diagnostics: list[str] = Field(default_factory=list)

class ListStatblockDraftsResponse(BaseModel):
    schema_version: Literal["dmb_statblock_draft_list_v1"] = "dmb_statblock_draft_list_v1"
    drafts: list[StoredStatblockDraftSummary]

class ReadStatblockDraftResponse(BaseModel):
    schema_version: Literal["dmb_statblock_draft_read_v1"] = "dmb_statblock_draft_read_v1"
    record: StoredStatblockDraftRecord
```

Suggested functions:

```python
def store_statblock_draft(
    *,
    base: Path,
    campaign_id: str,
    session: int,
    artifact: StatblockDraftArtifact,
    now: Callable[[], datetime] | None = None,
) -> StoredStatblockDraftRecord: ...


def list_statblock_drafts(*, base: Path) -> list[StoredStatblockDraftSummary]: ...


def read_statblock_draft(*, base: Path, artifact_id: str) -> StoredStatblockDraftRecord: ...
```

### 7.1 Store behavior

When storing:

1. Validate `artifact.artifact_id` is path-safe.
2. Create `<base>/statblock_drafts/` if missing.
3. Copy artifact with updated lifecycle fields:
   - `lifecycle_state="stored_artifact"`
   - `storage_status="stored_draft"`
   - `corpus_status="not_promoted"`
   - `updated_at=<now>`
4. Preserve:
   - markdown;
   - structured statblock;
   - combat defaults;
   - warnings;
   - provenance;
   - source refs;
   - breadcrumbs;
   - created_at;
   - created_by.
5. Write `StoredStatblockDraftRecord` as JSON via `write_json(...)`.
6. Return the stored record.

Overwriting behavior:

- For this PR, allow idempotent overwrite of the same `artifact_id` and document it.
- Do not create a revision system yet.
- Do not silently change `artifact_id`.

### 7.2 List behavior

List should:

- read all `*.json` records under `statblock_drafts/`;
- validate/parse each as `StoredStatblockDraftRecord`;
- return summaries sorted by `updated_at` descending, fallback title/artifact_id stable sort;
- return empty list if directory does not exist.

### 7.3 Read behavior

Read should:

- validate path-safe `artifact_id`;
- read `<artifact_id>.json`;
- return 404 if missing;
- return typed record if present.

---

## 8. Live-control endpoints

Add endpoints in `apps/live_control_server/routes/live.py`.

### 8.1 Store current draft artifact

```text
POST /api/live/statblocks/workbench/drafts
```

Request:

```json
{
  "artifact": { "...": "StatblockDraftArtifact" },
  "source": "workbench"
}
```

Response:

```json
{
  "schema_version": "dmb_statblock_draft_store_v1",
  "record": {
    "schema_version": "dmb_statblock_draft_record_v1",
    "artifact_id": "...",
    "title": "...",
    "campaign_id": "c2",
    "session": 22,
    "stored_at": "...",
    "updated_at": "...",
    "storage_path": "statblock_drafts/<artifact_id>.json",
    "artifact": { "...": "stored StatblockDraftArtifact" }
  },
  "diagnostics": [
    "stored as non-corpus draft artifact",
    "no corpus write, ingestion, or combat mutation occurred"
  ]
}
```

Use current live packet for `campaign_id` and `session`:

```python
base = session_dir()
packet, _, _, _ = load_session(base)
```

### 8.2 List stored drafts

```text
GET /api/live/statblocks/workbench/drafts
```

Response: `ListStatblockDraftsResponse`.

### 8.3 Read stored draft

```text
GET /api/live/statblocks/workbench/drafts/{artifact_id}
```

Response: `ReadStatblockDraftResponse`.

### 8.4 Errors

Recommended errors:

```text
400/422 unsafe artifact id
404 draft not found
500 invalid stored record / unexpected write failure
```

Keep details safe. Do not include host paths if avoidable; prefer relative `storage_path` in normal responses.

---

## 9. Frontend API/types

Update:

```text
apps/live-control-ui/src/api/types.ts
apps/live-control-ui/src/api/liveApi.ts
```

Suggested TypeScript types:

```ts
export interface StoredStatblockDraftRecord {
  schema_version: "dmb_statblock_draft_record_v1";
  artifact_id: string;
  title: string;
  campaign_id: string;
  session: number;
  stored_at: string;
  updated_at: string;
  storage_path: string;
  artifact: StatblockDraftArtifactView;
}

export interface StoredStatblockDraftSummary {
  artifact_id: string;
  title: string;
  draft_id: string;
  review_status: string;
  lifecycle_state: string;
  storage_status: string;
  corpus_status: string;
  stored_at: string;
  updated_at: string;
  storage_path: string;
}

export interface StoreStatblockDraftRequest {
  artifact: StatblockDraftArtifactView;
  source: "workbench";
}

export interface StoreStatblockDraftResponse {
  schema_version: "dmb_statblock_draft_store_v1";
  record: StoredStatblockDraftRecord;
  diagnostics: string[];
}

export interface ListStatblockDraftsResponse {
  schema_version: "dmb_statblock_draft_list_v1";
  drafts: StoredStatblockDraftSummary[];
}

export interface ReadStatblockDraftResponse {
  schema_version: "dmb_statblock_draft_read_v1";
  record: StoredStatblockDraftRecord;
}
```

API helpers:

```ts
export async function storeStatblockWorkbenchDraft(
  request: StoreStatblockDraftRequest,
): Promise<StoreStatblockDraftResponse> { ... }

export async function listStatblockWorkbenchDrafts(): Promise<ListStatblockDraftsResponse> { ... }

export async function getStatblockWorkbenchDraft(
  artifactId: string,
): Promise<ReadStatblockDraftResponse> { ... }
```

Use `encodeURIComponent(artifactId)` for read route.

---

## 10. Frontend Workbench behavior

Update:

```text
apps/live-control-ui/src/surface/modules/StatblockWorkbenchModule.tsx
```

### 10.1 Store draft action

PR #106 kept all future actions disabled. PR107 should graduate **Store draft** into a real action.

Recommended UI behavior:

- Add a clear storage section near command buttons or above Future actions.
- Button label: `Store draft`.
- Enabled when:
  - current artifact exists;
  - no command pending;
  - no store pending;
  - current artifact `storage_status !== "stored_draft"`.
- On click:
  - call `storeStatblockWorkbenchDraft({ artifact: currentArtifact, source: "workbench" })`;
  - replace displayed artifact with `response.record.artifact`;
  - show stored path/status;
  - refresh stored drafts list.

The existing `available_actions` list can still show future actions, but do not present a second confusing disabled Store card if there is now a real Store control. Options:

1. Filter `store_draft` out of the disabled future action card list and render it only as the real storage action; or
2. Render `store_draft` action card as enabled and wire it to the store handler while all other actions remain disabled.

Preference: **Option 1** for clarity.

### 10.2 Stored drafts list

Add a section:

```text
Stored drafts
```

Behavior:

- On Workbench mount, call `listStatblockWorkbenchDrafts()`.
- After successful store, refresh list.
- If list empty, show `No stored statblock drafts yet.`
- For each summary, show:
  - title;
  - review status;
  - storage status;
  - corpus status;
  - updated/stored time;
  - storage path.
- Add `Load` button per row.
- On Load:
  - call `getStatblockWorkbenchDraft(artifact_id)`;
  - replace displayed artifact with record.artifact;
  - show loaded storage path/status.

### 10.3 Status display

After storing, the visible status rail should show:

```text
Lifecycle: stored_artifact
Storage: stored_draft
Corpus: not_promoted
```

Add a small storage note:

```text
Stored as non-corpus draft: statblock_drafts/<artifact_id>.json
```

Do not imply it is indexed, promoted, or combat-ready.

### 10.4 Future actions remain disabled

Keep these disabled:

```text
Preview corpus promotion
Promote to corpus
Ingest to Semantic Knowledge Layer
Add to combat
```

If the server still includes `store_draft` in `available_actions`, either filter it or make it the only enabled action wired to storage. Do not leave two Store Draft buttons with conflicting states.

---

## 11. Backend tests

Add focused tests, likely in:

```text
tests/test_live_statblock_workbench_endpoint.py
```

or new:

```text
tests/test_live_statblock_draft_store.py
```

Use a temporary live session directory if existing test fixtures support monkeypatching `DUNGEONMIND_LIVE_SESSION_DIR`. Avoid writing into checked-in `session_22` during tests.

Test cases:

### 11.1 Store draft writes non-corpus record

Flow:

```text
GET /api/live/statblocks/workbench/sample
POST /api/live/statblocks/workbench/drafts with sample artifact
```

Assert:

- status 200;
- response schema `dmb_statblock_draft_store_v1`;
- record schema `dmb_statblock_draft_record_v1`;
- artifact status updated:
  - `lifecycle_state == stored_artifact`;
  - `storage_status == stored_draft`;
  - `corpus_status == not_promoted`;
- file exists under `<session_dir>/statblock_drafts/<artifact_id>.json`;
- file does not exist outside session dir;
- response storage path is relative, not absolute.

### 11.2 List stored drafts

After store:

```text
GET /api/live/statblocks/workbench/drafts
```

Assert:

- stored artifact appears in list;
- summary includes title/status/path;
- no full markdown in summary unless intentionally included.

### 11.3 Read stored draft

After store:

```text
GET /api/live/statblocks/workbench/drafts/{artifact_id}
```

Assert:

- returns record;
- artifact markdown/defaults/provenance preserved.

### 11.4 Unsafe artifact ID rejected

Submit artifact with unsafe ID, e.g.:

```text
../evil
nested/path
/path
~/.ssh/id_rsa
```

Assert 400/422 and no file written.

### 11.5 Missing draft read returns 404

```text
GET /api/live/statblocks/workbench/drafts/not-found
```

Assert 404.

### 11.6 No corpus/ingestion/combat mutation

At minimum assert no files are created in obvious corpus paths and no event/job rows are appended.

If using a temp live session dir, snapshot before/after:

```text
live_packet.json unchanged
surface_layout.json unchanged
event_log.jsonl unchanged
job_queue.jsonl unchanged
```

Only `statblock_drafts/` should change.

### 11.7 No secret exposure

Set fake env:

```text
DUNGEONBUDDY_INTERNAL_API_KEY=super-secret-test-key
DUNGEONMIND_SERVER_URL=https://example.invalid
```

Call store/list/read.

Assert response text does not contain:

```text
super-secret-test-key
DUNGEONBUDDY_INTERNAL_API_KEY
DUNGEONMIND_SERVER_URL
X-DungeonBuddy-Internal-Key
```

---

## 12. Frontend tests

Update:

```text
apps/live-control-ui/src/api/liveApi.test.ts
apps/live-control-ui/src/surface/modules/StatblockWorkbenchModule.test.tsx
```

### 12.1 API helper tests

Assert:

- `storeStatblockWorkbenchDraft()` POSTs to `/api/live/statblocks/workbench/drafts`;
- request body contains artifact/source;
- `listStatblockWorkbenchDrafts()` GETs `/api/live/statblocks/workbench/drafts`;
- `getStatblockWorkbenchDraft(id)` GETs `/api/live/statblocks/workbench/drafts/${encodeURIComponent(id)}`.

### 12.2 Component tests

Add tests:

1. Stored drafts list loads on mount.
   - Empty list shows empty state.

2. Store draft succeeds.
   - Click Store draft.
   - Calls `storeStatblockWorkbenchDraft` with current artifact.
   - Replaces artifact with stored artifact/status.
   - Shows `stored_draft` and storage path.
   - Refreshes stored drafts list.

3. Store draft failure.
   - Existing artifact remains visible.
   - Safe error message appears.

4. Load stored draft succeeds.
   - Mock list with one summary.
   - Click Load.
   - Calls `getStatblockWorkbenchDraft`.
   - Replaces displayed artifact.

5. Future actions remain disabled.
   - Preview corpus promotion / promote / ingest / add to combat disabled.

Use mocked API helpers. No live network.

---

## 13. Manual smoke

Backend:

```bash
uv run uvicorn apps.live_control_server.main:app --reload
```

Create a mock artifact via command endpoint:

```bash
curl -s \
  -X POST \
  -H "Content-Type: application/json" \
  http://127.0.0.1:8000/api/live/statblocks/workbench/command \
  -d '{"command_type":"statblock.draft.generate","requested_by":"human","as_artifact":true}' \
  | jq '.artifact' > /tmp/statblock-artifact.json
```

Store it:

```bash
jq '{artifact: ., source: "workbench"}' /tmp/statblock-artifact.json \
  | curl -s \
      -X POST \
      -H "Content-Type: application/json" \
      http://127.0.0.1:8000/api/live/statblocks/workbench/drafts \
      -d @- \
  | jq
```

List:

```bash
curl -s http://127.0.0.1:8000/api/live/statblocks/workbench/drafts | jq
```

Frontend:

```bash
cd apps/live-control-ui
npm run dev
```

Open Workbench and verify:

```text
Generate mock draft works.
Store draft works.
Status changes to stored_artifact / stored_draft / not_promoted.
Stored draft appears in list.
Load stored draft replaces display.
Corpus/ingest/add-to-combat remain disabled.
No secret strings appear.
```

---

## 14. Testing commands

Suggested backend:

```bash
uv run pytest \
  tests/test_live_statblock_workbench_endpoint.py \
  tests/test_live_session_bootstrap.py \
  -q
```

Suggested frontend:

```bash
cd apps/live-control-ui
npm test -- \
  src/surface/modules/StatblockWorkbenchModule.test.tsx \
  src/api/liveApi.test.ts
```

Typecheck:

```bash
cd apps/live-control-ui
npx tsc -p tsconfig.app.json --noEmit
```

Lint/format:

```bash
uv run ruff check \
  apps/live_control_server/services/statblock_workbench.py \
  apps/live_control_server/services/statblock_draft_store.py \
  apps/live_control_server/routes/live.py \
  tests/test_live_statblock_workbench_endpoint.py

git diff --check
```

If full UI test/build remains blocked by unrelated environment issues, document the caveat in the PR body.

---

## 15. Acceptance criteria

The PR is ready when:

- Server-side draft store service exists.
- Store/list/read endpoints exist under `/api/live/statblocks/workbench/drafts`.
- Stored records are written under the current live session's `statblock_drafts/` directory.
- Artifact ID path validation prevents traversal/unsafe paths.
- Store updates artifact statuses to `stored_artifact` / `stored_draft` / `not_promoted`.
- Store preserves markdown, structured statblock, combat defaults, warnings, provenance, source refs, breadcrumbs, created_at, and created_by.
- List returns summaries.
- Read returns full stored records.
- Responses use relative storage paths, not absolute host paths.
- Responses do not expose internal API keys or secret env names.
- Tests prove no corpus write, ingestion, event/job append, or combat mutation occurs.
- Frontend can store the current artifact.
- Frontend can list stored drafts.
- Frontend can load a stored draft into the Workbench display.
- Future corpus/ingest/add-to-combat actions remain disabled.
- Focused backend and frontend tests pass.

---

## 16. Suggested PR description

```markdown
### Motivation

PR #106 made the Statblock Workbench interactive but non-durable. This PR adds the next lifecycle step: storing a generated/rendered `StatblockDraftArtifact` as a non-corpus live/prep draft artifact. Stored drafts remain outside the markdown corpus and are not ingested or added to combat.

### Description

- Added a file-backed statblock draft store under the current live session workspace.
- Added store/list/read models and endpoints for Workbench draft artifacts.
- Stored drafts under `statblock_drafts/<artifact_id>.json` with safe artifact ID validation.
- Updated stored artifact statuses to `stored_artifact`, `stored_draft`, and `not_promoted`.
- Added frontend API helpers and types for store/list/read.
- Added Workbench storage controls: Store draft, stored status/path, stored drafts list, and load stored draft.
- Kept corpus promotion, ingestion, and add-to-combat actions disabled.
- Added backend/frontend tests covering storage, read/list, path safety, no-secret exposure, and no corpus/combat mutation.

### Testing

- `uv run pytest tests/test_live_statblock_workbench_endpoint.py tests/test_live_session_bootstrap.py -q`
- `cd apps/live-control-ui && npm test -- src/surface/modules/StatblockWorkbenchModule.test.tsx src/api/liveApi.test.ts`
- `cd apps/live-control-ui && npx tsc -p tsconfig.app.json --noEmit`
- `uv run ruff check apps/live_control_server/services/statblock_workbench.py apps/live_control_server/services/statblock_draft_store.py apps/live_control_server/routes/live.py tests/test_live_statblock_workbench_endpoint.py`
- `git diff --check`
```

---

## 17. Design reminder

This PR makes artifacts **durable as drafts**, not corpus knowledge.

The ladder after this PR should be:

```text
API-backed ✅
Commandable ✅
Visible ✅
Interactive ✅
Persistent draft storage ⏭️ this PR
Corpus promotion preview ❌
Corpus write ❌
Semantic ingestion/retrieval ❌
Combat-usable ❌
Planning-mode-integrated ❌
```

Keep this slice focused. The next PR should be corpus promotion preview, not ingestion and not combat.
