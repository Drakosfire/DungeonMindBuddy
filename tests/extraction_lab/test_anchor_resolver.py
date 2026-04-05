from extraction_lab.anchor_resolver import resolve_entity_anchor, resolve_fact_anchor
from extraction_lab.anchor_schema import EntityGoldAnchor, FactGoldAnchor


def test_entity_anchor_passes_with_class_name_and_fact_count() -> None:
    anchor = EntityGoldAnchor(
        anchor_id="mirathorn_city",
        intent="mirathorn",
        expected_class="place",
        expected_names=["Mirathorn"],
        min_fact_count=2,
    )
    entities = [{"entity_id": "ent_mirathorn", "display_name": "Mirathorn", "entity_class": "place", "aliases": []}]
    facts = [
        {"fact_id": "f1", "subject_entity_id": "ent_mirathorn", "attribute": "geography", "value": {"label": "foo"}},
        {"fact_id": "f2", "subject_entity_id": "ent_mirathorn", "attribute": "history", "value": {"label": "bar"}},
    ]
    result = resolve_entity_anchor(anchor, entities, facts)
    assert result["passed"] is True
    assert result["resolved_entity_id"] == "ent_mirathorn"


def test_entity_anchor_fails_with_class_mismatch() -> None:
    anchor = EntityGoldAnchor(
        anchor_id="mirathorn_city",
        intent="mirathorn",
        expected_class="place",
        expected_names=["Mirathorn"],
    )
    entities = [{"entity_id": "ent_mirathorn", "display_name": "Mirathorn", "entity_class": "group", "aliases": []}]
    result = resolve_entity_anchor(anchor, entities, [])
    assert result["passed"] is False
    assert result["fail_bucket"] == "class_mismatch"


def test_entity_anchor_fails_with_name_not_found() -> None:
    anchor = EntityGoldAnchor(
        anchor_id="mirathorn_city",
        intent="mirathorn",
        expected_class="place",
        expected_names=["Mirathorn"],
    )
    entities = [{"entity_id": "ent_other", "display_name": "Other City", "entity_class": "place", "aliases": []}]
    result = resolve_entity_anchor(anchor, entities, [])
    assert result["passed"] is False
    assert result["fail_bucket"] == "name_not_found"


def test_entity_anchor_fails_with_fact_count_below_min() -> None:
    anchor = EntityGoldAnchor(
        anchor_id="mirathorn_city",
        intent="mirathorn",
        expected_class="place",
        expected_names=["Mirathorn"],
        min_fact_count=2,
    )
    entities = [{"entity_id": "ent_mirathorn", "display_name": "Mirathorn", "entity_class": "place", "aliases": []}]
    facts = [{"fact_id": "f1", "subject_entity_id": "ent_mirathorn", "attribute": "geography", "value": {"label": "x"}}]
    result = resolve_entity_anchor(anchor, entities, facts)
    assert result["passed"] is False
    assert result["fail_bucket"] == "fact_count_below_min"


def test_fact_anchor_passes_on_attribute_and_keyword_match() -> None:
    entity_result = {"anchor_id": "mirathorn_city", "passed": True, "resolved_entity_id": "ent_mirathorn"}
    anchor = FactGoldAnchor(
        anchor_id="mirathorn_geography",
        intent="geo",
        subject_anchor="mirathorn_city",
        expected_attribute="geography",
        match_keywords=["stormspire"],
    )
    facts = [
        {
            "fact_id": "fact_1",
            "subject_entity_id": "ent_mirathorn",
            "attribute": "geography",
            "value": {"label": "Near Stormspire Peaks"},
        }
    ]
    result = resolve_fact_anchor(anchor, {"mirathorn_city": entity_result}, facts)
    assert result["passed"] is True
    assert result["matched_fact_id"] == "fact_1"


def test_fact_anchor_fails_when_subject_unresolved() -> None:
    anchor = FactGoldAnchor(
        anchor_id="mirathorn_geography",
        intent="geo",
        subject_anchor="mirathorn_city",
        expected_attribute="geography",
        match_keywords=["stormspire"],
    )
    result = resolve_fact_anchor(anchor, {}, [])
    assert result["passed"] is False
    assert result["fail_bucket"] == "subject_unresolved"


def test_fact_anchor_fails_with_missing_fact() -> None:
    entity_result = {"anchor_id": "mirathorn_city", "passed": True, "resolved_entity_id": "ent_mirathorn"}
    anchor = FactGoldAnchor(
        anchor_id="mirathorn_geography",
        intent="geo",
        subject_anchor="mirathorn_city",
        expected_attribute="geography",
        match_keywords=["stormspire"],
    )
    result = resolve_fact_anchor(anchor, {"mirathorn_city": entity_result}, [])
    assert result["passed"] is False
    assert result["fail_bucket"] == "missing_fact"


def test_fact_anchor_fails_with_attribute_mismatch() -> None:
    entity_result = {"anchor_id": "mirathorn_city", "passed": True, "resolved_entity_id": "ent_mirathorn"}
    anchor = FactGoldAnchor(
        anchor_id="mirathorn_geography",
        intent="geo",
        subject_anchor="mirathorn_city",
        expected_attribute="geography",
        match_keywords=["stormspire"],
    )
    facts = [
        {
            "fact_id": "fact_1",
            "subject_entity_id": "ent_mirathorn",
            "attribute": "history",
            "value": {"label": "Founded by settlers"},
        }
    ]
    result = resolve_fact_anchor(anchor, {"mirathorn_city": entity_result}, facts)
    assert result["passed"] is False
    assert result["fail_bucket"] == "attribute_mismatch"


def test_fact_anchor_fails_with_keyword_mismatch() -> None:
    entity_result = {"anchor_id": "mirathorn_city", "passed": True, "resolved_entity_id": "ent_mirathorn"}
    anchor = FactGoldAnchor(
        anchor_id="mirathorn_geography",
        intent="geo",
        subject_anchor="mirathorn_city",
        expected_attribute="geography",
        match_keywords=["stormspire"],
    )
    facts = [
        {
            "fact_id": "fact_1",
            "subject_entity_id": "ent_mirathorn",
            "attribute": "geography",
            "value": {"label": "River delta district"},
        }
    ]
    result = resolve_fact_anchor(anchor, {"mirathorn_city": entity_result}, facts)
    assert result["passed"] is False
    assert result["fail_bucket"] == "keyword_mismatch"
