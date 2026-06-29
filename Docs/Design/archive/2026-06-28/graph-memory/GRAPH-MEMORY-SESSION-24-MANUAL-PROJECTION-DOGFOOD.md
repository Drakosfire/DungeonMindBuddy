# Graph Memory Session 24 Manual Projection Dogfood

Status: design + fixture anchor  
Schema: `dmb_manual_graph_projection_dogfood_benchmark_v0`  
Campaign: `longmont-c2`  
Focus session: `session-24`

## Purpose

This dogfood benchmark tests a product question, not an extraction question:

> Given a raw recap and a manually authored gold graph, does graph-chip projection make the GM faster and better prepared for the next session while preserving source truth?

The benchmark is designed for the union-supergraph projection direction. Recap chips should resolve to global-style nodes, focus-session evidence should be highlighted, and adjacent nodes should help the GM prep the next scene.

## Non-goals

This is not:

- an LLM extractor benchmark;
- an approved-memory write;
- a canon promotion artifact;
- a corpus mutation;
- a production retrieval change;
- `/plan` integration;
- Agent Interaction integration;
- a claim that Session 24 graph memory is complete.

## Fixture location

```text
evals/graph_memory_layer/examples/session_24_manual_projection_dogfood/
  README.md
  session_24_raw_recap_PLACEHOLDER.md
  session_24_source_anchors.json
  session_24_manual_gold_graph.json
  session_24_projection_questions.json
  session_24_manual_dogfood_report_template.md
```

The placeholder recap file exists so the raw Discord-derived recap can be pasted in without embedding transport/UI noise into the initial commit.

## Benchmark question

The central question is:

> Reviewing Session 24, can the GM click chips like Caelynn, Edge refugees, the north wall, meat goo, tripod monsters, Grobnok, or the refugee plan and immediately understand what matters for opening Session 25?

The answer should be judged on whether the projection surfaces:

1. correct focus-session evidence;
2. useful adjacent nodes;
3. unresolved hooks;
4. high-risk approval boundaries;
5. prep-relevant scene choices;
6. restraint around unknowns.

## Source anchor model

The fixture uses paragraph-level source anchors until a line/span resolver is wired to the pasted raw recap. Each anchor includes expected text fragments so a future script can verify that the placeholder raw recap still matches the anchor assumptions.

Important anchors include:

- hybrid/Ogonob/firebolt/first compulsion;
- Bonogo pinning the hybrid and Baergrom’s crossbow jam;
- meatwing wide charm and tripod awakening;
- Stafl’s Enemies Abound attempt, golem wall pressure, Lysandra’s Commanding Shout, and Caelynn cleanse;
- wall/foundation damage, tripod fire kill, and golem weaknesses;
- sewer wall climb, sticky gel, Baergrom protecting Thrin, and Bonogo sewer kill;
- Ephanna impaled by tripod, Sleep/Luck, final assault setup, and poison spray;
- Karsemine friendly fire, final hybrid kill, and coordinated tripod kill;
- meat piles turning to goo and sinking underground;
- Caelynn’s Grobnok call and pending rockie-talkie bridge.

## Gold graph emphasis

The manual gold graph emphasizes:

- PCs and allies as clickable prep nodes;
- monsters as mechanics-memory nodes;
- locations as pressure surfaces;
- unresolved hooks as first-class graph nodes;
- deferred and ignored items as safety boundaries.

The most important unresolved hooks are:

- Edge refugee handling;
- north wall/foundation integrity;
- meat goo sinking underground;
- current status of Edge;
- Grobnok’s next-day callback;
- pending Grobnok-Lysandra rockie-talkie connection;
- short-rest/watch pressure at the gate.

## High-risk claims

The benchmark should friction or fail answers that claim:

- the refugees are safe, contaminated, admitted, housed, or rejected;
- the wall is safe, breached, collapsed, or repaired;
- the meat goo was destroyed or purified;
- Edge is saved, destroyed, empty, or fully occupied;
- Grobnok can already talk directly to Lysandra;
- the party has completed a long rest;
- exact HP/spell slots/final monster counts.

## Passing behavior

A successful projection should make these answers easy:

- “What is the exact situation as Session 25 opens?”
- “Who went where after the fight?”
- “What should I remember about the Edge refugees?”
- “What happened when they tried to burn the remains?”
- “Which monster mechanics should carry forward?”
- “What should I see when I click Caelynn?”
- “What should I see when I click the north wall?”
- “Which items need high-risk friction before approval?”

## Scoring

Each benchmark question is scored across five 0–2 dimensions:

| Dimension | 0 | 1 | 2 |
| --- | --- | --- | --- |
| Source grounding | No evidence or wrong source | Some relevant evidence | Correct anchors/snippets for each claim |
| Projection quality | Missing chips | Some chips surfaced | Required chips plus useful adjacency |
| Focus-session clarity | Confuses sessions | Mostly Session 24 | Distinguishes focus Session 24 from prior/global context |
| Prep usefulness | Generic recap | Partly actionable | Helps the GM run the next scene |
| Restraint | Invents or over-promotes | Minor overreach | Preserves deferred/unknown boundaries |

A question passes at 8/10 with no hard restraint failure.

Hard fail conditions:

- canon promotion;
- approved memory write;
- corpus mutation;
- production retrieval claim;
- unsupported exact count;
- unresolved hook claimed resolved;
- treating manual gold as extractor output.

## Why this belongs before extractor work

The existing graph-memory ladder already asks whether candidate graph output is safe, evidence-backed, and incomplete. This artifact asks a different product question:

> What should the graph projection be able to do once the graph is good enough?

That makes this a target fixture for projection UX, node view design, adjacency usefulness, and future extractor acceptance criteria.
