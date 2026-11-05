import {act,render,screen,waitFor} from "@testing-library/react";
import {beforeEach,expect,it,vi} from "vitest";
import {getIngestUsage,type ExtractionUsage,type UsageMetrics} from "../api/ingestUsageApi";
import {IngestionUsage} from "./IngestionUsage";
vi.mock("../api/ingestUsageApi",()=>({getIngestUsage:vi.fn()}));
const metrics:UsageMetrics={inputTokens:100,outputTokens:20,cachedInputTokens:50,reasoningTokens:15,totalTokens:120,knownInputTokens:100,knownOutputTokens:20,providerAttempts:1,costUsd:0,knownCostUsd:0,costStatus:"reported",pricingSource:"provider_reported:test"};
const result=(runId="r",totals=metrics):ExtractionUsage=>({schema:"dmb_extraction_usage_v1",managedWorldId:"w",runId,runRevision:5,currency:"USD",totals,passes:[{passName:"actor_pass",...totals}]});
beforeEach(()=>vi.resetAllMocks());
it("shows reported zero and clearly labels token subsets",async()=>{
 vi.mocked(getIngestUsage).mockResolvedValue(result());render(<IngestionUsage world="w" runId="r" revision={5}/>);
 expect(await screen.findAllByText(/\$0.000000 USD · provider reported/)).toHaveLength(2);
 expect(screen.getByText(/included in input and output, not added again/)).toBeInTheDocument();
 expect(getIngestUsage).toHaveBeenCalledWith("w","r",5,expect.any(AbortSignal));
});
it("does not show a partial known charge as the full price",async()=>{
 vi.mocked(getIngestUsage).mockResolvedValue(result("r",{...metrics,costUsd:null,knownCostUsd:0.012,costStatus:"partial"}));render(<IngestionUsage world="w" runId="r" revision={5}/>);
 expect(await screen.findByText(/not the full run price/)).toBeInTheDocument();
 expect(screen.queryByText(/provider reported/)).not.toBeInTheDocument();
});
it("leaves missing historical prices unavailable",async()=>{
 vi.mocked(getIngestUsage).mockResolvedValue(result("r",{...metrics,costUsd:null,knownCostUsd:null,costStatus:"unavailable"}));render(<IngestionUsage world="w" runId="r" revision={5}/>);
 expect(await screen.findByText(/No dollar price was retained/)).toBeInTheDocument();
});
it("hides old totals immediately and ignores a late response after selection changes",async()=>{
 let finish!:(v:ExtractionUsage)=>void;
 vi.mocked(getIngestUsage).mockImplementationOnce(()=>new Promise(r=>{finish=r})).mockResolvedValueOnce(result("new",{...metrics,costUsd:0.02,knownCostUsd:0.02}));
 const view=render(<IngestionUsage world="w" runId="old" revision={5}/>);
 view.rerender(<IngestionUsage world="w" runId="new" revision={5}/>);
 await screen.findAllByText(/\$0.020000/);
 await act(async()=>finish(result("old",{...metrics,costUsd:9,knownCostUsd:9})));
 await waitFor(()=>expect(screen.queryByText(/\$9.000000/)).not.toBeInTheDocument());
});
