import {cleanup,fireEvent,render,screen,waitFor} from '@testing-library/react';
import {afterEach,expect,it} from 'vitest';
import {SurfaceObjectMenu} from './SurfaceObjectMenu';
afterEach(cleanup);
it('mounts diagnostics only with menu open and Developer enabled; ordinary recovery stays available',async()=>{
 const {container}=render(<><button>Check Save</button><SurfaceObjectMenu label="Plan options"><pre>exact retained receipt</pre></SurfaceObjectMenu></>);
 expect(screen.getByRole('button',{name:'Check Save'})).toBeEnabled();
 expect(screen.queryByText('exact retained receipt')).toBeNull();
 const menu=container.querySelector('details')!;menu.open=true;fireEvent(menu,new Event('toggle'));
 fireEvent.click(await screen.findByLabelText('Developer'));expect(screen.getByText('exact retained receipt')).toBeVisible();
 menu.open=false;fireEvent(menu,new Event('toggle'));
 await waitFor(()=>expect(screen.queryByText('exact retained receipt')).toBeNull());
});
