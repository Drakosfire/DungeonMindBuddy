#!/usr/bin/env python3
"""Explicit local Elderwyld reset. Offline operator use; never a runtime alias.

Run with writers stopped and verified full database/file backups. `plan` seals
all inputs; `files`, `adopt`, `retire`, and `quarantine` are replayable stages.
Database URLs come only from the normal environment. Original source bytes and
saved document IDs are retained. Old semantic facts are deliberately not copied.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

OLD = 'eldyrwild'
NEW = 'elderwyld'
OLD_ROOT = 'corpus/eldyrwild-markdown'
NEW_ROOT = 'corpus/elderwyld-markdown'
APP_ENV = 'DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL'
GRAPH_ENV = 'DUNGEONMIND_WORLD_GRAPH_AUTHORITY_DATABASE_URL'


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical(value) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.pending')
    with temp.open('xb') as stream:
        stream.write(canonical(value))
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temp, path)


def inventory(root: Path, prefixes: tuple[str, ...]) -> dict[str, str]:
    result = {}
    for prefix in prefixes:
        base = root / prefix
        if not base.is_dir() or base.is_symlink():
            raise ValueError(f'Expected real directory: {prefix}')
        for path in sorted(base.rglob('*')):
            if path.is_symlink():
                raise ValueError(f'Symlink refused: {path.relative_to(root)}')
            if not path.resolve().is_relative_to(root.resolve()):
                raise ValueError('Source path escapes root')
            if path.is_file():
                result[path.relative_to(root).as_posix()] = digest(path.read_bytes())
    return result


def file_plan(root: Path) -> dict:
    before = inventory(root, (OLD_ROOT, NEW_ROOT, 'out/registries'))
    copies = {}
    folded = {p.casefold(): p for p in before if p.startswith(NEW_ROOT + '/')}
    for source, sha in before.items():
        if not source.startswith(OLD_ROOT + '/'):
            continue
        target = NEW_ROOT + source[len(OLD_ROOT):]
        collision = folded.get(target.casefold())
        if collision is not None and collision != target:
            raise ValueError(f'Case collision: {source} and {collision}')
        if target in before and before[target] != sha:
            raise ValueError(f'Different bytes at canonical target: {target}')
        folded[target.casefold()] = target
        copies[source] = target
    replacements = {}
    for name in ('workspace_documents.json', 'source_artifacts.json', 'recap_artifacts.json'):
        rel = 'out/registries/' + name
        obj = json.loads((root / rel).read_bytes())
        kept = []
        for record in obj['records']:
            if name == 'workspace_documents.json':
                if record.get('world_id') == OLD:
                    record['world_id'] = NEW
                target = record.get('target_relpath')
                if isinstance(target, str) and target.startswith(OLD_ROOT + '/'):
                    if record.get('world_id') not in (None, OLD, NEW) or record.get('campaign_id') not in ('longmont-c1', 'longmont-c2', NEW):
                        raise ValueError('Unexpected owner of old source path')
                    record['target_relpath'] = NEW_ROOT + target[len(OLD_ROOT):]
                kept.append(record)
            elif name == 'source_artifacts.json':
                # Immutable old-scope artifacts are archived, never relabeled.
                if record.get('world_id') != OLD:
                    kept.append(record)
            elif str(record.get('source_recap_path', '')).startswith(OLD_ROOT + '/'):
                if record.get('world_id') not in (None, OLD, NEW) or record.get('campaign_id') not in ('longmont-c1', 'longmont-c2'):
                    raise ValueError('Unexpected owner of old recap path')
            else:
                kept.append(record)
        obj['records'] = kept
        replacements[rel] = obj
    return {'before': before, 'copies': copies, 'replacements': replacements}


def apply_files(root: Path, plan: dict) -> None:
    expected = dict(plan['before'])
    for source, target in plan['copies'].items():
        expected[target] = expected[source]
    for rel, payload in plan['replacements'].items():
        current = digest((root / rel).read_bytes())
        if current not in (plan['before'][rel], digest(canonical(payload))):
            raise ValueError(f'Registry drift: {rel}')
    actual = inventory(root, (OLD_ROOT, NEW_ROOT, 'out/registries'))
    for rel, sha in actual.items():
        accepted = {expected.get(rel)}
        if rel in plan['replacements']:
            accepted.add(digest(canonical(plan['replacements'][rel])))
        if sha not in accepted:
            raise ValueError(f'File drift: {rel}')
    if set(plan['before']) - set(actual):
        raise ValueError('Preserved input file disappeared')
    for source, target in plan['copies'].items():
        dst = root / target
        if not dst.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            with dst.open('xb') as stream:
                stream.write((root / source).read_bytes())
        if digest(dst.read_bytes()) != plan['before'][source]:
            raise ValueError(f'Copy did not preserve bytes: {target}')
    for rel, payload in plan['replacements'].items():
        if digest((root / rel).read_bytes()) != digest(canonical(payload)):
            write_json(root / rel, payload)


def db_identity(conn):
    return list(conn.execute('SELECT current_database(), inet_server_addr()::text, inet_server_port()').fetchone())


def connect(env: str):
    import psycopg
    return psycopg.connect(os.environ[env])


def table_fingerprints(conn) -> dict:
    from psycopg import sql
    tables = conn.execute("SELECT table_schema,table_name FROM information_schema.tables WHERE table_type='BASE TABLE' AND table_schema NOT IN ('pg_catalog','information_schema') ORDER BY 1,2").fetchall()
    out = {}
    for schema, table in tables:
        rows = conn.execute(sql.SQL('SELECT to_jsonb(t)::text FROM {} t').format(sql.Identifier(schema, table))).fetchall()
        out[schema + '.' + table] = {'rows': len(rows), 'sha256': digest(canonical(sorted(r[0] for r in rows)))}
    return out


def scopes(conn, *, graph: bool) -> dict[str, str]:
    """Only exact namespace roots plus explicit dependent source/thread joins."""
    columns = conn.execute("SELECT table_schema,table_name,column_name FROM information_schema.columns WHERE table_schema NOT IN ('pg_catalog','information_schema')").fetchall()
    result = {}
    for schema, table, column in columns:
        if graph and schema == 'dungeonmind' and column in ('world_id', 'space_id'):
            result[schema + '.' + table] = f"{column} = 'eldyrwild'"
    if graph:
        result.update({
            'dungeonmind.source_revisions': "source_artifact_id IN (SELECT source_artifact_id FROM dungeonmind.source_artifacts WHERE world_id='eldyrwild')",
            'dungeonmind.evidence_refs': "source_artifact_id IN (SELECT source_artifact_id FROM dungeonmind.source_artifacts WHERE world_id='eldyrwild')",
            'dungeonmind.mind_turns': "thread_id IN (SELECT thread_id FROM dungeonmind.mind_threads WHERE world_id='eldyrwild')",
        })
    else:
        result = {
            'source.revision': "source_artifact_id IN (SELECT source_artifact_id FROM source.artifact WHERE world_id='eldyrwild')",
            'source.artifact': "world_id='eldyrwild'",
        }
        # Unique writing under any other old-scope APP owner must be designed
        # explicitly, not silently removed by a generic World reset.
        for schema, table, column in columns:
            if column == 'world_id' and (schema, table) != ('source', 'artifact'):
                from psycopg import sql
                n = conn.execute(sql.SQL('SELECT count(*) FROM {} WHERE world_id=%s').format(sql.Identifier(schema, table)), (OLD,)).fetchone()[0]
                if n:
                    raise ValueError(f'Unplanned old-scope APP owner: {schema}.{table}')
    return result


def canonical_space_state(conn) -> dict:
    from psycopg import sql
    tables = conn.execute("SELECT table_schema,table_name FROM information_schema.columns WHERE table_schema='dungeonmind' AND column_name='space_id' ORDER BY 1,2").fetchall()
    out = {}
    for schema, table in tables:
        rows = conn.execute(sql.SQL('SELECT to_jsonb(t)::text FROM {} t WHERE space_id=%s').format(sql.Identifier(schema, table)), (NEW,)).fetchall()
        out[schema + '.' + table] = {'rows': len(rows), 'sha256': digest(canonical(sorted(r[0] for r in rows)))}
    return out


def require_vnext_adoption_state(actual: dict, owned_after: dict | None) -> None:
    if any(value['rows'] for value in actual.values()) and actual != owned_after:
        raise ValueError('Canonical vNext authority appeared after planning')


def retirement_plan(conn, *, graph: bool) -> dict:
    from psycopg import sql
    selected = {}
    for table, predicate in scopes(conn, graph=graph).items():
        rows = conn.execute(sql.SQL('SELECT to_jsonb(t)::text FROM {} t WHERE ').format(sql.Identifier(*table.split('.'))) + sql.SQL(predicate)).fetchall()
        selected[table] = {'predicate': predicate, 'rows': len(rows), 'sha256': digest(canonical(sorted(r[0] for r in rows)))}
    return selected


def retire(conn, plan: dict) -> None:
    """Delete a sealed exact selection in one transaction, honoring all FKs.

    Materialize selected row identities before deletes so child predicates do
    not disappear after their parents. No CASCADE, trigger bypass or renaming.
    """
    import psycopg
    from psycopg import sql
    before = table_fingerprints(conn)
    pending = []
    survivors = {}
    for index, (table, spec) in enumerate(sorted(plan.items())):
        ident = sql.Identifier(*table.split('.'))
        rows = conn.execute(sql.SQL('SELECT to_jsonb(t)::text FROM {} t WHERE ').format(ident) + sql.SQL(spec['predicate'])).fetchall()
        if {'predicate': spec['predicate'], 'rows': len(rows), 'sha256': digest(canonical(sorted(r[0] for r in rows)))} != spec:
            raise ValueError(f'Retirement selection drift: {table}')
        survivors[table] = digest(canonical(sorted(r[0] for r in conn.execute(sql.SQL('SELECT to_jsonb(t)::text FROM {} t WHERE NOT (').format(ident) + sql.SQL(spec['predicate']) + sql.SQL(') OR (') + sql.SQL(spec['predicate']) + sql.SQL(') IS NULL')).fetchall())))
        temp = sql.Identifier(f'reset_selection_{index}')
        conn.execute(sql.SQL('CREATE TEMP TABLE {} ON COMMIT DROP AS SELECT ctid AS row_id FROM {} WHERE ').format(temp, ident) + sql.SQL(spec['predicate']))
        pending.append((table, temp))
    while pending:
        next_pending = []
        for table, temp in pending:
            try:
                with conn.transaction():
                    conn.execute(sql.SQL('DELETE FROM {} WHERE ctid IN (SELECT row_id FROM {})').format(sql.Identifier(*table.split('.')), temp))
            except psycopg.errors.ForeignKeyViolation:
                next_pending.append((table, temp))
        if len(next_pending) == len(pending):
            raise ValueError('Unexpected foreign-key dependency; retirement rolled back')
        pending = next_pending
    after = table_fingerprints(conn)
    for table in before:
        expected_rows = before[table]['rows'] - plan.get(table, {}).get('rows', 0)
        if after[table]['rows'] != expected_rows:
            raise ValueError(f'Unexpected delete effects: {table}')
        if table in plan:
            rows = conn.execute(sql.SQL('SELECT to_jsonb(t)::text FROM {} t').format(sql.Identifier(*table.split('.')))).fetchall()
            if digest(canonical(sorted(r[0] for r in rows))) != survivors[table]:
                raise ValueError(f'Unselected rows changed: {table}')
        if table not in plan or plan[table]['rows'] == 0:
            if after[table] != before[table]:
                raise ValueError(f'Unselected table changed: {table}')


def empty_bundle(plan_sha: str) -> bytes:
    from dungeonmind_dnd.application.world_object_vocabulary import load_builtin_v3_descriptor
    from dungeonmind.contracts.existing_world_adoption import ExistingWorldAdoptionBundleV2, existing_world_adoption_bundle_v2_canonical_bytes
    descriptor = load_builtin_v3_descriptor()
    from dungeonmind.application.semantic_profiles import descriptor_sha256
    graph = {'world_id': NEW, 'objects': [], 'relationships': [], 'evidence_refs': [],
             'relationship_endpoint_aspect_schema': 'dm_relationship_endpoint_aspect_v1',
             'semantic_profile': {'profile_id': descriptor.profile_id, 'profile_revision': descriptor.profile_revision,
                                  'schema_version': 'dm_semantic_profile_ref_v1', 'descriptor_sha256': descriptor_sha256(descriptor)}}
    bundle = ExistingWorldAdoptionBundleV2.model_validate({
        'adoption_id': 'elderwyld-empty-reset:' + plan_sha, 'world_id': NEW,
        'source_provenance': {'producer_id': 'buddy-operator-empty-reset', 'producer_revision': plan_sha,
            'source_world_revision_id': 'empty-reset-snapshot:' + digest(canonical(graph)),
            'source_graph_payload_sha256': digest(canonical(graph)),
            'authority_refs': [{'schema': 'buddy_operator_reset_plan_v1', 'identifier': plan_sha, 'sha256': plan_sha}]},
        'graph_schema': 'dm_union_graph_v6', 'graph_payload': graph, 'source_artifacts': [], 'source_revisions': [],
        'contributions': [], 'identity_decisions': []})
    return existing_world_adoption_bundle_v2_canonical_bytes(bundle)


def adopt(root: Path, raw: bytes, expected_world: dict):
    from dungeonmind.application.existing_world_adoption import adopt_existing_world
    from dungeonmind.application.graph_snapshot import VersionedUnionGraphSnapshotReader
    from dungeonmind.infrastructure.semantic_profiles import StaticSemanticProfileRegistry
    from dungeonmind.infrastructure.postgres import PostgresDatabase, PostgresRepositoryBundle
    from dungeonmind_dnd.application.world_object_vocabulary import load_builtin_v3_descriptor
    from apps.live_control_server.integrations.dungeonmind.world_graph_reads import direct_services_from_bundle
    from apps.live_control_server.services.world_graph_binding import bind_native_graph, deactivate_native_graph_binding
    from apps.live_control_server.services.world_container_registry import get_world_container
    current = get_world_container(root, NEW)
    actual = current.model_dump(mode='json')
    original_binding = expected_world['native_graph_binding']
    actual_binding = actual['native_graph_binding']
    if {k:v for k,v in actual.items() if k != 'native_graph_binding'} != {k:v for k,v in expected_world.items() if k != 'native_graph_binding'}:
        raise ValueError('Managed World identity drift')
    allowed = {(OLD, 'active', original_binding['binding_version']),
               (OLD, 'inactive', original_binding['binding_version'] + 1),
               (NEW, 'active', original_binding['binding_version'] + 2)}
    if actual_binding is None or (actual_binding['native_world_id'], actual_binding['status'], actual_binding['binding_version']) not in allowed:
        raise ValueError('Managed binding drift before adoption')
    bundle = PostgresRepositoryBundle(PostgresDatabase(os.environ[GRAPH_ENV]))
    receipt = adopt_existing_world(raw, adopted_at=datetime.now(timezone.utc), adoption_repository=bundle.existing_world_adoptions,
        graph_reader=VersionedUnionGraphSnapshotReader(profile_registry=StaticSemanticProfileRegistry([load_builtin_v3_descriptor()])))
    current = get_world_container(root, NEW)
    binding = current.native_graph_binding
    if binding is None or binding.native_world_id not in (OLD, NEW):
        raise ValueError('Unexpected managed binding')
    if binding.native_world_id == OLD and binding.status == 'active':
        current = deactivate_native_graph_binding(root, NEW, expected_binding_version=binding.binding_version)
    bind_native_graph(root, NEW, native_world_id=NEW, expected_binding_version=current.native_graph_binding.binding_version,
        authority_validator=lambda wid: direct_services_from_bundle(bundle, wid))
    return receipt.model_dump(mode='json')


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=('plan', 'files', 'adopt', 'retire', 'admit', 'quarantine'))
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--case', type=Path, required=True)
    args = parser.parse_args()
    root, case = args.root.resolve(), args.case.resolve()
    if case.is_relative_to(root):
        raise ValueError('Evidence must live outside the mutable data root')
    case.mkdir(parents=True, exist_ok=True, mode=0o700)
    for key in ('DMB_MANAGED_WORLD_DATA_ROOT', 'DMB_ARTIFACT_DATA_ROOT'):
        if os.environ.get(key) and Path(os.environ[key]).resolve() != root:
            raise ValueError('Configured data root differs from explicit target')
        os.environ[key] = str(root)
    plan_path = case / 'operation-plan.json'
    if args.stage == 'plan':
        if plan_path.exists():
            raise ValueError('Plan already sealed; reuse it')
        with connect(APP_ENV) as app, connect(GRAPH_ENV) as graph:
            for table, column in (('worlds','world_id'), ('knowledge_spaces','space_id')):
                if graph.execute(f'SELECT 1 FROM dungeonmind.{table} WHERE {column}=%s', (NEW,)).fetchone():
                    raise ValueError('Canonical native namespace is occupied')
            from apps.live_control_server.services.world_container_registry import get_world_container
            world = get_world_container(root, NEW).model_dump(mode='json')
            if world['native_graph_binding']['native_world_id'] != OLD or world['native_graph_binding']['status'] != 'active':
                raise ValueError('Expected original active old binding')
            plan = {'tool_sha256': digest(Path(__file__).read_bytes()), 'managed_world': world, 'schema': 'buddy_operator_reset_plan_v1', 'root': str(root),
                    'app_identity': db_identity(app), 'graph_identity': db_identity(graph), 'files': file_plan(root),
                    'app_before': table_fingerprints(app), 'graph_before': table_fingerprints(graph),
                    'app_retire': retirement_plan(app, graph=False), 'graph_retire': retirement_plan(graph, graph=True)}
            from scripts.restore_elderwyld_campaigns import campaign_rows, normalize_rows
            plan['campaigns'] = normalize_rows(campaign_rows(graph, OLD))
            plan['campaign_tool_sha256'] = digest(Path(__file__).with_name('restore_elderwyld_campaigns.py').read_bytes())
        write_json(plan_path, plan)
        print('Plan sealed; no live changes')
        return
    plan = json.loads(plan_path.read_bytes())
    if plan['tool_sha256'] != digest(Path(__file__).read_bytes()):
        raise ValueError('Plan requires the original exact operator tool')
    if plan['campaign_tool_sha256'] != digest(Path(__file__).with_name('restore_elderwyld_campaigns.py').read_bytes()):
        raise ValueError('Plan requires the original campaign migration helper')
    if plan['root'] != str(root):
        raise ValueError('Plan belongs to another source root')
    for env, name in ((APP_ENV, 'app'), (GRAPH_ENV, 'graph')):
        with connect(env) as conn:
            if db_identity(conn) != plan[name + '_identity']:
                raise ValueError('Plan belongs to another database')
    if args.stage == 'files':
        apply_files(root, plan['files'])
    elif args.stage == 'adopt':
        # Refuse a writer change before authority transition. Exact replay after
        # adoption is separately checked by Core's original bundle identity.
        with connect(APP_ENV) as conn:
            if not (case / 'app-retired.json').exists() and table_fingerprints(conn) != plan['app_before']:
                raise ValueError('APP drift before adoption')
        with connect(GRAPH_ENV) as conn:
            proof_path = case / 'canonical-native-after-admission.json'
            owned = json.loads(proof_path.read_bytes()) if proof_path.exists() else None
            require_vnext_adoption_state(canonical_space_state(conn), owned)
        raw = empty_bundle(digest(canonical(plan)))
        receipt = adopt(root, raw, plan['managed_world'])
        write_json(case / 'empty-adoption-receipt.json', receipt)
    elif args.stage == 'retire':
        from apps.live_control_server.services.world_container_registry import get_world_container
        binding = get_world_container(root, NEW).native_graph_binding
        if binding is None or binding.native_world_id != NEW or binding.status != 'active':
            raise ValueError('Canonical binding must be active before old namespace retirement')
        for env, name in ((APP_ENV, 'app'), (GRAPH_ENV, 'graph')):
            done = case / (name + '-retired.json')
            intent = case / (name + '-retirement-intent.json')
            with connect(env) as conn:
                from scripts.restore_elderwyld_campaigns import lock_tables, campaign_rows, normalize_rows, transfer_campaigns, head_state
                lock_tables(conn)
                current = table_fingerprints(conn)
                if done.exists():
                    if current != json.loads(done.read_bytes()):
                        raise ValueError('Database changed after retirement')
                    continue
                if intent.exists():
                    sealed = json.loads(intent.read_bytes())
                    if current == sealed['after']:
                        write_json(done, current)
                        continue
                    if current != sealed['before']:
                        raise ValueError('Interrupted retirement has unexpected state')
                if name == 'app' and current != plan['app_before']:
                    raise ValueError('APP drift since sealed plan')
                if name == 'graph':
                    receipt = json.loads((case / 'empty-adoption-receipt.json').read_bytes())
                    if head_state(conn)['head_revision_id'] != receipt['published_revision_id']:
                        raise ValueError('Canonical head changed before campaign transfer')
                    if normalize_rows(campaign_rows(conn, OLD)) != plan['campaigns']:
                        raise ValueError('Original campaign metadata drift')
                    transfer_campaigns(conn, plan['campaigns'])
                retire(conn, plan[name + '_retire'])
                proof = table_fingerprints(conn)
                proposed = {'before': current, 'after': proof}
                if intent.exists():
                    if json.loads(intent.read_bytes()) != proposed:
                        raise ValueError('Retirement replay differs')
                else:
                    # Written before commit: recover the commit/journal gap by
                    # exact whole-database fingerprints, never by an empty list.
                    write_json(intent, proposed)
            write_json(done, proof)
    elif args.stage == 'admit':
        if not (case / 'app-retired.json').exists() or not (case / 'graph-retired.json').exists():
            raise ValueError('Retire the sealed old namespace before admitting authored sources')
        from apps.live_control_server.services.workspace_document_registry import get_workspace_document_snapshot
        from apps.live_control_server.integrations.dungeonmind.native_world_source_admission import admit_native_world_source
        records = json.loads((root / 'out/registries/workspace_documents.json').read_bytes())['records']
        results = []
        for record in records:
            if record.get('world_id') != NEW or record.get('kind') != 'worldbuilding_source' or record.get('status') != 'active':
                continue
            snapshot = get_workspace_document_snapshot(root, record['document_id'])
            if record.get('content_status') != 'committed':
                results.append({'document_id': record['document_id'], 'state': 'draft_preserved_not_published'})
                continue
            status = admit_native_world_source(root, record['document_id'], expected_revision=record['revision'], expected_body_sha256=snapshot.content_sha256)
            if status.state != 'admitted' or status.space_id != NEW:
                raise ValueError('Native source admission did not establish canonical evidence')
            results.append(status.model_dump(mode='json'))
        write_json(case / 'native-admissions.json', results)
        with connect(GRAPH_ENV) as conn:
            write_json(case / 'canonical-native-after-admission.json', canonical_space_state(conn))
    else:
        if not (case / 'native-admissions.json').exists() or not (case / 'graph-retired.json').exists():
            raise ValueError('Retirement and authored source proof required before quarantine')
        target = case / 'retired-source-tree'
        old = root / OLD_ROOT
        for source, destination in plan['files']['copies'].items():
            if digest((root / destination).read_bytes()) != plan['files']['before'][source]:
                raise ValueError('Canonical bytes changed before quarantine')
        expected_old = {p[len(OLD_ROOT)+1:]: sha for p, sha in plan['files']['before'].items() if p.startswith(OLD_ROOT + '/')}
        if old.exists():
            if inventory(old, ('',)) != expected_old:
                raise ValueError('Old source tree changed before quarantine')
            if target.exists():
                raise ValueError('Quarantine collision')
            os.rename(old, target)
        elif not target.is_dir():
            raise ValueError('Neither old tree nor quarantine exists')
        if inventory(target, ('',)) != expected_old:
            raise ValueError('Quarantined bytes differ from sealed originals')
    print(args.stage + ' completed')


if __name__ == '__main__':
    main()
