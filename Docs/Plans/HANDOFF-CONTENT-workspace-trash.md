# CONTENT: recoverable workspace deletion

Status: MERGED; runtime delivered, final rendered acceptance continues in HANDOFF-CONTENT-trash-navigation.md. PR1445 merged39c6cd833d5cfc21801eb46033dfbaddda92a9ed after Architecture Cycle2 PASS on a960daaf3e52a527b3a88b643dedf7b80061a7e9. Source leases below are released to the named successor. Operator requested audit, plan, implementation and a PR for ARCHITECTURE review. PRIME owns this serial slice on branch codex/workspace-trash, base18bdd2e3a1282e02d678048b6ab2b5893aecc2e1, existing buddy-context-loop checkout. One implementation PR. No serving data mutation or runtime delivery before review. Storage and UI writers share this branch with disjoint leases; PRIME alone commits.

## Plan and safety contract

1. Audit surface storage and references. Build is registered worldbuilding source content; Plan/Runbook are application Content work objects and immutable revisions; Play is a separately pinned Run with progress, notes, content editions and proposals. Ingest has review/publication evidence, media has independently retained shared assets, graph has separately owned publication. They are not cascaded children of the document.
2. Implement Move to Trash and Restore for Build documents, World Plans and World Play sessions. Reuse existing discarded/active document status; add durable reversible Play lifecycle. No physical deletes, file unlink, media/CDN removal, graph retraction, history erasure or cascade. Trash hides objects from normal inventory and prevents new writing/playing/agent actions against trashed targets; existing pinned session reads and source/evidence history survive a trashed Plan. Trash never means deletion of a single scene. Explicit selected session identity/title must be shown.
3. World-scoped authenticated endpoints verify exact owner and expected revision. Serialize lifecycle against existing writer locks/CAS. A stale tab/pending save must not resurrect or silently overwrite Trash. Restore is explicit and recoverable after reload. Clearing a selected trashed session pointer must be atomic and must not select another session.
4. Shared small surface control opens a current-World Trash inventory with Restore and per-object Move to Trash, clear dependency copy and named confirmation. Actions disabled while pending/unsaved/conflicted; UI fences target changes and retains any recovery drafts under their original identities; navigating away only after confirmed success must not resurrect them. No hidden deletion of unsaved work. Surface navbar placement follows established controls.
5. Boundary tests cover stale revision, owner/auth isolation, autosave race, active selection, historical pinned reads, restore after reload, unchanged shared media/graph and no cascade. Mounted UI and production build. Submit exact-head PR to existing ARCHITECTURE chat. No generation/provider call needed.

## Leases

Storage worker: src/application_state/play/**, one migration successor0038, apps/live_control_server/services/workspace_document_registry.py and play_run_registry.py and new workspace_lifecycle.py, apps/live_control_server/routes/workspace_documents.py and play_runs.py and new lifecycle route if needed; backend auth classifier/main router registration only if required; owning Python tests. agent_play_surface_context.py and Play-targeted agent turn/proposal reservation admission may gain the narrow Run lifecycle guard needed to refuse new dispatch; no broad database triggers. Existing content service/repository only for narrowly required active/trashed guards. Return shared auth contract for UI adoption. Do not edit UI, docs, runtime or commits.

PRIME: this handoff; apps/live-control-ui/src/api/liveApi.ts and types, shared workspace Trash control/client and mounted tests, BuildSurfaceContext/PlanSurfacePage/PlaySurfacePage/PlaySurfaceContext and owning controller integration as required. No changes to Markdown/media grammar or scene structure. Inspect backend diff cumulatively before commit.

## Audit boundaries deferred

Ingest run/source retention, media asset deletion/purge, graph retraction and whole-World deletion need their own dependency semantics. This slice makes the three requested document/session examples recoverably deletable and records these boundaries rather than treating every stored record as one kind of document.

## Pinned API

GET /api/live/world-workspace/trash?world_id returns {world_id, items:[{kind:document|session,id,title,surface:build|plan|play,revision,status:active|trashed,updated_at,content_revision?}]}. POST /api/live/world-workspace/documents/{id}/trash|restore and /sessions/{id}/trash|restore?world_id require expected_revision; sessions additionally require expected_content_revision (0 for original pin). Run and edition heads are checked under the same Run lock. All routes use existing native GM auth/CSRF. UI uses authenticatedApiFetch with the explicit world-workspace classifier.

## Surface audit

| Surface | Stored authority and relationships | Deletion semantics in this slice |
| --- | --- | --- |
| Index / World selection | World container and navigation into owned inventories | No document owns the World; no World cascade. |
| Build | Registered worldbuilding source, retained Markdown file, revision snapshots, extraction source artifacts and published graph evidence | Reuse discarded state; active list excludes it; exact revision CAS; retain files/snapshots/media/evidence. Restore explicit. |
| Plan | PostgreSQL Content object, working copy and immutable revisions; Play pins an exact revision | Reuse discarded state; hide active inventory and refuse further authoring/new session creation; preserve committed revision reads used by existing sessions. |
| Play | PostgreSQL Run, immutable source pin, content editions, scene progress/notes and agent history/proposals | New reversible Run lifecycle; hide normal session inventory, block new writes/agent dispatch, clear only matching active pointer. Restore exact original content/notes under a new Run revision. |
| Ingest | External/authored source and extraction attempt with candidate review/publication evidence | Removing an attempt is not deleting its source or retracting graph facts; requires a separate retention/retraction design. No cascade from Build Trash. |
| Image Studio / library | Independently retained asset referenced by multiple documents/session revisions and possibly public CDN | Document Trash leaves the asset retained. Asset Trash and permanent CDN purge require reference/visibility policy; not conflated with removing an image occurrence in Markdown. |
| Combat Tracker | Separate tracker artifact/encounter state and source-linked statblocks | No workspace document ownership. No inherited document Trash or deletion of referenced statblocks/played combat. |
| Agent / graph overlays | Durable contextual receipts, source citations and independently published nodes/edges | Preserve historical receipts and published facts. New dispatch cannot use trashed authoring targets; history remains evidence. |

First delivery deliberately has no automatic expiry, empty-Trash or permanent-delete endpoint. Storage reclamation needs a separate explicit operation and reference policy. Trash is a user-visible reversible lifecycle, not an assertion that retained bytes or public CDN data were erased.

## Pre-review evidence and delivery gate

- Cumulative focused backend suite: 82 passed (Play content/editions, saved Agent context, authenticated content API, and four new actual lifecycle API tests), disposable PostgreSQL only.
- Actual routes cover auth refusal, foreign-World 404, stale document CAS409, strict bool422, Build Trash/Restore with exact CRLF/source bytes and independent media sentinel retained, Plan Trash with pinned Play history retained, and session dual-revision requirement.
- Storage regressions cover stale Run/edition heads, foreign World nonmutation, matching-pointer clear with no reselection, unrelated active pointer retention, post-Trash progress/selection/content refusal, history/command replay, explicit restore, and concurrent content-commit-vs-Trash with exactly one successful mutation.
- Frontend: 56 shared/Build/Play tests passed, plus the targeted mounted Plan dirty-delete guard passed. Production TypeScript/Vite build passes (existing chunk-size warning). Existing legacy Plan suite is not claimed green.
- Additional World contracts: 25 passed; one unchanged historical migration test fails while seeding schema0006 with modern Content code that inserts work_revision.world_id (column absent at0006). The test and failing insertion path match the fetched base; this slice does not repair that older fixture.
- New Python lifecycle files pass Ruff; cumulative diff whitespace checked.

No serving database migration, service restart, actual user document Trash operation or5202 frontend adoption has run. ARCHITECTURE must review the exact cumulative head before merge/delivery. Rendered5202 deletion/restore acceptance remains a post-review delivery gate. Existing operator examples are targets for that acceptance, not permission to physically purge storage. No generation/provider call is needed.

### Architecture Cycle1 correction

Cycle1 held head837ef1db69facec9d9ff0e81f37fe86230b9b195 for a same-ID stale confirmation: rerendering with a newer object/Run/edition revision silently retargeted the open modal. Confirmation now captures a copy of the displayed target and exact World/kind/ID/surface/revision/content-revision identity when opened. A changed identity immediately removes the confirmation, invalidates pending callbacks, and requires a fresh confirmation; dispatch checks the captured identity against the current host. Four added mounted cases cover document revision, session revision, content revision and a delayed delete response after a same-ID revision change. Shared lifecycle18/18 pass; production build passes. Exact successor head requires Architecture re-review before delivery.

### Delivery facts learned after merge

Serving API was backed up and migrated0037->0038; prior rows normalized for the new active default remain equal. Existing retained HTTP bodies, real Edge data and media library were unchanged by upgrade. Reviewed UI index915b0c2326a6849406556b274e12ed0babb8b0844b8ec854a46c234c18869a02 delivered. All three operator examples were moved to Trash through real5202 controls, restored through World Trash, and exact content/notes/history/media verified. Plan deletion did not cascade into its playable session. Actual reopening found an unchanged browser recovery cache reopening a deleted Plan as a conflict. Successor fixes that cache retirement and the operator's new request for primary-navbar Trash placement before claiming complete rendered delivery. No purge/provider call occurred.
