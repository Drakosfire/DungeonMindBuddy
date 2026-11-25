import {act,fireEvent,render,screen,waitFor,within} from '@testing-library/react';
import {describe,it,expect,vi} from 'vitest';
import {SourceCitationEvidence,type CitationChoice} from './SourceCitationEvidence';
import {startReadWave} from '../../api/inFlightReads';

function pending(){let resolve!:(value:{content:string;title:string})=>void;const promise=new Promise<{content:string;title:string}>(done=>{resolve=done;});return {promise,resolve};}
function choice(load:CitationChoice['load']):CitationChoice{return {key:'body:0',number:1,title:'Source · Full document',label:'Read source',kind:'section',load};}

describe('on-demand source display',()=>{
 it('changes only the opened title after the verified read, leaving exact content separate',async()=>{
  const read=pending(),load=vi.fn(()=>read.promise);render(<SourceCitationEvidence identity="turn-a" statements={[{choices:[choice(load)]}]}/>);
  fireEvent.click(screen.getByRole('button',{name:'Read source'}));expect(within(screen.getByRole('region',{name:'Opened source section'})).getByText('Source · Full document')).toBeVisible();
  await act(async()=>read.resolve({title:'Session 15 recap · Full document',content:'Exact retained passage.'}));
  expect(screen.getByText('Session 15 recap · Full document')).toBeVisible();expect(screen.getByText('Exact retained passage.')).toBeVisible();expect(load).toHaveBeenCalledTimes(1);
 });
 it.each(['identity','closed'])('does not attach a late title or source to a %s panel',async change=>{
  const read=pending(),props={statements:[{choices:[choice(()=>read.promise)]}]};const view=render(<SourceCitationEvidence identity="turn-a" {...props}/>);
  fireEvent.click(screen.getByRole('button',{name:'Read source'}));
  if(change==='identity')view.rerender(<SourceCitationEvidence identity="turn-b" {...props}/>);else fireEvent.click(screen.getByRole('button',{name:'Close section'}));
  await act(async()=>read.resolve({title:'Stale source title',content:'Stale source text'}));
  expect(screen.queryByText('Stale source title')).toBeNull();expect(screen.queryByText('Stale source text')).toBeNull();expect(screen.queryByRole('region',{name:'Opened source section'})).toBeNull();
 });
});


it('resolves a verified document name for a citation list and reuses the exact read',async()=>{
 const read=pending(),load=vi.fn(()=>read.promise);
 render(<SourceCitationEvidence identity="turn-a" prefetchTitles statements={[{choices:[{...choice(load),resolveTitle:true,buttonText:'1. Source · Full document'}]}]}/>);
 await waitFor(()=>expect(load).toHaveBeenCalledTimes(1));
 await act(async()=>read.resolve({title:'The City of Mirathorn · Full document',content:'Exact retained passage.'}));
 fireEvent.click(screen.getByRole('button',{name:'1. The City of Mirathorn'}));
 await screen.findByText('Exact retained passage.');expect(load).toHaveBeenCalledTimes(1);
});

it('does not apply a verified name to a different turn after a late read',async()=>{
 const read=pending(),load=vi.fn(()=>read.promise);const c={...choice(load),resolveTitle:true,buttonText:'1. Source · Full document'};
 const view=render(<SourceCitationEvidence identity="turn-a" prefetchTitles statements={[{choices:[c]}]}/>);
 await waitFor(()=>expect(load).toHaveBeenCalledTimes(1));
 view.rerender(<SourceCitationEvidence identity="turn-b" statements={[{choices:[c]}]}/>);
 await act(async()=>read.resolve({title:'Old name · Full document',content:'Old passage'}));
 expect(screen.queryByText('1. Old name')).not.toBeInTheDocument();
});


it('does not present a document name when the exact read fails validation',async()=>{
 const load=vi.fn().mockRejectedValue(new Error('Source binding differs'));
 render(<SourceCitationEvidence identity="turn-a" prefetchTitles statements={[{choices:[{...choice(load),resolveTitle:true,buttonText:'1. Source · Full document'}]}]}/>);
 expect(await screen.findByRole('button',{name:'1. Source name unavailable'})).toBeVisible();
 expect(screen.queryByText('1. The City of Mirathorn')).not.toBeInTheDocument();
});


it('retires prefetched titles and open content when the access wave changes',async()=>{
 const second=pending();
 const load=vi.fn().mockResolvedValueOnce({title:'Private document · Full document',content:'Private contents'}).mockReturnValueOnce(second.promise);
 const c={...choice(load),resolveTitle:true,buttonText:'1. Source · Full document'};
 render(<SourceCitationEvidence identity="same-turn" prefetchTitles statements={[{choices:[c]}]}/>);
 fireEvent.click(await screen.findByRole('button',{name:'1. Private document'}));
 await screen.findByText('Private contents');
 act(()=>startReadWave());
 expect(screen.queryByText('Private contents')).not.toBeInTheDocument();
 expect(screen.queryByText('1. Private document')).not.toBeInTheDocument();
 await waitFor(()=>expect(load).toHaveBeenCalledTimes(2));
 await act(async()=>second.resolve({title:'Current document · Full document',content:'Current contents'}));
 fireEvent.click(await screen.findByRole('button',{name:'1. Current document'}));
 expect(await screen.findByText('Current contents')).toBeVisible();
});

it('rejects late prefetched names from a retired access wave',async()=>{
 const old=pending(),next=pending(),load=vi.fn().mockReturnValueOnce(old.promise).mockReturnValueOnce(next.promise);
 const c={...choice(load),resolveTitle:true,buttonText:'1. Source · Full document'};
 render(<SourceCitationEvidence identity="same-turn" prefetchTitles statements={[{choices:[c]}]}/>);
 await waitFor(()=>expect(load).toHaveBeenCalledTimes(1));
 act(()=>startReadWave());await waitFor(()=>expect(load).toHaveBeenCalledTimes(2));
 await act(async()=>old.resolve({title:'Retired document',content:'Retired contents'}));
 expect(screen.queryByText('1. Retired document')).not.toBeInTheDocument();
 await act(async()=>next.resolve({title:'Current document',content:'Current contents'}));
 expect(await screen.findByRole('button',{name:'1. Current document'})).toBeVisible();
});

it('keeps citation qualifications on a resolved document name',async()=>{
 const load=vi.fn().mockResolvedValue({title:'Document · Full document',content:'Exact content'});
 const c={...choice(load),resolveTitle:true,buttonText:'1. Source · Full document · provisional',titleSuffix:' · provisional'};
 render(<SourceCitationEvidence identity="turn" prefetchTitles statements={[{choices:[c]}]}/>);
 expect(await screen.findByRole('button',{name:'1. Document · provisional'})).toBeVisible();
});
