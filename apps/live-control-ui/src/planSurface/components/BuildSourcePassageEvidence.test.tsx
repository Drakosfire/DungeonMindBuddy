import { act, fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { createHash, webcrypto } from 'node:crypto';
import { BuildSourcePassageEvidence, isBuildSourceCompletion, isSurfaceSourceCompletion } from './BuildSourcePassageEvidence';
import { ResponseEvidenceTabs } from './ResponseEvidenceTabs';
import { getAgentSourcePassage } from '../../api/liveApi';
import type { AgentSourcePassageReadResponseV1, WorldBuildGraphCompletionV2, SurfaceSourceCompletionV1 } from '../../api/types';
vi.mock('../../api/liveApi', () => ({ getAgentSourcePassage: vi.fn() }));
const load = vi.mocked(getAgentSourcePassage);
const text = 'Frank believes the **western gate** is haunted. 🐐';
const hash = (s: string) => createHash('sha256').update(s).digest('hex');
const id = '11111111-1111-4111-8111-111111111111';
function completion(): WorldBuildGraphCompletionV2 {
  return { schema: 'dmb_build_graph_completion_v2', context_receipt_sha256: 'a'.repeat(64),
    answer_basis: 'opened_source_passages', answer_context_status: 'source_grounded',
    answer_segments: [{kind: 'source_passage_claim', text: 'Frank believes the gate is haunted.'}], citation_map: null,
    source_citations: [{ segment_index: 0, text_sha256: hash('Frank believes the gate is haunted.'),
      provider_attempt_id: id, envelope_sha256: 'c'.repeat(64), read_event_id: id,
      receipt: {source_read_id: 'read', anchor_id: 'anchor', evidence_ref_id: 'evidence',
        source_artifact_id: 'source', source_revision_id: 'source-revision', outcome: 'enough',
        content_sha256: hash(text), line_start: 1, line_end: 1, returned_chars: [...text].length,
        truncated: false, evidence_sufficiency_status: 'sufficient'} } ] };
}
function response(c: WorldBuildGraphCompletionV2, index = 0): AgentSourcePassageReadResponseV1 {
  return {schema: 'dmb_agent_source_passage_read_v1', target: {
    schema: 'dmb_agent_source_passage_open_target_v1', kind: 'source_passage',
    world_id: 'world', turn_id: id, citation_index: index}, citation: c.source_citations[index]!, content: text};
}
beforeEach(() => { vi.resetAllMocks(); vi.stubGlobal('crypto', webcrypto); });
describe('source-only evidence', () => {
  it('requires an explicit read and renders the exact inert Markdown passage', async () => {
    const c = completion(); load.mockResolvedValue(response(c));
    render(<BuildSourcePassageEvidence completion={c} worldId="world" turnId={id} />);
    expect(load).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole('button', {name: 'Read passage 1'}));
    await screen.findByText('western gate');
    expect(load).toHaveBeenCalledWith('world', id, 0);
    expect(screen.getByText('western gate').tagName).toBe('STRONG');
    fireEvent.click(screen.getByRole('button', {name: 'Close passage'}));
    expect(screen.queryByLabelText('Opened source passage')).toBeNull();
  });
  it.each(['body', 'world', 'citation', 'index', 'error'])('refuses %s corruption without replacement', async failure => {
    const c = completion(), r = response(c);
    if (failure === 'body') r.content = 'x'.repeat([...text].length);
    if (failure === 'world') r.target.world_id = 'other';
    if (failure === 'citation') r.citation = {...r.citation, envelope_sha256: 'f'.repeat(64)};
    if (failure === 'index') r.target.citation_index = 1;
    if (failure === 'error') load.mockRejectedValue(new Error('missing')); else load.mockResolvedValue(r);
    render(<BuildSourcePassageEvidence completion={c} worldId="world" turnId={id} />);
    fireEvent.click(screen.getByRole('button', {name: 'Read passage 1'}));
    await screen.findByText(/No newer text has been substituted/);
    expect(screen.queryByText('western gate')).toBeNull();
  });
  it('deduplicates repeated receipts and exposes all unique passages', () => {
    const c = completion(), first = c.source_citations[0]!;
    c.source_citations = [first, ...Array.from({length: 10}, (_, i) => ({...first,
      read_event_id: `${String(i).padStart(8,'0')}-1111-4111-8111-111111111111`,
      receipt: {...first.receipt, source_artifact_id: `source-${i}`}})), {...first}];
    render(<BuildSourcePassageEvidence completion={c} worldId="world" turnId={id} />);
    expect(screen.getAllByRole('button', {name: /Read passage/})).toHaveLength(8);
    fireEvent.click(screen.getByRole('button', {name: 'Show more passages'}));
    expect(screen.getAllByRole('button', {name: /Read passage/})).toHaveLength(11);
  });
  it('discards a late read after the World or turn changes', async () => {
    const c = completion(); let resolve!: (r: AgentSourcePassageReadResponseV1) => void;
    load.mockImplementation(() => new Promise(r => {resolve = r;}));
    const {rerender} = render(<BuildSourcePassageEvidence completion={c} worldId="world" turnId={id} />);
    fireEvent.click(screen.getByRole('button', {name: 'Read passage 1'}));
    rerender(<BuildSourcePassageEvidence completion={c} worldId="other-world" turnId={id} />);
    await act(async () => resolve(response(c)));
    expect(screen.queryByLabelText('Opened source passage')).toBeNull();
  });
  it('keeps the existing separate Prompt tab', () => {
    render(<ResponseEvidenceTabs evidence={<BuildSourcePassageEvidence completion={completion()} worldId="world" turnId={id} />}
      prompt={<p>Exact saved request</p>} />);
    fireEvent.click(screen.getByRole('tab', {name: 'The Prompt'}));
    expect(screen.getByText('Exact saved request')).toBeInTheDocument();
    expect(load).not.toHaveBeenCalled();
  });
  it('strictly validates source attribution and rejects Graph masquerading', () => {
    const c = completion(), valid = (v: unknown) => isBuildSourceCompletion(v, 'a'.repeat(64), 'b'.repeat(64));
    expect(valid(c)).toBe(true);
    expect(valid({...c, citation_map: {entries: []}})).toBe(false);
    expect(valid({...c, source_citations: []})).toBe(false);
    expect(valid({...c, context_receipt_sha256: 'f'.repeat(64)})).toBe(false);
    expect(valid({...c, answer_segments: [{kind: 'graph_claim', text: 'invented'}]})).toBe(false);
    expect(valid({...c, answer_context_status: 'source_insufficient_evidence'})).toBe(false);
    expect(valid({...c, source_citations: [{...c.source_citations[0], extra: 'forged'}]})).toBe(false);
  });
});

it.each(['plan','play'] as const)('opens a named source citation for %s using the shared component',async surface=>{
  const c:SurfaceSourceCompletionV1={...completion(),schema:'dmb_surface_source_completion_v1',surface_id:surface,
    answer_basis:'opened_source_passages',answer_context_status:'source_grounded',
    answer_segments:[{kind:'source_passage_claim',text:'Frank believes the gate is haunted.'}],
    source_citations:completion().source_citations.map(c=>({...c,source_name:'Gatekeepers journal'}))};
  expect(isSurfaceSourceCompletion(c,'a'.repeat(64),surface)).toBe(true);
  expect(isSurfaceSourceCompletion(c,'a'.repeat(64),surface==='plan'?'play':'plan')).toBe(false);
  load.mockResolvedValue({schema:'dmb_agent_source_passage_read_v1',target:{schema:'dmb_agent_source_passage_open_target_v1',
    kind:'source_passage',world_id:'world',turn_id:id,citation_index:0},citation:c.source_citations[0]!,content:text});
  render(<BuildSourcePassageEvidence completion={c} worldId="world" turnId={id}/>);
  fireEvent.click(screen.getByRole('button',{name:'Read Gatekeepers journal · lines 1–1'}));
  await screen.findByText('western gate');expect(load).toHaveBeenCalledWith('world',id,0);
});
