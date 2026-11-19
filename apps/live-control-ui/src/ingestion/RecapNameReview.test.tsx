import {render,screen,fireEvent} from "@testing-library/react";
import {expect,it,vi} from "vitest";
import {RecapNameReview} from "./RecapNameReview";
import type {RecapNameReview as Review} from "../api/recapIngestApi";
const review:Review={schema:"dmb_recap_name_review_v1",scope:{managed_world_id:"m",native_world_id:"n",binding_version:1,campaign_id:"c"},source_sha256:"a".repeat(64),catalog_sha256:"b".repeat(64),review_id:"c".repeat(64),exact_mention_count:3,suggestions:[{id:"d".repeat(64),start:0,end:7,surface:"Marlena",options:["Marlene"],context_before:"They saw ",context_after:" waiting.",source_line:3}]};
it("requires a correction or explicit keep before invoking extraction",()=>{
 const proceed=vi.fn();render(<RecapNameReview review={review} onProceed={proceed} onCancel={()=>{}}/>);
 const button=screen.getByRole("button",{name:"Apply decisions and extract"});expect(button).toBeDisabled();
 fireEvent.change(screen.getByRole("combobox"),{target:{value:"apply:Marlene"}});fireEvent.click(button);
 expect(proceed).toHaveBeenCalledWith({review_id:review.review_id,decisions:[{id:review.suggestions[0].id,replacement:"Marlene"}]});
});
it("cancel returns to editing without extraction",()=>{
 const proceed=vi.fn(),cancel=vi.fn();render(<RecapNameReview review={review} onProceed={proceed} onCancel={cancel}/>);
 fireEvent.click(screen.getByRole("button",{name:"Back to editing"}));expect(cancel).toHaveBeenCalledOnce();expect(proceed).not.toHaveBeenCalled();
});

it("shows source context and lets the reader retain possessive meaning",()=>{
 const proceed=vi.fn();const r={...review,suggestions:[{...review.suggestions[0],surface:"Marlens",options:["Marlen","Marlen's"],context_before:"He read ",context_after:" intentions.",source_line:4}]};
 render(<RecapNameReview review={r} onProceed={proceed} onCancel={()=>{}}/>);
 expect(screen.getByRole("blockquote")).toHaveTextContent("He read Marlens intentions.");
 expect(screen.getByText("Source line 4")).toBeInTheDocument();
 fireEvent.change(screen.getByRole("combobox"),{target:{value:"apply:Marlen's"}});
 fireEvent.click(screen.getByRole("button",{name:"Apply decisions and extract"}));
 expect(proceed).toHaveBeenCalledWith({review_id:r.review_id,decisions:[{id:r.suggestions[0].id,replacement:"Marlen's"}]});
});
