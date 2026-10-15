"""Advisory unchanged-subset selection; never factual or publication approval."""
from copy import deepcopy
from dataclasses import dataclass

from src.graph_memory.extraction.extraction_profile import ExtractionPassSpec
import hashlib
import json
import math

REASON = "advisory_review_omitted_not_proven_false"
_RESULT_FIELDS = ("parsed", "raw_text", "usage", "cost_usd", "elapsed_ms", "response_id")
_OBSERVATION_FIELDS = (
    "provider", "requested_model", "resolved_model", "response_model", "state",
    "provider_attempt_count", "retry_count", "conformance_retry_count",
    "transport_retry_count", "input_tokens", "output_tokens", "cached_input_tokens",
    "reasoning_tokens", "cost_usd", "pricing_source", "latency_ms",
    "provider_response_id", "failure_code",
)


def json_copy(value):
    """Strict JSON, without arbitrary serialization hooks or object repr."""
    def validate(item):
        if item is None or type(item) in (str, bool, int):
            return
        if type(item) is float and math.isfinite(item):
            return
        if type(item) is list:
            for child in item:
                validate(child)
            return
        if type(item) is dict and all(type(key) is str for key in item):
            for child in item.values():
                validate(child)
            return
        raise ValueError("private review evidence is not JSON safe")
    validate(value)
    return json.loads(json.dumps(value, ensure_ascii=False, allow_nan=False))


def digest(value):
    return hashlib.sha256(json.dumps(json_copy(value), sort_keys=True,
                                   ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()


def edge_ids(edges):
    ids = [edge.get("edge_id") for edge in edges]
    if any(type(item) is not str or not item.strip() for item in ids) or len(set(ids)) != len(ids):
        raise ValueError("advisory review requires unique nonblank string input edge IDs")
    return ids


@dataclass(frozen=True)
class ConstrainedEdgeReviewPassSpec(ExtractionPassSpec):
    """A review-only request-local constraint; None means not yet bound."""
    allowed_edge_ids: tuple[str, ...] | None = None

    def __post_init__(self):
        if self.kind != "edge_review":
            raise ValueError("ID constraints require an edge review spec")
        if self.allowed_edge_ids is not None:
            constrained_edge_ids(self)


def constrained_edge_ids(spec):
    if not isinstance(spec, ConstrainedEdgeReviewPassSpec) or spec.kind != "edge_review":
        raise ValueError("ID constraints require a specialized edge review spec")
    ids = spec.allowed_edge_ids
    if type(ids) is not tuple or not ids:
        raise ValueError("advisory ID constraint is unbound or empty")
    edge_ids([{"edge_id": item} for item in ids])
    return ids


def review_prompt(graph, source_rows, *, allowed_edge_ids=None):
    ids = edge_ids(graph.get("edges", []))  # Validate before spending a provider call.
    payload = {
        "source_packet": source_rows,
        "endpoint_navigation_not_accepted_truth": [
            {key: node.get(key) for key in ("node_id", "label", "node_type", "description")}
            for node in graph.get("nodes", [])
        ],
        "edge_proposals": graph.get("edges", []),
    }
    if allowed_edge_ids is not None:
        if type(allowed_edge_ids) is not tuple or list(allowed_edge_ids) != ids:
            raise ValueError("review allowlist must exactly match canonical proposals")
        payload["allowed_edge_ids"] = list(allowed_edge_ids)
        payload["id_selection_rule"] = (
            "Return only exact IDs from allowed_edge_ids. Missing numbers and gaps "
            "are intentional; never infer, add or repair an ID."
        )
    return json.dumps(payload, ensure_ascii=False, allow_nan=False)


def apply_review(graph, parsed):
    original_ids = edge_ids(graph.get("edges", []))
    if type(parsed) is not dict or set(parsed) != {"retained_edge_ids"}:
        raise ValueError("advisory review requires only retained_edge_ids")
    ids = parsed["retained_edge_ids"]
    if (type(ids) is not list or any(type(item) is not str or not item.strip() for item in ids)
            or len(set(ids)) != len(ids) or not set(ids).issubset(original_ids)):
        raise ValueError("advisory review returned invalid or unknown edge IDs")
    result = deepcopy(graph)
    keep = set(ids)
    retained = [deepcopy(edge) for edge in graph.get("edges", []) if edge["edge_id"] in keep]
    deferred = [deepcopy(edge) for edge in graph.get("edges", []) if edge["edge_id"] not in keep]
    existing = {item["item_id"] for item in result.get("deferred_items", [])}
    for edge in deferred:
        item_id = "deferred:advisory-edge-review:" + edge["edge_id"]
        if item_id in existing:
            raise ValueError("advisory review disposition identity collision")
        existing.add(item_id)
        result.setdefault("deferred_items", []).append({
            "item_id": item_id, "label": edge.get("label") or "", "reason": REASON,
            "evidence_refs": deepcopy(edge.get("evidence_refs") or []),
            "warnings": ["advisory_selection_is_not_factual_acceptance"],
            "suggested_next_step": "Review the unchanged proposal and its source support.",
        })
    result["edges"] = retained
    return result, {"before_sha256": digest(graph), "retained": retained,
                    "deferred": deferred, "retained_count": len(retained),
                    "deferred_count": len(deferred), "semantic_acceptance": False}


class RecordingPassClient:
    """Private evidence capture around the same validated bounded GE instance."""
    def __init__(self, client):
        self.client = client
        self.completed = []
        self.pending = None
        self.advisory = None

    def run_pass(self, name, **kwargs):
        from src.graph_memory.extraction.category_candidate_graph_schema import schema_for_pass_spec

        self.pending = {"pass_id": name, "seam_request_sha256": digest({
            "model_id": kwargs["model_id"], "instructions": kwargs["instructions"],
            "user_content": kwargs["user_content"],
            "pass_spec": {
                "pass_id": kwargs["pass_spec"].pass_id,
                "kind": kwargs["pass_spec"].kind,
                "output_schema": schema_for_pass_spec(kwargs["pass_spec"]),
            },
        })}
        result = self.client.run_pass(name, **kwargs)
        if type(result) is dict and type(result.get("raw_text")) is str:
            self.pending["returned_raw_text"] = result["raw_text"]
        record = {**{key: value for key, value in self.pending.items() if key != "returned_raw_text"},
                  **json_copy({key: result.get(key) for key in _RESULT_FIELDS})}
        self.completed.append(record)
        self.pending = None
        return result

    def bundle(self, options, profile, *, error=None):
        observations = []
        for call in self.client.calls:
            observation = call.get("observation")
            row = {"observation": None if observation is None else {
                key: observation[key] for key in _OBSERVATION_FIELDS if key in observation}}
            for key in ("pass_name", "external_outcome", "response_artifact_path", "response_artifact_sha256"):
                if key in call:
                    row[key] = call[key]
            row["attempt_evidence"] = [{key: item[key] for key in (
                "event_id", "ordinal", "kind", "response_status", "path", "sha256"
            ) if key in item} for item in call.get("attempt_evidence", [])]
            observations.append(row)
        payload = {
            "schema": "dmb_private_extraction_failure_bundle_v1" if error else "dmb_private_extraction_review_bundle_v1",
            "profile": profile.qualified_id,
            "source_artifact_id": options.source_artifact_id or options.source_span_index.get("source_artifact_id"),
            "source_sha256": hashlib.sha256((options.source_text or "").encode()).hexdigest(),
            "completed_passes": self.completed, "pending_pass": self.pending,
            "execution_observations": observations, "advisory": self.advisory,
        }
        if error is not None:
            raw = getattr(error, "raw_model_response", None)
            payload["failure"] = {"type": type(error).__name__, "raw_text": raw if type(raw) is str else None}
        return json.dumps(json_copy(payload), ensure_ascii=False, allow_nan=False)
