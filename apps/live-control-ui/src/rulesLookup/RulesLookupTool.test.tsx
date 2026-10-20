import {act,fireEvent,render,screen,waitFor,within} from '@testing-library/react';
import {createHash,webcrypto} from 'node:crypto';
import {afterEach,beforeEach,expect,it,vi} from 'vitest';
import RulesLookupTool,{rulesPageLabel} from './RulesLookupTool';
import * as api from '../api/liveApi';
const state=vi.hoisted(()=>({epoch:0}));
vi.mock('../api/liveApi',()=>({NATIVE_GRAPH_ACCESS_TOKEN_CHANGED_EVENT:'rules-access-test',getNativeGraphAccessGeneration:()=>state.epoch,getRulesCatalog:vi.fn(),queryRulesEvidence:vi.fn(),getRulesPassage:vi.fn()}));
const corpus='a'.repeat(64), text='You cannot willingly end a move in another creature’s space.';
const hash=(value:string)=>createHash('sha256').update(value).digest('hex');
const hit={corpus,citation_id:'b'.repeat(64),ruleset_id:'dnd_2024',unit_id:'c'.repeat(64),text_sha256:hash(text),section:'Occupancy',source_title:'SRD 5.2.1',source_uri:'https://example.invalid/source.pdf',source_sha256:'d'.repeat(64),page_fingerprint:'e'.repeat(64),pdf_page_index:13,printed_page:14,excerpt:text,excerpt_start:0,excerpt_end:text.length,excerpt_complete:true};
const catalog={schema:'dmb_rules_catalog_v1',sources:[{corpus,available:true,ruleset_id:'dnd_2024',title:'SRD 5.2.1',coverage:'One section only.',unit_count:1}]} as const;
const packet={schema:'dmb_rules_lookup_packet_v1',corpus,ruleset_id:'dnd_2024',query_id:'f'.repeat(64),normalized_query:'prone',status:'evidence',coverage:'One section only.',coverage_status:'limited',hits:[hit],additional_matches:false} as const;
const passage={...hit,schema:'dmb_rules_passage_v1',text,attribution:'Public source attribution'} as const;
beforeEach(()=>{state.epoch=0;vi.stubGlobal('crypto',webcrypto);vi.mocked(api.getRulesCatalog).mockReset().mockResolvedValue(structuredClone(catalog) as any);vi.mocked(api.queryRulesEvidence).mockReset().mockResolvedValue(structuredClone(packet) as any);vi.mocked(api.getRulesPassage).mockReset().mockResolvedValue(structuredClone(passage) as any)});
afterEach(()=>vi.unstubAllGlobals());
async function search(){await screen.findByRole('combobox');await act(async()=>{fireEvent.change(screen.getByRole('textbox',{name:'Rules question'}),{target:{value:'prone'}});fireEvent.click(screen.getByRole('button',{name:'Look up rules'}))})}
it('uses a real shared packet and verified exact passage without replacing the source draft',async()=>{
 render(<><input aria-label="Source draft" defaultValue="keep this"/><RulesLookupTool/></>);const draft=screen.getByRole('textbox',{name:'Source draft'});
 await screen.findByRole('combobox');expect(api.queryRulesEvidence).not.toHaveBeenCalled();await search();
 await act(async()=>{fireEvent.click(screen.getByRole('button',{name:'Inspect cited passage'}))});const cited=await screen.findByRole('region',{name:'Cited rules passage'});
 expect(cited).toHaveTextContent(text);expect(cited).toHaveTextContent('Page 14');expect(api.getRulesPassage).toHaveBeenCalledWith(corpus,hit.citation_id,expect.any(AbortSignal));
 fireEvent.click(within(cited).getByRole('button',{name:'Close cited passage'}));expect(screen.getByRole('textbox',{name:'Source draft'})).toBe(draft);expect(draft).toHaveValue('keep this');
});
it('shows limited coverage and a missing-topic result without claiming no rule exists',async()=>{
 vi.mocked(api.queryRulesEvidence).mockResolvedValue({...packet,status:'no_evidence',hits:[]} as any);render(<RulesLookupTool/>);await search();
 expect(await screen.findByText(/No matching evidence/)).toHaveTextContent('does not establish that no rule exists');expect(screen.getByText('One section only.')).toBeInTheDocument();
});
it('keeps failures explicit and allows deliberate query retry',async()=>{
 vi.mocked(api.queryRulesEvidence).mockRejectedValueOnce(new Error('Rules source unavailable'));render(<RulesLookupTool/>);await search();await screen.findByRole('alert');
 fireEvent.click(screen.getByRole('button',{name:'Look up rules'}));await screen.findByRole('button',{name:'Inspect cited passage'});expect(api.queryRulesEvidence).toHaveBeenCalledTimes(2);
});
it('retires an old query when the user edits the question',async()=>{
 let resolve!:(value:any)=>void;vi.mocked(api.queryRulesEvidence).mockImplementation(()=>new Promise(done=>{resolve=done}));render(<RulesLookupTool/>);await search();
 const signal=vi.mocked(api.queryRulesEvidence).mock.calls[0][2]!;fireEvent.change(screen.getByRole('textbox',{name:'Rules question'}),{target:{value:'travel'}});expect(signal.aborted).toBe(true);
 await act(async()=>resolve(packet));expect(screen.queryByRole('button',{name:'Inspect cited passage'})).not.toBeInTheDocument();expect(screen.getByRole('button',{name:'Look up rules'})).toBeEnabled();
});
it('aborts an abandoned catalog owner',async()=>{
 let signal:AbortSignal|undefined;vi.mocked(api.getRulesCatalog).mockImplementation(value=>{signal=value;return new Promise(()=>{})});const view=render(<RulesLookupTool/>);view.unmount();expect(signal?.aborted).toBe(true);
});
it('ignores same-generation initial CSRF notification, but clears evidence on actual access change',async()=>{
 render(<RulesLookupTool/>);await search();await screen.findByRole('button',{name:'Inspect cited passage'});
 act(()=>window.dispatchEvent(new Event('rules-access-test')));expect(screen.getByRole('button',{name:'Inspect cited passage'})).toBeInTheDocument();
 act(()=>{state.epoch++;window.dispatchEvent(new Event('rules-access-test'))});expect(screen.queryByRole('button',{name:'Inspect cited passage'})).not.toBeInTheDocument();expect(screen.getByRole('button',{name:'Reload rules sources'})).toBeInTheDocument();expect(api.getRulesCatalog).toHaveBeenCalledTimes(1);
});
it('rejects cross-corpus query evidence',async()=>{
 vi.mocked(api.queryRulesEvidence).mockResolvedValue({...packet,corpus:'f'.repeat(64)} as any);render(<RulesLookupTool/>);await search();expect(await screen.findByRole('alert')).toHaveTextContent('did not match');expect(screen.queryByRole('button',{name:'Inspect cited passage'})).not.toBeInTheDocument();
});
it.each(['hash','provenance'])('rejects an invalid exact passage %s',async kind=>{
 vi.mocked(api.getRulesPassage).mockResolvedValue({...passage,...(kind==='hash'?{text:'Altered text'}:{section:'Other source'})} as any);render(<RulesLookupTool/>);await search();await act(async()=>{fireEvent.click(screen.getByRole('button',{name:'Inspect cited passage'}))});expect(await screen.findByRole('alert')).toHaveTextContent('could not be verified');expect(screen.queryByRole('region',{name:'Cited rules passage'})).not.toBeInTheDocument();
});
it('does not infer a printed page label from the PDF index',()=>{expect(rulesPageLabel({printed_page:null,pdf_page_index:13})).toBe('PDF page 14')});
it('allows explicit catalog reload after an unavailable source failure',async()=>{
 vi.mocked(api.getRulesCatalog).mockRejectedValueOnce(new Error('Unavailable'));render(<RulesLookupTool/>);fireEvent.click(await screen.findByRole('button',{name:'Reload rules sources'}));await screen.findByRole('combobox');expect(api.getRulesCatalog).toHaveBeenCalledTimes(2);
});
