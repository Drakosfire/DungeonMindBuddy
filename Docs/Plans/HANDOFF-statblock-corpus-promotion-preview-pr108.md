# HANDOFF — Statblock corpus promotion preview PR108

**Created:** 2026-06-09  
**Repo:** `Drakosfire/DungeonMindBuddy`  
**Target base branch:** `main`  
**Suggested next branch:** `codex/statblock-corpus-promotion-preview-pr108`  
**Depends on:** PR #107 / `55cc7b8e1ae81bb9bbdc9f37d497df491e0c8cae` — Add statblock Workbench draft storage  
**Primary design:** `Docs/Design/DESIGN-statblock-lifecycle-agentic-workbench.md`  
**Previous handoffs:**
- `Docs/Plans/HANDOFF-statblock-lifecycle-seam-pr1.md`
- `Docs/Plans/HANDOFF-statblock-lifecycle-command-smoke-pr2.md`
- `Docs/Plans/HANDOFF-statblock-workbench-readonly-pr3.md`
- `Docs/Plans/HANDOFF-statblock-workbench-draft-storage-pr107.md`
**Mode:** Corpus promotion preview only. Generate a reviewable corpus-write preview from a stored draft. Do not write corpus, ingest, retrieve, or mutate combat.

---

## 0. Copyable task prompt

```markdown
You are implementing Statblock Workbench PR108 in `Drakosfire/DungeonMindBuddy`.

Read first:

- `Docs/Plans/HANDOFF-statblock-corpus-promotion-preview-pr108.md`
- `Docs/Design/DESIGN-statblock-lifecycle-agentic-workbench.md`
- `Docs/Plans/HANDOFF-statblock-workbench-draft-storage-pr107.md`
- `src/agent/corpus_writer.py`

Goal: add corpus promotion preview for stored statblock draft artifacts.

PR #107 made `StatblockDraftArtifact` durable as non-corpus JSON drafts under the live session workspace. PR108 should let the Workbench preview what corpus promotion would create: target corpus path, YAML frontmatter, markdown body, breadcrumbs/source refs, promotion warnings, validation status, and a preview token.

Add a server-side preview endpoint for stored drafts, for example:

`POST /api/live/statblocks/workbench/drafts/{artifact_id}/corpus-preview`

The endpoint must read the stored draft record, build a deterministic promotion preview, and return it to the UI. It must not write files, call `write_corpus_file(..., dry_run=False)`, update the stored draft record, trigger ingestion, or mutate combat.

Frontend goal: enable “Preview corpus promotion” for stored drafts, show the proposed corpus path/frontmatter/markdown/breadcrumbs/warnings/token, and keep Confirm/Promote/Ingest/Add-to-combat disabled as future actions.

Do not write to `corpus/`. Do not update the Semantic Knowledge Layer. Do not add to combat. Do not expose `DUNGEONBUDDY_INTERNAL_API_KEY`. This PR previews canonization; the next PR will implement confirmed corpus write.
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
Corpus promotion preview ❌
Corpus write ❌
Semantic ingestion/retrieval ❌
Statblock View ❌
Add to combat ❌
Planning Mode generation tasks ❌
```

PR #107 added:

```text
Displayed StatblockDraftArtifact
→ Store draft
→ <live_session_dir>/statblock_drafts/<artifact_id>.json
→ list/read stored drafts in Workbench
```

PR #108 should add:

```text
Stored draft record
→ corpus promotion preview
→ proposed corpus path + frontmatter + markdown + breadcrumbs + warnings + preview token
```

This is still **not corpus write**.

---

## 2. Product intent

The GM should be able to inspect the exact corpus artifact that would be created before approving any mutation.

Target flow:

```text
Open Statblock Workbench
→ load or store a draft
→ click Preview corpus promotion
→ inspect proposed corpus path
→ inspect proposed frontmatter
→ inspect full markdown preview
→ inspect breadcrumbs/source refs/warnings
→ see Confirm corpus write as disabled/future
```

The Workbench should make it obvious that the draft is **not yet corpus canon** and **not yet retrievable**.

This PR prepares PR109, which should add the explicit confirm/write step.

---

## 3. Design boundary

### PR108 does

- read stored draft records;
- build promotion previews;
- propose a corpus-relative path;
- render frontmatter;
- render full markdown preview;
- include breadcrumbs and source refs;
- produce validation/warning messages;
- produce a preview token for later confirmation design;
- show preview in the Workbench.

### PR108 does not

- write to the markdown corpus;
- call a commit/write endpoint;
- call `write_corpus_file(..., dry_run=False)`;
- mutate stored draft records;
- update `corpus_status` persistently;
- trigger ingestion/reindex;
- verify retrieval;
- create Statblock View entries;
- add anything to combat;
- expose secrets.

### Important writer note

`src/agent/corpus_writer.py` already has a two-phase write model for other corpus workflows. It also currently denies generic `*_statblock*` files and has no dedicated generated-statblock corpus allowlist.

For PR108:

- Do not modify corpus writer allowlists.
- Do not depend on the writer allowing the proposed statblock path.
- It is acceptable, and useful, to call `is_writable_corpus_path(...)` for reporting only.
- If the current writer would reject the proposed statblock path, include that as a preview warning such as: `writer_allowlist_pending`.
- PR109 can add the confirmed write path and any needed corpus-writer allowlist change.

---

## 4. Proposed corpus path strategy

Use corpus-relative paths. Do not include host absolute paths.

Recommended display root:

```text
corpus/eldyrwild-markdown/
```

Recommended corpus-relative path for Campaign 2:

```text
Longmont Campaign/Campaign 2/Statblocks/generated/<slug>.md
```

Example full display path:

```text
corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Statblocks/generated/generated_obsidian_thornling.md
```

### 4.1 Campaign mapping

Use current live packet data:

```python
base = session_dir()
packet, _, _, _ = load_session(base)
campaign_id = packet["campaign_id"]  # e.g. longmont-c2
session = packet["session"]
```

Mapping rule:

```text
longmont-c2 → Longmont Campaign/Campaign 2
longmont-c<N> → Longmont Campaign/Campaign <N>
```

If campaign mapping is unknown, return a preview warning and use a conservative fallback under:

```text
Generated Statblocks/<campaign_id>/<slug>.md
```

But the C2 live path should be supported and tested.

### 4.2 Slug strategy

Create a safe slug from the stored artifact title:

```text
Generated Obsidian Thornling → generated_obsidian_thornling
Rendered Clockwork Mire Sentinel → rendered_clockwork_mire_sentinel
```

Rules:

- lowercase;
- ASCII-ish normalize if easy;
- replace non-alphanumeric runs with `_`;
- trim leading/trailing `_`;
- fallback to artifact id if title slug is empty;
- never allow `/`, `\`, `..`, `~`, absolute paths, or URL-like strings.

Preview path overrides are **out of scope** for PR108. Keep target path deterministic.

---

## 5. Promotion preview model

Add a new backend service:

```text
apps/live_control_server/services/statblock_corpus_preview.py
```

Suggested models:

```python
class StatblockPromotionWarning(BaseModel):
    code: str
    message: str
    severity: Literal["info", "warning", "error"] = "warning"

class StatblockCorpusPromotionPreviewRequest(BaseModel):
    include_writer_allowlist_check: bool = True

class StatblockCorpusPromotionPreviewValidation(BaseModel):
    ok: bool
    proposed_path_safe: bool
    writer_allowed_now: bool | None = None
    writer_reason: str | None = None

class StatblockCorpusPromotionPreviewResponse(BaseModel):
    schema_version: Literal["dmb_statblock_corpus_promotion_preview_v1"] = "dmb_statblock_corpus_promotion_preview_v1"
    preview_id: str
    artifact_id: str
    draft_id: str
    title: str
    campaign_id: str
    session: int
    source_record_path: str
    corpus_root_display: str = "corpus/eldyrwild-markdown"
    proposed_corpus_relpath: str
    proposed_corpus_display_path: str
    frontmatter: dict[str, Any]
    frontmatter_text: str
    markdown_body: str
    full_markdown: str
    breadcrumbs: list[StatblockBreadcrumb]
    source_refs: list[SourceRef]
    combat_defaults: CombatDefaults
    warnings: list[StatblockPromotionWarning] = Field(default_factory=list)
    validation: StatblockCorpusPromotionPreviewValidation
    preview_token: str
    diagnostics: list[str] = Field(default_factory=list)
    available_actions: list[StatblockWorkbenchAction] = Field(default_factory=list)
```

### 5.1 Preview token

The preview token is not a commit token yet. It is a stable proof that the preview was built from specific inputs.

Compute from:

```text
artifact_id
draft_id
stored record updated_at
proposed_corpus_relpath
full_markdown hash
```

Use a deterministic hash already available in the repo if convenient, or stdlib `hashlib.sha256(...).hexdigest()[:32]`.

Name it `preview_token`, not `confirm_token`, so it is not confused with `corpus_writer.write_corpus_file` commit tokens.

PR109 can decide whether to convert preview tokens into confirm/write tokens.

---

## 6. Frontmatter design

Use YAML frontmatter text at the top of the proposed markdown file.

Do not add a YAML dependency unless one already exists. A small deterministic frontmatter renderer is fine because fields are controlled.

Suggested frontmatter dictionary:

```yaml
---
schema_version: dmb_corpus_statblock_v1
document_class: statblock
source_type: generated_statblock_draft
title: Generated Obsidian Thornling
campaign_id: longmont-c2
campaign_number: 2
session: 22
artifact_id: statblock-draft-...
draft_id: mock-generated-obsidian-thornling
review_status: needs_dm_review
lifecycle_state: stored_artifact
storage_status: stored_draft
corpus_status: promotion_previewed
created_by: human
created_at: "2026-06-09T...Z"
updated_at: "2026-06-09T...Z"
generated_by: dungeonbuddy_statblock_workbench
statblock_generator: mock-statblock-generator
challenge_rating: "2"
creature_type: plant
source_record_path: statblock_drafts/statblock-draft-....json
breadcrumbs:
  - surface:statblock_workbench
  - source:mock_provider
source_refs:
  - sample-source-obsidian-thornling
---
```

Minimum required fields:

- `schema_version`;
- `document_class`;
- `source_type`;
- `title`;
- `campaign_id`;
- `session`;
- `artifact_id`;
- `draft_id`;
- `corpus_status: promotion_previewed`;
- `generated_by`;
- `source_record_path`;
- `breadcrumbs`.

### 6.1 Breadcrumb rendering

Keep both machine-readable and human-readable breadcrumb information.

In frontmatter, breadcrumbs can be compact strings or objects.

In markdown body, add a section:

```markdown
## Corpus Breadcrumbs

- `surface:statblock_workbench` — live_control_ui
- `source:mock_provider` — mock_provider
```

If breadcrumbs are missing, add a warning:

```text
missing_breadcrumbs
```

Do not silently promote an un-breadcrumbed artifact as clean.

---

## 7. Markdown body design

The full corpus preview should not be only raw statblock markdown. It should wrap the statblock in enough campaign context to be useful later.

Suggested body:

```markdown
# Generated Obsidian Thornling

> Generated statblock draft promoted from DungeonBuddy Workbench preview. Review before corpus write.

## Status

- Review status: needs_dm_review
- Source artifact: `statblock-draft-...`
- Draft id: `mock-generated-obsidian-thornling`
- Corpus status: promotion_previewed

## Combat Defaults

- AC: 14
- HP: 45
- Initiative: +3
- Passive Perception: 12
- Speed: 35 ft., climb 20 ft.
- Primary actions: Splinter Thorn, Root Snare

## Statblock

<artifact.markdown>

## Review Warnings

- WARNING `generated_mock_needs_dm_review`: Review root restraint wording before table use.

## Corpus Breadcrumbs

...

## Provenance

```json
{ ... compact provenance ... }
```
```

This gives the future Semantic Knowledge Layer richer retrieval material than a bare statblock.

---

## 8. Backend endpoint

Add endpoint in `apps/live_control_server/routes/live.py`:

```text
POST /api/live/statblocks/workbench/drafts/{artifact_id}/corpus-preview
```

Request body:

```json
{
  "include_writer_allowlist_check": true
}
```

Response: `StatblockCorpusPromotionPreviewResponse`.

Behavior:

1. Resolve current `session_dir()`.
2. Load current live packet for `campaign_id` and `session`.
3. Read stored draft using `read_statblock_draft(...)`.
4. Build promotion preview from stored record.
5. Return preview.
6. Do not write any file.
7. Do not update the stored draft JSON.
8. Do not queue jobs.
9. Do not trigger ingestion.

Errors:

```text
404 stored draft not found
422 unsafe artifact id
500 unexpected preview build failure
```

Keep errors safe. Do not include host absolute paths.

---

## 9. Backend service behavior

Suggested functions:

```python
def build_statblock_corpus_promotion_preview(
    *,
    base: Path,
    packet: dict[str, Any],
    artifact_id: str,
    include_writer_allowlist_check: bool = True,
) -> StatblockCorpusPromotionPreviewResponse: ...
```

Internal helpers:

```python
def slugify_statblock_title(title: str, fallback: str) -> str: ...
def campaign_corpus_prefix(campaign_id: str) -> tuple[str, list[StatblockPromotionWarning]]: ...
def proposed_statblock_corpus_relpath(campaign_id: str, title: str, artifact_id: str) -> str: ...
def render_statblock_frontmatter(record, packet, relpath) -> tuple[dict[str, Any], str]: ...
def render_statblock_markdown_body(record, warnings) -> str: ...
def build_preview_token(record, relpath, full_markdown) -> str: ...
```

### 9.1 Corpus writer reporting

If importing from `src.agent.corpus_writer` is lightweight enough, call:

```python
from src.agent.corpus_writer import is_writable_corpus_path

writer_allowed_now, writer_reason = is_writable_corpus_path(proposed_relpath, "create")
```

Do not call `write_corpus_file` in PR108.

If the writer reports false, include:

```text
warning code: writer_allowlist_pending
message: Current corpus writer allowlist does not yet permit this generated statblock path; PR109 must add/confirm the write allowlist before commit.
severity: info or warning
```

This keeps preview honest without blocking the UX.

---

## 10. Frontend API/types

Update:

```text
apps/live-control-ui/src/api/types.ts
apps/live-control-ui/src/api/liveApi.ts
apps/live-control-ui/src/api/liveApi.test.ts
```

Suggested TypeScript types:

```ts
export interface StatblockPromotionWarning {
  code: string;
  message: string;
  severity: "info" | "warning" | "error";
}

export interface StatblockCorpusPromotionPreviewRequest {
  include_writer_allowlist_check?: boolean;
}

export interface StatblockCorpusPromotionPreviewValidation {
  ok: boolean;
  proposed_path_safe: boolean;
  writer_allowed_now?: boolean | null;
  writer_reason?: string | null;
}

export interface StatblockCorpusPromotionPreviewResponse {
  schema_version: "dmb_statblock_corpus_promotion_preview_v1";
  preview_id: string;
  artifact_id: string;
  draft_id: string;
  title: string;
  campaign_id: string;
  session: number;
  source_record_path: string;
  corpus_root_display: string;
  proposed_corpus_relpath: string;
  proposed_corpus_display_path: string;
  frontmatter: Record<string, unknown>;
  frontmatter_text: string;
  markdown_body: string;
  full_markdown: string;
  breadcrumbs: StatblockBreadcrumb[];
  source_refs: Array<Record<string, unknown>>;
  combat_defaults: StatblockCombatDefaults;
  warnings: StatblockPromotionWarning[];
  validation: StatblockCorpusPromotionPreviewValidation;
  preview_token: string;
  diagnostics: string[];
  available_actions: StatblockWorkbenchAction[];
}
```

API helper:

```ts
export async function previewStatblockCorpusPromotion(
  artifactId: string,
  request: StatblockCorpusPromotionPreviewRequest = {},
): Promise<StatblockCorpusPromotionPreviewResponse> {
  return apiFetch<StatblockCorpusPromotionPreviewResponse>(
    `/api/live/statblocks/workbench/drafts/${encodeURIComponent(artifactId)}/corpus-preview`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    },
  );
}
```

---

## 11. Frontend Workbench behavior

Update:

```text
apps/live-control-ui/src/surface/modules/StatblockWorkbenchModule.tsx
```

### 11.1 Preview action

Enable a real `Preview corpus promotion` control only when:

- a current artifact exists;
- `artifact.storage_status === "stored_draft"`;
- no command/store/load/preview is pending.

If the current artifact is not stored, show disabled helper text:

```text
Store this draft before previewing corpus promotion.
```

### 11.2 Preview panel

After successful preview, show a new panel:

```text
Corpus promotion preview
```

Display:

- proposed corpus display path;
- corpus-relative path;
- validation status;
- preview token;
- warnings;
- frontmatter text in a `<pre>` block;
- full markdown preview in a `<pre>` block;
- breadcrumbs/source refs summary;
- diagnostics.

### 11.3 Future actions

After preview, show these actions but keep them disabled:

```text
Confirm corpus write — disabled: future PR will require explicit confirmation token.
Ingest to Semantic Knowledge Layer — disabled until corpus write exists.
Add to combat — disabled until corpus-backed Statblock View/combat integration exists.
```

Do not add any write/confirm handler in this PR.

### 11.4 State clearing

Clear preview state when:

- generating a new draft;
- rendering a new draft;
- loading a different stored draft;
- store fails.

Do not clear the preview on minor list refreshes.

---

## 12. Backend tests

Add focused tests, likely extending:

```text
tests/test_live_statblock_workbench_endpoint.py
```

Use the temp live session setup introduced around PR107. Do not write into checked-in `session_22`.

### 12.1 Preview stored draft

Flow:

```text
GET /api/live/statblocks/workbench/sample
POST /api/live/statblocks/workbench/drafts
POST /api/live/statblocks/workbench/drafts/{artifact_id}/corpus-preview
```

Assert:

- status 200;
- schema version `dmb_statblock_corpus_promotion_preview_v1`;
- proposed path starts with `Longmont Campaign/Campaign 2/Statblocks/generated/`;
- proposed display path starts with `corpus/eldyrwild-markdown/`;
- frontmatter text starts and ends with `---` block;
- full markdown includes frontmatter and artifact markdown;
- breadcrumbs/source refs are included;
- preview token is non-empty;
- diagnostics say no corpus write/ingestion/combat mutation occurred.

### 12.2 Preview does not mutate files

Snapshot temp live session and repo corpus area if practical.

Assert after preview:

- stored draft file unchanged;
- `live_packet.json` unchanged;
- `surface_layout.json` unchanged;
- `event_log.jsonl` unchanged;
- `job_queue.jsonl` unchanged;
- no new corpus file exists at proposed display path.

### 12.3 Missing draft returns 404

```text
POST /api/live/statblocks/workbench/drafts/not-found/corpus-preview
```

Assert 404.

### 12.4 Unsafe ID returns 422

Test URL-encoded unsafe IDs if FastAPI routing allows, or call service directly for unsafe ID cases.

Examples:

```text
../evil
nested/path
~/.ssh/id_rsa
https://evil
```

### 12.5 Missing breadcrumbs warning

Store a draft with empty breadcrumbs.

Preview should return warning code:

```text
missing_breadcrumbs
```

### 12.6 Writer allowlist report

If the service calls `is_writable_corpus_path`, assert response includes `writer_allowed_now` and, if false, a warning like `writer_allowlist_pending`.

Do not make this warning a failure.

### 12.7 No secret exposure

Set fake env:

```text
DUNGEONBUDDY_INTERNAL_API_KEY=super-secret-test-key
DUNGEONMIND_SERVER_URL=https://example.invalid
```

Call preview.

Assert response text does not contain:

```text
super-secret-test-key
DUNGEONBUDDY_INTERNAL_API_KEY
DUNGEONMIND_SERVER_URL
X-DungeonBuddy-Internal-Key
```

---

## 13. Frontend tests

Update:

```text
apps/live-control-ui/src/api/liveApi.test.ts
apps/live-control-ui/src/surface/modules/StatblockWorkbenchModule.test.tsx
```

### 13.1 API helper

Assert:

- `previewStatblockCorpusPromotion("statblock:draft test")` POSTs to encoded route;
- body includes request options;
- method and content type are correct.

### 13.2 Component behavior

Add tests:

1. Preview button disabled for unstored draft.

2. After storing current draft, Preview corpus promotion becomes enabled.

3. Clicking Preview:
   - calls `previewStatblockCorpusPromotion(artifact_id, ...)`;
   - shows pending state;
   - renders proposed path/frontmatter/full markdown/preview token;
   - keeps Confirm corpus write / Ingest / Add to combat disabled.

4. Preview failure:
   - existing artifact remains visible;
   - safe error message appears.

5. Loading a different stored draft clears the previous preview.

No live network.

---

## 14. Manual smoke

Backend:

```bash
uv run uvicorn apps.live_control_server.main:app --reload
```

Create and store an artifact:

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
```

Preview promotion:

```bash
ARTIFACT_ID=$(jq -r '.record.artifact_id' /tmp/statblock-store-response.json)

curl -s \
  -X POST \
  -H "Content-Type: application/json" \
  "http://127.0.0.1:8000/api/live/statblocks/workbench/drafts/${ARTIFACT_ID}/corpus-preview" \
  -d '{"include_writer_allowlist_check":true}' \
  | jq
```

Frontend:

```bash
cd apps/live-control-ui
npm run dev
```

Verify:

```text
Store draft works.
Preview corpus promotion becomes enabled after storage.
Preview shows proposed path/frontmatter/full markdown/token/warnings.
Confirm corpus write remains disabled.
No corpus file is created.
No ingestion or combat mutation occurs.
```

---

## 15. Testing commands

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
  apps/live_control_server/services/statblock_corpus_preview.py \
  apps/live_control_server/routes/live.py \
  tests/test_live_statblock_workbench_endpoint.py

git diff --check
```

If full UI test/build remains blocked by unrelated environment issues, document the caveat in the PR body.

---

## 16. Acceptance criteria

The PR is ready when:

- A corpus promotion preview service exists.
- A preview endpoint exists at `/api/live/statblocks/workbench/drafts/{artifact_id}/corpus-preview` or equivalent.
- Preview reads stored draft records and current live packet context.
- Preview proposes a deterministic corpus-relative path.
- Preview renders frontmatter text.
- Preview renders full markdown including frontmatter and artifact markdown.
- Preview includes breadcrumbs, source refs, combat defaults, warnings, validation status, diagnostics, and preview token.
- Preview reports whether the current corpus writer allowlist would accept the path, if implemented.
- Preview does not write files.
- Preview does not update stored draft records.
- Preview does not append events/jobs.
- Preview does not trigger ingestion.
- Preview does not mutate combat state.
- Preview responses do not expose internal secrets or host absolute paths.
- Workbench enables Preview corpus promotion only for stored drafts.
- Workbench displays preview path/frontmatter/full markdown/warnings/token.
- Confirm corpus write / ingest / add-to-combat remain disabled.
- Focused backend and frontend tests pass.

---

## 17. Suggested PR description

```markdown
### Motivation

PR #107 made Statblock Workbench artifacts durable as non-corpus draft records. This PR adds the next lifecycle step: previewing corpus promotion from a stored draft without writing to the corpus, ingesting, or mutating combat.

### Description

- Added a statblock corpus promotion preview service that reads stored draft records and builds proposed corpus path/frontmatter/markdown previews.
- Added `POST /api/live/statblocks/workbench/drafts/{artifact_id}/corpus-preview`.
- Rendered promotion preview fields: proposed corpus path, frontmatter text, markdown body, full markdown, breadcrumbs, source refs, combat defaults, validation, warnings, diagnostics, and preview token.
- Reported current corpus-writer allowlist status without performing any write.
- Added frontend API/types and Workbench UI for Preview corpus promotion.
- Kept Confirm corpus write, ingestion, and add-to-combat disabled.
- Added backend/frontend tests proving preview content and no mutation.

### Testing

- `uv run pytest tests/test_live_statblock_workbench_endpoint.py tests/test_live_session_bootstrap.py -q`
- `cd apps/live-control-ui && npm test -- src/surface/modules/StatblockWorkbenchModule.test.tsx src/api/liveApi.test.ts`
- `cd apps/live-control-ui && npx tsc -p tsconfig.app.json --noEmit`
- `uv run ruff check apps/live_control_server/services/statblock_workbench.py apps/live_control_server/services/statblock_draft_store.py apps/live_control_server/services/statblock_corpus_preview.py apps/live_control_server/routes/live.py tests/test_live_statblock_workbench_endpoint.py`
- `git diff --check`
```

---

## 18. Design reminder

This PR previews corpus promotion. It does not promote.

The ladder after PR108 should be:

```text
API-backed ✅
Commandable ✅
Visible ✅
Interactive ✅
Persistent draft storage ✅
Corpus promotion preview ⏭️ this PR
Corpus write ❌
Semantic ingestion/retrieval ❌
Combat-usable ❌
Planning-mode-integrated ❌
```

The next PR should be explicit confirmed corpus write, using preview/confirm discipline. Do not merge preview and write into one slice.
