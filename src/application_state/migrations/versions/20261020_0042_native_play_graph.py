"""Closed native Play Graph persistence; preserve all predecessor row meanings."""
from importlib import import_module
from alembic import op

revision = "20261020_0042"
down_revision = "20261020_0041"
branch_labels = None
depends_on = None

# Immutable migration authority only; never import mutable runtime/model policy.
_m24 = import_module("application_state.migrations.versions.20261016_0024_build_graph_turns")
_m25 = import_module("application_state.migrations.versions.20261016_0025_nullable_execution_counts")
_m40 = import_module("application_state.migrations.versions.20261019_0040_session_evidence_completion")
R, E, C = "graph_context_receipt", "graph_context_execution", "completion"
B, A, P, I = R+"->'play_basis'", R+"->'graph_authority'", R+"->'graph_packet'", R+"->'assembled_input'"
POL, SCOPE = E+"->'policy'", E+"->'policy'->'source_read_scope'"
_NATIVE = """(surface_id='play' AND submitted_intent_fingerprint_v2 IS NOT NULL)
 OR graph_context_receipt->>'schema'='dmb_play_world_graph_context_receipt_v1'
 OR graph_context_execution->>'schema'='dmb_play_world_graph_execution_v1'
 OR completion->>'schema'='dmb_play_world_graph_completion_v1'"""


def _closed(field, names):
    keys = "ARRAY["+",".join("'"+name+"'" for name in names.split())+"]"
    return f"jsonb_typeof({field})='object' AND ({field}) ?& {keys} AND (({field}) - {keys})='{{}}'::jsonb"


def _hash(field):
    return f"jsonb_typeof({field})='string' AND ({field})#>>'{{}}' ~ '^[a-f0-9]{{64}}$'"


def _integer(field, low, high=None):
    bound = f"BETWEEN {low} AND {high}" if high is not None else f">={low}"
    return f"CASE WHEN jsonb_typeof({field})='number' AND ({field})#>>'{{}}' ~ '^[0-9]+$' THEN (({field})#>>'{{}}')::numeric {bound} ELSE FALSE END"


def _array(field, low, high):
    return f"CASE WHEN jsonb_typeof({field})='array' THEN jsonb_array_length({field}) BETWEEN {low} AND {high} ELSE FALSE END"


def _and(*parts):
    return " AND ".join("("+part+")" for part in parts)


def _old_execution():
    explicit = " AND ".join(f"graph_context_execution->'policy' ? '{field}' AND graph_context_execution->'policy'->'{field}' = 'null'::jsonb" for field in _m25._FIELDS)
    normalized = _m25._FINITE_CHECK.replace("graph_context_execution", _m25._NORMALIZED_EXECUTION)
    return ("graph_context_execution IS NULL OR COALESCE(("
        f"(graph_context_execution->'policy'->>'policy_version' NOT IN {_m25._UNCAPPED_VERSIONS} AND ({_m25._FINITE_CHECK})) OR "
        f"(graph_context_execution->'policy'->>'policy_version' IN {_m25._UNCAPPED_VERSIONS} AND {explicit} AND ({normalized}))), FALSE)")


_OLD = {
    "agent_turn_graph_context_receipt_check": f"({_m24._PLAN_RECEIPT}) OR COALESCE(({_m24._BUILD_RECEIPT}), FALSE)",
    "agent_turn_graph_context_execution_check": _old_execution(),
    "agent_turn_graph_completion_check": _m40._NEW,
}

_RECEIPT = _and(
    "surface_resolution='resolved' AND surface_id='play' AND submitted_intent_fingerprint_v1 IS NULL AND submitted_intent_fingerprint_v2 IS NOT NULL",
    _closed(R,"schema receipt_serializer_version context_receipt_sha256 play_graph_policy play_basis play_sources play_source_frame_sha256 retrieval_session_id graph_authority graph_packet assembled_input evidence_mode source_opened"),
    f"{R}->>'schema'='dmb_play_world_graph_context_receipt_v1' AND {R}->>'receipt_serializer_version'='canonical-json-utf8-v1'",
    _hash(R+"->'context_receipt_sha256'"), _hash(R+"->'play_source_frame_sha256'"),
    f"{R}->'play_graph_policy'='{{\"schema\":\"dmb_play_graph_policy_v1\",\"policy\":\"native_play_world_v1\"}}'::jsonb",
    f"{R}->>'evidence_mode'='metadata_only' AND {R}->'source_opened'='false'::jsonb AND octet_length({R}::text)<=163840",
    f"length({R}->>'retrieval_session_id') BETWEEN 1 AND 128",
    f"{B}=play_context_receipt AND {B}->>'world_id'=world_id AND {B}->>'schema'='dmb_play_run_turn_context_receipt_v2' AND {B}->>'marker_grammar_version'='v2'",
    _integer(B+"->'run_revision'",1),_integer(B+"->'edition_revision'",0),_hash(B+"->'content_sha256'"),
    f"({B}->>'edition_revision'='0' AND {B}->'edition_revision_id'='null'::jsonb AND {B}->>'content_sha256'={B}->>'runbook_content_sha256') OR ({B}->>'edition_revision'<>'0' AND jsonb_typeof({B}->'edition_revision_id')='string')",
    f"({B}->'scene_note'='null'::jsonb AND {B}->'scene_note_sha256'='null'::jsonb) OR (jsonb_typeof({B}->'scene_note')='string' AND octet_length({B}->>'scene_note')<=32768 AND {B}->>'scene_note_sha256'=encode(sha256(convert_to({B}->>'scene_note','UTF8')),'hex'))",
    _closed(A,"managed_world_id native_world_id binding_version scope_mode campaign_id admissibility_version graph_revision"),
    f"{A}->>'managed_world_id'=world_id AND length(btrim({A}->>'native_world_id')) BETWEEN 1 AND 128 AND {A}->>'scope_mode'='world' AND {A}->'campaign_id'='null'::jsonb AND {A}->>'admissibility_version'='gm-v1' AND length(btrim({A}->>'graph_revision')) BETWEEN 1 AND 256",
    _integer(A+"->'binding_version'",1),
    _closed(R+"->'play_sources'","schema entries manifest_sha256"),
    f"{R}->'play_sources'->>'schema'='dmb_play_source_manifest_v1'",_hash(R+"->'play_sources'->'manifest_sha256'"),_array(R+"->'play_sources'->'entries'",0,2),
    _closed(P,"schema packet_serializer_version selection_policy_version evidence_sufficiency_policy_version retrieval_packet_sha256 candidate_assertion_ids candidate_relationship_ids candidate_evidence_ref_ids retrieval_status evidence_sufficiency_status result_limit coverage_status truncated omission_reasons"),
    f"{P}->>'schema'='dmb_play_world_graph_packet_v1' AND {P}->>'packet_serializer_version'='canonical-json-utf8-v1' AND {P}->>'selection_policy_version'<>'parent_initial_retrieval_with_selected_source_index_v1'",
    _hash(P+"->'retrieval_packet_sha256'"),_array(P+"->'candidate_assertion_ids'",0,512),_array(P+"->'candidate_relationship_ids'",0,512),_array(P+"->'candidate_evidence_ref_ids'",0,1024),
    f"{P}->>'retrieval_status' IN ('complete','empty') AND {P}->>'evidence_sufficiency_status' IN ('sufficient','insufficient') AND {P}->>'coverage_status' IN ('complete','incomplete') AND {P}->'truncated' IN ('true'::jsonb,'false'::jsonb)",
    _closed(I,"assembler_version budget_policy_version provider_model_name provider_model_version tokenizer_name tokenizer_version provider_envelope_input_tokens output_token_reserve context_window_limit packet_disposition packet_disposition_reason dispatched_packet_sha256 dispatched_assertion_ids dispatched_relationship_ids dispatched_evidence_ref_ids source_token_accounting included_history assembled_input_sha256"),
    _hash(I+"->'assembled_input_sha256'"),_integer(I+"->'provider_envelope_input_tokens'",0),_integer(I+"->'output_token_reserve'",0),_integer(I+"->'context_window_limit'",1),
    f"CASE WHEN jsonb_typeof({I}->'provider_envelope_input_tokens')='number' AND jsonb_typeof({I}->'output_token_reserve')='number' AND jsonb_typeof({I}->'context_window_limit')='number' THEN ({I}->>'provider_envelope_input_tokens')::numeric+({I}->>'output_token_reserve')::numeric<=({I}->>'context_window_limit')::numeric ELSE FALSE END",
    _array(I+"->'dispatched_assertion_ids'",0,512),_array(I+"->'dispatched_relationship_ids'",0,512),_array(I+"->'dispatched_evidence_ref_ids'",0,1024),_array(I+"->'source_token_accounting'",0,128),_array(I+"->'included_history'",0,64),
    f"(({I}->>'packet_disposition'='included' AND {P}->>'evidence_sufficiency_status'='sufficient' AND jsonb_typeof({I}->'dispatched_packet_sha256')='string' AND {I}->'packet_disposition_reason'='null'::jsonb) OR ({I}->>'packet_disposition'='omitted_insufficient' AND {P}->>'evidence_sufficiency_status'='insufficient' AND {I}->'dispatched_packet_sha256'='null'::jsonb AND {I}->>'packet_disposition_reason'='insufficient_evidence' AND {I}->'dispatched_assertion_ids'='[]'::jsonb AND {I}->'dispatched_relationship_ids'='[]'::jsonb AND {I}->'dispatched_evidence_ref_ids'='[]'::jsonb))",
    f"{E} IS NOT NULL AND {E}->>'schema'='dmb_play_world_graph_execution_v1'",
)

_KINDS = ('play_source_provider_inclusion_v1','validated_graph_operation_v3','provider_attempt_authorized_v3','provider_outcome','completion_binding','source_scope_extension_v3','source_read_authorized_v2','validated_source_read_v2','related_recap_context_authorized_v2','validated_related_recap_context_v2','related_recap_context_provider_inclusion_v2')
_INVALID_KIND = '$[*] ? (!exists(@.kind) || ('+' && '.join('@.kind != "'+kind+'"' for kind in _KINDS)+'))'
_EXECUTION = _and(
    f"{R}->>'schema'='dmb_play_world_graph_context_receipt_v1'",_closed(E,"schema context_receipt_sha256 execution_policy_sha256 policy events"),
    f"{E}->>'schema'='dmb_play_world_graph_execution_v1' AND {E}->>'context_receipt_sha256'={R}->>'context_receipt_sha256'",_hash(E+"->'execution_policy_sha256'"),
    _closed(POL,"policy_version allowed_graph_operations max_provider_attempts max_graph_operations max_results_per_operation max_total_provider_input_tokens max_total_provider_output_tokens provider_input_accounting source_opened source_read_scope max_source_read_chars max_chars_per_source_read source_read_accounting"),
    f"{POL}->>'policy_version'='play_world_graph_execution_v1' AND {POL}->>'source_read_accounting'='settled_receipts_v1' AND {POL}->'source_opened'='false'::jsonb",
    _integer(POL+"->'max_provider_attempts'",1,64),_integer(POL+"->'max_graph_operations'",0,512),_integer(POL+"->'max_results_per_operation'",0,4096),
    _integer(POL+"->'max_total_provider_input_tokens'",1),_integer(POL+"->'max_total_provider_output_tokens'",1),_integer(POL+"->'max_source_read_chars'",0,96000),_integer(POL+"->'max_chars_per_source_read'",1,12000),
    _array(POL+"->'allowed_graph_operations'",1,32),_closed(POL+"->'provider_input_accounting'","kind estimator"),
    f"{POL}->'provider_input_accounting'->>'kind' IN ('exact_token_count','conservative_upper_bound') AND length({POL}->'provider_input_accounting'->>'estimator') BETWEEN 1 AND 128",
    _closed(SCOPE,"schema retrieval_session_id world_id campaign_id graph_revision admitted_anchors"),
    f"{SCOPE}->>'schema'='dmb_graph_source_read_scope_v2' AND {SCOPE}->>'world_id'=world_id AND {SCOPE}->'campaign_id'='null'::jsonb AND {SCOPE}->>'graph_revision'={A}->>'graph_revision' AND {SCOPE}->>'retrieval_session_id'={R}->>'retrieval_session_id'",
    _array(SCOPE+"->'admitted_anchors'",0,512),_array(E+"->'events'",0,2048),f"octet_length({E}::text)<=1048576",
    f"NOT jsonb_path_exists({E}->'events','{_INVALID_KIND}')",
    f"NOT jsonb_path_exists({E}, '$.events[*] ? (@.kind == \"play_source_provider_inclusion_v1\" && (!exists(@.context_receipt_sha256) || @.context_receipt_sha256 != $receipt || !exists(@.execution_policy_sha256) || @.execution_policy_sha256 != $policy || !exists(@.source_frame_sha256) || @.source_frame_sha256 != $frame || !exists(@.source_ids) || @.source_ids.type() != \"array\" || @.source_ids.size() > 2))', jsonb_build_object('receipt',{R}->'context_receipt_sha256','policy',{E}->'execution_policy_sha256','frame',{R}->'play_source_frame_sha256'))",
)

_HAS_GRAPH = "jsonb_path_exists(completion,'$.answer_segments[*] ? (@.kind == \"graph_claim\")')"
_HAS_PLAY = "jsonb_path_exists(completion,'$.answer_segments[*] ? (@.kind == \"play_context_claim\")')"
_COMPLETION = f"""(
 ({C} IS NULL AND NOT jsonb_path_exists({E},'$.events[*] ? (@.kind == "completion_binding")')
  AND (status<>'completed' AND assistant_text IS NULL OR status='completed' AND answer_composition_kind='rules_mixed_v1'))
 OR COALESCE(({_and(
    "status='completed' AND assistant_text IS NOT NULL",
    _closed(C,"schema context_receipt_sha256 answer_basis answer_context_status answer_segments citation_map"),
    f"{C}->>'schema'='dmb_play_world_graph_completion_v1' AND {C}->>'context_receipt_sha256'={R}->>'context_receipt_sha256' AND octet_length({C}::text)<=81920",
    _array(C+"->'answer_segments'",1,128),
    f"NOT jsonb_path_exists({C}, '$.answer_segments[*] ? (!exists(@.kind) || (@.kind != \"play_context_claim\" && @.kind != \"graph_claim\" && @.kind != \"connective\"))')",
    f"{C}->>'answer_basis'=CASE WHEN {_HAS_GRAPH} AND {_HAS_PLAY} THEN 'play_sources_plus_world_graph' WHEN {_HAS_GRAPH} THEN 'world_graph' WHEN {_HAS_PLAY} THEN 'play_sources' ELSE 'nonfactual_context' END",
    f"(({_HAS_GRAPH} AND {C}->>'answer_context_status' IN ('graph_grounded','graph_grounded_partial') AND {C}->'citation_map'->>'schema'='dmb_graph_citation_map_v2' AND {C}->'citation_map'->>'context_receipt_sha256'={C}->>'context_receipt_sha256') OR (NOT {_HAS_GRAPH} AND {C}->>'answer_context_status' IN ('play_only_graph_unused','play_only_insufficient_evidence') AND {C}->'citation_map'='null'::jsonb))",
    f"{E}->'events'->-1->>'kind'='completion_binding'",
 )}), FALSE))"""

_NEW = dict(zip(_OLD, (_RECEIPT,_EXECUTION,_COMPLETION)))


def _replace(name, expression):
    op.execute(f"ALTER TABLE agent.turn DROP CONSTRAINT {name}")
    op.execute(f"ALTER TABLE agent.turn ADD CONSTRAINT {name} CHECK ({expression})")


def upgrade():
    for name, old in _OLD.items():
        _replace(name, f"CASE WHEN COALESCE(({_NATIVE}),FALSE) THEN COALESCE(({_NEW[name]}),FALSE) ELSE ({old}) END")


def downgrade():
    op.execute("LOCK TABLE agent.turn IN ACCESS EXCLUSIVE MODE")
    if op.get_bind().exec_driver_sql(f"SELECT EXISTS(SELECT 1 FROM agent.turn WHERE COALESCE(({_NATIVE}),FALSE))").scalar_one():
        raise RuntimeError("refusing to discard retained native Play intent/receipt/execution/completion")
    for name, old in _OLD.items():
        _replace(name, old)
