"""Exact Rules identity/composition invariants, independent of runtime/tool wiring."""
from hashlib import sha256
import json
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError
from application_state.agent_conversation.rules_authority_types import (
    AnswerCompositionV1, OrderedAnswerRefV1, RULES_BUDGET_V1, RulesAcceptedBindingV1,
    RulesBudgetV1, RulesClaimV1, RulesContextV1, RulesScopeV1, RulesSupportRefV1,
    RulesSupportV1, SegmentMapItemV1, SourceAffordanceV1, canonical_bytes, canonical_sha256,
)


def hashed(text): return sha256(text.encode('utf-8')).hexdigest()


def support(text='Cannot end a move in occupied space.', **overrides):
    fields = dict(schema='dmb_rules_support_v1', support_id=uuid4(), corpus_sha256='a'*64,
        ruleset_id='dnd_2024_srd_5_2_1', unit_id='b'*64, full_text_sha256=hashed(text), excerpt_start=0,
        excerpt_end=len(text), excerpt_text=text, excerpt_sha256=hashed(text), source_title='SRD 5.2.1',
        section='Occupancy', source_uri='https://example.invalid/srd.pdf', source_sha256='c'*64,
        page_fingerprint='d'*64, pdf_page_index=13, printed_page=14)
    fields.update(overrides)
    return RulesSupportV1(**fields)


def revalidate(model, edit):
    raw = model.model_dump(mode='json', by_alias=True)
    edit(raw)
    return type(model).model_validate_json(json.dumps(raw, ensure_ascii=False))


def composition(base=True):
    unit = support()
    ref = RulesSupportRefV1(support_id=unit.support_id, support_sha256=canonical_sha256(unit))
    claim = RulesClaimV1(kind='rules_claim', claim_id='rules:one', text='The source prohibits this move.', support_refs=(ref,))
    context = RulesContextV1(kind='rules_context', segment_id='context:one', text='Other rules may also apply.', category='gap')
    texts = ('The Plan names this crossing.',) if base else ()
    segments = ([OrderedAnswerRefV1(domain='base', segment_index=0)] if base else []) + [OrderedAnswerRefV1(domain='rules', segment_index=0), OrderedAnswerRefV1(domain='rules', segment_index=1)]
    answer = '\n'.join((*texts, claim.text, context.text))
    value = AnswerCompositionV1(schema='dmb_answer_composition_v1', base_disposition='approved' if base else 'absent',
        ordered_refs=tuple(segments), rules_segments=(claim,context), assistant_text_sha256=hashed(answer))
    return value, unit, texts, answer


def binding(base=True):
    value, unit, texts, answer = composition(base)
    items=[]; start=0
    for ordinal, ref in enumerate(value.ordered_refs):
        args=dict(base_segment_index=None,rules_claim_id=None,rules_context_id=None,category=None,support_refs=())
        if ref.domain=='base':
            text=texts[ref.segment_index]; domain='base'; args['base_segment_index']=ref.segment_index
        else:
            segment=value.rules_segments[ref.segment_index]; text=segment.text; domain=segment.kind
            if isinstance(segment,RulesClaimV1):args.update(rules_claim_id=segment.claim_id,support_refs=segment.support_refs)
            else:args.update(rules_context_id=segment.segment_id,category=segment.category)
        items.append(SegmentMapItemV1(ordinal=ordinal,domain=domain,text_start=start,text_end=start+len(text),**args));start+=len(text)+1
    result=RulesAcceptedBindingV1(schema='dmb_rules_accepted_binding_v1',world_id='world-A',conversation_id=uuid4(),turn_id=uuid4(),
        corpus_sha256=unit.corpus_sha256,ruleset_id=unit.ruleset_id,accepted_turn_revision=9,product_attempt=1,execution_id=uuid4(),
        producing_provider_attempt_id=uuid4(),request_envelope_sha256='e'*64,composition_sha256=canonical_sha256(value),
        assistant_text_sha256=hashed(answer),base_text_sha256=hashed('\n'.join(texts)) if base else None,
        base_disposition=value.base_disposition,segment_map=tuple(items),support_table=(SourceAffordanceV1(support_id=unit.support_id,support_sha256=canonical_sha256(unit),source_label='SRD 5.2.1 · Page 14'),),graph_used=False)
    return result,texts,answer


def test_unicode_canonical_bytes_are_stable_without_prose_normalization():
    unit=support('Tiny 🐉')
    assert b'\\u' not in canonical_bytes(unit)
    assert canonical_sha256(unit)==hashed(canonical_bytes(unit).decode())
    assert canonical_sha256(unit)!=canonical_sha256(support('Tiny  🐉',support_id=unit.support_id))


def test_scope_freezes_exact_owner_attempt_source_and_integer_budgets():
    scope=RulesScopeV1(schema='dmb_rules_scope_v1',execution_id=uuid4(),world_id='world-A',conversation_id=uuid4(),turn_id=uuid4(),product_attempt=1,
        ruleset_id='dnd_2024_srd_5_2_1',corpus_sha256='a'*64,authorization_id=uuid4(),capability_policy_sha256='b'*64,budget=RULES_BUDGET_V1)
    assert RulesScopeV1.model_validate_json(canonical_bytes(scope))==scope
    with pytest.raises(ValidationError):revalidate(scope,lambda d:d.update(product_attempt=0))
    with pytest.raises(ValidationError):revalidate(scope,lambda d:d.update(extra='no'))
    with pytest.raises(ValidationError):revalidate(RULES_BUDGET_V1,lambda d:d.update(calls=6.0))
    with pytest.raises(ValidationError):revalidate(RULES_BUDGET_V1,lambda d:d.update(calls=7))


@pytest.mark.parametrize('change',[
    lambda d:d.update(excerpt_sha256='e'*64),lambda d:d.update(excerpt_end=9000),lambda d:d.update(excerpt_start=1),
    lambda d:d.update(unit_id='A'*64),lambda d:d.update(source_uri='file:///private'),lambda d:d.update(pdf_page_index=-1),
    lambda d:d.update(excerpt_text=''),lambda d:d.update(path='/private'),
])
def test_support_rejects_changed_scope_shape_range_hash_or_path(change):
    with pytest.raises(ValidationError):revalidate(support(),change)


def test_support_enforces_utf8_budget_separately_from_codepoints():
    with pytest.raises(ValidationError):support('🐉'*5000)
    assert support('🐉'*1000).excerpt_end==1000


def test_mixed_composition_and_lightweight_binding_reconstruct_exact_base_text():
    comp,_,base,answer=composition()
    assert comp.render(base)==answer
    accepted,base,answer=binding()
    assert accepted.validate_text(answer,base)=='\n'.join(base)
    assert 'The source prohibits' not in canonical_bytes(accepted).decode()


def test_rules_only_and_unclaimed_do_not_require_fake_base_segments():
    comp,_,base,answer=composition(False)
    assert comp.render()==answer
    accepted,_,answer=binding(False)
    assert accepted.validate_text(answer)==''
    unclaimed=revalidate(accepted,lambda d:d.update(base_disposition='unclaimed'))
    assert unclaimed.validate_text(answer)=='' and not unclaimed.graph_used
    with pytest.raises(ValidationError):revalidate(unclaimed,lambda d:d.update(graph_used=True))


@pytest.mark.parametrize('change',[
    lambda d:d['ordered_refs'].append(d['ordered_refs'][-1]),
    lambda d:d['ordered_refs'].pop(),
    lambda d:d['ordered_refs'][0].update(segment_index=1),
    lambda d:d['rules_segments'][1].update(segment_id='rules:one'),
    lambda d:d.update(base_disposition='unclaimed'),
])
def test_composition_rejects_missing_reordered_or_ambiguous_segments(change):
    comp,*_=composition()
    with pytest.raises(ValidationError):revalidate(comp,change)


@pytest.mark.parametrize('change',[
    lambda d:d['segment_map'][0].update(text_start=1),
    lambda d:d['segment_map'][1].update(text_start=0),
    lambda d:d['segment_map'][1].update(ordinal=0),
    lambda d:d['segment_map'][0].update(rules_claim_id='forged'),
    lambda d:d['support_table'].clear(),
    lambda d:d['support_table'].append(d['support_table'][0]),
    lambda d:d['segment_map'][1]['support_refs'][0].update(support_sha256='f'*64),
    lambda d:d.update(base_text_sha256=None),
])
def test_binding_rejects_uncovered_or_misattributed_ranges(change):
    accepted,*_=binding()
    with pytest.raises(ValidationError):revalidate(accepted,change)


def test_stored_text_or_base_subsequence_cannot_be_substituted():
    accepted,base,answer=binding()
    with pytest.raises(ValueError):accepted.validate_text(answer+' changed',base)
    with pytest.raises(ValueError):accepted.validate_text(answer,('Other base.',))
    bad=revalidate(accepted,lambda d:d.update(assistant_text_sha256=hashed(answer.replace('\n',' ',1))))
    with pytest.raises(ValueError):bad.validate_text(answer.replace('\n',' ',1),base)


def test_binding_hash_covers_sources_and_mapping_but_not_an_extra_copy_of_prose():
    accepted,base,answer=binding()
    edited=revalidate(accepted,lambda d:d['support_table'][0].update(source_label='Another label'))
    assert canonical_sha256(accepted)!=canonical_sha256(edited)
    assert accepted.validate_text(answer,base)==edited.validate_text(answer,base)
