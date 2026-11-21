# ONBOARD: temporary guest graph additions

Status: MERGED in PR #4304 at `b84831800c7d00e549bb73ea496633e1bd46d370`;
default-off and not a released Sizzek demo. The serial slice was authorized by the owner's onboarding goal. Bugbot
critiqued the design before activation; the decisions below adopt its findings.
The owner authorized the full
onboarding goal and explicitly asked visitors to add and connect a graph node.
The preceding signed-out Home slice #4297 merged at
`b9030763c9f71d59268a0b4f5df4dd4143e01c2c`; the snapshot foundation #4281 is
merged and remains disabled pending release qualification. This slice is serial.
Base `b9030763c9f71d59268a0b4f5df4dd4143e01c2c`; branch
`codex/onboard-guest-graph-sandbox`; checkout is this isolated Buddy lane. No
live World, provider, server port or database is leased.

## Outcome and boundary

On the guest release graph, a visitor can name a new point, connect it to an
existing released point, inspect the resulting relationship, and reset their
additions. Clearly label every visitor-authored point and relationship as
temporary. Explain before editing that additions exist only in the current page
session and disappear on reload or reset. A reset removes all additions and
selection without modifying the released copy. Released content and its source
citations remain unchanged and visibly distinct from visitor additions.

The guest overlay lives only in React memory, is per mounted guest experience,
and has no API, persistence, account transfer, model or provider access. Do not
put visitor-authored values or local IDs into URLs, release citations, telemetry
or browser storage. Never issue a mutation or fall through to managed World APIs.
Guest additions are rendered as text, bounded in length and count, use a
collision-free local namespace, and do not masquerade as owner-approved facts
or cited Graph assertions. A release/public-ID change or component unmount
discards the overlay. Existing release-local source and point deep links must
continue to resolve only against the fetched current published copy.

The overlay is scoped to the mounted `(publicId, release_id)` copy and must not
render against a replacement copy even for one frame. Temporary selection is
not encoded in URL state; browser history may change selection without deleting
additions. Reset replaces the current fragment with the copy's neutral map and
clears additions, drafts and selection. With no released nodes, explain why
adding a connected point is unavailable; never invent a target. Allow at most
ten temporary nodes and ten temporary links; trim inputs, reject empty labels,
control and bidirectional override characters, and bound node and relation
labels. Connections run from the new guest point to an explicitly selected
released point, resolved by ID even when labels duplicate. Temporary entries
have no owner citation or asserted/inferred badge. Text is rendered as text.
“Session” means the mounted guest experience: leaving or refreshing can discard
additions. This slice does not provide live revocation detection for bytes
already delivered to the browser.

This slice does not claim that a saved example or generated scene used a guest
addition. Guided Build/media, Play/reset, live guest generation and account
transfer are successors and retain their separate isolation and quality gates.
Sizzek World ingestion, explicit owner publication, real sign-in, user testing
and public launch remain outstanding.

## Proposed lease and verification

Expected write set: this handoff and truthful predecessor status sync; the
guest-release page, its scoped styles, and owning tests; small new guest-only
components/tests and their CI classification/selectors if necessary;
`apps/live-control-ui/src/App.guestHome.test.tsx` and
`apps/live-control-ui/src/App.guestRelease.test.tsx` solely to verify root and
direct-route composition. Avoid
shared auth, private Graph APIs, database/schema, model/provider, storage,
global navigation and unrelated Home changes. No concurrent write lane was found
in the open guest/graph PR search; recheck before review.

Before activation, independent critique must examine local ID collision,
browser history/deep links, release switch, reset, malicious user text, guest
isolation, loading/revocation, and honest behavior if no release nodes exist.
Verify both root Home and direct guest route: add/connect, inspect, reset,
reload, release switch, keyboard/mobile access and no persistence or private
network requests. Include exact-SHA hosted and full discovered diagnostics,
base comparison of inherited failures, Bugbot review, and synthetic browser
witnesses. Release activation and owner content acceptance are separate gates.
