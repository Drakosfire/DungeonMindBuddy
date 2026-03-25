# DungeonMindBuddy — Project Context

## Project Identity

DungeonMindBuddy is a **narrative knowledge graph extraction and canon reduction pipeline** for TTRPG campaigns. It ingests GM-authored documents (session recaps, NPC dossiers, planning notes, world-building) and builds a structured knowledge graph of entities, facts, events, conflicts, and canon decisions — with full provenance back to source text.

This is a **pipeline/library project**, not a web application. There is no frontend, no API layer, and no database in v0.1. The "user" is a GM who feeds documents in and queries entity state out. A serving layer may come later but is explicitly out of scope for the initial vertical slice.

---

## Technology Stack & Versions

- **Python:** >=3.13 (match RulesIngestion sibling repo)
- **Package manager:** `uv` (NEVER use `python` or `pip` directly — always `uv run python`, `uv run pytest`, `uv add`)
- **Pydantic:** >=2.0.0 (all data models, validation, serialization)
- **blake3:** >=0.3.3 (content fingerprinting for determinism)
- **pytest:** >=9.0.2 (testing)
- **python-docx:** (document extraction — add when needed)

### Not in scope for v0.1
- No web framework (no FastAPI, Flask)
- No database (no MongoDB, Firestore, SQLite)
- No vector embeddings or retrieval
- No LLM/OpenAI integration for extraction (deterministic first, AI-assisted later)

---

## Critical Implementation Rules

### Python-Specific Rules

- ALL execution via `uv run`: `uv run python script.py`, `uv run pytest tests/`
- Type hints required on all function signatures
- Pydantic v2 models for all data contracts — `model_validate()`, `model_dump()`, not legacy v1 methods
- Use `from __future__ import annotations` for forward references
- f-strings for formatting, no `.format()` or `%` interpolation
- Use `pathlib.Path` for all filesystem operations, never raw string paths

### Schema / Contract Rules

- **JSON schemas in `schemas/v0.1/` are the normative contracts.** Pydantic models MUST conform to these schemas exactly.
- All record types inherit `baseRecord` fields: `schema_version`, `created_at`, `updated_at`, `record_status`, `extraction_pass_id`
- IDs are opaque strings matching pattern `^[A-Za-z0-9_.:-]+$` — stable references, not semantic keys
- `unevaluatedProperties: false` in schemas means Pydantic models must NOT add fields not in the schema
- Enums in schemas are controlled vocabularies — do not extend without schema version bump
- The `factValue` type is polymorphic on `kind` field (scalar/state/entity_ref/set/interpretive) — model accordingly

### Domain Rules (Non-Negotiable)

- **Identity is separated from state.** Entity holds identity and merge status. Fact holds attribute claims. Never put typed character state on Entity.
- **Contradictions are preserved, not flattened.** The Conflict schema exists to hold unresolved disagreements. Never silently overwrite a fact with a newer one.
- **Truth is derived, not stored.** Canon state is computed by the reducer from Facts + CanonDecisions. `CANON` as a stored truth_state is allowed but the safer default is derivation.
- **Every claim traces to evidence.** Facts require `evidence_ids` (minItems: 1). Events require `source_evidence_ids` (minItems: 1). No orphan assertions.
- **EvidenceUnits are the only admissible evidence layer.** All downstream objects (Mentions, Facts, Events) must reference EvidenceUnit IDs, not raw document text.

---

## Architecture Constraints

### Pipeline, Not Service

The system is a **staged extraction pipeline** modeled after the RulesIngestion sibling project:

```
Source Document → EvidenceUnits → Mentions → Entities → Facts/Events → Conflicts → Canon Reducer → Entity State Projection
```

Each stage:
- Takes well-defined input (previous stage output or source document)
- Produces well-defined output (JSON conforming to schema)
- Is independently testable with fixture data
- Is deterministic given the same input (no randomness, no LLM in core path for v0.1)

### Filesystem-First Persistence

- Pipeline outputs are JSON files written to `out/` directories
- No database in v0.1 — files are the persistence layer
- Each extraction run produces a directory of artifacts (like RulesIngestion's `out/<book>/<doc_id>/` pattern)

### Source Document Types

The real corpus contains these document types that map to `source_class`:

| Document format | Schema `source_class` | Examples |
|---|---|---|
| Session recaps (.docx) | `observed_session_recap` | Session summaries, play-by-play accounts |
| NPC dossiers (.md, .docx) | `ledger_or_dossier` | Character profiles, narrative ledgers |
| Session prep (.md, .docx) | `planning_document` | Pre-session reference packets |
| World/location docs (.docx) | `seed_reference` | City descriptions, location dossiers |
| Scene scripts (.docx) | `planning_document` | Scripted encounters, scene blueprints |

The corpus is **106 .docx files**, **4 .md files**, plus images/PDFs/3D models (non-text, ignored for extraction). A `.docx → text` stage is needed before evidence extraction.

---

## Testing Rules

- **Test structure:** `tests/` mirrors `src/` layout (e.g., `tests/models/`, `tests/extraction/`, `tests/reducer/`)
- **Fixtures over mocks:** Use JSON fixture files from `schemas/v0.1/examples/` and hand-crafted test data
- **Schema conformance tests required:** Every Pydantic model must have a test that validates against its JSON schema
- **Round-trip tests required:** `model → JSON → model` must be lossless for all record types
- **Reducer tests require known inputs/outputs:** Deterministic input → expected projection, not "it didn't crash"
- **Run with:** `uv run pytest tests/` — never bare `pytest`
- **Coverage target:** >80% for core models and reducer logic

---

## Code Quality & Style Rules

- **File size:** <300 lines preferred, >500 signals extraction needed
- **Function size:** <50 lines preferred, >100 requires decomposition
- **Naming:** snake_case for functions/variables, PascalCase for classes, UPPER_SNAKE for constants
- **Comments:** Explain WHY, not WHAT. No narrating code.
- **No unsolicited documentation files.** Never create READMEs, summaries, or completion reports unless explicitly requested.
- **Imports:** Group as stdlib → third-party → local, separated by blank lines

### Project Layout

```
DungeonMindBuddy/
├── schemas/v0.1/          # Normative JSON schemas (committed, versioned)
│   └── examples/          # Example instances for each schema
├── src/
│   ├── models/            # Pydantic models conforming to schemas
│   ├── extraction/        # EvidenceUnit extraction from source docs
│   ├── resolution/        # Mention extraction, entity resolution
│   ├── reducer/           # Canon reducer, conflict detection
│   └── query/             # Entity state projection queries
├── tests/                 # Mirrors src/ layout
├── out/                   # Pipeline output artifacts (gitignored)
├── specs/                 # Feature specs and handoffs
├── Docs/
│   ├── Design/            # Architecture docs
│   └── Eldyrwild and Campaign Context/  # Real test corpus (gitignored for size)
├── _bmad/                 # BMAD framework (committed)
├── _bmad-output/          # BMAD planning artifacts
├── pyproject.toml
└── .gitignore
```

---

## Development Workflow Rules

- **Always `uv run`** — never bare `python`, `pip`, or `pytest`
- **Empirical verification required** — run it and show evidence, no "should work" claims
- **Contract-first development** — JSON schema → Pydantic model → tests → pipeline stage
- **Consumer before producer** — build the reducer/query layer with fixture data before building extraction
- **Commit message format:** `type(scope): summary` — e.g., `feat(models): add Pydantic models for v0.1 schemas`
- **Branch naming:** `feature/description`, `fix/description`
- **Linter check after every edit** — run `uv run ruff check .` and fix issues

---

## Critical Don't-Miss Rules

### Anti-Patterns

- **NEVER run Python without `uv run`** — system Python lacks project dependencies
- **NEVER extend schema enums without bumping schema version** — downstream consumers depend on controlled vocabularies
- **NEVER silently overwrite facts** — always create a new Fact record and let the reducer resolve conflicts
- **NEVER put character state on Entity** — Entity is identity only; state belongs in Fact records
- **NEVER create orphan assertions** — every Fact/Event must trace to EvidenceUnit IDs
- **NEVER import from sibling repos** (RulesIngestion, DungeonMindServer) — this is an independent project
- **NEVER add LLM dependencies for v0.1** — the core pipeline must be deterministic and testable without API keys

### Edge Cases

- **Temporal validity:** Facts have `valid_from_session`/`valid_to_session` windows. A fact about "Lysandra is a Sergeant" may be valid sessions 1-14, while "Lysandra is a Lieutenant" is valid from session 15+. Both are true; neither overwrites the other.
- **Entity merging:** Two mentions may initially create two entities that are later discovered to be the same person. The `merged_into_other` entity status and `merged_into_entity_id` field handle this. Original entity and all its linked facts/mentions must be preserved.
- **Conflict types matter:** `hard_conflict` (mutually exclusive values), `temporal_conflict` (same attribute changed over time), `identity_conflict` (are these the same entity?), `soft_conflict` (interpretive disagreement), `source_conflict` (different documents disagree). Each has different resolution semantics.
- **CanonDecision audit trail:** Every manual override must be recorded as a CanonDecision with rationale, decided_by, and effect. Canon must be rebuildable by replaying decisions.

### Vertical Slice Definition

For this project, a "vertical slice" means:

**Input:** One session recap document (markdown or .docx)
**Output:** Queryable entity state — "show me everything known about entity X with provenance"

Pipeline stages exercised:
1. Source document → EvidenceUnits
2. EvidenceUnits → Mentions
3. Mentions → Entities
4. Evidence + Mentions → Facts
5. Facts → Canon Reducer → Entity State Projection
6. Query: "What is entity X's current state?" → projection with provenance chain

This exercises all 7 schema types and the core invariant (truth derived via reducer).

---

## Relationship to Sibling Projects

### RulesIngestion (patterns to reuse, not code to import)
- Contract-first schema design (JSON schema → Pydantic models)
- Staged pipeline with quality gates
- Filesystem-first artifact persistence
- Evaluation harness with benchmark contracts
- blake3 fingerprinting for determinism

### RulesLawyer (future integration point, not v0.1 scope)
- Eventually DungeonMindBuddy's entity state could be served via a similar RAG or query API
- That integration is post-v0.1 and would follow DungeonOverMind service boundary rules (REST API, not code import)

---

*Document status: Active. Mandatory guidance for all BMAD workflows (create-story, dev-story, code-review).*
