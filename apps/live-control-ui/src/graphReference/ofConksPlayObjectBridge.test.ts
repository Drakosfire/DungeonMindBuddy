import { describe, expect, it } from "vitest";

import {
  hasOfConksPlayObjectBody,
  playObjectBodyForNodeId,
} from "./ofConksPlayObjectBridge";

describe("ofConksPlayObjectBridge", () => {
  it("returns Morwin play body with Saladin connected", () => {
    const body = playObjectBodyForNodeId("npc:morwin-blackwell");
    expect(body).not.toBeNull();
    expect(body?.kind).toBe("npc");
    expect(body?.atTable).toMatch(/eyes and ears/i);
    expect(body?.attitude).toMatch(/Saladin/i);
    expect(body?.offersHooks?.some((line) => /gem/i.test(line))).toBe(true);
    expect(body?.connectedNow.some((chip) => chip.nodeId === "npc:saladin")).toBe(true);
  });

  it("resolves packet locations and items", () => {
    expect(playObjectBodyForNodeId("location:the-shacks")?.kind).toBe("location");
    expect(playObjectBodyForNodeId("item:maglubiyets-statue")?.kind).toBe("item");
    expect(hasOfConksPlayObjectBody("faction:baldurs-gate-mages-guild")).toBe(true);
  });

  it("returns null for unknown nodes", () => {
    expect(playObjectBodyForNodeId("npc:not-in-packet")).toBeNull();
    expect(hasOfConksPlayObjectBody("location-inn")).toBe(false);
  });
});
