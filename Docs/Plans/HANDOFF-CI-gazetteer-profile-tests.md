# Build extraction profile diagnostic repair

ACTIVE: user requested frontend diagnostic repair and Trace deployment. Serial test-only slice `codex/frontend-gazetteer-profile-tests`, based on `origin/main` at `75a6fc1545f3d956533d65621cda04a8ae9fb2e8`, follows merged #4770. Scope: `BuildGazetteerSelection.test.tsx` and this brief only.

Three tests fail before exercising profile selection because the mocked extraction hook omits the current saved-request arrays. Supply the empty recovery collections and assert the complete current hook input, including its World and recap context. Preserve the profile default, per-document reset, and launch lock assertions; do not change product behavior or remove coverage.

Verify the complete affected test file, exact-head hosted and discovered diagnostics, comparison with prior integrated baseline, and independent exact-head review. Continue unrelated diagnostic failures in separate serial slices.
