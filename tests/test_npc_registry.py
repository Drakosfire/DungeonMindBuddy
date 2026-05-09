"""Tests for the NPC registry artifact: schema, Pydantic loader, and lint script.

Filesystem checks use ``tmp_path`` and synthetic registry files so the tests
stay hermetic — no dependence on the real corpus shape.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from textwrap import dedent

import pytest
from pydantic import ValidationError as PydanticValidationError

from src.contracts.npc_registry import (
    NpcRegistryRecord,
    dump_npc_registry,
    load_npc_registry,
)
from src.contracts.schema_validation import validate_instance


_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT / "scripts"))

import lint_npc_registry as lint  # noqa: E402


_SCHEMA_FILE = "npc_registry.schema.json"
_SCHEMA_PATH = _REPO_ROOT / "schemas" / "v0.1" / _SCHEMA_FILE


def _valid_record_payload(**overrides) -> dict:
    base = {
        "slug": "elderly_fisherman",
        "display_name": "Kirfan",
        "aliases": ["the elderly fisherman"],
        "status": "tracked",
        "first_session": 1,
        "last_session": 3,
        "hub_path": "Setting/NPCs/elderly_fisherman/",
        "setting_hub_path": None,
        "notes": "",
    }
    base.update(overrides)
    return base


# --------------------------------------------------------------------------- #
# Schema-level validation
# --------------------------------------------------------------------------- #


class TestSchema:
    def test_accepts_complete_valid_record(self) -> None:
        payload = [_valid_record_payload()]
        validate_instance(payload, _SCHEMA_FILE)

    def test_rejects_record_missing_slug(self) -> None:
        bad = _valid_record_payload()
        bad.pop("slug")
        with pytest.raises(Exception):
            validate_instance([bad], _SCHEMA_FILE)

    def test_rejects_invalid_status_enum(self) -> None:
        bad = _valid_record_payload(status="archived")
        with pytest.raises(Exception):
            validate_instance([bad], _SCHEMA_FILE)

    def test_accepts_null_setting_hub_and_empty_notes(self) -> None:
        payload = [
            _valid_record_payload(setting_hub_path=None, notes="")
        ]
        validate_instance(payload, _SCHEMA_FILE)

    def test_rejects_unknown_field(self) -> None:
        bad = _valid_record_payload(secret_field="nope")
        with pytest.raises(Exception):
            validate_instance([bad], _SCHEMA_FILE)


# --------------------------------------------------------------------------- #
# Pydantic mirror
# --------------------------------------------------------------------------- #


class TestPydantic:
    def test_round_trip_via_loader_and_dump(self, tmp_path: Path) -> None:
        records_in = [
            NpcRegistryRecord.model_validate(
                _valid_record_payload(
                    slug="zelig",
                    display_name="Zelig",
                    first_session=2,
                    last_session=2,
                    hub_path="Setting/NPCs/zelig/",
                )
            ),
            NpcRegistryRecord.model_validate(
                _valid_record_payload(
                    slug="aldric",
                    display_name="Aldric",
                    aliases=["Al"],
                    first_session=1,
                    last_session=4,
                    hub_path="Setting/NPCs/aldric/",
                )
            ),
        ]

        path = tmp_path / "registry.json"
        path.write_text(dump_npc_registry(records_in), encoding="utf-8")

        records_out = load_npc_registry(path)
        # dump_npc_registry sorts by slug, so the on-disk order is alphabetical.
        assert [r.slug for r in records_out] == ["aldric", "zelig"]

        # Round-trip equality after re-sorting input the same way.
        sorted_in = sorted(records_in, key=lambda r: r.slug)
        for left, right in zip(sorted_in, records_out, strict=True):
            assert left.model_dump() == right.model_dump()

    def test_pydantic_rejects_first_session_greater_than_last(self) -> None:
        with pytest.raises(PydanticValidationError):
            NpcRegistryRecord.model_validate(
                _valid_record_payload(first_session=5, last_session=3)
            )

    def test_pydantic_rejects_tracked_with_null_hub(self) -> None:
        with pytest.raises(PydanticValidationError):
            NpcRegistryRecord.model_validate(
                _valid_record_payload(status="tracked", hub_path=None)
            )

    def test_pydantic_allows_candidate_with_null_hub(self) -> None:
        record = NpcRegistryRecord.model_validate(
            _valid_record_payload(status="candidate", hub_path=None)
        )
        assert record.status == "candidate"
        assert record.hub_path is None

    def test_pydantic_rejects_identical_hub_and_setting_paths(self) -> None:
        with pytest.raises(PydanticValidationError):
            NpcRegistryRecord.model_validate(
                _valid_record_payload(
                    hub_path="Longmont Campaign/Campaign 2/NPCs/kirfan/",
                    setting_hub_path="Longmont Campaign/Campaign 2/NPCs/kirfan/",
                )
            )

    def test_loader_raises_on_non_array_top_level(self, tmp_path: Path) -> None:
        path = tmp_path / "registry.json"
        path.write_text(json.dumps({"not": "an array"}), encoding="utf-8")
        with pytest.raises(ValueError, match="must be a JSON array"):
            load_npc_registry(path)


# --------------------------------------------------------------------------- #
# Lint script — synthetic corpus
# --------------------------------------------------------------------------- #


def _write_registry(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8")


def _scaffold_hub(corpus_root: Path, hub_rel: str) -> None:
    folder = corpus_root / hub_rel.rstrip("/")
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "README.md").write_text("# stub\n", encoding="utf-8")


def _run_lint(tmp_path: Path, registry_path: Path, corpus_root: Path) -> tuple[int, str]:
    import io
    from contextlib import redirect_stdout

    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = lint.main(
            [
                "--path",
                str(registry_path),
                "--corpus-root",
                str(corpus_root),
                "--schema",
                str(_SCHEMA_PATH),
            ]
        )
    return rc, buf.getvalue()


class TestLintScript:
    def test_clean_run_reports_zero_issues(self, tmp_path: Path) -> None:
        corpus_root = tmp_path / "corpus"
        hub_rel = "Setting/NPCs/jane_doe/"
        _scaffold_hub(corpus_root, hub_rel)

        registry = tmp_path / "_npc_registry.json"
        _write_registry(
            registry,
            [_valid_record_payload(slug="jane_doe", display_name="Jane Doe", hub_path=hub_rel)],
        )

        rc, output = _run_lint(tmp_path, registry, corpus_root)
        assert rc == 0, output
        assert "1 records, 1 OK, 0 with issues" in output
        assert "OK    [00] jane_doe" in output

    def test_missing_hub_directory_is_reported(self, tmp_path: Path) -> None:
        corpus_root = tmp_path / "corpus"
        corpus_root.mkdir()

        registry = tmp_path / "_npc_registry.json"
        _write_registry(
            registry,
            [
                _valid_record_payload(
                    slug="ghost",
                    display_name="Ghost",
                    hub_path="Setting/NPCs/ghost/",
                )
            ],
        )

        rc, output = _run_lint(tmp_path, registry, corpus_root)
        assert rc == 1
        assert "directory does not exist" in output

    def test_duplicate_slugs_are_reported(self, tmp_path: Path) -> None:
        corpus_root = tmp_path / "corpus"
        _scaffold_hub(corpus_root, "Setting/NPCs/twin/")

        registry = tmp_path / "_npc_registry.json"
        _write_registry(
            registry,
            [
                _valid_record_payload(
                    slug="twin", display_name="Twin A", hub_path="Setting/NPCs/twin/"
                ),
                _valid_record_payload(
                    slug="twin", display_name="Twin B", hub_path="Setting/NPCs/twin/"
                ),
            ],
        )

        rc, output = _run_lint(tmp_path, registry, corpus_root)
        assert rc == 1
        assert "duplicate slug 'twin'" in output

    def test_tracked_with_null_hub_is_reported(self, tmp_path: Path) -> None:
        corpus_root = tmp_path / "corpus"
        corpus_root.mkdir()

        registry = tmp_path / "_npc_registry.json"
        # Bypass Pydantic by writing JSON directly.
        _write_registry(
            registry,
            [_valid_record_payload(status="tracked", hub_path=None)],
        )

        rc, output = _run_lint(tmp_path, registry, corpus_root)
        assert rc == 1
        assert "hub_path" in output and "tracked" in output

    def test_first_session_greater_than_last_is_reported(
        self, tmp_path: Path
    ) -> None:
        corpus_root = tmp_path / "corpus"
        _scaffold_hub(corpus_root, "Setting/NPCs/odd/")

        registry = tmp_path / "_npc_registry.json"
        _write_registry(
            registry,
            [
                _valid_record_payload(
                    slug="odd",
                    display_name="Odd",
                    first_session=10,
                    last_session=5,
                    hub_path="Setting/NPCs/odd/",
                )
            ],
        )

        rc, output = _run_lint(tmp_path, registry, corpus_root)
        assert rc == 1
        assert "first_session (10) > last_session (5)" in output

    def test_slug_folder_name_mismatch_is_reported(self, tmp_path: Path) -> None:
        corpus_root = tmp_path / "corpus"
        # Folder is 'jane_doe' but the registry slug is 'janet_doe'.
        _scaffold_hub(corpus_root, "Setting/NPCs/jane_doe/")

        registry = tmp_path / "_npc_registry.json"
        _write_registry(
            registry,
            [
                _valid_record_payload(
                    slug="janet_doe",
                    display_name="Janet Doe",
                    hub_path="Setting/NPCs/jane_doe/",
                )
            ],
        )

        rc, output = _run_lint(tmp_path, registry, corpus_root)
        assert rc == 1
        assert "does not match slug 'janet_doe'" in output

    def test_setting_hub_path_must_point_to_world_layer(self, tmp_path: Path) -> None:
        corpus_root = tmp_path / "corpus"
        _scaffold_hub(corpus_root, "Longmont Campaign/Campaign 2/NPCs/kirfan/")
        _scaffold_hub(corpus_root, "Longmont Campaign/Campaign 1/NPCs/kirfan/")

        registry = tmp_path / "_npc_registry.json"
        _write_registry(
            registry,
            [
                _valid_record_payload(
                    slug="kirfan",
                    display_name="Kirfan",
                    hub_path="Longmont Campaign/Campaign 2/NPCs/kirfan/",
                    setting_hub_path="Longmont Campaign/Campaign 1/NPCs/kirfan/",
                )
            ],
        )

        rc, output = _run_lint(tmp_path, registry, corpus_root)
        assert rc == 1
        assert "setting_hub_path — must point to an Elderwyld world-layer hub path" in output

    def test_campaign_hub_requires_setting_fallback_when_world_sibling_exists(
        self, tmp_path: Path
    ) -> None:
        corpus_root = tmp_path / "corpus"
        _scaffold_hub(corpus_root, "Longmont Campaign/Campaign 1/NPCs/grishna/")
        _scaffold_hub(corpus_root, "Elderwyld/Cities and Towns/Stonebridge/NPCs/grishna/")

        registry = tmp_path / "_npc_registry.json"
        _write_registry(
            registry,
            [
                _valid_record_payload(
                    slug="grishna",
                    display_name="Grishna",
                    hub_path="Longmont Campaign/Campaign 1/NPCs/grishna/",
                    setting_hub_path=None,
                )
            ],
        )

        rc, output = _run_lint(tmp_path, registry, corpus_root)
        assert rc == 1
        assert "setting_hub_path — missing world fallback while an Elderwyld sibling hub exists" in output
