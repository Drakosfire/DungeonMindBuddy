from __future__ import annotations

from pathlib import Path

from scripts.live_dogfood_check import check_session


def test_check_session_reports_invalid_surface_layout_json(tmp_path: Path, capsys) -> None:
    session_dir = tmp_path / "session_22"
    session_dir.mkdir()
    (session_dir / "live_packet.json").write_text("{}\n", encoding="utf-8")
    (session_dir / "surface_layout.json").write_text("{not json\n", encoding="utf-8")

    assert check_session(session_dir) is False

    output = capsys.readouterr().out
    assert "surface_layout.json: invalid JSON" in output
