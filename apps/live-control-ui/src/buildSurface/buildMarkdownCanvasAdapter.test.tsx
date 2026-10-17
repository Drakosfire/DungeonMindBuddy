import { fireEvent, render, screen, within } from "@testing-library/react";
import { afterAll, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";

import { useMarkdownCanvasSession } from "../markdownCanvas/MarkdownCanvasSession";
import { useBuildMarkdownCanvasSlots } from "./buildMarkdownCanvasAdapter";

// happy-dom lacks the native dialog API; browser focus/Escape behavior is a rendered gate.
const dialogPrototype = Object.getPrototypeOf(document.createElement("dialog"));
const originalShowModal = Object.getOwnPropertyDescriptor(dialogPrototype, "showModal");
beforeAll(() => {
  Object.defineProperty(dialogPrototype, "showModal", { configurable: true, value(this: HTMLDialogElement) {
    this.setAttribute("open", "");
    this.open = true;
  } });
});
afterAll(() => {
  if (originalShowModal) Object.defineProperty(dialogPrototype, "showModal", originalShowModal);
  else Reflect.deleteProperty(dialogPrototype, "showModal");
});

vi.mock("../markdownCanvas/MarkdownCanvasSession", () => ({ useMarkdownCanvasSession: vi.fn() }));

function Controls({ hideFooterSave = true }: { hideFooterSave?: boolean }) {
  const slots = useBuildMarkdownCanvasSlots({ hideFooterSave });
  return <>{slots.tools}{slots.actions}</>;
}

const discard = vi.fn().mockResolvedValue(undefined);
const save = vi.fn().mockResolvedValue(undefined);
type Session = ReturnType<typeof useMarkdownCanvasSession>;
function session(dirty: boolean, overrides: Partial<Session> = {}) {
  vi.mocked(useMarkdownCanvasSession).mockReturnValue({
    record: { title: "Source" }, documentId: "source-A", documentKey: "source-A:1", dirty,
    phase: "ready_dirty", activeCommand: null, exportedMarkdownAuthoritative: false, ...overrides,
    discardLocalDraft: discard, saveMarkdown: save, saveDisabled: true,
  } as unknown as Session);
}
function openConfirmation() {
  fireEvent.click(screen.getByRole("button", { name: "Discard draft", exact: true }));
  return screen.getByRole("alertdialog", { name: "Discard local draft?" });
}

describe("Build source draft recovery", () => {
  beforeEach(() => { vi.clearAllMocks(); });

  it("offers accessible confirmation with hosted Save and preserves the draft on cancel", () => {
    session(true);
    render(<Controls />);
    const dialog = openConfirmation();
    expect(dialog).toHaveAccessibleDescription(/saved source will not change/);
    fireEvent.click(within(dialog).getByRole("button", { name: "Keep editing" }));
    expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument();
    expect(discard).not.toHaveBeenCalled();
    expect(save).not.toHaveBeenCalled();
    expect(screen.queryByRole("button", { name: "Save", exact: true })).not.toBeInTheDocument();
  });

  it("allows idle unsafe-source recovery through the existing handler only after explicit confirmation", () => {
    session(true, { phase: "save_error" });
    render(<Controls />);
    const dialog = openConfirmation();
    expect(discard).not.toHaveBeenCalled();
    fireEvent.click(within(dialog).getByRole("button", { name: "Discard changes" }));
    expect(discard).toHaveBeenCalledTimes(1);
    expect(save).not.toHaveBeenCalled();
    expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument();
  });

  it("cancels native dialog Escape without discarding", () => {
    session(true);
    render(<Controls />);
    fireEvent(openConfirmation(), new Event("cancel", { cancelable: true }));
    expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument();
    expect(discard).not.toHaveBeenCalled();
  });

  it("leaves clean sources quiet", () => {
    session(false);
    render(<Controls />);
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });

  it("preserves footer Save authority", () => {
    session(true);
    render(<Controls hideFooterSave={false} />);
    expect(screen.getByRole("button", { name: "Save", exact: true })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Discard draft" })).toBeEnabled();
    expect(save).not.toHaveBeenCalled();
  });

  it.each(["loading", "preparing", "committing", "committed_verification_pending"] as const)(
    "refuses to open confirmation during %s", phase => {
      session(true, { phase });
      render(<Controls />);
      const button = screen.getByRole("button", { name: "Discard draft" });
      expect(button).toBeDisabled();
      fireEvent.click(button);
      expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument();
      expect(discard).not.toHaveBeenCalled();
    },
  );

  it("refuses an already-open confirmation when a document mutation starts", () => {
    session(true);
    const { rerender } = render(<Controls />);
    openConfirmation();
    session(true, { activeCommand: { id: "build.rename", documentId: "source-A", startedAt: 1 } });
    rerender(<Controls />);
    const dialog = screen.getByRole("alertdialog");
    const confirm = within(dialog).getByRole("button", { name: "Discard changes" });
    expect(confirm).toBeDisabled();
    fireEvent.click(confirm);
    expect(discard).not.toHaveBeenCalled();
    fireEvent.click(within(dialog).getByRole("button", { name: "Keep editing" }));
    expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument();
  });

  it.each([
    { documentId: "source-B", documentKey: "source-B:1" },
    { documentId: "source-A", documentKey: "source-A:2" },
  ])("invalidates pending consent when identity changes to %j", identity => {
    session(true);
    const { rerender } = render(<Controls />);
    openConfirmation();
    session(true, identity);
    rerender(<Controls />);
    expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument();
    session(true);
    rerender(<Controls />);
    expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument();
    expect(discard).not.toHaveBeenCalled();
  });
});


describe("protected Build draft review in navigation", () => {
  it("keeps recovery reachable with footer hidden and cancellation leaves both versions untouched", () => {
    const prepare = vi.fn(() => ({ documentId: "source-A", fence: "fence", editorText: "Local wording", preservedMarkdown: "# Preserved source" }));
    const confirm = vi.fn();
    session(true, { exportedMarkdownAuthoritative: true, prepareDraftRecovery: prepare, confirmDraftRecovery: confirm });
    render(<Controls hideFooterSave />);
    fireEvent.click(screen.getByRole("button", { name: "Review protected draft", exact: true }));
    const dialog = screen.getByRole("dialog", { name: "Review protected draft" });
    expect(dialog).toHaveTextContent("Local wording");
    expect(dialog).toHaveTextContent("# Preserved source");
    fireEvent.click(within(dialog).getByRole("button", { name: "Cancel review" }));
    expect(confirm).not.toHaveBeenCalled();
    expect(discard).not.toHaveBeenCalled();
    expect(save).not.toHaveBeenCalled();
  });
  it("offers Restore for a clean re-imported draft even without footer controls", () => {
    const restore = vi.fn();
    session(false, { draftRecoveryAvailable: true, phase: "ready_clean", restoreDraftRecovery: restore });
    render(<Controls hideFooterSave />);
    fireEvent.click(screen.getByRole("button", { name: "Restore protected draft" }));
    expect(restore).toHaveBeenCalledOnce();
    expect(screen.queryByRole("button", { name: "Discard draft" })).not.toBeInTheDocument();
  });
});
