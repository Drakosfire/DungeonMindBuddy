import {act,fireEvent,render,screen,waitFor} from "@testing-library/react";
import {afterEach,beforeEach,expect,it,vi} from "vitest";
import * as liveApi from "../api/liveApi";
import * as savedApi from "../api/savedRecapRunsApi";
import * as candidateApi from "../api/exactRunCandidateProjectionApi";
import * as rawApi from "../api/recapIngestApi";
import type {ExactRunCandidateProjection} from "../api/exactRunCandidateProjectionApi";
import type {HistoricalRecapWorldProjectionResponse,RecapIngestStatus} from "../api/types";
import {session23WorldGraphRecapFixture} from "../planSurface/graphPreview/worldGraphRecapFixture";
import {IngestionModule} from "./IngestionModule";
const selected=vi.hoisted(()=>({value:{kind:"managed",worldId:"elderwyld",name:"Elderwyld",documentId:null} as any}));
vi.mock("../selectedWorld/SelectedWorldContext",()=>({useSelectedWorld:()=>selected.value}));
vi.mock("../chrome/NativeGraphAccessControl",()=>({NativeGraphAccessControl:()=>null}));
vi.mock("../playSurface/review/SessionEvidencePicker",()=>({SessionEvidencePicker:({onChange}:{onChange:(refs:unknown[])=>void})=><button onClick={()=>onChange([{run_id:"aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",review_revision:54,sha256:"a".repeat(64)}])}>Attach saved session evidence</button>}));
function deferred<T>(){let resolve!:(v:T)=>void;let reject!:(e:Error)=>void;const promise=new Promise<T>((a,b)=>{resolve=a;reject=b;});return {promise,resolve,reject};}
function result(session=22,overrides:Partial<RecapIngestStatus>={}):RecapIngestStatus{return {schema:"dmb_raw_recap_ingest_status_v1",campaign_id:"longmont-c2",session,status:"candidate_validation_ready",states:["immutable_app_source_prepared","graph_candidate_ready"],paths:{},authority:{source:"immutable_app_recap_v1"},warnings:[],errors:[],next_actions:[],ingest_report:{graph_preview:{status:"candidate_validation_ready",extraction_run_id:`run-session-${session}`,source_artifact_id:`artifact:recap:longmont-c2:session-${session}`}},entity_spelling_audit:[],...overrides};}
function mount(world:string|undefined="elderwyld"){window.history.replaceState({},"","/ingest?world=elderwyld&campaign=longmont-c2&session=session-22");return render(<IngestionModule campaignId="longmont-c2" session={23} managedWorldId={world}/>);}
async function input(text="A keeper scouts Mireward."){const field=await screen.findByRole("textbox",{name:/Write or paste a recap/});fireEvent.change(field,{target:{value:text}});return field;}
async function process(){fireEvent.click(screen.getByRole("button",{name:"Process recap"}));}
beforeEach(()=>{
 window.localStorage.clear();selected.value={kind:"managed",worldId:"elderwyld",name:"Elderwyld",documentId:null};
 vi.spyOn(savedApi,"getSavedRecapRuns").mockImplementation(async managedWorldId=>({schema:"dmb_saved_recap_runs_v1",managedWorldId,nativeWorldId:"world:elderwyld",bindingVersion:3,runs:[]}));
 vi.spyOn(savedApi,"getSavedRecapSource").mockRejectedValue(new Error("No exact source offered"));
 vi.spyOn(liveApi,"getRecapArtifacts").mockRejectedValue(new Error("File discovery forbidden"));
 vi.spyOn(candidateApi,"getExactRunCandidateProjection").mockImplementation(async id=>candidateRecapProjectionForRun(id));
 vi.spyOn(rawApi,"postRecapIngest").mockImplementation(async body=>{offerSavedRun(`run-session-${body.session}`,body.session);return result(body.session);});
});
afterEach(()=>vi.restoreAllMocks());
function historicalRecapProjectionForRun(runId: string): HistoricalRecapWorldProjectionResponse {
  const sessionNumber = Number(runId.match(/session-(\d+)/i)?.[1] ?? 22);
  const sessionId = `session-${sessionNumber}`;
  const sourceArtifactId = `artifact:recap:longmont-c2:${sessionId}`;
  const graphId = `fixture-world-head-${sessionNumber}`;
  const nodeId = "loc_mireward";
  return {
    ...session23WorldGraphRecapFixture,
    schema: "dmb_historical_recap_world_projection_v1",
    runId,
    runStatus: "candidate_validation_ready",
    sourceDomain: "recap",
    sourceArtifactId,
    sourceRevisionId: `source-revision-${sessionNumber}`,
    campaignId: "longmont-c2",
    sessionId,
    worldId: "world:elderwyld",
    managedWorldId: "elderwyld",
    bindingVersion: 3,
    sourceSha256: `sha256:${"a".repeat(64)}`,
    sourceStatus: "available",
    graphStatus: "available",
    graphId,
    markdown: `# Session ${sessionNumber} — Mireward Road\n\nThe party presses on near [Mireward](dmb-node:${nodeId}).`,
    focus: {
      focusSessionId: sessionId,
      focusedEvidenceRefIds: [],
      focusedEdgeIds: [],
      focusedNodeIds: [nodeId],
    },
    nodeViews: {
      [nodeId]: {
        nodeId,
        label: "Mireward",
        kind: "location",
        role: "place",
        aliases: ["Mireward"],
        sourceDomains: ["recap"],
        summary: "A road in the synthetic exact-run fixture.",
        anchoredToFocusSession: true,
        campaignScope: "longmont-c2",
        evidenceBadges: [],
        adjacency: [],
        suggestedExpansions: [],
        evidenceRefIds: [],
        sourceArtifactIds: [sourceArtifactId],
      },
    },
    mentions: [{
      mentionId: `mention:${sessionId}:mireward`,
      nodeId,
      label: "Mireward",
      startOffset: null,
      endOffset: null,
      evidenceRefIds: [],
    }],
    snapshot: {
      ...session23WorldGraphRecapFixture.snapshot,
      revisionId: graphId,
      headRevisionId: graphId,
      worldId: "world:elderwyld",
      focus: { kind: "session", campaignId: "longmont-c2", sessionId },
    },
  };
}

function candidateRecapProjectionForRun(runId: string): ExactRunCandidateProjection {
  const prior=historicalRecapProjectionForRun(runId);
  const key=`candidate:${runId}:${"c".repeat(64)}:${"d".repeat(64)}`;
  const source=prior.markdown.replace("[Mireward](dmb-node:loc_mireward)","Mireward");
  return {schema:"dmb_exact_run_candidate_projection_v1",trustBoundary:"unpublished_candidate",runId,runRevision:5,runStatus:"reviewable",profileId:"recap_category_v1@1.0",sourceDomain:"recap",
    sourceArtifactId:prior.sourceArtifactId,sourceRevisionId:prior.sourceSha256,sourceSha256:prior.sourceSha256,candidateSha256:"sha256:"+"c".repeat(64),spanIndexSha256:"sha256:"+"e".repeat(64),
    campaignId:prior.campaignId,sessionId:prior.sessionId,managedWorldId:"elderwyld",nativeWorldId:"world:elderwyld",bindingVersion:3,runWorldBindingStatus:"source_only",
    sourceMarkdown:source,narrativeMarkdown:source,projectedMarkdown:source.replace("Mireward.",`[Mireward](dmb-node:${key}).`),sourceDisplaySegments:[],
    nodes:[{viewKey:key,candidateNodeId:"loc_mireward",label:"Mireward",nodeType:"location",description:"Candidate-only place",confidence:"medium",semanticState:{},warnings:[],evidence:[]}],edges:[],
    nodeViews:{[key]:{node_id:key,label:"Mireward",kind:"candidate",role:"unpublished_candidate",aliases:[],source_domains:["recap"],evidence_badges:[],adjacency:[],anchored_to_focus_session:false}},
    sourceSpans:[],mentionsCount:1,unlinkedNodeCount:0,beatCount:0,diagnostics:[]};
}

function offerSavedRun(runId: string, sessionNumber: number) {
  vi.mocked(savedApi.getSavedRecapRuns).mockResolvedValue({
    schema: "dmb_saved_recap_runs_v1", managedWorldId: "elderwyld", nativeWorldId: "world:elderwyld", bindingVersion: 3,
    runs: [{runId, runRevision: 5, runStatus: "reviewable", sourceArtifactId: `artifact:recap:longmont-c2:session-${sessionNumber}`,
      campaignId: "longmont-c2", sessionId: `session-${sessionNumber}`, profileId: "recap_category_v2@2.0", createdAt: null, updatedAt: null,
      sourceRevisionId: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa", sourceSha256: "a".repeat(64), unavailableReason: null}],
  });
}


it("restores only local draft state, without title guesses or file inspections",async()=>{
 mount();await screen.findByRole("textbox",{name:/Write or paste a recap/});
 expect(rawApi.postRecapIngest).not.toHaveBeenCalled();expect(liveApi.getRecapArtifacts).not.toHaveBeenCalled();
 expect(screen.queryByLabelText("Session title")).not.toBeInTheDocument();expect(screen.queryByText(/Advanced file/)).not.toBeInTheDocument();
});
it("does not require a filename title and sends the submitted text unchanged",async()=>{
 mount();await input("# Session 22 Recap\n\nMireward.");await process();
 await waitFor(()=>expect(rawApi.postRecapIngest).toHaveBeenCalledOnce());
 expect(rawApi.postRecapIngest).toHaveBeenCalledWith({operation:"generate_recap_memory",campaign_id:"longmont-c2",managed_world_id:"elderwyld",session:22,raw_text:"# Session 22 Recap\n\nMireward.",include_graph_extraction:true,graph_model_id:"deepseek/deepseek-v4.1-flash-1017",force_graph_run:undefined});
});
it.each([undefined,"conflicting"])("refuses Process without a matching selected World: %s",async world=>{
 selected.value=world?{kind:"managed",worldId:"other",name:"Other",documentId:null}:{kind:"legacy"};
 mount(world===undefined?"":world);await input();expect(screen.getByRole("button",{name:"Process recap"})).toBeDisabled();expect(rawApi.postRecapIngest).not.toHaveBeenCalled();
});
it("uses the existing selected World when the embedded module has no World prop",async()=>{
 window.history.replaceState({},"","/surface");render(<IngestionModule campaignId="longmont-c2" session={23}/>);await input();await process();
 await waitFor(()=>expect(rawApi.postRecapIngest).toHaveBeenCalledWith(expect.objectContaining({managed_world_id:"elderwyld"})));
});
it("does not send blank recap text or an invalid source session",async()=>{
 mount();await input("   ");expect(screen.queryByRole("button",{name:"Process recap"})).not.toBeInTheDocument();
 await input();fireEvent.change(screen.getByLabelText("Recap/source session"),{target:{value:"0"}});expect(rawApi.postRecapIngest).not.toHaveBeenCalled();expect(screen.queryByRole("button",{name:"Process recap"})).not.toBeInTheDocument();
});
it("opens the exact Process candidate and carries the same run into Graph Review",async()=>{
 mount();await input();await process();await waitFor(()=>expect(candidateApi.getExactRunCandidateProjection).toHaveBeenCalledWith("run-session-22","elderwyld"));
 expect(new URLSearchParams(window.location.search).get("recapReviewRunId")).toBe("run-session-22");
 await waitFor(()=>expect(screen.getByRole("button",{name:"Open Graph Review"})).toBeEnabled());fireEvent.click(screen.getByRole("button",{name:"Open Graph Review"}));
 expect(new URLSearchParams(window.location.search).get("extractionRunId")).toBe("run-session-22");expect(new URLSearchParams(window.location.search).get("world")).toBe("elderwyld");
});
it("preserves the submitted draft after Process navigation and Return to draft",async()=>{
 mount();await input("Recover this original recap.");await process();await screen.findByRole("button",{name:"Return to draft"});fireEvent.click(screen.getByRole("button",{name:"Return to draft"}));
 expect(await screen.findByRole("textbox",{name:/Write or paste a recap/})).toHaveValue("Recover this original recap.");
 expect(rawApi.postRecapIngest).toHaveBeenCalledOnce();
});
it("preserves a draft on a transport failure and retries only deliberately",async()=>{
 vi.mocked(rawApi.postRecapIngest).mockRejectedValue(new Error("Source database unavailable"));
 mount();await input("Do not lose my draft.");await process();await screen.findByText("Processing failed");
 expect(screen.getByRole("textbox",{name:/Write or paste a recap/})).toHaveValue("Do not lose my draft.");expect(rawApi.postRecapIngest).toHaveBeenCalledOnce();
 await process();await waitFor(()=>expect(rawApi.postRecapIngest).toHaveBeenCalledTimes(2));
});
it("keeps a failed extraction and the source editable without a success claim",async()=>{
 vi.mocked(rawApi.postRecapIngest).mockResolvedValue(result(22,{status:"error",errors:["Extraction interrupted"],states:["immutable_app_source_prepared","graph_preview_failed"]}));
 mount();await input("Retain failed source.");await process();await screen.findByText("Processing failed");expect(screen.getByRole("textbox",{name:/Write or paste a recap/})).toHaveValue("Retain failed source.");expect(screen.queryByText("Recap processed")).not.toBeInTheDocument();
});
it.each([{campaign_id:"other"},{session:29}])("rejects a response for a different target: %j",async change=>{
 vi.mocked(rawApi.postRecapIngest).mockResolvedValue(result(22,change));mount();await input();await process();await screen.findByText("Response did not match this recap");
 expect(screen.getByRole("textbox",{name:/Write or paste a recap/})).toHaveValue("A keeper scouts Mireward.");expect(new URLSearchParams(window.location.search).has("recapReviewRunId")).toBe(false);
});
it("does not navigate to an inferred run when Process returns no exact run",async()=>{
 vi.mocked(rawApi.postRecapIngest).mockResolvedValue(result(22,{ingest_report:{}}));mount();await input();await process();await screen.findByText("Processing failed");expect(screen.getByRole("textbox",{name:/Write or paste a recap/})).toHaveValue("A keeper scouts Mireward.");expect(new URLSearchParams(window.location.search).has("recapReviewRunId")).toBe(false);
});
it("supports deliberate fresh extraction without replacing previous Graph facts",async()=>{
 mount();await input();fireEvent.click(screen.getByRole("checkbox",{name:"Run fresh extraction"}));await process();await waitFor(()=>expect(rawApi.postRecapIngest).toHaveBeenCalledWith(expect.objectContaining({force_graph_run:true})));
});
it("sends attached session evidence separately from unchanged external source text",async()=>{
 mount();await input("External author text.");fireEvent.click(screen.getByRole("button",{name:"Attach saved session evidence"}));await process();await waitFor(()=>expect(rawApi.postRecapIngest).toHaveBeenCalledWith(expect.objectContaining({raw_text:"External author text.",session_evidence:[{run_id:"aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",review_revision:54,sha256:"a".repeat(64)}]})));
});
it("ignores a late Process result after changing the source session and preserves the original draft",async()=>{
 const gate=deferred<RecapIngestStatus>();vi.mocked(rawApi.postRecapIngest).mockReturnValue(gate.promise);mount();await input("Original session draft.");await process();fireEvent.change(screen.getByLabelText("Recap/source session"),{target:{value:"29"}});
 await act(async()=>{gate.resolve(result());await gate.promise;});expect(new URLSearchParams(window.location.search).has("recapReviewRunId")).toBe(false);
 fireEvent.click(screen.getByRole("button",{name:"Return to draft"}));expect(await screen.findByRole("textbox",{name:/Write or paste a recap/})).toHaveValue("Original session draft.");
});
it("does not attach an old same-session completion to a new draft",async()=>{
 const gate=deferred<RecapIngestStatus>();vi.mocked(rawApi.postRecapIngest).mockReturnValue(gate.promise);mount();await input("Old source.");await process();fireEvent.click(screen.getByRole("button",{name:"New recap"}));await input("New source.");
 await act(async()=>{gate.resolve(result());await gate.promise;});expect(screen.getByRole("textbox",{name:/Write or paste a recap/})).toHaveValue("New source.");expect(new URLSearchParams(window.location.search).has("recapReviewRunId")).toBe(false);
});

it("drops a late Process result across World A to B to A without deleting the draft",async()=>{
 const gate=deferred<RecapIngestStatus>();vi.mocked(rawApi.postRecapIngest).mockReturnValue(gate.promise);
 const view=mount();await input("A retained World draft.");await process();
 selected.value={kind:"managed",worldId:"other",name:"Other",documentId:null};
 window.history.replaceState({},"","/ingest?world=other&campaign=longmont-c2&session=session-22");
 view.rerender(<IngestionModule campaignId="longmont-c2" session={23} managedWorldId="other"/>);
 selected.value={kind:"managed",worldId:"elderwyld",name:"Elderwyld",documentId:null};
 window.history.replaceState({},"","/ingest?world=elderwyld&campaign=longmont-c2&session=session-22");
 view.rerender(<IngestionModule campaignId="longmont-c2" session={23} managedWorldId="elderwyld"/>);
 await act(async()=>{gate.resolve(result());await gate.promise;});
 expect(new URLSearchParams(window.location.search).has("recapReviewRunId")).toBe(false);
 const back=screen.queryByRole("button",{name:"Return to draft"});if(back)fireEvent.click(back);
 expect(await screen.findByRole("textbox",{name:/Write or paste a recap/})).toHaveValue("A retained World draft.");
 expect(rawApi.postRecapIngest).toHaveBeenCalledOnce();
});
