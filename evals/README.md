# Lab and evaluation

- [Agent action catalog](plan-authoring-benchmark.md#action-catalog) and [workflow decision benchmark](plan-authoring-benchmark.md#workflow-decision-benchmark) — proven actions, requested actions, and when Buddy should use them.
- [Adventure-to-follow-up benchmark](adventure-to-follow-up-benchmark.md) — adventure intake, Plan, Play, combat, and cited recap continuity.
This directory holds experiments, regression fixtures, and evaluation evidence.
Start with the suite that owns the question you are testing.

| Question | Entry point |
| --- | --- |
| Did an extraction or graph change preserve the expected evidence? | [Graph memory fixtures and baselines](graph_memory_layer/README.md) |
| Did session-event extraction preserve chronology? | [Session-event extraction suite](session_events_extraction_vertical_slice/README.md) |
| Inspect the historical isolated Graph demo | [Historical Graph transport and launcher](native_graph_demo/README.md) |
| How fast is Old Bath House from Buddy through Plan, Play, and explicit Combat start? | [Old Bath House baseline](../Docs/Benchmarks/BASELINE-old-bath-house.md) and [runner](old_bath_house/README.md) |
| How does the canon layering baseline score? | [Canon layering runner](canon_layering/run_benchmarks.py) |
| What ingestion baseline was accepted, and what retrieval experiments came before? | [Accepted ingestion baseline and retrieval history](../Docs/Reports/REPORT-ingestion-baseline-and-retrieval-history-2026-11-07.md) |

Run local Buddy evaluations through the Projects storage check. Use a task slug
you own and reuse it only for runs with compatible dependencies.

```bash
scripts/run_local_lab.sh canon-baseline uv run python evals/canon_layering/run_benchmarks.py
```

The launcher verifies the Projects filesystem before allocating scratch, a uv
cache, and a task-local Python environment. Use `TMPDIR` for explicit generated
output paths too. The launcher exits if Projects is unavailable. Runner-specific
output overrides and commands invoked directly remain the caller’s responsibility.

Read the suite's inputs before running it. Some runners use paid providers or
private campaign sources. Record the source revision, inputs, runner options,
and result location. Keep generated runs in the task's output location and
promote only evidence or fixtures with a named consumer.

### Offline retrieval oracle

Pass `--oracle gold-oracle.json --citation-readback reopened.jsonl` to the
ordinary benchmark workflow's `report` mode with the retained capture
manifest. The report embeds `retrieval_analytics` keyed by case and item.
Capture mode rejects both options.

The `buddy_retrieval_oracle_v1` file maps case IDs under `cases` to
`question` and `items`. Each item has an `id` and a nonempty `witnesses`
list with `session`, `line`, `text`, and `source_sha256` per witness.
All witnesses for an item must appear with matching source readback.
Readback JSONL uses `question` (case ID), `handle`, and `matches` with
`ref`, `event`, `body_sha256`, `excerpt_sha256`, `start`, and `end`. The report matches them against Buddy’s authorized selected reads.

The report counts packet and excerpt tokens, verified unique Gold lines, and
exact repeated source spans. Gold line counts include surrounding prose.
Graph restatements and paraphrases are outside the exact overlap measure.
Erroneous context is unknown without semantic assessment.

### Ordinary retrieval benchmarks

Use ordinary Jev as the control. The measured opening-batch cohort delivered
15/15 eligible contexts with 72/72 required evidence items and a 6.54-second
median from request dispatch to writer-ready. See the
[retained evidence and build pins](../Docs/Plans/HANDOFF-RETRIEVAL-opening-batch.md).
The measured Jev loop and text writer context were subsequently shipped in
[#3673](https://github.com/Drakosfire/DungeonMindBuddy/pull/3673). Keep BM25,
semantic ranking and hybrid experiments in the lab. A historical lexical pilot
is a diagnostic and does not replace the production control.

Use the existing workflow's `capture-context` mode for retrieval-only runs.
It stops at the authorized writer-ready packet before writer dispatch. Keep
Gold local and score the retained packet against exact reopened citations.
Pin the build, Graph head, source revisions and admission view. Use the same
questions and evidence budget in both arms. For Wandering Forest, compare
ordinary Jev with bounded Event traversal at eight passages per arm and report
tokens as well. Diagnose each missing witness at publication, retrieval,
packet construction or citation readback before changing an owner.

**Timing and preflight.** Start with one ordinary question. Verify the runtime
and isolated database identities, then require a writer-ready capture and exact
citation reopening before launching the cohort. Roughly 6–7 seconds per question
is the historical Q-cohort median, with six seconds the optimization target.
Report setup wall time and
per-question request-to-ready time separately, including the median and slowest
question. If the first question runs for roughly 30 seconds without a ready
capture, inspect the current phase and last trace event before dispatching more.
That is a diagnostic checkpoint, with no automatic cancellation or retry. A
run that never dispatched a question is a setup failure and contributes no
retrieval latency sample.

### Latency waterfall

Retain individual intervals with the opt-in `capture-context --detailed-trace`
switch. Render an existing capture without an evaluator or provider call.

```bash
python -m evals.buddy_benchmark.workflow trace-report \
  --manifest MANIFEST.json --trace-input CAPTURE_DIRECTORY \
  --case Q01 --output REPORT_DIRECTORY
```

The command validates the retained writer packet and case identity, then emits
`trace-report.json` and `trace-report.html`. Use the run root for a browser
capture that stores transport clocks next to its capture directory. Browser
timing is attributed only when the retained browser request and clock bounds
match the captured case. Host-only captures use request start. The report
labels writer-ready and writer transport sink separately. Outer wrapper spans
are excluded from attributed wall time, and simultaneous independent spans
share one interval. The operation table shows timed call counts, zero-duration
markers, inclusive time, maximum observed call and exclusive wall time. Shared
intervals remain in the waterfall and are not assigned to an individual
operation. Packet content, Gold and citations are kept in the
original evidence artifacts.

### Graph completeness and missing-evidence attribution

For each Gold witness expected to have a Graph path, record the first proven
boundary where it was lost. Inspect the pinned source and admission, retained
extraction, review decision, publication receipt, and Graph readback in order.

| Boundary | Evidence of a gap |
| --- | --- |
| Source eligibility | The pinned source lacks the witness, or the source was ineligible or unadmitted. |
| Ingestion | An eligible source supports the fact or relationship, but extraction omitted or misrepresented it. |
| Review or publication | Extraction captured it, but review held it or an accepted item failed to publish. Record intentional holds separately from defects. |
| Graph construction | Publication retained it, but Graph readback shows a broken path, such as a duplicate identity, wrong endpoint, missing containment edge, or lost citation binding. |
| Retrieval, packet construction, or citation readback | A usable path exists. Trace whether traversal skipped it, the final packet dropped it, or its citation failed to reopen. |

Report cited Graph reachability and delivery with exactly reopened citations
against all Gold witnesses. Also report retrieval recall over the
Graph-reachable subset so Graph gaps remain visible without counting them as
crawler misses. Mark attribution as unproven when a boundary artifact is
missing and name the artifact needed to resolve it.

### Wandering Forest result

The six-question lab comparison used Elderwyld Graph
`rev:5293c1b237a0064bd16fffd080bfa6b1`, source epoch 191, pinned Campaign 2 recap
admissions, and at most eight source ranges per question in each arm.

| Measure | Bounded ordinary Jev | Bounded Event traversal |
| --- | ---: | ---: |
| Required witnesses | 15/16 in exact packet prose | At most 5/16 in reopened citation support |
| Median dispatch to writer-ready | 17.51 s | 10.24 s |
| Median writer message tokens | 10,535 | 4,184 |

All retained references reopened exactly. The Event score credits source text
behind Graph assertions, so it is an upper bound on writer-visible coverage.
These timings describe this cohort and pin. Setup and inventory scans are
excluded. At the time of this record the exact packets, traces, and readbacks
were retained locally under `Projects/.codex/forest-core-pin.QlxKcm`. This is
an operator-local lab directory, not a repository-tracked evidence bundle; it
may not be available to another reader. Access to the original authorized
inputs and retained artifacts is required to independently reproduce the
comparison. Do not copy private campaign material into the repository.

Keep ordinary Jev as the default. Search matched the recap containing Jev's
missing eastward-turn witness, but the controller offer menu omitted it.
Expanding adjacent offers recovered that witness and displaced a previously
covered one. The Event-plus-Jev pilot tied coverage and exceeded the shared
ceiling on three questions. The pinned Graph also lacked traversable paths for
some known Events, including the Thinking Tree clearing's connection to the
Forest. Missing producer lineage leaves the cause of those Graph gaps open.

For follow-up comparisons, count unique cited ranges and overlapping bytes
alongside citation references and message tokens. Check same-session
distractors separately. Shared source support can back distinct claims.
Adopt a traversal change only when it recovers required evidence within the
shared budget while preserving previously supported witnesses and exact
citation reopening.

For authoring actions, conversation-only boundaries, and Build and Ingest
workflows, see the [Buddy actions and authoring benchmark](plan-authoring-benchmark.md).

For an ordinary Plan browser replay, select a case in the context capture
command as well as choosing the writer sink.

```bash
python -m evals.buddy_benchmark.workflow capture-context \\
  --manifest MANIFEST.json --output CAPTURE_DIRECTORY \\
  --case Q01 --writer-transport --detailed-trace --clone-app
```

The manifest's browser_capture object supplies a bundle directory, a
bundle_inventory file pin containing each relative asset path and SHA-256,
and a jev_wire file pin containing the exact successful wire exchange.
Set DMB_BENCHMARK_NODE, DMB_BENCHMARK_PLAYWRIGHT and DMB_BENCHMARK_CHROMIUM
to the local Node executable, Playwright package directory and browser
executable. Use explicit local operator auth and launch without provider credentials.
Pin a disposable local App template and the read-only Core database. With
`--clone-app`, the App DSN names the template and its evaluator role needs
database creation privileges. The command owns a unique App clone and drops
it when capture exits successfully or raises an error. Saved capture artifacts
remain on disk. A custom runner that creates its own clone must use
`disposable_benchmark_database` around the entire run and close all workers
before exiting the context. This does not remove caller-owned cohort seeds.
The driver
starts one loopback instance and submits from Buddy's ordinary Plan composer.
The exact retained Jev request must match. The GenerationEngine writer
request is captured at the local transport sink. Neither provider is called.
The browser server uses Buddy’s hosted startup garbage-collection wrapper.
Compare these timing captures with others that use the same startup policy.

The optional manifest field browser_capture.settled_pane waits for a quiet
pane before timing Send. Leave it false for immediate Send after the
controls are ready. Leave off --detailed-trace for the coarse comparison arm.

### One App clone per benchmark workstream

For a browser cohort, pin the same shared App template in every member and
run `capture-context-cohort --browser-cohort --clone-app --workers 1` with
the usual manifest and output arguments. The App DSN names the template.
The coordinator records the owned clone and manifest in `owned-app.json`,
upgrades that clone to the checked-out App migration head once, and runs
each case serially in a fresh worker. The browser starts a new conversation
for each case. The runner does not scan the owned App database. It verifies
the shared read-only Core inventory once before and once after the cohort.
Writer request bytes, citations, timings and individual results are retained.
For deep output paths, set `DMB_BENCHMARK_BROWSER_TMPDIR` to a short
existing scratch directory on the same Projects filesystem to fit
Chromium's Unix socket path.

All workers close before the ownership helper drops the exact clone and
verifies removal. If execution is interrupted, check the recorded clone
identity and teardown before allocating another. The coordinator does
not modify the shared App template or Core snapshot.

### Parallel retrieval captures

Use `python -m evals.buddy_benchmark.workflow capture-context-cohort --manifest
COHORT.json --output NEW_OUTPUT --workers 6` for independent writer-off
retrieval cases. The cohort manifest has schema
`dmb_context_capture_cohort_v1` and a `members` list of ordinary capture
manifest pins, each with `path` and `sha256`. Members must have unique case
IDs, independent prequalified App clones and the same exact Core locator and
inventory pin. The App DSN supplies the loopback server and fixture login
and each member supplies its database name and identity. Core requires a
dedicated login with SELECT and schema USAGE, no role memberships or durable
write privileges, and a session configured for read-only transactions. Grant
access to `pg_control_system()` for the cluster identity check.

The coordinator retains `native-before.json` and `native-after.json` for the
whole cohort. Worker output and timing evidence are under `members/`.
The end inventory must match the beginning one to qualify the run.
Standalone capture still verifies and retains its own snapshots.

Add `--browser-cohort` to use ordinary Plan browser Send and stop at the local
writer transport sink. Each member must pin exactly one case, its UI bundle,
and its successful retained Jev exchange tape. Set the same local browser
runtime and credential-free environment as standalone browser capture.
Add `--detailed-trace` for individual host spans and first-Jev transport
intervals. Browser marks and the writer-ready packet are retained under each
member. The coordinator still brackets the whole cohort with two inventory
scans.
