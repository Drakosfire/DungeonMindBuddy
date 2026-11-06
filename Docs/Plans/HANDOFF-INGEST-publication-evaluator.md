# INGEST: shared reviewed-publication evaluator

Status: ACTIVE. Root adopts this bounded successor under the user's instruction to consolidate evaluation machinery and continue isolated ingestion through publication. Independent design critique `eb5a97331d7dc147209fd18cbba174458a323f0ab37f13b7b50bd0ba2a91ef97` inspected the existing owners and failure cases. S10 publication and independent readback completed; its observation windows are closed.

## Lane and topology

Branch `codex/ingest-publication-evaluator`, stacked on PR #2134 at `5946770f4f0f3d32c6fd97dc904ff72e443f1ccc`. Merge/rebase #2130 → #2133 → #2134 → this slice. No merge or deployment authority. Remote main and open PRs rechecked before activation; conversation activity #2135 and prompt #2131 are independent and untouched.

Root transfers the CLI, manifest runner, source helper and guide write lease from completed #2134 to this successor. No other active writer owns these paths. Evaluator55447 only; existing isolated APP/native identities and frozen product runtime remain pinned. Primary is read-only. No provider calls, terminal-run retirement, migrations or source admission/extension effects in this slice.

## Outcome and invariants

Add one publication mode to the existing parameterized evaluator: read-only preparation, qualification of the exact private signed packet, one confirmation, then read-only inspection/reporting. Repeated inline route/signing/once/conservation setup caused a real missing-signing-configuration refusal and stale per-session report prose. Product owners still sign, compile and publish; the evaluator neither constructs claims nor changes their representation.

Fail before preparation if the existing signing configuration is missing; never generate a key or fallback. Pin runtime, source/run/candidate, exact reviewed request, private packet and independent reviews. Qualify the owning signature/codec/compiler, parent/epoch, source openings, receipt absence and expiry under the shared database lease. Seal the once marker before any native write. APP stays read-only throughout; native writes exist only around the exact authenticated confirmation route. External provider HTTP is forbidden. Restore read-only bindings on every exit.

Preserve raw responses and before/after observations even when verification fails. Distinguish verified, committed but unverified, and unknown; never redispatch because a reply or proof is missing. Inspection queries Core receipts/results/exact child, not product confirmation recovery. Later head advancement must not invalidate an otherwise verifiable receipted child or attribute unrelated later writes to this operation. Preserve execution-window conservation separately.

Verify exact selected object/assertion values, metadata, endpoints and SUPPORT openings through existing Core/WK contracts. All prior entities/assertions/evidence and APP rows remain intact. Publication changes only the five existing owned Core tables, append-only except the exact World head row; source epoch is unchanged. Technical proof never awards Gold, retrieval or whole-goal acceptance. Report structured run IDs and counts instead of copied session prose.

## Exclusive expected writes

- `scripts/evaluate_ingestion.py`
- `src/ingestion_evaluation/runner.py`
- `src/ingestion_evaluation/publication.py`
- `src/ingestion_evaluation/authority.py` (small shared observation/transport helpers only)
- `src/ingestion_evaluation/source_authority.py` (reuse those helpers; preserve source mode behavior)
- `tests/test_ingestion_evaluation_publication.py`
- `tests/test_ingestion_evaluation_source_authority.py` (affected helper regression only)
- `Docs/Guides/ingestion-evaluation.md`
- This handoff.

No product routes, signing policies, schemas, prompts, Gold or capture semantics. No generic plugin framework, alternative producer or second per-recap harness. Checkpoint if the owning invariant requires paths or capabilities beyond this lease.

## Validation and delivery

Cover missing signing config, packet/signature/pin drift, expiry, parent/epoch/source drift, receipt presence, lease conflict, once/timeout/post-commit verification failure and read-only recovery. Prove APP/unowned table/prior payload/source epoch violations are rejected. Keep capture/source tests passing and their native-write restrictions unchanged. Inspect the cumulative diff and obtain exact-head independent subagent review, then commit/push/open the stacked PR.

Use retained S10 packet `19271950f08ae498e256fd0f46e0f144fbc217e51d39f74ec9dc402ce513962e` and actual receipt `recap-review:9e382014-8322-4e22-83eb-5d65c2dce188` for independent read-only real Core proof; never reconfirm it. Next new real execution may use S3 only after its source/identity/request/compiled-packet gates independently pass. Do not force those gates or broaden scope to manufacture an execution test.

Review map: `authority.py` contains only the four fixed local routes, read-only observation and secret redaction; source mode delegates its existing helpers without changing its lifecycle. `publication.py` keeps packet/signing/compiler checks, one-shot lifecycle, execution-window conservation and exact immutable-child verification explicit. The CLI/manifest guard prevents mode crossover. Tests reuse the existing real in-memory Buddy/WK/Core fixture for signed packets, commit, forged result kinds/metadata and later-head inspection, in addition to lifecycle and PostgreSQL regressions. Historical inspection returns `verified_core`, explicitly excluding the original DB window; only execution with a qualified retained window can return `verified`.

Author validation: 101 tests pass across publication/source/evidence/capture runner, including the disposable PostgreSQL fixture. Retained S10 read-only inspection with manifest `d0120a31f5b162c343c9e74b6c062cd515811793edc2cd0ea3b69f1ae3cde8cc` returned `verified_core`; proof `ad8edd96b0eea5c6135f9a440a5bd3023dc89f185ff30791a0779c5856a3c572`, unchanged DB observation `4ddb542a35dfe8e5cc9f5a950e82466c4421ad0e9059d7f63e56c64941ed0f93`. An initial read-only probe incorrectly looked for an APP revision on the graph artifact; the source-owner lookup was corrected and regression-tested, with the failed probe preserved. Independent review found an assertion-to-entity binding gap; exact compiled result-kind agreement and the owning Core prospective resolution now reject it. Final exact-head review remains a delivery gate.
