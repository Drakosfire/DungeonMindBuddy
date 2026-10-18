# INGEST: persist honest failed extraction steps

Status: ACTIVE — PRIME stewardship under the Ingestion dogfood goal; ARCHITECTURE critiqued the invariant and failure cases on 2026-10-17.

Base: fetched `origin/main@184e1379ce5b659918fbe514771f9cd20a90e4e1`.
Branch: `codex/ingest-failed-step-projection`.
Checkout: existing `/home/drakosfire/.codex/worktrees/buddy-context-loop/DungeonMindBuddy`.
Topology: serial, one reporting implementation PR. PRIME owns implementation, merge/delivery after independent ARCHITECTURE review. DOGFOOD owns the concurrently running Session 29 verification; no runtime restart until its request completes. Open relevant PRs and leases were checked; DOGFOOD's merged schema slice does not reserve these source paths.

## Invariant

The legacy package step reflects the authoritative requested production outcome, rather than the packaging helper's deliberate `allow_llm=False`. A requested production extraction that fails or produces a non-reviewable diagnostic candidate must persist `extract_candidate_graph=failed`, a bounded safe explanation, and existing failure/run lineage. Derive immediate response and later inspection from that same saved manifest. Source-only extraction without a model request remains skipped; a packageable candidate remains complete.

A failed workflow does not prove a provider call occurred. Do not infer attempted calls from allow_llm or candidate-file existence. Keep provider accounting/model unknown unless already authoritative. Preserve the no-second-model packaging rule. Failed production must not become reviewable through a caller's manual-candidate fallback. API already rejects candidate path plus requested extraction; the service should preserve that boundary rather than package a failed candidate.

Do not expose raw model output, prompts, credentials, tracebacks or private diagnostic paths in the new public failure explanation. Use fixed host text and allowlisted failure classification; retain detailed execution evidence in its existing private authority. Do not rewrite historical run artifacts. No status/schema migration, new execution flags, provider retry, source mutation or publication.

## Exclusive write lease

- `Docs/Plans/HANDOFF-INGEST-failed-step-projection.md`: authority, verification and settlement.
- `Docs/Plans/HANDOFF-INGEST-disposition-node-type-tolerance.md`: truthful settlement of merged #1393 only.
- `apps/live_control_server/services/recap_graph_preview_ingest.py`: coherent persisted failed-step projection and response derivation; no second extraction or failed-candidate fallback.
- `tests/test_live_recap_ingest_graph_preview_api.py`: owning response/manifest/reinspection regressions, source-only/success controls, sanitized failure, exactly one extraction invocation.

Any required additional path returns to PRIME before editing. First commit contains handoff and predecessor settlement only. Use existing Python/dependencies and standard disposable PostgreSQL fixture on54329, owned/removed by PRIME; never retained54331/54330. No new checkout, source copy, environment, or task directory under /tmp.

## Verification and delivery

Cover structured-output failure after fake extraction invocation, pre-provider refusal without invented execution, typed-validation failure with diagnostic candidate, source-only skipped, successful candidate complete, and immediate response→saved manifest→ordinary inspect_status agreement. Ensure failed step stays visible as current step, Graph Review remains unavailable, model unknown remains unknown, arbitrary diagnostic sentinels do not leak, and no second model invocation occurs. A new failure must not rewrite the preceding retained manifest. Existing old manifests remain readable unchanged.

Inspect exact cumulative diff, run focused owning tests and Ruff, commit/push/open one PR, obtain independent exact-head review. Runtime delivery waits for DOGFOOD's live request to finish, then uses owned ports with active-work and retained-state checks. Test/read historical failure artifacts without rewriting them. Full Session29 semantic readiness is separate and remains open.
