# HANDOFF — BLD-08 bounded worldbuilding extraction profile and pilot

- **Created:** 2026-07-22
- **Status:** ACTIVE / MERGEABLE candidate — rebased onto `main` after BLD-07 merge (`d4b8a203`). Addressing REQUEST CHANGES round 2: Build launch admits BLD-08 profile, session relationship sweep is profile-gated, automatic identity consolidation is profile-gated, validator exceptions fail closed, pilot records runtime SourceArtifact IDs.
- **Canonical handoff path:** `Docs/Plans/HANDOFF-bld08-worldbuilding-profile-pilot.md`
- **Suggested branch:** `agent/bld08-worldbuilding-profile-pilot`
- **Base revision:** `d4b8a203e48acfc34290747f4080baffdedd1ab9` (BLD-07 merge)

## §0 Capability decomposition decision

| Candidate outcome | Independently useful? | Durable/public contract changed? | Decision |
|---|---:|---:|---|
| Add a versioned bounded worldbuilding extraction profile | Yes | Yes | Include |
| Run deterministic plumbing cohort and record a scoped decision | No — proof required to accept the same profile capability | No durable product contract beyond report | Include (narrowed) |
| Bulk-ingest the corpus | Yes | Yes | Successor |
| Add PDF/OCR lineage | Yes | Yes | Successor: BLD-09 |
| Minimal BLD-04 predecessor seam: `post_extraction_validator` | Yes | Yes | Include (required for truthful bounds) |

**Selected capability:** a bounded executable worldbuilding profile with
production-enforced category bounds, proven by deterministic plumbing trials.
Candidates remain inspect-only under BLD-07 (`promotable=false`); there is no
worldbuilding publication / Graph Review confirmation path in this slice.

## §1 Mission

The runtime has an explicit versioned worldbuilding extraction profile that owns
its pass, prompt/schema, vocabulary, and **executable** validation policy and
produces bounded, source-evidenced Shepherd’s Flock candidates without
fabricated session chronology or incidental ecology/resource explosion.

**Invariant:** every trial uses the exact same admitted profile contract; every
reviewable candidate is within declared category bounds (enforced by
`post_extraction_validator` before VALIDATED/REVIEWABLE), retains canonical
source evidence, keeps session scope null, and remains inspect-only
(`worldbuilding_draft` / non-promotable).

## §2 Context, authority, and boundaries

| Field | Required content |
|---|---|
| Parent authority | `Docs/Design/ARCHITECTURE-campaign-supergraph.md` |
| Sequencing authority | Build slice plan BLD-08 |
| Runtime predecessor | BLD-04 extraction profile protocol/controller and BLD-03 source/run contracts |
| Review predecessor | BLD-07 exact generic Graph Review path (**inspect-only** for worldbuilding) |
| Repository rules | `AGENTS.md`, structured extraction/model policy, corpus PII/payload rules, external-agent PR loop |
| Base revision | `d4b8a203e48acfc34290747f4080baffdedd1ab9` |
| Exact input consumed | redacted fixture SourceArtifact (deterministic plumbing) OR explicitly selected local Shepherd’s Flock revisions for a future quality cohort; exact worldbuilding profile ID/version |
| Named successor | BLD-09 PDF/OCR lineage; bulk ingestion and ecology/resource profiles; authority elevation; real-source quality pilot |
| What remains false | no bulk corpus ingestion, PDF lineage, automatic promotion, worldbuilding Graph Review publication, combat integration, or universal worldbuilding quality claim |
| Explicit non-goals | broad generic runtime redesign, raw payload publication, corpus rewrite, eval-gold promotion, model/provider UI |

### Locked profile ownership

BLD-04 established a profile protocol. The BLD-08 worldbuilding profile owns or
references executable policy for:

```text
profile_id and profile_version
admitted source_domain/document_class
enabled pass IDs and order
worldbuilding-specific pass instructions/templates
structured-output schema IDs/versions
node/edge vocabulary and context policy (IR-compatible types only)
semantic defaults for authority/visibility/canon/session scope
post-extraction category and evidence validation (callable seam)
explicit excluded/deferred category behavior
```

**BLD-04 predecessor correction (minimal):** add
`ExtractionProfile.post_extraction_validator` and invoke it from the generic
production controller before VALIDATED/REVIEWABLE. Do not add a
worldbuilding-specific branch in the runner.

### Profile identity compatibility

Durable ID `worldbuilding_shepherds_flock_v0` is Shepherd’s-Flock-scoped for
this pilot. Document-class admission is intentionally broader
(`lore` / `gazetteer` / `faction` / `place` / `institution` as **document**
classes). That does **not** imply a universal reusable worldbuilding profile or
an `institution` **node** type.

### Initial category bounds

Included (must be subset of production `CandidateGraphPreview.NODE_TYPES`):

- locations and meaningful sublocations;
- factions, organizations, collectives (`group`);
- named NPCs and named creatures;
- creature/statblock references as source-backed objects, without inventing
  mechanical fields absent from the source;
- governance / command / doctrine represented as faction|organization|group;
- unresolved mentions when identity cannot be bound safely.

Excluded/deferred by default:

- incidental species, food, flora, products, materials, and scenery;
- unnamed generic inhabitants or disposable encounter instances;
- speculative cosmology or causal claims not stated by the source;
- session beats/chronology for evergreen lore;
- automatic identity merges or label-first edges;
- distinct `institution` node type (requires durable vocabulary predecessor).

Read in order:

1. Campaign Supergraph architecture
2. Build roadmap/slice plan
3. BLD-04 profile protocol and recap profile tests
4. BLD-03 source/span/run contracts
5. BLD-07 Graph Review binding (inspect-only for worldbuilding)
6. current category extractor vocabulary/predicate contracts
7. selected local Shepherd’s Flock sources and payload hygiene rules

Stop if the profile requires a new graph identity rule, cannot preserve source
evidence/null session, cannot remain bounded, or cannot be expressed through the
BLD-04 profile protocol plus the minimal validator seam above.

## §3 Observable-path inventory

| Path | Current behavior | Required behavior | Same invariant? | Boundary |
|---|---|---|---:|---|
| Profile load | no worldbuilding profile | exact ID/version with declared executable policy | Yes | profile registry |
| Source admission | recap assumptions possible | admit only declared worldbuilding source kinds and exact revisions | Yes | profile/controller |
| Pass selection | recap pass set/instructions | explicit bounded worldbuilding passes/order | Yes | profile |
| Prompt/schema | recap-oriented embedded behavior | profile-owned instructions/templates and strict schema refs | Yes | profile/client |
| Category output | broad/recap category behavior | only declared included categories; excluded items non-reviewable | Yes | profile/validator |
| Source evidence | existing canonical span refs | every positive candidate resolves exact artifact/span | Yes | runtime/validator |
| Session chronology | recap options encourage session/beat fields | session remains null; no session beats invented | Yes | profile/validator |
| Relationships | generic edge extraction | only supported exact endpoints/predicates/evidence | Yes | profile/edge validator |
| Repeat trials | anecdotal one-off possible | at least three comparable plumbing trial IDs | Yes | pilot harness |
| Trial failure | may disappear into aggregate | refusal/incomplete/schema/validation recorded explicitly | Yes | run/pilot |
| Review | candidate output may look final | exact run opens Graph Review inspect-only; prepare rejected | Yes | Graph Review / BLD-07 |
| Report hygiene | local payloads | redacted aggregate metrics, IDs, decisions; no raw corpus/model payload | Yes | report boundary |

## §4 Files in scope — allowlist

| Action | Path | Purpose |
|---|---|---|
| Create | `src/graph_memory/extraction/worldbuilding_extraction_profile.py` | Versioned executable category/pass/prompt/schema/vocabulary/validation policy |
| Edit | `src/graph_memory/extraction/extraction_profile.py` | BLD-04 seams: `post_extraction_validator`, session-sweep + identity-consolidation flags |
| Edit | `src/graph_memory/extraction/graph_preview_runner.py` | Register profile; invoke validator (fail-closed on exceptions) |
| Edit | `src/graph_memory/extraction/category_candidate_graph_extractor.py` | Profile-gated recap relationship sweep + identity consolidation |
| Edit | `apps/live_control_server/routes/graph_preview.py` | Admit BLD-08 profile on Build launch; pass exact ID/version |
| Edit | `apps/live_control_server/services/graph_preview_runner.py` | Pass exact profile through `run_worldbuilding_production_extraction` |
| Edit | `apps/live-control-ui/src/buildSurface/useBuildExtraction.ts` | Launch Build extraction with BLD-08 profile |
| Create | `tests/test_worldbuilding_extraction_profile.py` | Admission, category bounds, rendered prompt/schema, identity preservation |
| Create | `tests/test_worldbuilding_profile_pipeline.py` | Fixture-backed pipeline + negatives + validator exception |
| Edit | `tests/test_graph_preview_routes.py` | Build launch records BLD-08 profile and applies validator |
| Create | `evals/graph_memory_layer/worldbuilding_profile_pilot.py` | Local deterministic plumbing cohort runner |
| Create | `evals/graph_memory_layer/fixtures/worldbuilding_profile_fixture.json` | Redacted minimal contract fixture, not promoted gold |
| Create | `Docs/Reports/REPORT-build-worldbuilding-profile-pilot.md` | Redacted aggregate evidence and scoped go/no-go decision |

Full LLM responses, source excerpts, and local run artifacts remain uncommitted
outside the allowlist.

## §5 Explicitly out of scope

| Path/capability | Why |
|---|---|
| Broad generic runtime redesign beyond profile seams | keep predecessor correction minimal |
| `src/prompts/**` unrelated prompt registry/files | no second prompt authority or opportunistic redesign |
| `corpus/**` | no canon rewrite or source mutation |
| eval gold | pilot evidence is not gold promotion |
| PDF/OCR | BLD-09 |
| ecology/resource profile | later bounded profile |
| worldbuilding prepare/confirm / authority elevation | BLD-07 inspect-only; separate architecture decision |
| graduating `institution` node type | durable vocabulary predecessor |
| Kernel-owned cross-run identity merge policy | only same-run consolidation is profile-gated here |

## §6 Implementation contract

```text
Input:
  exact worldbuilding SourceArtifact revision(s) + canonical source spans +
  profile ID/version + (fixture client | model-policy-resolved client) +
  trial cohort controls.

Output:
  exact ExtractionRuns/candidate graphs governed by the profile plus a redacted
  aggregate report with scoped decision.

Invariant:
  only declared categories/passes/templates/schemas execute; session remains
  null; every reviewable candidate has evidence and passes profile validator;
  no trial publishes automatically; worldbuilding remains non-promotable.

Failure behavior:
  unknown/mixed profile version → fail before model call/cohort aggregation
  inadmissible source → fail admission
  excluded/undeclared category → non-reviewable via post_extraction_validator
  missing evidence → candidate/run non-reviewable when present at controller
  refusal/incomplete/schema/validation → failed trial, not empty success
  raw payload/source leak → block handback and redact/remove

Replay / idempotency:
  same source digest + profile/version + fixture/model policy → comparable inputs
  each trial has distinct exact run/trial ID
  changed source/profile/model policy → new cohort
  report regenerates from local manifests/metrics, not copied raw payloads
  publication is out of scope (inspect-only)

Trust boundary:
  Verifies profile/version/admission, executable prompt/schema selection,
  category bounds via production seam, source/null-session/evidence rules,
  trial comparability, redaction, and absence of auto-promotion.
```

### §6A State/fallback matrix

| Path | Success | Miss | Unavailable | Integrity failure | Stale | Retry |
|---|---|---|---|---|---|---|
| Profile load | exact version | unknown fails | stable error | invalid policy fails | mismatch starts new cohort | exact profile only |
| Source admission | exact artifact revision | missing/invalid source | stable error | digest/scope fail | changed source starts new cohort | exact source |
| Trial | candidate or explicit zero result | empty source invalid | failed exact run | refusal/schema/evidence fail | profile/source mismatch | new trial ID |
| Aggregate | all required comparable trials | incomplete cohort blocked | blocked report | redaction/metadata fail | changed policy invalidates cohort | rerun cohort |
| Review | inspect-only exact run | no prepare/confirm | review unavailable | invalid evidence blocks inspection | stale proposal rejects | existing Graph Review inspect path |

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
| Inspection | existing Graph Review exact-run path | exact run ID | inspect-only | BLD-07 non-promotable | no graph-head write |

### §6D Predecessor mapping

| Predecessor | Consumer | Transformation | Proof |
|---|---|---|---|
| BLD-04 profile protocol + validator seam | worldbuilding profile | supply exact passes/templates/schema/vocabulary/validation callable | profile + pipeline tests |
| canonical SourceArtifact/spans | runtime | retain null scope and evidence refs | pipeline tests |
| canonical ExtractionRun | pilot | exact trial/cohort metadata | pilot/report |
| Graph Review (BLD-07) | manual inspection | keep outputs inspect-only / non-promotable | integration evidence / prior BLD-07 |

## §7 Verification ownership and commands

| Guarantee | Boundary | Command |
|---|---|---|
| executable profile/version/category bounds | profile | `uv run pytest tests/test_worldbuilding_extraction_profile.py` |
| null session/evidence/source-to-candidate + negatives | production pipeline | `uv run pytest tests/test_worldbuilding_profile_pipeline.py` |
| comparable three-trial plumbing cohort | pilot/report | exact pilot command below |
| no automatic publication | Graph Review/diff | inspect run/report and changed paths |
| only allowlisted + validator-seam paths | diff/import inspection | changed-path checks |

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
Existing boundaries: production extraction runtime
Scenario: run the deterministic fixture cohort three times; assert
location/faction/NPC candidates, excluded item / undeclared type / missing
evidence are non-reviewable via the production seam, null session, and
scoped report decision go_deterministic_plumbing.
Expected: plumbing GO only; extraction quality unproven; candidates remain
inspect-only; report contains aggregate metrics/run IDs and no raw payloads.
Optional: open one exact run in Graph Review inspect-only (not required for
plumbing GO).
```

## §8 Required handback

Record SHAs, actual paths/discovery, all commands and provenance, exact source
artifact/profile/cohort IDs, aggregate metrics, scoped decision rationale,
redaction inspection, baseline failures, waivers, stop conditions, and
confirmation that no corpus, gold, or graph-head change was smuggled into the
pilot. The minimal BLD-04 validator seam is an allowed predecessor correction.

## §9 Acceptance rubric

- [ ] Profile ID/version and executable pass/prompt/schema/vocabulary/validation policy are explicit.
- [ ] Included and excluded category behavior is fixture-tested **through the production runtime**.
- [ ] Evergreen candidates retain null session and canonical source evidence.
- [ ] Relationship candidates use exact endpoints/predicates/evidence and unresolved identity stays unresolved.
- [ ] At least three comparable plumbing trials produce a redacted aggregate decision report scoped to deterministic plumbing.
- [ ] Refusal/incomplete/schema/validation failures are counted as failures, not empty success.
- [ ] No automatic promotion, corpus rewrite, gold promotion, or broad generic runtime redesign occurred.
- [ ] Only §4 paths changed (including the named BLD-04 validator seam).

## Stop conditions

Stop if BLD-04’s profile seam cannot express executable worldbuilding policy
even with the minimal validator callable, category bounds cannot prevent
explosion, source evidence/null session cannot survive, a pilot requires
corpus/gold mutation, identity semantics must change, or comparable trials
cannot be defined under one source/profile cohort.
