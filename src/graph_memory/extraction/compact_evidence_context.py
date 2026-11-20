"""Request-local paragraph handles for recap beat/edge prompts only.

Full source text stays in the packet; only repeated citation packaging is removed.
The model cannot define the dictionary or supply authority through a node hint.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import re
from typing import Any, Mapping, Sequence


class CompactEvidenceContext:
    def __init__(self, rows: Sequence[Mapping[str, Any]], *, source_sha256: str):
        self.source_sha256 = source_sha256
        self.entries: list[dict[str, Any]] = []
        self._by_span: dict[str, str] = {}
        self._by_handle: dict[str, str] = {}
        for row in rows:
            span, text = row["source_span_ref_id"], row["text"]
            if not isinstance(span, str) or not span or not isinstance(text, str) or span in self._by_span:
                raise ValueError("invalid or duplicate compact evidence source span")
            handle = f"E{len(self.entries) + 1}"
            self._by_span[span] = handle
            self._by_handle[handle] = span
            self.entries.append({"handle": handle, "source_span_ref_id": span,
                                 "text": text, "text_sha256": hashlib.sha256(text.encode()).hexdigest(),
                                 "line_start": row["line_start"], "line_end": row["line_end"]})

    def prompt_rows(self) -> list[dict[str, Any]]:
        return [{"source_span_ref_id": e["handle"], "text": e["text"],
                 "line_start": e["line_start"], "line_end": e["line_end"]} for e in self.entries]

    def inventory(self, nodes: Sequence[Mapping[str, Any]], *, descriptions: bool) -> list[dict[str, Any]]:
        result = []
        for node in nodes:
            compact = {key: node[key] for key in ("node_id", "label", "node_type") if key in node}
            if descriptions and node.get("description"):
                compact["description"] = node["description"]
            if node.get("context_anchor"):
                compact["context_anchor"] = True
            refs = node.get("evidence_refs") or []
            compact["evidence_ids"] = list(dict.fromkeys(
                self._by_span[ref["source_span_ref_id"]] for ref in refs
                if isinstance(ref, Mapping) and ref.get("source_span_ref_id") in self._by_span
            ))
            result.append(compact)
        return result

    def expand(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        """Resolve explicit citation fields only; quotes and prose are untouched.

        Canonical IDs retain the original validator's authority/deferral behavior.
        Unknown short handles and malformed citations fail closed here.
        """
        value = deepcopy(dict(payload))
        def visit(item):
            if isinstance(item, dict):
                if "source_span_ref_id" in item:
                    ref = item["source_span_ref_id"]
                    if not isinstance(ref, str):
                        raise ValueError("malformed compact evidence reference")
                    if ref in self._by_handle:
                        item["source_span_ref_id"] = self._by_handle[ref]
                    elif re.match(r"^E[0-9]", ref):
                        raise ValueError("unknown compact evidence reference")
                    # Canonical citations still go through the original span/quote
                    # validator, including its per-item deferral semantics.
                for child in item.values():
                    visit(child)
            elif isinstance(item, list):
                for child in item:
                    visit(child)
        visit(value)
        return value

    def record(self) -> dict[str, Any]:
        return {"schema": "dmb_compact_recap_evidence_context_v1",
                "source_sha256": self.source_sha256, "entries": deepcopy(self.entries)}


COMPACT_EVIDENCE_GUIDANCE = (
    "Evidence dictionary: the Source Packet contains each admitted paragraph once, "
    "identified by request-local E handles. Node evidence_ids are navigation hints, "
    "not proof of any claim. For output evidence_refs.source_span_ref_id use the exact "
    "E handle of the paragraph that supports the claim, and copy anchor_quotes verbatim "
    "from that paragraph. Do not use a node description as evidence. Preserve who said "
    "or believed a claim, uncertainty, plans versus completed actions, and temporal scope "
    "in every label and assertion. Do not infer a relationship from shared evidence_ids. "
    "Never cite supplemental context as if it were a Source Packet paragraph.\n\n"
)
