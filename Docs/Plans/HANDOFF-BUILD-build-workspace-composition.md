---

pr_body_template: |

## Handoff pointer

* Conversation: `Build Workspace Composition Recovery`
* Flow / agent: `BUILD`
* Direction: DESIGN → CODE
* Handoff: `Docs/Plans/HANDOFF-BUILD-build-workspace-composition.md`
* PR / branch: {{TODO: optional URL or branch; PR number is transport metadata only}}

## Verification pointer

* Base/head: {{TODO}}
* Changed paths: {{TODO}}
* Verification: {{TODO: exact commands/results and manual proof}}

The checked-in handoff, cumulative diff, nano commits, and independently rerun
verification are the review contract. The PR description is transport metadata only.
Document sync is separate from implementation review.
-----------------------------------------------------

# HANDOFF — Build workspace composition is real on `/build`

**Created:** 2026-08-04.
**Status:** ACTIVE — dispatch exactly one implementation capability.
**Canonical handoff path:** `Docs/Plans/HANDOFF-BUILD-build-workspace-composition.md`
**Conversation name:** `Build Workspace Composition Recovery`
**Flow / agent:** `BUILD`
**Handoff direction:** `DESIGN → CODE`
**Design agent:** DungeonBuddy design agent — `Build Workspace Composition Recovery`
**Code agent:** BUILD code agent — use the same conversation name
**PR title:** `BUILD: land Build workspace composition`
**Repository:** `Drakosfire/DungeonMindBuddy`
**Design-time base:** `b6d1df07fae7b28760994509dcf2ae9bd8fb74c7` (`main` on 2026-08-04)

> **Dispatch gate:** This slice exists because operator dogfood contradicted the source-level claim that Build is already a composed surface. Do not begin by adding more leaf capability code. First reproduce the real `/build` route from a clean checkout and production build. If current `main` already satisfies every live acceptance step, stop: the defect is deployment, stale assets, or operator entry-path mismatch, and this implementation mission is invalid.
>
> This checked-in handoff is complete authority for the slice. Do not compress it into the PR body. Keep implementation in nano commits. Do not cherry-pick or revive PR #497 wholesale.

## Shared vocabulary

| Term                       | Meaning in this slice                                                                                                                                                         |
| -------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Build workspace**        | One admitted worldbuilding document rendered through the shared Markdown Canvas and app-owned Nav, Tool, Edit, Agent, and Projection hosts.                                   |
| **Admitted document**      | The exact route `documentId` accepted by `MarkdownCanvasSession`, with a matching `session.record`; loading, conflict, rejected-kind, and load-error states are not admitted. |
| **Composition**            | The real `App` route tree and visible browser result, not a test harness that manually mounts selected providers or hosts.                                                    |
| **Active lease**           | The exact Build `SurfaceInteractionPublication.identity` bound to the admitted document.                                                                                      |
| **Singular host**          | Exactly one app-owned Tool Host, Edit Host, Agent chrome, and Projection Host. Build publishes into them; Build does not mount private copies.                                |
| **Operator-visible proof** | A clean built application in which the GM can click Build and immediately author in the Markdown Canvas, without constructing a `documentId` URL or filling a metadata setup form first. |

## Agent flow and nano-commit contract

Use `BUILD` throughout. Keep one discrete story per commit. Expected shape:

1. `test(build): reproduce missing app-route workspace composition`
2. `fix(build): bind admitted canvas to shared Build hosts`
3. `test(build): prove save reload and stale-lease cleanup`

The exact commit count may differ, but unrelated cleanup, style redesign, graph behavior changes, and documentation sync must not be bundled.

---

## §1 Mission and merge-ready invariant

### Mission

An operator can click Build (bare `/build`) and reach one visible shared Build workspace with an editable Markdown Canvas. When no safe campaign context exists (no known `?campaign=` and no last Build campaign), the operator chooses a campaign once; then a draft worldbuilding document is established with sensible defaults and the Canvas is admitted. Native exact World Graph search/inspection remains usable without leaving Build.

### Merge-ready invariant

One exact `/build` route lease and one exact admitted workspace document determine one `MarkdownCanvasSession`, one Canvas work-object identity, and one app-owned Nav/Tool/Edit/Agent/Projection composition; the Canvas remains sole document authority, every edit command revalidates the current document target, World Graph tools remain read-only and exact-lens, graph failure cannot hide or mutate the document, and document/route/lease replacement revokes all stale inventory, callbacks, context, and open projections before the replacement becomes usable.

### Pre-dispatch critique

| Question                                                | Answer                                                                                                                                                                                          |
| ------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Can one invariant govern every claimed observable path? | **Yes.** Every path asks whether one admitted Build document is represented by one truthful app-level workspace composition.                                                                    |
| Most likely falsifying sequence                         | Leaf components and isolated tests pass → `/build` is opened through the real `App` route or production bundle → Canvas or shared hosts are absent, unstyled, empty, or bound to stale context. |
| Would the §7 evidence detect that failure?              | **Yes, if followed.** The required owning test renders `App`, not a hand-built provider tree, and the manual proof uses `npm run build` plus the real served route.                             |
| Easiest owning boundary to under-test                   | `App` route composition plus CSS/import visibility. PR #506’s strongest Build test manually mounted providers and hosts, so it could not prove the shipped route.                               |
| Fact that forces stop or split                          | A clean production build at current `main` already passes the complete live proof; or repair requires changing shared host semantics for Plan/Ingest rather than Build publication/composition. |

---

## §2 Context, authority, and boundaries

### Current contradiction to resolve

Current `main` contains source-level pieces that imply a Build workspace:

* `BuildSurfacePage` mounts `AppChrome`, `MarkdownCanvasSessionProvider`, `BuildReferenceCapability`, `BuildIngestToolbar`, and `BuildSurfaceShell` for a selected document.
* `BuildSurfaceShell` renders `MarkdownCanvas`.
* `App` mounts the app-level `ToolHost`, Projection Host adapter, and `AgentInteractionChrome`.
* `AppChrome` owns site navigation and the shared `EditHost`.

That is not accepted proof. Operator dogfood found Build unusable as a Markdown/shared-host surface, the current `App.test.tsx` has no `/build` route composition test, and the latest main-tip dogfood record explicitly says Build Markdown/canvas is not ready. This slice closes that source-versus-product gap.

### Authority table

| Field                               | Required content                                                                                                                                                                                                                                                                              |
| ----------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Parent UI architecture              | `Docs/Design/ARCHITECTURE-surface-interaction-layer.md`                                                                                                                                                                                                                                       |
| UI execution plan                   | `Docs/Plans/PLAN-surface-interaction-hoist-build-first.md` — this is a repair/decomposition inside the intended SI-04 Build outcome                                                                                                                                                           |
| Canvas authority                    | `Docs/Design/DESIGN-shared-markdown-canvas-surface-composition.md` and landed `MarkdownCanvasSession` contracts                                                                                                                                                                               |
| Graph boundary                      | `Docs/Design/ARCHITECTURE-campaign-supergraph.md` — Build consumes projections; this PR does not write graph state                                                                                                                                                                            |
| Dispatch/review process             | `.cursor/skills/external-agent-pr-loop/templates/HANDOFF.template.md`, `Docs/Plans/JUMPSTART-docs-relevance-first.md`, repository rules                                                                                                                                                       |
| Base revision                       | `b6d1df07fae7b28760994509dcf2ae9bd8fb74c7`; re-anchor immediately before implementation                                                                                                                                                                                                       |
| Predecessor contracts               | MC-01 / PR #426 Canvas; R10a / PR #441 app Projection Host; PR #501 shared Tool Host; PR #503 shared Edit Host; PR #506 native Build World Graph search/inspect                                                                                                                               |
| Exact input consumed                | `?documentId=<opaque UUID>` → exact workspace snapshot → admitted `MarkdownCanvasSession`; Build World Graph lens from the accepted document campaign and optional exact revision pin                                                                                                         |
| Historical donor only               | Draft PR #497, `port/mc02b-build-graph-refs-on-main`, is 107 commits behind current main and bundles navbar actions, local checkpointing, extraction UI, old Plan resolver composition, and docs. Compare for lost intent only; do not use as implementation base or bulk cherry-pick source. |
| Named successor                     | `BUILD: insert exact World Graph reference into Canvas` — durable reference insertion, save, reload, and chip reopen using the published Threat proof                                                                                                                                         |
| What remains false after this slice | No graph-reference insertion; no graph writes/node creation; no Build Ask/Hermes plugin; no document library/picker; no Threat-card polish; no latency repair; no extraction-inspector migration                                                                                              |

### Read authoritative inputs in this order

1. `Docs/Design/ARCHITECTURE-surface-interaction-layer.md`
2. `Docs/Plans/PLAN-surface-interaction-hoist-build-first.md`
3. `Docs/Design/DESIGN-shared-markdown-canvas-surface-composition.md`
4. Current `main` implementations of `App`, `AppChrome`, `MarkdownCanvasSession`, `MarkdownCanvas`, shared hosts, and Build surface files
5. PR #506 cumulative diff and tests, specifically the manually composed E5/E11 harness
6. PR #497 only as historical evidence of intended visible composition; never as current authority

If the base moves, inspect all changes touching `App`, `AppChrome`, `MarkdownCanvas*`, `AgentInteractionProvider`, Tool/Edit/Projection hosts, or `buildSurface/**`. Stop if another active branch now owns the same capability.

---

## §3 Observable paths and adversarial sequences

### Observable-path inventory

| Path                                         | Current observed/claimed behavior                                                        | Required behavior                                                                                                                                                                                                      | Owning boundary                           |
| -------------------------------------------- | ---------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------- |
| `/build` with no `documentId`                | Source code presents a creation form; operator did not receive a usable shared workspace | Auto-create one draft worldbuilding source with defaults (title “Untitled worldbuilding source”); navigate once to its exact `documentId`; render the Markdown Canvas and shared hosts. Metadata is not the primary surface (defaults + Canvas/Agent presentation). Opening/error/retry states stay under Nav/Agent. | `App` + `BuildSurfacePage`                |
| `/build?documentId=<valid>` initial load     | Source claims Canvas/session composition; operator found no usable Canvas/shared layer   | Visible loading state, then one Markdown Canvas, one Nav, one Agent bar, one native Tool launcher, one native Edit launcher/host, and one shared Projection Host                                                       | `App` route composition                   |
| Admitted document, graph loading/unavailable | Build graph capability may be unavailable                                                | Canvas, Nav, Edit, and Agent remain usable; Find Existing is loading/disabled/absent truthfully; no fallback graph or arbitrary corpus search                                                                          | Build publication + shared hosts          |
| Admitted document, graph ready               | PR #506 capability exists                                                                | Tools → Find existing object → search → exact View → shared projection works through real `App` route                                                                                                                  | Build publication + Tool/Projection hosts |
| Plain Markdown edit                          | Canvas is source authority but Edit Host currently has no Build edit inventory           | User edit marks the current session dirty; Edit Host exposes document-bound Save; Save invokes the existing Canvas save/CAS path for the exact work object                                                             | Canvas session + Build edit publication   |
| Hard reload after Save                       | Current Canvas contracts should reload                                                   | Same exact document content/revision reappears; no new persistence format; host inventory rebinds once                                                                                                                 | Workspace snapshot + `App` composition    |
| Rejected/mismatched document                 | Leaf code fail-closes                                                                    | No stale prior Canvas, UUID, graph tool, edit command, agent context, or projection survives; truthful error/conflict UI remains under Nav/Agent shell                                                                 | Canvas admission + lease cleanup          |
| Document A → document B                      | Existing tests cover parts in isolation                                                  | A’s open Tool/Edit/projection/callbacks become unusable before B is ready; B gets a new exact lease and work object                                                                                                    | Provider + Build publication              |
| Build → Plan/Ingest → Build                  | App hosts are shared                                                                     | Exactly one host of each kind; no Build inventory or context leaks to another surface; returning rehydrates only the current Build document                                                                            | `App` + lease cleanup                     |
| Production build/preview                     | Not currently proven                                                                     | The same composition visible in tests is visible from built assets, not only Vite test/JSDOM or a stale development server                                                                                             | Build artifact + browser manual proof     |

### Ordered adversarial sequences

| Sequence                                                                                                                                      | Required safe outcome                                                                                                                     | Owning proof |
| --------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- | ------------ |
| Render leaf Build components manually → pass → render real `App` at `/build?...`                                                              | Real `App` must expose the same workspace; manual harness-only success is insufficient                                                    | E1           |
| Ready document A → open Find Existing and a graph object → replace URL with document B while graph request/relationship resolution is pending | A’s Tool/Edit/projection close or revoke; delayed A completion is a no-op; B remains clean until its own publication is ready             | E6           |
| Ready dirty document A → graph endpoint fails/retries                                                                                         | Canvas remains visible and dirty; Save remains targeted to A; graph failure does not clear editor content or change document authority    | E4           |
| Ready document A → retain Save callback → switch to document B → invoke retained A command                                                    | No save/prepare/commit occurs for either document through the stale command; current Edit Host re-resolves by command ID and exact target | E3/E6        |
| Bare `/build` under React StrictMode → auto-create / Back after admit                         | At most one document is created; transient entry URLs use replaceState so Back leaves Build without replaying create; Canvas becomes editable | E2           |
| Build → Plan → Build repeatedly                                                                                                               | One Tool Host, one Edit Host, one Agent chrome, one Projection Host; no duplicate DOM or resurrected Build drawer state                   | E7           |
| Save document → `npm run build` → serve `npm run preview` → hard reload exact URL                                                             | Saved body is present and host composition is still visible                                                                               | E8/E10       |

---

## §4 Files in scope (allowlist)

Every changed path must be listed here or fit the bounded test-only exception.

### Handoff authority

| Action | Path                                                      | Purpose                                                                            |
| ------ | --------------------------------------------------------- | ---------------------------------------------------------------------------------- |
| Create | `Docs/Plans/HANDOFF-BUILD-build-workspace-composition.md` | Complete design/verification authority; code agent must not rewrite or compress it |

### Production paths

| Action                                | Path                                                                                         | Purpose                                                                                                                        |
| ------------------------------------- | -------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| Modify if required                    | `apps/live-control-ui/src/App.tsx`                                                           | Repair real route/host composition only if the App-level reproduction proves mount order or route ownership is wrong           |
| Modify                                | `apps/live-control-ui/src/buildSurface/BuildSurfacePage.tsx`                                 | Make no-document entry and admitted-document transition land on the real shared workspace without duplicate create/navigation  |
| Create                                | `apps/live-control-ui/src/buildSurface/buildBareEntryCampaign.ts`                            | Resolve bare-/build campaign from known route or last Build campaign; unknown route campaigns fail closed; no silent dogfood default; keyed auto-create identity |
| Modify                                | `apps/live-control-ui/src/buildSurface/BuildSurfaceShell.tsx`                                | Compose the admitted Canvas and publish truthful Build context; no private host ownership                                      |
| Modify                                | `apps/live-control-ui/src/buildSurface/buildMarkdownCanvasAdapter.tsx`                       | Build-owned Canvas slots and replacement of duplicate footer Save when shared Edit Save is active                              |
| Modify                                | `apps/live-control-ui/src/buildSurface/buildDocumentCommands.ts`                             | Define stable Build document command IDs/conflicts; no new persistence contract                                                |
| Modify                                | `apps/live-control-ui/src/buildSurface/reference/BuildReferenceCapability.tsx`               | Bind native Build publication to current Canvas session/edit actions and revoke on non-admitted states                         |
| Modify                                | `apps/live-control-ui/src/buildSurface/reference/buildBuildSurfaceInteractionPublication.ts` | Publish exact Canvas identity, Find Existing tool, document-bound Save command, and existing projections under one Build lease |
| Modify or Create one                  | `apps/live-control-ui/src/buildSurface/buildSurface.css`                                     | Minimal Build composition/layout styling using existing tokens and TipTap/graph-reference visual grammar                       |
| Modify if a global import is required | `apps/live-control-ui/src/styles.css`                                                        | Only the minimum shared-safe import/layout rule needed to make Build visible; no palette or host redesign                      |

### Owning tests

| Action | Path                                                                                              | Purpose                                                                                                               |
| ------ | ------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------- |
| Modify | `apps/live-control-ui/src/App.test.tsx`                                                           | Mandatory real-App `/build` route proof: Canvas + Nav + Tool + Edit + Agent + Projection and singular-host assertions |
| Modify | `apps/live-control-ui/src/buildSurface/BuildSurfacePage.test.tsx`                                 | Entry/create/admission states and transition to exact document                                                        |
| Modify | `apps/live-control-ui/src/buildSurface/BuildSurfaceShell.test.tsx`                                | Canvas/context behavior across accepted, loading, error, conflict, and unmount states                                 |
| Modify | `apps/live-control-ui/src/buildSurface/reference/buildBuildSurfaceInteractionPublication.test.ts` | Exact Canvas/edit/tool inventory and fail-closed publication states                                                   |
| Modify | `apps/live-control-ui/src/buildSurface/reference/BuildReferenceCapability.test.tsx`               | Exact save target, lease replacement, graph-unavailable independence, stale callback rejection                        |

### Bounded discovery exception

```text
Directory: apps/live-control-ui/src/buildSurface/
Maximum additional paths: 2
Allowed path kinds: *.test.ts or *.test.tsx only
Decision rule: add only when the existing App/Build tests cannot isolate an owning-boundary regression without making one test file incoherent; record exact path and reason in the handback.
```

No production path qualifies under bounded discovery.

---

## §5 Files and capabilities explicitly out of scope

| Path, layer, or capability                                                          | Why excluded                                                                                                                            |
| ----------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| `apps/live-control-ui/src/surfaceInteraction/toolHost/**` production                | Shared Tool Host is a landed predecessor. A shared-host semantic defect is a stop/split, not a Build-local repair.                      |
| `apps/live-control-ui/src/surfaceInteraction/editHost/**` production                | Same: Build must publish valid commands into the host, not fork or redesign it.                                                         |
| `apps/live-control-ui/src/surfaceInteraction/projection/**` production              | PR #506 already hardened projection behavior. Change only under a separately reviewed stop report.                                      |
| `apps/live-control-ui/src/agentInteraction/AgentInteractionProvider.tsx` production | Provider lease semantics are predecessor authority; do not reopen them to make Build render.                                            |
| `apps/live-control-ui/src/agentInteraction/AgentInteractionChrome.tsx` production   | Build should publish context; do not create a Build-specific Agent bar or enable Ask here.                                              |
| `apps/live-control-ui/src/chrome/AppChrome.tsx` production                          | Shared Nav/Edit host owner. Build composition should work through existing public seams. If AppChrome itself is broken, stop and split. |
| `apps/live-control-ui/src/markdownCanvas/**` production                             | Canvas is landed independent authority. This slice consumes it; do not move Build policy into Canvas.                                   |
| `apps/live-control-ui/src/planSurface/**` production                                | Plan is not a Build implementation dependency or durable API donor.                                                                     |
| PR #497 bulk cherry-pick / old `BuildGraphReferenceShell`                           | Stale, 107 commits behind, and built on old Plan resolver/host ownership; use only as historical comparison.                            |
| Graph-reference insertion / TipTap graph node persistence                           | Named immediate successor. This PR proves the workspace that insertion will target.                                                     |
| Graph writes, Threat publication, statblock binding changes                         | Separate governed write/mechanics lanes. Read-only dogfood only.                                                                        |
| Build document picker/library, recent documents, auto-open preference               | Separate product capability. First-time bare `/build` may show a campaign pick when no safe context exists; document library/recent-doc UX is still out of scope. |
| Local “Save surface state” checkpoint                                               | Separate persisted UI-state contract bundled in PR #497; explicitly excluded.                                                           |
| Navbar graph status/actions redesign                                                | Presentation/polish, not composition truth.                                                                                             |
| Extraction inspector migration into Tool Host                                       | Separate Build tool capability. Keep current extraction behavior unchanged.                                                             |
| Threat glance/Hermes card polish and hydration latency                              | MAGIC-D3 successor work; this slice only uses an existing Threat as a read proof.                                                       |
| Documentation tracker/roadmap status updates                                        | Post-merge document sync, not implementation repair.                                                                                    |

---

## §6 Implementation contract and matrices

### Behavioral contract

```text
Input:
  /build route
  optional exact workspace documentId
  exact workspace snapshot and MarkdownCanvasSession admission result
  current Build World Graph lens/projection state

Output:
  no documentId + no safe known campaign:
    campaign picker under Nav/Agent; no durable create until a known campaign is chosen
  no documentId + known campaign (route or last Build):
    auto-create one draft worldbuilding source with defaults; replaceState once to exact document URL;
    opening/error/retry under Nav/Agent (metadata setup form is not the primary Build experience)
  admitted document:
    one visible Markdown Canvas and one lease-bound Build publication consumed by
    app-owned Tool, Edit, Agent, and Projection hosts

Invariant:
  §1 merge-ready invariant, unchanged

Failure behavior:
  document load/rejection/conflict -> truthful Canvas state; empty Build tool/edit inventory;
      no prior document/context/projection leakage
  graph loading/unavailable/error -> Canvas/Nav/Edit/Agent remain; graph tool is truthful and read-only;
      no corpus/latest/head fallback
  stale command/callback -> no-op
  production asset/import failure -> merge blocked; test-only composition is not accepted

Replay / idempotency:
  same route + same document -> one lease, one Canvas, one host inventory
  changed document -> old lease revoked before new inventory is usable
  StrictMode remount -> no duplicate create, publication, host, or save
  hard reload -> existing document/session reconstruction; no new client persistence format

Trust boundary:
  Verifies exact route documentId, accepted session.record identity, command target,
  current lease, current lens/load key, and current save availability.
  Trusts existing workspace snapshot/CAS and World Graph projection contracts after
  their owning adapters validate them.
```

### Commit point

This PR introduces no new durable commit model. The only durable operation exercised is the existing `MarkdownCanvasSession.saveMarkdown()` prepare/commit path.

* **Before commit:** local editor content and dirty state belong to the exact Canvas session.
* **Commit point:** existing workspace Markdown commit succeeds for the exact document/revision/digest contract.
* **After commit:** Canvas records the existing receipt/revision state and becomes clean.
* **Post-commit read failure:** preserve truthful committed receipt/state and allow exact reload/retry; never synthesize a new result.

### A. State and fallback matrix

| Observable path | Loading / initializing                           | Exact success                           | Ordinary miss                       | Dependency unavailable                    | Integrity / contract failure           | Stale / superseded                           | Retry / replay                        |
| --------------- | ------------------------------------------------ | --------------------------------------- | ----------------------------------- | ----------------------------------------- | -------------------------------------- | -------------------------------------------- | ------------------------------------- |
| Bare `/build`   | Shared Nav/Agent + opening draft state           | Auto-create → navigate → Canvas         | N/A (no form miss)                  | Create error + Retry; no fake Canvas      | Fail closed                            | Ignore late create result after route leaves | Explicit retry; no duplicate create   |
| Canvas          | Visible loading state                            | Exact admitted document/editor          | Not applicable for known exact ID   | Snapshot unavailable → load error         | Conflict/rejected kind shown           | Prior Canvas unmounted and authority cleared | Existing reload/discard controls only |
| Edit Host       | Hidden until admitted Canvas/work object         | Exact document Save command             | No commands                         | Graph unavailability does not affect it   | Disabled with exact Canvas reason      | Old target command no-op                     | Recompute from current session        |
| Tool Host       | Hidden/disabled until accepted lens publication  | Find Existing opens                     | Zero search results explicit        | Graph unavailable explicit                | Integrity error; no fallback           | Old tool/projection no-op                    | Retry current exact lens only         |
| Agent chrome    | Visible with Build route context                 | Build + exact document summary          | No document → neutral Build context | Ask remains honestly unavailable on Build | No UUID/path/hash from rejected record | Prior document context cleared               | Rehydrate current Build context       |
| Projection      | Closed while no valid selection                  | Exact selected graph ID                 | Miss/unresolved explicit            | Error/unavailable explicit                | Fail closed                            | Clear/no-op across lease change              | Retry exact lens/revision             |

No fallback may use latest ingest, preview source, arbitrary Markdown, corpus index, labels, or current head in place of an exact requested revision.

### B. Identity matrix

| Situation           | Required rule                                                            | Ambiguity behavior                                   | Fallback permitted? |
| ------------------- | ------------------------------------------------------------------------ | ---------------------------------------------------- | ------------------- |
| Workspace document  | Exact opaque route UUID must equal admitted `session.record.document_id` | Mismatch → no Canvas publication/tool/edit inventory | No                  |
| Build surface lease | `surfaceId=build` plus exact document instance identity                  | Identity change revokes prior host state             | No                  |
| Canvas work object  | `{ kind: "document", id: admittedDocumentId }`                           | Missing/mismatch → no edit commands                  | No                  |
| Edit command        | Re-resolve by stable command ID and exact current target at click time   | Missing/replaced/disabled → no-op                    | No                  |
| World Graph object  | Exact selected node ID from the current verified projection              | Duplicate labels stay separate; no auto-pick         | No                  |
| Graph revision      | Head only when response verifies head; pinned exact ID remains exact     | Mismatch/integrity failure → error                   | No                  |
| Display label       | Presentation only                                                        | Never substitutes for durable identity               | No                  |

### C. Persistence and replay matrix

| Operation            | Durable representation                              | Round-trip guarantee                               | Duplicate/replay behavior                          | Compatibility / migration                 | Rollback / reversion                      |
| -------------------- | --------------------------------------------------- | -------------------------------------------------- | -------------------------------------------------- | ----------------------------------------- | ----------------------------------------- |
| Plain Markdown save  | Existing workspace document revision/content digest | Edited body survives hard reload of exact document | Existing CAS/idempotency rules; stale target no-op | No new format or migration                | Existing conflict/reload/discard behavior |
| UI/host state        | Transient current provider/route state              | No new persistence claimed                         | Remount produces one current lease                 | Existing Agent pane persistence untouched | Route/document switch clears/rebinds      |
| Graph search/inspect | No document or graph write                          | No persistent mutation                             | Repeat read is observational                       | Existing projection contracts             | Close/retry only                          |

### D. Predecessor-to-consumer mapping

| Predecessor field/outcome       | Real shape                                                   | Consumer behavior                          | Transformation                                      | Owning proof |
| ------------------------------- | ------------------------------------------------------------ | ------------------------------------------ | --------------------------------------------------- | ------------ |
| `documentId` URL selection      | opaque UUID or null                                          | Select/create exact Build work object      | No slug/path derivation                             | E1/E2        |
| `MarkdownCanvasSession.phase`   | unloaded/loading/ready-like/load_error/conflict states       | Gate Canvas publication and edit inventory | Empty inventory outside admitted states             | E3/E4        |
| `session.record.document_id`    | exact workspace UUID                                         | Canvas work object + lease instance        | Must equal route ID                                 | E3/E6        |
| `session.record.campaign_id`    | exact campaign scope                                         | Build graph lens                           | Passed to existing resolver; no Plan session policy | E4/E5        |
| `session.saveDisabled`          | Canvas-owned boolean                                         | Save command availability                  | No independent Build reconstruction                 | E3           |
| `session.saveMarkdown()`        | existing async Canvas command                                | Shared Edit command invoke                 | Guarded target re-resolution                        | E3           |
| `BuildReferenceContextBinding`  | exact lens/projection/items/view callback                    | Find Existing tool + projection bindings   | Existing PR #506 mapping retained                   | E5/E6        |
| `SurfaceInteractionPublication` | one identity/canvas/tools/edit/projections/bindings envelope | Shared hosts render Build capabilities     | Add Build Save; no new manifest type                | E1/E3/E5     |
| `activeSurfaceContext`          | pointer-only surface/document summary                        | Agent chrome labels current Build context  | Neutral when no admitted record                     | E1/E4/E7     |

---

## §7 Evidence required to merge

Every result must state provenance: author-local, independently rerun local, CI, or operator manual.

| ID  | Guarantee                                                             | Owning boundary                        | Evidence class          | Required proof                                                                                                                                               | Merge-blocking result                                                                                                 |
| --- | --------------------------------------------------------------------- | -------------------------------------- | ----------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------- |
| E0  | The defect exists on the implementation base, or the slice is invalid | Built app + browser                    | baseline/manual         | Clean checkout, build/serve, open exact `/build` paths, capture what is absent                                                                               | If all acceptance steps already pass, stop and report deployment/stale-bundle mismatch; do not create a code PR       |
| E1  | Real `App` route renders one complete admitted Build composition      | `App`                                  | integration/adversarial | `App.test.tsx` covers bare `/build` (campaign pick when needed → Canvas) and `/build?documentId=...`; asserts Canvas, Nav, Tool, Edit, Agent and exactly one Projection Host owner | Any host proven only by manually mounting it outside `App`; bare `/build` that stays on a metadata form              |
| E2  | Bare `/build` auto-create is truthful and idempotent                  | `BuildSurfacePage`                     | regression              | Campaign pick / known-campaign auto-create; StrictMode one-create; history Back after admit does not recreate; unknown/blank route campaign fail closed; error/retry/route-away; replaceState for transient entry | Duplicate workspace creation, form-first entry, Back replay create, or unknown campaign durable write                 |
| E3  | Plain Markdown editing and Save use exact Canvas authority            | Canvas + Build publication + Edit Host | integration/adversarial | Edit current body → dirty; Save through Edit Host → existing prepare/commit once; stale retained command after document switch no-ops; reload preserves text | Footer-only Save, wrong-document save, duplicated save path, or independent readiness reconstruction                  |
| E4  | Graph dependency cannot take down or mutate the workspace             | Build publication/App                  | failure injection       | Projection loading/unavailable/error while document admitted; Canvas/Nav/Edit/Agent remain and document snapshot is unchanged                                | Canvas hidden, dirty state reset, or fallback graph/corpus path invoked                                               |
| E5  | Native search/inspect is usable through the real route                | App + Tool/Projection hosts            | integration             | Tools → Find Existing → search fixture/current Threat → exact View → shared projection; one host each                                                        | Leaf-only search test, label substitution, or private Build drawer/container                                          |
| E6  | Document replacement revokes stale capability                         | Provider + Build capability            | adversarial             | A ready/open → B loading/ready while request/command retained; A callbacks no-op and A projection/context disappears                                         | Any stale A save, object open, context, or inventory under B                                                          |
| E7  | Route switching keeps hosts singular and lease-safe                   | `App`                                  | integration             | Build → Plan/Ingest → Build; assert one Tool/Edit/Agent/Projection host and correct active surface inventory                                                 | Duplicate host DOM or resurrected Build state                                                                         |
| E8  | Production package is buildable                                       | package                                | build/typecheck         | `npm run typecheck`; `npm run build`                                                                                                                         | Failure introduced by head                                                                                            |
| E9  | Shared predecessors were not rewritten                                | diff/source guard                      | inspection              | No production changes outside §4; specifically no ToolHost/EditHost/Provider/ProjectionHost/Plan production diff                                             | Any unauthorized shared-host or Plan change                                                                           |
| E10 | A GM can use the real workspace with the published Threat             | built app + real backend               | operator dogfood        | Exact scenario below, captured in PR handback/comment                                                                                                        | Canvas/host missing, Save/reload fails, Threat cannot be searched/inspected, or operator must use a developer harness |

### Required commands

Run from repository root unless stated:

```bash
git fetch origin main
git rev-parse origin/main
git status --short

git diff --check

git diff --name-only <BASE>...HEAD

git diff --stat <BASE>...HEAD -- \
  apps/live-control-ui/src/App.tsx \
  apps/live-control-ui/src/App.test.tsx \
  apps/live-control-ui/src/buildSurface \
  apps/live-control-ui/src/styles.css

cd apps/live-control-ui
npm test -- --run \
  src/App.test.tsx \
  src/buildSurface/BuildSurfacePage.test.tsx \
  src/buildSurface/BuildSurfaceShell.test.tsx \
  src/buildSurface/reference/buildBuildSurfaceInteractionPublication.test.ts \
  src/buildSurface/reference/BuildReferenceCapability.test.tsx \
  src/surfaceInteraction/toolHost \
  src/surfaceInteraction/editHost \
  src/agentInteraction/AgentInteractionProvider.test.tsx \
  src/agentInteraction/AgentInteractionChrome.test.tsx

npm run typecheck
npm run build
```

If `AgentInteractionChrome.test.tsx` does not exist, do not invent it automatically; the App-level proof may own that assertion. Use the bounded test-only exception only when necessary and record the decision.

### Minimal live / dogfood proof

Use a clean `main`-based branch and a production build where possible:

```bash
cd apps/live-control-ui
npm run build
npm run preview -- --host 0.0.0.0
```

Run the live-control backend through the repository’s current canonical startup path.

Smallest realistic scenario:

1. Open `/build` from the command-board navigation (click Build — do not hand-construct a `documentId` URL).
2. Confirm the Markdown Canvas appears for an auto-created “Untitled worldbuilding source” (brief opening state is allowed; a metadata setup form is not).
3. Confirm visible Nav and bottom Agent chrome before and after admission.
4. Confirm the Markdown Canvas/editor is visible and receives keyboard input.
5. Type a unique marker, e.g. `Build composition proof <timestamp>`.
6. Confirm dirty state.
7. Open the shared Edit Host and invoke **Save** there.
8. Hard reload the exact document URL; confirm the marker survives and state is clean.
9. Open the shared Tool Host → **Find existing object**.
10. Search for the real Threat published during MAGIC-D3 (currently named `ANything`) or another exact known published Threat if that fixture has changed.
11. Open the exact result and confirm the shared Projection Host displays that exact graph object. Record node ID and loaded graph revision; do not paste them into product state to make the flow work.
12. Navigate to Plan or Ingest, then return to the Build document. Confirm no duplicate host and no stale open Build projection.

Evidence captured in the handback:

* execution SHA;
* exact document ID (safe identifier only; no corpus body/path dump);
* before/after workspace revision;
* exact Threat node ID and graph revision;
* screenshots or concise observations showing Canvas, Nav, Tool, Edit, Agent, and Projection;
* whether the proof used dev server or built preview;
* exact failure if any.

Do not add a new diagnostics panel or report surface to prove this PR.

### Baseline failure protocol

For any required command failing on base:

1. Run the same command on base and head.
2. Record exact difference.
3. Do not call the gate green.
4. Require an explicit operator waiver if the failure remains part of this acceptance gate.

---

## §8 Required review handback

The code agent/reviewer handback must include:

1. Exact PR URL or branch and head SHA.
2. §1 Mission and merge-ready invariant copied exactly.
3. Finding/reproduction ledger beginning with E0.
4. Nano-commit list and the discrete story for each commit.
5. Base SHA and head SHA.
6. Actual changed paths and focused diff stat.
7. Every §7 command/scenario and exact result.
8. Provenance for every result.
9. Base/head comparison for failures.
10. Operator waivers; `none` when none.
11. Paths outside §4; `none` or stop report.
12. Stop conditions encountered and resolution.
13. Confirmation that PR #497 was not bulk cherry-picked or used as current authority.
14. Confirmation that shared host and Canvas production files outside §4 remain unchanged.
15. Named successor still false: exact World Graph reference insertion/save/reload/reopen.
16. Confirmation that the checked-in handoff was implemented without omitted constraints.

---

## §9 Acceptance rubric

The reviewer accepts only when every item is true:

* [ ] One operator-visible Build workspace capability was delivered, proved by bare-/build E1 and E10 (click Build → choose campaign only when no safe context → Canvas).
* [ ] The real `App` route—not a manually assembled provider harness—renders the complete workspace, proved by E1.
* [ ] Exactly one Nav, Tool, Edit, Agent, and Projection host exists, proved by E1/E7.
* [ ] One admitted document maps to one Canvas and exact work-object identity, proved by E1/E3/E6.
* [ ] Plain Markdown edit → dirty → shared Edit Save → hard reload round-trips through existing Canvas authority, proved by E3/E10.
* [ ] Graph loading/unavailable/error does not hide or mutate Canvas state, proved by E4.
* [ ] Find Existing search/inspect works from the real Build route with exact identity and no fallback, proved by E5/E10.
* [ ] Document and route replacement revoke stale commands, callbacks, context, and projections, proved by E6/E7.
* [ ] No new persisted UI state, schema, reference syntax, graph write, or public host contract was introduced.
* [ ] No production path outside §4 changed, proved by E9.
* [ ] Current package typecheck/build pass, proved by E8.
* [ ] E0 was handled truthfully: code was changed only after the defect reproduced on a clean current base.
* [ ] The named insertion successor remains unimplemented and unclaimed.

---

## Stop conditions

Stop and report rather than expanding if any of these occurs:

1. **Current main already passes E0/E10 completely.** The defect is stale deployment, browser cache, wrong process, or wrong entry path. Propose a deployment/runbook/cache repair; do not write redundant composition code.
2. **Repair requires production changes to ToolHost, EditHost, AgentInteractionProvider, AgentInteractionChrome, ProjectionHost, AppChrome, MarkdownCanvas, or Plan.** Name the shared invariant failure and split for architecture review.
3. **A document library/picker or “last open document” persistence is required beyond auto-create on bare `/build`.** Picker/recent-doc UX is a separate product capability; this slice uses auto-create with defaults for Canvas-first entry.
4. **The implementation starts adding graph-reference insertion or TipTap graph-node serialization.** Stop; that is the named successor.
5. **The implementation starts adding local surface-state checkpointing, navbar status/actions, extraction inspector migration, Threat presentation, or performance work.** Stop for capability split.
6. **A backend, graph, statblock, or workspace schema change appears necessary.** This slice should compose existing contracts only.
7. **PR #497 is proposed as a merge/rebase base or bulk cherry-pick.** Stop. Mine a specific behavior only after mapping it to current contracts and §4.
8. **A new CSS/theme contract is proposed.** Reuse existing tokens and visual grammar; new theming is separate.
9. **The operator proof requires hidden IDs, direct APIs, or hand-edited storage.** The product path is still missing; report the exact owning boundary.

Use this stop-report shape:

```text
Stop condition:
Why the current mission cannot absorb it:
Invariant clause affected:
Required evidence now missing:
New public/durable contract discovered:
Affected observable paths or ownership layers:
Proposed successor slice:
Tracker or authority update needed:
```
