# Negative retrieval assessment

This is an assessment core, not an ordinary-turn runner. A pass from synthetic
observations validates only the assessor. It does not prove model behavior,
complete trace capture, question quality, browser delivery, or deployment.

The caller supplies case-private expected source labels, allowed outcomes and
an explicit maximum number of related-page catalog discovery attempts,
and independently observed results. `reads` must include all new discovery and
materialization activity in the turn, normalized to fixture-local source labels;
loading already retained dialogue or citation records is not a new read. A
complete journal is an affirmative, independently established capture property,
not merely an empty list. Unknown or unrecorded values are `None`. A partial
journal can prove an unexpected read but cannot prove no read occurred. Required
labels need source-specific proof and semantic assessment of the actual support;
a count alone is insufficient. A mapped observed required read proves its
presence even in a partial journal; a missing read remains unknown unless the
journal is complete and fully mapped. `semantic_quality` is an independent judgment
against the case's private rubric, never an exact-string test. For clarification,
relevance to the unresolved decision, answerability, non-repetition of supplied
information, and absence of false premises are separate semantic judgments. The
actual inline component, absence of retry/error presentation, question reopen,
answer submission, completion of the original task, and reopened answer are
separate observations at the owning UI/runtime boundary. A dispatch or a
scripted pending request does not establish continuation. Proposal mobility and the no-premature-mutation
check likewise require actual boundary observations. A `False` is a demonstrated
failure; missing evidence leaves a result unproven. An observed retry/error is
retained even if no typed outcome was produced. When the rubric permits only a
clarification, an independently observed missing inline question is also retained
for an interrupted turn; neither observation invents a successful clarification.
A case allowing a movable proposal does not require an inline question for that
proposal.

The draft fixture files are development material: both splits were authored
together and share structure, so `heldout-draft.json` is not independent held-out
evidence. An independently authored held-out set, a product observation adapter,
ordinary execution and held-out qualification remain to be built. Keep grading rubrics out of producer inputs.
Retain source SHA, fixture version, provider/model, complete trace, decisions,
UI evidence, and failed observations. The existing capture-context workflow
intentionally stops before writer dispatch and therefore cannot alone establish
clarification delivery or continuation.

`trace_observation.observed_acquisitions` projects a lower bound from the saved
trace: Graph operations, new source passages, authored-reference reads, selected
related-page reads, and recognized native Graph and corpus read/search activity.
Attempt and completion events are not deduplicated into source counts; their
source identity is unmapped. Unknown native policies are not inferred. Reused
historical passages are not new reads.
Even `capture_status: complete` does not establish a complete acquisition
journal: for example, `BuildJevHarness.configured_budget` calls related-page
catalog discovery before first-step selection, and that discovery is not an
individual trace observation. Evaluators must instrument and reconcile the
actual discovery and read owners before asserting zero. Unmapped acquisition
is a definite violation of a zero-read budget and otherwise remains unknown.

`capture_observation.observe` consumes the existing ordinary benchmark's saved
HTTP envelopes and correlates the request, persisted turn, one trace attempt,
and response. It validates retained HTTP bytes, recognizes validated saved typed
questions only when a recognized Build completion validates and the response
completion matches the saved completion,
and matching validated Build proposal or native answer completions. Answer
support, proposal mobility, UI results and semantic correctness require separate
evidence. A lower-bound
projection of the supplied user trace recorded six related-page reads and an
interrupted terminal; this is a failure observation, not a cohort rate. A
separate read-only adapter smoke against an existing twelve-turn capture reached
a completed turn with zero *observed* acquisitions; catalog coverage and this
benchmark's rubric were not established, so it is not a benchmark pass.

`summarize` reports minimum and maximum possible false-positive and missed-read
rates when a journal or source mapping is incomplete. It does not count unknown
as a pass or use model output as an independent semantic review. For offline
reports, it also requires both fixture-context and capture-environment
verification before counting an observed failure or success in a cohort rate;
unbound, unverified and missing-artifact reports remain unknown. Raw observed
violations remain visible for investigation. The current report cannot verify
its capture environment and therefore cannot by itself qualify a rate. Offline
reports and direct assessor results carry distinct schema tags so missing report
verification fields do not turn a report into an eligible direct assessment.
These tags identify formats, not proof against intentional artifact tampering;
the caller remains responsible for retaining and verifying evidence.

`related_page_probe.observe_related_page_owners()` instruments the actual
related-page discovery and materialization functions in a serial isolated
process. It records entry even when an operation fails or a catalog is empty,
restores the functions on exit, and records only host-side document identity
for materialization (never the source body or model-facing metadata). `catalog_discovery_count` scores catalog attempts separately
from `acquisition_labels`, which projects materialization attempts. Both are
partial observations, including failed attempts; a count within budget does
not establish absence of unobserved work. The probe is process-global while installed: do not run
it against a shared service, concurrent evaluator, or live World. A focused
synthetic test confirmed that the real Build budget path invokes catalog
discovery before a controller decision; its registry was stubbed, so this is
not a model-quality or full-turn result.

The native probe also records calls to the corpus discovery, member-read, explicit direct-source-read and actual body-open owners. It records only entry/outcome categories,
not source identity, query or body. Corpus discovery contributes an observed
catalog attempt; member reads, direct reads and body opens are unmapped read
attempts. Nested
owner calls may count the same underlying source more than once, so these are
not distinct-source counts. Imported aliases or other owners can bypass the
probe; its coverage and the report remain partial even when no calls appear.

`capture.capture(manifest, output)` wraps the existing ordinary
Build sequence capture, preserving its runtime, source, provider, and database
preflight. Probes are installed only around the actual turn POST, not the
runner's history, conversation setup or subsequent trace reads. They record
`not_started` if that POST was never entered, and retain partial observations
if it fails. On exit the records are detached snapshots, so retained wrappers or
late background completions cannot alter them. Async clients are unsupported:
an async method is rejected before dispatch, and an unexpected awaitable
response is marked `dispatch_uncertain`. Hooks are removed when the POST exits.
Work that occurs after the response, outside this process, through stale aliases or other owners remains
unobserved. Legacy probe records without a status wrapped the broader capture
and cannot be assumed to have the narrower timing boundary. The wrapper
is a process-global diagnostic: use an isolated serial process and the existing
owned database procedure. The caller must pass the independently frozen
`expected_manifest_sha256`; a missing or mismatched digest is rejected before
dispatch. This pin does not by itself establish independent authorship or
fixture provenance. Optional evaluator-side fixtures are checked against
the exact related-page catalog and saved bodies before and after each turn;
when supplied, the caller must also pass `expected_fixture_sha256`, computed
from the frozen mapping with `fixture_sha256`. Capture snapshots the canonical
JSON inputs and retains the set and case digests outside model-visible input.
those preflight reads occur outside the product-turn probe and are never sent
as grading instructions. Catalog pointers must belong to the requested World,
be distinct from the primary page and each other, and have valid revisions
before materialization. A mismatch stops dispatch or invalidates the run. The
first case may reuse an already seeded synthetic active conversation if its
complete saved dialogue matches the fixture. The wrapper also checks the
ordinary runner's own pre-dispatch history read, and retained-history binding
checks the actual prior dialogue after capture. The wrapper does not seed the conversation,
and concurrent history changes must invalidate the binding. The wrapper refuses
per-capture App cloning and selects the existing pinned cohort
path, which enforces a dedicated read-only Core login and avoids full Core
inventory scans. The executor must provide its already owned workstream App
clone and prove ownership, capacity, reset and teardown separately. The wrapper
does not seed a fixture, authorize a provider or deployment, or provide a
complete acquisition journal. Read the ordinary benchmark manifest and policy
before invoking it; Plan and the context-only writer stop are not supported.

`seed_dialogue.seed_dialogue` seeds frozen synthetic user/assistant pairs via
the conversation owner after checking the exact App-clone lease, a fresh
`negative-seed-<uuid>` World, and the supplied pinned page snapshot against
the persisted page owner. The caller must provision the synthetic World and
page before calling it.
It refuses an existing conversation and does not reset or retry a partial seed.
The owner-bound predecessor-source diagnostic round-tripped the development
placement dialogue with Build provenance; it did not exercise full capture.

`provision_fixture.provision_fixture` creates a uniquely named synthetic World
and its primary and related pages after verifying the workstream App lease. It
checks saved page bytes and related-page inventory through the owning services;
the caller supplies an isolated existing root and must configure the related-page
service to use that same root. Partial failures are retained, never reset or
retried automatically. The helper does not dispatch a model, construct a full
capture manifest or establish complete acquisition coverage. It does not
provision or activate a native Graph binding: the resulting World fails the
ordinary binding resolver with `native_graph_binding_missing`. A provider-free
diagnostic subsequently bound the same synthetic World to its own in-memory
Core through the App binding owner, then checked the real binding, identity and
principal access owners. A follow-up admitted and reopened the exact page in the
same memory Core using a test-selected GM audience; principal-to-audience
derivation remains unproven. This does not yet exercise an ordinary Build turn or
establish live-model or shared-Core qualification. A separately verified
binding and prompt-boundary audit are required for a real capture; do not write
to the shared read-only Core to supply one.

When the ordinary `answer-http` artifact includes its monotonic
`elapsed_ms`, the report exposes the request cycle through response-envelope
processing, including any context wrapper. This is not total browser delivery time and is not independently
verified while the capture environment is unqualified. Missing timing stays
unknown; invalid or non-finite values are rejected.

`report.report_case` joins an existing ordinary capture to its per-case probe,
checks the request against the fixture, hashes retained artifacts, and applies
the private rubric without calling a model. Supply the frozen mapping as
`fixture_set` and its independently supplied digest as `expected_fixture_sha256`;
the report checks the mapping digest and case membership as well as the retained
case pin. A missing or mismatched input leaves fixture context unverified.
Missing files are unproven. This
initial report intentionally has no authority to promote manual judgments or a
partial journal to complete. It records observed zero-budget violations and
retains available terminal status and separate discovery/materialization
attempt and exception counts even if required artifacts are missing; those
partial observations cannot qualify a cohort rate. It separately reports
whether the saved primary context and related-source fixture
were bound. Related-page trace and probe identities map to fixture labels only
through the validated stable pre/post inventory; unmapped material remains
unknown for positive controls. It leaves the case unproven because the capture environment and
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
conversation owner fixture using guarded anchors. The current witness renders
saved typed Build questions, submits an answer to a scripted completed transport,
and remounts with simulated saved question, answer and reply. It disables the
owner test's automatic Details-click observer and opens Details explicitly.
The generated test is byte-identical to the retained witness that passed twice
(1 passed, 324 filtered), using Node 21.6.2, copied locked dependencies and the
frontend lock. Evidence and prior inconsistent runs are retained at
`Projects/.codex/buddy-check.inline-continuation.666msV`. Scripted transport and
history do not prove server completion, durable persistence, no mutation,
actual model behavior, browser layout or deployment. Node 21 is not the
repository's required Node 22 exact-source qualification.

`controller_observations` projects only fixed choice labels and related-page vote
counts from captured *unvalidated* provider decisions, alongside provider/model
names. These are observations of model output, not proof of accepted decisions
or materialized reads; the latter are reported separately. Arbitrary model text
is not copied into the projection or sent to another model. In the supplied
failure, the one captured unvalidated opening selected `anchored`, with six
read and thirteen skip votes; the trace separately recorded six related-page
reads. Those observations do not establish why the later acquisition failed.

`build_http_witness.generate` derives an evaluator-only red/green witness from
`tests/test_surface_native_build_ordinary.py`. Its ambiguous-placement case
requires a completed typed question, no related-page materialization, no
proposal, and unchanged primary page through the ordinary HTTP/APP route. The
owner fixture injects synthetic controller votes and an in-memory native
repository; it cannot prove actual model behavior or deployed UI. Do not run
its default `application_state_dsn` fixture: that fixture creates multiple
physical databases and is paused under the current benchmark resource policy.
The generated witness imports an evaluator fixture that refuses anything but
a live, exact-source workstream owner and its pinned App clone. That fixture
performs a read-only identity check and never creates or drops a database; its
owner/worker integration still needs review. Three provider-free runs on the
same owned clone failed the typed-question expectation with HTTP 409
`build_contextual_placement_unresolved`. The latter two checked that the page
was unchanged and no proposal existed before asserting the response; the
instrumented run observed one catalog discovery and four materialization calls
over two related pages. Case 3 additionally retained the serialized synthetic
controller input before its mock transport. The pinned source, owner ledger,
derived witnesses and failed logs are recorded in the
`HANDOFF-RETRIEVAL-negative-intent-benchmark.md` provider-free baseline.
These runs are predecessor-source diagnostic evidence, not a live-model cohort,
current-head qualification or deployed UI evidence.

`frozen_placement_witness.generate` derives the separate frozen development
placement witness from the same owner test and a caller-pinned fixture file.
It verifies the related-page inventory around the measured turn and expects
zero discovery or materialization. The generated test requires the verified
owned App clone and scripted provider/in-memory Core fixture. On predecessor
source it intentionally failed that budget after one discovery and two
materializations, with the proposal path completed. The same proposal was
moved through the App review owner, and the moved position was bound into
apply preparation while the page remained unchanged. It is not a live-model
cohort, independent held-out evaluation, or exact-head qualification. The
owner fixture's later page save simulates author action; the owner asserts the
page was unchanged before that action.
The optional `related_page_vote` parameter selects a scripted `read` (default)
or `skip` vote without changing the related-page fixture. On the same
predecessor source, the skip control still discovered the catalog but recorded
no materializations. This comparison diagnoses the host path under scripted
votes; it does not measure a model's decisions.

`native_graph_probe.observe_native_graph_owners` records direct calls to the
native query, selected-read, authored-reference-read, context-reopen and
authored-corpus-source-read owners.
It retains owner and outcome only, never query text or source bodies. The
ordinary capture writes a separate partial probe artifact; the offline report
summarizes it without upgrading acquisition coverage or a cohort rate. Other
owners and other previously captured call aliases can bypass these wrappers, so zero
records do not prove that Graph or source acquisition did not happen.
An observed selected Graph, authored Graph, or authored corpus read attempt is scored as an unmapped
acquisition, which proves a violation for a case allowing no reads; it cannot
establish which required source was read. Query preparation alone is not scored
as a source read.
The existing preimported `native_authored_references` reader aliases are observed
when it still points to the original owner; independently replaced aliases are
left untouched.
