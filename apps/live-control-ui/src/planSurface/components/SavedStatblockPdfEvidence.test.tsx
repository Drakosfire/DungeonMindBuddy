import { fireEvent, render, screen } from '@testing-library/react';
import { expect, it, vi } from 'vitest';
import type { SavedStatblockPdfSources } from '../../api/conversationLibraryApi';
import { inspectNativeGraph } from '../../api/liveApi';
import type { NativeGraphSource } from '../../api/nativeGraphInspection';
import { SavedStatblockPdfEvidence } from './SavedStatblockPdfEvidence';

vi.mock('../../api/liveApi', () => ({ inspectNativeGraph: vi.fn() }));

const evidenceId = 'ev:' + 'a'.repeat(64);
const selection = { assertion_id: 'assertion:reviewed', evidence_ref_id: evidenceId };
const scope: SavedStatblockPdfSources['scope'] = {
  managed_world_id: 'world',
  native_world_id: 'native',
  binding_version: 1,
  revision_id: 'rev:reviewed',
  scope_mode: 'world',
  campaign_id: null,
};

it.each(['exact', 'different evidence', 'different revision'])(
  'reopens a reviewed passage only for the exact pin and evidence ID (%s)',
  async (result) => {
    const source: NativeGraphSource['source'] & { evidence_ref_id: string } = {
      evidence_ref_id: result === 'different evidence' ? 'ev:' + 'b'.repeat(64) : evidenceId,
      status: 'available',
      text: 'The stored reviewed passage.',
      source_artifact_id: 'src:reviewed',
      source_revision_id: 'srev:reviewed',
      body_sha256: 'a'.repeat(64),
      span_sha256: 'a'.repeat(64),
      span_start_byte: 0,
      span_end_byte: 28,
      source_authority_epoch: 1,
    };
    vi.mocked(inspectNativeGraph).mockClear().mockResolvedValue({
      schema: 'dmb_native_graph_source_v1',
      scope: result === 'different revision' ? { ...scope, revision_id: 'rev:other' } : scope,
      source,
    });
    render(<SavedStatblockPdfEvidence sources={{ scope, support: [selection] }} />);
    fireEvent.click(screen.getByText('Reviewed statblock sources'));
    fireEvent.click(screen.getByRole('button', { name: 'Open stored passage 1' }));
    if (result === 'exact') {
      await screen.findByText(source.text);
    } else {
      await screen.findByText(/The exact cited passage is unavailable/);
      expect(screen.queryByText(source.text)).toBeNull();
    }
    expect(inspectNativeGraph).toHaveBeenCalledWith(scope, { kind: 'source', ...selection });
  },
);

it('does not offer a raw PDF read for a historical locator', () => {
  vi.mocked(inspectNativeGraph).mockClear();
  render(<SavedStatblockPdfEvidence sources={{
    scope,
    support: [{ ...selection, evidence_ref_id: 'pdf-region:historical' }],
  }} />);
  fireEvent.click(screen.getByText('Reviewed statblock sources'));
  expect(screen.getByText(/unavailable in stored text/)).toBeVisible();
  expect(screen.queryByRole('button')).toBeNull();
  expect(inspectNativeGraph).not.toHaveBeenCalled();
});
