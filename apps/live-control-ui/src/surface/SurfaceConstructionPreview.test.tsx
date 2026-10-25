import {render,screen,cleanup} from '@testing-library/react';
import {afterEach,it,expect,vi} from 'vitest';
import {SurfaceConstructionPreview} from './SurfaceConstructionPreview';
afterEach(cleanup);
it('renders canonical GFM cells as inert text, without authoring controls',()=>{
 const visible=vi.fn();const view=render(<SurfaceConstructionPreview markdown={'| Name | Detail |\n| --- | --- |\n| **Nia** | A \\| B |\n'} onVisible={visible}/>);
 expect(screen.getByRole('cell',{name:'Nia'})).toBeTruthy();
 expect(screen.getByRole('cell',{name:'A | B'})).toBeTruthy();
 expect(screen.queryByRole('button')).toBeNull();expect(screen.queryByRole('textbox')).toBeNull();
 expect(visible).toHaveBeenCalledTimes(1);
 view.rerender(<SurfaceConstructionPreview markdown={'| Name | Detail |\n| --- | --- |\n| <img src=x onerror=alert(1)> | [test](https://example.com) |\n'} status="incomplete" onVisible={visible}/>);
 expect(view.container.querySelector('img')).toBeNull();expect(view.container.querySelector('a')).toBeNull();
 expect(screen.getByRole('status').textContent).toContain('Incomplete');
 expect(visible).toHaveBeenCalledTimes(1);
});
it('shows received text without inventing a table before its delimiter',()=>{
 const view=render(<SurfaceConstructionPreview markdown={'| Name | Detail |\n'}/>);
 expect(view.container.textContent).toContain('| Name | Detail |');expect(screen.queryByRole('table')).toBeNull();
});

it('observes actual mixed prose, headings and rows in their received order',()=>{
 const visible=vi.fn();const view=render(<SurfaceConstructionPreview markdown={'# Workshop\n\nThe forge warms the room.\n'} onVisible={visible}/>);
 expect(screen.getByRole('region',{name:'Object construction'})).toHaveAttribute('aria-busy','true');
 expect(screen.getByRole('heading',{name:'Workshop'})).toBeInTheDocument();
 expect(screen.getByText('The forge warms the room.')).toBeInTheDocument();
 view.rerender(<SurfaceConstructionPreview markdown={'# Workshop\n\nThe forge warms the room.\n\n| Name | Task |\n| --- | --- |\n| Nia | Repair hook |\n\n- Gather tools\n- Shape the hook\n'} onVisible={visible}/>);
 const preview=screen.getByRole('region',{name:'Object construction'});
 expect([...preview.children].map(n=>n.tagName)).toEqual(['SMALL','H1','P','TABLE','UL']);
 expect(screen.getByRole('cell',{name:'Repair hook'})).toBeInTheDocument();
 expect(visible).toHaveBeenCalledTimes(1);
 expect(screen.queryByRole('button')).not.toBeInTheDocument();
 expect(screen.queryByRole('textbox')).not.toBeInTheDocument();
});
it('keeps streamed checklist state, links, media and HTML inert',()=>{
 const view=render(<SurfaceConstructionPreview markdown={'- [ ] Review the page\n- [x] Read the chart\n\n[Source](https://example.com) ![Workshop](https://example.com/picture.png)\n\n<script>doSomething()</script>\n'}/>);
 expect(screen.getByLabelText('Unchecked in preview')).toBeInTheDocument();
 expect(screen.getByLabelText('Checked in preview')).toBeInTheDocument();
 expect(view.container.querySelector('input, a, img, script, iframe')).toBeNull();
 expect(view.container.textContent).toContain('Workshop');
 expect(view.container.textContent).toContain('<script>doSomething()</script>');
});
it('reveals only when received content is visible and reports interruption honestly',()=>{
 const visible=vi.fn();const view=render(<SurfaceConstructionPreview markdown="" onVisible={visible}/>);
 expect(visible).not.toHaveBeenCalled();expect(view.container.textContent).toBe('');
 view.rerender(<SurfaceConstructionPreview markdown={'A received paragraph.\n'} status="incomplete" onVisible={visible}/>);
 expect(visible).toHaveBeenCalledTimes(1);
 expect(screen.getByRole('region',{name:'Object construction'})).toHaveAttribute('aria-busy','false');
 expect(screen.getByRole('status')).toHaveTextContent('Incomplete');
 expect(screen.queryByText('Ready')).not.toBeInTheDocument();
});
