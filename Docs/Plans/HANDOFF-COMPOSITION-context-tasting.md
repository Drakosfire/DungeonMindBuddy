# COMPOSITION: frozen-context writer tasting

Status: ACTIVE. Authority: user authorized nine-model Q15 tasting, identical retained
context/system prompt, blind answers and separate quality/timing/cost; no retrieval.

Serial topology; branch codex/writer-context-tasting from fetched origin/main.
Write lease: this handoff, evals/buddy_benchmark/workflow.py,
tests/test_buddy_benchmark_workflow.py, Docs/Guides/ordinary-benchmark-workflow.md.
Task artifacts: out/writer-context-tasting-v1. No databases, services or primary writes.

One capability: parameterized provider-only tasting from pinned context-ready capture.
Reuse immutable artifact writer and GenerationEngine. Keep retained source immutable,
validate request hash/size and context-ready binding before any dispatch. Freeze
identical instructions/input/schema across models. Preserve failures without replay.
Blind labels shuffled before dispatch; identity mapping separate from answer packet.
Hosted open-weight runs do not prove local performance. Not ordinary APP delivery.

Verification: local offline owner tests, cumulative diff inspection, immutable
request hashes, actual GE usage/cost observations, manual source-grounded assessment.

## Native structured-output adoption (user-authorized successor in this PR)

GE PR33 merged as 563ae839cd9fef9510e0e389e115ebb8671eb8ed after exact-head
independent PASS and435 local tests. Native strict schema replaces OpenRouter
schema prose; parameter-supporting routes are required. Historical tasting remains
immutable. The lease also includes pyproject.toml and uv.lock solely for this GE
pin, plus optional pinned endpoint-catalog filtering in the existing workflow and
its tests. Serial owner dependency is satisfied; no second Buddy PR.
Use a separate candidate environment; leave original .venv and prior artifacts
unchanged. Gold excluded; no retrieval/primary data effects. Exclude endpoints
without declared structured_outputs/response_format/reasoning support. Do not
weaken the schema, repair results manually or downgrade after an endpoint failure.
