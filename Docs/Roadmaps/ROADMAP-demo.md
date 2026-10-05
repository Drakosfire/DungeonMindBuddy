# DEMO — one prepared adventure, one connected session

**Status:** ACTIVE — sole Buddy DEMO execution roadmap, adopted 2026-09-26  
**Repository:** `Drakosfire/DungeonMindBuddy`  
**Steward:** [STEWARDS-HANDOFF-demo.md](../Plans/STEWARDS-HANDOFF-demo.md)  
**Transfer mapping and source evidence:** [reconciliation report](../Reports/REPORT-DEMO-roadmap-reconciliation-2026-09-26.md)

## Product contract

A new GM creates/selects a World through the existing fixed-URL World primitive,
opens a usable blank World-scoped Plan, and authors or imports material. Neither
a campaign, recap, corpus import nor a published graph head is a prerequisite
for that blank document. The GM then prepares and explicitly confirms knowledge,
retrieves and cites it through the ordinary Agent path, develops a statblock and
image, and runs/resumes the session using readable, quickly reachable components.

The developer can design a representative component in the existing lightweight
workshop and mount it through Buddy's accepted surface/controller contracts.
Adding a presentation variant must not require reimplementing graph authority.

Scope is one bounded real adventure corpus, one demo World/space, and one session
with representative NPC, Threat/statblock, choice, encounter and roll table.
The final journey includes image selection and editable generated statblocks.
PDF parsing itself is outside scope; parsed Markdown is the agreed input.

## Adopted decisions — 2026-09-26

- Prove the durable local journey first; SERVER's hosted acceptance proceeds in
  parallel. A local PASS does not certify hosted readiness.
- Use a bounded Of Conks corpus for early rehearsal; retain C1/C2 regressions
  and final human acceptance. This replaces the old prerequisite that Of Conks
  cannot enter until the C1/C2 demo gate passes.
- DEMO owns Buddy demo-facing sequencing listed in the reconciliation. External
  domain ownership and active implementation leases remain intact.
- The adoption-time in-scope DEMO merge rule is superseded by the operator's
  2026-09-27 merge-control assignment, relayed by PRIME: **PRIME owns ecosystem
  merge coordination**. DEMO retains roadmap, product design, implementation
  and rehearsal ownership, and sends merge-ready PRs with the exact reviewed
  head, checks/live evidence, blockers and merge order to PRIME. DEMO does not
  merge autonomously or request another operator "Merge" for ordinary work.
  Existing review, live-witness and owner/lease holds remain prerequisites;
  this assignment does not approve #785 or any other pending PR.

## Card adoption direction — operator decision, 2026-10-03

**Status:** ADOPTED product direction and sequencing; production card implementation
requires a bounded Buddy-owned ACTIVE handoff. The operator authorized PRIME to
publish this documentation directly to remote main. This records direction,
not completion or approval of an unreviewed runtime change.

Adopt the useful interaction model demonstrated by DOGFOOD: connected scene cards,
scene lenses, choices, a grouped outline, location/map navigation, readable source
material and contextual writing. Plan is the editable preparation view; Play is
the interactive view of the same authored material. Preserve the prototype and
its private source/media/state snapshots as design and regression evidence.
Buddy PR #887 preserves the prototype at `5e2ef9f144e18f643dc1caa8316904dbfc801236`.
Its adoption inventory is pinned at `4b91c09d8a50188dfb1c9ce795358b32d17c02d7`
(`prototypes/plan-play-cards/ADOPTION-INVENTORY.md`). Neither is accepted
production implementation or independently frozen gold.

### Delivery order

1. Complete Graph-backed Ask in the shared canonical World conversation through
   Buddy's Agent Harness integration contract. It covers conversation execution,
   tools/context, authorization, lifecycle, evidence, and replay; the current
   Hermes adapter stays behind the existing seam. Do not add a new runtime
   abstraction or replace the current adapter in this slice. The synthetic
   DEMO consumer is ACTIVE under the pinned seven-path lease and
   consumes the accepted opt-in request/v2 response/history contract. No-policy
   requests stay byte-compatible v1. This fixture work does not prove parent-
   brokered traversal or live provider behavior; integrated acceptance, merge,
   and rollout wait for accepted APP-STATE and SERVER producer implementations.
2. After Graph acceptance, deliver one shared focused-card prepare/run experience
   across Session 29, Conks, and Sheep. Preserve source identity and evidence
   separately from navigation choices such as chronology, location, and scene
   focus. Reuse existing document and Playable authority; do not copy prototype
   persistence or add a second retrieval path.
3. Add durable Run choices, notes, submitted rolls, selected results, and combat
   outcomes, then complete the remaining J1–J6 journey. Keep rehearsal/preparation
   distinct from actual session outcomes and graph canon, and prove survival across
   navigation, restart, and resume at the owning boundary.
4. Advance J4 assets and reviewed COMPOSITOR packages through their own bounded
   lanes. They do not block Graph acceptance or the focused-card/run slice.

### Existing milestones retain their meaning

- J1: usable World preparation and source/document identity, including a card view.
- J2: multi-turn collaboration and durable reviewed card/document edits.
- J3: admitted Graph knowledge, reliable retrieval/citation and governed read-after-write.
- J4: real generation, accepted statblock/image versions and usable references.
- J5: cards/lenses/maps/choices make preparation a playable instrument.
- J6: choices, rolls, combat state and outcomes survive navigation/restart/resume.

No J1–J6 gate is closed by prototype screenshots or this reprioritization. The
#886 geometry repair is merged and its bounded technical gate passed; #869
movement and independent Graph/auth acceptance holds remain.
The operator's live 5202 session is reserved; coordinate any replacement with
SERVER and PRIME rather than restarting it for a fixture.

### Ownership and next dispatch

DEMO owns the product contract, first bounded production card handoff and
implementation sequence. ARCHITECTURE critiques reuse of document/Playable,
surface targeting, media and presentation contracts. APP-STATE owns any required
durable Run/notes/action-state change after the relevant contract is bounded;
no schema implementation is activated by this direction. SERVER owns runtime,
local credentials and Graph adapter integration. DungeonMind remains Graph
knowledge/evidence authority; COMPOSITOR produces source-backed packages for
DungeonMind admission and Buddy projection, not a competing knowledge store.

DOGFOOD supplies the pinned behavior inventory, representative fixtures and
observed usability evidence, and preserves private corpora/media outside Git.
RAKE DUTY advances the next free slice through targeted reconnaissance and
bounded tasks delegated by owners, without editing active leases or becoming a
passive status watcher. PRIME reviews exact implementation heads and coordinates
merges. Each new runtime slice declares its paths, contracts, resource ownership
and owning-boundary evidence before implementation. Product acceptance includes
operator use; visual polish alone does not establish durable or Graph behavior.

## Current execution checkpoint

The end-to-end demo remains unaccepted. Several integration and rehearsal steps
are now proven; J1–J6 have not passed as a connected journey.

**Plan conversation integration update (2026-10-03):** Buddy #900 and #902 are
merged at `f8712198848598c5ce83248eb66a54d93c1fd044` and
`3d27a0550cb0ffa74fb7ce9cb301435fcaef1eb2`. Saved-World Plan now consumes the
canonical World conversation for visible history/Ask recovery, and Compose/Revise
proposal context is assembled server-side from exact-basis completed Ask and
PlanAction pairs. This is code integration, not the missing live Graph-backed
Plan witness or full J2 acceptance. The Graph-backed product witness remains
unleased; the independent Agent composer usability slice merged as #904 and its
lease is closed. See the execution ledger entry below for the Graph witness and
owner/resource questions.

**Serial settlement at #909 activation (2026-10-04):** Buddy `origin/main` was
`e7b1464af6474e64a0f36c8a2fc57927b85db190`. PR #904 merged at
`fb1c48d622c9d8d404b1dddb5d5f618e03cc7ef0` from reviewed head
`c355234d1486d8cbc46aa9afa611d6d1340b812c`; its Agent composer lease is closed.
PR #886 merged at `4efada56aa93d529bf49128d82ba2d097b074af1` from tested head
`502b54d713e32e48f160182170c87b4f41fca990`. Its focused suite passed 187/187,
the isolated desktop/mobile geometry gate passed 1/1, and its Plan Page/shell
lease is released. The inherited UI typecheck failure at
`ThreatPublicationPanel.tsx:553` remains present on main and was not changed by
#886.

- RAKE PR #908 closed the bounded duplicate-v2-effect-target mismatch and
  merged at `e7b1464af6474e64a0f36c8a2fc57927b85db190` from reviewed head
  `fb866cd707ffc622b6be053822b0ffb03e0901b7`. Its UI identity/index/conformance
  suites passed 53/53 and Python passed 7/7. The shared fixture covers seven
  effect-target cases only; it does not establish full grammar parity for
  unknown versions, mixed grammars, or orphan Choice/Option structures.
  PRIME activated the serial DEMO card slice on that exact main with the
  exclusive lease in
  [HANDOFF-DEMO-saved-plan-card-projection.md](../Plans/HANDOFF-DEMO-saved-plan-card-projection.md).
  Its own model tests must fail closed for malformed, mixed, unknown, and orphan
  structures. No full parser equivalence or Run admission is claimed.
- **Graph-grounded saved-World Plan Ask — synthetic consumer ACTIVE (2026-10-05).**
  The canonical route is the server-owned `/api/live/agent/turn` World
  conversation; the legacy Plan `/api/live/query` path remains outside this
  capability. The initial design/roadmap handoff merged as Buddy #921 at
  `6240620423989ce0d132c26861c1e0b09cab3053` and was BLOCKED while owner
  contracts were unsettled. Buddy #923's APP-STATE receipt/replay foundation
  later merged at `93c07c243acd9abc9acc044f9a4e59390710871d`; #924's final
  view from the current Hermes adapter and pre-SDK budget guard merged at
  `6319ff30466dd9ab2e3e0752fce31ac8a71b7d4b`.
  PRIME accepted APP-STATE's portable execution-ledger design at
  `e907c904c95854ce539c919bac8e868a5fe4f69d` and the SERVER response/history
  projection in its route handoff at
  `70b1da70858a16dbe113cfa2967b76b7e23516a7`. SERVER and APP-STATE retain their
  own producer implementation/evidence leases. PRIME activated DEMO's serial
  synthetic consumer on base `main@6319ff30466dd9ab2e3e0752fce31ac8a71b7d4b`,
  branch `codex/demo-graph-execution-consumer`, under
  [the active handoff](../Plans/HANDOFF-DEMO-plan-graph-grounded-ask.md).
  This UI/API fixture slice preserves byte-compatible no-policy v1 behavior,
  consumes policy-only response/history v2, and presents only validated
  completion/citation and safe execution-disposition data. The capability is
  Buddy's runtime-neutral Agent Harness integration for conversation execution,
  tools/context, authorization, lifecycle, evidence, and replay; Hermes is the
  current concrete adapter behind the existing seam. It must never redispatch
  an authorized/unknown attempt or expose the raw execution ledger.
  #917 remains prototype evidence only; it is not a predecessor or code source.
  #914's visual hold is independent. PRIME reports scoped APP-STATE acceptance
  at local ref `7a8365a5a354e9d3c85e788112f7904f1e517cce` (publication approval
  pending) and SERVER acceptance at PR #926 head
  `746711815577e022e6961b32c135395e00d36531`. DEMO's mounted history test now
  consumes a body emitted by SERVER's actual v2 history projection/serializer
  using the APP-STATE execution types from that exact ref; it renders grounded
  status, citation, and completed/no-redispatch guidance. This is a joined
  wire-shape witness, not persisted runtime integration. Producer publication,
  merge, live/provider behavior and rollout remain gated; the fixture uses no
  live Graph, provider, service or database.
- #887 remains DOGFOOD's prototype-only evidence lane. Its private corpus,
  media, and state snapshots are not production data or sources to copy.
- #869, head `23d76f4d4f4f223b62067024e152e8cb2dde37b8`, remains
  Draft/HOLD for real movement preview/edit/Save/reload. Prior temporary
  runtime evidence below is historical; a fresh isolated lane is still needed.
- Operator UI 5202/API 8000 and DOGFOOD 5203 remain reserved; no dispatch
  authorizes replacing those runtimes.

**Saved-Plan card projection — MERGED (2026-10-04):** DEMO delivered the single
serial card/document projection in [PR #909](https://github.com/Drakosfire/DungeonMindBuddy/pull/909),
opened against `main@e7b1464af6474e64a0f36c8a2fc57927b85db190` from
`codex/demo-first-saved-plan-card-projection`. Its initial implementation head
is `ffd83e424bb238dc2331cf55ab6237993bc0762e`; its exact reviewed head is
`662b1e221617c7e900320f37fd27ee80d0858fe6`, merged at
`79611f775c98eadc6695fda0314f057f71801eb2`. The view is a read-only lens
over the same mounted editor draft; supported edits stay in Document and use
ordinary Save plus a fresh reopen. It adds no card store, parser admission,
Run, Graph, or J1–J6 acceptance. Focused suites pass 242/242: the model,
mounted tests, Plan Page/EditHost, and Playable index/conformance pass 109/109;
Markdown ingress and Plan Save tests pass 133/133. Mounted evidence now includes
the v2 editor-to-Cards-to-Save-to-reopen writer path and a pending/uncertain-save
regression that keeps the revision/digest pair unavailable until verified. A
reopened persisted server draft with no local pending write remains readable in
Document and is labeled uncommitted in Cards until ordinary Save and fresh
committed reopen; an unknown snapshot status keeps the saved basis unavailable.
A production Vite build to `/tmp` passes with the repository's existing
large-chunk advisory. The UI typecheck still reports only
`ThreatPublicationPanel.tsx(553,77): TS2503 Cannot find namespace 'JSX'`.
On the isolated synthetic preview, desktop 1280×800 had no horizontal overflow
(document width 1265px); mobile 390×844 had body width 375px and a 335px card
region with 20px side insets. The mobile heading/grid styles applied.
PRIME reports an independent 20/20 card-test review and a 71/71 Page/Card/EditHost
rerun on the exact clean head. The implementation lease is closed. No operator
acceptance or J1–J6 completion is claimed. Ports 5202, 8000, and 5203 remain
untouched.

**Merged — selected committed-card Plan Ask:**
After #909, add the selected committed Playable-card identity to the existing
server-owned World conversation's canonical Plan Ask. Do not include proposal,
review or Apply targeting in this first capability.

The inspected baseline `origin/main@414ae10436f95a10022723b4e8e02ae4c8a01aba`
shows that `PlanSurfacePage` publishes `agentContext: null`, ambient Plan context
has no card selection, `WorldPlanAgentTurnRequestV1` has no selected-element
target, and strict server `AgentTurnRequest` rejects unknown fields. The generic
Plan surface-context resolver rejects non-empty Plan pointers
(`tests/test_agent_surface_context.py::test_non_empty_plan_pointers_reject_surface`).
A typed selected-Playable `{kind, id}` target on the existing canonical managed-
World Plan turn, with Buddy server admission, is therefore required. Bind it to
the exact World, document/object revision, actual WorkRevision ID and
`revision_n`, content digest, and immutable turn/replay identity. Registry
`loaded_revision` is not a substitute for the WorkRevision pin. Reject stale, foreign, non-canonical or
missing targets. If membership requires a Plan read, define a pinned committed-
Plan read and nondisclosure behavior. The selected target must resolve against
the same committed Plan basis the server uses for Ask; fail closed whenever the
UI cannot prove that correspondence, including an unresolved dirty-draft case.
During a dirty edit, the UI may retain the selection only while the exact
`{kind, id}` remains unique in both the current mounted Cards projection and the
verified saved baseline. Duplicate or missing identity in either projection
marks the target stale and blocks Ask until the operator clears or reselects it.

Preserve the existing authorized server-resolved committed Plan context in
graphless Ask (`agent_turn_service.py` uses `_plan_message`). Send no client card,
source or draft Markdown and no Graph payload; keep `graph_request=none` and
`graph_selection=null`. If target provenance enters durable receipts/history,
APP-STATE has accepted the existing-supporting-reference storage and fingerprint contract. First-slice proof
must cover mounted selection-to-identity mapping, request pins and immutable
replay, stale target/document/basis rejection, unchanged World conversation
identity, and graph-disabled Ask with the existing committed Plan context.

Selected-card Compose/Review/Apply is a named serial successor, not implied by
this Ask capability. It must map exact v1/v2 Scene, Choice and Option body ranges
(including sibling headings and list items), define dirty-draft targeting, and
fence review/Apply through `WorldPlanEditBridge` before claiming selected-card
proposal → Apply → ordinary Save → fresh reopen. Existing document-selection
proposals remain unchanged. PRIME activated the bounded single DEMO implementation PR from `f8ad152c669e76cccb21fecfb9aecc3656589e5b` under [HANDOFF-DEMO-plan-agent-card-target](../Plans/HANDOFF-DEMO-plan-agent-card-target.md), after DEMO, SERVER, and APP-STATE accepted the contract. PR #911 merged at `4efdef1898e78aa3590a39e8f84c1fdb901b2695` from reviewed head `72b67cd7fcb91f1db0e5b58888d84e6d451c36f1`; the handoff records owning review/test evidence and closes the write lease. Cards can focus Ask on the exact committed Plan, with immutable target/basis history and replay. No SQL migration or operator runtime restart occurred. Selected-card body Compose/Review/Apply merged in PR #913 at `f971931ebade4bc7e4550b6fc2f659276afb30d1`, reviewed head `110440433e6d350a0508fd99f554974f09ad3a36`, under the now-SETTLED [handoff](../Plans/HANDOFF-DEMO-plan-card-edit-target.md). Exact body/range binding, parity, explicit draft-only Apply, Save/fresh reopen, stale/same-card correlation refusal and typed nullable action receipts were verified at their owning boundaries. Migration 0015 was tested only in isolated databases; the operator runtime is not yet refreshed/migrated for this capability. Graph-backed World conversation is the active capability recorded below. Source opening and source-document claims are not prerequisites for its first bounded Ask slice.

**Historical Graph-first checkpoint (2026-10-04; superseded 2026-10-05):** Buddy main at that checkpoint was `e671784dc53e698a33a5125f08d76953faa34a19`, including merged #919 recovery and #920 handoff settlement. The operator prioritized Graph integration in the canonical shared World conversation ahead of Plan-to-Run, multimedia, and further presentation expansion. PRIME had dispatched APP-STATE's immutable Graph receipt/replay slice and SERVER's managed-binding/context integration, including the minimal traversal/budget prerequisite for the then-current Hermes adapter. At that point, no contract PR or owning-boundary result was claimed and the DEMO consumer remained BLOCKED. PRIME later accepted the stable SERVER wire contract and activated the bounded synthetic consumer recorded in the active entry above. APP-STATE/SERVER still own producer implementation and integrated acceptance. Reuse the existing Agent Harness integration with the current Hermes Graph adapter and MIND read contract; do not build another retriever, ingestion pipeline, Graph store, or prototype-based predecessor. Source opening and governed Graph writes are separate future slices.

PR #917 remains prototype evidence, not a production prerequisite or code predecessor; PRIME withdrew its overlapping production reservation for the active DEMO consumer. #887 remains prototype evidence. The 2026-10-04 DOGFOOD Cards consultation informs later bounded adoption and adds no gate to the Graph slice. PR #914's synthetic desktop/narrow visual hold is independent and does not block Graph. Preserve its evidence without restoring the stale priority wording.

**Current capability priority:** Graph-backed World conversation through Buddy's runtime-neutral Agent Harness integration is the first production capability, ahead of focused-card prepare/run, durable Run state, multimedia and further presentation expansion. The contract covers conversation execution, tools/context, authorization, lifecycle, evidence, and replay. Hermes is the current concrete adapter behind the existing seam. The synthetic DEMO consumer is ACTIVE on deterministic fixtures against the accepted wire contract. It proves request, response/history, citations and recovery presentation only; parent-brokered traversal through the current Hermes adapter and connected acceptance remain producer-owned evidence. The integrated witness must record admitted evidence and exact Plan/Graph basis in the canonical conversation, then survive navigation and replay without duplicate provider work. Retain compact typed citations and disclose that source content was not opened. Source opening and governed Graph writes remain later slices.

**SERVER candidate contract review (2026-10-05):** read-only inspection of open draft PR #926 at `be94f4ea3e0c06c50b97e91bf58937c22b9b8902` found `validate_completion_against_receipt` still derives answer status and citation admission solely from the initial receipt packet and dispatched-input sets. This rejects valid later parent-brokered traversal evidence absent from the initial packet, contrary to the accepted final producing-envelope contract. The candidate also does not yet implement the documented typed `plan_context_failure` pre-dispatch projection. Treat both as producer-owned compatibility blockers; #926 is not integration acceptance. The DEMO consumer handles the documented typed failure without calling a confirmed pre-dispatch attempt uncertain or reposting it.

**Shared interface adoption target:** use the successful Conks prototypes (including the original Con-ready presentation), A Wild Sheep Chase and campaign Session 29 as joint examples of one prepare/run interface. Preserve focused central cards, lenses, readable semantic content and connections while allowing chronological, location and choice navigation appropriate to each source. Current production Cards is infrastructure, not full prototype adoption. Its observed loss of atomic reference labels and paragraph/list structure is now an ACTIVE bounded [projection-fidelity repair](../Plans/HANDOFF-DEMO-plan-card-projection-fidelity.md), after #913 released the overlapping paths. This independent UI lane can proceed alongside Graph owner work; it does not include focused scene/lens or aesthetic adoption. Durable Run decisions, rolls and notes remain separate contracts.

**Prior DEMO lane checkpoint (2026-09-28):** three bounded predecessors are now merged.
#785 / J4 World-scoped statblock drafts merged at
`f8b923875f9444a1addfb2472a2b8fab35eceb4c`, reviewed code head
`471a967d11e315b24fd5cfe5541f447753fb81f4` (three distinct review-head cycles,
four formal submissions: `5333492877`, `5333610809`, `5341223774`,
`5341878346`; exact-head scoped live acceptance passed). #786 statblock wire and
digest compatibility merged at `9f358bb9ecf4d28338ae4b6b0ef5e2c316700d59`,
reviewed head `51ee5e975d8d419430a2bd943cbc4622d10ac67f` (two distinct review
heads; final scoped consumer contract and focused tests passed; no product,
database, provider, or runtime operation). #787 native World source authority
merged at `f7ce9b99b8e9b73129c6f474989cdb30875a31c8`, reviewed head
`232a42614b1453a815df2dd12f172c0be3c7a155` (two distinct review heads; exact
ordinary Build import/readback/restart witness passed).

#787 admits the saved committed source snapshot to native World source authority;
it does not prove extracted/accepted knowledge, retrieval, J3, or the connected
demo. Buddy #788 then delivered the exact World-owned Plan lifecycle, merged to
main at `eac67508ea34115b102c7c4af8a55e17843a16d9` from reviewed code head
`27bb1a76a113ef85f54c6ac09bbd4d18aa121b41` after five distinct review-head
cycles. Its accepted create/save/reload/recovery and bounded ordinary-browser
evidence remain valid, but it did not prove full shell composition or J1/J2
acceptance. Operator dogfood identified a distinct World Plan composition gap:
the route lacked the shared Plan surface, editing tools and truthful
World/document context. Buddy #789 completed that composition slice and merged
at `ed1bf1ba0531bf9018f2397863825fa20c781bfe` from reviewed code head
`7e4fb73d5a553b58bd1350c9c0ded653ef97b2e0` after one distinct review-head
cycle; its 115 focused Plan tests passed. **That is not visual acceptance.** On
the exact blank World Plan witness at
`http://127.0.0.1:5201/plan?world=pr788-exact-head-witness-b-2026-09-28`, the
operator rejected the editor presentation as awful/default with no perceptible boundary.
Although CSS contains a 3px slate outer frame and 2px parchment editor border,
the nested Tiptap/Markdown presentation still reads as a dark generic panel
around a large blank slab. The operator re-viewed the actual route on
2026-09-29 and again rejected it as awful, boundaryless, and default-styled.
J2 composition code is integrated, but J2 and operator acceptance remain open;
the existence of border declarations or theme tokens is not product acceptance.
Buddy PR [#793](https://github.com/Drakosfire/DungeonMindBuddy/pull/793) was
closed unmerged on 2026-09-29 after its broad shell/identity/visual scope and
unavailable isolated-runtime witness stalled progress. Its source branch remains
preserved at `e122c7073ba8c79dcd428b608da5c8e92bc53abb`; that code is not
on `main` and its visual evidence is not product acceptance. The operator
approved a fresh DEMO steward and three serial, bounded replacements: (1)
prevent outgoing Plan edits while another document loads, (2) publish exact
World Plan saved/local-draft identity, and (3) put title/Save/format/insertion
in AppChrome/EditHost with stale-command fencing. [The steward handoff](../Plans/STEWARDS-HANDOFF-demo.md)
pins their boundaries. The operator appointed fresh DEMO task
`01a0efc8-f3a8-7be2-a556-33eb338338e8`. The first serial implementation
slice merged as Buddy #800 at `393ec5664916ee4eeabe0d0801bc6c8de9820c79`
from reviewed head `d64a9745fdc751360468266323489a18d2579ee1` under
[`HANDOFF-DEMO-plan-document-switch-safety.md`](../Plans/HANDOFF-DEMO-plan-document-switch-safety.md).
PRIME's first exact-head review held a handoff allowlist typo; the corrected
head passed independent focused review and 9/9 mounted Plan page tests. UI
typecheck retains the inherited `ThreatPublicationPanel.tsx:553` JSX namespace
error outside that diff. The delayed-snapshot witness proves the outgoing
editor is inert and its local draft stays intact until another saved Plan loads.
The second serial identity slice merged as Buddy #801 at
`442ee470a33ce4dfa0ba3239c9022ab69220cde9`, reviewed head
`550aa4c0251ffa08477bda2293829725f2d6a8d8`, under
[`HANDOFF-DEMO-world-plan-identity.md`](../Plans/HANDOFF-DEMO-world-plan-identity.md).
PRIME independently reran 18/18 focused mounted Plan page/context tests and
accepted the exact editor/context identity, legacy local-draft migration,
pending/failed selection retirement, promotion and unmount behavior. The
inherited JSX namespace typecheck error remains outside that diff. The third
serial EditHost placement slice merged as Buddy #802 at
`118e680244ab830c24c0f7cfa12f636ac303e034`, independently reviewed at
`1cc18982bb4e1db4bfbc13ab383761c3a8f64bb8`, under
[`HANDOFF-DEMO-world-plan-edithost.md`](../Plans/HANDOFF-DEMO-world-plan-edithost.md),
with 19/19 focused Plan/context/real EditHost tests, including a 390×844
close/reopen path and stale-callback fences. The inherited JSX namespace
typecheck error remains. These bounded repairs do not close J2 or the rejected
appearance gate.
The visual theme remains parked on the preserved #793 branch for a separate
appearance decision. #789 stays historical; J2 and operator acceptance remain open.

**Fresh World J2 rehearsal (2026-09-30):** in World
`demo-of-conks-fresh-journey-20260930-c`, Plan
`bd5a57e0-b091-488c-9d73-bf4a59b0ad97` was created in the fresh World and saved
before source import, then survived reload with its prep prose and conversation
turns. The current shared Plan Agent identifies itself as
`Conversation only`; after a request to add registered Read Aloud and
Decision/Consequence blocks, it returned copy-ready prose and said it could not
trigger Review/Apply. The editor stayed unchanged at saved Plan revision 3.
This reproduces a broken J2 transition on the current World Plan route; the
historical #784 editor bridge does not establish that this route uses it.
ARCHITECTURE's read-only ruling at Buddy `origin/main@9a8e0a7782252e297467cfe63826e40a85fd9b23`
selects reuse of #784's inert proposal and local editor-apply safeguards through
a distinct typed World-only admission path. Keep the existing campaign/session
branch unchanged; never alias World ID as campaign ID or invent a session. A
World proposal may use only the explicitly selected mounted editor draft as
untrusted model context, with exact World/document/base revision and saved-base
digest validation; disclose that draft, selection and instruction go to the
configured model. The server must not add committed Plan Markdown to the prompt.
At this witness checkpoint, ordinary Plan Ask remained metadata-only and graph:none. `WorldOwnedPlanPage`
owns editor/document/dirty/save state; Apply changes only the same mounted draft
and the existing Plan writer remains the Save authority.
RAKE's read-only audit at Buddy `origin/main@9a8e0a7782252e297467cfe63826e40a85fd9b23`,
#805 `f23d43d714b7aba68d940bbcb4cceb027f3c63e1`, and #784
`b6c63a56f784be5cc2fc7de5bb6d167e32520bb8` found that the legacy proposal
bridge checks World/document/revision/body/selection, but its caller checks the
thread before awaiting Apply and only after mutation; switching threads during
that await can still apply the old proposal. A delayed proposal can also show
stale Review after draft/selection changes, and #805's pending-thread fallback
may accept a completion after active scope becomes null/foreign. The active
World-only slice addresses these races with an authoritative live thread/scope
getter immediately before the synchronous editor transaction, stale-review
invalidation, fail-closed null/foreign handling, and late-response cancellation
on unmount. Fixture-backed route, mounted-editor, and focused race regressions
are part of its acceptance evidence.

PR #825 merged this bounded handoff at
`5b7e1e4543c94708e11687feb60093d98d6db93f`. The World-only Apply implementation
completed in PR #828, then its post-merge witness exposed a paragraph-boundary
round-trip guard failure. The bounded helper/mounted-editor repair completed in
PR #829, merged at `a393eee9ae6ca26dfa67f65bfdde2a83037bc485` from reviewed
code head `07cb2b7d2ab5fb655cbf51f16efb96ca40f7415a`. The repair retained the
Markdown round-trip guard and consumes only separator whitespace adjacent to
the split. Its 39/39 focused helper and mounted integration tests passed,
including ordinary Save/reload and stale-target/thread/scope checks. Scoped UI
typecheck retained only the inherited `ThreatPublicationPanel.tsx:553` JSX
namespace error; the UI node config passed. The TypeScript build-info write
limitation under read-only `node_modules/.tmp` was avoided by redirecting the
build-info file to `/tmp`. No provider or product runtime was used by the code
lane.

**Post-fix J2 Apply witness — PASS (2026-10-01):** the original APP-STATE
witness database/container had been auto-removed, so the same synthetic World
`demo-j2-plan-apply-witness-2026-10-01` and Plan
`46e2e8fe-6d91-4552-be31-e69c818e77c6` were reconstituted in a fresh isolated
database and revision chain. The two earlier failed proposals remain separate
browser-local historical evidence. Before each of exactly two new submissions,
the current Plan snapshot and committed revision were checked. A canonical
READ-ALOUD proposal and the plain-prose sentence “A lone watcher keeps vigil
above the marsh.” each passed Review → Apply → ordinary Save → reload on the
same Plan. The final snapshot and committed-revision read agreed at object
revision 6 / content revision 3, body SHA-256
`86e10d0283d650573170b241da529f9b57a560484514d3f9ef673dfe1b6222ef`, with no
divergent working copy. Both calls observed `gpt-5.3-codex`, one provider
attempt, zero transport/conformance retries, and unknown attributable cost.
The first used 422 input / 151 output tokens at 5,818 ms model / 5,825 ms
request; the second used 554 input / 106 output tokens at 4,238 ms model /
4,251 ms request. API/UI processes and the dedicated PostgreSQL container are
stopped; the container and persistent volume remain. During page loads the
background World Graph projection separately returned 503. No graph write or
read-after-write occurred. This witness does not prove managed-World graph
awareness, Session 28/native graph read, recap ingestion, visual acceptance, or
full J2/J1–J6/operator acceptance.

PRIME has since adjudicated the current-policy #812 live Responses gate PASS;
the earlier evidence checkpoint and its separate bootstrap 503 are recorded
below. The bounded J2 Apply slice and its post-fix witness are complete. The
saved-content Plan Ask merged in Buddy PR #833 at
`5a7abdfdf0be13c11b0ce849be433e03a6cb662d`. That slice pins the current
WorkObject revision, committed WorkRevision number, and SHA, then uses Content's
atomic current-World-Plan read before Agent dispatch. It discloses that committed
Plan text and the question go to the configured model, excludes the editor
draft, returns and persists only a compact receipt, and forces
`graph_request.mode=none`. It does not implement native graph retrieval or
citations.

**#833 configured-provider witness — PASS (2026-10-01):** in synthetic World
`demo-saved-plan-ask-witness-2026-10-01`, Plan
`d901c4ad-5d74-4430-ab6e-45f622086b0e`, committed WorkRevision
`65352d85-0871-483f-8e59-e145f7e86791` (revision 1, SHA
`3277078c8b2778896805bc7165aec43942c9da25ae74d97c481839356c56ddad`), one
bounded question used the saved seven-rings-at-dusk fact and excluded an
unsaved nine-rings-at-dawn editor draft. Reload restored the turn and exact
basis tuple. Trace `agent-trace-a66bdf5dd035` recorded OpenAI `gpt-6-luna`, one
model call, no tools or graph, 611 input / 48 output / 13 reasoning tokens and
trace-estimated `$0.0000851`; the provider request ID was not separately
surfaced. This witness closes only the connected saved-Plan Ask gate.

The first game-prep Graph capability was an explicit Buddy managed-World
to existing MIND V2 Graph binding for native `world_id=eldyrwild`. The completed
#836 slice stores a versioned relationship on the managed World; Buddy owns
the relation and its status, and MIND owns native Graph identity and head
existence. The managed World ID, native Graph `world_id`, and VNext Knowledge
`space_id` remain distinct. The paused #826 KnowledgeSpace path creates a
different empty resource and does not satisfy this binding.

PR #835 merged at Buddy main `1ccfe7f2af69684e1d02276f66b875ef336b82a0` from
corrected code head `3a1a12b05be8e00581dce45da2b1b5efa53f123a`. It gates the
listed Agent/query, projection/retrieval, Threat query-hydration, and Threat
identity-candidate Graph read responses behind the configured loopback local
operator. This is a local single-operator capability, not named-user or remote
GM identity. MIND `Admissibility.GM` remains a separate visibility filter.
ThreatDraft, Graph Review, and remaining publication workflow reads are not
claimed secured by #835. The route audit found unguarded Graph Preview
recap-projection, existing-object candidates, latest-preview, extract/promote
review-package and prepare, and Threat publication identity-resolution
responses that return source/evidence or stored candidate data. ThreatDraft
and prepare/commit internal revision reads also remain outside this gate.
These are not all native MIND projections. Classify and gate those routes
before any full-graph query activation.

Plan source-bundle diagnostics PR #839 merged at
`47f9955fd054017a1739dfa8129df65dd61d6bcd` from head
`fccb75c5ce5392681bdbaf14beb15b79be220ecc`. Its two mounted shell regressions
passed 2/2 and the cumulative diff check passed. UI typecheck retained the
inherited `ThreatPublicationPanel.tsx(553,77): TS2503 Cannot find namespace
'JSX'` error outside the change; no server, provider, database or runtime was
used. The handoff is COMPLETE. It clarifies the existing source-bundle
inspection; it does not add native Graph evidence or recap admission.

The Graph-binding handoff
[`HANDOFF-DEMO-existing-graph-binding.md`](../Plans/HANDOFF-DEMO-existing-graph-binding.md)
completed in Buddy PR #836 at `6de8d831ab82308086677fb3038122936ab9a756`, from
reviewed code head `cf226c24da4973f88bbfb904889b45e857ffef31`. It adds the
versioned managed-World/native-Graph relation, local-operator guarded bind and
deactivate operations, read-only identity/head validation, and redacted status
responses. The focused registry/binding/list-route suite passed 35 tests with
11 existing Pydantic warnings; Ruff and the cumulative diff check passed.
The broader TestClient hang was reproduced on base and head plus a trivial
synchronous route. Its disposable PostgreSQL integration was not run because
the fixture override is unset and fallback `127.0.0.1:54329` has no listener.
No live `eldyrwild` bind, Graph write, shared database, server or provider action
occurred. The implementation handoff is COMPLETE and its exclusive lease ended
at merge.

PR #826 remains OPEN at head `4fa28e586783f0e63edb85fa664afa53521367f6` and
paused. It must re-anchor and redesign its KnowledgeSpace binding against the
merged v2 managed-World record, retain distinct Graph and KnowledgeSpace
identities/lifecycles, and return its revised handoff and no-skip PostgreSQL
verification plan to PRIME. No #826 implementation or merge is authorized by
its old branch state.

**Session 29 existing-Graph retrieval — immediate J3 query gate; implementation BLOCKED.**

The bounded contract is pinned in
[HANDOFF-DEMO-session29-elderwyld-graph.md](../Plans/HANDOFF-DEMO-session29-elderwyld-graph.md).
The focused source audit at Buddy code head `672d18b` (Agent query code unchanged
through docs-only #853 at main `e6a4e7d3`) confirms the exact gap: Agent graph
resolution verifies the managed World, then passes its managed ID unchanged to
the MIND direct reader, which expects the bound native Graph ID. The Agent path
does not read #836's active binding, and it forwards the request's revision pin.
The narrow fix belongs at Buddy's trusted Agent-turn boundary: resolve the
active binding, capture its `binding_version` and one current native head, and
carry the managed and native IDs separately.

The query uses MIND V2 `WORLD_CROSS_CAMPAIGN` with `campaign_id=None` and GM
admissibility. Keep `campaign_id=longmont-c2` and `session_id=session-29` in Buddy
narrative focus only; never pass them as native scope, campaign, focus, or a
Graph entity ID. Pin every search, multi-hop, evidence, and source read to one
server-resolved current head. Return native citations, disclose the configured
provider destination and bounded excerpts before dispatch, and show the exact excerpts
sent after the turn.

This is a read-only query of existing `eldyrwild`. It is separate from the
fresh-World source-admission path below and #826's paused KnowledgeSpace
provisioning. Its implementation is serial after the merged #853 production
conversation runtime is implemented and accepted, then the DEMO Plan consumer
cutover is accepted. #853 is design-only; PRIME has not assigned its
implementation owner or lease. No current live read proves `eldyrwild`'s present
head or answerability. The previous native observation at
rev:680c246047d67f9fe0293ee90526f670 is historical only. The J3 live witness
and disposable `R1`-to-`R2`/restart fixture remain required. Do not mutate the real
Graph or create a KnowledgeSpace for either witness.

The user's DEMO minimum still requires one real, surface-aware conversational
Agent entry on every navigable DEMO surface (Index, Plan, Play, Build, Ingest
and Combat). Its reusable backend contract is accepted in PR #790 at exact
design head `3fcc60de6159add04fe9455f5aee0a58816bfece` (PRIME Cycle 4 DESIGN
PASS and ARCHITECTURE focused exact-head PASS). PR #791 implemented the bounded
backend baseline and merged at `6501bfa5143592cec8d7a3f521e3f34d929a5a95`
from reviewed code head `40e7c5f81ab0a6faa53026ea571d2994f77d163c` after two
distinct review-head cycles (`5349662805`, `5350948969`). It proves the
verified-World backend and conversation-only route, not universal UI adoption.
The first UI adoption, Index conversation through shared Agent chrome, merged
as Buddy #803 at `3c9d5f2300d8658b678d25c357760905538dabbd` from reviewed
head `47cac7b1d6ab3a1c9327438d10143b7977bbed93`. It supports verified World or
no owner and no primary work or graph request. The next serial bite was the
saved managed-World Plan Agent conversation under
[`HANDOFF-DEMO-plan-agent-conversation.md`](../Plans/HANDOFF-DEMO-plan-agent-conversation.md).
Its design-only Buddy #804 merged at
`7a4159f447da715a2a5d586b862a7079b7316929` from reviewed head
`e5b0d3e3e84eaae347092937281605e9478f7499` after PRIME and ARCHITECTURE
exact-head PASS. PRIME explicitly activated the bounded implementation.
Buddy #805 merged on 2026-09-30 at
`f23d43d714b7aba68d940bbcb4cceb027f3c63e1` from reviewed head
`0dc016d93f81212f7ee32ea2c137b7cbb2577c5b`. PRIME passed the exact cumulative
diff and its owning-boundary evidence; focused Plan, history and API tests
passed 147/147. The mounted reviewed Plan edit regression passed 1/1. UI
typecheck retains the inherited `ThreatPublicationPanel.tsx:553` JSX namespace
error. At #805 review, the separate legacy `PlanAgentInteractionBar.test.tsx`
suite was 3/8 on base and head because its fixture mocked the retired
`getWorkspaceDocument` call while the selected-World provider used
`getWorkspaceDocumentAny`. RAKE later reproduced five fixture failures on
current main; Buddy #858 merged at `13dbf3a42b0b040a482c0ced1ec0fe5d7b314c37`
from reviewed head `6d1effa5665dd644c343e0d8627b295a18bd23f3` with a one-file
test-only correction, and the mounted suite now passes 9/9. This repaired test
setup only; it changed no product behavior and does not expand #805's released
lease. No provider or live runtime was used.

**Plan transport-mode implementation — merged; live witness pending:** Buddy
#812 (`DEMO: route Hermes Agent turns through Responses mode`) merged at
`3494b8f4561b2ec465af42bf4fb55bac3f42ee3c` from reviewed head
`3e006ca17aa2d3bc5ac2db45e84d33a4e972cb6e`. The bounded change removes
Buddy's explicit Hermes `api_mode` override; the pinned Hermes runtime selects
transport. Its focused Hermes, Agent turn and trace suites passed 74/74, with
no provider, database or product runtime used. PR #819 subsequently made
`gpt-6-luna` the current `hermes_graph_agent` policy model. The original
#812 offline implementation probe used historical `gpt-5.3-codex` inputs; the
current-base exact-pin selector test resolves the current Luna tuple to
`codex_responses`. Neither offline result establishes a live request's mode.

PRIME assigned the isolated database pair
`prime-demo-agent-buddy-pg-20261001` at
`127.0.0.1:55457/dungeonbuddy_application_state` and
`prime-demo-agent-mind-pg-20261001` at `127.0.0.1:55458/dungeonmind`, with
API `127.0.0.1:7866`. The assigned UI port 5178 was blocked by CUA; PRIME
amended the lease to Vite on `127.0.0.1:5202`. The app-state schema reached
`20260930_0009`; DungeonMind reached Alembic head
`0012_vnext_space_provisioning`, with only the migration-owned epoch-0
authority singleton before the synthetic World/Plan was created.

**Initial witness checkpoint — conversation continuity PASS; transport
acceptance HOLD (2026-10-01):** ordinary Plan UI turns on synthetic World
`demo-plan-witness-2026-10-01`, saved Plan
`517a69c3-3c07-4a3d-8960-e2036bfc20b3`, correctly recalled the distinctive
color `ultramarine` on turn two. Both turn routes returned HTTP 200. After a
normal reload, the saved Plan note, revision 3, and both visible turns were
restored. Hermes pointer `hptr-fd69c2574a544527a9ac413c` tied the same agent
thread and Hermes session to that World/Plan. The Plan request path used
`graph_request={"mode":"none"}`; the first ledger snapshot showed zero tool
calls. A separate page-bootstrap graph-projection POST returned 503 due to the
World's absent adoption receipt and was not part of either Plan turn.

The captured first-turn ledger identified `openai-api`, `gpt-6-luna`, base
`https://api.openai.com/v1`, 528 input tokens and 78 output tokens; cost,
provider request IDs, per-turn IDs, and the post-second-turn aggregate ledger
were not captured. Current-base exact-pin offline tests passed 2/2 and resolved
the same model/provider/base to `codex_responses`, but the live trace did not
record the selected mode. No provider error was observed, and no third UI turn
was submitted. Return the exact trace gap to PRIME; do not call the live
transport gate a PASS or claim J1/J2/operator acceptance at that checkpoint.
PRIME's later disposition below resolved that current-policy gate.

PRIME later inspected the saved current-policy live trace and adjudicated the
#812 Responses gate **PASS**. It records `gpt-6-luna`,
`api_mode=codex_responses`, status `ok`, one model call, zero graph tools, 569
input / 52 output / 621 total tokens (43 reasoning), and trace-estimated USD
0.0000829. This estimate is not a billing receipt. Opening the trace made no
Agent request. This later evidence supersedes the initial HOLD for the current
transport gate only. The graph-projection 503 and malformed-looking inventory
document ID remain separate observations; neither is a Plan turn failure, and
this does not claim J2 or operator acceptance.

**Plan Agent continuity witness — PASS (2026-10-01):** the isolated
World Plan witness used the same saved World/Plan and visible conversation on
both sides of a backend/Hermes worker restart, with the Plan remaining at
revision 3 and the committed Plan body absent from persisted Hermes
system/message text. The initial visible follow-up alone was inconclusive.
PRIME later reports that a clean attributable direct recall challenge passed.
The exact request/turn IDs and actual cost were not recorded in this roadmap.
This is separate from C2 and does not close Plan Agent adoption.

Plan's current cited Ask and reviewed document-edit flows remain separate and
unchanged; the generic Agent endpoint has no citation/grounding response
contract, so this Plan conversation requests no graph. The endpoint supplies
saved Plan identity/title/revision metadata, not committed Plan Markdown; it
must not claim document QA, retrieval, quotation, citation or editing.
Content-aware Plan assistance needs a separate owner-reviewed server-side
content-access contract.

**Hermes host test — environment-limited; current-base rerun not claimed:**
RAKE isolated `tests/test_hermes_graph_agent_host.py::test_app_lifespan_shuts_down_global_host`
on Buddy `f34cc2a32b2abc9a4548d0750f911e154c39b54c`. It timed out at the
24-second sandbox cap while `TestClient.__enter__` waited for AnyIO portal
startup; faulthandler showed the portal thread idle in the event-loop selector.
A minimal portal reproduced the wait. The sandbox returned `EPERM` for both
the asyncio self-pipe wakeup and `socketpair()`. Outside the sandbox, the named
test passed 1/1 in 6.45 seconds. Test/module/dependency lock had no relevant
changes since #817. This identifies the test-runner sandbox's AF_UNIX wakeup
restriction as the owner; no Buddy code fix is indicated. The full host suite
has not been shown green, and this is not a fresh test pass on later
`main@bfa741261e715eadb48d873f87fccc1764417da8`. The narrow acceptance is a
minimal portal wakeup and the named test passing under the original timeout in a
runner that permits local AF_UNIX sockets.

**Next Play state — C1 and C2 complete; Agent adoption remains open:**
ARCHITECTURE's 2026-09-30 owner ruling makes `world_id` on the exact
World-owned Runbook revision canonical and derives a Run's World through its
pinned artifact/revision. Never use campaign equality, synthesize a Campaign,
or bind legacy Runs by ID match. The accepted design preserves strict campaign
PlayRun V1 and adds a separate World-only V2 route family. Phase A Buddy #808
merged at `6c6a8ab48d568c2827fca4ce019d701beb473166`; final evidence head
`ed09199b56206a0d3b7a6262380a1352ea567849` passed the five-suite PostgreSQL
owning-boundary witness on 2026-09-30: 53 passed, 11 Pydantic `schema`-field
shadow warnings, 35.18 seconds. This establishes World-owned Runbook revision
identity; it did not create Runs or change PlayRun storage.

Phase B Buddy #809 merged at `a8b0d5c29feaf451b4a7b562302272bc02fdad2a`.
Its nullable-owner migration, exact pin validation, no ownership backfill,
campaign-only V1, and World V2 route family are complete. The PostgreSQL
owning-boundary suite passed 76 tests against PRIME's disposable PostgreSQL 16
tmpfs target. It includes create → advance → discard → V2 reads/progress/
manifest and idempotent replay; new Run creation or rebase from the discarded
source still fails closed. Scoped Ruff, in-memory Python compilation,
cumulative diff checks, and migration upgrade/guarded downgrade evidence passed.
No product server, persistent database, provider, or corpus was used.

PRIME explicitly activated one serial Phase C1 implementation PR from
`main@a8b0d5c29feaf451b4a7b562302272bc02fdad2a`, branch
`codex/demo-world-play-c1`, under
[`HANDOFF-DEMO-world-play-surface-v2.md`](../Plans/HANDOFF-DEMO-world-play-surface-v2.md).
Its exact path list is the exclusive write lease. C1 exposes typed World-owned
Runbook list/create/read/snapshot and TipTap prepare/commit through existing
Content support, then adds specialized read-only World Play context V2 to the
nested `/api/live/query` contract. `dmb_agent_surface_context_request_v1` and
campaign behavior stay unchanged; V2 carries `world_id`, `run_id`, and
`run_revision`, not `campaign_id`, and is admitted only after World V2 detail
and exact pinned Runbook revision/SHA validation. The generic Agent backend
baseline in #791 remains unchanged. PRIME's refreshed open PR inventory (#798,
#781, #760–#761, #763–#765) has no overlap with C1 paths. The previous C1 target
`prime-demo-phase-c1-pg-20260930` at `127.0.0.1:32768` is retired. PRIME designated fresh disposable PostgreSQL 16
tmpfs container `prime-demo-c1-pg-20260930-b` at `127.0.0.1:55454`; PRIME owns
the container and DEMO owns only test-fixture databases. The exact DSN and
ownership are recorded in the C1 handoff. C1 completed in Buddy #810 at
`9aa82aacca3d27849b3fba83dcfc6577097b9b7d`; its seven-suite PostgreSQL witness
passed 242 tests with 11 existing Pydantic shadow warnings in 106.39 seconds.
C2 was activated as a serial successor under
[`HANDOFF-DEMO-world-play-surface-c2.md`](../Plans/HANDOFF-DEMO-world-play-surface-c2.md)
from this main commit and later merged as Buddy #820; its completion and
evidence are recorded below. It consumes C1's World V2 routes and preserves
campaign V1. Generic Agent Run resolution and Play Agent UI remain later work.

The pre-fix seven-suite C1 PostgreSQL invocation collected 242 tests: 240 passed
and two Hermes trace-capture assertions failed in the combined run because the
expected `dmb.agent.turn_trace` records were absent. PRIME traced this to
`src/application_state/migrations/env.py:15` calling
`logging.config.fileConfig` without `disable_existing_loggers=False`, which
disables the trace logger when the migration environment loads. PRIME activated
RAKE DUTY's separate repair lane on
`main@a8b0d5c29feaf451b4a7b562302272bc02fdad2a`, branch
`codex/rake-alembic-preserve-loggers`, under
`Docs/Plans/HANDOFF-RAKE-alembic-preserve-loggers.md`. Its exclusive paths are
that new handoff, `src/application_state/migrations/env.py`, and
`tests/test_application_state_migration_logging.py`; RAKE was authorized to
open one PR to `main`, with PRIME retaining review and merge. Buddy
[PR #811](https://github.com/Drakosfire/DungeonMindBuddy/pull/811) opened at
head `619c11998a7bc17bc0fd740791352e1b275cdf84`, a fast-forward from
`ae1e3aaff746aee8ad630ffa58f7e22d79d3997e`, and later merged at
`2da16c35e1902468451910a44550ff2db20a5bbe`. Its offline regression is at
`tests/test_application_state_migration_logging.py`, outside the nested
PostgreSQL fixture selector. RAKE reports the standalone regression passed 1/1 and the ordered regression plus two C1 Hermes trace tests passed 3/3 in 8.48 seconds. The run used the exact pinned DungeonMind commit `7c69e447f6d4acc963ac09c6fb9cb48cc1c5b9cc` from a temporary source archive to correct a stale installed package; no dependency sync or database access occurred. Eleven existing Pydantic `schema` shadowing warnings were emitted. Scoped Ruff and `git diff --check origin/main...HEAD` passed against current `main@efadc41019e39ca53d19bca85cd7e2a560763049`; the cumulative PR diff contains only RAKE's three leased paths.

PRIME independently reviewed RAKE's exact head and merged Buddy #811 at
`2da16c35e1902468451910a44550ff2db20a5bbe` from reviewed head
`619c11998a7bc17bc0fd740791352e1b275cdf84`. C1 was rebased onto that main; the
implementation code head at the fresh witness was
`561513a8a2ca2099380e4f891ec1012f37e1f21d`. Its seven-suite PostgreSQL witness
passed 242 tests with 11 existing Pydantic `schema`-field shadow warnings in
106.39 seconds against PRIME's disposable target
`prime-demo-c1-pg-20260930-b` at `127.0.0.1:55454`. A post-run query found no
`dungeonbuddy_app_state_test_*` databases. Scoped Ruff, Python `compileall`,
and cumulative/worktree `git diff --check` passed. ARCHITECTURE confirmed no
contract or witness change was needed. The earlier 240-pass, 2-failure run is
historical and superseded by this green witness; focused logger checks remain
separate predecessor evidence, and C1 did not absorb RAKE's repair. Buddy #810 merged at `9aa82aacca3d27849b3fba83dcfc6577097b9b7d` from
reviewed head `da2aa5c5dbe70d7ce49d90ecee2eb2274fae155e`. All C1-specific focused World Runbook, context, ownership, and
pin-boundary tests also passed (29 passed).

**C2 Play UI migration — COMPLETE:** Buddy PR #820 merged at
`bfa741261e715eadb48d873f87fccc1764417da8` from exact reviewed head
`0edeba0e231db57c451e4892bda867cd5e556f46` (behavioral correction
`269973feca4761ddfffab1c7a3843b7392168e5c`). The managed-World Play UI now
uses C1's typed V2 routes while preserving campaign
V1. Its eight focused UI/API suites passed 225/225, including two mounted
same-World A→B→A selection-generation regressions; cumulative diff checks
passed. PRIME's independent mounted Play/Start Run witness passed 32/32. UI
typecheck still reports only the inherited unrelated
`ThreatPublicationPanel.tsx(553,77): Cannot find namespace 'JSX'` diagnostic.
The C2 lease ended at merge. This slice does not establish Play Agent adoption,
J1/J2, connected-demo acceptance, visual acceptance, or operator acceptance.

ARCHITECTURE's 2026-10-01 Play Agent context ruling identifies the exact
server-verified World-owned Run plus expected `run_revision` as the primary
per-turn work locator. Resolve the Run's exact pinned Runbook artifact,
revision/content SHA, current Beat and optional Scene as supporting context;
never substitute the latest Runbook, campaign identity, or a browser pointer.
Without a valid selected Run, Play primary work is absent, and a selected
Runbook alone does not represent an active Run. These are per-turn context
fields, not the durable conversation key, which remains the server-verified
World. No implementation lease for Play Agent adoption is active.

The APP-STATE World-scoped conversation storage/domain service and World-wide
turn receipts are complete: Buddy #822 merged at
`0e49c4d708d3e16c8068384549adb50e863bf64a` and #827 at
`c48abb9fa5857df90af0b086ab78294445fd252a`. #822's assigned service/PostgreSQL
tests passed 14/14; its full Application State suite had three inherited stale
migration-head assertions confirmed on the exact base. #827's retry/PostgreSQL
tests passed 9/9 and conversation service tests passed 10/10.

**Plan World-conversation cutover — implementation merged:** the earlier
BLOCKED design sequence has settled. Runtime adoption #865, PlanAction ledger/
projection #897 and exact Ask projection #898 preceded the consumer #900 and
server proposal-context integration #902. The authoritative bounded contract is
[HANDOFF-DEMO-plan-world-conversation-cutover.md](../Plans/HANDOFF-DEMO-plan-world-conversation-cutover.md).
Saved-World Plan uses server-owned World history; new proposals combine eligible
completed Ask and PlanAction context under exact Plan/basis filtering and a
six-pair total cap. Client-supplied history does not become provider authority.
See the #900/#902 execution checkpoint for reviewed heads, merge revisions and
owning-boundary tests. Those merges do not prove Graph-backed Plan use, full J2,
or operator acceptance. Play consumer adoption remains separate and unleased
under its [conversation handoff](../Plans/HANDOFF-DEMO-play-agent-adoption.md).
#826 retains its independent KnowledgeSpace holds and is not a Play predecessor.

**Build Agent adoption — contract resolved, implementation still blocked:**
ARCHITECTURE's 2026-09-30 ruling establishes the exact admitted workspace
`document_id` plus its committed registry revision as primary work. An editor
session is only a secondary locator and must be server-verified against that
document and revision. Owner scope comes only from the authoritative record;
stale revisions conflict, and campaign/world ID equality never grants scope.
PRIME's 2026-09-30 reconciliation found that the old Build composition
implementation merged in Buddy #507 at
`19752690ee7a573141925aabcf352043da15bbe0`; its named outputs exist on current
main. The old handoff's ACTIVE label is stale, not a live code lease. PRIME
will route that status cleanup separately after RAKE's logger repair review.
Build Agent adoption stays blocked pending a new exact-document/revision
state-sync/admission slice and its own future resolver/request lease. PR #781
covers semantic-action UI only. No Build implementation lease is active, and
no overlapping Build Agent implementation is dispatched.

The next Play-specific owner gate is AGENT-INTERACTION's production shared-
conversation runtime adoption; DEMO surface cutover follows it. Ingest and
Combat Agent adoption remain open after Play. Campaign-owner/campaign-lens stays
fail-closed. The visual rejection remains open and is not waived by Agent work.
J1–J6 remain unaccepted until connected product witnesses pass.

**Current operator direction (2026-09-27, relayed by PRIME):** the knowledge
entry point is the first-customer path:

```text
New World (no campaign or recap)
→ blank, usable World-scoped Plan
→ author/import material
→ prepare + explicit confirmation of knowledge
→ ordinary Agent retrieval/citation of the accepted knowledge
→ restart and reopen
```

Use a **new native Of Conks World identity**, allocated through the existing
World primitive in designated isolated state. The original small one-shot
corpus/files are available, so retaining previous DEMO graph IDs or history is
not a prerequisite. Existing demo state is disposable in product intent, not
authorization to delete it, mutate an immutable revision, bypass source
admission or seed a synthetic graph. Leave old Worlds/artifacts available as
historical evidence. Keep the DB URLs fixed; do not allocate a database per World.
Use a new rehearsal display name so normal name-idempotency does not select the
previous World; the server, not the operator or a script, allocates its identity.

Document creation/editing/save and knowledge prepare/confirm retain their
separate contracts. Import must not become the gate for making a Plan usable,
and document edits must not silently publish knowledge. MIND #83/#85 are merged;
Buddy #787 now admits an exact committed source snapshot to native World source
authority. The remaining J3 gap is the connected governed assertion write and
ordinary read/citation path on that same authority. The active Agent backend
baseline does not publish graph knowledge and does not close J3. Source
admission alone is not J3. No bridge migration, broad framework rewrite, fake
campaign or automatic scope expansion is authorized.

**Historical implementation: J4 / #785**, frozen repair head
`07ec031ab5b62b8dbcd34f51ed4b6eaf0fa25262`, incorporating accepted main
`11d7b5801b51f664e7a6eeafcb2aa2b0f5922b71`. Author exact-head evidence:
169/169 UI tests (zero exclusions), 140/140 backend tests (11 warnings,
23.31 seconds), scoped Ruff and cumulative/local diff checks pass. Typecheck
retains only the independently hashed inherited JSX error. Backend verification
uses the new private lane environment and accepted DungeonMind pin, not the
operator runtime's preserved Python environment. A minimal control reproduced
a sandbox-only TestClient stall; incomplete sandbox jobs are not green evidence.

PRIME's formal **Cycle 1 HOLD** on prior head
`2e33b57737164ac0393975ab31d42a1c91a43d34` is
[review 5333492877](https://github.com/Drakosfire/DungeonMindBuddy/pull/785#pullrequestreview-5333492877).
Independent evidence on that earlier head was 164 UI / 140 backend tests.
The blocker was a delayed old completion overwriting a newer settled same-World
recovery pointer, so reload opened the old candidate. The repair and mounted
two-generation/unmount/remount/reload regression are committed; both reviewer
failures reproduced before the fix. Settlement now requires the exact current
draft/request/source-version attempt, including after settlement. PRIME's formal
**Cycle 2 IMPLEMENTATION PASS / MERGE HOLD** on `07ec031a…` is
[review 5333610809](https://github.com/Drakosfire/DungeonMindBuddy/pull/785#pullrequestreview-5333610809).
The independent reviewer reran 169 UI and 140 backend tests, scoped Ruff and
diff checks. Code acceptance does not waive the live generation witness.

PRIME merged Buddy #780 after independent Cycle 2 PASS (review 5333525840;
98 tests, zero skips) as `11d7b5801b51f664e7a6eeafcb2aa2b0f5922b71`.
Buddy now pins accepted DungeonMind `b83baf82c381b1929c2c7989326d667200ff544c`;
WorldKeeper remains `49a8620f066ce7ef8972a699020c012f50af9158`. This inherited
source-anchor preservation proof does not prove source-body opening, native
admission or J3, and does not expand the asset slice.

The required successful real generation/navigation/reload witness is still false.
The operator reiterated that necessary project OpenAI calls are standing-authorized;
do not ask again for each bounded call. The persistent demo targets `54330`/`54331`
remain untouched. After verifying the handoff's exact two named databases were
absent on its development PostgreSQL at `54329`, the lane created those empty
disposable targets and applied accepted DungeonMind/APP-STATE migrations. No
existing database was overwritten, fixture graph seeded or alternative port used.

On frozen `07ec031a…`, API `8817` and UI `5198`, ordinary Build source creation
allocated World `of-conks-j4-isolated-statblocks`; ordinary Plan creation/save
produced document `ee7ce7b9-e770-4293-ba4c-65428c5308b0`. This prepared checkpoint
does not prove blank Plan creation before source entry or native knowledge genesis.
With explicit freestanding generation (no graph head), the GM flow created draft
`c3d37a51-2dff-4aec-95b1-ee6dd7ea44bb`, source version 1, and dispatched once.
Switching to World B during generation showed an empty workbench. Returning to A
and reloading retained the same original draft/version and unresolved request,
with no candidate or automatic redispatch; no manual-ID repair was used.

Accepted SERVER `eb312545…` / GE `0d01547e…` at `7861` recorded one OpenAI
Responses POST returning HTTP 400. Producer request
`7c7ed81c906c4cc8a3290aa4ea0f78a2` returned `503 / provider_unavailable`,
latency **6,175 ms**. Duplicate log handlers are not two dispatches. Requested
model was `openai/gpt-5.6-luna`; actual successful model, usage, cost and model
processing time are unavailable, not zero. SERVER owns the producer repair;
no blind retry or Buddy provider patch.

SERVER's separate minimal generic diagnostic made one additional provider call:
HTTP 400, `invalid_request_error`, parameter `temperature`, message
`Unsupported parameter: 'temperature' is not supported with this model.`
Request `req_fad6d94dd9c14cdf8a3b21e715548a99`, **1,824 ms**, no response model
or usage. Thus current evidence is **one product dispatch plus one diagnostic**,
not two ingestion runs. The original error body was not retained; the diagnostic
is not claimed to be that original body. The owner observed configured
`temperature=0.7` and routed the GE control incompatibility to ARCHITECTURE.

SERVER PR #34, [`STATBLOCK: omit provider temperature through GenerationEngine`](https://github.com/Drakosfire/DungeonMindServer/pull/34),
passed PRIME Cycle 2 on frozen head
`0ddedbde9836bd05c9812e182c715b9a42199dca`, base
`eb3125455454716d32c6daf53ad005cdc1ec968c`
([review 5334080400](https://github.com/Drakosfire/DungeonMindServer/pull/34#pullrequestreview-5334080400)),
then merged at `1e8a6185…`. Its implementation pins accepted GE #7
`80288d7b467ac3c3586f4e3c964385cefe69f931` and sets `temperature=None`; 11
real-consumer tests and 16 combined seam tests passed with zero skips, and
exact-head red-team CI `36378550004` succeeded. Tests cover card, PCG, map and
image consumers with the actual pinned GE and fake external generation. The PR
and merge changed source; they do not prove a deployed-runtime update.

SERVER's current host read-only check found no visible service or listener on
`7861`; the unauthenticated health request could not connect, the historical
`/tmp` runtime checkout is absent, and sandbox restrictions blocked the `ss`
netlink check. Exact running Server/GenerationEngine refs and collection
isolation therefore remain unverified. No runtime, configuration, state, or
product generation was changed. PRIME accepts a read-only HOLD. Before DEMO
issues a new Ferry Keeper intent, the owning runtime host must establish exact
deployed refs and isolated collections; SERVER coordinates an update to
`1e8a6185…` only if the runtime is stale. Preserve failed request
`d41f849e-334d-4248-814d-8e9ccebf9148`; do not replay it. After runtime
coordination, DEMO still needs one genuinely new Ferry Keeper intent through
ordinary UI. #785 remains on its live gate until that succeeds.

The product's body request key `d41f849e-334d-4248-814d-8e9ccebf9148` is
distinct from the producer log request ID. SERVER verified it is terminal
`failed`, attempt count 1, with no candidate. Same-body/same-key requests replay
that saved failure without provider dispatch; a runtime repair cannot turn it
into success. Buddy currently conservatively shows unresolved recovery. Preserve
that failed identity; do not replace its key, rewrite its journal, or count this
as successful-generation acceptance. After the accepted owner fix, use an
explicit genuinely new threat intent through ordinary controls for the remaining
live witness, retaining the failed attempt and this UX limitation as evidence.

MIND #82 is accepted at `107483f1c4593df8e5599b033fdf2b72a46f3f51`
([Cycle 2 PASS](https://github.com/Drakosfire/DungeonMind/pull/82#pullrequestreview-5333657469)):
empty-native-KnowledgeSpace design/control-plane settlement only, not runtime
implementation, source admission, consumer activation or J3 acceptance.
MIND #83 now implements the public empty native initializer and is **MERGED**
at `031b6650d0a506cf40f0189fc5cfac055ac37308`, accepted head
`decf694fc7304c30e82eae77a30247066c0f954a`
([Cycle 2 PASS](https://github.com/Drakosfire/DungeonMind/pull/83#pullrequestreview-5333897671)).
PRIME independently reports 104 required unit cases plus ten boundary probes,
36 PostgreSQL cases with zero skips, Ruff/Pyright/diff checks and exact-head
core/integration/benchmark CI passing. This accepts public empty native
KnowledgeSpace initialization only: explicit descriptors and identity, one
atomic root/head/event/receipt, exact replay and no synthetic source/evidence.
Buddy's pinned runtime has **not** adopted this merge. Authentic source/evidence
admission, ordinary WorldKeeper/Agent native routing, World-owned Plan and the
connected J3 product witness remain separate, unaccepted gates. MIND reports a
PRIME-approved source/evidence-admission design at `86e8f22d007df99de577cb412301c5a6d4e2d597`; repository verification found it two commits ahead of MIND main and with no associated PR. Record this as a partial design return only: it is not merged implementation, a production entrypoint, or authority to activate Buddy J3.
Buddy PR #779 is now **MERGED** at accepted reviewed head
`2d5ab6ade1d89ec608c941093819ea36404fd18e`, merge
`2ccc96ff2a7d76328578609d5289fd3babcf6442`
([Cycle 2 PASS](https://github.com/Drakosfire/DungeonMindBuddy/pull/779)).
It proves isolated persistent Buddy → WorldKeeper → DungeonMind publication
composition: four PostgreSQL cases with zero skips plus 54 PLAY-1/V6.2 tests.
Its review explicitly leaves browser/Agent retrieval, source admission and
human DEMO acceptance unproven. It does not clear the fresh native Of Conks
source-to-retrieval gate or #785's live generation witness.
Keep the completed #785 scope historical and its lease released. No J3/image
work or full DEMO acceptance is claimed by #779.

Independent J1 preparation probe on the same frozen runtime: managed World B
had no source document and no graph head, yet its local blank editor accepted
authored Markdown, ordinary Save and reload preserved the text. Public API
allocated document `da85ba58-ff9a-4599-8ed5-ea301c076367`, committed revision3.
Its record is **not World-owned**: `world_id=null`,
`campaign_id=pr776-second-synthetic-world`, target session1. Content's current
service/schema requires campaigns; the route explicitly rejects World ID for
Plan. Do not confuse selected-World chrome or durable text with exact ownership.
New World creation also remains coupled to Build source creation.

The bounded successor design is
[World-owned blank Plan](../Plans/HANDOFF-DEMO-world-owned-blank-plan-v1.md):
**BLOCKED** only on its independent PRIME contract review and prospective
lease, plus re-anchor after the predecessor sync. The #785 acceptance/merge
condition is satisfied. It preserves campaign records, uses existing Content authority,
and requires a new World's ordinary blank Plan before any source/campaign/head.
No successor branch, implementation PR or lease is active. Native genesis and
source/WorldKeeper/Agent contracts remain separately owner-gated.

The earlier integrated/rehearsal facts below are preserved evidence, not an
instruction to preserve the legacy Of Conks head as this rehearsal's destination.

**Latest re-anchor (2026-09-27):** #775–#778 are integrated. #776
proves ordinary named-World switching across Build, Plan, Ingest and Play on
one runtime and DB pair. A fresh Of Conks World then received the exact parsed
adventure Markdown through Buddy's local source-import API and produced one
reviewable extraction candidate. #777 made all 48 assertions inspectable,
including 3 nonliteral evidence quotes. #778 enabled explicit literal quote
correction as a distinct immutable child run; its 48 assertions have zero
invalid quotes. The first inert prepare identified three selected relationships
whose endpoint kinds the current DungeonMind predicate contract does not admit;
those were explicitly rejected in review. A governed confirmation through the
normal Buddy product flow published 21 objects and 5 `contains` relationships
as `rev:22ef509825ee1048efc73a1a1aa4a60c`, with no model call, SQL repair or
manual ID assignment. This is a reviewed initial World, not a claim that every
candidate is good or that the extraction profile captures all adventure
content. The source was imported through the local source-import path; the
long-file browser import witness remains outstanding. The older ghost run
remains untouched.

Buddy #782 now supplies exact world-scope consumption by Plan object View,
Agent graph retrieval, grounding, and source-citation requests. PRIME passed
the exact `5762cf335593e9836ec07a40a7ba1632741f7231` head in one formal
review cycle; it merged at `9d31fef89e74a4e8b1f6fd9a5d4f9ed98f283437`.
The saved Of Conks Plan opened Hempholm and a real model Ask answered its
relationship to The Shacks and The Greenfields under the pinned World revision.
The published evidence anchors are still unreadable; Buddy #783 owns that
separate provenance defect. This was a bounded Plan-read PASS, not full J1 or
source-verified grounding. The first J2 rehearsal exposed Agent replies that
stayed in chat instead of editing the selected Plan. Buddy #784 now closes
that bounded transition: reviewed proposals apply to the exact mounted draft,
can be revised in a later turn, and survive ordinary Save/reload as registered
prose, Read Aloud and Decision/Consequence nodes. PRIME accepted exact head
`57c1e632f30e43702e640e301ab26aba14016bf2` in Review Cycle 2
(`5332645721`); merge is `b6c63a56f784be5cc2fc7de5bb6d167e32520bb8`.
The review repaired asynchronous target drift and stale Agent-thread races;
independent evidence is 154 focused UI tests, 10 Python tests and six additional
reviewer race witnesses. The unchanged ThreatPublicationPanel JSX typecheck
failure remains inherited. Real model proposals, ordinary Ask, Apply, Save and
reload were exercised on a separate disposable Plan without overwriting the
operator's draft. This is bounded J2 editing evidence, not the connected J1–J6
or human acceptance. Next: rehearse the repaired Plan transition and J3's
source-to-governed-knowledge doorway under one read/write authority. J3 is not
implemented or activated merely because #784 merged. Buddy #779 previously merged at
`2ccc96ff2a7d76328578609d5289fd3babcf6442`; its isolated PostgreSQL
proof is accepted and its test/report lease is released. The original basic-
presentation design STOP resolved to `RESUME_NON_UI` for the then-observed
functional blocker. The later #789 Plan witness is new contrary human
evidence: the composed editor surface is explicitly rejected visually. This reopens
the presentation acceptance question, but does not itself authorize an
unbounded redesign or application-code change. Record it for bounded steward
re-decomposition; no UI styling work is included in the universal Agent
contract.

Inherited work: PLAY-1 / Buddy #773 merged at
`7fe771e86df2e796484b058aa2e6a8e7c94c9fb9` after two review cycles;
it proves only the in-memory Buddy→WorldKeeper consumer mapping. Buddy #779
now proves isolated persistent composition; browser interaction, source
admission, and next-turn retrieval remain open. Basic presentation
design/dogfood has an existing merged handoff independent of historical F5/F6 UI work.
Foundation evidence and exact snapshot PRs are in the reconciliation; refresh at
activation rather than copying those snapshots into another permanent tracker.

Initial actions at roadmap adoption (historical sequence):

1. Establish one reproducible demo checkout/version combination, corpus and
   isolated durable state. Inventory actual codepaths for ingestion, graph reads,
   graph writes, document persistence, generation and Run persistence.
2. Rehearse the journey, recording the first broken transition and any explicitly
   prepared downstream checkpoints. Do not skip to implementing every proposed lane.
3. Continue the already-available basic-presentation pass on disjoint scope while
   knowledge integration progresses. It remains design/dogfood until its successor
   direction is accepted.
4. Keep the dependency-file order explicit: #773 is merged first; Rules #763
   must re-anchor/review against that main before its own merge; E5Q remains
   blocked behind #763. Route minimal external gaps to their existing owners.

## DEMO-J1 — start a World and prepare

**Acceptance:** Create/select a new World and open a coherent editable blank
World-scoped Plan through ordinary controls before importing a corpus. Author
material or import the bounded parsed Markdown using the normal source/document
flow; preserve exact document/source identity and round-trip. No campaign,
recap, initialized graph or special Of Conks import path is a prerequisite for
the blank Plan. Inspect accepted objects/source relationships when knowledge
has been explicitly confirmed under J3; an editable document alone is not
published knowledge.

**Inherited evidence:** CON-READY CR-U1–U5/U11; source ingress and durable
application-state foundations. Their presence is not proof that arbitrary
adventure Markdown becomes usable preparation without intervention.

**Likely owner:** DEMO Document/Agent plus Knowledge consumer.

**Verify before dispatch:** lossless Markdown/component round-trip; document and
source identity; supported ingestion authority; required source admission and
new-space initialization. If the chosen vNext demo cannot admit this corpus,
delegate the missing contract rather than borrowing an incompatible legacy read path.
The World-container create contract allocates identity/source root, not a graph
head; no source-admission or native-initialization capability is inferred from it.

## DEMO-J2 — collaborate on the surface

**Acceptance:** Across multiple turns, the agent authors and revises prose and
registered Markdown components in the selected Plan. The GM edits too. Save,
reload and route changes preserve the document; concurrent edits do not silently
overwrite each other. The agent retains the agreed planning context.

**Inherited evidence:** MarkdownCanvasSession, AgentRuntime, A5/A6/A7, CR-U12,
AUTHORING-ARTIFACT. Preserve current authoring and command arbitration rather than
building another editor or treating chat text as a completed document edit.

**Likely owner:** DEMO Document/Agent.

**Boundary:** ordinary reversible document edits can be immediate/undoable under
accepted policy; graph publication is a separate governed action. Unknown
component payloads cannot become executable code or silently vanish on save.

## DEMO-J3 — create knowledge and use it next turn

**Acceptance:** Highlight source content, create a node and an edge through the
accepted preparation/confirmation path, inspect their exact durable identities,
then ask the agent a factual question requiring the new node. Normal retrieval
must find it under the same scope/authority; a creation-payload echo is insufficient.
Reopen after restart.

**Current route / activation gate:** MIND #83/#85 and Buddy #787 are merged.
Buddy can admit the exact saved source snapshot to native World source authority;
it does not yet establish extracted assertions, governed assertion publication,
ordinary Agent read/citation, or J3 completion. World-owned blank Plan and
shared-surface composition code are integrated via #788/#789, but Plan visual
acceptance remains rejected. The active Agent backend baseline is specified
by the accepted #790 design and the ACTIVE implementation handoff above. Its
first bounded implementation supports explicit no-graph conversation and
verified World-scoped reads; it does not write graph knowledge or close J3.
Campaign-owner/campaign-lens reads remain fail-closed until Buddy accepts a
campaign→World membership authority; do not infer membership from IDs, artifact
fallbacks, or UI state. After the backend baseline and separately activated
six-surface adoption are reviewed, re-anchor and define the next bounded
capability for governed knowledge creation and ordinary read-after-write. The
old #785 serial-lane blocker is historical and no longer active.

**Inherited evidence:** PLAY-1 #773 and accepted isolated persistent PLAY-2
#779; PLAY-3 is not dispatched; V6.2 adapter; WorldKeeper #7/#8; CR-U4–U7.
These proofs do not close the connected DEMO-J3 journey.

**Likely owner:** DEMO Knowledge consumer; external repairs to MIND/WORLDKEEPER.

**Boundary:** profile pin, evidence admission, source identity and immutable child
read-back remain exact. Do not infer occurrence/mention binding from evidence
support. If text highlighting requires an unsupported binding capability, record
and delegate that gap; do not mask it with UI-only state. No silent V2→V3 migration.

## DEMO-J4 — design and generate a usable asset

**Acceptance:** Discuss/debate a creature across turns, settle a brief, launch
real async generation, keep working and navigate away, then find the completed
statblock. Review it, unlock/edit through its proper working-copy lifecycle,
save it, and reference the selected version from Plan. Generate image candidates,
select one, and reopen the association. The resulting object is available through
the agreed graph/product lookup path.

**Inherited evidence:** SBW foundations, Threat publication/hydration/projection,
REVISE-UX, HERMES-LIVENESS and cross-surface demo requirements. Rehearse existing
behavior before activating a large revision or media program.

**Likely owner:** DEMO Assets/Generation; producer/assets dependencies to SERVER;
generic execution gaps to ARCHITECTURE.

**Boundary:** generated candidate ≠ accepted mechanics ≠ editable working copy.
Editing accepted mechanics yields the governed successor behavior required by the
domain; never modify an immutable revision in place. Keep ongoing Run references
stable unless explicitly adopted. Reuse existing jobs/assets contracts; missing
durability is an explicit gap. Prepared assets may support a presentation only
when labeled prepared and do not count as real-generation acceptance.

## DEMO-J5 — turn preparation into a playable instrument

**Acceptance:** Start a Run from the prepared document/version. Quickly move among
the plan, choices, readable NPC/statblock projections, combat and roll tables.
Return from inspection without losing the current scene or current work. The
same component family can be exercised in the UI workshop and in the real surface
through accepted controllers.

**Inherited evidence:** BF/Playable foundations, exact mechanics projection,
current-moment context, CR-U8/U10/U13/U15/U16 and compact Combat Tracker interaction.

**Likely owner:** DEMO Run/Tools; presentation variants may proceed in isolation
once the view-model/action contract is agreed.

**Boundary:** document content/identity survives Plan→Play. Runtime choices,
initiative and HP belong to the Run. A full PC character-builder, universal rules
evaluator, pagination convergence or spatial workspace is not a prerequisite.

## DEMO-J6 — act, record and resume

**Acceptance:** Record a choice, modify combat HP, enter a physical roll, resolve
the selected table entry and record the outcome. Navigate, reload, restart and
resume the same Run with the same outcomes and selected content. No implicit
reroll when reopening a table.

**Inherited evidence:** APP-STATE durability, current Run identity and relevant
roll/combat code. Table parsing alone does not prove durable recorded results.

**Likely owner:** DEMO Run/Tools.

**Boundary:** preserve table identity/version, submitted roll and resolved result;
define unsupported/out-of-range input visibly. No need for Rules/Jev reasoning
to resolve an explicit table. Do not mutate canonical mechanics to record HP.

## Execution ledger — sole mutable work state

Maintain one concise record per selected slice or delegated blocker here. Do not
prematurely create six implementation PRs from the six journey milestones.

Each record contains:

```text
Journey milestone / concrete user transition
State: unverified | ready | active | blocked | integrated | human-accepted
Observed failure and acceptance witness
Owner task / active handoff / PR / exact accepted version
Write and runtime lease / predecessor / shared-file merge order
Latest integrated evidence and date
Next action or delegated dependency + return contract
```

The initial state of J1–J6 is **unverified as a connected journey**, not an assertion
that their foundations are absent. Historical slices retain their IDs.

### 2026-09-26 — PLAY-1 integration and DEMO preflight

- **DEMO-J3, in-memory consumer boundary:** integrated, not human-accepted.
  Buddy #773 accepted head `5a1736c55988e4b852bbcc2f0ada36d493fa5668`,
  merge `7fe771e86df2e796484b058aa2e6a8e7c94c9fb9`, final review
  `5327172769` (2 cycles). Independent exact-head evidence: 68 focused/V6
  tests, locked sync, Ruff, runtime import and diff check pass; default suite
  retains eight inherited collection errors. No product write route or
  persistent authority changed. No PLAY-2/3 dispatch follows automatically.
- **DEMO-J3, isolated persistent composition:** integrated, not human-accepted.
  Buddy #779 accepted head `2d5ab6ade1d89ec608c941093819ea36404fd18e`,
  merged at `2ccc96ff2a7d76328578609d5289fd3babcf6442` after two formal
  review cycles (Cycle 1 HOLD `5331382343`, Cycle 2 PASS `5331441470`).
  Independent Cycle 2 evidence: four isolated PostgreSQL tests, zero skips;
  54 PLAY-1/V6.2 regressions; scoped Ruff and cumulative diff check pass;
  no disposable database residue. Token
  `CON_READY_PLAY_2_PERSISTENT_VNEXT_POSTGRES_ACCEPTED` records this bounded
  proof only. The ordinary product write route, source admission, next-turn
  retrieval, restartable browser journey and human J3 acceptance remain open.
- **DEMO-J1, isolated Of Conks rehearsal:** **blocked after successful source
  import and extraction, before connected Plan/World use.** At Buddy main
  `29fa749c094ab891d5041e6d5f7e09d54176b7bc`, an isolated local pair
  (`dungeonmind_demo_ofconks_v1` at DungeonMind schema 0010 and
  `dungeonbuddy_application_state_demo_ofconks_v1` at APP-STATE schema 0006)
  was established without touching C1/C2. Ordinary Build Import created the
  managed `of-conks-cons-demo` source and committed document
  `c03fbfcb-79fc-46ae-9124-3f1f7c384c1b` revision 2 from local purchased
  `specimens/01-cleaned-single-column.md`, SHA-256
  `7a379fc9025635b1862b6af7eb5a43dd1ee9387b51cf63ba505491fffe7e68f1`.
  One ordinary Build Extract produced reviewable run
  `07a33f99-7520-4c59-bee2-b38514cb61b8` under the current bounded
  worldbuilding profile, with 33 object candidates and 30 relationship
  candidates; Graph Review displayed the first-World review with 63 changes.
  This is candidate evidence, not a quality PASS or World publication. No
  candidate facts were confirmed. The default profile intentionally omits
  adventure beats/encounters; its suitability for the full demo is unproven.

  The first connected product failure is **Build/imported managed World → Plan**:
  Plan still opens a C2 Session 23 prep, `+ New prep` offers only a C2 session
  number/title, and Ask names Longmont C2. There is no ordinary selection of
  the newly imported World as the Plan destination. Build also disables
  `Find existing object` with `Unknown Build document scope:
  of-conks-cons-demo`, while shared World chrome tries Eldyrwild rather than
  the selected managed World. These are Buddy context/routing gaps, not
  presentation defects or evidence that the extraction failed. At this
  historical checkpoint J1 remained blocked; J2–J6 were not certified by the
  partial rehearsal. The selected-context repair that followed is recorded
  below. Do not spend on another extraction to fix routing.

  The licensed Of Conks package remains local-only and must not be committed.
  Its `specimens/02-prepared.md` matches its local manifest; the local
  `playable/hempholm-prep.md` SHA-256 is
  `c473329dd3a0425559e1d2fae60707a13036e0c473f1dd802e8a96804a2fd86f`,
  not the manifest's `1b350f...` pin. Resolve that input pin before claiming a
  fully reproducible final rehearsal. The new demo DBs and source root are
  disposable local rehearsal state, not production authority.
- **DEMO-J1 selected-context repair:** integrated, not full J1 acceptance.
  Buddy #775 accepted head `ad26172c099f1dd3f8aa983d5f950aa407bd610e`,
  merged at `029004be50057fa7f31d50e0b071633ed36f52f9` after two
  formal review cycles. Historical handoff:
  [`HANDOFF-DEMO-selected-world-context-v1.md`](../Plans/HANDOFF-DEMO-selected-world-context-v1.md).
  The original Of Conks run remains cataloged, but its file-backed components
  and World/source registry are unavailable; it was not replayed or confirmed.
  Under PRIME's pinned evidence amendment, a new explicitly synthetic World
  proved ordinary Build source → Plan create/save/reload, honest missing-head
  behavior, then a user-approved one-node reviewed initialization and exact
  Plan Ask request routing captured without forwarding to a model. This is
  selected-context evidence, not licensed adventure retrieval or DEMO-J1 PASS.
- **DEMO-J1 ordinary World selection:** integrated, not full J1 acceptance.
  Buddy #776 accepted head `59f71fe68bac981c275d7bbeb2e1ceab4764edf7`,
  merged at `4f341eb5ca5edc6c81d5dd956bcea70ff9d9be85` after two
  formal PRIME review cycles. Historical handoff:
  [`HANDOFF-DEMO-world-selection-primitive-v1.md`](../Plans/HANDOFF-DEMO-world-selection-primitive-v1.md),
  adopted from PRIME's pinned OverMind design `936c7c9`. One verified World
  now scopes ordinary Build/Plan/Ingest/Play navigation, inventories and exact
  admission while both DB URLs stay fixed. The accepted same-runtime A/B proof
  covered a Plan→Build stale `documentId`, foreign Run refusal, browser
  back/forward, an unsaved draft return, alternate source import, and native
  graph A-versus-B isolation. World B had no graph head and truthfully reported
  it unavailable. This is synthetic product routing evidence, not recovery of
  the licensed Of Conks artifacts or full DEMO acceptance.
- **DEMO-J1 first World publication:** completed through reviewed Buddy
  extraction correction and the ordinary governed publication flow after #778.
  The selected candidate contained 25 objects and 23 relationships; three
  relationships were rejected after DungeonMind returned an explicit
  endpoint-kind admission error. The reviewed retry published 21 objects and
  five location `contains` relationships at
  `rev:22ef509825ee1048efc73a1a1aa4a60c`. Plan's normal projection reads the
  same head with 21 objects and 5 relationships. This proves a durable World
  head, not broad extraction quality, all source coverage, or J1 completion.
- **DEMO-J1 managed-World Plan read:** Buddy #782 passed one exact-head PRIME
  review cycle and merged at `9d31fef89e74a4e8b1f6fd9a5d4f9ed98f283437`.
  The saved Of Conks Plan opened Hempholm and a real Agent turn retrieved the
  pinned World under explicit world scope with a blank campaign ID. Its answer
  remained `partial_coverage`: the current published source anchors have no
  readable typed locator. Buddy #783 tracks that source-authority gap. Neither
  source-verified grounding nor the editable multi-turn Plan or full J1 journey
  has passed.
- **DEMO-J2 first broken transition (historical, repaired by #784):** two real Plan Agent turns asked for a
  brief Hempholm opening frame to be written into the selected Plan. The first
  reply stayed in chat and offered a later direct write; the second explicitly
  said the Agent cannot edit the document and suggested manual copy/paste.
  The Tiptap editor remained unchanged. At that checkpoint Agent received the selected
  Plan's metadata, not an authorized edit path into its mounted local draft.
  The resulting #784 design preserved the existing editor's dirty-draft/revision-safe
  save semantics and made every Agent edit reviewable before application.
- **DEMO-J2 reviewed Agent-to-Plan editing:** integrated, not full J2 or human
  acceptance. Buddy #784 accepted head
  `57c1e632f30e43702e640e301ab26aba14016bf2`, merged
  `b6c63a56f784be5cc2fc7de5bb6d167e32520bb8`, two formal PRIME
  cycles: Cycle 1 HOLD `5332599377`, Cycle 2 PASS `5332645721`.
  Historical handoff:
  [`HANDOFF-DEMO-plan-agent-reviewed-edit-v1.md`](../Plans/HANDOFF-DEMO-plan-agent-reviewed-edit-v1.md).
  Independent evidence: 154 focused UI tests, 10 Python tests, six additional
  reviewer boundary/race witnesses, scoped Ruff and cumulative diff check.
  No hosted checks were published; typecheck has only the unchanged inherited
  `ThreatPublicationPanel.tsx:553` JSX error. Cycle 1 exposed target/body drift
  during asynchronous hashing and stale Ask/Compose thread replacement; the
  accepted repair rechecks live bindings at mutation time and serializes requests
  with current-thread/scope/generation validation.
  Exact-head browser evidence used disposable Plan
  `37df6fd8-b37a-4806-adc3-e289f2c263fd` in the existing isolated Of Conks
  World. Read Aloud and Decision revisions applied as editable nodes; ordinary
  World Ask remained in the same thread; Save reached Committed and reload
  retained both revisions and eight conversation turns. Two proposal requests
  plus one ordinary Ask request exercised real generation; these HTTP counts
  are not a count of all provider calls in the Ask tool loop. Captured revised
  proposal: observed `gpt-5.3-codex`, 1178 input / 69 output tokens, 3300 ms
  model / 3358 ms request wall. The second proposal's detailed receipt was not
  transcribed before Apply, and provider dollar cost was not returned; no
  aggregate cost/token claim is made. No model-policy change or extraction rerun.
  The Plan edit lease is released. Next connected gate is J3: ordinary source
  highlighting → governed node/edge → later-turn durable retrieval and restart.
  Read-only reconnaissance finds the accepted WorldKeeper consumer has no
  production caller, and #779's native persistent test is not proof that the
  currently reviewed-initialized World uses the same read/write/source seam.
  A read-only contract clarification is routed to existing MIND; no answer,
  migration, source admission or J3 implementation is yet claimed. #783 remains
  independently owned and source-verified grounding remains unproven.
- **DEMO-J2 World-only reviewed Apply:** Buddy #828 merged at
  `dc30a7379b927edd8d9bfb510019f0fccbc3c5c5`, adding the managed-World
  Compose → Review → Apply bridge while leaving ordinary Ask metadata-only.
  The initial post-merge witness used synthetic World
  `demo-j2-plan-apply-witness-2026-10-01` and Plan
  `46e2e8fe-6d91-4552-be31-e69c818e77c6`, revision 3. Two configured-policy
  proposal submissions returned reviewable content: canonical READ-ALOUD and
  plain prose. Both Apply actions initially hit
  `Agent proposal would not round-trip in this Plan location.` No edit was
  applied and the saved body stayed unchanged. The configured model was
  `gpt-5.3-codex`; exact receipts for those failed attempts were not captured.
  The proposals targeted a collapsed caret after the first sentence; block
  insertion split the paragraph, and Markdown import normalized separator
  whitespace at the new edge.

  The bounded repair in PR #829 merged at
  `a393eee9ae6ca26dfa67f65bfdde2a83037bc485` from reviewed code head
  `07cb2b7d2ab5fb655cbf51f16efb96ca40f7415a`. It consumes only whitespace
  adjacent to the paragraph split and preserves the round-trip guard. The
  focused helper and mounted-editor suites passed 39/39. Under PRIME's
  authorization, exactly two fresh proposals were then reviewed, applied,
  saved through the ordinary routes and verified after reload: one canonical
  READ-ALOUD block and one plain-prose sentence. The final database snapshot
  and committed-revision endpoint agreed at object revision 6 / content
  revision 3, with no divergent working copy. Exact per-call receipts are in
  [`HANDOFF-DEMO-world-plan-apply-roundtrip-v1.md`](../Plans/HANDOFF-DEMO-world-plan-apply-roundtrip-v1.md);
  no attributable provider cost was returned. The two pre-fix failures remain
  historical evidence and were not reapplied. This completes the bounded Apply
  round-trip gate only; broader J2 and operator acceptance remain open.
  Proposal-generation metadata is a separate follow-up, not a blocker for this
  witness. A separate page-bootstrap World Graph projection still returned
  503; no graph write or read-after-write was attempted, and graph readiness
  remains unproven.
- **DEMO-J2 Plan conversation/context integration (#900/#902; 2026-10-03):**
  Buddy #900 merged at `f8712198848598c5ce83248eb66a54d93c1fd044` from reviewed
  head `30f4f36549ece68c173fd577c119a2ab88ceebed`. It moved saved-World Plan
  conversation display, New Conversation and uncertain Ask recovery onto the
  canonical server-owned World history contract. Its focused UI/API tests passed
  124/124; typecheck retained only the inherited
  `ThreatPublicationPanel.tsx:553` JSX namespace error. Buddy #902 merged at
  `3d27a0550cb0ffa74fb7ce9cb301435fcaef1eb2` from reviewed head
  `c5d96dd2ad066fe30e9dcbc90fac7263e8a70ce4`. The server now merges exact-basis
  completed Ask and PlanAction pairs, enforces the total six-pair cap and ignores
  browser-supplied history. PRIME reports 39 proposal tests and 16 owner-projection
  regressions passed; the author run also passed Ruff and cumulative diff checks.
  These are implementation/code witnesses only: no configured-provider call,
  live active-surface Graph turn, citation, reviewed Apply → ordinary Save →
  reload witness, or J1–J6/operator acceptance was performed. Plan still sends
  `graph_request=none`. The prior page-bootstrap Graph projection returned 503,
  and the prior surface witness reported Graph authentication unavailable; these
  are historical observations that require exact recheck before any new lane.
  The next proposed product witness remains unleased: on one selected saved
  managed-World Plan, ask an ordinary question against an already accepted Graph
  fact and preserve exact source/node citation; compose/revise from that evidence,
  Review, Apply to the same draft, Save through the ordinary writer, then reload
  and inspect content revision plus conversation/provenance. It performs no
  Graph write; J3 authoring/publication remains separate. Before activation,
  verify the current read/citation contract and owner, identify a usable accepted
  fact/source, and allocate a fresh isolated World/runtime. The Slice B
  disposable database at port 55461 was released to SERVER and must not be reused.
- **DEMO-J3 post-#784 product checkpoint:** read-only rehearsal on integrated
  `main@c19a6c2bf51ae01337b2ad8a3188d45ad6f0fd64`, same isolated World
  and disposable saved Plan. Unlocking and selecting Stacy in the mounted
  document exposes existing edit/insert/reference controls but no governed
  source-to-node/edge action. No document or graph mutation was performed.
  The existing WorldKeeper consumer has no production caller. Its native
  PostgreSQL proof uses a different repository composition from the ordinary
  reviewed-initialized World read path; compatibility is not established by
  sharing a World label or a “v3” name. WORLDKEEPER's read-only owner ruling
  confirms the accepted native runtime cannot consume this legacy parent:
  `bundle.world_graph` and `KnowledgeRevisionRepository` are distinct durable
  authorities, and native materialization rejects a legacy parent. A repin or
  shape wrapper is not a bridge. Preserving this selected World requires an
  explicitly accepted bridge-genesis, authentic source/evidence translation,
  and ordinary-read authority selection. A fresh isolated native World would
  still need a real product initialization/source-admission path, not fixture
  seeding. That minimum prerequisite is routed to existing MIND for an owner
  ruling/design; at that checkpoint no bridge, external merge or fresh genesis
  was authorized. The first-customer direction above now selects fresh native
  rehearsal, while its initialization/source-admission contract remains gated.
  Separately, WORLDKEEPER confirms Buddy's mandatory-campaign mapper is a
  consumer restriction: a bounded extension can use World-global `scope=()`
  without a fake campaign, but that does not solve parent/evidence/read authority.
  Accepted inspected pins: WorldKeeper
  `49a8620f066ce7ef8972a699020c012f50af9158`, DungeonMind
  `0f709d76fdc53bac9c9258d1751463ae2c76ca71`. No J3 implementation is active.
- **DEMO-J4 movement-control checkpoint (2026-10-02):** draft Buddy PR #869,
  `DEMO: typed movement reference editing`, adds candidate-local movement key,
  kind, distance and qualifier controls plus explicit references in every
  direct movement-effect array from the generated v1 contract (composite,
  passive, phase-transition, attack hit/miss and save success/failure). The
  exact-head ARCHITECTURE review initially held code head
  `7ad826d144b3116dbfc460b01d1073ce26e53ad6` because the attack/save arrays
  were protected; those typed controls and editor/mounted regressions are on
  code head `fa7b27e6cf1682bfbdbffd1e9abc792c845366f3`, which ARCHITECTURE
  reviewed PASS. ARCHITECTURE confirmed that PASS also carries to cumulative PR
  head `9e7647053df6dbf51a842c0b6b914d2f2af18d45`: that later commit changed
  only this roadmap, and the three UI files are byte-identical. The two
  owning Vitest files pass **150/150**; cumulative diff check passes. UI
  typecheck still reports only the inherited `ThreatPublicationPanel.tsx:553`
  `TS2503` JSX namespace error. PRIME allocated a fresh disposable J4 lane at
  `/tmp/j4-dms-buddy-pr869-20261002`. SERVER's isolated DMS/PostgreSQL packet was live at that checkpoint: DMS main `a79a52123c1d72caa87be3eec10b6b9a6da7df22`, PostgreSQL migrated
  through Alembic head `20261002_0012`, and the Firestore emulator health check
  passed at that checkpoint. DMS authenticated readiness returned `ready` with read routes enabled,
  generation disabled, and no readiness errors. No provider call or candidate/
  revision write occurred. The Buddy API and UI were started from PR head
  `2f47b3e6816094367ae53e6a9dd399ce826edb4a` on the reserved lane ports 17861 and
  15202; `syntheticWorld` was registered and the Workbench layout survived save
  and reload in the isolated DB. The surrounding legacy surface still reports
  graph authentication unavailable, so this does not prove graph behavior.
  At the DMS validator boundary, a synthetic `swim` reference with no matching
  local movement mode returned `UNKNOWN_MOVEMENT_REFERENCE`; changing only the
  reference to existing local key `hover` returned no issues. This is validator
  evidence only: a real Buddy UI preview → explicit edit → preview → save → reload
  witness, including the saved revision/readback, remains pending. Generation is
  disabled under PRIME's current runtime direction. The retained candidate body
  is not in checked-in evidence, so a synthetic same-schema witness cannot be
  called its repair or full J4 acceptance. This checkpoint does not close J4.
  Current runtime audit: the old `/tmp/j4-dms-buddy-pr869-20261002` lane and
  UI/API listeners on 15202/17861 are gone. Retained PostgreSQL on 55460 is
  historical state, not a fresh witness target; do not migrate it for this slice.
  A new isolated fixture and explicit runtime allocation are required.
- **DEMO-J4 prepared-checkpoint scope defect:** opening Plan Tools → Statblock
  in Of Conks displays `eldyrwild · longmont-c2` creation defaults. Code
  inspection confirms `LIVE_CONTROL_CREATE_CONTEXT` drives projection
  bootstrap, exact-revision override and freestanding fallback, not just the
  label. The ThreatDraft create contract also requires a nonblank campaign;
  the accepted managed-World Plan context uses world scope / blank nested
  campaign. Generation was not submitted: no threat, model call or foreign
  World write occurred. This is an independent downstream diagnostic, not a
  bypass counted toward connected J3/J4 acceptance. DEMO owns the eventual
  bounded asset-context repair, which must define truthful world-only scope,
  preserve legacy campaign behavior and fail closed on context drift before
  executing. No C2 fallback or invented campaign may make the witness pass.
  PRIME's read-only critique confirmed generation needs no new SERVER argument,
  but found no accepted World-only ThreatDraft contract. The steward's explicit
  versioned scope decision is now durable in
  [`HANDOFF-DEMO-world-scoped-statblock-drafts-v1.md`](../Plans/HANDOFF-DEMO-world-scoped-statblock-drafts-v1.md):
  **ACTIVE after independent design ACCEPT at `de08711183e94065b12b3a4d24765b333a760a1e`**.
  Serial implementation lane: `codex/demo-world-scoped-statblock-drafts`,
  isolated `/tmp/dmb-world-statblocks-fp0eww`, API `8817` / UI `5198`;
  no implementation PR yet at activation. The old #742/#366 handoff ACTIVE
  headers were reconciled to their already-merged historical status to release
  stale preflight overlaps. The 101-test existing draft/generation baseline passes
  outside the sandbox; the sandbox-only in-process route harness stalled and
  was stopped, not reported as passing.
  It proposes one capability: create, generate and reopen a selected-World draft,
  preserving campaign V1 records and rejecting World-only graph publication.
  J3 integration, images and Plan placement remain separate.
  The first implementation checkpoint (historical) opened **draft Buddy #785** at
  `d0afb5c36a34350345a6213d9f7085580cfe6198`, from exact activation/dispatch
  base `d3e0797d64572ef981b9d0f5d03c67ae5261e348`. Its first nano-commit
  implements V2/store lifecycle, unchanged provider-body consumption and the
  owning World-only publication guard; 129 focused backend/authority-port
  regressions, scoped Ruff and diff check pass. Three historical identity-route
  fixtures fail identically on base/head because they reference retired
  `pub_svc.kernel`; not reported green. No new model call ran. API admission,
  mounted UI/attempt recovery, live generation and formal implementation review
  remained outstanding at that checkpoint. The current exact-head code/test
  evidence and unpassed live/review gates are recorded above. At that historical
  checkpoint #785 was not merge-ready; it later merged at
  `f8b923875f9444a1addfb2472a2b8fab35eceb4c` as recorded in the current
  checkpoint above, but merge did not close J4. Its scoped live witness left
  durable candidate `cand_pzlyueamr9m2glmq` / draft
  `3dc55037-6bcb-4ff4-908d-6bff2e3deb2c` not save-ready because the movement
  reference `swim` was unregistered. No mechanics repair, successor save or
  acceptance, image selection/reopen, Plan association, or graph/product
  read-after-write was proven. The UI reported World Graph unavailable; the
  World-only publication guard was proven by tests only. J4 remains open.
- **DEMO-J1 input-pin and full-source browser witness:** the local purchased
  `/home/drakosfire/Downloads/of-conks-cons-v21-gold/specimens/01-cleaned-single-column.md`
  is still 48,778 bytes / 565 lines, SHA-256
  `7a379fc9025635b1862b6af7eb5a43dd1ee9387b51cf63ba505491fffe7e68f1`.
  It is human-normalized parsed Markdown, not proof of production PDF parsing.
  `specimens/02-prepared.md` matches its manufactured-target pin; the actual
  `playable/hempholm-prep.md` remains at the already recorded `c473329d…`
  rather than its stale local manifest pin. Do not use either manufactured
  target as real-generation evidence. Browser Import source currently exposes
  a Markdown paste field, not a file chooser. In the fresh World above, the
  ordinary Build paste flow imported the full pinned source as
  `Of Conks & Cons v2.1 (parsed Markdown)`, saved document
  `18910774-fe8d-4e07-b861-05760ee805f1` at revision 2, and read it back with
  the same SHA-256, 48,453 Markdown characters and 48,778 bytes. This passes
  the full-source paste/readback witness for the agreed normalized Markdown
  input; it does not prove PDF parsing or J3. It also does not prove MIND #96
  provisioning: Build selected the source with `campaign=<world_id>`, and the
  current Buddy adapter requires `campaign_id == world_id` then initializes
  `space_id` as `world_id` through `initialize_empty_knowledge_space`.
- **Shared lease:** #773 released `pyproject.toml`/`uv.lock` by merging first.
  Rules #763 still owns its open PR and must re-anchor against the new main;
  ARCHITECTURE confirmed E5Q is BLOCKED and has no active Buddy dependency-file
  lease. DEMO will not edit Rules or E5Q paths.

## External dependencies and independent programs

DEMO requests only the capability needed for an observed transition. MIND's kernel
program, WORLDKEEPER's lifecycle, ARCHITECTURE's E5 parity, SERVER's production
platform and Rules/Jev work remain separately owned. Shared leases still require
coordination even where acceptance paths are independent.

Do not wait for all of vNext, all provider parity, full hosting, or historical F5/F6 UI work by
default. Equally, do not bypass an actually missing contract. A proposed isolated
demo must prove coherent read/write authority and source admission. The current
operator choice removes legacy bridge migration as a DEMO prerequisite, not
native genesis/source authority. If the fresh-native route requires an absent
contract, return that precise gap to MIND rather than reintroducing migration,
fixture seeding or a parallel authority as an implementation shortcut.

### Fresh-World native source admission — separate later J3 gate remains open

- **State:** MIND #83/#85/#96 and Buddy #787 are merged; no active MIND or
  WorldKeeper prerequisite lease and no fresh-World source-admission
  implementation lease. Buddy #811
  merged at `2da16c35e1902468451910a44550ff2db20a5bbe`; C1 Buddy #810 then
  merged at `9aa82aacca3d27849b3fba83dcfc6577097b9b7d` after its seven-suite
  PostgreSQL owner witness passed 242 tests with 11 existing Pydantic shadow
  warnings in 106.39 seconds. C1 is complete. At this checkpoint C2 was
  ACTIVE under its separate handoff from main after #819 merged at
  `f34cc2a32b2abc9a4548d0750f911e154c39b54c`; C2 later merged as Buddy #820
  (see the current execution checkpoint). This does not close J3 or generic
  Agent Run resolution.
- **Accepted foundation:** MIND #83 provides public empty native initialization
  at `031b6650d0a506cf40f0189fc5cfac055ac37308`; MIND #85 provides native source
  and evidence admission at `7c69e447f6d4acc963ac09c6fb9cb48cc1c5b9cc`.
  MIND #96 adds server-minted native spaces and durable source-admission
  receipts at `619329c2c8586572ffd04558a79b3555c2ca3764`.
- **Buddy product seam:** #787 merged at
  `f7ce9b99b8e9b73129c6f474989cdb30875a31c8` and proves ordinary Build import,
  exact saved-source admission, reload, and fresh-process readback for the
  48,777-byte admitted snapshot. Its current adapter still sets the native
  `space_id` equal to `world_id` via caller-selected
  `initialize_empty_knowledge_space`; the source handoff does not use MIND #96's
  server-minted `create_empty_space`. The fresh-world browser witness above
  proves whole-source paste/readback for the 48,778-byte pin, not #96
  provisioning. Neither proves accepted assertions, graph publication,
  retrieval, or J3.
- **Fresh-world extraction checkpoint (2026-09-30):** normal Build Extract on
  source document `18910774-fe8d-4e07-b861-05760ee805f1` revision 2 created
  reviewable run `1a0d5bc4-ae35-4ef7-99a4-c298c5eddf84` and source artifact
  `artifact:worldbuilding:18910774-fe8d-4e07-b861-05760ee805f1:r2:7a379fc90256`.
  Graph Review found three nonliteral evidence quotes. More fundamentally,
  `apps/live_control_server/services/extract_promote.py` makes this
  `worldbuilding` ExtractionRun inspect-only: `worldbuilding_draft` assertions
  cannot reach World Graph prepare/confirm under the current contract. No
  correction child, confirmation, native graph write, retrieval or restart
  read-after-write was attempted or proven; the World projection also remained
  unavailable (503). This run is downstream inspection on the existing
  caller-selected `space_id=world_id` path, not evidence for MIND #96. Quote
  correction alone cannot clear either boundary.
- **Next fresh-World admission definition:** after the serial #810 gate and current
  J2 transition clear, define the separate Buddy product path from selected source
  spans through MIND #96 provisioning/admission and WorldKeeper prepare/commit
  to ordinary Agent citation and restart read-after-write. Buddy must persist
  the server-minted `world_id` → `space_id` binding, remove the current
  `campaign_id == world_id` admission assumption, and compose the accepted
  admission/change services in its authenticated server path. WorldKeeper's
  `confirmed_by` value is not authentication, so Buddy must derive it from the
  server-side session. Owner audits identify these as Buddy integration duties;
  no external contract gap or J3 implementation lease is currently active.
- **Human witness still required:** New World → blank Plan before import →
  import bounded Of Conks material → select/admit exact source evidence →
  inspect inert preparation → authenticated confirmation → ordinary Agent
  retrieval/citation → restart. No console/SQL/manual-ID repair, forced
  campaign or synthetic source/graph.
- **Exclusions:** deleting previous demo state, importing legacy graph IDs,
  bridge migration, new DB per World, production C1/C2 changes, and expanding
  completed #785.

## Final acceptance

Perform J1→J6 twice from a resettable environment without console/SQL/manual-ID
repair, including real generation, graph read-after-write and restart/resume.
Each journey begins with the first-customer World/blank-Plan path above; fresh
World identities may provide isolated rehearsal state under the existing fixed
DB URLs, without deleting old Worlds or requiring a corpus before Plan is usable.
Use production code and declared exact dependency versions. Record meaningful
limitations and failures. The operator then accepts legibility, coherence and
usefulness; technical test success does not self-award that judgment.

The evidence bundle contains corpus identity, repository/dependency pins, minimal
setup/reset instructions, durable-data location, recovery instructions, recorded
journey results and owner-routed residuals. Prefer existing scripts and reports;
avoid creating a new platform to run one rehearsal.

Label the first accepted outcome **LOCAL DEMO ACCEPTED**. SERVER's
hosted gate additionally proves login, world authorization, remote storage,
logout/login and deployed-service restart. Hosting consumes the same product
journey, rather than redefining or reimplementing it.
