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


def test_capture_refuses_old_schema_before_writing_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    import sys
    from scripts import capture_sbw07a_server_create_transcripts as capture
    from apps.live_control_server.integrations.dungeonmind_statblocks.generated import (
        OPENAPI_FINGERPRINT,
    )

    server = tmp_path / "server"
    artifact = server / "openapi/dungeonbuddy-statblocks-v1.json"
    artifact.parent.mkdir(parents=True)
    artifact.write_text("{}")
    buddy = Path(__file__).resolve().parents[1]
    output = tmp_path / "capture-output"
    monkeypatch.setattr(capture, "_assert_clean_worktree", lambda _: None)
    monkeypatch.setattr(capture, "_assert_package_from_checkout", lambda _: server / "statblocks_v1/__init__.py")
    old = "sha256:df46327f24180150aadd28a8fe6477ceabde40c300b64c931b27e639a762f36a"
    monkeypatch.setattr(capture, "_sha256_file", lambda _: old)
    monkeypatch.setattr(sys, "argv", [
        "capture", "--buddy-repo", str(buddy), "--server-repo", str(server),
        "--out-subdir", str(output),
    ])

    with pytest.raises(SystemExit, match="does not match Buddy vendored contract") as error:
        capture.main()
    assert old in str(error.value)
    assert OPENAPI_FINGERPRINT in str(error.value)
    assert not output.exists()
