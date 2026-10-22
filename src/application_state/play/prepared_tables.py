"""Explicit prepared-table grammar. No inference from ordinary Markdown tables."""
from __future__ import annotations

import hashlib
import json
import re
from markdown_it import MarkdownIt
from src.ingestion.frontmatter import split_frontmatter
from pydantic import BaseModel, ConfigDict, Field, StrictInt, field_validator, model_validator

LANGUAGE = "dmb-roll-table-v1"


class TableRow(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    row_id: str = Field(pattern=r"^row:[a-z0-9][a-z0-9._-]{0,127}$")
    min: StrictInt
    max: StrictInt
    outcome: str

    @field_validator("outcome")
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError("Outcome must not be blank")
        return value


class PreparedTable(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    schema_version: str
    table_id: str = Field(pattern=r"^table:[a-z0-9][a-z0-9._-]{0,127}$")
    title: str
    die_sides: StrictInt = Field(ge=2, le=9007199254740991)
    rows: list[TableRow]

    @model_validator(mode="after")
    def coherent(self):
        if self.schema_version != "dmb_roll_table_v1" or not self.title.strip():
            raise ValueError("Unsupported table version or blank title")
        next_value = 1
        ids = set()
        for row in self.rows:
            if row.row_id in ids or row.min != next_value or row.max < row.min or row.max > self.die_sides:
                raise ValueError("Rows must have unique IDs and cover the die exactly in ascending order")
            ids.add(row.row_id)
            next_value = row.max + 1
        if next_value != self.die_sides + 1:
            raise ValueError("Rows must cover the whole die")
        return self

    @property
    def content_sha256(self):
        return hashlib.sha256(json.dumps(self.model_dump(), sort_keys=True, ensure_ascii=False,
                                         separators=(",", ":")).encode("utf-8")).hexdigest()

    def resolve(self, value: int) -> TableRow:
        if type(value) is not int or not 1 <= value <= self.die_sides:
            raise ValueError("Physical roll must be an integer within the die range")
        return next(row for row in self.rows if row.min <= value <= row.max)


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def parse_table_json(value: str) -> PreparedTable:
    return PreparedTable.model_validate(json.loads(value, object_pairs_hook=_unique_object,
                                                  parse_constant=lambda _: (_ for _ in ()).throw(ValueError("Non-JSON number"))))


def read_prepared_tables(markdown: str) -> list[PreparedTable]:
    """Top-level fences only; an outer generic fence shields every inner example."""
    _, body = split_frontmatter(markdown)
    tables = []
    seen = set()
    lines = body.splitlines()
    for token in MarkdownIt("commonmark").parse(body):
        if token.type != "fence" or token.level != 0 or token.info.strip() != LANGUAGE:
            continue
        # CommonMark accepts an unclosed fence through EOF. Typed blocks do not.
        first, end = token.map
        closing = lines[end - 1] if end > first + 1 else ""
        if not re.fullmatch(r" {0,3}" + re.escape(token.markup[0]) + "{" + str(len(token.markup)) + r",}[ \t]*", closing):
            raise ValueError("Unterminated prepared-table fence")
        table = parse_table_json(token.content)
        if table.table_id in seen:
            raise ValueError("Duplicate table ID in source")
        seen.add(table.table_id)
        tables.append(table)
    return tables
