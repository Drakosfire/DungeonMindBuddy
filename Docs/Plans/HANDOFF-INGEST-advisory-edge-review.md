# INGEST: optional advisory edge review

Status ACTIVE: PRIME activates after ARCHITECTURE design PASS on
f665ca92d60aa7f2de43ca4f0dac9c2ae76b4cd3. Prerequisite PR1179 is merged
and settled. Implementation review remains required before merge.
PRIME owns solo implementation. Re-anchored base
a8a19345e21924716d184d3b7252ba8dd5a68f70, including PR1179 merge
4de42fa3bfc1115d909f82b40392e539cf98a0e3.
One capability: an explicitly selected Gazetteer1.4 performs a separate advisory
review of generated edge proposals. It may retain only original edge IDs; the
application copies original objects unchanged and preserves omissions as deferred
proposals, not disproved facts. Model selection is NOT source/native/identity
acceptance. No World publication or default profile change.

Evidence: private26-case development benchmark and separate review experiment
showed12→2 unsupported proposals retained, with all6 clear supported proposals
retained. Six context-dependent and two unresolved cases remain separate. This
is known development data, not held-out/general accuracy.1.3 role guard remains
independent/inherited. Full Mirathorn fidelity/publication remains incomplete.

## Flow and invariants

Add optional edge_review_pass spec to code-owned ExtractionProfile, defaultNone.
New internal pass kind edge_review returns only {retained_edge_ids:[string]}.
Validate exact keys/types, nonblank string IDs, unique input IDs before calling
review, unique returned IDs, subset membership;
blank/non-string/unknown/new/duplicate/malformed IDs FAIL the run, never silently salvage. Reorder
by original candidate order; do not let the model rewrite labels, refs, endpoints,
qualifiers, nodes, descriptions or identity. Empty subset allowed with truthful
all-deferred coverage, never a fidelity PASS. Old profiles make no extra calls.

Opt-in Gazetteer1.4 inherits1.3; review AFTER its source compiler so existing
role dispositions survive. Review input includes exact full source packet,
candidate endpoint navigation, and current edge proposals. Endpoint descriptions
and candidate kinds are NOT accepted truth. No hidden gold IDs/expected answers,
source omission, public corpus export or new native predicates. Generation's
prompt remains unchanged; compact navigation is local to the NEW review request.

Keep generation raw pass outputs immutable. Save review result/telemetry and an
advisory before/retained/deferred diagnostic with original objects/hashes. Omitted
edges become existing deferred_items with original refs and stable IDs, reason
advisory_review_omitted_not_proven_false. Collision fails closed. Retained edges
keep their existing candidate semantic states; no reviewed/accepted promotion.
All output artifacts must identify canonical post-review candidate separately
from pre-review/raw generation envelope; do not publish divergent candidates.

## Executor contract

Gazetteer1.4 requires an explicitly injected existing BoundedRecapPassClient,
configured for GenerationEngine -> OpenRouter DeepSeek V4.1 Flash. Validate the
client, provider/model and matching extraction model before ANY generation or
review call. Absent or incompatible client fails before inference; do not fall
through to OpenAICategoryGraphPassClient. Use the same client instance for writer
and reviewer so run deadlines, call accounting and evidence sink cover both.
This opt-in requirement does not migrate the default adapter or old profiles.
The registered worldbuilding service currently forwards category_client without
constructing a bounded client; therefore generic no-client Gazetteer1.4 use is
explicitly unavailable in this slice. Real registered research runs inject the
existing bounded client. A future UI/default routing change is separate scope.

Review adds one run_pass invocation, not a promise of one provider attempt.
The existing bounded GE client allows one structured-output conformance repair;
retain actual provider_attempt_count/conformance_retry_count/transport_retry_count
observations from its safe calls ledger. No new application retry, uncertain replay
or fallback. Existing max_transport_retries=0 and provider-route no-fallback remain
in force; missing observations remain unknown, never fabricated zero. Existing
credential loading, worker lifecycle, request budgets and cost accounting remain
owned by the bounded client/GE. Skip empty edge sets without invoking review.

raw_text means exactly the text returned by this client seam, not HTTP wire bytes.
Preserve its exact string, including whitespace, alongside the original GE attempt
artifact references/hashes where available. Do not claim direct SDK stripped text
or missing provider data is complete raw evidence. Whitelist JSON-safe ledger and
result fields explicitly; unsupported values cause controlled evidence failure,
never repr/default=str serialization of arbitrary objects.

On review failure/malformed output, no reviewable post-review candidate. Preserve
completed pass outputs AND exact raw responses where returned, review response
where available, request/profile/source hashes, usage/response IDs and unknown
costs. Use existing private RAW_MODEL_RESPONSE failure artifact with explicit
versioned evidence-bundle labeling; never pretend the bundle is one raw provider
response. Existing packaging must durably retain the bundle before FAILED state.
A failed sixth call must not erase successful generation or authorize replay.

Registered persistence dependency is merged PR1179 (reviewed a43b99d1), NOT legacy
 graph_ingest_packaging.py. The actual source-domain-neutral controller is
 graph_preview_runner.py.1179 owns retaining the supplied exception payload as
RAW_MODEL_RESPONSE before FAILED; this producer owns constructing its bundle.
The amendment below leases only successful private evidence registration at the
actual registered controller; accepted1179 failure retention remains unchanged.

Bundle schema dmb_private_extraction_failure_bundle_v1 contains exact source
artifact/hash, qualified profile, ordered completed pass IDs, request hashes,
exact raw_text where returned, parsed output, reported usage/cost/response IDs,
and failed-review raw response where available plus failure TYPE. Never capture
client/config objects, headers, credentials or exception repr. Missing usage/cost
remains unknown. Private scope/path/0600/hash registration comes from1179; raw
bundle must not be copied into public error/log messages. Existing provider output
budgets and profile pass count bound capture; no automatic retries or fallback.
The bundle is untrusted diagnostic data, never a promotable/corpus source.

For1.4 only, final envelope.candidate_graph must be a deep copy of the canonical
post-review candidate (including inherited source retention and deferred items).
Keep pre-review envelope separately in advisory diagnostics/raw pass lineage,
not as a second indistinguishable final candidate. Test normalized envelope→IR
roundtrip equality; old profiles retain their existing output behavior.

## Ownership / exact prospective write lease

- this handoff
- src/graph_memory/extraction/extraction_profile.py (optional spec only)
- src/graph_memory/extraction/category_candidate_graph_schema.py (internal pass kind)
- src/graph_memory/extraction/category_candidate_graph_extractor.py
  (optional review orchestration/raw-response preservation only)
- src/graph_memory/extraction/worldbuilding_edge_review.py (new pure review helpers)
- src/graph_memory/extraction/worldbuilding_gazetteer_profile.py (opt-in1.4)
- src/graph_memory/extraction/worldbuilding_profile_catalog.py (exact1.4 identity)
- src/graph_memory/extraction/graph_preview_runner.py (success private bundle registration only)
- tests/test_worldbuilding_edge_review.py (new)
- tests/test_worldbuilding_gazetteer_profile.py (newversion owning pipeline cases)

Parallel-independent of DOGFOOD1178 UI/turn/surface work; disjoint paths/runtime.
Frozen historical MIND extractor PRs are NOT dependencies: PRIME reserves only
this optional review orchestration hunk; roster/recap/identity/consolidation hunks
remain untouched. Rebase/re-review those old PRs before any future merge.
No serving, native DB or retained source/document write lease. Disposable APP
fixtures may test actual registered packaging; private research outputs stay out
of Git. If failure packaging needs another source path, amend contract explicitly.

## Required evidence / gates

Owning tests prove absent/direct-SDK/wrong-route/wrong-model clients are rejected
before any inference for1.4, unchanged old-profile default behavior, same injected
bounded-client writer/reviewer accounting, and actual-attempt versus invocation
counts. Use bounded-client engine seams or explicit test subclasses; no real model
calls in code tests. Owning fake-provider pipeline compares1.3(no review)/1.4(one review), exact original
kept objects, raw-generation immutability, omitted/deferred refs and diagnostics,
role-guard retention, empty/no-call, unknown/duplicate/rewritten ID failures,
no node/source/provenance change, source-qualified defaults and no new accepted
facts. Actual registered failure packaging must retain earlier raw responses and
review failure without a promotable result; hash-verify/fresh-process reopen.

Registered saved-source replay may reuse responses ONLY if request bytes/hashes
match; distinguish replay/zero new calls from fresh provider output and billing.
Any new semantic benchmark is separate exact-head evidence after independent code
review. Complete implementation→tests→cumulative diff→commit/push/PR, independent
review before merge. No full gold, native eligibility, retained publication,
source edit/restart or operator acceptance is pre-marked complete.

## Activation

Serial topology: one implementation PR for this capability. Branch
codex/worldbuilding-advisory-edge-review, checkout /tmp/buddy-advisory-review-design.
Base a8a19345e21924716d184d3b7252ba8dd5a68f70. Current open PRs inspected:
frozen1139/1142-1149 do not own active edits;1178 merged and settled.
DOGFOOD/SERVER own serving rollout; this lane owns no ports/retained databases.
Use existing general review output ceiling; caller budget must fit the full flow,
with no automatic increase. Lazy bounded-client validation avoids import cycles.
Private tests/evidence under /tmp; no provider calls before implementation review.

## Successful evidence persistence amendment

ARCHITECTURE accepted tenth-path amendment2997e724972ffe37cd5d74c79a11bd51b744930c.
PRIME activates this bounded runner edit; implementation review remains required.
The actual registered runner discards return-only pass outputs/envelope/diagnostics.
Add optional CategoryGraphExtractionResult.private_response_evidence (defaultNone)
for a strict JSON-safe versioned dmb_private_extraction_review_bundle_v1 SUCCESS
bundle: exact seam responses, ordered request hashes, safe GE observations and
available attempt artifact refs, source/profile identity/hash, advisory original
objects and pre-review envelope. This is private lineage, not another promotable
candidate, raw wire response, public diagnostics or publication approval.

Before candidate file/registration/status advancement, validate strict JSON and
bundle identity, persist this optional string using accepted atomic0600/fsync
writer, and compute existing RAW_MODEL_RESPONSE URI/hash component. Only after
successful evidence persistence write the candidate file; register both components
together through existing PREPARED->EXTRACTED admission. The registry forbids
same-status component checkpoints. Filesystem writes and DB admission are NOT one
atomic transaction. Later candidate-write/registry failure may leave private
orphan files, but cannot report success or admit a candidate without evidence. No new kind/schema; old profiles withNone remain unchanged.
Rename the private writer honestly within this leased runner if needed; preserve
1179 failure behavior. Success storage/serialization failure cannot return or
register a reviewable candidate or claim evidence retained. No automatic replay.
The same leased test file exercises actual registered success/failure in unique
APP fixture DBs, fresh-process reopen/hash/0600, canonical envelope-to-IR equality,
oldprofileNone/no artifact and storagefailure after successful provider result.
No serving, retained native data, model call or default routing lease is added.

## Implementation evidence for review

Author checks: new advisory pipeline/subset/executor/evidence tests; actual
registered synthetic success and failure, separate-process bundle reopen/hash0600,
old-profile artifact absence, and post-provider storage failure with PREPARED status,
no candidate file/components. Existing1179 failure cases remain covered. No provider
calls, retained corpus/World mutation or serving change. Independent exact-head
implementation review remains required; semantic benchmark and publication held.
