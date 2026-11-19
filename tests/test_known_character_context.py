from types import SimpleNamespace as NS
import pytest
from apps.live_control_server.services import known_character_context as service


def test_only_admitted_character_identity_fields_are_copied(monkeypatch):
    rows = {
        'c':NS(subject_entity_id='e1',predicate='dnd5e:classification',value=NS(term='dungeonbuddy:character')),
        'n':NS(subject_entity_id='e1',predicate='dnd5e:name',value=NS(value='Mara')),
        'n2':NS(subject_entity_id='place',predicate='dnd5e:name',value=NS(value='Tower')),
        's':NS(subject_entity_id='e1',predicate='dnd5e:summary',value=NS(value='Historical secret, not current recap')),
    }
    parsed=NS(get_assertion=rows.__getitem__,get_entity_aliases=lambda eid: ['candidate'],graph_payload_sha256='a'*64)
    listing=NS(entities=[NS(entity_id='e1'),NS(entity_id='place')],admitted_assertion_ids=list(rows),completeness=NS(status='complete'),result_digest='digest')
    reader=NS(list_entities=lambda read:listing,get_complete_entity=lambda read,eid:NS(found=True,completeness=NS(status='complete'),aliases=[NS(alias_text='M. Vale' if eid=='e1' else 'Mara',alias_id='alias1' if eid=='e1' else 'alias2')]))
    monkeypatch.setattr(service,'EntityReadService',lambda:reader)
    monkeypatch.setattr(service.native,'binding',lambda _: {'native_world_id':'world','binding_version':1})
    monkeypatch.setattr(service.native,'read_repository',lambda:NS(get_head=lambda _:NS(head_revision_id='r1')))
    monkeypatch.setattr(service.native,'read_context',lambda *a:(object(),NS(parsed=parsed),None,None))
    result=service.read_known_character_catalog('managed','campaign')
    assert result['entities'][0]['names']==['Mara','M. Vale']
    assert result['entities'][0]['assertion_ids']==['c','n']
    assert 'Historical secret' not in str(result)
    assert result['native_pin']['revision_id']=='r1'
    assert result['ambiguous_names']==['mara']


def test_provisioning_world_has_no_graph_reader_or_file_fallback(monkeypatch):
    class Pending(Exception): code='native_graph_provisioning_pending'
    def binding(_): raise Pending()
    monkeypatch.setattr(service.native,'binding',binding)
    monkeypatch.setattr(service.native,'read_repository',lambda:pytest.fail('provisioning cannot read Graph'))
    from apps.live_control_server.services import managed_world_graph_projection as m
    monkeypatch.setattr(m,'resolve_managed_source_identity',lambda _:NS(managed_world_id='m',native_world_id='n',binding_version=1))
    result=service.read_known_character_catalog('m','c')
    assert result['status']=='native_graph_provisioning' and result['entities']==[]


def test_name_review_rejects_catalog_from_changed_world_binding(monkeypatch):
    from apps.live_control_server.services import recap_name_review
    from graph_memory.ingestion.native_recap_source import SourceScope

    scope = SourceScope(
        managed_world_id="managed-a", native_world_id="native-a",
        binding_version=1, campaign_id="campaign",
    )
    monkeypatch.setattr(service, "read_known_character_catalog", lambda *_: {
        "entities": [],
        "native_pin": {"native_world_id": "native-a", "binding_version": 2},
    })
    with pytest.raises(ValueError, match="World binding changed"):
        recap_name_review.prepare_name_review("Mara waits.", scope, session_id="session-1")
