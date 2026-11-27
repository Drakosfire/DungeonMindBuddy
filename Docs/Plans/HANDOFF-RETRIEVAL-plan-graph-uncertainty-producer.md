# RETRIEVAL: Plan Graph-need uncertainty continuation

Status: ACTIVE under the user's over-retrieval goal and authorization to prepare
releases in parallel. Existing draft [#4987](https://github.com/Drakosfire/DungeonMindBuddy/pull/4987)
is the sole producer PR. Branch `codex/retrieval-plan-pending-graph-producer`,
checkout `negative-current-main-eval`, based on merged reader `458dfbeb97a089a60803890b99f0757152cfedd0`.
The reader is not live: producer merge, activation and acceptance remain held
until its compatible reader deployment and all applicable checks and reviews.

Ordinary Plan question: when the controller cannot decide whether World Graph
context is needed, retain the actual decision and complete the same turn with
one fixed scope question. Do not start Graph acquisition, a writer, or an action;
do not manufacture a provider result. Reopen the exact question and permit the
user's next turn through the ordinary conversation flow. A definite no-Graph
or required-Graph choice continues through its existing path.

Write scope: the existing producer PR's Graph-need dispatch, native producer,
Plan harness and APP service; focused tests, the action/benchmark catalog, and
this handoff. Runtime tests use the existing owned App clone serially; Core stays
read-only, with no provider calls for focused local tests. Validate actual
claim and storage atomicity, stale/expired claim and wrong-decision rejection,
no acquisition or writer on uncertainty, replay, and existing Graph/no-Graph
controls. Do not claim hosted acceptance from a unit test. Independent exact-head
review and the reader-first deployment gate are separate.
