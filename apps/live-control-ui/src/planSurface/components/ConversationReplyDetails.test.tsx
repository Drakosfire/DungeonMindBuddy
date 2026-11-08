import {useState} from 'react';
import {act,fireEvent,render,screen,waitFor} from '@testing-library/react';
import {expect,it,vi} from 'vitest';
import {ConversationReplyDetails} from './ConversationReplyDetails';

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
  fireEvent.click(screen.getByText('Details'));
  await waitFor(()=>expect(load).toHaveBeenCalledTimes(1));
  expect(screen.getByRole('button',{name:'Review suggestion on page'})).toBeEnabled();
  expect(screen.getByText('Loading reply details…')).toBeInTheDocument();
  await act(async()=>finish());await screen.findByText('Verified sources');
  expect(screen.getByText('Details').closest('details')).toHaveAttribute('open');
  fireEvent.click(screen.getByText('Details'));fireEvent.click(screen.getByText('Details'));
  expect(load).toHaveBeenCalledTimes(1);expect(screen.getAllByText('Details')).toHaveLength(1);
});

it('keeps failed details local and retries only when requested',async()=>{
  const load=vi.fn().mockRejectedValueOnce(new Error('Invalid receipt')).mockResolvedValue(undefined);
  function Harness(){const[open,setOpen]=useState(false);return <ConversationReplyDetails id="reply" open={open} onOpenChange={setOpen} loaded={false} load={load}><p>Execution timeline</p></ConversationReplyDetails>;}
  render(<Harness/>);fireEvent.click(screen.getByText('Details'));
  expect(await screen.findByRole('alert')).toHaveTextContent('Invalid receipt');
  expect(screen.getByText('Execution timeline')).toBeInTheDocument();expect(load).toHaveBeenCalledTimes(1);
  fireEvent.click(screen.getByText('Details'));fireEvent.click(screen.getByText('Details'));
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
  expect(screen.getByText('Details').closest('details')).not.toHaveAttribute('open');
  expect(screen.getByText('Advanced receipt')).not.toBeVisible();
});

it('retires an old inspection error when the owner supplies verified details',async()=>{
 const load=vi.fn().mockRejectedValue(new Error('Old detail read failed'));
 function Harness(){const[open,setOpen]=useState(false),[loaded,setLoaded]=useState(false);return <>
  <button onClick={()=>setLoaded(true)}>Accept verified details</button>
  <ConversationReplyDetails id="reply" open={open} onOpenChange={setOpen} loaded={loaded} load={load}><p>Receipt inspection</p></ConversationReplyDetails>
 </>;}
 render(<Harness/>);fireEvent.click(screen.getByText('Details'));await screen.findByRole('alert');
 fireEvent.click(screen.getByRole('button',{name:'Accept verified details'}));
 await waitFor(()=>expect(screen.queryByRole('alert')).not.toBeInTheDocument());expect(load).toHaveBeenCalledTimes(1);
});
