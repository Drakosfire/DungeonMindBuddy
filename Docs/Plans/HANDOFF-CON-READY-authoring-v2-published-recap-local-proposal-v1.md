# HANDOFF — CON-READY: Authoring v2 published-recap local proposal

**Created:** 2026-09-19  
**Status:** ACTIVE — V2-0 census passed; one bounded V2-1 implementation capability  
**Canonical handoff path:** `Docs/Plans/HANDOFF-CON-READY-authoring-v2-published-recap-local-proposal-v1.md`  
**Conversation/workstream:** `CON-READY / DOGFOOD-CONTINUITY / campaign memory authoring`  
**Flow / owner:** `CON-READY`  
**Direction:** DESIGN → CODE → REVIEW  
**Design authority base:** `main@11c1c4a469b509d9f8a2286f74f5ff087122fcbd` — V2-0 census landed  
**Activation gate:** `none — satisfied`  
**Dispatch base rule:** fresh current `main` containing this checked-in handoff; record the exact implementation branch base at dispatch/review  
**PR topology:** `serial` within CON-READY; unrelated open E5C PR #736 is a separate lane with no expected V2-1 path overlap  
**PR authorization:** open/update exactly this one assigned V2-1 implementation PR without asking; no successor/repair PRs  
**PR title:** `CON-READY: stage source-grounded proposals from published recap`  
**Proposed branch:** `con-ready/v2-1-published-recap-local-proposal-v1`

> Repository law: [`AGENTS.md`](../../AGENTS.md). Steward process: [`Docs/Process/STEWARD-CYCLE.md`](../Process/STEWARD-CYCLE.md). Parent sequencing authority: [`PLAN-CON-READY-authoring-v2-derived-gold-ablation-loop-v1.md`](PLAN-CON-READY-authoring-v2-derived-gold-ablation-loop-v1.md). V2-0 census: [`REPORT-CON-READY-authoring-v2-current-contract-census-v1.md`](../Reports/REPORT-CON-READY-authoring-v2-current-contract-census-v1.md).

---

## §1 Mission and merge-ready invariant

**Mission:** From ordinary published Campaign + Focus-session recap browse, the GM can highlight source prose or start from an existing graph pill and stage a truthful local `object`, `link_existing`, or `relationship` proposal, so semantic corrections can be expressed through the product before durable World commit is introduced.

**Merge-ready invariant:** **Published-memory browse remains non-write authority. Every V2-1 proposal is local-only, scoped to the exact campaign/session recap context, preserves only source identity actually supplied by the selected recap record, never fabricates a canonical evidence span, and cannot invoke graph-authoring prepare/commit, quick commit, merge materialization, or any World mutation. Switching campaign/session cannot leak one scope's staged proposals into another.**

### Pre-dispatch critique

| Question | Answer |
|---|---|
| Can one invariant govern every claimed observable path? | Yes — truthful source-contextualized local staging with zero durable write authority. |
| Most likely adversarial sequence | Stage C2/S27 proposal → switch to C1/S16 → stale C2 draft appears or can be staged under C1 identity; then switch back and original C2 draft is lost. |
| Will §7 actually detect that failure? | Yes — focused scope-switch/sessionStorage regression plus published-browse integration assertions. |
| Easiest owning boundary to under-test | The seam between `RecapArtifactRecord` source identity, `GraphAuthoringSelection`, and draft storage rehydration. |
| What PR topology is authorized, and why is it safe? | Serial in CON-READY. One V2-1 PR only. E5C #736 is unrelated and does not lease the expected frontend paths. |
| Fact that forces stop/split | Any required backend write/source-admission change; any need to synthesize `sourceSpanRefId`; any requirement to make ordinary browse acquire `ExplicitAuthoringAuthority`; any durable negative/ambiguity schema. |

---

## §2 Context, authority, lane, and PR topology

| Field | Required content |
|---|---|
| Parent authority | `PLAN-CON-READY-authoring-v2-derived-gold-ablation-loop-v1.md` |
| Design authority base | `main@11c1c4a469b509d9f8a2286f74f5ff087122fcbd` |
| Activation gate | none — V2-0 census PASS |
| Dispatch base rule | fresh current `main` containing this ACTIVE handoff |
| Predecessor contract | `REPORT-CON-READY-authoring-v2-current-contract-census-v1.md` |
| Exact input consumed | ordinary `RecapGraphModule` published-memory context + selected `RecapArtifactRecord` + `WorldGraphRecapProjection` + existing `GraphAuthoringSelection` / local proposal primitives |
| Named successor | V2-2: explicit source/write authority → existing governed `/api/live/graph-authoring/prepare` → `commit` → immutable World revision |
| What remains false | no durable World write; no prepare/confirm; no canonical evidence binding when recap projection has no authoritative span; no negative/ambiguity durable adjudication |
| Explicit non-goals | merge_objects; merge reconciliation; Agent/model assistance; extraction changes; derived gold export; generalized graph editor; Stage 4 UI polish |
| PR topology | serial |
| Authorized PR action | open/update exactly this assigned V2-1 PR; no additional PRs |
| Open implementation PRs in CON-READY at design time | none |
| Concurrent repository PR checked | #736 E5C; backend/dependency paths only, no expected V2-1 frontend lease overlap |
| Stack parent + merge/rebase order | not applicable |
| Branch / isolated checkout | `con-ready/v2-1-published-recap-local-proposal-v1` + isolated checkout/worktree |
| Runtime/state ownership | local Vite/Vitest browser state only; `sessionStorage` keys namespaced by campaign + session |
| State-authority sync set after merge | this handoff completion status; `PLAN-CON-READY-authoring-v2-derived-gold-ablation-loop-v1.md`; canonical + design-agent `STEWARDS-ANCHOR-con-ready.md` |

### Governing census findings

The V2-0 census established:

```text
PublishedMemoryBrowseContext != GraphReviewWriteAuthority

ordinary published recap:
  source-contextualized local proposal = allowed

ordinary published recap:
  prepare/commit = forbidden in V2-1
```

The existing governed write seam is already known and reserved for V2-2:

```text
POST /api/live/graph-authoring/prepare
→ POST /api/live/graph-authoring/commit
→ DungeonMind immutable World revision
```

V2-1 must not modify or bypass it.

---

## §3 Observable paths and adversarial sequences

| Path | Current behavior | Required behavior | Same §1 invariant? | Owning boundary |
|---|---|---|---:|---|
| Highlight ordinary published recap text | read-only selection has no authoring workflow | selection exposes a local Author memory action and can seed a local draft | Yes | `GraphProjectionReader` + published recap authoring host |
| Existing graph pill | opens campaign-memory Peek | pill can also seed local authoring from its exact existing node identity without losing normal Peek behavior | Yes | published recap projection |
| Create object | exact-run Author Draft can quick-commit; ordinary browse cannot author | ordinary browse stages `object` locally only | Yes | local authoring host + `useGraphObjectAuthoringDraft` |
| Link existing | resolver ancestry exists | selected text can resolve and stage `link_existing` locally | Yes | `GraphObjectAuthoringSurface` / resolver |
| Relationship | exact-run authoring stages relationship | ordinary browse can stage relationship locally from existing/local refs | Yes | local authoring host |
| Review staged proposals | ordinary browse has none | staged proposals are visible/removable and explicitly labeled local/not committed | Yes | staging tray |
| Campaign/session switch | published recap changes context; draft hook ancestry assumes stable scope | current selection clears; destination scope loads only its own stored proposals; returning restores the original scope's drafts | Yes | authoring host + draft hook |
| Source identity | recap projection exposes no canonical source spans | preserve selected recap record path/artifact id/hash when supplied; `sourceSpanRefId` remains null unless authoritative input supplies one | Yes | recap module → selection context |
| Write attempts | published browse has `writeAuthority=null` | still null; no prepare/commit/quick-commit call is reachable from V2-1 UI | Yes | workbench authority + local host |

Adversarial proof sequences:

| Sequence | Required safe outcome | Owning §7 proof |
|---|---|---|
| C2/S27 select text → stage object → C1/S16 | no C2 proposal shown or re-labeled as C1; selection reset | scope-switch integration test |
| C2/S27 → C1/S16 → back to C2/S27 | original C2 local draft rehydrates from C2/S27 storage key | draft persistence regression |
| selected recap record has `source_artifact_id=null` but has path/hash | proposal preserves path/hash and null artifact id; no invented id/span | source-context unit/integration assertion |
| click existing pill → author → stage link/relationship | exact existing node id/label preserved; normal Peek remains available | published-recap component test |
| stage any proposal from ordinary browse | no `graph-authoring/prepare`, `graph-authoring/commit`, quick-commit, or merge materialization API call | integration spy regression |

---

## §4 Files in scope — write lease

| Action | Path | Purpose |
|---|---|---|
| Modify | `apps/live-control-ui/src/planSurface/graphPreview/RecapGraphModule.tsx` | retain/pass exact selected `RecapArtifactRecord` source identity with published recap |
| Modify | `apps/live-control-ui/src/planSurface/graphPreview/WorldGraphRecapProjection.tsx` | enable source/pill authoring entry points and host local proposal workflow without changing Peek behavior |
| Create | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/PublishedRecapLocalAuthoring.tsx` | local-only authoring composition; no write-authority or commit APIs |
| Modify | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphObjectAuthoringSurface.tsx` | support truthful local-stage-only labels/controls without changing exact-run default semantics |
| Modify | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/graphAuthoringSelection.ts` | preserve optional `sourceArtifactId` alongside path/hash through local selection context; include it in equality/context identity |
| Modify if needed | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/useGraphObjectAuthoringDraft.ts` | make scope changes rehydrate/reset safely instead of retaining stale proposals |
| Modify | `apps/live-control-ui/src/planSurface/graphPreview/RecapGraphModule.test.tsx` | prove source-record continuity and ordinary published browse integration |
| Modify | `apps/live-control-ui/src/planSurface/graphPreview/WorldGraphRecapProjection.test.tsx` | prove highlight/pill → local proposal and no loss of normal Peek |
| Create | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/PublishedRecapLocalAuthoring.test.tsx` | focused local-only workflow and no-write proof |
| Modify | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/useGraphObjectAuthoringDraft.test.ts` | prove campaign/session storage isolation + rehydration |
| Modify | `apps/live-control-ui/src/planSurface/graphProjectionReader/GraphProjectionReader.test.tsx` | prove shared reader selection preserves exact optional source artifact id/path/hash and existing authoring behavior |
| Modify | `Docs/Plans/HANDOFF-CON-READY-authoring-v2-published-recap-local-proposal-v1.md` | implementation/review evidence and completion handback |
| Modify | `Docs/Plans/PLAN-CON-READY-authoring-v2-derived-gold-ablation-loop-v1.md` | backward-looking V2-0 sync / current V2-1 state only |
| Modify | `Docs/Plans/STEWARDS-ANCHOR-con-ready.md` | backward-looking V2-0 sync / current V2-1 state only |
| Modify | `Docs/Sources/design-agent/ACTIVE_AUTHORITY/STEWARDS-ANCHOR-con-ready.md` | byte-identical authority mirror |

**Bounded discovery exception:**

```text
Directory:
  apps/live-control-ui/src/planSurface/graphReviewWorkbench/
  apps/live-control-ui/src/planSurface/graphPreview/

Maximum additional paths:
  3

Allowed path kinds:
  focused component/helper tests or one narrowly extracted local-authoring helper

Decision rule:
  only when required to prove or isolate the §1 local-only invariant;
  no API/server/contracts paths and no write-authority paths.
```

A required backend or API-client change is a stop report, not bounded discovery.

---

## §5 Explicitly out of scope / collision boundary

| Path | Why this slice must not touch or claim it |
|---|---|
| `apps/live_control_server/routes/graph_authoring.py` | governed write authority already exists; V2-2 consumer |
| `apps/live_control_server/services/graph_object_authoring_prepare.py` | no prepare semantics change in V2-1 |
| `apps/live_control_server/services/graph_object_authoring_commit.py` | no commit semantics change in V2-1 |
| `apps/live_control_server/integrations/dungeonmind/world_graph_writes.py` | DungeonMind World publication is V2-2 |
| `apps/live-control-ui/src/planSurface/graphReviewWorkbench/useGraphObjectAuthoringQuickCommit.ts` | ordinary published browse must not quick-commit |
| `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphObjectAuthoringPrepareCommitPanel.tsx` | ordinary published browse must not prepare/commit |
| merge/materialization components | `merge_objects` is not native V2-1 vocabulary |
| extraction / model / prompt paths | V2-4 parked behind derived gold |
| gold fixture authoring paths | derived gold is V2-3; do not revive gold-first authoring |

Do not add a hidden write flag, manufacture `ExplicitAuthoringAuthority`, or pass dummy `sourceRunId` merely to reuse write-capable controls.

---

## §6 Implementation contract

```text
Input:
  PublishedMemoryBrowseContext
  selected RecapArtifactRecord for the exact campaign/session
  WorldGraphRecapProjection
  GraphAuthoringSelection including optional sourceArtifactId/path/hash
  existing GraphObjectAuthoringProposal primitives

Output:
  local staged proposals only:
    object
    link_existing
    relationship

Invariant:
  source-contextualized local proposal != canonical evidence-bound World contribution

Failure behavior:
  recap source metadata absent/partial
    → preserve only fields actually supplied; never synthesize canonical span/id

  resolver unavailable
    → creation/relationship local drafting remains usable where possible;
      link-existing reports resolver failure without changing write authority

  campaign/session changes
    → clear pending selection and rehydrate destination-scope proposals only

  write-capable dependency accidentally supplied
    → V2-1 presentation still does not render/invoke prepare/commit or quick commit
```

### Persistence / replay matrix

| Operation | Durable representation | Round-trip guarantee | Duplicate/replay | Compatibility/migration | Rollback/reversion |
|---|---|---|---|---|---|
| stage local proposal | browser `sessionStorage` under `graph-object-authoring-staged:{campaignId}:{sessionId}` | same scope remount restores staged proposals | preserve current local ids; no World idempotency claim | existing staged proposal union only | remove proposal or clear browser session |
| switch scope | destination campaign/session key | proposals from previous scope never appear under new scope | revisiting old scope restores its own list | no storage schema migration in V2-1 | switch back / remove proposals |

### Source identity mapping

| Source field | V2-1 mapping | Rule |
|---|---|---|
| `RecapArtifactRecord.campaign_id` | `GraphAuthoringSelection.campaignId` | exact |
| `RecapArtifactRecord.session_id` | `GraphAuthoringSelection.sessionId` | exact |
| `source_recap_path` | `sourceArtifactPath` | exact value; do not parse identity from path |
| `source_sha256` | `sourceArtifactSha256` | exact value when supplied |
| `source_artifact_id` | `GraphAuthoringSelection.sourceArtifactId` | exact optional value; add the nullable field rather than dropping or synthesizing identity |
| canonical source span | `sourceSpanRefId` | null unless already authoritative input supplies it |
| Tiptap offsets / paragraph ordinal | local interaction context only | not canonical evidence identity |

---

## §7 Evidence required to merge

| Guarantee / invariant clause | Owning boundary | Evidence class | Command or manual scenario | Expected evidence | Stop condition |
|---|---|---|---|---|---|
| highlight → local object proposal | published recap component | regression | focused Vitest | object proposal staged; source text/context present | action requires exact run/write authority |
| existing pill → local proposal | published recap component | regression | focused Vitest | existing node id/label preserved; Peek still works | pill authoring breaks inspection |
| link-existing remains local | authoring surface/resolver | regression | focused Vitest with API spies | staged `link_existing`; no prepare/commit | any durable write call |
| relationship remains local | local authoring host | regression | focused Vitest | staged relationship visible/removable | quick commit or prepare path reachable |
| scope isolation | draft hook + host | adversarial regression | C2 → C1 → C2 test | no cross-scope bleed; old scope restores | stale proposal visible under wrong scope |
| no fabricated evidence | source mapping | contract regression | null artifact/span fixture | null stays null; path/hash exact | synthesized span/id |
| published browse stays non-write | workbench integration | authority regression | existing + new focused tests | `data-write-authority="none"`; no mutation calls | ordinary browse acquires write authority |
| frontend compiles | UI package | build | `pnpm --dir apps/live-control-ui build` | pass | new build/type failure |
| focused tests | UI package | test | command below | pass | any V2-1 regression |
| diff hygiene | repository | static | commands below | clean/leased paths only | unexpected changed path |

Exact verification commands:

```bash
pnpm --dir apps/live-control-ui test --   src/planSurface/graphPreview/RecapGraphModule.test.tsx   src/planSurface/graphPreview/WorldGraphRecapProjection.test.tsx   src/planSurface/graphReviewWorkbench/PublishedRecapLocalAuthoring.test.tsx   src/planSurface/graphReviewWorkbench/useGraphObjectAuthoringDraft.test.ts

pnpm --dir apps/live-control-ui build

git diff --check
git diff --name-only <dispatch-base>...HEAD
```

### Minimal dogfood proof

```text
Existing surface:
  /ingest ordinary Campaign + Focus-session published recap

Smallest realistic scenario:
  open a known C1/C2 recap
  highlight one semantically wrong/thin phrase
  stage a new-object or link-existing proposal
  stage one relationship if appropriate
  switch campaign/session and return

Expected observation:
  proposal is clearly local/not committed
  exact source text + campaign/session/source artifact context remain visible
  no World memory changes
  destination scope does not show the original proposal
  returning restores the original local proposal
```

No V2-1 merge claim depends on a backend World revision.

---

## §8 Required review handback

Record:

1. `Review Cycle <N>` and exact PR/branch/head SHA;
2. exact implementation branch base;
3. open PR topology at dispatch and review;
4. §1 mission/invariant disposition;
5. actual source-identity fields preserved from `RecapArtifactRecord`;
6. proof that `sourceSpanRefId` was not fabricated;
7. proof that no prepare/commit/quick-commit/merge-materialization call is reachable;
8. C2 → C1 → C2 scope-switch result;
9. focused test/build results with provenance;
10. actual changed paths vs §4 / bounded discovery;
11. named V2-2 successor still false;
12. any baseline failure or waiver.

---

## §9 Acceptance rubric

- [ ] ACTIVE handoff was checked in before implementation dispatch.
- [ ] One V2-1 PR only; topology remained serial within CON-READY.
- [ ] Ordinary published recap supports highlight → local object proposal.
- [ ] Existing graph pill can seed local authoring without breaking Peek inspection.
- [ ] Existing-object resolution can stage `link_existing` locally.
- [ ] Relationships can be staged locally.
- [ ] Staged proposals are visibly local/uncommitted and removable.
- [ ] Campaign/session scope switching cannot leak proposals across storage scopes.
- [ ] Exact recap source path/hash/artifact identity is preserved when supplied.
- [ ] No canonical `sourceSpanRefId` is invented.
- [ ] Published browse remains `GraphReviewWriteAuthority = null`.
- [ ] No graph-authoring prepare/commit, quick commit, merge materialization, World write, gold export, Agent, or extraction work is introduced.
- [ ] Focused tests + UI build + diff hygiene pass or baseline failures are truthfully documented.
- [ ] Actual changed paths remain within §4 / bounded discovery.
- [ ] V2-2 remains the named successor.

## Stop conditions

Stop and return to the steward if:

- a backend/API contract change is required;
- current published recap cannot supply enough truthful source identity for local staging;
- the only viable implementation makes ordinary browse writable;
- `sourceSpanRefId` would need to be derived from offsets/path/labels;
- local staging requires `sourceRunId` or another fake exact-run identity;
- `merge_objects`, negative/source-only, ambiguity, gold export, or Agent assistance becomes required for the slice to be useful;
- the draft storage hook cannot safely isolate campaign/session scope without a second persistence contract;
- another active lane acquires a §4 path before dispatch/review.

Report the affected invariant, path, and proposed split rather than absorbing the successor.
