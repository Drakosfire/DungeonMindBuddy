"""Real PostgreSQL operator migration safety; no primary state or providers."""
import psycopg
import pytest

from scripts.consolidate_elderwyld import canonical, db_identity, digest, table_fingerprints
from scripts.restore_elderwyld_campaigns import apply_repair, campaign_rows, head_state, normalize_rows, transfer_campaigns, schema_state

ROWS = [{'world_id': 'eldyrwild', 'campaign_id': c, 'created_at': f'2026-08-18T23:40:27.{t}+00:00'}
        for c, t in [('longmont-c1', '304148'), ('longmont-c2', '316195')]]


@pytest.fixture
def state(application_state_dsn):
    with psycopg.connect(application_state_dsn) as conn:
        conn.execute('CREATE SCHEMA dungeonmind')
        conn.execute('CREATE TABLE dungeonmind.worlds (world_id text PRIMARY KEY)')
        conn.execute('CREATE TABLE dungeonmind.campaigns (world_id text REFERENCES dungeonmind.worlds, campaign_id text, created_at timestamptz NOT NULL, PRIMARY KEY(world_id,campaign_id))')
        conn.execute('CREATE TABLE dungeonmind.world_graph_heads (world_id text PRIMARY KEY REFERENCES dungeonmind.worlds, head_revision_id text NOT NULL)')
        conn.execute("INSERT INTO dungeonmind.worlds VALUES ('elderwyld'),('other')")
        conn.execute("INSERT INTO dungeonmind.world_graph_heads VALUES ('elderwyld','empty-reset-head'),('other','preserve-head')")
        conn.execute("INSERT INTO dungeonmind.campaigns VALUES ('other','keep', '2020-01-01Z')")
        conn.commit()
        plan = {'database': db_identity(conn), 'head': head_state(conn), 'before': table_fingerprints(conn),
                'campaigns': ROWS, 'columns': schema_state(conn), 'other_campaigns_sha256': digest(canonical([r[0] for r in conn.execute(
                    "SELECT to_jsonb(t)::text FROM dungeonmind.campaigns t WHERE world_id<>'elderwyld' ORDER BY 1")]))}
        conn.commit()
        yield conn, plan


def test_atomic_exact_transfer_and_replay_preserves_every_other_table(state):
    conn, plan = state
    with conn.transaction():
        proof = apply_repair(conn, plan)
    assert proof['changed']
    assert campaign_rows(conn, 'elderwyld') == [dict(row, world_id='elderwyld') for row in ROWS]
    with conn.transaction():
        replay = apply_repair(conn, plan)
    assert not replay['changed']
    assert replay['before'] == replay['after'] == proof['after']
    assert head_state(conn) == plan['head']


@pytest.mark.parametrize('conflict', ['partial', 'timestamp', 'extra'])
def test_conflicting_canonical_memberships_fail_closed(state, conflict):
    conn, plan = state
    if conflict == 'timestamp':
        transfer_campaigns(conn, ROWS)
        conn.execute("UPDATE dungeonmind.campaigns SET created_at='2020-01-01Z' WHERE world_id='elderwyld'")
    else:
        conn.execute("INSERT INTO dungeonmind.campaigns VALUES ('elderwyld',%s,'2020-01-01Z')", ('longmont-c1' if conflict == 'partial' else 'unexpected',))
    conn.commit()
    before = table_fingerprints(conn)
    with pytest.raises(ValueError, match='Conflicting'):
        with conn.transaction():
            apply_repair(conn, plan)
    assert table_fingerprints(conn) == before


@pytest.mark.parametrize('drift', ['head', 'database', 'other', 'schema'])
def test_wrong_target_or_retained_drift_refuses(state, drift):
    conn, plan = state
    if drift == 'database':
        plan['database'] = ['wrong', None, None]
    elif drift == 'head':
        conn.execute("UPDATE dungeonmind.world_graph_heads SET head_revision_id='newer' WHERE world_id='elderwyld'")
    elif drift == 'other':
        conn.execute("UPDATE dungeonmind.campaigns SET created_at='2021-01-01Z' WHERE world_id='other'")
    else:
        conn.execute('CREATE TABLE dungeonmind.unexpected (id text)')
    conn.commit()
    with pytest.raises(ValueError):
        with conn.transaction():
            apply_repair(conn, plan)
    assert campaign_rows(conn, 'elderwyld') == []


def test_insert_failure_rolls_back_both_memberships(state):
    conn, plan = state
    conn.execute("ALTER TABLE dungeonmind.campaigns ADD CONSTRAINT reject_second CHECK (campaign_id <> 'longmont-c2')")
    conn.commit()
    with pytest.raises(psycopg.errors.CheckViolation):
        with conn.transaction():
            apply_repair(conn, plan)
    assert campaign_rows(conn, 'elderwyld') == []


def test_no_canonical_world_is_created(state):
    conn, _ = state
    conn.execute("DELETE FROM dungeonmind.world_graph_heads WHERE world_id='elderwyld'")
    conn.execute("DELETE FROM dungeonmind.worlds WHERE world_id='elderwyld'")
    conn.commit()
    with pytest.raises(ValueError, match='must already exist'):
        transfer_campaigns(conn, ROWS)


@pytest.mark.parametrize('bad', [[], [ROWS[0]], [ROWS[0], ROWS[0]], [dict(ROWS[0], world_id='other'), ROWS[1]], [dict(ROWS[0], created_at='2020-01-01'), ROWS[1]]])
def test_donor_shape_refuses_missing_wrong_scope_or_ambiguous_dates(bad):
    with pytest.raises(ValueError):
        normalize_rows(bad)


def test_future_consolidation_transfers_membership_before_old_retirement(state):
    from scripts.consolidate_elderwyld import retire
    def retirement_plan_minimal(c):
        result = {}
        for table in ('worlds', 'campaigns', 'world_graph_heads'):
            rows = c.execute(f"SELECT to_jsonb(t)::text FROM dungeonmind.{table} t WHERE world_id='eldyrwild'").fetchall()
            result['dungeonmind.' + table] = {'predicate': "world_id='eldyrwild'", 'rows': len(rows), 'sha256': digest(canonical(sorted(r[0] for r in rows)))}
        return result
    conn, _ = state
    conn.execute("INSERT INTO dungeonmind.worlds VALUES ('eldyrwild')")
    for row in ROWS:
        conn.execute('INSERT INTO dungeonmind.campaigns VALUES (%s,%s,%s)', tuple(row.values()))
    conn.commit()
    sealed_rows = normalize_rows(campaign_rows(conn, 'eldyrwild'))
    selected = retirement_plan_minimal(conn)
    with conn.transaction():
        transfer_campaigns(conn, sealed_rows)
        retire(conn, selected)
    assert campaign_rows(conn, 'eldyrwild') == []
    assert campaign_rows(conn, 'elderwyld') == [dict(r, world_id='elderwyld') for r in ROWS]
    assert conn.execute("SELECT 1 FROM dungeonmind.worlds WHERE world_id='eldyrwild'").fetchone() is None


def test_trigger_cannot_mutate_another_world_campaign(state):
    conn, plan = state
    conn.execute("CREATE FUNCTION dungeonmind.corrupt_other() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN UPDATE dungeonmind.campaigns SET created_at='2022-01-01Z' WHERE world_id='other'; RETURN NEW; END $$")
    conn.execute('CREATE TRIGGER corrupt_other AFTER INSERT ON dungeonmind.campaigns FOR EACH ROW EXECUTE FUNCTION dungeonmind.corrupt_other()')
    conn.commit()
    before = table_fingerprints(conn)
    with pytest.raises(ValueError, match='survivor'):
        with conn.transaction():
            apply_repair(conn, plan)
    assert table_fingerprints(conn) == before


def test_future_transfer_also_rejects_trigger_mutation(state):
    conn, _ = state
    conn.execute("CREATE FUNCTION dungeonmind.corrupt_other() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN UPDATE dungeonmind.world_graph_heads SET head_revision_id='bad' WHERE world_id='other'; RETURN NEW; END $$")
    conn.execute('CREATE TRIGGER corrupt_other AFTER INSERT ON dungeonmind.campaigns FOR EACH ROW EXECUTE FUNCTION dungeonmind.corrupt_other()')
    conn.commit()
    before = table_fingerprints(conn)
    with pytest.raises(ValueError, match='transfer effect'):
        with conn.transaction():
            transfer_campaigns(conn, ROWS)
    assert table_fingerprints(conn) == before
