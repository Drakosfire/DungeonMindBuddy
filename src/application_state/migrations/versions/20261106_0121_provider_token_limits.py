"""Admit provider-owned token capacity; preserve all prior typed Play predicates.

No rows are rewritten. New native writer values fence out older readers; new
Play null token ceilings reuse the current closed execution/source predicates.
"""
from importlib import import_module

from alembic import op
from sqlalchemy import text

revision = "20261106_0121"
down_revision = "20261106_0120"
branch_labels = None
depends_on = None


def upgrade():
    owner=import_module('application_state.migrations.versions.20261106_0120_play_source_references')
    name='agent_turn_graph_context_execution_check'
    definition=op.get_bind().execute(text(
        "SELECT pg_get_constraintdef(oid) FROM pg_constraint "
        "WHERE conrelid='agent.turn'::regclass AND conname=:name"),{'name':name}).scalar_one()
    if not definition.startswith('CHECK (') or not definition.endswith(')'):
        raise RuntimeError('Owning Play execution predicate unavailable')
    previous=definition[len('CHECK ('):-1]
    def token_shapes(expression):
        for field in ('max_total_provider_input_tokens','max_total_provider_output_tokens'):
            value=owner._m42.POL+"->'"+field+"'"
            finite=owner._m42._integer(value,1)
            if finite not in expression:
                raise RuntimeError('Owning Play token shape changed before migration')
            expression=expression.replace(finite,"("+value+"='null'::jsonb OR ("+finite+"))")
        return expression
    # Referenced and unreferenced Play retain their different closed field sets.
    execution=("CASE WHEN "+owner._SELECTED+" THEN ("+token_shapes(owner._EXECUTION)+
        ") ELSE ("+token_shapes(owner._m79._NEW)+") END")
    nulls=[owner._m42.POL+"->'"+field+"'='null'::jsonb" for field in
        ('max_total_provider_input_tokens','max_total_provider_output_tokens')]
    selected="CASE WHEN "+owner._SELECTED+" THEN ("+owner._CONTEXT+") ELSE TRUE END"
    native=owner.E+"->>'schema'='dmb_play_world_graph_execution_v1'"
    predicate=("CASE WHEN "+native+" AND ("+' OR '.join(nulls)+") THEN COALESCE((("+
        execution+") AND ("+selected+")),FALSE) ELSE ("+previous+") END")
    owner._m42._replace(name,predicate)


def downgrade():
    raise RuntimeError('Older readers require the retired native writer token ceilings')
