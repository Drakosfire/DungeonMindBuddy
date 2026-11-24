"""Synthetic CLI-boundary tests; never instantiate the operational .buddy root."""
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/buddy_storage.py'
spec = importlib.util.spec_from_file_location('buddy_storage', SCRIPT)
b = importlib.util.module_from_spec(spec)
spec.loader.exec_module(b)
SCRATCH = Path(__file__).resolve().parents[3] / 'scratch/storage-fixtures'


class Fixture(b.System):
    def __init__(self, root):
        self.root = root
        self.clock = 1000
        self.uuid = b.UUID
        self.coverage = True
        self.complete = True
        self.references = []
        self.generation = 1
        self.fault = None
        self.hook = None
        self.mount = None
        self.cap = dict(total=100*b.GIB, free=80*b.GIB, inodes=100000, free_inodes=90000)

    def now(self):
        return self.clock

    def validate_root(self, root):
        b.require(root == self.root, 'fixture root mismatch')

    def filesystem(self, root):
        return self.uuid

    def capacity(self, root):
        return self.cap

    def observation(self, root):
        return dict(complete=self.complete, protocol=self.coverage,
                    generation=self.generation, references=self.references)

    def source(self, checkout, commit):
        if getattr(self, 'dirty', False):
            raise b.Refused('dirty or unique source data protected')
        return dict(path=str(checkout), commit=commit)

    def checkpoint(self, label):
        if self.hook:
            self.hook(label)
        if label == self.fault:
            raise OSError('synthetic interruption')

    def reproducible(self, path, source, files):
        if not getattr(self, 'build_proven', True):
            return False
        expected = {'output.txt': b.hashlib.sha256(b'generated').hexdigest(),
                    'database.sql': b.hashlib.sha256(b'fixture only').hexdigest()}
        return all(name in expected and row['sha256'] == expected[name]
                   for name, row in files.items())

    def mount_id(self, fd):
        if self.mount and str(os.readlink('/proc/self/fd/'+str(fd))).endswith(self.mount):
            return 'foreign'
        return super().mount_id(fd)


class Lifecycle(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='case-', dir=SCRATCH)
        self.root = Path(self.temp.name)
        for name in ('runtime', 'releases', 'candidates', 'backups', 'evidence'):
            (self.root/name).mkdir(mode=0o700)
        self.backend = Fixture(self.root)

    def tearDown(self):
        self.temp.cleanup()

    def cli(self, *args, ok=True):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = b.main(['--root', str(self.root), *map(str, args)], system=self.backend)
        self.assertEqual(code, 0 if ok else 2, err.getvalue())
        return json.loads(out.getvalue() if code == 0 else err.getvalue())

    def allocate(self, name='one', **changes):
        options = dict(candidate=name, owner='fixture', source=self.root/'source', commit='a'*40,
                       bytes=1024*1024, inodes=20, max_count=3, max_bytes=3*1024*1024,
                       max_age=1000, expires=1100)
        options.update(changes)
        args = ['allocate']
        for key, value in options.items():
            args += ['--'+key.replace('_', '-'), str(value)]
        return self.cli(*args, ok=changes.pop('ok', True))

    def sealed(self):
        self.allocate()
        (self.root/'candidates/one/build/output.txt').write_text('generated')
        self.cli('complete', 'one')
        self.cli('seal', 'one')
        self.backend.clock = 1200

    def planfile(self):
        result = self.cli('plan')
        p = self.root/'plan.json'
        p.write_text(json.dumps(result))
        return result, p

    def apply(self, result, p, ok=True, candidate='one', approval=None):
        return self.cli('apply', '--plan-path', p, '--digest', approval or result['digest'],
                        '--candidate', candidate, ok=ok)

    def test_default_plan_no_writes(self):
        before = sorted(str(x.relative_to(self.root)) for x in self.root.rglob('*'))
        self.cli()
        self.assertEqual(before, sorted(str(x.relative_to(self.root)) for x in self.root.rglob('*')))
        self.assertFalse((self.root/'candidates/.control').exists())

    def test_reference_only_allocation_and_exact_apply(self):
        self.sealed()
        self.assertEqual(set(x.name for x in (self.root/'candidates/one').iterdir()), {'manifest.json', 'build'})
        result, p = self.planfile()
        self.assertEqual([x['id'] for x in result['plan']['items']], ['one'])
        self.apply(result, p, ok=False, candidate='other')
        self.apply(result, p, ok=False, approval='0'*64)
        self.apply(result, p)
        self.assertFalse((self.root/'candidates/one').exists())
        # Replays are refused rather than falsely reporting another deletion.
        self.apply(result, p, ok=False)
        self.assertTrue(all((self.root/x).exists() for x in ('runtime','releases','backups','evidence')))

    def test_allocation_missing_limits_and_path_traversal(self):
        self.cli('allocate', '--candidate', '../escape', '--owner', 'fixture', '--source', self.root,
                 '--commit', 'a'*40, '--bytes', 10, '--inodes', 10, '--max-count', 2,
                 '--max-bytes', 100, '--max-age', 1000, '--expires', 1100, ok=False)
        self.assertFalse((self.root/'escape').exists())

    def test_wrong_mount_and_absent_root(self):
        self.backend.uuid = 'wrong'
        self.cli('inventory', ok=False)
        with self.assertRaises(b.Refused):
            b.Storage(self.root/'absent', self.backend)

    def test_capacity_and_budgets(self):
        for key, value in [('free', 10*b.GIB), ('free_inodes', 10000)]:
            previous = self.backend.cap[key]
            self.backend.cap[key] = value
            args = ['allocate', '--candidate','one','--owner','fixture','--source',str(self.root),
                    '--commit','a'*40,'--bytes','1000','--inodes','20','--max-count','1',
                    '--max-bytes','10000','--max-age','1000','--expires','1100']
            self.cli(*args, ok=False)
            self.assertFalse((self.root/'candidates/one').exists())
            self.backend.cap[key] = previous
        self.allocate(max_count=1)
        self.cli('complete', 'one')
        args[2] = 'two'
        self.cli(*args, ok=False)

    def test_incomplete_and_growth_protected(self):
        self.allocate(bytes=1)
        (self.root/'candidates/one/build/output').write_text('too big')
        self.cli('complete', 'one', ok=False)
        self.assertEqual(self.cli('plan')['plan']['items'], [])

    def test_unknown_dirty_sensitive_and_live_data(self):
        self.sealed()
        self.backend.dirty = True
        self.assertEqual(self.cli('plan')['plan']['items'], [])
        self.backend.dirty = False
        (self.root/'candidates/one/unknown').write_text('unique')
        self.assertEqual(self.cli('plan')['plan']['items'], [])
        (self.root/'candidates/one/unknown').unlink()
        self.backend.references = ['service:one']
        self.assertEqual(self.cli('plan')['plan']['items'], [])
        self.backend.references = []
        (self.root/'candidates/unknown').mkdir()
        inv = self.cli('inventory')
        self.assertTrue(next(x for x in inv['items'] if x['path']=='candidates/unknown')['protected'])

    def test_symlink_hardlink_and_mount(self):
        self.sealed()
        outside = self.root/'evidence/preserve'
        outside.write_text('unique')
        build = self.root/'candidates/one/build'
        for kind in ('symlink', 'hardlink', 'mount'):
            with self.subTest(kind=kind):
                if kind == 'symlink':
                    (build/'escape').symlink_to(outside)
                elif kind == 'hardlink':
                    os.link(outside, build/'escape')
                else:
                    self.backend.mount = '/build'
                self.assertEqual(self.cli('plan')['plan']['items'], [])
                if (build/'escape').exists():
                    (build/'escape').unlink()
                self.backend.mount = None
        self.assertEqual(outside.read_text(), 'unique')

    def test_changed_plan_and_incomplete_observation(self):
        self.sealed()
        result, p = self.planfile()
        for attr, value in [('clock', 2000), ('generation', 2), ('complete', False),
                            ('coverage', False), ('references', ['new-process'])]:
            old = getattr(self.backend, attr)
            setattr(self.backend, attr, value)
            self.apply(result, p, ok=False)
            setattr(self.backend, attr, old)
        self.assertTrue((self.root/'candidates/one').exists())
        (self.root/'candidates/one/build/output.txt').write_text('changed')
        self.apply(result, p, ok=False)

    def test_lease_acquire_release_and_seal(self):
        self.allocate()
        self.cli('complete','one')
        self.cli('acquire','one','consumer')
        self.cli('seal','one',ok=False)
        self.cli('release','one','consumer')
        self.cli('seal','one')
        self.cli('acquire','one','consumer',ok=False)

    def test_lock_competition_and_acquire_during_delete(self):
        self.sealed()
        s = b.Storage(self.root,self.backend)
        with s.lock():
            self.cli('allocate','--candidate','two','--owner','fixture','--source',str(self.root),
                     '--commit','a'*40,'--bytes','1000','--inodes','20','--max-count','2',
                     '--max-bytes','10000','--max-age','1000','--expires','1300',ok=False)
        result,p = self.planfile()
        observed=[]
        def hook(label):
            if label=='before_quarantine':
                observed.append(self.cli('acquire','one','racing',ok=False))
        self.backend.hook=hook
        self.apply(result,p)
        self.assertEqual(len(observed),1)

    def test_interruptions_never_replay_pending(self):
        self.sealed()
        result,p = self.planfile()
        self.backend.fault='after_quarantine'
        self.apply(result,p,ok=False)
        self.assertTrue((self.root/'candidates/.control/quarantine/one').exists())
        self.backend.fault=None
        self.apply(result,p,ok=False)
        self.assertEqual(self.cli('plan')['plan']['items'],[])

    def test_failure_at_allocation_is_incomplete(self):
        self.backend.fault='allocated'
        args=['allocate','--candidate','one','--owner','fixture','--source',str(self.root),
              '--commit','a'*40,'--bytes','1000','--inodes','20','--max-count','2',
              '--max-bytes','10000','--max-age','1000','--expires','1100']
        self.cli(*args,ok=False)
        self.assertEqual(self.cli('plan')['plan']['items'],[])

    def test_manifest_assertion_is_not_build_proof(self):
        self.sealed()
        self.backend.build_proven=False
        self.assertEqual(self.cli('plan')['plan']['items'],[])

    def test_directory_and_inode_growth_counts(self):
        self.allocate(inodes=3)
        (self.root/'candidates/one/build/generated-directory').mkdir()
        self.cli('complete','one',ok=False)

    def test_unknown_reference_and_legacy_consumer(self):
        self.sealed()
        (self.root/'candidates/.control/references/unknown.json').write_text('{}')
        self.assertEqual(self.cli('plan')['plan']['items'],[])

    def test_cli_has_no_test_bypass_flags(self):
        result=subprocess.run(['python3',str(SCRIPT),'--help'],capture_output=True,text=True)
        self.assertEqual(result.returncode,0)
        self.assertNotIn('uuid',result.stdout)
        self.assertNotIn('force',result.stdout)

    # Every checkpoint uses a fresh fixture and proves protected interrupted state.
    def test_fault_matrix(self):
        for point in ('before_quarantine','partial_removal','before_commit','after_commit'):
            with self.subTest(point=point):
                # Independent fresh candidate root for each destructive sequence.
                with tempfile.TemporaryDirectory(prefix='fault-',dir=SCRATCH) as d:
                    root=Path(d)
                    (root/'candidates').mkdir(mode=0o700)
                    backend=Fixture(root)
                    saved=(self.root,self.backend)
                    self.root,self.backend=root,backend
                    try:
                        self.sealed()
                        envelope,plan=self.planfile()
                        backend.fault=point
                        self.apply(envelope,plan,ok=False)
                        backend.fault=None
                        self.apply(envelope,plan,ok=False)
                        journals=[p for p in (root/'candidates/.control/journal').glob('*.json')
                                  if json.loads(p.read_text()).get('operation')=='remove']
                        self.assertEqual(len(journals),1)
                        state=json.loads(journals[0].read_text())['state']
                        self.assertEqual(state,'done' if point=='after_commit' else 'pending')
                    finally:
                        self.root,self.backend=saved


    def test_fsync_failure_is_pending_and_protected(self):
        self.sealed()
        result,p=self.planfile()
        original=b.fsync_dir
        calls=[]
        def fail_after_transition(path):
            calls.append(str(path))
            if str(path).endswith('/quarantine'):
                raise OSError('synthetic fsync failure')
            original(path)
        with patch.object(b,'fsync_dir',side_effect=fail_after_transition):
            self.apply(result,p,ok=False)
        self.assertTrue(calls)
        self.assertEqual(self.cli('plan')['plan']['items'],[])
        self.apply(result,p,ok=False)

    def test_protection_changes_after_quarantine(self):
        self.sealed()
        result,p=self.planfile()
        def hook(label):
            if label=='after_quarantine':
                self.backend.references=['legacy-consumer']
        self.backend.hook=hook
        self.apply(result,p,ok=False)
        self.assertTrue((self.root/'candidates/.control/quarantine/one/build/output.txt').exists())

    def test_unknown_control_and_candidate_root_swap(self):
        self.allocate()
        (self.root/'candidates/.control/unknown').write_text('preserve')
        self.cli('complete','one',ok=False)
        self.assertEqual(self.cli('plan')['plan']['items'],[])
        s=b.Storage(self.root,self.backend)
        (self.root/'candidates').rename(self.root/'saved')
        (self.root/'candidates').mkdir(mode=0o700)
        with self.assertRaises(b.Refused):
            s.validate()

    def test_unique_manifest_and_low_capacity_warning(self):
        self.sealed()
        p=self.root/'candidates/one/manifest.json'
        manifest=json.loads(p.read_text())
        manifest['unique_local_note']='retain'
        p.write_text(json.dumps(manifest))
        self.assertEqual(self.cli('plan')['plan']['items'],[])
        self.backend.cap['free']=10*b.GIB
        self.assertTrue(self.cli('inventory')['warnings'])

    def test_mid_removal_reference_change_stops(self):
        self.sealed()
        result,p=self.planfile()
        def hook(label):
            if label=='partial_removal':
                self.backend.references=['unexpected-open-file']
        self.backend.hook=hook
        self.apply(result,p,ok=False)
        self.assertTrue((self.root/'candidates/.control/quarantine/one').exists())
        self.assertEqual(self.cli('plan')['plan']['items'],[])

    def test_sensitive_output_stays_protected(self):
        self.allocate()
        (self.root/'candidates/one/build/database.sql').write_text('fixture only')
        self.cli('complete','one')
        self.cli('seal','one')
        self.backend.clock=1200
        self.assertEqual(self.cli('plan')['plan']['items'],[])

    def test_production_source_checks_real_git_checkout(self):
        source=self.root/'source'
        subprocess.run(['git','init','-q',str(source)],check=True)
        subprocess.run(['git','-C',str(source),'-c','user.name=Fixture','-c',
                        'user.email=fixture@example.invalid','commit','-q','--allow-empty','-m','fixture'],check=True)
        commit=subprocess.run(['git','-C',str(source),'rev-parse','HEAD'],check=True,
                              capture_output=True,text=True).stdout.strip()
        b.System().source(source,commit)
        (source/'unique').write_text('retain')
        with self.assertRaises(b.Refused):
            b.System().source(source,commit)



    def test_replaced_manifest_during_removal_is_preserved(self):
        self.sealed()
        result,p=self.planfile()
        replacement = self.root/'replacement.json'
        replacement.write_text('unique replacement data')
        def hook(label):
            if label=='partial_removal' and replacement.exists():
                target=self.root/'candidates/.control/quarantine/one/manifest.json'
                os.replace(replacement, target)
        self.backend.hook=hook
        self.apply(result,p,ok=False)
        target=self.root/'candidates/.control/quarantine/one/manifest.json'
        self.assertEqual(target.read_text(),'unique replacement data')
        self.assertEqual(self.cli('plan')['plan']['items'],[])

    def test_inplace_change_during_removal_is_preserved(self):
        self.sealed()
        result,p=self.planfile()
        changed=[]
        def hook(label):
            if label=='partial_removal' and not changed:
                target=self.root/'candidates/.control/quarantine/one/manifest.json'
                target.write_text('unique in-place data')
                changed.append(True)
        self.backend.hook=hook
        self.apply(result,p,ok=False)
        target=self.root/'candidates/.control/quarantine/one/manifest.json'
        self.assertEqual(target.read_text(),'unique in-place data')

    def test_candidate_replaced_before_quarantine_stays_put(self):
        self.sealed()
        result,p=self.planfile()
        def hook(label):
            if label=='before_quarantine':
                original=self.root/'candidates/one'
                original.rename(self.root/'saved-original')
                original.mkdir(mode=0o700)
                (original/'unique').write_text('preserve')
        self.backend.hook=hook
        self.apply(result,p,ok=False)
        self.assertEqual((self.root/'candidates/one/unique').read_text(),'preserve')
        self.assertTrue((self.root/'saved-original/build/output.txt').exists())
        self.assertFalse((self.root/'candidates/.control/quarantine/one').exists())

    def test_extra_file_arriving_before_approval_snapshot_is_preserved(self):
        self.sealed()
        result,p=self.planfile()
        original=b.Storage.tree
        injected=[]
        def tree(storage, path, *args, **kwargs):
            path=Path(path)
            if path.name=='one' and path.parent.name=='quarantine' and not injected:
                (path/'unique-local-data.txt').write_text('keep me')
                injected.append(True)
            return original(storage,path,*args,**kwargs)
        with patch.object(b.Storage,'tree',tree):
            self.apply(result,p,ok=False)
        self.assertEqual((self.root/'candidates/.control/quarantine/one/unique-local-data.txt').read_text(), 'keep me')

    def test_changed_build_before_approval_snapshot_is_preserved(self):
        self.sealed()
        result,p=self.planfile()
        original=b.Storage.tree
        injected=[]
        def tree(storage, path, *args, **kwargs):
            path=Path(path)
            if path.name=='one' and path.parent.name=='quarantine' and not injected:
                (path/'build/output.txt').write_text('changed local data')
                injected.append(True)
            return original(storage,path,*args,**kwargs)
        with patch.object(b.Storage,'tree',tree):
            self.apply(result,p,ok=False)
        self.assertEqual((self.root/'candidates/.control/quarantine/one/build/output.txt').read_text(), 'changed local data')

    def test_malformed_control_metadata_is_protected(self):
        self.allocate()
        journal=self.root/'candidates/.control/journal/unknown.json'
        for content in ('[]','{"state":"done","state":"pending"}'):
            journal.write_text(content)
            self.assertEqual(self.cli('plan')['plan']['items'],[])
            self.cli('complete','one',ok=False)


if __name__=='__main__':
    unittest.main()
