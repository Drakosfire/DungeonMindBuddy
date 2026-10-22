import {cleanup,render,screen} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {afterEach,expect,it,vi} from 'vitest';
import fixture from '../../../../tests/fixtures/statblocks/v1/exact-revision-response.json';
import type {CombatMechanicsSnapshot} from './combatTypes';
import {CombatMechanicsInspection} from './CombatMechanicsInspection';
afterEach(()=>{cleanup();vi.restoreAllMocks();});
it('renders the saved exact resource on demand without a DMS or Graph request',async()=>{
  const fetch=vi.spyOn(globalThis,'fetch').mockRejectedValue(new Error('Offline'));
  const snapshot={resource:fixture} as unknown as CombatMechanicsSnapshot;
  render(<CombatMechanicsInspection snapshot={snapshot}/>);
  expect(screen.queryByRole('heading',{name:'Ironhide Brute'})).toBeNull();
  await userEvent.click(screen.getByText('Saved mechanics · Ironhide Brute'));
  expect(await screen.findByRole('heading',{name:'Ironhide Brute'})).toBeInTheDocument();
  expect(screen.getAllByText(/Greatclub/).length).toBeGreaterThan(0);expect(fetch).not.toHaveBeenCalled();
});
