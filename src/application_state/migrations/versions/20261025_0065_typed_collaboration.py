"""Admit typed proposed collaboration without rewriting historical turn contracts."""

from importlib import import_module
from alembic import op

revision = "20261025_0065"
down_revision = "20261025_0064"
branch_labels = None
depends_on = None
_prior = import_module(
    "application_state.migrations.versions.20261025_0063_build_related_authored_pages"
)
_OLD = f"({_prior._OLD}) OR COALESCE(({_prior._RELATED}),FALSE)"
_TYPED = (
    _prior._RELATED.replace(
        "dmb_build_related_page_completion_v1", "dmb_build_collaboration_completion_v1"
    ).replace(
        "'citation_map','source_citations']",
        "'citation_map','source_citations','collaboration']",
    )
    + """
 AND graph_context_execution->'policy'->>'collaboration_output_policy'='typed_author_review_collaboration_v1'
 AND (completion->'collaboration'='null'::jsonb OR (
  jsonb_typeof(completion->'collaboration')='object' AND (
   (completion->'collaboration'->>'kind'='plan'
    AND ((completion->'collaboration') - ARRAY['kind','steps'])='{}'::jsonb
    AND jsonb_typeof(completion->'collaboration'->'steps')='array'
    AND CASE WHEN jsonb_typeof(completion->'collaboration'->'steps')='array' THEN jsonb_array_length(completion->'collaboration'->'steps')>0 ELSE FALSE END
    AND NOT jsonb_path_exists(completion,'$.collaboration.steps[*] ? (@.type() != "object" || !exists(@.text) || @.text.type() != "string" || !(@.text like_regex "\\\\S") || !exists(@.kind) || (@.kind != "discuss" && @.kind != "prepare_insertion"))'))
   OR (completion->'collaboration'->>'kind'='questions'
    AND ((completion->'collaboration') - ARRAY['kind','questions'])='{}'::jsonb
    AND jsonb_typeof(completion->'collaboration'->'questions')='array'
    AND CASE WHEN jsonb_typeof(completion->'collaboration'->'questions')='array' THEN jsonb_array_length(completion->'collaboration'->'questions')>0 ELSE FALSE END
    AND NOT jsonb_path_exists(completion,'$.collaboration.questions[*] ? (@.type() != "object" || !exists(@.text) || @.text.type() != "string" || !(@.text like_regex "\\\\S"))'))
  )
 ))
"""
)


def upgrade():
    _prior._draft._named._build._predecessor._replace(
        "agent_turn_graph_completion_check", f"({_OLD}) OR COALESCE(({_TYPED}),FALSE)"
    )


def downgrade():
    op.execute("LOCK TABLE agent.turn IN ACCESS EXCLUSIVE MODE")
    if (
        op.get_bind()
        .exec_driver_sql(
            "SELECT EXISTS(SELECT 1 FROM agent.turn WHERE completion->>'schema'='dmb_build_collaboration_completion_v1' OR graph_context_execution->'policy'->>'collaboration_output_policy'='typed_author_review_collaboration_v1')"
        )
        .scalar_one()
    ):
        raise RuntimeError("Retained typed collaboration requires recovery forward")
    _prior._draft._named._build._predecessor._replace(
        "agent_turn_graph_completion_check", _OLD
    )
