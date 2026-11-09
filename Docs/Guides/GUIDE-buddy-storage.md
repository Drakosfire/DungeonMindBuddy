# Buddy storage lifecycle tooling

This opt-in, standard-library CLI prepares a bounded candidate lifecycle. It has
**not been adopted by the live allocator**. It does not configure services, move
state, delete existing rollouts, or install a retention schedule. Production
consumer coverage and independent build provenance are deliberately unproven:
production `complete`, `seal`, `acquire`, `release` and destructive `apply` refuse
until those boundaries are integrated and reviewed. There is no force flag,
UUID override, consumer-coverage assertion flag, or automatic eviction.

## Root and retained classes

The production root is `/media/drakosfire/Projects/.buddy`. `--root` makes the
boundary explicit but accepts only this canonical production path. The default
adapter rejects alternative roots and symlink aliases. The accepted recovery
spelling `/home/drakosfire/Projects/.buddy` denotes the intended Projects layout;
operators must use the canonical `/media` spelling for this CLI. Tests inject
adapters through Python calls, never command-line or environment bypasses.

The root and `candidates/` must already exist on ext4 filesystem UUID
`48fa5d10-fe99-4557-9fc9-d8a2a4b41ac8`. UUID, mount ID, device, root identity and
candidate-root identity are rechecked. Missing paths, wrong UUID, symlinks,
foreign/nested mounts, nonexclusive ownership, unavailable capacity or uncertain
observations refuse. The CLI does not create the operational root or repair
permissions. It never falls back to home, `/tmp`, or repository-local storage.
Task builds, caches and test scratch remain under task-owned Projects `.codex`.

| Subtree | Retention policy |
| --- | --- |
| `runtime/` | Current API/UI/config retained; never a deletion target |
| `releases/` | Current and operator-verified rollback retained; all unknown releases also retained |
| `backups/` | Retained indefinitely; requires a separate exact backup retention action |
| `evidence/` | Retained indefinitely; compact receipts preferred, no automatic pruning |
| `candidates/<id>/` | Only expired, sealed, independently reproducible, owned candidates may be planned |
| `candidates/.control/` | Protected lock, compact journals, references, quarantine; never itself cleaned |

Existing data is not adopted merely because its name resembles a candidate.
Unknown files, dirty/unique source, unsafe links, DB dumps and configuration or
secret-like build paths remain protected. Source, corpus, images, evaluations,
environments, databases and credentials are never copied into candidates by this
CLI. A candidate contains a manifest referencing an immutable Git commit and
clean isolated checkout, plus a bounded `build/` directory. Completion checks
Git state, including ignored files. Keep dependencies in a separate task build
checkout; an ignored environment makes the referenced source checkout ineligible.

## Commands and allocation budgets

Read-only inventory and default dry-run plan create no directories or lock files:

```bash
python3 scripts/buddy_storage.py inventory
python3 scripts/buddy_storage.py
python3 scripts/buddy_storage.py plan
```

Output is compact JSON on stdout. Inventory reports categories, ownership,
state, age, apparent and allocated bytes when safely observable, capacity,
protection and reasons. Unknown sizes are identified rather than guessed.
No credential contents or raw Git/OS errors are printed. Printing a plan does not
save it to operational evidence; retaining a receipt is a separate operator step.

Allocation requires explicit policy limits on every invocation. For example,
AFTER a separately approved integration/cutover, an allocator could request:

```bash
python3 scripts/buddy_storage.py allocate \
  --candidate build-EXAMPLE --owner OWNER \
  --source /media/drakosfire/Projects/.codex/TASK/worktrees/clean-source \
  --commit FULL_40_HEX_COMMIT --expires UNIX_TIMESTAMP \
  --bytes 1073741824 --inodes 20000 \
  --max-count 3 --max-bytes 3221225472 --max-age 86400
```

This is a contract illustration, not authorization to invoke the live root.
A successful allocation creates an **incomplete/protected** manifest and an empty
`build/`; it does not execute a build. Every existing candidate must be recognized
and complete/sealed. Existing count, projected allocated/reserved bytes and age
must fit the caller's limits. No candidate is evicted to make room. Repeated
callers must be bound to reviewed limits by the future actual allocator; these
arguments alone are not a persistent machine-wide quota.

The free-byte reserve after planned use is at least the maximum of 10 GiB,
15 percent of filesystem capacity, and `--reserve-bytes` (which can only tighten
the minimum). At least 10 percent of filesystem inodes remain free after planned
use. Actual growth, including metadata and directories, is checked at completion;
overrun leaves the candidate protected. A reservation is accounting, not an OS
quota: a future build runner must bound writes while a build is running. This
CLI does not launch or constrain an uncooperative writer.

The transition API is:

```text
allocate → incomplete → complete → sealed → quarantine → removed
                            ↕
                    acquire/release reference
```

`complete ID` requires independent build provenance in addition to a clean source
reference. A manifest's own `reproducible` flag is insufficient. Production has no
trusted build-receipt adapter, so this transition refuses. Synthetic tests provide
separately known generated bytes. `seal ID` further requires complete consumer
coverage and no references. After sealing, `acquire ID TOKEN` refuses new consumers.
All reference acquisition/release, sealing, allocation and cleanup serialize on
the same nonblocking root lock. Tokens do not expire automatically: stale leases
remain protected until safely reconciled.

## Exact cleanup approval and crash outcomes

A plan envelope contains the plan and SHA-256 digest. Plans bind root identity,
UUID, device/inode identities, mount ID, manifest hashes, protection snapshot,
generation and a 300-second expiry. Apply requires both the exact digest and
exact candidate identity allowlist:

```text
apply --plan-path APPROVED_PLAN_JSON --digest EXACT_DIGEST --candidate EXACT_ID
```

Repeat `--candidate` for every item; omissions, extras and duplicates refuse.
An operator cannot turn missing operational coverage into permission by editing
a plan or supplying a different digest. The production observation adapter
always reports incomplete/unproven coverage. There is no production apply bypass.

Within synthetic cooperating fixtures, apply revalidates the entire allowlist
before the first transition, and each item again immediately before quarantine.
It rechecks references before each unlink/rmdir. Read, traversal and removal use
held descriptors and no-follow opens; metadata replacement uses relative directory
descriptors and atomic rename/fsync. Links, unexpected hardlinks, mount changes,
changed content or identity, incomplete observation and new references refuse.
Process scanning alone cannot serialize consumers. The future consumer adapter
must cover tasks, processes, cwd/executable/open files, services and rollback
references, all namespaces and all consumers, together with the shared reference
protocol. Legacy or uncooperative consumers must keep coverage false.

Every candidate state transition has a durable `pending` journal before the data
transition. Metadata files are fsynced, atomically renamed and their parent
fsynced. For cleanup, quarantine rename and both parent directories are persisted
before descriptor-relative deletion; the compact `done` journal is committed only
after actual removal and directory fsync. A successful per-item result means that
commit point was reached. Operations are not a multi-item transaction: if item 1
committed and item 2 failed, item 1's done journal is authoritative, while item 2
remains pending/protected. A refusal never claims an uncommitted deletion succeeded.

A failure before/after quarantine, partway through removal, before result commit,
or during fsync can leave pending/uncertain state. Inventory protects every
candidate when control state is unknown or a journal/quarantine is pending.
Repeated apply refuses rather than widening its allowlist, retrying uncertain
removal or claiming a second successful deletion. Even a failure after the done
commit may return refusal; the retained done journal records the actual outcome.
Quarantine retains the same protection rules; its name is not disposal authority.

There is deliberately no automatic journal repair, pending-delete replay, backup
cleanup, or quarantine purge. Reconciliation requires a separate reviewed action
that inspects the exact journal, identities, remaining bytes and consumer coverage.
Do not delete journals or clear leases to make the CLI proceed. Compact manifests,
plans, journals and results are retained without automatic expiry in this slice.

## Verification and remaining activation gates

Run only in the assigned Projects implementation checkout:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p test_buddy_storage.py -v
python3 scripts/buddy_storage.py --help
git diff --check
```

Fixtures live below the task's `scratch/storage-fixtures`; each test removes only
its own freshly created fixture. The tests inject UUID/capacity/clock/coverage,
known synthetic build output and fault checkpoints through explicit Python test
seams. They exercise CLI dispatch, filesystem writes, actual descriptor/lock
behavior, real Git cleanliness checks and injected crash/mount/capacity boundaries.
They do not prove operational process visibility or build reproducibility. No DB,
provider or network access is required.

Before live adoption, the steward must identify the original allocator; replace
its full-tree/home-default behavior; bind callers to durable budgets and bounded
writers; supply trusted build provenance; integrate all consumers with sealed
reference acquisition; prove process/service/task/rollback coverage; independently
review exact-head fault/race evidence; and authorize activation/cutover separately.
No live retention, recurring cleanup or recurrence prevention is claimed here.
