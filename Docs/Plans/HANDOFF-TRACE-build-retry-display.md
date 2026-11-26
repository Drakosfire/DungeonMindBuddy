# TRACE: saved Build retry display

Status: ACTIVE. The user authorized fixing the remaining diagnostic regressions and deploying the Trace release. Serial slice based on origin/main in `codex/build-retry-lineage-projection`; no overlapping open implementation PR was identified. Outcome: show explicitly linked Build retry attempts as one conversation entry after reload, without granting retry authority from display data.

Write scope: active conversation message projection and route, its strict frontend decoder and grouping consumer, and focused route, database, decoder and mounted-conversation tests. The existing v4 response remains unchanged for clients that do not request the new projection; any new projection is bounded, World/conversation scoped, and display-only. An actual retry must still re-read and verify the exact turn and eligibility. Never infer lineage from equal prompt text. Pagination and successor outside the page must not revive a historical Retry button.

Verification: independent exact-head review; focused owner-isolated database and route contracts including foreign World/pagination and v4 compatibility; frontend decoder/grouping and mounted retry tests; clean exact-SHA hosted frontend verification and integrated full discovered diagnostic. Merge this slice before starting its successor.
