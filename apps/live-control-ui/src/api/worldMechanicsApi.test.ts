import { afterEach, expect, it, vi } from "vitest";
import { associateWorldMechanics, listWorldMechanicsAssociations, setNativeGraphAccessToken } from "./liveApi";
import type { AssociateWorldMechanicsRequest } from "./worldMechanicsTypes";
afterEach(()=>{vi.restoreAllMocks();setNativeGraphAccessToken("");});
it("authenticates exact association reads and writes without altering the request",async()=>{
  setNativeGraphAccessToken("association-test-token");
  const fetch=vi.spyOn(globalThis,"fetch").mockImplementation(async()=>Response.json({fixture:true}));
  const request={request_id:"fixed-key",draft_id:"draft-one",expected_draft_version:3,expected_version:0,
    target:{managed_world_id:"elderwyld"}} as AssociateWorldMechanicsRequest;
  await listWorldMechanicsAssociations("elderwyld");await associateWorldMechanics("elderwyld",request);
  expect(fetch).toHaveBeenCalledTimes(2);
  for(const [url,init] of fetch.mock.calls){
    expect(String(url)).toBe("/api/live/world-mechanics/associations?world_id=elderwyld");
    expect(new Headers(init?.headers).get("Authorization")).toBe("Bearer association-test-token");
    expect(init?.credentials).toBe("same-origin");expect(init?.redirect).toBe("error");
  }
  expect(JSON.parse(String(fetch.mock.calls[1][1]?.body))).toEqual(request);
});
