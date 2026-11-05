import {beforeEach,expect,it,vi} from "vitest";
import {authenticatedApiFetch} from "./liveApi";
import {getIngestUsage} from "./ingestUsageApi";
vi.mock("./liveApi",()=>({authenticatedApiFetch:vi.fn(),LiveApiError:class extends Error {constructor(message:string,public status:number){super(message)}}}));
const metrics={inputTokens:10,outputTokens:2,cachedInputTokens:0,reasoningTokens:1,totalTokens:12,knownInputTokens:10,knownOutputTokens:2,providerAttempts:1,costUsd:0,knownCostUsd:0,costStatus:"reported",pricingSource:"provider_reported:test"};
const data=()=>({schema:"dmb_extraction_usage_v1",managedWorldId:"w",runId:"r",runRevision:5,currency:"USD",totals:{...metrics},passes:[{...metrics,passName:"actor_pass"}]});
beforeEach(()=>vi.resetAllMocks());
function respond(v:unknown){vi.mocked(authenticatedApiFetch).mockResolvedValue({response:{ok:true,json:async()=>v} as Response} as Awaited<ReturnType<typeof authenticatedApiFetch>>)}
it("requests exact revision without caching and accepts reported zero",async()=>{
 respond(data());const signal=new AbortController().signal;
 expect((await getIngestUsage("w","r",5,signal)).totals.costUsd).toBe(0);
 expect(authenticatedApiFetch).toHaveBeenCalledWith(expect.stringContaining("expected_run_revision=5"),{cache:"no-store",signal});
});
it.each([{managedWorldId:"foreign"},{runId:"other"},{runRevision:6},{currency:"EUR"}])("rejects wrong scope/revision/currency %o",async change=>{
 respond({...data(),...change});await expect(getIngestUsage("w","r",5,new AbortController().signal)).rejects.toThrow(/does not match/);
});
it.each([NaN,Infinity,-1,"0.1",true])("rejects invalid price %s",async costUsd=>{
 const v=data();respond({...v,totals:{...v.totals,costUsd}});await expect(getIngestUsage("w","r",5,new AbortController().signal)).rejects.toThrow();
});
