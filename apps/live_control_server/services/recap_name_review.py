"""Pre-model name review over the same source normalization and native catalog."""
from apps.live_control_server.services import known_character_context
from apps.live_control_server.services.source_artifact_registry import _normalize_source_text
from src.graph_memory.extraction.name_review import review_names,apply_review


def prepare_name_review(text,scope,*,session_id):
    original=_normalize_source_text(text)
    catalog=known_character_context.read_known_character_catalog(scope.managed_world_id,scope.campaign_id)
    pin=catalog['native_pin']
    if (pin['native_world_id'],pin['binding_version'])!=(scope.native_world_id,scope.binding_version):
        raise ValueError('World binding changed. Check names again.')
    return original,catalog,review_names(original,catalog,{**scope.model_dump(),"session_id":session_id})


def reviewed_source(text,scope,receipt,*,session_id):
    original,catalog,review=prepare_name_review(text,scope,session_id=session_id)
    corrected,record=apply_review(original,review,receipt)
    return original,corrected,catalog,record
