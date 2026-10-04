import { expect, test, type Page } from "@playwright/test";

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

async function readDockGeometry(page: Page) {
  return page.evaluate(() => {
    const rect = (selector: string) => {
      const element = document.querySelector<HTMLElement>(selector);
      if (!element) return null;
      const bounds = element.getBoundingClientRect();
      return {
        left: bounds.left,
        top: bounds.top,
        right: bounds.right,
        bottom: bounds.bottom,
        width: bounds.width,
        height: bounds.height,
      };
    };
    const workspace = document.querySelector<HTMLElement>("[data-testid='dock-responsive-canvas']");
    const layout = document.querySelector<HTMLElement>(".app-shell-layout");
    const drawer = document.querySelector<HTMLElement>("#app-edit-toolbox-drawer");
    const body = document.querySelector<HTMLElement>(".app-edit-toolbox-body");
    return {
      header: rect(".app-chrome-header"),
      nav: rect(".app-site-nav"),
      context: rect("[data-testid='surface-context-host']"),
      workspace: rect("[data-testid='dock-responsive-canvas']"),
      drawer: rect("#app-edit-toolbox-drawer"),
      toolBody: rect(".app-edit-toolbox-body"),
      documentWidth: document.documentElement.scrollWidth,
      layoutPaddingLeft: layout ? getComputedStyle(layout).paddingLeft : "missing",
      workspaceMarginLeft: workspace ? getComputedStyle(workspace).marginLeft : "missing",
      drawerBodyContained: Boolean(drawer && body && (() => {
        const host = drawer.getBoundingClientRect();
        const content = body.getBoundingClientRect();
        return content.left >= host.left && content.right <= host.right
          && content.top >= host.top && content.bottom <= host.bottom;
      })()),
    };
  });
}

test(
  "keeps Plan chrome stable while Edit docks on desktop and overlays on mobile",
  async ({ page, request }) => {
    const metaResponse = await request.get("/meta.json");
    expect(metaResponse.ok()).toBeTruthy();
    const meta = (await metaResponse.json()) as { stories: Record<string, unknown> };
    for (const story of mobileDockStories) {
      expect(Object.hasOwn(meta.stories, story)).toBeTruthy();

      await page.setViewportSize(narrow);
      await page.goto(`/?story=${story}&mode=preview`);
      await expect(page.locator("html[data-storyloaded]")).toBeVisible();
      const hasPlanSurface = story === "visual-contract--edit-host-dock-responsive";
      if (hasPlanSurface) {
        await expect(page.getByTestId("surface-context-host")).toBeVisible();
      } else {
        await expect(page.getByTestId("surface-context-host")).toHaveCount(0);
      }
      const drawer = page.locator("#app-edit-toolbox-drawer");
      const backdrop = page.locator(".app-edit-toolbox-backdrop");
      const canvas = page.getByTestId("dock-responsive-canvas");
      await expect(drawer).toBeVisible();
      await expect(backdrop).toBeVisible();

      const narrowOpen = await readDockGeometry(page);
      expect(narrowOpen.drawer?.width).toBeGreaterThanOrEqual(360);
      expect(narrowOpen.drawer?.left).toBeGreaterThanOrEqual(0);
      expect(narrowOpen.drawer?.right).toBeLessThanOrEqual(narrow.width);
      expect(narrowOpen.drawer?.bottom).toBeLessThanOrEqual(narrow.height);
      expect(narrowOpen.drawer?.top).toBeGreaterThanOrEqual(narrowOpen.header?.bottom ?? 0);
      expect(narrowOpen.drawer?.top).toBeLessThanOrEqual((narrowOpen.header?.bottom ?? 0) + 1);
      expect(narrowOpen.workspace?.top).toBeGreaterThanOrEqual(narrowOpen.header?.bottom ?? 0);
      expect(narrowOpen.layoutPaddingLeft).toBe("0px");
      expect(narrowOpen.workspaceMarginLeft).toBe("0px");
      expect(narrowOpen.workspace?.width).toBeGreaterThan(narrow.width * 0.75);
      expect(narrowOpen.documentWidth).toBeLessThanOrEqual(narrow.width);
      expect(narrowOpen.drawerBodyContained).toBe(true);
      if (story.endsWith("other-surface")) {
        await expect(page.locator(".plan-surface-root")).toHaveCount(0);
      }

      await page.getByRole("button", { name: "Close Edit" }).click();
      await expect(drawer).toBeHidden();
      await expect(backdrop).toHaveAttribute("hidden", "");
      await expect(backdrop).toHaveCSS("display", "none");
      const narrowClosed = await readDockGeometry(page);
      expect(narrowClosed.documentWidth).toBeLessThanOrEqual(narrow.width);
      expect(narrowOpen.nav).toEqual(narrowClosed.nav);
      if (hasPlanSurface) expect(narrowOpen.context).toEqual(narrowClosed.context);
      expect(narrowClosed.workspace?.left).toBe(narrowOpen.workspace?.left);
      expect(narrowClosed.workspace?.width).toBe(narrowOpen.workspace?.width);

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
    await expect(page.getByTestId("surface-context-host")).toBeVisible();
    const drawer = page.locator("#app-edit-toolbox-drawer");
    await expect(drawer).toBeVisible();
    const desktopOpen = await readDockGeometry(page);
    expect(desktopOpen.drawer?.width).toBe(380);
    expect(desktopOpen.drawer?.left).toBe(0);
    expect(desktopOpen.drawer?.right).toBe(380);
    expect(desktopOpen.drawer?.bottom).toBe(desktop.height);
    expect(desktopOpen.drawer?.top).toBeGreaterThanOrEqual(desktopOpen.header?.bottom ?? 0);
    expect(desktopOpen.drawer?.top).toBeLessThanOrEqual((desktopOpen.header?.bottom ?? 0) + 1);
    expect(desktopOpen.workspace?.top).toBeGreaterThanOrEqual(desktopOpen.header?.bottom ?? 0);
    expect(desktopOpen.layoutPaddingLeft).toBe("0px");
    expect(desktopOpen.workspaceMarginLeft).toBe("380px");
    expect(desktopOpen.workspace?.width).toBeGreaterThan(800);
    expect(desktopOpen.documentWidth).toBeLessThanOrEqual(desktop.width);
    expect(desktopOpen.drawerBodyContained).toBe(true);

    await page.getByRole("button", { name: "Close Edit" }).click();
    await expect(drawer).toBeHidden();
    const desktopClosed = await readDockGeometry(page);
    expect(desktopClosed.documentWidth).toBeLessThanOrEqual(desktop.width);
    expect(desktopOpen.nav).toEqual(desktopClosed.nav);
    expect(desktopOpen.context).toEqual(desktopClosed.context);
    expect(desktopOpen.workspace?.left).toBe(desktopClosed.workspace?.left! + 380);
    expect(desktopOpen.workspace?.width).toBe(desktopClosed.workspace?.width! - 380);
    await page.getByRole("button", { name: "Edit" }).click();
    await expect(drawer).toBeVisible();
    await page.getByRole("button", { name: "Close Edit" }).click();
    await expect(drawer).toBeHidden();
  },
);
