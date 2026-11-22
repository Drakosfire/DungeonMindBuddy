# DOGFOOD: select the bounded AW10 serving candidate

Status ACTIVE for preparation and independent review only. The user assigned
DOGFOOD this lane, authorized all replays/submissions, and authorized reviewed
PR merges when Buddy can create a new page from new context. No PRIME
coordination is required. Production cutover is not authorized by that grant.

## Serial lane and exact sources

Predecessor #4402 is merged at `90b95f43f06f2e92d2fabe67872e9ef446c91f6e`.
This successor is serial, with no unmerged behavioral parent. Documentation
branch `codex/dogfood-aw10-release-selection` starts at that merge in
`/home/drakosfire/Projects/.codex/79e2/DungeonMindBuddy`.
Exclusive writes are this handoff, the predecessor handoff and
`HANDOFF-BUILD-lore-from-conversation.md`, solely truthful predecessor
settlement. Existing release rehearsals #4356 and #4195 keep their own tooling
and cleanup paths; this slice edits neither. No concurrent runtime write lease.

The reviewed release source is the separately pushed branch
`codex/dogfood-aw10-serving-candidate`, exact commit
`2fa3c991094fb417be2519ec9af957971d343a79`, based on the observed serving commit
`03055f248645c3a2bc67d2904825637b23687ada`. It adopts the existing AW10 runtime
delta `0963123139adb8ca4cd039271e0972c06f6c2993` to
`8b3b8eab8f83f648c29d395d9cfe159ca5621a6f`, plus #4402. The one test-fixture
conflict preserves serving authored-source coverage and the prior-citation
condition. Dependency pins, migration files and deployment configuration are
unchanged. This is a release selection, not a request to merge the historical
serving branch into current main or roll back unrelated main changes. Historical
ACTIVE wording inside that immutable source artifact is superseded by this
current bounded assignment; it grants no new implementation or cutover lease.

## Invariants and review map

The ordinary Maelthor request must select conversation reuse, retain its exact
prior citations, perform zero new Graph/corpus/related-page acquisition, expose
review before save, create one page, reopen it and return the same receipt on
repeat. Source access remains freshly authorized during confirmation; immutable
revision reuse must never cache principal permission or source-view authority.
Freshly supplied context must also produce a populated new page through the
normal route, preserving proposed material and open questions.

Review the complete serving-base to candidate diff: opening route and retained
evidence admission; writer projection and prompt boundary; durable completion
and citation reopening; confirmation/save; frontend decoding and controls;
owning tests. No Maelthor-specific production code is admitted.

## Retained verification and limits

Evidence root: `/home/drakosfire/Projects/.codex/buddy-check.q9sCkN` on verified
Projects filesystem UUID `48fa5d10-fe99-4557-9fc9-d8a2a4b41ac8`. Isolated APP
and Core clones belong to each recorded test receipt; source fixtures and live
authorities are not mutated. Provider artifacts remain private outside Git.

- Candidate focused backend: 44 passed. Candidate saved-page-readers: 499
  passed, 19 failed. All 19 failing IDs reproduce on exact serving source with
  identical locked dependencies; four menu-hash errors differ after adding the
  reuse option. Only failing baseline cases were rerun, not its full suite.
- Exact-candidate frontend hosted verifier: 1,412 passed, build passed, cleanup
  complete, evidence validated. Full discovered: 8,103 passed, 115 failed,
  2 pending. Same 115 failed IDs as retained exact-serving baseline, no shared
  status changes or shared-case omissions, one new passing carried-citation case.
  Both candidate and serving baseline report `collection_parity: false`
  (8,218 versus 8,217 inventoried discovered cases); this is an additional red
  diagnostic fact, not a passed collection gate. The discovered diagnostic
  remains red; failed evidence validation is not green.
- Actual candidate Maelthor replay: `live-aw10-35e91c0511`, zero acquisition,
  exact retained digests, one saved/reopened page and idempotent receipt.
  Draft 13.338 seconds; confirmation/reopen 5.790 seconds. This misses the
  10-second draft target and is not hosted qualification.
- Candidate actual-provider fresh-context acceptance: `live-aw10-c04b9c3656`,
  empty new conversation, populated Copperglass Watch page from newly supplied
  proposed lore, all details and open question preserved, one saved/reopened
  page and identical repeated receipt. Draft 9.576 seconds; confirmation/reopen
  66 milliseconds. Ordinary route performs one Graph preparation and one
  related-page acquisition call, with zero source-body reads. This does not
  replace the separate strict zero-acquisition Maelthor proof.
- Independent cumulative source review: PASS at exact
  `2fa3c991094fb417be2519ec9af957971d343a79`, no actionable runtime findings.
  Reviewer independently ran 38 parser tests, inspected nested serialized
  provider inputs for the host prompt boundary, and verified the fresh-context
  page against actual disposable database state. The verdict supports bounded
  selection only, not full release or production qualification.
- Local production image built through the repo-owned preparation script:
  `sha256:177204f57d63111727b75ad47949852ddfc485d06320d455848a2357bdf0588c`,
  revision label exactly `2fa3c991094fb417be2519ec9af957971d343a79`.
  Network-disabled, read-only, non-root container with no host mounts or
  published ports passed liveness, HTML `/` and `/plan`, signed-out session
  refusal and packaged APP schema head `20261119_0169`. Readiness returned the
  expected 503 against synthetic unreachable dependencies. Earlier smoke
  attempts omitted required synthetic config or browser HTML Accept headers;
  all failures remain retained, and the corrected smoke passed. This is image
  packaging evidence, not authenticated hosted or database recovery evidence.
  See `serving-image-{build.log,id.txt,browser-receipt.json}` and
  `serving-image-smoke-browser-accept.log`. No image was published or deployed.

Original requested Maelthor page already exists in Elderwyld as document
`5c96c8cf-3cf2-41ab-9d40-c0c28f7b8061`, manually saved/reloaded from retained
discussion with the two exact original citation targets. Do not create a second
production page as a benchmark. This unblock does not qualify hosted automation.

## Delivery and remaining work

Finish exact-candidate independent review and fresh-context readback, inspect
this documentation diff, commit, push and open the assigned selection PR.
Do not switch production, migrate databases, publish an image or alter shared
deployment configuration in this slice. A cutover request must name the exact
reviewed source/image, current serving witness, recovery evidence and rollback.

Confirmation profiling identifies reusable immutable revision work: baseline
7.599 seconds, existing verified repository 3.106 seconds, plus parsed cache
1.700 seconds. These are single external dependency-injection experiments,
not product implementation or statistically qualified results. Both faster
variants retain two distinct fresh access contexts. A later bounded latency
slice must keep negative authorization/identity/epoch/digest checks and respect
#3307's opener/cache-integration overlap. Writer latency still dominates the
Maelthor draft; faster confirmation alone does not meet its draft target.
