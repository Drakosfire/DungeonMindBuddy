# HANDOFF — BLD-09 PDF/OCR source lineage pilot

- **Created:** 2026-07-22
- **Status:** PREPARED / DRAFT — may be stacked against the BLD-08 head; ACTIVE / MERGEABLE only after BLD-08 merge, rebase, and immutable merge-SHA re-anchor.
- **Canonical handoff path:** `Docs/Plans/HANDOFF-bld09-pdf-ocr-lineage-pilot.md`
- **Suggested branch:** `agent/bld09-pdf-ocr-lineage-pilot`

## Shared vocabulary

| Term | Definition |
|---|---|
| PDF source artifact | A server-admitted PDF-derived source with immutable content identity and lineage. |
| OCR artifact | Validated Markdown/text representation derived from a PDF, not a replacement for the original. |
| Page evidence | Source span metadata retaining PDF/page/region lineage. |
| Mechanical profile | Bounded extraction profile for statblock/mechanical source material. |

## §1 Mission

A bounded PDF/OCR source can enter the existing SourceArtifact → ExtractionRun →
Graph Review path with stable page evidence, explicit validation failures, and
no duplicate durable identity caused by overlapping PDF/Markdown copies.

**Invariant:** PDF-derived candidates remain traceable to the original PDF/page
lineage and cannot be promoted unless the same governed Graph Review path
accepts them.

## §2 Context, authority, and boundaries

| Field | Required content |
|---|---|
| Parent authority | `Docs/Design/ARCHITECTURE-campaign-supergraph.md` |
| Sequencing authority | `Docs/Plans/PLAN-build-surface-worldbuilding-ingest-pr-slices.md`, BLD-09 |
| Repository rules | `AGENTS.md`, `.cursor/rules/corpus-pii-and-llm-payloads.mdc`, `.cursor/rules/responses-api-structured-extraction.mdc`, `.cursor/rules/external-agent-pr-loop.mdc` |
| Base revision | Dispatch-time immutable merge SHA containing BLD-08; current `8ff2339f` is reference only |
| Predecessor contract | BLD-03/04 source/run/runtime, BLD-07 Graph Review, BLD-08 bounded worldbuilding profile |
| Exact input consumed | One explicitly selected local PDF slice, validated OCR/Markdown artifact, page map, mechanical profile |
| Named successor | Bulk corpus ingestion and broader statblock/combat integration |
| What remains false | Bulk PDF ingestion, raw PDF editing in TipTap, new rules semantics, combat automation |
| Explicit non-goals | Corpus-wide dedup migration, canon rewrite, raw payload/report publication, automatic graph commit, PDF viewer/editor UI |

Read in order:

1. `Docs/Design/ARCHITECTURE-campaign-supergraph.md`
2. `Docs/Plans/ROADMAP-build-surface-worldbuilding-ingest.md`
3. `Docs/Plans/PLAN-build-surface-worldbuilding-ingest-pr-slices.md`
4. BLD-03/04 source/run contracts
5. BLD-07 Graph Review publication boundary
6. Existing RulesIngestion Mark III artifact conventions
7. Existing source/provenance tests

If the existing RulesIngestion artifacts cannot provide reliable page lineage,
stop and report the evidence gap instead of guessing page numbers.

## §3 Observable-path inventory

| Path | Current behavior | Required behavior | Same invariant? | Owning boundary |
|---|---|---|---:|---|
| PDF admission | PDF may be treated as raw input without generic source identity | Register exact PDF digest and lineage metadata | Yes | PDF adapter |
| OCR conversion | OCR output may be considered source truth | Validate OCR/Markdown as derived artifact | Yes | OCR validator |
| Page span | Text spans may lose page origin | Every candidate span retains PDF/page reference | Yes | Source-span adapter |
| Duplicate copy | PDF/Markdown copies may produce duplicate identities | Canonical source lineage/digest flags duplicates | Yes | Source registry |
| Mechanical extraction | No bounded PDF profile | Run one explicit mechanical profile | Yes | Extraction profile |
| OCR failure | Generic parse failure | Review-blocking explicit diagnostic | Yes | PDF/OCR controller |
| Graph Review | Generic review predecessor | Same prepare/confirm path | Yes | Graph Review |
| Raw payload/report | Full artifacts are local | Report only redacted aggregate evidence | Yes | Pilot/report boundary |

## §4 Files in scope (allowlist)

| Action | Path | Purpose |
|---|---|---|
| Create | `src/graph_memory/extraction/pdf_source_adapter.py` | PDF/OCR source identity and page-lineage normalization |
| Create | `src/graph_memory/extraction/pdf_lineage.py` | Page/region evidence contract |
| Create | `tests/test_source_artifact_pdf_lineage.py` | PDF digest/page/span/validation proof |
| Create | `tests/test_graph_run_registry_pdf_lineage.py` | Run reload and page-evidence persistence proof |
| Create | `evals/graph_memory_layer/pdf_lineage_pilot.py` | Local bounded pilot runner |
| Create | `evals/graph_memory_layer/fixtures/pdf_lineage_fixture.json` | Redacted page-lineage fixture only |
| Create | `Docs/Reports/REPORT-build-pdf-lineage-pilot.md` | Redacted aggregate pilot report and decision |

**Bounded discovery exception:** Not applicable — paths are enumerated. Raw
PDFs, OCR payloads, and full LLM artifacts remain local and are not added to
the PR allowlist.

## §5 Files and capabilities explicitly out of scope

| Path, layer, or capability | Why out of scope |
|---|---|
| `corpus/**` | No raw PDF/OCR or canon mutation in the implementation PR |
| `src/prompts/*.py` | No prompt redesign |
| `apps/live-control-ui/**` | Raw PDF editing/viewer UI is not Build v0 |
| `apps/live_control_server/routes/**` | Use existing source/run APIs; route changes require a separate contract slice |
| `src/graph_memory/extract_promote_ops.py` | No new publication semantics |
| `evals/**/gold/**` | Pilot does not promote gold |
| Combat/statblock consumer surfaces | Separate successor |
| Bulk corpus runner | Separate successor after pilot evidence |

## §6 Implementation contract and conditional matrices

```text
Input:
  One local PDF identity/digest, validated OCR/Markdown artifact, page map,
  source artifact metadata, and bounded mechanical extraction profile.

Output:
  Source spans with PDF/page lineage, reviewable ExtractionRun, explicit
  validation diagnostics, and redacted aggregate pilot report.

Invariant:
  Every candidate evidence path resolves to PDF/page lineage; invalid OCR,
  missing page map, duplicate identity, or schema failure blocks review.

Failure behavior:
  OCR/page map invalid → source artifact is not admissible.
  Missing page lineage → candidate is non-reviewable.
  Duplicate source digest/lineage → flag/reuse canonical identity per registry.
  LLM refusal/incomplete/schema failure → failed run, no empty candidate graph.
  Report contains raw payload/corpus text → stop and redact before handback.

Replay / idempotency:
  same PDF digest + OCR digest + profile → same source identity policy;
  changed OCR/page map/profile → new derived artifact/run;
  retry after partial OCR validation → remains blocked or resumes explicitly;
  Graph Review confirmation remains the only durable graph write.

Trust boundary:
  Verifies: PDF/OCR digest, page map, source lineage, span references,
  structured output, duplicate policy, and report redaction.
  Records or trusts without proving: mechanical semantic correctness until
  human review.
```

### State and fallback matrix

| Path | Loading | Success | Miss | Dependency unavailable | Integrity failure | Stale | Retry |
|---|---|---|---|---|---|---|---|
| PDF admission | Await local artifact | Register exact digest | Missing PDF blocks | Stable unavailable | Digest/page failure blocks | Changed PDF creates new artifact | Re-admit exact PDF |
| OCR validation | Running/derived state | Validated Markdown + page map | Empty OCR blocks | Tool failure is explicit | Page mismatch blocks | OCR digest mismatch blocks | Re-run OCR as new derivation |
| Extraction | Run state | Candidates with page evidence | No candidates is explicit | Retryable failed run | Schema/evidence failure | Profile/source mismatch | New run |
| Review/promotion | Proposed only | Existing Graph Review confirm | No selected candidate is no-op | N/A | Invalid evidence blocks | Stale proposal rejects | Existing receipt/query path |

### Identity matrix

| Situation | Required rule | Ambiguity behavior | Fallback |
|---|---|---|---|
| PDF source | Stable content digest + source domain | Duplicate/near-duplicate flagged | No filename identity |
| OCR derivation | Parent PDF digest + OCR digest/version | Changed derivation is new artifact | No overwrite |
| Page span | PDF digest + page/region/span ID | Missing page fails review | No paragraph-only fallback |
| Candidate | Source artifact/span assertion ID | Ambiguous duplicate remains unresolved | No first-win merge |
| Mechanical object | Existing graph identity rules | Possible duplicate is review item | No automatic merge |

### Persistence and replay matrix

| Operation | Durable representation | Round-trip guarantee | Duplicate/replay | Compatibility | Rollback |
|---|---|---|---|---|---|
| PDF source | SourceArtifact digest + lineage | Reload preserves parent identity | Duplicate policy explicit | Existing source registry | Mark superseded |
| OCR artifact | Derived artifact with parent/page map | Reload resolves page spans | New OCR version is new derivation | Original PDF remains authority | Preserve old derivation |
| Pilot run | ExtractionRun + local aggregate report | Run points to exact source/profile | Retry creates/resumes explicit run | BLD-08 profile unaffected | No graph write rollback needed |

### Predecessor-to-consumer mapping

| Predecessor | Consumer | Transformation | Proof |
|---|---|---|---|
| RulesIngestion PDF/OCR artifact | `pdf_source_adapter` | Attach digest, parent, page map, and derived content identity | PDF lineage tests |
| Markdown span | Page-aware span | Add PDF/page/region lineage | Span test |
| Generic ExtractionRun | PDF pilot | Store source/profile/page evidence references | Registry test |
| Graph Review | Mechanical candidate | Use existing prepare/confirm path | Promotion integration test/report |

## §7 Verification ownership map and commands

| Guarantee | Owning boundary | Command | Expected evidence |
|---|---|---|---|
| Page lineage is stable | PDF adapter | `uv run pytest tests/test_source_artifact_pdf_lineage.py` | Digest/page/span cases |
| Run reload preserves page evidence | Run registry | `uv run pytest tests/test_graph_run_registry_pdf_lineage.py` | Exact run reload |
| Bounded pilot executes | Pilot runner | `uv run python evals/graph_memory_layer/pdf_lineage_pilot.py --trials 3` | Local aggregate output |
| Review path is reused | Promotion boundary | `uv run pytest tests/test_extract_promote_ops_atomic.py tests/test_live_extract_promote_api.py` | Existing publication contract |
| No raw payload enters docs | Report/diff inspection | Inspect report and changed paths | Redacted aggregate only |
| No scope creep | Git | `git diff --name-only "$(git merge-base HEAD origin/main)"...HEAD` | Only §4 paths |

```bash
uv run pytest tests/test_source_artifact_pdf_lineage.py \
  tests/test_graph_run_registry_pdf_lineage.py \
  tests/test_extract_promote_ops_atomic.py \
  tests/test_live_extract_promote_api.py
uv run python evals/graph_memory_layer/pdf_lineage_pilot.py --trials 3
git diff --check
git diff --name-only "$(git merge-base HEAD origin/main)"...HEAD
```

### Minimal live proof

```text
Existing surface used: local PDF/OCR artifact pipeline and Graph Review
Smallest scenario: admit one bounded PDF slice, validate OCR/page map, extract
one mechanical candidate, review it, and inspect page evidence
Expected observation: page lineage survives reload and invalid artifacts block
Evidence captured: local run IDs and redacted report, never raw payload
```

## §8 Required handback

1. Base and head SHA.
2. Focused diff stat limited to §4.
3. Exact result of every §7 command.
4. Provenance for each result.
5. Page-lineage, duplicate, validation-failure, and review evidence.
6. Base/head comparison for baseline failures.
7. Operator waivers; `none` if none.
8. Paths outside §4; `none` or stop report.
9. Stop conditions; `none` if none.
10. Confirmation that bulk ingestion and combat/statblock integration remain successors.
11. Confirmation that raw PDF/OCR/LLM payloads remain local.

## §9 Acceptance rubric

- [ ] PDF-derived source identity is stable and lineage-aware — proved by adapter tests.
- [ ] Page/region evidence survives source-span and run reload — proved by lineage/registry tests.
- [ ] Invalid OCR/page maps block review — proved by failure tests.
- [ ] Duplicate copies do not silently create durable identities — proved by identity tests.
- [ ] The bounded pilot reports aggregate evidence from at least three trials — proved by pilot command/report.
- [ ] Graph Review remains the only publication path — proved by promotion tests/diff inspection.
- [ ] Raw corpus/LLM payloads remain local — proved by report and changed-path inspection.
- [ ] No path outside §4 changed — proved by changed-path command.

## Stop conditions

Stop and report if:

- page lineage cannot be established from the predecessor artifact;
- OCR validation requires changing corpus canon;
- duplicate detection requires a new global identity/merge contract;
- PDF extraction requires raw PDF editing UI;
- the pilot cannot stay bounded to one source slice and one mechanical profile.

```text
Stop condition:
Why the current mission cannot absorb it:
New contract discovered:
Affected paths:
Proposed successor slice:
Authority update needed:
```
