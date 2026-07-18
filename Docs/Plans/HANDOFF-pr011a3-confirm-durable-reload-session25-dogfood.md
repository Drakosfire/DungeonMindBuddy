# HANDOFF — PR011A3 Confirm Prepared Graph Review Proposal into Durable Campaign Memory

**Created:** 2026-07-17, America/Denver
**Status:** ACTIVE — dispatch exactly one implementation capability after the pre-dispatch re-anchor is checked in.
**Canonical handoff path:** `Docs/Plans/HANDOFF-pr011a3-confirm-durable-reload-session25-dogfood.md`
**Pre-dispatch anchor:** `cec9834f8667d2af31447540b5acb9dade0373aa` — merge of GitHub PR #365 / PR011A2
**Implementation base:** `<DOCS_REANCHOR_SHA>` — replace with the immutable SHA that checks in this handoff and the tracker/roadmap changes below.
**Suggested branch:** `agent/pr011a3-confirm-durable-reload`

Do not dispatch while `<DOCS_REANCHOR_SHA>` remains unresolved.

---

## Pre-dispatch repository re-anchor

Before an implementation agent begins, check in this handoff together with the following documentation corrections.

### `Docs/Plans/PR-TRACKER-campaign-supergraph.md`

Update the active sequence to:

```text
DONE    PR011A-foundation  Extract/promote shared ops + HTTP (#363, `fdd7ec82`)
DONE    PR011A1            Server-owned ingest-run → promotion binding
                           (#364, `bcc874ed`)
DONE    PR011A2            Graph Review prepare / review panel
                           (#365, `cec9834f`)
READY   PR011A3            Confirm, durable reload, Session 25 dogfood
BLOCKED PR011B             Hermes preview_write / confirm_commit (on A3)
READY   PR009              Play projection migration (parallel product lane)
BLOCKED PR012              Leftover cleanup safety net
```

Update the detailed slice records:

```text
PR011A1
Status: DONE — GitHub #364, merge
bcc874ed0807b2df24e55724eddee81c541f9d2a

PR011A2
Status: DONE — GitHub #365, merge
cec9834f8667d2af31447540b5acb9dade0373aa

PR011A3
Status: READY
Depends on: PR011A2 (DONE)
```

The tracker must identify PR011A3 as the sole next Phase 8 critical-path capability. PR011B remains blocked.

### `Docs/Roadmaps/ROADMAP-campaign-supergraph.md`

Update the current critical path to:

```text
DONE  PR011A-foundation  Extract/promote shared ops + HTTP
DONE  PR011A1            Server-owned ingest-run → promotion binding
DONE  PR011A2            Graph Review prepare / review panel
NEXT  PR011A3            Confirm, durable reload, Session 25 dogfood
THEN  PR011B             Hermes preview_write / confirm_commit over the same path
```

Update Phase 8 current state to say:

```text
PR011A1 and PR011A2 are complete.

Graph Review can select a server-validated promotable ingest run, prepare a
head-pinned sealed promotion proposal, project game-facing review items, and
maintain a Kernel-valid assertion selection.

The missing product capability is explicit GM confirmation followed by truthful
durable revision reload and end-to-end proof that the reviewed object has become
campaign memory.
```

Do not describe PR011A3 as a new Kernel, ingestion system, generic Graph Review redesign, or Hermes capability.

---

## Dispatch gate

Do not dispatch until all of the following are true:

* this handoff exists at its canonical repository path;
* the tracker records PR011A1 and PR011A2 as `DONE`;
* the roadmap records PR011A3 as `NEXT`;
* `<DOCS_REANCHOR_SHA>` has been replaced with the immutable docs re-anchor SHA;
* `git rev-parse HEAD` and `git rev-parse origin/main` include that SHA;
* the implementation agent has read the authorities listed in §2;
* no implementation of PR011B, authored entity/statblock generation, Play migration, or generalized Graph Review authoring has begun in this branch.

The checked-in handoff is the complete implementation authority. The worker must not compress, omit, reinterpret, or replace it with a PR-body summary.

---

## §0 Capability decomposition decision

| Candidate outcome                                                                                     |                                 Independently useful? | Public/durable contract changed? | User or operator surface changed? | Failure model changed? | Independently testable or revertible? | Decision                                             |
| ----------------------------------------------------------------------------------------------------- | ----------------------------------------------------: | -------------------------------: | --------------------------------: | ---------------------: | ------------------------------------: | ---------------------------------------------------- |
| Confirm one prepared Graph Review proposal using selected assertion IDs                               |                                                   Yes |                              Yes |                               Yes |                    Yes |                                   Yes | Include                                              |
| Reload the exact committed World Graph revision and replace preview-only success with durable objects |           No, not separate from truthful confirmation |          No new storage contract |                               Yes |                    Yes |                                   Yes | Include                                              |
| Show a compact committed-revision receipt and open affected durable objects                           | No, this is the observable completion of confirmation |                               No |                               Yes |                    Yes |                                   Yes | Include                                              |
| Prove the journey with Session 25 Hesta/apothecary material                                           |              No product capability; verification only |                               No |            Uses existing surfaces |                     No |                                   Yes | Include as acceptance evidence                       |
| Give Hermes `preview_write` or `confirm_commit`                                                       |                                                   Yes |                              Yes |                               Yes |                    Yes |                                   Yes | Named successor: PR011B                              |
| Create the flexible authored entity/statblock object                                                  |                                                   Yes |                              Yes |                               Yes |                    Yes |                                   Yes | Named successor after A3                             |
| Load a durable statblock into the combat tracker                                                      |                                                   Yes |                      Potentially |                               Yes |                    Yes |                                   Yes | Parallel/successor Play work                         |
| Automatically publish at the end of ingestion                                                         |                                                   Yes |                              Yes |                               Yes |                    Yes |                                   Yes | Reject                                               |
| Add durable client-side proposal or operation history                                                 |                                                   Yes |                              Yes |                               Yes |                    Yes |                                   Yes | Reject unless a stop condition proves it unavoidable |
| Replace the transitional authored-overlay authoring system                                            |                                                   Yes |                              Yes |                               Yes |                    Yes |                                   Yes | Successor                                            |
| Build a generic graph editor or graph-management dashboard                                            |                                                   Yes |                              Yes |                               Yes |                    Yes |                                   Yes | Reject                                               |

**Selected capability**

A GM can explicitly confirm the currently prepared Graph Review proposal so that exactly the selected assertions advance the World Graph head and Graph Review truthfully reloads the committed revision as durable campaign memory.

**Why the included rows share one invariant**

Confirmation is not complete when the POST returns. The user-visible capability becomes true only when the sealed proposal is committed, the returned revision is verified through the read path, and the surface replaces preview-only state with objects from that committed revision. The confirm operation, durable reload, receipt, and affected-object opening all establish or expose one publication invariant.

**Named successors**

* PR011B — Hermes uses this same `preview_write` / `confirm_commit` path without gaining a second write protocol.
* Authored entity/statblock vertical slice — DungeonBuddy and DungeonMind produce a typed authored object that enters this same governed path.
* PR009 Play migration — Play consumes revision-pinned graph objects and later loads durable statblocks into the existing combat tracker.
* Broader Graph Object Authoring migration from authored overlay/event log into `GraphContribution`.
* Any permanent operation-history, proposal-draft, undo/retract, or run-completion management surface.

---

## §1 Mission

```text
A GM can confirm a prepared Graph Review proposal so that exactly the selected
assertions become durable, reloadable campaign memory at one truthful committed
World Graph revision.
```

### Invariant

```text
The UI must never report a successful merge or display preview material as
durable unless the server has committed one revision bound to the sealed
proposal, selected assertion IDs, and pinned parent revision, and the client has
reloaded that exact committed revision through the normal World Graph read path.
```

### Mission falsification test

```text
This is not one slice if implementation must also deliver:

- Hermes write tools or agent capability registration;
- a new authored entity/statblock contract;
- Play or combat-tracker integration;
- a new graph identity, merge, contribution, or persistence model;
- automatic ingest publication;
- a generic Graph Review redesign;
- durable browser proposal history;
- a second publication receipt store outside existing World Graph and
  contribution authority.
```

---

## §2 Context, authority, and boundaries

| Field                       | Required content                                                                                                                                                                                                                                       |
| --------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Parent architecture         | `Docs/Design/ARCHITECTURE-campaign-supergraph.md`                                                                                                                                                                                                      |
| Sequencing authority        | `Docs/Plans/PR-TRACKER-campaign-supergraph.md` after the pre-dispatch re-anchor                                                                                                                                                                        |
| Roadmap                     | `Docs/Roadmaps/ROADMAP-campaign-supergraph.md` after the pre-dispatch re-anchor                                                                                                                                                                        |
| Product bridge              | `Docs/Design/DESIGN-extract-promote-graph-review-bridge.md`                                                                                                                                                                                            |
| Governed tool contract      | `Docs/Design/CONTRACT-agent-tool-authored-prep-contributions-v0.md`                                                                                                                                                                                    |
| Surface boundary            | `Docs/Design/DESIGN-graph-object-authoring-surface.md`                                                                                                                                                                                                 |
| Repository rules            | `AGENTS.md`, `.cursor/rules/external-agent-pr-loop.mdc`, `.cursor/skills/external-agent-pr-loop/SKILL.md`                                                                                                                                              |
| Implementation base         | `<DOCS_REANCHOR_SHA>`, descending directly from `cec9834f8667d2af31447540b5acb9dade0373aa`                                                                                                                                                             |
| Predecessor implementation  | PR011A-foundation #363, PR011A1 #364, PR011A2 #365                                                                                                                                                                                                     |
| Exact input consumed        | A PR011A2 `ExtractPromotePrepareResponse` containing the sealed `reviewPackage`, `proposalDigest`, `parentRevisionId`, `runId`, typed `reviewItems`, and a Kernel-valid selected assertion-ID set                                                      |
| Commit authority            | Existing `confirm_extract_promote` → `GraphContribution` → Kernel publication → atomic World Graph head                                                                                                                                                |
| Read authority after commit | Existing revision-pinned World Graph projection and retrieval services                                                                                                                                                                                 |
| Named successor             | PR011B                                                                                                                                                                                                                                                 |
| What remains false          | Hermes cannot initiate or confirm writes; Build/statblock generation does not persist through this path; Play is not migrated; authored overlay/event log remains; ingestion does not auto-publish                                                     |
| Explicit non-goals          | New Kernel semantics, new contribution storage, authentication system, browser-supplied principal or policy, `allowLiveWorld` UI, compatibility confirm body, auto-confirm, undo/retract, general object authoring, run management, combat integration |

### Read authoritative inputs in this order

1. `Docs/Design/ARCHITECTURE-campaign-supergraph.md`
2. Re-anchored `Docs/Plans/PR-TRACKER-campaign-supergraph.md`
3. Re-anchored `Docs/Roadmaps/ROADMAP-campaign-supergraph.md`
4. `Docs/Design/DESIGN-extract-promote-graph-review-bridge.md`
5. `Docs/Design/CONTRACT-agent-tool-authored-prep-contributions-v0.md`
6. `apps/live_control_server/models/extract_promote.py`
7. `apps/live_control_server/services/extract_promote.py`
8. `apps/live_control_server/routes/extract_promote.py`
9. `src/graph_memory/extract_promote_ops.py`
10. `apps/live-control-ui/src/api/extractPromoteApi.ts`
11. `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewExtractPromoteSheet.tsx`
12. `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewSessionToolbar.tsx`
13. Existing owning-boundary backend and frontend tests
14. Repository implementation and review rules

If the base moved, the checked-in prepare/confirm shape differs materially, or the existing read APIs cannot load a specific committed revision, stop and report the consequence before implementation.

### Authority precedence

```text
1. Canonical Campaign Supergraph architecture
2. Re-anchored Campaign Supergraph tracker
3. Canonical checked-in PR011A3 handoff
4. Extract/promote bridge and governed-tool contracts
5. Current repository implementation and tests
6. Project Sources and attached context
7. PR summaries and chat discussion
```

### Locked boundaries

* Ingest creates proposed memory.
* Graph Review judges and confirms proposed memory.
* The Kernel owns durable publication.
* The World Graph head is the durable completion point.
* The browser does not select filesystem paths, principal identity, live-world permission, dry-run mode, idempotency policy, or graph storage roots.
* The sealed review package remains proposal authority.
* The browser sends exact assertion IDs; it never resolves assertions by label.
* The UI does not parse Kernel or contribution internals to determine whether publication succeeded.
* Post-confirm rendering reads the committed revision through the normal read path.
* Chat, local component state, and preview-union state are not campaign memory.

---

## §3 Observable-path inventory

| Observable path                                 | Current behavior                                             | Required behavior                                                                                                     | Same invariant as §1? | Owning boundary                                   |
| ----------------------------------------------- | ------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------- | --------------------: | ------------------------------------------------- |
| Open a prepared review sheet                    | Typed review items and valid local selection; no confirm CTA | Existing behavior retained                                                                                            |                   Yes | React component                                   |
| Zero selected assertions                        | Selection count reaches zero; no confirm action exists       | Confirm button visible but disabled; no request sent                                                                  |                   Yes | React component                                   |
| Valid confirmation                              | Not implemented                                              | Sends sealed package plus exact selected assertion IDs only                                                           |                   Yes | API client + route                                |
| Confirmation while selection changes            | Not applicable                                               | Selection freezes when confirm begins; no mutation of submitted IDs                                                   |                   Yes | React component                                   |
| Confirmation while user closes or switches run  | Not safely owned                                             | Normal close/run-switch actions disabled while request is in flight                                                   |                   Yes | Graph Review workflow                             |
| Stale parent revision                           | Existing backend rejects proposal                            | Old proposal is never retried as a write; user is told the graph changed and must prepare/review a fresh proposal     |                   Yes | Service + workflow                                |
| Unknown assertion ID                            | Kernel/service rejects                                       | Fail closed; do not silently drop or resolve by label                                                                 |                   Yes | Service                                           |
| Dependency-invalid selection                    | A2 prevents ordinary UI creation of it                       | Server still validates and rejects adversarial requests                                                               |                   Yes | Service + Kernel                                  |
| Exact duplicate retry after response loss       | Operator API supports idempotency policy supplied by caller  | Product policy is server-owned; exact retry resolves as committed/already applied rather than duplicating publication |                   Yes | Service                                           |
| Already-applied exact proposal                  | Raw operator behavior                                        | Return typed successful no-op receipt naming the existing committed revision                                          |                   Yes | Service + route                                   |
| Publication failure before commit               | Backend can return failure result                            | No head advancement; UI remains in failure state and does not show durable objects                                    |                   Yes | Kernel + service + component                      |
| Publication succeeds but audit/rebuild degrades | Backend distinguishes published state                        | Return success with degraded audit warning; reload committed revision; never retry confirmation                       |                   Yes | Service + component                               |
| Unknown/network result after request dispatch   | No product UX                                                | Mark result ambiguous; permit only an exact idempotent retry/check using the same sealed package and IDs              |                   Yes | API client + component                            |
| Reload committed revision                       | Not implemented                                              | Fetch exact `committedRevisionId`; reject mismatched or unpinned read result                                          |                   Yes | Existing World Graph read API + frontend workflow |
| Refresh Graph Review catalog                    | Not implemented after confirm                                | Refresh after successful/no-op confirmation; do not treat refresh failure as publication failure                      |                   Yes | Workbench state                                   |
| Replace preview state                           | Preview projection remains visible                           | Durable projection/objects from committed revision become primary completion state                                    |                   Yes | Graph Review workflow                             |
| Open affected objects                           | Not implemented                                              | Use server-projected durable object IDs; never infer by label                                                         |                   Yes | Service response + selected-object UI             |
| Browser or server reload after completion       | Preview and local receipt are not authority                  | Current graph head or pinned committed revision contains the objects and relationships                                |                   Yes | World Graph store/read integration                |
| Session 25 Hesta/apothecary proof               | Not yet run through UI confirm                               | Full ingest → review → confirm → retrieve → reload evidence recorded                                                  |     Yes, verification | Existing product surfaces                         |
| Hermes retrieves the committed object           | Hermes is read-only and graph-grounded                       | Fresh graph retrieval finds the object after publication; no Hermes write capability added                            |     Yes, verification | Existing Hermes read path                         |

Every row shares the §1 invariant. A discovered requirement that does not share it is a split trigger.

---

## §4 Files in scope — allowlist

### Required documentation paths

| Action | Path                                                                     | Purpose                                                                              |
| ------ | ------------------------------------------------------------------------ | ------------------------------------------------------------------------------------ |
| Create | `Docs/Plans/HANDOFF-pr011a3-confirm-durable-reload-session25-dogfood.md` | Complete implementation authority                                                    |
| Modify | `Docs/Plans/PR-TRACKER-campaign-supergraph.md`                           | Mark A3 `DOING` during implementation while A1/A2 remain `DONE`; keep PR011B blocked |
| Modify | `Docs/Roadmaps/ROADMAP-campaign-supergraph.md`                           | Reflect the active A3 gate without claiming PR011B                                   |
| Create | `Docs/Reports/PR011A3-SESSION25-DURABLE-MEMORY-DOGFOOD.md`               | Record exact end-to-end acceptance evidence and limitations                          |

The pre-dispatch docs commit already sets A3 to `READY/NEXT`. The implementation branch may change A3 to `DOING`; it must not mark A3 `DONE` before merge. The operator must perform a post-merge re-anchor with the real GitHub PR and merge SHA.

### Backend product boundary

| Action                                           | Path                                                             | Purpose                                                                                                         |
| ------------------------------------------------ | ---------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| Modify                                           | `apps/live_control_server/models/extract_promote.py`             | Replace the product confirm body with strict v2 request and typed product receipt                               |
| Modify                                           | `apps/live_control_server/services/extract_promote.py`           | Inject server-owned confirmation policy, call existing ops, classify exact outcomes, and project a safe receipt |
| Modify                                           | `apps/live_control_server/routes/extract_promote.py`             | Expose strict v2 confirm behavior and stable error envelopes                                                    |
| Modify                                           | `tests/test_live_extract_promote_api.py`                         | Route/service/commit-state owning tests                                                                         |
| Modify if required by exact applied-state checks | `apps/live_control_server/services/promotable_ingest_run.py`     | Keep post-confirm promotability truthful without creating a second receipt store                                |
| Modify if required by exact applied-state checks | `apps/live_control_server/services/graph_ingest_run_registry.py` | Project existing authoritative applied state into catalog summaries                                             |
| Modify if preceding two files change             | `tests/test_promotable_ingest_run.py`                            | Applied/stale/idempotent promotability coverage                                                                 |
| Modify if registry changes                       | `tests/test_live_graph_ingest_run_registry.py`                   | Catalog refresh and truthful summary coverage                                                                   |

Do not modify `src/graph_memory/extract_promote_ops.py`, Kernel merge code, contribution storage, or World Graph persistence merely to reshape product responses. If the existing operations cannot establish the required invariant, stop and report the missing Kernel contract.

### Frontend API and Graph Review workflow

| Action                                                         | Path                                                                                                | Purpose                                                                                  |
| -------------------------------------------------------------- | --------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------- |
| Modify                                                         | `apps/live-control-ui/src/api/extractPromoteApi.ts`                                                 | Strict confirm request, typed success/error handling                                     |
| Modify                                                         | `apps/live-control-ui/src/api/types.ts`                                                             | Product request/receipt contracts                                                        |
| Modify                                                         | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewExtractPromoteSheet.tsx`      | Confirm CTA, frozen submitted selection, progress, failure, and receipt states           |
| Modify                                                         | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewSessionToolbar.tsx`           | Bind confirm lifecycle to the current prepared proposal/run and prevent unsafe switching |
| Modify                                                         | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewWorkbenchModule.tsx`          | Refresh catalog and transition to durable revision/object state                          |
| Modify if this owns durable projection display                 | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewLiveProjectionPanel.tsx`      | Replace preview completion state with committed revision data                            |
| Modify                                                         | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewExtractPromoteSheet.test.tsx` | Owning component/workflow tests                                                          |
| Modify if present and needed                                   | `apps/live-control-ui/src/api/extractPromoteApi.test.ts`                                            | Exact serialized body and error/receipt parsing                                          |
| Modify if present and needed                                   | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewWorkbenchModule.test.tsx`     | Catalog refresh and committed-revision transition proof                                  |
| Modify only if existing read caller lacks necessary invocation | `apps/live-control-ui/src/api/liveApi.ts`                                                           | Call the existing revision-pinned projection contract; do not add a new graph read API   |

### Bounded discovery exception

```text
Directory:
apps/live-control-ui/src/planSurface/graphReviewWorkbench/

Maximum additional paths:
4

Allowed path kinds:
Existing .ts, .tsx, and owning test files only.

Decision rule for including a path:
The path must already own one of these exact behaviors:
- selected live-run/workbench state;
- revision-pinned projection reload;
- selected durable object opening;
- catalog refresh;
- owning workflow tests.

Required report when a path is added:
Name the path, the behavior it already owns, why the listed files cannot prove
the invariant without it, and confirm that no new product surface or durable
contract is introduced.
```

No backend bounded discovery exception exists. An additional backend production path is a stop condition.

Generated API fixtures or snapshots may be updated only when an existing repository rule requires them. They must be reported explicitly in the handback.

---

## §5 Files and capabilities explicitly out of scope

| Path, ownership layer, or capability                                               | Why this slice must not touch or claim it                                   |
| ---------------------------------------------------------------------------------- | --------------------------------------------------------------------------- |
| `src/graph_memory/kernel/**`                                                       | Kernel publication semantics are predecessor authority, not A3 product work |
| `src/graph_memory/world_supergraph/**`                                             | No new storage or head model                                                |
| `src/graph_memory/extract_promote_ops.py`                                          | Shared orchestration is already established; changes require stop review    |
| `src/graph_memory/extract_promote_proposal.py`                                     | Proposal sealing is predecessor authority                                   |
| `src/graph_memory/candidate_graph_to_contribution.py`                              | Candidate mapping is predecessor authority                                  |
| Contribution or identity model schemas                                             | No new graph semantics                                                      |
| `apps/live-control-ui/src/modules/IngestionModule.tsx`                             | Ingest must not auto-publish                                                |
| Hermes graph-agent runtime, host, plugin, pointer store, or tool catalog           | PR011B                                                                      |
| Agent capability registry                                                          | PR011B                                                                      |
| DungeonMind/DungeonBuddy authored entity or statblock types                        | Named successor                                                             |
| Combat tracker or Play surface                                                     | PR009/successor                                                             |
| Authored overlay/event-log migration                                               | Separate authoring capability                                               |
| Undo, retract, supersede, or correction-management UI                              | Separate capability                                                         |
| New authentication or account system                                               | Not needed to prove server-owned product principal                          |
| Browser `allowLiveWorld`, `confirmingPrincipal`, `dryRun`, or idempotency controls | Explicitly forbidden                                                        |
| Compatibility support for product confirm v1                                       | Forward-only project contract                                               |
| Persistent browser operation history                                               | Separate durable contract                                                   |
| Automatic navigation or publication from `/ingest`                                 | Product boundary violation                                                  |
| Generic graph visualization/editor changes                                         | Separate capability                                                         |
| Backlog cleanup unrelated to this invariant                                        | PR012 or named consumer owner                                               |

Nearby code is not authorization.

---

## §6 Implementation contract and conditional matrices

### Product input

The current PR011A2 prepared state supplies:

```text
proposalId
proposalDigest
parentRevisionId
worldId
runId
campaignId
sessionId
reviewPackage
reviewItems
reviewSummary
selected assertion IDs
```

The confirm operation consumes only:

```json
{
  "schema": "dmb_extract_promote_confirm_request_v2",
  "reviewPackage": {
    "...": "opaque sealed package returned by prepare"
  },
  "assertionIds": [
    "assertion:..."
  ]
}
```

Requirements:

* `reviewPackage` is required and remains opaque to the browser.
* `assertionIds` is required and non-empty.
* IDs must be unique.
* IDs retain the stable selection order used by the UI.
* Every ID must exist and be selectable in the sealed package.
* Unknown, duplicate, dependency-invalid, or unselected endpoint combinations fail closed.
* Extra fields are rejected.
* The following product request fields are forbidden:

  * `confirmingPrincipal`
  * `allowLiveWorld`
  * `dryRun`
  * `allowIdempotentNoop`
  * `worldId`
  * `runId`
  * manifest, source, candidate, store, or filesystem paths

### Server-owned confirmation policy

The route/service owns these values:

```text
confirming principal:
  resolved server-side;
  use an existing authenticated/operator principal when available;
  otherwise use one bounded, tested Graph Review product principal constant;
  never accept it from the browser.

dry run:
  false

live-world permission:
  server policy for the Graph Review product confirm route;
  never supplied by the browser.

idempotent no-op:
  enabled for exact proposal retries so response loss cannot cause duplicate
  publication.

world root:
  existing server configuration only.
```

The exact internal principal string is not a browser contract. It must be centralized rather than duplicated in the route and service.

### Product output

The route returns a typed product receipt rather than exposing the raw Kernel/ops result dictionary.

```ts
interface ExtractPromoteConfirmReceipt {
  schema: "dmb_extract_promote_confirm_v2";
  outcome:
    | "committed"
    | "already_applied"
    | "published_audit_degraded";
  worldId: string;
  proposalId: string;
  proposalDigest: string;
  parentRevisionId: string;
  committedRevisionId: string;
  headAdvanced: boolean;
  selectedAssertionIds: string[];
  acceptedAssertionIds: string[];
  affectedObjectIds: string[];
  appliedAssertionCount: number;
  auditStatus: "ok" | "degraded";
  warnings: string[];
}
```

Required semantics:

#### `committed`

```text
headAdvanced = true
committedRevisionId names the new published revision
auditStatus = ok
affectedObjectIds contains exact durable IDs projected from accepted selected assertions
```

#### `already_applied`

```text
headAdvanced = false
committedRevisionId names the revision in which the exact proposal/selection is already applied
auditStatus = ok unless existing authoritative evidence says otherwise
the outcome is successful and must not ask the user to confirm again
```

#### `published_audit_degraded`

```text
headAdvanced = true
committedRevisionId names the revision that was published
auditStatus = degraded
warnings explain the post-publication audit/rebuild degradation
the client reloads the committed revision and must not retry confirmation
```

The service may derive `affectedObjectIds` from the verified sealed proposal and authoritative identity-resolution/merge result. The browser must not derive durable IDs from labels or parse raw Kernel proposal internals.

If the existing result cannot project exact affected durable IDs without a new Kernel or persisted contract, stop and report the missing predecessor capability.

### Stable failure behavior

| Failure                                           | Required result                                                                                                                                             |
| ------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Empty selection                                   | `422`, stable `empty_selection` or existing equivalent; no write                                                                                            |
| Unknown assertion ID                              | `422` or `409`, stable validation code; no write                                                                                                            |
| Dependency-invalid assertion set                  | Fail closed; no write                                                                                                                                       |
| Tampered package or digest mismatch               | `409 proposal_verification_failed`; no write                                                                                                                |
| Parent revision changed                           | `409` stale/proposal verification failure; no write                                                                                                         |
| World uninitialized                               | Stable non-success error; no write                                                                                                                          |
| Server policy refuses configured mutation root    | Server/configuration failure; never ask browser for `allowLiveWorld`                                                                                        |
| Publication returns `published=false`             | Non-success response; no head advancement                                                                                                                   |
| Exact request already applied                     | Typed `already_applied` success                                                                                                                             |
| Publication succeeded but later audit degraded    | Typed `published_audit_degraded` success                                                                                                                    |
| Catalog refresh fails after success               | Preserve successful receipt; offer refresh retry only                                                                                                       |
| Durable projection reload fails after success     | Preserve committed revision receipt; offer reload retry only                                                                                                |
| Response lost after request may have committed    | Mark result ambiguous and permit exact idempotent retry; do not prepare a different proposal automatically                                                  |
| Unexpected internal exception before known commit | Stable safe 500 error; do not claim success                                                                                                                 |
| Unexpected exception after known commit           | Must be classified as committed/degraded if the service can prove the committed revision; never report a retryable publication failure after a known commit |

### Replay and idempotency

```text
same sealed package + same assertion IDs:
  first call commits;
  exact retry returns already_applied or the same truthful committed revision;
  never creates a second active contribution or second graph revision for the
  same exact proposal application.

same sealed package + different assertion IDs:
  treated as a distinct attempted selection;
  accepted only if proposal binding and current-head rules allow it;
  must not silently reinterpret an already-applied subset.

same run prepared against a changed head:
  creates a new proposal;
  old proposal remains stale and cannot confirm.

retry after pre-commit failure:
  allowed only when the failure is explicitly pre-commit and the same proposal
  remains valid.

retry after published_audit_degraded:
  prohibited; retry only the read/audit/reload action.

duplicate delivery:
  deduplicated by existing proposal/contribution authority;
  no new browser-generated idempotency key.
```

### Trust boundary

```text
Verifies:
- sealed proposal schema and digest;
- pinned parent revision;
- selected assertion membership;
- dependency-valid assertion set;
- source and campaign/world binding already sealed by prepare;
- publication result and committed revision;
- affected durable object IDs;
- exact revision reload.

Records or trusts without re-proving:
- the existing Kernel's atomic publication guarantee;
- predecessor contribution and identity semantics;
- server configuration for world roots;
- server-owned product principal.

Rejects:
- browser principals and policy flags;
- arbitrary paths;
- label-based assertion or object resolution;
- unknown assertion IDs;
- stale proposals;
- preview data presented as durable state;
- client inference from raw result dictionaries.
```

### Commit point

```text
Commit point:
Atomic World Graph head publication inside the existing Kernel operation.

Before commit:
- confirm may fail safely;
- Graph Review remains on prepared preview state;
- no success receipt or durable object state is shown.

After commit:
- the committed revision is campaign memory even if audit, catalog refresh,
  projection reload, navigation, or response delivery later fails.

Truthful result after a post-commit failure:
- return committed or published_audit_degraded when the committed revision is
  known;
- retain the committed revision receipt client-side;
- retry only read/refresh operations.

Recovery or reconciliation path:
- exact idempotent confirm retry when the original response is unknown;
- revision-pinned projection reload;
- catalog refresh;
- existing contribution/revision audit tools;
- never auto-create a replacement proposal and silently confirm it.
```

---

### §6A State and fallback matrix

| Observable path           | Loading or initializing                                            | Exact success                                  | Ordinary miss                                                                              | Dependency unavailable                      | Integrity or contract failure                      | Stale or superseded                                     | Retry or replay                                                  |
| ------------------------- | ------------------------------------------------------------------ | ---------------------------------------------- | ------------------------------------------------------------------------------------------ | ------------------------------------------- | -------------------------------------------------- | ------------------------------------------------------- | ---------------------------------------------------------------- |
| Confirm CTA               | Disable selection, close, and run-switch controls; show “Merging…” | Receive typed receipt                          | Not applicable                                                                             | Show safe request failure; no success state | Fail closed                                        | Old proposal invalid                                    | Exact retry only when result is unknown or explicitly pre-commit |
| World Graph publication   | Existing Kernel operation                                          | One committed revision                         | No selectable assertions is blocked before call                                            | Stable server failure                       | No publication                                     | Parent mismatch fails                                   | Existing idempotent exact retry                                  |
| Durable projection reload | Show committed receipt while loading                               | Response revision equals `committedRevisionId` | Affected object absent is an integrity/product failure, not a label fallback               | Preserve receipt and offer reload           | Reject mismatched revision or malformed projection | Do not silently load latest different revision as proof | Retry read only                                                  |
| Catalog refresh           | Refresh after receipt                                              | Current catalog displayed                      | Run may remain reviewable if partial assertions remain; do not invent “fully merged” state | Preserve committed receipt                  | Show refresh warning                               | Refresh current catalog                                 | Retry refresh only                                               |
| Affected-object opening   | Wait for committed projection                                      | Open exact durable ID                          | Show “committed object not present in projection” and diagnostics                          | Preserve receipt                            | Never search by label                              | Re-read committed revision                              | Retry exact-ID read                                              |
| Stale proposal recovery   | No confirm retry                                                   | New prepare creates a new package for review   | Run no longer promotable produces explicit terminal state                                  | Show dependency failure                     | Never reuse old package                            | Old selection discarded                                 | User explicitly reviews refreshed proposal                       |
| Ambiguous response loss   | Show unknown-result state                                          | Exact retry returns committed/already applied  | Not applicable                                                                             | Remain ambiguous                            | Never assume failure                               | Do not reprepare until exact result checked             | Exact package/ID retry                                           |

There is no fallback to preview-union state, label search, manifest paths, corpus search, local browser memory, or Hermes prose for publication truth.

---

### §6B Identity matrix

| Situation              | Required matching rule                                        | Ambiguity behavior                          | Fallback permitted?       | Persistence consequence                                 |
| ---------------------- | ------------------------------------------------------------- | ------------------------------------------- | ------------------------- | ------------------------------------------------------- |
| Assertion selection    | Exact `assertionId` contained in sealed package               | Reject unknown or duplicate IDs             | No                        | Only exact selected assertions may enter contribution   |
| Assertion dependency   | Exact dependency assertion IDs from server projection/package | Reject invalid combinations                 | No                        | No edge may publish without valid durable/new endpoints |
| Durable object opening | Exact server-returned durable object ID                       | Report failure if absent                    | No label fallback         | Object identity survives reload                         |
| Alias or label         | Presentation only                                             | Never used to locate publication result     | No                        | None                                                    |
| Normalized key         | Not used by client                                            | Not applicable                              | No                        | None                                                    |
| Rename                 | Stable durable object ID remains authoritative                | Display new label from committed projection | No rebinding by old label | Persisted ID remains                                    |
| Deletion/retraction    | Existing graph lifecycle semantics                            | Do not recreate by label                    | No                        | Read result follows pinned revision                     |
| Rebinding              | Kernel-owned identity outcome only                            | Client cannot rebind                        | No                        | Existing identity decision authority                    |

This slice introduces no new graph identity semantics.

---

### §6C Persistence and replay matrix

| Operation                 | Durable representation                                                                         | Round-trip guarantee                                                                                                       | Duplicate or replay behavior                     | Compatibility or migration                                              | Rollback or reversion                                      |
| ------------------------- | ---------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------ | ----------------------------------------------------------------------- | ---------------------------------------------------------- |
| Confirm selected proposal | Existing `GraphContribution`, contribution ledger, immutable World Graph revision, atomic head | Selected accepted assertions and their durable identities are readable from `committedRevisionId`                          | Exact retry is idempotent/already applied        | Product confirm v2 is forward-only; no browser v1 compatibility         | Existing graph contribution lifecycle only; no new UI undo |
| Reload committed revision | Existing World Graph projection/read contract                                                  | Returned revision must exactly match receipt                                                                               | Repeat reads are safe                            | No new read schema unless existing API already requires additive typing | Read-only                                                  |
| Catalog refresh           | Existing graph-ingest registry and World Graph state                                           | Refresh must not change publication truth                                                                                  | Repeat safe                                      | Do not create a second applied-run receipt store                        | Read-only                                                  |
| Client receipt            | Ephemeral React state only                                                                     | Receipt survives workflow actions during current mounted session; campaign truth survives through graph, not local receipt | Reconstructed from exact retry/read where needed | No local-storage migration                                              | Closing receipt does not revert commit                     |
| Session 25 dogfood report | Markdown report                                                                                | Records evidence/provenance only                                                                                           | New evidence appended accurately                 | Not runtime authority                                                   | Deletable documentation; graph commit remains              |

A new durable publication-receipt file, browser operation log, or run-completion database is a second durable contract and requires stop review.

---

### §6D Predecessor-to-consumer mapping

**Grounding source**

```text
Canonical checked-in Pydantic models and TypeScript contracts on
<DOCS_REANCHOR_SHA>, plus owning API tests.

Do not construct a simplified fixture from memory.
```

| Predecessor field or outcome                    | Real shape and optionality                            | Consumer field or behavior       | Transformation                                           | Proof                              |
| ----------------------------------------------- | ----------------------------------------------------- | -------------------------------- | -------------------------------------------------------- | ---------------------------------- |
| `reviewPackage`                                 | Required opaque object from prepare                   | Confirm request `reviewPackage`  | Pass unchanged                                           | Exact serialized-body test         |
| `reviewItems[].assertionId`                     | Required string                                       | Confirm request `assertionIds[]` | Select exact IDs only                                    | Component/API test                 |
| `reviewItems[].dependsOnAssertionIds`           | Optional/empty array                                  | Selection validity               | A2 cascade retained; backend revalidates                 | Component + API adversarial test   |
| `proposalDigest`                                | Required string                                       | Receipt and UI binding           | Must equal response receipt; never recomputed by browser | API/component test                 |
| `parentRevisionId`                              | Required string                                       | Receipt and stale behavior       | Server verifies through sealed package                   | Stale-parent integration test      |
| `runId`                                         | Required prepared-run identity                        | Workflow binding only            | Not sent in confirm body                                 | Serialized-body negative assertion |
| Current v1 `confirmingPrincipal`                | Required caller field in operator-shaped HTTP request | Removed from product body        | Inject server-side                                       | Route negative test                |
| Current v1 `dryRun`                             | Optional boolean                                      | Removed                          | Server uses `false`                                      | Route negative test                |
| Current v1 `allowLiveWorld`                     | Optional boolean                                      | Removed                          | Server policy                                            | Route negative test                |
| Current v1 `allowIdempotentNoop`                | Optional boolean                                      | Removed                          | Server enables exact retry safety                        | Duplicate/retry integration test   |
| Current raw `result` dictionary                 | Internal service/ops shape                            | Typed v2 receipt                 | Server projects stable fields                            | Response contract test             |
| Kernel `published=false`                        | Existing failure outcome                              | Non-success product response     | Preserve no-head-advance truth                           | Failure injection                  |
| Known committed revision with audit degradation | Existing post-publication outcome                     | `published_audit_degraded`       | Success + warning; no confirm retry                      | API + component test               |
| Exact duplicate application                     | Existing idempotent outcome                           | `already_applied`                | Success/no-op receipt                                    | Integration test                   |

The CLI and internal path-based operator seam may continue calling shared operations directly. Product HTTP confirm is forward-only v2.

---

## §7 Verification ownership map and commands

### Verification ownership map

| Guarantee                                                  | Owning boundary                       | Command or scenario                                                | Expected evidence                                                     |
| ---------------------------------------------------------- | ------------------------------------- | ------------------------------------------------------------------ | --------------------------------------------------------------------- |
| Product body contains only sealed package and selected IDs | Frontend API serializer + route model | API unit test and route test                                       | Forbidden fields absent/rejected                                      |
| Server owns principal and live-world/idempotency policy    | Service/route                         | Service spy or integration assertion                               | Correct internal call; browser fields rejected                        |
| Zero selection cannot confirm                              | React component + route               | Component test and adversarial API test                            | Disabled CTA; 422 if bypassed                                         |
| Selection is frozen during confirm                         | React workflow                        | Deferred-promise component test                                    | Submitted IDs unchanged; close/switch disabled                        |
| Stale proposal cannot publish                              | Service/Kernel integration            | Advance head after prepare, then confirm                           | 409; no new head                                                      |
| Exact retry cannot duplicate                               | Commit-owning integration             | Submit same package/IDs twice                                      | First committed; second already applied; one contribution/application |
| Publication failure does not advance head                  | Kernel/service failure injection      | Forced `published=false`                                           | Error response; head unchanged                                        |
| Audit degradation does not turn a commit into failure      | Service integration                   | Inject post-publication audit degradation                          | 200 degraded receipt; committed revision named                        |
| UI never retries confirm after degraded success            | Component                             | Mock degraded receipt                                              | Reload action only                                                    |
| Unknown response supports safe exact retry                 | Component/API integration             | First response rejected/lost; second exact request already applied | No new prepare; no duplicate write                                    |
| Durable reload pins committed revision                     | Frontend workflow + read API          | Mock/real confirm followed by projection fetch                     | Requested/returned revision equals receipt                            |
| Preview is not shown as durable completion                 | Component/workflow                    | Confirm then delay reload                                          | Receipt says reload pending; preview not relabeled as committed       |
| Affected objects open by exact durable ID                  | Service receipt + component           | Confirm fixture with identity remap                                | Exact returned ID selected                                            |
| Catalog refresh failure does not invalidate commit         | Component/workflow                    | Confirm success then refresh reject                                | Receipt preserved; refresh warning                                    |
| Browser/server reload sees committed object                | Store/read integration                | Restart/reload after confirm                                       | Object and relationship remain at head                                |
| Session 25 object becomes retrievable in Plan/Hermes       | Existing consumer surfaces            | Manual dogfood                                                     | Fresh graph read finds exact durable object                           |
| No successor capability added                              | Diff inspection                       | `git diff --name-only` and code review                             | No Hermes/Play/statblock paths                                        |

### Required backend commands

```bash
uv run pytest -q \
  tests/test_live_extract_promote_api.py \
  tests/test_promote_extract_cli.py \
  tests/test_extract_promote_review_projection.py \
  tests/test_promotable_ingest_run.py \
  tests/test_live_graph_ingest_run_registry.py
```

Run the existing Kernel regression set because A3 exercises its public publication contract:

```bash
uv run pytest -q \
  tests/test_graph_kernel_contribution_merge.py \
  tests/test_graph_kernel_contribution_rebuild.py \
  tests/test_graph_kernel_world_projection.py \
  tests/test_graph_kernel_identity.py
```

Run lint on every touched Python path:

```bash
uv run ruff check \
  apps/live_control_server/models/extract_promote.py \
  apps/live_control_server/routes/extract_promote.py \
  apps/live_control_server/services/extract_promote.py \
  tests/test_live_extract_promote_api.py
```

Extend that command with every additional allowlisted Python file actually changed.

### Required frontend commands

```bash
cd apps/live-control-ui

npm test -- --run \
  src/api/extractPromoteApi.test.ts \
  src/planSurface/graphReviewWorkbench/GraphReviewExtractPromoteSheet.test.tsx \
  src/planSurface/graphReviewWorkbench/GraphReviewWorkbenchModule.test.tsx
```

If one named file does not exist on the implementation base, create or use the owning test file and report the exact replacement. Do not silently omit the guarantee.

```bash
npx tsc --noEmit
```

Run any existing broader Graph Review suite that owns the modified workbench state.

### Exact contract assertions

Tests must assert:

```text
Confirm request keys:
- schema
- reviewPackage
- assertionIds

Forbidden request keys:
- confirmingPrincipal
- dryRun
- allowLiveWorld
- allowIdempotentNoop
- worldId
- runId
- candidateGraphPath
- sourceUri
- sourceRevisionId
- manifestPath
- previewUnionStorePath
```

Tests must validate the full typed v2 receipt rather than checking only HTTP status.

### Automated end-to-end publication proof

Use a temporary World Graph root or isolated copy. The test must execute:

```text
prepare against revision A
→ choose valid assertion IDs
→ confirm
→ assert head advances to revision B
→ fetch projection pinned to B
→ assert accepted object/relationship exists
→ submit exact confirm again
→ assert already_applied and no revision C
→ restart/recreate service client
→ fetch current head/projection
→ assert durable object still exists
```

Do not mutate the live checked-in/local Eldyrwild graph during automated tests.

### Minimal live proof

**Existing surfaces used**

* `/ingest`
* Graph Review
* Plan Agent Interaction
* Existing World Graph object/evidence presentation

**Smallest scenario**

```text
1. Use the real Session 25 recap/run.
2. Prefer Hesta and the apothecary when the actual extraction produces them.
3. Open the run in Graph Review.
4. Click Review & merge.
5. Inspect the real proposed object and relationship labels.
6. Keep a valid selected assertion set.
7. Record the current World Graph head.
8. Click Merge N changes into campaign memory only with explicit operator approval.
9. Record the receipt and new committed revision.
10. Confirm Graph Review reloads that exact revision.
11. Open the affected durable object by exact ID.
12. Open its relationship and admitted source evidence.
13. Reload the browser/server.
14. Confirm the durable object remains.
15. Ask Plan/Hermes a fresh question that requires the new object.
16. Confirm graph retrieval—not recap fallback or conversation memory—supplies it.
```

**Preferred acceptance object**

```text
Hesta
the Mireward apothecary
a relationship connecting the new material to Mireward Reach
```

Do not fabricate Hesta, the apothecary, or a Mireward relationship when the real Session 25 source/extraction does not support them. Use another real Session 25 object only after documenting why the preferred candidate was unavailable.

**Initial state**

```text
The chosen object is absent from the current World Graph head.
The run is preview-ready and server-marked promotable.
The World Graph is initialized.
```

**Expected observation**

```text
The head advances once.
The receipt identifies the exact committed revision.
The object and selected relationships are visible through the durable read path.
Reload preserves them.
Plan/Hermes can retrieve them from the new graph revision.
No automatic publication or Hermes write tool exists.
```

**Evidence captured**

* old and new revision IDs;
* run ID;
* proposal ID and digest;
* selected assertion IDs;
* confirm outcome;
* affected durable object IDs;
* screenshots or concise observations of review, receipt, durable object, relationship, and source evidence;
* Plan/Hermes question and graph-retrieval trace;
* browser/server reload result;
* exact commands and environment;
* whether the operator explicitly approved live publication.

If provider credentials, the real Session 25 run, or the live product environment are unavailable, record the live proof as `BLOCKED`. Do not substitute a fixture and claim live acceptance. The automated isolated-world proof remains mandatory but does not by itself satisfy the Session 25 dogfood gate without an explicit operator waiver.

### Baseline failure protocol

For each required command already failing on `<DOCS_REANCHOR_SHA>`:

| Command           | Base result      | Head result      | New failure introduced? | Acceptance effect                 | Waiver                               |
| ----------------- | ---------------- | ---------------- | ----------------------: | --------------------------------- | ------------------------------------ |
| `<exact command>` | `<exact result>` | `<exact result>` |                  Yes/No | Blocked or acceptable with waiver | `<explicit operator waiver or none>` |

No result may be described as CI unless it came from an attached CI workflow. Author-local, independently rerun, and manual results must remain distinct.

### Repository integrity commands

```bash
git diff --check

git diff --stat <DOCS_REANCHOR_SHA>...HEAD -- \
  Docs/Plans/HANDOFF-pr011a3-confirm-durable-reload-session25-dogfood.md \
  Docs/Plans/PR-TRACKER-campaign-supergraph.md \
  Docs/Roadmaps/ROADMAP-campaign-supergraph.md \
  Docs/Reports/PR011A3-SESSION25-DURABLE-MEMORY-DOGFOOD.md \
  apps/live_control_server/models/extract_promote.py \
  apps/live_control_server/routes/extract_promote.py \
  apps/live_control_server/services/extract_promote.py \
  tests/test_live_extract_promote_api.py \
  apps/live-control-ui/src/api/extractPromoteApi.ts \
  apps/live-control-ui/src/api/types.ts \
  apps/live-control-ui/src/planSurface/graphReviewWorkbench/

git diff --name-only <DOCS_REANCHOR_SHA>...HEAD
```

---

## §8 Required implementation handback

The PR body or final implementation handback must include:

1. Docs re-anchor SHA used as implementation base.
2. Final head SHA.
3. GitHub PR number.
4. Actual changed paths.
5. Every bounded-discovery path and justification.
6. Focused diff stat limited to §4 paths.
7. Exact product confirm request schema.
8. Exact product confirm receipt schema.
9. The server-owned principal/policy implementation seam.
10. Proof that browser principal/policy/path fields are rejected.
11. Proof that zero selection cannot confirm.
12. Proof that stale proposals cannot publish.
13. Proof that exact retry cannot duplicate publication.
14. Proof that `published=false` leaves the head unchanged.
15. Proof that audit degradation still returns the committed revision as success.
16. Proof that Graph Review requests and validates the exact committed revision.
17. Proof that affected objects are opened by durable ID rather than label.
18. Proof that catalog/projection refresh failure does not erase a successful receipt.
19. Automated temporary-world prepare→confirm→reload result.
20. Session 25 live dogfood result or explicit `BLOCKED` state.
21. Old/new revision IDs from live dogfood when run.
22. Evidence that Plan/Hermes retrieves the new object through fresh graph tools.
23. Every §7 command and exact result.
24. Provenance of every result:

    * author-local;
    * independently rerun local;
    * CI;
    * manual observation.
25. Base/head comparison for required failing commands.
26. Explicit operator waivers; write `none` when none exist.
27. Paths outside §4; write `none` or include a stop report.
28. Stop conditions encountered and their resolution; write `none` when none exist.
29. Deviations from §6 matrices; write `none` when none exist.
30. Confirmation that no Hermes write capability was added.
31. Confirmation that no authored entity/statblock capability was added.
32. Confirmation that no Play/combat integration was added.
33. Confirmation that ingestion still does not auto-publish.
34. Confirmation that no durable browser operation store or second publication receipt store was added.
35. Confirmation that the checked-in handoff was implemented without compression or omitted constraints.

Do not report “all tests passed” when a required suite was omitted, a baseline failure remains, live dogfood was blocked, or evidence is only author-reported.

---

## §9 Acceptance rubric

The reviewer accepts only when every applicable bullet is true.

* [ ] Exactly one capability was delivered: explicit proposal-bound confirmation into durable campaign memory.
* [ ] The product confirm body contains only `reviewPackage` and `assertionIds` plus its schema.
* [ ] The browser cannot supply principal, policy, paths, world root, dry-run, or idempotency flags.
* [ ] The sealed review package remains confirmation authority.
* [ ] The submitted assertion IDs are frozen at confirmation start.
* [ ] Zero selection disables confirm and an adversarial empty request fails.
* [ ] Unknown or dependency-invalid assertion IDs fail closed.
* [ ] A stale parent revision cannot publish.
* [ ] Exact retry is idempotent and does not create another revision.
* [ ] A pre-commit failure leaves the head unchanged.
* [ ] A known post-commit audit failure is reported as committed/degraded, not as a retryable publication failure.
* [ ] The success receipt names the exact committed revision.
* [ ] Graph Review reloads that exact revision through the normal read path.
* [ ] A mismatched read revision is rejected rather than treated as success.
* [ ] Preview material is never relabeled as durable while reload is pending or failed.
* [ ] Affected objects are selected by server-returned durable IDs.
* [ ] Catalog or projection refresh failure preserves publication truth and the committed receipt.
* [ ] Reload proves the object exists independently of local component state.
* [ ] Session 25 live proof is recorded or explicitly blocked with a named waiver requirement.
* [ ] Plan/Hermes retrieval proof uses fresh graph tools and does not add Hermes write capability.
* [ ] No new Kernel, contribution, identity, or storage semantics were introduced.
* [ ] No second durable receipt store or browser operation-history contract was introduced.
* [ ] No automatic ingest publication was added.
* [ ] No Hermes, authored entity/statblock, Play, combat, or general Graph Review successor was silently implemented.
* [ ] Every acceptance guarantee is proved at its owning boundary.
* [ ] Every changed path is in §4 or the bounded discovery report.
* [ ] Baseline failures and evidence provenance are reported truthfully.
* [ ] The authoritative handoff survived dispatch without omitted constraints.

---

## §10 Reviewer protocol

Review the publication invariant before reviewing individual files.

1. Restate the mission and invariant.
2. Confirm the implementation base includes `cec9834f` and the docs re-anchor.
3. Compare the actual diff with §§0, 3, 4, and 5.
4. Search for a hidden second capability or durable contract.
5. Inspect the exact serialized browser request.
6. Confirm forbidden operator fields are rejected, not merely ignored.
7. Trace the server-owned principal, live-world policy, and idempotency policy.
8. Trace the commit point through existing extract/promote ops and Kernel publication.
9. Audit stale, duplicate, pre-commit failure, post-commit degradation, and ambiguous-response paths.
10. Verify no success state can be reached from HTTP status alone.
11. Verify the exact committed revision is reloaded and checked.
12. Verify affected objects use durable IDs.
13. Verify preview state cannot masquerade as committed state.
14. Verify refresh failures do not cause a second confirmation.
15. Inspect save/reload and service restart behavior.
16. Compare base/head results for failing required gates.
17. Confirm live dogfood evidence is real and provenance-labeled.
18. Confirm PR011B and other successors remain false.
19. Leave a finding for every invariant failure, even when the immediate line appears locally reasonable.
20. Do not approve based solely on the author’s claimed test counts.

---

## §11 Re-review protocol

Begin every re-review from the prior finding ledger.

For each previous finding:

```text
Finding:
Original failure:
New implementation:
Owning proof:
Status:
- fixed
- partially fixed
- not fixed
- replaced by a new regression
```

Then perform a fresh full-invariant pass.

Specifically re-check:

* exact request serialization;
* forbidden product fields;
* proposal/run generation binding;
* selection freezing;
* stale proposal behavior;
* exact retry idempotency;
* no duplicate revision;
* published-but-audit-degraded behavior;
* post-confirm catalog refresh;
* exact committed-revision reload;
* durable-ID opening;
* preview-versus-durable presentation;
* server/browser reload;
* no successor leakage;
* test and dogfood provenance.

A corrected finding is not enough for approval if the fix introduces a replacement path that can silently misreport publication truth.

---

## Stop conditions

Stop and report before continuing when any of the following occurs:

1. The implementation base does not contain PR011A2 merge `cec9834f`.
2. The tracker or roadmap does not show A1/A2 done and A3 next.
3. The existing prepare response does not contain enough sealed authority to confirm without browser paths.
4. The existing confirm operation cannot distinguish pre-commit failure from known post-commit degradation.
5. The existing World Graph read API cannot load or prove one exact committed revision.
6. Exact affected durable object IDs cannot be projected without modifying Kernel identity or contribution semantics.
7. Safe exact retry requires a new persisted idempotency or operation-history store.
8. Truthful post-confirm state requires a new durable run-completion schema rather than existing graph/contribution authority.
9. A new backend production path outside §4 is required.
10. A new graph storage, identity, merge, proposal, or contribution contract is required.
11. Live proof requires automatic publication, a new management surface, or a browser `allowLiveWorld` control.
12. The Session 25 source does not support the claimed Hesta/apothecary objects and the implementation attempts to fabricate them.
13. Hermes, statblock, Play, combat, or generic authoring work becomes necessary to complete confirmation.
14. A required baseline gate fails differently on head and the change cannot be classified.
15. The agent cannot distinguish whether a failure occurred before or after the commit point.

A stop report must include:

```text
Discovered fact:
Why the current mission cannot safely absorb it:
New public/durable contract required:
Affected observable paths:
Affected ownership layers:
Paths required outside §4:
Proposed successor slice:
Operator decision required:
```

Do not widen the branch silently.

---

## Optional PR-body summary

```markdown
## Outcome

A GM can confirm a prepared Graph Review proposal so that exactly the selected
assertions become durable, reloadable campaign memory at one truthful committed
World Graph revision.

## Scope and verification

- Base: `<DOCS_REANCHOR_SHA>`
- Predecessors: #363, #364, #365
- Product confirm request: sealed review package + selected assertion IDs only
- Server-owned: principal, live-world policy, dry-run=false, idempotent retry
- Completion: committed revision receipt → revision-pinned reload → durable object
- Verification: route/service failure matrix, component workflow, isolated-world
  end-to-end proof, Session 25 dogfood
- Baseline failures and waivers: `<none or exact details>`
- Deferred successors: PR011B, authored entity/statblock, PR009 Play/combat
```

---

```text
STOP AFTER OPENING THE PR.

REQUEST REVIEW.

DO NOT BEGIN PR011B, AUTHORED ENTITY/STATBLOCK WORK, PLAY MIGRATION, OR COMBAT
INTEGRATION FROM THIS BRANCH.
```
