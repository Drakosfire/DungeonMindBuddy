# HANDOFF — BLD-08 worldbuilding extraction profile and pilot

- **Created:** 2026-07-22
- **Status:** DRAFT — dispatch only after BLD-07 is merged and re-anchored
- **Canonical handoff path:** `Docs/Plans/HANDOFF-bld08-worldbuilding-profile-pilot.md`
- **Suggested branch:** `agent/bld08-worldbuilding-profile-pilot`

## Shared vocabulary

| Term | Definition |
|---|---|
| Worldbuilding profile | Bounded extraction category/version policy for evergreen lore. |
| Pilot source | Small, explicitly selected source set used to falsify the profile. |
| Candidate | Reviewable proposed graph assertion, never automatic canon. |
| Profile explosion | Unbounded extraction of incidental species, products, or low-value nodes. |

## §1 Mission

The runtime has a bounded worldbuilding extraction profile that produces
source-anchored candidates for a small Shepherd’s Flock pilot without
fabricating session chronology or turning incidental ecology into graph truth.

**Invariant:** Worldbuilding extraction is explicit, bounded, source-evidenced,
and review-only; no pilot result is durable graph truth until Graph Review
confirmation.

## §2 Context, authority, and boundaries

| Field | Required content |
|---|---|
| Parent authority | `Docs/Design/ARCHITECTURE-campaign-supergraph.md` |
| Sequencing authority | `Docs/Plans/PLAN-build-surface-worldbuilding-ingest-pr-slices.md`, BLD-08 |
| Repository rules | `AGENTS.md`, `.cursor/rules/responses-api-structured-extraction.mdc`, `.cursor/rules/corpus-pii-and-llm-payloads.mdc`, `.cursor/rules/external-agent-pr-loop.mdc` |
| Base revision | Dispatch-time immutable merge SHA containing BLD-07; current `8ff2339f` is reference only |
| Predecessor contract | Generic SourceArtifact/ExtractionRun/runtime adapters and Graph Review handoff |
| Exact input consumed | Explicitly selected local Shepherd’s Flock source artifact(s), worldbuilding profile version, and model policy |
| Named successor | BLD-09 PDF/OCR source lineage pilot |
| What remains false | Bulk corpus ingestion, PDF lineage, ecology/resource profile, automatic promotion |
| Explicit non-goals | Prompt-file redesign, unbounded category expansion, raw payload sharing, corpus canon rewrite, combat integration |

Read in order:

1. `Docs/Design/ARCHITECTURE-campaign-supergraph.md`
2. `Docs/Plans/ROADMAP-build-surface-worldbuilding-ingest.md`
3. `Docs/Plans/PLAN-build-surface-worldbuilding-ingest-pr-slices.md`
4. BLD-03/04 source/run/runtime contracts
5. BLD-07 Graph Review handoff
6. Existing category profile/schema tests and local pilot conventions

If profile behavior requires editing `src/prompts/*.py`, stop and report the
required prompt decision instead of modifying prompt files opportunistically.

## §3 Observable-path inventory

| Path | Current behavior | Required behavior | Same invariant? | Owning boundary |
|---|---|---|---:|---|
| Profile selection | Recap-shaped/default behavior | Explicit worldbuilding profile/version | Yes | Profile contract |
| Category coverage | Categories may be broad or implicit | Bounded location/faction/NPC/creature/institution coverage | Yes | Profile |
| Source evidence | Candidates may be path/span fragile | Every candidate retains paragraph/source evidence | Yes | Runtime/profile |
| Session chronology | Recap options encourage session fields | Evergreen source keeps session null | Yes | Source/profile validation |
| Incidental ecology | Broad extraction can explode taxonomy | Exclude or classify as unresolved unless explicitly covered | Yes | Profile |
| Repeat trials | Pilot output may be anecdotal | At least three local trials with aggregate reporting | Yes | Pilot harness |
| Review/promotion | Pilot artifacts are not graph truth | Only explicitly selected Graph Review contribution may publish | Yes | Graph Review |
| Payload hygiene | LLM artifacts are local | No raw corpus/LLM payload in docs or external output | Yes | Pilot/report boundary |

## §4 Files in scope (allowlist)

| Action | Path | Purpose |
|---|---|---|
| Create | `src/graph_memory/extraction/worldbuilding_extraction_profile.py` | Bounded profile/version/category policy |
| Create | `tests/test_worldbuilding_extraction_profile.py` | Profile bounds/null-session/forbidden-category proof |
| Create | `tests/test_worldbuilding_profile_pipeline.py` | Fixture-backed source-to-candidate contract proof |
| Create | `evals/graph_memory_layer/worldbuilding_profile_pilot.py` | Local three-trial pilot runner and aggregate output |
| Create | `Docs/Reports/REPORT-build-worldbuilding-profile-pilot.md` | Redacted aggregate pilot report and decision |
| Create | `evals/graph_memory_layer/fixtures/worldbuilding_profile_fixture.json` | Redacted/fixture-only expected profile cases |

**Bounded discovery exception:** Not applicable — paths are enumerated. Full
LLM payloads and raw corpus excerpts remain uncommitted local run artifacts,
not additional allowed paths.

## §5 Files and capabilities explicitly out of scope

| Path, layer, or capability | Why out of scope |
|---|---|
| `src/prompts/*.py` | Prompt redesign requires a separate strong-model design/review slice |
| `corpus/**` | No canon rewrite or raw source mutation |
| `evals/**/gold/**` | Pilot output is not gold promotion |
| `apps/live-control-ui/**` | Build/Graph Review UI already has separate slices |
| `apps/live_control_server/**` | Runtime contract is predecessor; no route changes |
| PDF/OCR paths | BLD-09 |
| Ecology/resource taxonomy expansion | Later bounded profile |
| Automatic graph commit | Graph Review remains the publication owner |

## §6 Implementation contract and conditional matrices

```text
Input:
  Worldbuilding SourceArtifact(s), explicit profile ID/version, source spans,
  configured model policy, and fixture/pilot controls.

Output:
  Bounded candidate graph/run artifacts plus an aggregate three-trial report
  stating accepted/rejected/deferred profile behavior.

Invariant:
  Profile emits only declared bounded categories, preserves source evidence,
  keeps session scope null, and never promotes pilot output automatically.

Failure behavior:
  Unsupported category → omit or mark unresolved under explicit policy; never
  silently invent a category.
  Missing source evidence → candidate is non-reviewable.
  Profile/version mismatch → fail before extraction.
  LLM refusal/incomplete/schema failure → failed trial/run, not empty success.
  Payload/report hygiene violation → stop and remove/redact before handback.

Replay / idempotency:
  same source/profile/model policy → distinct trial IDs but comparable input;
  changed profile/source digest → new trial cohort;
  three trials report aggregate metrics, not raw payload;
  pilot results never mutate durable graph without explicit Graph Review action.

Trust boundary:
  Verifies: category bounds, profile version, source/session scope, evidence,
  structured output, trial manifest, and redaction.
  Records or trusts without proving: semantic truth until GM review.
```

### State and fallback matrix

| Path | Loading | Success | Miss | Dependency unavailable | Integrity failure | Stale | Retry |
|---|---|---|---|---|---|---|---|
| Profile load | Load explicit version | Use exact profile | Unknown profile fails | Stable dependency error | Invalid profile fails | Version mismatch fails | Re-run exact profile |
| Trial | Record running state | Persist candidate/run result | Empty source is explicit | Retryable failed trial | Schema/evidence failure | Source digest mismatch | New trial ID |
| Aggregate report | Await all required trials | Report aggregate metrics | Incomplete cohort is not ready | Mark blocked | Redaction failure blocks report | Profile changed starts new cohort | Repeat cohort |
| Promotion | No automatic action | Graph Review only | No selected candidates is no-op | N/A | Candidate remains unreviewable | Proposal stale | Existing confirm flow |

### Identity matrix

| Situation | Required rule | Ambiguity behavior | Fallback |
|---|---|---|---|
| Profile | Stable ID + version | Unknown/mixed version fails cohort | No default profile |
| Source | Exact artifact/digest | Duplicate source copy is flagged | No path-label identity |
| Trial | Unique trial ID with shared cohort metadata | Missing trial metadata invalidates report | No anonymous trial |
| Candidate | Stable assertion/source span IDs | Ambiguous identity remains unresolved | No first-win merge |
| Session scope | Always null for evergreen source | Any fabricated session fails acceptance | No synthetic session |

### Persistence and replay matrix

| Operation | Durable representation | Round-trip guarantee | Duplicate/replay | Compatibility | Rollback |
|---|---|---|---|---|---|
| Profile | Versioned code/config contract | Same version reloads same bounds | New version creates new cohort | Recap profile unchanged | Revert profile |
| Trial | Local run manifest/output | Inputs and model policy recorded | Repeat gets distinct trial ID | No graph truth claim | Delete local payload only |
| Report | Redacted aggregate Markdown | No raw corpus/LLM payload | Regenerate from local artifacts | Not gold | Correct report or withdraw |

### Predecessor-to-consumer mapping

| Predecessor | Consumer | Transformation | Proof |
|---|---|---|---|
| Generic extraction options | Worldbuilding profile | Select explicit bounded categories and null scope | Profile tests |
| Source spans | Candidate assertions | Preserve paragraph evidence | Pipeline tests |
| Run registry | Pilot runner | Record exact source/profile/trial IDs | Pilot tests |
| Graph Review | Promotion decision | Keep pilot output proposed until explicit selection | Report + boundary inspection |

## §7 Verification ownership map and commands

| Guarantee | Owning boundary | Command | Expected evidence |
|---|---|---|---|
| Profile categories are bounded | Profile contract | `uv run pytest tests/test_worldbuilding_extraction_profile.py` | Allowed/forbidden category cases |
| Null session and source evidence hold | Pipeline | `uv run pytest tests/test_worldbuilding_profile_pipeline.py` | Candidate anchors and null scope |
| Three trials are comparable and redacted | Pilot/report | `uv run python evals/graph_memory_layer/worldbuilding_profile_pilot.py --trials 3` | Local aggregate artifact; no payload in report |
| No automatic promotion | Review boundary/diff | Report and diff inspection | No commit call |
| No scope creep | Git | `git diff --name-only "$(git merge-base HEAD origin/main)"...HEAD` | Only §4 paths |

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
Existing surface used: local graph extraction/pilot runner and Graph Review
Smallest scenario: run the same bounded source/profile three times, aggregate
candidate category/evidence outcomes, and review without auto-commit
Expected observation: stable evidence/null session; bounded category behavior
Evidence captured: local run IDs and redacted aggregate report only
```

## §8 Required handback

1. Base and head SHA.
2. Focused diff stat limited to §4.
3. Exact result of every §7 command.
4. Provenance for each result.
5. Three-trial aggregate and redaction evidence.
6. Base/head comparison for baseline failures.
7. Operator waivers; `none` if none.
8. Paths outside §4; `none` or stop report.
9. Stop conditions; `none` if none.
10. Confirmation that BLD-09 owns PDF/OCR.
11. Confirmation that no prompt file, corpus canon, gold, or graph head changed.

## §9 Acceptance rubric

- [ ] Profile is explicit, versioned, and bounded — proved by profile tests.
- [ ] Location/faction/NPC/creature/institution coverage is fixture-tested — proved by pipeline tests.
- [ ] Evergreen candidates retain null session and source evidence — proved by pipeline tests.
- [ ] Pilot runs at least three trials and reports aggregate outcomes — proved by pilot command/report.
- [ ] Raw corpus/LLM payloads remain local and redacted — proved by report/diff inspection.
- [ ] No automatic graph promotion occurs — proved by review boundary inspection.
- [ ] No path outside §4 changed — proved by changed-path command.
- [ ] BLD-09 remains unimplemented and unclaimed.

## Stop conditions

Stop and report if:

- prompt changes are required to achieve profile behavior;
- profile bounds cannot prevent category/ecology explosion;
- a pilot requires modifying corpus canon or eval gold;
- source evidence or null session scope cannot survive extraction;
- three trials cannot be made comparable under one profile/version.

```text
Stop condition:
Why the current mission cannot absorb it:
New contract discovered:
Affected paths:
Proposed successor slice:
Authority update needed:
```
