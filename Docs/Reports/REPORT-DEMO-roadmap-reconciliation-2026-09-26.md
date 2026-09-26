# DEMO roadmap reconciliation — adopted transfer record

**Surveyed:** 2026-09-26  
**Status:** ADOPTED 2026-09-26; historical transfer evidence  
**Companions:** [steward handoff](../Plans/STEWARDS-HANDOFF-demo.md), [single execution roadmap](../Roadmaps/ROADMAP-demo.md)

## Adopted decision

The existing Codex **PLAY** task was renamed **DEMO**. It retains its history;
no separate task or literal conversation-history merge was needed.
Consolidate Buddy demo delivery order and acceptance into one product roadmap.
Preserve domain architecture, completed evidence, and independently owned shared
capability programs. Transfer execution rows, not every document mentioning a demo.

The canonical authorities are `Docs/Plans/STEWARDS-HANDOFF-demo.md` and
`Docs/Roadmaps/ROADMAP-demo.md`. OverMind retains cross-repository
ownership/dependency references, not a second copy of Buddy's product backlog.
This report is dated reconciliation evidence, not another live tracker.

## Evidence and limits

GitHub main and open PR state were read directly, rather than inferred from the
older local checkouts. Survey anchors:

- DungeonOverMind: `3cb3e16b23c69602347d69639e87244fbaa142be`.
- DungeonMindBuddy: `f1087dcb45c805f5be6146b7b466b5280471f8c2`.
- DungeonMind: `54a419f99057d96e0c4e7620d8bd8ccc6816fb62`.
- WorldKeeper: `a0a70db275cf6c5f3876fe7b4d2a557de12388f5`.
- DungeonMindServer: `afcf04e975130364542d9d7b4736a62154f2df29`.
- GenerationEngine: `19cf68dceb5f4ec7a3d20e17ae6d5c9c8d7aeaa5`.

Source paths below are repository-relative. For Buddy, their pinned tree is
[the surveyed Buddy revision](https://github.com/Drakosfire/DungeonMindBuddy/tree/f1087dcb45c805f5be6146b7b466b5280471f8c2/Docs).
For cross-repository programs, use
[the surveyed OverMind revision](https://github.com/Drakosfire/DungeonOverMind/tree/3cb3e16b23c69602347d69639e87244fbaa142be/Docs).
Re-read heads, reviews, and open leases at activation. No live product rehearsal,
test rerun, or PR review was performed by this survey. Old completion records are
evidence of foundations, not a present end-to-end certification.

## Current work that must survive the transfer

- **Buddy PLAY-1 is open PR #773**, head
  `f9101085abdd552ea19ee88e4b30e7868207b813`. It contains the consumer mapping,
  tests, report, and dependency changes. Inherit its existing branch, handoff,
  review history, and limited in-memory scope. Do not restart it or call it
  browser/persistence acceptance. [PR #773](https://github.com/Drakosfire/DungeonMindBuddy/pull/773).
- **Buddy V6.2 is merged PR #767**, merge
  `f30b4c906bb179b25f00207c40cb38c0debdc264`. Its completion does not switch
  production routing. [PR #767](https://github.com/Drakosfire/DungeonMindBuddy/pull/767).
- **WorldKeeper #7 and #8 are merged.** WK-5 composition and V3 custom-predicate
  compatibility exist. Some WorldKeeper roadmap/anchor headers still say WK-5
  ACTIVE. Delegate status repair to WORLDKEEPER; do not recreate the capability.
- **UI-F0–F4 are recorded merged.** UI-F5 #760 remains an unmerged design handoff
  blocked on Canvas packaging; GitHub reported its stack dirty. UI-F6 #761 remains
  dependent on F5. Neither is a blanket UI implementation lease.
- **Basic presentation work is separately available now.**
  `Docs/Plans/HANDOFF-DEMO-READY-basic-presentation-design-pass-v1.md` is on main.
  It permits design/dogfood and a decision STOP, not application implementation.
  It explicitly does not wait for Canvas F5/F6. Inherit it and its human review
  boundary; do not substitute a new UI-platform project.
- **Agent current-moment context #671 is merged**, merge
  `bd1a7572f4d955a90f5ff5addbc8e49f14b5f3c9`. Its old handoff header still says
  awaiting re-review. Test current behavior before inventing a replacement.
- **Buddy #763 is an actual Rules query implementation**, not merely its original
  handoff shell. It was open/dirty and changes `pyproject.toml` and `uv.lock`,
  as does #773. #764/#765 form its dependent stack. E5Q also waits on the
  dependency-file seam. A named merge order is needed even though these programs
  have different goals. [PR #763](https://github.com/Drakosfire/DungeonMindBuddy/pull/763).
- Governance PRs are open across the ecosystem (OverMind #10, Buddy #772,
  DungeonMind #79, WorldKeeper #9, GenerationEngine #14, Server #33).
  Do not bundle operating-law changes into DEMO reconciliation. Read accepted
  policy again after those merge.
- GenerationEngine #15/#16 and OverMind #11 show live Rules/Jev-related work.
  Excluding that work from DEMO's acceptance path does not cancel its existing
  authorization or reserve its files for DEMO.

## Transfer product sequencing into DEMO

### 1. CON-READY acceptance and source-to-World work

Sources:

- `Docs/Roadmaps/ROADMAP-con-ready.md`.
- `Docs/Plans/STEWARDS-ANCHOR-con-ready.md`.
- `Docs/Plans/PLAN-CON-READY-PLAY-dogfood-thread-v1.md`.

Transfer the remaining source reading, useful semantic index, node/edge
authoring, agent source follow-through, preparation, NPC/statblock use, combat,
navigation, and durability acceptance to DEMO. Map CR-U1–U17 to the new journey
before removing their execution status. Retain their useful acceptance language
as a reference catalog without an independent dispatch sequence.

The old CON-READY anchor should become a short redirect to DEMO. PLAY-1/2/3 keep
their existing identifiers and technical contracts; the old PLAY plan becomes
historical sequencing evidence with a forwarding notice. Production-authority
migration remains separately governed, not silently included in PLAY-2/3.

### 2. Existing DEMO-READY ladder

Source: `Docs/Roadmaps/ROADMAP-demo-ready-c1-c2-to-of-conks.md`.

Transfer residual Stage 4 object usefulness, Stage 5 navigation, Stage 6
cross-surface editing, Stage 7 Agent usefulness, and human demo acceptance.
Keep completed durability and historical corpus work as regression evidence.
Retire this document's independent stage sequence after transfer.

Two sequencing amendments were adopted:

1. Use a bounded parsed Of Conks corpus as the early DEMO rehearsal; C1/C2
   remains a regression/product witness. The old STOP 9 prerequisite for even
   introducing Of Conks is superseded for DEMO by this adoption.
2. Move Stage 8 off-laptop hosting to SERVER's platform program. A local demo
   still needs real durable storage, restart/resume, and recovery; it is not
   hosted-production acceptance. This local-first choice was accepted by the operator.

Do not mark outstanding WOW/human gates passed because their order changes.
Preserve the evidence and obtain a final human product judgment.

### 3. Cross-surface statblock demonstration

Source: `Docs/Roadmaps/ROADMAP-cross-surface-statblock-demo.md`.

Transfer its entire remaining integration sequence to DEMO. Its July PARTIAL /
BLOCKED rows conflict with later completed statblock foundation records. Reconcile
each against implementation before creating work. Preserve Threat/thread/
mechanics identity invariants; retire the old roadmap's execution authority.

Use `DEMO-J1` through `DEMO-J6` for the new journey, avoiding collisions with
this document's historical DEMO-00–09 identifiers.

### 4. Playable and combat delivery

Sources:

- `Docs/Roadmaps/ROADMAP-playable-hoist-dungeonmind-kernel.md`, especially §§5–6.
- `Docs/Roadmaps/ROADMAP-play-world-object-combat-projection.md` and its
  `Docs/Plans/PR-TRACKER-play-world-object-combat-projection.md` companion.

Transfer remaining Plan→Run preparation, current-moment navigation, choices,
contextual/global object access, exact Threat mechanics→combat, required NPC
inspection, and live-use acceptance to DEMO. Retain hoisting criteria as
architecture reference. Kernel promotion remains evidence-driven and MIND-owned.

Do not import the full PC mechanics/state program or every proposed object type
as a prerequisite for one demo. Re-anchor old PWO/PLAY/COMBAT identifiers against
the already implemented Play/APP-STATE foundations. Transfer only unfulfilled
demo capabilities; leave expanded PC/NPC domain work as later domain backlog.

### 5. Threat/statblock product work

Sources:

- `Docs/Roadmaps/ROADMAP-threat-statblock-authoring-projection.md`.
- `Docs/Plans/PR-TRACKER-threat-statblock-authoring-projection.md`.

Transfer AUTHORING-ARTIFACT, demo-required REVISE-UX and HERMES-LIVENESS, the
bounded grounded-context→draft action, needed editor controls, and Plan/Play
integration. The user's requested post-generation review/edit and image choice
also activate product questions previously parked under SBW13/14 and SBW16–18;
they do not activate the entire revision/media/3D program.

Rehearse what already works. DEMO owns selecting/editing/attaching assets in Buddy;
SERVER owns required producer/asset API changes; ARCHITECTURE owns reusable
inference changes. Existing immutable-mechanics and binding contracts remain.
The old domain roadmap retains completed foundations and non-demo expansion;
transferred rows become links, not a second READY queue.

### 6. Agent and Markdown work

Sources: current AgentRuntime/context decisions, A5/A6/A7 handoffs, shared
MarkdownCanvas and surface-composition architecture, and the authoring-artifact
row above.

DEMO owns the needed user-visible chain: multi-turn continuity, current document
and selection context, revision-aware document/component edits, new-node query,
agreed generation brief, and async result discovery. Reuse merged context work.
Do not absorb generic agent research, a new harness, or all context-budget
optimization. Document editing is distinct from publishing graph knowledge.

### 7. Basic UI presentation

Sources: `Docs/Plans/PLAN-ui-presentation-substrate-sidequest-v1.md` §17A and
`HANDOFF-DEMO-READY-basic-presentation-design-pass-v1.md`.

Transfer the demo-facing design/dogfood pass and its accepted bounded product
successors to DEMO. F0–F4 become consumed foundations. F5 Canvas convergence,
F6's convergence-specific closure, spatial workspace, theme packs, and broad
frontend migration remain outside DEMO's mandatory path.

Amend the sidequest's overall-success wording so incomplete F5/F6 cannot block
ordinary demo polish. Keep their own gates intact. A dedicated current Canvas/UI
implementation owner was not established by task history; route a real shared
library defect through ARCHITECTURE for owner confirmation before dispatch.

## Programs that remain independently owned

- **MIND:** DungeonMind generic contracts, admission, identity, retrieval,
  publication, vNext bridge/cutover and performance. DEMO consumes exact accepted
  versions and requests minimal failing-fixture repairs. Coordinate Buddy-side
  vNext adapter ownership explicitly; repository location alone does not cancel
  an existing MIND lease.
- **WORLDKEEPER:** semantic preparation/confirmation/verification contracts and
  lifecycle. DEMO owns Buddy consumer UX and adapters within accepted contracts.
- **ARCHITECTURE:** E5 provider-execution parity and cross-repository ownership
  questions. Keep `ROADMAP-ecosystem-architecture-reset.md` independently active.
  A provider migration is a DEMO dependency only when the rehearsal proves it is.
- **SERVER:** platform refresh phases A–G, auth/tenancy, deployment, storage,
  asset APIs, and production operations. Split Phase F: Buddy statblock/image
  interaction goes to DEMO; server delivery/auth/assets stay here. Phase G reuses
  the DEMO product witness, then adds login, authorization, remote persistence,
  logout/login and service-restart checks. It is not another product backlog.
- **Rules/Jev/RulesEngine work:** keep outside DEMO unless a specific requested
  demo action actually requires it. Typed roll-table lookup is not a RulesEngine
  project. Preserve existing work and coordinate shared paths.
- **APP-STATE:** AS0–AS5 are recorded complete. Keep architecture and recovery
  law; DEMO owns required consumer persistence fixes. Do not launch AS6 merely
  because the demo uses combat or rolls.
- **SURFACE-INTEGRATION:** closed program. Keep closure evidence, not an active
  gate. `PR-TRACKER-campaign-supergraph.md` is frozen; do not revive it.

## Retirement and index disposition

1. The Buddy DEMO handoff and roadmap are the active product authority. The
   old CON-READY, DEMO-READY, cross-surface, Playable, combat and statblock
   execution files have forwarding notices and full dated archive copies.
2. Transferred product rows no longer dispatch from those older files. Current
   indexes point to DEMO. Completed foundation and domain architecture remain.
3. The Campaign Supergraph roadmap's physical retirement remains with existing
   UI #761 settlement ownership. Its stale sequence is not current authority;
   the frozen tracker is not reactivated.
4. The export/source manifest records DEMO as current repository authority.
   User-managed Project Sources are not assumed refreshed by repository changes.
5. OverMind's platform Phase F/G and roadmap pointers are coordinated separately
   without duplicating the Buddy product queue.
6. Existing branches and PRs were not canceled, rebased or repurposed by this
   document transaction. No task history was combined or archived.

## Adopted decisions

- Local durable DEMO first; SERVER hosted acceptance in parallel.
- Of Conks becomes the early bounded rehearsal; retain C1/C2
  regression evidence and final human acceptance, replacing the old admission order.
- DEMO may autonomously fix and polish within its adopted Buddy
  scope. Outside-domain work pauses the dependent step and is delegated; unrelated
  safe DEMO work continues.
- **Standing merge policy:** DEMO may merge its bounded
  in-scope changes only after independent exact-head review and required checks.
  Cross-owner PRs retain their owner's merge authority.
