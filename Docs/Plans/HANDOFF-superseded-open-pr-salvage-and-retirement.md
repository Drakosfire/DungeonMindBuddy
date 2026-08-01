# HANDOFF — Mine and retire superseded open PRs

**Created:** 2026-07-31
**Status:** ACTIVE — until salvage PR #464 merges; then archive pointer to evidence ledger.
**Canonical handoff path:** `Docs/Plans/HANDOFF-superseded-open-pr-salvage-and-retirement.md`
**Repository:** `Drakosfire/DungeonMindBuddy`
**Original mining base:** `c371d43178a2b83da299319a047f93bae50d0959`
**Re-anchored implementation base (2026-08-01):** `2fa5b7909a28f0c7cf15aab35a56db68ef67ca2e` (`origin/main` tip; includes merged #462)
**Suggested branch:** `chore/mine-retire-superseded-prs`
**Salvage PR:** [#464](https://github.com/Drakosfire/DungeonMindBuddy/pull/464)
**Evidence ledger:** [`Docs/Reports/REPORT-superseded-open-pr-salvage-2026-07-31.md`](../Reports/REPORT-superseded-open-pr-salvage-2026-07-31.md)

> **Re-anchor (2026-08-01).** Mining was performed against exact base `c371d431…`. Before merge, this branch was reconstructed onto `2fa5b790…` because #462 merged into main. All temporal claims below that still say “#462 is open / protected-unmerged” are superseded by the Protected-state table and REPORT §6 as refreshed on this re-anchor. Protocol sections (§0–§10) are the complete authoritative dispatch — do not replace them with a summary.

---

## §0 Capability decomposition decision

Candidate outcome

Independently useful?

Public/durable contract changed?

User or operator surface changed?

Failure model changed?

Independently testable or revertible?

Decision

Determine what unique value remains on eight obsolete PR branches

No, reconnaissance supporting salvage

No

No

No

No

Include as mandatory first phase

Reimplement small, still-relevant behavior on current main

Yes

Maybe

Maybe

Maybe

Yes

Include only when bounded by this handoff

Preserve valuable evidence/design/future obligations that should not ship as code now

Yes

Documentation only

No

No

Yes

Include

Close each mined source PR with a traceable disposition

Yes

GitHub workflow state

Operator surface only

No

Yes

Include

Finish the complete Build graph-reference and dogfood loop from #432

Yes

Yes

Yes

Yes

Yes

Named successor unless #431 has merged and the remaining change is demonstrably tiny

Land a universal PDF/OCR ingestion capability from #395

Yes

Yes

Yes

Yes

Yes

Named successor unless already required by a current merged authority and bounded to this salvage invariant

Replace Graph Review loading with the complete #444 branch

Yes

Yes

Yes

Yes

Yes

Reject wholesale; mine only safe behavior

Replace merged #462 with #460’s parallel Threat-publication implementation

Yes

Yes

No

Yes

Yes

Reject

Merge or cherry-pick any source PR wholesale

No

Unbounded

Unbounded

Unbounded

Poor

Prohibited

Selected capability: Current main becomes the sole reachable home for every still-relevant contribution from the eight retiring PRs, after which each source PR is closed with a durable disposition record.

Why the included work shares one invariant: This is a one-time reconciliation/migration boundary. Code, tests, reports, successor notes, and PR closures are included only because they eliminate hidden authority that otherwise remains stranded on obsolete open branches.

### Named successors:

Build World Reference Loop and Build dogfood workflow after #431.

PDF/OCR source lineage if it remains a current product priority after revalidation.

Browse-first committed World Graph session loading if current Graph Review still needs it after strict-projection revalidation.

Threat publication identity resolution and governed commit after #462.

Any substantial UI completion discovered from #432 or #444 that cannot be proved as a small salvage change.

Mission falsification test: This is no longer one salvage slice if the worker must introduce a new general-purpose framework, a second active implementation chain, a new durable graph-writing authority, a new statblock publication API, or a broad product surface that would remain independently useful without the repository-retirement outcome.

## §1 Mission

Current main preserves every still-relevant behavior, test, design finding, or future-work obligation that previously existed only on PRs #231, #395, #432, #433, #444, #449, #459, or #460, and those eight source PRs are closed with an explicit, reviewable disposition.

Invariant

For each source PR, every materially distinct contribution is classified as
IMPLEMENTED, PRESERVED, ALREADY_PRESENT, or REJECTED with current-main evidence.

Nothing is copied wholesale from an obsolete branch. No active-thread ownership
is overwritten. No unsafe fallback or parallel public contract is revived.

A source PR is closed only after its retained value is reachable from the
salvage PR or a named durable successor artifact.

### Mission falsification test

This is not one salvage slice if implementation must also finish an entire
Build, PDF-ingestion, Graph Review, or Threat-publication product milestone.
Those become named successor handoffs; the useful obligation is preserved before
the obsolete source PR is closed.

## §2 Context, authority, and boundaries

Field

Required content

Parent authority

Operator’s four-thread model: Build, UI, Statblock, Timeline; open-PR audit performed 2026-07-31

Repository rules

AGENTS.md; .cursor/rules/external-agent-pr-loop.mdc; .cursor/skills/external-agent-pr-loop/SKILL.md

Base revision

c371d43178a2b83da299319a047f93bae50d0959

Exact source inputs

The eight PRs and exact source heads listed in §2A

Protected state

#442 retained; #431/#463 active and outside this worker’s authority; #462 MERGED at 2fa5b790… (2026-08-01) — classify #460 against merged main, do not modify merged publication paths

Named successor

Fresh current-main PRs for substantial Build, PDF, Graph Review, or Threat publication work

What remains false

This slice does not promise complete Build dogfood, PDF ingestion, graph publication, Threat projection, or Timeline completion

Explicit non-goals

Merging old branches; rebasing source PRs; resolving #431 review findings; replacing #462; Timeline work; graph snapshot storage; universal cleanup of all closed branches

Read authoritative inputs in order before changing code:

AGENTS.md.

.cursor/rules/external-agent-pr-loop.mdc.

.cursor/skills/external-agent-pr-loop/SKILL.md.

Original mining used origin/main at exact base c371d43178a2b83da299319a047f93bae50d0959. Re-anchored implementation base (2026-08-01): 2fa5b7909a28f0c7cf15aab35a56db68ef67ca2e (includes merged #462).

Current active/protected PR metadata and changed paths for #431, #442, and #463, plus merged #462 publication paths on main, for collision avoidance only.

Each source PR body, comments, reviews, commits, and full changed-file list at the exact source head in §2A.

Current-main implementations and tests corresponding to each source path.

Current plans, trackers, reports, and design decisions governing Build, Graph Review, extraction, and Threat/statblock publication.

Mining started from exact base c371d43178a2b83da299319a047f93bae50d0959. On 2026-08-01 this salvage branch was re-anchored onto 2fa5b7909a28f0c7cf15aab35a56db68ef67ca2e after #462 merged. Further main movement still requires an explicit re-anchor report; do not silently substitute a newer base.

### Authority precedence

1. Repository rules and merged architecture/decision documents on current main
2. Current active tracker and roadmap state on current main
3. This handoff
4. Current-main implementation and owning-boundary tests
5. Source PR code, tests, reports, review discussion, and commit history
6. Historical PR descriptions and branch-local “current” claims
7. Chat summaries

Source PRs are evidence, not authority.

## §2A Exact source PR inventory

PR

Exact source head

Historical purpose

Initial posture

#231

006e53b27f175de0fb96f2a706745701bbbece84

C2S23 contextual-vocabulary ablation dogfood report and runner

Mine research evidence; port runnable harness only if still compatible and non-duplicative

#395

bb7e4eb7485ee0923b5c45c01abf93ba9f68040a

Build PDF/OCR lineage pilot stacked on old worldbuilding-profile work

Most stack likely landed elsewhere; reassess missing PDF lineage separately; no dormant framework

#432

5cdcd107e50cc89f16e44c4072705549e28d696e

Build graph-reference canvas, exact-run inspector, Find existing, starter canvas

Product behaviors are valuable; architecture is obsolete and stacked on #431; mine behavior, not implementation

#433

543847c9484a0a57f1950f389680db70b4841bac

Split ExtractionRun lifecycle truth from review-package inspection truth

Strong direct implementation candidate if still absent on main

#444

127168de48d2d94803f906ff69a26bbc9fefaf82

Browse committed World Graph sessions in Graph Review

Mine browse-first UX/server intent; reject first-wins projection tolerance

#449

2369d32b3b574104cc09fc8abb0bddef69031f51

Record R0-A validation failure, diagnostics handoff, structured-output pattern

Preserve durable evidence/pattern only after removing stale authority claims

#459

0abdb55d5779273e406643221e0a41e959371055

Finalize PR431 handoff

Expected no unique value after #431 reconstruction; prove before rejecting

#460

a4d95b68907a8b99e0991616817cd3c6a9e466e8

Parallel SBW09a durable Threat publication lifecycle

Mine adversarial cases or lessons missing from #462; never revive parallel API/models

## §3 Observable-path and ordered-workflow inventory

Observable path

Current behavior

Required behavior

Same invariant?

Owning boundary

Inspect one source PR

Value is mixed with obsolete code and stale claims

Produce itemized contribution ledger grounded in source head and current main

Yes

Mining report

Contribution already exists on main

Old PR remains open and misleading

Record exact current-main path/test/commit evidence; do not duplicate

Yes

Mining report + diff review

Small useful behavior is absent

Value exists only on obsolete branch

Reimplement on current main with current types/ownership and owning-boundary tests

Yes

Current owning layer

Useful behavior is substantial or collides with active work

Temptation to broaden salvage PR

Preserve as named successor handoff/backlog item with exact source references; do not implement here

Yes

Plan/report authority

Historical evidence remains useful

Report or design exists only on branch

Move or rewrite into current docs with truthful status banner and current authority links

Yes

Docs

Historical claim is stale or unsafe

Branch describes rejected architecture or obsolete sequencing

Record REJECTED with reason; do not preserve misleading “active” status

Yes

Mining report

Source PR closure

PR remains in open work queue

Close only after ledger and retained artifact are present on salvage branch

Yes

GitHub PR state

Closure command partially fails

Some PRs close and some remain open

Report exact states; retry idempotently; do not claim completion

Yes

GitHub workflow

Salvage PR later fails review

Source PRs may already be closed

Closed source branches remain recoverable; reopen only if operator directs; fix salvage PR rather than restoring old authority

Yes

GitHub + branch history

Protected PR check

Worker may accidentally include #442 or active threads

Verify #442 remains open; #431/#463 are unchanged by this operation; #462 remains MERGED and its publication paths are not rewritten by salvage

Yes

GitHub metadata

Ordered execution sequence

Verify base and protected PR state.

Fetch all eight source PRs and record exact source heads.

Inspect full diff, commit messages, PR body, comments, reviews, and current-main equivalents.

Create the mining ledger before implementation decisions.

Classify every materially distinct contribution.

Freeze the actual implementation/preservation subset and verify it fits §4.

Reimplement or preserve from current main; do not cherry-pick.

Run owning-boundary verification.

Open the salvage PR with the complete disposition ledger.

Close each source PR with the standardized comment in §8A.

Update the salvage PR body/report with closure evidence.

Verify all eight source PRs are closed and protected PRs remain in the expected state.

## §4 Files in scope — allowlist

The salvage report is mandatory. Other listed paths are conditional and may change only when their source contribution is classified IMPLEMENTED or PRESERVED.

Action

Path

Purpose

Create

Docs/Reports/REPORT-superseded-open-pr-salvage-2026-07-31.md

Canonical per-PR contribution, decision, evidence, and closure ledger

Create

Docs/Plans/HANDOFF-superseded-open-pr-salvage-and-retirement.md

Check in this authoritative dispatch if repository workflow requires the handoff to travel with the PR

Create or modify

Docs/Design/PATTERN-openai-structured-outputs-complex-contracts.md

Preserve only the verified durable design pattern mined from #449; remove stale branch-local authority

Modify

apps/live_control_server/models/extract_promote.py

Conditional #433 inspection-status contract using current-main vocabulary

Modify

apps/live_control_server/services/extract_promote.py

Conditional #433 review-package inspection classification at owning service boundary

Modify

tests/test_live_extract_promote_api.py

Conditional #433 route/response proof including structured diagnostics

Create or modify

Docs/Plans/PR-TRACKER-threat-statblock-authoring-projection.md

Only if required to preserve one still-current obligation from #449/#460 without duplicating existing authority

Create or modify

Docs/Roadmaps/ROADMAP-threat-statblock-authoring-projection.md

Only if current roadmap lacks a retained obligation proven by #449/#460

Create or modify

Docs/Reports/GRAPH-MEMORY-VOCABULARY-ABLATION-DOGFOOD-C2S23-MIREWARD.md

Conditional preservation of #231 evidence with truthful historical/research status

Create or modify

evals/graph_memory_layer/run_c2s23_vocabulary_ablation_dogfood.py

Conditional port only if current harness still supports it and it adds unique repeatable evidence

Bounded discovery exception

Directories and maximum additional changed paths:

1. apps/live-control-ui/src/buildSurface/
   Maximum additional paths: 6
   Allowed kinds: current-main Build component, helper, CSS, or focused test.
   Decision rule: only a small user-visible behavior from #432 that remains
   absent, does not depend on unmerged #431 code, and does not import Plan-owned
   implementation as a permanent Build dependency.

2. apps/live-control-ui/src/planSurface/graphReviewWorkbench/
   Maximum additional paths: 6
   Allowed kinds: current Graph Review load/inspection component, helper, or
   focused test.
   Decision rule: only safe browse-first or inspection-truth behavior from
   #432/#444; no broad workbench rewrite.

3. apps/live_control_server/services/ and apps/live_control_server/routes/
   Maximum additional paths: 4 total beyond the exact #433 paths.
   Allowed kinds: one existing service/route plus focused test support needed
   to expose safe committed-session browsing or exact-run inspection truth.
   Decision rule: must use current strict graph projection and current public
   model vocabulary; no new graph-write authority.

4. src/graph_memory/extraction/
   Maximum additional paths: 4
   Allowed kinds: bounded PDF lineage value object/source adapter and package
   export only.
   Decision rule: include only if current product authority already admits PDF
   input and the capability can be exercised end-to-end in this PR. Dormant
   foundation code is prohibited.

5. tests/
   Maximum additional paths: 6
   Allowed kinds: focused owning-boundary tests for a conditionally included
   implementation path.

6. Docs/Reports/, Docs/Plans/, Docs/Design/
   Maximum additional paths: 8
   Allowed kinds: archival report, successor handoff, tracker pointer, or
   decision/pattern preservation directly tied to one source PR disposition.

For every discovered path, the mining report must state:

source PR and source path;

why current main does not already own the value;

why implementation belongs in this salvage PR rather than a successor;

owning-boundary verification;

collision analysis against #431, #462, and #463.

If any maximum would be exceeded, stop and propose a successor. Do not enlarge the exception.

## §5 Explicitly out of scope and collision denylist

Path, layer, or capability

Why prohibited

PR #442 and out/graph_memory/worlds/eldyrwild/**

Intentional transfer vehicle retained open; not part of cleanup

PR #431 branch or its graphReference/** implementation

Active Build prerequisite under separate review/ownership

apps/live_control_server/models/threat_publication.py and canonical #462 paths

Active Statblock implementation; do not edit from salvage branch

Any threat_statblock_publication* path from #460

Parallel superseded public contract; never revive

Timeline prompt/eval paths owned by #463

Active Timeline thread

First-wins edge-map, assertion, or projection tolerance from #444

Explicitly rejected; strict projection remains authority

Wholesale #432 Build shell or Plan imports

Obsolete stacked architecture and cross-surface ownership leakage

Auto-creating production Mireward starter content on bare /build

Dogfood fixture behavior is not automatically product behavior

New graph mutation, publication, confirmation, or commit endpoint

Separate durable authority

New universal source-adapter framework

Separate architecture capability

Raw provider payload retention

Rejected by Statblock failure analysis

Schema relaxation or blind retry for statblock generation

Rejected response to R0-A failure

Reopening or rewriting #231/#395/#432/#433/#444/#449/#459/#460 after closure

Closure is final for this operation unless operator explicitly reverses it

Nearby useful work is not authorization.

## §6 Mining and implementation contract

## §6.1 Classification vocabulary

Every materially distinct contribution gets exactly one primary disposition:

Disposition

Meaning

Required evidence

IMPLEMENTED

Reimplemented in the salvage PR using current-main ownership and vocabulary

Changed paths, tests, and source-to-current mapping

PRESERVED

Kept as a truthful report, design pattern, test fixture, or named successor obligation

Durable current-main artifact path

ALREADY_PRESENT

Current main already owns equivalent or better behavior

Exact path, symbol/test, and comparison note

REJECTED

Unsafe, obsolete, duplicative, stale, or no longer aligned

Explicit reason and current authority

“No action,” “not needed,” and “superseded” without evidence are invalid dispositions.

## §6.2 Universal source-to-current rule

Input:
  Exact source PR head, source diff, source discussion, and current-main code/tests.

Output:
  One itemized mining decision per materially distinct contribution.

Invariant:
  Same as §1.

Failure behavior:
  Cannot determine current owner → preserve as an explicit unresolved successor;
  do not guess and do not close until that successor is durable.

Replay / idempotency:
  Re-running the audit on the same source heads and base must produce the same
  contribution inventory and materially equivalent decisions.

Trust boundary:
  Verifies: source content, current-main equivalence, tests, and protected ownership.
  Records without re-proving: historical operator observations clearly labeled as such.
  Rejects: branch-local claims of “current,” “active,” or “merge-ready” without
  current-main verification.

## §6.3 Per-PR mining matrix

PR #231 — vocabulary-ablation dogfood

Candidate value:

The C2S23 Mireward research report and its observed comparative findings.

A deterministic runner, only if it still executes against current eval contracts.

Evidence that edge + node vocabulary packets outperformed baseline in that bounded historical cohort.

Required treatment:

Check whether the report or equivalent findings already exist on main.

Check whether the current extraction/evaluation architecture has superseded the runner.

If preserving the report, add a RESEARCH_ONLY or HISTORICAL banner and name current authority.

Port the runner only if it passes unchanged-in-purpose against current fixtures and does not recreate obsolete experiment infrastructure.

Do not promote its bounded result into a general production claim.

PR #395 — PDF/OCR lineage pilot

Candidate value:

Page/region evidence identity tied to exact PDF and OCR digests.

Fail-closed page-map validation.

Exact ExtractionRun round-trip of PDF evidence.

Pilot report and fixture-backed proof.

Known current-main caution:

Extraction profiles and worldbuilding profile infrastructure have since landed independently; do not re-port those portions.

PDF lineage files were absent at the audited main tip, but absence alone is not product authorization.

Required treatment:

Determine whether current Build/product authority admits PDF as a current input path.

If yes and the complete path can be proved end-to-end within the bounded exception, implement the smallest exact lineage contract.

If no, preserve the report and create a named successor handoff that records the exact value objects, digest identity, page/region semantics, and required proof.

Do not add unused adapters, routes, or UI that no current product path exercises.

PR #432 — Build graph-reference canvas and stay-on-Build inspection

Candidate value:

Build can search existing World Graph objects, inspect them, insert an exact reference, save, reload, and reopen the reference.

Extraction result/summary remains on Build rather than forcing navigation to Graph Review.

Exact-run inspector is read-only and can open full Graph Review secondarily.

“Find existing object” pre-fills search but does not auto-insert.

Reusable behavior/tests around Build document persistence and reference reopening.

Unsafe or obsolete implementation traits:

Stacked on unmerged #431.

Build shell imports Plan-owned resolvers/adapters.

Broad combined slice with starter content, graph references, inspector, and navigation changes.

Required treatment:

Compare behavior against current main and active #431.

Do not implement #431 successor behavior before #431 merges.

Preserve missing behaviors as the next Build dogfood handoff when blocked by #431.

A tiny orthogonal behavior may be implemented only if it requires no #431 code and no permanent Build → Plan implementation dependency.

Treat Mireward starter content as a dogfood fixture candidate, not automatic production initialization.

PR #433 — inspection truth

Candidate value:

An ExtractionRun may remain reviewable while its review package reports a separate inspectionStatus such as blocked or invalid_evidence.

Structured false_anchor_quote and span_ref diagnostics remain visible.

Lifecycle truth and inspection truth are not collapsed.

Required treatment:

Confirm the fields and behavior are still absent on current main.

Reimplement using current model serialization aliases and error vocabulary.

Prove at route boundary that a reviewable run with unknown span evidence returns runStatus=reviewable, inspectionStatus=blocked.

Prove false anchor evidence returns inspectionStatus=invalid_evidence with both quote and span diagnostics retained.

Do not require #432 frontend code for the server contract to be useful.

This is the strongest default IMPLEMENTED candidate.

PR #444 — browse committed World Graph sessions

Candidate value:

Graph Review should browse sessions/contributions from committed World Graph state, not depend exclusively on ephemeral ingest-run catalogs.

A loaded recap should project committed state.

Browse-first UI vocabulary may be more coherent than run-first loading.

Rejected behavior:

First-wins edge-map or divergent-shadow tolerance.

Any weakening of strict assertion/evidence/projectability invariants.

Required treatment:

Determine what portions of browse-first loading have already landed or been replaced.

Mine safe session catalog/projection behavior only if it uses current strict graph APIs.

If the remaining capability requires server + broad workbench rewrite, preserve it as a successor handoff and close #444.

Record explicit rejection of first-wins tolerance in the mining report.

PR #449 — R0-A failure evidence and structured-output pattern

Candidate value:

Durable R0-A FAIL_PRODUCT evidence.

Four-zone diagnostic model for provider/schema/Pydantic/domain failures.

Reusable complex Structured Outputs contract/compiler pattern.

Typed diagnostics requirement and prohibition on raw provider payload retention, blind retry, or schema relaxation.

Known current-main caution:

The active Statblock roadmap has already been re-anchored and incorporates the R0-A sequencing consequence.

Branch-local “ACTIVE” or next-PR sequencing claims are stale unless reverified.

Required treatment:

Avoid duplicating the R0-A report if current reports already preserve the factual evidence.

Preserve the Structured Outputs pattern only after verifying it against current DungeonMindServer code or relabeling it as RESEARCH_ONLY/ACTIVE_REFERENCE with exact external authority boundaries.

Preserve general lessons; remove branch/SHA-specific active sequencing claims.

Do not dispatch DMS/Buddy diagnostics implementation from this salvage PR unless current repo authority explicitly places it next and it fits §4.

PR #459 — PR431 handoff finalization

Candidate value:

Potentially only historical reconstruction evidence for #431.

Required treatment:

Compare the file with the handoff embedded in #431 and any current-main authority.

If no unique constraint remains, classify every contribution ALREADY_PRESENT or REJECTED and close.

Do not add a second active PR431 handoff.

Expected outcome: no implementation.

PR #460 — parallel Threat publication lifecycle

Candidate value:

Adversarial cases, persistence lessons, route error mapping, bounded-history/path-safety checks, or tests not present in canonical #462.

Rejected behavior:

Parallel threat_statblock_publication* models, routes, stores, or service authority.

Numbered obsolete handoff/tracker edits.

Replacing #462.

Required treatment:

Compare each behavioral guarantee and adversarial test to #462, not merely file names.

If #462 already proves it, classify ALREADY_PRESENT with exact test evidence.

#462 has merged (2fa5b790…). If a valuable #460 guarantee is still missing from merged main, preserve it as a named successor obligation or add a focused owning-boundary test on canonical paths only after handoff refresh; do not revive parallel APIs.

If #462 has merged before dispatch re-anchor, a genuinely missing focused test may be added to canonical current-main paths only after handoff refresh.

## §6A State and fallback matrix

Observable path

Loading / inspection

Exact useful contribution

Ordinary no-unique-value

Dependency unavailable

Integrity/contract failure

Stale/superseded claim

Retry/replay

Source PR audit

Defer decision until full source/current comparison

Classify and retain

ALREADY_PRESENT or REJECTED

Preserve unresolved successor; do not guess

Stop if source head cannot be fetched or differs

Treat branch-local current claims as untrusted

Idempotent on same heads/base

Code salvage

No code before ledger decision

Reimplement on current main

No change

Prefer PRESERVED successor over speculative fallback

Fail closed; do not weaken current contract

Never port stale compatibility behavior by default

Re-run owning tests

PR closure

Not allowed before retained value is reachable

Close with exact disposition

Close after rejection evidence

Retry GitHub operation

Do not claim closure when state unknown

Closed PR remains historical evidence only

gh pr close is idempotent

No unnamed fallback is permitted.

## §6B Identity matrix

Situation

Required matching rule

Ambiguity behavior

Fallback permitted?

Persistence consequence

Source PR

Exact PR number + exact head SHA

Stop if head changed

No

Mining report records immutable source head

Source contribution

Exact path/symbol/test/behavior

Itemize separately when mixed

No first-win

Each material contribution gets one disposition

Current equivalent

Exact current-main path/symbol/test/observable behavior

If approximate, classify unresolved rather than already present

No label-only equivalence

Report records evidence

Renamed/recreated feature

Behavioral and contract equivalence, not filename resemblance

Require explicit mapping

No silent rebinding

Preserve current authority path

Closed PR

Exact PR number

No substitute

No

Closure comment links salvage PR/report

## §6C Persistence and replay matrix

Operation

Durable representation

Round-trip guarantee

Duplicate/replay behavior

Compatibility/migration

Rollback/reversion

Mining decision

Salvage report row

Every source contribution remains attributable

Reaudit updates evidence, not identity

Old branch remains readable

Revert salvage PR restores main, not old PR authority automatically

Preserved successor

Checked-in handoff/tracker/report

Exact source PR/head and missing capability survive closure

Do not duplicate successor entries

Current authority links required

Can be removed by later explicit decision

Source PR closure

GitHub closed state + comment

PR remains inspectable with source branch history

Repeated close is harmless

No merge implied

Reopen only by operator decision

## §6D Predecessor-to-current mapping

The mining report must contain this table for every implemented contribution:

Source PR/path/behavior

Source shape and assumptions

Current owner/path

Transformation

Proof

<exact source>

<real branch shape>

<current-main owner>

<reimplemented / adapted / narrowed>

<test/scenario>

“Copied from PR” is not a valid transformation.

## §7 Verification ownership map and commands

Mandatory repository and closure verification

Guarantee

Owning boundary

Command or scenario

Expected evidence

Exact base used

Git

git rev-parse HEAD before first change

c371d43178a2b83da299319a047f93bae50d0959

Source heads are exact

GitHub

gh pr view <N> --json headRefOid for all eight

Matches §2A

No unexpected path

Git

git diff --name-only 2fa5b790...HEAD

Every path in §4 or reported bounded exception

No wholesale source merge

Git history/diff

inspect commits and git diff --stat

Purpose-built commits; no source branch merge commit/cherry-pick dump

Mining ledger complete

Report review

inspect report against all changed files and source diffs

Every material contribution classified

Source PRs closed

GitHub

gh pr view 231 395 432 433 444 449 459 460 --json number,state,url or equivalent loop

All eight CLOSED, none MERGED by this operation

#442 retained

GitHub

gh pr view 442 --json state,title

OPEN

Active threads protected

GitHub

inspect #431/#442/#463 state/head before and after; confirm #462 remains MERGED and salvage does not rewrite its paths

No salvage-operation mutation

Formatting

Git

git diff --check

Exit 0

Conditional #433 verification

uv run pytest -q tests/test_live_extract_promote_api.py -k "false_anchor or review_package or reviewable"

Expected route evidence:

unknown/missing span evidence: response remains tied to runStatus=reviewable and reports inspectionStatus=blocked;

false anchor quote: inspectionStatus=invalid_evidence;

structured span_ref and false_anchor_quote diagnostics are preserved;

exact-source quote validation is not weakened.

Conditional UI verification

If any UI path changes:

cd apps/live-control-ui
npm test -- --run <exact focused test paths>
npm run typecheck
npm run build

Manual scenario must use the existing surface; do not build a new dogfood panel solely for proof.

Conditional graph-session verification

If any #444 browse-first behavior changes server/kernel paths:

uv run pytest -q tests/test_world_graph_sessions.py tests/test_graph_kernel_world_projection.py
uv run python -m graph_memory.union_supergraph.validate --json

Required adversarial proof: divergent or duplicate shadow assertions still fail under current strict rules; no first-wins selection is introduced.

Conditional PDF-lineage verification

If PDF lineage is implemented:

uv run pytest -q tests/test_source_artifact_pdf_lineage.py tests/test_graph_run_registry_pdf_lineage.py
uv run pytest -q tests/test_extract_promote_ops_atomic.py tests/test_live_extract_promote_api.py

Minimal live/fixture proof must demonstrate:

exact PDF digest and OCR digest identity;

page and region round-trip;

bbox optionality;

mismatch/corruption fails closed;

evidence survives exact ExtractionRun reload;

a real current product entry path consumes the contract.

If the final condition cannot be proved, PDF lineage must be PRESERVED as a successor, not IMPLEMENTED as dormant code.

Conditional #231 runner verification

If the runner is ported:

uv run python evals/graph_memory_layer/run_c2s23_vocabulary_ablation_dogfood.py

Also run the current focused tests for the harness symbols the runner imports. Record that the result is historical/bounded and not a production quality claim.

### Baseline failure protocol

For every required command failing on base, run the identical command on base and head and include:

Command

Base result

Head result

New failure?

Acceptance effect

Waiver

<command>

<exact>

<exact>

Yes/No

blocked or explicit operator decision

none or named

Do not call parity a green gate.

## §8 Required implementation handback and closure protocol

The salvage PR body and report must include:

Exact base and head SHA.

Source PR exact heads.

Per-PR material contribution inventory.

Disposition for each contribution.

Actual changed paths and focused diff stat.

Source-to-current mapping for each implemented behavior.

Exact current-main evidence for every ALREADY_PRESENT decision.

Exact authority/reason for every REJECTED decision.

Durable artifact path for every PRESERVED decision.

Every §7 result and provenance.

Protected PR before/after state.

Closure comment URL or timestamp for each source PR.

Confirmation that none of the eight source PRs was merged.

Confirmation that no source branch was used as the implementation base.

Confirmation that #442 remains open.

Named successor capabilities still false.

## §8A Standard source-PR closure comment

Post a tailored version of this comment to each source PR immediately before or as part of closure:

Closing after repository salvage review.

Source head inspected: `<exact SHA>`
Salvage PR: `<new PR URL>`
Canonical disposition report: `Docs/Reports/REPORT-superseded-open-pr-salvage-2026-07-31.md`

Disposition:
- IMPLEMENTED: <exact behaviors/paths, or none>
- PRESERVED: <exact report/handoff/successor paths, or none>
- ALREADY PRESENT: <current-main paths/tests, or none>
- REJECTED: <unsafe/obsolete/duplicative items and authority, or none>

This PR was not merged or cherry-picked wholesale. Its branch and discussion remain available as historical evidence.

The comment must not claim a feature shipped when it was only preserved as a successor.

## §8B Closure sequencing

Do not close a source PR before the salvage PR exists remotely and the disposition report is committed on its branch.

After opening the salvage PR, close all eight source PRs in the same work session.

Update the salvage report/PR body with closure evidence afterward.

If one closure fails, report partial state and retry; do not leave the task with a vague “most closed.”

Do not close #442.

## §9 Acceptance rubric

The reviewer accepts only when every bullet is true.

The worker started from exact mining base c371d43178a2b83da299319a047f93bae50d0959, then re-anchored onto 2fa5b7909a28f0c7cf15aab35a56db68ef67ca2e after #462 merged (or stopped for a further re-anchor).

All eight source heads match §2A.

Every materially distinct contribution from every source PR has exactly one evidenced disposition.

Every IMPLEMENTED item uses current-main vocabulary, ownership, and tests rather than branch-local architecture.

Every PRESERVED item has a durable current-main artifact and a named future decision boundary.

Every ALREADY_PRESENT item names exact current-main implementation/test evidence.

Every REJECTED item names the current authority or safety reason.

No source PR was merged or cherry-picked wholesale.

No active #431 or #463 ownership was modified or silently absorbed; merged #462 publication paths were not rewritten by salvage.

#442 remains open and untouched.

No threat_statblock_publication* parallel API was revived.

No first-wins graph/assertion/projection tolerance was revived.

No Build implementation permanently imports Plan-owned implementation to simulate neutrality.

No dormant PDF/source framework was added without an exercised current product path.

If #433 was implemented, route-level inspection truth and diagnostic retention are proved.

If UI changed, focused tests, typecheck, build, and existing-surface manual proof pass.

If graph-session behavior changed, strict projection adversarial proof passes.

If PDF lineage changed, exact digest/page/region round-trip and product consumption are proved.

The salvage report is truthful about historical versus current evidence.

PRs #231, #395, #432, #433, #444, #449, #459, and #460 are all CLOSED.

None of those eight is marked MERGED as a result of this operation.

Closure comments link the salvage PR/report and accurately distinguish implemented from preserved work.

git diff --check passes and every changed path is in §4 or the bounded exception.

Substantial remaining capabilities are named successors rather than hidden scope expansion.

## §10 Reviewer protocol

Review the salvage invariant before reviewing individual implementations.

Independently fetch every source PR at the recorded head.

Sample each contribution inventory against the actual diff and discussion.

Challenge ALREADY_PRESENT claims by comparing behavior, not filenames.

Challenge REJECTED claims for accidental loss of useful evidence.

Challenge IMPLEMENTED claims for wholesale copying or obsolete ownership.

Check collision with #431, #462, and #463.

Verify #442 remains open.

Audit first-wins, label-rebinding, raw-payload, schema-relaxation, and blind-retry hazards explicitly.

Verify every successor artifact is actionable and cites exact source PR/head/path.

Rerun all applicable §7 commands.

Verify closure state and closure comments after the salvage PR is opened.

Reject the PR if source PR closure happened without a durable retained-value ledger.

### Stop conditions

Stop and report instead of broadening when:

origin/main differs from the required base;

a source PR head differs from §2A;

a useful item requires changing an active #431/#462/#463 branch or contract;

a source contribution is large enough to be an independently useful product capability;

PDF lineage has no current product consumer;

browse-first Graph Review requires weakening strict graph projection;

Build graph references require unmerged #431 implementation;

#460 exposes a critical flaw in #462 that cannot be preserved as a review requirement;

current plans conflict about whether a contribution is still wanted;

more than the bounded additional paths are required;

closure permissions are unavailable;

any source PR cannot be closed after the salvage PR opens;

preserving a useful item requires inventing new architecture not present in source or current authority.

Use this report shape:

Stop condition:
Source PR and exact head:
Material contribution at risk:
Why IMPLEMENTED / PRESERVED / ALREADY_PRESENT / REJECTED is not yet defensible:
Affected active thread:
Required paths outside scope:
Proposed successor or re-anchor:
Operator decision required:

### Final dispatch check

One reconciliation invariant governs inspection, preservation, implementation, and closure.

Exact source PRs and heads are listed.

#442 and active thread PRs are protected.

Unsafe #444 and #460 behaviors are explicitly denied.

#433 has concrete owning-boundary proof if implemented.

PDF lineage cannot land as dormant foundation code.

Build successor behavior cannot bypass #431.

Closure sequencing and comments are explicit.

Conditional changed-path bounds and verification are explicit.
