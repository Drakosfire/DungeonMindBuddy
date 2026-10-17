import { fireEvent,render,screen,waitFor } from '@testing-library/react';
import { describe,it,expect,vi } from 'vitest';
import { PreparedBuildImage,type PreparedImage } from './PreparedBuildImage';
import type { CapturedBuildInsertion } from '../buildSurface/buildComposeBridge';
const id='ac6c15cc-8c68-4732-8ae2-d9f3f051393a';
const fixture=vi.hoisted(()=>({calls:[] as string[],selected:{} as Record<string,unknown>}));
vi.mock('../api/liveApi',()=>({authenticatedApiFetch:vi.fn(async(path:string,init?:RequestInit)=>{
 fixture.calls.push((init?.method??'GET')+' '+path);
 if(path.includes('/preparations/')&&path.endsWith('/asset'))return{response:new Response(JSON.stringify({...fixture.selected,asset_id:id,revision:2}))};
 if(path.includes('/preparations/'))return{response:new Response(JSON.stringify(fixture.selected))};
 if(path.endsWith('/capabilities'))return{response:new Response(JSON.stringify({configured:true,library_ready:true,storage_configured:true,models:[{id:'flux-2-pro',label:'FLUX',formats:['png'],controls:[]}]}))};
 if(path.endsWith('/generate'))return{response:new Response(JSON.stringify({prompt:'Prepared Edge',model:'flux-2-pro',images:[{asset_id:id,state:'staged',data_url:'data:image/png;base64,AA==',media_type:'image/png'}]}))};
 return{response:new Response(JSON.stringify({asset_id:id,state:'ready',delivery_url:'https://imagedelivery.net/test/buddy-'+id.replaceAll('-','')+'/public'}))};
})}));
function setup(){
 fixture.calls=[];
 const basis={world_id:'elderwyld',document_id:'edge',registry_revision:1,content_sha256:'a'.repeat(64),visibility:'internal' as const,draft_sha256:'b'.repeat(64),caret:1,draft_generation:0,selection_generation:0};
 const record:PreparedImage={schema_version:'dmb_build_image_preparation_v2',action_id:'action',prompt:'Prepared Edge',alt:'Edge at dusk',revision:1,asset_id:null,created_at:'2020-01-01T00:00:00Z',after_turn_sequence:1,reservation:{conversation_id:'conv',expected_pointer_revision:1,basis}};
 fixture.selected=record;
 const captured={basis,draftMarkdown:'Edge',editorJson:'{}'} as CapturedBuildInsertion;
 const bridge={capture:vi.fn().mockResolvedValue(captured),insert:vi.fn()};return{record,bridge,captured};
}
describe('prepared image conversation action',()=>{
 it('prefills without generation, then generates, saves and explicitly inserts',async()=>{
  const {record,bridge,captured}=setup();render(<PreparedBuildImage record={record} bridge={bridge} active/>);
  fireEvent.click(screen.getByRole('button',{name:'Open Image Studio'}));
  expect(await screen.findByLabelText('What would you like to see?')).toHaveValue('Prepared Edge');
  expect(fixture.calls.some(item=>item.includes('/generate'))).toBe(false);
  fireEvent.click(screen.getByRole('button',{name:/Choose model/}));
  fireEvent.click(screen.getByRole('button',{name:'Generate image'}));
  fireEvent.click(await screen.findByRole('button',{name:'Save image'}));
  fireEvent.click(await screen.findByRole('button',{name:'Insert into page'}));
  await screen.findByText('Image inserted into your draft. Save the page when ready.');
  expect(bridge.insert).toHaveBeenCalledWith(captured,`![Edge at dusk](dmb-media:${id})`);
  expect(fixture.calls.filter(item=>item.includes('/generate'))).toHaveLength(1);
 });
 it('disables archived action and refuses another page',async()=>{
  const {record,bridge}=setup();const view=render(<PreparedBuildImage record={record} bridge={bridge} active={false}/>);
  expect(screen.getByRole('button',{name:'Open Image Studio'})).toBeDisabled();
  bridge.capture.mockResolvedValue({basis:{...record.reservation.basis,document_id:'other'}});
  view.rerender(<PreparedBuildImage record={record} bridge={bridge} active/>);
  fireEvent.click(screen.getByRole('button',{name:'Open Image Studio'}));
  await waitFor(()=>expect(screen.getByRole('alert')).toHaveTextContent('Open the page used'));
  expect(bridge.insert).not.toHaveBeenCalled();
 });
});
