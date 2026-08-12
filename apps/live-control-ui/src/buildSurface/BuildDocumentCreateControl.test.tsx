import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { BuildDocumentCreateControl } from "./BuildDocumentCreateControl";

describe("BuildDocumentCreateControl", () => {
  const baseProps = {
    destinationOptions: [
      {
        kind: "campaign" as const,
        campaignId: "longmont-c2",
        worldId: "eldyrwild",
        label: "longmont-c2",
        value: "campaign:longmont-c2",
      },
    ],
    suggestedDestinationValue: "campaign:longmont-c2",
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

  it("submits import with title destination and markdown", () => {
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
      destination: { kind: "campaign", campaignId: "longmont-c2" },
      markdown: expect.stringContaining("# Imported"),
    });
  });

  it("does not submit whitespace-only markdown", () => {
    const onImportSubmit = vi.fn();
    render(
      <BuildDocumentCreateControl {...baseProps} onImportSubmit={onImportSubmit} />,
    );

    fireEvent.click(screen.getByTestId("build-document-import-open"));
    fireEvent.change(screen.getByTestId("build-document-create-title"), {
      target: { value: "Imported" },
    });
    fireEvent.change(screen.getByTestId("build-document-import-markdown"), {
      target: { value: "   \n\t  \n" },
    });

    const submit = screen.getByTestId("build-document-import-submit");
    expect(submit).toBeDisabled();
    fireEvent.click(submit);
    expect(onImportSubmit).not.toHaveBeenCalled();
  });

  it("submits markdown with trailing newlines untrimmed", () => {
    const onImportSubmit = vi.fn();
    render(
      <BuildDocumentCreateControl {...baseProps} onImportSubmit={onImportSubmit} />,
    );

    fireEvent.click(screen.getByTestId("build-document-import-open"));
    fireEvent.change(screen.getByTestId("build-document-create-title"), {
      target: { value: "Imported" },
    });
    const markdown = "# Imported\n\nBody.\n\n";
    fireEvent.change(screen.getByTestId("build-document-import-markdown"), {
      target: { value: markdown },
    });
    fireEvent.click(screen.getByTestId("build-document-import-submit"));

    expect(onImportSubmit).toHaveBeenCalledWith({
      title: "Imported",
      destination: { kind: "campaign", campaignId: "longmont-c2" },
      markdown,
    });
  });

  it("requires world name before new-world submit is enabled", () => {
    render(<BuildDocumentCreateControl {...baseProps} />);

    fireEvent.click(screen.getByTestId("build-document-create-open"));
    fireEvent.change(screen.getByTestId("build-document-create-destination"), {
      target: { value: "__new_world__" },
    });
    fireEvent.change(screen.getByTestId("build-document-create-title"), {
      target: { value: "Orchard Notes" },
    });

    expect(screen.getByTestId("build-document-create-submit")).toBeDisabled();
    expect(screen.getByTestId("build-document-create-world-name")).toBeInTheDocument();
  });

  it("submits new world destination with trimmed world name", () => {
    const onSubmit = vi.fn();
    render(<BuildDocumentCreateControl {...baseProps} onSubmit={onSubmit} />);

    fireEvent.click(screen.getByTestId("build-document-create-open"));
    fireEvent.change(screen.getByTestId("build-document-create-destination"), {
      target: { value: "__new_world__" },
    });
    fireEvent.change(screen.getByTestId("build-document-create-world-name"), {
      target: { value: "The Glass Orchard" },
    });
    fireEvent.change(screen.getByTestId("build-document-create-title"), {
      target: { value: "Orchard Notes" },
    });
    fireEvent.click(screen.getByTestId("build-document-create-submit"));

    expect(onSubmit).toHaveBeenCalledWith({
      title: "Orchard Notes",
      destination: { kind: "new_world", name: "The Glass Orchard" },
    });
  });

  it("disables destination and world name fields while creating", () => {
    const { rerender } = render(<BuildDocumentCreateControl {...baseProps} />);

    fireEvent.click(screen.getByTestId("build-document-create-open"));
    fireEvent.change(screen.getByTestId("build-document-create-destination"), {
      target: { value: "__new_world__" },
    });
    fireEvent.change(screen.getByTestId("build-document-create-world-name"), {
      target: { value: "The Glass Orchard" },
    });

    rerender(<BuildDocumentCreateControl {...baseProps} creating />);

    expect(screen.getByTestId("build-document-create-destination")).toBeDisabled();
    expect(screen.getByTestId("build-document-create-world-name")).toBeDisabled();
  });

  it("preserves New world selection and world name when destination options refresh", () => {
    const onSubmit = vi.fn();
    const { rerender } = render(
      <BuildDocumentCreateControl {...baseProps} onSubmit={onSubmit} createError={null} />,
    );

    fireEvent.click(screen.getByTestId("build-document-create-open"));
    fireEvent.change(screen.getByTestId("build-document-create-destination"), {
      target: { value: "__new_world__" },
    });
    fireEvent.change(screen.getByTestId("build-document-create-world-name"), {
      target: { value: "The Glass Orchard" },
    });
    fireEvent.change(screen.getByTestId("build-document-create-title"), {
      target: { value: "Orchard Notes" },
    });

    // Simulate managed-worlds refresh after W is created but source POST failed:
    // suggested snaps back to campaign, and a world option appears.
    rerender(
      <BuildDocumentCreateControl
        {...baseProps}
        onSubmit={onSubmit}
        createError="The world was created, but the source could not be created."
        suggestedDestinationValue="campaign:longmont-c2"
        destinationOptions={[
          ...baseProps.destinationOptions,
          {
            kind: "world",
            worldId: "the-glass-orchard",
            label: "The Glass Orchard",
            value: "world:the-glass-orchard",
          },
        ]}
      />,
    );

    expect(screen.getByTestId("build-document-create-destination")).toHaveValue("__new_world__");
    expect(screen.getByTestId("build-document-create-world-name")).toHaveValue("The Glass Orchard");

    fireEvent.click(screen.getByTestId("build-document-create-submit"));
    expect(onSubmit).toHaveBeenCalledWith({
      title: "Orchard Notes",
      destination: { kind: "new_world", name: "The Glass Orchard" },
    });
  });

  it("follows suggested destination when Build navigates C1 → C2 without an explicit pick", () => {
    const c1Option = {
      kind: "campaign" as const,
      campaignId: "longmont-c1",
      worldId: "eldyrwild",
      label: "longmont-c1",
      value: "campaign:longmont-c1",
    };
    const c2Option = {
      kind: "campaign" as const,
      campaignId: "longmont-c2",
      worldId: "eldyrwild",
      label: "longmont-c2",
      value: "campaign:longmont-c2",
    };
    const { rerender } = render(
      <BuildDocumentCreateControl
        {...baseProps}
        destinationOptions={[c1Option, c2Option]}
        suggestedDestinationValue="campaign:longmont-c1"
      />,
    );

    fireEvent.click(screen.getByTestId("build-document-create-open"));
    expect(screen.getByTestId("build-document-create-destination")).toHaveValue(
      "campaign:longmont-c1",
    );

    rerender(
      <BuildDocumentCreateControl
        {...baseProps}
        destinationOptions={[c1Option, c2Option]}
        suggestedDestinationValue="campaign:longmont-c2"
      />,
    );

    expect(screen.getByTestId("build-document-create-destination")).toHaveValue(
      "campaign:longmont-c2",
    );
  });

  it("upgrades derived campaign destination to colliding managed world when suggestion arrives", () => {
    const campaignOption = {
      kind: "campaign" as const,
      campaignId: "longmont-c2",
      worldId: "eldyrwild",
      label: "longmont-c2",
      value: "campaign:longmont-c2",
    };
    const worldOption = {
      kind: "world" as const,
      worldId: "longmont-c2",
      label: "Longmont C2 (world)",
      value: "world:longmont-c2",
    };

    const { rerender } = render(
      <BuildDocumentCreateControl
        {...baseProps}
        destinationOptions={[campaignOption]}
        suggestedDestinationValue="campaign:longmont-c2"
      />,
    );

    fireEvent.click(screen.getByTestId("build-document-create-open"));
    expect(screen.getByTestId("build-document-create-destination")).toHaveValue(
      "campaign:longmont-c2",
    );

    // Managed worlds load after first paint; controller now recommends the world destination.
    rerender(
      <BuildDocumentCreateControl
        {...baseProps}
        destinationOptions={[campaignOption, worldOption]}
        suggestedDestinationValue="world:longmont-c2"
      />,
    );

    expect(screen.getByTestId("build-document-create-destination")).toHaveValue(
      "world:longmont-c2",
    );
  });
});
