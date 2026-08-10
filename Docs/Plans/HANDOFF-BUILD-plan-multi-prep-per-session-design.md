# Handoff: Plan multi-prep-per-session (contingent / ahead-of-time)

**Purpose:** Give the design agent a focused brief from PR #543 Create New Prep dogfood so we can examine what work is required to support this **now**, not as a vague later successor.

**Status:** DESIGN ACCEPTED — Shape B (workspace-backed drafts until promote). Superseded for implementation by `Docs/Plans/HANDOFF-BUILD-dogfood-polish-plan-session-affinity-workspace-drafts.md`  
**Created:** 2026-08-10  
**Accepted:** 2026-08-10  
**Repository:** `Drakosfire/DungeonMindBuddy`  
**Merged predecessor:** PR #543 → `b8e4dd214b1171793051ce507c0b93c6d87efa91`  
**Canonical path:** `Docs/Plans/HANDOFF-BUILD-plan-multi-prep-per-session-design.md`  
**Implementation handoff:** `Docs/Plans/HANDOFF-BUILD-dogfood-polish-plan-session-affinity-workspace-drafts.md`

**Predecessor / adjacent:**
- PR #541 — choose active Plan prep document (`documentId` selection)
- PR #543 — generalized intentional workspace-document create + `target_relpath` uniqueness
- Backlog IDEA: *Multiple Plan preps per session (contingent / ahead-of-time branches)*
- Decision: `Docs/Design/DECISION-workspace-document-target-relpath-duplicate-repair.md`

**Not this brief:** surface context bar chrome placement; Ask continuity across document switches; EditHost dock-default-open polish.

---

## 1. Primary design goal

Decide how Plan **Create New Prep** should let the GM:

1. **Prep ahead of the live session cursor** (e.g. live is ~22, still author Session 27+), and
2. **Keep more than one Plan document aimed at the same upcoming session**, because the right prep depends on what happened in the prior session (contingent / branching prep).

The design must preserve opaque `documentId` as the active document identity (#541/#543), and must **not** reopen silent duplicate durable-path ownership.

---

## 2. Operator need (dogfood voice)

> If I want to prep way ahead of time and have more than one plan for a given session depending on what happened in the prior session, the current Target Session → `Session N Prep.md` singleton fights me.

Concrete examples the product should admit:

- Two active drafts both “for Session 27”: *if the party goes north* vs *if the siege breaks*.
- An early Session 30 sketch while still playing Session 22, without pretending it is already the canonical corpus Session Prep file.
- Selecting among those drafts in the Plan selector by human-meaningful labels, not by fighting 409s.

---

## 3. What is true in the product today

### 3.1 Target session is overloaded

**Target session** currently means both:

| Role | Meaning today |
|---|---|
| Affinity label | “This prep is aimed at table Session N” |
| Durable singleton key | Create builds `…/Session Prep/Session N Prep.md` and the registry allows **at most one** non-null owner of that path (active *or* discarded) |

Create suggestion is `liveSession + 1`, skipping only *active* selector `target_session` values. Discarded path owners are invisible to the suggestion but still block create (409).

Dogfood evidence (2026-08-10):

- Live cursor ≈ 22 → default suggestion **23**
- Discarded Session 23 still owns `Session 23 Prep.md`
- Default Create immediately 409s with registry jargon + UUID
- Creating **27** works and lands on a new opaque `documentId`

### 3.2 Invariants that must stay sealed

Do **not** “fix” multi-prep by weakening:

- one non-null `target_relpath` → one registry owner (create + metadata PATCH)
- discarded owners still count
- exact `documentId` URL/Canvas activation
- intentional create (no silent empty-registry bootstrap)

The collision guard is correct for **paths**. The product mistake is forcing every Plan create to claim the canonical `Session N Prep.md` path from the session number alone.

### 3.3 Corpus reality

Longmont Campaign layout historically treats `Session N Prep.md` as *the* prep file for that session. That may remain the **canonical publish/commit target**. It should not be the only allowed Plan workspace document that can be *about* Session N.

---

## 4. Design question (answer this first)

**Separate session affinity from durable path claim.**

Propose a contract where:

- many Plan documents may share the same `target_session` (or equivalent affinity), and
- at most one of them (or none, until promotion) owns the canonical `Session N Prep.md` path, and
- additional docs use distinct durable paths (or null path until claim/promote), and
- the Plan selector remains a quiet list of exact documents, not a session-management app.

Also decide what Create New Prep should **suggest** by default when:

- live session is behind the highest active prep,
- a lower session path is owned only by discarded records,
- the operator is deliberately branching an already-prepped session.

---

## 5. Candidate shapes (examine cost to ship now)

Design agent: pick one primary shape for a **now** slice, with explicit reject reasons for the others. Prefer reversible, small-scope options.

### Shape A — Affinity + distinct branch paths

- Keep `target_session: N` as affinity metadata.
- Canonical path remains `Session N Prep.md` (optional claim).
- Additional creates use distinct paths, e.g.  
  `Session N Prep — <branch-slug>.md` or  
  `Session N Prep/<branch-slug>.md`  
  under an allowlisted writer root.
- Selector label includes session + branch/title.
- 409 still applies per exact path.

**Examine:** corpus allowlist / write policy; whether branch files are first-class corpus or `out/workspace/…` drafts.

### Shape B — Draft path until promote

- New creates always get a registry-owned draft path (UUID under `out/workspace/plan/…` or similar), with `target_session` as affinity only.
- “Promote to Session Prep” (separate intentional action) claims `Session N Prep.md` under the uniqueness guard (may 409 if already owned).
- Enables ahead-of-time and branching without touching corpus layout until the GM chooses.

**Examine:** snapshot/hydration for missing corpus files; promote UX; what “Save to Markdown” means pre-promote.

### Shape C — Same path forbidden; session affinity only in title

- Drop structured `target_session` from create (or make optional).
- Operator names docs freely; path is always UUID-owned draft.
- Weakest corpus alignment; cheapest uniqueness story; poorest “Session N” discovery.

**Examine only if A/B are too expensive for a now slice.**

### Non-shapes (reject unless strongly justified)

- Allowing two records to share the same non-null `target_relpath`.
- Silent auto-suffix on 409.
- Auto-restore discarded docs to free a path.
- Building a full document-management / branch-merge product in this slice.

---

## 6. Work to examine for “complete this now”

Produce a scoped estimate as **files/contracts/dependencies**, not calendar time.

### 6.1 Product / UX

- Create form fields: session affinity vs path claim vs branch label.
- Default suggestion policy that does not aim at discarded-owned canonical paths.
- Collision copy without UUID/`target_relpath` jargon (handoff Scenario E).
- Selector option labeling for same-session multiples.
- Whether empty-state create and “next prep” create share one form schema.

### 6.2 Client contracts

- `WorkspaceDocumentCreateIntent` for `kind: "plan"` — what becomes required/optional.
- `durablePlanTargetRelpath` / `suggestNextPlanTargetSession` — replace or split.
- Plan create control copy and validation fail-closed rules.
- Tests: same-session two creates succeed with distinct paths; canonical claim still 409s when owned.

### 6.3 Server / registry

- Create request validation when path is omitted vs caller-provided vs server-derived.
- Writer allowlist for any new Plan path patterns.
- PATCH still cannot steal another record’s path.
- Whether discarded canonical owners block promote (yes today; confirm product intent).

### 6.4 Corpus / authoring lifecycle

- When does TipTap Save write which file?
- Hydration when affinity is Session N but path is draft.
- Relationship to existing “committed workspace target file is missing” on Session 26.

### 6.5 Explicit out of scope for the now slice (unless design proves otherwise)

- Merge/diff of two Session-27 branches into one canonical prep.
- Auto-discard of losing branch.
- Surface context bar relocation.
- Ask thread continuity.
- Build/runbook multi-doc redesign beyond reusing the shared create contract.

---

## 7. Success criteria for the design answer

The design agent’s output should be mergeable into an implementation handoff and must include:

1. **Chosen shape** (A/B/C or a tighter hybrid) and why.
2. **Field-level create contract** for Plan (intent → request → registry record).
3. **Path policy table**: who generates path, when canonical claim happens, what 409 means in GM language.
4. **Suggestion policy** for Create New Prep defaults.
5. **Now vs later**: smallest shippable slice that unlocks ahead-of-time + same-session multiples, vs deferred promote/merge work.
6. **Falsification**: GM can create two Session-27-aimed Plan docs, switch by selector, edit both without cross-contamination; claiming the canonical Session 27 path twice still fails closed.

---

## 8. Suggested reading pack (attach / open)

| Doc | Why |
|---|---|
| This handoff | Mission + constraints |
| `Docs/Plans/HANDOFF-BUILD-dogfood-polish-generalized-workspace-document-create.md` §5, §16 | Create contract + dogfood scenarios E |
| `Docs/Design/DECISION-workspace-document-target-relpath-duplicate-repair.md` | Path uniqueness + repair policy |
| `apps/live-control-ui/src/planSurface/config/planSessionDescriptor.ts` | `durablePlanTargetRelpath`, `suggestNextPlanTargetSession` |
| `apps/live-control-ui/src/workspaceDocument/workspaceDocumentCreation.ts` | Kind-aware create intent |
| `apps/live_control_server/services/workspace_document_registry.py` | Create/PATCH uniqueness |
| `Docs/Design/DESIGN-plan-surface-session-prep-current-goal-2026-07.md` | Plan product checkpoint (if still ACTIVE) |

---

## 9. Operator judgment to preserve

Creating a prep should feel like **“I made the prep I am about to work on,”** including contingency preps — not like administering a single slot per session number.

Path uniqueness is a **storage safety** invariant. Session affinity is a **planning** concept. Do not collapse them again.
