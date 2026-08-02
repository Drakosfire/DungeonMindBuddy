---
pr_body_template: |
  ## Outcome

  Implement one paired TL01 grounding-path smoke that preserves assertion/evidence identity from source bytes through normal comparison, and either applies one proven local repair or reports the exact blocker without relaxing grounding.

  ## Base

  `<immutable origin/main SHA containing PR #486 and HANDOFF-pr488>`

  ## Invariant

  For one selected assertion, control and candidate traces remain bound to the same case, evidence, phrase, packet, renderer, model, and comparison path; a lane is evaluable only when production owned-evidence grounding succeeds and normal metrics are observed.

  ## Result

  - Control: `<lane result>`
  - Candidate: `<lane result>`
  - Overall: `<GROUNDING_PATH_READY | LOCAL_REPAIR_REQUIRED | PROVIDER_PHRASE_FIDELITY_BLOCKED | UNRESOLVED_DIAGNOSTIC_GAP>`
  - Provider calls: `<count>`

  ## Changed paths

  `<exact allowlisted paths>`

  ## Verification

  `<commands, exact results, provenance, base/head repair reproducer if applicable>`

  ## Still false

  No TL01H, V14/Adv V12, prompt mutation, retired-cohort mutation, fuzzy grounding, Kernel/graph write, projection, or UI change.
---

> **Status:** ACTIVE IMPLEMENTATION HANDOFF
> **Use for:** Dispatching exactly one coding agent to isolate and recover the shared TL01 source-phrase grounding path required before any new temporal prompt or promotion cohort.
> **Do not use for:** Authoring `tl01h-v1`, creating V14/Adv V12, modifying frozen prompts or retired cohorts, relaxing exact grounding, changing Temporal Kernel semantics, writing graph state, or building temporal UI.
> **Canonical repo path:** `Docs/Plans/HANDOFF-pr488-tl01-grounding-path-recovery.md`
> **Created:** 2026-08-01
> **Repository:** `Drakosfire/DungeonMindBuddy`
> **Design anchor:** `main@3d5e66b53b09112178dda99063fd9acade3fb087`
> **Parent authority candidate:** PR `#486`, head `63d1aceb7db2f06863da49d4ebc1f33362e0dcd9`, `Docs/Plans/JUMPSTART-tl01-grounding-path-recovery.md`
> **Required implementation base:** the immutable `origin/main` SHA containing merged PR `#486` and this handoff; record that SHA in the implementation PR body before any code change.
> **Suggested implementation branch:** `feat/tl01-grounding-path-recovery`
> **Suggested implementation PR title:** `test(tl01): isolate shared source-phrase grounding path`

# HANDOFF — TL01 Shared Source-Phrase Grounding-Path Recovery

## §0 Capability decomposition decision

| Candidate outcome | Independently useful? | Public/durable contract changed? | User/operator surface changed? | Failure model changed? | Independently testable or revertible? | Decision |
|---|---|---|---|---|---|---|
| One stage-bound trace for one exact assertion and owned evidence span | Yes | Diagnostic artifact only; no compatibility promise | CLI/report only | Yes — first failing stage becomes explicit | Yes | Include |
| Deterministic exact-phrase replay through both frozen prompt identities | Yes | No | No | Establishes local-path baseline | Yes | Include as proof of the same capability |
| Same-fixture live smoke through `tl01f-v1` and `tl01g-v1` | Yes | No | CLI/report only | Establishes evaluability gate | Yes | Include |
| Smallest repair at one locally proven shared owner | Conditionally | Possibly internal behavior | No | Restores the same grounding invariant | Yes | Include only after a base-failing reproducer identifies that owner |
| New prompt `tl01h-v1` | Yes | Prompt contract | No | Yes | Yes | Successor; forbidden |
| Fresh V14/Adv V12 promotion pair | Yes | Evaluation authority | No | Yes | Yes | Successor; blocked |
| Fuzzy, semantic, normalized, or synthesized quote acceptance | Yes | Grounding contract | No | Yes | Yes | Separate contract decision; forbidden |
| Temporal Kernel, graph write, projection, or Timeline UI | Yes | Product/runtime contracts | Yes | Yes | Yes | Separate workstream; forbidden |

### Selected capability

The temporal evaluation harness can determine the first stage at which one exact owned evidence phrase stops being preserved through the shared TL01 extraction path, and can restore that same exact-path invariant only when a failing reproducer proves a local shared owner is defective.

### Why the included outcomes share one invariant

The trace, deterministic replay, paired live smoke, and conditional local repair all establish or test the same property: one exact phrase and its assertion/evidence identity remain inspectable and fail-closed from fixture bytes through normal comparison. The repair is not authorization for semantic expansion; it is permitted only to make the already-declared invariant true at the proven owner.

### Named successors

- fresh V14 holdout and Adv V12 adversarial cohorts;
- any `tl01h-v1` prompt;
- broader temporal-shadow readiness;
- textual normalization or altered grounding policy;
- Temporal Kernel integration;
- graph publication or surface projection.

## §1 Mission and invariant

### Mission

A TL01 steward can run one bounded, reproducible paired smoke that shows exactly whether an evidence phrase survives packet construction, rendering, provider output, transport validation, evidence ownership, exact grounding, overlay assembly, and comparison for both frozen prompt lanes.

### Invariant

For one selected assertion, every observed stage is bound to the same case digest, base assertion ID, owned evidence ref, resolved source-span digest, expected phrase, prompt identity, packet/renderer identity, provider response, returned `source_phrase`, and comparison result. A lane is evaluable only when the production path proves the returned phrase inside owned evidence and emits ordinary comparison metrics. Missing or paraphrased phrases, foreign evidence, invalid transport, absent metrics, and unclassified stages remain explicit failures.

### Mission falsification test

This is not one slice if implementation must also change prompt meaning, introduce a new quote-matching policy, create a promotion cohort, modify graph/Kernel behavior, or build a new operator product surface.

The unlock gate is not “tests pass.” The unlock gate is paired live evidence: both frozen lanes produce transport-valid, owned-evidence-grounded output and observed normal comparison metrics on the same smoke fixture.

## §2 Context, authority, and boundaries

### Current verified truth at design time

| Item | Value |
|---|---|
| Current `main` | `3d5e66b53b09112178dda99063fd9acade3fb087` |
| PR `#486` head | `63d1aceb7db2f06863da49d4ebc1f33362e0dcd9` |
| TL01G merge | PR `#468`, merge `2c827f2bb3055eec3969a31a0262462650e1607f` |
| Frozen control | `tl01f-v1` |
| Frozen control SHA256 | `7a9d27c3a9980893f18757d7a5fe0612cf67f9aad8dfd2ccb20f9e3c667b7143` |
| Frozen candidate | `tl01g-v1` |
| Frozen candidate SHA256 | `3af1e470e304008d2490ba73e1a53628519c211bb54e17a10cd4c694beae9013` |
| Shared packet | `tl01c-packet-v1` |
| Shared renderer | `render_temporal_shadow_user_content_v2` |
| Live smoke model | `gpt-5.4-mini` |
| Last observed matrix | candidate `0/9`, control `1/9`; `17/18` failed before comparison |
| Current recommendation | `DIAGNOSE_GROUNDING_PATH` |
| Promotion authority | none |

These values must be rechecked after PR `#486` merges. Drift is not automatically acceptable.

### Authority precedence

1. `AGENTS.md` and external-agent PR-loop rules
2. checked-in temporal contracts
3. merged PR `#468` implementation, tests, fixtures, and durable evidence
4. `REPORT-tl01g-resolution-proof-abstention-gate.md`
5. merged PR `#486` jumpstart
6. this checked-in handoff
7. `Backlog.md` reminders
8. PR descriptions, Project Sources, attachments, and chat summaries

A conflict with a higher authority is a stop condition. This handoff may make a lower-level design choice only where the higher authority is silent.

### Required reading order

1. `AGENTS.md`
2. `.cursor/rules/external-agent-pr-loop.mdc`
3. `.cursor/skills/external-agent-pr-loop/SKILL.md`
4. `Docs/Design/CONTRACT-temporal-shadow-extraction-v1.md`
5. `Docs/Design/CONTRACT-temporal-prompt-calibration-v2.md`
6. `Docs/Design/CONTRACT-temporal-shadow-overlay-v1.md`
7. `Docs/Reports/REPORT-tl01g-resolution-proof-abstention-gate.md`
8. `Docs/Plans/JUMPSTART-tl01-grounding-path-recovery.md`
9. `src/graph_memory/temporal_shadow_extraction.py`
10. `src/graph_memory/temporal_shadow_extraction_schema.py`
11. `evals/graph_memory_layer/temporal_shadow_prompt_calibration.py`
12. `tests/test_temporal_shadow_extraction_tl01g.py`
13. `tests/test_temporal_shadow_prompt_calibration.py`
14. committed TL01G aggregate and representative grounding-failure records

### Implementation-base protocol

The implementation agent must:

1. fetch current `origin/main` after PR `#486` and this handoff are merged;
2. record the exact immutable SHA in the implementation PR body before code changes;
3. branch from that SHA;
4. verify the branch is not missing a temporal-path change from a newer merged PR;
5. stop if the declared prompt, packet, renderer, model, or owning paths materially differ.

Do **not** rewrite this handoff to contain its own future merge SHA.

### What remains false after this slice

Even on success:

- no prompt is promoted;
- no new promotion cohort exists;
- no broader temporal-shadow readiness is established;
- no textual normalization policy is accepted;
- no graph, Kernel, retrieval, projection, or UI behavior is added;
- no retired cohort regains authority.

## §3 Observable-path inventory

| Observable path | Current behavior | Required behavior after this slice | Same invariant? | Owning boundary |
|---|---|---|---|---|
| Deterministic control replay | Existing fake-client tests prove selected cases, but not one stage-bound paired smoke | Exact phrase reaches normal comparison under `tl01f-v1` | Yes | diagnostic runner + production extraction path |
| Deterministic candidate replay | Same limitation | Exact phrase reaches normal comparison under `tl01g-v1` | Yes | diagnostic runner + production extraction path |
| Live control smoke | Last matrix mostly fails before comparison | One call yields an explicit lane result and bounded trace | Yes | live diagnostic workflow |
| Live candidate smoke | Last matrix fails before comparison | One call yields an explicit lane result and bounded trace | Yes | live diagnostic workflow |
| Packet missing expected phrase | Not isolated by current aggregate | First failing stage is `PACKET_MISSING_PHRASE` | Yes | packet construction |
| Renderer missing expected phrase | Not isolated by current aggregate | First failing stage is `RENDERER_MISSING_PHRASE` using decoded JSON values | Yes | renderer |
| Provider call unavailable | Provider failure code exists but is not part of the proposed stage trace | Provider failure remains explicit; no metrics synthesized and no silent retry | Yes | provider client / diagnostic workflow |
| Provider omits or paraphrases phrase | Collapses later into generic `grounding_failure` | Trace records raw returned phrase and classifies `PROVIDER_PHRASE_FIDELITY_BLOCKED` only after local request-path proof | Yes | provider boundary + diagnostic classifier |
| Transport rejects output | Existing `invalid_model_output` | Trace records transport failure before grounding classification | Yes | transport schema |
| Returned evidence is foreign or absent | Existing fail-closed ownership check | Explicit `EVIDENCE_OWNERSHIP_MISMATCH`; no phrase fallback | Yes | production grounding conversion |
| Exact phrase is present in owned resolved text but validator rejects | Not currently localized | Base-failing reproducer identifies `GROUNDING_VALIDATOR_DEFECT` | Yes | production exact matcher |
| Grounding succeeds but overlay fails | Existing generic error | Explicit `OVERLAY_ASSEMBLY_FAILED` with identity preserved | Yes | overlay assembly |
| Overlay exists but comparison metrics do not | Current aggregate can represent missing values poorly | Metrics absence is explicit; null is never totaled as zero | Yes | comparison/calibration aggregation |
| Same deterministic input replayed | Expected deterministic behavior | Same case/prompt/fake output produces same trace identities and comparison | Yes | diagnostic runner |
| Changed fixture bytes or digest | Existing case validation | Fail closed before provider invocation | Yes | case loader |
| Missing live opt-in or credentials | Ad hoc | No provider call; clear CLI failure and zero output claiming live evidence | Yes | diagnostic CLI |
| Post-fix paired rerun | Not defined | At most one additional control and candidate call, same fixture/model/renderer | Yes | live diagnostic workflow |

No row authorizes a fallback. A failure at one stage does not permit bypassing that stage to reach comparison.

## §4 Files in scope — exact allowlist

| Action | Path | Purpose |
|---|---|---|
| Create | `evals/graph_memory_layer/temporal_shadow_grounding_path.py` | Paired diagnostic runner, recording client wrapper, stage classifier, bounded trace writer, and explicit live CLI |
| Create | `tests/test_temporal_shadow_grounding_path.py` | Owning-boundary deterministic, classification, replay, call-budget, and no-live-default proof |
| Create | `evals/graph_memory_layer/examples/temporal_shadow_grounding_smoke_v1/README.md` | Mark fixture diagnostic-only and never promotion authority |
| Create | `evals/graph_memory_layer/examples/temporal_shadow_grounding_smoke_v1/source.md` | Tiny synthetic source containing one unique ASCII phrase |
| Create | `evals/graph_memory_layer/examples/temporal_shadow_grounding_smoke_v1/base-contribution.json` | One candidate-only assertion bound to one evidence ref |
| Create | `evals/graph_memory_layer/examples/temporal_shadow_grounding_smoke_v1/gold-overlay.json` | Gate-simple exact expected overlay |
| Create | `evals/graph_memory_layer/examples/temporal_shadow_grounding_smoke_v1/temporal-case-tl01f.json` | Frozen-control case |
| Create | `evals/graph_memory_layer/examples/temporal_shadow_grounding_smoke_v1/temporal-case-tl01g.json` | Frozen-candidate case, byte-equivalent except prompt identity and required digest consequences |
| Create | `evals/graph_memory_layer/examples/temporal_shadow_grounding_smoke_v1/fake-model-output.json` | One exact owned-evidence transport batch reused by both deterministic lanes |
| Create | `Docs/Reports/REPORT-tl01g-grounding-path-recovery.md` | Durable bounded evidence, conclusion, and successor gate |
| Modify only if a failing reproducer proves ownership | `src/graph_memory/temporal_shadow_extraction.py` | Smallest local shared-path repair or minimal observation seam that does not alter public semantics |
| Modify only if a failing reproducer proves ownership | `evals/graph_memory_layer/temporal_shadow_prompt_calibration.py` | Correct missing-vs-zero metrics or paired aggregation defect; not required merely to host the new smoke |
| Modify only when paired with the proven owner above | `tests/test_temporal_shadow_extraction_tl01g.py` | Regression for an extraction-owner repair or frozen-identity guard |
| Modify only when paired with the proven owner above | `tests/test_temporal_shadow_prompt_calibration.py` | Regression for a calibration-owner repair |

### Bounded discovery exception

- **Directory:** `tests/` or `evals/graph_memory_layer/`
- **Maximum additional paths:** 1
- **Allowed path kinds:** one existing shared CLI/helper test or one existing temporal CLI module
- **Decision rule:** the diagnostic cannot be invoked or proved through the new runner and current public evaluation functions without changing that existing seam
- **Required report:** exact path, why the new module cannot own it, and why this does not add a second capability

There is no production discovery exception outside the four conditional modifications above. A need to change another production path is a stop condition.

Generated files under `out/` are not committed and do not expand the allowlist.

## §5 Files and capabilities explicitly out of scope

| Path or capability | Why excluded |
|---|---|
| Prompt text, prompt registry identity, or prompt hashes for `tl01f-v1` / `tl01g-v1` | Frozen experimental identity |
| `evals/.../temporal_shadow_holdout_v8` through `v13` | Retired observed evidence; never mutate |
| `evals/.../temporal_shadow_adversarial_v6` through `v11` | Retired observed evidence; never mutate |
| Any V14 or Adv V12 directory | Successor promotion authority |
| `src/graph_memory/kernel/**` | Temporal evaluation may not change graph semantics |
| `src/graph_memory/temporal_shadow.py` or TL00 temporal models | Overlay/Kernel contract change is a separate capability |
| Packet schema version or renderer identity | Frozen unless PR `#486` authority is explicitly amended; local renderer bug may be repaired without version change only when behavior already contradicts the declared renderer contract |
| Fuzzy/semantic/case-folded/punctuation-normalized quote matching | New grounding policy, not diagnostics |
| Provider-specific bypass or synthesized quote | Violates owned-evidence grounding |
| Graph writes, promotion, projection, Plan/Play/Build UI | Separate architecture and product work |
| Repository-wide cleanup or refactor | Not needed to establish the invariant |
| Full prompt, full source document, or unrestricted provider response logging | Violates bounded evidence discipline |

## §6 Implementation contract

### §6.1 Inputs

The diagnostic runner consumes:

```text
control case path       temporal-case-tl01f.json
candidate case path     temporal-case-tl01g.json
fake model output       fake-model-output.json for deterministic mode
delegate client         FakeTemporalShadowExtractionClient or OpenAITemporalShadowExtractionClient
model_id                exactly gpt-5.4-mini for live smoke
output_dir              under out/evals/temporal_shadow_grounding_path/
mode                    deterministic | live
phase                   initial | post_fix
```

The two case files must be equivalent in all semantic inputs except frozen prompt identity. The runner must fail before a provider call if base contribution, gold, selected assertions, evidence registry, snippet limit, packet version, or renderer differ.

### §6.2 Smoke fixture

The fixture must contain exactly:

- one candidate-only contribution;
- one selected assertion;
- one owned evidence ref;
- one resolved source span;
- one short ASCII-only phrase appearing exactly once in the owned span;
- one Gate-simple temporal answer whose lane/value are not under dispute;
- exact case/base/gold/source digests;
- no prose, assertion skeleton, or proposition copied from retired promotion cohorts.

Use an unmistakable phrase similar in shape to:

```text
the brass moth struck the north bell exactly twice
```

The final fixture phrase may differ, but it must remain ASCII-only, contiguous, unique in the owned span, and semantically attached to the selected assertion.

`README.md` must contain:

```text
DIAGNOSTIC ONLY — NEVER PROMOTION AUTHORITY
```

The fixture must not be discoverable by holdout/adversarial promotion auto-discovery.

### §6.3 Runner architecture

The runner must exercise the existing production evaluation path rather than implement a second extractor.

Use a recording wrapper around the selected `TemporalShadowExtractionClient`:

```text
production run_temporal_shadow_extraction
  → recording client receives real instructions + rendered user_content
  → delegate client performs fake or live provider call
  → recording client captures bounded raw batch + ProviderMeta
  → production transport/ownership/grounding/overlay/comparison continues unchanged
```

The wrapper may observe the request/response boundary. It must not modify instructions, rendered content, raw output, evidence refs, or source phrase.

The diagnostic classifier may inspect:

- parsed rendered JSON;
- the recorded raw batch;
- the real transport model;
- the real production error/result;
- fixture-bound expected phrase and evidence identity.

It must not independently decide that an otherwise rejected annotation is acceptable. The production path remains authoritative.

### §6.4 Decoded-render rule

Renderer preservation is tested on decoded JSON string values, not raw JSON bytes.

`render_temporal_shadow_user_content_v2` uses JSON escaping. Therefore:

- parse the rendered JSON;
- find the exact packet/evidence snippet value;
- compare the Unicode string value to the fixture source phrase;
- do not classify ordinary JSON escaping as renderer corruption.

Transport preservation is exact Python/Unicode string equality after JSON parsing, not wire-byte equality.

### §6.5 Phrase-grounding rule

This slice preserves current production behavior:

```text
normalized phrase = " ".join(source_phrase.split())
normalized snippet = " ".join(preview_snippet.split())
match = normalized phrase is a contiguous substring of normalized cited owned snippet
```

No additional normalization is authorized. In particular: no case folding, punctuation stripping, Unicode compatibility normalization, fuzzy matching, semantic matching, or label-to-quote substitution.

### §6.6 Bounded trace

Each lane trace must record only:

- `repository_sha`
- `run_mode` and `phase`
- `lane`: `control` | `candidate`
- `case_id` and `case_digest`
- `prompt_version` and `prompt_sha256`
- `packet_version` and renderer identity
- `model_id`
- `provider_response_id` when available
- `assertion_id`
- owned `evidence_ref_ids`
- resolved span digest
- bounded expected phrase
- packet phrase present: `true`|`false`
- rendered decoded phrase present: `true`|`false`
- transport accepted: `true`|`false`
- returned `evidence_ref_ids`
- bounded returned `source_phrase`
- owned-evidence check result
- phrase match result, `evidence_ref_id`, and normalized offset when present
- production error code and bounded diagnostics when failed
- `overlay_id` when produced
- comparison metrics present: `true`|`false`
- bounded comparison metrics when produced
- lane result

Do not persist:

- full system instructions;
- full rendered prompt;
- unrestricted source text;
- full provider response envelopes;
- secrets, API keys, environment values, or absolute local paths.

The JSON trace under `out/` is diagnostic output with no compatibility promise and no product consumer. The checked-in report is the durable evidence surface.

### §6.7 Lane result taxonomy

Each deterministic or live lane ends in exactly one result:

| Result | Meaning |
|---|---|
| `EVALUABLE` | Production path produced grounded overlay and normal comparison metrics |
| `PACKET_MISSING_PHRASE` | Resolved owned phrase is absent from the packet |
| `RENDERER_MISSING_PHRASE` | Packet contains phrase but decoded rendered packet does not |
| `PROVIDER_EXECUTION_FAILED` | Provider did not return a usable raw batch |
| `PROVIDER_PHRASE_FIDELITY_BLOCKED` | Local request path is proven exact, transport is inspectable, and provider returned no phrase, a paraphrase, or a noncontiguous fragment |
| `TRANSPORT_REJECTED` | Raw provider batch cannot validate as current transport |
| `EVIDENCE_OWNERSHIP_MISMATCH` | Returned refs are absent, unknown, or not owned by the assertion |
| `GROUNDING_VALIDATOR_DEFECT` | Exact returned phrase is demonstrably present in the same cited owned resolved span, but production matcher rejects it |
| `OVERLAY_ASSEMBLY_FAILED` | Transport and grounding pass but overlay construction fails |
| `COMPARISON_METRICS_UNOBSERVED` | Overlay exists but ordinary comparison does not produce metrics |
| `UNRESOLVED_DIAGNOSTIC_GAP` | Available trace cannot identify the first failing stage |

Result assignment must be deterministic and first-failure ordered. Later-stage checks cannot overwrite an earlier failure.

### §6.8 Overall report conclusion

The checked-in report selects exactly one conclusion:

| Conclusion | Required evidence |
|---|---|
| `GROUNDING_PATH_READY` | Both deterministic lanes and both live lanes are `EVALUABLE` on the same fixture/model/renderer, with real comparison metrics |
| `LOCAL_REPAIR_REQUIRED` | A base-failing deterministic or live reproducer identifies one local owner; report names the owner and either includes the bounded repair or stops before repair if it exceeds scope |
| `PROVIDER_PHRASE_FIDELITY_BLOCKED` | Both deterministic lanes are `EVALUABLE`; rendered request is exact; at least one live lane returns missing/paraphrased phrase; no local semantic relaxation is made |
| `UNRESOLVED_DIAGNOSTIC_GAP` | Provider execution is unavailable, traces are incomplete, stages disagree, or the first failing owner cannot be proven |

If control and candidate differ, report separate lane results. Do not convert a candidate-only provider phrase failure into an isolated prompt verdict within this PR. It is lane-conditioned evidence for a later prompt decision, not promotion authority.

### §6.9 Conditional repair authorization

A production/evaluation modification is authorized only after a test or deterministic reproducer fails on the immutable implementation base and proves one of:

- packet construction omits exact evidence already available at its owner;
- renderer drops or changes a decoded packet string;
- transport parsing changes a valid returned string;
- evidence ownership resolves a different ref/span than the traced identity;
- current exact whitespace-normalized matcher rejects a phrase present in the cited owned snippet;
- overlay assembly fails after successful production grounding;
- calibration totals absent metrics as observed zeros.

The repair must:

- modify only the proven owner;
- preserve prompt text, packet version, renderer identity, and grounding policy unless the proven owner is the renderer implementation contradicting its existing contract;
- add a regression that fails on base and passes on head;
- rerun deterministic paired replay;
- rerun at most one post-fix paired live smoke.

If the required change is semantic normalization, prompt revision, schema versioning, or more than one production owner, stop and propose a successor.

### §6.10 Provider-call budget

```text
initial live smoke:   1 control + 1 candidate
post-fix verification: at most 1 control + 1 candidate
maximum total:         4 provider calls
```

The runner performs no automatic provider retries. More calls require an explicit stop report and operator decision before execution.

Tests must prove one paired invocation calls each lane exactly once and deterministic mode makes zero live provider calls.

### §6.11 Output

Successful completion produces:

- deterministic paired test evidence;
- one local initial trace pair;
- optional one local post-fix trace pair;
- `Docs/Reports/REPORT-tl01g-grounding-path-recovery.md`;
- an optional bounded local repair and regression when authorized.

No graph, corpus, prompt, cohort, or runtime data is committed by the smoke.

### §6.12 Trust boundary

**Verifies:**

- fixture digests and paired equivalence
- exact prompt identities
- packet and decoded renderer preservation
- raw transport shape
- evidence ownership
- production exact phrase grounding
- overlay/comparison completion

**Records without treating as truth:**

- provider-returned annotation semantics
- provider diagnostic wording
- extraction confidence

**Rejects:**

- foreign evidence
- missing/blank/paraphrased phrases where exact phrase is required
- invalid transport
- absent metrics presented as zero
- stale or mismatched fixture identity
- prompt/cohort mutation

## §6A State and fallback matrix

| Path | Loading / initialization | Exact success | Ordinary miss | Dependency unavailable | Integrity / contract failure | Stale / superseded | Retry / replay |
|---|---|---|---|---|---|---|---|
| Deterministic control | Validate paired fixture and frozen hashes | `EVALUABLE` with metrics | Not applicable | Fake output missing → fail | Fail closed before comparison | Prompt/hash drift → stop | Exact replay required deterministic |
| Deterministic candidate | Same | `EVALUABLE` with metrics | Not applicable | Fake output missing → fail | Fail closed | Prompt/hash drift → stop | Exact replay required deterministic |
| Live control | Validate all local stages before call | Explicit lane result | Provider returns no phrase → provider fidelity result | Provider call fails → `PROVIDER_EXECUTION_FAILED`; no fallback | Fail closed | Base/fixture drift → stop | No automatic retry; one post-fix call only |
| Live candidate | Same | Explicit lane result | Same | Same | Same | Same | Same |
| Phrase grounding | Requires cited owned evidence | Exact current matcher succeeds | Phrase absent → explicit failure | Evidence unresolved → fail | Foreign evidence / false-negative classified | No fallback to other refs | Deterministic replay only |
| Comparison | Requires grounded overlay | Metrics present | Not applicable | Not applicable | Missing metrics remain unobserved | No prior aggregate substitution | Recompute from same successful run only |

No path may fall back to another fixture, retired cohort, foreign evidence, label text, source filename, or latest run.

## §6B Identity matrix

| Situation | Required matching rule | Ambiguity behavior | Fallback permitted? | Persistence consequence |
|---|---|---|---|---|
| Case | Exact case digest and case ID | Stop | No | Trace binds exact digest |
| Prompt | Exact version plus frozen SHA256 | Stop | No | Trace records both |
| Assertion | Exact `base_assertion_id` | Stop | No | No rebinding |
| Evidence | Exact owned `evidence_ref_id` and resolved span digest | Foreign/missing explicit | No | Trace records ordered refs and digest |
| Expected phrase | Exact fixture phrase; current whitespace normalization only | Multiple occurrences violate fixture contract | No | Trace stores bounded phrase |
| Returned phrase | Exact post-JSON string; current whitespace-normalized substring match | Missing/paraphrased explicit | No | Trace stores bounded returned value |
| Lane | Exact control / candidate bound to prompt version | Mismatch stops before provider | No | Separate trace per lane |
| Provider response | Exact response ID when supplied | Missing ID is recorded, not invented | No | Report labels provider-observed evidence |
| Rename / alias / normalized key | Prohibited | Stop | No | None |
| Rebinding after fixture change | Prohibited; changed bytes create a new case digest | Stop | No | Prior trace remains bound to old digest |

First-win matching is prohibited.

## §6C Persistence and replay matrix

| Operation | Durable representation | Round-trip guarantee | Duplicate / replay behavior | Compatibility / migration | Rollback / reversion |
|---|---|---|---|---|---|
| Fixture load | Checked-in JSON/Markdown with digests | Exact bytes and IDs validate | Same bytes produce same deterministic identities | No migration; v1 diagnostic fixture only | Revert fixture commit |
| Deterministic trace | Generated local JSON under `out/` | Same input/fake output produces equivalent bounded trace | Re-running overwrites only with explicit CLI flag or new output dir | No compatibility promise; no product consumer | Delete local output |
| Live trace | Generated local JSON under `out/` | Records exact response identity and lane result | New provider call is a new observation; never deduplicate as same result | No compatibility promise | Delete local output; report remains evidence |
| Checked-in report | Markdown | Must faithfully summarize local trace fields and provenance | Amend only through ordinary review; never rewrite retired evidence | No machine-loader contract | Revert report commit |
| Local repair | Source/test diff | Existing public behavior preserved except proven defect | Regression prevents reintroduction | No migration unless stop condition raised | Revert repair commit |

The diagnostic trace format is not a durable runtime contract. Adding a loader, API, registry, or UI consumer is a split trigger.

## §6D Predecessor-to-diagnostic mapping

### Grounding sources

- `TemporalShadowExtractionCaseV1`
- `GraphContribution` + owned evidence refs
- `build_assertion_evidence_packets`
- `TemporalPromptSpec` / `compute_prompt_sha256`
- `render_temporal_shadow_user_content_v2`
- `TemporalShadowExtractionClient.extract_annotations`
- `TemporalModelAnnotationBatchTransportV1`
- production `ground_and_convert_model_batch`
- `assemble_temporal_overlay`
- `compare_temporal_overlays` / run result
- `TemporalShadowExtractionError`
- `ProviderMeta`

| Predecessor field / outcome | Real shape / optionality | Diagnostic field / behavior | Transformation | Proof |
|---|---|---|---|---|
| `case.case_id` | required string | `case_id` | identity | fixture/runner test |
| case file bytes | checked by SHA-bound refs | `case_digest` | SHA256 | replay test |
| `prompt_version` | supported exact string | lane prompt identity | `compute_prompt_sha256` | frozen-hash test |
| packet `evidence_snippets[]` | evidence ID + preview snippet + line bounds | packet phrase and ownership observations | decoded inspection only | packet test |
| rendered `user_content` | JSON string | decoded renderer observation | `json.loads`, no semantic alteration | escaping test |
| provider raw batch | dict or provider failure | transport observation | record bounded selected fields | fake/live runner test |
| `ProviderMeta.response_id` | string; may be empty in fake client | provider response identity | record as supplied | trace test |
| transport annotation | strict Pydantic model | returned phrase/refs | exact values | transport classification test |
| `TemporalShadowExtractionError.code` | stable string | lane result input | first-failure mapping | classification matrix test |
| comparison metrics | typed metrics on successful run | `comparison_metrics_present` and bounded metrics | model dump | evaluable test |
| absent comparison | no metrics | explicit false / unobserved | never numeric zero | missing-metrics test |

Invented “close enough” predecessor values are not acceptable. The fixture may be synthetic; the code paths and types must be real.

## §7 Verification ownership map and commands

### §7.1 Guarantees

| Guarantee | Owning boundary | Command or scenario | Expected evidence |
|---|---|---|---|
| Fixture is one assertion / one owned ref / one unique ASCII phrase | fixture loader + test | focused pytest | Exact inventory and uniqueness assertions |
| Control/candidate inputs differ only by frozen prompt identity | paired runner | focused pytest | Failure before delegate call on any other difference |
| Frozen prompt hashes unchanged | extraction tests | existing TL01G pytest | Exact known hashes |
| Packet contains exact phrase and evidence ref | packet builder through runner | focused pytest | Trace says packet present |
| Renderer preserves decoded string | renderer boundary | focused escaping test | Decoded phrase exactly equal |
| Fake control reaches comparison | production extraction workflow | focused pytest | `EVALUABLE`, metrics present |
| Fake candidate reaches comparison | production extraction workflow | focused pytest | `EVALUABLE`, metrics present |
| Diagnostic runner does not duplicate acceptance semantics | workflow boundary | injected phrase/ownership/transport failures | Lane result agrees with production error/result |
| Foreign evidence never falls back | production grounding | focused pytest | `EVIDENCE_OWNERSHIP_MISMATCH` |
| False-negative matcher classification requires demonstrable presence | classifier + production matcher | focused pytest | Only exact cited-owned presence can yield validator defect |
| Missing metrics are not zero | comparison/calibration boundary | focused pytest | explicit `comparison_metrics_present=false`; no numeric unsafe claim |
| Deterministic mode performs zero live calls | recording wrapper | focused pytest | live delegate spy untouched |
| Paired live workflow calls each lane once | diagnostic workflow | fake live-delegate spy test | exactly two delegate calls |
| Live fixture/model/renderer are identical across lanes | diagnostic workflow | trace comparison | only prompt identity differs |
| Provider-call budget is honored | workflow + handback | live scenario and call ledger | 2 initial, ≤2 post-fix |
| No full prompts/source docs are written | trace writer | focused artifact-content test | forbidden fields/strings absent |
| Diagnostic fixture is not promotion-discovered | existing/new discovery test | focused pytest | fixture omitted from fresh cohort discovery |
| Conditional repair is base-failing/head-green | owning production boundary | exact regression command | base/head evidence |
| Retired cohort and prompt bytes unchanged | repository boundary | git diff guards | no changed paths/bytes |

### §7.2 Required automated commands

Run before any live call:

```bash
uv run pytest -q tests/test_temporal_shadow_grounding_path.py
uv run pytest -q tests/test_temporal_shadow_extraction_tl01g.py
uv run pytest -q tests/test_temporal_shadow_prompt_calibration.py
```

Run lint on all changed Python paths:

```bash
uv run ruff check \
  evals/graph_memory_layer/temporal_shadow_grounding_path.py \
  tests/test_temporal_shadow_grounding_path.py \
  src/graph_memory/temporal_shadow_extraction.py \
  evals/graph_memory_layer/temporal_shadow_prompt_calibration.py \
  tests/test_temporal_shadow_extraction_tl01g.py \
  tests/test_temporal_shadow_prompt_calibration.py
```

Omit conditional paths that are unchanged only when the exact command/result ledger says so.

Repository scope checks:

```bash
git diff --check
git diff --name-only <implementation-base>...HEAD
git diff --stat <implementation-base>...HEAD -- <§4 paths>
```

### §7.3 Deterministic CLI proof

The implementation must expose an invocation equivalent to:

```bash
uv run python evals/graph_memory_layer/temporal_shadow_grounding_path.py \
  --control-case evals/graph_memory_layer/examples/temporal_shadow_grounding_smoke_v1/temporal-case-tl01f.json \
  --candidate-case evals/graph_memory_layer/examples/temporal_shadow_grounding_smoke_v1/temporal-case-tl01g.json \
  --fake-output evals/graph_memory_layer/examples/temporal_shadow_grounding_smoke_v1/fake-model-output.json \
  --model-id gpt-5.4-mini \
  --mode deterministic \
  --phase initial \
  --output-dir out/evals/temporal_shadow_grounding_path/deterministic
```

Expected:

```text
control:   EVALUABLE
candidate: EVALUABLE
provider calls: 0
comparison metrics present: true for both
```

### §7.4 Minimal live proof

Live execution must require both an explicit CLI mode and an environment opt-in, so default tests or casual invocation cannot spend provider calls.

Example contract:

```bash
DMB_RUN_LIVE_TL01_GROUNDING_SMOKE=1 \
uv run python evals/graph_memory_layer/temporal_shadow_grounding_path.py \
  --control-case evals/graph_memory_layer/examples/temporal_shadow_grounding_smoke_v1/temporal-case-tl01f.json \
  --candidate-case evals/graph_memory_layer/examples/temporal_shadow_grounding_smoke_v1/temporal-case-tl01g.json \
  --model-id gpt-5.4-mini \
  --mode live \
  --phase initial \
  --output-dir out/evals/temporal_shadow_grounding_path/live-initial
```

The exact opt-in name may differ if repository convention requires it; behavior may not.

Record:

- exact repository SHA;
- exact two provider response IDs when available;
- exact call count;
- separate control and candidate lane results;
- whether comparison metrics are observed;
- evidence provenance as author-local/provider-observed.

If a local repair is applied, run one equivalent `--phase post_fix` pair in a new output directory. Do not rerun promotion cohorts.

### §7.5 Frozen-byte guards

Prove after implementation:

- control prompt SHA256 unchanged
- candidate prompt SHA256 unchanged
- packet version unchanged
- renderer identity unchanged
- retired cohort directories unchanged
- no V14 or Adv V12 directory exists
- no Kernel/graph/UI path changed

Use hash/inventory commands or existing tests and record exact output in the PR handback.

### §7.6 Baseline-failure protocol

For any required command red on the immutable base:

| Command | Base result | Head result | New failure? | Acceptance effect | Waiver |
|---|---|---|---|---|---|
| `<command>` | `<exact>` | `<exact>` | Yes / No | blocked or explicit waiver | `<none or operator waiver>` |

Do not call the gate green when a baseline failure remains. Live provider observations are never CI evidence.

## §8 Required implementation handback

The implementation PR body must include:

1. Immutable implementation base and head SHA.
2. Exact actual changed paths.
3. Focused diff stat limited to §4.
4. Frozen prompt hashes before and after.
5. Packet version and renderer identity before and after.
6. Deterministic control and candidate trace summaries.
7. Initial live control and candidate trace summaries.
8. Optional post-fix paired trace summaries.
9. Provider response IDs and exact call count.
10. Per-lane result taxonomy and overall report conclusion.
11. First failing stage for each non-evaluable lane.
12. Exact base-failing/head-green reproducer for every conditional repair.
13. Every §7 command and exact result.
14. Evidence provenance: author-local, provider-observed, independently rerun, or CI.
15. Baseline failures and explicit waivers; write none where appropriate.
16. Paths outside §4; write none or include a stop report.
17. Stop conditions encountered; write none where appropriate.
18. Confirmation that deterministic mode made zero provider calls.
19. Confirmation that no automatic provider retry occurred.
20. Confirmation that null/unobserved metrics were never presented as zero.
21. Confirmation that prompts, retired cohorts, Kernel, graph writes, projection, UI, TL01H, V14, and Adv V12 remain unchanged/unimplemented.
22. Confirmation that the authoritative handoff was implemented without compression or omitted constraints.

A report concluding `PROVIDER_PHRASE_FIDELITY_BLOCKED` or `UNRESOLVED_DIAGNOSTIC_GAP` is a valid completed PR when the diagnostic invariant and required evidence are satisfied.

## §9 Acceptance rubric

Accept only when every applicable statement is true.

1. Exactly one capability was delivered: paired shared-grounding diagnosis/recovery.
2. One diagnostic fixture contains one candidate assertion, one owned evidence ref, and one unique ASCII phrase.
3. The fixture is explicitly diagnostic-only and excluded from promotion discovery.
4. Control and candidate cases differ only by frozen prompt identity.
5. Both deterministic lanes reach ordinary comparison through the production path.
6. The recording wrapper observes but does not mutate request or response values.
7. Renderer preservation is judged on decoded JSON strings.
8. Production grounding remains the authority; the diagnostic classifier cannot accept rejected semantics.
9. Every lane has exactly one first-failure result.
10. Provider phrase fidelity is not blamed until packet, renderer, and transport observations support it.
11. A validator defect is not claimed unless the exact returned phrase is proven in the same cited owned resolved span.
12. Foreign or missing evidence never falls back.
13. Missing comparison metrics remain unobserved, never numeric zero.
14. Initial live proof uses exactly one control and one candidate call.
15. Post-fix live proof, when present, uses at most one additional control and candidate call.
16. No automatic provider retries occur.
17. No full prompt, unrestricted source body, or unrestricted provider envelope is persisted.
18. Every conditional production change has a base-failing/head-green owning-boundary regression.
19. No fuzzy, semantic, case-folded, punctuation-stripped, or synthesized quote acceptance was added.
20. Frozen prompt text and hashes are unchanged.
21. Retired cohort bytes are unchanged; no V14/Adv V12 exists.
22. No Kernel, graph write, projection, or UI path changed.
23. The checked-in report selects exactly one allowed overall conclusion and shows separate lane results.
24. The report does not claim prompt promotion or broader readiness.
25. `git diff --name-only` contains only §4 paths or an approved bounded exception.
26. Required command provenance and baseline comparisons are truthful.
27. Named successors remain false and unclaimed.

## §10 Reviewer protocol

1. Review the invariant before individual files.
2. Verify implementation base contains merged PR `#486` and this handoff.
3. Recheck prompt hashes, packet version, renderer identity, and model ID.
4. Compare actual paths to §4 and §5.
5. Inspect fixture novelty and confirm it is not promotion authority.
6. Confirm paired cases differ only by prompt identity.
7. Confirm the diagnostic calls the real production extraction path.
8. Confirm the wrapper does not edit instructions, JSON, raw output, refs, or phrase.
9. Trace one deterministic lane from source bytes through comparison.
10. Trace each live lane from decoded rendered packet through provider output and production result.
11. Confirm result classification is first-failure ordered and mutually exclusive.
12. Confirm renderer checks are decoded-string checks, not raw-escape checks.
13. Confirm exact current whitespace normalization is unchanged.
14. Confirm missing metrics cannot be aggregated as zero.
15. Confirm provider-call count and response IDs match evidence.
16. If code was repaired, rerun the base-failing reproducer at the owning boundary.
17. Confirm no prompt, cohort, Kernel, graph, projection, or UI scope entered through a “diagnostic” helper.
18. Confirm report conclusion follows §6.8 exactly.
19. Confirm successors remain blocked unless the merged report is `GROUNDING_PATH_READY`.

Request changes if the PR:

- edits a frozen prompt;
- creates or mutates a promotion cohort;
- adds quote normalization or fuzzy matching;
- treats null metrics as zero;
- uses a fake-provider success as live evaluability;
- changes more than one unproven production owner;
- hides different control/candidate lane outcomes;
- logs full prompts or source documents;
- exceeds provider budget without prior operator decision.

## §11 Re-review protocol

Begin every re-review with a finding ledger.

| Prior finding | Claimed fix | Owning file/test | Verified? | New consequence? |
|---|---|---|---|---|
| `<finding>` | `<fix>` | `<path/test>` | Yes / No | `<none or consequence>` |

For every prior finding:

1. verify the literal fix;
2. rerun the whole paired invariant;
3. recheck sibling control/candidate behavior;
4. inspect whether the fix changed grounding, identity, trace privacy, or call budget;
5. re-run frozen-byte and path guards;
6. add new findings rather than reviewing only the changed line.

### Stop conditions

Stop and report rather than broadening scope when:

- current `main` materially changes temporal extraction/calibration after the handoff anchor;
- PR `#486` does not merge or its merged content materially differs;
- frozen prompt hashes, packet version, renderer identity, or model profile differ;
- the committed TL01G evidence cannot support the claimed representative failure; do not fabricate missing raw provider payloads;
- the smoke cannot use the same semantic fixture for both lanes;
- deterministic local replay fails in more than one independent owner;
- exact local replay passes but live provider output persistently paraphrases or omits the phrase;
- the proposed repair requires fuzzy, semantic, case-folded, punctuation-normalized, Unicode-normalized, or synthesized matching;
- a packet/schema version change is required;
- a new durable trace schema, API, registry, database, or UI is required;
- a production path outside §4 must change;
- provider calls would exceed four;
- the first failing stage cannot be determined from bounded evidence;
- a second independently useful behavior is required;
- a required baseline failure needs an operator waiver.

Use this report shape:

```text
Stop condition:
First failing stage:
Evidence available:
Evidence missing:
Why the current mission cannot absorb it:
New public/durable contract discovered:
Affected observable paths:
Required path outside scope:
Proposed successor slice:
Tracker/authority update needed:
Operator decision required:
Provider calls already spent:
```

A stop report is a valid outcome. It must not be rewritten as `GROUNDING_PATH_READY`.

### Successor gate

After this implementation PR merges, re-anchor from its immutable merge SHA.

Only when the merged report concludes:

```text
GROUNDING_PATH_READY
```

may a later steward author a separate handoff for:

```text
fresh V14 holdout
+ fresh Adv V12 adversarial cohort
+ cumulative span and proposition-template novelty
+ Gate E3 boundary and proposition-value audits
+ paired tl01f-v1 versus tl01g-v1 calibration
```

Even `GROUNDING_PATH_READY` does not authorize `tl01h-v1`. A new prompt requires evaluable comparison evidence that isolates a candidate-specific defect after the shared grounding path is healthy.

## Suggested implementation PR body skeleton

```markdown
## Outcome

Implement one paired TL01 grounding-path smoke that preserves assertion/evidence identity from source bytes through normal comparison, and either applies one proven local repair or reports the exact blocker without relaxing grounding.

## Base

`<immutable origin/main SHA containing PR #486 and HANDOFF-pr488>`

## Invariant

For one selected assertion, control and candidate traces remain bound to the same case, evidence, phrase, packet, renderer, model, and comparison path; a lane is evaluable only when production owned-evidence grounding succeeds and normal metrics are observed.

## Result

- Control: `<lane result>`
- Candidate: `<lane result>`
- Overall: `<GROUNDING_PATH_READY | LOCAL_REPAIR_REQUIRED | PROVIDER_PHRASE_FIDELITY_BLOCKED | UNRESOLVED_DIAGNOSTIC_GAP>`
- Provider calls: `<count>`

## Changed paths

`<exact allowlisted paths>`

## Verification

`<commands, exact results, provenance, base/head repair reproducer if applicable>`

## Still false

No TL01H, V14/Adv V12, prompt mutation, retired-cohort mutation, fuzzy grounding, Kernel/graph write, projection, or UI change.
```

## Final dispatch check

- [ ] PR `#486` and this handoff are merged before implementation begins.
- [ ] Immutable implementation base is recorded in the implementation PR body.
- [ ] Capability decomposition still yields one invariant.
- [ ] All observable paths are represented.
- [ ] Expected diff fits §4.
- [ ] Every matrix is complete.
- [ ] The fixture is diagnostic-only and promotion-invisible.
- [ ] Live execution is explicit opt-in and budgeted.
- [ ] Every acceptance claim maps to §7 proof at its owning boundary.
- [ ] No essential constraint exists only in chat.
