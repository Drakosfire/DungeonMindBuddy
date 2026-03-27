# Handoff: Phase D — Synthesis Agent + CLI (`ingest`, `ask`)

## Read First

- `Docs/Design/DESIGN-layered-canon-vertical-slice.md` — canonical design, especially Component 6 (Synthesis Agent), Component 7 (CLI Loop), and Phase C checkpoint
- `src/store.py` — `FactStore` with `project()` delegation to reducer
- `src/reducer/canon_projection.py` — `project_entity_state()` returns `{ entities, conflicts, metrics }`
- `src/ingestion/chunker.py` — `chunk_document()` API
- `src/ingestion/entity_extractor.py` — `run_entity_extraction()` sync wrapper
- `src/ingestion/fact_extractor.py` — `run_fact_extraction()` sync wrapper
- `MODEL_POLICY.json` (repo root) — model roles: `retrieval_synthesis` -> `gpt-5.3-chat-latest`

## Current Baseline (Do Not Rebuild)

Phases A–C are complete and passing.

- Phase A: store + docx converter + chunker
- Phase B: Pass 1 entity extraction (strict recall `1.000`, entity density `1.603`)
- Phase C: Pass 2 fact extraction (all 5 gates pass, 519 facts from 126 evidence units)

Pipeline chain is proven:
```
docx -> chunk_document() -> run_entity_extraction() -> run_fact_extraction() -> FactStore
```

Projection reducer is proven: `FactStore.project(campaign_id)` returns valid entity-attribute-value projections with conflict detection.

**Policy decisions in effect:**
- Conflict count from automated extraction is **non-blocking** (90 world-layer conflicts are expected behavior for granular extraction)
- Model selection via `MODEL_POLICY.json` roles, not hardcoded strings

## Scope for This Handoff

Implement **Phase D only**: synthesis agent + context formatter + CLI with `ingest` and `ask` commands.

Do **not** implement `plan`, `play`, or `provenance` commands (those are Phase E).

## Objective

Wire the full `ingest` → `ask` loop:
1. `ingest` takes a document path + layer metadata, runs the full A→B→C pipeline, persists to store
2. `ask` takes a natural language question + optional campaign_id, runs the projection, formats context, calls the LLM, prints grounded prose

The gate: `ingest "The City of Mirathorn.docx"` then `ask "Catch me up on Mirathorn"` produces prose a GM would read and agree with.

## Deliverables

Create:
- `src/agent/__init__.py`
- `src/agent/context_formatter.py` — projection dict → structured text for LLM
- `src/agent/synthesis.py` — formatted context + question → LLM → prose
- `src/cli.py` — CLI REPL with `ingest` and `ask` commands
- `src/__main__.py` — `python -m dungeonbuddy` entry point
- `tests/test_context_formatter.py`
- `tests/test_synthesis.py`
- `evals/mirathorn_vertical_slice/eval_synthesis.py` — Phase D gate script

## Component 1: Context Formatter (`src/agent/context_formatter.py`)

Transforms a projection dict (from `project_entity_state`) + entity metadata into structured text the synthesis LLM consumes.

### Input

```python
def format_projection_context(
    projection: dict[str, Any],
    entities: list[dict[str, Any]],
    question: str | None = None,
) -> str:
    """Render projection as structured text for the synthesis LLM."""
```

### Output Shape

The formatter should produce text like:

```
== Entity: Mirathorn (location) ==
  history: Founded over 200 years ago by settlers fleeing the Lundayell Empire...
    [CANON, from: The City of Mirathorn / Origin and History]
  geography: Nestled at the base of Stormspire Peaks on the shores of Lake Mirathorn...
    [CANON, from: The City of Mirathorn / Geography]
  demographics: ~12,000 permanent residents...
    [CANON, from: The City of Mirathorn / Demographics]
  economy: Tourism-driven economy centered on Festival of Expansion...
    [CANON, from: The City of Mirathorn / Economy]
  defenses: City walls with guarded gates, Captain Lysandra Ironveil commanding...
    [CANON, from: The City of Mirathorn / Defenses]
  CONFLICTS:
    operational_status: 3 competing facts (auto_conflict_001)

== Entity: Shepherd's Flock (faction) ==
  operational_status: Active protest movement at city gates...
    [CANON, from: The City of Mirathorn / Factions]
  goals: Abolition of entry toll...
    [CANON, from: The City of Mirathorn / Factions]
```

### Design Rules

1. **Include entity type** from entity metadata (resolve `entity_id` → `entity_type` + `display_name`).
2. **Include source provenance** for each attribute — `truth_state` and at minimum the `source_layer`. Evidence unit text is available for deeper provenance but the formatter should keep context concise.
3. **Surface conflicts explicitly** — for each entity, if any attributes have `conflict_ids`, note them. The LLM should know when facts disagree.
4. **Order entities by fact count** (descending) — entities with more facts are more likely to be relevant.
5. **Cap total context length** — if projection has 200+ entities, the formatter should either:
   - Filter to entities relevant to the question (if question is provided), or
   - Truncate to top N entities by fact count with a note that more exist.
   - For Phase D, a simple top-50 cap is fine. Relevance filtering is a Phase E+ concern.

### What Not To Do

- Do not call the LLM from the formatter. It is pure string formatting.
- Do not attempt semantic relevance filtering yet. That's future work.
- Do not render the full evidence unit text inline. Keep it to the fact `value.label` + provenance summary.

## Component 2: Synthesis Agent (`src/agent/synthesis.py`)

Takes formatted context + a user question, calls the LLM, returns grounded prose.

### API

```python
def synthesize_answer(
    formatted_context: str,
    question: str,
    *,
    model: str | None = None,
    openai_client: Any | None = None,
) -> str:
    """Send projection context + question to LLM, return grounded prose."""
```

### System Prompt

```
You are a Game Master's assistant for a tabletop RPG campaign.

Answer the GM's question using ONLY the facts provided in the projection context below.
When facts come from different truth states, distinguish them:
- CANON: established world truth
- PREP: GM planning notes (may not have happened yet)
- OBSERVED: what actually happened in play

If facts conflict on the same attribute, explain which version is current and why.
Do not invent information beyond what is stated in the projection.
If the projection doesn't contain enough to answer, say so explicitly.

Cite entity names when referencing facts. Keep the tone helpful and concise —
this is a GM's quick reference, not a novel.
```

### Model

Use `retrieval_synthesis` role from `MODEL_POLICY.json` (`gpt-5.3-chat-latest`). This is the grounded response synthesis model.

Resolve via:
```python
import json
from pathlib import Path

def _resolve_model(model: str | None) -> str:
    if model:
        return model
    policy_path = Path(__file__).resolve().parents[2] / "MODEL_POLICY.json"
    if policy_path.exists():
        policy = json.loads(policy_path.read_text())
        role = policy.get("actions", {}).get("retrieval_synthesis", "retrieval_synthesis")
        return policy.get("models", {}).get(role, "gpt-5.3-chat-latest")
    return "gpt-5.3-chat-latest"
```

Or adapt the same resolution pattern used in entity/fact extractors.

### Runtime

- Load `.env.development` for `OPENAI_API_KEY` (same pattern as extractors)
- Standard `openai.OpenAI()` chat completion (not structured output — we want free prose)
- No caching needed for synthesis (questions vary, answers should be fresh from current projection)

## Component 3: CLI (`src/cli.py` + `src/__main__.py`)

### Entry Point

`src/__main__.py`:
```python
from src.cli import main
main()
```

Invoked as: `uv run python -m src --store ./my_campaign`

### CLI Shape

```
$ uv run python -m src --store ./my_campaign

dungeonbuddy> ingest "path/to/doc.docx" --layer world --source-class seed_reference
  Chunking... 126 evidence units
  Pass 1 entity extraction... 209 entities
  Pass 2 fact extraction... 519 facts
  Stored. Total: 126 evidence units, 209 entities, 519 facts.

dungeonbuddy> ask "Catch me up on Mirathorn" --campaign longmont_01
  [prose output from synthesis agent]

dungeonbuddy> entities
  [list of entity display_name + type + fact count]

dungeonbuddy> projection --campaign longmont_01
  [raw formatted projection context, same as what the LLM sees]

dungeonbuddy> quit
```

### Commands for Phase D

| Command | What It Does |
|---------|--------------|
| `ingest <path> --layer <world\|campaign> [--campaign <id>] [--source-class <class>] [--title <title>]` | Full pipeline: chunk → Pass 1 → Pass 2 → store.save() |
| `ask <question> [--campaign <id>]` | Project → format → LLM synthesis → print |
| `entities` | List all entities with fact counts |
| `projection [--campaign <id>]` | Print raw formatted projection (debug/inspect tool) |
| `quit` / `exit` | Exit REPL |

### `ingest` Implementation

1. Parse arguments: `path`, `--layer` (required: `world` or `campaign`), `--campaign` (required if layer=campaign), `--source-class` (default: `seed_reference` for world, `planning_document` for campaign), `--title` (default: filename stem)
2. Generate `document_id` from filename: `doc_<snake_case_stem>`
3. Call `chunk_document(path, document_id, title, canon_layer, campaign_id, source_class)`
4. Call `run_entity_extraction(evidence_units, known_entities=store.list_entities(), cache_dir=store_dir / ".cache")`
5. Call `run_fact_extraction(evidence_units, entities=entities, canon_layer=layer, campaign_id=campaign_id, source_class=source_class, cache_dir=store_dir / ".cache")`
6. `store.add_evidence_units(units)` → `store.add_entities(entities)` → `store.add_facts(facts)` → `store.save()`
7. Print summary counts

### `ask` Implementation

1. `projection = store.project(campaign_id)`
2. `context = format_projection_context(projection, store.list_entities(), question)`
3. `answer = synthesize_answer(context, question)`
4. Print answer

### Argument Parsing

Use Python's built-in `shlex.split()` for REPL line parsing and `argparse` for per-command argument handling. Keep it simple — this is a vertical slice CLI, not a production tool.

### Error Handling

- If `OPENAI_API_KEY` is not set, print a clear error on `ingest` or `ask` and continue the REPL (don't crash)
- If a file doesn't exist, print error and continue
- If store directory doesn't exist, create it on first `ingest`

## Explicit Gates (Phase D Acceptance)

All gates apply to Mirathorn Set A.

### Gate D1 — Ingest Pipeline Round-Trip

`ingest "The City of Mirathorn.docx" --layer world` succeeds:
- Evidence units, entities, and facts persist to store directory
- `store.load()` round-trips cleanly
- Counts are reasonable (>100 evidence units, >100 entities, >400 facts)

Pass condition: hard pass/fail.

### Gate D2 — Synthesis Produces Grounded Prose

`ask "Catch me up on Mirathorn"` produces output that:
- Mentions Mirathorn by name
- References at least 3 distinct attributes (geography, history, demographics, economy, defenses, etc.)
- Does not contain obvious hallucinations beyond projection content
- Is >200 characters (not a stub/error)

Pass condition: checked by eval script with string/keyword assertions, not LLM-as-judge.

### Gate D3 — Provenance In Context

The formatted context (visible via `projection` command) includes:
- Entity display names with types
- Attribute values with truth_state labels
- Conflict annotations where they exist

Pass condition: structural check on `format_projection_context()` output.

### Gate D4 — CLI Stability

The CLI REPL:
- Handles `ingest` → `ask` → `entities` → `projection` → `quit` sequence without crash
- Handles missing file gracefully (error message, continues)
- Handles missing API key gracefully (error message, continues)

Pass condition: eval script runs the sequence programmatically.

## Test Requirements

### `tests/test_context_formatter.py`

1. Formats a minimal projection (1 entity, 2 attributes) into expected text shape
2. Includes entity type from entity metadata
3. Surfaces conflicts in output
4. Handles empty projection gracefully
5. Respects entity cap (if >50 entities, output is truncated)

### `tests/test_synthesis.py`

1. Calls synthesize_answer with a mock OpenAI client
2. System prompt contains required grounding instructions
3. Formatted context appears in the messages sent to the LLM
4. Returns the LLM's response content

All tests must run without live API calls via stubs/mocks.

## Integration: What Already Exists

The following are **frozen and working** — do not modify them:

| File | Status |
|------|--------|
| `src/store.py` | Frozen (Phase A) |
| `src/reducer/canon_projection.py` | Frozen (pre-Phase A) |
| `src/ingestion/chunker.py` | Frozen (Phase A) |
| `src/ingestion/entity_extractor.py` | Frozen (Phase B) |
| `src/ingestion/fact_extractor.py` | Frozen (Phase C) |
| `src/contracts/schema_validation.py` | Frozen |
| `schemas/v0.1/*` | Frozen |

## Verification Commands

```bash
uv run ruff check src/agent/ src/cli.py src/__main__.py tests/test_context_formatter.py tests/test_synthesis.py evals/mirathorn_vertical_slice/eval_synthesis.py
uv run pytest tests/test_context_formatter.py tests/test_synthesis.py
uv run pytest
uv run python evals/mirathorn_vertical_slice/eval_synthesis.py
```

The eval script (`eval_synthesis.py`) should:
- Load `.env.development`
- Require `OPENAI_API_KEY`
- Run ingest on `The City of Mirathorn.docx` (or load from existing store if cache exists)
- Run `ask "Catch me up on Mirathorn"`
- Validate Gates D1–D3
- Print metrics and single PASS/FAIL

## Done Criteria

- Context formatter implemented and tested (no LLM dependency)
- Synthesis agent implemented and tested (mock LLM in unit tests, real LLM in eval)
- CLI REPL runs `ingest` → `ask` → `entities` → `projection` → `quit`
- All D gates pass on Mirathorn Set A
- No regressions in full test suite
- Output is ready for Phase E (`plan`, `play`, `provenance` commands)
