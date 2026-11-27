# Lab and evaluation

This directory holds experiments, regression fixtures, and evaluation evidence.
Start with the suite that owns the question you are testing.

## Actions and workflow coverage

- [Agent action catalog](plan-authoring-benchmark.md#action-catalog): the
  canonical inventory of ordinary Agent choices, operator actions and requested
  capabilities, with the strongest verified boundary and remaining proof.
- [Workflow decision benchmark](plan-authoring-benchmark.md#workflow-decision-benchmark):
  cases for deciding when to discuss, retrieve, propose, or refrain from acting,
  including destination and side-effect checks.
- [Right Action at the Right Time coverage matrix](right-action-coverage.md):
  fixture specifications for direct, contrast and multi-step workflow cases.
- [Adventure-to-follow-up benchmark](adventure-to-follow-up-benchmark.md):
  the joined intake, Plan, Play, Combat, recap and cited follow-up journey.

An inventory entry or fixture is not itself a passing end-to-end result. Read its
evidence and open boundaries; component or scripted proof does not establish an
ordinary live workflow. The [ordinary benchmark workflow](../Docs/Guides/ordinary-benchmark-workflow.md)
explains capture, offline reporting and independent assessment.

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

To test recovery after a lost Build confirmation, use the live Build fixture
with both `browser_capture.confirm_save` and `browser_capture.lose_confirm_ack`
set to `true`. The browser drops the response to the bound confirmation
after the owning server has processed it. The capture retains that receipt
and compares committed page and proposal readbacks before and after reload.
If the page saved once and the bound review remains applying without a
confirmation request, the harness also exercises Buddy’s Check insertion
control after reload. The same interception stays armed until that exact
confirmation returns. After withholding the response, the capture reopens
the receipt and committed page and verifies that no second confirmation or
page change occurred. The browser request start timestamp can be unavailable
for the aborted request. The capture retains it as null and independently
records the trusted Check insertion click and the matching fetch in the
same browser clock. A fetch observed before the click fails the control. A run without a withheld receipt leaves recovery
unverified.

For the known-failure contrast, set `browser_capture.terminal_build_failure`
on an owned ordinary Build capture with Save disabled. The injected failure
occurs after the proposal writer response and before the proposal becomes
reviewable. The capture checks the durable failed proposal and turn, reopens
the exact turn in the browser, records whether Retry or Check insertion is
offered, and verifies the page and send count. The browser leaves the Retry
button untouched.

For a provider-free Play Choice control, use ordinary `capture --case
<case-id> --clone-app` with a pinned saved Plan and
`browser_capture.play_choice` containing the Run ID, Run revision, current
scene ID, Choice ID and alternate option ID. The browser clicks the exact
option, reopens its selection and records the progress request. Preselect the
same active Run in the isolated fixture. The harness admits the read-only
Graph projection and exact active Run synchronization for that World, then
independently checks the Run, unchanged active pointer, saved Plan and zero
assistant sends. This
measures an operator action and produces no assistant action-choice score.

To measure Buddy's action choice separately, use the shared response capture
with an ordinary `play` request template in an owned App clone. Pin the
active Run, edition and exact current scene and beat. The harness records
the assistant response and owner readbacks of Run progress, edition, active
pointer, Plan and Play proposal inventory. It does not click an operator
control or treat the response as proof of a mutation.

For an unsent draft recovery control, use `capture --build-fixture --case
RECOVERY-1 --clone-app` and set `browser_capture.unsent_draft` to `true`.
The browser fills the composer and reloads it without clicking Send. The
harness records whether the exact draft returns, any attempted turn POST,
the conversation and committed page before and after, and zero provider calls.
Use a fresh isolated browser and omit provider credentials.

For a live Plan placement case, use the saved Plan editor with a pinned
selection and the normal provider configuration.

```bash
python -m evals.buddy_benchmark.workflow capture \
  --manifest MANIFEST.json --output CAPTURE_DIRECTORY \
  --case PLAN-CARDS-1 --live-plan --clone-app
```

Pin the Plan revision and content digest, browser bundle inventory, and exact
`browser_capture.selection_text`. The driver selects a unique matching passage
in the mounted editor. The harness checks the browser's placement catalogue,
selection, Plan revision, and conversation pointer before forwarding the turn.
It retains the ordinary response, history, and committed Plan readback. A
rejected placement is retained separately as fixture evidence. Keep scoring
Gold local. This mode stops at review, before applying a proposal.

To reuse a conversation already restored in the owned App fixture, pass a
`browser_capture.plan_history` evidence pin. Its JSON contains a
`conversation_id` and an ordered `prior_turns` list with `turn_id`, `sequence`,
`user_text_sha256`, and `assistant_text_sha256`. The harness reads back the active
conversation and rejects any divergence before Send. For an insertion at the
first text position, set `browser_capture.at_document_start` to true and omit
`selection_text`. The browser positions the caret and the harness checks the
captured range and exact committed text digest before dispatch.

For a private Image Studio preview, use the live Build browser mode and set
`browser_capture.image_preview` to true. Omit selection, unsent-draft and
confirmation fields. The case question is the exact image description. The
driver opens Image Studio, generates once and decodes the staged image. The
capture compares the committed page, complete saved image library and
conversation before and after, and independently reopens the staged asset.
Use an approved, configured image route in isolated benchmark state.

For Image to image, add `browser_capture.image_parent` with the exact
`asset_id` and `content_sha256`. The case question is the edit direction.
The shared capture binds the mounted POST to that parent, verifies the decoded
child against the staged record, and reopens the original before and after.

For a saved-image placement, also set `browser_capture.image_placement_anchor`
to an exact, unique destination paragraph. Use an owned App clone with image
provider credentials unset. The browser opens the existing library asset,
places it after the paragraph, waits for one ordinary page commit,
and reloads. The capture verifies the resulting committed page independently.

An ordinary Build sequence can reuse a restored active conversation by
pinning the same history shape in the top-level `build_history` field. Use
response capture on an owned App clone. The harness records and verifies the
complete active prefix before dispatch, then retains each newer turn and its
ordinary citation readbacks. For an interrupted Build turn, pin
`lifecycle_status: interrupted` and use a null assistant digest when the saved
turn has no reply. In-progress turns cannot be admitted.

An owned Build response capture can opt into a lore-page confirmation by
setting `lore_confirmation.foreign_conversation_id` to a different retained
conversation in the fixture. The harness records rejected confirmations,
presents the delivered review, confirms once, reopens the committed revision
and exact citations, and checks that a repeated confirmation returns the same
receipt without saving a second page.

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

### Interrupted workstream clone recovery

A retained clone whose creating process has exited must not be silently
replaced. The recovery option of `disposable_benchmark_database` takes the
pinned old owner receipt and original cooperative lock and reuses the exact
clone for the entire resumed context. A caller must maintain a fresh owner and
worker receipt under that lock and explicitly record acceptance or abandonment
before cleanup. Exceptions or missing acceptance retain the clone. Receipt and
lock pins, old process/worker closure, database identity and live connections
are checked; an explicitly pinned current loopback port may differ after a
container restart, but the template and clone database identities must still
match the original cluster. Ambiguous or still-running old workers are refused. This is not a
cross-host lock or a replacement for worker supervision. Inspect the retained
ledger and exact clone before any recovery attempt.
