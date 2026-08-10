# HANDOFF — DOGFOOD-POLISH: generalized intentional workspace-document create

**Created:** 2026-08-10
**Status:** READY FOR IMPLEMENTATION
**Repository:** `Drakosfire/DungeonMindBuddy`
**Observed `main` anchor:** `81e7b5d71ff647e17fe806bb4ab851f6800b478c`
**Suggested branch:** `agent/dogfood-polish-workspace-document-create`
**Suggested PR title:** `DOGFOOD-POLISH: generalize intentional workspace document creation`
**Canonical handoff path:** `Docs/Plans/HANDOFF-BUILD-dogfood-polish-generalized-workspace-document-create.md`

**Predecessor:** PR #541 — `DOGFOOD-POLISH: choose active Plan prep document`
**Required successor:** `DOGFOOD-POLISH: surface context bar`
**Independent successor:** `DOGFOOD-POLISH: preserve Plan Ask continuity across prep-document switches`

---

## §0 Mission

Make **creating a workspace document an intentional, reusable product capability** rather than a collection of unrelated surface-specific calls to `createWorkspaceDocument`.

Plan is the first real consumer:

```text
Plan
  → Create New Prep
  → explicit Plan creation metadata
  → shared kind-aware workspace-document creation
  → server issues exact opaque documentId
  → exact document resolves successfully
  → active Plan document changes
  → URL commits exact documentId
  → Canvas lands on the newly created prep
```

The implementation must establish a shared creation contract that can later serve `worldbuilding_source` and `runbook` without rewriting document identity, create-state, retry, or activation semantics.

This is **not** permission to build a generic document-management application.

### Merge-ready invariant

At every successful creation:

> Exactly one user creation intent produces exactly one durable workspace document. The server-issued opaque `documentId` is the only new document identity. A surface may become active on that document only after the exact created identity has been resolved/admitted. URL/history, Canvas, and surface publication commit that same identity together.

And on failure:

> A failed create never changes the current document. A successful create followed by failed activation never creates a second replacement document on retry.

---

## §1 Why this slice exists

PR #541 solved intentional **selection** of an existing Plan prep document.

Dogfood immediately exposed the missing half:

* switching among old prep documents works;
* creating the prep document the GM actually wants to work on does not;
* Plan only creates implicitly when there are zero active Plan records;
* Build has its own bare-entry `worldbuilding_source` auto-create behavior;
* the runbook spike has another local create path;
* all three ultimately call the same `createWorkspaceDocument` API.

The product problem is therefore not:

> “Add a button in Plan that POSTs a document.”

It is:

> “Define what intentional workspace-document creation means once, then let Plan become the first surface to consume it.”

The dogfood judgment also established that the eventual home for Plan selection/creation is a shared **surface context bar**. That placement work is deliberately a successor. Do not make this PR wait for it.

---

## §2 Current authority and observed implementation

### Workspace registry

The server already owns:

* server-issued UUID `document_id`;
* `kind = plan | runbook | worldbuilding_source`;
* campaign identity;
* Plan/runbook `target_session` and `target_relpath`;
* worldbuilding-specific metadata validation;
* worldbuilding target path generation;
* registry persistence.

Do **not** add a second document-create endpoint.

### Plan

Current Plan behavior already provides the hard identity/navigation predecessor:

* exact `?documentId=<uuid>` selection;
* resolve-first navigation;
* `pushState` for intentional document changes;
* `replaceState` canonicalization for bare/default resolution;
* stale-resolution generation fencing;
* failure keeps the current Canvas authoritative;
* unrelated query parameters remain preserved;
* Canvas local state remains keyed by opaque `documentId`.

Preserve those rules.

Current Plan also has an implicit zero-record bootstrap in `resolvePlanningDocument` that creates a Plan document automatically.

That implicit bootstrap should be removed as the normal zero-document product behavior. An empty Plan registry should become an explicit empty state with **Create New Prep**.

### Build

`BuildSurfacePage.tsx` currently auto-creates `worldbuilding_source` on bare Build entry with:

* `"Untitled worldbuilding source"`;
* `source_domain = worldbuilding`;
* document class;
* authority state;
* visibility state;
* its own StrictMode/in-flight create latch;
* its own landing/navigation rules.

Do not change Build behavior in this PR.

Treat it as the second characterized creation shape demonstrating why the shared contract must not encode Plan assumptions.

### Runbook

`tiptapRunbookDescriptors.ts` also creates through the workspace registry when its expected runbook does not exist.

Do not migrate or redesign the runbook spike here.

---

## §3 Capability decomposition

This PR includes four inseparable pieces.

### A. Shared kind-aware creation intent

Introduce a workspace-document-owned client contract representing valid creation intent by kind.

The exact TypeScript spelling is flexible, but the conceptual shape should be discriminated:

```ts
type WorkspaceDocumentCreateIntent =
  | {
      kind: "plan";
      campaignId: string;
      title: string;
      targetSession: number | null;
      targetRelpath: string | null;
    }
  | {
      kind: "runbook";
      campaignId: string;
      title: string;
      targetSession: number | null;
      targetRelpath: string | null;
    }
  | {
      kind: "worldbuilding_source";
      campaignId: string;
      title: string;
      documentClass: string;
      authorityState: WorldbuildingAuthorityState;
      visibilityState: WorldbuildingVisibilityState;
    };
```

The shared layer converts this to the existing API `CreateWorkspaceDocumentRequest`.

Important properties:

* Plan/runbook cannot accidentally send worldbuilding metadata.
* `worldbuilding_source` cannot supply its own `target_relpath`.
* `source_domain: "worldbuilding"` is derived by the shared worldbuilding mapping, not repeatedly invented by callers.
* the contract remains keyed by the existing `WorkspaceDocumentKind`;
* no surface name appears in document identity.

Suggested ownership:

```text
apps/live-control-ui/src/workspaceDocument/
  workspaceDocumentCreation.ts
  workspaceDocumentCreation.test.ts
```

A shared React hook/state helper is acceptable if useful, but the durable abstraction is the **creation contract**, not a particular hook.

### B. Shared create lifecycle

Intentional creation must have one reusable lifecycle:

```text
idle
  → creating
  → created(exact server record)
  → resolving/admitting exact documentId
  → activated
```

Failure lanes:

```text
create failed
  → current document untouched
  → retry may POST again

create succeeded, activation failed
  → created record retained
  → current document untouched
  → retry activation of SAME documentId
  → MUST NOT POST another document
```

The shared creation path must prevent duplicate POSTs from double click, repeated submit, or component re-render.

A button being visually disabled is not sufficient proof. Use an in-flight latch/ref or equivalent state authority.

### C. Shared exact-document navigation primitive

The query helper introduced by #541 is conceptually workspace-document behavior, not Plan behavior.

Hoist:

```text
planDocumentSelectionSearch(...)
```

into a workspace-document-owned exact-ID navigation helper, e.g.:

```text
workspaceDocumentSelectionSearch(currentSearch, documentId)
```

Rules remain identical:

* only `documentId` changes;
* `session` remains graph/memory focus;
* `campaigns`, `campaign`, `tool`, `dogfood`, and other unrelated state are preserved;
* title, session number, target path, list position, or kind are never URL document identity.

Plan selection and Plan creation should consume this shared helper.

Do not create another create-specific URL builder.

### D. Plan `Create New Prep`

Plan consumes A–C.

This is the proof that the abstraction is usable, not merely extracted code.

---

## §4 Plan product behavior

### 4.1 Empty Plan

Today:

```text
no active Plan docs
  → resolvePlanningDocument silently creates one
```

After this PR:

```text
no active Plan docs
  → Plan renders usable empty state
  → "No prep documents yet"
  → Create New Prep
```

No durable document should be minted merely because the operator navigated to Plan.

This is the first intentional-creation proof.

### 4.2 Existing Plan document

When a document is already active, keep the #541 selector and add a quiet **Create New Prep** affordance adjacent to it.

Do not move either control into AppChrome in this slice.

Temporary shape:

```text
Prep document  [ C2 Session 26 Prep ▾ ]   [ Create New Prep ]
```

The surface-context-bar successor will relocate this group later.

### 4.3 Creation form

`Create New Prep` opens a small bounded form/popover/inline panel.

Required editable fields:

* **Target session**
* **Title**

Not exposed in the first UI:

* `documentId`
* `target_relpath`
* status
* revision
* content status
* graph session/lens
* registry metadata

Target path is derived from the Plan creation policy.

Initial target-session suggestion:

1. start at `planView.session + 1`;
2. if loaded active Plan records already occupy that session or later sessions, suggest the next higher unused session;
3. suggestion is metadata only and remains editable.

Example:

```text
live session: 25
active prep targets: 26, 27

Create New Prep
  Target session: 28
  Title: C2 Session 28 Prep
```

The title may initially follow the target-session suggestion. Once the operator edits the title manually, do not keep overwriting it.

### 4.4 No fake durable paths

Current `defaultPlanTargetRelpath` can return a sentinel `"TBD durable planning path"` for unsupported campaign shapes.

Intentional creation must never persist that as though it were a real target.

For a campaign without a known Plan target-path policy:

* Create is disabled/fails closed;
* explain that a durable Plan path cannot yet be derived;
* do not POST a registry record.

A placeholder string is not document authority.

### 4.5 Successful create

Given active A:

```text
A active
→ operator submits Create New Prep
→ POST once
→ server returns record B with opaque documentId B
→ resolve/admit exact B
→ only then push history entry naming B
→ Canvas B mounts
→ Plan publication identity becomes B
→ selector refreshes and includes B
```

The create response establishes the new identity, but Plan should still use the #541 exact resolution/admission path before committing browser/surface activation.

Do not infer the newly created document from “first record in refreshed list.”

### 4.6 Browser history

Creation is intentional navigation.

Therefore:

```text
A
→ Create B
→ Back
= exact A

Forward
= exact B
```

Creation success uses one history entry.

Do not stack transient form/create URLs.

### 4.7 Existing dirty draft

A may contain unsaved local changes.

Creating B must not:

* auto-save A;
* discard A;
* copy A into B;
* block creation merely because A is dirty.

The existing documentId-keyed authoring state remains authority.

Proof:

```text
edit A locally
→ Create B
→ B active
→ Back / select A
→ A local draft recovered
```

### 4.8 Create failure

If POST fails:

```text
A remains Canvas
A remains URL
A remains Plan publication
form remains recoverable
error is visible
retry is allowed
```

### 4.9 Created but activation fails

This state is materially different from create failure.

Example:

```text
POST B succeeds
exact GET/activation B fails
```

Required behavior:

* A stays active.
* B's exact `documentId` is retained.
* refresh the document list if possible so B becomes discoverable.
* tell the operator that the prep was created but could not be opened.
* offer **Retry open** or equivalent.
* retry must resolve B.
* retry must not create C.

This is a merge-blocking correctness rule.

### 4.10 Competing navigation while create is pending

A slow create must not hijack a newer browser/surface decision.

If:

```text
Create B begins
→ browser history / another document navigation supersedes it
→ B POST eventually succeeds
```

then:

* the durable B may now exist;
* refresh the selector/list;
* do not force navigation back to B if its creation intent is stale;
* never lose B;
* never overwrite the newer current document.

Creation and selection/history need one coherent stale-intent rule.

Do not solve this by disabling browser navigation.

---

## §5 Durable target-path collision safety

Intentional creation makes a previously rare registry hazard normal:

Two opaque workspace document IDs must not silently point at the same durable Markdown target.

The current registry accepts caller-provided `target_relpath` for Plan/runbook and does not make that target identity unique.

### Required server hardening

For non-null caller-owned `target_relpath`:

```text
if another workspace record already owns the same durable target_relpath:
    reject create with 409
    do not append a new registry record
```

Apply the check while holding the registry mutation lock.

This should cover active and discarded records. Discarding document identity does not make its durable target safe to silently re-own.

`worldbuilding_source` is unaffected because its target path is server-generated from its new UUID.

Do not add:

* automatic filename suffixes;
* title-based collision identity;
* silent reuse of an existing document;
* automatic restore of a discarded document.

Those are separate product semantics.

### Preflight stop condition

Before enforcing this invariant, run a read-only scan of the current workspace registry.

If existing production/dev registry state already contains duplicate non-null `target_relpath` ownership, **STOP** and report the records rather than choosing one authority or rewriting them in this PR.

---

## §6 Shared creation does not mean shared surface policy

The workspace-document layer owns:

* legal kind-specific creation intent;
* API request construction;
* single-create/in-flight behavior;
* exact created record/documentId;
* create-vs-created-but-not-activated distinction;
* exact-ID navigation helper.

The surface owns:

* whether creation is offered;
* wording;
* metadata suggestions;
* where the control appears;
* how the new document is admitted;
* which Canvas adapter opens it;
* surface publication after activation;
* surface-specific history policy using the shared exact-ID helper.

Therefore:

```text
workspaceDocument/
  knows "plan"
  does NOT know "PlanSurfaceShell"
```

and:

```text
workspaceDocument/
  knows "worldbuilding_source"
  does NOT know "/build should auto-create on bare entry"
```

---

## §7 Build/runbook proof without migration

Do not absorb Build or runbook UX migration.

However, the shared contract must prove it is genuinely kind-parameterized.

Unit proof should include at least:

### Plan intent

```text
kind=plan
→ target session/path allowed
→ no worldbuilding metadata
```

### Worldbuilding intent

```text
kind=worldbuilding_source
→ source_domain=worldbuilding
→ class/authority/visibility required
→ caller target_relpath impossible/omitted
```

### Runbook intent

```text
kind=runbook
→ session/path supported
→ no worldbuilding metadata
```

If a second kind requires changing Plan-specific types or URL semantics, the abstraction has failed.

Runtime migration of:

* Build bare auto-create;
* North Gate runbook bootstrap;

remains a later cleanup and is not a merge requirement.

---

## §8 Agent Interaction boundary

Do not change:

* `agentInteractionHistory.ts`;
* Plan thread storage keys;
* Hermes session ownership;
* thread continuity semantics;
* AgentInteractionProvider ownership.

Today Plan Ask continuity is document-scoped.

Creating B may therefore present the same known behavior as selecting B under #541.

That is still the explicit successor:

**DOGFOOD-POLISH: preserve Plan Ask continuity across prep-document switches**

Do not hide that migration inside document creation.

Cross-document thread contamination or actual thread loss is a correctness failure; document-scoped continuity itself remains the known successor behavior.

---

## §9 Surface-context-bar boundary

Dogfood also established:

> prep selection/create belongs with graph-load status in a shared surface-context bar.

Do not implement that here.

This PR may add the create affordance beside the current selector in Plan so the workflow can be used and dogfooded.

Explicit successor:

**DOGFOOD-POLISH: surface context bar**

That successor owns:

* AppChrome/shared host composition;
* always-visible graph-load state;
* relocation of Plan prep selector;
* relocation of Create New Prep;
* Build retaining graph context without Plan-only document chrome.

No AppChrome ownership migration is required for this PR.

---

## §10 Document bookkeeping — part of this PR

The operator explicitly requested that bookkeeping travel with this capability.

### 10.1 Check in this handoff

Add:

```text
Docs/Plans/HANDOFF-BUILD-dogfood-polish-generalized-workspace-document-create.md
```

Do not create another roadmap or product architecture document for the same capability.

### 10.2 `Backlog.md`

Update the existing creation entry rather than duplicating it:

```text
[IDEA] Generalized intentional workspace-document create
```

→

```text
[DOING] Generalized intentional workspace-document create
```

Add:

* this handoff path;
* implementation branch;
* predecessor #541;
* clear statement that Plan is consumer #1.

Promote:

```text
[IDEA] Surface context bar (prep doc + always graph load)
```

→

```text
[READY] Surface context bar (prep doc + always graph load)
```

Add dependency:

```text
after generalized intentional workspace-document create
```

Do not dispatch it in the same PR.

### 10.3 Close stale #529 bookkeeping

`Backlog.md` currently still contains:

```text
[DOING] Finish DOGFOOD-POLISH semantic prep authoring
```

PR #529 is merged.

Remove that active entry and append it to `Backlog-DONE.md` as:

```text
[DONE] Finish DOGFOOD-POLISH semantic prep authoring
```

Record:

```text
PR #529
merge: 95a2fbc7725ce2f65e6d63ccaa11a1db5458baf9
```

Preserve its original Context / Insight / Action text and add a concise Outcome.

### 10.4 Do not touch unrelated sequencing authority

Do not update merely for bookkeeping:

* Campaign Supergraph PR tracker;
* Campaign Supergraph roadmap;
* World Graph status guide;
* README;
* architecture authorities.

This is a DOGFOOD-POLISH product capability, not a change to Supergraph critical-path sequencing.

### 10.5 Merge bookkeeping

Do **not** mark generalized creation DONE inside its own unmerged branch.

At implementation time it is `[DOING]`.

After merge, the normal `/done` bookkeeping should move it to `Backlog-DONE.md` with the merge SHA.

---

## §11 Expected implementation surface

Likely new shared files:

```text
apps/live-control-ui/src/workspaceDocument/workspaceDocumentCreation.ts
apps/live-control-ui/src/workspaceDocument/workspaceDocumentCreation.test.ts
apps/live-control-ui/src/workspaceDocument/workspaceDocumentNavigation.ts
apps/live-control-ui/src/workspaceDocument/workspaceDocumentNavigation.test.ts
```

A shared hook is acceptable if useful:

```text
apps/live-control-ui/src/workspaceDocument/useWorkspaceDocumentCreation.ts
```

Likely Plan changes:

```text
apps/live-control-ui/src/planSurface/PlanSurfaceShell.tsx
apps/live-control-ui/src/planSurface/PlanSurfaceShell.test.tsx
apps/live-control-ui/src/planSurface/components/PlanDocumentSelector.tsx
apps/live-control-ui/src/planSurface/components/PlanDocumentSelector.test.tsx
apps/live-control-ui/src/planSurface/config/planSessionDescriptor.ts
apps/live-control-ui/src/planSurface/config/planSessionDescriptor.test.ts
apps/live-control-ui/src/planSurface/planSurface.css
```

A small sibling create component is preferable to turning the selector into a document-management component, e.g.:

```text
apps/live-control-ui/src/planSurface/components/PlanDocumentCreateControl.tsx
```

Likely server hardening:

```text
apps/live_control_server/services/workspace_document_registry.py
tests/...workspace_document_registry...
```

Use the repository's actual owning test file names after discovery.

Bookkeeping:

```text
Backlog.md
Backlog-DONE.md
Docs/Plans/HANDOFF-BUILD-dogfood-polish-generalized-workspace-document-create.md
```

---

## §12 Explicit non-goals

Do not add:

* rename document;
* archive/delete/restore UI;
* document search;
* favorites/recents;
* cross-campaign document manager;
* arbitrary target-path editor;
* Plan session as document identity;
* automatic graph-lens changes when a prep is created;
* Agent thread migration;
* AppChrome/surface-context-bar implementation;
* Build create UX redesign;
* Build auto-create removal;
* runbook UX redesign;
* generic “New Document” dashboard;
* new workspace-document backend endpoint;
* graph writes;
* corpus ingestion;
* auto-save of the document being left.

---

## §13 Suggested implementation sequence

### Commit 1 — bookkeeping + shared exact-ID ownership

* check in handoff;
* update Backlog / Backlog-DONE;
* hoist #541 query helper into `workspaceDocument`;
* keep Plan behavior unchanged;
* tests prove query preservation.

### Commit 2 — shared kind-aware creation contract

* discriminated create intent;
* request mapping;
* shared create lifecycle/in-flight protection;
* Plan/runbook/worldbuilding unit characterization.

No Plan UI yet.

### Commit 3 — registry target ownership guard

* read-only duplicate-path preflight;
* server rejects duplicate non-null target paths atomically;
* owning tests;
* no live registry rewrite.

### Commit 4 — Plan intentional creation

* remove silent Plan zero-record bootstrap;
* empty-state Create New Prep;
* existing-document Create New Prep control;
* metadata form/defaults;
* create → exact resolve → activate → history;
* create failure and created-but-not-activated recovery.

### Commit 5 — adversarial proof

* double-submit;
* stale create completion;
* dirty A → create B → return A;
* browser history;
* query preservation;
* list refresh;
* invalid path policy;
* duplicate target collision;
* publication identity.

Do not split the PR into review nano-cycles unless a genuinely material issue is found.

---

## §14 Automated proof

### Shared creation

Prove:

* each kind maps to a legal existing API request;
* illegal cross-kind metadata cannot be constructed or is rejected;
* double invocation while one create is in flight performs one POST;
* created result exposes exact server `document_id`;
* created-but-activation-failed state retains the exact record;
* activation retry cannot issue a second POST.

### Registry

Prove:

* Plan/runbook target-path collision → 409;
* registry record count unchanged after rejection;
* discarded target still cannot be silently re-owned;
* two distinct target paths create distinct UUID documents;
* worldbuilding server-generated path remains UUID-bound.

### Plan

Required integration proofs:

1. no active Plan docs → no automatic POST on page load;
2. empty state exposes Create New Prep;
3. create B from A → exact B Canvas;
4. URL names B only after exact resolution;
5. Plan publication identity names B;
6. selector refresh contains B;
7. Back returns exact A; Forward returns exact B;
8. `session`, `campaigns`, `tool`, `dogfood` survive;
9. create POST failure leaves A exactly authoritative;
10. create succeeds / B activation fails → A retained, B retained, Retry Open does not POST again;
11. duplicate submit → one document;
12. slow create superseded by history/navigation cannot hijack current document;
13. dirty A survives A → Create B → A;
14. unknown durable-path policy performs zero POST;
15. duplicate Plan target path performs zero second registry append.

Also preserve #541 selector race/failure/history tests.

### Suggested verification

From `apps/live-control-ui`:

```bash
npx vitest run \
  src/workspaceDocument/ \
  src/planSurface/config/planSessionDescriptor.test.ts \
  src/planSurface/components/PlanDocumentSelector.test.tsx \
  src/planSurface/PlanSurfaceShell.test.tsx

npx tsc --noEmit
npm run build
```

Run the owning workspace-registry Python test suite for server collision hardening.

Report actual base-vs-branch failures rather than expanding scope to unrelated pre-existing failures.

---

## §15 Code review gate

Review cumulative implementation, not PR-description compliance.

Ask:

1. Does the server still issue the only document identity?
2. Can one click/intent create more than one registry record?
3. Can activation failure cause retry to mint another document?
4. Can a stale create completion hijack a newer navigation choice?
5. Can two document IDs own the same durable target path?
6. Does URL/Canvas/publication always agree after activation?
7. Is `session` still only graph/memory focus?
8. Did shared code learn Plan-specific UI/surface behavior?
9. Could a `worldbuilding_source` adopt the creation primitive without changing its identity contract?
10. Did the PR accidentally redesign Build/runbook/AppChrome/Ask?

Material findings only.

When those are clean:

```text
CODE REVIEW: PASS
→ proceed to real-UI DOGFOOD pass
```

Do not merge before the dogfood pass.

---

## §16 Required real-UI dogfood pass

Use the actual Plan surface and real workspace registry.

### Scenario A — empty campaign

With a campaign that has no active Plan document:

* open Plan;
* verify no document appears merely from navigation;
* Create New Prep is understandable;
* create one;
* confirm immediate landing in the new Canvas.

Question:

> Does this feel like “I made the prep I am about to work on,” rather than registry administration?

### Scenario B — normal next-prep creation

From an existing prep:

* click Create New Prep;
* inspect suggested session/title;
* create;
* begin editing immediately.

Observe:

* number of decisions/clicks;
* whether “target session” is understandable;
* whether the title default is useful;
* whether the new document feels obviously active.

### Scenario C — history

```text
A
→ Create B
→ Back
→ Forward
```

Verify exact document identity and local draft state.

### Scenario D — dirty source document

Edit A without saving.

Create B.

Return to A.

Any data loss or cross-contamination is a **STOP**.

### Scenario E — validation/collision

Attempt to create a prep for a session/path already represented.

The product should explain the problem without UUID/provenance jargon and without silently creating a second document.

### Scenario F — failure

Exercise a failed create or unavailable API if practical.

The old prep must remain completely usable.

### Scenario G — Ask

Keep Ask open while creating/switching.

Record the existing document-scoped thread behavior.

Do not repair it here unless there is actual cross-document contamination or loss.

### Scenario H — placement

Judge the temporary selector + Create affordance only for usability.

Do **not** spend this PR polishing it into final chrome.

The already-queued surface-context-bar slice owns the durable placement.

---

## §17 Dogfood disposition

Exactly one:

### PASS

Creation is understandable, confident, and no material correction is needed.

### PASS WITH POLISH

One consolidated, creation-local polish pass only:

* wording;
* default title/session behavior;
* form spacing;
* validation message;
* loading state;
* focus/keyboard behavior;
* retry-open clarity.

Then one smoke pass.

Do not enter iterative visual review loops.

### STOP

Use only for a material product/correctness problem, such as:

* duplicate documents;
* ambiguous durable target ownership;
* data loss;
* wrong Canvas after creation;
* history identity failure;
* stale-create hijack;
* creation requires document-management semantics not designed here;
* shared abstraction cannot actually support another kind.

Name the missing capability instead of growing the PR indefinitely.

---

## §18 Acceptance checklist

Before merge:

* [ ] creation is explicit on Plan;
* [ ] Plan empty load creates nothing;
* [ ] shared contract is kind-parameterized;
* [ ] Plan is consumer #1, not owner of the shared primitive;
* [ ] server issues opaque `documentId`;
* [ ] new document resolves exactly before activation;
* [ ] URL/Canvas/publication agree;
* [ ] unrelated query state survives;
* [ ] one intent cannot double-create;
* [ ] activation retry cannot re-create;
* [ ] stale creation cannot hijack navigation;
* [ ] dirty previous document survives;
* [ ] durable target-path collision fails closed;
* [ ] no fake `"TBD durable planning path"` is persisted;
* [ ] Build runtime behavior unchanged;
* [ ] runbook runtime behavior unchanged;
* [ ] Agent Interaction ownership unchanged;
* [ ] surface-context-bar remains explicit successor;
* [ ] Backlog creation entry is DOING;
* [ ] surface context bar is READY;
* [ ] merged #529 stale DOING entry archived as DONE;
* [ ] code review passed;
* [ ] real UI dogfood performed;
* [ ] bounded polish, if any, completed.

---

## §19 Handback shape

Return:

### DOGFOOD-POLISH capability

`generalized intentional workspace-document create`

### PR / head

* PR number
* branch
* head SHA
* base SHA

### Shared contract now true

Describe:

* creation-intent types;
* create lifecycle;
* exact-ID navigation ownership;
* durable path collision behavior.

### Plan behavior now true

Describe:

* empty state;
* Create New Prep;
* metadata defaults;
* create/activate/history;
* failure/retry.

### Automated proof

Exact commands and results.

### Code review disposition

`PASS` or `STOP`

### UI dogfood disposition

`PASS`, `PASS WITH POLISH`, or `STOP`

Include:

* real document(s) created;
* what felt natural;
* friction;
* any polish performed;
* any correctness stop.

### Document bookkeeping

Confirm:

* Backlog entry → DOING;
* surface context bar → READY;
* #529 semantic-prep entry → DONE archive.

### What remains false

At minimum:

* Plan Ask continuity across document switches;
* shared surface-context bar;
* Build intentional-create UX / migration;
* runbook create migration;
* rename/archive/delete/document management.

### Recommended next slice

Default recommendation after successful dogfood:

**DOGFOOD-POLISH: surface context bar**

Unless dogfood produces a more fundamental creation blocker.

---

# Final product test

The PR succeeds if the GM can say:

> “I need a new prep document.”

…and DungeonBuddy can create exactly one durable workspace document, land them confidently on that exact document, preserve everything they were already working on, and do so through a creation contract that is clearly not owned by Plan.
