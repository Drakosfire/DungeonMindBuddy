---
pr_body_template: |
  ## Handoff pointer
  - Workstream: Playable Architecture Graduation / live dogfood D3
  - Flow: PLAY
  - Direction: DESIGN → CODE → REVIEW
  - Handoff: Docs/Plans/HANDOFF-PLAY-c2s27-native-dogfood.md
  - Branch / PR: agent/play-c2s27-native-dogfood / `PLAY: dogfood C2 Session 27 through native Play`

  ## Verification pointer
  - Design/base anchor: `62f7f9e856327247b8677b4c951801e4c58a826c`
  - Predecessor: merged PR #622 / D2 exact admitted Runbook view
  - Base/head: `62f7f9e856327247b8677b4c951801e4c58a826c` / <implementation head>
  - Changed paths: HANDOFF §4 only
  - Product change: none — this is a real-session dogfood transaction over shipped authorities

  The checked-in handoff, cumulative diff, exact Session 27 artifact, setup helper,
  and completed dogfood report are the review contract. The PR description is
  transport metadata only.
---

# HANDOFF — dogfood C2 Session 27 through native Play

**Created:** 2026-08-19  
**Status:** ACTIVE — dispatch exactly one real-session dogfood capability while `main` remains anchored at `62f7f9e856327247b8677b4c951801e4c58a826c`; re-anchor before dispatch if `main` moves.  
**Canonical handoff path:** `Docs/Plans/HANDOFF-PLAY-c2s27-native-dogfood.md`  
**Workstream:** `Playable Architecture Graduation / live dogfood D3`  
**Flow / owner:** `PLAY`  
**Direction:** DESIGN → CODE → REVIEW  
**Implementation base:** `62f7f9e856327247b8677b4c951801e4c58a826c`  
**Suggested branch:** `agent/play-c2s27-native-dogfood`  
**PR title:** `PLAY: dogfood C2 Session 27 through native Play`

> Repository law: `AGENTS.md`.  
> Playable authority: `Docs/Design/ARCHITECTURE-playable-material-and-runtime.md`.  
> Play product design: `Docs/Design/DESIGN-play-surface-projection.md`.  
> D2 predecessor: `Docs/Plans/HANDOFF-PLAY-native-runbook-instructions.md`.  
> Living sequence: `Docs/Roadmaps/ROADMAP-playable-hoist-dungeonmind-kernel.md`.  
> Deferred P3B design: `Docs/Plans/HANDOFF-PLAY-native-graph-object-sheet.md`.

---

## 0. Re-anchor, predecessor sync, and why this PR exists

Current repository truth at design time:

```text
main:
  62f7f9e856327247b8677b4c951801e4c58a826c

D2 / PR #622:
  merged:                  62f7f9e856327247b8677b4c951801e4c58a826c
  implementation/evidence b923117bd7767884053bbe32f25043c7cfe8dcab
  final reviewed head:    c549611a889bc132d385e536ccc675ca695b356c
  formal review cycles:   1

native /play now has:
  explicit existing Run chooser
  explicit Start Run from one chosen committed Runbook
  exact Run + sealed manifest + committed Runbook admission
  Scene / Beat / Choice / Option table deck
  full exact admitted Runbook view beside the Table view
  existing Runtime progress mutations under run_revision CAS
  reload persistence for existing Runtime state

roadmap gate after D2:
  real-session dogfood / re-anchor
  P3B remains designed but NON-DISPATCHABLE
```

### Backward-looking atomic state-authority sync carried by this PR

This dogfood implementation consumes merged D2 / PR #622. Per `AGENTS.md`, it owns the mutable-state sync that is now truthfully knowable.

Update together in this PR:

1. `Docs/Plans/HANDOFF-PLAY-native-runbook-instructions.md`
   - mark D2 / PR #622 **MERGED / HISTORICAL**;
   - record merge SHA `62f7f9e856327247b8677b4c951801e4c58a826c`;
   - record implementation/evidence head `b923117bd7767884053bbe32f25043c7cfe8dcab`;
   - record final reviewed head `c549611a889bc132d385e536ccc675ca695b356c`;
   - record **1 formal review cycle**;
   - name this D3 Session 27 native-Play dogfood transaction as the consuming successor.
2. `Docs/Roadmaps/ROADMAP-playable-hoist-dungeonmind-kernel.md`
   - replace D2 `this PR` wording with merged PR #622 truth;
   - move the mutable integration tip to `62f7f9e...`;
   - mark D2 complete;
   - select this D3 real-session dogfood transaction as current next;
   - add a D3 row only when implementation/dogfood evidence is truthfully known;
   - do **not** pre-mark D3 complete;
   - do **not** choose P3B, P4, a Plan→Runbook bridge, or any other post-dogfood implementation as already next.
3. `Docs/Plans/HANDOFF-PLAY-native-graph-object-sheet.md`
   - record D2 as complete;
   - keep P3B **NON-DISPATCHABLE**;
   - state that this D3 real-session dogfood/report is the current gate;
   - require a post-dogfood re-anchor to explicitly name P3B before P3B may dispatch.

Do **not** edit stable architecture/design authorities merely because #622 merged. Their ownership claims did not change.

### Why the next slice is dogfood rather than another product feature

The shipped lifecycle is now coherent enough to test:

```text
committed Runbook
    ↓
explicit Start Run
    ↓
exact Run + manifest admission
    ↓
Table projection + full Runbook projection
    ↓
Runtime progress
    ↓
reload / continue
```

Repository inspection also exposed real authoring debt:

- the historical `/tiptap-callout-spike` remains North-Gate / Session-23 oriented;
- Runbook write targets are still constrained to the old Mireward eval path family;
- the old descriptor may fall back to a campaign-specific/default Runbook when no exact `documentId` is supplied;
- normal UI does not yet provide a clean general-purpose way to create/promote multiple Scene/Beat identities.

Those are **candidate findings**, not permission to expand this PR.

If we repair all of them before using the product, we lose the dogfood signal that should tell us which one actually matters next.

This PR therefore provides only the smallest deterministic setup needed to make the real Session 27 Runbook eligible for the already-shipped Play lifecycle. It does not repair general Runbook authoring.

---

## §1 Mission and merge-ready invariant

**Mission:** Run the actual Campaign 2 Session 27 Mireward climax from one exact committed Runbook through native `/play`, and capture where the shipped Runbook → Start Run → Table/Runbook → Runtime workflow helps or fails without adding product behavior merely to make the dogfood pass.

**Merge-ready invariant:**

> **One version-controlled C2 Session 27 Runbook artifact is registered and committed through the existing workspace-document + Markdown-writer authority, then deliberately started through the shipped `/play` Start Run UI and admitted as one exact Run UUID bound to that exact Runbook document/revision/SHA and sealed manifest. The dogfood setup helper never creates the Play Run or manifest, never edits registry JSON directly, never silently substitutes another Runbook, and is idempotent on the same exact artifact. During dogfood, Table and Runbook views plus existing Runtime controls are used as shipped; observed friction is recorded in the dogfood report rather than repaired by scope expansion. The PR adds no production product behavior, does not create new Playable kinds or a second authority, and does not make P3B dispatchable. A post-dogfood re-anchor—not this PR's speculative design—chooses the next implementation slice.**

### Pre-dispatch critique

| Question | Answer |
|---|---|
| Can one invariant govern the slice? | **Yes.** The capability is one repeatable real-session dogfood transaction over already-shipped authorities. |
| What is the most dangerous false success? | A helper directly creates/seals a Run or silently opens a default Runbook, proving the helper instead of proving Start Run/native Play. Forbidden. |
| What is the second dangerous false success? | The Session 27 artifact is over-modeled into tracked Choices/pressure types so the product appears more structured than the actual GM workflow requires. Forbidden. |
| What is the third dangerous false success? | Dogfood reveals friction and the PR immediately implements the guessed repair, destroying the evidence boundary. Stop and record it instead. |
| What proves value? | The GM can actually use the exact Session 27 material at the table, mutate real Runtime progress, reload it, and leave a concrete ranked friction report. |
| Stop/split trigger | Any production UI/backend/schema/parser/authoring repair required to complete setup or dogfood. Record the blocker; do not absorb it. |

---

## §2 Authority and current seams — consume, do not redesign

### Existing workspace-document authority

Use existing services only:

```text
apps/live_control_server/services/workspace_document_registry.py
  create_workspace_document(...)
  list_workspace_documents(...)
  get_workspace_document_snapshot(...)

apps/live_control_server/services/tiptap_markdown_write.py
  prepare_tiptap_markdown_write(...)
  commit_tiptap_markdown_write(...)
  TiptapMarkdownWritePrepareRequest
  TiptapMarkdownWriteCommitRequest
```

The current Runbook writer policy already admits:

```text
evals/c2_live_prep/mireward-prep/content/tiptap/<safe-name>.md
```

Use that existing dogfood path family. Do **not** generalize Runbook storage in this PR.

### Existing Play authority

The setup helper ends when the workspace Runbook is active + committed.

Everything after that must use the shipped product:

```text
/play
  → explicit Start a Run
  → choose exact C2S27 Runbook
  → existing P2A Run create/replay
  → existing P2B1 manifest seal/replay
  → /play?run=<uuid>
  → existing P3A admission
  → existing D2 Table / Runbook views
  → existing P2 Runtime mutations
```

The setup helper must **not** import or call Play Run creation, reference-manifest sealing, Run progress mutation, or rebase services.

### Existing Playable identity authority

The artifact uses only the existing v1 family:

```text
Scene
Beat
Choice
Option
```

For Session 27 this dogfood intentionally uses:

```text
1 Scene
5 Beats
0 Choices
0 Options
```

The strategic directions remain ordinary Runbook-level instructions. This preserves the unexpected-player-plan escape hatch rather than pretending the GM already knows the branch taxonomy.

### Runtime/state isolation

Source isolation is not runtime isolation.

This lane owns during dogfood:

- the local workspace-document record whose exact `target_relpath` is the C2S27 artifact;
- the one Run UUID deliberately created by the operator through `/play`;
- that Run's manifest and Runtime progress during the dogfood session.

Do not run another agent's destructive/reset dogfood workflow against the same local workspace/runtime directories while this session is active.

Open PR #578 remains historical/mining evidence. Do not cherry-pick or merge it into this lane. Re-anchor if another active lane begins changing any exact §4 path or the same runtime record.

---

## §3 The exact Session 27 dogfood artifact

Create:

```text
evals/c2_live_prep/mireward-prep/content/tiptap/c2s27-mireward-climax-runbook.md
```

Metadata used by setup:

```text
title:          C2 Session 27 — Mireward Climax
campaign_id:    longmont-c2
kind:           runbook
target_session: 27
target_relpath: evals/c2_live_prep/mireward-prep/content/tiptap/c2s27-mireward-climax-runbook.md
```

### Artifact design rule

This is a **modular climax Runbook**, not a scripted sequence.

The document must distinguish:

1. global GM instructions / known truth — ordinary H1/H2 prose;
2. table-addressable moments — one Scene + five Beats with stable markers;
3. strategic directions / exit ramps / unresolved questions — ordinary H2 material after the playable sequence.

Do not invent new durable kinds for session intent, pressure, NPC cue, exit ramp, open question, or GM decision.

Do not use plain Markdown blockquotes (`>`). Native `/play` P1 admission treats those import warnings as blocking, and Start Run can succeed while READY still fails.

### Required playable identities

Use these exact IDs:

```text
scene:mireward-climax
beat:survive-breach
beat:town-wide-siege
beat:thrin-memory
beat:wall-hinge
beat:aftermath-fork
```

Required source order:

```text
Scene: Mireward Siege Climax
  Beat: Survive the current breach
  Beat: Town-wide siege
  Beat: Thrin's forest-memory awakens
  Beat: Wall hinge crisis
  Beat: Aftermath and strategic fork
```

Do not add Choice/Option markers for north/stay/evacuate/tunnels.

### Required document content

The artifact should be table-usable prose, not a test fixture full of placeholder text. Preserve the following planning truth.

#### Global section — `# C2 Session 27 Prep`

#### `## Session intent`

Capture:

> Increase the tension and bring the Mireward combat/siege to a climax that pushes the party to choose a direction. By the end of Session 27, remaining in the exact current status quo should clearly be impossible.

Also state:

- holding Mireward indefinitely is not viable;
- no NPC chooses the party's final direction;
- the climax must stay modular enough to follow player choices.

#### `## Current play state`

Capture that Session 27 begins **without a reset** in or immediately adjacent to active combat from Session 26:

- Baergrom is physically plugging the tunnel with his shield;
- Bonogo is attacking behind him;
- a surviving swarm is trying to drag a townsman into the blocked tunnel;
- the party is scattered between surface and tunnels;
- wall damage comes from liquefied soil / crawling meat swarms / undermining;
- oil/fire is already in the breach;
- guards are fighting alongside the party.

Explicit constraint:

> Do not introduce a fresh combat before resolving the immediate breach.

#### `## Enemy intent and adaptation`

Capture:

- enemy progression: open-ground assault → burned remains/liquefaction → underground movement → Thrin abduction → civilian/foundation attacks → structural failure from beneath;
- the Meat Mind coordinates Under-Hymn Brood/Lurker behavior;
- its objective is not simply body count: break Mireward's fallback function and obtain Thrin / the forest-memory alive;
- the key table realization is: **killing monsters and saving the wall are no longer identical objectives**;
- after the immediate fight, sustained subterranean hum should reveal that the enemy is widening/undermining rather than merely coming through one tunnel.

Use the line or close paraphrase:

> They are not coming through the tunnel. They are widening it.

#### `## Thrin and the forest-memory`

Capture:

- Thrin's seed is an autonomous living memory rather than ordinary meat corruption;
- it resists incorporation;
- the enemy wants what the forest saw;
- the awakening should be defensive/informational, not a deus-ex-machina solution to the siege.

Useful table line:

> It wants what the forest saw.

#### `## Table constraints`

Capture:

- do not script a fixed five-step railroad;
- beats may compress, overlap, reorder, or be skipped if player action resolves their purpose;
- make infrastructure, civilians/refugees, enemy intent, and wall geometry compete for attention;
- keep the hinge crisis player-solvable;
- Lysandro may die, but his death is not mandatory and must not be a predetermined cutscene;
- after the climax, give the players a genuine breath for healing/triage/information before asking direction;
- do not force a long rest decision in prep unless table events make it obvious.

### Playable Scene

Marker must immediately precede the heading:

```markdown
<!-- dmb-playable-element:v1 kind=scene id=scene:mireward-climax -->
## Mireward Siege Climax
```

Scene body should remind the GM:

- this is one modular siege-climax context, not five mandatory sequential rooms;
- visible success means Mireward survives the immediate crisis but is hurt and no longer a stable indefinite status quo;
- visible failure can move the town to an inner line / evacuation / collapse without automatically ending the campaign.

### Beat 1

```markdown
<!-- dmb-playable-element:v1 kind=beat id=beat:survive-breach -->
### Survive the current breach
```

Include concrete options/pressures without prescribing outcomes:

- save the townsman or let the swarm pull him away;
- kill, drive off, trap, burn, or follow the surviving swarm;
- get Thrin safely back into the defensive line;
- pull Baergrom out before the tunnel becomes a tomb—or decide that holding the point is exactly what is needed;
- investigate what the swarm was doing to the wall;
- collapse, burn, flood, or otherwise interfere with the local tunnel;
- reconnect the scattered party.

The Beat resolves when the immediate breach stops demanding initiative-level attention, not necessarily when every monster is dead.

### Beat 2

```markdown
<!-- dmb-playable-element:v1 kind=beat id=beat:town-wide-siege -->
### Town-wide siege
```

Bring the wider battle into view after the immediate breach:

- subterranean hum is sustained across more than the local tunnel;
- Under-Hymn Brood / Latchlings target foundations, seams, supports, refugee routes, or other structural vulnerabilities;
- present at least two competing pressures so the party cannot solve everything by standing in one square;
- information from guards/refugees should make the enemy's adaptation legible;
- this Beat should make the wall/town a system under attack, not just a monster encounter map.

Do not add a new boss merely because this Beat exists. Under-Hymn Brood vs larger boss remains an open table question unless play strongly calls for escalation.

### Beat 3

```markdown
<!-- dmb-playable-element:v1 kind=beat id=beat:thrin-memory -->
### Thrin's forest-memory awakens
```

Use Thrin to reveal/complicate rather than solve:

- defensive memory response becomes visible;
- it resists the Meat Mind's attempt to absorb/control it;
- it can communicate that the enemy's interest is the forest-memory itself;
- it may reveal useful sensory/history fragments, but should not dictate the party's strategic direction;
- preserve uncertainty about exactly what the carrier knows and why the enemy needs it.

### Beat 4

```markdown
<!-- dmb-playable-element:v1 kind=beat id=beat:wall-hinge -->
### Wall hinge crisis
```

This is the climax hinge:

- structural failure becomes immediate and visible;
- the party must decide what to save: wall section, people, access route, Thrin, infrastructure, or some unexpected combination;
- Lysandro may be placed at genuine risk if table events support it;
- any Lysandro death must emerge from player-visible stakes/action, not hidden inevitability;
- a clever engineering/magic/social plan should be allowed to change the geometry of the crisis;
- the objective is to make status quo impossible, not to predetermine town destruction.

### Beat 5

```markdown
<!-- dmb-playable-element:v1 kind=beat id=beat:aftermath-fork -->
### Aftermath and strategic fork
```

Once the immediate climax resolves:

- give a real breath;
- triage wounded;
- surface refugee status;
- surface wall/tunnel condition;
- surface supply/healing/Hesta information if relevant;
- surface what leadership knows;
- surface any news/absence from Tealeaf, Grobnok, Mirathorn, or Edge only when established/available;
- let the players choose what problem they pursue next.

The Beat is successful if the table has enough information to choose intentionally, even if the choice surprises the prep.

### Runbook-level instructions after playable Beats

These H2 sections intentionally exercise D2's body-boundary behavior. They must remain outside `beat:aftermath-fork` in Table mode while remaining readable in Runbook mode.

#### `## Strategic directions`

List as **ordinary bullets, not Choice/Option markers**:

- north toward Edge / the Fen;
- stay and fortify Mireward;
- evacuate or reorganize the settlement/refugees;
- follow the tunnels / go into the earth;
- unexpected player plan.

For staying, capture likely consequences without making them a forced punishment:

- Edge continues to deteriorate;
- refugee pressure can increase;
- the enemy gains time to adapt;
- Mireward may become better defended if the party invests in it.

#### `## Exit ramps`

Preserve:

- northbound;
- into earth;
- Mireward falls back to an inner line;
- an unexpected player-created solution.

#### `## Information sources`

Use this as a reminder, not a required NPC checklist. Potential sources include:

- Nera;
- Salla;
- Brin;
- Thrin;
- Lysandra / Lysandro as established at the table.

Do not invent new facts merely to fill these names.

#### `## Open questions`

Retain unresolved prep rather than silently deciding it in the artifact:

- How much of the wall actually falls?
- Does Under-Hymn Brood remain the structural threat, or does play justify a larger boss?
- What exactly does Thrin's carrier know?
- Where do the tunnels ultimately originate?
- Is a long rest possible after the climax?
- What healing/potions/Hesta capacity is actually available?
- What is the refugee situation after the breach?
- Does Tealeaf answer?
- What is Grobnok doing / what can he report?
- What is happening in Mirathorn?
- How much time does Edge have?

#### `## Session success condition`

End with:

> By the end of Session 27, remaining in the exact current status quo should clearly be impossible. The party should understand enough of the siege, Thrin, and the available directions to choose what they do next.

### Artifact structural proof

The server-side existing marker scanner must derive exactly:

```text
scene:mireward-climax
beat:survive-breach       → scene:mireward-climax
beat:town-wide-siege      → scene:mireward-climax
beat:thrin-memory         → scene:mireward-climax
beat:wall-hinge           → scene:mireward-climax
beat:aftermath-fork       → scene:mireward-climax
```

No Choice or Option element may be present.

---

## §4 Files in scope — exclusive write lease

| Action | Path | Purpose |
|---|---|---|
| Create | `Docs/Plans/HANDOFF-PLAY-c2s27-native-dogfood.md` | checked-in authority for this dogfood transaction |
| Modify | `Docs/Plans/HANDOFF-PLAY-native-runbook-instructions.md` | backward-looking D2 / #622 merged-historical sync |
| Modify | `Docs/Roadmaps/ROADMAP-playable-hoist-dungeonmind-kernel.md` | D2 completion + D3 current gate; no post-dogfood implementation selection |
| Modify | `Docs/Plans/HANDOFF-PLAY-native-graph-object-sheet.md` | D2 complete; keep P3B non-dispatchable behind D3 report/re-anchor |
| Create | `evals/c2_live_prep/mireward-prep/content/tiptap/c2s27-mireward-climax-runbook.md` | real Session 27 Runbook artifact |
| Create | `scripts/c2s27_native_play_dogfood.py` | dry-run-first idempotent local setup of exact workspace Runbook only |
| Create | `tests/test_c2s27_native_play_dogfood.py` | setup idempotency/fail-closed + marker-structure proof |
| Create | `Docs/Dogfood/PLAY-C2S27-NATIVE-RUNBOOK-DOGFOOD.md` | exact operator sequence for real Play dogfood |
| Create | `Docs/Reports/REPORT-play-c2s27-native-runbook-dogfood-2026-08.md` | initially NOT RUN; fill with actual observations before review/merge |
| Create | `Docs/Dogfood/BRIEF-PLAY-native-table-ux-from-c2s27-dogfood.md` | steward brief to Play design agent: redesign native Table UX around Of Conks keepers; not CODE |
| Create | `Docs/Design/DESIGN-play-native-current-moment-deck.md` | design-agent return; steward-accepted Table redesign; not CODE dispatch |
| Modify | `apps/live-control-ui/src/playSurface/playSurface.css` | steward-authorized mid-dogfood contrast fix: Play light-background buttons must set dark text instead of inheriting global `#e8eaef` |

No bounded discovery exception beyond the one CSS path above.

Do not edit other production UI/backend merely because dogfood setup or the live session reveals friction. The CSS contrast patch is an explicit steward exception so Session 27 can continue; it is not permission to implement P3B or other Play product work.

---

## §5 Explicitly out of scope

Do not modify or claim:

```text
apps/live-control-ui/src/** except `playSurface/playSurface.css` (contrast lease amendment)
apps/live_control_server/**
src/graph_memory/**
DungeonMind/**
DungeonMindDnD/**
```

Do not implement:

- Plan → Runbook product handoff;
- Runbook workspace-path generalization;
- replacement of `/tiptap-callout-spike`;
- generic Runbook selector/editor;
- Runbook create UI;
- Scene/Beat authoring buttons;
- Keep / Remove / Edit / Decide scaffold UI;
- agent-generated planning scaffold;
- new `briefing`, `pressure`, `gm-decision`, `npc-cue`, `exit-ramp`, or other durable kind;
- graph-reference opening / P3B;
- Add to Combat / P4;
- new combat encounter;
- new backend start-run/setup endpoint;
- Run/manifest creation in the setup helper;
- automatic Runbook selection;
- auto-latest Runbook logic;
- automatic Runtime writes during setup;
- Run deletion/rebase/cleanup;
- changes to the general Markdown writer allowlist;
- changes to the general workspace registry contract.

### Important anti-fix rule

When dogfood finds a product defect or friction:

```text
observe
→ reproduce if useful
→ record exact consequence
→ rank it
→ continue if safely possible
```

Not:

```text
observe
→ patch product code inside this PR
→ resume dogfood
```

If it prevents meaningful continuation, record it as a **DOGFOOD BLOCKER** and stop the session path. That blocker is evidence for the next re-anchor.

---

## §6 Setup-helper contract

Create `scripts/c2s27_native_play_dogfood.py` as a dogfood-only helper over existing services.

### CLI contract

Default is read-only/dry-run:

```bash
uv run python scripts/c2s27_native_play_dogfood.py
```

Mutation requires explicit intent:

```bash
uv run python scripts/c2s27_native_play_dogfood.py --apply
```

Support repository-root override for tests if useful:

```bash
--root <path>
```

The helper must emit enough copyable output to capture:

```text
status
document_id
campaign_id
target_session
target_relpath
revision
content_status
content_sha256
created_this_run
committed_this_run
```

JSON output is preferred; one stable final JSON object is sufficient.

### Constants

The script owns dogfood constants only:

```text
TITLE = C2 Session 27 — Mireward Climax
CAMPAIGN_ID = longmont-c2
TARGET_SESSION = 27
TARGET_RELPATH = evals/c2_live_prep/mireward-prep/content/tiptap/c2s27-mireward-climax-runbook.md
EXPECTED_ARTIFACT_SHA256 = <computed from canonical final-newline artifact>
```

The SHA pin ensures setup cannot silently register/commit a locally modified artifact.

### Pre-mutation validation

Before any registry mutation, require:

1. exact target file exists;
2. canonical writer-normalized content SHA matches `EXPECTED_ARTIFACT_SHA256`;
3. existing workspace ownership for the exact target path is unambiguous.

Inspect records with status filtering disabled so a discarded owner is visible.

### Existing-record cases

#### No record owns exact target

Dry-run:

- report `would_create_and_commit`;
- mutate nothing.

`--apply`:

1. call existing `create_workspace_document(...)` with exact metadata;
2. use existing writer `prepare_tiptap_markdown_write(...)`;
3. require `writer_ok` and confirm token;
4. call existing `commit_tiptap_markdown_write(...)` with exact content and expected revision;
5. reload exact snapshot;
6. require active + committed + session 27 + exact content SHA;
7. report exact resulting document ID/revision/SHA.

#### One active draft record owns exact target

Require exact:

- `kind == runbook`;
- campaign `longmont-c2`;
- target session `27`;
- expected title;
- target path exact.

Dry-run reports `would_commit_existing_draft`.

`--apply` commits **that same document ID** through prepare/commit. Do not create a replacement.

This is the recovery path if a previous setup attempt created the record and stopped before commit.

#### One active committed exact record owns target

Reload its snapshot and require exact expected SHA.

Report `ready_existing` and perform **no write** even with `--apply`.

A second `--apply` therefore returns the same document ID and same revision.

#### Discarded owner

Fail closed.

Do not revive it, delete it, patch it, or create a second owner.

#### Metadata conflict

If the target owner has wrong campaign/kind/session/title/path state, fail closed with the conflicting document ID and field.

Do not silently repair metadata.

#### Multiple owners

Fail closed even if repository invariants normally prevent this.

### Forbidden imports/calls

The helper must not import/call:

```text
play_run_registry create/replay
play_run_reference_manifest seal/replay
play_run_progress mutation
play_run_rebase
```

The helper's terminal success is **workspace Runbook ready for the operator to choose in `/play`**.

### Setup-helper tests

`tests/test_c2s27_native_play_dogfood.py` must prove at least:

1. artifact SHA pin matches the checked-in Session 27 file;
2. existing `derive_play_run_reference_elements(...)` sees exactly one Scene + five Beats and zero Choice/Option;
3. dry-run with no record mutates nothing;
4. `--apply`/core apply with no record creates exactly one Runbook and commits it through writer authority;
5. second apply is a no-op with same document ID + same revision;
6. an existing exact draft record is committed rather than replaced;
7. discarded exact owner fails closed with no second record;
8. wrong campaign/session/kind/title on exact owner fails closed;
9. artifact SHA mismatch fails before registry mutation;
10. helper code path does not create any Play Run/reference-manifest/runtime state.

Tests may exercise a factored pure/core setup function rather than shelling the CLI repeatedly.

---

## §7 Dogfood operator runbook

Create:

```text
Docs/Dogfood/PLAY-C2S27-NATIVE-RUNBOOK-DOGFOOD.md
```

This document is operational, not architecture authority.

### Phase A — prepare exact Runbook

From repository root on the PR head:

```bash
uv run python scripts/c2s27_native_play_dogfood.py
uv run python scripts/c2s27_native_play_dogfood.py --apply
uv run python scripts/c2s27_native_play_dogfood.py --apply
```

Expected:

- first command is read-only;
- first apply yields one exact active committed Session 27 Runbook;
- second apply is a no-op on the **same document ID and revision**.

Capture:

```text
Runbook document ID:
Runbook revision:
Runbook SHA:
Target path:
```

### Phase B — prove shipped Start Run

Start the existing backend/frontend normally.

1. Open `/play` with **no** `run` query.
2. Confirm no existing Run or Runbook is auto-selected.
3. In `Start a Run`, deliberately choose `C2 Session 27 — Mireward Climax`.
4. Start it through the UI.
5. Capture the exact resulting Run UUID.
6. Confirm browser route is `/play?run=<that UUID>`.
7. Confirm native Play reaches READY.

Do not use curl/Python/service calls to create the Run or manifest.

Capture:

```text
Run UUID:
Observed route:
Runbook document ID/revision/SHA shown/verified:
READY result:
```

### Phase C — pre-session structural smoke

In Table mode verify:

- one Scene: Mireward Siege Climax;
- five Beats in authored order;
- no authored Choice/Option controls for strategic directions;
- the opening Beat represents the active breach rather than a fresh setup scene.

Focus a non-first Beat locally, switch:

```text
Table → Runbook → Table
```

Verify:

- Runbook mode shows global session intent/current state/enemy intent;
- Runbook mode shows `Strategic directions`, `Exit ramps`, and `Open questions`;
- those global sections are not included in the final Beat body in Table mode;
- returning to Table restores local focus;
- mode switching alone writes no Runtime state.

### Phase D — real Runtime smoke before/at table

Using shipped controls only:

1. set/focus the appropriate current Scene/Beat when the session starts;
2. resolve or unresolve at least one Beat when true;
3. write at least one scratch note if useful;
4. hard reload the exact `/play?run=<uuid>` route;
5. confirm persisted authoritative progress remains.

Do not mutate a Beat merely to satisfy evidence if it would make the real session state false. The goal is real usage, not checkbox theater.

### Phase E — actual Session 27 dogfood

Run the actual session from this Runbook if practical.

The observer should capture **moments of friction**, not narrate every click.

Record when any of these occurs:

- needed information is not discoverable quickly enough;
- Runbook mode is too dense to scan;
- Table mode hides essential global context;
- Beat granularity fights the real session;
- a Beat is useful but the current Runtime controls are awkward;
- the GM needs a graph object/reference and leaving Play breaks flow;
- the GM needs exact mechanics/Combat and the handoff is awkward;
- authoring/setup overhead dominates the value of Play;
- the party takes an unexpected direction and the Runbook handles it well or poorly;
- a product error blocks continued use.

For each meaningful event record:

```text
Moment:
What I was trying to do:
What Play showed / required:
Impact at table:
Workaround used:
Candidate capability, if any:
```

Do not implement the workaround in this PR.

---

## §8 Dogfood report contract

Create initially:

```text
Docs/Reports/REPORT-play-c2s27-native-runbook-dogfood-2026-08.md
```

Initial status must be:

```text
NOT RUN
```

Before this PR receives final merge review, replace NOT RUN with the actual result or an explicit `BLOCKED` result that contains enough evidence to choose the next slice.

### Required report sections

```markdown
# Report — C2 Session 27 native Play dogfood

## Result
PASS_USEFUL | PASS_WITH_FRICTION | BLOCKED

## Exact identities
- PR head
- Runbook document ID
- Runbook revision
- Runbook SHA
- Run UUID
- exact /play route

## What was actually used

## What worked

## Friction, ranked
| Severity | Moment | Cost at table | Workaround | Candidate owner |

## Unexpected-player-path behavior

## Table vs Runbook mode

## Runtime continuity / reload

## Authoring/setup cost

## Decision questions

## Recommendation for re-anchor
```

### Required decision questions

Answer these from observed use, not roadmap inertia:

1. **P3B / exact graph-reference opening:** Did inability to open referenced NPC/location/item/source context from the active Runbook materially interrupt table flow?
2. **Plan → Runbook authoring:** Was getting accepted prep into a runnable Runbook a sharper problem than using the Runbook at the table?
3. **Playable authoring controls:** Did lack of normal Scene/Beat promotion/identity controls materially block prep iteration?
4. **Runbook storage policy:** Did the eval-only Runbook path/setup requirement become real user-facing friction worth generalizing next?
5. **Combat / P4:** Did moving from Play context into actual combat/mechanics become the dominant missing capability?
6. **Runtime ergonomics:** Were current Scene/Beat/resolved/note controls the dominant problem?
7. **No new capability:** Did the shipped path work well enough that another workstream should take priority?

### Recommendation discipline

The report may recommend a candidate next slice.

This PR must **not**:

- mark that candidate implemented;
- make P3B dispatchable;
- rewrite the roadmap current sequence past D3;
- create the next implementation handoff before post-dogfood re-anchor unless the steward explicitly decides to do so after reading the completed report.

---

## §9 Evidence required for review

### Automated setup/artifact proof

From repository root:

```bash
uv run pytest -q tests/test_c2s27_native_play_dogfood.py
```

Repository hygiene:

```bash
uv run python scripts/steward_preflight.py \
  --handoff Docs/Plans/HANDOFF-PLAY-c2s27-native-dogfood.md

git diff --check

git diff --name-only 62f7f9e856327247b8677b4c951801e4c58a826c...HEAD
```

### Existing Play regression smoke

No production Play code changes, so keep this focused rather than rerunning every historical suite:

```bash
cd apps/live-control-ui
pnpm exec vitest run \
  src/playSurface/StartRunPanel.test.tsx \
  src/playSurface/startRunAttempt.test.ts \
  src/playSurface/runbook/nativeRunbookProjection.test.ts \
  src/playSurface/runbook/RunbookTableDeck.test.tsx \
  src/App.test.tsx
```

The important acceptance evidence is the **real dogfood report**, not ceremony around command transcripts.

### Required dogfood identity capture

Review must be able to see:

```text
Runbook document ID
Runbook revision
Runbook content SHA
Run UUID
exact /play?run=<uuid> route
Runtime reload result
completed dogfood report result
```

A `BLOCKED` result is legitimate if the blocker is real and specific. Do not patch around a product blocker inside this PR merely to turn the report green.

---

## §10 Acceptance rubric

Reviewer accepts when all applicable items are true:

- [ ] D2 / PR #622 is atomically synchronized backward as merged/historical across the named mutable authorities.
- [ ] Roadmap integration tip is `62f7f9e...`, D2 is complete, D3 is current, and D3 is not pre-marked complete.
- [ ] P3B remains NON-DISPATCHABLE pending completed D3 report + re-anchor.
- [ ] The Session 27 artifact is real table-usable prep, not placeholder test prose.
- [ ] The artifact contains exactly one marked Scene and five marked Beats with the exact IDs in §3.
- [ ] Strategic directions remain ordinary instructions; there are zero Choice/Option markers.
- [ ] Setup is dry-run first and explicit `--apply` for mutation.
- [ ] Setup uses existing workspace + writer services; it does not edit registry JSON directly.
- [ ] Setup never creates a Run, manifest, progress mutation, or rebase.
- [ ] First apply yields one exact active committed Session 27 Runbook.
- [ ] Second apply is a no-op on the same document ID and revision.
- [ ] Conflict/discard/SHA mismatch cases fail closed.
- [ ] Operator deliberately starts the Run through shipped `/play` rather than bypassing it.
- [ ] Exact Run reaches READY on the Session 27 Runbook.
- [ ] Table mode shows the one Scene/five Beats and no fake strategic Choice controls.
- [ ] Runbook mode exposes global instructions and the H2 sections after the Beats without folding them into the final Beat.
- [ ] Existing Runtime progress is used truthfully and survives reload.
- [ ] Actual dogfood observations are recorded, including ranked friction or an exact blocker.
- [ ] No production product code/backend/schema/grammar changed.
- [ ] No next implementation is treated as selected until post-dogfood re-anchor.
- [ ] Every changed path is inside §4.

---

## Stop conditions

Stop and report rather than expanding when any of these occurs:

- the exact artifact cannot become a valid committed Runbook using existing writer authority;
- setup requires a new allowed Runbook path family;
- setup requires changing workspace registry behavior;
- setup would need to create/seal the Run directly;
- the Session 27 Markdown fails existing Playable admission and fixing it would require parser/grammar changes rather than correcting the artifact;
- real Play cannot Start the exact Runbook through the shipped UI;
- Play reaches a real product blocker that prevents meaningful dogfood;
- dogfood reveals a need for P3B, P4, Plan authoring, storage generalization, or Runtime UX changes;
- another active lane claims an exact §4 path or mutates the same live workspace/runtime state;
- `main` moves before dispatch and re-anchor changes the predecessor facts.

Use this report shape:

```text
Stop condition:
Observed while doing:
Exact artifact/document/run identity:
Why current D3 cannot absorb it:
Product boundary affected:
Workaround available? yes/no
Dogfood can continue? yes/no
Candidate successor slice:
Mutable authority update needed:
```

A stop condition is not a failed steward process. This PR exists specifically to make the next product decision evidence-driven.

---

## Post-merge successor — intentionally unselected

There is **no pre-authorized CODE successor** in this handoff.

After D3 merges:

```text
read completed dogfood report
→ re-anchor current main + mutable roadmap/design state
→ decide the smallest independently useful repair or capability
→ write that handoff
→ only then dispatch
```

Candidates that may emerge include—but are not limited to:

- P3B exact graph-reference opening;
- Plan → accepted Runbook workflow;
- generic Runbook workspace storage/authoring;
- Scene/Beat authoring controls;
- P4 Add to Combat;
- Runtime ergonomics;
- no Play change at all.

The dogfood report, not this candidate list, chooses the next slice.
