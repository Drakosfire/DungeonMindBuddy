import { describe, expect, it } from "vitest";

import {
  canResolveOfConksLocalGraphReference,
  tryOfConksLocalGraphReferenceResolution,
} from "./buildPlayLocalGraphReference";

describe("tryOfConksLocalGraphReferenceResolution", () => {
  it("resolves Of Conks play objects and threats only", () => {
    expect(canResolveOfConksLocalGraphReference("location:the-shacks")).toBe(true);
    expect(canResolveOfConksLocalGraphReference("threat:grotesque-tree")).toBe(true);
    expect(canResolveOfConksLocalGraphReference("threat:tripod-null-calf")).toBe(false);
    expect(tryOfConksLocalGraphReferenceResolution("location:the-shacks", "The Shacks")?.graphNodeId)
      .toBe("location:the-shacks");
    expect(tryOfConksLocalGraphReferenceResolution("npc:stranger")).toBeNull();
  });
});
