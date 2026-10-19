import {afterEach,expect,it,vi} from "vitest";
import {setNativeGraphAccessToken} from "../../api/liveApi";
import {readSessionReview,exportSessionReview,type SessionReview} from "./sessionReviewApi";
afterEach(()=>{setNativeGraphAccessToken(null);vi.restoreAllMocks()});
it("authenticates the exact World review and refuses a foreign response",async()=>{
 setNativeGraphAccessToken("synthetic-review-token");
 const fetch=vi.spyOn(globalThis,"fetch").mockResolvedValue(Response.json({world_id:"other",run_id:"run-a",review:null}));
 await expect(readSessionReview("run-a","elderwyld")).rejects.toThrow("another session");
 expect(fetch.mock.calls[0][0]).toBe("/api/live/world-play-runs/v2/run-a/review?world_id=elderwyld");
 expect(new Headers(fetch.mock.calls[0][1]?.headers).get("Authorization")).toBe("Bearer synthetic-review-token");
 expect(fetch.mock.calls[0][1]?.redirect).toBe("error");
});
it("exports recollections with original notes and checkpoint references, without prepared prose",()=>{
 const value={run_id:"r",world_id:"w",revision:2,draft_markdown:"Party escaped",checkpoint:{captured_at:"date",run_revision:7,content:{content_sha256:"abc",markdown:"Unplayed proposal"},progress:{notes_by_element_id:{gate:"Original note"}}}} as unknown as SessionReview;
 const exported=exportSessionReview(value);expect(exported).toContain("Party escaped");expect(exported).toContain("Original note");expect(exported).toContain("abc");expect(exported).not.toContain("Unplayed proposal");
});
