const { chromium } = require(process.env.DMB_BENCHMARK_PLAYWRIGHT);
const { writeFileSync } = require("node:fs");
const { setTimeout: delay } = require("node:timers/promises");

async function pollBrowserRead(read, timeout, interval, description) {
  const deadline = performance.now() + timeout;
  while (performance.now() < deadline) {
    const value = await read();
    if (value) return value;
    await delay(interval);
  }
  throw new Error("Timed out waiting for " + description);
}

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
    if (build || process.env.DMB_BENCHMARK_LIVE_BROWSER === "1") {
      const selected = process.env.DMB_BENCHMARK_SELECTION;
      if (!selected || !selected.trim()) throw new Error("Placement fixture needs selected text");
      const editor = page.locator((build ? ".build-surface-shell" : ".world-plan-visual-editor") + " .ProseMirror[contenteditable=true]:visible");
      if (await editor.count() !== 1) throw new Error("Placement fixture needs one editable editor");
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
    const live = process.env.DMB_BENCHMARK_LIVE_BROWSER === "1";
    const send = page.getByRole("button", { name: build || live ? /^(Send message|Propose edit)$/ : /^Send message$/ });
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
    let delivered;
    try {
      await send.click({ timeout: 12000 });
      delivered = await response;
    } catch (error) {
      const alerts = await page.getByRole("alert").allTextContents();
      writeFileSync(process.env.DMB_BENCHMARK_BROWSER_RESULT, JSON.stringify({
        alerts, apiFailures, composerHasQuestion: await composer.inputValue() === process.env.DMB_BENCHMARK_QUESTION,
        planTarget: build ? undefined : await page.getByLabel("Actual Plan change target").allTextContents(),
      }, null, 2));
      throw error;
    }
    if (delivered.headers()["x-benchmark-placement-rejected"] === "1") {
      throw new Error("Plan placement failed benchmark preflight; rejected request retained");
    }
    let buildCheckpoint;
    if (process.env.DMB_BENCHMARK_LIVE_BROWSER === "1") {
      // Keep the page alive while its ordinary client consumes the terminal event.
      buildCheckpoint = await pollBrowserRead(() => page.evaluate(async () => {
        const response = await fetch("/__benchmark/browser-response-retained", { cache: "no-store" });
        const checkpoint = await response.json();
        return checkpoint.retained === true ? checkpoint : false;
      }), 75000, 250, "retained Build response");
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
      confirmation = { attempted: false };
      try {
        const checkpoint = buildCheckpoint;
        confirmation.checkpoint = { retained: checkpoint.retained === true,
          has_action: Boolean(checkpoint.action_id), has_correlation: Boolean(checkpoint.idempotency_key) };
        let action = checkpoint.action_id;
        const world = process.env.DMB_BENCHMARK_WORLD;
        if (!action && checkpoint.idempotency_key) {
          const recovered = await pollBrowserRead(() => page.evaluate(async ({ world, checkpoint }) => {
            const path = "/api/live/agent/worlds/" + encodeURIComponent(world)
              + "/conversation?include_turn_correlation=true";
            const response = await fetch(path, { cache: "no-store" });
            if (!response.ok) return false;
            const history = await response.json();
            if (history.active_conversation_id !== checkpoint.conversation_id) return false;
            const turns = history.turns.filter(turn => turn.idempotency_key === checkpoint.idempotency_key);
            if (turns.length !== 1 || ["accepted", "running"].includes(turns[0].lifecycle_status)) return false;
            const turn = turns[0];
            const actionId = turn.knowledge_context?.completion?.action_id;
            if (turn.lifecycle_status === "completed" && !actionId) return false;
            return { action_id: actionId ?? null, lifecycle: turn.lifecycle_status };
          }, { world, checkpoint }), 40000, 500, "bound durable proposal");
          confirmation.recovered_lifecycle = recovered.lifecycle;
          action = recovered.action_id;
          if (action) await page.reload();
        }
        if (!action || !/^[a-f0-9-]{36}$/i.test(action)) throw new Error("Turn has no bound proposal to confirm");
        const reviewPath = "/api/live/agent/worlds/" + encodeURIComponent(world)
          + "/build-proposals/" + encodeURIComponent(action) + "/review";
        confirmation.action_id = action;
        const review = page.getByRole("region", { name: "Suggestion review", exact: true });
        await review.waitFor({ timeout: 15000 });
        const beforeSave = await page.evaluate(async ({ id, reviewPath }) => {
          async function read(path) {
            const response = await fetch(path, { cache: "no-store" });
            return { status: response.status, body: await response.json() };
          }
          return { page: await read("/api/live/workspace-documents/" + encodeURIComponent(id) + "/snapshot?view=committed"),
            review: await read(reviewPath) };
        }, { id: documentId, reviewPath });
        confirmation.beforeSave = beforeSave;
        const exactReview = beforeSave.review.body.review ?? beforeSave.review.body;
        if (beforeSave.page.status !== 200 || beforeSave.review.status !== 200
          || exactReview.action_id !== action || exactReview.world_id !== world || exactReview.state !== "editing") {
          throw new Error("The exact editable proposal or committed page could not be read");
        }
        const text = await review.getByRole("textbox", { name: "Suggestion text" }).innerText();
        if (text.trim() !== exactReview.markdown.trim()) throw new Error("Visible suggestion differs from the bound proposal");
        const confirmed = page.waitForResponse(result => {
          const request = result.request();
          return request.method() === "POST" && new URL(result.url()).pathname === reviewPath
            && request.postDataJSON()?.operation === "confirm";
        }, { timeout: 20000 });
        confirmed.catch(() => {});
        confirmation.attempted = true;
        await review.getByRole("button", { name: "Save", exact: true }).click();
        const receipt = await confirmed;
        confirmation.request = receipt.request().postDataJSON();
        confirmation.status = receipt.status();
        confirmation.body = await receipt.json();
        const saved = confirmation.body.review ?? confirmation.body;
        confirmation.verified = receipt.ok() && saved.state === "applied" && saved.action_id === action
          && saved.world_id === world && saved.apply?.apply_id === confirmation.request.apply_id;
      } catch (error) {
        confirmation.error = String(error);
      }
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
