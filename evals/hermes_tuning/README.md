# Hermes tuning experiment

## Synthetic co-GM style pairs

Run the fixed 12-case matched cohort after validating it offline:

```bash
uv run pytest -q tests/test_hermes_tuning_style_pairs.py
uv run ruff check evals/hermes_tuning/run_style_pairs.py tests/test_hermes_tuning_style_pairs.py
uv run python evals/hermes_tuning/run_style_pairs.py --output /tmp/hermes-style-cohort.json --stop-after 2
uv run python evals/hermes_tuning/run_style_pairs.py --resume --output /tmp/hermes-style-cohort.json --stop-after 12 --blind-output /tmp/hermes-style-blind.json
```

The harness requires policy-resolved `openai-api` / `gpt-6-luna`, a key in the established environment, and exactly twelve checked-in synthetic cases. Each pair uses the same evidence, task request, conversation-only policy, and system prompt. The treatment appends only the fixed `voice_variation` sentence from `scenario.json` to the user request. Arm order is randomized by a saved seed. Each turn uses a fresh session and one Hermes call; no direct API arm or Graph tool is enabled. Raw answers, safe call telemetry, evidence, prompt hashes, gates, and order are stored in the raw cohort. The separate blind packet contains A/B answers and scoring keys only, with no condition mapping, timing, or token/cost measures. Have reviewers score that packet before consulting the raw mapping.

The deterministic screen checks successful nonempty output, a 100-word cap, no headings/bullets, at least one explicit uncertainty marker, exactly one model call, and zero tool events. These checks do not establish full factual grounding. In particular, the lexical uncertainty check can conservatively reject an answer that conveys uncertainty without one of its listed terms. Evidence-keyed grounding, uncertainty preservation, task fit, naturalness, clarity, concision, and A/B/tie preference require blinded human scoring. A failed hard screen cannot win on prose; exclude that pair from the primary prose preference summary unless blind review identifies a gate-classification defect before unblinding.

The completed cohort is documented in [`artifacts/style-pairs-20261002T085003Z.json`](artifacts/style-pairs-20261002T085003Z.json). All 24 turns returned `ok`, each made one observed model call, and no tools were called. The deterministic lexical screen initially passed 22/24 answers: both `council-bell` answers failed only because their explicit uncertainty used wording outside the screen's marker list. Both blinded reviewers independently judged both answers to preserve uncertainty, so this is a recorded false negative; the original gate fields remain unchanged. Both reviewers also independently rejected the control answer for `northfield-well` (invented resident attribution) and the voice-sentence answer for `gloam-orchard` (invented unaffected comparison row). Those two pairs are excluded from the primary comparison, leaving ten pairs where both answers passed human grounding/uncertainty/format/actionability gates.

Each reviewer scored ten eligible pairs while blind to condition, using 1–5 scales in this order: task fit/actionability, clarity, natural co-GM voice, concision. PRIME's A/B/tie preferences mapped to control/voice were 4/5/1; the independent reviewer's were 4/6/0. Mean scores by arm were:

| Reviewer | Arm | Task fit/actionability | Clarity | Natural co-GM voice | Concision |
|---|---|---:|---:|---:|---:|
| PRIME | Control | 4.6 | 4.6 | 4.2 | 4.3 |
| PRIME | Voice sentence | 4.4 | 4.4 | 4.2 | 4.0 |
| Independent | Control | 4.5 | 4.6 | 4.0 | 4.4 |
| Independent | Voice sentence | 4.5 | 4.4 | 3.9 | 4.0 |

Both reviewers show a small preference lean toward the voice sentence, while its naturalness means are tied or slightly lower and its clarity/concision means are lower. This mixed, small-sample result does not establish a prose-quality improvement or justify a product prompt change. Estimated cost was $0.0045904 using the checked-in pricing table, with 21,344 reported total tokens. Wall time varied across matched arms and is descriptive only. Twelve pairs are exploratory. Non-streaming calls leave TTFT unknown. The two locked blinded score files' hashes, mapped case-level ratings, and post-score gate adjudication are preserved in the result artifact; raw answers and original automated gates are unchanged.

The process emitted ignored provider-plugin registration compatibility warnings and asynchronous `FileNotFoundError` logging traces for generated temporary Hermes home directories during cleanup. All 24 typed turn results and observed model calls completed successfully. These logger diagnostics were not included in the raw answer artifact; timings remain descriptive and may include setup/logging work.

This experiment separates prose from tool use. Every supplied fact is synthetic; no campaign corpus content is used. The paired prose cases send the same effective user prompt and system policy through a direct Luna Responses call and Buddy's embedded Hermes conversation-only route. The Graph cases run Hermes with the normal read-only Graph tool definitions while an in-process fake dispatcher returns a deterministic synthetic fixture.

## Run it

Install the pinned environment and run the control, one voice variation, and the isolated Graph cases:

```bash
uv sync --locked
uv run python evals/hermes_tuning/run_pair.py --variant control
uv run python evals/hermes_tuning/run_pair.py --variant voice
uv run python evals/hermes_tuning/run_synthetic_graph.py
uv run python evals/hermes_tuning/run_host_latency.py --samples 5
uv run python evals/hermes_tuning/run_host_phases.py --samples 5
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

## Process-isolated host latency

The successor harness calls `HermesGraphAgentHost` directly from one parent process (spawn start method). It records `start()` through worker-ready separately, then executes one turn on that fresh worker followed by four turns on the same worker. Each host turn is paired with a direct Responses call using the same effective synthetic prompt, system policy, and policy-resolved model. The direct call precedes each host turn. Artifact: [`host-latency-20261002T051413Z.json`](artifacts/host-latency-20261002T051413Z.json).

Provider/model were `openai-api` / `gpt-6-luna`. Worker-ready took 1,728.9 ms; the cold host turn took 9,112.5 ms, with a 5,007.8 ms observed model call and 4,104.6 ms unallocated residual. Adding the separately measured ready span gives 10,841.4 ms from host start through the cold result. The four subsequent outer turns had a median wall time of 6,216.3 ms and median residual of 1,970.8 ms. All five used worker PID 1351768; the four later turns therefore reused the same process. Each turn made one model call and zero tool calls.

| Sample | Phase | Direct wall | Host wall | Model call | Residual | Direct tokens / cost | Hermes tokens / cost |
|---|---|---:|---:|---:|---:|---:|---:|
| 1 | Cold worker | 5,070.8 ms | 9,112.5 ms | 5,007.8 ms | 4,104.6 ms | 246 / 365 · $0.0002071 | 633 / 367 · $0.0002468 |
| 2 | Reused worker | 4,568.5 ms | 6,488.4 ms | 4,098.8 ms | 2,389.6 ms | 246 / 332 · $0.0001906 | 633 / 290 · $0.0002083 |
| 3 | Reused worker | 4,003.1 ms | 6,148.9 ms | 4,496.3 ms | 1,652.7 ms | 246 / 301 · $0.0001751 | 633 / 304 · $0.0002153 |
| 4 | Reused worker | 4,062.9 ms | 6,283.7 ms | 5,032.7 ms | 1,251.0 ms | 246 / 318 · $0.0001836 | 633 / 363 · $0.0002448 |
| 5 | Reused worker | 3,014.0 ms | 6,096.9 ms | 3,808.1 ms | 2,288.8 ms | 246 / 249 · $0.0001491 | 633 / 233 · $0.0001798 |

The warm median residual is 52% below the cold residual in this five-turn run. Direct control wall times also varied (3,014.0–5,070.8 ms), while Hermes provider-call durations overlapped (cold 5,007.8 ms; warm 3,808.1–5,032.7 ms). Treat this as an observed association with a reused worker, not proof of a warm-up cause or a production speedup. Host-ready, outer turn, and model-call spans are directly timed; import, plugin discovery, scheduling, projection, and IPC are not isolated. Neither route streams useful answer text to this harness, so TTFT is unknown.

All five host answers passed the experiment's deterministic screening gates: status `ok`, nonempty response, at most 100 whitespace-delimited words, bridge-and-dusk pressure, Nera marked missing/disappeared/vanished, and at least one explicit uncertainty marker. This screening is not a grounding proof; inspect the stored synthetic answers for semantic correctness. After the run, the gate was corrected to accept “Nera vanished,” and the gate fields were recomputed offline. Raw model answers, provider timings, tokens, costs, and PIDs were unchanged; the artifact marks this post-run gate-only correction.

A requested real-corpus follow-up remains blocked: automatic review rejected sending private C2 Session 23 evidence and its prompt to OpenAI, with the stated reason that tuning approval did not specifically authorize exporting that payload to the external destination. Do not reroute that payload through another client. Resume that cohort only after explicit approval for the particular content and destination. A permitted native-Graph witness is also still needed before making any claim about real Graph crawling.

## Host phase timings

The phase successor uses the same synthetic scenario and direct Luna control, but leaves worker startup lazy so the first `execute()` measures acquisition/readiness at the actual parent/worker boundary. Four subsequent turns reuse the same worker. The artifact [`host-phases-20261002T064329Z.json`](artifacts/host-phases-20261002T064329Z.json) contains five direct/host pairs and bounded phase spans; the harness writes each sample before reporting progress.

| Sample | Worker | Direct wall | Host wall | Provider call | Host residual | Acquire/ready | Worker result wait |
|---|---|---:|---:|---:|---:|---:|---:|
| 1 | Cold | 4,962.2 ms | 11,570.5 ms | 3,705.6 ms | 7,864.9 ms | 2,638 ms | 8,930 ms |
| 2 | Reused | 3,448.7 ms | 4,999.8 ms | 3,050.5 ms | 1,949.3 ms | 0 ms | 4,998 ms |
| 3 | Reused | 3,504.1 ms | 5,052.5 ms | 3,072.8 ms | 1,979.8 ms | 0 ms | 5,050 ms |
| 4 | Reused | 3,494.4 ms | 7,349.7 ms | 3,979.4 ms | 3,370.2 ms | 0 ms | 7,348 ms |
| 5 | Reused | 3,751.7 ms | 6,383.5 ms | 4,231.0 ms | 2,152.6 ms | 0 ms | 6,381 ms |

The same worker PID (1433786) served all five turns. Each host turn passed the deterministic answer gates, made one provider call, and made zero tool calls. Direct estimated costs were $0.0001281, $0.0001391, $0.0001401, $0.0001536, and $0.0001481; host estimated costs were $0.0001538, $0.0001473, $0.0002008, $0.0001908, and $0.0001933. Host inputs were 633 tokens per call versus 246 for each direct control.

Serialization, wire encoding, queue puts, acceptance, and decoding measured 0–1 ms per phase. Cold worker acquisition/readiness accounts for 2,638 ms of the cold turn. `host_worker_result_wait` encloses the entire worker execution, including the observed provider duration, so it must not be added to provider time. After subtracting model-call duration, the remaining cold gap is about 5.2 seconds inside worker execution; warm residuals are 1.9–3.4 seconds. The host instrumentation localizes that time to the worker interval but does not separate imports, plugin discovery, provider setup, response projection, or other worker work. These five calls describe one run and do not prove a production speedup. No private corpus or live Graph was used; non-streaming API output leaves TTFT unknown.

## Rung 3 worker phase timings

The worker-phase slice adds six bounded spans inside the actual Rung 3 execution. It uses the same synthetic scenario, direct Luna control, process boundary, and five-turn sequence as the prior witness. After review, the labels were corrected and this five-turn witness was rerun; the raw records, including unmodified synthetic answers, are in [`host-phases-20261002T080751Z.json`](artifacts/host-phases-20261002T080751Z.json). Worker PID was 1514024 for all five host turns; samples 2–5 reused it. Each direct and host turn made one model call, each host turn made zero tool calls, and all ten answers passed the deterministic hard gates.

Reproduce that run with:

```bash
uv run python evals/hermes_tuning/run_host_phases.py --samples 5 --output evals/hermes_tuning/artifacts/host-phases-20261002T080751Z.json
```

| Sample | Worker | Direct wall | Host wall | Host acquire/ready | Model call | Host residual | Bootstrap/logger+home setup | Cached factory lookup | Plugin discovery | Agent construction | Provider conversation | Normalize/project | Unallocated in worker wait | Direct cost | Hermes cost |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | Cold | 5,836.7 ms | 10,244.7 ms | 1,878 ms | 4,551.3 ms | 5,693.3 ms | 1,216 ms | 1 ms | 460 ms | 390 ms | 6,283 ms | 0 ms | 14 ms | $0.0001616 | $0.0002163 |
| 2 | Reused | 5,511.0 ms | 6,863.5 ms | 0 ms | 4,871.8 ms | 1,991.7 ms | 3 ms | 1 ms | 423 ms | 485 ms | 5,929 ms | 0 ms | 18 ms | $0.0001911 | $0.0002403 |
| 3 | Reused | 4,883.1 ms | 8,220.5 ms | 0 ms | 6,433.6 ms | 1,786.9 ms | 2 ms | 1 ms | 402 ms | 296 ms | 7,505 ms | 0 ms | 13 ms | $0.0002206 | $0.0002548 |
| 4 | Reused | 3,068.6 ms | 5,022.4 ms | 0 ms | 3,023.6 ms | 1,998.8 ms | 3 ms | 1 ms | 457 ms | 327 ms | 4,218 ms | 0 ms | 14 ms | $0.0001356 | $0.0002028 |
| 5 | Reused | 3,960.2 ms | 5,064.8 ms | 0 ms | 3,894.7 ms | 1,170.1 ms | 3 ms | 1 ms | 396 ms | 304 ms | 4,335 ms | 0 ms | 24 ms | $0.0001831 | $0.0001713 |

Provider conversation encloses the observed model call, so those columns overlap and must not be added. The provider-call residual inside that phase was about 1,732 ms cold and 440–1,194 ms warm. Bootstrap/logger+home setup, cached factory lookup, plugin discovery, and construction together measured 2,067 ms cold and 701–912 ms warm. The sum of worker phases was within 13–24 ms of `host_worker_result_wait` on every turn. The total host residual also includes cold acquire/readiness (1,878 ms) and small parent/IPC overhead; that makes the worker-phase breakdown consistent with, rather than additive to, the host residual.

The API returns complete answers after the conversation, so normalization/projection rounded below the 1 ms display precision on these runs; this is a measured lower bound, not proof the work is free. The cold bootstrap/logger+home interval is conspicuous, and plugin discovery/construction recur on warm turns. These measurements identify where this code spends time in this run; they do not demonstrate an optimization or explain all machine/provider variability. Provider durations and direct-control wall times vary between adjacent samples. The worker's module startup imports happen before the `ready` message and are included in host acquire/readiness. Separately, `_initialize_worker_logger_home()` imports and caches `run_agent` during first-turn bootstrap/logger+home setup. The later factory lookup is cached; this experiment cannot isolate the true cold `run_agent` import without changing bootstrap behavior, which is outside this lease. Policy resolution, inference resolution, and retrieval-session hydration before `_RUNTIME_LOCK` are also outside the six spans. The artifact contains only the synthetic scenario, answers, usage, and timing telemetry; no private corpus or Graph service was used. The timing telemetry contains no prompt, answer, or Graph context fields.
