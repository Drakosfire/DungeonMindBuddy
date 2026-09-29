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

const mobileDockStories = [
  "visual-contract--edit-host-dock-responsive",
  "visual-contract--edit-host-dock-responsive-other-surface",
] as const;

test(
  "opens and closes the docked EditHost on mobile surfaces and preserves the desktop split",
  async ({ page, request }) => {
    const metaResponse = await request.get("/meta.json");
    expect(metaResponse.ok()).toBeTruthy();
    const meta = (await metaResponse.json()) as { stories: Record<string, unknown> };
    for (const story of mobileDockStories) {
      expect(Object.hasOwn(meta.stories, story)).toBeTruthy();

      await page.setViewportSize(narrow);
      await page.goto(`/?story=${story}&mode=preview`);
      await expect(page.locator("html[data-storyloaded]")).toBeVisible();
      const drawer = page.locator("#app-edit-toolbox-drawer");
      const backdrop = page.locator(".app-edit-toolbox-backdrop");
      const canvas = page.getByTestId("dock-responsive-canvas");
      await expect(drawer).toBeVisible();
      await expect(backdrop).toBeVisible();

      const narrowLayout = await page.evaluate(() => {
        const drawerElement = document.querySelector<HTMLElement>("#app-edit-toolbox-drawer");
        const bodyElement = document.querySelector<HTMLElement>(".app-edit-toolbox-body");
        const layoutElement = document.querySelector<HTMLElement>(".app-shell-layout");
        const canvasElement = document.querySelector<HTMLElement>(
          '[data-testid="dock-responsive-canvas"]',
        );
        return {
          drawerWidth: drawerElement?.getBoundingClientRect().width ?? 0,
          bodyWidth: bodyElement?.clientWidth ?? 0,
          leftPadding: layoutElement ? getComputedStyle(layoutElement).paddingLeft : "missing",
          canvasWidth: canvasElement?.getBoundingClientRect().width ?? 0,
          documentWidth: document.documentElement.scrollWidth,
        };
      });
      expect(narrowLayout.drawerWidth).toBeGreaterThanOrEqual(360);
      expect(narrowLayout.drawerWidth).toBeLessThanOrEqual(narrow.width);
      expect(narrowLayout.bodyWidth).toBeGreaterThan(300);
      expect(narrowLayout.leftPadding).toBe("0px");
      expect(narrowLayout.canvasWidth).toBeGreaterThan(narrow.width * 0.75);
      expect(narrowLayout.documentWidth).toBeLessThanOrEqual(narrow.width);
      if (story.endsWith("other-surface")) {
        await expect(page.locator(".plan-surface-root")).toHaveCount(0);
      }

      await page.getByRole("button", { name: "Close Edit" }).click();
      await expect(drawer).toBeHidden();
      await expect(backdrop).toHaveAttribute("hidden", "");
      await expect(backdrop).toHaveCSS("display", "none");

      await page.getByRole("button", { name: "Edit" }).click();
      await expect(drawer).toBeVisible();
      await page.getByRole("button", { name: "Close Edit" }).click();
      await expect(drawer).toBeHidden();
      await expect(backdrop).toHaveCSS("display", "none");
      expect(await canvas.evaluate((element) => element.getBoundingClientRect().width))
        .toBeGreaterThan(narrow.width * 0.75);
    }

    await page.setViewportSize(desktop);
    await page.goto("/?story=visual-contract--edit-host-dock-responsive&mode=preview");
    await expect(page.locator("html[data-storyloaded]")).toBeVisible();
    const drawer = page.locator("#app-edit-toolbox-drawer");
    await expect(drawer).toBeVisible();
    const desktopLayout = await page.evaluate(() => {
      const drawerElement = document.querySelector<HTMLElement>("#app-edit-toolbox-drawer");
      const layoutElement = document.querySelector<HTMLElement>(".app-shell-layout");
      const canvasElement = document.querySelector<HTMLElement>(
        '[data-testid="dock-responsive-canvas"]',
      );
      return {
        drawerWidth: drawerElement?.getBoundingClientRect().width ?? 0,
        leftPadding: layoutElement ? getComputedStyle(layoutElement).paddingLeft : "missing",
        canvasWidth: canvasElement?.getBoundingClientRect().width ?? 0,
      };
    });
    expect(desktopLayout.drawerWidth).toBe(380);
    expect(desktopLayout.leftPadding).toBe("380px");
    expect(desktopLayout.canvasWidth).toBeGreaterThan(800);

    await page.getByRole("button", { name: "Close Edit" }).click();
    await expect(drawer).toBeHidden();
    await page.getByRole("button", { name: "Edit" }).click();
    await expect(drawer).toBeVisible();
    await page.getByRole("button", { name: "Close Edit" }).click();
    await expect(drawer).toBeHidden();
  },
);
