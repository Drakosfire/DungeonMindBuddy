import { describe, expect, it } from "vitest";

import { extractPrepMarkup } from "./playPrepHost";

describe("extractPrepMarkup", () => {
  it("keeps wrap content and drops scripts", () => {
    const { markup, bodyClass } = extractPrepMarkup(`<!doctype html>
<html><body class="statblocks-page">
  <div class="wrap"><h1>Statblocks</h1><div id="statblock-corpus-index"></div></div>
  <script>alert(1)</script>
</body></html>`);
    expect(bodyClass).toBe("statblocks-page");
    expect(markup).toContain('class="wrap"');
    expect(markup).toContain("Statblocks");
    expect(markup).not.toContain("<script");
  });

  it("includes combat floating controls with the wrap", () => {
    const { markup } = extractPrepMarkup(`<!doctype html>
<html><body>
  <div class="wrap combat-wrap" id="combat-tracker"><h1>Combat</h1></div>
  <div class="combat-floating-controls"><button type="button">Next</button></div>
  <script src="assets/prep.js"></script>
</body></html>`);
    expect(markup).toContain("combat-wrap");
    expect(markup).toContain("combat-floating-controls");
    expect(markup).not.toContain("<script");
  });
});
