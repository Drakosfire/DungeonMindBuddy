"""Same synthetic source bytes consumed by the editor conformance suite.

The v2 parser sorts membership arrays; these are not document order authority.
No database, Run creation, persisted manifest or private corpus is exercised.
"""
import json
from pathlib import Path

import pytest

from apps.live_control_server.services.play_run_reference_manifest import (
    PlayRunReferenceManifestError,
    derive_play_run_reference_elements,
    derive_play_run_reference_elements_v2,
    detect_playable_grammar_version,
)

CASES = json.loads((Path(__file__).parent / "fixtures/playable_edge_conformance.json").read_text())["cases"]


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["name"])
def test_shared_source_effect_target_conformance(case):
    markdown = case["markdown"]
    assert detect_playable_grammar_version(markdown) == case["grammar"]
    derive = derive_play_run_reference_elements if case["grammar"] == 1 else derive_play_run_reference_elements_v2
    if not case["valid"]:
        with pytest.raises(PlayRunReferenceManifestError) as error:
            derive(markdown)
        assert error.value.status_code == 409
        return
    parsed = derive(markdown)
    if case["grammar"] == 1:
        assert [element.model_dump() for element in parsed] == case["expected"]
        assert [element.element_id for element in parsed] == case["order"]
    else:
        assert {name: [element.model_dump() for element in getattr(parsed, name)]
                for name in ("beats", "scenes", "choices", "options", "edges")} == case["expected"]
