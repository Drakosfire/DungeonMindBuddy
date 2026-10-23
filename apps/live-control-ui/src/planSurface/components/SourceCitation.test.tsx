import {act,fireEvent,render,screen,within} from '@testing-library/react';
import {expect,it,vi} from 'vitest';
import {SourceCitationEvidence,type CitationChoice} from './SourceCitationEvidence';
function choice(load=vi.fn(async()=> 'An exact **passage**.')):CitationChoice {
  return {key:'a',number:1,title:'Market journal · lines 4–8',label:'Read Market journal · lines 4–8',kind:'passage',load};
}
it('places a numbered marker in the statement, exposes attribution and only reads on click',async()=>{
  const c=choice();render(<SourceCitationEvidence identity="one" statements={[{text:'A supported statement.',choices:[c]}]}/>);
  const button=screen.getByRole('button',{name:c.label});
  expect(button.textContent).toBe('1');expect(button.closest('p')?.textContent).toBe('A supported statement.1');
  expect(button.getAttribute('aria-describedby')).toBe(screen.getByRole('tooltip',{hidden:true}).id);
  fireEvent.mouseOver(button);button.focus();expect(c.load).not.toHaveBeenCalled();
  fireEvent.click(button);await screen.findByText('passage');
  expect(button.getAttribute('aria-expanded')).toBe('true');
  expect(document.getElementById(button.getAttribute('aria-controls')!)).toBe(screen.getByLabelText('Opened source passage'));
  fireEvent.click(button);expect(screen.queryByLabelText('Opened source passage')).toBeNull();
});
it('keeps multiple citations at the end of a formatted statement and opens the chosen one',async()=>{
  const a=choice(),b={...choice(vi.fn(async()=> 'Second exact passage.')),key:'b',number:2,label:'Read Other journal',title:'Other journal'};
  render(<SourceCitationEvidence identity="one" statements={[{text:'A **supported** statement.',choices:[a,b]}]}/>);
  const paragraph=screen.getByText('supported').closest('p')!;
  expect(within(paragraph).getAllByRole('button').map(b=>b.textContent)).toEqual(['1','2']);
  fireEvent.click(screen.getByRole('button',{name:b.label}));await screen.findByText('Second exact passage.');
  expect(a.load).not.toHaveBeenCalled();expect(b.load).toHaveBeenCalledOnce();
});
it.each(['close','scope','unmount'])('discards a late response after %s',async(action)=>{
  let resolve!:(text:string)=>void;
  const c=choice(vi.fn(()=>new Promise<string>(r=>{resolve=r;})));
  const view=render(<SourceCitationEvidence identity="one" statements={[{text:'Claim.',choices:[c]}]}/>);
  fireEvent.click(screen.getByRole('button',{name:c.label}));
  if(action==='close')fireEvent.click(screen.getByRole('button',{name:'Close passage'}));
  if(action==='scope')view.rerender(<SourceCitationEvidence identity="two" statements={[{text:'Claim.',choices:[c]}]}/>);
  if(action==='unmount')view.unmount();
  await act(async()=>resolve('Late secret text.'));
  expect(screen.queryByText('Late secret text.')).toBeNull();
});

it.each(['A supported statement.\n','A supported **statement**.\r\n  '])('keeps citations inline after trailing whitespace: %j',text=>{
  const c=choice();render(<SourceCitationEvidence identity="one" statements={[{text,choices:[c]}]}/>);
  expect(screen.getByRole('button',{name:c.label}).closest('p')).not.toBeNull();
});
it.each(['| Label | Value |\n| --- | --- |\n| Tree | Tough |\n','```text\nLiteral code\n```\n'])('keeps end controls outside literal code and within table semantics: %j',text=>{
  const c=choice();const view=render(<SourceCitationEvidence identity="one" statements={[{text,choices:[c]}]}/>);
  const button=screen.getByRole('button',{name:c.label});
  expect(button.closest('code')).toBeNull();
  if(text.startsWith('|'))expect(button.closest('td')).not.toBeNull();
  expect(view.container.querySelectorAll('.source-citation__button')).toHaveLength(1);
});

it('portals hover details outside transcript clipping and clamps the right edge',()=>{
  const c=choice();render(<div style={{overflow:'hidden'}}><SourceCitationEvidence identity="one" statements={[{text:'Claim.',choices:[c]}]}/></div>);
  const button=screen.getByRole('button',{name:c.label});
  vi.spyOn(button,'getBoundingClientRect').mockReturnValue({left:990,bottom:50} as DOMRect);
  fireEvent.mouseEnter(button);
  const tooltip=screen.getByRole('tooltip');
  expect(tooltip.parentElement).toBe(document.body);
  expect(Number.parseFloat(tooltip.style.left)+288).toBeLessThanOrEqual(window.innerWidth-8);
  fireEvent.keyDown(button,{key:'Escape'});expect(tooltip).not.toBeVisible();
  expect(c.load).not.toHaveBeenCalled();
});

it.each(['resize','scroll'])('dismisses a positioned tooltip on %s',event=>{
  const c=choice();render(<SourceCitationEvidence identity="one" statements={[{text:'Claim.',choices:[c]}]}/>);
  fireEvent.mouseEnter(screen.getByRole('button',{name:c.label}));
  expect(screen.getByRole('tooltip')).toBeVisible();
  fireEvent(window,new Event(event));
  expect(screen.queryByRole('tooltip')).toBeNull();
});
