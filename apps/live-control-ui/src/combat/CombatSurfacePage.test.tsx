import type {ReactNode} from 'react';
import {act, render, screen} from '@testing-library/react';
import {afterEach, expect, it, vi} from 'vitest';
import {CombatSurfacePage} from './CombatSurfacePage';

const first = '61ad2a39-03be-406f-849c-d6099193a3f9';
const second = '55f30682-e2a2-49a8-9973-a3d06ffe9470';

vi.mock('../chrome/AppChrome', () => ({AppChrome: ({children}: {children: ReactNode}) => children}));
vi.mock('../agentInteraction/usePublishSurfaceInteraction', () => ({usePublishSurfaceInteraction: () => undefined}));
vi.mock('../selectedWorld/SelectedWorldContext', () => ({useSelectedWorld: () => ({kind:'managed',worldId:'elderwyld'})}));
vi.mock('../surface/modules/CombatRosterModule', () => ({
  CombatRosterModule: ({scope, encounterListHref}: {scope?: {worldId: string; encounterId: string}; encounterListHref?: string}) => (
    <div>{scope ? `${scope.worldId} / ${scope.encounterId}` : 'Encounter picker'}
      {encounterListHref && <a href={encounterListHref}>All encounters</a>}
    </div>
  ),
}));

function navigate(url: string) {
  window.history.pushState(null, '', url);
  window.dispatchEvent(new PopStateEvent('popstate'));
}

afterEach(() => window.history.replaceState(null, '', '/'));

it('admits the selected World and updates the scoped encounter with navigation', () => {
  navigate(`/combat?world=elderwyld&encounter=${first}`);
  render(<CombatSurfacePage/>);
  expect(screen.getByText(`elderwyld / ${first}`)).toBeVisible();
  expect(screen.getByRole('link', {name:'All encounters'})).toHaveAttribute('href','/combat?world=elderwyld');

  act(() => navigate(`/combat?world=elderwyld&encounter=${second}`));
  expect(screen.getByText(`elderwyld / ${second}`)).toBeVisible();
  expect(screen.queryByText(`elderwyld / ${first}`)).toBeNull();

  act(() => navigate('/combat?world=elderwyld'));
  expect(screen.getByText('Encounter picker')).toBeVisible();
});

it.each([
  '/combat?world=elderwyld&encounter=malformed',
  `/combat?encounter=${first}`,
  `/combat?world=elderwyld&world=elsewhere&encounter=${first}`,
  `/combat?world=elderwyld&encounter=${first}&encounter=${second}`,
])('rejects an ambiguous or malformed link without mounting the roster', url => {
  navigate(url);
  render(<CombatSurfacePage/>);
  expect(screen.getByRole('alert')).toHaveTextContent('This encounter link is invalid.');
  expect(screen.queryByText('Encounter picker')).toBeNull();
});

it('does not fall back to a different admitted World', () => {
  navigate(`/combat?world=elsewhere&encounter=${first}`);
  render(<CombatSurfacePage/>);
  expect(screen.getByRole('status')).toHaveTextContent('Open this link in its World');
  expect(screen.queryByText('Encounter picker')).toBeNull();
});
