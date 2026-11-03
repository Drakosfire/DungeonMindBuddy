# RETRIEVAL: remove unreachable claim hydration compatibility

Status: ACTIVE under the operator's code cleanup and demolition goal.
Owner: PRIME. Base: origin/main@0ca2eba73adeffb9a4a2bfe80a204647686c6faf.
Branch: codex/remove-claim-hydration-compat.
Checkout: /home/drakosfire/.codex/worktrees/buddy-context-loop/DungeonMindBuddy.
Topology: serial after delivered PR2041; parallel-independent of ADVERSARY PR2040
and its parser/prompt successors. No overlapping source/test paths or runtime lease.

## Outcome and exclusive write set

Hydration delegates claim validation directly to GraphClaim and stores the session
once through the existing replace_session owner. Remove the empty legacy-schema
set, unreachable claim-field invention, unused schema plumbing, exception rethrow,
and fallback to create_session (the same locked assignment as replace_session).
Retain the real callers in Hermes, claim-ID handling and all current validation.

- src/graph_memory/interaction/session_hydrate.py.
- This handoff.
- Docs/Plans/HANDOFF-INGEST-remove-compact-preview-extractor.md: truthful merged
  predecessor settlement.
- Docs/Plans/HANDOFF-HERMES-worldbuilding-source-span-follow-through.md: settle
  its stale ACTIVE label against verified merged PR570; do not rewrite its history.

Repository-wide symbol searches found no registration, mutation or caller of the
empty compatibility set/private schema helpers outside the hydrator. The session
store's create/replace methods have identical locked assignments; both public
methods remain because other real callers exercise them. PR1868 has no hydrator
or store write paths. The historical source-span handoff's implementation merged
in August; its old conditional path listing is not an active lane.

## Critique and preserved boundaries

Missing/invalid claim kind, revision, authority, support and extra fields must
still refuse through GraphClaim.model_validate. Foreign claim revisions must not
be rebound to the session snapshot. Full claim/support and selected-subject source
metadata must round-trip. Missing session IDs still refuse before storage, and
unexpected store errors propagate instead of retrying the same write via an alias.

No packet schema policy, source authority, retrieval operation, session model,
publication behavior, new representation or compatibility adapter is introduced.
No provider, primary database, Graph, Gold, fixture or live service effects during
implementation. ADVERSARY owns Gold and ingestion-quality work independently;
manual Graph curation remains stopped.

## Verification and delivery

Run existing interaction and selected-subject source hydration tests, Ruff and
cumulative diff checks. Verify the real store implementation and all private
symbol references. Obtain independent Bugbot review of the exact cumulative head,
commit/push/open this bounded PR, and merge/deliver only after applicable CI and
integration gates. These checks establish hydration behavior, not ingestion quality.

## Author verification

Existing interaction and selected-subject source tests: 56 passed in 1.27s.
These exercise full claim round-trip, foreign revision preservation, malformed
claim refusals and source metadata continuity through the public hydrator.
Ruff and cumulative diff checks pass. No new tests mirror the removed unreachable
branch; existing owner-level contracts remain the acceptance checks. No provider,
primary, Graph, Gold or live service effects were used for these checks.
