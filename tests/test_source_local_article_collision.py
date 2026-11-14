"""Definite articles may require source-local review; they never prove identity."""
import pytest

from apps.live_control_server.models.world_graph_identity_models import IdentityCandidate
from apps.live_control_server.models.world_graph_mutation_context import (
    MutationObject, WorldGraphMutationContext, resolve_identity_against_context,
)


def resolve(label, *, existing_label='Grit and Grime', aliases=(), kind='location', canon='canonical', source_local=True):
    obj = MutationObject(object_id='loc:grit', label=existing_label, kind=kind,
                         aliases=aliases, canon_state=canon)
    context = WorldGraphMutationContext(world_id='eldyrwild', revision_id='rev:test',
        head_revision_id='rev:test', objects={obj.object_id: obj})
    candidate = IdentityCandidate(world_id='eldyrwild', candidate_id='location:grit',
        label=label, object_kind='location', evidence_ref_ids=['source:session10:paragraph4'],
        campaign_scope='longmont-c1', source_artifact_id='artifact:session10',
        proposed_node_id='source-local:v1:'+'a'*64)
    return resolve_identity_against_context(context, candidate, source_local=source_local)


@pytest.mark.parametrize('label,existing', [
    ('The Grit and Grime', 'Grit and Grime'),
    ('Grit and Grime', 'The Grit and Grime'),
    ('THE  Grit and Grime', 'Grit and Grime'),
])
def test_article_variation_requires_review_without_binding(label, existing):
    result = resolve(label, existing_label=existing)
    assert result.outcome == 'ambiguous'
    assert result.blocked_by == ['loc:grit']
    assert result.requires_human_review
    assert result.target_node_id is None
    assert result.created_node_id is None


def test_article_variation_of_existing_alias_requires_review():
    assert resolve('Grit and Grime', existing_label='Warehouse club',
                   aliases=('The Grit and Grime',)).outcome == 'ambiguous'


@pytest.mark.parametrize('kind', ['item', 'party'])
def test_article_variation_does_not_bypass_cross_kind_review(kind):
    assert resolve('The Grit and Grime', kind=kind).outcome == 'ambiguous'


@pytest.mark.parametrize('canon', ['retracted', 'rejected'])
def test_article_variation_does_not_reactivate_withdrawn_objects(canon):
    assert resolve('The Grit and Grime', canon=canon).outcome == 'created_new'


def test_article_variation_does_not_match_arbitrary_substrings():
    assert resolve('Grit and Grime partygoers').outcome == 'created_new'


def test_article_expansion_does_not_change_legacy_identity_resolution():
    result = resolve('The Grit and Grime', source_local=False)
    assert result.outcome != 'resolved_existing'
    assert result.target_node_id is None
