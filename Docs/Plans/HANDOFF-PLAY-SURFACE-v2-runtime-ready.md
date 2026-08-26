---
pr_body_template: |
  ## Handoff pointer
  - Conversation/workstream: PLAY-SURFACE / BF2
  - Flow: PLAY-SURFACE
  - Direction: DESIGN → CODE → REVIEW
  - Handoff: Docs/Plans/HANDOFF-PLAY-SURFACE-v2-runtime-ready.md
  - Branch / PR: agent/play-surface-v2-runtime-ready / PLAY-SURFACE: admit beat-first v2 runtime

  ## Verification pointer
  - Base/head: record exact SHAs in the PR
  - Changed paths: HANDOFF §4
  - Verification: HANDOFF §7

  The checked-in handoff, cumulative diff, nano-commit story, and independently
  rerun evidence are the review contract. This body is transport metadata.
---

# HANDOFF — Beat-first v2 Runtime READY and cockpit contract sync (BF2)

**Created:** 2026-08-26  
**Status:** ACTIVE — implementation under review  
**Canonical handoff path:** `Docs/Plans/HANDOFF-PLAY-SURFACE-v2-runtime-ready.md`  
**Workstream:** `PLAY-SURFACE / BF2`  
**Flow / owner:** `PLAY-SURFACE`  
**Handoff direction:** DESIGN → CODE  
**Suggested branch:** `agent/play-surface-v2-runtime-ready`  
**PR title:** `PLAY-SURFACE: admit beat-first v2 runtime`

> **Dispatch base at design time:** `555a9c7965aca47a24536277b9b36ae569a7285a` — `PLAY-SURFACE: re-anchor cockpit design on scene-centered play`.  
> Before branch creation, fetch `main`, record the exact base SHA, inspect active PR/worktree leases, and stop if another owner has acquired any production path in §4. A disjoint main advance is not itself a blocker.

Parent authorities:

* `Docs/Design/ARCHITECTURE-playable-material-and-runtime.md`
* `Docs/Design/DESIGN-play-current-moment-cockpit.md`
* `Docs/Design/DESIGN-play-surface-projection.md`
* `Docs/Design/DESIGN-play-surface-gm-cockpit-target.md`
* `Docs/Roadmaps/ROADMAP-con-ready.md`
* `Docs/Plans/STEWARDS-ANCHOR-con-ready.md`
* `Docs/Design/ARCHITECTURE-application-state-layer.md`
* `Docs/Design/ARCHITECTURE-surface-interaction-layer.md`

Predecessors:

* BF1 / PR #628 — Beat-first v2 grammar, index, and manifest foundation.
* APP-STATE AS2–AS5 — historical immutable Runbook WorkRevisions, PostgreSQL Play Runtime, active-Run continuity, legacy Play persistence demolition.
* `555a9c7…` — Scene-centered Play design re-anchor.

This is the exact BF2 dispatch contract. Cycle 1 review `5035652206` required the file to be checked in; it does not weaken the original constraints. Paths added only because the review named them as required (this HANDOFF itself) remain review-authorized extras, not a silent lease expansion.

---

## §1 Mission and merge-ready invariant

**Mission:** A Beat-first v2 Play Run can become truthfully READY against its exact pinned Playable WorkRevision, with durable current-position semantics and derived authored-Choice relevance, so the later Scene-centered cockpit can consume Runtime state without inventing or repairing it in presentation code.

**Merge-ready invariant:** Every native-ready v2 Run is bound to one exact historical Playable WorkRevision and its sealed v2 manifest; before READY it has one durably admitted `current_beat_id` seeded from the exact pinned document order, `current_scene_id` is either null or a Scene owned by that Beat, all resolved Beats / Decision selections / note anchors are admitted against the sealed v2 membership, progress changes retain the existing `run_revision` CAS contract, and Beat/Scene relevance is derived solely from sealed `activates`/`suppresses` edges plus persisted selections and is never stored independently. Zero-Beat v2 material fails closed, stale mutations fail closed, and existing v1 Run admission/progress behavior remains unchanged.

### Pre-dispatch critique

| Question | Answer |
|---|---|
| Can one invariant govern every claimed observable path? | Yes. Every path is admission or mutation of one exact Run/Playable/manifest binding plus derivation from that state. |
| Most likely adversarial sequence | Two clients open one BF1-created v2 Run with empty progress → both derive seed → one CAS wins → stale completion attempts a second mutation or reports a different current Beat. |
| Will §7 actually detect that failure? | Yes. PostgreSQL concurrency/idempotency proof plus native-admission test must show convergence on one seed and one truthful READY state. Cycle 1 additionally requires an owning-boundary native load → preflight → seed CAS → reread/admit witness. |
| Easiest owning boundary to under-test | The join between exact historical WorkRevision document order and durable seed mutation. Manifest arrays must not accidentally become ordering authority. |
| Fact that forces stop/split | Native READY requires a new public endpoint/schema, a new durable state field, or a real BF3 workspace UI merely to avoid misrepresenting v2. |

---

## §2 Context, authority, and lane

| Field | Required content |
|---|---|
| Parent authority | Architecture/design/roadmap listed in the header |
| Base revision | `555a9c7965aca47a24536277b9b36ae569a7285a` at design time; record the exact fetched `main` before branch creation |
| Predecessor contract | BF1 / PR #628 grammar+manifest; APP-STATE AS2–AS5 PostgreSQL Runtime |
| Exact input consumed | `PlayRunRecord` + exact historical pinned WorkRevision + sealed `PlayRunReferenceManifestV1 \| V2` + current `PlayRunProgress` |
| Named successor | BF3 Scene-centered cockpit; BF3.x/P3 retrieval; P4 Combat workspace; BF4 Plan composition |
| What remains false | BF3 cockpit UI, collapsible chrome, At-a-Glance category expansion, Combat workspace, new Note schema, v1→v2 migration, manifest-array document order |
| Explicit non-goals | Combat runtime, Surface Interaction host, Agent writes, new persisted progress fields, new endpoints |
| Branch / isolated checkout | `agent/play-surface-v2-runtime-ready` |
| Parallel lanes / collision hotspots | Play Surface vs APP-STATE AS5: AS5 demolished Play file persistence; BF2 may proceed on the disjoint Play Surface lease. Stop if another owner acquires any §4 production path. |
| Runtime/state ownership | Shared PostgreSQL Play Runtime. No new schema. Existing `run_revision` CAS owns mutation. |
| State-authority sync set after merge | HANDOFF completion/archive; `Docs/Roadmaps/ROADMAP-con-ready.md` BF2 status; design-agent mirrors already in this PR's design-sync set |

---

## 0. Repository truth and capability decomposition

### 0.1 Current truth

The durable Playable model is already:

```text
Runbook → Beat → Scene → Decision → Option
```

BF1 already supplies v2 grammar, index, manifest sealing, and v1/v2 discrimination. APP-STATE already supplies immutable WorkRevisions, exact Run binding, PostgreSQL progress CAS, and active-Run resume.

What remains structurally false is BF2:

```text
v2 sealed Run → native Play admission → durable current Beat → optional same-Beat current Scene → valid v2 progress mutation → derived Choice relevance → READY
```

### 0.2 Candidate outcomes

| Candidate | Decision |
| ---------------------------------------- | ------------------------------------------------------------------- |
| v2 Runtime current-position admission | **KEEP — BF2 mission** |
| v2 Choice relevance derivation | **KEEP — same Runtime/projection invariant** |
| Scene-centered cockpit implementation | **SPLIT — BF3** |
| Collapsible Beat Context / At a Glance | **SPLIT — BF3** |
| At-a-Glance category → central workspace | **SPLIT — BF3**, contract synchronized here |
| Combat → central workspace | **SPLIT — P4/Combat**, same presentation contract synchronized here |
| Global/on-demand object finder | **SPLIT — BF3.x/P3** |
| New Note persistence model | **SPLIT / not authorized** |
| Agent-assisted Play authoring | **SPLIT / later** |

---

## 1. Capability contract (dispatch)

### 1.1 What becomes true

```text
v2 Run can cross native Play admission into READY
v2 current Beat is durably seeded before READY
Beat-only current position is legal
current Scene is optional
current Scene must belong to current Beat
explicit Beat + Scene progress is admitted
v2 Decisions / Options are valid Runtime selections
activates / suppresses produces derived relevance
activation wins when the same target is both activated and suppressed
suppressed material remains admitted / addressable
historical pinned WorkRevision remains the source of document order and prose
v1 Runs behave exactly as before
```

First seed must occur only after a read-only preflight proves the exact pinned authority set. A malformed/mismatched v2 load must perform zero Runtime writes. A READY v2 Run cannot be cleared back to empty progress.

### 1.2 Exact pinned authority

BF2 never derives current position from current/latest Runbook revision, current workspace draft, filesystem Runbook bytes, manifest array order, display labels, or a reconstructed document from current state.

It uses the Run's exact persisted binding and the exact pinned WorkRevision bytes as document-order authority.

Seed rule:

```text
exact pinned v2 WorkRevision
→ derive Beat order from document bytes using BF1 fence/grammar admission
→ first beat_kind=spine Beat
→ otherwise first Beat
→ zero Beats = fail closed
```

Before the surface reports the Run as READY:

```text
current_beat_id = chosen seed
current_scene_id = null
```

must be durable Runtime truth.

Concurrency uses existing `run_revision` CAS. Two simultaneous first admissions must converge on one persisted current Beat. A 409/rebase recovery must refetch the full exact authority set when the Playable binding changed rather than pairing a reread Run with stale manifest/WorkRevision bytes.

### 1.3 Derived authored-Choice relevance

Relevance is projection state. It is never persisted. Compare the complete behavior-bearing v2 structural contract — membership, parentage, `beat_kind`, and `activates`/`suppresses` edges — against the exact pinned WorkRevision. Fail closed on divergence.

---

## §3 Observable paths and adversarial sequences

| Path | Current behavior | Required behavior | Same §1 invariant? | Owning boundary |
|---|---|---|---:|---|
| Existing v1 Run | Scene-first admission/progress | Unchanged | Yes | progress admission + native projection |
| New/BF1 v2 Run with empty progress | Not READY / Scene-first refusal | Read-only preflight, then durable first-spine/first-Beat seed, then READY | Yes | native load → preflight → CAS seed |
| v2 Run already seeded | n/a | Resume exact persisted Beat/Scene; do not reseed | Yes | native load |
| READY v2 → empty progress PUT | Previously accepted via empty short-circuit | Reject; preserve prior Run/revision | Yes | `replace_play_run_progress` |
| v2 Beat-only / Beat+same-Beat Scene | Scene-first rules | Legal | Yes | `_admit_progress_v2` |
| v2 Beat + foreign Scene / unknown IDs | n/a | Fail closed | Yes | `_admit_progress_v2` |
| Decision → own/foreign Option | n/a | Legal / fail closed | Yes | `_admit_progress_v2` |
| simultaneous first admissions | n/a | One seed wins; other converges after CAS conflict/reread | Yes | PostgreSQL CAS + full rebind |
| 409 during seed after rebase | reread Run only | Full reload of Run+manifest+pinned WorkRevision | Yes | PlaySurfacePage load |
| pinned historical revision N while N+1 exists | n/a | Continue from N | Yes | exact committed revision |
| sealed edge/`beat_kind` corruption | membership-only compare | Fail closed | Yes | `compareV2Membership` |
| zero-Beat / malformed manifest | n/a | Never READY; no seed write | Yes | preflight |
| derived relevance | n/a | Recompute; never persist | Yes | projection |

| Sequence | Required safe outcome | Owning §7 proof |
|---|---|---|
| empty v2 load → preflight fail | zero Runtime writes | App test: mismatched manifest never calls PUT |
| empty v2 load → preflight ok → seed CAS | durable current Beat then READY | owning-boundary postgres helper + App seed test |
| seed 409 → reread rebased binding | old manifest/bytes not reused | App test: committed revision refetch |
| seed → empty replacement | reject; prior Beat preserved | postgres + progress tests |
| equivalent concurrent seeds | one Beat; no divergent Runtime | existing postgres converge test |

---

## §4 Write lease

| Path | Why |
|---|---|
| `Docs/Plans/HANDOFF-PLAY-SURFACE-v2-runtime-ready.md` | Checked-in review contract (Cycle 1 required this missing dispatch copy) |
| `apps/live_control_server/services/play_run_registry.py` | Version-aware v1/v2 progress admission; BF1-parser opening Beat; sealed-structure compare; owning first-admission helper |
| `src/application_state/play/service.py` | Distinguish legal pre-READY empty progress from clearing an already-seeded v2 current Beat |
| `apps/live-control-ui/src/playSurface/runbook/nativeRunbookProjection.ts` | v2 native admission, read-only preflight, Beat-rooted ready model |
| `apps/live-control-ui/src/playSurface/runbook/v2RuntimeProjection.ts` | BF2-local helper: empty progress, opening Beat, sealed-structure compare, relevance |
| `apps/live-control-ui/src/playSurface/PlaySurfacePage.tsx` | Preflight then seed; full rebind on 409; smallest truthful v2 READY presentation |
| `apps/live-control-ui/src/playSurface/runbook/index.ts` | Export BF2 helper/type only if required |
| `tests/test_play_run_progress.py` | v1/v2 progress admission, including refuse empty-clear after READY |
| `tests/application_state/test_play_runtime_postgres.py` | Durable seed/CAS/concurrency/historical-revision and owning-boundary first admission |
| `apps/live-control-ui/src/playSurface/runbook/nativeRunbookProjection.test.ts` | v2 admission, order, membership, edges, relevance |
| `apps/live-control-ui/src/playSurface/runbook/v2RuntimeProjection.test.ts` | BF2-local helper tests |
| `apps/live-control-ui/src/App.test.tsx` | `/play` load/READY: preflight, seed, 409 rebind, no PUT on mismatch |
| `Docs/Design/DESIGN-play-current-moment-cockpit.md` | Cockpit composition refinement as BF3/P4 target |
| `Docs/Design/DESIGN-play-surface-projection.md` | Same |
| `Docs/Design/DESIGN-play-surface-gm-cockpit-target.md` | Same |
| `Docs/Roadmaps/ROADMAP-con-ready.md` | Future BF3/P4 behavior; not marked implemented |
| `Docs/Sources/design-agent/ACTIVE_REFERENCE/DESIGN-play-current-moment-cockpit.md` | Byte-identical mirror |
| `Docs/Sources/design-agent/ACTIVE_REFERENCE/DESIGN-play-surface-projection.md` | Byte-identical mirror |
| `Docs/Sources/design-agent/ACTIVE_REFERENCE/DESIGN-play-surface-gm-cockpit-target.md` | Byte-identical mirror |
| `Docs/Sources/design-agent/ACTIVE_AUTHORITY/ROADMAP-con-ready.md` | Byte-identical mirror |

Bounded discovery exception (original dispatch): `apps/live-control-ui/src/playSurface/runbook/` may add at most two extra paths — one BF2-local pure helper/type module and its focused test. Used for `v2RuntimeProjection.ts` and `v2RuntimeProjection.test.ts`.

Do not modify `RunbookTableDeck.tsx` merely to force v2 into its v1 Scene-first presentation.

---

## §5 Explicitly out of scope

| Path | Why |
|---|---|
| `apps/live-control-ui/src/playSurface/runbook/RunbookTableDeck.tsx` | v1 Scene-first deck stays v1-only |
| Combat runtime/persistence/service/API | P4 |
| Campaign Supergraph / World identity / mechanics authority | not Play Runtime |
| Surface Interaction host / AgentInteractionProvider | later |
| Plan authoring composition | BF4 |
| New Run schema / PlayRunProgress fields / note schema | not authorized |
| `ARCHITECTURE-playable-material-and-runtime.md` | stop if cockpit refinement requires a semantic architecture change |
| `apps/live_control_server/services/play_run_reference_manifest.py` | BF1 parser is consumed, not rewritten |

Also do not claim: global search/finder, At a Glance runtime UI, Beat Context runtime UI, cockpit CSS/layout, new image asset, legacy v1 migration, temporal/tick ledger.

---

## §6 Implementation notes

```text
Input: PlayRunRecord
       exact historical pinned WorkRevision
       sealed PlayRunReferenceManifestV1 | V2
       current PlayRunProgress
Output: v1: unchanged admitted native projection
        v2: truthful READY native projection after read-only authority
            preflight and durable current-Beat seed, with Beat-rooted
            structure, optional current Scene, admitted progress, and
            derived relevance
Durable state: existing PlayRunProgress only
New persisted schema: none
New endpoint: none expected
Mutation authority: existing run_revision CAS
Document order authority: exact pinned WorkRevision bytes via BF1 grammar
Relevance authority: sealed v2 edges + persisted selections
Failure: identity/membership/integrity mismatch → fail closed, no seed write
         stale CAS → conflict / full authority rebind
         dependency unavailable → no fabricated READY state
```

---

## §7 Evidence required to merge

Run:

```bash
uv run pytest tests/test_play_run_progress.py -q
uv run pytest tests/application_state/test_play_runtime_postgres.py -q
pnpm --dir apps/live-control-ui exec vitest run src/playSurface/runbook/nativeRunbookProjection.test.ts src/playSurface/runbook/v2RuntimeProjection.test.ts src/App.test.tsx
pnpm --dir apps/live-control-ui run build
uv run ruff check apps/live_control_server/services/play_run_registry.py src/application_state/play/service.py tests/test_play_run_progress.py tests/application_state/test_play_runtime_postgres.py
git diff --check
cmp Docs/Design/DESIGN-play-current-moment-cockpit.md Docs/Sources/design-agent/ACTIVE_REFERENCE/DESIGN-play-current-moment-cockpit.md
cmp Docs/Design/DESIGN-play-surface-projection.md Docs/Sources/design-agent/ACTIVE_REFERENCE/DESIGN-play-surface-projection.md
cmp Docs/Design/DESIGN-play-surface-gm-cockpit-target.md Docs/Sources/design-agent/ACTIVE_REFERENCE/DESIGN-play-surface-gm-cockpit-target.md
cmp Docs/Roadmaps/ROADMAP-con-ready.md Docs/Sources/design-agent/ACTIVE_AUTHORITY/ROADMAP-con-ready.md
git diff --name-only origin/main...HEAD
git diff --stat origin/main...HEAD
```

Must prove in addition to the original dispatch matrix:

* empty v2 progress is legal only as pre-READY stored state; a READY v2 current Beat cannot be cleared;
* native load preflights the exact authority set before any seed PUT;
* mismatched document/manifest performs zero Runtime writes;
* 409 recovery refetches Run + manifest + pinned WorkRevision and does not combine generations;
* sealed `beat_kind` and `activates`/`suppresses` participate in integrity comparison;
* opening Beat derivation honors BF1 fence/grammar admission;
* one owning-boundary helper/witness crosses load → preflight → seed CAS → reread against PostgreSQL.

---

## §8 Named successors

BF3 — Scene-centered cockpit. BF3.x / P3 — fast retrieval. P4 / Combat. BF4 — Plan composition.

---

## §9 Acceptance rubric

- [ ] One v2 Run crosses the native admission boundary into READY without Scene-first reinterpretation.
- [ ] READY has a durable `current_beat_id`.
- [ ] Seed uses exact pinned document order via BF1 grammar, not manifest array order.
- [ ] Zero-Beat v2 material fails closed.
- [ ] Beat-only v2 current position is legal.
- [ ] Scene parentage is enforced.
- [ ] Existing `run_revision` CAS owns mutation concurrency.
- [ ] Concurrent/equivalent first seeds converge without divergent Runtime.
- [ ] Decision/Option membership is validated from the sealed v2 manifest.
- [ ] Relevance is derived from selections + sealed edges and never persisted.
- [ ] Activation wins suppression.
- [ ] Suppression never removes membership/navigation eligibility.
- [ ] Historical pinned WorkRevision remains authority after a newer revision exists.
- [ ] v1 admission/progress/render semantics are unchanged.
- [ ] No second public Runtime API or persisted state contract was introduced.
- [ ] BF3 cockpit UI remains unimplemented and unclaimed.
- [ ] No Combat runtime behavior changed.
- [ ] The four canonical design/roadmap documents capture the accepted collapsible-context / central-workspace refinement.
- [ ] Those docs explicitly state that Combat is an At-a-Glance entry, not a permanent side rail.
- [ ] Canonical/mirror pairs remain byte-identical.
- [ ] No paths outside the §4 lease changed without an explicit stop/review.
- [ ] The checked-in HANDOFF is present and is the review contract.
- [ ] A READY v2 Run cannot be cleared back to empty progress.
- [ ] First seed is the final mutation after read-only v2 admission/preflight.
- [ ] 409/rebase recovery rebinds the full authority set.
- [ ] Sealed `beat_kind` and transition edges participate in native integrity comparison.

---

## 14. Stop conditions

Stop and report if implementation discovers any of the following:

* v2 READY requires a new persisted progress field;
* first seed cannot be expressed safely with existing CAS semantics;
* document order is unavailable from the exact pinned WorkRevision at admission;
* a new public endpoint is required solely for BF2;
* v1 and v2 cannot coexist without changing v1 behavior;
* native admission requires fabricating Scene-first v2 structure;
* BF2 requires meaningful cockpit layout/component work;
* design refinement requires a second projection host;
* collapse/open workspace state must become durable Run state;
* Combat ownership must change;
* a new Note schema appears necessary;
* a leased production path is owned by another active PR/worktree;
* current `main` materially contradicts this handoff.
