# RETRIEVAL · Q01 writer transport capture

**Active** under the Q01 latency goal. Base `6473f3134b002bc02b35308ce290bbdfbad0a518`, branch `codex/q01-writer-transport`. Delivery is serial. The open cohort-inventory change #4217 owns batch preflight and is independent of this single-case experiment. Reconcile the workflow file at integration if both land.

Scope is the behavior of `evals/buddy_benchmark/context_capture.py`, its workflow CLI, the matching workflow tests, ordinary Plan contract test and this handoff. Keep the current writer-ready stop as the default. An explicit evaluation-only sink captures the exact authorized serialized request through GenerationEngine's lower transport. It never delegates or returns a provider result. Keep ordinary product routes and primary data untouched.

Verify byte equality, clock order, exactly one authorized request, interrupted lifecycle, zero external writer calls, and no retained assistant response. A sink-induced transport exception deliberately follows the SDK's uncertain post-dispatch lifecycle. It is not provider receipt. Validate on the owning isolated Plan contract before accepting. Later tracing and overhead experiments build on that proven endpoint.
