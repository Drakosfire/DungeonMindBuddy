# HANDOFF — CON-READY: Authoring v2 governed World commit

**Created:** 2026-09-20  
**Status:** ACTIVE — one governed published-recap write capability  
**Canonical handoff path:** `Docs/Plans/HANDOFF-CON-READY-authoring-v2-governed-world-commit-v1.md`  
**Conversation/workstream:** `CON-READY / DOGFOOD-CONTINUITY / campaign memory authoring`  
**Flow / owner:** `CON-READY`  
**Direction:** DESIGN → CODE → TEST → TARGETED DOGFOOD → REVIEW  
**Design authority base:** `main@28754d1fdda15be97475f35e08127833b088a256` — V2-1A / PR #741 merged  
**Activation gate:** satisfied — PR #741 merged; Review Cycle 3 PASS / MERGE-READY; no open implementation PRs at design re-anchor  
**Dispatch base rule:** fresh current `main` containing this checked-in handoff and the completed-V2-1A state sync; record the exact implementation branch base at dispatch/review  
**PR topology:** `serial` within CON-READY  
**Authorized branch:** `con-ready/authoring-v2-governed-world-commit-v1`  
**Authorized PR title:** `CON-READY: publish staged recap memory to World`  
**PR authorization:** open/update exactly one implementation PR for this capability; no derived-gold, extraction ablation, merge/reconciliation, or Agent-authoring successor PR  
**Named successor:** V2-3 — derive evaluation gold from committed human adjudication

> Repository law: `AGENTS.md`. Steward process: `Docs/Process/STEWARD-CYCLE.md`. Sequencing authority: `Docs/Plans/PLAN-CON-READY-authoring-v2-derived-gold-ablation-loop-v1.md`. V2-1A authority/evidence: `Docs/Plans/HANDOFF-CON-READY-authoring-v2-working-projection-ui-dogfood-v1.md` and `Docs/Reports/REPORT-CON-READY-authoring-v2-working-projection-ui-dogfood-v1.md`.

---

## §1 Mission and merge-ready invariant

### Mission

Turn the published-recap Author Node workflow from a local working projection into an explicit governed World-write loop.

The GM must be able to stage an ordinary `object`, `link_existing`, or `relationship` proposal while reading a published recap, deliberately choose **Review & publish**, inspect the exact prepared write, confirm it, and then observe the result as durable DungeonMind World memory.

This slice exists to reach real writes. It is not another UI-polish slice.

### Merge-ready invariant

> **From one selected published recap, the GM can explicitly prepare and confirm staged human proposals through the existing DungeonMind governed publication seam using a server-proven immutable recap source identity. A successful confirm publishes exactly one immutable World revision, returns the exact durable identities created, clears only the committed local proposals, and refreshes the same recap surface against committed World truth. Missing/drifted source authority, changed proposals, or a stale World parent fails closed without publishing. Canonical recap bytes are never mutated.**

The ordinary loop is:

```text
published recap
→ highlight phrase / inspect pill
→ stage local human proposal
→ local working projection changes
→ Review & publish
→ server resolves exact published recap source
→ prepare against current immutable World parent
→ operator inspects prepared change
→ explicit confirm
→ one DungeonMind World revision
→ committed local proposals clear
→ recap surface refreshes from World
→ created/changed durable memory is readable
```

This is the first product slice where the published-recap surface gains a deliberate durable-write transition.

### Same-label / duplicate identity rule

Creating a second object with the same label is **not** automatically a merge or a resolver failure.

If the operator deliberately chooses **Create new** and stages a new-object proposal despite an exact/similar existing label:

```text
same label
≠ same identity
≠ automatic merge
```

The governed write may create a distinct durable node ID. Existing overlap/identity warnings remain warnings unless current contract already makes that proposal invalid.

After refresh, the ordinary recap mention linker must preserve its current ambiguity safety: two nodes claiming the same surface must not cause an arbitrary pill winner. An ambiguity diagnostic / unlinked occurrence is truthful.

This behavior is intentionally useful for later ingestion-ablation adversarial cases. This PR does **not** add merge, delete, reconciliation, or duplicate cleanup.

---

## §2 Re-anchor facts, predecessor contract, and source-authority decision

### 2.1 Exact predecessor

At design re-anchor:

```text
main:
28754d1fdda15be97475f35e08127833b088a256

PR #741:
MERGED

accepted implementation head:
9b5874e9b30663d4008427acebdff03d7c6531ae

formal final judgment:
Review Cycle 3 — PASS / MERGE-READY
review id 5262735475

open implementation PRs:
none
```

V2-1A established:

- the published recap remains visible while Author Node is open;
- `object`, `link_existing`, and `relationship` proposals are local/reversible;
- the working projection reflects local proposals immediately;
- local objects are visibly local/uncommitted;
- root object prose and one-hop relationship expansion are usable;
- no prepare/commit path is reachable from published-local mode.

Those interaction semantics survive. V2-2 adds one explicit transition from that local state into existing governed publication.

### 2.2 Existing governed publication seam

The existing backend already owns the durable write protocol:

```text
POST /api/live/graph-authoring/prepare
→ source prove/admit
→ current World parent
→ signed publication intent
→ explicit confirm token

POST /api/live/graph-authoring/commit
→ re-resolve source
→ re-prove admitted source pair
→ stale-parent check
→ DungeonMind publish/recover
→ immutable child revision
→ created_node_ids for new object proposals
```

Do not create a second write protocol.

Existing exact-run Graph Review uses `sourceRunId` to resolve a promotable ingest run. That path remains valid and behaviorally unchanged.

### 2.3 Published-recap source selector decision

Published-recap authoring must **not** invent or select an extraction run merely to obtain write authority.

Add a first-class published-recap source selector:

```text
recapArtifactId
```

This is the server-owned `RecapArtifactRecord.artifact_id` already selected by the Recap surface, not a browser-supplied filesystem path and not the nullable canonical `source_artifact_id` field.

For an EXPRESSIBLE write, source selection is exactly one of:

```text
sourceRunId XOR recapArtifactId
```

Rules:

- `sourceRunId` → current exact-run behavior, unchanged.
- `recapArtifactId` → resolve the exact server-owned recap record; verify campaign/session; verify its registered source path/bytes/digest using existing recap/source-registry contracts; derive or load the deterministic recap `GraphMemorySourceArtifact`; then pass that source through the same existing DungeonMind source-admission authority used by Graph Review.
- both selectors → 422/409 fail closed; no source admission and no World write.
- neither selector for an expressible prepare → fail closed.
- the browser may send `recapArtifactId`; it may not supply a path/digest as publication authority.
- `GraphAuthoringSelection.sourceArtifactPath` and `sourceArtifactSha256` remain useful local/source context but do not become trusted write inputs.

If the existing recap-record digest contract and canonical `create_recap_source_artifact` digest contract disagree for real normalized recaps, STOP with the exact bytes/digests. Do not weaken source provenance to make the UI write.

### 2.4 Publication intent binding

The signed prepare intent must bind the chosen source selector strongly enough that confirm cannot swap:

- `sourceRunId`;
- `recapArtifactId`;
- campaign/session;
- admitted source artifact/revision;
- proposal digest;
- expected World parent.

Confirm re-resolves the same selected source and re-proves the sealed admitted pair before publication.

### 2.5 What read-back means in this slice

Two truths must not be conflated:

1. **Durable object truth:** a successful new-object commit returns `created_node_ids`; the exact returned node must exist at `published_revision_id` and be retrievable through ordinary World read/projection contracts.
2. **Recap mention navigation:** the recap projection links label/alias surfaces deterministically and is explicitly navigation-only. Unique new labels may become pills after refresh. Duplicate/ambiguous surfaces may correctly remain unlinked with an ambiguity diagnostic.

Do not invent canonical evidence-span bindings just to force a pill.

---

## §3 Observable paths and adversarial sequences

| Path | Current behavior | Required behavior | Same §1 invariant? | Owning boundary |
|---|---|---|---:|---|
| Published recap stages one new object | Local-only proposal + working projection | Same local behavior until operator explicitly chooses publish | Yes | published recap UI |
| Review & publish from published recap | Unavailable | Existing prepare UI is reachable with `recapArtifactId`; prepare does not advance World head | Yes | UI + prepare service |
| Prepare with valid recap record | Exact-run requires `sourceRunId` | Server resolves recap record → canonical recap source → source admission → current parent → signed intent | Yes | source resolver + prepare |
| Confirm valid prepared write | Published-local cannot confirm | Re-resolve/re-prove source, publish exactly one immutable revision, return durable receipt/created IDs | Yes | commit + DungeonMind authority |
| Commit success | Local proposal remains unless exact-run surface clears it | Clear only committed proposal IDs; preserve unrelated local drafts | Yes | draft owner/UI |
| Commit success + refresh | No published-local refresh path | Reload recap projection against current World head without leaving campaign/session | Yes | RecapGraphModule / projection view |
| Unique authored label exists in recap prose | Local overlay can show a pill | Refreshed ordinary World recap may link it using existing mention linker | Yes | World recap projection |
| Two durable nodes claim same recap surface | Not a V2-1A durable case | No arbitrary pill winner; preserve current ambiguity diagnostic semantics | Yes | World recap projection |
| Prepare source missing/drifted | Published-local never prepares | Fail closed; no World mutation | Yes | source resolution/admission |
| Proposal changes after prepare | Existing prepare panel invalidates preview | Keep invalidation; confirm impossible until re-prepare | Yes | prepare/commit UI |
| World head advances after prepare | Existing backend supports stale-parent failure | 409 stale parent; no new revision; operator must prepare again | Yes | commit |
| Exact-run Graph Review | Existing `sourceRunId` path | Byte/behavior compatible except additive source-selector contract | Yes | backend + existing UI/tests |
| Deliberate same-label Create new | Local proposal can be staged with warnings | Distinct durable node is allowed; no implicit link/merge/reconciliation | Yes | proposal → publish |
| Commit retry / lost response | Existing recover/idempotency path | Same operation/source/proposals returns same published revision, no duplicate write | Yes | commit authority |

Adversarial sequences that must be proved:

| Sequence | Required safe outcome | Owning §7 proof |
|---|---|---|
| prepare valid recap → mutate proposal locally → click commit | prepared preview invalidated; no stale proposal set published | UI regression |
| prepare recap A → submit confirm with recap B selector | confirmation invalid; no World head change | backend contract |
| prepare → another write advances head → confirm | `stale_parent`; no child from stale prepare | backend integration |
| prepare → source record/path/digest no longer proves same immutable recap → confirm | source failure; no publication | backend integration |
| commit succeeds → refresh fails | durable commit receipt remains truthful; local committed proposals are not resurrected; user can retry refresh | UI regression |
| same-label node A exists → deliberately create node B with same label → refresh recap | A and B remain distinct durable IDs; no automatic merge; recap linker does not arbitrarily choose one | integration + projection regression |
| commit request replay after successful publication | same published revision / already-applied result | backend integration |

---

## §4 Files in scope — write lease

Expected paths:

| Action | Path | Purpose |
|---|---|---|
| Modify | `Docs/Plans/HANDOFF-CON-READY-authoring-v2-governed-world-commit-v1.md` | canonical contract, evidence, review handback |
| Create | `Docs/Reports/REPORT-CON-READY-authoring-v2-governed-world-commit-v1.md` | exact implementation/dogfood findings and remaining V2-3 boundary |
| Modify | `apps/live_control_server/services/graph_object_authoring_prepare.py` | additive `recapArtifactId` request/source-selector contract; prepare source resolution and signed-intent binding |
| Modify | `apps/live_control_server/services/graph_object_authoring_commit.py` | confirm selector binding, re-resolution/re-proof, stale/idempotent semantics |
| Modify | `tests/test_graph_object_authoring_prepare.py` | source-selector XOR, recap resolution, source admission, prepare no-mutation proof |
| Modify | `tests/test_graph_object_authoring_commit.py` | confirm binding, source drift, stale parent, retry compatibility |
| Modify | `tests/test_graph_object_authoring_routes.py` | API contract for additive recap selector and error envelopes |
| Create | `tests/test_graph_object_authoring_published_recap_write.py` | disposable real-authority end-to-end recap → prepare → commit → exact read-back + duplicate ambiguity witness |
| Modify | `apps/live-control-ui/src/api/types.ts` | additive `recapArtifactId` prepare/commit request field |
| Modify | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphObjectAuthoringPrepareCommitPanel.tsx` | pass recap source selector, show governed prepare/confirm result and created IDs |
| Modify | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphObjectAuthoringPrepareCommitPanel.test.tsx` | published-recap prepare/commit request + success/failure evidence |
| Modify | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphObjectAuthoringSurface.tsx` | expose existing prepare/commit panel after published wizard review when durable source selector exists |
| Modify | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphObjectAuthoringSurface.test.tsx` | published wizard durable transition regression |
| Modify | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphObjectAuthoringPublishedWizard.tsx` | final-step copy/affordance truthfully distinguishes local review from governed publish |
| Modify | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/PublishedRecapLocalAuthoring.tsx` | stop forcing local-only at publish transition; pass recap record identity, clear committed proposals, request projection refresh |
| Modify | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/PublishedRecapLocalAuthoring.test.tsx` | local-before-prepare, explicit publish, proposal clearing, same-label Create new semantics |
| Modify | `apps/live-control-ui/src/planSurface/graphPreview/WorldGraphRecapProjection.tsx` | thread refresh callback/source record into published authoring while preserving Peek/local projection |
| Modify | `apps/live-control-ui/src/planSurface/graphPreview/WorldGraphRecapProjection.test.tsx` | post-commit root/pill/ambiguity behavior |
| Modify | `apps/live-control-ui/src/planSurface/graphPreview/RecapGraphModule.tsx` | provide exact campaign/session recap reload after successful commit |
| Modify | `apps/live-control-ui/src/planSurface/graphPreview/RecapGraphModule.test.tsx` | current-scope refresh and no navigation drift |
| Modify if needed | `apps/live-control-ui/src/planSurface/planSurface.css` | only minimal layout needed to fit existing prepare/commit panel into Author Node |

### Bounded source-resolution extraction

If `graph_object_authoring_prepare.py` would otherwise need to duplicate recap-registry/source-registry mechanics, one small server helper and its focused test may be created.

```text
Directory:
  apps/live_control_server/services/

Maximum additional production paths:
  1

Maximum additional focused test paths:
  1

Allowed purpose:
  resolve recapArtifactId from server-owned RecapArtifactRecord
  verify campaign/session/path/digest using existing contracts
  obtain deterministic canonical recap SourceArtifact + revision token
  return a small resolved-source DTO consumed by existing Graph Review source admission

Not allowed:
  new storage format
  new route family
  new source catalog
  browser-trusted path/digest
  DungeonMind pin/schema change
```

Any other production path outside this lease is a STOP/re-brief.

---

## §5 Explicitly out of scope / collision boundary

| Path / capability | Why this slice must not touch or claim it |
|---|---|
| `merge_objects` publication / merge reconciliation | separate durable identity operation; currently intentionally inexpressible |
| automatic dedupe / exact-label auto-merge | would destroy the deliberate same-label adversarial case and changes identity policy |
| delete/undo of a published World revision | immutable World semantics; separate compensating-write design |
| canonical recap Markdown mutation | recap remains source, never the graph write target |
| invented canonical source-span binding from highlight offsets | recap v1 mentions are navigation-only; V2-1A already established this boundary |
| derived-gold export / benchmark fixture generation | V2-3 successor |
| extraction/model ablation | V2-4 successor |
| Agent authoring / Assess World Graph | later manual-loop successor; no privileged write path |
| local-draft-aware Agent query | separate capability |
| statblock generation / graph-native artifacts | downstream capability after author→write→query loop is proven |
| generic graph editor | broader product workflow |
| corpus recap bytes | read-only source |
| DungeonMind dependency/persistence schema | existing authority contract is sufficient unless a real dependency STOP is proven |

Also out of scope: opening a second PR, spawning a cleanup PR from dogfood, or silently folding duplicate cleanup into this implementation.

---

## §6 Implementation contract

### Input

```text
published recap context:
  campaignId
  sessionId
  recapArtifactId = RecapArtifactRecord.artifact_id

local staged proposals:
  object
  link_existing
  relationship

existing durable context:
  current DungeonMind World head
  server-owned recap/source registries
  existing WorldGraphSourceAdmissionAuthority
```

### Output

On prepare:

```text
no World mutation
exact admitted source pair
expected parent revision
proposal/contribution digest
signed confirmation intent
human-readable assertion preview
```

On commit:

```text
exactly one immutable DungeonMind World revision
or idempotent recovery of the same revision
created_node_ids for object proposals
published_revision_id
parent_revision_id
operation_id
truthful no-mutation/source guarantees
```

### Source selector

```text
EXPRESSIBLE request:
  exactly one of sourceRunId / recapArtifactId

INEXPRESSIBLE merge request:
  remains inexpressible; do not create new source-selector exceptions
```

The implementation may model the XOR validation as a helper, validator, or resolver rule. It must be shared by prepare/commit semantics rather than drifting independently.

### Recap source resolution

For `recapArtifactId`:

1. resolve the exact server-owned `RecapArtifactRecord`;
2. require exact campaign/session equality with the authoring request;
3. resolve only the record's server-owned recap path;
4. require the current source bytes to match the record's registered digest;
5. create/load the existing deterministic recap `GraphMemorySourceArtifact` using current source-registry behavior;
6. use that artifact's canonical URI and digest-derived revision token;
7. pass it through `WorldGraphSourceAdmissionAuthority.prove_or_admit`;
8. seal the admitted DungeonMind pair into prepare intent;
9. on confirm, re-resolve the recap record/source and `prove` the sealed admitted pair before publish.

No browser path/digest is authoritative at any step.

### Commit point

```text
Before DungeonMind publish:
  local proposals may exist
  canonical recap unchanged
  source pair may be admitted/proved
  World head unchanged

DungeonMind publish:
  immutable child revision becomes durable

After publish:
  publication receipt is truth
  created_node_ids are durable node identities
  UI cleanup/refresh may still fail independently
```

If post-commit refresh fails, report **write succeeded; refresh failed**. Do not label the write failed and do not re-submit automatically.

### Local proposal cleanup

Only proposal IDs included in the successful commit are cleared from session-scoped local draft storage.

Uncommitted sibling proposals stay staged.

If commit returns `already_applied`, the same committed proposal IDs may be cleared because the durable result is already proven.

### Read-back

At owning integration boundary, for each newly created object:

```text
commit.created_node_ids[localProposalId]
→ exact node exists in published_revision_id
→ exact object read succeeds
→ scoped World projection contains node
```

The UI success view must expose the durable created node ID(s) in technical/write details or equivalent truthful operator-visible receipt.

After UI refresh:

- unique label/alias mention may become a normal durable pill;
- duplicate label ambiguity must remain ambiguity, not an arbitrary bind;
- the local `local-authoring:<proposal>` identity must no longer masquerade as the durable identity.

### Replay / idempotency

```text
same source selector + same proposals + same prepared operation after success
→ recover same published revision / already_applied

changed proposal after prepare
→ preview invalidated / confirmation invalid

changed source selector after prepare
→ confirmation invalid

changed World head before first successful publish
→ stale_parent

refresh retry
→ read-only; never republishes
```

---

## §7 Evidence required to merge

| Guarantee / invariant clause | Owning boundary | Evidence class | Command or manual scenario | Expected evidence | Stop condition |
|---|---|---|---|---|---|
| recap selector is server-resolved, not path/digest trusted | prepare service | contract/adversarial | backend focused tests | `recapArtifactId` resolves exact record/source; spoofed/mismatched campaign/session fails | browser path/digest influences authority |
| sourceRunId remains compatible | prepare + commit | regression | existing prepare/commit suites | exact-run tests unchanged except additive field | exact-run behavior changes |
| selector XOR | prepare + commit | contract | both/neither selector tests | expressible requests fail closed | implicit latest/run fallback |
| prepare is non-mutating | source + World authority | integration | published-recap integration test | source admitted/proved; World head unchanged | prepare advances World |
| confirm re-proves source | commit | adversarial | delete/drift source between prepare/commit | no publication; stable source error | publish occurs |
| stale parent fails closed | commit | adversarial | advance head after prepare | 409 stale parent; no stale child | stale write publishes |
| new object becomes durable | real authority/read service | integration | create object via API prepare/commit | returned created ID exists at published revision and exact read succeeds | only local overlay proves it |
| deliberate same-label new object stays distinct | real authority + recap projection | integration/adversarial | create second same-label object | distinct durable IDs; no auto merge; recap mention ambiguity remains truthful | arbitrary identity winner/merge |
| commit retry is idempotent | authority | integration | resend exact commit | same published revision / already_applied | second child revision |
| UI does not write before confirm | published Author Node | component/integration | stage → review → prepare | local state + prepare only; no commit call | staging/prepare publishes |
| UI clears only committed drafts | draft owner | regression | two proposals, commit one prepared set | committed IDs clear; unrelated local draft remains | all drafts wiped |
| UI refreshes same scope after commit | RecapGraphModule | component/integration | commit success → refresh | same campaign/session; new head projection | scope/navigation drifts |
| durable receipt remains truthful if refresh fails | prepare/commit panel | adversarial UI | commit success + refresh rejection | “write succeeded” preserved + retry refresh | UI reports write failure |
| created durable IDs are visible to operator | commit panel | UI regression | successful object commit | created IDs shown in write details | durable identity hidden |
| no canonical recap mutation | filesystem/source contract | integration/diff | before/after source digest | same recap bytes | source file changes |

Exact verification commands:

```bash
uv run pytest \
  tests/test_graph_object_authoring_prepare.py \
  tests/test_graph_object_authoring_commit.py \
  tests/test_graph_object_authoring_routes.py \
  tests/test_graph_object_authoring_published_recap_write.py -q

pnpm --dir apps/live-control-ui exec vitest run \
  src/planSurface/graphReviewWorkbench/GraphObjectAuthoringPrepareCommitPanel.test.tsx \
  src/planSurface/graphReviewWorkbench/GraphObjectAuthoringSurface.test.tsx \
  src/planSurface/graphReviewWorkbench/PublishedRecapLocalAuthoring.test.tsx \
  src/planSurface/graphPreview/WorldGraphRecapProjection.test.tsx \
  src/planSurface/graphPreview/RecapGraphModule.test.tsx

pnpm --dir apps/live-control-ui typecheck
pnpm --dir apps/live-control-ui build
git diff --check
git diff --name-only <dispatch-base>...HEAD
```

If the PostgreSQL-backed integration test has an established repository prerequisite/fixture, use that exact fixture. Do not silently replace it with a helper-only fake and claim durable publication proof.

### Minimal live dogfood proof — required

Use the actual published recap/Author Node surface.

#### Witness A — real new durable object

```text
1. Open a real Campaign 1 or Campaign 2 recap.
2. Choose a phrase/entity that is genuinely absent from current World memory.
3. Highlight → Author Node → Create new.
4. Stage the object.
5. Verify the working projection changes but World is still unchanged.
6. Choose Review & publish.
7. Inspect prepared assertions + exact expected parent.
8. Confirm.
9. Capture published revision + created durable node ID.
10. Refresh/reload the same campaign/session.
11. Prove the exact durable node is readable.
12. If the label is unique in recap text, observe the ordinary World-backed pill; if it is not linked, record the truthful linker diagnostic rather than forcing a pill.
```

The operator chooses the actual campaign fact. Do not seed a fake production-world object merely to satisfy the test.

#### Witness B — duplicate preparation semantics

Deterministic integration coverage is mandatory:

```text
existing durable node A label = X
→ deliberately stage Create new node B label = X
→ publish
→ A.id != B.id
→ both survive durable read
→ no automatic merge/rebind
→ recap mention linker refuses arbitrary winner for surface X
```

A live duplicate in the real Mirathorn World is **not** required for merge. If the operator explicitly designates a safe/adversarial real target, the UI may be dogfooded the same way. Otherwise preserve the real campaign and use the disposable integration witness to prepare the V2-3/V2-4 experiment.

### Report

Create:

`Docs/Reports/REPORT-CON-READY-authoring-v2-governed-world-commit-v1.md`

Record:

- exact implementation base/head/PR;
- exact source-selector implementation;
- whether existing normalized recap digests were directly compatible;
- exact source artifact/revision admitted for live Witness A;
- parent/published revision;
- local proposal ID → created durable node ID;
- refresh/read-back result;
- any recap linker ambiguity/unique-pill result;
- duplicate integration witness IDs/result;
- dogfood friction;
- explicit V2-3 boundary.

---

## §8 Required review handback

### Implementation handback — pre-review

- Dispatch base: `main@28b1fdf494ffc6e53b99b311b2f4d5256fd5e8a2`.
- Implementation branch: `con-ready/authoring-v2-governed-world-commit-v1`.
- Implementation commit: `3a254140` — `CON-READY: publish staged recap memory to World`.
- Assigned PR: #742 OPEN — `CON-READY: publish staged recap memory to World`; opened from this handback at `a441dc6d`.
- PR topology: `serial`; no other CON-READY implementation PR was opened during implementation.
- §1 invariant: backend selector binding, governed prepare/confirm, durable receipt IDs, same-scope refresh wiring, and duplicate-safe disposable proof are implemented. Live Witness A remains pending operator-selected real-world dogfood.
- Source selector: `sourceRunId XOR recapArtifactId`; `recapArtifactId` resolves the server-owned `RecapArtifactRecord`, verifies campaign/session/path/digest, creates/loads the deterministic recap SourceArtifact, and binds its admitted pair into the confirmation intent.
- Prepare/commit bindings: campaign, campaign relation, world, both source-selector fields, admitted source artifact/revision, expected parent, operation ID, proposal digest, contribution digest, and actor.
- Evidence produced: backend focused suite **50 passed**; focused UI suite **79 passed**; UI typecheck **passed**; UI build **passed** with the existing chunk-size warning; compileall and `git diff --check` **passed**. Full command output and the live-dogfood boundary are recorded in `Docs/Reports/REPORT-CON-READY-authoring-v2-governed-world-commit-v1.md`.
- Live Witness A: not performed by the implementation agent because the handoff requires the operator to choose a genuinely absent campaign fact before a real World write. No production object was seeded.
- Duplicate integration witness: two same-label durable objects remain distinct and the recap linker emits `ambiguous_mention_surface` rather than selecting an arbitrary pill winner.
- Actual implementation paths remain inside §4; the steward preflight reported pre-existing stale overlaps from older handoffs, which were not edited.
- Baseline/waiver: the stale retired-module patch in the existing commit test was removed from the leased test file so the required backend suite runs green; remaining Pydantic field-shadow warnings are pre-existing.
- Prior finding ledger: V2-1A review findings were closed before this dispatch; no new review cycle has occurred for V2-2.
- V2-3 remains unimplemented.

Record:

1. `Review Cycle <N>` and exact PR/branch/head SHA;
2. exact dispatch base;
3. serial topology and open PR set at dispatch;
4. §1 invariant disposition;
5. source selector actually implemented and why it is authoritative;
6. exact prepare/commit publication binding fields;
7. §7 evidence required vs produced with provenance;
8. live Witness A result;
9. duplicate integration witness result;
10. exact created durable node IDs and published revision IDs;
11. actual changed paths vs §4/bounded discovery;
12. baseline failures/waivers;
13. prior finding ledger on re-review;
14. confirmation that V2-3 remains unimplemented.

---

## §9 Acceptance rubric

- [ ] Handoff was steward-authored and checked into `main` before dispatch.
- [ ] V2-1A / #741 completion is synchronized in current state authority before implementation dispatch.
- [ ] PR topology is serial and only the assigned V2-2 PR is opened.
- [ ] Published recap stages locally exactly as V2-1A did until the operator explicitly chooses governed publication.
- [ ] Expressible writes require exactly one authoritative selector: `sourceRunId XOR recapArtifactId`.
- [ ] Published recap source identity is resolved/proved server-side from the selected recap record; browser path/digest is never trusted.
- [ ] Prepare does not advance World head.
- [ ] Confirm re-proves source identity and fails closed on source drift or stale parent.
- [ ] Successful new-object confirm publishes exactly one immutable DungeonMind World revision and returns durable created node IDs.
- [ ] Exact created node is readable at the published revision through the real World read boundary.
- [ ] Successful/idempotently recovered commits clear only committed local proposals.
- [ ] Same campaign/session refresh reads committed World truth without navigation drift.
- [ ] Post-commit refresh failure cannot make a successful durable write look failed.
- [ ] Same-label deliberate Create new can produce a second durable node without automatic merge/reconciliation.
- [ ] Duplicate recap mention remains ambiguity-safe; no arbitrary pill winner is introduced.
- [ ] Canonical recap Markdown remains byte-stable.
- [ ] Exact-run `sourceRunId` authoring remains compatible.
- [ ] No `merge_objects`, delete, derived-gold, ablation, Agent-authoring, or statblock successor capability is silently added.
- [ ] Actual changed paths stay inside §4 / bounded discovery.
- [ ] Required backend, frontend, typecheck, build, diff, integration, and live dogfood evidence is recorded at the exact reviewed head.

## Stop conditions

Stop and return to the steward if:

- real published recap records cannot be deterministically converted/proved as canonical recap SourceArtifacts without changing provenance semantics;
- normalized recap digest semantics conflict between recap registry and source registry;
- V2-2 requires a new DungeonMind persistence/schema primitive rather than the existing publication authority;
- durable object publication succeeds but exact read-back fails at the owning World boundary;
- correct duplicate behavior would require changing global identity/mention policy;
- a required production path falls outside §4/bounded discovery;
- another implementation PR opens in this serial workstream;
- implementation needs merge/reconciliation, delete/undo, derived gold, extraction, Agent, or statblock work to claim success.

Report the exact failed invariant, source/world IDs, relevant paths, and smallest proposed successor.
