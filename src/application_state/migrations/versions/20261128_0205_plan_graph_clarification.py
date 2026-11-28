"""Admit the host-owned Plan Graph clarification, without producing it."""
from importlib import import_module

from alembic import op

revision = '20261128_0205'
down_revision = '20261128_0204'
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
           AND COALESCE(graph_context_execution#>>'{events,3,scope_observation,source_use}', 'legacy')
               IN ('legacy','source_needed')
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
    conn.exec_driver_sql("LOCK TABLE agent.turn IN ACCESS EXCLUSIVE MODE")
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
    definition = conn.exec_driver_sql(
        "SELECT pg_get_functiondef('agent.validate_turn_graph_write()'::regprocedure)"
    ).scalar_one()
    lifecycle_marker = "CONSTRAINT = 'agent_turn_lifecycle_check',"
    check_start = "IF (SELECT ("
    check_end = ") IS FALSE FROM (SELECT NEW.*) AS candidate)"
    if definition.count(lifecycle_marker) != 1:
        raise RuntimeError("Owning turn lifecycle guard is unavailable")
    marker = definition.index(lifecycle_marker)
    start = definition.rfind(check_start, 0, marker)
    end = definition.rfind(check_end, start, marker)
    if start < 0 or end < 0:
        raise RuntimeError("Owning turn lifecycle predicate is unavailable")
    start += len(check_start)
    previous = definition[start:end]
    replacement = ("CASE WHEN completion->>'schema'='dmb_plan_graph_need_clarification_v1' THEN "
                   + _CALL + " ELSE (" + previous + ") END")
    conn.exec_driver_sql(definition[:start] + replacement + definition[end:])


def downgrade():
    raise RuntimeError('Retained Plan clarifications require a compatible forward reader')
