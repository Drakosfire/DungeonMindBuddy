from extraction_lab.pipeline_contract import (
    compute_heuristic_blocklist_hash,
    compute_pipeline_contract,
    compute_taxonomy_hash,
    contracts_equal,
)


def test_compute_pipeline_contract_is_stable() -> None:
    first = compute_pipeline_contract(
        store_sha256="store123",
        corpus_source_sha256="source123",
        entity_model="gpt-5.4-nano",
        fact_model="gpt-5.4-nano",
    )
    second = compute_pipeline_contract(
        store_sha256="store123",
        corpus_source_sha256="source123",
        entity_model="gpt-5.4-nano",
        fact_model="gpt-5.4-nano",
    )
    assert first == second
    assert contracts_equal(first, second)


def test_contracts_equal_detects_required_field_change() -> None:
    baseline = compute_pipeline_contract(
        store_sha256="store123",
        corpus_source_sha256="source123",
        entity_model="gpt-5.4-nano",
        fact_model="gpt-5.4-nano",
    )
    changed = dict(baseline)
    changed["entity_model"] = "gpt-5.4-mini"
    assert not contracts_equal(baseline, changed)


def test_hash_fields_are_hex_and_non_empty() -> None:
    taxonomy_hash = compute_taxonomy_hash()
    blocklist_hash = compute_heuristic_blocklist_hash()
    assert len(taxonomy_hash) == 64
    assert len(blocklist_hash) == 64
    int(taxonomy_hash, 16)
    int(blocklist_hash, 16)
