import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { BuildDocumentCreateControl } from "./BuildDocumentCreateControl";

describe("BuildDocumentCreateControl", () => {
  it("requires a title and does not default to untitled", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    render(
      <BuildDocumentCreateControl suggestedCampaignId="longmont-c2" onSubmit={onSubmit} />,
    );

    await user.click(screen.getByTestId("build-document-create-open"));
    const titleInput = screen.getByTestId("build-document-create-title");
    expect(titleInput).toHaveValue("");
    expect(titleInput).toHaveAttribute("placeholder", "Ironveil Property");
    expect(screen.getByTestId("build-document-create-submit")).toBeDisabled();

    await user.type(titleInput, "Ironveil Property");
    await user.click(screen.getByTestId("build-document-create-submit"));

    expect(onSubmit).toHaveBeenCalledWith({
      title: "Ironveil Property",
      campaignId: "longmont-c2",
    });
  });

  it("requires an explicit campaign when none is suggested", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    render(<BuildDocumentCreateControl suggestedCampaignId={null} onSubmit={onSubmit} />);

    await user.click(screen.getByTestId("build-document-create-open"));
    await user.type(screen.getByTestId("build-document-create-title"), "Stormspire Notes");
    expect(screen.getByTestId("build-document-create-submit")).toBeDisabled();

    await user.selectOptions(screen.getByTestId("build-document-create-campaign"), "longmont-c1");
    await user.click(screen.getByTestId("build-document-create-submit"));
    expect(onSubmit).toHaveBeenCalledWith({
      title: "Stormspire Notes",
      campaignId: "longmont-c1",
    });
  });

  it("shows Retry Open when activation fails", async () => {
    const user = userEvent.setup();
    render(
      <BuildDocumentCreateControl
        suggestedCampaignId="longmont-c1"
        activationError="network"
        onSubmit={vi.fn()}
        onRetryOpen={vi.fn()}
      />,
    );

    await user.click(screen.getByTestId("build-document-create-open"));
    expect(screen.getByTestId("build-document-create-retry-open")).toBeInTheDocument();
  });

  it("does not adopt a foreign suggested campaign into the visible select", async () => {
    const user = userEvent.setup();
    render(
      <BuildDocumentCreateControl suggestedCampaignId="eldyrwild" onSubmit={vi.fn()} />,
    );

    await user.click(screen.getByTestId("build-document-create-open"));
    const campaignSelect = screen.getByTestId("build-document-create-campaign");
    expect(campaignSelect).toHaveValue("");
    expect(
      Array.from(campaignSelect.querySelectorAll("option")).map((option) => option.value),
    ).not.toContain("eldyrwild");
  });
});
