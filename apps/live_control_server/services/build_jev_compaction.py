"""Lossless, non-authoritative provider view; full receipts remain host-owned."""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .build_jev_transitions import AcquiredEvidence, SourceScope


CONTAINED_CODEC = "contained_passage_slices_v1"
CONTAINED_RULE = (
    " contained_passage_slices_v1 maps each literal container to flat "
    "[handle,start,end,...] triples: exact half-open Unicode code-point slices. "
    "Expand before reading references; surrounding container text does not share a slice's provenance."
)


_FIELDS = ("id", "subject", "source_class", "epistemic_kind", "temporal_scope")


def _structured(unit: AcquiredEvidence) -> bool:
    if unit.observation_text is None and not unit.opened_passages:
        return False
    if (
        unit.observation_text is None
        or not unit.opened_passages
        or unit.source_class != "admitted_graph_observation_and_opened_passages"
    ):
        raise ValueError("incomplete structured evidence")
    for passage in unit.opened_passages:
        if (
            passage.end_line < passage.start_line
            or passage.source_artifact_id != unit.scope.source_artifact_id
            or passage.source_revision != unit.scope.source_revision_id
        ):
            raise ValueError("opened passage source differs")
    text = (
        "Reviewed Graph observation:\n"
        + unit.observation_text
        + "\nOpened source passages:\n"
    )
    text += "\n\n".join(p.text for p in unit.opened_passages)
    if text != unit.text:
        raise ValueError("structured evidence does not reconstruct full host text")
    return True


def _segments(text: str, dictionary: dict[str, str]) -> list[str | int]:
    """Exact string substitution only; no normalization or partial fuzzy match."""
    chunks, cursor = [], 0
    candidates = [(key, body) for key, body in dictionary.items() if len(body) >= 32]
    while cursor < len(text):
        matches = [
            (start, -len(body), key, body)
            for key, body in candidates
            if (start := text.find(body, cursor)) >= 0
        ]
        if not matches:
            chunks.append(text[cursor:])
            break
        start, _, key, body = min(matches)
        if start > cursor:
            chunks.append(text[cursor:start])
        chunks.append(int(key[1:]))
        cursor = start + len(body)
    return chunks


def _expand(segments: list, dictionary: dict[str, str], used: set[str]) -> str:
    if not isinstance(segments, list):
        raise ValueError("invalid text segments")
    text = []
    for segment in segments:
        if isinstance(segment, str):
            text.append(segment)
        elif type(segment) is int and (key := f"p{segment}") in dictionary:
            used.add(key)
            text.append(dictionary[key])
        else:
            raise ValueError("unknown or malformed passage reference")
    return "".join(text)


def verify_projection(
    payload: dict,
    scope: SourceScope,
    units: tuple[AcquiredEvidence, ...],
    *,
    codec: str | None = None,
) -> None:
    """Independently expand the view and compare every original unit's bytes."""
    if codec is not None:
        if codec != CONTAINED_CODEC:
            raise ValueError("unsupported evidence codec")
        from .build_initial_packet_codec import canonical

        expanded = expand_contained_passages(payload)
        expected = project_evidence(scope, units)
        if canonical(expanded) != canonical(expected):
            raise ValueError(
                "contained evidence does not reconstruct exact parent projection"
            )
        return
    if set(payload) != {"scope", "evidence", "passages"} or payload[
        "scope"
    ] != scope.model_dump(mode="json"):
        raise ValueError("compact projection scope/schema differs")
    dictionary = payload["passages"]
    if not isinstance(dictionary, dict) or not all(
        isinstance(k, str) and isinstance(v, str) and v for k, v in dictionary.items()
    ):
        raise ValueError("invalid shared passage dictionary")
    ordered = sorted(units, key=lambda u: u.id)
    if len(payload["evidence"]) != len(ordered) or len({u.id for u in ordered}) != len(
        ordered
    ):
        raise ValueError("compact evidence identities differ")
    used: set[str] = set()
    for view, unit in zip(payload["evidence"], ordered, strict=True):
        if (
            unit.scope != scope
            or hashlib.sha256(unit.text.encode()).hexdigest() != unit.content_sha256
        ):
            raise ValueError("host evidence scope/hash differs")
        common = {key: unit.model_dump(mode="json")[key] for key in _FIELDS}
        if any(view.get(key) != value for key, value in common.items()):
            raise ValueError("compact evidence qualifications differ")
        if _structured(unit):
            if set(view) != set(_FIELDS) | {"observation", "opened"}:
                raise ValueError("structured view schema differs")
            observation = _expand(view["observation"], dictionary, used)
            if observation != unit.observation_text or len(view["opened"]) != len(
                unit.opened_passages
            ):
                raise ValueError("observation bytes or opened passage count differs")
            for opened, original in zip(
                view["opened"], unit.opened_passages, strict=True
            ):
                if (
                    not isinstance(opened, str)
                    or dictionary.get(opened) != original.text
                ):
                    raise ValueError("opened passage bytes/identity differs")
                used.add(opened)
        else:
            if (
                set(view) != set(_FIELDS) | {"text"}
                or _expand(view["text"], dictionary, used) != unit.text
            ):
                raise ValueError("compact evidence bytes/schema differs")
    if used != set(dictionary):
        raise ValueError("unreferenced injected passage")


def project_evidence(
    scope: SourceScope, units: tuple[AcquiredEvidence, ...], *, codec: str | None = None
) -> dict:
    """Intern exact strings only. Output does not contain or replace host proofs."""
    bodies = set()
    for unit in units:
        if unit.scope != scope:
            raise ValueError("host evidence scope differs")
        if _structured(unit):
            bodies.update(p.text for p in unit.opened_passages)
        else:
            bodies.add(unit.text)
    dictionary = {f"p{i}": body for i, body in enumerate(sorted(bodies), 1)}
    keys = {body: key for key, body in dictionary.items()}
    views = []
    for unit in sorted(units, key=lambda u: u.id):
        view = {key: unit.model_dump(mode="json")[key] for key in _FIELDS}
        if _structured(unit):
            assert unit.observation_text is not None
            view.update(
                observation=_segments(unit.observation_text, dictionary),
                opened=[keys[p.text] for p in unit.opened_passages],
            )
        else:
            view["text"] = [int(keys[unit.text][1:])]
        views.append(view)
    payload = {
        "scope": scope.model_dump(mode="json"),
        "evidence": views,
        "passages": dictionary,
    }
    verify_projection(payload, scope, units)
    if codec is not None:
        if codec != CONTAINED_CODEC:
            raise ValueError("unsupported evidence codec")
        payload = encode_contained_passages(payload)
        verify_projection(payload, scope, units, codec=codec)
    return deepcopy(payload)


def _cost(value: dict) -> int:
    from .build_jev_dispatch import _json_nodes

    return len(
        json.dumps(
            value, ensure_ascii=True, separators=(",", ":"), allow_nan=False
        ).encode()
    ) + 64 * _json_nodes(value)


def encode_contained_passages(payload: dict) -> dict:
    """Exact text reuse only; handles and every evidence layer remain distinct."""
    literal = expand_contained_passages(payload)
    bodies = literal["passages"]
    containers, aliases = {}, {}
    for handle in sorted(bodies, key=lambda h: (-len(bodies[h]), h)):
        text = bodies[handle]
        target = next((key for key, value in containers.items() if text in value), None)
        if target is None:
            containers[handle] = text
        else:
            start = containers[target].find(text)
            aliases.setdefault(target, []).extend((handle, start, start + len(text)))
    if not aliases:
        return literal
    compact = {**literal, "passages": containers, CONTAINED_CODEC: aliases}
    # Include the grammar's actual conservative cost, not just body-byte savings.
    if _cost(compact) + _cost({"grammar": CONTAINED_RULE}) >= _cost(literal):
        return literal
    from .build_initial_packet_codec import canonical

    if canonical(expand_contained_passages(compact)) != canonical(literal):
        raise ValueError("contained codec failed exact round trip")
    return compact


def expand_contained_passages(payload: dict) -> dict:
    """No reference chains, implicit units, normalization or recovery from raw IO."""
    if not isinstance(payload, dict) or set(payload) not in (
        {"scope", "evidence", "passages"},
        {"scope", "evidence", "passages", CONTAINED_CODEC},
    ):
        raise ValueError("contained projection schema differs")
    bodies = payload["passages"]
    if not isinstance(bodies, dict) or not all(
        isinstance(k, str) and k and isinstance(v, str) and v for k, v in bodies.items()
    ):
        raise ValueError("invalid literal passage dictionary")
    result = deepcopy(payload)
    if CONTAINED_CODEC not in result:
        return result
    groups = result.pop(CONTAINED_CODEC)
    if not isinstance(groups, dict) or not groups:
        raise ValueError("invalid contained passage groups")
    expanded = result["passages"]
    for container, rows in groups.items():
        if (
            container not in bodies
            or not isinstance(rows, list)
            or not rows
            or len(rows) % 3
        ):
            raise ValueError(
                "contained passage requires a literal container and complete triples"
            )
        text = bodies[container]
        for index in range(0, len(rows), 3):
            handle, start, end = rows[index : index + 3]
            if (
                not isinstance(handle, str)
                or not handle
                or handle in expanded
                or type(start) is not int
                or type(end) is not int
                or not 0 <= start < end <= len(text)
            ):
                raise ValueError("invalid contained passage handle or Unicode offsets")
            expanded[handle] = text[start:end]
    return result
