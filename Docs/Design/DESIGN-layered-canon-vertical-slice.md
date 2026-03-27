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

#### Chunking Strategy

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

- Evidence unit extraction patterns (chunking, section-aware splitting)
- Schema validation and contract-first design
- Gold-anchored evaluation (benchmark against hand-curated expected outputs)
- Embedding and retrieval patterns (when the canon layer needs to be queried, not just projected)

The key difference: RulesIngestion extracts deterministic mechanical rules. DungeonMindBuddy extracts narrative, interpretive, layered world-state. The pipeline shape transfers; the extraction prompts and target schemas do not.

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

## Success Criteria

After Step 3, an agent given the three-layer projection can:
1. Describe Mirathorn accurately from canon, citing sources
2. Distinguish world truth from GM planning intent from live session events
3. Never hallucinate beyond what the projection contains
4. Each layer is clearly separated, provenance is traceable, and canon was never corrupted by higher layers

If that demo works, the rest is execution.
