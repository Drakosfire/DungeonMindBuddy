import {act,cleanup,fireEvent,render,screen,within} from '@testing-library/react';
import {useLayoutEffect} from 'react';
import {afterEach,beforeEach,expect,it,vi} from 'vitest';
import {DocumentReferenceProvider} from './DocumentReferenceProvider';
import {PeekRegionProvider,PeekRegionSlot} from '../surfaceInteraction/peekHost';
const state=vi.hoisted(()=>({gate:null as Promise<void>|null,resolve:()=>{},reject:(_:Error)=>{},attempts:0}));
vi.mock('../ui/deferredComponent',async original=>{
 const actual=await original<typeof import('../ui/deferredComponent')>();
 return {...actual,deferredComponent:(load:()=>Promise<any>,label:string)=>{
  let loading:Promise<any>|undefined;
  return actual.deferredComponent(()=>{
   state.attempts++;
   const pending=loading??=(async()=>{await state.gate;return load()})();
   const clear=()=>{if(loading===pending)loading=undefined};void pending.then(clear,clear);return pending;
  },label);
 }};
});
vi.mock('./DocumentReferenceBody',()=>({default:({markdown,onReady}:{markdown:string;onReady:()=>void})=>{
 useLayoutEffect(onReady,[markdown,onReady]);
 return <div data-testid="body">{markdown}<a data-document-reference href="/build?world=elderwyld&documentId=2cd1f643-a070-4cec-bbb0-24c803e30b98">Nested</a></div>;
}}));
const A='bba72416-9dfe-49bb-add0-21a346e9a421';
const saved={title:'Saved A',markdown:'Body A',digest:'a'.repeat(64),revisionLabel:'Saved revision 8'};
const load=vi.fn();
function suspend(){state.gate=new Promise<void>((resolve,reject)=>{state.resolve=resolve;state.reject=reject})}
function Fixture({world='elderwyld',source='plan'}:{world?:string;source?:string}){
 return <PeekRegionProvider><DocumentReferenceProvider worldId={world} sourceIdentity={source} load={load}>
  <a data-document-reference href={`/build?world=${world}&documentId=${A}`}>Inspect A</a>
  <input aria-label="Source draft" defaultValue="unsaved"/>
 </DocumentReferenceProvider><PeekRegionSlot/></PeekRegionProvider>;
}
beforeEach(()=>{state.gate=null;state.attempts=0;load.mockReset().mockImplementation(target=>Promise.resolve(target.documentId===A?saved:{...saved,title:'Saved B',markdown:'Body B'}))});
afterEach(cleanup);
it('requests no body code for closed, loading or failed references',async()=>{
 let reject!:(error:Error)=>void;load.mockImplementation(()=>new Promise((_,fail)=>{reject=fail}));
 render(<Fixture/>);expect(state.attempts).toBe(0);
 fireEvent.click(screen.getByRole('link',{name:'Inspect A'}));await screen.findByText('Opening saved document…');expect(state.attempts).toBe(0);
 await act(async()=>reject(new Error('Saved revision unavailable')));
 expect(screen.getByRole('alert')).toHaveTextContent('Saved revision unavailable');expect(state.attempts).toBe(0);
});
it('uses latest reference after suspension while preserving source draft DOM',async()=>{
 suspend();render(<Fixture/>);const draft=screen.getByRole('textbox',{name:'Source draft'});
 fireEvent.change(draft,{target:{value:'keep this'}});const link=screen.getByRole('link',{name:'Inspect A'});fireEvent.click(link);
 await screen.findByText('Loading saved document content…');
 link.setAttribute('href','/build?world=elderwyld&documentId=2cd1f643-a070-4cec-bbb0-24c803e30b98');fireEvent.click(link);
 await screen.findByRole('heading',{name:'Saved B'});await act(async()=>state.resolve());
 expect(await screen.findByTestId('body')).toHaveTextContent('Body B');expect(screen.queryByText('Body A')).not.toBeInTheDocument();
 expect(screen.getByRole('textbox',{name:'Source draft'})).toBe(draft);expect(draft).toHaveValue('keep this');
});
it.each(['close','source','world'])('does not resurrect suspended content after %s',async action=>{
 suspend();const view=render(<Fixture/>);fireEvent.click(screen.getByRole('link',{name:'Inspect A'}));await screen.findByText('Loading saved document content…');
 if(action==='close')fireEvent.click(screen.getByRole('button',{name:'Close reference'}));
 else view.rerender(<Fixture source={action==='source'?'play':'plan'} world={action==='world'?'other-world':'elderwyld'}/>);
 await act(async()=>state.resolve());expect(screen.queryByRole('region',{name:'Document reference'})).not.toBeInTheDocument();expect(screen.queryByTestId('body')).not.toBeInTheDocument();
});
it('restores Back scroll after delayed DOM commits rather than the clamped fallback',async()=>{
 render(<Fixture/>);fireEvent.click(screen.getByRole('link',{name:'Inspect A'}));await screen.findByTestId('body');
 const pane=screen.getByRole('region',{name:'Document reference'});let top=0;
 Object.defineProperty(pane,'scrollTop',{configurable:true,get:()=>top,set:value=>{top=pane.querySelector('[data-testid="body"]')?value:0}});
 pane.scrollTop=143;fireEvent.click(within(pane).getByRole('link',{name:'Nested'}));await screen.findByRole('heading',{name:'Saved B'});await screen.findByTestId('body');
 suspend();fireEvent.click(screen.getByRole('button',{name:'← Previous reference'}));await screen.findByText('Loading saved document content…');expect(pane.scrollTop).toBe(0);
 await act(async()=>state.resolve());await screen.findByTestId('body');expect(pane.scrollTop).toBe(143);
});
it('retries a failed chunk without refetching the admitted document',async()=>{
 suspend();const report=vi.spyOn(console,'error').mockImplementation(()=>{});render(<Fixture/>);fireEvent.click(screen.getByRole('link',{name:'Inspect A'}));await screen.findByText('Loading saved document content…');
 await act(async()=>state.reject(new Error('Chunk unavailable')));await screen.findByRole('button',{name:'Retry saved document content'});
 state.gate=null;fireEvent.click(screen.getByRole('button',{name:'Retry saved document content'}));expect(await screen.findByTestId('body')).toHaveTextContent('Body A');expect(load).toHaveBeenCalledTimes(1);report.mockRestore();
});
