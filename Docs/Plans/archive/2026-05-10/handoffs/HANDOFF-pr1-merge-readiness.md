# HANDOFF: PR #1 — complete merge playbook

**Date:** 2026-05-09 (updated with full rebase + critique + success metrics)  
**PR:** [Drakosfire/DungeonMindBuddy#1](https://github.com/Drakosfire/DungeonMindBuddy/pull/1)  
**Branch:** `codex/implement-dynamic-lexical-artifact-generation`  
**Base (GitHub):** `main`  
**Status:** Do not merge until all sections under **Success measurements** pass.

This document is the single instruction set for the agent (or human) closing PR #1. Execute in order unless a step explicitly allows parallel work.

---

## 1. Context you must not skip

### 1.1 Why the PR looks “small” on GitHub but is dangerous to merge

- **Merge-base** between the PR branch and current `main` is commit `258c08b` (*Align world/campaign corpus contracts and extend breadcrumb retrieval harness*).
- **`main` has moved forward** with commits that include:
  - `731ca52` — lexical retrieval plans, corpus hubs, eval harnesses, **token resolution** package and tests
  - `507318f`, `f8eba50`, `c132576`, `a02f16f` — **Plans directory archival** (many `HANDOFF-*` / `REPORT-*` moved under `Docs/Plans/archive/2026-05-09/…`)

If you merge the PR branch **without rebasing**, Git will replay the PR’s commits on top of current `main`. Because the PR still contains the *old* tree (files that `main` later deleted or moved), the merge can **reintroduce hundreds of deleted/moved files** at their old paths (for example root-level `Docs/Plans/HANDOFF-*.md`, a root `Docs/Plans/CHECKLIST-dynamic-lexical-retrieval-rollout.md`, etc.).

**Conclusion:** Rebase onto current `main` is mandatory before merge, not optional cleanup.

### 1.2 What PR #1 is supposed to deliver (scope)

- **`src/lexicon_phase_b/`** — deterministic **route-equivalence manifest** builder from `_npc_registry.json`, plus **`RouteEquivalenceRecord`** schema (`schemas.py`).
- **Tests** proving slug/route-id behavior for **file-shaped** and **directory-shaped** `hub_path` values, kind inference where generalized, and contract defaults.

Anything beyond that (retriever wiring, Phase C+, new gold) is **out of scope** for this PR.

---

## 2. Full critique (what was wrong and what still matters)

### 2.1 Original correctness issue (largely addressed on PR head)

- **Bug pattern:** Deriving the route slug from `Path(hub_path).parent.name` (or equivalent) so that a **directory-shaped** path `…/NPCs/<entity>/` produced slug `npcs` instead of the entity folder name.
- **Fix on branch:** `_extract_entity_slug` in `src/lexicon_phase_b/route_equivalence_manifest.py` normalizes path parts, treats a trailing file segment (e.g. `README.md`) as “use parent folder for slug,” and if the tail is a known bucket name (`npcs`, `locations`, …) uses the segment before it.

**Success measurement:** Tests assert identical `from_route_id` / `to_route_id` for the same logical hub given **file** vs **directory** trailing form (see §6).

### 2.2 Blocker: branch is rooted before `main`; merge without rebase revives deleted layout

See §1.1.

**Success measurement:** After rebase, `git diff main...HEAD --stat` shows **only** intentional PR files (lexicon package, lexicon tests, optional report/docs touch). No mass re-add of `Docs/Plans/HANDOFF-*` at repo root, no resurrection of deleted top-level review files unless deliberately reverted by project decision.

### 2.3 Blocker: three new test files **collide by basename** with existing tests on `main`

On **current `main`**, these paths already exist and test **`src.token_resolution`** and benchmark lexicon seeds:

| Path on `main` | Purpose |
|----------------|---------|
| `tests/test_token_resolution_resolver.py` | `resolve_for_query`, explain diff, Packet C |
| `tests/test_token_resolution_contracts.py` | Lexicon artifact / build_lexicon contracts |
| `tests/test_benchmark_lexicon_seeds.py` | `BenchmarkLexiconSeeds`, committed seed JSON |

The PR branch **replaced** those paths with tests that import **`src.lexicon_phase_b.route_equivalence_manifest`**. After a rebase, Git will report **modify/modify conflicts**. You must **not** accept the PR version as a wholesale replacement of `main`’s files — that would delete the token-resolution test suite.

**Resolution (mandatory naming):** Move PR-only tests under `tests/lexicon_phase_b/` with **new basenames**, for example:

| Remove from repo root (after rebase) | Add under `tests/lexicon_phase_b/` |
|--------------------------------------|-------------------------------------|
| `tests/test_token_resolution_resolver.py` (PR’s lexicon slug tests) | `tests/lexicon_phase_b/test_route_id_path_shapes.py` (or `test_route_equivalence_path_shapes.py`) |
| `tests/test_token_resolution_contracts.py` (PR’s `RouteEquivalenceRecord` defaults) | `tests/lexicon_phase_b/test_route_equivalence_record_defaults.py` |
| `tests/test_benchmark_lexicon_seeds.py` (PR’s location kind seed test) | `tests/lexicon_phase_b/test_route_equivalence_entity_kind_inference.py` |

Keep **`main`’s** three original files **unchanged** in behavior and path (resolve conflicts by taking `main`’s versions for those paths, then **add** the new lexicon files as above).

**Success measurement:**

- `uv run pytest tests/test_token_resolution_resolver.py tests/test_token_resolution_contracts.py tests/test_benchmark_lexicon_seeds.py -q` — all pass (same as pre-PR `main` surface).
- `uv run pytest tests/lexicon_phase_b/ -q` — all pass including merged `test_route_equivalence_manifest.py` plus the three renamed modules.

### 2.4 Blocker: `scripts/audit_world_campaign_alignment.py` missing on old PR tip

The PR’s own report noted the audit script was absent on the **old** branch. On **current `main`** the script exists: `scripts/audit_world_campaign_alignment.py`.

**Success measurement:** After rebase, `uv run python scripts/audit_world_campaign_alignment.py` exits **0** with no hierarchy violations attributable to this PR’s corpus edits (if the PR does not touch corpus, expect unchanged behavior vs `main`; if it touches gold/corpus, fix per project checklist).

### 2.5 Semantic tension: `source_type` vs generalized `entity_kind`

`RouteEquivalenceRecord` uses `source_type: Literal["npc_registry"]` while `entity_kind` can be `location`, `faction`, etc. Data is still loaded from `_npc_registry.json`, but the literal reads as “NPC-only.”

**Required decision (pick one and document in PR body + optionally in `schemas.py` docstring):**

- **A — Keep literal, document:** State that `npc_registry` means *registry file contract* (historical filename `_npc_registry.json`), not “entity is an NPC.”
- **B — Generalize:** Widen `source_type` (e.g. `campaign_hub_registry`) and bump `schema_version` with a one-line changelog in the PR description.

**Success measurement:** PR description states the choice; tests or schema comments align; no reviewer confusion left implicit.

### 2.6 Policy gap: `entity_kind == "unknown"`

If no `/npcs/`, `/locations/`, etc. segment matches, kind is `"unknown"` and `record_id` can become `route-eq:…:unknown:…`. There is no documented rule: allow vs filter vs downgrade confidence.

**Required decision:**

- Either **add tests** for the allowed `unknown` shape and set `confidence` appropriately, or **filter** (`_record_to_edge` returns `None`) or **raise** when kind would be `unknown`.

**Success measurement:** Chosen policy is tested; no silent `unknown` edges with `confidence="high"` unless explicitly intended and documented.

### 2.7 Schema version bump

PR evolved `schema_version` default (e.g. `0.1.0` → `0.2.0`) with generalized kinds. PR description must mention bump and whether any consumer exists (if none, say “pre-consumer, contract pin only”).

### 2.8 Slug helper robustness (follow-up, optional for merge if documented)

`_extract_entity_slug` handles “tail is bucket name → use `parts[-2]`.” Deeper nesting (e.g. `…/NPCs/slug/Variants/`) could mis-slug. Optional hardening: test for one extra nesting shape or document “unsupported path shapes raise / are rejected.”

---

## 3. Rebase: exact procedure and conflict resolution

### 3.1 Preconditions

```bash
cd /path/to/DungeonMindBuddy
git fetch origin
git checkout codex/implement-dynamic-lexical-artifact-generation
git pull --ff-only origin codex/implement-dynamic-lexical-artifact-generation   # if you track the remote branch
```

### 3.2 Rebase onto current main

```bash
git rebase origin/main
```

### 3.3 Expected conflict classes and how to resolve them

**Class A — `Docs/Plans/` and archive files**

- **`main`** deleted or moved many files; **PR branch** may still add them at old paths.
- **Rule:** Prefer **`main`**’s tree for anything under `Docs/Plans/` **unless** you intentionally add a small delta (for example updating `REPORT-pr1-merge-readiness.md` or linking from `Docs/Plans/README.md`).
- For each conflict: if the file on `main` is **gone** (moved to `Docs/Plans/archive/…`), **do not** restore the old path; take `main` (delete) or move your edit into the archive path the project uses.

**Class B — `tests/test_token_resolution_*.py` and `tests/test_benchmark_lexicon_seeds.py`**

- **Rule:** **`git checkout --ours`** these paths during rebase **if** “ours” is the rebased commit (i.e. **`main`**’s version) — verify with `git status` and `git show :2:path` / `:3:path` if unsure. In rebase terminology: **upstream = `main` = first parent** for conflicts; use the version that matches **`main`**’s token-resolution tests.
- After resolving, **create** the three new files under `tests/lexicon_phase_b/` with the names in §2.3, pasting/adapting the PR’s test **bodies** from the conflicting “theirs” side (lexicon tests), then `git add` the new files.

**Class C — `src/lexicon_phase_b/`**

- Usually **no conflict** if only the PR touched these. If conflict: merge manually preserving `_extract_entity_slug`, `_KIND_SEGMENTS` triples, `RouteEquivalenceRecord` fields, and `build_route_equivalence_manifest` behavior.

**Class D — `corpus/`, `evals/`, `src/token_resolution/`**

- If the PR never intended to change these, take **`main`**. If the PR added lexicon-only code and `main` already has `src/token_resolution/`, ensure you do **not** delete or revert `main`’s package.

### 3.4 Continue or abort

```bash
# After fixing each commit’s conflicts:
git add -A
git rebase --continue

# If the replay is wrong beyond repair:
git rebase --abort
```

### 3.5 Alternative: squash then rebase (acceptable)

If commit-by-commit replay is noisy:

```bash
git fetch origin
git checkout codex/implement-dynamic-lexical-artifact-generation
git reset --soft origin/main
# Re-apply a single commit with only the intended files:
git add src/lexicon_phase_b/ tests/lexicon_phase_b/ …
git commit -m "feat(lexicon_phase_b): route equivalence manifest + tests"
```

Then force-push (only with coordination). This avoids replaying obsolete doc commits entirely.

### 3.6 Push

```bash
git push --force-with-lease origin codex/implement-dynamic-lexical-artifact-generation
```

---

## 4. File-level checklist (after rebase)

| Action | Path(s) |
|--------|---------|
| Keep | `src/lexicon_phase_b/__init__.py` |
| Keep / merge | `src/lexicon_phase_b/route_equivalence_manifest.py` |
| Keep / merge | `src/lexicon_phase_b/schemas.py` |
| Keep | `tests/lexicon_phase_b/test_route_equivalence_manifest.py` (merge with any new tests in same dir) |
| Add (from PR content, new names) | `tests/lexicon_phase_b/test_route_id_path_shapes.py` |
| Add | `tests/lexicon_phase_b/test_route_equivalence_record_defaults.py` |
| Add | `tests/lexicon_phase_b/test_route_equivalence_entity_kind_inference.py` |
| Preserve from `main` unchanged | `tests/test_token_resolution_resolver.py`, `tests/test_token_resolution_contracts.py`, `tests/test_benchmark_lexicon_seeds.py` |
| Update if still present | `Docs/Plans/archive/2026-05-09/reports/REPORT-pr1-merge-readiness.md` — must reflect post-rebase commands and **merge verdict** |
| Optional | `Docs/Plans/README.md` — link to this handoff if not already |

**Do not** leave duplicate or wrong-pathed copies of the three colliding test names at `tests/` root.

---

## 5. Implementation follow-ups (if not already satisfied post-rebase)

1. **`source_type` vs `entity_kind`:** Implement decision §2.5 in `src/lexicon_phase_b/schemas.py` + PR description.
2. **`unknown` kind policy:** Implement §2.6 in `route_equivalence_manifest.py` + tests.
3. **PR description:** Replace stale “Phase B only” text with: slug fix, kind generalization, `schema_version`, test layout (`tests/lexicon_phase_b/`), audit result, rebase note.

---

## 6. Success measurements (merge gate — all must pass)

Use a clean worktree at **`HEAD` = rebased PR branch**.

### 6.1 Diff scope (sanity)

```bash
git fetch origin
git diff origin/main...HEAD --stat
```

**Pass:** Stat is limited to lexicon source, lexicon tests, and at most small intentional doc/report edits. **Fail:** Hundreds of `Docs/Plans/` files or deleted corpus reappearing.

### 6.2 Lexicon unit tests

```bash
uv run pytest tests/lexicon_phase_b/ -q
```

**Pass:** Non-zero tests collected; **all passed**; exit code 0.

### 6.3 Token-resolution and benchmark seed tests preserved

```bash
uv run pytest tests/test_token_resolution_resolver.py \
               tests/test_token_resolution_contracts.py \
               tests/test_benchmark_lexicon_seeds.py -q
```

**Pass:** All passed; exit code 0.

### 6.4 Regression spot-check (recommended)

```bash
uv run pytest tests/test_token_resolution_derive.py -q   # if present on main
uv run pytest tests/ -q --ignore=tests/evals --ignore=…   # optional; scope to team policy
```

**Pass:** No new failures vs `main` baseline for the chosen scope.

### 6.5 World/campaign alignment audit

```bash
uv run python scripts/audit_world_campaign_alignment.py
```

**Pass:** Exit code **0**; no unfixed violations required by current project gates.

### 6.6 Evidence in PR

**Pass:** PR description or a pinned comment lists exact commands from §6.2–§6.5 and **PASS** (or acceptable skip with substitute command documented). Optional: attach or link updated `REPORT-pr1-merge-readiness.md`.

### 6.7 Final merge verdict

**Merge-ready** only when §6.1–§6.5 and policy decisions §2.5–§2.6 are satisfied and §6.6 is done.

---

## 7. Required report (after execution)

Update or create:

- `Docs/Plans/archive/2026-05-09/reports/REPORT-pr1-merge-readiness.md`

Must include:

1. Rebase strategy used (commit-by-commit vs squash) and final `HEAD` OID.
2. `git diff origin/main...HEAD --stat` excerpt.
3. Exact command lines and exit codes for §6.2–§6.5.
4. One **before/after** route-id example (directory vs file path) if code changed post-review.
5. Explicit **merge verdict:** `ready` | `not ready` and why.

---

## 8. Out of scope for this PR

- Retriever wiring, lexical artifact promotion, benchmark canvas changes.
- Phase A gold edits unless audit failure requires them (then separate commit with checklist update).
- Broad refactors of `src/token_resolution/` unrelated to merge conflict resolution.

---

## 9. Quick reference — PR and plan links

- PR: https://github.com/Drakosfire/DungeonMindBuddy/pull/1  
- Super-plan: `Docs/Plans/PLAN-split-corpus-retrieval-to-autonomous-demo.md`  
- Operational checklist: `Docs/Plans/CHECKLIST-dynamic-lexical-retrieval-rollout.md` (path on `main` under archive if moved — resolve via repo search if needed)
