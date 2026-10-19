import {act,fireEvent,render,screen,waitFor} from "@testing-library/react";
import {beforeEach,expect,it,vi} from "vitest";
import {SessionEvidencePicker} from "./SessionEvidencePicker";
import {SessionEvidenceViewer} from "./SessionEvidenceViewer";
import {listSessionEvidence,readSessionEvidence,type SessionEvidence} from "./sessionEvidenceApi";
vi.mock("./sessionEvidenceApi",()=>({listSessionEvidence:vi.fn(),readSessionEvidence:vi.fn()}));
const item={schema_version:"dmb_session_evidence_v1",world_id:"elderwyld",run_id:"run-a",review_revision:54,sha256:"a".repeat(64),ended_at:"2026-10-19T00:00:00Z",citation_url:"/play?world=elderwyld&run=run-a&evidence_revision=54",sources:[{kind:"closing_reflections",text:"Players want combat next time.",sha256:"b".repeat(64),citation_url:"/play?world=elderwyld&run=run-a&evidence_revision=54"}]} as SessionEvidence;
beforeEach(()=>{localStorage.clear();vi.resetAllMocks();vi.mocked(listSessionEvidence).mockResolvedValue([item]);vi.mocked(readSessionEvidence).mockResolvedValue(item)});
it("requires explicit attachment and emits exact pinned references",async()=>{
 const change=vi.fn();render(<SessionEvidencePicker worldId="elderwyld" targetKey="c2:30" onChange={change}/>);
 fireEvent.click(screen.getByText(/Supplemental session evidence/));const box=await screen.findByRole("checkbox");expect(box).not.toBeChecked();
 fireEvent.click(box);expect(change).toHaveBeenLastCalledWith([{run_id:"run-a",review_revision:54,sha256:"a".repeat(64)}]);
 expect(screen.getByRole("link",{name:"Read saved evidence"})).toHaveAttribute("href",item.citation_url);
});
it("keeps stored attachment refs when reads fail, instead of silently dropping them",async()=>{
 const refs=[{run_id:"run-a",review_revision:54,sha256:"a".repeat(64)}];localStorage.setItem("dmb.ingestion.session-evidence.elderwyld.c2:30",JSON.stringify(refs));
 vi.mocked(listSessionEvidence).mockRejectedValue(new Error("offline"));const change=vi.fn();
 render(<SessionEvidencePicker worldId="elderwyld" targetKey="c2:30" onChange={change}/>);
 fireEvent.click(screen.getByText(/Supplemental session evidence/));expect(await screen.findByRole("alert")).toHaveTextContent("offline");expect(change).toHaveBeenLastCalledWith(refs);
 fireEvent.click(screen.getByRole("button",{name:"Clear selected session evidence"}));expect(change).toHaveBeenLastCalledWith([]);
});
it("renders pinned sources read-only without a reflections editor",async()=>{
 render(<SessionEvidenceViewer worldId="elderwyld" runId="run-a" revision={54}/>);
 expect(await screen.findByText("Players want combat next time.")).toBeInTheDocument();expect(readSessionEvidence).toHaveBeenCalledWith("elderwyld","run-a",54);
 expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
});
