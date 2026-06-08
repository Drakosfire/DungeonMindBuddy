# HANDOFF — DungeonBuddy StatBlockGenerator proxy/client seam

**Created:** 2026-06-08  
**Repo:** `Drakosfire/DungeonMindBuddy`  
**Target base branch:** `main`  
**Suggested next branch:** `codex/dungeonbuddy-statblockgenerator-proxy-client`  
**Depends on:** DungeonMindServer PR #9 / `72e565b91d0611b1f786c540270ffda469e17654` — Implement StatBlockGenerator v2 draft API  
**Related roadmap:** `Docs/Plans/PLAN-command-board-combat-statblock-generator-roadmap.md`  
**Related design:** `Docs/Design/DESIGN-command-board-combat-statblock-generator-integration.md`  
**Mode:** Consumer seam implementation handoff. Keep this slice narrow.

---

## 0. Re-anchor

DungeonMindServer now exposes the first v2 StatBlockGenerator producer contract:

```text
GET  /api/statblockgenerator/v2/health
POST /api/statblockgenerator/v2/generate-draft
```

That endpoint returns a live-combat draft envelope with:

- structured statblock;
- rendered markdown;
- deterministic combat defaults;
- warnings;
- provenance;
- lifecycle state.

The next DungeonBuddy PR should create the **consumer seam**. It should not yet build the Combat Pane generator UI, rewrite combat state, or add corpus promotion.

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

Practical rule for this PR:

> Build a thin Buddy-owned adapter boundary. Do not duplicate StatBlockGenerator logic in DungeonBuddy.

---

## 2. PR goal

Add a typed StatBlockGenerator client/proxy seam in DungeonBuddy that can call the DungeonMindServer v2 draft API or a mock provider through the same interface.

Minimum product flow for this PR:

```text
Buddy code builds a StatBlockDraftRequest
→ Buddy proxy/client sends it to DungeonMindServer v2 generate-draft or mock provider
→ Buddy receives StatBlockDraftResponse
→ tests assert markdown/defaults/warnings/provenance are preserved
```

No UI yet unless it is a tiny dev-only smoke surface. Prefer tests and a boring adapter first.

---

## 3. Design boundaries

### DungeonBuddy owns

- frontend request routing;
- live command-board state;
- encounter/session context assembly;
- corpus/source refs;
- decision to accept a generated draft into live combat state;
- later decision to promote a reviewed draft into corpus through Buddy's safe write path.

### DungeonMindServer owns

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

This depends on the current live-control architecture, so the exact file paths may shift. The important shape is provider separation.

Likely files:

```text
apps/live-control-ui/src/api/statblockGenerator/types.ts
apps/live-control-ui/src/api/statblockGenerator/client.ts
apps/live-control-ui/src/api/statblockGenerator/mockProvider.ts
apps/live-control-ui/src/api/statblockGenerator/httpProvider.ts
apps/live-control-ui/src/api/statblockGenerator/fixtures/statblockDraftResponse.fixture.json
apps/live-control-ui/src/api/statblockGenerator/__tests__/client.test.ts
```

If DungeonBuddy already has a backend API / command router layer for live-control, prefer placing the server/proxy handler there and keeping the frontend API client pointed at Buddy, not directly at DungeonMindServer.

Potential backend/proxy shape if applicable:

```text
POST /api/live/statblock-generator/health
POST /api/live/statblock-generator/generate-draft
```

or as live commands:

```text
POST /api/live/commands
command_type: statblock_generator.health
command_type: statblock_generator.generate_draft
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
  | "terrain_pressure";

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

## 6. Client interface

Create a provider-neutral interface:

```ts
export interface StatBlockGeneratorProvider {
  health(): Promise<StatBlockGeneratorHealth>;
  generateDraft(request: StatBlockDraftRequest): Promise<StatBlockDraftResponse>;
}
```

Then implement:

```text
MockStatBlockGeneratorProvider
HttpStatBlockGeneratorProvider
```

The mock provider should return a stable fixture. The HTTP provider should call the v2 DungeonMindServer endpoints.

Configuration should allow selecting mock vs HTTP without changing consumer code.

Suggested env/config names:

```text
DUNGEONMIND_SERVER_URL
STATBLOCK_GENERATOR_PROVIDER=mock|http
```

Use whatever naming convention already exists in the repo if there is one.

---

## 7. Proxy principle

If this slice includes a Buddy backend route, its job is only to:

1. accept a frontend request;
2. enrich it minimally if explicitly available;
3. call the provider;
4. return the v2 response envelope unchanged or with a tiny Buddy wrapper;
5. record logs suitable for debugging.

It should not mutate corpus. It should not save generated drafts. It should not insert into combat. It should not rewrite statblock markdown.

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
- provenance with `mode`, `source_refs`, `generated_at`, `adapter_version`.

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
   - consumers can read `combat_defaults` without inspecting `statblock`.

3. **HTTP provider request shape**
   - `generateDraft()` posts to `/api/statblockgenerator/v2/generate-draft`;
   - `health()` gets `/api/statblockgenerator/v2/health`;
   - tests mock `fetch` / request library, no live network call.

4. **Error envelope handling**
   - `success=false` response preserves `error.code`, `error.message`, and `timestamp`;
   - provider does not throw away server-side contract errors.

Optional:

5. **Buddy proxy smoke** if a backend route is added
   - frontend request → Buddy route → mocked provider → same envelope back.

---

## 10. Out of scope

Do not build the Combat Pane generator UI.

Do not add a Statblock View button yet.

Do not add combat entity insertion.

Do not add corpus promotion.

Do not add generated-draft persistence.

Do not duplicate StatBlockGenerator Pydantic validation in TypeScript beyond lightweight shape checks.

Do not make frontend code depend directly on DungeonMindServer in a way that cannot be swapped for an in-process or backend-proxied call later.

---

## 11. Acceptance criteria

The next PR is ready when:

- DungeonBuddy has a typed `StatBlockGeneratorProvider` interface;
- mock and HTTP providers exist, or a clear Buddy backend proxy exists with mocked provider tests;
- request/response types mirror the DungeonMindServer v2 draft contract;
- tests prove health and generate-draft request paths without live network calls;
- a successful draft response fixture preserves markdown, combat defaults, warnings, and provenance;
- error envelope handling is covered;
- no UI/product flow depends on this yet;
- no corpus or combat-state mutation occurs.

---

## 12. Suggested PR description

```markdown
### Motivation

DungeonMindServer now exposes a StatBlockGenerator v2 draft API. This PR adds the DungeonBuddy consumer seam so the command board can eventually request generated statblock drafts through a Buddy-owned adapter/proxy rather than coupling the frontend directly to generator internals.

### Description

- Added TypeScript request/response types mirroring the StatBlockGenerator v2 draft contract.
- Added a provider-neutral `StatBlockGeneratorProvider` interface.
- Added mock and HTTP providers for health and generate-draft.
- Added a fixture draft response used by tests.
- Added tests for fixture shape, mock provider behavior, HTTP route shape, and error envelope preservation.

### Testing

- `<repo-appropriate test command>`
```

---

## 13. Design note for the agent

Keep the seam boring.

The important decision is architectural, not visual: DungeonBuddy owns state/routing/context; DungeonMindServer owns generation. This PR should make that boundary real with types, providers, fixtures, and tests.

Once this lands, the next useful slice is either:

1. a tiny developer smoke surface that calls the provider and renders returned markdown/defaults; or
2. a `StatblockView` integration that can call `generateDraft()` from a known source statblock.

Do not jump straight to inline combat generation until this seam is proven.
