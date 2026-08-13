# HANDOFF — Steward preflight snapshot

**Created:** 2026-08-12  
**Status:** ACTIVE — one implementation capability  
**Canonical handoff path:** `Docs/Plans/HANDOFF-DOCUMENTS-steward-preflight.md`  
**Conversation/workstream:** `DungeonBuddy development-process optimization`  
**Flow / owner:** `DOCUMENTS`  
**Direction:** DESIGN → CODE → REVIEW  
**Base revision:** `964a360286d1c2e4444787002c00b40257dae34f`  
**PR title:** `DOCUMENTS: add steward preflight snapshot`

> Repository law: [`AGENTS.md`](../../AGENTS.md). Steward process: [`Docs/Process/STEWARD-CYCLE.md`](../../Docs/Process/STEWARD-CYCLE.md). External PR mechanics: [`.cursor/skills/external-agent-pr-loop/SKILL.md`](../../.cursor/skills/external-agent-pr-loop/SKILL.md).

## §1 Mission and merge-ready invariant

**Mission:** A steward can run one read-only command before dispatch or review and receive a machine-readable snapshot of the candidate handoff's write lease, current worktrees, active handoff/PR overlaps, base drift, runtime-state declaration, and explicitly labeled review-cycle judgments so mechanical reconciliation no longer depends on copy/paste.

**Merge-ready invariant:** `scripts/steward_preflight.py` reports repository process state without mutating Git/GitHub, never invents ownership when data is unavailable, blocks on concrete write-lease overlap or an unparseable/empty candidate lease, warns rather than blocks on non-conflicting base drift or missing optional remote data, counts review cycles only from explicit `Review Cycle N` formal-review bodies bound to distinct head SHAs, and leaves slice decomposition/ownership-transfer decisions to the steward.

### Pre-dispatch critique

| Question | Answer |
|---|---|
| Can one invariant govern every claimed observable path? | Yes — all behavior produces one truthful preflight snapshot; it does not perform workflow mutations. |
| Most likely adversarial sequence | Candidate §4 overlaps an active PR but not an active handoff → script checks only handoffs → false `pass`. Or multiple review comments on one head are counted as multiple cycles. |
| Will §7 actually detect that failure? | Yes — fixtures cover handoff-only, PR-only, wildcard lease overlap, same-branch exclusion, distinct-head review counting, and unavailable GitHub data. |
| Easiest owning boundary to under-test | GitHub/open-PR normalization because `gh` output is external and optional. |
| Fact that forces stop/split | Need to mutate branches/worktrees/handoffs or automatically decide ownership transfer; that is a separate capability. |

## §2 Context, authority, and lane

| Field | Required content |
|---|---|
| Parent authority | `AGENTS.md` parallel-lane/write-lease/review-cycle law; `Docs/Process/STEWARD-CYCLE.md` lane allocation and learning rules |
| Base revision | `964a360286d1c2e4444787002c00b40257dae34f` |
| Predecessor contract | PR #572 foundational law + PR #573 Steward Cycle/template layering |
| Exact input consumed | Checked-in HANDOFF markdown, local Git metadata/worktrees, optional `gh` open-PR/review JSON |
| Named successor | Optional handoff initialization/state-sync helpers if repetition remains painful after dogfood |
| What remains false | Tool does not author a handoff, create a worktree/branch, transfer a lease, post reviews, merge, or update state authorities |
| Explicit non-goals | Product/runtime code; Git/GitHub mutation; semantic capability decomposition; auto-resolving collisions |
| Branch / isolated checkout | `agent/process-steward-preflight` |
| Parallel lanes / collision hotspots | Open product PRs may continue; this lane leases only the files in §4. `Docs/Process/STEWARD-CYCLE.md` is a process hotspot but no other process lane is active after #573. |
| Runtime/state ownership | Not applicable — read-only CLI over repo metadata; tests use temporary fixtures/mocks |
| State-authority sync set after merge | This handoff only; Steward Cycle is implementation/reference content in the PR itself |

## §3 Observable paths and adversarial sequences

| Path | Current behavior | Required behavior | Same §1 invariant? | Owning boundary |
|---|---|---|---:|---|
| Candidate handoff has clean disjoint lease | Steward manually compares files/branches | JSON `pass` with lease + observed lanes | Yes | CLI aggregation |
| Candidate overlaps active handoff | Manual detection | JSON `block` naming both paths/owner | Yes | lease comparison |
| Candidate overlaps open PR with no active handoff | Easy to miss | JSON `block` naming PR/branch | Yes | GitHub normalization + lease comparison |
| Candidate branch already owns its PR | Could self-conflict | Same branch is excluded from collision set | Yes | lane identity |
| `main` advanced from candidate base | Could be harmless independent lane | `warn`, include ancestor/equality facts; do not invent invalidation | Yes | Git base check |
| GitHub/`gh` unavailable | Tool could fail entirely or claim no PRs | truthful warning + local-only snapshot; no false claim of complete remote scan | Yes | CLI dependency boundary |
| Reviews contain repeated comments/same-head judgments | Naive count inflates cycles | count one explicit formal cycle per distinct head SHA; expose duplicates/anomalies | Yes | review parser |

| Sequence | Required safe outcome | Owning §7 proof |
|---|---|---|
| Active PR writes `shared.ts` → candidate leases `shared.ts` → preflight | `block`, even when no active handoff mentions it | PR-overlap test |
| Review Cycle 1 body on head A → another Review Cycle 1 comment on A → Review Cycle 2 body on head B | count 2 distinct-head formal judgments, report duplicate same-head entry | review-cycle test |
| `gh` command unavailable → local handoff overlap exists | still `block` from local evidence + remote-unavailable warning | dependency-failure test |

## §4 Files in scope — write lease

| Action | Path | Purpose |
|---|---|---|
| Create | `scripts/steward_preflight.py` | Read-only aggregation/parsing/CLI. |
| Create | `tests/test_steward_preflight.py` | Owning proof for lease, Git/worktree, PR, and review-cycle semantics. |
| Modify | `Docs/Process/STEWARD-CYCLE.md` | Add the preflight command as an optional mechanical aid before dispatch/review. |
| Create | `Docs/Plans/HANDOFF-DOCUMENTS-steward-preflight.md` | Slice authority. |

**Bounded discovery exception:** Not applicable — no additional paths are required.

## §5 Explicitly out of scope / collision boundary

| Path | Why this slice must not touch or claim it |
|---|---|
| `scripts/review_external_pr.py` | Existing review engine remains unchanged; steward preflight may reuse/import its parser contract. |
| `.cursor/skills/external-agent-pr-loop/**` | PR mechanics landed in #573; no need to reopen them for a read-only preflight helper. |
| `AGENTS.md` / `.cursor/rules/**` | Foundational law already landed in #572. |
| Product source/tests | No product behavior. |

## §6 Implementation contract

```text
Input:
  --handoff <checked-in or local HANDOFF path>
  optional --pr <number> for review-cycle metadata
  optional --repo <owner/name>
  optional --local-only to skip GitHub discovery

Output:
  deterministic JSON snapshot containing candidate metadata/lease,
  main/head/worktree state, active handoff lanes, optional open PR lanes,
  concrete write conflicts, warnings, base relation, optional review-cycle summary,
  and status pass|warn|block.

Invariant:
  same as §1

Failure behavior:
  candidate missing/unreadable/unparseable §4 → block/explicit error
  Git metadata unavailable → explicit error (repo context is required)
  GitHub unavailable when not local-only → warning; local evidence remains usable
  overlap → block with provenance

Replay / idempotency:
  unchanged repository inputs → semantically identical snapshot except ordering-stable transient command details
  changed lanes/PRs → refreshed snapshot
  no mutation on any path

Trust boundary:
  Verifies: syntactic handoff lease + observed Git/GitHub metadata
  Records/trusts without proving: semantic validity of the handoff's declared runtime/state ownership and whether a base change invalidates behavior
```

### A. State / fallback matrix

| Observable path | Loading/init | Exact success | Ordinary miss | Dependency unavailable | Integrity failure | Stale/superseded | Retry/replay |
|---|---|---|---|---|---|---|---|
| Local repo/handoffs | read synchronously | normalized snapshot | no other active lanes | Git unavailable = error | empty candidate §4 = block | base differs = warn | rerun safe |
| GitHub PR/reviews | optional read | PR/review facts included | no open PR/reviews | `gh` unavailable = warning/local evidence only | malformed JSON = warning, not fabricated empty truth | remote state naturally refreshed | rerun safe |

### B. Identity matrix

| Situation | Required rule | Ambiguity behavior | Fallback permitted? |
|---|---|---|---|
| Lane identity | branch name when declared/observed; handoff path and PR number remain provenance | unknown branch remains unknown, never guessed | Yes: provenance objects stay separate |
| Write path | normalized repo-relative literal/glob lease entries | wildcard overlap is conservative and reported with both patterns | No silent first-win |
| Review cycle | explicit `Review Cycle <N>` body + review `commit_id` | duplicate labels or same-head formal entries reported as anomalies; distinct heads determine count | No inference from generic comments |

### C. Persistence / replay matrix

Not applicable — read-only output; no durable state is written.

### D. Predecessor → consumer mapping

**Grounding source:** `scripts/review_external_pr.py` handoff parser and documented `gh` JSON fields.

| Predecessor field/outcome | Real shape/optionality | Consumer behavior | Transformation | Proof |
|---|---|---|---|---|
| `extract_allowlist_paths()` | list of parsed backticked §4 `Path` cells | candidate/active handoff lease | sorted normalized paths | fixture tests |
| `git worktree list --porcelain` | record blocks with `worktree`, `HEAD`, optional `branch` | observed checkout lanes | branch ref stripped to branch name | parser test |
| `gh pr view --json number,headRefName,headRefOid,url,files` | PR identity + files array | open PR lane | file paths only; same branch optionally excluded | mocked PR test |
| `gh api .../pulls/<N>/reviews` | review objects with body + `commit_id` | cycle summary | explicit cycle regex; distinct commit IDs | mocked review test |

## §7 Evidence required to merge

| Guarantee / invariant clause | Owning boundary | Evidence class | Command or manual scenario | Expected evidence | Stop condition |
|---|---|---|---|---|---|
| Exact and wildcard lease overlaps block | pure comparison | unit | `uv run pytest tests/test_steward_preflight.py -q` | overlap cases pass | false pass |
| PR-only overlap is visible; same branch excluded | GitHub normalization | mocked contract | same test module | block/exclusion cases pass | self-conflict or missed PR conflict |
| `gh` unavailable degrades truthfully | dependency boundary | failure injection | same test module | warning + local facts preserved | fabricated complete remote scan |
| Base drift is warning, not automatic invalidation | Git boundary | unit/mock | same test module | relation fields + warn | false block from harmless main advance |
| Review cycles count explicit distinct-head judgments only | review parser | unit | same test module | duplicates/anomalies surfaced; count stable | comments inflate count |
| CLI never mutates repo | integration/static | review + CLI smoke | `uv run python scripts/steward_preflight.py --help` | read-only options only | mutation command/path exists |
| Repository quality | repo | regression | `uv run ruff check scripts/steward_preflight.py tests/test_steward_preflight.py` | pass | lint failure |
| Scope | Git diff | static | `git diff --check && git diff --name-only 964a360286d1c2e4444787002c00b40257dae34f...HEAD` | only §4 paths | extra path |

Exact verification commands:

```bash
uv run pytest tests/test_steward_preflight.py -q
uv run ruff check scripts/steward_preflight.py tests/test_steward_preflight.py
uv run python scripts/steward_preflight.py --help
git diff --check
git diff --name-only 964a360286d1c2e4444787002c00b40257dae34f...HEAD
```

### Minimal live / dogfood proof

Existing surface: repository process itself.  
Smallest realistic scenario: run preflight against this handoff while another unrelated product PR is open.  
Expected observation: current worktrees/PR lane appear; no false collision unless an actual §4 path overlaps.  
Evidence captured: CLI JSON in review handback when an execution environment is available.

### Baseline failure handling

Not applicable — no required baseline failure known.

## §8 Required review handback

Record Review Cycle N, exact PR/head, unit/lint/help results with provenance, candidate snapshot behavior, all conflicts/warnings seen, changed paths vs §4, prior findings on re-review, and named successor still false.

## §9 Acceptance rubric

- [ ] One read-only preflight command produces the complete mechanical steward snapshot defined by §6.
- [ ] Concrete active-handoff or open-PR write overlap blocks; same-lane PR identity does not self-conflict.
- [ ] GitHub unavailability is a visible warning and never masquerades as “no remote conflicts.”
- [ ] Base drift is reported without the tool making semantic invalidation decisions.
- [ ] Review-cycle metadata follows explicit-label + distinct-head semantics and reports anomalies.
- [ ] No Git/GitHub/process state is mutated.
- [ ] Tests exercise the adversarial sequences at the owning parser/aggregation boundaries.
- [ ] Actual changed paths stay inside §4.
- [ ] The tool does not author handoffs or decide collision resolution; those remain steward responsibilities.
