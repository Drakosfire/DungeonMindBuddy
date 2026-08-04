---
pr_body_template: |
  ## Handoff pointer
  - Conversation: `TL01G V15 / Adv V13 Promotion Matrix`
  - Flow / agent: `TIMELINE`
  - Direction: DESIGN → CODE
  - Handoff: `Docs/Plans/HANDOFF-TIMELINE-tl01g-v15-adv13-promotion-matrix.md`
  - Branch: `timeline/tl01g-v15-adv13-promotion-matrix`
  - PR mode: **this PR is the implementation PR; do not open a second PR**

  ## Execution pointer
  - Initial branch base: `dd1a7f2a2783e2a2fb189150bd837065122bee8f`
  - Predecessor: PR #498 merged as `dd1a7f2a2783e2a2fb189150bd837065122bee8f`
  - Certified inputs: holdout V15 / adversarial V13 at `24679b19ac093cdbefa430cb0e930dff8c8a6dae`
  - Frozen control/candidate: `tl01f-v1` / `tl01g-v1`
  - Provider budget: one six-lane × three-repetition matrix, maximum **18 attempts**, no retry

  ## Verification pointer
  - Base/head/provider execution SHA: TODO after implementation begins
  - Certified digest verification: TODO from §7
  - Changed paths: §4 allowlist only
  - Matrix, aggregate, and disposition: TODO from §7 evidence ledger

  The checked-in handoff, cumulative diff, nano commits, certified input bytes,
  provider manifests, aggregate, report, and independently rerun verification are
  the review contract. The PR body is transport metadata only.
---

# HANDOFF — TIMELINE: Execute Certified TL01G V15 / Adv V13 Promotion Matrix

**Created:** 2026-08-03.  
**Status:** ACTIVE — dispatch exactly one bounded provider-execution capability.  
**Canonical handoff path:** `Docs/Plans/HANDOFF-TIMELINE-tl01g-v15-adv13-promotion-matrix.md`  
**Conversation name:** `TL01G V15 / Adv V13 Promotion Matrix`  
**Flow / agent:** `TIMELINE`  
**Handoff direction:** `DESIGN → CODE`  
**Design agent:** GPT-5.6 Thinking, DungeonBuddy project conversation  
**Code agent:** TIMELINE code agent operating on this PR branch  
**PR title:** `TIMELINE: execute certified TL01G V15 / Adv V13 promotion matrix`  
**Branch:** `timeline/tl01g-v15-adv13-promotion-matrix`  
**Initial branch base:** `dd1a7f2a2783e2a2fb189150bd837065122bee8f`  
**Predecessor merge:** PR #498, merge `dd1a7f2a2783e2a2fb189150bd837065122bee8f`  
**Certified input SHA:** `24679b19ac093cdbefa430cb0e930dff8c8a6dae`

> **Same-PR implementation gate:** This PR is the sole implementation and evidence
> surface for this capability. Do not merge it as a handoff-only PR, do not open a
> sibling implementation PR, and do not move provider execution to another branch.
> Push every implementation, evidence, report, and review-response nano commit back
> to this PR.
>
> **Certified-input immutability gate:** Holdout V15, adversarial V13, their source,
> base, gold, case, audit, and the owning TL01G test bytes are already certified.
> They are read-only in this PR. The certification SHA and every digest in §2 must
> verify before any provider call. A mismatch is a stop condition, not permission to
> repair, reseal, substitute, or re-version inside this PR.
>
> **One-matrix gate:** This PR authorizes exactly one six-lane × three-repetition live
> matrix, at most **18 provider attempts**, with **zero retry**. Every attempted call
> counts even when the provider supplies no response ID. A partial or failed matrix
> is preserved and reported; it is never silently restarted.
>
> **No-cutover gate:** Even a green promotion disposition is model-evaluation evidence
> only. This PR does not simulate or perform temporal producer cutover, graph adoption,
> cross-surface projection, Timeline UI, or integration with active Build/Statblock
> work. Those lines must settle and receive separate operator-approved design.
>
> This checked-in handoff is the complete authority. The implementation agent must not
> compress, omit, replace, or rewrite it. A required change to the runner, prompt,
> packet, renderer, schema, certified inputs, evaluator thresholds, or product code is
> a stop/split, not an implementation detail.

## Shared vocabulary

| Term | Definition |
|---|---|
| **Certified input set** | The exact V15/Adv13 source, base, gold, case, audit, and owning-test bytes listed in §2 at certification SHA `24679b19…`. |
| **Provider execution SHA** | One clean full Git SHA used by every live run manifest. It must descend from current main and contain the certified SHA unchanged. |
| **Attempt** | One requested provider invocation for one prompt lane, cohort, and repetition. Failed and response-less invocations still consume budget. |
| **Complete matrix** | Exactly baseline/candidate × development/holdout/adversarial × repetitions 1–3, with one unambiguous success or failure manifest for all 18 specs. |
| **Machine decision** | The calibration runner’s `CalibrationDecision`. It is evidence, not sole roadmap authority. |
| **Human roadmap disposition** | The one precedence-based conclusion published by this PR after validating integrity, provenance, shared failures, and row-level classifications. |
| **Representation-only mismatch** | A semantic/lane/status match whose remaining difference is exact textual extent, canonical JSON representation, or equivalent evaluator-facing form. |
| **Prompt-specific failure** | A candidate failure not shared by control and not caused by invalid inputs, unavailable provider, runner contract, or representation-only mismatch. |
| **Commit point** | The first live provider attempt. After it, no history rewrite, input mutation, retry, or experiment redesign is permitted. |
| **Stop condition** | A fact that invalidates this slice or requires a different invariant; implementation stops and reports instead of absorbing the work silently. |

## Agent flow and nano-commit contract

Use the `TIMELINE` flow and keep exactly one capability in this PR.

Required nano-commit story:

1. `docs(timeline): add certified v15 adv13 promotion matrix handoff` — created by the design agent; no provider call.
2. `chore(eval): track tl01g promotion-v15 aggregate` — add only the exact `.gitignore` exception needed to retain the durable aggregate; rerun all pre-live proofs and commit before calls.
3. `eval(timeline): record certified v15 adv13 promotion matrix` — commit only the generated aggregate and truthful report after the one authorized matrix.
4. Review-response nano commits — report/wording corrections only, or one zero-provider `--reaggregate-only` regeneration from the exact complete manifest set. No input, runner, threshold, or provider rerun change is allowed.

Before the first provider attempt, ordinary history-preserving commits and a rebase onto
current `origin/main` are allowed only while all pinned identities and certified digests
still match. After the first provider attempt, do not rebase, amend, squash, force-push,
or delete observed manifests. A late main update, if truly necessary, must be a
history-preserving merge and must not alter any pinned experiment input.

## §0 Capability decomposition, reanchor, and workspace reset

### Capability decomposition

| Candidate outcome | Independently useful? | Durable contract changed? | Separate failure model? | Decision |
|---|---:|---:|---:|---|
| Verify certified V15/Adv13 bytes and frozen runner identities | No — prerequisite to the matrix | No | No | Include |
| Execute one bounded promotion matrix | Yes | Produces one durable aggregate | Yes | **Selected capability** |
| Publish one evidence-grounded roadmap disposition | No — interpretation of the same matrix | Report only | Same matrix failure model | Include |
| Author or repair fixtures/gold/tests | Yes | Yes | Yes | Exclude; predecessor owns certified inputs |
| Revise `tl01g-v1` or create `tl01h-v1` | Yes | Yes | Yes | Named conditional successor |
| Define textual normalization policy | Yes | Yes | Yes | Named conditional successor |
| Broader-shadow dogfood or producer cutover | Yes | Yes | Yes | Named conditional successor; explicitly not authorized |

**Selected capability:** Execute one exact promotion matrix over the already-certified
V15/Adv13 inputs and publish one truthful disposition.

**Why included rows share one invariant:** Preflight verification, provider execution,
aggregation, and disposition are inseparable stages of one evidence-producing operation.
None is independently useful without the same frozen inputs and one-matrix provenance.

### Current repository anchor

At handoff creation:

| Authority | Current fact |
|---|---|
| DungeonMindBuddy `main` | `dd1a7f2a2783e2a2fb189150bd837065122bee8f` |
| PR #498 | Merged; V15/Adv13 disposition `CERTIFIED_FOR_EXECUTION` |
| Certification SHA | `24679b19ac093cdbefa430cb0e930dff8c8a6dae` |
| Active Timeline PR with this capability | None found at dispatch |
| Other open implementation work | Build PR #497 remains draft; transfer PR #442 is intentionally non-mergeable operational storage |
| Frozen candidate | `tl01g-v1`; no successor prompt is authorized here |
| Provider artifact target | `evals/graph_memory_layer/artifacts/temporal_shadow_prompt_calibration/tl01g/promotion-v15` |

### Fresh branch and worktree

Use a fresh clone or worktree. Do not reuse PR #496, PR #498, or another TL01 branch.

```bash
git fetch --prune origin
git switch timeline/tl01g-v15-adv13-promotion-matrix
git rebase origin/main
git status --short
git rev-parse HEAD
git rev-parse origin/main
git merge-base --is-ancestor origin/main HEAD
```

Required result before any other edit:

```text
worktree: clean
origin/main: ancestor of HEAD
exact rebased origin/main SHA: recorded in the PR handback
certification SHA 24679b19…: reachable ancestor
no active sibling Timeline PR owns promotion-v15 execution
promotion-v15 artifact directory: absent
```

If `origin/main` has moved, compare all pinned Git blob identities and certified digests
in §2. Unrelated main movement is acceptable before calls only when every identity
remains exact. Any runner, extraction, schema, calibration-test, grounding-test, or
certified-input change requires a handoff amendment and fresh review before provider
execution. Do not infer compatibility from passing tests alone.

## §1 Mission and merge-ready invariant

**Mission:** The Timeline steward can obtain one trustworthy promotion judgment for
frozen `tl01g-v1` from the certified V15 / Adv V13 pair so the operator can choose the
next Timeline research slice without mutating observed inputs or simulating cutover.

**Merge-ready invariant:** From one clean provider execution SHA descended from current
main and certification SHA `24679b19…`, byte-frozen `tl01f-v1` and `tl01g-v1` use the
pinned packet, renderer, runner, schema, development cases, and certified V15/Adv13
inputs across at most one exact six-lane × three-repetition matrix; every attempted
call and failure remains explicit, the durable aggregate and human report agree under
§6 precedence, certified bytes remain unchanged, and no prompt revision, retry,
product cutover, graph authority, or second implementation capability is introduced.

### Pre-dispatch critique

| Question | Answer |
|---|---|
| Can one invariant govern every claimed observable path? | **Yes.** Verification, calls, manifests, aggregate, and disposition all establish one trustworthy evaluation result from one frozen experiment. |
| What adversarial sequence is most likely to falsify it? | Verify only cases → silently miss changed source/audit/test bytes → run calls → encounter shared failures or representation differences → report candidate prompt failure → rerun selected cells. The handoff blocks this with full digest verification, pinned runner blobs, exact 18-spec accounting, shared-failure analysis, precedence, and zero retry. |
| Would §7 detect that sequence? | **Yes.** It verifies every certified digest, the runner/extraction/test blob identities, clean provider SHA, complete manifest matrix, row-level classifications, no input diff, no retry directories, and report/aggregate agreement. |
| Which boundary is easiest to under-test? | Human disposition. The runner can emit `ITERATE_PROMPT` while integrity, shared control failures, or representation mismatches make that interpretation unsupported. |
| What fact forces a stop or split? | Any digest or pinned-blob drift; need to change runner/prompt/schema/threshold/input; provider invocation beyond the one matrix; incomplete manifests presented as complete; or need for product/cutover work. |

## §2 Context, authority, frozen identities, and certified inputs

| Field | Required content |
|---|---|
| Parent authority | `Docs/Reports/REPORT-tl01g-v15-adv13-cohort-certification.md`; PR #498; `Docs/Plans/HANDOFF-TIMELINE-tl01g-v15-adv13-cohort-certification.md` |
| Failure-taxonomy precedent | `Docs/Reports/REPORT-tl01g-v14-fresh-promotion-evidence.md`; PR #496, as invalid/incomplete history only |
| Repository rules | `AGENTS.md`; `.cursor/rules/external-agent-pr-loop.mdc`; `.cursor/skills/external-agent-pr-loop/SKILL.md` |
| Initial base revision | `dd1a7f2a2783e2a2fb189150bd837065122bee8f` |
| Required implementation base | Exact current `origin/main` after §0; must preserve all identities below |
| Predecessor contract | Provider-unobserved `CERTIFIED_FOR_EXECUTION` V15/Adv13 at `24679b19…` with exact digest table below |
| Exact input consumed | Existing development F/G cases, certified V15 F/G cases, certified Adv V13 F/G cases, model `gpt-5.4-mini`, current calibration CLI |
| Independently useful output | One durable `promotion-v15/calibration/aggregate.json` and one truthful disposition report |
| What remains false | No `tl01h-v1`; no normalization policy; no broader-shadow acceptance; no producer/graph/surface cutover; no timeline API/UI/event/role work |
| Explicit non-goals | Fixture/gold/source/case/audit/test repair; prompt/packet/renderer/runner/schema/threshold edits; corpus/Project Source work; graph/kernel/API/UI changes; retries; second matrix |

### Authority precedence

```text
1. Current repository rules and exact current-main implementation
2. PR #498 certification report and certified SHA/digests
3. This checked-in handoff
4. Frozen runner/extraction/schema contracts and owning tests
5. PR #496 observed report as failure-taxonomy precedent only
6. Project Sources and chat summaries
```

### Required read order

Before changing files:

1. This handoff.
2. `Docs/Reports/REPORT-tl01g-v15-adv13-cohort-certification.md`.
3. `Docs/Plans/HANDOFF-TIMELINE-tl01g-v15-adv13-cohort-certification.md`, especially its Named successor.
4. `evals/graph_memory_layer/temporal_shadow_prompt_calibration.py` read-only.
5. `tests/test_temporal_shadow_prompt_calibration.py` read-only.
6. `tests/test_temporal_shadow_grounding_path.py` read-only.
7. `tests/test_temporal_shadow_extraction_tl01g.py` read-only and certified.
8. `Docs/Reports/REPORT-tl01g-v14-fresh-promotion-evidence.md` as a warning about invalid gold, shared failures, and human precedence.
9. Existing `promotion-v14/calibration/aggregate.json` read-only as an artifact-shape example, never as input or fallback.

### Frozen prompt and execution identities

| Identity | Required exact value |
|---|---|
| Control prompt | `tl01f-v1` |
| Control SHA256 | `7a9d27c3a9980893f18757d7a5fe0612cf67f9aad8dfd2ccb20f9e3c667b7143` |
| Candidate prompt | `tl01g-v1` |
| Candidate SHA256 | `3af1e470e304008d2490ba73e1a53628519c211bb54e17a10cd4c694beae9013` |
| Packet | `tl01c-packet-v1` |
| Renderer | `render_temporal_shadow_user_content_v2` |
| Model | `gpt-5.4-mini` |
| Repetitions | `3` |
| Experiment role | `promotion` |
| Certified input SHA | `24679b19ac093cdbefa430cb0e930dff8c8a6dae` |
| Runner Git blob | `45b01c78f24ada02dcaa4b89bfba6da90c745445` |
| Calibration-test Git blob | `3e4fcaa20ee2ef7aa92f4d485c46c2b671c860d9` |
| Grounding-path-test Git blob | `f233fdaba86673eef760ccf42e015ddc175dc2b6` |
| Extraction Git blob | `bcf279c387869f9fe675221894e8dc55d6640b95` |
| Extraction-schema Git blob | `05fc8c1a860e187edc4e84cd4b54ea0b3e475e5e` |
| Output directory | `evals/graph_memory_layer/artifacts/temporal_shadow_prompt_calibration/tl01g/promotion-v15` |
| Authorized attempts | maximum `18`; zero retry |

Verify Git blob identities with `git rev-parse HEAD:<path>`. If current main differs,
stop before editing `.gitignore` or invoking the provider.

### Certified input digest manifest

The following SHA-256 manifest is copied from the merged certification report. It must
pass byte-for-byte on the execution worktree before calls and again after calls:

```text
17918e9f8ec30c7d8d23f2d26dd88eb1138d4a2b64a9a2c7df33991dafae6069  tests/test_temporal_shadow_extraction_tl01g.py
7a4044375b70d421920f8ab302e88ea6fb2f74ca35187600332dfa6217815445  evals/graph_memory_layer/examples/temporal_shadow_holdout_v15/GOLD-AUDIT.md
ab5ab1f2b4dd3bd77b5750bb6ec826f1ccd80da69e7608e3459cca1d036e304e  evals/graph_memory_layer/examples/temporal_shadow_holdout_v15/base-contribution.json
cb8b3739d7ec79e3215d9c4e6fb61bb990846a72afabcb045f95027d788b48b8  evals/graph_memory_layer/examples/temporal_shadow_holdout_v15/gold-overlay.json
7ef55ca2297f13b0ebce890c1fa420c9311e3ab9f4d7bcfeca8b85b68738a71a  evals/graph_memory_layer/examples/temporal_shadow_holdout_v15/temporal-case-tl01f.json
af0e61cf31a1d368a4148c166d8c8913f28d1319d3c9a7bea2669d0d79156e79  evals/graph_memory_layer/examples/temporal_shadow_holdout_v15/temporal-case-tl01g.json
f4b0d87e8034393229e9b6dd06a6976a46ed2928066a8f27f2c6bc5c4d827710  evals/graph_memory_layer/examples/temporal_shadow_holdout_v15/sources/dusk-gong-ceased.md
881ba3901c1b915e4631a88c174a094dd8afe94dbf5f944ba3c3277be5a266c1  evals/graph_memory_layer/examples/temporal_shadow_holdout_v15/sources/emberglass-identity.md
23fcc6234f5dfa0bd297fae067259d0a183f1ee4f216456760ba9f91ea924d27  evals/graph_memory_layer/examples/temporal_shadow_holdout_v15/sources/ferry-dusk-tide.md
9963d300c35fb11210e9f83388bd9f0a3bb72a35cec12ef2fd8957b8a12effa6  evals/graph_memory_layer/examples/temporal_shadow_holdout_v15/sources/marshal-ambiguous.md
15ae7f52f9ec336b2c4ddaa9fa19b6e39f8ec6d7bb9f169dd3b8d04058fcafe0  evals/graph_memory_layer/examples/temporal_shadow_holdout_v15/sources/pier-scribe-missing.md
07b2c803e0964aa084c2d607516851570decfcd187e54c7e3b58cef282776314  evals/graph_memory_layer/examples/temporal_shadow_holdout_v15/sources/reckoner-start.md
4a49f2720345b7d89f37e797809101ce5477285de9b5a4b8077a71c88f603388  evals/graph_memory_layer/examples/temporal_shadow_holdout_v15/sources/reckoner-still.md
69d9997d96485c9aef4c5a48c14ad17fb680aa18f8ac41a37fda5019c99f5ce6  evals/graph_memory_layer/examples/temporal_shadow_holdout_v15/sources/reef-ledger-end.md
d1bbded5f2df89eb12e608c98dd15c5cf88a115635647ca84aa9dfad12e7d0de  evals/graph_memory_layer/examples/temporal_shadow_holdout_v15/sources/session-21-tide-horn-tending.md
5212dec5fc38184e26cd852810bf1f8ba6ffac2966872024310c263118c743cc  evals/graph_memory_layer/examples/temporal_shadow_holdout_v15/sources/shoal-intent.md
f2b11adc5efe520e28dfa407d7abac881c8c5e7ff2280de0f999178cb7d7a2b0  evals/graph_memory_layer/examples/temporal_shadow_holdout_v15/sources/tide-horn-session.md
ac839cd60ad7bacb79a4da02040c150c742f2f892cf20fc1802ce7b292989b07  evals/graph_memory_layer/examples/temporal_shadow_holdout_v15/sources/vault-sealed-since.md
c566a0b2ad05e1d0184d1f900bc1b3e1876dda23ce23987bea80de798b1f60e7  evals/graph_memory_layer/examples/temporal_shadow_adversarial_v13/GOLD-AUDIT.md
47babf81f9c1224482e3b895c5813ac12b4358e1840b6f8c832173a626b4bb06  evals/graph_memory_layer/examples/temporal_shadow_adversarial_v13/base-contribution.json
f937a3d9216c8baf2213a63cc30c49dcc90e4c7aa8382b7d04d1dc07fef79da7  evals/graph_memory_layer/examples/temporal_shadow_adversarial_v13/gold-overlay.json
83e214ccc99cdc2f52277b0cb30938a9297dd8781bacd18cbbc2c496d2cecd62  evals/graph_memory_layer/examples/temporal_shadow_adversarial_v13/temporal-case-tl01f.json
924f79ab30e1fbe64e23d3b593fb5a1843f2e7cd5d06a58b1decf6903a060791  evals/graph_memory_layer/examples/temporal_shadow_adversarial_v13/temporal-case-tl01g.json
a6dfdcc2b344b2f19c6c66069aefbdec555c1e238d2612172db35ca381da62e0  evals/graph_memory_layer/examples/temporal_shadow_adversarial_v13/sources/beacon-cracked-historical.md
65d5ef51369a9dc4811bc6938376a57ae40623121d13fbca5beff39b3efc4d04  evals/graph_memory_layer/examples/temporal_shadow_adversarial_v13/sources/beacon-fog-prerequisite.md
d51634c740b42451499faf2d690b339f6ef99c25ccae28403930027775eb39cf  evals/graph_memory_layer/examples/temporal_shadow_adversarial_v13/sources/causeway-moonrise.md
eeae1d2ca2b5111f45905e2aa9b17a30479d664f9cebbbd4f4152687b71a2cb4  evals/graph_memory_layer/examples/temporal_shadow_adversarial_v13/sources/causeway-open-edict.md
2bf3730ed454003faa3acbd6c072addc0dfa84d33043e7594f85ea889725183c  evals/graph_memory_layer/examples/temporal_shadow_adversarial_v13/sources/fuel-clerk-still.md
4f42a7da9369f25acaff1c6af82577c52fe6fa6fe7d2b1bcde60274cabcdf8ad  evals/graph_memory_layer/examples/temporal_shadow_adversarial_v13/sources/fuel-tally-end.md
da250b8f21b335e4de0aea37cf7e945d3701112b76130b61b724f53f563a71cb  evals/graph_memory_layer/examples/temporal_shadow_adversarial_v13/sources/register-ink-black.md
da41ff52dd037cb420990235f23b5690a2dbc7239cfbd191f31a28caea4c9d69  evals/graph_memory_layer/examples/temporal_shadow_adversarial_v13/sources/register-keeper-ambiguous.md
fcdb75422c423764ad405faf2dcc098f66339202d564458cad5dfe4bfbf6662a  evals/graph_memory_layer/examples/temporal_shadow_adversarial_v13/sources/register-keeps-session19.md
33e3fc98f7943c60ecad607da7d8fbe16ff7d78b741815573ea12f1f0da620c9  evals/graph_memory_layer/examples/temporal_shadow_adversarial_v13/sources/register-locks-nightfall.md
```

The cohort `README.md` files and certification report are documentation pointers updated
after the certification SHA; they are read-only in this PR but are not members of the
certified execution-input digest set.

## §3 Observable paths and adversarial sequences

| Path | Current behavior | Required behavior | Same invariant? | Owning boundary |
|---|---|---|---:|---|
| Certified-input preflight | Inputs exist on merged main | Full SHA ancestry, Git blobs, all certified digests, prompt hashes, and clean tree verify before calls | Yes | Git + deterministic tests |
| Output initialization | `promotion-v15` absent | Runner creates exactly one local experiment directory from one clean execution SHA | Yes | calibration CLI |
| Baseline development | Existing `tl01f-v1` development case | Three explicit outcomes, no substitution or prior-manifest reuse | Yes | manifests + aggregate |
| Candidate development | Existing `tl01g-v1` development case | Three explicit outcomes under the same model/SHA | Yes | manifests + aggregate |
| Baseline holdout V15 | Certified control case | Three explicit outcomes bound to certification SHA | Yes | seal verification + manifests |
| Candidate holdout V15 | Certified candidate case | Three explicit outcomes bound to same fixture bytes | Yes | seal verification + manifests |
| Baseline adversarial V13 | Certified control case | Three explicit outcomes bound to certification SHA | Yes | seal verification + manifests |
| Candidate adversarial V13 | Certified candidate case | Three explicit outcomes bound to same fixture bytes | Yes | seal verification + manifests |
| Provider failure | Missing/refused/incomplete/error response | Count attempt; preserve failure manifest and null/unobserved comparison fields | Yes | runner + report |
| Model/contract/evidence failure | Grounding, invalid output, target mismatch, contract, or evidence error | Preserve exact code/diagnostics and do not convert failure to zero-valued safety metrics | Yes | aggregate run records |
| Interrupted/partial matrix | Fewer than 18 unambiguous outcomes | No live rerun; human disposition `PROMOTION_EVIDENCE_INCOMPLETE` | Yes | artifact inventory + report |
| Aggregate-only failure | All 18 exact manifests exist; aggregate missing/stale | One zero-provider `--reaggregate-only` is permitted | Yes | reaggregate validation |
| Input drift after calls | Any certified/input/runner byte changes | Preserve observed evidence; stop, no patch and no rerun | Yes | Git diff + digest check |
| Human disposition | Machine decision may be misleading under shared or representation failures | Apply §6 precedence and row-level comparison before naming successor | Yes | report review |
| Green machine decision | Runner may say ready | Treat only as readiness evidence; no cutover or cross-surface claim | Yes | report non-claims |

### Ordered failure sequences

| Sequence | Required safe outcome | Owning proof |
|---|---|---|
| Certified SHA reachable → one source/test digest differs → provider not yet called | Stop before call; no local repair | §7 preflight digest manifest |
| `.gitignore` edited → tree left dirty → live command invoked | Runner must refuse; commit exact allowlist change, rerun preflight, then invoke once | clean-worktree test + provider SHA |
| First provider call succeeds → later cell fails → operator wants rerun | Preserve all outcomes, consume attempt, finish only remaining first-attempt specs if runner is still in the same single invocation; never invoke matrix again | manifest inventory + invocation record |
| Process interrupts after partial manifests → command exits | Do not invoke live command again; report incomplete unless exact 18 manifests already exist | artifact inventory |
| All manifests exist → aggregate construction alone fails | Use one `--reaggregate-only` call with identical arguments; prove zero provider calls | reaggregate logs + unchanged manifest set |
| Control and candidate share grounding/semantic collapse → machine says iterate | Human report classifies shared failure and blocks isolated prompt claim | row-level shared-failure table |
| Candidate differs only by exact phrase extent/representation → machine says iterate | Select textual-normalization disposition only when semantic/status/lane checks are otherwise clean | classification ledger |
| Candidate has isolated unsafe/lane/status/value failure on certified gold | Select `ITERATE_PROMPT`; name rows and leave `tl01h-v1` unimplemented | assertion stability + report |
| All runner gates green → Build/Statblock work still active | Select readiness only; do not start cutover or surface integration | non-claims + named successor |
| Review discovers certified-input defect after observation | Human disposition incomplete; inputs remain immutable; no rerun on V15/Adv13 | post-live digest + stop report |

## §4 Files in scope (tracked allowlist)

Every tracked changed path must appear here.

| Action | Path | Purpose |
|---|---|---|
| Create | `Docs/Plans/HANDOFF-TIMELINE-tl01g-v15-adv13-promotion-matrix.md` | Complete same-PR design authority |
| Modify | `.gitignore` | Add only the exact `tl01g/promotion-v15/calibration/aggregate.json` exception chain |
| Create | `evals/graph_memory_layer/artifacts/temporal_shadow_prompt_calibration/tl01g/promotion-v15/calibration/aggregate.json` | Durable machine aggregate from the one authorized matrix |
| Create | `Docs/Reports/REPORT-tl01g-v15-adv13-promotion-matrix.md` | Provenance, outcomes, failure classification, human precedence, and named successor |

### Bounded generated-evidence exception — local ignored run artifacts

```text
Directory:
  evals/graph_memory_layer/artifacts/temporal_shadow_prompt_calibration/tl01g/promotion-v15/

Maximum run directories:
  exactly 18 lane/cohort/repetition run directories under calibration/

Allowed path kinds:
  runner-generated run-manifest.json, failure-manifest.json, comparison/overlay/output
  files, and logs produced by the one authorized invocation

Decision rule:
  no manually authored file belongs here; every run directory must map to one exact
  §6 provider spec; only calibration/aggregate.json is tracked in Git

Required retention:
  preserve local manifests through review; do not delete failures or response-less
  attempts merely because they are ignored by Git
```

If any additional tracked path or manually authored artifact is required, stop and
request a handoff amendment before changing it.

## §5 Files and capabilities explicitly out of scope

| Path / capability | Why this slice must not touch or claim it |
|---|---|
| `tests/test_temporal_shadow_extraction_tl01g.py` | Certified owning-test byte; digest-pinned and read-only |
| `evals/.../temporal_shadow_holdout_v15/**` except README read | Certified input set; no edits under any outcome |
| `evals/.../temporal_shadow_adversarial_v13/**` except README read | Certified input set; no edits under any outcome |
| V15/Adv13 `README.md` and certification report | Read-only documentation pointers; not execution inputs |
| `evals/graph_memory_layer/temporal_shadow_prompt_calibration.py` | Pinned runner; required change is stop/split |
| `tests/test_temporal_shadow_prompt_calibration.py` | Pinned runner contract; required change is stop/split |
| `tests/test_temporal_shadow_grounding_path.py` | Pinned shared-path contract; required change is stop/split |
| `src/graph_memory/temporal_shadow_extraction.py` | Frozen prompt, packet, renderer, client, and extraction semantics |
| `src/graph_memory/temporal_shadow_extraction_schema.py` | Frozen transport/aggregate schemas |
| Existing `tl01g/promotion/` and `promotion-v14/` artifacts | Immutable prior evidence; no overwrite, copy, or fallback |
| `.gitignore` beyond the exact promotion-v15 exception | No artifact-policy cleanup or reorganization |
| `tl01h-v1` or any prompt revision | Requires observed candidate-specific evidence and separate handoff |
| Textual normalization/evaluator relaxation | Separate policy capability; exact matching remains unchanged here |
| Graph/Kernel/contribution/publication code | No graph authority or temporal producer adoption |
| Timeline API, event nodes, participant roles, projection, UI | Separate product capabilities after acceptance design |
| Build/Statblock branches or surfaces | Active neighboring work; no cross-surface integration or simulated cutover |
| `Docs/Roadmaps/**`, Campaign Supergraph tracker, Project Sources | Document sync and broader sequencing are separate operations |
| Corpus or canonical campaign prose | Evaluation uses certified synthetic stimuli only |
| Provider retry, selected-cell rerun, second matrix | Violates the one-matrix invariant |

## §6 Implementation contract and conditional matrices

```text
Input:
  current-main frozen calibration implementation
  exact tl01f-v1 / tl01g-v1 prompts
  existing development F/G cases
  certified V15 F/G cases and Adv V13 F/G cases at 24679b19…
  model gpt-5.4-mini

Output:
  one promotion-v15 aggregate representing at most 18 attempts
  one report selecting exactly one human roadmap disposition

Invariant:
  §1 merge-ready invariant, unchanged

Failure behavior:
  certified digest / pinned blob mismatch → stop before calls
  provider/infrastructure failure         → count attempt; preserve failure; incomplete
  partial or ambiguous manifest matrix     → no retry; incomplete
  shared control/candidate failure         → incomplete or root-specific shared blocker,
                                             never isolated prompt blame
  representation-only candidate blocker    → advance to textual-normalization design
  isolated candidate semantic/safety defect→ iterate prompt
  all readiness gates observed and green   → ready for broader-shadow acceptance design
  post-observation input defect             → preserve evidence; incomplete; fresh design

Replay / idempotency:
  deterministic preflight/tests → repeat freely before the first call
  live matrix                   → invoke once only
  --reaggregate-only            → one zero-provider replay from exact complete manifests
  changed input after calls     → prohibited; no rerun
  duplicate provider invocation → stop and report budget violation

Trust boundary:
  Verifies:
    certified bytes, prompt/runner identities, clean execution SHA, exact matrix,
    manifest provenance, aggregate reconstruction, explicit failure accounting
  Records or trusts without proving:
    provider semantic quality and natural-language diagnostics
  Rejects:
    prior artifact fallback, missing metrics as zero, machine decision as sole authority,
    shared failures as candidate-specific, post-hoc input repair, retry
```

### Commit point

```text
Commit point:
  first attempted live provider call in the one authorized CLI invocation

Before commit:
  rebase is allowed; deterministic verification may repeat; `.gitignore` exception must
  be committed; output directory must be absent; worktree must be clean

After commit:
  no rebase/amend/squash/force-push, no certified or pinned input edits, no second live
  command, no selected-cell rerun, and no deletion of failed manifests

Truthful result after post-commit failure:
  preserve the exact observed manifest set, publish PROMOTION_EVIDENCE_INCOMPLETE, and
  name the root cause without inventing missing metrics

Recovery:
  only `--reaggregate-only` from an exact complete manifest set is permitted here;
  every other recovery is a separately designed successor
```

### Provider-call budget

```text
baseline development:  3 attempts
candidate development: 3 attempts
baseline holdout V15:   3 attempts
candidate holdout V15:  3 attempts
baseline Adv V13:       3 attempts
candidate Adv V13:      3 attempts
maximum total:         18 attempts
retries:                0
```

### A. State and fallback matrix

| Observable path | Loading / initializing | Exact success | Ordinary miss | Dependency unavailable | Integrity / contract failure | Stale / superseded | Retry / replay |
|---|---|---|---|---|---|---|---|
| Certified input verification | Resolve SHA, blobs, digests | All exact | Missing path blocks | Git unavailable → stop | Any mismatch → stop | New main drift → rebrief | Deterministic before calls |
| Output directory | Must not exist | Fresh directory | Existing directory blocks | Filesystem unavailable → stop | Ambiguous prior manifests → stop | Any prior promotion-v15 is stale/conflicting | No live reuse |
| Live matrix | Build exact 18 specs | One outcome each | Model miss is observed | Provider failure consumes attempt | Wrong identity/SHA/seal → stop/incomplete | Wrong case/model output ignored only as explicit failure | No retry |
| Aggregate | Validate exact disk matrix | One aggregate | Missing outcome → incomplete | Files unavailable → incomplete | Multiple manifests/SHA mismatch → stop | Prior aggregate never fallback | Reaggregate-only once |
| Human report | Read aggregate + manifests | One disposition | N/A | Incomplete evidence → incomplete | Contradiction blocks merge | Superseded machine result retained as evidence | Wording corrections only |

No fallback to V14/Adv12, prior aggregate, another case path, another prompt, label,
source filename, copied response, or latest artifact is permitted.

### B. Identity matrix

| Situation | Required rule | Ambiguity behavior | Fallback permitted? |
|---|---|---|---|
| Prompt identity | Exact versions and SHA-256 in §2 | Stop before calls | No |
| Packet/renderer | Exact pinned names under pinned extraction blob | Stop | No |
| Runner/schema/tests | Exact Git blobs in §2 | Stop/rebrief | No |
| Certification | Full `24679b19…` reachable ancestor | Stop | No |
| Certified files | Every SHA-256 in manifest matches | Stop | No |
| Development cases | Exact current canonical F/G pair | Pair validator must pass | No |
| V15/Adv13 pairs | Same fixture bytes/IDs except case/prompt identity | Stop | No |
| Provider execution | One clean full 40-char SHA across all manifests | Incomplete/stop | No |
| Run spec | Exact lane + cohort + repetition 1–3 | Missing/duplicate → incomplete | No |
| Provider response | Exact ID when supplied; missing remains missing | Record without invention | No |
| Rename/rebind | Prohibited | Stop | No |

### C. Persistence and replay matrix

| Operation | Durable representation | Round-trip guarantee | Duplicate / replay behavior | Compatibility / migration | Rollback / reversion |
|---|---|---|---|---|---|
| Certified inputs | Git blobs at certification SHA + current tree | Exact digests before/after | Never copy/reseal | Existing schemas only | No post-call edit |
| Per-run outcomes | Local success/failure manifests | One unambiguous outcome per spec | Live replay prohibited | Existing runner schema | Preserve after attempt |
| Aggregate | Tracked `promotion-v15/calibration/aggregate.json` | Reconstructs exact matrix/SHA/metrics | Reaggregate-only from exact manifests | Existing aggregate schema | Revert aggregate commit, not observations |
| Report | Tracked Markdown | Agrees with aggregate/manifests | Amend for accuracy only | No loader contract | Revert report commit |
| Branch history | Git commits in this PR | Execution/certification SHAs remain reachable | No rewrite after calls | History-preserving merge only | Revert commits, never erase observed SHA |

### D. Predecessor-to-consumer mapping

**Grounding sources:** PR #498 certification report and digest table; current calibration
runner/schema; exact paired case files; prior PR #496 report for classification examples.

| Predecessor field / outcome | Real shape / optionality | Consumer behavior | Transformation | Proof |
|---|---|---|---|---|
| Certification SHA | Full 40-char Git commit | `--holdout-seal-commit` and `--adversarial-seal-commit` | None | runner seal verification + ancestry |
| Certified digest manifest | SHA-256 + repo-relative path | Preflight and post-live byte verification | None | `sha256sum -c` |
| `tl01f-v1` / `tl01g-v1` | Prompt versions + fixed hashes | Baseline/candidate lanes | None | TL01G tests + aggregate identity |
| Development F/G cases | Existing paired cases | Development lanes | None | pair validator |
| V15 F/G cases | Certified paired case JSON | Holdout lanes | Prompt identity only | seal/case checks |
| Adv V13 F/G cases | Certified paired case JSON | Adversarial lanes | Prompt identity only | seal/case checks |
| Run success manifest | Optional response ID + comparison/overlay | Aggregate run record | Existing runner logic | manifest inspection |
| Failure manifest | Failure code, diagnostics, optional response ID | Explicit failed run; nullable metrics | Existing runner logic | aggregate run record |
| Machine decision | Enum + diagnostics | Evidence for precedence | Bounded mapping below | report comparison |
| Prior V14/Adv12 matrix | Invalid/incomplete observed history | Classification precedent only | No metric reuse | diff/path inspection |

### Human roadmap disposition precedence

The report must select exactly one disposition, in this order:

1. **`PROMOTION_EVIDENCE_INCOMPLETE`** when certified integrity, pinned identities,
   provider availability, one clean provider SHA, exact 18-spec matrix, manifest
   consistency, comparison observability, or shared control/candidate evaluability is
   not established. Any post-observation certified-input defect also lands here.
2. **`ADVANCE_TO_TEXTUAL_NORMALIZATION`** only when the certified inputs are valid,
   control and candidate semantics/statuses/lanes/temporal values are otherwise
   correct, and the only demonstrated blocker is exact textual phrase/copy or canonical
   representation. Do not modify equality or normalization here.
3. **`ITERATE_PROMPT`** only when certified evidence isolates candidate-specific unsafe
   over-resolution, source-time leakage, status/lane/value/semantic failure,
   grounding/model-output noncompliance, or quality-threshold failure not shared by
   control and not representation-only. Name every material assertion and pattern;
   leave `tl01h-v1` unimplemented.
4. **`PROMPT_READY_FOR_BROADER_SHADOW`** only when all machine readiness gates are
   observed and green, all 18 outcomes are present, no candidate safety/grounding/
   evidence/contract/provider failures exist, no material shared collapse exists,
   certified inputs remain exact, and report/aggregate agree.

Machine decision mapping is not automatic:

| Machine decision | Maximum human claim without additional proof |
|---|---|
| `PROVIDER_FAILURE`, `BLOCKED_BY_CONTRACT`, `BLOCKED_BY_EVIDENCE` | `PROMOTION_EVIDENCE_INCOMPLETE` |
| `BLOCKED_BY_INPUT_REPRESENTATION` | At most `ADVANCE_TO_TEXTUAL_NORMALIZATION`, after row-level semantic/lane/status verification |
| `ITERATE_PROMPT` | `ITERATE_PROMPT` only after excluding input, shared, and representation-only causes |
| `PROMPT_READY_FOR_BROADER_SHADOW` | Readiness disposition only; never cutover authority |

### Required row-level failure classification

Every unique non-exact or failed assertion pattern must be classified as one of:

```text
certified_input_or_gold_defect
shared_control_candidate_failure
evaluator_gold_representation_mismatch
exact_text_normalization_difference
actual_temporal_semantic_failure
actual_temporal_lane_or_status_failure
candidate_safety_or_source_time_failure
provider_or_infrastructure_failure
model_or_contract_noncompliance
```

The report must distinguish observed zeros from null/unobserved metrics. Large headline
`wrong_temporal_value` totals cannot establish prompt failure without row inspection.

## §7 Evidence required to merge

### Evidence ledger

| Guarantee / invariant clause | Owning boundary | Evidence class | Command / scenario | Expected evidence | Stop condition |
|---|---|---|---|---|---|
| Current-main ancestry and sole capability owner | Git / PR | provenance | §0 commands + PR search | Exact base; no sibling owner | stale/competing PR |
| Certified SHA reachable and unchanged | Git | provenance | `cat-file`, ancestor, exact-path diff | Reachable ancestor; no certified diff | missing/non-ancestor/diff |
| Every certified digest exact | filesystem | contract | `sha256sum -c` manifest | all OK before and after calls | any mismatch |
| Frozen prompt/packet/renderer exact | tests + extraction | contract | TL01G tests + prompt hashes | exact identities | drift |
| Runner/schema/test blobs pinned | Git object identity | contract | `git rev-parse HEAD:<path>` | exact §2 blobs | drift |
| Clean provider execution SHA | Git + runner | provenance | clean status + manifests | one full singleton SHA | dirty/multiple/missing |
| Exact six-lane × three-repetition matrix | runner/manifests | contract | live command + inventory | exactly 18 outcomes | partial/duplicate/extra |
| Maximum 18 attempts and zero retry | invocation/artifacts | budget | invocation log + no run-04/second output | ≤18 attempts, one invocation | budget/retry violation |
| Failures remain explicit | manifests/aggregate | regression | inspect run records | codes/diagnostics/null metrics retained | missing treated as zero |
| Aggregate reconstructs manifests | calibration CLI | contract | aggregate/reaggregate validation | IDs/SHA/specs/results agree | mismatch/ambiguity |
| Shared vs candidate-specific causes classified | report | adversarial/manual | row-level comparison | each material pattern classified | unsupported prompt claim |
| Human precedence applied exactly | report | acceptance | aggregate/report comparison | one supported disposition | contradiction |
| Certified/pinned bytes unchanged post-live | Git + hashes | negative proof | repeat preflight + changed-path scan | exact | any mutation |
| No product/cutover scope | diff/report | scope | allowlist scan + non-claims | only §4 tracked paths | extra capability |

### Required pre-live verification

Run from the fresh rebased branch before editing `.gitignore`:

```bash
git fetch --prune origin
git status --short
git rev-parse HEAD
git rev-parse origin/main
git merge-base --is-ancestor origin/main HEAD

git cat-file -e 24679b19ac093cdbefa430cb0e930dff8c8a6dae^{commit}
git merge-base --is-ancestor \
  24679b19ac093cdbefa430cb0e930dff8c8a6dae HEAD

test "$(git rev-parse HEAD:evals/graph_memory_layer/temporal_shadow_prompt_calibration.py)" = \
  "45b01c78f24ada02dcaa4b89bfba6da90c745445"
test "$(git rev-parse HEAD:tests/test_temporal_shadow_prompt_calibration.py)" = \
  "3e4fcaa20ee2ef7aa92f4d485c46c2b671c860d9"
test "$(git rev-parse HEAD:tests/test_temporal_shadow_grounding_path.py)" = \
  "f233fdaba86673eef760ccf42e015ddc175dc2b6"
test "$(git rev-parse HEAD:src/graph_memory/temporal_shadow_extraction.py)" = \
  "bcf279c387869f9fe675221894e8dc55d6640b95"
test "$(git rev-parse HEAD:src/graph_memory/temporal_shadow_extraction_schema.py)" = \
  "05fc8c1a860e187edc4e84cd4b54ea0b3e475e5e"

uv run pytest -q tests/test_temporal_shadow_extraction_tl01g.py
uv run pytest -q \
  tests/test_temporal_shadow_prompt_calibration.py \
  tests/test_temporal_shadow_grounding_path.py
uv run ruff check tests/test_temporal_shadow_extraction_tl01g.py

test ! -e \
  evals/graph_memory_layer/artifacts/temporal_shadow_prompt_calibration/tl01g/promotion-v15
```

Create a temporary checksum file from the exact §2 digest block and run:

```bash
sha256sum -c /tmp/tl01g-v15-adv13-certified.sha256
```

Every row must report `OK`. Also prove no certified byte differs from the certification
commit by running `git diff --exit-code 24679b19… HEAD --` over every path in that
checksum file.

Then modify only `.gitignore` with this exact exception chain and commit it:

```text
!evals/graph_memory_layer/artifacts/temporal_shadow_prompt_calibration/tl01g/promotion-v15/
!evals/graph_memory_layer/artifacts/temporal_shadow_prompt_calibration/tl01g/promotion-v15/calibration/
!evals/graph_memory_layer/artifacts/temporal_shadow_prompt_calibration/tl01g/promotion-v15/calibration/aggregate.json
```

Rerun all pre-live verification, including hashes, tests, absent output directory,
`git diff --check`, and `git status --short`. The worktree must be clean.

### Provider execution commit and authorized live command — invoke once

```bash
EXECUTION_SHA="$(git rev-parse HEAD)"
CERTIFICATION_SHA="24679b19ac093cdbefa430cb0e930dff8c8a6dae"

test "$(printf %s "$EXECUTION_SHA" | wc -c)" -eq 40
git merge-base --is-ancestor "$CERTIFICATION_SHA" "$EXECUTION_SHA"
git status --short                            # must be empty

uv run python evals/graph_memory_layer/temporal_shadow_prompt_calibration.py \
  --development-case \
    evals/graph_memory_layer/examples/temporal_shadow_cohort/temporal-case-tl01f.json \
  --candidate-development-case \
    evals/graph_memory_layer/examples/temporal_shadow_cohort/temporal-case-tl01g.json \
  --holdout-case \
    evals/graph_memory_layer/examples/temporal_shadow_holdout_v15/temporal-case-tl01f.json \
  --candidate-holdout-case \
    evals/graph_memory_layer/examples/temporal_shadow_holdout_v15/temporal-case-tl01g.json \
  --baseline-adversarial-case \
    evals/graph_memory_layer/examples/temporal_shadow_adversarial_v13/temporal-case-tl01f.json \
  --adversarial-case \
    evals/graph_memory_layer/examples/temporal_shadow_adversarial_v13/temporal-case-tl01g.json \
  --model-id gpt-5.4-mini \
  --repetitions 3 \
  --experiment-role promotion \
  --output-dir \
    evals/graph_memory_layer/artifacts/temporal_shadow_prompt_calibration/tl01g/promotion-v15 \
  --holdout-seal-commit "$CERTIFICATION_SHA" \
  --adversarial-seal-commit "$CERTIFICATION_SHA"
```

Do not invoke this live command a second time. Do not print or commit API keys. Use the
repository-root environment-loading contract.

If and only if all 18 exact success/failure manifests exist and aggregate construction
alone failed, one zero-provider invocation with identical arguments plus
`--reaggregate-only` is permitted. Record proof that it made zero provider calls.
If the manifest set is partial, ambiguous, duplicated, or spans multiple repository
SHAs, stop and report incomplete evidence.

### Required post-live verification

```bash
uv run pytest -q tests/test_temporal_shadow_extraction_tl01g.py
uv run pytest -q \
  tests/test_temporal_shadow_prompt_calibration.py \
  tests/test_temporal_shadow_grounding_path.py
uv run ruff check tests/test_temporal_shadow_extraction_tl01g.py
sha256sum -c /tmp/tl01g-v15-adv13-certified.sha256

git diff --check
git merge-base --is-ancestor \
  24679b19ac093cdbefa430cb0e930dff8c8a6dae HEAD

git diff --name-only <REBASED_BASE_SHA>...HEAD
git diff --stat <REBASED_BASE_SHA>...HEAD -- \
  Docs/Plans/HANDOFF-TIMELINE-tl01g-v15-adv13-promotion-matrix.md \
  .gitignore \
  evals/graph_memory_layer/artifacts/temporal_shadow_prompt_calibration/tl01g/promotion-v15/calibration/aggregate.json \
  Docs/Reports/REPORT-tl01g-v15-adv13-promotion-matrix.md
```

Inspect and record:

- exact live-command invocation count;
- provider attempts consumed, maximum 18;
- every lane/cohort/repetition outcome and available response ID;
- full provider execution SHA set, expected singleton equal to `$EXECUTION_SHA`;
- certification SHA, seal verification, prompt hashes, packet, renderer, model, case IDs/digests, and calibration ID;
- success/failure counts and every nullable/unobserved metric by lane and cohort;
- unsafe over-resolution, source leakage, wrong value, wrong lane/status, evidence,
  grounding, model-output, contract, and provider failures;
- assertion-stability rows for every material non-exact or failed pattern;
- control/candidate shared versus isolated failures;
- exact machine decision and diagnostics;
- one human disposition under §6 precedence;
- proof that certified and pinned bytes did not change after calls;
- proof that no retry or second matrix exists.

### Required report structure

`Docs/Reports/REPORT-tl01g-v15-adv13-promotion-matrix.md` must contain:

1. Authoritative human disposition at the top.
2. PR/branch/base, certification SHA, provider execution SHA, final head, model, calibration ID, attempt count, and live invocation count.
3. Frozen prompt/packet/renderer/runner identities.
4. Full six-lane × three-repetition outcome table.
5. Provider response IDs when supplied; explicit `none` when absent.
6. Aggregate metrics with observed/null distinction.
7. Row-level failure-classification table using §6 classes.
8. Shared-control/candidate analysis.
9. Machine decision and why human precedence agrees or overrides it.
10. One selected named successor and explicit non-claims.
11. Pre-live/post-live command results and provenance.
12. Certified digest and pinned-blob verification results.
13. Baseline failures, waivers, stop conditions, and paths outside §4.

### Minimal live proof

```text
Existing surface used:
  temporal prompt calibration CLI

Smallest realistic scenario:
  one exact baseline/candidate × development/V15/Adv13 × three-repetition matrix

Expected observation:
  18 explicit outcomes from one clean SHA plus one aggregate and one bounded disposition

Evidence captured:
  local success/failure manifests, aggregate.json, report, full Git SHAs, response IDs
```

This is an evaluation workflow, not a product surface.

### Baseline failure protocol

For any required deterministic command already failing on the rebased base:

- run the identical command on base and head;
- record exact base/head results and provenance;
- do not call the gate green;
- request an explicit operator waiver only if it remains an acceptance gate;
- do not modify unrelated code to absorb it.

A provider failure is not a baseline failure and consumes attempt budget normally.

## §8 Required review handback

The implementation handback must include:

1. Exact PR URL, branch, rebased base SHA, provider execution SHA, and reviewed head.
2. Confirmation that no second implementation PR/branch or live invocation was created.
3. §1 Mission and merge-ready invariant copied exactly.
4. Nano-commit list and discrete story for each commit.
5. Actual changed paths and focused diff stat against §4.
6. Every §7 command and exact result with provenance.
7. Exact certified digest verification before and after calls.
8. Exact pinned Git blob verification before calls.
9. Live invocation count, attempt count, and proof of zero retry.
10. Complete 18-cell outcome/response-ID table.
11. Full provider execution SHA set and manifest consistency result.
12. Aggregate identity, machine decision, diagnostics, and null/unobserved metrics.
13. Row-level failure classification and shared-vs-isolated analysis.
14. Exactly one human roadmap disposition with precedence reasoning.
15. Confirmation that certified inputs, frozen prompt/packet/renderer, runner, schema,
    thresholds, prior aggregates, graph code, corpus, and Project Sources are unchanged.
16. Baseline failures and waivers; `none` when none.
17. Paths outside §4; `none` or stop report.
18. Stop conditions encountered and resolution; `none` when none.
19. Named successor and all still-false capabilities.
20. Confirmation that the authoritative handoff was implemented without compressed or omitted constraints.

## §9 Acceptance rubric

- [ ] Exactly one capability was delivered: one certified TL01G promotion matrix and disposition.
- [ ] Current-main ancestry, certification ancestry, pinned Git blobs, and every certified digest verified before calls.
- [ ] `.gitignore` changed only for the exact promotion-v15 aggregate exception.
- [ ] Provider execution used one clean full SHA and exact frozen identities.
- [ ] The live command ran once, consumed no more than 18 attempts, and was not retried.
- [ ] Exactly one unambiguous outcome exists for each of the 18 specs, or the report truthfully says evidence incomplete.
- [ ] Failures, missing response IDs, and null/unobserved metrics remain explicit.
- [ ] Aggregate, manifests, and report agree on identities, outcomes, diagnostics, and machine decision.
- [ ] Every material non-exact/failure pattern has row-level classification.
- [ ] Shared control/candidate failures are not mislabeled candidate prompt defects.
- [ ] `ADVANCE_TO_TEXTUAL_NORMALIZATION` is claimed only for representation-only blockers.
- [ ] `ITERATE_PROMPT` is claimed only for isolated candidate-specific defects on certified evidence.
- [ ] `PROMPT_READY_FOR_BROADER_SHADOW` is claimed only when every readiness condition is observed and green.
- [ ] A readiness disposition makes no cutover, graph-authority, API, UI, or cross-surface claim.
- [ ] Certified and pinned bytes remain unchanged after calls.
- [ ] Prior artifacts and observed cohorts remain untouched.
- [ ] Only §4 tracked paths changed.
- [ ] Every required proof has a produced result and provenance, or an explicit operator waiver.
- [ ] Exactly one conditional successor is selected; it remains unimplemented.

## Stop conditions

Stop immediately and report rather than expanding scope when any of these becomes true:

1. Current main no longer preserves every pinned Git blob or certified digest.
2. Certification SHA `24679b19…` is missing, unreachable, or not an ancestor.
3. Another PR/branch or existing artifact owns `promotion-v15` execution.
4. The output directory already exists before the authorized call.
5. A required fix touches prompts, packet, renderer, runner, schema, thresholds,
   extraction, certified inputs, owning tests, prior aggregates, or graph/product code.
6. The runner cannot consume V15/Adv13 without a new schema or compatibility path.
7. The provider command is invoked more than once, attempts exceed 18, or retry is requested.
8. The manifest set is partial, ambiguous, duplicated, or spans multiple execution SHAs.
9. Missing comparison metrics are being interpreted as observed zeros or safety evidence.
10. Shared control/candidate failure is being used to justify candidate-only iteration.
11. A post-observation certified-input or gold defect is discovered.
12. Branch history is rebased, squashed, amended, or force-pushed after the first call.
13. Any tracked path outside §4 becomes necessary.
14. The requested outcome expands into normalization implementation, prompt authoring,
    broader-shadow dogfood, producer cutover, graph adoption, or surface integration.
15. Evidence cannot support exactly one disposition under §6 precedence.

Use this stop-report shape:

```text
Stop condition:
Why the current mission cannot absorb it:
Invariant clause affected:
Required evidence now missing:
New public/durable contract discovered:
Affected observable paths or ownership layers:
Provider attempts already consumed:
Certification/provider SHAs involved:
Observed manifest set:
Proposed successor slice:
Operator decision needed:
```

## Named conditional successors

The final report selects exactly one of these; none is implemented here:

| Final disposition | Named successor |
|---|---|
| `PROMOTION_EVIDENCE_INCOMPLETE` | Root-cause-specific recovery handoff. If an input defect is found after calls, author a new certified cohort pair; never repair/rerun V15/Adv13. |
| `ADVANCE_TO_TEXTUAL_NORMALIZATION` | `TIMELINE: design exact textual normalization and grounding policy` |
| `ITERATE_PROMPT` | `TIMELINE: design tl01h-v1 from named certified failures` |
| `PROMPT_READY_FOR_BROADER_SHADOW` | `TIMELINE: design broader-shadow acceptance and dogfood gate` |

The broader-shadow successor is deliberately an acceptance/design slice, not cutover.
It must account for the stability of Build, Timeline, and Statblock development before
any simulated or real producer adoption.
