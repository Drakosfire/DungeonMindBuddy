# Checklist — C1S4 Preplanning Vertical Slice

**Purpose:** Operational tracker for the bounded C1S4 preplanning demo: ingest C1S1-C1S3 into one planner-visible knowledge surface, hold C1S4 out as oracle-only, enrich retrieval/tool calls from the prior-session KB, and later grade synthetic C1S4 prep against the actual C1S4 recap.

**Super-plan amendment:** `Docs/Plans/AMENDMENT-c1s4-preplanning-vertical-slice-reanchor.md`  
**Implementation handoff:** `Docs/Plans/HANDOFF-pr25-c1s4-preplanning-vertical-slice.md`  
**Canonical super-plan:** `Docs/Plans/PLAN-split-corpus-retrieval-to-autonomous-demo.md`  
**Dynamic lexical rollout tracker:** `Docs/Plans/CHECKLIST-dynamic-lexical-retrieval-rollout.md`

---

## Reanchor

- [x] C1S1-C1S3 are the bounded KB input sessions.
- [x] C1S4 is the held-out oracle session.
- [x] The first C1S4 PR is deterministic scaffold only; no live planner, no prep-quality grading.
- [x] C1S13 retrieval falsification remains useful but is no longer the next product-demo blocker.
- [x] Retrieval tuning must not be mixed into the C1S4 scaffold PR.

---

## Phase 0 — Deterministic KB boundary scaffold

**Goal:** prove the KB contains only allowed prior-session evidence before any planner sees it.

- [ ] Create `evals/c1s4_preplanning_vertical_slice/README.md`.
- [ ] Create `evals/c1s4_preplanning_vertical_slice/GATES.md`.
- [ ] Create `gold/kb_policy.json` with:
  - [ ] `campaign_id: longmont-c1`,
  - [ ] included sessions `[1, 2, 3]`,
  - [ ] held-out sessions `[4]`,
  - [ ] included C1S1-C1S3 session-memory JSONL paths,
  - [ ] forbidden C1S4 oracle/source/derivative paths,
  - [ ] actual C1S4 recap path as `oracle_source_relpath`.
- [ ] Create `step0_kb_materialize.py`.
- [ ] Step 0 loads all C1S1-C1S3 records into one manifest/result object.
- [ ] Step 0 fails if any loaded record/source path references Session 4.
- [ ] Step 0 emits record counts by session and route-bearing record counts.
- [ ] Tests prove injected Session 4 records/paths are rejected.

**Verification:**

```bash
uv run pytest tests/test_c1s4_preplanning_vertical_slice.py -q
uv run python evals/c1s4_preplanning_vertical_slice/step0_kb_materialize.py
uv run python scripts/materialize_session_memory.py --all-blessed --check
```

---

## Phase 1 — Retrieval/context-bundle smoke

**Goal:** prove retrieval can operate over the combined C1S1-C1S3 KB and produce a bounded planner-visible context bundle without oracle leakage.

- [ ] Create `gold/preplanning_task.json` with natural C1S4 preplanning ask(s).
- [ ] Create `step1_retrieval_context.py`.
- [ ] Create `preplanning_context_bundle.py`.
- [ ] Step 1 runs deterministic preplanning-oriented queries over the combined KB.
- [ ] Step 1 returns a context bundle with:
  - [ ] schema id,
  - [ ] KB id,
  - [ ] campaign id,
  - [ ] allowed sessions `[1, 2, 3]`,
  - [ ] held-out sessions `[4]`,
  - [ ] retrieved unit ids,
  - [ ] routes,
  - [ ] source paths,
  - [ ] short snippets or `lexical_plain` excerpts,
  - [ ] leakage check fields.
- [ ] Bundle items only reference C1S1-C1S3 source paths/sessions.
- [ ] Tests assert C1S4 is absent from bundle items.

**Verification:**

```bash
uv run pytest tests/test_c1s4_preplanning_vertical_slice.py -q
uv run python evals/c1s4_preplanning_vertical_slice/step1_retrieval_context.py
```

---

## Phase 2 — Oracle target authoring

**Goal:** derive a fair grader from the actual C1S4 recap without making the planner predict unknowable play outcomes.

- [ ] Create `gold/c1s4_oracle_targets.json`.
- [ ] Each target has a forecastability label:
  - [ ] `should_surface_from_prior_context`,
  - [ ] `plausible_pressure`,
  - [ ] `oracle_only_event`,
  - [ ] `must_not_predict`.
- [ ] Each target records C1S4 oracle support, but planner-visible tests never load that support.
- [ ] Targets distinguish prior-continuity coverage from impossible prediction.
- [ ] Tests validate oracle schema and forbidden-path separation.

---

## Phase 3 — Live preplanning planner trace

**Goal:** run the actual planner loop using the C1S1-C1S3 KB and bounded context-bundle tool surface.

- [ ] Add `step2_preplanning_planner_trace.py`.
- [ ] Planner receives a natural C1S4 preplanning ask.
- [ ] Planner can query session memory / context bundle only from the C1S1-C1S3 KB.
- [ ] Tool trace proves no C1S4 read.
- [ ] Output is structured enough for grading:
  - [ ] current campaign state,
  - [ ] unresolved hooks,
  - [ ] likely pressure points,
  - [ ] NPC/location reuse candidates,
  - [ ] uncertainty notes,
  - [ ] grounding references.
- [ ] Run writes sidecar JSON and markdown report.
- [ ] Cost is reported, not hidden.

---

## Phase 4 — Oracle grading

**Goal:** compare synthetic C1S4 prep to the actual C1S4 recap as held-out oracle.

- [ ] Add `step3_grade_against_c1s4_oracle.py`.
- [ ] Grade prior-continuity coverage separately from oracle-only events.
- [ ] Penalize oracle leakage.
- [ ] Penalize unsupported certainty.
- [ ] Reward grounded uncertainty where future events are not knowable.
- [ ] Emit per-target verdicts and aggregate summary.

---

## Phase 5 — Cohort and presentation

**Goal:** once the single-run trace is stable, make it reviewable and repeatable.

- [ ] Add N-run cohort wrapper if stochastic behavior matters.
- [ ] Add cost summary.
- [ ] Add deterministic artifact paths under `artifacts/runs/<date>/`.
- [ ] Optional: add canvas/deep-dive presentation only after JSON artifacts stabilize.

---

## Standing rules

- C1S4 is oracle-only until the grader phase.
- Linked/equivalent routes do not become answer evidence without explicit policy.
- Retrieval improvements are separate PRs from vertical-slice boundary scaffolding.
- Corpus mutation is out of scope for the scaffold.
- Planner live run comes after deterministic boundary proof.
- Prep grading must distinguish forecastable continuity from unknowable player/session events.
