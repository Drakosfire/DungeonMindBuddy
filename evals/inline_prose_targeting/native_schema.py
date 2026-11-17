"""Approved fixture-only CHECK extensions; never an APP migration or product setup."""
import json
from pathlib import Path
from urllib.parse import urlparse
import psycopg
from psycopg import sql


def extend_empty_clone(dsn: str, evidence: Path):
    parsed=urlparse(dsn); database=parsed.path.lstrip('/')
    if parsed.hostname!='127.0.0.1' or parsed.port!=55467 or not database.startswith('dungeonbuddy_app_state_test_') or database.startswith('dungeonbuddy_app_state_test_template_'):
        raise ValueError('Schema proof may modify only its uniquely owned clone on55467')
    target="payload #> '{reservation,prose_target}'"
    review_target="payload->'prose_target'"
    def binding(expr):
        return f"""jsonb_typeof({expr})='object'
            AND {expr}->>'schema'='dmb_build_prose_target_v1'
            AND {expr}->>'operation'='replace_paragraph'
            AND length({expr}->>'alias')>0
            AND {expr}->>'catalog_sha256' ~ '^[a-f0-9]{{64}}$'
            AND {expr}->>'before_text_sha256' ~ '^[a-f0-9]{{64}}$'
            AND jsonb_typeof({expr}->'from')='number'
            AND jsonb_typeof({expr}->'to')='number'
            AND ({expr}->>'from')::numeric>=1
            AND ({expr}->>'to')::numeric>({expr}->>'from')::numeric
            AND ({expr}->>'from')::numeric=trunc(({expr}->>'from')::numeric)
            AND ({expr}->>'to')::numeric=trunc(({expr}->>'to')::numeric)"""
    new_proposal=f"""payload->>'schema_version'='dmb_build_document_proposal_v2'
        AND {binding('('+target+')')}
        AND NOT (payload #> '{{reservation,basis}}' ? 'selection')
        AND payload #>> '{{reservation,basis,editor_sha256}}' ~ '^[a-f0-9]{{64}}$'"""
    new_review=f"""payload->>'schema'='dmb_build_proposal_review_v4'
        AND {binding('('+review_target+')')}
        AND jsonb_typeof(payload->'placement_caret')='number'
        AND (payload->>'placement_caret')::numeric>=0
        AND (payload->>'placement_caret')::numeric=trunc((payload->>'placement_caret')::numeric)
        AND NOT (payload ? 'placement') AND NOT (payload ? 'retired_placements')
        AND (payload->'apply'='null'::jsonb OR payload#>'{{apply,prose_target}}'=payload->'prose_target')"""
    # Keep the entire replacement arms and add separate boundary-only arms.
    def boundary_arm(arm, old_version, new_version):
        return (arm.replace(old_version, new_version)
            .replace("dmb_build_prose_target_v1", "dmb_build_prose_boundary_target_v1")
            .replace("->>'operation'='replace_paragraph'", "->>'operation' IN ('insert_before','insert_after')")
            .replace("::numeric>=1", "::numeric>=0")
            .replace("::numeric>(", "::numeric=("))
    new_proposal = f"({new_proposal}) OR ({boundary_arm(new_proposal, 'dmb_build_document_proposal_v2', 'dmb_build_document_proposal_v3')})"
    new_review = f"({new_review}) OR ({boundary_arm(new_review, 'dmb_build_proposal_review_v4', 'dmb_build_proposal_review_v5')})"
    changes=[]
    with psycopg.connect(dsn) as conn:
        observed=conn.execute('SELECT current_database(),current_user,inet_server_addr()::text,inet_server_port()').fetchone()
        if observed[0]!=database:raise ValueError('Connected database differs from owned clone')
        counts=conn.execute('SELECT (SELECT count(*) FROM agent.build_proposal),(SELECT count(*) FROM agent.build_proposal_review)').fetchone()
        if counts!=(0,0):raise ValueError('Only empty disposable fixture tables may be extended')
        for table,name,extra in [('build_proposal','build_proposal_schema_variant',new_proposal),('build_proposal_review','build_review_current_placement',new_review)]:
            row=conn.execute("SELECT pg_get_constraintdef(oid),pg_get_expr(conbin,conrelid) FROM pg_constraint WHERE conrelid=%s::regclass AND conname=%s",('agent.'+table,name)).fetchone()
            if not row:raise ValueError('Expected existing constraint is absent')
            expression=f'({row[1]}) OR COALESCE(({extra}), FALSE)'
            conn.execute(sql.SQL('ALTER TABLE agent.{} DROP CONSTRAINT {}, ADD CONSTRAINT {} CHECK ({})').format(sql.Identifier(table),sql.Identifier(name),sql.Identifier(name),sql.SQL(expression)))
            installed=conn.execute("SELECT pg_get_constraintdef(oid) FROM pg_constraint WHERE conrelid=%s::regclass AND conname=%s",('agent.'+table,name)).fetchone()[0]
            changes.append(dict(table=table,name=name,original=row[0],original_expression=row[1],additional_arm=extra,installed=installed))
        evidence.parent.mkdir(parents=True,exist_ok=True)
        evidence.write_text(json.dumps(dict(test_only=True,database=database,identity=observed,empty_counts=counts,changes=changes),indent=2))
