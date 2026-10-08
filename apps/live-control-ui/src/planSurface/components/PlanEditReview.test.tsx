import { fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { PlanEditReview, type PlanEditReviewProps } from "./PlanEditReview";
const props:PlanEditReviewProps = {
  targetLabel:"Session title", status:"review", onApply:vi.fn(), onDiscard:vi.fn(),
  before:{markdown:"# Campaign 2\n\nThe hours they bought.\n\n## Opening\n\nThe siege has broken."},
  after:{markdown:"# Campaign 2\n\n## Breaking the Siege\n\nThe hours they bought.\n\n## Opening\n\nThe siege has broken.",placementLabel:"Inserted below Campaign 2",sourceLineTarget:{startLine:3,endLine:3,targetKey:"title-insertion"}},
};
describe("PlanEditReview",()=>{
  it("renders surrounding document headings and the exact highlighted insertion without dispatching a mutation",()=>{
    HTMLElement.prototype.scrollIntoView=vi.fn();
    render(<PlanEditReview {...props}/>);
    const before=screen.getByRole("region",{name:"Before Session title"}),after=screen.getByRole("region",{name:"After Session title"});
    expect(within(before).getByRole("heading",{name:"Campaign 2"})).toBeVisible();
    expect(within(after).getByRole("heading",{name:"Breaking the Siege"})).toHaveAttribute("data-source-block","true");
    expect(within(after).getByRole("heading",{name:"Opening"})).toBeVisible();
    expect(props.onApply).not.toHaveBeenCalled();expect(props.onDiscard).not.toHaveBeenCalled();
  });
  it("expands the same comparison, restores inline focus, and calls only explicit guarded actions",async()=>{
    const user=userEvent.setup(),apply=vi.fn(),discard=vi.fn();render(<PlanEditReview {...props} onApply={apply} onDiscard={discard}/>);
    const before=screen.getByRole("region",{name:"Before Session title"});
    await user.click(screen.getByRole("button",{name:"Expand review"}));expect(screen.getByRole("dialog")).toContainElement(before);
    await user.keyboard("{Escape}");expect(screen.queryByRole("dialog")).toBeNull();expect(screen.getByRole("button",{name:"Expand review"})).toHaveFocus();
    await user.click(screen.getByRole("button",{name:"Apply to draft"}));expect(apply).toHaveBeenCalledTimes(1);expect(discard).not.toHaveBeenCalled();
  });
  it("blocks stale Apply and distinguishes applied draft from an explicit existing Save action",()=>{
    const save=vi.fn(),view=render(<PlanEditReview {...props} status="stale"/>);
    expect(screen.queryByRole("button",{name:"Apply to draft"})).toBeNull();
    expect(screen.queryByRole("button",{name:"Discard proposal"})).toBeNull();
    view.rerender(<PlanEditReview {...props} status="applied" saveAction={{onSave:save}}/>);
    expect(screen.getByText("Applied to your draft. Save Plan keeps this change.")).toBeVisible();expect(save).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button",{name:"Save Plan"}));expect(save).toHaveBeenCalledTimes(1);
    view.rerender(<PlanEditReview {...props} status="saved"/>);expect(screen.getByText("Saved to your Plan.")).toBeVisible();expect(screen.queryByRole("button",{name:"Save Plan"})).toBeNull();
  });
});
