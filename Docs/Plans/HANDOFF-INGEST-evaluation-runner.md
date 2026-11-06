# INGEST: standardize isolated ingestion evaluation

Status: ACTIVE. Root adopts the user's explicit tooling-standardization request.

## Lane and topology

Branch `codex/ingest-evaluation-runner`, stacked on PR #2128 head `df104a41eea68d34fada0da3b4633072dfa99f92`; merge/rebase #2128 first. Main/open PRs checked. Connected-page lanes #2125/#2127 do not overlap. No merge or primary runtime authority.

## Outcome

Replace copied cohort operators, monitors and terminal assessors with one reusable manifest-driven CLI. Commands qualify, capture, observe, audit and report share source/runtime pins, database identities and durable execution state. Keep capture, literal evidence, independent semantic Gold assessment and publication acceptance separate. This is evaluation machinery, not a new ingestion producer or a redesign of product ingestion.

## Expected exclusive writes

- `scripts/evaluate_ingestion.py`
- `src/ingestion_evaluation/` (new package)
- `tests/test_ingestion_evaluation_runner.py`
- `Docs/Guides/ingestion-evaluation.md`
- This handoff.

## Invariants and failure cases

No corpus-specific names, session counts, database addresses, filesystem roots, private credentials or accepted answers in implementation. A pinned manifest supplies runtime/source/request/dependency/database identities and output directory. Credentials come from explicitly named environment variables and are never retained. Use the ordinary product ingestion route and existing model accounting/quote validators at their owners; do not duplicate semantic rules. Primary state is never connected. Native connections are read-only; permitted APP changes are explicitly bounded and prior rows preserved.

Retain raw requests/responses and actual attempts, including failure and unknown outcomes. Never redispatch an item with a dispatch marker because observation expired or a process stopped. Pause stops later dispatch; interrupted items remain unproven and require read-only inspection. A run completing or literal quotes passing does not establish Gold or publication acceptance. Reports identify the first broken/unproven boundary and retain explicit missing accounting, never zero-fill it.

Preserve existing evidence as immutable predecessors. Support read-only audit/import of historical cohorts without making old copied scripts execution authorities. No model dispatch until this CLI is tested, independently reviewed, pinned into an isolated runtime and freshly qualified. No database migration, primary mutation or graph publication in this slice.

## Verification and delivery

Synthetic tests for manifest pin drift, append-only conservation, native identity mismatch, duplicate dispatch, interrupted execution, pause between items, missing receipts, failed attempts and deterministic reporting. Exercise the ordinary route adapter with fake provider/disposable state, and compare retained cohort evidence/accounting against the existing audited result. Keep Gold judgments source-grounded and independent. Inspect cumulative diff, use independent subagent review, commit/push/open one stacked PR; then resume the broad ingestion/publication goal through the standardized runner.

## Discovery checkpoints

Independent inventory `80eecc5fbb218289a36521355e2cedec463f4e79c6f77d0bee8fbdf582bd9ba5` identified pause/unknown-outcome and ownership requirements. Preliminary review `97937015cd381646f4e15346c480c89f8a30fa9bc14b66b1d71b48d5b3684b64` required transport, startup isolation, audit-chain and adapter coverage corrections. Retained comparison `52c794166e4a8907f3465eaf83231fd82b98540f8c37f9a3597e4f6434cc849a` matched all four actual run/component/private-event/usage records and identified independent receipt, corrected revision and audit-interval checks to preserve. These remain within this evaluation capability. `audit-retained` is read-only and cannot dispatch; it links historical capture proofs rather than claiming a new qualification proves historical conservation.

Formal review of initial head identified a cross-directory replay gap: local dispatch markers alone cannot exclude a source already prepared/unknown elsewhere. Extend the same lifecycle implementation with a database-scoped transient advisory lease, active-transaction checks and explicit unresolved same-source preflight. Add synthetic and disposable PostgreSQL regression coverage; no schema, reconciliation, retry or new producer.
