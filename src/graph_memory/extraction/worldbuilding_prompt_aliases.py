"""Request-local model handles, resolved to existing host evidence identities."""

from __future__ import annotations

from copy import deepcopy
import secrets
from typing import Any, Mapping, Sequence


def validate_worldbuilding_vocabulary(packet: Any) -> None:
    """Do not render a vocabulary identity when its semantic label is missing."""
    if packet is None:
        return
    for hint in packet.do_not_merge_hints:
        for identity in (hint.left_vocab_id, hint.right_vocab_id):
            label = packet.entry_labels.get(identity)
            if not isinstance(label, str) or not label.strip():
                raise ValueError("Worldbuilding vocabulary caution lacks a resolved label")


class WorldbuildingPromptAliases:
    """Keep source and candidate identities outside model-visible structures."""

    def __init__(self, source_rows: Sequence[Mapping[str, Any]], *, nonce: str | None = None) -> None:
        self._nonce = nonce or secrets.token_hex(8)
        if not self._nonce.isalnum():
            raise ValueError("invalid request-local alias namespace")
        self._span_to_handle: dict[str, str] = {}
        self._handle_to_span: dict[str, str] = {}
        self._rows: list[dict[str, Any]] = []
        self._node_to_handle: dict[str, str] = {}
        self._handle_to_node: dict[str, str] = {}
        self._beat_to_handle: dict[str, str] = {}
        self._handle_to_edge: dict[str, str] = {}
        for row in source_rows:
            span = row.get("source_span_ref_id")
            if not isinstance(span, str) or not span or span in self._span_to_handle:
                raise ValueError("invalid or duplicate source span")
            handle = f"S{self._nonce}_{len(self._rows) + 1}"
            self._span_to_handle[span] = handle
            self._handle_to_span[handle] = span
            self._rows.append({"source_span_ref_id": handle, "line_start": row["line_start"],
                               "line_end": row["line_end"], "text": row["text"]})
        if not self._rows:
            raise ValueError("Worldbuilding extraction requires source spans")

    def source_rows(self) -> list[dict[str, Any]]:
        return deepcopy(self._rows)

    def _evidence(self, refs: Any) -> list[dict[str, Any]]:
        projected = []
        for ref in refs or []:
            if not isinstance(ref, Mapping) or ref.get("source_span_ref_id") not in self._span_to_handle:
                raise ValueError("source evidence is not in the request")
            item: dict[str, Any] = {"source_span_ref_id": self._span_to_handle[ref["source_span_ref_id"]]}
            if "anchor_quotes" in ref:
                item["anchor_quotes"] = deepcopy(ref["anchor_quotes"])
            projected.append(item)
        return projected

    def nodes(self, nodes: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
        result = []
        seen: set[str] = set()
        for node in nodes:
            node_id = node.get("node_id")
            if not isinstance(node_id, str) or not node_id or node_id in seen:
                raise ValueError("invalid candidate node identity")
            seen.add(node_id)
            if node_id not in self._node_to_handle:
                handle = f"N{self._nonce}_{len(self._node_to_handle) + 1}"
                self._node_to_handle[node_id] = handle
                self._handle_to_node[handle] = node_id
            item = {key: deepcopy(node[key]) for key in ("label", "node_type", "description", "context_anchor") if key in node}
            item["node_id"] = self._node_to_handle[node_id]
            if node.get("evidence_refs"):
                item["evidence_refs"] = self._evidence(node["evidence_refs"])
            result.append(item)
        return result

    def beats(self, beats: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
        result = []
        for beat in beats:
            beat_id = beat.get("beat_id")
            if not isinstance(beat_id, str) or not beat_id or beat_id in self._beat_to_handle:
                raise ValueError("invalid candidate beat identity")
            self._beat_to_handle[beat_id] = f"B{self._nonce}_{len(result) + 1}"
            item = {key: deepcopy(beat[key]) for key in ("order", "title", "summary") if key in beat}
            item["beat_id"] = self._beat_to_handle[beat_id]
            try:
                item["involved_node_ids"] = [self._node_to_handle[node] for node in beat.get("involved_node_ids") or []]
            except (KeyError, TypeError) as exc:
                raise ValueError("beat node is not in the request") from exc
            item["evidence_refs"] = self._evidence(beat.get("evidence_refs"))
            result.append(item)
        return result

    def resolve_output(self, payload: Mapping[str, Any], *, endpoints: bool = False) -> dict[str, Any]:
        value = deepcopy(dict(payload))
        def visit(item: Any) -> None:
            if isinstance(item, dict):
                if "source_span_ref_id" in item:
                    handle = item["source_span_ref_id"]
                    if not isinstance(handle, str) or handle not in self._handle_to_span:
                        raise ValueError("unknown source evidence handle")
                    item["source_span_ref_id"] = self._handle_to_span[handle]
                if endpoints:
                    for key in ("from_node_id", "to_node_id"):
                        if key in item:
                            handle = item[key]
                            if not isinstance(handle, str) or handle not in self._handle_to_node:
                                raise ValueError("unknown candidate node handle")
                            item[key] = self._handle_to_node[handle]
                    if "involved_node_ids" in item:
                        handles = item["involved_node_ids"]
                        if not isinstance(handles, list) or any(not isinstance(h, str) or h not in self._handle_to_node for h in handles):
                            raise ValueError("unknown candidate node handle")
                        item["involved_node_ids"] = [self._handle_to_node[h] for h in handles]
                for nested in item.values():
                    visit(nested)
            elif isinstance(item, list):
                for nested in item:
                    visit(nested)
        visit(value)
        return value

    def review_graph(self, graph: Mapping[str, Any]) -> dict[str, Any]:
        nodes = self.nodes(graph.get("nodes") or [])
        edges = []
        self._handle_to_edge = {}
        for edge in graph.get("edges") or []:
            edge_id = edge.get("edge_id")
            if not isinstance(edge_id, str) or not edge_id or edge_id in self._handle_to_edge.values():
                raise ValueError("invalid or duplicate candidate edge identity")
            handle = f"R{self._nonce}_{len(edges) + 1}"
            self._handle_to_edge[handle] = edge_id
            item = {key: deepcopy(edge[key]) for key in ("label", "relationship_type", "predicate_family",
                    "semantic_state", "proposed_action", "confidence", "warnings") if key in edge}
            item["edge_id"] = handle
            for key in ("from_node_id", "to_node_id"):
                if edge.get(key) not in self._node_to_handle:
                    raise ValueError("edge endpoint is not in the request")
                item[key] = self._node_to_handle[edge[key]]
            item["evidence_refs"] = self._evidence(edge.get("evidence_refs"))
            edges.append(item)
        return {"nodes": nodes, "edges": edges}

    def resolve_review(self, parsed: Mapping[str, Any]) -> dict[str, Any]:
        if set(parsed) != {"retained_edge_ids"} or not isinstance(parsed["retained_edge_ids"], list):
            raise ValueError("invalid advisory selection")
        handles = parsed["retained_edge_ids"]
        if any(not isinstance(handle, str) or handle not in self._handle_to_edge for handle in handles):
            raise ValueError("unknown advisory edge handle")
        if len(handles) != len(set(handles)):
            raise ValueError("duplicate advisory edge handle")
        return {"retained_edge_ids": [self._handle_to_edge[handle] for handle in handles]}

    def record(self) -> dict[str, Any]:
        """Host-only mapping for interpreting retained private model responses."""
        return {"schema": "dmb_worldbuilding_prompt_aliases_v1",
                "source_handles": dict(self._handle_to_span),
                "node_handles": dict(self._handle_to_node),
                "beat_handles": {handle: original for original, handle in self._beat_to_handle.items()},
                "edge_handles": dict(self._handle_to_edge)}
