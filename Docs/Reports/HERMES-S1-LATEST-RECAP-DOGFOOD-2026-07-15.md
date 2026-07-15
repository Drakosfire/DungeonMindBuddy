# Hermes S1 Latest-Recap Dogfood — 2026-07-15

**Gate:** REJECTED
**Question:** “What changed after the latest ingested recap?”
**Scope:** read-only Plan/Hermes sensemaking over the retained S0 retrieval boundary

## Deterministic contract

Command:

```text
PYTHONPATH=src:. uv run python scripts/hermes_s1_latest_recap_dogfood.py
```

Result: `ok=true`, `cost_usd=0.00`, with no corpus or graph mutations.

The server-owned context correctly identified:

- latest admitted recap: `session-24`;
- graph head: `session-23`;
- pinned graph revision: `rev:5cadc9798562862cdde22350d8a3b56c`;
- comparison boundary: latest admitted recap to graph head;
- outcome: `memory_lag`;
- diagnostic: `latest_recap_not_in_graph_head`.

Artifact: `evals/graph_memory_layer/artifacts/last_s1_latest_recap_dogfood.json`

## Real Plan/Hermes trials

The canonical question was submitted three times in the live Plan surface at
`/plan?campaign=longmont-c2&session=24&dogfood=1&tool=recap`, using fresh
requests in the same Ask DungeonBuddy drawer.

| Trial | Agent result | Graph result | Duration |
|---|---|---|---:|
| 1 | `hermes · partial · abstained` | `empty · 0 matched · abstained` | 11296 ms |
| 2 | `hermes · partial · abstained` | `empty · 0 matched · abstained` | 10282 ms |
| 3 | `hermes · partial · abstained` | `empty · 0 matched · abstained` | 10390 ms |

The selected final response exposed:

- answer: generic insufficient-admitted-evidence abstention;
- reason: `no_admissible_claims`;
- warning: `graph_context_empty`;
- diagnostic: `focus_overlay_built`, `Focused 0 nodes for focus=session`;
- ingestion proof still showed admitted source units through Session 24.

The user-facing response did not identify the latest recap, comparison boundary,
or memory lag, and did not select meaningful campaign movement.

## Gate decision

**Reject S1.** The deterministic resolver is green, but the real agent path does
not consume that context as a useful sensemaking answer. Three trials reproduced
the same generic abstention, so this is a stable product failure rather than
sampling noise.

The next gate is to repair the S1 route so an empty focused graph does not
terminate the turn before Hermes can use the server-provided latest-recap
context. A successful rerun must name the admitted recap and comparison
boundary, disclose memory lag, and either describe grounded movement or make a
specific disclosed evidence-gap request.

`CreativeOperationSession` and other creative workflow primitives remain
explicitly out of scope until that rerun passes.
