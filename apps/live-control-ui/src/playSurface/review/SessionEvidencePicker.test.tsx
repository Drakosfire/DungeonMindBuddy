import {act,fireEvent,render,screen,waitFor} from "@testing-library/react";
import {beforeEach,expect,it,vi} from "vitest";
import {SessionEvidencePicker} from "./SessionEvidencePicker";
import {SessionEvidenceViewer} from "./SessionEvidenceViewer";
import {listSessionEvidence,readSessionEvidence,type SessionEvidence,type SessionEvidenceIndexItem} from "./sessionEvidenceApi";
vi.mock("./sessionEvidenceApi",()=>({listSessionEvidence:vi.fn(),readSessionEvidence:vi.fn()}));
const item={schema_version:"dmb_session_evidence_v1",world_id:"elderwyld",run_id:"run-a",review_revision:54,sha256:"a".repeat(64),ended_at:"2026-10-19T00:00:00Z",citation_url:"/play?world=elderwyld&run=run-a&evidence_revision=54",sources:[{kind:"closing_reflections",text:"Players want combat next time.",sha256:"b".repeat(64),citation_url:"/play?world=elderwyld&run=run-a&evidence_revision=54"}]} as SessionEvidence;
const indexItem={run_id:"run-a",review_revision:54,title:"Played session",ended_at:"2026-10-19T00:00:00Z",source_count:1,citation_url:"/play?world=elderwyld&run=run-a&evidence_revision=54"} as SessionEvidenceIndexItem;
const indexItemB={...indexItem,run_id:"run-b",citation_url:"/play?world=elderwyld&run=run-b&evidence_revision=54"};
beforeEach(()=>{localStorage.clear();vi.resetAllMocks();vi.mocked(listSessionEvidence).mockResolvedValue([indexItem]);vi.mocked(readSessionEvidence).mockResolvedValue(item)});
it("requires explicit attachment and emits exact pinned references",async()=>{
 const change=vi.fn();render(<SessionEvidencePicker worldId="elderwyld" targetKey="c2:30" onChange={change}/>);
 fireEvent.click(screen.getByText(/Supplemental session evidence/));const box=await screen.findByRole("checkbox");expect(box).not.toBeChecked();expect(readSessionEvidence).not.toHaveBeenCalled();
 fireEvent.click(box);await waitFor(()=>expect(change).toHaveBeenLastCalledWith([{run_id:"run-a",review_revision:54,sha256:"a".repeat(64)}]));expect(readSessionEvidence).toHaveBeenCalledWith("elderwyld","run-a",54);
 expect(screen.getByRole("link",{name:"Read saved evidence"})).toHaveAttribute("href",item.citation_url);
});
it("keeps stored attachment refs when reads fail, instead of silently dropping them",async()=>{
 const refs=[{run_id:"run-a",review_revision:54,sha256:"a".repeat(64)}];localStorage.setItem("dmb.ingestion.session-evidence.elderwyld.c2:30",JSON.stringify(refs));
 vi.mocked(listSessionEvidence).mockRejectedValue(new Error("offline"));const change=vi.fn();
 render(<SessionEvidencePicker worldId="elderwyld" targetKey="c2:30" onChange={change}/>);
 fireEvent.click(screen.getByText(/Supplemental session evidence/));expect(await screen.findByRole("alert")).toHaveTextContent("offline");expect(change).toHaveBeenLastCalledWith(refs);
 fireEvent.click(screen.getByRole("button",{name:"Clear selected session evidence"}));expect(change).toHaveBeenLastCalledWith([]);
});
it("does not restore cleared refs when a new detail read settles late",async()=>{
 const refs=[{run_id:"run-a",review_revision:54,sha256:"a".repeat(64)}];localStorage.setItem("dmb.ingestion.session-evidence.elderwyld.c2:30",JSON.stringify(refs));
 vi.mocked(listSessionEvidence).mockResolvedValue([indexItemB]);
 let resolvePending!:(value:SessionEvidence)=>void;const pending=new Promise<SessionEvidence>(resolve=>{resolvePending=resolve});
 vi.mocked(readSessionEvidence).mockImplementation((_worldId,runId)=>runId==="run-a"?Promise.resolve(item):pending);
 const change=vi.fn();render(<SessionEvidencePicker worldId="elderwyld" targetKey="c2:30" onChange={change}/>);
 fireEvent.click(screen.getByText(/Supplemental session evidence/));const boxes=await screen.findAllByRole("checkbox");
 fireEvent.click(boxes[1]);expect(await screen.findByText(/Loading source/)).toBeInTheDocument();
 fireEvent.click(screen.getByRole("button",{name:"Clear selected session evidence"}));expect(change).toHaveBeenLastCalledWith([]);
 await act(async()=>{resolvePending({...item,run_id:"run-b",citation_url:indexItemB.citation_url});await pending});
 expect(change).toHaveBeenLastCalledWith([]);expect(localStorage.getItem("dmb.ingestion.session-evidence.elderwyld.c2:30")).toBeNull();
});
it("does not restore saved refs when initial hydration settles after clear",async()=>{
 const refs=[{run_id:"run-a",review_revision:54,sha256:"a".repeat(64)}];localStorage.setItem("dmb.ingestion.session-evidence.elderwyld.c2:30",JSON.stringify(refs));
 let resolvePending!:(value:SessionEvidence)=>void;const pending=new Promise<SessionEvidence>(resolve=>{resolvePending=resolve});
 vi.mocked(readSessionEvidence).mockReturnValue(pending);
 const change=vi.fn();render(<SessionEvidencePicker worldId="elderwyld" targetKey="c2:30" onChange={change}/>);
 fireEvent.click(screen.getByText(/Supplemental session evidence/));
 fireEvent.click(await screen.findByRole("button",{name:"Clear selected session evidence"}));expect(change).toHaveBeenLastCalledWith([]);
 await act(async()=>{resolvePending(item);await pending});
 expect(change).toHaveBeenLastCalledWith([]);expect(localStorage.getItem("dmb.ingestion.session-evidence.elderwyld.c2:30")).toBeNull();
});
it("renders pinned sources read-only without a reflections editor",async()=>{
 render(<SessionEvidenceViewer worldId="elderwyld" runId="run-a" revision={54}/>);
 expect(await screen.findByText("Players want combat next time.")).toBeInTheDocument();expect(readSessionEvidence).toHaveBeenCalledWith("elderwyld","run-a",54);
 expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
});
