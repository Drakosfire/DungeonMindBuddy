"""Admit the host-owned Plan Graph clarification, without producing it."""
from importlib import import_module

from alembic import op
from sqlalchemy import text

revision = '20261128_0204'
down_revision = '20261128_0203'
branch_labels = None
depends_on = None

_shape = import_module('application_state.migrations.versions.20261109_0142_native_storage_json_owner')
_native = import_module('application_state.migrations.versions.20261101_0103_shared_native_turns')
_FUNCTION = 'agent.plan_graph_clarification_storage_shape'
_CALL = _FUNCTION + '(' + ','.join(name for name, _ in _shape._ARGS) + ')'
_ANCHOR = " ELSE jsonb_typeof(completion)='object'\n"
_CLARIFICATION = """
 WHEN completion->>'schema'='dmb_plan_graph_need_clarification_v1' THEN
   surface_id='plan' AND answer_composition_kind='base'
   AND jsonb_typeof(completion)='object'
   AND completion ?& ARRAY['schema','surface_id','context_receipt_sha256','observation_event_id','answer_context_status','answer_segments']
   AND completion - ARRAY['schema','surface_id','context_receipt_sha256','observation_event_id','answer_context_status','answer_segments']='{}'::jsonb
   AND completion->>'surface_id'='plan'
   AND completion->>'context_receipt_sha256'=graph_context_receipt->>'context_receipt_sha256'
   AND completion->>'observation_event_id' ~ '^[0-9a-f-]{36}$'
   AND completion->>'answer_context_status'='discussion'
   AND completion->'answer_segments'='[{"kind":"clarification","text":"What context would you like me to use for this request?"}]'::jsonb
   AND assistant_text='What context would you like me to use for this request?'
   AND graph_context_receipt#>>'{native_query,schema}'='dmb_native_plan_graph_query_pending_v1'
   AND graph_context_execution#>>'{events,-1,kind}'='native_plan_graph_clarification_v1'
   AND graph_context_execution#>>'{events,-1,observation_event_id}'=completion->>'observation_event_id'
   AND graph_context_execution#>>'{events,-2,kind}'='native_plan_graph_need_observed_v1'
   AND graph_context_execution#>>'{events,-2,event_id}'=completion->>'observation_event_id'
   AND graph_context_execution#>>'{events,-2,choice}'='uncertain'
   AND (
       NOT EXISTS (SELECT 1 FROM jsonb_array_elements(graph_context_execution->'events') AS event
       WHERE event->>'kind' NOT IN ('native_plan_graph_need_authorized_v1', 'provider_outcome',
           'native_plan_graph_need_observed_v1', 'native_plan_graph_clarification_v1'))
       OR (
           jsonb_array_length(graph_context_execution->'events')=9
           AND graph_context_execution#>>'{events,0,kind}'='native_plan_author_scope_authorized_v1'
           AND graph_context_execution#>'{events,0,intent_opening}'='true'::jsonb
           AND graph_context_execution#>>'{events,1,kind}'='provider_outcome'
           AND graph_context_execution#>>'{events,1,outcome}'='sdk_entered'
           AND graph_context_execution#>>'{events,2,kind}'='provider_outcome'
           AND graph_context_execution#>>'{events,2,outcome}'='response_received'
           AND graph_context_execution#>>'{events,3,kind}'='native_plan_author_scope_observed_v1'
           AND graph_context_execution#>>'{events,3,scope_observation,requested_work}'
               NOT IN ('clarify','different_destination')
           AND graph_context_execution#>>'{events,3,context_receipt_sha256}'=completion->>'context_receipt_sha256'
           AND graph_context_execution#>>'{events,3,execution_policy_sha256}'=graph_context_execution->>'execution_policy_sha256'
           AND graph_context_execution#>>'{events,1,provider_attempt_id}'=graph_context_execution#>>'{events,0,provider_attempt_id}'
           AND graph_context_execution#>>'{events,2,provider_attempt_id}'=graph_context_execution#>>'{events,0,provider_attempt_id}'
           AND graph_context_execution#>>'{events,3,controller_attempt_id}'=graph_context_execution#>>'{events,0,provider_attempt_id}'
           AND graph_context_execution#>>'{events,3,decision_request_id}'=graph_context_execution#>>'{events,0,decision_request_id}'
           AND graph_context_execution#>>'{events,3,controller_envelope_sha256}'=graph_context_execution#>>'{events,0,envelope_sha256}'
           AND graph_context_execution#>>'{events,3,parent_request_sha256}'=graph_context_execution#>>'{events,0,parent_request_sha256}'
           AND graph_context_execution#>>'{events,4,kind}'='native_plan_graph_need_authorized_v1'
           AND graph_context_execution#>>'{events,5,kind}'='provider_outcome'
           AND graph_context_execution#>>'{events,5,outcome}'='sdk_entered'
           AND graph_context_execution#>>'{events,5,provider_attempt_id}'=graph_context_execution#>>'{events,4,provider_attempt_id}'
           AND graph_context_execution#>>'{events,6,kind}'='provider_outcome'
           AND graph_context_execution#>>'{events,6,outcome}'='response_received'
           AND graph_context_execution#>>'{events,6,provider_attempt_id}'=graph_context_execution#>>'{events,4,provider_attempt_id}'
           AND graph_context_execution#>>'{events,7,controller_attempt_id}'=graph_context_execution#>>'{events,4,provider_attempt_id}'
       )
   )
   AND NOT jsonb_path_exists(graph_context_execution,'$.events[*] ? (@.kind == "completion_binding")')
 ELSE jsonb_typeof(completion)='object'
"""


def upgrade():
    conn = op.get_bind()
    if _native._NATIVE.count(_ANCHOR) != 1:
        raise RuntimeError('Native completion predicate changed before Plan clarification migration')
    predicate = _native._NATIVE.replace(_ANCHOR, _CLARIFICATION, 1)
    parameters = ','.join(name + ' ' + kind for name, kind in _shape._ARGS)
    conn.exec_driver_sql('CREATE FUNCTION ' + _FUNCTION + '(' + parameters + ''')
RETURNS boolean LANGUAGE plpgsql IMMUTABLE CALLED ON NULL INPUT
PARALLEL SAFE SECURITY INVOKER SET search_path=pg_catalog AS $plan_clarification$
BEGIN
    IF jsonb_typeof(graph_context_receipt)='object' THEN
        graph_context_receipt := graph_context_receipt || '{}'::jsonb;
    END IF;
    IF jsonb_typeof(graph_context_execution)='object' THEN
        graph_context_execution := graph_context_execution || '{}'::jsonb;
    END IF;
    RETURN COALESCE((''' + predicate + '''),FALSE);
END
$plan_clarification$''')
    definition = conn.execute(text("SELECT pg_get_constraintdef(oid) FROM pg_constraint "
        "WHERE conrelid='agent.turn'::regclass AND conname='agent_turn_lifecycle_check'")).scalar_one()
    if not definition.startswith('CHECK (') or not definition.endswith(')'):
        raise RuntimeError('Owning turn CHECK predicate unavailable')
    previous = definition[len('CHECK ('):-1]
    conn.exec_driver_sql('ALTER TABLE agent.turn DROP CONSTRAINT agent_turn_lifecycle_check')
    conn.exec_driver_sql('ALTER TABLE agent.turn ADD CONSTRAINT agent_turn_lifecycle_check CHECK ('
        "CASE WHEN completion->>'schema'='dmb_plan_graph_need_clarification_v1' THEN "
        + _CALL + ' ELSE (' + previous + ') END)')


def downgrade():
    raise RuntimeError('Retained Plan clarifications require a compatible forward reader')
