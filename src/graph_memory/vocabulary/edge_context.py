from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .model import ContextVocabularyPacket, DoNotMergeDecision

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
        lines.extend(_name_line(packet, name))
    return lines


def _predicate_lines(packet: ContextVocabularyPacket) -> list[str]:
    lines: list[str] = []
    for label in _sorted_text(list(packet.predicate_hints)):
        predicates = _sorted_text(list(packet.predicate_hints[label]))
        if predicates:
            lines.append(f"- {label}: {', '.join(predicates)}")
    return lines


def _name_line(packet: ContextVocabularyPacket, name: str) -> list[str]:
    kind = packet.type_hints.get(name)
    lines = [f"- {name} [{kind}]" if kind else f"- {name}"]
    aliases = packet.entry_aliases.get(name, [])
    if aliases:
        lines.append(f"  aliases: {', '.join(aliases)}")
    candidate_aliases = packet.candidate_entry_aliases.get(name, [])
    if candidate_aliases:
        lines.append(f"  candidate aliases / review only: {', '.join(candidate_aliases)}")
    return lines


def _resolved_vocab_id(packet: ContextVocabularyPacket, vocab_id: str) -> tuple[str, bool]:
    label = packet.entry_labels.get(vocab_id)
    if label is None:
        return vocab_id, False
    kind = packet.entry_kinds.get(vocab_id)
    return (f"{label} [{kind}]" if kind else label), True


def _do_not_merge_line(packet: ContextVocabularyPacket, hint: DoNotMergeDecision) -> tuple[str, bool]:
    left, left_resolved = _resolved_vocab_id(packet, hint.left_vocab_id)
    right, right_resolved = _resolved_vocab_id(packet, hint.right_vocab_id)
    line = f"- {left} must not merge with {right}"
    if hint.reason:
        line += f" — {hint.reason}"
    return line, left_resolved or right_resolved


def _do_not_merge_lines(packet: ContextVocabularyPacket, retained_names: set[str] | None = None) -> list[str]:
    lines: list[str] = []
    for hint in sorted(
        packet.do_not_merge_hints,
        key=lambda hint: (hint.left_vocab_id, hint.right_vocab_id, hint.decision_id),
    ):
        if retained_names is not None:
            left_label = packet.entry_labels.get(hint.left_vocab_id)
            right_label = packet.entry_labels.get(hint.right_vocab_id)
            if left_label is None and right_label is None:
                continue
            if left_label not in retained_names and right_label not in retained_names:
                continue
        line, _ = _do_not_merge_line(packet, hint)
        lines.append(line)
    return lines


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
