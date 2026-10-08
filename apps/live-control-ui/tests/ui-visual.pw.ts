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
    const compact = viewport.width <= 960;
    const beatToggle = page.getByTestId(compact ? "play-compact-outline-toggle" : "play-beat-context-toggle");
    const glanceToggle = page.getByTestId(compact ? "play-compact-outcomes-toggle" : "play-at-a-glance-toggle");
    if (compact) {
      await expect(beatToggle).toBeVisible();
      await expect(glanceToggle).toBeVisible();
      await expect(beatToggle).toHaveAttribute("aria-expanded", "false");
      await expect(glanceToggle).toHaveAttribute("aria-expanded", "false");
      await expect(beat).toBeHidden();
      await expect(glance).toBeHidden();
    } else {
      await expect(beat).toBeVisible();
      await expect(glance).toBeVisible();
    }

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
    if (compact) {
      const sceneTop = geometry.centralTop;
      await beatToggle.click();
      await expect(beat).toBeVisible();
      await expect(glance).toBeHidden();
      const [sceneAfterOpen, beatAfterOpen] = await Promise.all([
        central.evaluate((element) => element.getBoundingClientRect().top),
        beat.evaluate((element) => element.getBoundingClientRect().top),
      ]);
      expect(Math.abs(sceneAfterOpen - sceneTop)).toBeLessThan(1);
      expect(Math.abs(beatAfterOpen - sceneAfterOpen)).toBeLessThan(1);
      await beatToggle.click();
      await expect(beat).toBeHidden();
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
      await expect(beatToggle).toHaveAttribute("aria-expanded", "false");
      await beatToggle.focus();
      await page.keyboard.press("Enter");
      await expect(beatToggle).toHaveAttribute("aria-expanded", "true");
      await page.keyboard.press("Enter");
      await expect(beatToggle).toHaveAttribute("aria-expanded", "false");
    }
  }
});

test("keeps the full App Play route readable and keyboard-operable at narrow widths", async ({ page }) => {
  const story = "play-current-moment-cockpit--app-shell-responsive-cockpit";
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
    const scene = page.getByTestId("play-workspace-current");
    const sceneTitle = page.getByRole("heading", { name: "North Gate" });
    const compact = viewport.width <= 960;
    const beatToggle = page.getByTestId(compact ? "play-compact-outline-toggle" : "play-beat-context-toggle");
    const note = page.getByRole("textbox", { name: "Scene note" });
    await expect(page.getByTestId("play-surface-ready")).toBeVisible();
    await expect(page.getByTestId("play-start-new-run")).toHaveText("Start New Run");
    await expect(page.getByRole("navigation", { name: "Command board navigation" })).toBeVisible();
    await expect(scene).toBeVisible();
    await expect(sceneTitle).toBeVisible();
    await expect(note).toBeVisible();

    if (viewport.width === desktop.width || viewport.width === narrow.width) {
      const screenshot = viewport.width === desktop.width
        ? "play-cockpit-app-shell-desktop.png"
        : "play-cockpit-app-shell-narrow.png";
      await expect(page).toHaveScreenshot(screenshot);
    }

    const geometry = await page.evaluate(() => {
      const bounds = (selector: string) => {
        const element = document.querySelector<HTMLElement>(selector);
        if (!element) return null;
        const rect = element.getBoundingClientRect();
        return { top: rect.top, left: rect.left, right: rect.right, width: rect.width, bottom: rect.bottom };
      };
      const title = document.querySelector<HTMLElement>("#play-workspace-heading")?.getBoundingClientRect();
      const scene = bounds("[data-testid='play-central-workspace']");
      const beat = bounds("[data-testid='play-beat-context']");
      const glance = bounds("[data-testid='play-at-a-glance']");
      const appWrap = bounds(".app-wrap");
      const cockpit = document.querySelector<HTMLElement>("[data-testid='play-cockpit-shell']");
      const cockpitColumnCount = cockpit
        ? getComputedStyle(cockpit).gridTemplateColumns.split(" ").filter(Boolean).length
        : 0;
      const body = document.querySelector<HTMLElement>(".play-scene-board-body");
      return {
        scene,
        beat,
        glance,
        appWrap,
        cockpitColumnCount,
        titleVisibleInFirstViewport: Boolean(title && title.top >= 0 && title.bottom <= window.innerHeight),
        bodyFontSize: body ? Number.parseFloat(getComputedStyle(body).fontSize) : 0,
        documentWidth: document.documentElement.scrollWidth,
      };
    });
    expect(geometry.scene).not.toBeNull();
    expect(geometry.beat).not.toBeNull();
    expect(geometry.glance).not.toBeNull();
    expect(geometry.appWrap).not.toBeNull();
    expect(geometry.appWrap!.width).toBeGreaterThan(viewport.width * (viewport.width > 960 ? 0.9 : 0.8));
    if (viewport.width > 960) {
      expect(geometry.cockpitColumnCount).toBe(3);
    } else {
      expect(geometry.cockpitColumnCount).toBe(1);
    }
    expect(geometry.scene!.left).toBeGreaterThanOrEqual(0);
    expect(geometry.scene!.right).toBeLessThanOrEqual(viewport.width);
    expect(geometry.scene!.width).toBeGreaterThan(viewport.width * (viewport.width <= 390 ? 0.7 : 0.5));
    expect(geometry.documentWidth).toBeLessThanOrEqual(viewport.width);
    expect(geometry.titleVisibleInFirstViewport).toBe(true);
    expect(geometry.bodyFontSize).toBeGreaterThanOrEqual(14);
    if (compact) {
      await expect(page.getByRole("navigation", { name: "Play panels" })).toBeVisible();
      await expect(page.getByTestId("play-beat-context")).toBeHidden();
      await expect(page.getByTestId("play-at-a-glance")).toBeHidden();
    }

    if (viewport.width === 320) {
      await page.getByTestId("play-start-new-run").focus();
      await page.keyboard.press("Tab");
      const firstControlAfterRunAction = await page.evaluate(() => (
        document.activeElement?.getAttribute("data-testid") ?? null
      ));
      expect(firstControlAfterRunAction).not.toBe("play-beat-context-toggle");

      await beatToggle.focus();
      await expect(beatToggle).toHaveAttribute("aria-expanded", "false");
      await page.keyboard.press("Enter");
      await expect(beatToggle).toHaveAttribute("aria-expanded", "true");
      await page.keyboard.press("Enter");
      await expect(beatToggle).toHaveAttribute("aria-expanded", "false");
    }

    await page.waitForFunction(() => (
      (window as Window & { __dmbPlayShellFixtureRequests?: Array<{ method: string; path: string }> })
        .__dmbPlayShellFixtureRequests?.some(({ method }) => method !== "GET")
    ));
    const writes = await page.evaluate(() => (
      (window as Window & { __dmbPlayShellFixtureRequests?: Array<{ method: string; path: string }> })
        .__dmbPlayShellFixtureRequests?.filter(({ method }) => method !== "GET") ?? []
    ));
    expect(writes.length).toBeGreaterThan(0);
    expect(writes.every(({ method, path }) => (
      method === "PUT" && path === "/api/live/world-play-runs/v2/active"
    ))).toBe(true);
  }
});

test("collapses supporting panels when the Play canvas is narrow inside a wide viewport", async ({ page }) => {
  await page.setViewportSize(desktop);
  await page.goto("/?story=play-current-moment-cockpit--app-shell-responsive-cockpit&mode=preview");
  await expect(page.locator("html[data-storyloaded]")).toBeVisible();

  const cockpit = page.getByTestId("play-current-moment-cockpit");
  const shell = page.getByTestId("play-cockpit-shell");
  const outlineToggle = page.getByTestId("play-beat-context-toggle");
  const outcomesToggle = page.getByTestId("play-at-a-glance-toggle");
  const compactOutlineToggle = page.getByTestId("play-compact-outline-toggle");
  const compactOutcomesToggle = page.getByTestId("play-compact-outcomes-toggle");
  await expect(outlineToggle).toHaveAttribute("aria-expanded", "true");
  await expect(outcomesToggle).toHaveAttribute("aria-expanded", "true");

  await cockpit.evaluate((element) => {
    element.style.width = "800px";
    element.style.marginInline = "auto";
  });
  await expect(compactOutlineToggle).toBeVisible();
  await expect(compactOutcomesToggle).toBeVisible();
  await expect(compactOutlineToggle).toHaveAttribute("aria-expanded", "false");
  await expect(compactOutcomesToggle).toHaveAttribute("aria-expanded", "false");
  await expect.poll(() => shell.evaluate((element) => (
    getComputedStyle(element).gridTemplateColumns.split(" ").filter(Boolean).length
  ))).toBe(1);

  await compactOutlineToggle.click();
  await expect(compactOutlineToggle).toHaveAttribute("aria-expanded", "true");
  await cockpit.evaluate((element) => { element.style.width = "760px"; });
  await expect(compactOutlineToggle).toHaveAttribute("aria-expanded", "true");

  await cockpit.evaluate((element) => { element.style.width = "1000px"; });
  await expect(outlineToggle).toHaveAttribute("aria-expanded", "true");
  await expect(outcomesToggle).toHaveAttribute("aria-expanded", "true");
  await expect.poll(() => shell.evaluate((element) => (
    getComputedStyle(element).gridTemplateColumns.split(" ").filter(Boolean).length
  ))).toBe(3);
});

test("keeps compact scene navigation and the Run record directly reachable", async ({ page }) => {
  await page.setViewportSize({ width: 768, height: 900 });
  await page.goto("/?story=play-current-moment-cockpit--app-shell-responsive-cockpit&mode=preview");
  await expect(page.locator("html[data-storyloaded]")).toBeVisible();

  const compactOutline = page.getByTestId("play-compact-outline-toggle");
  const compactOutcomes = page.getByTestId("play-compact-outcomes-toggle");
  const scene = page.getByTestId("play-central-workspace");
  const outline = page.getByTestId("play-beat-context");
  const outcomes = page.getByTestId("play-at-a-glance");
  await expect(compactOutline).toBeVisible();
  await expect(compactOutcomes).toBeVisible();
  await expect(compactOutline).toHaveAttribute("aria-expanded", "false");
  await expect(compactOutcomes).toHaveAttribute("aria-expanded", "false");

  const sceneTopBefore = await scene.evaluate((element) => element.getBoundingClientRect().top);
  await compactOutline.click();
  await expect(outline).toBeVisible();
  await expect(outcomes).toBeHidden();
  await expect(compactOutline).toHaveAttribute("aria-expanded", "true");
  const positions = await Promise.all([
    scene.evaluate((element) => element.getBoundingClientRect().top),
    outline.evaluate((element) => element.getBoundingClientRect().top),
  ]);
  expect(Math.abs(positions[0] - sceneTopBefore)).toBeLessThan(1);
  expect(Math.abs(positions[1] - positions[0])).toBeLessThan(1);

  await compactOutcomes.click();
  await expect(outline).toBeHidden();
  await expect(outcomes).toBeVisible();
  await expect(compactOutline).toHaveAttribute("aria-expanded", "false");
  await expect(compactOutcomes).toHaveAttribute("aria-expanded", "true");
  await compactOutcomes.click();
  await expect(outcomes).toBeHidden();
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
