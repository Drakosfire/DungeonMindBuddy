---
pr_body_template: |
  ## Handoff pointer
  - Conversation/workstream: DOGFOOD-CONTINUITY / durable richness recovery
  - Flow: DOGFOOD-CONTINUITY
  - Direction: DESIGN → CODE → REVIEW → MERGE → HUMAN DOGFOOD
  - Handoff: `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-db-backed-graph-object-provenance-v1.md`
  - Branch / PR: `dogfood-continuity/no-document-primary-surface-nav-v1` / PR #695 / `DOGFOOD-CONTINUITY: project graph-object provenance from durable source bytes`

  ## Verification pointer
  - Base: `c032f9473380a9121cac41b3f3d08ad46628672b` (`main`; includes #694 merge `df15db4c695240ce08b5812d43ca398cd70ff6ac`)
  - Predecessor: PR #694 merged; Stage 5A same-document navigation passed human dogfood and Stage 5B is conditional/parked
  - Live witness: C2 Session 25 durable source + World `node:orik` → Brin relationship provenance
  - Verification: DB-only provenance path + field-preservation tests + no-click-fetch browser witness + build

  The checked-in handoff, cumulative diff, nano-commit story, independently
  rerun evidence, and live witness are the review contract. This body is
  transport metadata only.
---

# HANDOFF — DOGFOOD-CONTINUITY: DB-backed graph-object provenance v1

**Created:** 2026-09-08
**Status:** IMPLEMENTATION IN REVIEW — PR #695; not DONE
**Canonical handoff path:** `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-db-backed-graph-object-provenance-v1.md`
**Conversation/workstream:** `DOGFOOD-CONTINUITY / durable richness recovery`
**Flow / owner:** `DOGFOOD-CONTINUITY`
**Direction:** DESIGN → CODE → REVIEW → MERGE → HUMAN DOGFOOD
**Base revision:** `c032f9473380a9121cac41b3f3d08ad46628672b` — current `main` (includes #694 merge `df15db4c695240ce08b5812d43ca398cd70ff6ac`)
**Design-handoff origin:** `dogfood-continuity/db-backed-graph-object-provenance-v1` @ `57c4cb9fc1040dbfd10f5e46f7c04124adf99d67`
**Implementation branch:** `dogfood-continuity/no-document-primary-surface-nav-v1`
**PR:** `#695`
**PR title:** `DOGFOOD-CONTINUITY: project graph-object provenance from durable source bytes`

> Repository law: [`AGENTS.md`](../../AGENTS.md). Product sequence: [`Docs/Roadmaps/ROADMAP-demo-ready-c1-c2-to-of-conks.md`](../Roadmaps/ROADMAP-demo-ready-c1-c2-to-of-conks.md). Current steward anchor: [`STEWARDS-ANCHOR-con-ready.md`](STEWARDS-ANCHOR-con-ready.md). Historical presentation evidence: PR #372 / commit `82a5361325c79ae453d15fd53264d24800c11096`.

---

## §0 Accepted product ruling and exact re-anchor

The operator clarified the current program:

> First recover the fun/useful prototype capability as a real product capability: project it well, project it fast, read it from durable DB-backed authorities, and make the underlying state destroyable/recoverable. Once that substrate is trustworthy, deliberately make the styling and presentation fun and readable.

That means this is **not** the natural-language / visual redesign of the Orik card.
It is the durable projection substrate that the later presentation slice must be able to trust.

Exact repository truth at this authority attachment:

```text
main                            c032f9473380a9121cac41b3f3d08ad46628672b
PR #694                         MERGED as squash df15db4c695240ce08b5812d43ca398cd70ff6ac
accepted #694 head              d82ac0c755ad3e7581fa7a023f9c2bb46df64337
formal #694 review cycles       2
Stage 5A                        implementation merged + human dogfood PASS
Stage 5B                        conditional / PARKED unless a concrete remount failure reappears
Stage 2 / STOP 2                OPEN
implementation PR               #695
implementation branch           dogfood-continuity/no-document-primary-surface-nav-v1
design-handoff origin           dogfood-continuity/db-backed-graph-object-provenance-v1 @ 57c4cb9f
Review Cycle 1                  d123327b HOLD — presentation scope, incoming-edge copy, root Backlog IDEA
Review Cycle 2                  2b2b198a code PASS / PR HOLD — missing lane authority + exact-head evidence
this attachment                 Cycle 3 head will be the docs/state-sync commit; do not pre-mark PASS
```

PR #694 removed the full-document reload from Index / Plan / Play / Ingest / Build. The operator called the result a **big win**. Do not immediately dispatch Stage 5B from this slice.

### Current durable authority coordinates

```text
DungeonMind World authority     127.0.0.1:54330 / dungeonmind_cutover_live
Buddy APP-STATE                 127.0.0.1:54331 / dungeonbuddy_application_state
DungeonMind dev                 127.0.0.1:54329 / disposable tmpfs; not product authority
```

World remains graph truth. APP-STATE owns exact Buddy source bytes. Buddy may make product-presentation joins between admitted World evidence and exact APP-STATE source bytes, but must not reconstruct graph truth or invent evidence.

### Existing accepted C2S25 witness

```text
run_id
  graph-ingest:longmont-c2:session-25:20260808T005650Z

source_artifact_id
  artifact:recap:longmont-c2:session-25:fd38b5915b32

source_revision_id
  8ed1e034-23c6-4295-b2ff-05d5cdd643a9

source SHA-256
  fd38b5915b32beb77142c0334c578e7ff0d46ef6d91deb545801761508d26d0d

World
  eldyrwild

previously observed World head
  rev:680c246047d67f9fe0293ee90526f670

World object
  node:orik

known related context
  Brin
```

Stage 2B already proved the source revision survives APP-STATE recovery and that clicking Orik can resolve through the durable World authority without moving the World head.

### New design finding: rich provenance still leaks through the filesystem boundary

The mounted DungeonMind read adapter explicitly classifies source text/excerpts as a **Buddy product-local presentation join**, not graph authority. The current generic projection implementation still resolves relationship excerpts from product-local `source_span_index.json` under `repo_root` when available.

At the same time:

1. `HistoricalRecapWorldProjectionResponse` already loads the exact selected recap from APP-STATE before asking DungeonMind for the current World projection.
2. DungeonMind evidence already carries exact `source_artifact_id`, `source_revision_id`/digest provenance, and `source_span_ref_id` identities.
3. C2S25 uses digest-bound line spans such as:

```text
evidence:artifact:recap:longmont-c2:session-25:fd38b5915b32:
artifact:recap:longmont-c2:session-25:fd38b5915b32:
span:fd38b5915b32:23-23
```

4. Existing source-anchor logic already understands digest-bound line-span and recap-paragraph identities without consulting `source_span_index.json`.
5. The server World wire already supports:

```text
sourceExcerpt
sourceExcerptIsFullParagraph
sourceExcerptHighlightSpans
```

6. Buddy's camelCase `WorldGraphProjectionAdjacencyCandidate` and `worldGraphNodeViewAdapter.ts` currently preserve `sourceExcerpt` but drop the latter two fields before the shared card model.

This slice repairs **that one end-to-end provenance path** for durable historical recap reading.

### §0A Backward-looking predecessor sync

The implementation PR must truthfully record facts already true before this slice begins:

```text
PR #694                         DONE / MERGED
merge                           df15db4c695240ce08b5812d43ca398cd70ff6ac
review cycles                   2
Stage 5A                        accepted by human dogfood
Stage 5B                        conditional / parked
current capability              DB-backed graph-object provenance v1
Stage 2 / STOP 2                OPEN
Stage 4                         NOT DONE
```

Sync these mutable authorities inside the implementation PR:

```text
Docs/Roadmaps/ROADMAP-demo-ready-c1-c2-to-of-conks.md
Docs/Plans/STEWARDS-ANCHOR-con-ready.md
Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-no-document-primary-surface-nav-v1.md
```

The sync may record this slice as CURRENT. It must not pre-mark this slice DONE, close Stage 2 / STOP 2, close Stage 4, or advance the later presentation/styling slice.

---

## §1 Mission and merge-ready invariant

**Mission:** When a historical recap already has an exact durable APP-STATE source revision, relationship provenance shown from its World-object cards comes from those durable source bytes rather than a checkout-local sidecar/file join, and the complete server provenance shape survives Buddy's client adapter without loss.

**Merge-ready invariant:**

> Loading the exact C2 Session 25 historical recap and opening `node:orik` can expose the Orik/Brin relationship's admitted source prose using the APP-STATE `source.revision` bytes bound to `artifact:recap:longmont-c2:session-25:fd38b5915b32`; the result remains available when checkout-local `source_span_index.json` / source-sidecar material is absent; the relationship's `sourceExcerpt`, `sourceExcerptIsFullParagraph`, and `sourceExcerptHighlightSpans` survive the server → UI World-node-view → shared-card adaptation; no graph write, re-ingestion, new durable state, filesystem fallback, or extra click-time network request is required.

### What this capability proves

```text
DungeonMind World evidence identity
        +
APP-STATE exact source bytes
        ↓
validated product-presentation provenance join
        ↓
World node view
        ↓
Buddy client adapter with no field loss
        ↓
existing GraphObjectCard model
```

### What it deliberately does not prove

```text
all historical recap sources are adopted                 FALSE
all World/worldbuilding source bytes are DB-backed        FALSE
Orik card natural-language composition is finished        FALSE
Threat-specific presentation is finished                  FALSE
Stage 4 recap WOW experience is finished                  FALSE
```

---

## §2 Authority and trust-boundary contract

### Truth ownership

| Data | Authority | Rule |
|---|---|---|
| object / relationship identity | DungeonMind World `54330` | Buddy reads only |
| predicate / campaign scope / evidence refs | DungeonMind World `54330` | never inferred from prose |
| exact selected C2S25 recap bytes | Buddy APP-STATE `54331` `source.revision` | exact artifact + digest binding |
| source span identity | DungeonMind evidence | must match admitted evidence; no fuzzy rebinding |
| source excerpt text | deterministic product join | slice exact APP-STATE bytes using admitted span identity |
| card rendering model | Buddy UI | may present; may not invent missing graph/source facts |

### Fail-closed rules

The durable excerpt is **available only when all required bindings agree**:

```text
World evidence source_artifact_id
  == APP-STATE source_artifact_id

DungeonMind-admitted source revision digest
  == APP-STATE source.revision content_sha256

source_span_ref_id
  resolves under the existing admitted span grammar

span digest prefix (when present)
  == bound source digest prefix
```

If any requirement fails:

- do not read a repository file as fallback;
- do not consult `source_span_index.json` as fallback on this historical path;
- do not synthesize an excerpt from nearby text;
- do not attach another source's excerpt;
- keep the relationship valid but provenance text unavailable;
- surface a bounded diagnostic only where the existing response contract supports diagnostics without inventing a second product state.

### Existing span grammar is authority

Do **not** create a second historical-span grammar.

Reuse/hoist the existing direct-read logic that already understands:

```text
…:paragraph:NNN
…:span:<12-hex-digest-prefix>:<start>-<end>
```

The implementation may make that resolver a shared pure helper if necessary. It must remain deterministic and digest-bound.

---

## §3 Observable paths and adversarial sequences

| Path | Required behavior | Owning boundary |
|---|---|---|
| Load C2S25 historical recap | APP-STATE exact source bytes + one current World projection produce recap/node views | historical recap projection service |
| Click Orik | existing in-memory node view opens; no new source/World request solely to render card | historical recap UI |
| Orik → Brin relationship | source prose comes from C2S25 APP-STATE source bytes when admitted evidence points at that source | durable provenance join |
| Checkout lacks `source_span_index.json` | same durable Orik/Brin provenance still resolves | server integration test/live witness |
| APP-STATE source absent | historical recap already fails closed as `source_content_unavailable`; no filesystem rescue | historical recap service |
| evidence artifact differs from selected recap | relationship may remain visible; excerpt from selected recap is not attached | provenance join |
| digest-bound span prefix mismatches | excerpt unavailable; never slice mismatched bytes | span resolver |
| client adaptation | full paragraph/highlight metadata survives camelCase → snake_case adapter | UI adapter |
| unrelated World projection consumers | retain existing behavior; this slice does not migrate Plan/Build generic World source joins | generic World service |

### Adversarial sequence A — no checkout-sidecar dependence

```text
persist exact C2S25 source in disposable APP-STATE
provide admitted World evidence for artifact fd38… / span fd38…:23-23
make repo_root empty / no source_span_index.json
build historical recap projection
→ exact excerpt resolves from APP-STATE markdown
```

### Adversarial sequence B — digest mismatch

```text
World evidence points at span fd38…:23-23
APP-STATE bytes/digest do not match fd38…
→ no provenance excerpt
→ no repo fallback
→ no graph mutation
```

### Adversarial sequence C — cross-artifact evidence

```text
Orik has relationship evidence from C2S25 + another source
selected durable source = C2S25
→ only evidence bound to C2S25 may yield C2S25 source prose
→ other evidence remains represented by its evidence refs without fabricated prose
```

### Adversarial sequence D — UI field preservation

```text
World adjacency
  sourceExcerpt = "…"
  sourceExcerptIsFullParagraph = true
  sourceExcerptHighlightSpans = [{start, end}]

adaptWorldGraphNodeView(...)
→ GraphProjectionAdjacencyCandidate retains all three values exactly
→ buildGraphObjectCardFromNodeView(...) retains them exactly
```

---

## §4 Files in scope — write lease

Expected cumulative changed paths:

| Action | Path | Purpose |
|---|---|---|
| Create | `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-db-backed-graph-object-provenance-v1.md` | slice authority |
| Modify | `Docs/Roadmaps/ROADMAP-demo-ready-c1-c2-to-of-conks.md` | record #694 merge/human acceptance, park Stage 5B, set this capability current |
| Modify | `Docs/Plans/STEWARDS-ANCHOR-con-ready.md` | re-anchor to #694 merge + current durable-richness slice |
| Modify | `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-no-document-primary-surface-nav-v1.md` | backward-looking #694 merge / 2-cycle / human-accepted status |
| Modify | `apps/live_control_server/services/historical_recap_world_projection.py` | own exact APP-STATE source → admitted World-evidence provenance join |
| Modify | `apps/live_control_server/services/world_graph_projection.py` | allow historical path to request World projection without checkout-local excerpt hydration, if required |
| Modify | `apps/live_control_server/integrations/dungeonmind/world_graph_reads.py` | expose/reuse existing pure digest-bound span logic and/or disable repo-sidecar excerpt join for this explicit path; no World semantics change |
| Modify | `apps/live-control-ui/src/api/types.ts` | make camelCase World adjacency type faithfully represent server provenance fields |
| Modify | `apps/live-control-ui/src/worldGraph/worldGraphNodeViewAdapter.ts` | preserve complete provenance fields into shared snake_case card model |
| Modify | `apps/live-control-ui/src/worldGraph/worldGraphNodeViewAdapter.test.ts` | field-preservation regression |
| Modify | `tests/test_historical_recap_world_projection.py` | owning server regressions: APP-STATE bytes, no sidecar, mismatch/cross-artifact |

### Bounded discovery exception

One additional production helper path may be created or modified **only** if it is necessary to hoist the existing digest-bound span slicing into a pure shared function rather than duplicate the grammar.

Allowed area:

```text
apps/live_control_server/services/
apps/live_control_server/integrations/dungeonmind/
src/graph_memory/retrieval/
```

Maximum additional production paths: **1**.

One additional focused test path may accompany that helper.

Decision rule:

> Prefer reusing/hoisting one existing pure span resolver. Do not duplicate the digest/paragraph parsing rules in a second module merely to stay under the path count.

Any other production path outside §4 is a stop report.

---

## §5 Explicitly out of scope

Do not absorb any of these into this PR:

- bulk C1/C2 source adoption / Stage 2C coverage expansion;
- unknown historical `source_revision_id` policy;
- C1 Session 10 repair;
- new APP-STATE tables, migrations, or source formats;
- DungeonMind schema/revision/contribution writes;
- World head advancement;
- re-ingestion / re-extraction;
- generic Plan/Build World-source join migration;
- object-card CSS redesign;
- natural-language card header composition such as `Orik is a Mireward defender.`;
- removal/reordering of NPC/campaign/type badges;
- new `whyItMattersNow` generation;
- model-generated summaries;
- Threat/statblock styling or hydration;
- prior/next session navigation;
- Agent-on-Ingest;
- Stage 5B AppChrome remount work;
- authority auto-start/restart policy;
- remote/VPC/object-storage move.

### Product-presentation posture

This slice may make already-supported provenance **appear** in the existing card because the data finally reaches it. It must not redesign the card around raw graph structure.

The later presentation slice owns questions such as:

```text
Should the top read:
  ORIK
  Orik is a Mireward defender.

instead of:
  NPC · LONGMONT C2
  ORIK
  Mireward defender · associated with Brin
```

Do not solve that here.

---

## §6 Implementation contract

### §6A Historical projection source posture

Current historical recap projection already performs the authoritative source lookup once:

```text
ExtractionRun exact artifact + digest
        ↓
source_service.get_source_markdown(...)
        ↓
APP-STATE SourceMarkdownRecord
```

Reuse that already-loaded `SourceMarkdownRecord`.

Do not perform a second APP-STATE lookup per node, relationship, or click.

The historical projection's World read must be able to run without product-file excerpt hydration. An internal option/strategy on the World projection service is acceptable if needed, provided:

- the public HTTP World projection request schema does not change;
- default behavior of unrelated consumers does not change;
- no second World read path is created;
- the direct DungeonMind adapter remains the only mounted graph read path.

### §6B Durable provenance join

Build a mapping from the admitted World projection's evidence views:

```text
evidence_ref_id
  → source_artifact_id
  → source_span_ref_id
  → DungeonMind source revision digest
```

For evidence bound to the exact selected durable source artifact/digest, resolve source text from `source.markdown` using the existing digest-bound span grammar.

Apply the resolved provenance to adjacency / suggested-expansion records without changing:

- edge identity;
- node identity;
- predicate;
- direction;
- campaign scope;
- evidence refs;
- focus anchoring;
- ranking.

No evidence = no excerpt.

### §6C Client field fidelity

The current server World contract already emits the complete adjacency provenance shape. Buddy's client type/adapter must become lossless for that shape.

At minimum preserve:

```text
sourceExcerpt
sourceExcerptIsFullParagraph
sourceExcerptHighlightSpans
```

Before implementation, produce a short field matrix comparing:

```text
server WorldGraphProjectionAdjacencyCandidate
→ UI WorldGraphProjectionAdjacencyCandidate
→ GraphProjectionAdjacencyCandidate
→ GraphObjectRelationshipViewModel
```

If another field from the existing server contract is silently dropped at the same adapter boundary, it may be repaired **only if it belongs to this same relationship-provenance/card-data contract**. Record it explicitly in the handback.

A missing new server concept is not permission to expand the contract. Stop instead.

### §6D Performance contract

This capability must be cheap by construction:

```text
historical recap load
  existing APP-STATE source lookup: 1
  World projection calls:           1
  additional DB lookup per node:    0
  additional DB lookup per edge:    0
  click-time source requests:        0
  click-time World requests:         0 solely for card provenance
```

Source span resolution should operate in memory over the already-loaded source Markdown and already-returned World evidence/node views.

Do not add an N+1 provenance API.

Record one warm-path timing observation before/after on the exact head if practical. Timing is diagnostic, not a microbenchmark contest; any obvious material regression should be investigated before merge.

### §6E Recovery posture

This PR creates **no new durable state**.

It consumes the already-recoverable APP-STATE `source.revision` bytes whose persistence is covered by the Stage 2A/2B authority fingerprint/backup contract.

Therefore:

- do not destroy the live 54331 volume merely to re-prove Stage 2A;
- do prove in disposable integration coverage that provenance resolution succeeds with no source-sidecar files present;
- live witness must record the exact source revision ID/digest used;
- if implementation introduces any new durable state, STOP — that is a second capability and needs a new persistence/recovery contract.

---

## §7 Evidence required to merge

### §7A Required automated evidence

Server focused tests:

```bash
uv run pytest -q \
  tests/test_historical_recap_world_projection.py \
  tests/application_state/test_source_content_postgres.py
```

If the shared span helper touches an existing owning test, include that exact test path in the focused command.

UI focused tests:

```bash
npm --prefix apps/live-control-ui run test -- \
  src/worldGraph/worldGraphNodeViewAdapter.test.ts \
  src/graphObjectCard/buildGraphObjectCardFromNodeView.test.ts
```

Required quality gates:

```bash
uv run ruff check <changed Python paths>
npm --prefix apps/live-control-ui run build
git diff --check
git diff --name-only c032f9473380a9121cac41b3f3d08ad46628672b...HEAD
```

Use the repository's known baseline discipline if unrelated full-suite failures exist: record base/head exact failure classes rather than silently waiving them.

### §7B Required server owning-boundary tests

At minimum prove:

1. exact APP-STATE source bytes + matching World evidence span → excerpt;
2. no `source_span_index.json` / no source-sidecar available → same excerpt;
3. mismatched digest prefix → no excerpt / fail closed;
4. evidence from a different artifact → selected source text is not attached;
5. same response retains exact World snapshot/revision IDs;
6. no graph mutation/write path is called;
7. historical service still fails closed when source is not adopted.

### §7C Required UI owning-boundary tests

Use a World adjacency fixture containing:

```text
sourceExcerpt: non-empty
sourceExcerptIsFullParagraph: true
sourceExcerptHighlightSpans: at least one span
```

Assert exact preservation through:

```text
adaptWorldGraphNodeView
→ GraphProjectionAdjacencyCandidate
→ buildGraphObjectCardFromNodeView
```

Do not merely test that `sourceExcerpt` renders; the regression under repair is field loss at the adapter boundary.

### §7D Live C2S25 witness

Against the assembled application and current durable authorities:

1. confirm exact repository head and service configuration;
2. confirm C2S25 source identity:

```text
source_artifact_id
  artifact:recap:longmont-c2:session-25:fd38b5915b32

source_revision_id
  8ed1e034-23c6-4295-b2ff-05d5cdd643a9

sha256
  fd38b5915b32beb77142c0334c578e7ff0d46ef6d91deb545801761508d26d0d
```

3. record actual World head used;
4. load C2 Session 25 in Ingest;
5. click Orik (`node:orik`);
6. identify a relationship/evidence path bound to the C2S25 source — preferably the known Orik/Brin / warehouse-sheltering context using digest-bound span `fd38b5915b32:23-23`;
7. verify the card receives the durable source excerpt/provenance;
8. verify browser Network shows **no additional source/World request caused solely by clicking Orik** after the recap projection has loaded;
9. verify World head is unchanged before/after;
10. record whether the resulting card is still visually/thinly presented — that is expected input to the next presentation slice, not a reason to expand this PR.

### §7E No-worktree-source witness

One owning-boundary witness must demonstrate the historical provenance result does not require the product source sidecar.

Preferred proof:

- disposable test/runtime with an empty `repo_root` / no `source_span_index.json`, while exact source bytes exist in APP-STATE.

Do not rename/delete live corpus files merely to make this proof.

---

## §8 Required review handback

Record:

1. `Review Cycle <N>` and exact PR/head SHA;
2. predecessor merge `df15db4c695240ce08b5812d43ca398cd70ff6ac` (#694) and implementation merge-base `c032f9473380a9121cac41b3f3d08ad46628672b`;
3. §1 invariant disposition;
4. actual changed paths vs §4;
5. whether bounded discovery was used and why;
6. field matrix: server World adjacency → UI World adjacency → shared node view → card relationship model;
7. exact C2S25 APP-STATE source identity/digest;
8. actual World head used by live witness;
9. exact source span/evidence used for Orik provenance;
10. proof that no checkout source-sidecar was required;
11. focused server/UI/build/ruff/diff evidence with provenance;
12. click-time network observation;
13. any warm-path timing observation;
14. confirmation that World head did not move;
15. confirmation that no durable state/schema was added;
16. prior finding ledger on re-review;
17. explicit still-false list from §9.

---

## §9 Acceptance rubric

- [ ] One capability only: historical graph-object relationship provenance can come from already-durable APP-STATE source bytes.
- [ ] C2S25 Orik witness uses exact APP-STATE source revision `8ed1e034-23c6-4295-b2ff-05d5cdd643a9` / digest `fd38…`.
- [ ] Matching admitted C2S25 evidence span resolves from `source.markdown` without `source_span_index.json`.
- [ ] Missing/mismatched source evidence never falls back to a checkout file on this historical path.
- [ ] World identity/evidence semantics remain DungeonMind-owned and read-only.
- [ ] Server provenance fields survive Buddy client adaptation without loss.
- [ ] No N+1 DB/source/World requests are introduced.
- [ ] Clicking an already-loaded historical object does not fetch provenance separately.
- [ ] No new durable state, migration, graph write, re-ingestion, or World-head advancement occurs.
- [ ] #694 predecessor sync lands backward-looking and truthfully.
- [ ] Stage 5B remains parked/conditional.
- [ ] Stage 2 / STOP 2 remain OPEN.
- [ ] Stage 4 remains NOT DONE.
- [ ] Bulk source adoption remains separate.
- [ ] Natural-language / fun styling remains separate.

### Explicitly still false after merge

```text
all C1/C2 recap sources DB-backed                   FALSE
C1S10 source adopted                               FALSE
all generic World source excerpts DB-backed        FALSE
Plan/Build generic World source joins migrated     FALSE
Orik primary card prose redesigned                 FALSE
raw graph taxonomy fully hidden from presentation  FALSE
Threat visual treatment restored                   FALSE
prior/next recap navigation                        FALSE
Agent-on-Ingest                                    FALSE
Stage 4 / STOP 4                                   FALSE
Stage 2 / STOP 2                                   OPEN
```

---

## §10 Mandatory post-merge human STOP

After merge, dogfood C2S25 again.

The human question is now deliberately about **data substrate**, not styling:

> When I click Orik, do I now have trustworthy, durable source context available to the card without relying on my checkout — even if the card still needs a presentation pass?

Then inspect 3–5 additional C2S25 objects/relationships and classify each missing useful fact as one of:

```text
A. present in DungeonMind + APP-STATE and projected correctly
B. present upstream but lost in Buddy adaptation
C. World evidence exists but source bytes are not yet durable in APP-STATE
D. genuinely absent from current authority
E. present and trustworthy; only presentation/styling is poor
```

That classification decides the next slice:

- many **C** → Stage 2C source-adoption coverage expansion;
- many **B** → another projection-fidelity slice;
- mostly **E** → begin deliberate Stage 4 presentation/natural-language styling;
- many **D** → stop and assess whether the original prototype depended on data that was never actually durable/authoritative.

Do not pre-author the styling handoff before this STOP.

---

## Stop conditions

Stop and report instead of expanding if:

- resolving the C2S25 excerpt requires a new APP-STATE schema/table;
- World evidence does not carry enough artifact/span identity to bind exact source bytes;
- the required source artifact/digest differs from the accepted C2S25 APP-STATE identity;
- the implementation needs to reconstruct or mutate graph truth;
- a second World projection/retrieval call is required per clicked object merely to obtain provenance;
- preserving the fields requires a new public wire schema rather than filling fields already present in the server contract;
- generic Plan/Build source migration becomes necessary to satisfy the historical invariant;
- bulk source adoption enters the PR;
- CSS/card prose redesign enters the PR;
- another active lane claims any §4 production path;
- a production path outside §4 + bounded discovery is required;
- source mismatch is repaired by filesystem fallback, fuzzy matching, or nearby-text inference.

Report:

```text
Stop condition:
Invariant clause affected:
Observed source/evidence identities:
Why current mission cannot absorb it:
Affected paths/authority layers:
Required new durable/public contract:
Proposed successor/rebrief:
State-authority update needed:
```
