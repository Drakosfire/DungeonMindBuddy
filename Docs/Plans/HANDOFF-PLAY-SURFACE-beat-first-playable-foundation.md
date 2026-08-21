---
pr_body_template: |
  ## Handoff pointer
  - Workstream: PLAY-SURFACE / Beat-first Playable foundation (BF1)
  - Flow: PLAY-SURFACE
  - Direction: DESIGN → CODE → REVIEW
  - Handoff: Docs/Plans/HANDOFF-PLAY-SURFACE-beat-first-playable-foundation.md
  - Design contract: Docs/Design/DESIGN-play-current-moment-cockpit.md
  - Branch / PR: agent/play-surface-beat-first-playable-foundation / `PLAY-SURFACE: beat-first Playable grammar and manifest foundation`

  ## Verification pointer
  - Dispatch base: re-anchor current `main` and record the exact SHA in the PR body before editing
  - Predecessor: merged current-moment cockpit design PR
  - Changed paths: HANDOFF §4 only
  - Verification: HANDOFF §7 + exact-head formal review
---

# HANDOFF — Beat-first Playable grammar and manifest foundation (BF1)

**Created:** 2026-08-21  
**Status:** DESIGNED — dispatchable only after the current-moment cockpit design PR merges and `main` is re-anchored.  
**Canonical handoff path:** `Docs/Plans/HANDOFF-PLAY-SURFACE-beat-first-playable-foundation.md`  
**Workstream:** `PLAY-SURFACE / Beat-first Playable foundation (BF1)`  
**Flow / owner:** `PLAY-SURFACE`  
**Direction:** DESIGN → CODE → REVIEW  
**Suggested branch:** `agent/play-surface-beat-first-playable-foundation`  
**PR title:** `PLAY-SURFACE: beat-first Playable grammar and manifest foundation`

> Operating law: `AGENTS.md`.  
> Design contract: `Docs/Design/DESIGN-play-current-moment-cockpit.md` (§1 containment, §2 serialization, §3 manifest).  
> Architecture: `Docs/Design/ARCHITECTURE-playable-material-and-runtime.md`.  
> Living sequence: `Docs/Roadmaps/ROADMAP-playable-hoist-dungeonmind-kernel.md`.

---

## 0. Re-anchor and predecessor truth

Before dispatch:

1. fetch current `main` and record its exact SHA in the PR body;
2. confirm the current-moment cockpit design PR merged and
   `DESIGN-play-current-moment-cockpit.md` is on `main` unchanged, or amend
   this handoff to the reviewed head;
3. inspect active PRs/worktrees for overlapping writes to the paths in §4;
4. verify Lane B / Combat collision status has not changed the boundary.

The design contract is the authority for grammar and manifest semantics. Where
this handoff and the contract disagree, the contract wins and the handoff is
amended — not the other way around.

---

## 1. Mission and merge-ready invariant

### Mission

Deliver the Beat-first Playable wire foundation: the v2 grammar
(parse/validate/serialize), the structure index over v2, and the v2 sealed Run
reference manifest — so that every later cockpit, runtime-position, and
authoring slice builds on one reviewed, integrity-checked structural truth.

This slice contains **no cockpit UI, no Runtime current-position change, no
relevance projection, and no migration tooling**.

### Merge-ready invariant

> **A Runbook authored with `dmb-playable-element:v2` round-trips through import, TipTap edit, save, and committed reload with stable Beat/Scene/Decision/Option identity; validation fails closed on illegal containment, duplicate IDs, bad transition edges, and mixed grammar versions; and a Run created against a v2 revision seals a `dmb_play_run_reference_manifest_v2` whose membership, parentage, and transition edges replay without consulting current workspace state. Existing v1 documents, manifests, and Runs behave exactly as before.**

### What may be true after merge

```text
true:
  v2 grammar is parseable, validatable, and serializable
  v2 structure index derives Beat/Scene/Decision/Option membership
  v2 manifest seals and replays identity + parentage + transition edges
  v1 and v2 coexist, each read by its own reader
```

### What must remain false after merge

```text
false:
  any cockpit/table UI consumes v2
  Runtime current-position semantics changed (still v1 P2B2 behavior)
  relevance derivation exists at runtime
  Plan has Beat-first authoring controls
  any v1 document or Run was migrated
  P3B/P4 dispatchability changed
```

---

## 2. Capability contract

### Included

1. **v2 grammar parse/validate/serialize** per design contract §2:
   - `beat` on H2; `scene` on H3 inside the nearest preceding Beat;
     `choice` on H4 inside the nearest preceding Beat with optional `scene`
     association into the same Beat; `option` as a marked list item inside the
     current Decision;
   - optional `beat_kind=spine|optional|interrupt` on `beat`;
   - `activates` / `suppresses` edge attributes on `option`, targeting IDs in
     the same document;
   - heading level is part of the grammar; misplaced directives fail
     validation;
   - literal fenced-code interiors are never parsed (v1 `~~~` and
     variable-length-backtick treatment carries forward);
   - unmarked headings/prose remain non-semantic; the D2 termination rule for
     preceding playable body slices carries forward.
2. **Fail-closed validation** per design contract §2.5: duplicate IDs, Scene
   outside a Beat or nested under a Scene, Decision outside a Beat, Option
   outside a Decision, cross-Beat or unknown Scene association, edges to
   unknown IDs, unknown kind/version, mixed v1+v2 structural directives in one
   document.
3. **v2 structure index**: the smallest read-only derived index addressing
   Beats/Scenes/Decisions/Options by stable ID and document order — same
   posture as merged P1B (no new grammar, save policy, persistence, or editor
   mutation).
4. **v2 manifest seal/replay** per design contract §3:
   `dmb_play_run_reference_manifest_v2` with beats (id, kind), scenes (id,
   parent beat), choices (id, parent beat, optional scene association),
   options (id, parent choice), and edges (option, effect, target kind/id);
   seal derives from the exact still-current bound revision/SHA and fails
   closed if the workspace has advanced; replay uses the immutable sidecar
   only.
5. **Coexistence**: v1 documents/manifests/Runs are untouched and keep v1
   semantics; unknown schema versions fail closed.

### Prohibited

- cockpit/table UI of any kind;
- Runtime current-position, selection, relevance, or progress changes;
- v1→v2 conversion/migration tooling;
- rebase behavior changes;
- Plan authoring controls;
- Combat anything;
- a second Playable database;
- a general condition/rules engine or expression language.

---

## 3. Design decisions already frozen (do not reopen in code)

- Decision is the product word; `choice`/`option` remain the wire kinds.
- Consequences attach to Beats and Options only.
- Transition vocabulary is exactly `activates` / `suppresses`.
- Manifest stores identity/membership/parentage/edges; prose, titles, and
  rendering order come from the pinned revision bytes.
- All sealed edges are immutable for the Run's revision.

If implementation discovers these are unimplementable as written, stop and
hand back to stewardship with the concrete blocker; do not improvise a new
containment model in code.

---

## 4. Exclusive write lease

Expected production write lease (exact paths confirmed at dispatch re-anchor):

| Area | Paths (expected) |
|---|---|
| Playable grammar | `apps/live-control-ui/src/**/playable*` v2 grammar module(s); semantic Markdown directive parse/serialize |
| Structure index | v2 membership derivation alongside the merged P1B index |
| Manifest service/routes | `apps/live_control_server/services/play_run_reference_manifest*` v2 schema + seal/replay; route admission |
| Tests | focused unit/service/route tests for grammar, validation, index, seal, replay, coexistence |

No changes to: Runtime progress services, Play surface UI, Plan surface UI,
Combat, migration tooling, or documentation authorities (except the roadmap
ledger row required by the living-roadmap contract).

---

## 5. Verification

1. Focused backend tests: v2 seal/replay, fail-closed validation matrix,
   coexistence with v1 fixtures, workspace-advanced seal refusal.
2. Focused frontend tests: v2 parse/serialize round-trip, stable identity
   through rename, fence-literal treatment, D2 termination rule.
3. `git diff --check`; changed paths inside §4.
4. Living-roadmap disposition row naming the implementation/evidence head.

## 6. Review contract

One exact distinct head receives one formal reviewer judgment
(PASS / REQUEST-CHANGES-equivalent via COMMENT when GitHub blocks the formal
states on the same account). Any repair commit creates a new head and another
review cycle.

The reviewer must independently verify: the design contract was implemented as
frozen; nothing from §2-Prohibited shipped; v1 behavior is byte-stable; and
the roadmap ledger row names the evidence head.

---

## 7. Post-merge successor posture

After BF1 merges, re-anchor and let evidence choose between BF2 (Runtime
current-position v2 + relevance derivation) and BF4 (Plan Beat-first authoring
composition). BF3 (cockpit projection) requires BF2. Do not pre-authorize the
second slice here.
