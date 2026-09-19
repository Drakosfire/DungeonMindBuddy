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

## Implementation record (pre-review)

**Dispatch base:** `026fd546cb564f3262dbbe6aaf94fc1cee6df84a` (`origin/main` at dispatch)  
**Rebased onto:** `main@bdcabc513b7cb7f68aa5198c4932d92815fbf871` after E5D `#737` merge (no §4 frontend overlap)  
**PR:** [#738](https://github.com/Drakosfire/DungeonMindBuddy/pull/738)  
**PR topology at dispatch:** serial within CON-READY  
**Bounded discovery used (2 of 3):**
- `apps/live-control-ui/src/planSurface/graphReviewWorkbench/useGraphAuthoringSelection.ts` — include `sourceArtifactId` in authoring context identity (original V2-1)
- `apps/live-control-ui/src/planSurface/graphReviewWorkbench/graphAuthoringSelection.test.ts` — original V2-1 proof of selection/source identity; omitted from the pre-review implementation record (review cycle 1 correction)

`GraphObjectAuthoringStagingTray.tsx` was temporarily modified in review cycle 1 to add `data-*` observability. Review cycle 2 rejected that as outside §4 and outside the focused-test / extracted-helper discovery allowance. The production file is reverted. Identity proof now inspects the scoped `sessionStorage` JSON from `PublishedRecapLocalAuthoring.test.tsx`.

### Review cycle 1 (2026-09-19)

**Head reviewed:** `4697f1ed44aea755278d51a9ecb35d055ea168c5`  
**Formal GitHub review:** not posted. The connected account is also the PR author; GitHub rejected `REQUEST_CHANGES` on own PR. The review is still complete as steward judgment.

**Invariant disposition:** local-stage / non-write contract held. Visible authoring UI stays in V2-1. Operator dogfood findings remain successor design evidence, not work to strip from this PR.

**Merge blockers (repaired on this head's successor commits):**

1. Campaign/session switch could pair the previous recap payload with the new authoring scope, and `loadRecapProjection` had no stale-response guard. Repair: immediately invalidate/clear the loaded projection on scope change so it is non-authorable, and ignore late responses whose generation no longer matches.
2. Manual draft and relationship staging could create proposals without recap path/hash/optional artifact id. Repair: those controls remain; they now copy exact supplied recap identity and leave `sourceSpanRefId` null. Cycle 2 identity proof inspects the persisted proposal selection in scoped `sessionStorage`, including a non-null `source_artifact_id` case.

**UX findings:** keep the current visible UI for continued dogfood. Do not fold Surface Context, Author Node chip composition, Karsemine identity-vs-alias, existing-node edit, or duplicate merge into these two correctness repairs.

### Review cycle 2 (2026-09-19)

**Head reviewed:** `d6e05bb16f840b53691043732709710ece5f0805`  
**Formal GitHub review:** [#738 review `5257362094`](https://github.com/Drakosfire/DungeonMindBuddy/pull/738#pullrequestreview-5257362094) — HOLD

**Cycle 1 blockers:** fixed. Campaign/session transitions immediately make the previous recap non-authorable and reject stale projection responses. Manual-object and relationship proposals retain supplied recap path/hash/artifact ID with `sourceSpanRefId=null`. Visible authoring UI remains.

**Remaining blocker (repaired on this head's successor commits):** `GraphObjectAuthoringStagingTray.tsx` was modified outside §4. Adding `data-*` fields for test observability is not a focused test or a narrowly extracted helper. Repair: revert the production file; `PublishedRecapLocalAuthoring.test.tsx` asserts the actual persisted proposal selection in scoped `sessionStorage`.

**Non-blocking cleanup also landed:** close the malformed §7 Markdown fence around build evidence; update `buildManualGraphAuthoringSelection` comment so it no longer claims “no recap grounding.”

**UX findings:** successor design evidence only. V2-2 remains unauthorized.

### Source identity actually preserved

| RecapArtifactRecord | GraphAuthoringSelection |
|---|---|
| `campaign_id` | `campaignId` |
| `session_id` | `sessionId` |
| `source_recap_path` | `sourceArtifactPath` |
| `source_sha256` | `sourceArtifactSha256` |
| `source_artifact_id` | `sourceArtifactId` (nullable; never synthesized) |
| canonical span | `sourceSpanRefId` remains null unless already on the selection |

### Write-authority proof

`PublishedRecapLocalAuthoring` exposes `data-write-authority="none"`. `GraphObjectAuthoringSurface` `localStageOnly` never renders `GraphObjectAuthoringPrepareCommitPanel`, even if campaign/session ids are present for the resolver. Focused tests spy `prepareGraphObjectAuthoringWrite` and `commitGraphObjectAuthoringWrite`. Quick-commit and merge materialization are not imported.

### C2 → C1 → C2

`useGraphObjectAuthoringDraft` rehydrates/resets on campaign/session key change and does not write the previous scope's proposals onto the destination key.

`RecapGraphModule` also keeps loaded recap and authoring scope atomic: a campaign/session change immediately clears the previous projection (non-authorable loading chrome remains), and stale `postWorldGraphRecapProjection` responses are ignored.

### §7 commands

```text
vitest run RecapGraphModule.test.tsx WorldGraphRecapProjection.test.tsx
  PublishedRecapLocalAuthoring.test.tsx useGraphObjectAuthoringDraft.test.ts
  graphAuthoringSelection.test.ts GraphProjectionReader.test.tsx
  GraphObjectAuthoringSurface.test.tsx
→ 7 files, 83 passed
  (GraphObjectAuthoringSurface 35; remaining 48; exact-run default semantics unchanged)

pnpm --dir apps/live-control-ui build
→ tsc fails on pre-existing unused locals in GraphReviewWorkbenchModule.tsx
  (out of lease; same unused bindings exist on dispatch-base main).
  No new tsc errors in §4 / bounded-discovery files.
```

V2-2 remains the named successor and is not authorized.

### Operator dogfood findings — review-time design exploration, not V2-1 merge blockers

Recorded 2026-09-19 on `/ingest?campaign=longmont-c2&session=session-27` against this PR's UI. These are **feel / composition / identity-vocabulary** findings. They do **not** by themselves falsify the V2-1 local-stage invariant. **Do not expand #738** into Surface Context, Author Node, existing-node edit, Peek kinds, or merge. **Do not remove the visible authoring UI** to “fix” review; that UI is how dogfood exposed the composition problems. Review cycle 1 confirmed this: keep highlight → Author graph, local staging form, resolver, relationship controls, and staged-proposal tray in V2-1. The two merge blockers above are separate correctness repairs.

#### What landed and was accepted

- Highlighting recap prose immediately surfaces **Author graph object**. That trigger is correct. Keep it.
- Bind or Create **does recognize** a known node (Karsemine). Matching existing campaign objects is valuable; the verb and destination are what are wrong.
- Clicking an existing pill still opens Peek. Keep that inspect path. It also silently seeds the local draft with the node id/label, but that is not a visible **edit this node** affordance.

#### Placement: the author action sits under the campaign loader

Current published-recap stack:

```text
site nav + World Graph chrome
SurfaceContextHost          ← empty on Ingest
CENTER:
  recap-reader-toolbar      ← Campaign + Focus session
  Author graph object       ← appears here on highlight
  recap markdown
  GraphObjectAuthoringSurface  ← the actual form, below the prose
```

The operator's intended home is the **per-surface sub-nav** already in the product as **Surface Context** (`SurfaceContextHost` under `app-chrome-header`). Plan publishes `PREP`. Build publishes `DOCUMENT`. Ingest publishes nothing, so campaign loading, session selection, surface name, and interactive actions (Author graph / bind-or-create) remain in the recap body.

Review should treat this as chrome composition, not a V2-1 write-path defect:

| Band | Owns |
|---|---|
| World Graph in site nav | what world is available |
| Surface Context | what this surface has loaded + its actions |
| Center | recap prose only |

Campaign, Focus session, surface name (`INGEST` / recap), and the highlight action belong in Surface Context, not in `recap-reader-toolbar` / `graph-authoring-selection-action-bar`.

#### Workflow: Author graph does not change the view

Clicking **Author graph object** calls `draft.openWithSelection` on `PublishedRecapLocalAuthoring`. Nothing in the viewport moves. The form is `GraphObjectAuthoringSurface` stacked **under the markdown**, so the operator must scroll past the recap to interact. That is confusing and not intuitive.

Exact-run already owns **Author Node** (`GraphReviewAuthorNodeHost` / `GraphReviewAuthorNodeDrawer`) as a chrome-band drawer. Published browse already wraps `RecapGraphModule` in that host, but `GraphReviewAuthorNodePanel` refuses to open a workflow without `liveRun` (`Authoring requires an explicit source/run context.`). V2-1 bypassed the empty drawer by inlining the form under the recap. That is why the toggle exists and still does not help.

Operator direction to explore (do not implement in this PR):

```text
highlight phrase
  → small decision chip / compact peek
      known-node matches
      + Create new
  → Create new
      → open Author Node workflow
      → not a form below the markdown
```

Keep three existing surfaces. Do not invent a fourth:

| Moment | Surface |
|---|---|
| Highlight a phrase | Compact bind/create chip (near the selection or in Surface Context) |
| Phrase *is* a known node | Chip names the node; Peek remains inspect; Author / edit that existing node should also be available |
| Phrase is a different name | Chip offers alias bind |
| Create new | Author Node drawer, seeded with the highlight, still local-only |

Do **not** put bind/create into the full Peek region. Peek is already the world-object / campaign-memory card (`PeekClaim kind="world-object"`). A second Peek for suggestions will fight pill inspect.

Author Node may open for **local staging** from ordinary published recap without granting prepare/commit. The current `liveRun` empty state conflates **write authority** with **drawer usefulness**. Exact-run write remains the later gate.

#### Identity: Karsemine is that node, not an alias

Authoring Karsemine from highlighted recap text:

- Bind or Create finds the known node. Keep that recognition.
- The only bind verb is **Add as alias** (`GraphObjectAuthoringBindExistingPanel`). Copy says “Most of the time this is an alias of an existing node.”
- That verb is for a *different string* attached to an existing node. Highlighting **Karsemine** when Karsemine is already in the graph is **identity**: that *is* the node.
- Clicking the Karsemine **pill** already does the right thing (Peek the existing object). Highlighting the same name in prose currently takes the alias/create path instead.

The World graph currently has **Karsemine as PC** and **Karsemine as character**. Those are duplicate identity records. They should stay visible as two known nodes and wait for **merge**. Alias-linking will not collapse them. `merge_objects` remains out of V2-1 vocabulary and is not required for this slice to prove local staging.

Default vocabulary to explore after merge:

```text
exact selected text = an existing node's primary label
  → "this is that node" (inspect / Peek), not Add as alias

selected text ≠ canonical label, resolver match
  → alias bind is legitimate

two same-name nodes (PC vs character)
  → show both; merge later; do not pick a winner via alias
```

#### Existing nodes should be authorable, not only new highlights

A later dogfood note on the same published-recap surface: **node editing and authoring should be available on existing nodes as well.**

Current V2-1 is biased toward **create from highlighted prose**. An existing pill still Peeks (correct) and `handleInspectNode` silently `openWithSelection`s that node's identity plus relationship seed, but Peek itself is inspect-only, the form stays below the markdown, and Bind or Create on a matching name still offers alias/create rather than **edit this node**. There is no visible authoring entry on the existing object comparable to highlight → Author graph.

Operator direction to explore (do not implement in this PR):

```text
existing pill / known-node chip / identity match
  → Peek remains inspect
  → Author / edit that existing node is also available
      same Author Node / local-stage workflow as Create new
      seeded with exact node id/label
      still no prepare/commit from published browse
```

This is the same composition family as the chip → Author Node and Karsemine identity notes: existing-object edit vs new-object create. Do not fold it into the two review-cycle-1 correctness repairs.

#### Seams to inspect on the #738 diff (read-only during this review)

- `WorldGraphRecapProjection.tsx` / `RecapGraphModule.tsx` — in-document `recap-reader-toolbar`
- `PublishedRecapLocalAuthoring.tsx` — reader then `GraphObjectAuthoringSurface`; `onGraphAuthoringAction` does not open Author Node or scroll/focus; pill inspect silently seeds a draft but is not a visible existing-node edit path
- `GraphProjectionReader.tsx` — inline **Author graph object** bar
- `GraphObjectAuthoringBindExistingPanel.tsx` / `GraphObjectAuthoringSelectedSource.tsx` — alias-first copy; only bind action is Add as alias
- `GraphReviewAuthorNodeHost.tsx` / `GraphReviewAuthorNodePanel.tsx` — drawer already mounted on published browse; `liveRun` gate
- `SurfaceContextHost` — Ingest contributes nothing; Plan/Build already do

#### Review disposition

Judge #738 against the §1 local-stage invariant and §9 rubric. Record these findings in the review handback as **successor design evidence**, not as required #738 code changes, unless a finding actually violates non-write / source-identity / scope-isolation.

Do not dispatch V2-2, Surface Context, Author Node local-stage, or merge from this note. After #738 merges and the workstream is re-anchored, the designing steward decomposes the next independently useful slice from this evidence.

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
13. operator dogfood findings disposition: invariant-failing vs successor design evidence (see Implementation record).

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
