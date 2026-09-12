import json

from extraction_lab.anchor_schema import load_entity_anchors, load_fact_anchors
from extraction_lab.benchmark_contract import compute_benchmark_contract


def _write_json(path, payload) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _anchors(tmp_path, *, core_name="Brin", working_name="Karsemine"):
    entities = tmp_path / "entities.json"
    facts = tmp_path / "facts.json"
    _write_json(
        entities,
        [
            {
                "anchor_id": "brin",
                "intent": "Brin identity",
                "expected_class": "actor",
                "expected_names": [core_name],
                "surface": "core_extraction",
            },
            {
                "anchor_id": "karsemine",
                "intent": "Working set",
                "expected_class": "actor",
                "expected_names": [working_name],
                "surface": "working_set",
            },
        ],
    )
    _write_json(
        facts,
        [
            {
                "anchor_id": "brin_role",
                "intent": "Brin role",
                "subject_anchor": "brin",
                "expected_attribute": "role",
                "match_keywords": ["leader"],
                "surface": "core_extraction",
            }
        ],
    )
    return load_entity_anchors(entities), load_fact_anchors(facts)


def _contract(root, entities, facts):
    return compute_benchmark_contract(
        surface="core_extraction",
        source_paths=[root / "session.md"],
        corpus_source_root=root,
        entity_anchors=entities,
        fact_anchors=facts,
    )


def test_corpus_identity_is_independent_of_absolute_root(tmp_path) -> None:
    entities, facts = _anchors(tmp_path)
    root_a = tmp_path / "checkout-a" / "corpus"
    root_b = tmp_path / "checkout-b" / "corpus"
    root_a.mkdir(parents=True)
    root_b.mkdir(parents=True)
    (root_a / "session.md").write_text("Brin leads the refugees.\n", encoding="utf-8")
    (root_b / "session.md").write_text("Brin leads the refugees.\n", encoding="utf-8")
    assert (
        _contract(root_a, entities, facts)["corpus"]["fingerprint"]
        == _contract(root_b, entities, facts)["corpus"]["fingerprint"]
    )


def test_gold_identity_is_surface_filtered_and_semantic(tmp_path) -> None:
    root = tmp_path / "corpus"
    root.mkdir()
    (root / "session.md").write_text("Brin leads the refugees.\n", encoding="utf-8")
    entities, facts = _anchors(tmp_path, working_name="Karsemine")
    baseline = _contract(root, entities, facts)
    unrelated_entities, unrelated_facts = _anchors(
        tmp_path, working_name="Karsemine Ironveil"
    )
    unrelated = _contract(root, unrelated_entities, unrelated_facts)
    changed_entities, changed_facts = _anchors(tmp_path, core_name="Brynn")
    changed = _contract(root, changed_entities, changed_facts)
    assert baseline["gold"]["fingerprint"] == unrelated["gold"]["fingerprint"]
    assert baseline["gold"]["fingerprint"] != changed["gold"]["fingerprint"]


def test_gold_identity_ignores_anchor_and_set_like_list_order(tmp_path) -> None:
    root = tmp_path / "corpus"
    root.mkdir()
    (root / "session.md").write_text("Brin leads the refugees.\n", encoding="utf-8")
    entities, facts = _anchors(tmp_path)
    baseline = _contract(root, entities, facts)
    reordered = compute_benchmark_contract(
        surface="core_extraction",
        source_paths=[root / "session.md"],
        corpus_source_root=root,
        entity_anchors=list(reversed(entities)),
        fact_anchors=list(reversed(facts)),
    )
    assert baseline["gold"]["fingerprint"] == reordered["gold"]["fingerprint"]


def test_corpus_byte_change_changes_identity(tmp_path) -> None:
    entities, facts = _anchors(tmp_path)
    root = tmp_path / "corpus"
    root.mkdir()
    source = root / "session.md"
    source.write_text("Brin leads the refugees.\n", encoding="utf-8")
    before = _contract(root, entities, facts)
    source.write_text("Brin follows the refugees.\n", encoding="utf-8")
    after = _contract(root, entities, facts)
    assert before["corpus"]["fingerprint"] != after["corpus"]["fingerprint"]


def test_corpus_identity_fails_closed_without_stable_root(tmp_path) -> None:
    entities, facts = _anchors(tmp_path)
    contract = compute_benchmark_contract(
        surface="core_extraction",
        source_paths=[tmp_path / "session.md"],
        corpus_source_root=None,
        entity_anchors=entities,
        fact_anchors=facts,
    )
    assert contract["corpus"]["available"] is False
    assert contract["corpus"]["fingerprint"] is None
