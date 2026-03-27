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
**Gate:** Does the projection contain everything an agent would need to write an accurate description of Mirathorn? PASSED — Step 1 complete.

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

### Step 4: Decide on Ingestion Automation

**Only after Steps 1–3 pass.** At this point you know:
- The projection shape gives an agent sufficient grounded context
- The layer boundaries hold with real content
- What the LLM extraction pipeline needs to produce

Then build the ingestion loop, leveraging patterns from RulesIngestion (chunking, evidence unit extraction, schema validation). The extraction target is narrative facts rather than mechanical rules, but the pipeline shape is transferable.

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
