# HANDOFF — make post-merge state-authority sync sets machine-consumable

**Created:** 2026-08-16  
**Status:** DESIGNED — DO NOT DISPATCH until this design handoff is on `main`  
**Canonical handoff path:** `Docs/Plans/HANDOFF-DOCUMENTS-machine-readable-state-sync-set.md`  
**Conversation/workstream:** `Development Process Optimization / state-authority sync`  
**Flow / owner:** `DOCUMENTS`  
**Direction:** DESIGN → CODE → REVIEW  
**Design base:** `9b170c71a9d800157918186f8f17dc43fd993bcf`  
**Implementation base:** `PIN_AFTER_THIS_DESIGN_MERGE`  
**Suggested implementation branch:** `agent/process-machine-readable-state-sync-set`  
**PR title:** `DOCUMENTS: emit exact post-merge state sync set`

> Repository law: [`AGENTS.md`](../../AGENTS.md). Steward process: [`Docs/Process/STEWARD-CYCLE.md`](../Process/STEWARD-CYCLE.md). External PR mechanics: [`.cursor/skills/external-agent-pr-loop/SKILL.md`](../../.cursor/skills/external-agent-pr-loop/SKILL.md).

## Design evidence

The process consolidation itself is already complete on current `main`:

- PR #572 established `AGENTS.md` law for isolated lanes, review-cycle counting, and atomic state-authority sync.
- PR #573 replaced active Jumpstart process authority with `Docs/Process/STEWARD-CYCLE.md` and reduced the HANDOFF template to slice-specific material.
- PR #574 added `scripts/steward_preflight.py` for read-only lane/write-lease/base/review-cycle reconciliation.

The remaining mechanical seam is post-merge sync-set transcription.

Current evidence:

- `HANDOFF-PLAY-run-progress-cas.md` declares `State-authority sync set after merge` as prose: “this handoff completion + living Playable hoist roadmap current sequence; stable architecture only if evidence changes a claim.”
- PR #603 then performs the real post-#601 authority transaction as an exact three-document documentation PR and records the review-cycle/merge facts manually.
- `review_external_pr.py merge` already emits `merge_commit`, `merged_at`, PR URL/title, and local fast-forward diagnostics specifically for the post-merge atomic doc-sync, but does not accept a handoff or emit its state-authority sync paths.

The missing capability is therefore not semantic document automation. It is an exact, machine-readable declaration and transport of the paths the steward already decided must be synchronized.

---

## §1 Mission and merge-ready invariant

**Mission:** The steward can merge an externally reviewed PR with its checked-in handoff and receive the exact declared post-merge state-authority sync paths in the merge JSON, so merge SHA/time and sync-set paths no longer have to be recopied from prose before the semantic state update.

**Merge-ready invariant:**

> When `review_external_pr.py merge` is invoked with a checked-in handoff that declares an exact post-merge sync set, it validates that declaration **before any merge mutation**, preserves the existing merge behavior unchanged, and emits a deterministic de-duplicated list of exact repo-relative sync paths alongside the merge SHA/timestamp; it never edits those documents, infers additional authorities, converts prose aliases into guessed paths, or allows an invalid supplied handoff to proceed into a merge.

### Pre-dispatch critique

| Question | Answer |
|---|---|
| Can one invariant govern every claimed observable path? | Yes. Template/process syntax, parser behavior, and merge JSON all establish one exact declared sync-set transport contract. |
| Most likely adversarial sequence | Steward supplies `--handoff`; §2 says only “this handoff + roadmap”; tool merges first and discovers afterward that no exact paths can be recovered. Required: fail before `gh pr merge`. |
| Will §7 detect that failure? | Yes. Unit tests must prove invalid/missing exact declarations stop before the merge subprocess is called. |
| Easiest owning boundary to under-test | Backward compatibility: existing `merge <pr>` without `--handoff` must remain byte/behavior compatible apart from unrelated pre-existing nondeterminism. |
| Fact that forces stop/split | Need to author/edit semantic state documents automatically, infer authorities from filenames, change review-cycle meaning, or introduce a general workflow engine. |

---

## §2 Context, authority, and lane

Read in this order:

1. `AGENTS.md` — atomic state-authority sync law and review-cycle definition.
2. `Docs/Process/STEWARD-CYCLE.md` — dispatch/merge/re-anchor lifecycle.
3. `.cursor/skills/external-agent-pr-loop/templates/HANDOFF.template.md` — current per-slice declaration shape.
4. `scripts/review_external_pr.py` — existing `merge` behavior and JSON contract.
5. `tests/test_review_external_pr.py` — owning regression tests.
6. `Docs/Plans/HANDOFF-PLAY-run-progress-cas.md` + PR #603 — concrete proof that prose sync aliases still require manual exact-path reconstruction.

| Field | Required content |
|---|---|
| Parent authority | `AGENTS.md` atomic state-authority sync + `Docs/Process/STEWARD-CYCLE.md` |
| Base revision | replace `PIN_AFTER_THIS_DESIGN_MERGE` with the exact design-merge SHA before CODE dispatch |
| Predecessor contract | merged PRs #572–#574; current `review_external_pr.py merge` JSON |
| Exact input consumed | PR number + optional `--handoff <checked-in HANDOFF path>` |
| Named successor | optional later completeness checker for an already-authored state-sync commit/PR, only if real friction remains |
| What remains false | no semantic doc editing; no auto-generated roadmap/handoff text; no automatic state-sync PR; no generalized transaction engine |
| Explicit non-goals | product runtime; trackers/roadmaps unrelated to process; historical handoff rewrites; auto-inference of “this handoff” / “living roadmap” aliases |
| Branch / isolated checkout | `agent/process-machine-readable-state-sync-set` in isolated worktree/equivalent |
| Parallel lanes / collision hotspots | process template + Steward Cycle + `review_external_pr.py`; serialize with any active lane touching those exact paths |
| Runtime/state ownership | tests only; GitHub mutation remains the existing `gh pr merge` path and must not occur on validation failure |
| State-authority sync set after merge | `Docs/Plans/HANDOFF-DOCUMENTS-machine-readable-state-sync-set.md` |

### Exact declaration syntax

The HANDOFF template's existing §2 row remains the authority; do not add a second sync-set section.

Its value must become mechanically explicit:

```markdown
| State-authority sync set after merge | `Docs/Plans/HANDOFF-FOO.md`; `Docs/Roadmaps/ROADMAP-foo.md`; `Docs/Plans/PR-TRACKER-foo.md` |
```

Rules:

- values are exact repo-relative paths in backticks;
- one or more paths are required for an active implementation handoff;
- preserve declaration order or sort deterministically, but document and test the chosen rule;
- duplicates collapse deterministically;
- prose aliases such as `this handoff`, `living roadmap`, `tracker`, or `handoff-only` are not machine-readable substitutes;
- conditional stable authorities such as architecture are **not** listed as mandatory sync paths merely because they must be re-read; if evidence changes a stable claim, that is a steward stop/re-anchor decision, not a routine inferred sync.

---

## §3 Observable paths and adversarial sequences

| Path | Current behavior | Required behavior | Same §1 invariant? | Owning boundary |
|---|---|---|---:|---|
| `merge <pr>` without `--handoff` | Existing merge/ff/stash JSON flow | Unchanged | Yes | `review_external_pr.py` CLI/merge tests |
| `merge <pr> --handoff valid.md` | Unsupported | Pre-validate exact sync set, merge normally, emit exact paths | Yes | handoff parser + merge command |
| `merge <pr> --handoff invalid.md` | Unsupported | Fail before any GitHub merge mutation | Yes | parser/CLI ordering test |
| already-merged PR + valid handoff | Existing capture-state behavior without handoff | Preserve idempotent capture state and emit declared sync paths | Yes | merge capture-state path |

Adversarial sequences:

| Sequence | Required safe outcome | Owning §7 proof |
|---|---|---|
| invalid handoff → merge invocation | parse/validation error; `gh pr merge` never called | unit test with merge subprocess spy |
| valid handoff with duplicate paths → merge | one deterministic de-duplicated output list | parser/unit test |
| no `--handoff` → merge | current behavior remains unchanged | regression test |
| PR already merged → rerun with valid handoff | no second merge attempt; capture-state JSON includes same exact sync set | regression test |

---

## §4 Files in scope — write lease

| Action | Path | Purpose |
|---|---|---|
| Modify | `.cursor/skills/external-agent-pr-loop/templates/HANDOFF.template.md` | Require exact backticked repo-relative post-merge sync paths in the existing §2 field. |
| Modify | `Docs/Process/STEWARD-CYCLE.md` | Make exact path declaration part of dispatch readiness and explain that the merge helper transports, but never authors, the semantic sync. |
| Modify | `scripts/review_external_pr.py` | Add optional `merge --handoff`, pre-validate/extract the exact sync set, and emit it in merge/capture-state JSON. |
| Modify | `tests/test_review_external_pr.py` | Prove syntax extraction, pre-mutation failure, backward compatibility, de-duplication, and already-merged behavior. |

**Bounded discovery exception:** Not applicable. Any additional path requires a stop/re-brief.

---

## §5 Explicitly out of scope / collision boundary

| Path / capability | Why this slice must not touch or claim it |
|---|---|
| `AGENTS.md` | Foundational atomic-sync law is already correct; this slice is mechanics beneath it. |
| `scripts/steward_preflight.py` | Lane preflight is already a separate capability; do not expand this slice into another preflight redesign. |
| `tests/test_steward_preflight.py` | No `steward_preflight` behavior changes are required. |
| `Backlog.md` | PR #605 already owns backlog authority cleanup. |
| Campaign / Play / Threat roadmaps or trackers | Active domain sequencing is unrelated and may be owned by parallel PRs. |
| Any semantic state-sync document mutation | The human/steward remains responsible for the actual state transition content. |

---

## §6 Implementation contract

### Parser contract

Input: parsed HANDOFF §2 table.

Target row label:

```text
State-authority sync set after merge
```

Output:

```text
list[str] exact repo-relative paths
```

Required behavior:

- extract only explicit code-span paths from the target row;
- reject missing row, empty set, placeholder text, or prose-only aliases when `--handoff` is supplied;
- reject obvious absolute paths / parent traversal;
- deterministically de-duplicate;
- do not inspect filenames elsewhere in the handoff to infer missing members;
- parsing must happen before any merge mutation.

### Merge CLI contract

New optional argument:

```bash
uv run python scripts/review_external_pr.py merge <PR> \
  --handoff Docs/Plans/HANDOFF-<FLOW>-<slug>.md
```

Existing invocation remains valid:

```bash
uv run python scripts/review_external_pr.py merge <PR>
```

When `--handoff` is supplied and valid, both normal merge and already-merged capture-state JSON include:

```json
{
  "state_authority_sync_set": [
    "Docs/Plans/HANDOFF-...md",
    "Docs/Roadmaps/ROADMAP-...md"
  ]
}
```

The helper must **not**:

- edit any listed file;
- create a branch/PR for the sync;
- generate semantic replacement text;
- decide whether architecture changed;
- infer omitted authorities;
- dispatch the successor.

The steward uses the emitted merge metadata + exact paths to perform the guarded semantic transaction already required by `AGENTS.md`.

---

## §7 Evidence required to merge

| Guarantee / invariant clause | Owning boundary | Evidence | Expected result | Stop condition |
|---|---|---|---|---|
| Exact §2 syntax parses deterministically | parser | focused unit tests | exact ordered/de-duplicated path list | prose/placeholder accepted as path authority |
| Invalid supplied handoff cannot merge | merge ordering | subprocess-spy unit test | parser fails before `gh pr merge` | any mutation happens first |
| Existing no-handoff merge is unchanged | CLI regression | existing + new merge tests | prior JSON/merge behavior preserved | new handoff requirement becomes mandatory globally |
| Valid handoff paths reach merge JSON | merge output | unit test | `state_authority_sync_set` exact | missing/reformatted paths |
| Already-merged capture remains idempotent | capture-state path | unit test | no second merge; exact sync set emitted | duplicate merge attempt |
| Docs/template describe one authority | document inspection | exact diff review | no second process authority introduced | duplicate process law |

Exact verification:

```bash
uv run pytest -q tests/test_review_external_pr.py
uv run python scripts/review_external_pr.py merge --help
uv run python scripts/review_external_pr.py merge 0 --handoff /definitely/missing.md  # must fail before any merge attempt; use a safe test/mocked path rather than a live PR if CLI integration is exercised
git diff --check
git diff --name-only <base>...HEAD
```

The third command is illustrative of ordering, not permission to target a real PR. Unit tests are the owning proof for mutation safety.

---

## §8 Required review handback

Record:

1. `Review Cycle <N>` and exact PR/head SHA.
2. Exact implementation base and actual changed paths versus §4.
3. Parser contract disposition, including invalid/prose-only declarations.
4. Proof that validation precedes every merge mutation path.
5. Proof that `merge <pr>` without `--handoff` is backward compatible.
6. Proof that already-merged capture state remains idempotent.
7. Exact `tests/test_review_external_pr.py` result and provenance.
8. Any path outside §4 (`none` or stop report).
9. Confirmation that semantic state-document editing remains manual/steward-owned.
10. Named successor still false.

---

## §9 Acceptance rubric

- [ ] One exact post-merge sync-set transport capability is delivered.
- [ ] The existing HANDOFF §2 field, not a second authority, becomes machine-consumable.
- [ ] Supplying an invalid handoff stops before merge mutation.
- [ ] Existing no-handoff merge behavior remains available and unchanged.
- [ ] Normal merge and already-merged capture state emit exact declared paths when `--handoff` is supplied.
- [ ] No semantic state document is automatically edited or inferred.
- [ ] Only §4 paths changed.
- [ ] Focused tests and `git diff --check` pass.
- [ ] Post-merge state-authority sync for this implementation is limited to marking this handoff complete unless evidence proves another process authority became stale.

## Stop conditions

Stop rather than expand if implementation requires:

- automatic semantic edits to handoff/roadmap/tracker/status documents;
- filename heuristics to guess omitted sync authorities;
- a new process authority rather than updating Steward/template mechanics;
- changes to `steward_preflight.py` to make the merge capability work;
- a generalized workflow/transaction framework;
- product-domain roadmap/tracker edits;
- an additional write path outside §4.

Report the exact consequence and propose a successor slice if any appears.
