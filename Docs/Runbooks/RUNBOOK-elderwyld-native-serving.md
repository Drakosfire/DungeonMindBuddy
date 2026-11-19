# Elderwyld native serving

Status: V9.B actual activation accepted at PR4079 merge
e36abef5d75d543b7e8c656d611b93723757b362, exact reviewed5b422140079b357e064176732b20918a85ba14d5,
Cycle1review5971846921, frontend1411 selected passes/build/canonical/cleanup.
V10 retirement and V11 serving measurements remain required. Functional qualification
is not a speed claim. Current serving mirrors and commands below remain pinned.

## Serving anchor

Open http://127.0.0.1:5202/graph?world=elderwyld. UI5202 serves the compiled accepted
assets and proxies the owned primary18292. Qualified same-version fallback18293
uses the same latest migrated authorities. Other-lane API8000 is not ours to stop.

Pinned mirrors are at
`/home/drakosfire/Projects/.codex/v7-elderwyld-scope/verification/v9b-serving`:
Buddy4f4ed526278badc8b9b7241e418e90c7fd474c98 (runtime equal1c7ddcd),
Core4b6516e2c0dfd81acaa4410b9b9bb9da18894c90. Never silently substitute later main
or sync the running venv. Actual first-party imports are mirror-bound; installed
Core distribution metadata alone does not identify the imported code.

Live Core54330/dungeonmind_cutover_live_restore_20261011 uses0022_native_read_artifacts;
APP54331/dungeonbuddy_application_state uses20261118_0168. Qualification preserved
Elderwyld600/head5293c1b/epoch194/bindingv3 and existing active Run. These observations
are not permanent expected values after legitimate product writes. The owned606
rehearsal restore is not live and must never be promoted over the real World.

Task variables for the commands below (execute with host localhost/process access):

```bash
task=/home/drakosfire/Projects/.codex/v7-elderwyld-scope
ops="$task/scratch/v9-buddy/v9b-live"
py="$task/worktrees/DungeonMindBuddy/.venv/bin/python"
```

Private profiles are in `$ops/private` (directory0700/files0600), with existing
operator auth/session, binding key, original data roots and provider configuration.
Do not print or commit those secrets. Profile/config changes require requalification;
launch guards intentionally reject drift. No provider generation was invoked during
activation; configuration status does not prove provider reachability.

## Observe before changing anything

Read `$ops/ui-active.json`, `primary-process.json`, `fallback-process.json` for current
operational pointers; verify actual `/proc/<pid>/cmdline`, cwd and listener identity.
Their launch-only `launched_unqualified` labels do not summarize later qualification.
Immutable `$ops/serving-completion-processes.json` records the completed qualification,
not permanent current PIDs. At qualification: primary1064371 generation2,
fallback1049478 generation1, UI1069583 generation3.

Use actual UI plus authenticated product reads through5202 and responding-PID headers
to establish readiness. Direct `/health/live` is only liveness. Run localhost probes
from the host executor: restricted execution can report a refused connection while
the host deployment is healthy. Inspect authoritative host state before any restart.

The `verify_serving_reads.py`, `verify_serving_native_inspection.py` and
`capture_live_authority.py` qualification helpers are fixed600/head+parent oracles.
Do not reuse them as generic current-head health checks after legitimate writes;
never change/reset live authority to make them pass. Their frozen proof receipts
must remain immutable. For normal readiness, read the current head/binding and use
current authorized neighborhood/object/source requests, retaining their actual pins
and exact citations. Unknown authority/source/import drift requires inspection.

## Same-version process rollback

Establish fallback18293 is healthy with the accepted imports/config, latest migrated
persistence and current authorized reads before moving traffic. Verify the target PID
is not a zombie or reused foreign process. Mapping only checks process existence,
so target readiness is an explicit prerequisite. Then:

```bash
"$py" "$ops/switch_serving_ui_v4.py" fallback
```

Require successful actual5202 responses with the fallback PID header, current
head/binding and ordered/cited results before treating rollback as complete.
The helper checks original reviewed input hashes, separate mapping-delta approval,
built asset hashes, owned UI identity and strictPort binding. It never seizes an
unknown listener. A failed or uncertain mapping is not success; inspect the saved
process/log before retrying. Preserve failed receipts and prior generations.

To restore qualified primary traffic after its readiness is established:

```bash
"$py" "$ops/switch_serving_ui_v4.py" primary
```

Repeat actual5202/browser/current-read checks. Same-version mapping rollback was
exercised primary→fallback→restarted primary with84 matching route cases, anonymous401,
exact1276-byte citation,8 native inspections,8 existing product reads,163 assets and
browser details/excerpt in all three phases. This does not prove new live writes.

## Graceful owned API restart

First move5202 to the other qualified, ready API as above. Never stop the API that
is still serving5202. The reusable helpers below were syntax checked and independently
reviewed (restart-helper-review.json); they have not been executed. The original
one-off primary drain/restart was executed and has separate immutable receipts.

For primary restart while fallback is serving:

```bash
"$py" "$ops/stop_serving_for_restart.py" primary
"$py" "$ops/launch_serving_v4.py" primary
```

Run sequentially and stop if either command fails. The stop helper validates the
actual authenticated latest-head neighborhood through5202 with the other PID before
signalling the exact owned uvicorn/cwd. It allows graceful drain and refuses a forced
kill. The launch helper verifies reviewed inputs and immutable sources/assets, refuses
an occupied API port, and preserves matching generation archives for safe retries.
It starts the actual app/lifespan and never migrates at startup. Launch is not
readiness: inspect its generation log and fresh imported-source attestation, then
prove direct current authorized reads before switching5202 back to primary.
The same sequence applies to fallback only while verified primary is serving.

Use unique phase labels if freezing a fresh after-request attestation:

```bash
"$py" "$ops/attest_serving.py" primary unique-phase-label
```

Do not overwrite old phase receipts or delete generation evidence to unblock retry.
If identities/inputs/schema diverge, stop and qualify a new concrete plan.

## Recovery and retention

Routine rollback does not downgrade schemas or restore an old dump over later writes.
Recovery is separate: retain the fresh preactivation exported-snapshot dumps and
new owned32903 restore databases recorded in the report. Core/APP snapshots were
separate, not globally atomic. Inventory proof covers stored tables/definitions,
sequences and large objects, not every SQL function/view/policy/ACL. The two named
APP CHECK rendering differences have exact bounded equivalence evidence. Source
vector0.8.6 and recovery0.8.7 are an explicit extension difference.

Native bodies/components and864 existing referenced files were verified;112 historical
locator candidates remain absent, and external CDN objects are not independently
backed up by these dumps. Original roots remain selected; no old-name bridge or
file reconstruction. Preserve these limits when assessing file/provider capabilities.

Owner Elderwyld activation retains serving mirrors/builds/node_modules, private
configuration, task caches, backups, recovery DBs and evidence through V10/V11.
Mirrors and output directories are actively used by serving processes. No manual
paths were removed or bytes reclaimed. Cleanup followup: after qualified replacement,
check process/mount/DB connections, dirty state and unique commits/data, then dispose
only of explicitly approved task-owned reproducible resources. The report inventories
paths and recovery DBs. Frozen classic baseline must not be rerun.
