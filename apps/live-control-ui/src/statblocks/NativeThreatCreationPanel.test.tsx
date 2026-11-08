import {webcrypto} from 'node:crypto';
import {act,cleanup,render,screen,waitFor} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {beforeEach,afterEach,expect,it,vi} from 'vitest';
import * as api from '../api/liveApi';
import type {ThreatDraftV2} from '../api/types';
import {threatPacket,threatCreated,threatDraftId} from '../test/nativeThreatCreationFixture';
import {NativeThreatCreationPanel} from './NativeThreatCreationPanel';
const draft={world_id:'elderwyld',draft_id:threatDraftId,version:3} as ThreatDraftV2;
const key=`dmb.nativeThreat.review:${draft.world_id}:${draft.draft_id}`;
beforeEach(()=>{
 localStorage.clear();vi.stubGlobal('crypto',webcrypto);
 Object.defineProperty(navigator,'locks',{configurable:true,value:{request:vi.fn(async(_name:string,action:()=>unknown)=>action())}});
 vi.spyOn(api,'prepareNativeThreat');vi.spyOn(api,'confirmNativeThreat');vi.spyOn(api,'getNativeThreat');
});
afterEach(()=>{cleanup();vi.restoreAllMocks();vi.unstubAllGlobals();});
it('requires explicit review and confirmation and persists before the write',async()=>{
 const packet=await threatPacket();vi.mocked(api.prepareNativeThreat).mockResolvedValue(packet);
 vi.mocked(api.confirmNativeThreat).mockImplementation(async value=>{expect(JSON.parse(localStorage.getItem(key)!)).toEqual(value);return threatCreated();});
 render(<NativeThreatCreationPanel draft={draft}/>);expect(api.prepareNativeThreat).not.toHaveBeenCalled();expect(api.getNativeThreat).not.toHaveBeenCalled();
 await userEvent.click(screen.getByRole('button',{name:'Review creature creation'}));await screen.findByRole('heading',{name:'Rolling ooze'});
 expect(screen.getByText(packet.source_text,{normalizer:value=>value})).toBeInTheDocument();expect(api.confirmNativeThreat).not.toHaveBeenCalled();
 await userEvent.click(screen.getByRole('button',{name:'Create proposed creature'}));await screen.findByText(/Creature created in the World Graph/);
 expect(api.confirmNativeThreat).toHaveBeenCalledExactlyOnceWith(packet);expect(localStorage.getItem(key)).toBeNull();
});
it('retains and resumes the exact review after a lost acknowledgement and remount',async()=>{
 const packet=await threatPacket();vi.mocked(api.prepareNativeThreat).mockResolvedValue(packet);
 vi.mocked(api.confirmNativeThreat).mockRejectedValueOnce(new Error('Lost acknowledgement')).mockResolvedValueOnce({...threatCreated(),replayed:true});
 const view=render(<NativeThreatCreationPanel draft={draft}/>);await userEvent.click(screen.getByRole('button',{name:'Review creature creation'}));await screen.findByRole('heading',{name:'Rolling ooze'});await userEvent.click(screen.getByRole('button',{name:'Create proposed creature'}));await screen.findByRole('alert');const original=localStorage.getItem(key);
 view.unmount();render(<NativeThreatCreationPanel draft={draft}/>);await screen.findByRole('heading',{name:'Rolling ooze'});await userEvent.click(screen.getByRole('button',{name:'Create proposed creature'}));await screen.findByText(/Creature created in the World Graph/);
 expect(api.confirmNativeThreat).toHaveBeenNthCalledWith(2,JSON.parse(original!));expect(api.prepareNativeThreat).toHaveBeenCalledTimes(1);
});
it('keeps malformed retained text and blocks confirmation',async()=>{
 const packet=await threatPacket();packet.source_text='Tampered display';const raw=JSON.stringify(packet);localStorage.setItem(key,raw);
 render(<NativeThreatCreationPanel draft={draft}/>);await screen.findByRole('alert');expect(screen.queryByRole('button',{name:'Create proposed creature'})).toBeNull();expect(screen.getByRole('button',{name:'Review creature creation'})).toBeDisabled();expect(localStorage.getItem(key)).toBe(raw);expect(api.confirmNativeThreat).not.toHaveBeenCalled();
});
it('does not overwrite another view’s stored review during prepare',async()=>{
 let finish!:(value:Awaited<ReturnType<typeof threatPacket>>)=>void;
 vi.mocked(api.prepareNativeThreat).mockImplementation(()=>new Promise(resolve=>{finish=resolve}));render(<NativeThreatCreationPanel draft={draft}/>);
 await userEvent.click(screen.getByRole('button',{name:'Review creature creation'}));await waitFor(()=>expect(api.prepareNativeThreat).toHaveBeenCalledTimes(1));localStorage.setItem(key,'foreign retained review');
 await act(async()=>finish(await threatPacket()));expect(await screen.findByRole('alert')).toHaveTextContent('Another view');expect(localStorage.getItem(key)).toBe('foreign retained review');expect(api.confirmNativeThreat).not.toHaveBeenCalled();
});
it('ignores a late preparation after switching World/draft',async()=>{
 let finish!:(value:Awaited<ReturnType<typeof threatPacket>>)=>void;
 vi.mocked(api.prepareNativeThreat).mockImplementation(()=>new Promise(resolve=>{finish=resolve}));const view=render(<NativeThreatCreationPanel draft={draft}/>);await userEvent.click(screen.getByRole('button',{name:'Review creature creation'}));
 view.rerender(<NativeThreatCreationPanel draft={{...draft,world_id:'other-world',draft_id:'22222222-2222-4222-8222-222222222222'}}/>);
 await act(async()=>finish(await threatPacket()));expect(screen.queryByRole('heading',{name:'Rolling ooze'})).toBeNull();expect(localStorage.getItem(key)).toBeNull();expect(api.confirmNativeThreat).not.toHaveBeenCalled();
});
it('reads an existing committed result without preparing or confirming again',async()=>{
 vi.mocked(api.getNativeThreat).mockResolvedValue({...threatCreated(),replayed:true});render(<NativeThreatCreationPanel draft={draft}/>);
 await userEvent.click(screen.getByRole('button',{name:'Check existing creature'}));await screen.findByText(/Creature created in the World Graph/);expect(api.prepareNativeThreat).not.toHaveBeenCalled();expect(api.confirmNativeThreat).not.toHaveBeenCalled();
});
it('keeps a stale review until explicit fresh preparation succeeds',async()=>{
 const packet=await threatPacket();vi.mocked(api.prepareNativeThreat).mockResolvedValueOnce(packet).mockResolvedValueOnce({...threatCreated(),replayed:true});vi.mocked(api.confirmNativeThreat).mockRejectedValue(new api.LiveApiError('Draft changed',409));
 render(<NativeThreatCreationPanel draft={draft}/>);await userEvent.click(screen.getByRole('button',{name:'Review creature creation'}));await screen.findByRole('heading',{name:'Rolling ooze'});await userEvent.click(screen.getByRole('button',{name:'Create proposed creature'}));await screen.findByRole('alert');expect(localStorage.getItem(key)).not.toBeNull();
 await userEvent.click(screen.getByRole('button',{name:'Prepare a new review'}));await screen.findByText(/Creature created in the World Graph/);expect(localStorage.getItem(key)).toBeNull();
});
