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
it('does not invent a preview before the actual table delimiter',()=>{
 const view=render(<SurfaceConstructionPreview markdown={'| Name | Detail |\n'}/>);
 expect(view.container.textContent).toBe('');expect(screen.queryByRole('table')).toBeNull();
});
