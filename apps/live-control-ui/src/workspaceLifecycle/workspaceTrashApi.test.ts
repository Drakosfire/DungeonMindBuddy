import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { setNativeGraphAccessToken } from "../api/liveApi";
import { changeWorkspaceTrash, listWorkspaceTrash } from "./workspaceTrashApi";
const doc={kind:"document" as const,id:"doc-a",title:"Disposable",surface:"plan" as const,revision:7};
const session={...doc,kind:"session" as const,id:"run-a",surface:"play" as const,revision:5,content_revision:13};
const result=(target=doc)=>({...target,status:"trashed",updated_at:"2026-10-19T00:00:00Z"});
beforeEach(()=>setNativeGraphAccessToken("synthetic-token"));
afterEach(()=>{setNativeGraphAccessToken(null);vi.restoreAllMocks();});
it.each([doc,session])("sends the owning CAS and auth for $kind deletion",async target=>{
 const fetch=vi.spyOn(globalThis,"fetch").mockResolvedValue(Response.json({...target,status:"trashed",updated_at:"2026-10-19T00:00:00Z"}));
 await changeWorkspaceTrash("world-a",target,"trash");
 const [url,init]=fetch.mock.calls[0]; expect(url).toBe(`/api/live/world-workspace/${target.kind==='session'?'sessions':'documents'}/${target.id}/trash?world_id=world-a`);
 expect(new Headers(init?.headers).get("Authorization")).toBe("Bearer synthetic-token");expect(init?.redirect).toBe("error");
 expect(JSON.parse(init?.body as string)).toEqual({expected_revision:target.revision,...(target.kind==='session'?{expected_content_revision:13}:{})});
});
it("authenticates Trash inventory and rejects a different World",async()=>{
 const fetch=vi.spyOn(globalThis,"fetch").mockResolvedValue(Response.json({world_id:"other",items:[]}));
 await expect(listWorkspaceTrash("world-a")).rejects.toThrow("does not match");expect(new Headers(fetch.mock.calls[0][1]?.headers).get("Authorization")).toBe("Bearer synthetic-token");
});
it("rejects an unrelated successful mutation response",async()=>{
 vi.spyOn(globalThis,"fetch").mockResolvedValue(Response.json({...result(),id:"other"}));
 await expect(changeWorkspaceTrash("world-a",doc,"trash")).rejects.toThrow("does not match");
});
it("does not retry an uncertain lifecycle POST",async()=>{
 const fetch=vi.spyOn(globalThis,"fetch").mockRejectedValue(new TypeError("interrupted"));
 await expect(changeWorkspaceTrash("world-a",session,"trash")).rejects.toThrow("interrupted");expect(fetch).toHaveBeenCalledOnce();
});
it("reuses cookie session CSRF for lifecycle mutation",async()=>{
 setNativeGraphAccessToken(null);const fetch=vi.spyOn(globalThis,"fetch").mockResolvedValueOnce(Response.json({status:"active",csrf_token:"synthetic-csrf"})).mockResolvedValueOnce(Response.json(result()));
 await changeWorkspaceTrash("world-a",doc,"trash");expect(fetch.mock.calls[0][0]).toBe('/api/live/agent/local-session');expect(new Headers(fetch.mock.calls[1][1]?.headers).get('X-DMB-Graph-CSRF')).toBe('synthetic-csrf');
});
