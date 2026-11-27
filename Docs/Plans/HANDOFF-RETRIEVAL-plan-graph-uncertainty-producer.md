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
