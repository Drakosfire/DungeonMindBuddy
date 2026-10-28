#!/usr/bin/env python3
"""Offline, explicit campaign metadata repair; never called by runtime reads.

Seal a plan from the original PostgreSQL custom-format backup with `plan`, then
apply that exact plan with writers stopped. The donor SQL is read, never run.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess

from scripts.consolidate_elderwyld import (
    GRAPH_ENV, NEW, OLD, canonical, connect, db_identity, digest,
    table_fingerprints, write_json,
)

CAMPAIGNS = {'longmont-c1', 'longmont-c2'}


def normalize_rows(rows):
    normalized = []
    for row in rows:
        if set(row) != {'world_id', 'campaign_id', 'created_at'} or row['world_id'] != OLD:
            raise ValueError('Unexpected donor World or campaign fields')
        stamp = datetime.fromisoformat(row['created_at'])
        if stamp.tzinfo is None:
            raise ValueError('Campaign timestamp requires timezone')
        normalized.append(dict(row, created_at=stamp.astimezone(timezone.utc).isoformat()))
    if len(normalized) != 2 or {r['campaign_id'] for r in normalized} != CAMPAIGNS:
        raise ValueError('Expected exactly the two original campaign memberships')
    return sorted(normalized, key=lambda r: r['campaign_id'])


def donor_rows(dump: Path, container: str):
    with dump.open('rb') as stream:
        raw = subprocess.run(
            ['docker', 'exec', '-i', container, 'pg_restore', '--data-only',
             '--schema=dungeonmind', '--table=campaigns', '--file=-'],
            stdin=stream, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True,
        ).stdout.decode('utf-8')
    marker = 'COPY dungeonmind.campaigns (world_id, campaign_id, created_at) FROM stdin;\n'
    if raw.count(marker) != 1:
        raise ValueError('Backup does not contain exactly one campaign data section')
    lines = raw.split(marker, 1)[1].split('\n\\.\n', 1)[0].splitlines()
    # The original backup may contain other Worlds; only the explicit donor
    # World is selected. Escaped COPY fields fail normalization, never execute.
    rows = [dict(zip(('world_id', 'campaign_id', 'created_at'), line.split('\t'), strict=True))
            for line in lines if line.split('\t', 1)[0] == OLD]
    return normalize_rows(rows)


def campaign_rows(conn, world):
    return [{'world_id': world, 'campaign_id': campaign, 'created_at': stamp.astimezone(timezone.utc).isoformat()}
            for campaign, stamp in conn.execute(
                'SELECT campaign_id,created_at FROM dungeonmind.campaigns WHERE world_id=%s ORDER BY campaign_id', (world,))]


def head_state(conn):
    row = conn.execute('SELECT to_jsonb(h) FROM dungeonmind.world_graph_heads h WHERE world_id=%s', (NEW,)).fetchone()
    if row is None:
        raise ValueError('Canonical Graph head is required')
    return row[0]


def schema_state(conn):
    return [list(row) for row in conn.execute("SELECT table_schema,table_name,column_name,data_type,is_nullable,column_default FROM information_schema.columns WHERE table_schema NOT IN ('pg_catalog','information_schema') ORDER BY 1,2,ordinal_position")]


def lock_tables(conn):
    """Offline migration: exclude all native writers through commit/proof."""
    from psycopg import sql
    tables = conn.execute("SELECT table_schema,table_name FROM information_schema.tables WHERE table_type='BASE TABLE' AND table_schema NOT IN ('pg_catalog','information_schema') ORDER BY 1,2").fetchall()
    for schema, table in tables:
        conn.execute(sql.SQL('LOCK TABLE {} IN SHARE ROW EXCLUSIVE MODE').format(sql.Identifier(schema, table)))


def transfer_campaigns(conn, rows):
    """Caller holds native writer locks and has checked binding/head authority."""
    rows = normalize_rows(rows)
    expected = [dict(row, world_id=NEW) for row in rows]
    if not conn.execute('SELECT 1 FROM dungeonmind.worlds WHERE world_id=%s', (NEW,)).fetchone():
        raise ValueError('Canonical World must already exist')
    actual = campaign_rows(conn, NEW)
    if actual == expected:
        return False
    if actual:
        raise ValueError('Conflicting, partial or unexpected canonical memberships')
    before = table_fingerprints(conn)
    others = conn.execute('SELECT to_jsonb(t)::text FROM dungeonmind.campaigns t WHERE world_id<>%s ORDER BY 1', (NEW,)).fetchall()
    for row in expected:
        conn.execute('INSERT INTO dungeonmind.campaigns (world_id,campaign_id,created_at) VALUES (%s,%s,%s)',
                     (NEW, row['campaign_id'], row['created_at']))
    if campaign_rows(conn, NEW) != expected:
        raise ValueError('Campaign transfer differs from donor')
    after = table_fingerprints(conn)
    others_after = conn.execute('SELECT to_jsonb(t)::text FROM dungeonmind.campaigns t WHERE world_id<>%s ORDER BY 1', (NEW,)).fetchall()
    if others_after != others or after['dungeonmind.campaigns']['rows'] != before['dungeonmind.campaigns']['rows'] + 2:
        raise ValueError('Unexpected campaign survivor changes')
    if any(after.get(table) != value for table, value in before.items() if table != 'dungeonmind.campaigns') or set(after) != set(before):
        raise ValueError('Unexpected campaign transfer effect')
    return True


def apply_repair(conn, plan):
    lock_tables(conn)
    if db_identity(conn) != plan['database'] or head_state(conn) != plan['head'] or schema_state(conn) != plan['columns']:
        raise ValueError('Database or canonical head drift')
    before = table_fingerprints(conn)
    # Replay may differ only by the two exact mapped memberships. Every other
    # retained table must still match the sealed preflight.
    for table, proof in plan['before'].items():
        if table != 'dungeonmind.campaigns' and before.get(table) != proof:
            raise ValueError(f'Native state drift: {table}')
    if set(before) != set(plan['before']):
        raise ValueError('Native schema drift')
    expected = [dict(row, world_id=NEW) for row in normalize_rows(plan['campaigns'])]
    all_other = conn.execute('SELECT to_jsonb(t)::text FROM dungeonmind.campaigns t WHERE world_id<>%s ORDER BY 1', (NEW,)).fetchall()
    if digest(canonical([r[0] for r in all_other])) != plan['other_campaigns_sha256']:
        raise ValueError('Other campaign memberships changed')
    changed = transfer_campaigns(conn, plan['campaigns'])
    after = table_fingerprints(conn)
    for table in before:
        if table != 'dungeonmind.campaigns' and before[table] != after[table]:
            raise ValueError(f'Unexpected migration effect: {table}')
    others_after = conn.execute('SELECT to_jsonb(t)::text FROM dungeonmind.campaigns t WHERE world_id<>%s ORDER BY 1', (NEW,)).fetchall()
    if digest(canonical([r[0] for r in others_after])) != plan['other_campaigns_sha256'] or after['dungeonmind.campaigns']['rows'] != before['dungeonmind.campaigns']['rows'] + (2 if changed else 0):
        raise ValueError('Unexpected campaign survivor changes')
    if campaign_rows(conn, NEW) != expected:
        raise ValueError('Incorrect migrated memberships')
    return {'changed': changed, 'before': before, 'after': after, 'head': head_state(conn)}


def binding(root):
    from apps.live_control_server.services.world_container_registry import get_world_container
    value = get_world_container(root, NEW).model_dump(mode='json')
    native = value['native_graph_binding']
    if native['status'] != 'active' or native['native_world_id'] != NEW:
        raise ValueError('Expected active canonical managed binding')
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=('plan', 'apply'))
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--case', type=Path, required=True)
    parser.add_argument('--donor-dump', type=Path, required=True)
    parser.add_argument('--container', required=True)
    args = parser.parse_args()
    root, case, dump = args.root.resolve(), args.case.resolve(), args.donor_dump.resolve()
    if case.is_relative_to(root):
        raise ValueError('Evidence must be outside mutable source root')
    tool_sha = digest(Path(__file__).read_bytes())
    donor_sha = digest(dump.read_bytes())
    rows = donor_rows(dump, args.container)
    world = binding(root)
    plan_path = case / 'plan.json'
    with connect(GRAPH_ENV) as conn:
        if args.stage == 'plan':
            if plan_path.exists():
                raise ValueError('Plan already sealed')
            lock_tables(conn)
            if campaign_rows(conn, NEW):
                raise ValueError('Expected missing canonical memberships')
            plan = {'schema': 'buddy_elderwyld_campaign_repair_v1', 'tool_sha256': tool_sha,
                    'helper_sha256': digest(Path(__file__).with_name('consolidate_elderwyld.py').read_bytes()),
                    'donor_sha256': donor_sha, 'campaigns': rows, 'root': str(root),
                    'binding': world, 'database': db_identity(conn), 'head': head_state(conn),
                    'before': table_fingerprints(conn), 'columns': schema_state(conn), 'other_campaigns_sha256': digest(canonical([
                        r[0] for r in conn.execute('SELECT to_jsonb(t)::text FROM dungeonmind.campaigns t WHERE world_id<>%s ORDER BY 1', (NEW,))]))}
            case.mkdir(parents=True, exist_ok=True, mode=0o700)
            write_json(plan_path, plan)
        else:
            plan = json.loads(plan_path.read_bytes())
            if any((plan['tool_sha256'] != tool_sha,
                    plan['helper_sha256'] != digest(Path(__file__).with_name('consolidate_elderwyld.py').read_bytes()), plan['donor_sha256'] != donor_sha,
                    plan['campaigns'] != rows, plan['root'] != str(root), plan['binding'] != world)):
                raise ValueError('Sealed repair input drift')
            proof = apply_repair(conn, plan)
            # Evidence written before transaction commit; exact replay recovers
            # any commit/journal gap without guessing from a partial insert.
            write_json(case / 'intent.json', proof)
        conn.commit()
    if args.stage == 'apply':
        write_json(case / 'completed.json', proof)
    print('Campaign repair ' + args.stage + ' complete')


if __name__ == '__main__':
    main()
