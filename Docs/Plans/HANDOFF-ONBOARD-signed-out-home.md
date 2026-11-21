# ONBOARD: signed-out demo at Buddy Home

Status: MERGED in PR #4297 at `b9030763c9f71d59268a0b4f5df4dd4143e01c2c`;
the root demo remains disabled and unconfigured pending release qualification.
The slice was serial, explicitly authorized by the owner's onboarding goal
and clarification. Bugbot critiqued the proposed design before activation;
the decisions below adopt its findings. The owner explicitly clarified
that `buddy.dungeonmind.net` itself must make the Sizzek demo available while
signed out. The authorized onboarding goal includes review, merge and deployment
when applicable gates pass. This slice is serial after snapshot PR #4281, merged
at `74bc45dd0b1616be2a03d5fe84c1b5730b5cf3a8`. Base:
`74bc45dd0b1616be2a03d5fe84c1b5730b5cf3a8`; branch:
`codex/onboard-signed-out-home`; checkout: this isolated Buddy checkout. No live
World, production service, port or database is leased for implementation.

## Outcome and boundary

At the canonical root, signed-out visitors see the configured owner-published
guest copy directly, while authenticated users retain their current personal
World entry. The copy is read only in this slice. A missing or invalid public
configuration leaves the current welcome page usable; a withdrawn or missing
copy presents a truthful unavailable state. Sign-in must take visitors through
the existing DungeonMind flow and must not claim guest work is transferred.
The snapshot's approved public ID is deployment configuration, never a private
World identifier, and configuration alone does not publish anything. Leave all
feature flags off until owner content acceptance and release qualification.

Routing: inside the existing hosted authentication gate, select the
guest root only when auth is definitively signed out, the guest feature is
enabled, and a canonical configured public UUID is present. Do not mount the
private selected-World provider on that path. Recognize release-local root
fragments so refresh and browser Back/Forward stay on the guest surface, while
continuing to reject noncanonical paths and query-bearing bypasses. Direct
`/visit/{id}` links and authenticated Home behavior remain intact. Guest
actions must continue to call only release APIs with omitted credentials.
The guest surface needs a real sign-in link, not a root link that loops back to
the guest demo. Missing/revoked release or auth-status failure must not fall
through to a different published copy or any private World.

Require `VITE_GUEST_RELEASE_PAGE=1` and a lowercase canonical UUID in
`VITE_GUEST_HOME_PUBLIC_ID`. Missing or malformed configuration keeps the
existing welcome; a configured but unavailable release stays unavailable.
Only the definitive `signed_out` state selects the root demo; checking and
unavailable remain gate states, authenticated and local-operator states retain
their existing Home, and auth changes unmount the prior subtree. Allow root
`#copy/...` fragments only for a valid configured demo; resolve their content
against the fetched copy, never against a private World. Existing
`#buddy-about` and `#buddy-home-main` links retain the existing welcome page.
Other unknown fragments and query-bearing root URLs do not become guest
bypasses. Sign-in uses the existing login helper with return target `/`, so a
successful sign-in opens personal Home rather than replaying a guest fragment;
existing `auth_error` handling remains unchanged.

The owner-approved snapshot foundation is not the complete demo: temporary
graph edits, saved/live Build and media experiences, Play/reset, real source
ingestion and user evaluation remain serial successors. Do not expose private
Sizzek content or automatically enable a deployment during implementation.

## Proposed bounded lease and verification

Exclusive expected write set: this handoff and predecessor status sync;
`apps/live-control-ui/src/App.tsx`, its guest/root route tests; the minimal
guest-release page and its tests needed for Home composition and sign-in; any
small owned styling required for root presentation; a new focused app composition
test, `ci/contracts.json`, `ci/test-classification.json` and
`tests/test_ci_contract.py` only to include and guard that test in the existing
hosted contract. Preserve `src/localWorld` as the first selector. CI drafts
#2298 and #2288 are open; their workflow proposals do not grant a conflicting
lease for this narrow selector/classification update. Avoid changes to shared auth, selected-World state,
server APIs, migrations, lockfiles and unrelated Home behavior. The previous
Home #3965 and compact navigation #1080 are merged; #2313 is closed. Open
integration draft #3824 is not an exclusive route lease; recheck its current
head and active assignments before final review. No parallel implementation
lane is assigned by this handoff.

Bugbot's pre-activation critique called for the explicit auth transition,
fragment, configuration and login decisions above. Verify at app composition with
real gate state transitions and guest transport, including no private requests
in clean signed-out sessions, signed-in Home, refresh/navigation/deep links,
login and error states. Exercise pending guest fetch followed by authentication,
authenticated-to-signed-out, auth outage, account switching and malformed or
stale fragments. Test local operator and other existing entry routes.
Use exact-SHA hosted and full discovered frontend verification with honest base
comparisons, independent Bugbot review, and synthetic desktop/mobile browser
witnesses. Live deployment, real sign-in, owner content review and public
acceptance remain separate gates; don't claim them from mocks.
