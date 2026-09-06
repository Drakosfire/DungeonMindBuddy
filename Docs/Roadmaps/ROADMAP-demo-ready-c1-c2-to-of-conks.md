# DEMO-READY — C1/C2 to Of Conks and Cons

**Status:** ACTIVE EXECUTION ROADMAP  
**Parent:** [`ROADMAP-con-ready.md`](ROADMAP-con-ready.md)  
**Created:** 2026-09-06  
**Repository:** `Drakosfire/DungeonMindBuddy`  
**Starting `main`:** `823d9d4121c4534be64bf3de620b24446b2b18ab` — DFC-3 / PR #687 merged  
**Evidence:** [`../Reports/REPORT-c1-c2-demo-readiness.md`](../Reports/REPORT-c1-c2-demo-readiness.md)  
**Recovery ledger:** [`../Operations/CAMPAIGN-MATERIAL-LIBRARY-c1-c2.md`](../Operations/CAMPAIGN-MATERIAL-LIBRARY-c1-c2.md)

This roadmap is the current execution sequence for getting DungeonBuddy **human-demo ready** and therefore ready to begin serious Of Conks and Cons dogfood. It supersedes older automatic sequencing such as “resume DFC-2b” or “resume BF3B” for this period.

The acceptance corpus is **Longmont Campaign 1 and Campaign 2**. Of Conks and Cons is not the test fixture for repairing continuity.

---

## 0. Target

The target is not “all architecture complete.”

The target is:

> **A human who did not build DungeonBuddy can open the application, inhabit the existing C1/C2 corpus, review prior recaps as rich interactive documents, move naturally across surfaces without losing context, edit/save real material, use World context and the Agent from the surface they are already in, reload/restart without losing work, and do this without depending on a particular laptop checkout.**

When that is true, Of Conks and Cons should enter the product as another real corpus—not as a heroic integration project.

### Demo-ready means, at minimum

1. Historical C1/C2 recaps are readable in-product.
2. Prior sessions are easy to navigate.
3. Recap prose supports entity pills, object inspection, provenance, and useful Threat/statblock projection.
4. DungeonMind World context is available through the controlled Buddy-facing contract.
5. Plan / Build / Ingest / Play feel like one application, not four page loads.
6. Existing recoverable material opens in its owning surface; current authoring works where no historical material survives.
7. Meaningful edits save and reopen.
8. Agent follows campaign/session/surface/object/selection context and exposes useful observability.
9. Durable state and artifact bytes are no longer owned by `/home/...`, one worktree, browser-only state, or an ephemeral local database.
10. The same trusted C1/C2 dogfood journey still works after the durable authorities move off the laptop.

This does **not** mean the convention product is finished. BF3B, Combat, and additional Play capability may still remain after this roadmap. This roadmap gets us to a trustworthy platform on which Of Conks can be dogfooded without special treatment.

---

## 1. Starting truth from DFC-3

DFC-3 / PR #687 established the following current product truth:

- `53` historical C1/C2 `ingest.run` rows are discoverable in APP-STATE.
- Historical recap review is **DISCOVERABLE_NOT_USABLE**: validated/prepared history binds, then the exact-review resolver rejects it because promotion-grade review requires `reviewable`.
- The recap Markdown exists in git for representative sessions, but the assembled historical review path does not render it.
- `32 / 53` Ingest runs have complete review-supporting bundles on `primary-checkout`; `21 / 53` are partial. The recovery ledger records exact component locators and APP-STATE digests where present.
- Plan has `0` current APP-STATE historical WorkObjects; one exact historical C2 Session 27 Plan remains recoverable from stranded bytes.
- Build has `0` current APP-STATE documents; one exact orphan worldbuilding document survives but needs an adapter/identity decision.
- Play has no admitted historical C1/C2 Runbooks or Runs. Do not fabricate historical Play state.
- Buddy-facing DungeonMind World projection currently returns `503 authority_unavailable`.
- AppChrome uses document navigation; moving among Plan / Build / Ingest / Play reloads/remounts the application and loses transient context.
- Shared Agent chrome exists, but Agent is **NOT_CONNECTED** as a useful user capability on all four surfaces.
- Historical review bytes remain laptop-local under gitignored `out/`; current PostgreSQL is local and has already demonstrated that local persistence can disappear.

The work ahead is therefore mostly **continuity, assembly, durability, and product interaction** rather than a new architecture program.

---

# 2. Operating rule: STOP means STOP

Every stage below ends in a named **STOP / CHECK-IN**.

At a STOP:

1. do not automatically dispatch the next roadmap stage;
2. run the assembled product against real C1/C2 material;
3. record the first user-visible failures, not only test status;
4. compare the result to this roadmap’s intended experience;
5. align with the product owner on whether the next stage is still the right stage;
6. update this roadmap if dogfood changes the ordering.

### Development cadence

- Prefer **one independently useful capability per PR**.
- Prefer no more than **two implementation PRs between human dogfood stops**.
- If a stage expands beyond two PRs, or uncovers a new authority boundary, **STOP and rebrief** rather than silently growing the slice.
- Review cycles remain counted, but review is not a substitute for dogfood.
- Do not pre-author a chain of successor handoffs across multiple STOPs.
- Two agents may work in parallel only on clearly disjoint leases. Parallelism never skips the shared STOP.

---

# 3. Execution roadmap

## Stage 1 — Historical recap inspect without promotion

### Human outcome

A user can choose an existing C1/C2 historical session/run and **read the actual recap comfortably**, even when the historical run is `validated` or `prepared` and is not promotable.

### Required behavior

- historical inspect and promotion/review are separate concepts;
- `validated` / `prepared` history may be inspected without silently becoming `reviewable`;
- actual source recap prose renders in the assembled Graph Review / recap experience;
- current run identity/status remains truthful;
- no historical ingestion is rerun;
- no graph mutation occurs merely to inspect history.

### Required dogfood corpus

At minimum:

- C1 Session 10;
- C2 Session 23;
- C2 Session 25;
- one additional rich C1/C2 session.

### Explicitly still false afterward

Pills, Threat treatment, durable review artifacts, World availability, Agent context, and no-reload navigation may still be incomplete.

### STOP 1 — READ THE HISTORY

**Do not start rich recap interaction work until this is dogfooded.**

Human check:

> Can I sit in DungeonBuddy, move among old sessions, and simply read what happened without knowing run IDs, lifecycle semantics, or filesystem paths?

At this stop we decide whether the recap reading experience itself is pleasant enough to build interactions on top of.

---

## Stage 2 — Durable historical artifact authority

### Human/system outcome

Historical inspection no longer depends on a particular worktree’s gitignored `out/` directory.

### Required behavior

- adopt/copy only exact digest-matching historical bytes;
- preserve stable run/component identity;
- use the DFC-3 recovery ledger as the source locator, not inferred timestamps;
- no re-ingestion as a repair mechanism;
- missing components remain explicitly missing;
- product resolution uses a durable product-controlled artifact authority;
- a clean checkout can resolve representative adopted artifacts after process restart.

The final VPC location does not have to be chosen in this stage if that would broaden the slice. The contract, identities, and bytes must be portable there later.

### STOP 2 — DATA SAFETY / RECOVERY CHECK

Before proceeding:

- verify representative digests independently;
- verify a clean checkout can read adopted artifacts;
- confirm no historical content was rewritten;
- inspect what remains partial/missing;
- align on the durable artifact contract and whether the next storage move should already target VPC/object storage.

This is the point to catch a bad storage decision **before** we pile UI work on it.

---

## Stage 3 — Restore DungeonMind World availability

This stage may run in parallel with Stage 2 after STOP 1 if leases are truly disjoint.

### Human outcome

The World chip is healthy and useful C1/C2 World context can be opened from Buddy through the controlled DungeonMind contract.

### Required behavior

- fix the current `authority_unavailable` path;
- preserve the post-cutover boundary: Buddy does not regain graph-storage or graph-kernel ownership;
- prove known C1/C2 NPC/place/threat retrieval through the Buddy-facing contract;
- make failures legible rather than generic “Graph” errors.

### STOP 3 — WORLD DOGFOOD

Using existing C1/C2 material, open several known objects from normal product use:

- NPC;
- place;
- threat;
- related/provenance context where available.

Check whether World feels like useful context **inside DungeonBuddy**, not a separate graph-admin system.

Do not begin recap pill integration on assumptions about the World contract if this stop fails.

---

## Stage 4 — Rich recap interaction: pills, objects, provenance, Threats

### Human outcome

Historical recap review becomes one of the product’s “wow” experiences.

### Required behavior

- entity-linked words/phrases render as polished pills/tokens in readable recap prose;
- hover/click opens useful object detail without losing the recap;
- provenance can lead back to relevant source/evidence;
- Threats project with the stronger Threat/statblock visual language already present in the product where appropriate;
- prior/next or otherwise low-friction session navigation works from the recap experience;
- use the existing good Of Conks-era styling/components as design evidence rather than creating an unrelated visual system;
- interactions operate on existing C1/C2 material without re-extraction.

### STOP 4 — RECAP “WOW” DOGFOOD

This is a deliberate visual/product review, not just functional verification.

Spend time reading multiple C1/C2 sessions and interacting naturally with pills and objects.

Questions:

- Is the prose pleasant to read?
- Are pills informative without making the recap noisy?
- Does a Threat feel materially more useful than a generic entity?
- Can I move among sessions quickly?
- Do interactions preserve where I was reading?

Do not proceed merely because tests pass. Tune the experience here if needed.

---

## Stage 5 — Persistent application shell / DFC-NAV1

### Human outcome

Plan → Build → Ingest → Play feels like navigation inside one application.

### Required behavior

- no full-document reload between primary surfaces;
- AppChrome remains mounted;
- World and Agent providers do not restart merely because the surface changes;
- campaign/session/current-object context is preserved according to explicit rules;
- URLs remain meaningful and hard reload still works;
- surface-specific selection is preserved when appropriate rather than accidentally discarded.

### STOP 5 — NAVIGATION DOGFOOD

Navigate repeatedly among all four surfaces while holding a real C1/C2 context.

Check for:

- flashes/remounts;
- lost campaign/session/run selection;
- reset World state;
- reset Agent state;
- browser back/forward surprises;
- hard-reload failures.

If this still feels like four tools glued together, stop here and fix it.

---

## Stage 6 — Real material and writeability across Plan / Build / Ingest / Play

### Human outcome

The application contains enough real C1/C2 material to exercise every surface honestly, and meaningful edits survive.

### Plan

- re-adopt the exact surviving C2 Session 27 Plan if its bytes still match the ledger;
- open/edit/save/reopen it through Plan;
- do not manufacture prose for missing historical Plan identities.

### Build

- recover/adapt exact surviving C1/C2 Build/worldbuilding bytes where a truthful identity can be established;
- if historical Build history is genuinely unavailable, prove current Build authoring by creating **new** C1/C2 material through the product rather than pretending it is recovered history.

### Ingest

- retain historical inspection from Stages 1–4;
- retain strict promotion semantics for new/reviewable ingestion work;
- do not make historical “inspectable” synonymous with “promotable.”

### Play

There is no admitted historical C1/C2 Runbook to recover.

Prove current product capability honestly:

- create a new Runbook through DungeonBuddy using existing C1/C2 campaign material;
- save/reopen it;
- start/resume a real Run;
- demonstrate that current Play durability works without inventing historical Run state.

### STOP 6 — CROSS-SURFACE WORKING SESSION

Perform one real C1/C2 working session:

```text
review recap
→ inspect World context
→ open/edit Plan
→ open/edit or create Build material
→ return to Ingest/history
→ open/edit/save Runbook
→ start/resume Play
→ reload browser
→ restart API
→ reopen the same work
```

Anything that requires hidden IDs, manual file surgery, or remembering which worktree owns the bytes is a blocker here.

**BF3B remains parked through this stop.** We need a coherent product before adding more Play interaction depth.

---

## Stage 7 — Agent as a real cross-surface capability

### Human outcome

The same Agent can help from the material currently on screen rather than behaving as detached chrome.

### Minimum context envelope

The Agent should receive governed context for:

- current campaign;
- current session when applicable;
- current surface;
- current WorkObject / WorkRevision / Ingest run / Play Run as applicable;
- current selection or highlighted text/object;
- admitted World context;
- source/provenance links where allowed.

### Required interaction

The core magic moment must become demonstrable:

> Highlight a word/sentence in a recap, planning document, or worldbuilding document → invoke Agent → ask whether related World objects exist → inspect them, or receive a governed proposal for a new node/edges when appropriate.

Writes remain proposals until approved at the owning boundary.

### Observability is part of the feature

For every Agent turn expose, behind an advanced/log affordance:

- model called;
- tokens in / out;
- cost;
- total turn time;
- step/tool timing;
- useful trace of context/tool actions;
- failure reason when a step cannot complete.

### STOP 7 — AGENT DOGFOOD

Exercise Agent from:

- historical recap;
- Plan;
- Build;
- Play.

Do not declare this ready because the provider is shared. The user must actually ask useful questions and inspect the resulting trace.

At this stop decide whether Agent write proposals are mature enough for the demo or whether read/reason/inspect is the correct demo boundary.

---

## Stage 8 — Move durable authorities off the laptop

### Human outcome

The exact product journey proven above works when the laptop is merely a client/application host and no longer the unique owner of durable state.

### Target authority posture

At minimum:

```text
APP-STATE PostgreSQL
→ remotely hosted / durable / backed up

Artifact/content authority
→ durable remotely reachable storage
→ immutable identity/digest preservation

DungeonMind
→ remotely available through its controlled contract
```

### Required behavior

- no relied-upon demo material depends on `/home/...`, a named worktree, or gitignored local `out/`;
- remote PostgreSQL is the actual authority for its domains;
- artifact storage is backed up/redundant according to the chosen operational posture;
- backup/restore or equivalent recovery evidence exists before deleting local safety copies;
- local browser state is not the only copy of required work.

### STOP 8 — MIGRATION DOGFOOD

Run the **same Stage 6 + Stage 7 journey**, not a new synthetic smoke test.

Then deliberately remove local assumptions:

- fresh checkout / clean local artifact cache;
- restart application;
- reconnect to remote authorities;
- reopen the same C1/C2 material.

If the demo works only because the old laptop paths are still present, this stage is not done.

---

## Stage 9 — Human demo gate

### Human outcome

Someone who did not build the system can experience DungeonBuddy without being coached through its internal architecture.

### Demo path

At minimum:

```text
open C1/C2
→ choose a prior session
→ read recap
→ interact with pills / node / Threat
→ inspect World/source context
→ move to Plan / Build / Play without reload
→ make and save a meaningful edit
→ ask Agent about current material
→ inspect Agent trace if desired
→ reload/restart and continue
```

The observer should not need to understand:

- WorkObject IDs;
- registry formats;
- graph database vocabulary;
- historical worktree layout;
- local Postgres setup;
- which subsystem owns a given answer.

### STOP 9 — GO / NO-GO FOR OF CONKS

This is an explicit product-owner alignment point.

If the experience is coherent and pleasant, mark **OF-CONKS-READY** and begin Of Conks dogfood.

If it is not, record the top few human-visible failures and fix those before introducing a new corpus.

---

## Stage 10 — Of Conks and Cons enters as ordinary product dogfood

Of Conks is now allowed to become the forcing corpus.

Rules:

- no bespoke Of Conks-only ingestion path;
- no hidden filesystem/manual bypass because convention material is “special”;
- no relaxing authority or provenance rules to make the demo work;
- if Of Conks exposes a missing general capability, treat it as normal product debt;
- reuse the recap/pill/Threat visual language already proven on C1/C2.

At this point BF3B, additional Play cockpit work, Combat, and convention-specific run-pressure can be re-sequenced according to **actual Of Conks dogfood**, not the old pre-continuity roadmap order.

---

# 4. Parallelism guidance

The preferred default remains one focused PR at a time, but two agents may work in parallel where the authority/lease boundaries are clean.

Likely safe pairings:

- Stage 2 artifact authority + Stage 3 DungeonMind service availability;
- Stage 4 recap interaction + preparatory DFC-NAV1 work only after the interaction contract is stable;
- later Plan recovery + Build adapter work when they do not touch shared registries/migrations.

Likely unsafe pairings:

- two PRs changing Graph Review exact-run resolution;
- artifact migration and another PR changing the same component URI semantics;
- navigation shell changes and Agent provider ownership changes without coordination;
- multiple APP-STATE migrations against the same schema boundary;
- any Buddy change that reaches directly into DungeonMind graph internals.

Parallel work rejoins at the next shared STOP before proceeding.

---

# 5. Things explicitly not authorized by this roadmap

- Re-ingesting C1/C2 merely because historical review is inconvenient.
- Reconstructing missing historical prose from memory or model output.
- Silently upgrading historical `validated` runs to `reviewable`.
- Giving Buddy graph-storage/kernel ownership after DungeonMind cutover.
- Treating the Markdown recovery ledger as a permanent product database.
- Moving to VPC first and hoping usability follows.
- Resuming BF3B because an older roadmap called it next.
- Building Combat to avoid fixing broken corpus continuity.
- Calling Agent “ready” because shared chrome renders.
- Calling a surface durable because code exists without reopen/restart evidence.
- Hiding product failures behind manual developer-only setup for the final human demo.

---

# 6. Completion markers

Use these markers in future roadmap/anchor updates:

```text
DFC-3                 DONE — C1/C2 evidence baseline / recovery ledger (#687)
DEMO-R1               historical recap inspect without promote
DEMO-R2               durable historical artifact authority
DEMO-R3               DungeonMind World availability
DEMO-R4               rich recap pills / objects / Threat projection
DEMO-R5               persistent no-reload shell (DFC-NAV1)
DEMO-R6               cross-surface real material + write/save/reopen
DEMO-R7               Agent cross-surface context + observability
DEMO-R8               remote durable authorities + recovery proof
DEMO-R9               human demo gate / OF-CONKS-READY
OF-CONKS-DOGFOOD      next forcing corpus after DEMO-R9
```

Do not mark a stage DONE until its STOP has been explicitly dogfooded and accepted.
