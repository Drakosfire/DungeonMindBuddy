"""Admit intentional responses and object-only replies without rewriting history."""

from importlib import import_module
from alembic import op
from sqlalchemy import text

revision = "20261025_0070"
down_revision = "20261025_0069"
branch_labels = None
depends_on = None
_prior = import_module(
    "application_state.migrations.versions.20261025_0067_relationship_review"
)
_OLD = f"({_prior._OLD}) OR COALESCE(({_prior._REVIEW}),FALSE)"
_NEW = _prior._REVIEW.replace(
    "dmb_build_relationship_review_completion_v1",
    "dmb_build_intentional_response_completion_v1",
)
for clause in (
    " AND graph_context_execution->'policy'->>'working_draft_context_policy'='captured_build_working_draft_context_v1'",
    " AND graph_context_execution->'policy'->>'related_page_context_policy'='selected_exact_related_authored_pages_v1'",
    " AND graph_context_execution->'policy'->>'collaboration_output_policy'='typed_author_review_collaboration_v1'",
    " AND graph_context_execution->'policy'->>'connected_page_review_policy'='typed_connected_page_review_v1'",
    " AND graph_context_execution->'policy'->>'relationship_review_policy'='typed_saved_relationship_review_v1'",
):
    assert _NEW.count(clause) == 1
    _NEW = _NEW.replace(clause, "")
_NEW = _NEW.replace(
    "completion->>'answer_basis'='working_draft_context'",
    "completion->>'answer_basis' IN ('working_draft_context','saved_source','saved_source_and_opened_passages','opened_source_passages','conversation')",
)
_NEW = _NEW.replace(
    "IN ('authored_grounded'", "IN ('discussion','authored_grounded'", 1
)
_NEW = _NEW.replace("BETWEEN 1 AND 128", "BETWEEN 0 AND 128")
_NEW += """
 AND graph_context_execution->'policy'->>'intentional_response_policy'='build_intentional_response_v2'
 AND (completion->>'answer_context_status' NOT IN ('discussion','creative_proposal','insufficient_evidence')
      OR NOT jsonb_path_exists(completion,'$.answer_segments[*] ? (@.kind != "connective")'))
 AND (completion->>'answer_basis'<>'conversation' OR
      (completion->'source_citations'='[]'::jsonb AND NOT jsonb_path_exists(completion,'$.answer_segments[*] ? (@.kind != "connective")')))
 AND (jsonb_array_length(completion->'answer_segments')>0 OR completion->'collaboration'<>'null'::jsonb)
 AND (completion->'collaboration'='null'::jsonb OR (
      (completion->'collaboration'->>'kind'='questions') OR
      (completion->'collaboration'->>'kind'='plan' AND graph_context_execution->'policy'->>'plan_surface_available'='true') OR
      (completion->'collaboration'->>'kind'='connected_page' AND graph_context_execution->'policy'->>'connected_page_review_policy'='typed_connected_page_review_v1') OR
      (completion->'collaboration'->>'kind'='relationship' AND graph_context_execution->'policy'->>'relationship_review_policy'='typed_saved_relationship_review_v1')))
"""
_BASE_LIFECYCLE = """
 (status = 'completed' AND assistant_text IS NOT NULL AND btrim(assistant_text) <> ''
  AND failure_code IS NULL AND completed_at IS NOT NULL)
 OR (status IN ('accepted', 'running') AND assistant_text IS NULL AND failure_code IS NULL AND completed_at IS NULL)
 OR (status IN ('failed', 'interrupted') AND assistant_text IS NULL AND failure_code IS NOT NULL AND completed_at IS NOT NULL)
"""
_NEW_LIFECYCLE = f"({_BASE_LIFECYCLE}) OR COALESCE((status='completed' AND assistant_text='' AND failure_code IS NULL AND completed_at IS NOT NULL AND completion->'answer_segments'='[]'::jsonb AND ({_NEW})),FALSE)"


def _replace(name, expression):
    conn = op.get_bind()
    # Names originate from inspected PostgreSQL catalog rows or fixed constants.
    quoted = '"' + name.replace('"', '""') + '"'
    conn.exec_driver_sql(f"ALTER TABLE agent.turn DROP CONSTRAINT {quoted}")
    conn.exec_driver_sql(
        f"ALTER TABLE agent.turn ADD CONSTRAINT {quoted} CHECK ({expression})"
    )


def upgrade():
    conn = op.get_bind()
    conn.exec_driver_sql("LOCK TABLE agent.turn IN ACCESS EXCLUSIVE MODE")
    # Ask this PostgreSQL server to deparse the known baseline. Do not guess an
    # auto-generated check name or replace a merely similar constraint.
    conn.exec_driver_sql(
        f"CREATE TEMP TABLE dmb_lifecycle_expected (status TEXT, assistant_text TEXT, failure_code TEXT, completed_at TIMESTAMPTZ, CHECK ({_BASE_LIFECYCLE})) ON COMMIT DROP"
    )
    expected = conn.exec_driver_sql(
        "SELECT pg_get_constraintdef(oid) FROM pg_constraint WHERE conrelid='pg_temp.dmb_lifecycle_expected'::regclass AND contype='c'"
    ).scalar_one()
    rows = conn.execute(
        text(
            "SELECT conname FROM pg_constraint WHERE conrelid='agent.turn'::regclass AND contype='c' AND pg_get_constraintdef(oid)=:expected"
        ),
        {"expected": expected},
    ).fetchall()
    if len(rows) != 1:
        raise RuntimeError(
            "Unexpected agent.turn lifecycle constraint; refuse replacement"
        )
    old_name = rows[0][0]
    conn.exec_driver_sql(
        'ALTER TABLE agent.turn DROP CONSTRAINT "' + old_name.replace('"', '""') + '"'
    )
    conn.exec_driver_sql(
        f"ALTER TABLE agent.turn ADD CONSTRAINT agent_turn_lifecycle_check CHECK ({_NEW_LIFECYCLE})"
    )
    _replace(
        "agent_turn_graph_completion_check", f"({_OLD}) OR COALESCE(({_NEW}),FALSE)"
    )


def downgrade():
    conn = op.get_bind()
    conn.exec_driver_sql("LOCK TABLE agent.turn IN ACCESS EXCLUSIVE MODE")
    retained = conn.exec_driver_sql("""SELECT EXISTS(SELECT 1 FROM agent.turn
      WHERE completion->>'schema'='dmb_build_intentional_response_completion_v1'
      OR graph_context_execution->'policy'->>'intentional_response_policy'='build_intentional_response_v2'
      OR jsonb_path_exists(graph_context_execution,'$.events[*] ? (@.kind == "build_requested_work_resolved_v1")'))""").scalar_one()
    if retained:
        raise RuntimeError("Retained intentional responses require recovery forward")
    _replace("agent_turn_graph_completion_check", _OLD)
    _replace("agent_turn_lifecycle_check", _BASE_LIFECYCLE)
