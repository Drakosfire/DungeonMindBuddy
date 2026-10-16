# AGENT: actionable evidence-bundle refusals

Status ACTIVE under PRIME Mirathorn goal. Serial successor to accepted #1261, main 0dea746abe32185586f59d78c730caa83ab4be94. PRIME implements solo in /tmp/prime-recap-mention-boundaries, branch codex/evidence-bundle-refusal-reasons. ARCHITECTURE independently reviews before merge.

## Outcome

Known bundle admission failures return stable, actionable reason codes and safe correction guidance through the existing parent denial protocol. Malformed requests, unsupported operations, unavailable turn/policy, changed frozen scope and unresolved previous attempts remain distinct. A model can correct its request without blindly repeating an unavailable operation. Unknown exceptions keep generic feedback; raw validation inputs, exception messages, paths and source data never enter diagnostics.

Evidence: ordinary Council turn 8bac71ea-9c2e-40a8-9983-53514fb820d4 completed46.855s/4calls/32passages on accepted main, tenfacts and source-integrity independently PASS. First request returned generic evidence_bundle_unavailable; exact rejected arguments and root exception were not retained, so cause remains unknown. This slice does not claim to repair an inferred cause or causally explain latency. Strict roster-boundary caveat remains a separate semantic limitation.

## Exact lease

- This handoff.
- apps/live_control_server/services/graph_evidence_bundle.py
- apps/live_control_server/services/agent_turn_service.py
- tests/test_graph_evidence_bundle.py
- tests/test_agent_turn_service.py

No schema, provider, corpus, retained database, source authority or serving-runtime changes. Existing APP failure observation records reason code; denied payload hashing and exact-envelope exclusion remain unchanged. No extra raw request logging or new durable fields. Existing uncertain-attempt marker and successful cache behavior remain intact. One PR, no unmerged dependency. Open PRs inspected: DOGFOOD1259/1235 UI and1244packager are disjoint.

## Verification

Exercise each known refusal before Graph/source IO; malformed IDs/extra fields cannot leak values; wrong scope cannot hit cache; unresolved attempts cannot rerun. Exercise actual parent broker and trace failure capture, exact current-envelope denial recognition, altered denial rejection, generic unknown-exception sanitization and retained413overflow behavior. Existing bundle success/byte/receipt/inclusion tests stay passing. Record beginning/end refs, test evidence and cumulative diff, commit/push/open PR, independent review. Runtime re-adoption and ordinary question remain separate.
