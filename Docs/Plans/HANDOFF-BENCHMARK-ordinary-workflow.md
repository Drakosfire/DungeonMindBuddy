# BENCHMARK: consolidate ordinary question execution and reports

Status: ACTIVE under the operator's explicit consolidation request.

One serial PR, branch `codex/benchmark-workflow`, base fetched main
`38c3e11ff03f2d299c0b5c56249e456aa025eb86`. Existing isolated checkout;
no behavioral dependency on open Q09 PR2206. No live runtime, provider, migration
or primary-data lease. No paid calls in this slice. PRIME owns product delivery.

## Outcome and boundaries

Extend the existing `evals/buddy_benchmark` package with one parameterized ordinary
capture/report CLI. Reuse its checkpoint and inventory utilities through a shared
owner instead of importing a question-specific driver. Keep question text and
expected review data separate: model requests contain only the ordinary question
and normal product context. Never inject Gold, subject IDs or evidence handles.

Capture uses existing ordinary application routes, new-conversation CAS, actual
durable-turn correlation and protected context traces. Environment/runtime and
isolated database identity must be explicit and verified before dispatch. No
automatic migration, database provisioning, fallback or retry-until-pass path.
Offline report must not import/start the app, contact databases or providers.
Reports bind artifacts, deduplicate attempts, retain failures/unknown billing,
and separate raw operational facts from pinned independent semantic judgments.

## Demolition

Replace the ordinary ad hoc `/tmp/q09-ordinary-turn.py` launcher after retained
parity is demonstrated. Preserve its unique provenance as nonexecuting evidence.
The old oracle/Hermes gauntlet and selected-subject Q01/native fixture/S8 proofs
exercise distinct historical contracts; ordinary capture does not supersede them.
Label that distinction honestly rather than delete unique proof capabilities.
Remove duplicated checkpoint/row inventory implementations from existing callers;
parameterize their routing-key differences so retained snapshot shapes stay exact.

## Expected write set

- This handoff.
- `evals/buddy_benchmark/artifacts.py`
- `evals/buddy_benchmark/workflow.py`
- `evals/buddy_benchmark/q01_native_answer_proof.py` (shared utility extraction only)
- `evals/buddy_benchmark/s8_statement_proposal_assessment.py` (same)
- `tests/test_buddy_benchmark_workflow.py`
- `tests/test_buddy_benchmark_q01_native_answer_proof.py` (only if extraction needs it)
- `Docs/Guides/ordinary-benchmark-workflow.md`
- `.github/workflows/world-ownership-core.yml` (one-line test selection only; scope checkpoint coordinated with PRIME)

External retained manifests/reports remain evidence, not hardcoded corpus logic.
Any additional product/runtime capability is a stop/split checkpoint.

## Verification and delivery

Validate against six frozen baseline captures and corrected Q09 without executing
them again. Common reports must preserve HTTP503/409 failures, original Q09 versus
corrected Q09 identities, token totals, actual citation evidence and unknown costs.
Semantic findings remain independently reviewed data; token/keyword matching does
not become a semantic pass. Exercise capture through inert route/transport tests,
including failed preflight, fresh-conversation CAS and wrong-turn rejection.
Verify no assessment/Gold data enters dispatch and offline mode has no network or
database effects. Test immutable collision/tampering/partial evidence behavior.
Get independent subagent cumulative review, inspect diff, commit/push/open one PR.
Root does not merge without separate authority.

## Verified predecessor and implementation findings

Q09 PR2206 merged as `fdddd7932fbc75ebcd82aabd163db41108964786` and
PRIME reports local API delivery; this tooling lane remains independent of that
behavior and preserves its partial composition result.

The new report CLI replays all seven retained captures, preserving the five
original HTTP failures, exact token accounting, 49 prepared prompt witnesses and
unknown billing. Canonical review adoptions bind the four exact capture artifacts
and World/conversation/turn identity. Known Q04 citation success and corrected Q09
partial composition remain separate from HTTP delivery.

The superseded `/tmp/q09-ordinary-turn.py` ordinary launcher has been removed
only after parity verification; its hash and nonexecuting text are retained in
the established external evidence workspace. Distinct historical oracle and
selected-subject proof capabilities remain explicitly historical.

223 workflow/affected utility tests passed, excluding three unchanged historical
Q01 fixture setup errors. Those exact errors reproduce against the unchanged
baseline fixture: `lane() missing 1 required positional argument: monkeypatch`.
No broad historical-fixture repair is absorbed here. New pure checks cover
runtime/dependency drift, startup resource redirection, non-JSON/uncertain
responses, immutable dispatch, review binding and offline import isolation.

The CI test list needs one new pure module in its existing query-and-answer
command. This is a bounded scope checkpoint for durability of the same capability;
no new CI architecture or job is added.
