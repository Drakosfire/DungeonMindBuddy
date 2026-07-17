import { describe, expect, it } from "vitest";

import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import {
  NORTH_GATE_RUNBOOK_TARGET_RELPATH,
  northGateRunbookCreateRequest,
  northGateSessionRunbookStarterMarkdown,
  runbookDescriptorFromRecord,
  tiptapRunbookStorageKey,
} from "./tiptapRunbookDescriptors";
import { FIXTURE_DOC_ID } from "../../planSurface/config/planSessionDescriptor";
import { fixtureWorkspaceDocumentRecord } from "../../planSurface/config/planSessionDescriptor";

describe("Tiptap runbook descriptors", () => {
  it("maps registry records to runbook descriptors with opaque ids", () => {
    const record = fixtureWorkspaceDocumentRecord({
      document_id: FIXTURE_DOC_ID,
      kind: "runbook",
      title: "North Gate Session Runbook",
      target_relpath: NORTH_GATE_RUNBOOK_TARGET_RELPATH,
    });
    const descriptor = runbookDescriptorFromRecord(record);
    expect(descriptor.documentId).toBe(FIXTURE_DOC_ID);
    expect(descriptor.targetRelpath).toBe(NORTH_GATE_RUNBOOK_TARGET_RELPATH);
  });

  it("uses workspace document storage keys", () => {
    const key = tiptapRunbookStorageKey({ documentId: FIXTURE_DOC_ID });
    expect(key).toBe(`dmb.workspaceDocument.${FIXTURE_DOC_ID}`);
  });

  it("keeps the North Gate reset starter isolated from the durable Markdown artifact", () => {
    const artifactPath = resolve(
      process.cwd(),
      "../../evals/c2_live_prep/mireward-prep/content/tiptap/north-gate-session-runbook.md",
    );
    const artifactMarkdown = readFileSync(artifactPath, "utf8").trim();
    const starterMarkdown = northGateSessionRunbookStarterMarkdown.trim();

    expect(starterMarkdown).not.toBe(artifactMarkdown);
    expect(starterMarkdown).toContain("# C2S23 North Gate Session Runbook");
    expect(starterMarkdown).toContain("## Hard boundaries");
    expect(starterMarkdown).toContain("[North Reach Gate](#dmb-ref:location:north-reach-gate)");
    expect(artifactMarkdown).toContain("# C2S23 Mireward Reach North Gate Runbook");
  });

  it("suggests north gate create payload without inventing document ids", () => {
    const payload = northGateRunbookCreateRequest();
    expect(payload.kind).toBe("runbook");
    expect(payload.target_relpath).toBe(NORTH_GATE_RUNBOOK_TARGET_RELPATH);
  });
});
