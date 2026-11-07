# INGEST: bind assessment verdicts to their reviewed evidence

Status: ACTIVE. Root adopts this bounded slice under the user's resumed
DeepSeek study/tooling objective. Independent contract review is retained at
`/tmp/ingest-assessment-contract-review-resume.json`.

## Outcome and authority

An assessment cannot report a different criterion, outcome, reason or evidence
from its pinned canonical review row. This fixes projection integrity, not
semantic truth, historical unknowns, Gold or publication acceptance. A local
copy of a retained failed judgment was changed to pass and the current report
accepted it; the original artifacts were not changed.

## Lane and topology

- Fetched current `origin/main` before activation; isolated checkout is
  `/home/drakosfire/Projects/.codex/ingest-draft-navigation/DungeonMindBuddy`.
- Branch: `codex/ingest-assessment-verdict-binding`.
- **stacked** on PR #2176, exact head/base
  `1df09854b3cc3816df3382aa60da60ef97ab55c3`.
- Parent evaluator order: #2130 → #2133 → #2134 → #2137 → #2146 → #2154 →
  #2155 → #2156 → #2160 → #2165 → #2169 → #2175 → #2176, then this slice.
  Re-anchor and rebase after each parent settles. No merge authority is granted.
- Sibling #2180 owns ordinary model configuration, runner tests and
  `Docs/Guides/ingestion-evaluation.md`; this slice has no behavioral dependency
  or write overlap with it. #2182 retrieval and #2172 Play are outside scope.
- Ancestor #2155 assessment ownership transfers to this bounded successor;
  completed ancestors stay unchanged. Root writes code; reviewers are read-only.
- No port, service, provider or database write lease. Offline evidence output
  lives under the retained study workspace; primary data remains unchanged.

## Exclusive expected write set

- `Docs/Plans/HANDOFF-INGEST-assessment-verdict-binding.md`
- `src/ingestion_evaluation/assessment.py`
- `tests/test_ingestion_evaluation_assessment.py`
- `tests/test_ingestion_evaluation_comparison.py`
- `tests/test_ingestion_evaluation_normalization.py`
- `Docs/Guides/ingestion-study-assessments.md`

## Invariant and failure cases

Require the selected review row's canonical `criterion_id`, `outcome`, `reason`
and `evidence` to equal the assessment judgment. Evidence list order is exact;
review annotations may add fields. Check unknown judgments too, across all three
phases. Never infer a verdict from `status`, a synonym, or a substring.

Reject missing or contradictory canonical fields at the existing report owner,
with criterion/field diagnostics that do not dump artifact contents. Assembly
and comparison continue to call that owner; add no duplicate validator, legacy
adapter, second format or fallback. Historical bytes remain immutable and their
pinned historical validator remains reproducibility evidence. A new assessment
requires an explicitly reviewed canonical row, not an invented legacy mapping.

## Validation and delivery

Test contradictory outcome/reason/evidence, missing canonical fields, unknown
judgments, each phase and extra annotations. Exercise the actual report CLI and
the comparison boundary to show forged outcomes cannot affect counts. Run the
assessment, assembly, comparison, blinding and baseline suites. Recheck retained
modern assessments offline without regrading or rewriting them. Inspect the
exact cumulative parent-to-head diff, obtain independent subagent review, then
commit, push and open one bounded PR. No new inference, publication, model
comparison or default adoption is part of this slice.

## Author verification

The five focused suites pass: 134 tests. All 19 retained modern assessments
produce reports exactly equal to their previously retained reports under the
stricter validator. The reproduced local-copy fail-to-pass mutation is now
rejected at `assessment.report`; original artifacts and judgments are unchanged.
Evidence is retained in the study workspace at
`study-deepseek-resumption-v1/verdict-binding-retained-validation-v1.json`.
These checks establish projection integrity, not semantic nonregression or
default acceptance. Independent cumulative-head review remains required.

## Required fixture checkpoint

A broader tooling check found that the retained-normalization fixture still
pinned an identity-only review. It now retains the explicit canonical fixture
verdict, and a normalization-boundary test proves forged assessments fail before
workers/output. Root extends this slice's test lease to that one existing file;
no normalization implementation or protocol changes are absorbed. This belongs
with the parent verifier fix, not its precision-contract successor. The earlier
134-test/exact-head review remains historical; the revised cumulative head needs
its own formal review before remote delivery.
