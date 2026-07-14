# PR006C — Initial Eldyrwild C2 Contribution Bundle

**Date:** 2026-07-11  
**Slice:** PR006C — Approved Initial World Supergraph Contribution Bundle  
**Predecessor:** PR006B / GitHub #334 (merge `b234988056abebb5b2a033cf236548a7c8c472f5`)

---

## Product framing

PR006C approves a **deterministic bootstrap package for `/ingest`**, not a bypass of `/ingest` review and not a production World Supergraph publication.

```text
Sources / GM knowledge
  ↓
PR006C checked-in bundle (this PR)
  ↓
/ingest
  load → validate → inspect/edit → approve
  ↓
Kernel GraphContribution merge
  ↓
PR006D publishes the initial immutable Eldyrwild world head
  ↓
/plan queries the published graph; controlled writes re-enter the same path
```

Merging this PR records review approval of the bootstrap **input**. It does not create or expose a campaign graph head.

---

## Authority model (Option B)

Two legitimate contribution kinds are present and kept distinct:

| Records | Kind | Provenance |
| --- | --- | --- |
| `001`, `002`, `004`, `005` | `manual_import` curated from sources | Each contribution is anchored to **exactly one** corpus artifact + revision (`repo://corpus/...` + `sha256:` pin). Mirathorn and Mireward are separate contributions so a Mireward-only corpus change supersedes only the Mireward contribution. Validation does **not** re-read the corpus; it requires internal agreement between contribution revision, assertion revision, and embedded `content_sha256`. |
| `003`, `006` | `graph_review_authored_assertion` (`authored_by: gm`) | Self-contained authored records. Evidence may cite the contribution JSON via `graph-data://...`. |

The hybrid of “claims recap/worldbuilding support while citing only the contribution JSON” is rejected.

---

## Bundle identity

| Field | Value |
| --- | --- |
| Bundle ID | `eldyrwild-longmont-c2-initial-v1` |
| Bundle digest | `5f8288d3052a9e59192884f2c35a13d51f665095d84cca2081a56638108d3fa5` |
| World ID | `eldyrwild` |
| Campaign scope | `longmont-c2` |
| Planning focus | `mireward-planning-window` |
| Focus sessions | `session-22`, `session-23` |
| Bundle path | `graph_data/approved_contribution_bundles/eldyrwild-longmont-c2-initial-v1/` |

### Ordered contribution IDs

1. `contribution:82f23934d8eaca8a` — `001-mirathorn-world-hub.json`
2. `contribution:43782369bd717d32` — `002-mireward-world-hub.json`
3. `contribution:33d7cdb0ff623f28` — `003-questionable-company-roster.json`
4. `contribution:c086a0b72324ff16` — `004-session-22-mireward-road.json`
5. `contribution:1227841724520c18` — `005-session-23-mireward-gate-battle.json`
6. `contribution:022187fdefdf4557` — `006-tripod-null-calf-threat-prep.json`

### Source artifact IDs

Corpus-backed:

- `corpus:eldyrwild:mirathorn-city`
- `corpus:eldyrwild:mireward-readme`
- `corpus:eldyrwild:session-22-recap`
- `corpus:eldyrwild:session-23-recap`

Authored:

- `graph-native:eldyrwild-c2-initial-v1:003-questionable-company-roster`
- `graph-native:eldyrwild-c2-initial-v1:006-tripod-null-calf-threat-prep`

---

## Semantic contents

| Measure | Count |
| --- | --- |
| Unique bundle-owned nodes | 12 |
| Unique bundle-owned edges | 11 |
| Accepted assertions | 30 (`node` 16, `edge` 11, `attribute` 3) |
| Rejected assertions | 0 |
| Unresolved mentions | 0 |
| Identity decisions | 0 |
| Source domains | `worldbuilding`, `manual_seed`, `recap`, `statblock` |

### Shared-support assertions (PR006B contract)

| Node | Semantic assertion ID | Active contributions | Domains |
| --- | --- | --- | --- |
| `location:mireward` | `assertion:3e2a37249f847f60` | mireward world hub + session 22 + session 23 | `worldbuilding`, `recap` |
| `party:questionable-company` | `assertion:e43e22317e459bac` | roster + session 22 + session 23 | `manual_seed`, `recap` |

Mireward existence assertions use `campaign_scope = null` and `temporal_scope = null`.  
Questionable Company existence assertions use `campaign_scope = longmont-c2` and `temporal_scope = null`.

---

## Governance

```text
identity decisions: 0
unresolved mentions: 0
rejected assertions: 0
approval basis: merge of PR006C (bootstrap package for /ingest)
```

PR006D must pin:

- the actual PR006C merge SHA; and
- this bundle digest

then exercise the same path the GM will use: load into `/ingest` → validate → inspect/approve → merge → publish.

---

## Evidence coverage

| Measure | Result |
| --- | --- |
| Accepted assertions with matching top-level + embedded evidence refs | 100% (30/30) |
| Accepted assertions with resolvable embedded source artifacts | 100% (30/30) |
| Recap assertions with session locator | 100% |
| Non-recap assertions with source locator | 100% |

“Resolvable” means IDs match and embedded artifacts carry inspectable URIs — not merely that some field is non-empty. Recap `source_span_ref_id` values are stable labels suitable for `/ingest` inspection; this package does **not** prove that those labels resolve to highlightable spans until the `/ingest` source resolver exercises them.

---

## Provenance coherence

For each accepted `manual_import` assertion, validation requires:

- contribution / assertion / embedded artifact share one `source_artifact_id`;
- contribution / assertion revision equal `sha256:` + embedded `content_sha256`;
- evidence domain equals artifact domain equals the assertion provenance domain;
- corpus URIs use `repo://corpus/`.

For authored records, validation requires `graph_review_authored_assertion`, a non-empty `authored_by`, and `graph-data://` self-citation.

### Campaign / session coherence

- Recap and GM-authored contributions must set `contribution.campaign_scope` to the manifest primary campaign; world-hub contributions may keep `null`.
- Every embedded artifact `campaign_id` must equal the primary campaign.
- Recap evidence/artifact `session_id` values must agree, belong to `manifest.focus_sessions`, and match any `temporal_scope.session_id`.
- Recap edge `value.session_ids` must match the assertion temporal session.
- The observed recap-session set must equal `manifest.focus_sessions`.

---

## Dry-run publication

```text
Dry-run publication:
  temporary test root only
  identity-safe sentinel baseline (no Mirathorn/Caelynn/S23 overlap)

Production Eldyrwild graph head:
  not created

Runtime availability:
  unchanged
```

The dry-run asserts exactly one `location:mirathorn`, one `pc:caelynn`, and one Session 23 gate-battle event under the bundle’s durable IDs. Rebuild with `publish=False` is equivalent to that temporary head.

---

## Plan trust statement

Plan may trust this bundle **after** `/ingest` approval and PR006D publication for:

- identities and basic roles of Mirathorn and Mireward;
- the Questionable Company roster;
- the existence and location of the Session 22 and Session 23 events;
- party participation in those events;
- the Tripod Null-Calf’s association with the Session 23 gate battle;
- provenance distinguishing corpus-backed imports from GM-authored records;
- independent multi-source support for Mireward and the Questionable Company.

Plan may not trust this bundle alone (pre-`/ingest` / pre-PR006D) for live campaign memory, complete Campaign 2 history, rich statblocks, visibility filtering, projection ranking, or retrieval.

---

## Unsupported projection requirements

1. Arbitrary attribute assertion values are retained in the contribution ledger but are not currently materialized as rich node fields.
2. A Plan card cannot yet surface the Tripod’s battlefield role, challenge expectation, or first-appearance detail from the graph head alone.
3. Visibility/admissibility has not been exercised through Projection Engine.
4. The initial bundle does not establish campaign completeness.

---

## Non-claims

PR006C does not prove:

- that `/ingest` UI is complete;
- identity resolution against pre-existing world nodes;
- production Eldyrwild world-head publication;
- projection usefulness;
- Plan or Play integration;
- complete Campaign 2 coverage;
- that corpus files were re-read at validation time (digests are pinned statically);
- that recap `source_span_ref_id` labels resolve to highlightable source spans.
