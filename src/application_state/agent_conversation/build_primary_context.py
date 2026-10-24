"""Exact acquired primary work, distinct from relevance-selected evidence."""

from __future__ import annotations

from uuid import UUID

STATUS_POLICY = "host_retrieval_status_finite_output_v1"
POLICY = "exact_acquired_primary_work_context_v1"
SCHEMA = "dmb_build_primary_context_writer_v1"
ROLE = "authored_page_under_edit_not_world_or_played_truth"


def enabled(policy):
    from .types import BuildPrimaryWorkPolicyV1, BuildPrimaryWorkImagePolicyV1

    return isinstance(policy, (BuildPrimaryWorkPolicyV1, BuildPrimaryWorkImagePolicyV1))


def selection(execution):
    from .types import BuildWriterEvidenceSelectionV1

    rows = [
        e for e in execution.events if isinstance(e, BuildWriterEvidenceSelectionV1)
    ]
    if len(rows) != 1:
        raise ValueError("Primary work requires its unique settled selection boundary")
    return rows[0]


def records(execution, basis=None):
    from .types import ValidatedBuildSectionReadV1

    if not enabled(execution.policy):
        return ()
    boundary = selection(execution).sequence
    rows = tuple(
        sorted(
            (
                e
                for e in execution.events[:boundary]
                if isinstance(e, ValidatedBuildSectionReadV1)
            ),
            key=lambda e: str(e.event_id),
        )
    )
    if basis is not None and any(e.source_basis != basis for e in rows):
        raise ValueError("Primary work read belongs to another saved basis")
    if len({e.read_id for e in rows}) != len(rows):
        raise ValueError("Duplicate primary work read")
    return rows


def writer_read_ids(execution):
    selected = selection(execution)
    return set(selected.section_read_ids) | {e.read_id for e in records(execution)}


def project(execution, basis=None):
    return {
        "policy": POLICY,
        "role": ROLE,
        "sections": [
            {
                "read_id": str(e.read_id),
                "line_start": e.line_start,
                "line_end": e.line_end,
                "text": e.text,
            }
            for e in records(execution, basis)
        ],
    }


def packet_rows(packet):
    """Shape check for finite selectors; producer validation separately proves bodies."""
    lane = packet.get("artifact_under_edit")
    if lane is None:
        return []
    if (
        packet.get("schema") != SCHEMA
        or not isinstance(lane, dict)
        or set(lane) != {"policy", "role", "sections"}
        or lane["policy"] != POLICY
        or lane["role"] != ROLE
        or not isinstance(lane["sections"], list)
    ):
        raise ValueError("Invalid primary work context lane")
    seen = set()
    for row in lane["sections"]:
        if not isinstance(row, dict) or set(row) != {
            "read_id",
            "line_start",
            "line_end",
            "text",
        }:
            raise ValueError("Invalid primary work section")
        if (
            not isinstance(row["read_id"], str)
            or str(UUID(row["read_id"])) != row["read_id"]
            or row["read_id"] in seen
            or type(row["line_start"]) is not int
            or type(row["line_end"]) is not int
            or not 0 < row["line_start"] <= row["line_end"]
            or not isinstance(row["text"], str)
            or not row["text"]
        ):
            raise ValueError("Invalid or duplicate primary work selector")
        seen.add(row["read_id"])
    return lane["sections"]


def validate_packet(packet, execution, basis):
    """Reconstruct lane membership and exact text independently of a worker."""
    from .types import ValidatedBuildSectionReadV1

    status_policy = getattr(execution.policy, "writer_status_policy", None)
    if packet.get("writer_status_policy") != status_policy:
        raise ValueError("Writer status capability differs from frozen policy")
    if packet.get("world_context_policy") != getattr(execution.policy, "world_context_policy", None):
        raise ValueError("World context capability differs from frozen policy")
    selected = packet.get("exposure", {}).get("saved_sections", [])
    if not enabled(execution.policy):
        if "artifact_under_edit" in packet or packet.get("schema") == SCHEMA:
            raise ValueError("Historical policy cannot gain primary work context")
        rows = [ValidatedBuildSectionReadV1.model_validate(e) for e in selected]
        if [e.model_dump(mode="json", by_alias=True) for e in rows] != selected:
            raise ValueError(
                "Historical saved section differs from exact serialized read"
            )
        return rows
    packet_rows(packet)
    expected = project(execution, basis)
    if packet.get("artifact_under_edit") != expected:
        raise ValueError("Primary work context differs from exact acquired saved reads")
    # All saved sections in Build belong to primary work. Their bodies occur once,
    # in this lane; the selection receipt still records the unchanged evidence vote.
    if selected:
        raise ValueError("Primary work must not be duplicated into selected evidence")
    return list(records(execution, basis))
