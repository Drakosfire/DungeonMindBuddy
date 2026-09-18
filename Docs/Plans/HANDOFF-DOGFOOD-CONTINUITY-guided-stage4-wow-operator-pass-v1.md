# HANDOFF — DOGFOOD-CONTINUITY: guided Stage 4 UX/WOW operator pass v1

**Created:** 2026-09-17  
**Status:** RECORDED — human pass complete; see `Docs/Reports/REPORT-DOGFOOD-CONTINUITY-guided-stage4-wow-operator-pass-v1.md`  
**Canonical path:** `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-guided-stage4-wow-operator-pass-v1.md`  
**Workstream:** `CON-READY / DOGFOOD-CONTINUITY / UI language / Stage 4 WOW`  
**Base:** `main@5defc5f4bb53b3403b3fc56526ad4391670e698f`  
**Operator:** product owner / GM  
**Agent role:** dogfood facilitator and observer, not implementer  
**PR topology:** none  
**Authorized code changes:** none

> The campaign-memory sidequest is over. This session resumes the interrupted UX/WOW pass using the real merged product.

---

## 0. Your job

Walk the operator through DungeonBuddy as a real user.

Do **not** give them the whole test script at once.

Give **one concrete action at a time**, wait for their reaction, ask at most one short follow-up when needed, record what they say, and then choose the next action.

Your goal is not to make the operator prove that the product works.

Your goal is to discover:

> **What feels good, what feels awkward, what breaks immersion, and what prevents the campaign-memory experience from feeling deliberately designed?**

Do not implement fixes during this session.

Do not open a PR.

Do not turn observed friction into speculative architecture while the operator is still dogfooding.

---

## 1. Read before starting

Read:

1. `Docs/Plans/STEWARDS-ANCHOR-con-ready.md`
2. `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-ui-language-design-series-v1.md`
3. `Docs/Design/ui-language/DESIGN-interaction-layer-language.md`
4. `Docs/Roadmaps/ROADMAP-demo-ready-c1-c2-to-of-conks.md` — Stage 4
5. `Docs/Reports/REPORT-DOGFOOD-CONTINUITY-published-memory-graph-review-browse-v1.md`

Current accepted interaction grammar:

```text
cheap chrome
expensive current work
chip → glance → peek
related things do not navigate away
one coherent secondary context
Agent cheap/absent when not useful
```

Current merged campaign-memory path:

```text
Campaign + Focus session
→ published recap
→ token / glance
→ complete World object
→ relationships / origin / evidence
```

---

## 2. Session rules

### One step at a time

Good:

> Open Ingest and choose Campaign 2, Session 27. Tell me what your eye goes to first.

Bad:

> Please test campaign selection, pills, relationships, provenance, refresh, C1, C2, narrow mode, and Agent.

Let the operator react naturally before asking analytical questions.

### Prefer observation over pass/fail

Ask things like:

- What did you expect to happen?
- Did that feel natural?
- What are you looking for right now?
- What feels noisy or unnecessary?
- Would you use this while preparing/running a game?
- Did you lose track of where you were?

Do not repeatedly ask “did that pass?”

### Preserve operator language

Capture short verbatim phrases when useful.

Do not rewrite “this feels like a database admin page” into “information hierarchy concern” and lose the original observation.

You may classify it afterward.

### No live repair

If something breaks:

1. capture the exact visible failure;
2. identify the action that produced it;
3. ask one question about impact;
4. continue elsewhere if the product remains usable.

Only stop the whole dogfood session if the failure prevents meaningful continued exploration.

---

## 3. Feedback classes

Classify observations after hearing the operator, not before.

Use:

```text
UX   presentation / hierarchy / interaction friction
SEM  campaign memory is wrong, missing, duplicated, or too thin
NAV  orientation / session / campaign / return-context problem
SRC  provenance / evidence / source-reading problem
PERF latency or responsiveness changes the experience
AUTH browse/write/exact-run authority leaks into ordinary use
BUG  product behavior contradicts its intended contract
GOOD something worth explicitly preserving
IDEA possible improvement that was not actually a blocker
```

An observation may have more than one class.

Do not convert every preference into a defect.

---

# 4. Guided journey

The order below is a starting structure, not a rigid script.

If the operator notices something interesting, follow it for a few steps before returning.

## Phase A — arrive in the product

Start on the current merged application.

Ask the operator to open ordinary Graph Review / Ingest and select a recent Campaign 2 session with meaningful campaign content. Session 27 is a reasonable starting point.

First action:

> Open Campaign 2, Session 27. Do not click anything yet. Tell me what you notice first and what you think this page is asking you to do.

Observe:

- initial hierarchy;
- whether recap is clearly the primary work;
- infrastructure/debug language leaking into ordinary use;
- whether Campaign / Focus session controls make sense;
- whether the page feels loaded, empty, busy, or calm.

Do not explain the interface before they react.

---

## Phase B — read before interacting

Have the operator read naturally for a short stretch.

Then ask:

> As you read, do the World references help you scan the recap, or do they compete with the prose?

Do not ask them to inspect every token.

Choose one reference they are naturally curious about.

---

## Phase C — glance

Ask them to hover/focus the chosen World reference without opening the full object.

Then:

> Did that glance answer enough to decide whether you wanted more?

Observe:

- useful identity;
- current-session relevance;
- noise;
- placement;
- whether it obscures prose;
- whether glance feels distinct from full inspection.

If the operator ignores glances and immediately clicks, record that rather than forcing glance use.

---

## Phase D — complete object / Peek

Ask them to open the same reference.

Then:

> What information are you looking for first?

Let them inspect normally.

Follow with whichever single question best fits what they did:

- Is the first screen the useful part, or are you immediately hunting?
- Does this feel like information about the campaign, or information about the graph?
- Is anything important hidden under Advanced?
- Is anything technical occupying space you would rather give to table-useful context?

Explicitly notice whether opening the object preserved the recap and reading position.

---

## Phase E — relationships

Pick one relationship the operator actually finds interesting.

Ask them to follow it.

Then:

> Do you still understand where you are and how you got here?

Observe:

- relationship wording;
- target identity;
- temporal/session context;
- whether navigating related objects feels exploratory or disorienting;
- whether the user can return to the recap without rebuilding context.

Do not intentionally choose obscure edge cases unless ordinary exploration naturally exposes one.

---

## Phase F — provenance / source

From an object or relationship where provenance is available, ask the operator to inspect the source/evidence.

Then:

> Is this source view helping you trust or remember the campaign, or does it feel like diagnostics?

Observe:

- exact useful source span;
- readability;
- digest/technical metadata leaking into normal presentation;
- ability to return;
- whether provenance answers “why does DungeonBuddy think this?”

If source navigation fails, capture the exact visible state. Do not diagnose from the database during this session.

---

## Phase G — session movement

Return to the recap.

Ask the operator to move to an adjacent session using the most obvious product affordance available.

If no obvious affordance is apparent, do **not** immediately tell them where it is. Ask:

> If you wanted the previous or next session, where would you look?

This is UX evidence.

Then have them move across two or three sessions.

Observe:

- friction;
- repeated setup;
- scroll/context preservation;
- whether session identity remains obvious;
- whether switching feels like navigation inside one app.

---

## Phase H — campaign movement

Ask the operator to move from Campaign 2 to Campaign 1 and choose a session that looks interesting.

Then:

> Does this feel like the same product and same interaction model, just a different campaign?

Exercise at least one glance and one object open in C1.

This is useful for detecting campaign-specific accidental behavior without turning the session into exhaustive regression testing.

---

## Phase I — refresh continuity

While the operator has a meaningful Campaign + Focus session selected, ask them to refresh the browser.

Then ask only:

> Did you come back where you expected?

If yes, continue.

If no, capture what was lost.

Do not test every persistence permutation.

---

## Phase J — free exploration

Now stop driving tightly.

Say:

> Spend a few minutes exploring anything in these recaps that you are actually curious about. Tell me what you try to do and anything that gets in your way.

This phase matters.

The earlier phases test designed interactions. This phase tests whether the product invites useful behavior the script did not predict.

Follow the operator rather than redirecting them back to the checklist.

---

# 5. Optional probes — use only when relevant

Do not mechanically execute all of these.

### Threat

If a Threat appears naturally, inspect it and ask whether it feels materially more useful than a generic entity.

### Narrow viewport

If responsive behavior is part of the operator's concern, repeat one recap → object → close sequence at roughly phone width.

Do not turn the whole session into responsive QA.

### Tools / secondary context

If the operator naturally reaches for Tools, observe whether it competes with World-object inspection or whether the one-secondary-context model feels coherent.

### Author Node

Do not enter authoring merely to test it.

If the operator tries to author from ordinary browse, observe whether the product truthfully explains the missing explicit write authority.

### Agent

7A1 remains queued.

Do not redirect the session into Agent evaluation unless the operator explicitly wants to try it.

If the current product says Agent is unavailable or requires another surface, record the friction but do not treat that as the primary Stage 4 UX failure.

---

# 6. Things you must not do

During this dogfood session:

- do not edit application code;
- do not open a PR;
- do not start a new ingestion/model run;
- do not regenerate candidates;
- do not change World data;
- do not query raw PostgreSQL merely to explain a UX observation;
- do not run the 16-question semantic gauntlet;
- do not dispatch 7A1;
- do not coach the operator around confusing UX before recording the confusion;
- do not turn every observation into a proposed solution.

If the operator asks “why is this happening?”, you may inspect code/repository state after the experience has been recorded, but clearly separate diagnosis from the dogfood observation.

---

# 7. Running notes

Maintain a compact session ledger while you guide the operator.

Use this shape:

```text
Observation O<n>
Action:
What operator expected:
What happened:
Operator words:
Impact:
Class: UX | SEM | NAV | SRC | PERF | AUTH | BUG | GOOD | IDEA
Confidence:
Possible owning boundary: only if clear
```

Do not make the operator fill this out.

You maintain it silently from the conversation.

---

# 8. End-of-session synthesis

When the operator says they are done—or the useful exploration has clearly saturated—produce a concise narrative report.

It must contain:

### What worked

Call out interactions worth protecting.

Especially note anything that now feels natural after the campaign-memory sidequest.

### Friction, in experienced order

Report problems in the order the operator encountered them.

Do not rank by implementation convenience.

### UX vs memory quality

Separate:

```text
the interface made good information hard to use
```

from:

```text
the interface worked but the graph did not know enough / knew the wrong thing
```

This distinction decides whether the next slice is UX or semantic evaluation.

### The operator's actual workflow

Describe what the operator chose to do during free exploration.

This is product evidence for DungeonBuddy's intended workflow.

### Suggested next steward decision

End with at most three candidate outcomes:

```text
A. One bounded UX defect clearly dominates.
B. UX is good enough; semantic-memory quality is now the earliest blocker.
C. The pass is satisfying enough to record Stage 4 / operator dogfood and re-sequence.
```

Do not dispatch or implement one without steward authorization.

---

# 9. Success condition

This handoff succeeds when the operator can say something substantially stronger than “the page renders.”

We want enough observed product use to answer:

> **Now that the campaign memory actually works through the product, what is the next thing that stops DungeonBuddy from feeling like a tool I genuinely want to use?**

That answer—not the old roadmap queue—owns the next slice.
