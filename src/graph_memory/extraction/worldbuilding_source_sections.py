"""Retain explicitly owned numbered source sections without model paraphrase."""

from copy import deepcopy
from hashlib import sha256
import json
import re
from typing import Any


class SourceSectionRetentionError(ValueError):
    """A recognized source layout cannot be retained without ambiguity."""


def owned_livestock_sections(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return exact source spans and names for recognized owned livestock sections.

    This is metadata for a versioned profile postprocessor. It deliberately
    shares the section-boundary rules used by ``retain_owned_sections`` so a
    classifier cannot silently drift from the text-retention boundary.
    """
    previous_end = 0
    refs = set()
    for row in rows:
        if (row["line_start"] <= previous_end or row["line_end"] < row["line_start"]
                or row["source_span_ref_id"] in refs):
            raise SourceSectionRetentionError("invalid source span ordering or identity")
        previous_end = row["line_end"]
        refs.add(row["source_span_ref_id"])

    sections = []
    for owner in rows:
        match = re.fullmatch(r"####\s+Fantastic Livestock for (?:the\s+)?(.+)",
                             owner["text"], flags=re.I)
        if not match:
            continue
        following = [row for row in rows if row["line_start"] > owner["line_end"]]
        end = next((row["line_start"] for row in following
                    if (re.match(r"^#{1,3}\s+", row["text"])
                        or (re.match(r"^####\s+", row["text"])
                            and not re.match(r"^####\s+\d+\.\s+", row["text"])))
                    and not re.fullmatch(r"##\s+(?:Animal Products and Uses|Cultural Significance):?",
                                         row["text"], flags=re.I)), None)
        if end is None:
            raise SourceSectionRetentionError("unbounded source owner section")
        selected = [row for row in following if row["line_start"] < end]
        headers = [row for row in selected if re.match(r"^####\s+\d+\.\s+", row["text"])]
        numbers = [int(re.match(r"^####\s+(\d+)\.", row["text"]).group(1))
                   for row in headers]
        if not numbers or numbers != list(range(1, len(numbers) + 1)):
            raise SourceSectionRetentionError("unsupported numbered source sequence")
        sections.append({
            "owner_label": match.group(1).strip(),
            "owner_span_ref_id": owner["source_span_ref_id"],
            "species_labels": [re.sub(r"^####\s+\d+\.\s+", "", row["text"]).strip()
                               for row in headers],
            "source_span_ref_ids": [row["source_span_ref_id"]
                                    for row in [owner, *selected]],
        })
    return sections



def owned_livestock_definitions(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Describe individual source definitions without creating Graph identities.

    Shared owner/preamble text is part of each definition's evidence, preserving
    qualifiers that apply to the whole group. This is a source-boundary record,
    not an accepted candidate or permission to publish an observation.
    """
    sections = owned_livestock_sections(rows)
    by_ref = {row["source_span_ref_id"]: row for row in rows}
    definitions = []
    for section in sections:
        selected = [by_ref[ref] for ref in section["source_span_ref_ids"]]
        starts = [index for index, row in enumerate(selected)
                  if re.match(r"^####\s+\d+\.\s+", row["text"])]
        shared = selected[:starts[0]]
        for number, start in enumerate(starts):
            end = starts[number + 1] if number + 1 < len(starts) else len(selected)
            body = selected[start:end]
            # A heading alone carries a name, not a source definition.
            if not any(row["text"].strip() and not re.match(r"^#{1,6}\s+", row["text"])
                       for row in body[1:]):
                raise SourceSectionRetentionError("source definition has no body")
            evidence = [*shared, *body]
            title = re.sub(r"^####\s+\d+\.\s+", "", body[0]["text"]).strip()
            payload = {
                "schema": "dmb_source_definition_v1",
                "owner_label": section["owner_label"],
                "owner_span_ref_id": section["owner_span_ref_id"],
                "title": title,
                "definition_span_ref_id": body[0]["source_span_ref_id"],
                "description": "\n\n".join(row["text"] for row in evidence),
                "source_span_ref_ids": [row["source_span_ref_id"] for row in evidence],
            }
            digest = sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False,
                                       separators=(",", ":")).encode("utf-8")).hexdigest()
            definitions.append({"definition_id": f"source-definition:{digest}", **payload})
    return definitions


def retain_owned_sections(
    graph: dict[str, Any], rows: list[dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    result = deepcopy(graph)
    retained = []
    section_records = owned_livestock_sections(rows)
    for section in section_records:
        label = section["owner_label"].casefold()
        targets = [node for node in result.get("nodes", [])
                   if node.get("node_type") == "location"
                   and str(node.get("label", "")).removeprefix("The ").casefold() == label]
        if len(targets) != 1:
            raise SourceSectionRetentionError("source owner has no unique place candidate")
        target = targets[0]
        evidence = [row for row in rows
                    if row["source_span_ref_id"] in set(section["source_span_ref_ids"])]
        prose = "\n\n".join(row["text"] for row in evidence)
        original = str(target.get("description") or "").strip()
        target["description"] = (original if prose in original
                                 else original + ("\n\n" if original else "") + prose)
        existing = {ref["source_span_ref_id"] for ref in target.get("evidence_refs", [])}
        target.setdefault("evidence_refs", []).extend(
            {"source_span_ref_id": row["source_span_ref_id"], "anchor_quotes": [row["text"]]}
            for row in evidence if row["source_span_ref_id"] not in existing
        )
        retained.append({"candidate_id": target["node_id"],
                         "owner_span_ref_id": section["owner_span_ref_id"],
                         "subsections": len(section["species_labels"]), "source_spans": len(evidence),
                         "derivation": "verbatim-source-sections"})
    return result, {"enabled": True, "retained_sections": retained}
