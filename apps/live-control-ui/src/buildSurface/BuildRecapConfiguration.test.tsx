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
