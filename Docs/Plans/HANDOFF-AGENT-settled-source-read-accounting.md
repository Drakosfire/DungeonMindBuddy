# AGENT: settle source-read reservations with durable receipts

Status: ACTIVE. PRIME implements solo under the Mirathorn lifecycle goal; ARCHITECTURE independently reviews. Topology: serial successor to merged Buddy #1258; base 61991c78ab01ed8e4f694ec4b36c2863ff5fb198. Branch codex/settled-source-read-accounting, isolated non-serving checkout /tmp/prime-recap-mention-boundaries. No runtime, retained DB, corpus or provider mutation in this slice.

## Outcome and contract

A completed short passage charges its actual returned characters, releasing unused reservation only after a validated durable receipt. Unknown or unresolved source calls retain the full reservation. Enforce capacity at every authorization prefix, so later settlement cannot excuse earlier overbooking. Repeated reads charge their own returned characters. Keep aggregate 96000 and per-anchor12000 body/transport/provider/storage protections; call-count authorization remains uncapped where already authorized.

Use an explicit opt-in typed V3 policy subtype carrying required source_read_accounting=settled_receipts_v1. Existing serialized policy bytes/digests and frozen reservation semantics remain unchanged; no default injected into historical records. Existing JSONB shape permits the additional policy field; prove real PostgreSQL append/reconstruction without a migration. Parent broker and durable APP validator share one pure accounting function. Existing source pins, exact scope, sequencing, full receipt cardinality, duplicate rejection, body proofs, provider inclusion and citation validation remain authoritative.

Observed predecessor: ordinary Council turn7ab8f2d0-6227-4ae1-a2af-81d0295cc33b returned116.73s/20modelcalls;8opened passages totaled969characters but reserved96000, then seven source_read_over_budget failures. Preserve original evidence/answer. No claim this alone fixes model wandering or semantic roster scope.

## Exclusive write set

- This handoff.
- src/application_state/agent_conversation/types.py
- apps/live_control_server/services/agent_turn_service.py
- apps/live_control_server/services/plan_action_consultation.py
- tests/test_settled_source_read_accounting.py
- tests/test_agent_turn_service.py
- tests/application_state/test_agent_conversation_postgres.py

Open ownership inspected: DOGFOOD #1259 Ingest evidence UI, #1235 publication UI, #1244 package evidence aliases; other open legacy work does not lease these paths. Runtime stable5876/8002 and DOGFOOD5202/8000 untouched. No unmerged dependency. A schema or additional durable contract beyond the explicit subtype is a stop/amend signal.

## Required evidence and review

Prove full8anchor12kreservation settles to actualbody usage and permits later admission; unresolvedbatch blocks; partial/duplicate/changed/future receipt cannot refund; unavailable0/truncated/mixedreceipts charge exactcounts; concurrent overbooking rejected at authorization prefix even with later settlement; oldpolicy remains reservation accounting with unchanged bytes/hash; exactpolicy hashed and reopened through APP PostgreSQL; broker and APP agree; provider/citation checks unchanged. Test corrected path alongside source/provider regressions, inspect cumulative base→head diff, commit/push/open PR for independent review. No merge before review; runtime adoption and a fresh ordinary Agent benchmark follow separately.

## Author evidence

- 29 accounting/dynamic-source/uncapped-policy unit tests passed; 26 selected parent/shared-consumer tests passed (overlap includes new accounting cases).
- Four mounted authenticated route/Core-source/provider-inclusion/citation/history cases and one nine-read PostgreSQL settlement/reopen case passed. Evidence: local build-scratch/settled-source-read-36971ac134/result.json. Actual source receipt persistence needs no schema migration.
- Initial repeated identical-read provider fixture hit existing presentation ambiguity (identical public bytes bound to multiple read events). Preserved failed logs; no presentation/admission gate changed. The final proof separates real route/citation cases from nine durable APP appends. This slice does not claim to fix repeated-identical-result presentation.
- A standalone broker test collection initially imported an old installed Core; rerun explicitly used accepted Core source path. Ruff and cumulative diff checks pass. No provider calls, retained database changes or serving changes.
