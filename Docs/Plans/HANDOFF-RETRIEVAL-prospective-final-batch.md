# RETRIEVAL: prospective final read batch

Status: DELIVERED. PR2321 merged as06c42c079569f09c950cf623306d454570c57d3b from independently reviewed/captured cee04fd1dc784b223acd11f769d65f95b95a7999. Its implementation lease is released; the consuming opening-batch handoff records current authority. Root is retrieval steward.
Authority is the user’s standing retrieval goal and full merge rights. No deployment or primary changes.
Goal remains six-second actual request→context-ready with all15 contexts preserved.

## Evidence and hypothesis

Merged2317 at33a21f7928babcde59c3be3250c2713cc0526822 is the accepted next baseline:
15/15 actual contexts,72/72 required atoms,10.216s median request→ready. Writer
output excluded; primary/original evaluator/native rows conserved.

Retained navigation-frontier-audit-v1.json finds42/44 successive retrieval
transitions have no new candidate rows,36also unchanged other navigation state
(examined acquisition statuses excluded, not assumed irrelevant). Observed
postauthorization→response intervals across those stable transitions total
996ms median per case; this excludes some authorization/selection costs and is
not a guaranteed saving. Actual terminal interval alone is491ms median.

Independent first-batch-source-availability-audit-v1.json finds65/72 required
exact-quote supports available after the first actual read batch, covering14/15
cases. Q15's7additional supports arrive in round2. This is source-availability
analysis of real committed prefixes, NOT an earlier authorized final context.
No question-specific stop, exception, oracle or Gold is allowed in runtime.

Hypothesis: an explicit prospective collection-plan decision can eliminate
repeated relevance rounds after the model's intended successful final batch,
without a host inventing evidence sufficiency or provider finish responses.

## Single capability and contract

One serial Buddy PR; no SDK/Core/model replacement. A new current readonly Plan
input/result codec asks one additional independent conditional-plan question:
`review_after_reads` or `finish_if_selected_reads_succeed`. It cannot inspect
candidate_* answers. Decoder binds the proposition to actual included handles.
Existing all-excluded fallback remains its sole operation owner; the prospective
proposition has false applicability there, not synthetic stop permission.

For actual selected keyword/discovery/expansion/Rules/unknown or unsupported
families, completion is explicitly inapplicable and normal review continues.
No selected obligation is silently removed. This is the declared condition's
false branch, not compatibility fallback or another producer. Non-read metadata
expansion must be reviewed before a new final-batch plan can become applicable.

One pure domain owner derives selected read obligations from the actual admitted
selection, frozen query/catalog and attempted state as of that selection. It
requires every selected eligible record/extent to have matching successful
current-batch observation, exact authority and no unavailable/partial/pending
work. Empty/unprovable closure is not success. Reuse existing record expansion
and exact full-document-fulfills-section semantics at their owner, extracting a
shared pure predicate if needed rather than duplicating it in APP and runtime.
Do not require exhausting unselected World candidates.

A new host conclusion event records actual deterministic fulfillment of the
model's prospective collection plan, linked to the real selection/attempt and
computed read IDs. It is NOT a fabricated finish_retrieval response/selection.
APP computes it under existing claim/raw guard/CAS/actual ACK; full recovery
rederives the same closure. No caller-provided success/read-ID list is authority.
Only proven conclusion permits driver.finished and writer authorization. Actual
ordinary finish responses remain valid. Read commits and failure retention stay.

Current/historical codecs remain exact and disjoint. Current readonly runtime
emits one authoritative new contract, not a compatibility switch. Build/Play,
editing and unsupported modalities keep their existing owners. No writer prompt,
output grading, source label or ingestion changes. Empty reader fence only.

## Proposed owner map (must resolve exact paths before ACTIVE)

- jev_retrieval_contract.py: current Plan input/result/serialized question and
  applicability, old wire retained exactly.
- native_retrieval.py: concrete selected/concluded codecs, actual parent/result
  proof and phase/writer readiness. One narrowly scoped native_batch_completion.py
  may own pure selected-read closure; this is one invariant owner, not new storage.
- plan_jev_decision.py: concrete dispatch to current/historical proof readers.
- native_execution.py/types.py: explicit event union/export and readonly scope.
- native_plan_session.py/service.py: computed closed conclusion command.
- native_plan_statements.py/native_record_execution.py/native_corpus.py: only
  exact existing expansion/success/overlap predicates needed by closure.
- plan_jev_dispatch.py/plan_jev_driver.py: new exact response contract, after-real-
  read conditional settlement, no new actual provider attempt or synthetic vote.
- corpus_source_navigation.py only if relocating existing extent-fulfillment
  predicate to its pure owner avoids duplicated semantics.
- current writer readiness proof owner only if required; no composition changes.
- one unused146reader-fence migration after verifying current head/leases.
- existing pure SDK contract, native APP decision/acquisition/session tests.
- consuming handoff and truthful prior2317handoff merge/lease settlement.

Before activation pin current remote main/PR inventory, exact path allowlist,
checkout/resource ownership and source baseline. Review map must follow the
producer proof→selected closure→actual commit→writer frontier. This is an
indivisible capability across those owners; no independent event/skip-flag PR.

## Verification and decision

Use the same existing consolidated workflow and isolated fixtures. Locally prove
actual new SDK choice/proof, no reinterpretation of old fallback, all-excluded
behavior, unsupported/metadata choices, selected closure grouping/overlap,
partial/grant-only/foreign/stale/duplicate/forged/public-mutation refusal, commit
ambiguity, preserved earlier successful reads, full recovery and writer admission.
No new per-question scripts, provider cap, fallback, manual evidence or Gold input.

Only after owner proof and independent exact-code review, run one changed15case
context cohort against retained2317captures. No unchanged fresh baseline. Preserve
all actual provider attempts/tokens/cost-or-unknown/source volume/elapsed timing.
Independently require15/15 contexts and72/72 atoms, attribution, chronology,
uncertainty and exact quotation/citation support. Q15 is a genuine premature-stop
risk and must pass generically; never add a named exception or weaken Gold.
Reject a quality loss or immaterial latency result. Keep failed evidence and no
unchanged reruns seeking pass. Even adoption does not complete the broader goal
unless actual six-second behavior is verified.

## Design review

prospective-final-batch-design-review-v1.json passes bounded design with explicit
applicability/closure. Earlier fallback-reuse shortcuts and circular preclaim
fusion are rejected: current initial claim binds actual prepared SDK bytes, so
fusion requires separate request-admission redesign rather than placeholder wire.

The original design was BLOCKED pending inventory. The activation below resolves
that gate under standing goal authority; no additional user permission is pending.

## Activation

Branch codex/retrieval-prospective-final-batch, base a2716bdec99f0020aafe2f3b473d6a1d2f4d78f6.
Existing clean recorded-names-control checkout; no serving runtime or benchmark
worker remains. Topology serial. Open PR inventory contains Surface/Storage/CI/
older composition lanes, no overlapping retrieval/runtime/migration lease.
Prior2317lease released at33a21f792; sync its handoff truthfully in this slice.
Isolated port55447; original evaluator and primary immutable. New candidate/test
clones only. Frozen `.venv` unchanged. Logs/artifacts under Projects-backed out.

Exact exclusive expected write paths:

- Docs/Plans/HANDOFF-RETRIEVAL-prospective-final-batch.md
- Docs/Plans/HANDOFF-RETRIEVAL-initial-source-discovery.md (merged predecessor settlement)
- src/application_state/agent_conversation/jev_retrieval_contract.py
- src/application_state/agent_conversation/native_retrieval.py
- src/application_state/agent_conversation/native_batch_completion.py
- src/application_state/agent_conversation/plan_jev_decision.py
- src/application_state/agent_conversation/native_execution.py
- src/application_state/agent_conversation/types.py
- src/application_state/agent_conversation/native_reads.py
- src/application_state/agent_conversation/native_plan_session.py
- src/application_state/agent_conversation/service.py
- src/application_state/agent_conversation/native_source_keywords.py
- src/application_state/agent_conversation/plan_jev_rules_lookup.py
- src/application_state/agent_conversation/native_corpus.py (shared exact overlap owner if needed)
- apps/live_control_server/services/corpus_source_navigation.py
- apps/live_control_server/services/plan_jev_dispatch.py
- apps/live_control_server/services/plan_jev_driver.py
- src/application_state/migrations/versions/20261109_0146_prospective_read_batch.py
- tests/test_jev_retrieval_contract.py
- tests/test_native_plan_assertions.py (shared ordinary SDK fixture answers the new explicit question; preserve its existing review flow)
- tests/test_native_batch_completion.py
- tests/application_state/test_surface_native_acquisition.py
- tests/application_state/test_surface_native_decisions.py (optional future codec fixture path, historical default unchanged)

Applicability decision: preserve actual conditional proposition in new result;
all-excluded/unsupported selection makes it false, and ordinary review/actual
fallback retains authority. No contradiction repair call. No unproven source
closure or copied provider finish event. Metadata expansion remains an obligation
to review, including Q15 by generic rules, never a question-specific condition.
No additional user permission is pending. Independent exact-code review and
local owner proof remain gates before any new paid candidate.
