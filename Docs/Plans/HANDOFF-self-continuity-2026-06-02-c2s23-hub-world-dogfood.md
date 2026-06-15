# HANDOFF — Self-continuity: C2S23 hub+world dogfood retrieval landed

**Created:** 2026-06-02 (UTC).  
**Status:** ACTIVE — start a fresh **prime** Cursor agent here. This is not an external-worker PR handoff.  
**Parent context:** Hub-world dogfood retrieval slice implemented, probed live, committed, and pushed to `main`. User captured two corpus-ingest follow-ups (monster/ecology, Mirathorn civic layer) as backlog IDEAs — ingest-first, not scoring-only patches.  
**Plan anchors:** `Docs/Plans/PLAN-c2-live-control-surface-query-pane.md`, `Docs/Plans/ROADMAP-c2s23-authority-activation-and-dogfood.md`, `.cursor/plans/hub_world_retrieval_dogfood_3ce8ec34.plan.md` (all todos complete).

---

## §0 Read This First

The next prime agent's job is **design and prioritization**, not re-implementing hub-world retrieval — that slice is on `main`.

Core questions for the prime agent:

1. **What is the next correctness slice?** Options include: Mirathorn civic hub ingest spec (user-chosen over scoring tweak), wiring dogfood-full as live-control default for Session 23 prep, PR94 instrumented dogfood re-run against manual baseline, or live-control query pane product work.
2. **What is corpus work vs retrieval work?** Live probes proved two failure modes that look similar but need different fixes:
   - **Coverage gap** — terms like "float goat" exist on disk but outside the S21–23 manifest window and are unorganized (monster/ecology backlog).
   - **Retrieval miss** — governance docs are manifest-present but lose to prep/comms noise until hub ingest makes them discoverable (Mirathorn council backlog).
3. **Fix stale workstream docs.** CHECKLIST and ROADMAP still describe PR95 as last green and Step 0 as blocking. Re-verify before quoting; this handoff §1 is the corrected re-anchor until atomic doc-sync lands.

Do **not** treat chat history as canonical. Re-read §1 and run §8 verification before acting.

---

## §1 Current Re-anchor

**Scope:** Workstream (C2 live prep / C2S23 authority activation) + session bridge.

### Git (verified 2026-06-02)

```text
HEAD     9f7ef87452f84b8ba8e1aa8a32f7249cf5c780ce
origin   9f7ef87452f84b8ba8e1aa8a32f7249cf5c780ce  (fetch confirmed — aligned)
Branch   main...origin/main
Message  feat(c2-live-prep): add dogfood-full hub+world retrieval manifest
```

**Untracked (do not commit unless asked):** `evals/c2_live_prep/live/_pytest/` — pytest fixture junk from local runs.

### Retrieval stack on `main` (post-PR95 trajectory)

| Milestone | Status | Evidence |
|-----------|--------|----------|
| Slim C2S23 manifest (43 routes) | ✅ on `main` | `evals/c2_live_prep/benchmarks/c2s23_planning_corpus_manifest.json` |
| Manifest query/admission (PR97+) | ✅ on `main` | `src/live_play/manifest_context_query.py`, PR97 handoff |
| Live query wiring (PR98) | ✅ on `main` | `src/live_play/live_query_context.py` |
| Specificity-aware retrieval (PR100) | ✅ on `main` | `fa2148d` |
| **Dogfood-full manifest (182 routes)** | ✅ **`9f7ef87`** | `c2s23_dogfood_full_manifest.json`, `world_evidence` role |
| Hub-world gold cohort | ✅ **10/10** | `evals/c2_live_prep/artifacts/last_c2s23_hub_world_query_eval.json` |

**Dogfood switch:** `DMB_C2S23_DOGFOOD_DEFAULTS=1` → dogfood-full manifest in live query + telemetry harness. Slim manifest remains default when flag unset.

### Session 22 content state (re-verified on disk)

Step 0 ingest path is **substantially complete** for the canonical played recap:

```text
Session Recaps/Session 22 - Mireward Road and Lysandro.md
→ _normalized/Session 22 - Mireward Road and Lysandro.md
→ _breadcrumbed/Session 22 - Mireward Road and Lysandro.{breadcrumbed,frontmatter_seed}.md
→ _session_memory/Session 22 - Mireward Road and Lysandro.records_meta.{json,jsonl}
```

Earlier staging mis-promotion (`Session 22 - Mireward Gate Lysandro Ironveil.md`) was a known hazard; backlog READY item covers ingest guardrails. Do not assume Step 0 is still blocked without checking `_normalized/` for duplicates.

### Stale canonical docs (contradiction — fix in doc-sync)

| Source | Says | Reality on `main` |
|--------|------|-------------------|
| `CHECKLIST-c2-live-control-surface-query-pane.md` Reanchor block | Last green PR #95; next gate Step 0 + PR96 | PR97–100 + dogfood-full `9f7ef87` landed; S22 memory exists |
| `ROADMAP-c2s23-authority-activation-and-dogfood.md` | PR92 merged; PR93 next | Query/admission + live wiring + dogfood-full shipped |
| `PLAN-c2-live-control-surface-query-pane.md` `last_updated_at` | 2026-05-30 | Does not mention dogfood-full or hub-world cohort |

**Prime agent action:** Run atomic doc-sync (CHECKLIST Reanchor + ROADMAP changelog + PLAN forward sequence) in one edit batch when updating workstream status — do not leave handoff-only truth.

---

## §2 What shipped in `9f7ef87`

**Mission:** Expand live-query retrieval from 43-route slim slice to full dogfood surface without authority collapse.

| Deliverable | Path / contract |
|-------------|-----------------|
| `world_evidence` source role | `reference_tool`; `forbidden_uses: [play_facts]` |
| Dogfood-full manifest builder | `build_dogfood_full_manifest()` in `planning_corpus_manifest.py` |
| Manifest artifact | **182 entries** — slim + C2 hub satellites + full Elderwyld `*.md` |
| Layer-aware scoring | Statblock/timeline boosts; world/hub play-fact penalties |
| Hub-world gold | 10 questions — statblock, dossier, timeline, location, authority traps, xlayer |
| Ingested corpus library | `scripts/build_ingested_corpus_library.py` + canvas |
| Live telemetry artifacts | `evals/c2_live_prep/artifacts/runs/2026-06-02/` |

**Design locks preserved:**

- Slim manifest unchanged (PR97 regression path).
- Elderwyld never admits play facts.
- Campaign hub satellites remain `hub_evidence` / `canon_play`.

---

## §3 Live dogfood evidence (2026-06-02 probes)

All runs: `DMB_C2S23_DOGFOOD_DEFAULTS=1`, `--no-enhancement`. Artifacts under `evals/c2_live_prep/artifacts/runs/2026-06-02/`.

| Question | Artifact | Outcome |
|----------|----------|---------|
| Last thing in Session 22 | `live_query_trace_session22_dogfood_full_rerun.json` | ✅ Correct — Lysandro gate; S22 recaps admitted (slim manifest had wrongly cited S21) |
| Karsemine heard at night (S22) | `live_query_trace_karsemine_heard_dogfood_full_rerun.json` | ✅ Rhythmic sound from north |
| What is a float goat | `live_query_trace_dogfood_float_goat.json` | Honest "no evidence" — **manifest-correct**; term lives in S6 recap, C2 Notes, C1 Bubbles hub (outside window, unorganized) |
| How is Mirathorn Goverened | `live_query_trace_dogfood_mirathorn_governance.json` | **Retrieval miss** — `The City of Mirathorn.md` in manifest but not admitted over prep/comms |
| Why do all Elderwyld cities start with M | `live_query_trace_dogfood_elderwyld_m_cities.json` | ✅ Good — refuses invented etymology; cites Mirathorn/Mireward only |

**No authority traps** on these probes (world files not cited as play proof).

---

## §4 Known gaps (user-validated interpretation)

### A. Monster & ecology — coverage + organization (not critical)

Float goat probe: honest gap is **expected** given S21–23 manifest window and lack of ecology hub structure. User decision: **backlog for ingestion improvements**, not a retrieval scoring patch.

**Backlog:** `Backlog.md` § `[IDEA] Corpus ingest — monster & ecology layer`.

### B. Mirathorn governance — retrieval miss on manifest-present world docs

`The City of Mirathorn.md` contains explicit governance prose ("democratic city-state governed by a council…"). File is in dogfood manifest but ranked below prep comms. User decision: **intentional thoughtful ingest** of Mirathorn city council world docs before tuning scoring.

**Backlog:** `Backlog.md` § `[IDEA] Corpus ingest — Mirathorn city council & governance world docs`.

### C. Out of scope (still deferred)

- C1 sessions 1–17 / early C2 recaps in planning manifest
- `lexical_terms[]` on manifest entries (`Docs/Plans/DESIGN-lexical-evidence-query-language.md` — design doc on `main`, implementation not started)
- Replacing slim manifest as sole production default

---

## §5 Other READY backlog (high-signal, unrelated)

| Entry | Why it matters |
|-------|----------------|
| Ingest guardrail — duplicate normalized + staging-doc quarantine | Session 22 materialization pain; prevents wrong recap canonization |
| Automated breadcrumb frontmatter seed | Stop hand-curating `entity_index` per session |
| Grobnok callback verbatim | Live-play content debt |
| d-table generator workflow | Prep tooling repeatability |

---

## §6 Recommended next priorities (for prime agent to rank)

| Rank | Slice | Rationale |
|------|-------|-----------|
| **1** | **Atomic doc-sync** — CHECKLIST Reanchor, ROADMAP changelog, PLAN `last_updated_at` | Sources currently contradict `main`; re-anchor act incomplete without this |
| **2** | **Mirathorn civic hub ingest spec** | User-flagged; manifest-present docs lose without hub organization; add gold question only after ingest |
| **3** | **PR94 instrumented dogfood re-run** | Roadmap calls for comparing manifest-backed answers vs manual baseline; dogfood-full is now the substrate |
| **4** | **Live-control default manifest** | When does `live_agent_loop` / query pane use dogfood-full for Session 23 prep? |
| **5** | Monster/ecology ingest | Backlog IDEA; not blocking S23 prep |
| **6** | Live Control Query Pane product slice | `PLAN-c2-live-control-surface-query-pane.md` — consumes retrieval orchestration |

**Explicitly not next:** Scoring-only patch for Mirathorn governance or float goat without corpus ingest work first.

---

## §7 Verification commands (§7 contract)

```bash
# Hub-world unit suite
uv run pytest tests/test_planning_corpus_manifest.py \
  tests/test_manifest_context_query.py tests/test_ingested_corpus_library.py -q
# Expected: 71 passed (verified 2026-06-02 on 9f7ef87)

# Hub-world gold cohort (deterministic — no API key)
uv run python -m evals.c2_live_prep.run_c2s23_manifest_context_query \
  --manifest evals/c2_live_prep/benchmarks/c2s23_dogfood_full_manifest.json \
  --questions evals/c2_live_prep/benchmarks/c2s23_hub_world_questions.seed.json \
  --output-dir evals/c2_live_prep/artifacts/runs/2026-06-02

uv run python -m evals.c2_live_prep.evaluate_c2s23_context_packets \
  --gold evals/c2_live_prep/benchmarks/c2s23_hub_world_query_gold.json \
  --packet-dir evals/c2_live_prep/artifacts/runs/2026-06-02 \
  --packet-prefix c2s23_manifest_query_context_packet_ \
  --output evals/c2_live_prep/artifacts/last_c2s23_hub_world_query_eval.json
# Expected: 10/10 passed

# Live query smoke (requires .env / OPENAI_API_KEY)
DMB_C2S23_DOGFOOD_DEFAULTS=1 uv run python -m evals.c2_live_prep.run_live_query_telemetry_trace \
  --question "How is Mirathorn governed?" --no-enhancement \
  --output evals/c2_live_prep/artifacts/runs/2026-06-02/live_query_trace_mirathorn_governance_rerun.json
```

---

## §8 Key file map

| Concern | Path |
|---------|------|
| Dogfood manifest | `evals/c2_live_prep/benchmarks/c2s23_dogfood_full_manifest.json` |
| Slim manifest (regression) | `evals/c2_live_prep/benchmarks/c2s23_planning_corpus_manifest.json` |
| Manifest builder | `src/live_play/planning_corpus_manifest.py` |
| Scoring / admission | `src/live_play/manifest_context_query.py` |
| Live query entry | `src/live_play/live_query_context.py` |
| Hub-world gold | `evals/c2_live_prep/benchmarks/c2s23_hub_world_query_gold.json` |
| Authority decision | `Docs/Design/DECISION-world-campaign-knowledge-hierarchy.md` |
| Mirathorn governance (missed) | `corpus/.../Mirathorn/The City of Mirathorn.md` |
| Mirathorn council | `corpus/.../Mirathorn/City Council Building/The City Council.md` |
| Session recap writer (prior work, landed) | `src/agent/corpus_writer.py`, `.cursor/skills/recap-write/SKILL.md` |

---

## §9 Rubric — carry forward into next slice

1. **Ingest before scoring** when manifest-present world docs lose to prep noise — user rejected scoring-only fix for Mirathorn governance.
2. **Honest "no evidence" is correct** when the term is outside manifest window — do not inflate answers for float-goat-style probes; organize corpus instead.
3. **Slim vs dogfood-full** — keep both artifacts; regression gold on slim if it stays a CI path (S22+enhancement S21 bleed was observed on slim).
4. **Authority discipline held** — hub-world gold includes `auth-world-01` / `auth-hub-01`; live probes showed no world-as-play-fact traps.
5. **Benchmark disk artifacts** — cohort summaries and dated runs under `evals/c2_live_prep/artifacts/`; live traces need working env (sandbox may deny `.env.development`).

---

## §10 Open questions for prime agent + user

1. Promote Mirathorn civic ingest IDEA → READY with a written hub spec, or defer until after PR94 dogfood re-run?
2. Flip live-control server to dogfood-full by default for Session 23 workspace, or keep env-flag only?
3. Session recap writer plan file in IDE shows all todos complete — any productization left, or close plan?
