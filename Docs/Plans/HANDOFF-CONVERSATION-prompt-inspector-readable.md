# CONVERSATION: readable captured-request inspection

SETTLED PRIME serial UI presentation slice on codex/prompt-inspector-readable,
based on7517a42083d7244f8adf6ff3166027b7cfedbdd0 (merged2332). No unmerged parent.
Existing context-loop checkout/dependencies. User requests nested JSON pretty
printing/wrapping, clear input-message semantics and reachable collapse controls.
2332 is delivered; do not expand its completed pending-bubble fix. API447264 and
UI496660 own8000/5202; no provider/database/session authority changes.

Display adjacent captured requests, not a fabricated chat transcript. Explain
that input-message positions/roles belong to the provider request; structural
removed/added fields do not prove memory deletion or context loss. Decode JSON
objects/arrays inside content strings only for readable display. Preserve exact
captured bytes, ordinary prose, values and HTML escaping; never mutate a request.
Use native disclosures with sticky identifying summaries and collapse affordances
inside prompt inspection. Fix the missing inline prompt CSS scope, not unrelated
conversation or source rendering. No global disclosure framework or model changes.

Exclusive writes: this handoff and predecessor HANDOFF-CONVERSATION-running-reply-placeholder.md settlement;
UI src/planSurface/components/PreparedRequestInspector.tsx/.test.tsx,
BuddyContextTrace.tsx, BuddyPromptInspector.tsx, BuddyContextTrace.css.
The existing Surface2330/2326/2313/2262, Storage2308 and CI2288/2298 lanes do not
own these paths. Earlier inspector presentation lease is adopted by PRIME.
Coordination remains off;2104 remains held. Serial independently reviewed PR.

Verify readable nested message content in full/component/diff views, exact-byte
roundtrip after navigation, plain text and escaped HTML, native collapse controls,
comparison and unavailable-capture behavior. Run owning tests, exact-source local
hosted/build and discovered baseline comparison. Review cumulative changes, merge
and deliver UI-only under standing authority. Current native browser connection
is unavailable; DOM tests and served-asset checks are not rendered/scroll proof.

Merged2333 at edc2f7c784e4d0843a3358fff7fe535545837650 and delivered reviewed
e2c515886 to5202; API447264 unchanged, UI549446.71 owner tests and exact hosted
passed; full discovered remains red with unchanged164 failures/1pending and
identical collection errors, five new passes/no removals.Independent bounded
Bugbot review approved. Served assets/cookie Graph1404 verified, not rendered
scroll-geometry proof. Raw captures and provider requests unchanged.
