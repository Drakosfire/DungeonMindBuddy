import {afterEach,expect,it,vi} from "vitest";
import {setNativeGraphAccessToken} from "../../api/liveApi";
import {readSessionReview} from "./sessionReviewApi";
afterEach(()=>{setNativeGraphAccessToken(null);vi.restoreAllMocks()});
it("authenticates the exact World review and refuses a foreign response",async()=>{
 setNativeGraphAccessToken("synthetic-review-token");
 const fetch=vi.spyOn(globalThis,"fetch").mockResolvedValue(Response.json({world_id:"other",run_id:"run-a",review:null}));
 await expect(readSessionReview("run-a","elderwyld")).rejects.toThrow("another session");
 expect(fetch.mock.calls[0][0]).toBe("/api/live/world-play-runs/v2/run-a/review?world_id=elderwyld");
 expect(new Headers(fetch.mock.calls[0][1]?.headers).get("Authorization")).toBe("Bearer synthetic-review-token");
 expect(fetch.mock.calls[0][1]?.redirect).toBe("error");
});
it("does not turn legacy generated text into final thoughts",async()=>{
 setNativeGraphAccessToken("synthetic-review-token");
 vi.spyOn(globalThis,"fetch").mockResolvedValue(Response.json({world_id:"elderwyld",run_id:"run-a",source_changed:false,review:{schema_version:"dmb_session_review_v1",world_id:"elderwyld",run_id:"run-a",revision:2,status:"ended",draft_markdown:"Old generated recap text",checkpoint:{progress:{notes_by_element_id:{}},content:{content_sha256:"a".repeat(64)}}}}));
 const value=await readSessionReview("run-a","elderwyld");expect(value.review?.final_thoughts).toBe("");expect(value.review?.draft_markdown).toBe("Old generated recap text");
});
