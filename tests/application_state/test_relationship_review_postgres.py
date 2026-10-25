"""Evaluate the installed database admission boundary on disposable PostgreSQL."""
import copy
from importlib import import_module
import psycopg
from psycopg.types.json import Jsonb
from tests.test_relationship_review_output import fixture


def test_installed_relationship_completion_constraint_accepts_only_new_frozen_review(application_state_dsn):
    migration=import_module('application_state.migrations.versions.20261025_0067_relationship_review')
    _,proposal=fixture()
    receipt={'schema':'dmb_build_graph_context_receipt_v1','context_receipt_sha256':'a'*64,'source_basis':{'content_sha256':'b'*64}}
    policy={'working_draft_context_policy':'captured_build_working_draft_context_v1','related_page_context_policy':'selected_exact_related_authored_pages_v1','collaboration_output_policy':'typed_author_review_collaboration_v1','connected_page_review_policy':'typed_connected_page_review_v1','relationship_review_policy':'typed_saved_relationship_review_v1'}
    completion={'schema':'dmb_build_relationship_review_completion_v1','context_receipt_sha256':'a'*64,'answer_basis':'working_draft_context','answer_context_status':'creative_proposal','answer_segments':[{'kind':'connective','text':'Ready for author review.'}],'citation_map':None,'source_citations':[],'collaboration':proposal}
    with psycopg.connect(application_state_dsn) as c:
        installed=c.execute("SELECT pg_get_constraintdef(oid) FROM pg_constraint WHERE conname='agent_turn_graph_completion_check'").fetchone()[0]
        assert 'dmb_build_relationship_review_completion_v1' in installed
        def allowed(value,profile=policy):
            return c.execute('SELECT COALESCE(('+migration._REVIEW+'),FALSE) FROM (SELECT %s::jsonb completion,%s::jsonb graph_context_receipt,%s::jsonb graph_context_execution) v',(Jsonb(value),Jsonb(receipt),Jsonb({'policy':profile}))).fetchone()[0]
        assert allowed(completion)
        assert not allowed(completion,{k:v for k,v in policy.items() if k!='relationship_review_policy'})
        old=copy.deepcopy(completion);old['schema']='dmb_build_connected_page_review_completion_v1'
        assert not allowed(old)
        for mutate in [lambda p:p.update(published=True),lambda p:p['source'].update(node_id='model-id'),lambda p:p.update(context=[]),lambda p:p.pop('quote')]:
            bad=copy.deepcopy(completion);mutate(bad['collaboration']);assert not allowed(bad)
