# Checklist — C1S4 Preplanning Vertical Slice

**Purpose:** Operational tracker for the bounded autonomous demo loop: build a single C1S1–C1S3 campaign-memory KB, use it to enrich a synthetic C1S4 preplanning turn, and grade the result against the existing C1S4 recap as a held-out oracle.

**Super-plan addendum:** `Docs/Plans/ADDENDUM-c1s4-preplanning-vertical-slice.md`  
**Technical design:** `Docs/Design/DESIGN-c1s4-preplanning-vertical-slice.md`  
**Implementation handoff:** `Docs/Plans/HANDOFF-c1s4-preplanning-vertical-slice.md`

---

## Reanchor block

- [x] **Campaign:** Longmont Campaign 1.
- [x] **Planner-visible sessions:** C1S1, C1S2, C1S3 only.
- [x] **Held-out oracle:** C1S4 recap (`Session 4 - The Grotesque Tree of Hempholm.md`).
- [x] **Current repo premise:** C1S1–C1S3 are blessed pilot session-memory sessions; C1S4 exists but is not part of the planner-visible KB.
- [x] **Active next milestone:** M4.0 KB boundary proof.
- [x] **Blocking principle:** prove C1S4 exclusion before adding a live planner turn.

---

## M4.0 — KB boundary proof

**Goal:** Build and verify a deterministic C1S1–C1S3-only KB manifest.

- [ ] Create `evals/c1s4_preplanning_vertical_slice/`.
- [ ] Add `README.md` explaining the vertical slice and oracle/anti-leak model.
- [ ] Add `GATES.md` with M4.0–M4.4 status signposts.
- [ ] Add `gold/kb_policy.json` with:
  - [ ] `campaign_id: longmont-c1`.
  - [ ] `included_sessions: [1, 2, 3]`.
  - [ ] `heldout_session: 4`.
  - [ ] explicit forbidden C1S4 source / normalized / breadcrumbed / session-memory path patterns.
- [ ] Add `step0_kb_materialize.py` that loads only C1S1–C1S3 session-memory JSONL records.
- [ ] Emit a deterministic KB manifest with input paths, hashes, session counts, record counts, and forbidden-path scan results.
- [ ] Add tests that fail if any C1S4 path appears in the planner-visible KB manifest.
- [ ] Add tests that fail if any loaded record has `session_number == 4`.
- [ ] Add tests that fail if the KB loader uses wildcard all-session loading rather than the explicit policy.

**Exit gate:** C1S1–C1S3 records load as a single KB surface, and C1S4 is provably absent.

---

## M4.1 — Retrieval and preplanning context bundle

**Goal:** Query the combined KB and convert retrieved anchors into bounded planner context.

- [ ] Add deterministic retrieval smoke queries against the combined C1S1–C1S3 KB.
- [ ] Use current stable default-equivalence retrieval behavior as the first baseline.
- [ ] Do not depend on open/experimental scene-continuity packet PRs for first pass.
- [ ] Add `preplanning_context_bundle.py`.
- [ ] Bundle fields include:
  - [ ] query text,
  - [ ] retrieved unit IDs,
  - [ ] source recap paths,
  - [ ] routes,
  - [ ] `why_matched`,
  - [ ] bounded snippets or source spans from allowed sessions only,
  - [ ] explicit `allowed_sessions: [1, 2, 3]`,
  - [ ] explicit `heldout_sessions: [4]`.
- [ ] Add a no-oracle-leak scan over bundle paths and text.
- [ ] Keep candidate retrieval candidate-like; do not make `query_session_memory` return arbitrary prose directly.

**Exit gate:** the context bundle is useful for planning and still proves C1S4 exclusion.

---

## M4.2 — C1S4 oracle target seed

**Goal:** Create a grader-only oracle target file derived from the actual C1S4 recap.

- [ ] Add `gold/c1s4_oracle_targets.json`.
- [ ] Record the oracle source path explicitly.
- [ ] Mark the oracle file as grader-only.
- [ ] Categorize targets:
  - [ ] `continuity_anchor` — should be surfaced from C1S1–C1S3 context.
  - [ ] `planning_affordance` — useful prep direction, not exact prediction.
  - [ ] `oracle_only_event` — happened in C1S4 but should not be required as prediction.
  - [ ] `forbidden_leakage_indicator` — exact held-out details that should not appear unless reasonably inferable.
- [ ] For each graded target, include forecastability notes.
- [ ] Do not grade impossible player-choice or improvisational events as required predictions.

**Exit gate:** oracle targets support fair grading without rewarding leakage or impossible prediction.

---

## M4.3 — Live planner synthetic prep turn

**Goal:** Run a natural GM preplanning ask through the planner using only C1S1–C1S3 KB context.

- [ ] Add `gold/preplanning_task.json`.
- [ ] Add `step2_preplanning_planner_trace.py`.
- [ ] Planner receives a natural ask, not bespoke file paths.
- [ ] Planner may call a session-memory query tool.
- [ ] Planner may consume only context bundles authorized by C1S1–C1S3 retrieval.
- [ ] Tool trace must prove no C1S4 read.
- [ ] Output artifact should include:
  - [ ] current campaign state,
  - [ ] unresolved hooks,
  - [ ] likely pressure points,
  - [ ] NPCs and locations to reuse,
  - [ ] scene seed candidates,
  - [ ] uncertainty / do-not-assume notes,
  - [ ] source-backed evidence references.
- [ ] Write sidecar JSON and markdown report.

**Exit gate:** one live planner run produces a grounded synthetic prep artifact with no C1S4 leakage.

---

## M4.4 — Oracle grading and cohort report

**Goal:** Compare synthetic prep to C1S4 oracle targets in a way that rewards grounded prep, not prophecy.

- [ ] Add `grader.py`.
- [ ] Add `step3_grade_against_c1s4_oracle.py`.
- [ ] Grade target coverage by category.
- [ ] Separate evidence coverage from output prose quality.
- [ ] Track oracle leakage separately from missed continuity.
- [ ] Emit closed failure buckets:
  - [ ] `passed`,
  - [ ] `missed_forecastable_continuity`,
  - [ ] `weak_context_support`,
  - [ ] `oracle_only_not_required`,
  - [ ] `possible_oracle_leakage`,
  - [ ] `tool_trace_policy_violation`,
  - [ ] `grader_or_oracle_gap`.
- [ ] Add optional N-run cohort summary once one-shot path is green.
- [ ] Include cost telemetry for live planner runs.

**Exit gate:** the benchmark can explain whether failures are retrieval, context-bundle, planner-output, oracle-design, or leakage failures.

---

## Non-goals for the first implementation PR

- [ ] Do not build a vector database.
- [ ] Do not introduce a graph store.
- [ ] Do not ingest C1S4 into the planner-visible KB.
- [ ] Do not require scene-beat packet mode.
- [ ] Do not modify existing C1S13 retrieval gold.
- [ ] Do not tune alias saturation or promotion criteria.
- [ ] Do not add the live planner turn before M4.0 is green.

---

## Suggested first PR verification commands

```bash
uv run python scripts/materialize_session_memory.py --all-blessed --check
uv run pytest tests/test_c1s4_preplanning_vertical_slice_step0.py -q
uv run python -m evals.c1s4_preplanning_vertical_slice.step0_kb_materialize --check
```

Add exact command names after the slice files exist.
