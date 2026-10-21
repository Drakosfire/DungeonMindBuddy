import {act,cleanup,fireEvent,render,screen,waitFor,within} from '@testing-library/react';
import {afterEach,beforeEach,expect,it,vi} from 'vitest';
import * as api from '../api/recapSemanticReviewApi';
import {BuildRecapSemanticReview} from './BuildRecapSemanticReview';
import {recapRun,recapReview,decisionReceipt} from './buildRecapCorrection.testSupport';
const clone=<T,>(value:T):T=>structuredClone(value);
function props(){return {run:clone(recapRun),review:clone(recapReview),worldId:'world-a',onBusy:vi.fn(),isCurrent:()=>true,
  onDecided:vi.fn().mockResolvedValue(vi.fn())};}
function request(){return JSON.parse(localStorage.getItem(Object.keys(localStorage).find(k=>k.startsWith('dmb.buildRecapSemanticReview.v1:'))!)!).request;}
beforeEach(()=>{
  localStorage.clear();Object.defineProperty(navigator,'locks',{configurable:true,value:{request:(_key:string,action:()=>unknown)=>Promise.resolve(action())}});
  vi.spyOn(api,'decideRecapSemantics').mockImplementation(async(runId,input)=>({...decisionReceipt,runId,state:input.decision,reviewDecisionRef:input.reviewDecisionRef}));
});
afterEach(()=>{cleanup();vi.restoreAllMocks();});
it.each(['accepted','rejected'] as const)('persists explicit %s decision before POST and commits only after current-run proof',async decision=>{
  const p=props(),commit=vi.fn();p.onDecided.mockResolvedValue(commit);
  vi.mocked(api.decideRecapSemantics).mockImplementation(async(runId,input,basis)=>{
    expect(request()).toEqual(input);expect(commit).not.toHaveBeenCalled();
    return {...decisionReceipt,runId,state:decision,reviewDecisionRef:input.reviewDecisionRef,basisSha256:basis};
  });
  render(<BuildRecapSemanticReview {...p}/>);
  const button=screen.getByRole('button',{name:decision==='accepted'?'Accept corrected interpretation':'Reject corrected interpretation'});
  expect(button).toBeDisabled();fireEvent.click(screen.getByRole('checkbox'));fireEvent.click(button);
  await waitFor(()=>expect(commit).toHaveBeenCalledOnce());
  expect(p.onDecided).toHaveBeenCalledOnce();expect(localStorage.length).toBe(0);expect(api.decideRecapSemantics).toHaveBeenCalledOnce();
});
it('retains an unknown decision across reload and explicitly retries the identical reference/revision',async()=>{
  vi.mocked(api.decideRecapSemantics).mockRejectedValueOnce(new Error('lost response'));
  const p=props(),ui=render(<BuildRecapSemanticReview {...p}/>);
  fireEvent.click(screen.getByRole('checkbox'));fireEvent.click(screen.getByRole('button',{name:'Accept corrected interpretation'}));
  await screen.findByRole('alert');const original=request();ui.unmount();
  render(<BuildRecapSemanticReview {...p}/>);
  expect(api.decideRecapSemantics).toHaveBeenCalledOnce();expect(screen.queryByRole('button',{name:'Reject corrected interpretation'})).toBeNull();
  fireEvent.click(screen.getByRole('button',{name:'Recover saved review decision'}));
  await waitFor(()=>expect(p.onDecided).toHaveBeenCalledOnce());
  expect(vi.mocked(api.decideRecapSemantics).mock.calls[1][1]).toEqual(original);
});
it('blocks dispatch if local recovery cannot be saved',async()=>{
  vi.spyOn(Storage.prototype,'setItem').mockImplementation(()=>{throw new Error('storage full');});
  render(<BuildRecapSemanticReview {...props()}/>);fireEvent.click(screen.getByRole('checkbox'));
  fireEvent.click(screen.getByRole('button',{name:'Accept corrected interpretation'}));
  expect(await screen.findByRole('alert')).toHaveTextContent('storage full');expect(api.decideRecapSemantics).not.toHaveBeenCalled();
});
it('retains the original decision if current-run adoption fails',async()=>{
  const p=props();p.onDecided.mockRejectedValue(new Error('foreign child status'));
  render(<BuildRecapSemanticReview {...p}/>);fireEvent.click(screen.getByRole('checkbox'));
  fireEvent.click(screen.getByRole('button',{name:'Accept corrected interpretation'}));
  expect(await screen.findByRole('alert')).toHaveTextContent('foreign child');expect(request().decision).toBe('accepted');
});
it('refuses a changed verified semantic basis before showing decision controls',()=>{
  const p=props();(p.review as typeof recapReview).semanticDisposition!.basisSha256='f'.repeat(64);
  render(<BuildRecapSemanticReview {...p}/>);expect(screen.getByRole('alert')).toHaveTextContent('basis could not be verified');
  expect(screen.queryByRole('button',{name:'Accept corrected interpretation'})).toBeNull();
});
it('does not offer acceptance for nonliteral evidence or a rejected interpretation',()=>{
  const p=props();p.review.inspectionStatus='invalid_evidence';
  const ui=render(<BuildRecapSemanticReview {...p}/>);expect(screen.queryByRole('checkbox')).toBeNull();
  p.review.inspectionStatus='ready';(p.review as typeof recapReview).semanticDisposition!.state='rejected';
  (p.run.lineage!.semantic_disposition as Record<string,unknown>).state='rejected';
  ui.rerender(<BuildRecapSemanticReview {...p}/>);expect(screen.getByRole('status')).toHaveTextContent('rejected');
  expect(api.decideRecapSemantics).not.toHaveBeenCalled();
});
it('does not dispatch after scope changes while waiting for storage lock',async()=>{
  let release!:()=>void,current=true;
  Object.defineProperty(navigator,'locks',{configurable:true,value:{request:(_key:string,action:()=>unknown)=>new Promise((resolve,reject)=>{release=()=>{try{resolve(action());}catch(error){reject(error);}};})}});
  const p=props();p.isCurrent=()=>current;
  render(<BuildRecapSemanticReview {...p}/>);fireEvent.click(screen.getByRole('checkbox'));fireEvent.click(screen.getByRole('button',{name:'Accept corrected interpretation'}));
  current=false;await act(async()=>{release();await Promise.resolve();});
  expect(api.decideRecapSemantics).not.toHaveBeenCalled();
});

it('does not replace another mounted view’s pending decision',async()=>{
  let resolve!:(value:typeof decisionReceipt)=>void;
  vi.mocked(api.decideRecapSemantics).mockReturnValue(new Promise(r=>{resolve=r;}));
  const p=props(),a=render(<BuildRecapSemanticReview {...p}/>),b=render(<BuildRecapSemanticReview {...p}/>);
  const qa=within(a.container),qb=within(b.container);
  fireEvent.click(qa.getByRole('checkbox'));fireEvent.click(qb.getByRole('checkbox'));
  fireEvent.click(qa.getByRole('button',{name:'Accept corrected interpretation'}));
  await waitFor(()=>expect(api.decideRecapSemantics).toHaveBeenCalledOnce());const original=request();
  fireEvent.click(qb.getByRole('button',{name:'Reject corrected interpretation'}));
  expect(await qb.findByRole('alert')).toHaveTextContent('Another saved decision is pending');
  expect(api.decideRecapSemantics).toHaveBeenCalledOnce();expect(request()).toEqual(original);
  a.unmount();b.unmount();await act(async()=>{resolve({...decisionReceipt,reviewDecisionRef:original.reviewDecisionRef});await Promise.resolve();});
});
it('refuses modified saved request fields before sending a write',async()=>{
  vi.mocked(api.decideRecapSemantics).mockRejectedValueOnce(new Error('lost response'));
  const p=props(),ui=render(<BuildRecapSemanticReview {...p}/>);
  fireEvent.click(screen.getByRole('checkbox'));fireEvent.click(screen.getByRole('button',{name:'Accept corrected interpretation'}));
  await screen.findByRole('alert');ui.unmount();
  const key=Object.keys(localStorage)[0],value=JSON.parse(localStorage.getItem(key)!);value.request.reviewerId='forged';localStorage.setItem(key,JSON.stringify(value));
  render(<BuildRecapSemanticReview {...p}/>);
  expect(screen.getByRole('alert')).toHaveTextContent('does not match');expect(api.decideRecapSemantics).toHaveBeenCalledOnce();
  expect(screen.getByRole('button',{name:'Accept corrected interpretation'})).toBeDisabled();
});
