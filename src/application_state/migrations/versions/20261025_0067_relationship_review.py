"""Admit frozen saved-page relationship review output; preserve old captures."""
from importlib import import_module
from alembic import op
revision = "20261025_0067"
down_revision = "20261025_0066"
branch_labels = None
depends_on = None
_prior = import_module("application_state.migrations.versions.20261025_0066_connected_page_review")
_OLD = f"({_prior._OLD}) OR COALESCE(({_prior._REVIEW}),FALSE)"
_RELATIONSHIP = """
 jsonb_typeof(completion->'collaboration')='object'
 AND completion->'collaboration'->>'kind'='relationship'
 AND (completion->'collaboration') ?& ARRAY['kind','read_id','quote','source','target','predicate','label','context']
 AND ((completion->'collaboration') - ARRAY['kind','read_id','quote','source','target','predicate','label','context'])='{}'::jsonb
 AND jsonb_typeof(completion->'collaboration'->'read_id')='string'
 AND jsonb_typeof(completion->'collaboration'->'quote')='string'
 AND jsonb_typeof(completion->'collaboration'->'predicate')='string'
 AND jsonb_typeof(completion->'collaboration'->'label')='string'
 AND jsonb_typeof(completion->'collaboration'->'context')='string'
 AND jsonb_typeof(completion->'collaboration'->'source')='object'
 AND jsonb_typeof(completion->'collaboration'->'target')='object'
 AND (completion->'collaboration'->'source') ?& ARRAY['label','kind']
 AND (completion->'collaboration'->'target') ?& ARRAY['label','kind']
 AND ((completion->'collaboration'->'source') - ARRAY['label','kind'])='{}'::jsonb
 AND ((completion->'collaboration'->'target') - ARRAY['label','kind'])='{}'::jsonb
 AND jsonb_typeof(completion->'collaboration'->'source'->'label')='string'
 AND jsonb_typeof(completion->'collaboration'->'source'->'kind')='string'
 AND jsonb_typeof(completion->'collaboration'->'target'->'label')='string'
 AND jsonb_typeof(completion->'collaboration'->'target'->'kind')='string' 
"""
_REVIEW = _prior._REVIEW.replace("dmb_build_connected_page_review_completion_v1", "dmb_build_relationship_review_completion_v1").replace("completion->'collaboration'='null'::jsonb OR", f"completion->'collaboration'='null'::jsonb OR COALESCE(({_RELATIONSHIP}),FALSE) OR") + " AND graph_context_execution->'policy'->>'relationship_review_policy'='typed_saved_relationship_review_v1'"
def upgrade():
 _prior._prior._prior._draft._named._build._predecessor._replace("agent_turn_graph_completion_check",f"({_OLD}) OR COALESCE(({_REVIEW}),FALSE)")
def downgrade():
 op.execute("LOCK TABLE agent.turn IN ACCESS EXCLUSIVE MODE")
 if op.get_bind().exec_driver_sql("SELECT EXISTS(SELECT 1 FROM agent.turn WHERE completion->>'schema'='dmb_build_relationship_review_completion_v1' OR graph_context_execution->'policy'->>'relationship_review_policy'='typed_saved_relationship_review_v1')").scalar_one():
  raise RuntimeError("Retained relationship reviews require recovery forward")
 _prior._prior._prior._draft._named._build._predecessor._replace("agent_turn_graph_completion_check",_OLD)
