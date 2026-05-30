# C2S23 Dogfood — Manual Baseline Capture

**Campaign:** longmont-c2  
**Planning session:** 23  
**Source sessions:** 21, 22  
**Benchmark seed:** `evals/c2_live_prep/benchmarks/c2s23_dogfood_questions.seed.json`  
**Charter:** `Docs/Plans/BENCHMARK-c2s23-dogfood-planning-charter.md`

Copy one block per question. Do not fill gold answers from corpus survey before attempting the question in the live workflow.

---

## Run metadata

| Field | Value |
|-------|-------|
| Date | |
| Operator | |
| Live workspace path | |
| Recap ingest path (CLI / pane) | |
| Session 22 ingest complete (Y/N/partial) | |
| Breadcrumb state | |
| Session memory materialized (Y/N) | |

---

## Question record (duplicate per question)

### {question_id}

| Field | Value |
|-------|-------|
| **question id** | |
| **question** | |
| **manual answer** | |
| **sources consulted** | (paths, modules, or APIs) |
| **source roles** | (comma-separated: pre_canonical_evidence, canon_play, derived_memory, planning_scaffold, reference_tool, live_observation, audit) |
| **authority notes** | (mistakes avoided or made; which tier answered play facts) |
| **artifact actions desired** | (from seed `expected_artifact_actions` + anything else) |
| **artifact actions attempted** | (what you actually ran; include failures) |
| **friction** | (missing tool, wrong retrieval, UI confusion, stale index, etc.) |
| **confidence** | (high / medium / low) |
| **evaluator notes** | (follow-up PR, capability inventory update, authority trap outcome) |

---

## Example (structure only — do not treat as gold)

### auth-02

| Field | Value |
|-------|-------|
| **question id** | auth-02 |
| **question** | A rolled result on a prep travel table… |
| **manual answer** | No. Roll tables are reference_tool; they do not prove play. |
| **sources consulted** | RUNBOOK authority section; live_packet known_roll_tables (empty) |
| **source roles** | reference_tool, audit |
| **authority notes** | Refused to cite table roll as play fact. |
| **artifact actions desired** | — |
| **artifact actions attempted** | Read inspector only |
| **friction** | No registered roll tables on packet for S23 workspace |
| **confidence** | high |
| **evaluator notes** | PR95 for table seeding + create |

---

## Round summary (after all questions)

| Metric | Count |
|--------|-------|
| Questions attempted | |
| High confidence | |
| Authority traps passed | |
| Authority traps failed | |
| Blocked by missing capability | |
| Recommended PR95 items | |
| Recommended PR96 items | |

**Stop conditions met?** (Y/N — see charter)

**Next action:**
