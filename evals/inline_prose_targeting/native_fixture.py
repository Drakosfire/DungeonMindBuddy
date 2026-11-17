"""Explicit disposable opt-in adapter for scripted native prose proof, not a product route."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
from uuid import uuid4
from application_state.build_proposal.types import BuildProposalReservation, BuildProseTarget, BuildProseBoundaryTarget, BuildProviderAuthorization
from application_state.build_proposal.service import BuildProposalService
from application_state.build_proposal.review import BuildProposalReviewService, BuildReviewCommand
from application_state.errors import ApplicationStateConflictError
from application_state.agent_conversation import AgentConversationService
from application_state.content import pages
from tests.page_fixtures import create_page_fixture, save_page
from tests.application_state.test_agent_conversation_postgres import _new
from apps.live_control_server.services.workspace_document_registry import get_workspace_document_snapshot


def sha(text): return hashlib.sha256(text.encode('utf-8')).hexdigest()
def wire(value): return json.dumps(value, ensure_ascii=False, separators=(',', ':'))
def utf16(text): return len(text.encode('utf-16-le')) // 2


def node_size(node):
    if node.get('type') == 'text': return utf16(node.get('text', ''))
    if 'content' in node or node.get('type') in {'paragraph','heading','pageRow','pageSlot','table','tableRow','tableCell','tableHeader'}:
        return 2 + sum(node_size(child) for child in node.get('content', []))
    return 1


def catalog_for(doc):
    """Same narrow root-paragraph offers as the mounted host; no model offsets."""
    choices, targets, headings = [], {}, []
    offset = ordinal = 0
    content = doc.get('content', [])
    for index, node in enumerate(content):
        children = node.get('content', [])
        text = ''.join(child.get('text', '') for child in children)
        # Native containers remain untouched and never acquire prose authority.
        # Count their exact recursive PM size so later root offsets remain exact.
        size = node_size(node)
        if node['type'] not in {'paragraph', 'heading'} or any(x['type'] != 'text' for x in children):
            offset += size
            continue
        next_is_table = index + 1 < len(content) and content[index + 1].get('type') == 'table'
        if node['type'] == 'heading':
            attrs = node.get('attrs', {})
            level = attrs.get('level')
            plain_caption = (level == 2 and text.strip() and
                all(key == 'level' or value is None for key, value in attrs.items()) and
                all(not child.get('marks') for child in children))
            if next_is_table and plain_caption:
                offset += size
                continue
            if not isinstance(level, int) or isinstance(level, bool) or not 1 <= level <= 6:
                offset += size
                continue
            while headings and headings[-1][0] >= level: headings.pop()
            headings.append((level, text))
        elif text.strip() and all(all(mark['type'] in {'bold','italic','strike','code','underline'} for mark in child.get('marks', [])) for child in children):
            ordinal += 1
            # Host aliases still count excluded caption paragraphs.
            if next_is_table:
                offset += size
                continue
            section = ' / '.join(row[1] for row in headings) or 'Before the first heading'
            for operation, start, end in [('replace_paragraph',offset+1,offset+size-1),('insert_before',offset,offset),('insert_after',offset+size,offset+size)]:
                alias = f'passage{ordinal}:{operation}'
                choices.append(dict(selector=alias,operation=operation,section=section,passage=text))
                targets[alias] = dict(operation=operation, **{'from':start,'to':end},before_text_sha256=sha(text))
        offset += size
    return choices, targets


class NativeProseFixture:
    def __init__(self, root: Path):
        self.root = root
        self.world = 'synthetic-prose-' + uuid4().hex[:10]
        self.document_id = None
        self.admitted = {}
        self.proposals = BuildProposalService(allow_prose_targets=True, allow_prose_boundaries=True, admit_prose_target=self.admit)
        self.reviews = BuildProposalReviewService(allow_prose_targets=True, allow_prose_boundaries=True, validate_prose_target=self.admit)

    def bootstrap(self, value):
        if self.document_id: raise ValueError('Fixture already bootstrapped')
        record = create_page_fixture(self.root,title='Synthetic prose targeting',world_id=self.world,
            campaign_id=self.world,kind='worldbuilding_source',source_domain='worldbuilding',
            document_class='lore',authority_state='draft',visibility_state='internal')
        self.document_id = record.document_id
        save_page(self.root,self.document_id,value['markdown'])
        if value.get('page_presentation') is not None:
            snap=pages.snapshot_page(self.document_id,world_id=self.world)
            pages.commit_page(self.document_id,value['markdown'],world_id=self.world,
                expected_revision=snap.page.object_revision,expected_working_copy_revision=snap.working_copy_revision,
                page_presentation=value['page_presentation'])
        self.conversation = _new(AgentConversationService(),self.world)
        return self.page()

    def page(self):
        snapshot = get_workspace_document_snapshot(self.root,self.document_id)
        return dict(world_id=self.world,document_id=self.document_id,registry_revision=snapshot.loaded_revision,
            content_sha256=snapshot.content_sha256,markdown=snapshot.markdown,
            page_presentation=snapshot.page_presentation.model_dump(mode='json') if snapshot.page_presentation else None,
            conversation_id=str(self.conversation.conversation_id),pointer_revision=1)

    def admit(self, reservation):
        captured = self.admitted.get(str(reservation.idempotency_key))
        if captured is None or reservation.prose_target != captured['target'] or reservation.basis.model_dump(mode='json') != captured['basis']:
            raise ApplicationStateConflictError('Target does not match this host-admitted capture')
        page = self.page(); basis = reservation.basis
        if (basis.world_id != self.world or basis.document_id != self.document_id
                or basis.registry_revision != page['registry_revision'] or basis.content_sha256 != page['content_sha256']):
            raise ApplicationStateConflictError('Saved source changed since host capture')

    def stage(self, value):
        basis = value['basis']; raw = value['editor_json']; doc = json.loads(raw)
        choices, targets = catalog_for(doc)
        if choices != value['catalog_choices'] or sha(raw) != basis['editor_sha256'] or sha(value['draft_markdown']) != basis['draft_sha256']:
            raise ApplicationStateConflictError('Snapshot or offered catalog changed')
        codec = BuildProseBoundaryTarget if value['prose_target'].get('schema') == 'dmb_build_prose_boundary_target_v1' else BuildProseTarget
        target = codec.model_validate(value['prose_target'])
        expected = targets.get(target.alias)
        if (expected is None or target.catalog_sha256 != sha(wire(choices))
                or any(target.model_dump(mode='json')[key] != expected[key] for key in ['operation','from','to','before_text_sha256'])):
            raise ApplicationStateConflictError('Alias is not an admitted exact root paragraph')
        action = uuid4()
        reservation = BuildProposalReservation(idempotency_key=action,conversation_id=self.conversation.conversation_id,
            expected_pointer_revision=1,basis=basis,prose_target=target,instruction='Scripted synthetic paragraph rewrite')
        self.admitted[str(action)] = dict(target=target,basis=reservation.basis.model_dump(mode='json'))
        record,_ = self.proposals.reserve(reservation)
        # This is explicitly a scripted provider-output control, not a model call.
        auth = BuildProviderAuthorization(provider_attempt_id=uuid4(),provider='openai',model='synthetic-no-provider',
            payload_sha256=sha('synthetic'),payload_utf8_bytes=9)
        record = self.proposals.advance(self.world,action,expected_revision=record.revision,state='authorized',authorization=auth)
        record = self.proposals.advance(self.world,action,expected_revision=record.revision,state='sdk_entered')
        output = wire(dict(destination='current_page',target='prose_target',replacement_markdown=value['replacement_markdown'],summary='Scripted fixture rewrite',assumptions=[]))
        record = self.proposals.advance(self.world,action,expected_revision=record.revision,state='response_received',raw_response=output)
        return self.proposals.advance(self.world,action,expected_revision=record.revision,state='proposed').model_dump(mode='json')

    def review(self, action, command=None):
        from uuid import UUID
        record = self.reviews.get(self.world,UUID(action)) if command is None else self.reviews.execute(self.world,UUID(action),BuildReviewCommand.model_validate(command))
        return record.model_dump(mode='json')

    def save(self, value):
        basis = value['basis']; current = self.page()
        if any(basis[key] != current[key] for key in ['world_id','document_id','registry_revision','content_sha256']):
            raise ApplicationStateConflictError('Explicit Save basis is stale')
        snap = pages.snapshot_page(self.document_id,world_id=self.world)
        kwargs = {}
        if 'page_presentation' in value: kwargs['page_presentation'] = value['page_presentation']
        pages.commit_page(self.document_id,value['markdown'],world_id=self.world,
            expected_revision=snap.page.object_revision,expected_working_copy_revision=snap.working_copy_revision,**kwargs)
        return self.page()
