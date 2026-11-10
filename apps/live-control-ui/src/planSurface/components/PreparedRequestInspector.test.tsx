import { fireEvent, render, screen } from '@testing-library/react'
import { expect, it } from 'vitest'
import { PreparedRequestInspector } from './PreparedRequestInspector'
it('shows added removed and changed exact components, retaining full current bytes', () => {
  const previousPayloadJson=JSON.stringify({instructions:'Keep it grounded',messages:[{role:'user',content:'Before'}],tools:[{name:'read'}]})
  const payloadJson=JSON.stringify({instructions:'Keep it grounded',messages:[{role:'user',content:'<script>Now</script>'}],temperature:0})
  render(<PreparedRequestInspector {...{payloadJson,previousPayloadJson}} />)
  expect(screen.getByLabelText('Changes since previous model call')).not.toHaveTextContent('System instructions')
  fireEvent.click(screen.getByText('Changed · Message 1 · user · /messages/0'))
  expect(screen.getByText(/"content": "Before"/)).toBeInTheDocument()
  expect(screen.getAllByText(/<script>Now<\/script>/).length).toBeGreaterThan(0)
  expect(document.querySelector('script')).toBeNull()
  expect(screen.getByText('Removed · Tool 1 · /tools/0')).toBeInTheDocument()
  expect(screen.getByText('Added · temperature · /temperature')).toBeInTheDocument()
  fireEvent.click(screen.getByRole('checkbox',{name:'Exact JSON bytes'}))
  expect(screen.getByLabelText('Captured request').querySelector('pre')?.textContent).toBe(payloadJson)
})
it('does not imply there is a comparison without a previous captured request', () => {
  render(<PreparedRequestInspector payloadJson='{"input":"Only capture"}' />)
  expect(screen.queryByLabelText('Changes since previous model call')).not.toBeInTheDocument()
})

it('pretty prints encoded message content in full, component and change views while preserving exact captured bytes',()=>{
 const content=JSON.stringify({authored_sources:[{selection_ids:['work0'],text:'<script>Evidence</script>'}],literal:'42'});
 const payloadJson=JSON.stringify({model:'writer',input:[{role:'user',content}]},null,1);
 const previousPayloadJson=JSON.stringify({model:'decision',state:{question:'An ordinary question'}});
 render(<PreparedRequestInspector {...{payloadJson,previousPayloadJson}}/>);
 const request=screen.getByLabelText('Captured request');
 const decoded=JSON.parse(request.querySelector('pre')!.textContent!);
 expect(decoded.input[0].content).toEqual(JSON.parse(content));expect(decoded.input[0].content.literal).toBe('42');expect(document.querySelector('script')).toBeNull();
 const heading=screen.getByText('Added · Message 1 · user · /input/0');const details=heading.closest('details')!;
 expect(details).toHaveClass('buddy-prompt__disclosure');fireEvent.click(heading.closest('summary')!);expect(details).toHaveAttribute('open');
 expect(JSON.parse(details.querySelector('pre')!.textContent!).content.authored_sources[0].selection_ids).toEqual(['work0']);
 fireEvent.click(heading.closest('summary')!);expect(details).not.toHaveAttribute('open');
 fireEvent.click(screen.getByRole('button',{name:/Message 1 · user/}));expect(JSON.parse(request.querySelector('pre')!.textContent!).content).toEqual(JSON.parse(content));
 fireEvent.click(screen.getByRole('checkbox',{name:'Exact JSON bytes'}));expect(JSON.parse(request.querySelector('pre')!.textContent!).content).toBe(content);
 fireEvent.click(screen.getByRole('button',{name:'Show full request'}));expect(request.querySelector('pre')!.textContent).toBe(payloadJson);
 fireEvent.click(screen.getByRole('checkbox',{name:'Exact JSON bytes'}));fireEvent.click(screen.getByRole('button',{name:/Message 1 · user/}));expect(JSON.parse(request.querySelector('pre')!.textContent!).content).toEqual(JSON.parse(content));
 expect(screen.getByText(/not separate chat turns/)).toBeInTheDocument();expect(screen.getByText(/different models or formats/)).toBeInTheDocument();
});
it.each(['Normal prose','42','true','null'])('keeps non-object message content as text: %s',content=>{
 render(<PreparedRequestInspector payloadJson={JSON.stringify({input:[{role:'user',content}]})}/>);
 expect(JSON.parse(screen.getByLabelText('Captured request').querySelector('pre')!.textContent!).input[0].content).toBe(content);
});
