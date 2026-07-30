---
# Literal Markdown the worker MUST use as the PR-body skeleton.
# The complete checked-in handoff remains authoritative.
pr_body_template: |
  ## Outcome
  An operator can create, generate, edit, validate, accept, hard-reload, and reopen one real statblock revision through the current Workbench so that `SBW08` begins from a proven exact resource rather than synthetic identity.

  ## Merge-ready invariant
  One exact run on merged `main` owns every claimed success: the same new ThreatDraft lineage must produce one candidate and one accepted `(statblock_id, revision_id, digest)` that survives hard reload; any provider, contract, validation, persistence, or reopen failure remains a recorded gate failure and cannot be repaired, bypassed, or relabeled inside this PR.

  ## Evidence required to merge
  | Guarantee | Owning boundary | Required evidence | Result |
  |---|---|---|---|
  | Real current provider path was exercised | operator workflow + readiness route | readiness snapshot and product-door dogfood | {{TODO}} |
  | One exact draft lineage reached a candidate or failed truthfully | Workbench + Buddy generation operation | draft/version, request ID, candidate ID or terminal failure packet | {{TODO}} |
  | One shipped numeric edit validated | Workbench editor + validation route | before/after field and validation receipt | {{TODO}} |
  | One exact accepted locator survived reload | acceptance operation + Workbench reopen path | exact `(statblock_id, revision_id, digest)` before and after hard reload | {{TODO}} |
  | Gate documents match the observed result | report + tracker/roadmap | focused docs diff and changed-path check | {{TODO}} |

  ## Scope and explicit deferrals
  - Base: `2f95d2af998e73ce876ff66fcdc731eff590a3b2`
  - Actual head: {{TODO}}
  - Actual changed paths: {{TODO}}
  - Paths outside handoff allowlist: {{TODO: none or stop report}}
  - Deferred successors still false: `R0-A-DIAGNOSTICS`, re-anchored `SBW08`, `AUTHORING-LIBRARY`, `SBW06d`, publication, query/hydration, projection, placement, combat.

  ## Evidence produced
  ### Automated
  Documentation validation and changed-path commands only; no runtime code changes are authorized.

  ### Adversarial
  {{TODO: record the ordered failure/reload sequence actually exercised}}

  ### Regression
  {{TODO: compare the new run with the 2026-07-29 `FAIL_PRODUCT` baseline}}

  ### Manual / dogfood
  {{TODO: complete Workbench scenario and exact identities}}

  ## Gaps, waivers, and stop conditions
  {{TODO: none, or exact missing evidence and named successor handoff}}
---

# HANDOFF — PR457 R0-A accepted revision proof

**Created:** 2026-07-30.
**Status:** ACTIVE — dispatch exactly one evidence-producing capability.
**Canonical handoff path:** `Docs/Plans/HANDOFF-pr457-r0a-accepted-revision-proof.md`
**Repository:** `Drakosfire/DungeonMindBuddy`
**Implementation base:** `2f95d2af998e73ce876ff66fcdc731eff590a3b2` — merge of PR `#456`
**Suggested branch:** `dogfood/r0a-accepted-revision-proof-2026-07-30`

> **Dispatch gate:** This is a dogfood evidence PR, not a repair PR. Run the real current path and record one truthful result. Any required runtime-code change is a stop condition and belongs in a new handoff.
>
> This checked-in handoff is the complete authority. The worker must not compress, omit, replace, or rewrite it before execution. The PR description must use the frontmatter skeleton and remain a truthful merge contract.

## Shared vocabulary

| Term | Definition |
|---|---|
| **Accepted revision proof** | A real Workbench run that produces one exact immutable `(statblock_id, revision_id, digest)` and reopens that same identity after a hard browser reload. |
| **Exact run lineage** | One new `ThreatDraftV1` draft/version, its generation request ID, its candidate ID, its validation receipt, and its accepted locator. |
| **Product door** | Launcher → Plan → Tools → Statblock. The abandoned `/surface` board is not the authoritative entry path for this proof. |
| **Truthful failure** | A provider, contract, validation, persistence, or reopen miss recorded with its real stage and durable identities without fallback, hidden mutation, or success inflation. |
| **Owning boundary** | The Workbench, Buddy route/service/store, or DungeonMind response boundary where the observed guarantee becomes true. |
| **Stop condition** | Any fact requiring implementation, contract redesign, hidden-state editing, or a path outside §4. |

## §1 Mission and merge-ready invariant

An operator can create, generate, edit, validate, accept, hard-reload, and reopen one real statblock revision through the current Workbench so that `SBW08` begins from a proven exact resource rather than synthetic identity.

**Merge-ready invariant:** One exact run on merged `main` owns every claimed success: the same new ThreatDraft lineage must produce one candidate and one accepted `(statblock_id, revision_id, digest)` that survives hard reload; any provider, contract, validation, persistence, or reopen failure remains a recorded gate failure and cannot be repaired, bypassed, or relabeled inside this PR.

### Pre-dispatch critique

| Question | Answer |
|---|---|
| Can one invariant govern every claimed observable path? | Yes. Every path either advances the same exact draft lineage toward an accepted locator or records where that lineage stopped. |
| What adversarial sequence is most likely to falsify it? | Draft creation persists → real generation returns `definition_invalid` or another terminal response → no candidate exists → the operator is tempted to retry blindly, use a different draft, or patch code and still call the gate closed. |
| Would the proposed §7 evidence actually detect that failure? | Yes. The evidence ledger requires the exact draft/version, request ID, candidate or terminal operation, validation receipt, accepted locator, and hard-reload reopen observation. Missing any stage blocks a pass. |
| Which owning boundary is easiest to under-test? | Hard reload and exact reopen. Session memory or remembered IDs can look like persistence without proving the product can recover the same accepted identity. |
| What fact would force this slice to stop or split? | Any code, contract, UI, provider, persistence, or script change required to make the run proceed. The worker must record the failure and dispatch a separately re-anchored successor. |

## §2 Context, authority, and boundaries

| Field | Required content |
|---|---|
| Parent authority | `Docs/Roadmaps/ROADMAP-threat-statblock-authoring-projection.md`; `Docs/Plans/PR-TRACKER-threat-statblock-authoring-projection.md`; `Docs/Reports/REPORT-threat-statblock-roadmap-reanchor-2026-07-30.md` |
| Repository rules | `AGENTS.md`; `.cursor/rules/external-agent-pr-loop.mdc`; `.cursor/skills/external-agent-pr-loop/SKILL.md` |
| Base revision | `2f95d2af998e73ce876ff66fcdc731eff590a3b2` |
| Predecessor contract | PR `#454` merged provider-contract sync, timeout alignment, and freestanding provenance honesty; PR `#456` publication-first roadmap re-anchor |
| Prior evidence | `Docs/Reports/MAGIC-MOMENT-R0-A-2026-07-29.md` — `FAIL_PRODUCT`, real provider `definition_invalid / HTTP 422`, no candidate |
| Exact input consumed | One newly created real Campaign 2 ThreatDraft using a clean, nonduplicated Mireward Latchling description and the current Workbench create/generate request contract |
| Named success successor | Re-anchor `Docs/Plans/HANDOFF-sbw08-world-graph-statblock-binding-contract.md` against current graph Kernel/projection contracts |
| Named failure successor | `R0-A-DIAGNOSTICS`: a newly re-anchored owning-boundary diagnostics handoff; PR `#449` and its DMS handoff are historical research, not dispatch authority |
| What remains false | No Threat publication, `ThreatStatblockBinding`, Hermes hydration, projection, placement, combat integration, authoring library, or accepted-revision revise UX |
| Explicit non-goals | Runtime code changes; DMS prompt/schema changes; validation relaxation; automatic repair/retry; bootstrap repair; `/surface` cleanup; graph writes; `SBW08`; Hermes authoring; library or editor UX |

Read authoritative inputs in order before running:

1. `Docs/Roadmaps/ROADMAP-threat-statblock-authoring-projection.md`
2. `Docs/Plans/PR-TRACKER-threat-statblock-authoring-projection.md`
3. `Docs/Reports/REPORT-threat-statblock-roadmap-reanchor-2026-07-30.md`
4. `Docs/Reports/MAGIC-MOMENT-R0-A-2026-07-29.md`
5. `Docs/Runbooks/INSTRUCTIONS-reboot-dogfood-R0A-R0B.md`
6. `Docs/Runbooks/RUNBOOK-authored-world-object-magic-moment-dogfood.md`
7. `Docs/Runbooks/SCRIPT-R0-A-statblock-live-dependency-proof.md`, except its stale `/surface` entry/reopen directions are superseded by this handoff and the current closeout instructions
8. `AGENTS.md` and the external-agent PR-loop rules

Authority precedence:

```text
1. Current repository rules
2. Merged publication-first roadmap and tracker
3. This checked-in handoff
4. Current closeout instructions and dogfood runbook
5. Current implementation and owning-boundary behavior
6. Historical R0-A report and open PR #449 research
7. Chat summaries
```

If `main` moved after the base, record the actual SHA. Continue only when the movement is documentation-only or unrelated and the Workbench/provider contracts are unchanged. Otherwise stop and re-anchor.

## §3 Observable-path and adversarial-sequence inventory

| Path | Current behavior | Required behavior in this slice | Same invariant as §1? | Owning boundary |
|---|---|---|---:|---|
| Runtime preflight | Three local processes may be unavailable or misconfigured | Record exact health/readiness; unavailable dependency produces `BLOCKED_DEPENDENCY`, not implementation | Yes | DMS health + Buddy readiness + UI |
| Product entry | Current authoritative path is launcher → Plan → Tools → Statblock | Use that path; do not use `/surface` as the gate door | Yes | Live Control UI |
| Draft create | PR `#454` allows honest freestanding creation when appropriate and explicit opt-in otherwise | Create one new draft; capture exact draft ID/version and graph context; no invented pointers | Yes | Workbench + ThreatDraft store |
| Real generation success | Candidate may load through current provider contract | Capture request ID and candidate ID; continue with same lineage | Yes | Buddy generation service + DMS |
| Real generation terminal failure | Prior run collapsed `definition_invalid` to a generic sentence | Capture every structured field available in UI/API/tombstone; stop the gate without code changes | Yes | DMS error envelope + Buddy operation/tombstone + Workbench |
| Dedicated numeric edit | AC, HP scalar, and ability scores are shipped controls | Change one combat-relevant numeric field and capture before/after | Yes | Workbench editor working copy |
| Validation | Working copy can produce a validation receipt or issues | Require a clean receipt for the exact edited definition; user-correctable edit mistakes may be fixed using existing controls | Yes | Buddy validation route + Workbench |
| Accept/save mechanics | Current acceptance flow can create immutable mechanics | Capture exact `statblock_id`, `revision_id`, and `digest`; verify UI does not claim graph publication | Yes | Acceptance operation + DMS exact revision |
| Hard reload and reopen | Current recovery may require exact UI controls and can be awkward | Hard reload, return through Plan → Tools → Statblock, and reopen the same accepted identity using product-visible controls only | Yes | Workbench recovery + durable stores |
| Retry/replay | Same-draft retry exists; old terminal request remains durable | Retry only when the product presents it and the operator deliberately tests the same draft; record whether request identity is reused or replaced | Yes | generation reconciliation + Workbench |
| Gate documentation | Tracker currently says `FAIL_PRODUCT`; roadmap blocks `SBW08` on accepted proof | Add one new report and update authority only to the result actually observed | Yes | checked-in reports/tracker/roadmap |

Adversarial sequences:

| Sequence | Required safe outcome | Owning proof |
|---|---|---|
| New draft persists → generate terminally fails → browser reload | Draft/failure lineage remains truthful; report `FAIL_PRODUCT` or `BLOCKED_DEPENDENCY`; no candidate or accepted identity is invented | §7 generation-failure and report rows |
| Generate succeeds → numeric edit dirties working copy → validation rejects it | Operator may revert/correct only through shipped controls; no hidden JSON edit; clean receipt required before accept | §7 edit/validation row |
| Accept succeeds → success response is observed → browser hard reload → exact identity cannot reopen | Do not call `PASS`; record `PASS_WITH_FRICTION` or `FAIL_PRODUCT` with exact recovery limitation | §7 accept/reopen row |
| Bootstrap status is not ready/authoritative → no exact override supplied | Use the shipped explicit freestanding opt-in only; graph revision remains null and node/source arrays remain empty | §7 create row |
| Same submit/retry is triggered twice | Record request IDs and durable result; no second draft or candidate may be used to conceal duplicate behavior | §7 lineage row |
| Provider returns a new or richer validation packet | Capture it verbatim within safe bounded fields; do not design or implement propagation in this PR | §7 stop-condition row |

## §4 Files in scope (allowlist)

| Action | Path | Purpose: how this establishes or proves §1 |
|---|---|---|
| Create | `Docs/Reports/MAGIC-MOMENT-R0-A-<actual-run-date>.md` | Authoritative report for one exact rerun; preserve the 2026-07-29 failure report unchanged |
| Modify | `Docs/Plans/PR-TRACKER-threat-statblock-authoring-projection.md` | Point to the new report and record the observed gate status / next authorized slice |
| Modify only on full accepted-revision proof | `Docs/Roadmaps/ROADMAP-threat-statblock-authoring-projection.md` | Change immediate authority from accepted-revision proof to re-anchored `SBW08`; do not modify on another failure unless a factual contradiction is found |

**Bounded discovery exception:**

```text
Directory: Docs/Reports/
Maximum additional paths: 1
Allowed path kinds: exactly one new file named MAGIC-MOMENT-R0-A-YYYY-MM-DD.md using the actual execution date
Decision rule for including one: preserve all prior reports; one new run receives one new report
```

If a same-date report already exists, append an unambiguous suffix such as `-rerun-2` and document why. No production, test, generated, fixture, runtime-state, or other documentation path is authorized.

## §5 Files and capabilities explicitly out of scope

| Path, layer, or capability | Why this slice must not touch or claim it |
|---|---|
| `apps/**`, `src/**`, `tests/**`, generated clients, OpenAPI files | Any runtime or contract change is a separate implementation capability and stop condition |
| DungeonMindServer repository | A repeated provider failure must produce a newly re-anchored DMS handoff, not an in-flight cross-repo fix |
| `Docs/Plans/HANDOFF-sbw08-world-graph-statblock-binding-contract.md` | `SBW08` re-anchor is the next PR after a successful proof, not part of this evidence PR |
| `Docs/Plans/HANDOFF-dms-generation-validation-diagnostics.md` on PR `#449` | Historical research is stale against merged PRs `#454` and `#456`; do not merge or dispatch it as authority |
| `Docs/Runbooks/SCRIPT-R0-A-statblock-live-dependency-proof.md` | Its stale `/surface` directions are superseded here; correcting the reusable script is a later atomic docs sync, not required to prove this run |
| Bootstrap/head resolution | PR `#454` defined honest explicit opt-in; architecture repair is independent of accepted mechanics proof |
| AI revise / `SBW06d` | Explicitly deferred; not required for the accepted-revision prerequisite |
| ThreatDraft or accepted-mechanics library | Reopen friction may select this successor, but building it would be a second capability |
| `SBW08–SBW10`, graph publication, query/hydration, projection | Require the accepted resource produced by this proof |
| Placement and combat integration | Later lifecycle gates |
| Prompt tuning, schema relaxation, automatic provider repair | No authorization; diagnostics must identify a recurring failure first |

Nearby work is not authorization. The worker may inspect current code and durable records to classify observed behavior, but may not edit them.

## §6 Implementation contract and conditional matrices

```text
Input:
  DungeonMindBuddy main at or descended from 2f95d2af998e73ce876ff66fcdc731eff590a3b2
  configured real DungeonMindServer
  Buddy live-control API and Live Control UI
  one new clean Mireward Latchling ThreatDraft

Output:
  one new authoritative R0-A report
  tracker synchronized to the exact observed verdict
  roadmap advanced to SBW08 only after exact accepted identity survives hard reload

Invariant:
  one exact new draft lineage owns every success claim; failure never becomes success through fallback, hidden mutation, another draft, or documentation wording

Failure behavior:
  provider/auth unavailable → BLOCKED_DEPENDENCY report; no implementation
  definition_invalid / structured 422 → FAIL_PRODUCT report with all safe diagnostics; stop for R0-A-DIAGNOSTICS
  generic UI error with richer downstream data hidden → FAIL_PRODUCT; name Buddy diagnostic propagation/presentation successor
  no candidate → edit/validate/accept/reopen remain unproved
  validation failure caused by the operator's shipped numeric edit → correct/revert through existing UI only and revalidate; persistent product failure stops
  acceptance failure → record exact operation/request state; no graph/publication work
  accepted identity cannot reopen through product-visible recovery → PASS_WITH_FRICTION or FAIL_PRODUCT; never use raw filesystem/API mutation to manufacture reopen

Replay / idempotency:
  same product click without retry intent → must not be represented as two independent successful lineages
  product-supported retry on the same draft → record original and retry request IDs and durable outcomes
  new draft after failure → prohibited as a way to hide the first lineage; a second exploratory run must be reported separately and cannot replace it

Trust boundary:
  Verifies: provider readiness, Buddy orchestration, exact identities, validation receipt, acceptance locator, product-visible hard reload/reopen
  Records or trusts without proving: encounter balance, generated design quality, graph publication readiness beyond exact resource identity
  Rejects: mocks, corpus-promotion Statblock View, hidden store edits, copied accepted IDs from logs without product reopen, latest-revision fallback
```

Commit model:

```text
Runtime commit point:
  successful accepted-mechanics operation creating the exact immutable statblock revision

Before commit:
  draft, candidate, and working-copy state may exist; no accepted revision may be claimed

After commit:
  the exact locator is durable and must remain the same through hard reload/reopen

Truthful result after a post-commit reopen failure:
  accepted mechanics may exist, but the gate is not a clean PASS; record PASS_WITH_FRICTION or FAIL_PRODUCT according to whether exact product recovery is possible

Documentation commit point:
  report + tracker (+ roadmap only on full proof) are committed together in one PR
```

### A. State and fallback matrix

| Observable path | Loading / initializing | Exact success | Ordinary miss | Dependency unavailable | Integrity / contract failure | Stale / superseded | Retry / replay |
|---|---|---|---|---|---|---|---|
| Preflight | wait for explicit health/readiness | all three processes available | not configured = blocked | `BLOCKED_DEPENDENCY` | malformed readiness = `FAIL_PRODUCT`/stop | record actual main/provider SHA | rerun preflight only |
| Draft create | submit once | exact draft/version visible | required field miss corrected in UI | server unavailable = blocked | provenance mismatch/failure recorded | exact graph override must be current if used | no second draft to hide failure |
| Generate | truthful in-flight state | exact candidate + request ID | no candidate = failure | timeout/unavailable classified | 4xx/contract/schema failure fails closed | terminal tombstone remains authority | same-draft retry only when deliberate |
| Validate | exact working copy | clean receipt for edited definition | user-edit issue may be corrected | downstream unavailable stops | integrity/digest mismatch fails closed | stale receipt cannot authorize accept | revalidate exact current copy |
| Accept | exact validated copy | exact immutable locator | no accepted locator = failure | downstream unavailable stops | idempotency/integrity failure recorded | stale validation cannot authorize | existing acceptance reconciliation only |
| Reopen | hard reload | same locator/definition visible | missing recovery path = friction/fail | server unavailable distinguished | digest/identity mismatch fails closed | no `latest` fallback | repeat exact reopen, not new accept |
| Documentation | draft report from observed state | report/tracker truthfully synchronized | N/A | blocked verdict is valid evidence | contradiction blocks merge | latest report pointer explicit | one report per run |

Named fallbacks permitted:

- Create may use the shipped explicit **freestanding without graph head** opt-in. It must produce `graph_revision_id=null`, `selected_node_ids=[]`, and `admitted_source_anchor_ids=[]`.
- No fallback is permitted for generation candidate, validation receipt, accepted revision, exact digest, or hard-reload reopen.

### B. Identity matrix

| Situation | Required rule | Ambiguity behavior | Fallback permitted? |
|---|---|---|---|
| ThreatDraft | exact new `draft_id` + integer version | multiple drafts cannot be merged into one proof | No |
| Generation attempt | exact request ID bound to exact draft/version | duplicate/different request IDs are reported separately | No |
| Candidate | exact candidate ID returned through Buddy | missing candidate cannot be replaced by provider-only object | No |
| Working copy | exact active candidate plus local edits | stale/candidate-switch ambiguity blocks acceptance claim | No |
| Validation | exact receipt/digest for current working definition | stale receipt is invalid | No |
| Accepted mechanics | exact `(statblock_id, revision_id, digest)` | mismatch after reload fails closed | No |
| Graph context | exact revision or explicit null freestanding state | labels/heads cannot substitute silently | Only shipped explicit freestanding path |
| Display name | informational only | never identity | No |

### C. Persistence and replay matrix

| Operation | Durable representation | Round-trip guarantee | Duplicate / replay behavior | Compatibility / migration | Rollback / reversion |
|---|---|---|---|---|---|
| Create draft | `ThreatDraftV1` store | exact draft/version survives generation failure and reload | duplicate create is a separate draft and cannot replace proof lineage | current store only | no destructive cleanup in this PR |
| Generate terminal state | generation operation/tombstone | exact request outcome remains observable | same-draft retry recorded; terminal state not rewritten as success | current reconciliation formats | no store edits |
| Candidate | candidate cache/ref + DMS resource | exact candidate identity drives edit/validate | duplicate retrieval deterministic | current contracts | no deletion |
| Validate | validation receipt bound to definition digest | exact current copy only | revalidation creates/returns current receipt according to existing behavior | current contract | stale receipt discarded by existing product |
| Accept | acceptance journal + DMS statblock/revision | exact locator/digest survives hard reload | existing idempotency/reconciliation only | current contract | immutable revision not deleted |
| Report | checked-in markdown | exact IDs/verdict preserved | one new report per run | prior reports remain evidence | revert docs PR only; runtime artifacts remain |

### D. Predecessor-to-consumer mapping

**Grounding sources:** current Buddy response models and the 2026-07-29 report. This PR does not adapt a contract; it maps observed product outcomes into durable evidence.

| Predecessor field / outcome | Real shape and optionality | Report / tracker behavior | Transformation | Proof source |
|---|---|---|---|---|
| readiness `configured`, `available`, `downstream_status` | booleans + status string | record exact snapshot | no reinterpretation | readiness response |
| draft identity | `draft_id`, `version` | record exact values | none | Workbench/server response |
| generation identity | `request_id`; candidate optional on failure | record candidate ID or terminal absence | none | Workbench response + operation/tombstone |
| generation failure | `failure_category`, message, HTTP/terminal code where available, structured details where available | record exact safe fields and missing-detail limitation | no invented issue packet | UI/API/tombstone |
| candidate identity | exact `candidate_id` | record and bind later stages | none | Workbench/server response |
| numeric edit | field path and before/after values | record user-visible edit | none | Workbench observation |
| validation | receipt/digest/issue counts as exposed | record exact result | none | validation response/UI |
| acceptance | `statblock_id`, `revision_id`, `digest` | record exact locator | none | acceptance result |
| reopen | same locator visible after hard reload | PASS evidence or friction/failure | exact equality check | manual product observation |

Invented fixture identities, remembered values, or raw provider-only objects are not acceptable evidence.

## §7 Evidence required to merge

Every material invariant clause must be exercised at its owning boundary. This PR is docs-only, but the product dogfood evidence is merge-blocking.

| Guarantee / invariant clause | Owning boundary | Evidence class | Command or manual scenario | Expected evidence | Stop condition |
|---|---|---|---|---|---|
| Run is anchored to merged current code | repository | regression / provenance | `git rev-parse HEAD`; `git show -s --format='%H %s' HEAD` | immutable SHA recorded in report | main moved materially from declared contracts |
| Real provider is reachable | DMS + Buddy readiness | manual / dogfood | DMS health; Buddy `/api/live/statblocks/v1/readiness`; UI HTTP check | configured/available and exact status captured | unavailable dependency or malformed response |
| Correct product door is used | Live Control UI | manual / dogfood | launcher → Plan → Tools → Statblock | Workbench opens without `/surface` | current navigation differs materially |
| One exact new draft lineage exists | Workbench + ThreatDraft store | manual / dogfood | create one clean Mireward Latchling draft | exact draft ID/version and graph context | hidden state edit or second draft substituted |
| Generation result is truthful | Buddy generation + DMS | adversarial / dogfood | Create & generate once; deliberately record success or terminal failure | request ID + candidate ID, or exact failure fields and no candidate | result cannot be classified from available product/store evidence |
| Numeric edit and validation bind to same candidate | Workbench editor + validation route | manual / dogfood | change AC/HP/ability; validate current copy | before/after field and clean receipt | only protected/manual JSON editing would work |
| Exact immutable revision is accepted | acceptance operation + DMS | manual / dogfood | Accept/Save mechanics | exact locator and no graph-publish claim | no locator, stale validation, integrity failure |
| Exact accepted identity survives hard reload | Workbench recovery + durable stores | adversarial / dogfood | hard reload; Plan → Tools → Statblock; product-visible reopen | same locator/digest visible and mechanics hydrate | filesystem/API-only recovery or identity mismatch |
| Prior failure baseline is compared honestly | report | regression | compare with `MAGIC-MOMENT-R0-A-2026-07-29.md` | explicit fixed/same/new failure classification | prior report overwritten or ignored |
| Documentation authority matches result | report + tracker + conditional roadmap | contract / docs | inspect focused diff | only observed verdict/next action changes | roadmap advanced without full proof |
| No implementation scope entered | git diff | regression | `git diff --name-only <base>...HEAD` | only §4 paths | any code/test/generated/runtime path changes |

Run and record exact results:

```bash
cd /home/drakosfire/Projects/DungeonOverMind/DungeonMindBuddy
git rev-parse HEAD
git show -s --format='%H %s' HEAD

curl -fsS http://127.0.0.1:7860/api/internal/dungeonbuddy/v1/statblocks/health/live
curl -fsS http://127.0.0.1:8000/api/live/statblocks/v1/readiness | python3 -m json.tool
curl -fsS -o /dev/null -w '%{http_code}\n' http://127.0.0.1:5173/

python3 -c 'import json;from pathlib import Path;p=Path("out/graph_memory/worlds/eldyrwild/head.json");print(json.loads(p.read_text())["head_revision_id"] if p.exists() else "no-head-file")'

git diff --check
git diff --stat 2f95d2af998e73ce876ff66fcdc731eff590a3b2...HEAD -- Docs/Reports Docs/Plans/PR-TRACKER-threat-statblock-authoring-projection.md Docs/Roadmaps/ROADMAP-threat-statblock-authoring-projection.md
git diff --name-only 2f95d2af998e73ce876ff66fcdc731eff590a3b2...HEAD
```

No automated runtime suite is required because runtime code must not change. If any code changes, stop rather than adding tests to this PR.

### Minimal live / dogfood proof

```text
Existing surface used:
  Live Control launcher → Plan → Tools → Statblock

Smallest realistic scenario:
  Create one new Mireward Latchling ThreatDraft, generate with the real provider,
  edit one shipped numeric combat field, validate, accept, hard reload, and reopen
  the exact accepted locator.

Expected observation:
  one exact lineage survives from draft through accepted immutable mechanics;
  or the report identifies the exact stage where it stopped without fallback.

Evidence captured:
  readiness snapshot; repository SHA; graph context; draft/version; request ID;
  candidate ID or terminal failure; numeric edit; validation result; accepted locator;
  hard-reload reopen result; screenshots/receipts when useful.
```

### Baseline failure protocol

The baseline is the 2026-07-29 run at repository SHA `686ccb7ed70fd1894212c22252c2567f68daa2b4`:

```text
create succeeded
→ real provider returned definition_invalid / HTTP 422
→ Buddy recorded downstream_validation_failed
→ no candidate
```

The new report must state exactly one of:

- fixed by merged changes: candidate path now succeeds;
- same failure: same stage and materially same contract outcome;
- new failure: different stage, payload, or product behavior;
- blocked dependency: provider/runtime unavailable.

Do not infer root cause from a successful or failed rerun alone. A repeated opaque failure selects the diagnostics successor; it does not authorize implementation here.

## §8 Required PR description and handback

The PR description must remain current and include:

1. §1 Mission copied exactly.
2. §1 merge-ready invariant copied exactly.
3. The completed §7 evidence ledger with result and provenance.
4. Base SHA and head SHA.
5. Actual changed paths and focused diff stat.
6. Exact dogfood steps and every durable identity observed.
7. Exact verdict and comparison with the 2026-07-29 baseline.
8. Automated evidence: documentation commands, or `none` for runtime tests.
9. Manual/dogfood evidence provenance.
10. Baseline failures and any explicit operator waiver; normally `none`.
11. Paths outside §4; `none` or a stop report.
12. Stop conditions encountered and resolution.
13. Named successor selected by the result:
    - full proof → re-anchor `SBW08`;
    - repeated diagnostic failure → new `R0-A-DIAGNOSTICS` handoff;
    - exact reopen friction → `AUTHORING-LIBRARY` / accepted-mechanics browse decomposition;
    - dependency unavailable → rerun only after dependency restoration.
14. Confirmation that publication/query/placement/combat remain unimplemented.
15. Demolition declaration:

```text
Replaced path: none
Deleted in this PR: no
If no, retained reason: this PR changes evidence and sequencing only
Named remaining consumer: current Statblock Workbench accepted-mechanics path
Required deletion owner: none
```

A generic Summary/Test Plan PR body does not satisfy this section.

## §9 Acceptance rubric

The reviewer accepts only when every bullet is true and each behavioral bullet names its §7 proof.

- [ ] Exactly one independently useful outcome was delivered: one truthful R0-A rerun and gate closeout.
- [ ] The exact same new draft lineage owns every claimed success from create through reopen.
- [ ] The product path used launcher → Plan → Tools → Statblock.
- [ ] The real provider was used or the report truthfully records `BLOCKED_DEPENDENCY`.
- [ ] A candidate ID exists before edit/validate/accept are claimed.
- [ ] One shipped numeric combat field was edited and the exact current working copy validated before acceptance.
- [ ] A clean pass includes an exact `(statblock_id, revision_id, digest)` equality check after hard reload.
- [ ] No mock, corpus-promotion view, hidden store edit, raw filesystem mutation, provider-only object, remembered ID, or `latest` fallback was used as proof.
- [ ] A failure PR does not advance the roadmap to `SBW08`.
- [ ] A successful PR advances only the accepted-revision prerequisite; it does not implement or claim `SBW08`.
- [ ] The new report preserves the 2026-07-29 report unchanged and compares against it explicitly.
- [ ] Tracker and conditional roadmap changes match the exact observed verdict.
- [ ] No production, test, generated, fixture, or runtime-state file changed.
- [ ] The PR description contains the complete evidence ledger and exact result provenance.
- [ ] The named successor remains unimplemented and unclaimed.

## Stop conditions

Stop and report rather than expanding if execution discovers:

- any required production, test, generated, fixture, or runtime-state change;
- a current provider contract shape materially different from checked-in Buddy models;
- a repeated `definition_invalid` whose field/reference diagnostics are not available through the current consumer path;
- a richer DMS diagnostic packet that Buddy drops or cannot render;
- a candidate that exists only on DMS and is not authoritative through Buddy;
- acceptance that succeeds but cannot be reconciled to an exact locator;
- hard reload that requires raw filesystem edits, direct hidden-store mutation, or an unshipped API call;
- ambiguous draft/candidate/accepted identity;
- a main-branch move affecting statblock contracts or Workbench behavior;
- pressure to fix the stale `/surface` script, bootstrap head, authoring library, revise UX, or publication path inside this PR;
- a claim that `SBW08` can proceed without an exact accepted locator surviving reopen.

Use this report:

```text
Stop condition:
Why the current mission cannot absorb it:
Invariant clause affected:
Required evidence now missing:
Observed draft/version/request/candidate/accepted identities:
Provider/Buddy failure fields:
Required path outside scope:
Proposed successor slice:
Tracker or authority update needed:
Operator decision required:
```

The worker must not resolve a stop condition by silently broadening the mission.