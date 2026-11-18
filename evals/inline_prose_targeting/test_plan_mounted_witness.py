"""Generator integrity, not frontend behavior or model evidence."""
from pathlib import Path
import pytest
from evals.inline_prose_targeting.plan_mounted_witness import OWNER, derive, replace_once

ROOT=Path(__file__).resolve().parents[2]

def test_derived_fixture_preserves_owner_bytes_and_reuses_real_surface():
    owner=ROOT/OWNER; before=owner.read_bytes()
    generated=derive(before.decode(),owner)
    assert owner.read_bytes()==before
    assert "from \""+str(owner.parent/'PlanSurfacePage')+"\"" in generated
    assert "entry.selector === 'after:2'" in generated
    assert "if (mode === 'altered_boundary') { capture.from += 1; capture.to += 1; }" in generated
    assert 'expect(reopened.getJSON()).toEqual(afterJson)' in generated
    assert 'expect(editor.commands.undo()).toBe(true)' in generated
    assert "it.each(['offered_boundary','altered_boundary','stale_draft'] as const)" in generated
    assert "expect(request.plan_authoring_capture!.from).toBe(1)" in generated

@pytest.mark.parametrize('source',['absent','anchor anchor'])
def test_anchor_drift_refuses_instead_of_silently_running_old_fixture(source):
    with pytest.raises(ValueError):replace_once(source,'anchor','new')

def test_owner_case_drift_is_not_an_unverified_substitute():
    owner=ROOT/OWNER
    source=owner.read_text().replace("entries.find(entry => entry.kind === 'end_page')!",'changed')
    with pytest.raises(ValueError):derive(source,owner)
