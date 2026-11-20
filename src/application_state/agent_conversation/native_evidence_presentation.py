"""Lossless display of existing evidence; never an evidence producer or authority.

TSV cells are JSON values, so embedded tabs/newlines/quotes cannot change rows.
Field paths appear once in a header instead of once per nested record. Container
layouts are host-only readback evidence, never sent as model context.
"""
from copy import deepcopy
from hashlib import sha256
import json


def _json(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def reviewed_qualification_frame(frame, review):
    """Apply explicit reviewed data separation, never discover/scrub prose.

    Diagnostic presentation only. Original APP bindings remain about the original
    frame. Review classifications are human evidence, not machine-proven semantic
    correctness or a new publication/citation authority.
    """
    def fingerprint(value):
        return sha256(_json(value).encode()).hexdigest()
    if (not isinstance(review, dict)
            or set(review) != {"schema", "reviewer", "source_frame_sha256", "records"}
            or review["schema"] != "dmb_reviewed_qualification_parts_v1"
            or not isinstance(review["reviewer"], str) or not review["reviewer"].strip()
            or review["source_frame_sha256"] != fingerprint(frame)
            or not isinstance(review["records"], list)):
        raise ValueError("Invalid or misbound qualification review")
    result = deepcopy(frame)
    slots = {}
    for handle, qualification in result["native_assertions"]["qualifications"].items():
        for index, entry in enumerate(qualification.get("domain_metadata", [])):
            context = entry.get("world_context") if isinstance(entry, dict) else None
            if isinstance(context, dict) and "source_qualification" in context:
                if not isinstance(context["source_qualification"], str):
                    raise ValueError("Qualification review requires literal text slots")
                slots[handle, index] = context
    seen = set()
    for record in review["records"]:
        if (not isinstance(record, dict)
                or set(record) != {"qualification_handle", "domain_index", "original_sha256", "parts"}
                or not isinstance(record["qualification_handle"], str)
                or type(record["domain_index"]) is not int
                or not isinstance(record["parts"], list) or not record["parts"]):
            raise ValueError("Invalid qualification review record")
        key = record["qualification_handle"], record["domain_index"]
        if key not in slots or key in seen:
            raise ValueError("Unknown or duplicated qualification review slot")
        seen.add(key)
        parts = record["parts"]
        if any(not isinstance(p, dict) or set(p) != {"role", "text"}
               or not isinstance(p["role"], str) or p["role"] not in {"meaning", "host_audit"}
               or not isinstance(p["text"], str) or not p["text"] for p in parts):
            raise ValueError("Unresolved or invalid qualification classification")
        original = slots[key]["source_qualification"]
        if ("".join(p["text"] for p in parts) != original
                or sha256(original.encode()).hexdigest() != record["original_sha256"]):
            raise ValueError("Qualification parts do not reconstruct original bytes")
        meaning = "".join(p["text"] for p in parts if p["role"] == "meaning")
        if not meaning.strip():
            raise ValueError("Qualification review cannot erase all meaning")
        slots[key]["source_qualification"] = meaning
    if seen != set(slots):
        raise ValueError("Qualification review does not cover every source qualification")
    return result, {"original_frame_sha256": fingerprint(frame),
                    "presented_frame_sha256": fingerprint(result),
                    "review_sha256": fingerprint(review),
                    "scope": "reviewed diagnostic presentation; original APP authority unchanged"}


def _walk(value, path=(), *, atomic=()):
    if path in atomic:
        return {"cell": list(path)}, {path: value}
    if isinstance(value, dict) and value:
        children, leaves = [], {}
        for key, item in value.items():
            layout, cells = _walk(item, (*path, key), atomic=atomic)
            children.append([key, layout])
            leaves.update(cells)
        return {"object": children}, leaves
    if isinstance(value, list) and value:
        children, leaves = [], {}
        for index, item in enumerate(value):
            layout, cells = _walk(item, (*path, index), atomic=atomic)
            children.append(layout)
            leaves.update(cells)
        return {"array": children}, leaves
    return {"cell": list(path)}, {path: value}


def _restore(layout, cells):
    if "object" in layout:
        return {key: _restore(child, cells) for key, child in layout["object"]}
    if "array" in layout:
        return [_restore(child, cells) for child in layout["array"]]
    return cells[tuple(layout["cell"])]


def _table(title, rows, *, atomic=()):
    layouts, leaves, columns = [], [], []
    for row in rows:
        layout, cells = _walk(row, atomic=atomic)
        layouts.append(layout)
        leaves.append(cells)
        for path in cells:
            if path not in columns:
                columns.append(path)
    # Display citation handles before content, without changing record order.
    columns.sort(key=lambda path: (path not in {("assertion_handle",), ("qualification_handles",)},))
    header = _json([list(path) for path in columns])
    lines = [title, header]
    lines += ["\t".join(_json(cells[path]) if path in cells else "_" for path in columns) for cells in leaves]
    return "\n".join(lines), {"columns": [list(path) for path in columns], "layouts": layouts}


def restore_flat_native_evidence(text, proof):
    """Offline/owner readback check; not a product input or alternate producer."""
    if proof.get("schema") != "flat_native_assertions_v2":
        raise ValueError("Read historical flat artifacts with their pinned renderer")
    sections = text.split("\n\n")
    envelope = json.loads(sections[1])
    state = json.loads(sections[3])
    restored = []
    for section, table in zip(sections[4:], proof["tables"], strict=True):
        lines = section.split("\n")
        columns = [tuple(path) for path in json.loads(lines[1])]
        if columns != [tuple(path) for path in table["columns"]]:
            raise ValueError("Flat evidence header differs")
        rows = []
        for line, layout in zip(lines[2:], table["layouts"], strict=True):
            raw = line.split("\t") if columns else []
            if len(raw) != len(columns):
                raise ValueError("Flat evidence row width differs")
            cells = {path: json.loads(cell) for path, cell in zip(columns, raw, strict=True) if cell != "_"}
            rows.append(_restore(layout, cells))
        restored.append(rows)
    state["assertions"] = restored[0]
    definitions = {}
    for row in restored[1]:
        handles = row["qualification_handles"]
        if not isinstance(handles, list) or not handles or any(not isinstance(h, str) for h in handles):
            raise ValueError("Invalid shared qualification handles")
        for handle in handles:
            if handle in definitions:
                raise ValueError("Duplicate shared qualification handle")
            definitions[handle] = deepcopy(row["qualification"])
    if set(definitions) != set(proof["qualification_keys"]):
        raise ValueError("Shared qualification handles differ")
    state["qualifications"] = {key: definitions[key] for key in proof["qualification_keys"]}
    state = {key: state[key] for key in proof["assertion_keys"]}
    envelope["native_assertions"] = state
    return {key: envelope[key] for key in proof["envelope_keys"]}


def flat_native_evidence(frame):
    """Return model text and host-only proof, preserving the full input tree."""
    envelope = deepcopy(frame)
    assertions = envelope.pop("native_assertions")
    if not isinstance(assertions, dict) or not isinstance(assertions["assertions"], list) or not isinstance(assertions["qualifications"], dict):
        raise ValueError("Flat presentation requires native assertion records")
    state = {key: value for key, value in assertions.items() if key not in {"assertions", "qualifications"}}
    facts, fact_proof = _table("FACTS — one row per original assertion", assertions["assertions"])
    groups = {}
    for handle, value in assertions["qualifications"].items():
        # Byte equality includes value types and object order. Do not normalize,
        # compare prose similarity, or infer equivalent source restrictions.
        group = groups.setdefault(_json(value), {"qualification_handles": [], "qualification": value})
        group["qualification_handles"].append(handle)
    qualifications, qualification_proof = _table(
        "QUALIFICATIONS — every listed original handle names the complete value in its row",
        list(groups.values()), atomic={("qualification_handles",)})
    text = "\n\n".join([
        "EVIDENCE ENVELOPE (native_assertions follow below; all other fields unchanged)\n"
        "Table headers list original field paths in column order. Cells are JSON values separated by tabs. "
        "A bare _ means that field is absent, not false or null. Citation handles and qualifications retain their original meaning.", _json(envelope),
        "ASSERTION STATE (scope/completeness qualifiers; not universal absence)", _json(state), facts, qualifications])
    proof = {"schema": "flat_native_assertions_v2", "tables": [fact_proof, qualification_proof],
        "envelope_keys": list(frame), "assertion_keys": list(assertions),
        "qualification_keys": list(assertions["qualifications"])}
    if _json(restore_flat_native_evidence(text, proof)) != _json(frame):
        raise ValueError("Flat presentation changed evidence")
    return text, proof
