# INGEST: preserve epistemic qualification in recap prose

Status: ACTIVE. Root adopts this bounded producer-policy clarification under the user's ingestion implementation authorization.

## Lane and topology

Branch `codex/ingest-epistemic-qualification`, base PR #2130 at `e4233c8e0c6c2ddff3ba0126bbd9c7d3459fad82`. Stacked: merge/rebase #2130 first. Main/open PRs checked; connected-page #2129 is independent. No merge/deployment authority.

## Evidence and invariant

Current standard-v2 Session 3 run `658a20e8-4403-4eee-8b73-c728fd79db3f` loses tentative actor attribution in accepted raw actor/thread output, despite selecting the exact source quote containing the hedge. Raw, normalized and final prose are equal; the guard did not strip uncertainty. Calling a claim a source recollection does not itself make its asserted actor tentative.

Independent full Gold batch: SHA256 `a9c408da342d9cc74757ae503b07212927bc3e208bbad299a8910abf873bf38e`. Independent producer/design critique: SHA256 `75cef881a2bce23667f4f7d6e9f3a9338a9668b113f0a76ad0710cba97c3c32b`.

Replace the existing uncertain-actor sentence in `_RECAP_SOURCE_FAITHFULNESS` with an explicit distinction between attribution and epistemic force. Keep tentative actors/outcomes tentative, including recollections and reports; do not hedge confident source statements merely because they are attributed. Do not append another policy layer. This is a generic source-meaning contract, with no corpus names, benchmark answers or special cases.

## Exclusive expected writes

- `src/graph_memory/extraction/recap_extraction_profile.py`
- `tests/test_recap_source_faithfulness_profile.py`
- This handoff.

Plans, ownership, chronology, identity consolidation, prompt schemas, producers, output/reasoning budgets, retries, quotes, source authority and Worldbuilding remain outside this slice. No manual candidate rewrite or Gold weakening. Existing chronology and ownership failures remain separately unresolved.

## Validation and delivery

Six synthetic source contrasts cover tentative actor/outcome claims, attributed confident statements, recollections, unresolved identity and local qualifier scope. Verify the rendered recap/preview contracts receive the clarification once, source/evidence/schema fields remain unchanged, and Worldbuilding does not inherit it. Preserve historical prompt hash fixtures by test-only restoration of the exact predecessor sentence. These tests prove assembly and scope, not model compliance.

Inspect cumulative diff, independent subagent review, commit/push/open one PR. Qualify a frozen reviewed runtime through the standardized evaluator; actual fresh output and unchanged source Gold must establish any quality improvement. Preserve all older captures. No database writes, publication or model calls in this implementation slice.
