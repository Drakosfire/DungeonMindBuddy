> Status: ACTIVE EXECUTION STEWARDSHIP HANDOFF
> Use for: Re-anchoring the merged TL01G line after PR #496; next gate is a Gate-faithful successor cohort pair before another promotion claim.
> Do not use for: Naming `tl01h-v1` from retired V14/Adv V12 evidence, mutating `tl01g-v1`, reviving retired cohorts, changing Temporal Kernel semantics, or building a Timeline UI.
> Canonical repo path: `Docs/Plans/JUMPSTART-tl01-grounding-path-recovery.md`
> Prepared: 2026-08-01
> Updated: 2026-08-03 (post-merge doc-sync for PR #496)
> Repository: `Drakosfire/DungeonMindBuddy`
> Verified `main` anchor: `eefc8927c3e679c1688d1dd85f565f8d9eb3d9c8` (PR #496 merge)
> Merged TL01G anchor: PR `#468`, merge `2c827f2bb3055eec3969a31a0262462650e1607f`
> Fresh promotion attempt: PR `#496`, merge `eefc8927c3e679c1688d1dd85f565f8d9eb3d9c8` — V14/Adv V12 observed then retired **`PROMOTION_EVIDENCE_INCOMPLETE`**
> Grounding-path recovery: PR `#486`, merge `27e67981f78c4901deff8919ca525b5a4ab585ae` — `GROUNDING_PATH_READY` (smoke prerequisite only)
> Completion condition: a Gate-faithful successor cohort pair (holdout >14, adversarial >12) is sealed and observed before another promotion claim; `tl01f-v1`/`tl01g-v1` remain frozen.

# JUMPSTART — TL01 Grounding-Path Recovery

## §0 Pickup prompt

```text
Continue the temporal/TL01 line in Drakosfire/DungeonMindBuddy from current
main eefc8927c3e679c1688d1dd85f565f8d9eb3d9c8.

TL01G merged in PR #468 at 2c827f2bb3055eec3969a31a0262462650e1607f.
Grounding-path recovery merged in PR #486 (`GROUNDING_PATH_READY` on shared smoke).
Fresh promotion evidence merged in PR #496: V14/Adv V12 sealed, observed (18 attempts),
then retired as PROMOTION_EVIDENCE_INCOMPLETE (Adv V12 ungrounded `since the equinox flood`).
No promotion authority exists. No tl01h-v1 from that matrix.

Next single action: author a genuinely fresh Gate-faithful successor cohort pair
(holdout version > LAST_RETIRED_HOLDOUT=14, adversarial version >
LAST_RETIRED_ADVERSARIAL=12) under a new handoff. Pre-live Gate E3 + owned-evidence
value grounding must cover every resolved annotation before the first provider call.

Do not edit tl01f-v1 or tl01g-v1. Do not patch or reuse V8–V14 / Adv V6–V12 as
promotion authority. PR486 GROUNDING_PATH_READY remains a smoke prerequisite only.
```

## §1 Mission and invariant

**Mission**

Establish one bounded, reproducible grounding-path smoke that determines whether an exact evidence phrase survives every shared layer used by both frozen TL01 prompt lanes, and either repairs the proven local defect or reports the exact external blocker without manufacturing evaluable metrics.

**Invariant**

```text
For one exact selected assertion and its owned evidence span, every diagnostic stage
is bound to the same case digest, assertion ID, evidence ref, resolved span bytes,
prompt identity, provider response, and returned source_phrase. A run is evaluable
only when the returned phrase is proven inside owned evidence and normal comparison
metrics are actually produced. Missing metrics, paraphrases, foreign evidence,
unparseable output, or an unresolved stage remain explicit failures.
```

This slice is not prompt calibration. It is shared-path recovery required before prompt calibration can resume.

## §2 Re-anchor ledger

| Item | Current verified truth |
|---|---|
| Current `main` | `eefc8927c3e679c1688d1dd85f565f8d9eb3d9c8` (PR #496 merge) |
| TL01G merge | PR `#468`, `2c827f2bb3055eec3969a31a0262462650e1607f` |
| Grounding-path recovery | PR `#486`, `27e67981f78c4901deff8919ca525b5a4ab585ae` — `GROUNDING_PATH_READY` (smoke prerequisite only; not invalidated by PR #496) |
| Fresh promotion attempt | PR `#496`, `eefc8927c3e679c1688d1dd85f565f8d9eb3d9c8` — V14/Adv V12 sealed, observed, retired **`PROMOTION_EVIDENCE_INCOMPLETE`** |
| Last retired holdout / adversarial cutoffs | `LAST_RETIRED_HOLDOUT=14`, `LAST_RETIRED_ADVERSARIAL=12` |
| Control | frozen `tl01f-v1` |
| Control SHA256 | `7a9d27c3a9980893f18757d7a5fe0612cf67f9aad8dfd2ccb20f9e3c667b7143` |
| Candidate | frozen `tl01g-v1` |
| Candidate SHA256 | `3af1e470e304008d2490ba73e1a53628519c211bb54e17a10cd4c694beae9013` |
| Prompt-only freeze | `67408bd871ba684e70ddf6e53dd7088d0036a475` |
| Shared packet | `tl01c-packet-v1` |
| Shared renderer | `render_temporal_shadow_user_content_v2` |
| Last observed provider seal (V14/Adv V12) | `cde3b48d5b95ba4fc1f7c779993c2497f66914f7` — retired incomplete promotion evidence |
| Last provider execution SHA (V14/Adv V12) | `d1b5cc60604ba888985013c0093e0605f0ab158d` — 18/18 attempts observed |
| Prior retired seal (V13/Adv V11) | `33bae3485babb0d15373b91b0cbcb13282b42491` — regression evidence only |
| Last durable aggregate (V14) | `temporal-prompt-calibration:a4d817300eab3c82` at `promotion-v14/` — incomplete promotion evidence |
| Prior durable aggregate (V13) | `temporal-prompt-calibration:a1dd130979808f2f` — regression evidence only |
| Human recommendation | Author Gate-faithful successor cohort pair (>14/>12) before another promotion claim |
| Promotion authority | none |
| Open temporal PR collision | none found at re-anchor |

### Judgment record (PR #496)

| Field | Value |
|---|---|
| Verdict | **Accepted** — docs + eval evidence landed; promotion authority incomplete by design of disposition |
| Invariant judged | Trustworthy fresh promotion evidence **or** honest incomplete disposition without post-observation gold repair |
| Evidence | Sealed V14/Adv V12 cohorts + `promotion-v14` aggregate + [`REPORT-tl01g-v14-fresh-promotion-evidence.md`](../Reports/REPORT-tl01g-v14-fresh-promotion-evidence.md) + Gate-faithfulness retirement tests + future-cohort grounding guard |
| Review rounds | COMMENT on `6570d0d8` (P0 defective Adv V12 gold; P1 ITERATE_PROMPT isolation; P1 Gate-faithfulness tests), `d21b5429` (P1 future-cohort grounding guard; P1 out-of-allowlist report revert), `f49ae88b` (containment/recurrence prevention accepted); docs clarification `127cca31` |
| Rubric learned | (1) Pre-live Gate E3 / owned-evidence value grounding must cover every resolved annotation before the first provider call; fixture consistency alone is insufficient. (2) Defective sealed gold after observation → `PROMOTION_EVIDENCE_INCOMPLETE`, preserve bytes, retire the pair; never patch gold or invent `tl01h-v1` from that matrix. (3) Auto-discovered successor cohorts (holdout > retired holdout cutoff AND adversarial > retired adversarial cutoff) must fail closed on `_collect_resolved_value_grounding_defects() == []`. (4) Cohort `sources/*.md` are eval source fixtures / stimulus / owned evidence — not corpus, Supergraph ingest, or ChatGPT Project Sources. |

Intervening commits after TL01G include grounding-path recovery (PR #486) and fresh promotion evidence (PR #496). Re-run collision and path-drift checks before the next cohort handoff.

## §3 Authority and reading order

Authority precedence:

```text
1. AGENTS.md and external-agent PR-loop rules
2. checked-in temporal contracts
3. merged TL01G code, tests, fixtures, and durable artifacts
4. REPORT-tl01g-resolution-proof-abstention-gate.md
5. this jumpstart
6. Backlog.md reminders
7. PR descriptions, attachments, and chat summaries
```

Read in full before editing:

1. `AGENTS.md`
2. `.cursor/rules/external-agent-pr-loop.mdc`
3. `.cursor/skills/external-agent-pr-loop/SKILL.md`
4. `Docs/Design/CONTRACT-temporal-shadow-extraction-v1.md`
5. `Docs/Design/CONTRACT-temporal-prompt-calibration-v2.md`
6. `Docs/Design/CONTRACT-temporal-shadow-overlay-v1.md`
7. `Docs/Reports/REPORT-tl01g-resolution-proof-abstention-gate.md`
8. `src/graph_memory/temporal_shadow_extraction.py`
9. `evals/graph_memory_layer/temporal_shadow_prompt_calibration.py`
10. `tests/test_temporal_shadow_extraction_tl01g.py`
11. `tests/test_temporal_shadow_prompt_calibration.py`
12. the committed TL01G aggregate and representative failure records

The report’s handback is controlling:

```text
PR #496 completed the attempted V14/Adv V12 promotion matrix as
PROMOTION_EVIDENCE_INCOMPLETE (Adv V12 ungrounded gold retained unchanged).
→ author genuinely fresh Gate-faithful successor pair (holdout >14, adversarial >12)
→ do not name tl01h-v1 from incomplete evidence
→ PR486 GROUNDING_PATH_READY remains smoke prerequisite only
```

## §4 Capability decomposition

| Candidate outcome | Independently useful? | Contract changed? | Failure model changed? | Decision |
|---|---:|---:|---:|---|
| Stage-bound grounding trace for one exact assertion | Yes | Diagnostic artifact only | Yes, failures become localized | Include |
| Deterministic exact-phrase replay without provider | Yes | No production contract | No | Include as baseline proof |
| Same-case live smoke through `tl01f-v1` and `tl01g-v1` | Yes | No prompt change | Produces real evaluability gate | Include |
| Smallest local fix at a proven shared owner | Yes | Possibly | Yes | Conditionally include only after reproducer |
| New abstention prompt `tl01h-v1` | Yes | Prompt contract | Yes | Split; forbidden |
| Fresh V14/Adv V12 promotion pair | Yes | Sealed evaluation authority | Yes | Split; blocked on green smoke |
| Textual normalization or fuzzy grounding | Yes | Grounding semantics | Yes | Split; not an implicit fallback |
| Timeline/graph projection surface | Yes | Product/UI contract | Yes | Split; forbidden |

The selected slice has one invariant: exact phrase/evidence identity remains traceable and fail-closed through the shared extraction path.

## §5 Exact observable path

For each frozen lane, trace the same selected assertion through:

```text
case + case_digest
→ base assertion + owned evidence_ref_ids
→ resolved evidence span bytes + digest
→ TL01C packet object
→ rendered user content
→ provider request metadata
→ raw provider response / response_id
→ validated transport item
→ returned evidence_ref_ids + source_phrase
→ owned-evidence phrase lookup
→ overlay assembly
→ normal comparison metrics
```

Every stage must expose enough bounded evidence to answer:

1. Was the exact evidence phrase available in the packet?
2. Did rendering preserve the phrase and the verbatim instruction?
3. Did the provider return an exact quote, a paraphrase, a label fragment, or no phrase?
4. Did transport validation alter or reject it?
5. Did the item cite owned evidence?
6. Did phrase matching use the same resolved span bytes recorded in the trace?
7. Did the run reach ordinary comparison, or are metrics unobserved?

Do not log full prompts or unrestricted corpus text. Store bounded snippets, digests, offsets, identities, and the returned phrase required to reproduce the failure.

## §6 Diagnostic result taxonomy

Each smoke run must end in exactly one stage result:

| Result | Meaning | Progression consequence |
|---|---|---|
| `EVALUABLE` | grounded overlay assembled and normal comparison metrics observed | lane passes smoke |
| `PACKET_MISSING_PHRASE` | owned resolved phrase absent from packet | local defect; repair packet owner |
| `RENDERER_MISSING_PHRASE` | packet has phrase but rendered content does not | local defect; repair renderer owner |
| `PROVIDER_PHRASE_FIDELITY_BLOCKED` | rendered content is exact, provider returns paraphrase/fragment/omission | no local semantic relaxation; report blocker |
| `TRANSPORT_REJECTED` | provider response cannot validate without grounding evaluation | isolate schema/output defect |
| `EVIDENCE_OWNERSHIP_MISMATCH` | returned refs are absent, unknown, or foreign | fail closed; no phrase fallback |
| `GROUNDING_VALIDATOR_DEFECT` | exact phrase is present in the same owned resolved span but validator rejects it | local defect; repair exact matcher |
| `OVERLAY_ASSEMBLY_FAILED` | grounding passes but overlay construction fails | local defect outside phrase matching |
| `UNRESOLVED_DIAGNOSTIC_GAP` | trace cannot identify first failing stage | slice not complete |

Do not convert `PROVIDER_PHRASE_FIDELITY_BLOCKED` into fuzzy matching, semantic matching, or quote synthesis inside this slice. Such behavior is a separate contract decision.

## §7 Smoke fixture contract

Create one tiny diagnostic fixture, not a promotion cohort.

Required properties:

- one candidate-only contribution;
- one selected assertion;
- one owned evidence ref and one resolved span;
- a short, unmistakable phrase that appears exactly once in the owned span;
- a Gate-simple annotation whose lane/value are not themselves under dispute;
- exact case/base/gold/evidence digests;
- no source span or proposition copied from retired promotion cohorts;
- no claim of holdout, adversarial, or promotion authority.

Suggested fixture directory:

```text
evals/graph_memory_layer/examples/temporal_shadow_grounding_smoke_v1/
```

The README must state `DIAGNOSTIC ONLY — NEVER PROMOTION AUTHORITY`.

The deterministic baseline uses a fake provider response that returns the exact phrase and must reach comparison under both prompt identities. The live smoke uses the same fixture, same model, same packet, and same renderer for both lanes.

Provider-call budget for diagnosis:

```text
initial live smoke: 1 control + 1 candidate
post-fix verification: at most 1 additional control + 1 additional candidate
```

More calls require a written reason in the report. Do not turn the smoke into an unsealed calibration search.

## §8 Exact allowlist

Expected production/evaluation paths:

| Action | Path |
|---|---|
| Modify if proven necessary | `src/graph_memory/temporal_shadow_extraction.py` |
| Modify | `evals/graph_memory_layer/temporal_shadow_prompt_calibration.py` |
| Modify | `tests/test_temporal_shadow_extraction_tl01g.py` |
| Modify | `tests/test_temporal_shadow_prompt_calibration.py` |
| Create | `tests/test_temporal_shadow_grounding_path.py` |
| Create | `evals/graph_memory_layer/examples/temporal_shadow_grounding_smoke_v1/**` |
| Create | `Docs/Reports/REPORT-tl01g-grounding-path-recovery.md` |

Bounded discovery exception: one existing temporal CLI path may change only if the smoke cannot be invoked through current public evaluation functions. Name and justify it before editing.

Forbidden paths and mutations:

- any prompt text, prompt hash, or prompt registry entry for `tl01f-v1` or `tl01g-v1`;
- any file inside V8–V13 or Adv V6–V11 cohort directories;
- any new V14/Adv V12 directory;
- Temporal Kernel models, packet schema versions, overlay schema, thresholds, graph writes, or projection/UI code;
- broad normalization or fuzzy/semantic source-phrase acceptance;
- provider-specific exception that bypasses owned-evidence grounding.

Unexpected production paths are a stop condition, not an automatic allowlist expansion.

## §9 Execution sequence

### A. Reproduce and freeze the failure

1. Branch from the exact current `origin/main` SHA and record it in the implementation PR body.
2. Confirm prompt files and hashes equal the frozen identities above.
3. Re-run the two targeted TL01G/calibration modules before changes.
4. Reproduce one representative committed grounding failure from the TL01G aggregate without editing retired fixtures.
5. Record assertion ID, case digest, evidence refs, source phrase, provider response ID, and first failing function.

### B. Prove deterministic local correctness

1. Add the diagnostic smoke fixture.
2. Run exact fake-provider replay for control and candidate.
3. Assert packet contains the owned span and exact phrase.
4. Assert rendered content contains the exact phrase and explicit verbatim-grounding instruction.
5. Assert transport preserves phrase and evidence refs byte-for-byte as strings.
6. Assert exact phrase lookup succeeds only in owned evidence.
7. Assert normal comparison metrics are observed.

If deterministic replay fails, repair only the proven local owner before any live call.

### C. Run the paired live smoke

For both lanes, persist one bounded trace with:

```text
repository_sha
case_digest
prompt_version + prompt_sha256
packet_version + renderer identity
model_id
provider_response_id
assertion_id
evidence_ref_ids
resolved_span_digest
bounded resolved-span snippet
returned source_phrase
phrase match result + offset when present
failure stage/result taxonomy
comparison metrics present: true|false
```

The trace may live in the diagnostic report or a schema-free local artifact referenced by the report. Do not establish a new durable runtime schema accidentally.

### D. Apply only a proven local repair

A code change is authorized only when the trace proves one of:

- packet omits data already available at its owner;
- renderer drops or corrupts exact data from the packet;
- transport parsing alters valid returned strings;
- evidence ownership resolution selects different bytes than traced;
- exact substring matching rejects a phrase demonstrably present in owned evidence;
- overlay assembly fails after successful grounding.

Add a regression test that fails on the merge base and passes on head. Re-run the paired live smoke after the repair.

### E. Report and gate successors

The report must select one conclusion:

```text
GROUNDING_PATH_READY
LOCAL_REPAIR_REQUIRED
PROVIDER_PHRASE_FIDELITY_BLOCKED
UNRESOLVED_DIAGNOSTIC_GAP
```

`GROUNDING_PATH_READY` requires `EVALUABLE` for both frozen lanes on the same live smoke. Only that conclusion permits a later re-anchor for fresh V14/Adv V12 authoring.

## §10 Required evidence

Minimum commands:

```bash
uv run pytest -q tests/test_temporal_shadow_grounding_path.py
uv run pytest -q tests/test_temporal_shadow_extraction_tl01g.py
uv run pytest -q tests/test_temporal_shadow_prompt_calibration.py
uv run ruff check \
  src/graph_memory/temporal_shadow_extraction.py \
  evals/graph_memory_layer/temporal_shadow_prompt_calibration.py \
  tests/test_temporal_shadow_grounding_path.py \
  tests/test_temporal_shadow_extraction_tl01g.py \
  tests/test_temporal_shadow_prompt_calibration.py
git diff --check
git diff --name-only <implementation-base>...HEAD
```

Also prove:

- frozen prompt text and SHA256 unchanged;
- retired cohort directory bytes unchanged;
- no new promotion directories exist;
- diagnostic fixture is never discovered as holdout/adversarial promotion input;
- failure traces preserve assertion/evidence identity and distinguish missing metrics from zero metrics;
- exact same fixture and renderer are used by both lanes;
- provider-call count stays within the declared budget;
- live evidence is labeled author-local/provider-observed, not CI-attested.

No repository-wide CI claim is permitted without attached checks.

## §11 Review protocol

Review from the invariant, not from the literal fix.

1. Verify the branch base and no open temporal collision.
2. Compare changed paths to §8.
3. Confirm prompts, hashes, retired cohorts, packet version, and renderer identity remain frozen unless the exact renderer owner is the proven defect.
4. Inspect the trace from source bytes through comparison.
5. Confirm each result taxonomy is mutually exclusive and fail-closed.
6. Confirm fake-provider success cannot substitute for live evaluability.
7. Confirm live provider failure cannot be reported as unsafe=0, safe, or prompt-specific.
8. Confirm no fuzzy grounding or foreign-evidence fallback entered through a “diagnostic” helper.
9. Confirm both lanes run the same case and shared path.
10. Confirm successor gates remain explicit.

A review must request changes if the PR creates a fresh cohort, edits a frozen prompt, hides provider failure, totals null metrics as zero, or relaxes grounding without a separate contract decision.

## §12 Stop conditions

Stop and report before implementation expands if:

- current main materially changed temporal extraction/calibration after this anchor;
- the representative failure cannot be reproduced from durable evidence;
- the smoke requires modifying a frozen prompt or retired fixture;
- exact local replay passes but the live provider persistently paraphrases/omits phrases;
- the proposed repair requires fuzzy, semantic, normalized, or synthesized quote matching;
- a packet/schema version change is required;
- more than one independently useful production behavior is needed;
- a new durable trace schema or operator surface becomes necessary;
- provider calls exceed the declared budget without new information;
- the same smoke cannot be used for both lanes.

A stop report is a valid result. It must name the first failing stage, evidence, consequence, and smallest successor.

## §13 Handback

Suggested implementation branch:

```text
feat/tl01g-grounding-path-recovery
```

Suggested PR title:

```text
fix(tl01): recover shared source-phrase grounding path
```

The implementation PR body must record:

- exact immutable implementation base and head;
- exact changed paths and allowlist exceptions;
- frozen prompt/packet/renderer identities before and after;
- representative pre-change failure;
- deterministic fake-provider trace for both lanes;
- live paired trace for both lanes;
- provider-call counts and response IDs;
- first failing stage and selected result taxonomy;
- regression proving any local repair;
- exact commands/results and evidence provenance;
- explicit statement that TL01H, V14/Adv V12, textual normalization, broader-shadow readiness, Kernel changes, and Timeline UI remain false.

## §14 Successor gate

After PR #496 merged, re-anchor from `eefc8927c3e679c1688d1dd85f565f8d9eb3d9c8`.

PR #496 authored, observed, and retired holdout V14 / adversarial V12 as
**`PROMOTION_EVIDENCE_INCOMPLETE`**. That pair is not promotion authority. The next
steward must author a separate handoff for:

```text
fresh holdout (> LAST_RETIRED_HOLDOUT=14)
+ fresh adversarial (> LAST_RETIRED_ADVERSARIAL=12)
+ cumulative span and proposition-template novelty
+ pre-live Gate E3 / owned-evidence value grounding over every resolved annotation
+ paired tl01f-v1 vs tl01g-v1 calibration
```

That successor still does not authorize `tl01h-v1`. A new prompt is justified only
by evaluable comparison evidence on Gate-faithful gold after the shared grounding
path is healthy (PR486 smoke prerequisite).
