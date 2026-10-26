import {createHash,webcrypto} from 'node:crypto';
import {cleanup,fireEvent,render,screen,waitFor,act} from '@testing-library/react';
import {afterEach,beforeEach,expect,it,vi} from 'vitest';
import {ConversationConnectedPageReview,connectedReviewOrigin} from './ConversationConnectedPageReview';
import {publishConnectedPageReviewHost} from '../../buildSurface/connectedPageReviewHost';
import {getAgentConnectedPageOrigin} from '../../api/liveApi';
vi.mock('../../api/liveApi',()=>({getAgentConnectedPageOrigin:vi.fn()}));
const id='11111111-1111-4111-8111-111111111111';
const proposal={kind:'connected_page' as const,title:'Copper Workshop',read_id:id,quote:'Copper House | Repair lantern',person_label:null,relationships:[],instructions:'Practical workshop'};
const body='# Table\n\n| Name | Task |\n| --- | --- |\n| Copper House | Repair lantern |\n';
const value=()=>({schema:'dmb_agent_connected_page_origin_v1',world_id:'world',turn_id:'turn',read_id:id,origin:{kind:'saved_page_excerpt',document_id:id,revision:7,content_sha256:createHash('sha256').update(body).digest('hex'),line_start:5,line_end:5,selected_text:'| Copper House | Repair lantern |'}});
let retire=()=>{};
beforeEach(()=>{vi.clearAllMocks();vi.stubGlobal('crypto',webcrypto);});
afterEach(()=>{cleanup();retire();});
it('opens only the exact source-bound read and derives actual full lines without writing',async()=>{
 const open=vi.fn();retire=publishConnectedPageReviewHost({worldId:'world',documentId:'current',open});vi.mocked(getAgentConnectedPageOrigin).mockResolvedValue(value());
 render(<ConversationConnectedPageReview worldId='world' documentId='current' turnId='turn' proposal={proposal} disabled={false}/>);
 expect(getAgentConnectedPageOrigin).not.toHaveBeenCalled();fireEvent.click(screen.getByRole('button',{name:'Review new page'}));
 await waitFor(()=>expect(open).toHaveBeenCalledTimes(1));expect(open.mock.calls[0][0]).toMatchObject({ownerDocumentId:'current',origin:{document_id:id,revision:7,line_start:5,line_end:5,selected_text:'| Copper House | Repair lantern |'}});
});
it('refuses wrong scope, changed bytes, absent and ambiguous quote',async()=>{
 for(const raw of [{...value(),turn_id:'other'},{...value(),origin:{...value().origin,selected_text:'Changed text'}},{...value(),read_id:'other'}])await expect(connectedReviewOrigin(raw,'world','turn',proposal)).rejects.toThrow();
 await expect(connectedReviewOrigin(value(),'world','turn',{...proposal,quote:'missing'})).rejects.toThrow('exact saved occurrence');
 await expect(connectedReviewOrigin(value(),'world','turn',{...proposal,quote:'|'})).rejects.toThrow('exact saved occurrence');
});
it('retires late source acquisition across a host round trip',async()=>{
 const old=vi.fn(),next=vi.fn();retire=publishConnectedPageReviewHost({worldId:'world',documentId:'current',open:old});let finish!:(v:unknown)=>void;vi.mocked(getAgentConnectedPageOrigin).mockReturnValue(new Promise(r=>{finish=r;}));
 render(<ConversationConnectedPageReview worldId='world' documentId='current' turnId='turn' proposal={proposal} disabled={false}/>);fireEvent.click(screen.getByRole('button',{name:'Review new page'}));
 act(()=>{retire();retire=publishConnectedPageReviewHost({worldId:'world',documentId:'other',open:next});retire();retire=publishConnectedPageReviewHost({worldId:'world',documentId:'current',open:next});});
 await act(async()=>{finish(value());});expect(old).not.toHaveBeenCalled();expect(next).not.toHaveBeenCalled();
});
