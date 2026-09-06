---
pr_body_template: |
  ## Handoff pointer
  - Conversation/workstream: DEMO-READY / Stage 1
  - Flow: DOGFOOD-CONTINUITY
  - Direction: DESIGN → CODE → REVIEW → DOGFOOD STOP
  - Handoff: `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-historical-recap-inspection-v1.md`
  - Branch / PR: `agent/dogfood-continuity-historical-recap-inspection-v1` / `DOGFOOD-CONTINUITY: read historical recaps without promotion`

  ## Verification pointer
  - Base: `af00ec42d03d14dd56230bd201eed495449f3d38`
  - Changed paths: HANDOFF §4
  - Verification: HANDOFF §7

  The checked-in handoff, cumulative diff, numbered review handback, and independently
  rerun evidence are the review contract. Merge does not clear ROADMAP STOP 1;
  assembled human dogfood does.
---

# HANDOFF — Historical Recap Inspection v1

**Created:** 2026-09-06  
**Status:** ACTIVE — dispatch exactly one implementation capability  
**Canonical handoff path:** `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-historical-recap-inspection-v1.md`  
**Conversation/workstream:** `DEMO-READY / Stage 1`  
**Flow / owner:** `DOGFOOD-CONTINUITY`  
**Direction:** DESIGN → CODE → REVIEW → DOGFOOD STOP  
**Base revision:** `af00ec42d03d14dd56230bd201eed495449f3d38`  
**Implementation branch:** `agent/dogfood-continuity-historical-recap-inspection-v1`  
**PR title:** `DOGFOOD-CONTINUITY: read historical recaps without promotion`  
**Parent roadmap:** [`../Roadmaps/ROADMAP-demo-ready-c1-c2-to-of-conks.md`](../Roadmaps/ROADMAP-demo-ready-c1-c2-to-of-conks.md) — **Stage 1**

> Repository law: [`AGENTS.md`](../../AGENTS.md). Steward process: [`Docs/Process/STEWARD-CYCLE.md`](../../Docs/Process/STEWARD-CYCLE.md). External PR mechanics: [`.cursor/skills/external-agent-pr-loop/SKILL.md`](../../.cursor/skills/external-agent-pr-loop/SKILL.md).
>
> **Roadmap gate:** this implementation may merge when its invariant is proven, but **STOP 1 — READ THE HISTORY remains closed until the product owner dogfoods the assembled C1/C2 experience after merge. Do not auto-dispatch Stage 2 or rich-pill work from this PR.**

---

## §0 Steward ruling

DFC-3 / PR #687 proved that DungeonBuddy can discover 53 historical C1/C2 `ingest.run` identities but cannot read the historical recap from the assembled product. The current failure is semantic coupling:

```text
historical run selected
→ Graph Review asks for exact review-package
→ exact review-package resolves through promotable_ingest_run
→ canonical run must be REVIEWABLE
→ validated/prepared history returns 422
→ no source prose is shown
```

That coupling is correct for **promotion** and wrong for **history inspection**.

This PR must not weaken promotion safety. It creates a separate read-only historical recap inspection seam whose only job is:

> **Given one exact canonical recap ExtractionRun, return that run's exact recorded source prose when those bytes can be verified, regardless of whether the run is promotable.**

The frontend then renders those exact source bytes as a comfortable read-only document using the existing `GraphProjectionReader` with no node views or source-span overlays yet.

Do not add pills, assertions, candidate graph review, Threat treatment, Agent context, durable artifact migration, navigation changes, or graph mutation in this slice.

---

## §1 Mission and merge-ready invariant

### Mission

> **A user can load an existing C1/C2 historical recap run and read its exact recap as a rich read-only document even when the run is `validated` or `prepared`, without changing that run's lifecycle or promotion eligibility.**

### Independently useful outcome

After this PR, historical C1/C2 run identity is no longer merely catalog-visible. When exact source bytes for the selected run are available in the current product source authority, Graph Review shows the recap body with normal Markdown structure instead of a lifecycle dead-end.

### Merge-ready invariant

> **For one exact APP-STATE recap ExtractionRun, historical inspection resolves only that run's recorded `source_artifact` component, verifies repository containment and the recorded content digest before returning prose, never requires or changes `REVIEWABLE` status, never substitutes latest/sibling/session/title bytes, and reports exact-source unavailability or integrity failure truthfully without mutating ExtractionRun, World, source, or promotion state.**

### Pre-dispatch critique

| Question | Answer |
| --- | --- |
| Can one invariant govern every claimed observable path? | Yes. Every path is an exact-run, read-only source inspection or preservation of the existing promotion path. |
| Most likely adversarial sequence | User selects a `validated` run whose recorded source path is missing → implementation silently loads another recap for the same session or latest run → UI looks useful but lies about provenance. |
| Will §7 detect that failure? | Yes. Owning tests require exact run/component identity, missing-source no-fallback behavior, digest mismatch failure, and unchanged lifecycle. |
| Easiest owning boundary to under-test | The server read resolver: source path containment/digest verification can be bypassed accidentally if the UI or route reads corpus files directly. |
| Fact that forces stop/split | If readable historical recap requires artifact adoption/copying, session-level source reconstruction, source-registry migration, a new durable storage contract, or candidate/span recovery. Those belong to Stage 2 or a rebrief. |

---

## §2 Context, authority, and boundaries

| Field | Required content |
| --- | --- |
| Parent authority | `Docs/Roadmaps/ROADMAP-demo-ready-c1-c2-to-of-conks.md` Stage 1; `Docs/Roadmaps/ROADMAP-con-ready.md`; `Docs/Plans/STEWARDS-ANCHOR-con-ready.md` |
| Repository rules | `AGENTS.md`; one capability; exact write lease; review every distinct head; backward-looking authority sync in consuming PR |
| Base revision | `af00ec42d03d14dd56230bd201eed495449f3d38` |
| Predecessor | DFC-3 / PR #687, merge `823d9d4121c4534be64bf3de620b24446b2b18ab`, accepted head `29e4e2af0505fdd74ea279b166667ac75db06745`, 3 review cycles |
| Exact input consumed | Canonical APP-STATE `ExtractionRun` selected by exact `run_id`, including its source-domain/scope/status and recorded `source_artifact` component URI + SHA-256; current repo-contained source bytes |
| Existing presentation seam | `GraphProjectionReader` already renders Markdown through read-only TipTap and supports future graph-node/source-span enrichment |
| Existing promotion seam | `get_exact_run_review_package()` → `resolve_promotable_ingest_run()` → `get_reviewable_extraction_run()`; remains strict |
| Named successor | Roadmap Stage 2 — durable historical artifact authority; later Stage 4 — pills/object/provenance/Threat interaction |
| What remains false | Historical candidate assertions/evidence may still be unavailable; historical review/correction remains unavailable unless truly `reviewable`; pills/Threat/Agent/World/NAV1 remain false |
| Branch / isolated checkout | `agent/dogfood-continuity-historical-recap-inspection-v1` + isolated worktree/equivalent |
| Parallel lane state | No open PR observed at handoff creation. Re-run preflight before dispatch. |
| Runtime/state ownership | Real C1/C2 APP-STATE and source bytes are read-only. Tests use isolated state. No historical row/source/World mutation is permitted. |

### 2.1 Read authoritative inputs in this order

1. `AGENTS.md`
2. `Docs/Roadmaps/ROADMAP-demo-ready-c1-c2-to-of-conks.md`
3. `Docs/Reports/REPORT-c1-c2-demo-readiness.md`
4. `Docs/Operations/CAMPAIGN-MATERIAL-LIBRARY-c1-c2.md`
5. `apps/live_control_server/services/graph_run_registry.py`
6. `apps/live_control_server/services/promotable_ingest_run.py`
7. `apps/live_control_server/services/extract_promote.py`
8. `apps/live_control_server/routes/graph_preview.py`
9. `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewWorkbenchModule.tsx`
10. `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewExactRunProjection.tsx`
11. `apps/live-control-ui/src/planSurface/graphProjectionReader/GraphProjectionReader.tsx`
12. owning tests named in §7

If current `main`, the route layout, component model, or DFC-3 evidence differs materially from this handoff, stop before coding.

### 2.2 Why this is a new inspection contract, not a relaxed review contract

Current server truth is intentionally strict:

```text
get_reviewable_extraction_run(run_id)
  status != REVIEWABLE → 422
```

and:

```text
get_exact_run_review_package(run_id)
  → resolve_promotable_ingest_run(run_id)
  → same promotion-grade evidence boundary
```

Do not add `validated` or `prepared` to `EXACT_REVIEWABLE_STATUSES`. Do not weaken `get_reviewable_extraction_run()`. Do not make `resolve_promotable_ingest_run()` accept historical statuses.

The new path is a **read contract** under the existing read-only graph-preview/extraction-run family.

### 2.3 Proposed public read contract

Use this route unless current authority at dispatch provides a clearly better already-mounted read namespace:

```text
GET /api/live/graph-preview/extraction-runs/{run_id}/recap-inspection
```

Response contract, exact naming may follow existing model conventions but semantics may not change:

```text
schema_version: dmb_historical_recap_inspection_v1
run_id
run_status
source_domain
source_artifact_id
campaign_id
session_id
source_status: available | unavailable
source_uri: string | null
source_sha256: string | null
source_prose: string | null
unavailable_reason: string | null
```

The route is exact `run_id` only. It accepts no selector query and performs no latest/session fallback.

### 2.4 Exact source authority

For this slice, the selected canonical `ExtractionRun`'s `source_artifact` component is the locator claim.

Required ready path:

```text
APP-STATE ExtractionRun
→ exact source_artifact component
→ safe repo-contained URI resolution
→ file exists
→ recorded component SHA-256 exists
→ current bytes SHA-256 == recorded SHA-256
→ UTF-8 source prose
→ historical inspection response
```

Do not require candidate graph, source span index, validation report, provenance index, preview union store, SourceArtifact registry reconstruction, or promotability merely to read source prose.

### 2.5 Missing vs integrity failure

Historical material is partially stranded. The read contract must distinguish an ordinary unavailable exact source from evidence corruption.

- missing source component → `source_status=unavailable`;
- source component has no recorded digest → `source_status=unavailable`;
- recorded safe path does not exist in the current authority → `source_status=unavailable`;
- unsafe/escaping URI → fail closed, non-2xx integrity/contract error;
- file exists but SHA-256 disagrees with the run claim → fail closed, non-2xx integrity error;
- invalid UTF-8/read failure → fail closed, non-2xx unreadable/integrity error;
- unknown run ID → 404;
- non-recap source domain → explicit 422/not-applicable, not a generic recap response.

An unavailable exact source is **not permission** to find another file with the same session/title or another run.

---

## §3 Observable paths and adversarial sequences

### 3.1 Observable-path inventory

| Path | Current behavior | Required behavior | Same invariant? | Owning boundary |
| --- | --- | --- | ---: | --- |
| Catalog select `validated` recap with exact source bytes | Workbench binds run, says not exact-reviewable, shows no recap | Load read-only recap inspection and render rich source prose while retaining `validated` status | Yes | server inspection resolver + Graph Review module |
| Catalog select `prepared` recap with exact source bytes | Same dead-end | Same readable historical projection; no promotion claim | Yes | same |
| Catalog select truly `reviewable` run | Existing exact review package / promotion path | Existing behavior remains unchanged | Yes | existing review-package seam |
| Historical source component missing | No prose / lifecycle message | Show exact-source unavailable state for selected run; do not substitute another run/file | Yes | inspection resolver + UI unavailable state |
| Historical source digest missing | Not separately expressed | Unavailable/unverifiable; no prose claimed exact | Yes | inspection resolver |
| Historical source digest mismatch | Not reached for nonreviewable history | Fail closed with integrity error; no prose | Yes | inspection resolver |
| Unsafe source URI | Not reached for nonreviewable history | Fail closed before filesystem read | Yes | inspection resolver |
| Unknown run | Catalog/exact GET failure | 404, no fallback | Yes | route/service |
| Worldbuilding run | Existing separate exact handoff behavior | Recap-inspection rejects as not applicable; existing worldbuilding review path untouched | Yes | route/service |
| Rich source rendering | Exact-review path uses plain `<pre>`; nonreviewable has nothing | Historical source uses existing `GraphProjectionReader` with empty graph enrichment | Yes | UI projection |

### 3.2 Adversarial sequences

| Sequence | Required safe outcome | Owning proof |
| --- | --- | --- |
| Select run A → A source path missing → run B same session has readable source | A remains selected; UI says exact source unavailable; B is never silently loaded | service + UI tests |
| Select `validated` A → inspect source → click/trigger any promotion UI | Inspection never changes A status; promotion remains blocked by existing reviewable rule | API/service tests + existing promote regression |
| Select A → recorded URI points outside repo | inspection fails closed; no bytes returned | service test |
| Select A → source file modified after adoption so digest differs | inspection fails closed; altered prose is not returned | service test |
| Select A → inspection response identity does not match A due to mocked/stale response | client rejects response and does not display prose under wrong run | UI test |
| Load readable A → switch to another catalog run | reader replaces document with the newly selected exact source or truthful unavailable state | UI test |

---

## §4 Files in scope — implementation PR write lease

Every changed path must appear here. Do not add adjacent cleanup.

| Action | Path | Purpose |
| --- | --- | --- |
| Modify | `apps/live_control_server/services/graph_run_registry.py` | Own exact-run read-only source-component resolution, containment/digest verification, and truthful unavailable/integrity states without touching reviewability |
| Create | `apps/live_control_server/models/historical_recap_inspection.py` | Stable read-response contract for exact historical recap source inspection |
| Modify | `apps/live_control_server/routes/graph_preview.py` | Mount exact `run_id` recap-inspection GET under existing read API |
| Modify | `tests/test_graph_run_registry.py` | Owning service proof: validated/prepared read, no fallback, missing, unsafe URI, digest mismatch, no lifecycle mutation |
| Modify | `tests/test_live_recap_ingest_graph_preview_api.py` | HTTP contract proof for ready/unavailable/error/non-recap/unknown paths |
| Modify | `apps/live-control-ui/src/api/types.ts` | Client type for historical recap inspection response |
| Modify | `apps/live-control-ui/src/api/liveApi.ts` | Exact-run recap inspection client call under read API |
| Modify | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/graphReviewWorkbenchUtils.ts` | Classify non-reviewable recap history for inspection without changing exact-reviewable/promotable status law |
| Modify | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/graphReviewWorkbenchUtils.test.ts` | Preserve status classification boundaries |
| Modify | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewWorkbenchModule.tsx` | Fetch source-only inspection for selected non-reviewable recap runs; preserve existing reviewable path |
| Create | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewHistoricalRecapProjection.tsx` | Render exact source prose through existing `GraphProjectionReader` with no graph enrichment yet |
| Modify | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewWorkbenchModule.test.tsx` | User-facing proof for validated/prepared readable history, unavailable state, identity mismatch, and reviewable-path preservation |
| Modify | `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-c1-c2-demo-readiness-survey-v1.md` | Backward-looking sync: DFC-3 accepted/merged, 3 review cycles |
| Modify | `Docs/Roadmaps/ROADMAP-con-ready.md` | Backward-looking sync: DFC-3 done; DEMO-READY Stage 1 active |
| Modify | `Docs/Plans/STEWARDS-ANCHOR-con-ready.md` | Re-anchor current forcing function to this Stage 1 implementation |
| Modify | `Docs/Roadmaps/ROADMAP-demo-ready-c1-c2-to-of-conks.md` | Record DFC-3 merged and Stage 1 ACTIVE; do not pre-mark STOP 1 passed |

### Bounded discovery exception

```text
Directory: apps/live-control-ui/src/planSurface/graphProjectionReader/
Maximum additional paths: 1
Allowed path kinds: existing read-only reader test/style support only
Decision rule: include one path only if GraphReviewHistoricalRecapProjection cannot reuse GraphProjectionReader's current public contract without a narrowly-scoped compatibility adjustment. Any new interaction, pill, source-span, or authoring behavior is a STOP/split.
```

If another path is required, stop and report it before editing.

---

## §5 Explicitly out of scope

| Path / capability | Why |
| --- | --- |
| `apps/live_control_server/services/promotable_ingest_run.py` | Promotion strictness is not being relaxed |
| `apps/live_control_server/services/extract_promote.py` | Existing review-package/prepare semantics remain promotion-grade |
| `apps/live_control_server/routes/extract_promote.py` | Do not turn the promotion namespace into generic historical reading |
| SourceArtifact/registry migration | Stage 2 / durability work; not required to verify one exact source component |
| Historical artifact copy/adoption | Stage 2 |
| Candidate graph/span/validation/provenance recovery | Stage 2 and later rich interaction |
| Entity pills / node cards | Roadmap Stage 4 |
| Threat/statblock projection | Roadmap Stage 4 |
| DungeonMind availability | Roadmap Stage 3 |
| Agent context / observability | Roadmap Stage 7 |
| AppChrome/router/NAV1 | Roadmap Stage 5 |
| Plan/Build/Play recovery | Roadmap Stage 6 |
| Re-ingestion | Prohibited as continuity repair |
| ExtractionRun lifecycle mutation | Inspection is read-only |
| Session-wide inferred recap fallback | Would lie about exact run provenance; rebrief if needed |
| Of Conks content | C1/C2 remain the acceptance corpus |

---

## §6 Implementation contract and matrices

### 6.1 Server contract

```text
Input:
  exact run_id
  canonical APP-STATE ExtractionRun
  recorded SOURCE_ARTIFACT component URI + SHA-256
  current repo-contained source bytes

Output:
  dmb_historical_recap_inspection_v1
  exact run/source identity + lifecycle status
  source prose only when exact bytes verify
  explicit unavailable state when exact bytes are absent/unverifiable

Invariant:
  identical to §1 merge-ready invariant

Failure behavior:
  unknown run → 404
  non-recap run → 422 not applicable
  missing component/path/digest → 200 unavailable, no prose
  unsafe URI → fail closed non-2xx
  digest mismatch → fail closed non-2xx
  unreadable/invalid text → fail closed non-2xx

Replay / idempotency:
  same run + same bytes → same semantic response
  same run + missing bytes → same unavailable response
  same run + changed bytes → integrity failure, never changed prose

Trust boundary:
  Verifies: exact run identity, source-domain applicability, safe containment, recorded digest, current byte digest
  Trusts without proving: historical extraction quality, candidate graph correctness, promotion eligibility
```

No commit point exists. This is a read-only capability.

### 6.2 State / fallback matrix

| Observable path | Exact success | Ordinary unavailable | Dependency unavailable | Integrity failure | Fallback |
| --- | --- | --- | --- | --- | --- |
| recap-inspection GET | exact verified source prose | 200 `source_status=unavailable` | normal APP-STATE/API unavailable behavior | fail closed non-2xx | **None** |
| Graph Review non-reviewable recap | rich read-only exact source | explicit unavailable message retaining selected run/status | surface error remains truthful | error; no prose | **None** |
| Graph Review reviewable recap | existing exact review package | existing behavior | existing behavior | existing behavior | existing review-package only |

### 6.3 Identity matrix

| Situation | Required rule | Ambiguity behavior | Fallback permitted? |
| --- | --- | --- | --- |
| Exact `run_id` | Only selected canonical APP-STATE row | Unknown → 404 | No |
| `source_artifact` component | Only component recorded on selected run | Missing → unavailable | No |
| Campaign/session/title | Display/scope context only | Never used to choose bytes | No |
| Sibling/latest run | Never substituted after explicit run selection | N/A | No |
| Relocated/equivalent file by digest | Not searched in this slice | Rebrief if needed | No |

### 6.4 Persistence / replay matrix

No new persistence is introduced.

| Operation | Durable representation | Round-trip guarantee | Replay behavior |
| --- | --- | --- | --- |
| inspect | none; derived read response | exact source bytes returned only after digest verification | idempotent while authorities unchanged |
| UI reader | ephemeral projection | switching runs replaces projection by exact selected identity | no writes |

### 6.5 Predecessor-to-consumer mapping

| Predecessor fact | Consumer behavior in this PR |
| --- | --- |
| DFC-2c gives canonical APP-STATE run identity/components | inspection starts from exact run row; no manifest fallback |
| DFC-3 proves 53 catalog rows but 0 historical reviewable | non-reviewable recap branch uses source-only inspection |
| DFC-3 ledger records exact component locators/digests | dogfood chooses representative runs known to have source bytes; implementation does not hardcode ledger paths |
| Existing reviewable path is promotion-grade | remains unchanged and tested |
| `GraphProjectionReader` is read-only Markdown presentation | historical source prose renders there with `nodeViews={}` / `sourceSpans={[]}` or equivalent public empty enrichment |

### 6.6 UI contract

For a selected non-reviewable recap run:

```text
selected run identity/status
→ historical recap inspection request
→ identity cross-check response against selected run
→ available: GraphProjectionReader(source_prose, no graph enrichment)
→ unavailable: explicit historical-source-unavailable state
```

The reader must:

- preserve headings, paragraphs, emphasis, lists, tables, links, and useful spacing through the existing Markdown reader;
- hide/handle frontmatter according to existing `GraphProjectionReader` behavior;
- remain read-only;
- display human-facing campaign/session context and lifecycle truth without making `run_id` the document title;
- not render pills merely because `GraphProjectionReader` is capable of graph references; this response contains plain exact source Markdown only.

The existing `GraphReviewExactRunProjection` remains the richer assertion/evidence view for genuinely reviewable packages. Do not force the source-only response into that model.

---

## §7 Evidence required to merge

### 7.1 Server owning-boundary tests

Required proofs:

1. `validated` recap + exact source component/path/digest → inspection 200 with exact prose and `run_status=validated`.
2. `prepared` recap + exact source → same read success, lifecycle unchanged.
3. missing source component → 200 unavailable; no prose.
4. missing exact source file while sibling/session bytes exist → unavailable; no fallback.
5. missing recorded source digest → unavailable; no prose claimed exact.
6. unsafe/escaping URI → fail closed.
7. digest mismatch → fail closed and altered bytes never returned.
8. unknown run → 404.
9. worldbuilding/non-recap run → explicit not-applicable failure.
10. before/after APP-STATE row fingerprint/status unchanged by inspection.
11. existing `get_reviewable_extraction_run()` still rejects `validated`/`prepared`.

Expected focused commands:

```bash
uv run pytest tests/test_graph_run_registry.py -q
uv run pytest tests/test_live_recap_ingest_graph_preview_api.py -q
```

### 7.2 UI owning-boundary tests

Required proofs:

1. selected validated recap requests historical inspection, not `getExactRunReviewPackage`.
2. selected prepared recap does the same.
3. available inspection renders source with semantic Markdown structure through the read-only reader; at minimum prove heading + paragraph + list/table fixture, not only text presence.
4. selected run lifecycle remains visibly truthful (`validated` / `prepared`), with no reviewable/promotable language.
5. unavailable exact source is visible and does not trigger sibling/latest fallback.
6. mismatched inspection response identity is rejected.
7. reviewable run still uses the existing exact review-package path.
8. no prepare/confirm/promotion call is triggered by reading history.

Expected focused commands:

```bash
cd apps/live-control-ui
npm run test -- \
  src/planSurface/graphReviewWorkbench/graphReviewWorkbenchUtils.test.ts \
  src/planSurface/graphReviewWorkbench/GraphReviewWorkbenchModule.test.tsx
npm run typecheck
npm run build
```

### 7.3 Assembled C1/C2 dogfood witness before review approval

Run API + UI from the implementation worktree against the configured 53-row APP-STATE **read-only** if still available. If that leftover authority has disappeared, use an isolated APP-STATE populated through the already-accepted DFC-2c exact adoption path; do not re-ingest and do not silently mutate the operator leftover DB.

Exercise at minimum:

- C1 Session 10 — `graph-ingest:longmont-c1:session-10:20260722T023135Z`;
- C2 Session 23 — use an exact catalog run whose recorded source component is present on current main, such as the later `aed38be1e2c2` source family; record the exact run chosen in the handback;
- C2 Session 25 — `graph-ingest:longmont-c2:session-25:20260808T005650Z`;
- one additional rich C1/C2 session, preferably C1 Session 1;
- one intentionally unavailable exact-source run, proving truthful no-fallback UI.

For each readable witness record:

```text
campaign/session
exact run_id
run lifecycle status
source_artifact_id
inspection HTTP status
source_status
rendered recap heading / representative prose
whether review/promote controls appeared
```

Also record before/after ingest identity digest or equivalent exact-run fingerprint proving no historical mutation.

### 7.4 Static/process verification

```bash
git rev-parse HEAD
uv run python scripts/steward_preflight.py \
  --handoff Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-historical-recap-inspection-v1.md

git diff --check
git diff --name-only af00ec42d03d14dd56230bd201eed495449f3d38...HEAD
```

Changed paths must remain inside §4.

---

## §8 Required implementation handback

Report:

1. `Review Cycle <N>` and exact PR/head SHA;
2. exact base SHA and whether `main` moved during implementation;
3. nano-commit sequence and what each commit proves;
4. actual changed paths vs §4;
5. exact recap-inspection route/schema shipped;
6. server status/fallback matrix results;
7. proof promotion/reviewable semantics were not weakened;
8. UI behavior for validated, prepared, reviewable, unavailable, and identity-mismatch paths;
9. assembled C1S10 / C2S23 / C2S25 / additional-session witness;
10. exact unavailable-source witness proving no fallback;
11. before/after historical run identity/status fingerprint;
12. test/typecheck/build commands and results;
13. backward-looking DFC-3 state-authority sync summary;
14. any STOP/split condition encountered;
15. explicit statement that no re-ingestion, artifact adoption, World mutation, or historical lifecycle mutation occurred.

---

## §9 Acceptance rubric and ROADMAP STOP 1

### Merge acceptance

- [ ] Historical source inspection is a separate read contract from promotion/review.
- [ ] `validated` historical recap with exact source bytes renders in Graph Review.
- [ ] `prepared` historical recap with exact source bytes renders in Graph Review.
- [ ] Recap renders through existing rich read-only Markdown presentation, not `<pre>`.
- [ ] Exact run/status/source identity stays visible and truthful.
- [ ] Missing exact source is explicit and does not fallback.
- [ ] Unsafe/digest-mismatch source fails closed.
- [ ] Reviewable promotion path remains unchanged.
- [ ] No historical DB/source/World mutation occurs.
- [ ] DFC-3 predecessor authority is atomically synchronized as accepted/merged.
- [ ] All changed paths are inside §4.

### STOP / split conditions during implementation

Stop and rebrief if:

- source reading requires copying/adopting historical bytes;
- exact source cannot be resolved without searching sibling runs/session titles;
- a new durable artifact authority is required;
- candidate/span/provenance bytes become required just to show prose;
- promotion/review APIs would need relaxed lifecycle semantics;
- GraphProjectionReader needs new graph/pill behavior to render ordinary Markdown;
- UI work expands into session-navigation redesign, AppChrome, Agent, World, Threats, or general Ingest redesign.

### ROADMAP STOP 1 — READ THE HISTORY

**Merge is not authorization to dispatch Stage 2.**

After this PR merges, stop development and dogfood the merged assembled product with the product owner.

Human question:

> **Can I sit in DungeonBuddy, move among old C1/C2 sessions, and simply read what happened without knowing run IDs, lifecycle semantics, or filesystem paths?**

At that check-in, explicitly judge:

- Is the recap visually pleasant enough to read for several minutes?
- Is session/run selection understandable, or does it still expose pipeline archaeology?
- Does loading history feel like opening a session rather than debugging an ingest run?
- Are missing exact-source states understandable?
- What is the first thing that now feels bad?

Only after that discussion do we decide whether Stage 2 remains next, whether one small Stage 1 UX follow-up is required, or whether the roadmap ordering changes.
