"""Recognize narrow submitted role propositions without inventing ownership."""

from copy import deepcopy
import re
from typing import Any

from .worldbuilding_source_sections import retain_owned_sections

PROFILE = "worldbuilding_gazetteer_v1@1.3"
REASON = "proprietor_role_not_ownership_assertion"


def _clean(text: str) -> str:
    return (
        re.sub(r"\s+", " ", text.replace("**", "").replace("__", ""))
        .strip()
        .removesuffix(".")
    )


def _proposition(text: str, actor: str, target: str) -> str:
    text, actor, target = (
        _clean(text),
        re.escape(_clean(actor)),
        re.escape(_clean(target)),
    )
    if re.fullmatch(actor + r"\s*[–—-]\s*Proprietor of (?:the )?" + target, text, re.I):
        return "role_only"
    if re.fullmatch(actor + r" owns (?:the )?" + target, text, re.I) or re.fullmatch(
        actor + r"\s*[–—-]\s*Owner of (?:the )?" + target, text, re.I
    ):
        return "ownership_proposition"
    return "unresolved"


def compile_role_support(graph: dict[str, Any], rows: list[dict[str, Any]]):
    result, diagnostics = retain_owned_sections(graph, rows)
    spans = {row["source_span_ref_id"]: row["text"] for row in rows}
    labels: dict[str, list[str]] = {}
    for node in result.get("nodes", []):
        labels.setdefault(node["node_id"], []).append(str(node.get("label") or ""))
    records, kept = [], []
    for edge in result.get("edges", []):
        if edge.get("relationship_type") != "owns":
            kept.append(edge)
            continue
        subjects = labels.get(edge.get("from_node_id"), [])
        targets = labels.get(edge.get("to_node_id"), [])
        refs = edge.get("evidence_refs") or []
        states, seen = [], set()
        valid = (
            len(subjects) == len(targets) == 1
            and bool(subjects[0])
            and bool(targets[0])
            and bool(refs)
        )
        for ref in refs:
            span = ref.get("source_span_ref_id")
            text = spans.get(span)
            quotes = ref.get("anchor_quotes") or []
            if (
                span in seen
                or not isinstance(text, str)
                or not quotes
                or any(not isinstance(q, str) or not q or q not in text for q in quotes)
            ):
                valid = False
            seen.add(span)
            if valid:
                states.append(_proposition(text, subjects[0], targets[0]))
        if not valid:
            decision = "unresolved_support"
        elif "ownership_proposition" in states:
            decision = "ownership_proposition_present"
        elif states and all(state == "role_only" for state in states):
            decision = REASON
        else:
            decision = "unresolved_support"
        record = {"edge_id": edge["edge_id"], "decision": decision, "profile": PROFILE}
        if decision == REASON:
            record["raw_edge"] = deepcopy(edge)
            item_id = "deferred:role-support:" + edge["edge_id"]
            if any(
                item["item_id"] == item_id for item in result.get("deferred_items", [])
            ):
                raise ValueError("role-support disposition identity collision")
            result.setdefault("deferred_items", []).append(
                {
                    "item_id": item_id,
                    "label": edge.get("label") or "",
                    "reason": REASON,
                    "evidence_refs": deepcopy(refs),
                    "warnings": ["source_support_policy:" + PROFILE],
                    "suggested_next_step": "Review ownership support; the submitted source establishes a proprietor role.",
                }
            )
        else:
            kept.append(edge)
        records.append(record)
    result["edges"] = kept
    diagnostics["ownership_role_support"] = {"profile": PROFILE, "records": records}
    return result, diagnostics
