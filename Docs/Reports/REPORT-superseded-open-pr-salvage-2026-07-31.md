# REPORT — Superseded open PR salvage and retirement

**Date:** 2026-07-31 (revised 2026-08-01 after PR #464 REQUEST_CHANGES)
**Original mining base:** `c371d43178a2b83da299319a047f93bae50d0959`
**Re-anchored implementation base / required current base:** `2fa5b7909a28f0c7cf15aab35a56db68ef67ca2e` (#462 merge commit; current `main` tip at re-anchor)
**Actual head:** `{{HEAD_AFTER_REVISION_COMMIT}}`
**Salvage branch:** `chore/mine-retire-superseded-prs`
**Salvage PR:** https://github.com/Drakosfire/DungeonMindBuddy/pull/464
**Evidence ledger authority:** This report is the canonical disposition ledger for the eight source PRs listed below. Dispatch record: [`Docs/Plans/HANDOFF-superseded-open-pr-salvage-and-retirement.md`](../Plans/HANDOFF-superseded-open-pr-salvage-and-retirement.md).

### Re-anchor note

The first salvage commit mined against `c371d431…`. PR #464 received **REQUEST_CHANGES** requiring re-implementation on current `main` after #462 (SBW09a publication operation ledger) merged at `2fa5b790…` on 2026-08-01. This revision re-anchors the ledger and #433 code mapping to that base. Source PRs were closed after salvage PR #464 existed remotely (per authoritative handoff §8B); this doc refresh does **not** reopen them.

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

**Salvage invariant:** No rebased stacked heads, no dormant PDF/publication parallel APIs, no first-wins projection tolerance, no tracker/roadmap overwrite, no threat-publication parallel stack. #433 behavior is **reimplemented** on current-main models/services — not ported from the source PR branch as implementation base.

---

## §2 Source disposition ledger (outcome table)

| PR | GitHub state before salvage | Salvage outcome | Landed in this branch | Named successor |
|---|---|---|---|---|
| #231 | CLOSED | **ALREADY_PRESENT** (+ REJECTED runner) | Report note only | — |
| #395 | CLOSED | **ALREADY_PRESENT** (+ REJECTED shell) + **PRESERVED** pilot report | Report + [`REPORT-build-pdf-lineage-pilot.md`](REPORT-build-pdf-lineage-pilot.md) | [`HANDOFF-bld09-pdf-ocr-lineage-pilot.md`](../Plans/HANDOFF-bld09-pdf-ocr-lineage-pilot.md) (successor gate; PREPARED/DRAFT — not a replacement for completed report) |
| #432 | OPEN (superseded) | **PRESERVED** intent (+ REJECTED shell) | Report + successor handoff | [`HANDOFF-build-stay-on-build-dogfood-after-mc02.md`](../Plans/HANDOFF-build-stay-on-build-dogfood-after-mc02.md) |
| #433 | OPEN (superseded) | **IMPLEMENTED** (code) + **PRESERVED** (UI successor) | Code + report §6D | Frontend inspection UI after #431/#432 |
| #444 | OPEN (superseded) | **PRESERVED** (+ REJECTED first-wins) | Report + successor handoff | [`HANDOFF-graph-review-browse-committed-sessions.md`](../Plans/HANDOFF-graph-review-browse-committed-sessions.md) |
| #449 | OPEN (superseded) | **PRESERVED** docs (+ REJECTED tracker/report overwrite) | Pattern + conditional handoff | [`HANDOFF-dms-generation-validation-diagnostics.md`](../Plans/HANDOFF-dms-generation-validation-diagnostics.md) (conditional) |
| #459 | OPEN (duplicate) | **REJECTED** as independent authority | Report only | — (same as #431) |
| #460 | OPEN (superseded) | **REJECTED** parallel API (+ **PRESERVED** residual checklist) | Report §#460 checklist | Residual obligations only; core guarantees **ALREADY_PRESENT** on merged `main` (#462) |

---

## §3 Per-PR contribution tables

Disposition codes: **IMPLEMENTED** — landed in salvage branch; **PRESERVED** — named successor or historical record; **ALREADY_PRESENT** — on main before salvage or merged independently; **REJECTED** — obsolete or harmful; do not port.

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
| Completed BLD-09 PDF/OCR lineage pilot report | **PRESERVED** | [`REPORT-build-pdf-lineage-pilot.md`](REPORT-build-pdf-lineage-pilot.md) — HISTORICAL banner; **GO**; 3/3 trials; one canonical identity; fail-closed OCR/page-map; zero promotions |
| Stale PREPARED/DRAFT successor handoff | **PRESERVED** (gate only) | [`HANDOFF-bld09-pdf-ocr-lineage-pilot.md`](../Plans/HANDOFF-bld09-pdf-ocr-lineage-pilot.md) — re-anchor gate; **not** a replacement for the completed report |
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
| `get_exact_run_review_package` enrichment | **IMPLEMENTED** | Wraps **complete post-resolution** review-package construction boundary (source prose read, candidate parse, scope validation, frozen span-index load/validate, evidence projection) — not only `_assert_and_project_candidate_evidence` |
| Tests: `blocked` / `invalid_evidence` + `span_ref` / `false_anchor_quote` retention | **IMPLEMENTED** | `tests/test_live_extract_promote_api.py` |
| Test: post-resolution span-index failure retains inspection fields | **IMPLEMENTED** (regression target) | `test_review_package_span_index_failure_keeps_inspection_fields` |
| `false_anchor_quote` / `span_ref` diagnostic emission | **ALREADY_PRESENT** | Pre-salvage main behavior |
| Frontend inspection UI types | **PRESERVED** | Successor after #431/#432 Build inspector lands |

#### §6D — #433 source-to-current mapping

Reimplemented on current-main models/services from #433 behavior; adapted to current camelCase error vocabulary and owning-boundary tests. **Not** a direct port from source PR branch.

| Source (#433 head) | Current path / symbol | Transformation |
|---|---|---|
| `ExtractPromoteInspectionStatus = Literal["ready", "blocked", "invalid_evidence"]` | `models/extract_promote.py` | Reimplemented on current-main Pydantic models |
| `ExtractPromoteErrorResponse.run_status` / `inspection_status` | `models/extract_promote.py` | Optional camelCase-serialized fields on 422 error body |
| `_review_package_inspection_status(diagnostics)` | `services/extract_promote.py` | `false_anchor_quote` → `invalid_evidence`; else `blocked` |
| `_with_review_package_inspection_context(exc, run_status=…)` | `services/extract_promote.py` | Attaches `run_status` + `inspection_status` to every post-resolution `ExtractPromoteError` (not only evidence-projection) |
| `get_exact_run_review_package` review-package construction | Same function | try/except wraps the **complete post-resolution** boundary: source prose read → candidate parse → scope validation → frozen span-index load/validate → evidence projection; preserves `resolved.status` (e.g. `reviewable`) while inspection fails |
| API tests for blocked + invalid_evidence | `tests/test_live_extract_promote_api.py` | Asserts `runStatus=reviewable`, `inspectionStatus`, and retained `span_ref`/`false_anchor_quote` diagnostics |
| Post-resolution span-index failure | `test_review_package_span_index_failure_keeps_inspection_fields` | Asserts inspection enrichment survives span-index load/validate failure after resolution |

### #444 — Graph Review browse-first sessions (`127168de`)

| Contribution | Disposition | Evidence |
|---|---|---|
| Browse-first World Graph session catalog + Load UX (§1A) | **PRESERVED** | [`HANDOFF-graph-review-browse-committed-sessions.md`](../Plans/HANDOFF-graph-review-browse-committed-sessions.md) §1A / §2A |
| Corpus-backed recap catalog product finding (§1B / §2B) | **PRESERVED** | Same handoff: statuses `not_ingested` / `preview_ready` / `stale_vs_source` / `broken(reason)`; populate/refresh CTA; quarantine eval dogfood — **separate** from browse-committed-sessions §1A |
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
| Entire `threat_statblock_publication*` parallel API/models/routes/store | **REJECTED** | Superseded by merged #462 SBW09a ledger design on `main` |
| Core begin/refresh/cancel/replay/stale/corrupt/history guarantees | **ALREADY_PRESENT** on merged `main` (#462) | [`HANDOFF-sbw09a-publication-operation-ledger.md`](../Plans/HANDOFF-sbw09a-publication-operation-ledger.md); merged at `2fa5b790…` |
| Residual review obligations (see §#460 checklist below) | **PRESERVED** | Successor obligations only where merged-main tests do not yet prove the case |

#### §#460 — Review checklist (classified against merged `main`, not open #462)

When reviewing publication guarantees, map #460 research items to merged-main tests. Parallel `threat_statblock_publication*` API remains **REJECTED**.

| #460 obligation | Disposition on merged `main` | Merged-main test evidence |
|---|---|---|
| Route query-param rejection | **ALREADY_PRESENT** | `test_begin_route_rejects_extra_field_with_422`, `test_begin_route_rejects_invalid_draft_id_with_422`, `test_read_route_rejects_malformed_operation_id_with_422` |
| Process-boundary GET reload | **ALREADY_PRESENT** | `test_restart_reload_preserves_exact_snapshot_locator_parent_and_digests`, `test_restart_reload_via_new_test_client_preserves_operation` |
| Claim-under-lock / competing begin | **ALREADY_PRESENT** | `test_competing_begin_allows_one_active_operation` |
| Corrupt ledger / invalid filename | **ALREADY_PRESENT** | `test_corrupt_ledger_fails_closed_without_rewrite`, `test_corrupt_ledger_bad_schema_fails_closed` |
| World/campaign / parent mismatch | **ALREADY_PRESENT** | `test_begin_rejects_parent_mismatch_without_record`, `test_begin_route_parent_mismatch_returns_409` |
| History full | **ALREADY_PRESENT** | `test_history_full_rejects_without_mutation` |
| No draft/graph mutation | **ALREADY_PRESENT** | `test_all_operations_leave_draft_graph_and_dungeonmind_unchanged`, `test_route_flow_leaves_threat_draft_bytes_unchanged` |
| Manual live-proof — operator begin → read → stale → cancel without World Graph mutation | **PRESERVED** | Successor obligation; not automated in merged-main suite |

---

## §4 Changed paths (salvage branch vs re-anchored base `2fa5b790…`)

### Code (#433 — reimplemented on current main)

| Path | Action |
|---|---|
| `apps/live_control_server/models/extract_promote.py` | Modified |
| `apps/live_control_server/services/extract_promote.py` | Modified |
| `tests/test_live_extract_promote_api.py` | Modified |

### Documentation

| Path | Action |
|---|---|
| `Docs/Reports/REPORT-superseded-open-pr-salvage-2026-07-31.md` | Added / revised |
| `Docs/Plans/HANDOFF-superseded-open-pr-salvage-and-retirement.md` | Added |
| `Docs/Design/PATTERN-openai-structured-outputs-complex-contracts.md` | Added (scrubbed from #449) |
| `Docs/Plans/HANDOFF-dms-generation-validation-diagnostics.md` | Added (scrubbed CONDITIONAL successor) |
| `Docs/Plans/HANDOFF-graph-review-browse-committed-sessions.md` | Added |
| `Docs/Plans/HANDOFF-build-stay-on-build-dogfood-after-mc02.md` | Added |
| `Docs/Reports/REPORT-build-pdf-lineage-pilot.md` | Added (PRESERVED historical pilot from #395) |

**Explicitly not changed:** `PR-TRACKER-threat-statblock-authoring-projection.md`, `ROADMAP-threat-statblock-authoring-projection.md`, any `threat_statblock_publication*` paths, PDF/OCR implementation code, #444 first-wins projection code, #462 merged paths (salvage did not rewrite SBW09a ledger implementation).

---

## §5 Verification results

Intended verification set for re-anchored revision (base `2fa5b790…` → `{{HEAD_AFTER_REVISION_COMMIT}}`):

| Command | Expected | Result |
|---|---|---|
| `uv run pytest -q tests/test_live_extract_promote_api.py -k "false_anchor or review_package or reviewable or span_index_failure"` | #433 blocked/invalid_evidence + diagnostic retention + span-index failure enrichment | **PASS** — `5 passed, 58 deselected` (2026-08-01; post-resolution span-index loader forced via monkeypatch because byte corruption is caught pre-resolution by digest seal) |
| `uv run pytest -q tests/test_live_extract_promote_api.py` (full file — required by authoritative handoff) | All extract-promote API tests pass | **PASS** — `63 passed` (2026-08-01) |
| `git diff --name-only 2fa5b790...HEAD` | Only §4 allowlist paths | **PASS** — 3 code + 7 docs (see §4); no denylist paths |
| `git diff --check` | Exit 0 | **PASS** |
| Conditional UI / graph-kernel / PDF lineage implementation | N/A unless those paths changed | **not applicable** — no UI, projection-kernel, or PDF implementation paths in salvage allowlist |
| Source PR retirement | Eight source PRs CLOSED with disposition comments; none MERGED by salvage | **PASS** — closures recorded §10; re-anchor doc refresh does not reopen |

---

## §6 Protected PR states

These PRs remain **protected active work** — salvage must not close, rebase, or overwrite them:

| PR | Role | State after salvage / at re-anchor |
|---|---|---|
| **#431** | MC-02a surface-neutral graph reference | **OPEN** — active implementation; #459 duplicate rejected |
| **#442** | Eldyrwild world-graph snapshot transfer | **OPEN** — intentional transfer vehicle; do not close/merge |
| **#462** | SBW09a publication operation ledger | **MERGED** at `2fa5b790…` (2026-08-01); salvage did not rewrite its paths |
| **#463** | TL01F Timeline temporal lane gate | **OPEN** — active Timeline thread; outside salvage authority |

Salvage **may** reference successors that **depend on** #431 merging first. #462 obligations are classified against merged `main`, not an open successor.

---

## §7 Explicit confirmations from dispatch handoff

- [x] No wholesale source merge or cherry-pick of stacked heads from source PRs.
- [x] No code based on a source PR branch as implementation base — #433 reimplemented from current `main` models/services (§6D).
- [x] No dormant PDF/OCR framework **implementation** code landed (pilot **report** preserved only).
- [x] No `threat_statblock_publication*` parallel stack ported.
- [x] No first-wins / divergent-shadow projection tolerance from #444.
- [x] No PR-TRACKER or ROADMAP edits in salvage branch.
- [x] #231, #395 already CLOSED on GitHub — ledger + preserved pilot report.
- [x] #449 pattern/handoff scrubbed; dispatch-now tracker claims rejected.
- [x] R0-A treated as **OPERATOR_CONFIRMED_PASS** on main; DMS-VAL-01 handoff is **CONDITIONAL** on regression only.
- [x] **#442 remains OPEN.**
- [x] **#462 merged** at re-anchor base; salvage did not rewrite SBW09a paths.

---

## §8 Named successors still false

| Successor | Source PR | Blocked on |
|---|---|---|
| Build World Reference Loop v1 (MC-02a) | #432, #459 | #431 merge |
| MC-02b / candidate-assisted Find existing | #432 | MC-02a |
| Stay-on-Build extraction inspector/summary | #432 | [`HANDOFF-build-stay-on-build-dogfood-after-mc02.md`](../Plans/HANDOFF-build-stay-on-build-dogfood-after-mc02.md) after #431 |
| BLD inspection-truth | #432 | Build inspector milestone |
| Graph Review browse-first committed sessions (§1A) | #444 | [`HANDOFF-graph-review-browse-committed-sessions.md`](../Plans/HANDOFF-graph-review-browse-committed-sessions.md); strict projection |
| Corpus-backed recap catalog (§1B / §2B) | #444 | Same handoff; status vocabulary + populate/refresh design |
| PDF/OCR lineage product gate | #395 | [`HANDOFF-bld09-pdf-ocr-lineage-pilot.md`](../Plans/HANDOFF-bld09-pdf-ocr-lineage-pilot.md) (PREPARED/DRAFT; completed evidence in [`REPORT-build-pdf-lineage-pilot.md`](REPORT-build-pdf-lineage-pilot.md)) |
| DMS generation validation diagnostics | #449 | [`HANDOFF-dms-generation-validation-diagnostics.md`](../Plans/HANDOFF-dms-generation-validation-diagnostics.md) — **only if** R0-A-class opaque `definition_invalid` regresses |
| Frontend extract-promote inspection UI | #433 | Build inspector after #431/#432 |
| SBW09b+ publication resolution / graph proposal | #460 research | Core ledger on merged #462; residual manual live-proof only |
| Publication manual live-proof (operator) | #460 | **PRESERVED** — not yet automated |

---

## §9 Closure protocol

Source PRs (#432, #433, #444, #449, #459, #460) were closed after salvage PR #464 existed remotely, using the §8A template in [`HANDOFF-superseded-open-pr-salvage-and-retirement.md`](../Plans/HANDOFF-superseded-open-pr-salvage-and-retirement.md). Already-CLOSED #231/#395 received ledger comments only. None of the eight were MERGED. Do not close #442. Re-anchor doc refresh does **not** reopen closed source PRs.

---

## §10 Closure evidence (2026-07-31)

Salvage PR: https://github.com/Drakosfire/DungeonMindBuddy/pull/464

| Source PR | State after salvage | Disposition comment |
|---|---|---|
| #231 | CLOSED (pre-existing) | https://github.com/Drakosfire/DungeonMindBuddy/pull/231#issuecomment-5144826464 |
| #395 | CLOSED (pre-existing) | https://github.com/Drakosfire/DungeonMindBuddy/pull/395#issuecomment-5144826729 |
| #432 | CLOSED (not merged) | https://github.com/Drakosfire/DungeonMindBuddy/pull/432#issuecomment-5144826972 |
| #433 | CLOSED (not merged) | https://github.com/Drakosfire/DungeonMindBuddy/pull/433#issuecomment-5144827428 |
| #444 | CLOSED (not merged) | https://github.com/Drakosfire/DungeonMindBuddy/pull/444#issuecomment-5144828122 |
| #449 | CLOSED (not merged) | https://github.com/Drakosfire/DungeonMindBuddy/pull/449#issuecomment-5144828658 |
| #459 | CLOSED (not merged) | https://github.com/Drakosfire/DungeonMindBuddy/pull/459#issuecomment-5144829285 |
| #460 | CLOSED (not merged) | https://github.com/Drakosfire/DungeonMindBuddy/pull/460#issuecomment-5144829762 |

Protected after salvage / at re-anchor: **#431 OPEN**, **#442 OPEN**, **#462 MERGED** (`2fa5b790…`, 2026-08-01), **#463 OPEN**.

Source PRs were closed after salvage PR #464 existed remotely (per authoritative handoff §8B). This re-anchor documentation refresh does not reopen them.
