---
pr_body_template: |
  ## Handoff pointer
  - Conversation: `TL01G V15 / Adv V13 Cohort Certification`
  - Flow / agent: `TIMELINE`
  - Direction: DESIGN → CODE
  - Handoff: `Docs/Plans/HANDOFF-TIMELINE-tl01g-v15-adv13-cohort-certification.md`
  - Branch: `timeline/tl01g-v15-adv13-cohort-certification`
  - PR mode: **this PR is the implementation PR; do not open a second PR**

  ## Execution pointer
  - Initial branch base: `d3b4060fabd6c2b7fff0403af260637845c86dd9`
  - Predecessor: PR #496 merged as `eefc8927c3e679c1688d1dd85f565f8d9eb3d9c8`
  - Frozen control/candidate: `tl01f-v1` / `tl01g-v1`
  - Certification pair: holdout V15 / adversarial V13
  - Provider budget: **0 calls**; this PR must not execute a live matrix

  ## Verification pointer
  - Base/head: TODO after implementation begins
  - Certification SHA and fixture digests: TODO
  - Changed paths: §4 allowlist only
  - Verification: TODO from §7 evidence ledger

  The checked-in handoff, cumulative diff, nano commits, certified fixture bytes,
  and independently rerun verification are the review contract. The PR body is
  transport metadata only. Provider execution is a separate successor PR.
---

# HANDOFF — TIMELINE: Certify TL01G V15 / Adv V13 Cohorts

**Created:** 2026-08-02.  
**Status:** ACTIVE — dispatch exactly one pre-live certification capability.  
**Canonical handoff path:** `Docs/Plans/HANDOFF-TIMELINE-tl01g-v15-adv13-cohort-certification.md`  
**Conversation name:** `TL01G V15 / Adv V13 Cohort Certification`  
**Flow / agent:** `TIMELINE`  
**Handoff direction:** `DESIGN → CODE`  
**Design agent:** GPT-5.6 Thinking, DungeonBuddy project conversation  
**Code agent:** TIMELINE code agent operating on this PR branch  
**PR title:** `TIMELINE: certify TL01G V15 and Adv V13 cohorts`  
**Branch:** `timeline/tl01g-v15-adv13-cohort-certification`  
**Initial branch base:** `d3b4060fabd6c2b7fff0403af260637845c86dd9`  
**Predecessor merge:** PR #496, merge `eefc8927c3e679c1688d1dd85f565f8d9eb3d9c8`  
**Predecessor doc-sync:** `d3b4060fabd6c2b7fff0403af260637845c86dd9`

> **Same-PR implementation gate:** This open PR is the sole implementation surface
> for this capability. Do not merge it as a handoff-only PR and do not open a
> sibling implementation PR. Rebase this branch onto current `origin/main` before
> fixture work if main has moved, then push every implementation and review-response
> nano commit back to this PR.
>
> **Zero-provider gate:** This PR authorizes **no live model/provider call**. It must
> not create run manifests, failure manifests, calibration artifacts, aggregate
> output, or a promotion disposition. Its only outcome is a provider-unobserved,
> independently reviewable cohort pair certified for a later execution PR.
>
> **Dispatch gate:** No fixture authoring begins until the exact current-main base,
> frozen prompt identities, retired cutoffs, and existing future-cohort guards are
> reverified. The checked-in handoff is complete authority and must not be compressed,
> replaced, or rewritten by the implementation agent.

## Shared vocabulary

| Term | Definition |
|---|---|
| **Certification** | A pre-live claim that one exact fixture/gold/case/test byte set satisfies all declared integrity, independence, Gate-faithfulness, and pairing proofs. It is not model evidence and cannot support prompt promotion. |
| **Certified cohort pair** | Holdout V15 and adversarial V13 at one recorded certification SHA, provider-unobserved, with exact digests and green owning tests. |
| **Evaluation stimulus** | Synthetic Markdown under the cohort's `sources/` directory used only as controlled evidence input. It is not canonical campaign prose, production graph input, runtime content, or a Project Source. |
| **Owned evidence** | An evidence registry entry whose path, line range, identifier, and source text belong to the same cohort and are cited by the annotation under review. |
| **Gate-faithful gold** | Gold whose status, lane, source phrase, temporal value, and abstention/resolution rationale are licensed by the selected proposition and owned evidence under frozen TL01G Gates A–F. |
| **Source-time leakage** | Treating the session or timestamp of the evidence document as the fictional occurrence or validity time when the proposition/evidence does not assert that time. |
| **Certification SHA** | The first clean full Git SHA containing final source, base, gold, paired cases, audit, and owning tests that passes §7. It must remain reachable and the certified bytes must not change afterward. |
| **Execution PR** | A later, separately reviewed PR that consumes certified bytes without editing them and runs the bounded provider matrix. |
| **Stop condition** | A fact that invalidates this slice or requires a different invariant; implementation stops and reports rather than absorbing the work silently. |

## Agent flow and nano-commit contract

Use the `TIMELINE` flow and keep one capability in this PR.

Required nano-commit story:

1. `docs(timeline): add v15 adv13 cohort certification handoff` — already opened by the design agent.
2. `test(timeline): define v15 adv13 certification gates` — test/helper changes only; no cohort files and no provider calls.
3. `test(timeline): author v15 holdout certification fixtures` — V15 fixture, source, audit, and paired cases.
4. `test(timeline): author adv13 certification fixtures` — Adv V13 fixture, source, audit, and paired cases.
5. `docs(timeline): record v15 adv13 certification` — certification report and README seal pointers only after all §7 commands pass on a clean tree.
6. Review-response nano commits, each addressing one named finding. If certified bytes change, invalidate the previous certification SHA, rerun all §7 evidence, and record a new certification SHA without rewriting history.

Do not squash, amend, or force-push after a certification SHA is published in the
report. There are no provider observations in this PR, so review-directed fixture
repair is allowed before merge, but every repair creates a new certification SHA
and leaves the prior attempt visible in history.

## §0 Reanchor and workspace reset

### Source and repository authority

The project-source packet is context, not implementation authority:

- `CORPUS-ANCHOR.md` is a source-location anchor. It confirms canonical campaign
  prose lives under `corpus/eldyrwild-markdown/`; this PR does not consume or edit it.
- `GRAPH-MEMORY-SUPERGRAPH-ARCHITECTURE-ROADMAP.md` in Project Sources is a
  superseded stub. Current repository authority is the Campaign Supergraph
  architecture, roadmap, and tracker on `main`.
- `LLM-graph-construction.md` is research-only. It supports provenance-first eval
  discipline but does not set sequence or implementation scope.
- Synthetic files under `evals/.../sources/` are controlled evaluation stimuli,
  not canonical campaign/worldbuilding source artifacts.

Current repository anchors at dispatch:

| Authority | Current fact |
|---|---|
| DungeonMindBuddy `main` | `d3b4060fabd6c2b7fff0403af260637845c86dd9` at handoff creation |
| PR #496 | Merged; V14/Adv V12 retired with `PROMOTION_EVIDENCE_INCOMPLETE` |
| Frozen candidate | `tl01g-v1`; no successor prompt is authorized |
| Retired cutoffs | holdout `14`, adversarial `12` |
| DungeonMind `main` | `c5604c10eb1785a6c432b3999d27b851232ebb85`; finalized contribution review adoption merged, but this PR consumes no DungeonMind API or package |
| Other workstreams | Build and Statblock remain active; this PR must not simulate cutover or cross-surface integration |

### Fresh branch and worktree

Do not reuse the merged PR #496 worktree or any retired TL01 branch.

```bash
git fetch --prune origin
git switch timeline/tl01g-v15-adv13-cohort-certification
git rebase origin/main
git status --short
git rev-parse HEAD
git rev-parse origin/main
git merge-base --is-ancestor origin/main HEAD
```

Required result before implementation:

```text
worktree: clean
origin/main: ancestor of HEAD
exact rebased origin/main SHA: recorded in PR handback
no V15 or Adv V13 directory already exists on current main
no sibling Timeline PR owns the same cohort versions
```

If main gains any holdout version above 14 or adversarial version above 12 before
fixture authoring, stop. Re-versioning and cumulative novelty ownership require a
new handoff amendment before work continues.

## §1 Mission and merge-ready invariant

**Mission:** The Timeline steward can merge one provider-unobserved, Gate-faithful
V15 / Adv V13 cohort pair so a later execution PR can test frozen `tl01g-v1`
without authoring or repairing gold under observation.

**Merge-ready invariant:** At one recorded certification SHA descended from current
main, V15 and Adv V13 are synthetic, mutually independent, cumulatively novel,
exactly paired between frozen `tl01f-v1` and `tl01g-v1`, fully bound to owned
evidence, and Gate-faithful for every selected assertion; all certification tests
pass, no provider call or calibration artifact exists, and the certified fixture,
gold, source, case, audit, and owning-test bytes remain unchanged for the successor
execution PR.

### Pre-dispatch critique

| Question | Answer |
|---|---|
| Can one invariant govern every claimed observable path? | **Yes.** This slice creates and certifies one immutable evaluation asset. Provider execution, model judgment, prompt iteration, and product cutover are separate invariants and are excluded. |
| Why split certification from execution? | PR #496 authored fixtures and spent the live matrix budget in one PR; a sealed gold defect was discovered only after observation. Separating the assets from execution gives review a complete provider-unobserved fixture surface and makes any repair cheap, explicit, and non-contaminating. |
| What adversarial sequence is most likely to falsify it? | Author plausible synthetic prose → mechanically bind audit/gold → let session metadata or a related phrase license an unsupported temporal value → certify → later spend provider budget on invalid gold. |
| Would §7 detect that failure? | **Only if tests exercise every resolved occurrence and every valid-time boundary at the owning evidence boundary, and distinguish proposition time from evidence-document time.** The handoff requires those proofs for both future cohort families before certification. |
| Which boundary is easiest to under-test? | Session-valued occurrence/validity. Existing helpers may find a session number in evidence metadata even when the proposition does not assert that fictional time. V15/Adv13 certification must require proposition/source licensing, not registry metadata alone. |
| What fact forces a stop or split? | Need for a prompt, renderer, packet, schema, evaluator, calibration-runner, or production-code change; inability to construct independent cohorts; any provider call; concurrent ownership of V15/Adv13; or a second durable capability such as normalization policy. |

## §2 Context, authority, and boundaries

| Field | Required content |
|---|---|
| Parent authority | `Docs/Reports/REPORT-tl01g-v14-fresh-promotion-evidence.md`; archived PR #496 handoff; `Docs/Reports/REPORT-tl01g-resolution-proof-abstention-gate.md` |
| Repository rules | `AGENTS.md`; `.cursor/rules/external-agent-pr-loop.mdc`; `.cursor/skills/external-agent-pr-loop/SKILL.md` |
| Initial base revision | `d3b4060fabd6c2b7fff0403af260637845c86dd9` |
| Required implementation base | Exact current `origin/main` after §0 rebase, recorded before test changes |
| Predecessor contract | V14/Adv V12 retired; comprehensive `_collect_resolved_value_grounding_defects` guard exists for successors above cutoffs 14/12 |
| Exact input consumed | Frozen prompt identities, existing TL01G test helpers, prior cohorts as negative/novelty history, new synthetic V15/Adv13 evidence stimuli |
| Independently useful output | One certified, provider-unobserved cohort pair with exact certification SHA and report |
| Named successor | `TIMELINE: execute certified TL01G promotion matrix` consuming V15/Adv13 without fixture edits |
| What remains false | No prompt is promoted; no matrix is observed; no `tl01h-v1`; no broader shadow acceptance; no production temporal producer or graph authority |
| Cross-repo boundary | No DungeonMind code, package, schema, API, migration, or cutover is consumed or changed |
| Explicit non-goals | Provider calls; aggregate/reporting of model output; prompt/packet/renderer edits; textual normalization; graph/kernel/UI/API/event/role work; corpus ingest; Project Source changes |

### Frozen predecessor identities

| Identity | Required exact value |
|---|---|
| Control prompt | `tl01f-v1` |
| Control SHA256 | `7a9d27c3a9980893f18757d7a5fe0612cf67f9aad8dfd2ccb20f9e3c667b7143` |
| Candidate prompt | `tl01g-v1` |
| Candidate SHA256 | `3af1e470e304008d2490ba73e1a53628519c211bb54e17a10cd4c694beae9013` |
| Packet | `tl01c-packet-v1` |
| Renderer | `render_temporal_shadow_user_content_v2` |
| Later execution model | `gpt-5.4-mini` — recorded for successor compatibility only; not called here |
| Retired holdout cutoff | `LAST_RETIRED_HOLDOUT_VERSION = 14` |
| Retired adversarial cutoff | `LAST_RETIRED_ADVERSARIAL_VERSION = 12` |
| Prior observed cohorts | V8–V14 / Adv V6–V12 are non-promotion history; never copy as gold authority |

### Required read order

Before changing files, read:

1. This handoff.
2. `Docs/Reports/REPORT-tl01g-v14-fresh-promotion-evidence.md`.
3. `evals/graph_memory_layer/examples/temporal_shadow_holdout_v14/README.md`.
4. `evals/graph_memory_layer/examples/temporal_shadow_adversarial_v12/README.md`.
5. `tests/test_temporal_shadow_extraction_tl01g.py`.
6. `src/graph_memory/temporal_shadow_extraction.py` **read-only** for frozen Gate A–F semantics.
7. `evals/graph_memory_layer/temporal_shadow_prompt_calibration.py` **read-only** to preserve later case compatibility.
8. V14/Adv12 and earlier cohorts as defects/novelty history, not templates to paraphrase.

If current-main identities or cutoffs differ, or the successor guard no longer has
both holdout and adversarial coverage, stop and report before implementation.

## §3 Observable paths and adversarial sequences

| Path | Current behavior | Required behavior | Same invariant? | Owning boundary |
|---|---|---|---:|---|
| V15 discovery | No directory above holdout cutoff 14 | Exactly one V15 directory is auto-discovered and all future-holdout guards execute | Yes | TL01G test suite |
| Adv V13 discovery | No directory above adversarial cutoff 12 | Exactly one Adv V13 directory is auto-discovered and all future-adversarial guards execute | Yes | TL01G test suite |
| Paired control/candidate cases | No V15/Adv13 cases | Within each cohort, F/G cases differ only by `case_id` and `prompt_version` | Yes | case JSON + pairing test |
| Target set | Prior cohorts have fixed selected IDs | Each pair selects the exact same unique assertion IDs; selected IDs equal base assertion IDs and gold annotation IDs with no extras/misses | Yes | fixture contract test |
| Owned evidence | Prior defects included weak phrase/value licensing | Every assertion and annotation resolves only cohort-owned evidence IDs and source files; no path escapes the cohort directory | Yes | evidence registry tests |
| Textual occurrence | Raw phrase can drift from source | `raw_expression` and `source_phrase` are exact contiguous grounded substrings of owned evidence and modify the selected proposition | Yes | comprehensive grounding helper |
| Session occurrence | Evidence metadata can masquerade as fictional time | Session value is accepted only when the proposition/source phrase or same owned span explicitly licenses occurrence in that session; source registry identity alone is insufficient | Yes | new source-time licensing test/helper |
| Valid start/end | V12 exposed unsupported values and weak cue fidelity | Each non-null boundary independently has a direction-compatible cue in the grounded source phrase and an evidence-grounded value concerning the proposition | Yes | Gate E3/D helper |
| Abstention statuses | Mechanical audit can agree with bad gold | `unresolved`, `ambiguous`, and `not_applicable` rows have null temporal lanes and a proposition-first rationale; ambiguity requires competing proposition readings | Yes | gold/audit contract tests |
| Novelty | Successors can paraphrase observed templates | Semantic fingerprints, exact span hashes, vocabulary, source templates, and proposition-template Jaccard are disjoint against retired cohorts and the sibling successor | Yes | cumulative novelty tests |
| Certification | No provider-unobserved successor asset | Clean certification SHA and report record exact identities/digests and zero provider calls | Yes | Git history + report |
| Provider execution | Previously coupled to authoring | Explicitly absent; any invocation or artifact is a merge blocker | Yes | changed-path/artifact scan |

### Ordered failure sequences

| Sequence | Required safe outcome | Owning proof |
|---|---|---|
| Evidence file is tagged Session 15 → proposition lacks session-time claim → gold uses `session-15` | Certification fails; evidence-document time cannot license proposition time | source-time licensing tests |
| Source contains one transition → annotation cites a different phrase/value in same span | Certification fails on exact source phrase/value and proposition-bound cue | comprehensive grounding test |
| Start cue exists but gold chooses valid end, or vice versa | Certification fails direction-specific Gate E3 | boundary proof tests |
| Future promise names a prerequisite but no execution time → gold resolves | Certification fails Gate B/D rationale; expected unresolved | explicit case-class test + audit binding |
| Persistent state says “still/remains” without boundary → gold invents start/end | Certification fails; expected not_applicable | explicit case-class test |
| Ambiguous row relies on surrounding evidence rather than proposition fork | Certification fails proposition-first ambiguity check | ambiguity contract test |
| V15/Adv13 replay prior proposition skeleton with renamed entities | Certification fails cumulative proposition-template Jaccard | novelty test |
| V15 and Adv13 share vocabulary/source template/assertion IDs | Certification fails mutual-disjointness checks | sibling independence test |
| Review finds defect after certification report | Invalidate old certification SHA; repair before merge; rerun all §7; publish new SHA; no history rewrite | commit history + report |
| Any provider call occurs before merge | Stop; delete no evidence, report violation, and re-brief. This PR cannot become execution authority | provider-absence proof |

## §4 Files in scope (allowlist)

Every changed path must appear here or fit one bounded source exception.

| Action | Path | Purpose |
|---|---|---|
| Create | `Docs/Plans/HANDOFF-TIMELINE-tl01g-v15-adv13-cohort-certification.md` | Complete design authority for this same-PR implementation |
| Modify | `tests/test_temporal_shadow_extraction_tl01g.py` | Add V15/Adv13 constants, explicit non-skippable fixture contracts, comprehensive source-time/value/Gate-faithfulness tests, and certification guards |
| Create | `evals/graph_memory_layer/examples/temporal_shadow_holdout_v15/README.md` | State synthetic evaluation role, provider-unobserved certification, certification SHA, and immutability contract |
| Create | `evals/graph_memory_layer/examples/temporal_shadow_holdout_v15/GOLD-AUDIT.md` | Bind every selected assertion to proposition class, status, lane, value, source phrase, evidence refs/files, rejected alternative, and Gate rationale |
| Create | `evals/graph_memory_layer/examples/temporal_shadow_holdout_v15/base-contribution.json` | Fresh holdout assertions and cohort-owned evidence refs |
| Create | `evals/graph_memory_layer/examples/temporal_shadow_holdout_v15/gold-overlay.json` | Human-reviewed, Gate-faithful temporal gold |
| Create | `evals/graph_memory_layer/examples/temporal_shadow_holdout_v15/temporal-case-tl01f.json` | Frozen control case |
| Create | `evals/graph_memory_layer/examples/temporal_shadow_holdout_v15/temporal-case-tl01g.json` | Frozen candidate case paired to control except prompt identity |
| Create | `evals/graph_memory_layer/examples/temporal_shadow_adversarial_v13/README.md` | State synthetic adversarial role, provider-unobserved certification, certification SHA, and immutability contract |
| Create | `evals/graph_memory_layer/examples/temporal_shadow_adversarial_v13/GOLD-AUDIT.md` | Bind every selected adversarial assertion to proposition, expected abstention/resolution, lane/value, evidence, rejected alternative, and Gate rationale |
| Create | `evals/graph_memory_layer/examples/temporal_shadow_adversarial_v13/base-contribution.json` | Fresh adversarial assertions and cohort-owned evidence refs |
| Create | `evals/graph_memory_layer/examples/temporal_shadow_adversarial_v13/gold-overlay.json` | Human-reviewed, Gate-faithful adversarial gold |
| Create | `evals/graph_memory_layer/examples/temporal_shadow_adversarial_v13/temporal-case-tl01f.json` | Frozen control adversarial case |
| Create | `evals/graph_memory_layer/examples/temporal_shadow_adversarial_v13/temporal-case-tl01g.json` | Frozen candidate adversarial case paired to control except prompt identity |
| Create | `Docs/Reports/REPORT-tl01g-v15-adv13-cohort-certification.md` | Record certification SHA, exact digests, evidence results, zero-call proof, and successor execution contract |

### Bounded discovery exception 1 — V15 evaluation stimuli

```text
Directory: evals/graph_memory_layer/examples/temporal_shadow_holdout_v15/sources/
Maximum additional paths: 12
Allowed path kinds: UTF-8 Markdown files only
Decision rule: include only a synthetic stimulus directly referenced by a V15
               evidence registry entry; every file must be named in GOLD-AUDIT.md.
```

### Bounded discovery exception 2 — Adv V13 evaluation stimuli

```text
Directory: evals/graph_memory_layer/examples/temporal_shadow_adversarial_v13/sources/
Maximum additional paths: 10
Allowed path kinds: UTF-8 Markdown files only
Decision rule: include only a synthetic stimulus directly referenced by an Adv V13
               evidence registry entry; every file must be named in GOLD-AUDIT.md.
```

No other discovery exception exists. If implementation requires another path,
stop and request a handoff amendment before editing it.

## §5 Files and capabilities explicitly out of scope

| Path / capability | Why this slice must not touch or claim it |
|---|---|
| `src/graph_memory/temporal_shadow_extraction.py` | Frozen prompt, packet, renderer, schema, and production extraction behavior are experiment inputs, not certification scope |
| `evals/graph_memory_layer/temporal_shadow_prompt_calibration.py` | Provider execution, thresholds, aggregate decisions, and manifest behavior belong to the successor execution PR |
| `tests/test_temporal_shadow_prompt_calibration.py` | Runner contract is consumed unchanged; a required runner fix is a stop/split |
| `tests/test_temporal_shadow_grounding_path.py` | Predecessor smoke contract is consumed unchanged |
| `.gitignore` | No calibration artifact is authorized, so no artifact path should be unignored |
| Any `evals/.../artifacts/temporal_shadow_prompt_calibration/**` path | Zero provider calls and zero aggregate output in this PR |
| V14 / Adv V12 fixture, gold, source, audit, case, README, or aggregate | Retired immutable evidence; read-only negative history |
| V8–V13 / Adv V6–V11 | Retired observed evidence; no edits |
| `Docs/Reports/REPORT-tl01g-v14-fresh-promotion-evidence.md` | Parent authority; post-merge doc sync may point to successor certification later |
| `Docs/Reports/REPORT-tl01g-resolution-proof-abstention-gate.md` | Predecessor report is outside this implementation allowlist |
| `Docs/Roadmaps/**`, `Docs/Plans/PR-TRACKER-campaign-supergraph.md` | Timeline evaluation does not amend the Campaign Supergraph critical path in this PR |
| `corpus/**` | Canonical campaign prose is not an evaluation-stimulus workspace |
| DungeonMind repository or packages | Other foundational work is settling; no cutover, dependency, or backport here |
| `tl01h-v1` or any prompt revision | No trustworthy observed candidate-specific failure exists yet |
| Textual normalization/evaluator relaxation | Separate policy capability; certification must expose representation differences rather than redefine equality |
| Graph/Kernel, contributions, events, roles, projection, API, UI, or surface work | Separate product capabilities after producer acceptance |
| Provider execution, run manifests, aggregate, or promotion report | Named successor only |

## §6 Implementation contract and conditional matrices

```text
Input:
  current-main frozen TL01F/TL01G identities
  retired cohort history through holdout V14 / adversarial V12
  existing future-cohort discovery and comprehensive grounding helpers
  newly authored synthetic V15 / Adv V13 stimuli and assertions

Output:
  one provider-unobserved certified V15 / Adv V13 cohort pair
  one clean certification SHA
  one certification report with exact identities, digests, tests, and zero-call proof

Invariant:
  the §1 merge-ready invariant

Failure behavior:
  fixture/gold/audit defect before certification → repair in discrete commit, rerun all proofs
  defect after certification but before merge → invalidate certification, repair, publish new SHA
  required production/runner change → stop and split
  provider call or model artifact → stop; this PR is no longer valid under current handoff
  concurrent successor version appears on main → stop and re-version through handoff amendment

Replay / idempotency:
  rerunning deterministic certification tests on identical bytes → same results
  recomputing file digests on identical bytes → same digests
  changed certified byte → certification report/SHA becomes stale and merge is blocked

Trust boundary:
  Verifies: fixture shape, exact pairing, target-set equality, owned evidence,
            grounded source phrases/values, Gate E3 direction, source-time licensing,
            abstention null lanes, cumulative novelty, sibling disjointness, zero artifacts
  Records without proving: future model behavior and future promotion disposition
```

### A. State and fallback matrix

| State | Required behavior | Fallback permitted? |
|---|---|---|
| Cohorts absent | Tests may return no successors on base; implementation creates exact V15/Adv13 | No alternate versions without amendment |
| Draft fixtures present, tests red | Continue local review/repair; no certification claim | No provider call |
| All proofs green, tree dirty | Do not certify; commit intended bytes and rerun on clean tree | No |
| Certified SHA recorded | Source/base/gold/case/audit/test bytes frozen for successor execution | No silent edits |
| Review defect after certification | Publish explicit invalidation/new certification SHA after repair | No history rewrite |
| Main changes unrelated before merge | Rebase only before certification; rerun all proofs | No cherry-pick from old Timeline branches |
| Main adds competing successor cohort | Stop and re-brief versions/novelty pool | No first-win ownership |
| Provider unavailable | Not applicable; provider is never called | No |

### B. Identity matrix

| Identity | Required rule | Ambiguity behavior | Fallback permitted? |
|---|---|---|---|
| Prompt identity | Exact frozen versions and SHA256 values | Any mismatch blocks certification | No |
| Cohort version | Exactly holdout V15 and adversarial V13 | Existing/conflicting directory blocks work | No |
| Assertion IDs | Unique within cohort and disjoint from all prior/sibling cohorts | Duplicate or overlap blocks certification | No |
| Evidence IDs | Unique, cohort-owned, exact registry lookup | Missing/foreign/duplicate blocks certification | No |
| Selected target set | Exact equality across F/G case, base assertions, and gold annotations | Extra/missing/order drift blocks certification | No |
| Source paths | Repo-relative paths under the same cohort `sources/` directory | Escape or missing file blocks certification | No |
| Certification SHA | Full reachable clean 40-character commit SHA | Stale/unreachable/dirty blocks report | No |

### C. Persistence and replay matrix

| Operation | Durable representation | Round-trip guarantee | Duplicate / replay behavior | Compatibility | Reversion |
|---|---|---|---|---|---|
| Load paired case | JSON case files | Loader sees exact frozen prompt identity and same fixture target set | Repeated load is identical | Existing loader only | Revert PR |
| Resolve evidence | Case evidence registry + Markdown span | Exact path/line text and ID resolve deterministically | Repeated resolution identical | Existing evidence schema | Revert PR |
| Load gold | `gold-overlay.json` | Every selected assertion has exactly one annotation and stable typed values | Repeated load identical | Existing overlay schema | Revert PR |
| Human audit | `GOLD-AUDIT.md` | Machine-checked rows bind exact fixture/evidence facts and human Gate rationale | Duplicate rows/IDs fail | New columns are local certification documentation, not a runtime schema | Revert PR |
| Certification | Git SHA + report | Recorded digests match bytes at certification SHA | Changed bytes require new certification | Successor execution verifies same bytes | Revert PR before execution |

### D. Predecessor-to-consumer mapping

**Grounding source:** current-main TL01G loader/tests and PR #496 retirement report.

| Predecessor fact | Real shape | V15/Adv13 consumer rule | Proof |
|---|---|---|---|
| Frozen prompt IDs | version + SHA256 | Case identity must match exact values | prompt-freeze and case tests |
| Retired cutoffs | integers 14 / 12 | Auto-discovery must find V15 / Adv13 | discovery tests |
| Comprehensive grounding helper | defect list over resolved occurrence/boundary/source phrases | Must return `[]` for both cohorts | explicit certification test |
| Gate E3 boundary helper | proposition-bound, direction-specific, value-grounded | Apply independently to every non-null start/end | owning tests |
| V14/Adv12 defect | unsupported value/cue discovered post-observation | Add negative regression and source-time proof so class cannot recur | regression + certification tests |
| Paired case loader | control/candidate case JSON | Differ only in `case_id` and `prompt_version` | paired-case tests |
| Calibration runner | accepts case paths and frozen identities | Read-only compatibility target for successor | loader-only smoke; no runner execution |

## §6.1 Cohort composition contract

The agent invents new entities, places, predicates, prose, and exact values. Do not
copy or lightly paraphrase prior cohort propositions. The semantic classes below
are requirements, not prose templates.

### Holdout V15 — minimum 12 selected assertions

V15 must contain at least one row for each class:

1. resolved occurrence with explicitly licensed session value;
2. resolved occurrence with exact textual point;
3. resolved valid-start with explicitly licensed session value;
4. resolved valid-start with exact textual value;
5. resolved valid-end with explicitly licensed session value;
6. resolved valid-end with exact textual value;
7. persistent-state restatement with no narrated boundary → `not_applicable`;
8. identity/classification statement with no temporal proposition → `not_applicable`;
9. future commitment without execution time → `unresolved`;
10. temporally eligible proposition with missing/unsupported value → `unresolved`;
11. proposition-level competing temporal readings → `ambiguous` with null lanes;
12. source-time licensing trap whose correct result is abstention rather than using the evidence episode time.

At least one valid-time row must contain both start and end only if each boundary
has independent source phrase/value proof. A dual-boundary row is optional; do not
add one merely for complexity.

### Adversarial V13 — minimum 10 selected assertions

Adv V13 must include distinct constructions covering:

1. source-time leakage with a misleading session-tagged evidence document;
2. a future prerequisite/condition that is not an execution-time value;
3. a textual occurrence whose exact phrase is embedded in distractor prose;
4. a valid-start candidate with a related but wrong value elsewhere in the span;
5. a valid-end candidate with a wrong-direction transition cue nearby;
6. a persistent-state `still`/`remains` restatement without a boundary;
7. proposition-level ambiguity that surrounding evidence cannot collapse;
8. a historical occurrence with a textual value and an attractive wrong valid-time lane;
9. a source-phrase copy trap where copying a larger/smaller phrase changes the value contract;
10. an assertion with temporal words in evidence but no eligible temporal proposition.

Adversarial rows may resolve or abstain as justified, but the audit must name the
tempting wrong answer and the exact Gate that rejects it.

### GOLD-AUDIT required columns

Both audits must contain one row per selected assertion with these columns:

```text
Assertion ID
Assertion proposition
Gate B eligibility
Proposition class
Gold status
Gold lane
Temporal value(s)
Source phrase
Evidence ref IDs
Owned source file(s)
Rejected alternative
Gate rationale
Audit result
```

Tests must bind all machine-checkable columns to base, case, evidence, and gold.
`Gate rationale` and `Rejected alternative` remain human review surfaces but must
be nonblank and reference the relevant Gate letter(s).

## §7 Evidence required to merge

| Guarantee / invariant clause | Owning boundary | Evidence class | Command / scenario | Expected evidence | Stop condition |
|---|---|---|---|---|---|
| Current-main ancestry and uncontested versions | Git / PR | provenance | `git rev-parse`, ancestor check, directory/PR search | exact base; no existing V15/Adv13 owner | stale or competing version |
| Frozen prompt/packet/renderer identities unchanged | extraction registry + tests | contract | focused TL01G tests | exact versions and hashes | any identity drift |
| Exactly paired F/G cases | case files + loader | contract | paired-case tests | only `case_id` and `prompt_version` differ | any fixture/target drift |
| Exact target-set equality | base/gold/cases | adversarial contract | explicit set/order tests | one-to-one exact selected IDs | extras, misses, duplicates |
| Cohort-owned evidence only | evidence registry + source resolver | contract | path/ID/span tests | all refs resolve under same cohort | foreign/missing/path escape |
| Every resolved value/source phrase grounded | gold + owned evidence | owning regression | `_collect_resolved_value_grounding_defects(V15/Adv13)` | empty defect lists | any defect |
| Session values licensed by proposition/source, not registry metadata alone | source-time helper + fixtures | adversarial | positive/negative unit cases and cohort audit | metadata-only case rejected; explicit fictional-time case accepted | metadata-only value passes |
| Valid start/end direction and proposition binding | Gate E3 helper | adversarial | boundary tests over every non-null boundary | independent start/end proof | wrong direction or unrelated cue passes |
| Abstention rows have null lanes and proposition-first rationale | gold/audit | contract | status/lane/audit tests | unresolved/ambiguous/not_applicable all null; rationale nonblank | invented value/lane |
| Holdout cumulative novelty | fingerprints/Jaccard | regression | auto-discovery tests | V15 disjoint from retired holdouts | overlap threshold/fingerprint collision |
| Adversarial cumulative novelty | source/proposition templates | regression | auto-discovery tests | Adv13 disjoint from retired adversarial cohorts | overlap threshold/template replay |
| Sibling mutual independence | IDs, vocabulary, source templates | adversarial | V15↔Adv13 tests | no shared IDs/reserved vocabulary/template replay | sibling leakage |
| Synthetic source role truthful | README/audit/path | documentation contract | README content + path tests | explicitly non-corpus/non-runtime/non-Project-Source | authority ambiguity |
| Zero provider calls/artifacts | repo diff/filesystem | negative proof | artifact/path scan | no manifests, aggregates, promotion artifacts, or `.gitignore` changes | any provider artifact/call evidence |
| Certification SHA/digests truthful | Git + report | provenance | clean-tree hash/ancestry/digest commands | exact full SHA and digest table match | dirty/stale/unreachable SHA |
| No path outside §4 | Git diff | scope | changed-path command | exact allowlist + bounded source files | any extra path |

Required command set, recorded with exact output and provenance:

```bash
uv run pytest -q tests/test_temporal_shadow_extraction_tl01g.py
uv run pytest -q \
  tests/test_temporal_shadow_prompt_calibration.py \
  tests/test_temporal_shadow_grounding_path.py
uv run ruff check tests/test_temporal_shadow_extraction_tl01g.py

python -m json.tool evals/graph_memory_layer/examples/temporal_shadow_holdout_v15/base-contribution.json >/dev/null
python -m json.tool evals/graph_memory_layer/examples/temporal_shadow_holdout_v15/gold-overlay.json >/dev/null
python -m json.tool evals/graph_memory_layer/examples/temporal_shadow_holdout_v15/temporal-case-tl01f.json >/dev/null
python -m json.tool evals/graph_memory_layer/examples/temporal_shadow_holdout_v15/temporal-case-tl01g.json >/dev/null
python -m json.tool evals/graph_memory_layer/examples/temporal_shadow_adversarial_v13/base-contribution.json >/dev/null
python -m json.tool evals/graph_memory_layer/examples/temporal_shadow_adversarial_v13/gold-overlay.json >/dev/null
python -m json.tool evals/graph_memory_layer/examples/temporal_shadow_adversarial_v13/temporal-case-tl01f.json >/dev/null
python -m json.tool evals/graph_memory_layer/examples/temporal_shadow_adversarial_v13/temporal-case-tl01g.json >/dev/null

git status --short
git diff --check
git diff --name-only <base>...HEAD
git diff --stat <base>...HEAD -- <§4 paths and bounded source paths>

test ! -e evals/graph_memory_layer/artifacts/temporal_shadow_prompt_calibration/tl01g/promotion-v15
! git diff --name-only <base>...HEAD | grep -E \
  'temporal_shadow_prompt_calibration.py|test_temporal_shadow_prompt_calibration.py|src/graph_memory|/artifacts/|^\.gitignore$'
```

Before writing the certification report:

```bash
git status --short                 # must be empty
git rev-parse HEAD                 # full certification SHA candidate
git rev-parse HEAD^{commit}
git merge-base --is-ancestor <base> HEAD
sha256sum <all V15/Adv13 base, gold, case, audit, source, and owning-test files>
```

The report must distinguish:

```text
CERTIFIED_FOR_EXECUTION
CERTIFICATION_FAILED
```

Only `CERTIFIED_FOR_EXECUTION` is mergeable. It means asset certification only,
not prompt readiness or permission to interpret model quality.

### Minimal live / dogfood proof

`Not applicable — provider execution is deliberately deferred. The realistic proof
is deterministic loading, evidence resolution, Gate-faithfulness, and exact digest
verification over the complete synthetic cohort pair.`

### Baseline failure protocol

For any required command already failing on the rebased base:

- run the same command on base and head;
- record exact base/head results;
- do not describe the gate as green;
- request an explicit operator waiver only if the command remains a required gate;
- do not alter unrelated code to absorb the failure.

## §8 Required review handback

The handback must include:

1. Exact PR URL, branch, base SHA, head SHA, and certification SHA.
2. §1 mission and merge-ready invariant copied exactly.
3. Nano-commit list and discrete story for each commit.
4. Actual changed paths and focused diff stat against §4.
5. V15 and Adv13 assertion-class inventory with IDs.
6. Exact control/candidate prompt identities and hashes.
7. Exact file digest table or a durable report section containing it.
8. Every §7 command and exact result, with provenance.
9. Produced defect lists from comprehensive grounding checks; both must be empty.
10. Source-time leakage negative/positive proof results.
11. Provider/artifact absence proof.
12. Baseline failures and explicit waivers; `none` when none.
13. Paths outside §4; `none` or stop report.
14. Stop conditions encountered and resolution; `none` when none.
15. Confirmation that no production, runner, prompt, corpus, Project Source, or DungeonMind path changed.
16. Named successor and all capabilities still false.
17. Confirmation that the authoritative handoff was implemented without compressed or omitted constraints.

## §9 Acceptance rubric

- [ ] Exactly one capability was delivered: provider-unobserved V15/Adv13 certification.
- [ ] One clean certification SHA contains final certified bytes and remains reachable.
- [ ] Frozen prompt, packet, renderer, and retired-cutoff identities remain exact.
- [ ] V15 and Adv13 are auto-discovered above cutoffs and explicitly non-skippable.
- [ ] F/G cases are exactly paired and target sets equal base/gold IDs.
- [ ] Every assertion and annotation resolves only cohort-owned evidence.
- [ ] Comprehensive grounding defect lists are empty for both cohorts.
- [ ] Session-valued temporal fields cannot pass on evidence metadata alone.
- [ ] Every non-null valid boundary has direction-specific proposition-bound proof.
- [ ] Every abstention row has null temporal lanes and a nonblank Gate rationale.
- [ ] Cumulative novelty and sibling-disjointness proofs pass.
- [ ] README/audit language identifies `sources/` as synthetic evaluation stimuli only.
- [ ] No provider call, manifest, aggregate, artifact path, or `.gitignore` change exists.
- [ ] Certification report says only `CERTIFIED_FOR_EXECUTION`; it makes no prompt-quality claim.
- [ ] No path outside §4 or bounded source exceptions changed.
- [ ] All required commands have exact produced results and provenance.
- [ ] The execution successor remains unimplemented.

## Stop conditions

Stop immediately and report rather than expanding scope when any of these becomes true:

1. Current main already contains V15, Adv V13, or another successor above the cutoffs.
2. A live provider call has occurred on either cohort.
3. A required fix touches prompt, packet, renderer, schema, production extraction, calibration runner, evaluator thresholds, or aggregate logic.
4. A valid cohort cannot be authored without reusing prior proposition/source templates above thresholds.
5. A session-valued case cannot be distinguished from source-time metadata under test-only certification rules.
6. The paired case loader requires a new public/durable schema.
7. Review requires canonical corpus prose or production graph input rather than synthetic stimuli.
8. Another branch/PR owns the same versions or capability.
9. A second capability—normalization, prompt revision, provider execution, graph adoption, UI, or cross-repo cutover—becomes necessary.
10. Any file outside §4 or the bounded source exceptions is required.

## Named successor

After this PR merges and post-merge doc sync records the certification, author a
new handoff for:

```text
TIMELINE: execute certified TL01G promotion matrix
```

That successor must:

- branch from then-current `main`;
- verify the exact certification SHA and every certified file digest before calls;
- verify and treat V15/Adv13 fixture, source, audit, gold, case, and owning-test bytes as read-only; treat README/report as read-only documentation pointers;
- run at most one exact six-lane × three-repetition matrix using frozen
  `tl01f-v1` / `tl01g-v1`, packet `tl01c-packet-v1`, renderer
  `render_temporal_shadow_user_content_v2`, and model `gpt-5.4-mini`;
- use no retry and count every attempted provider call;
- publish aggregate/report only after complete provenance checks;
- distinguish invalid/incomplete evidence, representation mismatch, textual-only
  normalization need, prompt-specific failure, and readiness without collapsing them;
- make no production cutover claim.
