# H3 standard recap beat-pass omission

Status: ACTIVE for bounded implementation and independent review only. Provider execution remains gated.

Authority: user-approved ingestion simplification study; owning study steward adopts this slice after independent owner/design critique. Primary data stays unchanged.

## Lane and topology

Branch `codex/ingest-h3-beat-pass-omission`, current ingest-draft-navigation checkout. Stacked experimental child of PR #2164, exact base `7fdb1a14d1c459bee2fb31f04906e967a4a18f0c`. Parent precedes this child if ever adopted; no merge authority. Rejected PR #2166 is excluded. Shared evaluator stack is read-only and separate.

Expected write lease: `src/graph_memory/extraction/recap_extraction_profile.py`, `tests/test_category_candidate_graph_extractor.py`, `tests/test_extraction_profiles.py`, `tests/test_recap_source_quote_beat_summary.py`, `tests/test_recap_source_faithfulness_profile.py`, this handoff. Steward amendment: historical full-pass beat/policy fixtures explicitly select the retained beat contract; no assertions weakened or new runtime path. No services, ports or database writes.

## Outcome and invariant

Standard recap omits only the beat model call through existing optional-profile support. Five node passes and the edge pass retain their exact requests under fixed synthetic responses. Encounter preview retains beats. Historical schemas/readers and source navigation remain intact. Beat counts, raw knowledge, bindings and beat-specific deferrals can disappear; that is measured behavior, not hidden parity.

Publication mapping currently selects nodes/edges, but that does not prove semantic redundancy. Full unchanged Gold includes knowledge found only in raw model beat responses. Host source excerpts cannot replace model knowledge.

## Verification and gates

Verify standard six-pass execution, exact surviving request equality, compact evidence dictionary equality and surviving candidate node/edge evidence. Run source quote, authority, profile, contribution and exact-run projection tests at their owners; distinguish inherited failures. Inspect cumulative diff and obtain independent exact-head review. Then pin composed donor-inclusive runtime, method/schedule/assessment hashes and qualification before any fresh provider execution. No default adoption from this screen.

Study artifacts live in `ingestion-resume/study-experiment-h3-pass-contribution-v1` under the attached visualization root. `design-draft-v1.json` is provisional and grants no provider authority. Preserve all H1/H2 failures and immutable baseline.

## Author verification

187 focused tests passed across category extraction, retained beat exact-source contracts, compact evidence, contribution mapping and source authority. Combined profile/policy run: 122 passed, six failed. All six failing node/profile snapshot tests also fail on exact parent `7fdb1a14` in isolated `/tmp/h3-parent-verification`; inherited failures remain unmodified. Original failure logs retained under `/tmp/h3-owner-tests-initial.log`, `/tmp/h3-owner-tests-v2.log`, `/tmp/h3-parent-tests-exact.log` pending pinned study evidence capture.

Synthetic surviving-request equality includes model ID, instructions, prompt and pass specification. It does not prove live semantic equivalence, cost reduction, full publication or human acceptance. No provider or database calls performed.
