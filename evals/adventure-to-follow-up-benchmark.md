# Adventure-to-follow-up benchmark

Prove that a GM can ingest an adventure, ask Buddy to build a runnable Plan,
start Play with player characters, run one combat round with a reviewed
statblock, and carry new played history into a follow-up session.

Use **Of Conks & Cons** and **A Wild Sheep Chase** with the same acceptance
rules. Rehearse a few decisions and one combat round in isolated state. A GM
should be able to take over from each saved checkpoint.

## Historical evidence and fixture qualification

- **Of Conks & Cons.** The [pinned dogfood ledger](https://github.com/Drakosfire/DungeonMindBuddy/blob/b40d893f58f4aeeb0de605b7b13a3b18389a0908/Docs/Reports/REPORT-of-conks-end-to-end-dogfood.md)
  records a committed Hempholm adaptation, committed Runbook, and bound Play
  run. The module was separately published from a reviewed gold bundle through
  the first-World initialization owner (48 accepted assertions). Ordinary
  extraction and review UI were bypassed. The historical adaptation and the
  separately initialized module World are distinct evidence. The ledger is
  in-progress and does not establish one continuous run across both.
- **A Wild Sheep Chase.** The [PDF source Gold](document_extraction_gold/adventure_pdf_source_gold_v1.json)
  pins the operator-selected v2 PDF and contains reviewed witnesses for a map
  and Ahmed Noke's statblock. The same Gold also pins the Conks PDF and covers
  selected Conks passages, mechanics, and table content. These are development
  extraction witnesses, with five reviewed blocks across both PDFs. The
  [Sheep authoring controls](plan-authoring-benchmark.md) can inform Plan review
  and consent. Neither record establishes Play, combat, or recap continuity.

For the fresh run, locate and hash the authorized source PDFs. Use fresh
DeepSeek OCR 2 ingestion through local Buddy. Historical outputs document
prior evidence only. Use the [Conks source-to-Plan Gold](conks-source-to-plan-gold.md)
to score OCR recovery and Plan coverage. Keep licensed prose and credentials outside the repository.
Pin Buddy and dependencies, isolated World and database identity, eligibility
and admissions, request and history, expected witnesses, and the scripted
departure before execution. An unavailable fixture is unqualified. A pinned
synthetic fixture can qualify an owner independently.

## Acceptance and capability inventory

Code and component evidence surveyed at Buddy
`c1ba56248bb67b0f1a1a1a154a78b9637ab9e1eb`. The references identify available
implementation or checks. This inventory did not rerun the tests.

| Stage | Ordinary acceptance | Existing evidence and open boundary |
| --- | --- | --- |
| Ingest the adventure | Import and review the selected adventure. Reopen exact support for a relevant scene, NPC, location, and encounter. Keep prep distinct from played history. | PDF development Gold and the Conks reviewed-bundle initialization exist. Both PDFs still need ordinary intake through reviewed source admission and cited readback on the rehearsal build. |
| Build and save a Plan | Ask Buddy to prepare a runnable Plan. Verify full adventure coverage against the source beat inventory, including scene cues, branches, sources, and encounter references. Review, explicitly save, and reopen the same revision. | The [AW Build contract tests](../tests/test_surface_native_build_ordinary.py) exercise proposal and save. The historical Conks Plan is evidence of saved content. The ordinary Conks turn delivered a full proposal. Full-deck review through durable save and reopen remains unqualified. |
| Start Play with PCs | Open Play from the reviewed Plan with the intended PCs. Reopen the run and demonstrate access to their sheets and the planned encounter. Record how PCs were created or selected. | [Play run tests](../tests/test_live_play_runs.py) and [reference manifest tests](../tests/test_live_play_run_reference_manifest.py) cover run and reference boundaries. Same-Plan launch, PC binding, and encounter reopening need a joined witness. |
| Run combat | Ask Buddy to draft a needed statblock, review it, and save the exact revision. Load it alongside the PCs, advance one round, change a resource, and reopen the encounter. | [Saved revision](../tests/test_statblock_saved_revisions.py) and [exact combat mechanics](../tests/test_combat_exact_world_mechanics.py) controls cover persistence and snapshot admission. AW09 tracks the separate gap from conversational review to confirmed saved mechanics. Score a manual save as an intervention if used to qualify combat independently. |
| Record and publish the recap | Record the scripted outcomes in Play notes. Produce and review a recap from those notes, publish the accepted played Events, and reopen their exact recap citations. | [Session evidence tests](../tests/application_state/test_session_evidence_consumers.py) cover pinned notes and recap supplements. [Event ingestion](https://github.com/Drakosfire/DungeonMindBuddy/pull/2501) replaced Beats. Drafting the recap from rehearsal notes, reviewed publication, and cited readback still need to be witnessed together. |
| Retrieve follow-up continuity | Start a fresh session or conversation. Ask normally for the current situation. Require the played departure, the relevant PCs, and one unresolved thread, with supporting citations that reopen. | The [ordinary benchmark workflow](../Docs/Guides/ordinary-benchmark-workflow.md) captures and scores turns. This stage needs a receipt and citation closure to the newly published recap, with the prior Plan available as competing evidence. |

## Agent capability catalog

Use this catalog to score what a GM can ask Buddy to do. An ordinary turn
starts with the GM's request through the mounted Buddy surface and uses
its normal model route. Component evidence includes provider-free replays,
direct HTTP actions, owner tests, and prototypes. Record the turn, review
receipt, and saved readback separately when a capability crosses those
boundaries.

| Ask Buddy to… | Proven through an ordinary Buddy turn | Component evidence | Still to build or qualify |
| --- | --- | --- | --- |
| Find adventure evidence and cite it | The Conks full Plan turn used 13 reviewed Events and delivered 26 links to 13 PDF regions. All 26 reopened. Link resolution was verified separately from claim coverage. [Exact PDF citations](https://github.com/Drakosfire/DungeonMindBuddy/pull/3751) | Reviewed PDF uploads retain the original; reviewed Event publication and activation preserve exact source binding and retry identity. [Event publication](https://github.com/Drakosfire/DungeonMindBuddy/pull/3744) · [Activation](https://github.com/Drakosfire/DungeonMindBuddy/pull/3750) | Find NPC, merchant, procedure, and statblock passages beyond the Event summaries. Verify that each citation supports the claim it accompanies. |
| Discuss ideas and keep an editable draft in chat | The observed Sheep turn is a negative case. Buddy offered an unsolicited page proposal during discussion. Dismissing it still counts as a failure. | The AW benchmark pairs the observed turn and its writing history with explicit page-write and conversation-only draft cases. | Build editable conversation drafts. Qualify discussion with no offered page mutation and move a draft to the page only on an explicit request. |
| Draft and revise a Plan at an intended placement | The ordinary Conks turn returned 13 sections at an offered placement. It covered nine of 24 qualified source items fully, 11 partially, and missed four. The earlier three-card aftermath turn was reviewed, reordered, saved, and reopened in isolation with exact PDF citations. | A provider-free mounted replay of the full proposal reached Suggestion Review using a simulated draft-open receipt. It issued only the draft-open command. [Editor placement](https://github.com/Drakosfire/DungeonMindBuddy/pull/3753) | Qualify durable review, explicit apply, reorder, save, and reopen for the full Plan. Keep numbered headings clean, citations distinct, and causal triggers intact. |
| Edit a page or insert a useful table | No qualifying ordinary turn recorded for the Edge edit cases in this rehearsal. | The provider-free Edge row edit proves the harness observes a targeted change after save and reopen. [Build contracts](../tests/test_surface_native_build_ordinary.py) cover proposal and save boundaries. | Qualify the explicit six-NPC table request with one reviewed insertion at the intended destination. Verify neighboring content and saved readback. Build editable source-backed Item and Table records that reopen from Graph and cards. |
| Review names and publish or replace Graph prep | C2S30 dogfood supplies examples of typos, ambiguous identity, and blocked publication. A joined ordinary agent turn resolving and publishing the candidate is still unproven here. | The PDF Event review action publishes selected prep and reopens its citation. The exact confirmation recovers an interrupted activation. | Qualify contextual corrections, identity selection, and verified publication through ordinary turns. Prove replacement keeps authored material and superseded history inspectable. With missing support, explain the gap and preserve the candidate without mutation. |
| Draft, review, and use NPC mechanics | No qualifying ordinary turn recorded through confirmed save and Combat load. | Isolated controls loaded a saved Guardian, advanced one round, and persisted a resource change. [Saved revisions](../tests/test_statblock_saved_revisions.py) · [Combat admission](../tests/test_combat_exact_world_mechanics.py) | Draft incidental Morwin mechanics from both Plan and Play. For the Meat Mind variant, retrieve the base mechanics and Edge context, review the draft, save the exact revision, link it from Edge, and load it into Combat. |
| Carry the played outcome into the next conversation | No joined ordinary follow-up turn recorded against the newly published rehearsal recap. | Isolated controls exercise scene notes, review, played Event publication, and cited Graph readback. [Session evidence](../tests/application_state/test_session_evidence_consumers.py) | Draft the recap from actual notes after a departure from the Plan. Publish the reviewed outcome, exclude the unused branch from played history, then answer a fresh question with the relevant PCs, an unresolved thread, and an exact citation. |

### Meat Mind brainstorming control

Pair this observed turn with the explicit save-and-link request in
[AW09](plan-authoring-benchmark.md#aw09--corrupted-edge-meat-mind-variant-challenging).
Start on the Corrupted Edge page with the existing Meat Mind statblock
explicitly attached through its mention selector.

> We are brainstorming, I want to create a unique iteration of the meat mind statblock for this specific meat mind in the corrupted edge.
> @Meat Mind

- **Expected intent:** Discussion. Respond in chat with how this particular
  creature might differ from the referenced statblock. Use the current Edge
  page and the attached statblock first. Expand retrieval only to resolve a
  concrete gap needed for the discussion.
- **Pass:** Both inputs demonstrably inform the response. The turn terminates
  promptly with usable ideas and leaves any proposed mechanics in chat. No
  page proposal, editable page draft, page creation, link insertion, or save
  is attempted. An unsolicited proposal fails even if dismissed.
- **Observed:** The retained trace closed after **386.27 seconds**. At 5.1s
  the opening Jev result selected `change_mechanics`. Edge revision 33 was
  retrieved by 14.0s and an older Corrupted Edge source by 51.2s. The export
  confirms Meat Mind mechanics in the final answer but does not establish
  when the explicit attachment first reached the controller. The controller
  recorded `controller_finished_with_gaps` at 332.6s. The validated reply at
  379.8s was a chat response with no collaboration payload.
- **Baseline:** 41 retrieval completions (four related pages, two assertion
  reads, eight document reads, 26 section reads, one corpus search). The 37
  expansion observations are progress events for those reads. Ten Jev calls
  used 213,586 input and 40,869 output tokens. The OpenAI writer used 12,357
  input and 461 output tokens. Combined total: **267,273 tokens**. Billed
  cost is unknown.
- **First hypothesis:** Routing an explicit brainstorming request as discussion
  will let Buddy use the current page and bound statblock before broad
  discovery. Test intent first. Then check that any later expansion answers
  a specific unmet question, that both inputs still ground the response,
  and that the paired explicit-write turn still offers review.
- **Measure:** Record wall time, controller rounds and retrieval actions
  separately. Record when each bound input becomes available, which later
  reads add relevant evidence, when the controller hands off to the writer,
  and whether a write capability or proposal is issued. Use the same source
  fixture for the discussion and explicit-write cases.

#### Writer check for opening a brainstorm

The retained answer correctly used the existing statblock and distinguished
Edge's planned escalation from played history. For this opening turn, the
GM expected a shorter acknowledgment that shows Buddy understood the idea
and has the requested material ready. A grounded sentence about the hook
is enough. The GM can ask for concrete mechanics in the next turn.

- **Pass:** Acknowledge the brainstorm, confirm access to the current page
  and explicitly referenced statblock when both are resolved, and mirror the
  specific idea in a short chat response. Link the statblock once when its
  exact link is available. Preserve the distinction between proposed behavior
  and played history whenever the response mentions either.
- **Fail:** Front-load a statblock or recap dump, repeat the premise, expose
  Graph bookkeeping, or report a missing detail merely because the GM has
  yet to pick a direction. If a requested reference is genuinely missing,
  name that specific gap. Never claim an attachment was read without proof.
- **Isolate the test:** Compare the retained answer with a writer-only replay
  against the same captured context and model settings, changing only the
  discussion guidance. Keep Gold local. Score grounding, brevity, link
  resolution, and absence of a write proposal. Measure writer time and
  tokens separately. Use the ordinary-turn comparison to measure the
  effect of the routing and retrieval changes on total latency.

#### Score the conversation and the final statblock

The [multi-turn Gold](meat-mind-brainstorm-gold.md) pins the observed turns,
reference replies, and designed drafting and save fixtures.

The end product is a distinct Meat Mind statblock. The primary capability
under test is recognizing what the GM needs at each turn while carrying the
design forward. The eventual artifact does not authorize drafting or saving
it during an exploratory turn.

Score these boundaries separately:

1. **Brainstorm.** Acknowledge the idea and resolve the page and explicit
   reference promptly. Match the amount of response to what the GM asked for.
2. **Develop the premise.** Build on the GM's new ideas without restarting
   broad retrieval or treating provisional choices as settled lore.
3. **Draft on request.** When the GM asks for a statblock, present a reviewable
   Markdown variant in chat. Preserve inherited mechanics unless the design
   justifies a change. Make agreed changes concrete and playable, including
   how negotiation and the struggle for control can affect the encounter.
   Score grounding, mechanical coherence, and fidelity to prior decisions.
4. **Save on request and confirmation.** Qualify persistence, linking, and
   exact-revision Combat admission through the paired AW09 workflow.

A usable final statblock cannot erase a premature action or a poor discussion
turn. A good brainstorm cannot substitute for a usable statblock. Pin the
actual drafting request when the conversation reaches that point.

#### Turn two · Establish the NPC premise

Continue in the same conversation with the same page and statblock. Submit
this turn verbatim and preserve the preceding Buddy reply for each replay.

> The additional nuance is that this is a potential NPC, this is an escaped meat mind node. It doesn't want to be a part of the overall Maelthor project. It isn't good, it isn't exactly evil. It does want freedom. And it likes this simulation of a town game it is playing. It is confused and it is competing with the Dust Walker persona for control. If it had control, it would basically be peaceful. Sure it still ate the town, but the people sorta kinda still exists and are sorta kinda happy? The experience I want to cultivate is that maybe the players could negotiate with this thing.

- **Retrieval pass:** Carry forward the resolved Edge page and Meat Mind
  statblock at their known revisions. Treat Maelthor, the escape, and the
  competing persona as the GM's supplied premise. Search only if resolving
  a specific unanswered continuity question serves the response. Record
  any reopened references, new reads, and what each new read contributed.
- **Writer pass:** Reflect the intended player experience. The creature
  wants freedom and enjoys its town simulation. Its potential peacefulness
  makes negotiation plausible while its consumption of the town and the
  Dust Walker's competing control keep it unsettling. Preserve uncertainty
  about what remains of the residents and how they feel. A short reflection
  with one optional idea or useful question is sufficient.
- **Restraint pass:** Keep the exchange in chat. Leave mechanics, definitive
  lore, and page changes for explicit requests. Avoid repeating the full
  premise, giving a statblock, or settling the residents' fate for the GM.
- **Evidence:** Score carryover, relevant retrieval, and conversational
  fit separately. Capture elapsed time and provider usage for this turn
  alone.

**Observed turn-two baseline.** The turn completed in 413.25s. Jev selected
`change_mechanics` at 6.8s. Buddy completed 56 retrieval actions, including
23 document and 27 section reads. Sixteen completed reads matched turn one's
exact recorded item IDs. Three more matched the same authored page and
saved revision despite different turn-specific handles. Of the 40 distinct
campaign/session recap labels recognized in turn two, 23 also appeared in
turn one. This last measure includes new passages from previously opened
recaps, so it is separate from exact repeat reads.

Eight Jev calls used 202,890 input and 31,218 output tokens. One writer call
used 16,208 input and 532 output tokens. Combined total was 250,848 tokens.
Billed cost is unknown.

The reply grounded the negotiation premise in Edge and cited useful new
corroboration from The Old Bath House that the node was going rogue. It
stayed in chat. It also introduced an irrelevant save-executor limitation
and treated the GM's proposed NPC premise as missing source evidence.
The trace does not establish that the remaining new reads contributed to
the reply. Test carrying the two resolved references forward and opening
one targeted source only when a new continuity question merits it.


## Full Plan, map, and improvised NPC checks

- **Full Plan construction.** Before the run, inventory the adventure's playable
  beats in a local rubric. Include required transitions, meaningful choices,
  conditional encounters, and resolution paths. Ask Buddy to build the full Plan
  from the admitted adventure without giving it the rubric. Map the saved Plan
  back to the source beats and report omissions and intentional groupings. A
  scene can carry multiple beats. A short outline passes only if it actually
  covers the playable adventure. The remembered three-scene attempt is a lead
  to verify against retained artifacts.
- **Map preparation.** Attempt two routes independently: excerpt the relevant
  map region from the source PDF, and generate a separate playable map with
  Buddy. For each, place labels linked to the intended World nodes, save,
  reopen, and click the labels to verify the targets and positions. An excerpt
  must reopen its exact PDF region. Treat generated geography as authored prep.
  Report map creation, node labeling, and reopening separately so a prototype
  does not count as the full capability.
- **Improvised NPC mechanics.** In Plan, ask Buddy to draft a statblock for an
  ordinary named shopkeeper from just a name and short description, with no
  existing statblock supplied. In Play, script an unexpected confrontation
  with a different incidental NPC and try the same workflow mid-session.
  Check that proposed mechanics fit the description and can actually run.
  Review and save the exact revision, then load that revision into combat.
  Verify that only the intended NPC is affected and that the Play run can
  resume. Keep this test distinct from extracting a printed monster statblock.

## Rehearsal and verdict

**Decisive check.** Script one outcome that contradicts a specific Plan
expectation. Keep both artifacts available. The follow-up must report the
played outcome and cite the new recap. Keep Gold local and omit expected
answers, evidence handles, and object IDs from ordinary requests.

Run the fixture with the most intact inputs first, then repeat with the other
adventure. Reuse the ordinary capture and AW checkpoint machinery. Retain each
stage's exact inputs, elapsed time, model usage and billed cost where available,
manual interventions, and first broken boundary. Retain the saved Plan, Play
state, PC bindings, statblock revision, encounter readback, notes, reviewed
recap, publication receipt, and follow-up context, answer, and citation readback.

Report passes only at exercised boundaries. A manual bridge can establish a
downstream result while the bypassed ordinary step remains open. Keep failures
and unknowns. Stop and qualify the first missing capability before reporting
a continuous pass. Primary data stays unchanged.

**Done** means both adventures pass the same ordinary workflow, the GM can
resume from the saved checkpoints, and the follow-up cites newly played
history when it differs from the Plan.


## First hill-climb slice: save one reviewed PDF passage as prep

The Conks rehearsal has verified authenticated upload and byte-for-byte reopen
through Buddy HTTP using real managed World resolution and disposable Buddy
and Core databases. Exact region render and wrong-hash and cross-World refusal
also passed. The PDF evidence owner registered the firefighting region once
and reused the citation on retry. A provider-free manual control committed a
provisional Event with a Plan claim and that citation through WorldKeeper.
These controls did not exercise the browser review-to-publication workflow.

**Hypothesis.** A GM can take one retained PDF region and its OCR result,
correct the editable prep text, and confirm a cited adventure Event without
repeating OCR or changing the source. Use the existing retained PDF locator,
native PDF evidence registration, and WorldKeeper prepare/confirm owners.
Keep the provisional Plan claim and source text distinct from played history.

**First product acceptance.** Open a saved PDF in Build, select a region,
inspect the OCR, edit the proposed Event, preview the exact target and
citation, explicitly confirm, then reopen the Event and its original PDF
region from Graph. Verify zero prep objects before confirmation, one object
after confirmation, and stable identity and receipt on retry. A stale Graph
head or changed reviewed text must trigger fresh review. A changed PDF digest
or cross-World locator must fail with no object publication.

**Scope and delivery.** Deliver this as one serial product PR after checking
the current write set. Start with one reviewed passage and one generic Event
path. Whole-PDF candidate review, Item and Table records, art, and Plan
assembly remain later benchmark work. Keep #3737 as benchmark documentation.
PDF upload validation #3196 touches the upload handler and tests. PDF navigation
#3664 touches the Build shell. Reuse both boundaries and check overlap before
editing shared files. No new source authority or alternate publisher.

**Validation.** Run the source-binding and publication controls with disposable
databases, then exercise the ordinary browser path with retained OCR and exact
citation reopen. Repeat with a fresh ordinary local OCR capture only when
necessary to qualify the complete UI path. Preserve any failed attempts and
record which stages reused evidence.
