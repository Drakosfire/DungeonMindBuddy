import {useState} from 'react';
import {act,fireEvent,render,screen,waitFor} from '@testing-library/react';
import {expect,it,vi} from 'vitest';
import {ConversationReplyDetails, TraceEvidence, TraceDiagnostics} from './ConversationReplyDetails';

it('keeps one disclosure open through delayed hydration and does not repeat a read',async()=>{
  let finish!:()=>void;
  const load=vi.fn(()=>new Promise<void>(resolve=>{finish=resolve;}));
  function Harness(){const[open,setOpen]=useState(false),[loaded,setLoaded]=useState(false);return <>
    <p>Saved reply</p><button>Review suggestion on page</button>
    <ConversationReplyDetails id="reply" open={open} onOpenChange={setOpen} loaded={loaded}
      load={async signal=>{await load();if(!signal.aborted)setLoaded(true);}}>
      {loaded?<p>Verified sources</p>:null}<p>Execution timeline</p>
    </ConversationReplyDetails></>;}
  render(<Harness/>);expect(load).not.toHaveBeenCalled();
  fireEvent.click(screen.getByText('Trace'));
  await waitFor(()=>expect(load).toHaveBeenCalledTimes(1));
  expect(screen.getByRole('button',{name:'Review suggestion on page'})).toBeEnabled();
  expect(screen.getByText('Loading reply details…')).toBeInTheDocument();
  await act(async()=>finish());await screen.findByText('Verified sources');
  expect(screen.getByText('Trace').closest('details')).toHaveAttribute('open');
  fireEvent.click(screen.getByText('Trace'));fireEvent.click(screen.getByText('Trace'));
  expect(load).toHaveBeenCalledTimes(1);expect(screen.getAllByText('Trace')).toHaveLength(1);
});

it('keeps failed details local and retries only when requested',async()=>{
  const load=vi.fn().mockRejectedValueOnce(new Error('Invalid receipt')).mockResolvedValue(undefined);
  function Harness(){const[open,setOpen]=useState(false);return <ConversationReplyDetails id="reply" open={open} onOpenChange={setOpen} loaded={false} load={load}><p>Execution timeline</p></ConversationReplyDetails>;}
  render(<Harness/>);fireEvent.click(screen.getByText('Trace'));
  expect(await screen.findByRole('alert')).toHaveTextContent('Invalid receipt');
  expect(screen.getByText('Execution timeline', {selector: 'p'})).toBeInTheDocument();expect(load).toHaveBeenCalledTimes(1);
  fireEvent.click(screen.getByText('Trace'));fireEvent.click(screen.getByText('Trace'));
  expect(load).toHaveBeenCalledTimes(1);fireEvent.click(screen.getByRole('button',{name:'Retry details'}));
  await waitFor(()=>expect(load).toHaveBeenCalledTimes(2));
});

it('loads citations directly without opening the advanced disclosure',async()=>{
  const load=vi.fn();
  function Harness(){const[open,setOpen]=useState(false),[loaded,setLoaded]=useState(false);return <>
    {loaded&&<button>Read cited passage</button>}
    <ConversationReplyDetails id="reply" open={open} onOpenChange={setOpen} loaded={loaded} showSources
      load={async()=>{await load();setLoaded(true);}}><p>Advanced receipt</p></ConversationReplyDetails>
  </>;}
  render(<Harness/>);fireEvent.click(screen.getByRole('button',{name:'Show citations'}));
  await screen.findByRole('button',{name:'Read cited passage'});expect(load).toHaveBeenCalledTimes(1);
  expect(screen.getByText('Trace').closest('details')).not.toHaveAttribute('open');
  expect(screen.getByText('Advanced receipt')).not.toBeVisible();
});

it('retires an old inspection error when the owner supplies verified details',async()=>{
 const load=vi.fn().mockRejectedValue(new Error('Old detail read failed'));
 function Harness(){const[open,setOpen]=useState(false),[loaded,setLoaded]=useState(false);return <>
  <button onClick={()=>setLoaded(true)}>Accept verified details</button>
  <ConversationReplyDetails id="reply" open={open} onOpenChange={setOpen} loaded={loaded} load={load}><p>Receipt inspection</p></ConversationReplyDetails>
 </>;}
 render(<Harness/>);fireEvent.click(screen.getByText('Trace'));await screen.findByRole('alert');
 fireEvent.click(screen.getByRole('button',{name:'Accept verified details'}));
 await waitFor(()=>expect(screen.queryByRole('alert')).not.toBeInTheDocument());expect(load).toHaveBeenCalledTimes(1);
});


it('uses the same exact read for direct page review without opening Details',async()=>{
 const load=vi.fn();
 function Harness(){const[open,setOpen]=useState(false),[loaded,setLoaded]=useState(false);return <>
  <textarea aria-label="Unsent draft" defaultValue="Keep this thought"/>
  {loaded&&<p>Exact saved page review</p>}
  <ConversationReplyDetails id="reply" open={open} onOpenChange={setOpen} loaded={loaded} showSources reviewLabel="Review new page"
    load={async()=>{await load();setLoaded(true);}}><p>Advanced receipt</p></ConversationReplyDetails>
 </>;}
 render(<Harness/>);expect(load).not.toHaveBeenCalled();
 fireEvent.click(screen.getByRole('button',{name:'Review new page'}));await screen.findByText('Exact saved page review');
 expect(load).toHaveBeenCalledTimes(1);expect(screen.getByText('Trace').closest('details')).not.toHaveAttribute('open');
 expect(screen.getByLabelText('Unsent draft')).toHaveValue('Keep this thought');
});

it('switches Trace tabs using the keyboard while keeping the selected tab focused', () => {
  render(<ConversationReplyDetails id="reply" open onOpenChange={() => {}} loaded load={async () => {}}>
    <p>Evidence content</p>
  </ConversationReplyDetails>);
  const evidence = screen.getByRole('tab', {name: 'Evidence'});
  evidence.focus();
  fireEvent.keyDown(evidence, {key: 'ArrowRight'});
  const crawler = screen.getByRole('tab', {name: 'Graph crawler'});
  expect(crawler).toHaveFocus();
  fireEvent.keyDown(crawler, {key: 'ArrowRight'});
  const timeline = screen.getByRole('tab', {name: 'Execution timeline'});
  expect(timeline).toHaveFocus();
  expect(timeline).toHaveAttribute('aria-selected', 'true');
  expect(screen.getByRole('tabpanel')).toHaveAttribute('aria-labelledby', timeline.id);
  fireEvent.keyDown(timeline, {key: 'End'});
  expect(screen.getByRole('tab', {name: 'Diagnostics'})).toHaveFocus();
});


it('confines saved suggestion review to Evidence when switching Trace tabs', () => {
  render(<ConversationReplyDetails id="reply" open onOpenChange={() => {}} loaded load={async () => {}}>
    <TraceEvidence><section aria-label="Saved suggestion review">Kept suggestion</section></TraceEvidence>
  </ConversationReplyDetails>);
  const suggestion = screen.getByRole('region', {name: 'Saved suggestion review'});
  expect(suggestion).toBeVisible();
  for (const name of ['Graph crawler', 'Execution timeline', 'Prompt', 'Diagnostics']) {
    fireEvent.click(screen.getByRole('tab', {name}));
    expect(suggestion).not.toBeVisible();
  }
  fireEvent.click(screen.getByRole('tab', {name: 'Evidence'}));
  expect(suggestion).toBeVisible();
});


it('shows saved turn information only in Diagnostics',()=>{
 render(<ConversationReplyDetails id="reply" open onOpenChange={()=>{}} loaded load={async()=>{}}>
  <TraceDiagnostics><p>Turn 6 · completed</p></TraceDiagnostics>
 </ConversationReplyDetails>);
 expect(screen.getByText('Turn 6 · completed')).not.toBeVisible();
 fireEvent.click(screen.getByRole('tab',{name:'Diagnostics'}));
 expect(screen.getByText('Turn 6 · completed')).toBeVisible();
});
