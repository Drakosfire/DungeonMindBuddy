import {render,screen} from "@testing-library/react";
import {expect,it} from "vitest";
import {useCampaignTrashScope,usePublishCampaignTrashScope} from "./campaignTrashScope";
function Owner(){usePublishCampaignTrashScope("longmont-c2");return null;}
function Reader(){return <span data-testid="scope">{useCampaignTrashScope()??"none"}</span>;}
it("publishes campaign Trash scope and clears on departure",()=>{
 const {rerender}=render(<><Owner/><Reader/></>);expect(screen.getByTestId("scope")).toHaveTextContent("longmont-c2");
 rerender(<Reader/>);expect(screen.getByTestId("scope")).toHaveTextContent("none");
});
