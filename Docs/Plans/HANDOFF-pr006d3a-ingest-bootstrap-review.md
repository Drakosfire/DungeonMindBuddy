# HANDOFF — PR006D3A — Read-only `/ingest` bootstrap review

> Status: READY IMPLEMENTATION HANDOFF
> Parent tracker slice: `PR006D3 — /ingest review and activation UI`
> Predecessor: GitHub PR #337, merged as `815f9d8d0f0582d3b8b7d86038e5d598c0a653b9`
> Base: `origin/main` at `815f9d8d0f0582d3b8b7d86038e5d598c0a653b9`
> Successor: PR006D3B — explicit prepare/confirm activation interaction

## §0 Build in this repo

- **Frontend:** `cd apps/live-control-ui && npm test`, `npm run typecheck`, and `npm run build`.
- **Repository checks:** `git diff --check` and the scope checks in §7.
- **Backend tests are not the owning proof for this slice.** PR006D2 already owns the server contract. This PR must prove the actual `/ingest` rendering boundary with Vitest/Testing Library.
- **Obey `AGENTS.md` and `.cursor/rules/`.** Do not add dependencies, regenerate the backend contract by hand, or introduce a second bootstrap response shape.

## §1 Mission

An `/ingest` user can inspect the approved Eldyrwild bootstrap memory so that activation is understandable before any write is offered.

## §2 Context and boundaries

- **Parent epic / tracker:** `Docs/Plans/PR-TRACKER-campaign-supergraph.md` → PR006D3.
- **Predecessor:** PR006D2, GitHub #337, merged at `815f9d8d0f0582d3b8b7d86038e5d598c0a653b9`.
- **Input this PR consumes:**
  - `GET /api/live/world-graph-bootstrap/status`;
  - the strict Pydantic response models in `apps/live_control_server/models/world_graph_bootstrap.py`;
  - the real generated contract fixture at `tests/fixtures/world_graph_bootstrap/api-contract-v1.json`.
- **What remains false:** no user can prepare, confirm, or publish the bootstrap from the UI.
- **Explicitly not included:**
  - `POST /prepare` or `POST /confirm` clients or controls;
  - confirmation tokens, actor entry, acknowledgement, or publication;
  - Kernel, backend policy, route, fixture, or service changes;
  - Projection Engine, Plan/Play migration, general graph editing, or Graph Review authoring changes;
  - redesign of the existing preview-run Graph Review workbench.

### Why D3 is split here

The tracker-level D3 journey contains two independently useful verbs:

```text
inspect
publish
```

Read-only rendering risks contract drift, omission, misleading trust copy, and unusable information hierarchy. Mutation risks stale proposals, actor/token binding, irreversible publication, idempotency, and truthful post-commit reporting. They require different review boundaries and must not be stabilized in one PR.

PR006D3A therefore establishes only the read side. PR006D3B may add prepare/confirm after this review surface is accepted.

## §3 Authoritative inputs

Read these in order before changing code:

1. `Docs/Plans/PR-TRACKER-campaign-supergraph.md` — PR006D and PR006D3.
2. `Docs/Design/ARCHITECTURE-campaign-supergraph.md` — read/write separation, surface ownership, and World Supergraph authority.
3. `apps/live_control_server/models/world_graph_bootstrap.py` — exact field names, states, classifications, trust boundary, receipt, and evidence-locator status.
4. `tests/fixtures/world_graph_bootstrap/api-contract-v1.json` — canonical schemas and examples produced by real service operations.
5. `apps/live_control_server/routes/world_graph_bootstrap.py` — status route and direct stable error-body behavior.
6. `apps/live-control-ui/src/ingestSurface/MemoryIngestPage.tsx` — `/ingest` mounting seam.
7. `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewWorkbenchModule.tsx` — existing Graph Review consumer that must remain intact.
8. `.cursor/rules/external-agent-pr-loop.mdc`.

**Base:** `815f9d8d0f0582d3b8b7d86038e5d598c0a653b9`.

If `origin/main` has moved, inspect every intervening change that touches:

```text
apps/live_control_server/models/world_graph_bootstrap.py
apps/live_control_server/routes/world_graph_bootstrap.py
tests/fixtures/world_graph_bootstrap/api-contract-v1.json
apps/live-control-ui/src/api/
apps/live-control-ui/src/ingestSurface/
```

Stop if the serialized status contract or `/ingest` composition boundary changed materially. Re-anchor the handoff rather than coding against the stale base.

## §4 Files in scope

| Action | Path | Purpose |
|---|---|---|
| Modify | `apps/live-control-ui/src/api/types.ts` | Add the exact status/error and nested review types consumed from PR006D2. Do not add prepare/confirm request or response types. |
| Modify | `apps/live-control-ui/src/api/liveApi.ts` | Add one status-only client for `GET /api/live/world-graph-bootstrap/status`; preserve stable bootstrap error bodies as renderable domain states. |
| Modify | `apps/live-control-ui/src/ingestSurface/MemoryIngestPage.tsx` | Mount the read-only bootstrap review in the real `/ingest` route without replacing or coupling it to the existing Graph Review workbench. |
| Create | `apps/live-control-ui/src/ingestSurface/MemoryIngestPage.test.tsx` | Prove the route-level composition contains the bootstrap review and retains the existing Graph Review workbench. |
| Create | `apps/live-control-ui/src/ingestSurface/worldGraphBootstrap/WorldGraphBootstrapReviewPanel.tsx` | Render the approved package, real memory contents, trust boundaries, health/read state, and diagnostics without mutation controls. |
| Create | `apps/live-control-ui/src/ingestSurface/worldGraphBootstrap/WorldGraphBootstrapReviewPanel.test.tsx` | Exercise ready, active, head-advanced, blocked, invalid, and transport-failure rendering from the committed PR006D2 contract fixture. |
| Create | `apps/live-control-ui/src/ingestSurface/worldGraphBootstrap/worldGraphBootstrapReview.css` | Provide component-scoped layout and responsive styles using existing application tokens. |

Every changed path must appear above. If another path is required, stop and report it; do not silently broaden the allowlist.

## §5 Files explicitly out of scope

| Path | Why this PR must not touch it |
|---|---|
| `src/graph_memory/**` | Kernel, storage, initialization, projection, and graph semantics are predecessor/successor ownership. |
| `graph_data/approved_contribution_bundles/**` | The approved bundle is an immutable input to this UI. |
| `apps/live_control_server/**` | PR006D2 owns the backend contract; a mismatch is a stop condition, not permission to patch server and UI together. |
| `tests/fixtures/world_graph_bootstrap/api-contract-v1.json` | The fixture is canonical generated input. The UI adapts to it; this PR does not rewrite it. |
| `apps/live-control-ui/src/planSurface/graphReviewWorkbench/**` | Existing recap/run Graph Review behavior remains a neighboring workflow, not the implementation home for bootstrap activation. |
| `apps/live-control-ui/src/planSurface/config/ingestSurfaceConfig.ts` | Do not turn bootstrap review into a toolbox mutation workflow or absorb Diagnostics/Author Draft changes. |
| `apps/live-control-ui/src/planSurface/projection/**` | No projection-container refactor is required to render one read-only top-level `/ingest` section. |
| `apps/live-control-ui/package.json` and lockfiles | No new dependency is authorized. |
| `Docs/Plans/PR-TRACKER-campaign-supergraph.md` | The implementation worker does not mark its own slice complete. |

Also out of scope:

- prepare/confirm mutation;
- arbitrary contribution publishing;
- ongoing recap ingestion into the persistent world head;
- authored-memory migration from overlay/event log to Kernel;
- source editing, evidence repair, identity merge, or graph correction;
- Projection Engine or Plan/Play consumption.

## §6 Implementation contract

```text
Input:
  A no-query GET to /api/live/world-graph-bootstrap/status.
  Success body: dmb_world_graph_bootstrap_status_v1.
  Stable domain error body: dmb_world_graph_bootstrap_error_v1.
  Canonical examples/schemas: tests/fixtures/world_graph_bootstrap/api-contract-v1.json.

Output:
  A read-only section on /ingest that makes the bootstrap state and exact
  reviewable campaign memory understandable without offering a write.

Invariant:
  Every user-visible memory claim comes from the PR006D2 response currently
  being rendered, and the mounted experience cannot prepare, confirm, or
  publish anything.

Failure behavior:
  ready / active / active_head_advanced
    → render the state truthfully and render review content when present.

  invalid_bundle / blocked_existing_world / inconsistent_lineage / error
    → render the stable code, message, and diagnostics; do not fabricate review
      content or imply activation is safe.

  malformed, HTML, transport, or non-contract response
    → render an honest unavailable state with retry; do not fall back to a
      preview run, fixture, or hard-coded package display.

Replay or idempotency:
  Repeated mount, retry, or refresh performs only the same GET.
  The same response renders the same facts and never creates a graph revision.

Trust boundary:
  Verifies:
    - response schema discriminant before rendering typed content;
    - all review collections displayed are from the returned status payload;
    - state-specific copy matches the returned state;
    - unverified evidence locators remain visibly unverified.

  Records or trusts:
    - PR006D2 certification of the fixed bundle and review projection;
    - Kernel receipt and integrity booleans when returned;
    - source/evidence locator strings, which this UI does not independently
      resolve or verify.
```

### Required information hierarchy

The default presentation must answer, in this order:

1. **What is this?** World, campaign, focus session, package ID, and current state.
2. **How much memory?** Contributions, nodes, relationships, attributes, accepted assertions, support, evidence, and sources.
3. **What will DungeonBuddy remember?** Every returned node, relationship, and attribute—not merely digest and totals.
4. **Where did it come from?** Contributions and source artifacts with source domain and classification.
5. **What may I trust?** `canTrust`, `cannotTrust`, diagnostics, receipt/integrity state when present.
6. **What is technical detail?** Raw IDs, digests, contribution IDs, evidence refs, and locators may sit behind explicit Details affordances, but must remain reachable.

### Rendering rules

- Resolve relationship endpoint labels from the returned node collection for readable relationship rows. Preserve raw IDs behind Details.
- Show all classifications exactly as returned: `sourceDerived`, `gmAuthored`, or `mixed`.
- Render evidence locator status. An `unverified` locator must not become a trusted hyperlink or be described as verified source navigation.
- Do not turn source URIs into arbitrary filesystem navigation.
- `active_head_advanced` means the current head descends from the initialization; it does not mean the initialization revision is still the current head.
- Do not copy claims from constants, fixture text, or campaign knowledge into production rendering. Fixtures belong only in tests.
- The review may use collapsed sections for density, but all returned nodes, relationships, attributes, contributions, and sources must be reachable from the normal component.
- Existing Graph Review remains mounted and behaviorally independent below or beside this section. Bootstrap status failure must not prevent recap/run Graph Review from loading.

### Status client rules

The generic `apiFetch` helper currently assumes a FastAPI `detail` envelope on errors, while the bootstrap route returns `dmb_world_graph_bootstrap_error_v1` directly. The status client must preserve that stable body instead of collapsing it to HTTP status text.

Do not generalize the entire API client unless required by the status contract. A narrow discriminated status result is preferable to a broad error-handling rewrite.

The D3A diff must contain no request to:

```text
/api/live/world-graph-bootstrap/prepare
/api/live/world-graph-bootstrap/confirm
```

## §7 Verification commands

Run every command from the repository root unless the command changes directory.

```bash
cd apps/live-control-ui
npm test -- \
  src/ingestSurface/worldGraphBootstrap/WorldGraphBootstrapReviewPanel.test.tsx \
  src/ingestSurface/MemoryIngestPage.test.tsx
npm run typecheck
npm run build
cd ../..

git diff --check

git diff --stat 815f9d8d0f0582d3b8b7d86038e5d598c0a653b9...HEAD -- \
  apps/live-control-ui/src/api/types.ts \
  apps/live-control-ui/src/api/liveApi.ts \
  apps/live-control-ui/src/ingestSurface/MemoryIngestPage.tsx \
  apps/live-control-ui/src/ingestSurface/MemoryIngestPage.test.tsx \
  apps/live-control-ui/src/ingestSurface/worldGraphBootstrap/WorldGraphBootstrapReviewPanel.tsx \
  apps/live-control-ui/src/ingestSurface/worldGraphBootstrap/WorldGraphBootstrapReviewPanel.test.tsx \
  apps/live-control-ui/src/ingestSurface/worldGraphBootstrap/worldGraphBootstrapReview.css

git diff --name-only 815f9d8d0f0582d3b8b7d86038e5d598c0a653b9...HEAD

if git diff 815f9d8d0f0582d3b8b7d86038e5d598c0a653b9...HEAD -- \
  apps/live-control-ui/src/api/liveApi.ts \
  apps/live-control-ui/src/ingestSurface/ \
  | grep -E '/world-graph-bootstrap/(prepare|confirm)'; then
  echo 'D3A introduced a forbidden mutation endpoint' >&2
  exit 1
fi
```

### Fixture-backed test requirements

Tests must read `tests/fixtures/world_graph_bootstrap/api-contract-v1.json` from the repository. Do not recreate equivalent status objects by hand.

The owning tests must prove:

- the ready example exposes the real package counts and visible campaign contents;
- Mirathorn, Mireward, Questionable Company/party material, Session 22/23 chronology, and Tripod Null-Calf content are reachable from the rendered review when present in the fixture;
- all returned relationships and attributes are represented, not only nodes;
- source-derived / GM-authored / mixed classifications render faithfully;
- trust and non-trust claims remain separate;
- unverified evidence locators remain marked unverified and are not trusted links;
- active and active-head-advanced copy does not conflate initial and current head;
- blocked and invalid stable errors render their real diagnostics;
- transport failure leaves the existing Graph Review workbench usable;
- the only bootstrap network operation is GET `/status` with no query, request body, prepare, or confirm call.

## §8 Required PR handback

- **Branch:** `agent/pr006d3a-ingest-bootstrap-review` from `main` at the base SHA above.
- Open a **draft PR** against `main`.

The PR body must contain:

1. One-sentence outcome copied from §1.
2. Base SHA and head SHA.
3. `git diff --stat` limited to §4 paths.
4. Every §7 command and result.
5. Explicit statement that no `live_llm` test ran or was required.
6. Paths outside §4: `none`, or a stop report.
7. Bootstrap operations observed in UI tests: list them; the accepted D3A answer is status GET only.
8. Deviations, split triggers, and deferred D3B work: `none`, or explicit details.

Do not mark PR006D3 or PR006D complete from the implementation branch. The design/review owner re-anchors and updates the tracker after review and merge.

## §9 Acceptance rubric

The reviewer accepts only when every item is true:

- [ ] An `/ingest` user can inspect the exact approved bootstrap memory before any write is offered—verified by the focused panel and page tests in §7 using the committed PR006D2 fixture.
- [ ] The page exposes every returned node, relationship, attribute, contribution, and source, with game-readable labels before raw IDs—verified by `WorldGraphBootstrapReviewPanel.test.tsx`.
- [ ] Ready, active, active-head-advanced, blocked, invalid, and unavailable states make distinct truthful claims—verified by `WorldGraphBootstrapReviewPanel.test.tsx`.
- [ ] Trust copy is response-driven; `canTrust` and `cannotTrust` are not collapsed—verified by fixture-backed assertions.
- [ ] Unverified evidence locators remain unverified and non-navigable—verified by fixture-backed assertions.
- [ ] Existing recap/run Graph Review remains mounted and independently usable—verified by `MemoryIngestPage.test.tsx`.
- [ ] No prepare, confirm, publication, actor, proposal, or token behavior exists—verified by the focused tests and mutation-endpoint diff guard in §7.
- [ ] Typecheck and production build pass.
- [ ] No paths outside §4 changed—verified by `git diff --name-only`.
- [ ] PR006D3B remains explicitly false and unclaimed.

### Review boundary map

Review the future implementation at these seams:

```text
Pydantic status/error models
  ↔ canonical generated contract fixture

canonical fixture
  ↔ TypeScript status/error types

HTTP status + direct stable error body
  ↔ frontend status result

status state
  ↔ state-specific user-visible claim

review collections
  ↔ every visible node / relationship / attribute / source

evidence locatorStatus
  ↔ verified vs unverified UI treatment

MemoryIngestPage
  ↔ bootstrap review + retained Graph Review workbench

read-only mission
  ↔ actual network calls and absence of mutation controls
```

## Stop conditions

Stop and report rather than expanding scope if implementation requires:

- changing the PR006D2 backend model, route, service, or fixture;
- introducing prepare/confirm types or calls to make the read surface work;
- a second public or durable contract;
- changing the existing Graph Review workbench’s run-selection or authoring behavior;
- adding a package or code-generation dependency;
- resolving or trusting evidence locators in the browser;
- building Projection Engine, graph search, Plan migration, or active publication health beyond the returned status/receipt;
- adding source editing, graph correction, identity merge, or general authoring.

```text
Stop condition:
Why §1 cannot absorb it:
Affected contract or path:
Proposed successor slice:
Tracker change needed:
```

The expected successor is:

```text
PR006D3B
  A GM can explicitly confirm a prepared bootstrap proposal in /ingest so that
  the approved initial World Supergraph is published deliberately.
```
