from __future__ import annotations

import hashlib
import json
from typing import Any, get_args

from src.contracts.entity_taxonomy import ALLOWED_SUBTYPE_FACETS, EntityClass
from src.ingestion import entity_extractor, fact_extractor


def _stable_sha256(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode(
        "utf-8"
    )
    return hashlib.sha256(encoded).hexdigest()


def compute_taxonomy_hash() -> str:
    payload = {
        "entity_classes": sorted(get_args(EntityClass)),
        "allowed_subtype_facets": sorted(ALLOWED_SUBTYPE_FACETS),
    }
    return _stable_sha256(payload)


def compute_heuristic_blocklist_hash() -> str:
    payload = {
        "junk_entity_exact": sorted(getattr(entity_extractor, "_JUNK_ENTITY_EXACT", set())),
        "junk_entity_prefixes": sorted(getattr(entity_extractor, "_JUNK_ENTITY_PREFIXES", tuple())),
        "low_signal_single_tokens": sorted(getattr(entity_extractor, "_LOW_SIGNAL_SINGLE_TOKENS", set())),
        "low_signal_phrases": sorted(getattr(entity_extractor, "_LOW_SIGNAL_PHRASES", set())),
    }
    return _stable_sha256(payload)


def compute_pipeline_contract(
    *,
    store_sha256: str,
    corpus_source_sha256: str,
    entity_model: str,
    fact_model: str,
    recap_model: str | None = None,
    batch_size: int | None = None,
    filter_version: str | None = None,
    pipeline_code_sha: str | None = None,
) -> dict[str, Any]:
    contract: dict[str, Any] = {
        "contract_version": 1,
        "store_sha256": store_sha256,
        "corpus_source_sha256": corpus_source_sha256,
        "entity_prompt_id": getattr(entity_extractor, "_PROMPT_ID", ""),
        "fact_prompt_id": getattr(fact_extractor, "_PROMPT_ID", ""),
        "entity_model": entity_model,
        "fact_model": fact_model,
        "taxonomy_hash": compute_taxonomy_hash(),
        "heuristic_blocklist_hash": compute_heuristic_blocklist_hash(),
    }

    recap_prompt_id = getattr(entity_extractor, "_RECAP_PROMPT_ID", None)
    if recap_prompt_id:
        contract["recap_prompt_id"] = recap_prompt_id
    if recap_model:
        contract["recap_model"] = recap_model
    if batch_size is not None:
        contract["batch_size"] = batch_size
    if filter_version:
        contract["filter_version"] = filter_version
    if pipeline_code_sha:
        contract["pipeline_code_sha"] = pipeline_code_sha
    return contract


def contracts_equal(left: dict[str, Any], right: dict[str, Any]) -> bool:
    required = [
        "contract_version",
        "store_sha256",
        "corpus_source_sha256",
        "entity_prompt_id",
        "fact_prompt_id",
        "entity_model",
        "fact_model",
        "taxonomy_hash",
        "heuristic_blocklist_hash",
    ]
    return all(left.get(field) == right.get(field) for field in required)
