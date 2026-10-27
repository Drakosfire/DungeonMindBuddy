# INGEST — explicit GenerationEngine experiment targets

Status: SETTLED by Buddy#1826 merge
`b368c903d30c87865d25ce9d2bd5af66a5f4b927`, reviewed head
`19d48333d4fe86372bcb74e26dd27c6b71b0e23d`, independent Bugbot APPROVE,
204 owner tests, hosted integration/Docker gates passed. Protected API delivery
preserved all retained rows/files. ADVERSARY independently confirmed identical
consumer source trees and began ordinary comparisons. This lease has ended;
the separate OpenAI native-schema rejection is owned by
`HANDOFF-INGEST-openai-schema-projection.md`.

Original serial consumer slice. Owner: PRIME. Branch:
`codex/ingestion-explicit-targets`, existing buddy-context-loop checkout, base
`8a881050e46b61d007a7749bb6dd73678caa444c` (fresh remote main).
Authority: operator's explicit request that ingestion not reject models before
GE, OverMind#60 merge `e7c74bb00ff894825e507e42102098463d3b78b4` and its bounded
cross-owner contract. GE#29 is merged `2ef4a6d463b01cac193ce59e3959ada7a82d7d73`,
reviewed `24aef7ee0c668876190d77926fb8918a18cd4b03`, independent APPROVE,
401 owner tests and Python3.11/3.13 CI test/build/core-wheel gates passed.

## Invariant and critique

Caller-selected provider/model/settings must flow through the same registered
source, bounded process worker, pass sequence, advisory reviewer and evidence
ledger. Closed model pairs do not establish source safety or semantic quality.
Removing those guards must preserve executor ownership, writer/reviewer target
matching, source/revision binding, budgets, schema/evidence checks and no-fallback
behavior. Supported transports remain checked; unknown provider or blank model
fails before inference. No hard-coded replacement seven-model allowlist.

Preserve the exact existing DeepSeek/OpenRouter baseline request, including
its specific route and JSON instruction; do not apply that behavior to every
OpenRouter model. Explicit reasoning effort is configuration, not a silent
compatibility remap. Existing product defaults remain unchanged. Gazetteer gets
an optional explicit execution configuration at its current ordinary source
owner, so the benchmark need not bypass that owner to choose a target.

## Exclusive writes and topology

One PR, then dependent immutable benchmark adoption. Exclusive paths:
- src/graph_memory/extraction/bounded_recap_execution.py
- src/graph_memory/extraction/category_candidate_graph_extractor.py (advisory
  executor guard only; no prompts or schemas)
- apps/live_control_server/services/worldbuilding_ge_execution.py
- tests/test_bounded_recap_execution.py, tests/test_worldbuilding_edge_review.py,
  tests/test_worldbuilding_ge_execution.py
- pyproject.toml and uv.lock (exact GE pin/extra only)
- This handoff and HANDOFF-AGENT-final-answer-capture.md (settle merged predecessor).

Open PRs re-anchored. Historical #1146 overlaps bounded-client diagnostics and
#1148 concerns recap prompts; neither is adopted or advanced here. PRIME assigns
this current-main serial write lease; those historical lanes have no concurrent
write authority over these paths during this slice. ADVERSARY edits only eval
records/corpus/gold, not these runtime paths. GE's implementation lease ended
at #29 merge. Plan final-answer capture #1825 is merged/delivered at this base;
its lockfile lease is complete and transfers to this slice.

## Verification and delivery

Provider-free tests cover arbitrary explicit models on supported transports,
invalid selections, optional reasoning, unchanged DeepSeek wire behavior,
non-DeepSeek OpenRouter isolation, exact target matching and same-pass/source
advisory behavior. Exercise ordinary Gazetteer registered-source selection and
ledger target truth. Preserve all source/scope/revision rejection tests. Worker
and GE conformance/termination tests remain applicable; no direct SDK route.
Use existing dependencies and disposable APP54329 fixtures only. No primary APP,
native Graph, corpus or runtime state writes during tests. No live model calls,
benchmark dependency updates, ingestion prompts/schemas/pass-order/representation,
gold or semantic-validation changes. No historical repair/reingestion or model
winner selection. Exact cumulative diff, independent Bugbot, commit/push/PR and
CI before PRIME merge; protected API adoption follows applicable gates. Comparison
readiness belongs to ADVERSARY after exact owner pins are handed back.
