# HANDOFF — DOGFOOD-POLISH: Revision-Safe Build Document Rename

**Line of work:** DOGFOOD-POLISH
**Status:** DOING — dispatched after PR #558 merge
**Repository:** `Drakosfire/DungeonMindBuddy`
**Predecessor:** PR #558 — `FIX: Build document context campaign authority + single-lane admit`
**Predecessor reviewed head:** `ef5ba51399b2d7cdeba6eb04eadc21c70ec2b53e`
**Predecessor review:** Review Cycle 2 — PASS (`4911605708`)
**Base:** `main` after PR #558 merge — `53424b6dfcc4aab46fe53cab9496ba5ef9845df4`
**Branch:** `agent/dogfood-polish-build-document-rename`
**Suggested PR title:** `DOGFOOD-POLISH: rename Build sources without breaking Canvas CAS`
**Canonical handoff path:** `Docs/Plans/HANDOFF-BUILD-dogfood-polish-build-document-rename.md`

---

## §0 Mission

Let the operator rename the exact Build worldbuilding source they are currently authoring, directly from the `DOCUMENT` Surface Context, without changing document identity, losing local edits, invalidating Canvas authority, or creating an artificial conflict on the next Markdown save.

The visible operation is intentionally small:

```text
DOCUMENT
Ironveil Property ▾    C2 · lore    Unsaved changes    Rename    + New source
```

But the implementation is not merely a text-field PATCH.

Workspace-document metadata mutation increments the same registry `revision` used by Markdown authoring CAS. Therefore a rename from revision `N` to `N+1` must be adopted by the currently admitted `MarkdownCanvasSession` as a **metadata-only revision rebase** while preserving the exact editor body, content digest, dirty state, and local draft.

This PR closes the next concrete Build dogfood gap after intentional document context.

It does **not** generalize every metadata field.

---

## §1 Governing invariant

> **Renaming a Build source changes metadata for the same exact admitted `documentId`; the metadata PATCH is CAS-bound to the Canvas session's current revision, and the returned revision is rebased into that same live Canvas without changing its body, digest, dirty state, or work-object identity.**

More concretely:

```text
documentId      = immutable work-object identity

Canvas session  = authority for:
                  current revision
                  current server snapshot
                  dirty local draft
                  content SHA
                  Markdown save CAS

Surface Context = presentation + explicit rename affordance

Build controller = document selection/navigation policy
                   NOT authoring-revision authority

metadata PATCH  = one exact document mutation
                  against Canvas revision N
                  returning revision N+1

rename success  = same documentId
                  same Markdown/content SHA
                  revision N+1
                  new title
                  dirty remains whatever it was
```

A rename must never create a second authoring state machine beside Markdown Canvas.

---

## §2 Why this is the next PR

The older Build Plan-parity backlog sequenced:

1. insert exact World Graph references into Build Canvas,
2. document rename / light metadata + document actions,
3. shared Statblock/tool parity.

The first capability is already present in current Build composition:

* Build has a graph-reference search projection.
* exact graph objects can be viewed.
* `insertChip(nodeId)` resolves against the authorized live projection.
* object/campaign admission is checked.
* the canonical reference is inserted into the active Markdown Canvas.
* chip runtime can reopen inserted graph objects.

Do not build that capability again.

The remaining operator-facing document problem is that durable Build sources need useful identity labels after creation.

The previously imagined “Build heading bar” should also **not** be revived literally. Since Surface Context landed, title/status belong in the `DOCUMENT` context module and Save belongs in the shared Edit Host. Ready-state MarkdownCanvas deliberately suppresses duplicate document chrome.

This PR should follow the current architecture rather than recreate the pre-Surface-Context mockup.

---

## §3 Current-state observations that constrain the implementation

### 3.1 Build document selection is now separate from Canvas authority

`useBuildWorkspaceDocumentController` owns:

* exact `documentId` selection,
* resolve-before-navigation,
* browser history,
* New Source creation,
* selector list refresh.

`MarkdownCanvasSession` owns:

* accepted workspace snapshot,
* accepted registry record,
* loaded revision,
* content SHA,
* local dirty state,
* editor,
* save,
* reconciliation.

This boundary must become **stronger**, not blurrier, in this PR.

In particular:

> Do not use `controller.activeRecord.revision` as `expected_revision` for rename.

After a Markdown save, Canvas can hold a newer record than the controller's original preflight record.

---

### 3.2 The server already has the required mutation

Existing route:

```text
PATCH /api/live/workspace-documents/{document_id}
```

Existing metadata contract supports:

* `title`
* `target_session`
* `target_relpath`
* `document_class`
* `authority_state`
* `visibility_state`
* `expected_revision`

For this PR, use **title only**.

No new server endpoint is expected.

---

### 3.3 Metadata mutation advances workspace revision

The registry performs expected-revision checking and then advances:

```text
revision N → revision N+1
```

even when only `title` changed.

That revision also participates in Markdown prepare/commit authority.

Therefore this sequence is currently dangerous if implemented naïvely:

```text
Canvas loaded at revision 7
→ operator types unsaved Markdown
→ local draft base_revision = 7
→ rename PATCH succeeds
→ registry revision = 8
→ Canvas still thinks revision = 7
→ next Save attempts expected_revision = 7
→ conflict
```

That would make rename actively hostile to authoring.

The required sequence is:

```text
Canvas loaded at revision 7, dirty
→ rename PATCH expected_revision=7
→ server returns same documentId, revision=8, new title
→ Canvas adopts metadata revision 8
→ local dirty body remains untouched
→ local draft base_revision becomes 8
→ content SHA remains unchanged
→ next Save expected_revision=8
→ content commit succeeds
```

This is the central proof of the PR.

---

### 3.4 Existing command arbitration should own the race

`MarkdownCanvasSession` already exposes document-bound command arbitration through `runDocumentCommand`.

It already provides:

* exact selected-document capture,
* optional admission checks,
* single active document command,
* conflict/duplicate rejection,
* `AbortController`,
* invalidation on document change,
* invalidation on unmount.

Use it.

Do not create a second Build-specific async mutation generation system unless a concrete gap in `runDocumentCommand` is discovered.

---

## §4 Product behavior

### Loaded document

Current:

```text
DOCUMENT
Ironveil Property ▾    C2 · lore    Saved    + New source
```

Target:

```text
DOCUMENT
Ironveil Property ▾    C2 · lore    Saved    Rename    + New source
```

Exact visual ordering can follow the existing Surface Context grammar.

`Rename` should be a Build-owned Surface Context action.

---

### Rename interaction

Selecting `Rename` opens a compact popover.

Fields:

```text
Title
[ Ironveil Property                         ]

Cancel                         Rename source
```

Requirements:

* current authoritative title prefilled,
* text field receives a normal editable value,
* leading/trailing whitespace trimmed on submit,
* blank title cannot submit,
* title identical after trimming cannot submit,
* explicit submit only,
* blur does not PATCH,
* Enter may submit when valid,
* Escape/Cancel closes without mutation,
* no document ID, path, revision, SHA, or registry jargon in normal UI.

During request:

```text
Renaming…
```

Disable duplicate submission.

---

### Success

On successful rename:

* same `documentId`,
* same Canvas instance/editor,
* new title appears in DOCUMENT context,
* selector displays new title after refresh,
* revision advances to returned server revision,
* dirty state is preserved,
* body is preserved,
* content SHA is preserved,
* URL does not change,
* browser history gets no entry,
* World Graph lens does not change,
* no graph projection reload is caused solely by title change,
* Agent Interaction subsequently describes the same document with the new title.

Popover closes after the authoritative returned record has been adopted.

---

### Failure

If PATCH fails:

* old authoritative title remains visible,
* entered candidate title remains in the open rename form,
* document stays loaded,
* local Markdown draft stays intact,
* revision does not advance locally,
* selector is not rewritten optimistically,
* compact error appears in the popover.

Suggested generic copy:

```text
Could not rename this source.
```

For a stale-revision / 409 response, prefer:

```text
Source changed elsewhere. Reload before retrying.
```

Do not automatically discard, reload, or rebase a 409.

---

## §5 Scope: title only

This PR deliberately does **not** expose every field accepted by the metadata endpoint.

### Included

* `title`

### Deferred

#### `document_class`

The registry accepts free-form class strings, but the product does not yet have a sufficiently intentional operator vocabulary for general class editing.

#### `visibility_state`

`internal` / `player_safe` changes have policy implications and deserve an explicit product slice.

#### `authority_state`

Absolutely do not casually expose:

```text
draft → reviewed → canonical
```

as a generic metadata dropdown.

That is worldbuilding authority/promotion semantics and belongs behind its own governed workflow.

#### `campaign_id`

Not mutable through this metadata endpoint and not a rename concern.

#### `target_relpath`

Registry-owned for worldbuilding sources.

#### discard / restore

Document lifecycle is separate from rename.

Do not turn “Discard local draft” and “Discard source” into one ambiguous noun.

---

## §6 Desired architecture

### 6.1 Rename presentation belongs to Build Surface Context

Create a Build-owned component such as:

```text
BuildDocumentRenameControl.tsx
```

It owns:

* popover state,
* candidate title,
* form validation,
* error presentation.

It does not own workspace revision state.

---

### 6.2 Rename execution belongs to MarkdownCanvasSession

Add a neutral document-metadata command seam to the Canvas session rather than reaching around it from `BuildSurfaceContext`.

Preferred conceptual API:

```ts
session.updateDocumentMetadata({
  title: "Ironveil Property",
})
```

or an equivalently small neutral shape.

Internally it must use:

```text
runDocumentCommand
→ exact editable admission
→ admitted revision
→ PATCH exact document
→ validate response
→ metadata-only rebase
```

Do not make the generic Canvas layer understand Build or worldbuilding product semantics.

The generic layer may understand:

```text
metadata patch
document identity
revision
snapshot rebase
command arbitration
```

Build decides that this particular action is “Rename source.”

---

### 6.3 Command identity

Introduce a neutral command ID, e.g.:

```text
document.metadata.update
```

Do not call a generic Canvas command `build.rename`.

Build may alias it if needed for its publication inventory, as it already does with document Save.

Rename and Save must not run concurrently.

The command should:

```text
admission: editable
invalidateOnDocumentChange: true
```

---

### 6.4 Add metadata-only rebase to authoring

`useWorkspaceDocumentAuthoring` needs one bounded capability for adopting a successful metadata-only server mutation.

Conceptually:

```ts
adoptMetadataUpdate({
  previousRevision,
  record,
})
```

or equivalent.

Requirements before adoption:

1. returned `document_id` equals the active exact document,
2. existing snapshot is present,
3. mutation was launched from that snapshot's revision,
4. returned revision is the server-expected successor,
5. returned kind/status remain admissible for the live session.

For current registry semantics, normal successful transition is:

```text
N → N+1
```

If the response violates expected identity/revision semantics, fail closed rather than locally inventing state.

---

## §7 Metadata-only rebase contract

Given:

```text
snapshot:
  record.title = Old
  loaded_revision = N
  content_sha256 = H

localState:
  base_revision = N
  base_content_sha256 = H
  dirty = D
  tiptap_json = J
  exported_markdown = M
```

and successful metadata response:

```text
record:
  document_id = same ID
  title = New
  revision = N+1
```

the adopted state must become:

```text
snapshot:
  record = returned record
  loaded_revision = N+1
  markdown = unchanged
  content_sha256 = H
  file_fingerprint = unchanged
  file_exists = unchanged

localState:
  title = New
  base_revision = N+1
  base_content_sha256 = H
  dirty = D
  tiptap_json = J
  exported_markdown = M
  exported_markdown_authoritative = unchanged
```

Also:

```text
expectedRevisionRef = N+1
```

Crucially:

```text
documentKey = unchanged
```

A metadata rename must **not remount TipTap**.

That preserves:

* cursor/selection where possible,
* live editor instance,
* unsaved content,
* semantic node/chip state.

---

## §8 Surface Context should consume live Canvas authority

There is an architectural cleanup worth doing as part of this bounded slice.

Today `BuildSurfaceContext` is mounted outside `MarkdownCanvasSessionProvider`, so BuildShell mirrors:

```text
session.statusLabel
```

up through:

```text
onAuthoringStatusChange
→ controller.setAuthoringStatusLabel
→ BuildSurfaceContext
```

That is an authoring-state mirror created only because the context component cannot see the Canvas session.

Rename now needs the authoritative live Canvas record and revision too.

Do **not** expand that mirror to include:

```text
title
revision
metadata mutation state
...
```

Instead, restructure the active-document branch so loaded `BuildSurfaceContext` can consume `useOptionalMarkdownCanvasSession()` directly.

Conceptually:

```tsx
<AppChrome>
  {activeDocumentId ? (
    <MarkdownCanvasSessionProvider ...>
      <BuildSurfaceContext ... />
      <BuildReferenceCapability ...>
        ...
      </BuildReferenceCapability>
    </MarkdownCanvasSessionProvider>
  ) : (
    <>
      <BuildSurfaceContext ... />
      empty state
    </>
  )}
</AppChrome>
```

Exact composition can vary.

Rules:

* empty Build still gets DOCUMENT context without a Canvas session,
* loaded Build gets direct Canvas-session status/record authority,
* controller record remains selection/preflight state,
* accepted `session.record` wins for live title/revision/status,
* do not teach generic `SurfaceContextHost` anything about Markdown Canvas or Build.

After this, remove the `authoringStatusLabel` mirror if it no longer has another legitimate consumer.

---

## §9 Source-of-truth precedence

For a loaded Build document:

```text
session.documentId / session.record
    ↓
authoritative live work object

controller.activeRecord
    ↓
selection/preflight/navigation record
```

For rendering the active title:

```text
accepted session.record.title
    > controller.activeRecord.title
```

The latter may temporarily be useful during admission/loading but must not overwrite a newer Canvas record after Save or Rename.

For expected revision:

```text
session admitted envelope revision
    ONLY
```

Never:

```text
controller.activeRecord.revision
selector record.revision
URL
cached registry list record
```

---

## §10 Rename lifecycle

### Start

Operator clicks Rename.

Require:

* one accepted document,
* exact `session.documentId`,
* editable Canvas admission,
* no conflicting command,
* nonblank changed title.

Capture current admitted revision `N`.

---

### Execute

Call existing workspace metadata PATCH with:

```json
{
  "title": "<trimmed title>",
  "expected_revision": N
}
```

No other metadata fields.

---

### Validate response

Before local adoption:

* exact same `document_id`,
* expected worldbuilding document identity remains valid,
* active document has not changed,
* command not aborted,
* returned revision is valid successor.

---

### Adopt

Perform metadata-only rebase.

Then:

* Surface Context renders returned title,
* refresh selector registry list,
* Agent context naturally republishes from session record,
* close rename popover.

---

## §11 Save / rename serialization

This must be deterministic.

### Rename while Save is running

Rename action should be unavailable while a conflicting Canvas command is active.

If a retained/stale callback invokes rename anyway:

```text
runDocumentCommand → conflict/no-op
```

No PATCH.

---

### Save while Rename is running

Shared Edit Host Save should be disabled while metadata update is active.

Update Build's Save conflicts accordingly.

Current Build Save conflicts with extraction; extend the conflict set rather than inventing separate booleans when possible.

Programmatic retained Save invocation should likewise fail through command arbitration.

---

### Rename after Save

This is an owning test.

Sequence:

```text
load revision 4
edit
Save
Canvas now revision 5

controller preflight record may still say revision 4

Rename
```

Required request:

```text
expected_revision = 5
```

This explicitly proves rename is using Canvas authority, not controller state.

---

## §12 Navigation and stale completion

### A → rename pending → operator switches to B

Preferred product behavior for this PR:

* disable document selector / New Source / Rename while the metadata command is actively mutating A.

This reduces ambiguity for a very short mutation.

But still prove stale safety at the authority layer.

If A unmounts or document identity changes while a retained/asynchronous rename exists:

* command aborts/invalidates,
* late A response is not adopted into B,
* B title/revision/draft remain untouched,
* no selector rewrite makes A's late response look like B state.

UI disabling is ergonomics.

Command invalidation is the correctness boundary.

---

## §13 Dirty-draft behavior — merge-critical

This is the highest-value dogfood path.

Starting state:

```text
Ironveil Property
revision 10
Saved
```

Operator types:

```text
The western warehouse is empty during festival season.
```

State:

```text
revision 10
Unsaved changes
```

Operator renames source:

```text
Ironveil Property → Ironveil Manufactory Grounds
```

Required immediate state:

```text
title: Ironveil Manufactory Grounds
revision: 11
status: Unsaved changes
editor text: unchanged
```

Then operator Save:

```text
expected_revision = 11
→ content commit
→ revision 12
```

Hard reload exact document URL:

```text
title: Ironveil Manufactory Grounds
content includes the unsaved-before-rename sentence
status: Saved
```

If this sequence does not work, the PR is not complete.

---

## §14 Reload / Discard terminology

Do not broaden this slice simply because the backlog also mentioned “Reload / Discard.”

Current MarkdownCanvas already presents:

```text
Reload from server
Discard local draft
```

where reconciliation requires those recovery actions.

That remains correct.

A future polish slice can decide whether ready-state recovery commands belong in shared Edit Host.

Separately, registry-level:

```text
Discard source
```

means changing the durable document lifecycle status.

Those are materially different operations.

Do not introduce an ambiguous `Discard` button in this PR.

---

## §15 World Graph independence

Rename is workspace-document metadata.

It must not mutate or reinterpret:

```text
campaigns=
session=
graphRevision=
World Graph focus
World Graph selected campaigns
```

The Build reference capability should remain bound to:

```text
same documentId
same document campaign
same graph lens
```

A title/revision metadata update must not cause a cold graph reload merely because the document record object changed.

Do not put `record.revision` or `record.title` into graph projection request identity.

Existing open/inserted graph chips should remain usable after rename.

---

## §16 Agent Interaction behavior

Build currently publishes Agent context from the accepted Markdown Canvas record.

Preserve that authority.

After successful rename, Agent Interaction should naturally republish:

```text
Build · Ironveil Manufactory Grounds
```

with:

```text
same documentId
new revision
same campaign
same content SHA
same dirty state
```

Do not manually publish a rename-specific parallel context.

A failed rename must leave Agent context on the old authoritative title.

---

## §17 Error semantics

### Validation

Blank:

```text
"   "
```

→ no PATCH.

Same normalized title:

```text
" Ironveil Property "
```

when current title is `Ironveil Property`

→ no PATCH.

---

### 409 revision conflict

No automatic reconciliation.

Required outcome:

* retain Canvas,
* retain local draft,
* retain old accepted record locally,
* show error,
* let operator deliberately Reload if appropriate.

Never silently throw away the local draft to “fix” rename.

---

### Network / 5xx

Same local behavior:

* no optimistic authoritative title,
* no local revision change,
* form remains available for retry.

---

### Malformed successful response

If same-document / revision invariants fail:

* treat as failed adoption,
* do not advance local expected revision,
* surface an integrity-style rename error.

Do not “best effort” merge a surprising record.

---

## §18 Owning tests

### E1 — clean rename

Given clean A at revision `N`:

```text
Rename A → New A
```

Assert:

* exactly one PATCH,
* exact `documentId`,
* `title = "New A"`,
* `expected_revision = N`,
* returned revision `N+1` adopted,
* same content SHA,
* `dirty === false`,
* URL unchanged,
* no new history entry.

---

### E2 — dirty rename preserves authoring state

Given A dirty at revision `N`:

* capture local Markdown / TipTap JSON,
* rename,
* assert returned revision `N+1`,
* assert local body unchanged,
* assert `dirty === true`,
* assert base revision rebased to `N+1`,
* assert base content SHA unchanged.

Then Save.

Assert Save uses `N+1` and succeeds.

This is mandatory.

---

### E3 — rename after Save uses Canvas revision

Given:

```text
controller record revision = N
Canvas save advances session to N+1
```

Rename.

Assert PATCH:

```text
expected_revision = N+1
```

not `N`.

This directly owns the controller-vs-Canvas authority boundary.

---

### E4 — title appears everywhere it should

After successful rename:

* DOCUMENT context shows new title,
* selector refresh shows new title,
* Agent surface context uses new title,
* Canvas still has no duplicate ready-state title header.

---

### E5 — failed rename

Mock network/500.

Assert:

* old accepted title remains,
* revision unchanged,
* dirty state/body unchanged,
* candidate input retained,
* error visible,
* no selector optimistic rewrite.

---

### E6 — stale revision

PATCH returns 409.

Assert:

* no local metadata adoption,
* no revision advancement,
* no body loss,
* compact stale-source message,
* no automatic reload.

---

### E7 — Save blocks Rename

Start Save and hold promise.

Attempt Rename.

Assert:

* rename control disabled, and/or
* retained direct invocation results in command conflict,
* zero metadata PATCHes.

---

### E8 — Rename blocks Save

Start rename and hold PATCH.

Attempt retained/shared Save.

Assert:

* no prepare/commit starts while rename is active,
* once rename adopts revision `N+1`, Save may proceed from `N+1`.

---

### E9 — document replacement invalidates rename

A rename starts.

Before completion, replace/unmount A and admit B through a test-level retained path.

Resolve A request.

Assert:

* B unchanged,
* A response not adopted into B session,
* no stale title/revision leaks.

---

### E10 — blank / same title

Assert zero PATCHes for:

* empty,
* whitespace only,
* normalized same title.

---

### E11 — graph capability survives rename

With Build World Graph projection ready:

* rename source,
* verify no extra graph projection request solely due to rename,
* Find Existing still works,
* insert a graph reference,
* reopen chip successfully.

---

### E12 — dirty rename → Save → hard reopen

Integration-level Build page proof:

```text
open A
edit body
rename
save
unmount/re-render exact URL
```

Assert both new title and changed body survive.

---

## §19 Tests that are not sufficient by themselves

Do not accept only:

* a rename-form component test,
* a mocked PATCH API test,
* a server registry test proving title changes,
* a clean-document rename happy path.

Those miss the actual architecture risk.

The merge-critical proof crosses:

```text
metadata PATCH
→ revision rebase
→ existing dirty local draft
→ next Markdown Save CAS
```

---

## §20 Likely implementation shape

### New

```text
Docs/Plans/
  HANDOFF-BUILD-dogfood-polish-build-document-rename.md

apps/live-control-ui/src/buildSurface/
  BuildDocumentRenameControl.tsx
  BuildDocumentRenameControl.test.tsx
```

### Modify

```text
apps/live-control-ui/src/buildSurface/
  BuildSurfaceContext.tsx
  BuildSurfaceContext.test.tsx
  BuildSurfacePage.tsx
  BuildSurfacePage.test.tsx
  BuildSurfaceShell.tsx
  buildDocumentCommands.ts
  useBuildWorkspaceDocumentController.ts
  useBuildWorkspaceDocumentController.test.ts
```

Controller changes should be limited to removing obsolete authoring-state mirroring and supporting selector refresh. It does not become metadata authority.

### Generic Canvas / authoring seam

```text
apps/live-control-ui/src/markdownCanvas/
  markdownCanvasTypes.ts
  MarkdownCanvasSession.tsx
  relevant session tests

apps/live-control-ui/src/workspaceDocument/
  useWorkspaceDocumentAuthoring.ts
  useWorkspaceDocumentAuthoring.test.tsx
```

### API client if needed

```text
apps/live-control-ui/src/api/
  liveApi.ts
  liveApi.test.ts
```

Use the already-landed PATCH endpoint.

### Styling

```text
apps/live-control-ui/src/buildSurface/buildSurface.css
```

Only if required for the compact Surface Context popover.

---

## §21 Production-path stop conditions

STOP and reassess rather than expanding scope if implementation appears to require:

1. changing `SurfaceContextHost` to understand Build documents,
2. changing workspace-document server revision semantics globally,
3. making controller `activeRecord` the Canvas revision authority,
4. remounting MarkdownCanvas after rename,
5. coupling World Graph request identity to document title/revision,
6. adding a new persistence path instead of existing metadata PATCH,
7. exposing `authority_state` promotion because “the form is already here,”
8. rewriting generic Markdown reconciliation to ignore arbitrary revision mismatches.

A **specific metadata-only rebase** is required.

A **general weakening of CAS reconciliation** is not.

---

## §22 Nano-commit suggestion

A useful implementation sequence:

1. `test(canvas): prove metadata revision rebase preserves dirty draft`
2. `feat(canvas): adopt metadata-only workspace record updates`
3. `feat(build): rename active source from DOCUMENT context`
4. `test(build): prove dirty rename save and stale command fencing`

Exact commit count is not important; capability boundaries are.

---

## §23 Verification

At minimum run the owning UI suites covering:

```bash
cd apps/live-control-ui

pnpm exec vitest run \
  src/workspaceDocument/useWorkspaceDocumentAuthoring.test.tsx \
  src/markdownCanvas/ \
  src/buildSurface/ \
  src/App.test.tsx
```

Then:

```bash
pnpm exec tsc -b
pnpm build
```

If implementation changes server code despite the expected no-server-change design, add the relevant workspace registry/API server tests and justify why the existing route was insufficient.

Do not use a green unrelated suite as proof of the metadata→Canvas CAS boundary.

---

## §24 Manual dogfood

Use a real existing Build source.

### Flow A — dirty rename

1. Open Build.
2. Load `Ironveil Property` or another existing source.
3. Type a distinctive unsaved sentence.
4. Confirm `Unsaved changes`.
5. Rename the source from DOCUMENT context.
6. Confirm:

   * new title appears,
   * editor does not flash/remount,
   * unsaved sentence remains,
   * status remains `Unsaved changes`,
   * URL `documentId` is unchanged.
7. Save through the shared Edit Host.
8. Hard reload.
9. Confirm:

   * renamed title persists,
   * edited body persists,
   * status is clean/saved.

This is the primary dogfood scenario.

### Flow B — graph continuity

After rename:

1. Open Find Existing.
2. Search a known graph object.
3. Insert it.
4. Click/reopen its chip.

Confirm graph behavior is unchanged.

### Flow C — failure

1. Make rename PATCH unavailable or force failure.
2. Attempt rename.
3. Confirm:

   * source remains loaded,
   * old title remains authoritative,
   * entered candidate title remains available,
   * Markdown edits remain untouched.
4. Restore server and retry.

### Flow D — source switch

1. Rename A successfully.
2. Switch to B.
3. Confirm:

   * B has its own title,
   * no A rename form/error leaks,
   * shared hosts remain singular.

---

## §25 Explicit non-goals

Do not include:

* document class editing,
* player-safe/internal editing,
* draft/reviewed/canonical authority changes,
* campaign reassignment,
* target path editing,
* source discard/restore,
* promotion to canonical corpus source,
* graph writes,
* graph object creation,
* ingestion redesign,
* Statblock generator integration,
* Plan rename,
* generic document manager,
* title-in-Canvas ready header,
* Surface Context host redesign,
* World Graph reload/performance work.

---

## §26 Merge gate

Merge only if both statements are demonstrably true:

> **Renaming a Build source changes only metadata of the same exact admitted `documentId`: the PATCH is CAS-bound to the MarkdownCanvasSession's current revision, the returned metadata revision is rebased into that same live Canvas without losing or cleaning a dirty draft, and the next Markdown Save continues from the returned revision.**

And:

> **DOCUMENT Surface Context owns rename presentation; MarkdownCanvasSession remains the sole content/revision authority. Rename creates no new document, no URL/history transition, no Canvas remount, no World Graph reload, and no second mirrored authoring state.**

The strongest falsification is:

```text
dirty Canvas at N
→ rename to N+1
→ dirty body survives
→ Save from N+1 succeeds
→ hard reload contains both new title and new body
```

If that sequence fails, STOP.

---

## §27 Successors

After this PR, the Build polish sequence becomes:

1. **Build document lifecycle / recovery actions**

   * decide ready-state Reload / Discard local changes placement in shared Edit Host,
   * separately design durable source discard/restore with explicit destructive semantics.

2. **Build light metadata policy**

   * class / visibility only after operator-facing vocabulary and policy are defined,
   * authority-state elevation remains a governed promotion design.

3. **Shared Threat / Statblock projection parity**

   * Build graph chips should open the same campaign-facing Threat projection as Plan,
   * Workbench remains a separate authoring Tool.

4. **Shared tool inventory parity**

   * publish appropriate shared tools into Build without Plan ownership or surface-specific forks.

Do not pull those into this rename PR.
</user_query>
