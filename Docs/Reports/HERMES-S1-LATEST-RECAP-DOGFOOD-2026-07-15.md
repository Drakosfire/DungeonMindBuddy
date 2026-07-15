# Hermes S1 Latest-Recap Dogfood — 2026-07-15

**Gate:** ACCEPTED after repair rerun
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

## Initial live rejection

Earlier the same day, three live Plan/Hermes trials at
`/plan?campaign=longmont-c2&session=24&dogfood=1&tool=recap` all returned a
generic empty-graph abstention:

| Trial | Agent result | Graph result | Duration |
|---|---|---|---:|
| 1 | `hermes · partial · abstained` | `empty · 0 matched · abstained` | 11296 ms |
| 2 | `hermes · partial · abstained` | `empty · 0 matched · abstained` | 10282 ms |
| 3 | `hermes · partial · abstained` | `empty · 0 matched · abstained` | 10390 ms |

Root cause: `latest_recap_change` was injected into the Hermes packet, then dropped
on retrieval-session hydrate; with no admissible claims the validator returned
`no_admissible_claims` instead of a specific disclosed gap.

## Repair rerun — live Hermes trials

After preserving `latest_recap_change` through the retrieval-session boundary and
adding a server-owned S1 gap fallback, three fresh Hermes queries were submitted
through `POST /api/live/query` with `query_backend=hermes` and Plan-equivalent
focus `session-24` (outer live packet remained `session=22`).

| Trial | Grounding | Acceptance | Memory lag | Duration |
|---|---|---|---|---:|
| 1 | `partial` | `partial_coverage` | disclosed | 14079 ms |
| 2 | `partial` | `partial_coverage` | disclosed | 11680 ms |
| 3 | `partial` | `partial_coverage` | disclosed | 11191 ms |

Each trial named `session-24`, the comparison boundary to graph-head
`session-23` at revision `rev:5cadc9798562862cdde22350d8a3b56c`, disclosed
memory lag, and made a specific evidence-gap / promotion request. None returned
`no_admissible_claims`.

Artifact: `evals/graph_memory_layer/artifacts/last_s1_live_repair_trials.json`

## Gate decision

**Accept S1.** The deterministic resolver remains green, and the repaired live
route no longer terminates on an empty focused graph before using the
server-provided latest-recap context.

S1 acceptance proves the first conversational sensemaking gate. It does not
authorize creative workflow primitives by itself; Phase 2
`CreativeOperationSession` construction may now begin under the reset plan.
