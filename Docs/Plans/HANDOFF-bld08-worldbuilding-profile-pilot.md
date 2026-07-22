# HANDOFF — BLD-08 bounded worldbuilding extraction profile and pilot

- **Created:** 2026-07-22
- **Status:** PREPARED / DRAFT — may be stacked against the BLD-07 head; ACTIVE / MERGEABLE only after BLD-07 merge, rebase, and immutable merge-SHA re-anchor.
- **Canonical handoff path:** `Docs/Plans/HANDOFF-bld08-worldbuilding-profile-pilot.md`
- **Suggested branch:** `agent/bld08-worldbuilding-profile-pilot`

## §0 Capability decomposition decision

| Candidate outcome | Independently useful? | Durable/public contract changed? | Decision |
|---|---:|---:|---|
| Add a versioned bounded worldbuilding extraction profile | Yes | Yes | Include |
| Run repeated Shepherd’s Flock trials and record a decision | No — proof required to accept the same profile capability | No durable product contract beyond report | Include |
| Bulk-ingest the corpus | Yes | Yes | Successor |
| Add PDF/OCR lineage | Yes | Yes | Successor: BLD-09 |
| Change generic profile protocol/runtime | Yes | Yes | Stop and return to BLD-04 contract |

**Selected capability:** a bounded executable worldbuilding profile, proven on a
small real source cohort, that remains review-only until Graph Review confirms
selected assertions.

## §1 Mission

The runtime has an explicit versioned worldbuilding extraction profile that owns
its pass, prompt/schema, vocabulary, and validation policy and produces bounded,
source-evidenced Shepherd’s Flock candidates without fabricated session
chronology or incidental ecology/resource explosion.

**Invariant:** every trial uses the exact same admitted profile contract; every
reviewable candidate is within declared category bounds, retains canonical
source evidence, keeps session scope null, and remains proposed until explicit
Graph Review confirmation.

## §2 Context, authority, and boundaries

| Field | Required content |
|---|---|
| Parent authority | `Docs/Design/ARCHITECTURE-campaign-supergraph.md` |
| Sequencing authority | Build slice plan BLD-08 |
| Runtime predecessor | BLD-04 extraction profile protocol/controller and BLD-03 source/run contracts |
| Review predecessor | BLD-07 exact generic Graph Review path |
| Repository rules | `AGENTS.md`, structured extraction/model policy, corpus PII/payload rules, external-agent PR loop |
| Base revision | Dispatch-time immutable merge SHA containing BLD-07 |
| Exact input consumed | explicitly selected local Shepherd’s Flock SourceArtifact revision(s), source spans, exact worldbuilding profile ID/version, and model policy |
| Named successor | BLD-09 PDF/OCR lineage; bulk ingestion and ecology/resource profiles remain later |
| What remains false | no bulk corpus ingestion, PDF lineage, automatic promotion, combat integration, or universal worldbuilding quality claim |
| Explicit non-goals | generic runtime redesign, raw payload publication, corpus rewrite, eval-gold promotion, model/provider UI |

### Locked profile ownership

BLD-04 established a profile protocol. The BLD-08 worldbuilding profile owns or
references executable policy for:

```text
profile_id and profile_version
admitted source_domain/document_class
enabled pass IDs and order
worldbuilding-specific pass instructions/templates
structured-output schema IDs/versions
node/edge vocabulary and context policy
semantic defaults for authority/visibility/canon/session scope
post-extraction category and evidence validation
explicit excluded/deferred category behavior
```

This is not “configuration around unchanged recap prompts.” The profile is the
intentional owner of worldbuilding prompt and schema behavior through BLD-04’s
seam.

Do not edit unrelated `src/prompts/*.py` opportunistically or create a second
prompt registry. If BLD-04’s profile protocol cannot express the required
instructions or schemas, stop and report the missing contract; fix the generic
profile seam in a separately reviewed predecessor correction before continuing.

### Initial category bounds

Included:

- locations and meaningful sublocations;
- factions, organizations, collectives;
- named NPCs and named creatures;
- creature/statblock references as source-backed objects, without inventing
  mechanical fields absent from the source;
- institutions, governance, command, doctrine, and explicit durable
  relationships;
- unresolved mentions when identity cannot be bound safely.

Excluded/deferred by default:

- incidental species, food, flora, products, materials, and scenery;
- unnamed generic inhabitants or disposable encounter instances;
- speculative cosmology or causal claims not stated by the source;
- session beats/chronology for evergreen lore;
- automatic identity merges or label-first edges.

Read in order:

1. Campaign Supergraph architecture
2. Build roadmap/slice plan
3. BLD-04 profile protocol and recap profile tests
4. BLD-03 source/span/run contracts
5. BLD-07 Graph Review binding
6. current category extractor vocabulary/predicate contracts
7. selected local Shepherd’s Flock sources and payload hygiene rules

Stop if the profile requires a new graph identity rule, cannot preserve source
evidence/null session, cannot remain bounded, or cannot be expressed through the
BLD-04 profile protocol.

## §3 Observable-path inventory

| Path | Current behavior | Required behavior | Same invariant? | Boundary |
|---|---|---|---:|---|
| Profile load | no worldbuilding profile | exact ID/version with declared executable policy | Yes | profile registry |
| Source admission | recap assumptions possible | admit only declared worldbuilding source kinds and exact revisions | Yes | profile/controller |
| Pass selection | recap pass set/instructions | explicit bounded worldbuilding passes/order | Yes | profile |
| Prompt/schema | recap-oriented embedded behavior | profile-owned instructions/templates and strict schema refs | Yes | profile/client |
| Category output | broad/recap category behavior | only declared included categories; excluded items omitted/deferred | Yes | profile/validator |
| Source evidence | existing canonical span refs | every positive candidate resolves exact artifact/span | Yes | runtime/validator |
| Session chronology | recap options encourage session/beat fields | session remains null; no session beats invented | Yes | profile/validator |
| Relationships | generic edge extraction | only supported exact endpoints/predicates/evidence | Yes | profile/edge validator |
| Repeat trials | anecdotal one-off possible | at least three comparable trial IDs in one cohort | Yes | pilot harness |
| Trial failure | may disappear into aggregate | refusal/incomplete/schema/validation recorded explicitly | Yes | run/pilot |
| Review | candidate output may look final | exact run opens Graph Review; only selected confirmation publishes | Yes | Graph Review |
| Report hygiene | local payloads | redacted aggregate metrics, IDs, decisions; no raw corpus/model payload | Yes | report boundary |

## §4 Files in scope — allowlist

| Action | Path | Purpose |
|---|---|---|
| Create | `src/graph_memory/extraction/worldbuilding_extraction_profile.py` | Versioned executable category/pass/prompt/schema/vocabulary/validation policy |
| Create | `tests/test_worldbuilding_extraction_profile.py` | Admission, category bounds, prompt/schema ownership, excluded behavior, and null-session proof |
| Create | `tests/test_worldbuilding_profile_pipeline.py` | Fixture-backed source → evidence-bearing candidate/run proof |
| Create | `evals/graph_memory_layer/worldbuilding_profile_pilot.py` | Local repeat-trial cohort runner using production profile/runtime |
| Create | `evals/graph_memory_layer/fixtures/worldbuilding_profile_fixture.json` | Redacted minimal contract fixture, not promoted gold |
| Create | `Docs/Reports/REPORT-build-worldbuilding-profile-pilot.md` | Redacted aggregate evidence, manual judgment, and go/no-go decision |

### Bounded discovery exception

```text
Directory: src/graph_memory/extraction
Maximum additional paths: 2
Allowed path kinds: existing profile registry/export or schema-template module created by BLD-04
Decision rule: only to register or reference the new profile through the established protocol; no generic runtime redesign
Required report: exact predecessor seam and why registration cannot occur in the named profile file
```

Full LLM responses, source excerpts, and local run artifacts remain uncommitted
outside the allowlist.

## §5 Explicitly out of scope

| Path/capability | Why |
|---|---|
| generic controller/profile protocol changes | BLD-04 predecessor correction required |
| `src/prompts/**` unrelated prompt registry/files | no second prompt authority or opportunistic redesign |
| `corpus/**` | no canon rewrite or source mutation |
| eval gold | pilot evidence is not gold promotion |
| UI/backend routes | predecessors already expose product path |
| PDF/OCR | BLD-09 |
| ecology/resource profile | later bounded profile |
| automatic graph commit | Graph Review only |
| identity/merge rules | Kernel-owned |

## §6 Implementation contract

```text
Input:
  exact worldbuilding SourceArtifact revision(s) + canonical source spans +
  profile ID/version + model-policy-resolved client + trial cohort controls.

Output:
  exact ExtractionRuns/candidate graphs governed by the profile plus a redacted
  aggregate report with manual accept/reject/defer decisions.

Invariant:
  only declared categories/passes/templates/schemas execute; session remains
  null; every candidate has evidence; no trial publishes automatically.

Failure behavior:
  unknown/mixed profile version → fail before model call/cohort aggregation
  inadmissible source → fail admission
  excluded category → omit or explicit unresolved/deferred policy, never invent type
  missing evidence → candidate/run non-reviewable
  refusal/incomplete/schema/validation → failed trial, not empty success
  raw payload/source leak → block handback and redact/remove

Replay / idempotency:
  same source digest + profile/version + model policy → comparable cohort inputs
  each trial has distinct exact run/trial ID
  changed source/profile/model policy → new cohort
  report regenerates from local manifests/metrics, not copied raw payloads
  promotion occurs only through exact Graph Review action

Trust boundary:
  Verifies profile/version/admission, executable prompt/schema selection,
  category bounds, source/null-session/evidence rules, trial comparability,
  redaction, and absence of auto-promotion. Human review judges truth.
```

### §6A State/fallback matrix

| Path | Success | Miss | Unavailable | Integrity failure | Stale | Retry |
|---|---|---|---|---|---|---|
| Profile load | exact version | unknown fails | stable error | invalid policy fails | mismatch starts new cohort | exact profile only |
| Source admission | exact artifact revision | missing/invalid source | stable error | digest/scope fail | changed source starts new cohort | exact source |
| Trial | candidate or explicit zero result | empty source invalid | failed exact run | refusal/schema/evidence fail | profile/source mismatch | new trial ID |
| Aggregate | all required comparable trials | incomplete cohort blocked | blocked report | redaction/metadata fail | changed policy invalidates cohort | rerun cohort |
| Review | exact proposed run | no selected assertion no-op | review unavailable | invalid evidence blocks | stale proposal rejects | existing Graph Review flow |

### §6B Identity matrix

| Situation | Required rule | Ambiguity | Fallback |
|---|---|---|---|
| Profile | exact ID/version | mixed/unknown invalid | no default recap profile |
| Source | exact artifact/revision/digest | duplicates flagged by registry | no path/title identity |
| Trial/cohort | unique trial IDs + shared cohort metadata | missing metadata invalidates report | no anonymous trial |
| Candidate | stable assertion + source span IDs | unresolved identity remains unresolved | no first-win merge |
| Session | null for evergreen sources | any fabricated value fails | none |

### §6C Persistence/replay matrix

| Operation | Durable representation | Round trip | Replay | Compatibility | Reversion |
|---|---|---|---|---|---|
| Profile | versioned production code/config | exact executable policy | new version new cohort | recap profile unchanged | revert profile |
| Trial | canonical run manifest + local payloads | exact source/profile/model/trial | distinct IDs | runtime unchanged | delete local payload only |
| Report | redacted aggregate Markdown | regenerate from metrics/manifests | cohort-specific | not gold/canon | correct or withdraw |
| Promotion | existing Graph Review contribution | exact selected assertions | existing receipt semantics | same publication path | existing graph lifecycle |

### §6D Predecessor mapping

| Predecessor | Consumer | Transformation | Proof |
|---|---|---|---|
| BLD-04 profile protocol | worldbuilding profile | supply exact passes/templates/schema/vocabulary/validation | profile tests |
| canonical SourceArtifact/spans | runtime | retain null scope and evidence refs | pipeline tests |
| canonical ExtractionRun | pilot | exact trial/cohort metadata | pilot/report |
| Graph Review | manual decision | keep all outputs proposed until explicit confirmation | integration evidence |

## §7 Verification ownership and commands

| Guarantee | Boundary | Command |
|---|---|---|
| executable profile/version/category bounds | profile | `uv run pytest tests/test_worldbuilding_extraction_profile.py` |
| null session/evidence/source-to-candidate behavior | production pipeline | `uv run pytest tests/test_worldbuilding_profile_pipeline.py` |
| comparable three-trial cohort and redacted aggregation | pilot/report | exact pilot command below |
| no automatic publication | Graph Review/diff | inspect run/report and changed paths |
| no generic runtime redesign | diff/import inspection | changed-path checks |

```bash
uv run pytest tests/test_worldbuilding_extraction_profile.py \
  tests/test_worldbuilding_profile_pipeline.py
uv run python evals/graph_memory_layer/worldbuilding_profile_pilot.py \
  --trials 3
git diff --check
git diff --name-only "$(git merge-base HEAD origin/main)"...HEAD
```

### Minimal live proof

```text
Existing boundaries: production extraction runtime and Graph Review
Scenario: run one exact bounded source/profile cohort three times; inspect
location/faction/NPC/creature/institution candidates, excluded incidental items,
evidence/null session, failures, and one manual Graph Review selection.
Expected: profile behavior is bounded and inspectable; candidates remain proposed;
report contains aggregate metrics/run IDs and no raw payload/source prose.
```

## §8 Required handback

Record SHAs, actual paths/discovery, all commands and provenance, exact source
artifact/profile/model/cohort IDs, aggregate metrics, manual accepted/rejected/
deferred rationale, redaction inspection, baseline failures, waivers, stop
conditions, and confirmation that no generic runtime, corpus, gold, or graph-head
change was smuggled into the pilot.

## §9 Acceptance rubric

- [ ] Profile ID/version and executable pass/prompt/schema/vocabulary/validation policy are explicit.
- [ ] Included and excluded category behavior is fixture-tested.
- [ ] Evergreen candidates retain null session and canonical source evidence.
- [ ] Relationship candidates use exact endpoints/predicates/evidence and unresolved identity stays unresolved.
- [ ] At least three comparable trials produce a redacted aggregate decision report.
- [ ] Refusal/incomplete/schema/validation failures are counted as failures, not empty success.
- [ ] No automatic promotion, corpus rewrite, gold promotion, or generic runtime redesign occurred.
- [ ] Only §4 and approved discovery paths changed.

## Stop conditions

Stop if BLD-04’s profile seam cannot express executable worldbuilding policy,
category bounds cannot prevent explosion, source evidence/null session cannot
survive, a pilot requires corpus/gold mutation, identity semantics must change,
or comparable trials cannot be defined under one source/profile/model cohort.
