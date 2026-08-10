---
pr_body_template: |
  ## Handoff pointer
  - Conversation: Plan multi-prep workspace drafts
  - Flow / agent: BUILD
  - Direction: DESIGN → CODE
  - Handoff: Docs/Plans/HANDOFF-BUILD-dogfood-polish-plan-session-affinity-workspace-drafts.md
  - PR / branch: agent/dogfood-polish-plan-session-affinity-workspace-drafts

  ## Verification pointer
  - Base: b8e4dd214b1171793051ce507c0b93c6d87efa91 (PR #543 merge)
  - Verification: focused client + registry + TipTap write tests listed in §7

  The checked-in handoff, cumulative code diff, nano commits, and independently
  rerun verification are the review contract. The PR description is transport
  metadata only. Document sync is a separate operation.
---

# HANDOFF — DOGFOOD-POLISH: decouple Plan session affinity from draft storage

**Created:** 2026-08-10.
**Status:** ACTIVE — dispatch exactly one implementation capability.
**Canonical handoff path:** `Docs/Plans/HANDOFF-BUILD-dogfood-polish-plan-session-affinity-workspace-drafts.md`
**Conversation name:** `Plan multi-prep workspace drafts`
**Flow / agent:** `BUILD`
**Handoff direction:** `DESIGN → CODE`
**Design authority:** Shape B decision in this conversation (2026-08-10) + design brief `Docs/Plans/HANDOFF-BUILD-plan-multi-prep-per-session-design.md`
**Code agent:** TBD
**PR title:** `DOGFOOD-POLISH: decouple Plan session affinity from draft storage`
**Suggested branch:** `agent/dogfood-polish-plan-session-affinity-workspace-drafts`
**Base revision:** `b8e4dd214b1171793051ce507c0b93c6d87efa91` (PR #543 merge on `main`)

> **Dispatch gate:** Dispatch is prohibited until capability decomposition is complete, one independently useful mission remains, the merge-ready invariant and required evidence survive critique, every expected path is known, required contract matrices are resolved, and every acceptance claim has an owning proof.
>
> This checked-in handoff is the complete authority. The worker must not compress, omit, replace, or rewrite it before implementation. The PR description is only a transport pointer; it cannot substitute for the handoff, code diff, nano-commit story, or verification evidence.

## Shared vocabulary

| Term | Definition |
|---|---|
| **Session affinity** | `target_session` — planning metadata naming which table session a Plan prep is aimed at. Not storage authority. |
| **Workspace draft path** | Server-owned `out/workspace/plan/<documentId>.md` for normal Create New Prep. |
| **Canonical Session Prep path** | Corpus `…/Session Prep/Session N Prep.md` owned by at most one registry record (active or discarded). |
| **Promotion** | Future content-aware transition from workspace draft → canonical Session Prep. Explicitly deferred. |
| **Capability / Invariant / Evidence ledger / Stop condition** | As in the external-agent HANDOFF template. |

## Agent flow and nano-commit contract

Use flow `BUILD`. Keep nano commits: each commit one discrete fix or proof story.

Recommended commit sequence:

1. Server: Plan workspace path generation on create when `target_relpath` omitted
2. Server: authorize UUID-bound Plan workspace writes; preserve canonical Session Prep allowlist
3. Server: seal Plan metadata PATCH against `target_relpath` transitions
4. Client: Plan create intent omits path; prep-frontier suggestion
5. Client: Create New Prep UX (For session, same-session helper, distinct-title gate)
6. Proofs: same-session alternatives, save isolation, PATCH-not-promote, path authority
7. Bookkeeping only if operator requests in this PR (prefer post-merge doc-sync)

## Review and doc-sync contract

Review against this handoff + cumulative diff + nano commits. Plan/checklist/Backlog updates are a separate document-sync after merge unless the operator explicitly includes bookkeeping in-scope.

---

## §1 Mission and merge-ready invariant

```text
A GM can create multiple active Plan prep documents aimed at the same session
(and ahead of the live cursor) as independently writable workspace drafts so
that contingent / ahead-of-time prep no longer fights canonical Session Prep
path ownership.
```

**Merge-ready invariant:**

> A Plan workspace document's session affinity never determines its identity or unique storage target. Normal Create New Prep always receives a server-owned UUID workspace target (`out/workspace/plan/<documentId>.md`). Canonical Session Prep ownership remains separate, unique (including discarded owners), and is not claimable via Create New Prep or ordinary metadata PATCH.

### Pre-dispatch critique

| Question | Answer |
|---|---|
| Can one invariant govern every claimed observable path? | Yes — affinity ≠ storage; create always gets own workspace path; uniqueness still one-owner-per-non-null-path; PATCH cannot promote. |
| What adversarial sequence is most likely to falsify it? | Create A for Session 27 → Create B for Session 27 with distinct title → PATCH B's `target_relpath` to A's canonical or workspace path / or attempt write to A's workspace path. |
| Would the proposed §7 evidence actually detect that failure? | Yes — registry create/PATCH proofs + TipTap authorize identity-bound path + Plan shell same-session create/select/save tests. |
| Which owning boundary is easiest to under-test? | Writer `authorize_target_for_record(plan)` allowing any UUID-shaped workspace path instead of exact own `document_id`. |
| What fact would force this slice to stop or split? | Discovering Save still requires corpus Session Prep path; or hydration of absent workspace file fails for `kind=plan`; or Create New Prep still derives client-side canonical path. |

Do not dispatch until the invariant and evidence plan survive this critique. **Critique survives.**

---

## §2 Context, authority, and boundaries

| Field | Required content |
|---|---|
| Parent authority | Shape B decision (this design): draft path until promote; every new Plan doc gets server-owned UUID workspace path immediately. Design brief: `Docs/Plans/HANDOFF-BUILD-plan-multi-prep-per-session-design.md`. |
| Repository rules | `#543` path uniqueness (`_require_unique_target_relpath`); `#541` exact `documentId` selection; `#543` create lifecycle (intent epoch / supersession); no silent registry surgery. |
| Base revision | `b8e4dd214b1171793051ce507c0b93c6d87efa91` |
| Predecessor contract | PR #543 generalized intentional workspace-document create + path uniqueness + create supersession |
| Exact input consumed | Plan Create New Prep (title + session affinity only); registry create with `kind=plan` and omitted `target_relpath` |
| Named successor | Promote workspace Plan draft → canonical Session Prep (content-aware); surface context bar; Ask continuity; EditHost dock-default-open |
| What remains false | Promotion UI/API; branch compare/merge; canonical/alternate badges; auto-discard alternatives; Build/runbook multi-doc redesign |
| Explicit non-goals | Shape A corpus branch filenames; pathless (`target_relpath: null`) Plan create as product flow; title uniqueness as server invariant; document manager; AppChrome surface-context-bar move; Ask continuity |

Read authoritative inputs in order before changing code:

1. This handoff (§1–§9) and Shape B product contract below
2. `Docs/Design/DECISION-workspace-document-target-relpath-duplicate-repair.md`
3. PR #543 merge behavior: create controller + `_require_unique_target_relpath`
4. Seams: `workspace_document_registry.py` create/PATCH; `tiptap_markdown_write.py` `authorize_target_for_record`; `workspaceDocumentCreation.ts`; `planSessionDescriptor.ts`; `PlanDocumentCreateControl.tsx`; `PlanSurfaceShell.tsx`
5. Existing owning tests listed in §4

If the base moved, an authority conflicts, or Save/hydration cannot accept workspace Plan paths without a second persistence model, **stop and report**.

### Product model (authoritative)

```text
documentId
    = document identity

target_session
    = planning/session affinity

out/workspace/plan/<documentId>.md
    = normal writable draft storage

corpus/.../Session Prep/Session N Prep.md
    = optional canonical corpus claim (not inferred at Create)
```

Many Plan documents may share `target_session = 27` while each owns a different durable workspace path. Only one registry record may own a given non-null `target_relpath` (active or discarded).

### Field-level create contract

**Client Plan intent (product):**

```ts
{
  kind: "plan";
  campaignId: string;
  title: string;
  targetSession: number; // required for Create New Prep
}
```

Map to API by **omitting** `target_relpath`. Do not derive storage from session on the client.

**Server:** when `kind=plan` and `target_relpath` omitted/null, set:

```text
out/workspace/plan/<document_id>.md
```

via `_plan_workspace_target_relpath(document_id)`.

Low-level API may still accept an explicit Plan `target_relpath` for fixtures/migration/compat; when supplied it must pass allowlist policy + `_require_unique_target_relpath`. Create New Prep must never supply it.

Runbook remains caller-path-oriented. Worldbuilding remains server-path-oriented.

### Path policy

| Document state | Path owner | Example | Corpus? | Multiple for same `target_session`? |
|---|---|---|---|---|
| New Plan workspace prep | Server | `out/workspace/plan/<uuid>.md` | No | Yes |
| Historical/canonical Plan prep | Existing record | `corpus/.../Session N Prep.md` | Yes | One per exact path |
| Future promoted Plan prep | Explicit promotion (deferred) | `corpus/.../Session N Prep.md` | Yes | One canonical owner |
| Worldbuilding source | Server | `out/workspace/worldbuilding/<uuid>.md` | No | N/A |
| Runbook | Existing policy | Existing | Existing | Existing |

### Writer / hydration

`authorize_target_for_record` for `kind=plan`:

```text
if target == exact own workspace Plan path:
    allow
else if target matches allowed canonical Session Prep path:
    allow
else:
    reject
```

Identity-bound: only `out/workspace/plan/<that record's document_id>.md`, not any UUID-shaped path.

Absent workspace file + `content_status=draft` → empty snapshot + Plan starter content (existing behavior). No new hydration state.

`committed` means durable write to owned Markdown target — **not** “canonical Session N prep.”

### PATCH is not promotion

For `kind=plan`, ordinary metadata PATCH may update `title` and `target_session`, but **must not** change `target_relpath` to a different value. Restating the exact current path may remain legal. Future promotion is a content-aware operation (deferred).

### Create New Prep UX

- Rename label `Target session` → `For session`
- No path field, no canonical checkbox, no branch slug, no document ID
- Same-session quiet copy when other active preps share affinity:
  `N other preps are already aimed at Session K. This will create another alternative.`
- UI-only: disable submit when an **active** same-session document has the same normalized title; discarded titles may be reused. Server does **not** enforce title uniqueness.
- Default session = prep frontier:

```text
highestActiveAffinity = max(target_session of active Plan docs with non-null target_session)
prepFrontier = max(liveSession, highestActiveAffinity)
defaultCreateSession = prepFrontier + 1
```

Discarded documents do not participate in the frontier.

---

## §3 Observable-path and adversarial-sequence inventory

| Path | Current behavior | Required behavior | Same invariant as §1? | Owning boundary |
|---|---|---|---:|---|
| Create New Prep | Client derives canonical `Session N Prep.md` | Omits path; server assigns `out/workspace/plan/<uuid>.md` | Yes | create intent + registry create |
| Second create same session | 409 if path occupied (incl. discarded) | Succeeds with distinct workspace path | Yes | registry create |
| Create form suggestion | Gap-fill from `liveSession+1` | Prep frontier (`max(live, max active affinity)+1`) | Yes | `suggestNextPlanTargetSession` |
| Same-session duplicate title (UI) | Not gated | Submit disabled until distinct among active same-session | Yes | `PlanDocumentCreateControl` |
| Select between same-session alts | Selector works by `documentId` | Unchanged; titles distinguish | Yes | selector (characterization OK) |
| Save workspace Plan draft | Writer rejects non-Session-Prep plan paths | Writes own UUID workspace path; corpus unchanged | Yes | `authorize_target_for_record` + prepare/commit |
| Edit A → switch B → edit B → return A | documentId local state | Remains isolated | Yes | Plan shell / local draft (regression) |
| Discarded canonical owns Session 23 path; create Session 23 workspace | Would 409 if claiming canonical | Succeeds (workspace path) | Yes | registry create |
| Explicit create/PATCH onto occupied canonical path | 409 on create; PATCH had uniqueness after #543 | Create still 409; PATCH cannot change Plan path at all | Yes | registry |
| PATCH workspace → canonical | Allowed if unique | Rejected for `kind=plan` path change | Yes | `_update_workspace_document_metadata_unlocked` |
| Write document B to A's workspace path | N/A / reject Session Prep only | Reject identity mismatch | Yes | `authorize_target_for_record` |
| #543 create supersession / history | Preserved | Must remain preserved | Yes | Plan shell + creation controller |

| Sequence | Required safe outcome | Owning proof |
|---|---|---|
| Create A@27 → Create B@27 distinct titles → save both | Two workspace files; corpus Session 27 Prep untouched | §7 same-session + save |
| live=22, active=23,27 → open create | Suggests 28; operator can set 30 and create | §7 frontier |
| Discarded owns Session 23 Prep.md; create affinity 23 | Workspace create succeeds | §7 discarded isolation |
| PATCH B target to canonical Session 27 Prep | 422/409 fail closed; no revision/path mutation | §7 PATCH seal |
| Corrupted write attempt B → A's workspace path | Authorize rejects | §7 path authority |
| Delayed create / navigate supersession from #543 | Unchanged safe outcomes | Existing PlanSurfaceShell tests must stay green |

---

## §4 Files in scope (allowlist)

| Action | Path | Purpose: how this establishes or proves §1 |
|---|---|---|
| Modify | `apps/live-control-ui/src/workspaceDocument/workspaceDocumentCreation.ts` | Plan intent drops `targetRelpath`; request omits path |
| Modify | `apps/live-control-ui/src/workspaceDocument/workspaceDocumentCreation.test.ts` | Contract proofs for Plan intent mapping |
| Modify | `apps/live-control-ui/src/planSurface/config/planSessionDescriptor.ts` | Prep-frontier suggestion; stop using durable canonical path for Create |
| Modify | `apps/live-control-ui/src/planSurface/config/planSessionDescriptor.test.ts` | Frontier + create helper proofs |
| Modify | `apps/live-control-ui/src/planSurface/components/PlanDocumentCreateControl.tsx` | For session; same-session helper; distinct-title gate; remove durable-path gate |
| Modify | `apps/live-control-ui/src/planSurface/components/PlanDocumentCreateControl.test.tsx` | UX validation proofs |
| Modify | `apps/live-control-ui/src/planSurface/PlanSurfaceShell.tsx` | Create passes title/session only; wire same-session counts into create control as needed |
| Modify | `apps/live-control-ui/src/planSurface/PlanSurfaceShell.test.tsx` | Same-session create/select/isolation + preserve #543 races |
| Modify | `apps/live-control-ui/src/planSurface/planSurface.css` | Quiet helper/error copy styles only if required |
| Modify | `apps/live_control_server/services/workspace_document_registry.py` | `_plan_workspace_target_relpath`; create default; Plan PATCH path seal |
| Modify | `tests/test_workspace_document_registry.py` | Same-session create; discarded canonical irrelevant; PATCH not promote; uniqueness still sealed |
| Modify | `apps/live_control_server/services/tiptap_markdown_write.py` | Authorize exact Plan workspace UUID path + existing Session Prep |
| Modify | `tests/test_tiptap_markdown_write.py` | Path authority + Save to workspace Plan path |
| Modify | `Docs/Plans/HANDOFF-BUILD-plan-multi-prep-per-session-design.md` | Mark design accepted / superseded by this handoff (status only) |
| Modify | `Backlog.md` / `Backlog-DONE.md` | Only if operator includes bookkeeping in this PR; otherwise post-merge doc-sync |

**Bounded discovery exception:**

```text
Directory: apps/live-control-ui/src/planSurface/
Maximum additional paths: 3
Allowed path kinds: existing create-control props types, thin CSS, or characterization-only selector test
Decision rule for including one: required to pass same-session helper props or a failing characterization after the allowlist changes; report in handback
```

`defaultPlanTargetRelpath` / `durablePlanTargetRelpath` may remain for legacy/canonical display/tests if still referenced; they must **not** drive Create New Prep storage.

---

## §5 Files and capabilities explicitly out of scope

| Path, layer, or capability | Why this slice must not touch or claim it |
|---|---|
| Promote to Session Prep API/UI | Successor content transaction |
| `release_target_relpath_from_discarded_duplicate` redesign | Already sealed in #543; only consume uniqueness |
| Build bare `worldbuilding_source` auto-create | Independent consumer; already server-path |
| Runbook create / descriptors | Caller-path policy unchanged |
| AppChrome / GraphLoadPanel / surface context bar | READY successor; sequencing only |
| Ask continuity across prep switches | Independent successor |
| EditHost always-open toolbar | Sidequest; separate polish |
| Corpus layout / Session Prep filename grammar | No Shape A |
| Server title-uniqueness invariant | UI affordance only |
| Document rename/archive/search manager | Explicit non-goal |
| `src/prompts/*.py`, gold fixtures | Unrelated |
| Live registry surgery / manual `workspace_documents.json` edits | STOP — use governed repair only if preflight fails |

---

## §6 Implementation contract and conditional matrices

```text
Input:
  Plan Create New Prep: { title, targetSession }
  Optional low-level create: kind=plan with explicit target_relpath (compat only)

Output:
  Registry record with opaque documentId, target_session affinity,
  non-null target_relpath = out/workspace/plan/<documentId>.md (normal create)
  Activated Plan surface on exact documentId

Invariant:
  Affinity never determines identity or unique storage; Create New Prep always
  gets server UUID workspace target; canonical ownership unique and not PATCH-promotable

Failure behavior:
  Occupied explicit/compat path → 409, no mutation
  Plan PATCH path change → reject (422 preferred; 409 if framed as conflict), no mutation
  Unauthorized write path → TipTap write error, no file write
  Same-session duplicate title (UI) → submit disabled
  Create/activation failures → preserve #543 semantics

Replay / idempotency:
  same create intent while busy → rejected (no second POST)
  retry after create_failed → new POST allowed
  retry after activation_failed → activate only, no repost (#543)
  superseded create POST → intentCurrent=false, no auto-activate (#543)

Trust boundary:
  Verifies: registry path uniqueness; Plan workspace path == record.document_id;
            PATCH cannot rebind Plan storage; writer allowlist
  Records or trusts without proving: human title distinctiveness (UI only)
```

### A. State and fallback matrix

| Observable path | Loading / initializing | Exact success | Ordinary miss | Dependency unavailable | Integrity / contract failure | Stale / superseded | Retry / replay |
|---|---|---|---|---|---|---|---|
| Create New Prep | creating phase | record + activate | N/A | API error → create_failed | 409 on compat path clash | intentCurrent fencing | #543 rules |
| Open new workspace prep | draft, file absent | empty + starter | N/A | snapshot error surfaced | committed+missing still 409 | N/A | reload same documentId |
| Save workspace prep | saving | committed to UUID path | N/A | write error | authorize reject | N/A | retry save |
| Select alt same session | loading exact id | Canvas on that id | 404 keeps current | list refresh soft | N/A | generation fence | #541/#543 |

### B. Identity matrix

| Situation | Required rule | Ambiguity behavior | Fallback permitted? |
|---|---|---|---|
| Exact documentId | Sole activation identity | Fail closed on unknown | No |
| target_session | Affinity only; many docs OK | N/A | N/A |
| Title | Display / UI distinctness among active same-session | Block submit in UI | No server fallback |
| target_relpath | Unique owner including discarded | 409 | No |
| Workspace plan path | Must equal `out/workspace/plan/<own documentId>.md` | Reject write | No |

### C. Persistence and replay matrix

| Operation | Durable representation | Round-trip guarantee | Duplicate / replay behavior | Compatibility / migration | Rollback / reversion |
|---|---|---|---|---|---|
| Create (normal Plan) | Registry row + workspace path binding; file may be absent until Save | documentId stable; path = UUID workspace | Uniqueness on path; titles not unique server-side | Explicit path create remains for fixtures | Discard status only (no auto-delete) |
| Save | Markdown bytes at owned path; content_status=committed | Reload snapshot matches | Concurrent write uses existing locks | Canonical records unchanged | N/A |
| PATCH metadata | title / target_session only for Plan path rebinding | Path unchanged | Path change rejected | Restate same path OK | N/A |

### D. Predecessor-to-consumer mapping

**Grounding source:** current `WorkspaceDocumentCreateIntent` plan arm + `create_workspace_document` + `authorize_target_for_record`

| Predecessor field / outcome | Real shape and optionality | Consumer field / behavior | Transformation | Proof fixture/test |
|---|---|---|---|---|
| `intent.targetRelpath` (Plan) | `string \| null` today | Removed from Plan product intent | Omit from POST | `workspaceDocumentCreation.test.ts` |
| Client `durablePlanTargetRelpath(...)` at create | Canonical corpus path | Must not be called for Create New Prep | Delete call site in shell | `PlanSurfaceShell` create tests |
| Server `target_relpath=None` for plan | Stored as null today | Generate workspace path | `_plan_workspace_target_relpath` | registry tests |
| Plan authorize Session Prep only | Regex allowlist | Also allow exact own workspace path | Mirror worldbuilding identity check | `test_tiptap_markdown_write.py` |
| Plan PATCH `target_relpath` | Allowed if unique (#543) | Reject different value for kind=plan | Seal in metadata update | registry PATCH tests |
| `suggestNextPlanTargetSession` | Gap-fill from live+1 | Prep frontier | `max(live, maxActive)+1` | descriptor tests |

---

## §7 Evidence required to merge

| Guarantee / invariant clause | Owning boundary | Evidence class | Command or manual scenario | Expected evidence | Stop condition |
|---|---|---|---|---|---|
| Same-session alternatives get distinct workspace paths | registry create | contract | pytest registry: two plan creates session=27 | different document_id; same target_session; distinct `out/workspace/plan/<id>.md`; both active | Shared path or null path on normal create |
| Create New Prep omits client path | creation intent + Plan shell | contract | vitest creation + PlanSurfaceShell | POST body has no target_relpath (or null); record returns workspace path | Client still sends Session N Prep.md |
| Prep frontier suggestion | planSessionDescriptor | unit | vitest descriptor | live=22, active=23,27 → 28; live=25, active=23 → 26 | Gap-fill 24 behavior remains |
| Discarded canonical irrelevant to workspace create | registry | adversarial | create session affinity matching discarded canonical owner | 200/success with workspace path | 409 |
| Canonical uniqueness still sealed | registry | regression | create/assign second owner of Session N Prep.md | 409 no mutation | Silent duplicate |
| Path authority identity-bound | tiptap write | adversarial | plan record B cannot authorize A's workspace path | write error | Any-UUID allow |
| Save workspace Plan does not touch corpus | tiptap write + optional shell | contract/integration | save two workspace drafts | files under `out/workspace/plan/`; corpus Session Prep unchanged | Corpus mtime/content change |
| PATCH not promotion | registry metadata | adversarial | PATCH workspace plan → canonical Session Prep path | reject; revision/path unchanged | Path updated |
| documentId isolation across alts | PlanSurfaceShell | regression | edit A → B → A | local/server content isolated | Cross-doc clobber |
| #543 create races preserved | PlanSurfaceShell / creation controller | regression | existing supersession tests | still green | Flake or remove |

Run:

```bash
cd apps/live-control-ui && pnpm exec vitest run \
  src/workspaceDocument/workspaceDocumentCreation.test.ts \
  src/planSurface/config/planSessionDescriptor.test.ts \
  src/planSurface/components/PlanDocumentCreateControl.test.tsx \
  src/planSurface/PlanSurfaceShell.test.tsx

cd ../.. && uv run pytest \
  tests/test_workspace_document_registry.py \
  tests/test_tiptap_markdown_write.py \
  -q

git diff --check
git diff --stat <base>...HEAD -- <§4 paths>
git diff --name-only <base>...HEAD
```

### Minimal live / dogfood proof

```text
Existing surface used: Plan Create New Prep + selector + Save
Smallest realistic scenario:
  1. Create "If the party goes north" for Session 27
  2. Create "If the siege breaks" for Session 27
  3. Switch and edit both; Save both
  4. Confirm Create suggests frontier beyond max active affinity
Expected observation:
  Both selectable; both writable; no path/UUID/promotion/conflict UI;
  corpus Session 27 Prep untouched if it exists
Evidence captured: manual notes + registry/path listing under out/workspace/plan/
```

### Baseline failure protocol

For any required command already failing on base: compare base vs head; do not call green; name waiver if required.

---

## §8 Required review handback

The review handback, not the PR description, must include:

1. Exact PR URL or branch/head SHA being reviewed
2. §1 Mission and merge-ready invariant copied exactly
3. The §7 evidence ledger: required evidence, produced result, and provenance
4. Nano-commit list and the discrete fix/proof story for each commit
5. Base SHA and head SHA
6. Actual changed paths and focused diff stat limited to §4
7. Every §7 command/scenario and exact result
8. Provenance of each result
9. Baseline failures with base/head comparison
10. Explicit operator waivers; `none` when none exist
11. Paths outside §4; `none` or a stop report
12. Stop conditions encountered and resolution; `none` when none exist
13. Successor capabilities deferred and still false
14. Confirmation that the authoritative handoff was implemented without compressed or omitted constraints

---

## §9 Acceptance rubric

- [ ] Exactly one independently useful capability from §1 was delivered — proved by §7 same-session + create mapping proofs
- [ ] Merge-ready invariant holds across every §3 path/sequence — proved by §7 ledger
- [ ] Review identifies exact PR/branch/head SHA and checks the invariant against handoff + cumulative diff
- [ ] Every required proof has a produced result and provenance, or an explicit operator waiver
- [ ] No second public/durable contract was silently introduced (no promotion API; no title uniqueness server invariant) — proved by diff inspection + contract tests
- [ ] §6 matrices followed — proved by §7
- [ ] Real predecessor vocabulary used — proved by creation/registry/write tests
- [ ] No path outside §4 changed — proved by `git diff --name-only`
- [ ] Baseline failures reported truthfully
- [ ] Minimal live proof did not grow into unacknowledged product surface
- [ ] Named successors remain unimplemented: promotion, surface context bar, Ask continuity

## Stop conditions

Stop and report rather than expanding if implementation discovers:

- Save still impossible for workspace Plan paths without inventing a second persistence model
- Hydration treats absent `out/workspace/plan/<uuid>.md` as integrity failure for draft records
- Create New Prep still must know campaign corpus layout to succeed
- PATCH seal cannot be added without breaking a required non-Plan metadata flow that this slice did not inventory
- A second independently useful outcome (promotion, document manager, chrome move)
- Required path outside §4 / bounded exception
- Live registry preflight fails uniqueness — **do not** manually delete records; report and use governed repair only with operator approval

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

---

## Dogfood acceptance (operator voice)

```text
I have one Session 27 plan.
I think Session 26 could end two different ways.
I create another prep for Session 27.
I name the two possibilities.
I switch between them and work normally.
Nothing asks me about files, paths, UUIDs, promotion, or conflicts.
```

And:

```text
I am currently around Session 22.
I already sketched through Session 27.
Create New Prep suggests Session 28,
but I can type Session 30 and start sketching it immediately.
```
