---
pr_body_template: |
  ## Handoff pointer
  - Conversation/workstream: DOGFOOD-CONTINUITY / DFC-3
  - Flow: DOGFOOD-CONTINUITY
  - Direction: DESIGN → CODE → REVIEW
  - Handoff: `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-c1-c2-demo-readiness-survey-v1.md`
  - Branch / PR: `agent/dogfood-continuity-c1-c2-demo-readiness-survey-v1` / `DOGFOOD-CONTINUITY: survey C1/C2 demo readiness`

  ## Verification pointer
  - Base: `678e9c276ad58505c53ce61d5a659ea8c792ca31`
  - Changed paths: HANDOFF §4
  - Verification: HANDOFF §7

  The checked-in handoff, cumulative diff, numbered review handback, and independently
  rerun evidence are the review contract. This body is transport metadata.
---

# HANDOFF — C1/C2 Demo Readiness Survey v1

**Created:** 2026-09-06  
**Status:** ACTIVE — steward-designated reconnaissance slice  
**Canonical handoff path:** `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-c1-c2-demo-readiness-survey-v1.md`  
**Conversation/workstream:** `DOGFOOD-CONTINUITY / DFC-3`  
**Flow / owner:** `DOGFOOD-CONTINUITY`  
**Direction:** DESIGN → CODE → REVIEW  
**Base revision:** `678e9c276ad58505c53ce61d5a659ea8c792ca31`  
**PR title:** `DOGFOOD-CONTINUITY: survey C1/C2 demo readiness`

> Repository law: [`AGENTS.md`](../../AGENTS.md). Steward process: [`Docs/Process/STEWARD-CYCLE.md`](../../Docs/Process/STEWARD-CYCLE.md). External PR mechanics: [`.cursor/skills/external-agent-pr-loop/SKILL.md`](../../.cursor/skills/external-agent-pr-loop/SKILL.md).

## §0 Steward ruling

The next forcing function is no longer another storage-class recovery PR.

The product-readiness question is:

> **Can a human turn DungeonBuddy on and pleasantly inhabit the existing Campaign 1 and Campaign 2 body of work—especially historical recap review—without knowing its internal architecture?**

C1/C2 are the acceptance corpus. They must be used as they already exist. This slice does **not** authorize starting ingestion over, regenerating historical artifacts, inventing replacement content, or using Of Conks and Cons as the target corpus.

Of Conks and Cons may be inspected only as **prior UI/design evidence**, especially for richer entity pills, node interactions, Threat projection, and statblock styling that should inform the normal product experience.

This PR is intentionally reconnaissance/documentation-only. Its useful product is a trustworthy map of what exists, what is usable, what is stranded, and what blocks the human demo.

---

## §1 Mission and merge-ready invariant

**Mission:** The steward can choose the next demo-readiness implementation slices from a reproducible, evidence-backed survey of existing C1/C2 material, current UX, persistence authority, and cross-surface capability rather than architectural assumptions.

**Merge-ready invariant:**

> Every material/readiness claim is grounded in current APP-STATE, the current assembled product, the controlled DungeonMind boundary, exact surviving historical evidence, or clearly labelled code/test evidence. No historical work is regenerated, silently repaired, mutated, or promoted from assumption to fact.

### Pre-dispatch critique

| Question | Answer |
| --- | --- |
| Can one invariant govern every claimed observable path? | Yes. This is reconnaissance only: truthful evidence and inventory, no product repair. |
| Most likely adversarial sequence | Catalog/metadata says material exists → agent assumes it is usable → report marks it ready without actually opening it in the assembled UI. |
| Will §7 detect that failure? | Yes. Major demo capabilities require assembled browser dogfood and explicit evidence provenance. |
| Easiest owning boundary to under-test | Historical recap UX: run identity may exist in APP-STATE while source/artifacts/pills/node interaction are unusable. |
| Fact that forces stop/split | Any proposed fix, migration, artifact adoption, re-ingestion, UI change, status mutation, or new product contract. Report it; do not implement it. |

---

## §2 Context, authority, and lane

| Field | Required content |
| --- | --- |
| Parent authority | `Docs/Roadmaps/ROADMAP-con-ready.md`; `Docs/Plans/STEWARDS-ANCHOR-con-ready.md`; current Surface/Play/Agent design authorities |
| Base revision | `678e9c276ad58505c53ce61d5a659ea8c792ca31` |
| Predecessor contract | DFC-1 historical inventory; DFC-2a exact Plan adoption; DFC-2c / PR #686 exact historical Ingest run adoption |
| DFC-2c accepted state | PR #686; accepted head `2a088c4b357a5bc43635fd31aefad42f4b5d4e95`; merge `678e9c276ad58505c53ce61d5a659ea8c792ca31`; 2 review cycles |
| Exact inputs consumed | Current configured Buddy APP-STATE; current UI/API on `main`; known historical roots from DFC-1; current C1/C2 source/artifact material; DungeonMind only through its controlled Buddy-facing contract |
| Named successor | One or more implementation slices selected from this survey; expected candidates include rich recap restoration and persistent shell navigation, but this PR does not pre-decide them |
| What remains false | No UX, artifact, persistence, navigation, Agent, recap, Build, Plan, Play, or World-context defect is repaired here |
| Explicit non-goals | No production code; no migrations; no imports/adoptions; no re-ingestion; no graph mutation; no Runbook/Plan recovery; no artifact copying; no UI styling changes; no router/AppChrome changes; no Agent changes; no Of Conks content work |
| Branch / isolated checkout | `agent/dogfood-continuity-c1-c2-demo-readiness-survey-v1` + isolated worktree/equivalent |
| Parallel lanes / collision hotspots | No open PR observed at dispatch; rerun steward preflight. Real local APP-STATE and external DungeonMind services are shared runtime authorities and must be treated read-only. |
| Runtime/state ownership | Real C1/C2 authority is observational/read-only. Use disposable state for any write-path verification. Never alter historical campaign material merely to prove a capability. |
| State-authority sync set after merge | DFC-2c handoff/report acceptance state; `ROADMAP-con-ready.md`; `STEWARDS-ANCHOR-con-ready.md` |

Read current authority and predecessor evidence before surveying. Do not restart DFC-1 archaeology from zero.

Primary predecessor evidence:

- `Docs/Reports/REPORT-dogfood-continuity-historical-material.md`
- `Docs/Reports/REPORT-dogfood-continuity-plan-exact-adoption.md`
- `Docs/Reports/REPORT-dogfood-continuity-ingest-manifest-adoption.md`

---

## §3 Required fact-finding

### 3.1 Human demo journey

Exercise the current assembled product as a user:

```text
start DungeonBuddy
→ establish Campaign 1 / Campaign 2 context
→ review historical recap
→ navigate between prior sessions
→ interact with prose / pills / nodes / related objects
→ inspect Threat / statblock treatment
→ move between Plan / Build / Ingest / Play
→ inspect existing material
→ determine edit/save capability
→ observe World context
→ observe Agent availability/context
→ reload/restart where relevant
```

The report must distinguish **architecturally present** from **human-usable today**.

### 3.2 Rich recap review — highest-priority survey

This requires the most detail.

Use real C1/C2 sessions, including at minimum:

- `longmont-c1 / session-10`
- `longmont-c2 / session-23`
- `longmont-c2 / session-25` — known current example of catalog-visible `validated` history that dead-ends in the review resolver
- one additional C1/C2 session selected because it exposes the richest surviving recap/entity interaction

For historical recap UX, establish independently:

| Capability | Question |
| --- | --- |
| Recap prose | Can the user read the actual historical recap comfortably? |
| Session navigation | Can they move previous/next or among sessions without reconstructing IDs? |
| Entity pills | Are entity-linked terms rendered? From what data? |
| Pill styling | What current styling exists? What stronger styling previously existed? |
| Pill interaction | Hover/click/selection behavior? |
| Node/object detail | Does interaction open useful graph/object information? |
| Provenance | Can the user connect graph understanding back to recap text/source? |
| Threat projection | Does a Threat project differently/usefully from generic entities? |
| Statblock treatment | Locate the richer statblock-style projection previously built, including exact current/historical component/file/commit evidence and whether it remains connected |
| Existing extraction review | Can previously ingested candidate/review material actually be inspected? |
| Review/correction | What can a human currently approve/correct/reject? |
| Agent | Can Agent reason about the current recap, entity, or selected text? |
| Persistence | What recap/review resources depend on local files rather than durable authority? |

Do **not** repair any failure found here.

### 3.3 Surface readiness

Survey all four existing primary surfaces.

For each of **Plan / Build / Ingest / Play**, report:

```text
historical C1/C2 material exists?
visible in product?
openable?
readable?
editable?
save path exists?
save path live-proven?
reopen after save?
hard reload behavior?
API restart behavior where relevant?
World/context projection present?
Agent present?
Agent receives useful current context?
important local-filesystem dependency?
main user-visible blocker?
```

Historical write assertions require provenance:

- `LIVE-READ` — observed against real C1/C2 authority without mutation
- `ISOLATED-WRITE` — exercised safely against disposable authority
- `TEST-PROVEN` — owning-boundary test exists/passes
- `CODE-ONLY` — implementation appears to exist but was not exercised
- `UNKNOWN` — insufficient evidence

Do not call something “ready” from `CODE-ONLY`.

### 3.4 World / DungeonMind continuity

DungeonMind cutover is complete.

Buddy must not gain direct graph-architecture ownership during this survey.

Establish through the current controlled contract:

- whether C1 and C2 World content is available now;
- whether Buddy surfaces can query/use it;
- where the current visible “Graph” error originates;
- which surfaces currently project useful World context;
- whether recap pills/nodes use current World authority or historical/local artifacts;
- whether relevant NPC/place/threat information can be opened from normal product use.

Do not mutate DungeonMind or bypass its controlled contract to make Buddy appear healthy.

### 3.5 Persistent application shell

Exercise normal navigation among:

```text
Plan → Build → Ingest → Play → Plan
```

Report:

- whether navigation causes full document reload;
- which UI/providers/state are destroyed and remounted;
- whether campaign/session/object context survives;
- whether Agent continuity survives;
- exact current files/components responsible;
- existing design/code already intended to solve it.

Do not implement DFC-NAV1 here.

### 3.6 Agent readiness

For each primary surface determine:

- Agent affordance visible?
- same shared provider or surface-specific implementation?
- current campaign available?
- current session available?
- current object/revision available?
- selected text/object available?
- World context available?
- can Agent only answer, or also propose writes?
- what write approval boundary exists?
- does surface navigation lose Agent state/context?

The goal is to tell the steward how far we are from:

> “Use the Agent naturally from every surface.”

Not to implement it.

### 3.7 Persistence and VPC-readiness inventory

For every dependency exercised by the demo journey, classify current authority:

```text
APP-STATE PostgreSQL
DungeonMind controlled remote/service authority
Git-tracked file
local untracked artifact
repo-relative out/
browser local/session storage
generated/transient state
unknown
```

Explicitly identify anything that prevents this future claim:

> “The laptop no longer owns the durable reading/writing state; PostgreSQL + durable artifact storage can be remotely hosted and backed up.”

Do not design or implement the VPC deployment in this PR.

---

## §4 Files in scope — write lease

| Action | Path | Purpose |
| --- | --- | --- |
| Create | `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-c1-c2-demo-readiness-survey-v1.md` | Slice authority |
| Create | `Docs/Reports/REPORT-c1-c2-demo-readiness.md` | Point-in-time readiness findings and recommended decomposition |
| Create | `Docs/Operations/CAMPAIGN-MATERIAL-LIBRARY-c1-c2.md` | Transitional live library/recovery ledger for existing C1/C2 material |
| Modify | `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-ingest-manifest-adoption-v1.md` | Backward-only DFC-2c acceptance/merge sync |
| Modify | `Docs/Reports/REPORT-dogfood-continuity-ingest-manifest-adoption.md` | Record exact DFC-2c steward acceptance |
| Modify | `Docs/Roadmaps/ROADMAP-con-ready.md` | Record DFC-2c complete and make this survey the active forcing function |
| Modify | `Docs/Plans/STEWARDS-ANCHOR-con-ready.md` | Re-anchor current state and active survey |

If `Docs/Operations/` does not yet exist, creating the directory to contain the one declared library file is within lease.

### Discovery authority

Read-only discovery is intentionally broad:

```text
Current repository and Git history
Current configured APP-STATE
Known DFC-1 historical roots
Current assembled Buddy UI/API
Controlled DungeonMind Buddy-facing contract
Existing worktrees/branches when needed to locate exact prior UI/material evidence
```

Read-only discovery does not grant a write lease.

No additional committed path is allowed without steward rebrief.

---

## §5 Explicitly out of scope / collision boundary

| Path | Why this slice must not touch or claim it |
| --- | --- |
| `apps/**` | No product implementation in reconnaissance PR |
| `src/**` | No product implementation in reconnaissance PR |
| `scripts/**` | No product implementation in reconnaissance PR |
| `tests/**` | No product implementation in reconnaissance PR |
| `src/application_state/migrations/**` | No schema changes |
| historical artifact roots | Evidence only; never mutate |
| DungeonMind data/graph internals | Controlled contract only; no graph writes |
| Plan/Build/Ingest/Runbook importers | No adoption or recovery writes |
| AppChrome/router/navigation | Survey only |
| Agent implementation | Survey only |
| recap resolver/promotion logic | Survey only |
| Of Conks and Cons material | Not target corpus |
| BF3B / Combat | Not part of current readiness survey except where existing UI visibly intersects |

Temporary local commands/files under ignored `out/` are allowed for evidence capture only and must not become product authority.

---

## §6 Output contracts

### 6.1 `CAMPAIGN-MATERIAL-LIBRARY-c1-c2.md`

Header must state:

```text
Status: ACTIVE TRANSITIONAL RECOVERY LIBRARY

Purpose:
Keep a durable human-readable locator for existing C1/C2 material until
APP-STATE + durable artifact storage + remote hosting + backup/redundancy
make this ledger unnecessary.

This file is not product authority and does not authorize reconstruction
or mutation. It records where exact material currently survives.
```

Use stable root aliases plus repo-relative/URI locators rather than machine-specific home-directory paths where possible.

Minimum fields:

| Field |
| --- |
| Campaign |
| Session / campaign-level scope |
| Material type |
| Human title/description |
| Stable ID if one exists |
| Current product authority |
| Root/source label |
| Exact relative path / URI / DB identity |
| Digest/fingerprint if available |
| Git-tracked / DB / local-only |
| Owning surface |
| Visible in product? |
| Openable? |
| Interaction level |
| Redundancy posture |
| Evidence provenance |
| Known blocker / notes |

Material types should include, where evidence exists:

- recap/source;
- Ingest run;
- candidate/review artifact bundle;
- Plan;
- Build/worldbuilding source;
- Runbook/Playable material;
- Play Run/runtime state;
- significant source documents/assets needed to make those useful.

Do **not** enumerate every World graph node. World object availability belongs in the readiness report unless a distinct durable artifact needs a recovery locator.

Use explicit states such as:

```text
PRODUCT_READY
OPENABLE_PARTIAL
CATALOG_ONLY
STRANDED_EXACT
MISSING_BYTES
NOT_ADOPTED
UNKNOWN
```

Never convert `UNKNOWN` into `MISSING` merely because the current checkout lacks a file.

### 6.2 `REPORT-c1-c2-demo-readiness.md`

The report begins with a compact readiness scorecard:

| Demo element | Readiness | Live evidence | Existing implementation | Existing C1/C2 material | Primary blocker | Likely repair shape |
| --- | --- | --- | --- | --- | --- | --- |

Required demo elements:

1. campaign/session discovery;
2. rich historical recap reading;
3. session-to-session recap navigation;
4. entity pills and node/object interaction;
5. Threat/statblock projection;
6. historical Ingest inspection/review;
7. Plan historical open/edit/save;
8. Build historical open/edit/save;
9. Play/Runbook historical open/edit/run/resume;
10. World context across surfaces;
11. persistent no-reload application shell;
12. Agent on Plan;
13. Agent on Build;
14. Agent on Ingest/recap;
15. Agent on Play;
16. reload/restart durability;
17. VPC/off-hardware data readiness.

Use readiness labels:

```text
READY
USABLE_WITH_GAPS
DISCOVERABLE_NOT_USABLE
NOT_CONNECTED
BLOCKED_BY_MISSING_MATERIAL
UNKNOWN
```

For every non-READY row, name the **first user-visible failure**, not merely an architectural deficiency.

The report must end with:

### Proposed implementation sequence

Rank the smallest next implementation slices by impact on this target:

> A human can pleasantly use the existing C1/C2 corpus end-to-end.

Do not automatically inherit old DFC-2b/BF3B sequencing.

Each proposed slice must state:

```text
user-visible outcome
evidence that justifies it
likely owning boundary
what remains false afterward
collision/ordering dependency
```

This is recommendation only. Do not author successor handoffs in this PR.

---

## §7 Evidence required to merge

| Guarantee | Evidence |
| --- | --- |
| Survey ran against exact current `main` | exact SHA recorded |
| APP-STATE authority identified correctly | DSN/database/schema status without secrets |
| Existing C1/C2 DB material counted | exact Plan/Runbook/Ingest/Play counts |
| Historical Ingest continuity represented truthfully | current 53-run state and actual openability/reviewability distinguished |
| Rich recap UX surveyed | assembled browser evidence on required representative sessions |
| Historical material inventory is actionable | exact root alias + locator + identity/digest where available |
| Current World availability surveyed | Buddy-facing DungeonMind contract evidence |
| Plan/Build/Ingest/Play surveyed | actual routes + evidence provenance |
| Navigation reload behavior established | assembled Plan→Build→Ingest→Play navigation witness |
| Agent readiness established | per-surface provider/context evidence |
| Persistence/VPC blockers established | every demo dependency classified by durable authority/storage location |
| No product/history mutation | git diff plus before/after relevant authority counts/fingerprints |
| No re-ingestion | no new historical ExtractionRun identity and no historical ingestion pipeline invocation |

### Required live dogfood

At least one assembled browser pass is mandatory.

Record exact observations for:

```text
C1 Session 10 recap/history
C2 Session 23 recap/history
C2 Session 25 recap/history
one additional rich-interaction session

Plan
Build
Ingest
Play

Plan → Build → Ingest → Play → Plan navigation
```

If browser access is unavailable, stop rather than claiming UI readiness from code inspection alone.

### Real-state mutation rule

The configured C1/C2 authority is read-only for this survey.

For edit/save claims:

- use a disposable authority if safely available;
- otherwise rely on owning-boundary tests/code and label the claim accordingly;
- never alter real campaign prose, status, graph state, Runbooks, Plans, or Ingest lifecycle merely to produce evidence.

### Verification commands

At minimum:

```bash
git rev-parse HEAD
uv run python scripts/steward_preflight.py \
  --handoff Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-c1-c2-demo-readiness-survey-v1.md

git diff --check
git diff --name-only 678e9c276ad58505c53ce61d5a659ea8c792ca31...HEAD
```

Run any existing focused tests/commands needed to validate a readiness assertion, but do not add or modify tests in this slice.

---

## §8 Required review handback

Report:

1. `Review Cycle <N>` and exact PR/head SHA;
2. confirmation that this remained reconnaissance-only;
3. exact runtime authority coordinates used;
4. exact C1/C2 material counts and inventory totals;
5. assembled recap-review findings;
6. Plan/Build/Ingest/Play readiness summary;
7. World/DungeonMind projection findings;
8. navigation findings;
9. Agent findings;
10. persistence/VPC-local dependency findings;
11. actual changed paths vs §4;
12. any material/root that could not be inspected;
13. evidence provenance gaps;
14. proposed next slices ranked by human-demo value;
15. confirmation that no historical content was regenerated/reingested/mutated.

---

## §9 Acceptance rubric

- [ ] DFC-2c is truthfully synchronized as accepted/merged.
- [ ] C1/C2—not Of Conks—is the surveyed acceptance corpus.
- [ ] The assembled product was actually dogfooded.
- [ ] Historical recap review received detailed treatment.
- [ ] The richer prior pill/Threat/statblock UX was located and its current connectivity established.
- [ ] Plan, Build, Ingest, and Play each have a readiness disposition.
- [ ] Agent readiness is reported for every primary surface.
- [ ] full-page reload/navigation behavior is demonstrated, not inferred.
- [ ] World availability is checked only through the controlled Buddy-facing DungeonMind boundary.
- [ ] The campaign material library contains actionable exact locators rather than vague prose.
- [ ] Local-only/unredundant material is explicitly identified.
- [ ] Every “ready” claim has live or owning-boundary evidence.
- [ ] No real C1/C2 material was mutated.
- [ ] No historical ingestion was rerun.
- [ ] No product implementation was smuggled into the reconnaissance PR.
- [ ] The report provides a ranked, evidence-driven next implementation sequence.

## Stop conditions

Stop and report instead of fixing when:

- historical material needs copying/adoption;
- a DB/schema migration appears necessary;
- recap review requires resolver changes;
- a UI component needs rewiring/restyling;
- AppChrome/router work is required;
- Agent context/public contracts need changes;
- Build/Plan/Runbook recovery requires writes;
- DungeonMind requires direct graph access;
- any historical source would need regeneration or re-ingestion;
- a new durable product contract appears necessary.

The expected response to a discovered product failure is:

```text
Observed user failure:
Existing material/evidence:
Owning boundary:
Current authority:
Why it is not usable:
Likely repair shape:
Candidate successor:
```

Not a fix.
