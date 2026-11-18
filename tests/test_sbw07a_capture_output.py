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


def test_capture_marks_interrupted_publication(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from scripts.capture_sbw07a_server_create_transcripts import _publish_capture

    leaf = tmp_path / "leaf.json"
    manifest = tmp_path / "MANIFEST.json"
    manifest.write_bytes(b"previous manifest")
    outputs = {leaf: b"new leaf", manifest: b"new manifest"}
    replace = Path.replace

    def fail_manifest(source: Path, target: Path) -> Path:
        if target == manifest:
            raise OSError("interrupted publication")
        return replace(source, target)

    with monkeypatch.context() as patch:
        patch.setattr(Path, "replace", fail_manifest)
        with pytest.raises(OSError, match="interrupted publication"):
            _publish_capture(tmp_path, outputs)

    marker = tmp_path / ".capture-in-progress"
    assert marker.exists()
    assert manifest.read_bytes() == b"previous manifest"
    with pytest.raises(SystemExit, match="Interrupted or active capture"):
        _publish_capture(tmp_path, outputs)

    marker.unlink()
    _publish_capture(tmp_path, outputs)
    assert not marker.exists()
    assert manifest.read_bytes() == b"new manifest"
    assert leaf.read_bytes() == b"new leaf"
