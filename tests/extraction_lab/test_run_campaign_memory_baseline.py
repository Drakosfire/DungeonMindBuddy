import json
from pathlib import Path

from extraction_lab.run_campaign_memory_baseline import run_campaign_memory_baseline
from tests.extraction_lab.test_campaign_memory_baseline_manifest import manifest_payload


ROOT = Path(__file__).resolve().parents[2]


def test_default_is_inert_dry_run(tmp_path: Path) -> None:
    payload = manifest_payload()
    import subprocess

    payload["repository_sha"] = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps(payload), encoding="utf-8")
    out = tmp_path / "out"
    result = run_campaign_memory_baseline(
        manifest_path=manifest, out_dir=out, repo_root=ROOT
    )
    assert result["mode"] == "dry_run"
    assert result["plan"]["source_ingestions"] == 21
    assert not out.exists()
