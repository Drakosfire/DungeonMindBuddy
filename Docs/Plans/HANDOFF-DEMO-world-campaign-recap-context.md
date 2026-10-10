# DEMO handoff — bind campaign recap extraction to the selected World Graph

**Status:** ACTIVE implementation; PRIME owns independent review and merge.
**Base:** `main@5be59b2ee3c06913e607f0d64c938fba4515a235`
**Branch:** `codex/demo-world-recap-context-20261010`
**Scope:** Buddy recap graph extraction, review preparation, and confirm-time context validation.

## User outcome

When a GM creates a campaign recap graph extraction, Buddy uses the explicitly
selected managed World, resolves its exact active native Graph binding on the
server, and asks DungeonMind to verify campaign membership and the initialized
Graph head before writing staged corpus/source/run state. The immutable
observation follows the extraction run into prepare and confirm. A changed head,
campaign membership, or binding fails closed. Generic World authoring and
first-World worldbuilding remain independent of a campaign or pre-existing head.

## Contract consumed

DungeonMind PR #111 is merged at `b789ddc207a0a5a820a11f85e18d203d355d8f53`.
Buddy pins this exact source because it provides
`SourceAnchorIndexRequest` and the bearer-authenticated
`GET /v1/worlds/{world_id}/campaigns/{campaign_id}/ingest-context` contract.
The response is validated for schema, exact native World/campaign identity,
member status, head revision, graph schema, and payload SHA-256. A missing
membership remains 404; an uninitialized head remains 409 with
`world_graph_not_initialized`.

Configure `DUNGEONMIND_PUBLICATION_BASE_URL` as the MIND HTTP(S) origin and
`DUNGEONMIND_PUBLICATION_BEARER_TOKEN` as the bearer credential. The request
never accepts a native Graph World ID from the browser; it accepts only
`managed_world_id` and resolves the active binding server-side.

The extracted run lineage records schema, managed/native IDs, binding version,
campaign ID, extraction-time head, graph schema, and payload digest. This remains
immutable provenance; recap candidate extraction consumes source text and does
not depend on the Graph contents at that head. Prepare reads a fresh MIND
observation, checks membership and binding identity against the extraction
lineage, and reviews the unchanged candidate against the fresh mutation context.
It seals that current review head into the proposal and rechecks it before
returning. Confirm rechecks membership and binding identity, then relies on the
existing governed parent compare-and-swap; exact retries can return the existing
`already_applied` receipt after head advancement. Historical recap runs without
the new lineage remain eligible for explicit selected-World/source adoption
through the existing path. Existing extraction runs remain reusable while
their exact source, campaign membership, and selected binding identity remain
valid, even if another publication advances the head.

## Boundaries

- Generic document/World authoring and the first-World worldbuilding flow do not
  require a campaign or initialized Graph head.
- `generate_recap_memory` without graph extraction remains available for corpus
  maintenance. Any recap graph run requires a selected managed World.
- No historical S28 candidate is rewritten, re-extracted, adopted, or published
  by this slice. The corrected S28 candidate remains held and unbound; historical
  adoption requires its own authority and workflow.
- No MIND continuation paths, SERVER #1014 rollout, database/runtime changes,
  provider calls, or shared corpus writes are included.
- PRIME retains merge authority. This handoff does not claim demo acceptance.

## Verification checkpoint

The context and selected-target suites pass 13 tests, including a legacy-shaped
recap prepare boundary, reuse after an unrelated head advance, and confirm
replay after the head advances. Changed Python files pass Ruff, the
exact MIND-pinned `SourceAnchorIndexRequest` import succeeds against the current
MIND source, and `git diff --check` passes. The full recap API suite passes 26
tests using its fixture's isolated PostgreSQL databases, which it creates and
drops by unique name. An initial sandboxed run could not reach that endpoint;
the elevated run exposed implementation errors, which were fixed before the
passing rerun. The UI test runner is absent from this checkout's
`node_modules`; UI tests/build remain unverified here.

`uv lock --check --offline` cannot run to completion in this temporary checkout
because the ignored `out/hermes-agent` path required by the workspace lock is
absent. The source pin and matching lock source entries were updated to MIND
PR #111; package metadata and import compatibility were checked against that
exact source.

No recap was staged or extracted against a real World. No shared/production
database, product runtime, provider, or operator acceptance is involved or
claimed.
