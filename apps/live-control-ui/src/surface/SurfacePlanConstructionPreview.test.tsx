import {render,screen,cleanup} from '@testing-library/react';
import {afterEach,it,expect,vi} from 'vitest';
import {SurfacePlanConstructionPreview} from './SurfacePlanConstructionPreview';
afterEach(cleanup);
it('shows complete plan rows inertly and never turns generated markup into controls',()=>{
 const visible=vi.fn();const steps=[{text:'Discuss <img src=x> [a](https://example.com)',kind:'discuss' as const}];
 const view=render(<SurfacePlanConstructionPreview steps={steps} status="building" onVisible={visible}/>);
 expect(screen.getByRole('region',{name:'Plan construction'})).toHaveAttribute('aria-busy','true');
 expect(screen.getAllByRole('listitem')).toHaveLength(1);expect(visible).toHaveBeenCalledTimes(1);
 view.rerender(<SurfacePlanConstructionPreview steps={[...steps,{text:'Prepare one sentence.',kind:'prepare_insertion'}]} status="incomplete" onVisible={visible}/>);
 expect(screen.getAllByRole('listitem')).toHaveLength(2);expect(screen.getByRole('status')).toHaveTextContent('Incomplete');
 for(const role of ['checkbox','button','textbox','link','img'])expect(screen.queryByRole(role)).toBeNull();
 expect(visible).toHaveBeenCalledTimes(1);
});
it('reveals a complete outcome before the first row without creating editing or execution controls',()=>{
 const visible=vi.fn();render(<SurfacePlanConstructionPreview objective="Develop a useful shop scene." steps={[]} status="building" onVisible={visible}/>);
 expect(screen.getByText('Expected outcome')).toBeInTheDocument();expect(screen.getByText('Develop a useful shop scene.')).toBeInTheDocument();
 expect(visible).toHaveBeenCalledTimes(1);expect(screen.queryByRole('textbox')).toBeNull();expect(screen.queryByRole('button')).toBeNull();
});

it('shows true and false proposed choices as inert observations',()=>{
 render(<SurfacePlanConstructionPreview steps={[{text:'Discuss first.',kind:'discuss',selected:true},{text:'Write later.',kind:'prepare_insertion',selected:false}]} status="building"/>);
 const rows=screen.getAllByRole('listitem');expect(rows[0]).toHaveTextContent('☑');expect(rows[1]).toHaveTextContent('☐');
 expect(screen.queryByRole('checkbox')).toBeNull();expect(screen.queryByRole('button')).toBeNull();
});
