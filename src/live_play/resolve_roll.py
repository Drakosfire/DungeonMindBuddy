from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.live_play.roll_table_registry import RollTableRegistry

TABLE_ALIASES = {
    "weather": "T-WX",
    "r5": "R5",
}

WEATHER_ROLL_RE = re.compile(r"^Weather\s+(\d+)\.?\s*$", re.IGNORECASE)
R5_ROLL_RE = re.compile(r"^R5\s+(\d+)\.?\s*$", re.IGNORECASE)
TABLE_ROLL_RE = re.compile(r"^(T-[A-Z0-9-]+|R\d+)\s+(\d+)\.?\s*$", re.IGNORECASE)


@dataclass(frozen=True)
class ResolvedRoll:
    table_id: str
    roll: int
    title: str
    row_text: str
    source_path: str
    row_locator: str
    provenance: dict[str, object]


@dataclass(frozen=True)
class RollResolveDiagnostic:
    code: str
    message: str


class RollResolveError(Exception):
    def __init__(self, diagnostic: RollResolveDiagnostic) -> None:
        super().__init__(diagnostic.message)
        self.diagnostic = diagnostic


def parse_roll_command(text: str) -> tuple[str, int]:
    stripped = text.strip()
    match = WEATHER_ROLL_RE.match(stripped)
    if match:
        return "T-WX", int(match.group(1))
    match = R5_ROLL_RE.match(stripped)
    if match:
        return "R5", int(match.group(1))
    match = TABLE_ROLL_RE.match(stripped)
    if match:
        return match.group(1).upper(), int(match.group(2))
    raise RollResolveError(
        RollResolveDiagnostic(code="unparseable_command", message=f"cannot parse roll command: {text!r}")
    )


def resolve_roll_command(
    registry: RollTableRegistry,
    text: str,
) -> ResolvedRoll:
    try:
        table_id, roll = parse_roll_command(text)
    except RollResolveError:
        raise
    if not registry.has_table(table_id):
        raise RollResolveError(
            RollResolveDiagnostic(code="unknown_table", message=f"unknown table id: {table_id}")
        )
    ref = registry.get_ref(table_id)
    try:
        row_text, row_locator = registry.resolve_row(table_id, roll)
    except ValueError as exc:
        raise RollResolveError(
            RollResolveDiagnostic(code="resolve_failed", message=str(exc))
        ) from exc
    return ResolvedRoll(
        table_id=table_id,
        roll=roll,
        title=ref.title,
        row_text=row_text,
        source_path=ref.source_path,
        row_locator=row_locator,
        provenance={
            "source_paths": [
                {
                    "path": ref.source_path,
                    "role": "roll_table",
                    "notes": row_locator,
                }
            ],
            "generated_by": "resolve_roll",
            "notes": None,
        },
    )


def resolve_roll_from_packet(
    packet: dict[str, Any],
    text: str,
    *,
    root: Path,
) -> ResolvedRoll:
    registry = RollTableRegistry.from_packet(packet, root)
    return resolve_roll_command(registry, text)
