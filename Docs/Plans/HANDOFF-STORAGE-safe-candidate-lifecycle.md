# HANDOFF — Safe candidate lifecycle tooling

**Created:** 2026-11-09
**Status:** BLOCKED — publication approval denied; no effective write lease or dispatch
**Flow / owner:** STORAGE / coordinator stewardship
**Implementation owner:** task `01a1c171-e939-700d-87a6-d289ba3d1033`
**Design authority base:** `51c961d39602710cef7e093720852570f4194f0e`
**Handoff locator:** this path at the immutable stewardship commit supplied with dispatch; steward publishes the branch before dispatch.
**Activation gate:** obtain explicit approval for publishing this stewardship branch to `Drakosfire/DungeonMindBuddy`, publish the pinned contract, refresh collision preflight, then steward records ACTIVE. Automatic approval review rejected the attempted push as insufficiently authorized; no push executed. No runtime readiness dependency.
**PR topology:** serial — one open STORAGE implementation PR maximum. Recovery and existing product/CI work are nonconflicting context through disjoint new files and fixture-only runtime ownership; this lane has no unmerged behavioral dependency on them.
**PR authorization:** open/update exactly one `STORAGE: bound candidate allocation and cleanup` implementation PR; no merge, deployment, scheduler installation, live invocation, or successor PR is authorized.

## §1 Mission and merge-ready invariant

Deliver an independently usable, opt-in CLI that bounds new candidate allocations and plans/removes only explicitly approved disposable candidates under a verified Projects Buddy root. This is tooling preparation, not completion of live recurrence prevention.

Invariant: every data mutation stays within a positively identified, exclusively owned disposable candidate on the expected Projects filesystem; control-metadata writes are confined to the explicitly defined protected control subtree; active/recovery/release/backup/evidence/unknown data remains protected; missing or stale protection, mount, capacity, ownership or journal evidence fails closed.

Critique: a stale cleanup plan followed by a new process reference, symlink swap, mount change or interrupted delete is the primary adversarial sequence. Proof belongs at the CLI/filesystem/process boundary, not just pure selector helpers. Real allocator integration remains false and is explicitly separated below.

## §2 Authority, topology and ownership

Current remote main was fetched at design time. Its AGENTS.md supersedes dirty-checkout policy and legacy Cursor gates: portable pinned authority is permitted; a worker must not author its own authority. This is a steward-authored contract intended for publication separately from implementation; publication is currently blocked. No tracked preventive tooling is changed by the steward.

Concurrent owners checked: recovery task `01a1c166-361d-76b6-8262-4cf2ca9d100f` and PRIME own old home runtime restoration; this lane has no access lease to those files, services or ports. Open PR metadata was read on 2026-11-09: no STORAGE PR; unrelated CI, retrieval, ingest, surface and deployment drafts remain outside this new-file lease. Local worktrees were inventoried; no existing lane owns the three new implementation paths below. Run current collision preflight again before implementation.

| Field | Value |
|---|---|
| Branch / isolated checkout | `codex/storage-safe-candidate-lifecycle`, task-owned Projects checkout allocated after publication |
| Runtime/state ownership | Synthetic task-owned fixture roots only; no ports, services, operational root or live data lease |

Implementation branch: `codex/storage-safe-candidate-lifecycle`. Allocate an isolated checkout beneath the task-owned Projects `.codex` root from the published handoff commit, recording exact base and checkout path in PR evidence. Never use dirty main or the steward checkout for implementation. Do not allocate before publication.

State-authority sync set after merge: this handoff only, updated by steward after exact-head review and authorized merge; implementation may report evidence in the PR but may not activate or redesign its authority.

Named successor: identify and adopt the actual operational allocator, then independently review activation/cutover and recurrence proof. No successor PR or live activation is authorized here. Recovery remains separate.

### Read-only allocator investigation: evidence and limits

- Running API PID 2843896 named `/home/drakosfire/.local/state/dungeonmindbuddy/runtime/launch_api.py`; that launcher is absent on current filesystem. Running UI PID 2843974 named a dependency beneath `nonlive-graph-review-ec1da1b`. These are recovery evidence, not allocator proof.
- Existing inventory `/media/drakosfire/Projects/.codex/2026-11-09/task-4/rollout-candidate-sizes.csv` records actual accumulated directories beneath the old home `rollout-candidates` root, including `buddy-main-a044ac4e` and many `buddy-api-*` entries. It does not identify their producer.
- `/home/drakosfire/Projects/.codex/buddy-benchmark-baseline/prepare_corpus_parent_v1.py:19` and `prepare_receipt_order_v1.py:19` reference delivered candidate source trees. Their allocation statements create benchmark bundles/cohorts elsewhere. They are consumers, not proven rollout allocators.
- Focused tracked-script, retained launcher, local-state script, task-owned script, Cursor transcript/tool and transient service inspection found no surviving source that allocates the accumulated rollout directories. No allocator path is guessed or leased. Its identity is a genuine remaining blocker for operational recurrence prevention. Do not claim integration or root-cause closure.

## §3 Observable paths

Required CLI paths: inventory; allocation refusal/success; default dry-run cleanup plan; explicit apply of exact plan; repeated apply; interrupted allocation/deletion recovery; competing allocator/cleaner; stale references, lease and plan; absent/wrong mount; insufficient byte/inode headroom; symlink/hardlink/mount escape; incomplete process visibility; unknown data.

Every path must preserve §1. Unknown state reports protected with a reason. No automatic repair or fallback path is permitted.

## §4 Files in scope — write lease

| Action | Path | Purpose |
|---|---|---|
| Create | `scripts/buddy_storage.py` | One standalone standard-library storage lifecycle CLI |
| Create | `tests/test_buddy_storage.py` | CLI/filesystem adversarial and crash/concurrency evidence |
| Create | `Docs/Guides/GUIDE-buddy-storage.md` | Exact CLI contract, retention, limitations and separate activation gate |

This table is prospective only while BLOCKED; it grants no effective write lease.

Bounded discovery exception: none. Changes outside these exact paths return to steward. No dependency/lockfile/config change is authorized. Steward alone owns this handoff.

## §5 Explicit exclusions

| Path | Reason |
|---|---|
| `AGENTS.md` | Shared policy; current dirty checkout is preserved |
| `.cursor/**` | No process-policy rewrite |
| `scripts/*` other than §4 | No unproven allocator/launcher changes |
| `/home/drakosfire/.local/state/dungeonmindbuddy/**` | Recovery ownership; read-only evidence only |
| `/media/drakosfire/Projects/.buddy/**` | Intended operational topology only; no creation, cleanup, relocation or activation in this implementation task |
| `runtime/**`, `releases/**`, `backups/**`, `evidence/**` under any state root | Never candidate cleanup targets |
| `corpus/**`, `out/**`, databases, service definitions, credentials | No product state, live data or runtime lease |

No communication with PRIME or external agents. No runtime restart, mount/security/global environment change, deployment, timer/cron installation or blanket deletion.

## §6 Implementation contract

Intended operational root: explicit Buddy-specific configuration under `/media/drakosfire/Projects/.buddy`, resolving to filesystem UUID `48fa5d10-fe99-4557-9fc9-d8a2a4b41ac8`. Never globally change XDG_STATE_HOME. Absent/inaccessible/wrong UUID is a hard stop, with no home or /tmp fallback. Do not create the operational root in this slice.

Topology: `runtime/` is protected current API/UI/config; `releases/` protects current and one operator-verified rollback; `candidates/` is the only disposable lifecycle boundary; `backups/` and `evidence/` are explicitly retained, separately protected classes. Existing task worktrees/scratch/cache remain under task-owned Projects `.codex`; no migration or additional generic cleanup categories.

Control topology inside `candidates/.control/`: `lifecycle.lock`, `journal/<operation-id>.json`, and `quarantine/<candidate-id>/`. This subtree is protected and never itself a cleanup candidate. Normal apply/allocation may create/update only these metadata paths plus the manifest and bounded contents of an owned candidate; inventory/dry-run may create nothing. Compact plan/result output goes to stdout by default; retaining it under operational `evidence/` requires a separate operator action, not this CLI deletion flow. Journals retain only compact identities/results; no credential contents. Unknown existing control state blocks mutation.

New candidates reference an immutable Git commit and isolated source checkout plus bounded build output; no full source/corpus/image/evaluation/runtime-environment copy per candidate. Allocation takes explicit owner, expiry, planned bytes/inodes and configured maximum candidate count/aggregate bytes/age. Reject missing limits. Check projected usage and reserve at least max(10 GiB, 15 percent filesystem capacity) plus planned allocation, and at least 10 percent free inodes after projected use; expose stricter configured reserves. Refuse before allocating if unknown/insufficient. Recheck under a single root-scoped allocator/cleaner lock; use exclusive create and fail closed when lock is busy. Recheck actual growth before candidate completion; failed allocation remains explicitly incomplete/protected until reconciled.

Candidate retention: eligibility requires both explicit expired TTL and completed, reproducible, manifest-owned disposable status; count/byte pressure never overrides protection. No deletion purely by age/name. Inventory category, allocated/apparent bytes, age, owner, state, live/rollback/task protection and reason. Warn before reserve/budget exhaustion; allocation refuses beyond limits. Do not silently evict to make room.

Evidence retention: compact manifests, plans, operation journals and results retained without automatic deletion in this slice. No full trees or credential values. Backups: all retained indefinitely until a separately approved exact backup-retention action; never inferred disposable. Releases: current and verified rollback always retained; unknown/unverified releases retained; no release deletion here. A future different retention policy requires separate steward scope.

Dry-run is default and has no filesystem mutations (including no mkdir or new lock file for read-only inventory). Apply requires explicit command, exact plan digest and item identity allowlist. Plans bind root device/UUID, candidate inode/device, manifest hash, protection snapshot, generation and expiry. Revalidate every binding, descendant containment, active task/process/open-file/cwd/executable/service/rollback references and mount topology immediately before any destructive step under lock; inaccessible observation blocks apply. Refuse symlinks, unexpected hardlinks, nested mounts, unknown files, dirty/unique source data, DB dumps/config/secrets, stale/unknown leases and process references. A manifest assertion alone is not sufficient proof that data is disposable. Live references always beat deletion approval. Process scanning is only supplementary observation, not synchronization: a root lock cannot stop an uncooperative consumer opening a path. Destructive apply therefore additionally requires a sealed candidate and an authoritative consumer-reference lease protocol covering all consumers, with reference acquisition serialized under the same lock and new acquisitions forbidden once sealed/quarantined. Missing/unproven protocol coverage or any legacy consumer blocks destructive apply. This slice may implement the protocol within the standalone CLI and synthetic cooperating test consumers, but cannot assert operational coverage. The future allocator/consumer integration and activation review must establish that coverage before any real apply is possible. Do not offer a force/waiver flag. Test a consumer attempting reference acquisition during deletion and prove refusal; test a legacy/uncooperative/unknown consumer and prove apply is blocked.

Crash safety: use atomic write/fsync/rename journals and same-filesystem quarantine for approved disposable objects; record pending before transition, commit result after durable completion. Do not follow links during recursive removal; operate relative to held directory descriptors, checking identities/mounts to avoid TOCTOU escapes. Quarantine is not retention expiry: keep prior protection and revalidate before deletion. Interrupted/uncertain state reports pending/protected and requires safe reconciliation; replay never widens the allowlist or reports deletion before actual completion. Preserve compact failure evidence without secrets. Define precise commit points and per-item partial outcomes in guide and tests.

Fixture support: inject filesystem identity/capacity/process-observation adapters only through explicit test seams; production invocation must never accept a bypass flag or arbitrary UUID override. All implementation verification uses synthetic task-owned fixture roots, no live root. No real DB/network/provider calls.

## §7 Evidence required to merge

Prove at CLI boundary that default plan does not mutate; only exact allowlist applies; live/unknown/backups/evidence/rollback/dirty data is retained; missing/wrong mount and low projected bytes/inodes reject; failed allocation does not leak an eligible candidate; crash/replay records truthful state; concurrent lock excludes allocation/cleanup races; symlink/hardlink/nested-mount and stale-plan changes cannot escape. Include fault injection before/after quarantine rename, journal commit, partial removal and fsync error. Test process-reference changes between plan/apply and during apply, plus incomplete observation.

Exact commands from isolated implementation checkout:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p test_buddy_storage.py -v
python3 scripts/buddy_storage.py --help
git diff --check
git diff --name-only 51c961d39602710cef7e093720852570f4194f0e...HEAD
```

Tests must use unittest-compatible discovery and leave outputs solely in task-owned fixture scratch on Projects. Record actual commands, exact SHA, OS/Python, fixture mount identity, failures and cleanup inventory. Independently rerun the focused CLI evidence at exact implementation head before approval. No live dogfood is authorized; missing operational integration proof stays explicit.

## §8 Required handback

Exact base/head/branch/PR and topology; cumulative path diff; commands/results with provenance; adversarial evidence and limitations; crash/commit model; retained fixture/scratch paths and ownership/cleanup follow-up; no root-cause closure or live activation claim. Report any additional necessary path or contract before editing it. Steward settlement records actual authorized merge and review cycles only when true.

## §9 Acceptance rubric

- [ ] Published steward-pinned ACTIVE handoff preceded worker edits.
- [ ] Exactly §4 paths changed and one assigned PR opened; no runtime or operational-root mutation.
- [ ] All §6 safety clauses have CLI-boundary §7 evidence, independently rerun.
- [ ] Explicit retention and fail-closed observation/capacity/mount/identity behavior hold; unknown consumer protocol coverage blocks destructive apply.
- [ ] Crash and concurrency evidence demonstrates no widened or escaped deletion.
- [ ] Actual allocator remains honestly unresolved; separate integration/activation is not claimed.
- [ ] Dirty original checkout preserved; task artifact cleanup inventory reported.

Stop on scope growth, unsafe shared state, unprovable filesystem/process protection, missing exact-head evidence or any attempt to treat this lease as live deletion/rollout authority.
