"""Admit separately attributed session evidence in Plan completions."""
from importlib import import_module
import re
from alembic import op

revision = "20261019_0040"
down_revision = "20261019_0039"
branch_labels = None
depends_on = None
_previous = import_module("application_state.migrations.versions.20261017_0032_build_images")
_OLD = f"({_previous._previous._OLD}) OR COALESCE(({_previous._previous._AUTHORING}), FALSE) OR COALESCE(({_previous._IMAGE}), FALSE)"
_NEW = _OLD
for _basis in ("committed_plan_plus_world_graph", "committed_plan"):
    _NEW, _count = re.subn(
        rf"completion->>'answer_basis'\s*=\s*'{_basis}'",
        f"completion->>'answer_basis' IN ('{_basis}', '{_basis}_plus_session_evidence')",
        _NEW,
    )
    assert _count == 2, "Expected both retained Plan completion variants"
_NEW = f"({_NEW}) AND (completion IS NULL OR completion->>'answer_basis' NOT IN ('committed_plan_plus_session_evidence','committed_plan_plus_world_graph_plus_session_evidence') OR COALESCE(jsonb_path_exists(completion->'answer_segments', '$[*] ? (@.kind == \"session_evidence_claim\")'), FALSE))"


def upgrade():
    _previous._previous._previous._predecessor._replace("agent_turn_graph_completion_check", _NEW)


def downgrade():
    op.execute("LOCK TABLE agent.turn IN ACCESS EXCLUSIVE MODE")
    if op.get_bind().exec_driver_sql("SELECT EXISTS(SELECT 1 FROM agent.turn WHERE completion->>'answer_basis' IN ('committed_plan_plus_session_evidence','committed_plan_plus_world_graph_plus_session_evidence'))").scalar_one():
        raise RuntimeError("refusing to discard retained session-evidence completions")
    _previous._previous._previous._predecessor._replace("agent_turn_graph_completion_check", _OLD)
