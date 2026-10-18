"""Host-owned literal quote validation for recap candidate graphs.

This module deliberately does not infer what a quote means. It only binds
candidate evidence to a canonical source paragraph and withholds positive items
whose supplied anchor quotes are not normalized literal matches.
"""

from __future__ import annotations

import copy
import hashlib
import json
from collections.abc import Mapping
from typing import Any

from graph_memory.anchor_quotes import (
    anchor_quote_matches_to_dicts,
    find_anchor_quote_matches,
)
from graph_memory.source_span import (
    SourceSpanIndex,
    build_source_span_index_for_text,
    document_source_ref_id,
    source_span_index_from_dict,
    source_span_index_to_dict,
    validate_source_span_index,
)


NONLITERAL_QUOTE_REASON = "recap_nonliteral_anchor_quote"
DEPENDENT_ITEM_REASON = "recap_dependency_on_quote_deferred_item"

_POSITIVE_COLLECTIONS: tuple[tuple[str, str, str], ...] = (
    ("nodes", "node_id", "label"),
    ("edges", "edge_id", "label"),
    ("beats", "beat_id", "title"),
    ("source_observations", "observation_id", "title"),
    ("proposed_writes", "write_id", "label"),
)


class RecapQuoteIntegrityError(ValueError):
    """A source or evidence identity cannot be safely validated."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _normalized_sha256(value: str) -> str:
    digest = str(value or "").strip().lower()
    if digest.startswith("sha256:"):
        digest = digest.removeprefix("sha256:")
    if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
        raise RecapQuoteIntegrityError(
            "source_digest_invalid", "the recap source digest is malformed"
        )
    return digest


def _validate_source_binding(
    *,
    source_text: str,
    source_artifact_id: str,
    source_sha256: str,
    source_span_index: Mapping[str, Any],
) -> tuple[SourceSpanIndex, dict[str, Any], str]:
    if not isinstance(source_text, str) or not source_text:
        raise RecapQuoteIntegrityError(
            "source_text_missing", "the frozen recap source text is missing"
        )
    artifact_id = str(source_artifact_id or "").strip()
    if not artifact_id:
        raise RecapQuoteIntegrityError(
            "source_artifact_missing", "the frozen recap SourceArtifact ID is missing"
        )
    expected_digest = _normalized_sha256(source_sha256)
    observed_digest = hashlib.sha256(source_text.encode("utf-8")).hexdigest()
    if observed_digest != expected_digest:
        raise RecapQuoteIntegrityError(
            "source_digest_mismatch", "the frozen recap source digest does not match its bytes"
        )
    if not isinstance(source_span_index, Mapping):
        raise RecapQuoteIntegrityError(
            "source_index_missing", "the canonical recap SourceSpanIndex is missing"
        )
    try:
        parsed_index = source_span_index_from_dict(source_span_index)
        validate_source_span_index(
            parsed_index,
            source_artifact_id=artifact_id,
            content_sha256=expected_digest,
        )
        canonical_index = build_source_span_index_for_text(
            source_artifact_id=artifact_id,
            content_sha256=expected_digest,
            text=source_text,
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise RecapQuoteIntegrityError(
            "source_index_invalid", "the recap SourceSpanIndex failed validation"
        ) from exc
    if dict(source_span_index) != source_span_index_to_dict(canonical_index):
        raise RecapQuoteIntegrityError(
            "source_index_mismatch",
            "the recap SourceSpanIndex does not match the frozen source bytes",
        )
    return parsed_index, source_span_index_to_dict(canonical_index), expected_digest


def _canonical_source_ref(
    raw_ref: Any,
    *,
    artifact_id: str,
    source_ref_id: str,
    spans_by_id: Mapping[str, Any],
    source_lines: list[str],
) -> tuple[dict[str, Any], int, bool]:
    if not isinstance(raw_ref, Mapping):
        raise RecapQuoteIntegrityError(
            "evidence_ref_invalid", "a recap evidence reference is malformed"
        )
    ref = dict(raw_ref)
    if str(ref.get("source_artifact_id") or "").strip() != artifact_id:
        raise RecapQuoteIntegrityError(
            "source_artifact_mismatch",
            "a recap evidence reference is not bound to the frozen SourceArtifact",
        )
    if str(ref.get("source_ref_id") or "").strip() != source_ref_id:
        raise RecapQuoteIntegrityError(
            "source_ref_mismatch",
            "a recap evidence reference is not bound to the frozen source text",
        )
    if str(ref.get("evidence_role") or "") != "source_evidence":
        raise RecapQuoteIntegrityError(
            "source_evidence_role_invalid",
            "a positive recap reference is not host-admitted source evidence",
        )
    span_id = str(ref.get("source_span_ref_id") or "").strip()
    span = spans_by_id.get(span_id)
    if not span_id or span is None:
        raise RecapQuoteIntegrityError(
            "source_span_mismatch",
            "a recap evidence reference does not resolve to a canonical source span",
        )
    expected_anchor_id = f"anchor:{span_id}"
    anchor_id = str(ref.get("source_anchor_id") or "").strip()
    if anchor_id and anchor_id != expected_anchor_id:
        raise RecapQuoteIntegrityError(
            "source_anchor_mismatch",
            "a recap evidence reference carries a noncanonical source anchor",
        )
    if (
        span.source_artifact_id != artifact_id
        or span.source_ref_id != source_ref_id
        or span.content_sha256 == ""
        or span.start_line < 1
        or span.end_line < span.start_line
        or span.end_line > len(source_lines)
    ):
        raise RecapQuoteIntegrityError(
            "source_span_mismatch", "a recap source span is outside its canonical source"
        )
    paragraph = "\n".join(source_lines[span.start_line - 1 : span.end_line]).strip()
    if not paragraph:
        raise RecapQuoteIntegrityError(
            "source_span_empty", "a recap evidence span resolves to empty source content"
        )

    raw_quotes = ref.get("anchor_quotes")
    if not isinstance(raw_quotes, list) or not raw_quotes:
        ref["anchor_quotes"] = []
        ref["anchor_quote_matches"] = []
        return ref, 0, True

    verified_quotes: list[str] = []
    verified_matches: list[dict[str, Any]] = []
    invalid = False
    for raw_quote in raw_quotes:
        if not isinstance(raw_quote, str) or not raw_quote.strip():
            invalid = True
            continue
        matches = find_anchor_quote_matches(paragraph, [raw_quote])
        if not matches:
            invalid = True
            continue
        verified_quotes.append(raw_quote)
        verified_matches.extend(anchor_quote_matches_to_dicts(matches))

    # Cached matches are never evidence. Replace them with matches recomputed
    # from the exact pinned paragraph, including on deferred diagnostic refs.
    ref["anchor_quotes"] = verified_quotes
    ref["anchor_quote_matches"] = verified_matches
    return ref, len(verified_quotes), invalid


def _record_id(item: Mapping[str, Any], key: str) -> str:
    item_id = str(item.get(key) or "").strip()
    if not item_id:
        raise RecapQuoteIntegrityError(
            "candidate_item_id_missing", "a recap candidate item has no stable ID"
        )
    return item_id


def _validate_positive_item(
    item: Any,
    *,
    id_key: str,
    label_key: str,
    artifact_id: str,
    source_ref_id: str,
    spans_by_id: Mapping[str, Any],
    source_lines: list[str],
) -> tuple[dict[str, Any], str, int, int, bool]:
    if not isinstance(item, Mapping):
        raise RecapQuoteIntegrityError(
            "candidate_item_invalid", "a positive recap candidate item is malformed"
        )
    normalized = dict(item)
    item_id = _record_id(normalized, id_key)
    refs = normalized.get("evidence_refs")
    if not isinstance(refs, list) or not refs:
        raise RecapQuoteIntegrityError(
            "candidate_evidence_missing",
            "a positive recap candidate item has no source evidence references",
        )
    valid_refs: list[dict[str, Any]] = []
    quote_count = 0
    invalid_quote = False
    for raw_ref in refs:
        normalized_ref, valid_count, ref_invalid = _canonical_source_ref(
            raw_ref,
            artifact_id=artifact_id,
            source_ref_id=source_ref_id,
            spans_by_id=spans_by_id,
            source_lines=source_lines,
        )
        quote_count += valid_count
        invalid_quote = invalid_quote or ref_invalid
        if normalized_ref.get("anchor_quotes"):
            valid_refs.append(normalized_ref)
    normalized["evidence_refs"] = valid_refs
    return normalized, item_id, quote_count, len(refs), invalid_quote


def _deferred_item(
    *,
    item: Mapping[str, Any],
    item_id: str,
    label_key: str,
    reason_code: str,
) -> dict[str, Any]:
    label = str(item.get(label_key) or item_id).strip() or item_id
    if reason_code == NONLITERAL_QUOTE_REASON:
        reason = "A source quote did not match its exact pinned source paragraph."
    else:
        reason = "This item depends on a candidate withheld by recap quote integrity."
    evidence_refs = [
        copy.deepcopy(ref)
        for ref in item.get("evidence_refs", [])
        if isinstance(ref, Mapping) and ref.get("anchor_quotes")
    ]
    return {
        "item_id": item_id,
        "label": label,
        "reason": reason,
        "evidence_refs": evidence_refs,
        "suggested_next_step": "Inspect the pinned source span before restoring this item.",
        "warnings": [reason_code],
    }


def _references_any_candidate_id(value: Any, candidate_ids: set[str]) -> str | None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            key_text = str(key)
            if key_text == "item_id":
                continue
            if isinstance(child, str) and child in candidate_ids:
                return key_text
            found = _references_any_candidate_id(child, candidate_ids)
            if found:
                return found
    elif isinstance(value, str):
        if value in candidate_ids:
            return "value"
    elif isinstance(value, (list, tuple)):
        for child in value:
            found = _references_any_candidate_id(child, candidate_ids)
            if found:
                return found
    return None


def validate_and_defer_nonliteral_recap_items(
    candidate_graph: Mapping[str, Any],
    *,
    source_text: str,
    source_artifact_id: str,
    source_sha256: str,
    source_span_index: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Validate source quotes and defer unsafe positive recap items.

    The input graph is not mutated. Source identity/span problems raise a typed
    error so the owning runner can persist a failed validation run. Nonliteral
    quotes create stable existing ``DeferredItem`` records instead.
    """
    if not isinstance(candidate_graph, Mapping):
        raise RecapQuoteIntegrityError(
            "candidate_graph_invalid", "the recap candidate graph is malformed"
        )
    index, canonical_payload, digest = _validate_source_binding(
        source_text=source_text,
        source_artifact_id=source_artifact_id,
        source_sha256=source_sha256,
        source_span_index=source_span_index,
    )
    artifact_id = str(source_artifact_id).strip()
    source_ref_id = document_source_ref_id(artifact_id)
    graph = copy.deepcopy(dict(candidate_graph))
    source_ids = graph.get("source_artifact_ids")
    if (
        not isinstance(source_ids, list)
        or source_ids != [artifact_id]
    ):
        raise RecapQuoteIntegrityError(
            "candidate_source_identity_mismatch",
            "the recap candidate graph is not bound to exactly its frozen source",
        )

    spans_by_id = {span.source_span_id: span for span in index.spans}
    source_lines = source_text.splitlines()
    deferred: list[dict[str, Any]] = []
    dispositions: list[dict[str, str]] = []
    deferred_ids: set[str] = set()
    deferred_node_ids: set[str] = set()
    checked_items = 0
    checked_refs = 0
    checked_quotes = 0

    existing_deferred = graph.get("deferred_items", [])
    if not isinstance(existing_deferred, list):
        raise RecapQuoteIntegrityError(
            "deferred_collection_invalid", "the recap deferred-items collection is malformed"
        )
    existing_deferred_ids: set[str] = set()
    normalized_existing_deferred: list[dict[str, Any]] = []
    for raw_item in existing_deferred:
        if not isinstance(raw_item, Mapping):
            raise RecapQuoteIntegrityError(
                "deferred_item_invalid", "a recap deferred item is malformed"
            )
        item = copy.deepcopy(dict(raw_item))
        item_id = str(item.get("item_id") or "").strip()
        if not item_id or item_id in existing_deferred_ids:
            raise RecapQuoteIntegrityError(
                "deferred_item_id_invalid",
                "recap deferred item IDs are missing or duplicated",
            )
        existing_deferred_ids.add(item_id)
        refs = item.get("evidence_refs", [])
        if not isinstance(refs, list):
            raise RecapQuoteIntegrityError(
                "deferred_evidence_invalid", "a recap deferred item's evidence is malformed"
            )
        verified_refs: list[dict[str, Any]] = []
        had_invalid_quote = False
        for raw_ref in refs:
            verified, quote_count, invalid = _canonical_source_ref(
                raw_ref,
                artifact_id=artifact_id,
                source_ref_id=source_ref_id,
                spans_by_id=spans_by_id,
                source_lines=source_lines,
            )
            checked_refs += 1
            checked_quotes += quote_count
            had_invalid_quote = had_invalid_quote or invalid
            if verified.get("anchor_quotes"):
                verified_refs.append(verified)
        item["evidence_refs"] = verified_refs
        if had_invalid_quote:
            warnings = item.get("warnings") or []
            if not isinstance(warnings, list):
                warnings = []
            item["warnings"] = list(dict.fromkeys([*warnings, NONLITERAL_QUOTE_REASON]))
        normalized_existing_deferred.append(item)

    normalized_items: dict[str, list[tuple[dict[str, Any], str, int, int, bool]]] = {}
    positive_ids: set[str] = set()
    for collection, id_key, label_key in _POSITIVE_COLLECTIONS:
        raw_items = graph.get(collection, [])
        if not isinstance(raw_items, list):
            raise RecapQuoteIntegrityError(
                "candidate_collection_invalid",
                f"the recap {collection} collection is malformed",
            )
        checked: list[tuple[dict[str, Any], str, int, int, bool]] = []
        seen_ids: set[str] = set()
        duplicate_code = {
            "nodes": "duplicate_node_id",
            "edges": "duplicate_edge_id",
            "beats": "duplicate_beat_id",
            "source_observations": "duplicate_observation_id",
            "proposed_writes": "duplicate_write_id",
        }[collection]
        for raw_item in raw_items:
            normalized, item_id, quote_count, ref_count, invalid = _validate_positive_item(
                raw_item,
                id_key=id_key,
                label_key=label_key,
                artifact_id=artifact_id,
                source_ref_id=source_ref_id,
                spans_by_id=spans_by_id,
                source_lines=source_lines,
            )
            if item_id in seen_ids:
                raise RecapQuoteIntegrityError(
                    duplicate_code, f"{duplicate_code}: recap candidate item IDs are not unique"
                )
            seen_ids.add(item_id)
            if item_id in positive_ids or item_id in existing_deferred_ids:
                raise RecapQuoteIntegrityError(
                    "candidate_item_id_duplicate",
                    "recap candidate IDs collide across positive and deferred items",
                )
            positive_ids.add(item_id)
            checked_items += 1
            checked_refs += ref_count
            checked_quotes += quote_count
            if invalid:
                deferred_ids.add(item_id)
                if collection == "nodes":
                    deferred_node_ids.add(item_id)
                deferred.append(
                    _deferred_item(
                        item=normalized,
                        item_id=item_id,
                        label_key=label_key,
                        reason_code=NONLITERAL_QUOTE_REASON,
                    )
                )
                dispositions.append(
                    {"kind": collection, "item_id": item_id, "reason_code": NONLITERAL_QUOTE_REASON}
                )
            else:
                checked.append((normalized, item_id, quote_count, ref_count, False))
        normalized_items[collection] = checked

    # Dependency dispositions are computed from the complete set of quote-invalid
    # nodes, then propagated to all existing typed positive collections.
    for collection, id_key, label_key in _POSITIVE_COLLECTIONS:
        if collection == "nodes":
            continue
        kept: list[tuple[dict[str, Any], str, int, int, bool]] = []
        for item, item_id, quote_count, ref_count, _ in normalized_items[collection]:
            dependency = False
            if collection in {"edges", "beats", "source_observations"}:
                dependency = _references_any_candidate_id(item, deferred_node_ids) is not None
            elif collection == "proposed_writes":
                dependency = _references_any_candidate_id(item, deferred_ids) is not None
            if not dependency:
                kept.append((item, item_id, quote_count, ref_count, False))
                continue
            deferred_ids.add(item_id)
            deferred.append(
                _deferred_item(
                    item=item,
                    item_id=item_id,
                    label_key=label_key,
                    reason_code=DEPENDENT_ITEM_REASON,
                )
            )
            dispositions.append(
                {"kind": collection, "item_id": item_id, "reason_code": DEPENDENT_ITEM_REASON}
            )
        normalized_items[collection] = kept

    # Proposed writes can form a chain of target references; defer to a stable
    # fixed point rather than leaving a target dangling after one pass.
    writes = normalized_items.get("proposed_writes", [])
    while True:
        newly_deferred: list[tuple[dict[str, Any], str, int, int, bool]] = []
        kept_writes = []
        for item, item_id, quote_count, ref_count, _ in writes:
            if _references_any_candidate_id(item, deferred_ids) is None:
                kept_writes.append((item, item_id, quote_count, ref_count, False))
                continue
            deferred_ids.add(item_id)
            newly_deferred.append((item, item_id, quote_count, ref_count, False))
        if not newly_deferred:
            normalized_items["proposed_writes"] = kept_writes
            break
        for item, item_id, _, _, _ in newly_deferred:
            deferred.append(
                _deferred_item(
                    item=item,
                    item_id=item_id,
                    label_key="label",
                    reason_code=DEPENDENT_ITEM_REASON,
                )
            )
            dispositions.append(
                {"kind": "proposed_writes", "item_id": item_id, "reason_code": DEPENDENT_ITEM_REASON}
            )
        writes = kept_writes

    # Keep every surviving reference with freshly recomputed match offsets.
    for collection, _, _ in _POSITIVE_COLLECTIONS:
        if collection in graph:
            graph[collection] = [item for item, *_ in normalized_items.get(collection, [])]
    graph["deferred_items"] = [*normalized_existing_deferred, *deferred]

    if deferred_ids:
        # Check all retained positive items, plus any future/unknown root shape
        # (including standing links), for references we did not explicitly
        # disposition through the current typed candidate contract.
        for collection, _, _ in _POSITIVE_COLLECTIONS:
            for item in graph.get(collection) or []:
                key = _references_any_candidate_id(item, deferred_ids)
                if key:
                    raise RecapQuoteIntegrityError(
                        "unsupported_dependent_reference",
                        "a retained recap candidate item has an undispositioned candidate-ID reference",
                    )
        for root_key, root_value in graph.items():
            if root_key == "diagnostics":
                continue
            key = _references_any_candidate_id(root_value, deferred_ids)
            if key:
                raise RecapQuoteIntegrityError(
                    "unsupported_dependent_reference",
                    "an untyped recap graph structure references a deferred candidate ID",
                )

    return graph, {
        "schema": "dmb_recap_quote_integrity_v1",
        "source_artifact_id": artifact_id,
        "source_sha256": digest,
        "source_span_index_sha256": hashlib.sha256(
            (
                json.dumps(canonical_payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
                + "\n"
            ).encode("utf-8")
        ).hexdigest(),
        "positive_items_checked": checked_items,
        "evidence_refs_checked": checked_refs,
        "literal_quotes_verified": checked_quotes,
        "items_deferred": len(deferred),
        "invalid_quote_items": sum(
            1 for item in dispositions if item["reason_code"] == NONLITERAL_QUOTE_REASON
        ),
        "deferred_item_ids": dispositions,
    }
