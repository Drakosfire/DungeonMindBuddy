import { act, fireEvent, render, screen } from '@testing-library/react';
import { expect, it, vi } from 'vitest';
import type { LibraryTurns } from '../api/conversationLibraryApi';
import { readRetryAttempts, type TurnRetryContext } from '../api/conversationRetryApi';
import { ConversationRetryAttempts } from './ConversationRetryAttempts';

vi.mock('../api/conversationRetryApi', () => ({ readRetryAttempts: vi.fn() }));

it('keeps the current request loading when an earlier request for the same turn resolves', async () => {
  const context: TurnRetryContext = {
    world_id: 'world', conversation_id: 'conversation', turn_id: 'A', root_id: 'root',
    revision: 1, ordinal: 1, predecessor_id: 'previous', successor_id: null,
    eligible: false, reason: 'retried',
  };
  const pending: { signal: AbortSignal; resolve: (page: LibraryTurns) => void }[] = [];
  vi.mocked(readRetryAttempts).mockImplementation((_world, _conversation, _turn, _before, signal) =>
    new Promise(resolve => pending.push({ signal: signal!, resolve })));
  const { container, rerender, unmount } = render(<ConversationRetryAttempts context={context} />);
  const panel = container.querySelector('details')!;
  const open = () => {
    panel.open = true;
    fireEvent(panel, new Event('toggle'));
  };

  open();
  rerender(<ConversationRetryAttempts context={{ ...context, turn_id: 'B' }} />);
  open();
  rerender(<ConversationRetryAttempts context={context} />);
  open();
  expect(pending.map(request => request.signal.aborted)).toEqual([true, true, false]);

  await act(async () => pending[0].resolve({
    schema: 'dmb_conversation_library_turns_v3', world_id: 'world',
    conversation_id: 'conversation', turns: [], next_before_sequence: null,
  }));
  expect(screen.getByText('Loading previous attempts…')).toBeVisible();
  unmount();
  expect(pending[2].signal.aborted).toBe(true);
});
