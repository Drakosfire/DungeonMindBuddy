# HANDOFF — Statblock View read-only PR111

**Created:** 2026-06-09  
**Repo:** `Drakosfire/DungeonMindBuddy`  
**Target base branch:** `main`  
**Suggested next branch:** `codex/statblock-view-readonly-pr111`  
**Depends on:** PR #110 / `222a3a5c5f25b80ace1a29ef588ee3c66061fec9` — Activate generated statblock retrieval  
**Primary design:** `Docs/Design/DESIGN-statblock-lifecycle-agentic-workbench.md`  
**Previous handoffs:**
- `Docs/Plans/HANDOFF-statblock-lifecycle-seam-pr1.md`
- `Docs/Plans/HANDOFF-statblock-lifecycle-command-smoke-pr2.md`
- `Docs/Plans/HANDOFF-statblock-workbench-readonly-pr3.md`
- `Docs/Plans/archive/2026-06-22/handoffs/HANDOFF-statblock-workbench-draft-storage-pr107.md`
- `Docs/Plans/archive/2026-06-22/handoffs/HANDOFF-statblock-corpus-promotion-preview-pr108.md`
- `Docs/Plans/archive/2026-06-22/handoffs/HANDOFF-statblock-corpus-confirmed-write-pr109.md`
- `Docs/Plans/archive/2026-06-22/handoffs/HANDOFF-statblock-retrieval-activation-pr110.md`
**Mode:** Read-only consumer surface. Build a corpus-backed generated Statblock View that can list and read verified generated statblocks. Do not add to combat yet.

---

## 0. Copyable task prompt

```markdown
You are implementing Statblock View PR111 in `Drakosfire/DungeonMindBuddy`.

Read first:

- `Docs/Plans/archive/2026-06-22/handoffs/HANDOFF-statblock-view-readonly-pr111.md`
- `Docs/Plans/archive/2026-06-22/handoffs/HANDOFF-statblock-retrieval-activation-pr110.md`
- `Docs/Plans/archive/2026-06-22/handoffs/HANDOFF-statblock-corpus-confirmed-write-pr109.md`
- `Docs/Design/DESIGN-statblock-lifecycle-agentic-workbench.md`
- `apps/live_control_server/services/statblock_draft_store.py`
- `apps/live_control_server/services/statblock_retrieval_activation.py`
- `apps/live-control-ui/src/surface/moduleRegistry.tsx`

Goal: build a read-only Statblock View over corpus-backed generated statblocks.

PR110 made generated statblocks retrievable/admissible through the manifest-backed retrieval layer. PR111 should add the first consumer surface: a dedicated Statblock View module that lists corpus-promoted/generated statblocks, lets the user select one, reads its stored draft metadata plus corpus markdown, and displays a clean read-only statblock detail view.

Add server-side endpoints such as:

- `GET /api/live/statblocks/view/generated`
- `GET /api/live/statblocks/view/generated/{artifact_id}`

The list should include only stored drafts that have confirmed corpus write metadata, and should show retrieval status where available. The detail endpoint should return the stored record, corpus path metadata, corpus markdown/full text, combat defaults, warnings, provenance, breadcrumbs, retrieval metadata, and disabled future actions.

Frontend goal: add a `StatblockViewModule` and register it as an optional surface module. It should display a generated statblock list and read-only detail view. It may include an “Open selected in Workbench” affordance only if cheap/read-only, but it must not mutate Workbench state.

Do not add to combat. Do not mutate combat. Do not write corpus. Do not trigger ingestion. Do not call DungeonMindServer generation. Do not expose internal secrets.
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
Confirmed corpus write ✅
Retrieval activation/verification ✅
Statblock View ❌
Add to combat ❌
Planning Mode generation tasks ❌
```

PR #110 added:

```text
confirmed generated statblock corpus file
→ session-scoped generated-statblock manifest overlay
→ retrieval verification through build_context_packet(...)
→ stored draft retrieval metadata
```

PR #111 should add:

```text
corpus-backed generated statblocks
→ list/read API
→ read-only Statblock View module
→ clear bridge toward future Add to Combat
```

This PR still does **not** add to combat.

---

## 2. Product intent

The Workbench proves the lifecycle. The Statblock View is the first actual consumer surface.

The GM should be able to open the live command board, enable/select Statblock View, and see generated statblocks that have made it into the corpus-backed path.

Target user-visible flow:

```text
Open command board
→ enable Statblock View
→ see generated corpus-backed statblocks
→ select Geomantic Drake Juvenile
→ read markdown/statblock details
→ see combat defaults, warnings, provenance, breadcrumbs, corpus path, retrieval status
→ Add to combat is visible but disabled/future
```

This provides a stable place for PR112 to add combat integration.

---

## 3. Design boundary

### PR111 does

- create a read-only server view service;
- list generated statblocks from stored draft records;
- filter to corpus-backed/promoted records;
- read corpus markdown text from the confirmed corpus path;
- return stored metadata + corpus text + combat defaults;
- add a dedicated Statblock View frontend module;
- register the module in the surface registry and default catalog/layout as optional/hidden;
- show read-only detail state;
- show disabled future actions for Add to Combat.

### PR111 does not

- generate statblocks;
- store drafts;
- write corpus;
- activate retrieval;
- verify retrieval;
- mutate event/job/combat state;
- add monsters to combat;
- build initiative cards;
- edit markdown;
- import arbitrary external statblocks;
- add a global search engine beyond the current generated statblock list/filter.

---

## 4. Source of truth for PR111

Use the stored draft records as the index of generated statblocks because they already carry:

```text
artifact_id
title
corpus_relpath
corpus_display_path
corpus_written_at
corpus_preview_token
retrieval_status
retrieval_manifest_path
retrieval_activated_at
retrieval_verified_at
retrieval_query
retrieval_evidence_path
retrieval_evidence_score
artifact.combat_defaults
artifact.warnings
artifact.provenance
artifact.breadcrumbs
```

Read the markdown file from:

```text
<repo_root>/corpus/eldyrwild-markdown/<record.corpus_relpath>
```

Do not parse the manifest overlay as the main list source. The overlay is retrieval activation state; the stored records are the lifecycle registry.

---

## 5. Backend service design

Add a service module:

```text
apps/live_control_server/services/statblock_view.py
```

Suggested models:

```python
class GeneratedStatblockListItem(BaseModel):
    artifact_id: str
    draft_id: str
    title: str
    campaign_id: str
    session: int
    review_status: str
    lifecycle_state: str
    storage_status: str
    corpus_status: str
    retrieval_status: str | None = None
    corpus_relpath: str
    corpus_display_path: str
    corpus_written_at: str | None = None
    retrieval_verified_at: str | None = None
    armor_class: int | str | None = None
    hit_points: int | str | None = None
    challenge_rating: str | None = None
    creature_type: str | None = None
    primary_actions: list[str] = Field(default_factory=list)
    warning_count: int = 0

class GeneratedStatblockListResponse(BaseModel):
    schema_version: Literal["dmb_generated_statblock_list_v1"] = "dmb_generated_statblock_list_v1"
    statblocks: list[GeneratedStatblockListItem]
    diagnostics: list[str] = Field(default_factory=list)

class GeneratedStatblockDetailResponse(BaseModel):
    schema_version: Literal["dmb_generated_statblock_detail_v1"] = "dmb_generated_statblock_detail_v1"
    artifact_id: str
    draft_id: str
    title: str
    stored_record: StoredStatblockDraftRecord
    corpus_relpath: str
    corpus_display_path: str
    corpus_markdown: str
    corpus_markdown_bytes: int
    corpus_file_fingerprint: str | None = None
    combat_defaults: CombatDefaults
    warnings: list[ReviewWarning]
    provenance: dict[str, Any]
    breadcrumbs: list[StatblockBreadcrumb]
    source_refs: list[SourceRef]
    retrieval: dict[str, Any]
    available_actions: list[StatblockWorkbenchAction] = Field(default_factory=list)
    diagnostics: list[str] = Field(default_factory=list)
```

Use existing artifact model classes if import paths are clear; otherwise keep view models permissive enough to serialize the current `StatblockDraftArtifact` fields.

Suggested functions:

```python
def list_generated_statblocks(*, base: Path, root: Path) -> GeneratedStatblockListResponse: ...

def read_generated_statblock(*, base: Path, root: Path, artifact_id: str) -> GeneratedStatblockDetailResponse: ...
```

---

## 6. Backend behavior

### 6.1 List behavior

List generated statblocks by reading existing records under:

```text
<live_session_dir>/statblock_drafts/*.json
```

Include only records where:

```text
record.artifact.corpus_status == "promotion_confirmed"
record.corpus_relpath is not empty
```

For each record:

- verify the corpus file exists;
- include warning/diagnostic if missing, but do not crash the whole list;
- summarize combat defaults;
- summarize structured statblock fields if present:
  - `challenge_rating`;
  - `creature_type`;
  - `name`;
- include retrieval status fields;
- sort by `corpus_written_at` descending, fallback `updated_at` descending, fallback title.

Do not include full markdown in the list response.

### 6.2 Detail behavior

Read one generated statblock by `artifact_id`.

Validate:

- safe artifact id through existing draft store validation path;
- record exists;
- record has `corpus_status == promotion_confirmed`;
- record has `corpus_relpath`;
- corpus file exists under repo corpus root.

Return:

- stored record;
- corpus markdown text;
- corpus path metadata;
- combat defaults from the artifact;
- warnings/provenance/breadcrumbs/source refs;
- retrieval metadata;
- future actions:
  - `add_to_combat` disabled for PR112;
  - `open_in_workbench` maybe disabled or informational;
  - `refresh_retrieval_verification` disabled unless you intentionally wire it to PR110 endpoint, but prefer not to.

### 6.3 Missing states

Error mapping:

```text
404 stored draft not found
409 generated statblock is not corpus-promoted
409 corpus file missing
422 unsafe artifact id
500 unexpected read failure
```

Do not expose absolute host paths in normal responses or errors.

### 6.4 Fingerprint

If cheap, include a fingerprint of corpus markdown:

```text
sha256(full_markdown)[:16 or 32]
```

This helps later combat/cache slices know what exact corpus file was viewed.

---

## 7. Live-control endpoints

Add endpoints in `apps/live_control_server/routes/live.py`:

```text
GET /api/live/statblocks/view/generated
GET /api/live/statblocks/view/generated/{artifact_id}
```

Route behavior:

```python
base = session_dir()
root = repo_root()
```

Then delegate to `statblock_view.py`.

Do not wire these through Workbench command endpoints.

---

## 8. Frontend API/types

Update:

```text
apps/live-control-ui/src/api/types.ts
apps/live-control-ui/src/api/liveApi.ts
apps/live-control-ui/src/api/liveApi.test.ts
```

Suggested TypeScript types:

```ts
export interface GeneratedStatblockListItem {
  artifact_id: string;
  draft_id: string;
  title: string;
  campaign_id: string;
  session: number;
  review_status: string;
  lifecycle_state: string;
  storage_status: string;
  corpus_status: string;
  retrieval_status?: string | null;
  corpus_relpath: string;
  corpus_display_path: string;
  corpus_written_at?: string | null;
  retrieval_verified_at?: string | null;
  armor_class?: number | string | null;
  hit_points?: number | string | null;
  challenge_rating?: string | null;
  creature_type?: string | null;
  primary_actions: string[];
  warning_count: number;
}

export interface GeneratedStatblockListResponse {
  schema_version: "dmb_generated_statblock_list_v1";
  statblocks: GeneratedStatblockListItem[];
  diagnostics: string[];
}

export interface GeneratedStatblockDetailResponse {
  schema_version: "dmb_generated_statblock_detail_v1";
  artifact_id: string;
  draft_id: string;
  title: string;
  stored_record: StoredStatblockDraftRecord;
  corpus_relpath: string;
  corpus_display_path: string;
  corpus_markdown: string;
  corpus_markdown_bytes: number;
  corpus_file_fingerprint?: string | null;
  combat_defaults: StatblockCombatDefaults;
  warnings: StatblockReviewWarning[];
  provenance: Record<string, unknown>;
  breadcrumbs: StatblockBreadcrumb[];
  source_refs: Array<Record<string, unknown>>;
  retrieval: Record<string, unknown>;
  available_actions: StatblockWorkbenchAction[];
  diagnostics: string[];
}
```

API helpers:

```ts
export async function listGeneratedStatblocks(): Promise<GeneratedStatblockListResponse> { ... }

export async function getGeneratedStatblock(
  artifactId: string,
): Promise<GeneratedStatblockDetailResponse> { ... }
```

Use `encodeURIComponent(artifactId)`.

---

## 9. Frontend module design

Add:

```text
apps/live-control-ui/src/surface/modules/StatblockViewModule.tsx
```

Register in:

```text
apps/live-control-ui/src/surface/moduleRegistry.tsx
```

Add optional module catalog/layout entry in:

```text
src/live_play/session_bootstrap.py
```

Suggested module id:

```text
statblock_view
```

Catalog entry:

```json
{
  "module_id": "statblock_view",
  "title": "Statblock View",
  "default_slot": "main",
  "required": false,
  "enabled_by_default": false,
  "description": "Read-only corpus-backed generated statblock viewer.",
  "config_schema": null
}
```

Layout entry should be disabled by default, like the Workbench.

---

## 10. Statblock View UI behavior

### 10.1 Loading/list state

On mount:

```text
GET /api/live/statblocks/view/generated
```

Show:

- loading state;
- error state;
- empty state: `No corpus-backed generated statblocks yet.`;
- diagnostics if present.

### 10.2 List UI

List each item with:

- title;
- AC / HP / CR;
- creature type;
- primary actions;
- corpus status;
- retrieval status;
- warning count;
- corpus written timestamp;
- corpus display path.

Clicking an item loads detail:

```text
GET /api/live/statblocks/view/generated/{artifact_id}
```

Default selection behavior:

- If the list is non-empty, auto-select the first item or show “Select a statblock.”
- Preference: auto-select first item for GM utility.

### 10.3 Detail UI

Detail sections:

```text
Header / status rail
Combat summary
Corpus markdown preview
Warnings needing DM review
Retrieval status
Provenance / source refs / breadcrumbs
Disabled future actions
```

Use `corpus_markdown` as the markdown body. Do not add a markdown-rendering dependency; use readable `<pre>`/pre-wrap for now.

### 10.4 Future action affordances

Show but disable:

```text
Add to current combat
Create encounter copy
Refresh retrieval verification
Edit statblock
```

Only `Add to current combat` is on the near-term roadmap. The others are optional if they clutter the UI; keep it minimal.

### 10.5 Link from Workbench

Optional and only if cheap:

- After retrieval verified or corpus write result, Workbench may show text:

```text
Open Statblock View module to browse corpus-backed statblocks.
```

Do not make Workbench directly mutate/select the Statblock View in this PR unless there is already cross-module state infrastructure.

---

## 11. State/status rules

The Statblock View should treat corpus-backed generated statblocks as read-only records.

Display states:

```text
corpus_status = promotion_confirmed → corpus-backed
retrieval_status = retrieval_verified → retrieval verified
retrieval_status = manifest_activated → activated but not verified
retrieval_status missing/null → corpus-backed but retrieval not activated
```

Do not require retrieval verification to list a statblock. A corpus-written statblock is viewable even if retrieval verification has not happened.

But visually distinguish:

```text
Corpus-backed ✅
Retrieval verified ✅ / pending / not activated
Combat-ready ❌ future PR
```

---

## 12. Backend tests

Add/extend tests:

```text
tests/test_statblock_view.py
```

or extend:

```text
tests/test_live_statblock_workbench_endpoint.py
```

Prefer a new test file if the Workbench endpoint test is getting large.

Use temp live session and temp corpus roots. Do not write to checked-in corpus.

### 12.1 List only corpus-promoted generated statblocks

Setup:

- stored non-promoted draft;
- corpus-promoted draft with corpus file;
- maybe corpus-promoted draft with missing corpus file.

Assert:

- non-promoted draft is not included;
- corpus-promoted draft is included;
- list response has summary fields;
- no full markdown in list item;
- diagnostics report missing file if applicable.

### 12.2 Read detail returns corpus markdown and metadata

Setup corpus-promoted draft with actual corpus file.

Assert:

- status 200;
- schema `dmb_generated_statblock_detail_v1`;
- `corpus_markdown` contains the statblock title/body;
- combat defaults preserved;
- warnings/provenance/breadcrumbs/source refs present;
- retrieval metadata present;
- available actions include disabled `add_to_combat`.

### 12.3 Read rejects non-promoted draft

Stored draft without confirmed corpus write.

Assert 409.

### 12.4 Missing corpus file returns 409

Record says promoted but corpus file is missing.

Assert 409 and no absolute path leakage.

### 12.5 Unsafe/missing artifact ids

Cover:

```text
unsafe id → 422
unknown id → 404
```

### 12.6 No mutation

For list/read, snapshot session dir and corpus dir before/after.

Assert no files change.

### 12.7 No secret exposure

Set fake env:

```text
DUNGEONBUDDY_INTERNAL_API_KEY=super-secret-test-key
DUNGEONMIND_SERVER_URL=https://example.invalid
```

Call list/read.

Assert response text does not contain:

```text
super-secret-test-key
DUNGEONBUDDY_INTERNAL_API_KEY
DUNGEONMIND_SERVER_URL
X-DungeonBuddy-Internal-Key
```

---

## 13. Frontend tests

Add/update:

```text
apps/live-control-ui/src/api/liveApi.test.ts
apps/live-control-ui/src/surface/modules/StatblockViewModule.test.tsx
```

### 13.1 API helper tests

Assert:

- `listGeneratedStatblocks()` GETs `/api/live/statblocks/view/generated`;
- `getGeneratedStatblock(id)` GETs encoded `/api/live/statblocks/view/generated/{artifact_id}`.

### 13.2 Module tests

Test cases:

1. Empty state.
   - API returns empty list.
   - Shows `No corpus-backed generated statblocks yet.`

2. List and auto-detail load.
   - API list returns one item.
   - Detail endpoint returns corpus markdown.
   - UI shows title, AC, HP, CR, corpus path, markdown, retrieval status.

3. Select different statblock.
   - List returns two items.
   - Click second.
   - Detail updates.

4. Detail failure.
   - List remains visible.
   - Safe error displays.

5. Add to combat disabled.
   - Button exists and is disabled.

6. Loading/error state.
   - List fetch failure shows module error.

No live network.

---

## 14. Manual smoke

Backend:

```bash
uv run uvicorn apps.live_control_server.main:app --reload
```

After creating a corpus-backed generated statblock through PR109/PR110 flow:

```bash
curl -s http://127.0.0.1:8000/api/live/statblocks/view/generated | jq

ARTIFACT_ID="<artifact id>"

curl -s "http://127.0.0.1:8000/api/live/statblocks/view/generated/${ARTIFACT_ID}" | jq
```

Frontend:

```bash
cd apps/live-control-ui
npm run dev
```

Verify:

```text
Enable Statblock View from hidden modules.
Generated statblock appears in list.
Selecting it displays corpus markdown and combat defaults.
Retrieval status is visible.
Add to combat is visible but disabled.
No writes occur.
```

---

## 15. Testing commands

Suggested backend:

```bash
uv run pytest \
  tests/test_statblock_view.py \
  tests/test_live_statblock_workbench_endpoint.py \
  tests/test_live_session_bootstrap.py \
  -q
```

Suggested frontend:

```bash
cd apps/live-control-ui
npm test -- \
  src/surface/modules/StatblockViewModule.test.tsx \
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
  apps/live_control_server/services/statblock_view.py \
  apps/live_control_server/services/statblock_draft_store.py \
  apps/live_control_server/routes/live.py \
  tests/test_statblock_view.py

git diff --check
```

If `npm run build` remains blocked by the known `@types/node` environment/config issue, document the caveat in the PR body.

---

## 16. Acceptance criteria

The PR is ready when:

- Read-only generated Statblock View service exists.
- List endpoint exists.
- Detail endpoint exists.
- List includes corpus-promoted generated statblocks and excludes non-promoted drafts.
- Detail reads corpus markdown from the confirmed corpus path.
- Detail returns combat defaults, warnings, provenance, breadcrumbs, source refs, corpus metadata, and retrieval metadata.
- List/read do not mutate session, corpus, event/job, or combat state.
- Responses do not expose internal secrets or host absolute paths.
- `StatblockViewModule` exists.
- Module is registered and available as an optional surface module.
- Module displays generated statblock list and read-only detail view.
- Add to combat remains disabled.
- Focused backend/frontend tests pass.

---

## 17. Suggested PR description

```markdown
### Motivation

PR #110 activated generated statblocks into the manifest-backed retrieval layer. This PR adds the first consumer surface: a read-only Statblock View for corpus-backed generated statblocks.

### Description

- Added a read-only generated Statblock View service.
- Added list/detail endpoints under `/api/live/statblocks/view/generated`.
- Listed corpus-promoted generated statblocks from stored draft records.
- Read confirmed corpus markdown and returned detail metadata: combat defaults, warnings, provenance, breadcrumbs, source refs, corpus path, retrieval metadata, and disabled future actions.
- Added frontend API/types for generated statblock list/detail.
- Added `StatblockViewModule` with generated statblock list and read-only detail panel.
- Registered `statblock_view` as an optional live surface module.
- Kept Add to combat disabled for PR112.
- Added backend/frontend tests proving read-only behavior and no mutation.

### Testing

- `uv run pytest tests/test_statblock_view.py tests/test_live_statblock_workbench_endpoint.py tests/test_live_session_bootstrap.py -q`
- `cd apps/live-control-ui && npm test -- src/surface/modules/StatblockViewModule.test.tsx src/api/liveApi.test.ts`
- `cd apps/live-control-ui && npx tsc -p tsconfig.app.json --noEmit`
- `uv run ruff check apps/live_control_server/services/statblock_view.py apps/live_control_server/services/statblock_draft_store.py apps/live_control_server/routes/live.py tests/test_statblock_view.py`
- `git diff --check`
```

---

## 18. Design reminder

This PR builds the read-only consumer surface. It does not make statblocks combat entities.

The ladder after PR111 should be:

```text
API-backed ✅
Commandable ✅
Visible ✅
Interactive ✅
Persistent draft storage ✅
Corpus promotion preview ✅
Confirmed corpus write ✅
Retrieval activation/verification ✅
Statblock View ⏭️ this PR
Add to combat ❌
Planning-mode-integrated ❌
```

PR112 should add Add to Combat from Statblock View / Workbench using the existing combat defaults as the hydration contract.
