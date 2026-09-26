import { expect, test } from "@playwright/test";

const desktop = { width: 1280, height: 800 };
const narrow = { width: 390, height: 844 };

const cases = [
  { story: "object-sheet--rich-npc", viewport: desktop, snapshot: "object-rich-desktop.webp" },
  { story: "object-sheet--rich-npc", viewport: narrow, snapshot: "object-rich-narrow.webp" },
  { story: "object-sheet--faction", viewport: desktop, snapshot: "object-faction-desktop.webp" },
  { story: "object-sheet--faction", viewport: narrow, snapshot: "object-faction-narrow.webp" },
  { story: "object-sheet--relationship-heavy", viewport: desktop, snapshot: "object-relationships-desktop.webp" },
  { story: "object-sheet--relationship-heavy", viewport: narrow, snapshot: "object-relationships-narrow.webp" },
  { story: "visual-contract--tool-host-overlay", viewport: desktop, snapshot: "toolhost-overlay-desktop.webp" },
  { story: "visual-contract--tool-host-peek", viewport: desktop, snapshot: "toolhost-peek-desktop.webp" },
] as const;

test.describe("fixed Buddy visual contract", () => {
  for (const visualCase of cases) {
    test(visualCase.snapshot, async ({ page, request }) => {
      const metaResponse = await request.get("/meta.json");
      expect(metaResponse.ok()).toBeTruthy();
      const meta = (await metaResponse.json()) as { stories: Record<string, unknown> };
      expect(Object.hasOwn(meta.stories, visualCase.story)).toBeTruthy();

      await page.setViewportSize(visualCase.viewport);
      await page.goto(`/?story=${visualCase.story}&mode=preview`);
      await expect(page.locator("html[data-storyloaded]")).toBeVisible();
      await expect(page.locator("#ladle-root")).not.toBeEmpty();
      if (visualCase.story === "visual-contract--tool-host-peek") {
        await expect(page.locator('.app-peek-claim[data-peek-claim="tools"]:not([hidden])')).toBeVisible();
      }
      await expect(page).toHaveScreenshot(visualCase.snapshot);
    });
  }
});
