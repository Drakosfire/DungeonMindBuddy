const { chromium } = require(process.env.DMB_BENCHMARK_PLAYWRIGHT);
const { writeFileSync } = require("node:fs");

async function run() {
  const origin = process.env.DMB_BENCHMARK_BROWSER_ORIGIN;
  const browser = await chromium.launch({
    executablePath: process.env.DMB_BENCHMARK_CHROMIUM, headless: true, args: ["--no-sandbox"],
  });
  try {
    const context = await browser.newContext({ serviceWorkers: "block" });
    await context.route("**/*", route => {
      if (new URL(route.request().url()).origin !== origin) return route.abort();
      return route.continue({ headers: { ...route.request().headers(),
        authorization: "Bearer " + process.env.DMB_BENCHMARK_BROWSER_TOKEN } });
    });
    const page = await context.newPage();
    const apiFailures = [];
    const turnNetworkFailures = [];
    page.on("requestfailed", request => {
      if (new URL(request.url()).pathname === "/api/live/agent/turn") {
        turnNetworkFailures.push(request.failure()?.errorText ?? "unknown");
      }
    });
    page.on("response", response => {
      const pathname = new URL(response.url()).pathname;
      if (pathname.startsWith("/api/") && response.status() >= 400) {
        apiFailures.push({ pathname, status: response.status() });
      }
    });
    const documentId = process.env.DMB_BENCHMARK_DOCUMENT_ID;
    const build = process.env.DMB_BENCHMARK_SURFACE === "build";
    await page.goto(origin + (build ? "/build?world=" : "/plan?world=") +
      encodeURIComponent(process.env.DMB_BENCHMARK_WORLD) + "&documentId=" + encodeURIComponent(documentId));
    const composer = build ? page.getByLabel("Message DungeonBuddy") :
      page.getByPlaceholder("Ask Buddy, or tell it what to change…");
    if (!(await composer.isVisible())) {
      const conversation = page.locator(build ? ".conversation-dock__launcher" : ".plan-conversation-dock__launcher").getByRole("button");
      await conversation.click({ timeout: 15000 });
    }
    await composer.waitFor({ timeout: 20000 });
    await composer.fill(process.env.DMB_BENCHMARK_QUESTION);
    if (build) {
      const selected = process.env.DMB_BENCHMARK_SELECTION;
      if (!selected || !selected.trim()) throw new Error("Build fixture needs selected text");
      const editor = page.locator(".build-surface-shell .ProseMirror[contenteditable=true]");
      if (await editor.count() !== 1) throw new Error("Build fixture needs one editable editor");
      await editor.focus();
      await editor.evaluate((root, text) => {
        const matches = [];
        const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
        while (walker.nextNode()) {
          const node = walker.currentNode;
          let at = node.data.indexOf(text);
          while (at !== -1) { matches.push([node, at]); at = node.data.indexOf(text, at + 1); }
        }
        if (matches.length !== 1) throw new Error("Selected text must occur exactly once in one editor text node");
        const [node, at] = matches[0], range = document.createRange(), selection = window.getSelection();
        range.setStart(node, at); range.setEnd(node, at + text.length);
        selection.removeAllRanges(); selection.addRange(range);
        document.dispatchEvent(new Event("selectionchange"));
        if (selection.toString() !== text) throw new Error("Browser selection did not match fixture");
      }, selected);
    }
    const send = page.getByRole("button", { name: build ? /^(Send message|Propose edit)$/ : "Send message", exact: !build });
    await send.waitFor({ state: "visible" });
    if (process.env.DMB_BENCHMARK_PANE_SETTLED === "1") {
      await page.waitForLoadState("networkidle", { timeout: 30000 });
    }
    const calibrate = () => page.evaluate(async () => {
      const bounds = [];
      for (let i = 0; i < 20; i += 1) {
        const start = performance.now();
        const value = Number(await (await fetch("/__benchmark/clock", { cache: "no-store" })).text());
        const end = performance.now();
        bounds.push([value - end, value - start]);
      }
      return bounds;
    });
    const before = await calibrate();
    await send.evaluate(button => {
      button.addEventListener("click", () => performance.mark("benchmark-browser-send"), { once: true, capture: true });
    });
    const response = page.waitForResponse(result =>
      new URL(result.url()).pathname === "/api/live/agent/turn" && result.request().method() === "POST",
    { timeout: 60000 });
    response.catch(() => {});
    try {
      await send.click({ timeout: 12000 });
    } catch (error) {
      const alerts = await page.getByRole("alert").allTextContents();
      writeFileSync(process.env.DMB_BENCHMARK_BROWSER_RESULT, JSON.stringify({
        alerts, apiFailures, composerHasQuestion: await composer.inputValue() === process.env.DMB_BENCHMARK_QUESTION,
      }, null, 2));
      throw error;
    }
    const delivered = await response;
    if (process.env.DMB_BENCHMARK_LIVE_BUILD === "1") {
      // Keep the page alive while its ordinary client consumes the terminal event.
      await page.waitForFunction(async () => {
        const response = await fetch("/__benchmark/build-response-retained");
        return (await response.json()).retained === true;
      }, undefined, { timeout: 75000, polling: 250 });
    }
    const after = await calibrate();
    const browserMarks = await page.evaluate(() => {
      const click = performance.getEntriesByName("benchmark-browser-send").at(-1)?.startTime;
      const resources = performance.getEntriesByType("resource");
      const request = resources.filter(entry => new URL(entry.name).pathname === "/api/live/agent/turn")
        .map(entry => entry.startTime).at(-1);
      const preflight = resources.filter(entry => entry.startTime >= click && entry.startTime < request)
        .map(entry => ({
          phase: new URL(entry.name).pathname.endsWith("/committed-revision") ? "committed_plan_revision" : "other_resource",
          start: entry.startTime, requestStart: entry.requestStart,
          responseStart: entry.responseStart, end: entry.responseEnd,
        }));
      return { click, request, preflight };
    });
    let confirmation;
    if (process.env.DMB_BENCHMARK_CONFIRM_SAVE === "1") {
      const review = page.getByRole("region", { name: "Suggestion review", exact: true });
      await review.waitFor({ timeout: 15000 });
      const beforeSave = await page.evaluate(async id => {
        const response = await fetch("/api/live/workspace-documents/" + encodeURIComponent(id) + "/snapshot?view=committed");
        return { status: response.status, body: await response.json() };
      }, documentId);
      if (beforeSave.status !== 200) throw new Error("Pre-confirmation committed page could not be read");
      const expectedPath = /^\/api\/live\/agent\/worlds\/[^/]+\/build-proposals\/[^/]+\/review$/;
      const confirmed = page.waitForResponse(result => {
        const request = result.request();
        return request.method() === "POST" && expectedPath.test(new URL(result.url()).pathname)
          && request.postDataJSON()?.operation === "confirm";
      }, { timeout: 20000 });
      confirmed.catch(() => {});
      await review.getByRole("button", { name: "Save", exact: true }).click();
      const receipt = await confirmed;
      confirmation = { beforeSave, request: receipt.request().postDataJSON(),
        path: new URL(receipt.url()).pathname, status: receipt.status(), body: await receipt.json() };
    }
    writeFileSync(process.env.DMB_BENCHMARK_BROWSER_RESULT, JSON.stringify({
      before, after, browserMarks, confirmation, status: delivered.status(), chromiumVersion: browser.version(),
      playwrightVersion: require(require("node:path").join(process.env.DMB_BENCHMARK_PLAYWRIGHT, "package.json")).version,
      request: delivered.request().postDataJSON(), turnNetworkFailures,
    }, null, 2));
  } finally {
    await browser.close();
  }
}

run().catch(error => {
  console.error(error.stack ?? error.message);
  process.exitCode = 1;
});
