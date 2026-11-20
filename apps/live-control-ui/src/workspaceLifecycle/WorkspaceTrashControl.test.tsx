import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";
import { WorkspaceTrashControl } from "./WorkspaceTrashControl";
import * as api from "./workspaceTrashApi";
vi.mock("./workspaceTrashApi", () => ({ listWorkspaceTrash: vi.fn(), changeWorkspaceTrash: vi.fn(), listCampaignPlanTrash:vi.fn(), changeCampaignPlanTrash:vi.fn() }));
const doc = { kind:"document" as const, id:"doc-a", title:"Disposable Plan", surface:"plan" as const, revision:7 };
const session = { kind:"session" as const, id:"run-a", title:"Lakeside session", surface:"play" as const, revision:5, content_revision:13 };
const item = { ...doc, status:"trashed" as const, updated_at:"2026-10-19T15:00:00Z" };
beforeAll(() => {
  HTMLDialogElement.prototype.showModal = function () { this.setAttribute("open", ""); };
  HTMLDialogElement.prototype.close = function () { this.removeAttribute("open"); };
});
beforeEach(() => { vi.mocked(api.listWorkspaceTrash).mockResolvedValue([item]); vi.mocked(api.changeWorkspaceTrash).mockResolvedValue(item); });
afterEach(() => vi.clearAllMocks());
describe("recoverable document lifecycle", () => {
  it.each([doc,session])("requires named confirmation and keeps owning revision for $kind", async current => {
    const onTrashed = vi.fn(); render(<WorkspaceTrashControl worldId="elderwyld" current={current} onTrashed={onTrashed} />);
    fireEvent.click(screen.getByRole("button",{name:"Delete",exact:true}));
    expect(screen.getByRole("dialog")).toHaveTextContent(current.title);
    expect(screen.getByRole("dialog")).toHaveTextContent(/restore it from Trash/i);
    expect(api.changeWorkspaceTrash).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button",{name:"Move to Trash",exact:true}));
    await waitFor(() => expect(onTrashed).toHaveBeenCalledOnce());
    expect(api.changeWorkspaceTrash).toHaveBeenCalledWith("elderwyld",current,"trash");
  });
  it("blocks deletion when an edit or pending writer appears after opening confirmation", () => {
    const onTrashed = vi.fn(); const props={worldId:"elderwyld",current:doc,onTrashed};
    const {rerender}=render(<WorkspaceTrashControl {...props} />);
    fireEvent.click(screen.getByRole("button",{name:"Delete",exact:true}));
    rerender(<WorkspaceTrashControl {...props} blocked />);
    expect(screen.getByRole("button",{name:"Move to Trash",exact:true})).toBeDisabled();
    fireEvent.click(screen.getByRole("button",{name:"Move to Trash",exact:true}));
    expect(api.changeWorkspaceTrash).not.toHaveBeenCalled();
  });
  it("cancels confirmation when the selected document changes", () => {
    const {rerender}=render(<WorkspaceTrashControl worldId="elderwyld" current={doc} onTrashed={vi.fn()} />);
    fireEvent.click(screen.getByRole("button",{name:"Delete",exact:true}));
    rerender(<WorkspaceTrashControl worldId="elderwyld" current={{...doc,id:"doc-b"}} onTrashed={vi.fn()} />);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(api.changeWorkspaceTrash).not.toHaveBeenCalled();
  });
  it.each([
    ["document revision", doc, { ...doc, revision: 8 }],
    ["session revision", session, { ...session, revision: 6 }],
    ["session content revision", session, { ...session, content_revision: 14 }],
  ] as const)("requires fresh confirmation after the same ID changes %s", async (_label, original, changed) => {
    const onTrashed = vi.fn();
    const { rerender } = render(<WorkspaceTrashControl worldId="elderwyld" current={original} onTrashed={onTrashed} />);
    fireEvent.click(screen.getByRole("button", { name:"Delete", exact:true }));
    expect(screen.getByRole("dialog")).toHaveTextContent(original.title);
    rerender(<WorkspaceTrashControl worldId="elderwyld" current={changed} onTrashed={onTrashed} />);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(api.changeWorkspaceTrash).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name:"Delete", exact:true }));
    fireEvent.click(screen.getByRole("button", { name:"Move to Trash", exact:true }));
    await waitFor(() => expect(onTrashed).toHaveBeenCalledOnce());
    expect(api.changeWorkspaceTrash).toHaveBeenCalledWith("elderwyld", changed, "trash");
  });
  it("ignores a delayed delete response after the same ID advances revision", async () => {
    let resolve!: (value: typeof item) => void;
    vi.mocked(api.changeWorkspaceTrash).mockReturnValueOnce(new Promise(done => { resolve = done; }));
    const onTrashed = vi.fn();
    const { rerender } = render(<WorkspaceTrashControl worldId="elderwyld" current={doc} onTrashed={onTrashed} />);
    fireEvent.click(screen.getByRole("button", { name:"Delete", exact:true }));
    fireEvent.click(screen.getByRole("button", { name:"Move to Trash", exact:true }));
    expect(api.changeWorkspaceTrash).toHaveBeenCalledWith("elderwyld", doc, "trash");
    rerender(<WorkspaceTrashControl worldId="elderwyld" current={{...doc, revision:8}} onTrashed={onTrashed} />);
    await act(async () => resolve(item));
    expect(onTrashed).not.toHaveBeenCalled();
  });
  it("does not navigate another target after a delayed delete response", async () => {
    let resolve!: (value: typeof item)=>void; vi.mocked(api.changeWorkspaceTrash).mockReturnValueOnce(new Promise(done => {resolve=done;}));
    const onTrashed=vi.fn(); const {rerender}=render(<WorkspaceTrashControl worldId="elderwyld" current={doc} onTrashed={onTrashed} />);
    fireEvent.click(screen.getByRole("button",{name:"Delete",exact:true}));fireEvent.click(screen.getByRole("button",{name:"Move to Trash",exact:true}));
    rerender(<WorkspaceTrashControl worldId="other" current={{...doc,id:"doc-b"}} onTrashed={onTrashed} />);
    await act(async () => resolve(item));expect(onTrashed).not.toHaveBeenCalled();
  });
  it("shows uncertain mutation failure without auto retry or closing the current document", async () => {
    vi.mocked(api.changeWorkspaceTrash).mockRejectedValueOnce(new Error("Network interrupted. Reload to check its state."));
    const onTrashed=vi.fn();render(<WorkspaceTrashControl worldId="elderwyld" current={doc} onTrashed={onTrashed} />);
    fireEvent.click(screen.getByRole("button",{name:"Delete",exact:true}));fireEvent.click(screen.getByRole("button",{name:"Move to Trash",exact:true}));
    expect(await screen.findByRole("alert")).toHaveTextContent("Reload to check its state");
    expect(api.changeWorkspaceTrash).toHaveBeenCalledOnce();expect(onTrashed).not.toHaveBeenCalled();
  });
  it("restores from a fresh Trash inventory when no document is open", async () => {
    const restored=vi.fn();render(<WorkspaceTrashControl worldId="elderwyld" current={null} onTrashed={vi.fn()} onRestored={restored} />);
    fireEvent.click(screen.getByRole("button",{name:"Trash",exact:true}));
    const dialog=await screen.findByRole("dialog");
    fireEvent.click(await within(dialog).findByRole("button",{name:"Restore Disposable Plan"}));
    await waitFor(() => expect(restored).toHaveBeenCalledOnce());
    expect(api.changeWorkspaceTrash).toHaveBeenCalledWith("elderwyld",item,"restore");
    expect(dialog).toHaveTextContent("Trash is empty.");
  });
  it("ignores a late inventory response after switching Worlds", async () => {
    let resolve!: (value: typeof item[])=>void;vi.mocked(api.listWorkspaceTrash).mockReturnValueOnce(new Promise(done => {resolve=done;}));
    const {rerender}=render(<WorkspaceTrashControl worldId="elderwyld" current={null} onTrashed={vi.fn()} />);
    fireEvent.click(screen.getByRole("button",{name:"Trash",exact:true}));
    rerender(<WorkspaceTrashControl worldId="other" current={null} onTrashed={vi.fn()} />);
    await act(async () => resolve([item]));expect(screen.queryByText("Disposable Plan")).not.toBeInTheDocument();
  });
});

it("cancels campaign confirmation on scope change and uses the campaign adapter",async()=>{
 vi.mocked(api.changeCampaignPlanTrash).mockResolvedValue(item);
 const onTrashed=vi.fn();const {rerender}=render(<WorkspaceTrashControl campaignId="campaign-a" current={doc} onTrashed={onTrashed}/>);
 fireEvent.click(screen.getByRole("button",{name:"Delete",exact:true}));
 rerender(<WorkspaceTrashControl campaignId="campaign-b" current={doc} onTrashed={onTrashed}/>);
 expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
 expect(api.changeCampaignPlanTrash).not.toHaveBeenCalled();
 fireEvent.click(screen.getByRole("button",{name:"Delete",exact:true}));
 fireEvent.click(screen.getByRole("button",{name:"Move to Trash",exact:true}));
 await waitFor(()=>expect(onTrashed).toHaveBeenCalledOnce());
 expect(api.changeCampaignPlanTrash).toHaveBeenCalledWith("campaign-b",doc,"trash");
 expect(api.changeWorkspaceTrash).not.toHaveBeenCalled();
});
