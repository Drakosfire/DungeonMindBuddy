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
`allowProseTargets` option. Normal services/routes do not enable it. This original replacement proof implements `replace_paragraph`; the separately
opted-in boundary proof below adds scripted insertion. Ordinary model routing
remains unproved. Native records/reviews use v2/v4 only inside the disposable proof.
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

## Isolated boundary insertion proof and coverage limit

`allowProseBoundaries` is a separate default-off flag. Replacement-only readers
reject boundary proposal v3/review v5 and `dmb_build_prose_boundary_target_v1`.
The existing immutable catalog issues before/after aliases. The host validates the
exact zero-width root boundary, anchor paragraph digest and editor snapshot;
original author caret/selection and Move provenance are unchanged. New paragraph
IDs are deterministic, collision-checked and within the existing 80-character
presentation limit. One Undo restores the whole original editor document.

`native_boundary_frontend.test.ts` covers before/after placement, stale/readonly/
foreign state, multi-paragraph/forged targets, missing or invalid-ID normalization,
and plain-page refusal. `native_boundary_roundtrip.test.tsx` witnesses scripted
insertion after Preparation, duplicate text elsewhere, actual native review and
explicit Save/cold reopen, full retained row/link/IDs and idempotent receipt. It
uses a **pre-existing synthetic row**, not a row added to make an edit pass.
`native_boundary_contract_test.py` exercises the versioned owner boundaries.
Use a fresh owned adapter/clone for each network roundtrip, as above.

**Real coverage gap:** this isolated boundary path refuses pages without existing
Page presentation. `tiptap/pageComposer/presentation.ts::projectPresentation`
currently returns null for a plain page without a row/image-text wrapper, so
native Save cannot certify retaining its block identities on cold reopen. The
proof checks the actual project/hydrate owner roundtrip before any draft mutation
and refuses normalization. It never inserts a dummy row or changes unrelated
content. Broad plain-page support needs the existing Page presentation/Save
contract to define and retain identities without visual wrappers. That owner is
outside this slice; no product acceptance or ordinary contextual routing claim
is made. Production migration/rollback qualification remains absent.

### Build semantic placement coverage correction

The routing export now uses `routing_build.dev.json` and independently authored
`routing_build.holdout.json`, not the shared historical scouts page. The original
cases files remain historical baseline inputs; Plan controls keep that fixture.
Build development covers a river crossing, while held-out Build covers telescope
safety with no reused passage/context. Each includes an unrelated opening,
duplicate passage in a different section, contextual rewrite, ambiguity,
contextual insertion between two adjacent paragraphs and discussion-only request.
The actual Build catalog supplies every before/after choice; private answer sets
accept both aliases resolving to the same physical boundary. Export tests invoke
the real replay scorer with each equivalent alias and reject top/opening/wrong-
section nominations. These are scorer controls, not held-out model evaluations.
No producer has run or received evaluator answers. Set `PROSE_PYTHON` to the
existing Python environment if `python3` cannot import the scorer dependencies.

## Plan mounted contextual-boundary witness

`plan_mounted_witness.py` derives a named test from the existing PlanSurfacePage
fixture, preserving its real mounted surface, proposal review and frontend Save
owner. Guarded single-occurrence anchors fail if that owner fixture changes.
It does not edit the owning file. Generated code and a source/derived SHA256
receipt are retained externally for inspection. The adapter changes the synthetic
page, request, offered section boundary and assertions: unrelated top caret,
duplicate passage in Rumours, insertion after Preparation objective/before Opening
Beat, unchanged neighbor JSON and playable marker, native Undo/Redo, explicit Save
and a fresh mount. An altered boundary is rejected without mutation or Save; an intervening human edit invalidates the pending suggestion without retargeting or Save.

Reproduction (existing dependency symlink and global lock as above):

```sh
python -m evals.inline_prose_targeting.plan_mounted_witness --evidence "$TASK/plan-witness"
flock /tmp/dungeonmind-frontend-verification-$(id -u).lock \
  node node_modules/vitest/vitest.mjs run \
  --config evals/inline_prose_targeting/vitest.config.mts \
  evals/inline_prose_targeting/plan_mounted.generated.test.tsx \
  -t 'contextual Plan boundary benchmark' --reporter=json \
  --outputFile="$TASK/plan-witness/results.json"
rm evals/inline_prose_targeting/plan_mounted.generated.test.tsx
python -m pytest evals/inline_prose_targeting/test_plan_mounted_witness.py -q
```

Do not commit the generated owner fixture. The ordinary model turn and review/
persistence transports remain the owner's scripted mocks. This is frontend
contextual-placement/Save/remount proof, not model accuracy or PostgreSQL proof.
Other owner tests are discovered but filtered; their skipped status is not a pass.
Production routing/authoring remains unchanged. PlanSurfacePage is still leased
by #3824, its owner fixture by #1188/#1014, Plan bridge by #1014 and saved review
backend by #3919/#3824; no ownership release is inferred from nonconflicting hunks.

### Typed-reference identity variant

Use `--typed-references` and test filter `typed-reference Plan contextual persistence`
to preserve two pre-existing graphNodeReference atoms named Warden with distinct
`warden:river` and `warden:ridge` identities through a plain-prose insertion. Assertions inspect actual editor node types/IDs,
sealed application Markdown and cold-remounted JSON, while retaining the unrelated
caret, contextual section placement, untouched neighbors and Undo/Redo checks.
A same-label/wrong-but-valid-ID contrast tests the assertion oracle, not runtime
rejection. This is not an ordinary URL or evidence-citation substitute. No Graph
object lookup, native chip opening, reference availability or model choice is proved.

`--owner-root <isolated-pinned-checkout>` reads the owner fixture/runtime from a
separate checkout without editing it. Its installed UI dependencies must be
available there. The receipt records both harness SHA and owner-source SHA plus
the exact fixture/derived digests; never relabel this as a merged branch or use an
unrecorded moving checkout. As before, the original fixture's server transports
are scripted. Frontend Save/cold remount is not native server persistence.

The typed-reference variant also proves current refusal of a newly proposed graph
identity before action preparation/Save. The initial positive attempt to insert
new typed references failed and is retained separately, not relabeled successful.
Bare labels can remain ordinary prose; they do not satisfy a typed-reference task.
Future reference creation requires host-bound existing-identity admission, not a
looser Markdown validator. Receipts record the generator digest and tracked-dirty
status so working-tree runs cannot masquerade as exact clean harness evidence.
