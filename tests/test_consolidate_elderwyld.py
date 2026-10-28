"""Operator safety cases; no primary databases, providers or source files."""
import json
from pathlib import Path

import pytest

from scripts.consolidate_elderwyld import NEW_ROOT, OLD_ROOT, apply_files, file_plan


def seed(root: Path):
    for prefix in (NEW_ROOT, OLD_ROOT, 'out/registries'):
        (root / prefix).mkdir(parents=True)
    (root / OLD_ROOT / 'original.md').write_bytes(b'# Original\r\nNever normalize my bytes.\r\n')
    (root / NEW_ROOT / 'Edge.md').write_bytes(b'# Edge\nNew dogfood writing.\n')
    for name in ('workspace_documents', 'source_artifacts', 'recap_artifacts'):
        (root / 'out/registries' / (name + '.json')).write_text(json.dumps({'records': []}))


def test_collision_refuses_before_any_write(tmp_path):
    seed(tmp_path)
    (tmp_path / NEW_ROOT / 'original.md').write_text('Different writing')
    with pytest.raises(ValueError, match='Different bytes'):
        file_plan(tmp_path)
    assert (tmp_path / NEW_ROOT / 'original.md').read_text() == 'Different writing'


def test_renamed_case_collision_refuses(tmp_path):
    seed(tmp_path)
    (tmp_path / NEW_ROOT / 'ORIGINAL.md').write_text('same meaning is insufficient')
    with pytest.raises(ValueError, match='Case collision'):
        file_plan(tmp_path)


def test_symlink_escape_refuses(tmp_path):
    seed(tmp_path)
    (tmp_path / OLD_ROOT / 'escape.md').symlink_to(tmp_path / NEW_ROOT / 'Edge.md')
    with pytest.raises(ValueError, match='Symlink'):
        file_plan(tmp_path)


def test_drift_refuses_before_any_copy(tmp_path):
    seed(tmp_path)
    plan = file_plan(tmp_path)
    (tmp_path / NEW_ROOT / 'Edge.md').write_text('Newer writing')
    with pytest.raises(ValueError, match='File drift'):
        apply_files(tmp_path, plan)
    assert not (tmp_path / NEW_ROOT / 'original.md').exists()


def test_preserves_bytes_ids_and_replays_without_relabeled_evidence(tmp_path):
    seed(tmp_path)
    path = tmp_path / 'out/registries/workspace_documents.json'
    path.write_text(json.dumps({'records': [{'document_id': 'keep-id', 'world_id': 'eldyrwild', 'campaign_id': 'longmont-c2', 'target_relpath': OLD_ROOT + '/original.md'}]}))
    source = tmp_path / 'out/registries/source_artifacts.json'
    source.write_text(json.dumps({'records': [{'source_artifact_id': 'immutable-old', 'world_id': 'eldyrwild'}, {'source_artifact_id': 'keep-other', 'world_id': 'other'}]}))
    original = (tmp_path / OLD_ROOT / 'original.md').read_bytes()
    plan = file_plan(tmp_path)
    apply_files(tmp_path, plan)
    apply_files(tmp_path, plan)
    assert (tmp_path / NEW_ROOT / 'original.md').read_bytes() == original
    assert json.loads(path.read_bytes())['records'] == [{'document_id': 'keep-id', 'world_id': 'elderwyld', 'campaign_id': 'longmont-c2', 'target_relpath': NEW_ROOT + '/original.md'}]
    assert json.loads(source.read_bytes())['records'] == [{'source_artifact_id': 'keep-other', 'world_id': 'other'}]


def test_old_path_with_other_world_owner_is_refused(tmp_path):
    seed(tmp_path)
    (tmp_path / 'out/registries/workspace_documents.json').write_text(json.dumps({'records': [{'document_id': 'other', 'world_id': 'another-world', 'campaign_id': 'another-world', 'target_relpath': OLD_ROOT + '/original.md'}]}))
    with pytest.raises(ValueError, match='Unexpected owner'):
        file_plan(tmp_path)
