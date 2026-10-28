"""Frozen saved-page projections; full draft and saved evidence stay distinct."""

from __future__ import annotations

from uuid import UUID

STATUS_POLICY = "host_retrieval_status_finite_output_v1"
POLICY = "exact_acquired_primary_work_context_v1"
DRAFT_POLICY = "selected_saved_work_with_full_draft_v2"
SCHEMA = "dmb_build_primary_context_writer_v1"
DRAFT_SCHEMA = "dmb_build_primary_context_writer_v2"
SCHEMAS = (SCHEMA, DRAFT_SCHEMA)
ROLE = "authored_page_under_edit_not_world_or_played_truth"


def enabled(policy):
    from .types import BuildPrimaryWorkPolicyV1, BuildPrimaryWorkImagePolicyV1

    return isinstance(policy, (BuildPrimaryWorkPolicyV1, BuildPrimaryWorkImagePolicyV1))


def schema(policy):
    return DRAFT_SCHEMA if policy.primary_work_context_policy == DRAFT_POLICY else SCHEMA


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
    if execution.policy.primary_work_context_policy == DRAFT_POLICY:
        from .types import BuildDraftContextCapturedV1
        captures = [e for e in execution.events[:boundary] if isinstance(e, BuildDraftContextCapturedV1)]
        if len(captures) != 1 or captures[0].record.snapshot.snapshot_sha256 != execution.policy.working_draft_snapshot_sha256:
            raise ValueError("Selected primary work requires its complete captured draft")
        chosen = selection(execution).section_read_ids
        if len(set(chosen)) != len(chosen) or not set(chosen) <= {e.read_id for e in rows}:
            raise ValueError("Selected primary work requires unique acquired pre-selection reads")
        rows = tuple(e for e in rows if e.read_id in chosen)
    return rows


def writer_read_ids(execution):
    selected = selection(execution)
    return set(selected.section_read_ids) | {e.read_id for e in records(execution)}


def project(execution, basis=None):
    return {
        "policy": execution.policy.primary_work_context_policy,
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
    from .build_draft_context import resolve_body_aliases
    packet = resolve_body_aliases(packet)
    lane = packet.get("artifact_under_edit")
    if lane is None:
        return []
    if (
        packet.get("schema") not in SCHEMAS
        or not isinstance(lane, dict)
        or set(lane) != {"policy", "role", "sections"}
        or lane["policy"] not in (POLICY, DRAFT_POLICY)
        or (packet.get("schema") == DRAFT_SCHEMA) != (lane["policy"] == DRAFT_POLICY)
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
    from .authored_graph_references import validate_packet as validate_authored_packet
    validate_authored_packet(packet, execution)

    status_policy = getattr(execution.policy, "writer_status_policy", None)
    if packet.get("writer_status_policy") != status_policy:
        raise ValueError("Writer status capability differs from frozen policy")
    if packet.get("world_context_policy") != getattr(execution.policy, "world_context_policy", None):
        raise ValueError("World context capability differs from frozen policy")
    selected = packet.get("exposure", {}).get("saved_sections", [])
    if not enabled(execution.policy):
        if "artifact_under_edit" in packet or packet.get("schema") in SCHEMAS:
            raise ValueError("Historical policy cannot gain primary work context")
        rows = [ValidatedBuildSectionReadV1.model_validate(e) for e in selected]
        if [e.model_dump(mode="json", by_alias=True) for e in rows] != selected:
            raise ValueError(
                "Historical saved section differs from exact serialized read"
            )
        return rows
    if execution.policy.primary_work_context_policy == DRAFT_POLICY and "working_draft_context" not in packet:
        raise ValueError("Selected saved context requires its complete working draft lane")
    if packet.get("schema") != schema(execution.policy):
        raise ValueError("Primary writer schema differs from frozen policy")
    packet_rows(packet)
    expected = project(execution, basis)
    from .build_draft_context import resolve_body_aliases
    packet = resolve_body_aliases(packet)
    if packet.get("artifact_under_edit") != expected:
        raise ValueError("Primary work context differs from exact acquired saved reads")
    # Supplied saved sections belong to primary work. Their bodies occur once,
    # in this lane; the selection receipt still records the unchanged evidence vote.
    if selected:
        raise ValueError("Primary work must not be duplicated into selected evidence")
    return list(records(execution, basis))
