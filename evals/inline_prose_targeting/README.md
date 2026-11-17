# No-selection inline prose targeting

Synthetic baseline pinned by the handoff. `cases.dev.json` is development;
`cases.holdout.json` is reserved for subsequent routing evaluation, not tuned here.
All cases start with no selection and the caret at the unrelated document top.

`baseline.test.ts` invokes real mounted editor/Build bridge/Plan catalog APIs.
It characterizes available host authority, not ordinary agent behavior. A supported
Plan boundary is not evidence the model selected it; an unsupported offer is a
capability miss, not an observed unsafe ordinary edit. No provider is invoked.

Run with Vitest/jsdom and the UI test setup, under the repository global frontend
verification lock, with external Projects node_modules/cache and result paths.

Report routing separately: exact/acceptable target, valid miss, unnecessary
clarification, correct clarification/discussion, unsafe wrong target. Report
transaction, unrelated-content/citation preservation, Undo, explicit Save and
cold-reopen as separate stages. Never score unrun model cases as passing. Duplicate
passages require contextual disambiguation or a question, not first-match binding.

## Isolated native replacement proof

The optional bridge and mounted review use an explicit default-off in-process
`allowProseTargets` option. Normal services/routes do not enable it. Only
`replace_paragraph` is implemented; ordinary model routing and contextual insertion
remain unproved. Native records/reviews use v2/v4 only inside the disposable proof.
The fixture extends two cloned-database format CHECKs with explicit authorization;
no product migration or production compatibility is claimed.

`native_frontend.test.ts` proves the actual composer transaction, full unrelated
JSON preservation, one Undo/Redo, stale/readonly/foreign and multi-paragraph refusal.
Missing block IDs that would normalize unrelated nodes are explicitly refused.
`native_roundtrip.test.tsx` uses the real mounted BuildPageProposal, actual review
API codec and native PostgreSQL proposal/review/page owners through the isolated
adapter. It tests a scripted alias with duplicate text, unrelated caret, native
Undo before Save, durable review binding, explicit Save, fresh editor hydration
including an unrelated row/link/IDs, and idempotent confirm. It is not browser or
ordinary model evidence. The deterministic tests do not score semantic routing.

Reproduction requires Node22.23.0/npm10.9.8, existing locked UI dependencies and the
owning Python environment. Run only in an isolated checkout. Expose UI dependencies
at that checkout's root `node_modules` (a temporary symlink is sufficient; remove
only a link this run created), then use `vitest run --config
evals/inline_prose_targeting/vitest.config.mts` under the per-user global frontend
verification lock. Retain JSON output externally on Projects. Select individual
non-network test files to run just the host controls.

For the roundtrip, first run `python -m evals.inline_prose_targeting.native_server
--root <owned-external-evidence-directory>` with `PYTHONPATH=src:.` and
`DMB_APPLICATION_STATE_TEST_DATABASE_URL` pointing to the uniquely owned disposable
PostgreSQL on127.0.0.1:55467. The adapter owns only127.0.0.1:15567, refuses a different
server, creates a unique template/clone, records its test-only schema difference,
and serves only one synthetic World/page. Start a fresh adapter for each roundtrip
run. `native_contract_test.py` runs the actual backend-owner cases with the same
disposable test fixture. Never substitute a live database or enable this owner in
production. A stopped/older reader is not made compatible by this proof.
