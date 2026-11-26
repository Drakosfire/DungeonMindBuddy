# RETRIEVAL: negative intent benchmark

Status: ACTIVE — user authorized the benchmark goal in this conversation. This
brief assigns the first serial, eval-only slice to `codex/negative-retrieval-benchmark`,
based on `origin/main` c3a2ae6032b0f16fc19d21be14759a0a8607782b (rebased from 42a524ade after checking the shared native-writer change). Checkout:
`/home/drakosfire/Projects/.codex/793a/DungeonMindBuddy`. The diagnostic
owner now holds one disposable App clone on loopback port 33351; the existing
Core snapshot is read-only. No model, provider, or production state was used.

## Outcome and lease

Build an independently reviewable evaluation of unnecessary acquisition and
clarification delivery. Expected write lease: this handoff, new files under
`evals/negative_retrieval/`, and new focused tests under
`tests/evals/test_negative_retrieval*.py`. Do not edit shared runners, runtime,
frontend, dependency locks, or active owners' files in this slice. Existing
AW10 is a related positive-context control, not evidence of this new case.
The CI owner separately split the one classification entry documented below;
that exception does not grant a broader shared-file lease.
The protected behavioral invariant is that already sufficient context is not
supplemented by unnecessary discovery or reads, while genuinely needed evidence
is not suppressed. An actionable clarification or a safe movable proposal can
both be valid where the case permits them. No mutation precedes user action.

Critique: a zero read count is meaningless without a complete acquisition journal;
a clarification displayed outside the saved turn or a scripted component fixture
does not establish ordinary delivery; a scorer must not count missing evidence
as success. Model-facing fixtures must not contain private grading answers or
host metadata. Positive retrieval controls must be judged against required
witnesses, not mere activity. Semantic question quality requires an independent
assessment, not exact wording matching.

## Topology and verification

Serial. Slice 1 is eval-only on current main; inspect open PRs and leases before
claiming any shared path. PR #4573 merged as
`5c8c859f337fce63978206cacf6f43e2df3bce75` into its pinned serving lineage,
clearing the successor's predecessor-merge gate without establishing deployment.
Its handoff requires a bounded routing assignment pinned to the then-current
serving parent and a shared Plan-driver lease check before editing. PR #3867 owns
related Build targeting work. This slice neither changes nor dispatches either.
Subsequent runtime/delivery fixes require their
own pinned ownership and sequencing after this benchmark identifies failures.
Merge and deployment require separate authority.

The subsequent serving writer PR #4612 merged as
`f2645348438b7322d41062e1cc5e213aa45ad36f`, satisfying its merge prerequisite.
The source-free routing handoff at `e5c6e7d393c46ade5a1be5d4d7c40427fa3c8256`
still records a BLOCKED design/lease, with a possible no-Plan-driver-write path
under investigation. Production activation and signed-in acceptance remain
separate; neither the merge nor that possible design activates the routing lane.
The new V3 writer's prompt cleanup does not qualify predecessor or other roles
for live provider dispatch.

Validate scorer and fixture integrity with focused tests, including false pass,
missing evidence, zero-read, required-read, and clarification/proposal controls.
Run actual ordinary runtime and UI integration on isolated exact source when the
necessary harness and environment are qualified; distinguish those results
from scripted assessment. Retain exact pins, complete traces and failures.
At qualification use repository-mandated exact-SHA boundary checks. The final
goal additionally requires held-out cases, user-facing inline continuation and
reopen, and deployed smoke evidence; this brief does not claim those achieved.

## Shepherd naming regression checkpoint

The user reported a creative naming request that took 241 seconds and read 11 related pages, 16 full documents, 24 sections, two assertions and one source search before producing a name-list preview. Its trace is private and remains outside the repository. The controller repeatedly selected `finish_with_gaps` while including candidates; the serving selector makes included candidates take precedence over the global finish fallback. This is evidence of an over-retrieval path, not proof that every selected source was irrelevant or that a specific change will fix it.

`dev-creative-names` is a synthetic development analogue with a supplied speculative premise, a request for ten names and several plausibly related distractor pages. Its private rubric expects an answer, no premature page mutation, zero catalog discoveries and zero reads, with semantic quality judged separately. It is a development case, not a replay of the private trace or an independent holdout. Its shape must not be shown as a benchmark key or grading rule to the product model. Existing `dev-research` remains a positive required-ledger-read control. Before claiming a live pass, instrument all discovery and materialization owners, verify the capture journal is complete, bind the fixture and runtime, and run independently held-out cases; a partial trace only proves a lower bound.

## Native corpus owner observation

The negative capture's partial native probe now records the actual corpus
capture, member-read, direct-source-read and body-open owner calls in addition to the
previous Graph and authored-reference owners. A corpus capture counts as a
known discovery attempt; a member, direct read or body open is an unmapped
read attempt.
Nested calls can count one underlying source more than once. The probe captures
no arguments, source IDs, query or body, and does not prove absence of work by
other owners or stale aliases. Offline reports still cannot qualify the capture
environment or a zero-read rate. Coverage is a diagnostic improvement, not a
complete acquisition journal. Focused tests exercise owner wrapping, errors, cleanup, privacy and report
attribution; an actual in-memory corpus capture also verifies nested body-open
observation. An ordinary product-turn witness is still required.

## Turn attribution boundary

The original partial probes wrapped the full capture case, including history,
conversation setup and post-response trace reads. This could attribute those
operations to the tested turn. The evaluator now installs both probes only
around the turn POST, forbids a second dispatch in one capture and records
`not_started` when the POST was not entered. It retains failed-POST records and
restores hooks before the runner continues. Detached snapshots prevent late
alias calls and background completions from changing recorded POST-window rows.
Async client methods are rejected before dispatch; an unexpected awaitable
response is rejected and marked `dispatch_uncertain`. Legacy records without
this status remain broad-window evidence. This is still partial: asynchronous activity
after the response, subprocesses, stale aliases and other owners can escape;
no zero-acquisition pass follows from an empty POST window.

## Diagnostic checkpoint

The question observer now validates the containing recognized Build completion,
not only the question object, before accepting matching saved and response
evidence. Provider-free predecessor HTTP case 77 passed with the real saved
question; catalog discovery remained an observed zero-budget violation. Evidence:
`Projects/.codex/buddy-check.negative-inline.SsurDn/http-owner/session/case-77`.

Question recognition now validates the typed question object and requires the
saved completion to match the HTTP response. Provider-free predecessor HTTP
case 74 confirmed this on the frozen ambiguous case. The witness observed the
question but also catalog discovery, so the zero-discovery budget remains red;
it is not a qualified benchmark pass. Evidence is retained under `Projects/`
`.codex/buddy-check.negative-inline.SsurDn/http-owner/session/case-74`.

The observer now recognizes a validated non-object-only native Build answer
whose response and saved completion agree. Required support and semantic quality
remain separate unknowns. Provider-free predecessor case 73 exercised the frozen
related-ledger positive control with correlated history and observed the answer.
Case 70 used an outdated synthetic writer key and case 72 omitted correlation
fields; both failed witnesses are retained alongside cases 71 and 73 under
`Projects/.codex/buddy-check.negative-inline.SsurDn/http-owner/session/`.
These use scripted providers and synthetic memory Core, not live-model evidence.

The offline observer recognizes a completed, validated Build proposal completion
only when the response and saved history agree; it does not infer proposal
mobility. Provider-free predecessor HTTP case 69 exercised this correlation
against the real proposal owner. Case 68 failed in its witness because the owner
helper returned no case object; both are retained under `Projects/.codex/`
`buddy-check.negative-inline.SsurDn/http-owner/session/case-68` and `case-69`.
This uses synthetic binding, in-memory Core and scripted providers.

The trace projector now recognizes the fixed host native read/search progress
policies as unmapped attempts. Case 67 used a provider-free predecessor HTTP
native-source turn and observed six matching activity events, all projected;
attempt and completion events are not counts of distinct sources. Evidence is
retained under `Projects/.codex/buddy-check.negative-inline.SsurDn/http-owner/`
`session/case-67`. Other owners remain uncovered, so absence stays unproven.

The authored corpus-source path is now included in the partial owner probe and
scored as an unmapped read attempt. In provider-free predecessor-source HTTP
case 64, a saved authored-source body read was absent from the context trace and
the trace projector observed zero acquisitions. Case 66 used the updated probe
and observed that owner once on the same synthetic path; case 65 failed in the
witness's missing import before exercising it. These cases use a synthetic App
binding and in-memory Core, and establish neither complete acquisition coverage
nor model quality. Retained evidence: `Projects/.codex/`
`buddy-check.negative-inline.SsurDn/http-owner/session/case-64` through `case-66`.

The process-local native probe now also covers the preimported authored-reference
reader when that alias still points to the original owner; other acquisition
paths remain unobserved. A provider-free predecessor-source diagnostic used the
existing synthetic App clone and in-memory Core to prepare a query and read a
selected statement with its expected support. Case 62 passed and recorded both
calls; its binding was a synthetic test binding, not the managed product binding.
Case 61 failed at the resumed owner's ledger guard before database access and is
retained. Evidence is under `Projects/.codex/buddy-check.negative-inline.SsurDn/`
`http-owner/session/case-61` and `case-62`. This does not qualify a cohort or
establish complete acquisition coverage.

Re-anchor: merged main `6edfc8270ca0da36b8061f70699c710f8edaa00e`
into this eval lane. The focused evaluator suite passed 44 tests using the
pinned dependency sources and the CI inventory passed in the merged working
tree. These are not the repository's exact-source hosted verifier, and the
runtime and UI observations below remain tied to their stated predecessor
sources. The merged main's action-catalog policy applies to subsequent
product-action changes; this slice continues to own evaluation only.

Native Graph observation is now a separate partial, process-local capture
artifact. It records direct calls and outcomes for native query, selected read,
authored-reference read and context reopen, without retaining arguments or
source bodies. Offline reports summarize the artifact without asserting a
complete acquisition journal or affecting a cohort rate. Captured aliases and
other Graph, corpus and lookup owners can bypass the wrappers.

Case 55 exercised the candidate probe against the actual native query owner and
a synthetic memory-Core binding (1 test passed). Cases 56–60 exercised it
around a frozen placement HTTP witness on predecessor `d008072`. The initial
case included a test-selected Graph reference; cases 57–60 removed that extra
request reference. In case 60, the dispatch returned HTTP 200 with one proposal
and an unchanged page, while the direct native query owner returned once. Its
dispatch-scoped memory-Core counters recorded one head read, one revision read
and three source-view opens; the response retained a pending native query with
authority. The related-page probe separately recorded one catalog discovery
and no materializations, leaving the zero-budget test red. These are scripted
controller/writer, local-operator, synthetic memory-Core observations; they do
not prove a completed Graph search, live-model decision, complete coverage,
hosted authentication or current-head behavior. Workers, generated tests and
logs remain under `http-owner` and `http-owner/session/case-55` through
`case-60`.

Case 32 tested the runtime owner's proposed synthetic memory-Core path on the
retained owned App clone and predecessor product source `d00807237abff7a190960cef85796a7faa4c8166`.
The frozen placement fixture first reproduced the missing-binding refusal. The
test assigned an owner to its fresh synthetic App World, checked the real access
owner allowed that principal and denied an unrelated principal, initialized an
in-memory Core with the same World ID, and used `bind_native_graph` to validate
and persist its exact native head. Both actual managed binding and source identity
resolvers returned that same World and binding version; native head revision
readback and prior-dialogue seeding passed (1 test). The owner did not patch the
binding or access return values. Worker, derived test and log are retained under
`http-owner/session/case-32` and `http-owner`. This is synthetic memory-Core,
provider-free predecessor evidence: it does not prove an ordinary Build request,
source readback, current-head or shared-Core behavior, model quality, or UI.
The owner separately confirmed the schema-version prompt leak; live provider
dispatch on the predecessor remains held pending final serialized-request audit.

Case 33 repeated that synthetic binding and admitted the frozen primary page
into the same in-memory Core using its native source owner. Opening the source
at the resulting head returned the exact page text and digest (1 test). The
earlier real App owner/foreign-principal checks also passed, but the Core read
used a test-selected GM audience: it does not prove that an ordinary Build
request derives that audience from its principal. It remains provider-free,
predecessor-source evidence, not a shared-Core or live-model qualification.
The worker, derived test and log are retained under `http-owner/session/case-33`
and `http-owner`; no provider or shared Core was used.

Case 34 extended case 33 through the actual native `prepare_query` owner with
the real managed binding resolver and the same in-memory repository. After a
separate real App owner-access check, an explicitly constructed GM principal
produced a query pinned to the same managed World, native World, binding version
and current head; opening the admitted page through that query's pinned source
context returned the exact body and digest. A constructed player-role principal
was rejected (1 test). The diagnostic configures only the isolated root and
in-memory repository; it does not patch binding or access results. Worker,
derived test and log are retained under `http-owner/session/case-34` and
`http-owner`. This does not exercise HTTP authentication, integrated App access
inside a Build turn, a live provider, shared Core, current head or UI.

Case 35 extended the frozen placement HTTP skip-vote witness with a real
synthetic App binding to its own memory Core head and real managed binding and
source identity resolvers. The disposable test used the real catalog owner to
prepare an unbound local-operator-owned World, and checked owner access before
the request; it restored the fixture's substituted native binding function to
the real one. The local-operator-authenticated HTTP proposal was created, moved
and prepared without a premature page mutation; pre/post related inventory
matched. The zero-acquisition assertion remained red with one catalog discovery
and no materializations. Worker, generated test and failure log are retained
under `http-owner/session/case-35` and `http-owner`. Controller and writer were
scripted, Core was memory-backed and product source was predecessor `d008072`.
The preflight access check is separate from the HTTP path; this does not prove
hosted authentication, a live-model decision, current-head behavior or UI.

Cases 45–46 exercised the frozen `dev-ambiguous` replacement request and page
through the ordinary HTTP owner with the actual synthetic App binding and no
authored Graph reference in the request. The controller was scripted to
`clarify_request` and skip the unrelated related page; the scripted writer asked
which of North or South was intended. Case 45's fake transport incorrectly
assumed a one-line draft and produced a 503; that fixture failure is retained.
Case 46 corrected its multiline and source-free assertions. The endpoint returned
HTTP 200 and the active-messages endpoint contained the typed saved question;
the primary page and pre/post related inventory were unchanged. The zero
retrieval budget failed on one catalog discovery and no materializations.
The workers, derived tests and logs remain under `http-owner` and
`http-owner/session/case-45` and `case-46`. This is predecessor `d008072`,
synthetic memory-Core, local-operator and scripted-provider evidence. It does
not establish a model's intent choice, independent semantic judgment, inline UI,
answer continuation, exhaustive acquisition coverage or current-head behavior.

Cases 47–49 submitted the direct answer `North.` to that frozen ambiguous
exchange. Case 47 failed in an inherited fake-transport assertion that required
Graph evidence for discussion; it is a test-fixture failure, not a product
failure. Cases 48–49 corrected that assertion. In case 49 both question and
answer returned HTTP 200, were saved and remained in library readback after
archival, and the page stayed unchanged. Each turn recorded one catalog
discovery and no materializations; the original zero-retrieval assertion
remained red. No proposal was created. The follow-up controller was explicitly
scripted to `discuss`, so this is not evidence that a live model would fail to
complete the replacement; completion of the original task remains unproven.
Workers, generated tests and logs are retained under `http-owner` and
`http-owner/session/case-47` through `case-49`. This remains predecessor-source,
synthetic memory-Core and local-operator evidence, without inline UI or live
provider qualification.

Cases 50–53 exercised frozen `dev-research` as a required-evidence positive
control with the real synthetic App binding, memory Core and a scripted
`source_lookup`/read decision. Cases 50–51 failed in the fake writer because it
looked for the ledger under incorrect input keys. Case 52 established that the
exact ledger text was in serialized writer input under `related_pages`, but its
deliberate non-answer failed the answer assertion. Case 53 used the offered
local selector and exact source quote: HTTP returned 200, one persisted related
page read matched the frozen ledger, the writer input contained its text, and
the host accepted the scripted answer of two copper pieces on market days
(1 test). Pre/post related inventory and the primary page were unchanged; the
probe recorded one catalog discovery and two materializations of the related
page. Workers, generated tests and logs remain under `http-owner` and
`http-owner/session/case-50` through `case-53`. Some inherited console markers
say `ambiguous`; the fixture pin and generated test select `dev-research`.
This is predecessor `d008072`, local-operator and scripted-provider evidence,
not a live-model decision, independent semantic review, full acquisition
journal, current-head qualification or cohort rate.

Case 54 used the same frozen ledger question and real synthetic binding, but
scripted the related-page vote to `skip` while keeping `source_lookup`. The
HTTP turn completed with a scripted request to inspect the ledger rather than
an invented toll. No related-page read event or materialization was observed,
and the exact ledger body was absent from the writer input; one catalog
discovery was observed (1 diagnostic test passed). Pre/post inventory and the
primary page stayed unchanged. The worker, generated test and log are retained
under `http-owner` and `http-owner/session/case-54`. The compared positive
case 53 did read and include the ledger. Both use predecessor source, scripted
providers and memory Core. The journal is partial, so the skip control cannot
prove global absence of acquisition or contribute a qualified missed-evidence
rate; it is not a live-model choice or independent semantic assessment.

Cases 36–37 extended the prior scripted saved-question and answer witness with
the real synthetic App binding and source-identity resolvers against memory
Core. Case 36 failed because the diagnostic incorrectly expected a lifecycle
field in the library projection; that failed log is retained. Case 37 used the
saved-turn owner for status and passed: the local-operator HTTP question result
was typed and saved, a follow-up answer returned HTTP 200 and saved a completed
turn, the question and answer remained in library readback after archival, and
the page remained unchanged (1 test). Owner access was checked separately before
dispatch. Workers, generated tests and logs remain under `http-owner` and
`http-owner/session/case-36` and `case-37`. Controller and writer were scripted,
product source was predecessor `d008072`, and the question arose from a
reviewed-step fixture. This does not establish completion of the original task,
hosted authentication, live-model quality, current-head behavior or inline UI.

Cases 38–40 extended the same real-binding question witness to a follow-up
message containing the answer plus an explicit request to propose the lamp
detail. Case 38 failed before dispatch because its test attempted to reuse a
write capability absent from the base request. Cases 39–40 used a fresh
capability from the existing draft and passed. In case 40 the completed HTTP
turn created a proposal, the review owner moved it, apply preparation retained
the moved position, the page remained unchanged, and question and answer were
available after archival (1 test). Failed and passing workers, generated tests
and logs remain under `http-owner` and `http-owner/session/case-38` through
`case-40`. Routing and writer outputs were scripted, the follow-up explicitly
requested the proposal, and product source was predecessor `d008072`. This
demonstrates continuation plumbing, not independent model intent, actual apply,
hosted authentication, current-head qualification or inline UI behavior.

Cases 41–43 prepared a component-contract replay from the same controlled
question, answer and proposal flow. Case 41 failed after the proposal checks
because the capture helper omitted a `Path` import; case 42 corrected the helper
and retained a library projection. Case 43 instead fetched the real
local-operator-authenticated active-messages HTTP endpoint before archival;
its three-message response contained the saved typed question and answer and
has SHA-256 `80fc7b40f09389141c20dd3519c2359a4c87b44ceb1a211f45ecaba36f10e7b3`.
The full controlled flow passed (1 test). A mounted-component replay of those
exact synthetic bytes is prepared under
`Projects/.codex/buddy-check.inline-real-replay.Zmi5uy`, but has not run: the
first lock attempt refused and a 30-second wait expired while another live
frontend verifier held the shared lock. Do not claim UI evidence from this
prepared replay. The capture remains scripted-provider, memory-Core and
predecessor-source evidence, not a live-model, current-head or deployed run.
The case workers, generated tests and logs remain under `http-owner` and
`http-owner/session/case-41` through `case-43`.

The first mounted replay eventually acquired the frontend lock and failed to
find the question component. It used case 43's active-messages bytes but
incorrectly supplied empty detailed history, so that result does not identify a
product defect. Case 44 captured matching actual active-messages and detailed
history HTTP responses in one controlled flow (1 server-side test passed):
SHA-256 `2e14ab42a36a045abb19391659cb627964b6146e1e00617641ab55d5c4512bb2`
and `e3df29abb1326a74a9efc07d1f72cbea15754c6170a3a693de05a4e154ca3b19`.
The matching-payload UI replay is prepared in the same isolated directory but
its 30-second lock wait expired before Vitest started. The first failure and
new attempt remain in `replay-attempt6.log` and `replay-attempt7.log`. Neither
establishes an inline result; this is synthetic scripted-provider predecessor
evidence, not a live browser/server session or current-head qualification.

The matching-payload replay subsequently acquired the shared frontend lock and
passed (1 test, 325 filtered): the mounted component rendered the captured typed
question and saved answer, accepted an edited answer into the composer, and
showed no retry prompt. The replayed component file SHA-256 was
`b002f5a3fa484ef3e6dfb05beccb06ef85a0ef1c42473f635f589987664a223e`,
matching the benchmark checkout; the log is `replay-attempt9.log` in the
isolated replay directory. The exact case 44 HTTP responses were replayed via
mocked transport with their matching detailed history. This was a mounted
component diagnostic with Node 21.6.2 and copied matching-lock dependencies;
it did not send the edited answer to the server, exercise a browser or live
provider, or satisfy Node 22 exact-source or deployed qualification. The prior
empty-history failure and lock timeouts remain retained.

Rate integrity: raw assessor results are now always unknown in cohort rate
summaries, even when they show a violation. Only report-schema results with
both fixture context and capture environment verified can contribute; a
violation observed on an unbound capture remains diagnostic evidence. This
closes a path that could previously count raw results without those bindings.
Reports also record a canonical digest of the scored rubric, and aggregation
requires both the expected case ID and rubric digest to match. This prevents
accidental reuse under another case or changed expectations; it does not prove
independent authorship or turn caller-supplied verification flags into evidence.

Re-anchor checkpoint: this lane merged main `7a1a6bfb35347d8b79f8e05074ef023416db9328`
after the Build rich-paste receipt and Plan Turn changes. The focused evaluator
suite passed 43 tests in the shared Python environment. The CI inventory still
reports the evaluator test as unclassified; its shared manifest remains under
the CI lane's lease. This is not locked-environment or current-head runtime
qualification, and the predecessor-source observations below remain unchanged.

Primary context binding now checks the complete prior conversation, clean page,
and the product-validated source receipt/provenance join. A read-only smoke on
an existing ordinary capture passed using a fixture reconstructed from that
same capture; it is not independent benchmark qualification. The optional
related-page preflight checks the exact fixture inventory and source bodies
before and after a turn without adding them to the controller request. The
ordinary fixture still needs isolated provisioning and complete acquisition
coverage before it can qualify a cohort.

A derived mounted-UI witness on source `203dd55cbf3e19661b9e14ab02a33459e08b5119`
rendered a saved typed Build question, retained an edited answer on remount,
added it to the composer, and sent it to a scripted pending Build transport.
One test passed with 324 filtered using Node 21.6.2 and copied dependencies under
the frontend lock. The nonqualifying evidence and two test-harness failures
(matcher usage and wrong working directory) are retained at
`Projects/.codex/buddy-check.negative-inline.SsurDn`. Server completion,
durable continuation, actual model behavior, Node 22 exact-source checks, and
deployment remain unproven.

The preflight now rejects a missing or mismatched pinned page and prior
conversation before dispatch, and checks related-page inventory before and
after the turn. An intermediate focused test run had two failures because its
mock capture tests did not supply the newly required snapshot; the tests were
updated to isolate that mock and separate snapshot/history rejection checks
were added. The next focused run passed 23 tests. These are working-tree
checks, not exact-source qualification.

Re-anchor: base `c3a2ae6032b0f16fc19d21be14759a0a8607782b` contains a
non-overlapping shared native-writer optimization; previous exact-head results
remain predecessor evidence. The current benchmark resource policy uses one
owned App clone per workstream, serial resets and retries, a read-only shared
Core and no full inventory scans. The wrapper now refuses per-capture clones
and delegates through the pinned cohort path that enforces read-only Core and
skips Core table-content inventories. Owner lifecycle, capacity and cleanup
remain executor prerequisites. The allocation and retained owner are recorded
in the provider-free baseline below.

The clarification scorer now separates an answerable question that addresses
the actual gap from one that repeats supplied information or adds false
premises. Inline rendering, absence of retry/error presentation, question
reopen, answer submission, completed continuation and answer reopen each have
separate evidence checks. These checks remain unproven without their actual
owning-boundary evidence. Unvalidated opening votes are retained separately
from observed reads; in the supplied trace the controller reported anchored
context and six read votes, and six related-page reads were observed. The raw
response's validation status is not upgraded by this observation.

CI inventory ownership: the earlier inventory reported
`tests/evals/test_negative_retrieval_assessment.py` as unclassified. The CI owner
explicitly split that single entry to this lane in the pinned
`HANDOFF-CI-one-app-workstream.md` at
`8bfb1d9488c1d8783c57c4c9b3b9e7296e6940f8`; the entry is now in the existing
qualification category. This does not transfer other manifest entries or depend
on CI4598 merging. Keep normal test discovery and do not alter other selectors.

Planned diagnostic runtime lease: one uniquely owned disposable App clone on the
shared local benchmark server, reused serially for this workstream, plus the
existing read-only shared Core snapshot. No other lane's clone may be used or
removed. Check capacity across both shared benchmark servers immediately before
allocation; pin the template, cluster, clone OID, exact source and owner/worker
process identities. Retain the clone for review, retries and follow-up; close
workers and connections before explicit acceptance/abandonment and verify its
exact removal. This extends only this benchmark's runtime allocation, not its
source write lease or merge/deployment authority. Prepare and inspect the owner,
worker and their inputs before allocation. A provider-free HTTP witness must
use the owner-bound fixture, never the repository's raw multi-clone fixture.

Before allocating the HTTP witness clone, the ordinary test collected only after
staging the repository's exact pinned Core, GenerationEngine and WorldKeeper
sources; the shared Python environment had older installed revisions. The
shared App template reports schema `20261122_0189`, while this exact Buddy source
requires `20261123_0195`. A diagnostic worker must first verify its owned clone
identity, then migrate only that clone with the repository migration owner;
the template and read-only Core remain untouched. The initial import/collection
failure and corrected collection are retained in the task's `http-owner` evidence.


## Provider-free HTTP baseline

Owner ledger: `Projects/.codex/buddy-check.negative-inline.SsurDn/http-owner/session/owner.json`.
It owns exactly `benchmark_run_8c2a3c2ca7a6475ba97789e2bb319658`, OID 220491
on the shared local cluster; source `d00807237abff7a190960cef85796a7faa4c8166`.
The owner is retained for review and serial follow-up. The checked-out source,
worker hashes, capacity evidence, exact pinned dependency sources, preflight
collection failure and corrected collection are retained alongside the ledger.
The clone alone migrated 0189 to 0195. The shared Core uses its dedicated
read-only login; no model or external provider was called.

Case 1 exercised the ordinary Build/APP HTTP route with synthetic controller
votes and an in-memory Core. It failed its required typed-question outcome:
HTTP 409 `build_contextual_placement_unresolved`, after one related-page catalog
discovery and four physical materialization calls covering two pages. Case 2
repeated the scenario on the same clone with safety assertions moved before the
status check: the primary page was unchanged and zero proposals existed, then
the same 409 failed the acceptance assertion. Both failed logs and derived test
hashes remain in `session/case-1` and `session/case-2`. They prove the bounded
HTTP failure and safety checks, not model quality, deployed UI or a full
negative-retrieval rate. Do not rerun unchanged. The source-free routing owner
and the inline successful-completion path remain separate required work.

Case 3 captured the actual serialized synthetic controller input before its
mock transport, using the same owned clone and no external provider. It again
returned the same 409, after confirming the unchanged page and zero proposals.
The retained `session/case-3` evidence includes the derived witness, failure
log and owner-only controller input (SHA-256
`bd19a922189a49c4d32b47c884e0fa8b4aacd7bfdf114bfe88da1a6008678610`).
The input's `placement_policy` is semantic guidance for selecting an insertion
point, rather than capacity or accounting policy. A field inventory alone is
not a complete prompt-boundary audit: inspect actual values, nested inputs and
host bindings against the ecosystem policy before any provider dispatch. This
synthetic capture does not qualify the current head or establish model quality.

Case 3 controller-input review, limited to this synthetic request: the outer
`model` is the provider transport selector; `questions` contains fixed choice
names, task instructions and answer options. `state.user_question` is the
synthetic author request. `state.interaction` contains the offered operations,
synthetic current-page title and passage, heading aliases, selected-reference
display label, related-page titles, page-target kind, empty dialogue history,
working-draft availability and insertion-matching instructions. No database
keys, receipts, hashes, execution identifiers, accounting limits or telemetry
were observed in those serialized values. The labels are request-local choices,
not authorization. This manual review covers only the captured controller call;
it does not verify other producers, later calls, nested tool results, alias
resolution or host-side authorization and must not be used as a blanket
provider-dispatch approval. The related-page questions were still offered in
this anchored synthetic case, and the synthetic read votes led to the observed
materializations; the capture does not show how a live model would vote.

Case 4 ran the existing ordinary Build draft scope controls through the same
owner-bound clone, with the related-page owners instrumented. The anchored
control made one catalog-discovery attempt and zero materialization calls;
the `source_lookup` control made one discovery and four materialization calls.
Both existing event assertions and the physical-read assertions passed (2
tests); the retained worker, derived test and full log are under
`http-owner/session/case-4`, with the worker beside `session`. These synthetic
controller votes demonstrate that discovery and materialization must be scored
separately. The optional page is not established as necessary evidence for
this draft, so this is not a genuine required-evidence positive control or a
model-quality rate. It uses the same predecessor source and mocked provider and
in-memory Core as the earlier cases; it does not qualify the current head.

Case 5 used the same ordinary HTTP owner with a synthetic draft request that
explicitly asks for a bridge toll from `Optional lore`; the related page held
the toll. With scripted `source_lookup` and read votes, one persisted
related-page read event matched that title and exact toll-bearing text, and the
probe observed four materialization attempts. The owning test passed (1 test).
The worker and derived source are retained under `http-owner` and
`http-owner/session/case-5` respectively. This is a required-source path
witness, not a model decision or an answer-quality judgment: the controller
and writer are scripted, Core is in memory, and the source is the predecessor
SHA. A separately bound ordinary fixture and independent semantic assessment
are still required for the positive benchmark rate.

Case 6 extended that same synthetic positive witness to inspect the actual
serialized writer request: the toll-bearing related-page text appeared in it,
as well as in the persisted read event. The test passed (1 test), with the
worker and derived witness retained under `http-owner` and `session/case-6`.
The writer transport was mocked, so this does not establish a correct answer,
live provider behavior or a full prompt-boundary audit.

Execution constraint: ordinary `build_sequence` capture carries one pinned
page and conversation across its cases. The development fixtures specify
different pages and dialogue histories; a single such sequence cannot bind
them as independent cases. Provision and verify a separate case fixture and
capture for each, then aggregate the independently bound reports. Do not
combine their scores merely because their requests ran in one conversation.

The evaluator wrapper can now reuse a preseeded active conversation for the
first case only after checking its complete dialogue against the fixture. The
ordinary runner checks the active conversation again, and the offline binding
still checks retained prior history. A focused diagnostic run passed 32 tests,
including acceptance of an exact prefix and refusal of a mismatch before
dispatch. This does not provision the synthetic histories, prevent concurrent
turns, or substitute for an owning-boundary run; a changed retained prefix must
invalidate the result. The focused run used the existing shared Python
environment and is not exact-source qualification.

The wrapper now also validates the ordinary runner's own pre-dispatch history
read. A diagnostic test changes the prefix after initial preflight while keeping
the conversation ID and confirms the runner is stopped before dispatch; all
32 focused tests passed. This closes that observed check gap, not the interval
after the runner's read: retained-history binding remains necessary to detect
intervening turns, and an owning-boundary run remains outstanding.

Case 7 exercised the candidate wrapper against an actual saved conversation
read through the ordinary HTTP endpoint, backed by the owner-bound App clone.
It matched the complete saved dialogue on preflight and on the runner-side
read (1 test passed). The worker and derived test are retained under
`http-owner` and `session/case-7`; the candidate wrapper was loaded by its
pinned file hash `c8680ac5df49809e076e2ee2593823f81dc4427d89a4021e1fbdbdff82c546af`
against predecessor product source `d00807237abff7a190960cef85796a7faa4c8166`.
The fixture was reconstructed from that same saved turn, page/source preflight
and final benchmark dispatch were stubbed, and the prior turn used synthetic
providers. This verifies the real history endpoint's shape and wrapper
handoff only; it is not a frozen independent case, full capture or current-head
qualification.

Case 8 used the existing conversation owner and its test submission helpers to
create a fresh synthetic World in the same App clone, accept and complete the
exact frozen `dev-placement` dialogue without contacting a provider, and read
the same user/assistant pair through `list_build_dialogue` (1 test passed).
The development fixture bytes were pinned by SHA-256
`ee990d0006d07913a0c17e3973fe2987158925134bbf2df7b0cb981b7889c9bf`;
the worker and derived test are retained under `http-owner` and
`session/case-8`. This was a seeding proof using the existing test's Plan
provenance, not a complete Build case: page provisioning, a reusable guarded
seeder, the ordinary HTTP capture and the post-capture binding remain open.
The runtime source is the predecessor SHA, not the current benchmark head.

Cases 9 and 10 advanced that proof to Build provenance and the new guarded
`seed_dialogue` helper. Against the owner-bound clone, the helper round-tripped
the frozen development dialogue and rejected a second seed in the same World
(1 test passed). It checks the owner lease, a fresh synthetic World and the
supplied snapshot, but does not provision or verify the actual saved page.
Both diagnostics and pinned candidate code remain under `http-owner/session`;
the product source is the predecessor SHA. The focused assessment suite also
passed 33 tests in the shared environment, including invalid-world and malformed
history refusals before database access. Exact-head qualification remains open.

Cases 11–14 exercised an actual synthetic page created and saved by the page
owner, then bound to the frozen Build dialogue. The helper now reads the
persisted owner snapshot and refuses mismatched saved content before creating a
conversation. Case 14 proved both the forged-snapshot refusal and successful
page/dialogue round trip (1 test passed); case 13's generated test had a string
escaping SyntaxError during collection and is retained. The focused suite
passed 34 tests in the shared environment. These diagnostics use the predecessor
product source and do not establish an ordinary benchmark turn or exact-head
qualification. The caller still owns safe page/World provisioning.

Case 15 exercised the new eval-owned `provision_fixture` and guarded seeder
together against the owned clone. It created a fresh synthetic World, saved
and verified the frozen primary page and the `harbour` related page through
their owners, and round-tripped the frozen dialogue (1 test passed). The
fixture and candidate source hashes, derived test and owner logs are retained in
`http-owner/session/case-15`; the related-page root was configured to the
isolated test directory. The product source remains the predecessor SHA, and
the test did not construct a full ordinary capture or contact a model. The
focused suite passed 35 tests in the shared environment, including duplicate
source rejection before database access. Exact-head and CI classification
requirements remain open.

Case 16 checked the fresh World's real native-binding resolver after fixture
provisioning. It returned `native_graph_binding_missing`, while the page and
dialogue setup still passed (1 diagnostic test). The test and worker are
retained under `http-owner/session/case-16` and `http-owner`. A synthetic App
World alone is therefore not an ordinary Build capture fixture. A reviewed,
authorized synthetic Core binding compatible with the shared read-only Core
policy is still required; do not write to that Core or fake a binding as a
qualification shortcut. This is predecessor-source evidence, not a live-model
turn. Resolve this dependency with its owning lane before dispatch.

Case 17 retained the exact serialized synthetic writer request before its mock
transport, extending the required-source witness. The request includes the
toll-bearing source text; its three input messages contain projected Build work,
Rules context and native evidence, and it has no tool definitions. A targeted
inspection of nested identifier/hash/capacity/telemetry field names found only
`house_ruleset_id: null`. The owner-only wire SHA-256 is
`42e6818de88499478c974f9b9f5904c2a91cd534caf86abd04d95e89b7202c27`, with the
worker, derived test and log retained under `http-owner/session/case-17` and
`http-owner`. One diagnostic test passed with synthetic controller and writer
transports. This targeted inspection is not a complete boundary audit: the
instruction text, all values, alternative calls and host binding checks still
need review before live dispatch; no provider was contacted.

Follow-up manual review of that same synthetic wire found a prompt-boundary
concern outside this eval-only lease. Model-visible instructions contain the
implementation version `dmb_surface_evidence_answer_v8` as the current answer
policy and require it as the `schema` output value; the visible strict output
schema repeats that constant. The ecosystem prompt policy excludes
serializer/schema/pipeline implementation versions from model-visible input.
The captured value appears to conflict with that rule even though the host may
need its existing versioned contract for validation. The instruction family is
constructed in `surface_evidence_answer.py`; the v8 policy is owned in
`native_plan_assertions.py`. This is a synthetic predecessor-source observation,
not proof of every live writer path. Do not strip values, weaken validation or
change those shared runtime owners in this benchmark lease. The owning lane must
review the final serialized request and host-side contract before live dispatch.

Re-anchor after the wire finding: fetched Buddy main
`55bf93989bb04e385ed93f5bdade4f4a21bb6890` still defines the v8 policy and
the version-substituting instruction family. This is a source inspection, not
a capture of that exact head. DOGFOOD #4573 remains open at
`f713f4ae0429635bbe6f0603f1594d8c1c308d10`, with its new exact-head
qualification pending and its source-free routing successor still serially
blocked. The retained shared-Core capture manifest names the existing
`elderwyld` World, not a verified synthetic World; copying its binding into
the newly provisioned fixture would not establish authority or isolation.

The rate summarizer now treats offline reports as unknown unless both fixture
context and capture environment are independently verified. Previously it
could count a raw observed violation from a report whose overall status was
unproven, making a cohort rate look more certain than its fixture binding.
Missing-artifact reports also contribute unknown rather than causing a crash.
The raw failure remains visible in the report. Focused diagnostic: 36 tests
passed in the shared Python environment; the report still cannot itself attest
the capture environment, and exact-head qualification remains outstanding.

The scorer now distinguishes proof of a required read from proof of its
absence: an explicitly mapped required read establishes presence even when
the acquisition journal is partial, while an absent or unmapped witness is
unknown until the journal is complete and fully mapped. Semantic support and
overall journal completeness remain separate requirements. The focused
diagnostic suite passed 37 tests in the shared environment; no benchmark rate
or exact-head qualification is implied.

Offline reports now have a distinct format tag from direct assessor results.
The rate summarizer treats reports with either verification field missing as
unknown, and also treats unrecognized or missing format tags as unknown. The
focused test removes each field and the tag to exercise these cases. The tags
are format discrimination, not authentication of manually edited artifacts.

The related-page preflight now checks each catalog pointer against the requested
World, rejects the primary page and duplicate identities, and requires a valid
revision before materialization. Previously it compared a pointer to its
materialized body without itself establishing the pointer's World. A focused
test rejects foreign, primary and invalid-revision pointers before the
materialization call; all 37 focused tests passed in the shared environment.
The real Build catalog already scopes discovery; this is evaluator-side
defense and does not establish a current-head owning-boundary run.

Case 18 loaded the updated preflight by SHA-256
`5e4fa2b88683d39c83e8564f857de44ba58d92bca19aa0c0308b1fe210bd6d7e`
against the real synthetic page catalog on the owner-bound App clone. It
matched the provisioned fixture inventory, then rejected an injected
foreign-World pointer before materialization (1 test passed). The worker,
derived test and log are retained under `http-owner` and `session/case-18`.
Product source was the predecessor `d00807237abff7a190960cef85796a7faa4c8166`;
this is not an exact-head run or a live-model benchmark.

Case 19 ran the existing ordinary Build reviewed-step owner test with a
synthetic typed-question writer result on the owner-bound App clone. It passed
the HTTP completion, saved typed reply, replay, unchanged-page, archived
conversation library reopen and foreign-scope refusal assertions (1 test).
The worker, derived test and log are retained under `http-owner` and
`session/case-19`. The controller and writer transports are scripted, Core is
in memory, and the product source is the predecessor SHA. This is a successful
saved-question control, not the ambiguous placement case, a mounted UI test,
answer submission, continuation, current-head qualification or deployed proof.

Cases 20–22 extended that owner test with a synthetic answer submitted through
the ordinary Build endpoint. Case 20 failed because the fixture still forbade
controller routing after the reviewed step; case 21 received HTTP 200 but the
test incorrectly expected a lifecycle field in the library projection. Case 22
reset the fixture and checked status through the conversation owner: it passed
HTTP submission, completed saved answer turn, retained typed question and
answer after conversation switch, and unchanged primary page (1 test). All
workers, derived tests and logs remain under `http-owner/session/case-20`–
`case-22`. The controller/writer were scripted and the output was not judged
to complete the original task. This is not mounted UI, ambiguous-placement,
live-model, exact-head or deployed evidence.

An isolated mounted-component follow-up exercised a scripted completed answer,
updated synthetic saved history and remount. The first attempt failed to find
the question after remount; its console output was truncated. A corrected
saved-reply projection still failed (`corrected.log`). Adding diagnostic DOM
output produced one pass (`reopen-dom.log`), but replacing that output with a
five-second asynchronous assertion failed again (`waited.log`). The scripted
reply and answer appeared in the passing DOM capture, but this inconsistent
result does not establish successful reopen or a product defect: the synthetic
harness and timing remain unresolved. The derived test and logs are retained
at `Projects/.codex/buddy-check.inline-continuation.666msV`; its disposable UI
copy and copied dependencies were removed after the process exited. Node 21.6.2
and matching copied lockfile dependencies were used under the frontend lock;
this is not the required Node 22 exact-source verification, actual server
continuation, live-model behavior or deployed smoke.

The follow-up explicitly opened the saved question's Details after remount.
The first changed test hit its 5-second overall timeout; one retry timed out
waiting for the shared frontend lock and did not execute Vitest. With a
15-second test timeout and the lock acquired, the assertion still failed to
find `Question 1`. `derived-explicit-details.test.tsx`, `explicit-details.log`
and `explicit-details-final.log` are retained in the same evidence directory.
The test uses synthetic history and transport, so this remains an unresolved
diagnostic rather than proof of a product regression; no UI owner files changed.

The next diagnostic disabled the test helper's automatic Details-click
observer and explicitly opened the saved question's Details on both mounts.
It passed twice (one test, 324 filtered in each run): the scripted completed
reply, saved question and submitted answer appeared after remount. The changed
witness and logs are retained as `derived-manual-inspection.test.tsx`,
`manual-inspection-after-lock.log` and `manual-inspection-repeat.log` in the
same evidence directory. An earlier attempt did not start because the shared
frontend lock was held by another exact-source verifier. This outcome is
consistent with a test-helper interaction contributing to the inconsistency,
but does not prove its cause. Transport and saved history were simulated;
Node 21 and copied dependencies remain diagnostic only. It does not establish
real-server continuation, task completion, exact-head UI or deployed behavior.

The eval-owned inline witness generator now reproduces the controlled
completed-response/remount test byte-for-byte from the existing UI owner
fixture. It preserves the simulated transport/history limitation and the
explicit Details interactions; the focused evaluator suite passed 37 tests in
the shared environment. The two retained Node 21 diagnostic passes apply to
that generated byte sequence, not to actual server or deployed behavior.

Buddy main `93d94e9de081c1ba55daf530348a63cfacdfa124` merged the serial
cohort App-clone runner #4583. This benchmark branch still needs integration
against the updated runner and an authorized synthetic Core binding; that merge
does not itself qualify the fixture or unblock model dispatch.

The benchmark branch subsequently merged Buddy main
`f5538e832756ccb58d2a14b1e96c824682b1da48` at merge commit
`b94905804db142935880612c9fa6d544a8c19760`; the changed-file sets were
disjoint. The evaluator suite passed 37 tests and 11 focused merged-runner
cohort guard tests passed (121 deselected) using the shared Python environment.
The runner's shared-clone mode requires one browser worker, captures at the
writer-off boundary and performs Core inventories; it is not a drop-in full
Build response cohort under this lane's no-full-scan policy. The eval wrapper's
single owned-clone capture remains separate. No live capture, policy exception,
Core write or exact-source qualification follows from this integration.

The evaluator wrapper now requires the caller's frozen manifest SHA-256 and
rejects a missing, malformed or mismatched pin before invoking the ordinary
runner. Previously it hashed the file it had just received, which detected a
later change but did not bind capture to an independently frozen manifest.
The focused diagnostic suite passed 38 tests in the shared environment. The
digest alone does not establish independent case authorship, fixture
provenance, a synthetic Core binding or exact-head qualification.

Capture now also requires a separately frozen canonical fixture-set digest when
fixtures are supplied, snapshots the checked JSON inputs, and retains the set
and case digests host-side. Offline reporting verifies the case pin against a
caller-supplied set digest before marking fixture context verified. Missing or
mismatched pins remain unproven. This does not authenticate the pin's author or
prove independent held-out authorship. The focused suite passed 40 tests in the
shared environment; no live capture or exact-source qualification is implied.

The report now requires the independently pinned full fixture mapping and
verifies that the reported case is actually a member of that mapping. Merely
placing a valid set digest beside an unrelated case digest no longer qualifies
the fixture. A focused regression also mutates the caller's fixture after the
pin check and confirms capture uses its frozen snapshot. The shared-environment
suite passed 41 tests. These checks do not authenticate authorship or establish
a complete capture environment.

Cases 23–24 exercised the frozen `dev-placement` request, primary page and
dialogue on the ordinary Build/APP owner fixture using scripted anchored/read
votes and an in-memory Core. Case 23 reached a proposal but the inherited test
incorrectly indexed the seeded prior turn as the current turn. After correcting
that test lookup, case 24 reached and checked the proposal and failed its zero
retrieval budget: one related catalog discovery and four materialization calls
across two pages. Both failures and derived source are retained under
`http-owner/session/case-23` and `case-24`. The existing owner fixture's related
pages differ from the frozen `harbour` inventory, prior dialogue used synthetic
Plan provenance, and provider votes/output were scripted. This is a bounded
negative-path diagnostic, not a qualified fixture, model rate, real Core or
deployed result. The test's later explicit page save simulates author action;
the owner assertions check the unchanged page before that action.

Case 25 adapted the same disposable owner fixture to expose exactly the frozen
`harbour` related-page inventory and verified its title, body and identity before
and after the measured product turn. Those pre/post fixture reads were excluded
from the probe. The proposal path completed, but the zero-retrieval assertion
failed: one catalog discovery and two materialization calls for the related
page. The derived witness, worker and failure log are retained under
`http-owner/session/case-25` and `http-owner`. The synthetic owner fixture's
unrelated source page was made ineligible for related-page discovery within
that disposable World; prior dialogue still used test Plan provenance, the Core
was in memory, and the controller/writer were scripted. This improves fixture
matching but is not a qualified live-model cohort or exact-head result.

Case 26 ran the new eval-owned `frozen_placement_witness` generator against
the owner test and the pinned development fixture. It reproduced the expected
red result: verified pre/post inventory, completed scripted proposal, one
catalog discovery and two materialization attempts. The generator and fixture
hashes, generated test, worker and failure log are retained under
`http-owner/session/case-26` and `http-owner`. The generator checks its fixture
pin and exact test anchors; the focused evaluator suite passed 43 tests in the
shared environment. This remains predecessor-source, synthetic-provider and
in-memory Core evidence; it does not qualify a real-model rate or deployment.

Cases 29–30 extended the generated frozen placement witness to move the actual
proposal through the App review owner. Case 30 also checked that apply
preparation retained the moved caret and that the primary page remained
unchanged before the subsequent simulated author save. Those assertions passed;
the test remained red on the expected one discovery and two materializations.
Workers, generated tests and logs are retained under `http-owner/session/case-29`
and `case-30`. Controller and writer were scripted, Core was in memory, and
product source was the predecessor SHA. This is not a UI move, actual apply at
the moved caret, live-model rate or current-head qualification. The focused
shared-environment suite passed 43 tests.

Case 31 repeated case 30's frozen inventory, scripted anchored controller,
proposal move and apply preparation with the related-page vote changed from
`read` to `skip`. Pre/post inventory and unchanged-page checks passed. The
zero-retrieval assertion remained red: the probe recorded one catalog
discovery and no materializations, versus one discovery and two
materializations with the read vote. The worker, derived test and failure log
are retained under `http-owner/session/case-31` and `http-owner`. This isolates
eager discovery in this scripted predecessor-source scenario; it does not
establish a live model's vote, a cohort rate, current-head behavior or deployed
UI behavior. The focused shared-environment evaluator suite passed 43 tests.

Cases 27–28 exercised the existing proposal-move App owner control. Case 27
stopped during setup because its legacy fixture assumed an empty `elderwyld`
conversation, while the retained clone already had state. Case 28 adapted the
disposable test and helper to a fresh synthetic World and passed: move persisted
across reopen, stale revision was rejected, apply preparation used the moved
position, and the primary page remained unchanged (1 test). The worker,
derived test and logs remain under `http-owner/session/case-27` and `case-28`.
This proves the existing move capability separately from the frozen placement
proposal; it does not prove that specific proposal was moved in the UI, current
head qualification or deployment. No provider was contacted.

Offline reporting now exposes available terminal status and separate
discovery/materialization attempt and exception counts even when other
required capture artifacts are missing. Such reports stay unproven and count
as unknown in cohort rates. A focused regression covers a raised
materialization and rejects a probe from another case; 42 tests passed in the
shared Python environment. This is evaluator diagnostic coverage, not an
attribution of the original trace's undisclosed exception.
