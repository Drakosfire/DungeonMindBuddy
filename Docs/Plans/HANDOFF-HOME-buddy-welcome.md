# HOME: illustrated Buddy welcome

Status: ACTIVE, serial. Explicit operator goal in this chat authorizes implementation through reviewable PRs; merge and deployment remain separate authority.

Owner/lane: this chat, `codex/buddy-home-welcome`, existing isolated checkout `/home/drakosfire/Projects/.codex/7550/DungeonMindBuddy`, freshly fetched `origin/main`. No shared runtime/database lease. No service starts without an independently selected port. Implementation base: `81d7c90f4e320d2d038912f8c61f192389748ae8`.

Outcome: match the approved charcoal/parchment/gold Home concept, with original mill artwork, meaningful synthetic preview references, introductory anchors, existing sign-in and selected-World entry, and links back to DungeonMind. Preserve app chrome, account controls and World ownership. Preview data never enters private World state.

Write lease: this handoff; `apps/live-control-ui/src/BuddyApp.tsx`; new `apps/live-control-ui/src/home/` files; `App.tsx` for the two explicit signed-out Home anchors; `App.test.tsx` for the changed landing contract. Shared navigation/auth/World-selector owners are consumed, not modified. Inspect open PRs before shared-path changes. Open-PR scan found no Home implementation; existing Plan/Play welcome work stays outside this slice. Anchor admission is necessary because the existing signed-out gate otherwise rejects introductory navigation; no general guest-route expansion is authorized.

Failure cases: signed-out preview must never fetch private World data; references must reveal actual sample content; unavailable/loading World selection must not expose a false Open action; primary entry must retain World context; narrow layouts and keyboard focus must remain usable. Auth uses the existing server login path and sanitized return destination, not custom SSO.

Validation: focused Home interaction tests; desktop/mobile browser comparison with approved concept, keyboard/anchor/sample and auth-state witnesses; final committed exact-SHA hosted verifier and full discovered diagnostic, retain failures truthfully. Inspect cumulative base-to-head diff before commit/push/PR. Independent review and merge authority remain separate.

Additional owning-boundary test lease: `apps/live-control-ui/src/App.guestEntry.test.tsx` to prove signed-out Home anchors and sample notes never call private APIs.

Successor: serial main-site Open Buddy link in `Drakosfire/LandingPage`, after this PR is settled under repository authority. Main-site source/lease must be freshly inspected before activation; no write lease to that repository is granted by this file. Full goal retains both destinations.
