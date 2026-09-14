# ARCHIVE — DOGFOOD-CONTINUITY Stage 4H / Stage 4I ingestion notebooks

**Archived:** 2026-09-14  
**Historical PRs:** #710, #711  
**Disposition:** experimental evidence only; both notebooks are intentionally unmerged.  
**Successor:** `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-stage4l-c1-s1-s10-chronological-graph-rehearsal-v1.md`

This report preserves the parts of PRs #710 and #711 that should influence future ingestion work after those disposable notebook branches are closed. It is not executable authority and does not make their accumulated code production policy.

## What graduates as evidence

### 1. Cheap extraction is good enough to move the bottleneck downstream

Stage 4H showed that a stronger Sol baseline consistently found the important campaign material, but many apparent misses were actually **subject attachment / identity** problems rather than absent knowledge. Examples included Karsemine's discovery being represented on the creature and Mireward pressure being represented on a sibling Mireward identity.

Stage 4I.2 then showed that `deepseek/deepseek-v4.1-flash` with reasoning disabled can recover similarly useful campaign memory at much lower cost. Human inspection found specific, GM-usable material for Brin, Karsemine, Hesta, Thrin, Mireward, and creature mechanics. The dominant weakness was object hygiene: duplicate/sibling identities, document-shaped entities, historical/current flattening, and too much unranked detail.

**Inherited decision:** Do not spend the next experiment on a larger model or more reasoning. Use DeepSeek V4.1 Flash with reasoning disabled and spend experimental attention on context, identity continuity, publication, and graph shape.

### 2. Semantic context direction is settled for this phase

The controlled paragraph-vs-whole-document work selected:

> **Reason globally, cite locally.**

The extractor may receive the whole authored document as semantic context, while every persisted assertion must still resolve to granular source spans/evidence.

Do not return to paragraph-only semantic context unless new evidence falsifies this decision.

### 3. The known working DeepSeek transport is explicit

The useful transport contract discovered on #711 is:

```text
model: deepseek/deepseek-v4.1-flash
provider: official DeepSeek through OpenRouter
provider fallback: disabled
reasoning: disabled / none
transport: Chat Completions
response_format: json_object
schema: included in system instructions
validation: mandatory local schema/Pydantic validation
retry: bounded same-request resend on malformed/empty/schema-invalid output
retry cap used in experiments: 5
```

A resend is transport repair, not semantic repair: same prompt, same request semantics, no evaluator model, no rewritten content.

The provider/model/endpoint actually serving each paid request must be recorded. API keys must never be printed, committed, hashed, or written to receipts.

### 4. Candidate artifacts are durable; inference is not a provenance repair mechanism

Later C2 dogfood posted to #711 reinforced a key architectural rule already suggested by #710/#711:

> **Model output is a durable candidate artifact. Provenance, admission, identity reconciliation, and publication may be replayed without calling the model again.**

If source authority or publication metadata is wrong, repair the deterministic layer and replay the saved candidate. Do not rerun inference merely to fix evidence admission.

### 5. Source authority must be correct before publication

#710 exposed unsafe authority projection when planning material was normalized into world/seed authority and became CANON despite prose saying otherwise. Later C2 rehearsal showed the inverse failure: extracted recap objects existed but ordinary campaign projection excluded them because the recap source authority had not been admitted correctly.

**Inherited rule:** source bytes, source artifact identity, digest, campaign/session scope, and source domain must be admitted/provable before candidate assertions become ordinary World memory. No compatibility transform may silently elevate planning prose into played/canon truth.

### 6. Identity continuity is now a first-class experimental variable

Observed fragmentation included:

```text
Orik / Orric
Mireward / Mireward Reach
Karsemine / Karsemin / Kasemine
Baergrom / Baergorm
Lysandra / Lysandro
named location / generic location
creature singular / plural / descriptive variants
```

Independent entity recall can look perfect while one fictional thing becomes several durable nodes.

The repository already has deterministic standing-context machinery:

- campaign party registries;
- canonical corpus refs for PCs/companions;
- known-entity registries and alias surfaces;
- conversion of an existing World head into canonical known-entity context;
- `extra_known_entities` on category extraction.

**Inherited direction:** prefer canonical identity context and deterministic reconciliation before buying model sophistication.

### 7. Missing seed context can create false model failures

The C2 Session 3 dogfood brief on #711 found that early sessions were extracted with an empty PC seed because the Campaign 2 party registry began at Session 20. The actor pass explicitly assumed PCs were supplied as anchors, so several PCs never became candidate nodes at all.

This is a context failure, not an extraction-comprehension failure.

For future chronological corpus experiments:

- stable campaign PCs are deterministic identity anchors;
- a prior admitted rehearsal World head supplies already-known recurring identities;
- future-session World knowledge must not be leaked backward into earlier extraction;
- seeded identity does **not** by itself prove session participation.

### 8. PC identity is deterministic authority

Current generic mapping can turn `character` into `npc`, even when the standing anchor is a campaign PC. A model should not decide whether a rostered campaign PC is a PC.

**Inherited rule:** roster/corpus identity determines PC-vs-NPC kind. Extraction may add observations, actions, facts, and relationships to that identity; it must not demote a known PC to NPC or mint a duplicate character to represent the same person.

### 9. Edge extraction and edge publication are separate scores

C2 candidate graphs contained many relationship edges, while publication dropped them because predicates/endpoints were not admitted by the DungeonMind write contract. A node-only fallback made the World look more complete than it was.

**Inherited rule:** always report separately:

```text
edges extracted
edges attached to canonical endpoints
edges with admitted predicates
edges publishable
edges published
```

`non_edge_fallback` is evidence of a publication gap, not successful graph ingestion.

### 10. Quality is not a scalar count

#710/#711 repeatedly showed that entity/fact counts cannot distinguish useful memory from fragmentation or trivia. Future experiment review should prioritize:

```text
identity coherence
continuity-critical completeness
source-grounded specificity
correct authority
correct temporal shape
GM usefulness / salience
novel-entity preservation
noise / document-structure leakage
cross-entity composition potential
```

The forcing question remains practical: would a GM trust the resulting object/graph enough to plan or run without reopening the source recap?

### 11. Cost telemetry must distinguish source size from request amplification

Whole-document context can multiply API input because the same document is retransmitted across extraction passes. Old file-count projections were misleading, especially when one scaffold generated most evidence units and cost.

Record at minimum:

```text
unique source bytes / tokens
request count
context retransmission / amplification
input / cached / output tokens
per-request latency
per-session wall time
retry count
actual cost
```

Do not call aggregate concurrent pipeline throughput single-request model decode speed.

## What does NOT graduate

The following remain historical notebook implementation/details and should not be copied forward by inertia:

- the Sol/Flex three-repetition baseline runner itself;
- the Luna/Terra/Sol model matrix;
- the full reasoning-effort ablation matrix;
- the old 84-request comparison topology as a production requirement;
- legacy-frontmatter authority coercions used only to measure frozen sources;
- file-count-only corpus cost projections;
- raw notebook stores as production truth;
- experiment-specific ranking/salience categories as durable schema;
- stale PR-body claims superseded by later receipts/comments.

Useful code concepts must be deliberately reimplemented or narrowly transplanted under the successor handoff's write lease. Closing an experiment PR is not a merge mechanism.

## Durable evidence locators

### PR #710 — Stage 4H Sol baseline

- paid execution head: `6a61b63dca555d3d70cac3e38eb3e48c6fc690da`
- executive record: PR #710 comment `5649023090`
- deterministic salvage: PR #710 comment `5650056954`
- final notebook head: `e4cbe4e47399947296159248ee7706cb0d932b3a`

Key observed baseline:

```text
entity recall: 1.0 / 1.0 / 1.0
fact recall:   0.6 / 0.6 / 0.6
mean run cost: about $2.75
identity fragmentation: material
major false-miss mechanism: subject / sibling identity attachment
```

### PR #711 — Stage 4I / 4I.2 context + DeepSeek screen

- final reviewable notebook head: `43f69e7888a642c3875d942e0e07277c2a599a99`
- 16-arm report: PR #711 comment `5654862343`
- formal Review Cycle 2: `5191677852`
- C2 dogfood + extraction-context brief: PR #711 comment `5664936622`

Key selected profile for the next experiment:

```text
model: deepseek/deepseek-v4.1-flash
reasoning: disabled
semantic context: whole document
citation/evidence: local source spans
provider: DeepSeek via OpenRouter, fallback disabled
transport: json_object + mandatory local validation
retry: bounded same-request transport resend
```

## Archive disposition

PRs #710 and #711 are historical evidence stores, not implementation ancestors. The next experiment starts from current `main`, consumes only the decisions recorded here, and may read those branches/PRs for provenance. It must not merge either notebook or depend on their branch ancestry.
