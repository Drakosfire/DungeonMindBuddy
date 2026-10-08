# SERVER — current Core a501 rollout preparation

**PREPARATION ONLY.** PRIME owns exact-pin review and a future exclusive execution lease. No current source/environment/schema/process/data change is authorized. #1007/#1014 operator merge holds remain separate.

## Current source and preserved inputs

Live Buddy is `d0ac6f28abf5d1130502712c2ee85f5735045ad0`, Core5d (`5d4e98963991995bdc280e57df52b8d0fe8de79e`), Buddy0018/Core0013. DMS remains `c3867e9eb961250d6d2086ddfec1b6fae22c5fc4` / tree `a1f102ec2c59b1286b0a0e7c9b91e0baa01049bd` with its existing Python3.12 environment and private configuration. Capture fresh refs/trees/branches/environment paths at activation; never assume an old PID is still owned.

Candidate implementation composition `3bcb516edf9c36904b8f929893de1c00e140f29f` / tree `aeaf9533e93a332c804a93fa689e45e080e15881` merges accepted d0 with #1019 main `804a9d38b877ad931f64ebbb015632d5f69010ce`. UI/run/API/Python blobs equal d0. The final review head adds only current backup-helper/tests and this authority settlement; use the PR's exact head/tree before execution. #1019's source acceptance and 129 distinct passing synthetic cases carry; its inherited native-write fixture failure and real-data consumer integration limitation remain explicit.

New inactive environment: `/home/drakosfire/.local/state/dungeonmindbuddy/rollout-candidates/core-a501-composed-3bcb516e-venv`. Core is exact `a501784f21aaafb46d7561f46397a3afdc42f125`; Hermes remains0.18.2. Installation provenance retains the durable frozen composed source in `direct_url.json`; an explicit inactive-only editable `.pth` override binds **effective imports** to permanent `/home/drakosfire/.local/state/dungeonmindbuddy/runtime/src`. No live package/source installation occurred. Private binding record and proof are `rollout-candidates/core-a501-inactive-runtime-binding.json` and `core-a501-permanent-binding-proof.json` (proof SHA `6221cab99cd5dc94ede3a2a371a3734b4cf0175a736d74acb20ac9701bd2098d`). Actual module bytes match composed Python source; repo/model-policy roots are permanent runtime, managed registry/profile resolution is valid, and the registered source digest matches. Recheck all these facts after the stopped candidate switch before migrations/start.

## Executable command contract — requires a new lease

The following are reviewable commands, **not current execution authority**. They assume fresh DOGFOOD empty/draft/recovery quiet-window handback; zero open Agent turns/Plan actions; exact clean d0/DMS sources; verified port/listener ancestry; and fresh named endpoint/cluster identity matching the private inventory. Stop only the verified owning launcher; repaired cleanup stops its birth-verified descendants. Require5202/8000/7860 closed before backup/switch/migration. Preserve all browser storage, private profiles, corpora, keys and output stores.

Set only task-specific variables under the future lease:

```bash
ROLLOUT_PY=/home/drakosfire/.local/state/dungeonmindbuddy/rollout-candidates/core-a501-composed-3bcb516e-venv/bin/python
ROLLOUT_SOURCE=/tmp/dmb-current-main-rollout-candidate
CORE_SOURCE=/home/drakosfire/.local/state/dungeonmindbuddy/rollout-candidates/core-a501-migration-source
```

1. Fresh **operational preservation** backup, source pair Buddy0018/Core0013:

```bash
"$ROLLOUT_PY" "$ROLLOUT_SOURCE/scripts/current_main_rollout_backup.py" --execute
```

The current reviewed helper rejects any other schema pair, database name, endpoint, cluster ID or major; verifies free space; writes private custom dumps/inventories and the complete file archive; records both clean source refs/trees/branches and environment targets/manifests; and leaves `INCOMPLETE` on failure. The archive includes live-session, private operator/shared/Buddy configuration, Graph sessions/inventory, runtime output/corpus, managed corpus/registry and DMS env/key. Record its printed backup directory in an owner-private `ROLLOUT_BACKUP` variable. Independently verify every manifest hash/byte count, dump inventory and archive listing. A failed/partial backup stops the lease. The prior0007 helper is superseded by this implementation, not reused or relabeled.

2. Switch only the stopped clean Buddy checkout to the exact **accepted** PR head and its reviewed inactive environment symlink, retaining the recorded old ref/branch/link. DMS c386/environment remains unchanged. Verify permanent imported bytes/roots/profile/source digest and Corea501/Hermes again. Perform **only Core0013→0014**; Buddy remains0018:

```bash
cd "$CORE_SOURCE"
"$ROLLOUT_PY" - <<'PY'
from pathlib import Path
import os
from dotenv import dotenv_values
from psycopg.conninfo import conninfo_to_dict
from alembic.config import Config
from alembic import command
v = dotenv_values('/home/drakosfire/Projects/DungeonOverMind/DungeonMindBuddy/.env')
dsn = v['DUNGEONMIND_WORLD_GRAPH_AUTHORITY_DATABASE_URL']
f = conninfo_to_dict(dsn)
assert f['host'] == '127.0.0.1' and f['port'] == '54330' and f['dbname'] == 'dungeonmind_cutover_live'
os.environ['DUNGEONMIND_DATABASE_URL'] = dsn
command.upgrade(Config('alembic.ini'), '0014_adopted_withdrawal_v2')
PY
```

Migration source is the durable archive of exact a501; `rollout-candidates/core-a501-migration-manifest.json` pins archive and0014 file hashes. Revalidate source0013 and cluster identity immediately before this command. Compare **all preexisting row and file hashes** to the fresh baseline after migration and startup. Start through the reviewed whole `./run` with `UV_NO_SYNC=1` and preserved prior launcher environment; no dependency sync. Verify all health, existing V1 history, Graph/source reads, roots and private state before releasing QA.

3. Any failed gate: stop the same verified launcher and require all ports closed. Restore **both** named databases from the verified pair (even though only Core migrated), never a partial restart:

```bash
"$ROLLOUT_PY" - "$ROLLOUT_BACKUP" "$ROLLOUT_SOURCE" <<'PY'
from pathlib import Path
import importlib.util, json, subprocess, sys
root, source = map(Path, sys.argv[1:])
spec = importlib.util.spec_from_file_location('backup', source/'scripts/current_main_rollout_backup.py')
b = importlib.util.module_from_spec(spec); spec.loader.exec_module(b)
m = json.loads((root/'manifest.json').read_text())
assert not (root/'INCOMPLETE').exists()
for name, entry in m['files'].items():
    assert b._sha256(root/name) == entry['sha256'] and (root/name).stat().st_size == entry['bytes']
for key, name, dump in [('DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL',b.BUDDY_DATABASE_NAME,'buddy-application-state.dump'),('DUNGEONMIND_WORLD_GRAPH_AUTHORITY_DATABASE_URL',b.CORE_DATABASE_NAME,'dungeonmind-graph-authority.dump')]:
    dsn = b._configured_dsn(key, name)
    env = b._pg_environment(dsn); env['PGDATABASE'] = 'postgres'
    subprocess.run(['/usr/bin/pg_restore','--dbname=postgres','--exit-on-error','--clean','--if-exists','--create',str(root/dump)],env=env,check=True)
PY
```

Before restore revalidate endpoint/cluster IDs against the backup manifest and confirm no database clients/writes remain. Restore preserved files from the **hash-verified** private archive into a private staging directory, then replace only its declared original subjects with preserved symlinks/permissions:

```bash
"$ROLLOUT_PY" - "$ROLLOUT_BACKUP" "$ROLLOUT_SOURCE" <<'PY'
from pathlib import Path
import importlib.util, json, os, shutil, subprocess, sys, tempfile
backup, source = map(Path, sys.argv[1:]); os.umask(0o077)
spec = importlib.util.spec_from_file_location('backup',source/'scripts/current_main_rollout_backup.py')
b = importlib.util.module_from_spec(spec); spec.loader.exec_module(b)
m = json.loads((backup/'manifest.json').read_text()); archive = backup/'buddy-preserved-files.tar'
assert b._sha256(archive) == m['files'][archive.name]['sha256']
staging = Path(tempfile.mkdtemp(prefix='paired-restore-',dir=backup))
subprocess.run(['/usr/bin/tar','--extract','--preserve-permissions','--file',str(archive),'--directory',str(staging)],check=True)
for target, name in b._state_subjects():
    restored = staging/name
    if target.is_symlink() or target.is_file(): target.unlink()
    elif target.exists(): shutil.rmtree(target)
    target.parent.mkdir(parents=True,exist_ok=True)
    if restored.is_symlink(): target.symlink_to(os.readlink(restored))
    elif restored.is_dir(): shutil.copytree(restored,target,symlinks=True)
    else: shutil.copy2(restored,target)
for item in m['source_environment'].values():
    ref = item['branch'] or item['head']
    subprocess.run(['git','switch',ref] if item['branch'] else ['git','switch','--detach',ref],cwd=item['root'],check=True)
    assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=item['root'],text=True).strip()==item['head']
    if item['venv_link'] is not None:
        link = Path(item['root'])/'.venv'; temp = link.with_name('.venv-rollback')
        temp.symlink_to(item['venv_link']); os.replace(temp,link)
PY
```

Verify restored schema0018/0013, all before-table/file hashes, both source refs/trees/environment/config identities and old health before reopening writes. Restore the recorded previous whole-launcher environment with `UV_NO_SYNC=1`; do not infer it from a new shell or mutate DMS dependencies. Full dump restore is the rollback;0014 downgrade refuses once V2 receipts exist. No receipt/schema workaround or data repair is permitted.

## Evidence and limits

- Current helper: focused schema gate/private archive tests and changed-file Ruff; exact results in PR review packet. Old backup/rehearsal witnesses are history, not evidence that this new helper was run on live data.
- Accepted Core consumer proof:129 distinct synthetic passes; inherited native first-world write fixture failure reproduced on5d. MIND83505e is Core operation evidence; no real-data Buddy withdrawn-child read is claimed.
- Automatic approval rejected full live-database **test replication**; that payload stays held. A future operational preservation backup has a separate exact local purpose/payload and requires its own explicit lease and approval review. No backups/migrations/restores above were executed by this preparation.
- V4 promotion, locator-null withdrawal, provider calls and Graph coverage changes require separate data authority. Current operator runtime/inspection remains stable.

## Immutable predecessor evidence

Superseded f6e7/0007→0013 instructions and UI-only transitions are archived in [the exact e77 handoff](https://github.com/Drakosfire/DungeonMindBuddy/blob/e77fc546234c7adf98b241900e6da7d813bba73b/Docs/Plans/HANDOFF-SERVER-current-main-paired-rollout-2026-10-07.md) and [accepted operation comment6048011402](https://github.com/Drakosfire/DungeonMindBuddy/pull/1014#issuecomment-6048011402). They are not active instructions. Unique private prior proof pointers remain `/tmp/dmb-full-stack-witness-x5fstjdz/certified-result.json` (83f0ffe…) and `rollout-candidates/execute-e77fc546-20261007/`; do not publish private contents or treat the old source pair as current.
