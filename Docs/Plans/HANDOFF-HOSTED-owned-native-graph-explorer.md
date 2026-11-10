# HOSTED: authorize the owned native World graph

**Status:** ACTIVE for the backend scope below. Frontend paths remain unleased until the existing graph coordinator freezes/transfers them.
**Owner:** wire_hosted_graph_access, explicitly assigned design/stewardship and implementation by the coordinating root.
**Design base:** current main `999a5eabe00b282d605c72044c9bf8a15e3c8ee3`, verified by connector and present locally. Current-main AGENTS.md supersedes inherited older checkout policy and permits this pinned branch handoff.
**Implementation base:** `b0322b7d2e21714f5abefef3cbd5b09affb62b33`, draft explorer #2330.
**Topology:** stacked, exactly one assigned owner-access PR above #2330. Required merge order is existing explorer stack, finalized #2330, then this slice. Rebase/reconcile onto the actual finalized parent before publication/review. No merge/deploy authority.
**Branch:** `codex/hosted-owned-graph-20261110` at `/home/drakosfire/Projects/.codex/hosted-owned-graph-20261110/worktrees/DungeonMindBuddy`.
**Authorization:** Alan asked to view his corpus graph and wire it to be ready to deploy with user ownership. Root explicitly directed proceeding with owner-only initially as a bounded least-privilege behavior, not permanent product policy. No shared-member GM assumption, actual ownership change, merge or deployment.
**Activation facts:** graph coordinator froze/transferred `main.py`, `routes/native_graph_explorer.py`, `services/native_graph_explorer.py` on its side at b032; frontend App/selector/liveApi remain held pending synchronization assessment. Current open HOSTED #1512/#1514 are documentation-only; deploy prep #1828 owns only deployment packaging paths; #2358 is Backlog only. Older preflight historical ACTIVE records are not new authorities over this explicit root assignment. Shared test inventory is additive for this slice's exact new tests only.
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

No write lease to predecessor handoff or frontend currently. The earlier proposal below is reference context only; its prospective paths are NOT active leases. Changes outside this active table return to the coordinating root or explicit owner.

## Pin and proof

This handoff is committed before implementation. Local unit/auth proof uses scrubbed environment, disabled dotenv/conftest where appropriate and actual current middleware/native functions. Full APP/Core fixture and browser/TS/aggregate proof remain required before deployment readiness, and frontend activation remains pending. Current-source aggregate checks and independent review are required; passing scoped tests alone is not completion. No tests or gates are removed.

---

# Historical design proposal (superseded by active authority above)

# HANDOFF — HOSTED: browse and author an owned native World graph

**Created:** 2026-11-10
**Status:** DRAFT — local steward-review proposal only; no ACTIVE lease or implementation authority.
**Handoff locator:** prospective `Docs/Plans/HANDOFF-HOSTED-owned-native-graph-explorer.md`; not yet committed or published.
**Conversation/workstream:** Buddy index graph explorer, user-owned hosted access.
**Flow / owner:** HOSTED / coordinating steward, to be designated at approval.
**Direction:** DESIGN → CODE → REVIEW
**Design authority base:** `999a5eabe00b282d605c72044c9bf8a15e3c8ee3`
**Activation gate:** Steward settles the proposed ownership/visibility policy, exact collection authorization and shared-path leases; pins this reviewed handoff on an explicitly authorized durable branch/ref under repository law; re-anchors the finalized explorer predecessor; records exact topology and assigned publication action. This draft cannot satisfy that gate.
**Dispatch base rule:** fresh current integration state after activation, never current main checkout or shared working tree.
**PR topology:** proposed serial successor to the current explorer slice; no implementation branch exists. A stacked alternative requires an explicit steward amendment naming the actual finalized #2330 head and merge order.
**PR authorization:** none granted by this draft. Steward must name the one permitted implementation PR action at activation. No merge/deploy authority.
**PR title:** `HOSTED: authorize owned native graph exploration`

Current repository law is AGENTS.md at main 999a5eabe00b282d605c72044c9bf8a15e3c8ee3, changed by 854041e955e2857de92e572f8b0794b98b098eb7. It permits a handoff on any durable pinned ref and explicitly says legacy .cursor process documents are not additional policy gates. The older AGENTS.md in the b032 explorer checkout is superseded by that current-main authority. No main merge is required to activate an explicitly authorized bounded handoff. This uncommitted local design file still grants no implementation authority.

## §1 Mission and merge-ready invariant

**Mission:** A signed-in user can choose an existing World they own and view the graph actually loaded for that World, select a native point, zoom and inspect it, and explicitly create/connect supported native objects through Buddy's index, ready for deployment review without deployment. The graph remains an entity/relationship view; this slice does not turn source/evidence records into canvas nodes.

**Proposed policy, awaiting steward decision:** Only an exact preexisting APP `owner_subject` matching the freshly introspected DMS subject may be mapped to native GM visibility in this first hosted slice. The configured hosted World allowlist remains an additional restriction, not evidence of ownership. No nonowner action grant maps to GM; unowned Worlds stay denied. The user request for ownership does not settle a broader shared-member role design.

**Merge-ready invariant:** Every displayed World, graph, preparation, confirmation and recovery result is authorized for that verified owner at the owning boundary, bound to the exact server-resolved managed/native World and current binding, and derived from native authority. Sign-in, selectors, labels, local credentials and stale operation state never grant another World's graph or write authority.

**Critique:** Selection and graph operations share one invariant, but hosting anonymous demos, new-World initialization and ownership assignment are separate contracts. The likely failure is preparing in World A, changing owner/binding/selection, and later confirming or displaying A's response under B. Integration tests must exercise request middleware, current APP ownership, native publication, recovery and UI invalidation together.

## §2 Context, authority, lane, and PR topology

| Field | Required content |
|---|---|
| Parent authority | User asks to view corpus graph and prepare deployment with user ownership. Existing `DESIGN-world-ownership-and-action-grants-core.md` action semantics; current APP catalog owns storage, not that document's obsolete file-backed storage wording. |
| Design authority base | Main `999a5eabe00b282d605c72044c9bf8a15e3c8ee3`; inspected explorer #2330 head `b0322b7d2e21714f5abefef3cbd5b09affb62b33`. Both must be rechecked before activation. |
| Activation gate | Accept or replace owner-only proposal; settle exact owner-filtered collection policy; finalize predecessor and transfer shared paths; durable reviewed ACTIVE handoff under current-main AGENTS.md, on any authorized pinned ref. |
| Predecessor contract | Existing managed native explorer graph/prepare/confirm/operation endpoints, native receipt verification, and Buddy index UI. #2330 remains open and is undergoing a separately owned UI correction. |
| Exact input consumed | Fresh DMS subject; authoritative APP World record and active native binding; current native revision/descriptors; principal/World journal and exact native receipts. |
| Named successor | Shared-member visibility roles; ownership assignment/transfer; new empty native World initialization; hosted anonymous demonstration; deployment/cutover. |
| What remains false | An unowned existing corpus is not automatically claimed by the signed-in user. New World creation is not a vNext initializer. Drafting code does not deploy or qualify a live service. |
| PR topology | Proposed serial. No successor branch before predecessor completion unless steward declares an explicit stack. |
| Authorized PR action | None yet. At activation, explicitly name one implementation PR and whether publication is authorized. |
| Branch / isolated checkout | None while DRAFT/BLOCKED; future task-owned Projects worktree only after activation. |
| Parallel lanes / collision hotspots | Existing explorer UI correction owns six UI files plus its handoff; local-session handoff lists agent_graph_auth.py; shared main.py, hosted_auth.py, world selector/client and test inventory need explicit collision preflight. |
| Runtime/state ownership | Synthetic task-owned APP/Core databases, synthetic DMS mock service/cookies, separate service ports and browser profile. No live catalog, user graph, provider or deployment. |
| State-authority sync set after merge | This handoff and completed predecessor `HANDOFF-SURFACE-native-graph-demo.md` facts only. Hosted readiness/launch document updates must be named by the steward if their claims change. |

## §3 Observable paths and adversarial sequences

| Path | Current behavior | Required behavior | Owning boundary |
|---|---|---|---|
| Hosted World selection | Denied; local GET lists all Worlds | Return only exact allowed owned Worlds, minimum selector metadata, no creator/grant/foreign graph leakage | Auth middleware + APP catalog + selector |
| Existing corpus graph | Hosted route rejected | Verify owner and active binding, then return native selected graph; no allocation/seed/migration | Route policy + native service |
| Create/connect | Local-operator only | Same reviewed native prepare/confirm contract under revalidated owner; no implicit write | Auth + journal + WorldKeeper/Core |
| Operation lookup/recovery | Principal/World-scoped local journal | Retain scope, revalidate current ownership/binding before returning receipt or graph | APP journal + receipt verification |
| Sign-out/auth unavailable | Fail closed | Clear/suspend hosted graph and refuse new requests; no playground fallback | Auth state + UI invalidation |
| Owner/binding changes mid-operation | Not a hosted contract | Deny before next effect/result; do not report committed without native proof or redispatch unknown writes | Permission check + publication boundary |

Adversarial acceptance includes another owner with the same World name; forged subject/role/forwarding headers; missing/duplicate/conflicting selectors; unowned Worlds; read/write/manage/share grantees; allowlisted nonowner; foreign-origin POST; operation ID guesses; logout then login as another subject; A→B selection while A read/confirm returns; revocation before confirm/recovery; service restart after committed-but-lost response.

## Historical proposed paths (not an active lease)

No row reserves ownership while this is a draft. The steward must confirm/split these exact paths before ACTIVE.

| Action | Path | Purpose |
|---|---|---|
| Create | `Docs/Plans/HANDOFF-HOSTED-owned-native-graph-explorer.md` | Approved owning contract |
| Modify | `Docs/Plans/HANDOFF-SURFACE-native-graph-demo.md` | Truthful completed predecessor sync only |
| Create | `apps/live_control_server/services/hosted_native_graph_access.py` | Explorer-specific trusted owner checks and explicit World collection policy |
| Modify | `apps/live_control_server/services/hosted_auth.py` | Narrow exact collection policy seam; retain global authentication/Origin and all unrelated denials |
| Modify | `apps/live_control_server/main.py` | Exact four explorer route resolvers and approved collection policy registration |
| Modify | `apps/live_control_server/services/agent_graph_auth.py` | Only a reviewed principal auth-method/type addition if necessary; no global native route enablement |
| Modify | `apps/live_control_server/routes/native_graph_explorer.py` | Explorer-scoped owner authorization; local behavior preserved |
| Modify | `apps/live_control_server/services/native_graph_explorer.py` | Required owner rechecks before effects/recovery and result disclosure |
| Modify | `apps/live_control_server/routes/world_containers.py` | Approved hosted owner-filtered existing-World list; do not expose unowned creation/binding mutation |
| Modify | `apps/live-control-ui/src/selectedWorld/WorldSelector.tsx` | Hosted allowed-World selection and clear unsupported creation/ownership state |
| Modify | `apps/live-control-ui/src/selectedWorld/WorldSelector.test.tsx` | Selection isolation and denied/unavailable behavior |
| Modify | `apps/live-control-ui/src/App.tsx` | Accurate hosted state, subject/World scoped invalidation if required |
| Modify | `apps/live-control-ui/src/App.guestEntry.test.tsx` | Auth transition and no-fallback proof |
| Modify | `apps/live-control-ui/src/nativeGraphDemo/managedNativeGraphApi.ts` | Subject/selection invalidation if required; no retry weakening |
| Modify | `apps/live-control-ui/src/nativeGraphDemo/managedNativeGraphApi.test.ts` | Pending requests across subject/World transitions |
| Modify | `apps/live-control-ui/src/api/liveApi.ts` | Exact affected route/auth wiring only |
| Modify | `apps/live-control-ui/src/api/liveApi.nativeGraphExplorerAuth.test.ts` | Cookie/Origin/mutation retry boundary |
| Create | `tests/test_hosted_native_graph_access.py` | Actual middleware/auth/owner/native isolation tests |
| Modify | `tests/test_hosted_auth.py` | Preserve closed route policy while adding reviewed collection seam |
| Modify | `tests/test_native_graph_explorer.py` | Owner changes, binding changes, exact recovery |
| Modify | `ci/test-classification.json` | Add only exact new test inventory entries, coordinator-owned |

**Bounded discovery exception:** None. Any additional path, role schema, migration, background job or new public route returns to the steward.

## Historical exclusions

| Path | Why this slice must not touch or claim it |
|---|---|
| `src/application_state/migrations/**` | No ownership assignment/schema migration is needed for preexisting owner checks |
| `src/application_state/world_catalog/types.py` | No new roles or grant semantics without a separate decision |
| `apps/live_control_server/services/dms_principal.py` | Reuse existing identity resolver unchanged; no fabricated identity/cache |
| `apps/live_control_server/services/agent_graph_local_session.py` | Local cookie/CSRF behavior retained |
| `apps/live_control_server/native_graph_demo/**` | No standalone or anonymous hosted enablement |
| `apps/live_control_server/services/index_graph.py` | No guest allocation or shared demo data changes |
| `scripts/adopt_world_catalog.py` | No live adoption, owner assignment or retained-data migration |
| `pyproject.toml` | No dependency/profile or upstream ontology changes |

No deployment manifests, live environment, production DSNs, cookie store, operator profile, actual user's corpus or provider call may be changed or used as synthetic test data. No merge, auto-merge, deployment, credential changes, ownership transfer or service cutover.

## §6 Implementation contract

This section describes the owner-only recommendation for review, not an accepted policy.

- Authenticate through the current DMS resolver and exact fixed server origin. Use only the trusted request-scoped subject. Preserve unavailable versus signed-out distinctions and trusted-Origin enforcement for every POST, including read-shaped POSTs.
- Establish authority from current APP record and exact managed/native binding. Require `record.owner_subject == principal.subject` AND the current configured hosted allowlist. Missing owner, inaccessible catalog, inactive/provisioning binding or mismatch is no access, not migration/setup success.
- Resolve the four exact explorer paths server-side. Prepare verifies request native World/binding/revision against authority; confirm and status resolve the stored operation under exact principal+managed World, then recheck its record/binding. No global change making unrelated native routes accept hosted identity.
- World listing needs a separately explicit exact collection policy rather than a one-World resolver or blanket exemption. The approved policy must filter on trusted subject and authoritative ownership, intersect the configured allowlist, return minimum selector fields, and never return foreign records before authorization. The unchanged local list remains local-only. Hosted create, binding and sharing stay denied.
- No role is inferred from read/write/manage/share. Owner-to-native-GM conversion, if approved, is limited to this explorer. All unowned and nonowner Worlds remain excluded.
- Revalidate ownership at every effectful or result-disclosing boundary. A bounded request-scoped snapshot must not become persistent permission. Ownership changes during long operations need an explicit race policy reviewed against existing APP publication locking; if current locking cannot enforce the intended boundary, stop rather than adding unsafe best-effort claims.
- Native source/graph state and WorldKeeper receipts remain authority. Preserve preparation review, scoped IDs, exact publication verification, unknown outcome handling and no blind mutation replay. Do not add seed content or fallback browser graph.
- The visible canvas, selected point, details and revision/export indicator must follow the same successful managed/native World, binding version and graph revision, never merely the selected World label. Clear stale selection when its node is absent or scope changes; zoom is local presentation. Inspect only admitted loaded native objects through already-authorized contracts; adding a source/evidence inspection endpoint or evidence-as-node projection is outside this slice.
- UI must invalidate pending requests and hide earlier graph material when identity, auth status or selected World changes. Browser drafts/layout may remain scoped presentation state but must not cross owner/World scope. Existing corpus read and snapshot export make no persistent semantic change.
- A corpus lacking an owner remains unavailable in hosted mode. Report that metadata state separately; any later ownership assignment requires an explicit verified operator action and is not authorized here.

## §7 Evidence required to merge

1. Real middleware + current DMS resolver through synthetic transport; valid owned World succeeds, signed-out/unavailable/forged identity and foreign origins deny before graph effects.
2. Real APP isolated-clone catalog records for two owners and an unowned World, including every independent grant type. Selector contains only permitted owner records and never leaks names/bindings/counts of others.
3. Actual native read/prepare/confirm/recovery on synthetic APP/Core data, no native/ownership dependency overrides. Exact graph readback, stable IDs, receipt recovery after fresh-process restart, no automatic seed or model call.
4. Ownership/binding revoked between read/prepare/confirm/status and concurrent interleavings. Denied requests make no publication; unknown outcomes preserve the original ID and truthfully distinguish committed-but-not-readable.
5. Browser sign-in, existing owned selection, corpus graph display, reviewed create/connect on synthetic data, logout, alternate login, Back/Forward, stale response, error, unsupported new-World creation and no playground fallback.
6. Exact-source focused backend/UI tests, strict TS/build, existing auth-app aggregate, test inventory, existing hosted frontend verifier, default-discovered base/head comparison, independent review. Existing failures stay visible and are never excluded to pass.

Exact commands below are the prospective contract, run only in the activated isolated lane with its scrubbed test runtime and synthetic APP/Core fixtures:

```bash
python scripts/steward_preflight.py --handoff Docs/Plans/HANDOFF-HOSTED-owned-native-graph-explorer.md --local-only
python -m pytest -q tests/test_hosted_native_graph_access.py tests/test_hosted_auth.py tests/test_native_graph_explorer.py
python scripts/ci_contract.py run auth-app
python scripts/ci_contract.py inventory
cd apps/live-control-ui
npm test -- src/selectedWorld/WorldSelector.test.tsx src/App.guestEntry.test.tsx src/nativeGraphDemo/managedNativeGraphApi.test.ts src/api/liveApi.nativeGraphExplorerAuth.test.ts
npm run typecheck
npm run build
cd ../..
git diff --check
python scripts/ci_local_frontend.py run --repo "$PWD" --sha "$(git rev-parse HEAD)" --suite hosted --output "$TASK_ROOT/verification/hosted-final"
python scripts/ci_local_frontend.py run --repo "$PWD" --sha "$(git rev-parse HEAD)" --suite discovered --output "$TASK_ROOT/verification/discovered-final"
```

Steward must pin installed runtime/fixtures, task TMPDIR/cache, approved exact test command syntax and base SHA at activation. No network install fallback, baseline suppression or production dotenv load. Mock tests do not prove real hosted browser cookie delivery; that remains an authorized deployment-rehearsal gate, not a reason to deploy now.

Assessment evidence already exists for unchanged b032: 138 current auth checks and 23 synthetic fail-closed explorer/permission checks passed. Those establish current denial behavior only, not this proposal's acceptance.

## §8 Required review handback

Return exact head/base and topology; accepted policy versus this recommendation; all shared-path transfers; changed paths versus lease; focused, aggregate, DB, browser and restart evidence separately; authorization and race findings; known baseline failures; retained artifacts; outstanding deployment/ownership gates. No passing unit count alone means deploy-ready.

## §9 Acceptance and stop conditions

- Existing correctly owned native Worlds are selectable and their actual graph is viewable after DMS sign-in.
- Foreign/unowned/granted-but-not-owner data remains inaccessible, including collection metadata and recovered operations.
- Explicit create/connect remains fully reviewed and native-authoritative; reads never allocate or mutate.
- Owner-only policy and collection contract are explicitly accepted, not inferred from this draft.
- No live ownership assignment, corpus write, deployment or service change occurs.
- Stop for undefined owner-to-GM semantics, inability to enforce revocation at the owning boundary, a new schema/migration/role/public capability, leased-path overlap, missing isolated test runtime or an unapproved external action.

## Local draft preflight and exact activation next step

The unchanged legacy preflight helper was run locally against this draft. It correctly reports non-ACTIVE and also finds seven historical lease overlaps involving main.py, App.tsx and test-classification.json. These are evidence for coordinator reconciliation, not proof every historical lane is still running. Its main mismatch warning compares stale local main, not the already verified origin/main. Current policy still requires actual open-work/lease coordination, but legacy helper output cannot create a new main-merge requirement.

The authorized coordinating steward can now: (1) accept or revise the owner-only recommendation and exact collection contract; (2) coordinate existing explorer files and finalize its head; (3) choose serial successor or an explicit stack, assign the exact expected paths/runtime and one PR action; (4) place the reviewed handoff in an isolated design/implementation branch and pin its commit, mark ACTIVE only with those facts; (5) re-read that pinned authority and dispatch implementation. A human can instead make the same design/authorization decision. No outside-agent message or main merge is inherently required. The current assignment has not performed any of these activation/publication steps.
