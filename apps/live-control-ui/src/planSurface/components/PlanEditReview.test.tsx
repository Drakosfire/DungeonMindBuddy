import { fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { PlanEditReview, type PlanEditReviewProps } from "./PlanEditReview";
const props:PlanEditReviewProps = {
  targetLabel:"Session title", status:"review", onApply:vi.fn(), onDiscard:vi.fn(),
  before:{markdown:"# Campaign 2\n\nThe hours they bought.\n\n## Opening\n\nThe siege has broken."},
  after:{markdown:"# Campaign 2\n\n<!-- dmb-playable-element:v1 kind=scene id=scene:siege -->\n## Breaking the Siege\n\nThe hours they bought.\n\n## Opening\n\nThe siege has broken.",placementLabel:"Inserted below Campaign 2",sourceLineTarget:{startLine:4,endLine:4,targetKey:"title-insertion"}},
};
describe("PlanEditReview",()=>{
  it("renders surrounding document headings and the exact highlighted insertion without dispatching a mutation",()=>{
    HTMLElement.prototype.scrollIntoView=vi.fn();
    render(<PlanEditReview {...props}/>);
    const before=screen.getByRole("region",{name:"Before Session title"}),after=screen.getByRole("region",{name:"After Session title"});
    expect(within(before).getByRole("heading",{name:"Campaign 2"})).toBeVisible();
    expect(within(after).getByRole("heading",{name:"Breaking the Siege"})).toHaveAttribute("data-source-block","true");
    expect(within(after).queryByText("<!-- dmb-playable-element:v1 kind=scene id=scene:siege -->")).not.toBeInTheDocument();
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


it("highlights the actual appended cue rather than the captured scene start and refocuses on expand/restore", async () => {
  const user = userEvent.setup();
  const scrolled: HTMLElement[] = [];
  const original = HTMLElement.prototype.scrollIntoView;
  HTMLElement.prototype.scrollIntoView = function() { scrolled.push(this); };
  const before = "---\ntitle: Saved\n---\n\n# Plan\n\n<!-- dmb-playable-element:v1 kind=scene id=scene:opening -->\n## Opening\n\n**Situation**\n\nExisting prose.\n\n## Following scene\n\nKeep this too.\n";
  const cue = "Optional pacing cue: Pause and let the group choose.";
  const after = before.replace("\n## Following scene", `\n${cue}\n\n## Following scene`);
  const beforePreview = Object.freeze({markdown:before, sourceLineTarget:{startLine:10,endLine:10,targetKey:"scene:before"}});
  const afterPreview = Object.freeze({markdown:after, sourceLineTarget:{startLine:10,endLine:10,targetKey:"scene:after"}});
  try {
    render(<PlanEditReview {...props} targetLabel="Opening" before={beforePreview} after={afterPreview}/>);
    const old = screen.getByRole("region", {name:"Before Opening"});
    const next = screen.getByRole("region", {name:"After Opening"});
    const added = within(next).getByText(cue).closest("p")!;
    expect(added).toHaveAttribute("data-source-block", "true");
    expect(within(old).queryByText(cue)).toBeNull();
    expect(within(old).getByText("Insertion point · no text removed")).toBeVisible();
    expect(within(next).getByText("Situation").closest("p")).not.toHaveAttribute("data-source-block");
    expect(scrolled).toContain(added);
    scrolled.length = 0;
    await user.click(screen.getByRole("button", {name:"Expand review"}));
    expect(scrolled).toContain(added);
    expect(screen.getByRole("dialog")).toContainElement(screen.getByRole("button", {name:"Apply to draft"}));
    scrolled.length = 0;
    await user.keyboard("{Escape}");
    expect(scrolled).toContain(added);
    expect(beforePreview.markdown).toBe(before); expect(afterPreview.markdown).toBe(after);
  } finally { HTMLElement.prototype.scrollIntoView = original; }
});

it.each([
  {name:"deletion", before:"# Plan\n\nRemove this.\n\nKeep this.", after:"# Plan\n\nKeep this.", old:"Remove this.", next:null},
  {name:"replacement", before:"# Plan\n\nOld prose.\n\nKeep this.", after:"# Plan\n\nNew prose.\n\nKeep this.", old:"Old prose.", next:"New prose."},
])("highlights actual $name without marking shared text as changed", ({before,after,old,next}) => {
  render(<PlanEditReview {...props} before={{markdown:before}} after={{markdown:after}}/>);
  const left = screen.getByRole("region", {name:"Before Session title"});
  const right = screen.getByRole("region", {name:"After Session title"});
  expect(within(left).getByText(old).closest("p")).toHaveAttribute("data-source-block", "true");
  expect(within(left).getByText("Keep this.").closest("p")).not.toHaveAttribute("data-source-block");
  if (next) expect(within(right).getByText(next).closest("p")).toHaveAttribute("data-source-block", "true");
  else expect(within(right).getByText("Deletion point · no text added")).toBeVisible();
});

it("shows identical frozen previews as unchanged without inventing a highlight", () => {
  const markdown = "# Plan\n\nSame prose.";
  const {container} = render(<PlanEditReview {...props} before={{markdown}} after={{markdown}}/>);
  expect(screen.getAllByText("Unchanged")).toHaveLength(2);
  expect(container.querySelector('[data-source-block="true"]')).toBeNull();
  expect(props.onApply).not.toHaveBeenCalled();
});


it.each(["append", "delete"])("uses preceding visible context for EOF %s with trailing newline and original YAML/marker offsets", operation => {
  const base = "---\ntitle: Saved\n---\n\n# Plan\n\n<!-- dmb-playable-element:v1 kind=scene id=scene:opening -->\nExisting.\n";
  const extended = base + "New cue.\n";
  const before = operation === "append" ? base : extended;
  const after = operation === "append" ? extended : base;
  render(<PlanEditReview {...props} before={{markdown:before}} after={{markdown:after}}/>);
  const unchangedSide = screen.getByRole("region", {name: `${operation === "append" ? "Before" : "After"} Session title`});
  const changedSide = screen.getByRole("region", {name: `${operation === "append" ? "After" : "Before"} Session title`});
  expect(within(unchangedSide).getByText("Existing.").closest("p")).toHaveAttribute("data-source-block", "true");
  expect(within(changedSide).getByText(/New cue\./).closest("p")).toHaveAttribute("data-source-block", "true");
  expect(within(unchangedSide).queryByTestId("markdown-reader-source-no-highlight")).toBeNull();
  expect(within(unchangedSide).queryByTestId("markdown-reader-html-literal")).toBeNull();
});

it("does not invent context when the unchanged side has no visible text", () => {
  render(<PlanEditReview {...props} before={{markdown:"---\ntitle: Saved\n---\n\n"}} after={{markdown:"---\ntitle: Saved\n---\n\nNew cue.\n"}}/>);
  const before = screen.getByRole("region", {name:"Before Session title"});
  expect(before.querySelector('[data-source-block="true"]')).toBeNull();
  expect(within(before).queryByTestId("markdown-reader-source-no-highlight")).toBeNull();
});


it("skips trailing blanks and canonical marker lines when finding preceding EOF context", () => {
  const base = "---\ntitle: Saved\n---\n\n# Plan\n\nExisting.\n\n<!-- dmb-playable-element:v1 kind=scene id=scene:next -->\n\n";
  render(<PlanEditReview {...props} before={{markdown:base}} after={{markdown:base + "New cue.\n"}}/>);
  const before = screen.getByRole("region", {name:"Before Session title"});
  expect(within(before).getByText("Existing.").closest("p")).toHaveAttribute("data-source-block", "true");
  expect(within(before).queryByTestId("markdown-reader-source-no-highlight")).toBeNull();
});
