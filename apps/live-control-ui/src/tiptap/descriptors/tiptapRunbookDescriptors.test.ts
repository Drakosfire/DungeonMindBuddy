import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import {
  DEFAULT_TIPTAP_RUNBOOK_DOCUMENT_ID,
  getTiptapRunbookDescriptor,
  northGateSessionRunbookStarterMarkdown,
  TIPTAP_RUNBOOK_DESCRIPTORS,
  tiptapRunbookStorageKey,
} from "./tiptapRunbookDescriptors";

describe("Tiptap runbook descriptors", () => {
  it("defaults to the North Gate session runbook", () => {
    expect(DEFAULT_TIPTAP_RUNBOOK_DOCUMENT_ID).toBe("north-gate-session-runbook");
    expect(getTiptapRunbookDescriptor().documentId).toBe("north-gate-session-runbook");
    expect(getTiptapRunbookDescriptor("bogus").documentId).toBe("north-gate-session-runbook");
  });

  it("keeps descriptor ids and write targets safe and isolated", () => {
    expect(TIPTAP_RUNBOOK_DESCRIPTORS).toHaveLength(2);
    for (const descriptor of TIPTAP_RUNBOOK_DESCRIPTORS) {
      expect(descriptor.documentId).toMatch(/^[a-z0-9]+(?:-[a-z0-9]+)*$/);
      expect(descriptor.targetRelpath).toMatch(/^evals\/c2_live_prep\/mireward-prep\/content\/tiptap\/[a-z0-9-]+\.md$/);
    }
    const keys = TIPTAP_RUNBOOK_DESCRIPTORS.map(tiptapRunbookStorageKey);
    expect(new Set(keys).size).toBe(keys.length);
  });

  it("keeps the North Gate reset starter aligned with the durable Markdown artifact", () => {
    const artifactPath = resolve(
      process.cwd(),
      "../../evals/c2_live_prep/mireward-prep/content/tiptap/north-gate-session-runbook.md",
    );
    const artifactMarkdown = readFileSync(artifactPath, "utf8").trim();

    expect(northGateSessionRunbookStarterMarkdown.trim()).toBe(artifactMarkdown);
  });
});
