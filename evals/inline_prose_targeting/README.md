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

## Offline nomination scoring (no model or writes)

`routing_artifacts.test.ts` exports the actual Build paragraph and Plan placement
catalogs for the frozen development and held-out requests. It leaves the collapsed
caret at the unrelated top and never changes the document. Plan's captured-caret
distractor is retained; equivalent section boundaries are both accepted. The
intra-paragraph Plan request is a capability miss, not a missing model prediction.

With the dependency setup above and a **new external directory**, run under the
same global lock:

```sh
PROSE_ROUTING_EXPORT="$TASK/routing-export" node node_modules/vitest/vitest.mjs run \
  --config evals/inline_prose_targeting/vitest.config.mts \
  evals/inline_prose_targeting/routing_artifacts.test.ts
python -m pytest evals/inline_prose_targeting/test_replay_score.py -q
```

The export writes separate `producer/dev.json`, `producer/holdout.json` and
`evaluator-private/{dev,holdout}.json` files. Give a future output producer **only**
the selected producer file, not this checkout, answer files, tests, or evaluator
manifest. Expected answers, original case labels, host selectors/offsets, and
snapshot identities never enter producer inputs. Only requests and opaque
choice aliases with meaningful passage/location labels are exposed. Keep held-out
answers private and do not tune the producer on held-out scores. Files are
write-once; use a new directory for a different snapshot/source.

A supplied replay has the following shape (digest is SHA256 of exact input bytes):

```json
{"schema":"prose_routing_replay_v1","inputs_sha256":"<digest>","provenance":"scripted","decisions":[{"id":"case1","decision":{"clarify":true}}]}
```

Each decision is exactly one of `{"alias":"choice1"}`, `{"clarify":true}` or
`{"discuss":true}`. No offsets or write actions are accepted. Missing cases remain
unscored. Duplicate cases, extra fields, stale input digests and malformed
responses reject the replay; unknown and semantically wrong target aliases are
hard failures. Run the evaluator separately from the output producer:

```sh
python -m evals.inline_prose_targeting.replay_score \
  --inputs "$TASK/routing-export/producer/dev.json" \
  --manifest "$TASK/routing-export/evaluator-private/dev.json" \
  --decisions "$TASK/dev-decisions.json" --output "$TASK/dev-score.json"
```

Exit 2 means a wrong/unknown target nomination, 1 means missing coverage or other
misses, and 0 means supplied decisions match these control cases. None means
ordinary routing is qualified. `scripted` and `external_unverified` provenance
never claim model evidence. Clarification recall and overuse, intentional non-edit,
capability misses, and offered-alias membership are reported separately. This
membership check is **not** live snapshot/read-only admission; the native bridge
negative tests own that. No application, Undo, Save or reopen is performed by the
scorer. A wrong nomination is not reported as an observed wrong-target write.
