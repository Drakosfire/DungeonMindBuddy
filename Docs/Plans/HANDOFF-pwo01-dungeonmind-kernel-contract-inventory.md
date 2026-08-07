# HANDOFF — PWO01 DungeonMind kernel world-object contract inventory

**Created:** 2026-08-07  
**Status:** ACTIVE AFTER `KERNEL-0` — dispatch exactly one docs-only post-cutover contract-inventory capability.  
**Canonical handoff path:** `Docs/Plans/HANDOFF-pwo01-dungeonmind-kernel-contract-inventory.md`  
**Conversation / workstream:** Play + World-Object Combat Projection  
**Flow / agent:** `DOCUMENTS`  
**Handoff direction:** `DESIGN → CODE`  
**Coordination repository:** `Drakosfire/DungeonMindBuddy`  
**Kernel repository to inspect:** `Drakosfire/DungeonMind`  
**Design-time DungeonMindBuddy base:** `8d2a35019f64fa80b716a7d621903908e14d95b1`  
**Design-time DungeonMind anchor:** `7c311ae0d0d59d7379dee38780be509970fb3a8c`  
**Suggested implementation branch:** `agent/pwo01-kernel-contract-inventory`  
**Expected implementation PR title:** `DOCUMENTS: inventory post-cutover world-object contracts`  
**Roadmap:** [`../Roadmaps/ROADMAP-play-world-object-combat-projection.md`](../Roadmaps/ROADMAP-play-world-object-combat-projection.md)  
**PR tracker:** [`PR-TRACKER-play-world-object-combat-projection.md`](PR-TRACKER-play-world-object-combat-projection.md)

> **Dispatch gate:** this handoff may merge before the graph-kernel cutover, but the implementation PR described here must not begin until `KERNEL-0` is actually complete and the coding agent can name the exact post-cutover `DungeonMind/main` SHA that owns the graph-kernel contracts being inventoried.
>
> This checked-in handoff is the implementation authority. The implementation PR description is transport metadata only. It does **not** need to say that this handoff merged, does **not** need to narrate the handoff lifecycle, and does **not** become authoritative by being kept synchronized with review repairs. The implementation branch simply must be based on repository state where this handoff is available, and the implementation report must record the exact SHAs it audited.

---

## §0 Capability decomposition decision

`PWO01` exists to prevent every downstream Play/NPC/PC/Combat PR from independently guessing what the new DungeonMind kernel exposes after cutover.

| Candidate outcome | Independently useful? | Changes runtime/public contract? | Belongs in PWO01? |
|---|---:|---:|---|
| Re-anchor the exact post-cutover DungeonMind graph-kernel contracts | Yes | No | **Yes** |
| Inventory the exact DungeonBuddy consumer boundary for those contracts | Yes | No | **Yes** |
| Audit existing Threat exact mechanics/resource-binding identity against the new kernel | Yes | No | **Yes** |
| Audit current NPC representation and identify the smallest missing first-class `npc` contract | Yes | No | **Yes** |
| Audit current Player Character identity, party-anchor, mechanics, and persistent-state authority | Yes | No | **Yes** |
| Freeze one evidence-backed downstream contract map | Yes | No | **Yes** |
| Implement `npc` as a new world-object kind | Yes | Yes | **PWO02 — excluded** |
| Implement `player_character` as a new world-object kind | Yes | Yes | **PWO03 — excluded** |
| Add `/play` | Yes | Yes | **PLAY01 — excluded** |
| Change combat persistence | Yes | Yes | **COMBAT01 — excluded** |
| Add a generic universal Character schema | No | Yes | **Explicitly prohibited** |
| Invent a PC mechanics revision model because none exists | No | Yes | **Explicitly prohibited** |

**Selected capability:**

```text
Produce one evidence-backed post-cutover contract inventory that tells downstream
agents exactly how DungeonBuddy addresses, requests, projects, and pins world
objects and generated mechanics through the DungeonMind kernel, while explicitly
identifying the current NPC and Player Character gaps without implementing them.
```

**Merge-ready invariant:**

```text
Every downstream identity or mechanics claim in the report is grounded in one
exact post-cutover repository contract, path, symbol, persisted shape, or test;
missing contracts remain named gaps rather than inferred substitutes, and no
runtime or durable authority changes occur in this PR.
```

### §0.1 `KERNEL-0` dispatch gate

Before changing any file for the PWO01 implementation PR, the coding agent must record all of the following in its working notes and in the report's re-anchor table:

```text
DungeonMindBuddy main SHA:
DungeonMind main SHA:
Kernel cutover merge / decision SHA or PR:
Current graph-kernel ownership statement:
Current DungeonBuddy adapter/consumer ownership statement:
```

`KERNEL-0` is considered satisfied for this handoff only when current repository truth shows that DungeonMind is the graph-kernel authority being targeted by this workstream. A roadmap sentence saying a cutover is planned is not sufficient.

If the cutover is not complete, stop before opening an implementation PR and report:

```text
PWO01_BLOCKED_ON_KERNEL_0
<exact missing merge, contract, or authority fact>
```

Do not produce a speculative inventory against the predecessor kernel and call it post-cutover truth.

### §0.2 Mandatory review-cycle accounting

Both the coding agent and the reviewer must count review cycles explicitly. This is a process requirement for this workstream.

**Definition:** a review cycle is one complete cumulative reviewer pass over one implementation head SHA. Clarification comments that do not constitute a cumulative review do not increment the count.

Use this exact convention:

```text
Cycle 0
  Coding agent has opened the implementation PR and supplied initial evidence.
  No cumulative reviewer pass has completed yet.

Review cycle 1
  Reviewer performs the first cumulative review of the implementation PR head.

Cycle 1 repair
  Coding agent addresses the findings from review cycle 1 and publishes a new head.

Review cycle 2
  Reviewer performs the next cumulative review of the new head.

...continue monotonically until merge-ready.
```

Rules:

1. The reviewer must title every cumulative review or top-level review summary:
   `Review cycle N — head <SHA>`.
2. The coding agent must title every repair handback:
   `Cycle N repair — head <SHA>` and enumerate each finding from that cycle with its disposition.
3. Do not reset the count after rebases, agent/session changes, model changes, reviewer restarts, or branch updates.
4. A cumulative pass that finds zero blockers still counts as a review cycle.
5. The final merge-ready review must state `Review cycles completed: N`.
6. The coding agent must preserve enough PR comments or checked-in evidence for a fresh reviewer to recover the current count without guessing.
7. **Do not use the PR description as the cycle ledger.** The body may remain a minimal transport pointer for the entire review.
8. **Do not require the implementation PR description to say this handoff merged.** Handoff availability is established by the implementation base/history and the checked-in canonical path, not by narrative PR-body maintenance.

For this workstream, reviewer time is spent on the cumulative diff, the checked-in handoff, the report, exact evidence, and repairs—not on keeping prose in the PR description cosmetically current.

---

## §1 Mission

A downstream implementation agent can read one PWO01 report and write exact tests for `PWO02`, `PWO03`, `PLAY01`, and `COMBAT01` without consulting predecessor union-store assumptions or inventing Player Character mechanics authority.

### Core questions the report must answer

1. **World object identity:** What exact type(s), IDs, tenancy fields, concrete kind discriminator, and immutable graph-revision identity does the post-cutover DungeonMind kernel expose to a consumer?
2. **Projection:** What exact request identity and response envelope does DungeonBuddy use to project one object, including relationships and object-specific payload?
3. **Generated resources:** How is an exact generated resource binding represented now—resource kind, resource ID, revision ID, digest, role, and multiplicity?
4. **Threat proof:** Can an existing published Threat still be traced from exact world-object identity to exact accepted statblock mechanics with no Markdown/path/display-name lookup?
5. **NPC gap:** What does the current kernel call and store for persistent non-player people, and exactly what is missing before `kind=npc` can be a first-class contract?
6. **PC identity gap:** How do deterministic party anchors/registry identity map into the kernel after cutover, and what prevents a first-class `player_character` object today?
7. **PC mechanics/state authority:** Is there currently an exact, durable mechanics reference suitable for a pinned Play/Combat consumer? Where do persistent current HP/resources live? If either answer is “nowhere,” say so explicitly.
8. **Consumer seam:** Which DungeonBuddy contracts/adapters should downstream surfaces depend on rather than kernel storage internals?
9. **Prohibited fallbacks:** Which predecessor paths must downstream work avoid—Markdown files, corpus paths, artifact titles, display names, implicit `latest`, first binding, or surface-owned copies?

### Required final disposition

The report must end with exactly one of:

```text
PWO01_READY
```

or

```text
PWO01_NOT_READY — <exact blocking contract facts>
```

If `PWO01_READY`, the report must give readiness rows for these four successors:

```text
PWO02 — NPC world object: READY | BLOCKED
PWO03 — Player Character world object: READY | BLOCKED
PLAY01 — Play surface shell: READY | BLOCKED
COMBAT01 — exact source locator persistence: READY | BLOCKED
```

A successor may remain blocked even when PWO01 itself is complete; the value of this PR is to identify the exact block.

---

## §2 Context, authority, and required reads

### 2.1 Parent authority

Read current versions in this order:

#### DungeonMindBuddy

```text
Docs/Roadmaps/ROADMAP-play-world-object-combat-projection.md
Docs/Plans/PR-TRACKER-play-world-object-combat-projection.md
Docs/Design/DECISION-grounded-authored-world-object-lifecycle.md
Docs/Design/ARCHITECTURE-surface-interaction-layer.md
Docs/Design/DESIGN-authored-threat-statblock-domain-contract.md
Docs/Plans/PR-TRACKER-threat-statblock-authoring-projection.md
Docs/CONVENTION-NPC-Hub-Package.md
Docs/CONVENTION-PC-Hub.md
```

The PC corpus convention is especially important: it currently states that the corpus owns PC continuity, **not** the live player character sheet by default. PWO01 must not silently convert corpus dossier/statblock Markdown into the normal mechanics authority merely because Combat needs numbers.

#### DungeonMind

Read the current post-cutover kernel authority and the current exact mechanics-resource authority. At design time the latest known exact statblock resource work is represented by:

```text
Docs/Handoffs/HANDOFF-exact-statblock-resource-resolver.md
DndMechanicsResourceRef
DndThreatMechanicsBinding
exact revision graph reads
Threat mechanics hydration
statblock resource resolver
```

These names are **design-time reconnaissance anchors**, not permission to assume the post-cutover contract kept the same files or symbols. Record replacements and deletions explicitly.

### 2.2 Current DungeonMindBuddy implementation seams to inspect

Re-discover after `KERNEL-0`; do not trust these paths to remain unchanged. Current pre-cutover examples include:

```text
apps/live-control-ui/src/statblocks/projection/ThreatSheetProjection.tsx
apps/live-control-ui/src/statblocks/projection/threatSheetViewModel.ts
apps/live-control-ui/src/graphReference/ResolvedGraphObjectProjection.tsx
apps/live-control-ui/src/surfaceInteraction/types.ts
apps/live-control-ui/src/App.tsx
apps/live_control_server/services/combat_state.py
src/graph_memory/party_context.py
src/graph_memory/session_graph_context.py
apps/live_control_server/services/party_registry_surface.py
apps/live_control_server/services/party_registry_write.py
corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/_party_registry.json
```

Also inspect the actual current PC-generation / character-sheet system wherever it lives. Search by behavior and public routes/types; do not assume it is in this repository simply because older DungeonMind product architecture once hosted a PlayerCharacterGenerator.

### 2.3 Authority precedence

When evidence conflicts, use this order:

```text
1. current merged code + tests at the recorded SHAs
2. current accepted architecture / decision documents
3. current active tracker / checked-in handoff
4. current open PR cumulative code when the PR is explicitly part of KERNEL-0
5. design-time anchors in this handoff
6. historical docs / archived prototypes / corpus conventions
7. PR descriptions and chat summaries
```

PR descriptions may help locate code; they are never sufficient evidence for a contract claim.

---

## §3 Required contract inventory

The implementation report must contain all matrices below. Use exact symbol/path/schema names. If no contract exists, write `MISSING` and explain the observed consequence.

### A. Kernel world-object identity matrix

| Concern | Exact post-cutover contract | Owning repo/path/symbol | Persisted or derived? | Failure/ambiguity behavior |
|---|---|---|---|---|
| world identity | | | | |
| object/node identity | | | | |
| concrete object kind | | | | |
| campaign/world tenancy | | | | |
| graph revision identity | | | | |
| visibility/authority | | | | |
| aliases/display label | | | | |
| provenance/evidence pointers | | | | |

The report must explicitly say whether `Threat`, `NPC`, and `PlayerCharacter` are represented as distinct concrete kinds today. Do not infer subtype semantics from labels or source folders.

### B. Projection request/response matrix

Inventory the exact contract DungeonBuddy can depend on for:

```text
world_id
campaign_id / visibility scope
focus object(s)
revision pin / head behavior
admissibility / query text when relevant
request/cache identity
selected exact object
relationships
object-specific typed payload or extension seam
zero / one / many semantics
stale or unavailable behavior
```

State which fields are contract authority and which are UI/cache concerns.

### C. Exact generated-resource binding matrix

| Concern | Exact contract | Owner | Multiplicity | Normal consumer rule |
|---|---|---|---|---|
| world object ref | | | | |
| resource kind | | | | |
| resource ID | | | | |
| immutable revision ID | | | | |
| definition/content digest | | | | |
| binding ID | | | | |
| role / phase / variant | | | | |
| selected/preferred policy | | | | |

Explicitly verify:

```text
exact pinned consumer → exact revision/digest
no display-name resolution
no implicit latest fallback
no first-winner behavior for plural bindings
no copied full mechanics body in graph truth
```

### D. DungeonBuddy consumer boundary matrix

For each current consumer, state the exact adapter/API/type it should depend on after cutover:

| Consumer | Current entry point | Kernel-facing adapter | Exact identity retained | Must not depend on |
|---|---|---|---|---|
| Plan graph-object projection | | | | |
| Build graph-object projection | | | | |
| Threat Sheet | | | | |
| shared World Graph lens/provider | | | | |
| future Play projection | | | | |
| future Combat seed adapter | | | | |

If the cutover leaves DungeonBuddy reaching directly into kernel persistence/storage internals, call that out as a blocker rather than normalizing it.

### E. Threat exact proof trace

Choose one real existing accepted/published Threat if current local fixtures/state allow it; prefer a Mireward Threat such as Mireward Latchling or Tripod Null-Calf. Trace:

```text
exact world object ID
→ exact graph revision
→ exact Threat/resource binding
→ exact statblock ID
→ exact statblock revision ID
→ exact digest
→ typed mechanics hydration
→ current Threat projection consumer
```

The report is not required to run a live UI, but every hop must cite current code/test/persisted evidence. If live/persisted product state is unavailable, use the strongest exact checked-in fixture and state that limitation.

Any hop that requires corpus Markdown, `statblock_path`, artifact title, display-name lookup, or implicit `latest` is a named contract gap.

### F. NPC representation audit

Answer:

```text
What exact kind/type represents a persistent non-player person today?
Where does identity come from?
How are aliases/relationships/provenance represented?
How does existing generic actor extraction map into that identity?
How are monsters/Threats prevented from being collapsed into NPCs?
What minimum missing contract blocks PWO02?
```

Do not design optional personality/motivation/occupation fields into a universal base object unless current kernel authority already does so.

### G. Player Character identity audit

Trace the current Campaign 2 party identity path from source/registry through graph materialization/projection. At minimum inspect:

```text
_party_registry.json
party_context.py or its post-cutover replacement
session_graph_context.py or its post-cutover replacement
party registry write/read surface
current graph node IDs emitted for PCs
party membership relationships
```

Answer whether the existing deterministic party anchor can become the stable first-class `player_character` identity without duplication, or whether a deterministic migration/link is required.

The report must explicitly reject this outcome:

```text
Baergrom (legacy party anchor)
Baergrom (new PlayerCharacter)
```

as two silently independent durable world identities.

### H. Player Character mechanics and persistent-state audit

This is a required PWO01 deliverable, not a later optional investigation.

Find and name the current authority, if any, for:

```text
stable PC mechanics identity
character sheet / build persistence
revision/version identity
ruleset/version declaration
max HP / AC / initiative derivation
current HP
limited-use resources / spell slots / class resources
save/reload semantics
player-owned vs GM-owned authority
```

Separate these concerns explicitly:

```text
PlayerCharacter world identity
PC mechanics/build definition
persistent PC state
encounter-local combat overlay
```

Do not call a dossier, recap, static Markdown statblock, or party registry a mechanics authority unless current product code actually treats it as such.

Finish this section with exactly one of:

```text
PC_MECHANICS_PIN_AVAILABLE — <exact contract and owner>
```

or

```text
PC_MECHANICS_PIN_MISSING — <smallest missing exact-reference contract>
```

And independently:

```text
PC_PERSISTENT_STATE_AUTHORITY_AVAILABLE — <exact contract and owner>
```

or

```text
PC_PERSISTENT_STATE_AUTHORITY_MISSING — <smallest missing authority decision/contract>
```

`PWO01` identifies these facts; it does not invent the missing implementation.

---

## §4 Observable and adversarial audit paths

This is a docs-only inventory, but it must cover the behaviors downstream code will depend on.

| Path | Contract to verify | Required conclusion |
|---|---|---|
| Exact object by ID + pinned graph revision | deterministic historical projection | no head/latest substitution |
| Object at head | explicit head semantics | distinguish head request from pinned revision |
| Unknown object ID | ordinary miss | no label fallback |
| Wrong object kind | integrity/type mismatch | fail closed or exact documented behavior |
| Multiple resource bindings | plural mechanics | no first-winner |
| Resource provider unavailable | dependency failure | mechanics unavailable without rewriting object truth |
| Wrong resource revision/digest | integrity failure | no best-effort mechanics |
| Browser/surface switch | same exact request | shared projection request identity remains reusable |
| Legacy combat entity | old path/artifact identity | compatibility is explicit; exact source identity is not fabricated |
| PC without shared mechanics | player-owned sheet | Play/Combat must not silently scrape corpus prose |

The report must distinguish what is already proved by tests from what is only a required downstream behavior.

---

## §5 Implementation output and file allowlist

This implementation PR is intentionally docs-only.

### Required created file

```text
Docs/Reports/PWO01-dungeonmind-kernel-world-object-contract-inventory.md
```

### Allowed changed paths

| Action | Path | Purpose |
|---|---|---|
| Create | `Docs/Reports/PWO01-dungeonmind-kernel-world-object-contract-inventory.md` | Entire PWO01 deliverable |

No other changed path is authorized.

If the coding agent discovers that a second durable document is necessary to state the result truthfully, stop and ask for decomposition rather than silently widening the PR.

### Explicitly out of scope

```text
DungeonMind production code
DungeonMindBuddy production code
schemas/models/routes/services
UI components
world graph data migrations
party registry mutation
corpus edits
NPC creation
PlayerCharacter creation
Play route
Combat persistence
CombatantSeed adapter
tracker/roadmap status sync
Backlog changes
this handoff status sync
```

Roadmap/tracker/handoff status synchronization is a separate document-sync operation after the implementation report is reviewed/merged.

---

## §6 Report quality contract

Every substantive contract claim must include enough evidence for a fresh reviewer to re-open it:

```text
repository
exact audited SHA
path
symbol/schema/test name when available
what the evidence proves
what it does not prove
```

Avoid large pasted code blocks. Prefer concise contract extracts and exact pointers.

### Required report structure

```text
# PWO01 — DungeonMind kernel world-object contract inventory

1. Disposition
2. Re-anchor ledger
3. Kernel ownership after cutover
4. World-object identity matrix
5. Projection request/response matrix
6. Generated-resource binding matrix
7. DungeonBuddy consumer boundary matrix
8. Exact Threat proof trace
9. NPC representation audit
10. Player Character identity audit
11. Player Character mechanics/state audit
12. Prohibited fallback / legacy-path ledger
13. Successor readiness
14. Evidence ledger
15. Review-cycle ledger
```

### Prohibited-fallback / legacy-path ledger

The report must name the status of all discovered predecessor identities relevant to Play/Combat, including at minimum any surviving forms of:

```text
statblock_path
statblock_artifact_id
statblock_title
corpus fingerprint as mechanics identity
Markdown filename/path as combat mechanics authority
display-name resolution
implicit latest revision
first matching binding
party-anchor-only PC semantics
```

For each, classify:

```text
ACTIVE AUTHORITY
COMPATIBILITY-ONLY
DEAD BUT NOT DELETED
NOT FOUND POST-CUTOVER
```

Do not delete any of them in PWO01.

---

## §7 Evidence ledger and verification

Because this is an audit PR, review evidence is primarily exact-source inspection rather than behavioral tests. Still, the coding agent must prove the document itself is clean and the evidence is reproducible.

| Evidence ID | Claim | Owning evidence | Merge-blocking stop condition |
|---|---|---|---|
| E1 | `KERNEL-0` is actually complete | current merged authority + exact SHAs | cutover still planned/in-flight |
| E2 | world-object identity matrix is exact | post-cutover kernel types/tests | any required row inferred from docs only |
| E3 | projection contract is exact | request/response types + tests | hidden storage/internal dependency required |
| E4 | resource binding is exact | kernel/resource contracts + Threat consumer tests | latest/name/first-winner required |
| E5 | Threat trace is coherent | exact fixture/state + code/tests | any hop cannot retain exact identity |
| E6 | NPC gap is grounded | current type/extraction/projection code | report invents target fields instead of naming gap |
| E7 | PC identity audit is grounded | registry + materialization + projection code/tests | duplicate identity risk unresolved in report |
| E8 | PC mechanics/state answer is grounded | actual owning system or explicit absence evidence | mechanics authority guessed from corpus prose |
| E9 | consumer boundary is actionable | DungeonBuddy adapters/types | downstream must reach kernel storage internals |
| E10 | docs-only scope holds | changed-file list | any non-report path changed |

Minimum verification at implementation handback:

```text
git diff --check
git diff --name-only <base>...HEAD
```

Plus the exact repository/code-search commands used to locate the contracts where useful. If an owning package has a lightweight contract test that materially confirms a report claim, the agent may run it and record the result; PWO01 does not require broad test suites merely to make a docs change.

---

## §8 Coding-agent instructions

1. Do not begin until `KERNEL-0` satisfies §0.1.
2. Re-anchor both repositories and record exact SHAs before reading historical plans.
3. Read the authorities in §2 before exploring implementation details.
4. Treat current merged code/tests as truth; use PR descriptions only as navigation aids.
5. Search broadly enough to find renamed/replaced kernel contracts after cutover; do not force the report into design-time symbol names.
6. Produce exactly the one report in §5.
7. Do not change runtime code even if the audit reveals an obvious one-line fix.
8. Do not create NPC/PC schemas in this PR.
9. Do not invent PC mechanics/state authority. An explicit `MISSING` result is a successful PWO01 outcome if that is current truth.
10. Keep the implementation PR body minimal. It may point to this handoff, the report, base/head SHAs, and verification. It does **not** need to say “handoff merged,” summarize every repair, or become the review ledger.
11. Start review-cycle accounting at `Cycle 0` when requesting the first cumulative review.
12. After each reviewer pass, publish `Cycle N repair — head <SHA>` with a one-to-one disposition for every finding before requesting the next review.
13. Never reset the cycle count.
14. If a review finding requires production changes to make the report true, classify that as a discovered blocker/successor; do not absorb the implementation into PWO01.

### Coding-agent handback format

```text
PWO01 implementation head: <SHA>
Audited DungeonMindBuddy SHA: <SHA>
Audited DungeonMind SHA: <SHA>
KERNEL-0 evidence: <merge/decision>
Changed paths: <must be report only>
Disposition: PWO01_READY | PWO01_NOT_READY
PC mechanics disposition: ...
PC persistent-state disposition: ...
Successor readiness: PWO02 / PWO03 / PLAY01 / COMBAT01
Verification: ...
Review cycle requested: <N>
```

---

## §9 Reviewer instructions — applies explicitly to the future reviewer/me

The reviewer is responsible for reviewing **current repository truth**, not for rewarding completeness of prose.

At the beginning of each cumulative pass:

1. Recover the previous cycle number from PR review/comments.
2. Increment it exactly once.
3. State `Review cycle N — head <SHA>` before findings.
4. Identify the implementation base SHA and both audited repository SHAs.
5. Confirm the cumulative diff contains only the report path.

Review the report adversarially against this handoff:

### Authority checks

- Does `KERNEL-0` have exact merged evidence, or did the author audit a planned cutover?
- Does every identity/projection/resource claim point to current code/tests?
- Are old DungeonMindBuddy union-store details being smuggled in as post-cutover truth?
- Is any cache/resident/prewarm state incorrectly treated as authority?

### Threat checks

- Can one exact Threat be followed without name/path/Markdown/latest fallback?
- Are multiple bindings represented honestly?
- Does full mechanics remain exact immutable resource authority rather than graph-copied JSON/Markdown?

### NPC checks

- Does the audit distinguish a persistent NPC from Threat/monster semantics?
- Does it identify the smallest missing PWO02 contract instead of designing a giant person schema?

### Player Character checks

- Is deterministic party-anchor identity preserved or explicitly migrated, rather than duplicated?
- Does the report honor the player-owned character-sheet boundary in the current PC convention?
- Is the mechanics pin answer based on an actual mechanics store/API/version contract?
- Is persistent PC state separated from encounter-local runtime state?
- If current HP/resources have no durable owner, does the report say `MISSING` instead of pretending combat runtime should own all of it?

### Consumer-boundary checks

- Can PWO02/PWO03/PLAY01/COMBAT01 write tests against named adapters/contracts?
- Is any downstream consumer being told to depend on kernel persistence internals?
- Are prohibited fallbacks explicit?

### Review-cycle behavior

- Findings must be specific: failure, affected report section/evidence, source that contradicts it, and required correction/proof.
- A reviewer pass with no blockers still increments the cycle count and may approve.
- If new repairs are pushed, the next cumulative review uses the next integer; never reuse the previous cycle number.
- Final approval states `Review cycles completed: N`.
- Do **not** request PR-description edits merely to say the handoff merged, to mirror cycle history, or to narrate repairs. The body is transport metadata.

### Merge blockers

Any of these blocks PWO01:

```text
KERNEL-0 not actually complete
report relies on predecessor assumptions without labeling them historical
contract claim has no exact current evidence
PC mechanics/state authority is invented
NPC/PC implementation is mixed into the docs PR
normal combat path is allowed to resolve mechanics from Markdown/path/name/latest
world-object consumer is required to depend on kernel storage internals without naming that as a blocker
changed files exceed the report-only allowlist
review-cycle count is reset or cannot be recovered after substantive reviews
```

---

## §10 Expected consequences after merge

A successful PWO01 does **not** itself make NPC, PC, Play, or Combat more capable.

It makes the next implementation slices cheaper and safer by freezing what they can depend on.

Expected sequencing after a `PWO01_READY` report:

```text
PWO02 — first-class NPC world-object contract
PWO03 — first-class Player Character world-object identity/migration
PLAY01 — Play surface shell (may proceed as soon as its kernel consumer seam is ready)
COMBAT01 — exact source locator + bounded operational snapshot persistence
```

`PWO02` and `PWO03` may be parallel if the report shows their kernel changes are independent. `PC01` remains later if the report concludes the exact PC mechanics/state authority is still missing.

The product invariant remains:

```text
Threat, NPC, and PlayerCharacter are distinct world-object kinds that may share
projection/capability infrastructure; Combat consumes a truthful runtime-seed
contract and never decides world-object identity or canonical mechanics authority.
```

---

## §11 Minimal implementation PR transport body

The coding agent may use a body approximately this small:

```markdown
## Handoff pointer
- Flow: DOCUMENTS
- Handoff: `Docs/Plans/HANDOFF-pwo01-dungeonmind-kernel-contract-inventory.md`
- Report: `Docs/Reports/PWO01-dungeonmind-kernel-world-object-contract-inventory.md`

## Verification pointer
- Implementation base/head: `<base>` → `<head>`
- Audited DungeonMindBuddy: `<sha>`
- Audited DungeonMind: `<sha>`
- `git diff --check`: `<result>`
- Changed paths: report only

The checked-in handoff, report, cumulative diff, exact-source evidence, and
independently rerun review are the review contract. The PR description is
transport metadata only.
```

Nothing is gained by adding “the handoff merged” to this body. Do not make that a review requirement.
