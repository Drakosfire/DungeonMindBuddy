"""Admit exact-source connected-page review objects without changing old completions."""

from importlib import import_module
from alembic import op

revision = "20261025_0066"
down_revision = "20261025_0065"
branch_labels = None
depends_on = None
_prior = import_module(
    "application_state.migrations.versions.20261025_0065_typed_collaboration"
)
_OLD = f"({_prior._OLD}) OR COALESCE(({_prior._TYPED}),FALSE)"
_CONNECTED = """
 jsonb_typeof(completion->'collaboration')='object'
 AND completion->'collaboration'->>'kind'='connected_page'
 AND (completion->'collaboration') ?& ARRAY['kind','title','read_id','quote','person_label','relationships','instructions']
 AND ((completion->'collaboration') - ARRAY['kind','title','read_id','quote','person_label','relationships','instructions'])='{}'::jsonb
 AND jsonb_typeof(completion->'collaboration'->'title')='string'
 AND jsonb_typeof(completion->'collaboration'->'read_id')='string'
 AND jsonb_typeof(completion->'collaboration'->'quote')='string'
 AND jsonb_typeof(completion->'collaboration'->'instructions')='string'
 AND (completion->'collaboration'->'person_label'='null'::jsonb OR jsonb_typeof(completion->'collaboration'->'person_label')='string')
 AND jsonb_typeof(completion->'collaboration'->'relationships')='array'
 AND NOT jsonb_path_exists(completion,'$.collaboration.relationships[*] ? (@ != "owns" && @ != "operates")')
"""
_REVIEW = (
    _prior._TYPED.replace(
        "dmb_build_collaboration_completion_v1",
        "dmb_build_connected_page_review_completion_v1",
    ).replace(
        "completion->'collaboration'='null'::jsonb OR (",
        f"completion->'collaboration'='null'::jsonb OR COALESCE(({_CONNECTED}),FALSE) OR (",
    )
    + " AND graph_context_execution->'policy'->>'connected_page_review_policy'='typed_connected_page_review_v1'"
)


def upgrade():
    _prior._prior._draft._named._build._predecessor._replace(
        "agent_turn_graph_completion_check", f"({_OLD}) OR COALESCE(({_REVIEW}),FALSE)"
    )


def downgrade():
    op.execute("LOCK TABLE agent.turn IN ACCESS EXCLUSIVE MODE")
    if (
        op.get_bind()
        .exec_driver_sql(
            "SELECT EXISTS(SELECT 1 FROM agent.turn WHERE completion->>'schema'='dmb_build_connected_page_review_completion_v1' OR graph_context_execution->'policy'->>'connected_page_review_policy'='typed_connected_page_review_v1')"
        )
        .scalar_one()
    ):
        raise RuntimeError("Retained connected-page reviews require recovery forward")
    _prior._prior._draft._named._build._predecessor._replace(
        "agent_turn_graph_completion_check", _OLD
    )
