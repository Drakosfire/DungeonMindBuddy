import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { JSONContent } from "@tiptap/core";
import { authenticatedApiFetch } from "../api/liveApi";
import { markdownToTiptapDoc } from "../tiptap/markdown/markdownToTiptap";
import { tiptapJsonToSemanticMarkdown } from "../tiptap/markdown/calloutMarkdown";
import { ReadOnlyBodyContent } from "./ReadOnlyBodyContent";

const graphContent: JSONContent[] = [{
  type: "paragraph",
  content: [
    { type: "text", text: "Consult " },
    { type: "graphNodeReference", attrs: { nodeId: "loc:ironveil-warehouse", label: "Ironveil Warehouse" } },
    { type: "text", text: " before entering." },
  ],
}];

describe("ReadOnlyBodyContent Graph-reference activation", () => {
  it("keeps Graph references inert by default", () => {
    render(<ReadOnlyBodyContent content={graphContent} />);

    const reference = screen.getByText("Ironveil Warehouse");
    expect(reference.tagName).toBe("SPAN");
    expect(reference.closest("button")).toBeNull();
    expect(reference).toHaveAttribute("data-graph-node-id", "loc:ironveil-warehouse");
  });

  it("opts into a native keyboard-accessible button and sends its exact node ID", async () => {
    const onActivateGraphNode = vi.fn();
    const user = userEvent.setup();
    render(<ReadOnlyBodyContent content={graphContent} onActivateGraphNode={onActivateGraphNode} />);

    const reference = screen.getByRole("button", { name: "Ironveil Warehouse" });
    expect(reference).toHaveAttribute("data-graph-node-id", "loc:ironveil-warehouse");
    await user.tab();
    expect(reference).toHaveFocus();
    await user.keyboard("{Enter}");

    expect(onActivateGraphNode).toHaveBeenCalledTimes(1);
    expect(onActivateGraphNode).toHaveBeenCalledWith("loc:ironveil-warehouse", reference);
  });

  it("passes the clicked reference as the origin even when it was not focused first", () => {
    const onActivateGraphNode = vi.fn();
    render(<ReadOnlyBodyContent content={graphContent} onActivateGraphNode={onActivateGraphNode} />);
    const reference = screen.getByRole("button", { name: "Ironveil Warehouse" });
    expect(reference).not.toHaveFocus();
    fireEvent.click(reference);
    expect(onActivateGraphNode).toHaveBeenCalledWith("loc:ironveil-warehouse", reference);
  });

  it("does not activate references when authored content fails the safe-rendering checks", () => {
    const onActivateGraphNode = vi.fn();
    const unsafeContent: JSONContent[] = [
      ...graphContent,
      { type: "image", attrs: { src: "javascript:alert(1)" } },
    ];
    render(<ReadOnlyBodyContent content={unsafeContent} onActivateGraphNode={onActivateGraphNode} />);

    expect(screen.getByRole("status")).toHaveTextContent("cannot be displayed safely");
    expect(screen.queryByRole("button", { name: "Ironveil Warehouse" })).not.toBeInTheDocument();
    expect(onActivateGraphNode).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("status"));
    expect(onActivateGraphNode).not.toHaveBeenCalled();
  });
});


vi.mock("../api/liveApi", () => ({ authenticatedApiFetch: vi.fn() }));
const assetA = "ac6c15cc-8c68-4732-8ae2-d9f3f051393a";
const assetB = "bc6c15cc-8c68-4732-8ae2-d9f3f051393a";
function metadata(asset_id = assetA, delivery_url = "https://imagedelivery.net/account/map/public", state = "ready") {
  return { response: { ok: true, json: async () => ({ asset_id, delivery_url, state }) } } as Awaited<ReturnType<typeof authenticatedApiFetch>>;
}
function imageBody(assetId = assetA, alt = "Edge map"): JSONContent[] {
  return [{ type: "paragraph", content: [{ type: "mediaImage", attrs: { assetId, alt } }] }];
}

describe("ReadOnlyBodyContent saved media projection", () => {
  beforeEach(() => { vi.mocked(authenticatedApiFetch).mockReset(); });

  it("renders repeated saved images from real Markdown independently, preserving surrounding blocks and source", async () => {
    const user = userEvent.setup();
    vi.mocked(authenticatedApiFetch).mockResolvedValue(metadata());
    const markdown = `Before.\n\n> [!READ-ALOUD]\n> A quiet town.\n\n![Map detail](dmb-media:${assetA} "dmb-image:v1 width=40 collapsed=false")\n\n![Map overview](dmb-media:${assetA} "dmb-image:v1 width=80 collapsed=true")\n\n| Name | Role |\n| --- | --- |\n| Mara | Soldier |\n\nAfter.`;
    const doc = markdownToTiptapDoc(markdown).doc;
    const original = JSON.stringify(doc);
    const source = tiptapJsonToSemanticMarkdown(doc);
    const { container } = render(<ReadOnlyBodyContent content={doc.content} />);
    const detail = await screen.findByRole("img", { name: "Map detail" });
    expect(detail).toHaveAttribute("src", "https://imagedelivery.net/account/map/public");
    expect(detail.closest(".document-media-image")).toHaveStyle({ width: "40%" });
    expect(screen.queryByRole("img", { name: "Map overview" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Expand image: Map overview" }).closest(".document-media-image")).toHaveStyle({ width: "80%" });
    await user.click(screen.getByRole("button", { name: "Expand image: Map overview" }));
    expect(screen.getByRole("img", { name: "Map overview" })).toBeVisible();
    await user.click(screen.getByRole("button", { name: "Collapse image: Map detail" }));
    expect(screen.getByRole("img", { name: "Map overview" })).toBeVisible();
    expect(container.querySelector('[data-md-callout="read-aloud"]')).toHaveTextContent("A quiet town.");
    expect(screen.getByRole("table")).toHaveTextContent("Mara");
    expect(screen.getByText("Before.")).toBeInTheDocument();
    expect(screen.getByText("After.")).toBeInTheDocument();
    expect(JSON.stringify(doc)).toBe(original);
    expect(tiptapJsonToSemanticMarkdown(doc)).toBe(source);
    expect(vi.mocked(authenticatedApiFetch).mock.calls.every(([url]) => String(url).endsWith("/metadata"))).toBe(true);
  });

  it.each([
    [assetB, "https://imagedelivery.net/account/map/public", "ready"],
    [assetA, "http://imagedelivery.net/account/map/public", "ready"],
    [assetA, "https://evil.example/map.png", "ready"],
    [assetA, "https://imagedelivery.net/account/map/public", "staged"],
    [assetA, "https://user:password@imagedelivery.net/account/map/public", "ready"],
  ])("preserves an unavailable reference without rendering untrusted metadata %s %s %s", async (id, url, state) => {
    vi.mocked(authenticatedApiFetch).mockResolvedValue(metadata(id, url, state));
    const { container } = render(<ReadOnlyBodyContent content={imageBody()} />);
    expect(await screen.findByText(/Image unavailable/)).toBeInTheDocument();
    expect(screen.queryByRole("img")).not.toBeInTheDocument();
    expect(screen.getByText("Edge map")).toBeInTheDocument();
    expect(container.querySelector(`[data-media-asset-id="${assetA}"]`)).toBeInTheDocument();
  });

  it("ignores the old occurrence's metadata when captured content changes", async () => {
    let resolveOld!: (value: Awaited<ReturnType<typeof authenticatedApiFetch>>) => void;
    vi.mocked(authenticatedApiFetch).mockImplementationOnce(() => new Promise(resolve => { resolveOld = resolve; }));
    vi.mocked(authenticatedApiFetch).mockResolvedValue(metadata(assetB, "https://imagedelivery.net/account/new/public"));
    const { rerender } = render(<ReadOnlyBodyContent content={imageBody()} />);
    rerender(<ReadOnlyBodyContent content={imageBody(assetB, "New map")} />);
    expect(await screen.findByRole("img", { name: "New map" })).toHaveAttribute("src", "https://imagedelivery.net/account/new/public");
    resolveOld(metadata());
    await waitFor(() => expect(screen.queryByRole("img", { name: "Edge map" })).not.toBeInTheDocument());
    expect(screen.getByRole("img", { name: "New map" })).toHaveAttribute("src", "https://imagedelivery.net/account/new/public");
  });

  it("rejects malformed saved media before metadata lookup and retains unsafe body protection", () => {
    const body = imageBody();
    body[0].content![0].attrs!.width = 101;
    body[0].content![0].attrs!.collapsed = false;
    render(<ReadOnlyBodyContent content={body} />);
    expect(screen.getByRole("status")).toHaveTextContent("cannot be displayed safely");
    expect(authenticatedApiFetch).not.toHaveBeenCalled();
  });
});
