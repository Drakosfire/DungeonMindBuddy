# RETRIEVAL: Plan Graph-need uncertainty continuation

Status: ACTIVE under the user's over-retrieval goal and authorization to prepare
releases in parallel. Existing draft [#4987](https://github.com/Drakosfire/DungeonMindBuddy/pull/4987)
is the sole producer PR. Branch `codex/retrieval-plan-pending-graph-producer`,
checkout `negative-current-main-eval`, based on merged reader `0a367b42dbd75d3e250f9f02db68ee7fff0f5bf3` (#5004).
The reader is not live: producer merge, activation and acceptance remain held
until its compatible reader deployment and all applicable checks and reviews.

Ordinary Plan question: when the controller cannot decide whether World Graph
context is needed, retain the actual decision and complete the same turn with
one fixed scope question. Do not start Graph acquisition, a writer, or an action;
do not manufacture a provider result. Reopen the exact question and permit the
user's next turn through the ordinary conversation flow. A definite no-Graph
or required-Graph choice continues through its existing path.

The real-model creative control also exposed a work-choice failure in this same
turn. For fresh V1 openings only, the harness emits the versioned guidance that
#5003 can read; retained SDK openings and other versions keep their prior wire.
The reader must be live before emission. This addition is part of making the
producer turn usable, and needs creative, source-required, edit/follow-up and
replay controls rather than treating a successful no-Graph choice as completion.

The no-search edit control also revealed a `require_graph` decision before the
opening. Fresh Graph-need dispatches emit the reader-compatible exclusion
guidance from #5004. Retained decisions keep their original version and wire.
The reader must be live first; the actual edit, source-required and held-out
controls must establish behavior without treating a model vote as proof.

Write scope: the existing producer PR's Graph-need dispatch, native producer,
Plan harness and APP service; focused tests, the action/benchmark catalog, and
this handoff. Runtime tests use the existing owned App clone serially; Core stays
read-only, with no provider calls for focused local tests. Validate actual
claim and storage atomicity, stale/expired claim and wrong-decision rejection,
no acquisition or writer on uncertainty, replay, and existing Graph/no-Graph
controls. Do not claim hosted acceptance from a unit test. Independent exact-head
review and the reader-first deployment gate are separate.

## Intent-first producer and ordinary comparison

The user assigned this implementation to #4987. Compare against main
`63404f5cf39d847a831241908aa055fc6f881a59`. Keep the serving-dependent producer
history available while porting only the Plan ownership changes. A direct
merge of the serving branch and main conflicts across unrelated product
surfaces.

The first admitted Jev request uses the shared Plan intent catalog with the
current Plan title, visible selection, and relevant dialogue. Seal the request,
claim, and editor basis before dispatch. Move source authority, query and
saved-page discovery out of that admission. After the acknowledged intent,
use the existing Graph-need decision where applicable. Bind later acquired
authority and exact catalog entries durably before use. Reopen and validate
retained receipts through their original wire and source owners.

Ordinary controls on the pinned main runtime passed with simulated providers
on a disposable evaluator:

- Discussion versus Plan write authority
  (`test_plain_plan_cannot_write_after_discussion_intent`).
- Current Plan caret edit and exact saved proposal replay
  (`test_ordinary_plan_caret_reopens_its_exact_captured_proposal`).
- Selected saved Worldbuilding page and exact citation reopening
  (`test_ordinary_plan_reads_saved_worldbuilding_and_reopens_exact_capture`).

Reuse those controls on the candidate. Compare actual first request, source
preparation order, chosen action, exact proposal/citation and replay behavior.
Include a no-source discussion control that fails if any opening source
preparation occurs and a source-required control that verifies preparation
starts only after intent. Record latency at the same boundaries on both heads.
The isolated main run used simulated providers and establishes routing
controls, with no live-model quality or latency claim.

The first main-port trial used `aa31508aa99fe683f5488a10799d60c1b1fb2821`
and the producer-only diff from serving parent `0a367b42dbd7`. Main is missing
the pending Plan reader and its test module. With that test excluded from the
trial, conflicts were confined to `agent_turn_service.py`,
`context_trace_store.py`, and `test_agent_native_corpus_sources.py`. The trial
left both branches unchanged. Resolve against main's shared intent-only Plan
ballot and current trace storage. Integrate the required reader contracts
without importing the unrelated serving overlay. Preserve #5008's separate
serving qualification and its migration hold.

### Required admission split on main

The port at `df13f41bf8fa` retains the earlier dispatch order. The service
prepares source authority before entering the harness. The harness claims a
source-bound native receipt and runs Graph need before its intent ballot.
Moving the two harness calls alone would still perform source preparation
before dispatch.

The first intent attempt needs durable admission based on the submitted
request, editor basis and dialogue, before source authority exists. Bind
its acknowledged choice to the subsequent native claim. Keep source
preparation behind that choice and require an exact authorization before
using any acquired entries. Retained source-bound turns continue through
their original receipt and wire validators. An interrupted intent attempt
must reconcile its durable outcome before retry or any source preparation.

The ordinary HTTP controls must observe both Jev transport entry and the
source owner. Require intent entry first, require no source preparation for
a conversation-only answer, and require source preparation after intent for
a citation request. Keep the captured placement and replay controls in the
same qualification. Benchmark reruns remain gated on these checks.
