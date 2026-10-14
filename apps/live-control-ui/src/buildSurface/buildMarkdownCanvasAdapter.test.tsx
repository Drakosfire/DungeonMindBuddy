import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useMarkdownCanvasSession } from "../markdownCanvas/MarkdownCanvasSession";
import { useBuildMarkdownCanvasSlots } from "./buildMarkdownCanvasAdapter";

vi.mock("../markdownCanvas/MarkdownCanvasSession", () => ({ useMarkdownCanvasSession: vi.fn() }));

function Controls({ hideFooterSave = true }: { hideFooterSave?: boolean }) {
  const slots = useBuildMarkdownCanvasSlots({ hideFooterSave });
  return <>{slots.tools}{slots.actions}</>;
}

const discard = vi.fn().mockResolvedValue(undefined);
const save = vi.fn().mockResolvedValue(undefined);

function session(dirty: boolean, overrides: Partial<Pick<ReturnType<typeof useMarkdownCanvasSession>, "phase" | "activeCommand">> = {}) {
  vi.mocked(useMarkdownCanvasSession).mockReturnValue({
    record: { title: "Source" }, dirty, phase: "ready_dirty", activeCommand: null, ...overrides, exportedMarkdownAuthoritative: false,
    discardLocalDraft: discard, saveMarkdown: save, saveDisabled: true,
  } as unknown as ReturnType<typeof useMarkdownCanvasSession>);
}

describe("Build source draft recovery", () => {
  beforeEach(() => { vi.clearAllMocks(); });
  afterEach(() => { vi.restoreAllMocks(); });

  it("offers discard even when Save is hosted in Edit, and cancellation preserves the draft", () => {
    session(true);
    const confirm = vi.spyOn(window, "confirm").mockReturnValue(false);
    render(<Controls />);
    fireEvent.click(screen.getByRole("button", { name: "Discard local draft" }));
    expect(confirm).toHaveBeenCalledWith(expect.stringContaining("saved source will not change"));
    expect(discard).not.toHaveBeenCalled();
    expect(save).not.toHaveBeenCalled();
    expect(screen.queryByRole("button", { name: "Save", exact: true })).not.toBeInTheDocument();
  });

  it("uses the existing discard handler only after confirmation and never saves", () => {
    session(true);
    vi.spyOn(window, "confirm").mockReturnValue(true);
    render(<Controls />);
    fireEvent.click(screen.getByRole("button", { name: "Discard local draft" }));
    expect(discard).toHaveBeenCalledTimes(1);
    expect(save).not.toHaveBeenCalled();
  });

  it("leaves clean sources quiet", () => {
    session(false);
    render(<Controls />);
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });

  it("preserves footer Save authority when Save is not hosted elsewhere", () => {
    session(true);
    render(<Controls hideFooterSave={false} />);
    expect(screen.getByRole("button", { name: "Save", exact: true })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Discard local draft" })).toBeEnabled();
    expect(save).not.toHaveBeenCalled();
  });
});


describe("Build recovery operation exclusion", () => {
  afterEach(() => { vi.restoreAllMocks(); });

  it.each(["loading", "preparing", "committing", "committed_verification_pending"] as const)(
    "refuses discard during %s without treating saveDisabled as the busy signal", phase => {
      vi.clearAllMocks();
      session(true, { phase });
      const confirm = vi.spyOn(window, "confirm").mockReturnValue(true);
      render(<Controls />);
      const button = screen.getByRole("button", { name: "Discard local draft" });
      expect(button).toBeDisabled();
      fireEvent.click(button);
      expect(confirm).not.toHaveBeenCalled();
      expect(discard).not.toHaveBeenCalled();
    },
  );

  it("refuses discard while a document mutation owns the session", () => {
    vi.clearAllMocks();
    session(true, { activeCommand: { id: "build.rename", documentId: "source", startedAt: 1 } });
    const confirm = vi.spyOn(window, "confirm").mockReturnValue(true);
    render(<Controls />);
    fireEvent.click(screen.getByRole("button", { name: "Discard local draft" }));
    expect(screen.getByRole("button", { name: "Discard local draft" })).toBeDisabled();
    expect(confirm).not.toHaveBeenCalled();
    expect(discard).not.toHaveBeenCalled();
  });
});
