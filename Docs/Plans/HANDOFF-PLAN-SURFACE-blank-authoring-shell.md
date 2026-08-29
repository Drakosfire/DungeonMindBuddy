---
pr_body_template: |
  ## Handoff pointer
  - Conversation/workstream: PLAN-SURFACE / BLANK-SHELL
  - Flow: PLAN-SURFACE
  - Direction: DESIGN → CODE → REVIEW
  - Handoff: `Docs/Plans/HANDOFF-PLAN-SURFACE-blank-authoring-shell.md`
  - Branch / PR: `agent/plan-blank-authoring-shell` / `PLAN-SURFACE: make blank authoring a real surface state`

  ## Verification pointer
  - Base/head: record exact SHAs in the PR
  - Changed paths: HANDOFF §8
  - Verification: HANDOFF §10

  The checked-in handoff, cumulative diff, state-machine evidence, zero-material
  browser witness, and independently rerun verification are the review contract.
  This body is transport metadata.
---

# HANDOFF — Plan blank authoring shell

**Created:** 2026-08-28
**Status:** DONE
**Merged:** PR #661
**Accepted head:** `ffa0b18d6212a6780d6be90f91a25626bf15b464`
**Merge:** `770f79cca4aa3c12aa8a35db2db77ce376f2ff9e`
**Review cycles:** 4
**Canonical handoff path:** `Docs/Plans/HANDOFF-PLAN-SURFACE-blank-authoring-shell.md`  
**Workstream:** `PLAN-SURFACE / BLANK-SHELL`  
**Flow / owner:** `PLAN-SURFACE`  
**Handoff direction:** DESIGN → CODE  
**Suggested branch:** `agent/plan-blank-authoring-shell`  
**PR title:** `PLAN-SURFACE: make blank authoring a real surface state`

> **Dispatch base:** `b0603b988c9392f8d8938284650cf9378368d122`
>
> Repository content at this base is equivalent to the preceding CUTOVER merge
> `84f3401b23fcac32a57416d5419dc7d33cf6eabc`; the two immediately following
> commits only create and remove an accidental one-byte probe file. Do not use
> either probe commit as product/design evidence.
>
> Re-fetch `main` and active write leases immediately before implementation.
> If `main` advances, rebase before production work.

Parent authorities:

- `AGENTS.md`
- `Docs/Design/ARCHITECTURE-surface-interaction-layer.md`
- `Docs/Design/ARCHITECTURE-application-state-layer.md`
- `Docs/Design/DESIGN-shared-markdown-canvas-surface-composition.md`
- `Docs/Design/DESIGN-playable-authoring-and-adoption.md`
- `Docs/Roadmaps/ROADMAP-con-ready.md`
- `Docs/Plans/STEWARDS-ANCHOR-con-ready.md`

Relevant product predecessors:

```text
DF0 / PR #657
  DONE — local Play dogfood gateway
  accepted head:
    dc20fe8e63eec691265e75eb73c69f441ffd779d
  merge:
    87a769d05605ff021d28f0b69c5d7ab0b8205440
  review cycles:
    3

BF4A
  DESIGNED / PAUSED
  Native Runbook authoring gateway
  blocked because Plan authoring chrome and Canvas are not valid zero-material
  surface states yet.

BF3B
  DESIGNED / PAUSED ON BF4A
  Decision interaction and visible relevance
```

Active parallel lane at design time:

```text
#659 AGENT-INTERACTION
  AgentRuntime / Hermes backend boundary
  no Plan/SurfaceInteraction frontend write overlap identified at design time
```

---

## §0 Why this PR exists

### 0.1 The discovered flaw is more foundational than BF4A

The current Plan shell treats successful durable document resolution as the
precondition for having a real authoring surface.

Today the effective sequence is approximately:

```text
enter /plan
→ resolve a durable planning document
→ build Plan config/publication
→ publish Canvas work-object identity
→ Canvas publishes editor tools
→ Edit/Tools hosts finally have matching inventory
```

When document resolution is empty or fails, that chain breaks near the top.
The shell publishes no matching surface inventory, and the shared hosts quite
reasonably render nothing when they have no inventory.

That creates the wrong operator model:

```text
no document
→ no authoring surface
→ no Edit host
→ no Tools host
→ controls required to create/recover/edit are hidden by the state that needs them
```

This was exposed by BF4A, but it predates BF4A.

### 0.2 Repository truth

`PlanSurfaceShell` currently publishes no projection surface unless exact
document resolution reaches `ready`:

```text
if documentLoadStatus != ready OR publication absent
  → publishProjectionSurface(null)
```

`EditHost` only renders when commands/panels match the active Canvas work
object. `ToolHost` only renders when tools exist.

Those host rules are not themselves the defect. The defect is that Plan stops
publishing a truthful authoring work target and inventory whenever durable
content is absent.

### 0.3 Product correction

This slice freezes the following rule:

> **Entering an authoring surface yields a ready authoring shell even when no
> durable document exists yet. A local blank draft is a first-class surface
> work target with explicit local identity. Durable document authority begins
> only after explicit promotion through the existing workspace-document create
> boundary. Chrome visibility does not depend on successful durable document
> resolution.**

A blank shell is therefore not:

```text
null document
missing Canvas
fake UUID
empty server WorkObject created on route entry
load failure disguised as empty state
```

It is:

```text
local authoring identity
+ local editable TipTap content
+ normal surface context
+ mounted Edit/Tools inventory
+ explicit promotion boundary on first Save
```

---

## §1 Sequencing decision

This is a **separate predecessor PR**, not a BF4A amendment.

Reason:

- always-valid Plan surface identity is independently useful;
- local→durable promotion is an authoring contract of its own;
- BF4A should remain narrowly about reopening/saving an existing Runbook;
- BF3B remains downstream of BF4A.

Target sequence:

```text
DF0
  DONE

PLAN-BLANK-SHELL
  DONE
  zero-material Plan authoring + local→durable promotion
  accepted head: ffa0b18d6212a6780d6be90f91a25626bf15b464
  merge:         770f79cca4aa3c12aa8a35db2db77ce376f2ff9e
  review cycles: 4

BF4A
  CURRENT
  NEXT
  explicit Runbook → ordinary editor → pathless Runbook Save

BF3B
  AFTER BF4A
  Decision select/change/clear + consequence/relevance
```

Do not fold BF4A Runbook save semantics or BF3B runtime choice semantics into
this slice.

---

## §2 Mission and merge-ready invariant

### 2.1 Mission

> **Make Plan a valid authoring surface before a durable document exists. Bare
> `/plan` with no active Plan documents opens a ready local draft shell with
> normal Edit/Tools chrome. Exact-document load failures remain truthful error
> states but keep the same surface chrome mounted. The first Save of the local
> blank explicitly creates a real Plan WorkObject through the existing create
> API, preserves the current editor content, promotes surface identity to the
> returned exact `documentId`, updates the URL, and continues under ordinary
> workspace-document authority without silently fabricating or masking state.**

### 2.2 Merge-ready invariant

> **At every mounted Plan surface state after `PlanView` itself is available,
> Plan publishes exactly one current surface identity and one current Canvas
> work target. When no durable document is admitted, that target is explicitly
> local and can never be mistaken for a server `documentId`. Edit and Tool
> inventory remain mounted and target that exact work object; commands may be
> disabled with specific reasons, but the hosts do not disappear merely
> because document resolution is empty, loading, or failed. A legitimate empty
> first-use state owns editable local TipTap content. A load error owns an error
> Canvas and never silently becomes a blank draft. First Save of a local blank
> uses the existing Plan create contract once, adopts the exact returned
> WorkObject identity, preserves the local editor bytes across promotion, and
> then uses existing workspace-document write authority. No automatic server
> document is created merely by visiting `/plan`.**

### 2.3 What becomes true

```text
bare /plan + no active Plans
→ Plan shell READY
→ local blank draft Canvas visible
→ Edit host visible
→ Tools host visible
→ Unlock editing visible
→ edit locally
→ first Save
→ one existing Plan create intent
→ exact durable Plan identity admitted
→ URL names exact documentId
→ editor content preserved
→ ordinary subsequent Save behavior
```

Also:

```text
/plan?documentId=<exact id>
→ chrome mounts before/through resolution
→ successful exact admission keeps chrome
→ selector membership is irrelevant to exact-ID admission
```

And:

```text
exact document load error
→ truthful error Canvas
→ chrome still mounted
→ commands disabled/recovery-capable with specific reasons
→ no blank draft silently substituted
```

### 2.4 What remains false

```text
auto-create a server Plan on route entry
fake durable document UUID
Runbook pathless-save rule (BF4A)
Runbook selector redesign
BF3B Decision interaction
new backend endpoint
new persistence table
new document schema
new generic authoring router
load-error fallback to blank content
```

---

## §3 Blank-shell state machine

The implementation must model the Plan authoring state explicitly rather than
continue overloading `planningDocument == null`.

A representative state machine is:

```ts
type PlanAuthoringShellState =
  | { kind: "resolving"; shell: PlanShellIdentity; requestedDocumentId: string | null }
  | { kind: "blank_ready"; draft: PlanLocalDraft }
  | { kind: "promoting"; draft: PlanLocalDraft; retainedCreateId: string | null }
  | { kind: "durable_ready"; document: PlanDocumentDescriptor }
  | { kind: "load_error"; shell: PlanShellIdentity; requestedDocumentId: string | null; message: string };
```

Exact naming is not frozen. Semantics are.

### 3.1 `resolving`

Used while an exact durable document or default Plan selection is being
resolved.

Required:

```text
surface identity exists
Canvas work target exists
Edit/Tools hosts remain present
Canvas body may say Loading…
commands requiring an admitted editor/document are disabled with reason
```

Do not temporarily publish `null` and resurrect the surface later.

### 3.2 `blank_ready`

This is the legitimate first-use state.

Entered only when:

```text
no explicit documentId requested
AND
active Plan listing resolves successfully
AND
there are zero admissible active Plan documents
```

It owns real local editable content.

It is not entered for network/API/integrity failure.

### 3.3 `promoting`

Entered only after explicit Save on `blank_ready`.

It owns one retained create intent.

Required:

```text
no second create while first intent is retained
editor remains mounted/readable
commands that would race promotion are disabled
status explains Creating Plan… / Saving…
```

### 3.4 `durable_ready`

Existing ordinary exact WorkspaceDocument authoring state.

After promotion this state uses the exact server `documentId` returned by the
create contract.

### 3.5 `load_error`

Used when a requested/default durable document could not be resolved for an
actual error.

Required:

```text
error stays visible
surface identity stays present
Tools stay present
Edit host stays present
Unlock editing remains discoverable as an Edit capability
commands needing document/editor authority are disabled with truthful reasons
existing selector/create/retry recovery affordances remain available
```

Do not make the error disappear behind a fresh blank Plan.

---

## §4 Identity contract

### 4.1 Durable identity remains unchanged

A persisted Plan uses:

```text
WorkspaceDocumentRecord.document_id
```

as its durable WorkObject identity.

Nothing in this slice changes that.

### 4.2 Local blank identity is explicitly non-durable

A local blank draft uses a separate surface work-object identity, for example:

```ts
{
  kind: "plan-local-draft",
  id: "local-plan:<opaque-local-id>"
}
```

Requirements:

- the ID is never passed to workspace-document GET/prepare/commit as a
  `documentId`;
- the ID is never published to Agent context as a durable `documentId`;
- it is valid only as local Canvas/Edit command targeting identity;
- it remains stable for the lifetime of the local draft;
- promotion replaces it with the exact returned server document identity.

### 4.3 Local draft identity persistence

Use one retained local draft identity per campaign while that draft is
unpromoted.

Preferred implementation:

```text
campaign-scoped local pointer
→ opaque local draft id
→ local TipTap state stored under that local id
```

A page reload before first Save should recover that same local draft when
possible rather than silently minting a new local identity and losing edits.

This may reuse existing localStorage/local TipTap state primitives. It must not
require APP-STATE or a new backend table.

On successful durable promotion:

```text
clear local blank pointer
clear/migrate local-id draft state
retain durable-id local working state as appropriate
```

No orphan local draft should remain selected after promotion.

### 4.4 Surface identity and Agent context must remain distinct

The current legacy projection adapter derives both Canvas work identity and
Agent `documentId` from `config.canvas.documentId`. That is too coupled for a
local blank.

This PR is authorized to add the smallest compatibility seam necessary to
express:

```text
Canvas work target:
  { kind: "plan-local-draft", id: <local id> }

Agent context documentId:
  null
```

while preserving existing persisted-document behavior:

```text
Canvas work target:
  { kind: "document", id: <server UUID> }

Agent context documentId:
  <server UUID>
```

Preferred shape is an optional explicit Canvas work-object identity on the
legacy Surface config/publication, with current `documentId` fallback retained
for all existing callers.

Do not encode the local ID into the durable `documentId` field merely because
that is convenient.

---

## §5 Local blank metadata and starter content

A blank Plan needs enough truthful metadata to render and eventually create a
real Plan, without pretending server-owned values already exist.

### 5.1 Metadata

Local blank metadata is:

```text
kind:
  plan

campaignId:
  exact planView.campaign_id

targetSession:
  existing suggestNextPlanTargetSession(...) result once selector state is known

title:
  existing defaultSessionPrepTitle(...) suggestion for that target session

targetRelpath:
  null / unknown locally

durable documentId:
  null

content status:
  local draft, not server "draft" authority
```

Do not fabricate a path.

### 5.2 Starter body

Reuse the existing Plan starter semantics rather than inventing a second
first-document template.

The blank Canvas should start from the same conceptual content produced by:

```text
createStarterContentForPlanDocument(...)
```

adapted to local metadata.

This gives the operator a recognizable editable prep scaffold rather than a
completely empty white box.

### 5.3 Selector-list failure

If active Plan listing itself is unavailable, Plan may still render a local
shell and editable Canvas, but first Save must not guess a target session that
could conflict with unseen durable Plans.

Required:

```text
editor/chrome visible
Save/Create disabled
reason: active Plan inventory is unavailable; target session cannot be chosen safely
Retry list remains available
```

Once selector state becomes trustworthy, normal target-session suggestion may
enable first Save.

Do not treat list failure as `zero Plans`.

---

## §6 First-Save promotion contract

### 6.1 Creation boundary

First Save from `blank_ready` uses the **existing** workspace-document create
contract.

Use the existing kind-aware create intent:

```ts
{
  kind: "plan",
  campaignId,
  title,
  targetSession,
}
```

The server remains owner of Plan durable path derivation.

No new creation endpoint is authorized.

### 6.2 Promotion sequence

The conceptual sequence is:

```text
local blank draft
→ user presses Save
→ serialize current TipTap state safely
→ create Plan WorkObject once
→ receive exact WorkspaceDocumentRecord
→ verify kind/campaign/status/target path are admissible
→ bind/migrate current local draft to exact returned documentId
→ replace browser URL with exact ?documentId=<uuid>
→ continue/save current bytes through existing workspace-document prepare/commit authority
→ verify committed snapshot
→ durable_ready
```

The implementation may order snapshot-admission and URL replacement slightly
differently for safety, but these laws are mandatory:

1. **one create intent**;
2. no editor-content loss;
3. exact returned identity becomes authority as soon as creation is known to
   have succeeded;
4. retries never mint replacement WorkObjects after create success;
5. ordinary prepare/commit remains body-write authority;
6. URL eventually names the exact durable `documentId`;
7. no fake path or identity is invented.

### 6.3 Create success + later save failure

This is a first-class state and must be handled explicitly.

If create succeeds but prepare/commit fails:

```text
server WorkObject exists
→ UI must not pretend it is still purely local
→ exact durable identity is retained
→ current editor content remains recoverable as dirty local state for that exact document
→ retry Save writes the same WorkObject
→ no second POST create
```

This is the critical lost-boundary case.

A retry-safe create controller already exists. Reuse it.

### 6.4 Create failure

If create fails before any WorkObject exists:

```text
remain blank_ready
retain same local draft identity
retain exact editor content
show create/save error
retry may issue a new create intent
```

### 6.5 Durable-path gate

Plan's existing durable-path rule remains real.

After create returns:

```text
valid Plan target_relpath
→ body commit may proceed

null / TBD / invalid Plan target path
→ fail closed before body commit
→ retain created exact WorkObject + local dirty content
→ show specific reason
```

Do not weaken Plan's path rule globally.

BF4A separately owns the rule that a `kind=runbook` may be pathless.

### 6.6 URL semantics

Promotion should use `replaceState`, not create a fake navigable history entry
for the no-longer-existing local identity.

Required:

```text
/plan
(local blank)

first Save creates D
→ replace current URL with /plan?documentId=D
```

Browser Back should not navigate to an obsolete pseudo-document URL.

---

## §7 Chrome contract

### 7.1 Chrome inventory belongs to the surface, not document resolution

Once PlanView is available, Plan owns its authoring chrome continuously.

The Plan shell must publish surface inventory in:

```text
resolving
blank_ready
promoting
durable_ready
load_error
```

Do not publish `null` merely because durable document admission is not READY.

### 7.2 Edit host

The Edit host must always have matching inventory for the current Plan Canvas
work target.

At minimum, every Plan authoring shell state exposes:

```text
Unlock editing / Lock editing
```

When editing actions cannot run, they remain visible but disabled.

Examples:

```text
Insert block
  disabled: Document is still loading.

Save
  disabled: No durable target session is available yet.

Save
  disabled: Document failed to load; retry or choose another document.
```

### 7.3 Truthful disabled reasons

The current legacy AppChrome compatibility path collapses disabled state to a
generic reason. This slice is authorized to thread an optional
`disabledReason` through:

```text
MarkdownEditorToolAction
→ AppChromeAction
→ SurfaceInteractionAvailability
→ EditHost title/accessible reason
```

Existing callers without a reason retain current behavior.

Do not invent per-host bespoke error strings when the owning surface can
provide the reason.

### 7.4 Tool host

Plan's ordinary Tool inventory remains visible in blank/error states.

Tools whose required World/context data is available may remain enabled.
Tools requiring an admitted durable document must be disabled with a reason.

Do not remove the entire Tool host because document resolution failed.

### 7.5 Agent bar

The Agent bar may remain visible, but it must never be the only remaining
surface chrome in a zero-material or error Plan state.

For a local blank:

```text
campaign context:
  valid

documentId:
  null

local Canvas work-object identity:
  not represented as durable Agent documentId
```

---

## §8 Write lease

### 8.1 Handoff

| Action | Path |
|---|---|
| Create | `Docs/Plans/HANDOFF-PLAN-SURFACE-blank-authoring-shell.md` |

### 8.2 Plan shell / state

| Action | Path | Purpose |
|---|---|---|
| Modify | `apps/live-control-ui/src/planSurface/PlanSurfaceShell.tsx` | explicit shell state machine; never-null Plan surface after PlanView |
| Modify | `apps/live-control-ui/src/planSurface/PlanSurfaceShell.test.tsx` | zero-material/error/exact-ID acceptance |
| Create | `apps/live-control-ui/src/planSurface/planBlankAuthoringState.ts` | pure local identity/state/promotion helpers |
| Create | `apps/live-control-ui/src/planSurface/planBlankAuthoringState.test.ts` | pure state-machine/retry/promotion evidence |
| Modify | `apps/live-control-ui/src/planSurface/types.ts` | local-vs-durable authoring descriptor types if needed |
| Modify | `apps/live-control-ui/src/planSurface/config/planSurfaceConfig.ts` | blank-shell config/publication support |
| Modify if needed | `apps/live-control-ui/src/planSurface/config/planSessionDescriptor.ts` | reuse starter/session metadata for local Plan draft |

### 8.3 Canvas / local promotion

| Action | Path | Purpose |
|---|---|---|
| Modify | `apps/live-control-ui/src/planSurface/components/PlanSurfaceCanvas.tsx` | local blank editor + truthful toolbar availability/promotion entry |
| Create if needed | `apps/live-control-ui/src/planSurface/components/PlanBlankCanvas.tsx` | bounded local draft Canvas if separating persisted/local modes is cleaner |
| Create if needed | `apps/live-control-ui/src/planSurface/usePlanBlankAuthoring.ts` | bounded local-state + first-save promotion orchestration |

Use at most one of the two optional production files above unless review
evidence proves both are necessary.

### 8.4 Existing create/local-draft machinery

| Action | Path | Purpose |
|---|---|---|
| Modify if required | `apps/live-control-ui/src/workspaceDocument/workspaceDocumentCreation.ts` | only if a missing retained-create/promote helper is proven; do not change API semantics |
| Modify if required | `apps/live-control-ui/src/tiptap/state/tiptapLocalState.ts` | only for safe local-id→durable-id state migration/recovery helper |

Do not rewrite the general persisted-document authoring hook unless the Plan
promotion cannot be implemented without duplicating prepare/commit correctness.
If `useWorkspaceDocumentAuthoring.ts` must change, STOP first and record the
exact missing seam; reviewer must approve the lease widening before code lands.

### 8.5 Surface Interaction compatibility seam

This slice may make the minimal backward-compatible change needed to separate
local Canvas identity from durable document identity:

| Action | Path |
|---|---|
| Modify | `apps/live-control-ui/src/agentInteraction/surfaceInteractionCompat.ts` |
| Modify | `apps/live-control-ui/src/agentInteraction/surfaceInteractionCompat.test.ts` |
| Modify | `apps/live-control-ui/src/agentInteraction/projectionSurfacePublication.ts` |
| Modify if required | `apps/live-control-ui/src/planSurface/types.ts` |

Required compatibility:

```text
existing config.canvas.documentId-only callers
→ unchanged Canvas work object + Agent documentId

blank Plan explicit local workObject + documentId=null
→ local Canvas target
→ Agent documentId null
```

### 8.6 Truthful disabled-reason plumbing

| Action | Path |
|---|---|
| Modify | `apps/live-control-ui/src/chrome/AppChrome.tsx` |
| Modify | `apps/live-control-ui/src/tiptap/MarkdownEditorToolbar.tsx` |
| Modify | `apps/live-control-ui/src/agentInteraction/surfaceInteractionCompat.ts` |
| Modify tests owning those adapters | existing colocated test files only |

This lease is limited to optional disabled-reason propagation. Do not redesign
AppChrome or EditHost layout.

### 8.7 Host regressions

The host implementation itself should not need behavior changes if Plan keeps
truthful inventory present.

Do **not** modify by default:

```text
apps/live-control-ui/src/surfaceInteraction/editHost/EditHost.tsx
apps/live-control-ui/src/surfaceInteraction/toolHost/ToolHost.tsx
```

If implementation cannot satisfy this handoff without changing host
empty-inventory semantics globally, STOP and report why. That would be a wider
Surface Interaction contract change.

### 8.8 State-authority sync

The implementation PR carries the backward-looking DF0/current sequencing
update:

| Action | Path |
|---|---|
| Modify | `Docs/Plans/HANDOFF-PLAY-SURFACE-local-dogfood-bootstrap.md` |
| Modify | `Docs/Roadmaps/ROADMAP-con-ready.md` |
| Modify | `Docs/Sources/design-agent/ACTIVE_AUTHORITY/ROADMAP-con-ready.md` |
| Modify | `Docs/Plans/STEWARDS-ANCHOR-con-ready.md` |
| Modify | `Docs/Sources/design-agent/ACTIVE_AUTHORITY/STEWARDS-ANCHOR-con-ready.md` |

Target sequence:

```text
DF0
  DONE

PLAN-BLANK-SHELL
  DONE
  accepted head: ffa0b18d6212a6780d6be90f91a25626bf15b464
  merge:         770f79cca4aa3c12aa8a35db2db77ce376f2ff9e
  review cycles: 4

BF4A
  CURRENT

BF3B
  BLOCKED ON BF4A
```

This slice is merged. Successor BF4A is current.

### 8.9 Explicitly unleased

Do not modify:

```text
backend workspace-document route/schema
APP-STATE migrations
WorkObject / WorkRevision schema
BF1 Playable grammar
Play Run schema/progress
BF3B cockpit files
Combat
World Graph/CUTOVER
AgentRuntime/Hermes backend lane
Plan selector default kind=plan policy
Runbook pathless Save semantics (BF4A)
```

---

## §9 Pure state/promotion contract

The local shell logic must be testable without rendering the entire app.

At minimum expose pure helpers equivalent to:

```ts
createPlanLocalDraftIdentity(...)
createPlanLocalDraftMetadata(...)
nextPlanShellState(...)
planShellWorkObject(...)
planShellAgentDocumentId(...)
```

and, if promotion state is represented separately:

```ts
retainCreatedPlan(...)
adoptCreatedPlanIdentity(...)
```

Important invariants:

```text
local work object ID != durable documentId namespace

blank state never follows a load error

create success is sticky
  → retry cannot mint a replacement WorkObject

promotion target always equals exact server-returned document_id

Agent documentId is null until durable identity is admitted
```

---

## §10 Required automated evidence

### 10.1 State machine

Run the new pure state tests.

Must prove:

1. no explicit document + successful zero-record listing → `blank_ready`;
2. no explicit document + listing error → not `blank_ready`;
3. explicit document → resolving exact identity;
4. exact load error → `load_error`, never blank;
5. local blank identity remains stable across ordinary re-render/retry;
6. create success retains exact server document identity;
7. retry after create success cannot create again;
8. Agent `documentId` is null for local blank;
9. durable ready Agent `documentId` is exact server UUID.

### 10.2 Plan shell rendering

Run:

```bash
pnpm --dir apps/live-control-ui exec vitest run \
  src/planSurface/PlanSurfaceShell.test.tsx
```

Required cases:

#### Bare `/plan`, zero Plans

```text
Plan starter Canvas visible
Edit host visible
Tools host visible
Unlock editing visible
Save command visible
agent bar not sole chrome
no create API call merely from mounting
```

#### Bare `/plan`, selector/list unavailable

```text
shell/chrome visible
error/list warning visible
editor may remain local
Save/Create disabled with specific reason
no assumption that zero Plans exist
```

#### Exact persisted Plan

```text
chrome visible during resolution
exact Plan admitted
normal persisted editor behavior unchanged
```

#### Exact Runbook UUID not present in Plan selector

```text
exact document still admits by ID
chrome remains visible
selector's kind=plan inventory does not control exact-ID admission
Runbook save eligibility remains whatever pre-BF4A law currently says
```

#### Exact document load error

```text
error Canvas visible
Edit host visible
Tools host visible
Unlock editing visible
save/insert actions disabled with truthful reason
blank starter content not silently substituted
```

### 10.3 Surface Interaction compatibility

Prove:

```text
persisted document config
→ same neutral Canvas workObject as before
→ same Agent documentId as before

local blank config
→ Canvas workObject kind plan-local-draft
→ local id exact
→ Agent documentId null
→ tools remain present
```

Existing Build/Ingest/Play compatibility tests remain green.

### 10.4 Disabled reason propagation

Prove at least one Plan blank/error command arrives at `EditHost` as:

```text
availability.status = disabled
availability.disabledReason = exact owning reason
```

Existing callers that only set `disabled: true` retain the legacy generic
fallback reason.

### 10.5 First-Save promotion

Automated integration must prove:

```text
blank local id L
editor content M

Save
→ exactly one create Plan request
→ response document D
→ no content loss
→ durable identity becomes D
→ URL uses ?documentId=D
→ body write targets D, never L
→ retry after post-create failure targets D and does not create D2
```

At minimum test these failure boundaries:

1. create fails → remain local L with M;
2. create succeeds, snapshot/admission fails → retain D and M, no second create;
3. create succeeds, prepare fails → retain D and M, no second create;
4. commit succeeds but verification fails → D remains authority, content/recovery state truthful;
5. complete success → durable ready D.

### 10.6 Existing persisted Plan regressions

Prove ordinary existing Plan:

```text
open
edit
save
conflict/reload/discard
```

still uses existing behavior.

This slice must not regress current local-draft conflict protection for durable
documents.

### 10.7 Build

```bash
pnpm --dir apps/live-control-ui run build
git diff --check
```

### 10.8 Mirrors

```bash
cmp Docs/Roadmaps/ROADMAP-con-ready.md \
    Docs/Sources/design-agent/ACTIVE_AUTHORITY/ROADMAP-con-ready.md

cmp Docs/Plans/STEWARDS-ANCHOR-con-ready.md \
    Docs/Sources/design-agent/ACTIVE_AUTHORITY/STEWARDS-ANCHOR-con-ready.md
```

---

## §11 Mandatory real browser witness

This PR exists because the zero-material browser path has repeatedly exposed
false assumptions that tests built around preloaded material do not catch.

A real browser witness is mandatory.

### 11.1 Zero-material first use

Use a campaign with no active Plan documents, or a disposable application-state
DB where that condition is truthful.

Required:

```text
1. Navigate to bare /plan.
2. Do not provide documentId.
3. Confirm no durable Plan was auto-created merely by opening the route.
4. Confirm Plan Canvas is visible with starter content.
5. Confirm Tool chrome is visible.
6. Confirm Edit chrome is visible.
7. Confirm Unlock editing is visible.
8. Unlock editing.
9. Change starter prose.
10. Confirm Save is available only once create metadata is trustworthy.
11. Save.
12. Confirm exactly one durable Plan WorkObject is created.
13. Confirm browser URL becomes /plan?documentId=<exact returned UUID>.
14. Confirm typed content is still present after promotion.
15. Reload.
16. Confirm exact durable document and saved content return.
```

### 11.2 Load-error distinction

Exercise a real failing/nonexistent exact document URL:

```text
/plan?documentId=<missing UUID>
```

Required:

```text
error is visible
blank starter content is NOT substituted
Edit chrome remains visible
Tools chrome remains visible
agent bar is not the only chrome
commands explain why unavailable
normal recovery/navigation remains possible
```

### 11.3 Exact Runbook reachability precursor

Before BF4A resumes, verify this predecessor does not re-break its prerequisite:

```text
/plan?documentId=<existing Runbook UUID>
→ exact document resolves despite Plan selector being kind=plan only
→ authoring chrome remains mounted
```

Do not add BF4A's pathless Runbook Save change here.

---

## §12 Acceptance matrix

| Entry state | Canvas body | Surface work target | Agent documentId | Edit host | Tool host | Save |
|---|---|---|---|---|---|---|
| bare `/plan`, zero Plans | local starter draft | `plan-local-draft:<id>` | `null` | visible | visible | enabled only when create metadata safe |
| bare `/plan`, list error | local/error-aware shell | local shell/draft identity | `null` | visible | visible | disabled with reason |
| exact persisted Plan loading | loading body | stable shell target | requested durable ID only after admission | visible | visible | disabled while loading |
| exact persisted Plan ready | normal editor | `document:<uuid>` | exact UUID | visible | visible | existing Plan law |
| exact Runbook ready | normal editor | `document:<uuid>` | exact UUID | visible | visible | pre-BF4A law |
| exact load error | error body | stable error-shell target | `null` unless exact durable admission succeeded | visible | visible | disabled with reason |
| local promotion in flight | current local editor | retained local/promoting target | `null` until durable create known | visible | visible | busy/disabled |
| create succeeded, save pending | same editor content | `document:<returned uuid>` | exact returned UUID | visible | visible | retry same document only |
| promotion complete | normal durable editor | `document:<uuid>` | exact UUID | visible | visible | ordinary Plan law |

The implementation may use slightly different internal names, but it must
satisfy every row semantically.

---

## §13 State-authority sync

The implementation PR should update CON-READY truth approximately to:

```text
DF0
  DONE — local Play can reach a real blank Runbook and Current Moment

PLAN-BLANK-SHELL
  DONE — Plan zero-material authoring + chrome continuity + first-save promotion
  accepted head ffa0b18d6212a6780d6be90f91a25626bf15b464
  merge 770f79cca4aa3c12aa8a35db2db77ce376f2ff9e
  review cycles: 4

BF4A
  CURRENT — reopen/save native Runbooks

BF3B
  BLOCKED ON BF4A — Decision interaction and visible relevance
```

CR-U11 / authoring readiness should distinguish:

```text
Durable content substrate exists.
Plan currently lacks a valid local blank authoring state.
PLAN-BLANK-SHELL owns that missing zero-material/promotion seam.
BF4A then owns native Runbook reopen/save.
```

Do not claim structure-aware Playable authoring is complete.

---

## §14 Stop conditions

Stop and report before widening if implementation requires:

- changing backend WorkspaceDocument creation semantics;
- a new create endpoint;
- a new persistence table for local drafts;
- treating a local draft ID as a durable document UUID;
- sending local draft ID as Agent `documentId`;
- silently auto-creating server documents on route entry;
- converting load errors into blank drafts;
- making the Plan selector list Runbooks;
- implementing BF4A pathless Runbook Save;
- implementing BF3B Decision controls;
- changing EditHost/ToolHost global empty-inventory semantics;
- rewriting `useWorkspaceDocumentAuthoring` into a generalized unbound-document engine without explicit review approval;
- touching AgentRuntime/Hermes backend work;
- changing World Graph/CUTOVER ownership.

Report:

```text
Stop condition:
Observed zero-material path:
Owning invariant:
Missing seam:
Why this slice cannot absorb it safely:
Exact files/contracts affected:
Proposed split or amendment:
Evidence required:
```

Do not widen silently.

---

## §15 Named successors

### BF4A — Native Runbook authoring gateway

After this slice merges:

```text
Play Create/select Runbook
→ Edit Runbook
→ exact Runbook opens in now-valid Plan authoring shell
→ BF4A permits pathless kind=runbook Save
→ new immutable WorkRevision
```

BF4A should rebase onto the merge and remove any assumptions that Plan chrome
requires an already-resolved durable document.

### BF3B — Decision interaction and visible relevance

After BF4A:

```text
Create blank Runbook
→ Edit/save Decision-bearing revision
→ Start exact Run
→ Decision visible
→ select/change/clear
→ consequence + relevance
→ reload
```

---

## §16 Core design principle

The acceptance boundary for an authoring surface is no longer:

```text
"Does it work when a valid document is already loaded?"
```

It is:

```text
"What does the operator see the first time they enter with nothing loaded,
what can they do from there, and how does local intent become durable authority
without hidden IDs or lost state?"
```

That is the behavior this PR must make true.
