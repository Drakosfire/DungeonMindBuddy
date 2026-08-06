# HANDOFF — OPT02 notify and prewarm one committed World Graph revision

**Created:** 2026-08-06.
**Status:** ACTIVE DESIGN — dispatch only after the predecessor gate below is satisfied.
**Canonical handoff path:** `Docs/Plans/HANDOFF-opt02-revision-ready-post-commit-prewarm.md`
**Conversation name:** `Optimization — Revision Ready Prewarm`
**Flow / agent:** `OPTIMIZATION`
**Handoff direction:** `DESIGN → CODE`
**Design agent:** `Optimization Designing Agent`
**Code agent:** `Optimization Coding Agent`
**PR title:** `OPTIMIZATION: prewarm committed World Graph revision`
**Suggested branch:** `opt/opt02-revision-ready-post-commit-prewarm`
**Design anchor:** PR #509 reviewed head `34b041d91980e1eac1d148b972332e057bdcb92f`, rebased onto completed Build/Statblock main `9d4f5a3005f87d07147c03d8eee499af3bd57aa3`.

### Predecessor gate status (recorded 2026-08-06)

| Gate clause | Status | Evidence |
| --- | --- | --- |
| PR #509 / OPT01 merged, or `origin/main` contains the exact reviewed OPT01 tree | **SATISFIED** | PR #509 merged at `2026-08-06T19:59:19Z` as merge commit `d50d0c3a45761376185d36fb39ae3a098a5b8cfc`; reviewed tip `34b041d91980e1eac1d148b972332e057bdcb92f` is an ancestor of `origin/main` |
| Immutable `origin/main` base SHA at dispatch | **CANDIDATE** `d50d0c3a45761376185d36fb39ae3a098a5b8cfc` — re-resolve at coding dispatch | `git rev-parse origin/main` after PR #509 merge |
| OPT01 E10 live proof passed, or explicit operator waiver on PR #509 | **NOT SATISFIED** | No live dogfood evidence and no operator waiver recorded on PR #509; OPT01 §8 marks E10 NOT PROVEN |

> **Dispatch gate:** Do not dispatch until PR #509 / OPT01 is merged or `origin/main` contains the exact reviewed OPT01 tree, **and** its required E10 live proof has either passed or received an explicit operator waiver. Resolve and record the immutable `origin/main` base SHA at dispatch. If the merged OPT01 runtime or Kernel publication facade differs materially from the reviewed shapes named here, stop and return to the Optimization Designing Agent.

> **Capability gate:** This slice owns only a process-local, best-effort post-commit resident prewarm. It must not create a durable event log, cross-process bus, filesystem watcher, surface-specific publication hook, projection-response recipe, UI status, write retry, or new publication authority.

> This checked-in handoff is the complete authority. Do not compress, replace, or reinterpret it before implementation. The PR description is only a transport pointer.

## §0 Optimization line charter

The Optimization line makes the World Graph feel continuously present without reopening graph authority, projection meaning, or surface design.

```text
OPT01  verified resident revision read runtime                    predecessor
OPT02  revision-ready notification and post-commit prewarm        ← this handoff
OPT03  bounded serving recipes / surface bootstrap                 successor
OPT04  delta-aware publication and materialization                 later successor
```

OPT01 established that one exact immutable revision can be admitted into a process-local resident generation after complete fail-closed verification. OPT02 connects successful publication to that runtime so the newly committed head can begin admission before the next Plan, Build, Threat, Recap, Graph Review, or Hermes read.

OPT02 does not make the resident runtime part of publication correctness. Durable publication remains complete when the immutable revision and `head.json` are committed under the existing Kernel/storage contract. Notification and prewarm are disposable latency work.

### Shared vocabulary

| Term | Definition |
| --- | --- |
| **Publication commit point** | The existing atomic `head.json` advance after the complete immutable revision directory has been written and validated. OPT02 does not move or redefine it. |
| **Successful Kernel publication** | `graph_memory.kernel.publish_world_graph_revision(...)` has completed its existing storage publish and Kernel post-publish work and is about to return `WorldGraphPublishResult` successfully. |
| **Revision-ready notification** | One process-local, non-durable message naming the exact committed `(resolved_root, world_id, revision_id)` and predecessor publication metadata. It is an optimization signal, not authority. |
| **Notification mailbox** | A bounded process-local handoff between the synchronous publisher and the live-server prewarm worker. Offering a notification must not wait for revision loading. |
| **Post-commit prewarm** | Best-effort admission of the exact notified revision through the OPT01 resident runtime before an ordinary projection/retrieval request requires it. |
| **Current-head check** | Re-reading the small authoritative `head.json` immediately before prewarm admission and requiring it still names the notified revision. |
| **Superseded notification** | A queued notification whose revision is no longer the current head when the worker is ready to process it. It is skipped, not treated as failure. |
| **Coalesced prewarm** | A prewarm and ordinary reader share the same OPT01 in-flight cold load for the exact resident key. |
| **Resident-ready outcome** | The notified exact revision is already resident or has passed full OPT01 cold admission and is now resident. |
| **Prewarm failure** | Revision admission failed or the coordinator could not process the signal. Publication remains committed and the next read follows ordinary OPT01 behavior. |
| **Process-local** | State exists only in one Python process. No guarantee is made to sibling workers, another host, or a restarted server. |
| **Payload recipe** | A completed Plan/Build/Threat/Recap/query projection response. OPT02 does not construct or prewarm these; OPT03 owns bounded recipes. |

### Agent flow and nano-commit contract

Use the `OPTIMIZATION` flow for every commit and review reference.

A suitable nano-commit sequence is:

1. characterize the central publication boundary and prove which outcomes are real publishes;
2. add the exact process-local revision-ready notification contract;
3. emit only after successful Kernel publication without changing return/error semantics;
4. add the bounded live-server prewarm coordinator and deterministic lifecycle;
5. prove publication/read races, rapid head advance, duplicate signals, failure isolation, and shutdown;
6. add structured observations and live dogfood evidence;
7. complete §8 only after all owning suites are rerun against the merged OPT01 base.

Each commit must tell one implementation or proof story. Do not bundle tracker, roadmap, backlog, report, or broad cleanup changes into this PR.

### Review and document-sync contract

The reviewer must identify the exact PR/branch/head and compare the cumulative diff against the immutable base resolved after PR #509 merges. Review the whole publication → notification → mailbox → current-head check → OPT01 admission → next read sequence, not isolated helper functions.

The review must continue through as many repair cycles as required. Every finding must name the failed invariant clause, affected observable path, owning boundary, and exact proof required.

Roadmap/tracker/status updates are a separate post-merge DOCUMENTS operation. This PR may check in only this handoff plus its implementation/test allowlist.

## §1 Mission and merge-ready invariant

**Mission:** After a successful World Graph publish, the live server can best-effort prewarm that exact committed revision so the next same-process read can reuse verified resident authority without delaying or weakening publication.

**Merge-ready invariant:** Every successful Kernel publication offers one exact process-local notification only after the existing durable commit and Kernel post-publish work; offering never performs graph-scale I/O or changes publication success, the live-server worker processes bounded notifications through the OPT01 verifier, skips revisions no longer named by current head, coalesces with ordinary readers, and reports every ready, superseded, dropped, or failed outcome without treating notification state as graph authority.

### Pre-dispatch critique

| Question | Answer |
| --- | --- |
| Can one invariant govern every claimed observable path? | Yes. Every path concerns whether one already-committed exact revision is offered and optionally admitted without changing durable authority or reader correctness. |
| What adversarial sequence is most likely to falsify it? | Publish A → A notification queues or begins loading → publish B → head becomes B → stale A work resumes and either blocks B, claims A is current, or evicts/overwrites B as the head-following authority. |
| Would the proposed §7 evidence actually detect that failure? | Yes. Barrier-controlled A/B tests require the worker to re-check head, skip queued stale A, admit B, and preserve exact-key OPT01 semantics when A was already in flight. |
| Which owning boundary is easiest to under-test? | The boundary between a committed publish and a failed/slow notification path. A test that only calls the prewarm service would not prove publication returns independently of the worker. |
| What fact would force this slice to stop or split? | Any need for a cross-process/durable event bus, watcher, new route/UI, payload-recipe prewarm, publication response field, contribution semantic change, or correctness dependency on the prewarm completing. |

## §2 Context, authority, and boundaries

| Field | Required content |
| --- | --- |
| Parent authority | `Docs/Design/ARCHITECTURE-campaign-supergraph.md`; `Docs/Roadmaps/ROADMAP-campaign-supergraph.md`; `Docs/Plans/PR-TRACKER-campaign-supergraph.md`; `Docs/Plans/HANDOFF-opt01-resident-verified-world-revision.md`. |
| Repository rules | One world-owned graph; immutable revisions; atomic head advancement; Kernel is the legal graph storage boundary; surfaces never own graph authority; cache/background work is never authority; one slice/one capability. |
| Base revision | Resolve `origin/main` after PR #509 merges. Design inspected against OPT01 head `34b041d91980e1eac1d148b972332e057bdcb92f`. Do not implement on an earlier tree. Candidate dispatch base after merge: `d50d0c3a45761376185d36fb39ae3a098a5b8cfc`. |
| Predecessor contract | OPT01 `WorldReadRuntime`, exact resident key/generation, complete cold admission, coalesced loads, request I/O counters, clear/scrub lifecycle; current Kernel `publish_world_graph_revision`; completed Statblock Workbench publication PR #508. |
| Exact input consumed | The existing successful `WorldGraphPublishResult` plus `root`, `world_id`, and `operation_ids` already known by the Kernel publication facade. |
| Named successor | `OPT03 — bounded serving recipes / surface bootstrap`, which may precompute small surface-specific responses after exact resident readiness. |
| What remains false | No cross-process notification; no startup scan; no guarantee another worker is warm; no completed projection payload is built; no warm guarantee after server restart; no write-path speedup; no delta publication. |
| Explicit non-goals | New route/schema/header; UI status; cache admin panel; filesystem watcher; durable queue; Redis/Postgres/event broker; retry/backoff scheduler; source-index format change; publication protocol change; contribution merge/rebuild semantics; rollback notification; payload cache prefill; Plan/Build/Threat/Hermes caller changes. |

### Authority read order

Read these in order before changing code:

1. `Docs/Design/ARCHITECTURE-campaign-supergraph.md`
2. merged `Docs/Plans/HANDOFF-opt01-resident-verified-world-revision.md`
3. `src/graph_memory/kernel/world_graph.py`
4. `src/graph_memory/world_supergraph/storage.py`
5. `src/graph_memory/kernel/world_read_runtime.py`
6. `src/graph_memory/kernel/__init__.py`
7. `apps/live_control_server/main.py`
8. `src/graph_memory/kernel/contribution_merge.py`
9. `src/graph_memory/kernel/contribution_rebuild.py`
10. `src/graph_memory/kernel/world_initialization.py`
11. `apps/live_control_server/services/graph_review_contribution_merge.py`
12. `apps/live_control_server/services/threat_publication_commits.py`
13. existing publication, runtime, service-lifecycle, and Kernel-boundary tests.

If the base moved, inspect every allowlisted path. If `world_graph.py`, `world_read_runtime.py`, or server lifespan ownership changed materially, stop and report before implementation.

### Current implementation facts this handoff depends on

1. Storage publication validates the full graph, writes `graph.json` and `revision.json`, then atomically replaces `head.json` under a per-world write lock.
2. The Kernel `publish_world_graph_revision` facade delegates to storage, synchronizes identity-decision replay authority, then returns `WorldGraphPublishResult`.
3. Contribution merge, supersession, retraction, rebuild publication, initialization, Graph Review, and Threat publication already converge on Kernel publication rather than needing separate surface hooks.
4. Idempotent contribution reprocessing can return `published=False` without creating a revision; that is not a revision-ready event.
5. OPT01 resident admission is exact-keyed, fully verified, coalesced, generation-bound, and independent of the completed payload cache.
6. The live server already owns long-lived process resources in FastAPI lifespan and performs deterministic shutdown.
7. Threat publication may immediately verify/read the committed revision after merge. That read must be able to coalesce with prewarm rather than causing a second load.

### Central-boundary rule

Emit from the Kernel publication facade only. Do not add notification calls to Graph Review, Threat publication, contribution merge, rebuild, initialization, or routes. Those callers are evidence that one central seam covers multiple publishers; they are not additional ownership points.

The low-level storage module must remain unaware of the live-server runtime. It commits durable bytes and head authority only.

## §3 Observable-path and adversarial-sequence inventory

| Path | Current behavior | Required behavior | Same invariant as §1? | Owning boundary |
| --- | --- | --- | --- | --- |
| Successful baseline/initialization publish | Returns after durable publish; first read cold-loads | Exact revision-ready notification offered after successful Kernel return path; worker may prewarm | Yes | Kernel facade + coordinator |
| Graph Review contribution confirm | Publishes then exact committed read can cold-load | Central notification is offered; exact read and prewarm share one OPT01 load if they race | Yes | Kernel facade + OPT01 coordinator |
| Statblock Workbench Threat confirm | Publishes binding revision, then verification/read can cold-load | Same central notification; no Statblock-specific hook; verification/prewarm coalesce | Yes | Kernel facade + coordinator |
| Rebuild with `publish=True` | Publishes new head; next read cold-loads | Same exact notification and prewarm behavior | Yes | Kernel facade |
| Idempotent merge/no-op | Returns `published=False`, no new revision | No notification, no prewarm, no misleading observation | Yes | Merge result + Kernel facade |
| Validation/stale-parent/revision-exists failure | No successful Kernel publish return | No revision-ready notification | Yes | Kernel facade |
| Kernel post-publish failure before successful return | Existing behavior may raise after storage mutation | Do not invent success or emit a ready notification; ordinary head read remains correctness fallback | Yes | Kernel facade |
| Notification mailbox unavailable/full | Not applicable today | Publication still succeeds; signal is coalesced/dropped with structured observation | Yes | Notification module |
| Coordinator not started / server not running | First read cold-loads | No correctness change; process-local signal may remain bounded or be dropped | Yes | Notification module |
| Prewarm completes before first read | First read performs cold load | First read is resident hit with zero graph-scale durable reads | Yes | Coordinator + OPT01 |
| First read starts before prewarm | Competing cold reads possible without coordination | One shared OPT01 load; reader and worker receive same generation/failure | Yes | OPT01 runtime |
| Duplicate exact notification | Could trigger duplicate work in naive implementation | Resident hit or mailbox coalescing; zero duplicate durable revision load | Yes | Mailbox + OPT01 |
| Rapid A then B publication | First reads cold-load whichever requested | Pending stale A is skipped after current-head check; B becomes warm; no “current” pointer regresses | Yes | Coordinator |
| A already loading when B publishes | A may finish as an exact historical resident | B is subsequently admitted; A never substitutes for B; current-head reads resolve B | Yes | Coordinator + OPT01 |
| Prewarm integrity/I/O failure | First read later discovers failure | Publication stays committed; terminal failure observation; no ready resident inserted | Yes | Coordinator + OPT01 |
| Runtime clear during prewarm | Explicit clear invalidates resident lifecycle | Pre-clear completion cannot repopulate cleared generation; no retry requirement | Yes | OPT01 lifecycle |
| Server shutdown with pending work | No prewarm worker today | Stop accepting, discard pending safely, terminate worker deterministically; no publish/read authority mutation | Yes | FastAPI lifespan + coordinator |
| Browser hard refresh | Server process remains alive; resident survives under OPT01 | No change; prewarmed revision remains available server-side | Yes | OPT01 runtime |
| Server/process restart | Resident and notifications disappear | First read cold-loads correctly; no replay claim | Yes | Process lifecycle |
| Sibling process/worker | No shared process memory | May cold-load independently; no cross-process guarantee | Yes | Explicit scope boundary |

### Ordered adversarial sequences

| Sequence | Required safe outcome | Owning proof |
| --- | --- | --- |
| Publish succeeds → prewarm loader is blocked → publisher returns | Publish result returns before loader release; head/revision are durable; notification work remains background | E3 |
| Publish A → queue A → publish B before A starts → worker takes A | Current-head check sees B and marks A superseded; B is eventually resident | E6 |
| Publish A → worker begins A cold load → publish B → B prewarm begins after A | A may remain exact historical resident; B becomes resident; unpinned context resolves B | E6 |
| Publish revision → ordinary projection starts before worker → both call exact resident key | One manifest/graph/contribution/source-index load; same generation or same failure | E5 |
| Notification offered twice for same revision | At most one cold load; second path is mailbox coalesced or resident hit | E5 |
| Notification offer raises internally / mailbox full | Error is contained; Kernel publication return and head are unchanged | E3/E8 |
| Revision files corrupted after commit but before prewarm | Prewarm fails closed, resident count unchanged, publication remains committed, ordinary read reports existing integrity error | E8 |
| Coordinator shutdown → notification races cleanup | Notification is either accepted before shutdown and terminally handled, or dropped with truthful status; no orphan consumer mutates a new app lifecycle | E7 |
| Runtime clear while worker waits on cold load | Clear epoch isolation wins; stale completion does not become ready; next read follows normal cold path | E7 |

## §4 Files in scope (allowlist)

| Action | Path | Purpose: how this establishes or proves §1 |
| --- | --- | --- |
| Create | `Docs/Plans/HANDOFF-opt02-revision-ready-post-commit-prewarm.md` | Complete design and review authority for this capability. |
| Create | `src/graph_memory/kernel/world_revision_ready.py` | Typed process-local notification and bounded non-blocking mailbox/offer contract. |
| Modify | `src/graph_memory/kernel/world_graph.py` | Offer the exact notification only after successful Kernel publication, without changing durable publish semantics. |
| Modify | `src/graph_memory/kernel/__init__.py` | Export only the typed Kernel notification/consumer boundary needed by the live server and public API tests. |
| Create | `apps/live_control_server/services/world_graph_prewarm.py` | Own one bounded worker, current-head check, OPT01 admission, coalescing behavior, observations, and shutdown. |
| Modify | `apps/live_control_server/main.py` | Start and stop the prewarm coordinator in the existing FastAPI lifespan. |
| Create | `tests/test_graph_kernel_world_revision_ready.py` | Prove exact event mapping, success-only emission, bounded/non-blocking offer, and failure isolation. |
| Create | `tests/test_world_graph_prewarm_service.py` | Prove resident admission, races, stale-head skipping, duplicate events, failure isolation, and worker lifecycle. |
| Modify | `tests/test_graph_kernel_public_api.py` | Prove the intended notification/consumer names are Kernel exports and storage internals are not exposed. |
| Create | `tests/test_live_control_server_lifespan.py` | Prove coordinator start/stop ownership and no leaked consumer across app lifecycles. |

**Bounded discovery exception:** Not applicable. If another path is required, stop and report it rather than adding it silently.

## §5 Files and capabilities explicitly out of scope

| Path, layer, or capability | Why this slice must not touch or claim it |
| --- | --- |
| `src/graph_memory/world_supergraph/storage.py` | Durable commit format and atomic head semantics are predecessor authority; storage must not import runtime notification/prewarm concerns. |
| `src/graph_memory/kernel/contribution_merge.py` | Existing publisher already calls the central Kernel facade; changing merge semantics would cross into write authority. |
| `src/graph_memory/kernel/contribution_rebuild.py` | Same central publication path already covers `publish=True`; no special hook. |
| `src/graph_memory/kernel/world_initialization.py` | Same central publication path; no initialization-specific notification. |
| Graph Review services/routes | No surface-specific hook, response field, retry, or UI. |
| Threat publication services/routes | Completed publication protocol remains unchanged; this PR observes the central Kernel result only. |
| Projection/retrieval request or response models | No public read contract change. |
| `src/graph_memory/world_projection_cache.py` | No completed payload warming or new cache key behavior; OPT01 remains unchanged. |
| Plan / Build / Statblock / Recap / Hermes / Play frontend paths | Existing surfaces are dogfood consumers only. |
| Durable notification/event files | A persistent outbox, event log, queue, or replay cursor is a separate architecture decision. |
| Redis, PostgreSQL, message broker, IPC, sockets | Cross-process delivery is not required for this process-local slice. |
| Filesystem watcher or polling scanner | Notification originates from the successful Kernel call, not out-of-band filesystem observation. |
| Startup scan / warm all heads | OPT02 reacts only to publications observed in the process lifetime. |
| Rollback/head-repoint notification | Rollback is not a newly committed revision and needs a separate head-change contract if later required. |
| Retry/backoff scheduler | A failed prewarm is recorded once; the ordinary reader remains the correctness retry. |
| Resident pinning or eviction-policy redesign | OPT01 LRU/generation semantics remain authoritative. |
| OPT03 serving recipes | No Plan/Build/Threat/Recap query or payload is constructed in the background. |
| OPT04 delta publication | No write/materialization optimization. |
| Roadmap/tracker/backlog/status sync | Separate DOCUMENTS operation after merge. |

## §6 Implementation contract and conditional matrices

### Core contract

```text
Input:
  successful Kernel publish invocation
  root: Path
  world_id: exact durable world ID
  WorldGraphPublishResult:
    head.world_id
    head.head_revision_id
    revision.revision_id
    revision.parent_revision_id
    revision.operation_ids
    revision.created_at

Output:
  one best-effort process-local notification offer
  one terminal prewarm observation when a live-server consumer handles it
  optionally one OPT01 resident generation for the exact notified revision

Invariant:
  notification and prewarm can improve latency but can never alter whether the
  revision is committed, which revision is head, or what an ordinary read returns.

Failure behavior:
  publish failure/no-op → no notification
  notification offer failure/full mailbox → contain and observe; publish succeeds
  stale notification → skip as superseded
  OPT01 admission failure → terminal failed observation; no ready resident
  coordinator absent/shutdown → bounded drop; ordinary read remains correct

Replay / idempotency:
  same exact notification → coalesce, resident hit, or one shared cold load
  newer revision for same world → supersede pending older work
  older notification after head advance → skip before admission
  retry after failed prewarm → ordinary read or a later exact notification may retry

Trust boundary:
  Verifies:
    current head still names the notified revision before proactive admission
    full revision/contribution/provenance/object integrity through OPT01
  Records or trusts without proving:
    operation_ids and created_at are telemetry copied from the successful result
    the notification itself is not durable proof of publication
```

### Publication commit and partial-failure contract

```text
Commit point:
  unchanged storage-level atomic head.json replacement after complete revision write

Before commit:
  no notification exists
  validation/stale-parent/revision-exists failures emit nothing

After storage commit but before successful Kernel return:
  existing Kernel post-publish behavior remains authoritative
  OPT02 does not reinterpret a raised call as successful or emit a ready signal

After successful Kernel return path:
  notification offer occurs before returning, but performs only bounded in-memory work
  notification/prewarm failure cannot change the returned WorldGraphPublishResult

Truthful result after post-commit prewarm failure:
  revision remains committed/head exactly as published
  prewarm observation is failed
  resident is absent unless another reader admitted it
  next read follows normal OPT01 verification and existing error mapping
```

### Notification shape and predecessor mapping

The process-local type is a caller-facing Kernel runtime contract but not a durable schema. Do not serialize it to disk or add it to API responses.

| Predecessor field | Real shape | Notification field / behavior | Transformation | Owning proof |
| --- | --- | --- | --- | --- |
| `root` argument | `Path` | `resolved_root: str` | `str(root.resolve())` before keying | E1 |
| `world_id` argument | exact safe world ID | `world_id` | unchanged; must agree with result head/revision | E1 |
| `result.revision.revision_id` | exact immutable `rev:*` | `revision_id` | unchanged | E1 |
| `result.head.head_revision_id` | exact current head | admission eligibility | must equal notification revision at offer time; worker re-checks later | E1/E6 |
| `result.revision.parent_revision_id` | exact prior head or null | `parent_revision_id` | unchanged telemetry | E1 |
| `result.revision.operation_ids` | ordered list | `operation_ids: tuple[str, ...]` | preserve order; no routing semantics | E1 |
| `result.revision.created_at` | ISO timestamp | `created_at` | unchanged telemetry | E1 |
| successful Kernel return | `WorldGraphPublishResult` | one notification offer | no offer for exceptions/no-op caller results | E2 |
| notification exact key | root/world/revision | OPT01 resident key | no label, operation, surface, or “latest” resolution | E4/E5 |

### Notification/mailbox contract

The implementation may use a queue or latest-by-world mailbox, but all of these properties are mandatory:

1. Offering occurs synchronously on the publisher thread but performs only a short lock/update/notify operation—never revision loading, head I/O, sleeps, thread joins, or callback execution that can block on consumer work.
2. The mailbox is bounded. Saturation or an absent consumer cannot grow memory without limit.
3. Newer pending notifications for the same `(resolved_root, world_id)` may replace older pending notifications.
4. A dropped/replaced notification is observable and never raises through the publisher.
5. There is at most one live-server consumer lease per process. A second coordinator must fail or remain inactive explicitly; it must not split events nondeterministically.
6. The mailbox and consumer state are process-local and cleared or safely detached during tests/shutdown.

### Prewarm coordinator contract

1. One bounded worker owns proactive admission. Do not create a new thread/task per publication.
2. Before loading, open current head through the Kernel and compare exact `world_id` and `head_revision_id` to the notification.
3. If current head differs, mark superseded and perform zero revision/contribution/source-index reads for that notification.
4. If current head matches, call the existing OPT01 exact resident loader. Do not duplicate integrity logic.
5. Use OPT01 coalescing when an ordinary reader or another exact notification is already loading the same key.
6. Do not open/build a projection response or query result.
7. Do not clear an existing resident or payload cache on notification.
8. Shutdown stops intake first, then discards or terminally accounts for pending work and releases the consumer lease. The server must not hang indefinitely on worker shutdown.

### Structured observation contract

Emit structured logs/observations sufficient to reconstruct publication-to-residency behavior without a new API or panel.

Required fields at terminal handling:

* `event = world_graph_post_commit_prewarm`
* `resolved_root`
* `world_id`
* `revision_id`
* `parent_revision_id`
* `operation_ids`
* `status = resident_hit | resident_miss | coalesced | superseded | failed | dropped`
* `queue_wait_ms`
* `prewarm_ms`
* `graph_payload_reads`
* `revision_manifest_reads`
* `contribution_reads`
* `source_index_reads`
* `head_json_reads`
* `resident_generation` (when ready)
* `error_type` / `error_message` (when failed)

Exact field naming may follow repository logging conventions, but the information and stable status vocabulary must be testable. Do not log graph bodies, contribution bodies, source text, or mechanics payloads.

### A. State and fallback matrix

| Observable path | Loading / initializing | Exact success | Ordinary miss | Dependency unavailable | Integrity / contract failure | Stale / superseded | Retry / replay |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Kernel notification offer | bounded mailbox update | accepted/coalesced | mailbox absent/full → dropped | consumer not started → bounded pending/drop | internal offer error contained | newer same-world event may replace pending | later exact publish or ordinary read |
| Worker current-head check | one `head.json` read | head matches revision | head absent → failed/unavailable observation | head I/O unavailable → failed | malformed/mismatched head → failed | head names another revision → superseded | later event/read |
| OPT01 prewarm admission | existing exact loader | ready generation | exact revision missing → failed | durable I/O error → failed | integrity error → failed closed | clear epoch may invalidate completion | ordinary read or later exact signal |
| Ordinary read racing prewarm | resolve normal request | same generation/result | no resident → joins/starts cold load | existing service error | existing fail-closed error | head resolution chooses exact current head | existing request retry |
| Shutdown | stop intake | worker stopped/lease released | pending dropped | join timeout observed | no authority mutation | late signals dropped | new app lifecycle starts fresh |

No fallback source is permitted. Ordinary reads do not trust notification state; they continue to observe `head.json` and exact revision authority under OPT01.

### B. Identity matrix

| Situation | Required rule | Ambiguity behavior | Fallback permitted? |
| --- | --- | --- | --- |
| Exact resident identity | `(resolved_root, world_id, revision_id)` only | none; all three must match | No |
| World/head identity | notification world must equal result/head world; worker head world must equal notification world | mismatch is integrity/failure | No |
| Operation IDs | telemetry only; never choose resident or surface behavior | duplicates/order preserved as received | No |
| Labels, campaign IDs, surface names | not part of notification identity | prohibited for routing | No |
| “Latest” revision | prohibited | worker reads exact current head and compares | No |
| Rename/rebind | not applicable to revision identity | exact immutable revision IDs remain stable | No |

### C. Persistence and replay matrix

| Operation | Durable representation | Round-trip guarantee | Duplicate / replay behavior | Compatibility / migration | Rollback / reversion |
| --- | --- | --- | --- | --- | --- |
| Publish notification | none | none across restart | bounded coalescing/hit in same process | no migration | removing OPT02 restores cold-on-read behavior |
| Pending mailbox | none | lost on process restart | same-world newest may supersede pending old | no compatibility promise | shutdown discards safely |
| Resident result | existing OPT01 process memory | exact revision model equality | duplicate exact load coalesces/hits | OPT01 contract | clear/restart removes |
| Structured logs | normal process logs only | observational, not replay authority | duplicate statuses allowed only when tied to distinct handling attempts | repository log conventions | no state rollback needed |

### D. Predecessor-to-consumer mapping

Grounding sources: merged OPT01 runtime types and counters; `WorldGraphPublishResult`; FastAPI lifespan; completed Graph Review and Threat publication flows.

| Predecessor field / outcome | Real shape and optionality | Consumer field / behavior | Transformation | Proof fixture/test |
| --- | --- | --- | --- | --- |
| `WorldGraphPublishResult.revision` | required on successful publish | exact notification | field-preserving mapping | `test_successful_publish_offers_exact_notification` |
| publish exception | raised; no successful result | no notification | no catch/relabel as success | failed/stale tests |
| merge `published=False` | service-level no-op, no Kernel publish | no notification | none | idempotent merge integration test |
| `get_world_read_runtime().get_or_load_resident` | sync exact loader, coalesced | worker admission | invoke existing API only | prewarm service tests |
| OPT01 request I/O counters | context-local counts/status/timing | terminal observation | worker establishes and resets its own counter context | observation tests |
| FastAPI lifespan | one app process lifecycle | coordinator start/stop | register before yield; unregister/shutdown in finally | lifespan test |
| Threat publish exact revision | commit ledger/revision result | dogfood correlation | compare exact revision ID to prewarm logs and surface reads | E10 |

## §7 Evidence required to merge

| ID | Guarantee / invariant clause | Owning boundary | Evidence class | Command or manual scenario | Expected evidence | Stop condition |
| --- | --- | --- | --- | --- | --- | --- |
| E1 | Successful Kernel publish offers one exact mapped notification | Kernel facade/notification type | Contract | Publish baseline and contribution revision with captured mailbox | Exact root/world/revision/parent/operation/timestamp; offer after Kernel post-publish work | Wrong identity, early offer, duplicate offer |
| E2 | Failed/no-op paths offer nothing | Kernel facade + merge integration | Adversarial/regression | Validation failure, stale parent, revision exists, idempotent merge | Zero notifications | Any false-ready signal |
| E3 | Publication never waits for or fails because of prewarm | Kernel facade/mailbox | Barrier/failure injection | Block worker load; fill/fail mailbox; publish | Publish returns exact result before loader release; head remains committed | Worker I/O on publisher thread or publication error changes |
| E4 | Matching notification produces an OPT01-verified resident | Coordinator + runtime | Integration | Publish, consume event, wait idle, resolve resident/read | Exact generation ready; one cold batch; subsequent read zero graph-scale I/O | Unverified/custom loader, wrong revision, duplicate reads |
| E5 | Ordinary reader and duplicate signal coalesce | OPT01 runtime + coordinator | Concurrency | Barrier-controlled reader/prewarm race; repeated event | One cold load; same generation/failure; duplicate is hit/coalesced | Two cold loads or divergent result |
| E6 | Rapid head advance cannot prewarm stale authority as current | Coordinator | Ordered adversarial | Queue/block A, publish B, release; test A queued and A in-flight variants | Queued A superseded with zero A durable reads; B resident; unpinned read B | A substituted for B, B starved, global current regression |
| E7 | Worker lifecycle and clear/shutdown are safe | Lifespan + OPT01 lifecycle | Concurrency/lifecycle | App start/stop, late event, clear during load, second app lifecycle | One consumer, no leaked worker, stale completion not ready, new lifecycle clean | Hang, leaked consumer, post-shutdown mutation |
| E8 | Prewarm failure never changes committed authority | Coordinator + Kernel/storage | Failure injection | Corrupt/missing revision after commit; force loader error | Publish/head unchanged; failed observation; no resident; ordinary read existing error | Rollback, swallowed integrity, false ready |
| E9 | Kernel/storage and public contracts remain bounded | Boundary/public API | Regression/static | Public API + boundary suites + focused diff | No app import of storage; no storage import of runtime; no route/schema change | New exemption, storage/runtime cycle, outside path |
| E10 | Completed human Threat publication is warm across existing surfaces | Live Workbench/Plan/Build/Threat/Hermes | Manual dogfood | Publish accepted Threat → exact revision → Plan → Build graph read → Threat/Hermes read → hard refresh | One total cold admission for new revision (prewarm or coalesced verifier); later same-revision reads zero graph/manifest/contribution/source-index reads | Needs UI change, duplicate cold loads, wrong revision, no terminal observation |

### Required commands

Resolve `<BASE>` to the immutable main SHA containing merged OPT01 before running:

```bash
uv run pytest \
  tests/test_graph_kernel_world_revision_ready.py \
  tests/test_graph_kernel_public_api.py -q

uv run pytest \
  tests/test_world_graph_prewarm_service.py \
  tests/test_live_control_server_lifespan.py \
  tests/test_graph_kernel_world_read_runtime.py \
  tests/test_world_graph_projection_service.py -q

uv run pytest \
  tests/test_graph_kernel_contribution_merge.py \
  tests/test_graph_review_contribution_merge_seam.py \
  tests/test_threat_publication_commits.py \
  tests/test_graph_kernel_world_initialization.py \
  tests/test_graph_kernel_contribution_rebuild.py -q

uv run pytest \
  tests/test_world_graph_projection_routes.py \
  tests/test_world_graph_recap_projection.py \
  tests/test_graph_kernel_world_projection.py \
  tests/test_graph_kernel_world_retrieval.py \
  tests/test_graph_kernel_boundaries.py -q

uv run ruff check \
  src/graph_memory/kernel/world_revision_ready.py \
  src/graph_memory/kernel/world_graph.py \
  src/graph_memory/kernel/__init__.py \
  apps/live_control_server/services/world_graph_prewarm.py \
  apps/live_control_server/main.py \
  tests/test_graph_kernel_world_revision_ready.py \
  tests/test_world_graph_prewarm_service.py \
  tests/test_graph_kernel_public_api.py \
  tests/test_live_control_server_lifespan.py

git diff --check

git diff --stat <BASE>...HEAD -- \
  Docs/Plans/HANDOFF-opt02-revision-ready-post-commit-prewarm.md \
  src/graph_memory/kernel/world_revision_ready.py \
  src/graph_memory/kernel/world_graph.py \
  src/graph_memory/kernel/__init__.py \
  apps/live_control_server/services/world_graph_prewarm.py \
  apps/live_control_server/main.py \
  tests/test_graph_kernel_world_revision_ready.py \
  tests/test_world_graph_prewarm_service.py \
  tests/test_graph_kernel_public_api.py \
  tests/test_live_control_server_lifespan.py

git diff --name-only <BASE>...HEAD
```

Also run repository-wide checks when practical:

```bash
uv run ruff check .
uv run pytest tests/ --maxfail=1
```

Repository-wide failures do not become green by assertion. Apply the baseline failure protocol.

### Deterministic prewarm/read table required in the handback

Record actual values from tests or dogfood:

| Scenario | Notification status | Head reads | Graph | Manifest | Contributions | Source indexes | First surface read |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Publish with worker, no competing read | TODO | TODO | TODO | TODO | TODO | TODO | resident hit |
| Publish + ordinary read races worker | TODO | TODO | TODO | TODO | TODO | TODO | coalesced/miss but one total batch |
| Duplicate exact notification | TODO | TODO | 0 | 0 | 0 | 0 | resident hit |
| A pending, B becomes head | A superseded / B ready | TODO | A=0; B=TODO | A=0; B=TODO | A=0; B=TODO | A=0; B=TODO | B hit |
| Prewarm failure | failed | TODO | TODO | TODO | TODO | TODO | ordinary exact failure/retry behavior |
| Server restart before any new publish | no event | normal | cold on first read | cold | cold | cold as applicable | correct cold path |

### Minimal live / dogfood proof

```text
Existing surfaces used:
  Statblock Workbench publication, Plan, Build graph reference/search, existing
  Threat/Hermes read path. No new UI or instrumentation panel.

Smallest realistic scenario:
  1. Start one live-server process against Eldyrwild with an empty OPT01 runtime.
  2. Publish one accepted Threat/statblock binding through the completed Workbench flow.
  3. Capture the exact committed world/revision from the publication outcome.
  4. Capture the matching revision-ready and terminal prewarm observations.
  5. Open/read the committed Threat in Plan.
  6. Navigate to Build and perform an existing graph object search/open.
  7. Use the existing Threat/Hermes read/query path.
  8. Hard-refresh the browser without restarting the server and repeat one read.

Expected observation:
  The newly committed exact revision incurs one total resident cold admission in
  the process. It may be owned by prewarm or coalesced with immediate publication
  verification/first read, but it must not happen twice. Every later same-revision
  request reports resident hit and zero graph/revision/contribution/source-index
  reads. All responses name the exact committed/head revision.

Evidence captured:
  Publication result/receipt revision ID; structured notification/prewarm log rows;
  service projection observations for Plan/Build/Threat/Hermes; compact stage timing
  and I/O table. Timing is characterization, not a universal latency claim.
```

If the live proof requires changing a surface, adding a route/header/panel, or changing publication responses, stop and return for split review.

### Baseline failure protocol

For every required command already failing on `<BASE>`:

1. run the identical command on base and head when possible;
2. record exact failing test names and counts;
3. state whether head adds failures;
4. do not call the command green;
5. name an explicit operator waiver only if the failure remains an acceptance gate.

Known historical failures are not automatically accepted. Re-establish the base result after PR #509 merges.

## §8 Required review handback

The Optimization Coding Agent must return:

1. Exact PR URL or branch/head SHA.
2. Immutable base SHA containing merged OPT01 and the PR #509 merge/acceptance reference.
3. The §1 Mission and merge-ready invariant copied exactly.
4. Complete §7 evidence ledger with produced result and provenance.
5. Nano-commit list and one discrete implementation/proof story per commit.
6. Actual changed paths and focused diff stat limited to §4.
7. Every required command and exact result.
8. Base/head comparison for every failing gate.
9. Public Kernel notification type/API names and exact field mapping.
10. Mailbox structure, capacity/bounding rule, same-world coalescing/drop rule, and consumer lease model.
11. Coordinator lifecycle: startup, intake, worker count, current-head check, admission call, shutdown, and late-event behavior.
12. Exact publication emission point relative to storage publish, identity-decision sync, and Kernel return.
13. Proof that failed/no-op/stale publications emit no notification.
14. Proof that notification/mailbox/worker failure cannot change publication return or durable head.
15. Barrier evidence for reader/prewarm coalescing and rapid A→B publication.
16. Deterministic table from §7, including total cold-load counts—not only per-caller counters.
17. Structured observation examples for ready, superseded, failed, and dropped states, with no graph/source/mechanics bodies.
18. E10 live dogfood result or explicit operator waiver.
19. Confirmation that no route/schema/UI, durable format, contribution/publication semantic, payload recipe, or cross-process contract changed.
20. Paths outside §4 and stop conditions; write none when none exist.
21. Successors still false:
    * no bounded surface recipe prewarm;
    * no cross-process/durable event delivery;
    * no startup head scan;
    * no delta-aware publication/materialization.
22. Confirmation that the authoritative handoff was implemented without compressed or omitted constraints.

## §9 Acceptance rubric

The reviewer accepts only when every bullet is true:

* Exactly one independently useful capability was delivered: best-effort resident prewarm after successful commit.
* PR #509 / OPT01 is merged and accepted or explicitly waived at its remaining live gate.
* Notification is emitted only from the central Kernel publication facade.
* Storage commit semantics and publication return/error contracts are unchanged.
* Successful publish maps to one exact root/world/revision notification — E1.
* Failed, stale, revision-exists, and no-op paths emit none — E2.
* Publisher performs no graph-scale prewarm work and cannot fail because of notification/worker behavior — E3.
* Matching current-head notification admits through the complete OPT01 verifier — E4.
* Reader races and duplicate signals produce one total cold load — E5.
* Rapid A→B publication cannot make A the head-following warm authority or starve B — E6.
* Coordinator startup/shutdown, clear races, and consumer ownership are deterministic — E7.
* Prewarm failure leaves the committed revision/head untouched and no false resident ready — E8.
* Kernel remains the sole legal graph storage boundary; storage does not import runtime/app layers — E9.
* Completed Workbench → Plan → Build → Threat/Hermes → hard-refresh proof passes or has an explicit operator waiver — E10.
* No public route/request/response schema or surface consumer changed.
* No durable event/queue, filesystem watcher, multi-process delivery, or startup scan was introduced.
* No projection payload recipe was built or warmed.
* No contribution, identity, publication, or durable graph semantics changed.
* Every changed path is in §4.
* Every required proof has exact result/provenance and baseline failures are reported truthfully.
* No universal latency claim is based on local timing alone.
* OPT03/OPT04 remain unimplemented and unclaimed.

## Stop conditions

Stop and report rather than expanding if implementation discovers:

* the live server uses multiple processes and product acceptance requires all workers warm;
* the Kernel facade cannot emit after successful publication without changing existing error/partial-durability semantics;
* a production publisher bypasses the Kernel facade and must be modified separately;
* notification requires a durable outbox, replay cursor, watcher, IPC, broker, Redis, or PostgreSQL;
* publication must wait for resident admission to be considered successful;
* a new route, response field/header, UI indicator, admin panel, CLI, or operator control is required;
* a projection payload or surface-specific recipe must be constructed for useful value;
* prewarm needs to mutate contribution/publication records or graph bytes;
* rollback/head repoint must share the same signal for correctness;
* OPT01 exact admission/coalescing cannot be reused as-is;
* deterministic tests cannot prove one total cold batch across reader/prewarm races;
* a path outside §4 is required;
* the base moved and an allowlisted path changed materially;
* any acceptance proof requires changing a product surface.

Use this report shape:

```text
Stop condition:
Why the current mission cannot absorb it:
Invariant clause affected:
Required evidence now missing:
New public/durable contract discovered:
Affected observable paths or ownership layers:
Proposed successor slice:
Tracker or authority update needed:
```

## Design-agent dispatch note

OPT02 is successful when publication can hand the newly committed exact revision to OPT01 early and safely. It is not required to make the whole surface instant. Resident admission may still be CPU/I/O heavy once per revision; broad projection construction, serialization, payload size, and surface-specific query costs remain visible. Those measurements determine OPT03.

Do not hide a second capability inside “prewarm.” In particular, do not build Plan, Build, Recap, Threat, or Hermes responses in the worker. Warm the verified revision only.

## §8 Coding-agent review handback (filled)

**Dispatch note:** Operator dispatched implementation while OPT01 E10 remained NOT PROVEN / unwaved. OPT02 E10 likewise remains NOT PROVEN pending live Workbench dogfood or an explicit operator waiver.

1. **PR / branch / head:** https://github.com/Drakosfire/DungeonMindBuddy/pull/511 ; branch `opt/opt02-revision-ready-post-commit-prewarm`; head `2f0fd592c0ded8fbe6f6545f54d937c686929240`.
2. **Immutable base:** `d50d0c3a45761376185d36fb39ae3a098a5b8cfc` (merge of PR #509 / OPT01 onto main). Design anchor tip `34b041d91980e1eac1d148b972332e057bdcb92f` is an ancestor of this base.
3. **§1 Mission (exact):** After a successful World Graph publish, the live server can best-effort prewarm that exact committed revision so the next same-process read can reuse verified resident authority without delaying or weakening publication.
4. **§1 Merge-ready invariant (exact):** Every successful Kernel publication offers one exact process-local notification only after the existing durable commit and Kernel post-publish work; offering never performs graph-scale I/O or changes publication success, the live-server worker processes bounded notifications through the OPT01 verifier, skips revisions no longer named by current head, coalesces with ordinary readers, and reports every ready, superseded, dropped, or failed outcome without treating notification state as graph authority.
5. **§7 evidence ledger**

| ID | Result | Provenance |
| --- | --- | --- |
| E1 | PASS — exact mapped notification after successful Kernel publish | `tests/test_graph_kernel_world_revision_ready.py` |
| E2 | PASS — stale-parent failure emits no offer observations | same module |
| E3 | PASS — publish returns while offer blocked; mailbox/offer failures contained | same module |
| E4 | PASS — coordinator admits via OPT01; second load zero durable reads | `tests/test_world_graph_prewarm_service.py` |
| E5 | PASS — reader/prewarm share one `_cold_load`; duplicate notification `resident_hit` with zero reads | same module |
| E6 | PASS — latest-by-world keeps B; A not admitted as head-following warm authority | same module |
| E7 | PASS — lifespan start/stop + consumer lease; clear during gated prewarm | `tests/test_live_control_server_lifespan.py` + prewarm clear test |
| E8 | PASS — corrupt graph after commit → failed observation; head unchanged; resident_count 0 | prewarm service |
| E9 | PASS for OPT02 scope — public API exports; `world_revision_ready` does not import storage; no route/schema change | public API + focused diff |
| E10 | NOT PROVEN — live Publish accepted Threat → Plan → Build → Threat/Hermes → hard refresh not run; no operator waiver | deferred |

6. **Nano-commits:** discrete stories for handoff, notification mailbox, Kernel emit, prewarm+lifespan, owning tests, §8 sync (see `git log`).
7. **Changed paths:** exactly the §4 allowlist (10 paths).
8. **Required commands / results (base `d50d0c3a`)**
   - revision_ready + public_api → included in **18 passed** owning set
   - prewarm + lifespan + OPT01 runtime/service → **37 passed**
   - contribution merge / Graph Review seam / Threat commits / initialization / rebuild → **133 passed**
   - routes + recap + projection + retrieval + boundaries → **167 passed, 6 failed** (all six pre-existing on `d50d0c3a`: multi-source retract, recap compatibility, retrieval heading digest, three boundary tests)
   - scoped ruff → **All checks passed!**
   - `git diff --check` → clean
9. **Result provenance:** independently rerun local after implementation.
10. **Base/head failing gates:** identical pre-existing six failures; head adds none among required owning tests.
11. **Public Kernel notification API**
    - Types: `WorldRevisionReadyNotification`, `RevisionReadyOfferResult`, `RevisionReadyMailbox`, `RevisionReadyConsumerLease`
    - Functions: `offer_revision_ready`, `offer_revision_ready_from_publish`, `notification_from_publish_result`, `get_revision_ready_mailbox`, `reset_revision_ready_mailbox`, offer observation helpers
    - Field mapping: `resolved_root=str(root.resolve())`, `world_id`, `revision_id`, `parent_revision_id`, `operation_ids` (tuple), `created_at`; require head.revision_id == published revision at mapping time
12. **Mailbox:** latest-by-`(resolved_root, world_id)` `OrderedDict`; default capacity 64 (`DMB_WORLD_GRAPH_REVISION_READY_MAILBOX_CAPACITY`); same-world replace → `coalesced`; saturation of distinct keys → `dropped`; exclusive consumer lease (second acquire fails).
13. **Coordinator lifecycle:** `start_world_graph_prewarm_coordinator` acquires lease + one daemon worker; intake via mailbox; current-head via `open_world_graph_head`; admission via `get_or_load_resident`; `stop` closes mailbox (pending → dropped observations), joins worker, releases lease, resets mailbox for next lifecycle. FastAPI lifespan starts before yield and stops in `finally` before Hermes shutdown.
14. **Emission point:** after storage publish return **and** `sync_identity_decisions_from_store`, immediately before returning `WorldGraphPublishResult`. Contained; never alters result.
15. **No notification for:** publish exceptions / stale parent / no successful Kernel return. Idempotent merge `published=False` never reaches Kernel publish.
16. **Failure isolation:** blocked/raising offer cannot change publish return or durable head (E3/E8 proofs).
17. **Barrier evidence:** gated `_cold_load` proves one cold load for reader+worker; A/B latest-by-world proves stale A not head-following.
18. **Deterministic prewarm/read table (local fixture world)**

| Scenario | Notification status | Head reads | Graph | Manifest | Contributions | Source indexes | First surface read |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Publish with worker, no competing read | resident_miss (cold admit) | 1 | ≥1 | ≥1 | ≥1 | 0 | subsequent get_or_load hit / 0 durable |
| Publish + ordinary read races worker | coalesced/miss shared | — | one `_cold_load` total | one | one | — | same generation |
| Duplicate exact notification | resident_hit | 1 | 0 | 0 | 0 | 0 | resident hit |
| A pending, B becomes head | B resident_miss; A absent or superseded | B:1 | A=0; B cold once | A=0; B cold | A=0; B cold | A=0 | B hit |
| Prewarm failure | failed | 1 | — | — | — | — | ordinary exact failure; head unchanged |
| Server restart before any new publish | no event | normal | cold on first read | cold | cold | as applicable | correct cold path |

19. **Structured observation examples:** `event=world_graph_post_commit_prewarm` with statuses `resident_miss`, `resident_hit`, `coalesced`, `superseded`, `failed`, `dropped`; offer side uses `world_graph_revision_ready_offer`. No graph/contribution/source bodies logged.
20. **E10:** NOT PROVEN — requires live Workbench → Plan → Build → Threat/Hermes → hard refresh, or operator waiver.
21. **Public/durable confirmation:** no route/schema/UI, durable format, contribution/publication semantic, payload recipe, or cross-process contract changed.
22. **Paths outside §4:** none.
23. **Stop conditions:** none.
24. **Successors still false:** no bounded surface recipe prewarm; no cross-process/durable event delivery; no startup head scan; no delta-aware publication/materialization.
25. **Authority confirmation:** authoritative handoff implemented without compressed or omitted constraints; OPT01 E10 gate was open at dispatch per operator instruction and remains recorded honestly for OPT02 acceptance.
