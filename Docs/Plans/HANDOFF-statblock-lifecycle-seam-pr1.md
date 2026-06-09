# HANDOFF — Statblock lifecycle seam PR1

**Created:** 2026-06-09  
**Repo:** `Drakosfire/DungeonMindBuddy`  
**Target base branch:** `main`  
**Suggested next branch:** `codex/statblock-lifecycle-seam-pr1`  
**Primary design:** `Docs/Design/DESIGN-statblock-lifecycle-agentic-workbench.md`  
**Production report:** `Docs/Plans/REPORT-to-design-agent-statblock-v2-production-deploy-2026-06-09.md`  
**Related handoff:** `Docs/Plans/HANDOFF-dungeonbuddy-statblockgenerator-proxy-client.md`  
**Mode:** Right-sized implementation handoff. Build the server-side lifecycle seam and artifact bones; do not build UI yet.

---

## 0. Copyable task prompt

```markdown
You are implementing the first DungeonBuddy statblock lifecycle seam PR.

Read first:

- `Docs/Plans/HANDOFF-statblock-lifecycle-seam-pr1.md`
- `Docs/Design/DESIGN-statblock-lifecycle-agentic-workbench.md`
- `Docs/Plans/REPORT-to-design-agent-statblock-v2-production-deploy-2026-06-09.md`
- `Docs/Plans/HANDOFF-dungeonbuddy-statblockgenerator-proxy-client.md`

Goal: add the server-side Python lifecycle seam for the live StatBlockGenerator v2 producer contract. This PR should create typed request/response models, a server-side HTTP client, a mock/provider boundary, a `StatblockDraftArtifact` mapper, lifecycle/command constants, fixtures, and tests.

Do not build UI. Do not mutate combat. Do not write to corpus. Do not ingest into the Semantic Knowledge Layer. Do not expose `DUNGEONBUDDY_INTERNAL_API_KEY` to browser code.
```

---

## 1. Re-anchor

DungeonMindServer production now exposes the live v2 producer contract at `https://www.dungeonmind.net`:

```text
GET  /api/statblockgenerator/v2/health
POST /api/statblockgenerator/v2/generate-draft
POST /api/statblockgenerator/v2/render-draft
```

These routes require:

```text
X-DungeonBuddy-Internal-Key: <secret>
```

matching Buddy/server-side env:

```text
DUNGEONBUDDY_INTERNAL_API_KEY=<secret>
```

The Buddy browser must never receive or send this key.

The existing planner statblock integration in `src/agent/planner.py` predates v2. It uses `DUNGEONMIND_STATBLOCK_URL`, `DUNGEONMIND_STATBLOCK_API_KEY`, `Authorization: Bearer`, a legacy request shape, and string-ish response extraction. Do not extend that legacy hook as the command-board lifecycle boundary in this PR.

---

## 2. Where this PR sits in the next few parts

### Part 1 — This PR: lifecycle seam bones

Build the non-UI foundation:

```text
v2 producer models
→ server-side client/provider
→ mock provider
→ draft response fixtures
→ StatblockDraftArtifact mapper
→ lifecycle/status enums
→ agent command-name constants
→ tests
```

This gives agents and future surfaces one typed seam.

### Part 2 — Developer smoke / command endpoint

Add a small Buddy-side route or CLI/dev harness that can call health/generate/render through the seam and show returned markdown/defaults. This proves real production connectivity without adding product UI.

### Part 3 — Statblock Workbench read/review skeleton

Create the dedicated Workbench surface for viewing a `StatblockDraftArtifact`: markdown, combat defaults, warnings, provenance, lifecycle/status, breadcrumbs, and review actions. Storage/corpus actions can be disabled stubs.

### Part 4 — Draft storage + corpus promotion preview

Store reviewed draft artifacts, preview a corpus write with frontmatter and breadcrumbs, and require confirmation before writing. No silent corpus mutation.

### Part 5 — Retrieval + Combat Pane consumption

After corpus ingestion/retrieval works, Statblock View and Combat Pane can retrieve corpus-backed statblocks, drill into markdown, and add combat-ready defaults into the initiative tracker.

---

## 3. Right-sized scope for PR1

This PR should implement the lifecycle seam in Python/server-side code first.

Why Python first:

- The internal key must remain server-side.
- `pyproject.toml` already includes `pydantic`, `httpx`, `pytest`, and `python-dotenv`.
- Agent/planner workflows are Python-side today.
- A future Buddy backend route can use the same client.
- The Vite live-control UI package is browser-oriented; putting the internal-key HTTP provider there risks accidental secret exposure.

This PR may include TypeScript docs or future-facing comments, but it should not add a browser-executed HTTP provider with the internal key.

---

## 4. Suggested implementation shape

Suggested files:

```text
src/statblocks/__init__.py
src/statblocks/v2_contract.py
src/statblocks/v2_client.py
src/statblocks/lifecycle_artifact.py
src/statblocks/lifecycle_commands.py

tests/statblocks/fixtures/generated_draft_response.fixture.json
tests/statblocks/fixtures/rendered_draft_response.fixture.json
tests/statblocks/test_v2_contract_models.py
tests/statblocks/test_v2_client.py
tests/statblocks/test_lifecycle_artifact.py
tests/statblocks/test_lifecycle_commands.py
```

Alternative package names are fine, but prefer a domain package like `src/statblocks/` over burying this inside `src/agent/planner.py`.

---

## 5. Models to define

### 5.1 v2 producer contract models

Use Pydantic models for the v2 envelope. Keep `statblock` as `dict[str, Any]` for now rather than recreating the full DungeonMindServer `StatBlockDetails` tree.

Minimum models:

```python
DraftMode = Literal[
    "generate_from_prompt",
    "generate_from_source_statblock",
    "revise_existing",
    "quick_reinforcement",
    "terrain_pressure",
    "render_existing",
]

class OutputOptions(BaseModel): ...
class SourceRef(BaseModel): ...
class DraftIntent(BaseModel): ...
class EncounterContext(BaseModel): ...
class TerrainContext(BaseModel): ...
class StatBlockDraftRequest(BaseModel): ...
class StatBlockDraftRenderRequest(BaseModel): ...
class CombatDefaults(BaseModel): ...
class ReviewWarning(BaseModel): ...
class DraftProvenance(BaseModel): ...
class StatBlockDraft(BaseModel): ...
class ContractError(BaseModel): ...
class StatBlockDraftResponse(BaseModel): ...
class StatBlockGeneratorHealth(BaseModel): ...
```

Keep models permissive enough to match production. Do not overfit to one smoke creature.

### 5.2 Response invariant

Add validation if straightforward:

```text
success == true  → draft must be present
success == false → error must be present
```

If this is annoying in Pydantic v2, test the invariant in helper functions instead.

---

## 6. Server-side client/provider

Create a provider-neutral interface/protocol and two implementations.

Suggested shape:

```python
class StatBlockGeneratorProvider(Protocol):
    def health(self) -> StatBlockGeneratorHealth: ...
    def generate_draft(self, request: StatBlockDraftRequest) -> StatBlockDraftResponse: ...
    def render_draft(self, request: StatBlockDraftRenderRequest) -> StatBlockDraftResponse: ...
```

Implement:

```text
MockStatBlockGeneratorProvider
DungeonMindServerStatBlockGeneratorClient
```

### 6.1 Env/config

Use these env vars:

```text
DUNGEONMIND_SERVER_URL=https://www.dungeonmind.net
DUNGEONBUDDY_INTERNAL_API_KEY=<secret>
```

Optional provider selector for later:

```text
STATBLOCK_GENERATOR_PROVIDER=mock|http
```

### 6.2 HTTP behavior

`DungeonMindServerStatBlockGeneratorClient` should:

- use `httpx`;
- trim trailing slash from base URL;
- send `X-DungeonBuddy-Internal-Key` on every v2 request;
- never log or return the key;
- raise a clear local configuration error if HTTP provider is constructed without a key;
- preserve server error envelopes when HTTP response body is a v2 envelope;
- expose timeout configuration, defaulting to something conservative such as 30 seconds;
- not perform live network calls in normal unit tests.

Suggested endpoints:

```text
GET  {base_url}/api/statblockgenerator/v2/health
POST {base_url}/api/statblockgenerator/v2/generate-draft
POST {base_url}/api/statblockgenerator/v2/render-draft
```

---

## 7. Buddy artifact mapper

Create `StatblockDraftArtifact` as the Buddy-owned lifecycle object.

Suggested Pydantic model:

```python
class StatblockDraftArtifact(BaseModel):
    artifact_id: str
    draft_id: str
    title: str

    markdown: str
    structured_statblock: dict[str, Any]
    combat_defaults: CombatDefaults
    warnings: list[ReviewWarning]
    provenance: DraftProvenance

    review_status: StatblockReviewStatus
    lifecycle_state: StatblockLifecycleState
    storage_status: StatblockStorageStatus
    corpus_status: StatblockCorpusStatus

    source_refs: list[SourceRef]
    breadcrumbs: list[StatblockBreadcrumb]

    created_by: Literal["human", "agent", "planning_task", "combat_task"]
    created_at: str
    updated_at: str
```

### 7.1 Lifecycle/status enums

```python
StatblockLifecycleState = Literal[
    "description_requested",
    "description_drafted",
    "description_approved",
    "generation_requested",
    "live_draft",
    "needs_review",
    "reviewed",
    "stored_artifact",
    "promotion_previewed",
    "corpus_promoted",
    "indexed",
    "combat_ready",
]

StatblockReviewStatus = Literal[
    "needs_dm_review",
    "warnings",
    "failed",
    "approved",
    "rejected",
]

StatblockStorageStatus = Literal[
    "not_stored",
    "stored_draft",
    "exported",
    "archived",
]

StatblockCorpusStatus = Literal[
    "not_promoted",
    "promotion_previewed",
    "promotion_confirmed",
    "write_failed",
    "indexed",
    "retrievable",
]
```

### 7.2 Mapper function

Suggested function:

```python
def artifact_from_draft_response(
    response: StatBlockDraftResponse,
    *,
    created_by: Literal["human", "agent", "planning_task", "combat_task"],
    breadcrumbs: list[StatblockBreadcrumb] | None = None,
    now: Callable[[], datetime] | None = None,
) -> StatblockDraftArtifact:
    ...
```

Mapping rules:

- require `response.success` and `response.draft`;
- `artifact_id` deterministic or UUID-like; tests should not depend on real time/randomness unless injected;
- `title` from `combat_defaults.name`, fallback to draft/statblock name, fallback to `draft_id`;
- preserve markdown;
- preserve structured statblock;
- preserve combat defaults;
- preserve warnings;
- preserve provenance;
- source refs from provenance if present;
- breadcrumbs default to empty list;
- `review_status` from draft;
- `lifecycle_state = "live_draft"` initially;
- `storage_status = "not_stored"` initially;
- `corpus_status = "not_promoted"` initially.

---

## 8. Agent command-name constants

Create constants now so future UI and agents share the same vocabulary.

Suggested file:

```text
src/statblocks/lifecycle_commands.py
```

Suggested constants:

```python
STATBLOCK_GENERATOR_HEALTH = "statblock.generator.health"
STATBLOCK_DESCRIPTION_REQUEST = "statblock.description.request"
STATBLOCK_DESCRIPTION_APPROVE = "statblock.description.approve"
STATBLOCK_DRAFT_GENERATE = "statblock.draft.generate"
STATBLOCK_DRAFT_RENDER = "statblock.draft.render"
STATBLOCK_DRAFT_REVIEW = "statblock.draft.review"
STATBLOCK_DRAFT_STORE = "statblock.draft.store"
STATBLOCK_CORPUS_PREVIEW_PROMOTE = "statblock.corpus.preview_promote"
STATBLOCK_CORPUS_CONFIRM_PROMOTE = "statblock.corpus.confirm_promote"
STATBLOCK_CORPUS_INGEST = "statblock.corpus.ingest"
STATBLOCK_COMBAT_ADD = "statblock.combat.add"
```

Only health/generate/render need behavior later. The rest are vocabulary for the lifecycle.

---

## 9. Fixtures

Add two response fixtures:

```text
tests/statblocks/fixtures/generated_draft_response.fixture.json
tests/statblocks/fixtures/rendered_draft_response.fixture.json
```

They should include:

- `success: true`;
- `draft.lifecycle_state: live_draft`;
- `draft.review_status: needs_dm_review` or `warnings`;
- non-empty markdown;
- combat defaults with name, armor class, hit points, primary actions;
- warnings array;
- provenance with mode, generator, generated_at, source refs, generation info.

These can be simplified from production smoke output. Do not include secrets.

Add one error fixture or construct error responses in tests:

```text
success: false
draft: null
error: { code, message, details }
timestamp: ...
```

---

## 10. Tests

No live network by default.

### 10.1 Contract model tests

`tests/statblocks/test_v2_contract_models.py`

Assert:

- generated fixture validates as `StatBlockDraftResponse`;
- rendered fixture validates as `StatBlockDraftResponse`;
- successful response has draft;
- error response has error;
- health fixture/payload validates.

### 10.2 Client tests

`tests/statblocks/test_v2_client.py`

Use `httpx.MockTransport` or equivalent.

Assert:

- `health()` calls `/api/statblockgenerator/v2/health`;
- `generate_draft()` calls `/api/statblockgenerator/v2/generate-draft`;
- `render_draft()` calls `/api/statblockgenerator/v2/render-draft`;
- all HTTP calls include `X-DungeonBuddy-Internal-Key`;
- missing key at client construction fails clearly;
- server `401`, `403`, `501`, and `500` responses preserve meaningful errors;
- key value is not included in exception message text.

### 10.3 Artifact mapper tests

`tests/statblocks/test_lifecycle_artifact.py`

Assert:

- draft response maps to `StatblockDraftArtifact`;
- markdown preserved;
- structured statblock preserved;
- combat defaults preserved;
- warnings/provenance preserved;
- lifecycle/status defaults are correct;
- breadcrumbs field exists;
- title fallback works;
- unsuccessful response cannot map to artifact.

### 10.4 Command constants tests

`tests/statblocks/test_lifecycle_commands.py`

Assert:

- constants have expected string values;
- no duplicates.

### 10.5 Optional live smoke

Optional, skipped unless env flag is set:

```text
DMB_LIVE_STATBLOCK_V2_SMOKE=1
```

Then call production v2 health only, using `DUNGEONMIND_SERVER_URL` and `DUNGEONBUDDY_INTERNAL_API_KEY`.

Do not run live generate by default because it can call OpenAI.

---

## 11. Out of scope

Do not modify `src/agent/planner.py` beyond maybe a comment pointing to the new client.

Do not replace the legacy planner hook in this PR.

Do not add UI.

Do not add FastAPI routes in Buddy unless the repo already has a clear server route seam and the change remains small.

Do not add corpus writes.

Do not add Semantic Knowledge Layer ingestion.

Do not add combat state mutation.

Do not add generated draft persistence.

Do not place the internal key in frontend/Vite code.

Do not use production network calls in default tests.

---

## 12. Acceptance criteria

The PR is ready when:

- `src/statblocks/` package exists with v2 contract models, client/provider, artifact model/mapper, and command constants;
- generated/rendered response fixtures exist and validate;
- mock/provider tests cover health/generate/render request paths;
- HTTP client injects `X-DungeonBuddy-Internal-Key` from server-side config;
- HTTP client refuses to run without a key;
- key value is not leaked in fixtures/errors/log text;
- `StatblockDraftArtifact` maps from a successful v2 response;
- lifecycle/storage/corpus statuses initialize correctly;
- command constants exist for future agent operations;
- no UI, corpus, ingestion, or combat mutation is introduced;
- tests pass with no live network calls.

---

## 13. Suggested PR description

```markdown
### Motivation

StatBlockGenerator v2 is live in production and returns command-board draft envelopes. This PR adds DungeonBuddy's first statblock lifecycle seam: a server-side v2 producer client, typed response models, draft artifact mapping, and lifecycle command constants. This gives future agents, planning mode, statblock workbench, and combat surfaces one shared foundation without exposing the internal API key to browser code.

### Description

- Added `src/statblocks/` package for the StatBlock v2 lifecycle seam.
- Added Pydantic models for the v2 health/generate/render contract.
- Added a server-side DungeonMindServer client/provider using `httpx` and `X-DungeonBuddy-Internal-Key`.
- Added mock provider and response fixtures for generated/rendered drafts.
- Added `StatblockDraftArtifact`, lifecycle/storage/corpus statuses, breadcrumbs, and artifact mapper.
- Added statblock lifecycle command-name constants for future agent operations.
- Added tests for contract parsing, client request shape/header injection, artifact mapping, command constants, and error envelope handling.

### Testing

- `python -m pytest tests/statblocks -v`
```

---

## 14. Design reminder

The API call produces a **draft**.

Buddy turns the draft into an **artifact**.

Corpus promotion turns the artifact into **campaign knowledge**.

The Semantic Knowledge Layer makes that knowledge **retrievable**.

The command board makes it **usable at the table**.

This PR builds the first typed seam in that chain.
