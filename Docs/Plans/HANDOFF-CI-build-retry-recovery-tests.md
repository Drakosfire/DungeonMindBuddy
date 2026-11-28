# Build retry recovery tests

ACTIVE: user requested frontend diagnostic repairs and Trace deployment. Serial branch `codex/frontend-build-retry-tests`, based on `origin/main` at `6f7fedb51`, follows #4805. Scope: retained-discussion and fresh-authoring Build retry recovery fixtures in the shared conversation integration file, plus this brief. Grouped lineage tests remain separate.

Use current exact-turn v3 correlation. Supply the retained discussion snapshot for refusal/remount cases; explicitly return `build_authoring_retry_required` for cases testing fresh placement, delayed capture, revision change, and page/World departure. Preserve all draft, no-double-dispatch, stale-target and error assertions. Verify the affected cases, exact-SHA hosted verification and independent review. The next integrated discovered checkpoint includes this slice.
