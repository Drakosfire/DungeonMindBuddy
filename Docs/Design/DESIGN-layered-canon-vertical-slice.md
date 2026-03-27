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

Section-level chunking using heading structure. One heading section → one evidence unit → typically 1–3 facts per entity mentioned. The heading hierarchy provides the `section_path` for provenance.

Leverage patterns from RulesIngestion (section-aware splitting, schema validation). The extraction target is narrative facts rather than mechanical rules, but the pipeline shape is transferable.

### Step 5: Event Sourcing and Infrastructure

**Only after Step 4 works.** Event sourcing, hard gates, determinism replay, gold artifact packs — all the infrastructure from the original plan — gets built once the core model is validated and the ingestion pipeline produces usable output.

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
