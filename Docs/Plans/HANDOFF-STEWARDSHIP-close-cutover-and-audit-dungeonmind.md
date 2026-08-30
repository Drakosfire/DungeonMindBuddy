# HANDOFF — STEWARDSHIP: close CUTOVER and audit DungeonMind

**Created:** 2026-08-29  
**Status:** ACTIVE — steward mission, not one implementation PR  
**Primary repository:** `Drakosfire/DungeonMindBuddy`  
**Secondary repository:** `Drakosfire/DungeonMind`  
**Buddy closure anchor:** `b667205f2fb8c78ff7e91d113facba12e3339a4d` — merge of Buddy #667  
**DungeonMind audit anchor:** `5ca5d688612349034f8ca490d465af166d883e6e` — current DungeonMind `main` and exact Buddy dependency pin  
**Reserved Buddy steward branch:** `steward/post-cutover-dungeonmind-audit`  
**Reserved DungeonMind steward branch:** `steward/post-cutover-library-critique`  
**One-line mission:** close the CUTOVER workstream truthfully, capture what the migration taught us, then evaluate DungeonMind from first principles as an independent library and turn that critique into a small evidence-backed successor ladder.

---

## §1 Outcome

This steward mission ends in two explicit states.

### A. DungeonMindBuddy / CUTOVER is closed

Repository authority must say, without stale qualifiers:

```text
D.3A mounted graph-engine excision     COMPLETE / MERGED  #665
D.3B physical graph-engine deletion    COMPLETE / MERGED  #667
D.3 Buddy graph-engine demolition      DONE
CUTOVER implementation                 CLOSED
```

Exact D.3B completion facts:

```text
PR                  #667
accepted head       d60bda6129d2c2aa6ccfd4d44336cc6e50619ec2
merge               b667205f2fb8c78ff7e91d113facba12e3339a4d
formal review cycles 2
final PASS review   5059960158
final owning cohort 107 passed / 0 required PostgreSQL skips (author-local)
```

The parked pre-switch `pinned exact-snapshot catch-up` path is no longer `DEFERRED` future work. It was conditional on observing a pre-switch Buddy snapshot B classified `STALE`; no such B was observed, authority transferred, the Buddy writer was retired, and the Buddy graph engine has now been physically deleted. Record that lane as **SUPERSEDED / CLOSED by completed authority transfer and demolition**. Do not resurrect it as living migration work.

### B. DungeonMind has an evidence-backed independent-library critique

The steward produces a durable DungeonMind report that answers both:

> **Bottom up:** what actually exists, what imports what, what is exercised, what costs complexity, and what can disappear?

and

> **Top down:** if we were designing the smallest trustworthy world-knowledge library today, knowing everything the cutover taught us, what would we build and what would we deliberately leave outside?

The critique must converge those views into a classified subsystem ledger and a small successor ladder. It may recommend deletion, collapse, relocation, API consolidation, experiments, or explicit retention. It must not perform a broad rewrite merely because the library is now safe to experiment on.

The important new operating freedom is real:

```text
DungeonMindBuddy main
  pins DungeonMind exactly at 5ca5d688612349034f8ca490d465af166d883e6e

future DungeonMind commits
  do NOT affect Buddy until an explicit Buddy repin
```

Use that isolation aggressively for learning. Do not casually consume it by repinning Buddy during the critique.

---

## §2 Authority and anchors

Read these before acting.

### DungeonMindBuddy closure authority

1. `AGENTS.md`
2. `Docs/Plans/PR-TRACKER-campaign-supergraph.md`
3. `Docs/Roadmaps/ROADMAP-campaign-supergraph.md`
4. `Docs/Design/STATUS-world-graph-continuity-spine.md`
5. `Docs/Plans/STEWARDS-ANCHOR-cutover.md`
6. `Docs/Plans/HANDOFF-CUTOVER-buddy-graph-engine-demolition.md`
7. `Docs/Plans/HANDOFF-CUTOVER-delete-legacy-graph-engine.md`
8. `Docs/Plans/HANDBACK-CUTOVER-D3B-physical-legacy-graph-engine-deletion.md`
9. GitHub truth for #667 and current Buddy `main`

Repository law is explicit: the cycle ends only when mutable repository authority agrees with the merge. With no suitable dependent CUTOVER implementation slice remaining, a **direct guarded steward sync** is the correct mechanism. Do not open a ceremonial docs-only PR.

### DungeonMind critique authority

1. `README.md`
2. `CONTRIBUTING.md`
3. `Docs/Architecture/ARCHITECTURE.md`
4. `Docs/Architecture/AUTHORITY.md`
5. accepted ADRs, especially `ADR-0022-independent-library-and-agent-harness-boundary.md`
6. `Docs/Roadmaps/ROADMAP.md`
7. `Docs/Reports/REPORT-2026-08-23-independent-library-transition.md`
8. current package tree, public exports, migrations, tests, benchmarks, and optional extras on exact `5ca5d688…`
9. Buddy `b667205f…` only as **read-only external-consumer evidence** for which DungeonMind seams the real client actually uses

Do not treat stale roadmap wording such as “R.3a current lane” as current repository truth. DungeonMind `main` is already `5ca5d688…` / PR #47. Part of the audit is identifying and correcting this kind of accumulated narrative drift.

---

## §3 Mission phases

This is a stewardship mission with multiple outputs, not a single merge-ready capability. Do not put all work below into one PR.

### Phase A — close CUTOVER repository state

Re-anchor Buddy at current `main` and perform one guarded synchronization of mutable CUTOVER authorities.

Minimum sync set to inspect and update together where they still claim live state:

```text
Docs/Plans/PR-TRACKER-campaign-supergraph.md
Docs/Sources/design-agent/ACTIVE_AUTHORITY/PR-TRACKER-campaign-supergraph.md
Docs/Roadmaps/ROADMAP-campaign-supergraph.md
Docs/Sources/design-agent/ACTIVE_AUTHORITY/ROADMAP-campaign-supergraph.md
Docs/Design/STATUS-world-graph-continuity-spine.md
Docs/Sources/design-agent/ACTIVE_REFERENCE/STATUS-world-graph-continuity-spine.md
Docs/Plans/STEWARDS-ANCHOR-cutover.md
Docs/Plans/HANDOFF-CUTOVER-buddy-graph-engine-demolition.md
Docs/Plans/HANDOFF-CUTOVER-delete-legacy-graph-engine.md
Docs/Plans/HANDBACK-CUTOVER-D3B-physical-legacy-graph-engine-deletion.md
```

Only change documents whose **current claims** changed. Historical narrative remains historical evidence.

Required closure truth:

```text
Buddy current main             b667205f2fb8c78ff7e91d113facba12e3339a4d
D.3B                           COMPLETE / MERGED
D.3                            DONE
CUTOVER                        CLOSED / terminal implementation state
pinned snapshot catch-up       SUPERSEDED / CLOSED; activation condition expired
DungeonMind living authority   unchanged
Buddy DungeonMind pin          5ca5d688612349034f8ca490d465af166d883e6e
```

The branch `cutover/design-pinned-snapshot-catchup` still exists. Do not delete it automatically: branch deletion is cleanup with destructive semantics and is not required for truthful state. Mark the path superseded in authority docs; branch removal may happen later with explicit approval.

### Phase B — capture the lessons from CUTOVER

Before criticizing DungeonMind, write down what the migration actually taught us. Use evidence, not generic software aphorisms.

At minimum preserve these lessons for the critique:

1. **Authority becomes real when clients accept its semantics.** R.3 disagreements were resolved by adapting Buddy to DungeonMind semantics instead of recreating Buddy compatibility.
2. **Evidence/provenance is knowledge semantics, not metadata.** Visibility, source lifecycle, revision identity, and evidence chains materially affect what a read is allowed to return.
3. **Exact immutable revision identity and head CAS paid for themselves.** Adoption, historical reads, governed publication, retry/recovery, and D₀/D_A continuity all used them.
4. **Fail-closed design is productive when it exposes real ownership mistakes.** The cutover repeatedly found hidden fallback paths, source-provenance ambiguity, and alternate-root assumptions that permissive behavior would have hidden.
5. **Runtime excision and physical deletion are different proof obligations.** D.3A proved the product did not need the engine; D.3B proved the engine was actually absent.
6. **Owning-boundary evidence matters.** Importability and helper tests were not enough; the blocker had to remain armed while Threat, worldbuilding, first-world, Graph Review, Hermes, and recovery actually executed.
7. **Compatibility layers accrue survival momentum unless deletion is planned.** `dungeonmind_kernel`, BuddyFiles adapters, lazy Kernel proxies, and historical test seams survived until a named demolition slice forced every consumer to declare a disposition.
8. **A real migration is a stronger architecture test than synthetic extensibility claims.** The useful abstractions are the ones that survived Eldyrwild, PostgreSQL, reload, retries, manual authoring, and client disagreement.
9. **One product does not prove a good library API.** DungeonMindBuddy proves authority and correctness, but it can also hide Buddy-shaped ceremony because both codebases evolved together.
10. **Pins create an unusually valuable experimentation boundary.** Once Buddy consumes an exact DungeonMind commit, DungeonMind can simplify or break on later branches without destabilizing Buddy. Repinning should be an explicit future adoption decision, not part of the audit.
11. **Review-cycle telemetry improved the handoffs.** D.3 design needed seven formal cycles, D.3A three, D.3B two. Do not optimize for the count; use the trend to ask which invariants became clearer and which finding classes repeated.
12. **Versioned correctness machinery has a cost.** V1/V2/V3/V4 contracts, receipts, migrations, repairs, and compatibility paths may be essential history or may now be residue. The audit must distinguish those cases rather than preserving everything because it once mattered.
13. **Product/harness and knowledge authority are now separable in practice.** DungeonMind should not absorb Agent Surface, Hermes/Pi orchestration, selected-text context, conversation state, or product-wide token budgeting merely because Buddy uses them next to graph reads.

Add lessons if the repository evidence supports them. Do not inflate this into a generic retrospective.

### Phase C — bottom-up DungeonMind audit

Start from the code and persistence reality on exact `5ca5d688…`.

Produce an inventory that covers at least:

#### C.1 Package and dependency topology

Map:

```text
src/dungeonmind/contracts
src/dungeonmind/domain
src/dungeonmind/application
src/dungeonmind/infrastructure
src/dungeonmind/service
src/dungeonmind/agents (if present)
src/dungeonmind_dnd/**
```

For each top-level subsystem record:

- public exports;
- inward/outward imports;
- optional dependency requirements;
- named current consumers;
- tests that actually exercise it;
- persistence/migration coupling;
- conceptual responsibility.

Validate the documented layering against the actual import graph. Treat `CONTRIBUTING.md` rules as claims to verify, not proof by themselves.

#### C.2 Public API reality

Inventory what a consumer must import to perform the core library jobs:

```text
select/read world head
project exact revision
search
get object
get neighborhood
evidence
source-anchor identity/revalidation
prepare/finalize governed contribution
publish exact-parent child
recover/retry publication
initialize a new world
```

Distinguish:

- intentionally public application services;
- contracts exposed because history required them;
- infrastructure types leaking into callers;
- internal objects imported by Buddy because there was no cleaner seam.

A public API is not “whatever is importable.”

#### C.3 Contract/version archaeology

Inventory generations of:

- graph snapshot/revision contracts;
- source/evidence contracts;
- adoption receipts and repairs;
- contribution/review/publication contracts;
- semantic profiles/vocabularies;
- read/projection/retrieval requests/results;
- errors.

For every retained old generation ask:

```text
Is it needed to read durable historical state?
Is it needed only by a migration that has completed?
Is it still exported publicly?
Could it be quarantined behind a compatibility loader?
Would deleting it make a live DB unreconstructable?
```

Do not delete durable-history support merely because the current consumer uses the newest version.

#### C.4 Persistence and migration audit

Walk the PostgreSQL schema and Alembic history from the bottom up:

- current tables and indexes;
- repository protocols vs actual adapter shape;
- transaction/CAS boundaries;
- immutable vs mutable records;
- migration-only columns/tables;
- source/provenance query patterns;
- indexes justified by current reads;
- test-only/in-memory semantic mismatches.

Ask whether the persistence model expresses the domain cleanly or whether migration history has become the architecture.

Do not mutate the live Eldyrwild database during this critique.

#### C.5 Read-path cost and complexity

R.3a demonstrated that a coherent read context could move real projection from ~20.7s to ~115ms without a broad cross-request scoped cache. Preserve that lesson.

Inspect:

- read-context lifetime;
- source/provenance snapshot semantics;
- parsing/cache ownership;
- search and anchor secondary costs;
- repeated object/materialization transformations;
- DTO conversion layers;
- current performance instrumentation.

Do not add new indexes/caches because they are conventional. Add them only if current measurements still identify a problem.

#### C.6 Founding-era agent/context machinery

Give unusually hard scrutiny to the areas already named by DungeonMind's own architecture-fitness roadmap:

- MindTurn orchestration;
- retrieval session/thread ownership;
- context assembly/budgeting;
- claim ledger / answer validation;
- `agents/` adapters;
- semantic-document / embedding machinery;
- duplicate generations of services/contracts retained from the founding ladder.

For each, identify a named independent-library consumer or classify the subsystem honestly.

The existence of tests is not itself proof that the responsibility belongs in the library.

#### C.7 Testing, tooling, and operational surface

Map:

- unit vs integration vs conformance tests;
- in-memory/PostgreSQL parity expectations;
- fixture duplication;
- migration/conformance scripts that should remain executable;
- benchmarks that still describe current behavior;
- optional extras and dependency weight;
- service/API adapters;
- logging/observability;
- packaging/versioning/release ergonomics.

Look specifically for stale tests whose main job is preserving a retired migration path rather than a durable contract.

### Phase D — top-down redesign critique

Now ignore the existing package structure temporarily.

Start from the north star:

> **DungeonMind is a small, trustworthy, extensible library for durable world knowledge. It owns knowledge semantics; clients own what users do with that knowledge.**

Design the smallest system you would build today to satisfy the evidence-backed capabilities.

At minimum answer:

#### D.1 Domain model

What are the irreducible concepts?

Likely candidates to challenge, not assume:

```text
World
PublishedRevision / Head
SourceArtifact / SourceRevision
EvidenceRef / SourceAnchor
SemanticProfile
Scope / Admissibility
GraphProjection
Contribution
Review / Finalization
Publication / Recovery
Initialization / Adoption
```

Which are true domain concepts, which are transport DTOs, and which exist because the migration needed them?

#### D.2 Ideal client surface

Sketch the API a second consumer should want to use.

A client should not need to understand Buddy history, adoption repair chronology, repository bundle construction, PostgreSQL adapter details, or internal version ladders for normal current operations.

Ask whether we want a small facade such as explicit read/write/init service sets, or whether the existing application-service surface is already good enough. Do not invent a facade merely for aesthetics; prove what ceremony it removes.

#### D.3 Ownership boundaries

Re-justify or reject each major responsibility:

- durable graph identity;
- provenance/evidence;
- scope/admissibility;
- semantic profiles;
- retrieval;
- governed publication;
- source-body handling;
- agent/session/context concepts;
- embeddings/semantic documents;
- transport hosts;
- operational lifecycle.

Anything that belongs to the client should move or disappear rather than becoming a “generic” library abstraction.

#### D.4 Extensibility

Evaluate whether the generic/profile split is genuinely extensible or merely D&D-shaped with indirection.

Do not create a second abstract taxonomy. Use a tiny second-profile or second-client probe only if it answers a concrete question.

#### D.5 Operational model

Ask what “independent library” means operationally:

- embedded in-process library first?
- optional service host?
- PostgreSQL required only for durable production adapter?
- clean in-memory test/reference implementation?
- migration/version policy?
- observability without becoming a platform?

Keep deployment ownership outside the core library unless evidence says otherwise.

#### D.6 Counterfactual test

For every subsystem ask:

> **If this did not exist today, would we build it again to support the consumers and correctness properties we now have?**

If yes, explain why.

If no, ask whether it enables a concrete imminent extension. If neither is true, it is a simplification candidate.

### Phase E — synthesis and successor decomposition

Classify every meaningful subsystem using the existing DungeonMind architecture-fitness vocabulary:

```text
ESSENTIAL COMPLEXITY
PRODUCTIVE ABSTRACTION
UNPROVEN ABSTRACTION
ACCIDENTAL COMPLEXITY
HISTORICAL RESIDUE
```

For each classification record:

- evidence;
- named consumer;
- cost;
- failure prevented / value created;
- recommended disposition;
- confidence;
- reversal path.

Then produce three views:

1. **Keep / protect** — mechanisms that survived real authority pressure and should not be casually simplified.
2. **Measure / probe** — plausible value that lacks enough evidence.
3. **Collapse / move / delete** — complexity with no current independent-library justification.

Finally author a small PR ladder. Each implementation successor must be independently useful and revertible. Examples may include:

```text
L.1A retire founding agent/session ownership
L.1B quarantine historical adoption/migration compatibility
L.1C consolidate public read service entry points
L.1D consolidate governed write/init entry points
L.2 smallest independent client ergonomics probe
L.3 public contract/versioning cleanup
```

These names are illustrative, not pre-decisions. Let the critique determine the real decomposition.

---

## §4 Critique deliverables

The primary DungeonMind output should be a durable report, suggested path:

```text
Docs/Reports/REPORT-2026-08-30-bottom-up-top-down-library-critique.md
```

It must include:

1. exact repo/head and verification baseline;
2. current package/dependency diagram;
3. public API consumer map;
4. persistence/migration map;
5. contract/version archaeology;
6. bottom-up subsystem findings;
7. top-down minimum-library design;
8. actual-vs-target delta;
9. architecture-fitness classification ledger;
10. CUTOVER lessons that materially influence the critique;
11. “what I would not touch” list;
12. “what I would delete/collapse first” list;
13. evidence gaps / experiments needed;
14. proposed successor PR ladder;
15. explicit non-goals.

Also update DungeonMind roadmap/architecture/README only where the critique proves their **current claims** are stale or changes an accepted direction. Stable authorities do not churn for ceremony.

A useful critique should make it possible for a future steward to answer, in a few minutes:

```text
What is DungeonMind for?
What is its smallest trustworthy core?
Which complexity has earned its place?
Which complexity exists because of history?
What should we test before deleting more?
What are the next 2–5 bounded PRs?
```

---

## §5 Verification baseline

Before critique-driven edits in DungeonMind, record the clean baseline on exact `5ca5d688…`.

At minimum:

```bash
uv sync --locked
uv run pytest -m "not integration"
uv run ruff check .
uv run pyright
```

When PostgreSQL is available:

```bash
uv sync --locked --extra postgres --extra api
docker compose -f compose.postgres.yml up -d
uv run alembic upgrade head
uv run pytest -m integration
```

Record exact pass/fail/skip counts and existing failures. Do not silently repair baseline failures while trying to characterize architecture.

For each proposed deletion/collapse experiment, run the narrow owning tests plus the broad non-integration floor. Persistence/public-contract changes require PostgreSQL evidence before merge.

Buddy is **not** an automatic regression target for every DungeonMind experiment because Buddy is pinned to the old commit. Only a future explicit repin/adoption PR needs to prove Buddy compatibility with the new DungeonMind head.

---

## §6 Safety boundary: use the pin, do not break it

Buddy currently declares exactly:

```text
dungeonmind[postgres] @ git+https://github.com/Drakosfire/DungeonMind.git@5ca5d688612349034f8ca490d465af166d883e6e
```

That pin is the experiment firewall.

During the critique and its DungeonMind-only successor PRs:

- do not edit Buddy product code;
- do not change Buddy's DungeonMind pin;
- do not add a temporary compatibility path to Buddy;
- do not make DungeonMind import Buddy;
- do not use Buddy's current behavior as the only acceptance oracle;
- do use Buddy `b667205f…` read-only to identify actual external consumers and accidental API leakage.

A future Buddy repin is a separate, explicit integration decision with its own handoff and evidence. It should consume a coherent DungeonMind milestone, not chase every cleanup commit.

This allows DungeonMind to make breaking internal changes, remove dead APIs, or reshape experimental public seams on its own branches while Buddy continues operating against `5ca5d688…`.

Do not confuse “safe to experiment” with “safe to destroy durable compatibility.” Historical persisted data and intentionally versioned public contracts still require explicit migration/deprecation reasoning inside DungeonMind.

---

## §7 Stop conditions

Stop and report rather than proceeding when:

1. Buddy `main` has moved and another active lane now owns one of the CUTOVER closure documents.
2. #666 or another active Buddy PR would be overwritten rather than cleanly rebased/composed after #667.
3. CUTOVER closure discovers a product/runtime dependency on a deleted Buddy graph package. That is a regression, not bookkeeping.
4. DungeonMind critique discovers that a proposed deletion is required to read current durable PostgreSQL state or historical revisions.
5. A simplification requires a new durable schema/public contract and the critique has not yet decomposed it into a bounded PR.
6. A subsystem appears unused only because current tests/exports hide dynamic loading, service entrypoints, migrations, or external use.
7. An experiment requires changing the Buddy pin to learn whether the DungeonMind design is coherent. Prefer a tiny independent client or local compatibility probe first.
8. A “generic” abstraction is being invented without a second concrete consumer/profile.
9. The critique starts optimizing for fewer files/classes rather than lower total conceptual/runtime/maintenance/client cost.
10. Any work would mutate the live Eldyrwild database without a separately explicit governed operation.

---

## §8 Steward handback requirements

The steward returns one consolidated handback with two repository sections.

### DungeonMindBuddy closure

Record:

- pre-sync `main`;
- post-sync `main`;
- exact files synchronized;
- #667 accepted head / merge / review-cycle count / PASS review;
- D.3 and CUTOVER terminal state;
- pinned snapshot catch-up disposition;
- mirror equality checks;
- #666 composition/rebase status, without taking ownership of its AGENT-INTERACTION semantics.

### DungeonMind critique

Record:

- base/head/branch/PR state;
- exact verification baseline;
- report path;
- architecture-fitness ledger summary;
- highest-confidence keep/delete/probe conclusions;
- top-down target architecture summary;
- bottom-up hotspots;
- open evidence gaps;
- proposed successor slices;
- what remains false;
- explicit statement that Buddy remains pinned to `5ca5d688…` unless a separately reviewed repin occurred.

Do not end the handback with “clean up DungeonMind.” End it with a small, named, evidence-backed next sequence or with an explicit conclusion that no change is currently justified.

---

## §9 Definition of done for this steward mission

This stewardship mission is complete when all of the following are true:

```text
Buddy mutable CUTOVER authority          truthful after #667
D.3                                      DONE
CUTOVER                                  CLOSED
conditional snapshot-catchup path        SUPERSEDED / CLOSED
#666 collision consequence               explicitly handed back to its owner

DungeonMind baseline                     measured at exact starting head
CUTOVER lessons                          captured as architecture evidence
bottom-up code/persistence audit         complete
top-down minimum-library critique        complete
subsystem classification ledger          complete
critique report                           durable in DungeonMind
future Buddy pin                         unchanged during critique
successor work                            decomposed into small DungeonMind slices
```

The final mindset shift is intentional:

> **Stop asking whether DungeonMind can replace Buddy's old graph engine. It already did. Start asking whether DungeonMind, standing on its own, is the library we would choose to build now.**
