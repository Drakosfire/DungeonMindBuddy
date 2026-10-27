import {act,fireEvent,render,screen,waitFor} from "@testing-library/react";
import {webcrypto,createHash} from "node:crypto";
import {canonical} from "../../shared/sourcePassageProtocol";
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
it("rehydrates an exact saved reference from the bounded index without reading note text",async()=>{
 const refs=[{run_id:"run-a",review_revision:54,sha256:"a".repeat(64)}];localStorage.setItem("dmb.ingestion.session-evidence.elderwyld.c2:30",JSON.stringify(refs));
 const change=vi.fn();render(<SessionEvidencePicker worldId="elderwyld" targetKey="c2:30" onChange={change}/>);
 fireEvent.click(screen.getByText(/Supplemental session evidence/));
 expect(await screen.findByText(/Played session · ended/)).toBeInTheDocument();
 expect(change).toHaveBeenLastCalledWith(refs);expect(listSessionEvidence).toHaveBeenCalledTimes(1);expect(readSessionEvidence).not.toHaveBeenCalled();
});
it("keeps older saved refs visible without downloading their source bodies",async()=>{
 const refs=[{run_id:"old-run-id",review_revision:4,sha256:"a".repeat(64)}];localStorage.setItem("dmb.ingestion.session-evidence.elderwyld.c2:30",JSON.stringify(refs));
 vi.mocked(listSessionEvidence).mockResolvedValue([indexItem]);const change=vi.fn();
 render(<SessionEvidencePicker worldId="elderwyld" targetKey="c2:30" onChange={change}/>);
 fireEvent.click(screen.getByText(/Supplemental session evidence/));
 const box=await screen.findByRole("checkbox",{name:/Saved session · old-run- · previously selected/});
 expect(box).toBeChecked();expect(readSessionEvidence).not.toHaveBeenCalled();expect(change).toHaveBeenLastCalledWith(refs);
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
 let resolvePending!:(value:SessionEvidenceIndexItem[])=>void;const pending=new Promise<SessionEvidenceIndexItem[]>(resolve=>{resolvePending=resolve});
 vi.mocked(listSessionEvidence).mockReturnValue(pending);
 const change=vi.fn();render(<SessionEvidencePicker worldId="elderwyld" targetKey="c2:30" onChange={change}/>);
 fireEvent.click(screen.getByText(/Supplemental session evidence/));
 fireEvent.click(await screen.findByRole("button",{name:"Clear selected session evidence"}));expect(change).toHaveBeenLastCalledWith([]);
 await act(async()=>{resolvePending([indexItem]);await pending});
 expect(change).toHaveBeenLastCalledWith([]);expect(localStorage.getItem("dmb.ingestion.session-evidence.elderwyld.c2:30")).toBeNull();
});
it("keeps the recent-session index when clear interrupts saved-ref hydration",async()=>{
 const refs=[{run_id:"run-a",review_revision:54,sha256:"a".repeat(64)}];localStorage.setItem("dmb.ingestion.session-evidence.elderwyld.c2:30",JSON.stringify(refs));
 let resolveIndex!:(value:SessionEvidenceIndexItem[])=>void;const pendingIndex=new Promise<SessionEvidenceIndexItem[]>(resolve=>{resolveIndex=resolve});
 vi.mocked(listSessionEvidence).mockReturnValue(pendingIndex);
 const change=vi.fn();render(<SessionEvidencePicker worldId="elderwyld" targetKey="c2:30" onChange={change}/>);
 fireEvent.click(screen.getByText(/Supplemental session evidence/));
 fireEvent.click(await screen.findByRole("button",{name:"Clear selected session evidence"}));
 await act(async()=>{resolveIndex([indexItem]);await pendingIndex});
 expect(await screen.findByText(/Played session · ended/)).toBeInTheDocument();expect(change).toHaveBeenLastCalledWith([]);
});
it("surfaces an index failure that arrives after clear",async()=>{
 const refs=[{run_id:"run-a",review_revision:54,sha256:"a".repeat(64)}];localStorage.setItem("dmb.ingestion.session-evidence.elderwyld.c2:30",JSON.stringify(refs));
 let rejectIndex!:(cause:Error)=>void;const pendingIndex=new Promise<SessionEvidenceIndexItem[]>((_resolve,reject)=>{rejectIndex=reject});
 vi.mocked(listSessionEvidence).mockReturnValue(pendingIndex);
 const change=vi.fn();render(<SessionEvidencePicker worldId="elderwyld" targetKey="c2:30" onChange={change}/>);
 fireEvent.click(screen.getByText(/Supplemental session evidence/));
 fireEvent.click(await screen.findByRole("button",{name:"Clear selected session evidence"}));
 await act(async()=>{rejectIndex(new Error("Index offline"));await Promise.resolve()});
 expect(await screen.findByRole("alert")).toHaveTextContent("Index offline");expect(screen.queryByText(/No ended sessions/)).not.toBeInTheDocument();
});
it("renders pinned sources read-only without a reflections editor",async()=>{
 vi.stubGlobal('crypto',webcrypto);
 const packet={...item,checkpoint_run_revision:8,session_content_sha256:'c'.repeat(64),
  sources:item.sources.map(source=>({...source,sha256:createHash('sha256').update(source.text).digest('hex')}))};
 const {sha256:_old,...body}=packet;
 vi.mocked(readSessionEvidence).mockResolvedValue({...packet,sha256:createHash('sha256').update(canonical(body)).digest('hex')});
 render(<SessionEvidenceViewer worldId="elderwyld" runId="run-a" revision={54}/>);
 expect(await screen.findByText("Players want combat next time.")).toBeInTheDocument();expect(readSessionEvidence).toHaveBeenCalledWith("elderwyld","run-a",54);
 expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
});
