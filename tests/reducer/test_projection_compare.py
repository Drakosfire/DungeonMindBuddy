from __future__ import annotations

import pytest

from src.reducer.projection_compare import assert_attribute_keys_match_golden_contract


def test_assert_attribute_keys_rejects_unknown_payload_keys() -> None:
    actual = {
        "campaign_id": "c1",
        "entities": {
            "ent_x": {
                "attributes": {
                    "mood": {
                        "selected_fact_id": "f1",
                        "value_label": "calm",
                        "value_normalized": "calm",
                        "fact_ids": ["f1"],
                        "provenance_evidence_ids": ["e1"],
                        "conflict_ids": [],
                        "unexpected_new_field": True,
                    }
                }
            }
        },
        "conflicts": [],
        "metrics": {},
    }
    expected = {
        "campaign_id": "c1",
        "entities": {
            "ent_x": {
                "attributes": {
                    "mood": {
                        "selected_fact_id": "f1",
                        "value_label": "calm",
                        "value_normalized": "calm",
                        "fact_ids": ["f1"],
                        "provenance_evidence_ids": ["e1"],
                        "conflict_ids": [],
                    }
                }
            }
        },
        "conflicts": [],
        "metrics": {},
    }
    with pytest.raises(AssertionError, match="unexpected keys"):
        assert_attribute_keys_match_golden_contract(
            actual_projection=actual,
            expected_projection=expected,
            label="unit",
        )
