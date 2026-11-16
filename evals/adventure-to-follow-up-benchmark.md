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

Before dispatch, locate the authorized PDF bytes and verify their hashes,
recover any reusable historical artifact by exact revision, and inventory
availability. Keep licensed prose and credentials outside the repository.
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
| Build and save a Plan | Ask Buddy to prepare a runnable Plan. Verify scene cues, relevant sources, and encounter references. Review, explicitly save, and reopen the same revision. | The [AW Build contract tests](../tests/test_surface_native_build_ordinary.py) exercise proposal and save. The historical Conks Plan is evidence of saved content. Ordinary agent preparation from newly ingested adventure material remains unqualified. |
| Start Play with PCs | Open Play from the reviewed Plan with the intended PCs. Reopen the run and demonstrate access to their sheets and the planned encounter. Record how PCs were created or selected. | [Play run tests](../tests/test_live_play_runs.py) and [reference manifest tests](../tests/test_live_play_run_reference_manifest.py) cover run and reference boundaries. Same-Plan launch, PC binding, and encounter reopening need a joined witness. |
| Run combat | Ask Buddy to draft a needed statblock, review it, and save the exact revision. Load it alongside the PCs, advance one round, change a resource, and reopen the encounter. | [Saved revision](../tests/test_statblock_saved_revisions.py) and [exact combat mechanics](../tests/test_combat_exact_world_mechanics.py) controls cover persistence and snapshot admission. AW09 tracks the separate gap from conversational review to confirmed saved mechanics. Score a manual save as an intervention if used to qualify combat independently. |
| Record and publish the recap | Record the scripted outcomes in Play notes. Produce and review a recap from those notes, publish the accepted played Events, and reopen their exact recap citations. | [Session evidence tests](../tests/application_state/test_session_evidence_consumers.py) cover pinned notes and recap supplements. [Event ingestion](https://github.com/Drakosfire/DungeonMindBuddy/pull/2501) replaced Beats. Drafting the recap from rehearsal notes, reviewed publication, and cited readback still need to be witnessed together. |
| Retrieve follow-up continuity | Start a fresh session or conversation. Ask normally for the current situation. Require the played departure, the relevant PCs, and one unresolved thread, with supporting citations that reopen. | The [ordinary benchmark workflow](../Docs/Guides/ordinary-benchmark-workflow.md) captures and scores turns. This stage needs a receipt and citation closure to the newly published recap, with the prior Plan available as competing evidence. |

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
