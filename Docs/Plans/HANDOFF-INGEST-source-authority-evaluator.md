# INGEST: shared source-authority evaluation lifecycle

Status: ACTIVE. Root adopts this bounded tooling slice under the user's explicit instruction to standardize the evaluation machinery now and continue isolated ingestion through publication.

## Lane and topology

Branch `codex/ingest-source-authority-evaluator`, stacked on PR #2133 at `1b405f21b17d26112e435931d49fa2a19a1d75e6`. Merge/rebase #2130, then #2133, then this slice. Sibling #2131 owns only recap wording and is behaviorally independent. Conversation-loading #2132 is independent. Remote main and exact parent rechecked before activation. No merge/deployment authority.

Root transfers the expected write lease for the evaluation CLI, runner and guide from completed implementation lane #2130 to this successor. Parent #2133's evidence checker remains read-only. No concurrent writer owns the paths below.

## Confirmed problem and invariant

Capture/evidence/accounting use one shared runner, but repeated source-only operator commands still reconstruct dispatch, receipt and conservation plumbing. Session 9 admission committed correctly; a manual post-commit assertion used the wrong name for the expected mutable source-authority table. Independent fresh proof `0d936a4dad84f926035b95d5475ae476c264ad2a793dd62cc83506a9a894c8a3` establishes the real outcome. Design critique `eb45617c8323792d5fc6d6e8bfc2b642612bed520be5349e396afca1e242cc20` supports one shared bounded successor rather than another recap harness.

Add a source-authority mode to the existing parameterized evaluation CLI for exactly two existing authenticated product operations: recap source-only admission and SUPPORT-passage extension. Reuse runtime/DB identities, immutable seals, lifecycle locks and the global evaluator lease. APP remains the source-byte authority; Core owns source admission, intervals, receipts, epoch and raw openings. No model output or source bytes are rewritten.

Qualify exact reviewed requests and an existing reviewable ingestion run/source binding before dispatch. Source-mode manifests must not dispatch ordinary capture commands. Preserve ordinary `Buddy`'s native-write prohibition; a separate route-allowlisted window permits only the selected source operation. No arbitrary route or table-write switch. Validate actual mutable-table names and row identities before effects. Preserve all prior APP/native rows except the exact selected World head and the singleton global source-authority epoch row; verify unchanged semantic entities/assertions and prior evidence through Core. Actual pinned Core schema has `knowledge_heads.space_id` and `knowledge_native_source_authority.singleton_id`, not two per-World head tables.

One execution marker permits one request. Distinguish known committed but verification-failed, unknown outcome, and no dispatch. Read-only inspection may resolve receipts/openings; it never retries, resumes source intents, reconciles providers or mutates state. Source admission's existing wire protocol does not accept an external parent pin: record the immediate preflight context and verify the actual receipt's parent afterward under the exclusive evaluator lease, without claiming stronger atomic protection from unrelated writers. Extension uses its existing explicit parent/epoch fields.

## Exclusive expected writes

- `scripts/evaluate_ingestion.py`
- `src/ingestion_evaluation/runner.py`
- `src/ingestion_evaluation/source_authority.py`
- `tests/test_ingestion_evaluation_source_authority.py`
- `Docs/Guides/ingestion-evaluation.md`
- This handoff.

No product routes/models, prompts/passes, schemas, Gold, capture semantics, claim preparation/confirmation, provider calls, migrations, Worldbuilding protocols or terminal-run adjudication changes. Existing established native Worlds only; no World genesis or authority provisioning. No new source representation or alternate producer.

## Validation and completion

Review map: `source_authority.py` separates exact-row conservation, the once/unknown lifecycle, read-only APP/Core preflight, the two fixed route adapters, and receipt/opening verification. The CLI selects this explicit mode; the ordinary capture runner rejects it. The shared lifecycle and both source-operation variants form one independently useful evaluation capability; separating transport from its once/verification contract would leave an unsafe partial tool or duplicate the plumbing again. Tests focus on boundary failures rather than treating mocks as Core publication proof.

Test request/route/source/DB/context pin failures before dispatch, exact mutable-row conservation, once/unknown handling, committed-but-unverified read-only recovery, no-replay after process interruption, external-HTTP prohibition, and unchanged ordinary capture's native-write ban. Retain all existing runner/evidence tests.

Inspect the cumulative diff, obtain exact-head independent subagent review, commit/push/open one focused PR. Then qualify and execute the already reviewed Session 9 eleven-passage SUPPORT extension through the shared CLI, once, with providers absent and primary unchanged. Pin request `8f046bc08b094257898d361fe4a5a9e811a5c07977967d684b998cee19efb1ff` and independent review `b8ad07fa0dc3b7112199ce171492850ca881ac7c35576c7f6e3f43b476f098fe`; recheck actual parent/epoch first. Independently reopen the exact source intervals and verify conservation. This proves source authority only; semantic publication and whole-cohort acceptance remain separate.
