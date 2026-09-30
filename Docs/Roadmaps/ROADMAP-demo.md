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

## Current execution checkpoint

The end-to-end demo remains unaccepted. Several integration and rehearsal steps
are now proven; J1–J6 have not passed as a connected journey.

**Current DEMO lane (2026-09-28):** three bounded predecessors are now merged.
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
the route lacked the shared Plan canvas, editing tools and truthful
World/document context. Buddy #789 completed that composition slice and merged
at `ed1bf1ba0531bf9018f2397863825fa20c781bfe` from reviewed code head
`7e4fb73d5a553b58bd1350c9c0ded653ef97b2e0` after one distinct review-head
cycle; its 115 focused Plan tests passed. **That is not visual acceptance.** On
the exact blank World Plan witness at
`http://127.0.0.1:5201/plan?world=pr788-exact-head-witness-b-2026-09-28`, the
operator rejected the canvas as awful/default with no perceptible boundary.
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
accepted the exact canvas/context identity, legacy local-draft migration,
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
error. The separate legacy `PlanAgentInteractionBar.test.tsx` suite remains
3/8 on both base and head because its fixture mocks the retired
`getWorkspaceDocument` call while the selected-World provider now uses
`getWorkspaceDocumentAny`; no changes to that out-of-slice path were made.
The #805 write lease ended at merge. No provider or live runtime was used.

Plan's current cited Ask and reviewed document-edit flows remain separate and
unchanged; the generic Agent endpoint has no citation/grounding response
contract, so this Plan conversation requests no graph. The endpoint supplies
saved Plan identity/title/revision metadata, not committed Plan Markdown; it
must not claim document QA, retrieval, quotation, citation or editing.
Content-aware Plan assistance needs a separate owner-reviewed server-side
content-access contract.

**Next Play prerequisite — BLOCKED:** before adopting Agent on Play, Buddy needs
an explicit World-owned Runbook/PlayRun owner contract. Current generic Agent
`_work_resolver` supports `kind="plan"` only; PlayRun V1 exposes only
`campaign_id`, current Runbook creation/committed revision is campaign-only,
and World-scoped Play consumers compare that field to the selected World.
ARCHITECTURE's 2026-09-30 owner ruling adopts `world_id` on the exact World-
owned Runbook revision as canonical and derives a Run's World through its
pinned artifact/revision. A typed `world_id` in PlayRun list/detail responses
must be server-derived from that pin; `campaign_id` may be retained only as a
non-authoritative compatibility locator after all readers are migrated. Do not
use campaign equality, synthesize a Campaign, or bind legacy Runs by ID match.
PRIME held design PR #806's initial head
`12821bc55dd7e2e2b2406665cdc59334f7c1021b` for explicit response versioning
and smaller serial scope. The revised BLOCKED
[`HANDOFF-DEMO-world-owned-play-runs.md`](../Plans/HANDOFF-DEMO-world-owned-play-runs.md)
preserves strict campaign V1 behavior and proposes a separate versioned
World-only V2 route family with a typed owner and no Campaign identity. It
sequences three separately activated PRs: A, explicit World-owned Runbook
identity/resolution without Run creation; B, the V2 PlayRun backend with exact
pin/manifest checks and a separately reviewed storage strategy; C, migration of
all audited Play/context consumers and the integrated World Run create/list/
resume witness. Generic Agent Run resolution and Play UI remain a later
successor after C. PRIME passed the final #806 head
`16974eee5f4904f907cdb4d57b170affa1107a15`, merged at
`36deec27e8a963cdb75bdb67609e15547786b446`. The separate
[`HANDOFF-DEMO-world-owned-runbook-foundation.md`](../Plans/HANDOFF-DEMO-world-owned-runbook-foundation.md)
now proposes Phase A's exact Content ownership, migration, resolver, campaign
compatibility witness, path lease, and test command. It remains BLOCKED with no
implementation lease until PRIME explicitly activates it after re-anchoring
main and current PR/lease state. Build, Ingest and Combat Agent adoption
remain open after Play. Campaign-owner/campaign-lens stays fail-closed. The
visual rejection remains open and is not waived by Agent work. J1–J6 remain
unaccepted until connected product witnesses pass.

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
evidence: the composed canvas is explicitly rejected visually. This reopens
the presentation acceptance question, but does not itself authorize an
unbounded redesign or application-code change. Record it for bounded steward
re-decomposition; no UI styling work is included in the universal Agent
contract.

Inherited work: PLAY-1 / Buddy #773 merged at
`7fe771e86df2e796484b058aa2e6a8e7c94c9fb9` after two review cycles;
it proves only the in-memory Buddy→WorldKeeper consumer mapping. Buddy #779
now proves isolated persistent composition; browser interaction, source
admission, and next-turn retrieval remain open. Basic presentation
design/dogfood has an existing merged handoff independent of Canvas F5/F6.
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
shared-canvas composition code are integrated via #788/#789, but Plan visual
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
  The TipTap canvas remained unchanged. At that checkpoint Agent received the selected
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
- **DEMO-J1 input-pin recheck:** the local purchased
  `/home/drakosfire/Downloads/of-conks-cons-v21-gold/specimens/01-cleaned-single-column.md`
  is still 48,778 bytes / 565 lines, SHA-256
  `7a379fc9025635b1862b6af7eb5a43dd1ee9387b51cf63ba505491fffe7e68f1`.
  It is human-normalized parsed Markdown, not proof of production PDF parsing.
  `specimens/02-prepared.md` matches its manufactured-target pin; the actual
  `playable/hempholm-prep.md` remains at the already recorded `c473329d…`
  rather than its stale local manifest pin. Do not use either manufactured
  target as real-generation evidence. Browser Import source currently exposes
  a Markdown paste field, not a file chooser. No new full-source import was
  submitted in this checkpoint, so the long-file browser witness remains open.
- **Shared lease:** #773 released `pyproject.toml`/`uv.lock` by merging first.
  Rules #763 still owns its open PR and must re-anchor against the new main;
  ARCHITECTURE confirmed E5Q is BLOCKED and has no active Buddy dependency-file
  lease. DEMO will not edit Rules or E5Q paths.

## External dependencies and independent programs

DEMO requests only the capability needed for an observed transition. MIND's kernel
program, WORLDKEEPER's lifecycle, ARCHITECTURE's E5 parity, SERVER's production
platform and Rules/Jev work remain separately owned. Shared leases still require
coordination even where acceptance paths are independent.

Do not wait for all of vNext, all provider parity, full hosting, or Canvas F5/F6 by
default. Equally, do not bypass an actually missing contract. A proposed isolated
demo must prove coherent read/write authority and source admission. The current
operator choice removes legacy bridge migration as a DEMO prerequisite, not
native genesis/source authority. If the fresh-native route requires an absent
contract, return that precise gap to MIND rather than reintroducing migration,
fixture seeding or a parallel authority as an implementation shortcut.

### First-customer native source prerequisites — satisfied; J3 remains open

- **State:** MIND #83/#85 and Buddy #787 are merged; no active MIND prerequisite
  lease and no J3 implementation lease.
- **Accepted foundation:** MIND #83 provides public empty native initialization
  at `031b6650d0a506cf40f0189fc5cfac055ac37308`; MIND #85 provides native source
  and evidence admission at `7c69e447f6d4acc963ac09c6fb9cb48cc1c5b9cc`.
- **Buddy product seam:** #787 merged at
  `f7ce9b99b8e9b73129c6f474989cdb30875a31c8` and proves ordinary Build import,
  exact saved-source admission, reload, and fresh-process readback for the
  48,777-byte admitted snapshot. It is source authority only; it does not prove
  extraction, accepted assertions, graph publication, retrieval, or J3.
- **Next J3 definition:** after the World-owned Plan lane, re-anchor and define
  the source-selection → governed assertion preparation/confirmation → ordinary
  Agent read/citation path, including exact identity/scope and durable
  read-after-write. If a concrete MIND/WorldKeeper contract gap appears, route
  that specific gap to its owner; do not assume an external blocker or create a
  parallel authority.
- **Human witness still required:** New World → blank Plan before import →
  author/import bounded Of Conks material → inspect inert preparation →
  explicit confirmation → ordinary Agent retrieval/citation → restart. No
  console/SQL/manual-ID repair, forced campaign or synthetic source/graph.
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
