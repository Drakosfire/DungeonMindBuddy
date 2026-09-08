---
pr_body_template: |
  ## Handoff pointer
  - Conversation/workstream: DOGFOOD-CONTINUITY / durable source coverage
  - Flow: DOGFOOD-CONTINUITY
  - Direction: DESIGN → CODE/OPERATE → REVIEW → MERGE → HUMAN DOGFOOD
  - Handoff: `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-stage-2c-broad-source-adoption-v1.md`
  - Branch / PR: `dogfood-continuity/stage-2c-broad-source-adoption-v1` / `DOGFOOD-CONTINUITY: adopt exact C1/C2 source material into durable APP-STATE`

  ## Verification pointer
  - Base: `d2c4248b14397525fd996309e230e513a3662bb1` (`main`; PR #695 merged)
  - Predecessor: #695 provenance substrate merged and human dogfood proved Orik correct; other objects still lacked source prose
  - Operator ruling: adopt every exact recoverable source we can prove; do not ration adoption
  - Verification: preview fingerprint → exact adoption → replay/noop → backup/clean restore → assembled C1/C2 dogfood

  The checked-in handoff, cumulative diff, independently rerun evidence,
  live adoption report, and post-adoption recovery proof are the review contract.
---

# HANDOFF — DOGFOOD-CONTINUITY: Stage 2C broad exact source adoption v1

**Created:** 2026-09-08  
**Status:** IMPLEMENTATION IN PROGRESS — one implementation capability
**Canonical handoff path:** `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-stage-2c-broad-source-adoption-v1.md`  
**Conversation/workstream:** `DOGFOOD-CONTINUITY / durable source coverage`  
**Flow / owner:** `DOGFOOD-CONTINUITY`  
**Direction:** DESIGN → CODE/OPERATE → REVIEW → MERGE → HUMAN DOGFOOD  
**Base revision:** `d2c4248b14397525fd996309e230e513a3662bb1` — `main` after merged PR #695  
**Implementation branch:** `dogfood-continuity/stage-2c-broad-source-adoption-v1`  
**PR title:** `DOGFOOD-CONTINUITY: adopt exact C1/C2 source material into durable APP-STATE`

> Repository law: [`AGENTS.md`](../../AGENTS.md). Product sequence: [`Docs/Roadmaps/ROADMAP-demo-ready-c1-c2-to-of-conks.md`](../Roadmaps/ROADMAP-demo-ready-c1-c2-to-of-conks.md). Current steward anchor: [`STEWARDS-ANCHOR-con-ready.md`](STEWARDS-ANCHOR-con-ready.md). Recovery ledger: [`../Operations/CAMPAIGN-MATERIAL-LIBRARY-c1-c2.md`](../Operations/CAMPAIGN-MATERIAL-LIBRARY-c1-c2.md).

---

## §0 Re-anchor and operator ruling

Exact repository truth at design time:

```text
main                            d2c4248b14397525fd996309e230e513a3662bb1
PR #695                         MERGED
accepted #695 head              fe55824e1927a29b03e7c2660ba653c86aaf4a82
formal #695 review cycles       3
Stage 5A                        MERGED + human dogfood PASS
Stage 5B                        PARKED / conditional
Stage 2 / STOP 2                OPEN
Stage 4 / STOP 4                NOT DONE
open PRs                        none
```

PR #695 proved the durable provenance seam end-to-end for C2 Session 25:

```text
DungeonMind World evidence identity
        +
APP-STATE exact source.revision bytes
        ↓
relationship provenance projection
        ↓
existing graph-object card model
```

The mandatory human STOP after #695 produced a clear result:

```text
Orik
  source prose/context correct
  provenance path correct
  remaining problem = presentation

other inspected objects
  old graph context present
  source prose absent
```

The operator then made the sequencing decision explicitly:

> **Adopt away.** Do not artificially ration exact source adoption.

Operationally that means:

> **If DungeonMind or the accepted historical Ingest ledger already gives us a source identity and expected digest, and we still possess exact matching bytes, adopt those bytes into durable APP-STATE. Missing material remains missing; conflicting material fails closed. Do not re-ingest, regenerate, infer, or rewrite source prose.**

This ruling supersedes the earlier hesitation around unknown historical Buddy `source_revision_id` values. A prior Buddy revision UUID is preserved when it is actually known. When no historical Buddy revision UUID is recoverable, this slice may create the **first durable APP-STATE adoption identity** for those exact bytes and must say so explicitly in lineage/reporting. That is adoption, not recovery of an old UUID.

### Durable authorities

```text
DungeonMind World authority     127.0.0.1:54330 / dungeonmind_cutover_live
Buddy APP-STATE                 127.0.0.1:54331 / dungeonbuddy_application_state
DungeonMind dev                 127.0.0.1:54329 / disposable tmpfs; test-only
```

World remains graph truth. APP-STATE owns durable Buddy source bytes. This slice does not write DungeonMind.

### Existing accepted source witness

C2S25 is already durable and must remain exact/no-op:

```text
source_artifact_id
  artifact:recap:longmont-c2:session-25:fd38b5915b32

source_revision_id
  8ed1e034-23c6-4295-b2ff-05d5cdd643a9

content SHA-256
  fd38b5915b32beb77142c0334c578e7ff0d46ef6d91deb545801761508d26d0d

World
  eldyrwild
```

Current World head at the preceding live witness:

```text
rev:680c246047d67f9fe0293ee90526f670
```

Do not assume it is unchanged at implementation time; observe and pin the actual head during preview/apply/live proof.

---

## §0A Backward-looking predecessor sync

The implementation PR must atomically record facts already true before Stage 2C begins:

```text
PR #695                         MERGED
authorized head                 fe55824e1927a29b03e7c2660ba653c86aaf4a82
merge                           d2c4248b14397525fd996309e230e513a3662bb1
review cycles                   3
#695 provenance capability      human dogfood PASS for Orik
human STOP finding              broader objects still lack source prose
operator decision               broad exact source adoption next
Stage 5B                        PARKED / conditional
Stage 2 / STOP 2                OPEN
Stage 4                         NOT DONE
```

Sync these mutable authorities inside the Stage 2C implementation PR:

```text
Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-db-backed-graph-object-provenance-v1.md
Docs/Roadmaps/ROADMAP-demo-ready-c1-c2-to-of-conks.md
Docs/Plans/STEWARDS-ANCHOR-con-ready.md
```

The sync may mark Stage 2C CURRENT. It must not pre-mark Stage 2C DONE, close Stage 2 / STOP 2, or start Stage 4 styling.

---

## §1 Mission and merge-ready invariant

### Mission

Adopt the broad set of **exact, already-identifiable C1/C2 source material** into durable Buddy APP-STATE so historical recap/object provenance no longer depends on a developer checkout wherever exact bytes are still available.

### Merge-ready invariant

> For the Longmont C1/C2 acceptance corpus, every source claim selected by the Stage 2C inventory that has (a) an existing authoritative source artifact identity and scope, (b) an authoritative expected content digest, and (c) exact available UTF-8 Markdown bytes hashing to that digest is persisted in APP-STATE `source.artifact` / immutable `source.revision`; replay is idempotent; unavailable or identity-incomplete material is reported without fabrication; any digest/scope/identity conflict blocks apply; the resulting APP-STATE can be independently backed up and restored with identical logical fingerprint and source revision identities; DungeonMind World remains read-only and at the same head before/after the operation.

This is one capability: **durable exact source coverage**.

### What this proves

```text
historical Ingest source claims ─┐
                                 ├─> deterministic source inventory
current World source/evidence ───┘
                                      ↓
                              exact-byte resolution
                                      ↓
                               APP-STATE source.*
                                      ↓
                         DB-backed historical provenance
                                      ↓
                       backup / clean-target restore
```

### Still false after merge unless separately proven

```text
all files in corpus are adopted                         FALSE
unidentified corpus files gain product identities       FALSE
non-Markdown source formats are archived                 FALSE
candidate_graph/source_span_index/review bundles durable FALSE
Stage 2 / STOP 2 automatically closed                    FALSE
Stage 4 styling complete                                 FALSE
Threat presentation restored                             FALSE
Agent-on-Ingest complete                                 FALSE
```

---

## §2 Target-set definition

The target set is intentionally broad but not fuzzy.

### §2A Source-claim families

Inventory the union of these source claims for **Longmont C1/C2 / Eldyrwild**:

1. **Historical Ingest claims** — the exact `source_artifact` component recorded by the 53 durable `ingest.run` rows restored in Stage 2B.
2. **Current World-referenced claims** — source artifacts/evidence referenced by the current DungeonMind Eldyrwild World projection/head, including worldbuilding/manual source material when an authoritative revision/digest can be established through existing read-only DungeonMind repository data.
3. **Already-durable APP-STATE sources** — included for classification/replay (`CURRENT_EXACT`), not duplicated.

Do not use Of Conks and Cons as target corpus. It remains design evidence only.

### §2B Eligibility contract

A candidate is **ADOPTABLE_EXACT** only when all are known:

```text
source_artifact_id
source_domain
campaign/world/session scope as applicable
expected SHA-256 digest
exact bytes locator
exact bytes SHA-256 == expected digest
bytes decode as UTF-8 Markdown
```

The expected digest must come from an existing accepted source claim:

- an `ingest.run` source-artifact component digest; or
- an authoritative DungeonMind source-revision digest reachable through the already-mounted read-only source repository.

The recovery library may help locate bytes. It is **not** sufficient authority to invent an artifact identity or expected digest by itself.

### §2C Deduplication

The durable revision target key is:

```text
(source_artifact_id, content_sha256)
```

Multiple historical runs may point at the same target. Collapse them to one adoption candidate and retain the sorted supporting run IDs/authority refs in the preview/report.

If one artifact ID legitimately has multiple exact historical digests, treat each digest as a separate immutable source revision under the same artifact, provided scope is consistent.

### §2D Domain/media boundary

This slice adopts exact **UTF-8 Markdown source material** only.

Examples that may qualify when authoritative identity/digest exists:

```text
recap
worldbuilding
manual_seed
session_memory
other textual source domains already represented as Markdown
```

Do not silently coerce JSON, images, PDFs, statblocks, or binary artifacts into Markdown. Classify them `UNSUPPORTED_MEDIA` and report them.

---

## §3 Inventory classifications

Every discovered claim must receive exactly one disposition before apply.

```text
CURRENT_EXACT
  exact artifact+digest already exists in APP-STATE; noop

ADOPTABLE_EXACT
  authoritative identity/digest + matching exact bytes; write on apply

UNAVAILABLE_BYTES
  identity/digest known, but exact bytes cannot be found; skip and report

AUTHORITY_METADATA_INCOMPLETE
  source is referenced, but authoritative digest/scope needed for safe adoption
  cannot be established through existing read-only seams; skip and report

UNSUPPORTED_MEDIA
  authoritative source exists but is not UTF-8 Markdown; skip and report

DIGEST_MISMATCH
  located bytes do not hash to the authoritative expected digest; BLOCK apply

SCOPE_CONFLICT
  same artifact identity disagrees on source_domain/campaign/session/world scope;
  BLOCK apply

REVISION_ID_CONFLICT
  a known/requested Buddy source_revision_id is already bound to different state;
  BLOCK apply

APP_STATE_CONFLICT
  same artifact/digest exists with different bytes/scope; BLOCK apply
```

### Missing vs conflicting

This slice must **not** let old missing material prevent adoption of everything else.

Therefore:

- `UNAVAILABLE_BYTES`, `AUTHORITY_METADATA_INCOMPLETE`, and `UNSUPPORTED_MEDIA` are non-blocking skips.
- any digest/scope/revision/APP-STATE conflict blocks the entire apply until understood.

That is the accepted safety posture for “adopt away.”

---

## §4 Preview / apply operator contract

Build a first-class bulk source-adoption operator rather than shelling the one-run CLI repeatedly.

### Required flow

```text
PREVIEW (default)
  read current 53-run APP-STATE catalog
  read current DungeonMind World/source claims (read-only)
  locate exact surviving bytes
  hash bytes
  classify every claim
  deduplicate durable targets
  print counts + blocking findings + skipped findings
  emit source_target_set_sha256
  emit World head used for inventory
  zero writes

APPLY
  require --apply
  require --expected-set-sha256 <preview value>
  require expected World head / revalidate World head
  rerun inventory immediately before writes
  reject target-set drift
  reject blocking findings
  persist all ADOPTABLE_EXACT candidates
  leave CURRENT_EXACT no-op
  report actual source_revision_id for every durable target

REPLAY
  same inventory
  all previously adopted targets => CURRENT_EXACT / noop
  source_target_set_sha256 stable when external authority/locators unchanged
```

### Suggested CLI

Prefer a dedicated operator, for example:

```bash
python scripts/adopt_historical_source_material.py \
  --world-id eldyrwild \
  --campaign longmont-c1 \
  --campaign longmont-c2

python scripts/adopt_historical_source_material.py \
  --world-id eldyrwild \
  --campaign longmont-c1 \
  --campaign longmont-c2 \
  --apply \
  --expected-set-sha256 <sha>
```

Exact flag names are implementation-detail latitude; the behavioral handshake is not.

### Fingerprint contents

`source_target_set_sha256` must be deterministic and independent of enumeration order. At minimum hash sorted canonical records containing:

```text
source_artifact_id
expected content_sha256
source_domain
campaign_id
session_id
world_id
authority claim kind
resolved locator identity (repo-relative / authority URI; no home path)
classification
known historical Buddy source_revision_id when one truly exists
```

Do **not** include a newly generated source revision UUID in the preview fingerprint.

---

## §5 Source revision identity policy

This section is the operator decision that previously blocked Stage 2C.

### Known historical Buddy revision ID

If a prior Buddy `source_revision_id` is actually known and verified, preserve it as an exact assertion using the accepted `persist_source_markdown(..., source_revision_id=...)` seam.

C2S25 is the canonical witness and must remain:

```text
8ed1e034-23c6-4295-b2ff-05d5cdd643a9
```

### Unknown historical Buddy revision ID

If no prior Buddy revision UUID is recoverable:

- do **not** invent that one existed;
- do **not** block adoption merely because the old UUID is unknown;
- create the first durable APP-STATE source revision through the normal insert path;
- classify/report identity provenance as `NEW_DURABLE_ADOPTION_IDENTITY`;
- record lineage that distinguishes this from historical UUID recovery.

Suggested lineage shape:

```json
{
  "adoption_kind": "new_durable_source_adoption",
  "adopted_from_run_ids": ["..."],
  "adopted_from_authority_refs": ["..."],
  "adopted_from_uri": "repo://...",
  "historical_buddy_revision_id_recovered": false
}
```

For a known recovered UUID, record that fact truthfully instead.

### Recovery meaning after adoption

New adoption UUIDs do not need to be deterministically regenerated from artifact+digest. Once adopted, the live APP-STATE backup/fingerprint contract becomes their recovery authority.

Therefore the Stage 2C recovery proof is **backup → clean restore with identical revision IDs**, not “destroy and rerun the importer to manufacture the same UUID.”

---

## §6 Source resolution rules

### Historical Ingest claims

Reuse the accepted exact-run/component machinery. For each durable `ingest.run` source component:

```text
run.source_artifact_id
component.uri
component.sha256
run.source_domain
run.campaign_id
run.session_id
```

Resolve only repository-contained/accepted locators. Hash raw bytes before decode. The current one-run source adoption service is implementation evidence; do not regress its containment/digest checks.

### World-referenced claims

Use DungeonMind only through its mounted read-only repository/contracts.

The implementation may consume source artifact/revision metadata already available from the pinned DungeonMind source repositories. It must not add a graph write or advance the World head.

If a World source artifact can be identified but the pinned read seam does not expose enough authoritative revision/digest data for safe adoption, classify `AUTHORITY_METADATA_INCOMPLETE`. Do not guess from file contents.

### Locator precedence

A safe source locator may come from:

1. exact historical run component URI;
2. exact authoritative World source URI/revision metadata;
3. the recovery library as a locator aid when it agrees with the authoritative artifact/digest claim.

Never select “latest file,” nearest filename, title similarity, timestamp proximity, or neighboring session prose.

### Multiple exact locators

If multiple files independently hash to the same expected digest, they are equivalent byte sources. Record the selected stable repo-relative locator and optionally the alternate count; do not treat identical bytes as conflict.

---

## §7 Runtime and authority boundaries

### No graph mutation

Forbidden:

```text
DungeonMind writes
World revision/head advancement
contribution replay
re-ingestion/re-extraction
candidate graph reconstruction
promoting validated/prepared runs
```

Observe the actual World head before preview/apply and after live product proof. It must not move because of Stage 2C.

### No runtime filesystem fallback after adoption

The adoption operator is allowed to read the surviving checkout/corpus **once as an operator boundary**.

Normal product historical reading/provenance after adoption must continue to use APP-STATE source bytes. Do not introduce a new runtime fallback to corpus files.

### No lifecycle mutation

Adopting source bytes must not change:

```text
ingest.run identity
validated/prepared/reviewable status
campaign/session identity
World object/evidence identity
```

---

## §8 Files in scope — write lease

Expected implementation paths:

| Action | Path | Purpose |
|---|---|---|
| Create | `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-stage-2c-broad-source-adoption-v1.md` | lane authority |
| Create | `src/product_continuity/source_adoption.py` | deterministic inventory/classification/fingerprint/apply orchestration |
| Create | `scripts/adopt_historical_source_material.py` | explicit preview/apply operator |
| Create | `tests/product_continuity/test_source_adoption_postgres.py` | owning PostgreSQL inventory/apply/replay/conflict tests |
| Modify | `apps/live_control_server/services/historical_recap_source_adoption.py` | reuse shared exact resolution/adoption primitives if needed; preserve one-run CLI behavior |
| Modify | `tests/test_historical_recap_source_adoption.py` | ensure single-run operator remains exact/backward-compatible |
| Modify | `apps/live_control_server/integrations/dungeonmind/world_graph_reads.py` | **only if needed** to expose a bounded read-only World source inventory helper from already-authoritative repository data |
| Modify | `tests/test_historical_recap_world_projection.py` | only if broader source coverage changes an owning historical projection expectation |
| Create | `Docs/Reports/REPORT-stage-2c-broad-source-adoption.md` | actual live coverage/adoption/replay/recovery evidence |
| Modify | `Docs/Operations/CAMPAIGN-MATERIAL-LIBRARY-c1-c2.md` | record observed post-apply durable source coverage while preserving historical loss record |
| Modify | `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-db-backed-graph-object-provenance-v1.md` | backward sync #695 merge + human STOP |
| Modify | `Docs/Roadmaps/ROADMAP-demo-ready-c1-c2-to-of-conks.md` | backward sync #695 + mark Stage 2C current, not done |
| Modify | `Docs/Plans/STEWARDS-ANCHOR-con-ready.md` | re-anchor to #695 merge + Stage 2C current |

### Bounded discovery

One additional production helper path under either of these areas may be added only if required to avoid duplicating an existing accepted resolver or APP-STATE repository primitive:

```text
src/product_continuity/
src/application_state/source/
apps/live_control_server/integrations/dungeonmind/
```

Maximum additional production paths: **1**.

Any schema migration, new public HTTP endpoint, or second durable data model is a STOP/rebrief signal.

---

## §9 Explicitly out of scope

Do not absorb:

- new APP-STATE tables/migrations;
- arbitrary binary/file archival;
- candidate graph, provenance index, validation report, or source-span-index durability;
- re-ingestion/re-extraction;
- reconstruction of missing source files;
- normalization/rewriting of historical prose;
- new artifact IDs for corpus files that lack an accepted identity claim;
- Build orphan adoption;
- Plan/Runbook/Play material work;
- Stage 4 card/hover styling;
- natural-language relationship composition;
- Threat/statblock presentation;
- prior/next session navigation;
- Agent-on-Ingest;
- Stage 5B shell work;
- authority auto-start;
- VPC/object-store migration.

If broad source adoption reveals one of these as the next blocker, record it; do not fix it here.

---

## §10 Required automated evidence

At minimum:

### Source adoption unit/integration

Prove on disposable PostgreSQL:

1. multiple runs pointing to same artifact+digest dedupe to one target;
2. one artifact with two exact digests produces two immutable revisions when scope agrees;
3. exact bytes/digest => `ADOPTABLE_EXACT` preview and successful apply;
4. replay => `CURRENT_EXACT`, zero additional source revisions;
5. missing bytes => `UNAVAILABLE_BYTES`, non-blocking;
6. incomplete World revision metadata => `AUTHORITY_METADATA_INCOMPLETE`, non-blocking;
7. unsupported media => `UNSUPPORTED_MEDIA`, non-blocking;
8. digest mismatch => apply blocked before source writes;
9. source scope conflict => apply blocked;
10. APP-STATE artifact/digest conflict => apply blocked;
11. expected target-set fingerprint mismatch => apply blocked;
12. known `source_revision_id` exact assertion preserves UUID;
13. unknown prior UUID creates one new durable adoption identity and replay preserves it;
14. C2S25 existing source remains exact/no-op;
15. ingest lifecycle/status rows are byte-for-byte/logically unchanged by source adoption;
16. World read helper, if added, performs no writes.

### Existing source seam regression

Keep the accepted one-run source-adoption tests green.

### APP-STATE recovery

The existing application-state fingerprint must include the newly adopted source rows. If it already does, do not alter fingerprint semantics merely for ceremony.

### Quality gates

```bash
uv run pytest -q \
  tests/product_continuity/test_source_adoption_postgres.py \
  tests/test_historical_recap_source_adoption.py \
  tests/application_state/test_source_content_postgres.py \
  tests/test_historical_recap_world_projection.py

uv run ruff check <changed Python paths>
git diff --check
git diff --name-only d2c4248b14397525fd996309e230e513a3662bb1...HEAD
```

Add only directly owning tests required by bounded discovery.

---

## §11 Live operator evidence required before merge

Run against the durable authorities with a pre-write backup already captured.

### §11A Preview

Record:

```text
main/head SHA
APP-STATE schema/head
World head
53 ingest.run count + status mix
unique source claims discovered
unique artifact+digest targets
CURRENT_EXACT count
ADOPTABLE_EXACT count
UNAVAILABLE_BYTES count
AUTHORITY_METADATA_INCOMPLETE count
UNSUPPORTED_MEDIA count
blocking conflict count
source_target_set_sha256
```

The report must include counts by source domain and campaign, plus a machine/human-readable list of every skipped or blocked item without leaking home-directory paths.

### §11B Pre-write safety

Before apply:

- capture APP-STATE fingerprint;
- capture an external APP-STATE backup;
- record backup SHA-256;
- record World head;
- do **not** destroy the live volume.

### §11C Apply

Apply only with the exact preview fingerprint and revalidated World head.

Record:

```text
newly adopted revisions
CURRENT_EXACT/noop revisions
actual generated source_revision_id values
known historical IDs preserved
skipped unavailable/incomplete items
zero conflicts
```

### §11D Replay

Immediately rerun the same operation.

Expected:

```text
new writes                      0
all durable targets             CURRENT_EXACT / noop
source revision count           unchanged
source_target_set_sha256        unchanged
```

### §11E Product witness

Use the assembled application, not only DB queries.

At minimum load:

```text
C2 Session 25  — regression witness; Orik provenance still correct
C1 Session 10  — previously catalog-only source
C2 Session 23  — previously catalog-only source
one additional C1 session
one additional C2 session
```

For each available exact source, prove historical prose comes from APP-STATE after adoption.

Then inspect several graph objects/relationships whose evidence points at different adopted sources. We are looking for source prose to appear beyond the single Orik witness.

Do not require pretty cards. This is source coverage proof.

### §11F No-checkout runtime witness

For representative adopted sessions, prove the historical source read/provenance path works when the original source locator is unavailable to the runtime process (disposable/empty repo root or equivalent safe test setup).

Do not rename/delete live corpus files.

### §11G World immutability

Record actual World head before preview, before apply, after apply, and after product dogfood. Stage 2C must not move it.

---

## §12 Recovery proof required before merge

This slice expands durable authority materially, so prove recovery again.

After apply/replay:

1. capture post-adoption APP-STATE fingerprint;
2. create an independently verified external PostgreSQL backup;
3. restore that backup into a **clean second target database**;
4. run the application-state verifier against the clean target;
5. require exact logical fingerprint parity;
6. verify representative newly-created source revision UUIDs/digests exist identically on the clean target;
7. verify C2S25 retains its known UUID exactly;
8. drop only the disposable witness target after proof.

Do not `down -v` the live 54331 authority merely to prove this slice.

Standing persistence standard remains:

> Persistence is proven by recognizable product state plus independently verified backup/restore of the identical logical objects, not by the presence of a Docker volume.

---

## §13 Coverage report contract

Create `Docs/Reports/REPORT-stage-2c-broad-source-adoption.md` from actual evidence.

Required sections:

```text
exact repo/head + authority coordinates
operator ruling
preview inventory counts
source_target_set_sha256
classification counts by campaign/domain
adopted target table (artifact, digest, revision ID, identity kind)
skipped target table + reason
blocked conflicts (must be zero at accepted apply)
replay/noop evidence
APP-STATE fingerprint before/after
backup SHA-256
clean-target restored fingerprint
World head before/after
assembled product witnesses
no-checkout witness
explicit still-missing material
```

Do not dump campaign prose into the report. Identity/digest/locator metadata is sufficient.

Update `CAMPAIGN-MATERIAL-LIBRARY-c1-c2.md` only with facts actually observed after apply. Preserve the 2026-09-07 loss event and historical survey context.

---

## §14 Review handback

Record for every formal review cycle:

1. `Review Cycle <N>` and exact head SHA;
2. exact implementation base `d2c4248b14397525fd996309e230e513a3662bb1`;
3. §1 invariant disposition;
4. actual changed paths vs §8;
5. bounded discovery, if any;
6. inventory source families actually used;
7. classification counts;
8. source_target_set_sha256;
9. blocking conflicts and resolution;
10. known historical UUIDs preserved;
11. count of `NEW_DURABLE_ADOPTION_IDENTITY` revisions;
12. exact automated evidence;
13. live apply/replay evidence;
14. pre/post APP-STATE fingerprints;
15. backup SHA + clean restore fingerprint;
16. actual World head before/after;
17. assembled C1/C2 product witnesses;
18. no-checkout proof;
19. prior finding ledger;
20. explicit still-false list.

---

## §15 Acceptance rubric

- [ ] One capability only: broad exact source adoption into durable APP-STATE.
- [ ] #695 merge + human STOP are backward-synced truthfully.
- [ ] Target inventory includes all 53 durable historical run source claims.
- [ ] Target inventory attempts current World-referenced textual sources without inventing missing authority metadata.
- [ ] Every `ADOPTABLE_EXACT` candidate is digest-verified before write.
- [ ] Missing/incomplete source material is skipped and explicitly reported.
- [ ] Any digest/scope/revision conflict blocks apply.
- [ ] Apply requires the exact preview target-set fingerprint.
- [ ] Known historical source revision IDs are preserved exactly.
- [ ] Unknown historical Buddy revision IDs do not block adoption; new IDs are labeled as new durable adoption identities.
- [ ] Replay produces zero new writes.
- [ ] No ingest lifecycle/status changes.
- [ ] No graph writes/re-ingestion/World-head movement.
- [ ] Representative C1/C2 historical source prose is served from APP-STATE.
- [ ] Source-backed graph-object provenance appears beyond the single Orik witness where evidence points at adopted sources.
- [ ] Runtime proof does not require original checkout source files.
- [ ] Post-adoption backup restores to identical logical fingerprint and source revision identities.
- [ ] Stage 2 / STOP 2 remain OPEN until the post-merge human STOP accepts them.
- [ ] Stage 4 remains NOT DONE.

---

## §16 Mandatory post-merge human STOP

After merge, dogfood the assembled product again before dispatching Stage 4.

This STOP asks whether source coverage is now broad enough that presentation is truly the dominant remaining problem.

### Concrete human pass

Open at least:

```text
C1 Session 10
C1 one additional rich session
C2 Session 23
C2 Session 25
C2 one additional rich session
```

Click 5–10 mixed graph objects/relationships:

```text
NPC
location
party/faction
campaign-lived high-degree NPC if available
one intentionally thin/session-local object
```

Classify failures:

```text
A — exact source/context present and projected correctly
B — source is durable but Buddy still loses it in projection
C — evidence exists but exact source remained unavailable/incomplete in Stage 2C
D — useful context genuinely does not exist in current authorities
E — data is present/trustworthy; remaining problem is presentation/styling
```

Decision rule:

```text
mostly A/E
  → green light Stage 4 deliberate readable/fun presentation

meaningful B
  → another narrow projection-fidelity repair first

meaningful C
  → inspect skipped Stage 2C coverage; acquire/adopt exact bytes if possible

meaningful D
  → investigate whether old prototype richness depended on non-authoritative/inferred data
```

The operator has already accepted broad adoption. Do not create another artificial “adopt only five more sources” gate after this PR.

### Stage 2 closure decision

The human may close Stage 2 / STOP 2 only if the post-merge coverage/recovery evidence is satisfactory. The implementation PR itself must not pre-close it.

---

## Stop conditions

Stop and report rather than expanding if:

- safe adoption requires a new APP-STATE schema/table;
- World source adoption requires a new DungeonMind public write or schema contract;
- exact expected digest cannot be established for a candidate;
- candidate bytes mismatch the accepted digest;
- one artifact identity carries contradictory scope;
- resolving a source requires fuzzy title/path/session inference;
- material must be regenerated/re-ingested to continue;
- the operator would need to mutate validated/prepared/reviewable lifecycle state;
- non-Markdown archival becomes necessary to satisfy the mission;
- generic binary artifact storage enters the slice;
- an active lane claims a leased production path;
- a production path outside §8 + bounded discovery is required.

Report:

```text
Stop condition:
Candidate/source identity:
Expected digest / observed digest:
Authority claim:
Available locator(s):
Why exact adoption cannot proceed:
Why current mission cannot absorb the required contract:
Proposed successor/rebrief:
State-authority update needed:
```
