# HANDOFF — DEMO: Plan section targeting

**Status:** ACTIVE — PRIME authorized this independent Plan consumer slice.
**Owner:** DEMO.
**Base:** Buddy `main@0ecda4d7995244bdf24ed7ba721ddaac17d855fb` (verified current after #891 merged; #891 changed only `PlanSurfaceShell.test.tsx`, outside this lease).
**Branch/worktree:** `codex/demo-plan-section-targeting` at `/tmp/demo-plan-section-targeting`.
**PR topology:** parallel-independent from the frozen #886 navigation shell PR at `e66afe387ea34a7f2a2467e27bfbcbc7f058a1be`; this is one separate PR, not stacked on #886, with no #886 file or runtime overlap.

**Lease amendment:** PRIME explicitly added
`apps/live-control-ui/src/planSurface/agentEdit/planAgentEditProposal.ts` and its
existing `planAgentEditProposal.test.ts` for section capture, typed inventory,
and full-document Apply validation. After ARCHITECTURE's contract ruling, PRIME
also added
`apps/live_control_server/services/plan_document_edit_proposal.py` and
`tests/test_world_plan_edit_proposal.py` for the narrow World-only replacement
prompt and its tests. No other server, route, model, API/schema or campaign test
path is leased.

## Mission

Let a Plan author target a round-trip-safe mounted Markdown heading section in
the existing `WorldPlanAgentConversation` composer. An available selected
section becomes the current editor selection, then follows the existing captured
target → proposal → review → Apply to mounted draft flow. For an exact
whole-section selection only, the existing `selected_text` field carries the
section's canonical Markdown bytes; the existing digest binds those bytes. There
is no new wire field or schema. Save remains a separate explicit action.

The capability uses the existing Plan composer and adds one bounded World
replace-selection prompt instruction so the provider can echo already-present
protected tokens. It does not change committed-basis Ask, `graph_request`,
`api/types`, client request shape, backend retrieval, Graph policy, or the held
APP-STATE #865 runtime. It does not claim campaign-wide retrieval or session
generation. Cards, playable markers and linked nodes do not become Graph
admission.

## Invariant

- A root-level Markdown heading selects its own heading through the content before
  the next root heading of the same or higher level. Child headings remain inside
  the parent range. Duplicate labels remain independently selectable by stable
  position identity, not by label text.
- A heading section is only a convenience for setting the editor selection. The
  existing capture bridge remains authoritative for World, document, draft,
  revision, editor and selection-generation fences. A changed draft, switched
  Plan or Agent thread, stale editor or changed selection invalidates a pending
  review under the existing fences.
- A preamble, empty draft, or document without root headings is reported honestly;
  the author can still make a direct editor selection or place a caret and use the
  existing composer.
- Whole-section capture serializes the selected editor root blocks with the same
  serializer as the full draft, strips frontmatter only for locating that excerpt,
  and requires one exact unique match. Ambiguous, missing, or over-cap sections
  fail before the provider call. The selected Markdown, not a new client claim,
  is bound by the existing selection digest.
- Selecting a section makes no API call. Only explicit proposal submission calls
  the existing World Plan proposal API. Apply changes the mounted draft only; it
  never prepares or commits a save. Do not auto-apply or add a second composer.
- The whole-section replacement must preserve the exact typed inventory of
  existing v2 playable markers and graph references, in order and under the same
  heading path. The provider prompt requests exact echoes, but frontend inventory
  and full-document simulation are the authority. Arbitrary text selections,
  caret edits, and campaign proposals retain their existing strict grammar.
- Apply replaces complete root blocks for a matched section. Before mutation it
  checks that the in-memory prefix and suffix are unchanged, that all protected
  identities remain, and that reimported prefix/suffix match the canonical
  baseline reimport. It also compares the admitted replacement's semantic tree
  with the selected subtree after full-document Markdown serialization and
  reimport. Plain-text whitespace normalization is allowed; node structure,
  marks, attributes, graph references and playable identities must remain.
- A proposal that changes its semantic tree through fragment or full-document
  round-trip is rejected before review or editor mutation. On Session 29, the
  parent Beat section currently combines adjacent list items during round-trip.
  Its option is visibly unavailable, and a direct whole-section capture is
  refused before the proposal API call. The nested Scene option remains
  available and actionable. Parent Beat editing remains pending a separate
  serializer/section-boundary repair.
- Preserve semantic editor structure, source quotes/callouts, all 90 v2 markers
  and all 72 linked node references in the Session 29 linked Plan, except for an
  explicitly reviewed change inside the selected range. Compare canonical
  serialization before and after and inspect the actual Save request. Do not
  claim original-byte identity where the established serializer normalizes
  Markdown. If unrelated source loss cannot be prevented through the existing
  capture/apply/save contracts, report the concrete boundary to PRIME; do not add
  a source-patching framework to this slice.

## Exclusive write lease

Modify only:

- `apps/live-control-ui/src/planSurface/components/WorldPlanAgentConversation.tsx`
- `apps/live-control-ui/src/planSurface/WorldPlanAgentReviewedEdit.integration.test.tsx`
- `apps/live-control-ui/src/planSurface/agentEdit/planSectionTarget.ts` (if a
  small pure range helper is useful)
- `apps/live-control-ui/src/planSurface/agentEdit/planSectionTarget.test.ts` (if
  that helper is added)
- `apps/live-control-ui/src/planSurface/agentEdit/planAgentEditProposal.ts`
- `apps/live-control-ui/src/planSurface/agentEdit/planAgentEditProposal.test.ts`
- `apps/live_control_server/services/plan_document_edit_proposal.py`
- `tests/test_world_plan_edit_proposal.py`
- this handoff

The proposal-helper lease is limited to the typed protected inventory from the
actual captured editor section and exact validation of its returned fragment.
Validate the simulated full-document Apply result too: preserve identity
sequence, occurrence and heading ownership; reject missing, changed, moved,
duplicated or newly introduced protected identities before the mounted draft can
change. Keep arbitrary selection/caret fragments and all non-section proposals
under the existing restricted grammar. Do not allow HTML, scripts, unsupported
links, lossy imports or warnings. An existing horizontal rule may be admitted
only when it is proven to belong to that captured section and survives the same
round-trip checks.

The service lease changes only the World replace-selection system prompt to
instruct the provider to echo existing protected tokens from the selected
section; it does not establish their provenance. Frontend typed inventory is
the deterministic safety gate. Keep caret and campaign prompt restrictions
unchanged. Service tests verify World prompt boundaries, token-preservation
instructions, refusal/pass-through and no-write behavior; do not claim live
provider reliability from injected generation output.

No CSS, AppChrome, `PlanSurfacePage`, navigation tests, API types/client,
backend routes/models, Graph policy, corpus edits or shared contracts. The
approved `selected_text` use is limited to canonical Markdown for an exact
whole-section selection; arbitrary editor selections keep their existing text
semantics. Do not add a request field or schema.

## Re-anchor and concurrent leases

The prior implementation base was `main@8dc639f06e05cf1809f42ecaba4c791ef21af66b`.
PR #891 merged at `0ecda4d7995244bdf24ed7ba721ddaac17d855fb`; its sole changed
path is `apps/live-control-ui/src/planSurface/PlanSurfaceShell.test.tsx`, with
no overlap with this lease. This branch was rebased onto that verified current
main SHA. The local `origin` in the reused temp clone points to an old local
checkout, so it is not used as remote authority.

The fresh open-PR audit found #886, #887, #869, #865, #844, #826, #798, #781,
#765, #764, #763, #761 and #760. Their changed-file lists do not overlap the
leased conversation component, reviewed-edit integration test or optional range
helper. #886 remains frozen at the head above with its independent visual gate
pending. APP-STATE #865 currently leases its agent-turn server model, route,
service and two backend tests; none is a Plan conversation UI path. PRIME
confirmed APP-STATE's chat-pane/retrieval recommendations do not activate a
lease on the files listed here. No ports, databases, provider state or live Plan
data are part of this lane.

## Required owning-boundary evidence

Use the actual corpus fixture
`corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Prep/Session 29 - Buddy Plan.md`.
It contains the linked Session 29 Plan, 72 `dmb-node:` references and 90
`dmb-playable-element:v2` markers. In mounted World Plan tests:

1. Select a scene heading and inspect its parent Beat heading. Prove the Scene
   target ends before the next same-or-higher-level heading and the nested
   headings remain within their parent range. Disable a parent section whose
   fragment round-trip changes editor structure, show the reason, and prove it
   makes no proposal API call or editor/Save mutation.
2. Propose and review the available nested Scene replacement, then Apply. Prove
   the intended selected region changes while outside editor structure/content,
   marker sequence and linked-node sequence remain semantically unchanged. Check
   the actual submitted source on the separate Save action. A proposal whose
   semantic tree changes during fragment or full-document reimport must fail
   before the editor changes.
3. Cover multi-paragraph blockquotes, bold/italic, canonical callouts and
   decision-consequence blocks through mounted Review → Apply → Save → reload.
   Cover repeated heading labels, preamble,
   empty/no-heading documents, stale draft/selection, and a Plan or thread switch.
   Selecting a section must not call the proposal API; Apply must not call
   prepare or commit; stale reviews must not mutate the editor.
4. Preserve precise evidence about Markdown canonicalization. Compare the mounted
   semantic serialization and Save payload instead of asserting untouched source
   bytes where normalization is part of the existing writer contract.

## Implementation evidence and limits

- Frontend owning-boundary evidence: 56 tests passed across section targeting,
  proposal admission and mounted Plan integration. Session 29 nested Scene edits
  apply and survive Save/reload with exact marker and graph-link sequence. The
  parent Beat option is disabled with a visible round-trip-safety reason, and a
  direct whole-section capture is refused before the proposal API call because
  its list structure changes on round-trip. The mounted editor and Save
  endpoints remain untouched. The separate nested Scene option remains
  actionable and passes its proposal, Apply, Save and reload flow.
  A separate mounted fixture proves bold/italic, a multi-paragraph blockquote,
  READ-ALOUD and DECISION-CONSEQUENCE content survives Review → Apply → Save →
  reload. Apply also rejects semantic drift before the mounted editor changes.
- Capture/admission tests cover exact selected digest, typed marker/reference
  preservation, changed/removed/duplicated/moved identity rejection, strict
  arbitrary selections, ambiguous excerpt refusal, the 8,000-character cap,
  stale fences and mounted Apply behavior. They also require semantic equality
  across the selected fragment round-trip.
- The Session 29 serializer's pre-existing full-document round-trip is not
  byte-idempotent: observed canonical editor export was 48,149 characters and
  reimport/export was 48,013. Section Apply compares unchanged prefix/suffix to
  the canonical baseline reimport and checks the selected semantic subtree
  separately. It does not claim original-byte preservation. Save integration
  verifies the prepared and committed payloads are identical and that all 90 v2
  markers and 72 linked references survive.
- Backend service evidence: 13 non-route tests passed after extracting MIND
  pin `7c69e447f6d4acc963ac09c6fb9cb48cc1c5b9cc` under `/tmp`. One
  database-backed route test was deselected
  because no designated disposable PostgreSQL DSN was available. The corrected
  service tests verify outer whitespace stripping and the unchanged caret prompt
  after whitespace normalization. Ruff and Python syntax checks passed. No
  database-backed route/write behavior is claimed.
- Direct TypeScript source checking with build metadata redirected to `/tmp`
  reports only inherited `TS2503: Cannot find namespace 'JSX'` at
  `src/statblocks/publication/ThreatPublicationPanel.tsx:553`; no error remains
  in leased files. The package wrapper could not write its build-info file under
  this checkout's read-only `node_modules` symlink. `git diff --check` passes.

The verified implementation is rebased onto
`main@0ecda4d7995244bdf24ed7ba721ddaac17d855fb`. Existing PR #890 is the
assigned publication target. Record its exact published head and verification
evidence there, then return any fidelity or contract limits to PRIME. Do not
merge.
