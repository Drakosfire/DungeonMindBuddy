# HANDOFF — Statblock corpus confirmed write PR109

**Created:** 2026-06-09  
**Repo:** `Drakosfire/DungeonMindBuddy`  
**Target base branch:** `main`  
**Suggested next branch:** `codex/statblock-corpus-confirmed-write-pr109`  
**Depends on:** PR #108 / `4fa8df55ee95cf64ec4bb6a6064b09177f48b216` — Add statblock corpus promotion preview  
**Primary design:** `Docs/Design/DESIGN-statblock-lifecycle-agentic-workbench.md`  
**Previous handoffs:**
- `Docs/Plans/HANDOFF-statblock-lifecycle-seam-pr1.md`
- `Docs/Plans/HANDOFF-statblock-lifecycle-command-smoke-pr2.md`
- `Docs/Plans/HANDOFF-statblock-workbench-readonly-pr3.md`
- `Docs/Plans/HANDOFF-statblock-workbench-draft-storage-pr107.md`
- `Docs/Plans/HANDOFF-statblock-corpus-promotion-preview-pr108.md`
**Mode:** Confirmed corpus write only. Add a narrow generated-statblock writer allowlist and a two-step prepare/commit flow. Do not ingest, retrieve, index, or mutate combat.

---

## 0. Copyable task prompt

```markdown
You are implementing Statblock Workbench PR109 in `Drakosfire/DungeonMindBuddy`.

Read first:

- `Docs/Plans/HANDOFF-statblock-corpus-confirmed-write-pr109.md`
- `Docs/Plans/HANDOFF-statblock-corpus-promotion-preview-pr108.md`
- `Docs/Design/DESIGN-statblock-lifecycle-agentic-workbench.md`
- `src/agent/corpus_writer.py`
- `apps/live_control_server/services/statblock_corpus_preview.py`
- `apps/live_control_server/services/statblock_draft_store.py`

Goal: implement explicit confirmed corpus write for stored statblock drafts.

PR #108 added preview-only corpus promotion. PR109 should add a two-step write flow:

1. Prepare corpus write: rebuild the PR108 promotion preview and call `write_corpus_file(..., dry_run=True)` to get the corpus writer's real `confirm_token` and unified diff.
2. Commit corpus write: require the exact writer `confirm_token`, rebuild the same content, call `write_corpus_file(..., dry_run=False, confirm_token=...)`, write the generated statblock markdown file to the allowlisted corpus path, and update the stored draft record's statuses.

Important: the PR108 `preview_token` is an audit/display token, not the corpus writer commit token. PR109 must use the writer's own dry-run `confirm_token` discipline.

Add a narrow generated-statblock create allowlist to `src/agent/corpus_writer.py`, likely:

`Longmont Campaign/Campaign N/Statblocks/generated/<safe_slug>.md`

Do not ingest into the Semantic Knowledge Layer. Do not verify retrieval. Do not add to combat. Do not modify broad corpus write policy beyond this narrow generated-statblock path. Do not expose internal secrets.
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
Persistent non-corpus draft storage ✅
Corpus promotion preview ✅
Corpus write ❌
Semantic ingestion/retrieval ❌
Statblock View ❌
Add to combat ❌
Planning Mode generation tasks ❌
```

PR #108 added:

```text
stored draft
→ proposed corpus path
→ frontmatter
→ full markdown preview
→ preview token
→ writer allowlist report
```

PR #109 should add:

```text
stored draft
→ prepare corpus writer dry-run
→ review writer diff + confirm_token
→ commit with confirm_token
→ write corpus markdown file
→ update stored draft corpus/write statuses
```

This PR still does **not** ingest or make the statblock retrievable.

---

## 2. Product intent

The GM should be able to take a stored Workbench draft and intentionally promote it into the markdown corpus, with a safety gate between preview and write.

Target user-visible flow:

```text
Open Statblock Workbench
→ load stored draft
→ Preview corpus promotion
→ Prepare corpus write
→ inspect corpus writer diff and confirm token
→ click Confirm corpus write
→ corpus markdown file is created
→ stored draft status updates to promoted/written
→ ingestion and add-to-combat remain disabled
```

The key safety principle:

```text
No silent corpus mutation.
```

The write must require explicit confirmation using the corpus writer's own confirm token.

---

## 3. Design boundary

### PR109 does

- add a narrow generated-statblock corpus writer allowlist;
- prepare a dry-run corpus write using `write_corpus_file(..., dry_run=True)`;
- expose the writer diff and writer `confirm_token` to the Workbench;
- commit the write only when the caller sends the exact writer `confirm_token`;
- create the generated statblock markdown file at the previewed allowlisted path;
- update the stored draft record to reflect corpus write success;
- show corpus write result in the Workbench.

### PR109 does not

- ingest/reindex the Semantic Knowledge Layer;
- verify retrieval;
- create a Statblock View search result;
- add to combat;
- call DungeonMindServer generation endpoints;
- modify unrelated corpus writer allowlists;
- allow overwriting existing corpus files;
- write outside `corpus/eldyrwild-markdown`;
- use the PR108 `preview_token` as a commit token.

---

## 4. Existing corpus writer contract

`src/agent/corpus_writer.py` already provides a two-phase write API:

```python
write_corpus_file(
    corpus_dir: Path,
    *,
    path: str,
    mode: str,
    content: str,
    dry_run: bool = True,
    confirm_token: str | None = None,
) -> dict[str, Any]
```

Dry-run returns:

```text
ok
phase = preview
path
mode
confirm_token
diff
new_size_bytes
next_call
```

Commit requires the same `confirm_token`. If file state or content changed since dry-run, the writer refuses the commit.

Use this contract directly. Do not invent a separate commit token.

---

## 5. Corpus writer allowlist change

Add one narrow create allowlist for generated statblock markdown.

Suggested regex:

```python
_GENERATED_STATBLOCK_CREATE_RE = re.compile(
    r"^Longmont Campaign/Campaign \d+/Statblocks/generated/[a-z0-9_]+\.md$"
)
```

In `is_writable_corpus_path(..., mode="create")`, allow this path before returning the create-mode error.

Important:

- Only allow `create`, not append.
- Only allow `Longmont Campaign/Campaign N/Statblocks/generated/<safe_slug>.md`.
- Only allow lowercase safe slugs generated by the PR108 slug strategy.
- Do not allow nested folders under `generated/`.
- Do not allow arbitrary `*statblock*` file names elsewhere.
- Preserve the existing static bible deny policy for dossier/seed/static statblock files.

### 5.1 Writer tests

Add/update tests around `is_writable_corpus_path` and `write_corpus_file`.

Required cases:

```text
Allowed create:
Longmont Campaign/Campaign 2/Statblocks/generated/generated_obsidian_thornling.md

Rejected create:
Longmont Campaign/Campaign 2/Statblocks/generated/Nested/foo.md
Longmont Campaign/Campaign 2/Statblocks/generated/Bad Slug.md
Longmont Campaign/Campaign 2/Statblocks/generated/foo.txt
Elderwyld/Creatures/generated_obsidian_thornling.md
Longmont Campaign/Campaign 2/NPCs/foo/foo_statblock.md

Rejected append:
Longmont Campaign/Campaign 2/Statblocks/generated/generated_obsidian_thornling.md
```

Also test dry-run/commit behavior for the allowed generated path using a temp corpus dir.

---

## 6. Corpus root resolution

Use repo-local corpus root:

```text
<repo_root>/corpus/eldyrwild-markdown
```

Suggested helper in a live-control service:

```python
def corpus_root() -> Path:
    return repo_root() / "corpus" / "eldyrwild-markdown"
```

Use `apps.live_control_server.config.repo_root()`.

Normal API responses should expose corpus-relative/display paths, not host absolute paths.

Only tests may inspect absolute temp paths.

---

## 7. Backend service design

Add a new service or extend the preview service carefully:

```text
apps/live_control_server/services/statblock_corpus_write.py
```

Keep write orchestration separate from pure preview logic in `statblock_corpus_preview.py`.

### 7.1 Models

Suggested models:

```python
class StatblockCorpusWritePrepareRequest(BaseModel):
    preview_token: str | None = None

class StatblockCorpusWritePrepareResponse(BaseModel):
    schema_version: Literal["dmb_statblock_corpus_write_prepare_v1"] = "dmb_statblock_corpus_write_prepare_v1"
    artifact_id: str
    draft_id: str
    title: str
    preview_token: str
    proposed_corpus_relpath: str
    proposed_corpus_display_path: str
    writer_ok: bool
    writer_phase: str | None = None
    writer_confirm_token: str | None = None
    writer_diff: str | None = None
    new_size_bytes: int | None = None
    warnings: list[StatblockPromotionWarning] = Field(default_factory=list)
    diagnostics: list[str] = Field(default_factory=list)
    available_actions: list[StatblockWorkbenchAction] = Field(default_factory=list)

class StatblockCorpusWriteCommitRequest(BaseModel):
    preview_token: str
    writer_confirm_token: str

class StatblockCorpusWriteCommitResponse(BaseModel):
    schema_version: Literal["dmb_statblock_corpus_write_commit_v1"] = "dmb_statblock_corpus_write_commit_v1"
    artifact_id: str
    draft_id: str
    title: str
    preview_token: str
    proposed_corpus_relpath: str
    proposed_corpus_display_path: str
    writer_ok: bool
    writer_phase: str | None = None
    bytes_written: int | None = None
    new_corpus_fingerprint: str | None = None
    stored_record: StoredStatblockDraftRecord
    diagnostics: list[str] = Field(default_factory=list)
    available_actions: list[StatblockWorkbenchAction] = Field(default_factory=list)
```

### 7.2 Prepare behavior

Function:

```python
def prepare_statblock_corpus_write(
    *,
    base: Path,
    packet: dict[str, Any],
    artifact_id: str,
    expected_preview_token: str | None = None,
) -> StatblockCorpusWritePrepareResponse: ...
```

Behavior:

1. Read stored draft record.
2. Build PR108 promotion preview by calling `build_statblock_corpus_promotion_preview(...)`.
3. If `expected_preview_token` is provided and does not match the rebuilt preview, return 409/422 through route.
4. Call:

```python
write_corpus_file(
    corpus_root(),
    path=preview.proposed_corpus_relpath,
    mode="create",
    content=preview.full_markdown,
    dry_run=True,
)
```

5. If writer returns `ok=False`, return response with `writer_ok=False`, warnings/diagnostics, and no commit action enabled.
6. If writer returns `ok=True`, return writer diff and `writer_confirm_token`.
7. Do not write corpus.
8. Do not update stored draft record.

### 7.3 Commit behavior

Function:

```python
def commit_statblock_corpus_write(
    *,
    base: Path,
    packet: dict[str, Any],
    artifact_id: str,
    preview_token: str,
    writer_confirm_token: str,
) -> StatblockCorpusWriteCommitResponse: ...
```

Behavior:

1. Read stored draft record.
2. Rebuild PR108 promotion preview.
3. Require `preview.preview_token == request.preview_token`.
4. Call:

```python
write_corpus_file(
    corpus_root(),
    path=preview.proposed_corpus_relpath,
    mode="create",
    content=preview.full_markdown,
    dry_run=False,
    confirm_token=writer_confirm_token,
)
```

5. If writer returns `ok=False`, return a safe 409/422/500 depending on reason. Do not update stored record.
6. If writer returns `ok=True`, update stored draft artifact statuses:
   - `lifecycle_state = "corpus_promoted"`
   - `corpus_status = "promotion_confirmed"`
   - `storage_status = "stored_draft"`
   - `updated_at = now`
7. Add or preserve metadata linking to corpus path. Since the current artifact model may not have an explicit corpus path field, use one of these options:
   - add a `corpus_relpath` / `promoted_corpus_relpath` field to the stored record model, or
   - add a dedicated `promotion` object to the stored record wrapper.

Prefer adding fields to `StoredStatblockDraftRecord` rather than overloading artifact internals:

```python
corpus_relpath: str | None = None
corpus_display_path: str | None = None
corpus_written_at: str | None = None
corpus_preview_token: str | None = None
```

8. Write the updated stored record back to `statblock_drafts/<artifact_id>.json`.
9. Return the commit response.

### 7.4 Commit staleness behavior

If any of these changed after prepare, the writer confirm token should fail:

- target file state;
- proposed content;
- proposed path.

That is good. Surface the failure as:

```text
stale_writer_confirm_token
```

or preserve the writer error in a safe response.

The user should need to prepare again.

---

## 8. Live-control endpoints

Add endpoints in `apps/live_control_server/routes/live.py`.

### 8.1 Prepare write

```text
POST /api/live/statblocks/workbench/drafts/{artifact_id}/corpus-write/prepare
```

Request:

```json
{
  "preview_token": "optional-pr108-preview-token"
}
```

Response: `StatblockCorpusWritePrepareResponse`.

### 8.2 Commit write

```text
POST /api/live/statblocks/workbench/drafts/{artifact_id}/corpus-write/commit
```

Request:

```json
{
  "preview_token": "pr108-preview-token",
  "writer_confirm_token": "writer-dry-run-confirm-token"
}
```

Response: `StatblockCorpusWriteCommitResponse`.

### 8.3 Errors

Recommended:

```text
404 stored draft not found
422 unsafe artifact id / missing token / preview token mismatch
409 stale writer confirm token or target file already exists
500 unexpected writer failure
```

Keep responses safe:

- no host absolute paths;
- no internal API keys;
- no raw tracebacks.

---

## 9. Frontend API/types

Update:

```text
apps/live-control-ui/src/api/types.ts
apps/live-control-ui/src/api/liveApi.ts
apps/live-control-ui/src/api/liveApi.test.ts
```

Suggested types:

```ts
export interface StatblockCorpusWritePrepareRequest {
  preview_token?: string | null;
}

export interface StatblockCorpusWritePrepareResponse {
  schema_version: "dmb_statblock_corpus_write_prepare_v1";
  artifact_id: string;
  draft_id: string;
  title: string;
  preview_token: string;
  proposed_corpus_relpath: string;
  proposed_corpus_display_path: string;
  writer_ok: boolean;
  writer_phase?: string | null;
  writer_confirm_token?: string | null;
  writer_diff?: string | null;
  new_size_bytes?: number | null;
  warnings: StatblockPromotionWarning[];
  diagnostics: string[];
  available_actions: StatblockWorkbenchAction[];
}

export interface StatblockCorpusWriteCommitRequest {
  preview_token: string;
  writer_confirm_token: string;
}

export interface StatblockCorpusWriteCommitResponse {
  schema_version: "dmb_statblock_corpus_write_commit_v1";
  artifact_id: string;
  draft_id: string;
  title: string;
  preview_token: string;
  proposed_corpus_relpath: string;
  proposed_corpus_display_path: string;
  writer_ok: boolean;
  writer_phase?: string | null;
  bytes_written?: number | null;
  new_corpus_fingerprint?: string | null;
  stored_record: StoredStatblockDraftRecord;
  diagnostics: string[];
  available_actions: StatblockWorkbenchAction[];
}
```

API helpers:

```ts
export async function prepareStatblockCorpusWrite(
  artifactId: string,
  request: StatblockCorpusWritePrepareRequest = {},
): Promise<StatblockCorpusWritePrepareResponse> { ... }

export async function commitStatblockCorpusWrite(
  artifactId: string,
  request: StatblockCorpusWriteCommitRequest,
): Promise<StatblockCorpusWriteCommitResponse> { ... }
```

Use `encodeURIComponent(artifactId)`.

---

## 10. Frontend Workbench behavior

Update:

```text
apps/live-control-ui/src/surface/modules/StatblockWorkbenchModule.tsx
```

### 10.1 Prepare write action

After PR108 preview is present, enable:

```text
Prepare corpus write
```

Only enabled when:

- current artifact is stored;
- `corpusPreview` exists;
- no command/store/load/preview/write action is pending.

On click:

```text
POST prepare endpoint with preview_token = corpusPreview.preview_token
show writer diff and writer confirm token
```

### 10.2 Commit action

After prepare succeeds with `writer_ok=true` and `writer_confirm_token`, enable:

```text
Confirm corpus write
```

Because this is now a real corpus mutation, require a simple UI confirmation guard.

Recommended minimal guard:

- button label initially: `Confirm corpus write`;
- clicking opens/shows a small confirmation panel;
- require user to type or click an explicit second button:

```text
Write corpus file
```

or require typing:

```text
PROMOTE
```

For PR109, a two-click confirmation is acceptable and simpler than text entry. The critical technical guard is the writer confirm token.

On commit success:

- show write success;
- display corpus path;
- display bytes written/fingerprint if available;
- replace current artifact with `response.stored_record.artifact`;
- refresh stored draft list;
- keep ingestion/add-to-combat disabled.

### 10.3 UI panels

Add panel:

```text
Corpus write preparation
```

Display:

- proposed path;
- writer diff in `<pre>`;
- writer confirm token;
- new size bytes;
- warnings/diagnostics;
- clear note: `This is the corpus writer dry-run. No file is written until confirmation.`

After commit, display:

```text
Corpus write result
```

Display:

- corpus display path;
- corpus-relative path;
- bytes written;
- new corpus fingerprint if returned;
- stored record status;
- disabled next actions:
  - Ingest to Semantic Knowledge Layer;
  - Verify retrieval;
  - Add to combat.

### 10.4 State clearing

Clear write preparation/result when:

- generating a new draft;
- rendering a new draft;
- loading another draft;
- storing another draft;
- creating a new promotion preview.

If commit fails, keep the preparation visible so the user can inspect the diff/token and prepare again if stale.

---

## 11. Backend tests

Add focused tests, likely extending:

```text
tests/test_live_statblock_workbench_endpoint.py
```

Add corpus writer tests if not already present:

```text
tests/test_corpus_writer_generated_statblocks.py
```

Use temp live session and temp corpus where possible. Avoid writing to checked-in corpus in tests.

### 11.1 Writer allowlist tests

Assert generated path is allowed for create:

```python
is_writable_corpus_path(
    "Longmont Campaign/Campaign 2/Statblocks/generated/generated_obsidian_thornling.md",
    "create",
)
```

Assert unsafe or broad paths are rejected.

### 11.2 Prepare write returns dry-run diff/token

Flow:

```text
store sample draft
preview corpus promotion
POST /corpus-write/prepare with preview_token
```

Assert:

- status 200;
- schema `dmb_statblock_corpus_write_prepare_v1`;
- `writer_ok is True`;
- `writer_phase == "preview"`;
- `writer_confirm_token` exists;
- `writer_diff` includes proposed markdown title/frontmatter;
- no corpus file exists yet;
- stored draft file unchanged.

### 11.3 Prepare rejects mismatched preview token

Send wrong preview token.

Assert 422 or 409 and no file written.

### 11.4 Commit writes corpus file only with confirm token

Flow:

```text
prepare → get writer_confirm_token
commit with preview_token + writer_confirm_token
```

Assert:

- status 200;
- schema `dmb_statblock_corpus_write_commit_v1`;
- writer phase committed;
- corpus file exists at proposed path under temp corpus root;
- file content equals preview full markdown;
- stored record now reflects corpus promotion:
  - artifact.lifecycle_state == corpus_promoted
  - artifact.corpus_status == promotion_confirmed
  - record.corpus_relpath == proposed path
  - record.corpus_written_at is set
- no ingestion/job/combat mutation occurred.

### 11.5 Commit without valid token fails

Cases:

- missing `writer_confirm_token`;
- wrong `writer_confirm_token`;
- stale token after target file changes;
- target file already exists before prepare/commit.

Assert no stored record status update on failure.

### 11.6 No ingestion/retrieval/combat mutation

Assert:

- no job queue append;
- no event log append;
- no live packet mutation;
- no surface layout mutation;
- no Semantic Knowledge Layer files/state changed;
- only corpus file and stored draft record change on successful commit.

### 11.7 No secret exposure

Set fake env:

```text
DUNGEONBUDDY_INTERNAL_API_KEY=super-secret-test-key
DUNGEONMIND_SERVER_URL=https://example.invalid
```

Call prepare and commit.

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

- `prepareStatblockCorpusWrite(id, { preview_token })` POSTs to encoded prepare endpoint;
- `commitStatblockCorpusWrite(id, { preview_token, writer_confirm_token })` POSTs to encoded commit endpoint.

### 12.2 Component tests

Add tests:

1. Prepare button disabled until corpus promotion preview exists.

2. Prepare corpus write:
   - click Preview corpus promotion;
   - click Prepare corpus write;
   - API called with preview token;
   - writer diff and confirm token render;
   - no commit happens automatically.

3. Confirm corpus write:
   - after prepare, click explicit confirm/write control;
   - API called with preview token + writer confirm token;
   - write result displays path/bytes/fingerprint;
   - current artifact updates to corpus-promoted status;
   - stored drafts list refreshes;
   - ingestion/add-to-combat remain disabled.

4. Prepare failure:
   - existing preview remains visible;
   - safe error appears.

5. Commit failure:
   - prepare diff remains visible;
   - safe error appears;
   - artifact status does not pretend to be promoted.

6. Generating/loading another draft clears prepare/commit state.

No live network.

---

## 13. Manual smoke

Backend:

```bash
uv run uvicorn apps.live_control_server.main:app --reload
```

Create/store/preview:

```bash
curl -s \
  -X POST \
  -H "Content-Type: application/json" \
  http://127.0.0.1:8000/api/live/statblocks/workbench/command \
  -d '{"command_type":"statblock.draft.generate","requested_by":"human","as_artifact":true}' \
  | jq '.artifact' > /tmp/statblock-artifact.json

jq '{artifact: ., source: "workbench"}' /tmp/statblock-artifact.json \
  | curl -s \
      -X POST \
      -H "Content-Type: application/json" \
      http://127.0.0.1:8000/api/live/statblocks/workbench/drafts \
      -d @- \
  | tee /tmp/statblock-store-response.json \
  | jq

ARTIFACT_ID=$(jq -r '.record.artifact_id' /tmp/statblock-store-response.json)

curl -s \
  -X POST \
  -H "Content-Type: application/json" \
  "http://127.0.0.1:8000/api/live/statblocks/workbench/drafts/${ARTIFACT_ID}/corpus-preview" \
  -d '{"include_writer_allowlist_check":true}' \
  | tee /tmp/statblock-preview-response.json \
  | jq

PREVIEW_TOKEN=$(jq -r '.preview_token' /tmp/statblock-preview-response.json)
```

Prepare writer dry-run:

```bash
curl -s \
  -X POST \
  -H "Content-Type: application/json" \
  "http://127.0.0.1:8000/api/live/statblocks/workbench/drafts/${ARTIFACT_ID}/corpus-write/prepare" \
  -d "{\"preview_token\":\"${PREVIEW_TOKEN}\"}" \
  | tee /tmp/statblock-write-prepare-response.json \
  | jq

CONFIRM_TOKEN=$(jq -r '.writer_confirm_token' /tmp/statblock-write-prepare-response.json)
```

Commit writer write:

```bash
curl -s \
  -X POST \
  -H "Content-Type: application/json" \
  "http://127.0.0.1:8000/api/live/statblocks/workbench/drafts/${ARTIFACT_ID}/corpus-write/commit" \
  -d "{\"preview_token\":\"${PREVIEW_TOKEN}\",\"writer_confirm_token\":\"${CONFIRM_TOKEN}\"}" \
  | jq
```

Verify manually:

```text
Corpus markdown file exists at proposed path.
Stored draft record now marks promotion_confirmed.
No ingestion job is queued.
Add-to-combat remains disabled.
```

---

## 14. Testing commands

Suggested backend:

```bash
uv run pytest \
  tests/test_live_statblock_workbench_endpoint.py \
  tests/test_live_session_bootstrap.py \
  tests/test_corpus_writer_generated_statblocks.py \
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
  src/agent/corpus_writer.py \
  apps/live_control_server/services/statblock_corpus_preview.py \
  apps/live_control_server/services/statblock_corpus_write.py \
  apps/live_control_server/services/statblock_draft_store.py \
  apps/live_control_server/routes/live.py \
  tests/test_live_statblock_workbench_endpoint.py \
  tests/test_corpus_writer_generated_statblocks.py

git diff --check
```

If full UI test/build remains blocked by unrelated environment issues, document the caveat in the PR body.

---

## 15. Acceptance criteria

The PR is ready when:

- Corpus writer has a narrow generated-statblock create allowlist.
- Existing corpus writer protections remain intact.
- Prepare endpoint exists and returns writer dry-run diff + writer confirm token.
- Commit endpoint exists and requires preview token + writer confirm token.
- Commit writes exactly one generated statblock markdown file under the allowlisted corpus path.
- Commit refuses stale/wrong/missing confirm tokens.
- Commit refuses existing target files via writer create mode.
- Stored draft record updates after successful write.
- Stored draft record does not update after failed write.
- Responses do not expose host absolute paths or internal secrets.
- Workbench shows prepare diff/token.
- Workbench requires explicit confirmation before commit.
- Workbench shows commit result and promoted status.
- Ingestion/retrieval/add-to-combat remain disabled.
- Tests prove no ingestion/job/combat mutation.
- Focused backend and frontend tests pass.

---

## 16. Suggested PR description

```markdown
### Motivation

PR #108 added corpus promotion preview for stored statblock drafts. This PR adds the explicit confirmed corpus write step using the existing corpus writer's dry-run/confirm-token discipline, while keeping ingestion, retrieval, and combat integration out of scope.

### Description

- Added a narrow generated-statblock create allowlist to `src/agent/corpus_writer.py`.
- Added statblock corpus write prepare/commit service using `write_corpus_file` dry-run and confirm-token commit.
- Added prepare and commit endpoints under `/api/live/statblocks/workbench/drafts/{artifact_id}/corpus-write/*`.
- Prepare returns writer diff, writer confirm token, proposed path, warnings, and diagnostics without writing.
- Commit requires preview token and writer confirm token, writes the generated statblock markdown file, and updates the stored draft record's corpus promotion status.
- Added frontend API/types and Workbench UI for preparing and confirming corpus write.
- Kept ingestion, retrieval verification, Statblock View, and add-to-combat disabled.
- Added backend/frontend tests for allowlist, dry-run, confirmed write, stale token refusal, no secret exposure, and no ingestion/combat mutation.

### Testing

- `uv run pytest tests/test_live_statblock_workbench_endpoint.py tests/test_live_session_bootstrap.py tests/test_corpus_writer_generated_statblocks.py -q`
- `cd apps/live-control-ui && npm test -- src/surface/modules/StatblockWorkbenchModule.test.tsx src/api/liveApi.test.ts`
- `cd apps/live-control-ui && npx tsc -p tsconfig.app.json --noEmit`
- `uv run ruff check src/agent/corpus_writer.py apps/live_control_server/services/statblock_corpus_preview.py apps/live_control_server/services/statblock_corpus_write.py apps/live_control_server/services/statblock_draft_store.py apps/live_control_server/routes/live.py tests/test_live_statblock_workbench_endpoint.py tests/test_corpus_writer_generated_statblocks.py`
- `git diff --check`
```

---

## 17. Design reminder

This PR writes corpus markdown. It does not ingest or retrieve.

The ladder after PR109 should be:

```text
API-backed ✅
Commandable ✅
Visible ✅
Interactive ✅
Persistent draft storage ✅
Corpus promotion preview ✅
Corpus write ⏭️ this PR
Semantic ingestion/retrieval ❌
Combat-usable ❌
Planning-mode-integrated ❌
```

Keep the slice narrow. PR110 should be ingestion/retrieval verification, not combat.
