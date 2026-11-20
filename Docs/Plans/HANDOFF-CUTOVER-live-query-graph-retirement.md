# Retire graph-attached live queries

MIND owns this serial V10 slice. Base e6c94c25f67d9f5363f89c5ad79fc161e39394ce
is the verified merge of Buddy PR #4252. Its reviewed source was
215a2f7b953f7a76d6fc0165793118df986bc765. The owning suite passed 68 tests,
the hosted suite passed 1,421 tests, the build and evidence validator
passed, and all three short checks passed.

Return typed HTTP 410 for graph-attached POST /live/query after DTO
validation and the native Graph GM authorization gate. Retire both
ordinary and Hermes graph requests before session lookup, managed World
lookup, graph resolution, Core access, or inference. Keep graphless
requests available to the current ChatModule.

Scope the implementation to the mounted route and its owning tests.
Verify malformed request and denied GM precedence, legacy and managed
graph requests, and zero downstream calls. Run the adjacent graphless
manifest and trace cases and exact-head hosted verification. Obtain
independent review before merging. Fresh generic /agent/turn graph
admission and retained Plan receipt recovery belong to a separate slice.
