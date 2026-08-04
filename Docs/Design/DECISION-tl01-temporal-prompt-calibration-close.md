# DECISION — Close TL01 temporal prompt calibration as not ready

**Created:** 2026-08-03
**Status:** ACCEPTED — governs whether further TL01 temporal prompt calibration work is authorized.
**Supersedes:** nothing. **Superseded by:** nothing.
**Authority for:** the TL01 series (`REPORT-tl01b` … `REPORT-tl01g-v15-adv13-promotion-matrix`), the frozen `tl01f-v1` / `tl01g-v1` prompts, all sealed `temporal_shadow_holdout_*` / `temporal_shadow_adversarial_*` cohorts, and any proposal to author `tl01h-v1` or a successor promotion cohort pair.

## Context

PR #500 (merged `ba56baafa27209bcde95aa9f5905790b9aec13a1`) executed the bounded experiment the calibration campaign had been building toward: one certified V15 / Adv V13 promotion matrix, six lanes × three repetitions, 18 provider attempts, zero retry, singleton execution SHA. Its authoritative human disposition is `PROMOTION_EVIDENCE_INCOMPLETE`.

That disposition is neither "the candidate is ready" nor "the candidate failed in a clearly actionable way." Under the stopping rule the campaign set for itself, an incomplete matrix is not authority to author `tl01h-v1`. The `[READY]` backlog entry captured 2026-08-01 already said so explicitly: *"Do not author `tl01h-v1` until evaluable runs exist."* After PR #500, evaluable runs still do not exist on the development lane.

### What the campaign produced

Real and durable:

- A temporal envelope contract (`Docs/Design/CONTRACT-temporal-envelope-v1.md`) with a kernel implementation that **is** in production service — `src/graph_memory/kernel/temporal.py` and `src/contracts/temporal_tick_gate.py` are imported by `src/cli.py` and `kernel/world_projection.py`.
- A non-authoritative shadow extraction path, sealed cohorts, repeatable control-versus-candidate matrices, provider provenance with singleton execution SHAs, grounding diagnostics, and a human review layer that stopped a misleading aggregate from declaring victory. That last property is the campaign's most valuable output: it repeatedly refused to promote on bad evidence.
- A far more accurate map of the failure space. Temporal extraction is not one problem; it decomposes into proposition classification, occurrence versus valid time, state restatement, source-time leakage, abstention, textual grounding, and representation normalization.

Also real:

- **No production consumer.** A repository-wide search for `temporal_shadow` outside the module itself returns only `tests/`, `evals/`, `Backlog.md`, and `.gitignore`. No agent, ingestion path, or API imports it.
- **No prompt proven promotable**, across the full TL01 series (ten `REPORT-tl01*` documents).
- **21,228 lines** of temporal Python across `src/`, `evals/`, and `tests/`, of which `tests/test_temporal_shadow_extraction_tl01g.py` alone is **3,442 lines** — a test file whose subject is cohort-fixture integrity, not temporal behavior.

### The cost signal that decided it

`Backlog.md` holds roughly forty `READY` entries. Four are TL01. The rest are Hermes authoring UX, Statblock/Workbench, Live UI, and ingest/promotion work that touches surfaces a GM actually sees. The opportunity cost of another calibration cycle is not abstract.

The proximate signal is review-cycle churn. PR #498 took three review cycles and PR #500 took two. All five were about report accuracy and fixture-test strictness — double-classified assertion patterns, a placeholder `git diff --stat`, deny-lists that should have been exact byte assertions. **None** produced new information about whether the model can read time out of prose. That is the diminishing-returns signature in its most recognizable form: the review loop became better at auditing itself than at learning about its subject.

## Decision

### 1. TL01 temporal prompt calibration closes as NOT READY

The campaign ends here. `tl01g-v1` is not promotable on the available evidence, and no further prompt/cohort cycle is authorized.

### 2. Do not author `tl01h-v1`

Not from the PR #500 matrix, and not from a re-reading of any earlier retired cohort. The candidate-only V15 signal on `assertion:1131fb59ebcaae89` (baseline exact 3/3; candidate two phrase-grounding failures plus one wrong-value run) is recorded evidence, not authority to iterate.

### 3. Everything stays frozen in place; nothing is unwound

Because the shadow layer has no production consumer, freezing costs nothing and strands no half-migrated path. Preserve unchanged:

| Artifact | Disposition |
|---|---|
| `src/graph_memory/kernel/temporal.py`, `src/contracts/temporal_tick_gate.py` | **In production service** — unaffected by this decision |
| `src/graph_memory/temporal_shadow*.py` | Frozen, non-authoritative, no consumer |
| `tl01f-v1` (`7a9d27c3…`) / `tl01g-v1` (`3af1e470…`) | Frozen; do not edit prompt text |
| Sealed cohorts through V15 / Adv V13 (certification SHA `24679b19…`) | Immutable regression evidence; never patch observed gold in place |
| `evals/graph_memory_layer/temporal_shadow_prompt_calibration.py` and matrix aggregates | Preserved as a working laboratory |
| Ten `Docs/Reports/REPORT-tl01*.md` | Preserved as the findings record |

### 4. Reopen condition: product pull, not prompt curiosity

Temporal prompt calibration reopens only when **a real product use case names a smaller temporal capability worth proving**. A use case must identify the surface that consumes the output and the user-visible behavior that improves. Absent that, an interesting prompt hypothesis is not sufficient cause, regardless of the state of the known defect in §6.

This is deliberately a product gate rather than a technical one. The project's success criterion is a governed lifecycle that improves actual play and surfaces — not increasingly sophisticated evaluations.

### 5. Correct the record: TL01 was never the Timeline capability

A working timeline capability already exists and is independent of TL01. The recap→timeline-append path is live-verified — `Docs/Experiments/STATUS-Session-Recap-Timeline-Append-Benchmark.md` records gates T1 through T5 all passing live, 3/3 on `gpt-5.4-mini` — and the corpus now holds 32 `timeline.md` files, 20 of them with more than a kilobyte of content. None of that was produced by TL01, which has no production consumer.

What is genuinely absent is a user-facing Timeline **UI**. The only Timeline module in the app, `apps/live-control-ui/src/surface/modules/TimelineModule.tsx`, is 64 lines inside the abandoned `/surface` Live Control board already slated for deletion.

So the accurate framing is not "twelve temporal PRs produced no timeline." It is: **the cheap recap-driven timeline path already delivers GM-visible value; the expensive structured-annotation path never earned adoption.** Any future "smaller temporal capability worth proving" under §4 should be evaluated against the recap→append path first, since that is where temporal value is currently being delivered.

### 6. Banked finding: the one fully observed comparison

Adv V13 succeeded 3/3 in **both** lanes with zero grounding failures, so that comparison is legitimate on its own terms:

| Metric (Adv V13, n=3 per lane) | `tl01f-v1` control | `tl01g-v1` candidate |
|---|---:|---:|
| `unsafe_over_resolution` | 6 | 4 |
| `source_leakage_fp` | 4 | **0** |
| `wrong_temporal_value` | 13 | 14 |

The candidate drove source-time leakage on the certified traps to zero and cut unsafe over-resolution by a third, at no meaningful cost in value accuracy, while getting **worse** at verbatim phrase fidelity.

This is n=3 on one cohort and is **not** promotion evidence; PR #500's report correctly declines to claim it. But it is a directional shape worth banking: this prompt family trades textual fidelity for source-time discipline. A future revisit should not re-derive it from zero.

### 7. Known unresolved defect (documented, not scheduled)

Both lanes fail development phrase-grounding 3/3 on `assertion:a73b9dc9bdfaa72c`, because the model's returned `source_phrase` is not verbatim in the cited snippet. This is the same failure class named in the 2026-08-01 backlog entry, *before* PR #486's grounding-path recovery. That work made the failure **observable**; it did not make it **pass**.

The campaign therefore closes with its own stated prerequisite unmet. Stated precisely, for whoever picks this up: **verbatim source-phrase grounding against renderer-produced snippets is an unsolved contract problem.** It is bounded, deterministic, and not LLM-shaped, and it plausibly gates the cost of *any* future extraction work that requires phrase-level evidence binding — not only temporal work.

It remains a single active `READY` backlog entry. It is **not** the reopen condition (§4 governs that), and it is not scheduled by this decision.

### 8. Process learning

Record the churn signature so it is catchable earlier: when consecutive review cycles are resolved entirely by tightening the evidence apparatus — classification taxonomies, digest pinning, exact-byte fixture assertions — and none change what is known about the subject under test, the loop has stopped paying. That is a stopping signal in its own right, independent of whether the current experiment succeeded.

## Non-goals

- No removal or refactor of the shadow layer, cohorts, runner, or reports.
- No change to the production temporal kernel or tick gate.
- No `tl01h-v1`, no successor cohort pair, no further provider spend on TL01 calibration.
- No claim that temporal extraction is unachievable — only that this loop stopped producing evidence that justified continuing it.

## Refs

- `Docs/Reports/REPORT-tl01g-v15-adv13-promotion-matrix.md` (authoritative disposition), PR #500 merged `ba56baafa27209bcde95aa9f5905790b9aec13a1`
- `Docs/Reports/REPORT-tl01g-v15-adv13-cohort-certification.md`, `REPORT-tl01g-grounding-path-recovery.md`, `REPORT-tl01g-resolution-proof-abstention-gate.md`, `REPORT-tl01g-v14-fresh-promotion-evidence.md`
- `Docs/Reports/REPORT-tl01b` … `REPORT-tl01f` (earlier series)
- `Docs/Design/CONTRACT-temporal-envelope-v1.md`
- `Docs/Experiments/STATUS-Session-Recap-Timeline-Append-Benchmark.md` (the timeline path that does work)
- Calibration ID `temporal-prompt-calibration:9d9b5d09a79af1b2`; certification SHA `24679b19ac093cdbefa430cb0e930dff8c8a6dae`; provider execution SHA `71c8af5480114de4a7f50cc6099df37f46eb237d`
