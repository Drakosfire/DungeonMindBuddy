"""Persist exact Play source selections; preserve historical turn predicates.

Storage shape only: Core admits sources; APP binds reads and actual producer
bytes. This migration neither republishes facts nor rewrites retained rows.
"""

from importlib import import_module

from alembic import op
from sqlalchemy import text

revision = "20261106_0120"
down_revision = "20261106_0119"
branch_labels = None
depends_on = None

_m42 = import_module(
    "application_state.migrations.versions.20261020_0042_native_play_graph"
)
_m53 = import_module(
    "application_state.migrations.versions.20261022_0053_native_source_navigation"
)
_m56 = import_module(
    "application_state.migrations.versions.20261022_0056_native_source_input"
)
_m46 = import_module(
    "application_state.migrations.versions.20261022_0046_surface_evidence_answers"
)
R, E = _m42.R, _m42.E
CTX = R + "->'authored_source_context'"
AUTH = CTX + "->'authority'"
REFS = CTX + "->'references'"
_KEYS = "schema receipt_serializer_version context_receipt_sha256 play_graph_policy play_basis play_sources play_source_frame_sha256 retrieval_session_id graph_authority graph_packet assembled_input evidence_mode source_opened"
_RECEIPT = _m42._RECEIPT.replace(
    _m42._closed(R, _KEYS), _m42._closed(R, _KEYS + " authored_source_context")
)
_m79 = import_module(
    "application_state.migrations.versions.20261027_0079_corpus_source_search"
)
_KINDS = (
    *_m79._KINDS,
    "build_authored_references_captured_v1",
    "native_authored_source_read_v1",
    "native_body_provider_included_v1",
)
_INVALID = (
    "$[*] ? (!exists(@.kind) || ("
    + " && ".join('@.kind != "' + kind + '"' for kind in _KINDS)
    + "))"
)
# Preserve the owning capability dispatch and navigation/section companion
# checks. Extend all three existing closed policy variants for this input.
_EXECUTION = _m79._NEW
for _owner in (_m42, _m53._m47, _m53, _m56._m55._m54, _m56._m55, _m56, _m79):
    _invalid = getattr(_owner, "_INVALID", getattr(_owner, "_INVALID_KIND", None))
    _EXECUTION = _EXECUTION.replace(_invalid, _INVALID)
for _suffix in (
    " native_source_section_policy corpus_source_policy",
    " native_source_section_policy",
    "",
):
    _keys = _m53._POLICY_KEYS + _suffix
    _EXECUTION = _EXECUTION.replace(
        _m42._closed(_m42.POL, _keys),
        _m42._closed(_m42.POL, _keys + " authored_source_context"),
    )
_CONTEXT = _m42._and(
    _m42._closed(CTX, "schema authority references"),
    f"{CTX}->>'schema'='dmb_play_authored_source_context_v1'",
    f"{E}#>'{{policy,authored_source_context}}'={CTX}",
    _m42._closed(
        AUTH,
        "schema_version managed_world_id native_world_id binding_version provisioning_id revision_id domain_ref profile_ref acquisition_epoch scope role",
    ),
    f"{AUTH}->>'schema_version'='dmb_native_corpus_authority_v1'",
    f"{AUTH}->>'managed_world_id'=world_id",
    f"{AUTH}->>'native_world_id'={R}#>>'{{graph_authority,native_world_id}}'",
    f"{AUTH}->'binding_version'={R}#>'{{graph_authority,binding_version}}'",
    f"{AUTH}->>'revision_id'={R}#>>'{{graph_authority,graph_revision}}'",
    f"{AUTH}->>'scope'='gm_world_cross_campaign_source_inspection' AND {AUTH}->>'role'='gm'",
    _m42._closed(REFS, "schema references"),
    f"{REFS}->>'schema'='dmb_authored_references_v2'",
    f"jsonb_typeof({REFS}->'references')='array' AND jsonb_array_length({REFS}->'references')>0",
    f"NOT jsonb_path_exists({REFS}, '$.references[*] ? (!exists(@.schema) || @.schema != \"dmb_authored_source_reference_v1\")')",
)
# Reuse the existing mixed-answer storage predicate; only this capability adds
# native body citations. Runtime completion validation still owns all joins.
_COMPLETION = (
    _m46._MIXED.replace(
        "dmb_surface_evidence_completion_v1", "dmb_surface_evidence_completion_v5"
    )
    .replace(
        "'citation_map','source_citations'",
        "'citation_map','source_citations','native_source_citations','native_body_citations'",
    )
    .replace(
        '@.kind != "limitation"',
        '@.kind != "limitation" && @.kind != "session_summary"',
    )
    + " AND jsonb_typeof(completion->'native_source_citations')='array' AND jsonb_typeof(completion->'native_body_citations')='array'"
)
_SELECTED = (
    f"{R} ? 'authored_source_context' OR {E}->'policy' ? 'authored_source_context'"
)


def upgrade():
    for name, predicate in (
        ("agent_turn_graph_context_receipt_check", _RECEIPT),
        ("agent_turn_graph_context_execution_check", _EXECUTION),
        ("agent_turn_graph_completion_check", None),
    ):
        definition = (
            op.get_bind()
            .execute(
                text(
                    "SELECT pg_get_constraintdef(oid) FROM pg_constraint "
                    "WHERE conrelid='agent.turn'::regclass AND conname=:name"
                ),
                {"name": name},
            )
            .scalar_one()
        )
        if not definition.startswith("CHECK (") or not definition.endswith(")"):
            raise RuntimeError("Owning turn CHECK predicate unavailable")
        previous = definition[len("CHECK (") : -1]
        if predicate is None:
            predicate = f"({previous}) OR ({_COMPLETION})"
        _m42._replace(
            name,
            f"CASE WHEN {_SELECTED} THEN COALESCE((({_CONTEXT}) AND ({predicate})),FALSE) ELSE ({previous}) END",
        )


def downgrade():
    raise RuntimeError("Exact Play source references require recovery forward")
