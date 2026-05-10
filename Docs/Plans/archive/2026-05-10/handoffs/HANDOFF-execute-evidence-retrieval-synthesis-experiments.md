# HANDOFF: Execute evidence retrieval & synthesis experiments

**Date:** 2026-04-03
**Status:** Ready for execution
**Prerequisite reading:**

- `Docs/Plans/archive/2026-05-09/reports/REPORT-evidence-gap-phases-0-6-findings.md` — what we know
- `Docs/Plans/HYPOTHESES-evidence-retrieval-synthesis-improvements.md` — what we want to test
- `evals/mirathorn_vertical_slice/output/evidence_gap_phase_ledger.json` — phase-by-phase metrics

---

## 1. Current best baseline

**Phase 3 (adaptive top-k)** is the high-water mark on semantic pass rate:


| Metric              | Phase 3  | Phase 6 (latest) |
| ------------------- | -------- | ---------------- |
| semantic pass       | **9/15** | 8/15             |
| evidence_gap        | 13       | 9                |
| retriever_gap       | 8        | 8                |
| synthesis_gap       | 5        | **12**           |
| hit                 | **34**   | 31               |
| avg context_support | 0.739    | 0.706            |
| fail_stale          | 0        | 0                |


**Key tension:** Phases 4-6 reduced evidence_gap (20 → 9) but inflated synthesis_gap (2 → 12). More tokens reach context, but the LLM fails to surface them. The two bottlenecks must be addressed in concert.

---

## 2. Experiment infrastructure

### How to run a benchmark

```bash
cd /home/drakosfire/Projects/DungeonOverMind/DungeonMindBuddy

# Base template — fill in ENV_VARS per experiment
ENV_VARS \
DMB_WRITE_COUNCIL_ROOM_QUESTION_SET_ARTIFACTS=1 \
DMB_PHASE_WRITE_LEDGER=1 \
DMB_PHASE_NAME="exp_NAME" \
DMB_PHASE_HYPOTHESIS="One-sentence hypothesis." \
uv run python evals/mirathorn_vertical_slice/run_council_room_question_set.py
```

### Artifacts produced per run


| Artifact              | Path                                                                   |
| --------------------- | ---------------------------------------------------------------------- |
| Full JSON summary     | `evals/mirathorn_vertical_slice/output/council_room_question_set.json` |
| Human-readable report | `evals/mirathorn_vertical_slice/output/council_room_question_set.md`   |
| Per-question trace    | `evals/mirathorn_vertical_slice/output/council_room_trace.jsonl`       |
| Ledger append         | `evals/mirathorn_vertical_slice/output/evidence_gap_phase_ledger.json` |


### Pre-registered metrics (record for every experiment)


| Metric                          | Source field in JSON                             |
| ------------------------------- | ------------------------------------------------ |
| semantic pass_updated           | `overall_semantic.pass_updated`                  |
| fail_stale                      | `overall_semantic.fail_stale`                    |
| evidence_gap                    | `stage_loss_report.overall_counts.evidence_gap`  |
| retriever_gap                   | `stage_loss_report.overall_counts.retriever_gap` |
| synthesis_gap                   | `stage_loss_report.overall_counts.synthesis_gap` |
| hit                             | `stage_loss_report.overall_counts.hit`           |
| avg context_support             | `overall_context_support.avg_support_ratio`      |
| avg context_chars               | per-question trace mean                          |
| failure_surface pass/retr/synth | `overall_failure_surface`                        |


### Rollback rule

If any experiment **regresses semantic pass below 7/15** or **introduces fail_stale > 0**, it fails immediately. Record the result in the ledger, note it as a negative finding, and move on.

---

## 3. Experiment waves

Experiments are grouped by required effort. Execute waves in order; each wave's results inform later waves.

---

### Wave 1: Parameter sweeps (no code changes)

These experiments use only env-var configuration. Each takes ~5 minutes to run.

#### Exp 1A — Phase 3 stability check (3 runs)

**Hypothesis (B2):** Phase 3's 9/15 semantic pass is stable, not a stochastic outlier.

Run Phase 3 config **three times** and record semantic pass for each. If all three hit ≥ 8/15 and at least two hit 9/15, Phase 3 is the stable retrieval baseline.

```bash
# Run 1
DMB_EVIDENCE_FIRST=1 \
DMB_EVIDENCE_ADAPTIVE_TOP_K=1 \
DMB_EVIDENCE_ADAPTIVE_TOP_K_MAX=48 \
DMB_EVIDENCE_DENSITY_THRESHOLD=0.3 \
DMB_WRITE_COUNCIL_ROOM_QUESTION_SET_ARTIFACTS=1 \
DMB_PHASE_WRITE_LEDGER=1 \
DMB_PHASE_NAME="exp1a_phase3_stability_run1" \
DMB_PHASE_HYPOTHESIS="Phase 3 stability check run 1 of 3." \
uv run python evals/mirathorn_vertical_slice/run_council_room_question_set.py
```

Repeat with `run2`, `run3` in the phase name. **Save a copy** of `council_room_question_set.json` after each run (e.g., `cp ...json ...json.exp1a_run1`).

**Pass:** ≥ 2/3 runs hit 9/15 semantic pass, zero fail_stale.
**Fail:** Median < 8/15 → Phase 3 advantage is noise.

#### Exp 1B — Tighter adaptive top-k (post doc-gating proxy)

**Hypothesis (B1):** Lowering `adaptive_top_k_max` from 48 → 32 reduces dilution and improves synthesis_gap without major evidence_gap regression.

```bash
DMB_EVIDENCE_FIRST=1 \
DMB_EVIDENCE_ADAPTIVE_TOP_K=1 \
DMB_EVIDENCE_ADAPTIVE_TOP_K_MAX=32 \
DMB_EVIDENCE_DENSITY_THRESHOLD=0.3 \
DMB_WRITE_COUNCIL_ROOM_QUESTION_SET_ARTIFACTS=1 \
DMB_PHASE_WRITE_LEDGER=1 \
DMB_PHASE_NAME="exp1b_tighter_topk_32" \
DMB_PHASE_HYPOTHESIS="Lower adaptive max (32) should reduce dilution and synthesis_gap." \
uv run python evals/mirathorn_vertical_slice/run_council_room_question_set.py
```

**Pass:** synthesis_gap < Phase 3's 5; evidence_gap ≤ 15; semantic pass ≥ 8.
**Fail:** evidence_gap > 15 (too aggressive) or semantic pass < 7.

#### Exp 1C — Stricter density threshold

**Hypothesis (B1 variant):** Raising density threshold from 0.3 → 0.5 prunes low-quality tail of adaptive expansion.

```bash
DMB_EVIDENCE_FIRST=1 \
DMB_EVIDENCE_ADAPTIVE_TOP_K=1 \
DMB_EVIDENCE_ADAPTIVE_TOP_K_MAX=48 \
DMB_EVIDENCE_DENSITY_THRESHOLD=0.5 \
DMB_WRITE_COUNCIL_ROOM_QUESTION_SET_ARTIFACTS=1 \
DMB_PHASE_WRITE_LEDGER=1 \
DMB_PHASE_NAME="exp1c_density_0_5" \
DMB_PHASE_HYPOTHESIS="Stricter density (0.5) prunes dilution tail from adaptive top-k." \
uv run python evals/mirathorn_vertical_slice/run_council_room_question_set.py
```

#### Exp 1D — Compact verbosity on Phase 3 retrieval

**Hypothesis (C3):** `compact` verbosity (80-140 words) forces the LLM to be more selective, reducing hedge/drift that causes synthesis_gap. Combined with Phase 3 retrieval (best recall).

```bash
DMB_EVIDENCE_FIRST=1 \
DMB_EVIDENCE_ADAPTIVE_TOP_K=1 \
DMB_EVIDENCE_ADAPTIVE_TOP_K_MAX=48 \
DMB_EVIDENCE_DENSITY_THRESHOLD=0.3 \
DMB_SYNTHESIS_PROFILE=mirathorn \
DMB_SYNTHESIS_VERBOSITY=compact \
DMB_WRITE_COUNCIL_ROOM_QUESTION_SET_ARTIFACTS=1 \
DMB_PHASE_WRITE_LEDGER=1 \
DMB_PHASE_NAME="exp1d_phase3_compact" \
DMB_PHASE_HYPOTHESIS="Compact verbosity on Phase 3 retrieval should reduce synthesis_gap." \
uv run python evals/mirathorn_vertical_slice/run_council_room_question_set.py
```

**Pass:** synthesis_gap < 5 AND semantic pass ≥ 8.
**Watch:** If semantic pass drops to 7, the compact constraint may be too tight.

#### Exp 1E — Default verbosity on Phase 3 retrieval (no verbose, no compact)

**Hypothesis (C3 control):** The `verbose` mode (180-320 words) added in Phase 5 may itself be causing synthesis_gap inflation by encouraging the LLM to pad. Default mode (100-200 words) is the middle ground.

```bash
DMB_EVIDENCE_FIRST=1 \
DMB_EVIDENCE_ADAPTIVE_TOP_K=1 \
DMB_EVIDENCE_ADAPTIVE_TOP_K_MAX=48 \
DMB_EVIDENCE_DENSITY_THRESHOLD=0.3 \
DMB_SYNTHESIS_PROFILE=mirathorn \
DMB_WRITE_COUNCIL_ROOM_QUESTION_SET_ARTIFACTS=1 \
DMB_PHASE_WRITE_LEDGER=1 \
DMB_PHASE_NAME="exp1e_phase3_default_verbosity" \
DMB_PHASE_HYPOTHESIS="Default verbosity (no verbose flag) on Phase 3 to isolate verbosity effect." \
uv run python evals/mirathorn_vertical_slice/run_council_room_question_set.py
```

#### Exp 1F — Context budget squeeze

**Hypothesis (C3 variant):** Halving `context_max_chars` from 20000 → 10000 forces harder pruning and reduces noise the LLM must navigate.

```bash
DMB_EVIDENCE_FIRST=1 \
DMB_EVIDENCE_ADAPTIVE_TOP_K=1 \
DMB_EVIDENCE_ADAPTIVE_TOP_K_MAX=48 \
DMB_EVIDENCE_DENSITY_THRESHOLD=0.3 \
DMB_CONTEXT_MAX_CHARS=10000 \
DMB_WRITE_COUNCIL_ROOM_QUESTION_SET_ARTIFACTS=1 \
DMB_PHASE_WRITE_LEDGER=1 \
DMB_PHASE_NAME="exp1f_context_budget_10k" \
DMB_PHASE_HYPOTHESIS="Halving context budget (10k chars) forces tighter pruning, may improve synthesis." \
uv run python evals/mirathorn_vertical_slice/run_council_room_question_set.py
```

**Pass:** synthesis_gap ≤ 5 with semantic pass ≥ 8.
**Watch:** evidence_gap or retriever_gap jumps → budget is too tight, starving recall.

#### Exp 1G — Enable claim verification

**Hypothesis (E1):** Claim verification catches hallucinations that pass must-hit tests, adding a second quality axis.

```bash
DMB_EVIDENCE_FIRST=1 \
DMB_EVIDENCE_ADAPTIVE_TOP_K=1 \
DMB_EVIDENCE_ADAPTIVE_TOP_K_MAX=48 \
DMB_EVIDENCE_DENSITY_THRESHOLD=0.3 \
DMB_CLAIM_VERIFICATION=1 \
DMB_WRITE_COUNCIL_ROOM_QUESTION_SET_ARTIFACTS=1 \
DMB_PHASE_WRITE_LEDGER=1 \
DMB_PHASE_NAME="exp1g_claim_verification" \
DMB_PHASE_HYPOTHESIS="Claim verification as second axis catches hallucinations missed by token tests." \
uv run python evals/mirathorn_vertical_slice/run_council_room_question_set.py
```

**Output:** Check `overall_accuracy` in the JSON. This experiment is diagnostic — it doesn't change answers, just adds a measurement. Note any questions where token-pass but claim-fail.

---

### Wave 2: Synthesis prompt changes (light code edits)

These experiments modify `src/agent/synthesis.py` only. **Back up the original before starting.**

#### Exp 2A — Two-step synthesis (extract then answer)

**Hypothesis (C1):** A two-step approach — first extract bullet-point claims from context, then answer from those claims — reduces synthesis_gap by forcing the LLM to explicitly notice must-hit facts before composing a narrative.

**Implementation:** In `src/agent/synthesis.py`, modify `synthesize_answer_async` to make **two LLM calls**:

1. **Extraction call:** System prompt instructs the LLM to extract all factual claims from the context as a numbered list. No answering.
2. **Answer call:** System prompt (existing `SYSTEM_PROMPT`) receives the question + the extracted claims (not the raw context).

```python
# New extraction prompt (add to synthesis.py)
EXTRACTION_PROMPT = """You are a factual extraction assistant.
Given a block of campaign context, extract every distinct factual claim as a numbered bullet list.
Include entity names, specific details, exact phrases, and terminal outcomes.
Do NOT answer any question. Do NOT summarize. Just list facts.
Output ONLY the numbered list."""
```

**File:** `src/agent/synthesis.py`
**Changes:**

- Add `EXTRACTION_PROMPT` constant.
- Add `--two-step-synthesis` CLI flag in `src/cli.py` (or use env var `DMB_TWO_STEP_SYNTHESIS=1`).
- When enabled, `synthesize_answer_async` makes two calls: extract → answer.
- Log extracted claims in `_last_ask_meta` for trace inspection.

**Run:**

```bash
DMB_EVIDENCE_FIRST=1 \
DMB_EVIDENCE_ADAPTIVE_TOP_K=1 \
DMB_EVIDENCE_ADAPTIVE_TOP_K_MAX=48 \
DMB_EVIDENCE_DENSITY_THRESHOLD=0.3 \
DMB_TWO_STEP_SYNTHESIS=1 \
DMB_WRITE_COUNCIL_ROOM_QUESTION_SET_ARTIFACTS=1 \
DMB_PHASE_WRITE_LEDGER=1 \
DMB_PHASE_NAME="exp2a_two_step_synthesis" \
DMB_PHASE_HYPOTHESIS="Two-step extract-then-answer should reduce synthesis_gap." \
uv run python evals/mirathorn_vertical_slice/run_council_room_question_set.py
```

**Pass:** synthesis_gap ≤ 5 AND semantic pass ≥ 9.
**Watch:** Latency doubles (two LLM calls). Token cost increases. If synthesis_gap drops but semantic pass doesn't improve, the extraction step is working but the answering step still loses tokens.

#### Exp 2B — Explicit citation structure in prompt

**Hypothesis (C2):** Adding an "Evidence:" section requirement and penalizing unsourced claims aligns output with core_claims.

**Implementation:** Append to `SYSTEM_PROMPT`:

```
Answer structure:
1. TL;DR: (1-2 sentences)
2. Evidence: bullet list of grounded facts from context, each citing the entity name
3. Analysis: (optional) only if facts conflict or require interpretation

Rule: Every claim in TL;DR must have a corresponding Evidence bullet. Do not state anything without a grounded source.
```

**File:** `src/agent/synthesis.py` — modify `SYSTEM_PROMPT` or add as a new profile appendix.
**Run with Phase 3 retrieval + default verbosity.**

**Pass:** embedding mean > 0.65 (up from 0.626); synthesis_gap ≤ 5.

---

### Wave 3: Retrieval algorithm changes (moderate code)

These require changes to `src/agent/evidence_retriever.py`.

#### Exp 3A — Per-seed neighbor budgeting

**Hypothesis (B3 variant / H3 from original handoff):** The global neighbor budget lets top seeds starve lower seeds. Per-seed allocation ensures diversity.

**Implementation:** In `retrieve_relevant_evidence`, replace the global `neighbor_budget` loop with:

```python
per_seed_budget = max(1, neighbor_budget // max(1, len(seeded)))
for seed in seeded:
    seed_expanded = 0
    rows = by_doc.get(seed.document_id, [])
    for source_order, evidence_id in rows:
        if evidence_id in selected_ids:
            continue
        if abs(source_order - seed.source_order_index) > neighbor_window:
            continue
        selected_ids.add(evidence_id)
        expanded += 1
        seed_expanded += 1
        if seed_expanded >= per_seed_budget:
            break
```

**File:** `src/agent/evidence_retriever.py:262-279`
**Run with Phase 3 env vars.**

**Pass:** evidence_gap ≤ 11 (improvement over Phase 3's 13) with semantic pass ≥ 8.

#### Exp 3B — Two-pass evidence retrieval (entity-informed second pass)

**Hypothesis (C from original handoff):** After initial evidence → entity ranking, do a second evidence pass using the top entities' provenance to pull additional evidence chunks.

**Implementation:**

1. First pass: existing `retrieve_relevant_evidence`.
2. `rank_entities_by_evidence_overlap` → get top N entities.
3. Collect `provenance_evidence_ids` from those entities' attributes in the projection.
4. Union provenance IDs with first-pass selected IDs.
5. Re-filter projection with the expanded evidence set.

**File:** `src/cli.py` — add second pass logic after the fuse step.
**Gated by `DMB_EVIDENCE_TWO_PASS=1` env var.**

**Pass:** evidence_gap ≤ 8 with semantic pass ≥ 8.

#### Exp 3C — Per-document chunk quotas

**Hypothesis (B3):** Capping chunks per document (e.g., max 12 per doc) prevents single-source dominance.

**Implementation:** After seed+neighbor selection in `retrieve_relevant_evidence`, add:

```python
doc_quota = int(os.environ.get("DMB_EVIDENCE_DOC_QUOTA", "0"))
if doc_quota > 0:
    doc_counts: dict[str, int] = {}
    quota_filtered = []
    for eid in selected_ordered:
        doc_id = evidence_doc_map.get(eid, "")
        doc_counts[doc_id] = doc_counts.get(doc_id, 0) + 1
        if doc_counts[doc_id] <= doc_quota:
            quota_filtered.append(eid)
    selected_ordered = quota_filtered
```

**Run with `DMB_EVIDENCE_DOC_QUOTA=12`.**

**Pass:** Better token diversity on multi-source questions (roster, council); watch for depth loss on single-doc questions.

---

### Wave 4: Document-level LLM planner & embedding rerank

#### Exp 4A — LLM document planner (pre-filter before chunk retrieval)

**Hypothesis (A2):** Presenting a compact document roster (id, title, type, source class, chunk count, and an LLM-generated summary) to a cheap LLM lets it select which documents to search *before* chunk-level BM25 scoring. This pre-filters the candidate pool, reducing noise and improving evidence recall on the chunks that survive.

**Why this matters now:**

The full corpus has **130 source markdown files** producing **65-120 unique ingested documents** (depending on the store) with up to **5299 evidence units**. The benchmark `phase_d_store` is a 6-document slice, but this experiment must be designed for the **full-corpus scale**. At 120 documents, BM25 scoring all campaign-eligible chunks is expensive and noisy — a document planner that narrows the pool to 3-8 relevant documents before chunk retrieval could eliminate 90%+ of candidates.

**Corpus structure (representative):**

```
Elderwyld/
  Cities and Towns/Mirathorn/        ← city reference, council building, sewers, academy, wolf manor
  Cities and Towns/Mossford/         ← separate town with 12+ location dossiers
  Events/Festival of Expansion/      ← multi-day event with sub-documents
  Events/Hearthbound Bake-Off/       ← standalone event
  Migrating Forest/Branchbound/      ← separate region/culture
  Shephards Flock/                   ← faction with statblocks
  Inns and Shops/                    ← location details
Longmont Campaign/
  Campaign 1/Session Recaps/         ← per-session play recaps
  Campaign 2/Session Recaps + Prep/  ← second campaign arc
  NPCs/, Character Docs/             ← character dossiers
  Homebrew Items/                    ← custom items
```

**Full-corpus stores available for testing:**


| Store                                                      | Docs | Evidence units | Notes                            |
| ---------------------------------------------------------- | ---- | -------------- | -------------------------------- |
| `out/stores/dungeonbuddy_store_escalation_full_mini_to_54` | 120  | 5299           | Most complete                    |
| `out/stores/dungeonbuddy_store_cheapest_full`              | 118  | 3867           | Full coverage, smaller chunks    |
| `out/stores/dungeonbuddy_store_nano_full`                  | 65   | 2526           | Partial coverage                 |
| `evals/mirathorn_vertical_slice/output/phase_d_store`      | 6    | 1313           | Benchmark slice (fast iteration) |


**Why this changes the design:** With 6 docs the roster fits in a few lines. With 120 docs the roster is substantial — but still far smaller than 5299 evidence chunks. The document planner prompt must handle a multi-page roster efficiently. Options:

- **Roster with one-line summaries:** ~120 lines, ~3-5K tokens — fits easily in a cheap model's context.
- **Hierarchical roster:** Group by directory path (city → building → room), letting the LLM navigate the hierarchy. Better for very large corpora.
- **Two-stage:** Hard metadata filters first (campaign_id, canon_layer), then LLM over the surviving subset.

**What retrieval currently selects** (from `whole_document_if_golden_analysis.json` on `phase_d_store`): most questions touch 4-6 of the 6 available documents. At full-corpus scale, the ratio of relevant-to-irrelevant documents is much more extreme — a question about the council room battle shouldn't search through Mossford location dossiers, Festival of Expansion events, or Branchbound culture packs.

**Implementation — new module `src/agent/document_planner.py`:**

Follow the same architecture as `src/agent/query_planner.py` (entity planner). Key components:

1. `**build_document_roster(store)`** — Build a compact text roster from store evidence units. Each evidence unit already carries `document_id`, `document_title`, `document_type`, `source_class`, `canon_layer`, `campaign_id`, and `section_path`. Aggregate per document:
  ```
   [doc_the_council_room] The Council Room (world_reference, seed_reference, world, 20 chunks)
     Path: Cities and Towns > Mirathorn > City Council Building
     Sections: Council Room Description, Details to Consider for Play
     Summary: Physical description of the council chamber — arched ceilings, chandelier, seating.

   [doc_battle_with_the_wolf_and_aftermath] Battle with The Wolf and Aftermath (world_reference, seed_reference, world, 124 chunks)
     Path: Cities and Towns > Mirathorn > City Council Building
     Sections: Battle with The Wolf, The Wolf's Escape, Branching Paths After the Fight
     Summary: Combat encounter with The Wolf in the council chamber, aftermath, consequences.
  ```
   **At full-corpus scale (120 docs, ~3-5K tokens for the roster):** This still fits comfortably in a cheap model's context window. The roster is structured metadata, not raw text — 120 documents × ~30 tokens each ≈ 3600 tokens.
   **Summary sources (choose one per deployment, configurable):**
  - **Option A (no LLM cost):** First 1-2 sentences of the document's first evidence unit text, plus top 5 unique `section_path[0]` entries. Fast, deterministic, free.
  - **Option B (one-time LLM cost):** Generate a 1-2 sentence summary per document, cache in `store_dir/document_summaries.json`. Regenerate only when document chunk count changes. Better for ambiguous titles.
  - **Option C (hybrid):** Use the corpus directory path (e.g., `Elderwyld/Cities and Towns/Mirathorn/Sewers`) as a hierarchical location signal alongside Option A summaries. The directory structure already encodes topical grouping.
   Start with Option A + directory path (Option C). Graduate to Option B if the planner struggles with terse metadata.
2. `**DOCUMENT_PLANNER_PROMPT`** — System prompt for the LLM:
  ```
   You are a document selector for a tabletop RPG knowledge graph.

   You receive a GM's question and a roster of source documents with metadata.
   Select which documents are likely to contain information needed to answer the question.

   ## Document roster format
   Each entry: [doc_id] Title (type, source_class, canon_layer, N chunks)
     Path: directory hierarchy showing topical grouping
     Sections: top section headings from the document
     Summary: brief description or first lines

   ## Rules
   - Select 2-8 documents depending on question scope. Fewer is better for focused questions.
   - Always include documents whose title, path, or summary mentions entities/events/locations from the question.
   - Include session recap documents if the question asks about what happened in play (observed events).
   - Include world reference documents if the question asks about locations, NPCs, or world details.
   - Use the directory path to identify topical relevance (e.g., a question about Mirathorn sewers → docs under Cities and Towns/Mirathorn/Sewers/).
   - If uncertain, include more rather than fewer — false negatives are worse than false positives here.
   - For broad questions ("tell me about the campaign"), select broadly across categories.
   - For narrow questions ("what happened to The Wolf?"), select tightly.

   Return ONLY valid JSON:
   {
     "selected_document_ids": ["doc_foo", "doc_bar"],
     "reasoning": "one sentence"
   }
  ```
3. `**plan_documents(question, roster, candidate_doc_ids, model=None)**` — Makes the LLM call, parses JSON, validates IDs against candidates. Falls back to full candidate set on error (same pattern as query planner).
4. `**DocumentPlan` dataclass:**
  ```python
   @dataclass(frozen=True)
   class DocumentPlan:
       selected_document_ids: list[str]
       reasoning: str
       model: str
       duration_ms: int
       fallback: bool = False
  ```

**Integration in `src/cli.py`:**

Insert document planning as the **first step** when `--document-planner` (or `DMB_DOCUMENT_PLANNER=1`) is enabled:

```
1. Build document roster from store.evidence_units
2. LLM selects relevant document IDs → DocumentPlan
3. Pass plan.selected_document_ids as scope_document_ids to retrieve_relevant_evidence()
4. Rest of pipeline unchanged
```

The `scope_document_ids` parameter already exists on `retrieve_relevant_evidence()` — it pre-filters to in-scope documents when non-empty. The document planner populates this parameter instead of leaving it empty or using a static list.

**Wire in the eval runner** (`run_council_room_question_set.py`):

Add env vars:

```python
DOCUMENT_PLANNER_ENV = "DMB_DOCUMENT_PLANNER"
DOCUMENT_PLANNER_MODEL_ENV = "DMB_DOCUMENT_PLANNER_MODEL"
```

When `DMB_DOCUMENT_PLANNER=1`, add `--document-planner` to the CLI command. Capture `document_planner_meta` in trace rows (selected docs, reasoning, duration_ms, fallback).

**Model:** Use `query_planning` action from `MODEL_POLICY.json` (resolves to `gpt-5.4-nano`). With a 6-document roster, the input is < 500 tokens — extremely cheap.

**Run:**

```bash
DMB_EVIDENCE_FIRST=1 \
DMB_EVIDENCE_ADAPTIVE_TOP_K=1 \
DMB_EVIDENCE_ADAPTIVE_TOP_K_MAX=48 \
DMB_EVIDENCE_DENSITY_THRESHOLD=0.3 \
DMB_DOCUMENT_PLANNER=1 \
DMB_WRITE_COUNCIL_ROOM_QUESTION_SET_ARTIFACTS=1 \
DMB_PHASE_WRITE_LEDGER=1 \
DMB_PHASE_NAME="exp4a_document_planner" \
DMB_PHASE_HYPOTHESIS="LLM document planner pre-filters chunk pool, reducing noise for BM25 scoring." \
uv run python evals/mirathorn_vertical_slice/run_council_room_question_set.py
```

**Testing strategy — two stores:**

1. **Fast iteration on `phase_d_store`** (6 docs, 1313 chunks): validate the planner makes sensible selections against the benchmark gold set. The planner should select 2-4 of 6 docs per question.
2. **Full-corpus validation on `dungeonbuddy_store_escalation_full_mini_to_54`** (120 docs, 5299 chunks): validate the planner scales — the roster stays under 5K tokens, the LLM correctly ignores irrelevant regions (Mossford, Branchbound, Festival events for council-room questions), and latency stays acceptable.

For the full-corpus run, the benchmark questions are still council-room focused, so the planner should aggressively filter to Mirathorn/City Council Building docs + campaign recaps. This is a strong test of precision.

**Pass criteria:**

- evidence_gap ≤ 10 (same or better than Phase 4-6)
- semantic pass ≥ 9 (matches Phase 3 high-water mark)
- avg context_chars decreases (less noise)
- No false negatives: every question's must-hit tokens live in a planner-selected document. **Verify this by cross-referencing the trace's selected_document_ids against the gold must-hit token locations.**
- On full-corpus store: planner selects < 15 docs (out of 120) for focused questions

**Fail criteria:**

- Planner excludes a document containing must-hit tokens → evidence_gap spikes
- Fallback rate > 20% (planner unreliable)
- Full-corpus roster exceeds model context window (unlikely at ~3-5K tokens, but verify)

**Diagnostic:** After the run, build a **per-question doc selection audit table**:


| Question | Planner selected docs | Docs containing must-hit tokens | Missed docs? |
| -------- | --------------------- | ------------------------------- | ------------ |


If the planner misses docs, examine its reasoning and consider whether Option B (LLM-generated summaries) would fix the gap.

**Key advantage over existing `scope_document_ids`:** Currently scope docs are statically provided or empty. The document planner dynamically selects docs per question, combining the metadata pre-filter (A1/A3) with an LLM triage (A2) in a single cheap call. At 120 documents this becomes a major lever — the BM25 candidate pool shrinks from thousands of chunks to hundreds.

**Template code reference:** `src/agent/query_planner.py` — reuse the same patterns for model resolution (`_resolve_planner_model` → `_resolve_document_planner_model`), API key loading, JSON parsing with markdown unwrapping, and graceful fallback.

#### Exp 4B — Chunk-level embedding rerank

**Hypothesis (B4):** Rerank the top-N BM25 candidates using the Phase 6 embedding model at the chunk level.

**Prerequisite:** `uv sync --extra embedding` for sentence-transformers.
**Latency concern:** Embedding 48 chunks × 1 question should be < 500ms on CPU with a 0.6B model, but measure.

#### Exp 4C — Document planner + best Wave 1-3 combination

**Hypothesis:** The document planner (4A) stacks with the best retrieval and synthesis configs from earlier waves because it operates at a different level (document pre-filter vs chunk scoring vs answer generation).

**Run:** Combine the winning configs from Waves 1-3 with `DMB_DOCUMENT_PLANNER=1`.

**Pass:** Hits all five criteria from Section 7 simultaneously.

---

## 4. Execution order and dependencies

```
Wave 1 (all independent, can run in any order)
├── Exp 1A: Phase 3 stability (3 runs)         ← FIRST, establishes baseline
├── Exp 1B: Tighter top-k (32)
├── Exp 1C: Stricter density (0.5)
├── Exp 1D: Compact verbosity
├── Exp 1E: Default verbosity
├── Exp 1F: Context budget 10k
└── Exp 1G: Claim verification

Analysis checkpoint: which levers move synthesis_gap? Which move evidence_gap?
Pick the best Wave 1 config as the new baseline.

Wave 2 (depends on Wave 1 analysis)
├── Exp 2A: Two-step synthesis            ← code change in synthesis.py
└── Exp 2B: Citation-structured prompt    ← prompt change in synthesis.py

Analysis checkpoint: does two-step or citation structure help?
Combine best synthesis approach with best Wave 1 retrieval.

Wave 3 (depends on Wave 1 baseline)
├── Exp 3A: Per-seed neighbor budget      ← code change in evidence_retriever.py
├── Exp 3B: Two-pass evidence retrieval   ← code change in cli.py
└── Exp 3C: Per-doc chunk quotas          ← code change in evidence_retriever.py

Wave 4 (can run in parallel with Waves 2-3 — independent pre-filter layer)
├── Exp 4A: LLM document planner          ← new module document_planner.py + cli.py wiring
├── Exp 4B: Embedding rerank              ← needs embedding infra
└── Exp 4C: Document planner + best combo ← depends on 4A + best of Waves 1-3

Final combination: best retrieval (Wave 1 + 3) × best synthesis (Wave 2) × doc planner (Wave 4)
```

---

## 5. Results table template

Fill this in as experiments complete. Copy into the ledger notes or a new report.


| Exp   | Phase name                     | semantic pass | evidence_gap | retriever_gap | synthesis_gap | hit | fail_stale | avg_support | notes |
| ----- | ------------------------------ | ------------- | ------------ | ------------- | ------------- | --- | ---------- | ----------- | ----- |
| 1A-r1 | exp1a_phase3_stability_run1    |               |              |               |               |     |            |             |       |
| 1A-r2 | exp1a_phase3_stability_run2    |               |              |               |               |     |            |             |       |
| 1A-r3 | exp1a_phase3_stability_run3    |               |              |               |               |     |            |             |       |
| 1B    | exp1b_tighter_topk_32          |               |              |               |               |     |            |             |       |
| 1C    | exp1c_density_0_5              |               |              |               |               |     |            |             |       |
| 1D    | exp1d_phase3_compact           |               |              |               |               |     |            |             |       |
| 1E    | exp1e_phase3_default_verbosity |               |              |               |               |     |            |             |       |
| 1F    | exp1f_context_budget_10k       |               |              |               |               |     |            |             |       |
| 1G    | exp1g_claim_verification       |               |              |               |               |     |            |             |       |
| 2A    | exp2a_two_step_synthesis       |               |              |               |               |     |            |             |       |
| 2B    | exp2b_citation_structure       |               |              |               |               |     |            |             |       |
| 3A    | exp3a_per_seed_budget          |               |              |               |               |     |            |             |       |
| 3B    | exp3b_two_pass_evidence        |               |              |               |               |     |            |             |       |
| 3C    | exp3c_doc_quotas               |               |              |               |               |     |            |             |       |
| 4A    | exp4a_document_planner         |               |              |               |               |     |            |             |       |
| 4B    | exp4b_embedding_rerank         |               |              |               |               |     |            |             |       |
| 4C    | exp4c_doc_planner_combo        |               |              |               |               |     |            |             |       |


---

## 6. Key files reference


| File                                                                   | Role                                                            | Modify in           |
| ---------------------------------------------------------------------- | --------------------------------------------------------------- | ------------------- |
| `src/agent/evidence_retriever.py`                                      | Evidence scoring, neighbor expansion, entity overlap            | Wave 3              |
| `src/agent/synthesis.py`                                               | System prompt, profiles, verbosity, LLM call                    | Wave 2              |
| `src/agent/retriever.py`                                               | Entity retrieval, filter_projection                             | Wave 3B             |
| `src/agent/query_planner.py`                                           | Entity-level LLM planner (template for doc planner)             | Wave 4A (reference) |
| `src/agent/document_planner.py`                                        | **New** — document-level LLM planner                            | Wave 4A (create)    |
| `src/cli.py`                                                           | Pipeline orchestration, CLI flags, _fuse, _fit_context_budget   | Wave 2-4            |
| `evals/mirathorn_vertical_slice/run_council_room_question_set.py`      | Benchmark runner, env var wiring, stage-loss classification     | All waves           |
| `evals/mirathorn_vertical_slice/gold/gold_questions.json`              | Must-hit tokens, core_claims, semantic equivalences             | Read-only           |
| `evals/mirathorn_vertical_slice/output/evidence_gap_phase_ledger.json` | Phase-by-phase metrics accumulator                              | All waves (append)  |
| `MODEL_POLICY.json` (parent repo)                                      | LLM model selection for synthesis, query planning, doc planning | Reference           |


---

## 7. Decision criteria after all experiments

After completing Waves 1-3, combine the best retrieval config with the best synthesis config and run a **final combination experiment**. The combination is the new default if it meets ALL of:

1. **semantic pass ≥ 9/15** (matches or beats Phase 3 high-water mark)
2. **evidence_gap ≤ 10** (maintained from Phase 4-6 gains)
3. **synthesis_gap ≤ 5** (reduced from current 12)
4. **fail_stale = 0**
5. **avg context_support ≥ 0.72**

If no single combination meets all five, pick the config that maximizes `hit` count (tokens correctly surfaced in answers) as the tiebreaker — that's the metric that best reflects end-user answer quality.