# HOSTED: authorize the owned native World graph

**Status:** ACTIVE for the backend and explicitly transferred frontend/entity-inspection scope below. Implementation and verification are in progress; not deployment-qualified.
**Owner:** wire_hosted_graph_access, explicitly assigned design/stewardship and implementation by the coordinating root.
**Policy anchor:** main `af88d3ac71232d02fe9f4cde72ae5cca50f4fe32`, re-inspected from the shared fetched ref after earlier anchors `8f3b08fad0528cc7bd9d96e45011a6f9777cb0f6` and `999a5eabe00b282d605c72044c9bf8a15e3c8ee3`. AGENTS.md is unchanged between these anchors and permits this pinned branch handoff. Initial authority is pinned in `afb137c4d310bb1c4baf10174b6350f40ea647c2`; frontend/inspection amendment in `5b141a6f7a0606c12a0020b0212fd385770f4549`.
**Implementation base:** `884e76c4ec5d6cb14b1e2f6d98c70f3e1a122e27`, the frozen #2330 graph/inspection candidate on `codex/buddy-index-native-20261110`. This owner lane was initially implemented above `b0322b7d2e21714f5abefef3cbd5b09affb62b33` and rebased without conflicts onto the explicit14-file successor. Parent acceptance is still pending; later parent corrections must be reconciled and relevant checks repeated.
**Topology:** stacked, exactly one assigned owner-access PR above #2330. Required merge order is existing explorer stack, finalized #2330, then this slice. Rebase/reconcile onto the actual finalized parent before publication/review. No merge/deploy authority.
**Branch:** `codex/hosted-owned-graph-20261110` at `/home/drakosfire/Projects/.codex/hosted-owned-graph-20261110/worktrees/DungeonMindBuddy`.
**Authorization:** Alan asked to view his corpus graph and wire it to be ready to deploy with user ownership. Root explicitly directed proceeding with owner-only initially as a bounded least-privilege behavior, not permanent product policy. No shared-member GM assumption, actual ownership change, merge or deployment.
**Activation facts:** graph coordinator froze/transferred `main.py`, `routes/native_graph_explorer.py`, `services/native_graph_explorer.py` on its side at b032; the same coordinator subsequently released App/selector/liveApi/auth-gate paths after its synchronization assessment, as recorded below. Current open HOSTED #1512/#1514 are documentation-only; deploy prep #1828 owns only deployment packaging paths; #2358 is Backlog only. Older preflight historical ACTIVE records are not new authorities over this explicit root assignment. Shared test inventory is additive for this slice's exact new tests only.
**Runtime:** synthetic offline auth/unit/native repositories initially. Task-owned scratch/cache/verification on Projects UUID `48fa5d10-fe99-4557-9fc9-d8a2a4b41ac8`; no shared service ports, live DB, user corpus or provider. Any persistent integration proof uses uniquely allocated fixture databases under existing authorized test machinery, not operator data.

## Active invariant and behavior

Only an introspected DMS subject equal to the authoritative preexisting APP World owner and admitted by the existing hosted World allowlist can enter this initial hosted native graph capability. Existing nonowner grants are preserved but do not grant native GM. An owned World can be listed through an explicitly registered owner-filtered collection policy and read/authored through the four exact existing explorer routes. Missing ownership/authority denies; there is no owner assignment, migration, seed, new World creation or generic auth exemption.

Permissions are checked at request admission, before each native publication boundary, before operation recovery and before returning graph/results. A publication already dispatched before a later external ownership change may finish; the result is still withheld after failed revalidation, and later retries revalidate before receipt recovery. This slice does not promise atomic cancellation of in-flight Core work across independently administered databases and does not add an ownership-transfer API.

Keep the current entity/relationship canvas and actual loaded managed/native World/binding/revision synchronization. Do not make source/evidence records into graph nodes. Local native routes retain their authentication. No global hosted enabling of other native routes.

## §4 Active backend write lease

| Action | Path | Purpose |
|---|---|---|
| Create | `Docs/Plans/HANDOFF-HOSTED-owned-native-graph-explorer.md` | Pinned active authority and updates |
| Create | `apps/live_control_server/services/hosted_native_graph_access.py` | Exact trusted owner authorization, scoped principal, filtered collection policy |
| Modify | `apps/live_control_server/services/hosted_auth.py` | Explicit exact collection-authorizer seam; all other middleware checks unchanged |
| Modify | `apps/live_control_server/main.py` | Explorer resolvers, collection registration, additive authenticated session identity |
| Modify | `apps/live_control_server/services/agent_graph_auth.py` | Narrow additive hosted owner principal method type only, no shared auth-policy widening |
| Modify | `apps/live_control_server/routes/native_graph_explorer.py` | Explorer-scoped auth dependency; local behavior preserved |
| Modify | `apps/live_control_server/services/native_graph_explorer.py` | Current owner revalidation at effects/recovery/return |
| Modify | `apps/live_control_server/routes/world_containers.py` | Hosted filtered existing-World list only; local list unchanged |
| Create | `tests/test_hosted_native_graph_access.py` | Owning middleware/auth/native denial contracts |
| Modify | `tests/test_hosted_auth.py` | Explicit collection seam and unrelated route regression |
| Modify | `tests/test_hosted_auth_login.py` | Additive session identity contract |
| Modify | `tests/test_native_graph_explorer.py` | Native owner revalidation and recovery |
| Modify | `ci/test-classification.json` | Exact new test entry only |

No write lease to the predecessor handoff, native API adapters or graph presentation files. The amendment below adds the exact transferred frontend paths. Changes outside these tables return to the coordinating root or explicit owner.


## Activated frontend and pinned entity-inspection amendment

The graph coordinator expressly released App.tsx, WorldSelector, liveApi.ts, HostedAuthGate and related tests after its loaded-snapshot assessment. The coordinator retains managedNativeGraphApi/nativeGraphDemoApi and canvas/detail presentation, plus AppChrome graph jump. This lane does not edit those retained files; reconcile their successor before final verification.

The same owner-only capability now includes exact POST `/api/live/native-graph-inspection/read` for world-scoped entity selection only, using the unchanged InspectionRead/InspectionPin response contract. It is required by the user's select-point/inspect request. Hosted catalog and source selections remain denied; no evidence-as-graph-nodes capability. Ownership and full binding are checked before/after read, and the existing inspection service verifies the exact native/revision pin.

Additional exclusive paths activated:
- `apps/live_control_server/routes/native_graph_inspection.py` (only owner-scoped entity read dependency/guard)
- `tests/test_native_graph_inspection.py` (preserve local-mode configuration under real dependency)
- `apps/live-control-ui/src/auth/HostedAuthGate.tsx`
- `apps/live-control-ui/src/auth/HostedAuthGate.test.tsx`
- `apps/live-control-ui/src/App.tsx`
- `apps/live-control-ui/src/App.guestEntry.test.tsx`
- `apps/live-control-ui/src/selectedWorld/WorldSelector.tsx`
- `apps/live-control-ui/src/selectedWorld/WorldSelector.test.tsx`
- `apps/live-control-ui/src/api/liveApi.ts`
- `apps/live-control-ui/src/api/liveApi.nativeGraphExplorerAuth.test.ts`

Frontend must use same-origin HTTPS cookie auth only for five exact hosted POST paths (four explorer, one entity inspection) and GET world-containers. Never send a local bearer/CSRF to hosted or remote destinations; retain strict local path behavior for all other routes. Authenticated session subject is now returned by backend. Require exact subject to expose authenticated children; remount/invalidate subject-scoped graph/selection state and draft keys on account change/logout. Unsupported hosted new-World creation stays disabled. Auth service refresh failure must not silently expose an old account's graph. No frontend call is ownership authority.

## Pin and proof

This handoff is committed before implementation. Local unit/auth proof uses scrubbed environment, disabled dotenv/conftest where appropriate and actual current middleware/native functions. Full APP/Core fixture and browser/TS/aggregate proof remain required before deployment readiness. Current-source aggregate checks and independent review are required; passing scoped tests alone is not completion. No tests or gates are removed.


## Deployment-review checklist and explicit limits

- Deployment uses `DMB_DEPLOYMENT_ENVIRONMENT=production` and `DMB_AUTH_MODE=hosted_dms`, the fixed HTTPS `DUNGEONMIND_SERVER_API_ORIGIN`, and exact trusted frontend origins. Browser graph traffic stays same-origin HTTPS and uses the DMS session cookie; local bearer credentials never travel to hosted URLs.
- The existing APP World must already have `owner_subject` equal to the authenticated DMS subject and an active, validated native binding. The configured `DMB_HOSTED_WORLD_ACCESS_JSON` must separately admit that subject and World. APP ownership, native binding and allowlist are three distinct requirements. This work does not mutate any of them or automatically adopt an unowned corpus.
- Retain separate application-state and native-graph authority databases with existing migrations applied by the deployment owner. Durable journal/native publication identities use `hosted_dms:<raw subject>` while ownership checks and the browser session identity retain the raw DMS subject. This separates new hosted operations from preexisting local-operator operations without migrating local data.
- Hosted access includes only the owner-filtered existing-World list, four explorer POST routes and exact world/entity inspection read. Source/evidence links, inspection catalog, new-World creation, owner assignment/transfer, shared-member native roles and unrelated native routes remain unavailable. The UI must represent those limits honestly.
- Rehearse two signed-in owners, an unowned World and every nonowner grant on synthetic data. Prove the graph and selected-node read match the actual displayed managed/native/binding/revision snapshot; account changes/logout and selection changes must discard stale display and requests. Browser credentials and native receipts are not inferred from mock results.
- Required final evidence: exact-head `ci_contract.py run auth-app`, additional new owner-boundary tests, inventory, isolated persistent APP/Core and restart proof, browser account-switch/write-review proof, frontend TypeScript/build, repo-owned exact-SHA hosted verifier and full discovered diagnostic, independent cumulative-diff review. Known baseline failures remain red and specifically named. No gate is removed or relabeled green.
- No merge, deploy, credential change, actual ownership mutation, real corpus publication, service cutover or production environment change is authorized by this handoff. A passing synthetic test count is not live deployment readiness.

## Verification so far

Working-tree diagnostics use scrubbed environment, no production dotenv, synthetic HTTPX DMS transport, APP catalog/journal fixtures and native in-memory Core. They exercise real middleware, typed identity, owner lookup, binding validation, routes and native runtime. The first combined backend run passed314 cases including195 new owner-boundary cases; all196 new owner-boundary cases including the subsequent identity-domain isolation regression now pass. These are diagnostic results, not qualifying exact-head evidence.

Independent boundary review found two in-scope defects during implementation: a prepared status could disclose after a binding changed during its read, and an opaque DMS subject could collide with the local-operator journal namespace. The implementation now revalidates full binding before disclosure and separates hosted operation identity. Both are covered by targeted regression tests. Independent working-tree backend review reports no outstanding finding; formal exact-head cumulative review is still pending.

Task outputs are retained under `/home/drakosfire/Projects/.codex/hosted-owned-graph-20261110/verification`; scratch/cache remain in that task root. No shared runtime has been stopped and no task outputs deleted. Parent #2330's frozen graph presentation/inspection successor884e76c4 is reconciled. Exact-head qualification is now due; later parent fixes require fresh reconciliation. The earlier design draft is retained in Git history, not a competing live authority.


Frontend diagnostics before parent reconciliation:85 focused tests pass;854 broader tests pass and six existing `liveApi.test.ts` history-fixture tests fail on undefined `page.turns`. Clean archived parent `3fa6ad63738dcb1d345a7d809c5321c26598aeb9` reproduces the exact six failures. They remain red, not waived. Both TypeScript projects and production build pass, with the existing chunk-size warning. Local managed draft storage keys are preserved; only new hosted drafts/layout receive subject+World scope. Commands, exact failure IDs and source hashes are retained in the task's `frontend-diagnostics/REPORT.txt`.
