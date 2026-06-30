from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .model import ContextVocabularyPacket

RENDER_METHOD = "edge_vocabulary_context_v1"


@dataclass(slots=True)
class EdgeVocabularyContext:
    context_text: str
    diagnostics: dict[str, Any]


def _sorted_text(values: list[str]) -> list[str]:
    return sorted(values, key=lambda value: (value.lower(), value))


def _typed_known_names(packet: ContextVocabularyPacket) -> list[str]:
    lines: list[str] = []
    for name in _sorted_text(list(packet.known_names)):
        kind = packet.type_hints.get(name)
        lines.append(f"- {name} [{kind}]" if kind else f"- {name}")
    return lines


def _predicate_lines(packet: ContextVocabularyPacket) -> list[str]:
    lines: list[str] = []
    for label in _sorted_text(list(packet.predicate_hints)):
        predicates = _sorted_text(list(packet.predicate_hints[label]))
        if predicates:
            lines.append(f"- {label}: {', '.join(predicates)}")
    return lines


def _do_not_merge_lines(packet: ContextVocabularyPacket) -> list[str]:
    return [
        f"- {hint.left_vocab_id} != {hint.right_vocab_id}"
        for hint in sorted(
            packet.do_not_merge_hints,
            key=lambda hint: (hint.left_vocab_id, hint.right_vocab_id, hint.decision_id),
        )
    ]


def _containment_lines(packet: ContextVocabularyPacket) -> list[str]:
    return [
        f"- {hint.child_label} -> {hint.parent_label}"
        for hint in sorted(
            packet.containment_hints,
            key=lambda hint: (hint.child_label.lower(), hint.parent_label.lower(), hint.hint_id),
        )
    ]


def _append_section(lines: list[str], title: str, section_lines: list[str]) -> None:
    if not section_lines:
        return
    if lines:
        lines.append("")
    lines.append(title)
    lines.extend(section_lines)


def render_edge_vocabulary_context(
    packet: ContextVocabularyPacket,
    *,
    max_lines: int | None = None,
    render_method: str = RENDER_METHOD,
) -> EdgeVocabularyContext:
    """Render a scoped vocabulary packet as compact edge-pass guidance."""
    if max_lines is not None and max_lines < 0:
        raise ValueError("max_lines must be greater than or equal to 0")

    lines: list[str] = ["Vocabulary context for edge extraction:"]
    known_name_lines = _typed_known_names(packet)
    combat_lines = [f"- {label}" for label in _sorted_text(list(packet.combat_encounter_hints))]
    predicate_lines = _predicate_lines(packet)
    do_not_merge_lines = _do_not_merge_lines(packet)
    containment_lines = _containment_lines(packet)

    _append_section(lines, "Known names:", known_name_lines)
    _append_section(lines, "Combat encounter anchors:", combat_lines)
    _append_section(lines, "Predicate hints:", predicate_lines)
    _append_section(lines, "Do-not-merge cautions:", do_not_merge_lines)
    _append_section(lines, "Containment hints:", containment_lines)

    untrimmed_line_count = len(lines)
    trimmed_line_count = 0
    if max_lines is not None and len(lines) > max_lines:
        trimmed_line_count = len(lines) - max_lines
        lines = lines[:max_lines]

    diagnostics = {
        "enabled": True,
        "packet_id": packet.packet_id,
        "render_method": render_method,
        "context_line_count": len(lines),
        "untrimmed_line_count": untrimmed_line_count,
        "trimmed_line_count": trimmed_line_count,
        "known_name_count": len(known_name_lines),
        "combat_encounter_hint_count": len(combat_lines),
        "predicate_hint_count": sum(len(values) for values in packet.predicate_hints.values()),
        "predicate_hint_subject_count": len(predicate_lines),
        "do_not_merge_hint_count": len(do_not_merge_lines),
        "containment_hint_count": len(containment_lines),
    }
    return EdgeVocabularyContext(context_text="\n".join(lines), diagnostics=diagnostics)
