# DEMO — one prepared adventure, one connected session

**Status:** ACTIVE — sole Buddy DEMO execution roadmap, adopted 2026-09-26  
**Repository:** `Drakosfire/DungeonMindBuddy`  
**Steward:** [STEWARDS-HANDOFF-demo.md](../Plans/STEWARDS-HANDOFF-demo.md)  
**Transfer mapping and source evidence:** [reconciliation report](../Reports/REPORT-DEMO-roadmap-reconciliation-2026-09-26.md)

## Product contract

A GM imports parsed adventure/session Markdown, prepares with an agent authoring
onto the document, inspects and authors knowledge, develops a statblock and image,
then runs and resumes the session using readable, quickly reachable components.

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
- The steward may merge bounded in-scope DEMO PRs after independent exact-head
  review, required checks and integration evidence. Cross-owner PRs remain with
  their owners.

## Current execution checkpoint

**No integrated rehearsal was performed by the survey. No journey milestone is
certified complete by the adoption transaction.**

Inherited work: PLAY-1 / Buddy #773 merged at
`7fe771e86df2e796484b058aa2e6a8e7c94c9fb9` after two review cycles;
it proves only the in-memory Buddy→WorldKeeper consumer mapping. Next technical
witnesses remain persistent isolated authority and browser interaction. Basic presentation
design/dogfood has an existing merged handoff independent of Canvas F5/F6.
Foundation evidence and exact snapshot PRs are in the reconciliation; refresh at
activation rather than copying those snapshots into another permanent tracker.

First actions:

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

## DEMO-J1 — import and prepare

**Acceptance:** Import the bounded parsed Markdown through ordinary product
controls into a fresh demo workspace. Open a coherent editable Plan; inspect
ingested objects and source relationships. No special Of Conks import path.

**Inherited evidence:** CON-READY CR-U1–U5/U11; source ingress and durable
application-state foundations. Their presence is not proof that arbitrary
adventure Markdown becomes usable preparation without intervention.

**Likely owner:** DEMO Document/Agent plus Knowledge consumer.

**Verify before dispatch:** lossless Markdown/component round-trip; document and
source identity; supported ingestion authority; required source admission and
new-space initialization. If the chosen vNext demo cannot admit this corpus,
delegate the missing contract rather than borrowing an incompatible legacy read path.

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

**Inherited evidence:** PLAY-1 #773; PLAY-2/3 planned successors; V6.2 adapter;
WorldKeeper #7/#8; CR-U4–U7. Existing in-memory proof does not close this milestone.

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
  presentation defects or evidence that the extraction failed. J1 remains
  blocked; J2–J6 are not certified by this partial rehearsal. Next: design the
  smallest managed-World Plan-context slice, preserving C1/C2, then re-test
  this exact transition. Independently determine the bounded World-reference
  lens repair before any accepted first-World publication. Do not spend on
  another extraction to fix routing.

  The licensed Of Conks package remains local-only and must not be committed.
  Its `specimens/02-prepared.md` matches its local manifest; the local
  `playable/hempholm-prep.md` SHA-256 is
  `c473329dd3a0425559e1d2fae60707a13036e0c473f1dd802e8a96804a2fd86f`,
  not the manifest's `1b350f...` pin. Resolve that input pin before claiming a
  fully reproducible final rehearsal. The new demo DBs and source root are
  disposable local rehearsal state, not production authority.
- **DEMO-J1 selected-context repair:** ACTIVE handoff
  [`HANDOFF-DEMO-selected-world-context-v1.md`](../Plans/HANDOFF-DEMO-selected-world-context-v1.md).
  One serial Buddy PR may prove that the imported managed World selection binds
  Plan, Build, Graph Review, Ask and World requests without C2/Eldyrwild
  fallback. This records dispatch authority, not implementation acceptance.
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
demo must prove coherent read/write authority and source admission. If only a
separately governed migration enables that, record it as a real dependency.

## Final acceptance

Perform J1→J6 twice from a resettable environment without console/SQL/manual-ID
repair, including real generation, graph read-after-write and restart/resume.
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
