import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { BuildDocumentCreateControl } from "./BuildDocumentCreateControl";

describe("BuildDocumentCreateControl", () => {
  const baseProps = {
    creatableCampaignIds: ["longmont-c2"],
    suggestedCampaignId: "longmont-c2",
    onSubmit: vi.fn(),
    onImportSubmit: vi.fn(),
  };

  it("blocks empty import submit and disables controls while creating", () => {
    const onImportSubmit = vi.fn();
    render(
      <BuildDocumentCreateControl
        {...baseProps}
        creating
        onImportSubmit={onImportSubmit}
      />,
    );

    expect(screen.getByTestId("build-document-import-open")).toBeDisabled();
    expect(onImportSubmit).not.toHaveBeenCalled();
  });

  it("blocks import submit while creating and ignores rapid double submit", () => {
    const onImportSubmit = vi.fn();
    const { rerender } = render(
      <BuildDocumentCreateControl {...baseProps} onImportSubmit={onImportSubmit} />,
    );

    fireEvent.click(screen.getByTestId("build-document-import-open"));
    fireEvent.change(screen.getByTestId("build-document-create-title"), {
      target: { value: "Imported" },
    });
    fireEvent.change(screen.getByTestId("build-document-import-markdown"), {
      target: { value: "# Imported\n\nBody.\n" },
    });

    fireEvent.click(screen.getByTestId("build-document-import-submit"));
    expect(onImportSubmit).toHaveBeenCalledTimes(1);

    rerender(
      <BuildDocumentCreateControl
        {...baseProps}
        creating
        onImportSubmit={onImportSubmit}
      />,
    );

    const submit = screen.getByTestId("build-document-import-submit");
    expect(submit).toBeDisabled();
    fireEvent.click(submit);
    expect(onImportSubmit).toHaveBeenCalledTimes(1);
  });

  it("submits import with title campaign and markdown", () => {
    const onImportSubmit = vi.fn();
    render(
      <BuildDocumentCreateControl {...baseProps} onImportSubmit={onImportSubmit} />,
    );

    fireEvent.click(screen.getByTestId("build-document-import-open"));
    fireEvent.change(screen.getByTestId("build-document-create-title"), {
      target: { value: "Imported" },
    });
    fireEvent.change(screen.getByTestId("build-document-import-markdown"), {
      target: { value: "# Imported\n\nBody.\n" },
    });
    fireEvent.click(screen.getByTestId("build-document-import-submit"));

    expect(onImportSubmit).toHaveBeenCalledWith({
      title: "Imported",
      campaignId: "longmont-c2",
      markdown: expect.stringContaining("# Imported"),
    });
  });

  it("retains pasted markdown and exposes retry import after failure", () => {
    const onRetryImport = vi.fn();
    render(
      <BuildDocumentCreateControl
        {...baseProps}
        importError="prepare failed"
        pendingImportDocumentId="11111111-1111-4111-8111-111111111111"
        onRetryImport={onRetryImport}
      />,
    );

    fireEvent.click(screen.getByTestId("build-document-import-open"));
    const markdownField = screen.getByTestId("build-document-import-markdown");
    fireEvent.change(markdownField, {
      target: { value: "# Keep me\n" },
    });
    fireEvent.click(screen.getByTestId("build-document-import-retry"));

    expect(markdownField).toHaveValue("# Keep me\n");
    expect(onRetryImport).toHaveBeenCalledWith({ markdown: "# Keep me\n" });
  });
});
