# Negative retrieval assessment

This is an assessment core, not an ordinary-turn runner. A pass from synthetic
observations validates only the assessor. It does not prove model behavior,
complete trace capture, question quality, browser delivery, or deployment.

The caller supplies case-private expected source labels and allowed outcomes,
and independently observed results. `reads` must include all new discovery and
materialization activity in the turn, normalized to fixture-local source labels;
loading already retained dialogue or citation records is not a new read. A
complete journal is an affirmative, independently established capture property,
not merely an empty list. Unknown or unrecorded values are `None`. A partial
journal can prove an unexpected read but cannot prove no read occurred. Required
labels need source-specific proof and semantic assessment of the actual support;
a count alone is insufficient. `semantic_quality` is an independent judgment
against the case's private rubric, never an exact-string test. For clarification,
relevance to the unresolved decision, answerability, non-repetition of supplied
information, and absence of false premises are separate semantic judgments. The
actual inline component, absence of retry/error presentation, question reopen,
answer submission, completion of the original task, and reopened answer are
separate observations at the owning UI/runtime boundary. A dispatch or a
scripted pending request does not establish continuation. Proposal mobility and the no-premature-mutation
check likewise require actual boundary observations. A `False` is a demonstrated
failure; missing evidence leaves a result unproven.

The draft fixture files are development material: both splits were authored
together and share structure, so `heldout-draft.json` is not independent held-out
evidence. An independently authored held-out set, a product observation adapter,
ordinary execution and held-out qualification remain to be built. Keep grading rubrics out of producer inputs.
Retain source SHA, fixture version, provider/model, complete trace, decisions,
UI evidence, and failed observations. The existing capture-context workflow
intentionally stops before writer dispatch and therefore cannot alone establish
clarification delivery or continuation.

`trace_observation.observed_acquisitions` projects a lower bound from the actual
saved trace: Graph operations, new source passages, authored-reference reads,
and selected related-page reads. Reused historical passages are not new reads.
Even `capture_status: complete` does not establish a complete acquisition
journal: for example, `BuildJevHarness.configured_budget` calls related-page
catalog discovery before first-step selection, and that discovery is not an
individual trace observation. Evaluators must instrument and reconcile the
actual discovery and read owners before asserting zero. Unmapped acquisition
is a definite violation of a zero-read budget and otherwise remains unknown.

`capture_observation.observe` consumes the existing ordinary benchmark's saved
HTTP envelopes and correlates the request, persisted turn, one trace attempt,
and response. It validates retained HTTP bytes, recognizes only saved typed
questions, and does not infer a UI result or semantic correctness. A lower-bound
projection of the supplied user trace recorded six related-page reads and an
interrupted terminal; this is a failure observation, not a cohort rate. A
separate read-only adapter smoke against an existing twelve-turn capture reached
a completed turn with zero *observed* acquisitions; catalog coverage and this
benchmark's rubric were not established, so it is not a benchmark pass.

`summarize` reports minimum and maximum possible false-positive and missed-read
rates when a journal or source mapping is incomplete. It does not count unknown
as a pass or use model output as an independent semantic review.

`related_page_probe.observe_related_page_owners()` instruments the actual
related-page discovery and materialization functions in a serial isolated
process. It records entry even when an operation fails or a catalog is empty,
restores the functions on exit, and keeps arguments and source contents out of
its records. Combine its `acquisition_labels` with trace observations; this is
still a partial journal. The probe is process-global while installed: do not run
it against a shared service, concurrent evaluator, or live World. A focused
synthetic test confirmed that the real Build budget path invokes catalog
discovery before a controller decision; its registry was stubbed, so this is
not a model-quality or full-turn result.

`capture.capture(manifest, output)` wraps the existing ordinary
Build sequence capture, preserving its runtime, source, provider, and database
preflight. It records the partial probe separately for each turn, including a
failure before a response, and restores the patched owner functions. The wrapper
is a process-global diagnostic: use an isolated serial process and the existing
owned database procedure. Optional evaluator-side fixtures are checked against
the exact related-page catalog and saved bodies before and after each turn;
those preflight reads occur outside the product-turn probe and are never sent
as grading instructions. A mismatch stops dispatch or invalidates the run. The
wrapper refuses per-capture App cloning and selects the existing pinned cohort
path, which enforces a dedicated read-only Core login and avoids full Core
inventory scans. The executor must provide its already owned workstream App
clone and prove ownership, capacity, reset and teardown separately. The wrapper
does not seed a fixture, authorize a provider or deployment, or provide a
complete acquisition journal. Read the ordinary benchmark manifest and policy
before invoking it; Plan and the context-only writer stop are not supported.

`report.report_case` joins an existing ordinary capture to its per-case probe,
checks the request against the fixture, hashes retained artifacts, and applies
the private rubric without calling a model. Missing files are unproven. This
initial report intentionally has no authority to promote manual judgments or a
partial journal to complete. It records observed zero-budget violations and
separately reports whether the saved primary context and related-source fixture
were bound. It leaves the case unproven because the capture environment and
other required boundaries are not yet independently verified.

`fixture_binding.verify_fixture` checks the complete ordered prior dialogue and
clean page against the captured request, then validates the current turn's
native context receipt and joins it to the turn provenance through the product
owner. It rejects pagination, changed history, intervening turns, and page or
receipt mismatches. This proves primary context only; related-page inventory,
prior citations, and the capture environment still need independent binding.
An existing ordinary captured turn passed this verifier read-only; its fixture
was constructed from that same capture and is an adapter smoke, not a frozen
benchmark or model-quality result.

`build_inline_witness.generate` derives a single test from the current mounted
conversation owner fixture using guarded anchors. In a disposable UI copy it
rendered saved typed Build questions, retained an edited answer across remount,
added it to the composer, and sent the answer to a scripted pending Build
transport. Diagnostic run: 1 passed, 324 filtered, Node 21.6.2, copied locked
package dependencies, frontend lock held. Evidence and the initial matcher-only
failure are retained at `Projects/.codex/buddy-check.negative-inline.SsurDn`.
The mocked transport does not prove server completion, durable reopen of the
answer, no mutation in the server, actual model behavior, browser layout, or
deployment. Node 21 is not the repository's required Node 22 exact-source
qualification; this is diagnostic evidence only.

`controller_observations` projects only fixed choice labels and related-page vote
counts from captured *unvalidated* provider decisions, alongside provider/model
names. These are observations of model output, not proof of accepted decisions
or materialized reads; the latter are reported separately. Arbitrary model text
is not copied into the projection or sent to another model. In the supplied
failure, the one captured unvalidated opening selected `anchored`, with six
read and thirteen skip votes; the trace separately recorded six related-page
reads. Those observations do not establish why the later acquisition failed.
