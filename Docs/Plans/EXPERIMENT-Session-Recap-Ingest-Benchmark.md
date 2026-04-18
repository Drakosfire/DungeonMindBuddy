# EXPERIMENT — Session Recap Ingest Benchmark (hand-off plan)

**Status:** ready for implementation hand-off (no code written yet).
**Author:** designed April 2026 from the manual Session 20 ingest pass; transcript [a073c164-9fc1-4c03-a888-2d71dd08bc22](a073c164-9fc1-4c03-a888-2d71dd08bc22).
**Scope contract:** `Docs/Plans/SCOPE-B-GOLD-Session-20-Ingest.md` (the "what passes" spec). This file specifies the "how it gets graded" experiment.
**Provenance:** `Docs/Plans/PROCESSING-NOTES-Session-20-Manual-Ingest.md` (the manual-ingest log that derived the gold).

---

## 1. Goal

Prove the `session-summary-from-notes` skill is **working and robust** by passing a benchmark that grades, against frozen gold, every artifact and behavior the skill produces from a single fixed raw-notes input — and detects regression on any of them.

A passing benchmark proves four things:

1. **Mechanical ingest is deterministic.** Given `Session 20 Recap.txt`, the canonical recap file (`Session 20 - Recap.md`) is byte-equal to gold every run. (Scope-A.)
2. **Writer safety holds.** Two-phase commit, allowlist, and dossier-immutability are enforced on every write attempt; no silent writes occur. (Cross-cutting C-gates.)
3. **Review surface is correct in shape.** Timeline rows, dual-hub creates, and footer pointers land at the right paths with exact-text matches where specified and shape matches where specified. (Scope-B.)
4. **Unsure queue surfaces the right questions.** The model identifies the small set of judgment items it cannot default confidently and asks them as structured questions at end-of-run. (Scope-B §E gates.)

A failing benchmark identifies *which* of these four broke, with diagnostic output sufficient to localize the regression to a file, function, or prompt block.

---

## 2. Why this benchmark, why now

We have **one real artifact pair** on disk now (`Session 20 Recap.txt` + the canonical `Session 20 - Recap.md` + the dual-hub Mossford NPC files). The manual ingest pass produced a frozen gold spec covering 9 deliverables. The next real recap is unknown (waiting on the GM's table). This is the moment to **lock down regression detection on what we have** before the next artifact arrives — so the next ingest stress-tests the skill against a fixed bar instead of recalibrating "what good looks like" from scratch.

The benchmark is **single-fixture, multi-gate**. It is not a generalization test. Generalization arrives when we have ≥ 2 real recap+notes pairs; until then, the benchmark proves repeatability + regression detection + writer safety.

---

## 3. Scope partition

The skill has two graded surfaces with very different cost/runtime/grading shapes. The benchmark mirrors that split.

### 3.1 Scope-A — Mechanical recap ingest

| Aspect | Value |
|---|---|
| What it grades | The deterministic transformation of `Session 20 Recap.txt` → `Session 20 - Recap.md`. |
| Grading mode | **Byte-equal** to gold (and structural sub-gates A1–A7 for diagnostic). |
| Runtime | **No LLM call.** Pure-function pipeline. |
| Speed | Sub-second per run. |
| Test framework | `pytest` (`tests/test_session_20_scope_a_gold.py`). |
| Fixture | `Session 20 Recap.txt` (input, repo root) + `corpus/.../Session 20 - Recap.md` (gold, on disk). |

**Belongs to Scope-A:** frontmatter emission, H1 normalization, leading-title-line stripping, robust paragraph splitting, duplicate-paragraph detection, identity transform on remaining body.

### 3.2 Scope-B — Review surface + unsure queue

| Aspect | Value |
|---|---|
| What it grades | The planner's behavior when run with `--allow-corpus-writes` against `Session 20 Recap.txt`: which files it creates / appends, which questions it surfaces in the unsure queue, which findings it reports. |
| Grading mode | **Per-§J-item** (9 items in `SCOPE-B-GOLD-Session-20-Ingest.md`). Mix of byte-equal (timeline rows, footer pointers) and shape (READMEs, dossier sections, unsure-queue questions). |
| Runtime | **Live LLM call** (real model, real planner loop). |
| Speed | 30–90 seconds per run (one full planning session, 2–4 turns with two-phase commit cycles). |
| Test framework | Scenario-based eval slice (`evals/session_recap_ingest_vertical_slice/`), modeled after `evals/npc_voice_vertical_slice/`. |
| Fixture | Frozen pre-state corpus snapshot + `Session 20 Recap.txt`. |

**Belongs to Scope-B:** §B Lysandra timeline append, §C dual-hub creation for Marla, §D Mossford backfill (Stacey, Stuart, Mayor/Sheriff stubs), §E unsure queue (3 questions), §F bidirectional pointers, §G/§H/§I findings.

### 3.3 Cross-cutting — Writer-safety gates (the C-gates)

These apply to **every write tool call** in Scope-B and are graded from the planner's tool trace:

- C1: Every commit was preceded by a `dry_run=true` call that returned a `confirm_token`.
- C2: Every commit echoed the matching `confirm_token`.
- C3: At least one **negative** test confirms stale-token rejection (run a chaos scenario where content is mutated between dry-run and commit; assert the writer refuses).
- C4: Zero writes occur on dossier / seed / statblock paths (allowlist deny enforcement).
- C5: Allowlist-gap paths (§H) produce **rejection messages, not silent fallback** (the planner must surface the gap as a finding, not just skip the write).

The C-gates use the same tool-trace inspection as Scope-B and are evaluated in the same runner.

---

## 4. Fixture inventory

### 4.1 Inputs (fixed; do not modify)

| File | Role | Size |
|------|------|------|
| `Session 20 Recap.txt` | Raw GM notes (24 lines, 1 duplicated paragraph). | ~7 KB |
| `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/Session 17 - Migrating Forest and Thrin.md` | Pattern reference (Scope-A shape survey). | ~10 KB |
| `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/Session 18 - Recap.md` | Pattern reference. | ~9 KB |
| `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/Session 19 - Recap.md` | Pattern reference (canonical title form). | ~8 KB |
| `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Prep/session_20_stacey_stuart_marla_reference.md` | Companion prep doc (Scope-B §F target). | ~14 KB |
| `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/timeline.md` | Append target (Scope-B §B). | existing |

### 4.2 Gold artifacts (frozen; benchmark grades against)

| File | Role |
|------|------|
| `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md` | Scope-A gold (byte-equal). |
| `Docs/Plans/SCOPE-B-GOLD-Session-20-Ingest.md` | Scope-B contract (human-readable; machine-readable JSON form is **needed**, see §6). |
| `corpus/eldyrwild-markdown/Elderwyld/Cities and Towns/Mossford/NPCs/marla_brambleback/{README.md, character_seed.md}` | Scope-B §C.1 gold (byte-equal). |
| `corpus/eldyrwild-markdown/Elderwyld/Cities and Towns/Mossford/NPCs/stacey_brambleback/{README.md, character_seed.md}` | Scope-B §D.1 gold (byte-equal). |
| `corpus/eldyrwild-markdown/Elderwyld/Cities and Towns/Mossford/NPCs/stuart/{README.md, character_seed.md}` | Scope-B §D.2 gold (byte-equal). |

### 4.3 Pre-state corpus snapshot (NEW; needed)

To run Scope-B **repeatably**, we cannot just point the planner at the live corpus — the recap and the Mossford files already exist there. The benchmark needs a frozen "pre-ingest" snapshot of the corpus where:

- `Session 20 - Recap.md` does **not** exist.
- `Mossford/NPCs/` does **not** exist (or is empty).
- `marla_brambleback/`, `stacey_brambleback/`, `stuart/` do **not** exist in either hub.
- Lysandra `timeline.md` does **not** have row 20.
- Footer pointers on the recap and prep doc do **not** exist.
- Everything else is byte-identical to the current corpus.

**Mechanism:** the eval runner copies the corpus to a tmpdir, then deletes/truncates the listed files, then points the planner at the tmpdir. See §7.3 for the runner pattern.

---

## 5. Gates (the explicit pass/fail list)

A benchmark run produces a JSON report with one boolean per gate. **Pass = all gates true.** Diagnostic output explains each fail.

### 5.1 Scope-A gates

| Gate | Description | How |
|------|-------------|-----|
| A1 | Frontmatter is the 8-field set with exact values for session=20, campaign_id=longmont-c2, etc. | YAML parse + field assertion. |
| A2 | H1 line is exactly `# Session 20 Recap`. | First non-frontmatter line. |
| A3 | Body has 11 paragraphs (12 in source minus 1 duplicate). | Robust paragraph split + count. |
| A4 | Duplicate detection report flagged source paragraphs at lines 6 and 10. | Inspect helper output. |
| A5 | Body does not start with the literal string `Session 20 Recap`. | First-line check after frontmatter+H1. |
| A6 | Robust splitter correctly separated source lines 5/6 (no trailing blank between them). | Inspect splitter output paragraph boundaries. |
| A7 | Body content is byte-equal to source minus duplicate, after stripping the leading title-only line. | String diff. |
| A8 | **Output file is byte-equal to gold `Session 20 - Recap.md`.** | `filecmp` / hash. (Subsumes A1–A7; the others exist for diagnostic granularity.) |

### 5.2 Scope-B gates (mirrors `SCOPE-B-GOLD-Session-20-Ingest.md` §J)

| Gate | Description | Grading |
|------|-------------|---------|
| B1 | §A recap byte-equal to `Session 20 - Recap.md` gold. (Equivalent to A8 but graded in the live-run context.) | byte-equal |
| B2 | §B Lysandra timeline row appended verbatim at the correct path. | exact-text after split-on-`\n` |
| B3 | §C.1 Marla setting hub README exists (shape) + `character_seed.md` byte-equal. | shape + exact |
| B4 | §C.2 Marla campaign hub README exists (shape) + dossier exists with required H1 + section headers (shape) + `timeline.md` row exact text. | shape + exact-row |
| B5 | §D.1 Stacey setting-hub README exists (shape) + `character_seed.md` byte-equal. | shape + exact |
| B6 | §D.2 Stuart setting-hub README exists (shape) + `character_seed.md` byte-equal. | shape + exact |
| B7 | §E Unsure queue contains exactly 3 items, ids = {tower_blueprint_placement, mayor_sheriff_names, stuart_surname}; each item's question text matches gold question shape (regex). | shape (regex on question + presence of default) |
| B8 | §F.1 + §F.2 footer blockquotes appended verbatim to the recap and prep doc. | exact-text |
| B9 | §G + §H findings present in run report (Sara, Frank, Tealeaf as backfill backlog; 6 allowlist patterns as gaps). | substring match per finding |

§I (no-action set) is enforced as a **negative gate** in C-gates (no spurious file creations).

### 5.3 Cross-cutting C-gates

| Gate | Description | How |
|------|-------------|-----|
| C1 | Every `write_corpus_file` and `append_timeline_row` commit was preceded by a `dry_run=true` call returning a `confirm_token`. | Tool-trace pairing check. |
| C2 | Every commit echoed the matching `confirm_token`. | Tool-trace argument inspection. |
| C3 | A separate **chaos scenario** mutates content between dry-run and commit; the writer rejects with `stale confirm_token`. | Dedicated test in `test_corpus_writer.py` (covered today; promote to benchmark gate). |
| C4 | Zero write attempts on dossier / seed / statblock paths in the trace. | Path filter on tool calls. |
| C5 | Each §H allowlist-gap path attempted in the trace produces a rejection that the planner surfaces as a finding (not silently skipped). | Tool-trace rejection inspection + finding-text check. |
| C6 | After all commits, the corpus fingerprint reported by the writer matches a recompute over the post-state tmpdir. | `recompute_corpus_fingerprint` parity. |
| C7 | No file outside the gold-listed paths was created or modified. | Pre-state vs post-state diff over tmpdir. |

### 5.4 Pass/fail summary

The benchmark passes iff: **all of A1–A8, B1–B9, C1–C7 are true** for one execution.

---

## 6. Existing infrastructure (inventory)

### 6.1 Code modules — reuse as-is

| Module | What it gives us |
|--------|------------------|
| `src/agent/corpus_writer.py` | `is_writable_corpus_path`, `write_corpus_file` (two-phase), `append_timeline_row`, `recompute_corpus_fingerprint`. C1, C2, C3, C4 enforcement is built in. Allowlist regexes: `_CREATE_ALLOWED_RE`, `_TIMELINE_RE`, `_HUB_README_RE`, `_DENY_BASENAMES`. |
| `src/agent/planner.py` | `run_planning_turn_detailed`, `make_tool_dispatcher`, `_planner_tools_responses`, `build_corpus_path_ref_index`. Conditional registration of write tools via `allow_corpus_writes` flag. |
| `src/agent/planner_cache.py` | `load_or_build_planner_instructions` (write-tools-on cache key), `corpus_fingerprint`. |
| `src/agent/planner_turn_output_schema.py` | Turn envelope schema with `needs_clarification`. **Will need extension** for `unsure_queue` (see §7.4). |
| `src/agent/skill_pipeline.py` | `scenario_key_for_user_line` — used by the npc_voice slice; reusable for routing the recap-ingest scenario. |
| `src/prompts/corpus_session_planner.py` | `_WRITE_TOOLS_ADDENDUM` documents the writer contract to the model. **Will need extension** for the unsure-queue primitive (see §7.4). |

### 6.2 Eval scaffolding — patterns to copy

| Pattern | Source | Reuse for |
|---------|--------|-----------|
| Per-scenario gold JSON with `final.require.{output_must_be_json_object, output_json_must_include_keys, output_json_message_contains_any}` | `evals/npc_voice_vertical_slice/gold/scenarios/torbin_clarify_bump_cr.json` | Unsure-queue question shape grading (B7). |
| Step 0 corpus environment pin (fingerprint + statblock service gate) | `evals/lysandra_vertical_slice/gold/step0_environment.json` + `step0_corpus_environment.py` | Recap-ingest slice's pre-state pin. |
| Live-eval scenario runner with tool-trace capture and per-step gates | `evals/planner_slice/live_eval.py` (`evaluate_scenario_detail`, `LiveEvalResult`) | The Scope-B runner. Read existing `tool_trace`, `corpus_fingerprint`, `report_path` shapes. |
| Suite report rendering + per-run dated artifacts | `evals/planner_slice/live_report.py` + `npc_voice_vertical_slice/artifacts/` layout | Recap-ingest slice's report directory. |
| Two-phase commit unit tests | `tests/test_corpus_writer.py` (allowlist + token + create/append) | C-gate base; promoted to benchmark via tool-trace inspection. |
| Write-dispatch integration tests | `tests/test_planner_write_dispatch.py` | C5 enforcement check (rejection surfacing). |
| Multi-step benchmark with environment-pinned step 0 + planner step 1 + gold matchers | `evals/lysandra_vertical_slice/step1_planner_trace.py` (`_DEFAULT_PLANNER_STEP1_SCENARIO_KEY`, `evaluate_scenario_detail`) | Recap-ingest slice's step-by-step structure. |

### 6.3 Telemetry / cost tracking — reuse

| Module | Use |
|--------|-----|
| `src/agent/planner_telemetry.py` (`text_sig`, `maybe_full_text`) | Trace logging. |
| `src/agent/planner_pricing.py` | Per-run cost estimate in the report. |
| `PLANNER_REVIEW_MODE=summary\|debug\|forensics` env var | Verbosity control. |
| `PLANNER_LOG_FULL_IO=1` | Full request/response capture for forensic reruns. |

### 6.4 Required runtime flags (already supported)

- `dmb plan --allow-corpus-writes` (CLI) **or** `DUNGEONMIND_PLANNER_ALLOW_WRITES=1` (env). Documented in `.cursor/rules/dungeonbuddy-environment.mdc`.
- `out/planner_eval_cache/` — cleared between runs only if the system instructions change (write-tools-on uses a separate cache key automatically).

---

## 7. Required infrastructure (what to build)

Six concrete deliverables. Each is small and independently testable.

### 7.1 Pure-function helpers for Scope-A — **NEW MODULE**

**File:** `src/agent/recap_ingest_helpers.py`

**Functions** (all pure; no IO; no LLM):

```python
@dataclass(frozen=True)
class Paragraph:
    text: str
    source_line_start: int  # 1-indexed line in raw notes
    source_line_end: int

@dataclass(frozen=True)
class DuplicateMatch:
    a: Paragraph
    b: Paragraph

def split_paragraphs_robust(body: str) -> list[Paragraph]:
    """Split on blank lines AND on isolated single newlines between sentence-complete blocks."""

def detect_duplicate_paragraphs(paragraphs: list[Paragraph]) -> list[DuplicateMatch]:
    """Exact-string compare (after whitespace normalization). Caught Session 20 lines 6/10."""

def strip_leading_title_line(body: str, session_number: int) -> tuple[str, bool]:
    """If first non-blank line matches `Session {N} Recap[:]?`, strip it. Return (new_body, was_stripped)."""

def emit_recap_frontmatter(*, session: int, campaign_id: str, title: str | None = None) -> str:
    """The 8-field invariant set. Title defaults to f'Session {N} - Recap'."""

def assemble_recap(*, raw_notes: str, session: int, campaign_id: str, remove_duplicates: bool = True) -> tuple[str, IngestReport]:
    """Compose frontmatter + H1 + de-duped body. Return (full_file_text, report)."""

@dataclass(frozen=True)
class IngestReport:
    title_line_stripped: bool
    duplicates_detected: list[DuplicateMatch]
    duplicates_removed: list[DuplicateMatch]
    paragraph_count_in: int
    paragraph_count_out: int
```

**Tests:** `tests/test_recap_ingest_helpers.py` — one test per function; round-trip on Session 20 input.

**Estimated effort:** 1 focused session. ~200 lines of code, ~150 lines of tests.

### 7.2 Scope-A gold test — **NEW TEST**

**File:** `tests/test_session_20_scope_a_gold.py`

Reads `Session 20 Recap.txt`, runs `assemble_recap(...)`, asserts byte-equal to the on-disk `Session 20 - Recap.md`. One test, one assertion. Fast, no LLM.

This **is** A8; A1–A7 are covered by `test_recap_ingest_helpers.py` for diagnostic granularity.

**Estimated effort:** 30 minutes.

### 7.3 Scope-B eval slice — **NEW DIRECTORY**

**Directory:** `evals/session_recap_ingest_vertical_slice/`

Mirrors `evals/npc_voice_vertical_slice/` and `evals/lysandra_vertical_slice/`.

**Files:**

```
evals/session_recap_ingest_vertical_slice/
├── README.md                                # What this slice grades, how to run
├── step0_corpus_environment.py              # Mirror of lysandra slice; resolve corpus dir + fingerprint pin
├── step0_pre_state.py                       # NEW: build a tmpdir corpus snapshot with §4.3 deletions applied
├── step1_recap_ingest_run.py                # Run planner with --allow-corpus-writes against pre-state
├── step2_grade_against_gold.py              # Diff outputs vs gold; emit per-gate JSON report
├── step3_unsure_queue_grading.py            # Grade the unsure queue payload against gold question shapes
├── step4_chaos_two_phase.py                 # C3 chaos test: mutate content between dry-run and commit
├── gold/
│   ├── scope_b_session_20.json              # Machine-readable gold (per-path expected content + tool-trace expectations)
│   ├── scope_b_session_20_unsure_queue.json # Three expected items with question regex + default + alternatives
│   ├── scope_b_session_20_findings.json     # G/H findings the run must surface (substring list)
│   └── step0_pre_state_manifest.json        # Files to delete/truncate in the pre-state snapshot
├── fixtures/
│   └── session_20_raw_notes.txt             # Symlink or copy of `Session 20 Recap.txt` for hermetic runs
└── artifacts/
    └── runs/                                # Auto-populated; mirrors npc_voice_vertical_slice/artifacts/
```

**`scope_b_session_20.json` shape (sketch):**

```json
{
  "schema": "session_recap_ingest_scope_b_v1",
  "scenario_id": "session_recap_ingest_session_20",
  "fixture": "fixtures/session_20_raw_notes.txt",
  "campaign_hub": "Longmont Campaign/Campaign 2",
  "expected_writes": [
    {
      "id": "B1_recap_create",
      "path": "Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md",
      "mode": "create",
      "grade": "byte_equal",
      "gold_path": "../../corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md"
    },
    {
      "id": "B2_lysandra_row",
      "path": "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/timeline.md",
      "mode": "append",
      "grade": "exact_row",
      "gold_row": "| **20**  | **Mossford** is saved (forest turns east); ... |"
    },
    {
      "id": "B3_marla_setting_seed",
      "path": "Elderwyld/Cities and Towns/Mossford/NPCs/marla_brambleback/character_seed.md",
      "mode": "create",
      "grade": "byte_equal",
      "gold_path": "../../corpus/.../character_seed.md"
    }
    /* ... B4–B6, B8.1, B8.2 ... */
  ],
  "expected_tool_trace": {
    "must_read": [
      "Longmont Campaign/Campaign 2/Session Recaps/Session 19 - Recap.md",
      "Longmont Campaign/Campaign 2/Session Recaps/Session 18 - Recap.md",
      "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/timeline.md",
      "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/README.md",
      "Longmont Campaign/Campaign 2/Session Prep/session_20_stacey_stuart_marla_reference.md"
    ],
    "must_call_tool": ["read_corpus_file", "write_corpus_file", "append_timeline_row"],
    "two_phase_commit_required": true,
    "forbidden_writes": [
      "*_character_dossier.md",
      "character_seed.md",
      "*_statblock*.md"
    ]
  },
  "no_action_set": [
    "*/forest*.md",
    "*/storm*.md",
    "*/tainted_meat*.md"
  ]
}
```

**`scope_b_session_20_unsure_queue.json` shape:**

```json
{
  "schema": "unsure_queue_v1",
  "expected_items": [
    {
      "id": "tower_blueprint_placement",
      "question_must_match": "(?i)tower.{0,40}(blueprint|location|placement)",
      "default_must_mention": "Locations",
      "alternatives_min_count": 3
    },
    {
      "id": "mayor_sheriff_names",
      "question_must_match": "(?i)(mayor|sheriff).{0,80}(name|slug|canonical)",
      "default_must_mention": "stub",
      "alternatives_min_count": 2
    },
    {
      "id": "stuart_surname",
      "question_must_match": "(?i)stuart.{0,40}(surname|family|name)",
      "default_must_mention": "stuart",
      "alternatives_min_count": 2
    }
  ],
  "max_total_items": 4,
  "min_total_items": 2
}
```

**Estimated effort:** 1.5–2 focused sessions. Most of the code is the runner glue; the gold JSONs are mechanical translations of the existing markdown gold.

### 7.4 Allowlist extensions + unsure-queue schema — **MODIFY EXISTING**

**Files modified:**

| File | Change |
|------|--------|
| `src/agent/corpus_writer.py` | Add 5 regex patterns (`_SETTING_HUB_NPC_README_RE`, `_SETTING_HUB_NPC_SEED_RE`, `_CAMPAIGN_DOSSIER_CREATE_RE`, `_LOCATIONS_CREATE_RE`, `_PREP_FOOTER_APPEND_RE`); extend `is_writable_corpus_path` mode dispatch. Dossier-create is **create-only** — append/edit remains denied. Prep footer append requires content-shape check (must be a single blockquote starting with `> **`). |
| `tests/test_corpus_writer.py` | One parametrized test per new pattern: allow case + deny case. |
| `src/agent/planner_turn_output_schema.py` | Add `unsure_queue: list[UnsureItem] | None` to the turn envelope. `UnsureItem = {id: str, question: str, default_action: dict, alternatives: list[dict]}`. Backward-compatible (optional field). |
| `tests/test_planner_turn_output_schema.py` | Schema-validation tests for the new field. |
| `src/prompts/corpus_session_planner.py` | Add `_UNSURE_QUEUE_ADDENDUM` describing when and how to use the queue (≤ 4 items, sparse, defaults required, alternatives required). Extend `INSTRUCTIONS_TEMPLATE_ID` hash so cache invalidates. |

**Estimated effort:** 1 focused session. Allowlist regexes are the bulk; schema extension is small; prompt addendum is ~30 lines.

### 7.5 Pre-state snapshot machinery — **NEW HELPER**

**File:** `evals/session_recap_ingest_vertical_slice/step0_pre_state.py`

Helper that:

1. Copies `corpus/eldyrwild-markdown/` to a tmpdir (use `shutil.copytree`).
2. Reads the deletion manifest (`gold/step0_pre_state_manifest.json`).
3. Deletes the listed files / removes the listed footer blocks (regex-based for the prep-doc footer).
4. Returns the tmpdir path.
5. Exposes a fixture/`pytest` integration so the runner can use it.

**Manifest shape:**

```json
{
  "delete": [
    "Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md",
    "Elderwyld/Cities and Towns/Mossford/NPCs/marla_brambleback/",
    "Elderwyld/Cities and Towns/Mossford/NPCs/stacey_brambleback/",
    "Elderwyld/Cities and Towns/Mossford/NPCs/stuart/"
  ],
  "remove_trailing_blockquote_in": [
    "Longmont Campaign/Campaign 2/Session Prep/session_20_stacey_stuart_marla_reference.md"
  ],
  "remove_table_row_session_in": [
    {
      "path": "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/timeline.md",
      "session": 20
    }
  ]
}
```

**Estimated effort:** half a session.

### 7.6 Run protocol + Makefile target — **DOCUMENTATION + GLUE**

**Files added/modified:**

- `evals/session_recap_ingest_vertical_slice/README.md` — how to run, env vars, expected runtime, expected cost.
- Top-level `Makefile` target (or `pyproject.toml` script) `bench-recap-ingest` — runs the full slice end-to-end and prints the JSON gate report.

**Estimated effort:** 30 minutes.

---

## 8. Run protocol

### 8.1 Local one-shot run

```bash
# Required env (set once)
export DUNGEONMIND_PLANNER_ALLOW_WRITES=1
export OPENAI_API_KEY=...   # or whatever the planner uses
export PLANNER_REVIEW_MODE=summary

# Scope-A (no LLM, ~1 second)
uv run pytest tests/test_recap_ingest_helpers.py tests/test_session_20_scope_a_gold.py -v

# Scope-B (live LLM, ~60 seconds, ~$0.15)
uv run python evals/session_recap_ingest_vertical_slice/step1_recap_ingest_run.py
uv run python evals/session_recap_ingest_vertical_slice/step2_grade_against_gold.py
uv run python evals/session_recap_ingest_vertical_slice/step3_unsure_queue_grading.py

# Chaos / two-phase (no LLM, deterministic)
uv run pytest evals/session_recap_ingest_vertical_slice/step4_chaos_two_phase.py -v

# All-in-one
make bench-recap-ingest
```

### 8.2 CI integration

- Scope-A + chaos C3 + writer unit tests → run on every PR. Fast, no API key needed.
- Scope-B → run on a separate workflow gated by `secrets.OPENAI_API_KEY` and a manual trigger or nightly cron. Cost: ~$0.15/run × N runs/day.

### 8.3 Outputs

Each run produces:

- `evals/session_recap_ingest_vertical_slice/artifacts/runs/<date>/recap_ingest--<model>--<PASS|FAIL>--<turn-count>--<utc>.md` — human-readable per-run report (mirrors npc_voice slice).
- `evals/session_recap_ingest_vertical_slice/artifacts/last_run.json` — machine-readable gate-by-gate report (one boolean per A/B/C gate, plus diagnostic strings on fails).
- `evals/session_recap_ingest_vertical_slice/artifacts/last_run.md` — symlink to the latest dated report for quick reopen.

---

## 9. Failure-mode taxonomy

When a run fails, the report localizes the regression to one of these classes. Each class maps to a small set of suspect files.

| Failure | What it likely means | Where to look |
|---------|----------------------|---------------|
| A1, A2, A5 fail | Frontmatter / title-line emission regressed. | `recap_ingest_helpers.emit_recap_frontmatter`, `strip_leading_title_line`. |
| A3, A4, A6 fail | Paragraph splitter or duplicate detector broke. | `recap_ingest_helpers.split_paragraphs_robust`, `detect_duplicate_paragraphs`. |
| A7, A8 fail without A1–A6 fail | Identity transform corrupted body (whitespace? quote normalization?). | `assemble_recap` body-stitching path. |
| B1 fail but A8 passes | Planner did not invoke the helpers correctly (wrong tool sequence). | `planner.py` dispatcher; SKILL.md protocol step 5. |
| B2 fail (Lysandra row) | `append_timeline_row` regression or model wrote wrong content. | `corpus_writer.append_timeline_row`; prompt addendum. |
| B3, B5, B6 fail (setting seeds byte-equal) | Model's seed-text generation regressed (prose drift). | Prompt addendum; consider freezing seed templates. |
| B4 fail (Marla campaign hub shape) | Dossier section structure regressed. | `_WRITE_TOOLS_ADDENDUM`; SKILL.md C.2 content rules. |
| B7 fail (unsure queue) | Model is not surfacing the queue, or surfacing wrong items, or too many items. | `_UNSURE_QUEUE_ADDENDUM` prompt; turn envelope schema. |
| B8 fail (footer pointers) | Allowlist for prep-doc footer append broken **or** model not emitting them. | `corpus_writer._PREP_FOOTER_APPEND_RE`; SKILL protocol step F. |
| B9 fail (findings missing) | Model does not surface the §G backfill or §H allowlist gaps. | Prompt addendum; SKILL protocol step 7 review-surface item types. |
| C1, C2 fail | Two-phase commit pairing broken. | `corpus_writer.write_corpus_file`; planner dispatcher. |
| C3 fail | Stale-token rejection broken. | `corpus_writer._compute_confirm_token`. Critical regression. |
| C4 fail | Allowlist deny enforcement broken. **Highest severity.** | `corpus_writer._DENY_BASENAMES`. |
| C5 fail | Allowlist rejections silently swallowed by planner. | Planner tool dispatcher; SKILL anti-pattern coverage. |
| C6 fail | Fingerprint computation drift. | `recompute_corpus_fingerprint`; investigate corpus state. |
| C7 fail | Spurious file creation outside gold-listed paths. | Tool trace; check planner did not invent paths. |

---

## 10. Out of scope (explicit; do not test in this benchmark)

These are **explicitly excluded**. If we want them tested, that is a separate benchmark spec.

- **Generalization across recaps.** Benchmark grades only Session 20 ingest. A second real recap is required to add a second scenario.
- **Recap *quality* judgment.** No "is the prose good" gates — Scope-A is identity transform on body; nothing creative is generated for the recap itself.
- **Setting-seed prose quality.** Currently graded byte-equal against the on-disk seeds. If the seed content is later revised, gold updates; the benchmark does not judge the seed's literary quality.
- **Backfill execution for Sara/Frank/Tealeaf.** §G surfaces them as findings; the benchmark does not run a backfill ingest. That is a separate, future scenario set.
- **Corpus-fingerprint downstream effects.** The benchmark verifies the fingerprint changed after writes; it does not re-run downstream Lysandra or NPC-voice slices on the new state. That is a separate cross-slice integration test.
- **Cost guardrails.** The benchmark reports cost; it does not fail on cost above a threshold. Set a budget alarm separately if needed.
- **SKILL.md correctness.** Tested implicitly (the model uses the SKILL via the prompt addendum); not graded directly.
- **Planner-cache hit/miss behavior.** Tested implicitly (run still passes); not graded directly.

---

## 11. Hand-off checklist

A single engineer can complete this in **~3 focused sessions** (~6–9 hours total). Order matters; do them top to bottom.

### Phase 1 — Scope-A and writer unit tests (no LLM; fast feedback)

- [ ] Implement `src/agent/recap_ingest_helpers.py` with the five functions in §7.1.
- [ ] Write `tests/test_recap_ingest_helpers.py` with one test per function + a Session-20 round-trip test.
- [ ] Write `tests/test_session_20_scope_a_gold.py` (one test, byte-equal assertion).
- [ ] Confirm `uv run pytest tests/test_recap_ingest_helpers.py tests/test_session_20_scope_a_gold.py` passes.

### Phase 2 — Allowlist extensions + unsure-queue schema (no LLM; small surface)

- [ ] Add five new allowlist patterns to `src/agent/corpus_writer.py` per §7.4.
- [ ] Add parametrized tests in `tests/test_corpus_writer.py` for each new pattern (allow + deny).
- [ ] Extend `src/agent/planner_turn_output_schema.py` with `unsure_queue` field.
- [ ] Add schema tests to `tests/test_planner_turn_output_schema.py`.
- [ ] Add `_UNSURE_QUEUE_ADDENDUM` to `src/prompts/corpus_session_planner.py`; bump `INSTRUCTIONS_TEMPLATE_ID`.
- [ ] Confirm `uv run pytest tests/test_corpus_writer.py tests/test_planner_turn_output_schema.py` passes.

### Phase 3 — Scope-B eval slice (live LLM; main investment)

- [ ] Create `evals/session_recap_ingest_vertical_slice/` directory.
- [ ] Write `step0_pre_state.py` + `gold/step0_pre_state_manifest.json` (§7.5).
- [ ] Write `gold/scope_b_session_20.json` translating §A–§I of the markdown gold spec to machine form (§7.3 sketch).
- [ ] Write `gold/scope_b_session_20_unsure_queue.json` (§7.3 sketch).
- [ ] Write `gold/scope_b_session_20_findings.json` (G + H substring lists).
- [ ] Write `step1_recap_ingest_run.py` modeled on `evals/lysandra_vertical_slice/step1_planner_trace.py`.
- [ ] Write `step2_grade_against_gold.py` (per-§J item grading, byte-equal vs shape).
- [ ] Write `step3_unsure_queue_grading.py` (regex on question + presence of default + alternatives count).
- [ ] Write `step4_chaos_two_phase.py` (C3 chaos: mutate content between dry-run and commit; assert rejection).
- [ ] Write `evals/session_recap_ingest_vertical_slice/README.md`.
- [ ] Add `make bench-recap-ingest` target.
- [ ] Run end-to-end; confirm all gates pass on a clean checkout.

### Phase 4 — CI wiring (optional, not blocking benchmark hand-off)

- [ ] Add Phase-1/Phase-2 tests to PR CI.
- [ ] Add Phase-3 to a manual-trigger or nightly workflow gated by `OPENAI_API_KEY`.

---

## 12. Open questions for the implementer

These are not blockers; the benchmark can be built without resolving them, but each may save rework later.

1. **`character_seed.md` byte-equal vs shape grading.** Current gold says byte-equal for the three on-disk seeds (Marla, Stacey, Stuart). The model regenerating these from prep doc + system prompt is unlikely to produce byte-equal output every time (LLM stochasticity on prose). Two options:
   - (a) Accept that B3/B5/B6 will require a fixed-temperature run (or `temperature=0`) and treat byte-equal as the gate.
   - (b) Soften to shape grading (frontmatter exact, H1 exact, presence of required prose anchors via regex).
   Recommend (b) for robustness; (a) only if we are willing to pin model + temperature very tightly. The current gold spec leaves this ambiguous; clarify before Phase 3.

2. **Marla campaign-hub dossier was never authored.** Scope-B §C.2 calls for a campaign dossier but it does not exist on disk yet. Either (a) author it manually first and freeze it as gold, or (b) write the gold as shape-only (required H1, required H2 sections, presence of "Bonogo" / "circus animal" / "bracelet" anchors) and let the model produce the prose. Recommend (b) for the same robustness reasons.

3. **Mayor / Sheriff stubs.** Same question — not on disk. The benchmark currently expects them to be created by the run if §E.2 unsure queue resolves to default. If we want Scope-B to grade their creation, we need a "default the queue" mode for the run; if we want Scope-B to grade only the *question shape* of the queue, the stubs do not get created during the bench run. **Recommend the latter**: bench-mode treats the unsure queue as terminal (model asks, run ends). Stub creation happens in a follow-up "GM answers the queue with default" scenario, not in this benchmark.

4. **Backfill backlog finding precision.** §G says "Sara, Frank, Professor Tealeaf"; the benchmark grades substring presence per name. Should it also require the run to identify the **first-appearance session number** for each? Current gold is loose on this. Recommend: tighten to "name + earliest session number mentioned" once we confirm Tealeaf's first appearance (currently noted as "earlier session — needs scan" in the gold).

5. **Recap fingerprint downstream impact.** When the bench run's tmpdir corpus changes, do we need to update `evals/lysandra_vertical_slice/gold/step0_environment.json` `expected_fingerprint`? **No** — bench runs use a tmpdir, not the live corpus, so the live fingerprint pin is unaffected. But the bench's own C6 gate needs its own pinning approach. Recommend: compute the post-state fingerprint once during gold authoring, pin it in `scope_b_session_20.json`, and update only when gold itself changes.

---

## 13. Estimated cost / effort summary

| Phase | Effort | One-time | Per-run cost |
|-------|--------|----------|--------------|
| 1 (Scope-A + helpers) | 2–3 hours | — | $0 |
| 2 (allowlist + schema + prompt) | 2 hours | — | $0 |
| 3 (Scope-B slice + gold) | 4–5 hours | gold-authoring is the bulk | ~$0.10–0.20 |
| 4 (CI) | 1 hour | — | as above × runs/day |
| **Total** | **~9–11 hours** | | |

Per-run wall time: ~2 minutes (Scope-A < 1s; Scope-B ~60–90s; chaos < 1s).

---

## 14. Why this experiment proves the design is robust

The benchmark passes iff:

- **Determinism holds** (Scope-A byte-equal across runs).
- **Writer safety holds** (C-gates: no unauthorized writes, no silent commits, no stale-token bypass).
- **Review surface is shaped correctly** (Scope-B per-§J pass).
- **The new primitive (unsure queue) is real and bounded** (≤ 4 items, exactly the right 3 questions for Session 20, each with default + alternatives).

Failure on any single gate localizes the regression to a small file/function set per the §9 taxonomy. The benchmark is single-fixture, but it covers every gate in the §J pass criteria, so it is a complete proof-of-current-state — and it becomes a *generalization* benchmark the moment a second `(raw_notes, gold_artifacts)` pair lands on disk (just add a second scenario JSON; the runner is fixture-agnostic).

This is the smallest experiment that validates *all* of the design claims made in `Docs/Plans/SCOPE-B-GOLD-Session-20-Ingest.md` and the revised `session-summary-from-notes` SKILL.
