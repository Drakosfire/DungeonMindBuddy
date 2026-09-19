from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from generationengine import GenerationClient, TextRequest
from pydantic import BaseModel

from src.ingestion.frontmatter import DocumentMetadata
from src.llm.generation_sync import run_awaitable_sync

_SCHEMA_NAME = "frontmatter_metadata_proposal"


class ProposedDocumentMetadata(BaseModel):
    title: str
    document_class: str
    canon_layer: str
    campaign_id: str | None = None
    temporal_scope: str
    session: int | None = None
    origin_session: int | None = None
    last_updated_session: int | None = None
    source_class: str


def _heuristic_document_class(path: Path, text: str) -> tuple[str, str, str | None, int | None]:
    lower_path = str(path).lower()
    lower_text = text.lower()

    if "longmont campaign" not in lower_path:
        return "world", "world", None, None

    campaign_id = "longmont-c1" if "campaign 1" in lower_path else "longmont-c2"

    if "session recap" in lower_text or "battle with the wolf" in lower_path:
        session = _infer_session_number(lower_text)
        return "play", "campaign", campaign_id, session
    if "session prep" in lower_path or "prep" in lower_text:
        session = _infer_session_number(lower_text)
        return "planning", "campaign", campaign_id, session
    return "reference", "campaign", campaign_id, None


def _infer_session_number(text: str) -> int | None:
    import re

    match = re.search(r"\bsession\s+(\d+)\b", text, flags=re.IGNORECASE)
    if match is None:
        return None
    return int(match.group(1))


def _source_class_for(document_class: str) -> str:
    if document_class == "world":
        return "seed_reference"
    if document_class == "play":
        return "observed_session_recap"
    if document_class == "planning":
        return "planning_document"
    return "ledger_or_dossier"


def _load_model_id() -> str:
    from src.model_policy import load_buddy_model_policy

    payload = load_buddy_model_policy(strict=True)
    if not payload:
        return "gpt-5.3-chat-latest"
    actions = payload.get("actions", {})
    models = payload.get("models", {})
    role = actions.get("structured_generation", "gpt-5.3-chat-latest")
    return str(models.get(role, role))


def infer_frontmatter_metadata_heuristic(path: Path, text: str) -> DocumentMetadata:
    document_class, canon_layer, campaign_id, session = _heuristic_document_class(path, text)
    title = path.stem.replace("_", " ").strip() or "Untitled Document"
    temporal_scope = "session_specific" if session is not None else "evergreen"
    origin_session = session
    last_updated_session = session
    if document_class == "reference" and session is None:
        temporal_scope = "campaign_stateful"
    if document_class == "world":
        temporal_scope = "evergreen"
        origin_session = None
        last_updated_session = None
    return DocumentMetadata(
        title=title,
        document_class=document_class,
        canon_layer=canon_layer,
        campaign_id=campaign_id,
        temporal_scope=temporal_scope,
        session=session,
        origin_session=origin_session,
        last_updated_session=last_updated_session,
        source_class=_source_class_for(document_class),
    )


def _frontmatter_inference_prompt(path: Path, text: str) -> str:
    return (
        "Infer frontmatter metadata for a markdown source document.\n"
        "Return JSON with keys: title, document_class, canon_layer, campaign_id, temporal_scope, session, origin_session, last_updated_session, source_class.\n"
        "Allowed document_class: world|play|planning|reference.\n"
        "Allowed canon_layer: world|campaign.\n"
        "Allowed temporal_scope: session_specific|campaign_stateful|evergreen.\n"
        "Allowed source_class: seed_reference|observed_session_recap|planning_document|ledger_or_dossier|other.\n"
        f"Path: {path}\n\n"
        f"Document excerpt:\n{text[:4000]}"
    )


class OpenAIFrontmatterInferenceClient:
    """Optional OpenAI-backed inference adapter for document metadata."""

    def __init__(self, *, client: Any | None = None) -> None:
        self._client = client

    def propose(self, *, model: str, path: Path, text: str) -> DocumentMetadata:
        request = TextRequest(
            user_prompt=_frontmatter_inference_prompt(path, text),
            provider="openai",
            model=model,
            temperature=None,
            json_schema=ProposedDocumentMetadata.model_json_schema(),
            schema_name=_SCHEMA_NAME,
        )
        result = run_awaitable_sync(lambda: self._generate_structured(request))
        parsed = getattr(result, "parsed", None)
        if parsed is None:
            raise ValueError("Frontmatter inference returned no parsed metadata.")
        if not isinstance(parsed, dict):
            raise ValueError(
                "Frontmatter inference parsed output must be an object, "
                f"got {type(parsed).__name__}"
            )
        payload = ProposedDocumentMetadata.model_validate(parsed).model_dump()
        return DocumentMetadata(
            title=payload["title"],
            document_class=payload["document_class"],
            canon_layer=payload["canon_layer"],
            campaign_id=payload["campaign_id"],
            temporal_scope=payload["temporal_scope"],
            session=payload["session"],
            origin_session=payload.get("origin_session"),
            last_updated_session=payload.get("last_updated_session"),
            source_class=payload["source_class"],
        )

    async def _generate_structured(self, request: TextRequest) -> Any:
        if self._client is not None:
            return await self._client.generate_structured(request)
        ge_client = GenerationClient.from_env()
        return await ge_client.generate_structured(request)


def infer_frontmatter_metadata(
    *,
    path: Path,
    text: str,
    model: str | None = None,
    openai_client: OpenAIFrontmatterInferenceClient | None = None,
) -> DocumentMetadata:
    if openai_client is None:
        return infer_frontmatter_metadata_heuristic(path, text)
    return openai_client.propose(model=model or _load_model_id(), path=path, text=text)


def metadata_preview(metadata: DocumentMetadata) -> str:
    return json.dumps(metadata.to_dict(), indent=2, ensure_ascii=False)
