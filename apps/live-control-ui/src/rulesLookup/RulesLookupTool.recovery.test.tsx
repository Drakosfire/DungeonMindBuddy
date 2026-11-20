import {act,cleanup,fireEvent,render,screen,waitFor} from '@testing-library/react';
import {afterEach,beforeEach,expect,it,vi} from 'vitest';
import {createHash,webcrypto} from 'node:crypto';
import RulesLookupTool from './RulesLookupTool';
import {ensureNativeGraphSession,setNativeGraphAccessToken} from '../api/liveApi';

const corpus='a'.repeat(64),text='You cannot willingly end a move in another creature’s space.';
const hit={corpus,citation_id:'b'.repeat(64),ruleset_id:'dnd_2024',unit_id:'c'.repeat(64),text_sha256:createHash('sha256').update(text).digest('hex'),section:'Occupancy',source_title:'SRD 5.2.1',source_uri:'https://example.invalid/source.pdf',source_sha256:'d'.repeat(64),page_fingerprint:'e'.repeat(64),pdf_page_index:13,printed_page:14,excerpt:text,excerpt_start:0,excerpt_end:text.length,excerpt_complete:true};
const catalog={schema:'dmb_rules_catalog_v1',sources:[{corpus,available:true,ruleset_id:'dnd_2024',title:'SRD 5.2.1',coverage:'One section only.',unit_count:1}]};
const packet={schema:'dmb_rules_lookup_packet_v1',corpus,ruleset_id:'dnd_2024',query_id:'f'.repeat(64),normalized_query:'prone',status:'evidence',coverage:'One section only.',coverage_status:'limited',hits:[hit],additional_matches:false};
beforeEach(()=>{vi.stubGlobal('crypto',webcrypto);setNativeGraphAccessToken('reset-rules-token');setNativeGraphAccessToken(null)});
afterEach(()=>{cleanup();vi.restoreAllMocks();vi.unstubAllGlobals()});
async function ask(){await screen.findByRole('combobox');await act(async()=>{fireEvent.change(screen.getByRole('textbox',{name:'Rules question'}),{target:{value:'prone'}});fireEvent.click(screen.getByRole('button',{name:'Look up rules'}))})}
function transport(stage:'catalog'|'query'|'inspect'|'none',recoveryStatus=503){
 let sessions=0,rejected=false;
 const calls:string[]=[];
 vi.spyOn(globalThis,'fetch').mockImplementation(async input=>{
  const path=String(input);calls.push(path);
  if(path.includes('/agent/local-session')){
   sessions++;
   return sessions===2&&recoveryStatus===503?Response.json({detail:'unavailable'},{status:503}):Response.json({status:'active',csrf_token:'csrf-'+sessions});
  }
  const target=stage==='inspect'?path.includes('/rules/passages/'):path.includes('/rules/'+stage);
  if(target&&!rejected){rejected=true;return Response.json({detail:{code:'graph_auth_required'}},{status:401})}
  if(path.includes('/rules/catalog'))return Response.json(catalog);
  if(path.includes('/rules/query'))return Response.json(packet);
  if(path.includes('/rules/passages/'))return Response.json({...hit,schema:'dmb_rules_passage_v1',text,attribution:'Public source attribution'});
  throw Error('Unexpected request '+path);
 });
 return {calls,get sessions(){return sessions}};
}
it.each(['catalog','query','inspect'] as const)('settles %s after warm CSRF → trusted401 → recovery503 and allows explicit reload',async stage=>{
 const wire=transport(stage);await ensureNativeGraphSession();render(<RulesLookupTool/>);
 if(stage!=='catalog')await ask();
 if(stage==='inspect')await act(async()=>fireEvent.click(screen.getByRole('button',{name:'Inspect cited passage'})));
 expect(await screen.findByRole('alert')).toHaveTextContent('Local session recovery failed');
 expect(screen.queryByText('Reading rules evidence…')).not.toBeInTheDocument();
 expect(screen.queryByRole('button',{name:'Inspect cited passage'})).not.toBeInTheDocument();
 expect(wire.sessions).toBe(2);
 await act(async()=>fireEvent.click(screen.getByRole('button',{name:'Reload rules sources'})));
 await screen.findByRole('combobox');await ask();
 expect(await screen.findByRole('button',{name:'Inspect cited passage'})).toBeEnabled();expect(wire.sessions).toBe(3);
});
it('successful query recovery retires the old replay and waits for an explicit fresh lookup',async()=>{
 const wire=transport('query',200);await ensureNativeGraphSession();render(<RulesLookupTool/>);await ask();
 await screen.findByRole('button',{name:'Reload rules sources'});
 expect(wire.calls.filter(path=>path.includes('/rules/query'))).toHaveLength(1);
 await act(async()=>fireEvent.click(screen.getByRole('button',{name:'Reload rules sources'})));await screen.findByRole('combobox');await ask();
 await screen.findByRole('button',{name:'Inspect cited passage'});
 expect(wire.calls.filter(path=>path.includes('/rules/query'))).toHaveLength(2);expect(wire.sessions).toBe(2);
});

it('does not admit a late response body after access rotation',async()=>{
 const wire=transport('none');const original=vi.mocked(fetch).getMockImplementation()!;
 let release!:()=>void;
 const stream=new ReadableStream<Uint8Array>({start(controller){release=()=>{controller.enqueue(new TextEncoder().encode(JSON.stringify(packet)));controller.close()}}});
 vi.mocked(fetch).mockImplementation(async(input,init)=>String(input).includes('/rules/query')?new Response(stream,{headers:{'Content-Type':'application/json'}}):original(input,init));
 await ensureNativeGraphSession();render(<RulesLookupTool/>);await ask();
 await act(async()=>{setNativeGraphAccessToken('rotated-rules-token');release()});
 await screen.findByRole('button',{name:'Reload rules sources'});
 expect(screen.queryByRole('button',{name:'Inspect cited passage'})).not.toBeInTheDocument();
 expect(screen.queryByText('Reading rules evidence…')).not.toBeInTheDocument();
});
it('retires exact-passage digest work on access rotation without resurrecting the prior evidence',async()=>{
 transport('none');await ensureNativeGraphSession();render(<RulesLookupTool/>);await ask();
 let resolve!:(value:ArrayBuffer)=>void;
 const digest=vi.fn(()=>new Promise<ArrayBuffer>(done=>{resolve=done}));
 vi.stubGlobal('crypto',{subtle:{digest}});
 await act(async()=>fireEvent.click(screen.getByRole('button',{name:'Inspect cited passage'})));
 await waitFor(()=>expect(digest).toHaveBeenCalledTimes(1));
 await act(async()=>{setNativeGraphAccessToken('rotated-digest-token');resolve(await webcrypto.subtle.digest('SHA-256',new TextEncoder().encode(text)))});
 expect(screen.queryByRole('region',{name:'Cited rules passage'})).not.toBeInTheDocument();
 expect(screen.getByRole('button',{name:'Reload rules sources'})).toBeInTheDocument();
});
