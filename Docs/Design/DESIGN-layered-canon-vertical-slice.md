# Layered Canon Vertical Slice — Design

**Date:** 2026-03-26
**Status:** Active
**Supersedes:** `Docs/Plans/mirathorn_event-sourced_slice_8eab1beb.plan.md` (scope narrowed, sequence changed)

## Goal

Prove that the three-layer model (Canon → Planning → Play) produces output a GM would actually use at the table, before investing in ingestion automation or event-sourcing infrastructure.

## The Three Layers

```
┌─────────────────────────────────────────────┐
│  Layer 3: Play                              │
│  Live session events that update state.     │
│  "What happened when the players showed up" │
├─────────────────────────────────────────────┤
│  Layer 2: Planning                          │
│  GM prep overlaid on canon.                 │
│  "What am I setting up for next session"    │
├─────────────────────────────────────────────┤
│  Layer 1: Canon                             │
│  World + campaign facts as truth.           │
│  "What is true about this place"            │
└─────────────────────────────────────────────┘
```

**Core invariant:** Lower layers are never mutated by higher layers. Campaign canon doesn't rewrite world canon. Planning doesn't rewrite canon. Play doesn't rewrite planning or canon. Each layer's projection is additive/overlay only.

## What Already Works

- v0.1 JSON schemas for evidence_unit, event, fact, conflict, canon_decision, entity, mention
- Deterministic canon projection reducer (`src/reducer/canon_projection.py`)
- 6 golden scenarios with benchmark runner testing layer isolation, conflict detection, determinism
- Schema validation pipeline with `$ref` registry
- The layer isolation invariant (campaign facts can't mutate world canon) is tested and passing

## The Projection Is Agent Context, Not GM Output

The projection is not the end-user artifact. It is structured context that an LLM agent consumes to produce prose for the GM. The LLM is the rendering layer — it takes the entity-attribute-value projection and synthesizes grounded, citable narrative from it.

This means the analytical format (entity → attribute → value + provenance) is a feature: it gives the agent unambiguous facts to work from rather than pre-baked prose to parrot. The GM never reads the projection directly; they read what the agent writes from it.

## What the Vertical Slice Must Answer

> **Does the projection give an agent everything it needs to write accurate, grounded prose about Mirathorn?**

This is the gate. If an agent fed the projection can produce a description the GM would read and agree with — citing the right sources, respecting layer boundaries, not hallucinating beyond what's in the facts — the model works.

## Sequence

### Step 1: Prove Canon Reads Right

**Input:** 5–10 hand-authored facts and evidence units extracted from the Mirathorn doc.
**Process:** Feed through existing reducer with `canon_layer=world`, `campaign_id=null`.
**Output:** A projection of Mirathorn.
**Gate:** Does the projection contain everything an agent would need to write accurate, grounded prose about Mirathorn? PASSED — Step 1 complete.

**Finding:** Initial hand-authoring only extracted entities that were *subjects* of multiple facts (Mirathorn, Shepherd's Flock) and skipped entities that were merely *mentioned* (Lake Mirathorn, Stormspire Peaks, Lundayell Empire, Festival of Expansion). This was wrong — mentioned entities are graph nodes that other documents connect to later. The ingestion pipeline must cast a wide net on entity extraction. This informed the two-pass extraction architecture in Step 4.

Scope: ~1–2 hours. No LLM. No new code. Just JSON fixtures through existing infrastructure.

### Step 2: Prove the Planning Layer Boundary

**Input:** The canon projection from Step 1, plus 2–3 hand-authored "planning" facts (e.g., "the protest at the gates will escalate," "the merchant guild has planted a spy in the guard").
**Process:** Feed through reducer as `canon_layer=campaign` with a campaign id.
**Output:** A combined projection showing world canon + planning overlay.
**Gate:** World canon unchanged? Does the combined projection give an agent enough to distinguish world truth from GM plans?

Scope: ~1–2 hours. Same infrastructure, new fixtures.

### Step 3: Prove Play Updates Don't Corrupt Lower Layers

**Input:** The combined projection from Step 2, plus 1–2 live events (e.g., "the party sided with the protesters," "the guard captain was killed").
**Process:** Apply as events, project again.
**Output:** Three-layer projection with visible audit trail.
**Gate:** Can you see all three layers clearly? Does the provenance chain make sense? Does canon remain intact?

Scope: ~1–2 hours. May need minor reducer extension for event application.

### Step 4: Ingestion Automation

**Only after Steps 1–3 pass.** At this point you know:
- The projection shape gives an agent sufficient grounded context
- The layer boundaries hold with real content
- What the LLM extraction pipeline needs to produce

#### GM Input Convention

GMs provide markdown documents with frontmatter declaring the layer:

```markdown
---
canon_layer: world              # world | campaign
campaign_id: null               # null for world, required for campaign
source_class: seed_reference    # seed_reference | planning_document | observed_session_recap | ledger_or_dossier
document_title: "The City of Mirathorn"
---

## Mirathorn Overview
### Origin and History
Founded over 200 years ago by settlers fleeing...
```

The GM declares the layer. The system never guesses it. `truth_state` is derived from layer + source_class (`world` + `seed_reference` → `CANON`; `campaign` + `planning_document` → `PREP`).

#### Two-Pass Extraction Architecture

Ingestion splits into two agent passes over each section-level chunk:

**Pass 1 — Entity Extraction (wide net, high gate):**
- Identify every named entity in the text: people, places, factions, items, events
- Cast wide — every proper noun, every named thing. Entities that are merely *mentioned* still get created as provisional nodes
- Output: entity records with display_name, entity_type, aliases
- A mention of "Stormspire Peaks" in a geography fact about Mirathorn creates `ent_stormspire_peaks` even if this document says nothing else about it. Other documents fill in facts later.

**Pass 1 quality gate:** Comprehensiveness is the priority. A missed entity is a missing node in the graph — facts from other documents have nothing to attach to. Validate against gold-authored entity lists for the Mirathorn slice. The gate is recall-oriented: every named thing in the source text must appear in the entity output. False positives (extracting "the gates" as an entity) are cheaper to prune than false negatives are to recover.

**Pass 2 — Fact Extraction (per entity):**
- For each entity identified, extract what this text asserts about it
- Classify into attribute enum (geography, history, demographics, defenses, economy, goals, etc.)
- Assign value shape: scalar, state, set, or interpretive
- Link facts to evidence units (the source chunk)
- Use `entity_ref` value kind to create cross-references between entities (Mirathorn's geography references Stormspire Peaks and Lake Mirathorn as entity_refs, not just text)

**Why two passes:**
- Pass 1 is cheaper (NER + classification), can use a smaller/faster model
- Pass 2 is interpretive, benefits from a more capable model
- Entity list from Pass 1 primes Pass 2 with known subjects to extract facts about
- Keeps entity coverage high even when a document only mentions something in passing

#### Two Granularities: Ingestion vs. Retrieval

Evidence units and facts serve different roles and have different size pressures.

**Ingestion chunks (evidence units)** are the input to the extraction LLM. They are light provenance records — a receipt of what was said where. Heading-bounded sections from the GM's markdown, preserving section_path for traceability. Larger is better here: the LLM extracting facts benefits from seeing a full section with its heading context for entity identification and attribute classification.

**Retrieval chunks (projected facts)** are what the agent queries over at runtime. Each fact is a self-contained, attributed assertion with provenance links back to evidence. Facts are denser and more semantically precise than raw text chunks — closer to the "clause family" projection that RulesIngestion research identified as the next retrieval quality frontier.

```
GM markdown  ──►  evidence units (light records, provenance)
                       │
                  extraction LLM
                       │
                       ▼
                  facts (structured assertions)  ──►  agent queries here
                       │
                  linked by evidence_ids
                       │
                       ▼
                  evidence units  ──►  provenance trail on demand
```

The evidence unit exists so you can trace *why* a fact exists. The fact exists so the agent can find and use it. Two different jobs, two different granularities, linked by `evidence_ids`.

**Informed by RulesIngestion findings:** Raw atomic evidence units are too fine for retrieval (micro-chunk pollution, duplicate collisions in top-K results). The canonical fix there was fold + merge to ~2000 char units. Here, the projected facts are a natural retrieval unit that sidesteps the problem entirely — each fact is already semantically self-contained with its label and attribute classification.

#### Chunking Strategy (Ingestion)

Section-level chunking via `docx_to_markdown()` → AST parser → evidence unit builder (adapts RulesIngestion's `ast_parser.py` → `stage_b.py` chain). One heading section → one evidence unit → typically 1–3 facts per entity mentioned. The heading hierarchy provides `section_path` for provenance.

**Two-tier heading detection** (corpus has inconsistent heading styles):
1. **Docx paragraph styles first.** If a paragraph has style `Heading 1`–`Heading 4`, map to markdown `#`–`####`. Build `section_path` from the heading hierarchy.
2. **Fallback: detect section patterns in text.** For docs like the Mossford gazetteer where everything is `Normal` style, detect numbered sections (`1. Watch Tower`, `2. Temple of the Nameless Stone`) or bold-text section headers. These become section boundaries.

**Minimum chunk:** If a heading section is under 50 characters, merge with the next section (avoid micro-chunks).

**Maximum chunk:** If a section exceeds ~3000 characters, keep it as-is — bigger is better for extraction context. Do not split large sections.

**Enrichment pipeline reuse:** Entity and fact extraction use the `enrich_units_batch` async semaphore pattern from `stage_a_prime.py` — swap prompts and Pydantic output schemas, same concurrency/caching/gate infrastructure. See Step 4 experiment design below.

#### Phase A Decisions (Implemented)

The initial deterministic implementation of Phase A introduced a few concrete decisions that now become part of the contract:

1. **Heading-only sections emit fallback evidence units.**  
   If a heading has no child paragraph content, emit an evidence unit for that heading so it still appears in provenance and `section_path` coverage checks.

2. **Heading absorption separator is ` -- `.**  
   During AST walk, heading text is prefixed into the first child paragraph using `heading -- child_text` to preserve context even when downstream systems only read `text`.

3. **Minimum-size merge preserves the earlier section path.**  
   When a section under 50 chars merges into the next chunk, the merged chunk keeps the original (small section's) `section_path` and earliest paragraph index.

4. **Gate comparison is structural/comparability, not strict path equality.**  
   Hand-authored Step 1 evidence uses some semantic labels not present as literal headings in source docs. The evaluation gate therefore checks:
   - automated output count exceeds hand-authored count,
   - hand section *leaf* coverage against automated path components is acceptable,
   - no weak text-overlap gaps against hand-authored evidence,
   - first and last non-empty markdown lines are covered.

This keeps the gate faithful to the intent ("structurally comparable and complete coverage") while avoiding false failures from naming abstraction differences.

### Step 5: Event Sourcing and Infrastructure

**Only after Step 4 works.** Event sourcing, hard gates, determinism replay, gold artifact packs — all the infrastructure from the original plan — gets built once the core model is validated and the ingestion pipeline produces usable output.

---

## Step 4 Experiment Design: Ingestion Automation + CLI Chat Loop

### What Exists (Reuse from RulesIngestion)

The RulesIngestion Mark III pipeline has proven infrastructure for exactly the pattern we need. The following are directly transferable:

| RI Component | File | What It Does | DungeonMindBuddy Use |
|---|---|---|---|
| `enrich_units_batch` | `extraction/stage_a_prime.py` | Async semaphore-limited LLM calls over evidence units with structured Pydantic output, input fingerprinting, cache-on-disk | Entity extraction (Pass 1) and fact extraction (Pass 2) — swap prompts and output schemas |
| `_responses_parse_sync` | `extraction/stage_a_prime.py` | OpenAI Responses API with `text_format=PydanticModel` for structured outputs, refusal detection | All LLM calls use this pattern |
| `ast_parser.py` | `extraction/ast_parser.py` | Markdown → heading tree (SurfaceAST) via `^#{1,6}\s+` regex, line classification, tree building | Chunking: docx → markdown → AST → evidence units |
| `stage_b.py` | `extraction/stage_b.py` | SurfaceAST → flat EvidenceUnits with `structural_path` provenance. Headings absorbed into first child, tables never split, monotonic ordering | Evidence unit production from heading tree |
| Pipeline orchestration | `extraction/pipeline.py` | Stage A → B → A′ chaining with gates at each stage, artifact writing | Pipeline shape: chunk → extract entities → extract facts → store |
| Gate diagnostics | `extraction/schemas.py` | `GateDiagnostic(name, passed, detail)` pattern for pass/fail checks | Entity recall gates, fact quality gates |

**Key difference:** RI ingests PDFs via OCR → markdown. DungeonMindBuddy ingests `.docx` files. We need one new function — `docx_to_markdown()` — and then the existing AST parser handles the rest.

### What Needs To Be Built

#### Component 1: `docx_to_markdown()` (`src/ingestion/docx_converter.py`)

Converts a `.docx` file to markdown with proper heading markers.

```python
def docx_to_markdown(docx_path: Path) -> str:
    """Convert docx to markdown, mapping paragraph styles to # headings.
    
    Fallback: detect numbered sections (e.g. '1. Watch Tower') in Normal-style
    paragraphs for documents without proper heading styles.
    """
```

- Maps `Heading 1` → `#`, `Heading 2` → `##`, etc.
- Detects numbered section patterns (`^\d+\.\s+\w`) in `Normal` paragraphs as heading fallback
- Preserves bold text as `**bold**` (may help section detection)
- Output: markdown string ready for `parse_markdown_to_ast()`

#### Component 2: Chunking Pipeline (`src/ingestion/chunker.py`)

Adapts RI's `ast_parser.py` → `stage_b.py` chain for DungeonMindBuddy evidence units.

```python
def chunk_document(
    docx_path: Path,
    document_id: str,
    document_title: str,
    canon_layer: str,
    campaign_id: str | None,
    source_class: str,
) -> list[dict]:
    """docx → markdown → AST → evidence units (v0.1 schema)."""
```

- Calls `docx_to_markdown()` → simplified AST parser → evidence unit builder
- Each chunk gets: `evidence_id`, `document_id`, `section_path`, `text`, `canon_layer`, etc.
- Minimum chunk: 50 chars (merge with next). Maximum: no split (bigger is better for extraction).
- Validates output against `evidence_unit.schema.json`

#### Component 3: Entity Extraction — Pass 1 (`src/ingestion/entity_extractor.py`)

Adapts `enrich_units_batch` pattern. Swap prompt and output schema.

**LLM prompt shape:**
```
System: You are an entity extraction agent for a TTRPG worldbuilding system.
Extract every named entity from the text. Include people, places, factions,
items, events. Cast a WIDE net — mentions count.

Known entities (reuse IDs if recognized):
{existing_entities_json}

For new entities: entity_id = "ent_" + snake_case(display_name)
```

**Pydantic output schema:**
```python
class ExtractedEntity(BaseModel):
    entity_id: str
    entity_type: Literal["npc", "location", "faction", "item", "other"]
    display_name: str
    aliases: list[str]
    is_new: bool  # false if reusing existing entity_id
```

**Model:** `fast_smart_mini` (gpt-5.4-mini) — NER + classification, fast and cheap.

**Infrastructure:** `enrich_units_batch` with `ExtractedEntity` output schema instead of `APrimeEnrichment`. Same async semaphore, same caching, same fingerprinting.

**Per chunk:** One LLM call. All chunks parallelized.

**Gate:** Entity recall ≥90% against gold entity list (for Set A docs).

#### Component 4: Fact Extraction — Pass 2 (`src/ingestion/fact_extractor.py`)

Same `enrich_units_batch` pattern, different prompt and schema. Depends on Pass 1 output.

**LLM prompt shape:**
```
System: You are a fact extraction agent for a TTRPG worldbuilding system.
For each entity mentioned in this text, extract what this text ASSERTS about it.

Entities found in this text: {entities_json}

Attribute enum: [species, role, rank_or_title, faction, current_location,
  physical_condition, mental_state, loyalty_or_alignment_context,
  relationship_tags, operational_status, portrayal_notes, unresolved_questions,
  source_comments, history, geography, demographics, defenses, economy,
  governance, atmosphere, goals]

Value kinds: scalar | state | set | interpretive
  interpretive requires: interpretation_level + strength

Evidence unit ID: {evidence_id}
```

**Pydantic output schema:**
```python
class ExtractedFact(BaseModel):
    fact_id: str
    subject_entity_id: str
    attribute: str  # from enum
    value: FactValue  # kind + label + normalized + optional entity_refs
```

**Model:** `fast_smart` (gpt-5.3-codex) — interpretive, needs to classify attributes correctly.

**Per chunk:** One LLM call. All chunks parallelized (they share the entity list from Pass 1).

**Post-extraction:** Assign `truth_state` and `source_authority` from document metadata:
- `world` + `seed_reference` → `CANON` / `seed_prep`
- `campaign` + `planning_document` → `PREP` / `planning_prep`
- `campaign` + `observed_session_recap` → `OBSERVED` / `observed_recap`

Validate all outputs against `fact.schema.json`.

#### Component 5: Fact Store (`src/store.py`)

JSON files on disk. No database needed for the vertical slice.

```python
class FactStore:
    def __init__(self, store_dir: Path)
    
    def load(self) -> None
    def save(self) -> None
    def add_evidence_units(self, units: list[dict]) -> None
    def add_entities(self, entities: list[dict]) -> None
    def add_facts(self, facts: list[dict]) -> None
    def get_entity_by_name(self, name: str) -> dict | None
    def list_entities(self) -> list[dict]
    def project(self, campaign_id: str | None) -> dict
        # Delegates to project_entity_state()
```

Entity deduplication on `add_entities`: case-insensitive match on `display_name` or any alias. Merge aliases, return existing `entity_id`.

#### Component 6: Synthesis Agent (`src/agent/synthesis.py`)

The `ask` command. Projection → formatted context → LLM → grounded prose.

**Context formatting:** Render projection as structured text:
```
Entity: Shepherd's Flock (Faction)
  operational_status: Protest dispersed by party diplomacy...
    [OBSERVED, session 7, from: Session 7 Recap]
    competing: CANON=active_protest, PREP=riot_escalation
  goals: Surface: toll abolition. Observed deeper: secret base with cells...
    [OBSERVED, session 7]
```

**LLM prompt:**
```
System: You are a GM assistant. Answer using ONLY the facts in the projection.
Cite truth_states (CANON/PREP/OBSERVED). If facts conflict, explain which is current.
Do not invent beyond what is stated.
```

**Model:** `retrieval_synthesis` (gpt-5.3-chat-latest) — grounded response synthesis.

#### Component 7: CLI Loop (`src/cli.py`)

```
$ uv run python -m dungeonbuddy --store ./my_campaign

dungeonbuddy> ingest "path/to/doc.docx" --layer world
dungeonbuddy> ask "What do I need to know about Mirathorn?" --campaign longmont_01
dungeonbuddy> plan "The protest will escalate" --campaign longmont_01
dungeonbuddy> play "The party stopped the riot" --campaign longmont_01 --session 7
dungeonbuddy> provenance "Brother Ashwood"
dungeonbuddy> entities
dungeonbuddy> projection --campaign longmont_01
```

| Command | Pipeline |
|---|---|
| `ingest` | docx → chunk → Pass 1 → Pass 2 → store |
| `ask` | store.project() → format context → LLM synthesis → print prose |
| `plan` | inline text → single evidence unit (planning_document) → Pass 1 → Pass 2 → store (PREP) |
| `play` | inline text → single evidence unit (observed_session_recap) → Pass 1 → Pass 2 → store (OBSERVED) |
| `provenance` | find entity → list facts → trace evidence_ids → print chain |
| `entities` | list all entities with fact counts |
| `projection` | run reducer → print formatted projection |

### Gold Artifacts for Set A Evaluation

Before running the automated pipeline, hand-author gold expected outputs:

**`The City of Mirathorn.docx` gold:**
- Gold entity list: Mirathorn, Lake Mirathorn, Stormspire Peaks, Lundayell Empire, Festival of Expansion, Shepherd's Flock, Wizard's Tower Brewing Co., and every NPC from City Council. (~15-20 entities)
- Gold fact set: Extend the 10 Step 1 facts with additional facts for skipped entities.

**`The City Council.docx` gold:**
- Gold entity list: every council member, the council as a faction, The Wolf, referenced locations.
- Gold fact set: role/rank_or_title for each council member, governance for Mirathorn.

**`lieutenant_lysandra_ironveil_character_dossier.md` gold:**
- Already has 6 golden scenario tests. Extend with gold entity list and fact set.

### Build Order

| Phase | What | Depends On | Gate |
|---|---|---|---|
| A | Fact store + docx-to-markdown + chunker | Nothing | Chunker produces evidence units from Mirathorn.docx structurally similar to hand-authored Step 1 units |
| B | Entity extraction (Pass 1) | Phase A + `openai` dep | Strict recall ≥0.90 and loose recall ≥0.95 against Mirathorn gold entity list, with entity density ≤1.80 per evidence unit (OpenAI-backed eval path only) |
| C | Fact extraction (Pass 2) | Phase B | Automated projection covers same ground as Step 1 hand-authored projection. Attribute classification reasonable. |
| D | Synthesis + CLI (`ingest`, `ask`) | Phase C | `ingest` Mirathorn.docx then `ask "Catch me up on Mirathorn"` produces grounded prose |
| E | `plan`, `play`, `provenance` | Phase D | Full CLI loop from design doc example works end-to-end |
| F | Blind eval (Set B) | Phase E frozen | GM evaluates Mossford projection without pipeline changes |

### Files to Create

```
src/
  ingestion/
    __init__.py
    docx_converter.py       # Phase A — docx → markdown
    chunker.py              # Phase A — markdown → AST → evidence units
    entity_extractor.py     # Phase B — Pass 1 LLM, adapts enrich_units_batch
    fact_extractor.py       # Phase C — Pass 2 LLM, adapts enrich_units_batch
    pipeline.py             # Phase C — orchestrates chunk → Pass 1 → Pass 2
  agent/
    __init__.py
    synthesis.py            # Phase D — projection → LLM → prose
    context_formatter.py    # Phase D — projection dict → text for LLM
  store.py                  # Phase A — JSON fact store
  cli.py                    # Phase D — CLI REPL
  __main__.py               # Phase D — `python -m dungeonbuddy`

tests/
  test_store.py             # Phase A
  test_chunker.py           # Phase A
  test_docx_converter.py    # Phase A

evals/
  mirathorn_vertical_slice/
    gold/
      gold_entities.json    # Phase B
      gold_facts.json       # Phase C
    eval_entity_recall.py   # Phase B
    eval_fact_quality.py    # Phase C
```

### Phase B Status (2026-03-27)

Phase B (Pass 1 entity extraction) is implemented and validated.

- OpenAI Responses structured parse adapter is wired (`responses.parse` + Pydantic model output).
- Eval gate now loads `.env.development`, requires `OPENAI_API_KEY`, and disables heuristic fallback.
- Gate reports strict recall, loose recall, and entity-density guardrail.
- Current Mirathorn strict gate result:
  - strict recall: `1.000`
  - loose recall: `1.000`
  - entity density: `1.603` (threshold `<= 1.80`)
  - gate: PASS

## Relationship to Original Plan

The original Mirathorn event-sourced slice plan is architecturally sound. This design doesn't reject it — it resequences it to answer the highest-risk question first (does the output work for a GM?) before committing to infrastructure.

| Original Plan Phase | This Design |
|---|---|
| Lock sources + author full gold pack | Step 1: Small hand-authored fixtures only |
| Build event-first ingestion loop | Step 4: After manual validation |
| Projection runner (3 checkpoints) | Steps 1–3: Prove each layer independently |
| Hard gates + determinism | Step 5: After ingestion works |

## Applicable Knowledge from RulesIngestion

**Directly transferable:**
- Section-aware splitting by heading structure (the chunking pipeline shape)
- Schema validation and contract-first design (validate before persist)
- Gold-anchored evaluation (benchmark extraction against hand-curated expected outputs)
- Chunk quality gates (reject micro-chunks, detect duplicates before indexing)

**Key findings that shaped this design:**
- Raw atomic evidence units pollute retrieval pools (190/1000 top-K results ≤40 chars in Starfinder). Fix: fold short units, merge by heading. Here, we sidestep this by querying over projected facts, not raw evidence units.
- Compositional queries need co-retrieval of multiple units. Here, the projection reducer assembles multi-evidence facts at projection time, so the agent gets composed answers directly.
- Chunk recipe must be locked before comparing anything else. Applies equally to extraction eval: lock the chunking before comparing extraction model performance.

**Key difference:** RulesIngestion extracts deterministic mechanical rules. DungeonMindBuddy extracts narrative, interpretive, layered world-state. The pipeline shape transfers; the extraction prompts and target schemas do not.

## Architecture: Projection → Agent → GM

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  Reducer      │ ──► │  LLM Agent   │ ──► │  GM          │
│  (projection) │     │  (prose)     │     │  (judgment)  │
│               │     │              │     │              │
│  Structured   │     │  Synthesizes │     │  Reads,      │
│  facts with   │     │  grounded    │     │  agrees or   │
│  provenance   │     │  narrative   │     │  corrects    │
└──────────────┘     └──────────────┘     └──────────────┘
        ▲                                       │
        └───── provenance available on demand ──┘
```

The default GM experience is prose from the agent. The projection lives in the background — but the provenance chain (fact → evidence → source section) is always accessible when the GM needs to inspect why the agent said what it said, or trace a claim back to its source document.

Logging is critical to this. Without high-quality logs of what the system did — which facts were projected, which layers contributed, which conflicts were resolved — there's no way to audit or correct the agent's output. The provenance isn't decoration; it's the mechanism by which the GM maintains authority over the system.

## Success Criteria: The CLI Chat Loop

The vertical slice is successful when it works as a command-line chat loop. If the core loop works in a terminal, it can be wired to the frontend later — that's just UI.

### The Loop

```
$ dungeonbuddy

> ingest "The City of Mirathorn.md"
  Ingested 8 evidence units, 12 entities, 27 facts (world canon)

> ingest "Campaign 1 Notes.md"
  Ingested 5 evidence units, 4 entities, 11 facts (campaign: longmont_01)

> ask "Catch me up on Mirathorn. What do I need to know?"
  Mirathorn sits at the base of the Stormspire Peaks...
  [grounded prose from projection, citing canon + campaign history]

> plan "The Shepherd's Flock protest will escalate into a riot tonight.
        Brother Ashwood will attempt to poison the water supply during
        the closing ceremony."
  Added 3 planning facts (campaign: longmont_01, truth_state: PREP)

> ask "What NPCs should I have ready for tomorrow?"
  [prose incorporating world canon NPCs + planning context]

> play "The party infiltrated the Shepherd's Flock. They learned about
        the water poisoning from inside. Brother Ashwood is the cell leader."
  Added 4 observed facts (campaign: longmont_01, truth_state: OBSERVED)
  Brother Ashwood: new entity created

> ask "What happened vs. what I planned?"
  [prose distinguishing PREP facts from OBSERVED facts, showing where
   play diverged from plan]

> provenance "Brother Ashwood"
  Entity: Brother Ashwood (ent_brother_ashwood)
  Facts:
    role: Shepherd's Flock cell leader [OBSERVED, session 5]
      ← evidence: "play" input, 2026-03-29
    goals: orchestrating water supply poisoning [PREP → OBSERVED]
      ← evidence: planning input + play confirmation
```

### What This Requires

1. **A fact store** — persists ingested evidence units, entities, and facts across commands
2. **The existing reducer** — projects current state from the store on each query
3. **An LLM call** — takes the projection as context, answers the question as grounded prose
4. **Ingestion pipeline** — parses markdown with frontmatter, extracts entities/facts via LLM
5. **Plan/play shortcuts** — lighter-weight ingestion for inline planning and session notes

### What "Works" Means

- `ingest` adds facts that show up in subsequent `ask` responses
- `ask` produces prose that is grounded in the projection (doesn't hallucinate beyond it)
- `plan` adds PREP-layer facts that the agent can distinguish from CANON
- `play` adds OBSERVED-layer facts without corrupting canon or planning
- `provenance` traces any claim back to its source evidence
- The same Mirathorn corpus produces consistent answers across sessions

If this loop works in a terminal, the frontend is just wiring. The core problem — layered, grounded, provenance-traced GM context — is solved.

## Evaluation: Blind A/B Corpus Split

The pipeline is validated against a development set and evaluated against a held-out blind set from the same corpus. The blind set is never touched during pipeline development.

### Set A — Development (tune against these)

| Document | Role |
|---|---|
| `The City of Mirathorn.docx` | Primary world canon doc. Step 1 gold fixtures authored from this. |
| `The City Council.docx` | NPC-heavy sub-doc. Council members referenced in Mirathorn facts. |
| `Longmont Campaign General Notes.docx` | Campaign-layer source. Tests campaign vs. world layer handling. |
| `lieutenant_lysandra_ironveil_character_dossier.md` | NPC dossier. Used in existing 6 reducer scenarios. |

Prompts are tuned, edge cases are fixed, and gold artifacts are authored against Set A docs. These are the training set.

### Set B — Blind (evaluate generalization)

| Document | What it tests |
|---|---|
| **Mossford Gazetteer + 12 location dossiers** | Complete separate city with same structure as Mirathorn. Tests generalization to a different place. 12 sub-docs (Copper Moss Brewery, Temple of the Nameless Stone, Watch Tower, etc.) test entity-linking across related documents. |
| **The cult of the Great Shepherd.docx** | Faction doc. Tests faction entity extraction, goals/methods attributes, and cross-entity links to Mirathorn entities (Ashenvale, corrupted guards). |
| **Festival of Expansion event docs** | Event-type content. Tests event entity extraction, schedule/mechanics, NPC participants across scenes. |
| **Stonebridge and The Wizard Tower Brewing Co.docx** | Another location. Tests generalization beyond cities. |
| **Campaign 2 Session Recaps / Narrative Ledger** | Campaign-layer content. Tests `truth_state: OBSERVED` fact production from session recaps. |

Mossford is the ideal blind anchor: a full town with a gazetteer and 12 location dossiers, structurally similar to Mirathorn but with different content. If the pipeline produces a Mossford projection the GM agrees with — without ever having tuned against it — that's real evidence of generalization.

### Benchmark Protocol

1. Build the pipeline against Set A. Tune prompts, fix edge cases, get entity recall and fact quality where you want them.
2. Freeze the pipeline. No more changes.
3. Run it on Set B.
4. GM evaluates blind output:
   - **Entity recall:** did it find everything named? (recall-oriented gate)
   - **Fact accuracy:** are the labels faithful to the source text?
   - **Attribute classification:** did geography go to `geography`, defenses to `defenses`?
   - **Cross-doc linking:** do entities mentioned in multiple Set B docs get connected?
5. Any failure in Set B that requires a pipeline fix → re-run Set B after the fix to confirm it didn't just overfit to the new case.
