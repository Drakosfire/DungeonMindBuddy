# Plan Image Studio integration timing repair

ACTIVE: user requested frontend diagnostic repair and Trace deployment. Serial test-only slice `codex/frontend-plan-image-tests` based on `origin/main` at `2c62d44f50a7e8152753526aebb2e27cc4e744c8`, after merged #4782. Scope: `PlanSurfacePage.test.tsx` and this brief.

Three tests open the Image Studio shell and immediately access a mock of its lazily imported child. Wait for the actual synthetic child to mount before inspecting props or placing an image. Preserve prompt identity, autosave, stale-placement and editor invariants; do not change runtime or bypass access checks.

Run the three affected integration tests, exact-head hosted and discovered diagnostics against the prior integrated baseline, and independent exact-head review. Other frontend failures remain in later serial slices.
