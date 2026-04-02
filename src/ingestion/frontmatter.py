from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from src.contracts.schema_validation import validate_instance


class FrontmatterError(ValueError):
    """Base error for frontmatter parsing/validation failures."""


class FrontmatterParseError(FrontmatterError):
    """Raised when a frontmatter block cannot be parsed."""


class FrontmatterValidationError(FrontmatterError):
    """Raised when parsed frontmatter fails schema validation."""


@dataclass(frozen=True)
class DocumentMetadata:
    title: str
    document_class: str
    canon_layer: str
    campaign_id: str | None
    temporal_scope: str
    session: int | None
    origin_session: int | None
    last_updated_session: int | None
    source_class: str

    def to_dict(self) -> dict[str, str | int | None]:
        return {
            "title": self.title,
            "document_class": self.document_class,
            "canon_layer": self.canon_layer,
            "campaign_id": self.campaign_id,
            "temporal_scope": self.temporal_scope,
            "session": self.session,
            "origin_session": self.origin_session,
            "last_updated_session": self.last_updated_session,
            "source_class": self.source_class,
        }


def _parse_scalar(raw: str) -> str | int | None:
    value = raw.strip()
    if value in {"", "null", "NULL", "None", "none", "~"}:
        return None
    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        return value[1:-1]
    if value.isdigit():
        return int(value)
    return value


def _parse_frontmatter_block(block: str) -> dict[str, str | int | None]:
    payload: dict[str, str | int | None] = {}
    for idx, line in enumerate(block.splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if ":" not in stripped:
            raise FrontmatterParseError(
                f"Invalid frontmatter line {idx}: expected 'key: value'."
            )
        key, raw_value = stripped.split(":", 1)
        key = key.strip()
        if not key:
            raise FrontmatterParseError(
                f"Invalid frontmatter line {idx}: empty key is not allowed."
            )
        payload[key] = _parse_scalar(raw_value)
    return payload


def _metadata_from_payload(payload: dict[str, str | int | None]) -> DocumentMetadata:
    try:
        validate_instance(payload, "document_metadata.schema.json")
    except Exception as exc:
        raise FrontmatterValidationError(str(exc)) from exc

    return DocumentMetadata(
        title=str(payload["title"]),
        document_class=str(payload["document_class"]),
        canon_layer=str(payload["canon_layer"]),
        campaign_id=(
            str(payload["campaign_id"]) if payload.get("campaign_id") is not None else None
        ),
        temporal_scope=str(payload["temporal_scope"]),
        session=int(payload["session"]) if payload.get("session") is not None else None,
        origin_session=(
            int(payload["origin_session"]) if payload.get("origin_session") is not None else None
        ),
        last_updated_session=(
            int(payload["last_updated_session"])
            if payload.get("last_updated_session") is not None
            else None
        ),
        source_class=str(payload["source_class"]),
    )


def split_frontmatter(markdown: str) -> tuple[str | None, str]:
    if not markdown.startswith("---\n"):
        return None, markdown

    lines = markdown.splitlines(keepends=True)
    if not lines:
        return None, markdown

    end_idx: int | None = None
    for idx in range(1, len(lines)):
        if lines[idx].strip() == "---":
            end_idx = idx
            break
    if end_idx is None:
        raise FrontmatterParseError("Frontmatter opening fence found without closing fence.")

    block = "".join(lines[1:end_idx]).strip()
    body = "".join(lines[end_idx + 1 :])
    return block, body


def parse_document_frontmatter(markdown: str) -> tuple[DocumentMetadata | None, str]:
    block, body = split_frontmatter(markdown)
    if block is None:
        return None, markdown

    payload = _parse_frontmatter_block(block)
    metadata = _metadata_from_payload(payload)
    return metadata, body


def load_document_frontmatter(path: Path) -> tuple[DocumentMetadata | None, str]:
    text = path.read_text(encoding="utf-8")
    return parse_document_frontmatter(text)


def render_frontmatter(metadata: DocumentMetadata) -> str:
    campaign_id = "null" if metadata.campaign_id is None else metadata.campaign_id
    session = "null" if metadata.session is None else str(metadata.session)
    origin_session = "null" if metadata.origin_session is None else str(metadata.origin_session)
    last_updated_session = (
        "null" if metadata.last_updated_session is None else str(metadata.last_updated_session)
    )
    return (
        "---\n"
        f'title: "{metadata.title}"\n'
        f"document_class: {metadata.document_class}\n"
        f"canon_layer: {metadata.canon_layer}\n"
        f"campaign_id: {campaign_id}\n"
        f"temporal_scope: {metadata.temporal_scope}\n"
        f"session: {session}\n"
        f"origin_session: {origin_session}\n"
        f"last_updated_session: {last_updated_session}\n"
        f"source_class: {metadata.source_class}\n"
        "---\n"
    )


def write_document_with_frontmatter(
    path: Path, *, metadata: DocumentMetadata, body: str
) -> None:
    rendered = render_frontmatter(metadata)
    if body.startswith("\n"):
        path.write_text(f"{rendered}{body}", encoding="utf-8")
        return
    path.write_text(f"{rendered}\n{body}", encoding="utf-8")
