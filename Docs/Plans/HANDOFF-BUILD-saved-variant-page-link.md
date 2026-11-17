# Link a saved conversation variant from its Build page

ACTIVE under the ordinary Meat Mind workflow goal. Serial successor to #3829.
Base 27f5e986439a3e1e68bb41e796b65d2b3125707c. Isolated checkout
aw-conversation-drafts, branch codex/aw-variant-page-link. Open page editing
search surfaced #2081, #2401, #1188 and #3824; avoid hosted transport changes.

Own the conversation draft control, its Build conversation wiring, the link
insertion owner and focused tests. Reuse BuildComposeBridge capture, apply,
and verified save. Bind the action to the original World and page; use an
explicit placement and save gesture. Canonicalize the link via the existing
saved variant URL helper. Keep a successful save recoverable if placement
or page persistence fails. Reject a foreign or changed page, preserve siblings,
and prove zero duplicates on replay plus fresh exact readback. Test with the
disposable AW environment. Keep primary state unchanged. Combat follows serially.

Review expanded the write set to the Build compose bridge, saved variant URL
helper, and shared document link admission. The generic generated proposal guard
continues to reject root-relative links. Typed placement admits only the
first-party variant destination and tests the actual editor serialization.
