# HANDOFF: Evidence Gap Bottleneck — Deep Analysis & Brainstorming

**Date:** 2026-04-03
**Status:** Ready for investigation
**Context:** After introducing the explicit evidence-first retrieval stage, the benchmark's stage-loss ladder now shows `evidence_gap = 20` as the dominant new bottleneck — 20 must-hit tokens exist in the full fact store but fall outside the evidence window selected by `retrieve_relevant_evidence()`. This is the expected and *correct* next optimization target.

---

## 1. What is the evidence gap?

The benchmark runner classifies every must-hit token through a five-stage ladder:

```
store_gap       → token not found anywhere in full campaign projection
evidence_gap    → token IN store BUT NOT in selected evidence chunks
retriever_gap   → token IN evidence BUT NOT in entity projection slice
synthesis_gap   → token IN entity projection BUT NOT in LLM answer
hit             → token present in the LLM answer
```

`evidence_gap = 20` means 20 tokens survive the store but are eliminated when `retrieve_relevant_evidence()` picks its evidence window. This is purely a recall problem at the evidence selection stage.

---

## 2. How evidence retrieval works today

### Pipeline position

```
Store (all evidence units)
  → retrieve_relevant_evidence()       ← THIS IS THE BOTTLENECK
    → rank_entities_by_evidence_overlap()
      → retrieve_relevant_entities() (lexical keyword match)
        → _fuse_ranked_entities()
          → filter_projection()
            → _fit_context_budget()
              → format_projection_context()
                → synthesis LLM
```

### `retrieve_relevant_evidence()` — current algorithm

**File:** `src/agent/evidence_retriever.py:226-305`

**Parameters (CLI defaults):**


| Parameter         | Default | CLI flag                     |
| ----------------- | ------- | ---------------------------- |
| `top_k`           | 24      | `--evidence-top-k`           |
| `neighbor_window` | 1       | `--evidence-neighbor-window` |
| `max_neighbors`   | 24      | `--evidence-max-neighbors`   |


**Theoretical max selected evidence:** `top_k + max_neighbors = 48` chunks.

**Scoring (`_score_units`):**

1. **BM25-style IDF overlap** between question tokens and unit `text + section_path`. Tokenizer strips stopwords, requires min 3-char lowercase words.
2. **Scope boost:** +0.35 if unit's `document_id` is in scope set.
3. **Phrase boost:** up to +0.30 for matching hardcoded phrase fragments (`trap`, `alarm`, `ward`, `countdown`, `consequence`, `session`).
4. **Session alignment:** +0.25 if question says "session N" and unit's `inferred_session` matches.

**Neighbor expansion:** After seeding top-k, walks `source_order_index` within each seed's document with `abs(idx - seed_idx) <= neighbor_window`. Budget-capped at `max_neighbors` total across all seeds, processed in seed-rank order (highest-scored seed's neighbors first).

### Key limitations visible from the algorithm

1. **Pure lexical match** — no semantic similarity. A question about "the wolf's death" won't match a chunk that says "the creature was slain" unless both share a word.
2. **Hardcoded phrase boosts** — only 6 terms get phrase bonuses. Domain vocabulary is much richer.
3. **Stopword filter + 3-char minimum** — drops short but meaningful tokens like "CR", "HP", "AC", names shorter than 3 characters.
4. **Global neighbor budget** — the first high-scoring seed can consume the entire neighbor budget, starving lower-ranked but important seeds.
5. **No entity-awareness** — evidence scoring doesn't know which entities a chunk's provenance links to, so it can't boost chunks that mention question-relevant entities.
6. **Flat top-k cutoff** — no adaptive thresholding. If 30 chunks are relevant but `top_k=24`, six get dropped regardless of score density.

---

## 3. What the stage-loss data tells us (retrieval-only baseline)

From `evals/mirathorn_vertical_slice/output/stage_loss_deep_dive_no_planner.json` (60 total must-hit tokens, 15 questions):


| Stage         | Count | %   |
| ------------- | ----- | --- |
| hit           | 37    | 62% |
| retriever_gap | 10    | 17% |
| synthesis_gap | 7     | 12% |
| store_gap     | 6     | 10% |


**Note:** This artifact predates the evidence-first stage, so `evidence_gap` is not broken out (evidence_text == full_projection_text when evidence-first is off). The 20-count evidence_gap appears when evidence-first is enabled, redistributing some of these retriever_gap and synthesis_gap tokens.

### Questions with the most token loss (from stage-loss deep dive)

**Retriever-gap dominated (chunks exist in store but retrieval missed them):**

- `q_battle_with_the_wolf_and_aftermath_2`: "arcane traps", "alarm pulses", "illusory walls" — 3 tokens lost
- `q_the_emergency_council_meeting_4_v2`: "time pressure", "countdown", "consequences" — 3 tokens lost
- `q_the_emergency_council_meeting_1`: "tradeoff" — 1 token lost
- `q_arch_current` / `q_arch_delta`: "arched ceilings", "floating chandelier", "secret passage", "chandelier", "runes" — multiple tokens lost at retriever

**Store-gap (not ingested at all):**

- "counter corruption", "decapitated", "not fully corrupted", "uncertain reliability", "not corrupted"

**Synthesis-gap (present in context but LLM didn't include in answer):**

- "bonogo" (twice), "caelynn", "ephanna", "corrupted guards", "secret passage"

---

## 4. Root cause hypotheses for evidence_gap

These are the most likely reasons chunks containing must-hit tokens are being excluded:

### H1: Vocabulary mismatch (highest probability)

The BM25 tokenizer requires exact word overlap. Questions use natural phrasing while evidence chunks use narrative/session-note language.

**Example:** Q asks about "the wolf's death" → chunk says "the creature was slain with a killing blow" → overlap is only on function words that get stopword-filtered.

**Test:** For each evidence_gap token, compare question tokens against the chunk that contains that token. Measure jaccard similarity. If < 0.1, vocabulary mismatch is confirmed.

### H2: Insufficient top-k / neighbor budget

With `top_k=24` and `max_neighbors=24`, we select at most 48 chunks from potentially thousands. If relevant chunks are spread across many documents, the budget may be too small.

**Test:** Re-run with `top_k=48, max_neighbors=48` and measure evidence_gap reduction. If it drops significantly, the budget is the constraint.

### H3: Neighbor budget starvation

The neighbor expansion loop processes seeds in rank order and uses a single shared budget. A high-scoring seed in document A could consume all 24 neighbor slots, leaving seeds in documents B and C with zero neighbors.

**Test:** Log per-seed neighbor allocation. If distribution is heavily skewed (e.g., seed 1 gets 20 neighbors, seeds 2-24 get 4 total), this is confirmed.

### H4: Scope filtering too aggressive

When `scope_document_ids` is provided, `retrieve_relevant_evidence` may restrict candidates to only those documents, dropping chunks from out-of-scope documents that contain relevant information.

**Test:** Compare `len(filtered)` vs `len(evidence_units)` in the debug payload. If scope filtering drops >50% of units, it may be overly restrictive.

### H5: Missing entity cross-references

Evidence chunks are scored independently of entities. A chunk might be low-IDF but critically important because it's the only provenance for a key entity attribute.

**Test:** For each evidence_gap token, find which entity attributes reference the chunk via `provenance_evidence_ids`. If those entities are in the retrieval set, the evidence chunk should have been boosted.

---

## 5. Concrete investigation plan

### Phase 1: Diagnostic data collection (no code changes)

1. **Run benchmark with `evidence-first` enabled and full trace output:**
  ```bash
   DMB_EVIDENCE_FIRST=1 \
   DMB_WRITE_COUNCIL_ROOM_QUESTION_SET_ARTIFACTS=1 \
   uv run python evals/mirathorn_vertical_slice/run_council_room_question_set.py
  ```
2. **For each question with evidence_gap tokens, extract:**
  - The must-hit token
  - The evidence chunk(s) in the store that contain it (grep the store's evidence units)
  - The score that chunk received from `_score_units`
  - The rank of that chunk (was it #25 when top_k=24?)
  - Whether the chunk's document was in-scope
3. **Build a diagnostic table:**

  | Question | Token | Chunk ID | Score | Rank | In top-k? | In-scope? | Why missed? |
  | -------- | ----- | -------- | ----- | ---- | --------- | --------- | ----------- |


### Phase 2: Parameter sensitivity sweep

Test evidence_gap reduction across parameter variations:


| Experiment    | top_k | neighbor_window | max_neighbors | Expected effect               |
| ------------- | ----- | --------------- | ------------- | ----------------------------- |
| Baseline      | 24    | 1               | 24            | Current evidence_gap=20       |
| Double seeds  | 48    | 1               | 24            | Test if more seeds helps      |
| Wider window  | 24    | 2               | 24            | Test if adjacent chunks help  |
| Double budget | 24    | 1               | 48            | Test if more neighbors help   |
| All increased | 48    | 2               | 48            | Upper bound on lexical recall |


**Key metric:** evidence_gap count. Secondary: context size (chars), total duration.

### Phase 3: Algorithmic improvements to brainstorm

Once diagnostics identify the dominant failure mode, consider these approaches:

#### A. Entity-aware evidence boosting

Use `rank_entities_by_evidence_overlap` in reverse: after initial entity retrieval identifies important entities, boost evidence chunks that are provenance for those entities' attributes.

**Pro:** Leverages existing provenance graph. **Con:** Circular dependency (entities depend on evidence, evidence boosted by entities).

#### B. Synonym/semantic expansion of query terms

Before scoring, expand the question's token set with known synonyms or entity name aliases from the store's entity metadata.

**Pro:** Addresses vocabulary mismatch without embeddings. **Con:** Requires a synonym source.

#### C. Two-pass evidence retrieval

1. First pass: current BM25 scoring → seed entities
2. Second pass: use seeded entities' provenance to pull additional evidence chunks not in the initial window

**Pro:** Directly addresses H5 (missing cross-references). **Con:** Adds latency.

#### D. Per-seed neighbor budgeting

Instead of a global `max_neighbors` budget, allocate `max_neighbors // len(seeded)` per seed, preventing top seeds from starving lower ones.

**Pro:** Simple fix for H3. **Con:** May waste budget on irrelevant seeds.

#### E. Score-threshold instead of top-k

Replace hard `top_k` with `min_score` threshold: include all chunks above a dynamic cutoff (e.g., `max_score * 0.3`).

**Pro:** Adapts to question difficulty. **Con:** Unpredictable context size; needs budget cap as safety valve.

#### F. Embedding-based reranking (heavier lift)

Add a lightweight embedding model (e.g., a small sentence-transformer) to rerank the top-N candidates from BM25.

**Pro:** Addresses vocabulary mismatch comprehensively. **Con:** Adds dependency, latency, and cost.

---

## 6. Key files for investigation


| File                                                                              | What it contains                                                                        |
| --------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------- |
| `src/agent/evidence_retriever.py`                                                 | `retrieve_relevant_evidence()`, `_score_units()`, `rank_entities_by_evidence_overlap()` |
| `src/agent/retriever.py`                                                          | `retrieve_relevant_entities()`, `filter_projection()`                                   |
| `src/cli.py` (lines 354-418)                                                      | `_fuse_ranked_entities()`, `_fit_context_budget()`, evidence-first CLI flags            |
| `src/agent/context_formatter.py`                                                  | `format_projection_context()`, scope relevance, entity cap logic                        |
| `evals/mirathorn_vertical_slice/run_council_room_question_set.py` (lines 414-570) | Stage-loss classification logic                                                         |
| `evals/mirathorn_vertical_slice/gold/gold_questions.json`                         | Must-hit tokens per question                                                            |
| `evals/mirathorn_vertical_slice/output/stage_loss_deep_dive_no_planner.json`      | Pre-evidence-first stage-loss data                                                      |


## 7. Must-hit tokens reference (all 15 questions, 60 total tokens)


| Question ID                                    | Must-hit tokens                                                       |
| ---------------------------------------------- | --------------------------------------------------------------------- |
| `q_the_emergency_council_meeting_1`            | wizards' college, arcane lockdown, wards, tradeoff                    |
| `q_longmont_session_12_council_chamber_roster` | bonogo, caelynn, thalia, wolf, guards, ephanna                        |
| `q_longmont_campaign_general_notes_1`          | shepherds, maelthor, worship, cult                                    |
| `q_the_city_council_2`                         | headmaster tinkerbright, wizard's college, detect, counter corruption |
| `q_the_city_council_4`                         | merril, agricultural union, torrin, guilds, rurik, infrastructure     |
| `q_battle_with_the_wolf_and_aftermath_1`       | killed, killing blow, bonogo, decapitated                             |
| `q_battle_with_the_wolf_and_aftermath_3`       | thalia, ensorcelled, not fully corrupted, corrupted guards            |
| `q_battle_with_the_wolf_and_aftermath_2`       | arcane traps, falling debris, alarm pulses, illusory walls            |
| `q_the_emergency_council_meeting_2_v2`         | thalia, wolf influence, guard operations, uncertain reliability       |
| `q_the_emergency_council_meeting_4_v2`         | time pressure, countdown, summoning, consequences                     |
| `q_arch_current`                               | arched ceilings, floating chandelier, secret passage                  |
| `q_arch_delta`                                 | chandelier, runes, secret passage                                     |
| `q_wolf_status`                                | killing blow, dead, oily sheen fades                                  |
| `q_pre_post`                                   | before, after, oily sheen, killing blow                               |
| `q_thalia`                                     | ensorcelled, wolf, not corrupted                                      |


---

## 8. Success criteria


| Metric                     | Current | Target | Stretch |
| -------------------------- | ------- | ------ | ------- |
| evidence_gap               | 20      | ≤10    | ≤5      |
| hit (total)                | ~37/60  | ≥45/60 | ≥50/60  |
| Context chars (avg)        | ~9.6K   | ≤15K   | ≤12K    |
| Evidence retrieval latency | <100ms  | <200ms | <150ms  |


The goal is to improve evidence recall without blowing up context size or latency. The ideal outcome is a precision-recall tradeoff that reduces evidence_gap by 50%+ while keeping context under 15K chars average.

---

## 9. Constraints and non-goals

- **No embedding infrastructure yet** — approaches requiring a vector DB or embedding model are brainstorming-only unless explicitly greenlit.
- **Don't break existing stages** — evidence improvements should not regress retriever_gap or synthesis_gap.
- **Keep latency reasonable** — evidence retrieval is currently <100ms; adding an LLM call here (like the query planner) would change the cost profile significantly.
- **The store_gap tokens are a separate problem** — don't try to solve ingestion gaps here. Those 6 tokens need re-ingestion, not retrieval fixes.

