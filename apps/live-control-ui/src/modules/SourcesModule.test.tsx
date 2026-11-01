import {render,screen} from "@testing-library/react";
import {afterEach,expect,it,vi} from "vitest";
import * as selection from "../selectedWorld/SelectedWorldContext";
import * as api from "../api/recapIngestApi";
import {SourcesModule} from "./SourcesModule";
afterEach(()=>vi.restoreAllMocks());
it("links the selected World to ordinary Ingest without guessing a source session or checking files",()=>{
 vi.spyOn(selection,"useSelectedWorld").mockReturnValue({kind:"managed",worldId:"elderwyld",name:"Elderwyld",documentId:null});
 const post=vi.spyOn(api,"postRecapIngest");render(<SourcesModule campaignId="longmont-c2" session={30}/>);
 const url=new URL(screen.getByRole("link",{name:"Open Ingest"}).getAttribute("href")!,window.location.origin);
 expect(url.searchParams.get("world")).toBe("elderwyld");expect(url.searchParams.get("campaign")).toBe("longmont-c2");expect(url.searchParams.has("session")).toBe(false);expect(post).not.toHaveBeenCalled();
});
it("does not guess a World from a campaign",()=>{
 render(<SourcesModule campaignId="elderwyld" session={30}/>);
 expect(screen.queryByRole("link")).not.toBeInTheDocument();expect(screen.getByText(/Select a World/)).toBeInTheDocument();
});
