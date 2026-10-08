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

test("keeps the active Play scene primary across available widths", async ({ page, request }) => {
  const metaResponse = await request.get("/meta.json");
  expect(metaResponse.ok()).toBeTruthy();
  const meta = (await metaResponse.json()) as { stories: Record<string, unknown> };
  const story = "play-current-moment-cockpit--responsive-cockpit";
  expect(Object.hasOwn(meta.stories, story)).toBeTruthy();

  const viewports = [
    desktop,
    { width: 960, height: 844 },
    { width: 768, height: 844 },
    narrow,
    { width: 320, height: 844 },
  ];

  for (const viewport of viewports) {
    await page.setViewportSize(viewport);
    await page.goto(`/?story=${story}&mode=preview`);
    await expect(page.locator("html[data-storyloaded]")).toBeVisible();
    const central = page.getByTestId("play-central-workspace");
    const beat = page.getByTestId("play-beat-context");
    const glance = page.getByTestId("play-at-a-glance");
    await expect(central).toBeVisible();
    await expect(beat).toBeVisible();
    await expect(glance).toBeVisible();

    const geometry = await page.evaluate(() => {
      const top = (selector: string) => {
        const element = document.querySelector<HTMLElement>(selector);
        return element?.getBoundingClientRect().top ?? Number.NaN;
      };
      const scene = document.querySelector<HTMLElement>("[data-testid='play-central-workspace']")!;
      const bounds = scene.getBoundingClientRect();
      const title = document.querySelector<HTMLElement>("#play-workspace-heading")!;
      const titleBounds = title.getBoundingClientRect();
      return {
        centralTop: bounds.top,
        beatTop: top("[data-testid='play-beat-context']"),
        glanceTop: top("[data-testid='play-at-a-glance']"),
        sceneLeft: bounds.left,
        sceneRight: bounds.right,
        centralWithinViewport: bounds.top < window.innerHeight,
        sceneTitleVisible: titleBounds.top >= 0 && titleBounds.bottom <= window.innerHeight,
        documentWidth: document.documentElement.scrollWidth,
      };
    });
    expect(geometry.centralWithinViewport).toBe(true);
    expect(geometry.sceneTitleVisible).toBe(true);
    expect(geometry.documentWidth).toBeLessThanOrEqual(viewport.width);
    expect(geometry.sceneLeft).toBeGreaterThanOrEqual(0);
    expect(geometry.sceneRight).toBeLessThanOrEqual(viewport.width);
    if (viewport.width <= 960) {
      expect(geometry.centralTop).toBeLessThan(geometry.beatTop);
      expect(geometry.centralTop).toBeLessThan(geometry.glanceTop);
    } else {
      expect(geometry.centralTop).toBeLessThanOrEqual(geometry.beatTop);
    }

    if (viewport.width === 390 || viewport.width === desktop.width) {
      const screenshot = viewport.width === 390
        ? "play-cockpit-narrow.png"
        : "play-cockpit-desktop.png";
      await expect(page).toHaveScreenshot(screenshot);
    }

    if (viewport.width === 320) {
      const beatToggle = page.getByTestId("play-beat-context-toggle");
      await beatToggle.focus();
      await page.keyboard.press("Enter");
      await expect(beatToggle).toHaveAttribute("aria-expanded", "false");
      await page.keyboard.press("Enter");
      await expect(beatToggle).toHaveAttribute("aria-expanded", "true");
    }
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
