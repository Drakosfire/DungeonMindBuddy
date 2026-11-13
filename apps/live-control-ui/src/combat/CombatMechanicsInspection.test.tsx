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

const loader = vi.hoisted(() => ({ fail: false }));
vi.mock("../ui/deferredComponent", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../ui/deferredComponent")>();
  const deferredComponent: typeof actual.deferredComponent = (load, label) =>
    actual.deferredComponent(async () => {
      if (loader.fail) throw new Error("Synthetic mechanics load failure");
      return load();
    }, label);
  return { deferredComponent };
});

it("retries the saved display without disturbing encounter input or fetching", async () => {
  const user = userEvent.setup();
  const fetch = vi.spyOn(globalThis, "fetch").mockRejectedValue(new Error("Offline"));
  vi.spyOn(console, "error").mockImplementation(() => {});
  loader.fail = true;
  const snapshot = { resource: fixture } as unknown as CombatMechanicsSnapshot;
  render(<><label>Encounter notes<input /></label><CombatMechanicsInspection snapshot={snapshot} /></>);
  await user.click(screen.getByText("Saved mechanics · Ironhide Brute"));
  const retry = await screen.findByRole("button", { name: "Retry mechanics display" });
  await user.type(screen.getByRole("textbox", { name: "Encounter notes" }), "Pending note");
  loader.fail = false;
  await user.click(retry);
  expect(await screen.findByRole("heading", { name: "Ironhide Brute" })).toBeVisible();
  expect(screen.getByRole("textbox", { name: "Encounter notes" })).toHaveValue("Pending note");
  expect(fetch).not.toHaveBeenCalled();
});
