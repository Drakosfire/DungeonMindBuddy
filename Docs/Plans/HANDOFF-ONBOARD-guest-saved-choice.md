# ONBOARD: a resettable saved guest choice

Status: ACTIVE. Serial successor to saved guest example PR #4318, merged at
`42fab090985407f32b237bf34685a4cdda734268`. The owner's onboarding goal
authorizes the bounded implementation, independent Bugbot review, merge and
deployment after the applicable gates. Base `402b6d41f4c5b5ef988a7fd4db0412c32cce2e11`;
branch `codex/onboard-guest-saved-choice`, isolated Buddy checkout. No live
World, provider, port or database is leased. Bugbot independently critiqued the
design; its findings are adopted below.

## Outcome and boundary

An owner can optionally attach one prewritten choice to an owner-authored saved
scene in a guest release. It has one prompt, exactly two distinct labels and two
prewritten outcomes. The owner reviews the prompt, both labels and both complete
outcomes before approving the exact release digest. Tell the owner both outcomes
are public, even before a guest chooses. Guests can select either option, see its
prewritten outcome and reset the choice. This is fictional possibility, not a
claim of actual play, live generation or personalization from temporary graph
additions. No guest input is sent to a server, inserted into URLs or stored in
browser persistence. A release/public-ID change, unmount, reload or reset clears
the outcome. Resetting the graph additions also resets the choice. The saved
scene and immutable published copy never change.

The prompt is at most 240 characters; each label at most 80 and each outcome at
most 2,000. Compare labels after trimming and Unicode case-folding; equivalent
labels are rejected. Treat option positions zero and one as copy-local stable
identities, never labels or external IDs. Visitors may switch freely between
the two prewritten outcomes; reset clears the selection, not an actual play
record. Show both full outcomes together, uncollapsed, during owner review.

Use a distinct optional, versioned, closed `saved_choice` manifest field that is
valid only with an existing valid saved example. Absence means an older or
choice-free release. A malformed present field must fail closed in staging,
publication and the owner review; the guest must not render it as an available
choice. Bound all text, reject blank, overlong, duplicate labels, control and
bidi characters and unsupported destinations under the existing release text
policy; render plain text only. No arbitrary HTML, Markdown execution, links,
remote assets, template interpolation, client identifiers or private source
identifiers enter the copy. The canonical release digest covers all choice
bytes. Owner changes require preparing and reviewing a new candidate.

The existing guest sandbox remains page-local and release-keyed. Selection is
not a PlayRun, a persistent player decision, a provider request or an indication
that either possible outcome happened. Keep the selected outcome and reset
control keyboard accessible, announce result changes without stealing focus,
and preserve the signed-out root and direct guest entry. No account transfer,
graph-informed generation, live media generation, source ingestion, canon
decision, real Play session or Sizzek publication is implied by this slice.

## Proposed lease and verification

Expected writes: this handoff, truthful settlement of the predecessor handoff;
`apps/live_control_server/services/guest_release_preparation.py`,
`src/application_state/guest_release_example.py`, and the existing staging and
publication callers only as needed to enforce choice closure; owner selection,
owner review, guest page, guest-scoped style/helpers and owning tests; affected
guest-release backend integration and frontend composition tests and required
CI classification. Do not change auth, provider, model prompts, managed World
mutations, PlayRun, shared editor, schema migrations or deployment settings.
The open-PR inventory checked at design found no other guest-release path in
62 open PRs. Recheck leases before activation and review.

Before activation, independent critique must cover hidden outcomes, immutable
digest review, malformed and old manifests, sensitive text/destinations,
selection and reset across release changes, browser history, keyboard and
assistive technology semantics. Verify owner prepare→exact review→publish→
anonymous read and withdrawal at the owning boundary with isolated data; prove
invalid or foreign shape fails, no guest mutation requests and no persistence;
cover option switching, reset, release change and older copies. Run exact-SHA
backend contract, hosted frontend verifier and full discovered diagnostic at an
integrated checkpoint, with baseline comparison; independently review the
cumulative diff and perform synthetic desktop/mobile browser witnesses. Full
release qualification, owner-selected Sizzek content and production rollout
remain separate gates.
