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
inline rendering, saved reopen, and answer continuation must each be observed at
the owning UI/runtime boundary. Proposal mobility and the no-premature-mutation
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
