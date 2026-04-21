# EXPERIMENT — Session recap timeline append (Stage 2)

**Parent:** Session recap ingest (Stage 1) — [EXPERIMENT-Session-Recap-Ingest-Benchmark.md](EXPERIMENT-Session-Recap-Ingest-Benchmark.md) (B2 origin: §5.2, lines ~139–144: Lysandra timeline row “exact-text after split-on-`\n`” in the **original** Scope-B contract).  
**Slice root:** `evals/session_recap_timeline_append_vertical_slice/`

This benchmark proves **downstream corpus enrichment** after recap ingest: the planner reads the **already committed** recap and appends a **Session 20** row to `captain_lysandra_ironveil/timeline.md` via **`append_timeline_row`** (same two-phase contract as `write_corpus_file`).

---

## Design choices (normative)

### A. Grading mode — **Hybrid**

- **Cells 1 + 3 (session + recap pointer):** strict shape — session token `**20**`; third column must be a single backticked path whose basename is `Session 20 - Recap.md` (full corpus-relative path allowed so we do not fight `append_timeline_row`’s normalized `recap_path` argument).
- **Cell 2 (beat):** non-empty prose with **order-independent** regex anchors: must mention **Lysandra** and at least one recap-grounded keyword (e.g. Mossford, forest, camp, rocky-talkie, cult/tower sketch, meat, antidote/charm, Sara, etc.).

**Why not byte-equal?** Model-authored beat prose varies; byte-equal would couple the gate to one phrasing and create false fails on equivalent summaries. **Why not pure schema?** We still want evidence the beat is **about this session’s Lysandra arc**, not a generic filler line.

### B. User message — **verbatim** (gold JSON)

Stored in `evals/session_recap_timeline_append_vertical_slice/gold/timeline_append_lysandra_session20.json` under `input.user_message`. It names the recap path, requires reading existing `timeline.md` for format, **`append_timeline_row` only** (two-phase), forbids recap assembly tools, and requires the **universal** `planner_turn_output` envelope (no `recap_write`).

### C. Skill choice — **Option (b): skill-less turn**

- **`active_skill_id=None`** → universal JSON schema; no `recap-write` dispatch guard.
- **Rationale:** `recap-write`’s dispatch guard allowlist is `recent_recaps ∪ prep_doc_path` and **does not** include NPC `timeline.md` or arbitrary recap paths for a “follow-up” turn. Extending that skill would widen blast radius. A dedicated minimal skill (option a) was viable but unnecessary because the planner already supports writes with the universal envelope when `include_write_tools=True`.

Instruction nuance: the runner appends a short **eval-only suffix** after `load_or_build_planner_instructions` so the global `corpus_session_planner.py` recap-ingest paragraph (which assumes `get_recap_context` first) does not mislead the model — **without** editing the shared prompt file.

### D. NPC scope — **Lysandra-only (first cohort)**

First live cohort targets **Captain Lysandra Ironveil** (`captain_lysandra_ironveil`), the canonical Campaign 2 hub with a rich existing `timeline.md`.

**Note:** A glob of `Longmont Campaign/Campaign 2/NPCs/**/timeline.md` finds **multiple** hubs with timelines (not only Lysandra). The first cohort is still **Lysandra-only** by scenario design; diversification is explicitly **post-pass** enumeration.

---

## Gates

| ID | Description |
|----|-------------|
| T1 | `append_timeline_row`: at least one `dry_run=true` preview and one `dry_run=false` commit; first call is preview; last is commit; last commit response `ok=true`, `phase=committed`. |
| T2 | No `write_corpus_file` in `tool_trace`. |
| T3 | No `assemble_recap_draft` or `build_recap_write_payload` in `tool_trace`. |
| T4 | `timeline.md` (graded path) contains a table row for session **20** satisfying the **hybrid** rubric (§A). |
| T5 | Pre-state builder: recap exists at the committed path; session **20** row absent before the run. |

**Pass:** T1–T4 true for a live run; T5 verified offline.

---

## Run protocol

1. **Offline:** `uv run pytest tests/test_timeline_append_grader.py tests/test_timeline_append_pre_state.py -q`
2. **Pre-state spot-check:** `step1_timeline_append_run.py --print-root` then assert recap file exists and `timeline.md` has no `| **20** |` row.
3. **Live cohort:** `step1_timeline_append_run.py --n 3 --model gpt-5.4-mini` with `DUNGEONMIND_PLANNER_ALLOW_WRITES=1`.
4. **Budget:** stop early if cumulative live spend exceeds **$1.50** with **≤1** pass (harness guard); hard cap **$2.00** total.

---

## Artifacts

Per run: `timeline_append--<scenario>--<model>--PASS|FAIL--1turn--<utc>--runNNN.{md,json}` under `evals/session_recap_timeline_append_vertical_slice/artifacts/runs/<YYYY-MM-DD>/`.

Cohort summary: `timeline_append_summary--<model>--N<n>--<utc>.{md,json}`.

---

## Relationship to Stage 1

- Does **not** run `assemble_recap_draft` or `write_corpus_file` for the recap.
- Does **not** modify `evals/session_recap_ingest_vertical_slice/` or Stage-1 STATUS/EXPERIMENT docs.
- **Stage-1 recap bytes** are pinned in this slice’s `gold/Session 20 - Recap.md` so pre-state is reproducible even if the live corpus recap later diverges.
