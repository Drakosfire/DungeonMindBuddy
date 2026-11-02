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
NATIVE_WORK_SCHEMA = "dmb_build_primary_work_evidence_v1"


def enabled(policy):
    from .types import BuildPrimaryWorkPolicyV1, BuildPrimaryWorkImagePolicyV1

    if isinstance(policy, (BuildPrimaryWorkPolicyV1, BuildPrimaryWorkImagePolicyV1)):
        return True
    if getattr(policy,'policy_version',None) != 'surface_native_execution_v1':
        return False
    from .native_execution import SurfaceNativeExecutionPolicyV1, NativeBuildActionV1
    return type(policy) is SurfaceNativeExecutionPolicyV1 and type(policy.action) is NativeBuildActionV1



def context_policy(policy):
    from .native_execution import SurfaceNativeExecutionPolicyV1, NativeBuildActionV1
    if type(policy) is SurfaceNativeExecutionPolicyV1 and type(policy.action) is NativeBuildActionV1:
        return DRAFT_POLICY if policy.action.intent.build_draft_context_sha256 is not None else POLICY
    return policy.primary_work_context_policy


def schema(policy):
    return DRAFT_SCHEMA if context_policy(policy) == DRAFT_POLICY else SCHEMA


def validate_reads(execution, *, max_chars):
    """One causal saved-read validator for actual legacy/shared execution records."""
    from . import types as t
    latest_attempt=latest_outcome=None
    authorizations,reads={},set()
    for event in execution.events:
        if isinstance(event,t.BuildSectionReadAuthorizationV1):
            if (latest_attempt is None or latest_outcome != 'response_received'
                    or event.read_id in authorizations or event.max_chars > max_chars):
                raise ValueError('Build section requires a resolved controller and unique authorization')
            authorizations[event.read_id]=event
        elif isinstance(event,t.ValidatedBuildSectionReadV1):
            auth=authorizations.get(event.read_id)
            if (auth is None or event.read_id in reads
                    or event.source_basis != auth.source_basis or event.source_class != auth.source_class
                    or event.line_start != auth.line_start or event.line_end != auth.line_end
                    or len(event.text) > auth.max_chars):
                raise ValueError('Build section receipt differs from its unique prior authorization')
            reads.add(event.read_id)
        elif isinstance(event,t.ProviderAttemptAuthorizedEventV1):
            if set(authorizations) != reads:
                raise ValueError('Provider cannot proceed with an unresolved Build section read')
            latest_attempt,latest_outcome=event.provider_attempt_id,None
        elif isinstance(event,t.ProviderOutcomeEventV1) and event.provider_attempt_id == latest_attempt:
            latest_outcome=event.outcome


def validate_selection_origin(execution, event):
    """A saved-work relevance vote must follow its one acknowledged controller."""
    from . import types as t
    before=execution.events[:event.sequence]
    providers=[e for e in before if isinstance(e,t.ProviderAttemptAuthorizedEventV1)]
    latest=providers[-1] if providers else None
    outcomes=[e.outcome for e in before if isinstance(e,t.ProviderOutcomeEventV1)
        and latest is not None and e.provider_attempt_id == latest.provider_attempt_id]
    if (latest is None or not outcomes or outcomes[-1] != 'response_received'
            or latest.provider_attempt_id != event.controller_attempt_id
            or latest.envelope_sha256 != event.controller_envelope_sha256
            or (latest.provider,latest.model,latest.api_mode) != execution.policy.provider_roles.controller.identity()
            or any(isinstance(e,t.BuildWriterEvidenceSelectionV1) for e in before)
            or any((e.provider,e.model,e.api_mode) == execution.policy.provider_roles.writer.identity() for e in providers)):
        raise ValueError('Writer selection lacks its unique acknowledged controller')


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
    if context_policy(execution.policy) == DRAFT_POLICY:
        from .types import BuildDraftContextCapturedV1
        captures = [e for e in execution.events[:boundary] if isinstance(e, BuildDraftContextCapturedV1)]
        if len(captures) != 1:
            raise ValueError("Selected primary work requires its complete captured draft")
        from .build_draft_context import native_build_action, captured_context_sha256
        action=native_build_action(execution)
        if (captured_context_sha256(captures[0].record) != action.intent.build_draft_context_sha256 if action is not None
                else captures[0].record.snapshot.snapshot_sha256 != execution.policy.working_draft_snapshot_sha256):
            raise ValueError("Selected primary work requires its complete captured draft")
        chosen = selection(execution).section_read_ids
        if len(set(chosen)) != len(chosen) or not set(chosen) <= {e.read_id for e in rows}:
            raise ValueError("Selected primary work requires unique acquired pre-selection reads")
        rows = tuple(e for e in rows if e.read_id in chosen)
    return rows


def writer_read_ids(execution):
    selected = selection(execution)
    return set(selected.section_read_ids) | {e.read_id for e in records(execution)}


def validate_writer_reads(execution, writer):
    """Keep actual saved-work inclusion equal to its existing selected closure."""
    from . import types as t
    before=execution.events[:writer.sequence]
    sections={e.event_id:e.read_id for e in before if isinstance(e,t.ValidatedBuildSectionReadV1)}
    included={sections[eid] for e in before if isinstance(e,t.BuildSectionProviderInclusionV1)
        and e.provider_attempt_id == writer.provider_attempt_id for eid in e.section_event_ids}
    if included != writer_read_ids(execution):
        raise ValueError('Source writer saved sections differ from selected closure')


def project(execution, basis=None):
    return {
        "policy": context_policy(execution.policy),
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


def native_work_frame(execution, basis):
    """Surface work only; the separate shared native frame owns World evidence."""
    from .build_draft_context import native_build_action, context_record, writer_reference, pack_body_aliases
    from .types import BuildSourceContextBasisV1
    action=native_build_action(execution)
    if action is None or type(basis) is not BuildSourceContextBasisV1:
        raise ValueError('Native Build work requires its concrete owning execution and basis')
    execution=type(execution).model_validate_json(execution.model_dump_json(by_alias=True))
    action=execution.policy.action
    from .build_world_context import validate_work_intent
    validate_work_intent(basis,action.intent)
    frame={'schema':NATIVE_WORK_SCHEMA,'source_basis':basis.model_dump(mode='json',by_alias=True),
        'artifact_under_edit':project(execution,basis)}
    if action.intent.build_draft_context_sha256 is not None:
        captured=context_record(execution)
        if captured.record.snapshot.saved_basis() != basis.model_dump(mode='json',by_alias=True):
            raise ValueError('Native Build work draft differs from its saved basis')
        frame['working_draft_context']=writer_reference(captured.record)
    from .build_intentional_response import selected_contract
    contract=selected_contract(execution)
    if contract is not None:
        frame['response_contract']=contract
    from .build_intentional_response import selected_action
    if selected_action(execution).operation in {'propose_build_insertion','prepare_build_image'}:
        capability=action.write_capability
        if capability is None:
            raise ValueError('Native authoring requires its captured editor capability')
        frame['captured_editor']=capability.model_dump(mode='json',exclude={'draft_markdown'})
        if 'working_draft_context' not in frame:
            frame['captured_editor']['draft_markdown']=capability.draft_markdown
    from .reviewed_action import writer_scope,SCOPE_KEY
    scope=writer_scope(execution)
    if scope is not None:
        frame[SCOPE_KEY]=scope
    from .plan_objective import contract as plan_contract,KEY as PLAN_OUTPUT_KEY
    plan=plan_contract(execution)
    if plan is not None:
        frame[PLAN_OUTPUT_KEY]=plan.model_dump(mode='json',by_alias=True)
    from .build_related_pages import project as project_related
    related=project_related(execution)
    if related is not None:
        frame['related_authored_pages']=related
    return pack_body_aliases(frame) if action.intent.build_draft_context_sha256 is not None else frame


def verify_native_work_input(execution, basis, raw):
    """Reconstruct the exact physical SDK work frame from actual owning records.

    Actual APP admission must still supply its locked work basis and bind the
    authorizing provider event. This grants no read, edit or dispatch by itself.
    """
    from hashlib import sha256
    from .source_writer_output import responses_text_frame, strict_json
    from .rules_authority_types import canonical_bytes
    body=strict_json(raw)
    frame=responses_text_frame(raw,schemas={NATIVE_WORK_SCHEMA},label='Native Build work')
    if (body.get('model') != execution.policy.provider_roles.writer.model
            or canonical_bytes(frame) != canonical_bytes(native_work_frame(execution,basis))):
        raise ValueError('Native Build SDK input differs from its exact saved-work/draft owner')
    return sha256(raw.encode()).hexdigest()


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
    if context_policy(execution.policy) == DRAFT_POLICY and "working_draft_context" not in packet:
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
