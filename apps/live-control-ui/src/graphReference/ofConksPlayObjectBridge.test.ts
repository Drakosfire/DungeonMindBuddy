import { describe, expect, it } from "vitest";

import {
  hasOfConksPlayObjectBody,
  ofConksPlayObjectNodeIds,
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
    expect(body?.provenance.pdfHeading).toMatch(/Area 2/i);
  });

  it("surfaces Maglubiyet charges without Build", () => {
    const body = playObjectBodyForNodeId("item:maglubiyets-statue");
    expect(body?.rulesNow?.some((line) => /3 charges/i.test(line))).toBe(true);
    expect(body?.rulesNow?.some((line) => /fear/i.test(line) && /DC 15/i.test(line))).toBe(true);
    expect(body?.toolLinks?.some((link) => link.panel === "items")).toBe(true);
  });

  it("surfaces Shacks firefighting and celebration RULES", () => {
    const body = playObjectBodyForNodeId("location:the-shacks");
    expect(body?.rulesNow?.some((line) => /Firefighting/i.test(line) && /DC 12/i.test(line))).toBe(
      true,
    );
    expect(body?.rulesNow?.some((line) => /DC 10 Constitution/i.test(line))).toBe(true);
    expect(body?.connectedNow.some((chip) => chip.nodeId === "item:bellys-mouthwash")).toBe(true);
    expect(body?.toolLinks?.some((link) => link.panel === "roll")).toBe(true);
  });

  it("surfaces Marrow chamber arrival and resin RULES", () => {
    const body = playObjectBodyForNodeId("location:the-marrow");
    expect(body?.atTable).toMatch(/helix/i);
    expect(body?.atTable).toMatch(/green light/i);
    expect(body?.rulesNow?.some((line) => /200 gp/i.test(line))).toBe(true);
    expect(body?.rulesNow?.some((line) => /DC 10/i.test(line))).toBe(true);
  });

  it("bridges Belly’s Mouthwash prize item", () => {
    const body = playObjectBodyForNodeId("item:bellys-mouthwash");
    expect(body?.kind).toBe("item");
    expect(body?.rulesNow?.some((line) => /4 charges/i.test(line))).toBe(true);
    expect(body?.rulesNow?.some((line) => /heroism/i.test(line))).toBe(true);
    expect(hasOfConksPlayObjectBody("item:bellys-mouthwash")).toBe(true);
  });

  it("gives Nar full Sarni source prose and wandering-life outcome", () => {
    const body = playObjectBodyForNodeId("npc:nar-granitetooth");
    expect(body?.attitude).toMatch(/Sarni/i);
    const source = (body?.sourceBlocks ?? []).map((b) => b.text).join("\n");
    expect(source).toMatch(/slit Sarni/i);
    expect(source).toMatch(/Sharindlar/i);
    expect(source).toMatch(/wandering life/i);
    expect(body?.provenance.pdfHeading).toBe("Area 1: The Shacks");
  });

  it("requires provenance.pdfHeading and sourceBlocks on every play object body", () => {
    for (const nodeId of ofConksPlayObjectNodeIds()) {
      const body = playObjectBodyForNodeId(nodeId);
      expect(body?.provenance.pdfHeading?.trim(), nodeId).toBeTruthy();
      expect((body?.sourceBlocks?.length ?? 0) >= 1, nodeId).toBe(true);
    }
  });

  it("gives Shacks door-dump and Maglubiyet Appendix B source", () => {
    const shacks = playObjectBodyForNodeId("location:the-shacks");
    const shacksSource = (shacks?.sourceBlocks ?? []).map((b) => b.text).join("\n");
    expect(shacksSource).toMatch(/noggin-shaped nose/i);
    const maglubiyet = playObjectBodyForNodeId("item:maglubiyets-statue");
    const magSource = (maglubiyet?.sourceBlocks ?? []).map((b) => b.text).join("\n");
    expect(magSource).toMatch(/blood will not dry/i);
  });

  it("gives Marrow helix and resin harvest source", () => {
    const marrow = playObjectBodyForNodeId("location:the-marrow");
    const source = (marrow?.sourceBlocks ?? []).map((b) => b.text).join("\n");
    expect(source).toMatch(/helix/i);
    expect(source).toMatch(/200 gp/i);
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
