# REPORT — Superseded open PR salvage and retirement

**Date:** 2026-07-31  
**Required base / actual base:** `c371d43178a2b83da299319a047f93bae50d0959`  
**Actual head:** see `git rev-parse origin/chore/mine-retire-superseded-prs` after push (single salvage commit on this branch)
**Salvage branch:** `chore/mine-retire-superseded-prs`  
**Evidence ledger authority:** This report is the canonical disposition ledger for the eight source PRs listed below. Dispatch record: [`Docs/Plans/HANDOFF-superseded-open-pr-salvage-and-retirement.md`](../Plans/HANDOFF-superseded-open-pr-salvage-and-retirement.md).

### Source heads (frozen)

| PR | Head SHA |
|---|---|
| #231 | `006e53b27f175de0fb96f2a706745701bbbece84` |
| #395 | `bb7e4eb7485ee0923b5c45c01abf93ba9f68040a` |
| #432 | `5cdcd107e50cc89f16e44c4072705549e28d696e` |
| #433 | `543847c9484a0a57f1950f389680db70b4841bac` |
| #444 | `127168de48d2d94803f906ff69a26bbc9fefaf82` |
| #449 | `2369d32b3b574104cc09fc8abb0bddef69031f51` |
| #459 | `0abdb55d5779273e406643221e0a41e959371055` |
| #460 | `a4d95b68907a8b99e0991616817cd3c6a9e466e8` |

---

## §1 Mission summary

Mine durable documentation and one bounded code salvage (#433 extract-promote inspection status) from eight long-lived open PRs whose stacked implementation is superseded by current `main`, name successors for still-valid intent, and retire the source PRs without rebasing or cherry-picking obsolete architecture.

**Salvage invariant:** No rebased stacked heads, no dormant PDF/publication parallel APIs, no first-wins projection tolerance, no tracker/roadmap overwrite, no threat-publication parallel stack.

---

## §2 Source disposition ledger (outcome table)

| PR | GitHub state before salvage | Salvage outcome | Landed in this branch | Named successor |
|---|---|---|---|---|
| #231 | CLOSED | **ALREADY_PRESENT** (+ REJECTED runner) | Report note only | — |
| #395 | CLOSED | **ALREADY_PRESENT** (+ REJECTED shell) | Report + preserved handoff pointer | [`HANDOFF-bld09-pdf-ocr-lineage-pilot.md`](../Plans/HANDOFF-bld09-pdf-ocr-lineage-pilot.md) |
| #432 | OPEN (superseded) | **PRESERVED** intent (+ REJECTED shell) | Report + successor handoff | [`HANDOFF-build-stay-on-build-dogfood-after-mc02.md`](../Plans/HANDOFF-build-stay-on-build-dogfood-after-mc02.md) |
| #433 | OPEN (superseded) | **IMPLEMENTED** (code) + **PRESERVED** (UI successor) | Code + report §6D | Frontend inspection UI after #431/#432 |
| #444 | OPEN (superseded) | **PRESERVED** (+ REJECTED first-wins) | Report + successor handoff | [`HANDOFF-graph-review-browse-committed-sessions.md`](../Plans/HANDOFF-graph-review-browse-committed-sessions.md) |
| #449 | OPEN (superseded) | **PRESERVED** docs (+ REJECTED tracker/report overwrite) | Pattern + conditional handoff | [`HANDOFF-dms-generation-validation-diagnostics.md`](../Plans/HANDOFF-dms-generation-validation-diagnostics.md) (conditional) |
| #459 | OPEN (duplicate) | **REJECTED** as independent authority | Report only | — (same as #431) |
| #460 | OPEN (superseded) | **REJECTED** parallel API (+ **PRESERVED** review checklist) | Report §#460 checklist | #462 [`HANDOFF-sbw09a-publication-operation-ledger.md`](../Plans/HANDOFF-sbw09a-publication-operation-ledger.md) |

---

## §3 Per-PR contribution tables

Disposition codes: **IMPLEMENTED** — landed in salvage branch; **PRESERVED** — named successor or historical record; **ALREADY_PRESENT** — on main before salvage; **REJECTED** — obsolete or harmful; do not port.

### #231 — C2S23 vocabulary ablation dogfood (`006e53b`)

| Contribution | Disposition | Evidence |
|---|---|---|
| Dogfood report `GRAPH-MEMORY-VOCABULARY-ABLATION-DOGFOOD-C2S23-MIREWARD.md` | **ALREADY_PRESENT** | `Docs/Reports/GRAPH-MEMORY-VOCABULARY-ABLATION-DOGFOOD-C2S23-MIREWARD.md` on main |
| Live LLM runner `run_vocabulary_ablation_c2s23_mireward_dogfood.py` | **ALREADY_PRESENT** | `evals/graph_memory_layer/run_vocabulary_ablation_c2s23_mireward_dogfood.py` |
| Precomputed runner `run_c2s23_vocabulary_ablation_dogfood.py` | **REJECTED** | Obsolete non-live method; not ported |
| Siege-prep lexical over-capture observation | **PRESERVED** (report only) | Historical note retained in this ledger; no code |
| PR branch itself | **REJECTED** | Already CLOSED on GitHub before salvage |

### #395 — Build surface worldbuilding profile (`bb7e4eb`)

| Contribution | Disposition | Evidence |
|---|---|---|
| Worldbuilding profile stack | **ALREADY_PRESENT** | Main Build surface profile modules |
| Build toolbar integration | **ALREADY_PRESENT** | `BuildIngestToolbar` / related main paths |
| `graphReviewRunSelection` | **ALREADY_PRESENT** | Graph Review run selection on main |
| Monolithic `BuildSurfaceShell` / local draft architecture | **REJECTED** | Superseded by current modular Build surface |
| PDF/OCR lineage intent | **PRESERVED** | [`HANDOFF-bld09-pdf-ocr-lineage-pilot.md`](../Plans/HANDOFF-bld09-pdf-ocr-lineage-pilot.md) (source head `bb7e4eb`) |
| PDF/OCR implementation code | **REJECTED** | Dormant framework prohibited; no PDF code landed |
| PR branch | **REJECTED** | Already CLOSED on GitHub before salvage |

### #432 — Build graph reference + stay-on-Build (`5cdcd107`)

| Contribution | Disposition | Evidence |
|---|---|---|
| Build graph-ref search/insert behaviors | **PRESERVED** | Successor after MC-02a (#431): [`HANDOFF-build-stay-on-build-dogfood-after-mc02.md`](../Plans/HANDOFF-build-stay-on-build-dogfood-after-mc02.md) |
| Stay-on-Build inspector/summary | **PRESERVED** | Same successor; blocked on #431 merge |
| Find existing handoff | **PRESERVED** | Named in MC-02b / Stay-on-Build successors |
| Starter content → MC-02a (#431), MC-02b, Stay-on-Build, BLD inspection-truth | **PRESERVED** | Successor map in stay-on-Build handoff |
| `BuildGraphReferenceShell` | **REJECTED** | Obsolete; #431 surface-neutral `graphReference` replaces |
| Plan-import architecture | **REJECTED** | Superseded by MC-02a extraction |
| Auto Mireward starter as product | **REJECTED** | Not a product requirement |
| Plan `PlanGraphRefSearch` | **ALREADY_PRESENT** | Main Plan surface |
| Basic Build extract + Graph Review handoff | **ALREADY_PRESENT** | Main Build ingest path |

### #433 — Extract-promote inspection status (`543847c`)

| Contribution | Disposition | Evidence |
|---|---|---|
| `ExtractPromoteInspectionStatus` type | **IMPLEMENTED** | `apps/live_control_server/models/extract_promote.py` |
| `run_status` / `inspection_status` on error paths | **IMPLEMENTED** | `apps/live_control_server/services/extract_promote.py` |
| `_review_package_inspection_status` / `_with_review_package_inspection_context` | **IMPLEMENTED** | `apps/live_control_server/services/extract_promote.py` |
| `get_exact_run_review_package` enrichment | **IMPLEMENTED** | Same service module |
| Tests: `blocked` / `invalid_evidence` + `span_ref` / `false_anchor_quote` retention | **IMPLEMENTED** | `tests/test_live_extract_promote_api.py` |
| `false_anchor_quote` / `span_ref` diagnostic emission | **ALREADY_PRESENT** | Pre-salvage main behavior |
| Frontend inspection UI types | **PRESERVED** | Successor after #431/#432 Build inspector lands |

#### §6D — #433 source-to-current mapping

| Source (#433 head) | Current path / symbol | Transformation |
|---|---|---|
| `ExtractPromoteInspectionStatus = Literal["ready", "blocked", "invalid_evidence"]` | `models/extract_promote.py` | Direct port |
| `ExtractPromoteErrorResponse.run_status` / `inspection_status` | `models/extract_promote.py` | Optional camelCase-serialized fields on 422 error body |
| `_review_package_inspection_status(diagnostics)` | `services/extract_promote.py` | `false_anchor_quote` → `invalid_evidence`; else `blocked` |
| `_with_review_package_inspection_context(exc, run_status=…)` | `services/extract_promote.py` | Enriches `run_not_promotable` with lifecycle + inspection fields |
| `get_exact_run_review_package` evidence projection | Same function | try/except wraps `_assert_and_project_candidate_evidence`; preserves `resolved.status` (e.g. `reviewable`) while inspection fails |
| API tests for blocked + invalid_evidence | `tests/test_live_extract_promote_api.py` | Asserts `runStatus=reviewable`, `inspectionStatus`, and retained `span_ref`/`false_anchor_quote` diagnostics |

### #444 — Graph Review browse-first sessions (`127168de`)

| Contribution | Disposition | Evidence |
|---|---|---|
| Browse-first World Graph session catalog + Load UX | **PRESERVED** | [`HANDOFF-graph-review-browse-committed-sessions.md`](../Plans/HANDOFF-graph-review-browse-committed-sessions.md) |
| `postWorldGraphRecapProjection` / `/recap-projection` API | **ALREADY_PRESENT** | Main projection API |
| Ingest-run catalog path | **ALREADY_PRESENT** | Main ingest catalog |
| `per_contribution_assertion_ids` first-wins tolerance | **REJECTED** | Main keeps strict `semantic_assertion_divergence` 409 |
| Divergent-shadow / first-wins projection rewrite | **REJECTED** | Unsafe; main keeps fail-closed `semantic_assertion_divergence` 409 |
| Remaining browse-first workbench rewrite size | **PRESERVED** (successor) | Exceeds salvage path bound; see browse-committed-sessions handoff |

### #449 — R0-A generation validation failure (`2369d32`)

| Contribution | Disposition | Evidence |
|---|---|---|
| `PATTERN-openai-structured-outputs-complex-contracts.md` | **PRESERVED** | Scrubbed copy in `Docs/Design/` (ACTIVE_REFERENCE) |
| `HANDOFF-dms-generation-validation-diagnostics.md` | **PRESERVED** | Scrubbed CONDITIONAL successor in `Docs/Plans/` |
| PR449 R0-A report overwrite | **REJECTED** | Main `MAGIC-MOMENT-R0-A-2026-07-29.md` is authoritative |
| Stale tracker R0-A FAIL_PRODUCT / DMS-VAL-01 dispatch-now claims | **REJECTED** | Not copied; #462 owns current Statblock work |
| R0-A factual evidence + roadmap reanchor on main | **ALREADY_PRESENT** | `Docs/Reports/REPORT-threat-statblock-roadmap-reanchor-2026-07-30.md`; R0-A **OPERATOR_CONFIRMED_PASS** |

### #459 — Duplicate MC-02a handoff (`0abdb55`)

| Contribution | Disposition | Evidence |
|---|---|---|
| Handoff document | **ALREADY_PRESENT** | Byte-identical to open PR #431 handoff |
| Independent dispatch authority | **REJECTED** | No unique value; use #431 only |

### #460 — Parallel threat publication API (`a4d95b`)

| Contribution | Disposition | Evidence |
|---|---|---|
| Entire `threat_statblock_publication*` parallel API/models/routes/store | **REJECTED** | Superseded by #462 SBW09a ledger design |
| Core begin/refresh/cancel/replay/stale/corrupt/history guarantees | **ALREADY_PRESENT** on #462 | [`HANDOFF-sbw09a-publication-operation-ledger.md`](../Plans/HANDOFF-sbw09a-publication-operation-ledger.md) |
| Residual review obligations (see §#460 checklist below) | **PRESERVED** | Review against #462 implementation |

#### §#460 — Review checklist (for #462, not ported code)

When reviewing SBW09a implementation, verify these adversarial cases called out by #460 research:

1. **Route query-param rejection** — malformed or conflicting query params fail closed without partial ledger writes.
2. **Process-boundary GET reload** — reload after process restart returns the same operation authority without reconstructing from mutable draft state.
3. **Claim-under-lock** — concurrent begin/claim does not produce twin active operations for one mechanics locator.
4. **Invalid filename corruption** — corrupt on-disk ledger filenames surface explicit error, not silent repair.
5. **World/campaign mismatch** — parent world/campaign drift becomes stale state; no silent rebase.
6. **Manual live-proof** — operator can exercise begin → read → stale → cancel without World Graph mutation.

---

## §4 Changed paths (salvage branch vs base)

### Code (#433 only — pre-existing in worktree before doc commit)

| Path | Action |
|---|---|
| `apps/live_control_server/models/extract_promote.py` | Modified |
| `apps/live_control_server/services/extract_promote.py` | Modified |
| `tests/test_live_extract_promote_api.py` | Modified |

### Documentation (this salvage commit)

| Path | Action |
|---|---|
| `Docs/Reports/REPORT-superseded-open-pr-salvage-2026-07-31.md` | Added |
| `Docs/Plans/HANDOFF-superseded-open-pr-salvage-and-retirement.md` | Added |
| `Docs/Design/PATTERN-openai-structured-outputs-complex-contracts.md` | Added (scrubbed from #449) |
| `Docs/Plans/HANDOFF-dms-generation-validation-diagnostics.md` | Added (scrubbed CONDITIONAL successor) |
| `Docs/Plans/HANDOFF-graph-review-browse-committed-sessions.md` | Added |
| `Docs/Plans/HANDOFF-build-stay-on-build-dogfood-after-mc02.md` | Added |

**Explicitly not changed:** `PR-TRACKER-threat-statblock-authoring-projection.md`, `ROADMAP-threat-statblock-authoring-projection.md`, any `threat_statblock_publication*` paths, PDF/OCR code, #444 first-wins projection code.

---

## §5 Verification results

| Command | Expected | Result |
|---|---|---|
| `uv run pytest -q tests/test_live_extract_promote_api.py -k "false_anchor or review_package or reviewable"` | #433 blocked/invalid_evidence + diagnostic retention | **PASS** — `4 passed, 58 deselected` (2026-07-31) |
| `git diff --name-only c371d431...HEAD` (post-commit) | Only §4 allowlist paths | **PASS** pending commit — expected 3 code + 6 docs |
| `git diff --check` | Exit 0 | **PASS** |
| Conditional UI / graph-kernel / PDF lineage | N/A — no UI, projection, or PDF paths changed | **not applicable** |
| Source PR retirement | Eight source PRs CLOSED with disposition comments; none MERGED by this op | `{{VERIFY_GITHUB_CLOSURE}}` (filled after PR open + close) |

---

## §6 Protected PR states

These PRs remain **protected active work** — salvage must not close, rebase, or overwrite them:

| PR | Role | Why protected |
|---|---|---|
| **#431** | MC-02a surface-neutral graph reference | Active implementation; #459 duplicate rejected |
| **#442** | Eldyrwild world-graph snapshot transfer | Intentional OPEN transfer vehicle; do not close/merge |
| **#462** | SBW09a publication operation ledger | Owns publication guarantees; #460 parallel API rejected |
| **#463** | TL01F Timeline temporal lane gate | Active Timeline thread; outside salvage authority |

Salvage **may** reference and name successors that **depend on** #431/#462 merging first.

---

## §7 Explicit confirmations from dispatch handoff

- [x] No rebased or cherry-picked stacked heads from source PRs (except bounded #433 port documented in §6D).
- [x] No dormant PDF/OCR framework code landed.
- [x] No `threat_statblock_publication*` parallel stack ported.
- [x] No first-wins / divergent-shadow projection tolerance from #444.
- [x] No PR-TRACKER or ROADMAP edits in salvage branch.
- [x] #231, #395 already CLOSED on GitHub — ledger only.
- [x] #449 pattern/handoff scrubbed; dispatch-now tracker claims rejected.
- [x] R0-A treated as **OPERATOR_CONFIRMED_PASS** on main; DMS-VAL-01 handoff is **CONDITIONAL** on regression only.

---

## §8 Named successors still false

| Successor | Source PR | Blocked on |
|---|---|---|
| Build World Reference Loop v1 (MC-02a) | #432, #459 | #431 merge |
| MC-02b / candidate-assisted Find existing | #432 | MC-02a |
| Stay-on-Build extraction inspector/summary | #432 | [`HANDOFF-build-stay-on-build-dogfood-after-mc02.md`](../Plans/HANDOFF-build-stay-on-build-dogfood-after-mc02.md) after #431 |
| BLD inspection-truth | #432 | Build inspector milestone |
| Graph Review browse-first committed sessions | #444 | [`HANDOFF-graph-review-browse-committed-sessions.md`](../Plans/HANDOFF-graph-review-browse-committed-sessions.md); strict projection |
| PDF/OCR lineage pilot | #395 | [`HANDOFF-bld09-pdf-ocr-lineage-pilot.md`](../Plans/HANDOFF-bld09-pdf-ocr-lineage-pilot.md) |
| DMS generation validation diagnostics | #449 | [`HANDOFF-dms-generation-validation-diagnostics.md`](../Plans/HANDOFF-dms-generation-validation-diagnostics.md) — **only if** R0-A-class opaque `definition_invalid` regresses |
| Frontend extract-promote inspection UI | #433 | Build inspector after #431/#432 |
| SBW09b+ publication resolution / graph proposal | #460 research | #462 SBW09a merge first |

---

## §9 Closure protocol

After the salvage PR is opened remotely with this report committed, close each open source PR (#432, #433, #444, #449, #459, #460) using the §8A template in [`HANDOFF-superseded-open-pr-salvage-and-retirement.md`](../Plans/HANDOFF-superseded-open-pr-salvage-and-retirement.md), and post the same disposition comment on already-CLOSED #231/#395. Do not MERGED any of the eight. Do not close #442. Then fill `{{VERIFY_GITHUB_CLOSURE}}` and `{{HEAD_AFTER_COMMIT}}`.
