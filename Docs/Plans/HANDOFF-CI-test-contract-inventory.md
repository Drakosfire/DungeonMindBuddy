# CI: inventory and reusable regression contracts

Status: ACTIVE. Alan authorized a five-PR additive CI transition; this is PR 1 only.
Base: 534ff9c70499d6dc847c949465e95a32e1012467.
Branch: codex/ci-test-contract-inventory. Topology: serial CI workstream; PR 2 is
not active before this reviewed PR is qualified and the coordinator authorizes
its successor. Opening this draft PR is authorized; deployment/protection changes
are not. Do not interpret the five-stage plan as permission to weaken current gates.

## Ownership and predecessor settlement

The CI implementation owner adopts this bounded handoff under Alan's assigned
inventory/transition-design scope. Current-main and open PRs were inspected:
#2276 exclusively owns graph route/Surface/canvas behavior; other Surface and
INGEST stacked lanes do not own CI command extraction. #2281 is merged and its
handoff is settled here, releasing the predecessor lease. Historical hosted-CI
handoff remains headed ACTIVE but records a completed original workflow creation;
no current PR/lane claims that historical lease. This serial transition explicitly
owns CI files under Alan's new instruction. Product, runtime and live-data paths
are excluded. No shared DB, server, ports or browser profile is allocated in PR 1.

## Write lease

- .github/workflows/hosted-validation.yml
- .github/workflows/world-ownership-core.yml
- ci/contracts.json and ci/test-classification.json
- scripts/ci_contract.py and scripts/ci_frontend_contract.mjs
- tests/test_ci_contract.py and tests/fixtures/ci_original_commands.json
- tests/test_ownership_ci_partition.py (preserve predecessor guard after extraction)
- Docs/Plans/HANDOFF-CI-frontend-coverage-balanced-ownership.md (settlement)
- This handoff and Docs/Plans/DESIGN-CI-additive-qualification.md

## Invariant

Extract exactly the existing pytest arguments and ordered frontend commands into
one versioned manifest, with Python and Node consumers for their existing runners.
Keep every existing job, matrix, dependency, timeout, service, failure aggregation,
trigger, permission and test selection. Add only inventory/contract guards in the
existing World/Content job. Preserve the ordinary Build partition and per-test
fresh DB clones. Do not run lane classification as a selector at this stage.

Every discovered test file receives exactly one explicit fast/domain-integration/
qualification assignment. Unclassified, stale or duplicate assignments fail. Test
names inherit their file's lane; lane counts are file counts, never case counts.
Vitest/Playwright discovery-config drift and pytest testpath/pattern drift fail
until reviewed. Non-ignored untracked test files are included. Python discovery
matches testpaths tests with test_*.py/*_test.py; frontend matches default Vitest
file patterns, and the configured UI Playwright pattern is separately inventoried.
Fast labels are candidates, not a promise of speed, no-DB purity or rollout safety.

Commands print checkout SHA, exact argv, elapsed duration and exit status, while
native pytest/Vitest output retains executed-case counts. Failure must propagate
and prevent later commands; no swallowing errors or shell-string execution.
Inventory prints classified/discovered file counts and its own measured duration.

## Verification and remaining gates

Compare original workflow arguments against the extracted manifest independently;
compare actual old/new collection identities and partition ownership, preserving
all original cases. Check Python/Node runner nonzero propagation and no later-step
execution. Deliberately introduce missing/stale/duplicate inventory entries in
isolated tests, never by changing real selectors. Run guards, Ruff and actual
frontend command consumer, then independent cumulative exact-head review and both
unchanged hosted workflows. Publish SHA/counts/durations with provenance.

Full default non-live regression command (prepared disposable environment only):

```bash
uv run --locked python scripts/ci_contract.py inventory
uv run --locked python scripts/ci_contract.py commands
uv run --locked python scripts/ci_contract.py run full-regression
```

Prepare pinned Hermes, locked Python/npm dependencies and Playwright Chromium;
provide disposable PostgreSQL fixtures with no operator credentials, provider keys
or live state. Full regression runs all default pytest testpaths, all Vitest tests,
TypeScript/Vite build and existing UI visual browser suite, stopping on any error.
Existing opt-in live_llm and optional embedding/provider tests remain explicitly
outside that offline default; a future qualification contract must record those
requirements separately, without inventing success or enabling paid/live execution.
PR 1 does not claim this broad suite already passes. Any collection/baseline failure
must remain visible and block later qualification rather than become an exclusion.
