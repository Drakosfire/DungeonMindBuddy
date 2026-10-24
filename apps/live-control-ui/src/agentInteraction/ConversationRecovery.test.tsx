import {act,fireEvent,render,screen} from '@testing-library/react';
import {expect,it,vi} from 'vitest';
import {ConversationRecovery} from './ConversationRecovery';

it('retries once on explicit click, with an accessible icon and in-flight guard',async()=>{
 let finish!:()=>void;const retry=vi.fn(()=>new Promise<void>(resolve=>{finish=resolve;}));
 render(<ConversationRecovery question="Discuss the quarry" blocked={false} onRetry={retry}/>);
 const button=screen.getByRole('button',{name:'Retry question'});expect(button).toHaveTextContent('');
 expect(button.querySelector('svg[aria-hidden="true"]')).not.toBeNull();expect(retry).not.toHaveBeenCalled();
 fireEvent.click(button);fireEvent.click(button);expect(retry).toHaveBeenCalledExactlyOnceWith('Discuss the quarry');expect(button).toBeDisabled();
 await act(async()=>finish());expect(button).toBeEnabled();
});
it('blocks unresolved requests and exposes a real retry failure without extra review ceremony',async()=>{
 const retry=vi.fn().mockRejectedValue(new Error('Retry transport unavailable'));
 const view=render(<ConversationRecovery question="Discuss the quarry" blocked onRetry={retry}/>);
 fireEvent.click(screen.getByRole('button'));expect(retry).not.toHaveBeenCalled();
 view.rerender(<ConversationRecovery question="Discuss the quarry" blocked={false} onRetry={retry}/>);
 fireEvent.click(screen.getByRole('button'));expect(await screen.findByRole('alert')).toHaveTextContent('Retry transport unavailable');
 expect(screen.getByRole('button')).toBeEnabled();
});
