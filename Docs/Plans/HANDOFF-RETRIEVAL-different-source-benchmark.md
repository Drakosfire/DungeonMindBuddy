# RETRIEVAL: different-source benchmark control

Status: ACTIVE. The user authorized the over-retrieval benchmark work and owns this lane.

Base: `origin/main` at `f549f313f58c35718104a97da376c17602e83812`. Branch: `codex/retrieval-different-source-benchmark`. Topology: parallel-independent of serving drafts #4973 (navigation) and #4979 (writer guidance); their source paths do not overlap this benchmark slice. Shared App clone remains serially owned by this workstream.

Scope and exclusive expected writes: development public/private negative-retrieval fixtures, their focused assessor test, and this handoff. Preserve private rubric separation. Add a synthetic control for the observed failure to honor a request for a different saved source. This is not a product fix or an independent held-out case.

Invariant and failure cases: an answer must cite the actual different source and its supported fact; the previously discussed source alone, fabricated evidence, unrelated retrieval, or mutation fail. Unknown semantic or acquisition capture must never count as a pass. Validate the fixture and assessor boundary without provider calls or databases, review the cumulative diff, then request independent exact-head review. Live benchmark and signed-in deployment verification remain separate goal requirements.
