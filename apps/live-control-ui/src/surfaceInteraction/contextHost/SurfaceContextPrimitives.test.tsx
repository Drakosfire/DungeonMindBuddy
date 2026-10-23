import {afterEach, describe, expect, it, vi} from 'vitest';
import {render, screen} from '@testing-library/react';
import {SurfaceContextPopover} from './SurfaceContextPrimitives';

afterEach(()=>vi.restoreAllMocks());

describe('shared Surface popover viewport placement',()=>{
  it.each([
    ['below','end',20,52,1200,'start'],
    ['below','start',1140,1172,1200,'end'],
    ['below','end',600,632,1200,'end'],
    ['beside','start',20,52,1200,'end'],
    ['beside','end',1140,1172,1200,'start'],
    ['beside','end',20,52,700,'start'],
  ] as const)('%s %s at %s stays inside viewport', (placement,align,left,right,viewport,expected)=>{
    vi.stubGlobal('innerWidth',viewport);
    vi.spyOn(HTMLElement.prototype,'getBoundingClientRect').mockImplementation(function(){
      return {left,right,width:right-left,top:10,bottom:42,height:32,x:left,y:10,toJSON:()=>({}),
        ...(this.classList.contains('surface-context-popover__panel')?{width:256}:{} )};
    });
    render(<SurfaceContextPopover open onOpenChange={()=>{}} align={align} placement={placement} trigger={<button>Start session</button>}>Confirmation</SurfaceContextPopover>);
    expect(screen.getByRole('dialog')).toHaveAttribute('data-align',expected);
    vi.unstubAllGlobals();
  });
});
