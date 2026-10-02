# Hermes tuning experiment

This experiment separates prose from tool use. Every supplied fact is synthetic; no campaign corpus content is used. The paired prose cases send the same effective user prompt and system policy through a direct Luna Responses call and Buddy's embedded Hermes conversation-only route. The Graph cases run Hermes with the normal read-only Graph tool definitions while an in-process fake dispatcher returns a deterministic synthetic fixture.

## Run it

Install the pinned environment and run the control, one voice variation, and the isolated Graph cases:

```bash
uv sync --locked
uv run python evals/hermes_tuning/run_pair.py --variant control
uv run python evals/hermes_tuning/run_pair.py --variant voice
uv run python evals/hermes_tuning/run_synthetic_graph.py
```

These commands make live calls to the policy-resolved OpenAI model using `OPENAI_API_KEY`. The harness prints only identifiers and measurement summaries; its JSON artifact stores the synthetic prompt, answers, token traces, and model/tool-event counts. The key is neither copied nor printed. The fixed fixture and rubric live in this directory; model outputs go under `artifacts/`.

## Prose pair results

Control and voice rows differ by exactly one additional sentence in the user request: “Write as a calm, practical co-GM: direct, warm, and specific; avoid generic dramatic flourishes.” Both routes received the same effective prompt within each row. Provider was `openai-api`, model `gpt-6-luna`, API mode for Hermes was `codex_responses`.

| Variant | Route | Wall time | Provider call | Input / output tokens | Estimated cost | Calls / tools |
|---|---|---:|---:|---:|---:|---:|
| Control | Direct | 4,071 ms | Included in wall | 246 / 229 | $0.0001391 | 1 / 0 |
| Control | Hermes | 7,908 ms | 3,544 ms | 633 / 263 | $0.0001948 | 1 / 0 |
| Voice | Direct | 3,568 ms | Included in wall | 269 / 247 | $0.0001504 | 1 / 0 |
| Voice | Hermes | 7,181 ms | 3,461 ms | 656 / 211 | $0.0001711 | 1 / 0 |

The input-token difference was 387 tokens in both pairs, reflecting Hermes's additional assembled request context. Control Hermes wall time exceeded the observed provider request by 4,364 ms; voice exceeded it by 3,720 ms. Initialization, plugin discovery, first visible text, and response projection were not timed separately, so these are unallocated residuals. All calls were non-streaming; TTFT is unknown.

Both versions passed the hard checks in the rubric. The paired answers were close in coverage and naturalness. The voice variation did not establish a quality improvement: direct voice output had the awkward phrase “still un followed,” while Hermes voice read more naturally in this one example. Sample count is one per cell, so latency and wording differences are descriptive only.

## Synthetic Graph cases

| Case | Hermes model calls | Graph operations | Result |
|---|---:|---|---|
| Direct fact: Nera's role | 2 | One successful `search` (9,348.5 ms total) | Correctly identified Nera as keeper of the east watchtower. |
| Two-hop: Nera to Old Quarry | 3 | Partial `search`, then successful depth-2 `neighborhood` (7,995.3 ms total) | The model supplied `targets: [{"kind":"node","id":"person:nera"}]`; the fake returned both fixture edges. The answer gave the chain and kept the trail's destination and Nera's whereabouts unverified. |

The fake dispatcher validates the model-visible `targets` schema before returning a neighborhood result; it does not expect the executor's downstream `seedNodeIds` field. The first search returns only Nera and no relationships. Hermes then makes one valid neighborhood request seeded by `person:nera` at depth 2, and the fake returns the two-edge fixture path. The recorded result is `status: ok` with successful retrieval events; here both turn completion and bounded fixture expansion succeeded. This demonstrates the tool contract on a deterministic fake, not autonomous crawling against a native Graph. The fake replaces the dispatcher inside the benchmark process; no Graph database or service is contacted. It says nothing about native Graph traversal, retrieval authority, evidence admission, source reads, or the personal corpus.

The exact records are [`20261002T043842Z-control.json`](artifacts/20261002T043842Z-control.json), [`20261002T043534Z-voice.json`](artifacts/20261002T043534Z-voice.json), and [`synthetic-graph-cases.json`](artifacts/synthetic-graph-cases.json). Each contains the input or fixture hash and response traces. The prose artifacts preserve full answers; all their content is synthetic.

## Scoring rubric

Hard correctness gates are evaluated separately from prose quality:

- **Grounding:** every concrete claim follows from supplied evidence or returned fixture nodes/edges.
- **Uncertainty:** unresolved facts remain explicitly unresolved; no outcome is invented.
- **Task fit:** answers the question directly, respects the word cap, and follows the requested format.
- **Prose quality:** natural phrasing, useful prioritization, clarity, and minimal rewriting required.

A response that fails a hard gate cannot win on prose. The four prose answers passed the hard gates. The Graph direct-fact answer was correct. In the two-hop case, the fake returned both requested fixture edges after Hermes supplied the accepted node target; the final answer reported the known chain while preserving the unresolved endpoint and motive. Soft prose judgments are qualitative and not blinded or statistically meaningful.

## Limits and next evidence gate

This is a Luna/Hermes harness comparison, not a campaign evaluation. It does not establish better prose, lower latency at scale, TTFT, or real Graph-crawling quality. It demonstrates one successful target-seeded neighborhood request against an in-process fixture only. No cross-model challenger was tested. The cost estimates use Buddy's checked-in pricing table; unknown provider-side fees are outside these traces.

A requested real-corpus follow-up remains blocked: automatic review rejected sending private C2 Session 23 evidence and its prompt to OpenAI, with the stated reason that tuning approval did not specifically authorize exporting that payload to the external destination. Do not reroute that payload through another client. Resume that cohort only after explicit approval for the particular content and destination. A permitted native-Graph witness is also still needed before making any claim about real Graph crawling.
