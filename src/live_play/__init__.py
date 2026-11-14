"""Helpers for the local live-play substrate."""

from importlib import import_module

_EXPORT_MODULES = {
    "LiveTurnResult": "live_turn",
    "ResolvedRoll": "resolve_roll",
    "RollTableRef": "roll_table_registry",
    "RollTableRegistry": "roll_table_registry",
    "TurnClassification": "classify_live_turn",
    "OpenAILiveTurnClassifierClient": "live_turn_classifier_client",
    "SequenceLiveTurnClassifierClient": "live_turn_classifier_client",
    "build_live_turn_classifier_sequence_client": "classify_live_turn",
    "classify_live_turn": "classify_live_turn",
    "classify_live_turn_heuristic": "classify_live_turn",
    "handle_live_turn": "live_turn",
    "resolve_roll_from_packet": "resolve_roll",
}

__all__ = list(_EXPORT_MODULES)


def __getattr__(name: str):
    if name not in _EXPORT_MODULES:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name = _EXPORT_MODULES[name]
    module = import_module(f".{module_name}", __name__)
    for export, owner in _EXPORT_MODULES.items():
        if owner == module_name:
            globals()[export] = getattr(module, export)
    return globals()[name]
