"""Exact source witnesses, not an entailment judge or citation repair."""

from copy import deepcopy

POLICY = "exact_source_quote_binding_v1"
FORMAT = "build_working_draft_answer_v4"
KEY = "source_quote_binding_policy"
KINDS = {
    "SavedFact": ("saved_source_claim", "section_read_ids"),
    "PassageFact": ("source_passage_claim", "passage_handles"),
    "RelatedPageDraftClaim": ("related_page_claim", "read_id"),
}


def enabled(packet):
    value = packet.get(KEY)
    if KEY in packet and value != POLICY:
        raise ValueError("Unknown source quote binding policy")
    if (
        value == POLICY
        and packet.get("connected_page_review_policy")
        != "typed_connected_page_review_v1"
    ):
        raise ValueError("Quoted source output requires its frozen Build profile")
    return value == POLICY


def sources(packet):
    from .build_draft_context import resolve_body_aliases

    packet = resolve_body_aliases(packet)
    saved = {}
    rows = [
        *packet.get("exposure", {}).get("saved_sections", []),
        *packet.get("artifact_under_edit", {}).get("sections", []),
    ]
    for row in rows:
        key, body = str(row["read_id"]), row["text"]
        if key in saved and saved[key] != body:
            raise ValueError("Ambiguous saved source quote identity")
        saved[key] = body
    return {
        "saved_source_claim": saved,
        "source_passage_claim": {
            r["handle"]: r["text"] for r in packet.get("opened_passages", [])
        },
        "related_page_claim": {
            str(r["read_id"]): r["markdown"]
            for r in packet.get("related_authored_pages", {}).get("pages", [])
        },
    }


def augment(schema, packet):
    """The raw contract retains familiar claim kinds but requires source witnesses."""
    if not enabled(packet):
        return schema
    for name, (kind, selector) in KINDS.items():
        if name not in schema["$defs"]:
            continue
        definition = schema["$defs"][name]
        definition["properties"]["supporting_quotes"] = {
            "type": "array",
            "items": {"type": "string", "minLength": 1},
            "description": "Exact nonblank contiguous quotes, one per selected source in selector order. Copy from that source only; never from another page.",
        }
        definition["required"].append("supporting_quotes")
        labels = (
            "The current saved page only. Other authored pages require related_page_claim."
            if kind == "saved_source_claim"
            else "Opened World source passages only."
            if kind == "source_passage_claim"
            else "Separately read saved authored pages: "
            + "; ".join(
                str(r["read_id"]) + " = " + r["page"]["title"]
                for r in packet.get("related_authored_pages", {}).get("pages", [])
            )
        )
        definition["properties"][selector]["description"] = labels
    return schema


def validate_and_project(body, packet):
    """Verify exact producer input; never reselect, guess, or edit a citation."""
    if not enabled(packet):
        return body
    if not isinstance(body, dict) or not isinstance(body.get("answer_segments"), list):
        raise ValueError("Quoted source answer requires typed segments")
    projected = deepcopy(body)
    material = sources(packet)
    selectors = {kind: selector for kind, selector in KINDS.values()}
    for segment in projected["answer_segments"]:
        if not isinstance(segment, dict) or segment.get("kind") not in selectors:
            continue
        kind = segment["kind"]
        selected = segment.get(selectors[kind])
        selected = [selected] if kind == "related_page_claim" else selected
        quotes = segment.get("supporting_quotes")
        if (
            not isinstance(selected, list)
            or not selected
            or not isinstance(quotes, list)
            or len(selected) != len(quotes)
        ):
            raise ValueError(
                "Source claim requires one exact quote per selected source"
            )
        for identity, quote in zip(selected, quotes):
            text = material[kind].get(identity) if isinstance(identity, str) else None
            if (
                not isinstance(quote, str)
                or not quote.strip()
                or text is None
                or quote not in text
            ):
                raise ValueError(
                    "Source claim quote is absent from its selected source"
                )
        del segment["supporting_quotes"]
    return projected
