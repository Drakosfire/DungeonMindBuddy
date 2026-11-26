# Plan and Play retry grouping tests

ACTIVE: user requested diagnostic repairs and Trace deployment. Serial branch `codex/frontend-plan-play-retry-group-tests`, based on `origin/main` at `d7d612c7e`, follows #4807. Scope: Plan and Play branches of the existing consecutive retry integration case and this brief; the Build lineage case remains unchanged.

Current saved-message details are fetched by exact sequence with correlation. Make the test fixture return the requested full turn for that exact read and open Trace before inspecting attempt details. Preserve one visible question, two prior attempts, one retry control, and remount grouping. Verify both cases, exact-SHA hosted and independent review. Full discovered diagnostics run at the next integrated checkpoint.
