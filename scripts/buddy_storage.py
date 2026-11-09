#!/usr/bin/env python3
"""Opt-in Buddy candidate lifecycle; no operational consumer coverage is assumed."""
from __future__ import annotations

import argparse
import contextlib
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import time
import uuid

PROJECTS = Path('/media/drakosfire/Projects')
ROOT = PROJECTS / '.buddy'
UUID = '48fa5d10-fe99-4557-9fc9-d8a2a4b41ac8'
GIB = 1024 ** 3
NAME = re.compile(r'[a-zA-Z0-9][a-zA-Z0-9_-]{0,79}\Z')
SHA = re.compile(r'[0-9a-f]{40}\Z')
NOFOLLOW = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW


class Refused(Exception):
    pass


def require(ok, reason):
    if not ok:
        raise Refused(reason)


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


def digest(value):
    return hashlib.sha256(encoded(value)).hexdigest()


def identity(path):
    s = path.lstat()
    return [s.st_dev, s.st_ino]


def safe_name(value):
    require(isinstance(value, str) and NAME.fullmatch(value), 'invalid candidate identity')
    return value


def no_links(path):
    require(path.is_absolute() and '..' not in path.parts, 'absolute canonical path required')
    for part in [path, *path.parents]:
        require(not part.is_symlink(), 'symlink path refused')


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, 'duplicate metadata keys')
        result[key] = value
    return result


def read_json(path):
    s = path.lstat()
    require(stat.S_ISREG(s.st_mode) and s.st_nlink == 1 and s.st_size <= 1024 * 1024,
            'unsafe metadata file')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd) as stream:
        require([os.fstat(stream.fileno()).st_dev, os.fstat(stream.fileno()).st_ino] ==
                [s.st_dev, s.st_ino], 'metadata changed')
        value = json.load(stream, object_pairs_hook=unique_object)
        require(isinstance(value, dict), 'metadata object required')
        return value


def open_dir(path):
    # Resolve every component relative to held descriptors; never follow links.
    no_links(path)
    fd = os.open('/', NOFOLLOW)
    try:
        for part in path.parts[1:]:
            child = os.open(part, NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = child
        return fd
    except BaseException:
        os.close(fd)
        raise


def fsync_dir(path):
    fd = open_dir(path)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def atomic(path, value):
    parent = open_dir(path.parent)
    tmp = '.pending-' + uuid.uuid4().hex
    try:
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                     0o600, dir_fd=parent)
        with os.fdopen(fd, 'wb') as stream:
            stream.write(encoded(value))
            stream.flush()
            os.fsync(stream.fileno())
        os.rename(tmp, path.name, src_dir_fd=parent, dst_dir_fd=parent)
        os.fsync(parent)
    finally:
        os.close(parent)


class System:
    """Production adapters deliberately cannot certify absent consumer integration."""
    def now(self):
        return time.time()

    def filesystem(self, root):
        result = subprocess.run(['findmnt', '-J', '-T', str(root), '-o', 'UUID'],
                                check=True, capture_output=True, text=True)
        return json.loads(result.stdout)['filesystems'][0]['uuid']

    def capacity(self, root):
        s = os.statvfs(root)
        return dict(total=s.f_blocks * s.f_frsize, free=s.f_bavail * s.f_frsize,
                    inodes=s.f_files, free_inodes=s.f_favail)

    def validate_root(self, root):
        require(root == ROOT, 'only the canonical Projects Buddy root is supported')

    def observation(self, root):
        # No operational registry/lease integration has been established. Do not
        # pretend /proc enumeration can certify services or other PID namespaces.
        return dict(complete=False, protocol=False, references=[], generation=None)

    def reproducible(self, path, source, files):
        # Source cleanliness does not prove build outputs disposable. A future
        # trusted allocator must supply independently verifiable build receipts.
        return False

    def mount_id(self, fd):
        with open('/proc/self/fdinfo/' + str(fd)) as stream:
            return next(line.split(':', 1)[1].strip() for line in stream
                        if line.startswith('mnt_id:'))

    def checkpoint(self, label):
        pass

    def source(self, checkout, commit):
        no_links(checkout)
        require(checkout.is_dir() and SHA.fullmatch(commit), 'immutable source required')
        def git(*args):
            return subprocess.run(['git', '-C', str(checkout), *args], check=True,
                                  capture_output=True, text=True).stdout.strip()
        require(git('rev-parse', 'HEAD') == commit, 'source commit changed')
        require(not git('status', '--porcelain', '--untracked-files=all', '--ignored'),
                'dirty or unique source data protected')
        return dict(path=str(checkout), commit=commit)


class Storage:
    def __init__(self, root, system=None):
        self.root = Path(root)
        self.system = system or System()
        no_links(self.root)
        self.system.validate_root(self.root)
        require(self.root.is_dir(), 'root must already exist; no fallback')
        require(self.system.filesystem(self.root) == UUID, 'Projects UUID mismatch')
        self.device = self.root.stat().st_dev
        self.candidates = self.root / 'candidates'
        require(self.candidates.is_dir() and not self.candidates.is_symlink(),
                'candidates must already exist')
        self.control = self.candidates / '.control'
        self.root_identity = identity(self.root)
        self.candidate_identity = identity(self.candidates)
        fd = open_dir(self.root)
        try:
            self.mount = self.system.mount_id(fd)
        finally:
            os.close(fd)
        self.validate()

    def directory(self, path):
        fd = open_dir(path)
        try:
            s = os.fstat(fd)
            require(s.st_uid == os.getuid() and not s.st_mode & 0o022,
                    'directory ownership is not exclusive')
            require(s.st_dev == self.device and self.system.mount_id(fd) == self.mount,
                    'directory mount changed')
        finally:
            os.close(fd)

    def validate(self):
        no_links(self.root)
        self.directory(self.root)
        self.directory(self.candidates)
        require(identity(self.root) == self.root_identity and
                self.system.filesystem(self.root) == UUID, 'root or mount changed')
        require(self.candidates.is_dir() and not self.candidates.is_symlink() and
                self.candidates.stat().st_dev == self.device and
                identity(self.candidates) == self.candidate_identity, 'candidate root changed')

    def check_control(self):
        if not self.control.exists():
            require(not self.control.is_symlink(), 'unsafe control root')
            return
        require(self.control.is_dir() and not self.control.is_symlink(), 'unsafe control root')
        self.directory(self.control)
        allowed = {'lifecycle.lock', 'journal', 'quarantine', 'references'}
        require(set(p.name for p in self.control.iterdir()) <= allowed, 'unknown control state')
        for name in ('journal', 'quarantine', 'references'):
            p = self.control / name
            if p.exists() or p.is_symlink():
                require(p.is_dir() and not p.is_symlink() and p.stat().st_dev == self.device,
                        'unsafe control directory')
                self.directory(p)
        for p in (self.control / 'journal').glob('*'):
            item = read_json(p)
            require(p.name.endswith('.json') and item.get('state') == 'done' and
                    item.get('operation') in ('allocate', 'complete', 'seal', 'acquire', 'release', 'remove'),
                    'pending or unknown journal requires reconciliation')
            safe_name(item.get('candidate'))
        require(not any((self.control / 'quarantine').glob('*')), 'quarantine requires reconciliation')
        for p in (self.control / 'references').glob('*'):
            lease = read_json(p)
            require(p.name == safe_name(lease.get('token')) + '.json', 'unknown consumer lease')
            safe_name(lease.get('candidate'))

    @contextlib.contextmanager
    def lock(self):
        self.validate()
        self.check_control()
        self.control.mkdir(mode=0o700, exist_ok=True)
        for name in ('journal', 'quarantine', 'references'):
            (self.control / name).mkdir(mode=0o700, exist_ok=True)
        p = self.control / 'lifecycle.lock'
        fd = os.open(p, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        try:
            s = os.fstat(fd)
            require(stat.S_ISREG(s.st_mode) and s.st_nlink == 1, 'unsafe lock')
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise Refused('lifecycle lock busy') from None
            self.validate()
            self.check_control()
            yield
        finally:
            os.close(fd)

    def tree(self, path, files=None, *, hash_files=True):
        """Inspect with held descriptors; reject links, special files and bind mounts."""
        rows = {}
        fd = open_dir(path)
        try:
            expected_mount = self.system.mount_id(fd)
            rootfd = open_dir(self.root)
            try:
                require(expected_mount == self.system.mount_id(rootfd), 'nested mount refused')
            finally:
                os.close(rootfd)
            def walk(parent, prefix=''):
                for name in sorted(os.listdir(parent)):
                    rel = prefix + name
                    s = os.stat(name, dir_fd=parent, follow_symlinks=False)
                    require(s.st_dev == self.device, 'foreign device refused')
                    require(stat.S_ISDIR(s.st_mode) or stat.S_ISREG(s.st_mode),
                            'links and special files protected')
                    if stat.S_ISDIR(s.st_mode):
                        rows[rel] = dict(identity=[s.st_dev, s.st_ino], size=0,
                                         allocated=s.st_blocks * 512, sha256=None)
                        child = os.open(name, NOFOLLOW, dir_fd=parent)
                        try:
                            require(self.system.mount_id(child) == expected_mount, 'nested mount refused')
                            walk(child, rel + '/')
                        finally:
                            os.close(child)
                    else:
                        require(s.st_nlink == 1, 'hardlinked data protected')
                        handle = os.open(name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=parent)
                        try:
                            require(identity_fd(handle) == [s.st_dev, s.st_ino], 'file changed')
                            h = hashlib.sha256()
                            if hash_files:
                                while chunk := os.read(handle, 1024 * 1024):
                                    h.update(chunk)
                            final = os.fstat(handle)
                            require((final.st_size, final.st_mtime_ns, final.st_ctime_ns) ==
                                    (s.st_size, s.st_mtime_ns, s.st_ctime_ns), 'file changed during inspection')
                            rows[rel] = dict(identity=[s.st_dev, s.st_ino], size=s.st_size,
                                             allocated=s.st_blocks * 512, sha256=h.hexdigest() if hash_files else None)
                        finally:
                            os.close(handle)
            walk(fd)
        finally:
            os.close(fd)
        if files is not None:
            require(rows == files, 'candidate contents changed or unknown')
        return rows

    def manifest(self, candidate):
        safe_name(candidate)
        path = self.candidates / candidate
        no_links(path)
        self.directory(path)
        m = read_json(path / 'manifest.json')
        require(set(m) == {'schema', 'id', 'root', 'candidate', 'owner', 'created', 'expires',
                           'state', 'source', 'planned_bytes', 'planned_inodes', 'max_bytes',
                           'reserve_bytes', 'reproducible', 'files'}, 'unknown manifest fields')
        require(m.get('schema') == 1 and m.get('id') == candidate and
                m.get('root') == self.root_identity, 'unowned candidate')
        require(m.get('candidate') == identity(path), 'candidate identity changed')
        require(isinstance(m.get('owner'), str) and m['owner'], 'owner missing')
        return path, m

    def observe(self):
        value = self.system.observation(self.root)
        require(value.get('complete') and value.get('protocol') and
                value.get('generation') is not None, 'consumer coverage unproven')
        require(isinstance(value.get('references'), list), 'unknown consumer references')
        return value

    def eligible(self, candidate):
        path, m = self.manifest(candidate)
        require(m.get('state') == 'sealed' and m.get('reproducible') is True,
                'incomplete or unsealed candidate protected')
        require(m['expires'] <= self.system.now(), 'TTL not expired')
        self.system.source(Path(m['source']['path']), m['source']['commit'])
        require(set(p.name for p in path.iterdir()) == {'manifest.json', 'build'},
                'unknown candidate data protected')
        rows = self.tree(path / 'build', m['files'])
        require(self.system.reproducible(path, m['source'], rows), 'build provenance unproven')
        for name in rows:
            require(not any(part.startswith('.') for part in Path(name).parts) and
                    not re.search(r'(?i)(secret|credential|config|backup|\.env|\.sql|\.dump|\.db)', name),
                    'sensitive or backup data protected')
        for ref in (self.control / 'references').glob('*.json'):
            lease = read_json(ref)
            require(lease.get('candidate') != candidate, 'consumer reference protected')
        return path, m

    def inventory(self):
        self.validate()
        results = []
        try:
            self.check_control()
            control_ok = True
        except (Refused, OSError, ValueError):
            control_ok = False
        observation = self.system.observation(self.root)
        for path in sorted(self.root.iterdir()):
            if path.name != 'candidates':
                row = dict(path=path.name, category=path.name, protected=True,
                           reason='outside disposable candidate boundary', owner='operator', state='retained')
                try:
                    rows = self.tree(path, hash_files=False)
                    row.update(apparent_bytes=sum(x['size'] for x in rows.values()),
                               allocated_bytes=sum(x['allocated'] for x in rows.values()),
                               age=max(0, self.system.now()-path.stat().st_mtime))
                except (Refused, OSError):
                    row['size_status'] = 'unknown; protected'
                results.append(row)
        for path in sorted(self.candidates.iterdir()):
            row = dict(path='candidates/' + path.name, category='candidate', protected=True)
            try:
                require(control_ok, 'unknown or pending control state')
                require(path.name != '.control', 'protected control metadata')
                _, m = self.manifest(path.name)
                rows = self.tree(path, hash_files=False)
                row.update(owner=m['owner'], state=m['state'], age=max(0, self.system.now()-m['created']),
                           apparent_bytes=sum(x['size'] for x in rows.values()),
                           allocated_bytes=sum(x['allocated'] for x in rows.values()))
                self.eligible(path.name)
                require(observation.get('complete') and observation.get('protocol'), 'consumer coverage unproven')
                require(not observation.get('references'), 'live/task/service references protected')
                row.update(protected=False, reason='expired sealed reproducible candidate')
            except (Refused, OSError, ValueError, KeyError, TypeError) as exc:
                row['reason'] = str(exc) if isinstance(exc, Refused) else 'unknown candidate state'
            results.append(row)
        capacity = self.system.capacity(self.root)
        warnings = []
        if capacity.get('free', 0) < max(10 * GIB, capacity.get('total', 0) * .15) + GIB:
            warnings.append('byte reserve near or below exhaustion; allocation may refuse')
        if capacity.get('free_inodes', 0) < capacity.get('inodes', 0) * .12:
            warnings.append('inode reserve near or below exhaustion; allocation may refuse')
        return dict(root=str(self.root), capacity=capacity, items=results, warnings=warnings,
                    operational_coverage=bool(observation.get('complete') and observation.get('protocol')))

    def allocate(self, args):
        name = safe_name(args.candidate)
        require(args.reserve_bytes >= 10 * GIB, 'reserve cannot weaken minimum')
        require(args.owner and len(args.owner) <= 100, 'explicit bounded owner required')
        limits = [args.bytes, args.inodes, args.max_count, args.max_bytes, args.max_age]
        require(all(type(v) is int and v > 0 for v in limits), 'positive explicit limits required')
        require(self.system.now() < args.expires <= self.system.now() + args.max_age,
                'expiry outside configured maximum age')
        source = self.system.source(Path(args.source), args.commit)
        with self.lock():
            entries = [p for p in self.candidates.iterdir() if p.name != '.control']
            used = 0
            for entry in entries:
                _, m = self.manifest(entry.name)
                require(m['state'] in ('complete', 'sealed'), 'incomplete candidate blocks allocation')
                require(self.system.now() - m['created'] <= args.max_age, 'candidate age budget exhausted')
                used += max(m['planned_bytes'], sum(r['allocated'] for r in self.tree(entry, hash_files=False).values()))
            require(len(entries) + 1 <= args.max_count and used + args.bytes <= args.max_bytes,
                    'candidate count/byte budget exhausted; no automatic eviction')
            self.capacity(args.bytes, args.inodes, args.reserve_bytes)
            path = self.candidates / name
            require(not path.exists() and not path.is_symlink(), 'candidate already exists')
            journal, operation = self.begin('allocate', name)
            path.mkdir(mode=0o700, exist_ok=False)
            m = dict(schema=1, id=name, root=self.root_identity, candidate=identity(path), owner=args.owner,
                     created=self.system.now(), expires=args.expires, state='incomplete', source=source,
                     planned_bytes=args.bytes, planned_inodes=args.inodes, max_bytes=args.max_bytes,
                     reserve_bytes=args.reserve_bytes, reproducible=False, files={})
            atomic(path / 'manifest.json', m)
            (path / 'build').mkdir(mode=0o700)
            fsync_dir(path)
            fsync_dir(self.candidates)
            self.system.checkpoint('allocated')
            self.commit(journal, operation)
            return dict(candidate=name, state='incomplete', source=source)

    def capacity(self, planned_bytes, planned_inodes, reserve_bytes):
        c = self.system.capacity(self.root)
        require(all(type(c.get(k)) is int and c[k] > 0 for k in ('total', 'free', 'inodes', 'free_inodes')),
                'capacity unknown')
        require(c['free'] - planned_bytes >= max(10 * GIB, c['total'] * .15, reserve_bytes),
                'insufficient projected byte headroom')
        require(c['free_inodes'] - planned_inodes >= c['inodes'] * .10,
                'insufficient projected inode headroom')

    def finish(self, candidate, seal=False):
        with self.lock():
            path, m = self.manifest(candidate)
            require(m['state'] == ('complete' if seal else 'incomplete'), 'invalid state transition')
            self.system.source(Path(m['source']['path']), m['source']['commit'])
            require(not list((self.control / 'references').glob('*.json')), 'consumer references protected')
            require(set(p.name for p in path.iterdir()) == {'manifest.json', 'build'}, 'unknown candidate data')
            rows = self.tree(path / 'build')
            all_rows = self.tree(path, hash_files=False)
            require(sum(r['allocated'] for r in all_rows.values()) <= m['planned_bytes'] and
                    len(all_rows) + 1 <= m['planned_inodes'], 'actual growth exceeded reservation')
            self.capacity(0, 0, m['reserve_bytes'])
            require(self.system.reproducible(path, m['source'], rows), 'build provenance unproven')
            if seal:
                require(rows == m['files'], 'completed contents changed')
                self.observe()
            journal, operation = self.begin('seal' if seal else 'complete', candidate)
            m.update(state='sealed' if seal else 'complete', files=rows, reproducible=True)
            require(len(encoded(m)) <= 1024 * 1024, 'manifest too large')
            atomic(path / 'manifest.json', m)
            actual = self.tree(path, hash_files=False)
            require(sum(r['allocated'] for r in actual.values()) <= m['planned_bytes'],
                    'completed metadata exceeded reservation; reconcile pending journal')
            self.commit(journal, operation)
            return dict(candidate=candidate, state=m['state'])

    def reference(self, candidate, token, release=False):
        safe_name(token)
        with self.lock():
            self.observe()
            path, m = self.manifest(candidate)
            p = self.control / 'references' / (token + '.json')
            if release:
                require(read_json(p).get('candidate') == candidate, 'reference mismatch')
                journal, operation = self.begin('release', candidate)
                p.unlink()
                fsync_dir(p.parent)
            else:
                require(m['state'] == 'complete', 'new consumer reference forbidden after seal')
                require(not p.exists(), 'reference token already exists')
                journal, operation = self.begin('acquire', candidate)
                atomic(p, dict(candidate=candidate, token=token))
            self.commit(journal, operation)
            return dict(candidate=candidate, reference=token, released=release)

    def plan(self, ttl=300):
        require(0 < ttl <= 300, 'plan lifetime must be at most 300 seconds')
        inventory = self.inventory()
        items = []
        observation = self.system.observation(self.root)
        for row in inventory['items']:
            if not row['protected']:
                candidate = Path(row['path']).name
                path, m = self.eligible(candidate)
                items.append(dict(id=candidate, identity=identity(path), manifest=digest(m)))
        plan = dict(schema=1, root=str(self.root), root_identity=self.root_identity, uuid=UUID,
                    generation=observation.get('generation'), protection=digest(observation),
                    created=self.system.now(), expires=self.system.now()+ttl, mount=self.mount, items=items)
        return dict(plan=plan, digest=digest(plan), inventory=inventory)

    def apply(self, envelope, approval, allow):
        plan = envelope['plan']
        require(approval == digest(plan) == envelope['digest'], 'exact plan digest required')
        require(set(allow) == {x['id'] for x in plan['items']} and len(allow) == len(plan['items']),
                'exact candidate allowlist required')
        results = []
        with self.lock():
            require(plan['root'] == str(self.root) and plan['root_identity'] == self.root_identity and
                    plan['uuid'] == UUID and plan['mount'] == self.mount, 'plan root mismatch')
            require(plan['created'] <= self.system.now() <= plan['expires'], 'stale plan')
            observation = self.observe()
            require(not observation['references'] and digest(observation) == plan['protection'] and
                    observation['generation'] == plan['generation'], 'protection changed')
            # Validate the whole allowlist before the first transition.
            for item in plan['items']:
                path, m = self.eligible(item['id'])
                require(identity(path) == item['identity'] and digest(m) == item['manifest'], 'stale candidate')
            for item in plan['items']:
                self.validate()
                require(digest(self.observe()) == plan['protection'], 'protection changed')
                path, m = self.eligible(item['id'])
                require(identity(path) == item['identity'] and digest(m) == item['manifest'], 'stale candidate')
                journal = self.control / 'journal' / (approval + '-' + item['id'] + '.json')
                operation = dict(state='pending', operation='remove', candidate=item['id'], identity=item['identity'], plan=approval)
                atomic(journal, operation)
                self.system.checkpoint('before_quarantine')
                target = self.control / 'quarantine' / item['id']
                # The checkpoint can represent a paused operation: do not move
                # a replacement object installed since approval was checked.
                self.validate()
                require(digest(self.observe()) == plan['protection'], 'protection changed')
                source_parent = open_dir(self.candidates)
                target_parent = open_dir(target.parent)
                try:
                    require(identity_at(source_parent, item['id']) == item['identity'],
                            'candidate replaced before quarantine')
                    require(not os.listdir(target_parent), 'quarantine no longer empty')
                    os.rename(item['id'], item['id'], src_dir_fd=source_parent, dst_dir_fd=target_parent)
                    os.fsync(source_parent)
                    os.fsync(target_parent)
                finally:
                    os.close(source_parent)
                    os.close(target_parent)
                fsync_dir(target.parent)
                self.system.checkpoint('after_quarantine')
                require(identity(target) == item['identity'], 'quarantine identity changed')
                require(digest(self.observe()) == plan['protection'], 'protection changed')
                require(digest(read_json(target / 'manifest.json')) == item['manifest'], 'quarantined manifest changed')
                self.tree(target / 'build', m['files'])
                require(set(p.name for p in target.iterdir()) == {'manifest.json', 'build'},
                        'unknown quarantined data')
                approved_tree = self.tree(target)
                self.remove(target, plan['protection'], approved_tree)
                self.system.checkpoint('before_commit')
                operation['state'] = 'done'
                atomic(journal, operation)
                self.system.checkpoint('after_commit')
                results.append(dict(candidate=item['id'], state='removed'))
        return dict(results=results)

    def begin(self, action, candidate):
        journal = self.control / 'journal' / (uuid.uuid4().hex + '.json')
        operation = dict(state='pending', operation=action, candidate=candidate)
        atomic(journal, operation)
        return journal, operation

    def commit(self, journal, operation):
        operation['state'] = 'done'
        atomic(journal, operation)

    def remove(self, path, protection, approved_tree):
        fd = open_dir(path)
        try:
            mount = self.system.mount_id(fd)
            def walk(parent, prefix=''):
                for name in sorted(os.listdir(parent)):
                    rel = prefix + name
                    require(rel in approved_tree, 'unknown data during removal')
                    expected = approved_tree[rel]
                    s = os.stat(name, dir_fd=parent, follow_symlinks=False)
                    require(s.st_dev == self.device, 'foreign device during removal')
                    require([s.st_dev, s.st_ino] == expected['identity'],
                            'entry replaced during removal')
                    if stat.S_ISDIR(s.st_mode):
                        child = os.open(name, NOFOLLOW, dir_fd=parent)
                        try:
                            require(self.system.mount_id(child) == mount, 'mount changed during removal')
                            require(identity_fd(child) == expected['identity'], 'directory replaced')
                            walk(child, rel + '/')
                            require(identity_fd(child) == identity_at(parent, name), 'directory swapped')
                        finally:
                            os.close(child)
                        self.validate()
                        require(digest(self.observe()) == protection, 'protection changed during removal')
                        os.rmdir(name, dir_fd=parent)
                    else:
                        require(stat.S_ISREG(s.st_mode) and s.st_nlink == 1, 'unsafe removal entry')
                        handle = os.open(name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=parent)
                        try:
                            require(identity_fd(handle) == expected['identity'], 'file replaced during removal')
                            h = hashlib.sha256()
                            while chunk := os.read(handle, 1024 * 1024):
                                h.update(chunk)
                            require(h.hexdigest() == expected['sha256'], 'file changed during removal')
                            self.validate()
                            require(digest(self.observe()) == protection, 'protection changed during removal')
                            require(identity_at(parent, name) == expected['identity'], 'file swapped before unlink')
                            os.unlink(name, dir_fd=parent)
                        finally:
                            os.close(handle)
                    self.system.checkpoint('partial_removal')
                os.fsync(parent)
            walk(fd)
            require(identity_fd(fd) == identity(path), 'quarantine swapped')
            self.validate()
            require(digest(self.observe()) == protection, 'protection changed during removal')
            parent = open_dir(path.parent)
            try:
                require(identity_at(parent, path.name) == identity_fd(fd), 'quarantine moved')
                os.rmdir(path.name, dir_fd=parent)
                os.fsync(parent)
            finally:
                os.close(parent)
            fsync_dir(path.parent)
        finally:
            os.close(fd)


def identity_fd(fd):
    s = os.fstat(fd)
    return [s.st_dev, s.st_ino]


def identity_at(fd, name):
    s = os.stat(name, dir_fd=fd, follow_symlinks=False)
    return [s.st_dev, s.st_ino]


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', default=str(ROOT))
    sub = p.add_subparsers(dest='command')
    sub.add_parser('inventory')
    sub.add_parser('plan')
    a = sub.add_parser('allocate')
    for name in ('candidate', 'owner', 'source', 'commit'):
        a.add_argument('--'+name, required=True)
    for name in ('bytes', 'inodes', 'max-count', 'max-bytes', 'max-age'):
        a.add_argument('--'+name, required=True, type=int)
    a.add_argument('--expires', required=True, type=float)
    a.add_argument('--reserve-bytes', type=int, default=10*GIB)
    for command in ('complete', 'seal'):
        sub.add_parser(command).add_argument('candidate')
    for command in ('acquire', 'release'):
        a = sub.add_parser(command)
        a.add_argument('candidate')
        a.add_argument('token')
    a = sub.add_parser('apply')
    a.add_argument('--plan-path', required=True)
    a.add_argument('--digest', required=True)
    a.add_argument('--candidate', action='append', required=True)
    return p


def main(argv=None, *, system=None):
    args = parser().parse_args(argv)
    try:
        s = Storage(args.root, system)
        command = args.command or 'plan'
        if command == 'inventory':
            result = s.inventory()
        elif command == 'plan':
            result = s.plan()
        elif command == 'allocate':
            result = s.allocate(args)
        elif command in ('complete', 'seal'):
            result = s.finish(args.candidate, command == 'seal')
        elif command in ('acquire', 'release'):
            result = s.reference(args.candidate, args.token, command == 'release')
        else:
            result = s.apply(read_json(Path(args.plan_path)), args.digest, args.candidate)
        print(json.dumps(result, sort_keys=True))
        return 0
    except (Refused, OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        # Never echo arbitrary OS, Git, JSON or credential contents.
        reason = str(exc) if isinstance(exc, Refused) else 'unsafe or unavailable state'
        print(json.dumps(dict(status='refused', reason=reason)), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
