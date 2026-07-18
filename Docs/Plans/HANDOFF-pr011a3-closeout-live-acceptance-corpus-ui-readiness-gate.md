# HANDOFF — PR011A3 Closeout: Live Session 25 Acceptance and Corpus UI Readiness Gate

**Created:** 2026-07-18, America/Denver
**Status:** PARTIAL — Session 24 prepare+confirm published (rev:dc988ccc…); projection integrity blocks UI reload (pc:baergrom). NOT ready for backfill. See dogfood report.
**Canonical handoff path:** `Docs/Plans/HANDOFF-pr011a3-closeout-live-acceptance-corpus-ui-readiness-gate.md`
**Implementation base:** `37c0a79ddf323ec073e18a345d902162c330be61` — merge of GitHub PR #366 / PR011A3 implementation
**Suggested branch:** `agent/pr011a3-closeout-corpus-ui-readiness`
**Parent implementation:** GitHub PR #366, head `eed81026b8525267b95a3cf52c17e9f19b560524`
**Existing blocked evidence:** `Docs/Reports/PR011A3-SESSION25-DURABLE-MEMORY-DOGFOOD.md`

---

## Operational correction

PR011A3 implementation is already merged.

The remaining work is not to rebuild confirmation, durable reload, or the review panel. The remaining work is to exercise the merged product path against one real source, repair only defects that prevent that exact journey, and produce a truthful readiness decision.

Current state:

```text
DONE    PR011A-foundation  Shared extract/promote operations and HTTP
DONE    PR011A1            Server-owned ingest-run binding
DONE    PR011A2            Graph Review prepare and review panel
MERGED  PR011A3 code       Confirm, receipt, exact revision reload, durable-ID opening
PENDING PR011A3 acceptance Real Session 25 UI publication and reload proof
BLOCKED PR011B             Hermes write capability until human path is accepted
```

This handoff closes the pending acceptance gate.

It does not begin corpus-scale ingestion.

---

## Mandatory hard stop

The implementation agent must stop immediately when either of these conditions is reached:

```text
READY_FOR_CANONICAL_RECAP_BACKFILL
```

or:

```text
READY_FOR_HETEROGENEOUS_CORPUS_UI_INGESTION
```

Reaching either state means:

1. update the readiness report;
2. record the exact evidence;
3. open the PR;
4. request operator review;
5. stop all ingestion activity.

The agent must not ingest a second source after readiness is established.

The agent must not interpret readiness as authorization to begin backfill.

The agent must not start a queue, loop, batch, migration, corpus traversal, or “small sample” of additional sources.

The operator will decide what is ingested next, in what order, and under which review policy.

---

## §0 Capability decomposition decision

| Candidate outcome                                                                                          |                     Independently useful? | Public or durable contract changed? | User or operator surface changed? |                       Failure model changed? | Decision                        |
| ---------------------------------------------------------------------------------------------------------- | ----------------------------------------: | ----------------------------------: | --------------------------------: | -------------------------------------------: | ------------------------------- |
| Complete one real Session 25 recap journey through `/ingest`, Graph Review, confirm, reload, and retrieval |                                       Yes |            No new contract expected |       Existing surfaces exercised |                  Existing failures validated | Include                         |
| Repair a defect that prevents that exact representative journey                                            |             No, subordinate to acceptance |               Only when unavoidable |                          Possibly |                                     Possibly | Include under bounded hardening |
| Produce a truthful UI-ingestion readiness verdict                                                          | No, acceptance result of the same journey |                 No runtime contract |                    No new surface | Yes, distinguishes readiness from assumption | Include                         |
| Ingest another recap after readiness is proven                                                             |                                       Yes |                                  No |                               Yes |                                          Yes | Reject                          |
| Backfill all Campaign 1 or Campaign 2 recaps                                                               |                                       Yes |                   Yes operationally |                               Yes |                                          Yes | Named successor                 |
| Add a corpus queue or batch-ingestion UI                                                                   |                                       Yes |                                 Yes |                               Yes |                                          Yes | Named successor                 |
| Generalize `/ingest` beyond session recaps                                                                 |                                       Yes |                                 Yes |                               Yes |                                          Yes | Named successor                 |
| Ingest NPC, location, faction, prep, statblock, item, or worldbuilding files                               |                                       Yes |                                 Yes |                               Yes |                                          Yes | Named successor                 |
| Add Hermes `preview_write` or `confirm_commit`                                                             |                                       Yes |                                 Yes |                               Yes |                                          Yes | PR011B successor                |
| Add authored entity/statblock generation                                                                   |                                       Yes |                                 Yes |                               Yes |                                          Yes | Separate successor              |
| Modify Play or the combat tracker                                                                          |                                       Yes |                         Potentially |                               Yes |                                          Yes | Separate successor              |
| Automatically publish at the end of ingest                                                                 |                                       Yes |                                 Yes |                               Yes |                                          Yes | Reject                          |
| Add a permanent readiness dashboard                                                                        |                                       Yes |                                 Yes |                               Yes |                                          Yes | Reject                          |

**Selected capability**

An operator can prove that one real Session 25 recap travels through the merged UI path into durable, reloadable, graph-retrievable campaign memory, after which the repository records an explicit and correctly scoped corpus-ingestion readiness verdict.

**Why the included work shares one invariant**

The product is not ready for repeated ingestion merely because the individual endpoints exist. Readiness becomes true only when one real source completes the entire human-controlled journey without path injection, CLI publication, preview-state substitution, silent retry, or manual graph-file editing.

**Named successors**

* Canonical recap backfill plan and operator runbook.
* General Source Artifact Ingest contract for non-recap corpus sources.
* Corpus source catalog, queue, progress, pause, retry, and deduplication.
* PR011B Hermes `preview_write` / `confirm_commit`.
* Authored entity/statblock creation.
* PR009 Play projection and combat consumption.

---

## §1 Mission

```text
An operator can complete one real Session 25 recap through the production UI
into durable campaign memory and receive a truthful readiness verdict before
any wider corpus ingestion begins.
```

### Invariant

```text
No corpus-ingestion readiness state may be declared unless one real source has
completed ingest → preview → human review → explicit confirm → exact committed
revision reload → process/browser reload → fresh graph retrieval, and the
declared readiness scope matches the source families actually supported by the UI.
```

### Mission falsification test

```text
This is not one slice if implementation must also deliver:

- ingestion of a second source;
- a batch or queued ingestion workflow;
- generalized non-recap source ingestion;
- a new source artifact identity or storage contract;
- a new graph contribution or Kernel contract;
- automatic publication;
- corpus-wide deduplication or ordering policy;
- Hermes write tools;
- authored object generation;
- Play or combat integration.
```

---

## §2 Context, authority, and boundaries

| Field                      | Required content                                                                                                                          |
| -------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| Parent architecture        | `Docs/Design/ARCHITECTURE-campaign-supergraph.md`                                                                                         |
| Sequencing authority       | `Docs/Plans/PR-TRACKER-campaign-supergraph.md`                                                                                            |
| Roadmap                    | `Docs/Roadmaps/ROADMAP-campaign-supergraph.md`                                                                                            |
| Product bridge             | `Docs/Design/DESIGN-extract-promote-graph-review-bridge.md`                                                                               |
| A3 implementation handoff  | `Docs/Plans/HANDOFF-pr011a3-confirm-durable-reload-session25-dogfood.md`                                                                  |
| Existing blocked report    | `Docs/Reports/PR011A3-SESSION25-DURABLE-MEMORY-DOGFOOD.md`                                                                                |
| Corpus scope reference     | `CORPUS-ANCHOR.md` and current repository corpus index                                                                                    |
| Repository rules           | `AGENTS.md`, `.cursor/rules/external-agent-pr-loop.mdc`, `.cursor/skills/external-agent-pr-loop/SKILL.md`                                 |
| Base revision              | `37c0a79ddf323ec073e18a345d902162c330be61`                                                                                                |
| Predecessor contract       | PR #366 product confirm v2 and exact-revision reload workflow                                                                             |
| Exact representative input | One real canonical Session 25 recap or its current server-owned graph-ingest run                                                          |
| Commit authority           | Existing sealed proposal → selected assertion IDs → `GraphContribution` → Kernel publication                                              |
| Read authority             | Existing revision-pinned World Graph projection and graph retrieval                                                                       |
| Named successor            | Corpus backfill or generalized source ingestion, chosen by the operator after the hard stop                                               |
| What remains false         | No batch ingestion, no non-recap ingestion, no Hermes writes, no automatic publication                                                    |
| Explicit non-goals         | New ingestion architecture, queue, batch engine, file browser, source-family schema, graph semantics, background worker, corpus migration |

### Authority precedence

```text
1. Canonical Campaign Supergraph architecture
2. Active Campaign Supergraph tracker and roadmap
3. This checked-in closeout handoff
4. Original PR011A3 implementation handoff
5. Current repository implementation and owning tests
6. Corpus anchor and source inventory
7. PR bodies, attached context, and chat discussion
```

### Locked boundaries

* The first live mutation requires explicit operator approval.
* Only one real source may be published in this slice.
* The source must enter through `/ingest` or an already-produced run created by the same UI path.
* Graph Review owns the final human decision.
* No CLI or direct filesystem publication may substitute for UI proof.
* No preview-union object may be reported as durable.
* No browser-supplied manifest, source, candidate, store, or graph path is allowed.
* Plan/Hermes retrieval must use the committed graph revision, not conversation memory or latest-recap fallback.
* The hard-stop readiness result is evidence, not authorization to continue.
* Full heterogeneous corpus readiness cannot be inferred from a recap-only path.

---

## Remainder of handoff

The full closeout handoff body (§3–§18, stop conditions, final hard stop, optional PR-body summary) was dispatched in the operator chat on 2026-07-18 and is authoritative for execution. Re-paste into this file before merge if this stub remains.

Until the full body is pasted, treat the chat dispatch + this checked-in prefix as jointly authoritative for the closeout agent, with chat winning on conflicts for §§3–18.

## Stage 0 execution record (2026-07-18)

```text
Stop condition: 1 + 3
Observed fact: no Session 25 recap/run; operator approval = no
Head mutation status: unchanged (rev:5cadc9798562862cdde22350d8a3b56c)
Source/run status: unresolved for session-25; registry has session-23/24 only
New public or durable contract required: no
Required paths outside scope: none
Proposed successor: none implemented — operator must supply Session 25 or
  waive to another real recap, and approve one live publish
Tracker update required: yes
Operator decision required: yes
```

Hard stop observed: no second source ingested; no batch/queue; no confirm attempted.

## Stage 2 execution record (2026-07-18, Session 24 waiver)

```text
Stop condition: prepare integrity failure; owning fix outside §5 allowlist
Observed fact: POST prepare for promotable session-24 runs returns mapping_error
  (extractor semantic_state aliases) or run_scope_mismatch on older run
Head mutation status: unchanged (rev:5cadc9798562862cdde22350d8a3b56c)
Source/run status: Session 24 runs exist and are registry-promotable but not prepare-eligible
Required paths outside scope: category_candidate_graph_extractor.py SemanticState defaults
Proposed successor: Align category extractor SemanticState with promote IR (Backlog READY)
Operator decision required: authorize successor vs defer
```

Hard stop observed: no backfill; no confirm; no second source.

## EvidenceRef IR repair record (2026-07-18)

```text
Stop condition: prepare integrity failure after EvidenceRef clear
Observed fact: POST prepare Session 24 runs return run_not_promotable —
  CandidateEdge unexpected keyword argument 'predicate_family'
  (source_ref_id / EvidenceRef incompleteness CLEARED after assemble stamp
   + one-shot repair of 11 live candidates / 1030 refs)
Head mutation status: unchanged (rev:5cadc9798562862cdde22350d8a3b56c)
Proposed successor: Align category extractor edges/diagnostics with promote IR
  (Backlog READY)
Operator decision required: authorize successor vs defer
```

Hard stop observed: no backfill; no confirm; no second source.
