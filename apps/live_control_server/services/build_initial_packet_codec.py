"""Lossless model-readable initial navigation packet, never new evidence authority."""

from __future__ import annotations

from collections import Counter
from copy import deepcopy
import json
import math

CODEC = "dmb_build_initial_packet_table_v1"
INTERPRETATION = (
    "Read each table row under its named columns, in order. Presence bit 0 means absent, "
    "not null. References [row,column,shared_index] replace null cells with the exact "
    "shared_values entry. Packet fields and decoded tables form the original navigation "
    "packet; qualifications remain attached. This is not additional source evidence."
)
TABLES = {"candidates", "claimLedger"}
MAX_WIRE_BYTES = 64000
MAX_DECODED_BYTES = 256000
MAX_ROWS = 64
MAX_COLUMNS = 128
MAX_SHARED = 256


def _validate_json(value):
    stack, count = [(value, 0)], 0
    while stack:
        item, depth = stack.pop()
        count += 1
        if depth > 32 or count > 32768:
            raise ValueError("Initial packet JSON exceeds depth/item bound")
        if isinstance(item, dict):
            if len(item) > 32768 or not all(isinstance(k, str) for k in item):
                raise ValueError("Initial packet object keys differ")
            stack.extend((v, depth + 1) for v in item.values())
        elif isinstance(item, list):
            if len(item) > 32768:
                raise ValueError("Initial packet array exceeds bound")
            stack.extend((v, depth + 1) for v in item)
        elif type(item) is float:
            if not math.isfinite(item):
                raise ValueError("Non-finite initial packet value")
        elif item is not None and type(item) not in {str, int, bool}:
            raise ValueError("Initial packet requires JSON values")


def canonical(value):
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _nodes(value):
    if isinstance(value, dict):
        return 1 + sum(_nodes(v) for v in value.values())
    if isinstance(value, list):
        return 1 + sum(_nodes(v) for v in value)
    return 0


def encode(packet: dict) -> dict:
    _validate_json(packet)
    if (
        not isinstance(packet, dict)
        or len(canonical(packet).encode()) > MAX_DECODED_BYTES
    ):
        raise ValueError("Initial packet exceeds bounded codec input")
    tables = {key: packet[key] for key in packet if key in TABLES}
    if any(
        not isinstance(rows, list)
        or len(rows) > MAX_ROWS
        or any(not isinstance(row, dict) for row in rows)
        for rows in tables.values()
    ):
        raise ValueError("Initial packet table shape differs")
    counts = Counter(
        canonical(value)
        for rows in tables.values()
        for row in rows
        for value in row.values()
    )
    shared_keys = []
    for key, count in sorted(counts.items()):
        cost = len(key.encode()) + 64 * _nodes(json.loads(key))
        if count > 1 and (count - 1) * cost > 80 * count + 128:
            shared_keys.append(key)
    if len(shared_keys) > MAX_SHARED:
        raise ValueError("Initial shared dictionary exceeds bound")
    shared_index = {key: index for index, key in enumerate(shared_keys)}
    result = dict(
        schema=CODEC,
        interpretation=INTERPRETATION,
        packet_fields={k: deepcopy(v) for k, v in packet.items() if k not in TABLES},
        field_order=list(packet),
        shared_values=[json.loads(key) for key in shared_keys],
        tables={},
    )
    for key, source_rows in tables.items():
        columns = sorted({column for row in source_rows for column in row})
        if len(columns) > MAX_COLUMNS or not all(isinstance(c, str) for c in columns):
            raise ValueError("Initial packet columns exceed bound")
        rows, presence, references = [], [], []
        for row_index, source in enumerate(source_rows):
            values = []
            presence.append(
                "".join("1" if column in source else "0" for column in columns)
            )
            for column_index, column in enumerate(columns):
                value = source.get(column)
                ref = shared_index.get(canonical(value)) if column in source else None
                values.append(None if ref is not None else deepcopy(value))
                if ref is not None:
                    references.append([row_index, column_index, ref])
            rows.append(values)
        result["tables"][key] = dict(
            columns=columns, rows=rows, presence=presence, references=references
        )
    if decode(result) != packet:
        raise ValueError("Initial packet codec did not round trip exactly")
    return result


def decode(payload: dict) -> dict:
    _validate_json(payload)
    if (
        not isinstance(payload, dict)
        or set(payload)
        != {
            "schema",
            "interpretation",
            "packet_fields",
            "field_order",
            "shared_values",
            "tables",
        }
        or payload["schema"] != CODEC
        or payload["interpretation"] != INTERPRETATION
        or len(canonical(payload).encode()) > MAX_WIRE_BYTES
    ):
        raise ValueError("Unknown or oversized initial packet codec")
    fields, tables, shared, order = (
        payload[k] for k in ("packet_fields", "tables", "shared_values", "field_order")
    )
    if (
        not isinstance(fields, dict)
        or not isinstance(tables, dict)
        or not set(tables) <= TABLES
        or set(fields) & TABLES
        or not isinstance(shared, list)
        or len(shared) > MAX_SHARED
        or not isinstance(order, list)
        or not all(isinstance(k, str) for k in order)
        or len(order) != len(set(order))
        or set(order) != set(fields) | set(tables)
    ):
        raise ValueError("Initial packet dictionary or field identity differs")
    costs = [len(canonical(value).encode()) for value in shared]
    expanded_bytes = len(canonical(fields).encode())
    decoded, used = deepcopy(fields), set()
    for name, table in tables.items():
        if not isinstance(table, dict) or set(table) != {
            "columns",
            "rows",
            "presence",
            "references",
        }:
            raise ValueError("Initial packet table schema differs")
        columns, rows, presence, refs = (
            table[k] for k in ("columns", "rows", "presence", "references")
        )
        if (
            not isinstance(columns, list)
            or len(columns) > MAX_COLUMNS
            or not all(isinstance(c, str) for c in columns)
            or columns != sorted(set(columns))
            or not isinstance(rows, list)
            or len(rows) > MAX_ROWS
            or not isinstance(presence, list)
            or len(presence) != len(rows)
            or not isinstance(refs, list)
            or len(refs) > MAX_ROWS * MAX_COLUMNS
        ):
            raise ValueError("Initial packet rows or columns differ")
        references = {}
        for ref in refs:
            if (
                not isinstance(ref, list)
                or len(ref) != 3
                or not all(type(i) is int for i in ref)
            ):
                raise ValueError("Malformed initial packet reference")
            row, column, index = ref
            if (
                not 0 <= row < len(rows)
                or not 0 <= column < len(columns)
                or not 0 <= index < len(shared)
                or (row, column) in references
            ):
                raise ValueError("Unknown or duplicate initial packet reference")
            references[row, column] = index
        output = []
        for ri, (row, mask) in enumerate(zip(rows, presence, strict=True)):
            if (
                not isinstance(row, list)
                or len(row) != len(columns)
                or not isinstance(mask, str)
                or len(mask) != len(columns)
                or any(bit not in "01" for bit in mask)
            ):
                raise ValueError("Initial packet row width or presence differs")
            item = {}
            for ci, column in enumerate(columns):
                ref = references.get((ri, ci))
                if mask[ci] == "0":
                    if row[ci] is not None or ref is not None:
                        raise ValueError("Absent initial packet cell has content")
                    continue
                if ref is not None:
                    if row[ci] is not None:
                        raise ValueError(
                            "Referenced initial packet cell has inline content"
                        )
                    value, size = shared[ref], costs[ref]
                    used.add(ref)
                else:
                    value, size = row[ci], len(canonical(row[ci]).encode())
                expanded_bytes += size + len(canonical(column).encode()) + 2
                if expanded_bytes > MAX_DECODED_BYTES:
                    raise ValueError("Initial packet expansion exceeds bound")
                item[column] = deepcopy(value)
            output.append(item)
        decoded[name] = output
    if used != set(range(len(shared))):
        raise ValueError("Unused initial packet dictionary values")
    result = {key: decoded[key] for key in order}
    if len(canonical(result).encode()) > MAX_DECODED_BYTES:
        raise ValueError("Initial packet expansion exceeds bound")
    return result
