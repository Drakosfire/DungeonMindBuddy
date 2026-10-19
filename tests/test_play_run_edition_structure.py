from uuid import uuid4

import pytest

from apps.live_control_server.services.play_run_edition_structure import (
    EditionStructureError,
    validate_edition_structure,
)
from apps.live_control_server.services.play_run_reference_manifest import (
    derive_sealed_manifest,
)
from tests.application_state.play_runtime_helpers import V2_SOURCE_MARKDOWN

SOURCE = V2_SOURCE_MARKDOWN.replace(
    "id=choice:route -->", "id=choice:route scene=scene:gate -->"
).replace("id=option:fire -->", "id=option:fire activates=scene:gate -->")


def manifest(source=SOURCE):
    return derive_sealed_manifest(
        source,
        run_id=str(uuid4()),
        playable_artifact_id=str(uuid4()),
        playable_revision=1,
        playable_content_sha256="a" * 64,
        sealed_at="2026-10-18T00:00:00Z",
    ).model_dump(mode="json", exclude_none=True)


def test_content_tables_callouts_media_titles_and_collapse_do_not_restructure():
    candidate = SOURCE.replace("The Gate", "The changed gate").replace(
        "Burn through the growth", "Try talking"
    )
    candidate += "\n| Detail | Value |\n|---|---|\n| weather | rain |\n\n> [!NOTE]\n> quiet\n\n![map](media:map){width=50%}\n\n<details><summary>More</summary>Text</details>\n"
    assert validate_edition_structure(SOURCE, candidate, manifest())


@pytest.mark.parametrize(
    "candidate",
    [
        SOURCE.replace("scene:gate", "scene:other"),
        SOURCE.replace("## Arrival", "### Arrival"),
        SOURCE.replace(
            "kind=beat id=beat:arrival", "kind=beat id=beat:arrival beat_kind=optional"
        ),
        SOURCE.replace("activates=scene:gate", "suppresses=scene:gate"),
        SOURCE.replace(" scene=scene:gate", ""),
        SOURCE.replace("id=option:wait", "id=option:fire"),
        SOURCE.replace("v2", "v1"),
        SOURCE.replace("### The Gate", "> ### The Gate"),
        SOURCE.replace(
            "<!-- dmb-playable-element:v2 kind=scene",
            "```\n<!-- dmb-playable-element:v2 kind=scene",
        )
        + "\n```",
        SOURCE
        + "\n<!-- dmb-playable-element:v2 kind=scene id=scene:new -->\n### New\n",
        SOURCE + "\n## Unmarked boundary\n",
        SOURCE.replace("### The Gate", "### The Gate\n\n### Another boundary"),
        SOURCE.replace(
            "- Wait and watch", "- Wait and watch\n- Another unmarked option"
        ),
        SOURCE.replace(
            "<!-- dmb-playable-element:v2 kind=option id=option:wait -->\n- Wait and watch\n",
            "",
        ),
        SOURCE.replace(
            "<!-- dmb-playable-element:v2 kind=option id=option:wait -->\n- Wait and watch",
            "<!-- dmb-playable-element:v2 kind=beat id=beat:other -->\n## Other\n<!-- dmb-playable-element:v2 kind=option id=option:wait -->\n- Wait and watch",
        ),
        "\n".join(reversed(SOURCE.splitlines())),
    ],
)
def test_structural_changes_fail(candidate):
    with pytest.raises(EditionStructureError):
        validate_edition_structure(SOURCE, candidate, manifest())


def test_frontmatter_and_marker_envelopes_are_preserved():
    origin = "---\ntitle: Original\n---\n" + SOURCE
    assert validate_edition_structure(
        origin, origin.replace("The Gate", "Another gate"), manifest()
    )
    with pytest.raises(EditionStructureError):
        validate_edition_structure(
            origin, origin.replace("title: Original", "title: Changed"), manifest()
        )
    with pytest.raises(EditionStructureError):
        validate_edition_structure(
            SOURCE, SOURCE.replace("<!-- dmb-", " <!-- dmb-", 1), manifest()
        )


def test_order_changes_rejected_even_when_sorted_manifest_matches():
    a = "<!-- dmb-playable-element:v2 kind=option id=option:fire activates=scene:gate -->\n- Burn through the growth"
    b = "<!-- dmb-playable-element:v2 kind=option id=option:wait -->\n- Wait and watch"
    candidate = SOURCE.replace(a, "PLACEHOLDER").replace(b, a).replace("PLACEHOLDER", b)
    assert manifest()["options"] == manifest(candidate)["options"]
    with pytest.raises(EditionStructureError):
        validate_edition_structure(SOURCE, candidate, manifest())


def test_scene_and_choice_order_and_parent_changes_fail():
    tail = "\n<!-- dmb-playable-element:v2 kind=beat id=beat:next -->\n## Next\n\n<!-- dmb-playable-element:v2 kind=scene id=scene:next -->\n### Next Scene\n"
    source = SOURCE + tail
    candidate = tail + SOURCE
    with pytest.raises(EditionStructureError):
        validate_edition_structure(source, candidate, manifest(source))
    gate = "<!-- dmb-playable-element:v2 kind=scene id=scene:gate -->\n### The Gate\n"
    moved = source.replace(gate, "") + "\n" + gate
    with pytest.raises(EditionStructureError):
        validate_edition_structure(source, moved, manifest(source))


def test_markers_inside_blockquotes_or_indented_code_are_not_active():
    for prefix in ["> ", "    "]:
        candidate = "\n".join(prefix + line for line in SOURCE.splitlines())
        with pytest.raises(EditionStructureError):
            validate_edition_structure(SOURCE, candidate, manifest())


def test_bom_frontmatter_remains_exact_metadata():
    source = "\ufeff---\ntitle: Original\n---\n" + SOURCE
    assert validate_edition_structure(source, source + "\nBody change\n", manifest())
    with pytest.raises(EditionStructureError):
        validate_edition_structure(
            source, source.replace("title: Original", "title: Changed"), manifest()
        )
