# HANDOFF — Statblock retrieval activation PR110

**Created:** 2026-06-09  
**Repo:** `Drakosfire/DungeonMindBuddy`  
**Target base branch:** `main`  
**Suggested next branch:** `codex/statblock-retrieval-activation-pr110`  
**Depends on:** PR #109 / `7089beb27a1f6a8839658ef846ba1298809295dc` — Add confirmed statblock corpus write flow  
**Primary design:** `Docs/Design/DESIGN-statblock-lifecycle-agentic-workbench.md`  
**Previous handoffs:**
- `Docs/Plans/HANDOFF-statblock-lifecycle-seam-pr1.md`
- `Docs/Plans/HANDOFF-statblock-lifecycle-command-smoke-pr2.md`
- `Docs/Plans/HANDOFF-statblock-workbench-readonly-pr3.md`
- `Docs/Plans/archive/2026-06-22/handoffs/HANDOFF-statblock-workbench-draft-storage-pr107.md`
- `Docs/Plans/archive/2026-06-22/handoffs/HANDOFF-statblock-corpus-promotion-preview-pr108.md`
- `Docs/Plans/archive/2026-06-22/handoffs/HANDOFF-statblock-corpus-confirmed-write-pr109.md`
**Mode:** Retrieval activation + verification. Activate generated statblock corpus files into the current manifest-backed retrieval layer and prove they can be admitted as evidence. Do not build Statblock View, do not add to combat, and do not introduce a new vector/embedding system.

---

## 0. Copyable task prompt

```markdown
You are implementing Statblock Workbench PR110 in `Drakosfire/DungeonMindBuddy`.

Read first:

- `Docs/Plans/archive/2026-06-22/handoffs/HANDOFF-statblock-retrieval-activation-pr110.md`
- `Docs/Plans/archive/2026-06-22/handoffs/HANDOFF-statblock-corpus-confirmed-write-pr109.md`
- `Docs/Plans/archive/2026-06-22/handoffs/HANDOFF-statblock-corpus-promotion-preview-pr108.md`
- `Docs/Design/DESIGN-statblock-lifecycle-agentic-workbench.md`
- `src/live_play/manifest_context_query.py`
- `src/live_play/live_query_context.py`
- `apps/live_control_server/services/statblock_draft_store.py`

Goal: after PR109 has written a generated statblock markdown file into the corpus, add a retrieval activation/verification step that makes the generated statblock discoverable by DungeonBuddy's current manifest-backed retrieval layer.

Important architecture note: current live retrieval is manifest-backed query/admission (`manifest_context_query.py`), not a vector database. Do not invent a new embeddings index in this PR. Treat PR110 "ingestion" as activating the generated statblock corpus document into a generated-statblock manifest overlay, then verifying that `build_context_packet(...)` can retrieve/admit it as evidence.

Add server-side endpoints such as:

- `POST /api/live/statblocks/workbench/drafts/{artifact_id}/retrieval/activate`
- `POST /api/live/statblocks/workbench/drafts/{artifact_id}/retrieval/verify`

Activation should create or update a session-scoped generated-statblock manifest overlay under the live session directory, for example:

`<live_session_dir>/statblock_retrieval/generated_statblocks_manifest.json`

Verification should merge the active planning manifest with the generated-statblock overlay and run the existing manifest query/admission path to prove the generated statblock can be retrieved/admitted.

Frontend goal: add Workbench controls for Activate retrieval and Verify retrieval after corpus write. Show manifest entry details, retrieval query, admitted evidence path/line range/excerpt, and status. Keep Statblock View and Add to combat disabled.

Do not mutate combat. Do not build Statblock View. Do not run a vector/embedding index. Do not call DungeonMindServer generation. Do not expose internal secrets.
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
Semantic/retrieval activation ❌
Statblock View ❌
Add to combat ❌
Planning Mode generation tasks ❌
```

PR #109 added:

```text
stored draft
→ corpus writer dry-run
→ writer confirm_token
→ confirmed corpus markdown write
→ stored draft status: promotion_confirmed
```

PR #110 should add:

```text
promotion_confirmed stored draft
→ generated-statblock manifest overlay entry
→ retrieval verification query
→ admitted evidence includes generated statblock corpus file
→ stored draft status: retrieval_verified
```

This PR still does **not** build a full Statblock View and does **not** add to combat.

---

## 2. Reality check: what “ingestion” means in this repo today

DungeonBuddy's current live context lookup path uses:

```text
live query
→ active/planning manifest
→ manifest entries
→ route/content scoring
→ evidence extraction from markdown/jsonl
→ admission rules
→ grounded answer/context packet
```

Relevant files:

```text
src/live_play/live_query_context.py
src/live_play/manifest_context_query.py
```

There is not currently a dedicated generated-statblock vector index in this slice of the repo. Do not add one here.

For PR110, the narrow equivalent of “Semantic Knowledge Layer activation” is:

```text
confirmed corpus file
→ manifest overlay entry
→ manifest-backed retrieval/admission can find it
```

If a future real vector/SKL service appears, it can consume the same corpus path and activation metadata later.

---

## 3. Product intent

The GM should be able to see that a generated statblock is not merely written to the corpus, but also retrievable as campaign knowledge.

Target Workbench flow:

```text
Generate/render draft
→ store draft
→ preview corpus promotion
→ confirmed corpus write
→ Activate retrieval
→ Verify retrieval
→ see admitted evidence excerpt from generated statblock
```

After verification, the system can honestly say:

```text
This generated statblock has a corpus file and the retrieval layer can admit it as evidence.
```

But still not:

```text
This statblock is available in Statblock View.
This statblock has been added to combat.
```

Those are later PRs.

---

## 4. Design boundary

### PR110 does

- read stored draft records with `corpus_status == promotion_confirmed`;
- require `corpus_relpath` and corpus file existence;
- build a generated-statblock manifest overlay entry;
- write/update a session-scoped manifest overlay under the live session directory;
- merge base planning manifest + generated-statblock overlay for verification;
- run `build_context_packet(...)` using a statblock-focused query;
- prove the generated statblock route appears in admitted evidence;
- update stored draft retrieval metadata after activation/verification;
- show retrieval status in the Workbench.

### PR110 does not

- call DungeonMindServer generation;
- write or modify the corpus markdown file;
- re-run corpus writer;
- create embeddings/vector indexes;
- mutate base planning manifests in `evals/c2_live_prep/benchmarks/`;
- trigger an ingestion job queue;
- build Statblock View;
- add anything to combat;
- change initiative state;
- expose secrets.

---

## 5. Proposed activation artifact

Create a new live-session-scoped overlay file:

```text
<live_session_dir>/statblock_retrieval/generated_statblocks_manifest.json
```

Schema:

```json
{
  "schema": "dmb_generated_statblock_manifest_overlay_v1",
  "campaign_id": "longmont-c2",
  "session": 22,
  "generated_at": "2026-06-09T...Z",
  "entries": [
    {
      "source_id": "generated_statblock-statblock-draft-test",
      "source_role": "world_evidence",
      "authority": "canon_play",
      "session_scope": [22],
      "route": "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Statblocks/generated/generated_obsidian_thornling.md",
      "route_exists": true,
      "admissible": true,
      "allowed_uses": ["planning_context", "statblock_lookup", "mechanical_reference"],
      "forbidden_uses": ["play_facts"],
      "lexical_terms": ["Generated Obsidian Thornling", "statblock", "armor class", "hit points", "challenge rating", "primary actions"],
      "notes": ["Generated statblock promoted through DungeonBuddy Workbench and confirmed into corpus."]
    }
  ]
}
```

Rationale:

- `source_role = world_evidence` maps into the existing world-reference lane.
- Mechanical/statblock queries already get a boost for world evidence or statblock paths.
- `authority = canon_play` reflects confirmed corpus promotion, but `forbidden_uses = ["play_facts"]` prevents a generated mechanical statblock from proving what happened in play.
- `allowed_uses` explicitly names statblock/mechanical lookup without needing to overhaul the admission model in this PR.

---

## 6. Stored draft record fields

Extend `StoredStatblockDraftRecord` and `StoredStatblockDraftSummary` with retrieval metadata.

Suggested fields:

```python
retrieval_status: str | None = None
retrieval_manifest_path: str | None = None
retrieval_activated_at: str | None = None
retrieval_verified_at: str | None = None
retrieval_query: str | None = None
retrieval_evidence_path: str | None = None
retrieval_evidence_score: float | None = None
```

Suggested status values:

```text
not_activated
manifest_activated
retrieval_verified
verification_failed
```

Do not add these fields to `StatblockDraftArtifact` unless there is already a clear artifact-level home. Record-level metadata is enough for this slice.

---

## 7. Backend service design

Add a service module:

```text
apps/live_control_server/services/statblock_retrieval_activation.py
```

Suggested models:

```python
class GeneratedStatblockManifestOverlay(BaseModel):
    schema: Literal["dmb_generated_statblock_manifest_overlay_v1"] = "dmb_generated_statblock_manifest_overlay_v1"
    campaign_id: str
    session: int
    generated_at: str
    entries: list[dict[str, Any]] = Field(default_factory=list)

class StatblockRetrievalActivationResponse(BaseModel):
    schema_version: Literal["dmb_statblock_retrieval_activation_v1"] = "dmb_statblock_retrieval_activation_v1"
    artifact_id: str
    draft_id: str
    title: str
    corpus_relpath: str
    corpus_display_path: str
    manifest_overlay_path: str
    manifest_entry: dict[str, Any]
    stored_record: StoredStatblockDraftRecord
    diagnostics: list[str] = Field(default_factory=list)
    available_actions: list[StatblockWorkbenchAction] = Field(default_factory=list)

class StatblockRetrievalVerifyRequest(BaseModel):
    query: str | None = None

class StatblockRetrievalVerifyResponse(BaseModel):
    schema_version: Literal["dmb_statblock_retrieval_verify_v1"] = "dmb_statblock_retrieval_verify_v1"
    artifact_id: str
    draft_id: str
    title: str
    query: str
    status: Literal["verified", "retrieved_not_admitted", "not_found"]
    corpus_relpath: str
    manifest_overlay_path: str
    admitted_evidence: list[dict[str, Any]] = Field(default_factory=list)
    rejected_evidence: list[dict[str, Any]] = Field(default_factory=list)
    retrieval_trace: dict[str, Any] = Field(default_factory=dict)
    stored_record: StoredStatblockDraftRecord | None = None
    diagnostics: list[str] = Field(default_factory=list)
    available_actions: list[StatblockWorkbenchAction] = Field(default_factory=list)
```

Suggested functions:

```python
def activate_statblock_retrieval(
    *,
    base: Path,
    root: Path,
    packet: dict[str, Any],
    artifact_id: str,
) -> StatblockRetrievalActivationResponse: ...


def verify_statblock_retrieval(
    *,
    base: Path,
    root: Path,
    packet: dict[str, Any],
    artifact_id: str,
    query: str | None = None,
) -> StatblockRetrievalVerifyResponse: ...
```

---

## 8. Activation behavior

Activation should:

1. Read stored draft record.
2. Validate `record.artifact.corpus_status == "promotion_confirmed"`.
3. Validate `record.corpus_relpath` and `record.corpus_display_path` are present.
4. Validate `root / "corpus" / "eldyrwild-markdown" / record.corpus_relpath` exists as a file.
5. Build a manifest entry from the record.
6. Load existing overlay if present.
7. Upsert the entry by `source_id` or `route`, replacing prior entry for the same artifact/path.
8. Write overlay JSON under:

```text
<live_session_dir>/statblock_retrieval/generated_statblocks_manifest.json
```

9. Update stored record retrieval metadata:

```text
retrieval_status = manifest_activated
retrieval_manifest_path = statblock_retrieval/generated_statblocks_manifest.json
retrieval_activated_at = now
```

10. Return activation response.

Activation must not:

- edit the corpus file;
- edit the base planning manifest;
- append events/jobs;
- mutate combat.

---

## 9. Manifest entry construction

Source ID:

```text
generated_statblock-<artifact_id>
```

Route:

```text
corpus/eldyrwild-markdown/<record.corpus_relpath>
```

Lexical terms should include:

- title;
- draft id;
- artifact id;
- creature name from structured statblock if present;
- challenge rating / CR if present;
- creature type if present;
- armor class / AC;
- hit points / HP;
- passive perception;
- primary actions;
- suggested tactics;
- source refs labels/reasons if simple to extract;
- `statblock`;
- `generated statblock`.

Keep lexical terms strings. Deduplicate case-insensitively.

---

## 10. Manifest merge for verification

Do not mutate the checked-in base manifest.

Add helper:

```python
def merge_generated_statblock_overlay(
    base_manifest: dict[str, Any],
    overlay: GeneratedStatblockManifestOverlay,
) -> dict[str, Any]: ...
```

Behavior:

- copy base manifest;
- append overlay entries;
- de-duplicate by normalized route/source_id, with overlay entries winning;
- add diagnostics/metadata if useful, e.g.:

```json
"generated_statblock_overlay": {
  "path": "statblock_retrieval/generated_statblocks_manifest.json",
  "entry_count": 1
}
```

This merged manifest is used in-memory for verification.

Do not write the merged manifest unless needed. If you do write one for debugging, write under live session only, never under benchmark manifests.

---

## 11. Verification behavior

Verification should:

1. Require activation overlay exists, or call activation first if the design remains simple. Preference: require activation and return a clear error if missing.
2. Load the current planning/active manifest using the same resolution policy as live query if practical. If easier, use `resolve_manifest_path(...)` from `live_query_context.py`.
3. Load overlay.
4. Merge base manifest + overlay.
5. Build a default query if none provided:

```text
What are the statblock details for "<title>"? Include armor class, hit points, challenge rating, and primary actions.
```

6. Call:

```python
build_context_packet(
    QueryRequest(question_id=f"statblock-retrieval-{artifact_id}", question=query),
    merged_manifest,
    root=root,
    config=QueryConfig(...),
)
```

7. Determine success:

```text
verified = admitted_evidence contains record route or corpus_relpath
retrieved_not_admitted = retrieved evidence contains it but admitted does not
not_found = neither retrieved nor admitted contains it
```

8. On verified, update stored record:

```text
retrieval_status = retrieval_verified
retrieval_verified_at = now
retrieval_query = query
retrieval_evidence_path = matched evidence path
retrieval_evidence_score = matched evidence score
```

9. Return verification response.

If verification fails, update record only if you want to record failure. If doing so, use:

```text
retrieval_status = verification_failed
retrieval_query = query
```

Do not mark as verified unless admitted evidence contains the generated statblock route.

---

## 12. Live-control endpoints

Add endpoints in `apps/live_control_server/routes/live.py`.

### 12.1 Activate retrieval

```text
POST /api/live/statblocks/workbench/drafts/{artifact_id}/retrieval/activate
```

Request body: none or `{}`.

Response: `StatblockRetrievalActivationResponse`.

### 12.2 Verify retrieval

```text
POST /api/live/statblocks/workbench/drafts/{artifact_id}/retrieval/verify
```

Request:

```json
{
  "query": "optional custom statblock retrieval query"
}
```

Response: `StatblockRetrievalVerifyResponse`.

### 12.3 Error mapping

Recommended:

```text
404 stored draft not found
422 unsafe artifact id
409 corpus write missing / corpus file missing / retrieval not activated
500 unexpected activation/verification failure
```

Safe errors only. No absolute host paths in normal responses.

---

## 13. Frontend API/types

Update:

```text
apps/live-control-ui/src/api/types.ts
apps/live-control-ui/src/api/liveApi.ts
apps/live-control-ui/src/api/liveApi.test.ts
```

Suggested types:

```ts
export interface StatblockRetrievalActivationResponse {
  schema_version: "dmb_statblock_retrieval_activation_v1";
  artifact_id: string;
  draft_id: string;
  title: string;
  corpus_relpath: string;
  corpus_display_path: string;
  manifest_overlay_path: string;
  manifest_entry: Record<string, unknown>;
  stored_record: StoredStatblockDraftRecord;
  diagnostics: string[];
  available_actions: StatblockWorkbenchAction[];
}

export interface StatblockRetrievalVerifyRequest {
  query?: string | null;
}

export interface StatblockRetrievalVerifyResponse {
  schema_version: "dmb_statblock_retrieval_verify_v1";
  artifact_id: string;
  draft_id: string;
  title: string;
  query: string;
  status: "verified" | "retrieved_not_admitted" | "not_found";
  corpus_relpath: string;
  manifest_overlay_path: string;
  admitted_evidence: Array<Record<string, unknown>>;
  rejected_evidence: Array<Record<string, unknown>>;
  retrieval_trace: Record<string, unknown>;
  stored_record?: StoredStatblockDraftRecord | null;
  diagnostics: string[];
  available_actions: StatblockWorkbenchAction[];
}
```

API helpers:

```ts
export async function activateStatblockRetrieval(
  artifactId: string,
): Promise<StatblockRetrievalActivationResponse> { ... }

export async function verifyStatblockRetrieval(
  artifactId: string,
  request: StatblockRetrievalVerifyRequest = {},
): Promise<StatblockRetrievalVerifyResponse> { ... }
```

Use `encodeURIComponent(artifactId)`.

---

## 14. Frontend Workbench behavior

Update:

```text
apps/live-control-ui/src/surface/modules/StatblockWorkbenchModule.tsx
```

### 14.1 Enable retrieval controls after corpus write

Add panel:

```text
Retrieval activation
```

Enable `Activate retrieval` only when:

- current artifact exists;
- `artifact.corpus_status === "promotion_confirmed"`;
- stored record has corpus path metadata if available;
- no command/store/load/preview/write/retrieval action is pending.

Enable `Verify retrieval` only after activation response exists or stored record `retrieval_status === "manifest_activated"` / `retrieval_verified`.

### 14.2 Display activation result

Show:

- manifest overlay path;
- source id;
- route;
- source role;
- authority;
- allowed/forbidden uses;
- lexical terms;
- diagnostics.

### 14.3 Display verification result

Show:

- query;
- status;
- matched evidence path;
- line range;
- evidence excerpt;
- evidence score;
- admitted vs rejected summary;
- diagnostics.

If verified, show a clear badge:

```text
Retrieval verified
```

### 14.4 Future actions remain disabled

Keep disabled:

```text
Open in Statblock View
Add to combat
```

This PR proves retrieval. It does not build the consumer surface.

### 14.5 State clearing

Clear retrieval activation/verification state when:

- generating a new draft;
- rendering a new draft;
- storing a different draft;
- loading a different draft;
- preparing or committing a new corpus write.

Do not clear retrieval result on harmless stored-drafts list refresh.

---

## 15. Backend tests

Add/extend tests, likely:

```text
tests/test_live_statblock_workbench_endpoint.py
tests/test_statblock_retrieval_activation.py
```

Use temp live session and temp corpus roots. Do not write to checked-in corpus or benchmark manifests.

### 15.1 Activation requires confirmed corpus write

Attempt activation on a stored draft with `corpus_status != promotion_confirmed`.

Assert:

```text
409
no overlay file written
stored record unchanged
```

### 15.2 Activation writes manifest overlay

Flow:

```text
store draft
prepare/commit corpus write
POST retrieval/activate
```

Assert:

- status 200;
- overlay exists under `<session_dir>/statblock_retrieval/generated_statblocks_manifest.json`;
- overlay schema correct;
- entry route is `corpus/eldyrwild-markdown/<corpus_relpath>`;
- source_role is `world_evidence`;
- authority is `canon_play`;
- allowed/forbidden uses as expected;
- route_exists true;
- lexical terms include title, statblock, armor class/AC, hit points/HP, CR/challenge rating, action names if available;
- stored record retrieval status becomes `manifest_activated`.

### 15.3 Activation does not mutate base manifest/corpus/combat

Assert:

- corpus markdown file unchanged;
- base benchmark manifest unchanged;
- live packet unchanged;
- surface layout unchanged;
- event log unchanged;
- job queue unchanged;
- only overlay file + stored draft record change.

### 15.4 Verification admits generated statblock evidence

Flow:

```text
commit corpus write
activate retrieval
POST retrieval/verify
```

Assert:

- status 200;
- response status `verified`;
- admitted evidence includes generated statblock route/path;
- evidence has text excerpt containing title or statblock content;
- line range is present for markdown evidence;
- stored record retrieval status becomes `retrieval_verified`;
- retrieval query is recorded.

### 15.5 Verification fails safely when not activated

Attempt verify before activation.

Assert 409 and no record marked verified.

### 15.6 Custom query supported

Use a custom query referencing the generated title and mechanical terms.

Assert verified.

### 15.7 Unsafe/missing ID and missing corpus file

Cover:

- unsafe artifact id → 422;
- missing draft → 404;
- corpus path metadata present but corpus file missing → 409.

### 15.8 No secret exposure

Set fake env:

```text
DUNGEONBUDDY_INTERNAL_API_KEY=super-secret-test-key
DUNGEONMIND_SERVER_URL=https://example.invalid
```

Call activate and verify.

Assert response text does not contain:

```text
super-secret-test-key
DUNGEONBUDDY_INTERNAL_API_KEY
DUNGEONMIND_SERVER_URL
X-DungeonBuddy-Internal-Key
```

---

## 16. Frontend tests

Update:

```text
apps/live-control-ui/src/api/liveApi.test.ts
apps/live-control-ui/src/surface/modules/StatblockWorkbenchModule.test.tsx
```

### 16.1 API helper tests

Assert:

- `activateStatblockRetrieval(id)` POSTs to encoded activate route;
- `verifyStatblockRetrieval(id, { query })` POSTs to encoded verify route with JSON body.

### 16.2 Component tests

Add tests:

1. Retrieval activation disabled until artifact is corpus-promoted.

2. After corpus write success, Activate retrieval becomes enabled.

3. Clicking Activate retrieval:
   - calls API;
   - shows pending state;
   - displays overlay path and manifest entry route;
   - updates displayed artifact/record status if response includes updated stored record.

4. Verify retrieval:
   - after activation, click Verify retrieval;
   - shows query/status;
   - renders admitted evidence path/excerpt/line range;
   - displays `Retrieval verified`.

5. Verification failure:
   - safe error message;
   - does not pretend verified.

6. Loading/generating another draft clears retrieval activation/verification panels.

7. Statblock View / Add to combat remain disabled.

No live network.

---

## 17. Manual smoke

Backend:

```bash
uv run uvicorn apps.live_control_server.main:app --reload
```

Create/store/preview/commit via existing PR109 flow, then:

```bash
ARTIFACT_ID="<artifact id from stored record>"

curl -s \
  -X POST \
  -H "Content-Type: application/json" \
  "http://127.0.0.1:8000/api/live/statblocks/workbench/drafts/${ARTIFACT_ID}/retrieval/activate" \
  -d '{}' \
  | jq

curl -s \
  -X POST \
  -H "Content-Type: application/json" \
  "http://127.0.0.1:8000/api/live/statblocks/workbench/drafts/${ARTIFACT_ID}/retrieval/verify" \
  -d '{}' \
  | jq
```

Expected:

```text
activation writes statblock_retrieval/generated_statblocks_manifest.json
verification returns status = verified
admitted evidence includes the generated statblock corpus path
no combat mutation occurs
```

Frontend:

```bash
cd apps/live-control-ui
npm run dev
```

Verify:

```text
After confirmed corpus write, Activate retrieval becomes available.
Activation shows manifest overlay details.
Verify retrieval returns admitted evidence from the generated statblock file.
Statblock View and Add to combat remain disabled.
```

---

## 18. Testing commands

Suggested backend:

```bash
uv run pytest \
  tests/test_live_statblock_workbench_endpoint.py \
  tests/test_live_session_bootstrap.py \
  tests/test_corpus_writer_generated_statblocks.py \
  tests/test_statblock_retrieval_activation.py \
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
  apps/live_control_server/services/statblock_retrieval_activation.py \
  apps/live_control_server/services/statblock_draft_store.py \
  apps/live_control_server/routes/live.py \
  src/live_play/manifest_context_query.py \
  tests/test_live_statblock_workbench_endpoint.py \
  tests/test_statblock_retrieval_activation.py

git diff --check
```

If `npm run build` remains blocked by the known `@types/node` environment/config issue, document the caveat in the PR body.

---

## 19. Acceptance criteria

The PR is ready when:

- Retrieval activation endpoint exists.
- Retrieval verification endpoint exists.
- Activation requires confirmed corpus write and existing corpus file.
- Activation writes a session-scoped generated-statblock manifest overlay.
- Activation does not mutate base benchmark manifests or corpus markdown.
- Stored draft records include retrieval metadata.
- Verification merges base manifest + generated overlay in memory.
- Verification uses existing manifest-backed query/admission runner.
- Verification proves admitted evidence contains the generated statblock corpus route.
- Verification records status/query/evidence metadata on the stored draft record.
- Responses do not expose host absolute paths or internal secrets.
- Workbench can activate retrieval and verify retrieval.
- Workbench shows manifest entry and admitted evidence details.
- Statblock View and Add to combat remain disabled.
- Tests prove no combat/event/job mutation.
- Focused backend and frontend tests pass.

---

## 20. Suggested PR description

```markdown
### Motivation

PR #109 confirmed generated statblock markdown into the corpus. This PR activates those generated statblocks into DungeonBuddy's current manifest-backed retrieval layer and verifies that the generated corpus file can be admitted as evidence.

### Description

- Added generated-statblock retrieval activation service.
- Added session-scoped manifest overlay under `statblock_retrieval/generated_statblocks_manifest.json`.
- Added activation endpoint for corpus-promoted statblock drafts.
- Added verification endpoint that merges the active planning manifest with the generated-statblock overlay and runs the existing manifest query/admission path.
- Extended stored draft records with retrieval activation/verification metadata.
- Added frontend API/types and Workbench controls for Activate retrieval and Verify retrieval.
- Displayed manifest entry details and admitted evidence/excerpt/line range in the Workbench.
- Kept Statblock View and Add to combat disabled.
- Added backend/frontend tests proving retrieval admission and no unrelated mutation.

### Testing

- `uv run pytest tests/test_live_statblock_workbench_endpoint.py tests/test_live_session_bootstrap.py tests/test_corpus_writer_generated_statblocks.py tests/test_statblock_retrieval_activation.py -q`
- `cd apps/live-control-ui && npm test -- src/surface/modules/StatblockWorkbenchModule.test.tsx src/api/liveApi.test.ts`
- `cd apps/live-control-ui && npx tsc -p tsconfig.app.json --noEmit`
- `uv run ruff check apps/live_control_server/services/statblock_retrieval_activation.py apps/live_control_server/services/statblock_draft_store.py apps/live_control_server/routes/live.py src/live_play/manifest_context_query.py tests/test_live_statblock_workbench_endpoint.py tests/test_statblock_retrieval_activation.py`
- `git diff --check`
```

---

## 21. Design reminder

This PR activates and verifies retrieval. It does not build the consumer surface.

The ladder after PR110 should be:

```text
API-backed ✅
Commandable ✅
Visible ✅
Interactive ✅
Persistent draft storage ✅
Corpus promotion preview ✅
Confirmed corpus write ✅
Retrieval activation/verification ⏭️ this PR
Statblock View ❌
Add to combat ❌
Planning-mode-integrated ❌
```

PR111 should build a Statblock View over corpus-backed generated statblocks. PR112 should add combat integration.
