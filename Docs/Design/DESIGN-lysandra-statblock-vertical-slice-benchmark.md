# Design: Lysandra vertical slice — agentic benchmark

**Status:** Active (Steps 0–4 implemented; harness consolidation in progress)  
**Scope:** DungeonMindBuddy agent loop + corpus — from natural GM ask to grounded, quality-checked output. Statblock service integration (HTTP, validation, store) is **future scope**, not gated here.  
**First gold target:** Captain Lysandra Ironveil (corpus naming; avoid alternate spellings in fixtures). The harness is designed for any entity type — NPC, location, faction — with per-target gold config.

---

## 1. What this slice proves

An **agent loop** (not a prescripted pipeline) can:

1. Receive a **natural GM ask** (no embedded instructions or step-by-step runbooks in the user message).
2. **Discover** which corpus files matter for this entity by navigating hub READMEs, following cross-links, and reading the right files — using only its permanent planner instructions and available tools.
3. **Ground** its answer in the real corpus content it read (not hallucinated paths, not retyped stat lines from memory).
4. Produce an **output** that is relevant, addresses the ask, and is grounded in what it actually retrieved.

Until all gates pass, the benchmark **fails**; partial progress is reported **per step** for debugging.

### What this slice does NOT prove (future scope)

- That the output is a valid structured statblock JSON (Steps 5–6: service call + schema validation).
- That the output is rules-legal (Step 7: legality checks).
- That the result is persisted and round-trips through a store (Step 8).
- That the creative prose is subjectively "good" (LLM-as-judge or human eval — not gated in v1).

---

## 2. Success criterion (single sentence)

**Benchmark pass** iff the agent, given a natural user ask and the corpus, produces a grounded response that demonstrates it **found**, **read**, and **used** the right entity files — with **no gate violations** on retrieval, canonical selection, baseline extraction, or context assembly.

---

## 3. Definitions

| Term | Meaning |
| --- | --- |
| **Grounding corpus** | `corpus/eldyrwild-markdown/` (or successor root) with a **pinned fingerprint** (hash of relevant subtree or full corpus per existing planner practice). |
| **Gold target** | The entity the benchmark is about. Identified by a **gold config** that includes aliases, corpus policy, expected outcomes. Today: an NPC (Lysandra). Tomorrow: a location, faction, item — same harness shape. |
| **Canonical baseline** | The single authoritative prior file for this entity **selected by policy** (Section 4), not merely the first search hit. For NPCs this is typically a statblock; for other entity types it could be a different document. |
| **Level up / power increase** | Increase in entity **power state**. By default CR-oriented for NPC statblocks; class-level progression is optional and must be explicit. Ambiguous user language ("level her up") requires intent disambiguation. |
| **Natural user ask** | A prompt that sounds like a real GM talking to a tool — not a numbered checklist of steps, not a prescriptive "first open X, then read Y." The agent must figure out what to do. |

### 3.1 Target corpus hierarchy (setting seed vs campaign lives)

This is the **directory schema we want when serious writing and ingestion catch up**. It separates **world bible** (pre–player-contact) from **table canon** (what happened in each Longmont campaign), so statblocks and timelines do not fight each other.

**1. Elderwyld / Mirathorn (setting — character seed)**

- **Purpose:** Who the NPC is in *your* narrative world **before** meaningful contact with the players; Mirathorn-local context.
- **Suggested layout** (under something like `Elderwyld/Cities and Towns/Mirathorn/NPCs/<npc_slug>/`):
  - `README.md` — one-screen map of files below.
  - **Character seed** (prose or structured notes): baseline concept, role in the city, hooks before the party arrives.
  - **Original statblock** — first mechanical export you treat as the setting's "day zero" sheet.
  - **Mirathorn-facing CR2 sheet** (or equivalent) — the concrete **CR 2** (or other fixed tier) statblock that belongs to the *setting* presentation (e.g. city guard stat block as published in the world), distinct from "whatever the table is using after six sessions."
- **Rule:** Do not bury the only copy of a **campaign-specific level-up** here; those belong under the campaign that earned them (below).

**2. Longmont Campaign / Campaign `<n>` / NPCs / `<npc_slug>` (per-campaign package)**

- **Purpose:** Everything the **table** needs for that campaign: continuity, prep, mechanical history **for that timeline**.
- **Suggested layout** (e.g. `Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/`):
  - `README.md` — links into recaps, Mirathorn seed folder, and "which statblock is current for C2."
  - `timeline.md` (or session-indexed notes) — what changed **in this campaign** and when.
  - **Character dossier** — voice, psychology, table-use (can remain one canonical `*_character_dossier.md`).
  - **Level-up statblocks** — **one file per campaign-locked mechanical state** (e.g. after a specific arc or session); name with campaign + tier or level so gates and humans agree (`*_statblock_c2_post_sess17_cr3.md`, etc.). If the same NPC levels in **Campaign 1** and **Campaign 2**, each level-up sheet lives **only** under the folder for the campaign where that progression happened.

**3. Policy / benchmark implication**

- `corpus_policy` (or gold) should be able to name **several** mechanical paths with **roles**: e.g. `setting_original_statblock`, `setting_mirathorn_cr2`, `campaign_c2_current_statblock`, so retrieval does not conflate "CR as creature" with "class level at the table."
- Fingerprint and eval gold must be refreshed whenever files move under `corpus/eldyrwild-markdown/`.

**4. Current corpus (implemented hub layout)**

- **Setting:** `Elderwyld/Cities and Towns/Mirathorn/NPCs/captain_lysandra_ironveil/` — `character_seed.md`, `captain_lysandra_ironveil_statblock_cr2.md`, `README.md`.
- **Campaign 2 table:** `Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/` — `captain_lysandra_ironveil_character_dossier.md`, `README.md`, `timeline.md`.
- **C2 level-up exports:** add under the C2 hub when authored. **Distinct `statblock_original`:** add under the Mirathorn hub when you split it from CR2.

---

## 4. Canonical baseline policy (must be fixed before Step 2 gates)

Retrieval cannot define "most recent" without a **policy object**. The benchmark loads a **gold policy file** (committed JSON), e.g. `evals/lysandra_vertical_slice/gold/corpus_policy.json`:

Suggested fields:

- `entity_primary_names`: `["Captain Lysandra Ironveil", "Lysandra Ironveil", …]`
- `statblock_candidate_globs` or explicit `candidate_paths[]` (maintainer-curated inventory of every file that might contain a statblock).
- `recency_key`: one of `path_session_number`, `git_mtime`, `frontmatter_updated`, `explicit_rank_order`.
- `canonical_path`: optional override if policy is "always this file regardless of others."
- `session_anchor`: path or id of the **latest session recap or prep** that bounds "current campaign moment" for this slice.

**Gate 2** (below) asserts the selected canonical path **equals** `gold.canonical_path` **or** matches `gold.selection_rule` evaluated deterministically on the candidate set.

---

## 5. Benchmark harness — one entrypoint, config-driven

### Design principle

The harness is **one entrypoint** that:

1. Loads a **config** (gold target identity, user query, expected outcomes).
2. Runs the **agent loop** (`run_planning_turn_detailed` with real tools, real corpus, real instructions — no injected scripts).
3. **Judges the result** against the config's expected outcomes.

The user query in the config is **natural language** — the kind of thing a GM would actually type. The agent's job is to figure out what to do with it.

### Config shape (target)

```json
{
  "id": "lysandra_upgrade_prose",
  "gold_target": {
    "entity_canonical_name": "Captain Lysandra Ironveil",
    "corpus_policy_path": "gold/corpus_policy.json"
  },
  "user_query": "Lysandra needs to be tougher for the siege arc — bump her up.",
  "expected_outcomes": {
    "retrieval": {
      "must_read_paths_containing": ["lysandra", "statblock"],
      "min_corpus_reads": 3
    },
    "output": {
      "must_contain_substrings": ["Lysandra"],
      "min_output_chars": 200
    }
  },
  "model_policy": "MODEL_POLICY.json"
}
```

The config is generic: `gold_target` could name any entity type. `expected_outcomes` are key-value checks, not hardcoded to CR or statblocks.

### What exists today (and the gap)

Today the harness is split across independent step scripts (`step1_planner_trace.py`, `step2_canonical_intent.py`, etc.) each with their own `main()`. The planner trace CLI (`step1_planner_trace.py`) is the closest to the one-entrypoint model — it runs the agent, scores the result, writes an artifact. But the deterministic steps (2–4) run separately and judge corpus structure, not agent output.

**Gap:** A single harness that loads config, runs the agent, and applies all relevant gates to the result in one pass.

---

## 6. Steps and gates

Each step produces a **structured trace record**. A step **fails closed**: later steps **do not run** unless earlier steps pass (or are explicitly marked optional; default is strict).

### Step 0 — Environment and corpus pin

| Gate ID | Predicate |
| --- | --- |
| `G0.1` | Corpus root exists and matches `gold.corpus_root` (or env override documented). |
| `G0.2` | `corpus_fingerprint` matches `gold.expected_fingerprint` **or** benchmark run documents `allow_fingerprint_drift: true` with explicit waiver (default **false**). |

### Step 1 — Agent retrieval (planner trace)

**What this is:** One bounded `run_planning_turn_detailed` call with a **natural user query** + normal planner `instructions` + tools + `dispatch_tool` → `PlanningTurnDetail.tool_trace` + `final_text`.

**What passing must convince us of:**

1. **Grounded file choice** — the agent actually **opened** corpus files via `read_corpus_file` with valid relative paths, not hallucinated paths in prose.
2. **Recall adequacy** — the files the gold config says are important appear somewhere in the tool trace.
3. **No runaway loop** — `hit_tool_round_limit` is false.
4. **Output exists and is non-trivial** — the final text is non-empty and addresses the entity.

**What passing does NOT prove:** output quality, correct level-up math, or statblock legality — only that the agent chose relevant files and produced a response.

| Gate ID | Predicate |
| --- | --- |
| `P1.1` | Deduped corpus read paths from `tool_trace` include paths matching `expected_outcomes.retrieval.must_read_paths_containing` substrings. |
| `P1.2` | `hit_tool_round_limit` is false. |
| `P1.3` | `final_text` is non-empty and ≥ `expected_outcomes.output.min_output_chars`. |
| `P1.4` | `final_text` contains `expected_outcomes.output.must_contain_substrings`. |

#### Corpus keyword regression check (offline, no LLM)

Separate from the agent benchmark. `step1_retrieval.py` runs keyword scoring over markdown files to verify **lexical signal exists** in the corpus for this entity. Useful for gold authoring, regression when corpus text moves, and CI without an API key. Does **not** prove the agent would open those files.

| Gate ID | Predicate |
| --- | --- |
| `G1.1` | `gold.required_paths_retrieved` ⊆ top-`K` paths (set inclusion). |
| `G1.2` | Canonical path from policy is in the top-`K`. |
| `G1.3` | No retrieved path is outside `corpus_policy.corpus_roots_allowed_prefixes`. |

### Step 2 — Identify canonical baseline

**Inputs:** `corpus_policy.json` — canonical path is `canonical_statblock_relpath`.
**Outputs:** `canonical_path`, `selection_reason`, `extracted_markdown`, `extracted_section_span`, marker checks, parsed fields (e.g. Challenge Rating).

| Gate ID | Predicate |
| --- | --- |
| `G2.1` | Selected `canonical_path` matches gold policy. |
| `G2.2` | Extracted content contains **required markers** from gold (e.g. `Armor Class`, `Hit Points`, `Challenge Rating`). |
| `G2.3` | **Single** selection: no unresolved ties. |

### Step 2.4 — Intent classification

**Inputs:** User ask (`classify_intent(user_line)` — LLM-backed, cheap model from `MODEL_POLICY.json`; test doubles for offline).
**Outputs:** `intent_mode`, `power_axis`, optional `clarifier_question`, `clarifier_required`.

| Gate ID | Predicate |
| --- | --- |
| `G2.4.1` | Classifier emits one of: `factual_lookup`, `upgrade_request`, `comparison_request`. |
| `G2.4.2` | `power_axis` is one of: `challenge_rating`, `class_level`, `hybrid`, `unknown`. |
| `G2.4.3` | If mode implies **upgrade** and axis is ambiguous, `clarifier_required == true` and `clarifier_question` is non-empty. |
| `G2.4.4` | Factual mode does not force class-level when only CR evidence exists. |

### Step 3 — Power baseline extraction

**Status:** Implemented (deterministic v1). Re-parses the canonical body for power baseline fields and evidence spans.

| Gate ID | Predicate |
| --- | --- |
| `G3.1` | `challenge_rating_current` equals gold expectation. |
| `G3.2` | Evidence spans resolve to **verbatim** slices of the canonical body (`body[start_char:end_char]`). |
| `G3.3` | `class_level_current` may be `null`; non-null requires gold approval. |
| `G3.4` | If CR is absent, gold `fallback_when_cr_absent` is applied. |

### Step 4 — Level-up context bundle

**Status:** Implemented (deterministic v1). Assembles a **structured bundle** for gates, regression, and tooling — not assembled for any agent prompt.

Bundle includes: `power_baseline`, `power_target` (axis + value from gold), statblock + dossier + timeline excerpts, optional session anchor, keyword-ranked recap snippets.

| Gate ID | Predicate |
| --- | --- |
| `G4.1` | Target is strictly above baseline on the gated axis. |
| `G4_RECAP` | Recap snippet count ≥ gold minimum; union of `verbatim` contains required substrings. |
| `G4_TIMELINE` | When gold requires it, policy pins a timeline path and the bundle excerpt is non-empty. |

---

## 7. Post-planner benchmark (Step 2 observation after agent turn)

After the agent turn (Step 1), the harness **optionally** runs `evaluate_step2_post_planner_benchmark`: classifies the same `user_message` the agent saw and checks whether statblock reads in the tool trace include the canonical path from policy. This is **observation / scoring only** — it does not change what the agent does. Violations merge under key `step2_bridge` on `LiveEvalResult`.

Gold key: `planner_bridge` in `step2_canonical_and_intent.json` (historical name; see `Docs/Plans/NAMING-benchmark-vs-runtime.md`).

---

## 8. Future scope (Steps 5–8)

These steps are defined but **not implemented or gated** in this slice:

- **Step 5** — HTTP call to StatblockGenerator (structured JSON response, not just markdown).
- **Step 6** — Schema validation (Pydantic/JSON Schema against `schema_version`).
- **Step 7** — Legality validation (deterministic 5e rules checks against a named `legality_profile`).
- **Step 8** — Store write + read-back with provenance.

When these land, they'll need: a versioned API contract (Section 9), a legality profile, and store backend selection.

---

## 9. API contract (Buddy ↔ StatblockGenerator) — future

| Concern | Requirement |
| --- | --- |
| **Request** | Versioned POST body with `schema_version`, entity name, description, optional `prior_statblock`, target power, legality profile. |
| **Response** | Structured JSON under a fixed key **in addition to** optional markdown. |
| **Errors** | Non-2xx returns JSON `{ "error_code", "message", "details" }`. |

StatblockGenerator rework is out of scope for this design, but in scope for **dependency** when Steps 5–8 activate.

---

## 10. Gold data

| Artifact | Role |
| --- | --- |
| `gold/corpus_policy.json` | Canonical path selection, aliases, session anchor, timeline path. |
| `gold/step0_environment.json` | Corpus fingerprint pin. |
| `gold/step1_retrieval.json` | Keyword regression: required paths, scan dirs, top-K. |
| `gold/planner_step1_*.json` | Agent benchmark scenarios: user query, expected tool trace, output gates. |
| `gold/step2_canonical_and_intent.json` | Canonical markers, intent fixtures, post-planner benchmark config. |
| `gold/step3_power_baseline.json` | Expected power baseline, evidence span fields. |
| `gold/step4_levelup_context.json` | Power target, recap assertions, timeline requirement. |

When corpus text changes, **gates fail until gold is updated** — intentional (prevents silent drift).

---

## 11. Risks and mitigations

| Risk | Mitigation |
| --- | --- |
| Multiple files for same entity, ambiguous canonical | Gold `corpus_policy` + explicit `G2.1`. |
| Power field not in statblock text | Gold documents fallback; `G3.4`. |
| Agent prescripted by user message | User queries must be natural language; no embedded step instructions. |
| Corpus rearrangement breaks gates | Fingerprint pin (`G0.2`) + gold refresh process. |
| Flaky LLM retrieval | Separate offline keyword regression check (no LLM) runs in CI cheaply. |

---

## 12. Implementation phases

1. **Gold pack + Step 0** (**DONE**): corpus survey, `corpus_policy.json`, `step0_environment.json`, `step0_corpus_environment.py`.
2. **Step 1 keyword regression** (**DONE**): `step1_retrieval.py` (offline corpus signal check).
3. **Step 1 agent benchmark** (**DONE**): `step1_planner_trace.py` — `run_planner_step1_turn()`, scenario gold files, CLI with artifact.
4. **Step 2 + 2.4** (**DONE**): canonical selection + intent classification (LLM-backed with test doubles).
5. **Step 3** (**DONE**): `power_baseline` + evidence spans.
6. **Step 4** (**DONE**): level-up context bundle + gates.
7. **Harness consolidation** (**NEXT**): single entrypoint that loads config, runs agent, applies all gates. Naturalize user queries in gold.
8. **Output quality gates** (**NEXT**): beyond "files opened" — is the output grounded, relevant, and complete?
9. **Steps 5–8** (**FUTURE**): StatblockGenerator HTTP, schema, legality, store.

---

## 13. Related documents and code

- Agent loop: `src/agent/planner.py` (`run_planning_turn_detailed`, `make_tool_dispatcher`, `_planner_tools_responses`).
- Intent + skill routing: `src/agent/skill_pipeline.py`, `src/npc_statblock_pipeline/canonical_intent.py`.
- Corpus path tools: `src/agent/corpus_path_tools.py`.
- NPC power-increase skill (human/IDE): `.cursor/skills/npc-power-increase/SKILL.md`.
- Flow doc: `Docs/Plans/FLOW-npc-power-skill-pipeline.md`.
- Naming conventions: `Docs/Plans/NAMING-benchmark-vs-runtime.md`.
- Corpus layout rules: `.cursor/rules/corpus-layout-conventions.mdc`.
- LLM context discovery rules: `.cursor/rules/llm-context-discovery.mdc`.
- Stepped eval pattern: `evals/planner_slice/live_eval.py`.
- Gate completion signpost: `evals/lysandra_vertical_slice/GATES.md`.

---

**Document owner:** DungeonMindBuddy / vertical slice workstream.  
**Next action:** Consolidate harness to single config-driven entrypoint; naturalize gold user queries; add output quality gates.
