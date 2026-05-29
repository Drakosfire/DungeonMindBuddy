from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PIPE_ROW_RE = re.compile(r"^\|\s*(\d+)\s*\|(.+)$")
BAND_HEADER_RE = re.compile(r"^##\s*(\d+)\s*[–-]\s*(\d+)")


@dataclass(frozen=True)
class RollTableRef:
    table_id: str
    title: str
    dice: str
    source_path: str
    status: str
    default_latency_mode: str | None = None


@dataclass(frozen=True)
class ParsedRollTable:
    ref: RollTableRef
    shape: str  # "pipe" | "band"
    pipe_rows: dict[int, str]
    band_sections: dict[tuple[int, int], list[str]]


def dice_maximum(dice: str) -> int:
    match = re.search(r"d(\d+)", dice.lower())
    if not match:
        raise ValueError(f"unsupported dice notation: {dice}")
    return int(match.group(1))


def build_roll_table_refs(packet: dict[str, Any]) -> list[RollTableRef]:
    refs: list[RollTableRef] = []
    for row in packet.get("known_roll_tables", []):
        refs.append(
            RollTableRef(
                table_id=row["table_id"],
                title=row["title"],
                dice=row["dice"],
                source_path=row["source_path"],
                status=row.get("status", "pending"),
                default_latency_mode=row.get("default_latency_mode"),
            )
        )
    return refs


def _parse_pipe_rows(text: str) -> dict[int, str]:
    rows: dict[int, str] = {}
    for line in text.splitlines():
        match = PIPE_ROW_RE.match(line.strip())
        if not match:
            continue
        roll = int(match.group(1))
        row_text = match.group(2).strip()
        if row_text.endswith("|"):
            row_text = row_text[:-1].rstrip()
        rows[roll] = row_text
    return rows


def _parse_band_sections(text: str) -> dict[tuple[int, int], list[str]]:
    sections: dict[tuple[int, int], list[str]] = {}
    current_key: tuple[int, int] | None = None
    current_items: list[str] = []

    def flush() -> None:
        nonlocal current_key, current_items
        if current_key is not None and current_items:
            sections[current_key] = current_items
        current_key = None
        current_items = []

    for line in text.splitlines():
        header = BAND_HEADER_RE.match(line.strip())
        if header:
            flush()
            current_key = (int(header.group(1)), int(header.group(2)))
            continue
        if current_key is None:
            continue
        stripped = line.strip()
        if not stripped or stripped.startswith("|") or stripped.startswith("#"):
            continue
        current_items.append(stripped)
    flush()
    return sections


def parse_roll_table_text(ref: RollTableRef, text: str) -> ParsedRollTable:
    pipe_rows = _parse_pipe_rows(text)
    if pipe_rows:
        return ParsedRollTable(ref=ref, shape="pipe", pipe_rows=pipe_rows, band_sections={})
    band_sections = _parse_band_sections(text)
    if band_sections:
        return ParsedRollTable(ref=ref, shape="band", pipe_rows={}, band_sections=band_sections)
    raise ValueError(f"unsupported roll table shape for {ref.table_id} at {ref.source_path}")


def load_parsed_table(ref: RollTableRef, root: Path) -> ParsedRollTable:
    path = root / ref.source_path
    if not path.is_file():
        raise FileNotFoundError(f"roll table source missing: {ref.source_path}")
    text = path.read_text(encoding="utf-8")
    return parse_roll_table_text(ref, text)


class RollTableRegistry:
    def __init__(self, tables: dict[str, ParsedRollTable]) -> None:
        self._tables = tables

    @classmethod
    def from_packet(cls, packet: dict[str, Any], root: Path) -> RollTableRegistry:
        tables: dict[str, ParsedRollTable] = {}
        for ref in build_roll_table_refs(packet):
            tables[ref.table_id] = load_parsed_table(ref, root)
        return cls(tables)

    def get_ref(self, table_id: str) -> RollTableRef:
        return self._tables[table_id].ref

    def has_table(self, table_id: str) -> bool:
        return table_id in self._tables

    def resolve_row(self, table_id: str, roll: int) -> tuple[str, str]:
        """Return (row_text, row_locator)."""
        parsed = self._tables[table_id]
        maximum = dice_maximum(parsed.ref.dice)
        if roll < 1 or roll > maximum:
            raise ValueError(f"roll {roll} out of range for {table_id} ({parsed.ref.dice})")

        if parsed.shape == "pipe":
            row_text = parsed.pipe_rows.get(roll)
            if row_text is None:
                raise ValueError(f"no pipe row for {table_id} roll {roll}")
            return row_text, f"pipe_row:{parsed.ref.dice}={roll}"

        for (low, high), items in parsed.band_sections.items():
            if low <= roll <= high:
                index = roll - low
                if index >= len(items):
                    raise ValueError(
                        f"roll {roll} maps to band {low}-{high} but only {len(items)} items exist"
                    )
                return items[index], f"band:{low}-{high}:item={roll}"
        raise ValueError(f"roll {roll} does not fall in any band for {table_id}")
