# HANDOFF — BLD-05a post-merge workspace-document authoring hardening

**Created:** 2026-07-23, America/Denver
**Status:** ACTIVE — dispatch exactly one post-merge hardening capability.
**Canonical handoff path:** `Docs/Plans/HANDOFF-bld05a-post-merge-authoring-hardening.md`
**Repository:** `Drakosfire/DungeonMindBuddy`
**Implementation base:** `ea7ad826a2ca4f9d275ce245a3884d4af72278a8`
**Suggested branch:** `agent/bld05a-post-merge-authoring-hardening`
**Predecessor:** merged PR #399, `BLD-05a: workspace-document authoring seam + thin Build`
**Named successor:** bounded shared-authoring polish and dogfood across Plan, Build, and runbook
**Operating mode:** fresh-context coding agent with adversarial lifecycle ownership; do not continue from the assumption that merge implies completion.

---

## §0 Capability decomposition decision

| Candidate outcome                                                                                   |                    Independently useful? | Public/durable contract changed? | User or operator surface changed? | Failure model changed? | Independently testable or revertible? | Decision                     |
| --------------------------------------------------------------------------------------------------- | ---------------------------------------: | -------------------------------: | --------------------------------: | ---------------------: | ------------------------------------: | ---------------------------- |
| Prevent post-commit verification from adopting unseen remote content                                |                                      Yes |     No — hardens merged contract |                               Yes |                    Yes |                                   Yes | Include                      |
| Preserve edits made while verification is in flight                                                 |                                      Yes |     No — hardens merged contract |                               Yes |                    Yes |                                   Yes | Include                      |
| Persist the first real editor transaction on all three consumers                                    |                                      Yes |     No — hardens merged contract |                               Yes |                    Yes |                                   Yes | Include                      |
| Prevent rejected document authority from reaching Build editor, storage, save, or Agent Interaction |                                      Yes |     No — hardens merged contract |                               Yes |                    Yes |                                   Yes | Include                      |
| Make Plan commit handback one-shot                                                                  |                                      Yes |     No — hardens merged contract |                               Yes |                    Yes |                                   Yes | Include                      |
| Make runbook reset a durable local reset rather than a visual claim                                 |                                      Yes |     No — hardens merged contract |                               Yes |                    Yes |                                   Yes | Include                      |
| Synchronize the BLD-05a judgment record and active gate after proof                                 | No — process closure for this capability |                               No |                                No |                     No |                                    No | Include as required handback |
| Improve state language, navigation, creation usability, and visual polish                           |                                      Yes |                      Potentially |                               Yes |                  Maybe |                                   Yes | Successor                    |
| Add extraction controls, SourceArtifact creation, ExtractionRun launch, or Graph Review handoff     |                                      Yes |                              Yes |                               Yes |                    Yes |                                   Yes | Reject from this slice       |

**Selected capability:** restore and prove the merged BLD-05a workspace-document lifecycle invariant under the five unresolved adversarial sequences, then synchronize repository authority so the next PR can begin from a truthful immutable base.

**Why included rows share one invariant:** each included behavior determines whether one accepted workspace-document identity and revision remains coherent across receipt, verification, editor/local state, surface authority, parent handback, persistence, and Agent Interaction. None creates a new product capability; all close failure sequences in the already-merged authoring lifecycle.

**Named successor:** bounded authoring polish and dogfood. It may improve language, affordances, navigation, creation/classification usability, Agent Interaction visibility, and visual consistency, but it must not begin until this handoff’s evidence ledger is green or explicitly waived.

---

## §1 Mission

Plan, Build, and runbook preserve one authorized workspace-document identity and revision through commit verification, first-edit persistence, cross-surface rejection, Plan handback, and runbook reset, so the merged BLD-05a seam becomes a truthful base for bounded authoring polish and dogfood.

### Merge-ready invariant

> For one workspace-document UUID, the server snapshot, durable commit receipt, local/editor base, URL selection, surface authority, lifecycle display, and Agent Interaction context identify the same authorized document revision; any mismatch fails safely without unintended mutation and provides an explicit recovery path.

Additional constraints:

* Plan, Build, and runbook use one local-state schema and one authoring lifecycle.
* Worldbuilding uses `sessionNumber: null`, never session `0`.
* Visiting `/build` without a document ID creates no durable document.
* Build accepts only authorized `worldbuilding_source` documents.
* A successful durable commit remains truthfully committed even when later verification fails.
* Verification is not allowed to advance the client’s expected revision beyond the authoritative commit receipt while retaining older editor content.
* A real user edit must never be discarded merely because it was the next editor update after attachment or load.
* Rejected records may exist only as diagnostic state and must not be exposed as accepted authoring or Agent Interaction context.

### Mission falsification test

This is not one slice if implementation must also deliver extraction controls, SourceArtifact or ExtractionRun creation, Graph Review handoff, graph publication, document-management UX, broad visual redesign, new Markdown syntax support, or a second authoring state machine.

---

## §2 Context, authority, and boundaries

PR #399 merged at `ea7ad826a2ca4f9d275ce245a3884d4af72278a8` while its own PR description still marked five guarantees as merge blockers and recorded no waiver. No functional code changed after commit `c4da6262c8d8720d669561ef84a0040ff1ec4226`; later commits changed only process and planning documentation.

Current merged strengths that must not regress:

* snapshot reads hold `workspace_document_mutation_lock`;
* commit responses are authoritative receipts constructed under the document mutation lock;
* discard clears the UUID-bound local draft before reopening;
* Plan, Build, and runbook call the shared `useWorkspaceDocumentAuthoring` hook;
* Build URL selection follows `popstate`;
* clean durable drafts are labeled `Draft`, not `Committed`;
* worldbuilding Agent Interaction scope uses `sessionNumber: null`;
* bare `/build` is an explicit creation form and performs no implicit durable write.

### Parent authority

1. `Docs/Design/DESIGN-merge-ready-invariant-evidence.md`
2. `Docs/Design/CONTRACT-workspace-document-identity-v1.md`
3. `Docs/Plans/ROADMAP-build-surface-worldbuilding-ingest.md`
4. `Docs/Plans/PLAN-build-surface-worldbuilding-ingest-pr-slices.md`
5. `Docs/Plans/HANDOFF-bld05a-workspace-document-authoring-seam.md`
6. `.cursor/rules/external-agent-pr-loop.mdc`
7. `.cursor/skills/external-agent-pr-loop/SKILL.md`
8. `.cursor/skills/external-agent-pr-loop/templates/HANDOFF.template.md`

### Authority precedence

```text
1. Adopted repository design and identity contracts
2. Active roadmap and implementation plan
3. This checked-in hardening handoff
4. Merged implementation and owning-boundary tests
5. PR #399 body, review comments, and attached handoff context
6. Chat summaries
```

The repository implementation does not override an explicit merge invariant merely because it is already merged. The merge is a historical fact; the evidence ledger determines whether the seam is hardened.

### Exact predecessor contracts consumed

**WorkspaceDocumentSnapshot**

```text
record
markdown
content_sha256
file_fingerprint
file_exists
loaded_revision
```

**TiptapMarkdownWriteCommitResponse**

```text
document_id
committed_revision
committed_record
normalized_content_sha256
file_fingerprint
target_relpath
registry_revision
writer_ok
writer_phase
diagnostics
```

**WorkspaceDocumentLocalState v3**

```text
document_id
kind
surface
base_revision
base_content_sha256
tiptap_json
exported_markdown
dirty
updated_at
last_local_save_at
```

### What remains false after this slice

* The shared authoring experience is not yet polished or dogfooded.
* Build does not launch extraction.
* No committed workspace revision becomes a SourceArtifact.
* No ExtractionRun is created or recovered.
* Build does not open Graph Review.
* No graph contribution is prepared, confirmed, or published.
* Full Markdown parity remains false.

If the implementation base has moved, first compare current `main` against `ea7ad826`. Continue only if intervening changes do not materially alter the five owning failure sequences. Otherwise stop and report the changed contract.

---

## §3 Observable-path inventory

| Observable path                                                      | Current merged behavior                                                                                       | Required behavior                                                                                                 | Same invariant? | Owning boundary                                  |
| -------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------- | --------------: | ------------------------------------------------ |
| Commit revision N; verification returns the exact committed snapshot | Receipt advances local base, then any returned snapshot is adopted                                            | Verification succeeds only when identity, revision, hash, and fingerprint agree with the receipt                  |             Yes | shared hook + verification rule                  |
| Commit revision N; another writer commits N+1 before verification    | Client adopts N+1 as expected revision while retaining editor content from N                                  | Keep N as the receipt-backed local base; enter conflict/reconciliation; block next save until explicit recovery   |             Yes | shared hook + reducer                            |
| User edits after commit receipt but before verification completes    | Verification dispatches clean state unconditionally                                                           | The real edit remains persisted and dirty; matching verification may validate N but cannot clear the later edit   |             Yes | editor update + shared hook + reducer            |
| First user paste/insertion/deletion after editor attachment          | A generic “skip next update” flag can discard it                                                              | Exactly one user transaction updates TipTap JSON and Markdown local state, sets dirty, and enables save           |             Yes | MarkdownEditorCore + shared hook + each consumer |
| Build opens a Plan or runbook UUID directly                          | Surface authority rejects, but rejected snapshot remains exposed as `record`; Build may publish scope/context | No editor, local storage, save, Build document scope, or context containing the rejected UUID/revision/path/hash  |             Yes | shared open + hook exposure + Build integration  |
| Navigate from valid Build document to rejected UUID                  | Previous accepted Agent Interaction context may remain if the rejected record is merely ignored               | Clear or replace prior Build document context; no stale accepted document context survives the rejected selection |             Yes | Build + Agent Interaction integration            |
| One Plan commit receipt reaches parent                               | Persistent receipt plus parent-owned descriptor can repeatedly retrigger callback                             | One callback per unique authoritative receipt; parent render stabilizes                                           |             Yes | PlanSurfaceCanvas + PlanSurfaceShell             |
| Reset committed runbook to starter                                   | Writes clean starter state, then reload adopts non-empty committed Markdown                                   | Replace editor with starter; mark dirty only when different; persist locally; refresh restores exact starter      |             Yes | runbook consumer + shared reconciliation         |
| Runbook reset when starter equals committed content                  | Reset semantics are not explicit                                                                              | Starter may remain clean because it equals committed content; refresh remains exact and stable                    |             Yes | runbook consumer                                 |
| Existing conflict discard                                            | Clears exact UUID local state and opens server                                                                | Preserve behavior                                                                                                 |             Yes | shared hook                                      |
| Existing verification network failure after commit                   | Remains truthfully committed with pending verification                                                        | Preserve behavior and error visibility                                                                            |             Yes | shared hook + lifecycle display                  |
| Browser back/forward between Build documents                         | URL hook follows `popstate`                                                                                   | Preserve loaded UUID and accepted Agent Interaction identity together                                             |             Yes | Build page + hook + Agent Interaction            |

A path marked “required behavior” is merge-blocking. Do not replace owning-boundary proof with a helper-only unit test.

---

## §4 Files in scope — allowlist

Every changed path must be listed here or admitted by the bounded discovery exception.

| Action           | Path                                                                                   | Purpose                                                                                                                               |
| ---------------- | -------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| Create           | `Docs/Plans/HANDOFF-bld05a-post-merge-authoring-hardening.md`                          | Canonical dispatch authority for this slice                                                                                           |
| Modify           | `apps/live-control-ui/src/workspaceDocument/useWorkspaceDocumentAuthoring.ts`          | Receipt verification, edit-during-verification preservation, accepted-state exposure, editor update handling                          |
| Modify           | `apps/live-control-ui/src/workspaceDocument/workspaceDocumentAuthoringMachine.ts`      | Represent mismatch/reconciliation and dirty-preserving verification truthfully if the current phases are insufficient                 |
| Modify           | `apps/live-control-ui/src/workspaceDocument/workspaceDocumentAuthoringMachine.test.ts` | Prove lifecycle transitions and labels                                                                                                |
| Create or Modify | `apps/live-control-ui/src/workspaceDocument/useWorkspaceDocumentAuthoring.test.tsx`    | Owning-boundary hook tests for N/N+1, edit during verification, first update, rejection, and recovery                                 |
| Modify           | `apps/live-control-ui/src/tiptap/MarkdownEditorCore.tsx`                               | Ensure programmatic hydration and user updates are distinguishable without generic next-update suppression                            |
| Create or Modify | `apps/live-control-ui/src/tiptap/MarkdownEditorCore.test.tsx`                          | Prove first real transaction is emitted exactly once                                                                                  |
| Modify           | `apps/live-control-ui/src/buildSurface/BuildSurfaceShell.tsx`                          | Publish Agent Interaction only from accepted authoring state and clear stale accepted context on rejection/navigation                 |
| Modify           | `apps/live-control-ui/src/buildSurface/BuildSurfaceShell.test.tsx`                     | Prove rejected Plan/runbook UUID isolation and stale-context clearing                                                                 |
| Modify           | `apps/live-control-ui/src/planSurface/components/PlanSurfaceCanvas.tsx`                | Consume each authoritative receipt exactly once                                                                                       |
| Modify           | `apps/live-control-ui/src/planSurface/PlanSurfaceShell.test.tsx`                       | Prove callback count is one and render stabilizes                                                                                     |
| Modify           | `apps/live-control-ui/src/tiptap/TiptapCalloutBridgeSpike.tsx`                         | Implement real reset-to-starter local state and editor replacement                                                                    |
| Modify           | `apps/live-control-ui/src/tiptap/TiptapCalloutBridgeSpike.test.tsx`                    | Prove reset, dirty semantics, refresh restore, and first transaction                                                                  |
| Modify           | `apps/live-control-ui/src/agentInteraction/AgentInteractionProvider.test.tsx`          | Only if needed to prove rejected/stale Build context removal through the real provider                                                |
| Modify           | `apps/live-control-ui/src/App.test.tsx`                                                | Only if needed to prove route-level Build identity/context behavior                                                                   |
| Modify           | `Docs/Plans/HANDOFF-bld05a-workspace-document-authoring-seam.md`                       | Record PR #399 as merged with incomplete evidence and point to this active hardening gate                                             |
| Modify           | `Docs/Plans/PLAN-build-surface-worldbuilding-ingest-pr-slices.md`                      | Replace stale `open_under_review` state, record historical merge judgment, add hardening PR judgment/evidence, and identify next gate |
| Modify           | `Docs/Plans/ROADMAP-build-surface-worldbuilding-ingest.md`                             | Record Phase 4A as incomplete until hardening merges, then bridge to Phase 4B                                                         |
| Modify           | `.cursor/rules/external-agent-pr-loop.mdc`                                             | Only if this work reveals a genuinely new reusable process invariant not already captured; otherwise do not touch                     |
| Modify           | `.cursor/skills/external-agent-pr-loop/SKILL.md`                                       | Same restriction as above; not routine doc-sync                                                                                       |
| Modify           | `.cursor/skills/external-agent-pr-loop/templates/HANDOFF.template.md`                  | Same restriction as above; not routine doc-sync                                                                                       |

### Bounded discovery exception

```text
Directory: apps/live-control-ui/src/workspaceDocument/
Maximum additional paths: 2
Allowed path kinds: one pure receipt/snapshot verification helper and its direct test
Decision rule: add only if it makes receipt agreement and mismatch behavior independently testable without duplicating lifecycle state
Required report: name the added path, why existing files could not own the rule cleanly, and confirm no new durable contract was introduced
```

```text
Directory: Docs/Archive/
Maximum additional paths: 2
Allowed path kinds: moves or archived copies of the predecessor and hardening handoffs
Decision rule: use only the repository’s existing handoff archive convention after the hardening PR is accepted
Required report: exact source and archive paths; do not invent a new archive hierarchy
```

If another path is required, stop and report it before implementation.

---

## §5 Files and capabilities explicitly out of scope

| Path, ownership layer, or capability              | Why excluded                                                                  |
| ------------------------------------------------- | ----------------------------------------------------------------------------- |
| `src/graph_memory/**`                             | No graph contract changes belong to authoring hardening                       |
| extraction runtime/profile files                  | Extraction remains the later capability                                       |
| SourceArtifact or ExtractionRun contracts         | Distinct durable identities and successor work                                |
| Graph Review and `extract_promote` paths          | Publication ownership must remain unchanged                                   |
| Build extraction toolbar or launch controls       | Phase 5 is blocked until authoring polish/dogfood                             |
| broad Plan layout or projection work              | Separate product capability                                                   |
| document list/search/management UI                | Belongs to bounded polish if dogfood justifies it                             |
| new local-state schema version                    | The merged v3 contract is sufficient unless a stop condition proves otherwise |
| new server endpoints or registry fields           | The unresolved defects are client lifecycle/integration defects               |
| new Markdown syntax support                       | Separate fidelity capability                                                  |
| direct corpus or canon mutation                   | Not authorized                                                                |
| process template rewrites without a new invariant | Avoid turning product hardening into another documentation expansion          |

---

## §6 Implementation contract and conditional matrices

### Core input

```text
Accepted snapshot:
  authoritative record for requested UUID
  loaded revision
  content hash
  file fingerprint
  Markdown bytes

Commit receipt:
  authoritative committed UUID
  committed revision and record
  normalized content hash
  file fingerprint
  target identity

Editor/local state:
  accepted UUID, kind, surface
  receipt- or snapshot-backed base revision/hash
  current TipTap JSON and exported Markdown
  dirty state
```

### Core output

```text
An accepted authoring state whose exposed record, expected CAS revision, editor content,
local base, lifecycle status, URL selection, and Agent Interaction context remain coherent.

Any mismatch produces a blocked, explicit, recoverable state without adopting unseen
remote content or publishing rejected identity.
```

### Trust boundary

**Verifies**

* requested UUID equals snapshot record UUID;
* requested kind and surface are authorized by the registry record;
* snapshot record revision equals loaded revision;
* verification UUID, committed revision, content hash, and file fingerprint agree with the commit receipt;
* local dirty state reflects actual editor content after any in-flight edit;
* reset content is persisted against the current server base.

**Trusts without re-proving**

* the server commit receipt is authoritative once returned successfully;
* snapshot and commit atomicity are owned by the backend lock and existing tests.

**Rejects**

* verification snapshots from a newer or different revision;
* different UUID, kind, or surface authority;
* a generic “next update” suppression that cannot prove the skipped transaction is programmatic;
* accepted record/context publication after authority rejection.

### Commit point

```text
Commit point:
  successful commit response received from the writer

Before commit:
  prepare/commit failure leaves editor and dirty local content available

After commit:
  local base advances immediately from the authoritative receipt

Post-commit verification:
  may validate the receipt or identify divergence
  may not decide whether the commit happened
  may not advance expected revision beyond the receipt while editor retains older content

Truthful result after post-commit failure:
  committed, with verification pending or reconciliation required

Recovery:
  explicit reload/reconcile/discard flow; no silent adoption
```

### §6A State and fallback matrix

| Sequence                                              | Required state                                | Expected revision/base                        | Editor/local content                        | Save                                                                           | Recovery                                            |
| ----------------------------------------------------- | --------------------------------------------- | --------------------------------------------- | ------------------------------------------- | ------------------------------------------------------------------------------ | --------------------------------------------------- |
| Open exact authorized snapshot                        | ready clean or dirty per reconciliation       | snapshot revision/hash                        | reconciled accepted content                 | per dirty and phase rules                                                      | normal                                              |
| Commit N; verification exact match                    | ready clean unless edited after receipt       | receipt N/hash                                | receipt content or later dirty edit         | enabled only if later edit exists                                              | normal                                              |
| Commit N; edit before verification returns exact N    | ready dirty                                   | receipt N/hash                                | later user edit preserved locally           | enabled                                                                        | save as N→N+1                                       |
| Commit N; verification returns N+1                    | conflict/reconciliation required              | remain receipt N/hash until explicit recovery | retain editor/local N or later edit         | blocked                                                                        | explicitly load remote N+1 or preserve/export local |
| Commit N; verification UUID/hash/fingerprint mismatch | conflict/reconciliation required              | remain receipt N/hash                         | retain local editor                         | blocked                                                                        | explicit reconciliation                             |
| Commit N; verification unavailable                    | committed verification pending                | receipt N/hash                                | local committed content or later dirty edit | later edit remains saveable only if lifecycle safely permits receipt-based CAS | retry verification or save from N                   |
| Build opens Plan/runbook UUID                         | load error/rejected authority                 | none accepted                                 | no editor/local state                       | blocked                                                                        | navigate to authorized Build UUID                   |
| Navigate valid Build → rejected UUID                  | rejected authority; prior doc context cleared | none accepted for rejected selection          | no rejected editor                          | blocked                                                                        | navigate back or select authorized document         |
| Runbook reset differs from committed                  | ready dirty                                   | current snapshot base revision/hash           | exact starter content                       | enabled                                                                        | refresh restores starter; save commits it           |
| Runbook reset equals committed                        | ready clean                                   | current snapshot base                         | exact starter content                       | disabled under normal dirty rule                                               | normal                                              |
| Conflict discard                                      | loading → ready clean server                  | current server revision/hash                  | server content                              | normal                                                                         | existing path                                       |

No “latest snapshot wins” fallback is permitted after a commit receipt.

### §6B Identity matrix

| Situation                 | Required matching rule                                                                    | Ambiguity behavior                                 | Fallback permitted? | Persistence/context consequence       |
| ------------------------- | ----------------------------------------------------------------------------------------- | -------------------------------------------------- | ------------------- | ------------------------------------- |
| Requested UUID            | Exact equality with snapshot and receipt                                                  | Reject                                             | No                  | No accepted local state or context    |
| Registry kind             | Exact equality with requested kind                                                        | Reject                                             | No                  | No editor/save/context                |
| Surface authority         | Kind must be in `SURFACE_ALLOWED_KINDS[surface]`                                          | Reject                                             | No                  | Rejected record diagnostic only       |
| Verification revision     | Exact equality with `committed_revision`                                                  | Conflict/reconcile on newer or older               | No                  | Do not update expected CAS            |
| Verification content hash | Exact equality with receipt hash                                                          | Conflict/reconcile                                 | No                  | Do not replace local base             |
| Verification fingerprint  | Exact equality with receipt fingerprint                                                   | Conflict/reconcile                                 | No                  | Do not replace local base             |
| Plan receipt consumption  | Unique by authoritative receipt identity: document ID + committed revision + content hash | Duplicate delivery is ignored                      | No                  | Parent callback once                  |
| Runbook reset             | Same workspace UUID and current server base                                               | No ambiguity                                       | No                  | Local state remains UUID-bound        |
| Build Agent Interaction   | Accepted Build record only                                                                | Clear prior accepted document context on rejection | No                  | Never publish rejected UUID/path/hash |

Display title and target path are never identity substitutes.

### §6C Persistence and replay matrix

| Operation                  | Durable/local representation                                        | Round-trip guarantee                                       | Duplicate/replay behavior                                                           | Compatibility               | Rollback/reversion                      |
| -------------------------- | ------------------------------------------------------------------- | ---------------------------------------------------------- | ----------------------------------------------------------------------------------- | --------------------------- | --------------------------------------- |
| Commit receipt application | local-state v3 base revision/hash + editor JSON/Markdown            | Reopen reflects committed N unless later dirty edit exists | Reapplying same receipt is idempotent                                               | No schema change            | Local draft may be discarded explicitly |
| Matching verification      | no new durable representation                                       | Must not alter content or clear later edits                | Repeated exact verification is idempotent                                           | Existing API                | No action needed                        |
| Mismatching verification   | lifecycle conflict plus preserved local state                       | Refresh cannot silently replace local editor               | Repeated mismatch stays blocked                                                     | Existing API                | Explicit remote reload/discard          |
| First user transaction     | local-state v3 JSON + Markdown + dirty flag                         | Refresh restores exact transaction                         | One transaction persists once; duplicate TipTap event must not double-apply content | Existing schema             | User edits normally                     |
| Plan commit callback       | in-memory consumed receipt key                                      | Parent update occurs once                                  | Same receipt ignored                                                                | No public API change        | New receipt may invoke callback         |
| Runbook reset              | local-state v3 with current base and starter JSON/Markdown          | Refresh restores exact starter                             | Repeating reset is idempotent                                                       | Existing schema             | Discard local draft returns to server   |
| Rejected Build selection   | no accepted local state; Agent Interaction document context cleared | Refresh remains rejected                                   | Repeated rejection produces no mutation                                             | Existing authority contract | Navigate to valid UUID                  |

### §6D Predecessor-to-consumer mapping

**Grounding source:** merged API types, `TiptapMarkdownWriteCommitResponse`, `WorkspaceDocumentSnapshot`, and local-state v3.

| Predecessor field/outcome           | Real shape                                            | Consumer behavior                              | Transformation                                                                          | Required proof                      |
| ----------------------------------- | ----------------------------------------------------- | ---------------------------------------------- | --------------------------------------------------------------------------------------- | ----------------------------------- |
| `receipt.document_id`               | UUID string                                           | accepted document identity                     | exact equality only                                                                     | hook mismatch test                  |
| `receipt.committed_revision`        | integer                                               | expected CAS and local base revision           | direct assignment after commit                                                          | receipt application test            |
| `receipt.normalized_content_sha256` | digest string                                         | local base hash and verification comparator    | direct assignment                                                                       | exact/mismatch tests                |
| `receipt.file_fingerprint`          | string or null in type                                | verification comparator                        | compare against snapshot according to real nullability; do not invent fallback identity | exact/mismatch tests                |
| `receipt.committed_record`          | authoritative record                                  | accepted record and lifecycle display          | replace prior accepted record                                                           | receipt test                        |
| `snapshot.loaded_revision`          | integer                                               | verification evidence only after commit        | must equal receipt revision                                                             | N/N+1 test                          |
| `snapshot.content_sha256`           | digest string                                         | verification evidence                          | must equal receipt hash                                                                 | mismatch test                       |
| `snapshot.file_fingerprint`         | fingerprint string                                    | verification evidence                          | must equal receipt fingerprint                                                          | mismatch test                       |
| editor `update` event               | TipTap transaction callback                           | local JSON/Markdown and dirty state            | persist unless specifically identified as programmatic replacement                      | first-transaction integration tests |
| authority rejection                 | `openWorkspaceDocumentAuthoringState.status="reject"` | no accepted record/editor/storage/save/context | diagnostics may retain reason only                                                      | Build cross-kind test               |
| runbook reset                       | starter TipTap JSON                                   | local reset against current base               | dirty iff exported starter differs from committed snapshot Markdown                     | reset/refresh test                  |

Do not use invented “close enough” fixtures. Tests must use the real API field names and nullable shapes.

---

## §7 Verification ownership map and commands

### Evidence ledger

| Guarantee                                    | Owning boundary                                             | Required evidence                                                                          | Merge-blocking stop condition                                               |
| -------------------------------------------- | ----------------------------------------------------------- | ------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------- |
| Verification cannot adopt unseen N+1 content | shared authoring hook                                       | commit N; verification returns N+1; next save blocked; expected revision remains N         | older editor can overwrite N+1 or silently adopt it                         |
| Editing during verification remains dirty    | shared editor + hook + reducer                              | edit after receipt and before exact verification completes                                 | verification clears or loses the edit                                       |
| First transaction always persists            | MarkdownEditorCore + hook + Plan/Build/runbook integrations | exactly one paste/insertion/deletion per consumer updates JSON/Markdown, dirty, and save   | one real transaction is skipped, remains clean, or needs a second edit      |
| Surface authority gates every consumer       | shared open + hook + Build + Agent Interaction              | open Build with Plan and runbook UUIDs, including valid→rejected navigation                | rejected or stale identity reaches storage, editor, save, scope, or context |
| Plan handback is one-shot                    | Plan integration                                            | one commit invokes parent callback exactly once and render stabilizes                      | receipt causes repeated parent updates                                      |
| Runbook reset is real and recoverable        | runbook integration                                         | reset committed runbook; assert starter; refresh; assert exact starter and dirty semantics | server content immediately or silently replaces reset                       |
| Shared consumers remain regression-safe      | Plan, Build, runbook, workspaceDocument, Agent Interaction  | complete focused suites                                                                    | any consumer remains untested or regresses                                  |
| Server snapshot remains atomic               | registry + writer                                           | existing concurrent old-or-new test rerun                                                  | mixed record/content revision                                               |
| Commit receipt remains authoritative         | writer + hook                                               | receipt/snapshot agreement and commit-success/verification-failure proofs                  | second GET decides whether save occurred                                    |
| URL and accepted context remain aligned      | Build page + Agent Interaction                              | back/forward and rejected selection tests                                                  | URL points to one UUID while accepted context remains another               |
| Documentation becomes truthful               | plan + handoffs + roadmap                                   | atomic diff records PR #399 historical gap, hardening result, next base, and next gate     | docs claim completion without produced evidence                             |

### Required automated commands

Run from repository root unless noted:

```bash
uv run pytest tests/test_workspace_document_registry.py
uv run pytest tests/test_live_tiptap_markdown_write.py
```

Run from `apps/live-control-ui`:

```bash
npm test -- --run src/workspaceDocument
npm test -- --run src/buildSurface
npm test -- --run src/planSurface
npm test -- --run src/tiptap/MarkdownEditorCore.test.tsx
npm test -- --run src/tiptap/TiptapCalloutBridgeSpike.test.tsx
npm test -- --run src/tiptap/state/tiptapLocalState.test.ts
npm test -- --run src/agentInteraction/AgentInteractionProvider.test.tsx src/App.test.tsx
npx tsc --noEmit
npm run build
```

Return to repository root:

```bash
git diff --check
git diff --stat ea7ad826a2ca4f9d275ce245a3884d4af72278a8...HEAD -- \
  Docs/Plans/HANDOFF-bld05a-post-merge-authoring-hardening.md \
  Docs/Plans/HANDOFF-bld05a-workspace-document-authoring-seam.md \
  Docs/Plans/PLAN-build-surface-worldbuilding-ingest-pr-slices.md \
  Docs/Plans/ROADMAP-build-surface-worldbuilding-ingest.md \
  apps/live-control-ui/src/workspaceDocument \
  apps/live-control-ui/src/tiptap/MarkdownEditorCore.tsx \
  apps/live-control-ui/src/tiptap/MarkdownEditorCore.test.tsx \
  apps/live-control-ui/src/tiptap/TiptapCalloutBridgeSpike.tsx \
  apps/live-control-ui/src/tiptap/TiptapCalloutBridgeSpike.test.tsx \
  apps/live-control-ui/src/buildSurface \
  apps/live-control-ui/src/planSurface/components/PlanSurfaceCanvas.tsx \
  apps/live-control-ui/src/planSurface/PlanSurfaceShell.test.tsx \
  apps/live-control-ui/src/agentInteraction/AgentInteractionProvider.test.tsx \
  apps/live-control-ui/src/App.test.tsx

git diff --name-only ea7ad826a2ca4f9d275ce245a3884d4af72278a8...HEAD
```

If a named test path does not exist before implementation, create it only when listed in §4. Do not silently replace a missing owning-boundary test with a lower-level test.

### Minimal live proof

Use the existing Plan, Build, and runbook surfaces. Do not build a new dogfood or diagnostics panel.

```text
Scenario 1 — Build first edit
Open an authorized worldbuilding source.
Perform one paste.
Observe Unsaved local changes and enabled Save.
Refresh.
Observe exact pasted content.

Scenario 2 — rejected Build identity
Open an authorized Build document, then navigate to a Plan UUID in /build.
Observe explicit rejection.
Inspect Agent Interaction.
Observe no rejected UUID, revision, path, or hash and no stale prior Build document scope.

Scenario 3 — Plan commit
Make one Plan edit and commit.
Observe one parent document update and stable render.

Scenario 4 — runbook reset
Open committed runbook.
Reset to starter.
Observe starter content and dirty state when different.
Refresh.
Observe exact starter content.
```

Capture concise evidence: scenario, observed state, and whether browser console produced repeated render/update warnings. This is proof, not the successor polish/dogfood study.

### Baseline failure protocol

For every required command that fails on base:

| Command     | Base result | Head result | New failure? | Acceptance effect                   | Waiver                           |
| ----------- | ----------- | ----------- | -----------: | ----------------------------------- | -------------------------------- |
| `<command>` | `<exact>`   | `<exact>`   |       Yes/No | blocked or explicit waiver required | none unless operator records one |

Do not call the gate green when a required suite remains failing. No waivers are presumed.

---

## §8 Required implementation handback

The PR body must use the invariant above verbatim and include:

1. Base SHA.
2. Head SHA.
3. Actual changed paths.
4. Focused diff stat limited to §4.
5. Every §7 command with exact result.
6. Evidence provenance: author-local, independently rerun local, CI, or manual.
7. The adversarial sequence and observed result for each evidence-ledger row.
8. Baseline failures with base/head comparison.
9. Explicit waivers; write `none` when none exist.
10. Paths outside §4; write `none` or include a stop report.
11. Stop conditions encountered and resolution.
12. Deviations from §6 matrices; write `none` when none exist.
13. Confirmation that no extraction, SourceArtifact, ExtractionRun, Graph Review, or publication capability was delivered.
14. Confirmation that the successor remains unimplemented.
15. Confirmation that this handoff was implemented without compression or omitted constraints.

### Required PR-description skeleton

```markdown
## Outcome

Plan, Build, and runbook preserve one authorized workspace-document identity and revision through commit verification, first-edit persistence, cross-surface rejection, Plan handback, and runbook reset, so the merged BLD-05a seam becomes a truthful base for bounded authoring polish and dogfood.

## Merge-ready invariant

For one workspace-document UUID, the server snapshot, durable commit receipt, local/editor base, URL selection, surface authority, lifecycle display, and Agent Interaction context identify the same authorized document revision; any mismatch fails safely without unintended mutation and provides an explicit recovery path.

## Evidence required to merge

| Guarantee | Owning boundary | Required evidence | Produced result |
|---|---|---|---|

## Scope and explicit deferrals

## Evidence produced

### Automated
### Adversarial
### Regression
### Manual

## Documentation synchronization

## Gaps, waivers, and stop conditions
```

---

## §9 Acceptance rubric

Accept only when every item is true.

* [ ] Verification exact-match logic compares document ID, committed revision, content hash, and fingerprint against the authoritative receipt.
* [ ] A verification snapshot at N+1 cannot advance expected revision while the editor retains N content.
* [ ] A real edit made during verification remains persisted and dirty after verification resolves.
* [ ] The first real editor transaction persists on Plan, Build, and runbook with no second transaction required.
* [ ] Any update suppression is tied to a specifically identified programmatic replacement, not “the next update.”
* [ ] Build rejects Plan and runbook UUIDs before accepted local state, editor, save, scope, or context is established.
* [ ] Navigating from a valid Build document to a rejected UUID clears stale accepted Build document context.
* [ ] Plan invokes its parent commit callback exactly once per unique receipt and rendering stabilizes.
* [ ] Runbook reset replaces the editor with exact starter content, is dirty iff it differs from committed content, and survives refresh.
* [ ] Existing discard, verification-failure, URL history, draft labeling, nullable worldbuilding session, atomic snapshot, and authoritative-receipt behavior remain green.
* [ ] Every behavioral guarantee is proved at its owning boundary.
* [ ] No unexpected path changed.
* [ ] No new local-state schema, server API, durable identity, extraction contract, or publication path was introduced.
* [ ] Documentation records PR #399 as merged with incomplete evidence rather than rewriting history.
* [ ] The hardening PR’s actual proof is recorded with provenance.
* [ ] The next immutable base and active gate are explicit.
* [ ] The bounded authoring polish/dogfood successor remains unimplemented and unclaimed.

---

## §10 Reviewer protocol

Review from the invariant, not from the patch list.

1. Reproduce each of the five merged failure sequences before judging the fix.
2. Inspect receipt application and verification as separate transitions.
3. Verify that verification cannot update expected CAS before agreement is established.
4. Inject an editor update while verification is unresolved.
5. Inspect all three consumers for first-update behavior; do not infer from one shared-hook test alone.
6. Open Build with wrong-kind UUIDs from both a clean start and after a valid Build document.
7. Inspect Agent Interaction scope and source envelope, not merely DOM editor absence.
8. Count Plan callback invocations and check render stabilization.
9. Reset a committed runbook, remount/refresh, and compare exact exported Markdown.
10. Rerun backend atomicity and receipt tests even if untouched.
11. Compare actual changed paths against §4.
12. Verify documentation changes distinguish historical merge state from newly produced hardening evidence.
13. Confirm the successor is only named, not implemented.

### Prior finding ledger

| Prior finding                                      | Required closure                                        |
| -------------------------------------------------- | ------------------------------------------------------- |
| Verification may adopt unseen N+1                  | Agreement gate plus mismatch/reconciliation proof       |
| First real editor transaction may be swallowed     | one-transaction proof on all consumers                  |
| Rejected authority leaks Agent Interaction context | accepted-state-only exposure and context clearing proof |
| Plan post-commit callback may loop                 | receipt consumption proof with callback count one       |
| Runbook reset reopens committed content            | starter-local dirty reset and refresh proof             |

A finding closes only when the ordered failure sequence is impossible and proved.

---

## §11 Atomic documentation synchronization and bridge

Do not update documents to “complete” before evidence exists.

When the hardening PR is ready to merge, update the documentation in the same accepted change set:

### Historical PR #399 record

Record:

```text
state: merged
merge_sha: ea7ad826a2ca4f9d275ce245a3884d4af72278a8
judgment: merged_with_incomplete_evidence
waiver: none recorded
consequence: post-merge hardening remained the active gate
```

Do not erase the original missing-evidence ledger.

### Hardening PR record

Add:

```text
state: accepted/merged only after proof
base_sha: ea7ad826a2ca4f9d275ce245a3884d4af72278a8
head_sha: <actual>
merge_sha: <actual>
invariant: <verbatim §1 invariant>
evidence: proved / newly fixed / waived / unresolved
provenance: exact command or manual scenario
```

### Original BLD-05a handoff

Change from stale `ACTIVE / REQUEST_CHANGES` to a terminal historical status that says:

* PR #399 merged before its evidence ledger was complete;
* this post-merge hardening handoff became the active gate;
* the final hardening result and merge SHA;
* archive location according to repository convention.

### Roadmap/current state

After hardening merges:

```text
Shared authoring seam hardened
→ bounded authoring polish and dogfood is the active next gate
→ extraction controls remain blocked until polish findings exist and their invariant/evidence ledger are critiqued
```

### Bridge contract into the next PR

The successor begins from the hardening merge SHA, not PR #399’s merge SHA.

The successor may cover only:

* state and conflict language;
* save and recovery affordances;
* document navigation;
* creation and classification usability;
* Agent Interaction context visibility;
* visual consistency across Plan, Build, and runbook;
* realistic authoring and recovery dogfood scenarios.

The successor must not include by default:

* extraction controls;
* SourceArtifact creation;
* ExtractionRun launch or recovery;
* Graph Review handoff;
* graph publication;
* a new authoring state machine;
* a new durable identity or persistence contract;
* broad Plan layout redesign.

Before dispatching that successor, copy forward:

1. hardening merge SHA;
2. final green evidence ledger;
3. any manual authoring friction observed during the minimal live proof;
4. any remaining explicitly waived limitation;
5. confirmed lifecycle vocabulary and recovery actions available to polish.

Dogfood findings that reveal a new invariant must be recorded as a stop condition or named successor, not silently absorbed.

---

## Stop conditions

Stop and report instead of broadening scope when any of the following is discovered:

* preserving edits during verification requires a new durable local-state schema;
* receipt/snapshot agreement cannot be proved from existing response fields;
* clearing rejected Build context requires a new app-wide Agent Interaction contract rather than using existing provider behavior;
* runbook reset requires a new server mutation;
* first-transaction correctness requires replacing the editor architecture rather than fixing update ownership;
* a path outside §4 or its bounded exceptions is required;
* a required suite fails on base and needs operator waiver;
* current `main` materially changes the predecessor contracts;
* the fix would add extraction, document management, graph review, or publication behavior;
* documentation cannot be synchronized atomically with the accepted hardening result.

Use:

```text
Stop condition:
Why the current invariant cannot absorb it:
New public/durable contract discovered:
Affected observable paths:
Affected ownership layers:
Required path outside scope:
Proposed successor:
Tracker/authority update needed:
Operator decision required:
```

---

## Final dispatch check

* [ ] The base SHA is current and immutable.
* [ ] The five prior failure sequences are understood before code changes.
* [ ] The invariant is copied verbatim into the PR body.
* [ ] Every changed path fits §4.
* [ ] Every §6 matrix is implemented or a stop condition is raised.
* [ ] Every material guarantee has an owning-boundary test.
* [ ] The minimal live proof uses existing surfaces only.
* [ ] PR #399 history is preserved truthfully.
* [ ] No successor behavior is claimed.
* [ ] The next PR’s base and gate will be explicit after merge.