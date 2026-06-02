# Design: Lexical Evidence Query Language for DungeonBuddy Retrieval

**Status:** Research / design (no implementation in this document)  
**Last updated:** 2026-06-01  
**Scope:** C1S1–4, C1S13, C2S22 smoke, C2S23 planning dogfood, manifest query/admission, live query traces

---

## Purpose

DungeonBuddy is a GM planning copilot over a living TTRPG corpus—not a generic RAG chatbot. Retrieval must help answer questions that carry **authority distinctions**:

- What happened in play vs what is only prep?
- What is canon vs derived memory vs staging?
- Which session, route family, or entity slug supports a claim?
- What evidence is admissible proof vs useful context vs dangerous distractor?

The current stack (`manifest_context_query.py`, C1S4 preplanning slice, sentence-routing breadcrumb benchmarks) already has the **bones**: activated manifest, source roles, authority boundaries, session scope, allowed/forbidden uses, recap/session-memory families, context packets, admitted/rejected evidence, live grounding, query enhancement, trace artifacts.

What is missing is a **transparent lexical evidence query plan**—a structured language that compiles natural GM questions into explicit filters, boosts, penalties, joins, and limits **without** collapsing everything into raw token overlap or hard session locks.

This document defines that language from benchmark analysis across the full retrieval lineage (C1S1–4, C1S13, C2S22, C2S23).

**Non-goals for this document:** Implement a new retrieval engine, replace manifest admission policy, or prescribe every operator upfront. The goal is discover the shape of the language from actual benchmark questions and artifacts.

---

## Corpus / benchmark artifacts inspected

### Suite inventory (retrieval/planning lineage)

| Suite | Sessions | Question/gold sources | Machine-scored? | Representative artifacts |
|-------|----------|----------------------|-----------------|--------------------------|
| **sentence_routing_retrieval_falsification** | C1S1–3 control, C1S13 holdout | `gold/breadcrumb_query_natural_c1s{1,2,3,13}_v1.json`, cohort manifests | Yes (route recall, context support ratio) | `artifacts/baselines/cohort_baseline_c1s13_v1.json`, `runs/2026-05-12/cohort_c1s13_v1/` |
| **c1s4_preplanning_vertical_slice** | C1S1–3 corpus; C1S4 oracle holdout | `gold/c1s4_beat_question_targets.json`, `gold/c1s4_expected_context_gold.json`, `gold/kb_policy.json` | Yes (Step 2C expected-context benchmark) | `artifacts/last_c1s4_step2c_multimode_report.json`, `pr58/pr58_retrieval_universe_summary.json` |
| **c2_live_prep — C2S23** | S21–22 source, S23 planning | `benchmarks/c2s23_dogfood_questions.seed.json` (22 Q), `c2s23_manifest_query_gold.json` (6 Q), `c2s23_route_evidence_gold.json` | Partial (6/22 PR97 gold; rest manual charter) | `artifacts/last_c2s23_manifest_query_context_eval.json`, `runs/2026-05-30/c2s23_manifest_query_context_packet_*.json` |
| **c2_live_prep — C2S22** | S20–21 memory, S22 prep | Smoke questions in `smoke_retrieval_packets.py` (5 Q); classifier gold | Smoke only; classifier separate | `artifacts/runs/2026-05-23/c2s22_smoke_summary.json`, `gold/session_22_live_turn_classifier.json` |
| **c2_live_prep — live traces** | S22 targeted | Harness-generated | Diagnostic (not gold-scored) | `artifacts/runs/2026-06-01/live_query_trace_session22_tuned_telemetry.json` |
| **planner_slice** | C1S3 statblock | Fixtures only | Planner eval, not retrieval admission | `fixtures/scenario_c1s3_*_statblock_context.json` |

**Confidence tiers:**

- **Full planning benchmark:** C2S23 manifest query (PR97), C1S4 Step 2C, C1S1–3/C1S13 breadcrumb natural gold.
- **Smoke / integration:** C2S22 retrieval smoke (reuses C1S4 module chain with `RETRIEVAL_MODE = "prior_only"`—a known anti-pattern for robustness validation).
- **Adjacent (feeds retrieval, not admission):** session events extraction, stage D entity resolution, recap ingest.

### Design docs and learnings consulted

| Document | Relevance |
|----------|-----------|
| `Docs/Plans/PLAN-split-corpus-retrieval-to-autonomous-demo.md` | Master retrieval rollout; route equivalence, alias safety, cohort A/B |
| `Docs/Plans/CHECKLIST-dynamic-lexical-retrieval-rollout.md` | Phase A–C operational tracker |
| `C1S13 Breadcrumb Retrieval Review.md` | Zero-tag failure anatomy; entity_index soft-oracle risk |
| `evals/c1s4_preplanning_vertical_slice/support_knowledge/SUPPORT_KNOWLEDGE_RETRIEVAL_CONTRACT.md` | Anti-oracle retrieval fields |
| `Docs/Plans/HANDOFF-pr97-manifest-query-admission.md` | Blind runner contract |
| `Docs/Plans/DESIGN-BRIEF-live-query-retrieval-alignment.md` | Session 22 last-beat ranking failure |
| `Docs/Plans/BENCHMARK-PHILOSOPHY-evidence-reference-context-packets.md` | Authority + packet contract |
| `Docs/Plans/BENCHMARK-c2s23-dogfood-planning-charter.md` | Manual baseline dimensions |
| `.cursor/rules/breadcrumb-query-objective-tradeoffs.mdc` | Alias activation, retrieval-before-answer |
| `.cursor/rules/anti-oracle-leakage.mdc`, `llm-context-discovery.mdc` | Discovery-not-provision |

### Code paths (current retrieval/admission)

| Module | Role |
|--------|------|
| `src/live_play/manifest_context_query.py` | Query features, lane-budget retrieval, span/unit extraction, admission |
| `src/live_play/planning_corpus_manifest.py` | Manifest composition, authority by role, staging demotion |
| `src/live_play/live_query_context.py` | Live grounding, evidence IDs, read-only policy |
| `evals/c1s4_preplanning_vertical_slice/query_lane_router.py` | C1 lane routing |
| `evals/c1s4_preplanning_vertical_slice/query_variant_retrieval.py` | Query variant retrieval |
| `evals/sentence_routing_retrieval_falsification/breadcrumb_query_run.py` | C1 natural-query benchmark runner |

---

## Question family taxonomy

Derived from `c2s23_dogfood_questions.seed.json` (22 questions), PR97 gold (6), C1S13 natural gold (27 scenarios), C1S4 beat targets (38 questions), C2S22 smoke (5), and C1S1 natural gold.

| Family | ID prefix / examples | PR97 gold? | Primary claim type |
|--------|---------------------|------------|-------------------|
| **A. Single-session play fact** | `s22-ingest-01`, `s22-ingest-02`, `loc-01` | Yes (partial) | `play_fact` |
| **B. Last/final event** | Live trace: "last thing in Session 22"; C1S13 beat questions | No (semantic gap) | `play_fact` |
| **C. Cross-session continuity** | `xsession-01`, `xsession-03`, `npc-03` | No | `planning_context` / `play_fact` |
| **D. NPC state / history** | `npc-01`, C1S13 entity questions, C2S22 smoke `active_npcs_*` | No | `planning_context` / `play_fact` |
| **E. Location / town planning** | `loc-01`, `town-01`, C1S13 location hierarchy | No | `planning_context` |
| **F. Prep scaffold vs canon** | `auth-01`, `town-02` | No | `play_fact` / `authority_guardrail` |
| **G. Authority trap** | `auth-02`, `auth-04`, `auth-05` | Yes (`auth-05`) | `authority_guardrail` |
| **H. Capability / actionability** | `loc-02`, `roll-02`, `manifest-01`, `npc-02` | Yes (3) | `capability_check` |
| **I. Pipeline / ingest readiness** | `s22-ingest-03` | Yes | `pipeline_state` |
| **J. Roll table / tool reference** | `roll-01`, `roll-03` | No | `planning_context` |
| **K. Open-loop → planning surface** | `xsession-02` | No | `planning_context` |
| **L. C1 breadcrumb natural recall** | C1S1–3/C1S13 scenarios | Yes (route gates) | Lexical recall (pre-manifest era) |
| **M. C1S4 synthetic prep (oracle holdout)** | `q01_*`, beat questions | Evaluator-only | `prior_recap_supported` etc. |

**Coverage gaps (16/22 C2S23 questions lack PR97 gold):** cross-session, NPC, town, roll-table, most authority traps except `auth-05`. Charter v0 is manual decision-capture for those.

---

## Evidence need taxonomy

For each family, the retrieval language must express **what evidence shapes an answer**, not just what tokens match.

### A. Single-session play fact

| Dimension | Pattern |
|-----------|---------|
| Primary roles | `play_recap`, `session_memory` |
| Authorities | `canon_play`, `derived_memory` |
| Lexical cues | "play outcomes", "happened", session number, recap title tokens |
| Route cues | `Session N - <title>.md`, `_normalized/`, `_session_memory/*.jsonl` |
| Session behavior | **PREFER** target session; do not hard-lock unless explicit |
| Distractors | `prep_scaffold`, `table_notes`, hub README instructions |
| Multi-source | Often one recap family + memory units |

### B. Last/final event

| Dimension | Pattern |
|-----------|---------|
| Primary | Same as A |
| Special relevance | **TAIL_SPAN** boost on play_recap; `document_position_score`; ending phrase markers |
| Distractors | Earlier-session recaps with overlapping vocabulary (Session 21 conical hill vs S22 Lysandro beat) |
| Known failure | `live_query_trace_session22_fresh_ingested_lexical.json` — S21 ranked above S22 |

### C. Cross-session continuity

| Dimension | Pattern |
|-----------|---------|
| Primary | Multi-session `play_recap` + `session_memory` |
| Session behavior | **ALLOW** sessions 21 and 22 (and older if question asks "earlier sessions") |
| Lexical cues | "between Session 21 and 22", "still constrain", "changed" |
| Distractors | Roll tables for geography; prep scaffolds as play proof |

### D. NPC state / history

| Dimension | Pattern |
|-----------|---------|
| Primary | Entity-named spans in recap/memory + `hub_evidence` README/timeline |
| Route cues | `NPCs/<slug>/README.md`, breadcrumb `[NPC][...]` tags (C1S13 lesson: zero tags → route failure) |
| Session behavior | Multi-session when question spans S21–22 |
| Distractors | Hub prose alone without play citation |

### E. Location / town planning

| Dimension | Pattern |
|-----------|---------|
| Primary | `play_recap` end-state + `planning_scaffold` for forward prep |
| Authority split | Play facts from canon; economy hooks may be scaffold |
| Distractors | `reference_tool` roll tables as geographic proof |

### F–G. Prep vs canon / authority trap

| Dimension | Pattern |
|-----------|---------|
| MUST reject | `table_notes`, `fresh_recap`, staging after canonical recap exists |
| MUST admit | `canon_play`, `derived_memory` for what did happen |
| Verdict shape | Policy answer in `source_excerpt` (`auth-05` gold) |

### H. Capability

| Dimension | Pattern |
|-----------|---------|
| Primary | `capability_audit`, `live_workspace`, honest `blocked_or_missing` |
| Retrieval breadth | Multi-role admission OK; status field carries truth |

### I. Pipeline state

| Dimension | Pattern |
|-----------|---------|
| Primary | Virtual `ingest_status` / `audit` + recap/memory corroboration |
| Forbidden | `prep_scaffold` for pipeline claims |

### L. C1 breadcrumb natural (legacy lane)

| Dimension | Pattern |
|-----------|---------|
| Primary | Session-memory records with inline route tags |
| Gates | `expect_route_substrings`, `must_hit_tokens`, `min_context_support_ratio` |
| Lesson | Route tags are join keys; lexical-only fails on C1S13 holdout |

---

## Hard policy vs soft relevance

### Hard filters (MUST — admission / policy)

These are **non-negotiable** and map to `_admission_reason()` and manifest composition:

```
MUST admissible = true
MUST route_exists = true
MUST authority IN <claim-specific allowlist>
MUST NOT forbidden_uses CONTAINS play_facts   (for play_fact claims)
MUST NOT source_role IN <claim-specific denylist>
MUST evidence_granularity IN (unit_id, line_range, text_excerpt)  (play_fact)
MUST evidence_score >= min_supporting_evidence_score  (play_fact, default 2.0)
MUST explicit_session_only WHEN user says "only Session N"
```

**Legitimate hard session lock:** only when `explicit_session_only=true` (user phrasing: "only use Session 22 recap evidence").

### Soft relevance (SHOULD / BOOST / PENALIZE)

```
PREFER session_scope OVERLAP query.session_numbers
PREFER source_role IN (play_recap, session_memory) WHEN claim = play_fact
BOOST title_phrase MATCH "Session 22 - Mireward Road and Lysandro"
BOOST lexical_terms / distinctive_tokens
BOOST tail_span WHEN asks_for_last_or_final AND source_role = play_recap
BOOST recency (max session_scope) WHEN no session in query AND asks_for_recent
PENALIZE hub_evidence_for_play_event
PENALIZE meta-* session_memory units for play_event
PENALIZE stopword_only_overlap
SOFT-DOWNRANK non-target sessions (-0.75 continuity vs -2.5 default mismatch)
```

### MAY include / NEVER use as proof

| Family | MAY (secondary) | NEVER as proof |
|--------|-----------------|----------------|
| Play fact | hub_evidence (orientation) | prep_scaffold, roll_table, live_packet (past play) |
| Planning | prep_scaffold, hub_evidence | staging as "happened" |
| Capability | broad role sampling | N/A (status is the answer) |

---

## Existing fields we can already query

### Manifest entry (planning corpus)

From `planning_corpus_manifest.py` / manifest JSON:

- `source_id`, `route`, `source_role`, `authority`
- `session_scope[]`, `route_exists`, `admissible`
- `allowed_uses[]`, `forbidden_uses[]`
- `notes[]` (sparse)
- `lexical_terms[]` (**scorer supports; manifest builder does not emit in production**)

### Query features (runtime, from question text)

From `_build_query_features()`:

- `tokens`, `content_tokens`, `stopword_tokens`, `distinctive_tokens`
- `session_numbers`, `title_phrases`, `exact_phrases`, `aliases`
- `asks_for_last_or_final`, `asks_for_play_event`, `asks_historical_continuity`, `explicit_session_only`
- `intent_hints` → `primary_claim_type`, `lane_budgets`

### Evidence unit (post-extraction)

- `path`, `source_role`, `authority`, `session_scope`
- `unit_id`, `line_start`, `line_end`, `text_excerpt`
- `evidence_score`, `score_components{}` (per-component breakdown)
- Session memory: `routes[]`, `source_recap_path` (implicit join)

### Implicit joins (already faked via paths)

| Join | Mechanism |
|------|-----------|
| manifest entry → markdown span | `extract_evidence_units` reads file, paragraph spans |
| manifest entry → session memory unit | JSONL `lexical_plain`, `unit_id`, line refs |
| session memory unit → source recap | `source_recap_path` alignment score |
| session memory → hub routes | `routes[].normalized_route` |
| recap family | canonical / `_normalized/` / `_breadcrumbed/` / `_session_memory/` same session |
| breadcrumb tag → hub route | Inline `[NPC][path]` in breadcrumb prose (C1 lane) |

### Trace / explainability (output, not yet a plan IR)

`retrieval_trace` in context packets already emits: `top_manifest_entries`, `lane_top_entries`, `top_markdown_spans`, `top_session_memory_units`, `admitted_evidence`, `rejected_evidence` with `score_components`.

---

## Missing fields / metadata that would help

1. **`lexical_terms` on production manifest entries** — scorer expects; builder omits.
2. **`recap_family_id`** — link canonical/normalized/breadcrumbed/memory for one session (dedup competing routes).
3. **`entity_slugs[]`** — explicit NPC/location slugs per entry (vs path tokenization).
4. **`breadcrumb_id`** — never populated; would enable tag→route join in manifest lane.
5. **`declared_title`** — separate from path for title matching (not substring over full route).
6. **`EvidenceQueryPlan` IR** — pre-LLM structured plan object (trace is post-hoc).
7. **Semantic rank gold** — `required_admitted_top1_path_contains` for Session 22 last-beat (evaluator-only).
8. **C2S22 full planning benchmark** — no gold parallel to C2S23; smoke uses `prior_only` mode.

---

## Proposed lexical query primitives

Smallest useful operator set (lexical-first, pragmatic):

| Primitive | Semantics | Example |
|-----------|-----------|---------|
| `LEXICAL(tokens)` | Distinctive token overlap on content | `LEXICAL(mireward lysandro lysandra)` |
| `PHRASE("...")` | Quoted phrase substring match | `PHRASE("met her father")` |
| `TITLE_MATCH("...")` | Recap title / route title fragment | `TITLE_MATCH("Session 22 - Mireward Road and Lysandro")` |
| `ROUTE_MATCH("...")` | Path substring / family | `ROUTE_MATCH("Session Recaps/Session 22")` |
| `ROUTE_FAMILY(session, slug)` | Canonical recap family for session | `ROUTE_FAMILY(22, mireward_lysandro)` |
| `ENTITY(slug)` | Hub slug / breadcrumb entity | `ENTITY(captain_lysandra_ironveil)` |
| `SESSION(n)` | Soft session preference | `PREFER SESSION(22)` |
| `SESSION_WINDOW(lo..hi)` | Continuity window | `PREFER SESSION_WINDOW(15..22)` |
| `SESSION_ONLY(n)` | Hard lock (explicit user only) | `MUST SESSION_ONLY(22)` |
| `SOURCE_ROLE(role)` | Role filter/boost | `PREFER SOURCE_ROLE(play_recap)` |
| `AUTHORITY(auth)` | Authority filter | `MUST AUTHORITY IN (canon_play, derived_memory)` |
| `ALLOWED_USE(use)` | Manifest use tag | `MUST ALLOWED_USE CONTAINS play_facts` |
| `FORBIDDEN_USE_NOT(use)` | Manifest forbidden tag | `MUST NOT forbidden_uses CONTAINS play_facts` |
| `TAIL_SPAN()` | Document position / ending boost | `BOOST TAIL_SPAN WHEN play_recap AND last_or_final` |
| `RECENCY()` | Max session_scope when no session in query | `BOOST RECENCY()` |
| `DISTINCTIVE_TERMS()` | Auto from query minus stopwords | `BOOST DISTINCTIVE_TERMS()` |
| `STOPWORD_DAMPEN()` | Downweight common tokens | `PENALIZE STOPWORD_DAMPEN()` |
| `HUB_DAMPEN_FOR_PLAY_EVENT()` | Hub README penalty | `PENALIZE hub_evidence WHEN play_event` |
| `META_UNIT_DAMPEN()` | session_memory meta-* units | `PENALIZE unit_id STARTS meta-` |
| `JOIN_MEMORY_TO_RECAP` | Align unit to source_recap_path | implicit in scorer |
| `LIMIT(n)` | Budget cap | `LIMIT admitted 10` |

---

## Proposed query IR

Machine-executable intermediate representation (JSON/dataclass). Compiles from `QueryFeatures` + claim type; drives entry/span/unit scoring; renders to DSL for debug.

```json
{
  "schema": "dmb_evidence_query_plan_v1",
  "query_id": "s22-last-beat",
  "raw_question": "what was the last thing that happened in Session 22",
  "compiled_from": {
    "intent_hints": ["play_fact", "planning_context"],
    "primary_claim_type": "play_fact",
    "session_numbers": [22],
    "explicit_session_only": false,
    "asks_for_last_or_final": true,
    "asks_for_play_event": true,
    "asks_historical_continuity": false,
    "distinctive_tokens": ["happened"],
    "title_phrases": ["session 22"],
    "aliases": []
  },
  "must": [
    {"field": "admissible", "op": "eq", "value": true},
    {"field": "route_exists", "op": "eq", "value": true},
    {"field": "authority", "op": "in", "value": ["canon_play", "derived_memory"]},
    {"field": "forbidden_uses", "op": "not_contains", "value": "play_facts"}
  ],
  "prefer": [
    {"feature": "source_role", "op": "in", "value": ["play_recap", "session_memory"], "weight": 5},
    {"feature": "session_scope_overlap", "op": "intersects", "value": [22], "weight": 6}
  ],
  "boost": [
    {"feature": "title_phrase", "value": "Session 22 - Mireward Road and Lysandro", "weight": 12},
    {"feature": "route_match", "value": "Session 22 - Mireward", "weight": 8},
    {"feature": "lexical_terms", "value": ["mireward", "lysandro", "lysandra", "final", "beat"], "weight": 4},
    {"feature": "tail_span", "when": {"source_role": "play_recap", "asks_for_last_or_final": true}, "weight": 8},
    {"feature": "ending_phrase", "value": ["met her father", "lysandro"], "weight": 3}
  ],
  "penalize": [
    {"feature": "session_scope_mismatch", "when": {"query_sessions": [22]}, "weight": 2.5},
    {"feature": "hub_evidence_for_play_event", "weight": 5},
    {"feature": "meta_unit_for_play_event", "weight": 3},
    {"feature": "stopword_only_overlap", "weight": 4}
  ],
  "hard_locks": [],
  "lane_budgets": {"play_recap": 4, "session_memory": 4, "hub_evidence": 4},
  "limits": {"max_admitted": 10, "max_retrieved": 30, "min_evidence_score": 2.0},
  "joins": ["manifest_entry_to_markdown_span", "manifest_entry_to_session_memory_unit", "memory_unit_to_source_recap"]
}
```

**Render target:** every live query and manifest query emits this plan in `retrieval_trace.query_plan` before scoring (Stage 2 of implementation).

---

## Human-readable DSL examples

### Play fact — Session 22 outcomes

```text
FIND evidence
FOR claim: play_fact
MUST authority IN canon_play, derived_memory
MUST NOT forbidden_uses CONTAINS play_facts
PREFER source_role IN play_recap, session_memory
PREFER session 22
BOOST title "Session 22 - Mireward Road and Lysandro"
BOOST lexical mireward swamp mirathorn lysandra
PENALIZE source_role prep_scaffold, table_notes
LIMIT admitted 10
```

### Last beat — Session 22

```text
FIND evidence
FOR claim: play_fact
MUST authority IN canon_play, derived_memory
PREFER session 22
BOOST title "Session 22 - Mireward Road and Lysandro"
BOOST tail_span WHEN source_role = play_recap
BOOST ending_phrase "met her father" "lysandro" "lysandra"
PENALIZE session 21 recap WHEN lexical overlap WITHOUT title_match
ALLOW session 21, 23 IN candidates WITH rank penalty
LIMIT admitted 10
```

### Cross-session continuity

```text
FIND evidence
FOR claim: planning_context
PREFER session_scope OVERLAP 21, 22
BOOST lexical "between" "changed" "north" "mireward"
BOOST route_family Session 21, Session 22
MAY source_role hub_evidence
PENALIZE reference_tool AS play proof
LIMIT admitted 12
```

### Explicit session lock (user-requested)

```text
FIND evidence
FOR claim: play_fact
MUST SESSION_ONLY 22
MUST authority IN canon_play, derived_memory
...
```

---

## Benchmark question worked examples

Each example: original question → family → evidence pattern → hard/soft → lexical cues → distractors → DSL sketch → IR claim_type.

### 1. Single-session play fact — `s22-ingest-01`

**Question:** "After ingesting the raw Session 22 table notes, what are the three most important play outcomes I need to carry into Session 23 prep?"

| Field | Value |
|-------|-------|
| Family | A. Single-session play fact |
| Evidence pattern | S22 recap + session_memory units; reject staging |
| Hard filters | authority ∈ {canon_play, derived_memory}; forbid table_notes, prep_scaffold for play_fact |
| Soft boosts | session 22, title "Mireward Road and Lysandro", lexical {swamp, mirathorn, mireward} |
| Distractors | `_ingest_staging/session_22_raw_notes.md`, prep runbooks |
| DSL | See "Play fact — Session 22 outcomes" above |
| IR `primary_claim_type` | `play_fact` |

PR97 gold: `acceptable_path_contains_any` S22 recap family paths; `min_supporting_evidence_score: 2.0`.

---

### 2. Last/final event — Session 22 (live trace + tests)

**Question:** "what was the last thing that happened in Session 22"

| Field | Value |
|-------|-------|
| Family | B. Last/final event |
| Evidence pattern | S22 recap **tail span** with Lysandro/Lysandra beat; memory units with ending phrases |
| Hard filters | Same as play_fact |
| Soft boosts | `TAIL_SPAN`, `TITLE_MATCH("Session 22 - Mireward Road and Lysandro")`, ending_phrase |
| Distractors | Session 21 "conical hill" / "giant bowl" spans sharing "session" tokens |
| Failure artifact | `live_query_trace_session22_fresh_ingested_lexical.json` — S21 cited |
| Success artifact | `live_query_trace_session22_tuned_retrieval_alignment.json` |

```text
BOOST tail_span + title_match Session 22
PENALIZE hub_evidence, session 21 UNLESS title_match
```

---

### 3. Cross-session continuity — `xsession-03`

**Question:** "If the party continues north toward Mireward Reach, what changed between Session 21 travel context and where Session 22 ended?"

| Field | Value |
|-------|-------|
| Family | C. Cross-session continuity |
| Evidence pattern | **Both** S21 and S22 recaps/memory; geographic delta |
| Hard filters | play_fact authorities for played deltas; no roll_table as geography proof |
| Soft boosts | SESSION_WINDOW(21..22), lexical {north, mireward, changed, travel} |
| Distractors | Travel roll tables, prep distance notes without play citation |

```json
"prefer": [
  {"feature": "session_scope_overlap", "value": [21, 22], "weight": 5}
],
"boost": [
  {"feature": "route_match", "value": "Session 21 - Drake Nest", "weight": 4},
  {"feature": "route_match", "value": "Session 22 - Mireward", "weight": 4}
]
```

---

### 4. NPC history/state — `npc-01`

**Question:** "What is Captain Lysandra Ironveil's state going into Session 23 (relationships, commitments, immediate pressures)?"

| Field | Value |
|-------|-------|
| Family | D. NPC state / history |
| Evidence pattern | S21–22 recap spans naming Lysandra + hub README/timeline |
| Soft boosts | `ENTITY(captain_lysandra_ironveil)`, multi-session scope |
| Distractors | Prep scaffold relationship notes without play citation; statblock without dossier read |

```text
BOOST entity captain_lysandra_ironveil
PREFER source_role play_recap, session_memory, hub_evidence
PENALIZE planning_scaffold AS sole proof
```

---

### 5. Location/town planning — `town-01`

**Question:** "What is the next town or settlement toward Mireward, and what trade or economy hooks matter for Session 23 opening scenes?"

| Field | Value |
|-------|-------|
| Family | E. Location / town planning |
| Evidence pattern | Play end-state (canon) + planning_scaffold for economy hooks |
| Authority split | Play facts from recap; economy may be scaffold |
| Distractors | Roll tables as proof of town names |

```text
FOR claim: planning_context
PREFER play_recap FOR end_state
MAY planning_scaffold FOR economy_hooks
MUST NOT treat reference_tool AS play_fact
```

---

### 6. Authority trap — `auth-05`

**Question:** "After canonical Session 22 recap exists, may I still use raw staged table notes as normal retrieval evidence for play-fact questions?"

| Field | Value |
|-------|-------|
| Family | G. Authority trap |
| Evidence pattern | Reject table_notes; admit canon for contrast; verdict in `source_excerpt` |
| Hard filters | `authority_guardrail` admission; table_notes → `authority_forbidden_for_play_fact` |
| Gold | Verdict contains "No" / "not as normal retrieval evidence" |

```text
FOR claim: authority_guardrail
MUST reject source_role table_notes FOR play_fact support
MUST admit canon_play FOR contrast
EMIT policy_verdict
```

---

### 7. Prep vs canon — `auth-01`

**Question:** "Did the shepherd-cult confrontation at the end of Session 22 definitely happen in play, or only appear in prep notes?"

| Field | Value |
|-------|-------|
| Family | F. Prep vs canon |
| Evidence pattern | Compare canon_play recap vs pre_canonical_evidence staging |
| Hard filters | Must choose provenance; staging alone ≠ canon |

```text
FIND evidence FOR claim: play_fact
MUST compare authority canon_play VS pre_canonical_evidence
PENALIZE answering from planning_scaffold alone
```

---

### 8. Capability — `loc-02`

**Question:** "Can I create a new named sub-location hub markdown file for a waystation north of the last stop using DungeonBuddy tooling during this dogfood round?"

| Field | Value |
|-------|-------|
| Family | H. Capability |
| Evidence pattern | capability_status + blocked_or_missing; not content retrieval |
| Gold | `missing_live_write_capability` blocker |

```text
FOR claim: capability_check
RETRIEVE live_workspace, prep_scaffold FOR context
EMIT capability_status missing
MUST NOT pretend write succeeded
```

---

### 9. Pipeline readiness — `s22-ingest-03`

**Question:** "What pipeline state must be true before I treat Session 22 as ready_for_planning_activation for cross-session planning?"

| Field | Value |
|-------|-------|
| Family | I. Pipeline state |
| Evidence pattern | Virtual ingest_status audit + S22 artifact existence |
| Hard filters | Reject prep_scaffold for pipeline claims |

```text
FOR claim: pipeline_state
MUST source_role ingest_status OR authority audit
CHECK state_flags ready_for_planning_activation, session_memory_materialized, ...
```

---

### 10. C1S13 holdout — breadcrumb natural (scenario)

**Question:** "Why did the party take Wolf's head to Stormspire Academy instead of just carrying the whole body?" (C1S13 natural gold)

| Field | Value |
|-------|-------|
| Family | L. C1 breadcrumb natural recall |
| Evidence pattern | Session-memory records with **inline route tags** to Stormspire hubs |
| Lesson | Zero tags → 27/27 route failures on holdout (C1S13 review) |
| IR join | `JOIN breadcrumb_tag → hub route` |

```text
BOOST route_substrings stormspire_academy, council_chambers
REQUIRE inline_tag OR route_family match
LEXICAL wolf head stormspire
```

---

### 11. C1S4 beat prep — `q01_who_are_the_npcs...` (evaluator-only target)

**Question:** "Who are the NPCs the players encountered in Stone Bridge...?" (C1S4 beat 1)

| Field | Value |
|-------|-------|
| Family | M. C1S4 synthetic prep |
| Retrieval corpus | C1S1–3 only; C1S4 forbidden (`kb_policy.json`) |
| Anti-oracle | Must NOT use `question_id`, `expected_retrieval_context`, `known_context_gaps` in retrieval |
| Modes | `prior_only`, `prior_plus_support_content_only`, `prior_plus_support_content_plus_lexical_hints` |

```text
FOR claim: prior_recap_supported
MUST session_scope IN 1,2,3
FORBIDDEN read heldout_session 4
BOOST lexical Pippa Bubbles Grishna "Stone Bridge" "River's Edge Pub"
INDEX support_knowledge title summary retrieval_terms ONLY
```

---

## How this differs from SQL

| SQL | Lexical evidence query language |
|-----|--------------------------------|
| Relational tables with fixed schema | Heterogeneous corpus artifacts (markdown spans, JSONL units, virtual audit rows) |
| Hard `WHERE session = 22` common | **PREFER** session; hard lock only on explicit user constraint |
| Joins on foreign keys | Joins faked via paths, `source_recap_path`, breadcrumb tags, recap families |
| Returns rows | Returns **ranked evidence units** with admission verdict + score components |
| Schema-first | **Lexical-first**: tokens, titles, routes, entities, position |
| Single result set | Admitted + rejected + capability_status + policy verdict |

The language is "SQL-like" in having explicit fields, filters, boosts, limits—but optimized for **campaign evidence planning**, not normalized tables.

---

## How this differs from raw vector/token retrieval

| Raw vector/BM25 RAG | Lexical evidence query language |
|---------------------|--------------------------------|
| Similarity score only | **Authority model** + admissibility gates |
| No source_role | Role lanes + per-claim MUST/NEVER |
| Embedding black box | **Explainable** score_components per boost |
| Session-agnostic | Session as preference + recency + continuity modes |
| Chunks arbitrary | Span/unit extraction with granularity rules |
| No rejected audit trail | `rejected_evidence` with reason_codes |
| Gold in prompt | **Anti-oracle**: runner blind to gold |

Vector retrieval may complement lexical matching later, but benchmarks prove **authority and route/title specificity** fail first—not embedding quality alone.

---

## Implementation sketch

Staged rollout (IR-first, no big-bang rewrite):

| Stage | Deliverable | Behavior change |
|-------|-------------|-----------------|
| **1** | `EvidenceQueryPlan` dataclass + JSON schema | None (emit-only) |
| **2** | Compile `QueryFeatures` + claim type → IR | None |
| **3** | DSL debug renderer in trace artifacts | Observability |
| **4** | Refactor `_score_entry` / span/unit scorers to read IR weights | Ranking driven by plan |
| **5** | Manifest emits `lexical_terms`, `recap_family_id` | Better boosts |
| **6** | Evaluator gold: `required_admitted_rank1_path` (semantic) | Catch S21-vs-S22 drift |
| **7** | Manifest slice cohort: minimal / prior / recent / full | Robustness proof |

**Recommended next PR (Stage 1–3):**

- Add `src/live_play/evidence_query_plan.py` with IR schema + compiler from existing `QueryFeatures`.
- Attach `query_plan` + `query_plan_dsl` to `retrieval_trace` in `build_context_packet`.
- Tests: compile known questions → assert IR fields match intent (no retrieval behavior change).
- Document compiler mapping in module docstring.

---

## Robustness matrix and validation tests

Manifest slices for cohort testing (same questions, progressively noisier manifests):

| Slice | Contents | Expected: "last thing Session 22" | Expected: "old threads for Session 23" |
|-------|----------|-----------------------------------|----------------------------------------|
| **Minimal** | S22 recap family only | S22 ranks #1 | May fail honestly (no older sessions) |
| **Prior** | S21 only (no S22) | No false S22 hits | S21 reachable |
| **Recent** | S21 + S22 + S23 workspace | S22 #1; S21 in candidates not top play_fact | Both reachable |
| **Full** | Production C2S23 manifest (~43 entries) | S22 #1 over S21 distractors | S15–S22 reachable when continuity asked |

**Existing tests to extend:**

- `test_session22_exact_title_wins_in_expanded_session_window`
- `test_session22_last_thing_not_dependent_on_prior_session_lock`
- `test_broad_continuity_question_can_retrieve_older_sessions`
- `test_only_session_query_enforces_explicit_session_lock`

**New cohort harness (Stage 7):**

- Fixture manifests: `evals/c2_live_prep/benchmarks/fixtures/manifest_slice_{minimal,recent,full}.json`
- Same 5–8 questions × 4 slices; report structural pass + **semantic rank pass** separately.

---

## Risks and anti-patterns

| Anti-pattern | Safeguard in query language |
|--------------|----------------------------|
| Hard prior-session lock | `SESSION(n)` is PREFER; `SESSION_ONLY(n)` only when explicit |
| Hard session filter for normal questions | IR `hard_locks[]` empty by default |
| Question-ID / gold routing | Compiler input = question text only; forbidden fields list in IR contract |
| Reading gold during retrieval | Runner open-guard tests; IR never references gold paths |
| Using expected answer as retrieval input | Separate evaluator channel; SUPPORT_KNOWLEDGE_RETRIEVAL_CONTRACT |
| Treating prep as canon | MUST authority + PENALIZE prep_scaffold for play_fact |
| Roll tables as play facts | FORBIDDEN source_role reference_tool for play_fact proof |
| Live observations as retroactive canon | Authority `live_observation` excluded from play_fact |
| Hub README as event proof | HUB_DAMPEN_FOR_PLAY_EVENT |
| Opaque score-only retrieval | Mandatory `query_plan` + `score_components` in trace |
| Pure vector retrieval without authority | Out of scope until authority gates pass lexical benchmarks |
| `prior_only` smoke as robustness proof | Document as **low-confidence**; require full-manifest cohort |
| Tiny manifest overfitting | Robustness matrix Stage 7 |
| Hand-curated entity_index oracle | Query-text-gated aliases; fail-loud on zero-tag memory |

---

## Recommended next PR

**Title:** `feat(retrieval): emit EvidenceQueryPlan IR and DSL in manifest query trace (no scoring change)`

**Files:**

- `src/live_play/evidence_query_plan.py` (new)
- `src/live_play/manifest_context_query.py` (attach plan to trace)
- `tests/test_evidence_query_plan.py` (compiler unit tests for 8+ benchmark questions)

**Verification:**

```bash
uv run pytest tests/test_evidence_query_plan.py tests/test_manifest_context_query.py -q
```

**Out of scope for that PR:** Changing ranking weights, manifest builder lexical_terms, semantic gold expansion.

---

## Appendix: C2S22 vs C2S23 benchmark gap

C2S22 has **no** full planning benchmark parallel to C2S23. Available C2S22 retrieval artifacts:

- `smoke_retrieval_packets.py` — 5 smoke questions over S20–21 session memory with `RETRIEVAL_MODE = "prior_only"` (useful integration smoke, **not** robustness validation).
- `run_session_22_classifier_benchmark.py` — live-turn routing, not evidence retrieval.
- Live fixtures under `evals/c2_live_prep/live/session_22/`.

Session 22 **content** enters C2S23 benchmarks via `source_sessions: [21, 22]` and question IDs `s22-ingest-*`. The lexical query language design should treat C2S23 as the canonical C2 planning retrieval benchmark while citing C2S22 smoke as a **lower-confidence** integration check until a dedicated C2S22 manifest-query gold set exists.

---

## Appendix: Lineage synthesis

| Era | Benchmark | Key learning for query language |
|-----|-----------|--------------------------------|
| C1S1–3 | Breadcrumb natural + cohort baselines | Route tags + lexical recall; expect_route_substrings |
| C1S13 | Holdout + scene-beat | Zero-tag failure; alias safety; hierarchy gold audit |
| C1S4 | Expected-context Step 2C | Lane routing, anti-oracle support knowledge, prior_only modes |
| C2S22 | Smoke | Module chain reuse; prior_only limitation |
| C2S23 | Manifest query PR97 | Authority admission, blind runner, 6/22 gold gap |
| Live traces | Session 22 tuning | Title/tail_span boosts fix semantic rank without session lock |

The lexical evidence query language unifies these threads: **transparent plans** that preserve authority, exploit routes/titles/entities, and remain robust as the activated corpus grows.
