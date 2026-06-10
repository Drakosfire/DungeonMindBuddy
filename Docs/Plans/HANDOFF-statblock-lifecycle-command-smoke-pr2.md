# HANDOFF — Statblock lifecycle command smoke PR2

**Created:** 2026-06-09  
**Repo:** `Drakosfire/DungeonMindBuddy`  
**Target base branch:** `main`  
**Suggested next branch:** `codex/statblock-lifecycle-command-smoke-pr2`  
**Depends on:** PR #103 / `23a4f636ccc2188aec8bc3d3db502172a4fbb52a` — Add statblock v2 lifecycle seam  
**Primary design:** `Docs/Design/DESIGN-statblock-lifecycle-agentic-workbench.md`  
**Previous handoff:** `Docs/Plans/HANDOFF-statblock-lifecycle-seam-pr1.md`  
**Production report:** `Docs/Plans/REPORT-to-design-agent-statblock-v2-production-deploy-2026-06-09.md`  
**Mode:** Right-sized implementation handoff. Build an agent-usable command facade and developer smoke harness over the PR #103 seam. No UI, persistence, corpus writes, ingestion, or combat mutation.

---

## 0. Copyable task prompt

```markdown
You are implementing Statblock lifecycle PR2 in `Drakosfire/DungeonMindBuddy`.

Read first:

- `Docs/Plans/HANDOFF-statblock-lifecycle-command-smoke-pr2.md`
- `Docs/Design/DESIGN-statblock-lifecycle-agentic-workbench.md`
- `Docs/Plans/HANDOFF-statblock-lifecycle-seam-pr1.md`
- `Docs/Plans/REPORT-to-design-agent-statblock-v2-production-deploy-2026-06-09.md`

Goal: add a small Python command facade and developer smoke harness over the PR #103 statblock lifecycle seam.

Build support for three command names only:

- `statblock.generator.health`
- `statblock.draft.generate`
- `statblock.draft.render`

The command facade should use the existing provider/client, optionally map successful draft responses into `StatblockDraftArtifact`, and return a typed command result that agents and future UI routes can consume.

Do not build UI. Do not store draft artifacts. Do not mutate combat. Do not write to corpus. Do not ingest into the Semantic Knowledge Layer. Do not expose `DUNGEONBUDDY_INTERNAL_API_KEY` outside server-side Python.
```

---

## 1. Re-anchor

PR #103 merged the first statblock lifecycle seam. DungeonBuddy now has:

```text
src/statblocks/v2_contract.py
src/statblocks/v2_client.py
src/statblocks/lifecycle_artifact.py
src/statblocks/lifecycle_commands.py
```

That gives Buddy:

- production-aware v2 contract models;
- a server-side HTTP provider for DungeonMindServer StatBlockGenerator v2;
- a mock provider;
- `StatblockDraftArtifact` and mapper;
- lifecycle/status enums;
- command-name constants.

The API call produces a **draft**. Buddy turns the draft into an **artifact**. Later corpus promotion turns the artifact into campaign knowledge. This PR should build the next small bridge: a command-level facade that an agent, CLI smoke test, future backend route, or future UI can call without knowing provider details.

---

## 2. Where this PR sits in the next few parts

### Part 1 — Done: lifecycle seam bones

PR #103 added typed models, provider boundary, mock/live client, artifact mapper, command constants, and tests.

### Part 2 — This PR: command facade + smoke harness

Add a small in-process command runner over health/generate/render.

```text
command request
→ provider call
→ v2 response
→ optional artifact mapping
→ command result
→ JSON-safe output for agents/dev smoke
```

This proves the seam is usable by agents without adding product UI.

### Part 3 — Workbench read/review skeleton

After this PR, build a read-only/review skeleton for `StatblockDraftArtifact`: markdown, combat defaults, warnings, provenance, breadcrumbs, and disabled storage/corpus actions.

### Part 4 — Draft storage lane

Persist draft artifacts as prep/live artifacts, still not corpus canon. Add export/copy affordances and status updates.

### Part 5 — Corpus promotion preview

Preview statblock markdown write with frontmatter and breadcrumbs. Require confirmation token. No silent hub mutation.

### Part 6 — Retrieval + Combat consumption

After promotion/indexing works, Statblock View and Combat Pane can retrieve corpus-backed statblocks and add combat-ready defaults into the initiative tracker.

---

## 3. PR goal

Create the first agent-usable command facade for the statblock lifecycle.

Supported commands in this PR:

```text
statblock.generator.health
statblock.draft.generate
statblock.draft.render
```

The facade should be provider-neutral and work with:

```text
MockStatBlockGeneratorProvider
DungeonMindServerStatBlockGeneratorClient
```

It should be usable from tests and from a local developer smoke script.

---

## 4. Suggested implementation shape

Suggested files:

```text
src/statblocks/lifecycle_service.py
scripts/statblock_lifecycle_smoke.py

tests/statblocks/fixtures/generate_draft_request.fixture.json
tests/statblocks/fixtures/render_draft_request.fixture.json

tests/statblocks/test_lifecycle_service.py
tests/statblocks/test_statblock_lifecycle_smoke.py
```

Optional if useful:

```text
src/statblocks/smoke_fixtures.py
```

Do not put browser/Vite code in this PR.

---

## 5. Command request/result models

Create typed Pydantic models for command-level interaction.

Suggested model names:

```python
class StatblockLifecycleCommandRequest(BaseModel): ...
class StatblockLifecycleCommandResult(BaseModel): ...
```

Suggested request shape:

```python
class StatblockLifecycleCommandRequest(BaseModel):
    command_type: str
    payload: dict[str, Any] = Field(default_factory=dict)
    requested_by: str = "agent"
    idempotency_key: str | None = None
    as_artifact: bool = True
    breadcrumbs: list[StatblockBreadcrumb] = Field(default_factory=list)
```

Suggested result shape:

```python
class StatblockLifecycleCommandResult(BaseModel):
    command_type: str
    status: Literal["ok", "error", "unsupported"]
    health: StatBlockGeneratorHealth | None = None
    response: StatBlockDraftResponse | None = None
    artifact: StatblockDraftArtifact | None = None
    error: ContractError | None = None
    diagnostics: list[str] = Field(default_factory=list)
```

Design intent:

- `health` command returns `health` only.
- `generate` and `render` commands return the raw `response`.
- If `as_artifact=True` and response succeeds, also return `artifact`.
- If provider raises `StatBlockGeneratorHTTPError` with a preserved v2 response, return `status="error"` and preserve the response/error instead of throwing away producer details.
- Unsupported commands return `status="unsupported"`, not an unstructured exception.

---

## 6. Command runner behavior

Suggested public function/class:

```python
class StatblockLifecycleService:
    def __init__(self, provider: StatBlockGeneratorProvider): ...

    def execute(
        self, request: StatblockLifecycleCommandRequest,
    ) -> StatblockLifecycleCommandResult: ...
```

Behavior:

### `statblock.generator.health`

- Call `provider.health()`.
- Return `status="ok"` and `health`.
- Do not create an artifact.

### `statblock.draft.generate`

- Validate `payload` as `StatBlockDraftRequest`.
- Call `provider.generate_draft(...)`.
- Return raw `StatBlockDraftResponse`.
- If `as_artifact=True` and response succeeds, map to `StatblockDraftArtifact` using `artifact_from_draft_response(...)`.
- `created_by` should come from request context. For now map `requested_by` conservatively:
  - `human` → `human`
  - `agent` → `agent`
  - `planning_task` → `planning_task`
  - `combat_task` → `combat_task`
  - unknown → `agent`

### `statblock.draft.render`

- Validate `payload` as `StatBlockDraftRenderRequest`.
- Call `provider.render_draft(...)`.
- Return raw response and optional artifact using the same rules.

### Unsupported command

- Return `status="unsupported"` and a `ContractError` with code like `unsupported_command`.
- Do not call provider.

### Error handling

- Preserve v2 error envelopes when the HTTP client raises `StatBlockGeneratorHTTPError` with `response`.
- For local validation/config errors, return a clear `ContractError`; do not leak internal API key values.
- Do not swallow diagnostics, but keep them safe.

---

## 7. Developer smoke script

Add a small CLI harness for local/operator validation.

Suggested path:

```text
scripts/statblock_lifecycle_smoke.py
```

Use stdlib `argparse`; no new dependencies.

Suggested subcommands:

```text
health
generate-fixture
render-fixture
```

Suggested examples:

```bash
uv run python scripts/statblock_lifecycle_smoke.py health --provider mock
uv run python scripts/statblock_lifecycle_smoke.py generate-fixture --provider mock
uv run python scripts/statblock_lifecycle_smoke.py render-fixture --provider mock
```

Optional live examples:

```bash
uv run python scripts/statblock_lifecycle_smoke.py health --provider http
uv run python scripts/statblock_lifecycle_smoke.py generate-fixture --provider http --confirm-live-generate
uv run python scripts/statblock_lifecycle_smoke.py render-fixture --provider http
```

### Script requirements

- Load local env via `src.bootstrap_env.load_dungeonmindbuddy_dotenv()`.
- Default provider should be `mock`.
- `--provider http` should use `DungeonMindServerStatBlockGeneratorClient` and require `DUNGEONBUDDY_INTERNAL_API_KEY`.
- Live generate should be guarded behind `--confirm-live-generate` because it can call OpenAI through DungeonMindServer.
- Health and render are safer live checks; generate is opt-in.
- Output JSON to stdout.
- Never print the internal API key.
- Exit non-zero on `status="error"` or `status="unsupported"` unless an explicit `--allow-error` is added.

---

## 8. Fixtures

Add request fixtures, not just response fixtures:

```text
tests/statblocks/fixtures/generate_draft_request.fixture.json
tests/statblocks/fixtures/render_draft_request.fixture.json
```

`generate_draft_request.fixture.json` should use a supported production mode:

```json
{
  "request_id": "buddy-smoke-generate-ember-wolf",
  "mode": "generate_from_prompt",
  "prompt": "Create a CR 1 ember wolf skirmisher for a volcanic road encounter.",
  "intent": {
    "mode": "generate_from_prompt",
    "creature_name": "Ember Wolf",
    "challenge_rating": "1",
    "role": "skirmisher",
    "tone": "dangerous but table-ready"
  },
  "source_refs": [
    {
      "id": "buddy-smoke-prompt",
      "kind": "prompt",
      "label": "Buddy smoke prompt",
      "reason": "Developer seam test"
    }
  ],
  "output_options": {
    "include_markdown": true,
    "include_json": true,
    "include_combat_defaults": true,
    "include_review_warnings": true,
    "persist": false
  }
}
```

`render_draft_request.fixture.json` should use a simple structured statblock and `mode="render_existing"`.

Do not include secrets in fixtures.

---

## 9. Tests

### 9.1 Service tests

`tests/statblocks/test_lifecycle_service.py`

Cover:

- health command calls provider health and returns `status="ok"`;
- generate command validates payload and calls provider generate;
- render command validates payload and calls provider render;
- successful generate maps to artifact when `as_artifact=True`;
- successful render maps to artifact when `as_artifact=True`;
- `as_artifact=False` returns response but no artifact;
- breadcrumbs are passed through to artifact;
- unsupported command returns `status="unsupported"` and does not call provider;
- HTTP error with preserved v2 envelope returns safe command error;
- validation error returns safe command error;
- error strings do not include a known fake secret.

Use `MockStatBlockGeneratorProvider`; no live network.

### 9.2 Smoke script tests

`tests/statblocks/test_statblock_lifecycle_smoke.py`

Keep this light. Suggested checks:

- script `--help` exits 0;
- `health --provider mock` emits JSON with `status: ok`;
- `generate-fixture --provider mock` emits JSON with an artifact;
- `render-fixture --provider mock` emits JSON with an artifact;
- `generate-fixture --provider http` without `--confirm-live-generate` refuses before network call.

Use subprocess if low-friction, or import a `main(argv)` function directly.

---

## 10. Out of scope

Do not build the Workbench UI.

Do not add React/Vite browser code.

Do not add FastAPI/backend HTTP routes unless the repo already has a clear route seam and the change remains tiny.

Do not modify `src/agent/planner.py` to replace the legacy hook in this PR.

Do not store generated artifacts.

Do not write to corpus.

Do not trigger ingestion.

Do not mutate combat state.

Do not run live generate in default tests.

Do not print or log `DUNGEONBUDDY_INTERNAL_API_KEY`.

---

## 11. Acceptance criteria

The PR is ready when:

- `StatblockLifecycleService` or equivalent command facade exists;
- command request/result models exist;
- health/generate/render command names are supported;
- generate/render commands can return both raw response and mapped artifact;
- unsupported commands are safe and structured;
- HTTP/provider errors preserve useful producer error details;
- no internal key leaks in errors, fixtures, logs, or CLI output;
- request fixtures exist;
- developer smoke script exists and defaults to mock provider;
- live generate requires explicit confirmation;
- tests cover service behavior and smoke script mock behavior;
- no UI, persistence, corpus, ingestion, or combat mutation is added.

---

## 12. Suggested PR description

```markdown
### Motivation

PR #103 added the server-side StatBlockGenerator v2 lifecycle seam. This PR adds the first command-level facade and developer smoke harness so agents, future backend routes, and future UI surfaces can call health/generate/render through one structured interface without knowing provider details or exposing the internal API key.

### Description

- Added statblock lifecycle command request/result models.
- Added `StatblockLifecycleService` over the existing provider/client seam.
- Supported `statblock.generator.health`, `statblock.draft.generate`, and `statblock.draft.render`.
- Mapped successful generate/render responses into `StatblockDraftArtifact` when requested.
- Preserved v2 producer error envelopes in command results.
- Added generate/render request fixtures.
- Added `scripts/statblock_lifecycle_smoke.py` for mock and opt-in live smoke checks.
- Added tests for command execution, artifact mapping, safe errors, fixtures, and smoke script behavior.

### Testing

- `uv run python -m pytest tests/statblocks -v`
```

---

## 13. Design reminder

This PR does not make statblocks visible yet. It makes them **commandable**.

That matters because the end state is not a one-off generator button. The end state is a lifecycle where humans and agents use the same commands:

```text
Draft → Artifact → Review → Store → Promote → Ingest → Retrieve → Use in Combat
```

Build the smallest trustworthy command bridge now. The Workbench can come next.
