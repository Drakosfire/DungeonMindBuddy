import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as liveApi from "../api/liveApi";
import { useBuildNativeWorldSourceEvidence } from "./useBuildNativeWorldSourceEvidence";

vi.mock("../api/liveApi", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../api/liveApi")>();
  return {
    ...actual,
    getNativeWorldSourceAdmissionStatus: vi.fn(),
    admitNativeWorldSource: vi.fn(),
  };
});

const DOC_A = "11111111-1111-4111-8111-111111111111";
const DOC_B = "22222222-2222-4222-8222-222222222222";

function status(documentId: string, state: "pending" | "admitted" = "pending") {
  return {
    schema_version: "dmb_native_world_source_admission_status_v1" as const,
    state,
    code: state === "pending" ? "native_admission_pending" : null,
    message: state === "pending" ? "Saved source is pending" : null,
    world_id: "eldyrwild",
    document_id: documentId,
    loaded_revision: 7,
    body_sha256: "body-sha256",
    admission_id: "admission-id",
    space_id: "eldyrwild",
    published_revision_id: state === "admitted" ? "rev:admitted" : null,
    source_artifact_id: state === "admitted" ? "source:admitted" : null,
    source_revision_id: state === "admitted" ? "source-rev:admitted" : null,
    evidence_ref_id: state === "admitted" ? "evidence:admitted" : null,
    span_start_byte: state === "admitted" ? 0 : null,
    span_end_byte: state === "admitted" ? 10 : null,
  };
}

describe("useBuildNativeWorldSourceEvidence", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(liveApi.getNativeWorldSourceAdmissionStatus).mockResolvedValue(status(DOC_A));
    vi.mocked(liveApi.admitNativeWorldSource).mockResolvedValue(status(DOC_A, "admitted"));
  });

  it("loads persisted status for the selected document and retries its exact registry revision", async () => {
    const { result } = renderHook(() => useBuildNativeWorldSourceEvidence(DOC_A));
    await waitFor(() => expect(result.current.status?.state).toBe("pending"));

    await act(async () => result.current.retry());

    expect(liveApi.getNativeWorldSourceAdmissionStatus).toHaveBeenCalledWith(DOC_A);
    expect(liveApi.admitNativeWorldSource).toHaveBeenCalledWith(DOC_A, 7);
    expect(result.current.status?.state).toBe("admitted");
  });

  it("reloads status when selection changes and does not retain the prior document's result", async () => {
    vi.mocked(liveApi.getNativeWorldSourceAdmissionStatus)
      .mockResolvedValueOnce(status(DOC_A))
      .mockResolvedValueOnce(status(DOC_B, "admitted"));
    const { result, rerender } = renderHook(
      ({ documentId }: { documentId: string }) => useBuildNativeWorldSourceEvidence(documentId),
      { initialProps: { documentId: DOC_A } },
    );
    await waitFor(() => expect(result.current.status?.document_id).toBe(DOC_A));

    rerender({ documentId: DOC_B });

    await waitFor(() => expect(result.current.status?.document_id).toBe(DOC_B));
    expect(result.current.status?.state).toBe("admitted");
  });
});
