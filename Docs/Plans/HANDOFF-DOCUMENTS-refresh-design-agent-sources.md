# HANDOFF — Refresh design-agent immediate-source export

**Created:** 2026-08-13  
**Status:** ACTIVE — one documentation/export capability  
**Canonical handoff path:** `Docs/Plans/HANDOFF-DOCUMENTS-refresh-design-agent-sources.md`  
**Conversation/workstream:** `DungeonBuddy development-process optimization`  
**Flow / owner:** `DOCUMENTS`  
**Direction:** DESIGN → CODE → REVIEW  
**Base revision:** `3a52d309a606608c9338147b78e0a2f708084042`  
**PR title:** `DOCUMENTS: refresh design-agent source export`

> Repository law: [`AGENTS.md`](../../AGENTS.md). Steward process: [`Docs/Process/STEWARD-CYCLE.md`](../../Docs/Process/STEWARD-CYCLE.md).

## §1 Mission and merge-ready invariant

**Mission:** The operator can refresh ChatGPT immediate / Project Sources from one repo-resident, classified bundle whose files exactly mirror the current canonical design/process source set.

**Merge-ready invariant:** `Docs/Sources/design-agent/` contains only the current 16-file clean upload set, each mirrored file is byte-identical to its canonical repository source at the pinned base except that the refreshed source-set index intentionally becomes canonical and mirror in the same commit, the bundle contains `AGENTS.md` + `STEWARD-CYCLE.md` + the slim handoff template, superseded Jumpstart is absent, and `Docs/Design/INDEX-design-agent-source-set.md` truthfully identifies the export as a non-authoritative mirror without claiming the user-managed Project Sources UI was already refreshed.

### Pre-dispatch critique

| Question | Answer |
|---|---|
| Can one invariant govern every path? | Yes. Every path either defines the upload manifest or is an exact mirror of one canonical source. |
| Most likely adversarial failure | Export copies drift from canonical files, or the source index claims the user's Project Sources were refreshed when only the repo bundle changed. |
| Does §7 catch it? | Yes: blob/content identity by mapping, exact file inventory, no-Jumpstart check, and explicit snapshot-date review. |
| Easiest boundary to under-test | The mirrored `INDEX-design-agent-source-set.md`, because it changes in the same commit it is exported. It must use the same blob at both paths. |
| Stop/split trigger | Any attempt to alter product architecture/sequence merely to make the bundle look current, or to add unresolved source-only/history files by default. |

## §2 Context, authority, and lane

| Field | Required content |
|---|---|
| Parent authority | Current `Docs/Design/INDEX-design-agent-source-set.md`; `Docs/Reports/graph-document-audit.md`; repository `main` |
| Base revision | `3a52d309a606608c9338147b78e0a2f708084042` |
| Exact input | Current canonical source files on the pinned base + the immediate files visible in this conversation |
| Current observed staleness | Attached Jumpstart is pre-Steward-Cycle; attached handoff template is pre-template-diet; source index predates `AGENTS.md`; `GRAPH-MEMORY-PROJECT-LAYOUT.md` is current repo reference but absent from attached set |
| Named successor | Optional deterministic refresh/check script after this manual mirror is dogfooded |
| What remains false | Repo changes cannot automatically replace files in the user's Project Sources UI; operator upload remains manual |
| Runtime/state ownership | Not applicable — repository documentation/export only |
| State-authority sync set | This handoff only after merge; the source index is updated inside the implementation PR because its claims change as part of the capability |

## §3 Observable paths and adversarial sequences

| Path | Current behavior | Required behavior | Same §1 invariant? | Owning boundary |
|---|---|---|---:|---|
| Operator wants fresh immediate sources | Reconstructs from downloads/File Library and stale index | Opens one classified repo folder | Yes | export manifest |
| Old Jumpstart is in attached sources | Can look like active process law | No active Jumpstart copy; Steward Cycle replaces it | Yes | source-set classification |
| Old HANDOFF template is attached | Carries duplicated/fixed process law | Clean export contains current slim template | Yes | process export |
| `AGENTS.md` not attached | Foundational law missing from immediate context | Included in PROCESS | Yes | process export |
| `GRAPH-MEMORY-PROJECT-LAYOUT.md` not attached | Current path/reference context omitted | Included in ACTIVE_REFERENCE | Yes | source-set index |
| Canonical file changes later | Export can become stale | Canonical wins; README says refresh required | Yes | mirror contract |

Adversarial sequence: canonical index is rewritten → export copies the old index blob → operator uploads internally contradictory bundle. Required outcome: canonical and export index paths use the same new blob.

## §4 Files in scope — write lease

| Action | Path | Purpose |
|---|---|---|
| Modify | `Docs/Design/INDEX-design-agent-source-set.md` | Current canonical source-set manifest and export pointer. |
| Create | `Docs/Sources/design-agent/README.md` | Export identity, upload instructions, canonical mapping. |
| Create | `Docs/Sources/design-agent/ACTIVE_AUTHORITY/ARCHITECTURE-campaign-supergraph.md` | Exact canonical mirror. |
| Create | `Docs/Sources/design-agent/ACTIVE_AUTHORITY/ROADMAP-campaign-supergraph.md` | Exact canonical mirror. |
| Create | `Docs/Sources/design-agent/ACTIVE_AUTHORITY/PR-TRACKER-campaign-supergraph.md` | Exact canonical mirror. |
| Create | `Docs/Sources/design-agent/ACTIVE_AUTHORITY/graph-document-audit.md` | Exact canonical mirror. |
| Create | `Docs/Sources/design-agent/ACTIVE_AUTHORITY/ARCHITECTURE-surface-interaction-layer.md` | Exact canonical mirror. |
| Create | `Docs/Sources/design-agent/ACTIVE_REFERENCE/STATUS-world-graph-continuity-spine.md` | Exact canonical mirror. |
| Create | `Docs/Sources/design-agent/ACTIVE_REFERENCE/ARCHITECTURE-plan-surface-toolbox.md` | Exact canonical mirror. |
| Create | `Docs/Sources/design-agent/ACTIVE_REFERENCE/GRAPH-MEMORY-PROJECT-LAYOUT.md` | Exact canonical mirror. |
| Create | `Docs/Sources/design-agent/ACTIVE_REFERENCE/PLAN-surface-interaction-hoist-build-first.md` | Exact canonical mirror. |
| Create | `Docs/Sources/design-agent/ACTIVE_REFERENCE/INDEX-hermes-campaign-authoring-foundation.md` | Exact canonical mirror. |
| Create | `Docs/Sources/design-agent/ACTIVE_REFERENCE/README.md` | Exact canonical mirror. |
| Create | `Docs/Sources/design-agent/ACTIVE_REFERENCE/INDEX-design-agent-source-set.md` | Same new blob as canonical index. |
| Create | `Docs/Sources/design-agent/SOURCE_ANCHOR/CORPUS-ANCHOR.md` | Exact canonical mirror. |
| Create | `Docs/Sources/design-agent/PROCESS/AGENTS.md` | Exact canonical mirror. |
| Create | `Docs/Sources/design-agent/PROCESS/STEWARD-CYCLE.md` | Exact canonical mirror. |
| Create | `Docs/Sources/design-agent/PROCESS/HANDOFF.template.md` | Exact canonical mirror. |
| Create | `Docs/Plans/HANDOFF-DOCUMENTS-refresh-design-agent-sources.md` | Slice authority. |

**Bounded discovery exception:** Not applicable.

## §5 Explicitly out of scope / collision boundary

| Path | Why this slice must not touch or claim it |
|---|---|
| `Docs/Plans/JUMPSTART-docs-relevance-first.md` | Remains a superseded compatibility stub at canonical path; intentionally absent from clean export. |
| Product architecture/roadmap/tracker contents beyond copying | This slice does not reinterpret or advance product state. |
| `corpus/**`, `out/**`, generated eval artifacts | Not immediate-source defaults. |
| Source-only historical/proposal files | Intentionally omitted unless operator explicitly requests historical research context. |
| Project Sources UI | User-managed external context; repo cannot mutate it automatically. |

## §6 Implementation contract

```text
Input:
  pinned current main + canonical source mapping

Output:
  Docs/Sources/design-agent classified 16-file upload mirror
  + README mapping/instructions
  + refreshed canonical source-set index

Invariant:
  same as §1

Failure behavior:
  missing canonical source → block
  mirror/canonical blob mismatch → block
  unexpected export file → block
  active Jumpstart in export → block
  source index claims Project Sources already refreshed → block

Replay/idempotency:
  same pinned source blobs → same mirror file contents
  changed main → refresh mapping copies and README pin

Trust boundary:
  Canonical repository paths define content.
  Export copies do not define authority.
```

### A. State / fallback matrix

Not applicable — static repository documentation/export; no runtime fallback.

### B. Identity matrix

| Situation | Required rule | Ambiguity behavior | Fallback permitted? |
|---|---|---|---|
| Export filename | Clean canonical basename inside classification folder | No download suffixes | No |
| Canonical identity | Repo-relative path in README/index mapping | Missing path blocks refresh | No |
| Superseded source | May remain at canonical compatibility path | Must not appear in clean active export | No active fallback |

### C. Persistence / replay matrix

| Operation | Durable representation | Round-trip guarantee | Duplicate/replay | Compatibility |
|---|---|---|---|---|
| Source export | Git blobs under `Docs/Sources/design-agent/` | Every mapped copy equals canonical bytes at pin | Re-refresh same pin is content-idempotent | Old uploaded filenames are replaced manually; Jumpstart compatibility remains at canonical stub path only |

### D. Predecessor → consumer mapping

**Grounding source:** current canonical source index + visible attached immediate-source inventory.

| Old/immediate source | Current consumer replacement | Transformation | Proof |
|---|---|---|---|
| `JUMPSTART-docs-relevance-first(2).md` | `PROCESS/STEWARD-CYCLE.md` | superseded process source removed/replaced | export inventory |
| `HANDOFF.template(1).md` | `PROCESS/HANDOFF.template.md` | old tutorial-heavy template replaced by current slim template | canonical blob equality |
| missing foundational law | `PROCESS/AGENTS.md` | add current foundational source | export inventory |
| missing graph layout reference | `ACTIVE_REFERENCE/GRAPH-MEMORY-PROJECT-LAYOUT.md` | add current reference | export inventory |
| remaining suffixed downloads | same clean basename under classified folder | exact current canonical copy | mapping/blob equality |

## §7 Evidence required to merge

| Guarantee | Owning boundary | Evidence class | Expected | Stop condition |
|---|---|---|---|---|
| Export inventory is exactly 16 mapped sources + README | export tree | structural diff | exact classified set | missing/extra active source |
| Every unchanged canonical source copy is exact | Git blob mapping | identity proof | destination uses canonical blob SHA | copied/re-authored bytes differ |
| Canonical and exported source index match | Git blob mapping | identity proof | both paths use same new blob SHA | two index versions |
| Jumpstart absent, Steward Cycle present | export inventory | classification proof | no active Jumpstart path; PROCESS Steward present | stale process source remains |
| AGENTS + Graph Memory layout added | export inventory | completeness proof | both present | omission |
| User-managed snapshot date remains truthful | canonical index review | temporal proof | still 2026-08-02 until actual upload | repo merge falsely claims UI refresh |
| Scope exact | PR diff | static | only §4 paths | unrelated file changes |

Verification commands for a local implementation environment:

```bash
git diff --check
git diff --name-only 3a52d309a606608c9338147b78e0a2f708084042...HEAD
find Docs/Sources/design-agent -type f | sort
! find Docs/Sources/design-agent -type f -iname '*JUMPSTART*' | grep .
cmp Docs/Design/ARCHITECTURE-campaign-supergraph.md Docs/Sources/design-agent/ACTIVE_AUTHORITY/ARCHITECTURE-campaign-supergraph.md
cmp Docs/Design/INDEX-design-agent-source-set.md Docs/Sources/design-agent/ACTIVE_REFERENCE/INDEX-design-agent-source-set.md
cmp AGENTS.md Docs/Sources/design-agent/PROCESS/AGENTS.md
cmp Docs/Process/STEWARD-CYCLE.md Docs/Sources/design-agent/PROCESS/STEWARD-CYCLE.md
cmp .cursor/skills/external-agent-pr-loop/templates/HANDOFF.template.md Docs/Sources/design-agent/PROCESS/HANDOFF.template.md
```

## §8 Required review handback

Record Review Cycle N, exact base/head, export inventory count, canonical→mirror identity result, Jumpstart absence, new AGENTS/layout presence, source-index temporal claims, changed paths, and any divergence from the visible attached-source set.

## §9 Acceptance rubric

- [ ] A clean repo-resident source export exists at `Docs/Sources/design-agent/`.
- [ ] The export has exactly the current 16-file upload set plus its README.
- [ ] Mirror files are byte-identical to canonical repository sources at the pinned refresh revision.
- [ ] The refreshed source index and its exported copy are identical.
- [ ] `AGENTS.md`, `STEWARD-CYCLE.md`, and current slim `HANDOFF.template.md` are in PROCESS.
- [ ] `GRAPH-MEMORY-PROJECT-LAYOUT.md` is included as ACTIVE_REFERENCE.
- [ ] Superseded Jumpstart and unresolved source-only/historical materials are absent from the clean active export.
- [ ] The index does not claim the operator's Project Sources UI was already refreshed.
- [ ] No product authority or implementation sequence is changed by this export PR.
