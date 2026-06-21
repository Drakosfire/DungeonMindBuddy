import { describe, expect, it } from "vitest";

import { chipToSourceAnchor, resolutionToSourceUnit } from "./derivedViewsAdapter";
import type { ReferenceResolution } from "../reference/referenceResolver";

describe("derivedViewsAdapter", () => {
  it("maps chip attrs to source anchor without declaring taxonomy", () => {
    const anchor = chipToSourceAnchor({
      kind: "ref",
      refType: "npc",
      refId: "lysandro-ironveil",
      label: "Lysandro Ironveil",
    });
    expect(anchor.href).toBe("#dmb-ref:npc:lysandro-ironveil");
    expect(anchor.refId).toBe("lysandro-ironveil");
  });

  it("maps resolved index item to source unit", () => {
    const resolution: ReferenceResolution = {
      status: "resolved",
      ref: {
        kind: "ref",
        refType: "npc",
        refId: "lysandro-ironveil",
        label: "Lysandro Ironveil",
      },
      message: "Resolved from live npc index.",
      sourcePath: "corpus/npcs/lysandro/README.md",
      item: { title: "Lysandro Ironveil", table_note: "Gate contact." },
    };
    const unit = resolutionToSourceUnit(resolution);
    expect(unit.sourcePath).toBe("corpus/npcs/lysandro/README.md");
    expect(unit.fields.title).toBe("Lysandro Ironveil");
    expect(unit.fields.table_note).toBe("Gate contact.");
  });
});
