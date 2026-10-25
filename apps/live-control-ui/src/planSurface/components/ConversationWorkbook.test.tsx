import {cleanup,fireEvent,render,screen} from '@testing-library/react'
import {afterEach,beforeEach,describe,expect,it,vi} from 'vitest'
import {ConversationWorkbook} from './ConversationWorkbook'
import {getWorkPlan,saveWorkPlan} from '../../api/conversationWorkPlanApi'
vi.mock('../../api/conversationWorkPlanApi',()=>({getWorkPlan:vi.fn(),saveWorkPlan:vi.fn(),continueWorkPlan:vi.fn()}))
const binding={worldId:'world',conversationId:'conversation',turnId:'turn'}
const source='Before writing:\n\n1. Read Edge’s table.\n2. Choose an existing shop owner.\n'
function mount(onAdd=vi.fn(),extra={}) {render(<ConversationWorkbook {...binding} source={source} onAdd={onAdd} {...extra}/>);return onAdd}
beforeEach(()=>window.sessionStorage.clear())
afterEach(()=>vi.restoreAllMocks())
describe('author conversation workbook',()=>{
 it('edits/selects steps and adds only reviewed steps without sending',()=>{
  const add=mount();fireEvent.click(screen.getByRole('button',{name:'Review plan'}))
  fireEvent.change(screen.getByLabelText('Step 1'),{target:{value:'Read the latest saved Edge table.'}})
  fireEvent.click(screen.getByLabelText('Include step 2'))
  fireEvent.click(screen.getByRole('button',{name:'Add to message'}))
  expect(add).toHaveBeenCalledWith('My reviewed plan:\n\n1. Read the latest saved Edge table.')
  expect(screen.getByRole('status')).toHaveTextContent('Review it and Send')
 })
 it('presents editable questions and author answers, preserving notes across reload',()=>{
  mount();fireEvent.click(screen.getByRole('button',{name:'Answer questions'}))
  fireEvent.change(screen.getByLabelText('Question 1'),{target:{value:'Which table should Buddy read?'}})
  fireEvent.change(screen.getByLabelText('Answer 1'),{target:{value:'The naming chart in Edge.'}})
  cleanup();const add=mount();fireEvent.click(screen.getByRole('button',{name:'Answer questions'}))
  expect(screen.getByLabelText('Answer 1')).toHaveValue('The naming chart in Edge.')
  fireEvent.click(screen.getByRole('button',{name:'Add to message'}))
  expect(add).toHaveBeenCalledWith(expect.stringContaining('Question: Which table should Buddy read?\nMy answer: The naming chart in Edge.'))
 })
 it('does not reuse another turn’s notes or overwrite mismatched source notes',()=>{
  mount();fireEvent.click(screen.getByRole('button',{name:'Review plan'}))
  fireEvent.change(screen.getByLabelText('Step 1'),{target:{value:'Private reviewed instruction'}})
  const stored=window.sessionStorage.getItem(window.sessionStorage.key(0)!)
  cleanup();mount(vi.fn(),{source:'1. New response\n'})
  fireEvent.click(screen.getByRole('button',{name:'Review plan'}))
  expect(screen.getByRole('alert')).toHaveTextContent('left untouched')
  fireEvent.change(screen.getByLabelText('Step 1'),{target:{value:'New local edit'}})
  expect(window.sessionStorage.getItem(window.sessionStorage.key(0)!)).toBe(stored)
  cleanup();mount(vi.fn(),{turnId:'other-turn'});fireEvent.click(screen.getByRole('button',{name:'Review plan'}))
  expect(screen.getByLabelText('Step 1')).not.toHaveValue('Private reviewed instruction')
 })
 it('warns when storage fails and still preserves editable text for the composer',()=>{
  const add=mount();fireEvent.click(screen.getByRole('button',{name:'Review plan'}))
  vi.spyOn(Storage.prototype,'setItem').mockImplementation(()=>{throw new Error('quota')})
  fireEvent.change(screen.getByLabelText('Step 1'),{target:{value:'Keep my long author text'}})
  expect(screen.getByRole('alert')).toHaveTextContent('could not be saved locally')
  fireEvent.click(screen.getByRole('button',{name:'Add to message'}))
  expect(add).toHaveBeenCalledWith(expect.stringContaining('Keep my long author text'))
 })
 it('does not infer a planning card from ordinary prose or execute anything',()=>{
  const add=mount(vi.fn(),{source:'There is no list in this answer.'})
  expect(screen.queryByRole('button',{name:'Review plan'})).not.toBeInTheDocument()
  expect(add).not.toHaveBeenCalled()
 })
})

it('automatically presents typed questions without Markdown guessing and retains edited answers',()=>{
 const collaboration={kind:'questions' as const,questions:[{text:'Keep this a possible encounter?'}]};
 const add=mount(vi.fn(),{source:'Let’s settle one choice.',collaboration});
 expect(screen.queryByRole('button',{name:'Review plan'})).not.toBeInTheDocument();
 fireEvent.change(screen.getByLabelText('Answer 1'),{target:{value:'Yes, an unplayed possibility.'}});
 cleanup();mount(add,{source:'Let’s settle one choice.',collaboration});
 expect(screen.getByLabelText('Answer 1')).toHaveValue('Yes, an unplayed possibility.');
 fireEvent.click(screen.getByRole('button',{name:'Add to message'}));
 expect(add).toHaveBeenCalledWith(expect.stringContaining('My answer: Yes, an unplayed possibility.'));
});
it('uses both typed plan rows and actions without parsing the acknowledgment',()=>{
 mount(vi.fn(),{source:'Sounds fun. Here is the plan.',collaboration:{kind:'plan',steps:[{text:'Read the existing table.',kind:'discuss'},{text:'Prepare page prose.',kind:'prepare_insertion'}]}});
 expect(screen.getByLabelText('Step 1')).toHaveValue('Read the existing table.');
 expect(screen.getByLabelText('Step 2')).toHaveValue('Prepare page prose.');
});
it('does not infer a workbook from an ordinary new typed answer containing a list',()=>{
 mount(vi.fn(),{collaboration:null});
 expect(screen.queryByRole('button',{name:'Review plan'})).not.toBeInTheDocument();
 expect(screen.queryByRole('region',{name:'Plan for review'})).not.toBeInTheDocument();
});

it('saves both typed actions and the author’s deferred choice without execution',async()=>{
 vi.mocked(getWorkPlan).mockResolvedValue(null);
 const pending=new Promise<never>(()=>{});vi.mocked(saveWorkPlan).mockReturnValue(pending);
 mount(vi.fn(),{source:'Let’s build together.',collaboration:{kind:'plan',steps:[{text:'Read names.',kind:'discuss'},{text:'Prepare prose.',kind:'prepare_insertion'}]},durable:{disabled:false,onContinue:vi.fn()}});
 await screen.findByLabelText('Action 2');
 expect(screen.getByLabelText('Action 2')).toHaveValue('prepare_insertion');
 fireEvent.click(screen.getByLabelText('Include step 2'));
 fireEvent.click(screen.getByRole('button',{name:'Save reviewed plan'}));
 expect(saveWorkPlan).toHaveBeenCalledWith(expect.anything(),0,[expect.objectContaining({text:'Read names.',kind:'discuss',selected:true}),expect.objectContaining({text:'Prepare prose.',kind:'prepare_insertion',selected:false})]);
});
