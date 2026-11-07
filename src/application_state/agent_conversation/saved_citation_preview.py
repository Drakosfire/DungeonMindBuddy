"""Stored answer presentation only; exact source reads retain admission ownership."""
from pydantic import ValidationError
from . import types as t
from .native_completion import SurfaceNativeCompletionV1

_NATIVE = {"dmb_surface_native_completion_v1": SurfaceNativeCompletionV1,
    **{f"dmb_surface_evidence_completion_v{n}": getattr(t, f"SurfaceEvidenceCompletionV{n}")
       for n in range(3, 8)}}
_FAMILIES = ("native_source_citations", "native_body_citations",
             "native_clause_citations", "native_assertion_citations")
_SEGMENTS = {"source_passage_claim", "native_assertion_claim", "saved_source_claim",
             "proposal", "limitation", "discussion", "draft_reference_claim"}


def details_required(reason):
    return {"status": "details_required", "reason": reason}


def project(row):
    """No receipt/execution reconstruction, current page lookup or source IO."""
    if row["status"] != "completed" or not row["assistant_text"]:
        return None
    if type(row["citation_has_rules"]) is not bool:
        return details_required("invalid_presentation")
    if row["citation_has_rules"]:
        # Base text/markers cannot stand in for the sealed Rules composition.
        return details_required("mixed_rules")
    raw = row["completion"]
    codec = _NATIVE.get(raw.get("schema")) if isinstance(raw, dict) else None
    if codec is None:
        return details_required("unsupported_completion")
    try:
        completion = codec.model_validate(raw)
        if (completion.surface_id != row["surface_id"]
                or "\n".join(s.text for s in completion.answer_segments) != row["assistant_text"]):
            return details_required("invalid_presentation")
        if (any(s.kind not in _SEGMENTS for s in completion.answer_segments)
                or getattr(completion, "source_citations", ())
                or getattr(completion, "citation_map", None)):
            return details_required("unsupported_sources")
        saved = getattr(completion, "saved_source_citations", ())
        basis = None
        if saved:
            from .types import BuildSourceContextBasisV1
            basis = BuildSourceContextBasisV1.model_validate(row["citation_source_basis"])
            if (completion.surface_id != "build" or basis.world_id != row["world_id"]
                    or any(s.kind == "saved_source_claim" and s.content_sha256 != basis.content_sha256
                           for s in completion.answer_segments)):
                return details_required("invalid_presentation")
        families = {name: [c.model_dump(mode="json", by_alias=True)
                            for c in getattr(completion, name, ())] for name in _FAMILIES}
        if any(c.get("managed_world_id", row["world_id"]) != row["world_id"]
               for citations in families.values() for c in citations):
            return details_required("invalid_presentation")
        return {"schema": "dmb_saved_native_citation_preview_v1", "status": "ready",
            "surface_id": completion.surface_id,
            "answer_segments": [{"kind": s.kind, "text": s.text,
                **({"content_sha256": s.content_sha256} if s.kind == "saved_source_claim" else {})}
                for s in completion.answer_segments],
            **families, "saved_source_citations": [c.model_dump(mode="json") for c in saved],
            "source_basis": basis.model_dump(mode="json", by_alias=True) if basis else None}
    except (ValidationError, ValueError, TypeError, AttributeError, KeyError):
        return details_required("invalid_presentation")
