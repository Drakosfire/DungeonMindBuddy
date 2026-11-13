from pathlib import Path

import pytest

from scripts.capture_sbw07a_server_create_transcripts import (
    _output_dirs,
    _prepare_output_dirs,
)


def test_scratch_capture_refuses_existing_leaf_alias(tmp_path: Path) -> None:
    _, tracked = _output_dirs(tmp_path, None)
    tracked.mkdir(parents=True)
    witness = tracked / "create-request.json"
    witness.write_text("tracked evidence")

    scratch, leaves = _output_dirs(tmp_path, Path("scratch"))
    scratch.mkdir()
    leaves.symlink_to(tracked, target_is_directory=True)
    with pytest.raises(SystemExit, match="new directory"):
        _prepare_output_dirs(scratch, leaves, scratch=True)
    assert witness.read_text() == "tracked evidence"

    scratch, leaves = _output_dirs(tmp_path, Path("fresh"))
    _prepare_output_dirs(scratch, leaves, scratch=True)
    assert leaves.is_dir()
    assert leaves.parent == scratch
