# RETRIEVAL: initial source discovery

Status: ACTIVE. Root owns design, implementation, local verification and delivery.
The user grants standing merge authority. No deployment or primary migration is
included. Six-second request-start→context-ready retrieval remains unproven.

## Slice and topology

One serial Buddy PR on `codex/retrieval-initial-source-discovery`, pinned base
`7ec9bcec9beed23c71f911943062bfc9c94bda51`. Reuse the clean recorded-names-control
checkout; no serving runtime was found there. PR2304 (guarded session),2309
(bootstrap reuse),2301 (selected-record owner) are merged; no unmerged behavior
dependency or SDK/Core change. Open PR inventory found no overlapping runtime
implementation. Storage-resource PR2308 owns only utility/guide/tests.

Outcome: current native readonly Plan discuss/clarify performs ordinary lexical
source discovery after mandatory authored reads and before the first retrieval
choice. Reuse the existing Core capture/catalog/term matcher and observation.
Metadata reaches the decision model; source bodies require explicit later choices.

Hypothesis: earlier discriminating navigation can avoid unnecessary full-source
reads and subsequent decisions. All15 retained source searches were mixed with
other selected work; there is no guaranteed search-only round to eliminate.
This is a controlled experiment, not an adopted speedup or QA success claim.

## Exclusive expected writes

- This handoff.
- `src/application_state/agent_conversation/native_corpus.py`
- `src/application_state/agent_conversation/native_reads.py`
- `src/application_state/agent_conversation/native_execution.py`
- `src/application_state/agent_conversation/native_retrieval.py`
- `src/application_state/agent_conversation/native_plan_session.py`
- `src/application_state/agent_conversation/service.py`
- `src/application_state/agent_conversation/types.py` (concrete event export only)
- `src/application_state/migrations/versions/20261109_0145_initial_source_discovery.py`
- `apps/live_control_server/services/corpus_source_navigation.py`
- `apps/live_control_server/services/plan_jev_harness.py`
- `tests/application_state/test_surface_native_acquisition.py`

No new storage table, SDK producer, ranking/embedding layer, ingestion, label repair,
composition change, writer grading, alternate default, fallback or benchmark script.
Expansion beyond these owners requires a steward scope checkpoint.

## Resolved design gates and invariant

Independent design critique is retained in
`retrieval-record-transitions-v1/initial-source-discovery-design-review-v1.json`.
Root resolved its three gates before implementation:

1. `NativeInitialSourceSearchAuthorizedV1` links the actual
   `NativePlanRequestedWorkSelectedV3` discuss/clarify choice, exact question,
   receipt/policy commitments and frozen source authority. It has no provider ID.
   Full phase admission refuses wrong/early/late/duplicate/foreign grants and
   unsettled mandatory authored reads. Do not fake a controller search vote.
2. Commit the grant before host Core inspection. Use the same actual materializer
   for this grant and historical selected grants. A retained grant with no
   observation refuses before another Core call or provider; no automatic repeat.
3. Empty reader-fence0145 follows0144. No source/user rows or physical tables are
   rewritten. Only new isolated databases may be upgraded in this experiment;
   the original evaluator and primary remain unchanged.

Current readonly navigation requires the exact new grant plus matching observation.
A retained success is replayed through actual APP admission before reuse, refreshing
public state from its guarded owner. Historical codecs retain old records exactly;
current Plan cannot silently resume the retired controller-search route. Build,
Play, writing work and legacy action families keep their existing explicit owners.

Mandatory authored reads precede discovery. It precedes the first retrieval
request preparation. Unavailable source authority stays explicitly unavailable.
Search catalogs are navigation, never writer evidence. Explicit section/direct/
full-document choices, Core current-access checks, exact immutable bytes, source
qualifications and per-success durable commits remain intact.

## Verification and acceptance

Run CI locally; do not dispatch GitHub CI. Review exact cumulative base→head.
Owner checks exercise actual isolated APP commits and guarded sessions, grant and
observation reload, forged work/question/policy/source authority, duplicate/late
requests, interrupted grant-only recovery, old-route refusal and forged public
catalog refresh without another Core capture. Inspect actual SDK bytes for
metadata-only exposure, and compare selected extents/handles/text to exact Core
source support. The migration test proves older readers refuse the new codec.

The retained generic completion fixture predates current semantic Plan work; its
writer-output tests are not this goal's oracle. Do not repair writer behavior to
get this slice green. Actual context-ready captures still must traverse the real
current writer input-authorization boundary without generating a response.

Use the consolidated `evals.buddy_benchmark.workflow capture-context` and report
commands. No new question-specific tooling. Preserve the frozen original baseline
in `retrieval-native-storage-comparison-v1` and current-source reference capture
in `retrieval-plan-session-context-v1` (15/15 contexts,72/72 atoms). Reuse unchanged
sources, question set and provider/dependency settings; exclude Gold/evaluator
hints from requests. Current capture request→ready was12.155s median; compatible
accepted→ready10.428s. Historical missing request-start clocks remain unknown.

After local owner proof and independent code review, run one changed15-case cohort
on isolated APP clones, with ordinary paid attempt accounting and no writer IO.
Preserve all artifacts, calls, timings and actual billed cost or unknown. Independently
check all15 context cases for required evidence coverage, attribution, chronology,
uncertainty, exact quote/source support and citation eligibility. Writer response
quality is excluded. Report cumulative nested work separately from actual elapsed
request-start→context-ready, including per-case decisions/reads and regressions.

Adopt only if context invariants pass and complete-cycle measurements show a
material gain toward six seconds. Added discovery may outweigh avoided reads.
Preserve rejected/failed findings; no unchanged reruns until one passes, weakened
Gold or hidden fallback. A passing local helper is not whole-cycle proof. Keep the
broader goal active until its actual requirements are verified.

## Evidence/resources

Port55447 is the isolated PostgreSQL evaluator. Tests allocate and remove only
owned disposable databases. Existing frozen `.venv` dependencies remain pinned.
Large logs/artifacts use this checkout's ignored `out/retrieval-initial-source-discovery-v1`
on the verified Projects volume. Original evidence/resources are preserved.
No provider calls occurred during design/owner verification.

Working-review HOLD about accepting old receipts was corrected by exact grant
qualification plus actual admission replay. All9 retired-contract/old Rules fixture
failures in `test_plan_jev_harness.py` reproduced on exact unchanged base7ec9bcec9;
retain that control rather than absorb adjacent fixture repairs. Local check and
candidate results remain external evidence until verified; this handoff does not
pre-mark the in-flight PR merged or the latency goal complete.
