# RETRIEVAL: reuse the prepared native revision during Graph bootstrap

Status: ACTIVE bounded design adopted by Root, the assigned retrieval steward,
under the continuing user authorization to own generic retrieval optimization.
This is the steward checkpoint for one independently useful bootstrap capability.
Pinned base c12bafca6b6949ae3aad5012c716eefbe6b61c81. Implementation complete; local owner validation passed. Exact-head review and PR delivery follow.

Topology: parallel-independent of PR2301 and PR2304. Neither unmerged behavior
is required. The existing PR2304 checkout must remain untouched. Allocate a
separate managed checkout from the pinned remote main; record its returned
path/branch before implementation. Root explicitly designates one separate PR
for this capability; this does not activate normalized storage or another slice.

Expected exclusive writes:
- apps/live_control_server/services/native_graph_reads.py
- tests/test_native_plan_assertions.py
- Docs/Plans/HANDOFF-RETRIEVAL-bootstrap-revision-reuse.md

Checked open2307 Play lease: models/agent_turn, authored_graph_references,
types, migration0144 and Play/frontend tests; no shared write paths here.
2301/2304 admission/session/repository/driver paths are also disjoint. Do not edit
shared CI/config/dependencies, schemas or prompts. Coordinate if overlap emerges.

Outcome: remove two redundant repository.get_revision calls during prepare_query
when an exact Core-prepared source context already owns immutable parsed R.
Reuse the existing Core read-context descriptor resolver result; derive
the Graph authority refs from the same exact parsed revision. No cross-request
cache, new representation, alternate producer or fallback.

Before scoped Core query construction, explicitly join parsed/access World and R
to source authority, including exact domain/profile IDs, revisions and hashes.
Use source_context.repository for this branch. Reject a separately supplied
repository that is not that prepared owner; do not silently cross-attest contexts.
Preserve GM authority, current binding checks at both ends, complete scoped Core
reads, retained source epoch and body-acquisition boundaries. Non-prepared query
composition remains its distinct existing owner. No new body/model exposure.

Evidence: redundant-bootstrap-revision-read-v1.json measures a single immutable
get_revision at176ms median; parsed-descriptor-reuse-design-review-v1.json
independently critiques identity/descriptor/repository failure cases. This is
component evidence, not a seconds-scale or full-cycle claim.

Validation: equivalent real-Core query output with and without prepared context;
no redundant revision reload in prepared path; mismatched World/R/descriptors,
repository injection and binding movement refuse. Run relevant existing local
owner contracts, inspect cumulative diff, independent exact-head review, commit,
push and open one bounded PR. No GitHub CI gate. No paid unchanged baseline.
Only consider changed candidate capture after matched bootstrap timing warrants
it. Primary and original evaluator remain unchanged; test only isolated55447.
Merge remains separate user authority. Six seconds remains unproven.

Managed checkout allocation pending operation f5b8fdcf-66b4-4f8e-8d1e-ecc0397190ca, requested name retrieval-bootstrap-reuse. Do not switch the preserved PR2304 checkout or repeat creation while this operation is live.

User explicitly approved the independent three-file cleanup lane in this chat. Root assigns the clean detached attached historical checkout /home/drakosfire/Projects/.codex/historical-graph-repair/DungeonMindBuddy, with branch codex/retrieval-bootstrap-revision-reuse. Its ec1376d4176140422fa4ab4ab90ce071a7d7a97a is an ancestor of main, no uncommitted/untracked files and no process cwd consumers were found. PR2304 stays at6170495a7 in recorded-names-control. This satisfies the separate-checkout requirement without waiting on the still-pending managed allocation. Do not restart/delete that pending operation.

Runtime uses the existing locked Python environment in recorded-names-control, with PYTHONPATH explicitly selecting this worktree. Test databases are disposable on evaluator55447; no server/port changes or primary writes. Evidence output is retrieval-bootstrap-reuse-v1. No paid capture is active.

Observed verification: all44 native assertion owner tests pass, including real-Core complete-query equality and mismatch/refusal cases. Provider-free old/candidate comparison over the frozen15ordinaryquestions yields15identical complete queries; median query bootstrap645.965→282.769ms,30→0revisionreloads. No end-to-end latency claim. Production Ruff passes;14test-file diagnostics exactly match pinnedbase. Initial erroneous object-identity assertion and its failurelog retained; Core properties return detached equal descriptors. Evidence: retrieval-bootstrap-reuse-v1. No new paidcalls, database schema changes or primary writes.
