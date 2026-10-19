import {fireEvent,render,screen,waitFor} from "@testing-library/react";
import {beforeEach,expect,it,vi} from "vitest";
import {SurfaceContextProvider,SurfaceContextHost} from "../../surfaceInteraction/contextHost";
import {SessionReviewPanel} from "./SessionReviewPanel";
import {readSessionReview,saveSessionReview,type SessionReview} from "./sessionReviewApi";
vi.mock("./sessionReviewApi",async original=>({...await original<typeof import("./sessionReviewApi")>(),readSessionReview:vi.fn(),saveSessionReview:vi.fn()}));
const content={content_sha256:"a".repeat(64),markdown:"Prepared: the town burns"} as never;
const ended={schema_version:"dmb_session_review_v1",world_id:"elderwyld",run_id:"run-a",revision:1,status:"ended",final_thoughts:"A human recollection.",checkpoint:{run_revision:7,captured_at:"2026-10-19T00:00:00Z",content,progress:{notes_by_element_id:{"scene:gate":"The party bypassed Edge."}}}} as SessionReview;
function mount(blocked=false){render(<SurfaceContextProvider><SessionReviewPanel runId="run-a" worldId="elderwyld" runRevision={7} content={content} blocked={blocked} sceneTitles={{"scene:gate":"Approach"}}/><SurfaceContextHost/></SurfaceContextProvider>)}
beforeEach(()=>{localStorage.clear();vi.resetAllMocks();window.history.replaceState({},"","/play?world=elderwyld&run=run-a");vi.mocked(readSessionReview).mockResolvedValue({world_id:"elderwyld",run_id:"run-a",review:null,source_changed:false});vi.mocked(saveSessionReview).mockResolvedValue(ended)});
it("requires an explicit end with exact saved source and blocks local edits",async()=>{
 mount(true);fireEvent.click(screen.getByRole("button",{name:"End session",exact:true}));
 expect(await screen.findByRole("button",{name:"Finish session"})).toBeDisabled();expect(saveSessionReview).not.toHaveBeenCalled();
});
it("ends with optional reflections and autosaves later recollections separately",async()=>{
 mount();fireEvent.click(screen.getByRole("button",{name:"End session",exact:true}));
 fireEvent.change(await screen.findByLabelText("Final thoughts and recollections (optional)"),{target:{value:"A human recollection."}});
 fireEvent.click(screen.getByRole("button",{name:"Finish session"}));
 expect(await screen.findByLabelText("Final thoughts and recollections")).toHaveValue(ended.final_thoughts);
 expect(saveSessionReview).toHaveBeenCalledWith("run-a","elderwyld",expect.any(String),expect.objectContaining({action:"end",final_thoughts:"A human recollection.",expected_revision:0,expected_run_revision:7,expected_content_sha256:"a".repeat(64)}));
 vi.mocked(saveSessionReview).mockResolvedValue({...ended,revision:2,final_thoughts:"I remember a survivor."});
 fireEvent.change(screen.getByLabelText("Final thoughts and recollections"),{target:{value:"I remember a survivor."}});
 await waitFor(()=>expect(saveSessionReview).toHaveBeenLastCalledWith("run-a","elderwyld",expect.any(String),expect.objectContaining({action:"save",expected_revision:1,final_thoughts:"I remember a survivor."})),{timeout:2000});
 expect(screen.queryByText("Prepared: the town burns")).not.toBeInTheDocument();
});
it("retains browser text on conflicting saved review and requires deliberate resolution",async()=>{
 vi.mocked(readSessionReview).mockResolvedValue({world_id:"elderwyld",run_id:"run-a",review:ended,source_changed:false});
 localStorage.setItem("dmb.session-reflections.elderwyld.run-a",JSON.stringify({revision:0,text:"My unsaved recollection"}));
 mount();expect(await screen.findByLabelText("Final thoughts and recollections")).toHaveValue("My unsaved recollection");
 expect(screen.getByRole("alert")).toHaveTextContent("Your text is retained");expect(saveSessionReview).not.toHaveBeenCalled();
});
it("recovers browser text even when the first server GET fails",async()=>{
 localStorage.setItem("dmb.session-reflections.elderwyld.run-a",JSON.stringify({revision:0,text:"Fresh memory, never overwrite"}));
 vi.mocked(readSessionReview).mockRejectedValueOnce(new Error("offline")).mockResolvedValueOnce({world_id:"elderwyld",run_id:"run-a",review:ended,source_changed:false});
 mount();fireEvent.click(screen.getByRole("button",{name:"End session",exact:true}));
 expect(await screen.findByRole("alert")).toHaveTextContent("offline");
 fireEvent.click(screen.getByRole("button",{name:"Reload saved review, keep my text"}));
 expect(await screen.findByLabelText("Final thoughts and recollections")).toHaveValue("Fresh memory, never overwrite");
 fireEvent.click(screen.getByRole("button",{name:"Keep my draft"}));
 expect(JSON.parse(localStorage.getItem("dmb.session-reflections.elderwyld.run-a")!).text).toBe("Fresh memory, never overwrite");
 expect(screen.getByLabelText("Final thoughts and recollections")).toHaveValue("Fresh memory, never overwrite");
});
