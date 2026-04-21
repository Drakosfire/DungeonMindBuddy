"""Tests for `scripts/lint_corpus_hubs.py`.

Builds a tiny synthetic corpus under `tmp_path` containing one compliant NPC
hub, one non-compliant PC hub, and one location-dossier collection. Asserts
the linter reports the expected OK / ISSUE counts and that the closed-vocab
checks fire on the right fields.
"""

from __future__ import annotations

import io
import sys
from contextlib import redirect_stdout
from pathlib import Path
from textwrap import dedent

import pytest

# Ensure the scripts directory is importable.
_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT / "scripts"))

import lint_corpus_hubs as lint  # noqa: E402


def _write(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(body).lstrip("\n"), encoding="utf-8")


@pytest.fixture
def synthetic_corpus(tmp_path: Path) -> Path:
    """Builds:

    - A compliant NPC hub: `<root>/Setting/NPCs/jane_doe/README.md` + dossier + timeline.
    - A non-compliant PC hub (`john_doe`): README + dossier, missing timeline →
      ISSUEs on subject_class, subject_doc_kind, AND timeline.
    - A non-compliant PC hub (`jane_pc`): README only, no dossier and no timeline
      → ISSUEs on both `timeline.md` and `{slug}_character_dossier.md` (proves
      the inception strictness fires on bare hubs).
    - A location-dossier collection: `<root>/Setting/Town/Town_Location_Dossiers/Inn.md`.
    - A top-level location hub WITHOUT a README (should ISSUE).
    """
    root = tmp_path / "corpus"

    # Compliant NPC hub.
    _write(
        root / "Setting" / "NPCs" / "jane_doe" / "README.md",
        """
        ---
        title: "Jane Doe — NPC hub"
        document_class: reference
        subject_class: npc
        subject_doc_kind: hub_index
        canon_layer: world
        ---

        # Jane Doe
        """,
    )
    _write(
        root / "Setting" / "NPCs" / "jane_doe" / "jane_doe_character_dossier.md",
        """
        ---
        title: "Jane Doe — dossier"
        document_class: reference
        subject_class: npc
        subject_doc_kind: dossier
        ---

        body
        """,
    )
    _write(
        root / "Setting" / "NPCs" / "jane_doe" / "timeline.md",
        """
        ---
        title: "Jane Doe — timeline"
        document_class: reference
        subject_class: npc
        subject_doc_kind: timeline
        ---

        | Session | Beat | Recap |
        |---------|------|-------|
        """,
    )

    # Non-compliant PC hub: missing subject_class, wrong subject_doc_kind, has dossier
    # but no timeline.
    _write(
        root / "Campaign" / "PCs" / "john_doe" / "README.md",
        """
        ---
        title: "John Doe"
        document_class: reference
        subject_doc_kind: dossier
        ---

        # John Doe
        """,
    )
    _write(
        root / "Campaign" / "PCs" / "john_doe" / "john_doe_character_dossier.md",
        """
        ---
        title: "John Doe — dossier"
        document_class: reference
        subject_class: pc
        subject_doc_kind: dossier
        ---
        """,
    )

    # Inception-only PC hub: README only, no dossier and no timeline. The new
    # PC strictness should ISSUE on both missing satellites.
    _write(
        root / "Campaign" / "PCs" / "jane_pc" / "README.md",
        """
        ---
        title: "Jane PC — Campaign N (PC hub)"
        document_class: reference
        subject_class: pc
        subject_doc_kind: hub_index
        canon_layer: campaign
        ---

        # Jane PC
        """,
    )

    # Location dossier collection (README optional; one dossier inside).
    _write(
        root / "Setting" / "Cities and Towns" / "Town" / "Town_Location_Dossiers" / "Inn.md",
        """
        ---
        title: "The Inn"
        document_class: world
        subject_class: location
        subject_doc_kind: location_dossier
        ---
        """,
    )

    # Top-level location hub WITHOUT a README (should ISSUE).
    # Add a world primer + sub-folder so it qualifies as a top hub.
    _write(
        root
        / "Setting"
        / "Cities and Towns"
        / "Town"
        / "The City of Town.md",
        """
        ---
        title: "The City of Town"
        document_class: world
        subject_class: location
        subject_doc_kind: world_primer
        ---
        """,
    )

    return root


def test_discover_hubs_finds_all_three_shapes(synthetic_corpus: Path) -> None:
    candidates = lint.discover_hubs(synthetic_corpus)
    shapes = sorted(c.shape for c in candidates)
    # NPC, PC, location_top, location_dossiers.
    assert "npc" in shapes
    assert "pc" in shapes
    assert "location_top" in shapes
    assert "location_dossiers" in shapes


def test_compliant_npc_hub_passes(synthetic_corpus: Path) -> None:
    npc_hub = synthetic_corpus / "Setting" / "NPCs" / "jane_doe"
    candidate = next(
        c for c in lint.discover_hubs(synthetic_corpus) if c.path == npc_hub
    )
    report = lint.validate_hub(candidate)
    assert report.ok, f"expected OK, got issues: {report.issues}"


def test_non_compliant_pc_hub_reports_missing_subject_class(
    synthetic_corpus: Path,
) -> None:
    pc_hub = synthetic_corpus / "Campaign" / "PCs" / "john_doe"
    candidate = next(
        c for c in lint.discover_hubs(synthetic_corpus) if c.path == pc_hub
    )
    report = lint.validate_hub(candidate)
    assert not report.ok
    issues = " | ".join(report.issues)
    assert "subject_class" in issues
    assert "subject_doc_kind" in issues  # was 'dossier', expected 'hub_index'
    assert "timeline.md" in issues  # dossier present, no timeline


def test_inception_only_pc_hub_reports_missing_dossier_and_timeline(
    synthetic_corpus: Path,
) -> None:
    """A PC hub with just a compliant README (no dossier, no timeline) must
    ISSUE on both satellites under the new inception-strictness rule."""
    pc_hub = synthetic_corpus / "Campaign" / "PCs" / "jane_pc"
    candidate = next(
        c for c in lint.discover_hubs(synthetic_corpus) if c.path == pc_hub
    )
    report = lint.validate_hub(candidate)
    assert not report.ok, "expected ISSUEs on inception-only PC hub"
    issues = " | ".join(report.issues)
    assert "timeline.md" in issues
    assert "_character_dossier.md" in issues
    # subject_class / subject_doc_kind are correct on this fixture, so the only
    # ISSUEs should be the two missing satellites.
    assert all(
        ("timeline.md" in i) or ("_character_dossier.md" in i)
        for i in report.issues
    ), f"unexpected ISSUEs beyond the two satellites: {report.issues}"


def test_location_dossier_collection_without_readme_is_ok(
    synthetic_corpus: Path,
) -> None:
    coll = (
        synthetic_corpus
        / "Setting"
        / "Cities and Towns"
        / "Town"
        / "Town_Location_Dossiers"
    )
    candidate = next(
        c for c in lint.discover_hubs(synthetic_corpus) if c.path == coll
    )
    report = lint.validate_hub(candidate)
    assert report.ok, f"expected OK (README optional), got issues: {report.issues}"


def test_main_emits_summary_and_returns_zero_by_default(
    synthetic_corpus: Path,
) -> None:
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = lint.main(["--corpus", str(synthetic_corpus)])
    out = buf.getvalue()
    assert rc == 0
    assert "Summary:" in out
    assert "OK count" not in out  # we use the literal "OK"/"ISSUE" prefix
    assert "OK" in out
    assert "ISSUE" in out


def test_main_strict_flag_returns_one_when_issues_exist(
    synthetic_corpus: Path,
) -> None:
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = lint.main(["--corpus", str(synthetic_corpus), "--strict"])
    assert rc == 1
