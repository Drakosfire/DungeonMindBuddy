import {fireEvent, render, screen} from '@testing-library/react';
import {expect, it, vi} from 'vitest';
import type {SurfaceNativeCompletionV1} from '../../api/types';
import {authenticatedApiFetch} from '../../api/liveApi';
import {ConversationLorePageConfirmation} from './ConversationLorePageConfirmation';

vi.mock('../../api/liveApi', () => ({authenticatedApiFetch: vi.fn()}));

it('saves only on explicit confirmation and submits the displayed digest', async () => {
  const digest = 'a'.repeat(64);
  const completion: SurfaceNativeCompletionV1 = {
    schema: 'dmb_surface_native_completion_v1',
    surface_id: 'build',
    context_receipt_sha256: 'b'.repeat(64),
    producing_provider_attempt_id: '00000000-0000-4000-8000-000000000001',
    answer_basis: 'mixed_evidence',
    answer_context_status: 'discussion',
    collaboration: {
      kind: 'lore_page',
      destination: {instruction: 'Create a page for Rowan.', title: 'Rowan'},
      open_questions: ['Why did Rowan leave?'],
    },
    answer_segments: [],
    saved_source_citations: [],
    native_body_citations: [],
    native_clause_citations: [],
    native_assertion_citations: [],
  };
  const api = vi.mocked(authenticatedApiFetch);
  api.mockResolvedValueOnce({
    response: Response.json({review_sha256: digest}),
  } as Awaited<ReturnType<typeof authenticatedApiFetch>>);
  api.mockResolvedValueOnce({
    response: Response.json({document_id: 'saved-page', revision_id: 'saved-revision', review_sha256: digest}),
  } as Awaited<ReturnType<typeof authenticatedApiFetch>>);
  render(<ConversationLorePageConfirmation
    worldId="fixture-world" conversationId="fixture-conversation" turnId="fixture-turn"
    completion={completion} digest={async () => digest} disabled={false}
  />);
  expect(screen.getByRole("region", {name: "Open questions"})).toHaveTextContent("Why did Rowan leave?");
  expect(api).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole('button', {name: 'Review save of Rowan'}));
  const confirm = await screen.findByRole('button', {name: 'Confirm save of Rowan'});
  expect(api).toHaveBeenCalledTimes(1);
  expect(String(api.mock.calls[0]?.[0])).toMatch(/lore-pages\/review$/);
  fireEvent.click(confirm);
  expect(await screen.findByRole('link', {name: 'Open saved page'}))
    .toHaveAttribute('href', '/build?world=fixture-world&documentId=saved-page');
  expect(api).toHaveBeenLastCalledWith(
    '/api/live/agent/worlds/fixture-world/conversation/lore-pages/confirm',
    expect.objectContaining({method: 'POST', body: JSON.stringify({
      conversation_id: 'fixture-conversation', turn_id: 'fixture-turn', review_sha256: digest,
    })}),
  );
});
