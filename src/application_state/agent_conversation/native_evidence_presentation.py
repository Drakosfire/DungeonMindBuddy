"""Lossless display of existing evidence; never an evidence producer or authority.

TSV cells are JSON values, so embedded tabs/newlines/quotes cannot change rows.
Field paths appear once in a header instead of once per nested record. Container
layouts are host-only readback evidence, never sent as model context.
"""
from copy import deepcopy
import json


def _json(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def _walk(value, path=()):
    if isinstance(value, dict) and value:
        children, leaves = [], {}
        for key, item in value.items():
            layout, cells = _walk(item, (*path, key))
            children.append([key, layout])
            leaves.update(cells)
        return {"object": children}, leaves
    if isinstance(value, list) and value:
        children, leaves = [], {}
        for index, item in enumerate(value):
            layout, cells = _walk(item, (*path, index))
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


def _table(title, rows):
    layouts, leaves, columns = [], [], []
    for row in rows:
        layout, cells = _walk(row)
        layouts.append(layout)
        leaves.append(cells)
        for path in cells:
            if path not in columns:
                columns.append(path)
    # Display citation handles before content, without changing record order.
    columns.sort(key=lambda path: (path not in {("assertion_handle",), ("qualification_handle",)},))
    header = _json([list(path) for path in columns])
    lines = [title, header]
    lines += ["\t".join(_json(cells[path]) if path in cells else "_" for path in columns) for cells in leaves]
    return "\n".join(lines), {"columns": [list(path) for path in columns], "layouts": layouts}


def restore_flat_native_evidence(text, proof):
    """Offline/owner readback check; not a product input or alternate producer."""
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
    state["qualifications"] = {row["qualification_handle"]: row["qualification"] for row in restored[1]}
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
    qualifications, qualification_proof = _table("QUALIFICATIONS — shared, referenced by original handle", [
        {"qualification_handle": key, "qualification": value} for key, value in assertions["qualifications"].items()])
    text = "\n\n".join([
        "EVIDENCE ENVELOPE (native_assertions follow below; all other fields unchanged)\n"
        "Table headers list original field paths in column order. Cells are JSON values separated by tabs. "
        "A bare _ means that field is absent, not false or null. Citation handles and qualifications retain their original meaning.", _json(envelope),
        "ASSERTION STATE (scope/completeness qualifiers; not universal absence)", _json(state), facts, qualifications])
    proof = {"tables": [fact_proof, qualification_proof], "envelope_keys": list(frame),
        "assertion_keys": list(assertions)}
    if _json(restore_flat_native_evidence(text, proof)) != _json(frame):
        raise ValueError("Flat presentation changed evidence")
    return text, proof
