from __future__ import annotations

from pathlib import Path

import pytest

from scripts.live_dogfood_reset import apply_plan, build_plan, main, validate_session_dir


def _repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    return root


def _session(root: Path) -> Path:
    session_dir = root / "evals" / "c2_live_prep" / "live" / "session_22"
    session_dir.mkdir(parents=True)
    (session_dir / "live_packet.json").write_text('{"campaign_id":"longmont-c2","session":22}\n', encoding="utf-8")
    (session_dir / "surface_layout.json").write_text("{}\n", encoding="utf-8")
    return session_dir


def _add_dogfood_artifacts(session_dir: Path) -> None:
    (session_dir / "statblock_drafts").mkdir()
    (session_dir / "statblock_drafts" / "draft.json").write_text("{}\n", encoding="utf-8")
    (session_dir / "statblock_retrieval").mkdir()
    (session_dir / "statblock_retrieval" / "generated_statblocks_manifest.json").write_text("{}\n", encoding="utf-8")
    (session_dir / "combat").mkdir()
    (session_dir / "combat" / "current_combat.json").write_text("{}\n", encoding="utf-8")
    (session_dir / "event_log.jsonl").write_text("keep\n", encoding="utf-8")


def _add_generated_corpus(root: Path) -> Path:
    generated = root / "corpus" / "eldyrwild-markdown" / "Longmont Campaign" / "Campaign 2" / "Statblocks" / "generated"
    generated.mkdir(parents=True)
    (generated / "dogfood-drake.md").write_text("# Dogfood Drake\n", encoding="utf-8")
    (generated / "notes.txt").write_text("not markdown\n", encoding="utf-8")
    return generated


def test_dry_run_does_not_delete_session_artifacts(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    session_dir = _session(root)
    _add_dogfood_artifacts(session_dir)

    result = main(["--repo-root", str(root), "--session-dir", str(session_dir)])

    assert result == 0
    assert (session_dir / "statblock_drafts" / "draft.json").exists()
    assert (session_dir / "statblock_retrieval" / "generated_statblocks_manifest.json").exists()
    assert (session_dir / "combat" / "current_combat.json").exists()
    assert (session_dir / "live_packet.json").exists()


def test_apply_deletes_only_approved_session_artifacts(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    session_dir = _session(root)
    _add_dogfood_artifacts(session_dir)

    plan = build_plan(session_dir=session_dir, repo_root=root)
    apply_plan(plan)

    assert not (session_dir / "statblock_drafts").exists()
    assert not (session_dir / "statblock_retrieval").exists()
    assert not (session_dir / "combat").exists()
    assert (session_dir / "live_packet.json").exists()
    assert (session_dir / "surface_layout.json").exists()
    assert (session_dir / "event_log.jsonl").read_text(encoding="utf-8") == "keep\n"


@pytest.mark.parametrize(
    "unsafe_rel",
    [
        ".",
        "evals",
        "evals/c2_live_prep",
        "evals/c2_live_prep/live",
    ],
)
def test_unsafe_session_dirs_are_refused(tmp_path: Path, unsafe_rel: str) -> None:
    root = _repo(tmp_path)
    unsafe = root / unsafe_rel
    unsafe.mkdir(parents=True, exist_ok=True)
    (unsafe / "live_packet.json").write_text("{}\n", encoding="utf-8")

    with pytest.raises(ValueError):
        validate_session_dir(unsafe, root)


def test_session_dir_without_live_packet_is_refused(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    session_dir = root / "evals" / "c2_live_prep" / "live" / "session_22"
    session_dir.mkdir(parents=True)

    with pytest.raises(ValueError):
        build_plan(session_dir=session_dir, repo_root=root)


def test_corpus_purge_requires_explicit_flag_and_deletes_only_markdown(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    session_dir = _session(root)
    generated = _add_generated_corpus(root)

    no_purge_plan = build_plan(session_dir=session_dir, repo_root=root)
    assert no_purge_plan.generated_corpus_targets == ()

    purge_plan = build_plan(session_dir=session_dir, repo_root=root, purge_generated_corpus=True)
    assert purge_plan.generated_corpus_targets == (generated / "dogfood-drake.md",)

    apply_plan(purge_plan)

    assert not (generated / "dogfood-drake.md").exists()
    assert (generated / "notes.txt").exists()
    assert (session_dir / "live_packet.json").exists()
