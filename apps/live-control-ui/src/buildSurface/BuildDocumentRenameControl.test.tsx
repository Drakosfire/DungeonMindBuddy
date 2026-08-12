import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { BuildDocumentRenameControl } from "./BuildDocumentRenameControl";

describe("BuildDocumentRenameControl", () => {
  it("does not PATCH blank or unchanged titles", async () => {
    const user = userEvent.setup();
    const onRename = vi.fn();
    render(
      <BuildDocumentRenameControl currentTitle="Ironveil Property" onRename={onRename} />,
    );

    await user.click(screen.getByTestId("build-document-rename-open"));
    const input = screen.getByTestId("build-document-rename-title");
    expect(input).toHaveValue("Ironveil Property");
    expect(screen.getByTestId("build-document-rename-submit")).toBeDisabled();

    await user.clear(input);
    await user.type(input, "   ");
    expect(screen.getByTestId("build-document-rename-submit")).toBeDisabled();

    await user.clear(input);
    await user.type(input, " Ironveil Property ");
    expect(screen.getByTestId("build-document-rename-submit")).toBeDisabled();
    expect(onRename).not.toHaveBeenCalled();
  });

  it("submits a trimmed new title", async () => {
    const user = userEvent.setup();
    const onRename = vi.fn().mockResolvedValue({
      ok: true,
      value: {
        document_id: "11111111-1111-4111-8111-111111111111",
        title: "Ironveil Manufactory Grounds",
        revision: 2,
      },
    });
    render(
      <BuildDocumentRenameControl currentTitle="Ironveil Property" onRename={onRename} />,
    );

    await user.click(screen.getByTestId("build-document-rename-open"));
    const input = screen.getByTestId("build-document-rename-title");
    await user.clear(input);
    await user.type(input, "  Ironveil Manufactory Grounds  ");
    await user.click(screen.getByTestId("build-document-rename-submit"));

    expect(onRename).toHaveBeenCalledWith("Ironveil Manufactory Grounds");
  });

  it("keeps candidate title and shows stale error on 409-shaped failure", async () => {
    const user = userEvent.setup();
    const onRename = vi.fn().mockResolvedValue({
      ok: false,
      code: "execute_failed",
      reason: "Source changed elsewhere. Reload before retrying.",
    });
    render(
      <BuildDocumentRenameControl currentTitle="Ironveil Property" onRename={onRename} />,
    );

    await user.click(screen.getByTestId("build-document-rename-open"));
    const input = screen.getByTestId("build-document-rename-title");
    await user.clear(input);
    await user.type(input, "Candidate Title");
    await user.click(screen.getByTestId("build-document-rename-submit"));

    expect(await screen.findByTestId("build-document-rename-error")).toHaveTextContent(
      /Source changed elsewhere/i,
    );
    expect(input).toHaveValue("Candidate Title");
    expect(screen.getByTestId("build-document-rename-form")).toBeInTheDocument();
  });
});
