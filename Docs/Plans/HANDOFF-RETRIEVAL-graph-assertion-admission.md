# Proposed amendment to PR #2462

Active under explicit user approval. This amendment would keep one serial PR and replace the controller identity split with post-selection name admission. The last verified remote base is 5d116c9d7 and the current draft head is e85912af398a717a6103bab7a4874ef125fb4394. Refresh both refs before editing.

The write lease would cover the existing handoff, native_plan_assertions.py, native_execution.py, native_writer.py, plan_source_turn.py, and the existing native assertion, execution, and writer owner tests. The current identity split changes in native_graph_reads.py and plan_jev_driver.py would be reverted within the same PR.

New Plan turns would pin the admission rule in the existing execution policy. Absence of that field would preserve historical policy serialization and reconstruction. One ordered projection would supply both the writer frame and its citation reconstruction. Omit a name only when a retained summary for the same entity repeats the name and preserves its writer-visible qualifications, evidence records, and exact source spans.

Run focused tests for historical policy hashes, stale or mismatched evidence, and citation closure. Then use isolated evaluator state and the existing ordinary benchmark workflow to measure all 15 contexts and 72 evidence items, provider input tokens, request-to-context-ready time, and delivered answer coverage, attribution, chronology, and citations. Record the measured trade-offs before adoption.
