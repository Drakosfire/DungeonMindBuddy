# LEARNINGS — The Oracle Gate: name your correctness oracle before you write a prompt

**Captured:** 2026-08-03
**Source:** TL01 temporal prompt-calibration close-out (`Docs/Design/DECISION-tl01-temporal-prompt-calibration-close.md`, PR #500 / #505), contrasted against the `statblocks_v1` line in `DungeonMindServer`.
**Applies to:** any LLM task whose output must be *correct* — extraction, generation, annotation, classification — before you write the first prompt.

---

## The one-sentence version

**Before writing a line of prompt, ask: is there a deterministic function that can check the output?** The answer decides which of two very different projects you are about to run, and they have wildly different costs. Ask it out loud, write the answer down, and size the effort to match.

## The two problems, side by side

Both lines are "versioned prompt + structured LLM output + a server that owns correctness." They diverged completely, and the divergence was decided upstream of any prompt.

| | `statblocks_v1` (DungeonMindServer) | TL01 temporal (DungeonMindBuddy) |
|---|---|---|
| Correctness question | "Is this HP formula pathological?" | "Does *became quay reckoner after the tally dispute* ground to session-21 as a valid-time start?" |
| Deterministic oracle? | **Yes** — D&D rules are computable | **No** — it's a judgment about prose semantics |
| Where complexity lives | Domain layer: `domain/derived.py` + `domain/validation.py` (~1,060-line validator) | Evaluation layer: sealed cohorts, control-vs-candidate matrices, gold audits, Jaccard guards |
| Evaluation apparatus | **None** — no `evals/`, no cohorts, no gold corpus | 21,228 lines of temporal Python; largest single file is a 3,442-line *cohort-fixture-integrity* test |
| Iteration signal | Validator catches a named defect → fix it | Statistical agreement with human gold → estimate |
| Outcome | Working generator, prompt v6, concrete named fixes | No promotable prompt; campaign closed as not ready |

The src:test ratio is the tell. statblocks_v1 is ~14,521 src to ~13,660 test, and the tests are *behavioral* — they prove the validator catches a bad formula. Temporal's largest test file guards *fixture bytes*, not temporal behavior. statblocks spent its complexity on the domain; temporal spent it on measuring itself.

## The lesson

**The evaluation apparatus was not over-engineering. It was the only available correctness signal.** When output correctness can't be computed, you have to *estimate* it from agreement with human gold — which forces sealed cohorts, control-vs-candidate matrices, provenance, and a human review layer to keep the estimate honest. statblocks needed none of that because its oracle never lies.

So the mistake was not "we built too much evaluation." The mistakes were:

1. **Not noticing, at the start, that we were signing up for the expensive kind of problem.** Temporal was a "no deterministic oracle" problem that we ran for twelve PRs as if it were a "yes."
2. **Not noticing, across five review cycles, that the signal had gone quiet.** PR #498 took three cycles and PR #500 took two; all five were resolved by tightening the evidence apparatus (classification taxonomies, digest pinning, exact-byte fixture assertions), and none changed what was known about whether the model can read time out of prose.

## The retry playbook — gates in order, each cheap to fail

If a prose-judgment extraction problem comes back, run these in order. Do not skip ahead.

- **Gate 0 — name the oracle.** Is there a deterministic function that can check the output? If yes, build it first and let it drive iteration (the statblocks way; no gold corpus needed). If no, you are buying the expensive problem — say so and size accordingly.
- **Gate 1 — split at the deterministic seam.** Even "no-oracle" problems have checkable parts. Temporal's verbatim `source_phrase` grounding is checkable (the phrase is in the snippet or it isn't); source-time leakage is *partially* checkable. Extract the checkable parts into a deterministic validator first, so the LLM is only ever asked the part that genuinely needs judgment — and that part is as small as possible. We asked the prompt to do everything and built a laboratory to grade all of it at once.
- **Gate 2 — one known-good smoke case through both lanes before any cohort exists.** A single end-to-end pass (one assertion, both prompts, phrase grounds, value resolves) is a hard precondition costing one provider call. No smoke, no cohort. The campaign's own backlog said "don't author `tl01h-v1` until evaluable runs exist" and then authored cohorts anyway.
- **Gate 3 — a stopping rule with a bound, set before the first run.** "Evidence incomplete" needs a pre-agreed limit: N matrices, or M consecutive review cycles that change only the apparatus and not the finding, and the campaign closes. We had a stopping rule but no bound, so "incomplete" became a reason to keep measuring instead of a reason to stop.
- **Gate 4 — reuse the path that already delivers value.** Temporal work should not be a shadow layer hoping for adoption. The recap→timeline-append path is live-verified (T1–T5 PASS, 3/3) and already populating 32 corpus `timeline.md` files. A retry should be a *smaller capability that path is already pulling for* — order the events a recap extracted, flag the one contradiction in an existing timeline — not "annotate all temporal structure."

## The portable signals

Two things transfer to every future problem, not just extraction:

1. **The self-auditing review loop is a stopping signal.** When consecutive review cycles are resolved entirely by tightening the evidence apparatus and none change what is known about the subject under test, the loop has stopped paying. Catchable on cycle two, not cycle five.
2. **The frozen shadow layer is a reusable laboratory, not a failed annotator.** The next "no deterministic oracle" problem (NPC voice consistency, plot-thread resolution, tone) will need cohort sealing, control-vs-candidate, singleton-SHA provenance, and human-review precedence. That machinery is already built and battle-tested. It just isn't a temporal asset.

## Refs

- `Docs/Design/DECISION-tl01-temporal-prompt-calibration-close.md`
- `Docs/Reports/REPORT-tl01g-v15-adv13-promotion-matrix.md` (the incomplete matrix)
- `DungeonMindServer/statblocks_v1/domain/derived.py`, `.../domain/validation.py` (the deterministic-oracle contrast)
- `Docs/Experiments/STATUS-Session-Recap-Timeline-Append-Benchmark.md` (the timeline path that works)
- PRs #468, #486, #496, #498, #500, #505
