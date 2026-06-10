# HANDOFF — DungeonBuddy statblock lifecycle seam

**Created:** 2026-06-08  
**Updated:** 2026-06-09  
**Repo:** `Drakosfire/DungeonMindBuddy`  
**Target base branch:** `main`  
**Suggested next branch:** `codex/dungeonbuddy-statblock-lifecycle-seam`  
**Depends on:** production DungeonMindServer StatBlock v2 deploy, commit `b3cae86` — v2 draft/render API + internal key lockdown  
**Read first:** `Docs/Plans/REPORT-to-design-agent-statblock-v2-production-deploy-2026-06-09.md`  
**Primary design:** `Docs/Design/DESIGN-statblock-lifecycle-agentic-workbench.md`  
**Related roadmap:** `Docs/Plans/PLAN-command-board-combat-statblock-generator-roadmap.md`  
**Related design:** `Docs/Design/DESIGN-command-board-combat-statblock-generator-integration.md`  
**Mode:** Consumer seam + lifecycle bones implementation handoff. Keep this slice narrow.

---

## 0. Re-anchor

DungeonMindServer production now exposes the live v2 StatBlockGenerator producer contract:

```text
GET  /api/statblockgenerator/v2/health
POST /api/statblockgenerator/v2/generate-draft
POST /api/statblockgenerator/v2/render-draft
```

Those endpoints return or wrap live-combat draft envelopes with:

- structured statblock;
- rendered markdown;
- deterministic combat defaults;
- warnings;
- provenance;
- lifecycle state;
- review status.

The endpoints require `X-DungeonBuddy-Internal-Key`, injected server-side only by Buddy. The browser must never receive this key.

The next DungeonBuddy PR should create the **statblock lifecycle seam**: v2 producer client/provider + Buddy-side `StatblockDraftArtifact` bones + command names for future agent operations.

It should not yet build the Workbench UI, Combat Pane generator UI, corpus promotion, ingestion, or combat mutation.

---

## 1. Product north star

The goal is not only to call StatBlockGenerator. The goal is to make the existing StatBlockGenerator workflow API-driven, agent-operable, and visible through dedicated DungeonBuddy surfaces.

North-star lifecycle:

```text
idea / planning need
→ description draft
→ human approval
→ statblock generation job
→ review surface
→ stored draft artifact
→ corpus promotion preview
→ corpus write
→ breadcrumb + semantic ingestion
→ command-board retrieval
→ statblock drilldown
→ add to combat
```

The core object is a `StatblockDraftArtifact`, not a loose string response.

---

## 2. Architecture position

Use Option B:

```text
DungeonBuddy frontend
→ DungeonBuddy backend / command-board API / agent tool layer
→ DungeonMindServer StatBlockGenerator v2 API
```

Do **not** make the live-control frontend call DungeonMindServer directly as the main product path.

Why:

1. DungeonBuddy should own command-board state, live-session state, corpus references, breadcrumbs, and request shaping.
2. DungeonMindServer should own generation internals and the StatBlockGenerator producer contract.
3. DungeonBuddy may eventually become part of DungeonMindServer. If so, the proxy/client layer can collapse into an internal service call.
4. If DungeonBuddy remains separate, it should avoid managing anything beyond routing frontend requests, enriching them with live/corpus context, and managing state.
5. This keeps the frontend stable if the generator service moves from HTTP to in-process calls later.
6. This keeps service credentials out of frontend code and browser-visible config.

Practical rule for this PR:

> Build a thin Buddy-owned adapter boundary and draft artifact model. Do not duplicate StatBlockGenerator logic in DungeonBuddy. Do not expose the internal API key to the browser.

---

## 3. PR goal

Add the first Buddy statblock lifecycle seam.

Minimum product flow for this PR:

```text
Buddy frontend/backend code builds a StatBlockDraftRequest
→ Buddy backend/proxy attaches internal service credential
→ Buddy proxy/client sends it to DungeonMindServer v2 generate-draft / render-draft or mock provider
→ Buddy receives StatBlockDraftResponse
→ Buddy maps it into StatblockDraftArtifact
→ tests assert markdown/defaults/warnings/provenance/breadcrumbs/status are preserved
```

No UI yet unless it is a tiny dev-only smoke surface. Prefer tests, fixtures, and boring adapters first.

---

## 4. Design boundaries

### DungeonBuddy owns

- frontend request routing;
- server-side proxy/client call into DungeonMindServer;
- internal API-key injection, never browser exposure;
- draft artifact creation and lifecycle state;
- future agent command interface;
- live command-board state;
- encounter/session context assembly;
- corpus/source refs and breadcrumbs;
- decision to accept a generated draft into live combat state;
- later decision to promote a reviewed draft into corpus through Buddy's safe write path;
- later ingestion into the Semantic Knowledge Layer.

### DungeonMindServer owns

- internal API-key validation for v2 producer endpoints;
- StatBlockGenerator model/prompt/provider internals;
- statblock generation;
- statblock markdown rendering for v2 drafts;
- deterministic combat defaults from `StatBlockDetails`;
- producer-side warnings/provenance.

### DungeonBuddy must not own in this slice

- D&D statblock generation internals;
- CR/balance math beyond passing through server warnings;
- markdown rendering from raw `StatBlockDetails`;
- corpus statblock writes;
- Semantic Knowledge Layer ingestion;
- Combat Pane UI;
- Workbench UI;
- initiative-barrel insertion.

---

## 5. Recommended implementation shape

Exact paths may shift with current live-control architecture. The important shape is provider separation, artifact mapping, command-name definitions, and server-side credential handling.

Likely files:

```text
apps/live-control-ui/src/api/statblockGenerator/types.ts
apps/live-control-ui/src/api/statblockGenerator/client.ts
apps/live-control-ui/src/api/statblockGenerator/mockProvider.ts
apps/live-control-ui/src/api/statblockGenerator/artifactMapper.ts
apps/live-control-ui/src/api/statblockGenerator/lifecycleCommands.ts
apps/live-control-ui/src/api/statblockGenerator/fixtures/generatedDraftResponse.fixture.json
apps/live-control-ui/src/api/statblockGenerator/fixtures/renderedDraftResponse.fixture.json
apps/live-control-ui/src/api/statblockGenerator/__tests__/client.test.ts
apps/live-control-ui/src/api/statblockGenerator/__tests__/artifactMapper.test.ts
```

If the HTTP provider would require the internal key, do **not** put that provider in browser-executed code. Prefer a Buddy backend/proxy handler.

Potential Buddy backend/proxy shape:

```text
POST /api/live/statblock-generator/health
POST /api/live/statblock-generator/generate-draft
POST /api/live/statblock-generator/render-draft
```

or as live commands:

```text
POST /api/live/commands
command_type: statblock.generator.health
command_type: statblock.draft.generate
command_type: statblock.draft.render
```

Do not overbuild the routing layer in this PR. A thin internal service/client with tests is enough if the command endpoint shape is not settled.

---

## 6. Contract types to mirror from DungeonMindServer

Mirror the v2 API contract as TypeScript types. Keep names close to the server models so drift is obvious.

Minimum request types:

```ts
export type DraftMode =
  | "generate_from_prompt"
  | "generate_from_source_statblock"
  | "revise_existing"
  | "quick_reinforcement"
  | "terrain_pressure"
  | "render_existing";

export interface StatBlockDraftRequest {
  request_id?: string | null;
  mode: DraftMode;
  intent: DraftIntent;
  prompt?: string | null;
  source_statblock?: unknown | null;
  revision_instructions?: string[];
  encounter_context?: EncounterContext | null;
  terrain_context?: TerrainContext | null;
  source_refs?: SourceRef[];
  output_options?: OutputOptions;
}

export interface StatBlockDraftRenderRequest {
  request_id?: string | null;
  statblock: unknown;
  source_refs?: SourceRef[];
  output_options?: OutputOptions;
}
```

Minimum response types:

```ts
export interface StatBlockDraftResponse {
  success: boolean;
  draft?: StatBlockDraft | null;
  error?: ContractError | null;
  timestamp: string;
}

export interface StatBlockDraft {
  draft_id: string;
  lifecycle_state: "live_draft";
  review_status: "needs_dm_review" | "warnings" | "failed";
  statblock: unknown;
  markdown: string;
  combat_defaults: CombatDefaults;
  warnings: ReviewWarning[];
  provenance: DraftProvenance;
}
```

For the first Buddy PR, `statblock` may remain `unknown` or a partial structural type. Do not recreate the full Python `StatBlockDetails` tree unless an existing generated schema already exists.

---

## 7. Buddy-side artifact bones

Add a Buddy-side artifact wrapper around the server response.

```ts
export interface StatblockDraftArtifact {
  artifact_id: string;
  draft_id: string;
  title: string;

  markdown: string;
  structured_statblock: unknown;
  combat_defaults: CombatDefaults;
  warnings: ReviewWarning[];
  provenance: DraftProvenance;

  review_status: StatblockReviewStatus;
  lifecycle_state: StatblockLifecycleState;
  storage_status: StatblockStorageStatus;
  corpus_status: StatblockCorpusStatus;

  source_refs: SourceRef[];
  breadcrumbs: StatblockBreadcrumb[];

  created_by: "human" | "agent" | "planning_task" | "combat_task";
  created_at: string;
  updated_at: string;
}
```

Lifecycle/status enums:

```ts
export type StatblockLifecycleState =
  | "description_requested"
  | "description_drafted"
  | "description_approved"
  | "generation_requested"
  | "live_draft"
  | "needs_review"
  | "reviewed"
  | "stored_artifact"
  | "promotion_previewed"
  | "corpus_promoted"
  | "indexed"
  | "combat_ready";

export type StatblockStorageStatus =
  | "not_stored"
  | "stored_draft"
  | "exported"
  | "archived";

export type StatblockCorpusStatus =
  | "not_promoted"
  | "promotion_previewed"
  | "promotion_confirmed"
  | "write_failed"
  | "indexed"
  | "retrievable";
```

Artifact mapping rules:

- `artifact.markdown = response.draft.markdown`
- `artifact.structured_statblock = response.draft.statblock`
- `artifact.combat_defaults = response.draft.combat_defaults`
- `artifact.warnings = response.draft.warnings`
- `artifact.provenance = response.draft.provenance`
- `artifact.review_status = response.draft.review_status`
- `artifact.lifecycle_state = "live_draft"` initially
- `artifact.storage_status = "not_stored"` initially
- `artifact.corpus_status = "not_promoted"` initially
- `artifact.source_refs = response.draft.provenance.source_refs`
- `artifact.breadcrumbs` may be empty initially but the field must exist

---

## 8. Agent command-name constants

Define command names now, even if most are not implemented yet.

```ts
export const STATBLOCK_COMMANDS = {
  GENERATOR_HEALTH: "statblock.generator.health",
  DESCRIPTION_REQUEST: "statblock.description.request",
  DESCRIPTION_APPROVE: "statblock.description.approve",
  DRAFT_GENERATE: "statblock.draft.generate",
  DRAFT_RENDER: "statblock.draft.render",
  DRAFT_REVIEW: "statblock.draft.review",
  DRAFT_STORE: "statblock.draft.store",
  CORPUS_PREVIEW_PROMOTE: "statblock.corpus.preview_promote",
  CORPUS_CONFIRM_PROMOTE: "statblock.corpus.confirm_promote",
  CORPUS_INGEST: "statblock.corpus.ingest",
  COMBAT_ADD: "statblock.combat.add",
} as const;
```

Immediate implementation may only wire health/generate/render. The namespace should still point to the full lifecycle.

---

## 9. Client / provider interface

Create a provider-neutral interface:

```ts
export interface StatBlockGeneratorProvider {
  health(): Promise<StatBlockGeneratorHealth>;
  generateDraft(request: StatBlockDraftRequest): Promise<StatBlockDraftResponse>;
  renderDraft(request: StatBlockDraftRenderRequest): Promise<StatBlockDraftResponse>;
}
```

Then implement:

```text
MockStatBlockGeneratorProvider
DungeonMindServerStatBlockGeneratorProvider // server-side only if it uses internal API key
```

The mock provider should return stable fixtures. The HTTP provider should call the live v2 DungeonMindServer endpoints.

Suggested env/config names:

```text
DUNGEONMIND_SERVER_URL
DUNGEONBUDDY_INTERNAL_API_KEY
STATBLOCK_GENERATOR_PROVIDER=mock|http
```

Header:

```text
X-DungeonBuddy-Internal-Key: <secret>
```

Use existing repo conventions if they differ.

---

## 10. Proxy principle

If this slice includes a Buddy backend route, its job is only to:

1. accept a frontend request;
2. enrich it minimally if explicitly available;
3. attach the internal API key from server-side config;
4. call the provider;
5. map the response to `StatblockDraftArtifact` if requested by that route;
6. return the v2 response envelope or artifact wrapper;
7. record logs suitable for debugging without logging secrets.

It should not mutate corpus. It should not save generated drafts. It should not insert into combat. It should not rewrite statblock markdown. It must not return the internal API key or server-side config to the frontend.

---

## 11. Fixtures

Add two Buddy-side fixtures modeled on the server response envelope:

```text
apps/live-control-ui/src/api/statblockGenerator/fixtures/generatedDraftResponse.fixture.json
apps/live-control-ui/src/api/statblockGenerator/fixtures/renderedDraftResponse.fixture.json
```

Each should include:

- `success: true`;
- `draft.lifecycle_state: live_draft`;
- non-empty `draft.markdown`;
- `draft.combat_defaults.name`, `armor_class`, `hit_points`, `primary_actions`;
- warnings array;
- provenance with `mode`, `source_refs`, `generated_at`, `adapter_version`, and `generator`.

These do not need to be real generated monsters. They need to pin the consumer shape.

---

## 12. Test expectations

Add tests that prove the seam and artifact mapping, not the final product.

Minimum tests:

1. **Types/fixture smoke**
   - fixture parses as `StatBlockDraftResponse` shape;
   - successful response has a draft;
   - draft has markdown, combat defaults, warnings, provenance.

2. **Mock provider smoke**
   - `generateDraft()` returns generated fixture;
   - `renderDraft()` returns rendered fixture;
   - consumers can read `combat_defaults` without inspecting `statblock`.

3. **HTTP/server provider request shape**
   - `generateDraft()` posts to `/api/statblockgenerator/v2/generate-draft`;
   - `renderDraft()` posts to `/api/statblockgenerator/v2/render-draft`;
   - `health()` gets `/api/statblockgenerator/v2/health`;
   - tests mock `fetch` / request library, no live network call.

4. **Internal key handling**
   - server-side HTTP provider includes `X-DungeonBuddy-Internal-Key`;
   - provider refuses or clearly errors if configured for HTTP without required key;
   - tests assert the key is not included in any frontend-exposed fixture/config object;
   - logs/errors do not include the key value.

5. **Artifact mapper**
   - response maps to `StatblockDraftArtifact`;
   - markdown, structured statblock, combat defaults, warnings, provenance, and source refs are preserved;
   - storage status starts as `not_stored`;
   - corpus status starts as `not_promoted`;
   - breadcrumbs field exists even if empty.

6. **Error envelope handling**
   - `success=false` response preserves `error.code`, `error.message`, and `timestamp`;
   - provider does not throw away server-side contract errors.

Optional:

7. **Buddy proxy smoke** if a backend route is added
   - frontend request → Buddy route → mocked provider → same envelope/artifact back.

---

## 13. Out of scope

Do not build the Workbench UI.

Do not build the Combat Pane generator UI.

Do not add a Statblock View button yet.

Do not add combat entity insertion.

Do not add corpus promotion.

Do not add Semantic Knowledge Layer ingestion.

Do not add generated-draft persistence beyond typed artifact construction.

Do not duplicate StatBlockGenerator Pydantic validation in TypeScript beyond lightweight shape checks.

Do not make browser-executed frontend code call DungeonMindServer directly with an internal key.

Do not store internal secrets in frontend `.env` variables, bundle-time config, static assets, or test fixtures.

---

## 14. Acceptance criteria

The next PR is ready when:

- DungeonBuddy has a typed `StatBlockGeneratorProvider` interface;
- mock and server-side HTTP providers exist, or a clear Buddy backend proxy exists with mocked provider tests;
- request/response types mirror the DungeonMindServer v2 draft contract, including `render_existing` and `renderDraft`;
- tests prove health, generate-draft, and render-draft request paths without live network calls;
- server-side HTTP calls include the internal API-key header from server-side config;
- no browser-visible code or fixture contains the internal key;
- `StatblockDraftArtifact` type exists;
- lifecycle/storage/corpus status enums exist;
- lifecycle command-name constants exist;
- artifact mapper preserves markdown, structured statblock, combat defaults, warnings, provenance, source refs, and status defaults;
- error envelope handling is covered;
- no UI/product flow depends on this yet;
- no corpus, ingestion, or combat-state mutation occurs.

---

## 15. Suggested PR description

```markdown
### Motivation

DungeonMindServer now exposes live StatBlockGenerator v2 draft/render APIs. This PR adds the DungeonBuddy statblock lifecycle seam so Buddy can request or render statblock drafts through a server-side adapter, map the response into a Buddy draft artifact, and prepare for future agent-operable review, storage, corpus promotion, retrieval, and combat hydration workflows.

### Description

- Added TypeScript request/response types mirroring the StatBlockGenerator v2 draft contract.
- Added a provider-neutral `StatBlockGeneratorProvider` interface.
- Added mock and server-side HTTP providers for health, generate-draft, and render-draft.
- Added internal API-key header injection in the server-side provider/proxy.
- Added `StatblockDraftArtifact` type and lifecycle/storage/corpus status enums.
- Added statblock lifecycle command-name constants for future agent operations.
- Added generated/rendered draft fixtures used by tests.
- Added an artifact mapper from `StatBlockDraftResponse` to `StatblockDraftArtifact`.
- Added tests for fixture shape, mock provider behavior, HTTP route shape, internal-key handling, artifact mapping, and error envelope preservation.

### Testing

- `<repo-appropriate test command>`
```

---

## 16. Design note for the agent

Keep the seam boring but future-shaped.

The important decision is architectural, not visual: DungeonBuddy owns state/routing/context, server-side credential handling, draft artifact lifecycle, breadcrumbs, and future corpus promotion. DungeonMindServer owns generation and v2 producer auth.

The API call produces a draft. Buddy turns that draft into an artifact. Corpus promotion turns the artifact into campaign knowledge. The Semantic Knowledge Layer makes it retrievable. The command board makes it usable at the table.

Do not jump straight to inline combat generation until this lifecycle seam is proven.
