import { act, cleanup, renderHook, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import * as api from '../api/liveApi';
import { useSavedMediaImage } from './useSavedMediaImage';
const id='ac6c15cc-8c68-4732-8ae2-d9f3f051393a';
const other='bc6c15cc-8c68-4732-8ae2-d9f3f051393a';
const metadata={asset_id:id,state:'staged',mime_type:'image/png',byte_length:1,content_sha256:'a'.repeat(64)};
const original={...metadata,data_url:'data:image/png;base64,AA=='};
let epoch=0;
let fetcher: ReturnType<typeof vi.spyOn<typeof api, 'authenticatedApiFetch'>>;
beforeEach(()=>{
 epoch=0;vi.spyOn(api,'getNativeGraphAccessGeneration').mockImplementation(()=>epoch);
 vi.stubGlobal('URL',URL);
 Object.defineProperty(URL,'createObjectURL',{configurable:true,value:vi.fn(()=> 'blob:private')});
 Object.defineProperty(URL,'revokeObjectURL',{configurable:true,value:vi.fn()});
 fetcher=vi.spyOn(api,'authenticatedApiFetch').mockImplementation(async path=>({response:Response.json(path.endsWith('/metadata')?metadata:original),csrf:null,requestEpoch:epoch}));
});
afterEach(()=>{cleanup();vi.restoreAllMocks();vi.unstubAllGlobals();});
it('reads an authenticated staged original and owns its Blob URL',async()=>{
 const {result,unmount}=renderHook(()=>useSavedMediaImage(id));
 await waitFor(()=>expect(result.current.url).toBe('blob:private'));
 expect(fetcher).toHaveBeenCalledTimes(2);
 expect(fetcher).toHaveBeenLastCalledWith(`/api/live/media/images/${id}`,expect.objectContaining({cache:'no-store',signal:expect.any(AbortSignal)}));
 const blob=vi.mocked(URL.createObjectURL).mock.calls[0][0] as Blob;
 expect(blob.size).toBe(1);expect(blob.type).toBe('image/png');
 unmount();expect(URL.revokeObjectURL).toHaveBeenCalledExactlyOnceWith('blob:private');
});
it('keeps ready CDN resolution without reading an original',async()=>{
 fetcher.mockResolvedValue({response:Response.json({...metadata,state:'ready',delivery_url:'https://imagedelivery.net/account/asset/public'}),csrf:null,requestEpoch:0});
 const {result}=renderHook(()=>useSavedMediaImage(id));
 await waitFor(()=>expect(result.current.url).toBe('https://imagedelivery.net/account/asset/public'));
 expect(fetcher).toHaveBeenCalledTimes(1);expect(URL.createObjectURL).not.toHaveBeenCalled();
});
it.each(['uploading','unknown','other','foreign-ready','bad-ready'])('rejects %s without fallback',async scenario=>{
 fetcher.mockResolvedValue({response:Response.json({...metadata,state:scenario==='foreign-ready'||scenario==='bad-ready'?'ready':scenario,asset_id:scenario==='other'?other:id,delivery_url:scenario==='bad-ready'?'http://imagedelivery.net/a':'https://evil.test/a'}),csrf:null,requestEpoch:0});
 const {result}=renderHook(()=>useSavedMediaImage(id));
 await waitFor(()=>expect(result.current.status).toContain('unavailable'));
 expect(result.current.url).toBeNull();expect(fetcher).toHaveBeenCalledTimes(1);
});
it.each(['identity','mime','length','digest','body','empty','state','denied'])('rejects mismatched original: %s',async scenario=>{
 const record={...original};
 if(scenario==='identity')record.asset_id=other;
 if(scenario==='mime')record.mime_type='image/jpeg';
 if(scenario==='length')record.byte_length=2;
 if(scenario==='digest')record.content_sha256='b'.repeat(64);
 if(scenario==='body')record.data_url='data:image/jpeg;base64,AA==';
 if(scenario==='empty')record.data_url='data:image/png;base64,';
 if(scenario==='state')record.state='unknown';
 fetcher.mockResolvedValueOnce({response:Response.json(metadata),csrf:null,requestEpoch:0}).mockResolvedValueOnce({response:scenario==='denied'?new Response(null,{status:403}):Response.json(record),csrf:null,requestEpoch:0});
 const {result}=renderHook(()=>useSavedMediaImage(id));
 await waitFor(()=>expect(result.current.status).toContain('unavailable'));
 expect(result.current.url).toBeNull();expect(URL.createObjectURL).not.toHaveBeenCalled();
});
it('revokes private presentation on owner change when new access fails',async()=>{
 const {result}=renderHook(()=>useSavedMediaImage(id));
 await waitFor(()=>expect(result.current.url).toBe('blob:private'));
 fetcher.mockResolvedValue({response:new Response(null,{status:403}),csrf:null,requestEpoch:1});
 act(()=>{epoch=1;window.dispatchEvent(new Event(api.NATIVE_GRAPH_ACCESS_TOKEN_CHANGED_EVENT));});
 expect(result.current.url).toBeNull();expect(URL.revokeObjectURL).toHaveBeenCalledWith('blob:private');
 await waitFor(()=>expect(result.current.status).toContain('unavailable'));
});
it('rejects a late original after asset replacement',async()=>{
 let finish!:(value:Awaited<ReturnType<typeof api.authenticatedApiFetch>>)=>void;
 fetcher.mockResolvedValueOnce({response:Response.json(metadata),csrf:null,requestEpoch:0}).mockImplementationOnce(()=>new Promise(resolve=>{finish=resolve;}));
 const {result,rerender}=renderHook(({asset})=>useSavedMediaImage(asset),{initialProps:{asset:id}});
 await waitFor(()=>expect(fetcher).toHaveBeenCalledTimes(2));
 fetcher.mockResolvedValue({response:new Response(null,{status:403}),csrf:null,requestEpoch:0});
 rerender({asset:other});expect(result.current.url).toBeNull();
 await act(async()=>finish({response:Response.json(original),csrf:null,requestEpoch:0}));
 expect(URL.createObjectURL).not.toHaveBeenCalled();
});
