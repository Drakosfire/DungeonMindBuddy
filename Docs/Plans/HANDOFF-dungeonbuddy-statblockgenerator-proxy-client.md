# HANDOFF — DungeonBuddy StatBlockGenerator proxy/client seam

**Created:** 2026-06-08  
**Updated:** 2026-06-08  
**Repo:** `Drakosfire/DungeonMindBuddy`  
**Target base branch:** `main`  
**Suggested next branch:** `codex/dungeonbuddy-statblockgenerator-proxy-client`  
**Depends on:** DungeonMindServer PR #9 / `72e565b91d0611b1f786c540270ffda469e17654` — Implement StatBlockGenerator v2 draft API  
**Also depends on:** DungeonMindServer PR #10 / `17ed495d7cebbff28c833788a5cccf3b3728eb53` — Add StatBlockGenerator v2 `render-draft` endpoint  
**Security dependency:** `Drakosfire/DungeonMindServer/Docs/Plans/HANDOFF-statblockgenerator-v2-internal-api-key.md` — lock v2 endpoints behind an internal API key before production use  
**Related roadmap:** `Docs/Plans/PLAN-command-board-combat-statblock-generator-roadmap.md`  
**Related design:** `Docs/Design/DESIGN-command-board-combat-statblock-generator-integration.md`  
**Mode:** Consumer seam implementation handoff. Keep this slice narrow.

---

## 0. Re-anchor

DungeonMindServer now exposes the first v2 StatBlockGenerator producer contract:

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
- lifecycle state.

The next DungeonBuddy PR should create the **consumer seam**. It should not yet build the Combat Pane generator UI, rewrite combat state, or add corpus promotion.

**Security re-anchor:** DungeonMindServer is internet-reachable. The v2 endpoints are intended for internal product consumers, not public anonymous callers. DungeonBuddy should be designed to call them through a Buddy-owned backend/proxy that injects an internal API key server-side only. The browser must never receive this key.

---

## 1. Long-term architecture position

Choose **Option B** from the design discussion:

```text
DungeonBuddy frontend
→ DungeonBuddy backend / command-board API / agent tool layer
→ DungeonMindServer StatBlockGenerator v2 API
```

Do **not** make the live-control frontend call DungeonMindServer directly as the main product path.

Why:

1. DungeonBuddy should own command-board state, live-session state, corpus references, and request shaping.
2. DungeonMindServer should own generation internals and the StatBlockGenerator producer contract.
3. DungeonBuddy may eventually become part of DungeonMindServer. If that happens, the proxy/client layer can collapse into an internal service call.
4. If DungeonBuddy remains separate, it should avoid managing anything beyond routing frontend requests, enriching them with live/corpus context, and managing state.
5. This keeps the frontend stable if the generator service moves from HTTP to in-process calls later.
6. This keeps service credentials out of frontend code and browser-visible config.

Practical rule for this PR:

> Build a thin Buddy-owned adapter boundary. Do not duplicate StatBlockGenerator logic in DungeonBuddy. Do not expose the internal API key to the browser.

---

## 2. PR goal

Add a typed StatBlockGenerator client/proxy seam in DungeonBuddy that can call the DungeonMindServer v2 draft API or a mock provider through the same interface.

Minimum product flow for this PR:

```text
Buddy frontend/backend code builds a StatBlockDraftRequest
→ Buddy backend/proxy attaches internal service credential
→ Buddy proxy/client sends it to DungeonMindServer v2 generate-draft / render-draft or mock provider
→ Buddy receives StatBlockDraftResponse
→ tests assert markdown/defaults/warnings/provenance are preserved
```

No UI yet unless it is a tiny dev-only smoke surface. Prefer tests and a boring adapter first.

---

## 3. Design boundaries

### DungeonBuddy owns

- frontend request routing;
- server-side proxy/client call into DungeonMindServer;
- internal API-key injection, never browser exposure;
- live command-board state;
- encounter/session context assembly;
- corpus/source refs;
- decision to accept a generated draft into live combat state;
- later decision to promote a reviewed draft into corpus through Buddy's safe write path.

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
- Combat Pane UI;
- initiative-barrel insertion.

---

## 4. Recommended implementation shape

This depends on the current live-control architecture, so the exact file paths may shift. The important shape is provider separation and keeping the service credential server-side.

Likely frontend-adjacent type/client files:

```text
apps/live-control-ui/src/api/statblockGenerator/types.ts
apps/live-control-ui/src/api/statblockGenerator/client.ts
apps/live-control-ui/src/api/statblockGenerator/mockProvider.ts
apps/live-control-ui/src/api/statblockGenerator/fixtures/statblockDraftResponse.fixture.json
apps/live-control-ui/src/api/statblockGenerator/__tests__/client.test.ts
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
command_type: statblock_generator.health
command_type: statblock_generator.generate_draft
command_type: statblock_generator.render_draft
```

Do not overbuild the routing layer in this PR. A thin internal service/client with tests is enough if the command endpoint shape is not settled.

---

## 5. Contract types to mirror from DungeonMindServer

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

For the first Buddy PR, `statblock` may remain `unknown` or a partial structural type. Do not try to recreate the full Python `StatBlockDetails` tree unless an existing generated schema already exists.

---

## 6. Client / provider interface

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

The mock provider should return stable fixtures. The HTTP provider should call the v2 DungeonMindServer endpoints.

Configuration should allow selecting mock vs HTTP without changing consumer code.

Suggested env/config names:

```text
DUNGEONMIND_SERVER_URL
DUNGEONMIND_INTERNAL_API_KEY
STATBLOCK_GENERATOR_PROVIDER=mock|http
```

Header name should match the DungeonMindServer security PR. Suggested header if no existing convention wins:

```text
X-DungeonBuddy-Internal-Key: <secret>
```

Use whatever naming convention already exists in the repo if there is one.

---

## 7. Proxy principle

If this slice includes a Buddy backend route, its job is only to:

1. accept a frontend request;
2. enrich it minimally if explicitly available;
3. attach the internal API key from server-side config;
4. call the provider;
5. return the v2 response envelope unchanged or with a tiny Buddy wrapper;
6. record logs suitable for debugging without logging secrets.

It should not mutate corpus. It should not save generated drafts. It should not insert into combat. It should not rewrite statblock markdown. It must not return the internal API key or server-side config to the frontend.

This keeps the long-term boundary clean whether DungeonBuddy merges into DungeonMindServer or remains a separate state/router service.

---

## 8. Smoke fixture

Add one Buddy-side fixture modeled on the server response envelope.

Suggested file:

```text
apps/live-control-ui/src/api/statblockGenerator/fixtures/statblockDraftResponse.fixture.json
```

It should include:

- `success: true`;
- `draft.lifecycle_state: live_draft`;
- non-empty `draft.markdown`;
- `draft.combat_defaults.name`, `armor_class`, `hit_points`, `primary_actions`;
- at least one warning;
- provenance with `mode`, `source_refs`, `generated_at`, `adapter_version`, and `generator`.

This does not need to be a real generated monster. It just needs to pin the consumer shape.

---

## 9. Test expectations

Add tests that prove the seam, not the final product.

Minimum tests:

1. **Types/fixture smoke**
   - fixture parses as `StatBlockDraftResponse` shape;
   - successful response has a draft;
   - draft has markdown, combat defaults, warnings, provenance.

2. **Mock provider smoke**
   - `generateDraft()` returns the fixture;
   - `renderDraft()` returns the fixture or a render-specific fixture;
   - consumers can read `combat_defaults` without inspecting `statblock`.

3. **HTTP/server provider request shape**
   - `generateDraft()` posts to `/api/statblockgenerator/v2/generate-draft`;
   - `renderDraft()` posts to `/api/statblockgenerator/v2/render-draft`;
   - `health()` gets `/api/statblockgenerator/v2/health`;
   - tests mock `fetch` / request library, no live network call.

4. **Internal key handling**
   - server-side HTTP provider includes the configured internal API-key header;
   - provider refuses or clearly errors if configured for HTTP without required key;
   - tests assert the key is not included in any frontend-exposed fixture/config object;
   - logs/errors do not include the key value.

5. **Error envelope handling**
   - `success=false` response preserves `error.code`, `error.message`, and `timestamp`;
   - provider does not throw away server-side contract errors.

Optional:

6. **Buddy proxy smoke** if a backend route is added
   - frontend request → Buddy route → mocked provider → same envelope back.

---

## 10. Out of scope

Do not build the Combat Pane generator UI.

Do not add a Statblock View button yet.

Do not add combat entity insertion.

Do not add corpus promotion.

Do not add generated-draft persistence.

Do not duplicate StatBlockGenerator Pydantic validation in TypeScript beyond lightweight shape checks.

Do not make browser-executed frontend code call DungeonMindServer directly with an internal key.

Do not store internal secrets in frontend `.env` variables, bundle-time config, static assets, or test fixtures.

---

## 11. Acceptance criteria

The next PR is ready when:

- DungeonBuddy has a typed `StatBlockGeneratorProvider` interface;
- mock and server-side HTTP providers exist, or a clear Buddy backend proxy exists with mocked provider tests;
- request/response types mirror the DungeonMindServer v2 draft contract, including `render_existing` and `renderDraft`;
- tests prove health, generate-draft, and render-draft request paths without live network calls;
- server-side HTTP calls include the internal API-key header from server-side config;
- no browser-visible code or fixture contains the internal key;
- a successful draft response fixture preserves markdown, combat defaults, warnings, and provenance;
- error envelope handling is covered;
- no UI/product flow depends on this yet;
- no corpus or combat-state mutation occurs.

---

## 12. Suggested PR description

```markdown
### Motivation

DungeonMindServer now exposes StatBlockGenerator v2 draft/render APIs. This PR adds the DungeonBuddy consumer seam so the command board can eventually request generated or rendered statblock drafts through a Buddy-owned adapter/proxy rather than coupling the frontend directly to generator internals or exposing service credentials in the browser.

### Description

- Added TypeScript request/response types mirroring the StatBlockGenerator v2 draft contract.
- Added a provider-neutral `StatBlockGeneratorProvider` interface.
- Added mock and server-side HTTP providers for health, generate-draft, and render-draft.
- Added internal API-key header injection in the server-side provider/proxy.
- Added fixture draft responses used by tests.
- Added tests for fixture shape, mock provider behavior, HTTP route shape, internal-key handling, and error envelope preservation.

### Testing

- `<repo-appropriate test command>`
```

---

## 13. Design note for the agent

Keep the seam boring.

The important decision is architectural, not visual: DungeonBuddy owns state/routing/context and server-side credential handling; DungeonMindServer owns generation and v2 producer auth. This PR should make that boundary real with types, providers, fixtures, and tests.

Once this lands, the next useful slice is either:

1. a tiny developer smoke surface that calls the provider and renders returned markdown/defaults; or
2. a `StatblockView` integration that can call `generateDraft()` or `renderDraft()` from a known source statblock.

Do not jump straight to inline combat generation until this seam is proven.
