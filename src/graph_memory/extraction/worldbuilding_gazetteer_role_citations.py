"""Deterministically restore exact role-line citations for Gazetteer characters."""

from __future__ import annotations

from dataclasses import replace
import re
from typing import Any

from .extraction_profile import register_extraction_profile
from .worldbuilding_gazetteer_profile import (
    GAZETTEER_LIVESTOCK_HYGIENE_PROFILE,
    compile_gazetteer_livestock_hygiene,
)

PROFILE_ID = "worldbuilding_gazetteer_v1"
PROFILE_VERSION = "1.7"
PROFILE = f"{PROFILE_ID}@{PROFILE_VERSION}"
_PRIOR_PROFILE = "worldbuilding_gazetteer_v1@1.6"
_PROFILE_WARNING = f"source_support_policy:{PROFILE}"
_UNCERTAIN_ROLE_PREFIX = re.compile(
    r"\b(?:perhaps|possibly|potentially|allegedly|purportedly)\b", re.IGNORECASE,
)
_MODAL_ROLE_PREFIX = re.compile(
    r"\b(?:may|might|could|would|should|will)\s+(?!is\b|was\b|has\b)"
    r"(?:[a-z'-]+\s+)*(?:be|become|serve|act|hold|remain|take|assume)\b",
    re.IGNORECASE,
)
_CONDITIONAL_ROLE_CLAUSE = re.compile(
    r"\b(?:if|unless|provided\s+that|subject\s+to)\b", re.IGNORECASE,
)
_NEGATED_ROLE_PREFIX = re.compile(
    r"\b(?:not(?!\s+only\b)|never|no\s+longer|formerly|former|"
    r"isn['’]t|wasn['’]t)\b", re.IGNORECASE,
)
_CLAUSE_BOUNDARY = re.compile(r",|\b(?:and|but|yet|while|whereas)\b", re.IGNORECASE)


def _normalized(value: Any) -> str:
    text = str(value or "").replace("**", "").replace("__", "")
    return re.sub(r"\s+", " ", text).strip().removesuffix(".")


def _role_value(row: dict[str, Any]) -> str | None:
    raw = str(row.get("text") or "").strip()
    for marker in ("**", "__", "*", "_"):
        if raw.startswith(marker):
            closing = raw.find(marker, len(marker))
            if closing > len(marker):
                raw = raw[len(marker):closing] + raw[closing + len(marker):]
            break
    label, separator, value = raw.partition(":")
    if not separator or label.strip().casefold() != "role":
        return None
    role = _normalized(value.strip().strip("*_` "))
    return role or None


def _affirmed_role_occurrence(description: str, role: str) -> bool:
    text = _normalized(description)
    pattern = re.compile(rf"(?<!\w){re.escape(role)}(?!\w)", re.IGNORECASE)
    for match in pattern.finditer(text):
        # Qualifiers belong to the containing sentence, not an arbitrary window.
        start = max(text.rfind(mark, 0, match.start()) for mark in ".!?;") + 1
        ends = [text.find(mark, match.end()) for mark in ".!?;"]
        end = min((index for index in ends if index >= 0), default=len(text))
        before = text[start:match.start()]
        after = text[match.end():end]
        # A separate coordinated clause may qualify a future action rather than
        # the present role. A modal must introduce a predicate, so names such as
        # May and Will do not count as uncertainty on their own.
        prefix = _CLAUSE_BOUNDARY.split(before)[-1]
        suffix = re.split(r"\b(?:and|but|yet|while|whereas)\b", after, maxsplit=1,
                          flags=re.IGNORECASE)[0]
        if (
            _UNCERTAIN_ROLE_PREFIX.search(prefix)
            or _MODAL_ROLE_PREFIX.search(prefix)
            or _CONDITIONAL_ROLE_CLAUSE.search(prefix + " " + suffix)
            or re.match(r"^\s*(?:if|unless|provided\s+that|subject\s+to)\b",
                        before, re.IGNORECASE)
        ):
            continue
        if _NEGATED_ROLE_PREFIX.search(prefix):
            continue
        if re.match(
            r"\s*(?:but\s+)?(?:not|never|no longer|formerly)\b",
            after,
            re.IGNORECASE,
        ):
            continue
        return True
    return False


def compile_gazetteer_role_citations(
    graph: dict[str, Any], rows: list[dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Apply v1.6 hygiene, then cite only an already-present unique role claim."""
    result, diagnostics = compile_gazetteer_livestock_hygiene(graph, rows)
    hygiene = diagnostics.get("livestock_semantic_hygiene")
    if isinstance(hygiene, dict):
        hygiene["profile"] = PROFILE
    for item in result.get("deferred_items", []):
        if not isinstance(item, dict) or not isinstance(item.get("warnings"), list):
            continue
        item["warnings"] = [
            _PROFILE_WARNING if warning == f"source_support_policy:{_PRIOR_PROFILE}" else warning
            for warning in item["warnings"]
        ]

    span_counts: dict[str, int] = {}
    for row in rows:
        span_ref = row.get("source_span_ref_id")
        if isinstance(span_ref, str) and span_ref:
            span_counts[span_ref] = span_counts.get(span_ref, 0) + 1

    records: list[dict[str, str]] = []
    for row in rows:
        role = _role_value(row)
        if role is None:
            continue
        span_ref = row.get("source_span_ref_id")
        text = row.get("text")
        reason: str | None = None
        target: dict[str, Any] | None = None
        if not isinstance(span_ref, str) or not span_ref or not isinstance(text, str) or not text:
            reason = "invalid_source_row"
        elif span_counts.get(span_ref) != 1:
            reason = "ambiguous_source_span"
        else:
            matches = [
                node for node in result.get("nodes", [])
                if isinstance(node, dict)
                and node.get("node_type") == "character"
                and isinstance(node.get("description"), str)
                and _affirmed_role_occurrence(node["description"], role)
            ]
            if len(matches) != 1:
                reason = "ambiguous_character_match" if len(matches) > 1 else "no_matching_character_claim"
            else:
                target = matches[0]
                refs = target.get("evidence_refs")
                if refs is not None and not isinstance(refs, list):
                    reason = "invalid_character_evidence_refs"
                elif any(
                    isinstance(ref, dict) and ref.get("source_span_ref_id") == span_ref
                    for ref in refs or []
                ):
                    reason = "already_cited"

        if reason is not None:
            records.append({"source_span_ref_id": str(span_ref or ""), "decision": reason})
            continue
        assert target is not None
        target.setdefault("evidence_refs", []).append({
            "source_span_ref_id": span_ref,
            "anchor_quotes": [text],
        })
        records.append({
            "source_span_ref_id": span_ref,
            "candidate_node_id": str(target.get("node_id") or ""),
            "decision": "citation_added",
        })

    diagnostics["role_line_citations"] = {"profile": PROFILE, "records": records}
    return result, diagnostics


GAZETTEER_ROLE_CITATION_PROFILE = register_extraction_profile(replace(
    GAZETTEER_LIVESTOCK_HYGIENE_PROFILE,
    profile_version=PROFILE_VERSION,
    source_section_retainer=compile_gazetteer_role_citations,
))
