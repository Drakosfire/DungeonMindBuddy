import { describe, expect, it } from "vitest";

import { scopePrepCss } from "./scopePrepCss";

describe("scopePrepCss", () => {
  it("scopes html/body/:root and element rules under the Play host", () => {
    const scoped = scopePrepCss(
      `:root { --bg: #000; }
html, body { margin: 0; }
body.prep-embed .wrap { padding: 0; }
a { color: red; }
button.primary { color: blue; }
`,
    );
    expect(scoped).toContain(".play-surface__host { --bg: #000; }");
    expect(scoped).toContain(".play-surface__host { margin: 0; }");
    expect(scoped).toContain(".play-surface__host.prep-embed .wrap { padding: 0; }");
    expect(scoped).toContain(".play-surface__host a { color: red; }");
    expect(scoped).toContain(".play-surface__host button.primary { color: blue; }");
  });

  it("leaves markdown viewer selectors global", () => {
    const scoped = scopePrepCss(
      `#md-viewer { z-index: 40; }
body.md-viewer-open { overflow: hidden; }
`,
    );
    expect(scoped).toContain("#md-viewer { z-index: 40; }");
    expect(scoped).toContain("body.md-viewer-open { overflow: hidden; }");
    expect(scoped).not.toContain(".play-surface__host #md-viewer");
  });

  it("parks keyframes without rewriting them", () => {
    const scoped = scopePrepCss(
      `@keyframes fade { from { opacity: 0; } to { opacity: 1; } }
.card { opacity: 1; }
`,
    );
    expect(scoped).toContain("@keyframes fade { from { opacity: 0; } to { opacity: 1; } }");
    expect(scoped).toContain(".play-surface__host .card { opacity: 1; }");
  });
});
