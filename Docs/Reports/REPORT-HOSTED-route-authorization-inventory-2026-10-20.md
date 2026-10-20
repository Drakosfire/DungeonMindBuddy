# HOSTED v1 — route and authorization inventory

**Snapshot:** 2026-10-20
**Authoritative Buddy source:** origin/main at 8bcbe69d1b6d7c70734927a314f4ded05846fb76 (merge commit for PR #1509).
**Scope:** source-only inventory of mounted apps/live_control_server HTTP routes, principal and data-scope checks, side effects, storage and worker boundaries. This is not a production deployment inspection or UX/backlog review.

## Executive decision

**No-go for invited users with distinct Worlds/roles or for public multi-user exposure on the checked-in application contract.** The code does not establish a per-person principal across the route surface, and its World-container model has no owner/member field. The DMS principal resolver and cookie-authenticated Origin helper are present but unmounted. Authentication, the intended managed-population restriction, and object authorization are three separate controls; the repository currently proves none of the last two for hosted Buddy users.

This is a conditional source finding, **not a claim that these routes are internet reachable**. The deployed host, reverse proxy, firewall, service bind address, and route allowlist were not inspected; actual network exposure is unknown. Source contains no app-wide authentication middleware/dependency. If an edge currently blocks routes or makes Buddy loopback-only, that external control must be documented and tested rather than assumed. Do not infer a vulnerability solely from a missing proxy configuration in this repository.

| Exposure mode | Source-based disposition | Conditions / evidence still required |
|---|---|---|
| Trusted local single operator | Plausible only for a private/local deployment boundary. The explicit local GM guard verifies local/development mode, a >=32-character bearer or local session, and a loopback peer. Numerous non-Graph API routes intentionally have no such guard, so the operator must keep the whole app private. | Confirm bind/firewall/edge; identify which endpoints are locally trusted. A loopback-only check on selected Graph routes is not a whole-app perimeter. |
| Invited, DMS-authenticated population | **Not ready for distinct users or account-private Worlds.** DMS identity introspection alone would yield a stable subject, but Buddy has no durable membership/role mapping and currently shares one local_operator subject across local auth modes. | Verify the external DMS/Google population gate with allowed and denied sign-in evidence; choose World creation, visibility, sharing, roles, revocation, legacy-World ownership and media privacy; prove browser cookie delivery to the chosen Buddy request. |
| Public multi-user | **No-go.** In addition to the identity and World-authorization gates above, the source does not provide a coherent per-user quota/audit boundary for provider or mutation operations across these routes. | Authenticated/anonymous route policy, per-user/World/global budgets and concurrency limits, abuse controls, privacy and durable multi-instance state need explicit design and acceptance. |

No server, DNS, TLS, live browser, real DMS session, database, provider, Cloudflare account, or production configuration was contacted. No application behavior or stored World was changed.

## What the code currently means by “authenticated”

Three separate questions must not be collapsed:

1. **Identity:** Is this request associated with a stable user? services/dms_principal.py defines a fail-closed server-to-server resolver for dungeonmind_session → DMS /api/auth/current-user → sub, but static search finds no route import/call. services/trusted_cookie_origin.py is likewise unmounted. The adapter and CSRF helper therefore do not protect any of the routes in the appendix.
2. **Managed-population eligibility:** Is that DMS identity in Alan’s intended limited population? Buddy cannot prove this. At DungeonMindServer origin/main commit 223cbbe92f64bb14019a1678cac1f4e2336efd40, auth_service.py:48-65 reads the existing session user and routers/auth_router.py:296-309 returns that user from /api/auth/current-user; the user model uses the Google sub (auth_service.py:11-24). session_config.py:49-76 names the cookie dungeonmind_session, gives it a 24-hour max age and root path, and in production configures Secure, SameSite=None and Domain=.dungeonmind.net. That parent-domain attribute is compatible with a browser sending the cookie to a Buddy subdomain, but does not prove delivery on the intended request or establish hosting configuration. The operator reports that the existing Google Auth is operational on dungeonmind.net; this audit assumes reuse of that login and does not propose a second sign-in system. The external OAuth audience, Workspace, or test-user restriction remains unverified. Operational login and a successful identity response do not prove the intended population gate.
3. **Object authorization:** May this subject read or mutate this World, run, document, event, proposal, file, image, graph binding, or operation? Current local guards authorize the one shared local_operator GM. Other routes use IDs, World existence, registry structure, exact revision or graph-binding checks. Those constrain object shape/scope but do not prove membership by the caller.

### Existing World privacy semantics and their boundary

There is a sound basis for saying some Buddy data is private by default, but current contracts use “private” for content audience and local World scoping—not for isolation between separate DMS accounts:

- **Content audience within a World:** the DungeonBuddy World domain contract declares `dungeonbuddy.visibility:gm` and `dungeonbuddy.visibility:player` labels (Docs/Contracts/vnext/dungeonbuddy_world_domain_contract_v1.json:9-11). The Plan/Playable design says the first projection is GM-only, existing markers do not establish player visibility, and missing/unknown audience is not public or player-safe (Docs/Design/DESIGN-world-plan-playable-adoption.md:143-145). Native World source admission accepts only internal visibility and requires the source to remain GM-private (apps/live_control_server/integrations/dungeonmind/native_world_source_admission.py:192-194). These are content/projection rules, not user-to-World membership checks.
- **World-to-World local scoping:** the completed World-selection contract says the selected World scopes ordinary Build, Plan, Ingest, and Play work, and explicitly calls that “local application correctness,” not a tenancy/security contract (Docs/Plans/HANDOFF-DEMO-world-selection-primitive-v1.md:35-43). This is the intended protection against accidentally showing World A data while working in World B; it is not a cross-account ACL.
- **List behavior:** GET `/api/live/world-containers` returns the registry records without a request principal (apps/live_control_server/routes/world_containers.py:44-46). The WorldSelector and PlayWorldPicker put the returned records directly into their menus/lists (apps/live-control-ui/src/selectedWorld/WorldSelector.tsx:22-23,50; apps/live-control-ui/src/playSurface/PlayWorldPicker.tsx:13-14,24); they do not filter by user. The durable World record contains its ID, name, source-root path, creation time, and optional native-Graph binding, but no account owner, member list, or access/visibility policy (apps/live_control_server/services/world_container_registry.py:71-78).
- **Other persisted owner fields:** media assets and Build image preparations have per-resource `owner_id` fields; preparation rows also include `world_id` (src/application_state/media.py:89-91,135; src/application_state/build_proposal/images.py:68,93-105). The local route supplies `principal.subject`, and both local auth methods currently return the shared `local_operator` subject (apps/live_control_server/routes/media_images.py:152,178-193; apps/live_control_server/services/agent_graph_auth.py:95-97,115-118). Agent `owner_scope.owner_id` is also the World/campaign ID in its context construction (apps/live_control_server/routes/agent.py:349-352). These are per-asset/operation scopes or World identity, not a durable mapping from a DMS subject to World membership. The mounted route surface has no DMS principal and the adapter that would resolve `sub` remains unmounted.

So, if “private by default” means GM-only content until a player projection is explicitly cleared, or preventing accidental cross-World mixing in the local application, existing design supports that. If it means each World is visible only to its creator/account among DMS-authenticated users, I found no source contract or enforcement for that behavior. This report does not assign owners to legacy Worlds or choose sharing roles.

### Positive controls observed

- services/agent_graph_auth.py:14-24,48-83,85-119 enables the native Graph local operator only in local/development mode; requires a 32-character non-whitespace bearer token or local session and verifies the ASGI peer is loopback. It ignores forwarded/client identity headers. NativeGraphPrincipal.subject is deliberately the shared local_operator, so this is a single-operator control, not multi-user authorization.
- services/agent_graph_local_session.py:21-29,75-96,110-194 implements a separate local browser session with Host/Origin checks, private state, HttpOnly cookie and HMAC-CSRF for unsafe requests. It must remain distinct from a hosted identity path.
- services/trusted_cookie_origin.py itself is a pure, fail-closed Origin helper for unsafe cookie-authenticated requests. It uses an exact injected allowlist; static search shows only its definition under apps/live_control_server. It currently protects no route.
- services/dms_principal.py fixes a constructor-supplied HTTPS DMS endpoint, makes a single bounded no-redirect request, caps cookie/body sizes and maps invalid/failed responses to no principal. Its docstring explicitly says callers must keep it unmounted until cookie delivery and route wiring are reviewed.
- World/container IDs, document IDs, expected revisions and artifact references are often validated before operations. These structural and concurrency controls are valuable, but they are not caller membership proofs.
- The route tree has 17 explicit retired 410 handlers. They remain in the OpenAPI/runtime inventory but reject their legacy operation; they should not be counted as active behavior.

## Route inventory and current guard coverage

apps/live_control_server/main.py:93-134 constructs a FastAPI app with no app-level auth dependency or middleware, mounts 26 top-level routers (:100-125), and defines /health (:127-129). routes/live.py:167-168 nests the Agent router under /api/live, giving /api/live/agent/.... FastAPI’s default OpenAPI/docs routes are framework-generated in addition to explicit declarations. Static AST inventory of the mounted route modules found **235 explicit declarations across 27 route modules**, plus /health.

A static classification of each route handler found:

- **70** declarations call/use the local Graph GM dependency/guard; this authenticates the shared local GM only.
- **3** are the local-session bootstrap/status/revoke routes and validate the local session contract.
- **162** have no Buddy request-principal guard found by source inspection, including **17** handlers whose declared response is 410 Gone. This leaves 145 active declarations without a route-level Buddy principal guard identified in this inventory. An upstream proxy may add protection, but none was inspected.

| Router / source file | Count | Current guard and major data/side-effect boundary |
|---|---:|---|
| routes/agent.py (nested under /api/live) | 16 | All local Graph GM. Agent turns, history, resolutions, traces, saved sections, source passages, and Build proposals. Provider/runtime and durable turn behavior are behind this route family; the principal remains one local operator. |
| routes/agent_graph_local_session.py | 3 | Local session protocol only; loopback/Host/Origin/session/CSRF controls. Not DMS hosted auth. |
| routes/combat_encounters.py | 5 | No request principal. _verified_world/managed graph binding constrains the selected encounter World, not its user. Registry mutation is persistent. |
| routes/extract_promote.py | 15 | 6 local GM guarded, 9 no Buddy principal. Review/correction/prepare/confirm operations can advance extraction and Worldbuilding publication workflows; distinguish read-only review from confirmation side effects. |
| routes/graph_authoring.py | 4 | No request principal found. Prepare/commit pair; legacy merge-reconciliation prepare/apply return 410. |
| routes/graph_preview.py | 24 | 1 local GM guard, 23 without a Buddy principal. Includes extraction runs, projections, resolver candidates, Gold authoring prepare/commit and review reads; exact source/World selectors are not user ACLs. |
| routes/live.py | 53 | 4 local GM guards, 49 without a Buddy principal; includes 12 410 retired Combat/statblock routes. Session state/events/jobs/surface/layout/commands, source catalogs, Plan edit proposals, Tiptap/statblock workbench, and nested Agent. /state derives and writes current_state.json; rebuild queues a file-backed job; events/jobs are polling JSON, not a stream. |
| routes/media_images.py | 10 | All local GM guarded; service uses principal.subject for owner-scoped rows, but every current caller resolves to local_operator. Generation/catalog can invoke paid/provider APIs. Explicit Save publishes an image with Cloudflare requireSignedURLs=false and public variant. No calls made. |
| routes/party_registry.py | 3 | No request principal found. Prepare/commit updates party registry. |
| routes/play_runs.py | 29 | 11 local GM, 18 without Buddy principal. Legacy and v2 Play run reads/writes, scene proposal/review commands, reference manifests and evidence. Run/World predicates and revision checks constrain stored records but are not membership authorization. Some proposals can invoke generation. |
| routes/recap_ingest.py | 1 | Local GM. Recap ingestion can persist a run and feed later extraction. |
| routes/rules_lookup.py | 3 | Router-level local Graph GM dependency. Catalog/query/passages. The local_operator identity is shared. |
| routes/source_navigation.py | 1 | No request principal found. Source-navigation read. |
| routes/statblock_candidates.py | 7 | No request principal found. Candidate generate/revise/validate/mechanics-accept/reconcile operations, with later threat publication workflow. |
| routes/statblock_integration.py | 1 | No request principal found. Readiness projection. |
| routes/threat_drafts.py | 4 | No request principal found. _admit_world_scope verifies managed World/graph revision, not the caller’s membership. CRUD mutates durable draft records. |
| routes/threat_publication.py | 5 | No request principal found. Starts/reads/refreshes/cancels/retries publication operations; service operation state is not a user-authorization boundary. |
| routes/threat_publication_commits.py | 2 | No request principal found. Confirms publication commit and reads it. |
| routes/threat_publication_identity.py | 3 | 1 local GM for identity-candidate preparation, 2 without Buddy principal. Identity resolution creates/reads operation state. |
| routes/threat_publication_proposals.py | 2 | No request principal found. Prepares/reads publication proposals. |
| routes/threat_query_hydration.py | 1 | Local Graph GM. Query hydration. |
| routes/workspace_documents.py | 22 | No request principal found. Campaign/World document list/create/read/update/revision/source artifact/native source admission and discard/restore. Registry validates World/document identity and roots; no caller owner/member relation. |
| routes/workspace_lifecycle.py | 3 | All local GM. Reversible Trash listing and document/session trash/restore; currently one shared operator. |
| routes/world_containers.py | 4 | List/create are unauthenticated at route level; binding update/deactivation use local Graph GM. Global file-backed registry contains no owner/member fields. |
| routes/world_graph_bootstrap.py | 3 | Retired 410 handlers. |
| routes/world_graph_projection.py | 3 | Local Graph GM. Projection routes. |
| routes/world_graph_retrieval.py | 8 | Local Graph GM. Search/object/neighborhood/evidence/recap-context reads. |

Route counts were generated by parsing route decorators and router prefixes with Python AST, then cross-checking the top-level mounts and nested Agent include. This deliberately does not import or start the application. Full method/path/guard/location list follows in the appendix. The additional explicit app endpoint GET /health is main.py:127-129 and has no principal check.

## Resource ownership and side effects

### Worlds and workspace documents

routes/world_containers.py:43-61 lists and creates without a request principal. services/world_container_registry.py:71-79 stores world_id, name, source_root_relpath, creation time and optional native-Graph binding; no owner/member field exists. CreateWorldContainerRequest at :162-168 accepts only a name (server derives IDs/paths). Binding changes at routes/world_containers.py:61-95 require local Graph GM. This prevents callers choosing arbitrary container path fields, but does not assign an authenticated person as owner.

Workspace APIs cover both campaign and World content. services/workspace_document_registry.py:521-548,693-829,829-1038,1120-1190 stores/filters documents by domain identifiers and checks canonical World IDs, World existence, and document↔World matches. routes/workspace_documents.py:89-591 does not pass a DMS principal into those operations. A valid world_id query is a selector, not proof the caller may access it.

Play v2 persists world_id and run identities (services/play_run_registry.py:733-874) and uses those selectors/revisions for coherent reads, updates and replay. That protects record integrity; the route does not compare a request subject to a World membership record. Combat routes similarly verify a managed graph binding but not a human actor (routes/combat_encounters.py:32-48). Threat and publication routes check World/graph scope and operation identities, not per-user ACL.

### File-backed live state and process workers

config.py:6-20,80-105 selects DUNGEONMIND_LIVE_SESSION_DIR, DMB_MANAGED_WORLD_DATA_ROOT, DUNGEONMIND_WORLD_GRAPH_ROOT and related roots. Unset defaults are within the code repository (session_dir() defaults to evals/c2_live_prep/live/session_22; managed root defaults to repo_root(); graph root defaults to repo_root()/out). session_store.py:22-29,32-75 stores live_packet.json, surface_layout.json, event_log.jsonl, job_queue.jsonl, and derived current_state.json; append_events_and_jobs appends JSONL and refresh_current_state rewrites derived state. GET /api/live/state calls the refresh path. Job completion rewrites the queue; POST /api/live/rebuild-packet adds a job whose documented execution is deferred.

main.py:78-90 creates the Build Jev runtime factory and starts get_hermes_graph_agent_host() in app lifespan, then shuts it down. hermes_graph_agent_host.py:1149-1156 creates multiprocessing request/response queues and a worker process. This is process-local orchestration, not a durable distributed queue or per-user actor. The durable-looking JSONL queue is not evidence of a worker scheduler/retry/lease system. For multiple replicas, repo-default paths and in-memory worker queues do not establish shared consistent state or cross-instance job ownership.

Static search under apps/live_control_server found no declared WebSocket route, StreamingResponse, FileResponse, UploadFile, FastAPI BackgroundTasks, or other route-owned streaming/upload/background-task mechanism. /api/live/events and /api/live/jobs are request/response polling endpoints. The Hermes host is the explicit subprocess-style background runtime found in this scan.

### Media

routes/media_images.py:70-257 places all media routes behind local Graph GM and scopes generated/staged rows using principal.subject. Because local auth modes both emit subject="local_operator", this is one operator namespace. POST /generate calls generation and stages the image; /catalog queries provider metadata; /save calls services/media_storage.py:28-67,73-110. The storage code verifies asset identity/provenance and explicitly requires requireSignedURLs is False, accepts only the public Cloudflare delivery variant, and returns visibility: public (media_storage.py:47-70). Saved image bytes are therefore public at the delivery layer once saved. If Worlds/media are meant private to users, this current public publication contract needs a separately designed access model before exposure. No real media or provider action was executed.

## Decisions required before hosted route wiring

Do not infer “private to creator” or “shared by all invited users” from the existing GM/player content labels or local World-selection contract. The data model currently represents legacy Worlds without an account owner and the user has not selected cross-account World ACL semantics. Choose and record:

1. Whether a World is private, shared, or public by default; who can create, list, read, update, delete/archive and restore it; how invites, roles, sharing and revocation work.
2. Whether all currently managed DMS identities are eligible, and exactly where the restricted population is enforced. Supply external configuration evidence plus one allowed and one denied sign-in witness. The current DMS current-user success alone proves only a valid DMS session.
3. How existing unowned Worlds and their documents, sessions, proposals, media and native graph bindings acquire durable principals. Options to evaluate include an operator inventory/claim based on provenance, an authoritative existing owner map, a deliberately shared operator-owned pilot set, or quarantine/disable until a verified claim. These are choices for the product owner; this inventory changes no records and selects none.
4. Whether saved image assets are intentionally public, and whether users can see each other’s media. The current local-only owner key and public CDN delivery cannot provide private multi-user media isolation.
5. Whether the initial service is strictly one host/private edge or must be horizontally scaled. The selected storage/queue semantics must match that operating model.

The authorization design needs an explicit route policy classification (public read, DMS identity-only, World membership + role, local-only, service/internal) and a mutation/read set per family. Do not mount one generic hosted_owner guard across all /api/live routes: it would neither assign World ACLs nor correctly distinguish local, service, user and intentionally public paths.

## Prioritized readiness gates

| Priority | Finding and evidence | Status / conditional impact | Bounded remedy | Acceptance evidence |
|---|---|---|---|---|
| **P1 — blocks invited/private multi-user exposure** | **No end-to-end per-person World authorization.** Observed: no app-wide guard (main.py:93-125); 162 handlers have no route-level Buddy principal guard, of which 145 are not retired 410 endpoints. World registry has no owner/member (world_container_registry.py:71-79) and list/create are unguarded (world_containers.py:43-61). | Observed code contract; exploitability/reachability is conditional on the uninspected network edge. Any route reachable without an external gate can disclose or mutate common file-backed state; selected routes use only object IDs/World selectors. | Decide ACL semantics first, persist durable user↔World membership/roles, then classify and guard each mounted route by auth mode and resource/action. Recheck authorization at job/operation completion, media/file access, replay and restore—not only at request start. | Synthetic HTTP tests: anonymous denied for protected operations; user A cannot list/read/update/trash/restore/run/resolve/publish or fetch media in B’s World; sharing/revocation and role matrix; local session and service callers retain their independent intended boundary; all route mutations prove rejection precedes side effects. |
| **P1 — blocks reliance on the stated managed population** | **Population eligibility is not evidenced by Buddy source.** Adapter only maps DMS current-user sub; DMS repo auth lookup returns a session identity, but population restriction appears external to these repositories. Buddy adapter is unmounted. | Observed repository boundary; current OAuth audience/Workspace/test-user configuration is unknown. Do not describe this as an open population vulnerability without inspecting the actual authorized Google/DMS configuration. | Establish the externally managed allowed population and keep a fail-closed, auditable eligibility contract at DMS or an explicit Buddy entitlement service. Keep identity separate from World membership. | Config proof plus real/safe test identity allow+deny witnesses; disabled/removed account rejection; callback/current-user contract and stable sub tests. Do not use production credentials in a local test report. |
| **P1 — blocks cookie-auth route integration** | **Hosted resolver/CSRF are dormant.** Observed: dms_principal.py and trusted_cookie_origin.py have no route caller; adapter comment says keep unmounted pending browser delivery. | Observed; user-facing session behavior and cookie arrival at buddy.dungeonmind.net are unknown. Route wiring now would be unproven and a blind integration could fail closed or pass an untrusted write. | After hostname/path selection and population/ACL design, perform controlled browser proof for the DMS HttpOnly cookie on the exact Buddy API request, Origin allowlist, wrong/absent/expired cookie, callback/deep-link, logout/revocation and no cross-origin leak. Then mount the resolver and Origin check only on explicitly cookie-authenticated routes before side effects. | Browser network receipt with cookie redacted; accepted/denied origin cases; no cookie leakage to unrelated hosts; identity expiry/revocation; exact route tests proving wrong World denied and mutations not replayed on auth recovery. No such live test was performed here. |
| **P1 if private media is expected** | **Saved image delivery is deliberately public.** Observed: media_storage.py:47-70 requires requireSignedURLs=false, public URL variant, and returns visibility=public; local owner IDs currently collapse to local_operator. | Source contract observed; whether user expects private media is a product decision. | Explicitly accept public media or design signed/private delivery with per-user/World ACL before hosted exposure. Keep private image metadata separate from public CDN bytes. | Two-user access test against actual delivery contract; if public is intended, explicit UI/product disclosure and prove no private data is embedded in image/provenance. |
| **P2 — single-host durability/scale design gate** | **Live state and queued work are repository-root/file-backed; worker queues are process-local.** Observed: config.py:94-105, session_store.py:22-29, main.py:78-90, hermes_graph_agent_host.py:1149-1156. | Inferred operational risk if deployed on ephemeral filesystem, restarted without persistent mounts, or scaled to multiple workers/replicas. Not a present bug for a single private host with protected persistent volume and one runtime process. | Before scale-out, move durable session/World/job state behind a transactional shared store, define leases/idempotency/cancellation and data migration; until then explicitly run single instance with persistent protected volume and tested backup/restore. | Clean restart and rollback preserve sessions, revisions, Trash, pending operation/job state; two-worker test proves no duplicate execution or lost update before enabling >1 worker/replica. |

## Nonblocking hardening and efficiency opportunities

- Generate and retain a route manifest from FastAPI OpenAPI (with default docs disabled or protected if appropriate); compare it in CI against an explicit auth-mode policy so new routes cannot silently appear outside classification.
- Add route-level mutation and provider-call budgets keyed to a stable principal, World and service-wide limit. Current local identity collapses users; shared quotas are essential before public exposure. Do not assume the R2B/Rules budgets globally cap unrelated image, Build, graph, recap or publication operations.
- Publish readiness separately from /health; current /health returns constant {"status":"ok"} (main.py:127-129) and does not establish DB, external DMS, file-root, media or worker readiness. Keep liveness cheap and add explicit readiness checks for configured roots/dependencies without making provider calls.
- Set production roots outside the source checkout, with persistent volumes, least-privilege OS permissions, backup/restore proof and an explicit one-instance limit until shared state is introduced. Avoid implicitly serving data from repo root.
- Ensure trace/log fields remain privacy-safe. Trace module declares a denylist (services/agent_turn_trace.py:25+); verify production logs and exception paths do not record prompts, cookies, source bodies, image bytes or secrets.
- Review proxy trust, forwarded-header acceptance, TLS termination, request/body/time limits, CORS and CSRF as a coherent route-specific policy. No proxy config was in scope or inspected; unknown configuration is not called a vulnerability.

## Route-wiring rehearsal (offline first; no deployment performed)

1. Resolve managed-population enforcement, user/World role semantics, legacy-world disposition and media privacy. Keep the current hosted_owner option disabled until these contracts exist.
2. Re-anchor the DMS callback/session contract and exact selected Buddy origin/path. Prove real browser cookie delivery only in the separately authorized staging/browser environment. Redact cookie values and avoid recording HAR files that contain credentials.
3. For every route in the appendix, classify: anonymous/public, DMS identity, World permission + role, local-only, or internal service. Record read/write scope, paid-provider use, job completion boundary and cancellation/retry behavior.
4. Add offline ASGI tests at actual route boundaries for identity/eligibility/ACL and side-effect ordering; test representative routes in every family and direct subresource selectors (run, operation, file, image, proposal, revision). Include A↔B isolation and revocation.
5. Stage one World with explicit ownership. Exercise create/list/share/revoke, Plan/Play/document workflows, Agent, graph reads/writes, Trash restore, media prepare/save, publication proposal/commit, browser expiry/logout and restart recovery. Assert data survives restart and rollback.
6. Keep deployment at one instance until transactional shared state and durable work dispatch are proven. Test backups and restore from an isolated copy; do not point checks at production data.
7. Record edge/DNS/TLS/reverse-proxy/firewall configuration and prove app port is not directly reachable where the deployment relies on an edge. Confirm static UI and API share the intended origin; same-origin frontend+API on buddy.dungeonmind.net does not itself need cross-origin CORS, but DMS server-to-server introspection and browser top-level login/callback remain separate origins/contracts.
8. Gate production release on successful, reviewed staging proof and explicit operator release authority. This inventory does not authorize a server inspection, config change, live cookie test, runtime restart or deployment.

## Source / inspection method and limits

- Buddy route and service evidence is pinned to commit 8bcbe69d1b6d7c70734927a314f4ded05846fb76; code anchors are paths/line numbers from that tree and are not line anchors for the uninspected deployed bundle.
- Route counts and appendix are generated from Python AST of checked-in FastAPI router declarations, effective prefixes and handler bodies, then reconciled with main.py mounts and the nested Agent include. This does not import the app or prove proxy behavior.
- Static searches found no WebSocket/SSE/stream/file upload/FastAPI background-task routes in apps/live_control_server. The process worker and JSONL job queue were separately traced.
- No behavioral test was run because this documentation-only slice changes no runtime code. git diff --check and static inventory consistency checks are the verification contract for this report.
- DMS/Google population and deployment topology remain external unknowns. No credentials or cookie values were inspected or printed.

## Appendix A — exhaustive explicit route declarations

The following is the exact decorator-derived method/path inventory for the 235 router declarations. The app-level GET /health endpoint (main.py:127-129) is additional, explicit, and has no principal check. Guard labels mean source-level classification only: local GM is the shared local-operator guard; local session is Buddy’s private local-session API; none found means no Buddy request-principal guard in the handler/router. The 410 rows are retained retired endpoints. Line numbers refer to route decorators in the pinned Buddy tree.

### `agent.py` (16)

| Method | Mounted path | Handler | Guard found | Notes |
|---|---|---|---|---|
| `GET` | `/api/live/agent/worlds/{world_id}/conversation` | `get_world_conversation_history` | local GM |  — `agent.py:1266` |
| `GET` | `/api/live/agent/worlds/{world_id}/conversation/turns/{turn_id}/saved-sections/{segment_index}/{section_event_id}` | `get_world_turn_saved_section` | local GM |  — `agent.py:1412` |
| `GET` | `/api/live/agent/worlds/{world_id}/conversation/turns/{turn_id}/source-passages/{citation_index}` | `get_world_turn_source_passage` | local GM |  — `agent.py:1434` |
| `GET` | `/api/live/agent/worlds/{world_id}/conversation/turns/{turn_id}/context-trace/{trace_id}/source-passages/{source_read_event_id}` | `get_world_historical_source_passage` | local GM |  — `agent.py:1458` |
| `GET` | `/api/live/agent/worlds/{world_id}/conversation/turns/{turn_id}/context-trace` | `get_world_turn_context_trace` | local GM |  — `agent.py:1496` |
| `GET` | `/api/live/agent/worlds/{world_id}/conversation/turns/{turn_id}/context-trace/{trace_id}/prompt/{provider_attempt_id}` | `get_world_turn_prompt` | local GM |  — `agent.py:1515` |
| `GET` | `/api/live/agent/worlds/{world_id}/conversation/commands/{command_id}` | `get_new_world_conversation_status` | local GM |  — `agent.py:1546` |
| `POST` | `/api/live/agent/worlds/{world_id}/conversation/commands/{command_id}/resolve` | `post_world_command_resolution` | local GM |  — `agent.py:1581` |
| `GET` | `/api/live/agent/worlds/{world_id}/conversation/commands/{command_id}/resolutions/{operation_id}` | `get_world_command_resolution` | local GM |  — `agent.py:1594` |
| `POST` | `/api/live/agent/worlds/{world_id}/conversation/new` | `post_new_world_conversation` | local GM |  — `agent.py:1620` |
| `POST` | `/api/live/agent/turn` | `post_agent_turn` | local GM |  — `agent.py:1654` |
| `POST` | `/api/live/agent/worlds/{world_id}/build-proposals` | `post_build_document_proposal` | local GM |  — `agent.py:1737` |
| `GET` | `/api/live/agent/worlds/{world_id}/build-proposals` | `list_build_document_proposals` | local GM |  — `agent.py:1754` |
| `GET` | `/api/live/agent/worlds/{world_id}/build-proposals/{action_id}` | `get_build_document_proposal` | local GM |  — `agent.py:1769` |
| `GET` | `/api/live/agent/worlds/{world_id}/build-proposals/{action_id}/prompt` | `get_build_document_proposal_prompt` | local GM |  — `agent.py:1783` |
| `POST` | `/api/live/agent/worlds/{world_id}/build-proposals/{action_id}/inserted` | `report_build_document_proposal_inserted` | local GM |  — `agent.py:1799` |

### `agent_graph_local_session.py` (3)

| Method | Mounted path | Handler | Guard found | Notes |
|---|---|---|---|---|
| `POST` | `/api/live/agent/local-session/` | `bootstrap` | local session |  — `agent_graph_local_session.py:23` |
| `GET` | `/api/live/agent/local-session/` | `status` | local session |  — `agent_graph_local_session.py:34` |
| `DELETE` | `/api/live/agent/local-session/` | `revoke` | local session |  — `agent_graph_local_session.py:41` |

### `combat_encounters.py` (5)

| Method | Mounted path | Handler | Guard found | Notes |
|---|---|---|---|---|
| `GET` | `/api/live/combat/encounters/` | `list_encounters` | none found |  — `combat_encounters.py:45` |
| `POST` | `/api/live/combat/encounters/` | `create_encounter_route` | none found |  — `combat_encounters.py:54` |
| `GET` | `/api/live/combat/encounters/{encounter_id}` | `get_encounter_route` | none found |  — `combat_encounters.py:68` |
| `PUT` | `/api/live/combat/encounters/{encounter_id}` | `save_encounter_route` | none found |  — `combat_encounters.py:82` |
| `POST` | `/api/live/combat/encounters/{encounter_id}/statblocks/{artifact_id}` | `add_generated_statblock_route` | none found |  — `combat_encounters.py:97` |

### `extract_promote.py` (15)

| Method | Mounted path | Handler | Guard found | Notes |
|---|---|---|---|---|
| `GET` | `/api/live/extract-promote/runs/{run_id}/worldbuilding-publication-coverage` | `get_worldbuilding_publication_coverage_route` | local GM |  — `extract_promote.py:149` |
| `GET` | `/api/live/extract-promote/status` | `get_extract_promote_status` | none found |  — `extract_promote.py:186` |
| `GET` | `/api/live/extract-promote/runs/{run_id}/review-package` | `get_extract_promote_exact_run_review` | none found |  — `extract_promote.py:204` |
| `POST` | `/api/live/extract-promote/runs/{run_id}/evidence-corrections` | `post_exact_run_evidence_corrections` | none found |  — `extract_promote.py:226` |
| `POST` | `/api/live/extract-promote/runs/{run_id}/recap-evidence-corrections` | `post_recap_evidence_corrections` | local GM |  — `extract_promote.py:256` |
| `POST` | `/api/live/extract-promote/runs/{run_id}/recap-candidate-corrections` | `post_recap_candidate_corrections` | local GM |  — `extract_promote.py:288` |
| `POST` | `/api/live/extract-promote/runs/{run_id}/semantic-disposition` | `post_recap_semantic_disposition` | local GM |  — `extract_promote.py:330` |
| `POST` | `/api/live/extract-promote/runs/{run_id}/selection-context` | `post_ingest_selection_context` | local GM |  — `extract_promote.py:359` |
| `POST` | `/api/live/extract-promote/prepare` | `post_extract_promote_prepare` | none found |  — `extract_promote.py:384` |
| `GET` | `/api/live/extract-promote/worldbuilding/capabilities` | `get_worldbuilding_publication_capabilities` | local GM |  — `extract_promote.py:418` |
| `POST` | `/api/live/extract-promote/worldbuilding/prepare` | `post_worldbuilding_write_plan_prepare` | none found |  — `extract_promote.py:448` |
| `POST` | `/api/live/extract-promote/worldbuilding/confirm` | `post_worldbuilding_write_plan_confirm` | none found |  — `extract_promote.py:484` |
| `POST` | `/api/live/extract-promote/worldbuilding/first-world/prepare` | `post_first_world_prepare` | none found |  — `extract_promote.py:520` |
| `POST` | `/api/live/extract-promote/worldbuilding/first-world/confirm` | `post_first_world_confirm` | none found |  — `extract_promote.py:556` |
| `POST` | `/api/live/extract-promote/confirm` | `post_extract_promote_confirm` | none found |  — `extract_promote.py:592` |

### `graph_authoring.py` (4)

| Method | Mounted path | Handler | Guard found | Notes |
|---|---|---|---|---|
| `POST` | `/api/live/graph-authoring/prepare` | `post_graph_object_authoring_prepare` | none found |  — `graph_authoring.py:33` |
| `POST` | `/api/live/graph-authoring/commit` | `post_graph_object_authoring_commit` | none found |  — `graph_authoring.py:46` |
| `POST` | `/api/live/graph-authoring/merge-reconciliation/prepare` | `post_graph_merge_reconciliation_prepare` | none found |  — `graph_authoring.py:59` |
| `POST` | `/api/live/graph-authoring/merge-reconciliation/apply` | `post_graph_merge_reconciliation_apply` | none found |  — `graph_authoring.py:66` |

### `graph_preview.py` (24)

| Method | Mounted path | Handler | Guard found | Notes |
|---|---|---|---|---|
| `GET` | `/api/live/graph-preview/artifacts` | `get_recap_artifacts` | none found |  — `graph_preview.py:95` |
| `GET` | `/api/live/graph-preview/runs` | `get_graph_preview_runs` | none found |  — `graph_preview.py:105` |
| `GET` | `/api/live/graph-preview/latest` | `get_graph_preview_latest` | none found |  — `graph_preview.py:120` |
| `GET` | `/api/live/graph-preview/graph-ingest/runs` | `get_graph_ingest_runs` | none found |  — `graph_preview.py:161` |
| `GET` | `/api/live/graph-preview/extraction-runs/{run_id}` | `get_extraction_run_by_id` | none found |  — `graph_preview.py:185` |
| `GET` | `/api/live/graph-preview/extraction-runs/{run_id}/recap-inspection` | `get_extraction_run_recap_inspection` | none found |  — `graph_preview.py:204` |
| `GET` | `/api/live/graph-preview/extraction-runs/{run_id}/candidate-projection` | `get_extraction_run_candidate_projection` | local GM |  — `graph_preview.py:223` |
| `GET` | `/api/live/graph-preview/extraction-runs/{run_id}/recap-projection` | `get_extraction_run_recap_projection` | none found |  — `graph_preview.py:263` |
| `GET` | `/api/live/graph-preview/extraction-runs/{run_id}/build-context` | `get_extraction_run_build_context` | none found |  — `graph_preview.py:314` |
| `POST` | `/api/live/graph-preview/extraction-runs` | `post_extraction_run` | none found |  — `graph_preview.py:379` |
| `GET` | `/api/live/graph-preview/graph-ingest/latest` | `get_latest_graph_ingest_run` | none found |  — `graph_preview.py:543` |
| `GET` | `/api/live/graph-preview/union-supergraph/projection` | `get_union_supergraph_projection` | none found |  — `graph_preview.py:563` |
| `POST` | `/api/live/graph-preview/existing-object-resolver/candidates` | `post_existing_object_resolver_candidates` | none found |  — `graph_preview.py:584` |
| `POST` | `/api/live/graph-preview/gold-authoring/prepare` | `post_gold_authoring_prepare` | none found |  — `graph_preview.py:595` |
| `POST` | `/api/live/graph-preview/gold-authoring/commit` | `post_gold_authoring_commit` | none found |  — `graph_preview.py:606` |
| `POST` | `/api/live/graph-preview/gold-authoring/verify-commit` | `post_gold_authoring_verify_commit` | none found |  — `graph_preview.py:617` |
| `GET` | `/api/live/graph-preview/gold-review/sessions` | `get_gold_review_sessions` | none found |  — `graph_preview.py:628` |
| `GET` | `/api/live/graph-preview/gold-review/compare` | `get_gold_review_compare` | none found |  — `graph_preview.py:634` |
| `GET` | `/api/live/graph-preview/gold-review/evidence` | `get_gold_review_evidence` | none found |  — `graph_preview.py:652` |
| `GET` | `/api/live/graph-preview/gold-review/projection` | `get_gold_review_projection` | none found |  — `graph_preview.py:674` |
| `GET` | `/api/live/graph-preview/gold-review/vocabulary-ablation` | `get_gold_review_vocabulary_ablation` | none found |  — `graph_preview.py:692` |
| `GET` | `/api/live/graph-preview/manual-review/beds` | `get_manual_review_beds` | none found |  — `graph_preview.py:708` |
| `GET` | `/api/live/graph-preview/manual-review/beds/{bed_id}` | `get_manual_review_bed` | none found |  — `graph_preview.py:717` |
| `GET` | `/api/live/graph-preview/recap` | `get_recap_graph_presentation` | none found |  — `graph_preview.py:726` |

### `live.py` (53)

| Method | Mounted path | Handler | Guard found | Notes |
|---|---|---|---|---|
| `POST` | `/api/live/citation-source` | `post_citation_source` | none found |  — `live.py:320` |
| `POST` | `/api/live/citation-freshness` | `post_citation_freshness` | none found |  — `live.py:334` |
| `GET` | `/api/live/source-bundle` | `get_ingestion_source_bundle` | none found |  — `live.py:347` |
| `GET` | `/api/live/locations/index` | `get_location_corpus_index` | none found |  — `live.py:366` |
| `GET` | `/api/live/roll-tables/index` | `get_roll_table_corpus_index` | none found |  — `live.py:380` |
| `GET` | `/api/live/npcs/index` | `get_npc_corpus_index` | none found |  — `live.py:394` |
| `GET` | `/api/live/statblocks/index` | `get_statblock_corpus_index` | none found |  — `live.py:406` |
| `GET` | `/api/live/statblocks/view/generated` | `get_generated_statblock_view_list` | none found |  — `live.py:420` |
| `GET` | `/api/live/statblocks/view/generated/{artifact_id}` | `get_generated_statblock_view_detail` | none found |  — `live.py:434` |
| `GET` | `/api/live/combat/current` | `get_current_combat` | none found | HTTP 410 (retired) — `live.py:465` |
| `PATCH` | `/api/live/combat/current/entities/{entity_id}` | `patch_current_combat_entity` | none found | HTTP 410 (retired) — `live.py:470` |
| `POST` | `/api/live/combat/current/entities/{entity_id}/hp-delta` | `post_current_combat_entity_hp_delta` | none found | HTTP 410 (retired) — `live.py:478` |
| `POST` | `/api/live/combat/current/sort-initiative` | `post_current_combat_sort_initiative` | none found | HTTP 410 (retired) — `live.py:486` |
| `POST` | `/api/live/combat/current/active-turn` | `post_current_combat_active_turn` | none found | HTTP 410 (retired) — `live.py:491` |
| `POST` | `/api/live/combat/current/turn` | `post_current_combat_turn` | none found | HTTP 410 (retired) — `live.py:496` |
| `GET` | `/api/live/combat/saves` | `get_combat_saves` | none found | HTTP 410 (retired) — `live.py:501` |
| `POST` | `/api/live/combat/current/load` | `post_combat_current_load` | none found | HTTP 410 (retired) — `live.py:506` |
| `POST` | `/api/live/combat/current/unload` | `post_combat_current_unload` | none found | HTTP 410 (retired) — `live.py:511` |
| `POST` | `/api/live/combat/current/new` | `post_combat_current_new` | none found | HTTP 410 (retired) — `live.py:516` |
| `POST` | `/api/live/combat/saves` | `post_combat_save_current` | none found | HTTP 410 (retired) — `live.py:521` |
| `POST` | `/api/live/statblocks/view/generated/{artifact_id}/combat/add` | `post_generated_statblock_combat_add` | none found | HTTP 410 (retired) — `live.py:526` |
| `GET` | `/api/live/statblocks/workbench/sample` | `get_statblock_workbench_sample` | none found |  — `live.py:537` |
| `POST` | `/api/live/statblocks/workbench/command` | `post_statblock_workbench_command` | none found |  — `live.py:549` |
| `POST` | `/api/live/statblocks/workbench/drafts` | `post_statblock_workbench_draft` | none found |  — `live.py:562` |
| `GET` | `/api/live/statblocks/workbench/drafts` | `get_statblock_workbench_drafts` | none found |  — `live.py:590` |
| `GET` | `/api/live/statblocks/workbench/drafts/{artifact_id}` | `get_statblock_workbench_draft` | none found |  — `live.py:601` |
| `POST` | `/api/live/statblocks/workbench/drafts/{artifact_id}/corpus-preview` | `post_statblock_workbench_draft_corpus_preview` | none found |  — `live.py:618` |
| `POST` | `/api/live/statblocks/workbench/drafts/{artifact_id}/corpus-write/prepare` | `post_statblock_workbench_draft_corpus_write_prepare` | none found |  — `live.py:647` |
| `POST` | `/api/live/statblocks/workbench/drafts/{artifact_id}/corpus-write/commit` | `post_statblock_workbench_draft_corpus_write_commit` | none found |  — `live.py:678` |
| `POST` | `/api/live/statblocks/workbench/drafts/{artifact_id}/retrieval/activate` | `post_statblock_workbench_draft_retrieval_activate` | none found |  — `live.py:711` |
| `POST` | `/api/live/statblocks/workbench/drafts/{artifact_id}/retrieval/verify` | `post_statblock_workbench_draft_retrieval_verify` | none found |  — `live.py:737` |
| `POST` | `/api/live/tiptap/markdown-write/prepare` | `post_tiptap_markdown_write_prepare` | local GM |  — `live.py:771` |
| `POST` | `/api/live/tiptap/markdown-write/commit` | `post_tiptap_markdown_write_commit` | local GM |  — `live.py:787` |
| `POST` | `/api/live/query` | `post_live_query` | local GM |  — `live.py:803` |
| `POST` | `/api/live/plan-document-edit/propose` | `post_plan_document_edit_proposal` | none found |  — `live.py:942` |
| `POST` | `/api/live/world-plan-edit/propose` | `post_world_plan_document_edit_proposal` | none found |  — `live.py:958` |
| `GET` | `/api/live/world-plan-edit/actions` | `get_world_plan_document_edit_actions` | none found |  — `live.py:980` |
| `GET` | `/api/live/world-plan-edit/conversation-actions` | `get_world_plan_edit_conversation_actions` | none found |  — `live.py:1007` |
| `GET` | `/api/live/state` | `get_live_state` | none found |  — `live.py:1033` |
| `GET` | `/api/live/events` | `get_live_events` | none found |  — `live.py:1038` |
| `GET` | `/api/live/jobs` | `get_live_jobs` | none found |  — `live.py:1045` |
| `GET` | `/api/live/surface` | `get_live_surface` | none found |  — `live.py:1052` |
| `GET` | `/api/live/plan-view` | `get_live_plan_view` | none found |  — `live.py:1063` |
| `GET` | `/api/live/artifact` | `get_live_artifact` | none found |  — `live.py:1108` |
| `GET` | `/api/live/capabilities` | `get_live_capabilities` | none found |  — `live.py:1130` |
| `POST` | `/api/live/commands` | `post_live_command` | none found |  — `live.py:1149` |
| `PUT` | `/api/live/surface/layout` | `put_live_surface_layout` | none found |  — `live.py:1164` |
| `POST` | `/api/live/jobs/{job_id}/complete` | `post_complete_job` | none found |  — `live.py:1177` |
| `POST` | `/api/live/resolve-roll` | `post_resolve_roll` | none found |  — `live.py:1185` |
| `POST` | `/api/live/rebuild-packet` | `post_rebuild_packet` | none found | HTTP 202 — `live.py:1211` |
| `GET` | `/api/live/world-plan-edit/actions/{action_id}/prompts` | `get_plan_action_prompt_index` | none found |  — `live.py:1240` |
| `GET` | `/api/live/world-plan-edit/actions/{action_id}/prompts/{provider_attempt_id}` | `get_plan_action_prompt_body` | none found |  — `live.py:1245` |
| `GET` | `/api/live/world-plan-edit/actions/{action_id}/terminal-diagnostic` | `get_plan_action_terminal_diagnostic` | local GM |  — `live.py:1251` |

### `media_images.py` (10)

| Method | Mounted path | Handler | Guard found | Notes |
|---|---|---|---|---|
| `GET` | `/api/live/media/images/capabilities` | `image_capabilities` | local GM |  — `media_images.py:70` |
| `GET` | `/api/live/media/images/catalog` | `image_model_catalog` | local GM |  — `media_images.py:84` |
| `POST` | `/api/live/media/images/generate` | `generate_image_preview` | local GM |  — `media_images.py:114` |
| `GET` | `/api/live/media/images/library` | `image_library` | local GM |  — `media_images.py:171` |
| `GET` | `/api/live/media/images/preparations/list` | `image_preparations` | local GM |  — `media_images.py:188` |
| `GET` | `/api/live/media/images/preparations/{action_id}` | `image_preparation` | local GM |  — `media_images.py:198` |
| `POST` | `/api/live/media/images/preparations/{action_id}/asset` | `associate_image` | local GM |  — `media_images.py:214` |
| `GET` | `/api/live/media/images/{asset_id}/metadata` | `image_metadata` | local GM |  — `media_images.py:227` |
| `GET` | `/api/live/media/images/{asset_id}` | `image_record` | local GM |  — `media_images.py:237` |
| `POST` | `/api/live/media/images/{asset_id}/save` | `save_image` | local GM |  — `media_images.py:252` |

### `party_registry.py` (3)

| Method | Mounted path | Handler | Guard found | Notes |
|---|---|---|---|---|
| `GET` | `/api/live/party-registry/` | `get_party_registry` | none found |  — `party_registry.py:27` |
| `POST` | `/api/live/party-registry/session-roster/prepare` | `post_party_registry_session_roster_prepare` | none found |  — `party_registry.py:39` |
| `POST` | `/api/live/party-registry/session-roster/commit` | `post_party_registry_session_roster_commit` | none found |  — `party_registry.py:53` |

### `play_runs.py` (29)

| Method | Mounted path | Handler | Guard found | Notes |
|---|---|---|---|---|
| `GET` | `/api/live/play-active-run` | `get_play_active_run_route` | none found |  — `play_runs.py:60` |
| `PUT` | `/api/live/play-active-run` | `put_play_active_run_route` | none found |  — `play_runs.py:69` |
| `GET` | `/api/live/play-runs` | `get_play_runs` | none found |  — `play_runs.py:78` |
| `PUT` | `/api/live/play-runs/{run_id}` | `put_play_run` | none found |  — `play_runs.py:94` |
| `PUT` | `/api/live/play-runs/{run_id}/reference-manifest` | `put_play_run_reference_manifest` | none found |  — `play_runs.py:109` |
| `GET` | `/api/live/play-runs/{run_id}/reference-manifest` | `get_play_run_reference_manifest_route` | none found |  — `play_runs.py:130` |
| `PUT` | `/api/live/play-runs/{run_id}/progress` | `put_play_run_progress_route` | none found |  — `play_runs.py:145` |
| `PUT` | `/api/live/play-runs/{run_id}/rebase` | `put_play_run_rebase` | none found |  — `play_runs.py:162` |
| `GET` | `/api/live/play-runs/{run_id}` | `get_play_run_route` | none found |  — `play_runs.py:179` |
| `GET` | `/api/live/world-play-runs/v2` | `get_world_play_runs_v2` | none found |  — `play_runs.py:194` |
| `GET` | `/api/live/world-play-runs/v2/active` | `get_world_play_active_run_v2` | none found |  — `play_runs.py:210` |
| `PUT` | `/api/live/world-play-runs/v2/active` | `put_world_play_active_run_v2` | none found |  — `play_runs.py:223` |
| `PUT` | `/api/live/world-play-runs/v2/{run_id}` | `put_world_play_run_v2` | none found |  — `play_runs.py:239` |
| `GET` | `/api/live/world-play-runs/v2/{run_id}` | `get_world_play_run_v2` | none found |  — `play_runs.py:259` |
| `PUT` | `/api/live/world-play-runs/v2/{run_id}/progress` | `put_world_play_run_progress_v2` | none found |  — `play_runs.py:271` |
| `PUT` | `/api/live/world-play-runs/v2/{run_id}/rebase` | `put_world_play_run_rebase_v2` | none found |  — `play_runs.py:292` |
| `GET` | `/api/live/world-play-runs/v2/{run_id}/reference-manifest` | `get_world_play_run_reference_manifest_v2` | none found |  — `play_runs.py:316` |
| `PUT` | `/api/live/world-play-runs/v2/{run_id}/reference-manifest` | `put_world_play_run_reference_manifest_v2` | none found |  — `play_runs.py:336` |
| `GET` | `/api/live/world-play-runs/v2/{run_id}/content` | `get_world_run_content` | local GM |  — `play_runs.py:364` |
| `GET` | `/api/live/world-play-runs/v2/{run_id}/content/revisions/{revision_n}` | `get_world_run_content_revision` | local GM |  — `play_runs.py:380` |
| `GET` | `/api/live/world-play-runs/v2/{run_id}/content/commands/{command_id}` | `get_world_run_content_command` | local GM |  — `play_runs.py:401` |
| `PUT` | `/api/live/world-play-runs/v2/{run_id}/content/commands/{command_id}` | `put_world_run_content_command` | local GM |  — `play_runs.py:422` |
| `GET` | `/api/live/world-play-runs/v2/{run_id}/content/proposals` | `list_world_run_scene_proposals` | local GM |  — `play_runs.py:457` |
| `GET` | `/api/live/world-play-runs/v2/{run_id}/content/proposals/{proposal_id}` | `get_world_run_scene_proposal` | local GM |  — `play_runs.py:473` |
| `POST` | `/api/live/world-play-runs/v2/{run_id}/content/proposals/{proposal_id}` | `post_world_run_scene_proposal` | local GM |  — `play_runs.py:489` |
| `GET` | `/api/live/world-play-runs/v2/{run_id}/review` | `get_world_session_review` | local GM |  — `play_runs.py:516` |
| `PUT` | `/api/live/world-play-runs/v2/{run_id}/review/commands/{command_id}` | `put_world_session_review` | local GM |  — `play_runs.py:528` |
| `GET` | `/api/live/world-session-evidence` | `list_session_evidence_route` | local GM |  — `play_runs.py:550` |
| `GET` | `/api/live/world-session-evidence/{run_id}/revisions/{revision}` | `read_session_evidence_route` | local GM |  — `play_runs.py:560` |

### `recap_ingest.py` (1)

| Method | Mounted path | Handler | Guard found | Notes |
|---|---|---|---|---|
| `POST` | `/api/live/recap-ingest` | `post_recap_ingest` | local GM |  — `recap_ingest.py:447` |

### `rules_lookup.py` (3)

| Method | Mounted path | Handler | Guard found | Notes |
|---|---|---|---|---|
| `GET` | `/api/live/rules/catalog` | `get_catalog` | local GM |  — `rules_lookup.py:17` |
| `GET` | `/api/live/rules/query` | `get_query` | local GM |  — `rules_lookup.py:21` |
| `GET` | `/api/live/rules/passages/{citation_id}` | `get_passage` | local GM |  — `rules_lookup.py:27` |

### `source_navigation.py` (1)

| Method | Mounted path | Handler | Guard found | Notes |
|---|---|---|---|---|
| `GET` | `/api/live/source-navigation` | `get_source_navigation` | none found |  — `source_navigation.py:19` |

### `statblock_candidates.py` (7)

| Method | Mounted path | Handler | Guard found | Notes |
|---|---|---|---|---|
| `POST` | `/api/live/threat-drafts/{draft_id}/candidates:generate` | `post_generate_candidate` | none found |  — `statblock_candidates.py:46` |
| `POST` | `/api/live/threat-drafts/{draft_id}/candidates:revise` | `post_revise_candidate_from_edited_definition` | none found |  — `statblock_candidates.py:62` |
| `GET` | `/api/live/statblock-candidates/{candidate_id}` | `get_statblock_candidate` | none found |  — `statblock_candidates.py:82` |
| `POST` | `/api/live/statblock-definitions:validate` | `post_validate_definition` | none found |  — `statblock_candidates.py:88` |
| `POST` | `/api/live/threat-drafts/{draft_id}/mechanics:accept` | `post_accept_mechanics` | none found |  — `statblock_candidates.py:95` |
| `GET` | `/api/live/threat-drafts/{draft_id}/acceptance-operations/{operation_id}` | `get_acceptance_operation_route` | none found |  — `statblock_candidates.py:110` |
| `POST` | `/api/live/threat-drafts/{draft_id}/acceptance-operations/{operation_id}:reconcile` | `post_reconcile_acceptance` | none found |  — `statblock_candidates.py:124` |

### `statblock_integration.py` (1)

| Method | Mounted path | Handler | Guard found | Notes |
|---|---|---|---|---|
| `GET` | `/api/live/statblocks/v1/readiness` | `get_statblock_integration_readiness` | none found |  — `statblock_integration.py:15` |

### `threat_drafts.py` (4)

| Method | Mounted path | Handler | Guard found | Notes |
|---|---|---|---|---|
| `POST` | `/api/live/threat-drafts/` | `post_threat_draft` | none found |  — `threat_drafts.py:60` |
| `GET` | `/api/live/threat-drafts/` | `get_threat_drafts` | none found |  — `threat_drafts.py:73` |
| `GET` | `/api/live/threat-drafts/{draft_id}` | `get_threat_draft_route` | none found |  — `threat_drafts.py:98` |
| `PUT` | `/api/live/threat-drafts/{draft_id}` | `put_threat_draft` | none found |  — `threat_drafts.py:107` |

### `threat_publication.py` (5)

| Method | Mounted path | Handler | Guard found | Notes |
|---|---|---|---|---|
| `POST` | `/api/live/threat-drafts/{draft_id}/publication-operations` | `post_begin_publication_operation` | none found |  — `threat_publication.py:97` |
| `GET` | `/api/live/threat-drafts/{draft_id}/publication-operations/{operation_id}` | `get_publication_operation` | none found |  — `threat_publication.py:106` |
| `POST` | `/api/live/threat-drafts/{draft_id}/publication-operations/{operation_id}/refresh` | `post_refresh_publication_operation` | none found |  — `threat_publication.py:114` |
| `POST` | `/api/live/threat-drafts/{draft_id}/publication-operations/{operation_id}/cancel` | `post_cancel_publication_operation` | none found |  — `threat_publication.py:122` |
| `POST` | `/api/live/threat-drafts/{draft_id}/publication-operations/{operation_id}/retry` | `post_retry_publication_operation` | none found |  — `threat_publication.py:132` |

### `threat_publication_commits.py` (2)

| Method | Mounted path | Handler | Guard found | Notes |
|---|---|---|---|---|
| `POST` | `/api/live/threat-drafts/{draft_id}/publication-operations/{operation_id}/proposals/{proposal_id}/commits` | `post_confirm_publication_commit` | none found |  — `threat_publication_commits.py:105` |
| `GET` | `/api/live/threat-drafts/{draft_id}/publication-operations/{operation_id}/commits/{commit_id}` | `get_publication_commit` | none found |  — `threat_publication_commits.py:128` |

### `threat_publication_identity.py` (3)

| Method | Mounted path | Handler | Guard found | Notes |
|---|---|---|---|---|
| `POST` | `/api/live/threat-drafts/{draft_id}/publication-operations/{operation_id}/identity-candidates/prepare` | `post_prepare_identity_candidates` | local GM |  — `threat_publication_identity.py:107` |
| `POST` | `/api/live/threat-drafts/{draft_id}/publication-operations/{operation_id}/identity-resolutions` | `post_identity_resolution` | none found |  — `threat_publication_identity.py:125` |
| `GET` | `/api/live/threat-drafts/{draft_id}/publication-operations/{operation_id}/identity-resolutions/{resolution_id}` | `get_identity_resolution` | none found |  — `threat_publication_identity.py:139` |

### `threat_publication_proposals.py` (2)

| Method | Mounted path | Handler | Guard found | Notes |
|---|---|---|---|---|
| `POST` | `/api/live/threat-drafts/{draft_id}/publication-operations/{operation_id}/identity-resolutions/{resolution_id}/proposals` | `post_prepare_publication_proposal` | none found |  — `threat_publication_proposals.py:103` |
| `GET` | `/api/live/threat-drafts/{draft_id}/publication-operations/{operation_id}/proposals/{proposal_id}` | `get_publication_proposal` | none found |  — `threat_publication_proposals.py:126` |

### `threat_query_hydration.py` (1)

| Method | Mounted path | Handler | Guard found | Notes |
|---|---|---|---|---|
| `POST` | `/api/live/threats/query-hydration` | `post_threat_query_hydration` | local GM |  — `threat_query_hydration.py:25` |

### `workspace_documents.py` (22)

| Method | Mounted path | Handler | Guard found | Notes |
|---|---|---|---|---|
| `GET` | `/api/live/workspace-documents` | `get_workspace_documents` | none found |  — `workspace_documents.py:89` |
| `POST` | `/api/live/workspace-documents` | `post_workspace_document` | none found |  — `workspace_documents.py:109` |
| `GET` | `/api/live/workspace-documents/world-plans` | `get_world_owned_plans` | none found |  — `workspace_documents.py:130` |
| `POST` | `/api/live/workspace-documents/world-plans` | `post_world_owned_plan` | none found |  — `workspace_documents.py:153` |
| `GET` | `/api/live/workspace-documents/world-runbooks` | `get_world_owned_runbooks` | none found |  — `workspace_documents.py:164` |
| `POST` | `/api/live/workspace-documents/world-runbooks` | `post_world_owned_runbook` | none found |  — `workspace_documents.py:186` |
| `GET` | `/api/live/workspace-documents/world-runbooks/{document_id}` | `get_world_owned_runbook` | none found |  — `workspace_documents.py:202` |
| `GET` | `/api/live/workspace-documents/world-runbooks/{document_id}/snapshot` | `get_world_owned_runbook_snapshot` | none found |  — `workspace_documents.py:226` |
| `POST` | `/api/live/workspace-documents/world-runbooks/{document_id}/tiptap/prepare` | `post_world_owned_runbook_tiptap_prepare` | none found |  — `workspace_documents.py:250` |
| `POST` | `/api/live/workspace-documents/world-runbooks/{document_id}/tiptap/commit` | `post_world_owned_runbook_tiptap_commit` | none found |  — `workspace_documents.py:282` |
| `GET` | `/api/live/workspace-documents/world-runbooks/{document_id}/committed-revision` | `get_world_owned_runbook_current_revision` | none found |  — `workspace_documents.py:314` |
| `GET` | `/api/live/workspace-documents/world-runbooks/{document_id}/committed-revision/{revision_n}` | `get_world_owned_runbook_exact_revision` | none found |  — `workspace_documents.py:341` |
| `GET` | `/api/live/workspace-documents/{document_id}` | `get_workspace_document_route` | none found |  — `workspace_documents.py:390` |
| `GET` | `/api/live/workspace-documents/{document_id}/snapshot` | `get_workspace_document_snapshot_route` | none found |  — `workspace_documents.py:406` |
| `GET` | `/api/live/workspace-documents/{document_id}/committed-revision` | `get_workspace_document_current_committed_revision` | none found |  — `workspace_documents.py:423` |
| `GET` | `/api/live/workspace-documents/{document_id}/committed-revision/{revision_n}` | `get_workspace_document_exact_committed_revision` | none found |  — `workspace_documents.py:437` |
| `PATCH` | `/api/live/workspace-documents/{document_id}` | `patch_workspace_document_metadata` | none found |  — `workspace_documents.py:451` |
| `POST` | `/api/live/workspace-documents/{document_id}/discard` | `post_workspace_document_discard` | none found |  — `workspace_documents.py:487` |
| `POST` | `/api/live/workspace-documents/{document_id}/restore` | `post_workspace_document_restore` | none found |  — `workspace_documents.py:506` |
| `POST` | `/api/live/workspace-documents/{document_id}/source-artifact` | `post_workspace_document_source_artifact` | none found |  — `workspace_documents.py:525` |
| `GET` | `/api/live/workspace-documents/{document_id}/native-world-source` | `get_native_world_source_status` | none found |  — `workspace_documents.py:568` |
| `POST` | `/api/live/workspace-documents/{document_id}/native-world-source` | `post_native_world_source_admission` | none found |  — `workspace_documents.py:587` |

### `workspace_lifecycle.py` (3)

| Method | Mounted path | Handler | Guard found | Notes |
|---|---|---|---|---|
| `GET` | `/api/live/world-workspace/trash` | `get_world_trash` | local GM |  — `workspace_lifecycle.py:63` |
| `POST` | `/api/live/world-workspace/documents/{document_id}/{action}` | `mutate_world_document_trash` | local GM |  — `workspace_lifecycle.py:72` |
| `POST` | `/api/live/world-workspace/sessions/{run_id}/{action}` | `mutate_world_session_trash` | local GM |  — `workspace_lifecycle.py:93` |

### `world_containers.py` (4)

| Method | Mounted path | Handler | Guard found | Notes |
|---|---|---|---|---|
| `GET` | `/api/live/world-containers` | `get_world_containers` | none found |  — `world_containers.py:43` |
| `POST` | `/api/live/world-containers` | `post_world_container` | none found |  — `world_containers.py:52` |
| `PUT` | `/api/live/world-containers/{managed_world_id}/native-graph-binding` | `put_native_graph_binding` | local GM |  — `world_containers.py:61` |
| `POST` | `/api/live/world-containers/{managed_world_id}/native-graph-binding/deactivate` | `post_deactivate_native_graph_binding` | local GM |  — `world_containers.py:83` |

### `world_graph_bootstrap.py` (3)

| Method | Mounted path | Handler | Guard found | Notes |
|---|---|---|---|---|
| `GET` | `/api/live/world-graph-bootstrap/status` | `get_bootstrap_status` | none found |  — `world_graph_bootstrap.py:32` |
| `POST` | `/api/live/world-graph-bootstrap/prepare` | `post_bootstrap_prepare` | none found |  — `world_graph_bootstrap.py:38` |
| `POST` | `/api/live/world-graph-bootstrap/confirm` | `post_bootstrap_confirm` | none found |  — `world_graph_bootstrap.py:44` |

### `world_graph_projection.py` (3)

| Method | Mounted path | Handler | Guard found | Notes |
|---|---|---|---|---|
| `POST` | `/api/live/world-graph/projection` | `post_world_graph_projection` | local GM |  — `world_graph_projection.py:101` |
| `POST` | `/api/live/world-graph/managed-projection` | `post_managed_world_graph_projection` | local GM |  — `world_graph_projection.py:122` |
| `POST` | `/api/live/world-graph/recap-projection` | `post_world_graph_recap_projection` | local GM |  — `world_graph_projection.py:147` |

### `world_graph_retrieval.py` (8)

| Method | Mounted path | Handler | Guard found | Notes |
|---|---|---|---|---|
| `POST` | `/api/live/world-graph/retrieval/search` | `post_world_graph_retrieval_search` | local GM |  — `world_graph_retrieval.py:115` |
| `POST` | `/api/live/world-graph/retrieval/object` | `post_world_graph_retrieval_object` | local GM |  — `world_graph_retrieval.py:136` |
| `POST` | `/api/live/world-graph/retrieval/complete-object` | `post_world_graph_complete_object` | local GM |  — `world_graph_retrieval.py:157` |
| `POST` | `/api/live/world-graph/retrieval/neighborhood` | `post_world_graph_retrieval_neighborhood` | local GM |  — `world_graph_retrieval.py:180` |
| `POST` | `/api/live/world-graph/retrieval/evidence` | `post_world_graph_retrieval_evidence` | local GM |  — `world_graph_retrieval.py:201` |
| `POST` | `/api/live/world-graph/retrieval/source-anchor/read` | `post_world_graph_retrieval_source_anchor_read` | local GM |  — `world_graph_retrieval.py:222` |
| `POST` | `/api/live/world-graph/retrieval/recap-context/v2/index` | `post_recap_context_index_v2` | local GM |  — `world_graph_retrieval.py:243` |
| `POST` | `/api/live/world-graph/retrieval/recap-context/v2/read` | `post_recap_context_read_v2` | local GM |  — `world_graph_retrieval.py:260` |

**Explicit declarations:** 235. **Top-level routers:** 26; Agent nested under `/api/live`; **health:** 1; **retired 410 declarations:** 17.
