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

it('opens the exact snapshot outside the table and closes back to its trigger', async () => {
  loader.fail = false;
  Object.defineProperty(HTMLDialogElement.prototype, 'showModal', {configurable:true,value:function(this:HTMLDialogElement){this.setAttribute('open','');}});
  Object.defineProperty(HTMLDialogElement.prototype, 'close', {configurable:true,value:function(this:HTMLDialogElement){this.removeAttribute('open');this.dispatchEvent(new Event('close'));}});
  const fetch=vi.spyOn(globalThis,'fetch').mockRejectedValue(new Error('Offline'));
  const view=render(<table><tbody><tr><td><CombatMechanicsInspection presentation="dialog" snapshot={{resource:fixture} as unknown as CombatMechanicsSnapshot}/></td></tr></tbody></table>);
  const trigger=screen.getByRole('button',{name:'Saved mechanics · Ironhide Brute'});
  await userEvent.click(trigger);
  const dialog=screen.getByRole('dialog',{name:'Saved mechanics · Ironhide Brute'});
  expect(dialog.closest('table')).toBeNull();
  expect(await screen.findByRole('heading',{name:'Ironhide Brute'})).toBeVisible();
  await userEvent.click(screen.getByRole('button',{name:'Close statblock'}));
  expect(screen.queryByRole('dialog')).toBeNull();
  expect(trigger).toHaveFocus();
  await userEvent.click(trigger);view.unmount();
  expect(screen.queryByRole('dialog')).toBeNull();expect(fetch).not.toHaveBeenCalled();
});
