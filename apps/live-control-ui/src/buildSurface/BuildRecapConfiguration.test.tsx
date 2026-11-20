import {cleanup,fireEvent,render,screen,waitFor} from '@testing-library/react';
import {afterEach,beforeEach,expect,it,vi} from 'vitest';
import {useState} from 'react';
import {BuildRecapConfiguration} from './BuildRecapConfiguration';
import * as evidenceApi from '../playSurface/review/sessionEvidenceApi';
beforeEach(()=>{localStorage.clear();vi.spyOn(evidenceApi,'listSessionEvidence').mockResolvedValue([]);vi.spyOn(evidenceApi,'readSessionEvidence').mockRejectedValue(new Error('must choose explicitly'));});
afterEach(()=>{cleanup();vi.restoreAllMocks();});
function Harness(){const [campaign,setCampaign]=useState(''),[session,setSession]=useState('');return <BuildRecapConfiguration documentId="doc-a" worldId="world-a"
 campaignId={campaign} session={session} evidence={[]} onCampaign={setCampaign} onSession={setSession} onEvidence={()=>undefined} disabled={false}/>;}
it('reads the World session index once while campaign/session inputs change',async()=>{
 render(<Harness/>);await waitFor(()=>expect(evidenceApi.listSessionEvidence).toHaveBeenCalledExactlyOnceWith('world-a'));
 fireEvent.change(screen.getByLabelText('Recap source campaign'),{target:{value:'longmont'}});
 fireEvent.change(screen.getByLabelText('Recap source campaign'),{target:{value:'longmont-c2'}});
 fireEvent.change(screen.getByLabelText('Recap source session'),{target:{value:'3'}});
 fireEvent.change(screen.getByLabelText('Recap source session'),{target:{value:'30'}});
 expect(evidenceApi.listSessionEvidence).toHaveBeenCalledTimes(1);expect(evidenceApi.readSessionEvidence).not.toHaveBeenCalled();
});

const loader = vi.hoisted(() => ({ fail: false }));
vi.mock("../ui/deferredComponent", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../ui/deferredComponent")>();
  const deferredComponent: typeof actual.deferredComponent = (load, label) =>
    actual.deferredComponent(async () => {
      if (loader.fail) throw new Error("Synthetic evidence load failure");
      return load();
    }, label);
  return { deferredComponent };
});

it("retains recap inputs when session evidence fails and is retried", async () => {
  loader.fail = true;
  vi.spyOn(console, "error").mockImplementation(() => {});
  render(<Harness />);
  const retry = await screen.findByRole("button", { name: "Retry session evidence" });
  fireEvent.change(screen.getByLabelText("Recap source campaign"), { target: { value: "longmont" } });
  fireEvent.change(screen.getByLabelText("Recap source session"), { target: { value: "3" } });
  expect(evidenceApi.listSessionEvidence).not.toHaveBeenCalled();
  loader.fail = false;
  fireEvent.click(retry);
  await waitFor(() => expect(evidenceApi.listSessionEvidence).toHaveBeenCalledExactlyOnceWith("world-a"));
  expect(screen.getByLabelText("Recap source campaign")).toHaveValue("longmont");
  expect(screen.getByLabelText("Recap source session")).toHaveValue(3);
});
