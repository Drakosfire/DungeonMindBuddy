"""Display lookup never supplies source authority or newer metadata as exact history."""
from types import SimpleNamespace as N
import pytest
from apps.live_control_server.services import native_source_display as display


def objects():
    artifact=N(source_artifact_id='source')
    revision=N(source_revision_id='revision',content_sha256='hash')
    return N(access=object(),authority=N(managed_world_id='world')),N(artifact=artifact,revision=revision),N(source_artifact=artifact,source_revision=revision)


@pytest.mark.parametrize('change',['exact','artifact','revision','hash','duplicate','unavailable','error'])
def test_opened_label_requires_exact_admitted_member_but_metadata_is_optional(monkeypatch,change):
    prepared,member,item=objects()
    if change in {'artifact','revision','hash'}:
        if change=='artifact':item.source_artifact=N(source_artifact_id='other')
        else:item.source_revision=N(source_revision_id='other' if change=='revision' else 'revision',content_sha256='other' if change=='hash' else 'hash')
    items=[item,item] if change=='duplicate' else [item]
    monkeypatch.setattr('dungeonmind.application.vnext.list_admitted_native_text_sources',lambda access:N(sources=items))
    calls=[]
    def metadata(items,world):
        calls.append((items,world))
        if change=='error':raise RuntimeError('metadata lookup unavailable')
        return [dict(status='unavailable' if change=='unavailable' else 'available',label='Recap',campaign_id='campaign',session_id='session',origin_matches_current_metadata=True)]
    monkeypatch.setattr(display,'source_display_metadata',metadata)
    label=display.opened_source_display_label(prepared,member)
    assert label==('Recap · campaign: campaign · session: session' if change=='exact' else None)
    assert len(calls)==(0 if change in {'artifact','revision','hash','duplicate'} else 1)


def test_old_page_label_stays_qualified_and_missing_names_stay_explicit():
    old=dict(status='available',label='Current page title',campaign_id=None,session_id=None,origin_matches_current_metadata=False)
    assert display.source_display_name(old,'Source')=='Current page title · current page label; selected source is an older revision'
    assert display.source_display_name(None,'Source')=='Source (source name unavailable)'
