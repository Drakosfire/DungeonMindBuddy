# DungeonBuddy Main
_Exported on 3/27/2026 at 10:21:51 MDT from Cursor (2.6.21)_

---

**User**

@DungeonMindBuddy/Docs/Plans/HANDOFF-next-agent-mirathorn-event-slice.md @DungeonMindBuddy/Docs/Plans/mirathorn_event-sourced_slice_8eab1beb.plan.md 
Lets examine these docs and this plan, lets consider how feasible this plan and goal are. 
We have a lot of knowledge about ingesting, chunking, information. 

Now we are aiming to build some layers of graphs that describe and support me as a game master using DungeonMind as a suite of tools in a similar way to how I work with an agent over a long period. 

However the first thing to do is see how we get a good vertical slice going. Evidence the idea on some of its assumptions works. 

Which currently is designed as My corpus of documents in a canon description that I would read and agree with as context ready to be used in an agent. 
Overlaying that with the planning, which takes the location and idea, and adds a plan or scenario over it, then on top of that is the play and how it interacts and updates the current state. 

So I see the is as layers. 

---

**Cursor**

Let me read both documents to understand the current plan and then we can discuss feasibility and the layered architecture you're describing.

Let me also look at what already exists in the DungeonMindBuddy codebase to ground this discussion in reality.

Now I have a solid picture. Let me give you an honest feasibility assessment grounded in what actually exists and what the plan proposes.

---

## What's Already Proven

The foundation is more real than a lot of plans at this stage:

- **7 JSON schemas** (evidence_unit, event, fact, conflict, canon_decision, entity, mention) all with Draft 2020-12 validation
- **A working deterministic reducer** (`canon_projection.py`) that takes facts + evidence + conflicts + decisions and produces a projection with provenance
- **6 golden scenarios** with a benchmark runner that tests layer isolation, conflict detection, and determinism
- **Schema validation pipeline** with proper `$ref` registry

The reducer already enforces the invariant you care most about: *campaign facts never overwrite world canon*. That's not theoretical - it's tested across 6 scenarios.

---

## Your Layers Model vs. The Plan

The way you're describing it - three layers - is cleaner than what the plan documents, and I think it's the right lens. Let me map it:

| Your Layer | Plan's Term | What It Represents |
|---|---|---|
| **Canon** | WorldCanon + CampaignRecap → Instantiation projection | "What is true about Mirathorn?" - stuff you'd read and nod at |
| **Planning** | PlanningEvents → ZeroTick projection | "What am I setting up for next session?" - GM prep overlaid on canon |
| **Play** | LiveSessionEvents → LiveState projection | "What happened when the players showed up?" - runtime state changes |

The plan calls these "projection checkpoints" but they're really your three layers materialized at different points.

---

## Feasibility: Where It's Strong

**Layer 1 (Canon) is almost proven.** The reducer already takes evidence units tagged with `canon_layer=world` and `canon_layer=campaign`, resolves conflicts between them, and produces a projection that preserves world baseline. The 6 scenarios exercise this. What's missing is feeding *real prose* (your Mirathorn doc) through it rather than hand-crafted JSON fixtures.

**The schema contracts are solid.** The fact that attribute enums, truth states, and layer semantics are all schema-enforced means you won't be chasing structural bugs. The schemas are opinionated enough to be useful but flexible enough for the three layers.

**The layering invariant is the hardest part and it's already working.** Campaign-scoped facts can't mutate world canon. That's the core guarantee, and it passes determinism tests.

---

## Feasibility: Where It Gets Risky

**1. The ingestion gap is the biggest hole.** The plan says "Adapt LLM ingestion loop to emit event-first outputs" but there's no LLM integration code in DungeonMindBuddy at all. You have extensive ingestion infrastructure over in RulesIngestion, but that pipeline is built for rules extraction (evidence units, clause-level granularity), not narrative world-building. The extraction target is fundamentally different:

- RulesIngestion: "What are the mechanical rules?" → structured, deterministic facts
- DungeonMindBuddy: "What is true about this fictional place?" → narrative, interpretive, layered

**2. The plan front-loads a massive gold artifact pack.** It asks you to manually author `evidence_units.json`, `events.json`, `facts.json`, `conflicts.json`, `canon_decisions.json`, plus three projection files - all by hand before any code runs. That's a lot of manual work before you get signal on whether the model even works for narrative content.

**3. Event-sourcing adds complexity before proving value.** The plan insists on event-first ingestion with strict ordering and participant linking. For a vertical slice, the question is: does the event layer earn its keep? You need events if you want "what changed and why" audit trails. But if the first thing to prove is "can I get a canon description I agree with," events are overhead.

---

## What I'd Recommend for the Vertical Slice

Your instinct is right - prove the layers bottom-up. But I'd sequence it differently than the plan:

**Step 1: Prove Canon reads right (smallest possible loop)**

Take the Mirathorn doc, extract a small number of facts and evidence units (5-10, by hand or with a quick LLM pass), feed them through the existing reducer, and look at the output. Ask yourself: *does this projection read like a description of Mirathorn I'd hand to a player or use as GM context?*

This tests the most important assumption: that the schema and reducer produce output that's useful to you as a GM, not just structurally valid.

**Step 2: Prove the layer boundary with one planning overlay**

Take that canon projection, add 2-3 "planning" facts (e.g., "the protest at the gates will turn violent when the party arrives," "the merchant guild has a spy in the guard"), and project again. Does the world canon stay intact? Does the planning overlay read like session prep you'd actually use?

**Step 3: Prove play updates don't corrupt the lower layers**

Add 1-2 "live" events (e.g., "the party sided with the protesters," "the guard captain was killed"). Project again. Can you see the three layers clearly in the output? Does the audit trail make sense?

Each step is maybe 1-2 hours of work, mostly authoring small JSON fixtures by hand and running them through the existing reducer. No LLM integration needed. No massive gold pack. You'd know within a day whether the model works for your use case.

**Step 4: Then worry about ingestion automation**

Once you're confident the layers produce output you'd actually use at the table, *then* build the LLM extraction pipeline. You'll know exactly what shape of output you need because you wrote the gold by hand and verified it works.

---

## The Core Question to Answer First

The plan is architecturally sound but front-loads infrastructure (event sourcing, hard gates, determinism replay) before answering the most important question:

> **Does the projection output read like something I'd actually use as a GM?**

If the answer is yes, the infrastructure investment pays off. If the projection format needs significant rethinking, you'll be glad you didn't build 6 types of gold artifacts first.

Your RulesIngestion experience is directly transferable for the extraction pipeline when you get there. The chunking, evidence unit extraction, and schema validation patterns all apply. But the *target representation* (narrative facts vs. mechanical rules) is different enough that you want to validate it with small manual examples before automating.

Does this assessment match your intuition? I'm curious whether you've already mentally validated that the reducer output format works for GM context, or if that's still an open question.

---

**User**

Yes, I agree, lets capture this as a high level plan for next steps. 
Put that in Docs in Design. 

---

**Cursor**

Done. The design doc is at `DungeonMindBuddy/Docs/Design/DESIGN-layered-canon-vertical-slice.md`. It captures the three-layer model, the resequenced steps that front-load the "does this output actually work for a GM" question, and defers infrastructure until that's answered. Each step is scoped to 1–2 hours with a clear gate before moving on.

---

**User**

Alright lets address step 1 
@DESIGN-layered-canon-vertical-slice.md (46-54) 

---

**Cursor**

Let me understand the exact input format by reading the existing infrastructure, and then find the Mirathorn source material.

Now let me look at an existing scenario to see the exact fixture format and the runner.

Now let me find the Mirathorn source content.

Good, the source doc exists. Let me extract the text from it.

Excellent. I have the full Mirathorn source text and understand the exact fixture format. Now I have what I need to author the Step 1 fixtures and run them through the reducer.

Let me note something important I spotted: the fact schema's `attribute` enum is NPC-centric (`species`, `role`, `mental_state`, etc.). Mirathorn is a *location* and Shepherd's Flock is a *faction*. Some attributes map reasonably (e.g., `current_location`, `operational_status`, `portrayal_notes`), but this is itself a finding the vertical slice should surface.

Let me build the fixtures and a runner.

Now let me write the runner script that loads these fixtures, validates them, runs the projection, and renders it in a way a GM can actually read.

Now let me check the `validate_many` function signature to make sure I'm calling it correctly.

The `validate_many` function raises exceptions rather than returning errors, and it expects a full filename like `evidence_unit.schema.json`. Let me fix the runner.

Now let's run it.

It works. All 8 evidence units and 10 facts validate against the schemas, the reducer produces a clean projection, and there are zero conflicts (expected — it's all world-layer canon from one document).

Here's what I'd put in front of you for the gate question:

---

**The output does read like usable GM context.** If I were prepping for a session and someone handed me this, I'd know:
- Where Mirathorn is, what it looks like, what it does economically
- The vibe when players approach (festive chaos, bottleneck, tension)
- Who the Shepherd's Flock are and what they're up to
- The founding history as background color
- Every fact traces back to a specific section of your source doc

**Things that surfaced that are worth noting:**

1. **The attribute enum is NPC-shaped for non-NPC entities.** Using `species` for a city's racial composition and `physical_condition` for its walls works but feels like a stretch. A location might want attributes like `description`, `defenses`, `demographics`, `history`. A faction might want `goals`, `methods`, `leadership`. This doesn't block Step 1 but it's a clear schema evolution target.

2. **The `normalized` field on facts is awkward for locations.** `stormspire_peaks_base:lake_mirathorn` as a normalized location value is something I invented — there's no convention for it. For NPCs the normalized field makes sense (`disciplined`, `alive`). For places and factions it's less clear what normalization means.

3. **The projection format is entity-attribute-value, which is analytical but not narrative.** A GM might prefer a prose briefing ("Mirathorn sits at the base of the Stormspire Peaks...") rather than a fact table. The raw projection is great for machine consumption and provenance tracking, but a rendering layer that turns it into prose would make it GM-ready.

4. **The provenance chain works well.** Every fact traces back to a specific section path in the source doc. That's exactly the audit trail you'd want.

**The core model works.** The reducer correctly produces a per-entity, per-attribute projection with layer isolation and provenance. The next question is whether you agree with how the Mirathorn content reads in this format, and whether the attribute enum needs broadening before Step 2.

---

**User**

Alright we worked on 1 and 2, take a look. 

---

**Cursor**

Let me read the current state of the files you've been working on.

Good changes. You addressed both issues:

**1. Attribute enum expanded.** The `attribute` definition in `common.schema.json` moved from being inline in the fact schema to a shared `$defs/attribute` and gained seven new domain-appropriate attributes: `history`, `geography`, `demographics`, `defenses`, `economy`, `governance`, `atmosphere`, `goals`. The fact schema now references it via `$ref`.

**2. Facts rewritten to use the right attributes.** The Mirathorn facts now use `geography` instead of `current_location`, `economy` instead of `role`, `demographics` instead of `species`, `defenses` instead of `physical_condition`, `history` instead of `source_comments`, `atmosphere` instead of `portrayal_notes`. The Shepherd's Flock fact that was `loyalty_or_alignment_context` is now `goals`. The `normalized` field usage is also cleaner — `null` where normalization doesn't make sense (history, atmosphere) and colon-delimited tags where it does (geography, economy, defenses).

Let me re-run the projection to make sure everything validates and renders with the new attributes.

That reads much better. The Mirathorn section now has attributes that make immediate sense for a location: Geography, History, Demographics, Economy, Defenses, Atmosphere, Operational Status. And the Shepherd's Flock has Goals instead of the shoehorned loyalty/alignment attribute.

Let me also verify the existing 6 scenarios still pass with the updated schema, since you changed where `attribute` is defined.

All 18 existing tests pass. The schema refactor (extracting `attribute` to `common.schema.json` and broadening the enum) is backward-compatible with the existing Lysandra-based scenarios.

The projection now reads like a GM reference sheet. Geography, History, Demographics, Economy, Defenses, Atmosphere — those are the sections you'd actually scan when prepping a session about Mirathorn. This is a solid Step 1 pass. Ready for Step 2 (planning layer) whenever you are.

---

**User**

Lets self reflect and commit

---

**Cursor**

Here's what's in the commit:

**Schema refactor (your edits):**
- `common.schema.json` — Extracted `attribute` enum into shared `$defs/attribute`, added 7 new location/faction attributes: `history`, `geography`, `demographics`, `defenses`, `economy`, `governance`, `atmosphere`, `goals`
- `fact.schema.json` — Replaced inline attribute enum with `$ref` to shared definition
- `event.schema.json` — Same `$ref` consolidation (was duplicating the enum)

**Dependency:**
- `pyproject.toml` + `uv.lock` — Added `python-docx` (used to extract Mirathorn source text)

**New files (our joint work):**
- `Docs/Design/DESIGN-layered-canon-vertical-slice.md` — Layered canon design doc
- `evals/mirathorn_vertical_slice/input/` — 8 evidence units + 10 facts hand-authored from the Mirathorn doc, plus empty conflicts/decisions
- `evals/mirathorn_vertical_slice/run_step1.py` — Runner that validates schemas, runs reducer, renders GM-readable projection
- `evals/mirathorn_vertical_slice/output/world_projection.json` — The actual projection output

All 18 existing tests pass. The schema change is backward-compatible.

Committed as `b1cdf23`. 

**Self-reflection on what we proved and what's next:**

**What Step 1 established:**
- The reducer produces a per-entity, per-attribute projection from real Mirathorn content that reads like a GM reference sheet
- The schema extension for location/faction attributes was needed and is backward-compatible
- Provenance tracing (fact → evidence → source section) works end-to-end
- The existing test suite is unaffected

**What Step 1 surfaced as open questions:**
- The `normalized` field convention for non-NPC attributes isn't settled (you used `null` for narrative attributes like history, colon-delimited tags for structured ones like economy — that feels right but should be codified)
- The projection is analytical (entity-attribute-value table), not narrative prose. A rendering layer that turns the projection into a GM briefing paragraph would make this directly usable as agent context
- `governance` was added to the enum but no fact uses it yet — the City Council section in the doc is a natural source for that

**Step 2 (Planning layer)** would add 2-3 campaign-scoped facts on top of this world baseline and verify the layer boundary holds with real narrative content rather than the synthetic Lysandra scenarios.

---

**User**

I'm not sure this is a negative. This is context that would be used for an agent to write prose for the GM to interpret or use or discard. 
The projection is analytical (entity-attribute-value table), not narrative prose. A rendering layer that turns the projection into a GM briefing paragraph would make this directly usable as agent context
I think the LLM is a projection layer to the user as prose. 

---

**Cursor**

You're right, and that's a cleaner architecture than what I was suggesting. The projection isn't the end-user output — it's the *context the agent consumes* to produce prose. The LLM is the rendering layer.

That means the entity-attribute-value format is actually ideal for its purpose: structured, unambiguous, with provenance. An agent given that projection can write "Mirathorn sits at the base of the Stormspire Peaks..." and cite exactly where that came from. The analytical format is a feature, not a gap — it gives the agent facts to synthesize rather than pre-baked prose to parrot.

This also means the quality gate for the projection isn't "would a GM read this directly?" but rather "does this give an agent everything it needs to write accurate, grounded prose about Mirathorn?" That's a different and arguably easier bar to clear, and the Step 1 output already passes it.

---

**User**

I think this is right. 
Update the guiding docs to reflect this 
This also means the quality gate for the projection isn't "would a GM read this directly?" but rather "does this give an agent everything it needs to write accurate, grounded prose about Mirathorn?" That's a different and arguably easier bar to clear, and the Step 1 output already passes it.

---

**Cursor**

Updated. The design doc now reflects that the projection is agent context, not GM-facing output. The key changes:

- New section "The Projection Is Agent Context, Not GM Output" making the architecture explicit
- Gate criteria reframed from "would a GM read this" to "does this give an agent what it needs"
- Architecture diagram showing the three-stage pipeline: Reducer → Agent → GM
- Success criteria rewritten around agent grounding and provenance, not direct GM readability
- Step 1 marked as PASSED

---

**User**

There is the provenance, so the GM can access this, it's not NEVER. It's in the background unless otherwise specified. 
Logging is critical.
We can't KNOW what we've done without high quality logs. When needed.

---

**Cursor**

Fixed. The projection isn't hidden from the GM — it's in the background, available on demand. And logging is called out as the mechanism that makes the whole thing trustworthy. Without it you can't know what the system did, can't trace why the agent said something, can't correct it when it's wrong.

---

**User**

Now, stop and reflect on what informed how the facts you wrote were constructed. 
Lets discuss and imagine an agent loop that ingested GM docs in markdown. GMs would need to flag Canon, or Play or Planning. 
What is the prompt broadly, shaped like to accomplish this. What are the data shapes we are asking for?



---

**Cursor**

Good question. Let me trace what I actually did when I authored those facts, because that's the specification for what the ingestion agent needs to replicate.

**What I did, step by step:**

1. **Read the source prose** and used the heading structure (Mirathorn Overview, Origin and History, Location, etc.) to segment it into evidence-sized chunks. Each heading boundary was roughly one evidence unit.

2. **Identified entities** by asking "who or what is this section *about*?" Not every noun — just the subjects that facts hang off of. Mirathorn is the subject of geography facts. Shepherd's Flock is the subject of goals facts. I skipped entities that were only *mentioned* (Lake Mirathorn, Stormspire Peaks, Lundayell Empire) because no facts were asserted about them specifically.

3. **Classified each chunk into an attribute** from the enum. This was the most interpretive step. The wall description could have been `physical_condition` or `atmosphere` — I chose `defenses` because the content was about fortifications. The economy paragraph was clearly `economy`. The "scene for players" section was `atmosphere` because it described sensory experience and mood.

4. **Decided the value shape** for each fact:
   - `scalar` for simple assertions ("founded 200+ years ago")
   - `state` for current conditions ("aged walls, symbolic towers")
   - `set` for enumerations (the list of races)
   - `interpretive` for things that required reading between the lines (the Shepherd's Flock having an "underlying cult agenda not yet visible to public" — that's GM knowledge layered onto what the text says about a protest)

5. **Wrote the label** as a compressed but faithful summary of the source text. Not a copy-paste, not a rewrite — a distillation that preserves the key information.

6. **Decided what `normalized` means** per attribute — or left it `null` when normalization doesn't apply (history is narrative, you can't normalize it to a tag).

**The hard parts an agent would need to handle:**
- Granularity: how much text is one evidence unit? One fact?
- Entity vs. mention: is Stormspire Peaks an entity we track, or just context in a fact about Mirathorn?
- Attribute selection from the enum — multiple valid choices exist
- When to use `interpretive` vs. `scalar` — the cult agenda fact is GM-level knowledge, not surface text

---

Now, for the ingestion loop. The GM provides markdown docs and flags the layer. Here's what I think the shape looks like:

**GM input:**
```markdown
---
canon_layer: world          # GM declares: world | campaign | planning
campaign_id: null           # null for world, required for campaign/planning
source_class: seed_reference # what kind of doc this is
document_title: "The City of Mirathorn"
---

## Mirathorn Overview
### Origin and History
Founded over 200 years ago by settlers fleeing...
```

The frontmatter is the GM's declaration. They're saying "everything in this document is world canon" or "this is my planning notes for campaign_longmont_01." That's a human judgment the system shouldn't guess at.

**Agent prompt shape (broadly):**

The agent gets a chunk of text plus metadata and produces structured extraction. Something like:

> You are extracting structured facts from a GM's world-building document.
> 
> **Source metadata:** [layer, source_class, document_title, section_path]
> 
> **Text:** [the evidence chunk]
> 
> **Extract:**
> 1. **Entities** — identify the primary subjects (people, places, factions, items). Only subjects that facts are asserted *about*, not every mention.
> 2. **Facts** — for each entity, extract facts using these attributes: [the enum]. For each fact provide:
>    - attribute (from enum)
>    - label (faithful summary of what the text asserts)
>    - kind (scalar | state | set | interpretive)
>    - normalized (short tag if applicable, null if the content is narrative)
>    - interpretation_level (direct_assertion | derived_summary | interpretive_inference)
> 
> **Output schema:** [the JSON shapes]

**The data shapes the agent produces:**

```
Input:  markdown chunk + frontmatter metadata
         ↓
Output: {
  evidence_units: [          # the chunks themselves, with section_path
    { text, section_path, paragraph_index, source_order_index }
  ],
  entities: [                # subjects identified
    { display_name, entity_type, aliases }
  ],
  facts: [                   # structured assertions
    { subject_entity_id, attribute, value: {kind, label, normalized, ...} }
  ]
}
```

The agent doesn't decide the layer — the GM already did that in the frontmatter. The agent doesn't decide `truth_state` — that's derived from the layer and source_class (`world` + `seed_reference` → `CANON`; `campaign` + `planning_document` → `PREP`). The agent's job is entity identification, attribute classification, and faithful summarization.

**The key design question** is chunking granularity — does the agent get the whole document and segment it, or do we pre-chunk by heading and give it one section at a time? Given what we know from RulesIngestion, section-level chunking with heading context is probably the right unit. One heading section → one evidence unit → typically 1-3 facts per entity mentioned.

What's your instinct on the chunking approach and the frontmatter convention?

---

**User**


Added the quality gate for Pass 1. The key principle: recall over precision. A missed entity is a broken graph connection that's hard to detect later. An extra entity is easy to prune or merge. The gate validates against gold entity lists and is explicitly recall-oriented.

This also means when we build the eval for Step 4, the gold artifact for Pass 1 should be a comprehensive entity list from the Mirathorn doc — including Lake Mirathorn, Stormspire Peaks, Lundayell Empire, Festival of Expansion, Wizard's Tower Brewing Co., and every NPC named in the City Council section. That becomes the benchmark the extraction agent must match or exceed.

The key design question is chunking granularity — does the agent get the whole document and segment it, or do we pre-chunk by heading and give it one section at a time? Given what we know from RulesIngestion, section-level chunking with heading context is probably the right unit. One heading section → one evidence unit → typically 1-3 facts per entity mentioned.

What's your instinct on the chunking approach and the frontmatter convention?

I think we did quite a bit of experimentation and have the reports and data laying around to make a very informed decision that will be a better than average baseline. 

So go poke around in RulesIngestion and surface the most relevant documents to the question of what size chunk provide high retrieval quality. 

Then we think about it from the lens of this goal which is to provide the LLM with enough context, which maybe has the exact same answer, or a slightly different or a very different. 

---

**Cursor**

Good find. Let me read the two most directly relevant documents — the chunking deep dive and the combined learnings report that frames the "too small vs. too big" tradeoff.

Now I have the full picture from RulesIngestion. Let me synthesize what's relevant and then think through how it applies differently to DungeonMindBuddy.

---

**What RulesIngestion learned about chunk granularity:**

The core finding is **not a magic number** — it's a **failure mode and its fix**:

1. **Raw Stage B evidence units are too atomic for retrieval.** Starfinder went from 13,162 raw units to 2,386 after fold + heading merge. The raw corpus flooded top-20 results with micro-chunks (190/1000 results were ≤40 chars) and duplicates (162 entries in duplicate groups). These are chunks like "Read Magic — Spell Level: M1" — a heading absorbed into a tiny unit.

2. **The fix is fold + merge, not a sweep of sizes.** `min_chars=200` folds short units into neighbors. `merge_max_chars=2000` merges consecutive units under the same heading. There was never a controlled experiment of "is 1500 better than 2000" — the 2000 cap was chosen as a reasonable ceiling and validated by eliminating the micro-chunk/duplicate failure mode.

3. **The real frontier isn't chunk size, it's chunk *coherence*.** The combined learnings report is clear: the next gains come from ensuring chunks are *self-sufficient* for the questions they need to answer. "Too small" creates fragments that don't retrieve well. "Too big" blurs semantics. The answer isn't a number — it's asking whether the unit contains enough context to be useful on its own.

4. **Compositional queries (T2) are the hardest.** Questions like "what applies when X and Y" need multiple units retrieved together. Single-chunk retrieval can't solve this alone — you need co-retrieval, cross-reference edges, or family projections.

---

**Now: how does this apply to DungeonMindBuddy?**

The use case is fundamentally different, and I think the answer is different too.

**RulesIngestion's retrieval problem:** Given a question ("how does sneak attack work?"), find the right chunks from a corpus of 2,000-13,000 evidence units to assemble an answer. The embedding model needs to match question phrasing to chunk content. Chunk size directly affects retrieval precision.

**DungeonMindBuddy's ingestion problem:** Given a GM's markdown document, extract entities and facts from it. The chunk isn't a retrieval target — it's the *input to an LLM that extracts structured data*. The question isn't "will this chunk be found by a query?" but "does this chunk give the LLM enough context to correctly identify entities and classify facts?"

These are different pressures:

| Concern | RulesIngestion (retrieval) | DungeonMindBuddy (extraction) |
|---|---|---|
| Too small | Micro-chunks pollute search results | LLM lacks context to classify correctly |
| Too big | Semantic blur, wrong chunks match | LLM may miss entities or conflate facts |
| Sweet spot | Self-sufficient for answering a question | Self-sufficient for entity/fact extraction |
| Failure mode | Wrong chunk retrieved | Wrong entity identified or fact misclassified |

**For extraction, I'd argue the chunk should be larger than for retrieval.** The LLM extracting facts benefits from seeing a full section — the heading gives entity/topic context, the body gives the facts, adjacent paragraphs give disambiguation. A `geography` fact about Mirathorn is easier to extract if the LLM sees the heading "Location" plus the paragraph, rather than just the paragraph alone.

The heading-bounded section is probably the right unit for extraction — one heading section with its content becomes one evidence unit, and the LLM processes it with the section_path as context. That maps closely to how I authored the facts: each evidence unit was a heading section from the Mirathorn doc.

**But there's a second question you're raising** — eventually this projected canon needs to be *retrievable* by an agent during a session. When the agent needs to answer "what do I know about the Shepherd's Flock?", it needs to find the relevant facts. At that point the RulesIngestion findings apply directly: the projected facts need to be indexed in a way that supports retrieval without micro-chunk pollution.

So there may be two chunk granularities at play:
1. **Ingestion chunks** (larger, heading-bounded sections) — input to the extraction LLM
2. **Retrieval chunks** (the projected facts themselves, or merged fact groups) — indexed for agent queries at runtime

The fact schema already gives you a natural retrieval unit: one fact is one searchable assertion with its label, attribute, and provenance. That's denser and more self-contained than a raw text chunk — closer to the "clause family" projection that the combined learnings report hypothesized as the next frontier.

What's your read on this two-granularity distinction?

---

**User**

Yes agreed. 
Ingestion chunks will be the ingested canon, it really only needs to be a light record. Retrieval chunks are what is queried over.  

---

**Cursor**

That's clean. The ingestion chunk is the evidence unit — a light record of what was said where, preserving provenance. It's the receipt, not the product. The retrieval chunks are the projected facts — the structured, attributed, layer-tagged assertions that an agent actually queries over.

The evidence unit exists so you can always trace *why* a fact exists. The fact exists so the agent can find and use it. Two different jobs, two different granularities, linked by `evidence_ids`.

Let me capture this in the design doc.

I can see you've already expanded the doc significantly with the two-pass extraction architecture and the entity extraction findings. Let me add the two-granularity distinction.

Now let me also tighten up the "Applicable Knowledge from RulesIngestion" section since we now have specific findings to reference rather than just vague pointers.

Done. The design doc now captures the two-granularity model: evidence units are light ingestion records for provenance, projected facts are the retrieval surface the agent queries over. The RulesIngestion findings are referenced concretely — not just "we learned stuff about chunking" but the specific failure modes (micro-chunk pollution, compositional retrieval gaps) and why the fact-as-retrieval-unit architecture avoids them.

---

**User**

Tell me a story of this being used, what does this vertical slice look like? 

---

**Cursor**

Let me tell you the story of running a session with this system.

---

**Friday afternoon. You're prepping for tomorrow's game.**

You open DungeonMind and drop in your Mirathorn doc — the one you've been building for months. It's markdown with a frontmatter tag: `canon_layer: world`. The system ingests it, extracts entities (Mirathorn, Shepherd's Flock, Commander Thalia Ashenvale, Torrin Flamescale, the Festival of Expansion, Lake Mirathorn, Stormspire Peaks — everything named), and pulls out facts about each one. Geography, defenses, demographics, goals, NPCs with their roles and stances. All tagged `truth_state: CANON`, all traceable back to the paragraph they came from.

You also drop in your campaign notes — the narrative ledger from the last few sessions. Frontmatter: `canon_layer: campaign`, `campaign_id: longmont_01`. The system ingests those too. Facts about what the party has done, who they've talked to, what they've learned. These layer on top of the world canon but can never overwrite it. Mirathorn's founding history stays the same whether or not the players burned down the gate.

You ask the agent: **"Catch me up on Mirathorn. What do I need to know going into tomorrow?"**

The agent queries the projected facts. It sees world canon: the city, its geography, defenses, the festival, the toll, the Shepherd's Flock protest. It sees campaign facts: the party arrived last session, they talked to the protesters, they're suspicious of the guard captain. It writes you a briefing:

> *Mirathorn sits at the base of the Stormspire Peaks on the shore of Lake Mirathorn — a trade hub of about 7,000 residents, currently swelling with visitors for the Festival of Expansion. The ancient walls are more symbolic than defensive these days, ivy-covered and aging, though the iron-reinforced gates are still imposing.*
>
> *The party arrived last session through the congested main gates, where the Shepherd's Flock was staging a loud protest against the steep entry toll. They spoke with one of the protest leaders and came away thinking the cult has a point about the toll but sensing something darker underneath. They also noticed Commander Ashenvale seemed dismissive of concerns about guard corruption — which tracks with her being ensorcelled, though they don't know that yet.*

You read it and nod. That's right. That's where we are.

---

**Now you plan.**

You open a planning doc. Frontmatter: `canon_layer: campaign`, `source_class: planning_document`. You write:

> The Shepherd's Flock protest will escalate into a riot at the gates tonight. The cult leaders have planted agitators in the crowd. During the chaos, a cult cell will attempt to poison the water supply at Lake Mirathorn. Commander Ashenvale will refuse to investigate the guard, and the party will need to go around her — either to Tinkerbright at the Wizard's College or to Torrin at the Guilds.

The system ingests this. These facts come in as `truth_state: PREP` — they're your intent, not yet canon. The projection now shows three kinds of information:

- World canon (immutable truth about the setting)
- Campaign history (what's happened in play)
- Planning overlay (what you're setting up)

You ask the agent: **"Given my plan, what NPCs should I have ready for tomorrow? What do they want?"**

The agent sees your planning facts layered over the canon. It knows the Shepherd's Flock is escalating. It knows Thalia is ensorcelled. It knows Tinkerbright is troubled by dark magic and eager to help. It knows Torrin cares about city defense. It writes:

> *You'll likely need these NPCs ready:*
>
> *— **Commander Thalia Ashenvale**: She'll stonewall. She's ensorcelled to overlook guard corruption, so she'll be defensive about accusations. Have her dismissive but not cartoonishly so — she genuinely believes the guard is clean.*
>
> *— **Archmagister Tinkerbright**: He's your players' likely ally if they go around Ashenvale. He views the corrupted meat as a perversion of magic and will offer Wizard's College resources. Play up the eccentric-but-serious angle.*
>
> *— **Torrin Flamescale**: If the players frame the water poisoning as a threat to city defenses, Torrin will mobilize the guilds. He's blunt and practical — he won't care about politics, just protecting the city.*
>
> *— **Shepherd's Flock leaders**: You'll need at least one charismatic face for the protest-turned-riot. Consider whether the party's earlier conversation with a leader gives them a way to de-escalate or if that leader is in on the agitator plan.*

Every one of those NPC descriptions comes from facts in the projection. The agent didn't invent Tinkerbright's personality — it's in the world canon from the City Council section of your doc. It didn't guess that Torrin cares about defense — that's his canonical stance on the cult issue.

If you wonder where the agent got something, you click through. The provenance chain shows: this claim came from fact `fact_thalia_mental_001`, sourced from evidence unit `evid_council_thalia_001`, which is paragraph 112 of "The City of Mirathorn.docx" under the "City Council > Commander Thalia Ashenvale" section. You can read the original text and decide if the agent got it right.

---

**Saturday. The session.**

The party does something you didn't plan for. They don't go to Tinkerbright or Torrin. They go straight to the Shepherd's Flock protest and try to infiltrate the cult. They succeed. They learn about the water poisoning plan from inside.

After the session, you write a session recap. Frontmatter: `canon_layer: campaign`, `source_class: observed_session_recap`. These are play-layer facts — `truth_state: OBSERVED`. What actually happened:

> The party infiltrated the Shepherd's Flock. Kael passed himself off as a disgruntled merchant. They learned the water poisoning is planned for the night of the festival's closing ceremony. The cult cell leader is someone called "Brother Ashwood" — not previously known. The party did NOT confront Ashenvale. The riot at the gates happened but the party was inside the cult camp when it did, so they experienced it as distant chaos.

The system ingests this. The projection updates:

- World canon: unchanged. Mirathorn's geography, history, demographics — all the same.
- Campaign history: now includes the party's infiltration, Brother Ashwood as a new entity, the water poisoning timeline.
- Planning: some of your prep is now superseded. The party didn't go to Tinkerbright, so that thread is still open but unactivated. The riot happened, so that planning fact transitions to observed.

Next week, when you ask the agent to catch you up again, it knows all three layers. It knows what the world is, what you planned, what actually happened, and — critically — where they diverged.

---

**That's the vertical slice.** The system is a memory that respects the difference between "what's true about the world," "what I'm planning," and "what happened." The agent writes prose from it. You exercise judgment over that prose. And when you need to know why the agent said something, the provenance chain is right there.

---

**User**

It would be successful if we could build this such that from a command line chat loop, the core loop would work, if it works there we can wire it up to the frontend for fun.  

---

**Cursor**

That's the right success criteria. If it works in a CLI chat loop — ingest a doc, ask a question, get a grounded answer, add planning, ask again, record play, ask again — the core loop is proven. Everything else is UI.

Let me update the design doc to make this the concrete target.

That's the target. A terminal where you can ingest, ask, plan, play, and trace provenance. Five commands that exercise every layer and every link in the chain. If that works, everything else is presentation.

---

**User**

We need some blind AB tests. 
I'm thinking for validation we can have baseline on the known docs. 
Then this is a series of A locations/events/docs to ingest. 
There is B which are not touched during development, with benchmarks. 

We have the corpus, it's my corpus so we can do whatever we want with it. 

---

**Cursor**

That's the right eval design. Let me look at what's actually in the corpus so we can propose a concrete partition.

This is a rich corpus. Here's a concrete partition:

**Set A — Development (touched during pipeline building):**

| Doc | Why it's in A |
|---|---|
| `The City of Mirathorn.docx` | Already used for Step 1 gold fixtures |
| `The City Council.docx` | NPCs referenced in existing Mirathorn facts |
| `Longmont Campaign General Notes.docx` | Locked as Milestone 1 campaign source |
| `lieutenant_lysandra_ironveil_character_dossier.md` | Already used in existing 6 scenarios |

You tune prompts, debug edge cases, and build gold artifacts against these. They're your training set.

**Set B — Blind (never touched during development):**

| Doc | Why it's good for blind eval |
|---|---|
| **Mossford Gazetteer + 12 location dossiers** | Complete separate city. Same structure as Mirathorn (location with sub-locations). Tests whether the pipeline generalizes to a different place. 12 sub-docs (Copper Moss Brewery, Temple of the Nameless Stone, Watch Tower, etc.) test entity-linking across related docs. |
| **The cult of the Great Shepherd.docx** | Faction doc. Tests faction entity extraction + goals/methods attributes. Also tests cross-entity links to Mirathorn entities (Ashenvale, corrupted guards). |
| **Festival of Expansion event docs** | Event-type content. Tests whether event entity extraction works, schedule/mechanics extraction, NPC participants across scenes. |
| **Stonebridge and The Wizard Tower Brewing Co.docx** | Another location. Tests generalization beyond cities. |
| **Campaign 2 Session Recaps / Narrative Ledger** | Campaign-layer content (not world). Tests whether ingestion correctly handles campaign-tagged material and produces `truth_state: OBSERVED` facts. |

**Why Mossford is the ideal blind anchor:** It's a full town with a gazetteer and 12 location dossiers you've never used in development. If the pipeline can ingest the Mossford gazetteer and produce a projection that you'd read and agree with — without ever having tuned against it — that's real generalization evidence.

**The benchmark protocol:**

1. Build the pipeline against Set A (Mirathorn). Tune prompts, fix edge cases, get entity recall and fact quality where you want them.
2. Freeze the pipeline. No more changes.
3. Run it on Set B (Mossford gazetteer + cult doc + festival docs).
4. You evaluate the blind output: entity recall (did it find everything named?), fact accuracy (are the labels faithful to the source?), attribute classification (did geography go to geography?).
5. Any failure in Set B that you fix requires re-running Set B to confirm the fix didn't just overfit to the new case.

Want me to add this to the design doc?

---

**User**

Yes add it to the design doc

---

**Cursor**

Added. The design doc now has the full A/B split with the specific documents in each set, why Mossford is the blind anchor, and the five-step benchmark protocol.

---

**User**

Pick up at starting a fresh agent, reflecting on the plan with a handoff and the design doc.  

---

**Cursor**

Good, I have the full design doc. Now let me commit the latest changes and write the handoff.

Now the handoff for the next agent.

Done. The next agent gets:

1. **`DESIGN-layered-canon-vertical-slice.md`** — read-the-whole-thing canonical design doc with all architecture decisions, the CLI loop target, two-granularity model, blind A/B eval split
2. **`HANDOFF-step2-planning-layer.md`** — specific execution instructions for Step 2: author planning facts, run two projections, verify the layer boundary holds, check for conflicts and new entities

The handoff tells them what to read first, what's done, what to do, what to watch for, and what not to revisit. Step 2 is scoped to 1–2 hours of fixture authoring and one reducer run.

---

**User**

Step 2 complete — the planning layer boundary holds.

What was done
3 planning-layer evidence units added to evidence_units.json — GM session prep notes for the longmont_01 campaign:

Shepherd's Flock protest escalating into a riot (diversion)
Merchant guild spy (Delara Windhaven) planted inside the city guard
Brother Ashwood's water poisoning plot during the closing ceremony
3 planning-layer facts added to facts.json with truth_state: "PREP", source_authority: "planning_prep":

Shepherd's Flock operational_status → riot_escalation (deliberately conflicts with world canon's active_protest)
Brother Ashwood role → cult cell leader (new entity, doesn't exist in world canon)
Brother Ashwood goals → water supply poisoning (interpretive, strong assertion)
run_step2.py created — runs two projections and verifies five gate checks.

Gate results (all passed)
World projection identical to Step 1 output — adding campaign evidence/facts did not mutate world canon
Campaign projection includes all world canon entities — Mirathorn and Shepherd's Flock carry through
Conflict detected — auto_conflict_001 on ent_shepherds_flock / operational_status between fact_shepherds_flock_status_001 (world: active protest) and fact_shepherds_flock_status_planning_001 (campaign: riot escalation). The planning fact wins by sort order in the campaign projection.
Brother Ashwood appears only in campaign projection — new entity properly isolated to the campaign layer
World projection has zero conflicts — clean baseline
Verification
18/18 existing tests pass
ruff check . clean
11 evidence units and 13 facts all validate against schemas

---

**Cursor**

Let me read the current state of the design doc and the key artifacts to reflect on where we are and what's next.

Let me also look at the current facts and evidence to see the full picture.

Good results. Steps 1 and 2 together have proven the two hardest things about the layered model:

1. **Layer isolation is real.** Adding campaign-scoped evidence and facts does not corrupt the world projection. The same reducer, same inputs, same code — `campaign_id=None` returns an identical result before and after planning facts exist. That's the core invariant, and it holds.

2. **Conflict detection is automatic.** You didn't manually declare the Shepherd's Flock `operational_status` conflict — the reducer derived it from the fact that two distinct values exist for the same entity+attribute. The planning fact wins in the campaign projection by sort order, but the world fact remains authoritative in the world projection. This is the mechanism by which the GM's plans can *overlay* truth without *destroying* it.

3. **Entity scoping works.** Brother Ashwood doesn't exist in world canon. He appears only when you ask for the campaign projection. If you ran a different campaign against the same world, he wouldn't be there. This is what makes the model multi-campaign-safe.

---

**What's next is Step 3: Prove Play Updates Don't Corrupt Lower Layers.**

Looking at the reducer, this is actually set up to work already. `ACTIVE_TRUTH_STATES` includes `OBSERVED`, and the `_fact_sort_key` function uses `asserted_in_session` and `sequence_index_within_session` to pick the latest fact when there are conflicts. So play-layer facts with a higher session number should naturally supersede PREP facts.

The interesting test is what happens when play *diverges* from the plan. For example:

- PREP says Brother Ashwood will poison the water supply
- But in play, the party stops him — so the OBSERVED fact is that his plot was foiled

The projection should show the OBSERVED outcome, not the PREP plan. And if the GM later asks "what did I plan vs. what happened?" the system should be able to show both, because both facts exist — the projection just picks the latest one.

Here's what Step 3 would look like concretely:

1. **Author 1-2 play-layer evidence units** — session recap entries with `canon_layer: "campaign"`, `campaign_id: "longmont_01"`, `source_class: "observed_session_recap"`. Something like: "The party infiltrated the Festival closing ceremony. They discovered Brother Ashwood near the main cistern and stopped the poisoning. The riot at the gates was quelled by the city guard with the party's intelligence."

2. **Author 1-2 play-layer facts** with `truth_state: "OBSERVED"`, `asserted_in_session: 5`, `sequence_index_within_session: 1`. These should directly conflict with the PREP facts — e.g., Brother Ashwood's `goals` becomes "plot foiled by party intervention" rather than "will poison the water supply."

3. **Create `run_step3.py`** that runs three projections:
   - World: `campaign_id=None` — unchanged from Steps 1 and 2
   - Campaign (all layers): `campaign_id="longmont_01"` — should now show OBSERVED facts winning over PREP facts
   - And renders a comparison showing PREP vs. OBSERVED for the same entity+attribute

4. **Gate:** World projection unchanged. Campaign projection shows OBSERVED facts superseding PREP. The provenance chain shows all three layers. Canon remains intact.

The key thing this tests that Steps 1-2 didn't: **temporal ordering within a campaign layer.** The `asserted_in_session` field has been null for everything so far. Step 3 is the first time it matters.

Want to proceed with Step 3?

---

**User**

I think in play he doesn't exist. 
Here is the actual play that happened 
Session 6 : The Road to Miraholm

Major Beats:
Negotiated Torbin’s ward contract
Shopped with Saladin, sold stuff
Bought standard goods from Morwin
Traveled with Saladin
Ephanna summons a sprite, no one but Torbin knows
Bonogo woke up and saw a ghost child, woke up Karsemine
Runaway horses, Ephana kills one
Baergrom stops the cart
Stafl? Talks the group out of Ephanna horse killing trouble
Find Pippa and Bubbles
Shopping, meet Elara Swiftwind at the Fur place
Go to the gate, see the beginning of the protest
Talked to Captain Lysandra Ironveil

Next Beats : The protest and then whatever direction they move in? They need to get Torbin somewhere safe.  

Looking Ahead :Splash in some politics, they need a hint to know about the meat. They made friends with Lysandra, Kaelyn was very into talking with them. 


Recap : We last left the group of 6 having a sidebar to discuss if they were really taking on this kid Torbin as a ward, or clerk, or slave or something. To which the decision was obviously, Hempholm was no place for a kid with ambition, and hey we’ve got money, lets change a life. Maybe, make that life our liaison in the city, or a student or something. Whatever, details aside a contract was negotiated. In exchange for an education, staying alive, monthly visits for his pops, and guaranteed room and board they had a kiddo. 

Next up had to be shopping, first to the garish wagon in the center of Hempholm! Saladin’s Emporium, which had jack fucking shit. It was huge inside, like a grocery store of empty shelves. About the only thing there was a flamboyantly dressed elf’s desk with a weird bleeding statue, “It’s paint, it’s a total fake” - Caelynn, a really old weird elf who would buy anything, and some dubious ‘knowledge’ for a steep price. Not a bad sort, but not the emporium they were looking for. So they went to Morwin’s which had a bitchy old man, who wouldn’t shutup about how much he hated that Saladin. Until he sold the party a ton of goods. That was pretty satisfying.

On to Mirathorn, it’d be two days, made all the more interesting for traveling with Saladin and his weird magical or mechanical wagon with no horses. Not a lot happened on the way. During the watch, which no one fell asleep during, Bongo was visited by a ghost child walking the road. To confirm it wasn’t food he woke up Karsemine, who confirmed it was spectral. There was a runaway cart stopped by Baergrom. A dead horse served for Bonogo by Ephanna. An escalation turned friendly with the dead horse’s owner by Stafl (I think), and some pre festivities with an epic performance by Stafl, spreading the song of the party to all who would listen. Even Bonogo was moved to play along!

Approaching Mirathorn they passed the abundance of the outskirts of Mirathron, a giant waterwheel visible from miles away against the mountain, the domineering walls around the city. Herd of float goats, Starling Cows, Luminox Sheep, Orchards and fields. Finally arriving at Outtown, the collection of shops, blacksmiths, breweries, tents, and temporary buildings erupting out of the city in preparation for the Festival of Expansion. Among them The Wizard Tower Brewery, Pippa and most importantly Bubbles! After drinking, catching up, telling their tales, it was time for a bit of exploration, shopping and then to see about getting into the city and this ‘toll’ they heard folk grumbling about. 

Torbin, immediately spend all 10 of his gold (which is a lot of fucking money for a kid, like, his father’s life savings) on candy. So much candy! After exploring a few shops, they decide it’s time to head into the city. Which is where they find a group gathering, passing out fliers chanting about how unfair the toll is. While they observe and chat with Captain Lysandra Ironveil, the crowd grows to around 50 people. The guards looking tense send a large contingent of troops out to disperse the crowd. Excusing herself, the Captain walks to joining the other guards, complaining of what a headache and ass chewing she will get if she has to close the gate.


Well shit, that could be a real blocker to getting Torbin inside and settled…

Session 7 : Passing Mirathorn Gates

Major Beats:



Next Beats : 

Looking Ahead :


Recap : 


We find our heroes between guards and a large crowd attempting to start a riot over the toll to enter the gates. Stafl (going by Tans while in the city) attempts to calm the crowd, however the crowd is already too loud to hear him.

Meanwhile, Ephanna has joined the crowd and joined in the chants (because of a high performance roll). Stafl then casts Suggestion on the leader of the crowd. Bonogo attempts to roar to get the crowd's attention, but also fails to get any notice.

Caelynn then gives a try (rolling 17 performance) and tells the crowd that we will talk to the Council about the fee if they settle down. Ephanna, again working with the crowd, encourages the crowd to go to the Council themselves!

Because of Caelynn the crowd opens and we are able to approach the Captain. The Captain is much happier with Caelynn's help and allows us to cut the line to enter the city gates, after paying the toll of course.

Lyra, the leader of the crowd, and her followers leave to go back to their base and Ephanna decides to take Torbin and go along with them, wanting to help with their plans. Ephanna discovers that the group is called The Shepherds Flock. Each is wearing a symbol of their group and there is talk of their leader, The Shepherd, back in the Swamp to the north.

Upon entering the gate each member must choose a magical ribbon for the celebration.  Black and Gold representing the Empire or Burgundy and Teal representing the City. Stafl (Tans) chooses Black and Gold, Caelynn chooses Burgundy and Teal, Bonogo chooses solid black, Karsemine chooses Burgundy and Teal, and Baergrom chooses Black and Gold.

As we enter the gate we see streets lined with vendors and an old guard tower in the back. Down the street is the Copper and Quartz Inn, no vacancy. Far to the back we see Steampunk architecture and rings of streets to other districts. With a few hours left before sundown we decide to look around at the shops and festivities.

Bonogo is immediately drawn to a carnival game where he has a chance to win a toy airship. With the confidence and swagger only a Rogue would have, he walked right up and paid his silver to play. And had terrible luck. So he played again, same outcome. Finally, with some focus and skill, he hits all targets and wins his new prized possession.

Meanwhile, Caelynn and Baergrom enter the herbal shop and are met with the overwhelming scent of herbs. Elara Greenleaf, an Elf Druid, greets the new visitors. The first question she asks is if Caelynn is elvish. She then yells to the back and Talia, a half-elf, comes out to help as well. Despite a shop full of herbs, Caelynn is most interested in finding out information about the glowing mushrooms. She offers 1 pound in exchange for information and 2 gold for a copy of the information from the book. (A very cool mushroom card is given with details hidden under a scratch off area). They soon discover that the mushrooms are very rare and extremely dangerous. Caelynn will need to take the mushrooms to the Head Alchemist at Stormspire Academy to see about making them into a potion.

Our story jumps back to check in on Ephanna and we find him captured, in a cell, bound and gagged. It is dim in the cell but by the flickering of a torch Ephanna can see in there are three cages and on the end is someone standing over Torbin forcing him to eat some meat. What will he do next?

Back on the street of vendors Stafl has decided to see if he can refill his coin purse. Putting on an incredible performance (20+7 roll) a large crowd gathers, including the owner of the Inn, Berin Ironfoot. This dwarf clearly rubs elbows with the wealthy and could be just who our adventures need to speak with. Stafl uses all his charm and charisma to swing the heroes a fantastic suite at the Inn and even gets food included. But nothing in life is free. Stafl will need to perform for guests and there is a favor Berin has asked for.

Berin meets with Caelynn and Karsemine to tell them about the rebel group that has been stirring up trouble (the one from the toll protest). They are a group of humans that no longer feel represented in the city and want to cause as much trouble as possible. He agrees that the flier they passed out looks suspicious and not spontaneous for the protest. He has also heard rumors of the Shepherd, but doesn't know much more than that. His favor is to find out more about the rebel group and to stand out by the gates to dissuade any further trouble.

Finally, the epic Ephanna battle. Ephanna uses the fey familiar to loosen the bonds and he gets the attention of the guard. With weapons and gear taken, it's blasting time. He hits the guard for 8 damage, plus 14 more and melts him on the spot. Another guard rushes in and attacks Ephanna, but receives Hellish Rebuke for his effort, dealing 21 damage. With two rebels down things are looking good. Until 3 more rebels come down the stairs. Even with Fear and Torbin helping where he can (like locking one rebel in a cell) Ephanna is quickly overwhelmed and is knocked to 1 HP. Will this be the end of Ephanna? Or is there another trick up the sleeve of his Warlock robe. 



---

**Cursor**

This is gold. The real play diverged completely from the plan — Brother Ashwood never shows up, the party *defuses* the riot through diplomacy instead of it escalating, and Ephanna ends up captured inside the Flock's base discovering something much darker (the meat, the cells). That's exactly the kind of messy reality the system needs to handle.

The key insight you're pointing to: Brother Ashwood is a PREP-only entity. No OBSERVED facts override him. He stays in the campaign projection as "a plan the GM made" — which is correct, because you might still use him later, or he might just be a discarded thread. The system shouldn't erase him, but it also shouldn't confuse him with what actually happened.

Let me check the schemas and then author the play-layer content from these real session recaps.

Let me check the valid enum values in the common schema.

Let me check the temporal fields definition to understand `asserted_in_session` properly.

All schema values line up. Let me implement Step 3 with your real session content.

Now let me create the Step 3 runner.

Now let me run it.

All 7 gates passed. Let me verify existing tests and linting are clean.

Step 3 is complete. All 7 gates passed, 18/18 tests pass, ruff clean. Here's what the output proves:

**The three-layer model works with real campaign content.**

Look at the Shepherd's Flock `operational_status` in the campaign projection — it's the most interesting attribute in the system now. Three facts compete for it:

| Fact | Truth State | Value |
|---|---|---|
| `fact_shepherds_flock_status_001` | CANON | Active protest at gates, pamphlets, tense guards |
| `fact_shepherds_flock_status_planning_001` | PREP | Riot escalation during closing ceremony |
| `fact_shepherds_flock_status_observed_001` | OBSERVED | Protest dispersed by party diplomacy; covert base with cells |

The OBSERVED fact wins (session 7 sorts after session 0), and the provenance chain shows exactly why — citing the Session 7 recap, the Session 5 prep notes, and the original Mirathorn doc. An agent reading this projection knows what *was planned*, what *actually happened*, and what the *baseline truth* is.

**Brother Ashwood stays as PREP-only.** He's in the campaign projection with both his facts (`role`, `goals`) still marked `truth_state=PREP`. The system didn't erase him — he's still a plan the GM made. Maybe he surfaces in Session 8, maybe he doesn't. The projection correctly preserves that ambiguity.

**The Shepherd appears as a play-discovered entity.** He didn't exist in world canon or in planning — the party found out about him through Ephanna's infiltration. He appears only in the campaign projection with `truth_state=OBSERVED`. If you later write a world canon doc about The Shepherd (as a known figure in the Swamp), that would add a world-layer fact that enriches the graph without touching the campaign observations.

**World canon remains untouched.** Identical to Step 1 output. Zero conflicts. No play or planning content leaked through.

Steps 1-3 are complete. The layered model's core invariants hold with real content from your campaign. The next move per the design doc is Step 4: ingestion automation — building the pipeline that does what we just did by hand (extract entities, extract facts, classify layers) via LLM.

---

**User**

Lets look at the corpus we will be using for automation

---

**Cursor**

That's only a few files. Let me search more broadly for the corpus.

Let me read a couple of the key documents to understand the content shapes — especially the Mossford gazetteer (blind set anchor) and the Shepherd's Flock doc.

Here's the full picture of your corpus. It's substantial — **110 text documents** (106 `.docx` + 4 `.md`), organized into a natural hierarchy that maps cleanly to the ingestion pipeline.

---

**The corpus has three major domains:**

### 1. World Canon — Elderwyld (the setting)

**Cities & Towns:**

| Location | Documents | Content Type |
|---|---|---|
| **Mirathorn** | `The City of Mirathorn.docx` + 16 sub-docs | City overview, council, sewers (7 rooms), Stormspire Academy (3 docs), Wolf Manor (2 docs), shops |
| **Mossford** | `Mossford_Map_Key_and_Gazetteer.docx` + 12 location dossiers | Full town gazetteer + Watch Tower, Temple of the Nameless Stone, Stoneweir Dam, Copper Moss Brewery, Market Square, Town Hall, Moldyards, Mossford Inn, Dense Worker Housing, Stone Bridge, Drying Barns, Southern Road |
| **Hempholm** | (empty directory) | Referenced in play but no dedicated doc yet |
| **Stonebridge** | `Stonebridge and The Wizard Tower Brewing Co.docx` | Town + brewery + NPCs (Grishna, Glowkindle, staff) |

**Factions:**
- `The cult of the Great Shephard.docx` — full faction doc with origins, hierarchy (Great Shepherd → Seren Darkroot → Eirik "The Wolf" → Lyra → sleeper cells), influence in Mirathorn, current agenda, named NPC dossiers for 5+ cell members

**Events:**
- `The Festival of Expansion.docx` + 10+ sub-docs — schedule, mechanics, combat contest (3 rounds), arcane contest, cultural ceremonies, costume emporium, skyship race, bake-off (5 docs), games table

**Other World Content:**
- `Migrating Forest/` — hex key, encounter table, expansion, Branchbound culture (4 docs)
- `Flora/` — Moonveil Oysters
- `Inns and Shops/` — The Copper & Quartz Inn
- `# Campaign Summary Mirathorn Post-Cultist Battle.docx`
- `The Stonebridge Flood.docx`
- `UnRefined Heading into the Flesh Kaiju.docx`

### 2. Campaign Content — Longmont Campaign

**Campaign 1:**
- `Longmont Campaign General Notes.docx`

**Campaign 2:**
- `Campaign 2 Notes.docx`
- `Campaign 2 Session Recaps.docx`
- `Elderwyld_Narrative_Ledger_Campaign2.md` — this is exceptional: 28+ active threads with status, linked NPCs, linked items, locations, and next hooks
- `Elderwyld_Narrative_Ledger_2.md`
- Session Prep: `Session 2 Prep.docx`, `Session 3 Prep.docx`, `session_20_stacey_stuart_marla_reference.md`
- NPC Dossier: `lieutenant_lysandra_ironveil_character_dossier.md`
- `The Wolf's Estate/` — scene doc

**Homebrew Items:** 10+ item docs + player copies
**Character Docs:** Ephanna Backstory
**NPCs:** Captain Lysandra Ironveil (PDF statblock), Torbin Jove (characteristics + statblock)

---

### Mapping to the A/B Split from the Design Doc

The design doc proposed:

**Set A (Development — tune against these):**

| Proposed | Actual File |
|---|---|
| `The City of Mirathorn.docx` | `Elderwyld/Cities and Towns/Mirathorn/The City of Mirathorn.docx` |
| `The City Council.docx` | `Elderwyld/Cities and Towns/Mirathorn/City Council Building/The City Council.docx` |
| `Longmont Campaign General Notes.docx` | `Longmont Campaign/Campaign 1/Longmont Campaign General Notes.docx` |
| `lieutenant_lysandra_ironveil_character_dossier.md` | `Longmont Campaign/Campaign 2/NPC Dossier/lieutenant_lysandra_ironveil_character_dossier.md` |

**Set B (Blind — evaluate generalization):**

| Proposed | Actual File |
|---|---|
| Mossford Gazetteer + 12 location dossiers | `Elderwyld/Cities and Towns/Mossford/` — **13 docs total, all present** |
| The cult of the Great Shepherd.docx | `Elderwyld/Shephards Flock/The cult of the Great Shephard.docx` |
| Festival of Expansion event docs | `Elderwyld/Events/The Festival of Expansion/` — **10+ docs** |
| Stonebridge and The Wizard Tower Brewing Co.docx | `Elderwyld/Stonebridge and The Wizard Tower Brewing Co.docx` |
| Campaign 2 Session Recaps / Narrative Ledger | `Campaign 2/Campaign 2 Session Recaps.docx` + both narrative ledgers |

---

### Observations for Ingestion Automation

1. **Format is almost entirely `.docx`.** The pipeline needs `python-docx` as the primary parser (already installed). The 4 `.md` files are trivially handled.

2. **Heading structure varies wildly.** The Mossford gazetteer uses `Normal` for everything — no heading styles, just numbered sections in the text. The Shepherd's Flock doc uses `Heading 3` and `Heading 4`. Stonebridge uses `Heading 2-4`. The Mossford location dossiers use `Title`, `Heading 1`, `Heading 2` properly. The chunking strategy can't rely solely on `docx` heading styles — it needs to detect section boundaries from text patterns too (numbered sections like "1. Watch Tower", bold text, etc.).

3. **The Mossford gazetteer is an ideal blind test.** It's structurally similar to Mirathorn (city overview with sub-locations) but different content. The 12 location dossiers test cross-document entity linking — entities mentioned in the gazetteer should connect to the same entities that have their own dedicated dossier documents.

4. **The Narrative Ledger is a fascinating test case.** It's a structured campaign document with 28+ threads, each with status, linked NPCs, linked items, locations, and next hooks. This is campaign-layer content (`truth_state: OBSERVED` or `PREP` depending on whether it's recording what happened or proposing what's next). The "Next Hook" fields are planning-layer facts. This single document would generate a massive number of entity cross-references.

5. **The Shepherd's Flock doc reveals information the play layer only partially discovered.** The party learned about "The Shepherd, back in the Swamp to the north." The world canon doc reveals that The Shepherd is Seren Darkroot, the Great Shepherd is a dead god, the meat is corrupted divine flesh, and the ultimate goal is summoning a flesh kaiju. That's a perfect test of layer isolation — the world canon knows things the campaign's observed play hasn't uncovered yet.

6. **No frontmatter on any documents.** The design doc specifies GMs will add `canon_layer` and `source_class` frontmatter. For existing docs, the ingestion pipeline either needs to infer layer from directory structure (`Elderwyld/` → world canon, `Longmont Campaign/` → campaign) or require the GM to tag them during ingestion.

---

**User**

Design this experiment and explicitly lay out what needs to be contructed and put into place, IE the actual agent loop or loops 

---

**Cursor**

Let me re-read the design doc and the reducer one more time to make sure the design is grounded in what exists.

Here's the complete construction plan. This is everything that needs to be built, in what order, with the actual agent prompt shapes.

---

## What Exists

| Component | Status |
|---|---|
| v0.1 JSON schemas (evidence_unit, fact, entity, conflict, canon_decision, common) | Done |
| Schema validation (`src/contracts/schema_validation.py`) | Done |
| Canon projection reducer (`src/reducer/canon_projection.py`) | Done |
| 18 golden scenario tests | Done |
| Steps 1-3 fixtures (14 evidence units, 16 facts) | Done |
| `python-docx` dependency | Done |

## What Needs To Be Built

Five new modules, one config, gold artifacts for Set A.

---

### Component 1: Fact Store (`src/store.py`)

Simplest possible persistence — JSON files on disk with load/append/save.

```python
class FactStore:
    def __init__(self, store_dir: Path):
        # store_dir contains: evidence_units.json, entities.json,
        # facts.json, conflicts.json, canon_decisions.json
    
    def load(self) -> None
    def save(self) -> None
    
    # Append operations (used by ingestion)
    def add_evidence_units(self, units: list[dict]) -> None
    def add_entities(self, entities: list[dict]) -> None
    def add_facts(self, facts: list[dict]) -> None
    
    # Query operations (used by ask/provenance)
    def get_entity_by_name(self, name: str) -> dict | None
    def get_facts_for_entity(self, entity_id: str) -> list[dict]
    def get_evidence_unit(self, evidence_id: str) -> dict | None
    def list_entities(self) -> list[dict]
    
    # Projection shortcut
    def project(self, campaign_id: str | None) -> dict:
        # Delegates to project_entity_state with current store contents
```

**Data lives in:** `~/.dungeonbuddy/stores/<store_name>/` or a `--store` CLI flag pointing to a directory.

**Entity deduplication:** When `add_entities` is called, check for existing entities where `display_name` or any alias matches (case-insensitive). If found, merge aliases and return the existing `entity_id` instead of creating a duplicate.

---

### Component 2: Docx Chunker (`src/chunker.py`)

Splits a `.docx` file into section-level evidence units.

```python
def chunk_document(
    docx_path: Path,
    document_id: str,
    document_title: str,
    canon_layer: str,       # "world" or "campaign"
    campaign_id: str | None,
    source_class: str,      # "seed_reference", "planning_document", etc.
) -> list[dict]:
    """Returns a list of evidence_unit dicts ready for schema validation."""
```

**Chunking strategy:**

The corpus has inconsistent heading styles. The chunker needs a two-tier approach:

1. **Try docx paragraph styles first** — if a paragraph has style `Heading 1`, `Heading 2`, `Heading 3`, or `Heading 4`, it's a section boundary. Build `section_path` from the heading hierarchy.

2. **Fallback: detect section patterns in text** — for docs like the Mossford gazetteer where everything is `Normal` style, detect numbered sections (`1. Watch Tower`, `2. Temple of the Nameless Stone`) or bold-text section headers. These become the section boundaries.

3. **Minimum chunk size:** If a heading section is under 50 characters, merge it with the next section (avoids micro-chunks).

4. **Maximum chunk size:** If a section exceeds ~3000 characters, it's fine — bigger is better for extraction context. Don't split large sections.

Each chunk becomes one evidence unit with `section_path` derived from the heading hierarchy.

---

### Component 3: Extraction Agents (`src/extraction.py`)

Two LLM agent calls per chunk. This is where the actual intelligence lives.

#### Pass 1 — Entity Extraction

**Input to LLM:**
```
System: You are an entity extraction agent for a TTRPG worldbuilding system.
Extract every named entity from the text below. Include:
- People (NPCs, historical figures, gods)
- Places (cities, landmarks, rivers, buildings, rooms)
- Factions (cults, guilds, councils, organizations)
- Items (named artifacts, specific objects)
- Events (festivals, battles, ceremonies)

Cast a WIDE net. If something has a proper name, extract it. 
A mention counts — even if the text says nothing else about it.

Here are entities already known to the system (reuse these IDs if you 
recognize the same entity):
{existing_entities_json}

For NEW entities, generate an entity_id as "ent_" + snake_case of 
the display name.

Respond with a JSON array of entity objects.
```

**Output schema (structured output):**
```json
[
  {
    "entity_id": "ent_mirathorn",
    "entity_type": "location",
    "display_name": "Mirathorn",
    "aliases": ["the city"],
    "is_new": false
  },
  {
    "entity_id": "ent_lake_mirathorn",
    "entity_type": "location",
    "display_name": "Lake Mirathorn",
    "aliases": [],
    "is_new": true
  }
]
```

**Model:** `fast_smart_mini` (gpt-5.4-mini) — this is NER + classification, doesn't need heavy reasoning.

**Per chunk:** One LLM call. All chunks in a document can be processed in parallel.

#### Pass 2 — Fact Extraction

**Input to LLM:**
```
System: You are a fact extraction agent for a TTRPG worldbuilding system.
For each entity mentioned in the text, extract what this text ASSERTS 
about it. Each fact is one attribute-value pair.

Entities found in this text:
{entities_json}

Attribute enum (use ONLY these):
species, role, rank_or_title, faction, current_location, 
physical_condition, mental_state, loyalty_or_alignment_context,
relationship_tags, operational_status, portrayal_notes, 
unresolved_questions, source_comments, history, geography, 
demographics, defenses, economy, governance, atmosphere, goals

Value kinds:
- "scalar": simple categorical (species, role, location)
- "state": current condition that changes over time (operational_status)
- "set": list of items (demographics races, relationship_tags)
- "interpretive": requires judgment, has strength + interpretation_level
  - interpretation_level: "direct_assertion" | "derived_summary" | "interpretive_inference"
  - strength: "strong" | "moderate" | "weak"

When a fact references another entity, use entity_ref in the value:
  { "kind": "scalar", "label": "Based in the Swamp to the north",
    "entity_refs": [{"entity_id": "ent_the_swamp", "role": "location"}] }

Generate fact_id as: "fact_{entity_id}_{attribute}_{sequence}"

Evidence unit ID for this chunk: {evidence_id}

Respond with a JSON array of fact objects.
```

**Output schema (structured output):**
```json
[
  {
    "fact_id": "fact_ent_mirathorn_geography_001",
    "subject_entity_id": "ent_mirathorn",
    "attribute": "geography",
    "value": {
      "kind": "scalar",
      "label": "At the base of the Stormspire Peaks, by Lake Mirathorn",
      "normalized": "stormspire_peaks_base:lake_mirathorn",
      "entity_refs": [
        {"entity_id": "ent_stormspire_peaks", "role": "landmark"},
        {"entity_id": "ent_lake_mirathorn", "role": "body_of_water"}
      ]
    }
  }
]
```

**Model:** `fast_smart` (gpt-5.3-codex) — interpretive work, needs to classify attributes correctly and write faithful labels. Could escalate to `retrieval_synthesis` if quality is poor.

**Per chunk:** One LLM call. Depends on Pass 1 completing first (needs entity list). All chunks can still be parallel if they share the same entity list.

#### Post-extraction processing

After both passes complete for all chunks:

1. **Deduplicate entities** against the store (case-insensitive name/alias matching)
2. **Assign truth_state** from metadata:
   - `canon_layer=world` + `source_class=seed_reference` → `truth_state=CANON`
   - `canon_layer=campaign` + `source_class=planning_document` → `truth_state=PREP`
   - `canon_layer=campaign` + `source_class=observed_session_recap` → `truth_state=OBSERVED`
3. **Assign source_authority** from source_class:
   - `seed_reference` → `seed_prep`
   - `planning_document` → `planning_prep`
   - `observed_session_recap` → `observed_recap`
4. **Validate** all outputs against JSON schemas
5. **Append** to store

---

### Component 4: Synthesis Agent (`src/synthesis.py`)

The `ask` command. Takes a projected entity state and a question, produces grounded prose.

**Input to LLM:**
```
System: You are a GM assistant for a TTRPG campaign. Answer the 
question using ONLY the facts provided in the projection below. 
Do not invent information beyond what is stated.

When citing facts, note the truth_state:
- CANON: established world truth
- PREP: GM's plan (hasn't happened yet in play)
- OBSERVED: what actually happened in play

If facts conflict, explain the conflict and which version is current.
Mention provenance sources when relevant.

Current projection:
{formatted_projection}

```

**Projection formatting** — the reducer output needs to be rendered into text the LLM can consume. Similar to what `run_step3.py` does but as plain text:

```
Entity: Shepherd's Flock (Faction)
  operational_status: Protest of ~50 people dispersed by party diplomacy...
    [OBSERVED, session 7, from: Session 7 Recap — Passing Mirathorn Gates]
    competing: CANON=active_protest, PREP=riot_escalation
  goals: Surface: toll abolition. Observed deeper activity: secret base...
    [OBSERVED, session 7]
  role: Cult staging protests against the city entry toll
    [CANON, from: The City of Mirathorn]

Entity: Brother Ashwood (NPC)
  role: Shepherd's Flock cell leader [PREP, from: GM session 5 prep]
  goals: Water supply poisoning [PREP, from: GM session 5 prep]
```

**Model:** `retrieval_synthesis` (gpt-5.3-chat-latest) — this is grounded response synthesis, exactly the role this model is tuned for.

---

### Component 5: CLI Loop (`src/cli.py`)

```
$ uv run python -m dungeonbuddy --store ./my_campaign

dungeonbuddy> ingest "path/to/doc.docx" --layer world
dungeonbuddy> ingest "path/to/doc.docx" --layer campaign --campaign longmont_01
dungeonbuddy> ask "What do I need to know about Mirathorn?"
dungeonbuddy> ask "What do I need to know about Mirathorn?" --campaign longmont_01
dungeonbuddy> plan "The protest will escalate into a riot" --campaign longmont_01
dungeonbuddy> play "The party stopped the riot" --campaign longmont_01 --session 7
dungeonbuddy> provenance "Brother Ashwood"
dungeonbuddy> entities
dungeonbuddy> projection --campaign longmont_01
```

**Command implementations:**

| Command | What it does |
|---|---|
| `ingest <path> --layer <world\|campaign> [--campaign <id>]` | Chunk docx → Pass 1 → Pass 2 → store |
| `ask <question> [--campaign <id>]` | Project → format context → LLM synthesis → print prose |
| `plan <text> --campaign <id>` | Create evidence unit from text (source_class=planning_document) → Pass 1 → Pass 2 → store with truth_state=PREP |
| `play <text> --campaign <id> --session <n>` | Same as plan but source_class=observed_session_recap, truth_state=OBSERVED, asserted_in_session=n |
| `provenance <entity_name>` | Find entity → list all facts → for each fact, trace evidence_ids → print chain |
| `entities` | List all entities in store with fact counts |
| `projection [--campaign <id>]` | Run reducer, print formatted projection (debugging) |

**`plan` and `play` are the same pipeline as `ingest`**, just with:
- Inline text instead of a docx file (the text becomes one evidence unit)
- Different metadata defaults (truth_state, source_class, source_authority)
- For `play`: `asserted_in_session` is set

---

### Component 6: OpenAI Client Config

```python
# src/llm.py
import openai

def get_client() -> openai.OpenAI:
    """Returns configured OpenAI client. Reads OPENAI_API_KEY from env."""
    return openai.OpenAI()

def extract_entities(text: str, existing_entities: list[dict], model: str) -> list[dict]:
    """Pass 1: entity extraction with structured output."""

def extract_facts(
    text: str, entities: list[dict], evidence_id: str, model: str
) -> list[dict]:
    """Pass 2: fact extraction with structured output."""

def synthesize_answer(projection_text: str, question: str, model: str) -> str:
    """Ask: grounded prose from projection."""
```

**Dependency to add:** `openai>=1.0.0`

---

### Gold Artifacts for Set A

Before running the automated pipeline, hand-author gold expected outputs for the development docs:

**For `The City of Mirathorn.docx`:**
- **Gold entity list** (recall target): Mirathorn, Lake Mirathorn, Stormspire Peaks, Lundayell Empire, Festival of Expansion, Shepherd's Flock, Wizard's Tower Brewing Co., and every NPC in the City Council section. This already partially exists as the Step 1 fixtures.
- **Gold fact set** (precision target): The 10 facts from Step 1 + additional facts for entities that were originally skipped.

**For `The City Council.docx`:**
- **Gold entity list**: Every council member, the council as a faction, The Wolf, referenced locations.
- **Gold fact set**: Role/rank_or_title for each council member, governance facts for Mirathorn.

**For `lieutenant_lysandra_ironveil_character_dossier.md`:**
- Already has 6 golden scenario tests. Extend with gold entity list and gold fact set.

---

### Build Order

Each phase is independently testable. Don't move to the next until the current one passes its gate.

**Phase A: Infrastructure (no LLM)**
1. `src/store.py` — fact store with load/save/append/query
2. `src/chunker.py` — docx section splitter
3. Tests for both: store round-trips, chunker produces valid evidence units from Mirathorn.docx
4. **Gate:** `chunker.py` produces evidence units from `The City of Mirathorn.docx` that are structurally similar to the 8 hand-authored ones in Step 1.

**Phase B: Entity Extraction (first LLM call)**
1. Add `openai` dependency
2. `src/extraction.py` — Pass 1 entity extraction
3. Run Pass 1 on Mirathorn.docx chunks
4. Compare output to gold entity list
5. **Gate:** Entity recall ≥90% against gold list. No major named entity missed.

**Phase C: Fact Extraction (second LLM call)**
1. `src/extraction.py` — Pass 2 fact extraction
2. Run Pass 2 on Mirathorn.docx chunks using Pass 1 entity list
3. Feed extracted facts through the existing reducer
4. Compare projection to Step 1 hand-authored projection
5. **Gate:** Automated projection covers the same ground as the hand-authored one. Attribute classification is reasonable. No hallucinated facts.

**Phase D: Synthesis Agent (third LLM call)**
1. `src/synthesis.py` — projection-to-prose
2. `src/cli.py` — wire up `ingest` and `ask` commands
3. Ingest Mirathorn.docx, then `ask "Catch me up on Mirathorn"`
4. **Gate:** Response is grounded in projection, doesn't hallucinate, cites correct layers.

**Phase E: Plan/Play + Provenance**
1. Wire up `plan`, `play`, `provenance` commands
2. Test the full loop from the design doc's CLI example
3. **Gate:** The full loop works end-to-end on Set A docs.

**Phase F: Blind Evaluation**
1. Freeze the pipeline
2. Run on Set B (Mossford gazetteer + location dossiers)
3. GM evaluates entity recall, fact accuracy, attribute classification, cross-doc linking
4. Document results

---

### Files to Create

```
src/
  store.py                    # Phase A
  chunker.py                  # Phase A
  extraction.py               # Phase B + C
  synthesis.py                # Phase D
  llm.py                      # Phase B (OpenAI client + model config)
  cli.py                      # Phase D + E

tests/
  test_store.py               # Phase A
  test_chunker.py             # Phase A

evals/
  mirathorn_vertical_slice/
    gold/
      gold_entities.json      # Phase B (hand-authored recall target)
      gold_facts.json         # Phase C (hand-authored precision target)
    eval_entity_recall.py     # Phase B
    eval_fact_quality.py       # Phase C
```

---

### Estimated Effort

| Phase | Work | Hours |
|---|---|---|
| A: Store + Chunker | Straightforward code, no LLM | 2-3 |
| B: Entity Extraction | Prompt engineering + eval | 2-3 |
| C: Fact Extraction | Prompt engineering + eval, most iterative | 3-4 |
| D: Synthesis + CLI | Wiring, less iteration | 2-3 |
| E: Plan/Play/Provenance | Extensions of existing patterns | 1-2 |
| F: Blind Eval | Run + review | 1-2 |
| **Total** | | **~12-16 hours** |

---

Want me to add this to the design doc and start building Phase A?

---

**User**

I think rules ingestion already has tooling to handle this, collecting all the instances and passing them for enrichment
Chunking strategy:

The corpus has inconsistent heading styles. The chunker needs a two-tier approach:

Try docx paragraph styles first — if a paragraph has style Heading 1, Heading 2, Heading 3, or Heading 4, it's a section boundary. Build section_path from the heading hierarchy.

Fallback: detect section patterns in text — for docs like the Mossford gazetteer where everything is Normal style, detect numbered sections (1. Watch Tower, 2. Temple of the Nameless Stone) or bold-text section headers. These become the section boundaries.

Minimum chunk size: If a heading section is under 50 characters, merge it with the next section (avoids micro-chunks).

Maximum chunk size: If a section exceeds ~3000 characters, it's fine — bigger is better for extraction context. Don't split large sections.

Each chunk becomes one evidence unit with section_path derived from the heading hierarchy.

---

**Cursor**

Good call — let me look at what RulesIngestion already has.

Let me look at the specific files that could be reused — particularly the enrichment pipeline and the AST/evidence unit pipeline.

You're right. RulesIngestion has exactly the infrastructure we need — we don't need to build the enrichment loop or the chunking pipeline from scratch. Here's what's directly transferable:

**The `enrich_units_batch` pattern from `stage_a_prime.py`** is the exact "collect instances, pass for enrichment" loop:
- Async semaphore-limited concurrent LLM calls
- OpenAI Responses API with structured Pydantic output schemas
- Input fingerprint → cache key → skip on replay
- Gate checks after batch completes

**The `ast_parser.py` → `stage_b.py` chain** is the chunking pipeline:
- `ast_parser.py`: markdown → heading tree (SurfaceAST)
- `stage_b.py`: heading tree → flat EvidenceUnits with `structural_path` provenance
- Headings absorbed into first child text, tables never split, monotonic ordering

What we need to ADD, not build from scratch:
1. A `docx_to_markdown()` function that maps `.docx` paragraph styles to markdown `#` headings, then the existing AST parser handles the rest
2. A numbered-section regex fallback for docs like the Mossford gazetteer where everything is `Normal` style
3. Entity extraction and fact extraction prompts (different from `A_PRIME_PROMPT_V2.md` but using the same `_responses_parse_sync` / `enrich_units_batch` infrastructure)
4. The fact store, synthesis agent, and CLI loop (genuinely new)

Let me revise the design to reflect this and add it to the design doc.

Now let me also update the chunking strategy section earlier in the document to include the specific two-tier approach you described.

The design doc is updated. Here's the summary of what changes:

**What we're reusing from RulesIngestion (not building from scratch):**

- **Enrichment loop** — `enrich_units_batch` from `stage_a_prime.py` is the exact pattern: async semaphore, OpenAI Responses API with Pydantic structured outputs, input fingerprint caching, gate diagnostics. We swap prompts and output schemas for entity extraction (Pass 1) and fact extraction (Pass 2).

- **AST parser** — `ast_parser.py`'s `^#{1,6}\s+` heading detection and tree building. Once we convert docx → markdown, this handles the heading hierarchy.

- **Evidence unit builder** — `stage_b.py`'s pattern of walking the heading tree and emitting flat units with `structural_path`, heading absorption, monotonic ordering.

- **Pipeline orchestration** — `pipeline.py`'s stage chaining with gates at each boundary.

**What's genuinely new:**

1. `docx_to_markdown()` — the missing first step, mapping `.docx` paragraph styles to `#` headings with a numbered-section regex fallback for inconsistent docs.

2. Entity/fact extraction prompts and Pydantic schemas — the actual domain-specific content.

3. Fact store — simple JSON-on-disk persistence.

4. Synthesis agent — projection → LLM prose.

5. CLI loop — the user-facing shell.

The **two-tier chunking strategy** you specified is now in the design doc — docx styles first, numbered-section regex fallback for Normal-style docs, 50-char minimum merge, no maximum split.

---

**User**

Now lets restate the goals we have in front of us

---

**Cursor**

Let me read the current state of the design doc to make sure I'm working from the latest.

Here's where we stand.

---

**Steps 1–3: DONE.** The three-layer model is validated with hand-authored data.

- Step 1 proved canon reads right (world projection from 10 facts, 8 evidence units)
- Step 2 proved the planning layer boundary holds (PREP facts don't mutate world canon, conflicts detected)
- Step 3 proved play updates don't corrupt lower layers (OBSERVED facts from real session recaps, new entities introduced in play, unfulfilled plans preserved)
- 18 tests passing, schemas validated, ruff clean

**Step 4 is what's in front of us: Ingestion Automation + CLI Chat Loop.** Six phases, each gated:

| Phase | Goal | Gate |
|---|---|---|
| **A** | Fact store + `docx_to_markdown()` + chunker | Chunker produces evidence units from `Mirathorn.docx` structurally similar to the hand-authored Step 1 units |
| **B** | Entity extraction (Pass 1) via LLM | Entity recall ≥90% against a gold entity list for Mirathorn |
| **C** | Fact extraction (Pass 2) via LLM | Automated projection covers the same ground as the Step 1 hand-authored projection |
| **D** | Synthesis agent + CLI with `ingest` and `ask` | `ingest Mirathorn.docx` then `ask "Catch me up on Mirathorn"` produces grounded prose |
| **E** | `plan`, `play`, `provenance` commands | Full CLI loop works end-to-end — the success criteria from the design doc |
| **F** | Blind eval on Set B (Mossford + others) | GM evaluates output from frozen pipeline on docs never seen during development |

The infrastructure story is: we're adapting proven patterns from RulesIngestion (the `enrich_units_batch` async enrichment loop, the AST parser → evidence unit builder chain, the pipeline orchestration with gates), not building from scratch. The genuinely new pieces are `docx_to_markdown()`, the entity/fact extraction prompts, the fact store, the synthesis agent, and the CLI loop.

**Phase A is the starting point** — it has no dependencies and produces the foundation everything else builds on.

---

**User**

Make a plan

---

**Cursor**

Let me gather the concrete details I need for the plan — the existing codebase structure, schemas, test infrastructure, and the target corpus file.

Let me check one more thing — whether the corpus files are actually on disk despite being gitignored.

Good — the corpus is on disk. `The City of Mirathorn.docx` is at the expected path. Now I have everything I need.

---

**User**

Implement the plan as specified, it is attached for your reference. Do NOT edit the plan file itself.

To-do's from the plan have already been created. Do not create them again. Mark them as in_progress as you work, starting with the first one. Don't stop until you have completed all the to-dos.

---

**Cursor**

Starting Phase A now. I’ll execute the to-dos in order, keep one in progress at a time, and run tests/lint as we go.

I’m implementing `FactStore` first with schema-validated add methods, entity dedup, JSON persistence, and reducer projection delegation.

Store and tests are green. I’m moving to the docx converter implementation next (heading-style + fallback detection).

I’m adding converter tests now, including one against the real Mirathorn corpus document plus synthetic style/fallback cases.

Next I’m implementing the chunker with a lightweight heading AST, heading-absorption behavior, min-size merge, and schema validation.

I’m running the new chunker gate script plus a full test/lint pass to verify Phase A end-to-end before closing all to-dos.

Implemented Phase A end-to-end, without editing the plan file, and completed all existing to-dos.

### What I built

- Added `FactStore` in `src/store.py`
  - JSON persistence for `evidence_units`, `entities`, `facts`
  - `load()`/`save()` round-trip
  - schema validation on add (`evidence_unit`, `entity`, `fact`)
  - entity dedup by case-insensitive display/alias overlap
  - `project()` delegates to `project_entity_state()`

- Added doc converter in `src/ingestion/docx_converter.py`
  - `docx_to_markdown()`:
    - heading style mapping (`Heading 1..6` -> `#..######`)
    - numbered-section fallback (`^\d+\.\s+\S` -> heading)
    - bold-only paragraph fallback -> heading
    - preserves bold runs as markdown `**...**`
  - `markdown_passthrough()` for `.md`
- Added `src/ingestion/__init__.py`

- Added chunker in `src/ingestion/chunker.py`
  - markdown block segmentation + heading tree construction
  - heading-absorption behavior (`heading -- first-child-text`)
  - emits schema-valid evidence units
  - min-chunk merge rule (<50 chars merged with next)
  - no max split
  - validates output with `evidence_unit.schema.json`

- Added Phase A gate eval script in `evals/mirathorn_vertical_slice/eval_chunker.py`
  - runs chunker on `The City of Mirathorn.docx`
  - compares against hand-authored Step 1 units
  - checks coverage with section-leaf matching + text overlap + first/last line coverage
  - prints pass/fail summary

### Tests added

- `tests/test_store.py`
- `tests/test_docx_converter.py`
- `tests/test_chunker.py`

### Validation run

- `uv run pytest` -> **27 passed**
- `uv run ruff check ...` on all changed files -> **All checks passed**
- `uv run python evals/mirathorn_vertical_slice/eval_chunker.py` -> **PASS: True**

### Notes

- Exact full `section_path` parity with hand-authored units is not possible for all cases because some hand-authored section labels (like `Approach to Mirathorn > City Fortification`) are semantic labels, not literal document heading hierarchy.  
- The gate script now evaluates structural comparability and coverage robustly (leaf-level + text overlap), which aligns with the plan’s “structurally comparable + full coverage” intent.

If you want, next I can start Phase B (Pass 1 entity extraction loop) on top of this foundation.

---

**User**

Lets pause and do an intentional commit, and update to relevant docs. Specifically the Design doc as we've made some decisions. 

---

**Cursor**

Great call. I’ll update the design doc with the concrete Phase A decisions we just made, then create an intentional commit with only the relevant Phase A files.

I’m going to add a focused “Phase A implementation decisions” section to the design doc, then I’ll commit only the Phase A code/tests/eval + that doc update.

Committed intentionally with the design doc update included.

### Commit created

- **Commit:** `7237253`
- **Message:** `feat(ingestion): implement Phase A store and chunking pipeline`

### Included in this commit

- `Docs/Design/DESIGN-layered-canon-vertical-slice.md`
- `src/store.py`
- `src/ingestion/__init__.py`
- `src/ingestion/docx_converter.py`
- `src/ingestion/chunker.py`
- `tests/test_store.py`
- `tests/test_docx_converter.py`
- `tests/test_chunker.py`
- `evals/mirathorn_vertical_slice/eval_chunker.py`

### Design doc updates made (as requested)

Added a new **“Phase A Decisions (Implemented)”** subsection that captures the concrete decisions we made during implementation:

- heading-only sections emit fallback evidence units
- heading absorption separator is ` -- `
- `<50` char merge keeps the earlier section path and earliest paragraph index
- gate comparison is structural/comparability-focused (not strict path equality)

### Not included (still uncommitted in working tree)

- `evals/mirathorn_vertical_slice/input/evidence_units.json`
- `evals/mirathorn_vertical_slice/input/facts.json`
- untracked `evals/mirathorn_vertical_slice/output/*`
- untracked `evals/mirathorn_vertical_slice/run_step2.py`
- untracked `evals/mirathorn_vertical_slice/run_step3.py`

If you want, I can do a second focused commit for the Step 2/3 fixture and runner artifacts.

---

**User**

Yes commit those

---

**Cursor**

I’ll create a second focused commit now for the Step 2/3 fixtures and runner artifacts. I’ll check status/diff/log first, then stage those files.

Committed.

### New commit

- **Commit:** `3d97383`
- **Message:** `feat(evals): add Step 2/3 layering fixtures and runner artifacts`

### Included in this commit

- `evals/mirathorn_vertical_slice/input/evidence_units.json`
- `evals/mirathorn_vertical_slice/input/facts.json`
- `evals/mirathorn_vertical_slice/run_step2.py`
- `evals/mirathorn_vertical_slice/run_step3.py`
- `evals/mirathorn_vertical_slice/output/campaign_projection.json`
- `evals/mirathorn_vertical_slice/output/campaign_projection_step3.json`
- `evals/mirathorn_vertical_slice/output/world_projection_step2.json`
- `evals/mirathorn_vertical_slice/output/world_projection_step3.json`

You now have two intentional commits:
1. `7237253` (Phase A implementation + design doc decisions)
2. `3d97383` (Step 2/3 fixtures, runners, and outputs)

---

**User**

Create a handoff for the next agent to start Phase B (Pass 1 entity extraction loop) on top of this foundation.

---

**Cursor**

I’ll draft a concrete handoff in `Docs/Plans` with current state, exact Phase B tasks, files to add, gates, and run commands so the next agent can start immediately.

Created the handoff for the next agent:

- `Docs/Plans/HANDOFF-phaseB-pass1-entity-extraction-loop.md`

It includes:

- current validated foundation (Phase A + recent commits)
- exact Phase B scope (Pass 1 only)
- required files to create
- loop/API expectations (async batch + structured output + cache)
- ID and dedup rules
- Mirathorn gold entity eval + recall gate (`>= 0.90`)
- test requirements and verification commands
- done criteria

If you want, I can also commit this handoff doc as a small docs-only commit.

---

**User**

@HANDOFF-phaseB-pass1-entity-extraction-loop.md (195-226) 

---

**Cursor**

That block reads as a clean **Phase B completion record** and it’s strong:

- strict + loose recall both `1.000`
- density guardrail satisfied (`1.603 <= 1.80`)
- OpenAI-backed path enforced (no heuristic fallback masking failures)
- lint + focused tests + full suite all passing

Recommended next move is to lock this in as an intentional checkpoint:
1. Commit Phase B implementation + eval artifacts.
2. Add a short “Phase B complete” note to the design doc (mirroring this evidence).
3. Create the Phase C handoff (Pass 2 fact extraction loop) with explicit gates.

If you want, I can do those three now.

---

**User**

Next 
Add a short “Phase B complete” note to the design doc (mirroring this evidence).
Create the Phase C handoff (Pass 2 fact extraction loop) with explicit gates.

---

**Cursor**

I’ll add a concise Phase B completion note in the design doc and then create a new Phase C handoff with explicit acceptance gates.

I see the Phase B execution details in the handoff, so I’ll mirror that as a concise checkpoint in the design doc and then write a dedicated Phase C handoff with explicit numeric gates.

Done — both items are in place.

### Updated design doc
Added a concise **Phase B Complete Checkpoint** section to:

- `Docs/Design/DESIGN-layered-canon-vertical-slice.md`

It mirrors the verified Phase B evidence (strict/loose recall and density guardrail) and marks Phase B as accepted baseline for Phase C.

### Created Phase C handoff
Created a new handoff with explicit, numeric gates:

- `Docs/Plans/HANDOFF-phaseC-pass2-fact-extraction-loop.md`

It includes:
- clear Phase C scope (Pass 2 only)
- required files to implement
- fact extraction contract and mapping rules
- explicit acceptance gates **C1–C5**
  - C1 schema/contract validity
  - C2 gold fact recall (`>= 0.90`)
  - C3 projection parity with Step 1 baseline attributes
  - C4 precision guardrails (duplicates/junk)
  - C5 determinism via cache replay
- required tests and verification commands

If you want, I can also add a short docs-only commit for these two updates.

---

**User**

@HANDOFF-phaseC-pass2-fact-extraction-loop.md (209-262) 

---

**Cursor**

This is a strong completion record — it reads like a proper Phase C acceptance block.

Two small things I’d tighten before treating it as final canonical history:

- `Model:` line says `MODEL_POLICY.json` `structured_generation` role. Earlier policy references `fast_smart` / `retrieval_synthesis` / `highest_intelligence`. If `structured_generation` is real in the current `MODEL_POLICY.json`, keep it; otherwise rename this to the actual role key to avoid drift.
- Gate C3 notes `90 world-layer conflicts (informational)`. Since that’s a major deviation from the original expectation, add one explicit sentence in the design doc’s Phase C section that conflict count is now **non-blocking** for granular extraction, so future agents don’t accidentally reintroduce a `0 conflict` gate.

Otherwise, this section is exactly what we want:
- clear PASS state
- explicit metrics
- created/modified files
- implementation decisions + limitations documented

If you want, I can make those two wording fixes directly in the handoff + design doc and commit docs-only.

---

**User**

Make those tweakes then lets discuss next steps. 

---

**Cursor**

Good — `structured_generation` does map to `fast_smart` which resolves to `gpt-5.3-codex`. The handoff line is accurate but slightly confusing because it mentions both the model string and the role key. I'll tighten the wording and add the conflict-count non-blocking note to the design doc.

Now add the Phase C checkpoint to the design doc with the conflict-count policy baked in.

Both tweaks are in place. Here's a summary:

**Handoff fix:** Clarified the model resolution chain (`structured_generation` -> `fast_smart` -> `gpt-5.3-codex`) and added an explicit permanent policy statement that conflict count from automated extraction is non-blocking for all future phases.

**Design doc addition:** Added a **Phase C Complete Checkpoint** section with all 5 gate results, pipeline output stats, and the conflict-count policy decision baked in as a directive to future agents.

---

Now for next steps. Looking at the build order from the design doc:

| Phase | Status |
|---|---|
| A | DONE — store + docx converter + chunker |
| B | DONE — Pass 1 entity extraction, recall `1.000` |
| C | DONE — Pass 2 fact extraction, all 5 gates pass |
| **D** | **NEXT — Synthesis + CLI (`ingest`, `ask`)** |
| E | `plan`, `play`, `provenance` commands |
| F | Blind eval (Set B — Mossford) |

**Phase D is the first time the system produces actual GM-facing output.** It has two pieces:

1. **Synthesis agent** (`src/agent/synthesis.py` + `context_formatter.py`) — takes a projection from the reducer, formats it as structured context, sends it to the LLM with a grounding prompt, returns prose. Uses `retrieval_synthesis` model role (`gpt-5.3-chat-latest`).

2. **CLI loop** (`src/cli.py` + `src/__main__.py`) — wires `ingest` and `ask` commands. `ingest` chains chunk -> Pass 1 -> Pass 2 -> store. `ask` runs store.project() -> format -> LLM -> print.

The gate for Phase D is concrete: `ingest Mirathorn.docx` then `ask "Catch me up on Mirathorn"` produces grounded prose that a GM would read and agree with.

How would you like to proceed? Options:
- I create a Phase D handoff now and you hand it to a fresh agent
- We discuss the synthesis prompt/context format design first before committing to implementation
- Something else

---

**User**

Write a handoff for phase D 

---

**Cursor**

Let me gather the context I need — the design doc's Phase D section, the current codebase structure, and the Phase C handoff for format reference.

Now let me look at the actual codebase to understand what already exists so I can accurately describe the starting point for Phase D.

Now let me check what pyproject.toml looks like for the project and if there's a `__main__.py` or `cli.py` already.

Good. I have everything I need. Let me also check the entity_extractor's public API more carefully so I can document the exact pipeline signature.

I have all the context. Now I'll write the handoff.

Done. The Phase D handoff is at `DungeonMindBuddy/Docs/Plans/HANDOFF-phaseD-synthesis-and-cli.md`.

Key points it covers:

- **Scope**: synthesis agent + context formatter + CLI with `ingest` and `ask` only (Phase E handles `plan`, `play`, `provenance`)
- **Three components**: context formatter (pure string formatting, no LLM), synthesis agent (LLM call using `retrieval_synthesis` model role), and CLI REPL with argument parsing
- **Four explicit gates**: D1 (ingest round-trip), D2 (grounded prose output), D3 (provenance in context), D4 (CLI stability)
- **Frozen baseline**: all Phase A–C files listed as do-not-modify
- **Context formatter output shape**: entity type, attribute values with truth_state labels, conflict annotations
- **Model policy**: synthesis uses `retrieval_synthesis` -> `gpt-5.3-chat-latest`, resolved from `MODEL_POLICY.json`
- **Test requirements**: unit tests with mocked LLM, eval script with real LLM against Mirathorn Set A

