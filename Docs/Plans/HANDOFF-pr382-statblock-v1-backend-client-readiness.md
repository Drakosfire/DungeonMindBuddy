# HANDOFF — PR382 DungeonMind statblock v1 backend client and readiness

**Status:** READY FOR DISPATCH
**Workstream:** `SBW01`
**Repository:** `Drakosfire/DungeonMindBuddy`
**Planned base:** `main` after the roadmap/design documentation PR merges; re-anchor to actual `main` SHA at dispatch
**Design authority:** `Docs/Design/DESIGN-threat-statblock-authoring-projection-workflow.md`
**Roadmap:** `Docs/Roadmaps/ROADMAP-threat-statblock-authoring-projection.md`
**Tracker:** `Docs/Plans/PR-TRACKER-threat-statblock-authoring-projection.md`
**Server contract authority:** `Drakosfire/DungeonMindServer/Docs/Design/DESIGN-dungeonbuddy-statblock-contract-v1.md`

> Template note: this handoff predates the current `§0–§11` external-agent capability template used by `SBW02+`. It remains the complete dispatch authority for `SBW01`; review tooling must map its existing sections rather than assuming uniform section numbering.

## 0. Dispatch gate

Do not begin implementation until:

- this handoff is present on the branch base;
- DungeonMindServer main still exposes the internal v1 router and published OpenAPI/client artifacts;
- the existing DungeonBuddy vendored TypeScript contract fingerprint test passes or any baseline failure is recorded;
- the worker has confirmed no newer handoff supersedes `SBW01`.

This PR establishes exactly one capability. Do not pull ThreatDraft, candidate generation, workbench UI, graph, persistence, media, or combat into it.

## 1. Mission

Establish one DungeonBuddy backend adapter that can authenticate to DungeonMindServer statblock v1, read health/readiness, and translate typed transport failures without exposing credentials or adding product workflow.

## 2. Invariant

Every later statblock operation crosses one server-owned typed client boundary; no UI component, route handler, or feature service constructs privileged DungeonMind HTTP requests directly.

## 3. Independently useful outcome

After this PR, DungeonBuddy can answer, through its own backend, whether the DungeonMind statblock v1 integration is configured and which capabilities the downstream service honestly advertises. Later PRs can inject the same client and add generate/validate/create/read operations without inventing transport, configuration, or error semantics again.

## 4. Scope

### 4.1 Configuration

Add strict server-side configuration with these semantic fields:

```text
base_url
internal_api_key
enabled
timeout_seconds
```

Recommended environment names:

```text
DUNGEONMIND_STATBLOCKS_BASE_URL
DUNGEONMIND_STATBLOCKS_INTERNAL_API_KEY
DUNGEONMIND_STATBLOCKS_ENABLED
DUNGEONMIND_STATBLOCKS_TIMEOUT_SECONDS
```

Rules:

- disabled or missing base URL/key is a deterministic local `unavailable` readiness state;
- configuration is loaded only in the server process;
- internal key must never be serialized in a response, exception string, or structured log;
- base URL normalization rejects unsupported schemes and removes only trailing slash ambiguity;
- timeout is positive and bounded by an explicit maximum.

### 4.2 Client boundary

Create one narrow injectable client interface and HTTP implementation.

Minimum public operations in this PR:

```text
get_health()
get_readiness()
get_exact_revision(statblock_id, revision_id)  # may be fake/fixture-proven if live read is feature-gated
```

The interface may declare later methods only when they are fully typed and unimplemented calls fail explicitly. Do not add placeholder methods returning `Any`.

Use DungeonMindServer v1 routes and service authentication. Confirm the exact header name from the current Server contract/code at implementation time; do not infer or duplicate it from old v2 routes.

### 4.3 DTO ownership

- Use generated/contract-derived statblock v1 DTOs.
- Do not create a handwritten canonical `StatblockDefinitionV1` mirror.
- A small DungeonBuddy readiness view model is allowed as a derived projection.
- Parse downstream `ErrorEnvelopeV1` strictly enough to preserve code/message.

If the Python backend cannot directly consume the generated TypeScript artifact, create only transport-envelope models needed by the adapter and lock them against published JSON fixtures/OpenAPI fingerprints. Report before proceeding if this would require duplicating the entire mechanics schema.

### 4.4 Error taxonomy

Expose stable internal exception/result categories:

```text
integration_disabled
integration_misconfigured
downstream_unavailable
downstream_authentication_failed
downstream_timeout
downstream_rate_limited
downstream_invalid_request
downstream_validation_failed
downstream_not_found
downstream_conflict
downstream_unexpected
```

Do not collapse every non-2xx response to `generation_failed`; generation is out of scope.

### 4.5 DungeonBuddy readiness route

Add one narrow DungeonBuddy route only if needed to prove and expose the boundary, for example:

```text
GET /api/live/statblocks/v1/readiness
```

Response semantics should resemble:

```json
{
  "schema": "dmb_statblock_integration_readiness_v1",
  "configured": true,
  "available": true,
  "downstream_status": "ready",
  "contract": "dungeonmind.dungeonbuddy-statblocks",
  "contract_version": "1.0.0",
  "capabilities": ["generation", "read", "persistence"],
  "diagnostics": []
}
```

Do not promise a capability not advertised by the downstream readiness response. Preserve an honest local distinction between configured and available.

No workbench UI is required. A typed `liveApi` function may be added only if a minimal developer/readiness panel or existing capability surface consumes it in this same PR.

## 5. Expected changed paths

The worker must inventory actual paths before editing. Expected scope is bounded to:

```text
apps/live_control_server/services/ or new apps/live_control_server/integrations/
apps/live_control_server/routes/live.py or a narrow statblock integration route module
apps/live_control_server/main.py only if a new router is mounted
apps/live-control-ui/src/api/types.ts       # only if route exposed to UI
apps/live-control-ui/src/api/liveApi.ts     # only if route exposed to UI
focused Python tests for client/readiness
configuration/runbook sample files only when required
```

Allowed discovery exception: current environment/config helper and existing external-service test patterns.

Forbidden expansion:

```text
StatblockWorkbenchModule.tsx
ThreatDraft/domain store
World Graph Kernel/contributions
combat tracker
Markdown/Tiptap nodes
DungeonMindServer code
```

## 6. Observable paths

### Success

- Configured client calls downstream readiness with the internal credential.
- Typed response maps to DungeonBuddy readiness.
- Exact revision read parses a fixture/response and retains exact IDs/digest.

### Disabled/misconfigured

- No downstream call.
- Route/result says unavailable with stable local diagnostic.
- No secret value appears.

### Authentication failure

- Maps to `downstream_authentication_failed`.
- Operator-facing diagnostic does not expose credential contents.

### Timeout/unavailable

- Request is bounded.
- Stable retryable classification.
- No silent fallback to mock data, corpus files, or cached unrelated statblocks.

### Invalid response

- Contract parse fails closed as `downstream_unexpected` or a narrower schema-mismatch category.
- Raw unbounded body is not reflected to the browser/log.

## 7. Tests

Required focused proof:

1. configuration validation and disabled state;
2. success readiness mapping;
3. capability honesty when generation or persistence is disabled;
4. auth failure mapping;
5. timeout mapping;
6. rate-limit/error-envelope mapping;
7. malformed JSON/schema mismatch fail-closed;
8. internal key absent from response/log capture;
9. exact revision fixture retains `statblock_id`, `revision_id`, and `definition_digest`;
10. no downstream call for local disabled/misconfigured state.

Use an injectable fake HTTP transport or mock server. Tests must not require a live DungeonMindServer or real secret.

Run the existing DungeonBuddy contract consumer proof relevant to:

```text
apps/live-control-ui/src/contracts/dungeonbuddy-statblocks-v1/dungeonbuddyStatblockV1Contract.test.ts
```

Record if a sibling Server checkout is required and unavailable; do not weaken the existing proof to make this PR pass.

## 8. Security requirements

- Secret server-side only.
- No query-parameter credential.
- Bounded timeout and response-body handling.
- No arbitrary URL from request input; base URL comes from trusted configuration.
- No redirect to attacker-controlled host unless the chosen HTTP client policy explicitly prevents credential forwarding.
- Validate statblock/revision ID formats before building exact-read paths.
- Do not log full downstream headers or full authored/user content.

## 9. Non-goals

- ThreatDraft CRUD.
- Candidate generation or revision.
- Mechanical validation workflow.
- Saving statblocks.
- Graph publication.
- UI workbench changes.
- Markdown embeds.
- Combat integration.
- Image or 3D media.
- DungeonMindServer changes.
- Generic shared HTTP client framework for unrelated integrations.

## 10. Predecessor and demolition

```text
Replaced path: none
Deleted in this PR: no
Retained reason: this establishes the new boundary before product operations consume it
Named remaining consumer: N/A
Required deletion owner: later slices delete direct/mock/corpus paths when replaced
```

Do not remove the current mock workbench in this PR; no user-facing replacement exists yet.

## 11. Stop conditions

Stop and return a design/implementation report before expanding scope if:

- the Server's current authentication header or readiness route differs materially from the published v1 contract;
- downstream readiness cannot truthfully advertise generation/read/persistence capabilities;
- consuming exact revision responses requires a second handwritten copy of the full statblock mechanics schema;
- an existing DungeonBuddy configuration abstraction requires broad unrelated migration;
- the only available HTTP path would expose the internal key to the browser;
- redirect behavior could forward credentials to an untrusted host and cannot be configured safely in-slice.

## 12. Successor capabilities

- `SBW02`: versioned ThreatDraft store.
- `SBW03`: exact draft-version candidate generation through this client.

Do not implement either successor here.

## 13. Suggested PR body

```markdown
## Outcome

Establish one server-owned DungeonMind statblock v1 client/readiness boundary for all later DungeonBuddy statblock operations.

## Scope

- strict server-side integration configuration
- authenticated health/readiness and exact-revision transport proof
- stable typed downstream error mapping
- honest DungeonBuddy readiness projection
- focused fake-transport tests; no live credentials

## Explicitly out of scope

ThreatDrafts, generation workflow, workbench UI, persistence, graph writes, Markdown, combat, and media.

## Verification

<List exact commands and results.>

## Demolition

No predecessor deleted; this PR establishes the boundary consumed by later replacement slices.
```
