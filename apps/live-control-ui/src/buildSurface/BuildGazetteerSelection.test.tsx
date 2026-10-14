import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { BuildIngestToolbar } from "./BuildIngestToolbar";
import { useBuildExtraction } from "./useBuildExtraction";

const state = vi.hoisted(() => ({ launching: false }));
vi.mock("./useBuildExtraction", () => ({ useBuildExtraction: vi.fn(() => ({
  statusLabel: "No extraction run", error: null, canLaunch: true, canRefresh: false,
  canOpenGraphReview: false, launching: state.launching, handoff: null, run: null,
  launch: vi.fn(), refresh: vi.fn(),
})) }));
vi.mock("./useBuildNativeWorldSourceEvidence", () => ({ useBuildNativeWorldSourceEvidence: () => ({
  loading: false, status: null, error: null, retrying: false, retry: vi.fn(), reload: vi.fn(),
}) }));

describe("Build extraction profile selection", () => {
  beforeEach(() => { state.launching = false; vi.clearAllMocks(); });
  it("keeps pilot default and submits an explicit gazetteer choice", () => {
    render(<BuildIngestToolbar documentId="doc-a" />);
    expect(screen.getByLabelText("Extraction approach")).toHaveValue("pilot");
    fireEvent.change(screen.getByLabelText("Extraction approach"), { target: { value: "gazetteer" } });
    expect(useBuildExtraction).toHaveBeenLastCalledWith({ documentId: "doc-a", profile: "gazetteer" });
  });
  it("resets selection for another document", () => {
    const view = render(<BuildIngestToolbar documentId="doc-a" />);
    fireEvent.change(screen.getByLabelText("Extraction approach"), { target: { value: "gazetteer" } });
    view.rerender(<BuildIngestToolbar documentId="doc-b" />);
    expect(screen.getByLabelText("Extraction approach")).toHaveValue("pilot");
    expect(useBuildExtraction).toHaveBeenLastCalledWith({ documentId: "doc-b", profile: "pilot" });
  });
  it("locks profile selection during launch", () => {
    state.launching = true;
    render(<BuildIngestToolbar documentId="doc-a" />);
    expect(screen.getByLabelText("Extraction approach")).toBeDisabled();
  });
});
